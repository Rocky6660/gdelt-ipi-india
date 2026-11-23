#!/usr/bin/env python3
"""IESH unit-level microdata from RBI DBIE (D39), with a manual fallback.

What is known (web search, Nov 2026):
  * IESH releases say unit-level data for previous rounds are on the RBI Database on
    Indian Economy (DBIE) portal under the 'Unit-level Data' head:
    https://data.rbi.org.in/DBIE/#/dbie/home   (footnote 3 of the Sep 2026 release).
  * RBI press release 'Dissemination of Unit-level Data on Inflation Expectations Survey of
    Households (IESH)' exists (website.rbi.org.in ... -42620); its text could not be read here.
  * The RBI Bulletin article of July 2025 (Ruhi, Sharma, Sankaran) uses 'unit level data on
    1-year ahead median inflation expectations', so the files exist.
[UNVERIFIED] DBIE is a single-page JavaScript app. Its back-end API, whether the unit-level
files need a login, their format (CSV/XLSX/ZIP), whether they carry a city identifier,
and which rounds are covered are all unknown. This script therefore:
  1. downloads the DBIE landing page and scans it (and any JS bundles it references) for
     'unit' / 'IESH' / 'survey' download paths, saving everything it fetches untouched;
  2. tries any candidate file URLs it finds (only same-host, only .csv/.xlsx/.xls/.zip);
  3. otherwise prints the manual procedure and stops (exit code 2), so the user can
     download the files by hand into data/raw/iesh_microdata/manual/;
  4. stacks whatever files are in data/raw/iesh_microdata/{auto,manual}/ into
     data/processed/iesh_microdata_stacked.csv, harmonising column names it recognises
     and listing the ones it does not, and writes logs/iesh_microdata_report.json
     (rounds found, city identifier present?, N per round) for Gate D39.

Fallback if no microdata: the published city-level statistics from iesh.py (D39 fallback).

Usage: python scripts/acquire/iesh_microdata.py [--root PATH] [--offline]
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urljoin

from acq_common import (Project, banner, base_parser, fetch, make_session, polite_sleep,
                        write_json)

SOURCE = "iesh_microdata"
DBIE_HOME = "https://data.rbi.org.in/DBIE/"
DBIE_SPA = "https://data.rbi.org.in/DBIE/#/dbie/home"

MANUAL = """
MANUAL PROCEDURE (D39) -- about 15 minutes in a browser:
  1. Open https://data.rbi.org.in/DBIE/#/dbie/home
  2. Find the 'Unit-level Data' head (menu or home tiles); choose
     'Inflation Expectations Survey of Households' (IESH).
  3. Download every round offered (keep the original file names; do not open and re-save
     them in Excel). Also download any questionnaire / codebook / readme file.
  4. Put the files in   data/raw/iesh_microdata/manual/
  5. Re-run:  python scripts/acquire/iesh_microdata.py --offline
  Record in docs/README_acquisition.md: whether a login was needed, the file format,
  which rounds were available, and whether a city variable is present.
