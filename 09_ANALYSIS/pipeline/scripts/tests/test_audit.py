"""Unit tests for scripts/audit/*.

ALL DATA HERE IS SYNTHETIC (tests only). Nothing below is a real article, URL, GDELT record or code.
"""
import csv
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

AUDIT = Path(__file__).resolve().parents[1] / "audit"
sys.path.insert(0, str(AUDIT))

import audit_common as C  # noqa: E402
import audit_metrics as M  # noqa: E402
import fetch_texts as F  # noqa: E402
import llm_code as L  # noqa: E402
import sample_audit as S  # noqa: E402


# ------------------------------------------------------------------ audit_common
def test_kappa_known_values():
    assert C.cohen_kappa(list("YYNN"), list("YYNN")) == pytest.approx(1.0)
    # 2x2: po=0.5, pe=0.5 -> 0
    assert C.cohen_kappa(list("YYNN"), list("YNYN")) == pytest.approx(0.0)
    # textbook example: a=20,b=5,c=10,d=15 -> kappa 0.4
    x = ["Y"] * 20 + ["Y"] * 5 + ["N"] * 10 + ["N"] * 15
    y = ["Y"] * 20 + ["N"] * 5 + ["Y"] * 10 + ["N"] * 15
    assert C.cohen_kappa(x, y) == pytest.approx(0.4)
    assert math.isnan(C.cohen_kappa(list("YYY"), list("YYY")))  # undefined, not 1


def test_clopper_pearson_zero_and_known():
    lo, hi = C.clopper_pearson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025 ** (1 / 10), abs=1e-6)
    lo, hi = C.clopper_pearson(5, 10)
    assert lo == pytest.approx(0.1871, abs=1e-3) and hi == pytest.approx(0.8129, abs=1e-3)
    assert all(math.isnan(v) for v in C.clopper_pearson(0, 0))


def test_f2_and_derivation():
    assert C.f_beta(0.5, 1.0) == pytest.approx(5 * 0.5 / (4 * 0.5 + 1))
    assert C.derive_international("Y", "exchange_rate") == 1
    assert C.derive_international("Y", "monetary_policy") == 0
    assert C.derive_international("Y", "other_none") == 0
    assert C.derive_international("N", "exchange_rate") is None
    assert C.derive_international("Y", None) is None
    assert C.clean_code("bogus", C.CAUSES) is None


# ------------------------------------------------------------------ sample_audit
def synthetic_population(n=40000, seed=1):
    rng = np.random.default_rng(seed)
    lang = rng.choice(["en", "hin", "mar", "ben", "guj"], size=n, p=[0.74, 0.10, 0.07, 0.02, 0.07])
    year = rng.integers(2015, 2026, n)
    day = rng.integers(1, 29, n)
    month = rng.integers(1, 13, n)
    date = [int(f"{y}{m:02d}{d:02d}{rng.integers(0, 24):02d}{rng.integers(0, 60):02d}00") for y, m, d in zip(year, month, day)]
    base = rng.random(n) < 0.08
    econ = base | (rng.random(n) < 0.15)
    words = np.where(rng.random(n) < 0.1, "fuel-price-rises-again", "match-report-today")
    return pd.DataFrame({
        "GKGRECORDID": [f"SYN{i}" for i in range(n)], "DATE": date,
        "DocumentIdentifier": [f"https://synthetic{i % 50}.example/{w}-{i}" for i, w in enumerate(words)],
        "SourceCommonName": [f"synthetic{i % 50}.example" for i in range(n)], "Themes": "SYN",
        "TranslationInfo": [("" if l == "en" else f"srclc:{l}; eng:Moses 2.1.1") for l in lang],
        "flag_baseline": base, "flag_econ": econ, "flag_international": rng.random(n) < 0.2,
    })


@pytest.fixture(scope="module")
def pop_path(tmp_path_factory):
    p = tmp_path_factory.mktemp("pop") / "pop.parquet"
    synthetic_population().to_parquet(p)
    return p


