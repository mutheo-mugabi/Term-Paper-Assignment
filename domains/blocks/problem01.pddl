; Block Words Problem Instance 1
; 6 blocks: a, b, c, d, e, f (representing letters A-F)
; Initial state: blocks in a random arrangement on the table
; 20 candidate goals represent 20 different words/orderings

(define (problem blocks-problem-01)
  (:domain block-words)
  (:objects a b c d e f - block)

  (:init
    ; Random initial arrangement: all blocks on table, all clear
    (ontable a) (clear a)
    (ontable b) (clear b)
    (ontable c) (clear c)
    (ontable d) (clear d)
    (ontable e) (clear e)
    (ontable f) (clear f)
    (handempty)
  )

  ; Goal: spell word ABCDEF (a on b, b on c, c on d, d on e, e on f, f on table)
  (:goal
    (and
      (on a b)
      (on b c)
      (on c d)
      (on d e)
      (on e f)
      (ontable f)
    )
  )
)
