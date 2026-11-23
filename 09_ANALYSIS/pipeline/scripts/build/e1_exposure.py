"""E1 descriptive: city news exposure from edition paths (design D5, D40, D42(a)); no IESH outcomes are used.

Mechanical edition-path rule (23 Nov 2026; the agent-verified pattern table of D40 was not built in the time
available): a window-day aggregate row (outlet x day x URL section) counts as local to IESH city c if any
segment of its URL section equals one of c's fixed aliases (optionally prefixed 'my-' or suffixed
'-news'/'-city'/'-ncr'/'capital'). State-level pages and single-state outlets' home-state attribution (D5) are
NOT included (the panel has no home-state field). Panel sources only; valid days only (D13).
Outputs (data/processed/index/):
  e1_city_window.csv   city x round: local articles (day-level distinct URLs), local inflation articles, share
  e1_gate_a.csv        D42(a) cell counts per city and per year (median local / flagged articles per window)
  e1_summary.json
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bq_runner as bq  # noqa: E402

ALIASES = {
    "Ahmedabad": ["ahmedabad"], "Bengaluru": ["bengaluru", "bangalore"], "Bhopal": ["bhopal"],
    "Bhubaneswar": ["bhubaneswar"], "Chandigarh": ["chandigarh"], "Chennai": ["chennai", "madras"],
    "Delhi": ["delhi", "new-delhi", "newdelhi"], "Guwahati": ["guwahati"], "Hyderabad": ["hyderabad"],
    "Jaipur": ["jaipur"], "Jammu": ["jammu"], "Kolkata": ["kolkata", "calcutta"], "Lucknow": ["lucknow"],
    "Mumbai": ["mumbai", "bombay"], "Nagpur": ["nagpur"], "Patna": ["patna"], "Raipur": ["raipur"],
    "Ranchi": ["ranchi"], "Thiruvananthapuram": ["thiruvananthapuram", "trivandrum"],
}
SEG = {c: re.compile(r"^(my-)?(" + "|".join(map(re.escape, a)) + r")(-news|-city|-ncr|capital)?$") for c, a in ALIASES.items()}


def city_of(section: str) -> str | None:
    if not isinstance(section, str):
        return None
    hits = {c for seg in section.lower().strip("/").split("/") for c, rx in SEG.items() if rx.match(seg)}
    return next(iter(hits)) if len(hits) == 1 else None  # ambiguous multi-city sections are dropped


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out = root / "data/processed/index"
    cfg = bq.load_config(root / "scripts/config.yaml")
    panel = pd.read_csv(out / "panel_outlets.csv")
    src = set(panel[panel.in_panel].domain)
    W = pd.read_csv(out / "ipi_window.csv")
    rounds = bq.read_rounds(root / cfg["paths"]["iesh_rounds"])
    L = int(cfg["rungs"][cfg["rung"]]["window_days"])
    cal = pd.DataFrame([{"round": r, "pdate": str(fs - pd.Timedelta(days=k))[:10]} for r, fs, _ in rounds
                        for k in range(1, L + 1)])
    daily = pd.read_csv(out / "ipi_daily.csv")
    valid = set(daily.loc[daily.valid_day.astype(bool), "pdate"].astype(str))
    G = []
    for f in glob.glob(str(out / "cache/*__G.parquet")):
        if "pdate" not in pq.read_schema(f).names:
            continue
        g = pd.read_parquet(f, columns=["row_type", "pdate", "source", "url_section", "n_distinct_urls", "n_infl_distinct"])
        G.append(g[(g.row_type == "S") & g.source.isin(src)])
    S = pd.concat(G)
    S["pdate"] = S.pdate.astype(str)
    S = S[S.pdate.isin(valid)]
    secs = pd.Series(S.url_section.dropna().unique())
    cmap = dict(zip(secs, secs.map(city_of)))
    S["city"] = S.url_section.map(cmap)
    S = S[S.city.notna()].merge(cal, on="pdate", how="inner")
    S = S[S["round"].isin(W.loc[W.valid_window, "round"])]
    cw = S.groupby(["city", "round"], as_index=False)[["n_distinct_urls", "n_infl_distinct"]].sum()
    cw["local_share"] = cw.n_infl_distinct / cw.n_distinct_urls
    cw["year"] = cw["round"].str[:4]
    cw.to_csv(out / "e1_city_window.csv", index=False)
    ga = cw.groupby(["city", "year"]).agg(windows=("round", "nunique"), med_local=("n_distinct_urls", "median"),
                                           med_flagged=("n_infl_distinct", "median")).reset_index()
    ga["cell_ok_inferential"] = (ga.med_local >= 100) & (ga.med_flagged >= 30)
    ga["cell_ok_descriptive"] = ga.med_flagged >= 10
    ga.to_csv(out / "e1_gate_a.csv", index=False)
    by_year = ga.groupby("year").agg(cities_ok_inferential=("cell_ok_inferential", "sum"),
                                     cities_ok_descriptive=("cell_ok_descriptive", "sum")).reset_index()
    by_year["gate_a_pass"] = by_year.cities_ok_inferential >= 12
    summ = dict(rule=__doc__.split("Outputs")[0].strip(), cities_with_any_local=int(cw.city.nunique()),
                sections_matched=int(sum(v is not None for v in cmap.values())),
                gate_a_by_year=by_year.to_dict("records"),
                overall_city_medians=cw.groupby("city")[["n_distinct_urls", "n_infl_distinct"]].median().round(1).to_dict("index"))
    (out / "e1_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(by_year.to_string(index=False))
    print(cw.groupby("city")[["n_distinct_urls", "n_infl_distinct"]].median().round(0).astype(int).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
