# MC-SDTF: Complete Mathematical Formulation

This document lists all 34 equations used in the MC-SDTF framework.

---

## 1. Decision Vector

```
x = [r, d, p_tx, f_s, α, N_gw, T_m, ε_h]
```

| Index | Symbol | Description | Range | Type |
|-------|--------|-------------|-------|------|
| 0 | r | Redundancy level (simplex/dual/TMR) | {1, 2, 3} | Integer |
| 1 | d | Duty cycle | [0.01, 1.0] | Continuous |
| 2 | p_tx | Transmission power (dBm) | [0, 20] | Continuous |
| 3 | f_s | Sampling frequency (Hz) | [0.1, 100] | Continuous |
| 4 | α | Edge processing allocation | [0, 1] | Continuous |
| 5 | N_gw | Number of gateways | domain-specific | Integer |
| 6 | T_m | Maintenance interval (hours) | [168, 4380] | Continuous |
| 7 | ε_h | Energy harvesting config | {0, 1, 2, 3} | Integer |

---

## 2. Multi-Objective Problem (Eq. 1-2)

**Eq. 1 — Objective vector:**
```
min  F(x) = [f₁(x), f₂(x), f₃(x), f₄(x)]
```

**Eq. 2 — Constraints:**
```
g₁(x) = A_min − A_sys(x) ≤ 0          (availability)
g₂(x) = L_total(x) − L_max ≤ 0        (latency)
g₃(x) = C_total(x) − C_budget ≤ 0     (budget)
x_lb ≤ x ≤ x_ub                        (bounds)
```

---

## 3. Objective 1 — System Availability (Eq. 3-9)

**Eq. 3 — System availability (negated for minimization):**
```
f₁(x) = −A_sys(x)
```

**Eq. 4 — Single-node availability:**
```
A_single = μ_repair / (λ_i + μ_repair)
```

**Eq. 5 — Redundancy models:**
```
A_node = A_single                           if r = 1 (Simplex)
A_node = 1 − (1 − A_single)²               if r = 2 (Dual)
A_node = 3·A_single² − 2·A_single³          if r = 3 (TMR)
```

**Eq. 6 — Gateway cluster availability:**
```
A_gateway = 1 − (1 − 0.9999)^(N_gw / 3)
```

**Eq. 7 — Domain-specific system availability:**
```
A_sys = A_node^(N/G) · A_gateway
```
where G = 50 (industrial), 10 (smart city), 120 (healthcare).

**Eq. 8 — Stress-dependent failure rate:**
```
λ_i = λ_base · (1 + 0.5·p_tx/20 + 0.3·f_s/100)
```

**Eq. 9 — Repair rate:**
```
μ_repair = 1 / (0.1 · T_m)
```

---

## 4. Objective 2 — Total Energy (Eq. 10-15)

**Eq. 10 — Total energy:**
```
f₂(x) = Σ [E_sense,i + E_proc,i(α) + E_comm,i(p_tx, d)] · r_i + E_infra(N_gw) − E_harvest(ε_h)
```

**Eq. 11 — Sensing energy:**
```
E_sense = P_sense · d · T_sim / 1000,    P_sense = 0.005 · f_s (W)
```

**Eq. 12 — Communication energy:**
```
E_comm = P_tx · t_tx · n_samples / 3.6×10⁶
P_tx(W) = 10^((p_tx − 30) / 10)
n_samples = f_s · 3600 · d · T_sim
```

**Eq. 13 — Processing energy:**
```
E_proc = (P_edge + P_cloud) · d · T_sim / 1000
P_edge = 0.5·α (W),    P_cloud = 0.01·(1−α) (W)
```

**Eq. 14 — Infrastructure energy:**
```
E_infra = N_gw · 50 · T_sim / 1000  (kWh)
```

**Eq. 15 — Energy harvesting offset:**
```
E_harvest = 0                                    if ε_h = 0 (None)
          = N · 0.3 · 5 · 365 / 1000            if ε_h = 1 (Solar)
          = N · 0.01 · T_sim / 1000              if ε_h = 2 (RF)
          = E_solar + E_RF                        if ε_h = 3 (Hybrid)
```

---

## 5. Objective 3 — Carbon Footprint (Eq. 16-19)

**Eq. 16 — Total carbon footprint (LCA):**
```
f₃(x) = CF_mfg(x) + CF_ops(E_total, γ_grid) + CF_eol(x)
```

**Eq. 17 — Manufacturing carbon (amortized):**
```
CF_mfg = (N · r · c_device + N_gw · c_gateway) / L_lifecycle
```

**Eq. 18 — Operational carbon:**
```
CF_ops = E_total · γ_grid
```

**Eq. 19 — End-of-life carbon:**
```
CF_eol = (N · r · 0.5 + N_gw · 5) / L_lifecycle
```

---

## 6. Objective 4 — Mean Recovery Time (Eq. 20-23)

**Eq. 20 — MRT (Monte Carlo over K fault scenarios):**
```
f₄(x) = (1/K) · Σ t_recovery,k(r, α, N_gw)
```

**Eq. 21-23 — Recovery time by fault type:**
```
t_sensor  = 3600s (r=1), 5s (r=2), 0.1s (r=3)
t_gateway = 30 + 300/N_gw  (seconds)
t_comm    = 10·(1−α) + 0.5·α  (seconds)
```

---

## 7. Constraints (Eq. 24-28)

**Eq. 24 — Availability constraint:**
```
g₁(x) = A_min − A_sys(x) ≤ 0
```

**Eq. 25-26 — Latency constraint:**
```
g₂(x) = L_total(x) − L_max ≤ 0
L_total = (L_edge + L_cloud + L_queue) / 1000  (seconds)
L_edge = 10·α (ms),  L_cloud = 200·(1−α) (ms),  L_queue = 50/N_gw (ms)
```

**Eq. 27-28 — Budget constraint:**
```
g₃(x) = C_total(x) − C_budget ≤ 0
C_total = N · c_node(r) + N_gw · c_gw
c_node(r) ∈ {50, 90, 130} USD,   c_gw = 2000 USD
```

---

## 8. Degradation Model (Eq. 29-30)

**Eq. 29 — Wiener process degradation:**
```
H(t) = H₀ + μ_d · t + σ_d · W(t)
```

**Eq. 30 — Duty-cycle-dependent drift:**
```
μ_d = 0.001 · (1.2·d + 0.8·(1−d))
```

---

## 9. Sub-Models (Eq. 31-34)

**Eq. 31 — Per-node energy:**
```
E_node = (E_sense + E_comm + E_proc) · r
```

**Eq. 32 — dBm to Watts:**
```
P_tx (W) = 10^((p_tx − 30) / 10)
```

**Eq. 33 — Knee-point identification (utopia distance):**
```
idx_knee = argmin_i √((1 − Â_i)² + Ê_i²)
Â_i = (A_i − A_min) / (A_max − A_min)
Ê_i = (E_i − E_min) / (E_max − E_min)
```

**Eq. 34 — Pareto dominance:**
```
x(a) ≺ x(b) ⟺ ∀j: f_j(x(a)) ≤ f_j(x(b)) ∧ ∃j: f_j(x(a)) < f_j(x(b))
```
