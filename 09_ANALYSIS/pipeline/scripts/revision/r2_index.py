"""Revision round 2, index and regression items (no primary estimate, flag or specification is changed; every model
below is an additional check on the existing data). Price-family flag (final flag), primary spec, h = 0, EWC fixed-b
CI and restricted wild-bootstrap p exactly as in phase1.fit_row.

  light: expectation robustness (trend, post-2022 dummy x index, subsamples, INR/USD, excl 2020-21 + post-2022),
         outlet composition (core outlets per window; >= median; balanced panel), joint test of monthly LP responses
  heavy: 7- and 10-day windows (last k days before fieldwork) rebuilt from the cached extraction; matched monthly series
         with the window construction on grid days, validated with the same Trends and episode checks as the paper
Outputs: data/processed/results_revision2/*.csv / *.json
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/analysis"))
sys.path.insert(0, str(ROOT / "scripts/build"))
import phase1 as p1  # noqa: E402

_fit = p1.fit_row


def _fit_seeded(*a, **k):
    """Every row uses the paper's bootstrap seed (phase1 RNG), so p-values do not depend on call order."""
    p1.RNG = np.random.default_rng(20261121)
    return _fit(*a, **k)


p1.fit_row = _fit_seeded

OUT = ROOT / "data/processed/results_revision2"
SW = json.loads((ROOT / "data/processed/results/d9_switch.json").read_text())
Y = "y1_median"
CORE = ["cpi_rt", "food_rt", "d_repo", "mode_phone"]
SPEC = [f"{Y}_lag", f"d_{Y}_lag"] + CORE
POST = dt.date(2022, 1, 1)
TERMS = ("inflation", "mehngai", "महंगाई")


def frame() -> pd.DataFrame:
    p1.IPI_COL, p1.MONTHLY_COL = SW["window_column"], SW["monthly_column"]
    df = p1.assemble(ROOT)
    mk = pd.read_csv(ROOT / "data/processed/markets_monthly.csv")
    fx = mk.assign(m=pd.PeriodIndex(mk.month.astype(str).str[:7], freq="M")).set_index("m").inr_usd_avg
    wm = df.fs.map(lambda d: pd.Period(d - dt.timedelta(days=1), "M"))  # same timing as dln_brent
    df["dln_inr"] = [100 * (math.log(fx[m]) - math.log(fx[m - 2])) if m in fx.index and (m - 2) in fx.index else np.nan
                     for m in wm]
    df["post2022"] = (df.fs >= POST).astype(float)
    df["ipi_x_post"] = df.ipi_z * df.post2022
    df["trend"] = np.arange(len(df), dtype=float)
    return df


def refit(df, s: pd.Series, label: str) -> dict:
    """Primary spec with the window series replaced by s (indexed by round); z-scored like phase1.assemble."""
    d = df.copy()
    d["alt"] = d["round"].map(s)
    d["alt_z"] = (d.alt - d.alt.mean()) / d.alt.std()
    base = d[d.cpi_base2012.fillna(False)]
    r = p1.fit_row(base, f"{Y}_h0", ["alt_z"] + SPEC, "alt_z", label)
    r["corr_with_published_series"] = float(d[["alt", "ipi_primary"]].corr().iloc[0, 1])
    return r


def expectation_robustness(df) -> pd.DataFrame:
    b = df[df.cpi_base2012.fillna(False)]
    f, h0 = p1.fit_row, f"{Y}_h0"
    inter = ["ipi_z", "ipi_x_post", "post2022"] + SPEC
    nc = b[b.covid == 0]
    rows = [f(b, h0, ["ipi_z"] + SPEC, "ipi_z", "primary (reference)"),
            f(b, h0, ["ipi_z"] + SPEC + ["trend"], "ipi_z", "add linear time trend"),
            f(b, h0, inter, "ipi_z", "post-2022 dummy + interaction: index (slope before 2022)"),
            f(b, h0, inter, "ipi_x_post", "post-2022 dummy + interaction: index x post-2022"),
            f(b[b.post2022 == 0], h0, ["ipi_z"] + SPEC, "ipi_z", "subsample: fieldwork before 2022"),
            f(b[b.post2022 == 1], h0, ["ipi_z"] + SPEC, "ipi_z", "subsample: fieldwork 2022 onward"),
            f(b, h0, ["ipi_z"] + SPEC + ["dln_inr"], "ipi_z", "add change in INR/USD (2-month log change)"),
            f(nc, h0, inter, "ipi_z", "excl 2020-21 + post-2022 regime: index (slope before 2022)"),
            f(nc, h0, inter, "ipi_x_post", "excl 2020-21 + post-2022 regime: index x post-2022")]
    return pd.DataFrame(rows)


