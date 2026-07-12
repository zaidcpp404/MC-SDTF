# MC-SDTF Execution Guide

Step-by-step instructions to reproduce all results from the paper.

---

## Prerequisites

- **Python** 3.9 or later (3.12 recommended)
- **RAM:** 4 GB minimum, 16 GB recommended
- **CPU:** Any modern multi-core processor
- **Disk:** 100 MB free space
- **OS:** Linux, macOS, or Windows

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/MC-SDTF.git
cd MC-SDTF

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Execution Phases

### Phase 1: Quick Verification (~2-5 minutes)

Verify everything works with a small run:

```bash
cd src
python main.py --quick
```

This runs NSGA-II with population=50 and 50 generations — enough to confirm the pipeline works end-to-end.

### Phase 2: Standard Run (~15-30 minutes)

```bash
python main.py
```

Uses population=200, 300 generations. Produces good-quality Pareto fronts suitable for analysis.

### Phase 3: Full Paper-Quality Run (~1-3 hours)

```bash
python main.py --full
```

Uses population=200, 500 generations — matches the settings reported in the paper.

---

## What Each Phase Produces

The pipeline executes 5 phases automatically:

| Phase | What It Does | Paper Section |
|-------|-------------|---------------|
| 1. Setup | Prints environment spec, parameter tables | Section V.A, Tables II-IV |
| 2. Diagrams | Generates architecture + sensor node figures | Figs. 1-2 |
| 3. Optimization | Runs NSGA-II for all 3 case studies | — |
| 4. Figures | Generates Pareto fronts, comparison, convergence | Figs. 6-10, Tables V-VIII |
| 5. Analysis | Prints overhead, findings, conclusion numbers | Sections VI-VII |

---

## Output Files

All outputs are saved to `src/output/`:

| File | Description |
|------|-------------|
| `Fig1_Architecture.png/pdf` | Four-layer architecture diagram |
| `Fig2_SensorNode.png/pdf` | Sensor node block diagram |
| `Fig6_industrial_Pareto.png/pdf` | Industrial Pareto front |
| `Fig7_smartcity_Pareto.png/pdf` | Smart City Pareto front |
| `Fig8_healthcare_Pareto.png/pdf` | Healthcare Pareto front |
| `Fig9_CrossDomain.png/pdf` | Cross-domain comparison |
| `Fig10_Convergence.png/pdf` | Convergence analysis |
| `Fig_SensitivityAnalysis.png/pdf` | Sensitivity analysis |
| `MCSDTF_Results_industrial.pkl` | Industrial optimization data |
| `MCSDTF_Results_smartcity.pkl` | Smart City optimization data |
| `MCSDTF_Results_healthcare.pkl` | Healthcare optimization data |
| `MCSDTF_AllResults.pkl` | Combined results |

---

## Running Individual Case Studies

```bash
# Run only industrial
python optimizer.py industrial 200 500

# Run only smart city
python optimizer.py smartcity 200 500

# Run only healthcare
python optimizer.py healthcare 200 500

# Run all three
python optimizer.py all 200 500
```

---

## Regenerating Figures Only

If you already have results (`.pkl` files in `output/`):

```bash
python main.py --figures-only
```

---

## Customizing Parameters

Edit `config.py` to modify case study parameters:

```python
# Example: relax industrial availability to 99.9%
params.A_min = 0.999

# Example: increase budget
params.budget = 750000

# Example: change grid carbon intensity
params.gamma_grid = 0.50
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Out of memory | Reduce `--pop` to 100 or `--gen` to 200 |
| Slow convergence | Increase `--gen` to 1000 |
| Too few Pareto points | Increase `--pop` to 300 or relax `A_min` |
| Import errors | Run `pip install -r requirements.txt` |
| `pymoo` not found | Run `pip install pymoo` |

---

## File-to-Paper Mapping

| Source File | Paper Element |
|-------------|---------------|
| `config.py` | Tables II, III, IV (case study parameters) |
| `objectives.py` | Section III.C (Eqs. 3-30) |
| `optimizer.py` | Section III.C.4 (NSGA-II setup, Listing 1) |
| `P01_architecture.py` | Fig. 1 |
| `P02_sensor_node.py` | Fig. 2 |
| `visualizations.py` | Figs. 6-10, Tables V-VIII |
| `analysis.py` | Sections V.A, VI.C, VI.A, VII |
| `main.py` | Orchestrates all of the above |
