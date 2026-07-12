"""
MC-SDTF Visualization Module
=============================
Generates all figures: Pareto fronts (Fig 6-8), Cross-domain (Fig 9),
Convergence (Fig 10), Sensitivity analysis.
Equivalent to P09_ParetoFronts, P10_NumericalResults, P11, P12, P13.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from pathlib import Path


def _find_key_points(avail, energy, carbon=None):
    """Find max-reliability, min-energy, and knee-point indices."""
    idx_maxA = np.argmax(avail)
    idx_minE = np.argmin(energy)

    a_range = max(avail) - min(avail)
    e_range = max(energy) - min(energy)
    a_n = (avail - min(avail)) / max(1e-10, a_range)
    e_n = (energy - min(energy)) / max(1e-10, e_range)
    dist = np.sqrt((1 - a_n) ** 2 + e_n ** 2)
    idx_knee = np.argmin(dist)

    sorted_idx = np.argsort(avail)
    idx_mid = sorted_idx[len(sorted_idx) // 2]

    return idx_maxA, idx_minE, idx_knee, idx_mid


# =========================================================================
# P09: Pareto Front Figures (Fig 6, 7, 8)
# =========================================================================

def plot_pareto_fronts(all_results: dict, output_dir: str = "output"):
    """Generate Pareto front figures for each case study."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    domains = ["industrial", "smartcity", "healthcare"]
    fig_nums = [6, 7, 8]
    titles = [
        "Industrial Smart Factory",
        "Smart City Environmental Monitoring",
        "Hospital Patient Monitoring",
    ]

    for domain, fig_num, title in zip(domains, fig_nums, titles):
        R = all_results[domain]
        fitness = R["fitness"]
        avail = -fitness[:, 0] * 100
        energy = fitness[:, 1]
        carbon = fitness[:, 2]
        mrt = fitness[:, 3]

        idx_maxA, idx_minE, idx_knee, _ = _find_key_points(avail, energy)

        fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

        # (a) Availability vs Energy, colored by carbon
        ax = axes[0]
        sc = ax.scatter(avail, energy, c=carbon, s=40, cmap="viridis",
                        edgecolors="k", linewidths=0.3, alpha=0.8)
        cb = plt.colorbar(sc, ax=ax)
        cb.set_label("Carbon Footprint (kgCO₂-eq/yr)", fontsize=9)
        ax.plot(avail[idx_maxA], energy[idx_maxA], "r^", ms=12, mew=2, label="Max Reliability")
        ax.plot(avail[idx_minE], energy[idx_minE], "gs", ms=12, mew=2, label="Max Sustainability")
        ax.plot(avail[idx_knee], energy[idx_knee], "mp", ms=14, mew=2, label="Knee Point")
        ax.set_xlabel("System Availability (%)")
        ax.set_ylabel("Total Energy Consumption (kWh/yr)")
        ax.set_title("(a) Availability vs. Energy")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # (b) Availability vs Recovery Time, colored by energy
        ax = axes[1]
        sc = ax.scatter(avail, mrt, c=energy, s=40, cmap="plasma",
                        edgecolors="k", linewidths=0.3, alpha=0.8)
        cb = plt.colorbar(sc, ax=ax)
        cb.set_label("Energy (kWh/yr)", fontsize=9)
        ax.set_xlabel("System Availability (%)")
        ax.set_ylabel("Mean Recovery Time (s)")
        ax.set_title("(b) Availability vs. Recovery Time")
        ax.grid(True, alpha=0.3)

        if domain == "healthcare":
            ax0 = axes[0]
            ax0.axvline(99.999, color="r", linestyle="--", lw=1.5, alpha=0.7)
            ax0.text(99.999, ax0.get_ylim()[1] * 0.95, "99.999% ECG req.",
                     fontsize=8, color="r", ha="right")

        fig.suptitle(f"Fig. {fig_num}. {title} Pareto Front", fontsize=13, fontweight="bold")
        plt.tight_layout()
        fig.savefig(out / f"Fig{fig_num}_{domain}_Pareto.png", dpi=300, bbox_inches="tight")
        fig.savefig(out / f"Fig{fig_num}_{domain}_Pareto.pdf", bbox_inches="tight")
        plt.close(fig)
        print(f"Fig. {fig_num} saved for {domain}")


# =========================================================================
# P10: Numerical Results Tables (Tables V, VI, VII)
# =========================================================================

