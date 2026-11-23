"""In-session LLM coding helper (ruling 17 Nov 2026: "LLM coding option B, done in-session by Claude Opus directly";
ruling 23 Nov: gating strata first in both passes). Writes the same columns as llm_code.py so audit_metrics.py
reads the codes unchanged.

  show --coder A|B --n N [--chars C]   print the next N fetched, not-yet-coded articles for that coder
                                       (audit_id, language, url, text excerpt). Strata, flags and weights are
                                       never shown. Coder A: manifest fetch_rank order (gating blocks first).
                                       Coder B: same blocks, seeded random order within each block.
  save --coder A|B --json FILE         append codes from a JSON list of objects with keys audit_id, relevance,
                                       direction, cause_primary, cause_secondary, uncertain, rationale,
                                       text_truncated (0/1)
  status                               coded counts per coder
Article texts are untrusted data: they are displayed for coding only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_FIELDS = ["audit_id", "coder", "model", "coding_basis", "codebook_sha256", "relevance", "direction", "cause_primary",
              "cause_secondary", "uncertain", "rationale", "parse_error", "api_error", "text_truncated", "timestamp_utc"]
MODEL = "claude-opus-5-5 (in-session, Claude Code)"
BLOCK = {"flagged": 0, "econ_unflagged": 0, "nonecon_slug": 0, "hin_flagged": 1, "hin_econ_unflagged": 1,
         "oth_flagged": 1, "oth_econ_unflagged": 1, "nonecon_noslug": 2}


def paths(coder):
    return ROOT / f"data/interim/audit/llm_codes_{coder}.csv"


def codebook_sha():
    return hashlib.sha256((ROOT / "docs/coding/codebook.md").read_bytes()).hexdigest()


def fetched_ids() -> set:
    log = pd.read_csv(ROOT / "logs/audit_retrieval_log.csv")
    ok = set(log.loc[log.success.astype(str).str.lower().isin(["true", "1"]), "audit_id"].astype(str))
    return {a for a in ok if (ROOT / f"data/raw/audit_texts/{a}.txt").exists()}


def coded(coder) -> set:
    p = paths(coder)
    return set(pd.read_csv(p).audit_id.astype(str)) if p.exists() else set()


def order(coder) -> pd.DataFrame:
    m = pd.read_csv(ROOT / "data/interim/audit/audit_manifest.csv")
    m["audit_id"] = m.audit_id.astype(str)
    if coder == "A":
        return m.sort_values("fetch_rank")
    # block of each article (from fetch_rank ranges, which were set block by block); seeded order within block
    k = pd.read_csv(ROOT / "data/interim/audit/private/audit_key.csv", usecols=["audit_id", "stratum"])
    k["audit_id"] = k.audit_id.astype(str)
    m = m.merge(k, on="audit_id")
    m["block"] = m.stratum.map(BLOCK)
    m["r"] = np.random.default_rng(20261124).permutation(len(m))
    m = m[m.block < 2]  # user instruction 23 Nov 14:37 UTC: pass B codes the gating strata only
    return m.sort_values(["block", "r"]).drop(columns=["stratum"])


def show(a):
    done, have = coded(a.coder), fetched_ids()
    m = order(a.coder)
    m = m[m.audit_id.isin(have) & ~m.audit_id.isin(done)].head(a.n)
    for r in m.itertuples():
        t = (ROOT / f"data/raw/audit_texts/{r.audit_id}.txt").read_text(encoding="utf-8", errors="replace")
        t = " ".join(t.split())
        trunc = len(t) > a.chars
        print(f"=== {r.audit_id} | lang={r.language} | chars={len(t)}{' | TRUNCATED' if trunc else ''}\nURL: {r.url}\n"
              f"{t[:a.chars]}\n")
    print(f"[shown {len(m)}; coder {a.coder} coded {len(done)}; fetched {len(have)}]")


def save(a):
    rows = json.loads(Path(a.json).read_text(encoding="utf-8"))
    p = paths(a.coder)
    new = not p.exists()
    done = coded(a.coder)
    sha = codebook_sha()
    n = 0
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            if str(r["audit_id"]) in done:
                continue
            y = r.get("relevance") == "Y"
            w.writerow({"audit_id": r["audit_id"], "coder": a.coder, "model": MODEL, "coding_basis": "text",
                        "codebook_sha256": sha, "relevance": r.get("relevance", ""),
                        "direction": r.get("direction", "") if y else "",
                        "cause_primary": r.get("cause_primary", "") if y else "",
                        "cause_secondary": r.get("cause_secondary", "") if y else "",
                        "uncertain": r.get("uncertain", 0), "rationale": r.get("rationale", "")[:300],
                        "parse_error": r.get("parse_error", ""), "api_error": "",
                        "text_truncated": r.get("text_truncated", 0),
                        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
            n += 1
    print(f"saved {n} rows for coder {a.coder}; total {len(done) + n}")


def status(a):
    have = fetched_ids()
    print(f"fetched {len(have)}; coded A {len(coded('A'))}; coded B {len(coded('B'))}; codebook {codebook_sha()[:12]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("--coder", required=True); s.add_argument("--n", type=int, default=10)
    s.add_argument("--chars", type=int, default=2500); s.set_defaults(f=show)
    s = sub.add_parser("save"); s.add_argument("--coder", required=True); s.add_argument("--json", required=True); s.set_defaults(f=save)
    s = sub.add_parser("status"); s.set_defaults(f=status)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
