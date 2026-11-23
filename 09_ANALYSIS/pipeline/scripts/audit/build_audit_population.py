"""Build the article-level audit population for sample_audit.py (D15), 23 Nov 2026.

Population = panel-source articles on L3 window days (the only days with URLs):
  * ECON-tagged articles: Q2 article rows (row_type A, window_day) from all window days;
  * non-ECON articles: ONLY the 19 seeded window days of the approved non-ECON pull (job audit_nonecon), because
    Q2 keeps article rows only for ECON/price-flagged articles. Q2's non-ECON price-flagged rows on other days are
    dropped so the non-ECON population is defined on the same 19 days throughout.
Flags (from V1 Themes; definitions as scripts/build/flags.csv):
  flag_baseline (ECON_INFLATION), flag_econ (any ECON_), flag_price_family, flag_wb442,
  flag_strict (>= 2 of ECON_INFLATION / WB_442_INFLATION / ECON_COST_OF_LIVING), flag_international (E4 family).
Also writes the non-ECON weight factor R = (non-ECON panel articles on all window days, from the Q2 aggregates)
/ (non-ECON articles on the 19 days); scale_audit_weights.py multiplies the nonecon_* sampling weights by R.
Outputs: data/interim/audit/population.parquet, data/interim/audit/population_meta.json
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

root = Path(__file__).resolve().parents[2]
flags = pd.read_csv(root / "scripts/build/flags.csv").set_index("flag")
# RE2 (pyarrow) has no lookahead: rupee tokens are blanked first (see add_flags), then any named currency matches
INTL = "|".join(f"(?:{r[1:-1]})" for r in flags[flags.family == "international"].regex).replace("(?!.*RUPEE)", "")
RX = {
    "flag_baseline": flags.loc["infl_baseline", "regex"][1:-1],
    "flag_econ": r"ECON_[A-Z0-9_]+",
    "flag_price_family": flags.loc["price_family", "regex"][1:-1],
    "flag_wb442": "WB_442_INFLATION",
    "flag_international": INTL,
}
FAM = ["ECON_INFLATION", "WB_442_INFLATION", "ECON_COST_OF_LIVING"]


def add_flags(t: pa.Table, themes_col: str) -> pd.DataFrame:
    th = pc.fill_null(t.column(themes_col), "")
    th = pc.replace_substring_regex(th, r"ECON_WORLDCURRENCIES_[A-Z_]*RUPEE[A-Z_]*", "RUPEE_TOKEN_REMOVED")
    d = {}
    for k, r in RX.items():
        d[k] = pc.match_substring_regex(th, f"(^|;)({r})(;|$)").to_numpy(zero_copy_only=False)
    fam = sum(pc.match_substring_regex(th, f"(^|;){c}(;|$)").to_numpy(zero_copy_only=False).astype(int) for c in FAM)
    df = t.drop_columns([themes_col]).to_pandas()
    for k, v in d.items():
        df[k] = v
    df["flag_strict"] = fam >= 2
    return df


panel = pd.read_csv(root / "data/processed/index/panel_outlets.csv")
panel_src = set(panel[panel.in_panel].domain)
non = pq.read_table(glob.glob(str(root / "data/processed/bq_out/audit_nonecon/*.parquet")))
non_df = add_flags(non, "Themes")
non_days = set(pd.to_datetime(non_df.pdate).dt.date.astype(str))
non_df = non_df[non_df.SourceCommonName.isin(panel_src)]
assert not non_df.flag_econ.any()

parts = []
cols = ["row_type", "window_day", "pdate", "gkgrecordid", "gdelt_date", "document_identifier", "source",
        "translation_info", "themes"]
for d in sorted(glob.glob(str(root / "data/processed/bq_out/q2_[AB]_L3_*"))):
    for f in sorted(Path(d).glob("part-*.parquet")):
        if "row_type" not in pq.read_schema(f).names:
            continue
        t = pq.read_table(f, columns=cols, filters=[("row_type", "=", "A"), ("window_day", "=", True)])
        if t.num_rows == 0:
            continue
        x = add_flags(t, "themes")
        x = x[x.source.isin(panel_src)]
        x = x[x.flag_econ]  # non-ECON rows come only from the 19-day pull
        parts.append(x)
eco = pd.concat(parts, ignore_index=True).rename(columns={
    "gkgrecordid": "GKGRECORDID", "gdelt_date": "DATE", "document_identifier": "DocumentIdentifier",
    "source": "SourceCommonName", "translation_info": "TranslationInfo"})
eco["DATE"] = eco.DATE.astype("Int64").astype(str)
non_df["DATE"] = non_df.DATE.astype("Int64").astype(str)
keep = ["pdate", "GKGRECORDID", "DATE", "DocumentIdentifier", "SourceCommonName", "TranslationInfo",
        "flag_baseline", "flag_econ", "flag_price_family", "flag_wb442", "flag_strict", "flag_international"]
pop = pd.concat([eco[keep], non_df[keep]], ignore_index=True)
pop["pdate"] = pd.to_datetime(pop.pdate).dt.date.astype(str)

# non-ECON weight factor from the Q2 aggregates (window days, panel): n_articles - n_econ (raw counts)
G = []
for f in glob.glob(str(root / "data/processed/index/cache/*__G.parquet")):
    if "pdate" in pq.read_schema(f).names:
        G.append(pd.read_parquet(f, columns=["row_type", "pdate", "source", "n_articles", "n_econ"]))
G = pd.concat(G)
S = G[(G.row_type == "S") & G.source.isin(panel_src)].copy()
S["pdate"] = S.pdate.astype(str)
S["non"] = S.n_articles - S.n_econ
tot_all = float(S.non.sum())
tot_19 = float(S[S.pdate.isin(non_days)].non.sum())
meta = dict(n_population=int(len(pop)), n_econ=int(len(eco)), n_nonecon=int(len(non_df)),
            nonecon_days=sorted(non_days), nonecon_days_with_rows=int(non_df.pdate.astype(str).nunique()),
            nonecon_articles_all_window_days_raw=tot_all, nonecon_articles_19_days_raw=tot_19,
            nonecon_weight_factor_R=tot_all / tot_19,
            note="R uses raw (non-deduplicated) S-row counts; sample_audit deduplicates by URL, so R is the ratio "
                 "of populations under the same counting rule only approximately (cross-day dup rate 0.3%).")
out = root / "data/interim/audit"
out.mkdir(parents=True, exist_ok=True)
pop.to_parquet(out / "population.parquet", index=False)
(out / "population_meta.json").write_text(json.dumps(meta, indent=1))
print(json.dumps({k: v for k, v in meta.items() if k != "nonecon_days"}, indent=1))
print(pop[[c for c in pop.columns if c.startswith("flag_")]].mean().round(4).to_dict())
