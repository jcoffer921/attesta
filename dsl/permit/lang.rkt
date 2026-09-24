#lang racket/base
;; Permit Rules DSL: declarative forms for permit / outfall / limit / clauses.
;;
;; Numeric literals for thresholds must be exact at read time. Bare integers
;; (30, 60, 2) are already exact under Racket's reader. Non-integer
;; thresholds must use the `#e` exact-decimal prefix (e.g. #e6.0, #e0.5) --
;; without it the reader would produce an inexact flonum, and these macros
;; reject that at macro-expansion time with a clear error instead of letting
;; floating point silently creep into a compliance evaluation.

(provide permit outfall limit
         monthly-avg daily-max range sample report-only
         mg/L s.u. MGD per-month per-week
         (struct-out permit-def)
         (struct-out outfall-def)
         (struct-out limit-def)
         (struct-out clause:monthly-avg)
         (struct-out clause:daily-max)
         (struct-out clause:range)
         (struct-out clause:sample-freq)
         (struct-out clause:report-only))

(require (for-syntax racket/base))

(struct permit-def (id outfalls) #:transparent)
(struct outfall-def (number limits) #:transparent)
(struct limit-def (parameter clauses) #:transparent)

(struct clause:monthly-avg (threshold unit) #:transparent)
(struct clause:daily-max (threshold unit) #:transparent)
(struct clause:range (min max unit) #:transparent)
(struct clause:sample-freq (count period) #:transparent)
(struct clause:report-only () #:transparent)

;; Unit / period tokens used as bare identifiers in permit source.
(define mg/L 'mg/L)
(define s.u. 's.u.)
(define MGD 'MGD)
(define per-month 'per-month)
(define per-week 'per-week)

(begin-for-syntax
  (define (check-exact-literal! stx id-stx label)
    (define v (syntax-e id-stx))
    (unless (and (number? v) (exact? v))
      (raise-syntax-error
       #f
       (format "~a must be an exact number literal; use the #e prefix for decimals (e.g. #e0.5)"
               label)
       stx id-stx))))

(define-syntax (permit stx)
  (syntax-case stx ()
    [(_ id outfall-expr ...)
     #'(permit-def id (list outfall-expr ...))]))

(define-syntax (outfall stx)
  (syntax-case stx ()
    [(_ number limit-expr ...)
     #'(outfall-def number (list limit-expr ...))]))

(define-syntax (limit stx)
  (syntax-case stx ()
    [(_ parameter clause-expr ...)
     #'(limit-def parameter (list clause-expr ...))]))

(define-syntax (monthly-avg stx)
  (syntax-case stx ()
    [(_ threshold unit)
     (begin
       (check-exact-literal! stx #'threshold "monthly-avg threshold")
       #'(clause:monthly-avg threshold unit))]))

(define-syntax (daily-max stx)
  (syntax-case stx ()
    [(_ threshold unit)
     (begin
       (check-exact-literal! stx #'threshold "daily-max threshold")
       #'(clause:daily-max threshold unit))]))

(define-syntax (range stx)
  (syntax-case stx ()
    [(_ mn mx unit)
     (begin
       (check-exact-literal! stx #'mn "range min")
       (check-exact-literal! stx #'mx "range max")
       #'(clause:range mn mx unit))]))

(define-syntax (sample stx)
  (syntax-case stx ()
    [(_ count period)
     (begin
       (check-exact-literal! stx #'count "sample count")
       #'(clause:sample-freq count 'period))]))

(define-syntax (report-only stx)
  (syntax-case stx ()
    [(_) #'(clause:report-only)]))
