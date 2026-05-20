# Probabilistic Plan Recognition — Reproducibility Study
**COMS7044A | Group of 3**

Reproducibility study of:
> Ramírez, M. & Geffner, H. (2010). **Probabilistic Plan Recognition Using
> Off-the-Shelf Classical Planners.** *AAAI-10*, pp. 1121–1126.

---

## What This Repo Contains

| Component | Description |
|---|---|
| `src/compiler.py` | PDDL compiler — Definition 2 & Proposition 3 from the paper |
| `src/planner.py` | Fast Downward wrapper (optimal A*/LM-Cut, greedy Lazy FF) |
| `src/scorer.py` | Bayesian scoring layer — Equations 1–5 exactly |
| `src/recognize.py` | Single PR problem CLI entry point |
| `src/evaluate.py` | Full evaluation pipeline (replicates Table 1) |
| `src/beta_analysis.py` | β parameter sensitivity sweep (group-of-3 extension) |
| `src/plot_results.py` | Figure + LaTeX table generation |
| `run_experiments.py` | Master runner for all experiments |
| `domains/` | All 6 PDDL domains (blocks, ipc_grid, logistics, intrusion, campus, kitchen) |
| `tests/test_core.py` | 22 unit tests — all passing without any planner |
| `report/report.tex` | Full LaTeX reproducibility report |

---

## Quick Start (5 minutes)

### Step 1 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Install Fast Downward
```bash
bash scripts/install_fd.sh          # clones and builds Fast Downward
export FD_PATH=$(pwd)/fast-downward/fast-downward.py
```
Requires: Python ≥ 3.6, g++, cmake. Tested on Ubuntu 22.04 and macOS 13.

### Step 3 — Run unit tests (no planner needed)
```bash
python -m pytest tests/test_core.py -v
# Expected: 22 passed
```

### Step 4 — Run a single recognition example
```bash
python src/recognize.py \
    --domain  domains/blocks/domain.pddl \
    --problem domains/blocks/problem01.pddl \
    --goals   domains/blocks/goals.txt \
    --obs     experiments/example_obs.txt \
    --true-goal 0 \
    --beta 1.0 \
    --fd-path $FD_PATH \
    --mode optimal
```

### Step 5 — Run full experiments (reproduces Table 1)
```bash
# Both optimal and greedy, all 6 domains, 15 trials per row (~5 hours total)
python run_experiments.py --fd-path $FD_PATH --modes optimal greedy

# Quick smoke-test (3 trials per row, ~15 minutes)
python run_experiments.py --fd-path $FD_PATH --quick
```
Results are saved to `results/<timestamp>/`.

### Step 6 — Generate figures and LaTeX tables
```bash
python src/plot_results.py \
    --results      results/<timestamp>/results_optimal.json \
    --beta-results results/beta_sensitivity.json \
    --mode         optimal \
    --output-dir   results/
```

### Step 7 — Compile the report
```bash
cd report
pdflatex report.tex && pdflatex report.tex
```

---

## Observation File Format

One action instance per line (action name followed by arguments):
```
pick-up a
stack a b
unstack c d
```

## Goals File Format

One goal per line, PDDL atoms comma-separated:
```
(on a b),(on b c),(on c d),(on d e),(on e f),(ontable f)
(on f e),(on e d),(on d c),(on c b),(on b a),(ontable a)
```

---

## How It Works (Method Summary)

For each candidate goal G and observation sequence O:

1. **Compile** the domain into two modified problems using `compiler.py`:
   - **Compliant** (G⁺_O): goal includes fluent `p_last` — planner must follow O
   - **Non-compliant** (G⁻_O): goal includes `¬p_last` — planner must avoid O
2. **Solve** both problems with Fast Downward to get costs c(G,O) and c(G,~O)
3. **Score** each goal with the Boltzmann likelihood (Equations 2–3):
   - Δ(G,O) = c(G,O) − c(G,~O)
   - P(O|G) = 1 / (1 + exp(β·Δ))
4. **Normalise** via Bayes' rule to get posterior P(G|O)

The hidden goal is identified as `argmax_G P(G|O)`.

---

## Key Design Choices

| Ambiguity in paper | Our resolution |
|---|---|
| β not specified | Default β=1.0; sensitivity sweep in extension |
| Original instances unavailable | Reconstructed from paper descriptions |
| "Suboptimal" obs for Campus/Kitchen | Greedy planner mode |
| Duplicate observations | Rename and clone action per paper's remark |
| "15 PR problems per row" | 15 random (goal, prefix) trials, seed=42 |

---

## Running Individual Domains

```bash
# Only run blocks and logistics in optimal mode
python run_experiments.py \
    --fd-path $FD_PATH \
    --modes optimal \
    --domains blocks logistics \
    --n-problems 15 \
    --seed 42

# Beta sensitivity sweep
python src/beta_analysis.py --results results/<timestamp>/results_optimal.json
```

---

## Citation

```bibtex
@inproceedings{ramirez2010,
  author    = {Ram{\'i}rez, Miquel and Geffner, Hector},
  title     = {Probabilistic Plan Recognition Using Off-the-Shelf Classical Planners},
  booktitle = {Proceedings of AAAI-10},
  pages     = {1121--1126},
  year      = {2010}
}
```
