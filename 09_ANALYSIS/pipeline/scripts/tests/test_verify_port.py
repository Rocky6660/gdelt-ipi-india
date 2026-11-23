"""Verifier's tests ported into the project, adapted to the fixed behaviour, plus tests for the
fixes (B1, B2, S1, S2, S4, S8a-c, S9). ALL DATA IS SYNTHETIC (tests only)."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "audit"))

import audit_common as C  # noqa: E402
import audit_metrics as M  # noqa: E402
import fetch_texts as F  # noqa: E402
import llm_code as L  # noqa: E402
import sample_audit as S  # noqa: E402

ALL = ["flagged", "econ_unflagged", "nonecon_slug", "nonecon_noslug", "hin_flagged", "hin_econ_unflagged", "oth_flagged", "oth_econ_unflagged"]


def build(rows):
    """rows: (stratum, weight, lang, rel, flags_dict, year)"""
    k, m, c = [], [], []
    for i, (st, w, lang, rel, fl, yr) in enumerate(rows):
        aid = f"V{i:04d}"
        k.append({"audit_id": aid, "stratum": st, "sampling_weight": w, "window_day": f"{yr}0101",
                  "gdelt_flags": ";".join(f"{a}={b}" for a, b in fl.items())})
        m.append({"audit_id": aid, "url": f"https://syn.example/{aid}", "language": lang})
        c.append({"audit_id": aid, "relevance": rel, "direction": "rising" if rel == "Y" else "",
                  "cause_primary": "monetary_policy" if rel == "Y" else "", "cause_secondary": ""})
    return pd.DataFrame(k), pd.DataFrame(m), pd.DataFrame(c)


def filler():
    rows = []
    for st in ALL:
        if st in ("flagged", "econ_unflagged"):
            continue
        lang = "hin" if st.startswith("hin") else "mar" if st.startswith("oth") else "en"
        fl = 1 if st.endswith("flagged") and not st.endswith("unflagged") else 0
        rows += [(st, 1.0, lang, "N", {"flag_baseline": fl, "flag_econ": 1, "flag_international": 0}, 2022)] * 2
    return rows


def f_(b):
    return {"flag_baseline": b, "flag_econ": 1, "flag_international": 0}


def test_hand_ipw_unequal_weights():
    rows = [("flagged", 10, "en", "Y", f_(1), 2016), ("flagged", 10, "en", "N", f_(1), 2016),
            ("flagged", 5, "en", "Y", f_(1), 2022), ("flagged", 5, "en", "Y", f_(1), 2022),
            ("econ_unflagged", 30, "en", "Y", f_(0), 2016), ("econ_unflagged", 10, "en", "N", f_(0), 2022),
            ("econ_unflagged", 10, "en", "Y", f_(0), 2022)] + filler()
    k, m, c = build(rows)
    rep, prf, *_ = M.run(k, m, c.copy(), c, c.copy(), None, B=50)
    g = rep["gates"]["D15_precision_recall"]
    assert g["precision"] == pytest.approx(20 / 34)
    assert g["gating_recall"] == pytest.approx(20 / 60)
    P, R = 20 / 34, 20 / 60
    assert g["f2_by_variant"]["flag_baseline"] == pytest.approx(5 * P * R / (4 * P + R))


def test_b2_nonresponse_adjusted_within_stratum_by_period_cells():
    """Old (2015-18) articles uncoded because of link rot: period-cell post-stratification recovers 0.5."""
    rows = [("flagged", 10, "en", "Y", f_(1), 2022)] * 20
    rows += [("econ_unflagged", 20, "en", "Y", f_(0), 2016)] * 10
    rows += [("econ_unflagged", 10, "en", "N", f_(0), 2022)] * 10
    rows += filler()
    k, m, c = build(rows)
    full, *_ = M.run(k, m, c.copy(), c, c.copy(), None, B=30)
    assert full["gates"]["D15_precision_recall"]["gating_recall"] == pytest.approx(200 / 400)
    old_ids = k[(k.stratum == "econ_unflagged") & k.window_day.str.startswith("2016")].audit_id.iloc[:5]
    c2 = c[~c.audit_id.isin(old_ids)]
    part, prf, kap, cov = M.run(k, m, c2.copy(), c2, c2.copy(), None, B=30)
    assert part["gates"]["D15_precision_recall"]["gating_recall"] == pytest.approx(0.5)  # was 200/350 at stratum level
    assert part["assumption"].startswith("non-response is treated as missing at random within stratum x period")


def test_b2_coverage_reports_rates_per_cell_and_empty_cell_is_not_imputed():
    rows = [("flagged", 10, "en", "Y", f_(1), 2022)] * 10
    rows += [("econ_unflagged", 20, "en", "Y", f_(0), 2016)] * 4
    rows += [("econ_unflagged", 10, "en", "N", f_(0), 2022)] * 10
    rows += filler()
    k, m, c = build(rows)
    log = pd.DataFrame({"audit_id": k.audit_id, "mode": "live", "success": "True"})
    # no old econ_unflagged article coded -> that cell is empty
    old_ids = k[(k.stratum == "econ_unflagged") & k.window_day.str.startswith("2016")].audit_id
    c2 = c[~c.audit_id.isin(old_ids)]
    log2 = log[~log.audit_id.isin(old_ids)]
    rep, prf, kap, cov = M.run(k, m, c2.copy(), c2, c2.copy(), log2)
    row = cov[(cov.stratum == "econ_unflagged") & (cov.period == "old")].iloc[0]
    assert row.sampled == 4 and row.retrieved == 0 and row.retrieval_rate == 0
    assert cov[(cov.stratum == "econ_unflagged") & (cov.period == "late")].iloc[0].retrieval_rate == 1.0
    g = rep["gates"]["D15_precision_recall"]
    assert g["status"] == "NOT_EVALUABLE" and np.isnan(g["gating_recall"])  # no silent drop of the empty cell
    pr = prf[(prf.truth_source == "A") & (prf.frame == "gating") & (prf.group == "all") & (prf.metric == "recall")].iloc[0]
    assert "cells with no coded articles" in pr.missing_reason
    rep2, *_ = M.run(k, m, c2.copy(), c2, c2.copy(), log2, collapse_empty=True)
    assert rep2["gates"]["D15_precision_recall"]["status"] != "NOT_EVALUABLE"  # explicit opt-in pooling


def test_b1_best_f2_only_from_declared_d9_variants():
    def fl(b, sp):
        return {"flag_baseline": b, "flag_econ": 1, "flag_international": 0, "flag_sports": sp, "flag_strict": 0}
    rows = [("flagged", 1, "en", "Y", fl(1, 1), 2022)] * 5 + [("flagged", 1, "en", "N", fl(1, 0), 2022)] * 15
    rows += [("econ_unflagged", 1, "en", "Y", fl(0, 1), 2022)] * 20
    rows += [(st, 1.0, "hin" if st.startswith("hin") else "mar" if st.startswith("oth") else "en", "N", fl(0, 0), 2022) for st in ALL[2:] for _ in range(2)]
    k, m, c = build(rows)
    rep, *_ = M.run(k, m, c.copy(), c, c.copy(), None, B=30)  # no declared variants
    assert rep["variants"] == ["flag_baseline"] and "flag_sports" not in rep["gates"]["D15_precision_recall"]["f2_by_variant"]
    rep2, *_ = M.run(k, m, c.copy(), c, c.copy(), None, B=30, variants=["flag_strict"])
    assert rep2["variants"] == ["flag_baseline", "flag_strict"]
    for bad in ("flag_sports", "flag_elections", "flag_international", "flag_econ", "price_family", "flag_missing"):
        with pytest.raises(ValueError):
            M.run(k, m, c.copy(), c, c.copy(), None, B=30, variants=[bad])


def test_cli_has_variants_option_and_config(tmp_path):
    import inspect
    assert "--variants" in inspect.getsource(M.main) and "--config" in inspect.getsource(M.main)
    rows = [("flagged", 10, "en", "Y", f_(1), 2022)] * 4 + filler() + [("econ_unflagged", 10, "en", "N", f_(0), 2022)] * 4
    k, m, c = build(rows)
    k.to_csv(tmp_path / "k.csv", index=False); m.to_csv(tmp_path / "m.csv", index=False); c.to_csv(tmp_path / "c.csv", index=False)
    (tmp_path / "cfg.json").write_text(json.dumps({"d9_variants": ["flag_strict"]}))
    with pytest.raises(ValueError):  # flag_strict not in this key -> refused, not ignored
        M.main(["--key", str(tmp_path / "k.csv"), "--manifest", str(tmp_path / "m.csv"), "--human", str(tmp_path / "c.csv"),
                "--llm-a", str(tmp_path / "c.csv"), "--llm-b", str(tmp_path / "c.csv"), "--log", "none", "--config", str(tmp_path / "cfg.json"),
                "--bootstrap", "30", "--out-dir", str(tmp_path / "o")])


def test_human_truth_scope_is_english_hindi_only():
    """If human codes become the truth, estimates cover en+hin; Marathi strata are excluded, not imputed."""
    from test_audit import toy
    key, man, a = toy()
    h = a.copy()
    h.loc[h.index[::2], "relevance"] = h.loc[h.index[::2], "relevance"].map({"Y": "N", "N": "Y"})
    h.loc[h.relevance == "N", ["direction", "cause_primary"]] = ""
    h.loc[(h.relevance == "Y") & (h.direction == ""), ["direction", "cause_primary"]] = ["rising", "monetary_policy"]
    mar = man.loc[man.language == "mar", "audit_id"]
    h = h[~h.audit_id.isin(mar)]  # no human codes for Marathi
    rep, prf, *_ = M.run(key, man, h, a, a.copy(), None, B=60)
    g = rep["gates"]["D15_precision_recall"]
    assert g["truth_source"] == "H" and "en,hin" in g["scope"]
    assert g["status"] in ("PASS", "FAIL")  # evaluable on the human-covered scope, not NOT_EVALUABLE
    assert any("human codes" in n for n in rep["notes"])


def test_d25_excludes_flagged_irrelevant():
    def f(i):
        return {"flag_baseline": 1, "flag_econ": 1, "flag_international": i}
    rows = [("flagged", 1, "en", "Y", f(0), 2022)] * 10 + [("flagged", 1, "en", "N", f(1), 2022)] * 10
    rows += [(st, 1.0, "hin" if st.startswith("hin") else "mar" if st.startswith("oth") else "en", "N", f(0), 2022) for st in ALL[1:] for _ in range(2)]
    k, m, c = build(rows)
    rep, *_ = M.run(k, m, c.copy(), c, c.copy(), None, B=30)
    assert rep["gates"]["D25_international_kappa"]["n"] == 10


def test_slug_based_codes_reported_separately():
    from test_audit import toy
    key, man, a = toy()
    s = a.copy()
    rep, *_ = M.run(key, man, a.copy(), a, a.copy(), None, B=60, slug=s)
    sl = rep["slug_based"]
    assert "SLUG-BASED" in sl["label"] and sl["gating_precision"] == pytest.approx(rep["gates"]["D15_precision_recall"]["precision"])
    rep2, *_ = M.run(key, man, a.copy(), a, a.copy(), None, B=60)
    assert "slug_based" not in rep2


def test_clopper_pearson_vs_scipy():
    st = pytest.importorskip("scipy.stats")
    for k_, n_ in [(0, 100), (1, 100), (3, 100), (7, 150), (50, 100), (100, 100)]:
        lo, hi = C.clopper_pearson(k_, n_)
        elo = 0.0 if k_ == 0 else st.beta.ppf(0.025, k_, n_ - k_ + 1)
        ehi = 1.0 if k_ == n_ else st.beta.ppf(0.975, k_ + 1, n_ - k_)
        assert lo == pytest.approx(elo, abs=1e-6) and hi == pytest.approx(ehi, abs=1e-6)


def test_kappa_three_categories_by_hand():
    a = list("AAABBBCCCA"); b = list("AABBBBCCAA")
    pe = (4 * 4 + 3 * 4 + 3 * 2) / 100
    assert C.cohen_kappa(a, b) == pytest.approx((0.8 - pe) / (1 - pe))
    ia = np.array(["ABC".index(x) for x in a]); ib = np.array(["ABC".index(x) for x in b])
    assert M.kappa_np(ia, ib, 3) == pytest.approx((0.8 - pe) / (1 - pe))


def test_oversample_ratio_and_weights():
    rng = np.random.default_rng(0)
    pop = pd.DataFrame({"year": np.r_[np.full(4000, 2016), np.full(6000, 2023)]})
    smp, info = S.draw_stratum(pop, 300, 1.5, rng)
    p_old = smp.loc[smp.year == 2016, "inclusion_prob_within"].iloc[0]
    p_new = smp.loc[smp.year == 2023, "inclusion_prob_within"].iloc[0]
    assert p_old / p_new == pytest.approx(1.5, rel=0.01) and len(smp) == 300
    assert (1 / smp.inclusion_prob_within).groupby(smp.year).sum().to_dict() == pytest.approx({2016: 4000, 2023: 6000})


# ------------------------------------------------------------------ sampler: DOC, tranches, human languages
def pop_file(tmp_path, n=40000, seed=1):
    from test_audit import synthetic_population
    p = tmp_path / "pop.parquet"
    df = synthetic_population(n=n, seed=seed)
    df.to_parquet(p)
    return p, df


def sampler(p, tmp, *extra):
    args = ["--input", str(p), "--manifest-out", str(tmp / "man.csv"), "--key-out", str(tmp / "key.csv"),
            "--sheet-out", str(tmp / "sheet.csv"), "--meta-out", str(tmp / "meta.json"), *extra]
    assert S.main(args) == 0
    return (pd.read_csv(tmp / "man.csv"), pd.read_csv(tmp / "key.csv"), pd.read_csv(tmp / "sheet.csv", dtype=str), json.loads((tmp / "meta.json").read_text()))


def test_s1_doc_stratum_added_only_when_hits_given(tmp_path):
    p, df = pop_file(tmp_path)
    rng = np.random.default_rng(5)
    hits = df[(~df.flag_baseline) & rng.random(len(df)).__lt__(0.05)][["DocumentIdentifier"]]
    hp = tmp_path / "doc.csv"
    hits.to_csv(hp, index=False)
    man, key, sheet, meta = sampler(p, tmp_path, "--doc-hits", str(hp))
    d = key[key.stratum == "doc_unflagged"]
    assert len(d) == 60 and meta["doc_stratum"] is True
    assert d.sampling_weight.sum() == pytest.approx(meta["strata"]["doc_unflagged"]["N"])
    assert set(d.audit_id).isdisjoint(set(sheet.audit_id))  # no human allocation for the DOC stratum
    assert not (key.loc[key.stratum == "flagged", "econ_row"] == 0).any()
    _, key0, _, _ = sampler(p, tmp_path / ".", )  # without hits no doc stratum
    assert "doc_unflagged" not in set(key0.stratum)


def test_s2_two_tranches_disjoint_ids_and_combined_weights(tmp_path):
    p, df = pop_file(tmp_path)
    days = sorted(df.DATE.astype(str).str[:8].unique())
    early, late = set(days[: len(days) // 2]), set(days[len(days) // 2:])
    out = {}
    for tr, dset in (("A", early), ("B", late)):
        sub = df[df.DATE.astype(str).str[:8].isin(dset)]
        pp = tmp_path / f"pop{tr}.parquet"
        sub.to_parquet(pp)
        d = tmp_path / tr
        d.mkdir()
        out[tr] = sampler(pp, d, "--tranche", tr)
    ka, kb = out["A"][1], out["B"][1]
    assert set(ka.audit_id).isdisjoint(set(kb.audit_id)) and ka.audit_id.str.startswith("TA").all() and kb.audit_id.str.startswith("TB").all()
    both = pd.concat([ka, kb])
    assert both.groupby("stratum").size().to_dict() == {"flagged": 300, "econ_unflagged": 300, "nonecon_slug": 150, "nonecon_noslug": 100,
                                                      "hin_flagged": 100, "hin_econ_unflagged": 100, "oth_flagged": 100, "oth_econ_unflagged": 100}
    assert out["A"][3]["human_n"] + out["B"][3]["human_n"] == 150
    assert out["A"][3]["seed"] != out["B"][3]["seed"]
    for st in ("flagged", "hin_flagged"):  # tranche weights sum to each tranche's population
        for tr, (man, key, sheet, meta) in out.items():
            assert key.loc[key.stratum == st, "sampling_weight"].sum() == pytest.approx(meta["strata"][st]["N"])


def test_s4_human_languages_configurable_default_english_hindi(tmp_path):
    p, _ = pop_file(tmp_path)
    _, key, sheet, meta = sampler(p, tmp_path)
    assert set(sheet.language) == {"en", "hin"} and len(sheet) == 150 and meta["human_languages"] == ["en", "hin"]
    assert not key.loc[key.human_selected, "stratum"].isin(["oth_flagged", "oth_econ_unflagged"]).any()
    t2 = tmp_path / "with_mar"
    t2.mkdir()
    _, key2, sheet2, meta2 = sampler(p, t2, "--human-languages", "en,hin,mar")
    assert len(sheet2) == 150 and "mar" in set(sheet2.language) and (sheet2.language == "hin").sum() == 40


# ------------------------------------------------------------------ fetch: soft failures, robots
class R:
    def __init__(self, status=200, text="", url="", ctype="text/html"):
        self.status_code, self.text, self.url, self.headers = status, text, url, {"Content-Type": ctype}
        self.encoding = self.apparent_encoding = "utf-8"
        self.history = []


class Sess:
    def __init__(self, resp):
        self.resp = resp

    def get(self, *a, **k):
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp


LONG = "<html><body><article><p>" + ("Synthetic sentence about nothing in particular. " * 40) + "</p></article></body></html>"


def test_s8a_redirect_to_home_and_section_is_failure():
    orig = "https://x.example/news/economy/onion-prices-surge-123.html"
    for final in ("https://x.example/", "https://x.example/news/economy/"):
        st, text, err = F.get_and_extract(Sess(R(text=LONG, url=final)), orig, "ua", 5, orig_url=orig)
        assert err.startswith("redirect_to_home_or_section"), final
    st, text, err = F.get_and_extract(Sess(R(text=LONG, url="https://www.x.example/news/economy/onion-prices-surge-123.html")), orig, "ua", 5, orig_url=orig)
    assert err == ""  # same article path after a host redirect is fine


def test_s8a_boilerplate_and_short_text_are_failures():
    cookie = "<html><body><article><p>" + ("Please accept cookies and subscribe to continue reading this page. " * 12) + "</p></article></body></html>"
    st, text, err = F.get_and_extract(Sess(R(text=cookie, url="u")), "u", "ua", 5)
    assert err.startswith("boilerplate:") or err.startswith("extracted_too_short")
    st, text, err = F.get_and_extract(Sess(R(text="<html><body><p>short</p></body></html>", url="u")), "u", "ua", 5)
    assert err.startswith("extracted_too_short")


def test_s8a_wayback_distance_and_capture_status():
    def js(ts, status="200"):
        return {"archived_snapshots": {"closest": {"available": True, "status": status, "url": f"http://web.archive.org/web/{ts}/http://x.example/a"}}}

    class W:
        def __init__(self, j):
            self.status_code, self._j = 200, j
        def json(self):
            return self._j
    ok = F.wayback_snapshot(Sess(W(js("20200110000000"))), "http://x.example/a", "20200101000000", "ua", 5, 30)
    assert ok[2] == ""
    far = F.wayback_snapshot(Sess(W(js("20210101000000"))), "http://x.example/a", "20200101000000", "ua", 5, 30)
    assert far[2].startswith("snapshot_too_far")
    redir = F.wayback_snapshot(Sess(W(js("20200102000000", "302"))), "http://x.example/a", "20200101000000", "ua", 5, 30)
    assert redir[2].startswith("snapshot_capture_status_")


def test_s8b_robots_rfc9309():
    cache = {}
    ua = "ua"
    ok, why = F.robots_allows("https://a.example/x", ua, cache, Sess(R(status=404, text="")), 5)
    assert ok  # 4xx = no robots file = allow
    ok, why = F.robots_allows("https://b.example/x", ua, {}, Sess(R(status=503, text="")), 5)
    assert not ok and "disallow" in why  # 5xx = complete disallow
    import requests
    ok, why = F.robots_allows("https://c.example/x", ua, {}, Sess(requests.ConnectionError("down")), 5)
    assert not ok and "unreachable" in why
    ok, why = F.robots_allows("https://d.example/x", ua, {}, Sess(R(status=200, text="User-agent: *\nDisallow: /x")), 5)
    assert not ok and why == "robots_disallowed"


def test_max_success_defaults_to_no_cap(tmp_path, monkeypatch):
    man = pd.DataFrame({"audit_id": [f"A{i:04d}" for i in range(1, 6)], "url": [f"https://s{i}.example/a" for i in range(5)], "language": "en",
                        "gkg_date": "20160101000000", "fetch_rank": range(1, 6), "human_selected": False})
    man.to_csv(tmp_path / "m.csv", index=False)
    monkeypatch.setattr(F, "get_and_extract", lambda *a, **k: (200, "Synthetic body. " * 50, ""))
    monkeypatch.setattr(F, "robots_allows", lambda *a, **k: (True, ""))
    F.main(["--manifest", str(tmp_path / "m.csv"), "--out-dir", str(tmp_path / "t"), "--log", str(tmp_path / "l.csv"), "--per-host-delay", "0", "--global-delay", "0"])
    assert len(list((tmp_path / "t").glob("*.txt"))) == 5
    import inspect
    assert "default=None" in inspect.getsource(F.main).split("--max-success")[1][:120]


# ------------------------------------------------------------------ LLM harness: slug basis, codebook hash
def test_s8c_slug_basis_codes_only_unretrieved_and_records_hash(tmp_path):
    (tmp_path / "t").mkdir()
    (tmp_path / "t" / "A0001.txt").write_text("synthetic text")
    man = pd.DataFrame({"audit_id": ["A0001", "A0002"], "url": ["https://s.example/fuel-price-hike", "https://s.example/123"], "language": "en"})
    seen = []

    def fake(client, model, system, user, max_tokens, retries=3):
        seen.append(user)
        return ('{"relevance":"Y","direction":"rising","cause_primary":"other_none","cause_secondary":"","uncertain":1,"rationale":"synthetic slug"}', "")

    out = tmp_path / "slug.csv"
    n = L.run_coder(None, "A", "m", man, tmp_path / "t", "CODEBOOK-TEXT", out, 1000, 100, call=fake, basis="slug")
    df = pd.read_csv(out)
    assert n == 1 and df.audit_id.tolist() == ["A0002"] and df.coding_basis.iloc[0] == "slug"
    assert df.codebook_sha256.iloc[0] == __import__("hashlib").sha256(b"CODEBOOK-TEXT").hexdigest()
    assert "ONLY the URL" in seen[0] and "ARTICLE TEXT" not in seen[0]


# ------------------------------------------------------------------ codebook consistency (S9, S10)
def test_s9_codebook_has_single_home_for_fuel_excise():
    cb = (ROOT / "docs" / "coding" / "codebook.md").read_text()
    assert re.search(r"Any tax or duty is `fiscal_tax_administered`.*excise", cb, re.S)
    row = [l for l in cb.splitlines() if l.startswith("| `fuel_energy_domestic`")][0]
    assert "NOT involving a tax" in row and "or tax" not in row.lower().replace("not involving a tax or duty", "")
    assert "hoarding" in cb and "MSP" in cb and "import duty" in cb
    assert "FREEZE" in cb
