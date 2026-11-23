#!/usr/bin/env python3
"""Google Trends for India and states, monthly (D7, D17, D26).

Terms: scripts/acquire/trends_terms.csv ("inflation", "mehngai", "महंगाई", item-price terms).
Rules from D7:
  * each series fetched 3 times on DIFFERENT DAYS and averaged (run `pull` once a day on
    three days, then `combine`);
  * states with more than 20% zero months are dropped;
  * state series are used within state only (state fixed effects), never compared across states.

Notes from the web (Nov 2026):
  * pytrends (unofficial) was archived in April 2025 according to developer blogs; it may still
    work but 429 rate-limit errors are common. [UNVERIFIED that it works on the run date.]
  * Google announced an official Trends API in 2025, in limited alpha. Not used here.
  * Fallback: download CSVs by hand from trends.google.com (Explore -> download icon,
    'multiTimeline.csv') and save them as
      data/raw/trends/manual/pull_YYYYMMDD/<GEO>__<term>.csv     e.g. IN__inflation.csv, IN-MH__mehngai.csv
    then run `combine`. The manual files are parsed the same way.
  * Monthly resolution: Trends returns monthly points for time ranges longer than about
    five years [UNVERIFIED threshold]; the script checks the returned frequency and stops if
    it is not monthly.

Two kinds of pull
  * solo: one term per request (own 0-100 scale): national and state series for D17 and E1.
  * anchored (national items only): up to 4 item terms + the anchor term in one request,
    so item attention shares are on a common scale (D26 weights).

Outputs
  data/raw/trends/pull_YYYYMMDD/<kind>/<GEO>__<term>.csv   frames as returned by pytrends
  data/processed/trends_monthly.csv       geo, term, kind, month, value_mean, value_sd, n_pulls, pull_dates
  data/processed/trends_state_filter.csv  geo, term, share_zero_months, keep (<= 20%)

Usage
  python scripts/acquire/trends.py pull    [--root PATH] [--states] [--sleep 30]
  python scripts/acquire/trends.py combine [--root PATH]
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import time
from pathlib import Path

from acq_common import (Project, banner, base_parser, log_download, read_csv_rows, sha256_file,
                        write_csv_rows)

SOURCE = "trends"
TIMEFRAME_DEFAULT = "2015-01-01 2026-10-31"


def slug(term: str) -> str:
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", term.strip())


def save_frame(proj, df, path: Path, note: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, encoding="utf-8")
    log_download(proj, SOURCE, "pytrends:" + note, 200, path.stat().st_size, sha256_file(path), note)


def with_backoff(fn, tries=5, base_wait=60):
    for k in range(tries):
        try:
            return fn()
        except Exception as e:  # pytrends raises TooManyRequestsError / ResponseError
            msg = str(e)
            if "429" in msg or "TooManyRequests" in type(e).__name__:
                w = base_wait * (2 ** k)
                print(f"   429 rate limit; waiting {w}s")
                time.sleep(w)
                continue
            raise
    raise RuntimeError("gave up after repeated 429s")


def pull(proj, args):
    try:
        from pytrends.request import TrendReq
    except ImportError:
        sys.exit("pip install pytrends  (or use the manual CSV fallback; see docstring)")
    terms = read_csv_rows(proj.acquire / "trends_terms.csv")
    today = dt.date.today().strftime("%Y%m%d")
    root = proj.raw_dir(SOURCE) / f"pull_{today}"
    py = TrendReq(hl="en-US", tz=-330, timeout=(10, 60), retries=0)

    def one(kw_list, geo, kind):
        fname = root / kind / f"{geo}__{'+'.join(slug(k) for k in kw_list)}.csv"
        if fname.exists():
            return
        def go():
            py.build_payload(kw_list, timeframe=args.timeframe, geo=geo, cat=0, gprop="")
            return py.interest_over_time()
        try:
            df = with_backoff(go)
        except Exception as e:
            log_download(proj, SOURCE, f"pytrends:{geo}:{kw_list}", f"error:{type(e).__name__}", None, "", str(e)[:200])
            print(f"   [fail] {geo} {kw_list}: {e}")
            return
        if df is None or df.empty:
            log_download(proj, SOURCE, f"pytrends:{geo}:{kw_list}", "empty", 0, "", "no data")
            return
        if len(df) > 2:
            gap = (df.index[1] - df.index[0]).days
            if gap < 27:
                sys.exit(f"Returned frequency is {gap} days, not monthly; widen --timeframe.")
        save_frame(proj, df, fname, f"{kind} {geo} {kw_list} timeframe={args.timeframe}")
        print(f"   ok {kind:8s} {geo:6s} {kw_list}")
        time.sleep(args.sleep)

    banner(f"Trends pull {today}")
    for t in terms:
        one([t["term"]], "IN", "solo")
    items = [t["term"] for t in terms if t["group"] == "item"]
    for i in range(0, len(items), 4):
        one(items[i:i + 4] + [args.anchor], "IN", "anchored")
    if args.states:
        geos = state_codes(py, proj, root)
        for g in geos:
            for t in terms:
                if t.get("pull_states", "N").upper() == "Y":
                    one([t["term"]], g, "solo")


def state_codes(py, proj, root):
    """ISO-3166-2 state codes as Trends uses them, discovered from Trends itself."""
    def go():
        py.build_payload(["inflation"], timeframe=TIMEFRAME_DEFAULT, geo="IN")
        return py.interest_by_region(resolution="REGION", inc_low_vol=True, inc_geo_code=True)
    df = with_backoff(go)
    save_frame(proj, df, root / "meta" / "IN_regions.csv", "state code discovery")
    codes = [c for c in df["geoCode"].astype(str) if c.startswith("IN-")]
    print(f"   {len(codes)} state/UT codes")
    return codes


def read_any(path: Path):
    import pandas as pd
    txt = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    if txt and txt[0].lower().startswith("category"):  # manual multiTimeline.csv: 2 header lines
        df = pd.read_csv(path, skiprows=2, encoding="utf-8-sig")
        df = df.rename(columns={df.columns[0]: "date"})
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
        df = df.rename(columns={df.columns[0]: "date"})
    if "isPartial" in df.columns:
        df = df[df["isPartial"].astype(str).str.lower() != "true"].drop(columns="isPartial")
    df["month"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m")
    long = df.drop(columns="date").melt(id_vars="month", var_name="term", value_name="value")
    long["term"] = long["term"].str.replace(r":\s*\(.*\)$", "", regex=True).str.strip()  # 'inflation: (India)'
    long["value"] = pd.to_numeric(long["value"].astype(str).str.replace("<1", "0.5"), errors="coerce")
    return long


def combine(proj, args):
    import pandas as pd
    frames = []
    base = proj.raw_dir(SOURCE)
    for f in list(base.glob("pull_*/*/*.csv")) + list(base.glob("manual/pull_*/*.csv")):
        if f.parent.name == "meta":
            continue
        pull_date = next(p.name[5:] for p in f.parents if p.name.startswith("pull_"))
        kind = "manual" if "manual" in f.parts else f.parent.name
        geo = f.name.split("__")[0]
        d = read_any(f)
        d["geo"], d["kind"], d["pull_date"], d["anchor_set"] = geo, kind, pull_date, f.stem.split("__", 1)[-1]
        frames.append(d)
    if not frames:
        sys.exit("No pulls found. Run `trends.py pull` (three different days) or add manual CSVs.")
    allp = pd.concat(frames, ignore_index=True)
    allp["kind"] = allp["kind"].replace({"manual": "solo"})
    g = allp.groupby(["geo", "term", "kind", "anchor_set", "month"])
    out = g["value"].agg(value_mean="mean", value_sd="std").reset_index()
    out["n_pulls"] = g["pull_date"].nunique().values
    out["pull_dates"] = g["pull_date"].apply(lambda s: ";".join(sorted(set(s)))).values
    out.to_csv(proj.processed / "trends_monthly.csv", index=False)
    short = out[out["n_pulls"] < 3]
    if len(short):
        print(f"[WARN] {short[['geo','term']].drop_duplicates().shape[0]} series have <3 pulls "
              "(D7 requires 3 pulls on different days).")
    st = out[(out.geo.str.startswith("IN-")) & (out.kind == "solo")]
    filt = (st.groupby(["geo", "term"])["value_mean"].apply(lambda s: float((s.fillna(0) == 0).mean()))
            .rename("share_zero_months").reset_index())
    filt["keep"] = filt["share_zero_months"] <= 0.20
    write_csv_rows(proj.processed / "trends_state_filter.csv", filt.to_dict("records"),
                   ["geo", "term", "share_zero_months", "keep"])
    print(f"wrote trends_monthly.csv ({len(out)} rows); state filter: "
          f"{int(filt['keep'].sum())}/{len(filt)} state-term series kept")


def main():
    p = base_parser(__doc__)
    p.add_argument("action", choices=["pull", "combine"])
    p.add_argument("--states", action="store_true", help="also pull state series (slow)")
    p.add_argument("--timeframe", default=TIMEFRAME_DEFAULT)
    p.add_argument("--anchor", default="inflation", help="anchor term for anchored item batches")
    p.set_defaults(sleep=30.0)
    args = p.parse_args()
    proj = Project(args.root)
    (pull if args.action == "pull" else combine)(proj, args)


if __name__ == "__main__":
    main()
