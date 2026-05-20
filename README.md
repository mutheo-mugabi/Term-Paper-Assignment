# Probabilistic Plan Recognition — Reproducibility Study

Reproducibility study of:

> Ramírez, M., & Geffner, H. (2010). **Probabilistic Plan Recognition Using
> Off-the-Shelf Classical Planners.** *Proceedings of AAAI-10*, 1121–1126.

We reimplement the probabilistic goal recognition system from scratch in Python,
evaluate it across all six planning domains from the paper (Block Words, IPC-Grid,
Logistics, Intrusion Detection, Campus, Kitchen), and investigate the sensitivity
of the unspecified β parameter as a group extension.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Running Experiments](#running-experiments)
5. [Repository Structure](#repository-structure)
6. [Troubleshooting](#troubleshooting)

---

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | ≥ 3.10 | Use `python3` on Mac/Linux |
| Git | any | To clone the repo |
| CMake | ≥ 3.16 | Needed to build Fast Downward |
| C++ compiler | any modern | Xcode CLT on Mac; `build-essential` on Linux |

Check your Python version:
```bash
python3 --version
```

---

## Installation

### Step 1 — Clone the repository
```bash
git clone https://github.com/YOURUSERNAME/Term-Paper-Assignment.git
cd pr-recognition
```

### Step 2 — Install Python dependencies
```bash
pip3 install -r requirements.txt
```

### Step 3 — Install Fast Downward

Fast Downward is the external planner used to solve the compiled PDDL problems.
The script below downloads and compiles it automatically (takes 5–10 minutes):

```bash
bash scripts/install_fd.sh
```

Confirm it installed correctly:
```bash
python3 fast-downward/fast-downward.py --version
```
You should see a version number. If this works, you are ready to run experiments.

> **Mac (Apple Silicon / M1/M2/M3):** If the build fails, run `brew install cmake gcc` first, then retry.
>
> **Linux:** If cmake is missing, run `sudo apt install cmake build-essential` first.

---

## Quick Start

Run the unit tests first to confirm everything is working — **no planner needed**:
```bash
python3 -m pytest tests/test_core.py -v
```
All 22 tests should pass.

Then run a single recognition example on the Block Words domain:
```bash
python3 src/recognize.py \
    --domain  domains/blocks/domain.pddl \
    --problem domains/blocks/problem01.pddl \
    --goals   domains/blocks/goals.txt \
    --obs     experiments/example_obs.txt \
    --true-goal 0 \
    --beta 1.0 \
    --fd-path fast-downward/fast-downward.py \
    --mode optimal
```

Expected output:
```
Loaded 20 goals, 2 observations
Planner mode: optimal, β=1.0
  Goal 1/20: ...
  ...
--- Results (β=1.0, mode=optimal) ---
  P=0.xxxx  Δ=x.xx  [...]  ← TRUE
  ...
  Q=1  S=1  time=x.xs
```

---

## Running Experiments

### Full evaluation — all 6 domains

**Greedy mode** (recommended first run, ~1 hour):
```bash
python3 run_experiments.py \
    --fd-path fast-downward/fast-downward.py \
    --modes greedy
```

**Optimal mode** (~15 mins - 1 hour):
```bash
python3 run_experiments.py \
    --fd-path fast-downward/fast-downward.py \
    --modes optimal
```

**Both modes** (for full Table 1 comparison):
```bash
python3 run_experiments.py \
    --fd-path fast-downward/fast-downward.py \
    --modes optimal greedy
```

Results are saved to `results/results_greedy.json` and `results/results_optimal.json`.

---

### Quick test run (verify setup without waiting hours)

Runs fewer problems per domain — good for checking everything works end-to-end:
```bash
python3 run_experiments.py \
    --fd-path fast-downward/fast-downward.py \
    --modes greedy \
    --quick
```

---

### Beta sensitivity analysis (group extension)

Sweeps β ∈ {0.1, 0.5, 1.0, 2.0, 5.0, 10.0} at 50% observations to investigate
the effect of the unspecified β parameter from the paper:
```bash
python3 src/beta_analysis.py
```

---

### Generate figures and tables

After running experiments, generate all plots and LaTeX tables:
```bash
# For greedy results
python3 src/plot_results.py \
    --results results/results_greedy.json \
    --mode greedy \
    --output-dir results/

# For optimal results
python3 src/plot_results.py \
    --results results/results_optimal.json \
    --beta-results results/beta_sensitivity.json \
    --mode optimal \
    --output-dir results/
```

Output files saved to `results/`:
- `q_comparison_optimal.pdf` — Q metric vs. paper (Figure 1)
- `s_comparison_optimal.pdf` — S metric vs. paper (Figure 2)
- `beta_sensitivity.pdf` — β sensitivity curves (Figure 3)
- `table_optimal.tex` — LaTeX table for report

---

### Run a single domain only

Use `--domains` to target one domain:
```bash
python3 run_experiments.py \
    --fd-path fast-downward/fast-downward.py \
    --modes greedy \
    --domains blocks
```

Available domain names: `blocks`, `ipc_grid`, `logistics`, `intrusion`, `campus`, `kitchen`

---

## Repository Structure

```
Term-Paper-Assignment/
│
├── README.md                     This file
├── requirements.txt              Python dependencies
├── run_experiments.py            Master experiment runner
│
├── src/                          Source code
│   ├── compiler.py               PDDL transformation (Definition 2, Proposition 3)
│   ├── planner.py                Fast Downward wrapper (optimal / greedy)
│   ├── scorer.py                 Bayesian scoring layer (Equations 1-5)
│   ├── recognize.py              Single PR problem — CLI entry point
│   ├── evaluate.py               Full evaluation pipeline (replicates Table 1)
│   ├── beta_analysis.py          Beta sensitivity extension
│   └── plot_results.py           Figure and LaTeX table generation
│
├── domains/                      PDDL domains (6 total)
│   ├── blocks/                   Block Words
│   │   ├── domain.pddl
│   │   ├── problem01.pddl
│   │   └── goals.txt             20 candidate goals
│   ├── ipc_grid/                 IPC-Grid (7 goals)
│   ├── logistics/                Logistics (10 goals)
│   ├── intrusion/                Intrusion Detection (15 goals)
│   ├── campus/                   Campus (2 goals)
│   └── kitchen/                  Kitchen (3 goals)
│
├── experiments/
│   ├── config.json               Domain paths and experiment parameters
│   └── example_obs.txt           Example observation file for quick demo
│
├── tests/
│   └── test_core.py              22 unit tests (scorer, compiler, metrics)
│
└── scripts/
    └── install_fd.sh             Automated Fast Downward installer
```

---

## Troubleshooting

**`zsh: command not found: python`**
Use `python3` instead of `python` on Mac/Linux. All commands in this README
already use `python3`.

**`pip3: command not found`**
```bash
python3 -m pip install -r requirements.txt
```

**`$FD_PATH` is empty / `expected one argument` error**
Do not use `$FD_PATH`. Pass the path directly:
```bash
--fd-path fast-downward/fast-downward.py
```

**Fast Downward not found after install**
Make sure you are running commands from inside the `pr-recognition/` folder,
not from a parent directory. Check with:
```bash
ls fast-downward/fast-downward.py
```
If this returns "No such file", re-run `bash scripts/install_fd.sh`.

**`cmake: command not found` during install**
- Mac: `brew install cmake`
- Linux: `sudo apt install cmake`

**Fast Downward build fails on Mac**
```bash
brew install cmake gcc
bash scripts/install_fd.sh
```

**`No plan found` for all goals**
This usually means a PDDL syntax issue in a compiled problem file. Run with
`--mode greedy` first as it is more permissive, then switch to `--mode optimal`.

**Tests fail**
```bash
pip3 install pytest
python3 -m pytest tests/test_core.py -v
```
If a specific test fails, open an issue on the GitHub repository.

---

## How It Works

The system implements the method from Ramírez & Geffner (AAAI-10) in four steps:

1. **Compile** — for each candidate goal G and observation sequence O, produce
   two modified PDDL problems: one where the agent *must* follow O (compliant,
   G⁺_O) and one where it must *not* (non-compliant, G⁻_O).

2. **Plan** — solve both problems with Fast Downward to get costs c(G,O) and
   c(G,~O).

3. **Score** — compute the posterior P(G|O) ∝ P(O|G)·P(G) where the likelihood
   uses a Boltzmann distribution: P(O|G) = 1 / (1 + exp(β·Δ)) and
   Δ = c(G,O) − c(G,~O).

4. **Evaluate** — report Q (fraction of trials where the true goal is
   most-likely) and S (average number of equally-most-likely goals) over 15
   trials per observation level per domain.

---

## Citation

```bibtex
@inproceedings{ramirez2010,
  title     = {Probabilistic Plan Recognition Using Off-the-Shelf Classical Planners},
  author    = {Ram{\'i}rez, Miquel and Geffner, Hector},
  booktitle = {Proceedings of the Twenty-Fourth AAAI Conference on Artificial Intelligence},
  pages     = {1121--1126},
  year      = {2010}
}
```
