import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bq_runner as r  # noqa: E402

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


@pytest.fixture
def cfg(tmp_path):
    c = r.load_config()
    c["_root"] = tmp_path
    return c


@pytest.fixture
def rounds():
    # 3 synthetic rounds, enough for structure tests
    return [("r1", dt.date(2022, 3, 10), dt.date(2022, 3, 20)),
            ("r2", dt.date(2023, 3, 9), dt.date(2023, 3, 19)),
            ("r3", dt.date(2024, 6, 1), dt.date(2024, 6, 10))]


def test_steps_never_multiples_of_seven():
    assert all(s % 7 for s in r.ALLOWED_STEPS)
    for bad in (7, 14, 5, 8):
        with pytest.raises(ValueError):
            r.grid_offset(1, bad)


@pytest.mark.parametrize("step", [1, 2, 3, 4, 6])
def test_grid_rotates_weekdays_and_is_deterministic(step):
    days = r.grid_days(dt.date(2017, 1, 1), dt.date(2018, 12, 31), step, 123, dt.date(2015, 2, 18))
    assert {d.weekday() for d in days} == set(range(7))
    assert days == r.grid_days(dt.date(2017, 1, 1), dt.date(2018, 12, 31), step, 123, dt.date(2015, 2, 18))
    gaps = {(b - a).days for a, b in zip(days, days[1:])}
    assert gaps == {step}


def test_offset_seeded(cfg):
    assert r.grid_offset(5, 6) == r.grid_offset(5, 6)
    assert 0 <= r.grid_offset(5, 6) < 6


def test_rung_partitions(cfg, rounds):
    p = r.build_partitions(cfg, "L2", rounds)
    assert len(p["window"]) == 21 * 3
    assert dt.date(2022, 3, 9) in p["window"] and dt.date(2022, 3, 10) not in p["window"]
    assert not set(p["window"]) & set(p["other"])
    # always-sampled placebo dates +/- 3 are present (in window or other)
    allv = set(p["window"]) | set(p["other"])
    for c in cfg["always_sampled"]:
        for k in range(-3, 4):
            assert dt.date.fromisoformat(c) + dt.timedelta(days=k) in allv
    assert all(dt.date(2015, 2, 18) <= d <= dt.date(2026, 10, 31) for d in allv)
    # L4 starts 2017, L3 2016
    assert min(r.build_partitions(cfg, "L4", rounds)["other"]) >= dt.date(2017, 1, 1)
    assert min(r.build_partitions(cfg, "L3", rounds)["other"]) >= dt.date(2016, 1, 1)
    # L0 is every day
    p0 = r.build_partitions(cfg, "L0", rounds)
    assert len(p0["window"]) + len(p0["other"]) == (dt.date(2026, 10, 31) - dt.date(2015, 2, 18)).days + 1
    assert len(p0["window"]) == 30 * 3


def test_stage_split_and_chunks(cfg, rounds):
    p = r.build_partitions(cfg, "L4", rounds)
    a = r.split_stage(p, "A", dt.date(2022, 1, 1)); b = r.split_stage(p, "B", dt.date(2022, 1, 1))
    assert a["other"] == [] and len(a["window"]) == len(p["window"])  # all 3 rounds are >= 2022
    assert len(b["other"]) == len(p["other"])
    months = r.month_chunks(a)
    assert months[0]["group"] == "2022-02"


def test_split_chunk_halves_until_limit():
    days = [dt.date(2022, 1, d) for d in range(1, 29)]
    ch = {"group": "2022-01", "window": days, "other": []}
    fn = lambda c: 10 * (len(c["window"]) + len(c["other"]))  # noqa: E731
    out = r.split_chunk(ch, fn, 100)
    assert all(c["dry_run_bytes"] <= 100 for c in out)
    assert sorted(d for c in out for d in c["window"]) == days
    assert len(out) >= 3


def test_inline_partitions_and_hash():
    sql = "SELECT 1 WHERE t IN UNNEST(@window_ts) AND u IN UNNEST(@other_ts) AND s IN UNNEST(@sources)"
    params = {"window_ts": {"type": "ARRAY<TIMESTAMP>", "value": ["2022-01-01", "2022-01-02"]},
              "other_ts": {"type": "ARRAY<TIMESTAMP>", "value": []},
              "sources": {"type": "ARRAY<STRING>", "value": ["a.com"]}}
    s2, p2 = r.inline_partitions(sql, params)
    assert "TIMESTAMP '2022-01-02'" in s2 and "ARRAY<TIMESTAMP>[]" in s2 and "@sources" in s2
    assert set(p2) == {"sources"}
    assert r.params_hash(sql, params) == r.params_hash(sql, params)
    assert r.params_hash(sql, params) != r.params_hash(sql + " ", params)


