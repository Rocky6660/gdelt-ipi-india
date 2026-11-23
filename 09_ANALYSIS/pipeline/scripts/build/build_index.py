"""Build the GDELT inflation perception indices (design_final D2, D3, D9-D14; ledger rulings 23 Nov 2026).

Rewritten 23 Nov 2026: the earlier build_index.py was not in the project folder (user ruling: rewrite from design).
No outcome data are read here (D31/Gate 2): only GKG extraction output, the IESH fieldwork calendar (dates only)
and the frozen panel / theme lists.

Inputs (paths relative to --root)
  data/processed/bq_out/q2_{A,B}_<rung>_*/part-*.parquet  Q2 output: row types A (article), S (window-day aggregate),
                                                            D (non-window-day aggregate)
  data/processed/source_superset.csv                       Stage A/B source superset (Gate 1a)
  data/raw/gdelt_lookup/MASTER-GDELTDOMAINSBYCOUNTRY-MAY2018.TXT  GDELT domain-to-country file (D2)
  scripts/build/panel_review.csv                           hand review of ambiguous domains (ruling 23 Nov)
  scripts/build/flags.csv                                  D10 theme flags (regex on V1 theme codes)
  data/raw/iesh_rounds.csv                                 round, fieldwork_start (window calendar only)
  data/processed/bq_out/daycount_L2/                       global GKG daily record counts (D13 global rule)
  scripts/config.yaml                                      rung, grid, seeds, index parameters

Outputs (data/processed/index/)
  panel_outlets.csv          every superset domain with its panel decision and the rule that made it
  ipi_window.csv             one row per IESH round: ipi_primary (D11 window article share) + robustness rows
  ipi_window_outlet.csv      host x window shares (for E1/E2 and checks)
  ipi_monthly.csv            month, ipi_monthly (D11 monthly series), days_used, usable_d23, variants
  ipi_daily.csv              daily monthly-definition index on all sampled days (D17 placebos/episodes)
  cooccurrence_window.csv    D14 co-occurrence shares per window (labelled co-occurrence, never topics)
  cooccurrence_monthly.csv   D14 co-occurrence shares per month (grid days)
  theme_stability.csv        D9 flag presence by year
  build_report.md / .json    exclusions, cores, duplicate rates, reliability (D3), N table, notes
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bq_runner as bq  # noqa: E402  (grid, windows and config are taken from the extraction code itself)

SOUTH_ASIA_FOREIGN = {"Bangladesh", "Pakistan", "Nepal", "Sri Lanka", "Bhutan"}
INFL_FAMILY_FLAGS = ("infl_baseline", "infl_wb442", "infl_costofliving")  # D9 strict: >= 2 of these
DEFAULTS = dict(
    siblings_pooled=True,          # probe 2026-11-18: *.indiatimes.com siblings pooled in SourceCommonName
    core_presence_share=0.80,      # D11 balanced core: present in >= 80% of (valid) windows / months
    min_window_articles=10,        # outlet present in a window if >= 10 distinct articles on valid days
    min_day_articles=5,            # monthly: outlet-day enters the daily mean if >= 5 articles
    min_month_articles=10,         # monthly: outlet present in a month if >= 10 articles on valid grid days
    valid_window_share=0.60,       # D13
    global_rule=0.50, core_rule=0.30, outlet_rule=0.30,   # D13 thresholds vs 28-day medians
    median_halfwidth_days=14,      # 28-day centred window for the D13 medians
    min_median_obs=3,              # fewer sampled days than this in the 28-day span -> rule not applied
    usable_month_days=5,           # D4/D23: months with < 5 sampled valid days not used
    core2018_start="2018-01-01",   # D11 second core incl. vernacular outlets
)


# ----------------------------------------------------------------------------- helpers
def norm_host(h: pd.Series) -> pd.Series:
    return h.fillna("").str.lower().str.replace(r"^(www\d?|m|amp|mobile)\.", "", regex=True)


def norm_url(u: pd.Series) -> pd.Series:
    """Same normalisation as the SQL url_norm: drop query/fragment, scheme, leading www., trailing slashes."""
    s = u.fillna("").str.replace(r"[?#].*$", "", regex=True)
    return s.str.replace(r"^https?://(?:www\.)?|/+$", "", regex=True)


def centred_median(dates: pd.Series, values: pd.Series, hw: int, min_obs: int) -> np.ndarray:
    """Median of `values` over observations within +/- hw days of each date (including itself)."""
    d = pd.to_datetime(dates).to_numpy("datetime64[D]").astype(np.int64)
    v = values.to_numpy(float)
    order = np.argsort(d)
    ds, vs = d[order], v[order]
    lo = np.searchsorted(ds, ds - hw, "left")
    hi = np.searchsorted(ds, ds + hw - 1, "right")  # 28-day span: [d-14, d+13]
    med = np.array([np.median(vs[a:b]) if b - a >= min_obs else np.nan for a, b in zip(lo, hi)])
    out = np.empty_like(med)
    out[order] = med
    return out


def load_flags(path: Path) -> pd.DataFrame:
    f = pd.read_csv(path)
    if len(f) > 63:
        raise SystemExit("flags.csv: at most 63 flags (bitmask)")
    f["bit"] = np.arange(len(f), dtype=np.uint64)
    f["rx"] = f.regex.map(re.compile)
    return f


def token_masks(tokens: list, flags: pd.DataFrame) -> np.ndarray:
    m = np.zeros(len(tokens), dtype=np.uint64)
    for rx, bit in zip(flags.rx, flags.bit):
        hit = np.fromiter((bool(t) and rx.match(t) is not None for t in tokens), bool, len(tokens))
        m[hit] |= np.uint64(1) << bit
    return m


def theme_bitmask(themes: pa.Array, flags: pd.DataFrame, cache: dict) -> np.ndarray:
    """Per-row OR of the flag bits of each V1 theme token (vectorised)."""
    arr = pc.fill_null(themes, "")
    lists = pc.split_pattern(arr, ";")
    if isinstance(lists, pa.ChunkedArray):
        lists = lists.combine_chunks()
    offsets = lists.offsets.to_numpy()
    flat = lists.flatten()
    enc = pc.dictionary_encode(flat)
    toks = enc.dictionary.to_pylist()
    new = [t for t in toks if t not in cache]
    if new:
        for t, m in zip(new, token_masks(new, flags)):
            cache[t] = m
    dmask = np.array([cache[t] for t in toks], dtype=np.uint64)
    tm = dmask[enc.indices.to_numpy()]
    if len(tm) == 0:
        return np.zeros(len(offsets) - 1, dtype=np.uint64)
    return np.bitwise_or.reduceat(tm, offsets[:-1].astype(np.int64))


# ----------------------------------------------------------------------------- panel (D2 + ruling 23 Nov)
def build_panel(root: Path, superset: Path, lookup: Path, review: Path) -> pd.DataFrame:
    s = pd.read_csv(superset)
    s["domain"] = s.domain.str.lower().str.strip()
    lk = pd.read_csv(lookup, sep="\t", header=None, names=["domain", "fips", "country"], dtype=str)
    lk["domain"] = lk.domain.str.lower().str.strip()
    lk = lk.drop_duplicates("domain")
    rv = pd.read_csv(review)
    rv["domain"] = rv.domain.str.lower().str.strip()
    p = s.merge(lk[["domain", "country"]], on="domain", how="left")
    p["country"] = p.country.fillna("UNLISTED")
    p = p.merge(rv[["domain", "decision", "confidence", "reason"]], on="domain", how="left")
    rule, keep = [], []
    for r in p.itertuples():
        if isinstance(r.decision, str):
            rule.append(f"review:{r.confidence}"); keep.append(r.decision == "keep")
        elif "top20" in str(r.origin):
            rule.append("top20_seed"); keep.append(True)
        elif r.domain == "indiatimes.com" or r.domain.endswith(".indiatimes.com"):
            rule.append("indiatimes_sibling"); keep.append(True)
        elif r.country == "India":
            rule.append("lookup_india"); keep.append(True)
        elif r.domain.endswith(".in") and r.country in ("India", "UNLISTED"):
            rule.append("in_tld"); keep.append(True)
        elif r.country in SOUTH_ASIA_FOREIGN:
            rule.append("lookup_south_asia_foreign"); keep.append(False)
        else:
            rule.append("UNDECIDED"); keep.append(False)
    p["rule"], p["in_panel"] = rule, keep
    und = p[p.rule == "UNDECIDED"]
    if len(und):
        raise SystemExit(f"panel: {len(und)} domains have no rule (add them to panel_review.csv): "
                         f"{', '.join(und.domain.head(20))}")
    return p


# ----------------------------------------------------------------------------- per-chunk compaction (cached)
A_COLS = ["row_type", "pdate", "window_day", "source", "host", "src_lang", "document_identifier", "themes",
          "v2tone", "word_count", "is_econ", "is_infl", "is_price"]
AGG_COLS = ["row_type", "pdate", "window_day", "source", "host", "src_lang", "url_section", "n_articles",
            "n_distinct_urls", "n_econ", "n_econ_distinct", "n_infl", "n_infl_distinct", "n_price",
            "n_price_distinct", "words_all", "words_infl"]


def chunk_key(d: Path, flags_sha: str) -> str:
    man = (d / "manifest.json").read_bytes() if (d / "manifest.json").exists() else b""
    files = sorted(d.glob("part-*.parquet"))
    stat = "|".join(f"{f.name}:{f.stat().st_size}:{int(f.stat().st_mtime)}" for f in files)
    return hashlib.sha256(man + stat.encode() + flags_sha.encode()).hexdigest()[:16]


def compact_chunk(d: Path, flags: pd.DataFrame, tok_cache: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    files = sorted(d.glob("part-*.parquet"))
    if not files:
        return pd.DataFrame(), pd.DataFrame()
    t = pa.concat_tables([pq.read_table(f, columns=A_COLS + [c for c in AGG_COLS if c not in A_COLS])
                          for f in files])
    rt = t.column("row_type")
    a = t.filter(pc.equal(rt, "A"))
    g = t.filter(pc.is_in(rt, pa.array(["S", "D"]))).select(AGG_COLS).to_pandas()
    mask = theme_bitmask(a.column("themes"), flags, tok_cache)
    ad = a.drop_columns(["themes"]).to_pandas()
    ad["fmask"] = mask
    ad["url_norm"] = norm_url(ad.document_identifier)
    ad = ad.drop(columns=["document_identifier"])
    for c in ("is_econ", "is_infl", "is_price", "window_day"):
        ad[c] = ad[c].fillna(False).astype(bool)
    ad["host"] = norm_host(ad.host)
    # wire-copy key (D11 row v): same day, word count and tone vector
    ad["tone_key"] = ad.v2tone.fillna("").str.split(",").str[:6].str.join(",")
    ad = ad.drop(columns=["v2tone"])
    g["host"] = norm_host(g.host)
    g["window_day"] = g.window_day.fillna(False).astype(bool)
    return ad, g


def load_all(root: Path, rung: str, flags: pd.DataFrame, cache_dir: Path, log) -> tuple[pd.DataFrame, pd.DataFrame]:
    flags_sha = hashlib.sha256(pd.util.hash_pandas_object(flags[["flag", "regex"]]).values.tobytes()).hexdigest()
    dirs = sorted(Path(p) for p in glob.glob(str(root / f"data/processed/bq_out/q2_[AB]_{rung}_*")) if Path(p).is_dir())
    cache_dir.mkdir(parents=True, exist_ok=True)
    tok_cache: dict = {}
    A, G = [], []
    for i, d in enumerate(dirs):
        k = chunk_key(d, flags_sha)
        fa, fg = cache_dir / f"{d.name}__{k}__A.parquet", cache_dir / f"{d.name}__{k}__G.parquet"
        if fa.exists() and fg.exists():
            ad, g = pd.read_parquet(fa), pd.read_parquet(fg)
        else:
            for old in cache_dir.glob(f"{d.name}__*"):
                old.unlink()
            ad, g = compact_chunk(d, flags, tok_cache)
            ad.to_parquet(fa, index=False); g.to_parquet(fg, index=False)
        ad["chunk"] = d.name; g["chunk"] = d.name
        A.append(ad); G.append(g)
        if (i + 1) % 25 == 0:
            log(f"  loaded {i + 1}/{len(dirs)} chunks")
    A = pd.concat(A, ignore_index=True)
    G = pd.concat(G, ignore_index=True)
    A["pdate"] = pd.to_datetime(A.pdate).dt.date
    G["pdate"] = pd.to_datetime(G.pdate).dt.date
    A["fmask"] = A["fmask"].astype(np.uint64)
    return A, G, len(dirs)


def has(flags_col: pd.Series, bit: int) -> np.ndarray:
    return (flags_col.to_numpy(np.uint64) >> np.uint64(bit)) & np.uint64(1) == 1


# ----------------------------------------------------------------------------- D13 validity
def day_validity(G: pd.DataFrame, panel_sources: set, daycount: pd.DataFrame | None, P: dict) -> pd.DataFrame:
    """Day-level exclusions on all sampled days: global count rule and panel ('core') volume rule."""
    g = G[G.source.isin(panel_sources)]
    vol = g.groupby("pdate").n_articles.sum().rename("panel_volume").reset_index()
    vol["panel_med"] = centred_median(vol.pdate, vol.panel_volume, P["median_halfwidth_days"], P["min_median_obs"])
    vol["core_ok"] = ~(vol.panel_volume < P["core_rule"] * vol.panel_med)
    if daycount is not None:
        dc = daycount.copy()
        dc["pdate"] = pd.to_datetime(dc.pdate).dt.date
        dc["global_med"] = centred_median(dc.pdate, dc.n_records, P["median_halfwidth_days"], P["min_median_obs"])
        vol = vol.merge(dc[["pdate", "n_records", "global_med"]], on="pdate", how="left")
        vol["global_ok"] = ~(vol.n_records < P["global_rule"] * vol.global_med)
        vol["global_available"] = vol.n_records.notna()
    else:
        vol["global_ok"], vol["global_available"] = True, False
    vol["valid_day"] = vol.core_ok & vol.global_ok
    return vol


def outlet_day_ok(df: pd.DataFrame, key: str, n: str, P: dict) -> pd.Series:
    """D13 outlet-day rule: volume >= 30% of the outlet's own 28-day median (over its sampled days)."""
    ok = pd.Series(True, index=df.index)
    for _, sub in df.groupby(key, sort=False):
        med = centred_median(sub.pdate, sub[n], P["median_halfwidth_days"], P["min_median_obs"])
        ok.loc[sub.index] = ~(sub[n].to_numpy(float) < P["outlet_rule"] * med)
    return ok


