"""Parse MoSPI item-level CPI (base 2012, All India) from the raw API pages already downloaded
(data/raw/cpi/api_cpi_getItemIndex/item_*.json) into data/processed/cpi2012_item.csv (23 Nov 2026).
The earlier build left this file empty. No values are altered; duplicate (period, item) records must agree,
otherwise the script stops. Columns: period (YYYY-MM), year, month, item, index, status."""
import glob, json, sys
from pathlib import Path
import pandas as pd
root = Path(__file__).resolve().parents[2]
rows = []
for f in sorted(glob.glob(str(root / "data/raw/cpi/api_cpi_getItemIndex/item_*.json"))):
    for r in json.load(open(f, encoding="utf-8")).get("data", []):
        rows.append({"year": int(r["year"]), "month": r["month"], "item": r["item"].replace("�", "-").strip(),
                     "index": pd.to_numeric(r["index"], errors="coerce"), "status": r.get("status"),
                     "baseyear": r.get("baseyear")})
d = pd.DataFrame(rows)
d = d[d.baseyear.astype(str) == "2012"]
d["period"] = pd.to_datetime(d.year.astype(str) + "-" + d.month, format="%Y-%B").dt.strftime("%Y-%m")
g = d.groupby(["period", "item"])["index"].agg(["nunique", "first", "size"])
bad = g[g["nunique"] > 1]
if len(bad):
    sys.exit(f"conflicting duplicate records: {bad.head()}")
d = d.drop_duplicates(["period", "item"]).sort_values(["item", "period"])
d[["period", "year", "month", "item", "index", "status"]].to_csv(root / "data/processed/cpi2012_item.csv", index=False)
print(len(d), "rows;", d.item.nunique(), "items;", d.period.min(), "to", d.period.max(),
      "; months per item (median):", int(d.groupby("item").size().median()), "; dup records dropped:", int((g["size"] > 1).sum()))
