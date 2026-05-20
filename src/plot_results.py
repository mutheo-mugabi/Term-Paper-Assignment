"""
Results Plotting
================
Generates figures for the reproducibility report:
  1. Q comparison: our results vs. paper's Table 1 (per domain, per planner mode)
  2. S comparison: spread metric
  3. Beta sensitivity curves
  4. Time comparison (log scale)
"""

import json
import os
import sys
import math
import argparse

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("[WARN] matplotlib not available; skipping plots")

OBS_PCTS = [10, 30, 50, 70, 100]
DOMAINS = ['blocks', 'ipc_grid', 'logistics', 'intrusion', 'campus', 'kitchen']
DOMAIN_LABELS = {
    'blocks':    'Block Words',
    'ipc_grid':  'IPC-Grid',
    'logistics': 'Logistics',
    'intrusion': 'Intrusion Det.',
    'campus':    'Campus',
    'kitchen':   'Kitchen',
}

# ---- Paper's Table 1 reference values ----
# Format: {domain: {obs_pct: {'Q': ..., 'S': ..., 'T': ..., 'L': ...}}}
# HSP*_f column (optimal)
PAPER_OPTIMAL = {
    'blocks': {
        10: {'Q': 1.00, 'S': 6.00, 'T': 1184.23, 'L': 10},
        30: {'Q': 1.00, 'S': 3.25, 'T': 1269.31, 'L': 11},
        50: {'Q': 1.00, 'S': 2.23, 'T': 1423.05, 'L': 11},
        70: {'Q': 1.00, 'S': 1.27, 'T': 1787.67, 'L': 12},
       100: {'Q': 1.00, 'S': 1.13, 'T': 2100.21, 'L': 12},
    },
    'ipc_grid': {
        10: {'Q': 0.75, 'S': 1.38, 'T':  73.38, 'L': 15},
        30: {'Q': 1.00, 'S': 1.00, 'T': 155.47, 'L': 17},
        50: {'Q': 1.00, 'S': 1.00, 'T': 202.69, 'L': 17},
        70: {'Q': 1.00, 'S': 1.00, 'T': 329.64, 'L': 20},
       100: {'Q': 1.00, 'S': 1.00, 'T': 435.60, 'L': 18},
    },
    'logistics': {
        10: {'Q': 0.90, 'S': 2.30, 'T':  120.94, 'L': 21},
        30: {'Q': 1.00, 'S': 1.07, 'T': 1071.91, 'L': 22},
        50: {'Q': 1.00, 'S': 1.20, 'T':  813.36, 'L': 23},
        70: {'Q': 1.00, 'S': 1.00, 'T':  606.87, 'L': 24},
       100: {'Q': 1.00, 'S': 1.00, 'T':  525.44, 'L': 24},
    },
    'intrusion': {
        10: {'Q': 1.00, 'S': 1.80, 'T':  26.29, 'L': 18},
        30: {'Q': 1.00, 'S': 1.13, 'T':  73.08, 'L': 19},
        50: {'Q': 1.00, 'S': 1.00, 'T': 103.58, 'L': 20},
        70: {'Q': 1.00, 'S': 1.00, 'T': 188.44, 'L': 21},
       100: {'Q': 1.00, 'S': 1.00, 'T': 179.41, 'L': 21},
    },
    'campus': {
        10: {'Q': 0.93, 'S': 1.33, 'T':  0.67, 'L': 10},
        30: {'Q': 1.00, 'S': 1.00, 'T':  0.92, 'L': 11},
        50: {'Q': 1.00, 'S': 1.00, 'T':  1.11, 'L': 11},
        70: {'Q': 1.00, 'S': 1.00, 'T':  1.41, 'L': 11},
       100: {'Q': 1.00, 'S': 1.00, 'T':  1.56, 'L': 11},
    },
    'kitchen': {
        10: {'Q': 0.88, 'S': 1.25, 'T':  77.85, 'L': 11},
        30: {'Q': 0.93, 'S': 1.21, 'T': 144.58, 'L': 11},
        50: {'Q': 1.00, 'S': 1.33, 'T': 218.51, 'L': 11},
        70: {'Q': 1.00, 'S': 1.20, 'T': 245.88, 'L': 11},
       100: {'Q': 1.00, 'S': 1.47, 'T': 488.00, 'L': 12},
    },
}

