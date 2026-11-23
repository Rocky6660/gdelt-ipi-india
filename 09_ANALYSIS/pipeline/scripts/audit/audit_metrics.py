#!/usr/bin/env python3
"""Audit metrics and gate report (D9, D15, D16, D25, D29).

Inputs (all produced by the other audit scripts; nothing is simulated here):
  --key       private key (audit_id, stratum, gdelt_flags, sampling_weight, window_day, ...)
  --manifest  audit_manifest.csv (audit_id, url, language)
  --human     filled coder sheet (relevance, direction, cause_primary, ...)  [optional]
  --llm-a/--llm-b  llm_codes_A.csv / llm_codes_B.csv                       [optional]
  --log       logs/audit_retrieval_log.csv (for retrieval mode)           [optional]

Definitions
  * Truth source: LLM coder A (--primary-coder) unless human-vs-LLM kappa on relevance < 0.7, then
    the human codes replace the LLM codes for the estimates (D15). If that kappa cannot be
    computed the source is 'undetermined' and the estimate gates are NOT_EVALUABLE.
  * Weights: design weights from the key, post-stratified within stratum x period cells (2015-18 vs
    2019+, the link-rot split used by the sampler) to each cell's full sampled weight over the
    coded articles. Un-retrieved or uncoded articles are not imputed; they reweight the rest of
    their own cell (assumption: missing at random within the cell). A cell with sampled but no coded
    articles makes the dependent estimates NaN unless --collapse-empty-cells is set (then the stratum
    is pooled over periods and the report says so). The bootstrap resamples within the same cells.
    The coverage table gives the retrieval rate and coding rate for every cell.
  * Variants: best-F2 candidates are ONLY the explicit D9 list given by --variants or --config (price
    family, World Bank price-stability, strict). Other flag columns are never considered.
  * Human truth: when relevance kappa < 0.7 the human codes are the truth, for the human-eligible
    languages only (--human-languages, default en,hin). Weights are rebuilt over those rows and the
    report labels the scope (English + Hindi), because other languages have no human codes.
  * Slug-based codes (D16 Mode B route, --slug-a) are reported separately, never mixed into the
    full-text estimates.
  * Frames: 'gating' = ECON strata (flagged, econ_unflagged, hin_*, oth_*) plus nonecon_slug;
    'econ' = ECON rows only. nonecon_noslug is never in a frame: it gives an upper bound on the
    miss rate (exact Clopper-Pearson CI) and a recall floor.
  * Precision = weighted share of flagged articles that are relevant. Recall = weighted share of
    relevant articles that are flagged. F2 = 5PR/(4P+R). CIs: stratified bootstrap (cluster by
    window_day in Mode B), percentile 95%.
  * Kappa: Cohen's kappa on articles coded by both sources, unweighted, bootstrap over articles.
    Direction and cause are compared only where both sources coded relevance = Y.
  * Gates use point estimates against the pre-set thresholds; intervals are reported alongside.
  * D29 compares vernacular (hin + other focal strata) with English recall within the ECON frame
    (like-for-like, because vernacular has no slug stratum). That reading of "within 0.15" is an
    interpretation; the gating-frame English recall is reported too.
  * Missing values are never filled with assumptions: a cell without data is NaN with a reason.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import (CAUSES, DIRECTION, RELEVANCE, INTERNATIONAL_CAUSES, clean_code,  # noqa: E402
                          clopper_pearson, derive_international, f_beta)

GENERAL = ("flagged", "econ_unflagged", "nonecon_slug", "nonecon_noslug", "doc_unflagged")
ECON_STRATA_GEN = ("flagged", "econ_unflagged")
VERN = ("hin_flagged", "hin_econ_unflagged", "oth_flagged", "oth_econ_unflagged")
SCREENED_NONECON = ("nonecon_slug", "doc_unflagged")  # screened non-ECON strata that belong to the gating frame
# Frames are row-level: econ = rows with econ_row == 1 (ECON strata, plus ECON members of doc_unflagged);
# gating = econ rows + SCREENED_NONECON strata. nonecon_noslug is never in a frame (bound only).
D9_FORBIDDEN = re.compile(r"sport|election|placebo|econ$|international", re.I)
FLAGGED_STRATA = ("flagged", "hin_flagged", "oth_flagged")
GROUP_STRATA = {  # strata that can contain each group (for the coverage requirement)
    "all": None,
    "en": GENERAL,
    "hin": ("hin_flagged", "hin_econ_unflagged"),
    "oth": ("oth_flagged", "oth_econ_unflagged"),
    "vernacular_focal": VERN,
}
SENTINEL = float("nan")


# ----------------------------------------------------------------------------- data assembly
def parse_flags(s) -> dict:
    out = {}
    for part in str(s if isinstance(s, str) else "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            try:
                out[k.strip()] = int(v)
            except ValueError:
                pass
    return out


def slug_informative(url: str, min_words: int = 3) -> bool:
    """Heuristic: a slug is informative if it has >= min_words word tokens of >= 3 letters (not numeric IDs)."""
    path = unquote(urlparse(str(url)).path).lower()
    toks = [t for t in re.split(r"[^\w]+", path) if t and not t.isdigit() and len(t) >= 3
            and t not in {"news", "article", "story", "html", "amp", "www", "index", "articleshow", "cms"}]
    toks = [t for t in toks if not re.search(r"\d{4,}", t)]
    return len(toks) >= min_words


def _load_codes(df: pd.DataFrame, tag: str) -> pd.DataFrame:
    """Clean a code table into columns rel_/dir_/cp_/cs_/unc_/intl_ with <tag> suffix. Invalid -> missing."""
    d = df.copy()
    rel = d["relevance"].map(lambda v: clean_code(v, RELEVANCE))
    dr = d["direction"].map(lambda v: clean_code(v, DIRECTION, allow_empty=True))
    cp = d["cause_primary"].map(lambda v: clean_code(v, CAUSES, allow_empty=True))
    cs = d["cause_secondary"].map(lambda v: clean_code(v, CAUSES, allow_empty=True)) if "cause_secondary" in d else cp * 0
    y = rel == "Y"
    out = pd.DataFrame({"audit_id": d["audit_id"].astype(str)})
    out[f"rel_{tag}"] = rel
    out[f"dir_{tag}"] = np.where(y & dr.notna() & (dr != ""), dr, None)
    out[f"cp_{tag}"] = np.where(y & cp.notna() & (cp != ""), cp, None)
    out[f"cs_{tag}"] = np.where(y & cs.notna() & (cs != ""), cs, None)
    out[f"intl_{tag}"] = [derive_international(r, c) for r, c in zip(out[f"rel_{tag}"], out[f"cp_{tag}"])]
    return out.drop_duplicates("audit_id", keep="last")


def build_frame(key, manifest, human=None, llm_a=None, llm_b=None, log=None, slug=None) -> pd.DataFrame:
    k = key.copy()
    k["audit_id"] = k["audit_id"].astype(str)
    fl = pd.DataFrame([parse_flags(s) for s in k["gdelt_flags"]], index=k.index).fillna(-1).astype(int)
    k = pd.concat([k, fl], axis=1)
    m = manifest[["audit_id", "language", "url"]].copy()
    m["audit_id"] = m["audit_id"].astype(str)
    d = k.merge(m, on="audit_id", how="left")
    d["sampling_weight"] = d["sampling_weight"].astype(float)
    d["retrieval_mode"] = ""
    if log is not None and len(log):
        ok = log[log["success"].astype(str).str.lower().isin(["true", "1"])].drop_duplicates("audit_id", keep="last")
        d["retrieval_mode"] = d["audit_id"].map(ok.set_index("audit_id")["mode"]).fillna("")
    for tag, tab in (("H", human), ("A", llm_a), ("B", llm_b), ("S", slug)):
        if tab is None or len(tab) == 0:
            for c in ("rel", "dir", "cp", "cs", "unc", "intl"):
                d[f"{c}_{tag}"] = None
            continue
        d = d.merge(_load_codes(tab, tag), on="audit_id", how="left")
    yr = d["window_day"].astype(str).str[:4].astype(int)
    d["period"] = np.where(yr.between(2015, 2018), "old", "late")
    d["cell"] = d["stratum"] + "|" + d["period"]
    if "econ_row" in d.columns:
        d["econ_row"] = d["econ_row"].astype(float).fillna(0).astype(int)
    else:
        d["econ_row"] = d["stratum"].isin(["flagged", "econ_unflagged", "hin_flagged", "hin_econ_unflagged", "oth_flagged", "oth_econ_unflagged"]).astype(int)
    d["lang_group"] = np.select(
        [d["stratum"].str.startswith("hin_"), d["stratum"].str.startswith("oth_"), d["language"] == "en"],
        ["hin", "oth", "en"], default="other_nonfocal")
    return d


# ----------------------------------------------------------------------------- weights and bootstrap
def check_variants(variants, baseline, columns):
    """Candidate set for best-F2 = the explicit D9 list only. Refuses undeclared, missing or non-D9 flags."""
    out = [baseline]
    for v in variants or []:
        if v == baseline:
            continue
        if not v.startswith("flag_"):
            raise ValueError(f"variant {v!r} must be a flag_* column")
        if D9_FORBIDDEN.search(v):
            raise ValueError(f"variant {v!r} is not a D9 classifier variant (placebo / international / ECON markers are refused)")
        if v not in columns:
            raise ValueError(f"declared variant {v!r} is not in the key's gdelt_flags")
        out.append(v)
    if baseline not in columns:
        raise ValueError(f"baseline {baseline!r} is not in the key's gdelt_flags")
    return out


class Cells:
    """Evaluates precision / recall / F2 cells on numpy arrays (point estimate and bootstraps).

    Weights are post-stratified within stratum x period cells: w_i = sw_i * W_c / sum_{coded in c} sw."""

    def __init__(self, d: pd.DataFrame, relcol: str, variants: list[str], cell_all: list[str], Wc: dict, groups: dict,
                 req_strata: dict, empty_cells: list[str]):
        self.d = d.reset_index(drop=True)
        self.cells_all = list(cell_all)
        cidx = {c: i for i, c in enumerate(self.cells_all)}
        self.s = self.d["cell"].map(cidx).to_numpy()
        self.sw = self.d["sampling_weight"].to_numpy(float)
        self.Wc = np.array([Wc[c] for c in self.cells_all], float)
        self.rel = (self.d[relcol] == "Y").to_numpy()
        self.flags = {v: (self.d[v] == 1).to_numpy() for v in variants}
        econ = (self.d["econ_row"] == 1).to_numpy()
        self.frames = {"econ": econ, "gating": econ | self.d["stratum"].isin(SCREENED_NONECON).to_numpy()}
        self.groups = groups
        self.variants = variants
        self.req_strata = req_strata  # frame -> set of strata that must be represented
        self.empty_cells = empty_cells
        self.present = set(self.d["stratum"])

    def _w(self, idx):
        s = self.s[idx]
        tot = np.bincount(s, weights=self.sw[idx], minlength=len(self.cells_all))
        with np.errstate(divide="ignore", invalid="ignore"):
            return self.sw[idx] * self.Wc[s] / tot[s]

    def eval(self, idx=None) -> dict:
        if idx is None:
            idx = np.arange(len(self.d))
        w = self._w(idx)
        rel = self.rel[idx]
        out = {}
        for fr, fmask in self.frames.items():
            fm = fmask[idx]
            for gname, gmask in self.groups.items():
                gm = gmask[idx] & fm
                for v in self.variants:
                    fl = self.flags[v][idx]
                    tp = float(np.sum(w[gm & rel & fl]))
                    fp_tot = float(np.sum(w[gm & fl]))
                    rl = float(np.sum(w[gm & rel]))
                    p = tp / fp_tot if fp_tot > 0 else SENTINEL
                    r = tp / rl if rl > 0 else SENTINEL
                    out[(v, fr, gname, "precision")] = p
                    out[(v, fr, gname, "recall")] = r
                    out[(v, fr, gname, "f2")] = f_beta(p, r)
                out[("__tot__", fr, gname, "rel_total")] = float(np.sum(w[gm & rel]))
        return out

    def missing_reason(self, frame: str, group: str):
        if group.startswith("mode="):
            return ""
        need = GROUP_STRATA.get(group, None)
        req = set(self.req_strata[frame])
        if need is not None:
            req &= set(need)
        absent = sorted(x for x in req if x not in self.present)
        empty = sorted(c for c in self.empty_cells if c.split("|")[0] in req)
        msg = []
        if absent:
            msg.append(f"no coded articles in strata: {','.join(absent)}")
        if empty:
            msg.append(f"sampled cells with no coded articles (not imputed): {','.join(empty)}")
        return "; ".join(msg)


class Resampler:
    """Resamples clusters (single rows, or window days in Mode B) with replacement within each stratum."""

    def __init__(self, strata_codes: np.ndarray, clusters: np.ndarray):
        self.by_s = []
        for s in np.unique(strata_codes):
            rows = np.where(strata_codes == s)[0]
            _, inv = np.unique(clusters[rows], return_inverse=True)
            self.by_s.append([rows[inv == j] for j in range(inv.max() + 1)])

    def draw(self, rng):
        parts = []
        for cl in self.by_s:
            pick = rng.integers(0, len(cl), len(cl))
            parts.append(np.concatenate([cl[j] for j in pick]))
        return np.concatenate(parts)


def make_groups(d: pd.DataFrame) -> dict:
    g = {"all": np.ones(len(d), bool), "en": (d["lang_group"] == "en").to_numpy(),
         "hin": (d["lang_group"] == "hin").to_numpy(), "oth": (d["lang_group"] == "oth").to_numpy(),
         "vernacular_focal": d["lang_group"].isin(["hin", "oth"]).to_numpy()}
    for m in sorted(set(d["retrieval_mode"]) - {""}):
        g[f"mode={m}"] = (d["retrieval_mode"] == m).to_numpy()
    return g


def estimate_prf(frame: pd.DataFrame, truth_col: str, variants, B, seed, cluster_by_day, eligible=None, collapse_empty=False):
    """frame: all sampled rows (key joined with codes). eligible: boolean mask of rows in scope (e.g. human languages).

    Cell totals W_c come from ALL eligible sampled rows, not only coded ones."""
    fr = frame if eligible is None else frame[eligible]
    fr = fr.copy()
    coded = fr[truth_col].notna()
    if not coded.any():
        return None, None
    notes = []
    if collapse_empty:
        for st, g in fr.groupby("stratum"):
            cc = g.groupby("cell")[truth_col].apply(lambda x: x.notna().any())
            if (~cc).any() and cc.any():
                fr.loc[g.index, "cell"] = st
                notes.append(f"stratum {st} pooled over periods (an empty cell)")
    Wc = fr.groupby("cell")["sampling_weight"].sum().to_dict()
    empty_cells = sorted(c for c in Wc if not fr.loc[(fr["cell"] == c) & coded, "cell"].any())
    d = fr[coded].copy()
    econ_mask = fr["econ_row"] == 1
    req = {"econ": set(fr.loc[econ_mask, "stratum"]),
           "gating": set(fr.loc[econ_mask | fr["stratum"].isin(SCREENED_NONECON), "stratum"])}
    cells = Cells(d, truth_col, variants, sorted(Wc), Wc, make_groups(d), req, empty_cells)
    cells.notes = notes
    point = cells.eval()
    clusters = (cells.d["window_day"].astype(str).to_numpy() if cluster_by_day else np.arange(len(cells.d)).astype(str))
    rs = Resampler(cells.s, clusters)  # resamples within stratum x period cells
    rng = np.random.default_rng(seed)
    reps = {k: [] for k in point}
    for _ in range(B):
        idx = rs.draw(rng)
        for k, v in cells.eval(idx).items():
            reps[k].append(v)
    ci = {}
    for k, v in reps.items():
        a_ = np.array(v, float)
        ok = a_[~np.isnan(a_)]
        ci[k] = (float(np.percentile(ok, 2.5)), float(np.percentile(ok, 97.5)), len(ok) / len(a_)) if len(ok) >= max(20, 0.5 * len(a_)) else (SENTINEL, SENTINEL, len(ok) / len(a_) if len(a_) else 0)
    return (cells, point), (ci, reps)


# ----------------------------------------------------------------------------- kappa
def kappa_np(a: np.ndarray, b: np.ndarray, k: int) -> float:
    n = len(a)
    if n == 0:
        return SENTINEL
    cm = np.bincount(a * k + b, minlength=k * k).reshape(k, k)
    po = np.trace(cm) / n
    pe = float(np.sum(cm.sum(1) * cm.sum(0))) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else SENTINEL


def kappa_ci(x: list, y: list, B: int, rng) -> dict:
    n = len(x)
    if n == 0:
        return {"n": 0, "kappa": SENTINEL, "lo": SENTINEL, "hi": SENTINEL, "reason": "no articles coded by both"}
    cats = sorted(set(x) | set(y), key=str)
    ix = {c: i for i, c in enumerate(cats)}
    a = np.array([ix[v] for v in x])
    b = np.array([ix[v] for v in y])
    k = len(cats)
    pt = kappa_np(a, b, k)
    out = {"n": n, "kappa": pt, "lo": SENTINEL, "hi": SENTINEL, "reason": ""}
    if math.isnan(pt):
        out["reason"] = "kappa undefined (no variation in codes)"
        return out
    if n < 10:
        out["reason"] = "n<10: interval not computed"
        return out
    vals = []
    for _ in range(B):
        j = rng.integers(0, n, n)
        v = kappa_np(a[j], b[j], k)
        if not math.isnan(v):
            vals.append(v)
    if len(vals) >= 0.5 * B:
        out["lo"], out["hi"] = float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))
    else:
        out["reason"] = "bootstrap undefined in most resamples"
    return out


def kappa_table(frame, src1, src2, B, rng, dims=("relevance", "direction", "cause_primary", "international_imported")):
    colmap = {"relevance": "rel", "direction": "dir", "cause_primary": "cp", "international_imported": "intl"}
    groups = {"all": frame.index == frame.index}
    for g in sorted(frame["language"].dropna().unique()):
        groups[f"language={g}"] = (frame["language"] == g).to_numpy()
    for m in sorted(set(frame["retrieval_mode"]) - {""}):
        groups[f"mode={m}"] = (frame["retrieval_mode"] == m).to_numpy()
    rows = []
    for gname, gm in groups.items():
        sub = frame[np.asarray(gm)]
        for dim in dims:
            c = colmap[dim]
            x, y = sub[f"{c}_{src1}"], sub[f"{c}_{src2}"]
            ok = x.notna() & y.notna()
            if dim != "relevance":
                ok &= (sub[f"rel_{src1}"] == "Y") & (sub[f"rel_{src2}"] == "Y")
            res = kappa_ci(list(x[ok]), list(y[ok]), B, rng)
            rows.append({"pair": f"{src1}-{src2}", "group": gname, "variable": dim, **res})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- gates
def status(cond, evaluable=True):
    if not evaluable:
        return "NOT_EVALUABLE"
    return "PASS" if cond else "FAIL"


def run(key, manifest, human, llm_a, llm_b, log, mode="A", baseline="flag_baseline", variants=None,
        primary="A", B=1000, seed=20261116, human_langs=("en", "hin"), slug=None, collapse_empty=False, no_human=False):
    """variants: explicit list of D9 variant flag columns (e.g. price-family, WB price stability, strict).
    If None only the baseline is evaluated (no best-F2 search). Other flag_* columns are never candidates."""
    frame = build_frame(key, manifest, human, llm_a, llm_b, log, slug)
    rng = np.random.default_rng(seed)
    variants = check_variants(variants, baseline, frame.columns)
    report = {"mode": mode, "primary_coder": primary, "baseline": baseline, "variants": variants, "gates": {}, "notes": [],
              "human_languages": list(human_langs), "collapse_empty_cells": collapse_empty,
              "assumption": "non-response is treated as missing at random within stratum x period cells (2015-18 / 2019+)"}

    # coverage per stratum x period cell (no imputation: shows how many were not retrieved / coded)
    have_log = log is not None and len(log) > 0
    cov = frame.groupby(["stratum", "period"]).agg(sampled=("audit_id", "size"),
                                                   retrieved=("retrieval_mode", lambda x: int((x != "").sum())),
                                                   llm_A=("rel_A", lambda x: int(x.notna().sum())),
                                                   llm_B=("rel_B", lambda x: int(x.notna().sum())),
                                                   human=("rel_H", lambda x: int(x.notna().sum()))).reset_index()
    cov["retrieval_rate"] = (cov["retrieved"] / cov["sampled"]).round(3) if have_log else float("nan")
    cov["llm_A_rate"] = (cov["llm_A"] / cov["sampled"]).round(3)
    report["coverage"] = cov.to_dict("records")

    # ---- kappas
    kt_hl = kappa_table(frame, "H", primary, B, rng)
    other = "B" if primary == "A" else "A"
    kt_hl_other = kappa_table(frame, "H", other, B, rng)
    kt_ll = kappa_table(frame, "A", "B", B, rng)
    kappas = pd.concat([kt_hl, kt_hl_other, kt_ll], ignore_index=True)

    def kget(tab, var, grp="all"):
        r = tab[(tab["variable"] == var) & (tab["group"] == grp)]
        return r.iloc[0] if len(r) else None

    k_rel, k_dir, k_cp = (kget(kt_hl, v) for v in ("relevance", "direction", "cause_primary"))
    kv = lambda r: SENTINEL if r is None else r["kappa"]  # noqa: E731

    # ---- truth source (D15 rule 1)
    if no_human and frame["rel_H"].notna().sum() == 0:
        # User ruling (ledger 17 Nov / handoff): NO human coding; two independent LLM passes; the paper states that
        # there is no human validation. Truth = primary LLM coder; LLM-LLM kappa is reported as reliability and is
        # used for the direction/cause rule; B-as-truth and A=B-agreement-as-truth are robustness rows.
        truth_src = primary
        k_rel, k_dir, k_cp = (kget(kt_ll, v) for v in ("relevance", "direction", "cause_primary"))
        report["gates"]["D15_relevance_kappa"] = {
            "kappa": kv(k_rel), "ci": [None if k_rel is None else k_rel["lo"], None if k_rel is None else k_rel["hi"]],
            "n": None if k_rel is None else int(k_rel["n"]), "truth_source": truth_src,
            "reading": "NO HUMAN CODING (user ruling): LLM coder %s is the truth source; kappa shown is LLM A vs LLM B "
                       "(reliability only, not validation)" % primary,
            "status": "NOT_APPLICABLE (no human coding by ruling)"}
        a_, b_ = frame["rel_A"], frame["rel_B"]
        frame["rel_AB"] = np.where(a_.notna() & b_.notna() & (a_ == b_), a_, None)
        extra_sources = {other, "AB"}
    elif math.isnan(kv(k_rel)):
        truth_src, truth_reason = "undetermined", "human-vs-LLM relevance kappa not computable (no overlapping human and LLM codes)"
    elif kv(k_rel) < 0.7:
        truth_src, truth_reason = "H", f"kappa relevance {kv(k_rel):.3f} < 0.7: human codes replace LLM codes"
    else:
        truth_src, truth_reason = primary, f"kappa relevance {kv(k_rel):.3f} >= 0.7: LLM codes used"
    if not (no_human and frame["rel_H"].notna().sum() == 0):
        extra_sources = set()
        report["gates"]["D15_relevance_kappa"] = {"kappa": kv(k_rel), "ci": [None if r is None else r["lo"] for r in [k_rel]] + [None if k_rel is None else k_rel["hi"]],
                                                  "n": None if k_rel is None else int(k_rel["n"]), "truth_source": truth_src, "reading": truth_reason,
                                                  "status": "NOT_EVALUABLE" if truth_src == "undetermined" else ("FAIL->human codes used" if truth_src == "H" else "PASS")}
    for name, r in (("D15_direction_kappa", k_dir), ("D15_cause_kappa", k_cp)):
        v = kv(r)
        report["gates"][name] = {"kappa": v, "ci": [None if r is None else r["lo"], None if r is None else r["hi"]],
                                 "n": None if r is None else int(r["n"]),
                                 "status": status(v >= 0.6, not math.isnan(v)),
                                 "reading": "usable in E3/E4 claims" if (not math.isnan(v) and v >= 0.6) else "NOT used in E3/E4 claims" if not math.isnan(v) else "cannot be evaluated"}

    # ---- precision / recall under each truth source
    prf_tables = []
    results = {}
    elig_H = frame["language"].isin(list(human_langs))
    scope = {}
    for src in sorted(({truth_src, primary, "H", "S"} | extra_sources) - {"undetermined"}):
        col = f"rel_{src}"
        if col not in frame or frame[col].notna().sum() == 0:
            continue
        elig = elig_H if src == "H" else None
        scope[src] = (f"languages {','.join(human_langs)} only (human-covered)" if src == "H" else "all sampled languages")
        got, ci = estimate_prf(frame, col, variants, B, seed + 7, cluster_by_day=(mode == "B"), eligible=elig, collapse_empty=collapse_empty)
        if got is None:
            continue
        cells, point = got
        cidict, reps = ci
        results[src] = (cells, point, cidict, reps)
        for (v, fr, g, st), val in point.items():
            if v == "__tot__":
                continue
            lo, hi, frac = cidict[(v, fr, g, st)]
            reason = cells.missing_reason(fr, g)
            prf_tables.append({"truth_source": src, "variant": v, "frame": fr, "group": g, "metric": st,
                               "estimate": val if not reason else SENTINEL, "ci_lo": lo if not reason else SENTINEL,
                               "ci_hi": hi if not reason else SENTINEL, "valid_boot_share": frac, "missing_reason": reason,
                               "n_coded": int(cells.groups[g][cells.frames[fr]].sum()), "scope": scope[src]})
    prf = pd.DataFrame(prf_tables)

    def cell(src, v, fr, g, st):
        r = prf[(prf.truth_source == src) & (prf.variant == v) & (prf.frame == fr) & (prf.group == g) & (prf.metric == st)]
        return r.iloc[0] if len(r) else None

    # ---- D15 precision/recall gate on the selected truth source
    if truth_src in results:
        P = cell(truth_src, baseline, "gating", "all", "precision")
        R = cell(truth_src, baseline, "gating", "all", "recall")
        pv, rv = (SENTINEL if x is None else x["estimate"] for x in (P, R))
        ev = not (math.isnan(pv) or math.isnan(rv))
        g = {"precision": pv, "precision_ci": [None if P is None else P["ci_lo"], None if P is None else P["ci_hi"]],
             "gating_recall": rv, "gating_recall_ci": [None if R is None else R["ci_lo"], None if R is None else R["ci_hi"]],
             "truth_source": truth_src, "scope": scope[truth_src], "status": status(ev and pv >= 0.5 and rv >= 0.6, ev)}
        if scope[truth_src] != "all sampled languages":
            report["notes"].append(f"Estimates use human codes, so they cover {scope[truth_src]}; other languages have no human codes and are not extrapolated.")
        # best F2 among variants
        f2s = {v: (cell(truth_src, v, "gating", "all", "f2")["estimate"] if cell(truth_src, v, "gating", "all", "f2") is not None else SENTINEL) for v in variants}
        valid = {v: x for v, x in f2s.items() if not math.isnan(x)}
        g["f2_by_variant"] = f2s
        g["best_f2_variant"] = max(valid, key=valid.get) if valid else None
        if g["status"] == "PASS":
            g["action"] = "baseline stays"
        elif g["status"] == "FAIL" and g["best_f2_variant"] and g["best_f2_variant"] != baseline:
            g["action"] = f"switch to best-F2 variant: {g['best_f2_variant']}"
        elif g["status"] == "FAIL" and g["best_f2_variant"] == baseline:
            g["action"] = "baseline is itself the best-F2 declared variant: D9's next step applies (strict flag, then 'audited, not externally validated')"
        elif g["status"] == "FAIL":
            g["action"] = "no declared variant has a computable F2: D9's next step applies"
        else:
            g["action"] = "no decision (not evaluable)"
        if len(variants) == 1:
            g["action"] += " [only the baseline was declared; pass --variants with the D9 list for a best-F2 search]"
        # upper bound from the unscreened non-ECON stratum
        fscope = frame if truth_src != "H" else frame[elig_H]
        ns = fscope[fscope["stratum"] == "nonecon_noslug"]
        codes = ns[f"rel_{truth_src}"].dropna()
        if len(codes):
            k_, n_ = int((codes == "Y").sum()), len(codes)
            lo, hi = clopper_pearson(k_, n_)
            N_ns = float(ns["sampling_weight"].sum())
            cells, point, _, _ = results[truth_src]
            rel_tot = point[("__tot__", "gating", "all", "rel_total")]
            tp = (R["estimate"] * rel_tot) if R is not None and not math.isnan(R["estimate"]) else SENTINEL
            floor = tp / (rel_tot + N_ns * hi) if not math.isnan(tp) else SENTINEL
            g["unscreened_nonecon"] = {"relevant": k_, "n": n_, "share": k_ / n_, "exact_ci": [lo, hi], "N_population_stratum": N_ns,
                                       "recall_floor_incl_unscreened_upper": floor,
                                       "reading": "upper bound on the missed-relevant share outside ECON and price-keyword slugs; not an estimate"}
        else:
            g["unscreened_nonecon"] = {"reading": "no coded articles in nonecon_noslug; bound not available"}
        report["gates"]["D15_precision_recall"] = g
    else:
        report["gates"]["D15_precision_recall"] = {"status": "NOT_EVALUABLE", "reading": "no usable truth codes"}

    # ---- D29 vernacular recall gate (ECON frame, like-for-like)
    d29 = {"status": "NOT_EVALUABLE", "reading": "no usable truth codes"}
    if truth_src in results:
        cells, point, cidict, reps = results[truth_src]
        rv_ = cell(truth_src, baseline, "econ", "vernacular_focal", "recall")
        re_ = cell(truth_src, baseline, "econ", "en", "recall")
        rg_ = cell(truth_src, baseline, "gating", "en", "recall")
        vv, ev_ = (SENTINEL if x is None else x["estimate"] for x in (rv_, re_))
        diff_ci = (SENTINEL, SENTINEL)
        kv_, ke_ = (baseline, "econ", "vernacular_focal", "recall"), (baseline, "econ", "en", "recall")
        if kv_ in reps and ke_ in reps:
            dd = np.array(reps[kv_], float) - np.array(reps[ke_], float)
            dd = dd[~np.isnan(dd)]
            if len(dd) >= 20:
                diff_ci = (float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5)))
        vern_urls = frame[frame["lang_group"].isin(["hin", "oth"])]
        unin = float(np.mean([not slug_informative(u) for u in vern_urls["url"]])) if len(vern_urls) else SENTINEL
        ng_coded = int(((vern_urls["retrieval_mode"] == "ngrams_approx") & vern_urls[f"rel_{truth_src}"].notna()).sum()) if len(vern_urls) else 0
        d29 = {"vernacular_recall_econ": vv, "vernacular_recall_ci": [None if rv_ is None else rv_["ci_lo"], None if rv_ is None else rv_["ci_hi"]],
               "english_recall_econ": ev_, "english_recall_ci": [None if re_ is None else re_["ci_lo"], None if re_ is None else re_["ci_hi"]],
               "english_recall_gating_frame": None if rg_ is None else rg_["estimate"],
               "difference": vv - ev_ if not (math.isnan(vv) or math.isnan(ev_)) else SENTINEL, "difference_ci": list(diff_ci),
               "vernacular_uninformative_slug_share": unin, "vernacular_ngrams_text_coded": ng_coded, "scope": scope[truth_src]}
        if mode == "B" and not math.isnan(unin) and unin > 0.5 and ng_coded == 0:
            d29.update(status="FAIL", reading="not estimable by D16 vernacular rule (Mode B, >50% uninformative slugs, no NGrams text): E2 reported as a measurement result")
        elif math.isnan(d29["difference"]):
            d29.update(status="NOT_EVALUABLE", reading="vernacular or English recall missing (no coded relevant articles or strata); not filled")
        else:
            ok = abs(d29["difference"]) <= 0.15
            d29.update(status=status(ok), reading="vernacular recall within 0.15 of English recall (point estimates)" if ok
                       else "gap > 0.15: E2 reported as a measurement result (differential theme recall under machine translation)")
    report["gates"]["D29_vernacular_recall"] = d29

    # ---- D25 kappa gate
    d25 = {"status": "NOT_EVALUABLE", "reading": "no usable truth codes or no flag_international in key"}
    if truth_src != "undetermined" and "flag_international" in frame.columns:
        sub = frame[frame["stratum"].isin(FLAGGED_STRATA) & (frame["flag_international"] >= 0)]
        x = sub[f"intl_{truth_src}"]
        ok = x.notna()
        xs, ys = list(sub.loc[ok, "flag_international"].astype(int)), list(x[ok].astype(int))
        res = kappa_ci(xs, ys, B, np.random.default_rng(seed + 11))
        kcp = kv(k_cp)
        gen = sub[sub["stratum"] == "flagged"]
        okg = gen[f"intl_{truth_src}"].notna()
        resg = kappa_ci(list(gen.loc[okg, "flag_international"].astype(int)), list(gen.loc[okg, f"intl_{truth_src}"].astype(int)), B, np.random.default_rng(seed + 12))
        evaluable = not math.isnan(res["kappa"]) and not math.isnan(kcp)
        d25 = {"kappa_flag_vs_cause_binary": res["kappa"], "ci": [res["lo"], res["hi"]], "n": res["n"],
               "n_coded_international_by_cause": int(sum(ys)), "n_flagged_international_by_theme": int(sum(xs)),
               "kappa_general_flagged_stratum_only": resg["kappa"], "d15_cause_kappa": kcp, "truth_source": truth_src,
               "status": status(evaluable and res["kappa"] >= 0.6 and kcp >= 0.6, evaluable),
               "reading": ("may be called 'international framing of inflation'" if evaluable and res["kappa"] >= 0.6 and kcp >= 0.6
                           else "descriptive only; no regression claims" if evaluable else "cannot be evaluated; descriptive only until it can")}
        if res["reason"]:
            d25["note"] = res["reason"]
    report["gates"]["D25_international_kappa"] = d25

    # ---- slug-based codes (D16 Mode B route): separate, labelled, never mixed into the gates
    if "S" in results:
        sl = {"label": "SLUG-BASED (URL slug only, not full text); reported separately, not used in any gate", "n_coded": int(frame["rel_S"].notna().sum()),
              "uninformative_slug_share_all_sampled": float(np.mean([not slug_informative(u) for u in frame["url"]]))}
        for st_ in ("precision", "recall", "f2"):
            r_ = cell("S", baseline, "gating", "all", st_)
            sl[f"gating_{st_}"] = None if r_ is None else r_["estimate"]
            sl[f"gating_{st_}_ci"] = [None if r_ is None else r_["ci_lo"], None if r_ is None else r_["ci_hi"]]
        both = frame[frame["rel_S"].notna() & frame["rel_A"].notna()]
        sl["kappa_slug_vs_fulltext_relevance"] = kappa_ci(list(both["rel_S"]), list(both["rel_A"]), B, np.random.default_rng(seed + 21))
        report["slug_based"] = sl
    return report, prf, kappas, cov


# ----------------------------------------------------------------------------- reporting
def _f(x, nd=3):
    return "NA" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def md_table(df) -> str:
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    rows += ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(rows)


def render_md(rep, prf, kappas, cov) -> str:
    g = rep["gates"]
    L = ["# Audit gate report", "", f"Mode: {rep['mode']}. Primary LLM coder: {rep['primary_coder']}. Baseline flag: {rep['baseline']}.",
         "Statuses: PASS, FAIL, NOT_EVALUABLE (missing data, nothing assumed).", ""]
    L += ["| Gate | Statistic (95% CI) | Status | Consequence |", "|---|---|---|---|"]
    r = g["D15_relevance_kappa"]
    lab = "LLM A vs LLM B (no human coding)" if str(r["status"]).startswith("NOT_APPLICABLE") else "human vs LLM"
    L.append(f"| D15 relevance kappa ({lab}), threshold 0.7 | {_f(r['kappa'])} ({_f(r['ci'][0])}, {_f(r['ci'][1])}), n={r['n']} | {r['status']} | {r['reading']} |")
    for k, nm in (("D15_direction_kappa", "direction"), ("D15_cause_kappa", "cause")):
        r = g[k]
        L.append(f"| D15 {nm} kappa, threshold 0.6 | {_f(r['kappa'])} ({_f(r['ci'][0])}, {_f(r['ci'][1])}), n={r['n']} | {r['status']} | {r['reading']} |")
    r = g["D15_precision_recall"]
    if "precision" in r:
        L.append(f"| D15 precision >= 0.5 and gating recall >= 0.6 | P {_f(r['precision'])} ({_f(r['precision_ci'][0])}, {_f(r['precision_ci'][1])}); R {_f(r['gating_recall'])} ({_f(r['gating_recall_ci'][0])}, {_f(r['gating_recall_ci'][1])}) | {r['status']} | {r['action']} |")
    else:
        L.append(f"| D15 precision/recall | NA | {r['status']} | {r['reading']} |")
    r = g["D25_international_kappa"]
    if "kappa_flag_vs_cause_binary" in r:
        L.append(f"| D25 kappa(international theme, international cause) >= 0.6 and cause kappa >= 0.6 | {_f(r['kappa_flag_vs_cause_binary'])} ({_f(r['ci'][0])}, {_f(r['ci'][1])}), n={r['n']}, coded international {r['n_coded_international_by_cause']} | {r['status']} | {r['reading']} |")
    else:
        L.append(f"| D25 | NA | {r['status']} | {r['reading']} |")
    r = g["D29_vernacular_recall"]
    if "difference" in r:
        L.append(f"| D29 vernacular recall within 0.15 of English (ECON frame) | vern {_f(r['vernacular_recall_econ'])}, eng {_f(r['english_recall_econ'])}, diff {_f(r['difference'])} ({_f(r['difference_ci'][0])}, {_f(r['difference_ci'][1])}) | {r['status']} | {r['reading']} |")
    else:
        L.append(f"| D29 | NA | {r['status']} | {r['reading']} |")
    pr = g["D15_precision_recall"]
    if "unscreened_nonecon" in pr and "share" in pr["unscreened_nonecon"]:
        u = pr["unscreened_nonecon"]
        L += ["", "## Unscreened non-ECON stratum (upper bound only)", "",
              f"{u['relevant']} of {u['n']} coded articles relevant; share {_f(u['share'])}, exact 95% CI ({_f(u['exact_ci'][0])}, {_f(u['exact_ci'][1])}). "
              f"Recall floor if the upper limit applied to the whole stratum: {_f(u['recall_floor_incl_unscreened_upper'])}. {u['reading']}."]
    if "slug_based" in rep:
        sl = rep["slug_based"]
        L += ["", "## Slug-based metrics (Mode B route)", "", sl["label"] + ".",
              f"Coded n {sl['n_coded']}; gating precision {_f(sl['gating_precision'])}, recall {_f(sl['gating_recall'])}, F2 {_f(sl['gating_f2'])}; "
              f"uninformative slug share {_f(sl['uninformative_slug_share_all_sampled'])}."]
    L += ["", "## Coverage by stratum x period cell (nothing imputed; MAR assumed within each cell)", "", md_table(cov), ""]
    if "f2_by_variant" in pr:
        L += ["## F2 by variant (gating frame, all languages)", ""] + [f"- {k}: {_f(v)}" for k, v in pr["f2_by_variant"].items()] + [""]
    L += ["## Files", "", "metrics_prf.csv (precision/recall/F2 by variant, frame, language/retrieval-mode group, truth source), metrics_kappa.csv (human-LLM and LLM-LLM kappas by language and retrieval mode)."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", nargs="+", default=["data/interim/audit/private/audit_key.csv"], help="one key, or one per tranche")
    ap.add_argument("--manifest", nargs="+", default=["data/interim/audit/audit_manifest.csv"])
    ap.add_argument("--human", default=None)
    ap.add_argument("--llm-a", default="data/interim/audit/llm_codes_A.csv")
    ap.add_argument("--llm-b", default="data/interim/audit/llm_codes_B.csv")
    ap.add_argument("--slug-a", default=None, help="llm_codes_slug_A.csv (slug-based codes, reported separately)")
    ap.add_argument("--log", default="logs/audit_retrieval_log.csv")
    ap.add_argument("--mode", choices=["A", "B"], default="A")
    ap.add_argument("--baseline", default="flag_baseline")
    ap.add_argument("--variants", default=None, help="comma-separated D9 variant flags (price-family, WB price stability, strict); the ONLY best-F2 candidates besides the baseline")
    ap.add_argument("--config", default=None, help="JSON with optional keys baseline, d9_variants, human_languages")
    ap.add_argument("--human-languages", default=None, help="default en,hin")
    ap.add_argument("--collapse-empty-cells", action="store_true")
    ap.add_argument("--primary-coder", choices=["A", "B"], default="A")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261116)
    ap.add_argument("--out-dir", default="outputs/audit")
    ap.add_argument("--no-human", action="store_true",
                    help="user ruling: no human coding; LLM coder --primary-coder is truth, LLM-LLM kappa is reliability")
    a = ap.parse_args(argv)

    cfg = json.loads(Path(a.config).read_text()) if a.config else {}
    baseline = cfg.get("baseline", a.baseline)
    variants = [v.strip() for v in a.variants.split(",") if v.strip()] if a.variants else cfg.get("d9_variants")
    hl = [x.strip() for x in (a.human_languages or ",".join(cfg.get("human_languages", ["en", "hin"]))).split(",")]

    def rd(p):
        return pd.read_csv(p, dtype=str) if p and Path(p).exists() else None
    key = pd.concat([pd.read_csv(k, dtype={"audit_id": str}) for k in a.key], ignore_index=True)
    manifest = pd.concat([pd.read_csv(m, dtype=str) for m in a.manifest], ignore_index=True)
    rep, prf, kap, cov = run(key, manifest, rd(a.human), rd(a.llm_a), rd(a.llm_b), rd(a.log), a.mode, baseline, variants,
                             primary=a.primary_coder, B=a.bootstrap, seed=a.seed, human_langs=hl, slug=rd(a.slug_a),
                             collapse_empty=a.collapse_empty_cells, no_human=a.no_human)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prf.to_csv(out / "metrics_prf.csv", index=False)
    kap.to_csv(out / "metrics_kappa.csv", index=False)
    (out / "gate_report.json").write_text(json.dumps(rep, indent=2, default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else str(o)))
    (out / "gate_report.md").write_text(render_md(rep, prf, kap, cov))
    print((out / "gate_report.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
