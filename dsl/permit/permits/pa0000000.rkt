#lang racket/base
;; PLACEHOLDER PERMIT -- FICTIONAL, FOR SYNTAX/TEST PURPOSES ONLY.
;;
;; Permit number "PA0000000", outfall 001, and every limit value below are
;; invented to exercise the DSL syntax. None of it is derived from an actual
;; Pennsylvania NPDES/DMR permit. Verify against a real permit before this is
;; used for anything beyond testing the Permit Rules DSL.

(require "../lang.rkt")

(provide the-permit)

(define the-permit
  (permit "PA0000000"
    (outfall 001
      (limit "TSS"  (monthly-avg 30 mg/L) (daily-max 60 mg/L) (sample 2 per-month))
      (limit "pH"   (range #e6.0 #e9.0 s.u.) (sample 1 per-week))
      (limit "Flow" (monthly-avg #e0.5 MGD) (report-only)))))
