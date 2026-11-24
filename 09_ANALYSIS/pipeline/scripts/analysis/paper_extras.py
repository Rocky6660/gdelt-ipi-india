"""Extra analyses and figures for the full-length paper (FINAL_TOUCHES Part 5, 24 Nov 2026). Presentation and cheap
robustness only: no estimate, flag or specification of the main analysis is changed. Final flag from d9_switch.json.

Outputs in data/processed/results_switched/ (prefix extra_) and figures in .../paper_figures/:
  extra_robustness.csv   exclude 2024-election window; placebo outcome (previous change); presence threshold 60%/90%
                         and volume-weighted (pooled) price-family index; all in the primary specification
  extra_mde.json         minimum detectable effect (80% power, 5% two-sided) for the primary cell; count of tests
  extra_iesh_rounds.csv  round, fieldwork start, date rule, survey mode, window validity
  figures: fig_monthly_episodes, fig_horizons, fig_var_irf, fig_forecast_errors, fig_audit_prf, fig_e3_items
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
R = ROOT / "data/processed/results_switched"
F = R / "paper_figures"
EPIS = {"onion": ("2019-09", "2019-12"), "fuel": ("2021-02", "2021-10"), "post-Ukraine": ("2022-03", "2022-07"),
        "tomato": ("2023-06", "2023-08")}


def main() -> int:
    sw = json.loads((ROOT / "data/processed/results/d9_switch.json").read_text())
    p1.IPI_COL = sw["window_column"]
    df = p1.assemble(ROOT)
    y = "y1_median"
    core = ["cpi_rt", "food_rt", "d_repo", "mode_phone"]
    spec = [f"{y}_lag", f"d_{y}_lag"] + core
    base = df[df.cpi_base2012.fillna(False)]
    rows = [p1.fit_row(base, f"{y}_h0", ["ipi_z"] + spec, "ipi_z", "primary (reference)")]
    ws, we = pd.to_datetime(df.window_start), pd.to_datetime(df.window_end)
    elec = (ws <= "2024-06-04") & (we >= "2024-06-04")
    rows.append(p1.fit_row(base[~elec.loc[base.index]], f"{y}_h0", ["ipi_z"] + spec, "ipi_z",
                           f"exclude round(s) whose window contains 4 Jun 2024 ({int(elec.sum())} dropped)"))
    # placebo outcome: the previous change (t-2 -> t-1) cannot be affected by attention before round t
    base = base.assign(prev_change=base[f"d_{y}_lag"], prev_level=base[y].shift(2))
    rows.append(p1.fit_row(base, "prev_change", ["ipi_z", "prev_level"] + core, "ipi_z",
                           "placebo outcome: previous change in expectation"))
    # presence threshold and volume weights from the outlet-level window file
    wo = pd.read_csv(ROOT / "data/processed/index/ipi_window_outlet.csv")
    wo = wo[wo.valid_window.astype(bool)]
    nwin = wo["round"].nunique()
    pres = wo[wo.present.astype(bool)].groupby("outlet")["round"].nunique() / nwin
    alt = {}
    for thr in (0.6, 0.9):
        core_o = pres.index[pres >= thr]
        alt[f"presence {int(thr * 100)}% ({len(core_o)} outlets)"] = wo[wo.outlet.isin(core_o)].groupby("round").a_price.mean()
    core80 = pres.index[pres >= 0.8]
    g = wo[wo.outlet.isin(core80)].groupby("round")
    alt[f"volume-weighted, 80% core ({len(core80)} outlets)"] = g.n_price_distinct.sum() / g.n_distinct_urls.sum()
    for name, s in alt.items():
        b2 = base.copy()
        b2["alt"] = b2["round"].map(s)
        b2["alt_z"] = (b2.alt - df["round"].map(s).mean()) / df["round"].map(s).std()
        rows.append(p1.fit_row(b2, f"{y}_h0", ["alt_z"] + spec, "alt_z", name))
    t = pd.DataFrame(rows)
    t.to_csv(R / "extra_robustness.csv", index=False)
    print(t[["model", "N", "beta", "ci_lo", "ci_hi", "p_wild"]].round(3).to_string())

    # minimum detectable effect (80% power, alpha 0.05 two-sided) using the EWC se and fixed-b t critical value
    r0 = rows[0]
    crit = p1.tcrit(int(r0["dof_B"]))
    from scipy import stats
    mde = float((crit + stats.t.ppf(0.8, int(r0["dof_B"]))) * r0["se_ewc"])
    ntests = {f: len(pd.read_csv(R / f)) for f in ("d19_national_lp.csv", "d20_regime.csv", "d22_forecast_eval.csv",
                                                     "d23_monthly_lp.csv", "paper_horse_race.csv")}
    (R / "extra_mde.json").write_text(json.dumps({"se_ewc": r0["se_ewc"], "dof": r0["dof_B"], "mde_pp_per_sd": mde,
                                                  "estimates_reported": ntests, "total": sum(ntests.values())}, indent=1))
    print("MDE", round(mde, 3), "tests", sum(ntests.values()))
    df[["round", "fieldwork_start", "fs_rule", "mode", "valid_window"]].to_csv(R / "extra_iesh_rounds.csv", index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    mon = pd.read_csv(ROOT / "data/processed/index/ipi_monthly.csv")
    mon = mon[mon.usable_d23]
    x = pd.PeriodIndex(mon.month, freq="M").to_timestamp()
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.plot(x, 100 * mon[sw["monthly_column"]], color="#1f4e79", lw=1.2, label="price family")
    ax.plot(x, 100 * mon.ipi_monthly, color="#7f7f7f", lw=1, ls="--", label="baseline tag")
    for k, (a, b) in EPIS.items():
        ax.axvspan(pd.Period(a, "M").to_timestamp(), pd.Period(b, "M").end_time, color="#c55a11", alpha=0.15)
        ax.text(pd.Period(a, "M").to_timestamp(), ax.get_ylim()[1] * 0.95, k, fontsize=7)
    ax.set_ylabel("% of articles (monthly, grid days)"); ax.legend(fontsize=7, frameon=False)
    fig.tight_layout(); fig.savefig(F / "fig_monthly_episodes.png", dpi=200); plt.close(fig)

    lp = pd.read_csv(R / "d19_national_lp.csv")
    pr = lp[lp.model.str.startswith("D19 primary-spec")].copy()
    pr["h"] = pr.model.str[-1].astype(int); pr["y"] = pr.outcome.str.rsplit("_", n=1).str[0]
    lab = {"y1_median": "1-yr median", "y1_mean": "1-yr mean", "m3_median": "3-month median", "cur_median": "current, median"}
    fig, axs = plt.subplots(1, 4, figsize=(9, 2.6), sharey=True)
    for ax, (k, v) in zip(axs, lab.items()):
        s = pr[pr.y == k]
        ax.errorbar(s.h, s.beta, yerr=[s.beta - s.ci_lo, s.ci_hi - s.beta], fmt="o", color="#1f4e79", capsize=2)
        ax.axhline(0, color="k", lw=0.7); ax.set_title(v, fontsize=8); ax.set_xticks(range(4)); ax.set_xlabel("h (rounds)")
    axs[0].set_ylabel("pp per SD of index")
    fig.tight_layout(); fig.savefig(F / "fig_horizons.png", dpi=200); plt.close(fig)

    irf = pd.read_csv(R / "d21_bvar_irf.csv")
    fig, ax = plt.subplots(figsize=(5.5, 3))
    for o, sty in zip(irf.order.unique(), ["-o", "--s"]):
        s = irf[irf.order == o]
        ax.plot(s.h, s.resp_y1_to_ipi_shock, sty, ms=3, label=("index before expectations" if o.index("ipi") < o.index("y1") else "expectations before index"))
    ax.axhline(0, color="k", lw=0.7); ax.set_xlabel("rounds after shock"); ax.set_ylabel("pp, 1-yr median")
    ax.legend(fontsize=7, frameon=False); fig.tight_layout(); fig.savefig(F / "fig_var_irf.png", dpi=200); plt.close(fig)

    pz = pd.read_csv(R / "d22_predictions.csv")
    fig, ax = plt.subplots(figsize=(8, 3))
    for c, col in [("AR1", "#7f7f7f"), ("AR1+CPI+food", "#c55a11"), ("HEADLINE AR1+CPI+food+IPI", "#1f4e79")]:
        ax.plot(range(len(pz)), pz[c] - pz.actual, marker="o", ms=2.5, lw=1, color=col, label=c.replace("HEADLINE ", "").replace("IPI", "index"))
    ax.axhline(0, color="k", lw=0.7); ax.set_xticks(range(0, len(pz), 4)); ax.set_xticklabels(pz["round"].iloc[::4], rotation=45, fontsize=7)
    ax.set_ylabel("forecast error (pp)"); ax.legend(fontsize=7, frameon=False)
    fig.tight_layout(); fig.savefig(F / "fig_forecast_errors.png", dpi=200); plt.close(fig)

    m = pd.read_csv(ROOT / "outputs/audit/metrics_prf.csv")
    m = m[(m.truth_source == "A") & (m.frame == "gating") & (m.group == "all")]
    pv = m.pivot_table(index="variant", columns="metric", values="estimate").loc[["flag_baseline", "flag_price_family", "flag_strict", "flag_wb442"]]
    lo = m.pivot_table(index="variant", columns="metric", values="ci_lo").loc[pv.index]
    hi = m.pivot_table(index="variant", columns="metric", values="ci_hi").loc[pv.index]
    pv.round(3).join(lo.add_suffix("_lo").round(3)).join(hi.add_suffix("_hi").round(3)).to_csv(R / "extra_audit_variants.csv")
    fig, ax = plt.subplots(figsize=(6, 3))
    xs = np.arange(len(pv)); w = 0.27
    for i, (mt, col) in enumerate([("precision", "#1f4e79"), ("recall", "#c55a11"), ("f2", "#7f7f7f")]):
        ax.bar(xs + (i - 1) * w, pv[mt], w, yerr=[pv[mt] - lo[mt], hi[mt] - pv[mt]], color=col, capsize=2, label=mt)
    ax.set_xticks(xs); ax.set_xticklabels(["baseline", "price family", "strict", "World Bank"], fontsize=8)
    ax.axhline(0.5, color="#1f4e79", ls=":", lw=0.8); ax.axhline(0.6, color="#c55a11", ls=":", lw=0.8)
    ax.legend(fontsize=7, frameon=False); ax.set_ylim(0, 1)
    fig.tight_layout(); fig.savefig(F / "fig_audit_prf.png", dpi=200); plt.close(fig)

    e3 = pd.read_csv(ROOT / "data/processed/results/e3_series_monthly.csv")
    num = [c for c in e3.columns if c not in ("month", "version") and e3[c].dtype != object][:4]
    fig, ax = plt.subplots(figsize=(8, 3))
    xx = pd.PeriodIndex(e3.month, freq="M").to_timestamp()
    for c in num:
        ax.plot(xx, e3[c], lw=1, label=c)
    ax.legend(fontsize=7, frameon=False); ax.set_ylabel("percent")
    fig.tight_layout(); fig.savefig(F / "fig_e3_series.png", dpi=200); plt.close(fig)
    print("figures written; e3 columns:", num)
    return 0


if __name__ == "__main__":
    sys.exit(main())