If DBIE has no IESH unit-level files, D39 falls back to the published city tables (iesh.py).
"""

# column-name harmonisation (lower-cased, stripped). Unknown names are kept and reported.
HARMONISE = {
    "round": ["round", "survey_round", "survey round", "round_no", "quarter", "survey_period", "period"],
    "city": ["city", "city_name", "centre", "center", "city name"],
    "perception": ["current_inflation", "current inflation", "perception", "q_current", "current_perception"],
    "exp_3m": ["three_month", "3 month", "3m", "three months ahead", "exp_3m", "three_months"],
    "exp_1y": ["one_year", "1 year", "1y", "one year ahead", "exp_1y"],
    "gender": ["gender", "sex"],
    "age": ["age", "age_group", "age group"],
    "category": ["category", "occupation", "respondent_category"],
    "weight": ["weight", "wt", "multiplier"],
}


def candidate_links(text: str, base: str) -> list[str]:
    urls = set()
    for m in re.finditer(r"""["']([^"']+\.(?:csv|xlsx?|zip))["']""", text, re.I):
        u = urljoin(base, m.group(1))
        if "rbi.org.in" in u:
            urls.add(u)
    return sorted(urls)


def scan_dbie(proj: Project, args) -> list[Path]:
    s = make_session()
    got = []
    home = fetch(proj, s, SOURCE, DBIE_HOME, dest_name="dbie_home.html", subdir="probe",
                 timeout=args.timeout, notes="DBIE landing page", skip_existing=False)
    if home is None:
        return got
    text = home.read_text(encoding="utf-8", errors="replace")
    scripts = re.findall(r"""<script[^>]+src=["']([^"']+\.js)["']""", text, re.I)
    hits = []
    for js in scripts[:20]:
        u = urljoin(DBIE_HOME, js)
        p = fetch(proj, s, SOURCE, u, subdir="probe/js", timeout=args.timeout,
                  notes="DBIE JS bundle (scanned for unit-level endpoints)")
        polite_sleep(args.sleep)
        if p is None:
            continue
        jt = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r".{0,80}(unit[-_ ]?level|IESH|inflation expectation).{0,120}", jt, re.I):
            hits.append(m.group(0)[:200])
        for c in candidate_links(jt, DBIE_HOME):
            fp = fetch(proj, s, SOURCE, c, subdir="auto", timeout=args.timeout,
                       notes="candidate unit-level file from JS bundle [UNVERIFIED]")
            if fp:
                got.append(fp)
            polite_sleep(args.sleep)
    write_json(proj.logs / "iesh_microdata_probe.json",
               {"home": DBIE_HOME, "scripts": scripts, "endpoint_hints": hits[:200]})
    print(f"probe: {len(scripts)} JS bundles, {len(hits)} text hints, {len(got)} files fetched "
          f"-> logs/iesh_microdata_probe.json")
    return got


def harmonise_cols(cols):
    mapping, unknown = {}, []
    for c in cols:
        lc = str(c).strip().lower()
        hit = next((k for k, alts in HARMONISE.items() if lc in alts or lc == k), None)
        if hit and hit not in mapping.values():
            mapping[c] = hit
        else:
            unknown.append(str(c))
    return mapping, unknown


def stack(proj: Project) -> dict:
    import pandas as pd
    files = []
    for sub in ("auto", "manual"):
        d = proj.raw_dir(SOURCE) / sub
        d.mkdir(exist_ok=True)
        files += [p for p in d.rglob("*") if p.is_file()]
    frames, report = [], {"files": [], "unknown_columns": {}}
    for f in files:
        try:
            if f.suffix.lower() == ".zip":
                ex = proj.root / "data" / "interim" / "iesh_microdata_unzipped" / f.stem
                ex.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(f) as z:
                    z.extractall(ex)
                inner = [p for p in ex.rglob("*") if p.suffix.lower() in (".csv", ".xlsx", ".xls")]
            else:
                inner = [f]
            for g in inner:
                if g.suffix.lower() == ".csv":
                    dfs = {"": pd.read_csv(g, low_memory=False)}
                elif g.suffix.lower() in (".xlsx", ".xls"):
                    dfs = pd.read_excel(g, sheet_name=None)
                else:
                    continue
                for sheet, df in dfs.items():
                    if df.shape[0] < 50:  # readme/codebook sheets
                        report["files"].append({"file": str(g.name), "sheet": sheet, "rows": int(df.shape[0]),
                                                "used": False})
                        continue
                    mapping, unknown = harmonise_cols(df.columns)
                    df = df.rename(columns=mapping)
                    df["_file"], df["_sheet"] = g.name, sheet
                    frames.append(df)
                    report["unknown_columns"][f"{g.name}:{sheet}"] = unknown
                    report["files"].append({"file": str(g.name), "sheet": sheet, "rows": int(df.shape[0]),
                                            "used": True, "recognised": sorted(set(mapping.values()))})
        except Exception as e:
            report["files"].append({"file": str(f.name), "error": f"{type(e).__name__}: {e}"})
    if frames:
        out = pd.concat(frames, ignore_index=True, sort=False)
        out.to_csv(proj.processed / "iesh_microdata_stacked.csv", index=False)
        report["n_rows"] = int(len(out))
        report["has_city"] = "city" in out.columns
        if "round" in out.columns:
            report["n_by_round"] = {str(k): int(v) for k, v in out["round"].value_counts().sort_index().items()}
    else:
        report["n_rows"] = 0
    return report


def main():
    p = base_parser(__doc__)
    p.add_argument("--offline", action="store_true", help="skip DBIE probing; only stack local files")
    args = p.parse_args()
    proj = Project(args.root)
    banner("IESH unit-level data (DBIE)")
    if not args.offline:
        scan_dbie(proj, args)
    rep = stack(proj)
    rep["d39_status"] = "microdata_available" if rep.get("n_rows") else "fallback_city_tables"
    write_json(proj.logs / "iesh_microdata_report.json", rep)
    if not rep.get("n_rows"):
        print("No unit-level IESH files found.")
        print(MANUAL)
        sys.exit(2)
    print(f"Stacked {rep['n_rows']} rows; city identifier present: {rep.get('has_city')}")
    print("Unrecognised columns per file are listed in logs/iesh_microdata_report.json; "
          "extend HARMONISE once the codebook is read.")


if __name__ == "__main__":
    main()
