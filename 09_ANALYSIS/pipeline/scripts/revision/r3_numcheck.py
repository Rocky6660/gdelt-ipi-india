"""Revision round 3: number check of the submission source (content.js, appendix.js) against the result files.

Three layers (a pooled match alone is not informative: with every result file pooled, any 2-decimal number in [0, 1]
finds a match by chance, so that layer is reported only as a screen):
  1. Tables: every decimal in a table must match, at its printed precision, a value in that table's own source files
     (mapping below). The chance-match rate of each table's pool is reported alongside.
  2. Targeted claims: every number added or changed in revision round 3 is rebuilt from its result file, formatted
     (p-values rounded half up, as bootstrap p-values are multiples of 0.0005) and must appear verbatim in the source.
  3. Pooled screen over the prose (all result files), with its chance-match rate.
Writes results_revision3/r3_numcheck.csv and r3_numcheck.json.
"""
from __future__ import annotations

import bisect
import json
import random
import re
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

PIPE = Path(__file__).resolve().parents[2]
SRC = PIPE.parents[1] / "10_OUTPUTS/paper/final/source"
OUT = PIPE / "data/processed/results_revision3"
R, S, R2, R3 = "data/processed/results/", "data/processed/results_switched/", "data/processed/results_revision2/", "data/processed/results_revision3/"
A, A2 = "outputs/audit/", "outputs/audit_revision2/"
TABLES = {
    "Table 4.": ["@window_corr"], "Table 5.": [S + "paper_descriptives.csv"],
    "Table 6.": [A + "retrieval_by_stratum.csv", A + "gate_report.json"], "Table 7.": [A + "metrics_prf.csv"],
    "Table 8.": [A2 + "prf_revision2.csv"], "Table 9.": [A2 + "prf_revision2.csv"],
    "Table 10.": [R + "d17_validation.csv", R + "d17_validation_flag_price_family.csv", R + "d17_validation_flag_strict.csv"],
    "Table 11.": [S + "d19_national_lp.csv", R + "d19_national_lp.csv", S + "extra_robustness.csv"],
    "Table 12.": [R2 + "expectation_robustness.csv", R2 + "window_length.csv", R2 + "outlet_composition.csv", R3 + "r3_lp.csv", R3 + "r3_index.csv"],
    "Table 13.": [S + "d19_national_lp.csv"], "Table 14.": [S + "paper_horse_race.csv", S + "d20_regime.csv"],
    "Table 15.": [S + "d22_forecast_eval.csv", R + "d22_forecast_eval.csv"], "Table 16.": [R + "e1_exposure_table.csv"],
    "Table 17.": [S + "e5_peaks.csv"], "Table D1.": [A + "gate_report.json"], "Table E1.": [R + "d19_national_lp.csv"],
    "Table E2.": [S + "d20_regime.csv"], "Table E3.": [S + "d23_monthly_lp.csv"],
    "Table E4.": [R2 + "outlets_by_year.csv", R2 + "outlet_summary.json"],
    "Table F1.": [S + "e2_d19.csv", S + "e4_d19.csv", S + "e5_excess_attention.csv", R + "e4_d19.csv", R + "e5_excess_attention.csv"],
    "Table F2.": [R + "e3_horse_race.csv"], "Table F3.": [S + "e2_leadlag_monthly.csv"], "Table F4.": [R + "e5_peaks.csv"],
}
NUM = re.compile(r"(?<![\w.])[−-]?\d+\.(\d+)(?![\w.])")


def vals_of(spec: str) -> list[float]:
    if spec == "@window_corr":
        w = pd.read_csv(PIPE / "data/processed/index/ipi_window.csv")
        c = w.select_dtypes("number").corr()["ipi_primary"]
        return c.dropna().tolist()
    f = PIPE / spec
    if f.suffix == ".csv":
        d = pd.read_csv(f)
        return [x for c in d.columns for x in pd.to_numeric(d[c], errors="coerce").dropna().tolist()]
    return [float(x) for x in re.findall(r"-?\d+\.\d+(?:e-?\d+)?|\b\d+\b", f.read_text(encoding="utf-8"))]


def expand(vals) -> list[float]:
    out = set()
    for v in vals:
        out.update((v, abs(v), 100 * v, abs(100 * v)))
    return sorted(out)


def match(P, raw: str, nd: int) -> bool:
    v, tol = abs(float(raw.replace("−", "-"))), 0.5 * 10 ** (-nd) + 1e-9
    i = bisect.bisect_left(P, v - tol)
    return i < len(P) and P[i] <= v + tol


