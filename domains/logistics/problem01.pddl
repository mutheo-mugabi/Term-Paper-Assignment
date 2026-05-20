; Logistics Problem Instance 1
; 2 cities (A, B), 6 packages, 1 truck each city, 1 airplane
; |G|=10: each goal specifies destination for some/all packages

(define (problem logistics-01)
  (:domain logistics)
  (:objects
    city-a city-b - city
    loc-a1 loc-a2 airport-a - location
    loc-b1 loc-b2 airport-b - location
    truck-a - truck
    truck-b - truck
    plane - airplane
    p1 p2 p3 p4 p5 p6 - package
  )
  (:init
    (in-city loc-a1 city-a) (in-city loc-a2 city-a) (in-city airport-a city-a)
    (in-city loc-b1 city-b) (in-city loc-b2 city-b) (in-city airport-b city-b)
    (is-airport airport-a) (is-airport airport-b)
    (at-vehicle truck-a loc-a1)
    (at-vehicle truck-b loc-b1)
    (at-vehicle plane airport-a)
    (at-package p1 loc-a1)
    (at-package p2 loc-a1)
    (at-package p3 loc-a2)
    (at-package p4 loc-b1)
    (at-package p5 loc-b1)
    (at-package p6 loc-b2)
  )
  ; Goal 1: all packages to city-b locations
  (:goal
    (and
      (at-package p1 loc-b1)
      (at-package p2 loc-b2)
      (at-package p3 loc-b1)
      (at-package p4 loc-a1)
      (at-package p5 loc-a2)
      (at-package p6 loc-a1)
    )
  )
)