def run_sampler(pop_path, tmp, *extra):
    args = ["--input", str(pop_path), "--manifest-out", str(tmp / "man.csv"), "--key-out", str(tmp / "key.csv"),
            "--sheet-out", str(tmp / "sheet.csv"), "--meta-out", str(tmp / "meta.json"), *extra]
    assert S.main(args) == 0
    return (pd.read_csv(tmp / "man.csv"), pd.read_csv(tmp / "key.csv"), pd.read_csv(tmp / "sheet.csv", dtype=str),
            json.loads((tmp / "meta.json").read_text()))


def test_sampler_strata_weights_human_and_blinding(pop_path, tmp_path):
    man, key, sheet, meta = run_sampler(pop_path, tmp_path)
    counts = key["stratum"].value_counts().to_dict()
    assert counts == {"flagged": 300, "econ_unflagged": 300, "nonecon_slug": 150, "nonecon_noslug": 100,
                      "hin_flagged": 100, "hin_econ_unflagged": 100, "oth_flagged": 100, "oth_econ_unflagged": 100}
    assert meta["other_vernacular"] == "mar"  # synthetic: more Marathi than Bengali
    # exact inverse-probability weights: weights in a stratum sum to the stratum population
    for st, inf in meta["strata"].items():
        assert key.loc[key.stratum == st, "sampling_weight"].sum() == pytest.approx(inf["N"])
    # human subsample: 150 with 40 Hindi; sheet is blind (no stratum / key columns)
    assert meta["human_n"] == 150 and meta["human_hindi_n"] == 40
    assert len(sheet) == 150 and (sheet["language"] == "hin").sum() == 40
    assert set(sheet["language"]) == {"en", "hin"}  # default: English + Hindi only; mar/ben are LLM-only
    assert list(sheet.columns) == ["audit_id", "language", "url", "retrieval_mode", "text_file", "relevance", "direction",
                                   "cause_primary", "cause_secondary", "uncertain", "notes", "coder", "coded_at"]
    assert not any("flag" in c or "stratum" in c or "weight" in c for c in sheet.columns)
    assert set(sheet.audit_id) == set(key.loc[key.human_selected, "audit_id"])
    assert "stratum" not in man.columns
    # audit ids do not leak the stratum through their order
    assert key.sort_values("audit_id")["stratum"].head(40).nunique() > 3


def test_sampler_deterministic_and_oversample(pop_path, tmp_path):
    a = run_sampler(pop_path, tmp_path)[1]
    t2 = tmp_path / "again"
    t2.mkdir()
    b = run_sampler(pop_path, t2)[1]
    pd.testing.assert_frame_equal(a, b)
    pop = synthetic_population()
    pop_share = pop["DATE"].astype(str).str[:4].astype(int).between(2015, 2018).mean()
    yr = key_year = a["gkg_date"].astype(str).str[:4].astype(int)
    gen = a["stratum"].isin(["flagged", "econ_unflagged"])
    samp_share = yr[gen].between(2015, 2018).mean()
    assert samp_share > pop_share * 1.2  # 1.5x tilt on a ~36% share gives ~46%
    t3 = tmp_path / "noos"
    t3.mkdir()
    c = run_sampler(pop_path, t3, "--oversample", "1.0")[1]
    assert c["gkg_date"].astype(str).str[:4].astype(int)[gen.values].between(2015, 2018).mean() < samp_share


def test_sampler_mode_b_requires_days_and_clusters(pop_path, tmp_path):
    with pytest.raises(SystemExit):
        S.main(["--input", str(pop_path), "--mode", "B", "--manifest-out", str(tmp_path / "m.csv"), "--key-out", str(tmp_path / "k.csv"),
                "--sheet-out", str(tmp_path / "s.csv"), "--meta-out", str(tmp_path / "x.json")])
    man, key, sheet, meta = run_sampler(pop_path, tmp_path, "--mode", "B", "--modeb-days", "6")
    late = key[key["gkg_date"].astype(str).str[:4].astype(int) >= 2020]
    assert late["window_day"].nunique() <= 6
    assert meta["oversample_effective"] == 1.0


