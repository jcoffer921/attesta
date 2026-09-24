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
(struct step:non-detect (marker treat-as) #:transparent)
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
;; An omitted or misspelled treat-as is a macro-expansion-time error.
(define-syntax (non-detect stx)
  (syntax-case stx (marker treat-as)
    [(_ (marker m) (treat-as t))
     (memq (syntax-e #'t) '(zero half-mdl report-limit))
     #'(step:non-detect m 't)]
    [(_ (marker m) (treat-as t))
     (raise-syntax-error 'non-detect
                          "treat-as must be exactly one of: zero, half-mdl, report-limit (no default is provided)"
                          stx #'t)]
    [(_ . _rest)
     (raise-syntax-error 'non-detect
                          "expected (non-detect (marker \"<\") (treat-as zero|half-mdl|report-limit))"
                          stx)]))

(define-syntax (require-field stx)
  (syntax-case stx ()
    [(_ field ...)
     #'(step:require-field (list 'field ...))]))