def outlet_composition(df):
    wo = pd.read_csv(ROOT / "data/processed/index/ipi_window_outlet.csv")
    wo = wo[wo.valid_window.astype(bool) & wo.present.astype(bool)]
    nwin = wo["round"].nunique()
    pres = wo.groupby("outlet")["round"].nunique()
    core = pres.index[pres >= 0.8 * nwin]
    wc = wo[wo.outlet.isin(core)]
    n = wc.groupby("round").outlet.nunique().rename("n_core_present")
    chk = pd.read_csv(ROOT / "data/processed/index/ipi_window.csv").set_index("round").n_core_present
    assert (chk.reindex(n.index) == n).all(), "core count differs from ipi_window.csv"
    yr = pd.Series(n.index.str[:4], index=n.index, name="year")
    by_year = n.groupby(yr).agg(["count", "min", "median", "max"]).reset_index().rename(columns={"count": "windows"})
    summ = dict(core_outlets=int(len(core)), valid_windows=int(nwin), min=int(n.min()), median=float(n.median()),
                max=int(n.max()))
    s = wc.groupby("round").a_price.mean()
    rows = [refit(df, s, "all valid windows (reference)")]
    med = n.median()
    keep = n.index[n >= med]
    rows.append(refit(df, s.where(s.index.isin(keep)), f"windows with >= median ({med:g}) core outlets ({len(keep)} windows)"))
    base = df[df.cpi_base2012.fillna(False)].dropna(subset=[f"{Y}_h0"] + SPEC)
    reg_rounds = set(base["round"]) & set(n.index)
    for scope, rset in (("every valid window", set(n.index)), ("every window in the regression sample", reg_rounds)):
        bal = [o for o, g in wo.groupby("outlet") if rset <= set(g["round"])]
        summ[f"balanced_outlets_{scope}"] = len(bal)
        if len(bal) >= 3:
            sb = wo[wo.outlet.isin(bal)].groupby("round").a_price.mean()
            rows.append(refit(df, sb, f"balanced panel: {len(bal)} outlets present in {scope}"))
    return pd.DataFrame(rows), by_year, summ


def lp_data(H: int):
    mon = pd.read_csv(ROOT / "data/processed/index/ipi_monthly.csv")
    mon = mon[mon.usable_d23].copy()
    mon["m"] = pd.PeriodIndex(mon.month, freq="M")
    m = mon.set_index("m")
    c = SW["monthly_column"]
    m["z"] = (m[c] - m[c].mean()) / m[c].std()
    s = p1.load_cpi(ROOT).cpi_yoy.dropna()
    surpr = {}
    for i in range(36, len(s)):  # identical to phase1.d23
        hist = s.iloc[:i].to_numpy()
        Yv = hist[12:]
        X = np.column_stack([np.ones(len(Yv))] + [hist[12 - l:len(hist) - l] for l in range(1, 13)])
        b, _ = p1.ols(Yv, X)
        surpr[s.index[i]] = s.iloc[i] - np.r_[1.0, hist[-1:-13:-1]] @ b
    m["cpi_surprise"] = pd.Series(surpr)
    m["brent_shock"] = np.log(p1.load_markets(ROOT)).diff() * 100
    return m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"))