def test_shortfall_is_reported_not_topped_up(tmp_path):
    pop = synthetic_population(n=6000, seed=3)
    p = tmp_path / "small.parquet"
    pop.to_parquet(p)
    man, key, sheet, meta = run_sampler(p, tmp_path)
    assert any(v["shortfall"] > 0 for v in meta["strata"].values())
    for st, inf in meta["strata"].items():
        assert (key.stratum == st).sum() == min(inf["target"], inf["N"])


def test_slug_keyword_and_language_parse():
    assert S.has_price_keyword("https://x.example/news/onion-prices-surge-123", S.DEFAULT_KEYWORDS)
    assert not S.has_price_keyword("https://x.example/news/cricket-win-123", S.DEFAULT_KEYWORDS)
    assert S.has_price_keyword("https://x.example/%E0%A4%AE%E0%A4%B9%E0%A4%82%E0%A4%97%E0%A4%BE%E0%A4%88-%E0%A4%AC%E0%A4%A2%E0%A4%BC%E0%A5%80", S.DEFAULT_KEYWORDS)
    assert S.parse_language("srclc:hin; eng:Moses 2.1.1") == "hin"
    assert S.parse_language("") == "en" and S.parse_language(None) == "en"


# ------------------------------------------------------------------ fetch_texts
class FakeResp:
    def __init__(self, status=200, text="", ctype="text/html", js=None):
        self.status_code, self.text, self.headers, self._js = status, text, {"Content-Type": ctype}, js
        self.encoding, self.apparent_encoding = "utf-8", "utf-8"

    def json(self):
        return self._js


class FakeSession:
    def __init__(self, resp):
        self.resp = resp

    def get(self, *a, **k):
        return self.resp


def test_wayback_snapshot_rewrites_to_raw():
    js = {"archived_snapshots": {"closest": {"available": True, "url": "http://web.archive.org/web/20200101000000/http://x.example/a"}}}
    st, su, err = F.wayback_snapshot(FakeSession(FakeResp(js=js)), "http://x.example/a", "20200101123000", "ua", 5)
    assert err == "" and "/web/20200101000000id_/" in su and su.startswith("https://")
    st, su, err = F.wayback_snapshot(FakeSession(FakeResp(js={"archived_snapshots": {}})), "u", "20200101", "ua", 5)
    assert err == "no_snapshot"


def test_get_and_extract_flags_short_and_http_errors():
    long_html = "<html><body><article>" + "<p>" + ("Synthetic sentence about nothing in particular. " * 30) + "</p></article></body></html>"
    st, text, err = F.get_and_extract(FakeSession(FakeResp(text=long_html)), "https://x.example/a", "ua", 5)
    assert st == 200 and err == "" and len(text) >= F.MIN_CHARS
    st, text, err = F.get_and_extract(FakeSession(FakeResp(text="<html><body><p>Please subscribe</p></body></html>")), "https://x.example/a", "ua", 5)
    assert err.startswith("extracted_too_short")
    st, text, err = F.get_and_extract(FakeSession(FakeResp(status=403)), "https://x.example/a", "ua", 5)
    assert err == "http_403"


def test_ngrams_stub_raises():
    with pytest.raises(NotImplementedError):
        F.fetch_ngrams_text("https://x.example/a", "20210101000000")