def _ledger(tmp_path):
    return r.Ledger(tmp_path / "logs" / "ledger.csv")


def test_ledger_columns_and_committed(cfg, tmp_path):
    L = _ledger(tmp_path)
    L.append(job_label="q2_A_x", sql_file="f", params_hash="h1", dry_run_bytes=10, cap_bytes=11, status="DRYRUN")
    L.append(job_label="q2_A_x", sql_file="f", params_hash="h1", dry_run_bytes=10, cap_bytes=11, status="RUN_STARTED")
    assert L.committed()["pending"] == 11 and L.committed()["actual"] == 0
    L.append(job_label="q2_A_x", sql_file="f", params_hash="h1", dry_run_bytes=10, cap_bytes=11,
             actual_billed_bytes=9, status="RUN_OK")
    c = L.committed()
    assert c["actual"] == 9 and c["pending"] == 0 and c["by_stage"]["q2"] == 9
    with open(L.path) as fh:
        assert next(csv.reader(fh)) == r.LEDGER_COLUMNS


def test_cap_refusals(cfg, tmp_path):
    L = _ledger(tmp_path)
    G = 10**9
    # ok case
    r.check_run_allowed(L, cfg, "q2_A_x", "h", 50 * G, math.ceil(52.5 * G), quota_used=0)
    # per-job scan limit (60 GB)
    with pytest.raises(r.Refused, match="per-job"):
        r.check_run_allowed(L, cfg, "q2_A_x", "h", 61 * G, 65 * G, quota_used=0)
    # hard project cap 670 GB, quota already high
    with pytest.raises(r.Refused, match="hard cap"):
        r.check_run_allowed(L, cfg, "q2_A_x", "h", 50 * G, 53 * G, quota_used=630 * G)
    # unknown quota is refused
    cfg["quota_used_override_bytes"] = None
    with pytest.raises(r.Refused, match="quota"):
        r.check_run_allowed(L, cfg, "q2_A_x", "h", G, G, quota_used=None)
    # stage cap: Q2 already at 640 GB from the ledger, job cap 20 GB -> 660 > 650
    for i in range(16):
        L.append(job_label=f"q2_B_{i}", sql_file="f", params_hash=f"h{i}", cap_bytes=40 * G,
                 actual_billed_bytes=40 * G, status="RUN_OK")
    with pytest.raises(r.Refused, match="stage cap"):
        r.check_run_allowed(L, cfg, "q2_B_new", "hz", 19 * G, 20 * G, quota_used=0)
    # non-q2 stage unaffected by stage cap but still hard cap (ledger actual 640 + 31 > 670)
    with pytest.raises(r.Refused, match="hard cap"):
        r.check_run_allowed(L, cfg, "q1_outlets", "hq", 30 * G, 31 * G, quota_used=0)
    r.check_run_allowed(L, cfg, "q1_outlets", "hq", 9 * G, 10 * G, quota_used=0)


def test_pending_jobs_count(cfg, tmp_path):
    L = _ledger(tmp_path); G = 10**9
    L.append(job_label="q2_A_p", sql_file="f", params_hash="hp", cap_bytes=60 * G, status="RUN_STARTED")
    with pytest.raises(r.Refused):
        r.check_run_allowed(L, cfg, "q2_A_n", "h", 50 * G, 52 * G, quota_used=620 * G)


def test_run_refused_without_dry_run(cfg, tmp_path):
    (tmp_path / "scripts/sql").mkdir(parents=True)
    (tmp_path / "scripts/sql/x.sql").write_text("SELECT 1")
    L = _ledger(tmp_path)
    with pytest.raises(r.Refused, match="no dry run"):
        r.do_run(None, cfg, L, "q1_outlets", "scripts/sql/x.sql", {}, tmp_path / "out")
    assert L.rows()[-1]["status"].startswith("REFUSED")


