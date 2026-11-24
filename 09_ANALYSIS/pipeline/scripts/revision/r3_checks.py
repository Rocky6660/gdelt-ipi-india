"""Revision round 3, part A: verify the internal-consistency items against the result files and data on disk.
Prints facts only; writes data/processed/results_revision3/r3_checks.json. No estimate, flag or specification changed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/analysis"))
sys.path.insert(0, str(ROOT / "scripts/audit"))
import phase1 as p1  # noqa: E402

OUT = ROOT / "data/processed/results_revision3"
SW = json.loads((ROOT / "data/processed/results/d9_switch.json").read_text())
RS = ROOT / "data/processed/results_switched"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    f: dict = {}
    # A1 Table 11 variants (price family)
    lp = pd.read_csv(RS / "d19_national_lp.csv")
    y1 = lp[lp.outcome == "y1_median_h0"]
    f["A1_table11"] = y1[["model", "N", "beta", "p_wild"]].round(4).to_dict("records")
    # A2 monthly series: raw vs 3-month centred MA (the peak rule), on usable months
    mon = pd.read_csv(ROOT / "data/processed/index/ipi_monthly.csv")
    mon = mon[mon.usable_d23].copy()
    mon["m"] = pd.PeriodIndex(mon.month, freq="M")
    m = mon.set_index("m")
    full = m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"))
    for col, lab in ((SW["monthly_column"], "price_family"), ("ipi_monthly", "baseline")):
        raw = 100 * full[col]
        ma = raw.rolling(3, center=True, min_periods=2).mean()
        top = raw.nlargest(5)
        f[f"A2_{lab}_raw_top5"] = {str(k): round(float(v), 3) for k, v in top.items()}
        f[f"A2_{lab}_ma3_top5"] = {str(k): round(float(v), 3) for k, v in ma.nlargest(5).items()}
        f[f"A2_{lab}_raw_2022_04"] = round(float(raw.get(pd.Period("2022-04", "M"), np.nan)), 3)
        f[f"A2_{lab}_ma3_2022_04"] = round(float(ma.get(pd.Period("2022-04", "M"), np.nan)), 3)
        f[f"A2_{lab}_ma3_2026_04"] = round(float(ma.get(pd.Period("2026-04", "M"), np.nan)), 3)
        # persistence after 2022: level and AR(1) by period
        s = raw.dropna()
        for a, b, nm in (("2016-01", "2021-12", "2016_21"), ("2022-01", "2023-12", "2022_23"), ("2024-01", "2026-12", "2024_26")):
            x = s[(s.index >= pd.Period(a, "M")) & (s.index <= pd.Period(b, "M"))]
            f[f"A2_{lab}_mean_{nm}"] = round(float(x.mean()), 3)
            f[f"A2_{lab}_n_{nm}"] = int(len(x))
    pk = pd.read_csv(RS / "e5_peaks.csv")
    f["A2_e5_peaks_file"] = pk.round(3).to_dict("records")
    f["A2_months_usable"] = int(len(mon))
    # window index by period
    w = pd.read_csv(ROOT / "data/processed/index/ipi_window.csv")
    w["yr"] = w["round"].str[:4].astype(int)
    for a, b in ((2016, 2021), (2022, 2023), (2024, 2026)):
        x = 100 * w[(w.yr >= a) & (w.yr <= b)][SW["window_column"]]
        f[f"A2_window_mean_{a}_{b}"] = round(float(x.mean()), 3)
    # A4 BVAR effective N
    p1.IPI_COL, p1.MONTHLY_COL = SW["window_column"], SW["monthly_column"]
    df = p1.assemble(ROOT)
    dv = df[df.cpi_base2012.fillna(False)]
    cols = ["dln_brent", "cpi_rt", "ipi_primary", "y1_median", "repo"]
    T = int(len(dv[cols].dropna()))
    f["A4_bvar_rows_T"] = T
    f["A4_bvar_effective_obs_after_2_lags"] = T - 2
    f["A4_rounds_with_cpi_base2012"] = int(df.cpi_base2012.fillna(False).sum())
    kk = dv.dropna(subset=cols)["round"]
    f["A4_bvar_round_range"] = [str(kk.iloc[0]), str(kk.iloc[-1])]
    # A5 month-rule count by year (rounds in the window file)
    r = pd.read_csv(ROOT / "data/raw/iesh_rounds.csv")
    r = r[r["round"].isin(w["round"])]
    mr = r[r.fs_rule != "exact"]
    f["A5_month_rule_total"] = int(len(mr))
    f["A5_month_rule_by_year"] = mr["round"].str[:4].value_counts().sort_index().to_dict()
    f["A5_month_rule_rounds_2020"] = mr[mr["round"].str[:4] == "2020"]["round"].tolist()
    f["A5_exact_total"] = int((r.fs_rule == "exact").sum())
    # A7 lead-lag N: months with both language series
    ll = mon.dropna(subset=["ipi_monthly_eng", "ipi_monthly_ver"])
    f["A7_leadlag_months"] = int(len(ll))
    f["A7_leadlag_first_last"] = [ll.month.iloc[0], ll.month.iloc[-1]]
    # E3 outcome
    e3 = pd.read_csv(ROOT / "data/processed/results/e3_horse_race.csv")
    f["E3_outcomes"] = [str(x) for x in e3.outcome.unique()]
    (OUT / "r3_checks.json").write_text(json.dumps(f, indent=1, default=str))
    print(json.dumps(f, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