def print_numerical_results(all_results: dict):
    """Print formatted result tables for each domain."""
    domains = ["industrial", "smartcity", "healthcare"]
    table_nums = ["V", "VI", "VII"]
    domain_names = [
        "Industrial Smart Factory",
        "Smart City Monitoring",
        "Hospital Patient Monitoring",
    ]
    var_names = ["r", "d", "p_tx", "f_s", "alpha", "N_gw", "T_m", "eps_h"]

    for domain, tnum, dname in zip(domains, table_nums, domain_names):
        R = all_results[domain]
        fitness = R["fitness"]
        solutions = R["solutions"]

        avail = -fitness[:, 0] * 100
        energy = fitness[:, 1]
        carbon = fitness[:, 2]
        mrt = fitness[:, 3]

        idx_maxA, idx_minE, idx_knee, idx_mid = _find_key_points(avail, energy)

        indices = [idx_maxA, idx_knee, idx_mid, idx_minE]
        labels = ["Max-Reliability", "Knee-Point", "Balanced", "Max-Sustainability"]

        print(f"\n{'=' * 90}")
        print(f"  TABLE {tnum}: {dname} Results")
        print(f"{'=' * 90}")
        header = f"{'Config':<20s} | {'Avail(%)':<10s} | {'Energy(kWh)':<12s} | {'CO2(kg/yr)':<12s} | {'MRT(s)':<8s} | {'r':>3s} | {'d':>5s}"
        print(header)
        print("-" * 90)

        for label, idx in zip(labels, indices):
            r_val = int(round(solutions[idx, 0]))
            d_val = solutions[idx, 1]
            print(f"{label:<20s} | {avail[idx]:<10.4f} | {energy[idx]:<12.1f} | "
                  f"{carbon[idx]:<12.1f} | {mrt[idx]:<8.1f} | {r_val:>3d} | {d_val:>5.2f}")

        # Key metrics
        print(f"\n  Energy range:   {min(energy):.1f} – {max(energy):.1f} kWh/yr")
        print(f"  Carbon range:   {min(carbon):.1f} – {max(carbon):.1f} kgCO2-eq/yr")
        e_reduction = (energy[idx_maxA] - energy[idx_knee]) / max(1e-10, energy[idx_maxA]) * 100
        print(f"  Energy reduction at knee: {e_reduction:.1f}%")
        print(f"  Knee availability: {avail[idx_knee]:.4f}%")


# =========================================================================
# P11: Sensitivity Analysis
# =========================================================================

def plot_sensitivity_analysis(all_results: dict, output_dir: str = "output"):
    """Plot sensitivity analysis using results data."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    R = all_results["industrial"]
    sol = R["solutions"]
    fit = R["fitness"]
    avail = -fit[:, 0] * 100
    energy = fit[:, 1]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # (a) Duty cycle vs Energy colored by availability
    ax = axes[0]
    sc = ax.scatter(sol[:, 1], energy, c=avail, s=30, cmap="RdYlGn", alpha=0.7)
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("Availability (%)")
    ax.set_xlabel("Duty Cycle (d)")
    ax.set_ylabel("Energy (kWh/yr)")
    ax.set_title("(a) Duty Cycle Impact on Energy")
    ax.grid(True, alpha=0.3)

    # (b) Maintenance interval vs Availability colored by energy
    ax = axes[1]
    sc = ax.scatter(sol[:, 6], avail, c=energy, s=30, cmap="viridis", alpha=0.7)
    cb = plt.colorbar(sc, ax=ax)
    cb.set_label("Energy (kWh/yr)")
    ax.set_xlabel("Maintenance Interval (hours)")
    ax.set_ylabel("Availability (%)")
    ax.set_title("(b) Maintenance Interval vs. Availability")
    ax.grid(True, alpha=0.3)

    fig.suptitle("Sensitivity Analysis – Industrial Case Study", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(out / "Fig_SensitivityAnalysis.png", dpi=300, bbox_inches="tight")
    fig.savefig(out / "Fig_SensitivityAnalysis.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Sensitivity analysis figure saved.")


# =========================================================================
# P12: Cross-Domain Comparison (Fig 9 + Table VIII)
# =========================================================================

def plot_cross_domain(all_results: dict, output_dir: str = "output"):
    """Generate cross-domain normalized comparison plot and table."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 6))

    domains = ["industrial", "smartcity", "healthcare"]
    colors = ["#337AB7", "#5CB85C", "#D9534F"]
    labels = ["Industrial", "Smart City", "Healthcare"]

    for domain, color, label in zip(domains, colors, labels):
        fit = all_results[domain]["fitness"]
        avail = -fit[:, 0] * 100
        energy = fit[:, 1]

        a_n = (avail - min(avail)) / max(1e-10, max(avail) - min(avail))
        e_n = (energy - min(energy)) / max(1e-10, max(energy) - min(energy))

        ax.scatter(a_n, e_n, c=color, s=40, alpha=0.6, edgecolors=color, label=label)

    ax.set_xlabel("Normalized Availability (0 = domain min, 1 = domain max)")
    ax.set_ylabel("Normalized Energy (0 = min, 1 = max)")
    ax.set_title("Fig. 9. Cross-Domain Normalized Pareto Front Comparison")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(out / "Fig9_CrossDomain.png", dpi=300, bbox_inches="tight")
    fig.savefig(out / "Fig9_CrossDomain.pdf", bbox_inches="tight")
    plt.close(fig)

    # Table VIII
    print(f"\n{'=' * 80}")
    print("  TABLE VIII: Cross-Domain Comparison")
    print(f"{'=' * 80}")
    print(f"{'Domain':<15s} | {'Avail Min%':>10s} | {'Avail Max%':>10s} | "
          f"{'E Range kWh':>12s} | {'Pareto Size':>12s} | {'Time(min)':>10s}")
    print("-" * 80)

    for domain, label in zip(domains, labels):
        fit = all_results[domain]["fitness"]
        avail = -fit[:, 0] * 100
        energy = fit[:, 1]
        t = all_results[domain]["time"]
        print(f"{label:<15s} | {min(avail):>10.4f} | {max(avail):>10.4f} | "
              f"{max(energy) - min(energy):>12.1f} | {fit.shape[0]:>12d} | {t / 60:>10.1f}")

    print("Cross-domain figure saved as Fig9.")


