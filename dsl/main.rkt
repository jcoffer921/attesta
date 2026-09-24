#lang racket/base
;; CLI entry point for the Attesta rule core.
;;
;;   racket dsl/main.rkt run --permit <file> --pipeline <file> [--period YYYY-MM]
;;   racket dsl/main.rkt describe --permit <file>
;;
;; Reads/writes JSON only; never evaluates DSL source text passed on the
;; command line or via stdin -- only files loaded from the repo's
;; dsl/permit/permits/ and dsl/pipeline/pipelines/ directories are
;; evaluated. On any error, writes {"error": {"code", "message"}} to stdout
;; and exits nonzero; never a raw stack trace.

(require json
         racket/runtime-path
         racket/path
         racket/string
         "common.rkt"
         "json.rkt"
         "permit/eval.rkt"
         "pipeline/run.rkt")

(define-runtime-path permits-dir "permit/permits")
(define-runtime-path pipelines-dir "pipeline/pipelines")

(struct cli-error (code message) #:transparent)

;; resolve-restricted : path-string path -> path
;; Only files that live inside `allowed-dir` (after path normalization) may
;; be loaded as DSL definitions.
(define (resolve-restricted file-str allowed-dir label)
  (define file (simplify-path (path->complete-path file-str) #f))
  (define allowed (simplify-path (path->complete-path allowed-dir) #f))
  (unless (path-prefix? file allowed)
    (raise (cli-error "invalid-path"
                       (format "~a must be a file under ~a" label allowed))))
  (unless (file-exists? file)
    (raise (cli-error "file-error" (format "~a not found: ~a" label file))))
  file)

(define (path-prefix? file dir)
  (define file-parts (explode-path file))
  (define dir-parts (explode-path dir))
  (and (<= (length dir-parts) (length file-parts))
       (for/and ([f file-parts] [d dir-parts]) (equal? f d))))

(define (load-permit file-str)
  (define path (resolve-restricted file-str permits-dir "--permit"))
  (with-handlers ([exn:fail? (lambda (e) (raise (cli-error "parse-error" (format "failed to load permit: ~a" (exn-message e)))))])
    (dynamic-require path 'the-permit)))

(define (load-pipeline file-str)
  (define path (resolve-restricted file-str pipelines-dir "--pipeline"))
  (with-handlers ([exn:fail? (lambda (e) (raise (cli-error "parse-error" (format "failed to load pipeline: ~a" (exn-message e)))))])
    (dynamic-require path 'the-pipeline)))

(define (parse-flags args)
  (let loop ([args args] [acc (hasheq)])
    (cond
      [(null? args) acc]
      [(and (pair? (cdr args)) (string-prefix? (car args) "--"))
       (loop (cddr args) (hash-set acc (string->symbol (substring (car args) 2)) (cadr args)))]
      [else (raise (cli-error "bad-args" (format "unrecognized argument(s): ~a" args)))])))

(define (read-stdin-json)
  (with-handlers ([exn:fail? (lambda (e) (raise (cli-error "invalid-json" (format "could not parse JSON on stdin: ~a" (exn-message e)))))])
    (define j (read-json (current-input-port)))
    (when (eof-object? j)
      (raise (cli-error "invalid-json" "empty stdin; expected a JSON object")))
    j))

(define (default-period raw-records)
  (cond
    [(null? raw-records) (raise (cli-error "eval-error" "no records supplied and no --period given; cannot infer reporting period"))]
    [else (month-of (hash-ref (car raw-records) 'sample_date))]))

(define (cmd-run flags)
  (define permit (load-permit (hash-ref flags 'permit (lambda () (raise (cli-error "bad-args" "missing --permit"))))))
  (define pipeline (load-pipeline (hash-ref flags 'pipeline (lambda () (raise (cli-error "bad-args" "missing --pipeline"))))))
  (define input (read-stdin-json))
  (unless (and (hash? input) (equal? (hash-ref input 'schema_version #f) 1))
    (raise (cli-error "invalid-json" "expected an object with schema_version: 1")))
  (define raw-records (hash-ref input 'records '()))
  (unless (list? raw-records)
    (raise (cli-error "invalid-json" "\"records\" must be an array")))
  (define-values (finals provenance rejections)
    (with-handlers ([exn:fail? (lambda (e) (raise (cli-error "eval-error" (format "pipeline failed: ~a" (exn-message e)))))])
      (run-pipeline pipeline raw-records)))
  (define period (hash-ref flags 'period (lambda () (default-period raw-records))))
  (define samples
    (with-handlers ([exn:fail? (lambda (e) (raise (cli-error "eval-error" (format "invalid normalized record: ~a" (exn-message e)))))])
      (map record->sample-rec finals)))
  (define results
    (with-handlers ([exn:fail? (lambda (e) (raise (cli-error "eval-error" (format "evaluation failed: ~a" (exn-message e)))))])
      (evaluate-permit permit samples period)))
  (write-json
   (hasheq 'schema_version 1
           'provenance (map provenance-entry->jsexpr provenance)
           'results (map trace->jsexpr results)
           'rejections (map rejection-entry->jsexpr rejections))))

(define (cmd-describe flags)
  (define permit (load-permit (hash-ref flags 'permit (lambda () (raise (cli-error "bad-args" "missing --permit"))))))
  (write-json (hasheq 'schema_version 1 'permit (permit->jsexpr permit))))

(module+ main
  (define argv (current-command-line-arguments))
  (with-handlers
      ([cli-error? (lambda (e)
                     (write-json (error-jsexpr (cli-error-code e) (cli-error-message e)))
                     (newline)
                     (exit 1))]
       [exn:fail? (lambda (e)
                    (write-json (error-jsexpr "internal-error" (exn-message e)))
                    (newline)
                    (exit 1))])
    (when (zero? (vector-length argv))
      (raise (cli-error "bad-args" "expected a subcommand: run | describe")))
    (define subcommand (vector-ref argv 0))
    (define flags (parse-flags (cdr (vector->list argv))))
    (case subcommand
      [("run") (cmd-run flags)]
      [("describe") (cmd-describe flags)]
      [else (raise (cli-error "bad-args" (format "unknown subcommand: ~a" subcommand)))])
    (newline)))
