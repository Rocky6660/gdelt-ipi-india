#!/usr/bin/env python3
"""Draw the D15 audit strata from an article-level parquet, with inverse-probability weights.

Input parquet columns (as produced by the extraction):
  GKGRECORDID, DATE, DocumentIdentifier, SourceCommonName, Themes, TranslationInfo,
  and boolean flag columns named flag_* . ASSUMPTIONS (check against the extraction):
  --baseline-col (default flag_baseline) = ECON_INFLATION baseline flag,
  --econ-col     (default flag_econ)     = any ECON theme. Other flag_* columns (variants,
  flag_international, ...) are carried into the key's gdelt_flags field.
  DATE is YYYYMMDDHHMMSS (int/str) or a datetime. Language comes from TranslationInfo
  ("srclc:hin; ..."); empty TranslationInfo = English ('en').

Strata (mutually exclusive). Focal vernacular = Hindi + (Marathi or Bengali, whichever has
more articles in the input). General strata use all other languages:
  flagged 300 | econ_unflagged 300 | nonecon_slug 150 | nonecon_noslug 100
  hin_flagged 100 | hin_econ_unflagged 100 | <oth>_flagged 100 | <oth>_econ_unflagged 100
Focal-language non-ECON articles are not sampled (D15 has no such stratum), so vernacular
recall is recall within ECON only.

Within each stratum, 2015-2018 articles are oversampled by --oversample (default 1.5 in Mode A,
forced to 1.0 in Mode B) through two sub-strata (2015-18 vs later) with simple random sampling
inside each, so inclusion probabilities are exact: pi = n_sub / N_sub, weight = 1 / pi.
If a sub-stratum is smaller than its allocation, all of it is taken (pi = 1) and the shortfall is
written to the meta file. Nothing is topped up from other strata.

Mode B (GDELT-only): --mode B needs --modeb-days K; 2020+ rows are limited to K seeded window
days and their weights are multiplied by D/K (D = number of 2020+ days in the input) so the
design weight still reflects the full population. Day-clustering must then be reflected in the
bootstrap (audit_metrics.py --mode B does this).

DOC stratum (D15 "+60 DOC keyword hits unflagged by themes", only if DOC passes): --doc-hits FILE
(csv/parquet with DocumentIdentifier or GKGRECORDID) adds stratum doc_unflagged (target --doc-target,
default 60) = general-language, baseline-unflagged articles with a DOC hit. It takes precedence over
econ_unflagged / nonecon_* for those articles, so strata stay mutually exclusive. It belongs to the
gating frame (it is DOC-screened); its ECON members also count in the ECON frame through the key's
econ_row column.

Two tranches (D34 Stage A then Stage B): run once per tranche on that tranche's window-day data with
--tranche A|B (--tranche-fraction-a, default 0.5, splits each stratum target and each human
allocation: A gets floor(x*f), B the remainder). Tranches use disjoint populations, different seeds,
ids prefixed T<tranche>, and their keys can be concatenated by audit_metrics.py (--key k1 k2).

Human subsample: --human-languages (default en,hin). Marathi/Bengali articles are assigned to
LLM-only coding unless the user confirms they read them (then add the language, e.g. en,hin,mar). The
total stays 150 (default 110 English + 40 Hindi); general strata draw humans from eligible languages only.

Outputs (paths configurable): manifest (audit_id,url,language,...; no strata), private key,
blind coder sheet for the human subsample, meta JSON.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import pandas as pd

SEED = 20261116
TARGETS = {
    "flagged": 300,
    "econ_unflagged": 300,
    "nonecon_slug": 150,
    "nonecon_noslug": 100,
    "hin_flagged": 100,
    "hin_econ_unflagged": 100,
    "oth_flagged": 100,
    "oth_econ_unflagged": 100,
}
HUMAN_ALLOC_BASE = {  # 110 English + 40 Hindi = 150 (default: English + Hindi only)
    "flagged": 40, "econ_unflagged": 35, "nonecon_slug": 25, "nonecon_noslug": 10,
    "doc_unflagged": 0, "hin_flagged": 20, "hin_econ_unflagged": 20, "oth_flagged": 0, "oth_econ_unflagged": 0,
}
HUMAN_ALLOC_WITH_OTH = {  # if the coder confirms they read the second vernacular language
    "flagged": 35, "econ_unflagged": 30, "nonecon_slug": 20, "nonecon_noslug": 10,
    "doc_unflagged": 0, "hin_flagged": 20, "hin_econ_unflagged": 20, "oth_flagged": 8, "oth_econ_unflagged": 7,
}


def human_allocation(human_langs, other_lang):
    return dict(HUMAN_ALLOC_WITH_OTH if other_lang in human_langs else HUMAN_ALLOC_BASE)


def tranche_split(x: int, tranche, fa: float) -> int:
    if tranche is None:
        return x
    a = int(np.floor(x * fa))
    return a if tranche == "A" else x - a


OVERSAMPLE_YEARS = (2015, 2018)

# Price keywords tested on URL slug tokens (lower case, URL-decoded). Edit or pass --keywords-file.
DEFAULT_KEYWORDS = [
    "inflation", "price", "prices", "pricey", "cpi", "wpi", "costlier", "dearer", "expensive",
    "pricier", "mehngai", "mehangai", "mahangai", "mahngai", "mehengai", "mahagai", "kimat", "kimatein",
    "महंगाई", "मंहगाई", "महंगा", "महंगे", "कीमत", "कीमतें", "दाम", "भाव", "महागाई", "किंमत",
    "মূল্যবৃদ্ধি", "দাম", "দামে", "মূল্য",
]


def parse_gkg_date(series: pd.Series) -> pd.Series:
    """Return a string Series YYYYMMDDHHMMSS."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series.dt.strftime("%Y%m%d%H%M%S")
    return series.astype("int64").astype(str).str.zfill(14)


