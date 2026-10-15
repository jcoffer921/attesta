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
  (append
   (for/list ([c substantive])
     (evaluate-clause outfall-num param c samples period freq report-only?))
   (frequency-traces outfall-num param freq samples period)))

;; A shortfall against the permit's sampling frequency is its own finding. It
;; is reported as a separate "sample-frequency" trace rather than by withholding
;; the statistic: the DMR statistic is computed from the samples that were
;; taken, so an exceedance in them must never be masked by a short sample count.
;; Zero samples is `missing-data` on the substantive clauses instead.
(define (frequency-traces outfall-num param freq samples period)
  (cond
    [(not freq) '()]
    [else
     (define in-period (in-period-samples outfall-num param samples period))
     (define required (required-count freq period))
     (cond
       [(and (pair? in-period) (< (length in-period) required))
        (list (trace outfall-num param "sample-frequency"
                     (map sample-rec-id in-period)
                     (map (lambda (s) (number->string (sample-rec-value s))) in-period)
                     (number->string (length in-period))
                     (number->string required)
                     "count >= required"
                     'under-sampled
                     (~a "Only " (length in-period) " sample(s) found for " param " in " period "; "
                         required " required by the permit. The statistics for this limit are computed "
                         "from the available sample(s); the shortfall is a separate monitoring-frequency finding.")))]
       [else '()])]))

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
    [(null? in-period)
     (make-trace outfall-num param c ids vals "n/a" (threshold-string c) 'missing-data
                 (~a "Only " (length in-period) " sample(s) found for " param " in " period
                     (if freq (~a "; " (required-count freq period) " required.") ".")))]
    [else
     (define-values (computed base-status lower-bound)
       (compute c in-period))
     (define status (if (and report-only? (memq base-status '(pass exceedance review-required)))
                         'report-only
                         base-status))
     (define nd-ids (map sample-rec-id (filter sample-rec-non-detect? in-period)))
     (make-trace outfall-num param c ids vals computed (threshold-string c) status
                 (reason-for c status computed nd-ids lower-bound))]))

(define (num->str x) (number->string x))

(define (threshold-string c)
  (cond
    [(clause:monthly-avg? c) (num->str (clause:monthly-avg-threshold c))]
    [(clause:daily-max? c) (num->str (clause:daily-max-threshold c))]
    [(clause:range? c) (~a (num->str (clause:range-min c)) ".." (num->str (clause:range-max c)))]))

;; Non-detect handling (PA DEP): a non-detect enters the statistic at its
;; reporting limit, so a computed value that involves one is an UPPER bound
;; and is shown qualified with "<". A pass on that upper bound is a real
;; pass. An exceedance that disappears when every non-detect is taken as 0
;; (the lower bound) cannot be demonstrated, so it is `review-required`
;; rather than `exceedance`.
(define (qualify str qualified?)
  (if qualified? (string-append "<" str) str))

(define (any-nd-at? in-period v)
  (ormap (lambda (s) (and (sample-rec-non-detect? s) (= (sample-rec-value s) v))) in-period))

;; compute : clause (listof sample-rec) -> (values computed status lower-bound-or-#f)
(define (compute c in-period)
  (define vals (map sample-rec-value in-period))
  (define nd? sample-rec-non-detect?)
  (define any-nd? (ormap nd? in-period))
  (cond
    [(clause:monthly-avg? c)
     (define n (length vals))
     (define mean (/ (apply + vals) n))
     (define lower (/ (apply + (for/list ([s in-period])
                                 (if (nd? s) 0 (sample-rec-value s))))
                      n))
     (define thr (clause:monthly-avg-threshold c))
     (values (qualify (num->str mean) any-nd?)
             (cond [(<= mean thr) 'pass]
                   [(> lower thr) 'exceedance]
                   [else 'review-required])
             (and any-nd? (num->str lower)))]
    [(clause:daily-max? c)
     (define mx (apply max vals))
     (define thr (clause:daily-max-threshold c))
     (define detected (for/list ([s in-period] #:unless (nd? s)) (sample-rec-value s)))
     (define detected-max (and (pair? detected) (apply max detected)))
     ;; qualified only when the maximum is attained solely by non-detects
     (define max-is-nd? (and (any-nd-at? in-period mx)
                             (not (and detected-max (= detected-max mx)))))
     (values (qualify (num->str mx) max-is-nd?)
             (cond [(<= mx thr) 'pass]
                   [(and detected-max (> detected-max thr)) 'exceedance]
                   [else 'review-required])
             (and max-is-nd? (if detected-max (num->str detected-max) "0")))]
    [(clause:range? c)
     (define mn (apply min vals))
     (define mx (apply max vals))
     (define below? (ormap (lambda (v) (< v (clause:range-min c))) vals))
     (define above? (ormap (lambda (v) (> v (clause:range-max c))) vals))
     (values (~a "min=" (num->str mn) " max=" (num->str mx))
             (if (or below? above?) 'exceedance 'pass)
             #f)]))

(define (make-trace outfall-num param c ids vals computed threshold status reason)
  (trace outfall-num param (clause-name c) ids (map num->str vals)
         computed threshold (comparison-for c) status reason))

(define (comparison-for c)
  (cond
    [(clause:monthly-avg? c) "mean <= threshold"]
    [(clause:daily-max? c) "max <= threshold"]
    [(clause:range? c) "min <= value <= max"]))

(define (reason-for c status computed nd-ids lower-bound)
  (define name (clause-name c))
  (define nd-note
    (if (null? nd-ids)
        ""
        (~a " Non-detect sample(s) " nd-ids " are used at their reporting limits.")))
  (case status
    [(pass) (~a name " is within limits (computed " computed ")." nd-note)]
    [(exceedance) (~a name " exceeds the permit limit (computed " computed ")." nd-note)]
    [(review-required)
     (~a name " computed " computed " exceeds the permit limit only because non-detect sample(s) "
         nd-ids " are used at their reporting limits; with those taken as zero the value is "
         lower-bound ". Compliance cannot be demonstrated or refuted from this data - human review required.")]
    [(report-only) (~a name " computed " computed "; limit is report-only, no pass/fail applies." nd-note)]))
