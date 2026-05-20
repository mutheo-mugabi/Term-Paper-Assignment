#!/usr/bin/env python3
"""
run_experiments.py
==================
Master experiment runner for the AAAI-10 reproducibility study.

Runs all three planner configurations (optimal, greedy, anytime) across
all six domains, saves raw results, generates plots and LaTeX tables.

Usage:
    python run_experiments.py --fd-path /path/to/fast-downward.py
    python run_experiments.py --fd-path fast-downward.py --modes optimal greedy
    python run_experiments.py --quick   # Fast smoke-test with 3 problems

Results are saved to results/<timestamp>/ and summary tables printed.
"""

import os
import sys
import json
import time
import argparse
import datetime
import statistics
import subprocess

# Ensure src/ is on the path
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, 'src')
sys.path.insert(0, SRC)

from evaluate import (
    run_domain_experiment, print_results_table,
    OBS_PERCENTAGES, N_PROBLEMS
)
from beta_analysis import sweep_beta_on_results, BETA_VALUES, compute_theoretical_example
from plot_results import (
    plot_q_comparison, plot_s_comparison,
    plot_beta_sensitivity, generate_latex_table,
    PAPER_OPTIMAL, PAPER_GREEDY, DOMAINS
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_domain_configs(config_path: str, fd_path: str) -> dict:
    """Load and resolve domain configurations."""
    with open(config_path) as f:
        raw = json.load(f)

    configs = {}
    base = os.path.dirname(config_path)

    for domain_name, dc in raw['domains'].items():
        cfg = dict(dc)
        cfg['domain_file'] = os.path.join(ROOT, dc['domain_file'])

        resolved_problems = []
        for prob in dc.get('problems', []):
            goals_file = prob.get('goals_file', dc.get('goals_file', ''))
            goals = load_goals(os.path.join(ROOT, goals_file))
            resolved_problems.append({
                'problem_file': os.path.join(ROOT, prob['problem_file']),
                'goals': goals,
            })
        cfg['problems'] = resolved_problems
        configs[domain_name] = cfg

    return configs, raw.get('evaluation', {})


def load_goals(goals_file: str) -> list:
    """Load goals from file (skip comments and blank lines)."""
    goals = []
    with open(goals_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                atoms = [a.strip() for a in line.split(',')]
                goals.append(atoms)
    return goals


def verify_fd(fd_path: str) -> bool:
    """Check that Fast Downward is callable."""
    try:
        result = subprocess.run(
            ['python3', fd_path, '--version'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 or 'fast downward' in (result.stdout + result.stderr).lower():
            print(f"[OK] Fast Downward found at: {fd_path}")
            return True
        # Also try just calling fd_path directly
        result2 = subprocess.run(
            [fd_path, '--version'],
            capture_output=True, text=True, timeout=10
        )
        if result2.returncode == 0:
            print(f"[OK] Fast Downward found at: {fd_path}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    print(f"[WARN] Fast Downward not found at '{fd_path}'.")
    print("       Install it: https://www.fast-downward.org/")
    print("       Then re-run with --fd-path /path/to/fast-downward.py")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Run all AAAI-10 reproducibility experiments')
    parser.add_argument('--fd-path', default='fast-downward.py',
                        help='Path to fast-downward.py executable')
    parser.add_argument('--config', default='experiments/config.json',
                        help='Experiment configuration JSON')
    parser.add_argument('--modes', nargs='+', default=['optimal', 'greedy'],
                        choices=['optimal', 'greedy', 'anytime'],
                        help='Planner modes to run')
    parser.add_argument('--domains', nargs='+', default=None,
                        help='Subset of domains to run (default: all six)')
    parser.add_argument('--beta', type=float, default=1.0)
    parser.add_argument('--n-problems', type=int, default=N_PROBLEMS)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--quick', action='store_true',
                        help='Quick smoke-test: 3 problems per row, optimal only')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory (default: results/<timestamp>)')
    parser.add_argument('--skip-verify', action='store_true',
                        help='Skip Fast Downward verification check')
    args = parser.parse_args()

    # Quick mode
    if args.quick:
        args.modes = ['optimal']
        args.n_problems = 3

    # Verify FD
    if not args.skip_verify:
        fd_ok = verify_fd(args.fd_path)
        if not fd_ok:
            print("\nProceeding anyway (results may fail). Use --skip-verify to suppress.")

    # Output directory
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = args.output_dir or os.path.join(ROOT, 'results', ts)
    os.makedirs(out_dir, exist_ok=True)
    print(f"\nResults will be saved to: {out_dir}")

    # Load configuration
    config_path = os.path.join(ROOT, args.config)
    domain_configs, eval_cfg = load_domain_configs(config_path, args.fd_path)

    # Filter domains
    target_domains = args.domains or list(domain_configs.keys())
    domain_configs = {k: v for k, v in domain_configs.items()
                      if k in target_domains}

    all_mode_results = {}

    for mode in args.modes:
        time_limit = {
            'optimal': 300.0, 'greedy': 120.0, 'anytime': 240.0
        }.get(mode, 300.0)

        print(f"\n{'='*65}")
        print(f"PLANNER MODE: {mode.upper()}")
        print(f"{'='*65}")

        mode_results = {}

        for domain_name, domain_config in domain_configs.items():
            print(f"\n--- Domain: {domain_name} ---")
            res = run_domain_experiment(
                domain_name=domain_name,
                domain_config=domain_config,
                fd_path=args.fd_path,
                planner_mode=mode,
                beta=args.beta,
                time_limit=time_limit,
                n_problems=args.n_problems,
                seed=args.seed,
            )
            mode_results[domain_name] = res
            print_results_table(domain_name, res, mode)

        all_mode_results[mode] = mode_results

        # Save per-mode results
        res_path = os.path.join(out_dir, f'results_{mode}.json')
        with open(res_path, 'w') as f:
            json.dump(mode_results, f, indent=2)
        print(f"\nSaved: {res_path}")

        # Generate plots
        try:
            plot_q_comparison(mode_results, mode, out_dir)
            plot_s_comparison(mode_results, mode, out_dir)
        except Exception as e:
            print(f"[WARN] Plot generation failed: {e}")

        # Generate LaTeX table
        try:
            table = generate_latex_table(mode_results, mode)
            tbl_path = os.path.join(out_dir, f'table_{mode}.tex')
            with open(tbl_path, 'w') as f:
                f.write(table)
            print(f"Saved LaTeX table: {tbl_path}")
        except Exception as e:
            print(f"[WARN] LaTeX table failed: {e}")

    # Beta sensitivity analysis (using optimal results at 50%)
    print(f"\n{'='*65}")
    print("BETA SENSITIVITY ANALYSIS")
    print(f"{'='*65}")

    compute_theoretical_example()

    if 'optimal' in all_mode_results:
        # Collect raw hypothesis cost data from optimal run
        # We store in a format sweep_beta_on_results can use
        # (This uses the stored per-run hypothesis costs if available)
        beta_results_path = os.path.join(out_dir, 'beta_sensitivity.json')
        try:
            from beta_analysis import sweep_beta_on_results, BETA_VALUES
            # Build synthetic sweep from stored results
            beta_out = {}
            for domain_name in all_mode_results.get('optimal', {}):
                pct_data = all_mode_results['optimal'][domain_name]
                raw = pct_data.get(50, {}).get('raw_hypotheses', [])
                if raw:
                    beta_out[domain_name] = sweep_beta_on_results(raw, BETA_VALUES)

            if beta_out:
                with open(beta_results_path, 'w') as f:
                    json.dump(beta_out, f, indent=2)
                plot_beta_sensitivity(beta_out, out_dir)
            else:
                print("  [INFO] No raw hypothesis data stored; run with --save-costs for beta sweep.")
        except Exception as e:
            print(f"[WARN] Beta analysis failed: {e}")

    # Print summary comparison table
    print(f"\n{'='*65}")
    print("SUMMARY: Q values vs. paper (optimal planner)")
    print(f"{'='*65}")
    print(f"{'Domain':<18} {'O%':>4}", end='')
    print(f" {'Paper':>7} {'Ours':>10}")
    print('-' * 45)

    if 'optimal' in all_mode_results:
        for domain in DOMAINS:
            if domain not in all_mode_results['optimal']:
                continue
            for pct in OBS_PERCENTAGES:
                paper_Q = PAPER_OPTIMAL.get(domain, {}).get(pct, {}).get('Q', None)
                our_data = all_mode_results['optimal'][domain].get(pct, {})
                our_Q = our_data.get('Q_mean', None)
                our_std = our_data.get('Q_std', 0)

                dom_str = domain if pct == OBS_PERCENTAGES[0] else ''
                paper_str = f'{paper_Q:.2f}' if paper_Q is not None else '  --'
                our_str = f'{our_Q:.3f}±{our_std:.3f}' if our_Q is not None else '       --'
                print(f"{dom_str:<18} {pct:>4}%  {paper_str:>7}  {our_str:>10}")

    print(f"\nAll results saved to: {out_dir}")
    print("To generate report: see report/ directory")


if __name__ == '__main__':
    main()
