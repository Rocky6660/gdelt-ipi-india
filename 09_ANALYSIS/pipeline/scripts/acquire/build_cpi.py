"""Combine the raw MoSPI CPI API pages (data/raw/cpi/api_cpi_getCPIIndex/*.json, base 2012) into one tidy file.
Writes data/processed/cpi2012_allindia.csv: year, month, period, sector, group, subgroup, index (All India only),
and data/processed/cpi2012_state.csv (all states). Duplicates across pages are dropped. No values are altered."""
import argparse, glob, json
from pathlib import Path
import pandas as pd
ap = argparse.ArgumentParser(); ap.add_argument("--root", type=Path, required=True); a = ap.parse_args()
recs = []
for f in sorted(glob.glob(str(a.root / "data/raw/cpi/api_cpi_getCPIIndex/*.json"))):
    try:
        j = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    d = j.get("data") if isinstance(j, dict) else j
    if isinstance(d, list):
        recs.extend(d)
df = pd.DataFrame(recs).drop_duplicates()
df["index"] = pd.to_numeric(df["index"], errors="coerce")
df["period"] = pd.to_datetime(df["month"].astype(str) + " " + df["year"].astype(str), format="%B %Y", errors="coerce").dt.strftime("%Y-%m")
cols = ["year", "month", "period", "state", "sector", "group", "subgroup", "index"]
df[cols].to_csv(a.root / "data/processed/cpi2012_state.csv", index=False)
ai = df[df.state.astype(str).str.lower() == "all india"][cols]
ai.to_csv(a.root / "data/processed/cpi2012_allindia.csv", index=False)
print(len(df), "records;", len(ai), "all-India;", ai.period.min(), "-", ai.period.max())
print(sorted(ai.group.astype(str).unique())[:20])
print(sorted(ai.sector.astype(str).unique()))
