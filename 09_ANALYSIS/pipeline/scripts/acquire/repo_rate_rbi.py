"""Repo rate and MPC decision dates from RBI press releases (D7 policy controls; handoff step 3).

Source: rbi.org.in press-release archive (BS_PressReleaseDisplay.aspx, year postback).
For each year it lists all press releases, keeps those whose title is a monetary policy
statement / MPC resolution or an off-cycle policy repo rate action, downloads each release
(raw HTML kept under data/raw/policy/rbi_pr/, every fetch logged), and extracts the policy
repo rate from the release text with a regex. Nothing is typed in by hand: a release whose
text does not yield exactly one repo-rate value is listed in the problems file for review.

Outputs
  data/raw/policy/rbi_pr/list_<year>.csv            all release titles/prids for the year
  data/raw/policy/rbi_pr/pr_<prid>.html             raw release pages
  data/processed/repo_rate_rbi_extract.csv          one row per kept release: date, prid, title, repo, sentence
  data/raw/policy/repo_rate.csv                     date,repo (+ prid,source_url): decision dates, as read by phase1.py
  logs/repo_rate_problems.txt                       releases where extraction was ambiguous
"""
from __future__ import annotations

import csv
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acq_common import Project, base_parser, fetch, make_session, polite_sleep, log_download, now_iso  # noqa: E402

from bs4 import BeautifulSoup  # noqa: E402

BASE = "https://www.rbi.org.in/Scripts/"
LIST_URL = BASE + "BS_PressReleaseDisplay.aspx"

TITLE_KEEP = re.compile(
    r"(monetary policy statement|resolution of the monetary policy committee|"
    r"bi-monthly monetary policy|policy repo rate|statement by .{0,60}governor,? on monetary policy)", re.I)
TITLE_DROP = re.compile(r"(minutes of the monetary policy committee|governor'?s statement)", re.I)

# Sentences that state the decided repo rate, e.g.
#  "reduce the policy repo rate under the liquidity adjustment facility (LAF) by 25 basis points to 6.25 per cent"
#  "keep the policy repo rate under the LAF unchanged at 6.5 per cent"
#  "keep the policy repo rate under the liquidity adjustment facility (LAF) unchanged at 7.25 per cent"
RATE_RE = re.compile(
    r"policy repo rate(?:(?!\.\s)[^;]){0,220}?\b(?:unchanged at|to|at)\s+(\d{1,2}(?:\.\d{1,2})?)\s*(?:per\s*cent|%)",
    re.I | re.S)
DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                     r"\s+(\d{1,2}),\s+(\d{4})")


def list_year(sess, year: int, proj: Project, timeout: float) -> list[dict]:
    g = sess.get(LIST_URL, timeout=timeout)
    soup = BeautifulSoup(g.text, "lxml")
    form = {i["name"]: i.get("value", "") for i in soup.select("input[name]") if i.get("type") != "submit"}
    form.update(hdnYear=str(year), hdnMonth="0")
    r = sess.post(LIST_URL, data=form, timeout=timeout)
    log_download(proj, "policy", f"{LIST_URL}#year={year}", r.status_code, len(r.content), "",
                 "press-release year listing (POST)")
    r.raise_for_status()
    # The listing HTML is malformed (unclosed <b>), so scan tokens in document order:
    # date header cells (class="tableheader") followed by release links.
    tok = re.compile(r'class="tableheader"[^>]*>\s*<b>\s*([A-Z][a-z]{2} \d{1,2}, \d{4})'
                     r"|href=BS_PressReleaseDisplay\.aspx\?prid=(\d+)>(.*?)</a>", re.S)
    rows, cur_date = [], ""
    for m in tok.finditer(r.text):
        if m.group(1):
            cur_date = m.group(1)
        else:
            title = BeautifulSoup(m.group(3), "lxml").get_text(" ", strip=True)
            rows.append({"year": year, "list_date": cur_date, "prid": m.group(2), "title": title})
    out = proj.raw_dir("policy") / "rbi_pr"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"list_{year}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "list_date", "prid", "title"])
        w.writeheader(); w.writerows(rows)
    return rows


