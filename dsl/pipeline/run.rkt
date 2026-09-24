#lang racket/base
;; Interprets a pipeline-def over a list of raw records (jsexpr-shaped
;; hasheq tables with symbol keys). Pure: no I/O, no randomness, no clock
;; reads. Every step application on every record produces a provenance
;; entry; a step that cannot apply produces a rejection entry and the record
;; is never silently dropped -- it just stops progressing through the
;; remaining steps.

(provide run-pipeline)

(require racket/string
         racket/format
         "lang.rkt"
         "../common.rkt")

;; run-pipeline : pipeline-def (listof jsexpr-hash) -> (values (listof jsexpr-hash) (listof provenance-entry) (listof rejection-entry))
(define (run-pipeline pdef raw-records)
  (define steps (pipeline-def-steps pdef))
  (define marker (extract-marker steps))
  (define finals '())
  (define provenance '())
  (define rejections '())
  (for ([rec raw-records])
    (define-values (status result entries reject) (process-record rec steps marker))
    (set! provenance (append provenance entries))
    (cond
      [(eq? status 'reject)
       (set! rejections (append rejections (list reject)))]
      [else
       (set! finals (append finals (list result)))]))
  (values finals provenance rejections))

;; process-record : jsexpr-hash (listof step) (or/c string? #f)
;;   -> (values (or/c 'ok 'reject) (or/c jsexpr-hash #f) (listof provenance-entry) (or/c rejection-entry #f))
(define (process-record rec steps marker)
  (let loop ([rec rec] [steps steps] [entries '()])
    (cond
      [(null? steps) (values 'ok rec (reverse entries) #f)]
      [else
       (define step (car steps))
       (define outcome (apply-step step rec marker))
       (cond
         [(eq? (car outcome) 'reject)
          (values 'reject #f (reverse entries) (cdr outcome))]
         [else
          (loop (cadr outcome) (cdr steps) (cons (cddr outcome) entries))])])))

(define (record-id rec) (hash-ref rec 'id "unknown"))

(define (extract-marker steps)
  (define nd (findf step:non-detect? steps))
  (and nd (step:non-detect-marker nd)))

(define (step-name step)
  (cond [(step:map-column? step) "map-column"]
        [(step:convert-units? step) "convert-units"]
        [(step:non-detect? step) "non-detect"]
        [(step:require-field? step) "require-field"]))

;; apply-step : step jsexpr-hash (or/c string? #f) -> (cons/c 'ok (cons/c jsexpr-hash provenance-entry))
;;                                                   | (cons/c 'reject rejection-entry)
(define (apply-step step rec marker)
  (cond
    [(step:map-column? step) (apply-map-column step rec)]
    [(step:convert-units? step) (apply-convert-units step rec marker)]
    [(step:non-detect? step) (apply-non-detect step rec)]
    [(step:require-field? step) (apply-require-field step rec)]))

(define (mk-ok name rec new-rec note)
  (list* 'ok new-rec (provenance-entry name (record-id rec) rec new-rec note)))

(define (mk-reject name rec reason)
  (cons 'reject (rejection-entry name (record-id rec) reason)))

(define (apply-map-column step rec)
  (define name "map-column")
  (define from (step:map-column-from step))
  (define to (step:map-column-to step))
  (define from-sym (string->symbol from))
  (cond
    [(hash-has-key? rec from-sym)
     (define val (hash-ref rec from-sym))
     (define new-rec (hash-set (hash-remove rec from-sym) to val))
     (mk-ok name rec new-rec (~a "renamed column " from " to " to))]
    [else
     (mk-reject name rec (~a "missing source column: " from))]))

(define unit-conversion-factors
  (hash '(ug/L . mg/L) 1/1000
        '(mg/L . ug/L) 1000))

(define (split-marker valstr marker)
  (if (and marker (string-prefix? valstr marker))
      (values marker (substring valstr (string-length marker)))
      (values "" valstr)))

(define (apply-convert-units step rec marker)
  (define name "convert-units")
  (define from-unit (step:convert-units-from-unit step))
  (define to-unit (step:convert-units-to-unit step))
  (define cur-unit-str (hash-ref rec 'unit #f))
  (define cur-unit (and cur-unit-str (string->symbol cur-unit-str)))
  (cond
    [(eq? cur-unit from-unit)
     (define valstr (hash-ref rec 'value))
     (define-values (prefix magnitude-str) (split-marker valstr marker))
     (define magnitude (parse-exact-decimal magnitude-str))
     (define factor (hash-ref unit-conversion-factors (cons from-unit to-unit) #f))
     (cond
       [(not factor)
        (mk-reject name rec (~a "no conversion known from " from-unit " to " to-unit))]
       [else
        (define converted (* magnitude factor))
        (define new-valstr (string-append prefix (number->string converted)))
        (define new-rec (hash-set (hash-set rec 'value new-valstr) 'unit (symbol->string to-unit)))
        (mk-ok name rec new-rec
               (~a "converted " magnitude-str " " from-unit " to " (number->string converted) " " to-unit))])]
    [else
     (mk-ok name rec rec (~a "unit " cur-unit-str " did not match " from-unit "; left unchanged"))]))

(define (apply-non-detect step rec)
  (define name "non-detect")
  (define marker (step:non-detect-marker step))
  (define treat-as (step:non-detect-treat-as step))
  (define valstr (hash-ref rec 'value))
  (cond
    [(string-prefix? valstr marker)
     (define magnitude-str (substring valstr (string-length marker)))
     (define magnitude (parse-exact-decimal magnitude-str))
     (define new-value
       (case treat-as
         [(zero) 0]
         [(half-mdl) (/ magnitude 2)]
         [(report-limit) magnitude]))
     (define new-rec (hash-set (hash-set rec 'value (number->string new-value)) 'non_detect #t))
     (mk-ok name rec new-rec
            (~a "non-detect value " valstr " treated as " treat-as " -> " (number->string new-value)))]
    [else
     (define new-rec (hash-set rec 'non_detect #f))
     (mk-ok name rec new-rec "not a non-detect value")]))

(define (blank? v) (or (not v) (equal? v "") (eq? v 'null)))

(define (apply-require-field step rec)
  (define name "require-field")
  (define fields (step:require-field-fields step))
  (define missing (filter (lambda (f) (or (not (hash-has-key? rec f)) (blank? (hash-ref rec f)))) fields))
  (cond
    [(null? missing) (mk-ok name rec rec "required fields present")]
    [else (mk-reject name rec (~a "missing required field(s): " missing))]))