def parse_language(ti) -> str:
    if ti is None or (isinstance(ti, float) and np.isnan(ti)) or str(ti).strip() == "":
        return "en"
    m = re.search(r"srclc:([A-Za-z]{2,3})", str(ti))
    return m.group(1).lower() if m else "unknown"


def url_slug(url: str) -> str:
    p = urlparse(str(url))
    return unquote(p.path or "").lower()


def has_price_keyword(url: str, keywords) -> bool:
    slug = url_slug(url)
    tokens = [t for t in re.split(r"[^\wऀ-ॿঀ-৿]+", slug) if t]
    ks = set(keywords)
    return any(t in ks for t in tokens)


def pick_other_language(df: pd.DataFrame) -> str:
    counts = df["language"].value_counts()
    mar, ben = int(counts.get("mar", 0)), int(counts.get("ben", 0))
    if mar == 0 and ben == 0:
        raise SystemExit("Neither Marathi (mar) nor Bengali (ben) found in TranslationInfo; cannot pick the second vernacular language.")
    return "mar" if mar >= ben else "ben"


def assign_strata(df, baseline_col, econ_col, other_lang, keywords, doc_mask=None) -> pd.Series:
    base = df[baseline_col].astype(bool)
    econ = df[econ_col].astype(bool) | base  # flagged is treated as ECON
    lang = df["language"]
    slug = df["DocumentIdentifier"].map(lambda u: has_price_keyword(u, keywords))
    s = pd.Series(pd.NA, index=df.index, dtype="object")
    gen = ~lang.isin(["hin", other_lang])
    doc = doc_mask if doc_mask is not None else pd.Series(False, index=df.index)
    s[gen & base] = "flagged"
    s[gen & ~base & doc] = "doc_unflagged"
    s[gen & econ & ~base & ~doc] = "econ_unflagged"
    s[gen & ~econ & ~doc & slug] = "nonecon_slug"
    s[gen & ~econ & ~doc & ~slug] = "nonecon_noslug"
    for code, tag in (("hin", "hin"), (other_lang, "oth")):
        s[(lang == code) & base] = f"{tag}_flagged"
        s[(lang == code) & econ & ~base] = f"{tag}_econ_unflagged"
    return s


