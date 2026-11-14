#!/usr/bin/env python3
"""
MC-SDTF Experiment Campaign (ICSSD2026 paper, Sections 5.1-5.6)
================================================================
Runs every experiment behind the paper's tables and figures and writes the
results as plain CSV files to ``results/data/``.

Stages
------
  nsga2        30 seeded NSGA-II runs per domain (industrial, smartcity, healthcare)
  compare      NSGA-III and MOEA/D on the industrial case, same budget and seeds
  scalability  NSGA-II on synthetic industrial deployments with N = 1,000 / 2,500 / 5,000
  analyze      HV, IGD, 95% CIs, Wilcoxon tests, knee points -> CSV tables
  figures      Figures 1-7 of the paper, drawn from the CSV files
  all          every stage above, in that order

Each finished run is cached in ``output/runs/`` (one .npz per run), so an
interrupted campaign resumes where it stopped. ``analyze`` and ``figures`` need
only the cache (or, for ``figures``, only ``results/data/``).

Examples (run from the repository root)
---------------------------------------
  python src/experiments.py all                  # full campaign
  python src/experiments.py nsga2 --domains industrial
  python src/experiments.py analyze figures      # rebuild tables and figures
  python src/experiments.py all --quick          # 2-minute smoke test (output/quick/)
"""

import argparse
import csv
import json
import os
import platform
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))

import matplotlib  # noqa: E402

matplotlib.use("Agg")

from pymoo.algorithms.moo.moead import MOEAD  # noqa: E402
from pymoo.algorithms.moo.nsga3 import NSGA3  # noqa: E402
from pymoo.core.callback import Callback  # noqa: E402
from pymoo.decomposition.tchebicheff import Tchebicheff  # noqa: E402
from pymoo.operators.crossover.sbx import SBX  # noqa: E402
from pymoo.operators.mutation.pm import PM  # noqa: E402
from pymoo.operators.sampling.rnd import FloatRandomSampling  # noqa: E402
from pymoo.optimize import minimize  # noqa: E402
from pymoo.util.ref_dirs import get_reference_directions  # noqa: E402
from scipy.stats import ranksums  # noqa: E402

from config import ALL_CASE_STUDIES  # noqa: E402
from metrics import (CONFIG_LABELS, OBJECTIVE_NAMES, VARIABLE_NAMES,  # noqa: E402
                     FrontQuality, key_points, knee_reductions, mean_ci95,
                     nondominated)
from optimizer import MCSDTFProblem, build_nsga2, make_repair  # noqa: E402

REPO = SRC.parent
DOMAINS = ["industrial", "smartcity", "healthcare"]
DOMAIN_LABELS = {"industrial": "Industrial", "smartcity": "Smart City", "healthcare": "Healthcare"}
ALGORITHMS = ["nsga2", "nsga3", "moead"]
ALGO_LABELS = {"nsga2": "NSGA-II", "nsga3": "NSGA-III", "moead": "MOEA/D"}

# Paper settings (Section 5.1)
POP_SIZE = 200
N_GEN = 500
N_RUNS = 30
SCALE_SIZES = [1000, 2500, 5000]
SCALE_RUNS = 5
MOEAD_PENALTY = 1e6      # constraint-violation penalty for MOEA/D (see README)
HV_STRIDE = 5            # generations between HV/IGD samples on the convergence curve


class Paths:
    """Where runs, data and figures go. Only the default configuration (full
    settings, repair="all") writes to results/; everything else goes to output/."""

    def __init__(self, quick: bool, repair: str = "all"):
        self.repair = repair
        out = REPO / "output"
        if repair != "all":
            out = out / f"{repair}_repair"
        if quick:
            out = out / "quick"
        self.raw = out / "runs"
        if quick or repair != "all":
            self.data, self.figs = out / "data", out / "figures"
        else:
            self.data, self.figs = REPO / "results" / "data", REPO / "results" / "figures"


# ---------------------------------------------------------------------------
# Problem, algorithms, single run
# ---------------------------------------------------------------------------

class TimedProblem(MCSDTFProblem):
    """MCSDTFProblem that also records the time spent evaluating objectives."""

    def __init__(self, params):
        super().__init__(params)
        self.eval_time = 0.0
        self.n_evals = 0

    def _evaluate(self, X, out, *args, **kwargs):
        t = time.perf_counter()
        super()._evaluate(X, out, *args, **kwargs)
        self.eval_time += time.perf_counter() - t
        self.n_evals += X.shape[0]


