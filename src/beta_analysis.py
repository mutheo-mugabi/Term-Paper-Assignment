"""
Beta Sensitivity Analysis
=========================
Extension for group-of-3 requirement: investigate the effect of β on
recognition quality across domains.

The paper does not specify β; this is a key ambiguity we investigate.
We sweep β ∈ {0.1, 0.5, 1.0, 2.0, 5.0, 10.0} and report Q and S
for each domain at 50% observations.

Additionally we plot P(G|O) as a function of β to show how the
distribution sharpens.
"""

import os
import sys
import json
import math
import argparse
import statistics
import itertools
import random
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from scorer import GoalHypothesis, BayesianScorer, compute_metrics, INFINITY

BETA_VALUES = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
DEFAULT_OBS_PCT = 50


def sweep_beta_on_results(results_with_costs: list,
                           betas: list = None) -> dict:
    """
    Given a list of dicts {cost_compliant, cost_noncompliant, is_true_goal, prior}
    per hypothesis (one PR problem), sweep beta values and compute metrics.

    Parameters
    ----------
    results_with_costs : list of lists
        Each element is a list of hypothesis dicts for one PR problem.
    betas : list of float
        Beta values to sweep.

    Returns
    -------
    dict: {beta: {'Q_mean', 'Q_std', 'S_mean', 'S_std'}}
    """
    if betas is None:
        betas = BETA_VALUES

    output = {}
    for beta in betas:
        scorer = BayesianScorer(beta=beta)
        Qs, Ss = [], []

        for hyp_dicts in results_with_costs:
            hyps = []
            for d in hyp_dicts:
                h = GoalHypothesis(
                    goal_atoms=[d.get('goal', 'unknown')],
                    prior=d.get('prior', 1.0),
                    cost_compliant=d.get('cost_compliant', INFINITY),
                    cost_noncompliant=d.get('cost_noncompliant', INFINITY),
                    is_true_goal=d.get('is_true_goal', False),
                    failed=d.get('failed', False),
                )
                hyps.append(h)

            scorer.score(hyps)
            Q, S, _, _ = compute_metrics(hyps)
            Qs.append(Q)
            Ss.append(S)

        output[beta] = {
            'Q_mean': statistics.mean(Qs) if Qs else 0,
            'Q_std':  statistics.stdev(Qs) if len(Qs) > 1 else 0,
            'S_mean': statistics.mean(Ss) if Ss else 0,
            'S_std':  statistics.stdev(Ss) if len(Ss) > 1 else 0,
        }

    return output


def analyse_beta_from_run_results(run_results_file: str,
                                   output_file: str,
                                   betas: list = None):
    """
    Load raw costs from a previous evaluation run (saved with --save-costs flag)
    and re-score at different beta values.
    """
    if betas is None:
        betas = BETA_VALUES

    with open(run_results_file) as f:
        data = json.load(f)

    all_output = {}
    for domain_name, pct_data in data.items():
        # Use 50% observation level
        hyp_lists = pct_data.get('50', {}).get('raw_hypotheses', [])
        if not hyp_lists:
            print(f"  [WARN] No raw hypothesis data for {domain_name} at 50%")
            continue

        sweep = sweep_beta_on_results(hyp_lists, betas)
        all_output[domain_name] = sweep

        print(f"\nDomain: {domain_name}")
        print(f"{'β':>8} {'Q_mean':>8} {'Q_std':>8} {'S_mean':>8} {'S_std':>8}")
        for b in sorted(sweep.keys()):
            r = sweep[b]
            print(f"{b:>8.1f} {r['Q_mean']:>8.3f} {r['Q_std']:>8.3f} "
                  f"{r['S_mean']:>8.3f} {r['S_std']:>8.3f}")

    with open(output_file, 'w') as f:
        json.dump(all_output, f, indent=2)
    print(f"\nBeta sweep results saved to {output_file}")
    return all_output


def compute_theoretical_example():
    """
    Compute a synthetic example showing how β shapes the posterior.
    Uses two hypotheses with different cost differences to illustrate.
    """
    print("\n--- Theoretical β sensitivity example ---")
    print("Setup: 3 goals, costs:")
    print("  G1: c(G+O)=5, c(G+~O)=3  → Δ=+2 (bad predictor)")
    print("  G2: c(G+O)=4, c(G+~O)=8  → Δ=-4 (good predictor)")
    print("  G3: c(G+O)=6, c(G+~O)=6  → Δ= 0 (neutral)")
    print()

    hyp_configs = [
        {'cost_compliant': 5, 'cost_noncompliant': 3, 'is_true_goal': False, 'prior': 1.0, 'goal': 'G1', 'failed': False},
        {'cost_compliant': 4, 'cost_noncompliant': 8, 'is_true_goal': True,  'prior': 1.0, 'goal': 'G2', 'failed': False},
        {'cost_compliant': 6, 'cost_noncompliant': 6, 'is_true_goal': False, 'prior': 1.0, 'goal': 'G3', 'failed': False},
    ]

    print(f"{'β':>6} {'P(G1|O)':>10} {'P(G2|O)':>10} {'P(G3|O)':>10} {'Q':>4}")
    for beta in BETA_VALUES:
        scorer = BayesianScorer(beta=beta)
        hyps = [GoalHypothesis(
            goal_atoms=[d['goal']],
            prior=d['prior'],
            cost_compliant=d['cost_compliant'],
            cost_noncompliant=d['cost_noncompliant'],
            is_true_goal=d['is_true_goal'],
            failed=d['failed'],
        ) for d in hyp_configs]
        scorer.score(hyps)
        Q, S, _, _ = compute_metrics(hyps)
        posts = [h.posterior for h in hyps]
        print(f"{beta:>6.1f} {posts[0]:>10.4f} {posts[1]:>10.4f} "
              f"{posts[2]:>10.4f} {Q:>4}")

    return hyp_configs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Beta sensitivity analysis')
    parser.add_argument('--results', default=None,
                        help='Path to raw results JSON (with hypothesis costs)')
    parser.add_argument('--output', default='beta_sensitivity.json')
    parser.add_argument('--betas', nargs='+', type=float, default=BETA_VALUES)
    args = parser.parse_args()

    compute_theoretical_example()

    if args.results:
        analyse_beta_from_run_results(args.results, args.output, args.betas)
