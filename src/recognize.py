"""
Probabilistic Plan Recognition Pipeline
========================================
Main entry point that glues together:
  1. PDDL compilation (compiler.py)
  2. Planner calls (planner.py)
  3. Bayesian scoring (scorer.py)

Usage
-----
    python recognize.py \
        --domain domains/blocks/domain.pddl \
        --problem domains/blocks/problem01.pddl \
        --goals domains/blocks/goals.txt \
        --obs domains/blocks/obs01.txt \
        --true-goal 3 \
        --beta 1.0 \
        --planner-mode optimal \
        --fd-path /path/to/fast-downward.py

goals.txt format:  one goal per line, atoms separated by commas
  (on a b),(on b c),(on c d)
  (on d e),(on e f),(on f a)

obs.txt format:  one action per line
  pick-up a
  put-down a
"""

import argparse
import os
import sys
import time
import json
import tempfile
import shutil

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from compiler import PDDLCompiler
from planner import FastDownward, INFINITY
from scorer import GoalHypothesis, BayesianScorer, compute_metrics, get_ranked_goals


def load_goals(goals_file: str):
    """Load candidate goals from file. Returns list of lists of atom strings."""
    goals = []
    with open(goals_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            atoms = [a.strip() for a in line.split(',')]
            goals.append(atoms)
    return goals


def load_observations(obs_file: str):
    """Load observation sequence from file. Returns list of action name strings."""
    obs = []
    with open(obs_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                obs.append(line.lower())
    return obs


def recognize(domain_file: str,
              problem_file: str,
              goals: list,
              observations: list,
              true_goal_idx: int = -1,
              beta: float = 1.0,
              fd_path: str = 'fast-downward.py',
              planner_mode: str = 'optimal',
              time_limit: float = 300.0,
              verbose: bool = True) -> dict:
    """
    Run the full probabilistic plan recognition pipeline.

    Parameters
    ----------
    domain_file     : path to original PDDL domain
    problem_file    : path to original PDDL problem
    goals           : list of goals, each a list of atom strings
    observations    : list of observed action names
    true_goal_idx   : index of the true (hidden) goal, -1 if unknown
    beta            : Boltzmann temperature parameter
    fd_path         : path to fast-downward.py
    planner_mode    : 'optimal', 'greedy', or 'anytime'
    time_limit      : total time limit in seconds (split across 2*|G| calls)
    verbose         : print progress

    Returns
    -------
    dict with keys:
        hypotheses, Q, S, total_time, metrics
    """
    if not observations:
        raise ValueError("Observation sequence is empty.")

    planner = FastDownward(fd_path=fd_path, mode=planner_mode,
                           time_limit=time_limit)
    scorer = BayesianScorer(beta=beta)

    hypotheses = []
    total_start = time.time()

    # Per-hypothesis time budget  (paper: split equally)
    per_hyp_limit = time_limit / max(len(goals), 1)

    with tempfile.TemporaryDirectory(prefix='pr_recog_') as workdir:
        compiler = PDDLCompiler(domain_file, problem_file, observations)

        for i, goal_atoms in enumerate(goals):
            hyp = GoalHypothesis(goal_atoms=goal_atoms)
            hyp.is_true_goal = (i == true_goal_idx)

            if verbose:
                print(f"  Goal {i+1}/{len(goals)}: {hyp.goal_str}")

            # Compile the modified domain + two problem variants
            hyp_dir = os.path.join(workdir, f'hyp_{i}')
            try:
                paths = compiler.compile(hyp_dir, goal_atoms)
            except Exception as e:
                if verbose:
                    print(f"    [COMPILE ERROR] {e}")
                hyp.failed = True
                hypotheses.append(hyp)
                continue

            # Solve compliant problem  (G+O)
            t0 = time.time()
            r_comp = planner.solve(paths['domain'], paths['compliant'])
            hyp.cost_compliant = r_comp.cost
            hyp.plan_time_compliant = time.time() - t0

            if verbose:
                print(f"    cost(G+O)  = {r_comp.cost:.1f}  [{hyp.plan_time_compliant:.2f}s]")

            # Solve noncompliant problem  (G+~O)
            t0 = time.time()
            r_nonc = planner.solve(paths['domain'], paths['noncompliant'])
            hyp.cost_noncompliant = r_nonc.cost
            hyp.plan_time_noncompliant = time.time() - t0

            if verbose:
                print(f"    cost(G+~O) = {r_nonc.cost:.1f}  [{hyp.plan_time_noncompliant:.2f}s]")

            if r_comp.cost >= INFINITY and r_nonc.cost >= INFINITY:
                hyp.failed = True

            hypotheses.append(hyp)

    # Bayesian scoring
    scorer.score(hypotheses)

    total_time = time.time() - total_start
    Q, S, max_post, true_post = compute_metrics(hypotheses)

    if verbose:
        print(f"\n--- Results (β={beta}, mode={planner_mode}) ---")
        ranked = get_ranked_goals(hypotheses)
        for h in ranked:
            marker = " ← TRUE" if h.is_true_goal else ""
            print(f"  P={h.posterior:.4f}  Δ={h.delta:.2f}  "
                  f"[{h.goal_str}]{marker}")
        print(f"  Q={Q}  S={S}  time={total_time:.1f}s")

    return {
        'hypotheses': hypotheses,
        'Q': Q,
        'S': S,
        'total_time': total_time,
        'beta': beta,
        'mode': planner_mode,
        'n_goals': len(goals),
        'n_obs': len(observations),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Probabilistic Plan Recognition (Ramírez & Geffner, AAAI-10)')
    parser.add_argument('--domain',   required=True, help='PDDL domain file')
    parser.add_argument('--problem',  required=True, help='PDDL problem file')
    parser.add_argument('--goals',    required=True, help='Goals file (one per line)')
    parser.add_argument('--obs',      required=True, help='Observations file (one action per line)')
    parser.add_argument('--true-goal', type=int, default=-1,
                        help='0-indexed true goal (for evaluation)')
    parser.add_argument('--beta',     type=float, default=1.0, help='β parameter')
    parser.add_argument('--fd-path',  default='fast-downward.py',
                        help='Path to fast-downward.py')
    parser.add_argument('--mode',     default='optimal',
                        choices=['optimal', 'greedy', 'anytime'],
                        help='Planner mode')
    parser.add_argument('--time-limit', type=float, default=300.0,
                        help='Total time limit in seconds')
    parser.add_argument('--output', default=None,
                        help='JSON output file for results')
    args = parser.parse_args()

    goals = load_goals(args.goals)
    obs   = load_observations(args.obs)

    print(f"Loaded {len(goals)} goals, {len(obs)} observations")
    print(f"Planner mode: {args.mode}, β={args.beta}")

    result = recognize(
        domain_file=args.domain,
        problem_file=args.problem,
        goals=goals,
        observations=obs,
        true_goal_idx=args.true_goal,
        beta=args.beta,
        fd_path=args.fd_path,
        planner_mode=args.mode,
        time_limit=args.time_limit,
        verbose=True,
    )

    if args.output:
        # Serialise (hypotheses contain non-serialisable objects)
        out = {k: v for k, v in result.items() if k != 'hypotheses'}
        out['hypotheses'] = [
            {
                'goal': h.goal_str,
                'cost_compliant': h.cost_compliant,
                'cost_noncompliant': h.cost_noncompliant,
                'delta': h.delta,
                'likelihood': h.likelihood,
                'posterior': h.posterior,
                'is_true_goal': h.is_true_goal,
            }
            for h in result['hypotheses']
        ]
        with open(args.output, 'w') as f:
            json.dump(out, f, indent=2)
        print(f"\nResults written to {args.output}")


if __name__ == '__main__':
    main()
