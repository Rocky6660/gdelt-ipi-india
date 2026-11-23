"""E3 salience basket and media-implied inflation, MV (design_final D26). Coverage-selection decomposition; not a
structural explanation; no causal language.

Attention m_{i,t}:
  * DOC version (D8 PASS, 23 Nov ruling): monthly item price-phrase article count / sourcecountry:india article count
    ("media-implied inflation"). Items whose 20-headline precision is < 0.5 are dropped
    (data/processed/doc/doc_precision_judged.csv; until that file exists every row is labelled PRECISION PENDING).
  * Trends version: anchored item searches (common scale within each batch; batches rescaled by the mean of their
    'inflation' anchor) ("search-implied inflation").
Weights: w_{i,t-1} = 3-month mean of m_i ending t-1, normalised over available items (lagged one month, period-averaged).
pi^med_t = sum_i w_{i,t-1} pi_{i,t};  pi^abs_t = sum_i |pi_i,t| pi_i,t / sum_i |pi_i,t|;  pi^CPI_t = headline CPI y/y
(official item weights are not available, so the official benchmark is the published headline).
Test: change in IESH current perception (median) on pi^med, pi^CPI and pi^abs in the same specification (horse race),
real-time month = latest CPI month released before fieldwork (same rule as phase1 cpi_rt); rounds with base-2012 CPI.
Outputs: data/processed/results/e3_series_monthly.csv, e3_horse_race.csv, e3_summary.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase1 as p1  # noqa: E402

CPI_ITEMS = {  # E3 item -> MoSPI item names (mean of y/y if several)
    "onion": ["Onion"], "tomato": ["Tomato"], "potato": ["Potato"], "petrol": ["Petrol for Vehicle"],
    "diesel": ["Diesel for Vehicle"], "lpg": ["LPG [excl. Conveyance]"], "milk": ["Milk: Liquid (litre)"],
    "pulses": ["Arhar, Tur"], "wheat_atta": ["Wheat/ Atta - Other Sources"], "rice": ["Rice - Other Sources"],
    "edible_oil": ["Mustard Oil", "Refined Oil [sunflower, Soyabean, Saffola, Etc.]"], "gold": ["Gold"],
}
TRENDS_TERM = {"onion price": "onion", "tomato price": "tomato", "potato price": "potato", "petrol price": "petrol",
               "diesel price": "diesel", "gas cylinder price": "lpg", "milk price": "milk", "dal price": "pulses",
               "atta price": "wheat_atta", "rice price": "rice", "edible oil price": "edible_oil", "gold price": "gold"}


def item_inflation(root: Path) -> pd.DataFrame:
    c = pd.read_csv(root / "data/processed/cpi2012_item.csv")
    c["m"] = pd.PeriodIndex(c.period, freq="M")
    out = {}
    for k, names in CPI_ITEMS.items():
        s = []
        for n in names:
            x = c[c["item"] == n].set_index("m")["index"].sort_index()
            if len(x):
                x = x.reindex(pd.period_range(x.index.min(), x.index.max(), freq="M"))
                s.append(100 * (x / x.shift(12) - 1))
        if s:
            out[k] = pd.concat(s, axis=1).mean(axis=1)
    a = pd.read_csv(root / "data/processed/cpi2012_allindia.csv")
    v = a[(a.sector == "Combined") & (a.subgroup == "Vegetables")].assign(m=lambda d: pd.PeriodIndex(d.period, freq="M"))
    v = v.groupby("m")["index"].mean().sort_index()
    v = v.reindex(pd.period_range(v.index.min(), v.index.max(), freq="M"))
    out["vegetables"] = 100 * (v / v.shift(12) - 1)
    return pd.DataFrame(out)


def attention_doc(root: Path) -> pd.DataFrame | None:
    p = root / "data/processed/doc/doc_daily.csv"
    if not p.exists():
        return None
    d = pd.read_csv(p, dtype={"date": str})
    d["m"] = pd.PeriodIndex(pd.to_datetime(d.date, format="%Y%m%d"), freq="M")
    mm = d.groupby(["series", "m"]).value.sum().unstack(0)
    if "den_india" not in mm:
        return None
    items = [c for c in mm.columns if c.startswith("item_")]
    att = mm[items].div(mm.den_india, axis=0)
    att.columns = [c[5:] for c in items]
    return att


def attention_trends(root: Path) -> pd.DataFrame | None:
    t = pd.read_csv(root / "data/processed/trends_monthly.csv")
    t = t[(t.geo == "IN") & (t.kind == "anchored")]
    if t.empty:
        return None
    t["m"] = pd.PeriodIndex(t.month, freq="M")
    out = {}
    for batch, g in t.groupby("anchor_set"):
        anchor = g[g.term == "inflation"].set_index("m").value_mean
        scale = 1.0 / anchor.mean() if anchor.mean() > 0 else np.nan
        for term, h in g[g.term != "inflation"].groupby("term"):
            if term in TRENDS_TERM:
                out[TRENDS_TERM[term]] = h.set_index("m").value_mean * scale
    return pd.DataFrame(out)


def implied(att: pd.DataFrame, pi: pd.DataFrame, drop: set) -> pd.DataFrame:
    items = [c for c in att.columns if c in pi.columns and c not in drop]
    a = att[items].sort_index()
    w = a.rolling(3, min_periods=2).mean().shift(1)
    idx = a.index.intersection(pi.index)
    w, p = w.loc[idx], pi.loc[idx, items]
    ok = w.notna() & p.notna()
    wn = w.where(ok)
    wn = wn.div(wn.sum(axis=1), axis=0)
    med = (wn * p.where(ok)).sum(axis=1, min_count=1)
    pa = p.where(ok)
    absw = pa.abs().div(pa.abs().sum(axis=1), axis=0)
    ab = (absw * pa).sum(axis=1, min_count=1)
    return pd.DataFrame({"pi_med": med, "pi_abs": ab, "n_items": ok.sum(axis=1)})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args()
    root, out = a.root, a.root / "data/processed/results"
    pi = item_inflation(root)
    cpi = p1.load_cpi(root)
    prec = root / "data/processed/doc/doc_precision_judged.csv"
    drop, prec_status = set(), "PRECISION PENDING (headline judging not done)"
    if prec.exists():
        pj = pd.read_csv(prec)
        pr = pj.groupby("item").relevant.apply(lambda s: (s.astype(str).str.upper() == "Y").mean())
        drop = set(pr[pr < 0.5].index)
        prec_status = f"precision judged; dropped (<0.5): {sorted(drop)}"
    versions = {}
    ad, at = attention_doc(root), attention_trends(root)
    if ad is not None:
        versions["doc_media_implied"] = implied(ad, pi, drop)
    if at is not None:
        versions["trends_search_implied"] = implied(at, pi, set())
    series = []
    for k, v in versions.items():
        series.append(v.assign(version=k).join(cpi[["cpi_yoy"]].rename(columns={"cpi_yoy": "pi_cpi"})))
    S = pd.concat(series).reset_index().rename(columns={"index": "month"}) if series else pd.DataFrame()
    S.to_csv(out / "e3_series_monthly.csv", index=False)

    df = p1.assemble(root)
    df = df[df.cpi_base2012.fillna(False)].copy()
    df["rt"] = df.fs.map(lambda d: p1.realtime_cpi_month(d - dt.timedelta(days=1)))
    df["d_cur"] = df.cur_median - df.cur_median.shift(1)
    rows = []
    for k, v in versions.items():
        d = df.copy()
        d["pi_med"] = d.rt.map(v.pi_med); d["pi_abs"] = d.rt.map(v.pi_abs); d["pi_cpi"] = d.rt.map(cpi.cpi_yoy)
        for f in ("pi_med", "pi_cpi", "pi_abs"):
            r = p1.fit_row(d, "d_cur", ["pi_med", "pi_cpi", "pi_abs", "cur_median_lag"], f,
                           f"E3 horse race [{k}] focus {f}")
            r["version"] = k
            rows.append(r)
        rows.append({**p1.fit_row(d, "d_cur", ["pi_med", "cur_median_lag"], "pi_med", f"E3 pi_med alone [{k}]"), "version": k})
        rows.append({"model": f"E3 corr(pi_med, pi_cpi) [{k}]", "version": k,
                     "beta": float(d[["pi_med", "pi_cpi"]].corr().iloc[0, 1]), "N": int(d[["pi_med", "pi_cpi"]].dropna().shape[0])})
    T = pd.DataFrame(rows)
    T["precision_status"] = prec_status
    T.to_csv(out / "e3_horse_race.csv", index=False)
    cols = [c for c in ["model", "N", "beta", "ci_lo", "ci_hi", "p_wild"] if c in T]
    md = ["# E3 salience basket (MV; coverage-selection decomposition, association only)", "",
          f"Versions: {list(versions)}; {prec_status}.",
          "Official item weights unavailable: pi^CPI = published headline y/y.", "",
          T[cols].round(3).to_markdown(index=False) if len(T) else "no versions available"]
    (out / "e3_summary.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
