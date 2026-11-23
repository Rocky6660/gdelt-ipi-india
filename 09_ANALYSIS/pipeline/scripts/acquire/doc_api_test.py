#!/usr/bin/env python3
"""D8: day-1 test of the GDELT DOC 2.0 API (gated component).

Four logged queries (D8), each with mode=timelinevolraw, 2017-01-01 .. 2026-10-31:
  (i)   inflation sourcecountry:india
  (ii)  domain:thehindu.com                                   (operator-only denominator)
  (iii) theme:ECON_INFLATION domain:thehindu.com
  (iv)  (inflation OR "price rise" OR costlier OR dearness) sourcelang:hindi
        (the API searches English machine translations of non-English articles [V-C])

What is documented (GDELT blog 'GDELT DOC 2.0 API Debuts', read Nov 2026):
  base https://api.gdeltproject.org/api/v2/doc/doc ; parameters QUERY, MODE (timelinevol,
  timelinevolraw, ...), FORMAT (json, csv, ...), STARTDATETIME/ENDDATETIME as YYYYMMDDHHMMSS,
  TIMELINESMOOTH; timeline resolution: <72h -> 15 min, 72h-1 week -> hourly, >1 week -> daily.
  CONFLICT: the same post says the API 'searches back to January 1, 2017' but also that
  START/END must fall within the last 3 months. This test settles it empirically.
  No rate limit is documented. [UNVERIFIED] GDELT is reported to answer fast repeat calls
  with a plain-text 'Please limit requests to one every 5 seconds' message; the script
  records any such text and the response headers.
[UNVERIFIED] JSON layout of timelinevolraw: {"timeline":[{"series":..., "data":[{"date":
  "YYYYMMDDTHHMMSSZ","value":n,"norm":total}, ...]}]}. Parsed defensively; the raw body is
  always saved.

Pass rule (D8): a query passes if its series reaches back to January 2017 (first point
<= 2017-01-31) at daily or weekly resolution (median step <= 7 days) with non-zero values.
  overall_pass = (i) and (ii) and (iii) pass. (iv) is reported separately (Hindi/E2).
Output: logs/doc_api_test.json, raw responses in data/raw/doc_api/.

Usage: python scripts/acquire/doc_api_test.py [--root PATH] [--sleep 6]
"""
from __future__ import annotations

import datetime as dt
import json
import statistics
import time

from acq_common import Project, banner, base_parser, log_download, make_session, now_iso, sha256_bytes, write_json

SOURCE = "doc_api"
BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERIES = {
    "i_inflation_india": "inflation sourcecountry:india",
    "ii_domain_thehindu": "domain:thehindu.com",
    "iii_theme_inflation_thehindu": "theme:ECON_INFLATION domain:thehindu.com",
    "iv_hindi_keywords": '(inflation OR "price rise" OR costlier OR dearness) sourcelang:hindi',
}
START, END = "20170101000000", "20261031235959"


def parse_dates(js):
    pts = []
    for ser in (js.get("timeline") or []):
        for d in ser.get("data") or []:
            ds = str(d.get("date", ""))
            try:
                t = dt.datetime.strptime(ds[:15], "%Y%m%dT%H%M%S")
            except ValueError:
                try:
                    t = dt.datetime.strptime(ds[:8], "%Y%m%d")
                except ValueError:
                    continue
            pts.append((t, d.get("value"), d.get("norm")))
        break  # first series = article count
    return sorted(pts)


