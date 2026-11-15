"""
MC-SDTF Pareto-Front Metrics
============================
Shared definitions used by the experiment campaign, the tables and the figures:

* key configurations of a front (max-reliability, knee point, balanced,
  max-sustainability), with the knee point computed as in the original code;
* normalization bounds, hypervolume (HV) and inverted generational distance (IGD)
  under the reference rules of Section 5.1;
* mean with a two-sided 95% Student-t confidence interval.
"""

import numpy as np
from scipy import stats
from pymoo.indicators.hv import HV
from pymoo.indicators.igd import IGD
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

OBJECTIVE_NAMES = ["neg_availability", "energy_kWh_per_yr", "carbon_kgCO2e_per_yr", "mrt_s"]
VARIABLE_NAMES = ["r", "d", "p_tx_dBm", "f_s_Hz", "alpha", "N_gw", "T_m_h", "eps_h"]
CONFIG_LABELS = ["Max-Reliability", "Knee-Point", "Balanced", "Max-Sustainability"]


# ---------------------------------------------------------------------------
# Key configurations
# ---------------------------------------------------------------------------

def _unit(v: np.ndarray) -> np.ndarray:
    span = v.max() - v.min()
    return (v - v.min()) / span if span > 0 else np.zeros_like(v, dtype=float)


AVAIL_TIE_TOL = 1e-9   # availabilities closer than this are treated as equal


def knee_point(avail: np.ndarray, energy: np.ndarray) -> int:
    """Knee point, as computed by the original MC-SDTF code.

    Availability and energy are min-max normalized to [0, 1] over the front; the
    knee is the solution closest (Euclidean distance) to the utopia point
    (normalized availability 1, normalized energy 0), i.e. the best compromise
    between the maximum-reliability and maximum-sustainability anchors.
    """
    if len(avail) == 1:
        return 0
    a_n, e_n = _unit(avail), _unit(energy)
    return int(np.argmin(np.hypot(1.0 - a_n, e_n)))


def knee_point_perpendicular(avail: np.ndarray, energy: np.ndarray) -> int:
    """Alternative knee definition (largest perpendicular distance from the line
    joining the two anchors, utopia side only). Not used for the reported
    results; kept so the two definitions can be compared."""
    if len(avail) == 1:
        return 0
    a_n, e_n = _unit(avail), _unit(energy)
    i_a, i_b = max_reliability(avail, None), int(np.argmin(energy))
    pa = np.array([a_n[i_a], e_n[i_a]])
    line = np.array([a_n[i_b], e_n[i_b]]) - pa
    length = np.hypot(*line)
    if length == 0:
        return i_a
    pts = np.column_stack([a_n, e_n]) - pa
    signed = (line[0] * pts[:, 1] - line[1] * pts[:, 0]) / length
    utopia = np.array([1.0, 0.0]) - pa
    if line[0] * utopia[1] - line[1] * utopia[0] < 0:
        signed = -signed
    return int(np.argmax(signed)) if np.any(signed > 1e-12) else int(np.argmax(np.abs(signed)))


def max_reliability(avail: np.ndarray, mrt) -> int:
    """Maximum-reliability solution: highest availability.

    Near the top of every front, many designs have availabilities that agree to
    about 1e-11 (the gateway term 1 - (1 - 0.9999)^(N_gw/3) equals 1.0 in
    double precision once N_gw is large), so a plain argmax would be decided by
    floating-point noise. Availabilities within AVAIL_TIE_TOL of the maximum are
    therefore treated as tied, and the tie is broken by the other reliability
    objective, the shortest mean recovery time (then the lowest index).
    """
    top = np.flatnonzero(avail >= avail.max() - AVAIL_TIE_TOL)
    if mrt is None or len(top) == 1:
        return int(top[0])
    return int(top[np.argmin(np.asarray(mrt)[top])])


def balanced_point(F: np.ndarray) -> int:
    """Equal-weight balanced solution in the normalized availability-energy plane:
    minimum of 0.5 x (1 - normalized availability) + 0.5 x normalized energy."""
    a_n, e_n = _unit(-F[:, 0]), _unit(F[:, 1])
    return int(np.argmin((1.0 - a_n) + e_n))


def key_points(F: np.ndarray) -> dict:
    """Indices of the four configurations reported in Tables 5-7."""
    avail = -F[:, 0]
    energy = F[:, 1]
    return {
        "Max-Reliability": max_reliability(avail, F[:, 3]),
        "Knee-Point": knee_point(avail, energy),
        "Balanced": balanced_point(F),
        "Max-Sustainability": int(np.argmin(energy)),
    }


def knee_reductions(F: np.ndarray) -> tuple:
    """Energy and carbon reduction (%) of the knee point relative to max-reliability."""
    k = key_points(F)
    i_a, i_k = k["Max-Reliability"], k["Knee-Point"]
    e = 100.0 * (F[i_a, 1] - F[i_k, 1]) / F[i_a, 1]
    c = 100.0 * (F[i_a, 2] - F[i_k, 2]) / F[i_a, 2]
    return e, c


# ---------------------------------------------------------------------------
# Fronts, HV and IGD
# ---------------------------------------------------------------------------

def nondominated(F: np.ndarray) -> np.ndarray:
    """Indices of the first non-dominated front of F (duplicates in F removed)."""
    if len(F) == 0:
        return np.array([], dtype=int)
    _, first = np.unique(F, axis=0, return_index=True)
    first = np.sort(first)
    nd = NonDominatedSorting().do(F[first], only_non_dominated_front=True)
    return first[nd]


class FrontScale:
    """Per-domain normalization: ideal = best value observed, nadir = worst value
    observed, over every final front of every run being compared."""

    def __init__(self, fronts):
        allF = np.vstack(fronts)
        self.ideal = allF.min(axis=0)
        self.nadir = allF.max(axis=0)
        span = self.nadir - self.ideal
        self.span = np.where(span > 0, span, 1.0)

    def __call__(self, F: np.ndarray) -> np.ndarray:
        return (F - self.ideal) / self.span


class FrontQuality:
    """HV and IGD for one domain.

    * HV reference point: the worst value of each objective observed across all
      runs (after normalization this is the point (1, 1, 1, 1)); HV is therefore
      the fraction of the box between the best and worst observed values that a
      front dominates.
    * IGD reference: the combined-best front, i.e. the non-dominated set of the
      union of all runs' final fronts, measured in the same normalized space.
    """

    def __init__(self, fronts):
        self.scale = FrontScale(fronts)
        allF = np.vstack(fronts)
        self.ref_idx = nondominated(allF)
        self.ref_front = allF[self.ref_idx]
        m = allF.shape[1]
        self._hv = HV(ref_point=np.ones(m))
        self._igd = IGD(self.scale(self.ref_front))

    def hv(self, F: np.ndarray) -> float:
        if F is None or len(F) == 0:
            return float("nan")
        return float(self._hv(self.scale(F)))

    def igd(self, F: np.ndarray) -> float:
        if F is None or len(F) == 0:
            return float("nan")
        return float(self._igd(self.scale(F)))


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def mean_ci95(values) -> tuple:
    """Mean and half-width of the two-sided 95% Student-t confidence interval."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    n = len(v)
    if n == 0:
        return float("nan"), float("nan")
    if n == 1:
        return float(v[0]), float("nan")
    half = stats.t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)
    return float(v.mean()), float(half)
