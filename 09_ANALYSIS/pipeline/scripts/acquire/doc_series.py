"""GDELT DOC 2.0 series (D8 PASS by user ruling 23 Nov 2026; build what is feasible).

The API allows one request per 5 s and drops about half of the connections, so every call is spaced (--gap, default
8 s), retried with back-off (up to --tries), and its raw JSON is cached under data/raw/doc_api/series/ (a cached
response is never re-requested). Failures are logged, never filled in.

Jobs
  national   timelinevolraw, 2017-01-01..2026-10-31 (daily): denominator `sourcecountry:india`; keyword numerator
             `(inflation OR "price rise" OR "price hike" OR costlier OR dearness) sourcecountry:india` (English
             terms: the API searches machine translations, D8); theme numerator `theme:ECON_INFLATION sourcecountry:india`.
  items      timelinevolraw per E3 item, price-phrase queries, `sourcecountry:india` (D26 attention m_i,t).
  precision  artlist samples for the D26 precision check: 4 seeded months x 5 articles = 20 headlines per item
             (judged afterwards; items with precision < 0.5 are dropped).
Outputs
  data/processed/doc/doc_daily.csv        series, date, value, norm
  data/processed/doc/doc_precision_sample.csv   item, month, title, url, domain, language, seendate
  logs/doc_series_log.csv                 one row per attempt
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import requests

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
UA = {"User-Agent": "research-data-acquisition/1.0 (academic project)"}
START, END = "20170101000000", "20261031235959"
NATIONAL = {
    "den_india": "sourcecountry:india",
    "kw_inflation": '(inflation OR "price rise" OR "price hike" OR costlier OR dearness) sourcecountry:india',
    "theme_inflation": "theme:ECON_INFLATION sourcecountry:india",
}
# E3 items (D26): price phrase required; CPI item names are matched in the E3 script.
ITEMS = {
    "onion": '("onion price" OR "onion prices") sourcecountry:india',
    "tomato": '("tomato price" OR "tomato prices") sourcecountry:india',
    "potato": '("potato price" OR "potato prices") sourcecountry:india',
    "petrol": '("petrol price" OR "petrol prices") sourcecountry:india',
    "diesel": '("diesel price" OR "diesel prices") sourcecountry:india',
    "lpg": '("LPG price" OR "cylinder price" OR "LPG cylinder price") sourcecountry:india',
    "milk": '("milk price" OR "milk prices") sourcecountry:india',
    "pulses": '("dal price" OR "dal prices" OR "pulses price" OR "pulses prices" OR "tur dal") sourcecountry:india',
    "wheat_atta": '("wheat price" OR "wheat prices" OR "atta price" OR "flour price") sourcecountry:india',
    "rice": '("rice price" OR "rice prices") sourcecountry:india',
    "edible_oil": '("edible oil price" OR "edible oil prices" OR "cooking oil price" OR "mustard oil price") sourcecountry:india',
    "vegetables": '("vegetable prices" OR "vegetable price") sourcecountry:india',
}


def key(params: dict) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]


class Client:
    def __init__(self, root: Path, gap: float, tries: int):
        self.cache = root / "data/raw/doc_api/series"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.log = root / "logs/doc_series_log.csv"
        self.gap, self.tries, self.last = gap, tries, 0.0

    def _log(self, name, params, status, note=""):
        new = not self.log.exists()
        with open(self.log, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["timestamp", "name", "query", "mode", "status", "note"])
            w.writerow([dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), name, params["query"],
                        params["mode"], status, note[:200]])

    def get(self, name: str, params: dict):
        p = self.cache / f"{name}__{key(params)}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        for t in range(self.tries):
            wait = self.gap - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                r = requests.get(BASE, params=params, headers=UA, timeout=120)
            except Exception as e:  # connection reset / timeout
                self._log(name, params, f"error:{type(e).__name__}", f"try {t + 1}")
                time.sleep(min(60, 10 * (t + 1)))
                continue
            if r.status_code == 429:
                self._log(name, params, "429", f"try {t + 1}")
                time.sleep(min(90, 15 * (t + 1)))
                continue
            if r.status_code != 200:
                self._log(name, params, str(r.status_code), r.text[:150])
                time.sleep(10)
                continue
            try:
                js = json.loads(r.text) if r.text.strip() else {}
            except json.JSONDecodeError:
                self._log(name, params, "bad_json", r.text[:150])
                continue
            p.write_text(json.dumps(js), encoding="utf-8")
            self._log(name, params, "200", f"try {t + 1}")
            return js
        self._log(name, params, "GAVE_UP", f"{self.tries} tries")
        return None


def timeline_rows(name: str, js) -> list[dict]:
    rows = []
    for s in (js or {}).get("timeline", []):
        for d in s.get("data", []):
            rows.append({"series": name, "date": d["date"][:8], "value": d.get("value"), "norm": d.get("norm")})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--jobs", default="national,items,precision")
    ap.add_argument("--gap", type=float, default=8.0)
    ap.add_argument("--tries", type=int, default=8)
    a = ap.parse_args()
    c = Client(a.root, a.gap, a.tries)
    out = a.root / "data/processed/doc"
    out.mkdir(parents=True, exist_ok=True)
    jobs = set(a.jobs.split(","))
    rows, failed = [], []
    tl = {}
    if "national" in jobs:
        tl.update(NATIONAL)
    if "items" in jobs:
        tl.update({f"item_{k}": v for k, v in ITEMS.items()})
    for name, q in tl.items():
        js = c.get(name, {"query": q, "mode": "timelinevolraw", "format": "json",
                          "startdatetime": START, "enddatetime": END})
        r = timeline_rows(name, js)
        if not r:
            failed.append(name)
        rows += r
        print(f"{name}: {len(r)} points", flush=True)
    if rows:
        with open(out / "doc_daily.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["series", "date", "value", "norm"])
            w.writeheader(); w.writerows(rows)
    prec = []
    if "precision" in jobs:
        months = [f"{y}{m:02d}" for y in range(2017, 2026) for m in range(1, 13)]
        for item, q in ITEMS.items():
            for mth in sorted(random.Random(f"20261123-{item}").sample(months, 4)):
                y, m = int(mth[:4]), int(mth[4:])
                last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
                js = c.get(f"prec_{item}_{mth}", {"query": q, "mode": "artlist", "format": "json", "maxrecords": "5",
                                                   "sort": "hybridrel", "startdatetime": f"{mth}01000000",
                                                   "enddatetime": f"{mth}{last:02d}235959"})
                for art in (js or {}).get("articles", []):
                    prec.append({"item": item, "month": mth, "title": art.get("title"), "url": art.get("url"),
                                 "domain": art.get("domain"), "language": art.get("language"),
                                 "seendate": art.get("seendate")})
                if js is None:
                    failed.append(f"prec_{item}_{mth}")
            print(f"precision sample {item}: {sum(p['item'] == item for p in prec)} headlines", flush=True)
        with open(out / "doc_precision_sample.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["item", "month", "title", "url", "domain", "language", "seendate"])
            w.writeheader(); w.writerows(prec)
    (out / "doc_failed.json").write_text(json.dumps(failed, indent=1))
    print(f"done; failed: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