def run_one(proj, s, key, q, args):
    params = {"query": q, "mode": "timelinevolraw", "format": "json",
              "startdatetime": START, "enddatetime": END}
    rec = {"key": key, "query": q, "params": params, "requested_at": now_iso()}
    t0 = time.time()
    try:
        r = s.get(BASE, params=params, timeout=args.timeout)
    except Exception as e:
        rec.update(status=f"error:{type(e).__name__}", error=str(e)[:300], passed=False)
        log_download(proj, SOURCE, BASE, rec["status"], None, "", key)
        return rec
    body = r.content
    rec.update(status=r.status_code, latency_s=round(time.time() - t0, 2), bytes=len(body),
               headers={k: v for k, v in r.headers.items()
                        if k.lower() in ("retry-after", "x-ratelimit-limit", "x-ratelimit-remaining",
                                         "content-type", "date", "server")})
    out = proj.raw_dir(SOURCE) / f"{key}.json"
    out.write_bytes(body)
    log_download(proj, SOURCE, r.url, r.status_code, len(body), sha256_bytes(body), key)
    text = body[:400].decode("utf-8", "replace")
    if not text.strip().startswith("{") and ("limit" in text.lower() or "rate" in text.lower()):
        rec["rate_limit_message"] = text.strip()[:300]
    try:
        js = json.loads(body.decode("utf-8", "replace") or "{}")
    except ValueError:
        rec.update(parse_error="non-JSON body", body_head=text[:300], passed=False)
        return rec
    pts = parse_dates(js)
    if not pts:
        rec.update(n_points=0, passed=False, note="no timeline points")
        return rec
    steps = [(b[0] - a[0]).total_seconds() / 86400 for a, b in zip(pts, pts[1:])]
    med = statistics.median(steps) if steps else None
    first, last = pts[0][0], pts[-1][0]
    nonzero = sum(1 for p in pts if (p[1] or 0) > 0)
    norm_present = any(p[2] is not None for p in pts)
    rec.update(n_points=len(pts), first_date=first.date().isoformat(), last_date=last.date().isoformat(),
               median_step_days=med,
               resolution=("15min" if med and med < 0.02 else "hourly" if med and med < 0.5 else
                           "daily" if med and med <= 1.5 else "weekly" if med and med <= 7.5 else
                           "monthly_or_coarser"),
               share_nonzero=round(nonzero / len(pts), 3), norm_field_present=norm_present,
               depth_ok=first <= dt.datetime(2017, 1, 31), resolution_ok=bool(med and med <= 7.5))
    rec["passed"] = bool(rec["depth_ok"] and rec["resolution_ok"] and nonzero > 0)
    return rec


def rate_probe(proj, s, args):
    """Two back-to-back cheap requests to see whether GDELT throttles (D8: log the rate limit)."""
    res = []
    for k in range(2):
        try:
            r = s.get(BASE, params={"query": "inflation", "mode": "timelinevolraw", "format": "json",
                                    "timespan": "1d"}, timeout=args.timeout)
            res.append({"try": k, "status": r.status_code, "head": r.text[:160]})
            log_download(proj, SOURCE, r.url, r.status_code, len(r.content), sha256_bytes(r.content),
                         f"rate probe {k}")
        except Exception as e:
            res.append({"try": k, "status": f"error:{type(e).__name__}"})
    throttled = any("limit" in str(x.get("head", "")).lower() or x.get("status") == 429 for x in res)
    return {"back_to_back": res, "throttled_without_pause": throttled}


def main():
    p = base_parser(__doc__)
    p.set_defaults(sleep=6.0, timeout=120.0)
    args = p.parse_args()
    proj = Project(args.root)
    s = make_session(retries=1)
    banner("D8 DOC 2.0 API test")
    results = []
    for key, q in QUERIES.items():
        rec = run_one(proj, s, key, q, args)
        results.append(rec)
        print(f"{key:30s} status={rec.get('status')} points={rec.get('n_points')} "
              f"first={rec.get('first_date')} res={rec.get('resolution')} pass={rec.get('passed')}")
        time.sleep(args.sleep)
    rate = rate_probe(proj, s, args)
    by = {r["key"]: r for r in results}
    overall = all(by[k].get("passed") for k in ("i_inflation_india", "ii_domain_thehindu",
                                                "iii_theme_inflation_thehindu"))
    summary = {"tested_at": now_iso(), "overall_pass": overall,
               "hindi_query_pass": by["iv_hindi_keywords"].get("passed"),
               "pause_between_queries_s": args.sleep, "rate_limit": rate,
               "decision": ("PASS: build keyword IPI, outlet theme series, E3 item series, E3 direction FV"
                            if overall else
                            "FAIL: use named fallbacks (Trends for validation; Trends + GKG item themes for "
                            "E3 weights; E3 direction cut). No Phase-1 element depends on DOC."),
               "queries": results}
    write_json(proj.logs / "doc_api_test.json", summary)
    print(f"overall_pass={overall}; rate limit throttled without pause: {rate['throttled_without_pause']}")
    print("wrote logs/doc_api_test.json")


if __name__ == "__main__":
    main()
