"""Phase 1 econometrics (design_final D19-D23). Prediction language only: 'predicts', never 'causes'.

Inputs (under --root):
  data/processed/index/ipi_window.csv        round, ipi_primary, robustness rows (build_index.py)
  data/processed/index/ipi_monthly.csv       month, ipi_monthly, days_used, usable_d23
  data/processed/iesh_national_excel.csv     RBI time series (survey_ended = round key)
  data/raw/iesh_rounds.csv                   round, fieldwork_start, mode, fs_rule
  data/processed/cpi2012_group_state.csv     MoSPI CPI base 2012 (All India Combined general + food)
  data/processed/markets_monthly.csv         Brent etc.
  data/raw/policy/repo_rate.csv              date,repo  (policy-rate changes; effective dates)
Outputs: data/processed/results/*.csv and phase1_summary.md

Declared rules (recorded in docs/analysis_plan.md before outcomes were merged):
  * Primary outcome = 1-year MEDIAN (D7 rule: the mean changed definition in Sep 2018). Mean in every table.
  * Continuous variant = published 1-year mean (bin distribution not available for all rounds).
  * IPI enters standardised (per SD over the estimation sample); beta = survey points per 1 SD of IPI.
  * Real-time CPI = latest y/y released by window end (MoSPI releases month m around the 12th of m+1).
  * DoCA unavailable/ends 2023 -> food CPI y/y is the food-price control (D19 fallback).
  * CPI-controlled regressions end with rounds whose real-time CPI is base-2012 (<= Dec 2025 data) (D7).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261121)
B_BOOT = 1999


# ----------------------------------------------------------------------------- basic OLS + inference
def ols(y: np.ndarray, X: np.ndarray):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    return beta, e


def ewc_se(X: np.ndarray, e: np.ndarray, B: int | None = None):
    """Equal-weighted cosine (EWC) HAR variance (Lazarus, Lewis, Stock & Watson 2018). Returns (se, dof B).
    Fixed-b inference: t-stat ~ t_B. Default B = ceil(0.4 * T^(2/3))."""
    T, k = X.shape
    B = B or max(2, int(math.ceil(0.4 * T ** (2 / 3))))
    t = np.arange(1, T + 1)
    u = X * e[:, None]
    omega = np.zeros((k, k))
    for j in range(1, B + 1):
        w = math.sqrt(2 / T) * np.cos(math.pi * j * (t - 0.5) / T)
        L = w @ u
        omega += np.outer(L, L)
    omega /= B
    XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ (T * omega) @ XtXi  # omega = long-run variance of x_t e_t

    return np.sqrt(np.diag(V)), B


def tcrit(B: int, alpha: float = 0.05) -> float:
    from scipy import stats
    return float(stats.t.ppf(1 - alpha / 2, B))


def wild_boot_p(y, X, j: int, B: int = B_BOOT) -> float:
    """Restricted wild bootstrap (Rademacher) p-value for H0: beta_j = 0, using the EWC t-stat."""
    beta, e = ols(y, X)
    se, dof = ewc_se(X, e)
    t0 = beta[j] / se[j]
    Xr = np.delete(X, j, axis=1)
    br, er = ols(y, Xr)
    fit_r = Xr @ br
    cnt = 0
    for _ in range(B):
        v = RNG.choice([-1.0, 1.0], size=len(y))
        yb = fit_r + er * v
        bb, eb = ols(yb, X)
        sb, _ = ewc_se(X, eb)
        cnt += abs(bb[j] / sb[j]) >= abs(t0)
    return (cnt + 1) / (B + 1)


def partial_r2(y, X, j):
    _, e_full = ols(y, X)
    _, e_r = ols(y, np.delete(X, j, axis=1))
    return 1 - (e_full @ e_full) / (e_r @ e_r)


def fit_row(df: pd.DataFrame, yname: str, xnames: list[str], focus: str, label: str, boot: bool = True) -> dict:
    d = df[[yname] + xnames].dropna()
    xnames = [c for c in xnames if c == focus or d[c].std() > 0]  # drop controls constant in this sample
    if len(d) < len(xnames) + 5:
        return dict(model=label, outcome=yname, N=len(d), note="too few obs")
    y = d[yname].to_numpy(float)
    X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in xnames])
    beta, e = ols(y, X)
    se, B = ewc_se(X, e)
    j = 1 + xnames.index(focus)
    tc = tcrit(B)
    return dict(model=label, outcome=yname, focus=focus, N=len(d), beta=beta[j], se_ewc=se[j], dof_B=B,
                ci_lo=beta[j] - tc * se[j], ci_hi=beta[j] + tc * se[j], t=beta[j] / se[j],
                p_wild=wild_boot_p(y, X, j) if boot else np.nan, partial_r2=partial_r2(y, X, j),
                r2=1 - (e @ e) / ((y - y.mean()) @ (y - y.mean())), controls=";".join(c for c in xnames if c != focus))


# ----------------------------------------------------------------------------- data assembly
def realtime_cpi_month(window_end: dt.date) -> pd.Period:
    m = pd.Period(window_end, "M")
    return m - 1 if window_end.day >= 12 else m - 2


def load_cpi(root: Path) -> pd.DataFrame:
    """All-India Combined general and consumer-food-price indices (base 2012), from build_cpi.py output."""
    c = pd.read_csv(root / "data/processed/cpi2012_allindia.csv")
    c = c[c.sector == "Combined"]
    c["m"] = pd.PeriodIndex(c.period, freq="M")
    gen = c[c.subgroup == "General-Overall"].groupby("m")["index"].mean()
    food = c[c.subgroup == "Consumer Food Price-Overall"].groupby("m")["index"].mean()
    out = pd.DataFrame({"cpi": gen, "food": food}).sort_index()
    out = out.reindex(pd.period_range(out.index.min(), out.index.max(), freq="M"))
    out["cpi_yoy"] = 100 * (out.cpi / out.cpi.shift(12) - 1)
    out["food_yoy"] = 100 * (out.food / out.food.shift(12) - 1)
    return out


def load_markets(root: Path) -> pd.Series:
    mk = pd.read_csv(root / "data/processed/markets_monthly.csv")
    mk["m"] = pd.PeriodIndex(mk["month"].astype(str).str[:7], freq="M")
    return mk.set_index("m")["brent_usd_avg"]


IPI_COL = "ipi_primary"  # D9/D17 switch chain may set another window column via --ipi-col
MONTHLY_COL = "ipi_monthly"


def assemble(root: Path) -> pd.DataFrame:
    ipi = pd.read_csv(root / "data/processed/index/ipi_window.csv")
    if IPI_COL != "ipi_primary":
        ipi["ipi_primary_baseline"] = ipi["ipi_primary"]
        ipi["ipi_primary"] = ipi[IPI_COL]
    nat = pd.read_csv(root / "data/processed/iesh_national_excel.csv", dtype={"round_no": str})
    rounds = pd.read_csv(root / "data/raw/iesh_rounds.csv")
    df = ipi.merge(rounds[["round", "fieldwork_start", "fs_rule", "mode"]], on="round", how="left")
    df = df.merge(nat.rename(columns={"survey_ended": "round"}), on="round", how="left")
    df["fs"] = pd.to_datetime(df.fieldwork_start).dt.date
    df = df.sort_values("fs").reset_index(drop=True)
    cpi = load_cpi(root)
    rt = df.fs.map(lambda d: realtime_cpi_month(d - dt.timedelta(days=1)))
    df["cpi_rt"] = rt.map(cpi.cpi_yoy)
    df["food_rt"] = rt.map(cpi.food_yoy)
    df["cpi_month_of_survey"] = df.fs.map(lambda d: pd.Period(d, "M")).map(cpi.cpi_yoy)  # future-CPI test
    df["cpi_base2012"] = rt.map(lambda p: p <= pd.Period("2025-12", "M"))
    brent = load_markets(root)
    wm = df.fs.map(lambda d: pd.Period(d - dt.timedelta(days=1), "M"))
    df["dln_brent"] = [100 * (math.log(brent.get(m, np.nan)) - math.log(brent.get(m - 2, np.nan)))
                       if brent.get(m) and brent.get(m - 2) else np.nan for m in wm]
    rp = root / "data/raw/policy/repo_rate.csv"
    if rp.exists():
        r = pd.read_csv(rp, parse_dates=["date"]).sort_values("date")
        df["repo"] = [r.loc[r.date.dt.date <= d - dt.timedelta(days=1), "repo"].iloc[-1]
                      if (r.date.dt.date <= d - dt.timedelta(days=1)).any() else np.nan for d in df.fs]
        df["d_repo"] = df.repo.diff()
    else:
        df["d_repo"] = np.nan
    md = df["mode"].astype(str).str.lower()
    df["mode_phone"] = md.str.contains("tele|phone").astype(float)
    df["covid"] = df.fs.map(lambda d: dt.date(2020, 3, 1) <= d <= dt.date(2021, 12, 31)).astype(float)
    for y in ("y1_median", "y1_mean", "m3_median", "cur_median"):
        df[f"{y}_lag"] = df[y].shift(1)
        df[f"d_{y}_lag"] = df[y].shift(1) - df[y].shift(2)
        for h in range(4):
            df[f"{y}_h{h}"] = df[y].shift(-h) - df[y].shift(1)
    mu, sd = df.ipi_primary.mean(), df.ipi_primary.std()
    df["ipi_z"] = (df.ipi_primary - mu) / sd
    df["d_ipi_z"] = df.ipi_z.diff()
    for c in [c for c in df.columns if c.startswith("row_") or c.startswith("variant_") or c == "ipi_core2018_with_vernacular"]:
        df[c + "_z"] = (df[c] - df[c].mean()) / df[c].std()
    df["high_lag"] = (df.cpi_rt.shift(1) > 6).astype(float).where(df.cpi_rt.shift(1).notna())
    return df


# ----------------------------------------------------------------------------- D19 / D20
def d19(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cpi_ok = df[df.cpi_base2012.fillna(False)]
    core = ["cpi_rt", "food_rt", "d_repo", "mode_phone"]
    if df.d_repo.isna().all():
        core = ["cpi_rt", "food_rt", "mode_phone"]
    for y in ("y1_median", "y1_mean", "m3_median", "cur_median"):
        for h in range(4):
            base = [f"{y}_lag", f"d_{y}_lag"]
            rows.append(fit_row(cpi_ok, f"{y}_h{h}", ["ipi_z"] + base + core, "ipi_z", f"D19 primary-spec h={h}",
                                boot=(h == 0)))
        rows.append(fit_row(cpi_ok, f"{y}_h0", ["ipi_z", f"{y}_lag", f"d_{y}_lag", "cpi_rt"], "ipi_z", "D19 AR+CPI only"))
        rows.append(fit_row(cpi_ok, f"{y}_h0", ["ipi_z", f"{y}_lag", f"d_{y}_lag"] + core + ["dln_brent"], "ipi_z",
                            "D19 full set (pump price unavailable)"))
        rows.append(fit_row(cpi_ok, f"{y}_h0", ["d_ipi_z", f"{y}_lag", f"d_{y}_lag"] + core, "d_ipi_z", "D19 dIPI variant"))
        rows.append(fit_row(cpi_ok, f"{y}_h0", ["ipi_z", f"{y}_lag", f"d_{y}_lag"] + core + ["cpi_month_of_survey"],
                            "ipi_z", "D19 future-CPI test"))
    y = "y1_median"
    spec = [f"{y}_lag", f"d_{y}_lag"] + core
    sub = cpi_ok[cpi_ok.covid == 0]
    rows.append(fit_row(sub, f"{y}_h0", ["ipi_z"] + spec, "ipi_z", "D19 drop 2020-21"))
    rows.append(fit_row(cpi_ok[cpi_ok.fs_rule == "exact"], f"{y}_h0", ["ipi_z"] + spec, "ipi_z",
                        "D19 exact-fieldwork rounds only (ruling b check)"))
    for c in [c for c in df.columns if c.endswith("_z") and c not in ("ipi_z", "d_ipi_z")]:
        rows.append(fit_row(cpi_ok, f"{y}_h0", [c] + spec, c, f"D11 robustness {c[:-2]}"))
    return pd.DataFrame(rows)


def d20(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df.cpi_base2012.fillna(False)].copy()
    y = "y1_median"
    core = ["cpi_rt", "food_rt", "mode_phone"] + ([] if d.d_repo.isna().all() else ["d_repo"])
    d["ipi_x_high"] = d.ipi_z * d.high_lag
    d["ipi_x_cont"] = d.ipi_z * (d.cpi_rt.shift(1) - 4)
    base = [f"{y}_lag", f"d_{y}_lag"] + core
    rows = [fit_row(d, f"{y}_h0", ["ipi_x_high", "ipi_z", "high_lag"] + base, "ipi_x_high", "D20 IPI x High"),
            fit_row(d, f"{y}_h0", ["ipi_x_cont", "ipi_z"] + base, "ipi_x_cont", "D20 IPI x (CPI-4)"),
            fit_row(d[d.covid == 0], f"{y}_h0", ["ipi_x_high", "ipi_z", "high_lag"] + base, "ipi_x_high",
                    "D20 IPI x High, excl 2020-21")]
    # leave-one-episode-out: episodes = maximal runs of high_lag == 1
    ep = (d.high_lag.fillna(0).diff().fillna(0) == 1).cumsum().where(d.high_lag == 1)
    for e in sorted(ep.dropna().unique()):
        rows.append(fit_row(d[ep != e], f"{y}_h0", ["ipi_x_high", "ipi_z", "high_lag"] + base, "ipi_x_high",
                            f"D20 leave out high episode {int(e)}", boot=False))
    out = pd.DataFrame(rows)
    out["N_high"] = int((d.high_lag == 1).sum())
    out["N_low"] = int((d.high_lag == 0).sum())
    return out


# ----------------------------------------------------------------------------- D21 small BVAR (appendix)
def bvar(df: pd.DataFrame, order: list[str], p: int = 2, lam: float = 0.2, H: int = 6) -> pd.DataFrame:
    Y = df[order].dropna().to_numpy(float)
    T, n = Y.shape
    sig = np.array([np.std(np.diff(Y[:, i])) or 1.0 for i in range(n)])
    Xs = [np.ones((T - p, 1))] + [Y[p - l - 1:T - l - 1] for l in range(p)]
    X, Yt = np.hstack(Xs), Y[p:]
    # Minnesota prior via dummy observations (random-walk mean, tightness lam, lag decay l^-1)
    Yd, Xd = [], []
    for l in range(1, p + 1):
        for i in range(n):
            yrow = np.zeros(n); xrow = np.zeros(1 + n * p)
            if l == 1:
                yrow[i] = sig[i] / lam
            xrow[1 + (l - 1) * n + i] = sig[i] * l / lam
            Yd.append(yrow); Xd.append(xrow)
    Xa, Ya = np.vstack([X, np.array(Xd)]), np.vstack([Yt, np.array(Yd)])
    Bh = np.linalg.lstsq(Xa, Ya, rcond=None)[0]
    U = Yt - X @ Bh
    S = U.T @ U / (len(Yt) - X.shape[1])
    P = np.linalg.cholesky(S)
    A = [Bh[1 + l * n:1 + (l + 1) * n].T for l in range(p)]
    irf = np.zeros((H + 1, n, n))
    state = [P] + [np.zeros((n, n))] * (p - 1)
    irf[0] = P
    for h in range(1, H + 1):
        nxt = sum(A[l] @ state[l] for l in range(p))
        state = [nxt] + state[:-1]
        irf[h] = nxt
    j_ipi, j_y = order.index("ipi_primary"), order.index("y1_median")
    return pd.DataFrame({"h": range(H + 1), "resp_y1_to_ipi_shock": irf[:, j_y, j_ipi],
                         "order": ">".join(order), "T": T})


# ----------------------------------------------------------------------------- D22 pseudo-real-time
def d22(df: pd.DataFrame, start: int = 20) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = df[df.cpi_base2012.fillna(False)].dropna(subset=["y1_median", "y1_median_lag", "cpi_rt", "food_rt", "ipi_z"])
    d = d.reset_index(drop=True)
    models = {"AR1": ["y1_median_lag"], "AR1+CPI+food": ["y1_median_lag", "cpi_rt", "food_rt"],
              "HEADLINE AR1+CPI+food+IPI": ["y1_median_lag", "cpi_rt", "food_rt", "ipi_z"]}
    preds = []
    for t in range(start, len(d)):
        tr, te = d.iloc[:t], d.iloc[t]
        row = {"round": te["round"], "actual": te.y1_median}
        for name, xs in models.items():
            X = np.column_stack([np.ones(len(tr))] + [tr[c] for c in xs])
            b, _ = ols(tr.y1_median.to_numpy(float), X)
            row[name] = float(np.r_[1.0, te[xs].to_numpy(float)] @ b)
        preds.append(row)
    P = pd.DataFrame(preds)
    res = []
    for bench in ("AR1", "AR1+CPI+food"):
        h = "HEADLINE AR1+CPI+food+IPI"
        e1, e2 = P.actual - P[bench], P.actual - P[h]
        ratio = math.sqrt((e2 ** 2).mean() / (e1 ** 2).mean())
        bs = []
        for _ in range(B_BOOT):
            ix = RNG.integers(0, len(P), len(P))
            bs.append(math.sqrt((e2.iloc[ix] ** 2).mean() / (e1.iloc[ix] ** 2).mean()))
        # Clark-West (2007): f = e1^2 - [e2^2 - (yhat1 - yhat2)^2]; one-sided t
        f = e1 ** 2 - (e2 ** 2 - (P[bench] - P[h]) ** 2)
        Xc = np.ones((len(f), 1))
        se, B = ewc_se(Xc, (f - f.mean()).to_numpy(float))
        from scipy import stats
        tcw = f.mean() / se[0]
        res.append(dict(benchmark=bench, model=h, n_eval=len(P), rmse_ratio=ratio,
                        ci_lo=np.percentile(bs, 2.5), ci_hi=np.percentile(bs, 97.5),
                        clark_west_t=tcw, clark_west_p_one_sided=1 - stats.t.cdf(tcw, B)))
    return P, pd.DataFrame(res)


# ----------------------------------------------------------------------------- D23 monthly LP
def d23(root: Path, H: int = 12) -> pd.DataFrame:
    mon = pd.read_csv(root / "data/processed/index/ipi_monthly.csv")
    mon = mon[mon.usable_d23].copy()
    mon["ipi_monthly"] = mon[MONTHLY_COL]
    mon["m"] = pd.PeriodIndex(mon.month, freq="M")
    cpi = load_cpi(root)
    s = cpi.cpi_yoy.dropna()
    surpr = {}
    for i in range(36, len(s)):  # recursive AR(12) one-step surprises
        hist = s.iloc[:i].to_numpy()
        Y = hist[12:]
        X = np.column_stack([np.ones(len(Y))] + [hist[12 - l:len(hist) - l] for l in range(1, 13)])
        b, _ = ols(Y, X)
        f = np.r_[1.0, hist[-1:-13:-1]] @ b
        surpr[s.index[i]] = s.iloc[i] - f
    br = np.log(load_markets(root)).diff() * 100
    m = mon.set_index("m")
    m["z"] = (m.ipi_monthly - m.ipi_monthly.mean()) / m.ipi_monthly.std()
    m["cpi_surprise"] = pd.Series(surpr)
    m["brent_shock"] = br
    full = m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"))
    rows = []
    for shock in ("cpi_surprise", "brent_shock"):
        for h in range(H + 1):
            d = pd.DataFrame({"y": full.z.shift(-h), "s": full[shock], "ylag": full.z.shift(1)}).dropna()
            if len(d) < 15:
                continue
            X = np.column_stack([np.ones(len(d)), d.s, d.ylag])
            b, e = ols(d.y.to_numpy(float), X)
            se, B = ewc_se(X, e)
            rows.append(dict(shock=shock, h=h, beta=b[1], se_ewc=se[1], dof_B=B, N=len(d)))
    return pd.DataFrame(rows)


def persistence(df: pd.DataFrame) -> pd.DataFrame:
    try:
        from statsmodels.tsa.stattools import adfuller, kpss
    except ImportError:
        return pd.DataFrame([{"note": "statsmodels not installed"}])
    rows = []
    for c in ("y1_median", "ipi_primary"):
        x = df[c].dropna()
        rows.append(dict(series=c, adf_stat=adfuller(x, autolag="AIC")[0], adf_p=adfuller(x, autolag="AIC")[1],
                         kpss_stat=kpss(x, nlags="auto")[0], kpss_p=kpss(x, nlags="auto")[1], N=len(x)))
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--no-boot", action="store_true")
    ap.add_argument("--ipi-col", default="ipi_primary", help="window index column used as the primary (D9 switch)")
    ap.add_argument("--out", default="data/processed/results", help="output directory relative to --root")
    ap.add_argument("--monthly-col", default="ipi_monthly")
    a = ap.parse_args()
    global B_BOOT, IPI_COL, MONTHLY_COL
    IPI_COL, MONTHLY_COL = a.ipi_col, a.monthly_col
    if a.no_boot:
        B_BOOT = 99
    out = a.root / a.out
    out.mkdir(parents=True, exist_ok=True)
    df = assemble(a.root)
    df.to_csv(out / "phase1_panel.csv", index=False)
    t19, t20 = d19(df), d20(df)
    t19.to_csv(out / "d19_national_lp.csv", index=False)
    t20.to_csv(out / "d20_regime.csv", index=False)
    persistence(df).to_csv(out / "d19_persistence.csv", index=False)
    dv = df[df.cpi_base2012.fillna(False)]
    v = [bvar(dv, ["dln_brent", "cpi_rt", "ipi_primary", "y1_median"] + ([] if dv.d_repo.isna().all() else ["repo"])),
         bvar(dv, ["dln_brent", "cpi_rt", "y1_median", "ipi_primary"] + ([] if dv.d_repo.isna().all() else ["repo"]))]
    pd.concat(v).to_csv(out / "d21_bvar_irf.csv", index=False)
    P, r22 = d22(df)
    P.to_csv(out / "d22_predictions.csv", index=False)
    r22.to_csv(out / "d22_forecast_eval.csv", index=False)
    if (a.root / "data/processed/index/ipi_monthly.csv").exists():
        d23(a.root).to_csv(out / "d23_monthly_lp.csv", index=False)
    prim = t19[(t19.model == "D19 primary-spec h=0") & (t19.outcome == "y1_median_h0")]
    lines = ["# Phase 1 summary (auto-generated; prediction language only)", "",
             f"Rounds in panel: {len(df)}; CPI-controlled sample: {int(df.cpi_base2012.fillna(False).sum())}", "",
             "## Primary cell (D19: 1-year median, h=0, IPI per 1 SD)", prim.to_markdown(index=False) if len(prim) else "n/a",
             "", "## D22 pseudo-real-time", r22.to_markdown(index=False)]
    (out / "phase1_summary.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