class PenalizedProblem(TimedProblem):
    """Static-penalty version of the problem for MOEA/D, which in pymoo does not
    accept constrained problems: every objective is increased by
    MOEAD_PENALTY x (sum of positive constraint violations). pymoo's own
    ConstraintsAsPenalty cannot be used here because in pymoo 0.6.1.6 it fails
    for problems with more than one objective."""

    def __init__(self, params, penalty):
        super().__init__(params)
        self.penalty = penalty
        self.n_ieq_constr = 0

    def _evaluate(self, X, out, *args, **kwargs):
        super()._evaluate(X, out, *args, **kwargs)
        cv = np.maximum(out.pop("G"), 0.0).sum(axis=1)
        out["F"] = out["F"] + self.penalty * cv[:, None]


class FrontHistory(Callback):
    """Stores the feasible non-dominated set after every generation."""

    def __init__(self):
        super().__init__()
        self.fronts = []

    def notify(self, algorithm):
        opt = algorithm.opt
        F, feas = opt.get("F"), opt.get("feas")
        self.fronts.append(F[feas].copy() if feas is not None else np.empty((0, 4)))


@lru_cache(maxsize=None)
def _ref_dirs(n_obj: int, n_points: int) -> np.ndarray:
    return get_reference_directions("energy", n_obj, n_points, seed=1)


def build_algorithm(name: str, pop_size: int, repair: str = "all"):
    if name == "nsga2":
        return build_nsga2(pop_size, repair)
    operators = dict(
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.8, eta=15, repair=make_repair(repair)),
        mutation=PM(eta=20, repair=make_repair(repair)),
    )
    ref_dirs = _ref_dirs(4, pop_size)
    if name == "nsga3":
        return NSGA3(ref_dirs=ref_dirs, pop_size=pop_size, eliminate_duplicates=True, **operators)
    if name == "moead":
        return MOEAD(ref_dirs=ref_dirs, decomposition=Tchebicheff(), **operators)
    raise ValueError(name)


def make_params(domain: str, n_nodes=None):
    params = ALL_CASE_STUDIES[domain]()
    if n_nodes is not None:
        params.n_nodes = int(n_nodes)
    return params


def run_tag(algo, domain, n_nodes=None):
    return f"{algo}_{domain}" + (f"_N{n_nodes}" if n_nodes else "")


def run_file(paths, algo, domain, seed, n_nodes=None):
    return paths.raw / run_tag(algo, domain, n_nodes) / f"seed_{seed:02d}.npz"


def run_one(algo, domain, seed, pop_size, n_gen, paths, n_nodes=None, history=False):
    """One optimization run. Saves the final feasible non-dominated front."""
    path = run_file(paths, algo, domain, seed, n_nodes)
    if path.exists():
        with np.load(path) as z:
            if int(z["pop_size"]) == pop_size and int(z["n_gen"]) == n_gen:
                return path
    params = make_params(domain, n_nodes)
    problem = PenalizedProblem(params, MOEAD_PENALTY) if algo == "moead" else TimedProblem(params)
    algorithm = build_algorithm(algo, pop_size, paths.repair)
    cb = FrontHistory() if history else None

    t0 = time.perf_counter()
    kwargs = {"callback": cb} if cb is not None else {}
    res = minimize(problem, algorithm, ("n_gen", n_gen), seed=seed, verbose=False, **kwargs)
    wall = time.perf_counter() - t0

    # Final front: feasible, non-dominated members of the final population,
    # re-evaluated on the unpenalized problem (identical to res.opt for NSGA-II/III).
    X = res.pop.get("X").copy()
    for j in problem.integer_vars:
        X[:, j] = np.round(X[:, j])
    out = MCSDTFProblem(params).evaluate(X, return_values_of=["F", "G"], return_as_dictionary=True)
    F, G = out["F"], out["G"]
    feas = np.all(G <= 0, axis=1)
    idx = np.flatnonzero(feas)[nondominated(F[feas])] if feas.any() else np.array([], dtype=int)
    order = idx[np.argsort(F[idx, 0])] if len(idx) else idx

    save = dict(X=X[order], F=F[order], wall=wall, eval_time=problem.eval_time,
                n_evals=problem.n_evals, seed=seed, pop_size=pop_size, n_gen=n_gen,
                n_nodes=params.n_nodes)
    if algo in ("nsga2", "nsga3") and res.opt is not None and res.F is not None:
        save["n_opt_pymoo"] = len(res.F)
    if cb is not None:
        sizes = np.array([len(f) for f in cb.fronts])
        save["hist_sizes"] = sizes
        save["hist_F"] = np.vstack(cb.fronts) if sizes.sum() else np.empty((0, 4))
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **save)
    return path


def load_run(path):
    with np.load(path) as z:
        d = {k: z[k] for k in z.files}
    for k in ("wall", "eval_time", "n_evals", "seed", "pop_size", "n_gen", "n_nodes"):
        d[k] = d[k].item()
    if "hist_sizes" in d:
        off = np.concatenate([[0], np.cumsum(d["hist_sizes"])])
        d["hist_fronts"] = [d["hist_F"][off[i]:off[i + 1]] for i in range(len(d["hist_sizes"]))]
    return d


