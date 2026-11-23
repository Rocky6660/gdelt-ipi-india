#!/usr/bin/env python3
"""Reachability check for every host the project needs (run this first).

For each host: DNS lookup, HTTPS request (GET, small, redirects not followed),
status code, latency. Behind an HTTP proxy, DNS may fail locally while HTTPS
works through the proxy, so the verdict is based on the HTTPS result.

Outputs:
  * a table on stdout;
  * logs/net_check.json (one record per host, plus a summary);
  * one line per host in logs/acquisition_log.csv (source = net_check).

Usage:  python scripts/acquire/net_check.py [--root PATH] [--timeout 15]
"""
from __future__ import annotations

import socket
import time

from acq_common import Project, base_parser, log_download, make_session, now_iso, write_json

# (host, test URL, what the project needs it for, decision IDs)
HOSTS = [
    ("data.gdeltproject.org", "http://data.gdeltproject.org/gdeltv2/lastupdate.txt",
     "GKG raw 15-min files, masterfile lists, GCAM codebook", "D6"),
    ("api.gdeltproject.org", "https://api.gdeltproject.org/api/v2/doc/doc?query=inflation&mode=timelinevolraw&format=json&timespan=1d",
     "DOC 2.0 API", "D8"),
    ("blog.gdeltproject.org", "https://blog.gdeltproject.org/", "GDELT documentation", "D6,D8"),
    ("rbi.org.in", "https://rbi.org.in/", "IESH releases (legacy Scripts/ pages)", "D3,D7"),
    ("www.rbi.org.in", "https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=24089",
     "IESH release pages", "D3,D7"),
    ("website.rbi.org.in", "https://website.rbi.org.in/", "new RBI website", "D7"),
    ("rbidocs.rbi.org.in", "https://rbidocs.rbi.org.in/", "IESH Excel/PDF attachments", "D7"),
    ("data.rbi.org.in", "https://data.rbi.org.in/DBIE/", "DBIE (unit-level IESH, policy rates)", "D7,D39"),
    ("mospi.gov.in", "https://mospi.gov.in/", "CPI releases", "D7"),
    ("www.mospi.gov.in", "https://www.mospi.gov.in/", "CPI releases", "D7"),
    ("esankhyiki.mospi.gov.in", "https://esankhyiki.mospi.gov.in/", "CPI downloads (portal)", "D7"),
    ("api.mospi.gov.in", "https://api.mospi.gov.in/", "CPI API (getCPIIndex/getItemIndex)", "D7,D26"),
    ("trends.google.com", "https://trends.google.com/trends/", "Google Trends (pytrends)", "D7,D17,D26"),
    ("bigquery.googleapis.com", "https://bigquery.googleapis.com/discovery/v1/apis/bigquery/v2/rest",
     "BigQuery sandbox", "D1,D4"),
    ("oauth2.googleapis.com", "https://oauth2.googleapis.com/", "Google auth", "D4"),
    ("accounts.google.com", "https://accounts.google.com/", "Google auth", "D4"),
    ("web.archive.org", "https://web.archive.org/", "archived pages (audit Mode A, fallbacks)", "D16,D38"),
    ("archive.org", "https://archive.org/", "Internet Archive", "D16"),
    ("ceda.ashoka.edu.in", "https://ceda.ashoka.edu.in/", "CEDA (Ashoka) main site", "D38"),
    ("dca.ceda.ashoka.edu.in", "https://dca.ceda.ashoka.edu.in/", "CEDA DoCA cleaned price mirror", "D38"),
    ("fcainfoweb.nic.in", "https://fcainfoweb.nic.in/reports/report_menu_web.aspx", "DoCA price reports", "D38"),
    ("consumeraffairs.nic.in", "https://consumeraffairs.nic.in/", "DoCA Price Monitoring Division", "D38"),
    ("ppac.gov.in", "https://ppac.gov.in/", "pump prices (optional control)", "D38"),
    ("fred.stlouisfed.org", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU",
     "Brent, INR/USD, 10y G-sec (fallback)", "D7"),
    ("api.anthropic.com", "https://api.anthropic.com/", "LLM classifier/audit", "D9,D15"),
    ("pypi.org", "https://pypi.org/simple/pytrends/", "package installs", "-"),
]


def check(session, host: str, url: str, timeout: float) -> dict:
    rec = {"host": host, "url": url, "dns": None, "dns_ip": None, "http_status": None,
           "latency_ms": None, "error": None, "reachable": False}
    try:
        rec["dns_ip"] = socket.gethostbyname(host)
        rec["dns"] = "ok"
    except Exception as e:
        rec["dns"] = f"fail:{type(e).__name__}"
    t0 = time.time()
    try:
        r = session.get(url, timeout=timeout, allow_redirects=False, stream=True)
        rec["http_status"] = r.status_code
        r.close()
        # Any HTTP answer from the host (incl. 3xx/4xx) proves the host is reachable.
        # A 403 can be a WAF/captcha page: flagged so the user checks it in a browser.
        rec["reachable"] = r.status_code < 500
        if r.status_code in (403, 429):
            rec["error"] = "reached, but blocked/rate-limited (WAF or captcha?)"
    except Exception as e:
        rec["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    rec["latency_ms"] = int((time.time() - t0) * 1000)
    return rec


def main() -> None:
    p = base_parser(__doc__)
    p.set_defaults(timeout=15.0)
    args = p.parse_args()
    proj = Project(args.root)
    session = make_session(retries=0)
    results = []
    print(f"{'host':28s} {'dns':10s} {'http':5s} {'ms':>6s}  verdict  purpose")
    print("-" * 100)
    for host, url, purpose, dec in HOSTS:
        rec = check(session, host, url, args.timeout)
        rec.update({"purpose": purpose, "decisions": dec})
        results.append(rec)
        verdict = "OK" if rec["reachable"] else "FAIL"
        print(f"{host:28s} {str(rec['dns'])[:10]:10s} {str(rec['http_status'] or '-'):5s} "
              f"{rec['latency_ms']:6d}  {verdict:7s}  {purpose[:40]}"
              + (f"  [{rec['error'][:60]}]" if rec["error"] else ""))
        log_download(proj, "net_check", url, rec["http_status"] or "error", None, "",
                     f"{verdict} {rec['error'] or ''}")
    summary = {
        "checked_at": now_iso(),
        "n_hosts": len(results),
        "n_reachable": sum(r["reachable"] for r in results),
        "unreachable": [r["host"] for r in results if not r["reachable"]],
        "gates": {
            "D6_gcam_pilot_possible": next(r["reachable"] for r in results if r["host"] == "data.gdeltproject.org"),
            "D8_doc_api_possible": next(r["reachable"] for r in results if r["host"] == "api.gdeltproject.org"),
        },
    }
    write_json(proj.logs / "net_check.json", {"summary": summary, "hosts": results})
    print("-" * 100)
    print(f"{summary['n_reachable']}/{summary['n_hosts']} hosts reachable. "
          f"Unreachable: {', '.join(summary['unreachable']) or 'none'}")
    print(f"Wrote {proj.logs / 'net_check.json'}")


if __name__ == "__main__":
    main()
