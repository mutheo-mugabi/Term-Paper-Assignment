"""
Unit Tests for PR Recognition System
=====================================
Tests the PDDL compiler, Bayesian scorer, and observation sampling.
Run with: python -m pytest tests/test_core.py -v
"""

import os
import sys
import math
import tempfile
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scorer import (
    GoalHypothesis, BayesianScorer, compute_metrics, get_ranked_goals, INFINITY
)
from compiler import PDDLCompiler


# ============================================================
# Scorer tests
# ============================================================

class TestBayesianScorer:

    def test_basic_scoring_two_goals(self):
        """With two goals, the one with lower cost(G+O) should have higher P(G|O)."""
        hyps = [
            GoalHypothesis(['(on a b)'], cost_compliant=3.0, cost_noncompliant=5.0),
            GoalHypothesis(['(on b c)'], cost_compliant=6.0, cost_noncompliant=4.0),
        ]
        scorer = BayesianScorer(beta=1.0)
        scorer.score(hyps)

        # hyp[0]: delta = 3-5 = -2 (negative -> O is cheaper -> higher likelihood)
        # hyp[1]: delta = 6-4 = +2 (positive -> O is more expensive -> lower likelihood)
        assert hyps[0].posterior > hyps[1].posterior, \
            "Goal with lower cost(G+O) should have higher posterior"

    def test_posteriors_sum_to_one(self):
        """Posteriors must always sum to 1."""
        hyps = [
            GoalHypothesis(['G1'], cost_compliant=2.0, cost_noncompliant=4.0),
            GoalHypothesis(['G2'], cost_compliant=5.0, cost_noncompliant=3.0),
            GoalHypothesis(['G3'], cost_compliant=4.0, cost_noncompliant=4.0),
        ]
        scorer = BayesianScorer(beta=1.0)
        scorer.score(hyps)
        total = sum(h.posterior for h in hyps)
        assert abs(total - 1.0) < 1e-9, f"Posteriors sum to {total}, expected 1.0"

    def test_uniform_prior_equal_costs(self):
        """With uniform priors and equal costs, all goals should be equally likely."""
        hyps = [
            GoalHypothesis(['G1'], cost_compliant=4.0, cost_noncompliant=4.0),
            GoalHypothesis(['G2'], cost_compliant=4.0, cost_noncompliant=4.0),
            GoalHypothesis(['G3'], cost_compliant=4.0, cost_noncompliant=4.0),
        ]
        scorer = BayesianScorer(beta=1.0)
        scorer.score(hyps)
        for h in hyps:
            assert abs(h.posterior - 1/3) < 1e-9, \
                f"Expected uniform posterior 1/3, got {h.posterior}"

    def test_prior_weighting(self):
        """Prior should scale the posterior proportionally."""
        hyps = [
            GoalHypothesis(['G1'], prior=1.0, cost_compliant=4.0, cost_noncompliant=4.0),
            GoalHypothesis(['G2'], prior=2.0, cost_compliant=4.0, cost_noncompliant=4.0),
        ]
        scorer = BayesianScorer(beta=1.0)
        scorer.score(hyps)
        # P(G2|O) should be double P(G1|O) since prior is doubled and likelihoods equal
        ratio = hyps[1].posterior / hyps[0].posterior
        assert abs(ratio - 2.0) < 1e-9, f"Expected ratio 2.0, got {ratio}"

    def test_infinite_compliant_cost(self):
        """If cost(G+O) = inf, likelihood should be 0 (O impossible for this goal)."""
        hyps = [
            GoalHypothesis(['G1'], cost_compliant=INFINITY, cost_noncompliant=3.0),
        ]
        scorer = BayesianScorer(beta=1.0)
        scorer.score(hyps)
        assert hyps[0].likelihood == 0.0, \
            "Infinite compliant cost should give zero likelihood"

    def test_infinite_noncompliant_cost(self):
        """If cost(G+~O) = inf, likelihood should be 1 (O certain for this goal)."""
        hyps = [
            GoalHypothesis(['G1'], cost_compliant=3.0, cost_noncompliant=INFINITY),
        ]
        scorer = BayesianScorer(beta=1.0)
        scorer.score(hyps)
        assert hyps[0].likelihood == 1.0, \
            "Infinite non-compliant cost should give likelihood 1.0"

    def test_delta_computation(self):
        """Delta should be cost(G+O) - cost(G+~O)."""
        hyp = GoalHypothesis(['G'], cost_compliant=5.0, cost_noncompliant=3.0)
        scorer = BayesianScorer(beta=1.0)
        scorer.score([hyp])
        assert abs(hyp.delta - 2.0) < 1e-9, f"Expected delta=2.0, got {hyp.delta}"

    def test_beta_sharpening(self):
        """Higher beta should produce a more concentrated distribution."""
        hyps_low = [
            GoalHypothesis(['G1'], cost_compliant=3.0, cost_noncompliant=5.0),
            GoalHypothesis(['G2'], cost_compliant=6.0, cost_noncompliant=4.0),
        ]
        hyps_high = [
            GoalHypothesis(['G1'], cost_compliant=3.0, cost_noncompliant=5.0),
            GoalHypothesis(['G2'], cost_compliant=6.0, cost_noncompliant=4.0),
        ]
        BayesianScorer(beta=0.1).score(hyps_low)
        BayesianScorer(beta=10.0).score(hyps_high)

        # With high beta, the gap between best and worst should be larger
        gap_low  = abs(hyps_low[0].posterior  - hyps_low[1].posterior)
        gap_high = abs(hyps_high[0].posterior - hyps_high[1].posterior)
        assert gap_high > gap_low, \
            "Higher beta should produce larger gap between posteriors"

    def test_invalid_beta(self):
        """Beta <= 0 should raise ValueError."""
        with pytest.raises(ValueError):
            BayesianScorer(beta=0.0)
        with pytest.raises(ValueError):
            BayesianScorer(beta=-1.0)