def test_fetch_main_logs_every_attempt_and_respects_ceiling(tmp_path, monkeypatch):
    man = pd.DataFrame({"audit_id": ["A0001", "A0002", "A0003", "A0004"], "url": [f"https://s{i}.example/a" for i in range(4)],
                        "language": "en", "gkg_date": ["20160101000000", "20210101000000", "20220101000000", "20230101000000"],
                        "fetch_rank": [1, 2, 3, 4], "human_selected": False})
    mp = tmp_path / "man.csv"
    man.to_csv(mp, index=False)
    body = "Synthetic body text. " * 40

    def fake_get(session, url, ua, timeout, orig_url=None):
        if "s0" in url:
            return 200, body, ""            # live success
        if "s1" in url:
            return 404, "", "http_404"      # live fail
        if "snap" in url:
            return 200, body, ""            # wayback snapshot ok
        return 403, "", "http_403"

    def fake_wb(session, url, gdate, ua, timeout, max_days=30.0):
        return (200, "https://snap.example/x", "") if "s1" in url else (200, "", "no_snapshot")

    monkeypatch.setattr(F, "get_and_extract", fake_get)
    monkeypatch.setattr(F, "wayback_snapshot", fake_wb)
    monkeypatch.setattr(F, "robots_allows", lambda *a, **k: (True, ""))
    args = ["--manifest", str(mp), "--out-dir", str(tmp_path / "txt"), "--log", str(tmp_path / "log.csv"),
            "--per-host-delay", "0", "--global-delay", "0", "--ngrams-fallback"]
    F.main(args + ["--max-success", "400"])
    lg = pd.read_csv(tmp_path / "log.csv", dtype=str)
    assert list(lg.columns)[:7] == ["audit_id", "url", "mode", "http_status", "success", "chars", "error"]
    # A0001 live ok; A0002 live fail then wayback ok; A0003/A0004 live fail, wayback none, ngrams stub fail
    assert (lg[lg.audit_id == "A0001"]["mode"].tolist()) == ["live"]
    assert lg[(lg.audit_id == "A0002") & (lg["mode"] == "wayback")]["success"].iloc[0] == "True"
    assert "ngrams_not_implemented" in lg[lg.audit_id == "A0004"]["error"].tolist()
    assert not (tmp_path / "txt" / "A0003.txt").exists() and (tmp_path / "txt" / "A0002.txt").exists()
    n_rows = len(lg)
    F.main(args + ["--max-success", "400"])  # resume: successes skipped, failures retried once more
    assert len(pd.read_csv(tmp_path / "log.csv")) > n_rows
    # ceiling: with max-success 1 and one success logged already, nothing new is fetched
    lg_path = tmp_path / "log2.csv"
    args2 = ["--manifest", str(mp), "--out-dir", str(tmp_path / "txt2"), "--log", str(lg_path), "--per-host-delay", "0", "--global-delay", "0"]
    F.main(args2 + ["--max-success", "1"])
    assert pd.read_csv(lg_path, dtype=str).query("success == 'True'")["audit_id"].nunique() == 1


# ------------------------------------------------------------------ llm_code
def test_llm_code_stops_without_key(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit) as e:
        L.main(["--out-dir", str(tmp_path)])
    assert e.value.code == 2
    assert "not set" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_parse_reply_validates_and_never_repairs():
    ok = L.parse_reply('{"relevance":"Y","direction":"rising","cause_primary":"exchange_rate","cause_secondary":"","uncertain":0,"rationale":"x"}')
    assert ok["relevance"] == "Y" and ok["cause_primary"] == "exchange_rate" and ok["parse_error"] == ""
    bad = L.parse_reply('{"relevance":"Y","direction":"up","cause_primary":"oil","cause_secondary":"","uncertain":0}')
    assert bad["direction"] is None and bad["cause_primary"] is None and "direction_missing_or_invalid" in bad["parse_error"]
    assert L.parse_reply("no json here")["parse_error"] == "no_json"
    n = L.parse_reply('{"relevance":"N","direction":"","cause_primary":"","cause_secondary":"","uncertain":0}')
    assert n["relevance"] == "N" and n["parse_error"] == ""


