"""
MC-SDTF Multi-Objective Optimizer (NSGA-II via pymoo)
=====================================================
Equivalent to P03_gamultiobj_Config.m using gamultiobj.
Uses pymoo's NSGA-II implementation with mixed-integer variables.
"""

import numpy as np
import time
import pickle
from pathlib import Path

from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.core.repair import Repair
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.termination import get_termination
from pymoo.optimize import minimize as pymoo_minimize
from pymoo.core.mixed import MixedVariableGA

from config import CaseStudyParams, ALL_CASE_STUDIES
from objectives import evaluate_objectives, evaluate_constraints


class MCSDTFProblem(Problem):
    """
    pymoo Problem definition for MC-SDTF optimization.

    Decision vector: [r, d, p_tx, f_s, alpha, N_gw, T_m, eps_h]
    Objectives: 4 (f1..f4, all minimized)
    Constraints: 3 inequality (g <= 0)
    """

    def __init__(self, params: CaseStudyParams):
        self.params = params

        #            r     d      p_tx   f_s    alpha  N_gw                    T_m    eps_h
        xl = np.array([1,  0.01,  0,     0.1,   0.0,   params.n_gateways_range[0], 168,   0])
        xu = np.array([3,  1.0,   20,    100,   1.0,   params.n_gateways_range[1], 4380,  3])

        super().__init__(
            n_var=8,
            n_obj=4,
            n_ieq_constr=3,
            xl=xl,
            xu=xu,
        )

        # Integer variable indices: r (0), N_gw (5), eps_h (7)
        self.integer_vars = [0, 5, 7]

    def _evaluate(self, X, out, *args, **kwargs):
        n = X.shape[0]
        F = np.zeros((n, 4))
        G = np.zeros((n, 3))

        for i in range(n):
            x = X[i].copy()
            # Round integer variables
            for idx in self.integer_vars:
                x[idx] = round(x[idx])
            F[i] = evaluate_objectives(x, self.params)
            G[i] = evaluate_constraints(x, self.params)

        out["F"] = F
        out["G"] = G


class IntegerVariableRounding(Repair):
    """Rounds only the integer variables r, N_gw and eps_h (indices 0, 5, 7)
    and leaves the five continuous variables untouched."""

    INTEGER_VARS = [0, 5, 7]

    def _do(self, problem, X, **kwargs):
        X = np.array(X, dtype=float, copy=True)
        X[:, self.INTEGER_VARS] = np.round(X[:, self.INTEGER_VARS])
        return X


def make_repair(repair: str = "all") -> Repair:
    """Repair applied after crossover and mutation.

    ``"all"`` (default) is pymoo's RoundingRepair, which is what this code has
    always used. Note that it rounds *every* decision variable to an integer,
    including the continuous ones (d, p_tx, f_s, alpha, T_m).
    ``"integer"`` rounds only r, N_gw and eps_h.
    """
    if repair == "all":
        return RoundingRepair()
    if repair == "integer":
        return IntegerVariableRounding()
    raise ValueError(f"unknown repair '{repair}'")


def build_nsga2(pop_size: int = 200, repair: str = "all") -> NSGA2:
    """NSGA-II as configured for the paper.

    SBX crossover (prob 0.8, eta 15) and polynomial mutation (eta 20), both
    followed by the rounding repair (see make_repair). The only stopping rule
    used anywhere in this repository is a fixed generation budget
    (``("n_gen", n_gen)``).
    """
    return NSGA2(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.8, eta=15, repair=make_repair(repair)),
        mutation=PM(eta=20, repair=make_repair(repair)),
        eliminate_duplicates=True,
    )


