#lang racket/base
;; Evaluates monitoring samples against a permit definition, producing one
;; evidence trace per substantive limit clause (monthly-avg / daily-max /
;; range). Pure: no I/O, no randomness, no clock reads. All arithmetic is on
;; exact rationals.

(provide evaluate-permit)

(require (except-in racket/list range)
         racket/format
         "lang.rkt"
         "../common.rkt")

;; evaluate-permit : permit-def (listof sample-rec) string -> (listof trace)
;; period is a "YYYY-MM" string identifying the reporting month being
;; evaluated. Monthly-avg / daily-max / range / sample-freq are all scoped to
;; samples whose sample-date falls within this period.
(define (evaluate-permit pdef samples period)
  (append*
   (for/list ([od (permit-def-outfalls pdef)])
     (append*
      (for/list ([ld (outfall-def-limits od)])
        (evaluate-limit (outfall-def-number od) (limit-def-parameter ld)
                         (limit-def-clauses ld) samples period))))))

(define (evaluate-limit outfall-num param clauses samples period)
  (define freq (findf clause:sample-freq? clauses))
  (define report-only? (ormap clause:report-only? clauses))
  (define substantive
    (filter (lambda (c) (or (clause:monthly-avg? c) (clause:daily-max? c) (clause:range? c)))
            clauses))
  (for/list ([c substantive])
    (evaluate-clause outfall-num param c samples period freq report-only?)))

(define (clause-unit c)
  (cond [(clause:monthly-avg? c) (clause:monthly-avg-unit c)]
        [(clause:daily-max? c) (clause:daily-max-unit c)]
        [(clause:range? c) (clause:range-unit c)]))

(define (clause-name c)
  (cond [(clause:monthly-avg? c) "monthly-avg"]
        [(clause:daily-max? c) "daily-max"]
        [(clause:range? c) "range"]))

(define (required-count freq period)
  (case (clause:sample-freq-period freq)
    [(per-month) (clause:sample-freq-count freq)]
    [(per-week) (* (clause:sample-freq-count freq) (weeks-in-month period))]
    [else (error 'required-count "unknown sample-freq period: ~a" (clause:sample-freq-period freq))]))

(define (in-period-samples outfall-num param samples period)
  (filter (lambda (s)
            (and (equal? (sample-rec-outfall s) outfall-num)
                 (equal? (sample-rec-parameter s) param)
                 (equal? (month-of (sample-rec-sample-date s)) period)))
          samples))

(define (evaluate-clause outfall-num param c samples period freq report-only?)
  (define in-period (in-period-samples outfall-num param samples period))
  (define unit (clause-unit c))
  (define mismatched (filter (lambda (s) (not (eq? (sample-rec-unit s) unit))) in-period))
  (define ids (map sample-rec-id in-period))
  (define vals (map sample-rec-value in-period))
  (cond
    [(pair? mismatched)
     (make-trace outfall-num param c ids vals "n/a" (threshold-string c) 'unit-error
                 (~a "Sample(s) " (map sample-rec-id mismatched)
                     " report unit(s) " (map sample-rec-unit mismatched)
                     " but the limit requires " unit "; conversion is not performed here."))]
    [(or (null? in-period)
         (and freq (< (length in-period) (required-count freq period))))
     (make-trace outfall-num param c ids vals "n/a" (threshold-string c) 'missing-data
                 (~a "Only " (length in-period) " sample(s) found for " param " in " period
                     (if freq (~a "; " (required-count freq period) " required.") ".")))]
    [else
     (define-values (computed comparison base-status)
       (compute c vals))
     (define status (if (and report-only? (memq base-status '(pass exceedance)))
                         'report-only
                         base-status))
     (make-trace outfall-num param c ids vals computed (threshold-string c) status
                 (reason-for c status computed))]))

(define (num->str x) (number->string x))

(define (threshold-string c)
  (cond
    [(clause:monthly-avg? c) (num->str (clause:monthly-avg-threshold c))]
    [(clause:daily-max? c) (num->str (clause:daily-max-threshold c))]
    [(clause:range? c) (~a (num->str (clause:range-min c)) ".." (num->str (clause:range-max c)))]))

(define (compute c vals)
  (cond
    [(clause:monthly-avg? c)
     (define mean (/ (apply + vals) (length vals)))
     (values (num->str mean) "mean <= threshold"
             (if (> mean (clause:monthly-avg-threshold c)) 'exceedance 'pass))]
    [(clause:daily-max? c)
     (define mx (apply max vals))
     (values (num->str mx) "max <= threshold"
             (if (> mx (clause:daily-max-threshold c)) 'exceedance 'pass))]
    [(clause:range? c)
     (define mn (apply min vals))
     (define mx (apply max vals))
     (define below? (ormap (lambda (v) (< v (clause:range-min c))) vals))
     (define above? (ormap (lambda (v) (> v (clause:range-max c))) vals))
     (values (~a "min=" (num->str mn) " max=" (num->str mx)) "min <= value <= max"
             (if (or below? above?) 'exceedance 'pass))]))

(define (make-trace outfall-num param c ids vals computed threshold status reason)
  (trace outfall-num param (clause-name c) ids (map num->str vals)
         computed threshold (comparison-for c) status reason))

(define (comparison-for c)
  (cond
    [(clause:monthly-avg? c) "mean <= threshold"]
    [(clause:daily-max? c) "max <= threshold"]
    [(clause:range? c) "min <= value <= max"]))

(define (reason-for c status computed)
  (define name (clause-name c))
  (case status
    [(pass) (~a name " is within limits (computed " computed ").")]
    [(exceedance) (~a name " exceeds the permit limit (computed " computed ").")]
    [(report-only) (~a name " computed " computed "; limit is report-only, no pass/fail applies.")]))
