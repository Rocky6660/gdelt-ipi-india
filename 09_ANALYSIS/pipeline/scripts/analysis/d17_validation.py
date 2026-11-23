"""D17 external validation of the monthly IPI (design_final D17; D35 'never cut'). Validation of the index only:
no IESH outcomes are used. Correlations with CPI check the index; they are not evidence of content beyond CPI.

Episode windows (fixed in this script on 23 Nov 2026 BEFORE the index was inspected around these dates; D17 names the
episodes but not their months): onion 2019-09..2019-12; fuel 2021-02..2021-10; post-Ukraine 2022-03..2022-07;
tomato 2023-06..2023-08. Peak = episode-window mean above the 90th percentile of non-episode months; accept if >= 3 of 4.
Placebo dates (D17): 2019-05-23 and 2024-06-04 (election results), 2023-11-19 (Cricket World Cup final), each +/- 3
days (always-sampled). 'No peak' = the +/-3-day mean of the daily IPI is below the 90th percentile of the other
sampled days within +/- 30 days.

Inputs: data/processed/index/ipi_monthly.csv, ipi_daily.csv; data/processed/trends_monthly.csv; CPI (phase1.load_cpi);
        data/processed/doc/doc_daily.csv (optional: DOC keyword / theme IPI cross-check, D8 PASS).
Output: data/processed/results/d17_validation.csv/.json and d17_summary.md. Trends pulls are recorded (D7 needs 3).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase1 as p1  # noqa: E402

EPISODES = {"onion_2019_20": ("2019-09", "2019-12"), "fuel_2021_22": ("2021-02", "2021-10"),
            "post_ukraine_2022": ("2022-03", "2022-07"), "tomato_2023": ("2023-06", "2023-08")}
PLACEBOS = {"election_2019": "2019-05-23", "election_2024": "2024-06-04", "cwc_final_2023": "2023-11-19"}
RNG = np.random.default_rng(20261123)


def resid(y: pd.Series, X: pd.DataFrame) -> pd.Series:
    d = pd.concat([y, X], axis=1).dropna()
    A = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in X.columns])
    b, e = p1.ols(d.iloc[:, 0].to_numpy(float), A)
    return pd.Series(e, index=d.index)


def block_boot_corr(a: pd.Series, b: pd.Series, block: int = 6, B: int = 2000) -> tuple[float, float]:
    d = pd.concat([a, b], axis=1).dropna().to_numpy(float)
    n = len(d)
    if n < 2 * block:
        return np.nan, np.nan
    out = []
    for _ in range(B):
        starts = RNG.integers(0, n - block + 1, size=int(np.ceil(n / block)))
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        out.append(np.corrcoef(d[idx, 0], d[idx, 1])[0, 1])
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--col", default="ipi_monthly", help="monthly series to validate (D9 switch chain: a variant column)")
    ap.add_argument("--tag", default="", help="suffix for output files (e.g. _variant_strict)")
    a = ap.parse_args()
    root, out = a.root, a.root / "data/processed/results"
    out.mkdir(parents=True, exist_ok=True)
    mon = pd.read_csv(root / "data/processed/index/ipi_monthly.csv")
    mon = mon[mon.usable_d23].copy()
    if a.col != "ipi_monthly":
        mon["ipi_monthly"] = mon[a.col]  # D9 switch chain: validate the variant series with identical rules
    mon["m"] = pd.PeriodIndex(mon.month, freq="M")
    m = mon.set_index("m")
    cpi = p1.load_cpi(root)
    m = m.join(cpi[["cpi_yoy", "food_yoy"]], how="left")
    tr = pd.read_csv(root / "data/processed/trends_monthly.csv")
    tr = tr[(tr.geo == "IN") & (tr.kind == "solo")]
    rows, rep = [], {"trends_pulls": sorted(set(";".join(tr.pull_dates.astype(str)).split(";"))),
                     "trends_n_pulls_min": int(tr.n_pulls.min()) if len(tr) else 0}
    rep["provisional"] = rep["trends_n_pulls_min"] < 3
    m["log_vol"] = np.log(m.n_articles_core)
    m["t"] = np.arange(len(m))
    for term in ("inflation", "mehngai", "महंगाई"):
        s = tr[tr.term == term].assign(m=lambda x: pd.PeriodIndex(x.month, freq="M")).set_index("m").value_mean
        if s.empty:
            continue
        j = m.join(s.rename("trends"), how="inner").dropna(subset=["ipi_monthly", "trends"])
        r_raw = float(j[["ipi_monthly", "trends"]].corr().iloc[0, 1])
        # each series' trend in GDELT panel volume removed (linear trend + log core volume)
        ri = resid(j.ipi_monthly, j[["t", "log_vol"]]); rt = resid(j.trends, j[["t", "log_vol"]])
        r_vol = float(np.corrcoef(ri.loc[rt.index.intersection(ri.index)], rt.loc[rt.index.intersection(ri.index)])[0, 1])
        pi = resid(j.ipi_monthly, j[["cpi_yoy", "food_yoy"]]); pt = resid(j.trends, j[["cpi_yoy", "food_yoy"]])
        k = pi.index.intersection(pt.index)
        r_part = float(np.corrcoef(pi.loc[k], pt.loc[k])[0, 1])
        lo, hi = block_boot_corr(pi.loc[k], pt.loc[k])
        rows.append(dict(check="trends", term=term, N=len(j), r_raw=r_raw, pass_r_ge_0_5=r_raw >= 0.5,
                         r_after_volume_trend=r_vol, r_partial_cpi_food=r_part, partial_ci_lo=lo, partial_ci_hi=hi,
                         beyond_cpi_supported=bool(lo > 0)))
    # cross-correlograms with CPI and food CPI (k > 0: IPI leads)
    for c in ("cpi_yoy", "food_yoy"):
        for k in range(-6, 7):
            x = pd.concat([m.ipi_monthly, m[c].shift(-k)], axis=1).dropna()
            rows.append(dict(check=f"xcorr_{c}", lag_ipi_leads=k, N=len(x), r=float(x.corr().iloc[0, 1])))
    # DOC cross-check (D8 PASS): monthly keyword / theme shares of sourcecountry:india volume
    dp = root / "data/processed/doc/doc_daily.csv"
    if dp.exists():
        dd = pd.read_csv(dp, dtype={"date": str})
        dd["m"] = pd.PeriodIndex(pd.to_datetime(dd.date, format="%Y%m%d"), freq="M")
        mm = dd.groupby(["series", "m"]).value.sum().unstack(0)
        if "den_india" in mm:
            for sname in ("kw_inflation", "theme_inflation"):
                if sname in mm:
                    sh = (mm[sname] / mm.den_india).rename("doc")
                    j = m.join(sh, how="inner").dropna(subset=["ipi_monthly", "doc"])
                    rows.append(dict(check="doc", term=sname, N=len(j), r_raw=float(j[["ipi_monthly", "doc"]].corr().iloc[0, 1])))
    # episodes
    ep_mask = pd.Series(False, index=m.index)
    for k, (s, e) in EPISODES.items():
        ep_mask |= (m.index >= pd.Period(s, "M")) & (m.index <= pd.Period(e, "M"))
    p90 = m.ipi_monthly[~ep_mask].quantile(0.9)
    mu, sd = m.ipi_monthly[~ep_mask].mean(), m.ipi_monthly[~ep_mask].std()
    n_ok = 0
    for k, (s, e) in EPISODES.items():
        w = m.ipi_monthly[(m.index >= pd.Period(s, "M")) & (m.index <= pd.Period(e, "M"))]
        ok = bool(w.mean() > p90)
        n_ok += ok
        rows.append(dict(check="episode", term=k, months=f"{s}..{e}", N=int(w.notna().sum()), episode_mean=float(w.mean()),
                         p90_non_episode=float(p90), z=float((w.mean() - mu) / sd), peak=ok))
    rep["episodes_peaking"] = int(n_ok)
    rep["episodes_pass_3_of_4"] = bool(n_ok >= 3)
    # placebos on the daily index
    dly = pd.read_csv(root / "data/processed/index/ipi_daily.csv", parse_dates=["pdate"])
    if a.col != "ipi_monthly":
        dly = dly.iloc[0:0]  # no daily series for variants: placebos reported for the baseline only
    dly = dly[dly.valid_day.astype(bool)].dropna(subset=["ipi"])
    n_peak = 0
    for k, dstr in PLACEBOS.items():
        d0 = pd.Timestamp(dstr)
        win = dly[(dly.pdate >= d0 - pd.Timedelta(days=3)) & (dly.pdate <= d0 + pd.Timedelta(days=3))]
        ctx = dly[(dly.pdate >= d0 - pd.Timedelta(days=30)) & (dly.pdate <= d0 + pd.Timedelta(days=30)) & ~dly.index.isin(win.index)]
        q90 = ctx.ipi.quantile(0.9)
        peak = bool(win.ipi.mean() > q90)
        n_peak += peak
        rows.append(dict(check="placebo", term=k, date=dstr, N=len(win), window_mean=float(win.ipi.mean()),
                         context_p90=float(q90), context_N=len(ctx), peak=peak))
    rep["placebos_with_peak"] = int(n_peak)
    t = pd.DataFrame(rows)
    t.to_csv(out / f"d17_validation{a.tag}.csv", index=False)
    trend_rows = t[t.check == "trends"]
    rep["trends_pass_any_headline_term"] = bool(trend_rows.pass_r_ge_0_5.any()) if len(trend_rows) else None
    rep["trends_pass_inflation_term"] = bool(trend_rows[trend_rows.term == "inflation"].pass_r_ge_0_5.any()) if len(trend_rows) else None
    rep["series"] = a.col
    (out / f"d17_validation{a.tag}.json").write_text(json.dumps(rep, indent=1, default=str))
    md = ["# D17 external validation (auto-generated; validation of the index only, no outcomes)", "",
          f"Trends pulls: {rep['trends_pulls']} (min per series {rep['trends_n_pulls_min']}; "
          f"{'PROVISIONAL: D7 needs 3 pulls' if rep['provisional'] else 'final'})", "",
          trend_rows.drop(columns=[c for c in t.columns if t[c].isna().all() or c in ("lag_ipi_leads", "r", "months", "episode_mean",
                                   "p90_non_episode", "z", "peak", "date", "window_mean", "context_p90", "context_N")],
                          errors="ignore").round(3).to_markdown(index=False) if len(trend_rows) else "no Trends rows",
          "", "## Episodes", t[t.check == "episode"][["term", "months", "N", "episode_mean", "p90_non_episode", "z", "peak"]].round(4).to_markdown(index=False),
          f"Episodes peaking: {n_ok} of 4 (accept if >= 3).",
          "", "## Placebos (daily)", t[t.check == "placebo"][["term", "date", "N", "window_mean", "context_p90", "peak"]].round(4).to_markdown(index=False),
          "", "## DOC cross-check", t[t.check == "doc"][["term", "N", "r_raw"]].round(3).to_markdown(index=False) if (t.check == "doc").any() else "DOC series not yet available",
          "", "## Cross-correlogram with CPI y/y (k > 0: IPI leads)",
          t[t.check == "xcorr_cpi_yoy"][["lag_ipi_leads", "N", "r"]].round(3).to_markdown(index=False)]
    (out / f"d17_summary{a.tag}.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
