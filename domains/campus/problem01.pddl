; Campus Problem Instance 1
; Student may be: attending-class or going-to-library

(define (problem campus-01)
  (:domain campus)
  (:objects
    dorm cafeteria building-a building-b library gym - location
    attending-class going-to-library - activity
  )
  (:init
    (at dorm)
    (connected dorm cafeteria) (connected cafeteria dorm)
    (connected cafeteria building-a) (connected building-a cafeteria)
    (connected cafeteria building-b) (connected building-b cafeteria)
    (connected building-a library) (connected library building-a)
    (connected building-b gym) (connected gym building-b)
    (connected dorm building-a) (connected building-a dorm)
    (connected dorm library) (connected library dorm)
  )
  ; Goal: attending-class
  (:goal (activity-done attending-class))
)
