; IPC-Grid Problem Instance 1
; 3x3 grid, 2 keys, some locked cells
; Agent starts at l11 (top-left), goals involve placing keys at target locations

(define (problem ipc-grid-problem-01)
  (:domain ipc-grid)
  (:objects
    l11 l12 l13
    l21 l22 l23
    l31 l32 l33 - location
    k1 k2 - key
  )

  (:init
    ; Agent starts at top-left
    (at-agent l11)
    (handempty)

    ; Keys at specific locations
    (at-key k1 l13)
    (at-key k2 l31)

    ; Grid connectivity (bidirectional)
    (connected l11 l12) (connected l12 l11)
    (connected l12 l13) (connected l13 l12)
    (connected l21 l22) (connected l22 l21)
    (connected l22 l23) (connected l23 l22)
    (connected l31 l32) (connected l32 l31)
    (connected l32 l33) (connected l33 l32)
    (connected l11 l21) (connected l21 l11)
    (connected l12 l22) (connected l22 l12)
    (connected l13 l23) (connected l23 l13)
    (connected l21 l31) (connected l31 l21)
    (connected l22 l32) (connected l32 l22)
    (connected l23 l33) (connected l33 l23)

    ; l22 is locked; k1 opens it
    (locked l22)
    (open l22 k1)
  )

  ; Goal: k1 at l33, k2 at l13
  (:goal
    (and
      (at-key k1 l33)
      (at-key k2 l13)
    )
  )
)
