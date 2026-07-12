"""
MC-SDTF Architecture Diagram Generator (Fig. 1)
================================================
Equivalent to P01_Architecture_Diagram.m
Generates the four-layer MC-SDTF framework architecture.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path


def generate_architecture_diagram(output_dir: str = "output"):
    """Generate the MC-SDTF four-layer architecture diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Layer definitions: name, y_bottom, color
    layers = [
        ("Layer 4: Multi-Objective Optimization", 7.5, "#D9534F"),
        ("Layer 3: Sustainability Assessment",    5.5, "#5CB85C"),
        ("Layer 2: Reliability Modeling",          3.5, "#337AB7"),
        ("Layer 1: Physical IoT Layer",            1.5, "#999999"),
    ]

    layer_height = 1.7
    layer_x = 0.8
    layer_w = 7.4

    for name, yb, color in layers:
        rect = mpatches.FancyBboxPatch(
            (layer_x, yb), layer_w, layer_height,
            boxstyle="round,pad=0.1",
            facecolor=color, alpha=0.12,
            edgecolor=color, linewidth=2,
        )
        ax.add_patch(rect)
        ax.text(layer_x + 0.15, yb + layer_height - 0.25, name,
                fontsize=11, fontweight="bold", color=color, va="top")

    def add_box(cx, cy, w, h, label, color):
        rect = mpatches.FancyBboxPatch(
            (cx - w / 2, cy - h / 2), w, h,
            boxstyle="round,pad=0.08",
            facecolor=color, alpha=0.30,
            edgecolor=color, linewidth=1.5,
        )
        ax.add_patch(rect)
        ax.text(cx, cy, label, fontsize=7.5, ha="center", va="center",
                color="black", linespacing=1.3)

    # Layer 4 components
    y4 = 8.15
    add_box(2.0, y4, 1.6, 0.8, "NSGA-II\n(pymoo)", "#D9534F")
    add_box(4.2, y4, 1.6, 0.8, "Pareto Front\nGenerator", "#D9534F")
    add_box(6.4, y4, 1.6, 0.8, "Constraint\nHandler", "#D9534F")

    # Layer 3 components
    y3 = 6.15
    add_box(1.7, y3, 1.3, 0.8, "Energy\nModel", "#5CB85C")
    add_box(3.4, y3, 1.3, 0.8, "Carbon\nFootprint", "#5CB85C")
    add_box(5.1, y3, 1.3, 0.8, "LCA\nModule", "#5CB85C")
    add_box(6.8, y3, 1.3, 0.8, "Resource\nLifecycle", "#5CB85C")

    # Layer 2 components
    y2 = 4.15
    add_box(2.0, y2, 1.6, 0.8, "Degradation\n(Wiener)", "#337AB7")
    add_box(4.2, y2, 1.6, 0.8, "Fault Injection\n& Recovery", "#337AB7")
    add_box(6.4, y2, 1.6, 0.8, "Predictive\nMaintenance", "#337AB7")

    # Layer 1 components
    y1 = 2.15
    add_box(1.7, y1, 1.3, 0.8, "Power\nSupply", "#999999")
    add_box(3.4, y1, 1.3, 0.8, "Sensor\nModels", "#999999")
    add_box(5.1, y1, 1.3, 0.8, "Comm.\nModels", "#999999")
    add_box(6.8, y1, 1.3, 0.8, "IoT\nPlatform", "#999999")

    # Feedback arrow on right side
    arrow_x = 8.8
    ax.annotate(
        "", xy=(arrow_x, 8.5), xytext=(arrow_x, 2.0),
        arrowprops=dict(arrowstyle="->", color="gray", lw=2),
    )
    ax.annotate(
        "", xy=(arrow_x, 2.0), xytext=(arrow_x, 8.5),
        arrowprops=dict(arrowstyle="->", color="gray", lw=2, linestyle="dashed"),
    )
    ax.text(arrow_x + 0.15, 5.3, "Feedback\nLoop", fontsize=9, color="gray",
            rotation=90, ha="left", va="center")

    # Title
    ax.text(4.5, 9.7, "Fig. 1. MC-SDTF Four-Layer Architecture",
            fontsize=13, fontweight="bold", ha="center")

    plt.tight_layout()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "Fig1_Architecture.png", dpi=300, bbox_inches="tight")
    fig.savefig(out / "Fig1_Architecture.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Fig. 1 saved as Fig1_Architecture.png and .pdf")


if __name__ == "__main__":
    generate_architecture_diagram()
