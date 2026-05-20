; Kitchen Domain - Flat predicates, no types, compatible with Fast Downward

(define (domain kitchen)
  (:requirements :strips :negative-preconditions)

  (:predicates
    (has-bread) (has-cereal) (has-milk) (has-eggs)
    (has-coffee) (has-lettuce) (has-tomato)
    (has-pasta) (has-sauce) (has-soup) (has-cheese)
    (toaster-on) (coffee-on) (stove-on) (microwave-on)
    (breakfast-done) (lunch-done) (dinner-done)
  )

  ; === Observable take actions ===
  (:action take-bread
    :parameters ()
    :precondition (has-bread)
    :effect (and (not (has-bread)) (toaster-on))
  )
  (:action take-cereal
    :parameters ()
    :precondition (and (has-cereal) (has-milk))
    :effect (and (not (has-cereal)) (not (has-milk)))
  )
  (:action take-eggs
    :parameters ()
    :precondition (has-eggs)
    :effect (and (not (has-eggs)) (stove-on))
  )
  (:action take-coffee
    :parameters ()
    :precondition (has-coffee)
    :effect (and (not (has-coffee)) (coffee-on))
  )
  (:action take-vegetables
    :parameters ()
    :precondition (and (has-lettuce) (has-tomato))
    :effect (and (not (has-lettuce)) (not (has-tomato)))
  )
  (:action take-pasta
    :parameters ()
    :precondition (and (has-pasta) (has-sauce))
    :effect (and (not (has-pasta)) (not (has-sauce)) (stove-on))
  )
  (:action take-soup
    :parameters ()
    :precondition (has-soup)
    :effect (and (not (has-soup)) (microwave-on))
  )
  (:action take-sandwich-items
    :parameters ()
    :precondition (and (has-bread) (has-cheese))
    :effect (and (not (has-bread)) (not (has-cheese)))
  )

  ; === Observable use actions ===
  (:action use-toaster
    :parameters ()
    :precondition (toaster-on)
    :effect (toaster-on)
  )
  (:action use-coffee-maker
    :parameters ()
    :precondition (coffee-on)
    :effect (coffee-on)
  )
  (:action use-stove
    :parameters ()
    :precondition (stove-on)
    :effect (stove-on)
  )
  (:action use-microwave
    :parameters ()
    :precondition (microwave-on)
    :effect (microwave-on)
  )

  ; === Non-observable complete-meal actions ===
  (:action make-breakfast-toast
    :parameters ()
    :precondition (and (toaster-on) (coffee-on))
    :effect (breakfast-done)
  )
  (:action make-breakfast-cereal
    :parameters ()
    :precondition (and (not (has-cereal)) (not (has-milk)))
    :effect (breakfast-done)
  )
  (:action make-lunch
    :parameters ()
    :precondition (and (not (has-bread)) (not (has-cheese)) (microwave-on))
    :effect (lunch-done)
  )
  (:action make-dinner
    :parameters ()
    :precondition (and (stove-on) (not (has-lettuce)))
    :effect (dinner-done)
  )
)