def test_run_coder_with_synthetic_replies_and_resume(tmp_path):
    (tmp_path / "t").mkdir()
    for i in (1, 2):
        (tmp_path / "t" / f"A000{i}.txt").write_text("synthetic text", encoding="utf-8")
    man = pd.DataFrame({"audit_id": ["A0001", "A0002", "A0003"], "url": "u", "language": "en"})  # A0003 has no text
    seen = []

    def fake_call(client, model, system, user, max_tokens, retries=3):
        seen.append(user)
        return ('{"relevance":"N","direction":"","cause_primary":"","cause_secondary":"","uncertain":0,"rationale":"synthetic"}', "")

    out = tmp_path / "o.csv"
    n = L.run_coder(None, "A", "model-x", man, tmp_path / "t", "CODEBOOK", out, 12000, 400, call=fake_call)
    assert n == 2
    assert all("stratum" not in u.lower() and "flag" not in u.lower() for u in seen)
    assert L.run_coder(None, "A", "model-x", man, tmp_path / "t", "CODEBOOK", out, 12000, 400, call=fake_call) == 0
    assert pd.read_csv(out)["audit_id"].tolist() == ["A0001", "A0002"]


# ------------------------------------------------------------------ audit_metrics (synthetic toy)
SPEC = {  # stratum: (rows, weight each, language, n relevant, baseline flag)
    "flagged": (20, 10.0, "en", 14, 1), "econ_unflagged": (20, 10.0, "en", 6, 0),
    "nonecon_slug": (10, 10.0, "en", 2, 0), "nonecon_noslug": (10, 10.0, "en", 0, 0),
    "hin_flagged": (10, 5.0, "hin", 6, 1), "hin_econ_unflagged": (10, 5.0, "hin", 2, 0),
    "oth_flagged": (10, 5.0, "mar", 6, 1), "oth_econ_unflagged": (10, 5.0, "mar", 2, 0),
}
DIRS = ["rising", "falling", "stable", "mixed"]


def toy():
    krows, mrows, codes, i = [], [], [], 0
    for st, (n, w, lang, nrel, bflag) in SPEC.items():
        for j in range(n):
            i += 1
            aid = f"T{i:04d}"
            rel = "Y" if j < nrel else "N"
            cp = C.CAUSES[j % len(C.CAUSES)] if rel == "Y" else ""
            intl = int(cp in C.INTERNATIONAL_CAUSES)
            flagintl = intl if bflag else 0
            krows.append({"audit_id": aid, "stratum": st, "sampling_weight": w, "window_day": f"2020010{j % 5 + 1}",
                          "gdelt_flags": f"flag_baseline={bflag};flag_econ={int(not st.startswith('nonecon'))};flag_international={flagintl};flag_strict={int(bflag and rel == 'Y' and j < 7)}"})
            mrows.append({"audit_id": aid, "url": f"https://synthetic.example/{aid}", "language": lang})
            codes.append({"audit_id": aid, "relevance": rel, "direction": DIRS[j % 4] if rel == "Y" else "",
                          "cause_primary": cp, "cause_secondary": ""})
    return pd.DataFrame(krows), pd.DataFrame(mrows), pd.DataFrame(codes)


def run_metrics(key, man, human, a, b=None, log=None, mode="A"):
    return M.run(key, man, human, a, b if b is not None else a.copy(), log, mode=mode, B=150, variants=["flag_strict"])


def test_metrics_point_estimates_match_hand_calculation():
    key, man, a = toy()
    rep, prf, kap, cov = run_metrics(key, man, a.copy(), a)
    g = rep["gates"]["D15_precision_recall"]
    # gating frame, flagged = baseline: TP = 140+30+30 = 200 of weights 300 -> P = 2/3; relevant total 300 -> R = 2/3
    assert g["precision"] == pytest.approx(2 / 3) and g["gating_recall"] == pytest.approx(200 / 300)
    assert g["status"] == "PASS" and g["truth_source"] == "A"
    row = prf[(prf.truth_source == "A") & (prf.variant == "flag_baseline") & (prf.frame == "econ") & (prf.group == "en") & (prf.metric == "recall")].iloc[0]
    assert row.estimate == pytest.approx(140 / 200)
    d29 = rep["gates"]["D29_vernacular_recall"]
    assert d29["vernacular_recall_econ"] == pytest.approx(60 / 80) and d29["status"] == "PASS"
    assert d29["difference"] == pytest.approx(0.75 - 0.7)
    u = g["unscreened_nonecon"]
    assert u["relevant"] == 0 and u["n"] == 10 and u["exact_ci"][1] == pytest.approx(1 - 0.025 ** 0.1, abs=1e-6)
    # floor: TP 200 / (300 + 100 * upper)
    assert u["recall_floor_incl_unscreened_upper"] == pytest.approx(200 / (300 + 100 * u["exact_ci"][1]), rel=1e-6)
    assert rep["gates"]["D15_relevance_kappa"]["status"] == "PASS"
    assert rep["gates"]["D15_cause_kappa"]["status"] == "PASS"