def run_optimization(
    case_study: str,
    pop_size: int = 200,
    n_gen: int = 500,
    seed: int = 42,
    verbose: bool = True,
    output_dir: str = "output",
) -> dict:
    """
    Run NSGA-II optimization for a given case study.

    Parameters
    ----------
    case_study : str
        One of 'industrial', 'smartcity', 'healthcare'
    pop_size : int
        Population size
    n_gen : int
        Number of generations
    seed : int
        Random seed
    verbose : bool
        Print progress
    output_dir : str
        Directory to save results

    Returns
    -------
    dict with keys: solutions, fitness, time, params, result
    """
    params = ALL_CASE_STUDIES[case_study]()
    problem = MCSDTFProblem(params)

    algorithm = build_nsga2(pop_size)

    termination = get_termination("n_gen", n_gen)

    if verbose:
        print(f"\n{'=' * 60}")
        print(f"  MC-SDTF NSGA-II Optimization: {case_study.upper()}")
        print(f"  Variables: {problem.n_var} | Pop: {pop_size} | Generations: {n_gen}")
        print(f"{'=' * 60}")

    t_start = time.time()

    res = pymoo_minimize(
        problem,
        algorithm,
        termination,
        seed=seed,
        verbose=verbose,
        save_history=True,
    )

    elapsed = time.time() - t_start

    # Extract Pareto-optimal solutions
    solutions = res.X.copy()
    fitness = res.F.copy()

    # Round integer variables in solutions
    for idx in problem.integer_vars:
        solutions[:, idx] = np.round(solutions[:, idx])

    if verbose:
        print(f"\nCompleted in {elapsed / 60:.1f} min ({elapsed / 3600:.2f} hours)")
        print(f"Pareto-optimal solutions found: {solutions.shape[0]}")

    # Extract convergence history (hypervolume per generation)
    history_hv = []
    if res.history is not None:
        for gen_data in res.history:
            if gen_data.opt is not None:
                history_hv.append(gen_data.opt.get("F").shape[0])

    result = {
        "solutions": solutions,
        "fitness": fitness,
        "time": elapsed,
        "case_study": case_study,
        "params": params,
        "n_pareto": solutions.shape[0],
        "history_n_pareto": history_hv,
        "pymoo_result": res,
    }

    # Save to disk
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    save_path = out_path / f"MCSDTF_Results_{case_study}.pkl"
    with open(save_path, "wb") as f:
        pickle.dump({k: v for k, v in result.items() if k != "pymoo_result"}, f)
    if verbose:
        print(f"Results saved to {save_path}")

    return result


def run_all_case_studies(
    pop_size: int = 200,
    n_gen: int = 500,
    seed: int = 42,
    output_dir: str = "output",
) -> dict:
    """Run optimization for all three case studies sequentially."""
    print("\n" + "=" * 70)
    print("  MC-SDTF: Running ALL THREE Case Study Optimizations")
    print("=" * 70)

    total_start = time.time()
    all_results = {}

    for cs in ["industrial", "smartcity", "healthcare"]:
        all_results[cs] = run_optimization(
            cs, pop_size=pop_size, n_gen=n_gen, seed=seed, output_dir=output_dir
        )

    total_time = time.time() - total_start
    all_results["total_time"] = total_time

    print(f"\n{'=' * 70}")
    print(f"  TOTAL OPTIMIZATION TIME: {total_time / 60:.1f} min ({total_time / 3600:.2f} hours)")
    print(f"{'=' * 70}")

    # Save combined results
    out_path = Path(output_dir)
    save_path = out_path / "MCSDTF_AllResults.pkl"
    save_data = {
        k: {kk: vv for kk, vv in v.items() if kk != "pymoo_result"}
        if isinstance(v, dict) else v
        for k, v in all_results.items()
    }
    with open(save_path, "wb") as f:
        pickle.dump(save_data, f)
    print(f"Combined results saved to {save_path}")

    return all_results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cs = sys.argv[1]
        pop = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        gen = int(sys.argv[3]) if len(sys.argv) > 3 else 500
        if cs == "all":
            run_all_case_studies(pop_size=pop, n_gen=gen)
        else:
            run_optimization(cs, pop_size=pop, n_gen=gen)
    else:
        print("Usage: python optimizer.py <industrial|smartcity|healthcare|all> [pop_size] [n_gen]")
        print("Example: python optimizer.py all 200 500")
