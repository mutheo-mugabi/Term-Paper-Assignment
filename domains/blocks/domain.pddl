; Block Words Domain
; Blocks World with 6 lettered blocks that must be stacked to spell a word.
; Based on Ramirez & Geffner (AAAI-10) Block Words domain.
; Each block has a letter; goal is to arrange blocks to spell a target word
; (i.e., a specific tower ordering).

(define (domain block-words)
  (:requirements :strips :typing :negative-preconditions)

  (:types block)

  (:predicates
    (on ?x - block ?y - block)     ; block x is directly on block y
    (ontable ?x - block)           ; block x is on the table
    (clear ?x - block)             ; nothing is on block x
    (holding ?x - block)           ; arm is holding block x
    (handempty)                    ; arm is not holding anything
  )

  (:action pick-up
    :parameters (?x - block)
    :precondition (and (clear ?x) (ontable ?x) (handempty))
    :effect (and (not (ontable ?x))
                 (not (clear ?x))
                 (not (handempty))
                 (holding ?x))
  )

  (:action put-down
    :parameters (?x - block)
    :precondition (holding ?x)
    :effect (and (not (holding ?x))
                 (clear ?x)
                 (handempty)
                 (ontable ?x))
  )

  (:action stack
    :parameters (?x - block ?y - block)
    :precondition (and (holding ?x) (clear ?y))
    :effect (and (not (holding ?x))
                 (not (clear ?y))
                 (clear ?x)
                 (handempty)
                 (on ?x ?y))
  )

  (:action unstack
    :parameters (?x - block ?y - block)
    :precondition (and (on ?x ?y) (clear ?x) (handempty))
    :effect (and (holding ?x)
                 (clear ?y)
                 (not (clear ?x))
                 (not (handempty))
                 (not (on ?x ?y)))
  )
)
