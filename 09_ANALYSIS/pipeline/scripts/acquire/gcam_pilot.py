#!/usr/bin/env python3
"""D6 pilot: raw GKG + translation GKG files, MB/day, download-time projection, go/no-go;
and the GCAM codebook lookup for WordNet-Affect and Loughran-McDonald dimension IDs.

Steps
  0. Reachability: GET http://data.gdeltproject.org/gdeltv2/lastupdate.txt. If it fails -> NO-GO
     (D6: 'first test that the proxy reaches the GDELT file host').
  1. Master file lists (raw, untouched, to data/raw/gdelt_files/):
       http://data.gdeltproject.org/gdeltv2/masterfilelist.txt              (English stream)
       http://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt  (translation stream)
     Line format verified on lastupdate-translation.txt (Nov 2026): '<bytes> <md5> <url>', e.g.
       5522823 188bc9... http://data.gdeltproject.org/gdeltv2/20261116224500.translation.gkg.csv.zip
     [masterfilelist file names are standard GDELT 2.0 names; not fetched from this workspace]
  2. Download every 15-minute *.gkg.csv.zip and *.translation.gkg.csv.zip for the pilot days
     (default: 3 days spread over the sample), check md5, measure MB/day and throughput
     (MB/s), and time a full unzip+line scan per file (processing cost).
  3. Exact compressed bytes for scope 1 and scope 2 from the master-list sizes:
       scope 1: pre-fieldwork windows (--window-days, default 30) for rounds 2020-2026;
       scope 2: last 7 days before fieldwork, rounds 2022-2026.
     Fieldwork dates come from data/raw/iesh_rounds.csv (iesh.py). If that file is missing,
     the projection uses an explicit planning assumption (6 rounds a year, --assumed-days)
     and is labelled 'provisional' in the JSON.
  4. Go if projected download time <= 72 h of background running (D6), per scope.
  5. GCAM codebook: http://data.gdeltproject.org/documentation/GCAM-MASTER-CODEBOOK.TXT
     -> data/processed/gcam_ids.csv and docs/gcam_ids.md (rows whose dictionary is
     WordNet Affect 1.0/1.1 or Loughran and McDonald), regenerated from the file itself.

Output: logs/gcam_pilot.json
Usage: python scripts/acquire/gcam_pilot.py [--root PATH] [--days 2020-05-06 2023-07-12 2026-09-02]
                                           [--window-days 30] [--skip-download]
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import statistics
import time
import zipfile
from collections import defaultdict
from pathlib import Path

from acq_common import (Project, banner, base_parser, fetch, log_download, make_session, now_iso,
                        read_csv_rows, sha256_file, write_json)

SOURCE = "gdelt_files"
HOST = "http://data.gdeltproject.org"
LASTUPDATE = f"{HOST}/gdeltv2/lastupdate.txt"
MASTER = {"gkg": f"{HOST}/gdeltv2/masterfilelist.txt",
          "translation_gkg": f"{HOST}/gdeltv2/masterfilelist-translation.txt"}
SUFFIX = {"gkg": ".gkg.csv.zip", "translation_gkg": ".translation.gkg.csv.zip"}
CODEBOOK = f"{HOST}/documentation/GCAM-MASTER-CODEBOOK.TXT"
GO_HOURS = 72.0


def load_master(path: Path, suffix: str) -> dict[str, list[tuple[int, str, str]]]:
    """day 'YYYY-MM-DD' -> list of (bytes, md5, url) for files with this suffix."""
    by_day = defaultdict(list)
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) != 3 or not parts[2].endswith(suffix):
                continue
            if suffix == ".gkg.csv.zip" and parts[2].endswith(".translation.gkg.csv.zip"):
                continue
            stamp = parts[2].rsplit("/", 1)[-1][:8]
            try:
                day = dt.datetime.strptime(stamp, "%Y%m%d").date().isoformat()
                by_day[day].append((int(parts[0]), parts[1], parts[2]))
            except ValueError:
                continue
    return by_day


def md5_file(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def scan_seconds(p: Path) -> tuple[float, int]:
    t0 = time.time()
    n = 0
    with zipfile.ZipFile(p) as z:
        for name in z.namelist():
            with z.open(name) as fh:
                for line in io.TextIOWrapper(fh, encoding="utf-8", errors="replace"):
                    n += 1
    return time.time() - t0, n


def scope_days(proj: Project, window_days: int, start_year: int, end_year: int, assumed_days: int):
    f = proj.raw / "iesh_rounds.csv"
    days, provisional = set(), False
    if f.exists():
        for r in read_csv_rows(f):
            fs = r.get("fieldwork_start")
            if not fs:
                continue  # D3: no dates -> excluded, never imputed
            d0 = dt.date.fromisoformat(fs)
            if not (start_year <= d0.year <= end_year):
                continue
            for k in range(1, window_days + 1):
                days.add((d0 - dt.timedelta(days=k)).isoformat())
    if not days:
        provisional = True
        n_rounds = 6 * (end_year - start_year + 1)
        return None, n_rounds * min(window_days, assumed_days), provisional
    return sorted(days), len(days), provisional


def codebook(proj: Project, s, args) -> dict:
    p = fetch(proj, s, SOURCE, CODEBOOK, dest_name="GCAM-MASTER-CODEBOOK.TXT", subdir="docs",
              timeout=args.timeout, notes="GCAM codebook")
    if not p:
        return {"status": "codebook_not_downloaded"}
    rows = []
    with open(p, encoding="utf-8", errors="replace") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            name = (r.get("DictionaryHumanName") or "")
            if "wordnet affect" in name.lower() or "wordnet-affect" in name.lower() or "loughran" in name.lower():
                rows.append({k: r.get(k, "") for k in ("Variable", "DictionaryID", "DimensionID", "Type",
                                                       "LanguageCode", "DictionaryHumanName", "DimensionHumanName")})
    out = proj.processed / "gcam_ids.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["Variable"])
        w.writeheader()
        w.writerows(rows)
    lm = [r for r in rows if "loughran" in r["DictionaryHumanName"].lower()]
    wna = [r for r in rows if "wordnet" in r["DictionaryHumanName"].lower()]
    md = [f"# GCAM dimension IDs (regenerated by gcam_pilot.py on {now_iso()})", "",
          f"Source: {CODEBOOK} (sha256 {sha256_file(p)}). Status: VERIFIED from the codebook file.", "",
          "GKG field `GCAM` holds `cX.Y:count` (word counts) and, for scored dictionaries, `vX.Y:value`.", "",
          f"## Loughran and McDonald ({len(lm)} rows)", "", "| Variable | Dimension | Language |", "|---|---|---|"]
    md += [f"| {r['Variable']} | {r['DimensionHumanName']} | {r['LanguageCode']} |" for r in lm]
    md += ["", f"## WordNet Affect ({len(wna)} rows; 1.0 and 1.1)", "",
           "| Variable | Dictionary | Dimension |", "|---|---|---|"]
    md += [f"| {r['Variable']} | {r['DictionaryHumanName']} | {r['DimensionHumanName']} |" for r in wna]
    md += ["", "Full table: data/processed/gcam_ids.csv", ""]
    (proj.docs / "gcam_ids.md").write_text("\n".join(md), encoding="utf-8")
    return {"status": "ok", "n_loughran": len(lm), "n_wordnet_affect": len(wna),
            "loughran_vars": [r["Variable"] for r in lm]}


def main():
    p = base_parser(__doc__)
    p.add_argument("--days", nargs="+", default=["2020-05-06", "2023-07-12", "2026-09-02"])
    p.add_argument("--window-days", type=int, default=30, help="D4 ladder rung window (30/21/14)")
    p.add_argument("--assumed-days", type=int, default=30, help="only used if iesh_rounds.csv is missing")
    p.add_argument("--skip-download", action="store_true", help="use master-list sizes only")
    p.set_defaults(timeout=300.0, sleep=0.2)
    args = p.parse_args()
    proj = Project(args.root)
    s = make_session()
    banner("D6 GCAM raw-file pilot")
    res = {"run_at": now_iso(), "pilot_days": args.days, "go_threshold_hours": GO_HOURS}

    try:
        r = s.get(LASTUPDATE, timeout=30)
        res["host_reachable"] = r.status_code == 200
        log_download(proj, SOURCE, LASTUPDATE, r.status_code, len(r.content), "", "reachability")
    except Exception as e:
        res["host_reachable"] = False
        res["host_error"] = str(e)[:200]
        log_download(proj, SOURCE, LASTUPDATE, f"error:{type(e).__name__}", None, "", "reachability")
    if not res["host_reachable"]:
        res["decision"] = "NO-GO: GDELT file host not reachable (D6 step 1). V2Tone only."
        write_json(proj.logs / "gcam_pilot.json", res)
        print(res["decision"])
        return

    res["codebook"] = codebook(proj, s, args)
    masters = {}
    for k, u in MASTER.items():
        mp = fetch(proj, s, SOURCE, u, dest_name=u.rsplit("/", 1)[-1], subdir="master",
                   timeout=900, notes=f"master file list {k}", skip_existing=False)
        if mp:
            masters[k] = load_master(mp, SUFFIX[k])
    if not masters:
        res["decision"] = "NO-GO: master file lists not downloadable."
        write_json(proj.logs / "gcam_pilot.json", res)
        return

    # 1. MB/day from master lists over the whole span, and on pilot days
    stream_stats = {}
    for k, by_day in masters.items():
        mb = {d: sum(x[0] for x in v) / 1e6 for d, v in by_day.items()}
        recent = [v for d, v in mb.items() if d >= "2020-01-01"]
        stream_stats[k] = {"days_listed": len(mb), "median_mb_per_day_2020plus": statistics.median(recent) if recent else None,
                           "pilot_days_mb": {d: round(mb.get(d, 0), 1) for d in args.days},
                           "files_per_pilot_day": {d: len(by_day.get(d, [])) for d in args.days}}
    res["streams"] = stream_stats

    # 2. download pilot files, check md5, measure throughput and scan time
    thr = []
    scan = []
    if not args.skip_download:
        for k, by_day in masters.items():
            for d in args.days:
                for size, md5, url in by_day.get(d, []):
                    dest = proj.raw_dir(SOURCE) / "pilot" / d / url.rsplit("/", 1)[-1]
                    cached = dest.exists() and dest.stat().st_size > 0
                    t0 = time.time()
                    fp = fetch(proj, s, SOURCE, url, dest_name=url.rsplit("/", 1)[-1], subdir=f"pilot/{d}",
                               timeout=args.timeout, notes=f"D6 pilot {k}", skip_existing=True)
                    el = time.time() - t0
                    if not fp:
                        continue
                    if md5_file(fp) != md5:
                        log_download(proj, SOURCE, url, "md5_mismatch", fp.stat().st_size, "", "re-download needed")
                    if not cached and el > 0.05:
                        thr.append(size / 1e6 / el)
                    if len(scan) < 30:
                        try:
                            scan.append(scan_seconds(fp)[0])
                        except zipfile.BadZipFile:
                            log_download(proj, SOURCE, url, "bad_zip", fp.stat().st_size, "", "")
    res["throughput_mb_per_s_median"] = statistics.median(thr) if thr else None
    res["scan_seconds_per_file_median"] = statistics.median(scan) if scan else None

    # 3. projections
    mbps = res["throughput_mb_per_s_median"]
    proj_out = {}
    for name, (y0, y1, wd) in {"scope1": (2020, 2026, args.window_days), "scope2": (2022, 2026, 7)}.items():
        days, ndays, provisional = scope_days(proj, wd, y0, y1, args.assumed_days)
        tot_mb = 0.0
        files = 0
        for k, by_day in masters.items():
            if days:
                tot_mb += sum(x[0] for d in days for x in by_day.get(d, [])) / 1e6
                files += sum(len(by_day.get(d, [])) for d in days)
            else:
                med = stream_stats[k]["median_mb_per_day_2020plus"] or 0
                tot_mb += med * ndays
                files += 96 * ndays
        hours_dl = (tot_mb / mbps / 3600) if mbps else None
        hours_scan = (files * res["scan_seconds_per_file_median"] / 3600) if res["scan_seconds_per_file_median"] else None
        go = hours_dl is not None and hours_dl <= GO_HOURS
        proj_out[name] = {"years": [y0, y1], "window_days": wd, "n_days": ndays, "n_files": files,
                          "total_gb_compressed": round(tot_mb / 1000, 1),
                          "download_hours_projected": None if hours_dl is None else round(hours_dl, 1),
                          "scan_hours_projected": None if hours_scan is None else round(hours_scan, 1),
                          "provisional_dates": provisional, "go": go}
    res["projections"] = proj_out
    if proj_out["scope1"]["go"]:
        res["decision"] = "GO scope 1"
    elif proj_out["scope2"]["go"]:
        res["decision"] = "GO scope 2 (scope 1 fails the 72 h rule)"
    elif mbps is None:
        res["decision"] = "UNDECIDED: no throughput measured (run without --skip-download)"
    else:
        res["decision"] = "NO-GO: both scopes exceed 72 h; V2Tone only"
    if any(v["provisional_dates"] for v in proj_out.values()):
        res["decision"] += " [provisional: iesh_rounds.csv missing; re-run after iesh.py]"
    write_json(proj.logs / "gcam_pilot.json", res)
    print(f"throughput {mbps} MB/s; scope1 {proj_out['scope1']}; scope2 {proj_out['scope2']}")
    print("DECISION:", res["decision"])


if __name__ == "__main__":
    main()
