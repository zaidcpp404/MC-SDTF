"""
MC-SDTF IoT Sensor Node Model Diagram (Fig. 1)
================================================
Generates a block diagram of the sensor node architecture.
Equivalent to P02_Simscape_Sensor_Node.m (visual output).
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path


def generate_sensor_node_diagram(output_dir: str = "output"):
    """Generate IoT sensor node block diagram (Fig. 1)."""
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def draw_subsystem(x, y, w, h, title, components, color, title_color=None):
        if title_color is None:
            title_color = color
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.1",
            facecolor=color, alpha=0.08, edgecolor=color, linewidth=2,
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h - 0.2, title,
                fontsize=10, fontweight="bold", ha="center", va="top", color=title_color)
        for i, comp in enumerate(components):
            cy = y + h - 0.7 - i * 0.45
            if cy > y + 0.15:
                ax.text(x + 0.2, cy, f"• {comp}", fontsize=7.5, va="center", color="#333")

    # Power Supply subsystem
    draw_subsystem(0.5, 5.5, 3.5, 4, "Power Supply",
                   ["Battery (Li-Ion 3.7V)", "Solar Cell Panel", "DC-DC Boost Converter",
                    "Voltage Sensor", "Current Sensor", "Energy Harvesting Ctrl"],
                   "#E67E22")

    # Sensing Unit subsystem
    draw_subsystem(0.5, 0.5, 3.5, 4.5, "Sensing Unit",
                   ["Vibration (MEMS ADXL345)", "Temperature (BME680)",
                    "Acoustic Emission", "Current (ACS712)",
                    "Configurable Sampling (f_s)", "ADC + Signal Conditioning",
                    "Duty Cycle Controller (d)"],
                   "#2ECC71")

    # Communication subsystem
    draw_subsystem(5.0, 5.5, 4, 4, "Communication",
                   ["LoRaWAN / NB-IoT / BLE 5.0", "Adaptive Tx Power (p_tx)",
                    "Spreading Factor Select", "Payload Formatter",
                    "Duty Cycle Compliance", "Retry / ACK Handler"],
                   "#3498DB")

    # Edge Processing subsystem
    draw_subsystem(5.0, 0.5, 4, 4.5, "Edge Processing",
                   ["ARM Cortex / Jetson AGX", "Local ML Inference",
                    "Edge Allocation (α)", "Anomaly Detection",
                    "Data Aggregation", "Cloud Upload Manager",
                    "Local Buffer (30s)"],
                   "#9B59B6")

    # Decision Variables panel
    draw_subsystem(10.0, 5.5, 3.5, 4, "Decision Variables (x)",
                   ["r  – Redundancy (1/2/3)", "d  – Duty Cycle [0.01, 1]",
                    "p_tx – Tx Power [0, 20] dBm", "f_s  – Sampling Freq [0.1, 100] Hz",
                    "α  – Edge Allocation [0, 1]", "N_gw – Gateway Count",
                    "T_m  – Maintenance Interval", "ε_h  – Harvesting Config"],
                   "#C0392B")

    # Output Monitors panel
    draw_subsystem(10.0, 0.5, 3.5, 4.5, "Output Monitors",
                   ["Energy Monitor (kWh)", "Health/Degradation Monitor",
                    "Availability Tracker", "Latency Monitor",
                    "Carbon Footprint Calc", "Recovery Time Logger",
                    "→ Feeds to Optimizer (Layer 4)"],
                   "#34495E")

    # Arrows between subsystems
    arrow_props = dict(arrowstyle="->", color="#555", lw=1.5)
    ax.annotate("", xy=(5.0, 7.5), xytext=(4.0, 7.5), arrowprops=arrow_props)
    ax.annotate("", xy=(5.0, 2.75), xytext=(4.0, 2.75), arrowprops=arrow_props)
    ax.annotate("", xy=(10.0, 7.5), xytext=(9.0, 7.5), arrowprops=arrow_props)
    ax.annotate("", xy=(10.0, 2.75), xytext=(9.0, 2.75), arrowprops=arrow_props)

    # Cross connections
    ax.annotate("", xy=(5.0, 5.5), xytext=(4.0, 5.0), arrowprops={**arrow_props, "linestyle": "dashed"})
    ax.annotate("", xy=(7.0, 5.5), xytext=(7.0, 5.0), arrowprops={**arrow_props, "linestyle": "dashed"})

    ax.text(7, 9.8, "Fig. 1. MC-SDTF IoT Sensor Node Model",
            fontsize=13, fontweight="bold", ha="center")

    plt.tight_layout()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "Fig1_SensorNode.png", dpi=300, bbox_inches="tight")
    fig.savefig(out / "Fig1_SensorNode.pdf", bbox_inches="tight")
    plt.close(fig)
    print("Fig. 1 sensor node diagram saved.")


if __name__ == "__main__":
    generate_sensor_node_diagram()
