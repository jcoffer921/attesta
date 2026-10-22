#lang racket/base
(require rackunit "../common.rkt")

(test-case "parse-exact-decimal parses integers and decimals as exact rationals"
  (check-equal? (parse-exact-decimal "30") 30)
  (check-true (exact? (parse-exact-decimal "30")))
  (check-equal? (parse-exact-decimal "0.5") 1/2)
  (check-equal? (parse-exact-decimal "-3.25") -13/4))

(test-case "parse-exact-decimal: 0.1 + 0.2 is exact, unlike IEEE floats"
  (check-equal? (+ (parse-exact-decimal "0.1") (parse-exact-decimal "0.2")) 3/10))

(test-case "parse-exact-decimal rejects malformed input"
  (check-exn exn:fail? (lambda () (parse-exact-decimal "not-a-number"))))

(test-case "month-of extracts the calendar month"
  (check-equal? (month-of "2026-03-14") "2026-03"))

(test-case "weeks-in-month approximates via ceil(days/7)"
  (check-equal? (weeks-in-month "2026-03") 5)  ; 31 days
  (check-equal? (weeks-in-month "2026-04") 5)  ; 30 days
  (check-equal? (weeks-in-month "2026-02") 4)) ; 28 days, not a leap year

(test-case "exact->decimal-string writes exact rationals as plain decimals parse-exact-decimal accepts"
  (check-equal? (exact->decimal-string 1/2) "0.5")
  (check-equal? (exact->decimal-string 3/2) "1.5")
  (check-equal? (exact->decimal-string -13/4) "-3.25")
  (check-equal? (exact->decimal-string 30) "30")
  (check-equal? (exact->decimal-string 0) "0")
  (check-equal? (exact->decimal-string 1/1000) "0.001")
  (check-equal? (parse-exact-decimal (exact->decimal-string 27/8)) 27/8))

(test-case "exact->decimal-string refuses a non-terminating rational instead of rounding"
  (check-exn exn:fail? (lambda () (exact->decimal-string 1/3))))
