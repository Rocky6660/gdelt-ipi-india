"""Number-consistency check for paper_full.md: every decimal number in the Abstract and Results (Section 9) must match,
at its printed precision, some value in the result files (or that value x100 for shares). Prints unmatched numbers.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

PIPE = Path(__file__).resolve().parents[2]
PAPER = PIPE.parents[1] / "10_OUTPUTS/paper/archive/paper_full.md"


def values() -> set[float]:
    vals: list[float] = []
    files = list((PIPE / "data/processed/results_switched").glob("*.csv")) + list((PIPE / "data/processed/results").glob("*.csv")) \
        + [PIPE / "outputs/audit/metrics_prf.csv", PIPE / "outputs/audit/metrics_kappa.csv",
           PIPE / "outputs/audit/retrieval_by_stratum.csv"] \
        + list((PIPE / "data/processed/results_revision2").glob("*.csv")) + list((PIPE / "outputs/audit_revision2").glob("*.csv"))
    for f in files:
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        for c in d.columns:
            v = pd.to_numeric(d[c], errors="coerce").dropna()
            vals += v.tolist()
    for f in list((PIPE / "data/processed/results_switched").glob("*.json")) + list((PIPE / "data/processed/results_revision2").glob("*.json")) + [PIPE / "outputs/audit/gate_report.json",
                                                                               PIPE / "data/processed/results/d9_switch.json"]:
        txt = f.read_text()
        vals += [float(x) for x in re.findall(r"-?\d+\.\d+(?:e-?\d+)?", txt)]
    out = set()
    for v in vals:
        for x in (v, abs(v), 100 * v, abs(100 * v), 10 * v):
            out.add(x)
    return out


def section(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


def main() -> int:
    t = PAPER.read_text(encoding="utf-8")
    parts = {"abstract": section(t, "## Abstract", "## 1."), "results": section(t, "## 9. Results", "## 10."), "audit+validation": section(t, "## 6.", "## 8.")}
    pool = sorted(values())
    import bisect
    bad = []
    for name, s in parts.items():
        s = re.sub(r"!\[.*?\]\(.*?\)", "", s)
        for m in re.finditer(r"(?<![\w.])[−-]?\d+\.(\d+)", s):
            raw = m.group(0).replace("−", "-")
            nd = len(m.group(1)); v = abs(float(raw)); tol = 0.5 * 10 ** (-nd) + 1e-9
            i = bisect.bisect_left(pool, v - tol)
            ok = i < len(pool) and pool[i] <= v + tol
            if not ok:
                ctx = s[max(0, m.start() - 50):m.end() + 20].replace("\n", " ")
                bad.append((name, raw, ctx))
    for b in bad:
        print("UNMATCHED", b)
    n = sum(len(re.findall(r"(?<![\w.])[−-]?\d+\.\d+", re.sub(r"!\[.*?\]\(.*?\)", "", p))) for p in parts.values())
    print(f"checked {n} decimal numbers; unmatched {len(bad)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