def _plan(tmp_path, cfg, label="q2_A_L2_2022-01", group="2022-01", first="2022-01"):
    d = tmp_path / cfg["paths"]["plan_dir"]; d.mkdir(parents=True, exist_ok=True)
    plan = {"rung": "L2", "stage": "A", "first_group": first, "total_dry_run_bytes": 1,
            "chunks": [{"label": label, "group": group, "window": ["2022-01-02"], "other": [], "dry_run_bytes": 10}]}
    (d / "plan_L2_A.json").write_text(json.dumps(plan))
    return plan


def test_q2_gate_full_chain(cfg, tmp_path):
    L = _ledger(tmp_path)
    lab = "q2_A_L2_2022-01"
    prm = {"window_ts": {"type": "ARRAY<TIMESTAMP>", "value": ["2022-01-02"]}, "other_ts": {"type": "ARRAY<TIMESTAMP>", "value": []}}
    with pytest.raises(r.Refused, match="probe_one_partition"):
        r.gate_q2_prereqs(cfg, L, lab, prm)
    for x in ("probe_one_partition", "q1_outlets"):
        L.append(job_label=x, sql_file="f", params_hash="h" + x, cap_bytes=1, actual_billed_bytes=1, status="RUN_OK")
    with pytest.raises(r.Refused, match="theme_lookup"):
        r.gate_q2_prereqs(cfg, L, lab, prm)
    L.append(job_label="theme_lookup", sql_file="f", params_hash="ht", cap_bytes=1, actual_billed_bytes=1, status="RUN_OK")
    with pytest.raises(r.Refused, match="freeze"):
        r.gate_q2_prereqs(cfg, L, lab, prm)
    sup = tmp_path / cfg["paths"]["source_superset"]; sup.parent.mkdir(parents=True)
    sup.write_text("domain,origin\na.com,top20\n")
    fz = tmp_path / "data/processed/gate1a_frozen.json"
    fz.write_text(json.dumps({"sha256": r.file_sha(sup), "price_alt": "WRONG", "trim_themes": False}))
    with pytest.raises(r.Refused, match="price_alt"):
        r.gate_q2_prereqs(cfg, L, lab, prm)
    fz.write_text(json.dumps({"sha256": r.file_sha(sup), "price_alt": cfg["price_alt"], "trim_themes": False}))
    with pytest.raises(r.Refused, match="not in any plan"):
        r.gate_q2_prereqs(cfg, L, lab, prm)
    _plan(tmp_path, cfg)
    r.gate_q2_prereqs(cfg, L, lab, prm)  # first month: allowed
    with pytest.raises(r.Refused, match="do not match"):
        r.gate_q2_prereqs(cfg, L, lab, dict(prm, window_ts={"type": "x", "value": ["2022-01-09"]}))
    _plan(tmp_path, cfg, label="q2_A_L2_2022-02", group="2022-02")
    with pytest.raises(r.Refused, match="first one-month"):
        r.gate_q2_prereqs(cfg, L, "q2_A_L2_2022-02", {})
    (tmp_path / cfg["paths"]["plan_dir"] / "CHECKED_L2_A").write_text("x")
    r.gate_q2_prereqs(cfg, L, "q2_A_L2_2022-02", {})
    # hash mismatch of the frozen source list
    sup.write_text("domain,origin\na.com,top20\nb.com,x\n")
    with pytest.raises(r.Refused, match="hash mismatch"):
        r.gate_q2_prereqs(cfg, L, "q2_A_L2_2022-02", {})
    r.gate_q2_prereqs(cfg, L, "q1_outlets", {})  # non-q2 jobs are not gated


def test_plan_budget_refused(cfg, tmp_path):
    L = _ledger(tmp_path)
    plan = {"chunks": [{"label": "q2_A_x", "dry_run_bytes": 400 * 10**9}, {"label": "q2_A_y", "dry_run_bytes": 260 * 10**9}]}
    with pytest.raises(r.Refused, match="does not fit"):
        r.check_plan_budget(cfg, L, [plan])
    L.append(job_label="q2_A_x", sql_file="f", params_hash="h", cap_bytes=1, actual_billed_bytes=1, status="RUN_OK")
    r.check_plan_budget(cfg, L, [plan])  # x done: only 260 GB left


def test_onescan_result():
    assert r.onescan_result(1000, {"a": 600, "b": 400})["ok"]
    assert not r.onescan_result(1300, {"a": 600, "b": 400})["ok"]


