#lang racket/base
(require rackunit
         "../common.rkt"
         "../permit/lang.rkt"
         "../permit/eval.rkt")

(define (s id outfall param value unit date [nd #f])
  (sample-rec id outfall param (parse-exact-decimal value) unit date nd))

(define (find-trace results param clause-name)
  (findf (lambda (t) (and (equal? (trace-parameter t) param) (equal? (trace-clause t) clause-name)))
         results))

;; --- daily-max: value exactly at the limit must pass, not exceed ---
(test-case "daily-max: value exactly at limit is compliant"
  (define p (permit "PA0000000" (outfall 1 (limit "TSS" (daily-max 60 mg/L)))))
  (define samples (list (s "a1" 1 "TSS" "60" 'mg/L "2026-03-05")))
  (define r (evaluate-permit p samples "2026-03"))
  (check-equal? (trace-status (find-trace r "TSS" "daily-max")) 'pass))

(test-case "daily-max: exceedance when strictly above the limit"
  (define p (permit "PA0000000" (outfall 1 (limit "TSS" (daily-max 60 mg/L)))))
  (define samples (list (s "a1" 1 "TSS" "60.01" 'mg/L "2026-03-05")))
  (define r (evaluate-permit p samples "2026-03"))
  (check-equal? (trace-status (find-trace r "TSS" "daily-max")) 'exceedance))

;; --- monthly-avg: exceedance when mean is strictly above threshold ---
(test-case "monthly-avg: mean exactly at threshold passes, above it exceeds"
  (define p (permit "PA0000000" (outfall 1 (limit "TSS" (monthly-avg 30 mg/L)))))
  (define at-limit (list (s "a1" 1 "TSS" "30" 'mg/L "2026-03-01") (s "a2" 1 "TSS" "30" 'mg/L "2026-03-15")))
  (define over-limit (list (s "b1" 1 "TSS" "30" 'mg/L "2026-03-01") (s "b2" 1 "TSS" "30.5" 'mg/L "2026-03-15")))
  (check-equal? (trace-status (find-trace (evaluate-permit p at-limit "2026-03") "TSS" "monthly-avg")) 'pass)
  (check-equal? (trace-status (find-trace (evaluate-permit p over-limit "2026-03") "TSS" "monthly-avg")) 'exceedance))

;; --- range: both boundary values must pass ---
(test-case "range: pH exactly at 6.0 and exactly at 9.0 both pass"
  (define p (permit "PA0000000" (outfall 1 (limit "pH" (range #e6.0 #e9.0 s.u.)))))
  (define samples (list (s "p1" 1 "pH" "6.0" 's.u. "2026-03-01") (s "p2" 1 "pH" "9.0" 's.u. "2026-03-15")))
  (check-equal? (trace-status (find-trace (evaluate-permit p samples "2026-03") "pH" "range")) 'pass))

(test-case "range: below min or above max is an exceedance"
  (define p (permit "PA0000000" (outfall 1 (limit "pH" (range #e6.0 #e9.0 s.u.)))))
  (define below (list (s "p1" 1 "pH" "5.9" 's.u. "2026-03-01")))
  (define above (list (s "p1" 1 "pH" "9.1" 's.u. "2026-03-01")))
  (check-equal? (trace-status (find-trace (evaluate-permit p below "2026-03") "pH" "range")) 'exceedance)
  (check-equal? (trace-status (find-trace (evaluate-permit p above "2026-03") "pH" "range")) 'exceedance))

;; --- missing-data: fewer samples than the declared frequency ---
(test-case "missing-data: fewer samples than required in the period"
  (define p (permit "PA0000000" (outfall 1 (limit "TSS" (monthly-avg 30 mg/L) (sample 2 per-month)))))
  (define samples (list (s "a1" 1 "TSS" "10" 'mg/L "2026-03-05")))
  (check-equal? (trace-status (find-trace (evaluate-permit p samples "2026-03") "TSS" "monthly-avg")) 'missing-data))

;; --- missing-data: an empty month (zero samples), even with no explicit sample clause ---
(test-case "missing-data: empty month with zero samples cannot be evaluated"
  (define p (permit "PA0000000" (outfall 1 (limit "Flow" (monthly-avg #e0.5 MGD)))))
  (define r (evaluate-permit p '() "2026-04"))
  (check-equal? (trace-status (find-trace r "Flow" "monthly-avg")) 'missing-data))

;; --- missing-data: per-week frequency shortfall ---
(test-case "missing-data: per-week sample frequency shortfall over the month"
  (define p (permit "PA0000000" (outfall 1 (limit "pH" (range #e6.0 #e9.0 s.u.) (sample 1 per-week)))))
  ;; March 2026 has 31 days -> 5 week-buckets required; only one sample given.
  (define samples (list (s "p1" 1 "pH" "7.0" 's.u. "2026-03-05")))
  (check-equal? (trace-status (find-trace (evaluate-permit p samples "2026-03") "pH" "range")) 'missing-data))

;; --- unit-error: sample unit does not match the limit's unit, never auto-converted ---
(test-case "unit-error: mismatched sample unit is never auto-converted"
  (define p (permit "PA0000000" (outfall 1 (limit "TSS" (daily-max 60 mg/L)))))
  (define samples (list (s "a1" 1 "TSS" "45" 'ug/L "2026-03-05")))
  (check-equal? (trace-status (find-trace (evaluate-permit p samples "2026-03") "TSS" "daily-max")) 'unit-error))

;; --- report-only: value is reported, no pass/fail, even when it would exceed ---
(test-case "report-only: no pass/fail even when the computed value would exceed"
  (define p (permit "PA0000000" (outfall 1 (limit "Flow" (monthly-avg #e0.5 MGD) (report-only)))))
  (define samples (list (s "f1" 1 "Flow" "0.9" 'MGD "2026-03-05")))
  (check-equal? (trace-status (find-trace (evaluate-permit p samples "2026-03") "Flow" "monthly-avg")) 'report-only))

;; --- exact arithmetic: classic 0.1 + 0.2 must not show floating-point drift ---
(test-case "exact arithmetic: 0.1 + 0.2 averages to an exact rational"
  (define p (permit "PA0000000" (outfall 1 (limit "TSS" (monthly-avg #e1.0 mg/L)))))
  (define samples (list (s "a1" 1 "TSS" "0.1" 'mg/L "2026-03-01") (s "a2" 1 "TSS" "0.2" 'mg/L "2026-03-02")))
  (define t (find-trace (evaluate-permit p samples "2026-03") "TSS" "monthly-avg"))
  (check-equal? (trace-computed-value t) "3/20")
  (check-equal? (trace-status t) 'pass))

;; --- multiple substantive clauses on one limit each produce their own trace ---
(test-case "a limit with two substantive clauses produces two independent traces"
  (define p (permit "PA0000000" (outfall 1 (limit "TSS" (monthly-avg 30 mg/L) (daily-max 60 mg/L)))))
  (define samples (list (s "a1" 1 "TSS" "70" 'mg/L "2026-03-05")))
  (define r (evaluate-permit p samples "2026-03"))
  (check-equal? (trace-status (find-trace r "TSS" "monthly-avg")) 'exceedance)
  (check-equal? (trace-status (find-trace r "TSS" "daily-max")) 'exceedance))
