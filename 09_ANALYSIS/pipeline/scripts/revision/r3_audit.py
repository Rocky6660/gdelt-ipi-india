"""Revision round 3, audit items: (A6) reconcile coded / relevant counts across Table 8, Section 4.1.1 and 4.1.4;
(C14) exact binomial CI for the unscreened non-economic stratum and the whole-flow recall bound across that CI.
Same weights and cells as the paper's audit (coder A truth, collapse-empty-cells). Writes results_revision3/r3_audit.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/audit"))
import audit_metrics as am  # noqa: E402

OUT = ROOT / "data/processed/results_revision3"


def frame():
    rd = lambda p: pd.read_csv(ROOT / p, dtype={"audit_id": str})  # noqa: E731
    return am.build_frame(rd("data/interim/audit/private/audit_key.csv"), rd("data/interim/audit/audit_manifest.csv"), None,
                          rd("data/interim/audit/llm_codes_A.csv"), None, rd("logs/audit_retrieval_log.csv"),
                          rd("data/interim/audit/llm_codes_slug_A.csv"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    fr = frame()
    f: dict = {}
    coded = fr[fr.rel_A.notna()]
    gating = coded[(coded.econ_row == 1) | coded.stratum.isin(am.SCREENED_NONECON)]
    f["coded_all"] = int(len(coded))
    f["relevant_all_first_pass"] = int((coded.rel_A == "Y").sum())
    f["relevant_by_stratum"] = coded[coded.rel_A == "Y"].stratum.value_counts().to_dict()
    f["gating_coded"] = int(len(gating))
    f["gating_relevant"] = int((gating.rel_A == "Y").sum())
    g = gating.groupby("lang_group").agg(coded=("audit_id", "size"), relevant=("rel_A", lambda s: int((s == "Y").sum())))
    f["gating_by_lang_group"] = g.to_dict("index")
    onf = gating[gating.lang_group == "other_nonfocal"]
    f["other_nonfocal_by_stratum_language"] = onf.groupby(["stratum", "language"]).size().rename("n").reset_index().to_dict("records")
    f["other_nonfocal_flagged_baseline"] = int((onf.flag_baseline == 1).sum())
    f["other_nonfocal_flagged_price_family"] = int((onf.flag_price_family == 1).sum())
    # C14 bound: R(p) = TP / (Rel_gating + N_noslug * p), for the point share and the exact CI limits
    (cells, point), _ = am.estimate_prf(fr, "rel_A", ["flag_baseline", "flag_price_family"], 1, 20261116 + 7, False,
                                        collapse_empty=True)
    rel_tot = point[("__tot__", "gating", "all", "rel_total")]
    ns = fr[(fr.stratum == "nonecon_noslug")]
    codes = ns.rel_A.dropna()
    k, n = int((codes == "Y").sum()), len(codes)
    lo, hi = am.clopper_pearson(k, n)
    N_ns = float(ns.sampling_weight.sum())
    bound = {"relevant": k, "n": n, "share": k / n, "exact_ci_lo": lo, "exact_ci_hi": hi}
    for v in ("flag_baseline", "flag_price_family"):
        R = point[(v, "gating", "all", "recall")]
        tp = R * rel_tot
        for lab, p in (("at_ci_lo", lo), ("at_point", k / n), ("at_ci_hi", hi)):
            bound[f"{v}_recall_whole_flow_{lab}"] = tp / (rel_tot + N_ns * p)
        bound[f"{v}_recall_gating"] = R
    f["C14_unscreened_bound"] = bound
    (OUT / "r3_audit.json").write_text(json.dumps(f, indent=1, default=str))
    print(json.dumps(f, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
