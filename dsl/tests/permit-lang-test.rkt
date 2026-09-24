#lang racket/base
(require rackunit
         (only-in racket/list first)
         "../permit/lang.rkt")

(test-case "permit/outfall/limit build the expected struct tree"
  (define p (permit "PA0000000" (outfall 1 (limit "TSS" (daily-max 60 mg/L)))))
  (check-equal? (permit-def-id p) "PA0000000")
  (check-equal? (length (permit-def-outfalls p)) 1)
  (define od (first (permit-def-outfalls p)))
  (check-equal? (outfall-def-number od) 1)
  (define ld (first (outfall-def-limits od)))
  (check-equal? (limit-def-parameter ld) "TSS")
  (define c (first (limit-def-clauses ld)))
  (check-true (clause:daily-max? c))
  (check-equal? (clause:daily-max-threshold c) 60)
  (check-true (exact? (clause:daily-max-threshold c))))

(test-case "bare integer thresholds are exact"
  (define c (monthly-avg 30 mg/L))
  (check-equal? (clause:monthly-avg-threshold c) 30)
  (check-true (exact? (clause:monthly-avg-threshold c))))

(test-case "#e-prefixed decimal thresholds are exact rationals, not flonums"
  (define c (monthly-avg #e0.5 MGD))
  (check-equal? (clause:monthly-avg-threshold c) 1/2)
  (check-true (exact? (clause:monthly-avg-threshold c))))

(test-case "range accepts two exact boundaries"
  (define c (range #e6.0 #e9.0 s.u.))
  (check-equal? (clause:range-min c) 6)
  (check-equal? (clause:range-max c) 9))

;; A bare (non-#e) decimal literal is an inexact flonum under Racket's
;; reader; the macros must reject it at macro-expansion time rather than
;; silently letting floating point into a compliance threshold.
(test-case "a bare decimal literal (no #e) is rejected at macro-expansion time"
  (check-exn exn:fail:syntax?
             (lambda () (expand #'(monthly-avg 0.5 MGD)))))

(test-case "sample and report-only clauses build the expected structs"
  (define sc (sample 2 per-month))
  (check-equal? (clause:sample-freq-count sc) 2)
  (check-equal? (clause:sample-freq-period sc) 'per-month)
  (check-true (clause:report-only? (report-only))))
