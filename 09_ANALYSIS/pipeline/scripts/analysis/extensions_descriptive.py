"""Phase 2 descriptive versions (MV) of E2, E4, E5 (design_final D24, D25, D29). Prediction / association language
only; no causal claims. Gates that depend on the audit (E2 recall gate D29, E4 kappa gate D25) are PENDING until
audit_metrics.py has run; until then every regression row is labelled gate_status = "PENDING (descriptive only)".

Uses phase1.assemble() so the sample, controls and inference (EWC/fixed-b, wild bootstrap) match D19 exactly.

Outputs (data/processed/results/)
  e5_asym_lp.csv          monthly LP of the IPI on CPI y/y increases vs decreases (and deseasonalised m/m), h=0..12
  e5_peaks.csv            attention peaks and decay half-lives (coarse under L3: grid days only)
  e5_excess_attention.csv ExcessAttention during disinflation entered in the D19 specification
  e4_sint_window.csv      S^int (share of inflation articles co-occurring with international themes) by round
  e4_d19.csv              S^int alongside the IPI in the D19 specification
  e2_series_window.csv    z-scored IPI_eng / IPI_ver by round; e2_d19.csv national rows; e2_leadlag_monthly.csv
  ext_figures/*.png       one figure per extension
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase1 as p1  # noqa: E402

PENDING = "PENDING audit gate (descriptive only)"


def zs(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std()


def spec(y: str = "y1_median") -> list[str]:
    return [f"{y}_lag", f"d_{y}_lag", "cpi_rt", "food_rt", "d_repo", "mode_phone"]


def e5(root: Path, df: pd.DataFrame, out: Path) -> dict:
    mon = pd.read_csv(root / "data/processed/index/ipi_monthly.csv")
    mon = mon[mon.usable_d23].copy()
    mon["ipi_monthly"] = mon[os.environ.get("MONTHLY_COL", "ipi_monthly")]  # switch-aware (env MONTHLY_COL)
    mon["m"] = pd.PeriodIndex(mon.month, freq="M")
    cpi = p1.load_cpi(root)
    m = mon.set_index("m")[["ipi_monthly"]].join(cpi[["cpi", "cpi_yoy"]], how="left")
    m = m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"))
    m["z"] = zs(m.ipi_monthly)
    d = m.cpi_yoy.diff()
    m["d_pos"], m["d_neg"] = d.clip(lower=0), d.clip(upper=0)
    mm = 100 * np.log(m.cpi).diff()
    moy = pd.Series(m.index.month, index=m.index)
    mm_sa = mm - mm.groupby(moy).transform("mean")
    m["sa_pos"], m["sa_neg"] = mm_sa.clip(lower=0), mm_sa.clip(upper=0)
    rows = []
    for kind, (pos, neg) in {"yoy_change": ("d_pos", "d_neg"), "mm_deseasonalised": ("sa_pos", "sa_neg")}.items():
        for h in range(13):
            x = pd.DataFrame({"y": m.z.shift(-h), "pos": m[pos], "neg": m[neg], "ylag": m.z.shift(1)}).dropna()
            if len(x) < 20:
                continue
            X = np.column_stack([np.ones(len(x)), x.pos, x.neg, x.ylag])
            b, e = p1.ols(x.y.to_numpy(float), X)
            se, B = p1.ewc_se(X, e)
            tc = p1.tcrit(B)
            rows.append(dict(shock=kind, h=h, N=len(x), beta_pos=b[1], pos_ci_lo=b[1] - tc * se[1], pos_ci_hi=b[1] + tc * se[1],
                             beta_neg=b[2], neg_ci_lo=b[2] - tc * se[2], neg_ci_hi=b[2] + tc * se[2], dof_B=B))
    pd.DataFrame(rows).to_csv(out / "e5_asym_lp.csv", index=False)

    # peaks and half-lives on a 3-month centred moving average of the monthly IPI
    ma = m.ipi_monthly.rolling(3, center=True, min_periods=2).mean()
    thr = ma.quantile(0.75)
    peaks = []
    vals = ma.to_numpy()
    for i in range(len(vals)):
        lo, hi = max(0, i - 6), min(len(vals), i + 7)
        if np.isnan(vals[i]) or vals[i] < thr or vals[i] < np.nanmax(vals[lo:hi]):
            continue
        base = np.nanmin(vals[max(0, i - 12):i + 1])
        half = base + (vals[i] - base) / 2
        after = np.where(vals[i + 1:] <= half)[0]
        before = np.where(vals[:i][::-1] <= half)[0]
        peaks.append(dict(peak_month=str(ma.index[i]), peak_value=vals[i], baseline_prior12=base,
                          rise_months_to_peak=int(before[0] + 1) if len(before) else None,
                          half_life_months=int(after[0] + 1) if len(after) else None,
                          note="coarse: grid days only under L3"))
    pk = pd.DataFrame(peaks)
    pk.to_csv(out / "e5_peaks.csv", index=False)

    # ExcessAttention during disinflation in the D19 spec (window level)
    d = df[df.cpi_base2012.fillna(False)].copy()
    ok = d[["ipi_primary", "cpi_rt"]].dropna()
    b, _ = p1.ols(ok.ipi_primary.to_numpy(float), np.column_stack([np.ones(len(ok)), ok.cpi_rt]))
    d["resid_ipi_cpi"] = d.ipi_primary - (b[0] + b[1] * d.cpi_rt)
    d["disinfl"] = (d.cpi_rt < d.cpi_rt.shift(1)).astype(float).where(d.cpi_rt.shift(1).notna())
    d["excess_attention"] = zs(d.resid_ipi_cpi) * d.disinfl
    r = [p1.fit_row(d, "y1_median_h0", ["excess_attention", "ipi_z"] + spec(), "excess_attention",
                    "E5 ExcessAttention (disinflation) in D19 spec"),
         p1.fit_row(d, "y1_median_h0", ["ipi_z", "excess_attention"] + spec(), "ipi_z",
                    "E5 IPI with ExcessAttention control")]
    pd.DataFrame(r).to_csv(out / "e5_excess_attention.csv", index=False)
    return dict(m=m, pk=pk, excess=r)


def e4(root: Path, df: pd.DataFrame, out: Path) -> dict:
    co = pd.read_csv(root / "data/processed/index/cooccurrence_window.csv")
    s = co[["round", "n_infl_articles", "cooc_family_international"]].rename(columns={"cooc_family_international": "s_int"})
    s.to_csv(out / "e4_sint_window.csv", index=False)
    d = df.merge(s, on="round", how="left")
    d = d[d.cpi_base2012.fillna(False)].copy()
    d["s_int_z"] = zs(d.s_int)
    rows = [p1.fit_row(d, "y1_median_h0", ["s_int_z", "ipi_z"] + spec(), "s_int_z", "E4 S^int alongside IPI (D19 spec)"),
            p1.fit_row(d, "y1_median_h0", ["ipi_z", "s_int_z"] + spec(), "ipi_z", "E4 IPI with S^int control")]
    t = pd.DataFrame(rows)
    t["gate_status"] = PENDING
    t["label_rule"] = "'share of inflation articles co-occurring with international themes'; not a cause measure"
    t.to_csv(out / "e4_d19.csv", index=False)
    return dict(s=s, t=t, corr_sint_ipi=float(d[["s_int", "ipi_primary"]].corr().iloc[0, 1]))


def e2(root: Path, df: pd.DataFrame, out: Path) -> dict:
    d = df[df.cpi_base2012.fillna(False)].copy()
    d["eng_z"], d["ver_z"] = zs(d.ipi_eng), zs(d.ipi_ver)
    d[["round", "ipi_eng", "ipi_ver", "eng_z", "ver_z"]].to_csv(out / "e2_series_window.csv", index=False)
    rows = []
    for y in ("y1_median", "cur_median"):
        for c in ("eng_z", "ver_z"):
            rows.append(p1.fit_row(d, f"{y}_h0", [c] + spec(y), c, f"E2 {c[:3]} only, D19 spec ({y})"))
        rows.append(p1.fit_row(d, f"{y}_h0", ["ver_z", "eng_z"] + spec(y), "ver_z", f"E2 ver with eng control ({y})"))
    t = pd.DataFrame(rows)
    t["gate_status"] = PENDING
    t["note"] = "H7 two-sided exploratory; national comparison has almost no power (D29)"
    t.to_csv(out / "e2_d19.csv", index=False)
    mon = pd.read_csv(root / "data/processed/index/ipi_monthly.csv")
    mon = mon[mon.usable_d23].dropna(subset=["ipi_monthly_eng", "ipi_monthly_ver"])
    e, v = zs(mon.ipi_monthly_eng).to_numpy(), zs(mon.ipi_monthly_ver).to_numpy()
    ll = [dict(lag_ver_minus_eng=k, corr=float(np.corrcoef(e[max(0, -k):len(e) - max(0, k)],
                                                           v[max(0, k):len(v) - max(0, -k)])[0, 1]),
               N=len(e) - abs(k)) for k in range(-6, 7)]
    pd.DataFrame(ll).to_csv(out / "e2_leadlag_monthly.csv", index=False)
    return dict(t=t, corr_window=float(d[["ipi_eng", "ipi_ver"]].corr().iloc[0, 1]), ll=pd.DataFrame(ll), d=d, mon=mon)


def figures(out: Path, r5, r4, r2) -> bool:
    try:
        import matplotlib
    except ImportError:
        print("matplotlib not installed: figures skipped (tables written)")
        return False
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fd = out / "ext_figures"
    fd.mkdir(exist_ok=True)
    m = r5["m"]
    fig, ax = plt.subplots(figsize=(9, 3.5))
    x = m.index.to_timestamp()
    ax.plot(x, m.ipi_monthly * 100, color="#2a6f97", lw=1.2, label="IPI monthly (% of articles)")
    ax2 = ax.twinx(); ax2.plot(x, m.cpi_yoy, color="#9a3412", lw=1, label="CPI y/y (%)")
    for p in r5["pk"].peak_month:
        ax.axvline(pd.Period(p, "M").to_timestamp(), color="grey", lw=0.6, ls=":")
    ax.set_ylabel("IPI, % of articles"); ax2.set_ylabel("CPI y/y, %")
    ax.set_title("E5: monthly IPI and CPI inflation (dotted: attention peaks)")
    fig.legend(loc="upper left", fontsize=8); fig.tight_layout(); fig.savefig(fd / "e5_ipi_cpi_peaks.png", dpi=150); plt.close(fig)
    s = r4["s"]
    fig, ax = plt.subplots(figsize=(9, 3)); ax.plot(range(len(s)), s.s_int * 100, marker="o", ms=3, color="#2a6f97")
    ax.set_xticks(range(0, len(s), 6)); ax.set_xticklabels(s["round"].iloc[::6], rotation=45, fontsize=7)
    ax.set_ylabel("% of inflation articles"); ax.set_title("E4: share of inflation articles co-occurring with international themes")
    fig.tight_layout(); fig.savefig(fd / "e4_sint.png", dpi=150); plt.close(fig)
    d = r2["d"]
    fig, ax = plt.subplots(figsize=(9, 3)); ax.plot(range(len(d)), d.eng_z, label="English (z)", color="#2a6f97")
    ax.plot(range(len(d)), d.ver_z, label="Vernacular (z)", color="#9a3412")
    ax.set_xticks(range(0, len(d), 6)); ax.set_xticklabels(d["round"].iloc[::6], rotation=45, fontsize=7)
    ax.legend(fontsize=8); ax.set_title("E2: window IPI, English vs vernacular outlets (core 2018)")
    fig.tight_layout(); fig.savefig(fd / "e2_eng_ver.png", dpi=150); plt.close(fig)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args()
    p1.IPI_COL = os.environ.get("IPI_COL", "ipi_primary")  # switch-aware: final flag via env (d9_switch.json)
    out = a.root / os.environ.get("EXT_OUT", "data/processed/results")
    out.mkdir(parents=True, exist_ok=True)
    df = p1.assemble(a.root)
    r5, r4, r2 = e5(a.root, df, out), e4(a.root, df, out), e2(a.root, df, out)
    figs = figures(out, r5, r4, r2)
    lines = ["# Extensions E2, E4, E5: descriptive versions (auto-generated; association language only)", "",
             f"Figures: {'written to ext_figures/' if figs else 'NOT produced (matplotlib missing)'}.",
             f"Index column: {p1.IPI_COL}; E2 language splits use the baseline tag (no price-family language split built).", "",
             "## E5 ExcessAttention", pd.DataFrame(r5["excess"])[["model", "N", "beta", "ci_lo", "ci_hi", "p_wild"]].to_markdown(index=False),
             "", "## E5 peaks", r5["pk"].to_markdown(index=False),
             "", f"## E4 S^int (corr with IPI {r4['corr_sint_ipi']:.2f})", r4["t"][["model", "N", "beta", "ci_lo", "ci_hi", "p_wild"]].to_markdown(index=False),
             "", f"## E2 (window corr eng/ver {r2['corr_window']:.2f})", r2["t"][["model", "N", "beta", "ci_lo", "ci_hi", "p_wild"]].to_markdown(index=False),
             "", "## E2 monthly lead-lag (positive lag: vernacular later)", r2["ll"].round(3).to_markdown(index=False)]
    (out / "extensions_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
