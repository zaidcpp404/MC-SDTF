"""
MC-SDTF Framework Configuration & Case Study Parameters
========================================================
Defines all parameters for Industrial, Smart City, and Healthcare case studies.
Equivalent to P04, P05, P06 MATLAB files.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# =========================================================================
# Sensor / Device profiles: [active_power_W, sleep_power_W, sampling_freq_Hz]
# =========================================================================

INDUSTRIAL_SENSOR_PROFILES = np.array([
    [0.040, 0.001, 3200],   # Vibration (MEMS) ADXL345
    [0.003, 0.0001, 1],     # Temperature BME680
    [0.050, 0.002, 1000],   # Acoustic emission VS900-RIC
    [0.066, 0.001, 100],    # Current ACS712
    [0.001, 0.0001, 100],   # Voltage INA219
    [0.010, 0.001, 10],     # Spindle speed Hall effect
    [0.015, 0.001, 1],      # Coolant flow YF-S201
    [0.002, 0.0001, 0.5],   # Ambient temperature DHT22
    [0.002, 0.0001, 0.5],   # Humidity DHT22
    [0.002, 0.0001, 1],     # Power consumption PZEM-004T
])

SMARTCITY_SENSOR_PROFILES = np.array([
    [0.100, 0.001, 0.033],  # PM2.5
    [0.100, 0.001, 0.033],  # PM10
    [0.025, 0.001, 0.017],  # NO2
    [0.025, 0.001, 0.017],  # O3
    [0.030, 0.001, 0.017],  # CO
    [0.003, 0.0001, 0.017], # Temperature
    [0.003, 0.0001, 0.017], # Humidity
    [0.010, 0.001, 1.000],  # Noise
])

# Healthcare: [active_power_W, sleep_power_W, sampling_freq_Hz, continuous(1)/intermittent(0)]
HEALTHCARE_DEVICE_PROFILES = np.array([
    [0.150, 0.010, 250,   1],  # ECG
    [0.080, 0.005, 100,   1],  # SpO2
    [0.200, 0.001, 0.017, 0],  # Blood Pressure
    [0.005, 0.0001, 0.017, 0], # Temperature
    [0.060, 0.005, 25,    1],  # Respiration
    [0.001, 0.0001, 0,    0],  # Nurse Call
])

HEALTHCARE_BATTERY_WH = [1.85, 1.11, 2.22, 0.37, 1.11, 0.37]
HEALTHCARE_BATTERY_LIFE_HOURS = [72, 120, 168, 720, 120, 8760]


@dataclass
class CaseStudyParams:
    """Parameters for a single case study domain."""
    name: str
    n_nodes: int
    n_gateways_range: Tuple[int, int]
    A_min: float           # Minimum availability requirement
    L_max: float           # Maximum latency (seconds)
    gamma_grid: float      # Grid carbon intensity (kgCO2/kWh)
    T_sim: float           # Simulation period (hours)
    budget: float          # Budget constraint ($)
    lambda_sensor: float   # Base sensor failure rate (/hour)
    lambda_gateway: float  # Base gateway failure rate (/hour)
    CF_per_device: float   # Embodied carbon per device (kgCO2-eq)
    CF_per_gateway: float  # Embodied carbon per gateway (kgCO2-eq)
    device_lifecycle: float  # Years
    sensor_profiles: np.ndarray = field(default_factory=lambda: np.array([]))
    # Extra fields
    extra: Dict = field(default_factory=dict)


def get_industrial_params() -> CaseStudyParams:
    return CaseStudyParams(
        name="industrial",
        n_nodes=500,
        n_gateways_range=(3, 10),
        A_min=0.9999,
        L_max=2.0,
        gamma_grid=0.42,
        T_sim=8760,
        budget=500000,
        lambda_sensor=1e-5,
        lambda_gateway=5e-6,
        CF_per_device=8.5,
        CF_per_gateway=50.0,
        device_lifecycle=5,
        sensor_profiles=INDUSTRIAL_SENSOR_PROFILES,
        extra={
            "n_machines": 50,
            "sensors_per_machine": 10,
            "n_gateways_default": 5,
            "mu_d_bearing": 0.001,
            "H_fail": 10,
        },
    )


def get_smartcity_params() -> CaseStudyParams:
    return CaseStudyParams(
        name="smartcity",
        n_nodes=200,
        n_gateways_range=(5, 20),
        A_min=0.999,
        L_max=30.0,
        gamma_grid=0.35,
        T_sim=8760,
        budget=200000,
        lambda_sensor=5e-6,
        lambda_gateway=5e-6,
        CF_per_device=12.0,
        CF_per_gateway=50.0,
        device_lifecycle=7,
        sensor_profiles=SMARTCITY_SENSOR_PROFILES,
        extra={
            "n_critical": 30,
            "n_standard": 170,
            "area_km2": 2,
            "A_min_critical": 0.9999,
            "solar_area_m2": 0.04,
            "solar_eff": 0.20,
            "irradiance_avg": 4.5,
            "harvest_hours": 5,
            "battery_Wh": 3.7 * 6.6 * 2,
            "EC_sensor_tau_hours": 18 * 730,
        },
    )


def get_healthcare_params() -> CaseStudyParams:
    return CaseStudyParams(
        name="healthcare",
        n_nodes=720,
        n_gateways_range=(10, 25),
        A_min=0.99999,
        L_max=0.5,
        gamma_grid=0.45,
        T_sim=8760,
        budget=800000,
        lambda_sensor=1e-5,
        lambda_gateway=5e-6,
        CF_per_device=5.0,
        CF_per_gateway=35.0,
        device_lifecycle=3,
        sensor_profiles=HEALTHCARE_DEVICE_PROFILES[:, :3],
        extra={
            "n_beds": 120,
            "devices_per_bed": 6,
            "n_gateways_default": 15,
            "A_min_ecg": 0.99999,
            "A_min_vital": 0.9999,
            "A_min_other": 0.999,
            "L_max_ecg": 0.5,
            "L_max_spo2": 10,
            "device_profiles_full": HEALTHCARE_DEVICE_PROFILES,
            "battery_Wh": HEALTHCARE_BATTERY_WH,
            "battery_life_hours": HEALTHCARE_BATTERY_LIFE_HOURS,
        },
    )


ALL_CASE_STUDIES = {
    "industrial": get_industrial_params,
    "smartcity": get_smartcity_params,
    "healthcare": get_healthcare_params,
}


def print_case_study_table(params: CaseStudyParams):
    """Print formatted parameter table (equivalent to P04/P05/P06 console output)."""
    print(f"\n{'=' * 60}")
    print(f"  {params.name.upper()} CASE STUDY PARAMETERS")
    print(f"{'=' * 60}")
    print(f"  Nodes: {params.n_nodes}")
    print(f"  Gateway range: {params.n_gateways_range}")
    print(f"  Availability req: {params.A_min * 100:.3f}%")
    print(f"  Max latency: {params.L_max} s")
    print(f"  Grid carbon: {params.gamma_grid} kgCO2/kWh")
    print(f"  Budget: ${params.budget:,.0f}")
    print(f"  Device lifecycle: {params.device_lifecycle} years")
    print(f"  Simulation period: {params.T_sim} hours")
    for k, v in params.extra.items():
        print(f"  {k}: {v}")
    print()