# ----------------------------------------------------------------------------- window series (D11)
def window_calendar(cfg: dict, rung: str, rounds_csv: Path) -> pd.DataFrame:
    rounds = bq.read_rounds(rounds_csv)
    L = int(cfg["rungs"][rung]["window_days"])
    start = max(bq.D(cfg["rungs"][rung]["start"]), bq.D(cfg["table_first_partition"]))
    end = bq.D(cfg["sample_end"])
    rows = []
    for rnd, fs, _ in rounds:
        days = [fs - dt.timedelta(days=k) for k in range(L, 0, -1)]
        days_in = [d for d in days if start <= d <= end]
        if not days_in:
            continue
        rows += [{"round": rnd, "fieldwork_start": fs, "pdate": d, "day_in_window": i + 1}
                 for i, d in enumerate(days) if start <= d <= end]
    return pd.DataFrame(rows)


def equal_weight_index(share: pd.DataFrame, core: list, col: str, by: str) -> pd.Series:
    s = share[share.outlet.isin(core)]
    return s.groupby(by)[col].mean()


def build_window(A, G, cal, dayv, panel_sources, flags, P, report):
    S = G[(G.row_type == "S") & G.source.isin(panel_sources)].copy()
    S = S.merge(cal[["pdate", "round"]], on="pdate", how="inner")
    host_day = S.groupby(["round", "pdate", "host"], as_index=False)[
        ["n_articles", "n_distinct_urls", "n_econ_distinct", "n_infl_distinct", "n_price_distinct",
         "n_infl", "words_all", "words_infl"]].sum()
    host_day = host_day.merge(dayv[["pdate", "valid_day"]], on="pdate", how="left")
    host_day["valid_day"] = host_day.valid_day.fillna(False).astype(bool)
    host_day["outlet_ok"] = outlet_day_ok(host_day, "host", "n_distinct_urls", P)
    host_day["use"] = host_day.valid_day & host_day.outlet_ok

    # window validity: >= 60% valid days
    cv = cal.merge(dayv[["pdate", "valid_day"]], on="pdate", how="left").fillna({"valid_day": False})
    cv["valid_day"] = cv.valid_day.astype(bool)
    L = cal.groupby("round").day_in_window.max()
    wv = cv.groupby("round").agg(n_days=("pdate", "size"), n_valid_days=("valid_day", "sum"))
    wv["window_days_nominal"] = L
    wv["valid_window"] = wv.n_valid_days >= P["valid_window_share"] * wv.window_days_nominal

    # A-row numerators for variants: distinct URLs per host-day on window days
    Aw = A[A.window_day & A.source.isin(panel_sources)].merge(cal[["pdate", "round"]], on="pdate", how="inner")
    bit = dict(zip(flags.flag, flags.bit.astype(int)))
    fam = np.zeros(len(Aw), dtype=int)
    for f in INFL_FAMILY_FLAGS:
        fam += has(Aw["fmask"], bit[f]).astype(int)
    Aw["strict"] = fam >= 2
    Aw["wb442"] = has(Aw["fmask"], bit["infl_wb442"])
    wire = Aw[Aw.is_infl & Aw.word_count.notna() & (Aw.tone_key != "")]
    nh = wire.groupby(["pdate", "word_count", "tone_key"]).host.transform("nunique")
    wire_ids = set(wire.index[nh > 1])
    Aw["infl_nowire"] = Aw.is_infl & ~Aw.index.isin(wire_ids)
    report["wire_copy_share_of_infl_rows"] = float(len(wire_ids) / max(1, int(Aw.is_infl.sum())))
    keys = ["round", "pdate", "host"]
    parts = []
    for col, name in (("strict", "n_strict"), ("wb442", "n_wb442"), ("infl_nowire", "n_infl_nowire")):
        parts.append(Aw[Aw[col]].drop_duplicates(keys + ["url_norm"]).groupby(keys).size().rename(name))
    num = pd.concat(parts, axis=1).reset_index()
    host_day = host_day.merge(num, on=["round", "pdate", "host"], how="left").fillna(
        {"n_strict": 0, "n_wb442": 0, "n_infl_nowire": 0})

    # cross-day duplicate rate (R5) and dedup bound (D1)
    a_dup = Aw.sort_values("pdate").drop_duplicates(["round", "host", "pdate", "url_norm"])
    xd = a_dup.duplicated(["round", "host", "url_norm"])
    report["cross_day_dup_rate_A_rows"] = float(xd.mean()) if len(xd) else None
    report["cross_day_dup_rate_infl_rows"] = float(xd[a_dup.is_infl].mean()) if a_dup.is_infl.any() else None

    u = host_day[host_day.use]
    hw = u.groupby(["round", "host"], as_index=False)[
        ["n_articles", "n_distinct_urls", "n_econ_distinct", "n_infl_distinct", "n_price_distinct", "n_infl",
         "words_all", "words_infl", "n_strict", "n_wb442", "n_infl_nowire"]].sum()
    hw = hw.merge(wv[["valid_window"]], left_on="round", right_index=True, how="left")
    hw["present"] = hw.n_distinct_urls >= P["min_window_articles"]
    hw = hw[hw.present & hw.valid_window].copy()
    hw = hw.rename(columns={"host": "outlet"})
    den = hw.n_distinct_urls
    hw["a_share"] = hw.n_infl_distinct / den
    hw["a_strict"] = hw.n_strict / den
    hw["a_wb442"] = hw.n_wb442 / den
    hw["a_price"] = hw.n_price_distinct / den
    hw["a_nowire"] = hw.n_infl_nowire / den
    hw["a_econ"] = np.where(hw.n_econ_distinct > 0, hw.n_infl_distinct / hw.n_econ_distinct.where(hw.n_econ_distinct > 0), np.nan)
    hw["a_words"] = np.where(hw.words_all > 0, hw.words_infl.fillna(0) / hw.words_all.where(hw.words_all > 0), np.nan)
    hw["a_nodedup"] = hw.n_infl / hw.n_articles

    # paywall/teaser rule (D11): outlets whose yearly mean words/article changes by > 2x year on year
    # are excluded from the word-share row (median words/article is not available from aggregates).
    rd = cal.groupby("round").fieldwork_start.first()
    hw["year"] = hw["round"].map(rd).map(lambda d: d.year)
    yw = hw.groupby(["outlet", "year"]).apply(lambda x: x.words_all.sum() / max(1, x.n_articles.sum()),
                                              include_groups=False).rename("wpa").reset_index()
    yw["ratio"] = yw.groupby("outlet").wpa.transform(lambda s: (s / s.shift(1)))
    teaser = set(yw[(yw.ratio > 2) | (yw.ratio < 0.5)].outlet)
    report["word_share_excluded_outlets_teaser_break"] = sorted(teaser)

    valid_rounds = wv.index[wv.valid_window]
    nvw = len(valid_rounds)
    pres = hw.groupby("outlet")["round"].nunique()
    core = sorted(pres[pres >= P["core_presence_share"] * nvw].index)
    c18_start = bq.D(P["core2018_start"])
    r18 = [r for r in valid_rounds if rd[r] >= c18_start]
    pres18 = hw[hw["round"].isin(r18)].groupby("outlet")["round"].nunique()
    core18 = sorted(pres18[pres18 >= P["core_presence_share"] * len(r18)].index)

    out = wv.copy()
    out["window_fieldwork_start"] = rd  # not "fieldwork_start": phase1 merges that from iesh_rounds.csv
    out["window_start"] = cal.groupby("round").pdate.min()
    out["window_end"] = cal.groupby("round").pdate.max()
    hc = hw[hw.outlet.isin(core)]
    out["n_core"] = len(core)
    out["n_core_present"] = hc.groupby("round").outlet.nunique()
    out["n_articles_core"] = hc.groupby("round").n_distinct_urls.sum()
    out["n_infl_core"] = hc.groupby("round").n_infl_distinct.sum()
    out["ipi_primary"] = equal_weight_index(hw, core, "a_share", "round")
    out["row_word_share"] = equal_weight_index(hw[~hw.outlet.isin(teaser)], core, "a_words", "round")
    out["row_pooled_ratio"] = hc.groupby("round").n_infl_distinct.sum() / hc.groupby("round").n_distinct_urls.sum()
    out["row_share_among_econ"] = equal_weight_index(hw, core, "a_econ", "round")
    out["row_wire_filter"] = equal_weight_index(hw, core, "a_nowire", "round")
    out["variant_strict"] = equal_weight_index(hw, core, "a_strict", "round")
    out["variant_price_family"] = equal_weight_index(hw, core, "a_price", "round")
    out["variant_wb442"] = equal_weight_index(hw, core, "a_wb442", "round")
    out["ipi_core2018_with_vernacular"] = equal_weight_index(hw[hw["round"].isin(r18)], core18, "a_share", "round")
    out["check_no_dedup"] = equal_weight_index(hw, core, "a_nodedup", "round")
    # E2 inputs (not robustness rows; names avoid the row_/variant_ prefixes phase1 z-scores)
    lang = (S.assign(outlet=S.host).groupby(["outlet", "src_lang"]).n_articles.sum().reset_index()
            .sort_values("n_articles").drop_duplicates("outlet", keep="last").set_index("outlet").src_lang)
    hw["lang"] = hw.outlet.map(lang).fillna("native")
    out["ipi_eng"] = equal_weight_index(hw[hw.lang == "native"], core18 or core, "a_share", "round")
    out["ipi_ver"] = equal_weight_index(hw[hw.lang != "native"], core18 or core, "a_share", "round")
    for c in [c for c in out.columns if c.startswith(("ipi_", "row_", "variant_", "check_"))]:
        out.loc[~out.valid_window, c] = np.nan
    out = out.reset_index().rename(columns={"index": "round"})

    report["window"] = dict(
        rounds_with_window_days=int(len(wv)), valid_windows=int(nvw),
        core_outlets=core, core_size=len(core), core2018_outlets=core18, core2018_size=len(core18),
        core_language_counts=hw[hw.outlet.isin(core)].drop_duplicates("outlet").lang.value_counts().to_dict(),
        core2018_language_counts=hw[hw.outlet.isin(core18)].drop_duplicates("outlet").lang.value_counts().to_dict(),
        outlet_days_excluded_share=float(1 - host_day.outlet_ok.mean()),
        days_excluded=int((~cv.drop_duplicates("pdate").valid_day).sum()),
        corr_dedup_vs_nodedup=float(out[["ipi_primary", "check_no_dedup"]].corr().iloc[0, 1])
        if out.ipi_primary.notna().sum() > 2 else None,
        mean_share_dedup=float(out.ipi_primary.mean()), mean_share_nodedup=float(out.check_no_dedup.mean()),
    )

    # D3 split-half reliability (odd vs even days), nested lengths allowed by the rung
    rel = {}
    Lnom = int(L.max())
    for length in [x for x in P["nested_window_lengths"] if x <= Lnom]:
        hdw = host_day[host_day.use].merge(cal[["pdate", "round", "day_in_window"]], on=["pdate", "round"])
        hdw = hdw[hdw.day_in_window > Lnom - length]
        halves = []
        for parity in (0, 1):
            h = hdw[hdw.day_in_window % 2 == parity].groupby(["round", "host"], as_index=False)[
                ["n_distinct_urls", "n_infl_distinct"]].sum()
            h = h[(h.n_distinct_urls >= P["min_window_articles"] / 2) & h.host.isin(core) & h["round"].isin(valid_rounds)]
            h["a"] = h.n_infl_distinct / h.n_distinct_urls
            halves.append(h.groupby("round").a.mean())
        j = pd.concat(halves, axis=1).dropna()
        r = float(j.corr().iloc[0, 1]) if len(j) > 3 else np.nan
        rel[length] = dict(N=int(len(j)), split_half_r=r, spearman_brown=float(2 * r / (1 + r)) if r == r else None)
    report["window_reliability_D3"] = rel

    return out, hw, core, host_day


