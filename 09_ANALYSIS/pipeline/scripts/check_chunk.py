"""Automated first-chunk check (D4.5) used when no one can inspect before the rest of a stage runs.
Fails (exit 1) unless: rows > 0; article rows present whenever flagged articles exist; inflation share in a
plausible band (0.1%-10%); >= 50 sources. Prints the evidence; the run log keeps it."""
import glob, sys
import pandas as pd
d = sys.argv[1]
df = pd.concat(pd.read_parquet(f) for f in glob.glob(f"{d}*/*.parquet"))
agg = df[df.row_type.isin(["S", "D"])]
n, ni = agg.n_articles.sum(), agg.n_infl.sum()
na = int((df.row_type == "A").sum())
share = ni / n if n else 0
print(f"CHECK {d}: rows {len(df)}, A rows {na}, sources {agg.source.nunique()}, articles {int(n)}, infl share {share:.4f}")
ok = len(df) > 0 and (ni == 0 or na > 0) and 0.001 <= share <= 0.10 and agg.source.nunique() >= 50
print("CHECK", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
