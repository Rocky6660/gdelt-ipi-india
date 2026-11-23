#!/usr/bin/env python3
"""Policy and market controls (D7): repo rate and MPC dates, Brent, INR/USD, 10-year G-sec;
pump prices (optional, D38).

Sources
  * FRED CSV endpoint (no API key): https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>
      INDIRLTLT01STM  India 10-year government bond yield, monthly (OECD MEI) -- series page seen Nov 2026
      DEXINUS         INR per USD, daily (Fed H.10)                         -- [standard ID; not re-checked]
      DCOILBRENTEU    Brent spot, USD/bbl, daily (EIA)                      -- [standard ID; not re-checked]
  * MoSPI API, RBI dataset (swagger_user_rbi.yaml in nso-india/esankhyiki-mcp):
      GET https://api.mospi.gov.in/api/rbi/getRbiRecords?sub_indicator_code=33
      indicator 33 = 'Exchange Rate of the Indian Rupee vis-a-vis the SDR, US Dollar, ...
      (Monthly Average and end-Month Rates)'  -> RBI reference rate cross-check for INR/USD.
      [UNVERIFIED] response layout; saved raw.
  * Repo rate and MPC dates: no scriptable source confirmed. [UNVERIFIED] DBIE has a policy-
    rate table but its API is unknown. Fallback: fill templates/mpc_decisions_template.csv
    from RBI's 'Monetary Policy Statement' / 'Resolution of the Monetary Policy Committee'
    press releases (one row per MPC meeting, Oct 2016 onward; pre-MPC policy reviews from
    2015 if needed) and save it as data/raw/policy/manual/mpc_decisions.csv.
    The script validates that file (dates parse, rates in plausible range, change = diff)
    and builds a daily step series of the repo rate.
  * Pump prices: PPAC page https://ppac.gov.in/prices/retail-selling-price-rsp-of-petrol-diesel-and-domestic-lpg
    shows a menu item 'RSP of Petrol and Diesel in Metro Cities since 16.6.2017' (seen Nov 2026);
    [UNVERIFIED] its file URL. The script saves the PPAC pages and lists any xls/xlsx/pdf links.

Outputs
  data/raw/policy/...                       untouched downloads
  data/processed/markets_daily.csv          date, brent_usd, inr_usd (FRED)
  data/processed/markets_monthly.csv        month, brent_usd_avg, inr_usd_avg, gsec10y (FRED)
  data/processed/repo_rate_daily.csv        (only if the manual MPC file exists)
  data/processed/mpc_meetings.csv           (only if the manual MPC file exists)

Usage: python scripts/acquire/policy_markets.py [--root PATH] [--start 2014-01-01] [--end 2026-10-31]
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from acq_common import Project, banner, base_parser, fetch, make_session, polite_sleep, read_csv_rows

SOURCE = "policy"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_SERIES = {"DCOILBRENTEU": "brent_usd", "DEXINUS": "inr_usd", "INDIRLTLT01STM": "gsec10y"}
MOSPI_RBI = "https://api.mospi.gov.in/api/rbi/getRbiRecords"
PPAC_PAGES = ["https://ppac.gov.in/prices/retail-selling-price-rsp-of-petrol-diesel-and-domestic-lpg",
              "https://ppac.gov.in/retail-selling-price"]


def fred(proj, s, args):
    import pandas as pd
    frames = {}
    for sid, name in FRED_SERIES.items():
        p = fetch(proj, s, SOURCE, FRED.format(sid), dest_name=f"fred_{sid}.csv", subdir="fred",
                  timeout=args.timeout, notes=f"FRED {sid}", skip_existing=False)
        polite_sleep(args.sleep)
        if not p:
            continue
        df = pd.read_csv(p)
        dcol = df.columns[0]
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
        df[sid] = pd.to_numeric(df[sid], errors="coerce")  # FRED uses '.' for missing
        frames[name] = df.rename(columns={dcol: "date", sid: name})[["date", name]]
    if not frames:
        return
    daily = None
    for name in ("brent_usd", "inr_usd"):
        if name in frames:
            daily = frames[name] if daily is None else daily.merge(frames[name], on="date", how="outer")
    if daily is not None:
        daily = daily[(daily.date >= args.start) & (daily.date <= args.end)].sort_values("date")
        daily.to_csv(proj.processed / "markets_daily.csv", index=False)
        m = daily.set_index("date").resample("MS").mean().add_suffix("_avg").reset_index()
    else:
        m = None
    if "gsec10y" in frames:
        g = frames["gsec10y"]
        g = g.assign(date=g.date.dt.to_period("M").dt.to_timestamp())
        m = g if m is None else m.merge(g, on="date", how="outer")
    if m is not None:
        m = m[(m.date >= args.start) & (m.date <= args.end)].sort_values("date")
        m["month"] = m.date.dt.strftime("%Y-%m")
        m.drop(columns="date").to_csv(proj.processed / "markets_monthly.csv", index=False)
        print(f"wrote markets_daily.csv / markets_monthly.csv ({len(m)} months)")


def mospi_fx(proj, s, args):
    fetch(proj, s, SOURCE, MOSPI_RBI, dest_name="mospi_rbi_ind33.json", subdir="mospi_rbi",
          timeout=args.timeout, notes="MoSPI API RBI indicator 33 (INR monthly avg) [UNVERIFIED layout]",
          params={"sub_indicator_code": 33, "Format": "JSON", "limit": 5000}, skip_existing=False)


def ppac(proj, s, args):
    for u in PPAC_PAGES:
        p = fetch(proj, s, SOURCE, u, subdir="ppac", timeout=args.timeout, notes="PPAC page probe",
                  skip_existing=False)
        polite_sleep(args.sleep)
        if not p:
            continue
        soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "lxml")
        for a in soup.find_all("a", href=True):
            txt = a.get_text(" ", strip=True)
            href = urljoin(u, a["href"])
            if re.search(r"metro|petrol|diesel|rsp", txt, re.I) and re.search(r"\.(xlsx?|pdf)|download", href, re.I):
                print(f"  PPAC candidate: {txt[:70]} -> {href}")
                fetch(proj, s, SOURCE, href, subdir="ppac", timeout=args.timeout, notes=f"PPAC: {txt[:80]}")
                polite_sleep(args.sleep)


def mpc_manual(proj):
    import pandas as pd
    f = proj.raw_dir(SOURCE) / "manual" / "mpc_decisions.csv"
    if not f.exists():
        print("[ACTION] repo rate / MPC dates: fill scripts/acquire/templates/mpc_decisions_template.csv "
              "and save as data/raw/policy/manual/mpc_decisions.csv (see docstring).")
        return
    rows = [r for r in read_csv_rows(f) if r.get("announcement_date") and not r["announcement_date"].startswith("YYYY")]
    df = pd.DataFrame(rows)
    df["announcement_date"] = pd.to_datetime(df["announcement_date"], errors="raise")
    df["repo_rate_after"] = pd.to_numeric(df["repo_rate_after"], errors="raise")
    df = df.sort_values("announcement_date")
    problems = []
    if not df["repo_rate_after"].between(2, 12).all():
        problems.append("repo rate outside 2-12%")
    diff = (df["repo_rate_after"].diff() * 100).round()
    if "change_bp" in df and df["change_bp"].astype(str).str.len().gt(0).all():
        cb = pd.to_numeric(df["change_bp"], errors="coerce")
        bad = (cb.iloc[1:] != diff.iloc[1:]).sum()
        if bad:
            problems.append(f"{bad} rows where change_bp != change in repo_rate_after")
    df.to_csv(proj.processed / "mpc_meetings.csv", index=False)
    days = pd.date_range(df.announcement_date.min(), pd.Timestamp.today().normalize(), freq="D")
    daily = (df.set_index("announcement_date")["repo_rate_after"].reindex(days).ffill()
             .rename("repo_rate").rename_axis("date").reset_index())
    daily.to_csv(proj.processed / "repo_rate_daily.csv", index=False)
    print(f"wrote mpc_meetings.csv ({len(df)}) and repo_rate_daily.csv; checks: {problems or 'ok'}")


def main():
    p = base_parser(__doc__)
    p.add_argument("--start", default="2014-01-01")
    p.add_argument("--end", default="2026-10-31")
    p.add_argument("--skip-ppac", action="store_true")
    args = p.parse_args()
    proj = Project(args.root)
    s = make_session()
    banner("Policy and markets")
    fred(proj, s, args)
    mospi_fx(proj, s, args)
    if not args.skip_ppac:
        ppac(proj, s, args)
    mpc_manual(proj)


if __name__ == "__main__":
    main()