def joint_lp_test(H: int = 12, B: int = 4999, block: int = 12) -> pd.DataFrame:
    """Joint H0: all responses h = 0..H are zero, per shock. Same regressions as the paper's monthly LP
    (z_{t+h} on shock_t and z_{t-1}), estimated on the common sample where all horizons exist so the stacked
    covariance is defined. Tests: (i) Newey-West (lag H) Wald chi2(H+1); (ii) moving-block bootstrap of the same
    Wald statistic (recentred, block 12); (iii) Bonferroni on the paper's per-horizon EWC p-values;
    (iv) EWC fixed-b t test of the cumulative response (sum over h)."""
    from scipy import stats
    full = lp_data(H)
    pub = pd.read_csv(ROOT / "data/processed/results_switched/d23_monthly_lp.csv")
    rng = np.random.default_rng(20261124)
    K = H + 1
    sel = [3 * h + 1 for h in range(K)]

    def wald(Xm, Ym, b0=None):
        Ti = len(Xm)
        Bm = np.linalg.lstsq(Xm, Ym, rcond=None)[0]
        E = Ym - Xm @ Bm
        U = np.concatenate([Xm * E[:, [h]] for h in range(K)], axis=1)
        U = U - U.mean(0)
        Om = U.T @ U / Ti
        for l in range(1, H + 1):
            G = U[l:].T @ U[:-l] / Ti
            Om += (1 - l / (H + 1)) * (G + G.T)
        Abig = np.kron(np.eye(K), np.linalg.inv(Xm.T @ Xm / Ti))
        V = Abig @ Om @ Abig / Ti
        b = Bm[1, :] - (0 if b0 is None else b0)
        return float(b @ np.linalg.solve(V[np.ix_(sel, sel)], b)), Bm[1, :]

    rows = []
    for shock in ("cpi_surprise", "brent_shock"):
        D = pd.DataFrame({**{f"y{h}": full.z.shift(-h) for h in range(K)}, "s": full[shock], "ylag": full.z.shift(1)}).dropna()
        T = len(D)
        X = np.column_stack([np.ones(T), D.s, D.ylag])
        Yh = D[[f"y{h}" for h in range(K)]].to_numpy(float)
        W, bh = wald(X, Yh)
        nb = int(np.ceil(T / block))
        cnt = ok = 0
        for _ in range(B):
            st = rng.integers(0, T - block + 1, nb)
            idx = np.concatenate([np.arange(a, a + block) for a in st])[:T]
            try:
                Wb, _ = wald(X[idx], Yh[idx], b0=bh)
            except np.linalg.LinAlgError:
                continue
            ok += 1
            cnt += Wb >= W
        bs, es = p1.ols(Yh.sum(1), X)
        se, dof = p1.ewc_se(X, es)
        pp = pub[pub.shock == shock].sort_values("h").copy()
        pp["p"] = 2 * (1 - stats.t.cdf(np.abs(pp.beta / pp.se_ewc), pp.dof_B))
        rows.append(dict(shock=shock, horizons=f"0-{H}", N_common=T, N_per_horizon_paper=f"{pp.N.min()}-{pp.N.max()}",
                         wald_nw=W, df=K, p_chi2_nw=float(1 - stats.chi2.cdf(W, K)), p_block_bootstrap=(cnt + 1) / (ok + 1),
                         boot_draws_used=ok, min_p_per_horizon_paper=float(pp.p.min()),
                         p_bonferroni=float(min(1, K * pp.p.min())), cum_response_0_12=float(bs[1]), cum_se_ewc=float(se[1]),
                         cum_dof=int(dof), cum_ci_lo=float(bs[1] - p1.tcrit(dof) * se[1]),
                         cum_ci_hi=float(bs[1] + p1.tcrit(dof) * se[1]),
                         cum_p_ewc=float(2 * (1 - stats.t.cdf(abs(bs[1] / se[1]), dof))),
                         max_abs_diff_common_sample_vs_paper_beta=float(np.max(np.abs(bh - pp.beta.to_numpy())))))
    return pd.DataFrame(rows)


