"""D34 row-count reconciliation (run 23 Nov 2026 by user instruction).
(a) download completeness: manifest rows_written == rows_expected for every Q2 chunk;
(b) same-scan reconciliation: count of inflation-flagged article rows (A) per source x day x language equals the
    aggregate n_infl (S rows on window days, D rows on other days) from the same scan, and likewise is_econ vs n_econ;
(c) Q1 comparison: Q1 totals are per (domain, language) over all Q1 days (no day split), so only an exact re-count on
    the days shared by the Q1 and L3 grids can test +/-1%; that needs a new query (priced separately).
Writes data/processed/checks/d34_reconcile.json and prints a summary."""
import glob, json, sys
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
root = Path(__file__).resolve().parents[2]
out = {}
bad = []
for d in sorted(glob.glob(str(root / "data/processed/bq_out/q2_[AB]_L3_*"))):
    m = json.loads((Path(d) / "manifest.json").read_text())
    if m["rows_written"] != m["rows_expected"]:
        bad.append((Path(d).name, m["rows_written"], m["rows_expected"]))
out["a_chunks"] = len(glob.glob(str(root / "data/processed/bq_out/q2_[AB]_L3_*")))
out["a_manifest_mismatches"] = bad
A, G = [], []
for f in glob.glob(str(root / "data/processed/index/cache/*__A.parquet")):
    if "pdate" not in pq.read_schema(f).names: continue  # empty chunk (e.g. 2025-06 GDELT gap)
    A.append(pd.read_parquet(f, columns=["pdate", "source", "src_lang", "is_infl", "is_econ", "window_day"]))
for f in glob.glob(str(root / "data/processed/index/cache/*__G.parquet")):
    if "pdate" not in pq.read_schema(f).names: continue
    G.append(pd.read_parquet(f, columns=["pdate", "source", "src_lang", "n_infl", "n_econ", "n_articles"]))
A = pd.concat(A); G = pd.concat(G)
A["pdate"] = A.pdate.astype(str); G["pdate"] = G.pdate.astype(str)
k = ["pdate", "source", "src_lang"]
a = A.groupby(k).agg(a_infl=("is_infl", "sum"), a_econ=("is_econ", "sum")).reset_index()
g = G.groupby(k)[["n_infl", "n_econ", "n_articles"]].sum().reset_index()
j = g.merge(a, on=k, how="outer").fillna(0)
for x, y in (("a_infl", "n_infl"), ("a_econ", "n_econ")):
    diff = (j[x] - j[y]).abs()
    out[f"b_{x}_vs_{y}"] = dict(keys=int(len(j)), keys_mismatched=int((diff > 0).sum()),
                                total_a=int(j[x].sum()), total_agg=int(j[y].sum()),
                                rel_diff=float(abs(j[x].sum() - j[y].sum()) / max(1, j[y].sum())))
p = root / "data/processed/checks"; p.mkdir(parents=True, exist_ok=True)
(p / "d34_reconcile.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
ok = not bad and all(v["keys_mismatched"] == 0 for kk, v in out.items() if kk.startswith("b_"))
print("D34 (a)+(b):", "PASS" if ok else "FAIL")
ab_ok = ok

# (c) exact recount on shared Q1/L3 days (job d34_recount, user instruction 23 Nov 2026)
rc_files = glob.glob(str(root / "data/processed/bq_out/d34_recount/*.parquet"))
if rc_files:
    rc = pd.concat(pd.read_parquet(f) for f in rc_files)
    rc["pdate"] = rc.pdate.astype(str)
    days = set(rc.pdate)
    q2 = g[g.pdate.isin(days)][k + ["n_articles"]]
    jj = rc.merge(q2, on=k, how="outer", suffixes=("_recount", "_q2")).fillna(0)
    tot_r, tot_q = jj.n_articles_recount.sum(), jj.n_articles_q2.sum()
    day = jj.groupby("pdate")[["n_articles_recount", "n_articles_q2"]].sum()
    day["rel"] = (day.n_articles_q2 - day.n_articles_recount).abs() / day.n_articles_recount.clip(lower=1)
    out["c_recount"] = dict(days=len(days), keys=int(len(jj)),
                            keys_mismatched=int((jj.n_articles_recount != jj.n_articles_q2).sum()),
                            total_recount=int(tot_r), total_q2=int(tot_q),
                            rel_diff_total=float(abs(tot_q - tot_r) / tot_r),
                            days_over_1pct=int((day.rel > 0.01).sum()), max_day_rel_diff=float(day.rel.max()),
                            worst_days=day.sort_values("rel", ascending=False).head(5).round(4).reset_index().to_dict("records"))
    out["c_pass_1pct"] = bool(out["c_recount"]["rel_diff_total"] <= 0.01 and out["c_recount"]["days_over_1pct"] == 0)
    (p / "d34_reconcile.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out["c_recount"], indent=1, default=str)); print("D34 (c) +/-1%:", "PASS" if out["c_pass_1pct"] else "FAIL")
sys.exit(0 if ab_ok and out.get("c_pass_1pct", True) else 1)
