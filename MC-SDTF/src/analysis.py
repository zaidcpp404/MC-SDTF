"""
MC-SDTF Discussion & Analysis Module
=====================================
Computational overhead, key findings, conclusion highlights.
Equivalent to P14_to_P16_Discussion.m
"""

import numpy as np
import platform
import psutil
import sys
from pathlib import Path


# =========================================================================
# P07: Simulation Environment
# =========================================================================

def print_sim_environment():
    """Print simulation environment specification (Section V.A)."""
    print("=" * 55)
    print("  SIMULATION ENVIRONMENT SPECIFICATION")
    print("=" * 55)
    print(f"  Python Version:    {sys.version.split()[0]}")
    print(f"  Platform:          {platform.platform()}")
    print(f"  CPU:               {platform.processor() or 'N/A'}")
    print(f"  CPU Cores:         {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count()} logical")
    print(f"  System RAM:        {psutil.virtual_memory().total / 1e9:.1f} GB")
    print()

    pkgs = ["numpy", "scipy", "matplotlib", "pymoo", "psutil"]
    print("  Key Packages:")
    for pkg in pkgs:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "unknown")
            print(f"    [OK]  {pkg:<25s} v{ver}")
        except ImportError:
            print(f"    [!!]  {pkg:<25s} NOT FOUND")
    print()


# =========================================================================
# P14: Computational Overhead Analysis (Section VI.C)
# =========================================================================

def computational_overhead(all_results: dict):
    """Analyze computational overhead and payback."""
    print("\n" + "=" * 60)
    print("  COMPUTATIONAL OVERHEAD ANALYSIS")
    print("=" * 60)

    n_cores = psutil.cpu_count(logical=True)
    gamma_compute = 0.42  # kgCO2/kWh

    domains = ["industrial", "smartcity", "healthcare"]
    labels = ["Industrial", "Smart City", "Healthcare"]

    total_cpu_hours = 0
    total_wall = 0

    for domain, label in zip(domains, labels):
        R = all_results[domain]
        wall_hours = R["time"] / 3600
        cpu_hours = wall_hours * n_cores
        total_cpu_hours += cpu_hours
        total_wall += R["time"]

        print(f"\n  {label}:")
        print(f"    Wall-clock time:  {wall_hours:.3f} hours")
        print(f"    CPU-hours:        {cpu_hours:.3f} hours ({n_cores} cores)")

    print(f"\n  Total CPU-hours:      {total_cpu_hours:.3f}")
    print(f"  Total wall-clock:     {total_wall / 3600:.3f} hours")

    # Energy consumed by optimization
    CPU_TDP_W = 125
    utilization = 0.80
    system_overhead = 1.3
    P_system = CPU_TDP_W * utilization * system_overhead
    E_opt_kWh = P_system * (total_wall / 3600) / 1000

    print(f"\n  Energy consumed by optimization:")
    print(f"    System power draw:  {P_system:.0f} W (est.)")
    print(f"    Total:              {E_opt_kWh:.4f} kWh")

    CF_opt = E_opt_kWh * gamma_compute
    print(f"\n  Carbon footprint of optimization:")
    print(f"    Grid factor:        {gamma_compute} kgCO2/kWh")
    print(f"    Total CO2:          {CF_opt:.4f} kgCO2-eq")

    # Payback analysis
    print(f"\n  --- PAYBACK ANALYSIS ---")

    for domain, label in zip(domains, labels):
        R = all_results[domain]
        fit = R["fitness"]
        energy = fit[:, 1]
        avail = -fit[:, 0] * 100

        idx_maxA = np.argmax(avail)
        a_n = (avail - min(avail)) / max(1e-10, max(avail) - min(avail))
        e_n = (energy - min(energy)) / max(1e-10, max(energy) - min(energy))
        dist = np.sqrt((1 - a_n) ** 2 + e_n ** 2)
        idx_knee = np.argmin(dist)

        E_saved = energy[idx_maxA] - energy[idx_knee]
        CF_saved = E_saved * gamma_compute

        if E_saved > 0:
            payback_days = E_opt_kWh / (E_saved / 365)
        else:
            payback_days = float("inf")

        print(f"\n  {label}:")
        print(f"    Annual energy saving (knee vs max-rel): {E_saved:.1f} kWh/yr")
        print(f"    Annual carbon saving:                   {CF_saved:.1f} kgCO2-eq/yr")
        print(f"    Energy payback:                         {payback_days:.2f} days")

    print("\n  Note: This is a ONE-TIME design cost, not recurring.")