PAPER_GREEDY = {
    'blocks': {
        10: {'Q': 0.00, 'S': 1.67}, 30: {'Q': 0.50, 'S': 2.00},
        50: {'Q': 0.54, 'S': 1.23}, 70: {'Q': 0.73, 'S': 1.20},
       100: {'Q': 0.73, 'S': 1.07},
    },
    'ipc_grid': {
        10: {'Q': 0.75, 'S': 1.38}, 30: {'Q': 1.00, 'S': 1.08},
        50: {'Q': 1.00, 'S': 1.00}, 70: {'Q': 1.00, 'S': 1.00},
       100: {'Q': 1.00, 'S': 1.00},
    },
    'logistics': {
        10: {'Q': 1.00, 'S': 1.20}, 30: {'Q': 0.87, 'S': 1.13},
        50: {'Q': 1.00, 'S': 1.20}, 70: {'Q': 1.00, 'S': 1.00},
       100: {'Q': 1.00, 'S': 1.00},
    },
    'intrusion': {
        10: {'Q': 1.00, 'S': 2.20}, 30: {'Q': 1.00, 'S': 1.13},
        50: {'Q': 1.00, 'S': 1.00}, 70: {'Q': 1.00, 'S': 1.00},
       100: {'Q': 1.00, 'S': 1.00},
    },
    'campus': {
        10: {'Q': 0.67, 'S': 1.27}, 30: {'Q': 0.80, 'S': 1.07},
        50: {'Q': 0.80, 'S': 1.13}, 70: {'Q': 0.80, 'S': 1.00},
       100: {'Q': 1.00, 'S': 1.20},
    },
    'kitchen': {
        10: {'Q': 0.88, 'S': 1.25}, 30: {'Q': 0.93, 'S': 1.21},
        50: {'Q': 1.00, 'S': 1.27}, 70: {'Q': 1.00, 'S': 1.47},
       100: {'Q': 1.00, 'S': 1.60},
    },
}


