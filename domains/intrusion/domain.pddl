; Intrusion Detection Domain
; Based on Geib & Goldman (2002) plan library, converted to STRIPS.
; A hacker may: gain-access, vandalize, or steal-information on servers.
; Actions encoded as STRIPS with library-graph edges as action preconditions.
; Per the paper: 9 actions per machine, up to 20 machines -> 180 actions total.
; This instance uses 3 servers with 9 actions each = 27 observable actions.

(define (domain intrusion-detection)
  (:requirements :strips :typing :negative-preconditions)

  (:types server)

  (:predicates
    ; Observable low-level actions (completed flags)
    (port-scanned ?s - server)
    (vuln-found ?s - server)
    (exploit-run ?s - server)
    (got-shell ?s - server)
    (priv-escalated ?s - server)
    (backdoor-installed ?s - server)
    (files-listed ?s - server)
    (data-downloaded ?s - server)
    (defaced ?s - server)

    ; High-level attack outcomes (goals)
    (access-gained ?s - server)
    (vandalized ?s - server)
    (info-stolen ?s - server)
  )

  ; --- Low-level observable actions (library graph edges as STRIPS actions) ---

  (:action do-port-scan
    :parameters (?s - server)
    :precondition (and)
    :effect (port-scanned ?s)
  )

  (:action do-find-vuln
    :parameters (?s - server)
    :precondition (port-scanned ?s)
    :effect (vuln-found ?s)
  )

  (:action do-run-exploit
    :parameters (?s - server)
    :precondition (vuln-found ?s)
    :effect (exploit-run ?s)
  )

  (:action do-get-shell
    :parameters (?s - server)
    :precondition (exploit-run ?s)
    :effect (got-shell ?s)
  )

  (:action do-escalate-privs
    :parameters (?s - server)
    :precondition (got-shell ?s)
    :effect (priv-escalated ?s)
  )

  (:action do-install-backdoor
    :parameters (?s - server)
    :precondition (priv-escalated ?s)
    :effect (backdoor-installed ?s)
  )

  (:action do-list-files
    :parameters (?s - server)
    :precondition (got-shell ?s)
    :effect (files-listed ?s)
  )

  (:action do-download-data
    :parameters (?s - server)
    :precondition (files-listed ?s)
    :effect (data-downloaded ?s)
  )

  (:action do-deface
    :parameters (?s - server)
    :precondition (priv-escalated ?s)
    :effect (defaced ?s)
  )

  ; --- High-level outcome actions (non-observable, encode goal achievement) ---

  (:action achieve-access
    :parameters (?s - server)
    :precondition (backdoor-installed ?s)
    :effect (access-gained ?s)
  )

  (:action achieve-vandalize
    :parameters (?s - server)
    :precondition (defaced ?s)
    :effect (vandalized ?s)
  )

  (:action achieve-steal-info
    :parameters (?s - server)
    :precondition (data-downloaded ?s)
    :effect (info-stolen ?s)
  )
)
