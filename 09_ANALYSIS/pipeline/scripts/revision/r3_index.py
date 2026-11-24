"""Revision round 3, items needing the cached extraction (no new queries):
  C12 outlet de-duplication: subdomains of one parent outlet in the same language are pooled (economictimes.* and
      haryana.punjabkesari.in -> punjabkesari.in); lifestyle/entertainment domains are dropped. Window index rebuilt with
      the paper's rules (host-day distinct URLs on valid days, presence >= 10, equal-weight mean) and the primary LP re-run.
  C13 non-energy price family: price-family articles that carry at least one of ECON_INFLATION, WB_442_INFLATION,
      ECON_COST_OF_LIVING, ECON_PRICECONTROL / WB_2107_PRICE_CONTROLS, ECON_PRICEGOUGE / ECON_PRICEMANIPULATION (the
      cached theme bits; the cache does not separate FUELPRICES from the gasoline/diesel codes or WB_1623 from other
      subsidy codes, so those are excluded too). Window index, primary LP, and audit precision/recall from existing codes.
  C16 tone: GDELT V2Tone (overall tone) of audited relevant articles coded rising vs falling.
Check: the identity mapping reproduces the published price-family window index.
Writes data/processed/results_revision3/r3_index.csv, r3_index_audit.csv, r3_index.json.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for p in ("scripts/revision", "scripts/build", "scripts/audit"):
    sys.path.insert(0, str(ROOT / p))
import r2_index as r2  # noqa: E402
import build_index as bi  # noqa: E402
import audit_metrics as am  # noqa: E402
import r3_audit  # noqa: E402

OUT = ROOT / "data/processed/results_revision3"
DROP = {"bollywoodhungama.com", "femina.in", "vogue.in", "desimartini.com", "bollywoodtadka.in", "cinema.dinamalar.com",
        "cinema.vikatan.com", "temple.dinamalar.com", "food.ndtv.com"}
NE_BITS = ("infl_baseline", "infl_wb442", "infl_costofliving", "price_control", "gouging")


def parent(h: str) -> str:
    if h.endswith(".economictimes.indiatimes.com"):
        return "economictimes.indiatimes.com"
    if h == "haryana.punjabkesari.in":
        return "punjabkesari.in"
    return h


def index_from(hd: pd.DataFrame, core: list, num: str, mapper=lambda h: h, drop=frozenset()) -> tuple[pd.Series, dict]:
    x = hd[hd.host.isin(core) & ~hd.host.isin(drop)].copy()
    x["outlet"] = x.host.map(mapper)
    w = x.groupby(["round", "outlet"], as_index=False)[["n_distinct_urls", num]].sum()
    w = w[(w.n_distinct_urls >= 10) & w["round"].isin(VALID)]
    w["a"] = w[num] / w.n_distinct_urls
    g = w.groupby("round")
    return g.a.mean(), dict(outlets=int(w.outlet.nunique()), per_window_min=int(g.outlet.nunique().min()),
                            per_window_median=float(g.outlet.nunique().median()))


def main() -> int:
    global VALID
    OUT.mkdir(parents=True, exist_ok=True)
    df = r2.frame()
    cfg = bi.bq.load_config(ROOT / "scripts/config.yaml")
    rung = cfg["rung"]
    P = {**bi.DEFAULTS, **(cfg.get("index") or {}), "nested_window_lengths": cfg.get("nested_window_lengths", [7, 14])}
    panel = pd.read_csv(ROOT / "data/processed/index/panel_outlets.csv")
    ps = set(panel[panel.in_panel.astype(bool)].domain)
    flags = bi.load_flags(ROOT / "scripts/build/flags.csv")
    A, G, _ = bi.load_all(ROOT, rung, flags, ROOT / "data/processed/index/cache", print)
    dcf = glob.glob(str(ROOT / "data/processed/bq_out/daycount_L2/*.parquet"))
    dayv = bi.day_validity(G, ps, pd.concat(pd.read_parquet(f) for f in dcf) if dcf else None, P)
    cal = bi.window_calendar(cfg, rung, ROOT / cfg["paths"]["iesh_rounds"])
    win, hw, core, host_day = bi.build_window(A, G, cal, dayv, ps, flags, P, {})
    VALID = set(win.loc[win.valid_window, "round"])
    bit = dict(zip(flags.flag, flags.bit.astype(int)))
    Aw = A[A.window_day & A.source.isin(ps)].merge(cal[["pdate", "round"]], on="pdate", how="inner")
    Aw["ne_flag"] = Aw.is_price & np.any([bi.has(Aw.fmask, bit[b]) for b in NE_BITS], axis=0)
    num = (Aw[Aw["ne_flag"]].drop_duplicates(["round", "pdate", "host", "url_norm"]).groupby(["round", "pdate", "host"]).size()
           .rename("n_ne").reset_index())
    hd = host_day[host_day.use].merge(num, on=["round", "pdate", "host"], how="left").fillna({"n_ne": 0})
    info = {}
    ref, info["identity"] = index_from(hd, core, "n_price_distinct")
    pub = pd.read_csv(ROOT / "data/processed/index/ipi_window.csv").set_index("round").variant_price_family
    info["identity_max_abs_diff_vs_published"] = float((ref - pub.reindex(ref.index)).abs().max())
    dedup, info["dedup"] = index_from(hd, core, "n_price_distinct", parent, DROP)
    info["dedup_dropped"] = sorted(DROP & set(core))
    info["dedup_pooled"] = sorted(h for h in core if parent(h) != h)
    ne, info["nonenergy"] = index_from(hd, core, "n_ne")
    assert ne.notna().sum() > 50, "non-energy index empty"
    info["nonenergy_mean_pct"] = float(100 * ne.mean())
    info["pricefamily_mean_pct"] = float(100 * ref.mean())
    info["corr_nonenergy_pricefamily"] = float(pd.concat([ne, ref], axis=1).corr().iloc[0, 1])
    info["corr_dedup_pricefamily"] = float(pd.concat([dedup, ref], axis=1).corr().iloc[0, 1])
    rows = [r2.refit(df, ref, "price family, identity rebuild (reference)"),
            r2.refit(df, dedup, f"outlets de-duplicated ({info['dedup']['outlets']} outlets)"),
            r2.refit(df, ne, "non-energy price family")]
    pd.DataFrame(rows).to_csv(OUT / "r3_index.csv", index=False)

    # audit: match audited articles to article rows by normalised URL and day
    fr = r3_audit.frame()
    man = pd.read_csv(ROOT / "data/interim/audit/audit_manifest.csv", dtype={"audit_id": str})
    key = pd.read_csv(ROOT / "data/interim/audit/private/audit_key.csv", dtype={"audit_id": str})
    m = man[["audit_id", "url"]].merge(key[["audit_id", "window_day"]], on="audit_id")
    m["url_norm"] = bi.norm_url(m.url)
    m["pdate"] = pd.to_datetime(m.window_day.astype(str)).dt.date
    a = A[["pdate", "url_norm", "is_price", "fmask", "tone_key"]].copy()
    a["ne_flag"] = a.is_price & np.any([bi.has(a.fmask, bit[b]) for b in NE_BITS], axis=0)
    a = a.sort_values("ne_flag").drop_duplicates(["pdate", "url_norm"], keep="last")
    m = m.merge(a[["pdate", "url_norm", "is_price", "ne_flag", "tone_key"]], on=["pdate", "url_norm"], how="left")
    fr = fr.merge(m[["audit_id", "is_price", "ne_flag", "tone_key"]], on="audit_id", how="left")
    pf = fr.flag_price_family == 1
    info["audit_price_family_tagged"] = int(pf.sum())
    info["audit_price_family_matched_to_rows"] = int((pf & fr.is_price.fillna(False).astype(bool)).sum())
    fr["flag_nonenergy"] = (pf & fr["ne_flag"].fillna(False).astype(bool)).astype(int)
    info["audit_nonenergy_tagged"] = int(fr.flag_nonenergy.sum())
    (cells, point), (ci, _) = am.estimate_prf(fr, "rel_A", ["flag_baseline", "flag_price_family", "flag_nonenergy"], 1000,
                                              20261116 + 7, cluster_by_day=False, collapse_empty=True)
    ar = []
    for v in ("flag_baseline", "flag_price_family", "flag_nonenergy"):
        for mt in ("precision", "recall", "f2"):
            k = (v, "gating", "all", mt)
            ar.append(dict(variant=v, metric=mt, estimate=point[k], ci_lo=ci[k][0], ci_hi=ci[k][1]))
    pd.DataFrame(ar).to_csv(OUT / "r3_index_audit.csv", index=False)
    # C16 tone among relevant articles coded rising vs falling
    fr["tone"] = pd.to_numeric(fr.tone_key.fillna("").str.split(",").str[0], errors="coerce")
    rel = fr[(fr.rel_A == "Y") & fr.dir_A.isin(["rising", "falling"])]
    info["tone_direction_counts"] = fr[fr.rel_A == "Y"].dir_A.value_counts(dropna=False).to_dict()
    tr = rel.dropna(subset=["tone"])
    info["tone_n_with_tone"] = {d: int((tr.dir_A == d).sum()) for d in ("rising", "falling")}
    info["tone_mean"] = {d: float(tr[tr.dir_A == d].tone.mean()) for d in ("rising", "falling")}
    if tr.dir_A.nunique() == 2:
        from scipy import stats
        u = stats.mannwhitneyu(tr[tr.dir_A == "falling"].tone, tr[tr.dir_A == "rising"].tone)
        info["tone_auc_falling_more_positive"] = float(u.statistic / ((tr.dir_A == "falling").sum() * (tr.dir_A == "rising").sum()))
        info["tone_mannwhitney_p"] = float(u.pvalue)
    (OUT / "r3_index.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info, indent=1, default=str))
    print(pd.DataFrame(rows)[["model", "N", "beta", "ci_lo", "ci_hi", "p_wild", "corr_with_published_series"]].round(4).to_string())
    print(pd.DataFrame(ar).round(4).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
