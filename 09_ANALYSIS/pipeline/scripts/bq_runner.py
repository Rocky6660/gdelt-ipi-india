#!/usr/bin/env python3
"""BigQuery extraction runner for the GDELT inflation-perception project (D4, D36).

Safety rules enforced here, in code:
  * Every job needs a prior dry run for the SAME SQL text + parameters (ledger row status DRYRUN).
  * maximum_bytes_billed = ceil(dry_run_bytes * 1.05) is always set.
  * A job is refused if it would take estimated+actual spend over the hard project cap
    (default 670 GB), the stage cap (Q2 <= 650 GB), or the per-job scan cap (60 GB for Q2 chunks).
  * Stage-Q2 jobs are refused until the probe and Q1 ran OK and the Gate-1a outlet freeze file exists.
  * Nothing here contacts BigQuery unless a command needs it; google-cloud libs are imported lazily.

Run `python scripts/bq_runner.py --help`. No query has been run by the tooling authors.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import hashlib
import json
import math
import os
import random
import re
import sys
from pathlib import Path
from typing import Callable, Iterable

import yaml

# ---- portable file lock (fcntl on POSIX, msvcrt on Windows)
try:
    import fcntl as _fcntl
    def _lock(fh):  _fcntl.flock(fh, _fcntl.LOCK_EX)
    def _unlock(fh): _fcntl.flock(fh, _fcntl.LOCK_UN)
except ImportError:  # Windows
    import msvcrt as _msvcrt, time as _time
    def _lock(fh):
        pos = fh.tell(); fh.seek(0)
        while True:
            try:
                _msvcrt.locking(fh.fileno(), _msvcrt.LK_NBLCK, 1); break
            except OSError:
                _time.sleep(0.1)
        fh.seek(pos)
    def _unlock(fh):
        pos = fh.tell(); fh.seek(0)
        try: _msvcrt.locking(fh.fileno(), _msvcrt.LK_UNLCK, 1)
        except OSError: pass
        fh.seek(pos)

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
DEFAULT_CONFIG = SCRIPTS_DIR / "config.yaml"

LEDGER_COLUMNS = [
    "timestamp", "job_label", "sql_file", "params_hash",
    "dry_run_bytes", "cap_bytes", "actual_billed_bytes", "status", "job_id", "destination",
]
FULL_COLUMNS = ["DATE", "SourceCommonName", "GKGRECORDID", "DocumentIdentifier", "Themes", "V2Tone", "TranslationInfo"]
REDUCED_COLUMNS = ["DATE", "SourceCommonName", "Themes", "TranslationInfo"]
ALLOWED_STEPS = {1, 2, 3, 4, 6}


class Refused(Exception):
    """A safety rule blocked the action."""


# ----------------------------------------------------------------------------- config
def load_config(path: Path | str | None = None) -> dict:
    with open(path or DEFAULT_CONFIG) as fh:
        cfg = yaml.safe_load(fh)
    cfg["_root"] = REPO_ROOT
    return cfg


def rpath(cfg: dict, key: str) -> Path:
    return Path(cfg["_root"]) / cfg["paths"][key]


def D(s) -> dt.date:
    return s if isinstance(s, dt.date) else dt.date.fromisoformat(str(s))


def gb(cfg: dict, n: float) -> int:
    return int(n * cfg["gb"])


# ----------------------------------------------------------------------------- partition lists (D4 ladder)
def read_rounds(path: Path | str) -> list[tuple[str, dt.date, dt.date]]:
    out = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                fe = (r.get("fieldwork_end") or "").strip()
                out.append((r["round"], D(r["fieldwork_start"].strip()), D(fe) if fe else None))
            except (ValueError, KeyError, AttributeError):
                continue  # rounds with a missing start date are excluded, not imputed (D3); only the start is needed
    return out


def daterange(a: dt.date, b: dt.date) -> Iterable[dt.date]:
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def grid_offset(seed: int, step: int) -> int:
    """Fixed seeded offset, identical for all outlets."""
    if step not in ALLOWED_STEPS:
        raise ValueError(f"step {step} not allowed: must be one of {sorted(ALLOWED_STEPS)} (never a multiple of 7)")
    return random.Random(f"{seed}-{step}").randrange(step)


def grid_days(start: dt.date, end: dt.date, step: int, seed: int, epoch: dt.date) -> list[dt.date]:
    off = grid_offset(seed, step)
    return [d for d in daterange(start, end) if ((d - epoch).days - off) % step == 0]


def always_days(cfg: dict) -> set[dt.date]:
    hw = int(cfg["always_sampled_halfwidth"])
    out = set()
    for s in cfg["always_sampled"]:
        c = D(s)
        out.update(c + dt.timedelta(days=k) for k in range(-hw, hw + 1))
    return out


def build_partitions(cfg: dict, rung: str, rounds: list[tuple[str, dt.date, dt.date]]) -> dict:
    """Return {'window': [dates], 'other': [dates]} for a rung.

    window = the `window_days` days ending the day before fieldwork start (full column set).
    other  = systematic grid (step per rung) + always-sampled days, minus window days (reduced set).
    """
    spec = cfg["rungs"][rung]
    step = int(spec["step"])
    start = max(D(spec["start"]), D(cfg["table_first_partition"]))
    end = D(cfg["sample_end"])
    L = int(spec["window_days"])
    window: set[dt.date] = set()
    for _, fs, _fe in rounds:
        for k in range(1, L + 1):
            d = fs - dt.timedelta(days=k)
            if start <= d <= end:
                window.add(d)
    grid = set(grid_days(start, end, step, int(cfg["seed"]), D(cfg["grid_epoch"])))
    extra = {d for d in always_days(cfg) if start <= d <= end}
    other = (grid | extra) - window
    return {"window": sorted(window), "other": sorted(other)}


def q1_partitions(cfg: dict) -> list[dt.date]:
    return grid_days(D(cfg["table_first_partition"]), D(cfg["sample_end"]), int(cfg["q1_step"]),
                     int(cfg["seed"]), D(cfg["grid_epoch"]))


def split_stage(parts: dict, stage: str, stage_a_start: dt.date) -> dict:
    """Stage A = window days from stage_a_start on. Stage B = everything else on the rung. 'all' = both."""
    if stage == "all":
        return {"window": list(parts["window"]), "other": list(parts["other"])}
    if stage == "A":
        return {"window": [d for d in parts["window"] if d >= stage_a_start], "other": []}
    if stage == "B":
        return {"window": [d for d in parts["window"] if d < stage_a_start], "other": list(parts["other"])}
    raise ValueError("stage must be A, B or all")


def month_chunks(parts: dict) -> list[dict]:
    months = sorted({d.strftime("%Y-%m") for k in ("window", "other") for d in parts[k]})
    out = []
    for m in months:
        w = [d for d in parts["window"] if d.strftime("%Y-%m") == m]
        o = [d for d in parts["other"] if d.strftime("%Y-%m") == m]
        # D4.4(i) one-scan: BigQuery bills the union of both references' columns over all listed partitions,
        # so window days (full set) and other days (reduced set) go in SEPARATE jobs of the same template.
        if w:
            out.append({"group": m, "window": w, "other": []})
        if o:
            out.append({"group": m, "window": [], "other": o})
    return out


def q2_sql_for(cfg, window, other) -> str:
    """Window-day jobs: q2_stage_template.sql (other_ts empty). Other-day jobs: q2_stage_other.sql (one scan)."""
    if window and other:
        raise ValueError("a Q2 job may not mix window and other days (one-scan rule)")
    return f"{cfg['paths']['sql_dir']}/" + ("q2_stage_template.sql" if window else "q2_stage_other.sql")


def q2_split_dry(c, cfg, ledger, label, sql_file, window, other, sources, inline=None) -> int:
    """Q2 bytes as actually run: window-only job + other-only job (each exactly one scan of its columns)."""
    b = 0
    if window:
        b += do_dry_run(c, cfg, ledger, f"{label}_w", sql_file, build_q2_params(window, [], sources, cfg), inline=inline)
    if other:
        b += do_dry_run(c, cfg, ledger, f"{label}_o", q2_sql_for(cfg, [], other),
                        build_q2_params([], other, sources, cfg), inline=inline)
    return b


def split_chunk(chunk: dict, bytes_fn: Callable[[dict], int], limit: int) -> list[dict]:
    """Recursively halve a chunk (by date) until its dry-run bytes <= limit. Free: only dry runs."""
    b = bytes_fn(chunk)
    chunk = dict(chunk, dry_run_bytes=b)
    alld = sorted(set(chunk["window"]) | set(chunk["other"]))
    if b <= limit or len(alld) <= 1:
        return [chunk]
    mid = alld[len(alld) // 2]
    left = {"group": chunk["group"], "window": [d for d in chunk["window"] if d < mid],
            "other": [d for d in chunk["other"] if d < mid]}
    right = {"group": chunk["group"], "window": [d for d in chunk["window"] if d >= mid],
             "other": [d for d in chunk["other"] if d >= mid]}
    return split_chunk(left, bytes_fn, limit) + split_chunk(right, bytes_fn, limit)


# ----------------------------------------------------------------------------- parameters
def ts(d: dt.date) -> str:
    return d.isoformat()


def build_q2_params(window: list[dt.date], other: list[dt.date], sources: list[str], cfg: dict) -> dict:
    return {
        "window_ts": {"type": "ARRAY<TIMESTAMP>", "value": [ts(d) for d in window]},
        "other_ts": {"type": "ARRAY<TIMESTAMP>", "value": [ts(d) for d in other]},
        "sources": {"type": "ARRAY<STRING>", "value": sorted(set(sources))},
        "price_alt": {"type": "STRING", "value": cfg["price_alt"]},
        "trim_themes": {"type": "BOOL", "value": bool(cfg.get("trim_themes", False))},
    }


def build_std_job(name: str, cfg: dict) -> tuple[str, str, dict]:
    """(label, sql_file relative to repo, params) for probe / q1 / theme."""
    sql_dir = cfg["paths"]["sql_dir"]
    top20 = read_top20_domains(cfg)
    if name == "probe":
        return "probe_one_partition", f"{sql_dir}/probe_one_partition.sql", {
            "probe_day": {"type": "DATE", "value": cfg["probe_day"]}}
    if name == "q1":
        return "q1_outlets", f"{sql_dir}/q1_outlet_candidates.sql", {
            "q1_ts": {"type": "ARRAY<TIMESTAMP>", "value": [ts(d) for d in q1_partitions(cfg)]},
            "indian_langs": {"type": "ARRAY<STRING>", "value": list(cfg["indian_langs"])},
            "min_articles": {"type": "INT64", "value": int(cfg["q1_min_articles"])}}
    if name == "theme":
        return "theme_lookup", f"{sql_dir}/theme_lookup.sql", {
            "sample_ts": {"type": "ARRAY<TIMESTAMP>", "value": list(cfg["theme_lookup_dates"])},
            "sources": {"type": "ARRAY<STRING>", "value": top20},
            "candidate_regex": {"type": "STRING", "value": cfg["theme_candidate_regex"]}}
    if name == "daycount":  # D13 global daily count over the sampled partitions of the chosen rung
        rung = cfg.get("rung") or "L4"
        parts = rung_parts(cfg, rung)
        days = sorted(set(parts["window"]) | set(parts["other"]))
        return f"daycount_{rung}", f"{sql_dir}/global_daily_count.sql", {
            "ts": {"type": "ARRAY<TIMESTAMP>", "value": [ts(d) for d in days]}}
    raise ValueError(name)


def to_bq_param(name: str, spec: dict):
    from google.cloud import bigquery
    typ, val = spec["type"], spec["value"]

    def conv(t, v):
        if t == "TIMESTAMP":
            d = D(v)
            return dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc)
        if t == "DATE":
            return D(v)
        return v
    if typ.startswith("ARRAY<"):
        et = typ[6:-1]
        return bigquery.ArrayQueryParameter(name, et, [conv(et, v) for v in val])
    return bigquery.ScalarQueryParameter(name, typ, conv(typ, val))


def inline_partitions(sql: str, params: dict) -> tuple[str, dict]:
    """Replace ARRAY<TIMESTAMP> params by literal lists so partition pruning is certain."""
    new = {}
    for k, spec in params.items():
        if spec["type"] == "ARRAY<TIMESTAMP>":
            lit = ("[" + ", ".join(f"TIMESTAMP '{v}'" for v in spec["value"]) + "]") if spec["value"] \
                else "ARRAY<TIMESTAMP>[]"
            sql = re.sub(rf"@{k}\b", lambda _m, lit=lit: lit, sql)
        else:
            new[k] = spec
    return sql, new


def params_hash(sql: str, params: dict) -> str:
    blob = sql + "\n" + json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ----------------------------------------------------------------------------- ledger
STAGE_Q2_SQL_PREFIX = "q2_stage_"


def is_q2_job(label: str, sql_file: str = "") -> bool:
    """A job is Stage-Q2 if it uses a q2_stage_template*.sql file OR its label starts with 'q2_'."""
    return Path(sql_file or "").name.startswith(STAGE_Q2_SQL_PREFIX) or label.lower().startswith("q2_")


def stage_of_job(label: str, sql_file: str = "") -> str:
    return "q2" if is_q2_job(label, sql_file) else label.split("_")[0].lower()


def stage_of(label: str) -> str:  # kept for callers that only have a label
    return stage_of_job(label, "")


TERMINAL = ("RUN_OK", "RUN_FAILED", "EXPORT_FAILED")
BQ_MIN_BILL = 10 * 1024 * 1024  # BigQuery bills at least 10 MiB per query (R2)


def bq_cap(dry_bytes: int, cfg: dict) -> int:
    return max(math.ceil(dry_bytes * cfg["caps"]["cap_multiplier"]), BQ_MIN_BILL)


class Ledger:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        with open(self.path, newline="") as fh:
            return list(csv.DictReader(fh))

    def append(self, **kw) -> dict:
        row = {c: "" for c in LEDGER_COLUMNS}
        row["timestamp"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        row.update({k: ("" if v is None else v) for k, v in kw.items()})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", newline="") as fh:
            _lock(fh)
            new = os.fstat(fh.fileno()).st_size == 0  # decided under the lock: no double header
            w = csv.DictWriter(fh, fieldnames=LEDGER_COLUMNS)
            if new:
                w.writeheader()
            w.writerow(row)
            fh.flush()
            _unlock(fh)
        return row

    def latest_dryrun(self, params_hash_: str) -> dict | None:
        found = [r for r in self.rows() if r["status"] == "DRYRUN" and r["params_hash"] == params_hash_]
        return found[-1] if found else None

    def job_states(self) -> dict:
        """(label, hash) -> latest run-status row. For gating only; cost uses committed()."""
        st: dict = {}
        for r in self.rows():
            if r["status"] == "RUN_STARTED" or r["status"] in TERMINAL:
                st[(r["job_label"], r["params_hash"])] = r
        return st

    def has_status(self, label: str, h: str, status: str) -> bool:
        return any(r["job_label"] == label and r["params_hash"] == h and r["status"] == status for r in self.rows())

    def ok_labels(self) -> set[str]:
        return {r["job_label"] for r in self.rows() if r["status"] == "RUN_OK"}

    def committed(self) -> dict:
        """Every run is added, never replaced (re-runs pay again).
        RUN_OK -> actual billed (blank -> cap). RUN_FAILED / EXPORT_FAILED -> actual if > 0, else the cap.
        RUN_STARTED with no later terminal row for the same (label, hash) -> pending, counted at cap."""
        actual = 0
        by_stage: dict[str, int] = {}
        open_cap: dict[tuple, tuple[int, str]] = {}
        for r in self.rows():
            key = (r["job_label"], r["params_hash"])
            cap = int(float(r["cap_bytes"] or 0))
            st = stage_of_job(r["job_label"], r["sql_file"])
            if r["status"] == "RUN_STARTED":
                open_cap[key] = (cap, st)
            elif r["status"] in TERMINAL:
                open_cap.pop(key, None)
                billed = int(float(r["actual_billed_bytes"])) if r["actual_billed_bytes"] != "" else None
                if r["status"] == "RUN_OK":
                    v = billed if billed is not None else cap
                else:
                    v = billed if billed else cap
                actual += v
                by_stage[st] = by_stage.get(st, 0) + v
        pending = 0
        for cap, st in open_cap.values():
            pending += cap
            by_stage[st] = by_stage.get(st, 0) + cap
        return {"actual": actual, "pending": pending, "by_stage": by_stage}


@contextlib.contextmanager
def runner_lock(cfg: dict):
    """One runner at a time across the check -> RUN_STARTED sequence."""
    p = Path(cfg["_root"]) / "logs" / ".runner.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as fh:
        _lock(fh)
        try:
            yield
        finally:
            _unlock(fh)


def log(cfg: dict, msg: str) -> None:
    """Print and append to logs/bq_runner.log."""
    line = f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {msg}"
    print(msg)
    p = Path(cfg["_root"]) / "logs" / "bq_runner.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as fh:
        fh.write(line + "\n")


def check_run_allowed(ledger: Ledger, cfg: dict, label: str, h: str, dry_bytes: int, cap: int,
                      quota_used: int | None, sql_file: str = "") -> None:
    """Raise Refused if running this job could break a cap. Pure given its inputs (tested).
    quota_used = live INFORMATION_SCHEMA reading (already includes ledger jobs), or None.
    quota_used_override_bytes = pre-project spend entered by the human: ADDED to ledger spend."""
    caps = cfg["caps"]
    stage = stage_of_job(label, sql_file)
    scan_lim = gb(cfg, caps["per_job_scan_gb"].get(stage, caps["default_per_job_scan_gb"]))
    if cap > scan_lim:  # the cap, not the dry run, is what can be billed
        raise Refused(f"per-job scan limit: cap {cap/1e9:.1f} GB (dry run {dry_bytes/1e9:.1f} GB x "
                      f"{cfg['caps']['cap_multiplier']}) exceeds {scan_lim/1e9:.0f} GB for stage '{stage}': "
                      f"split the chunk (bq_runner.py plan does this)")
    override = cfg.get("quota_used_override_bytes")
    if quota_used is None and override is None:
        raise Refused("quota used this month is unknown (INFORMATION_SCHEMA unavailable). Check it by hand "
                      "(see `bq_runner.py quota`) and set quota_used_override_bytes in config.yaml")
    c = ledger.committed()
    candidates = []
    if quota_used is not None:
        candidates.append(int(quota_used))
    if override is not None:
        candidates.append(int(override) + c["actual"])
    candidates.append(c["actual"])
    used = max(candidates) + c["pending"]
    hard = gb(cfg, caps["hard_project_gb"])
    if used + cap > hard:
        raise Refused(f"hard cap: used {used/1e9:.1f} GB + job cap {cap/1e9:.1f} GB > {hard/1e9:.0f} GB")
    stage_caps = caps.get("stage_gb") or {}
    if stage in stage_caps:
        slim = gb(cfg, stage_caps[stage])
        s_used = c["by_stage"].get(stage, 0)
        if s_used + cap > slim:
            raise Refused(f"stage cap '{stage}': {s_used/1e9:.1f} GB committed + {cap/1e9:.1f} GB > {slim/1e9:.0f} GB")


# ----------------------------------------------------------------------------- BigQuery access (lazy)
_CREDS = None


def get_credentials():
    """User credentials via a browser sign-in (pydata-google-auth). Any machine-wide gcloud/ADC login is ignored on
    purpose, so the account is always the one the user signs in with. Token cached in the user's home, not here."""
    global _CREDS
    if _CREDS is not None:
        return _CREDS
    import pydata_google_auth
    _CREDS = pydata_google_auth.get_user_credentials(
        ["https://www.googleapis.com/auth/bigquery", "openid", "https://www.googleapis.com/auth/userinfo.email"],
        use_local_webserver=True, credentials_cache=pydata_google_auth.cache.ReadWriteCredentialsCache(
            filename="gdelt_ipi_credentials.json"))
    try:
        import google.auth.transport.requests as _gr, requests as _rq
        _CREDS.refresh(_gr.Request())
        info = _rq.get("https://www.googleapis.com/oauth2/v3/userinfo",
                       headers={"Authorization": f"Bearer {_CREDS.token}"}, timeout=20).json()
        print(f"[auth] signed in as {info.get('email', '?')}")
    except Exception as e:
        print(f"[auth] could not read account email: {e!r}")
    return _CREDS