def _job(args):
    algo, domain, seed, pop, gen, paths, n_nodes, history = args
    t = time.perf_counter()
    run_one(algo, domain, seed, pop, gen, paths, n_nodes, history)
    return algo, domain, n_nodes, seed, time.perf_counter() - t


def run_batch(jobs, n_workers):
    todo = [j for j in jobs if not _cached(j)]
    print(f"  {len(jobs) - len(todo)} cached, {len(todo)} to run", flush=True)
    if not todo:
        return
    t0 = time.perf_counter()
    if n_workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(n_workers) as ex:
            for i, r in enumerate(ex.map(_job, todo), 1):
                _report(i, len(todo), r, t0)
    else:
        for i, j in enumerate(todo, 1):
            _report(i, len(todo), _job(j), t0)


def _cached(job):
    algo, domain, seed, pop, gen, paths, n_nodes, _ = job
    p = run_file(paths, algo, domain, seed, n_nodes)
    if not p.exists():
        return False
    with np.load(p) as z:
        return int(z["pop_size"]) == pop and int(z["n_gen"]) == gen


def _report(i, n, r, t0):
    algo, domain, n_nodes, seed, dt = r
    tag = run_tag(algo, domain, n_nodes)
    el = time.perf_counter() - t0
    print(f"  [{i:3d}/{n}] {tag:<26s} seed {seed:2d}  {dt:6.1f} s   elapsed {el / 60:6.1f} min",
          flush=True)


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def stage_nsga2(cfg, paths):
    print("\n== NSGA-II: independent runs per domain ==")
    jobs = [("nsga2", d, s, cfg.pop, cfg.gen, paths, None, True)
            for d in cfg.domains for s in range(1, cfg.runs + 1)]
    run_batch(jobs, cfg.jobs)


def stage_compare(cfg, paths):
    print("\n== Algorithm comparison (industrial): NSGA-III and MOEA/D ==")
    jobs = [(a, "industrial", s, cfg.pop, cfg.gen, paths, None, False)
            for a in ("nsga3", "moead") for s in range(1, cfg.runs + 1)]
    run_batch(jobs, cfg.jobs)


def stage_scalability(cfg, paths):
    print("\n== Scalability: synthetic industrial deployments ==")
    jobs = [("nsga2", "industrial", s, cfg.pop, cfg.gen, paths, n, False)
            for n in cfg.sizes for s in range(1, cfg.scale_runs + 1)]
    run_batch(jobs, cfg.jobs)


def _runs(paths, algo, domain, n_nodes=None, n_runs=None):
    d = paths.raw / run_tag(algo, domain, n_nodes)
    files = sorted(d.glob("seed_*.npz")) if d.exists() else []
    runs = [load_run(f) for f in files]
    if n_runs is not None:
        runs = [r for r in runs if r["seed"] <= n_runs]
    return runs


def _write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow([_fmt(v) for v in row])
    print(f"  wrote {path.relative_to(REPO)}")


def _fmt(v):
    if isinstance(v, (float, np.floating)):
        return "" if not np.isfinite(v) else repr(float(v))
    if isinstance(v, np.integer):
        return int(v)
    return v


def _front_rows(X, F, extra=()):
    for x, f in zip(X, F):
        yield list(extra) + [100.0 * -f[0]] + list(f) + [int(round(x[0]))] + list(x[1:5]) \
            + [int(round(x[5])), x[6], int(round(x[7]))]


FRONT_HEADER = ["availability_pct"] + OBJECTIVE_NAMES + VARIABLE_NAMES