def chance(P, nd=2, n=1000) -> float:
    rnd = random.Random(7)
    return sum(match(P, f"{rnd.uniform(0, 1):.{nd}f}", nd) for _ in range(n)) / n


def p3(v) -> str:
    return str(Decimal(repr(float(v))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def f(v, nd=2) -> str:
    s = f"{float(v):.{nd}f}"
    return s.replace("-", "−")


def claims() -> list[tuple[str, str]]:
    """(label, expected text) pairs; the expected text is built from result files and must occur in the source."""
    lp = pd.read_csv(PIPE / R3 / "r3_lp.csv").set_index("model")
    ix = pd.read_csv(PIPE / R3 / "r3_index.csv").set_index("model")
    ij = json.loads((PIPE / R3 / "r3_index.json").read_text())
    au = json.loads((PIPE / R3 / "r3_audit.json").read_text())
    ck = json.loads((PIPE / R3 / "r3_checks.json").read_text())
    jt = pd.read_csv(PIPE / R2 / "joint_lp_test.csv").set_index("shock")
    er = pd.read_csv(PIPE / R2 / "expectation_robustness.csv").set_index("model")
    d19 = pd.read_csv(PIPE / S / "d19_national_lp.csv")
    dI = d19[(d19.model == "D19 dIPI variant") & (d19.outcome == "y1_median_h0")].iloc[0]
    aI = d19[(d19.model == "D19 AR+CPI only") & (d19.outcome == "y1_median_h0")].iloc[0]
    fC = d19[(d19.model == "D19 future-CPI test") & (d19.outcome == "y1_median_h0")].iloc[0]
    b = au["C14_unscreened_bound"]
    dd, ne = ix.loc["outlets de-duplicated (89 outlets)"], ix.loc["non-energy price family"]
    nl, gp = lp.loc["no lagged dependent variable"], lp.loc["months between rounds added"]
    pr, mk = lp.loc["outcome per two months (divided by months between rounds)"], lp.loc["intra-window Brent and INR/USD changes added"]
    row = lambda r, lab: f'["{lab}","{int(r.N)}","{f(r.beta, 3)}","({f(r.ci_lo, 3)}, {f(r.ci_hi, 3)})","{p3(r.p_wild)}"]'  # noqa: E731
    g = au["gating_by_lang_group"]["other_nonfocal"]
    c = [("T12 dedup row", row(dd, "Outlets de-duplicated, lifestyle domains dropped (89 outlets)")),
         ("T12 non-energy row", row(ne, "Non-energy price family")),
         ("T12 no-LDV row", row(nl, "No lagged dependent variable")),
         ("T12 gap row", row(gp, "Months between rounds added")),
         ("T12 per-2m row", row(pr, "Outcome per two months (divided by the months between rounds)")),
         ("T12 market row", row(mk, "Intra-window Brent and INR/USD changes added")),
         ("T12 INR p", f'"(0.019, 0.450)","{p3(er.loc["add change in INR/USD (2-month log change)"].p_wild)}"'),
         ("4.3.2 dedup", f"gives {f(dd.beta)} (p = {p3(dd.p_wild)})"), ("4.3.2 non-energy", f"gives {f(ne.beta)} (p = {p3(ne.p_wild)})"),
         ("4.3.2 no-LDV", f"gives {f(nl.beta)} (p = {p3(nl.p_wild)}, N = {int(nl.N)})"),
         ("4.3.2 gap", f"gives {f(gp.beta)} (p = {p3(gp.p_wild)})"), ("4.3.2 per-2m", f"gives {f(pr.beta)} (p = {p3(pr.p_wild)})"),
         ("4.3.2 market", f"gives {f(mk.beta)} (p = {p3(mk.p_wild)})"),
         ("A1 variants", f"p = {p3(aI.p_wild)}; next-month CPI added, p = {p3(fC.p_wild)}; intra-window Brent and INR/USD changes added, p = {p3(mk.p_wild)}"),
         ("T11 change in index", f'"{f(dI.beta)} [{f(dI.ci_lo)}, {f(dI.ci_hi)}] p = {p3(dI.p_wild)}"'),
         ("Bonferroni", f"Bonferroni p = {p3(jt.loc['brent_shock'].p_bonferroni)}"),
         ("C14 share/CI", f"share {f(b['share'], 3)}; exact Clopper–Pearson 95% CI {f(b['exact_ci_lo'], 4)} to {f(b['exact_ci_hi'], 3)}"),
         ("C14 baseline", f"{f(b['flag_baseline_recall_whole_flow_at_ci_lo'])} at the lower limit of the interval, {f(b['flag_baseline_recall_whole_flow_at_point'])} at the point estimate and {f(b['flag_baseline_recall_whole_flow_at_ci_hi'])} at the upper limit"),
         ("C14 price family", f"(price family: {f(b['flag_price_family_recall_whole_flow_at_ci_lo'])}, {f(b['flag_price_family_recall_whole_flow_at_point'])} and {f(b['flag_price_family_recall_whole_flow_at_ci_hi'])})"),
         ("A6 other languages", f"{g['coded']} coded articles ({g['relevant']} relevant)"),
         ("A6 gating", f"({au['gating_coded']:,} coded, {au['gating_relevant']} relevant)"),
         ("A6 119", f"Among the {au['relevant_all_first_pass']} articles"),
         ("A5 month rule", f"{ck['A5_month_rule_total']} rounds for which exact fieldwork dates are not published ({sum(v for k, v in ck['A5_month_rule_by_year'].items() if k < '2020')} rounds before 2020 and {ck['A5_month_rule_by_year']['2020']} in 2020"),
         ("A4 BVAR", f"({ck['A4_bvar_rows_T']} rounds from March 2016 to January 2026 enter; with two lags, {ck['A4_bvar_effective_obs_after_2_lags']} observations"),
         ("A2 raw", f"reaches {f(ck['A2_price_family_raw_2022_04'], 1)}% in April 2022 and {f(ck['A2_price_family_raw_top5']['2026-03'], 1)}% in March 2026"),
         ("A2 raw baseline", f"peaks at {f(ck['A2_baseline_raw_top5']['2022-07'], 1)}% of articles in July 2022"),
         ("A2 MA", f"which peaks at {f(ck['A2_price_family_ma3_2022_04'], 1)}% in April 2022 and {f(ck['A2_price_family_ma3_2026_04'], 1)}% in April 2026"),
         ("A2 Table 17 note", f"reaches {f(ck['A2_price_family_raw_top5']['2026-03'], 2)}% in March 2026"),
         ("A2 means", f"{f(ck['A2_price_family_mean_2016_21'])}% of articles in 2016–21, {f(ck['A2_price_family_mean_2022_23'])}% in 2022–23 and {f(ck['A2_price_family_mean_2024_26'])}% in 2024–26"),
         ("C13 mean/corr", f"(mean {f(ij['nonenergy_mean_pct'])}% of articles; correlation {f(ij['corr_nonenergy_pricefamily'])} with the price family)"),
         ("C12 corr", f"the index correlates at {f(ij['corr_dedup_pricefamily'])} with the published one"),
         ("C13 32 articles", f"the {ij['audit_price_family_tagged'] - ij['audit_nonenergy_tagged']} sampled articles tagged only by the price family"),
         ("C16 tone", f"({f(ij['tone_mean']['falling'])} against {f(ij['tone_mean']['rising'])}; Mann–Whitney p = {p3(ij['tone_mannwhitney_p'])})"),
         ("C16 counts", f"({ij['tone_direction_counts']['rising']} rising, {ij['tone_direction_counts']['falling']} falling)"),
         ("C15 gap", f"(median {f(lp.gap_months_median.iloc[0], 1)})"),
         ("2018 core", f"the *2018 core* is the set of {json.loads((PIPE / 'data/processed/index/build_report.json').read_text())['window']['core2018_size']} outlets"),
         ]
    # tie-rounded bootstrap p-values corrected in round 3 (value in the file must appear rounded half up)
    def pv(fname, model, outcome="y1_median_h0"):
        d = pd.read_csv(PIPE / fname)
        r = d[(d.model == model) & ((d.outcome == outcome) if "outcome" in d else True)].iloc[0]
        return p3(r.p_wild)
    c += [("T11 baseline primary p", f'p = {pv(R + "d19_national_lp.csv", "D19 primary-spec h=0")}"]'),
          ("T11 volume-weighted p", f'p = {pv(S + "extra_robustness.csv", "volume-weighted, 80% core (104 outlets)")}"'),
          ("T13 note m3 p", f'0.058, 0.054, {pv(S + "d19_national_lp.csv", "D19 primary-spec h=0", "m3_median_h0")} and'),
          ("T14/E2 High p", f'"(0.06, 0.30)","{pv(S + "d20_regime.csv", "D20 IPI x High")}"'),
          ("E1 wire p", f'"(0.009, 0.641)","{pv(R + "d19_national_lp.csv", "D11 robustness row_wire_filter")}"'),
          ("E1 2018 core p", f'"(−0.015, 0.579)","{pv(R + "d19_national_lp.csv", "D11 robustness ipi_core2018_with_vernacular")}"'),
          ("F1 ver|eng p", f'"(−0.048, 0.460)","{pv(S + "e2_d19.csv", "E2 ver with eng control (y1_median)")}"'),
          ("F1 eng cur p", f'"(0.012, 0.303)","{pv(S + "e2_d19.csv", "E2 eng only, D19 spec (cur_median)", "cur_median_h0")}"'),
          ("F1 S^int p", f'"(−0.285, 0.179)","{pv(S + "e4_d19.csv", "E4 S^int alongside IPI (D19 spec)")}"'),
          ("F1 excess p", f'"(−0.027, 0.610)","{pv(S + "e5_excess_attention.csv", "E5 ExcessAttention (disinflation) in D19 spec")}"'),
          ("F1 excess base p", f'"(−0.162, 0.678)","{pv(R + "e5_excess_attention.csv", "E5 ExcessAttention (disinflation) in D19 spec")}"'),
          ("T15 baseline AR1 ratio", f'["AR(1)","Baseline","{f(pd.read_csv(PIPE / R / "d22_forecast_eval.csv").set_index("benchmark").loc["AR1"].rmse_ratio)}"'),
          ("T11 60% CI hi", f'"0.30 [0.09, {f(pd.read_csv(PIPE / S / "extra_robustness.csv").set_index("model").loc["presence 60% (180 outlets)"].ci_hi)}]')]
    return c


def main() -> int:
    js = "const c=require('./content.js'),a=require('./appendix.js');console.log(JSON.stringify({b:[...c.body,...a],abs:c.abstract,refs:c.refs}))"
    doc = json.loads(subprocess.run(["node", "-e", js], cwd=SRC, capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    rows, summary = [], {}
    # 1 tables
    for item in doc["b"]:
        if item[0] != "table":
            continue
        key = next((k for k in TABLES if item[1].startswith(k)), None)
        cells = " | ".join(" | ".join(map(str, r)) for r in item[3])
        if key is None:
            if NUM.search(cells):
                rows.append(dict(layer="table", where=item[1][:40], number="(no source mapped)", matched=False))
            continue
        P = expand([v for s in TABLES[key] for v in vals_of(s)])
        n_bad = 0
        for m in NUM.finditer(cells):
            ok = match(P, m.group(0), len(m.group(1)))
            n_bad += not ok
            rows.append(dict(layer="table", where=key, number=m.group(0), matched=ok, context=cells[max(0, m.start() - 50):m.end() + 10]))
        summary[key] = dict(chance_2dp=chance(P), unmatched=n_bad)
    # 2 claims
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).replace('\\"', '"')
    for lab, exp in claims():
        rows.append(dict(layer="claim", where=lab, number=exp, matched=exp in text))
    # 3 pooled screen over prose
    allfiles = sorted({s for v in TABLES.values() for s in v if not s.startswith("@")} |
                      {str(p.relative_to(PIPE)).replace("\\", "/") for d in (R, S, R2, R3) for p in (PIPE / d).glob("*.csv")} |
                      {str(p.relative_to(PIPE)).replace("\\", "/") for d in (R, S, R2, R3) for p in (PIPE / d).glob("*.json")})
    P = expand([v for s in allfiles for v in vals_of(s)])
    prose = " ".join([doc["abs"]] + [x[1] if x[0] == "p" else "" for x in doc["b"]])
    prose = re.sub(r"\d{4}–\d{2}|\d{4}-\d{2}", "", prose)
    for m in NUM.finditer(prose):
        rows.append(dict(layer="prose screen", where="prose", number=m.group(0), matched=match(P, m.group(0), len(m.group(1))),
                         context=prose[max(0, m.start() - 60):m.end() + 15]))
    summary["prose_pool_chance_2dp"], summary["prose_pool_chance_3dp"] = chance(P, 2), chance(P, 3)
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "r3_numcheck.csv", index=False)
    for layer, g in d.groupby("layer"):
        summary[f"{layer}: checked"], summary[f"{layer}: unmatched"] = int(len(g)), int((~g.matched).sum())
    (OUT / "r3_numcheck.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if not k.startswith("Table")}, indent=1))
    print("per-table chance rate (2 dp):", {k: v["chance_2dp"] for k, v in summary.items() if k.startswith("Table")})
    for _, r in d[~d.matched].iterrows():
        print("UNMATCHED", r["layer"], "|", r["where"], "|", r.number, "|", str(r.get("context", ""))[:140])
    return 0


if __name__ == "__main__":
    sys.exit(main())