def draw_stratum(pop: pd.DataFrame, n: int, oversample: float, rng: np.random.Generator):
    """SRS inside two sub-strata (2015-18 vs other) with allocation tilted by `oversample`.

    Returns (sample_df with inclusion_prob_within, info dict).
    """
    if len(pop) == 0:
        return pop.assign(inclusion_prob_within=[]), {"N": 0, "n": 0, "shortfall": n}
    old = pop["year"].between(*OVERSAMPLE_YEARS)
    subs = {"y2015_18": pop[old], "later": pop[~old]}
    N_old, N_new = len(subs["y2015_18"]), len(subs["later"])
    if n >= len(pop):
        take = {"y2015_18": N_old, "later": N_new}
    else:
        denom = oversample * N_old + N_new
        n_old = int(round(n * oversample * N_old / denom)) if denom > 0 else 0
        n_old = max(n - N_new, min(n_old, N_old, n))
        n_old = max(0, n_old)
        take = {"y2015_18": n_old, "later": n - n_old}
        if take["later"] > N_new:  # cannot happen after the clamp, kept as a guard
            take["later"] = N_new
            take["y2015_18"] = n - N_new
    parts = []
    for name, sub in subs.items():
        k = take[name]
        if len(sub) == 0 or k <= 0:
            continue
        idx = rng.choice(len(sub), size=k, replace=False)
        chosen = sub.iloc[np.sort(idx)].copy()
        chosen["inclusion_prob_within"] = k / len(sub)
        parts.append(chosen)
    out = pd.concat(parts) if parts else pop.iloc[0:0].assign(inclusion_prob_within=[])
    return out, {"N": int(len(pop)), "n": int(len(out)), "shortfall": int(max(0, n - len(out))),
                 "take": {k: int(v) for k, v in take.items()}, "N_sub": {"y2015_18": int(N_old), "later": int(N_new)}}


