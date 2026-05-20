"""
Evaluation Pipeline
===================
Replicates Table 1 from Ramirez & Geffner (AAAI-10).
"""

import os
import sys
import json
import time
import random
import statistics
import argparse
import itertools
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from planner import FastDownward, INFINITY
from scorer import GoalHypothesis, BayesianScorer, compute_metrics

OBS_PERCENTAGES = [10, 30, 50, 70, 100]
N_PROBLEMS = 15


# ---------------------------------------------------------------------------
# Write a problem file with a specific goal
# ---------------------------------------------------------------------------

def _write_true_goal_problem(problem_file: str,
                              goal_atoms: list,
                              tmpdir: str) -> str:
    """
    Write a PDDL problem file whose goal is exactly goal_atoms.
    Uses bracket-matching to replace the (:goal ...) block cleanly.
    """
    text = open(problem_file, encoding='utf-8', errors='replace').read()

    # Build the new goal string
    goal_str = '(:goal (and\n'
    for atom in goal_atoms:
        goal_str += f'      {atom}\n'
    goal_str += '    ))'

    # Find the (:goal ...) block using bracket matching
    lower = text.lower()
    idx = lower.find('(:goal')
    if idx == -1:
        raise ValueError(f"No (:goal ...) in {problem_file}")

    depth = 0
    end = idx
    for i in range(idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    new_text = text[:idx] + goal_str + text[end:]

    out_path = os.path.join(tmpdir, 'true_goal_problem.pddl')
    with open(out_path, 'w') as f:
        f.write(new_text)
    return out_path


# ---------------------------------------------------------------------------
# Observation generator
# ---------------------------------------------------------------------------

def generate_plan(domain_file: str, problem_file: str,
                  fd_path: str, mode: str = 'optimal',
                  time_limit: float = 60.0) -> list:
    """Solve a planning problem and return the plan as a list of action strings."""
    planner = FastDownward(fd_path=fd_path, mode=mode, time_limit=time_limit)
    result = planner.solve(domain_file, problem_file)
    return result.plan


def sample_observations(plan: list, percentage: int) -> list:
    """Sample a prefix of the plan at the given percentage."""
    n = max(1, int(len(plan) * percentage / 100))
    return plan[:n]


# ---------------------------------------------------------------------------
# Single PR problem runner
# ---------------------------------------------------------------------------

def run_pr_problem(domain_file, problem_file, goals, observations,
                   true_goal_idx, beta, fd_path, planner_mode,
                   time_limit, workdir=None):
    """Run one PR problem and return result dict."""
    sys.path.insert(0, os.path.dirname(__file__))
    from recognize import recognize
    return recognize(
        domain_file=domain_file,
        problem_file=problem_file,
        goals=goals,
        observations=observations,
        true_goal_idx=true_goal_idx,
        beta=beta,
        fd_path=fd_path,
        planner_mode=planner_mode,
        time_limit=time_limit,
        verbose=False,
    )


# ---------------------------------------------------------------------------
# Domain experiment runner
# ---------------------------------------------------------------------------

def run_domain_experiment(domain_name, domain_config, fd_path,
                          planner_mode, beta=1.0, time_limit=300.0,
                          n_problems=N_PROBLEMS, seed=42):
    random.seed(seed)
    results_by_pct = {pct: [] for pct in OBS_PERCENTAGES}

    problems   = domain_config['problems']
    domain_file = domain_config['domain_file']
    use_suboptimal = domain_config.get('use_suboptimal', False)
    plan_mode  = 'greedy' if use_suboptimal else 'optimal'

    # Load goals for each problem
    def load_goals(goals_file):
        goals = []
        for line in open(goals_file, encoding='utf-8', errors='replace'):
            line = line.strip()
            if line and not line.startswith('#'):
                goals.append([a.strip() for a in line.split(',')])
        return goals

    # Build PR instances
    pr_instances = []
    rng_problems = list(itertools.islice(
        itertools.cycle(problems), n_problems))

    for prob_cfg in rng_problems:
        problem_file = prob_cfg['problem_file']
        goals_file   = prob_cfg.get('goals_file', '')
        goals        = prob_cfg.get('goals') or load_goals(goals_file)

        true_idx       = random.randint(0, len(goals) - 1)
        true_goal_atoms = goals[true_idx]

        # Write a temporary problem for the true goal and get its plan
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                true_prob = _write_true_goal_problem(
                    problem_file, true_goal_atoms, tmpdir)
                plan = generate_plan(domain_file, true_prob,
                                     fd_path, mode=plan_mode,
                                     time_limit=60.0)
            except Exception as e:
                print(f"    [WARN] Could not generate plan: {e}")
                plan = []

        if not plan:
            print(f"    [WARN] Could not generate plan for true goal in {problem_file}")

        pr_instances.append({
            'problem_file': problem_file,
            'goals': goals,
            'true_goal_idx': true_idx,
            'plan': plan,
            'plan_length': len(plan),
        })

    # Run recognition at each observation percentage
    for pct in OBS_PERCENTAGES:
        print(f"  [{domain_name}] obs={pct}% ...", flush=True)
        Qs, Ss, Ts, Ls = [], [], [], []

        for inst in pr_instances:
            plan = inst['plan']
            if not plan:
                Qs.append(0)
                Ss.append(len(inst['goals']))
                Ts.append(0.0)
                Ls.append(0)
                continue

            obs = sample_observations(plan, pct)
            Ls.append(len(plan))

            t0 = time.time()
            try:
                res = run_pr_problem(
                    domain_file=domain_file,
                    problem_file=inst['problem_file'],
                    goals=inst['goals'],
                    observations=obs,
                    true_goal_idx=inst['true_goal_idx'],
                    beta=beta,
                    fd_path=fd_path,
                    planner_mode=planner_mode,
                    time_limit=time_limit,
                    workdir=None,
                )
                Qs.append(res['Q'])
                Ss.append(res['S'])
                Ts.append(res['total_time'])
            except Exception as e:
                print(f"    [ERROR] {e}")
                Qs.append(0)
                Ss.append(len(inst['goals']))
                Ts.append(time.time() - t0)

        def _mean(lst): return statistics.mean(lst) if lst else 0.0
        def _std(lst):  return statistics.stdev(lst) if len(lst) > 1 else 0.0

        results_by_pct[pct] = {
            'Q_mean': _mean(Qs), 'Q_std': _std(Qs),
            'S_mean': _mean(Ss), 'S_std': _std(Ss),
            'T_mean': _mean(Ts), 'T_std': _std(Ts),
            'L_mean': _mean(Ls), 'n': len(Qs),
        }
        print(f"    Q={_mean(Qs):.3f}±{_std(Qs):.3f}  "
              f"S={_mean(Ss):.3f}±{_std(Ss):.3f}  "
              f"T={_mean(Ts):.1f}s")

    return results_by_pct


# ---------------------------------------------------------------------------
# Result table printer
# ---------------------------------------------------------------------------

def print_results_table(domain_name, results, planner_mode):
    print(f"\n{'='*70}")
    print(f"Domain: {domain_name.upper()}  (planner: {planner_mode})")
    print(f"{'='*70}")
    print(f"{'O%':>5} {'T(s)':>10} {'±':>6} {'Q':>6} {'±':>6} "
          f"{'S':>6} {'±':>6} {'L':>6}")
    print(f"{'-'*60}")
    for pct in OBS_PERCENTAGES:
        r = results.get(pct, {})
        print(f"{pct:>5} "
              f"{r.get('T_mean',0):>10.2f} "
              f"{r.get('T_std',0):>6.2f} "
              f"{r.get('Q_mean',0):>6.3f} "
              f"{r.get('Q_std',0):>6.3f} "
              f"{r.get('S_mean',0):>6.2f} "
              f"{r.get('S_std',0):>6.2f} "
              f"{r.get('L_mean',0):>6.1f}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',     required=True)
    parser.add_argument('--fd-path',    default='fast-downward.py')
    parser.add_argument('--mode',       default='optimal',
                        choices=['optimal','greedy','anytime'])
    parser.add_argument('--beta',       type=float, default=1.0)
    parser.add_argument('--time-limit', type=float, default=300.0)
    parser.add_argument('--n-problems', type=int,   default=N_PROBLEMS)
    parser.add_argument('--seed',       type=int,   default=42)
    parser.add_argument('--output',     default='results.json')
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    all_results = {}
    for domain_name, domain_config in config['domains'].items():
        print(f"\n{'='*60}\nRunning domain: {domain_name}")
        res = run_domain_experiment(
            domain_name=domain_name,
            domain_config=domain_config,
            fd_path=args.fd_path,
            planner_mode=args.mode,
            beta=args.beta,
            time_limit=args.time_limit,
            n_problems=args.n_problems,
            seed=args.seed,
        )
        all_results[domain_name] = res
        print_results_table(domain_name, res, args.mode)

    with open(args.output, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nFull results written to {args.output}")


if __name__ == '__main__':
    main()
