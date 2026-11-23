"""Paper outputs added after the Sonnet review (23 Nov 2026). Descriptive and in-sample only; no causal language.

Uses the final flag from results/d9_switch.json (baseline if absent) and the same assembly and estimator as
phase1.py, so every number here is reproducible from the same inputs.
Outputs (results dir of the final flag; figures in results/paper_figures/):
  paper_descriptives.csv      N, mean, sd, min, max of the index and the main variables (estimation sample)
  paper_sample_flow.csv       rounds -> valid window -> outcome lags -> real-time CPI (2012 base) -> estimation N
  paper_horse_race.csv        D19 primary spec with Google Trends "inflation" (z) alone and alongside the index
  paper_magnitude.json        1 SD of the window index in percentage points of article share
  fig_index_expectations.png  window index vs 1-yr median and mean expectations and real-time CPI y/y
  fig_coefficients.png        D19 coefficient plot: horizons h=0..3 and index variants (95% CI)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase1 as p1  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    sw_p = ROOT / "data/processed/results/d9_switch.json"
    sw = json.loads(sw_p.read_text()) if sw_p.exists() else {"window_column": "ipi_primary", "flag_changed": False}
    p1.IPI_COL = sw["window_column"]
    res = ROOT / ("data/processed/results_switched" if sw.get("flag_changed") else "data/processed/results")
    figd = res / "paper_figures"
    figd.mkdir(parents=True, exist_ok=True)
    df = p1.assemble(ROOT)
    y = "y1_median"
    core = ["cpi_rt", "food_rt", "d_repo", "mode_phone"]
    spec = [f"{y}_lag", f"d_{y}_lag"] + core
    est = df[df.cpi_base2012.fillna(False)].dropna(subset=[f"{y}_h0", "ipi_z"] + spec)

    # sample flow
    flow = [("IESH rounds in window file", len(df)),
            ("valid news window", int(df.valid_window.astype(bool).sum()) if "valid_window" in df else len(df)),
            ("with 1-yr median expectation", int(df[y].notna().sum())),
            ("with lagged level and change (2 earlier rounds)", int(df[[f"{y}_h0", f"d_{y}_lag"]].notna().all(axis=1).sum())),
            ("real-time CPI on 2012 base available", int(df[df.cpi_base2012.fillna(False)][[f"{y}_h0", f"d_{y}_lag"]].notna().all(axis=1).sum())),
            ("estimation sample (all controls)", len(est))]
    pd.DataFrame(flow, columns=["step", "rounds"]).to_csv(res / "paper_sample_flow.csv", index=False)

    # descriptives (estimation sample)
    cols = {"ipi_primary": "news index, window article share (%)", "y1_median": "1-yr ahead expectation, median (%)",
            "y1_mean": "1-yr ahead expectation, mean (%)", "cur_median": "current perceived inflation, median (%)",
            "cpi_rt": "real-time CPI y/y (%)", "food_rt": "real-time food CPI y/y (%)", "d_repo": "change in repo rate (pp)",
            "mode_phone": "telephone survey (share)"}
    est = est.assign(ipi_primary=100 * est.ipi_primary)  # share -> percent
    d = est[list(cols)].describe().T[["count", "mean", "std", "min", "max"]]
    d.index = [cols[c] for c in d.index]
    d.round(3).to_csv(res / "paper_descriptives.csv")

    # magnitude: 1 SD of the index
    sd = float(100 * df.ipi_primary.std())  # share -> percentage points
    mag = {"index_column": p1.IPI_COL, "index_sd_pp_article_share": sd, "index_mean_pct": float(100 * df.ipi_primary.mean()),
           "index_max_pct": float(100 * df.ipi_primary.max())}
    (res / "paper_magnitude.json").write_text(json.dumps(mag, indent=1))

    # horse race with Google Trends "inflation" (fieldwork month, IN, solo)
    tr = pd.read_csv(ROOT / "data/processed/trends_monthly.csv")
    tr = tr[(tr.geo == "IN") & (tr.kind == "solo") & (tr.term == "inflation")]
    tmap = dict(zip(tr.month.astype(str), tr.value_mean))
    df["trends"] = pd.to_datetime(df.fieldwork_start).dt.to_period("M").astype(str).map(tmap)
    df["trends_z"] = (df.trends - df.trends.mean()) / df.trends.std()
    sub = df[df.cpi_base2012.fillna(False)].dropna(subset=["trends_z"])
    rows = [p1.fit_row(sub, f"{y}_h0", ["ipi_z"] + spec, "ipi_z", "index alone (Trends sample)"),
            p1.fit_row(sub, f"{y}_h0", ["trends_z"] + spec, "trends_z", "Trends alone"),
            p1.fit_row(sub, f"{y}_h0", ["ipi_z", "trends_z"] + spec, "ipi_z", "index, with Trends"),
            p1.fit_row(sub, f"{y}_h0", ["ipi_z", "trends_z"] + spec, "trends_z", "Trends, with index")]
    hr = pd.DataFrame(rows)
    hr["trends_pulls"] = int(tr.n_pulls.min()) if len(tr) else 0
    hr.to_csv(res / "paper_horse_race.csv", index=False)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib missing; figures skipped")
        return 0
    s = df.dropna(subset=["ipi_primary"]).copy()
    s["fs"] = pd.to_datetime(s.fieldwork_start)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(s.fs, 100 * s.ipi_primary, color="#1f4e79", marker="o", ms=3, label="news index (window article share, %)")
    ax.set_ylabel("news index (%)")
    ax2 = ax.twinx()
    ax2.plot(s.fs, s.y1_median, color="#c55a11", marker="s", ms=3, label="1-yr expectation, median")
    ax2.plot(s.fs, s.y1_mean, color="#c55a11", ls="--", lw=1, label="1-yr expectation, mean")
    ax2.plot(s.fs, s.cpi_rt, color="#7f7f7f", lw=1, label="real-time CPI y/y")
    ax2.set_ylabel("percent")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left", frameon=False)
    ax.set_title("News index and household inflation expectations (IESH rounds)", fontsize=9)
    fig.tight_layout(); fig.savefig(figd / "fig_index_expectations.png", dpi=200); plt.close(fig)

    lp = pd.read_csv(res / "d19_national_lp.csv")
    pick = lp[(lp.outcome.str.startswith("y1_median")) & (lp.model.str.startswith("D19 primary-spec"))].copy()
    pick["label"] = pick.model.str.replace("D19 primary-spec ", "")
    rob = lp[lp.model.str.startswith("D11 robustness") | lp.model.isin(["D19 AR+CPI only", "D19 drop 2020-21",
             "D19 exact-fieldwork rounds only (ruling b check)", "D19 dIPI variant", "D19 future-CPI test"])]
    rob = rob[rob.outcome == "y1_median_h0"].copy()
    rob["label"] = rob.model.str.replace("D11 robustness ", "").str.replace("D19 ", "")
    alt = lp[(lp.model == "D19 primary-spec h=0") & (lp.outcome != "y1_median_h0")].copy()
    alt["label"] = "outcome: " + alt.outcome.str.replace("_h0", "")
    allr = pd.concat([pick, rob, alt])
    fig, ax = plt.subplots(figsize=(6, 0.3 * len(allr) + 1))
    yy = np.arange(len(allr))[::-1]
    ax.errorbar(allr.beta, yy, xerr=[allr.beta - allr.ci_lo, allr.ci_hi - allr.beta], fmt="o", color="#1f4e79", ms=4, capsize=2)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(yy); ax.set_yticklabels(allr.label, fontsize=7)
    ax.set_xlabel("coefficient on news index (pp per SD), 95% CI")
    fig.tight_layout(); fig.savefig(figd / "fig_coefficients.png", dpi=200); plt.close(fig)
    allr[["label", "outcome", "N", "beta", "ci_lo", "ci_hi", "p_wild"]].to_csv(res / "paper_coefficients.csv", index=False)
    print(pd.DataFrame(flow).to_string(), "\n", d.round(2).to_string(), "\n", mag, "\n",
          hr[["model", "focus", "N", "beta", "ci_lo", "ci_hi", "p_wild"]].round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
