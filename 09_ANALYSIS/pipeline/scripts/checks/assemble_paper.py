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
    ir["mode"] = ir["mode"].replace({"not_stated": "not stated"})
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
    text = "".join((PAPER / "parts" / p).read_text(encoding="utf-8") for p in ("p1.md", "p2.md", "p3.md"))
    for k, v in t.items():
        text = text.replace("{{" + k + "}}", v)
    text = text.replace("Cause: ten categories plus other/none", "Cause: nine categories plus other/none")
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    bad = [w for w in ("PROGRESS", "PENDING", "to be checked", "Gate ", "results_switched", ".csv", "D19", "D17", "D15",
                       "D9", "draft for review", "At the time of writing", "By the author's ruling") if w in text]
    out = PAPER / "paper_full.md"
    out.write_text(text, encoding="utf-8")
    print("written", out, len(text.split()), "words; placeholders left:", left, "; forbidden:", bad)
    return 1 if left or bad else 0


if __name__ == "__main__":
    sys.exit(main())