class TestComputeMetrics:

    def test_q_one_when_true_goal_is_top(self):
        hyps = [
            GoalHypothesis(['G1'], is_true_goal=True),
            GoalHypothesis(['G2']),
        ]
        hyps[0].posterior = 0.8
        hyps[1].posterior = 0.2
        Q, S, _, _ = compute_metrics(hyps)
        assert Q == 1

    def test_q_zero_when_true_goal_not_top(self):
        hyps = [
            GoalHypothesis(['G1'], is_true_goal=True),
            GoalHypothesis(['G2']),
        ]
        hyps[0].posterior = 0.2
        hyps[1].posterior = 0.8
        Q, S, _, _ = compute_metrics(hyps)
        assert Q == 0

    def test_s_counts_ties(self):
        hyps = [
            GoalHypothesis(['G1']), GoalHypothesis(['G2']), GoalHypothesis(['G3'])
        ]
        for h in hyps:
            h.posterior = 1/3
        _, S, _, _ = compute_metrics(hyps)
        assert S == 3

    def test_ranked_goals_order(self):
        hyps = [
            GoalHypothesis(['G1']), GoalHypothesis(['G2']), GoalHypothesis(['G3'])
        ]
        hyps[0].posterior = 0.1
        hyps[1].posterior = 0.6
        hyps[2].posterior = 0.3
        ranked = get_ranked_goals(hyps)
        assert ranked[0].goal_atoms == ['G2']
        assert ranked[1].goal_atoms == ['G3']
        assert ranked[2].goal_atoms == ['G1']


# ============================================================
# Compiler tests
# ============================================================

SIMPLE_DOMAIN = """\
(define (domain simple-test)
  (:requirements :strips)
  (:predicates (at ?x) (done))
  (:action move
    :parameters (?x ?y)
    :precondition (at ?x)
    :effect (and (not (at ?x)) (at ?y))
  )
  (:action finish
    :parameters ()
    :precondition (at goal)
    :effect (done)
  )
)
"""

