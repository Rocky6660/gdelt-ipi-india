"""Revision round 3, new local projections on the existing data (price family, one-year median, h = 0; EWC fixed-b CI
and restricted wild-bootstrap p with the paper's seed, as in phase1.fit_row):
  C15 irregular spacing: (a) no lagged dependent variable; (b) months between rounds as a control;
      (c) outcome divided by the months between rounds (change per two months)
  C17 intra-window daily Brent and INR/USD log changes (first to last trading day of the 14-day window) as controls
Writes data/processed/results_revision3/r3_lp.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/revision"))
import r2_index as r2  # noqa: E402  (frame(), seeded fit_row, SPEC)

p1 = r2.p1
OUT = ROOT / "data/processed/results_revision3"


def window_change(daily: pd.Series, start, end) -> float:
    s = daily[(daily.index >= start) & (daily.index <= end)].dropna()
    return 100 * (np.log(s.iloc[-1]) - np.log(s.iloc[0])) if len(s) >= 2 else np.nan


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = r2.frame()
    fs = pd.to_datetime(df.fieldwork_start)
    df["gap_months"] = (fs - fs.shift(1)).dt.days / 30.4375
    df["y1_h0_per2m"] = df.y1_median_h0 / df.gap_months * 2
    mk = pd.read_csv(ROOT / "data/processed/markets_daily.csv", parse_dates=["date"]).set_index("date")
    ws, we = pd.to_datetime(df.window_start), pd.to_datetime(df.window_end)
    df["dbrent_win"] = [window_change(mk.brent_usd, a, b) for a, b in zip(ws, we)]
    df["dinr_win"] = [window_change(mk.inr_usd, a, b) for a, b in zip(ws, we)]
    b = df[df.cpi_base2012.fillna(False)]
    f, Y, S = p1.fit_row, "y1_median_h0", r2.SPEC
    core = ["cpi_rt", "food_rt", "d_repo", "mode_phone"]
    rows = [f(b, Y, ["ipi_z"] + S, "ipi_z", "primary (reference)"),
            f(b, Y, ["ipi_z"] + core, "ipi_z", "no lagged dependent variable"),
            f(b, Y, ["ipi_z"] + S + ["gap_months"], "ipi_z", "months between rounds added"),
            f(b, "y1_h0_per2m", ["ipi_z"] + S, "ipi_z", "outcome per two months (divided by months between rounds)"),
            f(b, Y, ["ipi_z"] + S + ["dbrent_win", "dinr_win"], "ipi_z", "intra-window Brent and INR/USD changes added")]
    t = pd.DataFrame(rows)
    t["gap_months_min"], t["gap_months_max"] = b.gap_months.min(), b.gap_months.max()
    t["gap_months_median"] = b.gap_months.median()
    t["n_window_market_obs"] = int(b[["dbrent_win", "dinr_win"]].dropna().shape[0])
    t.to_csv(OUT / "r3_lp.csv", index=False)
    print(t[["model", "N", "beta", "ci_lo", "ci_hi", "p_wild"]].round(4).to_string())
    print("gap months", b.gap_months.describe().round(2).to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
