#lang racket/base
;; Boundary between Racket structs and jsexpr (JSON). All field names here
;; mirror the CLI's JSON contract exactly (snake_case).

(provide record->sample-rec
         trace->jsexpr
         provenance-entry->jsexpr
         rejection-entry->jsexpr
         permit->jsexpr
         error-jsexpr)

(require "common.rkt"
         "permit/lang.rkt")

;; record->sample-rec : jsexpr-hash -> sample-rec
;; Converts a fully pipeline-normalized record into the struct the evaluator
;; consumes. Assumes the record already carries: id, outfall, parameter,
;; value, unit, sample_date, non_detect.
(define (record->sample-rec rec)
  (sample-rec (hash-ref rec 'id)
              (hash-ref rec 'outfall)
              (hash-ref rec 'parameter)
              (parse-exact-decimal (hash-ref rec 'value))
              (string->symbol (hash-ref rec 'unit))
              (hash-ref rec 'sample_date)
              (hash-ref rec 'non_detect #f)))

(define (trace->jsexpr t)
  (hasheq 'outfall (trace-outfall t)
          'parameter (trace-parameter t)
          'clause (trace-clause t)
          'sample_ids (trace-sample-ids t)
          'sample_values (trace-sample-values t)
          'computed_value (trace-computed-value t)
          'threshold (trace-threshold t)
          'comparison (trace-comparison t)
          'status (symbol->string (trace-status t))
          'reason (trace-reason t)))

(define (provenance-entry->jsexpr p)
  (hasheq 'step (provenance-entry-step p)
          'record_id (provenance-entry-record-id p)
          'before (provenance-entry-before p)
          'after (provenance-entry-after p)
          'note (provenance-entry-note p)))

(define (rejection-entry->jsexpr r)
  (hasheq 'step (rejection-entry-step r)
          'record_id (rejection-entry-record-id r)
          'reason (rejection-entry-reason r)))

;; permit->jsexpr : permit-def -> jsexpr
;; Used by `describe` so other layers never have to parse s-expressions.
(define (permit->jsexpr pdef)
  (hasheq 'permit_id (permit-def-id pdef)
          'outfalls
          (for/list ([od (permit-def-outfalls pdef)])
            (hasheq 'outfall (outfall-def-number od)
                    'limits
                    (for/list ([ld (outfall-def-limits od)])
                      (hasheq 'parameter (limit-def-parameter ld)
                              'clauses (map clause->jsexpr (limit-def-clauses ld))))))))

(define (clause->jsexpr c)
  (cond
    [(clause:monthly-avg? c)
     (hasheq 'type "monthly-avg"
             'threshold (number->string (clause:monthly-avg-threshold c))
             'unit (symbol->string (clause:monthly-avg-unit c)))]
    [(clause:daily-max? c)
     (hasheq 'type "daily-max"
             'threshold (number->string (clause:daily-max-threshold c))
             'unit (symbol->string (clause:daily-max-unit c)))]
    [(clause:range? c)
     (hasheq 'type "range"
             'min (number->string (clause:range-min c))
             'max (number->string (clause:range-max c))
             'unit (symbol->string (clause:range-unit c)))]
    [(clause:sample-freq? c)
     (hasheq 'type "sample"
             'count (clause:sample-freq-count c)
             'period (symbol->string (clause:sample-freq-period c)))]
    [(clause:report-only? c)
     (hasheq 'type "report-only")]))

(define (error-jsexpr code message)
  (hasheq 'error (hasheq 'code code 'message message)))