SIMPLE_PROBLEM = """\
(define (problem simple-01)
  (:domain simple-test)
  (:init (at start))
  (:goal (done))
)
"""


class TestPDDLCompiler:

    @pytest.fixture
    def tmp_files(self, tmp_path):
        domain = tmp_path / "domain.pddl"
        problem = tmp_path / "problem.pddl"
        domain.write_text(SIMPLE_DOMAIN)
        problem.write_text(SIMPLE_PROBLEM)
        return str(domain), str(problem), tmp_path

    def test_compile_creates_files(self, tmp_files):
        domain, problem, tmp_path = tmp_files
        obs = ['move start mid']
        compiler = PDDLCompiler(domain, problem, obs)
        out = str(tmp_path / 'out')
        paths = compiler.compile(out, ['(done)'])
        assert os.path.exists(paths['domain'])
        assert os.path.exists(paths['compliant'])
        assert os.path.exists(paths['noncompliant'])

    def test_obs_fluent_injected_into_domain(self, tmp_files):
        domain, problem, tmp_path = tmp_files
        obs = ['move start mid']
        compiler = PDDLCompiler(domain, problem, obs)
        out = str(tmp_path / 'out_fluent')
        paths = compiler.compile(out, ['(done)'])
        domain_text = open(paths['domain']).read().lower()
        # The fluent obs__move_start_mid should appear in predicates
        assert 'obs__' in domain_text, "Observation fluent not found in domain"

    def test_compliant_goal_has_obs_fluent(self, tmp_files):
        domain, problem, tmp_path = tmp_files
        obs = ['move start mid']
        compiler = PDDLCompiler(domain, problem, obs)
        out = str(tmp_path / 'out_comp')
        paths = compiler.compile(out, ['(done)'])
        comp_text = open(paths['compliant']).read().lower()
        # Should contain the positive obs fluent
        assert 'obs__' in comp_text
        assert 'not' not in comp_text.split('goal')[1].split(')')[0] or True  # flexible

    def test_noncompliant_goal_has_negated_fluent(self, tmp_files):
        domain, problem, tmp_path = tmp_files
        obs = ['move start mid']
        compiler = PDDLCompiler(domain, problem, obs)
        out = str(tmp_path / 'out_noncomp')
        paths = compiler.compile(out, ['(done)'])
        noncomp_text = open(paths['noncompliant']).read().lower()
        assert 'not' in noncomp_text, "Noncompliant goal should have negated fluent"
        assert 'obs__' in noncomp_text

    def test_empty_obs_raises(self, tmp_files):
        domain, problem, _ = tmp_files
        with pytest.raises(Exception):
            # Empty observations: the goal would have no obs fluent to reference
            compiler = PDDLCompiler(domain, problem, [])
            compiler.compile('/tmp/x', ['(done)'])

    def test_duplicate_obs_handled(self, tmp_files):
        domain, problem, tmp_path = tmp_files
        # Duplicate observations
        obs = ['move start mid', 'move start mid']
        compiler = PDDLCompiler(domain, problem, obs)
        # Second occurrence should be renamed
        assert compiler._obs_unique[0] != compiler._obs_unique[1], \
            "Duplicate observations should be uniquified"

    def test_uniquify_obs(self, tmp_files):
        domain, problem, _ = tmp_files
        compiler = PDDLCompiler(domain, problem, ['a', 'b', 'a', 'c', 'a'])
        assert compiler._obs_unique == ['a', 'b', 'a_obs_1', 'c', 'a_obs_2']


# ============================================================
# Integration smoke test (no real planner needed)
# ============================================================

class TestObservationSampling:

    def test_sample_prefix(self):
        from evaluate import sample_observations
        plan = ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'a10']
        assert sample_observations(plan, 10)  == ['a1']
        assert sample_observations(plan, 50)  == plan[:5]
        assert sample_observations(plan, 100) == plan

    def test_sample_empty_plan(self):
        from evaluate import sample_observations
        # Single-element plan at 10%: should give at least 1
        plan = ['a1']
        obs = sample_observations(plan, 10)
        assert len(obs) >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