def validate(mm: pd.DataFrame, col: str, vol: str, label: str, d17) -> list[dict]:
    mm = mm.join(p1.load_cpi(ROOT)[["cpi_yoy", "food_yoy"]], how="left")
    mm["x"], mm["log_vol"], mm["t"] = mm[col], np.log(mm[vol]), np.arange(len(mm))
    tr = pd.read_csv(ROOT / "data/processed/trends_monthly.csv")
    tr = tr[(tr.geo == "IN") & (tr.kind == "solo")]
    d17.RNG = np.random.default_rng(20261123)
    out = []
    for term in TERMS:
        s = tr[tr.term == term].assign(m=lambda x: pd.PeriodIndex(x.month, freq="M")).set_index("m").value_mean
        if s.empty:
            continue
        j = mm.join(s.rename("trends"), how="inner").dropna(subset=["x", "trends"])
        ri, rt = d17.resid(j.x, j[["t", "log_vol"]]), d17.resid(j.trends, j[["t", "log_vol"]])
        kk = ri.index.intersection(rt.index)
        pi, pt = d17.resid(j.x, j[["cpi_yoy", "food_yoy"]]), d17.resid(j.trends, j[["cpi_yoy", "food_yoy"]])
        k2 = pi.index.intersection(pt.index)
        lo, hi = d17.block_boot_corr(pi.loc[k2], pt.loc[k2])
        out.append(dict(series=label, check="trends", term=term, N=len(j), r_raw=float(j[["x", "trends"]].corr().iloc[0, 1]),
                        r_after_volume_trend=float(np.corrcoef(ri.loc[kk], rt.loc[kk])[0, 1]),
                        r_partial_cpi_food=float(np.corrcoef(pi.loc[k2], pt.loc[k2])[0, 1]), partial_ci_lo=lo, partial_ci_hi=hi))
    ep = pd.Series(False, index=mm.index)
    for a_, b_ in d17.EPISODES.values():
        ep |= (mm.index >= pd.Period(a_, "M")) & (mm.index <= pd.Period(b_, "M"))
    p90, mu, sd = mm.x[~ep].quantile(0.9), mm.x[~ep].mean(), mm.x[~ep].std()
    for name, (a_, b_) in d17.EPISODES.items():
        w = mm.x[(mm.index >= pd.Period(a_, "M")) & (mm.index <= pd.Period(b_, "M"))]
        out.append(dict(series=label, check="episode", term=name, N=int(w.notna().sum()), episode_mean=float(w.mean()),
                        p90_non_episode=float(p90), z=float((w.mean() - mu) / sd), peak=bool(w.mean() > p90)))
    return out


