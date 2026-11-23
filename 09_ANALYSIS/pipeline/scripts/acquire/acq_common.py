"""Shared helpers for the acquisition scripts (D36: every download is logged).

Every script in scripts/acquire/ imports this module. It provides:
  * the --root argument (defaults to the repository root, two levels above this file);
  * an HTTP session with retries and a polite User-Agent;
  * fetch(): download a URL, write the raw bytes untouched to data/raw/<source>/,
    and append one line to logs/acquisition_log.csv with
    timestamp, source, url, status, bytes, sha256, notes.

No data are ever invented here. A failed download is logged with its status and
an empty sha256, and the caller decides on the fallback.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover
    sys.exit("requests is required: pip install -r scripts/acquire/requirements.txt")

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]
LOG_FIELDS = ["timestamp", "source", "url", "status", "bytes", "sha256", "notes"]
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) research-data-acquisition/1.0 "
    "(academic project; contact via repository owner)"
)


def base_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--root", type=Path, default=REPO_ROOT_DEFAULT,
                   help="project root (default: repository root)")
    p.add_argument("--sleep", type=float, default=1.0,
                   help="seconds to wait between requests (politeness)")
    p.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout, seconds")
    return p


class Project:
    """Paths relative to the project root."""

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.raw = self.root / "data" / "raw"
        self.processed = self.root / "data" / "processed"
        self.logs = self.root / "logs"
        self.docs = self.root / "docs"
        self.acquire = self.root / "scripts" / "acquire"
        for d in (self.raw, self.processed, self.logs):
            d.mkdir(parents=True, exist_ok=True)
        self.log_path = self.logs / "acquisition_log.csv"

    def raw_dir(self, source: str) -> Path:
        d = self.raw / source
        d.mkdir(parents=True, exist_ok=True)
        return d


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log_download(proj: Project, source: str, url: str, status, nbytes: Optional[int] = None,
                 sha: str = "", notes: str = "") -> None:
    new = not proj.log_path.exists()
    with open(proj.log_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow({
            "timestamp": now_iso(), "source": source, "url": url, "status": status,
            "bytes": "" if nbytes is None else nbytes, "sha256": sha,
            "notes": (notes or "").replace("\n", " ")[:500],
        })


def make_session(retries: int = 3, verify: bool | str = True) -> "requests.Session":
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(total=retries, backoff_factor=1.5,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset({"GET", "POST", "HEAD"}),
                  respect_retry_after_header=True)
    ad = HTTPAdapter(max_retries=retry)
    s.mount("https://", ad)
    s.mount("http://", ad)
    s.verify = verify
    return s


def safe_name(s: str, maxlen: int = 150) -> str:
    s = re.sub(r"[^A-Za-z0-9._=-]+", "_", s).strip("_")
    return s[:maxlen] or "file"


def fetch(proj: Project, session, source: str, url: str, dest_name: Optional[str] = None,
          subdir: str = "", method: str = "GET", timeout: float = 60.0, notes: str = "",
          skip_existing: bool = True, **kwargs) -> Optional[Path]:
    """Download url to data/raw/<source>/<subdir>/<dest_name>; log it; return the path or None.

    The bytes are written exactly as received (no decoding, no reformatting).
    If the file already exists and skip_existing is True, it is not re-downloaded,
    and a 'cached' line is logged with its hash.
    """
    d = proj.raw_dir(source)
    if subdir:
        d = d / subdir
        d.mkdir(parents=True, exist_ok=True)
    name = dest_name or safe_name(url.split("://", 1)[-1])
    path = d / name
    if skip_existing and path.exists() and path.stat().st_size > 0:
        log_download(proj, source, url, "cached", path.stat().st_size, sha256_file(path), notes)
        return path
    try:
        r = session.request(method, url, timeout=timeout, **kwargs)
    except Exception as e:  # network failure, DNS, TLS...
        log_download(proj, source, url, f"error:{type(e).__name__}", None, "", f"{notes} {e}")
        return None
    content = r.content
    if r.status_code != 200:
        log_download(proj, source, url, r.status_code, len(content), sha256_bytes(content),
                     f"{notes} non-200; not saved")
        return None
    tmp = path.with_suffix(path.suffix + ".part")
    with open(tmp, "wb") as f:
        f.write(content)
    os.replace(tmp, path)
    log_download(proj, source, url, r.status_code, len(content), sha256_bytes(content), notes)
    return path


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=str)


def polite_sleep(seconds: float) -> None:
    if seconds and seconds > 0:
        time.sleep(seconds)


def banner(msg: str) -> None:
    print("=" * 78)
    print(msg)
    print("=" * 78)


def read_csv_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
            n += 1
    return n
