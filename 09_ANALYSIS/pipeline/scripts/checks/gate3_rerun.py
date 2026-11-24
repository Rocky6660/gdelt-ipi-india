"""Gate 3 scripted verification re-run (design_final schedule Day 8-9: "verification re-run"; handoff step 6).

Re-runs the analysis chain from the cached GDELT extraction and compares the re-run outputs with the outputs the
paper cites. Nothing is queried from BigQuery (0 GB): build_index reads the compacted cache of the Stage A/B parquet.

Steps
  1. Hash the current index outputs and copy them to data/processed/gate3/before/.
  2. Re-run build_index.py (writes the index files in place), then compare with the copies.
  3. Re-run phase1.py with the final flag columns (from results/d9_switch.json if present) into results_gate3/,
     and d17_validation.py for the final monthly column with tag _gate3; compare with the cited results.
  4. Re-run audit_metrics.py into outputs/audit_gate3/ (same inputs, same seed) and compare gate statuses.
Comparison: CSVs are compared as numbers with a tolerance (abs 1e-9 + rel 1e-7, after aligning rows and columns);
non-numeric cells must match exactly. Bootstrap outputs use fixed seeds, so they are expected to match.
Output: data/processed/gate3/gate3_report.md and .json (PASS only if every compared file matches).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
IDX = ["ipi_window.csv", "ipi_monthly.csv", "ipi_daily.csv", "panel_outlets.csv"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"


def run(args: list[str]) -> None:
    r = subprocess.run([PY, *args], cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"{args[0]} failed:\n{r.stderr[-3000:]}")


def compare_csv(a: Path, b: Path) -> dict:
    if not a.exists() or not b.exists():
        return {"match": False, "reason": f"missing: {a if not a.exists() else b}"}
    if sha(a) == sha(b):
        return {"match": True, "reason": "identical bytes"}
    x, y = pd.read_csv(a), pd.read_csv(b)
    if list(x.columns) != list(y.columns) or len(x) != len(y):
        return {"match": False, "reason": f"shape/columns differ {x.shape} vs {y.shape}"}
    worst, bad = 0.0, []
    for c in x.columns:
        xn, yn = pd.to_numeric(x[c], errors="coerce"), pd.to_numeric(y[c], errors="coerce")
        if xn.notna().sum() == x[c].notna().sum() and x[c].notna().any():
            d = (xn - yn).abs()
            tol = 1e-9 + 1e-7 * yn.abs()
            both_nan = xn.isna() & yn.isna()
            off = ~((d <= tol) | both_nan)
            if off.any():
                bad.append(c)
                worst = max(worst, float(d[off].max()))
        elif not (x[c].astype(str) == y[c].astype(str)).all():
            bad.append(c)
    return {"match": not bad, "reason": "numeric within tolerance" if not bad else f"columns differ: {bad[:8]} (max abs diff {worst:.3g})"}


def main() -> int:
    out = ROOT / "data/processed/gate3"
    before = out / "before"
    before.mkdir(parents=True, exist_ok=True)
    idx = ROOT / "data/processed/index"
    rep = {"steps": [], "files": {}}
    for f in IDX:
        shutil.copy2(idx / f, before / f)
    run(["scripts/build/build_index.py", "--root", str(ROOT)])
    for f in IDX:
        rep["files"][f"index/{f}"] = compare_csv(idx / f, before / f)
    rep["steps"].append("build_index re-run from cache")

    sw = ROOT / "data/processed/results/d9_switch.json"
    s = json.loads(sw.read_text()) if sw.exists() else {"window_column": "ipi_primary", "monthly_column": "ipi_monthly",
                                                         "flag_changed": False}
    cited = "data/processed/results" if not s.get("flag_changed") else "data/processed/results_switched"
    run(["scripts/analysis/phase1.py", "--root", str(ROOT), "--ipi-col", s["window_column"],
         "--monthly-col", s["monthly_column"], "--out", "data/processed/results_gate3"])
    for f in ("d19_national_lp.csv", "d20_regime.csv", "d22_forecast_eval.csv", "d23_monthly_lp.csv", "d19_persistence.csv"):
        rep["files"][f"phase1/{f}"] = compare_csv(ROOT / "data/processed/results_gate3" / f, ROOT / cited / f)
    rep["steps"].append(f"phase1 re-run ({s['window_column']}, {s['monthly_column']}) vs {cited}")

    tag = "" if s["monthly_column"] == "ipi_monthly" else "_" + {
        "ipi_monthly_variant_price_family": "flag_price_family", "ipi_monthly_variant_wb442": "flag_wb442",
        "ipi_monthly_variant_strict": "flag_strict"}[s["monthly_column"]]
    run(["scripts/analysis/d17_validation.py", "--root", str(ROOT), "--col", s["monthly_column"], "--tag", "_gate3"])
    rep["files"]["d17/d17_validation.csv"] = compare_csv(ROOT / "data/processed/results/d17_validation_gate3.csv",
                                                         ROOT / f"data/processed/results/d17_validation{tag}.csv")
    rep["steps"].append("d17 re-run")


    # switch decision and the switched-flag extensions / paper outputs (FINAL_TOUCHES Part 5 item 12)
    sw_before = (ROOT / "data/processed/results/d9_switch.json").read_text()
    run(["scripts/analysis/d9_switch.py"])
    rep["files"]["switch/d9_switch.json"] = {"match": json.loads(sw_before)["final_flag"] == json.loads(
        (ROOT / "data/processed/results/d9_switch.json").read_text())["final_flag"], "reason": "final flag unchanged"}
    ext_dir = ROOT / "data/processed/gate3/ext"
    ext_dir.mkdir(parents=True, exist_ok=True)
    env = {**ENV, "IPI_COL": s["window_column"], "MONTHLY_COL": s["monthly_column"], "EXT_OUT": "data/processed/gate3/ext"}
    r = subprocess.run([PY, "scripts/analysis/extensions_descriptive.py"], cwd=ROOT, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    for f in ("e2_d19.csv", "e4_d19.csv", "e5_excess_attention.csv", "e5_peaks.csv", "e2_leadlag_monthly.csv"):
        rep["files"][f"extensions/{f}"] = compare_csv(ext_dir / f, ROOT / cited / f)
    rep["steps"].append("d9_switch and switched-flag extensions re-run")

    if (ROOT / "outputs/audit/gate_report.json").exists():
        run(["scripts/audit/audit_metrics.py", "--key", "data/interim/audit/private/audit_key.csv",
             "--manifest", "data/interim/audit/audit_manifest.csv", "--llm-a", "data/interim/audit/llm_codes_A.csv",
             "--llm-b", "data/interim/audit/llm_codes_B.csv", "--slug-a", "data/interim/audit/llm_codes_slug_A.csv",
             "--log", "logs/audit_retrieval_log.csv", "--no-human", "--variants", "flag_price_family,flag_wb442,flag_strict",
             "--collapse-empty-cells", "--out-dir", "outputs/audit_gate3"])
        g1 = json.loads((ROOT / "outputs/audit/gate_report.json").read_text())["gates"]
        g2 = json.loads((ROOT / "outputs/audit_gate3/gate_report.json").read_text())["gates"]
        st = {k: (g1[k].get("status"), g2.get(k, {}).get("status")) for k in g1}
        rep["files"]["audit/gate_statuses"] = {"match": all(a == b for a, b in st.values()), "reason": str(st)}
        rep["files"]["audit/metrics_prf.csv"] = compare_csv(ROOT / "outputs/audit_gate3/metrics_prf.csv",
                                                            ROOT / "outputs/audit/metrics_prf.csv")
        rep["steps"].append("audit_metrics re-run")

    rep["status"] = "PASS" if all(v["match"] for v in rep["files"].values()) else "FAIL"
    (out / "gate3_report.json").write_text(json.dumps(rep, indent=1))
    md = ["# Gate 3 verification re-run (auto-generated)", "", f"Status: **{rep['status']}**", "",
          "Steps: " + "; ".join(rep["steps"]), "", "| file | match | detail |", "|---|---|---|"]
    md += [f"| {k} | {v['match']} | {v['reason']} |" for k, v in rep["files"].items()]
    (out / "gate3_report.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