def select_human(sample: pd.DataFrame, alloc: dict, rng: np.random.Generator, eligible_ids=None, human_langs=None):
    """Stratified human subsample; adds human_rank (random within stratum) and human_selected.

    eligible_ids: if given (retrieval log), only these rows are candidates (rank assigned among them).
    """
    sample = sample.copy()
    sample["human_rank"] = np.nan
    sample["human_selected"] = False
    shortfalls = {}
    for st, k in alloc.items():
        m = sample["stratum"] == st
        if eligible_ids is not None:
            m = m & sample["audit_id"].isin(eligible_ids)
        if human_langs is not None:
            m = m & sample["language"].isin(human_langs)
        idx = sample.index[m]
        order = rng.permutation(len(idx))
        ranks = np.empty(len(idx), dtype=int)
        ranks[order] = np.arange(1, len(idx) + 1)
        sample.loc[idx, "human_rank"] = ranks
        sample.loc[idx[ranks <= k], "human_selected"] = True
        if len(idx) < k:
            shortfalls[st] = int(k - len(idx))
    return sample, shortfalls


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="article-level parquet")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--mode", choices=["A", "B"], default="A")
    ap.add_argument("--modeb-days", type=int, default=None, help="Mode B: number of seeded window days for 2020+ (set from the pilot)")
    ap.add_argument("--window-days", default=None, help="optional file with one YYYYMMDD per line; rows outside are dropped")
    ap.add_argument("--baseline-col", default="flag_baseline")
    ap.add_argument("--econ-col", default="flag_econ")
    ap.add_argument("--oversample", type=float, default=1.5)
    ap.add_argument("--keywords-file", default=None)
    ap.add_argument("--doc-hits", default=None, help="csv/parquet of DOC keyword hits (DocumentIdentifier or GKGRECORDID); adds the doc_unflagged stratum (only if DOC passes)")
    ap.add_argument("--doc-target", type=int, default=60)
    ap.add_argument("--tranche", choices=["A", "B"], default=None, help="D34 Stage A / Stage B draw")
    ap.add_argument("--tranche-fraction-a", type=float, default=0.5)
    ap.add_argument("--human-languages", default="en,hin", help="languages the human coder reads (default English + Hindi only)")
    ap.add_argument("--retrieval-log", default=None, help="if given, human subsample is drawn only among articles with a successful retrieval")
    ap.add_argument("--manifest-out", default=None)
    ap.add_argument("--key-out", default=None)
    ap.add_argument("--sheet-out", default=None)
    ap.add_argument("--meta-out", default=None)
    ap.add_argument("--text-dir", default="data/raw/audit_texts")
    a = ap.parse_args(argv)

    sfx = f"_tranche{a.tranche}" if a.tranche else ""
    a.manifest_out = a.manifest_out or f"data/interim/audit/audit_manifest{sfx}.csv"
    a.key_out = a.key_out or f"data/interim/audit/private/audit_key{sfx}.csv"
    a.sheet_out = a.sheet_out or f"data/interim/audit/coder/coding_sheet{sfx}.csv"
    a.meta_out = a.meta_out or f"data/interim/audit/private/audit_sampling_meta{sfx}.json"
    human_langs = [x.strip() for x in a.human_languages.split(",") if x.strip()]
    keywords = DEFAULT_KEYWORDS
    if a.keywords_file:
        keywords = [l.strip().lower() for l in Path(a.keywords_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    oversample = a.oversample if a.mode == "A" else 1.0
    seed = a.seed + (1000 if a.tranche == "B" else 0)  # tranches use different, fixed seeds
    a.seed = seed

    df = pd.read_parquet(a.input)
    need = {"GKGRECORDID", "DATE", "DocumentIdentifier", "SourceCommonName", "TranslationInfo", a.baseline_col, a.econ_col}
    miss = need - set(df.columns)
    if miss:
        raise SystemExit(f"Input is missing required columns: {sorted(miss)}")
    df = df.dropna(subset=["DocumentIdentifier"]).drop_duplicates("DocumentIdentifier").reset_index(drop=True)
    df["gkg_date"] = parse_gkg_date(df["DATE"])
    df["window_day"] = df["gkg_date"].str[:8]
    df["year"] = df["gkg_date"].str[:4].astype(int)
    if a.window_days:
        wd = set(Path(a.window_days).read_text().split())
        df = df[df["window_day"].isin(wd)].reset_index(drop=True)
    df["language"] = df["TranslationInfo"].map(parse_language)
    other = pick_other_language(df)

    rng = np.random.default_rng(a.seed)
    day_factor_info = None
    if a.mode == "B":
        if not a.modeb_days:
            raise SystemExit("Mode B requires --modeb-days (set from the pilot, D16).")
        late_days = sorted(df.loc[df["year"] >= 2020, "window_day"].unique())
        K = min(a.modeb_days, len(late_days))
        chosen = set(np.random.default_rng(a.seed + 1).choice(late_days, size=K, replace=False)) if K else set()
        df = df[(df["year"] < 2020) | df["window_day"].isin(chosen)].reset_index(drop=True)
        day_factor = (len(late_days) / K) if K else float("nan")
        day_factor_info = {"D_2020plus_days": len(late_days), "K_chosen": K, "chosen_days": sorted(chosen), "weight_factor": day_factor}
    doc_mask = None
    if a.doc_hits:
        dh = pd.read_parquet(a.doc_hits) if a.doc_hits.endswith(".parquet") else pd.read_csv(a.doc_hits, dtype=str)
        col = "DocumentIdentifier" if "DocumentIdentifier" in dh.columns else ("GKGRECORDID" if "GKGRECORDID" in dh.columns else None)
        if col is None:
            raise SystemExit("--doc-hits needs a DocumentIdentifier or GKGRECORDID column")
        doc_mask = df[col].isin(set(dh[col].astype(str)))
    df["stratum"] = assign_strata(df, a.baseline_col, a.econ_col, other, keywords, doc_mask)
    pop = df[df["stratum"].notna()]

    targets = dict(TARGETS)
    if a.doc_hits:
        targets["doc_unflagged"] = a.doc_target
    targets = {k: tranche_split(v, a.tranche, a.tranche_fraction_a) for k, v in targets.items()}
    drawn, info = [], {}
    for st, n in targets.items():
        pool = pop[pop["stratum"] == st]
        smp, inf = draw_stratum(pool, n, oversample, rng)
        inf["target"] = n
        info[st] = inf
        drawn.append(smp)
    sample = pd.concat(drawn, ignore_index=True)
    sample["sampling_weight"] = 1.0 / sample["inclusion_prob_within"]
    if a.mode == "B" and day_factor_info and not np.isnan(day_factor_info["weight_factor"]):
        late = sample["year"] >= 2020
        sample.loc[late, "sampling_weight"] *= day_factor_info["weight_factor"]
    sample["inclusion_prob"] = 1.0 / sample["sampling_weight"]

    # audit ids: random order so the id does not reveal the stratum
    perm = np.random.default_rng(a.seed + 2).permutation(len(sample))
    sample = sample.iloc[perm].reset_index(drop=True)
    pref = f"T{a.tranche}" if a.tranche else "A"
    sample["audit_id"] = [f"{pref}{i + 1:04d}" for i in range(len(sample))]

    eligible = None
    if a.retrieval_log:
        lg = pd.read_csv(a.retrieval_log)
        eligible = set(lg.loc[lg["success"].astype(str).str.lower().isin(["true", "1"]), "audit_id"])
    alloc = {k: tranche_split(v, a.tranche, a.tranche_fraction_a) for k, v in human_allocation(human_langs, other).items()}
    sample, human_short = select_human(sample, alloc, np.random.default_rng(a.seed + 3), eligible, human_langs)

    # fetch order: human-selected first, then the rest, interleaved across strata proportionally
    sample["fetch_key"] = 0.0
    for st, g in sample.groupby("stratum"):
        h = g[g["human_selected"]].sort_values("human_rank")
        rest = g[~g["human_selected"]].copy()
        r = np.random.default_rng(a.seed + 4).permutation(len(rest))
        sample.loc[h.index, "fetch_key"] = (np.arange(len(h)) + 0.5) / max(len(h), 1)
        sample.loc[rest.index, "fetch_key"] = 1.0 + (np.argsort(r) + 0.5) / max(len(rest), 1)
    sample = sample.sort_values(["fetch_key", "audit_id"]).reset_index(drop=True)
    sample["fetch_rank"] = np.arange(1, len(sample) + 1)
    sample = sample.sort_values("audit_id").reset_index(drop=True)

    flag_cols = [c for c in df.columns if c.startswith("flag_")]
    sample["gdelt_flags"] = sample[flag_cols].astype(int).astype(str).apply(
        lambda r: ";".join(f"{c}={v}" for c, v in zip(flag_cols, r)), axis=1) if flag_cols else ""

    Path(a.manifest_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.key_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.sheet_out).parent.mkdir(parents=True, exist_ok=True)

    manifest = pd.DataFrame({
        "audit_id": sample["audit_id"], "url": sample["DocumentIdentifier"], "language": sample["language"],
        "gkg_date": sample["gkg_date"], "fetch_rank": sample["fetch_rank"], "human_selected": sample["human_selected"],
    })
    manifest.to_csv(a.manifest_out, index=False)
    key = pd.DataFrame({
        "audit_id": sample["audit_id"], "stratum": sample["stratum"], "gdelt_flags": sample["gdelt_flags"],
        "sampling_weight": sample["sampling_weight"], "window_day": sample["window_day"],
        "outlet": sample["SourceCommonName"], "gkg_record_id": sample["GKGRECORDID"], "gkg_date": sample["gkg_date"],
        "human_selected": sample["human_selected"], "human_rank": sample["human_rank"],
        "fetch_rank": sample["fetch_rank"], "inclusion_prob": sample["inclusion_prob"],
        "econ_row": (sample[a.econ_col].astype(bool) | sample[a.baseline_col].astype(bool)).astype(int),
        "tranche": a.tranche or "",
    })
    key.to_csv(a.key_out, index=False)
    hs = sample[sample["human_selected"]].sort_values("fetch_rank")
    # order for the coder: shuffled (seeded) so stratum blocks do not appear
    hs = hs.iloc[np.random.default_rng(a.seed + 5).permutation(len(hs))]
    sheet = pd.DataFrame({
        "audit_id": hs["audit_id"], "language": hs["language"], "url": hs["DocumentIdentifier"],
        "retrieval_mode": "", "text_file": [f"{a.text_dir}/{i}.txt" for i in hs["audit_id"]],
        "relevance": "", "direction": "", "cause_primary": "", "cause_secondary": "", "uncertain": "",
        "notes": "", "coder": "", "coded_at": "",
    })
    sheet.to_csv(a.sheet_out, index=False)

    meta = {
        "seed": a.seed, "mode": a.mode, "oversample_effective": oversample, "other_vernacular": other,
        "n_input_after_dedup": int(len(df)), "strata": info, "human_shortfalls": human_short,
        "human_n": int(sample["human_selected"].sum()),
        "human_hindi_n": int((sample["human_selected"] & (sample["language"] == "hin")).sum()),
        "modeb": day_factor_info, "keywords_n": len(keywords), "baseline_col": a.baseline_col, "econ_col": a.econ_col,
        "human_pool_conditional_on_retrieval": bool(eligible is not None), "human_languages": human_langs,
        "tranche": a.tranche, "doc_stratum": bool(a.doc_hits), "keywords_sha256": __import__("hashlib").sha256("\n".join(sorted(keywords)).encode("utf-8")).hexdigest(),
    }
    Path(a.meta_out).write_text(json.dumps(meta, indent=2, default=str))
    short = {k: v["shortfall"] for k, v in info.items() if v["shortfall"]}
    print(f"Sampled {len(sample)} articles; human subsample {meta['human_n']} (Hindi {meta['human_hindi_n']}).")
    if short:
        print("SHORTFALL (stratum smaller than target; not topped up):", short, file=sys.stderr)
    if human_short:
        print("HUMAN SHORTFALL:", human_short, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