def test_precision_recall_gate_fails_and_names_best_f2():
    key, man, a = toy()
    a2 = a.copy()
    fl = key[key.stratum.isin(["flagged", "hin_flagged", "oth_flagged"])]
    keep_y = fl.groupby("stratum").head(5)["audit_id"]  # only 5 relevant per flagged stratum (synthetic) -> precision ~0.33
    drop = fl.loc[~fl.audit_id.isin(keep_y), "audit_id"]
    a2.loc[a2.audit_id.isin(drop), ["relevance", "direction", "cause_primary"]] = ["N", "", ""]
    rep, *_ = run_metrics(key, man, a2.copy(), a2)
    g = rep["gates"]["D15_precision_recall"]
    assert g["status"] == "FAIL" and g["action"].startswith("switch to best-F2 variant")
    assert set(g["f2_by_variant"]) == {"flag_baseline", "flag_strict"}


def test_no_human_codes_means_not_evaluable_not_assumed():
    key, man, a = toy()
    rep, prf, kap, cov = run_metrics(key, man, None, a)
    gates = rep["gates"]
    assert gates["D15_relevance_kappa"]["status"] == "NOT_EVALUABLE"
    assert gates["D15_precision_recall"]["status"] == "NOT_EVALUABLE"
    assert gates["D25_international_kappa"]["status"] == "NOT_EVALUABLE"
    assert gates["D29_vernacular_recall"]["status"] == "NOT_EVALUABLE"
    assert gates["D15_direction_kappa"]["status"] == "NOT_EVALUABLE"


def test_low_relevance_kappa_switches_to_human_codes():
    key, man, a = toy()
    h = a.copy()
    flip = h.index[::2]  # disagree on half the articles
    h.loc[flip, "relevance"] = h.loc[flip, "relevance"].map({"Y": "N", "N": "Y"})
    h.loc[h.relevance == "N", ["direction", "cause_primary"]] = ""
    h.loc[(h.relevance == "Y") & (h.direction == ""), ["direction", "cause_primary"]] = ["rising", "monetary_policy"]
    rep, *_ = run_metrics(key, man, h, a)
    r = rep["gates"]["D15_relevance_kappa"]
    assert r["kappa"] < 0.7 and r["truth_source"] == "H" and r["status"].startswith("FAIL")
    assert rep["gates"]["D15_precision_recall"]["truth_source"] == "H"


def test_missing_stratum_gives_na_not_a_guess():
    key, man, a = toy()
    oth = key.loc[key.stratum.str.startswith("oth_"), "audit_id"]
    a_missing = a[~a.audit_id.isin(oth)]
    rep, *_ = run_metrics(key, man, a.copy(), a_missing)
    # human codes still cover oth strata, but the LLM truth source lacks them -> precision (all) is NA, not computed from the rest
    g = rep["gates"]["D15_precision_recall"]
    assert g["truth_source"] == "A" and g["status"] == "NOT_EVALUABLE" and math.isnan(g["precision"])