def plot_q_comparison(our_results: dict, mode: str, output_dir: str):
    """Plot Q (recognition accuracy) comparison: ours vs. paper."""
    if not HAS_MPL:
        return

    paper_ref = PAPER_OPTIMAL if mode == 'optimal' else PAPER_GREEDY
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharey=True)
    fig.suptitle(f'Recognition Quality Q (mode: {mode})\nOur Results vs. Ramírez & Geffner (AAAI-10)',
                 fontsize=13, fontweight='bold')

    for ax, domain in zip(axes.flat, DOMAINS):
        paper = paper_ref.get(domain, {})
        ours  = our_results.get(domain, {})

        p_Q = [paper.get(p, {}).get('Q', None) for p in OBS_PCTS]
        o_Q = [ours.get(str(p), ours.get(p, {})).get('Q_mean', None) for p in OBS_PCTS]
        o_std = [ours.get(str(p), ours.get(p, {})).get('Q_std', 0) for p in OBS_PCTS]

        x = list(range(len(OBS_PCTS)))
        # Paper reference (no error bar)
        valid_p = [(i, v) for i, v in enumerate(p_Q) if v is not None]
        if valid_p:
            ax.plot([i for i, _ in valid_p], [v for _, v in valid_p],
                    'b--o', label='Paper (HSP*_f)' if mode == 'optimal' else 'Paper (Greedy)',
                    linewidth=2, markersize=6)

        # Our results with error bars
        valid_o = [(i, v, o_std[i]) for i, v in enumerate(o_Q) if v is not None]
        if valid_o:
            xs = [i for i, _, _ in valid_o]
            ys = [v for _, v, _ in valid_o]
            es = [e for _, _, e in valid_o]
            ax.errorbar(xs, ys, yerr=es, fmt='r-s', label='Ours',
                        linewidth=2, markersize=6, capsize=4)

        ax.set_title(DOMAIN_LABELS.get(domain, domain), fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([f'{p}%' for p in OBS_PCTS])
        ax.set_ylim(-0.05, 1.10)
        ax.set_ylabel('Q (accuracy)', fontsize=9)
        ax.set_xlabel('Observation %', fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=1.0, color='gray', linestyle=':', alpha=0.5)

    plt.tight_layout()
    path = os.path.join(output_dir, f'q_comparison_{mode}.pdf')
    plt.savefig(path, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved: {path}")


def plot_s_comparison(our_results: dict, mode: str, output_dir: str):
    """Plot S (spread) comparison."""
    if not HAS_MPL:
        return

    paper_ref = PAPER_OPTIMAL if mode == 'optimal' else PAPER_GREEDY
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fig.suptitle(f'Spread S (number of equally-likely top goals)\nmode: {mode}',
                 fontsize=13, fontweight='bold')

    for ax, domain in zip(axes.flat, DOMAINS):
        paper = paper_ref.get(domain, {})
        ours  = our_results.get(domain, {})

        p_S = [paper.get(p, {}).get('S', None) for p in OBS_PCTS]
        o_S = [ours.get(str(p), ours.get(p, {})).get('S_mean', None) for p in OBS_PCTS]
        o_std = [ours.get(str(p), ours.get(p, {})).get('S_std', 0) for p in OBS_PCTS]

        x = list(range(len(OBS_PCTS)))
        valid_p = [(i, v) for i, v in enumerate(p_S) if v is not None]
        if valid_p:
            ax.plot([i for i, _ in valid_p], [v for _, v in valid_p],
                    'b--o', label='Paper', linewidth=2, markersize=6)

        valid_o = [(i, v, o_std[i]) for i, v in enumerate(o_S) if v is not None]
        if valid_o:
            xs = [i for i, _, _ in valid_o]
            ys = [v for _, v, _ in valid_o]
            es = [e for _, _, e in valid_o]
            ax.errorbar(xs, ys, yerr=es, fmt='r-s', label='Ours',
                        linewidth=2, markersize=6, capsize=4)

        ax.set_title(DOMAIN_LABELS.get(domain, domain), fontsize=11)
        ax.set_xticks(x)
        ax.set_xticklabels([f'{p}%' for p in OBS_PCTS])
        ax.set_ylabel('S (spread)', fontsize=9)
        ax.set_xlabel('Observation %', fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(output_dir, f's_comparison_{mode}.pdf')
    plt.savefig(path, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved: {path}")


def plot_beta_sensitivity(beta_results: dict, output_dir: str):
    """Plot Q as a function of β for each domain."""
    if not HAS_MPL:
        return

    fig, ax = plt.subplots(figsize=(9, 5))

    colors = plt.cm.tab10.colors
    for i, (domain, sweep) in enumerate(beta_results.items()):
        betas = sorted(sweep.keys())
        Q_means = [sweep[b]['Q_mean'] for b in betas]
        Q_stds  = [sweep[b]['Q_std']  for b in betas]
        label = DOMAIN_LABELS.get(domain, domain)
        ax.errorbar(betas, Q_means, yerr=Q_stds, fmt='-o',
                    color=colors[i % len(colors)],
                    label=label, linewidth=2, markersize=6, capsize=3)

    ax.set_xlabel('β (Boltzmann temperature)', fontsize=12)
    ax.set_ylabel('Q (recognition accuracy)', fontsize=12)
    ax.set_title('Sensitivity of Recognition Quality to β\n(at 50% observations)', fontsize=12)
    ax.set_xscale('log')
    ax.set_ylim(-0.05, 1.10)
    ax.legend(fontsize=9, loc='lower right')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=1.0, color='gray', linestyle=':', alpha=0.5)

    path = os.path.join(output_dir, 'beta_sensitivity.pdf')
    plt.savefig(path, bbox_inches='tight', dpi=150)
    plt.close()
    print(f"Saved: {path}")


def generate_latex_table(our_results: dict, mode: str) -> str:
    """Generate LaTeX table comparing our results to the paper."""
    paper_ref = PAPER_OPTIMAL if mode == 'optimal' else PAPER_GREEDY
    mode_label = 'Optimal (A*/LM-Cut)' if mode == 'optimal' else 'Greedy (Lazy FF)'

    lines = [
        r'\begin{table}[t]',
        r'\centering',
        r'\caption{Comparison of results with Ramírez \& Geffner (AAAI-10) Table 1 '
        r'(' + mode_label + r'). '
        r'Q: fraction of PR problems where hidden goal is most likely. '
        r'S: avg number of most-likely goals. '
        r'$\pm$ denotes standard deviation over 15 runs.}',
        r'\label{tab:results_' + mode + r'}',
        r'\small',
        r'\begin{tabular}{llrrrrrr}',
        r'\toprule',
        r'Domain & O\% & \multicolumn{2}{c}{Paper Q / S} & \multicolumn{2}{c}{Ours Q} & \multicolumn{2}{c}{Ours S} \\',
        r'\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}',
        r' & & Q & S & Mean$\pm$Std & Mean$\pm$Std \\',
        r'\midrule',
    ]

    for domain in DOMAINS:
        paper = paper_ref.get(domain, {})
        ours  = our_results.get(domain, {})
        label = DOMAIN_LABELS.get(domain, domain)

        first_row = True
        for pct in OBS_PCTS:
            p_data = paper.get(pct, {})
            o_data = ours.get(str(pct), ours.get(pct, {}))

            p_Q = p_data.get('Q', '-')
            p_S = p_data.get('S', '-')
            o_Q = o_data.get('Q_mean', None)
            o_Qs = o_data.get('Q_std', 0)
            o_S = o_data.get('S_mean', None)
            o_Ss = o_data.get('S_std', 0)

            domain_col = label if first_row else ''
            first_row = False

            p_Q_str = f'{p_Q:.2f}' if isinstance(p_Q, float) else str(p_Q)
            p_S_str = f'{p_S:.2f}' if isinstance(p_S, float) else str(p_S)
            o_Q_str = f'{o_Q:.3f}$\\pm${o_Qs:.3f}' if o_Q is not None else '--'
            o_S_str = f'{o_S:.2f}$\\pm${o_Ss:.2f}' if o_S is not None else '--'

            lines.append(
                f'{domain_col} & {pct}\\% & {p_Q_str} & {p_S_str} & '
                f'{o_Q_str} & {o_S_str} \\\\'
            )
        lines.append(r'\midrule')

    lines += [
        r'\bottomrule',
        r'\end{tabular}',
        r'\end{table}',
    ]
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate result plots')
    parser.add_argument('--results', required=True,
                        help='JSON results file from evaluate.py')
    parser.add_argument('--beta-results', default=None,
                        help='JSON from beta_analysis.py')
    parser.add_argument('--mode', default='optimal')
    parser.add_argument('--output-dir', default='../results')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.results) as f:
        results = json.load(f)

    plot_q_comparison(results, args.mode, args.output_dir)
    plot_s_comparison(results, args.mode, args.output_dir)

    # LaTeX table
    table = generate_latex_table(results, args.mode)
    table_path = os.path.join(args.output_dir, f'table_{args.mode}.tex')
    with open(table_path, 'w') as f:
        f.write(table)
    print(f"Saved LaTeX table: {table_path}")

    if args.beta_results:
        with open(args.beta_results) as f:
            beta_data = json.load(f)
        plot_beta_sensitivity(beta_data, args.output_dir)
