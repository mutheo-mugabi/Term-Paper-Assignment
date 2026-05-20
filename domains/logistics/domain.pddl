; Logistics Domain
; Carrying packages among locations using planes and trucks.
; Based on Ramirez & Geffner (AAAI-10): 6 packages, 1-2 trucks per city, 1 plane.

(define (domain logistics)
  (:requirements :strips :typing :negative-preconditions)

  (:types
    location city - object
    vehicle - object
    truck airplane - vehicle
    package - object
  )

  (:predicates
    (in-city ?l - location ?c - city)
    (at-vehicle ?v - vehicle ?l - location)
    (at-package ?p - package ?l - location)
    (in-vehicle ?p - package ?v - vehicle)
    (is-airport ?l - location)
  )

  (:action load-truck
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (at-package ?p ?l) (at-vehicle ?t ?l))
    :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?t))
  )

  (:action unload-truck
    :parameters (?p - package ?t - truck ?l - location)
    :precondition (and (in-vehicle ?p ?t) (at-vehicle ?t ?l))
    :effect (and (at-package ?p ?l) (not (in-vehicle ?p ?t)))
  )

  (:action load-airplane
    :parameters (?p - package ?a - airplane ?l - location)
    :precondition (and (at-package ?p ?l) (at-vehicle ?a ?l) (is-airport ?l))
    :effect (and (not (at-package ?p ?l)) (in-vehicle ?p ?a))
  )

  (:action unload-airplane
    :parameters (?p - package ?a - airplane ?l - location)
    :precondition (and (in-vehicle ?p ?a) (at-vehicle ?a ?l) (is-airport ?l))
    :effect (and (at-package ?p ?l) (not (in-vehicle ?p ?a)))
  )

  (:action drive-truck
    :parameters (?t - truck ?from - location ?to - location ?c - city)
    :precondition (and (at-vehicle ?t ?from) (in-city ?from ?c) (in-city ?to ?c))
    :effect (and (not (at-vehicle ?t ?from)) (at-vehicle ?t ?to))
  )

  (:action fly-airplane
    :parameters (?a - airplane ?from - location ?to - location)
    :precondition (and (at-vehicle ?a ?from) (is-airport ?from) (is-airport ?to))
    :effect (and (not (at-vehicle ?a ?from)) (at-vehicle ?a ?to))
  )
)
