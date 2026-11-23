"""Verifier tests (independent check of bq_runner.py against design_final D1-D4, D36). All defects V1-V5 fixed; xfail marks removed."""
import datetime as dt
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bq_runner as r  # noqa: E402

G = 10**9
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


@pytest.fixture
def cfg(tmp_path):
    c = r.load_config()
    c["_root"] = tmp_path
    return c


def L(tmp_path):
    return r.Ledger(tmp_path / "logs" / "budget_ledger.csv")


def test_ledger_path_in_logs(cfg):
    assert cfg["paths"]["ledger"].startswith("logs/")


def test_ledger_append_only(cfg, tmp_path):
    led = L(tmp_path)
    led.append(job_label="a", status="DRYRUN")
    first = led.path.read_text()
    led.append(job_label="b", status="DRYRUN")
    assert led.path.read_text().startswith(first)
    assert len(led.rows()) == 2


def test_cap_is_ceil_105(cfg):
    for b in (1, 999, 2_123_456_789, 59 * G + 7):
        assert math.ceil(b * cfg["caps"]["cap_multiplier"]) >= b * 1.05


def test_always_sampled_and_window_end(cfg):
    rounds = [("r", dt.date(2019, 6, 1), dt.date(2019, 6, 10))]
    for rung in ("L0", "L1", "L2", "L3", "L4"):
        p = r.build_partitions(cfg, rung, rounds)
        allv = set(p["window"]) | set(p["other"])
        for c in ("2019-05-23", "2024-06-04", "2023-11-19"):
            for k in range(-3, 4):
                assert dt.date.fromisoformat(c) + dt.timedelta(days=k) in allv, (rung, c, k)
        assert max(p["window"]) == dt.date(2019, 5, 31)
        assert dt.date(2019, 6, 1) not in p["window"]
        n = cfg["rungs"][rung]["window_days"]
        assert len(p["window"]) == n


def test_rung_table_matches_D4(cfg):
    want = {"L0": (30, 1, "2015"), "L1": (30, 2, "2015"), "L2": (21, 3, "2015"),
            "L3": (14, 4, "2016-01"), "L4": (14, 6, "2017-01")}
    for k, (w, s, st) in want.items():
        spec = cfg["rungs"][k]
        assert spec["window_days"] == w and spec["step"] == s and str(spec["start"]).startswith(st)


def test_q2_columns_full_vs_reduced():
    sqlglot = pytest.importorskip("sqlglot")
    from sqlglot import exp
    tree = sqlglot.parse_one((SQL_DIR / "q2_stage_template.sql").read_text(), read="bigquery")
    ctes = {c.alias: c.this for c in tree.find_all(exp.CTE)}
    def cols(q):
        return {c.name for c in q.find_all(exp.Column)} - {"_PARTITIONTIME"}
    assert cols(ctes["win"]) == set(r.FULL_COLUMNS)
    assert cols(ctes["oth"]) == set(r.REDUCED_COLUMNS)
    # every branch of the UNION ALL has the same number of output columns
    widths = {k: len(ctes[k].expressions) for k in ("a_win", "a_oth", "s_win", "d_oth")}
    assert len(set(widths.values())) == 1, widths


# ---------------- defects (xfail = documented failure) ----------------

def test_rerun_keeps_earlier_cost(cfg, tmp_path):
    led = L(tmp_path)
    led.append(job_label="q2_A_x", params_hash="h", cap_bytes=50 * G, actual_billed_bytes=48 * G, status="RUN_FAILED")
    led.append(job_label="q2_A_x", params_hash="h", cap_bytes=50 * G, actual_billed_bytes=48 * G, status="RUN_OK")
    assert led.committed()["actual"] == 96 * G


def test_failed_counted_at_cap(cfg, tmp_path):
    led = L(tmp_path)
    led.append(job_label="q2_A_x", params_hash="h", cap_bytes=50 * G, actual_billed_bytes=0, status="RUN_FAILED")
    assert led.committed()["actual"] == 50 * G


def test_override_quota_added_to_ledger(cfg, tmp_path):
    led = L(tmp_path)
    for i in range(10):
        led.append(job_label=f"q2_B_{i}", params_hash=f"h{i}", cap_bytes=55 * G, actual_billed_bytes=55 * G, status="RUN_OK")
    cfg["quota_used_override_bytes"] = 100 * G  # used before the project started
    # true spend 100 + 550 = 650; a 30 GB job takes it to 680 > 670 -> must refuse
    with pytest.raises(r.Refused):
        r.check_run_allowed(led, cfg, "theme_lookup", "hx", 28 * G, 30 * G, quota_used=None)