def stage_analyze(cfg, paths):
    print("\n== Analysis: HV, IGD, confidence intervals, tables ==")
    data = paths.data
    per_run = []          # rows of runs_metrics.csv
    quality = {}          # domain -> dict of lists
    reps = {}             # domain -> representative run
    conv_rows = []

    for domain in DOMAINS:
        runs = _runs(paths, "nsga2", domain, n_runs=cfg.runs)
        runs = [r for r in runs if r["pop_size"] == cfg.pop and r["n_gen"] == cfg.gen]
        if not runs:
            print(f"  (no NSGA-II runs for {domain}; skipped)")
            continue
        fronts = [r["F"] for r in runs if len(r["F"])]
        fq = FrontQuality(fronts)
        q = {k: [] for k in ("hv", "igd", "size", "wall", "eval", "e_red", "c_red")}
        for r in runs:
            F = r["F"]
            hv, igd = fq.hv(F), fq.igd(F)
            e_red, c_red = knee_reductions(F) if len(F) else (np.nan, np.nan)
            r.update(hv=hv, igd=igd, e_red=e_red, c_red=c_red)
            for k, v in zip(q, (hv, igd, len(F), r["wall"], r["eval_time"], e_red, c_red)):
                q[k].append(v)
            per_run.append(["domain_campaign", "NSGA-II", domain, r["n_nodes"], r["seed"], r["seed"],
                            len(F), hv, igd, f"{domain}: NSGA-II, {len(runs)} runs",
                            e_red, c_red, r["wall"], r["eval_time"], r["n_evals"]])
        quality[domain] = q

        # Representative run: the run with the median HV (lower median for even counts).
        order = np.argsort([r["hv"] for r in runs])
        rep = runs[order[(len(runs) - 1) // 2]]
        reps[domain] = rep

        # Pareto-front files
        _write_csv(data / f"pareto_front_{domain}.csv",
                   ["seed", "solution", "configuration"] + FRONT_HEADER,
                   _rep_rows(rep))
        _write_csv(data / f"pareto_fronts_all_runs_{domain}.csv",
                   ["run", "seed", "solution"] + FRONT_HEADER,
                   (row for r in runs for row in _indexed_rows(r)))
        # Combined-best reference front (IGD reference), with the seed each point came from
        allX = np.vstack([r["X"] for r in runs if len(r["F"])])
        allF = np.vstack(fronts)
        src = np.concatenate([[r["seed"]] * len(r["F"]) for r in runs if len(r["F"])])
        ref = fq.ref_idx[np.argsort(fq.ref_front[:, 0])]
        _write_csv(data / f"reference_front_{domain}.csv",
                   ["source_seed"] + FRONT_HEADER,
                   ([s] + row for s, row in zip(src[ref], _front_rows(allX[ref], allF[ref]))))

        # Convergence (front size every generation, HV/IGD every HV_STRIDE generations)
        hist = [r for r in runs if "hist_sizes" in r]
        if hist:
            n_gen = min(len(r["hist_sizes"]) for r in hist)
            for g in range(n_gen):
                sizes = [r["hist_sizes"][g] for r in hist]
                m, h = mean_ci95(sizes)
                row = [domain, g + 1, m, h, min(sizes), max(sizes)]
                if (g + 1) % HV_STRIDE == 0 or g == 0:
                    hvs = [fq.hv(r["hist_fronts"][g]) if len(r["hist_fronts"][g]) else 0.0 for r in hist]
                    igds = [fq.igd(r["hist_fronts"][g]) if len(r["hist_fronts"][g]) else np.nan
                            for r in hist]
                    row += [*mean_ci95(hvs), *mean_ci95(igds)]
                else:
                    row += [np.nan] * 4
                conv_rows.append(row)

    if not quality:
        print("  nothing to analyze")
        return

    _write_csv(data / "convergence.csv",
               ["domain", "generation", "front_size_mean", "front_size_ci95", "front_size_min",
                "front_size_max", "hv_mean", "hv_ci95", "igd_mean", "igd_ci95"], conv_rows)

    # Section 5.6 summary: HV, IGD, front size, runtime (mean +- 95% CI)
    rows = []
    for d, q in quality.items():
        rows.append([d, len(q["hv"]), *mean_ci95(q["hv"]), *mean_ci95(q["igd"]),
                     *mean_ci95(q["size"]), *mean_ci95(q["wall"]), *mean_ci95(q["eval"]),
                     _hv_plateau(conv_rows, d)])
    _write_csv(data / "quality_metrics_summary.csv",
               ["domain", "n_runs", "hv_mean", "hv_ci95", "igd_mean", "igd_ci95",
                "front_size_mean", "front_size_ci95", "runtime_s_mean", "runtime_s_ci95",
                "eval_time_s_mean", "eval_time_s_ci95", "generation_mean_hv_reaches_99pct_of_final"],
               rows)

    # Key results: knee-point reductions
    rows = []
    for d, q in quality.items():
        e_rep, c_rep = knee_reductions(reps[d]["F"])
        rows.append([d, reps[d]["seed"], e_rep, c_rep, *mean_ci95(q["e_red"]), *mean_ci95(q["c_red"])])
    _write_csv(data / "key_results_knee_reductions.csv",
               ["domain", "representative_seed", "energy_reduction_pct_representative",
                "carbon_reduction_pct_representative", "energy_reduction_pct_mean",
                "energy_reduction_pct_ci95", "carbon_reduction_pct_mean", "carbon_reduction_pct_ci95"],
               rows)

    # Tables 5-7 (representative run) and their 30-run means
    table_no = {"industrial": 5, "smartcity": 6, "healthcare": 7}
    ci_rows = []
    for d in quality:
        rep = reps[d]
        kp = key_points(rep["F"])
        _write_csv(data / f"table{table_no[d]}_{d}.csv",
                   ["configuration", "seed", "solution"] + FRONT_HEADER,
                   ([lab, rep["seed"], kp[lab]] + next(_front_rows(rep["X"][[kp[lab]]], rep["F"][[kp[lab]]]))
                    for lab in CONFIG_LABELS))
        runs = [r for r in _runs(paths, "nsga2", d, n_runs=cfg.runs) if len(r["F"])]
        for lab in CONFIG_LABELS:
            vals = {"availability_pct": [], "energy_kWh_per_yr": [], "carbon_kgCO2e_per_yr": [],
                    "mrt_s": [], "r": []}
            for r in runs:
                i = key_points(r["F"])[lab]
                f, x = r["F"][i], r["X"][i]
                for k, v in zip(vals, (-100 * f[0], f[1], f[2], f[3], round(x[0]))):
                    vals[k].append(v)
            for k, v in vals.items():
                ci_rows.append([d, lab, k, len(v), *mean_ci95(v)])
    _write_csv(data / "tables5to7_mean_ci95_over_runs.csv",
               ["domain", "configuration", "quantity", "n_runs", "mean", "ci95"], ci_rows)

    # Table 8: cross-domain comparison
    rows = []
    for d, q in quality.items():
        F = reps[d]["F"]
        av = -100 * F[:, 0]
        e_ranges = [np.ptp(r["F"][:, 1]) if len(r["F"]) else np.nan
                    for r in _runs(paths, "nsga2", d, n_runs=cfg.runs)]
        rows.append([d, reps[d]["seed"], av.min(), av.max(), np.ptp(F[:, 1]), len(F),
                     *mean_ci95(q["size"]), *mean_ci95(e_ranges), *mean_ci95(q["wall"])])
    _write_csv(data / "table8_cross_domain.csv",
               ["domain", "representative_seed", "availability_min_pct", "availability_max_pct",
                "energy_range_kWh", "pareto_size", "pareto_size_mean", "pareto_size_ci95",
                "energy_range_kWh_mean", "energy_range_kWh_ci95", "runtime_s_mean", "runtime_s_ci95"],
               rows)

    # Table 9: algorithm comparison on the industrial case
    comp = {a: [r for r in _runs(paths, a, "industrial", n_runs=cfg.runs)
                if r["pop_size"] == cfg.pop and r["n_gen"] == cfg.gen] for a in ALGORITHMS}
    if all(comp.values()):
        fq = FrontQuality([r["F"] for a in ALGORITHMS for r in comp[a] if len(r["F"])])
        res = {}
        rows = []
        for a in ALGORITHMS:
            hv = [fq.hv(r["F"]) for r in comp[a]]
            igd = [fq.igd(r["F"]) for r in comp[a]]
            size = [len(r["F"]) for r in comp[a]]
            wall = [r["wall"] for r in comp[a]]
            res[a] = dict(hv=hv, igd=igd)
            rows.append([ALGO_LABELS[a], len(hv), *mean_ci95(hv), *mean_ci95(igd), *mean_ci95(size),
                         *mean_ci95(wall), sum(1 for s in size if s == 0)])
            for r, h, i in zip(comp[a], hv, igd):
                per_run.append(["algorithm_comparison", ALGO_LABELS[a], "industrial", r["n_nodes"],
                                r["seed"], r["seed"], len(r["F"]), h, i,
                                "industrial: NSGA-II + NSGA-III + MOEA/D pooled",
                                *(knee_reductions(r["F"]) if len(r["F"]) else (np.nan, np.nan)),
                                r["wall"], r["eval_time"], r["n_evals"]])
        _write_csv(data / "table9_algorithm_comparison.csv",
                   ["algorithm", "n_runs", "hv_mean", "hv_ci95", "igd_mean", "igd_ci95",
                    "front_size_mean", "front_size_ci95", "runtime_s_mean", "runtime_s_ci95",
                    "runs_without_feasible_solution"], rows)
        rows = []
        for b in ("nsga3", "moead"):
            for m in ("hv", "igd"):
                x = np.array(res["nsga2"][m]), np.array(res[b][m])
                x = [v[np.isfinite(v)] for v in x]
                stat, p = ranksums(x[0], x[1])
                rows.append([m, "NSGA-II", ALGO_LABELS[b], len(x[0]), len(x[1]), stat, p])
        _write_csv(data / "wilcoxon_ranksum_tests.csv",
                   ["metric", "algorithm_a", "algorithm_b", "n_a", "n_b", "statistic", "p_value_two_sided"],
                   rows)
        for a in ("nsga3", "moead"):
            _write_csv(data / f"pareto_fronts_all_runs_industrial_{a}.csv",
                       ["run", "seed", "solution"] + FRONT_HEADER,
                       (row for r in comp[a] for row in _indexed_rows(r)))
    else:
        print("  (algorithm comparison incomplete; Table 9 skipped)")

    # Scalability
    rows = []
    base = _runs(paths, "nsga2", "industrial", n_runs=cfg.runs)
    for n, runs in [(500, base)] + [(n, _runs(paths, "nsga2", "industrial", n, cfg.scale_runs))
                                    for n in cfg.sizes]:
        runs = [r for r in runs if r["pop_size"] == cfg.pop and r["n_gen"] == cfg.gen]
        if not runs:
            continue
        wall = [r["wall"] for r in runs]
        ev = [r["eval_time"] for r in runs]
        ovh = [r["wall"] - r["eval_time"] for r in runs]
        per_call = [1e6 * r["eval_time"] / r["n_evals"] for r in runs]
        size = [len(r["F"]) for r in runs]
        rows.append([n, len(runs), *mean_ci95(wall), *mean_ci95(ev), *mean_ci95(ovh),
                     *mean_ci95(per_call), *mean_ci95(size), sum(1 for s in size if s == 0)])
        if n != 500:
            for r in runs:
                per_run.append(["scalability", "NSGA-II", "industrial", n, r["seed"], r["seed"],
                                len(r["F"]), np.nan, np.nan, "",
                                *(knee_reductions(r["F"]) if len(r["F"]) else (np.nan, np.nan)),
                                r["wall"], r["eval_time"], r["n_evals"]])
    _write_csv(data / "scalability.csv",
               ["n_nodes", "n_runs", "runtime_s_mean", "runtime_s_ci95", "eval_time_s_mean",
                "eval_time_s_ci95", "optimizer_overhead_s_mean", "optimizer_overhead_s_ci95",
                "eval_time_per_solution_us_mean", "eval_time_per_solution_us_ci95",
                "front_size_mean", "front_size_ci95", "runs_without_feasible_solution"], rows)

    _write_csv(data / "runs_metrics.csv",
               ["experiment", "algorithm", "domain", "n_nodes", "run", "seed", "front_size", "hv", "igd",
                "hv_igd_reference_set", "knee_energy_reduction_pct", "knee_carbon_reduction_pct",
                "runtime_s", "eval_time_s", "n_evaluations"], per_run)

    _write_environment(data, cfg, per_run)
    _write_summary(data)


def _indexed_rows(r):
    for i, row in enumerate(_front_rows(r["X"], r["F"])):
        yield [r["seed"], r["seed"], i] + row


def _rep_rows(rep):
    kp = key_points(rep["F"]) if len(rep["F"]) else {}
    inv = {}
    for lab, i in kp.items():
        inv.setdefault(i, []).append(lab)
    for i, row in enumerate(_front_rows(rep["X"], rep["F"])):
        yield [rep["seed"], i, "; ".join(inv.get(i, []))] + row


def _hv_plateau(conv_rows, domain):
    pts = [(r[1], r[6]) for r in conv_rows if r[0] == domain and np.isfinite(r[6])]
    if not pts:
        return np.nan
    final = pts[-1][1]
    for g, hv in pts:
        if hv >= 0.99 * final:
            return g
    return np.nan


def _write_environment(data, cfg, per_run):
    import matplotlib as mpl
    import numpy as _np
    import psutil
    import pymoo
    import scipy
    env = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_physical_cores": psutil.cpu_count(logical=False),
        "cpu_logical_cores": psutil.cpu_count(),
        "ram_GB": round(psutil.virtual_memory().total / 1e9, 1),
        "packages": {"pymoo": pymoo.__version__, "numpy": _np.__version__, "scipy": scipy.__version__,
                     "matplotlib": mpl.__version__},
        "settings": {"repair": cfg.repair, "pop_size": cfg.pop, "n_gen": cfg.gen, "runs": cfg.runs,
                     "scalability_sizes": cfg.sizes, "scalability_runs": cfg.scale_runs,
                     "seeds": f"1..{cfg.runs}", "moead_penalty": MOEAD_PENALTY,
                     "parallel_workers": cfg.jobs},
        "total_optimization_wall_time_s": float(sum(r[12] for r in per_run
                                                    if not (r[0] == "algorithm_comparison"
                                                            and r[1] == "NSGA-II"))),
        "generated": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }
    with open(data / "environment.json", "w") as f:
        json.dump(env, f, indent=2)
    print(f"  wrote {(data / 'environment.json').relative_to(REPO)}")


def _read_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def _pm(row, key, nd):
    m, h = row[f"{key}_mean"], row.get(f"{key}_ci95", "")
    if m == "":
        return "n/a"
    s = f"{float(m):.{nd}f}"
    return s + (f" ± {float(h):.{nd}f}" if h != "" else "")


def _write_summary(data):
    """SUMMARY.md: the CSV results formatted as readable tables (generated, not hand-written)."""
    L = ["# Results summary", "",
         "Generated by `python src/experiments.py analyze` from the CSV files in this folder. "
         "Do not edit by hand. Values are mean ± half-width of the 95% Student-t confidence "
         "interval over independent seeded runs unless marked otherwise.", ""]
    env = json.load(open(data / "environment.json"))
    L += [f"Environment: Python {env['python']}, pymoo {env['packages']['pymoo']}, "
          f"NumPy {env['packages']['numpy']}, SciPy {env['packages']['scipy']}, "
          f"matplotlib {env['packages']['matplotlib']}; {env['platform']}, "
          f"{env['cpu_logical_cores']} logical cores, {env['ram_GB']} GB RAM; "
          f"{env['settings']['parallel_workers']} run(s) in parallel. "
          f"Total optimization time: {env['total_optimization_wall_time_s'] / 3600:.2f} h.", ""]

    q = _read_csv(data / "quality_metrics_summary.csv")
    L += ["## Pareto-front quality (Section 5.6)", "",
          "| Domain | Runs | HV | IGD | Front size | Runtime per run (s) | Gen. where mean HV reaches 99% of final |",
          "|:--|--:|:-:|:-:|:-:|:-:|--:|"]
    for r in q:
        L.append(f"| {DOMAIN_LABELS[r['domain']]} | {r['n_runs']} | {_pm(r, 'hv', 3)} | {_pm(r, 'igd', 3)} | "
                 f"{_pm(r, 'front_size', 1)} | {_pm(r, 'runtime_s', 1)} | "
                 f"{r['generation_mean_hv_reaches_99pct_of_final']} |")
    k = _read_csv(data / "key_results_knee_reductions.csv")
    L += ["", "## Knee-point reductions vs. max-reliability", "",
          "| Domain | Energy, representative run (%) | Carbon, representative run (%) | Energy, all runs (%) | Carbon, all runs (%) |",
          "|:--|:-:|:-:|:-:|:-:|"]
    for r in k:
        L.append(f"| {DOMAIN_LABELS[r['domain']]} | {float(r['energy_reduction_pct_representative']):.1f} | "
                 f"{float(r['carbon_reduction_pct_representative']):.1f} | "
                 f"{_pm({'x_mean': r['energy_reduction_pct_mean'], 'x_ci95': r['energy_reduction_pct_ci95']}, 'x', 1)} | "
                 f"{_pm({'x_mean': r['carbon_reduction_pct_mean'], 'x_ci95': r['carbon_reduction_pct_ci95']}, 'x', 1)} |")
    for d, n in (("industrial", 5), ("smartcity", 6), ("healthcare", 7)):
        p = data / f"table{n}_{d}.csv"
        if not p.exists():
            continue
        t = _read_csv(p)
        L += ["", f"## Table {n}: {DOMAIN_LABELS[d]} (representative run, seed {t[0]['seed']})", "",
              "| Configuration | Avail. (%) | Energy (kWh/yr) | CO₂ (kg/yr) | MRT (s) | r | N_gw | ε_h |",
              "|:--|--:|--:|--:|--:|--:|--:|--:|"]
        for r in t:
            L.append(f"| {r['configuration']} | {float(r['availability_pct']):.4f} | "
                     f"{float(r['energy_kWh_per_yr']):,.0f} | {float(r['carbon_kgCO2e_per_yr']):,.0f} | "
                     f"{float(r['mrt_s']):.1f} | {r['r']} | {r['N_gw']} | {r['eps_h']} |")
    p = data / "table8_cross_domain.csv"
    t = _read_csv(p)
    L += ["", "## Table 8: cross-domain comparison (representative runs)", "",
          "| Domain | Avail. min (%) | Avail. max (%) | E range (kWh) | Pareto size | Pareto size, all runs |",
          "|:--|--:|--:|--:|--:|:-:|"]
    for r in t:
        L.append(f"| {DOMAIN_LABELS[r['domain']]} | {float(r['availability_min_pct']):.4f} | "
                 f"{float(r['availability_max_pct']):.4f} | {float(r['energy_range_kWh']):,.0f} | "
                 f"{r['pareto_size']} | {_pm(r, 'pareto_size', 1)} |")
    p = data / "table9_algorithm_comparison.csv"
    if p.exists():
        t = _read_csv(p)
        L += ["", "## Table 9: algorithm comparison (industrial)", "",
              "HV and IGD here use one reference for all three algorithms (bounds and combined-best "
              "front pooled over every run of every algorithm), so the NSGA-II values differ from "
              "the per-domain values above.", "",
              "| Algorithm | Runs | HV | IGD | Front size | Runtime per run (s) |", "|:--|--:|:-:|:-:|:-:|:-:|"]
        for r in t:
            L.append(f"| {r['algorithm']} | {r['n_runs']} | {_pm(r, 'hv', 3)} | {_pm(r, 'igd', 3)} | "
                     f"{_pm(r, 'front_size', 1)} | {_pm(r, 'runtime_s', 1)} |")
        w = _read_csv(data / "wilcoxon_ranksum_tests.csv")
        L += ["", "| Wilcoxon rank-sum | Metric | Statistic | p (two-sided) |", "|:--|:--|--:|--:|"]
        for r in w:
            L.append(f"| {r['algorithm_a']} vs {r['algorithm_b']} | {r['metric'].upper()} | "
                     f"{float(r['statistic']):.3f} | {float(r['p_value_two_sided']):.3g} |")
    p = data / "scalability.csv"
    t = _read_csv(p)
    L += ["", "## Scalability (industrial template, NSGA-II)", "",
          "| N nodes | Runs | Runtime per run (s) | Objective evaluation (s) | Optimizer overhead (s) | µs per evaluation | Front size |",
          "|--:|--:|:-:|:-:|:-:|:-:|:-:|"]
    for r in t:
        L.append(f"| {int(r['n_nodes']):,} | {r['n_runs']} | {_pm(r, 'runtime_s', 1)} | "
                 f"{_pm(r, 'eval_time_s', 1)} | {_pm(r, 'optimizer_overhead_s', 1)} | "
                 f"{_pm(r, 'eval_time_per_solution_us', 1)} | {_pm(r, 'front_size', 1)} |")
    (data / "SUMMARY.md").write_text("\n".join(L) + "\n")
    print(f"  wrote {(data / 'SUMMARY.md').relative_to(REPO)}")


def stage_figures(cfg, paths):
    print("\n== Figures 1-7 ==")
    from P01_architecture import generate_architecture_diagram
    from P02_sensor_node import generate_sensor_node_diagram
    from visualizations import (plot_convergence_runs, plot_cross_domain, plot_pareto_fronts,
                                plot_sensitivity_analysis)
    figs, data = paths.figs, paths.data
    generate_architecture_diagram(str(figs))
    generate_sensor_node_diagram(str(figs))
    results = {}
    for d in DOMAINS:
        p = data / f"pareto_front_{d}.csv"
        if not p.exists():
            print(f"  (missing {p.name}; run analyze first)")
            return
        rows = _read_csv(p)
        F = np.array([[float(r[k]) for k in OBJECTIVE_NAMES] for r in rows])
        X = np.array([[float(r[k]) for k in VARIABLE_NAMES] for r in rows])
        results[d] = {"fitness": F, "solutions": X, "time": float("nan")}
    plot_pareto_fronts(results, str(figs))
    plot_sensitivity_analysis(results, str(figs))
    plot_cross_domain(results, str(figs))
    conv = _read_csv(data / "convergence.csv")
    plot_convergence_runs(conv, str(figs))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

STAGES = {"nsga2": stage_nsga2, "compare": stage_compare, "scalability": stage_scalability,
          "analyze": stage_analyze, "figures": stage_figures}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stages", nargs="+", choices=list(STAGES) + ["all"])
    ap.add_argument("--domains", nargs="+", default=DOMAINS, choices=DOMAINS)
    ap.add_argument("--runs", type=int, default=N_RUNS, help="independent runs (seeds 1..runs)")
    ap.add_argument("--pop", type=int, default=POP_SIZE)
    ap.add_argument("--gen", type=int, default=N_GEN)
    ap.add_argument("--sizes", type=int, nargs="+", default=SCALE_SIZES)
    ap.add_argument("--scale-runs", type=int, default=SCALE_RUNS)
    ap.add_argument("--jobs", type=int, default=1,
                    help="runs executed in parallel (default 1, so per-run times are not inflated by contention)")
    ap.add_argument("--repair", choices=["all", "integer"], default="all",
                    help="rounding repair: 'all' = pymoo RoundingRepair on every variable (the code used "
                         "for the paper, default); 'integer' = round only r, N_gw, eps_h. Non-default "
                         "choices write to output/integer_repair/, never to results/")
    ap.add_argument("--quick", action="store_true",
                    help="smoke test: pop 40, 30 generations, 3 runs, 1 scalability run; writes to output/quick/")
    cfg = ap.parse_args(argv)
    if cfg.quick:
        cfg.pop, cfg.gen, cfg.runs, cfg.scale_runs = 40, 30, 3, 1
    paths = Paths(cfg.quick, cfg.repair)
    stages = list(STAGES) if "all" in cfg.stages else cfg.stages
    print(f"MC-SDTF experiments: stages={stages} pop={cfg.pop} gen={cfg.gen} runs={cfg.runs} "
          f"jobs={cfg.jobs} -> {paths.data.relative_to(REPO)}")
    t0 = time.perf_counter()
    for s in stages:
        ts = time.perf_counter()
        STAGES[s](cfg, paths)
        print(f"  stage '{s}' finished in {(time.perf_counter() - ts) / 60:.1f} min", flush=True)
    print(f"\nDone in {(time.perf_counter() - t0) / 60:.1f} min.")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONHASHSEED", "0")
    main()
