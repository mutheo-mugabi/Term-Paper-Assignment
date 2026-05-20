"""
Bayesian Scoring Layer
======================
Implements the probabilistic goal recognition model from:
  Ramírez & Geffner, AAAI-10, equations 1–5.

The posterior is computed as:
    P(G|O) ∝ P(O|G) · P(G)

where the likelihood is defined via a Boltzmann distribution:
    P(O|G)  ∝ exp{-β · cost(G+O)}
    P(O~|G) ∝ exp{-β · cost(G+~O)}

and these are normalized so P(O|G) + P(O~|G) = 1 per hypothesis.

The key quantity is the cost difference:
    Δ(G, O) = cost(G+O) − cost(G+~O)

A smaller (or more negative) Δ means O is "cheaper" relative to ~O,
hence G better predicts O, and P(G|O) is higher.

Ambiguity: The paper does not specify β.  We default to β=1.0 and
provide a sweep function.  Values in [0.5, 5.0] are reasonable;
higher β makes the distribution peakier (more sensitive to cost diffs).

References: Equations 1–5 in the paper.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional

INFINITY = 1e7  # sentinel used by the planner when no plan is found


@dataclass
class GoalHypothesis:
    """Represents one candidate goal and its recognition results."""
    goal_atoms: List[str]          # PDDL atoms defining this goal
    prior: float = 1.0             # P(G) — uniform by default
    cost_compliant: float = INFINITY    # cost(G+O)
    cost_noncompliant: float = INFINITY # cost(G+~O)
    plan_time_compliant: float = 0.0
    plan_time_noncompliant: float = 0.0
    failed: bool = False           # True if either planner call failed
    is_true_goal: bool = False     # True if this is the hidden goal

    # Filled by scorer:
    delta: float = 0.0             # Δ(G, O)
    likelihood: float = 0.0        # P(O|G)
    posterior: float = 0.0         # P(G|O)

    @property
    def goal_str(self) -> str:
        return ', '.join(self.goal_atoms)


class BayesianScorer:
    """
    Computes posterior probabilities P(G|O) from planner costs.

    Parameters
    ----------
    beta : float
        The Boltzmann temperature parameter (β > 0).
        Higher β → distribution more concentrated on best goal.
        Lower β → more uniform distribution.
        Default: 1.0  (we investigate sensitivity in experiments).
    """

    def __init__(self, beta: float = 1.0):
        if beta <= 0:
            raise ValueError(f"β must be positive, got {beta}")
        self.beta = beta

    def score(self, hypotheses: List[GoalHypothesis]) -> List[GoalHypothesis]:
        """
        Given a list of GoalHypothesis objects (with costs filled in),
        compute delta, likelihood, and posterior for each.

        Implements:
            P(O|G)  ∝ exp{-β · cost(G+O)}       (Eq. 2)
            P(O~|G) ∝ exp{-β · cost(G+~O)}      (Eq. 3)
            normalize so P(O|G) + P(O~|G) = 1    (per-hypothesis)
            Δ(G,O) = cost(G+O) − cost(G+~O)     (Eq. 5)
            P(G|O) ∝ P(O|G) · P(G)              (Eq. 1)

        Returns the same list with posterior fields populated.
        """
        for hyp in hypotheses:
            hyp.delta = self._compute_delta(hyp)
            hyp.likelihood = self._compute_likelihood(hyp)

        # Normalise posteriors: P(G|O) = α · P(O|G) · P(G)
        raw = [hyp.likelihood * hyp.prior for hyp in hypotheses]
        total = sum(raw)

        if total < 1e-300:
            # All likelihoods essentially zero (all goals very expensive)
            # Fall back to uniform
            for hyp in hypotheses:
                hyp.posterior = 1.0 / len(hypotheses) if hypotheses else 0.0
        else:
            for hyp, r in zip(hypotheses, raw):
                hyp.posterior = r / total

        return hypotheses

    # ------------------------------------------------------------------
    def _compute_delta(self, hyp: GoalHypothesis) -> float:
        """Δ(G,O) = cost(G+O) − cost(G+~O)."""
        if hyp.failed:
            return 0.0
        c_o = hyp.cost_compliant
        c_no = hyp.cost_noncompliant
        # If either is infinite, treat conservatively
        if c_o >= INFINITY and c_no >= INFINITY:
            return 0.0
        if c_o >= INFINITY:
            return INFINITY      # O is infinitely expensive: very unlikely
        if c_no >= INFINITY:
            return -INFINITY     # ~O is infinitely expensive: O is certain
        return c_o - c_no

    # ------------------------------------------------------------------
    def _compute_likelihood(self, hyp: GoalHypothesis) -> float:
        """
        Compute P(O|G) via Boltzmann distribution (Eq. 2–3).

        P(O|G)  = exp{-β·c_O}  / (exp{-β·c_O} + exp{-β·c_~O})

        Using the log-sum-exp trick for numerical stability:
        P(O|G) = 1 / (1 + exp{-β·(c_~O - c_O)})
               = 1 / (1 + exp{β·Δ})
        """
        if hyp.failed:
            return 0.0

        c_o = hyp.cost_compliant
        c_no = hyp.cost_noncompliant

        # Handle infinities
        if c_o >= INFINITY and c_no >= INFINITY:
            return 0.5  # equal penalty
        if c_o >= INFINITY:
            return 0.0   # complying with O is impossible → O very unlikely
        if c_no >= INFINITY:
            return 1.0   # not complying is impossible → O certain

        delta = c_o - c_no   # = Δ(G, O)

        # Numerically stable sigmoid
        # P(O|G) = exp(-β·c_O) / (exp(-β·c_O) + exp(-β·c_~O))
        #        = 1 / (1 + exp(β · (c_O - c_~O)))
        #        = 1 / (1 + exp(β · Δ))
        try:
            val = 1.0 / (1.0 + math.exp(self.beta * delta))
        except OverflowError:
            val = 0.0 if delta > 0 else 1.0
        return val


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(hypotheses: List[GoalHypothesis]):
    """
    Compute Q (quality) and S (spread) metrics as defined in the paper.

    Q = 1 if the true goal is among the most-likely goals, else 0.
    S = number of goals tied for highest posterior.

    Returns (Q, S, best_posterior, true_goal_posterior)
    """
    if not hypotheses:
        return 0, 0, 0.0, 0.0

    max_post = max(h.posterior for h in hypotheses)
    most_likely = [h for h in hypotheses if abs(h.posterior - max_post) < 1e-9]

    true_hyps = [h for h in hypotheses if h.is_true_goal]
    if not true_hyps:
        return 0, len(most_likely), max_post, 0.0

    true_post = true_hyps[0].posterior
    Q = 1 if any(h.is_true_goal for h in most_likely) else 0
    S = len(most_likely)
    return Q, S, max_post, true_post


def get_ranked_goals(hypotheses: List[GoalHypothesis]) -> List[GoalHypothesis]:
    """Return hypotheses sorted by posterior (descending)."""
    return sorted(hypotheses, key=lambda h: h.posterior, reverse=True)
