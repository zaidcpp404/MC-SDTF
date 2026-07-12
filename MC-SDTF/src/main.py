#!/usr/bin/env python3
"""
MC-SDTF Framework – Main Runner
================================
Master script to execute the entire MC-SDTF pipeline:
  Phase 1: Environment check & parameter tables
  Phase 2: Architecture & sensor node diagrams
  Phase 3: Run NSGA-II optimizations (all 3 case studies)
  Phase 4: Generate all figures & tables
  Phase 5: Discussion analysis & conclusion highlights

Usage:
  python main.py                # Run everything (default: pop=200, gen=300)
  python main.py --quick        # Quick test run (pop=50, gen=50)
  python main.py --full         # Full run (pop=200, gen=500)
  python main.py --figures-only # Skip optimization, load existing results
"""

import argparse
import time
import pickle
import sys
from pathlib import Path

# Project modules
from config import ALL_CASE_STUDIES, print_case_study_table
from analysis import print_sim_environment, run_all_analyses
from P01_architecture import generate_architecture_diagram
from P02_sensor_node import generate_sensor_node_diagram
from optimizer import run_all_case_studies
from visualizations import generate_all_figures

OUTPUT_DIR = "output"


def phase1_setup():
    """Phase 1: Environment & parameter tables."""
    print("\n" + "#" * 70)
    print("  PHASE 1: Setup & Parameters")
    print("#" * 70)
    print_sim_environment()

    for name, factory in ALL_CASE_STUDIES.items():
        params = factory()
        print_case_study_table(params)


def phase2_diagrams():
    """Phase 2: Architecture & sensor node diagrams."""
    print("\n" + "#" * 70)
    print("  PHASE 2: Generate Diagrams")
    print("#" * 70)
    generate_architecture_diagram(OUTPUT_DIR)
    generate_sensor_node_diagram(OUTPUT_DIR)


def phase3_optimize(pop_size: int, n_gen: int):
    """Phase 3: Run all NSGA-II optimizations."""
    print("\n" + "#" * 70)
    print("  PHASE 3: Run Optimizations")
    print("#" * 70)
    return run_all_case_studies(
        pop_size=pop_size, n_gen=n_gen, output_dir=OUTPUT_DIR
    )


def phase4_figures(all_results: dict):
    """Phase 4: Generate all figures and tables."""
    print("\n" + "#" * 70)
    print("  PHASE 4: Generate Figures & Tables")
    print("#" * 70)
    generate_all_figures(all_results, OUTPUT_DIR)


def phase5_analysis(all_results: dict):
    """Phase 5: Discussion & conclusion."""
    print("\n" + "#" * 70)
    print("  PHASE 5: Discussion & Analysis")
    print("#" * 70)
    run_all_analyses(all_results)


def load_results(output_dir: str = OUTPUT_DIR) -> dict:
    """Load previously saved results."""
    path = Path(output_dir) / "MCSDTF_AllResults.pkl"
    if not path.exists():
        print(f"Error: {path} not found. Run optimization first.")
        sys.exit(1)
    with open(path, "rb") as f:
        return pickle.load(f)


def main():
    parser = argparse.ArgumentParser(description="MC-SDTF Framework Runner")
    parser.add_argument("--quick", action="store_true",
                        help="Quick test (pop=50, gen=50)")
    parser.add_argument("--full", action="store_true",
                        help="Full run (pop=200, gen=500)")
    parser.add_argument("--figures-only", action="store_true",
                        help="Only generate figures from existing results")
    parser.add_argument("--pop", type=int, default=None, help="Population size")
    parser.add_argument("--gen", type=int, default=None, help="Number of generations")

    args = parser.parse_args()

    if args.quick:
        pop_size, n_gen = 50, 50
    elif args.full:
        pop_size, n_gen = 200, 500
    else:
        pop_size, n_gen = 200, 300

    if args.pop is not None:
        pop_size = args.pop
    if args.gen is not None:
        n_gen = args.gen

    total_start = time.time()

    if args.figures_only:
        all_results = load_results()
        phase4_figures(all_results)
        phase5_analysis(all_results)
    else:
        phase1_setup()
        phase2_diagrams()
        all_results = phase3_optimize(pop_size, n_gen)
        phase4_figures(all_results)
        phase5_analysis(all_results)

    total_elapsed = time.time() - total_start
    print(f"\n{'=' * 70}")
    print(f"  MC-SDTF PIPELINE COMPLETE")
    print(f"  Total elapsed: {total_elapsed / 60:.1f} min ({total_elapsed / 3600:.2f} hours)")
    print(f"  Output directory: {OUTPUT_DIR}/")
    print(f"{'=' * 70}")

    # List output files
    out = Path(OUTPUT_DIR)
    if out.exists():
        print("\n  Generated files:")
        for f in sorted(out.iterdir()):
            size = f.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / 1024 / 1024:.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            print(f"    {f.name:<45s} {size_str:>10s}")


if __name__ == "__main__":
    main()