def get_client(cfg: dict):
    from google.cloud import bigquery
    return bigquery.Client(project=cfg["project"], location=cfg.get("location", "US"),
                           credentials=get_credentials())


QUOTA_SQL = """
SELECT COALESCE(SUM(total_bytes_billed), 0) AS billed
FROM `region-{region}`.INFORMATION_SCHEMA.{view}
WHERE creation_time >= TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH)
  AND job_type = 'QUERY' AND state = 'DONE' AND (cache_hit IS NULL OR NOT cache_hit)
"""

QUOTA_HELP = """Could not read quota from INFORMATION_SCHEMA. Check by hand, then set quota_used_override_bytes in config.yaml:
  bq --project_id={project} query --use_legacy_sql=false \\
    'SELECT SUM(total_bytes_billed)/1e9 AS gb FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
     WHERE creation_time >= TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), MONTH) AND job_type="QUERY"'
  or Cloud Console > IAM & Admin > Quotas > 'Query usage per day' / BigQuery > Administration > Monitoring.
Note: the sandbox quota is per project (JOBS_BY_PROJECT needs bigquery.jobs.listAll); months reset in UTC here, check the
Console if you run near midnight on the 1st."""

_QUOTA_CACHE: dict = {}
QUOTA_CHECK_CAP = 100_000_000  # INFORMATION_SCHEMA jobs bill >= 10 MB; hard ceiling 100 MB per reading