# =========================================================================
# P15: Key Findings (Section VI.A)
# =========================================================================

def key_findings(all_results: dict):
    """Generate key findings analysis."""
    print("\n" + "=" * 60)
    print("  KEY FINDINGS (Section VI.A)")
    print("=" * 60)

    domains = ["industrial", "smartcity", "healthcare"]
    labels = ["Industrial", "Smart City", "Healthcare"]
    var_names = ["Redundancy", "Duty Cycle", "Tx Power", "Sampling Freq",
                 "Edge Alloc", "N Gateways", "Maint. Interval", "Harvesting"]

    # Finding 1: Pareto Front Shape
    print("\n  FINDING 1: Pareto Front Shape")
    print("  " + "-" * 40)
    for domain, label in zip(domains, labels):
        fit = all_results[domain]["fitness"]
        avail = -fit[:, 0] * 100
        energy = fit[:, 1]

        sort_idx = np.argsort(avail)
        a_sorted = avail[sort_idx]
        e_sorted = energy[sort_idx]

        if len(a_sorted) > 10:
            mid = len(a_sorted) // 2
            q1 = len(a_sorted) // 4
            q3 = 3 * len(a_sorted) // 4

            slope_left = (e_sorted[mid] - e_sorted[q1]) / (a_sorted[mid] - a_sorted[q1] + 1e-10)
            slope_right = (e_sorted[q3] - e_sorted[mid]) / (a_sorted[q3] - a_sorted[mid] + 1e-10)

            if slope_right > slope_left:
                shape = "CONVEX (accelerating trade-off at high reliability)"
            elif slope_right < slope_left:
                shape = "CONCAVE (diminishing returns)"
            else:
                shape = "APPROXIMATELY LINEAR"
        else:
            shape = "INSUFFICIENT DATA"

        print(f"    {label}: {shape}")

    # Finding 3: Dominant Decision Variables
    print("\n  FINDING 3: Dominant Decision Variables")
    print("  " + "-" * 40)

    for domain, label in zip(domains, labels):
        sol = all_results[domain]["solutions"]
        fit = all_results[domain]["fitness"]

        print(f"\n    {label} – Correlation with Energy (f2):")
        n_vars = min(sol.shape[1], len(var_names))
        for v in range(n_vars):
            if np.std(sol[:, v]) > 1e-10 and np.std(fit[:, 1]) > 1e-10:
                rho = np.corrcoef(sol[:, v], fit[:, 1])[0, 1]
            else:
                rho = 0.0
            dominant = "<< DOMINANT" if abs(rho) > 0.5 else ""
            print(f"      {var_names[v]:<20s}: r = {rho:+.3f} {dominant}")


# =========================================================================
# P16: Conclusion Numerical Highlights
# =========================================================================

def conclusion_highlights(all_results: dict):
    """Generate conclusion numerical highlights."""
    print("\n" + "=" * 60)
    print("  CONCLUSION NUMERICAL HIGHLIGHTS")
    print("=" * 60)

    domains = ["industrial", "smartcity", "healthcare"]
    labels = ["Industrial", "Smart City", "Healthcare"]

    for i, (domain, label) in enumerate(zip(domains, labels)):
        fit = all_results[domain]["fitness"]
        avail = -fit[:, 0] * 100
        energy = fit[:, 1]
        carbon = fit[:, 2]

        idx_maxA = np.argmax(avail)
        a_n = (avail - min(avail)) / max(1e-10, max(avail) - min(avail))
        e_n = (energy - min(energy)) / max(1e-10, max(energy) - min(energy))
        dist = np.sqrt((1 - a_n) ** 2 + e_n ** 2)
        idx_knee = np.argmin(dist)

        e_red = (energy[idx_maxA] - energy[idx_knee]) / max(1e-10, energy[idx_maxA]) * 100
        c_red = (carbon[idx_maxA] - carbon[idx_knee]) / max(1e-10, carbon[idx_maxA]) * 100

        print(f"\n  ({i + 1}) {label}: {e_red:.1f}% energy reduction, {c_red:.1f}% carbon reduction")
        print(f"      at knee point ({avail[idx_knee]:.4f}% availability) vs max-reliability.")

    print()


# =========================================================================
# Run all discussion analyses
# =========================================================================

def run_all_analyses(all_results: dict):
    """Run all discussion and analysis functions."""
    print_sim_environment()
    computational_overhead(all_results)
    key_findings(all_results)
    conclusion_highlights(all_results)