# ----------------------------------------------------------------------------- monthly series (D11)
def build_monthly(A, G, cfg, rung, dayv, panel_sources, cal, flags, P, report):
    spec = cfg["rungs"][rung]
    start = max(bq.D(spec["start"]), bq.D(cfg["table_first_partition"]))
    grid = set(bq.grid_days(start, bq.D(cfg["sample_end"]), int(spec["step"]), int(cfg["seed"]), bq.D(cfg["grid_epoch"])))
    always = bq.always_days(cfg)
    g = G[G.source.isin(panel_sources)]
    od = g.groupby(["pdate", "source", "src_lang"], as_index=False)[["n_articles", "n_infl", "n_econ", "n_price"]].sum()
    od["outlet"] = od.source + "|" + od.src_lang
    # D9 variant numerators for the monthly series (counts, no dedup, same definition as n_infl)
    bit = dict(zip(flags.flag, flags.bit.astype(int)))
    Ap = A[A.source.isin(panel_sources)][["pdate", "source", "src_lang", "fmask"]].copy()
    fam = sum(has(Ap["fmask"], bit[f]).astype(int) for f in INFL_FAMILY_FLAGS)
    Ap["v_strict"], Ap["v_wb442"] = fam >= 2, has(Ap["fmask"], bit["infl_wb442"])
    vc = Ap.groupby(["pdate", "source", "src_lang"])[["v_strict", "v_wb442"]].sum().reset_index()
    od = od.merge(vc.rename(columns={"v_strict": "n_strict", "v_wb442": "n_wb442"}),
                  on=["pdate", "source", "src_lang"], how="left").fillna({"n_strict": 0, "n_wb442": 0})
    od = od.merge(dayv[["pdate", "valid_day"]], on="pdate", how="left").fillna({"valid_day": False})
    od["valid_day"] = od.valid_day.astype(bool)
    od["outlet_ok"] = outlet_day_ok(od, "outlet", "n_articles", P)
    od["on_grid"] = od.pdate.isin(grid)
    od["window_day"] = od.pdate.isin(set(cal.pdate))
    od["always"] = od.pdate.isin(always)
    od["month"] = pd.PeriodIndex(pd.to_datetime(od.pdate), freq="M").astype(str)
    od["share"] = od.n_infl / od.n_articles
    od["use"] = od.valid_day & od.outlet_ok & (od.n_articles >= P["min_day_articles"])

    gd = od[od.on_grid & od.use]
    pm = gd.groupby(["outlet", "month"]).n_articles.sum().reset_index()
    pm = pm[pm.n_articles >= P["min_month_articles"]]
    months_valid = gd.month.nunique()
    pres = pm.groupby("outlet").month.nunique()
    core = sorted(pres[pres >= P["core_presence_share"] * months_valid].index)
    m18 = sorted(m for m in gd.month.unique() if m >= P["core2018_start"][:7])
    pres18 = pm[pm.month.isin(m18)].groupby("outlet").month.nunique()
    core18 = sorted(pres18[pres18 >= P["core_presence_share"] * len(m18)].index)

    def daily(sub, core_list):
        s = sub[sub.outlet.isin(core_list)]
        return s.groupby("pdate").agg(ipi=("share", "mean"), n_outlets=("outlet", "nunique"),
                                      n_articles=("n_articles", "sum"), n_infl=("n_infl", "sum"))

    # all sampled days (daily file: placebos/episodes), monthly-definition index
    alld = od[od.use]
    d_all = daily(alld, core).reset_index()
    flags_day = od.drop_duplicates("pdate")[["pdate", "on_grid", "window_day", "always"]]
    d_all = d_all.merge(flags_day, on="pdate", how="left").merge(dayv[["pdate", "valid_day"]], on="pdate", how="right")
    d_all = d_all.sort_values("pdate")

    dg = daily(gd, core).reset_index()
    dg["month"] = pd.PeriodIndex(pd.to_datetime(dg.pdate), freq="M").astype(str)
    mon = dg.groupby("month").agg(ipi_monthly=("ipi", "mean"), days_used=("pdate", "nunique"),
                                  n_articles_core=("n_articles", "sum"), n_infl_core=("n_infl", "sum"))
    d18 = daily(gd[gd.month.isin(m18)], core18).reset_index()
    d18["month"] = pd.PeriodIndex(pd.to_datetime(d18.pdate), freq="M").astype(str)
    mon["ipi_monthly_core2018"] = d18.groupby("month").ipi.mean()
    eng = [o for o in (core18 or core) if o.endswith("|native")]
    ver = [o for o in (core18 or core) if not o.endswith("|native")]
    for name, lst in (("ipi_monthly_eng", eng), ("ipi_monthly_ver", ver)):
        x = daily(gd[gd.month.isin(m18)] if core18 else gd, lst).reset_index()
        x["month"] = pd.PeriodIndex(pd.to_datetime(x.pdate), freq="M").astype(str)
        mon[name] = x.groupby("month").ipi.mean() if len(x) else np.nan
    # D9 variants (same core, grid days, outlet-day rules); used by the D9/D17 switch chain, not robustness rows
    for name, num in (("ipi_monthly_variant_price_family", "n_price"), ("ipi_monthly_variant_strict", "n_strict"),
                      ("ipi_monthly_variant_wb442", "n_wb442")):
        x = gd.assign(share=gd[num] / gd.n_articles)
        x = daily(x, core).reset_index()
        x["month"] = pd.PeriodIndex(pd.to_datetime(x.pdate), freq="M").astype(str)
        mon[name] = x.groupby("month").ipi.mean()
    mon["usable_d23"] = mon.days_used >= P["usable_month_days"]
    allm = pd.period_range(min(od.month), max(od.month), freq="M").astype(str)
    mon = mon.reindex(allm)
    mon.index.name = "month"
    mon["days_used"] = mon.days_used.fillna(0).astype(int)
    mon["usable_d23"] = mon.usable_d23.fillna(False).astype(bool)
    mon = mon.reset_index()

    # window vs monthly definition on window days (D11 robustness line)
    wd = daily(od[od.window_day & od.use], core).reset_index().merge(cal[["pdate", "round"]], on="pdate")
    win_mdef = wd.groupby("round").ipi.mean().rename("ipi_window_monthly_def")

    report["monthly"] = dict(core_outlets=core, core_size=len(core), core2018_size=len(core18),
                             core2018_eng=len(eng), core2018_ver=len(ver),
                             grid_days_sampled=int(od[od.on_grid].pdate.nunique()),
                             grid_days_used=int(gd.pdate.nunique()),
                             months=int(len(mon)), months_usable_d23=int(mon.usable_d23.sum()),
                             outlet_days_excluded_share=float(1 - od.outlet_ok.mean()))
    return mon, d_all, win_mdef, core, od