def get_quota_used(client, cfg: dict, view: str = "JOBS_BY_USER", ledger: Ledger | None = None,
                   fresh: bool = False) -> int | None:
    """Read quota used. The reading is itself a job: dry-run first, then run with a byte cap, both ledgered
    as `quota_check`. Cached for the process (one reading per session) unless fresh=True."""
    from google.cloud import bigquery
    if view in _QUOTA_CACHE and not fresh:
        return _QUOTA_CACHE[view]
    region = str(cfg.get("location", "US")).lower()
    sql = QUOTA_SQL.format(region=region, view=view)
    h = hashlib.sha256(sql.encode()).hexdigest()[:16]
    try:
        dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
        db = int(dry.total_bytes_processed or 0)
        cap = min(max(math.ceil(db * cfg["caps"]["cap_multiplier"]), 50_000_000), QUOTA_CHECK_CAP)
        if ledger:
            ledger.append(job_label="quota_check", sql_file=f"(INFORMATION_SCHEMA.{view})", params_hash=h,
                          dry_run_bytes=db, cap_bytes=cap, status="DRYRUN")
            ledger.append(job_label="quota_check", sql_file=f"(INFORMATION_SCHEMA.{view})", params_hash=h,
                          dry_run_bytes=db, cap_bytes=cap, status="RUN_STARTED")
        job = client.query(sql, job_config=bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=cap))
        rows = list(job.result())
        if ledger:
            ledger.append(job_label="quota_check", sql_file=f"(INFORMATION_SCHEMA.{view})", params_hash=h,
                          dry_run_bytes=db, cap_bytes=cap, actual_billed_bytes=int(job.total_bytes_billed or 0),
                          status="RUN_OK", job_id=getattr(job, "job_id", ""))
        _QUOTA_CACHE[view] = int(rows[0]["billed"])
        return _QUOTA_CACHE[view]
    except Exception as e:  # noqa: BLE001
        if ledger:
            ledger.append(job_label="quota_check", sql_file=f"(INFORMATION_SCHEMA.{view})", params_hash=h,
                          status="RUN_FAILED")
        print(f"[quota] {view} failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def read_sql(cfg: dict, sql_file: str) -> str:
    p = Path(sql_file)
    if not p.is_absolute():
        p = Path(cfg["_root"]) / sql_file
    return p.read_text()


def prepare(cfg: dict, sql_file: str, params: dict, inline: bool | None) -> tuple[str, dict, str]:
    sql = read_sql(cfg, sql_file)
    if inline is None:
        inline = bool(cfg.get("inline_partitions"))
    if inline:
        sql, params = inline_partitions(sql, params)
    return sql, params, params_hash(sql, params)


def do_dry_run(client, cfg: dict, ledger: Ledger, label: str, sql_file: str, params: dict,
               inline: bool | None = None) -> int:
    from google.cloud import bigquery
    sql, params, h = prepare(cfg, sql_file, params, inline)
    jc = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                 query_parameters=[to_bq_param(k, v) for k, v in params.items()])
    job = client.query(sql, job_config=jc)
    b = int(job.total_bytes_processed)
    cap = bq_cap(b, cfg)
    ledger.append(job_label=label, sql_file=sql_file, params_hash=h, dry_run_bytes=b, cap_bytes=cap, status="DRYRUN")
    return b


