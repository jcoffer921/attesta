#lang racket/base
(require "../lang.rkt")

(provide the-pipeline)

(define the-pipeline
  (pipeline "lab-csv-import"
    (map-column "Analyte" -> parameter)
    (convert-units ug/L -> mg/L)
    (non-detect (marker "<") (treat-as report-limit))
    (require-field sample_date method)))