def parse_list_date(s: str) -> dt.date | None:
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    return None


def main() -> int:
    p = base_parser(__doc__.splitlines()[0])
    p.add_argument("--start-year", type=int, default=2015)
    p.add_argument("--end-year", type=int, default=dt.date.today().year)
    a = p.parse_args()
    proj = Project(a.root)
    sess = make_session()
    sess.headers["User-Agent"] = "Mozilla/5.0"

    kept = []
    for y in range(a.start_year, a.end_year + 1):
        rows = list_year(sess, y, proj, a.timeout)
        k = [r for r in rows if TITLE_KEEP.search(r["title"]) and not TITLE_DROP.search(r["title"])]
        print(f"{y}: {len(rows)} releases, {len(k)} kept")
        kept += k
        polite_sleep(a.sleep)

    ext, problems, notices = [], [], []
    for r in kept:
        url = f"{BASE}BS_PressReleaseDisplay.aspx?prid={r['prid']}"
        path = fetch(proj, sess, "policy", url, dest_name=f"pr_{r['prid']}.html", subdir="rbi_pr",
                     timeout=a.timeout, notes="MPC/policy release")
        polite_sleep(a.sleep)
        if path is None:
            problems.append(f"prid {r['prid']}: fetch failed | {r['title']}")
            continue
        soup = BeautifulSoup(path.read_bytes(), "lxml")
        body = soup.select_one("table.tablebg") or soup
        text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
        m_date = DATE_RE.search(text)
        rel_date = parse_list_date(r["list_date"]) or (
            dt.datetime.strptime(" ".join(m_date.groups()), "%B %d %Y").date() if m_date else None)
        rates = RATE_RE.findall(text)
        sents = [m.group(0) for m in RATE_RE.finditer(text)]
        vals = sorted({float(x) for x in rates})
        decision = bool(re.search(r"(MPC|Committee|Reserve Bank)[^.]{0,120}\bdecided\b|\bit has been decided\b|"
                                  r"\bhas decided to\b", text, re.I))
        if not vals:
            # No repo-rate sentence: a scheduling notice, a "Meeting of the MPC" notice or a LAF-window note.
            # Completeness is checked separately against the meeting calendar (see PROGRESS.md / validation).
            notices.append(f"prid {r['prid']} {rel_date}: no repo-rate sentence"
                           f"{' (has decision wording)' if decision else ''} | {r['title']}")
            continue
        # The decision is stated in the first repo-rate sentence of a release; later matches can be
        # market statistics ("... call rate eased ... to 7.11 per cent"). Multi-value releases are flagged.
        if len(vals) != 1:
            problems.append(f"prid {r['prid']} {rel_date}: {len(vals)} distinct values {vals}; using first "
                            f"sentence ({rates[0]}) | {r['title']}"
                            + "".join(f"\n    > {s[:220]}" for s in sents[:4]))
        ext.append({"date": rel_date.isoformat() if rel_date else "", "prid": r["prid"], "title": r["title"],
                    "repo": float(rates[0]), "n_values": len(vals),
                    "sentence": sents[0][:300] if sents else "", "source_url": url})

    ext.sort(key=lambda d: (d["date"], d["prid"]))
    with open(proj.processed / "repo_rate_rbi_extract.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ext[0].keys()) if ext else ["date"])
        w.writeheader(); w.writerows(ext)

    good = [e for e in ext if e["repo"] != "" and e["date"]]
    with open(proj.raw_dir("policy") / "repo_rate.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "repo", "prid", "source_url"])
        for e in good:
            w.writerow([e["date"], e["repo"], e["prid"], e["source_url"]])
    (proj.logs / "repo_rate_problems.txt").write_text(
        f"# {now_iso()}\n## problems\n" + ("\n".join(problems) if problems else "none")
        + "\n## skipped notices (no decision text, no repo value)\n" + "\n".join(notices) + "\n", encoding="utf-8")
    print(f"kept {len(kept)}, notices skipped {len(notices)}, extracted {len(good)}, problems {len(problems)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