def export_table(client, table_ref, out_dir: Path, rows_per_file: int = 2_000_000) -> dict:
    """Write a result table to parquet part files. Storage Read API first; on ANY failure the partial parts are
    discarded and the table is re-read from row 0 with list_rows paging (stream order differs between the two APIs,
    so resuming mid-way could duplicate or skip rows). Raises if rows written != rows expected."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    out_dir.mkdir(parents=True, exist_ok=True)
    table = client.get_table(table_ref)
    total = int(table.num_rows)
    state = {"flushed": 0, "files": []}
    method = "storage_read_api"

    def reset():
        for f in out_dir.glob("part-*.parquet"):
            f.unlink()
        state["flushed"], state["files"] = 0, []

    def write(tbl):
        fn = out_dir / f"part-{len(state['files']):05d}.parquet"
        pq.write_table(tbl, fn, compression="zstd")
        state["files"].append(fn.name)
        state["flushed"] += tbl.num_rows

    reset()
    try:
        from google.cloud import bigquery_storage
        bqs = bigquery_storage.BigQueryReadClient(credentials=get_credentials())
        buf, n = [], 0
        for batch in client.list_rows(table_ref).to_arrow_iterable(bqstorage_client=bqs):
            buf.append(batch)
            n += batch.num_rows
            if n >= rows_per_file:
                write(pa.Table.from_batches(buf)); buf, n = [], 0
        if buf:
            write(pa.Table.from_batches(buf))
    except Exception as e:  # noqa: BLE001
        print(f"[export] Storage Read API failed ({type(e).__name__}: {e}); restarting from row 0 with list_rows paging",
              file=sys.stderr)
        method = "list_rows_paging"
        reset()
        while state["flushed"] < total:
            tbl = client.list_rows(table_ref, start_index=state["flushed"], max_results=rows_per_file) \
                .to_arrow(create_bqstorage_client=False)
            if tbl.num_rows == 0:
                break
            write(tbl)
    manifest = {"rows_expected": total, "rows_written": state["flushed"], "files": state["files"], "method": method,
                "table_bytes": int(table.num_bytes or 0)}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    if state["flushed"] != total:
        raise RuntimeError(f"export incomplete: {state['flushed']} of {total} rows written")
    return manifest


def find_plan_chunk(cfg: dict, label: str) -> tuple[dict, dict] | None:
    pdir = rpath(cfg, "plan_dir")
    for f in sorted(pdir.glob("plan_*.json")) if pdir.exists() else []:
        plan = json.loads(f.read_text())
        for ch in plan["chunks"]:
            if ch["label"] == label:
                return plan, ch
    return None


def remaining_planned(plan: dict, ledger: Ledger) -> int:
    ok = ledger.ok_labels()
    return sum(int(ch["dry_run_bytes"]) for ch in plan["chunks"] if ch["label"] not in ok)


def check_plan_budget(cfg: dict, ledger: Ledger, plans: list[dict], extra: int = 0) -> None:
    """Committed Q2 + everything still planned (given plans) must fit in the Q2 stage cap (V8)."""
    lim = gb(cfg, cfg["caps"]["stage_gb"]["q2"])
    committed = ledger.committed()["by_stage"].get("q2", 0)
    rem = sum(remaining_planned(p, ledger) for p in plans) + extra
    if committed + rem > lim:
        raise Refused(f"Q2 plan does not fit: {committed/1e9:.1f} GB committed + {rem/1e9:.1f} GB still planned "
                      f"> {lim/1e9:.0f} GB stage cap. Move the rung down at Gate 0b.")


def gate_q2_prereqs(cfg: dict, ledger: Ledger, label: str, params: dict, sql_file: str = "") -> None:
    """D2/D34/D9: probe, Q1 and theme lookup finished and outlets + themes frozen at Gate 1a before any Q2 job runs.
    The plan membership and first-month check apply to every run path (V5)."""
    if not is_q2_job(label, sql_file):
        return
    done = ledger.ok_labels()
    for need in ("probe_one_partition", "q1_outlets", "theme_lookup"):
        if need not in done:
            raise Refused(f"Gate 1a prerequisite missing: '{need}' has no RUN_OK ledger row")
    freeze = Path(cfg["_root"]) / "data/processed/gate1a_frozen.json"
    if not freeze.exists():
        raise Refused("Gate 1a freeze file missing: run `bq_runner.py freeze-outlets --by <human>` after review")
    fr = json.loads(freeze.read_text())
    sup = rpath(cfg, "source_superset")
    if not sup.exists() or file_sha(sup) != fr.get("sha256"):
        raise Refused("source_superset.csv changed after the Gate 1a freeze (hash mismatch)")
    if fr.get("price_alt") != cfg["price_alt"] or bool(fr.get("trim_themes")) != bool(cfg.get("trim_themes", False)):
        raise Refused("price_alt / trim_themes in config.yaml differ from the values frozen at Gate 1a")
    found = find_plan_chunk(cfg, label)
    if found is None:
        raise Refused(f"label '{label}' is not in any plan under {rpath(cfg, 'plan_dir')}; run `plan` first")
    plan, ch = found
    if "window_ts" in params and (params["window_ts"]["value"] != ch["window"] or params["other_ts"]["value"] != ch["other"]):
        raise Refused("parameters do not match the planned chunk dates")
    if ch["group"] != plan["first_group"] and not checked_marker(cfg, plan["rung"], plan["stage"]).exists():
        raise Refused("first one-month chunk must be run and then checked (`mark-checked`) before the rest (D4.5)")
    sibling = plan_path(cfg, plan["rung"], "B" if plan["stage"] == "A" else "A")
    plans = [plan] + ([json.loads(sibling.read_text())] if sibling.exists() else [])
    check_plan_budget(cfg, ledger, plans)


def reconcile_open_jobs(client, cfg: dict, ledger: Ledger, label: str, h: str) -> None:
    """R1: a RUN_STARTED row with no terminal row means a runner died after submitting. Look the job up by its
    pre-assigned id and close it at the billed bytes (or the cap if unknown). Refuse while it is still running."""
    open_rows: dict[tuple, dict] = {}
    for r in ledger.rows():
        key = (r["job_label"], r["params_hash"])
        if r["status"] == "RUN_STARTED":
            open_rows[key] = r
        elif r["status"] in TERMINAL:
            open_rows.pop(key, None)
    r = open_rows.get((label, h))
    if r is None:
        return
    base = dict(job_label=label, sql_file=r["sql_file"], params_hash=h, dry_run_bytes=r["dry_run_bytes"],
                cap_bytes=r["cap_bytes"])
    jid = r.get("job_id", "")
    if not jid:
        ledger.append(**base, actual_billed_bytes=None, status="RUN_FAILED")  # legacy row: counted at cap
        log(cfg, f"{label}: orphaned RUN_STARTED without job id closed at cap")
        return
    try:
        job = client.get_job(jid, location=cfg.get("location", "US"))
    except Exception:
        ledger.append(**base, actual_billed_bytes=None, status="RUN_FAILED", job_id=jid)
        log(cfg, f"{label}: job {jid} never reached BigQuery; closed (counted at cap)")
        return
    if job.state != "DONE":
        raise Refused(f"job {jid} for {label} is still {job.state}; wait for it, then re-run")
    billed = int(job.total_bytes_billed or 0) or None
    if job.error_result is None and job.destination is not None:
        d = job.destination
        ledger.append(**base, actual_billed_bytes=billed, status="EXPORT_FAILED", job_id=jid,
                      destination=f"{d.project}.{d.dataset_id}.{d.table_id}")  # succeeded: download, don't re-pay
    else:
        ledger.append(**base, actual_billed_bytes=billed, status="RUN_FAILED", job_id=jid)
    log(cfg, f"{label}: orphaned job {jid} reconciled at {((billed or 0)/1e9):.2f} GB billed; its result was not "
             f"downloaded here -- use `export --job-id {jid}` if it succeeded")


def do_run(client, cfg: dict, ledger: Ledger, label: str, sql_file: str, params: dict,
           out_dir: Path, inline: bool | None = None, allow_rerun: bool = False) -> dict:
    from google.cloud import bigquery
    sql, params2, h = prepare(cfg, sql_file, params, inline)

    def refuse(msg: str):
        ledger.append(job_label=label, sql_file=sql_file, params_hash=h, status=f"REFUSED: {msg[:120]}")
        raise Refused(msg)

    dr = ledger.latest_dryrun(h)
    if dr is None:
        refuse("no dry run in the ledger for this exact SQL+params; run `dryrun` first")
    dry = int(float(dr["dry_run_bytes"]))
    cap = bq_cap(dry, cfg)
    if any(r["job_label"] == label and r["params_hash"] == h and r["status"] in ("RUN_OK", "EXPORT_FAILED")
           for r in ledger.rows()) and not allow_rerun:
        refuse("this job already ran (RUN_OK or EXPORT_FAILED). For a failed download use `export --job-id`; "
               "--allow-rerun pays for the query again")
    try:
        gate_q2_prereqs(cfg, ledger, label, params, sql_file)
    except Refused as e:
        refuse(str(e))
    reconcile_open_jobs(client, cfg, ledger, label, h)
    quota = get_quota_used(client, cfg, ledger=ledger)
    job_id = f"ipi_{re.sub(r'[^A-Za-z0-9_]', '_', label)[:60]}_{h[:8]}_{dt.datetime.now(dt.timezone.utc):%Y%m%d%H%M%S}_{random.randrange(16**6):06x}"
    with runner_lock(cfg):
        try:
            check_run_allowed(ledger, cfg, label, h, dry, cap, quota, sql_file=sql_file)
        except Refused as e:
            refuse(str(e))
        ledger.append(job_label=label, sql_file=sql_file, params_hash=h, dry_run_bytes=dry, cap_bytes=cap,
                      status="RUN_STARTED", job_id=job_id)
    jc = bigquery.QueryJobConfig(maximum_bytes_billed=cap,
                                 query_parameters=[to_bq_param(k, v) for k, v in params2.items()],
                                 labels={"ledger_label": re.sub(r"[^a-z0-9_-]", "-", label.lower())[:60]})
    base = dict(job_label=label, sql_file=sql_file, params_hash=h, dry_run_bytes=dry, cap_bytes=cap)
    job = None
    try:
        job = client.query(sql, job_config=jc, job_id=job_id)
        job.result()
    except Exception:
        billed = int(job.total_bytes_billed) if job is not None and getattr(job, "total_bytes_billed", None) else None
        ledger.append(**base, actual_billed_bytes=billed, status="RUN_FAILED", job_id=getattr(job, "job_id", "") or job_id)
        raise
    billed = int(job.total_bytes_billed or 0)
    dest = f"{job.destination.project}.{job.destination.dataset_id}.{job.destination.table_id}" if job.destination else ""
    try:
        manifest = export_table(client, job.destination, out_dir)
    except Exception:
        ledger.append(**base, actual_billed_bytes=billed, status="EXPORT_FAILED", job_id=job.job_id, destination=dest)
        log(cfg, f"EXPORT_FAILED {label}: query billed {billed/1e9:.2f} GB; retry the download with "
                 f"`export --job-id {job.job_id} --label {label}` (anonymous tables expire after ~24 h)")
        raise
    ledger.append(**base, actual_billed_bytes=billed, status="RUN_OK", job_id=job.job_id, destination=dest)
    out_gb = manifest["table_bytes"] / 1e9
    if out_gb > cfg["caps"]["output_gb_per_job"]:
        log(cfg, f"WARNING: output {out_gb:.2f} GB > {cfg['caps']['output_gb_per_job']} GB per-job output limit (D4.5)")
    log(cfg, f"OK {label}: billed {billed/1e9:.2f} GB (dry {dry/1e9:.2f}), rows {manifest['rows_written']}/"
             f"{manifest['rows_expected']} via {manifest['method']}, job {job.job_id}")
    return manifest


# ----------------------------------------------------------------------------- outlets
def file_sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_top20_domains(cfg: dict) -> list[str]:
    with open(rpath(cfg, "top20_seed"), newline="") as fh:
        return [r["domain"].strip().lower() for r in csv.DictReader(fh) if r["domain"].strip()]


_TWO_LEVEL_SUFFIXES = {"co.in", "org.in", "net.in", "gov.in", "nic.in", "ac.in", "edu.in", "res.in", "firm.in",
                       "gen.in", "ind.in", "co.uk", "org.uk", "com.au"}


def parent_domain(d: str) -> str | None:
    parts = d.split(".")
    if len(parts) <= 2:
        return None
    if ".".join(parts[-2:]) in _TWO_LEVEL_SUFFIXES:
        return ".".join(parts[-3:]) if len(parts) > 3 else None
    return ".".join(parts[-2:])


def read_domain_country(path: Path, country_names=("in", "ind", "india")) -> set[str]:
    out = set()
    if not Path(path).exists():
        return out
    with open(path, newline="", errors="replace") as fh:
        for line in fh:
            cols = re.split(r"[\t,;]", line.strip())
            if len(cols) < 2:
                continue
            dom, ctry = cols[0].strip().lower(), cols[1].strip().lower()
            if ctry in country_names:
                out.add(dom)
    return out


def build_source_superset(cfg: dict, q1_df=None) -> list[tuple[str, str]]:
    """Seed = hand-keyed top-20 (+ parent domains) + GDELT domain-to-country lookup (India) + .in domains + Q1 Indian-language hits."""
    src: dict[str, set[str]] = {}

    def add(d, why):
        d = d.strip().lower()
        if d:
            src.setdefault(d, set()).add(why)
    for d in read_top20_domains(cfg):
        add(d, "top20")
        p = parent_domain(d)
        if p:
            add(p, "top20_parent")
    for d in read_domain_country(rpath(cfg, "domain_country_lookup")):
        add(d, "gdelt_country_lookup")
    if q1_df is not None:
        for r in q1_df.itertuples():
            if bool(r.is_in_domain):
                add(r.domain, "q1_in_domain")
            if bool(r.is_indian_lang):
                add(r.domain, "q1_indian_language")
    return sorted((d, "|".join(sorted(w))) for d, w in src.items())


def read_sources(cfg: dict) -> list[str]:
    with open(rpath(cfg, "source_superset"), newline="") as fh:
        return [r["domain"] for r in csv.DictReader(fh)]


# ----------------------------------------------------------------------------- commands
def gate0_path(cfg):
    return Path(cfg["_root"]) / "data/processed/gate0_quota.json"


def cmd_quota(a, cfg):
    c = get_client(cfg)
    ledger = Ledger(rpath(cfg, "ledger"))
    got = None
    for view in ("JOBS_BY_USER", "JOBS_BY_PROJECT"):
        q = get_quota_used(c, cfg, view, ledger=ledger)
        if q is not None:
            got = q if got is None else got
            log(cfg, f"{view}: {q/1e9:.2f} GB billed this month (UTC month) of the 1 TiB sandbox quota")
            if a.scope == "user":
                break
    if got is None:
        print(QUOTA_HELP.format(project=cfg["project"]))
        return
    if a.record_gate0:
        p = gate0_path(cfg)
        if p.exists() and not a.force:
            sys.exit(f"{p} already records the Gate-0 (pre-project) reading; use --force to overwrite")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"bytes": got, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}))
        log(cfg, f"recorded Gate-0 quota reading {got/1e9:.2f} GB in {p}")


STD_CHOICES = ["probe", "q1", "theme", "daycount"]


def resolve_job(a, cfg):
    if a.job:
        return build_std_job(a.job, cfg)
    if not (a.sql and a.label):
        sys.exit(f"give --job {{{','.join(STD_CHOICES)}}} or --sql FILE --label LABEL [--params-file JSON]")
    params = json.loads(Path(a.params_file).read_text()) if a.params_file else {}
    return a.label, a.sql, params


def cmd_dryrun(a, cfg):
    label, sql_file, params = resolve_job(a, cfg)
    c = get_client(cfg)
    b = do_dry_run(c, cfg, Ledger(rpath(cfg, "ledger")), label, sql_file, params, inline=a.inline_partitions or None)
    log(cfg, f"{label}: dry run {b/1e9:.3f} GB; cap would be {bq_cap(b, cfg)/1e9:.3f} GB")


def cmd_run(a, cfg):
    label, sql_file, params = resolve_job(a, cfg)
    c = get_client(cfg)
    out = Path(a.out) if a.out else rpath(cfg, "out_dir") / label
    try:
        do_run(c, cfg, Ledger(rpath(cfg, "ledger")), label, sql_file, params, out,
               inline=a.inline_partitions or None, allow_rerun=a.allow_rerun)
    except Refused as e:
        sys.exit(f"REFUSED: {e}")


def cmd_export(a, cfg):
    """Re-download the result of a finished job (e.g. after EXPORT_FAILED) without paying for the query again."""
    c = get_client(cfg)
    ledger = Ledger(rpath(cfg, "ledger"))
    job = c.get_job(a.job_id, location=cfg.get("location", "US"))
    if job.state != "DONE" or job.error_result:
        sys.exit(f"job {a.job_id} is not a finished successful query")
    out = Path(a.out) if a.out else rpath(cfg, "out_dir") / a.label
    m = export_table(c, job.destination, out)
    prev = [r for r in ledger.rows() if r["job_id"] == a.job_id and r["status"] == "EXPORT_FAILED"]
    base = {k: prev[-1][k] for k in ("job_label", "sql_file", "params_hash", "dry_run_bytes", "cap_bytes")} if prev else \
        dict(job_label=a.label, sql_file="(export)", params_hash="")
    # billed bytes were already counted by the EXPORT_FAILED row, so this row adds 0
    ledger.append(**base, actual_billed_bytes=0, status="RUN_OK", job_id=a.job_id)
    log(cfg, f"exported {a.job_id}: {m['rows_written']}/{m['rows_expected']} rows via {m['method']}")


def rung_parts(cfg, rung):
    rounds = read_rounds(rpath(cfg, "iesh_rounds"))
    if not rounds:
        sys.exit(f"no usable rounds in {rpath(cfg, 'iesh_rounds')}")
    return build_partitions(cfg, rung, rounds)


def cmd_partitions(a, cfg):
    rung = a.rung or cfg["rung"]
    parts = split_stage(rung_parts(cfg, rung), a.stage, D(cfg["stage_a_start"]))
    print(f"rung {rung} stage {a.stage}: window days {len(parts['window'])}, other days {len(parts['other'])}")
    if a.out:
        Path(a.out).write_text(json.dumps({k: [ts(d) for d in v] for k, v in parts.items()}, indent=1))


def onescan_path(cfg, rung):
    return rpath(cfg, "plan_dir") / f"onescan_{rung}.json"


def colbytes(c, cfg, ledger, rung, parts, inline: bool | None = None) -> dict:
    """D4.2: bytes per column for a rung, via single-column dry runs (free). Respects partition inlining."""
    from google.cloud import bigquery
    do_inline = bool(cfg.get("inline_partitions")) if inline is None else inline
    out = {}
    for kind, cols, days in (("window", FULL_COLUMNS, parts["window"]), ("other", REDUCED_COLUMNS, parts["other"])):
        if not days:
            continue
        pspec = {"ts": {"type": "ARRAY<TIMESTAMP>", "value": [ts(d) for d in days]}}
        for col in cols:
            sql = f"SELECT `{col}` FROM `{cfg['source_table']}` WHERE _PARTITIONTIME IN UNNEST(@ts)"
            ps = pspec
            if do_inline:
                sql, ps = inline_partitions(sql, pspec)
            jc = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                         query_parameters=[to_bq_param(k, v) for k, v in ps.items()])
            b = int(c.query(sql, job_config=jc).total_bytes_processed)
            out[f"{kind}:{col}"] = b
            ledger.append(job_label=f"colbytes_{rung}_{kind}_{col}", sql_file="(inline single-column)",
                          params_hash=hashlib.sha256(sql.encode()).hexdigest()[:16], dry_run_bytes=b,
                          cap_bytes=bq_cap(b, cfg), status="DRYRUN")
    log(cfg, f"  bytes per column for {rung}: " + ", ".join(f"{k}={v/1e9:.1f}GB" for k, v in out.items()))
    return out


def onescan_result(q2_bytes: int, col_bytes: dict, tol: float = 0.01) -> dict:
    s = sum(col_bytes.values())
    rel = abs(q2_bytes - s) / s if s else float("inf")
    return {"q2_dry_run_bytes": q2_bytes, "sum_column_bytes": s, "rel_diff": rel, "ok": rel <= tol, "tolerance": tol}


def cmd_colbytes(a, cfg):
    c, ledger = get_client(cfg), Ledger(rpath(cfg, "ledger"))
    parts = rung_parts(cfg, a.rung)
    cb = colbytes(c, cfg, ledger, a.rung, parts, inline=a.inline_partitions or None)
    q2 = q2_split_dry(c, cfg, ledger, f"ladder_{a.rung}", f"{cfg['paths']['sql_dir']}/q2_stage_template.sql",
                      parts["window"], parts["other"], read_top20_domains(cfg), inline=a.inline_partitions or None)
    res = onescan_result(q2, cb)
    onescan_path(cfg, a.rung).parent.mkdir(parents=True, exist_ok=True)
    onescan_path(cfg, a.rung).write_text(json.dumps(res, indent=1))
    log(cfg, f"one-scan test {a.rung} (D4.4(i)): Q2 {q2/1e9:.1f} GB vs sum of columns {res['sum_column_bytes']/1e9:.1f} GB, "
             f"diff {res['rel_diff']:.2%} -> {'PASS' if res['ok'] else 'FAIL: use form (ii) or (iii)'}")


def cmd_ladder(a, cfg):
    c = get_client(cfg)
    ledger = Ledger(rpath(cfg, "ledger"))
    pre = None
    if gate0_path(cfg).exists():
        pre = int(json.loads(gate0_path(cfg).read_text())["bytes"])  # Gate-0 (pre-project) reading only (V7)
    else:
        pre = get_quota_used(c, cfg, ledger=ledger)
        if pre is not None:
            print("WARNING: no recorded Gate-0 quota reading; using the live reading, which may include project spend. "
                  "Run `quota --record-gate0` before the first project job.")
    if pre is None:
        pre = cfg.get("quota_used_override_bytes")
    if pre is None:
        print(QUOTA_HELP.format(project=cfg["project"]))
        sys.exit("quota unknown: cannot recommend a rung")
    limit = gb(cfg, cfg["caps"]["stage_gb"]["q2"]) - int(pre)
    srcs = read_top20_domains(cfg)  # source list does not change billed bytes
    rows, rec = [], None
    for rung in ("L0", "L1", "L2", "L3", "L4"):
        parts = rung_parts(cfg, rung)
        b = q2_split_dry(c, cfg, ledger, f"ladder_{rung}", f"{cfg['paths']['sql_dir']}/q2_stage_template.sql",
                         parts["window"], parts["other"], srcs, inline=a.inline_partitions or None)
        rows.append((rung, len(parts["window"]), len(parts["other"]), b))
        if a.columns:
            cb = colbytes(c, cfg, ledger, rung, parts, inline=a.inline_partitions or None)
            res = onescan_result(b, cb)
            onescan_path(cfg, rung).parent.mkdir(parents=True, exist_ok=True)
            onescan_path(cfg, rung).write_text(json.dumps(res, indent=1))
            log(cfg, f"  one-scan test {rung}: diff {res['rel_diff']:.2%} -> {'PASS' if res['ok'] else 'FAIL'}")
        if rec is None and b <= limit:
            rec = rung
    log(cfg, f"quota used before project {int(pre)/1e9:.1f} GB; Q2 limit = {cfg['caps']['stage_gb']['q2']} GB - quota = {limit/1e9:.1f} GB")
    print(f"{'rung':5}{'window_d':>10}{'other_d':>9}{'dry_run_GB':>12}  fits")
    for rung, nw, no, b in rows:
        print(f"{rung:5}{nw:>10}{no:>9}{b/1e9:>12.1f}  {'yes' if b <= limit else 'no'}")
    if rec:
        log(cfg, f"RECOMMENDED (lowest rung that fits): {rec}  -> record at Gate 0b, set `rung` in config.yaml")
    else:
        log(cfg, "NO RUNG FITS: escalate at Gate 0b (raw files for non-window days, D6 route, or window-only design)")
    Path(rpath(cfg, "plan_dir")).mkdir(parents=True, exist_ok=True)
    (rpath(cfg, "plan_dir") / "ladder.json").write_text(json.dumps(
        {"quota_pre_project": int(pre), "limit": limit, "recommended": rec,
         "rungs": [dict(rung=r, window_days=w, other_days=o, dry_run_bytes=b) for r, w, o, b in rows]}, indent=1))


def plan_path(cfg, rung, stage):
    return rpath(cfg, "plan_dir") / f"plan_{rung}_{stage}.json"


def cmd_plan(a, cfg):
    rung = a.rung or cfg["rung"] or sys.exit("set rung (config.yaml or --rung) after Gate 0b")
    one = onescan_path(cfg, rung)
    if not one.exists() or not json.loads(one.read_text()).get("ok"):
        sys.exit(f"REFUSED: D4.4(i) one-scan test for {rung} missing or failed ({one}); run `ladder --columns` or `colbytes --rung {rung}`")
    c = get_client(cfg)
    ledger = Ledger(rpath(cfg, "ledger"))
    sources = read_sources(cfg)  # the frozen superset: its hash is part of each job's hash
    allparts = rung_parts(cfg, rung)
    parts = split_stage(allparts, a.stage, D(cfg["stage_a_start"]))
    # chunks are split so that the CAP (dry x 1.05) stays within the scan limit
    limit = int(gb(cfg, cfg["caps"]["per_job_scan_gb"]["q2"]) / cfg["caps"]["cap_multiplier"])
    chunks = []
    for ch in month_chunks(parts):
        def bytes_fn(x):
            return do_dry_run(c, cfg, ledger, "q2_plan", q2_sql_for(cfg, x["window"], x["other"]),
                              build_q2_params(x["window"], x["other"], sources, cfg), inline=a.inline_partitions or None)
        chunks.extend(split_chunk(ch, bytes_fn, limit))
    per_group: dict[str, int] = {}
    for ch in chunks:
        per_group[ch["group"]] = per_group.get(ch["group"], 0) + 1
    seen: dict[str, int] = {}
    for ch in chunks:
        seen[ch["group"]] = seen.get(ch["group"], 0) + 1
        suffix = f"_{chr(96 + seen[ch['group']])}" if per_group[ch["group"]] > 1 else ""
        ch["label"] = f"q2_{a.stage}_{rung}_{ch['group']}{suffix}"
    # re-dry-run under the final label so the ledger holds the exact hash used at run time
    for ch in chunks:
        do_dry_run(c, cfg, ledger, ch["label"], q2_sql_for(cfg, ch["window"], ch["other"]),
                   build_q2_params(ch["window"], ch["other"], sources, cfg),
                   inline=a.inline_partitions or None)
    grid = set(grid_days(max(D(cfg["rungs"][rung]["start"]), D(cfg["table_first_partition"])), D(cfg["sample_end"]),
                         int(cfg["rungs"][rung]["step"]), int(cfg["seed"]), D(cfg["grid_epoch"])))
    plan = {"rung": rung, "stage": a.stage, "first_group": chunks[0]["group"] if chunks else None,
            "total_dry_run_bytes": sum(ch["dry_run_bytes"] for ch in chunks),
            "chunks": [dict(ch, window=[ts(d) for d in ch["window"]], other=[ts(d) for d in ch["other"]],
                            on_grid=[ts(d) for d in sorted(set(ch["window"]) | set(ch["other"])) if d in grid])
                       for ch in chunks]}
    sibling = plan_path(cfg, rung, "B" if a.stage == "A" else "A")
    plans = [plan] + ([json.loads(sibling.read_text())] if sibling.exists() else [])
    try:
        check_plan_budget(cfg, ledger, plans)
    except Refused as e:
        sys.exit(f"REFUSED: {e}")
    plan_path(cfg, rung, a.stage).parent.mkdir(parents=True, exist_ok=True)
    plan_path(cfg, rung, a.stage).write_text(json.dumps(plan, indent=1))
    log(cfg, f"plan written: {plan_path(cfg, rung, a.stage)}; {len(chunks)} chunks, total {plan['total_dry_run_bytes']/1e9:.1f} GB")


def checked_marker(cfg, rung, stage):
    return rpath(cfg, "plan_dir") / f"CHECKED_{rung}_{stage}"


def cmd_run_chunk(a, cfg):
    plan = json.loads(plan_path(cfg, a.rung, a.stage).read_text())
    ch = next((x for x in plan["chunks"] if x["label"] == a.label), None)
    if ch is None:
        sys.exit(f"label not in plan: {[x['label'] for x in plan['chunks']]}")
    sources = read_sources(cfg)
    params = build_q2_params([D(d) for d in ch["window"]], [D(d) for d in ch["other"]], sources, cfg)
    c = get_client(cfg)
    try:  # all gates (freeze, first-month check, stage cap, plan budget) live in do_run
        do_run(c, cfg, Ledger(rpath(cfg, "ledger")), ch["label"], q2_sql_for(cfg, [D(d) for d in ch["window"]], [D(d) for d in ch["other"]]),
               params, rpath(cfg, "out_dir") / ch["label"], inline=a.inline_partitions or None, allow_rerun=a.allow_rerun)
    except Refused as e:
        sys.exit(f"REFUSED: {e}")


def cmd_mark_checked(a, cfg):
    plan = json.loads(plan_path(cfg, a.rung, a.stage).read_text())
    ok = Ledger(rpath(cfg, "ledger")).ok_labels()
    first = [x for x in plan["chunks"] if x["group"] == plan["first_group"]]
    if not all(x["label"] in ok for x in first):
        sys.exit("first-group chunks are not all RUN_OK in the ledger")
    m = checked_marker(cfg, a.rung, a.stage)
    m.write_text(f"checked {dt.datetime.now(dt.timezone.utc).isoformat()} by {a.by}\n")
    print(f"marked {m}")


def cmd_seed_sources(a, cfg):
    import pandas as pd
    q1 = rpath(cfg, "q1_result")
    if not q1.exists():
        sys.exit(f"Q1 output {q1} not found: Q1 must finish before the source list is seeded (D34 fix)")
    if q1.is_dir():
        df = pd.concat([pd.read_parquet(f) for f in sorted(q1.glob("part-*.parquet"))], ignore_index=True)
    else:
        df = pd.read_parquet(q1) if q1.suffix == ".parquet" else pd.read_csv(q1)
    rows = build_source_superset(cfg, df)
    out = rpath(cfg, "source_superset")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "origin"])
        w.writerows(rows)
    print(f"{len(rows)} domains written to {out}. PRINT AND REVIEW at Gate 1a:")
    for d, why in rows[: a.show]:
        print(f"  {d:40} {why}")


def cmd_freeze(a, cfg):
    """Gate 1a (human): freezes the outlet list AND the theme definitions (price_alt, trim_themes)."""
    sup = rpath(cfg, "source_superset")
    if not sup.exists():
        sys.exit("source_superset.csv missing; run seed-sources")
    if "theme_lookup" not in Ledger(rpath(cfg, "ledger")).ok_labels():
        sys.exit("theme_lookup has no RUN_OK ledger row: run it and set price_alt from its output first (D9)")
    if not cfg.get("price_alt_confirmed"):
        sys.exit("set price_alt_confirmed: true in config.yaml after replacing the placeholder price_alt using the theme lookup")
    f = Path(cfg["_root"]) / "data/processed/gate1a_frozen.json"
    f.write_text(json.dumps({"sha256": file_sha(sup), "price_alt": cfg["price_alt"],
                             "trim_themes": bool(cfg.get("trim_themes", False)),
                             "themes": sorted(cfg["price_alt"].split("|")), "by": a.by,
                             "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}, indent=1))
    print(f"frozen outlets + themes -> {f}")


def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    sub = p.add_subparsers(dest="cmd", required=True)

    def job_args(s):
        s.add_argument("--job", choices=STD_CHOICES)
        s.add_argument("--sql"); s.add_argument("--label"); s.add_argument("--params-file")
        s.add_argument("--inline-partitions", action="store_true")
    s = sub.add_parser("quota", help="quota used this month (ledgered, capped)"); s.add_argument("--scope", default="user")
    s.add_argument("--record-gate0", action="store_true", help="store the pre-project reading used by `ladder`")
    s.add_argument("--force", action="store_true"); s.set_defaults(f=cmd_quota)
    s = sub.add_parser("dryrun", help="dry-run a SQL file and log it"); job_args(s); s.set_defaults(f=cmd_dryrun)
    s = sub.add_parser("run", help="run a dry-run job under all caps"); job_args(s)
    s.add_argument("--out"); s.add_argument("--allow-rerun", action="store_true"); s.set_defaults(f=cmd_run)
    s = sub.add_parser("export", help="re-download a finished job's result (after EXPORT_FAILED)")
    s.add_argument("--job-id", required=True); s.add_argument("--label", required=True); s.add_argument("--out"); s.set_defaults(f=cmd_export)
    s = sub.add_parser("partitions", help="show partition counts for a rung")
    s.add_argument("--rung", choices=list("L0 L1 L2 L3 L4".split())); s.add_argument("--stage", default="all", choices=["A", "B", "all"])
    s.add_argument("--out"); s.set_defaults(f=cmd_partitions)
    s = sub.add_parser("ladder", help="dry-run every rung; recommend the lowest that fits")
    s.add_argument("--columns", action="store_true", help="also dry-run bytes per column and run the D4.4(i) one-scan test")
    s.add_argument("--inline-partitions", action="store_true"); s.set_defaults(f=cmd_ladder)
    s = sub.add_parser("colbytes", help="bytes per column + one-scan test for one rung")
    s.add_argument("--rung", required=True); s.add_argument("--inline-partitions", action="store_true"); s.set_defaults(f=cmd_colbytes)
    s = sub.add_parser("plan", help="monthly chunk plan with dry runs; halves chunks whose cap exceeds the scan limit")
    s.add_argument("--rung"); s.add_argument("--stage", required=True, choices=["A", "B"]); s.add_argument("--inline-partitions", action="store_true"); s.set_defaults(f=cmd_plan)
    s = sub.add_parser("run-chunk"); s.add_argument("--rung", required=True); s.add_argument("--stage", required=True, choices=["A", "B"])
    s.add_argument("--label", required=True); s.add_argument("--allow-rerun", action="store_true"); s.add_argument("--inline-partitions", action="store_true"); s.set_defaults(f=cmd_run_chunk)
    s = sub.add_parser("mark-checked"); s.add_argument("--rung", required=True); s.add_argument("--stage", required=True, choices=["A", "B"]); s.add_argument("--by", required=True); s.set_defaults(f=cmd_mark_checked)
    s = sub.add_parser("seed-sources"); s.add_argument("--show", type=int, default=100000); s.set_defaults(f=cmd_seed_sources)
    s = sub.add_parser("freeze-outlets", help="Gate 1a (human): freeze outlets and themes"); s.add_argument("--by", required=True); s.set_defaults(f=cmd_freeze)
    return p


def main(argv=None):
    a = build_parser().parse_args(argv)
    cfg = load_config(a.config)
    a.f(a, cfg)


if __name__ == "__main__":
    main()