def test_per_job_cap_not_above_60(cfg, tmp_path):
    with pytest.raises(r.Refused):
        r.check_run_allowed(L(tmp_path), cfg, "q2_A_x", "h", 59 * G, math.ceil(59 * G * 1.05), quota_used=0)


def test_q2_gate_by_sql_file(cfg, tmp_path):
    (tmp_path / "scripts/sql").mkdir(parents=True)
    (tmp_path / "scripts/sql/q2_stage_template.sql").write_text((SQL_DIR / "q2_stage_template.sql").read_text())
    led = L(tmp_path)
    sql, p, h = r.prepare(cfg, "scripts/sql/q2_stage_template.sql", {}, False)
    led.append(job_label="stageA_2022", sql_file="scripts/sql/q2_stage_template.sql", params_hash=h,
               dry_run_bytes=10 * G, cap_bytes=11 * G, status="DRYRUN")
    cfg["quota_used_override_bytes"] = 0
    class FakeClient:  # would be reached only if every gate passed
        def query(self, *a, **k):
            raise RuntimeError("REACHED BIGQUERY")
    with pytest.raises(r.Refused):
        r.do_run(FakeClient(), cfg, led, "stageA_2022", "scripts/sql/q2_stage_template.sql", {}, tmp_path / "o")


# ---------------- re-verification (round 2) ----------------
import re as _re


def test_crashed_start_is_reconciled_before_rerun(cfg, tmp_path):
    """R1: an orphaned RUN_STARTED (runner killed after submit) is closed from BigQuery by its pre-assigned job id
    before a re-run, so its billed bytes stay in the ledger; a still-running job blocks the re-run."""
    led = L(tmp_path)
    led.append(job_label="q2_A_x", params_hash="h", cap_bytes=50 * G, status="RUN_STARTED", job_id="j1")
    class Job:
        def __init__(self, state): self.state, self.total_bytes_billed, self.error_result, self.destination = state, 48 * G, {"x": 1}, None
    class C:
        def __init__(self, state): self.state = state
        def get_job(self, jid, location=None): return Job(self.state)
    with pytest.raises(r.Refused):
        r.reconcile_open_jobs(C("RUNNING"), cfg, led, "q2_A_x", "h")
    r.reconcile_open_jobs(C("DONE"), cfg, led, "q2_A_x", "h")
    led.append(job_label="q2_A_x", params_hash="h", cap_bytes=50 * G, status="RUN_STARTED", job_id="j2")
    led.append(job_label="q2_A_x", params_hash="h", cap_bytes=50 * G, actual_billed_bytes=48 * G, status="RUN_OK")
    c = led.committed()
    assert c["actual"] + c["pending"] >= 96 * G


def test_zero_byte_job_cap_meets_minimum_billing(cfg):
    """R2: BigQuery bills at least 10 MiB per query; the cap has a 10 MiB floor."""
    assert r.bq_cap(0, cfg) >= 10 * 1024 * 1024


@pytest.mark.parametrize("url,expect", [
    ("https://timesofindia.indiatimes.com/city/mumbai/onion-prices-soar-in-city/articleshow/123456.cms", "city/mumbai/"),
    ("https://www.thehindu.com/news/cities/Delhi/", "news/cities/Delhi/"),
    ("https://www.bhaskar.com/local/rajasthan/jaipur/news/onion-price-130000000.html", "local/rajasthan/jaipur/"),
    ("https://indianexpress.com/article/cities/mumbai/onion-prices-9000000/", "article/cities/mumbai/"),
])
def test_url_section_excludes_slug(url, expect):
    """R3: url_section must not contain the article slug. Python emulation of the SQL in q2_stage_template.sql."""
    sql = (SQL_DIR / "q2_stage_template.sql").read_text()
    assert "LENGTH(s2) > 30" in sql and "[0-9]{4,}" in sql and ">= 3), 3)" in sql
    m = _re.match(r"^https?://[^/]+/((?:[^/?#]+/){1,3})", url)
    segs = m.group(1).split("/") if m else []
    slug = lambda x: len(x) > 30 or _re.search(r"[0-9]{4,}", x) or x.count("-") >= 3
    stop = min([i for i, x in enumerate(segs) if slug(x)] + [3])
    keep = [x for i, x in enumerate(segs) if x and i < stop]
    assert ("/".join(keep) + "/" if keep else None) == expect


def test_parent_domain_not_public_suffix():
    """R4 (nit): divyabhaskar.co.in must not add 'co.in' to the superset."""
    assert r.parent_domain("divyabhaskar.co.in") != "co.in"
