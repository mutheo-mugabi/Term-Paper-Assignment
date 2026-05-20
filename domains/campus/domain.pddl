; Campus Domain
; Tracks a student's activity by observing location changes.
; Based on Bui et al. (2008) plan library, converted to STRIPS.
; Only location-change actions are observable; top-level goal inferred.
; Per paper: |G|=2, 11 activities/locations, 132 STRIPS actions.
; Simplified version with key structure preserved.

(define (domain campus)
  (:requirements :strips :typing :negative-preconditions)

  (:types location activity)

  (:predicates
    (at ?l - location)
    (visited ?l - location)
    (activity-started ?a - activity)
    (activity-done ?a - activity)
    (connected ?l1 ?l2 - location)
  )

  ; Observable: move between connected locations
  (:action move
    :parameters (?from - location ?to - location)
    :precondition (and (at ?from) (connected ?from ?to))
    :effect (and (not (at ?from)) (at ?to) (visited ?to))
  )

  ; Non-observable: start an activity at a location
  (:action start-activity
    :parameters (?a - activity ?l - location)
    :precondition (and (at ?l) (visited ?l))
    :effect (activity-started ?a)
  )

  ; Non-observable: complete an activity
  (:action complete-activity
    :parameters (?a - activity)
    :precondition (activity-started ?a)
    :effect (activity-done ?a)
  )
)