def test_export_failed_counts_billed_and_retry_adds_zero(cfg, tmp_path):
    L = _ledger(tmp_path); G = 10**9
    L.append(job_label="q2_A_x", sql_file="f", params_hash="h", cap_bytes=50 * G, status="RUN_STARTED")
    L.append(job_label="q2_A_x", sql_file="f", params_hash="h", cap_bytes=50 * G, actual_billed_bytes=40 * G, status="EXPORT_FAILED", job_id="j1")
    L.append(job_label="q2_A_x", sql_file="f", params_hash="h", cap_bytes=50 * G, actual_billed_bytes=0, status="RUN_OK", job_id="j1")
    assert L.committed()["actual"] == 40 * G and L.committed()["pending"] == 0


def test_url_section_regex_keeps_three_dirs():
    import re
    pat = re.compile(r"^https?://[^/]+/((?:[^/?#]+/){1,3})")
    assert pat.match("https://x.com/local/rajasthan/jaipur/news/a-story.html").group(1) == "local/rajasthan/jaipur/"
    assert pat.match("https://timesofindia.indiatimes.com/city/mumbai/story/articleshow/1.cms?x=1").group(1) == "city/mumbai/story/"
    assert pat.match("https://x.com/a.html") is None


def test_daycount_job_and_sql(cfg):
    cfg["_root"] = Path(__file__).resolve().parents[2]
    cfg["rung"] = "L4"
    assert (SQL_DIR / "global_daily_count.sql").exists()


def test_seed_has_vernacular_majors():
    p = Path(__file__).resolve().parents[1] / "seeds/top20_indian_outlets.csv"
    doms = {x["domain"] for x in csv.DictReader(open(p))}
    for d in ("manoramaonline.com", "dailythanthi.com", "patrika.com", "dinakaran.com", "sakshi.com",
              "gujaratsamachar.com", "divyabhaskar.co.in", "esakal.com", "punjabkesari.in", "prabhatkhabar.com"):
        assert d in doms


def test_source_superset(cfg, tmp_path):
    import pandas as pd
    cfg["_root"] = Path(__file__).resolve().parents[2]  # real top20 seed
    look = tmp_path / "lookup.tsv"
    look.write_text("example.in\tIN\nbbc.co.uk\tUK\nprint.com\tIndia\n")
    cfg["paths"] = dict(cfg["paths"], domain_country_lookup=str(look))
    q1 = pd.DataFrame({"domain": ["vernac.com", "eng.com", "foo.in"], "is_in_domain": [False, False, True],
                       "is_indian_lang": [True, False, False]})
    got = dict(r.build_source_superset(cfg, q1))
    assert "thehindu.com" in got and "indiatimes.com" in got  # parent of timesofindia.indiatimes.com
    assert "example.in" in got and "print.com" in got and "bbc.co.uk" not in got
    assert "vernac.com" in got and "foo.in" in got and "eng.com" not in got


def test_top20_seed_columns():
    p = Path(__file__).resolve().parents[1] / "seeds/top20_indian_outlets.csv"
    rows = list(csv.DictReader(open(p)))
    assert len(rows) >= 20 and {"domain", "language", "single_state"} <= set(rows[0])
    assert all(x["single_state"] in ("Y", "N") for x in rows)


def test_sql_files_parse_and_have_params():
    sqlglot = pytest.importorskip("sqlglot")
    for f in SQL_DIR.glob("*.sql"):
        sqlglot.parse(f.read_text(), read="bigquery")
    q2 = (SQL_DIR / "q2_stage_template.sql").read_text()
    for ptxt in ("@window_ts", "@other_ts", "@sources", "@price_alt", "@trim_themes"):
        assert ptxt in q2
    # every table reference is partition-filtered and the forbidden columns are never read (comments ignored)
    for f in SQL_DIR.glob("*.sql"):
        body = "\n".join(l for l in f.read_text().splitlines() if not l.strip().startswith("--"))
        assert body.count("gkg_partitioned") == body.count("_PARTITIONTIME IN UNNEST") + body.count("_PARTITIONTIME = TIMESTAMP"), f.name
        for bad in ("GCAM", "V2Locations", "V2Themes", " Locations"):
            assert bad not in body, (f.name, bad)


def test_std_jobs_build(cfg):
    cfg["_root"] = Path(__file__).resolve().parents[2]
    for name in ("probe", "q1", "theme"):
        label, f, params = r.build_std_job(name, cfg)
        assert (cfg["_root"] / f).exists() and params
    q1 = r.q1_partitions(cfg)
    assert {(b - a).days for a, b in zip(q1, q1[1:])} == {6}
