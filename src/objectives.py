"""
MC-SDTF Objective & Constraint Functions
=========================================
Evaluates the 4 objectives and nonlinear constraints for the NSGA-II optimizer.
Equivalent to evaluateObjectives / evaluateConstraints in P03_gamultiobj_Config.m
"""

import numpy as np
from config import CaseStudyParams


def evaluate_objectives(x: np.ndarray, params: CaseStudyParams) -> np.ndarray:
    """
    Evaluate 4 objectives for decision vector x.

    Decision vector: x = [r, d, p_tx, f_s, alpha, N_gw, T_m, eps_h]
      r       - Redundancy level (1=simplex, 2=dual, 3=TMR)
      d       - Duty cycle [0.01, 1.0]
      p_tx    - Transmission power (dBm) [0, 20]
      f_s     - Sampling frequency (Hz) [0.1, 100]
      alpha   - Edge processing allocation [0, 1]
      N_gw    - Number of gateways (integer)
      T_m     - Maintenance interval (hours) [168, 4380]
      eps_h   - Energy harvesting config (0=none, 1=solar, 2=RF, 3=hybrid)

    Returns: [f1, f2, f3, f4]
      f1 = -Availability (negative, to minimize = maximize availability)
      f2 = Total energy consumption (kWh/yr)
      f3 = Carbon footprint (kgCO2-eq/yr)
      f4 = Mean recovery time (seconds)
    """
    n_nodes = params.n_nodes
    gamma_grid = params.gamma_grid
    T_sim = params.T_sim
    case = params.name

    r = int(round(x[0]))
    d = x[1]
    p_tx = x[2]
    f_s = x[3]
    alpha = x[4]
    N_gw = int(round(x[5]))
    T_m = x[6]
    eps_h = int(round(x[7]))

    # Clamp to the decision-variable bounds (rounding repair can move d and f_s
    # below their lower bounds, e.g. f_s = 0.1 Hz rounds to 0 Hz)
    r = max(1, min(3, r))
    d = max(0.01, min(1.0, d))
    f_s = max(0.1, min(100.0, f_s))
    N_gw = max(params.n_gateways_range[0], min(params.n_gateways_range[1], N_gw))
    eps_h = max(0, min(3, eps_h))

    # ---- f1: Negative Availability ----
    mu_d = 0.001 * (d * 1.2 + (1 - d) * 0.8)
    lambda_base = 1e-5
    stress_factor = 1 + 0.5 * (p_tx / 20) + 0.3 * (f_s / 100)
    lambda_i = lambda_base * stress_factor
    mu_repair = 1.0 / (T_m * 0.1)

    A_single = mu_repair / (lambda_i + mu_repair)
    if r == 1:
        A_node = A_single
    elif r == 2:
        A_node = 1 - (1 - A_single) ** 2
    else:
        A_node = 3 * A_single ** 2 - 2 * A_single ** 3

    A_gateway = 1 - (1 - 0.9999) ** (N_gw / 3)

    if case == "industrial":
        A_sys = A_node ** (n_nodes / 50) * A_gateway
    elif case == "smartcity":
        A_sys = A_node ** (n_nodes / 10) * A_gateway
    else:  # healthcare
        A_sys = A_node ** (n_nodes / 120) * A_gateway

    f1 = -A_sys

    # ---- f2: Total Energy Consumption (kWh/year) ----
    P_sense = 0.005 * f_s
    E_sense = P_sense * d * T_sim / 1000.0

    P_tx_watts = 10 ** ((p_tx - 30) / 10)
    t_tx_per_sample = 0.1
    n_samples = f_s * 3600 * d * T_sim
    E_comm = P_tx_watts * t_tx_per_sample * n_samples / 3600000.0

    P_proc_edge = 0.5 * alpha
    P_proc_cloud = 0.01 * (1 - alpha)
    E_proc = (P_proc_edge + P_proc_cloud) * d * T_sim / 1000.0

    E_node = (E_sense + E_comm + E_proc) * r
    E_gateway = N_gw * 50 * T_sim / 1000.0

    if eps_h == 0:
        E_harvest = 0
    elif eps_h == 1:
        E_harvest = n_nodes * 0.3 * 5 * 365 / 1000.0
    elif eps_h == 2:
        E_harvest = n_nodes * 0.01 * T_sim / 1000.0
    else:
        E_harvest = n_nodes * 0.3 * 5 * 365 / 1000.0 + n_nodes * 0.01 * T_sim / 1000.0

    f2 = n_nodes * E_node + E_gateway - E_harvest

    # ---- f3: Carbon Footprint (kgCO2-eq/year) ----
    CF_mfg = (n_nodes * r * params.CF_per_device + N_gw * params.CF_per_gateway) / params.device_lifecycle
    CF_ops = f2 * gamma_grid
    CF_eol = (n_nodes * r * 0.5 + N_gw * 5) / params.device_lifecycle
    f3 = CF_mfg + CF_ops + CF_eol

    # ---- f4: Mean Recovery Time (seconds) ----
    rng = np.random.RandomState(42)
    K = 20
    recovery_times = np.zeros(K)
    for k in range(K):
        fault_type = rng.randint(1, 4)
        if fault_type == 1:  # Sensor fault
            if r == 1:
                t_base = 3600.0
            elif r == 2:
                t_base = 5.0
            else:
                t_base = 0.1
        elif fault_type == 2:  # Gateway fault
            t_base = 30.0 + 300.0 / max(N_gw, 1)
        else:  # Communication fault
            t_base = 10.0 * (1 - alpha) + 0.5 * alpha
        recovery_times[k] = t_base
    f4 = float(np.mean(recovery_times))

    return np.array([f1, f2, f3, f4])


def effective_decision_vectors(X: np.ndarray, params: CaseStudyParams) -> np.ndarray:
    """Decision vectors exactly as evaluate_objectives uses them (rounded
    integers, and every variable clamped to its bounds). Used for reporting."""
    X = np.array(X, dtype=float, copy=True)
    for j in (0, 5, 7):
        X[:, j] = np.round(X[:, j])
    X[:, 0] = np.clip(X[:, 0], 1, 3)
    X[:, 1] = np.clip(X[:, 1], 0.01, 1.0)
    X[:, 3] = np.clip(X[:, 3], 0.1, 100.0)
    X[:, 5] = np.clip(X[:, 5], *params.n_gateways_range)
    X[:, 7] = np.clip(X[:, 7], 0, 3)
    return X


def evaluate_constraints(x: np.ndarray, params: CaseStudyParams) -> np.ndarray:
    """
    Nonlinear inequality constraints: g(x) <= 0 is feasible.

    Returns array of constraint values:
      c[0] = A_min - A_sys       (availability)
      c[1] = L_total - L_max     (latency)
      c[2] = C_total - budget    (budget)
    """
    F = evaluate_objectives(x, params)
    A_sys = -F[0]

    alpha = x[4]
    N_gw = int(round(x[5]))
    r = int(round(x[0]))

    # Availability constraint
    c0 = params.A_min - A_sys

    # Latency constraint
    L_edge = 10 * alpha
    L_cloud = 200 * (1 - alpha)
    L_queue = 50 / max(N_gw, 1)
    L_total = (L_edge + L_cloud + L_queue) / 1000.0
    c1 = L_total - params.L_max

    # Budget constraint
    cost_per_node = [0, 50, 90, 130]  # index 0 unused
    cost_gateway = 2000
    r_clamped = max(1, min(3, r))
    C_total = params.n_nodes * cost_per_node[r_clamped] + N_gw * cost_gateway
    c2 = C_total - params.budget

    return np.array([c0, c1, c2])
