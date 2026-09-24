#lang racket/base
(require rackunit
         "../pipeline/lang.rkt")

(test-case "pipeline builds an ordered list of step structs"
  (define pd (pipeline "lab-csv-import"
               (map-column "Analyte" -> parameter)
               (convert-units ug/L -> mg/L)
               (non-detect (marker "<") (treat-as report-limit))
               (require-field sample_date method)))
  (check-equal? (pipeline-def-name pd) "lab-csv-import")
  (check-equal? (length (pipeline-def-steps pd)) 4))

(test-case "map-column captures the source string and target symbol"
  (define st (map-column "Analyte" -> parameter))
  (check-equal? (step:map-column-from st) "Analyte")
  (check-equal? (step:map-column-to st) 'parameter))

(test-case "convert-units captures both units as symbols"
  (define st (convert-units ug/L -> mg/L))
  (check-equal? (step:convert-units-from-unit st) 'ug/L)
  (check-equal? (step:convert-units-to-unit st) 'mg/L))

(test-case "require-field captures a list of field symbols"
  (define st (require-field sample_date method))
  (check-equal? (step:require-field-fields st) '(sample_date method)))

;; non-detect: each valid treat-as value must expand successfully.
(test-case "non-detect accepts each documented treat-as value"
  (check-equal? (step:non-detect-treat-as (non-detect (marker "<") (treat-as zero))) 'zero)
  (check-equal? (step:non-detect-treat-as (non-detect (marker "<") (treat-as half-mdl))) 'half-mdl)
  (check-equal? (step:non-detect-treat-as (non-detect (marker "<") (treat-as report-limit))) 'report-limit))

;; non-detect: there is no default -- an invalid or missing treat-as is a
;; macro-expansion-time syntax error, never a silent fallback.
(test-case "non-detect rejects an invalid treat-as at macro-expansion time"
  (check-exn exn:fail:syntax?
             (lambda () (expand #'(non-detect (marker "<") (treat-as bogus))))))
