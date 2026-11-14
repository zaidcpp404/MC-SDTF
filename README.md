# MC-SDTF: Mission-Critical Sustainable Digital Twin Framework

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![NSGA-II](https://img.shields.io/badge/Optimizer-NSGA--II%20(pymoo%200.6.1)-orange.svg)](https://pymoo.org/)

> **Paper:** Zaid H. Berjis, Siddeeq Y. Ameen, Mohammed H. AL Jammas,
> *A Multi-Objective Optimization-Based Digital Twin Framework for Energy Reliability and
> Sustainability in Mission-Critical IoT Systems*, ICSSD2026 (paper EE-18, ICSSD-424).

This repository holds the Python implementation, the benchmark case-study definitions and the
Pareto-front data behind the paper. MC-SDTF (the **Mission-Critical** Sustainable Digital Twin
Framework) treats mission-critical reliability and environmental sustainability as jointly
optimized objectives and charts their Pareto front with NSGA-II for three IoT domains.

Every number in `results/data/` was produced by the code in `src/`; nothing there is written by
hand. [`results/data/SUMMARY.md`](results/data/SUMMARY.md) shows the results as readable tables.

---

## Overview

| Layer | Function | Implementation |
|-------|----------|----------------|
| **Layer 1** | Physical IoT (sensors, communication, power) | `src/objectives.py` |
| **Layer 2** | Reliability (availability, redundancy, recovery) | `src/objectives.py` |
| **Layer 3** | Sustainability (energy, carbon LCA, lifecycle) | `src/objectives.py` |
| **Layer 4** | Multi-objective optimization (NSGA-II) | `src/optimizer.py` |

### Case studies (benchmark definitions in `src/config.py`)

| Domain | Nodes | Availability target | Budget |
|--------|-------|---------------------|--------|
| **Industrial smart factory** | 500 sensors on 50 CNC machines | 99.99% | $500K |
| **Smart city monitoring** | 200 nodes (30 critical) | 99.9% standard / 99.99% critical | $200K |
| **Hospital patient monitoring** | 720 devices on 120 beds | 99.999% (ECG) | $800K |

### Objectives (all minimized by pymoo)

1. **f₁ = −A_sys** — negative system availability (maximizes availability)
2. **f₂ = E_total** — total energy consumption (kWh/yr)
3. **f₃ = CF_total** — carbon footprint (kgCO₂-eq/yr)
4. **f₄ = MRT** — mean recovery time (s)

Constraints: availability ≥ A_min, end-to-end latency ≤ L_max, deployment cost ≤ budget.
The full formulation is in [`docs/equations.md`](docs/equations.md).

---

## Quick start

```bash
git clone https://github.com/zaidcpp404/MC-SDTF.git
cd MC-SDTF
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Smoke test of the whole pipeline (about 15 s; writes to output/quick/, not results/)
python src/experiments.py all --quick
```

---

## Reproducing the paper

All commands run from the repository root. `src/experiments.py` caches every finished run in
`output/runs/`, so an interrupted campaign resumes where it stopped, and `analyze` / `figures`
can be re-run at any time without re-optimizing.

```bash
python src/experiments.py all          # the full campaign: every table and figure below
```

| Paper item | Command | Output |
|:--|:--|:--|
| Section 5.6: HV, IGD, front size (30 runs, mean ± 95% CI) | `python src/experiments.py nsga2 analyze` | `results/data/quality_metrics_summary.csv`, `runs_metrics.csv` |
| Table 5 (industrial) | `python src/experiments.py nsga2 analyze --domains industrial` | `results/data/table5_industrial.csv` |
| Table 6 (smart city) | `python src/experiments.py nsga2 analyze --domains smartcity` | `results/data/table6_smartcity.csv` |
| Table 7 (healthcare) | `python src/experiments.py nsga2 analyze --domains healthcare` | `results/data/table7_healthcare.csv` |
| Tables 5–7, 30-run means | `python src/experiments.py nsga2 analyze` | `results/data/tables5to7_mean_ci95_over_runs.csv` |
| Table 8 (cross-domain) | `python src/experiments.py nsga2 analyze` | `results/data/table8_cross_domain.csv` |
| Table 9 (NSGA-II vs NSGA-III vs MOEA/D) | `python src/experiments.py nsga2 compare analyze --domains industrial` | `results/data/table9_algorithm_comparison.csv`, `wilcoxon_ranksum_tests.csv` |
| Knee-point energy and carbon reductions | `python src/experiments.py nsga2 analyze` | `results/data/key_results_knee_reductions.csv` |
| Scalability (N = 1,000 / 2,500 / 5,000) | `python src/experiments.py nsga2 scalability analyze --domains industrial` | `results/data/scalability.csv` |
| Figure 1 (sensor node model) | `python src/experiments.py figures` | `results/figures/Fig1_SensorNode.png` |
| Figure 2 (industrial Pareto front) | `python src/experiments.py figures` | `results/figures/Fig2_industrial_Pareto.png` |
| Figure 3 (sensitivity analysis) | `python src/experiments.py figures` | `results/figures/Fig3_SensitivityAnalysis.png` |
| Figure 4 (smart city Pareto front) | `python src/experiments.py figures` | `results/figures/Fig4_smartcity_Pareto.png` |
| Figure 5 (healthcare Pareto front) | `python src/experiments.py figures` | `results/figures/Fig5_healthcare_Pareto.png` |
| Figure 6 (cross-domain comparison) | `python src/experiments.py figures` | `results/figures/Fig6_CrossDomain.png` |
| Figure 7 (convergence) | `python src/experiments.py figures` | `results/figures/Fig7_Convergence.png` |

`analyze` always reads every run in the cache, so the per-domain commands above give the
complete tables once all domains have been run. `figures` only reads `results/data/` and
takes a few seconds.

### Runtime

One NSGA-II run (population 200, 500 generations, 100,000 evaluations) takes well under two
minutes on a current desktop CPU. The run times measured for the committed data, and the
machine they were measured on, are in [`results/data/SUMMARY.md`](results/data/SUMMARY.md)
and [`results/data/environment.json`](results/data/environment.json). By default runs execute
one at a time so that the recorded per-run times are not inflated by contention;
`--jobs N` runs N in parallel.

---

## Data files (`results/data/`)

| File | Content |
|:--|:--|
| `pareto_front_<domain>.csv` | Final Pareto front of the representative run (the run with the median HV): decision variables, all four objectives and the configuration labels used in Tables 5–7 |
| `pareto_fronts_all_runs_<domain>.csv` | Final Pareto fronts of all 30 NSGA-II runs |
| `reference_front_<domain>.csv` | Combined-best reference front (non-dominated union of all 30 runs), used for IGD |
| `pareto_fronts_all_runs_industrial_{nsga3,moead}.csv` | Final fronts of the comparison algorithms |
| `runs_metrics.csv` | One row per run: HV, IGD, front size, knee-point reductions, runtime, objective-evaluation time |
| `quality_metrics_summary.csv` | HV, IGD, front size and runtime per domain (mean ± 95% CI) |
| `table5_industrial.csv`, `table6_smartcity.csv`, `table7_healthcare.csv` | Tables 5–7 |
| `tables5to7_mean_ci95_over_runs.csv` | The four configurations of Tables 5–7 averaged over all runs |
| `table8_cross_domain.csv` | Table 8 |
| `table9_algorithm_comparison.csv`, `wilcoxon_ranksum_tests.csv` | Table 9 and its Wilcoxon rank-sum tests |
| `key_results_knee_reductions.csv` | Energy and carbon reduction at the knee point |
| `scalability.csv` | Runtime split into objective evaluation and optimizer overhead for N = 500 … 5,000 |
| `convergence.csv` | Front size, HV and IGD per generation (mean ± 95% CI), the data of Figure 7 |
| `environment.json` | Python and package versions, platform, settings, total optimization time |
| `SUMMARY.md` | All of the above as readable tables (generated) |

Column names carry units. `availability_pct` is 100 × availability; `neg_availability` is the
objective f₁ exactly as minimized.

---

## Methods as implemented

These points describe exactly what the code does, including where it adds detail to the paper
text.

* **NSGA-II** (`build_nsga2` in `src/optimizer.py`): population 200, a fixed budget of 500
  generations as the only stopping rule, SBX crossover (probability 0.8, η = 15), polynomial
  mutation (η = 20), duplicate elimination.
* **Rounding repair.** The code uses pymoo's `RoundingRepair` after crossover and mutation.
  This repair rounds *every* decision variable to an integer, so the continuous variables
  (d, p_tx, f_s, α, T_m) are also searched on integer values (for example d ∈ {0.01, 1} after
  clamping, α ∈ {0, 1}). The committed results use this behavior because it is the code the
  paper's results were produced with. `--repair integer` rounds only r, N_gw and ε_h; its output
  goes to `output/integer_repair/` and never overwrites `results/`.
* **Runs and seeds.** 30 independent runs per domain with seeds 1–30. NSGA-III and MOEA/D use
  the same seeds, population, generation budget and variation operators.
* **Final front.** The feasible, non-dominated members of the final population (for NSGA-II this
  equals pymoo's `res.opt`).
* **HV and IGD** (`src/metrics.py`). Per domain, every objective is normalized with the best and
  worst values observed over all runs' final fronts. The HV reference point is the worst observed
  value of each objective, i.e. (1, 1, 1, 1) after normalization, so HV is the fraction of that
  box dominated by a front. IGD is measured against the combined-best front (the non-dominated
  union of all runs), in the same normalized space. Both use pymoo's indicators.
* **Table 9.** For the algorithm comparison, the normalization bounds and the combined-best
  front are pooled over all runs of all three algorithms, so NSGA-II's HV and IGD in Table 9 are
  on a common scale with NSGA-III and MOEA/D and differ slightly from its per-domain values.
  Differences are tested with the two-sided Wilcoxon rank-sum test (`scipy.stats.ranksums`).
* **NSGA-III** uses 200 reference directions from pymoo's Riesz s-energy method.
  **MOEA/D** (Tchebycheff decomposition, 200 weight vectors) does not accept constraints in
  pymoo, so it optimizes a static-penalty version of the problem (each objective + 10⁶ × total
  constraint violation); only feasible solutions count in its final front.
* **Confidence intervals.** Mean ± half-width of the two-sided 95% Student-t interval.
* **Key configurations.** Max-reliability = highest availability; max-sustainability = lowest
  energy; knee point = largest perpendicular distance from the line joining these two anchors
  in the normalized availability–energy plane (Section 4.4), on the utopia side of the line;
  balanced = lowest mean of the four objectives, each min-max normalized over the front.
  Tables 5–8 and Figures 2–6 use the representative (median-HV) run of each domain;
  `tables5to7_mean_ci95_over_runs.csv` and `key_results_knee_reductions.csv` also give the
  30-run means.
* **Smart city availability.** `config.py` applies a single 99.9% network constraint; the 99.99%
  target for the 30 critical nodes is recorded in the parameters but is not a separate
  constraint in the optimization.
* **Scalability.** The industrial case with `n_nodes` set to 1,000, 2,500 and 5,000 (all other
  parameters unchanged), 5 runs each. The objective functions are closed-form in N, so
  `scalability.csv` reports the measured split between objective evaluation and optimizer
  overhead rather than assuming one.

---

## Figures

Figures in `results/figures/` are drawn from the CSV files by `python src/experiments.py figures`
and use the paper's numbering. The files of the first repository release are kept, renamed to
the same numbering, in `results/figures/previous_release/`.

| Paper figure | Content | File | Name in the first release |
|:-:|:--|:--|:--|
| 1 | Sensor node model | `Fig1_SensorNode.png` | `Fig2_SensorNode.png` |
| 2 | Industrial Pareto front | `Fig2_industrial_Pareto.png` | `Fig6_industrial_Pareto.png` |
| 3 | Sensitivity analysis | `Fig3_SensitivityAnalysis.png` | `Fig_SensitivityAnalysis.png` |
| 4 | Smart city Pareto front | `Fig4_smartcity_Pareto.png` | `Fig7_smartcity_Pareto.png` |
| 5 | Healthcare Pareto front | `Fig5_healthcare_Pareto.png` | `Fig8_healthcare_Pareto.png` |
| 6 | Cross-domain comparison | `Fig6_CrossDomain.png` | `Fig9_CrossDomain.png` |
| 7 | Convergence | `Fig7_Convergence.png` | `Fig10_Convergence.png` |
| — | Four-layer architecture (not in the paper) | `Architecture_overview.png` | `Fig1_Architecture.png` |

---

## Repository structure

```
MC-SDTF/
├── README.md
├── LICENSE                     MIT
├── requirements.txt            pinned versions (Python 3.12)
├── src/
│   ├── experiments.py          30-run campaign, algorithm comparison, scalability, tables, figures
│   ├── metrics.py              knee point, HV, IGD, confidence intervals
│   ├── config.py               case-study parameters (Tables 2–4)
│   ├── objectives.py           objective and constraint functions
│   ├── optimizer.py            NSGA-II (pymoo) and the single-run optimizer
│   ├── visualizations.py       Figures 2–7
│   ├── P02_sensor_node.py      Figure 1
│   ├── P01_architecture.py     architecture overview
│   ├── analysis.py             discussion analyses (single-run pipeline)
│   └── main.py                 single-run pipeline (one seed per domain)
├── results/
│   ├── data/                   CSV results of the campaign (see above)
│   └── figures/                Figures 1–7, plus previous_release/
└── docs/
    ├── equations.md            mathematical formulation
    └── execution_guide.md      step-by-step instructions
```

`src/main.py` is the original single-run pipeline (one NSGA-II run per domain, seed 42, output
to `output/`). It is useful for exploring parameter changes; the paper's statistics come from
`src/experiments.py`.

---

## Dependencies

Pinned in `requirements.txt`: pymoo 0.6.1.6, NumPy 2.4.6, SciPy 1.17.1, matplotlib 3.10.9,
psutil 7.2.2, on Python 3.12.

---

## Citation

If you use this framework or data, please cite:

```bibtex
@inproceedings{berjis2026mcsdtf,
  author    = {Berjis, Zaid H. and Ameen, Siddeeq Y. and AL Jammas, Mohammed H.},
  title     = {A Multi-Objective Optimization-Based Digital Twin Framework for Energy
               Reliability and Sustainability in Mission-Critical {IoT} Systems},
  booktitle = {Proceedings of ICSSD2026},
  year      = {2026},
  note      = {Paper EE-18 (ICSSD-424)},
  url       = {https://github.com/zaidcpp404/MC-SDTF}
}
```

---

## License

MIT; see [LICENSE](LICENSE).