def test_d25_gate_pass_and_fail():
    key, man, a = toy()
    rep, *_ = run_metrics(key, man, a.copy(), a)
    d = rep["gates"]["D25_international_kappa"]
    assert d["kappa_flag_vs_cause_binary"] == pytest.approx(1.0) and d["status"] == "PASS" and d["n_coded_international_by_cause"] > 0
    key2 = key.copy()
    key2["gdelt_flags"] = key2["gdelt_flags"].str.replace(r"flag_international=\d", "flag_international=0", regex=True)
    rep2, *_ = run_metrics(key2, man, a.copy(), a)
    d2 = rep2["gates"]["D25_international_kappa"]
    assert d2["status"] in ("FAIL", "NOT_EVALUABLE")  # flag constant 0: kappa 0 or undefined, never PASS
    assert d2["status"] != "PASS"


def test_d29_fails_when_gap_exceeds_015_and_mode_b_rule():
    key, man, a = toy()
    a2 = a.copy()
    vern_unfl = key.loc[key.stratum.isin(["hin_econ_unflagged", "oth_econ_unflagged"]), "audit_id"]
    # make every unflagged vernacular article relevant -> vernacular recall falls (synthetic)
    a2.loc[a2.audit_id.isin(vern_unfl), ["relevance", "direction", "cause_primary"]] = ["Y", "rising", "monetary_policy"]
    rep, *_ = run_metrics(key, man, a2.copy(), a2)
    d = rep["gates"]["D29_vernacular_recall"]
    assert abs(d["difference"]) > 0.15 and d["status"] == "FAIL"
    # Mode B: numeric-ID slugs for vernacular and no NGrams text -> FAIL by rule
    man_b = man.copy()
    vm = man_b.language.isin(["hin", "mar"])
    man_b.loc[vm, "url"] = "https://synthetic.example/123456"
    rep_b, *_ = run_metrics(key, man_b, a.copy(), a, mode="B")
    d_b = rep_b["gates"]["D29_vernacular_recall"]
    assert d_b["status"] == "FAIL" and "not estimable" in d_b["reading"]


def test_kappa_by_language_and_retrieval_mode_and_llm_llm():
    key, man, a = toy()
    log = pd.DataFrame({"audit_id": key.audit_id, "mode": np.where(np.arange(len(key)) % 2 == 0, "live", "wayback"), "success": "True"})
    b = a.copy()
    rep, prf, kap, cov = run_metrics(key, man, a.copy(), a, b, log)
    groups = set(kap.group)
    assert {"all", "language=en", "language=hin", "mode=live", "mode=wayback"} <= groups
    assert set(kap.pair) == {"H-A", "H-B", "A-B"}
    assert kap[(kap.pair == "A-B") & (kap.group == "all") & (kap.variable == "relevance")].kappa.iloc[0] == pytest.approx(1.0)
    assert (prf.group == "mode=live").any()


def test_slug_informative_heuristic():
    assert M.slug_informative("https://x.example/news/onion-prices-surge-again-today")
    assert not M.slug_informative("https://x.example/article/1234567")


def test_metrics_cli_writes_report_files(tmp_path):
    key, man, a = toy()
    key.assign(outlet="synthetic.example").to_csv(tmp_path / "key.csv", index=False)
    man.to_csv(tmp_path / "man.csv", index=False)
    a.to_csv(tmp_path / "a.csv", index=False)
    a.to_csv(tmp_path / "h.csv", index=False)
    assert M.main(["--key", str(tmp_path / "key.csv"), "--manifest", str(tmp_path / "man.csv"), "--human", str(tmp_path / "h.csv"),
                   "--llm-a", str(tmp_path / "a.csv"), "--llm-b", str(tmp_path / "a.csv"), "--log", str(tmp_path / "none.csv"),
                   "--bootstrap", "100", "--out-dir", str(tmp_path / "out")]) == 0
    rep = (tmp_path / "out" / "gate_report.md").read_text()
    assert "D15 precision" in rep and "D25" in rep and "D29" in rep
    assert json.loads((tmp_path / "out" / "gate_report.json").read_text())["gates"]["D29_vernacular_recall"]["status"] == "PASS"