# ----------------------------------------------------------------------------- D14 co-occurrence
def cooccurrence(A_sub: pd.DataFrame, flags: pd.DataFrame, by: str, dedup: bool) -> pd.DataFrame:
    x = A_sub[A_sub.is_infl]
    if dedup:
        x = x.drop_duplicates(["pdate", "host", "url_norm"])
    rows = {}
    n = x.groupby(by).size()
    for f, b, fam in zip(flags.flag, flags.bit.astype(int), flags.family):
        if fam == "inflation" and f == "infl_baseline":
            continue
        rows[f"cooc_{f}"] = x.assign(h=has(x["fmask"], b)).groupby(by).h.mean()
    fams = {}
    for fam, sub in flags.groupby("family"):
        bits = np.uint64(0)
        for b in sub.bit.astype(int):
            bits |= np.uint64(1) << np.uint64(b)
        fams[f"cooc_family_{fam}"] = x.assign(h=(x["fmask"].to_numpy(np.uint64) & bits) > 0).groupby(by).h.mean()
    out = pd.concat({**rows, **fams}, axis=1)
    out.insert(0, "n_infl_articles", n)
    return out.reset_index()


def theme_stability(A: pd.DataFrame, flags: pd.DataFrame) -> pd.DataFrame:
    yr = pd.to_datetime(A.pdate).dt.year
    rows = []
    for f, b in zip(flags.flag, flags.bit.astype(int)):
        h = pd.Series(has(A["fmask"], b)).groupby(yr.values).sum()
        rows.append({"flag": f, **{str(k): int(v) for k, v in h.items()}})
    t = pd.DataFrame(rows)
    yrs = [c for c in t.columns if c != "flag"]
    t["present_every_year"] = (t[yrs] > 0).all(axis=1)
    return t


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--rung", default=None)
    ap.add_argument("--allow-partial", action="store_true",
                    help="build even if the Stage B plan is not complete (outputs marked partial)")
    a = ap.parse_args()
    root = a.root.resolve()
    cfg = bq.load_config(root / "scripts/config.yaml")
    rung = a.rung or cfg["rung"]
    P = {**DEFAULTS, **(cfg.get("index") or {}), "nested_window_lengths": cfg.get("nested_window_lengths", [7, 14])}
    out = root / "data/processed/index"
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rung": rung,
                    "params": {k: v for k, v in P.items()}}
    log = lambda m: print(m, flush=True)  # noqa: E731

    # completeness of extraction
    led = bq.Ledger(root / cfg["paths"]["ledger"])
    ok = led.ok_labels()
    missing = []
    for st in ("A", "B"):
        pf = root / cfg["paths"]["plan_dir"] / f"plan_{rung}_{st}.json"
        if pf.exists():
            plan = json.loads(pf.read_text())
            labels = [c["label"] for c in plan.get("chunks", [])]
            missing += [l for l in labels if l not in ok]
    report["missing_chunks"] = missing
    report["partial"] = bool(missing)
    if missing and not a.allow_partial:
        raise SystemExit(f"{len(missing)} planned chunks not RUN_OK yet (e.g. {missing[:3]}); use --allow-partial")

    panel = build_panel(root, root / cfg["paths"]["source_superset"],
                        root / "data/raw/gdelt_lookup/MASTER-GDELTDOMAINSBYCOUNTRY-MAY2018.TXT",
                        root / "scripts/build/panel_review.csv")
    panel.to_csv(out / "panel_outlets.csv", index=False)
    panel_sources = set(panel[panel.in_panel].domain)
    report["panel"] = dict(superset=int(len(panel)), in_panel=int(panel.in_panel.sum()),
                           by_rule=panel.groupby(["rule", "in_panel"]).size().rename("n").reset_index()
                           .to_dict("records"))
    log(f"panel: {len(panel_sources)} of {len(panel)} superset domains")

    flags = load_flags(root / "scripts/build/flags.csv")
    A, G, nchunks = load_all(root, rung, flags, out / "cache", log)
    report["chunks_loaded"] = nchunks
    dup = G.groupby(["row_type", "pdate", "source", "host", "src_lang", "url_section"], dropna=False).chunk.nunique()
    report["aggregate_keys_in_more_than_one_chunk"] = int((dup > 1).sum())
    if (dup > 1).any():
        raise SystemExit("same aggregate key appears in more than one chunk: partitions overlap")
    vol_all = G.groupby(G.source.isin(panel_sources)).n_articles.sum()
    report["article_share_in_panel"] = float(vol_all.get(True, 0) / vol_all.sum())
    log(f"loaded {nchunks} chunks: {len(A):,} article rows, {len(G):,} aggregate rows")

    dcf = glob.glob(str(root / "data/processed/bq_out/daycount_L2/*.parquet"))
    daycount = pd.concat(pd.read_parquet(f) for f in dcf) if dcf else None
    dayv = day_validity(G, panel_sources, daycount, P)
    report["days"] = dict(sampled=int(len(dayv)), invalid=int((~dayv.valid_day).sum()),
                          invalid_core_rule=int((~dayv.core_ok).sum()), invalid_global_rule=int((~dayv.global_ok).sum()),
                          global_count_available=int(dayv.global_available.sum()),
                          invalid_dates=[str(d) for d in dayv.loc[~dayv.valid_day, "pdate"]])

    cal = window_calendar(cfg, rung, root / cfg["paths"]["iesh_rounds"])
    win, hw, core_w, host_day = build_window(A, G, cal, dayv, panel_sources, flags, P, report)
    mon, daily, win_mdef, core_m, od = build_monthly(A, G, cfg, rung, dayv, panel_sources, cal, flags, P, report)
    win = win.merge(win_mdef, left_on="round", right_index=True, how="left")
    report["window"]["corr_window_vs_monthly_definition"] = (
        float(win[["ipi_primary", "ipi_window_monthly_def"]].corr().iloc[0, 1]) if win.ipi_primary.notna().sum() > 2 else None)

    # D14 co-occurrence (core outlets only)
    Aw = A[A.window_day & A.host.isin(core_w) & A.source.isin(panel_sources)].merge(cal[["pdate", "round"]], on="pdate")
    Aw = Aw[Aw["round"].isin(win.loc[win.valid_window, "round"])]
    co_w = cooccurrence(Aw, flags, "round", dedup=True)
    grid_core = od[od.on_grid & od.use & od.outlet.isin(core_m)][["pdate", "source", "src_lang"]]
    Am = A.merge(grid_core, on=["pdate", "source", "src_lang"], how="inner")
    Am["month"] = pd.PeriodIndex(pd.to_datetime(Am.pdate), freq="M").astype(str)
    co_m = cooccurrence(Am, flags, "month", dedup=False)
    stab = theme_stability(A[A.source.isin(panel_sources)], flags)
    report["flags_not_present_every_year"] = stab.loc[~stab.present_every_year, "flag"].tolist()
    report["notes"] = [
        "Outlet weights omega: equal weights over the balanced core (D11 'fixed omega'); pooled ratio is row (ii).",
        "Window dedup is day-level (R5): numerator and denominator both from day-level distinct URLs; "
        "cross-day duplicate rates reported above.",
        "Row (i) 75th-percentile word cap: not computable (per-article word counts exist only for flagged/ECON "
        "articles, not for the denominator). Not reported.",
        "Row (iv) readership-weighted: no readership data (D2 optional). Not reported.",
        "Row (v) wire-copy filter: inflation articles whose (day, word count, first 6 V2Tone fields) appear in more "
        "than one host are removed from the numerator; denominator unchanged.",
        "Placebo flag 'sports': no sports theme code occurs among the extracted (ECON/price) article rows; only "
        "'election' is available as a co-occurrence placebo.",
        "Monthly outlet key = SourceCommonName x source language, no dedup, grid days only (D11).",
    ]

    win.to_csv(out / "ipi_window.csv", index=False)
    hw.to_csv(out / "ipi_window_outlet.csv", index=False)
    mon.to_csv(out / "ipi_monthly.csv", index=False)
    daily.to_csv(out / "ipi_daily.csv", index=False)
    co_w.to_csv(out / "cooccurrence_window.csv", index=False)
    co_m.to_csv(out / "cooccurrence_monthly.csv", index=False)
    stab.to_csv(out / "theme_stability.csv", index=False)

    # N table (D3) — calendar/mode only, no outcomes
    rounds = pd.read_csv(root / cfg["paths"]["iesh_rounds"])
    nt = win.merge(rounds[["round", "mode", "fs_rule"]], on="round", how="left")
    report["N_table"] = dict(rounds_with_window=int(len(nt)), valid_windows=int(nt.valid_window.sum()),
                             valid_by_mode=nt[nt.valid_window]["mode"].fillna("not_stated").value_counts().to_dict(),
                             valid_by_fs_rule=nt[nt.valid_window].fs_rule.fillna("").value_counts().to_dict())
    (out / "build_report.json").write_text(json.dumps(report, indent=1, default=str))
    md = ["# build_index report", "", f"Built {report['built_at']} (rung {rung}); partial: {report['partial']}",
          f"Panel: {report['panel']['in_panel']} of {report['panel']['superset']} domains; "
          f"article share in panel {report['article_share_in_panel']:.3f}",
          f"Days: {report['days']['sampled']} sampled, {report['days']['invalid']} invalid "
          f"(core rule {report['days']['invalid_core_rule']}, global rule {report['days']['invalid_global_rule']}; "
          f"global counts available for {report['days']['global_count_available']} days)", "",
          "## Window series", json.dumps({k: v for k, v in report["window"].items()
                                          if k not in ("core_outlets", "core2018_outlets")}, indent=1, default=str),
          "", "## D3 split-half reliability", json.dumps(report["window_reliability_D3"], indent=1, default=str),
          f"Cross-day duplicate rate (A rows): {report.get('cross_day_dup_rate_A_rows')}; "
          f"inflation rows: {report.get('cross_day_dup_rate_infl_rows')}; wire-copy share of inflation rows: "
          f"{report.get('wire_copy_share_of_infl_rows')}",
          "", "## Monthly series", json.dumps({k: v for k, v in report["monthly"].items() if k != "core_outlets"}, indent=1),
          "", "## N table (D3)", json.dumps(report["N_table"], indent=1),
          "", f"Flags not present every year (D9): {report['flags_not_present_every_year']}",
          "", "## Notes", *[f"- {n}" for n in report["notes"]]]
    (out / "build_report.md").write_text("\n".join(md), encoding="utf-8")
    log("\n".join(md[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
