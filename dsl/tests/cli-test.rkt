#lang racket/base
;; Exercises the actual CLI as a subprocess, the way Django will call it:
;; JSON in on stdin, JSON out on stdout, structured error envelope + nonzero
;; exit on failure.

(require rackunit
         racket/system
         racket/port
         racket/runtime-path
         json)

(define-runtime-path main-rkt "../main.rkt")
(define-runtime-path repo-root "../..")
(define-runtime-path permit-file "../permit/permits/pa0000000.rkt")
(define-runtime-path pipeline-file "../pipeline/pipelines/lab-csv-import.rkt")

;; run-cli : (listof string) string -> (values jsexpr exit-code)
(define (run-cli args stdin-text)
  (define-values (proc out in err)
    (parameterize ([current-directory repo-root])
      (apply subprocess #f #f #f (find-system-path 'exec-file) (path->string main-rkt) args)))
  (display stdin-text in)
  (close-output-port in)
  (define stdout-text (port->string out))
  (define stderr-text (port->string err))
  (subprocess-wait proc)
  (close-input-port out)
  (close-input-port err)
  (values (with-handlers ([exn:fail? (lambda (e) (error 'run-cli "non-JSON stdout: ~a\nstderr: ~a" stdout-text stderr-text))])
            (read-json (open-input-string stdout-text)))
          (subprocess-status proc)))

(define valid-input
  (jsexpr->string
   (hasheq 'schema_version 1
           'records
           (list (hasheq 'id "r1" 'outfall 1 'Analyte "TSS" 'value "27.5" 'unit "mg/L"
                         'sample_date "2026-03-05" 'method "SM2540D")
                 (hasheq 'id "r2" 'outfall 1 'Analyte "TSS" 'value "31.0" 'unit "mg/L"
                         'sample_date "2026-03-12" 'method "SM2540D")))))

(test-case "run: valid JSON in produces the documented JSON envelope"
  (define-values (result code)
    (run-cli (list "run" "--permit" (path->string permit-file) "--pipeline" (path->string pipeline-file))
             valid-input))
  (check-equal? code 0)
  (check-equal? (hash-ref result 'schema_version) 1)
  (check-true (list? (hash-ref result 'provenance)))
  (check-true (list? (hash-ref result 'results)))
  (check-true (list? (hash-ref result 'rejections)))
  (define tss-monthly-avg
    (findf (lambda (r) (and (equal? (hash-ref r 'parameter) "TSS") (equal? (hash-ref r 'clause) "monthly-avg")))
           (hash-ref result 'results)))
  (check-equal? (hash-ref tss-monthly-avg 'status) "pass"))

(test-case "describe: emits the permit's limits as JSON, never s-expressions"
  (define-values (result code)
    (run-cli (list "describe" "--permit" (path->string permit-file)) ""))
  (check-equal? code 0)
  (check-equal? (hash-ref (hash-ref result 'permit) 'permit_id) "PA0000000"))

(test-case "malformed JSON on stdin returns a structured error, not a crash"
  (define-values (result code)
    (run-cli (list "run" "--permit" (path->string permit-file) "--pipeline" (path->string pipeline-file))
             "this is not json"))
  (check-not-equal? code 0)
  (check-true (hash? (hash-ref result 'error #f)))
  (check-true (string? (hash-ref (hash-ref result 'error) 'code))))

(test-case "a record rejected by the pipeline appears in rejections, not the results silently"
  (define bad-input
    (jsexpr->string
     (hasheq 'schema_version 1
             'records
             (list (hasheq 'id "bad1" 'outfall 1 'value "27.5" 'unit "mg/L"
                           'sample_date "2026-03-05" 'method "SM2540D")))))
  (define-values (result code)
    (run-cli (list "run" "--permit" (path->string permit-file) "--pipeline" (path->string pipeline-file))
             bad-input))
  (check-equal? code 0)
  (check-equal? (length (hash-ref result 'rejections)) 1)
  (check-equal? (hash-ref (car (hash-ref result 'rejections)) 'record_id) "bad1"))

(test-case "a permit path outside the restricted permits directory is refused"
  (define-values (result code)
    (run-cli (list "describe" "--permit" (path->string main-rkt)) ""))
  (check-not-equal? code 0)
  (check-true (hash? (hash-ref result 'error #f))))
