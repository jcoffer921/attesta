#lang racket/base
;; Evidence Pipeline DSL: an ordered list of normalization steps applied to
;; raw lab records.
;;
;; Note on `require-field`: field names are written with underscores
;; (sample_date, not sample-date) so they match the snake_case field names
;; used in the JSON record schema shared with the evaluator (sample_date,
;; non_detect, ...) -- Racket symbols allow underscores, so this needs no
;; extra translation layer at the JSON boundary.

(provide pipeline map-column convert-units non-detect require-field
         (struct-out pipeline-def)
         (struct-out step:map-column)
         (struct-out step:convert-units)
         (struct-out step:non-detect)
         (struct-out step:require-field))

(require (for-syntax racket/base))

(struct pipeline-def (name steps) #:transparent)
(struct step:map-column (from to) #:transparent)
(struct step:convert-units (from-unit to-unit) #:transparent)
(struct step:non-detect (marker treat-as basis) #:transparent)
(struct step:require-field (fields) #:transparent)

(define-syntax (pipeline stx)
  (syntax-case stx ()
    [(_ name step-expr ...)
     #'(pipeline-def name (list step-expr ...))]))

(define-syntax (map-column stx)
  (syntax-case stx (->)
    [(_ from -> to)
     #'(step:map-column from 'to)]))

(define-syntax (convert-units stx)
  (syntax-case stx (->)
    [(_ from -> to)
     #'(step:convert-units 'from 'to)]))

;; non-detect requires an explicit, valid treat-as; there is no default.
;; `report-limit` (use the reporting limit, flag the value as a non-detect) is
;; the PA DEP convention. `zero` is only legitimate when the permit limit is
;; below the most sensitive detection limit, so it must carry a (basis "...")
;; citing why. An omitted, misspelled, or unjustified treat-as is a
;; macro-expansion-time error.
(define-syntax (non-detect stx)
  (syntax-case stx (marker treat-as basis report-limit zero)
    [(_ (marker m) (treat-as report-limit))
     #'(step:non-detect m 'report-limit #f)]
    [(_ (marker m) (treat-as zero) (basis b))
     (string? (syntax-e #'b))
     #'(step:non-detect m 'zero b)]
    [(_ (marker m) (treat-as zero))
     (raise-syntax-error 'non-detect
                          "treat-as zero requires (basis \"...\") citing why zero is permitted (e.g. permit limit below the most sensitive detection limit)"
                          stx)]
    [(_ (marker m) (treat-as t) . _rest)
     (raise-syntax-error 'non-detect
                          "treat-as must be report-limit, or zero with a (basis \"...\") (no default is provided)"
                          stx #'t)]
    [(_ . _rest)
     (raise-syntax-error 'non-detect
                          "expected (non-detect (marker \"<\") (treat-as report-limit)) or (non-detect (marker \"<\") (treat-as zero) (basis \"...\"))"
                          stx)]))

(define-syntax (require-field stx)
  (syntax-case stx ()
    [(_ field ...)
     #'(step:require-field (list 'field ...))]))
