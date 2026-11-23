"""Shared constants and small statistics helpers for the audit scripts.

Allowed code values mirror docs/coding/codebook.md. Nothing here invents data.
"""
from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence

RELEVANCE = ("Y", "N")
DIRECTION = ("rising", "falling", "stable", "mixed", "none")
CAUSES = (
    "domestic_food_supply",
    "fuel_energy_domestic",
    "global_oil_commodities",
    "exchange_rate",
    "monetary_policy",
    "fiscal_tax_administered",
    "wages_demand",
    "corporate_pricing",
    "international_inflation_abroad",
    "other_none",
)
# Mapping fixed at Gate 2 (D25 fix). Edit only through the codebook.
INTERNATIONAL_CAUSES = frozenset(
    {"global_oil_commodities", "exchange_rate", "international_inflation_abroad"}
)


def derive_international(relevance, cause_primary) -> Optional[int]:
    """Binary international_imported from the primary cause. None when not codable."""
    if relevance != "Y" or cause_primary not in CAUSES:
        return None
    return int(cause_primary in INTERNATIONAL_CAUSES)


def clean_code(value, allowed: Sequence[str], allow_empty: bool = False):
    """Return the value if it is an allowed code, '' if empty and allowed, else None (missing).

    Invalid values are never repaired.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "" if allow_empty else None
    s = str(value).strip()
    if s == "":
        return "" if allow_empty else None
    if s in allowed:
        return s
    low = s.lower()
    if low in allowed:  # case-only difference is not a repair of meaning
        return low
    if s.upper() in allowed:
        return s.upper()
    return None


def cohen_kappa(a: Sequence, b: Sequence) -> float:
    """Cohen's kappa for two equal-length label sequences. NaN if undefined."""
    n = len(a)
    if n == 0 or n != len(b):
        return float("nan")
    cats = sorted(set(a) | set(b), key=str)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = 0.0
    for c in cats:
        pe += (sum(1 for x in a if x == c) / n) * (sum(1 for y in b if y == c) / n)
    if pe >= 1.0:
        return float("nan")
    return (po - pe) / (1.0 - pe)


def _binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if k >= n else 0.0
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05):
    """Exact binomial CI (lo, hi). (nan, nan) if n == 0."""
    if n <= 0:
        return (float("nan"), float("nan"))

    def solve(target, increasing_cdf_in_p_is_decreasing=True, f=None):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if f(mid) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    # upper: P(X <= k | p) = alpha/2 ; cdf decreases in p
    upper = 1.0 if k >= n else solve(alpha / 2, f=lambda p: _binom_cdf(k, n, p))
    # lower: P(X >= k | p) = alpha/2 i.e. 1 - cdf(k-1) = alpha/2 ; increases in p
    if k <= 0:
        lower = 0.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if 1 - _binom_cdf(k - 1, n, mid) < alpha / 2:
                lo = mid
            else:
                hi = mid
        lower = (lo + hi) / 2
    return (lower, upper)


def f_beta(precision: float, recall: float, beta: float = 2.0) -> float:
    if any(x is None or (isinstance(x, float) and math.isnan(x)) for x in (precision, recall)):
        return float("nan")
    d = beta**2 * precision + recall
    if d == 0:
        return 0.0  # precision and recall both defined and both zero
    return (1 + beta**2) * precision * recall / d