def heavy(df) -> None:
    import build_index as bi
    import d17_validation as d17
    bq = bi.bq
    cfg = bq.load_config(ROOT / "scripts/config.yaml")
    rung = cfg["rung"]
    P = {**bi.DEFAULTS, **(cfg.get("index") or {}), "nested_window_lengths": cfg.get("nested_window_lengths", [7, 14])}
    panel = pd.read_csv(ROOT / "data/processed/index/panel_outlets.csv")
    panel_sources = set(panel[panel.in_panel.astype(bool)].domain)
    flags = bi.load_flags(ROOT / "scripts/build/flags.csv")
    A, G, _ = bi.load_all(ROOT, rung, flags, ROOT / "data/processed/index/cache", print)
    dcf = glob.glob(str(ROOT / "data/processed/bq_out/daycount_L2/*.parquet"))
    daycount = pd.concat(pd.read_parquet(f) for f in dcf) if dcf else None
    dayv = bi.day_validity(G, panel_sources, daycount, P)
    cal = bi.window_calendar(cfg, rung, ROOT / cfg["paths"]["iesh_rounds"])
    rows, info, core14 = [], {}, None
    for k in (14, 10, 7):
        c = cal[cal.day_in_window > cal.groupby("round").day_in_window.transform("max") - k].copy()
        c["day_in_window"] = c.groupby("round").cumcount() + 1
        win, hw, core, _ = bi.build_window(A, G, c, dayv, panel_sources, flags, P, {})
        s = win.set_index("round").variant_price_family
        win[["round", "valid_window", "n_core_present", "variant_price_family"]].assign(core_size=len(core)).to_csv(
            OUT / f"window_{k}d.csv", index=False)
        if k == 14:
            ref = pd.read_csv(ROOT / "data/processed/index/ipi_window.csv").set_index("round").variant_price_family
            info["max_abs_diff_14d_rebuild_vs_published"] = float((s - ref.reindex(s.index)).abs().max())
            core14 = core
        info[f"{k}d"] = dict(core_size=len(core), valid_windows=int(win.valid_window.sum()),
                             core_present_min=float(win.n_core_present.min()), core_present_median=float(win.n_core_present.median()))
        rows.append(refit(df, s, f"{k}-day window (core {len(core)} outlets, {int(win.valid_window.sum())} valid windows)"))
    pd.DataFrame(rows).to_csv(OUT / "window_length.csv", index=False)

    spec = cfg["rungs"][rung]
    start = max(bq.D(spec["start"]), bq.D(cfg["table_first_partition"]))
    grid = set(bq.grid_days(start, bq.D(cfg["sample_end"]), int(spec["step"]), int(cfg["seed"]), bq.D(cfg["grid_epoch"])))
    g = G[G.row_type.isin(["S", "D"]) & G.source.isin(panel_sources) & G.pdate.isin(grid)]
    info["matched_rows_by_type"] = g.row_type.value_counts().to_dict()
    info["matched_rows_missing_distinct_counts"] = int(g.n_distinct_urls.isna().sum())
    hd = g.groupby(["pdate", "host"], as_index=False)[["n_distinct_urls", "n_price_distinct"]].sum()
    hd = hd.merge(dayv[["pdate", "valid_day"]], on="pdate", how="left")
    hd["valid_day"] = hd.valid_day.fillna(False).astype(bool)
    hd["outlet_ok"] = bi.outlet_day_ok(hd, "host", "n_distinct_urls", P)
    hd = hd[hd.valid_day & hd.outlet_ok]
    hd["month"] = pd.PeriodIndex(pd.to_datetime(hd.pdate), freq="M").astype(str)
    hm = hd.groupby(["month", "host"], as_index=False)[["n_distinct_urls", "n_price_distinct"]].sum()
    hm = hm[(hm.n_distinct_urls >= P["min_window_articles"]) & hm.host.isin(core14)]
    hm["a"] = hm.n_price_distinct / hm.n_distinct_urls
    ms = hm.groupby("month").agg(ipi_matched=("a", "mean"), n_outlets=("host", "nunique"), n_art=("n_distinct_urls", "sum"))
    mon = pd.read_csv(ROOT / "data/processed/index/ipi_monthly.csv").set_index("month")
    mon = mon[mon.usable_d23].join(ms, how="left")
    mon.reset_index()[["month", "ipi_matched", SW["monthly_column"], "n_outlets", "n_art"]].to_csv(OUT / "matched_monthly.csv", index=False)
    info["matched_corr_with_paper_monthly"] = float(mon[["ipi_matched", SW["monthly_column"]]].corr().iloc[0, 1])
    info["matched_months"] = int(mon.ipi_matched.notna().sum())
    info["matched_outlets_per_month"] = dict(min=int(mon.n_outlets.min()), median=float(mon.n_outlets.median()),
                                             max=int(mon.n_outlets.max()))
    mm = mon.assign(m=pd.PeriodIndex(mon.index, freq="M")).set_index("m")
    v = validate(mm, "ipi_matched", "n_art", "matched (window construction)", d17) + \
        validate(mm, SW["monthly_column"], "n_articles_core", "paper monthly (price family)", d17)
    pd.DataFrame(v).to_csv(OUT / "matched_validation.csv", index=False)
    (OUT / "heavy_info.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info, indent=1, default=str))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = frame()
    if "--heavy" in sys.argv:
        heavy(df)
        return 0
    expectation_robustness(df).to_csv(OUT / "expectation_robustness.csv", index=False)
    oc, by_year, summ = outlet_composition(df)
    oc.to_csv(OUT / "outlet_composition.csv", index=False)
    by_year.to_csv(OUT / "outlets_by_year.csv", index=False)
    (OUT / "outlet_summary.json").write_text(json.dumps(summ, indent=1))
    joint_lp_test().to_csv(OUT / "joint_lp_test.csv", index=False)
    print("light done", summ)
    return 0


if __name__ == "__main__":
    sys.exit(main())
