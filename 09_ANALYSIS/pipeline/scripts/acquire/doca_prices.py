#!/usr/bin/env python3
"""DoCA daily retail prices of 22 essential commodities by centre (D38).

Source order (D38):
  (1) CEDA (Ashoka University) cleaned mirror: https://dca.ceda.ashoka.edu.in
      Verified from its README and landing page (Nov 2026): 22 commodities, retail and
      wholesale, from 2009; centre-level archive 2009-2023 (README lists 180 centres; the
      landing page says 'over 500 centres'); from September 2023 DoCA aggregates to
      state/UT level and, per the CEDA page, 'centre-level data is no longer being published'.
      CSV download exists in the portal UI. [UNVERIFIED] any direct CSV URL or API.
  (2) DoCA price monitoring site: https://fcainfoweb.nic.in/reports/report_menu_web.aspx
      [UNVERIFIED] form field names and whether per-date centre reports can be scripted.
      Given (1), centre-level data after Aug/Sep 2023 probably do not exist anywhere;
      D38 then ends the E1 sample at Aug 2023. This script records the evidence for that.

What the script does
  * Probes the CEDA site: saves landing page + README + any linked CSV/ZIP it finds
    (same host only) to data/raw/doca/ceda/.
  * Probes the DoCA report page: saves it and writes logs/doca_form_fields.json (all form
    inputs/selects/options) so a person can see what a scripted request would need.
    If scripts/acquire/doca_form_config.json exists (you write it after reading the probe),
    it replays the ASP.NET postback for each date in the config and saves each response raw.
  * Stacks any CSVs found in data/raw/doca/{ceda,ceda_manual,doca_manual}/ into
    data/processed/doca_centre_daily.csv (date, centre, state, commodity, price_rs_per_kg, source),
    recognising column names heuristically and reporting the unrecognised ones.
  * Checks each IESH city against the centres actually present
    (scripts/acquire/iesh_city_centre_map.csv) -> data/processed/iesh_city_centre_match.csv
    with first/last date and number of days per city; this is the evidence for gate (d) in D42.

Manual fallback (expected to be needed): in a browser, open https://dca.ceda.ashoka.edu.in,
choose centre-level retail prices, all commodities, 2014-01-01 to latest, download CSV
(split by year if the portal limits size) into data/raw/doca/ceda_manual/, then run with --offline.

Usage: python scripts/acquire/doca_prices.py [--root PATH] [--offline]
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from acq_common import (Project, banner, base_parser, fetch, log_download, make_session,
                        polite_sleep, read_csv_rows, sha256_bytes, write_csv_rows, write_json)

SOURCE = "doca"
CEDA = "https://dca.ceda.ashoka.edu.in/"
CEDA_README = "https://dca.ceda.ashoka.edu.in/README.html"
DOCA = "https://fcainfoweb.nic.in/reports/report_menu_web.aspx"

COLMAP = {
    "date": ["date", "reporting_date", "price_date", "day"],
    "centre": ["centre", "center", "centre_name", "center_name", "market", "city", "centre name"],
    "state": ["state", "state_name", "state/ut", "state_ut"],
    "commodity": ["commodity", "commodity_name", "item", "commodity name"],
    "price": ["price", "retail_price", "retail price", "value", "price_rs_per_kg", "retail"],
    "zone": ["zone", "region"],
    "unit": ["unit", "units"],
}


def probe_ceda(proj, s, args):
    for u, name in ((CEDA, "ceda_home.html"), (CEDA_README, "ceda_readme.html")):
        p = fetch(proj, s, SOURCE, u, dest_name=name, subdir="ceda", timeout=args.timeout,
                  notes="CEDA mirror probe", skip_existing=False)
        polite_sleep(args.sleep)
        if not p:
            continue
        html = p.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = urljoin(u, a["href"])
            if urlparse(href).netloc.endswith("ceda.ashoka.edu.in") and re.search(r"\.(csv|zip)(\?|$)", href, re.I):
                fetch(proj, s, SOURCE, href, subdir="ceda", timeout=max(args.timeout, 300),
                      notes="CEDA linked data file")
                polite_sleep(args.sleep)


def probe_doca(proj, s, args):
    p = fetch(proj, s, SOURCE, DOCA, dest_name="doca_report_menu.html", subdir="doca_site",
              timeout=args.timeout, notes="DoCA report menu probe", skip_existing=False)
    if not p:
        return
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "lxml")
    fields = []
    for el in soup.find_all(["input", "select"]):
        f = {"tag": el.name, "name": el.get("name"), "id": el.get("id"), "type": el.get("type"),
             "value": (el.get("value") or "")[:80]}
        if el.name == "select":
            f["options"] = [(o.get("value"), o.get_text(strip=True)) for o in el.find_all("option")][:400]
        fields.append(f)
    write_json(proj.logs / "doca_form_fields.json", {"url": DOCA, "fields": fields})
    print(f"DoCA form: {len(fields)} fields -> logs/doca_form_fields.json")
    cfg_path = proj.acquire / "doca_form_config.json"
    if not cfg_path.exists():
        print("No doca_form_config.json: scripted DoCA download skipped (see docstring).")
        return
    cfg = json.loads(cfg_path.read_text())
    # cfg = {"static": {field: value, ...}, "date_field": "...", "dates": ["dd/mm/yyyy", ...]}
    hidden = {i.get("name"): i.get("value", "") for i in soup.find_all("input", type="hidden") if i.get("name")}
    for d in cfg.get("dates", []):
        data = dict(hidden, **cfg.get("static", {}))
        data[cfg["date_field"]] = d
        try:
            r = s.post(DOCA, data=data, timeout=args.timeout)
        except Exception as e:
            log_download(proj, SOURCE, DOCA, f"error:{type(e).__name__}", None, "", f"date {d}")
            continue
        out = proj.raw_dir(SOURCE) / "doca_site" / f"report_{d.replace('/', '-')}.html"
        out.write_bytes(r.content)
        log_download(proj, SOURCE, DOCA, r.status_code, len(r.content), sha256_bytes(r.content),
                     f"postback date {d} [UNVERIFIED form semantics]")
        polite_sleep(max(args.sleep, 2))


def harmonise(cols):
    m = {}
    for c in cols:
        lc = str(c).strip().lower()
        for k, alts in COLMAP.items():
            if (lc in alts or lc == k) and k not in m.values():
                m[c] = k
                break
    return m


def stack(proj):
    import pandas as pd
    frames, report = [], []
    for sub in ("ceda", "ceda_manual", "doca_manual"):
        d = proj.raw_dir(SOURCE) / sub
        d.mkdir(exist_ok=True)
        for f in sorted(d.rglob("*")):
            if f.suffix.lower() == ".zip":
                ex = proj.root / "data" / "interim" / "doca_unzipped" / f.stem
                ex.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(f) as z:
                    z.extractall(ex)
                files = list(ex.rglob("*.csv"))
            elif f.suffix.lower() == ".csv":
                files = [f]
            else:
                continue
            for g in files:
                try:
                    df = pd.read_csv(g, low_memory=False)
                except Exception as e:
                    report.append({"file": g.name, "error": str(e)})
                    continue
                m = harmonise(df.columns)
                df = df.rename(columns=m)
                report.append({"file": g.name, "rows": len(df), "mapped": m,
                               "unmapped": [c for c in df.columns if c not in m.values()]})
                if not {"date", "commodity", "price"} <= set(df.columns):
                    continue
                if "centre" not in df.columns:
                    df["centre"] = None  # state-level file (post Sep 2023)
                df["source"] = f"{sub}/{g.name}"
                frames.append(df)
    write_json(proj.logs / "doca_stack_report.json", report)
    if not frames:
        return None
    out = pd.concat(frames, ignore_index=True, sort=False)
    out["date"] = pd.to_datetime(out["date"], errors="coerce", dayfirst=True)
    out = out.rename(columns={"price": "price_rs_per_kg"})
    keep = [c for c in ["date", "centre", "state", "zone", "commodity", "price_rs_per_kg", "unit", "source"]
            if c in out.columns]
    out = out[keep].dropna(subset=["date"])
    out.to_csv(proj.processed / "doca_centre_daily.csv", index=False)
    print(f"wrote data/processed/doca_centre_daily.csv ({len(out)} rows)")
    return out


def match_cities(proj, df):
    rows = read_csv_rows(proj.acquire / "iesh_city_centre_map.csv")
    out = []
    centres = df.dropna(subset=["centre"]) if df is not None else None
    for r in rows:
        names = [r["candidate_doca_centre"]] + [x for x in r["alt_spellings_to_try"].split(";") if x]
        rec = dict(r, matched_centre_name="", first_date="", last_date="", n_days="", match_status="no_data")
        if centres is not None and len(centres):
            cn = centres["centre"].astype(str).str.strip().str.lower()
            for nm in names:
                sel = centres[cn == nm.lower()]
                if len(sel):
                    rec.update(matched_centre_name=nm, first_date=sel["date"].min().date(),
                               last_date=sel["date"].max().date(), n_days=sel["date"].nunique(),
                               match_status="found_exact")
                    break
            else:
                rec["match_status"] = "not_found_check_spelling"
        out.append(rec)
    fields = list(rows[0].keys()) + ["matched_centre_name", "first_date", "last_date", "n_days", "match_status"]
    write_csv_rows(proj.processed / "iesh_city_centre_match.csv", out, fields)
    print("wrote data/processed/iesh_city_centre_match.csv")
    for r in out:
        print(f"  {r['iesh_city']:20s} {r['match_status']:26s} {r['first_date']} .. {r['last_date']}")


def main():
    p = base_parser(__doc__)
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    proj = Project(args.root)
    banner("DoCA retail prices (CEDA mirror first)")
    if not args.offline:
        s = make_session()
        probe_ceda(proj, s, args)
        probe_doca(proj, s, args)
    df = stack(proj)
    if df is None:
        print("No price CSVs found. Follow the manual fallback in this script's docstring "
              "(download from the CEDA portal into data/raw/doca/ceda_manual/).")
    match_cities(proj, df)


if __name__ == "__main__":
    main()
