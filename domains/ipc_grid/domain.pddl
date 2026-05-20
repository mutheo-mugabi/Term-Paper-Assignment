; IPC-Grid Domain (Easy version)
; Agent moves in a grid transporting keys between cells.
; Some cells are locked and require a key to enter.
; Based on Ramirez & Geffner (AAAI-10) IPC-GRID domain.

(define (domain ipc-grid)
  (:requirements :strips :typing :negative-preconditions)

  (:types location key)

  (:predicates
    (at-agent ?l - location)        ; agent is at location l
    (at-key ?k - key ?l - location) ; key k is at location l
    (carrying ?k - key)             ; agent carries key k
    (locked ?l - location)          ; location l is locked
    (open ?l - location ?k - key)   ; key k opens location l
    (connected ?l1 ?l2 - location)  ; l1 and l2 are adjacent
    (handempty)                     ; agent not carrying anything
  )

  ; Move between adjacent, unlocked locations
  (:action move
    :parameters (?from - location ?to - location)
    :precondition (and
      (at-agent ?from)
      (connected ?from ?to)
      (not (locked ?to))
    )
    :effect (and
      (not (at-agent ?from))
      (at-agent ?to)
    )
  )

  ; Move into locked location with the right key
  (:action move-with-key
    :parameters (?from - location ?to - location ?k - key)
    :precondition (and
      (at-agent ?from)
      (connected ?from ?to)
      (locked ?to)
      (open ?to ?k)
      (carrying ?k)
    )
    :effect (and
      (not (at-agent ?from))
      (at-agent ?to)
    )
  )

  ; Pick up a key
  (:action pick-up-key
    :parameters (?k - key ?l - location)
    :precondition (and
      (at-agent ?l)
      (at-key ?k ?l)
      (handempty)
    )
    :effect (and
      (not (at-key ?k ?l))
      (not (handempty))
      (carrying ?k)
    )
  )

  ; Put down a key
  (:action put-down-key
    :parameters (?k - key ?l - location)
    :precondition (and
      (at-agent ?l)
      (carrying ?k)
    )
    :effect (and
      (at-key ?k ?l)
      (handempty)
      (not (carrying ?k))
    )
  )
)
