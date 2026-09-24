#lang racket/base
;; Shared, pure helpers used by both DSLs. No I/O, no randomness, no clock reads.

(provide parse-exact-decimal
         month-of
         days-in-month
         weeks-in-month
         (struct-out sample-rec)
         (struct-out trace)
         (struct-out provenance-entry)
         (struct-out rejection-entry))

(require racket/string)

;; parse-exact-decimal : string -> exact-rational
;; Parses a plain decimal string ("30", "0.5", "-3.25") into an exact
;; rational. Never goes through inexact/flonum arithmetic, so results are
;; bit-for-bit reproducible regardless of platform.
(define (parse-exact-decimal s)
  (unless (string? s)
    (error 'parse-exact-decimal "expected a string, got: ~e" s))
  (define m (regexp-match #px"^(-?)([0-9]+)(?:\\.([0-9]+))?$" s))
  (unless m
    (error 'parse-exact-decimal "not a valid decimal string: ~a" s))
  (define sign (list-ref m 1))
  (define int-part (list-ref m 2))
  (define frac-part (or (list-ref m 3) ""))
  (define digits (string-append int-part frac-part))
  (define numerator (string->number digits))
  (define denom (expt 10 (string-length frac-part)))
  (define magnitude (/ numerator denom))
  (if (string=? sign "-") (- magnitude) magnitude))

;; month-of : "YYYY-MM-DD" -> "YYYY-MM"
(define (month-of date-str)
  (substring date-str 0 7))

;; days-in-month : "YYYY-MM" -> exact integer
;; Pure calendar arithmetic; used only to size the "1 per week" approximation
;; below, never to read the current date.
(define (days-in-month period)
  (define year (string->number (substring period 0 4)))
  (define month (string->number (substring period 5 7)))
  (define (leap? y) (and (zero? (modulo y 4))
                          (or (not (zero? (modulo y 100))) (zero? (modulo y 400)))))
  (case month
    [(1 3 5 7 8 10 12) 31]
    [(4 6 9 11) 30]
    [(2) (if (leap? year) 29 28)]
    [else (error 'days-in-month "invalid month in period: ~a" period)]))

;; weeks-in-month : "YYYY-MM" -> exact integer
;; Approximation: ceil(days-in-month / 7). A per-week sample-frequency
;; requirement over a calendar month is checked against count * weeks, not
;; against real ISO week boundaries -- documented simplification for this
;; small DSL.
(define (weeks-in-month period)
  (define d (days-in-month period))
  (define q (quotient d 7))
  (if (zero? (remainder d 7)) q (+ q 1)))

;; A normalized monitoring sample, ready for evaluation against a permit.
;; value is an exact rational; unit is a symbol; sample-date is "YYYY-MM-DD".
(struct sample-rec (id outfall parameter value unit sample-date non-detect?) #:transparent)

;; Evidence trace for one substantive limit clause.
(struct trace
  (outfall parameter clause sample-ids sample-values
           computed-value threshold comparison status reason)
  #:transparent)

;; Pipeline provenance / rejection entries.
(struct provenance-entry (step record-id before after note) #:transparent)
(struct rejection-entry (step record-id reason) #:transparent)