# =========================================================================
# P13: Convergence Analysis (Fig 10)
# =========================================================================

def _compute_hypervolume_2d(front_2d, ref_point):
    """Compute 2D hypervolume indicator."""
    sorted_idx = np.argsort(front_2d[:, 0])
    sorted_front = front_2d[sorted_idx]
    hv = 0.0
    for i in range(len(sorted_front)):
        if i < len(sorted_front) - 1:
            width = sorted_front[i + 1, 0] - sorted_front[i, 0]
        else:
            width = ref_point[0] - sorted_front[i, 0]
        height = ref_point[1] - sorted_front[i, 1]
        hv += width * max(0, height)
    return hv


def plot_convergence(all_results: dict, output_dir: str = "output"):
    """Plot convergence analysis using optimization history."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5))

    domains = ["industrial", "smartcity", "healthcare"]
    colors = ["#337AB7", "#5CB85C", "#D9534F"]
    labels = ["Industrial", "Smart City", "Healthcare"]

    for domain, color, label in zip(domains, colors, labels):
        R = all_results[domain]
        res = R.get("pymoo_result")

        if res is not None and res.history is not None:
            gens = []
            n_pareto = []
            for i, gen_data in enumerate(res.history):
                if gen_data.opt is not None:
                    gens.append(i + 1)
                    n_pareto.append(gen_data.opt.get("F").shape[0])

            ax.plot(gens, n_pareto, "-o", color=color, label=label,
                    linewidth=2, markersize=3, alpha=0.8)
        else:
            # Fallback: use stored history
            hist = R.get("history_n_pareto", [])
            if hist:
                ax.plot(range(1, len(hist) + 1), hist, "-o", color=color,
                        label=label, linewidth=2, markersize=3, alpha=0.8)

    ax.set_xlabel("Generation")
    ax.set_ylabel("Pareto Front Size")
    ax.set_title("Fig. 10. Convergence Analysis")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(out / "Fig10_Convergence.png", dpi=300, bbox_inches="tight")
    fig.savefig(out / "Fig10_Convergence.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Fig. 10 convergence saved.")


# =========================================================================
# Combined plotting call
# =========================================================================

def generate_all_figures(all_results: dict, output_dir: str = "output"):
    """Generate all visualization figures and tables."""
    plot_pareto_fronts(all_results, output_dir)
    print_numerical_results(all_results)
    plot_sensitivity_analysis(all_results, output_dir)
    plot_cross_domain(all_results, output_dir)
    plot_convergence(all_results, output_dir)
    print("\nAll figures and tables generated.")
