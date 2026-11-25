"""Capacity control model for one Jaybird class.

Three customer types share one room:
  members   - book early, pay the least per class (r_M)
  ClassPass - book close to class, mid revenue (r_C)
  drop-ins  - book close to class, pay the most (r_D)

Two booking rules:
  b = stop member bookings once b members have booked (found by checking every b from 0 to capacity)
  y = stop ClassPass bookings when available spots = y (keep a spot for drop-ins when
      r_D x P(drop-ins fill it) > r_C)

Demand for each type is normal. Within a class, drop-in and ClassPass demand are independent.
Expected revenue assumes members book first, then ClassPass, then drop-ins.
"""
from dataclasses import dataclass
from math import erf, sqrt

import numpy as np

CAPACITY = 38
_erf = np.vectorize(erf)


def norm_cdf(x, mu, sd):
    """Normal CDF, like Excel's NORMDIST(x, mu, sd, TRUE)."""
    return 0.5 * (1 + _erf((np.asarray(x, dtype=float) - mu) / (sd * sqrt(2))))


def demand_pmf(mu, sd, cap=CAPACITY):
    """P(demand = 0..cap). Same as the Excel model: NORMDIST(k) - NORMDIST(k-1); the last value means 'cap or more'."""
    sd = max(sd, 0.01)
    cdf = norm_cdf(np.arange(cap + 1), mu, sd)
    p = np.diff(np.concatenate([[0.0], cdf]))
    p[-1] = 1 - norm_cdf(cap - 1, mu, sd)
    return p


@dataclass
class ClassResult:
    member_limit: int            # b*
    classpass_protect: int       # y
    expected_revenue: float
    max_revenue: float
    expected_members: float
    expected_classpass: float
    expected_dropins: float
    revenue_by_limit: np.ndarray   # expected revenue for every member limit 0..cap
    members_by_limit: np.ndarray
    classpass_by_limit: np.ndarray
    dropins_by_limit: np.ndarray
    spot_table: list               # ClassPass rule, one row per spot

    @property
    def pct_of_max(self):
        return self.expected_revenue / self.max_revenue if self.max_revenue else 0.0

    @property
    def expected_empty(self):
        return CAPACITY - (self.expected_members + self.expected_classpass + self.expected_dropins)


def classpass_rule(r_D, r_C, d_mu, d_sd, cap=CAPACITY):
    """Spot n (counted from the drop-ins' side) is kept for drop-ins if r_D x P(drop-in demand >= n) > r_C."""
    rows = []
    for n in range(1, cap + 1):
        p_fill = float(1 - norm_cdf(n - 1, d_mu, max(d_sd, 0.01)))
        value = r_D * p_fill
        rows.append({"spot": n, "chance_dropins_fill": p_fill, "expected_dropin_revenue": value,
                     "classpass_payout": r_C, "keep": value > r_C})
    protect = sum(r["keep"] for r in rows)
    return protect, rows


def solve_class(m_mu, m_sd, d_mu, d_sd, c_mu, c_sd, r_M, r_C, r_D, cap=CAPACITY):
    """Booking rules and expected results for one class."""
    y, spot_table = classpass_rule(r_D, r_C, d_mu, d_sd, cap)

    # Joint probability of d drop-ins and c ClassPass clients: P(D = d) x P(C = c).
    joint = np.outer(demand_pmf(d_mu, d_sd, cap), demand_pmf(c_mu, c_sd, cap))

    # Close-to-class bookings for each number of members already booked (k).
    dv = np.arange(cap + 1)[:, None]
    cv = np.arange(cap + 1)[None, :]
    late_cp, late_di = np.zeros(cap + 1), np.zeros(cap + 1)
    for k in range(cap + 1):
        open_spots = cap - k
        cp_allowed = max(0, open_spots - y)
        s_c = np.minimum(cv, cp_allowed)
        s_d = np.minimum(dv, open_spots - s_c)
        late_cp[k] = (joint * s_c).sum()
        late_di[k] = (joint * s_d).sum()

    # Members booked under each member limit b: P(sM = k | b).
    p_m = demand_pmf(m_mu, m_sd, cap)
    k_vals = np.arange(cap + 1)
    rev, mem, cp, di = (np.zeros(cap + 1) for _ in range(4))
    for b in range(cap + 1):
        dist = np.where(k_vals < b, p_m, 0.0)
        dist[b] = 1.0 if b == 0 else float(1 - norm_cdf(b - 1, m_mu, max(m_sd, 0.01)))
        mem[b], cp[b], di[b] = dist @ k_vals, dist @ late_cp, dist @ late_di
        rev[b] = r_M * mem[b] + r_C * cp[b] + r_D * di[b]

    best = rev.max()
    b_opt = int(max(i for i in range(cap + 1) if rev[i] >= best - 0.005))   # ties: highest member limit
    return ClassResult(b_opt, y, float(rev[b_opt]), cap * r_D, float(mem[b_opt]), float(cp[b_opt]),
                       float(di[b_opt]), rev, mem, cp, di, spot_table)


def solve_row(row, prices):
    """Solve one row of the demand data. prices: dict with member, classpass, dropin, dropin_happy_hour."""
    r_D = prices["dropin_happy_hour"] if str(row["happy_hour"]).strip().lower() == "yes" else prices["dropin"]
    return solve_class(row["members_mean"], row["members_sd"], row["dropins_mean"], row["dropins_sd"],
                       row["classpass_mean"], row["classpass_sd"],
                       prices["member"], prices["classpass"], r_D)
