"""Assemble 10_OUTPUTS/paper/paper_full.md from the three written parts, filling every {{TABLE_*}} placeholder
directly from the result files (no hand-typed numbers in appendix tables). Fails if a placeholder or a forbidden
pipeline artefact remains in the output.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

PIPE = Path(__file__).resolve().parents[2]
PAPER = PIPE.parents[1] / "10_OUTPUTS/paper"
RS, RB = PIPE / "data/processed/results_switched", PIPE / "data/processed/results"


def md(df: pd.DataFrame, nd: int = 3) -> str:
    df = df.copy()
    for c in df.columns:
        if df[c].dtype.kind == "f":
            df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{v:.{nd}f}")
    return df.to_markdown(index=False)


def rows(f: Path, mask=None, cols=("model", "N", "beta", "ci_lo", "ci_hi", "p_wild")) -> pd.DataFrame:
    d = pd.read_csv(f)
    if mask is not None:
        d = d[mask(d)]
    return d[[c for c in cols if c in d.columns]]


def clean_label(s: pd.Series) -> pd.Series:
    rep = {"D19 ": "", "D20 ": "", "D11 robustness ": "", "E2 ": "", "E4 ": "", "E5 ": "", "E3 ": "", "IPI": "index",
           "row_": "", "variant_": "", "ipi_core2018_with_vernacular": "2018 core incl. vernacular",
           " (ruling b check)": "", "high episode": "high-inflation episode", "S^int": "international share",
           "[trends_search_implied] ": "", "pi_med": "salience-weighted median", "pi_cpi": "published CPI",
           "pi_abs": "absolute salience-weighted", "focus ": "coefficient on ", ", D19 spec": ""}
    out = s.astype(str)
    for a, b in rep.items():
        out = out.str.replace(a, b, regex=False)
    return out


def p3(v) -> str:
    """p-values to 3 decimals, ties rounded half up (bootstrap p-values are multiples of 0.0005), as in the paper."""
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(repr(float(v))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def ci(e, lo, hi, nd=3) -> str:
    if pd.isna(e) or e < -1:
        return "–"
    return f"{e:.{nd}f} ({lo:.{nd}f}, {hi:.{nd}f})"


def reg_table(d: pd.DataFrame, first: str) -> str:
    d = d.copy()
    d["model"] = d.model.str.replace("x post-2022", "× post-2022", regex=False)
    out = pd.DataFrame({first: d.model, "N": d.N, "Coefficient": d.beta.map(lambda v: f"{v:.3f}"),
                        "95% CI": [f"({a:.3f}, {b:.3f})" for a, b in zip(d.ci_lo, d.ci_hi)],
                        "p": d.p_wild.map(p3)})
    return out.to_markdown(index=False)


def revision_tables(sname: dict) -> dict:
    """Revision round 2 tables (additional checks; no primary estimate, flag or specification changed)."""
    RR, AR = PIPE / "data/processed/results_revision2", PIPE / "outputs/audit_revision2"
    t = {}
    p = pd.read_csv(AR / "prf_revision2.csv")
    p = p[p.frame == "gating"]
    p["s"] = [ci(e, a, b) for e, a, b in zip(p.estimate, p.ci_lo, p.ci_hi)]
    fl = {"flag_baseline": "Baseline", "flag_price_family": "Price family"}
    case = {"reference (missing at random)": "Missing at random (paper)", "slug labels imputed": "Address-coded labels imputed",
            "unretrieved all relevant": "All unretrieved relevant", "unretrieved none relevant": "No unretrieved relevant"}
    a = p[p.group == "all"].pivot_table(index=["case", "variant"], columns="metric", values="s", aggfunc="first")
    a = a.reindex([(c, v) for c in case for v in fl]).reset_index()
    a["case"], a["variant"] = a.case.map(case), a.variant.map(fl)
    a = a[["case", "variant", "precision", "recall", "f2"]]
    a.columns = ["Unretrieved articles", "Definition", "Precision", "Recall", "F2"]
    t["TABLE_R_BOUNDS"] = a.to_markdown(index=False, disable_numparse=True)
    s = p[p.group.str.startswith("stratum=") & (p.variant == "flag_baseline") & (p.metric == "precision")].copy()
    s["stratum"] = s.group.str[8:]
    s = s[s.stratum.isin(["flagged", "hin_flagged", "oth_flagged"])]
    sv = s.pivot_table(index="stratum", columns="case", values="s", aggfunc="first")[list(case)]
    nn = s[s.case == "reference (missing at random)"].set_index("stratum")[["n_coded", "n_relevant"]]
    un = pd.read_csv(AR / "unretrieved_by_stratum.csv").set_index("stratum")
    sv = sv.join(nn).join(un).reindex(["flagged", "hin_flagged", "oth_flagged"]).reset_index()
    sv["stratum"] = sv.stratum.map(sname)
    sv["n"] = [f"{a} / {b} / {c} ({d})" for a, b, c, d in zip(sv.n_coded, sv.n_relevant, sv.unretrieved, sv.slug_relevant)]
    sv = sv[["stratum", "n"] + list(case)]
    sv.columns = ["Stratum (tagged)", "Coded / relevant / unretrieved (address-coded relevant)", "Paper", "Address codes",
                  "All relevant", "None relevant"]
    t["TABLE_R_STRATUM"] = sv.to_markdown(index=False, disable_numparse=True)
    gname = {"all": "All", "en": "English", "hin": "Hindi/Marathi", "oth": "Other Indian languages",
             "vernacular_focal": "All Indian languages", "mode=live": "Retrieved live", "mode=wayback": "Retrieved from archive"}
    r = p[(p.case == "reference (missing at random)") & p.group.isin(gname)]
    lg = r.pivot_table(index=["group", "variant"], columns="metric", values="s", aggfunc="first")
    n = r.drop_duplicates(["group", "variant"]).set_index(["group", "variant"])[["n_coded", "n_flagged", "n_relevant"]]
    lg = lg.join(n).reindex([(g, v) for g in gname for v in fl]).reset_index()
    lg["group"], lg["variant"] = lg.group.map(gname), lg.variant.map(fl)
    lg["n"] = [f"{a:,} / {b} / {c}" for a, b, c in zip(lg.n_coded, lg.n_flagged, lg.n_relevant)]
    lg = lg[["group", "variant", "n", "precision", "recall", "f2"]]
    lg.columns = ["Group", "Definition", "Coded / tagged / relevant", "Precision", "Recall", "F2"]
    t["TABLE_R_LANG"] = lg.to_markdown(index=False, disable_numparse=True)
    e = pd.read_csv(RR / "expectation_robustness.csv")
    e["model"] = e.model.str.replace("excl 2020-21", "Excluding 2020–21", regex=False).str.replace(
        "add ", "Add ", regex=False).str.replace("subsample:", "Subsample:", regex=False).str.replace(
        "primary (reference)", "Primary (reference)", regex=False).str.replace(
        "post-2022 dummy + interaction", "Post-2022 dummy and interaction", regex=False).str.replace(
        "(2-month log change)", "(two-month log change)", regex=False)
    t["TABLE_R_EXPECT"] = reg_table(e, "Specification")
    w = pd.read_csv(RR / "window_length.csv")
    hi = json.loads((RR / "heavy_info.json").read_text())
    w["model"] = [f"{k} days" + (" (paper)" if k == 14 else "") for k in (14, 10, 7)]
    tw = pd.DataFrame({"Window": w.model, "Core outlets": [hi[f"{k}d"]["core_size"] for k in (14, 10, 7)],
                       "Core outlets per window (min / median)": [f"{hi[f'{k}d']['core_present_min']:g} / {hi[f'{k}d']['core_present_median']:g}" for k in (14, 10, 7)],
                       "Correlation with 14-day series": w.corr_with_published_series.map(lambda v: f"{v:.3f}"),
                       "N": w.N, "Coefficient": w.beta.map(lambda v: f"{v:.3f}"),
                       "95% CI": [f"({a:.3f}, {b:.3f})" for a, b in zip(w.ci_lo, w.ci_hi)], "p": w.p_wild.map(p3)})
    t["TABLE_R_WINDOW"] = tw.to_markdown(index=False, disable_numparse=True)
    y = pd.read_csv(RR / "outlets_by_year.csv")
    y.columns = ["Year", "Valid windows", "Min", "Median", "Max"]
    y = y.astype(float).map(lambda v: f"{v:g}")
    t["TABLE_R_OUTLETS_YEAR"] = y.to_markdown(index=False)
    o = pd.read_csv(RR / "outlet_composition.csv")
    o["model"] = o.model.str.replace(">=", "≥", regex=False).str.replace("balanced panel", "Balanced panel", regex=False).str.replace(
        "all valid windows", "All valid windows", regex=False).str.replace("windows with", "Windows with", regex=False)
    t["TABLE_R_OUTLETS"] = reg_table(o, "Sample")
    mv = pd.read_csv(RR / "matched_validation.csv")
    ser = {"matched (window construction)": "Window construction, grid days in windows (68 months)",
           "paper monthly, same 68 months": "Monthly series, same 68 months",
           "paper monthly (price family)": "Monthly series, all 129 months"}
    rows = []
    for k, lab in ser.items():
        q = mv[mv.series == k]
        tr = q[q.check == "trends"].set_index("term")
        ep = q[q.check == "episode"].set_index("term")
        rows.append({"Series": lab, "r, inflation": f"{tr.loc['inflation', 'r_raw']:.3f}",
                     "r, inflation, partial (95% CI)": ci(tr.loc["inflation", "r_partial_cpi_food"], tr.loc["inflation", "partial_ci_lo"], tr.loc["inflation", "partial_ci_hi"]),
                     "r, mehngai": f"{tr.loc['mehngai', 'r_raw']:.3f}",
                     **{f"z, {nm}": f"{ep.loc[key, 'z']:.2f}" + (" (peak)" if ep.loc[key, "peak"] else "")
                        for key, nm in (("onion_2019_20", "onion"), ("fuel_2021_22", "fuel"), ("post_ukraine_2022", "post-Ukraine"), ("tomato_2023", "tomato"))},
                     "Episodes peaking": f"{int(ep.peak.sum())} of 4"})
    t["TABLE_R_MATCHED"] = pd.DataFrame(rows).to_markdown(index=False, disable_numparse=True)
    j = pd.read_csv(RR / "joint_lp_test.csv")
    tj = pd.DataFrame({"Shock": j.shock.map({"cpi_surprise": "CPI surprise (1 pp)", "brent_shock": "Brent (1%)"}),
                       "N (common sample)": j.N_common, "Wald χ²(13), Newey–West": j.wald_nw.map(lambda v: f"{v:.1f}"),
                       "p, asymptotic": j.p_chi2_nw.map(lambda v: "< 0.001" if v < 0.001 else f"{v:.3f}"),
                       "p, block bootstrap": j.p_block_bootstrap.map(p3),
                       "p, Bonferroni": j.p_bonferroni.map(p3),
                       "Cumulative response h = 0–12 (95% CI)": [ci(a, b, c) for a, b, c in zip(j.cum_response_0_12, j.cum_ci_lo, j.cum_ci_hi)],
                       "p, cumulative": j.cum_p_ewc.map(p3)})
    t["TABLE_R_JOINT"] = tj.to_markdown(index=False, disable_numparse=True)
    return t


def main() -> int:
    t = {}
    e1 = pd.read_csv(RB / "e1_exposure_table.csv")
    e1 = e1[["city", "median_local_per_window", "median_flagged_per_window", "max_flagged", "descriptive_cells", "flagged_share_pct"]]
    e1.columns = ["City", "Median local articles per window", "Median tagged per window", "Max tagged", "City-years meeting descriptive threshold", "Tagged share (%)"]
    t["TABLE_E1"] = md(e1, 2)
    ll = pd.read_csv(RS / "e2_leadlag_monthly.csv"); ll.columns = ["Lag (months)", "Correlation", "N"]
    t["TABLE_E2LL"] = md(ll, 3)
    e3 = rows(RB / "e3_horse_race.csv"); e3["model"] = clean_label(e3.model); e3.columns = ["Regression", "N", "Coefficient", "CI low", "CI high", "p"]
    t["TABLE_E3"] = md(e3, 3)
    pk = pd.read_csv(RS / "e5_peaks.csv")[["peak_month", "peak_value", "baseline_prior12", "rise_months_to_peak", "half_life_months"]]
    pk[["peak_value", "baseline_prior12"]] *= 100
    pk.columns = ["Peak month", "Peak (% of articles)", "Prior 12-month level (%)", "Months of rise", "Half-life (months)"]
    t["TABLE_E5"] = md(pk, 2)
    pb = pd.read_csv(RB / "e5_peaks.csv")[["peak_month", "peak_value", "baseline_prior12", "rise_months_to_peak", "half_life_months"]]
    pb[["peak_value", "baseline_prior12"]] *= 100
    pb.columns = pk.columns
    t["TABLE_E5_BASE"] = md(pb, 2)
    ext = pd.concat([rows(RS / f) .assign(Definition="price family") for f in ("e2_d19.csv", "e4_d19.csv", "e5_excess_attention.csv")]
                    + [rows(RB / f).assign(Definition="baseline") for f in ("e4_d19.csv", "e5_excess_attention.csv")])
    ext["model"] = clean_label(ext.model)
    ext = ext[["Definition", "model", "N", "beta", "ci_lo", "ci_hi", "p_wild"]]
    ext.columns = ["Definition", "Regression", "N", "Coefficient", "CI low", "CI high", "p"]
    t["TABLE_EXT"] = md(ext, 3)
    d11 = rows(RB / "d19_national_lp.csv", lambda d: d.model.str.startswith("D11"))
    d11["model"] = clean_label(d11.model); d11.columns = ["Construction", "N", "Coefficient", "CI low", "CI high", "p"]
    t["TABLE_D11"] = md(d11, 3)
    d20 = rows(RS / "d20_regime.csv"); d20["model"] = clean_label(d20.model); d20.columns = ["Specification", "N", "Coefficient", "CI low", "CI high", "p"]
    t["TABLE_D20"] = md(d20, 3)
    d23 = pd.read_csv(RS / "d23_monthly_lp.csv")[["shock", "h", "beta", "se_ewc", "N"]]
    d23["shock"] = d23.shock.map({"cpi_surprise": "CPI surprise (1 pp)", "brent_shock": "Brent (1%)"})
    d23.columns = ["Shock", "Months after", "Response (SD)", "EWC s.e.", "N"]
    t["TABLE_D23"] = md(d23, 3)
    g = json.loads((PIPE / "outputs/audit/gate_report.json").read_text())
    name = {"flagged": "English, tagged", "econ_unflagged": "English, economic, untagged", "hin_flagged": "Hindi/Marathi, tagged",
            "hin_econ_unflagged": "Hindi/Marathi, economic, untagged", "oth_flagged": "Other vernacular, tagged",
            "oth_econ_unflagged": "Other vernacular, economic, untagged", "nonecon_slug": "Non-economic, price word in address",
            "nonecon_noslug": "Non-economic, other"}
    cv = pd.DataFrame(g["coverage"])[["stratum", "period", "sampled", "retrieved", "retrieval_rate"]]
    cv["stratum"] = cv.stratum.map(name); cv["period"] = cv.period.map({"old": "2015–18", "late": "2019 onward"})
    cv.columns = ["Stratum", "Period", "Sampled", "Retrieved", "Rate"]
    t["TABLE_D1"] = md(cv, 3)
    ir = pd.read_csv(RS / "extra_iesh_rounds.csv")
    ir["fs_rule"] = ir.fs_rule.map({"exact": "exact", "month_rule": "month rule"}).fillna(ir.fs_rule)
    ir["mode"] = ir["mode"].fillna("not stated").replace({"not_stated": "not stated"})
    ir["valid_window"] = ir.valid_window.map({True: "yes", False: "no"}).fillna(ir.valid_window)
    ir.columns = ["Round", "Fieldwork start", "Date rule", "Mode", "Valid window"]
    t["TABLE_C"] = md(ir)
    wo = pd.read_csv(PIPE / "data/processed/index/ipi_window_outlet.csv"); wo = wo[wo.valid_window.astype(bool)]
    pr = wo[wo.present.astype(bool)].groupby("outlet")["round"].nunique() / wo["round"].nunique()
    core = pr.index[pr >= 0.8]
    lang = wo[wo.outlet.isin(core)].groupby("outlet").lang.agg(lambda s: s.mode()[0])
    lname = {"native": "English", "hin": "Hindi", "tam": "Tamil", "mal": "Malayalam", "tel": "Telugu", "mar": "Marathi",
             "pan": "Punjabi", "kan": "Kannada", "guj": "Gujarati", "ben": "Bengali"}
    t["CORE_LIST"] = "\n".join(f"* **{lname.get(l, l)} ({len(gr)}):** " + ", ".join(sorted(gr.index))
                               for l, gr in sorted(lang.groupby(lang), key=lambda x: -len(x[1])))
    t.update(revision_tables(name))
    text = "".join((PAPER / "parts" / p).read_text(encoding="utf-8") for p in ("p1.md", "p2.md", "p3.md"))
    for k, v in t.items():
        text = text.replace("{{" + k + "}}", v)
    text = text.replace("Cause: ten categories plus other/none", "Cause: nine categories plus other/none")
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    bad = [w for w in ("PROGRESS", "PENDING", "to be checked", "Gate ", "results_switched", ".csv", "D19", "D17", "D15",
                       "D9", "draft for review", "At the time of writing", "By the author's ruling") if w in text]
    text = text.replace("](figures/", "](../figures/")  # the assembled draft lives in paper/archive/
    out = PAPER / "archive" / "paper_full.md"
    out.write_text(text, encoding="utf-8")
    print("written", out, len(text.split()), "words; placeholders left:", left, "; forbidden:", bad)
    return 1 if left or bad else 0


if __name__ == "__main__":
    sys.exit(main())
