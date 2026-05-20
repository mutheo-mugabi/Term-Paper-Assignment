; Intrusion Detection Problem Instance 1
; 3 servers; hacker may attack any combination

(define (problem intrusion-01)
  (:domain intrusion-detection)
  (:objects s1 s2 s3 - server)
  (:init)
  ; Goal: gain access to s1
  (:goal (access-gained s1))
)
