"""D9/D17 switch chain, applied mechanically (design D9, D15, D17; user instruction 23 Nov: no tuning; the flag switches
only through the audit's best-F2 rule; if every variant fails, the index is "audited, not externally validated" and
H1/H5 are exploratory).

Order:
  1. D15: if the baseline fails (precision >= 0.5 and gating recall >= 0.6, primary truth source), the flag becomes the
     audit's best-F2 variant; otherwise the baseline stays.
  2. D17: validate the current flag's monthly series (Trends "inflation" r >= 0.5 AND >= 3 of 4 episodes). If it fails,
     try in order: best-F2 variant, strict flag (skipping ones already tried). The first that passes becomes the flag.
  3. If none passes: the flag from step 1 is kept, labelled "audited, not externally validated"; H1/H5 exploratory.
Inputs: outputs/audit/gate_report.json, data/processed/results/d17_validation*.json (computed here if missing).
Output: data/processed/results/d9_switch.json (flag, window column for phase1 --ipi-col, label, trail).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
MAP = {  # flag -> (monthly column, window column)
    "flag_baseline": ("ipi_monthly", "ipi_primary"),
    "flag_price_family": ("ipi_monthly_variant_price_family", "variant_price_family"),
    "flag_wb442": ("ipi_monthly_variant_wb442", "variant_wb442"),
    "flag_strict": ("ipi_monthly_variant_strict", "variant_strict"),
}


def d17(flag: str) -> dict:
    col = MAP[flag][0]
    tag = "" if flag == "flag_baseline" else f"_{flag}"
    subprocess.run([PY, str(ROOT / "scripts/analysis/d17_validation.py"), "--root", str(ROOT), "--col", col, "--tag", tag],
                   check=True, capture_output=True, env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    rep = json.loads((ROOT / f"data/processed/results/d17_validation{tag}.json").read_text())
    ok = bool(rep.get("trends_pass_inflation_term")) and bool(rep.get("episodes_pass_3_of_4"))
    return {"flag": flag, "series": col, "trends_pass": rep.get("trends_pass_inflation_term"),
            "episodes_peaking": rep.get("episodes_peaking"), "d17_pass": ok, "trends_provisional": rep.get("provisional")}


def main() -> int:
    g = json.loads((ROOT / "outputs/audit/gate_report.json").read_text())["gates"]["D15_precision_recall"]
    trail = [{"step": "D15", "status": g.get("status"), "precision": g.get("precision"),
              "gating_recall": g.get("gating_recall"), "best_f2_variant": g.get("best_f2_variant"),
              "f2_by_variant": g.get("f2_by_variant"), "action": g.get("action")}]
    best = g.get("best_f2_variant")
    flag = "flag_baseline"
    if str(g.get("status")) == "FAIL" and best and best != "flag_baseline":
        flag = best
    tried, validated = [], None
    for cand in [flag] + [c for c in (best, "flag_strict") if c and c not in (flag,)]:
        if cand in tried or cand not in MAP:
            continue
        tried.append(cand)
        r = d17(cand)
        trail.append({"step": "D17", **r})
        if r["d17_pass"]:
            validated = cand
            break
    final = validated or flag
    label = "validated (D15 + D17)" if validated and str(g.get("status")) == "PASS" else (
        "externally validated (D17); D15 via best-F2 rule" if validated else "audited, not externally validated")
    out = {"final_flag": final, "window_column": MAP[final][1], "monthly_column": MAP[final][0],
           "flag_changed": final != "flag_baseline", "label": label,
           "h1_h5_status": "confirmatory" if validated else "exploratory (D9: every variant failed D17)",
           "trail": trail}
    (ROOT / "data/processed/results/d9_switch.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
