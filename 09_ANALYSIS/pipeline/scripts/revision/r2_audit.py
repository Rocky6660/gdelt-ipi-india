"""Revision round 2, audit items: (1) retrieval bounds for the unretrieved sampled articles (all relevant / none
relevant / slug-coded labels imputed), by stratum; (2) precision, recall, F2 with 95% stratified-bootstrap CIs by
language and retrieval route. Same weights, cells, bootstrap and seed as the main audit run (coder A truth,
collapse-empty-cells). No flag or estimate of the main analysis is changed. Output: outputs/audit_revision2/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/audit"))
import audit_metrics as am  # noqa: E402

OUT = ROOT / "outputs/audit_revision2"
VARS = ["flag_baseline", "flag_price_family"]
_orig = am.make_groups


def groups(d):
    g = _orig(d)
    g["mode=unretrieved"] = (d["retrieval_mode"] == "").to_numpy()
    for s in sorted(d["stratum"].unique()):
        g[f"stratum={s}"] = (d["stratum"] == s).to_numpy()
    return g


am.make_groups = groups


def table(frame, col, label, B=1000):
    (cells, point), (ci, _) = am.estimate_prf(frame, col, VARS, B, 20261116 + 7, cluster_by_day=False, collapse_empty=True)
    rows = []
    for (v, fr, g, m), est in point.items():
        if v == "__tot__":
            continue
        gm = cells.groups[g] & cells.frames[fr]
        rows.append(dict(case=label, variant=v, frame=fr, group=g, metric=m, estimate=est, ci_lo=ci[(v, fr, g, m)][0],
                         ci_hi=ci[(v, fr, g, m)][1], n_coded=int(gm.sum()),
                         n_flagged=int((gm & cells.flags[v]).sum()), n_relevant=int((gm & cells.rel).sum())))
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rd = lambda p: pd.read_csv(ROOT / p, dtype={"audit_id": str})  # noqa: E731
    fr = am.build_frame(rd("data/interim/audit/private/audit_key.csv"), rd("data/interim/audit/audit_manifest.csv"), None,
                        rd("data/interim/audit/llm_codes_A.csv"), None, rd("logs/audit_retrieval_log.csv"),
                        rd("data/interim/audit/llm_codes_slug_A.csv"))
    miss = fr.rel_A.isna()
    print("sampled", len(fr), "coded A", int((~miss).sum()), "unretrieved", int(miss.sum()),
          "slug-coded among unretrieved", int((miss & fr.rel_S.notna()).sum()))
    fr["rel_allY"] = fr.rel_A.where(~miss, "Y")
    fr["rel_noneY"] = fr.rel_A.where(~miss, "N")
    fr["rel_slug"] = fr.rel_A.where(~miss, fr.rel_S)
    t = pd.concat([table(fr, "rel_A", "reference (missing at random)"), table(fr, "rel_allY", "unretrieved all relevant"),
                   table(fr, "rel_noneY", "unretrieved none relevant"), table(fr, "rel_slug", "slug labels imputed")])
    t.to_csv(OUT / "prf_revision2.csv", index=False)
    miss_tab = fr[miss].groupby(["stratum"]).agg(unretrieved=("audit_id", "size"), slug_coded=("rel_S", lambda s: s.notna().sum()),
                                                 slug_relevant=("rel_S", lambda s: (s == "Y").sum()))
    miss_tab.to_csv(OUT / "unretrieved_by_stratum.csv")
    print(miss_tab)
    return 0


if __name__ == "__main__":
    sys.exit(main())
