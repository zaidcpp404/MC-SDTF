# MC-SDTF Execution Guide

Step-by-step instructions to reproduce the results of the ICSSD2026 paper
(*A Multi-Objective Optimization-Based Digital Twin Framework for Energy Reliability and
Sustainability in Mission-Critical IoT Systems*).

---

## Prerequisites

- **Python 3.12** (the version used for the paper)
- **RAM:** 2 GB free is enough; the campaign keeps one run in memory at a time
- **Disk:** a few megabytes for the run cache in `output/runs/`
- **OS:** Linux, macOS or Windows

## Installation

```bash
git clone https://github.com/zaidcpp404/MC-SDTF.git
cd MC-SDTF

python3.12 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## Step 1: smoke test

```bash
python src/experiments.py all --quick
```

Runs every stage with population 40, 30 generations, 3 runs per domain and one scalability
run per size. Output goes to `output/quick/` and never touches `results/`. Use it to confirm
that the installation works; its numbers are not meaningful.

## Step 2: the full campaign

```bash
python src/experiments.py all
```

This runs, in order:

| Stage | Command | Runs |
|:--|:--|:--|
| NSGA-II, three domains | `python src/experiments.py nsga2` | 3 × 30 |
| NSGA-III and MOEA/D, industrial | `python src/experiments.py compare` | 2 × 30 |
| Scalability, N = 1,000 / 2,500 / 5,000 | `python src/experiments.py scalability` | 3 × 5 |
| Tables and statistics | `python src/experiments.py analyze` | — |
| Figures 1–7 | `python src/experiments.py figures` | — |

Each run uses population 200 and 500 generations (100,000 objective evaluations). The time of
every run is recorded in `results/data/runs_metrics.csv`, and `results/data/SUMMARY.md` gives the
per-run means and the total for the machine the committed data were produced on. The campaign
can be stopped at any point: finished runs are cached in `output/runs/` and skipped on restart.

Useful options:

| Option | Effect |
|:--|:--|
| `--domains industrial smartcity` | restrict the NSGA-II stage to some domains |
| `--runs 10` | fewer independent runs (seeds 1..10) |
| `--jobs 4` | run 4 optimizations in parallel (faster, but per-run times include contention) |
| `--sizes 1000 2500` | scalability sizes |
| `--scale-runs 3` | runs per scalability size |
| `--repair integer` | round only r, N_gw and ε_h (see the README); writes to `output/integer_repair/` |

## Step 3: tables and figures only

```bash
python src/experiments.py analyze      # rebuild every CSV from the cached runs
python src/experiments.py figures      # redraw Figures 1-7 from results/data/
```

`figures` needs only the committed CSV files, so it works straight after cloning.

---

## Paper item → file

| Paper item | File |
|:--|:--|
| Section 5.6 (HV, IGD, front size, runtime) | `results/data/quality_metrics_summary.csv` |
| Table 5 / 6 / 7 | `results/data/table5_industrial.csv`, `table6_smartcity.csv`, `table7_healthcare.csv` |
| Table 8 | `results/data/table8_cross_domain.csv` |
| Table 9 | `results/data/table9_algorithm_comparison.csv`, `wilcoxon_ranksum_tests.csv` |
| Knee-point reductions (abstract, conclusions) | `results/data/key_results_knee_reductions.csv` |
| Scalability (Section 5.6) | `results/data/scalability.csv` |
| Pareto-front data | `results/data/pareto_front_*.csv`, `pareto_fronts_all_runs_*.csv`, `reference_front_*.csv` |
| Figures 1–7 | `results/figures/Fig1_SensorNode.png` … `Fig7_Convergence.png` |

---

## Single-run pipeline (`src/main.py`)

The original pipeline runs one NSGA-II optimization per domain (seed 42) and prints the
tables and analyses to the console, saving figures and `.pkl` files to `output/`:

```bash
cd src
python main.py --quick        # population 50, 50 generations
python main.py --full         # population 200, 500 generations (paper settings)
python main.py --figures-only # redraw from output/MCSDTF_AllResults.pkl
python optimizer.py industrial 200 500
```

It is handy for exploring parameter changes in `config.py`, for example:

```python
from config import get_industrial_params
params = get_industrial_params()
params.A_min = 0.999       # relax availability to 99.9%
params.budget = 300000     # reduce the budget to $300K
```

The paper's statistics (30 runs, HV, IGD, confidence intervals, algorithm comparison) come
from `src/experiments.py`, not from `main.py`.

---

## Troubleshooting

| Problem | Solution |
|:--|:--|
| `ModuleNotFoundError: pymoo` | `pip install -r requirements.txt` inside the virtual environment |
| A run was interrupted | rerun the same command; cached runs are skipped |
| Changed `--pop` or `--gen` | runs with other settings are re-computed, not mixed with cached ones |
| `RuntimeWarning: invalid value encountered in power` from `sbx.py` | harmless warning inside pymoo's SBX operator |

---

## Source file → paper

| Source file | Paper element |
|:--|:--|
| `config.py` | Tables 2–4 (case-study parameters) |
| `objectives.py` | Section 4 (objective and constraint models) |
| `optimizer.py` | Section 4.4 and 5.1 (NSGA-II setup) |
| `metrics.py` | Section 4.4 (knee point), Section 5.1 (HV and IGD rules) |
| `experiments.py` | Sections 5.1–5.6, Tables 5–9, Figures 1–7 |
| `P02_sensor_node.py` | Figure 1 |
| `visualizations.py` | Figures 2–7 |
| `analysis.py`, `main.py` | single-run pipeline |
