"""Build the final IESH round list and the national series (user ruling (b), 21 Nov 2026).

* National series for every round comes from RBI's own time-series Excel (IESHddmmyyyy.xlsx, sheet
  'T2 Household IE'): mean / median / SD for current, 3-month and 1-year, plus SEs (from Sep 2018).
* Fieldwork start: the exact date scraped from the release where RBI states it (2020 onwards).
  Where RBI gives only the 'survey period ended' month (pre-2020 releases), the round gets the
  pre-registered MONTH RULE: fieldwork_start := 1st day of the survey-ended month, so the news window
  (window_days ending the day before fieldwork_start) ends on the last day of the previous month.
  Such rounds carry fs_rule = 'month_rule' and are tested in a 2020+-only robustness check.

Usage: python scripts/acquire/iesh_merge_rounds.py --root PIPE --excel PATH_TO_IESH_xlsx
Writes data/raw/iesh_rounds.csv (previous file kept as data/raw/iesh_rounds_scraped.csv) and
data/processed/iesh_national_excel.csv.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import shutil
from pathlib import Path

import openpyxl

START = dt.date(2015, 1, 1)


def parse_t2(xlsx: Path) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    rows = list(wb["T2 Household IE"].iter_rows(values_only=True))
    out, last = [], None
    names = ["cur_mean", "cur_median", "cur_sd", "m3_mean", "m3_median", "m3_sd", "y1_mean", "y1_median", "y1_sd"]
    for r in rows:
        r = list(r) + [None] * 14
        rid, ended, vals = r[1], r[2], r[3:12]
        if isinstance(ended, dt.datetime) and rid is not None:
            rec = {"round_no": str(rid).strip(), "survey_ended": ended.date().strftime("%Y-%m")}
            for k, v in zip(names, vals):
                rec[k] = v if isinstance(v, (int, float)) else ""
            out.append(rec)
            last = rec
        elif last is not None and rid is None and ended is None and isinstance(vals[0], str) and vals[0].startswith("["):
            for k, v in zip(names, vals):
                m = re.match(r"\[([\d.]+)\]", str(v or ""))
                last[k.replace("_mean", "_mean_se").replace("_median", "_median_se").replace("_sd", "_sd_se")] = \
                    float(m.group(1)) if m else ""
            last = None
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--excel", type=Path, required=True)
    a = ap.parse_args()
    t2 = parse_t2(a.excel)
    proc = a.root / "data/processed"
    cols = sorted({k for r in t2 for k in r}, key=lambda k: (k not in ("round_no", "survey_ended"), k))
    with open(proc / "iesh_national_excel.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(t2)

    raw = a.root / "data/raw/iesh_rounds.csv"
    keep = a.root / "data/raw/iesh_rounds_scraped.csv"
    if not keep.exists():
        shutil.copy(raw, keep)
    scraped = list(csv.DictReader(open(keep, newline="")))
    exact = {}
    for s in scraped:
        if s.get("round") and (s.get("fieldwork_start") or "").strip():
            exact.setdefault(s["round"], s)
    info = {}
    for s in scraped:
        if s.get("round"):
            info.setdefault(s["round"], s)
    fields = list(scraped[0].keys()) + ["round_no", "fs_rule"]
    rows = []
    for r in t2:
        ended = dt.date.fromisoformat(r["survey_ended"] + "-01")
        if ended < START:
            continue
        key = r["survey_ended"]
        base = dict(exact.get(key) or info.get(key) or {k: "" for k in scraped[0]})
        base["round"] = key
        base["round_no"] = r["round_no"]
        if key in exact:
            base["fs_rule"] = "exact"
        else:
            base["fieldwork_start"] = ended.isoformat()
            base["fieldwork_end"] = ""
            base["fs_rule"] = "month_rule"
        rows.append(base)
    with open(raw, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    n_ex = sum(r["fs_rule"] == "exact" for r in rows)
    print(f"rounds from {START}: {len(rows)} (exact dates {n_ex}, month rule {len(rows) - n_ex}); "
          f"national series rows {len(t2)}")


if __name__ == "__main__":
    main()
