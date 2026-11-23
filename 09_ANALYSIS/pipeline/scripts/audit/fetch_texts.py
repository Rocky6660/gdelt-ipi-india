#!/usr/bin/env python3
"""Retrieve audit article texts (Mode A, validation only), logging every attempt.

Order per article: live fetch -> Wayback Machine (availability API, then the snapshot) -> optional
NGrams fallback (2020+ only; STUB, see fetch_ngrams_text). Main text is extracted with trafilatura.
Texts go to data/raw/audit_texts/<audit_id>.txt. Every attempt, success or failure, is appended to
logs/audit_retrieval_log.csv with columns
  audit_id,url,mode,http_status,success,chars,error,timestamp_utc,snapshot_url
Use is for validation only, never for index construction. --max-success (default: no cap; the user's
decision on ~400 vs the full sample is pending) stops the run once that many texts are saved
(counting texts already in the log).

Soft failures are logged as failures, not successes: redirects to a home/section page, extracted text
that is very short or boilerplate (paywall, cookie wall, 404 text), and Wayback snapshots more than
--max-snapshot-days (default 30) from the GKG date or whose capture status is not 200. Articles are processed in `fetch_rank` order (human subsample
first, then strata interleaved). Re-running resumes: ids with a logged success are skipped.

Politeness: descriptive User-Agent (optionally AUDIT_CONTACT env var for a contact URL/email;
none is hard-coded), robots.txt respected for live fetches (RFC 9309: 4xx = allow; 5xx or unreachable = disallow), per-host minimum delay, global delay,
timeouts, no retries beyond one per mode. Wayback requests use the id_ snapshot form (raw page).
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse

MIN_CHARS = 300  # below this the text is treated as a failed extraction (paywall stub, cookie wall, error page)
LOG_FIELDS = ["audit_id", "url", "mode", "http_status", "success", "chars", "error", "timestamp_utc", "snapshot_url"]


def user_agent() -> str:
    contact = os.environ.get("AUDIT_CONTACT", "").strip()
    base = "AcademicValidationAuditBot/1.0 (research; low-volume; single fetch per URL)"
    return f"{base} {contact}" if contact else base


class Throttle:
    def __init__(self, per_host: float, global_delay: float):
        self.per_host, self.global_delay = per_host, global_delay
        self.last_host: dict[str, float] = {}
        self.last_any = 0.0

    def wait(self, host: str):
        now = time.monotonic()
        need = max(self.last_host.get(host, 0) + self.per_host, self.last_any + self.global_delay) - now
        if need > 0:
            time.sleep(need)
        t = time.monotonic()
        self.last_host[host] = t
        self.last_any = t


def extract_text(html: str, url: str | None = None) -> str:
    """Main-text extraction with trafilatura; falls back to readability if installed."""
    try:
        import trafilatura
        txt = trafilatura.extract(html, url=url, include_comments=False, include_tables=False, favor_recall=True)
        if txt:
            return txt.strip()
    except ImportError:
        pass
    try:
        from readability import Document
        import re as _re
        body = Document(html).summary()
        return _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", body)).strip()
    except ImportError:
        return ""


BOILERPLATE = ["subscribe to continue", "subscribe to read", "enable javascript", "accept cookies", "page not found",
               "404 not found", "access denied", "sign in to read", "log in to continue", "verify you are human",
               "this content is for subscribers", "captcha"]


def boilerplate_hit(text: str):
    t = text.lower()
    if len(t) < 1500:
        for pat in BOILERPLATE:
            if pat in t:
                return pat
    if len(t) < 3000 and ("page not found" in t or "404 not found" in t):
        return "page not found"
    return None


def redirect_suspicious(orig: str, final: str) -> bool:
    """True if a redirect landed on a home/section page rather than the article."""
    po, pf = urlparse(orig).path.rstrip("/"), urlparse(final).path.rstrip("/")
    if pf == "" and po != "":
        return True  # landed on the site root
    if po == pf:
        return False
    segs = [x for x in po.split("/") if x]
    last = segs[-1].lower() if segs else ""
    return len(last) >= 8 and last not in pf.lower()


def snapshot_days_from(snapshot_url: str, gkg_date: str):
    m = re.search(r"/web/(\d{14})", snapshot_url or "")
    if not m or not gkg_date:
        return None
    a = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
    b = datetime.strptime(str(gkg_date)[:14].ljust(14, "0"), "%Y%m%d%H%M%S")
    return abs((a - b).total_seconds()) / 86400


def log_row(path: Path, row: dict):
    new = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in LOG_FIELDS})


def _row(audit_id, url, mode, status, success, chars, error, snap=""):
    return {"audit_id": audit_id, "url": url, "mode": mode, "http_status": status, "success": bool(success),
            "chars": chars, "error": error, "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "snapshot_url": snap}


def robots_allows(url: str, ua: str, cache: dict, session, timeout: float, throttle=None):
    """RFC 9309: 2xx parse; 4xx = no robots (allow); 5xx or unreachable = complete disallow.

    Returns (allowed, reason)."""
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in cache:
        rp = robotparser.RobotFileParser()
        state = "ok"
        try:
            if throttle:
                throttle.wait(p.netloc)
            r = session.get(root + "/robots.txt", timeout=timeout, headers={"User-Agent": ua})
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            elif 400 <= r.status_code < 500:
                rp.parse([])
            else:
                state = f"robots_http_{r.status_code}_disallow"
        except Exception as e:
            state = f"robots_unreachable_disallow:{type(e).__name__}"
        cache[root] = (rp, state)
    rp, state = cache[root]
    if state != "ok":
        return False, state
    return (True, "") if rp.can_fetch(ua, url) else (False, "robots_disallowed")


def get_and_extract(session, url, ua, timeout, orig_url=None):
    """Return (status, text, error). Soft failures return a non-empty error."""
    import requests
    try:
        r = session.get(url, timeout=timeout, headers={"User-Agent": ua, "Accept-Language": "en,hi;q=0.8"}, allow_redirects=True)
    except requests.RequestException as e:
        return "", "", f"{type(e).__name__}: {str(e)[:150]}"
    if r.status_code != 200:
        return r.status_code, "", f"http_{r.status_code}"
    ctype = r.headers.get("Content-Type", "")
    if "html" not in ctype and "text" not in ctype:
        return r.status_code, "", f"non_text_content_type:{ctype[:40]}"
    final = getattr(r, "url", None)
    if orig_url and final and isinstance(final, str) and redirect_suspicious(orig_url, final):
        return r.status_code, "", f"redirect_to_home_or_section:{final[:120]}"
    r.encoding = r.encoding if r.encoding and r.encoding.lower() != "iso-8859-1" else r.apparent_encoding
    try:
        text = extract_text(r.text, url)
    except Exception as e:  # extraction must never stop the run
        return r.status_code, "", f"extract_exception:{type(e).__name__}"
    if len(text) < MIN_CHARS:
        return r.status_code, text, f"extracted_too_short({len(text)}<{MIN_CHARS})"
    bp = boilerplate_hit(text)
    if bp:
        return r.status_code, text, f"boilerplate:{bp}"
    return r.status_code, text, ""


def wayback_snapshot(session, url, gkg_date, ua, timeout, max_days=30.0):
    """Availability API; returns (status, snapshot_url or '', error)."""
    import requests
    ts = (gkg_date or "")[:14]
    try:
        r = session.get("https://archive.org/wayback/available", params={"url": url, "timestamp": ts},
                        timeout=timeout, headers={"User-Agent": ua})
    except requests.RequestException as e:
        return "", "", f"{type(e).__name__}: {str(e)[:150]}"
    if r.status_code != 200:
        return r.status_code, "", f"availability_http_{r.status_code}"
    try:
        snap = r.json().get("archived_snapshots", {}).get("closest", {})
    except ValueError:
        return r.status_code, "", "availability_bad_json"
    if not snap or not snap.get("available"):
        return r.status_code, "", "no_snapshot"
    if str(snap.get("status", "200")) != "200":
        return r.status_code, "", f"snapshot_capture_status_{snap.get('status')}"
    su = snap["url"]
    days = snapshot_days_from(su, gkg_date)
    if days is not None and max_days is not None and days > max_days:
        return r.status_code, "", f"snapshot_too_far({days:.0f}d>{max_days:.0f}d)"
    su = re.sub(r"(/web/\d{14})/", r"\1id_/", su, count=1)  # raw capture without the Wayback toolbar
    return r.status_code, su.replace("http://", "https://", 1), ""


def fetch_ngrams_text(url: str, gkg_date: str) -> str:
    """STUB. Fallback for 2020+ articles that fail live and Wayback (D16 Mode B text).

    Intended procedure (not implemented; the retrieval cost is UNVERIFIED, see disputes.md D16):
      1. From the GKG timestamp (YYYYMMDDHHMMSS) list the Web News NGrams 3.0 minute files for the
         surrounding window (GDELT publishes per-minute files; the exact path pattern must be
         confirmed from the GDELT site, e.g. under data.gdeltproject.org/gdeltv3/webngrams/).
      2. Download only those minute files (cap the number of days via the seeded window-day set; use
         the BigQuery NGrams table only if a one-day dry run is within the 60 GB reserve).
      3. Keep records whose `url` equals the article URL and stitch the n-gram fragments in `pos`
         order into approximate running text.
      4. Return the text with a first line "[APPROXIMATE TEXT RECONSTRUCTED FROM NGRAMS]" so the
         coder and the metrics can see that it is not the original text. retrieval mode = ngrams_approx.
    Until implemented this raises NotImplementedError and the attempt is logged as a failure.
    """
    raise NotImplementedError("NGrams retrieval is a documented stub; see docstring")


def read_log_state(path: Path):
    done, n_success = set(), 0
    if path.exists():
        import pandas as pd
        lg = pd.read_csv(path, dtype=str)
        ok = lg[lg["success"].str.lower() == "true"]
        done = set(ok["audit_id"])
        n_success = len(done)
    return done, n_success


def update_sheet(sheet_path: Path, log_path: Path, text_dir: str):
    import pandas as pd
    sh = pd.read_csv(sheet_path, dtype=str).fillna("")
    lg = pd.read_csv(log_path, dtype=str)
    ok = lg[lg["success"].str.lower() == "true"].drop_duplicates("audit_id", keep="last").set_index("audit_id")["mode"]
    sh["retrieval_mode"] = sh["audit_id"].map(ok).fillna("")
    sh.to_csv(sheet_path, index=False)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default="data/interim/audit/audit_manifest.csv")
    ap.add_argument("--out-dir", default="data/raw/audit_texts")
    ap.add_argument("--log", default="logs/audit_retrieval_log.csv")
    ap.add_argument("--max-success", type=int, default=None, help="optional ceiling on saved texts (default: none; pending user decision on 400 vs full)")
    ap.add_argument("--max-snapshot-days", type=float, default=30.0)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--per-host-delay", type=float, default=5.0)
    ap.add_argument("--global-delay", type=float, default=1.5)
    ap.add_argument("--no-live", action="store_true", help="skip live fetch (Wayback only)")
    ap.add_argument("--ngrams-fallback", action="store_true", help="try the NGrams stub for 2020+ failures (currently logs a failure)")
    ap.add_argument("--limit", type=int, default=None, help="process at most this many articles this run")
    ap.add_argument("--update-sheet", default=None, help="fill retrieval_mode in this coder sheet from the log and exit")
    a = ap.parse_args(argv)

    log_path = Path(a.log)
    if a.update_sheet:
        update_sheet(Path(a.update_sheet), log_path, a.out_dir)
        print("Coder sheet updated from log.")
        return 0

    import pandas as pd
    import requests
    man = pd.read_csv(a.manifest, dtype=str).sort_values("fetch_rank", key=lambda s: s.astype(int))
    done, n_success = read_log_state(log_path)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ua = user_agent()
    sess = requests.Session()
    thr, robots = Throttle(a.per_host_delay, a.global_delay), {}
    processed = 0
    for _, r in man.iterrows():
        if a.max_success is not None and n_success >= a.max_success:
            print(f"Reached ceiling of {a.max_success} saved texts; stopping.")
            break
        if a.limit is not None and processed >= a.limit:
            break
        aid, url, gdate = r["audit_id"], r["url"], r["gkg_date"]
        if aid in done:
            continue
        processed += 1
        text, mode_ok, snap_ok = "", "", ""
        if not a.no_live:
            host = urlparse(url).netloc
            res = robots_allows(url, ua, robots, sess, a.timeout, thr)
            allowed, why = res if isinstance(res, tuple) else (bool(res), "robots_disallowed")
            if allowed:
                thr.wait(host)
                st, text, err = get_and_extract(sess, url, ua, a.timeout, orig_url=url)
                ok = err == ""
                log_row(log_path, _row(aid, url, "live", st, ok, len(text), err))
                if ok:
                    mode_ok = "live"
            else:
                log_row(log_path, _row(aid, url, "live", "", False, 0, why))
        if not mode_ok:
            thr.wait("archive.org")
            st, snap, err = wayback_snapshot(sess, url, gdate, ua, a.timeout, a.max_snapshot_days)
            if err:
                log_row(log_path, _row(aid, url, "wayback", st, False, 0, err))
            else:
                thr.wait("archive.org")
                st, text, err = get_and_extract(sess, snap, ua, a.timeout)
                ok = err == ""
                log_row(log_path, _row(aid, url, "wayback", st, ok, len(text), err, snap))
                if ok:
                    mode_ok = "wayback"
        if not mode_ok and a.ngrams_fallback and gdate and int(gdate[:4]) >= 2020:
            try:
                text = fetch_ngrams_text(url, gdate)
                ok = len(text) >= MIN_CHARS
                log_row(log_path, _row(aid, url, "ngrams_approx", "", ok, len(text), "" if ok else "too_short"))
                if ok:
                    mode_ok = "ngrams_approx"
            except NotImplementedError:
                log_row(log_path, _row(aid, url, "ngrams_approx", "", False, 0, "ngrams_not_implemented"))
        if mode_ok:
            (out / f"{aid}.txt").write_text(text, encoding="utf-8")
            n_success += 1
    print(f"Done. Saved texts (all runs): {n_success}. Log: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
