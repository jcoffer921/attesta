#lang racket/base
(require rackunit
         "../pipeline/lang.rkt"
         "../pipeline/run.rkt"
         "../common.rkt")

(define (rec . kvs)
  (apply hasheq kvs))

;; --- map-column ---
(test-case "map-column renames the source column"
  (define pd (pipeline "p" (map-column "Analyte" -> parameter)))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'Analyte "TSS"))))
  (check-equal? (length finals) 1)
  (check-equal? (hash-ref (car finals) 'parameter) "TSS")
  (check-false (hash-has-key? (car finals) 'Analyte))
  (check-equal? (length prov) 1)
  (check-equal? (length rej) 0))

(test-case "map-column rejects (does not drop) a record missing the source column"
  (define pd (pipeline "p" (map-column "Analyte" -> parameter)))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'other "x"))))
  (check-equal? (length finals) 0)
  (check-equal? (length rej) 1)
  (check-equal? (rejection-entry-record-id (car rej)) "r1")
  (check-equal? (rejection-entry-step (car rej)) "map-column"))

;; --- convert-units ---
(test-case "convert-units converts ug/L to mg/L exactly"
  (define pd (pipeline "p" (convert-units ug/L -> mg/L)))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'value "1000" 'unit "ug/L"))))
  (check-equal? (hash-ref (car finals) 'value) "1")
  (check-equal? (hash-ref (car finals) 'unit) "mg/L"))

(test-case "convert-units leaves a non-matching unit unchanged (no auto-guessing)"
  (define pd (pipeline "p" (convert-units ug/L -> mg/L)))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'value "5" 'unit "mg/L"))))
  (check-equal? (hash-ref (car finals) 'value) "5")
  (check-equal? (hash-ref (car finals) 'unit) "mg/L"))

;; --- non-detect: each treat-as option ---
(test-case "non-detect treat-as zero"
  (define pd (pipeline "p" (non-detect (marker "<") (treat-as zero))))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'value "<5"))))
  (check-equal? (hash-ref (car finals) 'value) "0")
  (check-true (hash-ref (car finals) 'non_detect)))

(test-case "non-detect treat-as half-mdl"
  (define pd (pipeline "p" (non-detect (marker "<") (treat-as half-mdl))))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'value "<5"))))
  (check-equal? (hash-ref (car finals) 'value) "5/2")
  (check-true (hash-ref (car finals) 'non_detect)))

(test-case "non-detect treat-as report-limit"
  (define pd (pipeline "p" (non-detect (marker "<") (treat-as report-limit))))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'value "<5"))))
  (check-equal? (hash-ref (car finals) 'value) "5")
  (check-true (hash-ref (car finals) 'non_detect)))

(test-case "non-detect leaves a non-flagged value untouched but records non_detect: #f"
  (define pd (pipeline "p" (non-detect (marker "<") (treat-as zero))))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'value "5"))))
  (check-equal? (hash-ref (car finals) 'value) "5")
  (check-false (hash-ref (car finals) 'non_detect)))

;; --- require-field ---
(test-case "require-field passes when all fields are present and non-empty"
  (define pd (pipeline "p" (require-field sample_date method)))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'sample_date "2026-03-05" 'method "SM2540D"))))
  (check-equal? (length finals) 1)
  (check-equal? (length rej) 0))

(test-case "require-field rejects (does not drop) a record missing a required field"
  (define pd (pipeline "p" (require-field sample_date method)))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'sample_date "2026-03-05"))))
  (check-equal? (length finals) 0)
  (check-equal? (length rej) 1)
  (check-equal? (rejection-entry-record-id (car rej)) "r1"))

;; --- provenance: every applied step logs an entry, before rejection stops the chain ---
(test-case "a rejected record still produced provenance for the steps before the failure"
  (define pd (pipeline "p"
               (map-column "Analyte" -> parameter)
               (require-field sample_date method)))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'Analyte "TSS"))))
  (check-equal? (length finals) 0)
  (check-equal? (length rej) 1)
  ;; map-column succeeded and logged, require-field is what rejected it
  (check-equal? (length prov) 1)
  (check-equal? (provenance-entry-step (car prov)) "map-column"))

;; --- full pipeline end to end ---
(test-case "the full lab-csv-import pipeline runs a record end to end"
  (define pd (pipeline "lab-csv-import"
               (map-column "Analyte" -> parameter)
               (convert-units ug/L -> mg/L)
               (non-detect (marker "<") (treat-as report-limit))
               (require-field sample_date method)))
  (define-values (finals prov rej)
    (run-pipeline pd (list (rec 'id "r1" 'outfall 1 'Analyte "TSS" 'value "45" 'unit "ug/L"
                                'sample_date "2026-03-05" 'method "SM2540D"))))
  (check-equal? (length finals) 1)
  (define f (car finals))
  (check-equal? (hash-ref f 'parameter) "TSS")
  (check-equal? (hash-ref f 'value) "9/200")
  (check-equal? (hash-ref f 'unit) "mg/L")
  (check-false (hash-ref f 'non_detect))
  (check-equal? (length prov) 4)
  (check-equal? (length rej) 0))
