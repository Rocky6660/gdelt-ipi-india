#!/usr/bin/env python3
"""IESH (RBI Inflation Expectations Survey of Households): scrape releases (D3, D7).

What it does
  1. Discovery. Starts from scripts/acquire/iesh_release_urls.csv (seed release pages),
     follows every link to another PublicationsView.aspx?id=... page whose page text is an
     IESH release (releases link the previous round), and optionally scans an id range
     (--scan-ids START END) keeping only pages whose text names the IESH. Every page found
     is appended to the seed file, so later runs start from a longer list.
  2. Download. Saves each release page (HTML) and its Excel/PDF attachments untouched to
     data/raw/iesh/<page_id>/.
  3. Parse. Round, fieldwork dates (scraped; never defaulted), mode, cities, N, release
     date, the statistic definition footnote; Table 2 (national + city-wise mean/median
     with SE, perception / 3m / 1y), Table 3 (national, recent rounds), Table 5 cross-tabs
     (bin counts) -> continuous variants for D7.
  4. Merge manual input. Any CSV in data/raw/iesh/manual/ that follows the templates in
     scripts/acquire/templates/ is stacked in with source=manual.

Outputs
  data/raw/iesh_rounds.csv              round, fieldwork_start, fieldwork_end, mode, n (+ provenance)
  data/processed/iesh_city_round.csv    long: round, geography, measure, stat, estimate, se, ...
  data/processed/iesh_national_round.csv long national series (own release preferred over Table 3 of later releases)
  data/processed/iesh_distribution_round.csv  share >=10%, midpoint mean, interpolated median, median bin
  data/processed/iesh_definitions.csv   per-round statistic footnote, table titles, parse flags
  data/interim/iesh_tables/<page_id>/table_<k>.csv   every HTML table as a plain grid (for checking)

D7 notes recorded here (dispute accepted):
  * Bin step of the binned median: response bins are 1 percentage point wide
    ("0-1" ... "15-16", ">=16", "No idea"; RBI Bulletin July 2025). The published median is
    therefore an interpolated statistic on a 1 pp grid; the median bin is output per round.
  * Continuous variants (declare before Gate 2): share expecting >=10% (1-year), and the
    published distribution mean (Table 2/3 'Mean'); the midpoint mean from Table 5 is a check.
  [UNVERIFIED] Whether Table 5 exists in pre-2021 releases; whether the RBI mean is a
  midpoint mean, and what value the open top bin gets. Look for this in the footnotes
  (iesh_definitions.csv) and the PDF before Gate 2.

Fallback (if rbi.org.in blocks scripts or the parser fails):
  fill scripts/acquire/templates/iesh_rounds_manual_template.csv and
  iesh_city_round_manual_template.csv from the PDFs, save them as
  data/raw/iesh/manual/iesh_rounds_manual.csv and data/raw/iesh/manual/iesh_city_round_manual.csv,
  and re-run with --offline. See docs/README_acquisition.md.

Usage
  python scripts/acquire/iesh.py [--root PATH] [--scan-ids 14000 24200] [--offline] [--max-pages 200]
"""
from __future__ import annotations

import csv
import re
import sys
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

from bs4 import BeautifulSoup

from acq_common import (Project, banner, base_parser, fetch, log_download, make_session,
                        polite_sleep, read_csv_rows, write_csv_rows)
import iesh_parse as P

SOURCE = "iesh"
PUB_RE = re.compile(r"PublicationsView\.aspx\?id=(\d+)", re.I)
ATTACH_RE = re.compile(r"rbidocs\.rbi\.org\.in/rdocs/.+\.(xlsx?|pdf)$", re.I)

ROUNDS_FIELDS = ["round", "fieldwork_start", "fieldwork_end", "mode", "n", "n_cities", "cities",
                 "release_date", "page_id", "url", "fieldwork_snippet", "n_snippet", "source", "flags"]
LONG_FIELDS = ["round", "geography", "geo_type", "group_section", "measure", "stat", "estimate", "se",
               "page_id", "table", "source", "col_label"]
DIST_FIELDS = ["round", "horizon", "n_numeric", "share_ge10", "mean_midpoint", "top_bin_share",
               "median_interp", "median_bin", "bin_step_pp", "top_bin_midpoint_assumed", "page_id", "source"]
DEF_FIELDS = ["round", "page_id", "statistic_footnote", "table_captions", "n_tables", "flags"]

IESH_CITIES = ["Ahmedabad", "Bengaluru", "Bhopal", "Bhubaneswar", "Chandigarh", "Chennai", "Delhi",
               "Guwahati", "Hyderabad", "Jaipur", "Jammu", "Kolkata", "Lucknow", "Mumbai", "Nagpur",
               "Patna", "Raipur", "Ranchi", "Thiruvananthapuram"]
CITY_ALIASES = {"bangalore": "Bengaluru", "new delhi": "Delhi", "trivandrum": "Thiruvananthapuram",
                "calcutta": "Kolkata", "bombay": "Mumbai", "madras": "Chennai"}


def norm_city(label: str):
    l = label.strip().lower()
    if l in CITY_ALIASES:
        return CITY_ALIASES[l]
    for c in IESH_CITIES:
        if l == c.lower():
            return c
    return None


def page_id(url: str):
    m = PUB_RE.search(url)
    return m.group(1) if m else None


def canonical(pid: str) -> str:
    return f"https://www.rbi.org.in/Scripts/PublicationsView.aspx?id={pid}"


def discover_and_download(proj: Project, args) -> list[tuple[str, Path]]:
    seeds_path = proj.acquire / "iesh_release_urls.csv"
    seeds = read_csv_rows(seeds_path) if seeds_path.exists() else []
    known = {page_id(r["url"]) for r in seeds if page_id(r["url"])}
    queue = deque(sorted(known, key=int, reverse=True))
    if args.scan_ids:
        a, b = args.scan_ids
        queue.extend(str(i) for i in range(b, a - 1, -1) if str(i) not in known)
    session = make_session()
    seen, pages = set(), []
    while queue and len(pages) < args.max_pages:
        pid = queue.popleft()
        if pid in seen:
            continue
        seen.add(pid)
        url = canonical(pid)
        path = fetch(proj, session, SOURCE, url, dest_name="page.html", subdir=pid,
                     timeout=args.timeout, notes="IESH release page candidate")
        polite_sleep(args.sleep)
        if path is None:
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        text = P.page_text(html)
        if "what code is in the image" in text.lower() or "captcha" in text.lower():
            print(f"[WARN] id={pid}: captcha/WAF page received. Use the manual fallback.")
            log_download(proj, SOURCE, url, "captcha", path.stat().st_size, "", "WAF page")
            path.unlink()
            continue
        if not P.is_iesh_page(text):
            path.unlink()  # not an IESH page (from id scan); keep raw dir clean
            try:
                path.parent.rmdir()
            except OSError:
                pass
            continue
        pages.append((pid, path))
        if pid not in known:
            with open(seeds_path, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([url, P.parse_round(text) or "", "crawled by iesh.py", "auto"])
            known.add(pid)
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            nid = page_id(href)
            if nid and nid not in seen:
                queue.appendleft(nid)  # depth-first along 'previous round' links
            if ATTACH_RE.search(href):
                fname = Path(urlparse(href).path).name
                fetch(proj, session, SOURCE, href, dest_name=fname, subdir=pid,
                      timeout=args.timeout, notes=f"IESH attachment of id={pid}")
                polite_sleep(args.sleep)
        print(f"[ok] id={pid} round={P.parse_round(text)}")
    return pages


def parse_pages(proj: Project, pages: list[tuple[str, Path]]):
    rounds, long_rows, nat_rows, dist_rows, defs = [], [], [], [], []
    interim = proj.root / "data" / "interim" / "iesh_tables"
    for pid, path in pages:
        html = path.read_text(encoding="utf-8", errors="replace")
        text = P.page_text(html)
        rnd = P.parse_round(text)
        flags = []
        if not rnd:
            flags.append("round_not_parsed")
        fs, fe, snip = P.parse_fieldwork(text)
        if not fs:
            flags.append("fieldwork_not_parsed")
        n, nsnip = P.parse_n(text)
        if n is None:
            flags.append("n_not_parsed")
        ncity, cities = P.parse_cities(text)
        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")
        captions, city_names_from_table = [], []
        for k, t in enumerate(tables):
            grid = P.table_grid(t)
            if len(grid) < 2 or max(len(r) for r in grid) < 2:
                continue
            write_csv_rows(interim / pid / f"table_{k}.csv",
                           ({f"c{i}": x for i, x in enumerate(r)} for r in grid),
                           [f"c{i}" for i in range(max(len(r) for r in grid))])
            cap = P.table_caption(t)
            captions.append(f"[{k}] {cap[:200]}")
            capl = cap.lower()
            if re.search(r"table\s*5|cross-?tab", capl):
                ct = P.parse_crosstab(t)
                if ct:
                    if re.search(r"table\s*5\s*\(?a\)?", capl):
                        horizon = "exp_3m"
                    elif re.search(r"table\s*5\s*\(?b\)?", capl):
                        horizon = "exp_1y"
                    elif re.search(r"three\s*months?|3\s*months?", capl):
                        horizon = "exp_3m"
                    elif re.search(r"one\s*year|1\s*year", capl):
                        horizon = "exp_1y"
                    else:
                        horizon = "unknown"
                    for hz, counts in (("perception", ct["row_totals"]), (horizon, ct["col_totals"])):
                        st = P.distribution_stats(counts)
                        if st:
                            dist_rows.append({"round": rnd, "horizon": hz, **st, "bin_step_pp": 1,
                                              "top_bin_midpoint_assumed": 16.5, "page_id": pid,
                                              "source": f"table{k}_crosstab"})
                continue
            q = P.parse_quant_table(t)
            if not q:
                continue
            is_t3 = bool(re.search(r"table\s*3", capl)) or sum(
                bool(re.match(r"^[A-Za-z]{3}-\d{2}$", r["row_label"])) for r in q) > len(q) / 2
            for r in q:
                if r["measure"] is None or r["stat"] is None or r["kind"] is None:
                    continue
                lab = r["row_label"]
                if is_t3:
                    m = re.match(r"^([A-Za-z]{3,4})-(\d{2})$", lab)
                    if not m or not P.month_num(m.group(1)):
                        continue
                    rr = f"20{m.group(2)}-{P.month_num(m.group(1)):02d}"
                    nat_rows.append({"round": rr, "geography": "India", "geo_type": "national",
                                     "group_section": "", "measure": r["measure"], "stat": r["stat"],
                                     r["kind"]: r["value"], "page_id": pid, "table": f"table{k}(T3)",
                                     "source": "own_release" if rr == rnd else "later_release_T3",
                                     "col_label": r["col_label"]})
                else:
                    city = norm_city(lab)
                    if city:
                        city_names_from_table.append(city)
                        geo, gt = city, "city"
                    elif lab.lower().startswith(("overall", "all", "total")):
                        geo, gt = "India", "national"
                    else:
                        geo, gt = lab, "group"
                    long_rows.append({"round": rnd, "geography": geo, "geo_type": gt,
                                      "group_section": r["section"], "measure": r["measure"],
                                      "stat": r["stat"], r["kind"]: r["value"], "page_id": pid,
                                      "table": f"table{k}", "source": "scrape", "col_label": r["col_label"]})
        if not long_rows or all(x["page_id"] != pid for x in long_rows):
            flags.append("no_quant_table_parsed")
        city_list = cities or sorted(set(city_names_from_table))
        rounds.append({"round": rnd, "fieldwork_start": fs, "fieldwork_end": fe, "mode": P.parse_mode(text),
                       "n": n, "n_cities": ncity or (len(city_list) or None), "cities": ";".join(city_list),
                       "release_date": P.parse_release_date(text), "page_id": pid, "url": canonical(pid),
                       "fieldwork_snippet": snip[:300], "n_snippet": nsnip, "source": "scrape",
                       "flags": ";".join(flags)})
        defs.append({"round": rnd, "page_id": pid, "statistic_footnote": P.statistic_footnote(text),
                     "table_captions": " || ".join(captions)[:3000], "n_tables": len(tables),
                     "flags": ";".join(flags)})
    return rounds, collapse(long_rows), collapse(nat_rows), dist_rows, defs


def collapse(rows: list[dict]) -> list[dict]:
    """Join estimate and se, which arrive as separate long rows, onto one row."""
    out: dict[tuple, dict] = {}
    for r in rows:
        key = (r["round"], r["geography"], r.get("group_section", ""), r["measure"], r["stat"],
               r["page_id"], r["table"])
        d = out.setdefault(key, {k: r.get(k) for k in LONG_FIELDS if k not in ("estimate", "se")})
        for k in ("estimate", "se"):
            if r.get(k) is not None:
                d[k] = r[k]
    return list(out.values())


def merge_manual(proj: Project, rounds, long_rows):
    mdir = proj.raw_dir(SOURCE) / "manual"
    mdir.mkdir(exist_ok=True)
    mr = mdir / "iesh_rounds_manual.csv"
    ml = mdir / "iesh_city_round_manual.csv"
    if mr.exists():
        scraped = {r["round"]: r for r in rounds if r["round"]}
        for r in read_csv_rows(mr):
            if not r.get("round"):
                continue
            r["source"] = "manual"
            if r["round"] in scraped:
                # fill only the gaps of the scrape; disagreements are flagged, not overwritten
                s = scraped[r["round"]]
                for k in ("fieldwork_start", "fieldwork_end", "mode", "n", "n_cities", "cities"):
                    if r.get(k) and not s.get(k):
                        s[k] = r[k]
                        s["flags"] = (s.get("flags") or "") + f";{k}_from_manual"
                    elif r.get(k) and s.get(k) and str(r[k]) != str(s[k]) and s.get(k) != "not_stated":
                        s["flags"] = (s.get("flags") or "") + f";{k}_manual_disagrees({r[k]})"
                    elif r.get(k) and s.get(k) == "not_stated":
                        s[k] = r[k]
            else:
                rounds.append(r)
        print(f"[manual] merged {mr}")
    if ml.exists():
        have = {(x["round"], x["geography"], x["measure"], x["stat"]) for x in long_rows}
        for r in read_csv_rows(ml):
            key = (r.get("round"), r.get("geography"), r.get("measure"), r.get("stat"))
            if key not in have:
                r["source"] = "manual"
                long_rows.append(r)
        print(f"[manual] merged {ml}")
    return rounds, long_rows


def merge_manual_distribution(proj: Project, dist_rows):
    md = proj.raw_dir(SOURCE) / "manual" / "iesh_distribution_manual.csv"
    if not md.exists():
        return dist_rows
    have = {(r["round"], r["horizon"]) for r in dist_rows}
    groups: dict[tuple, dict] = {}
    for r in read_csv_rows(md):
        if not r.get("round") or r["round"].startswith("EXAMPLE"):
            continue
        try:
            groups.setdefault((r["round"], r["horizon"]), {})[r["bin"]] = float(r["count"])
        except (KeyError, ValueError):
            continue
    for (rnd, hz), counts in groups.items():
        if (rnd, hz) in have:
            continue
        st = P.distribution_stats(counts)
        if st:
            dist_rows.append({"round": rnd, "horizon": hz, **st, "bin_step_pp": 1,
                              "top_bin_midpoint_assumed": 16.5, "page_id": "", "source": "manual"})
    print(f"[manual] merged {md}")
    return dist_rows


def main():
    p = base_parser(__doc__)
    p.add_argument("--scan-ids", nargs=2, type=int, metavar=("START", "END"),
                   help="also scan PublicationsView ids in [START, END] (slow; polite)")
    p.add_argument("--max-pages", type=int, default=400)
    p.add_argument("--offline", action="store_true",
                   help="no network: parse pages already in data/raw/iesh/ plus manual files")
    args = p.parse_args()
    proj = Project(args.root)
    banner("IESH releases")
    if args.offline:
        pages = [(d.name, d / "page.html") for d in sorted(proj.raw_dir(SOURCE).iterdir())
                 if d.is_dir() and (d / "page.html").exists()]
    else:
        pages = discover_and_download(proj, args)
    print(f"{len(pages)} IESH release pages available")
    rounds, long_rows, nat_rows, dist_rows, defs = parse_pages(proj, pages)
    rounds, long_rows = merge_manual(proj, rounds, long_rows)
    dist_rows = merge_manual_distribution(proj, dist_rows)
    rounds = [r for r in rounds if not str(r.get("round", "")).startswith("EXAMPLE")]
    long_rows = [r for r in long_rows if not str(r.get("round", "")).startswith("EXAMPLE")]

    # national series: own release first, then Table 3 of later releases for rounds with no page
    nat_own = [r for r in long_rows if r["geo_type"] == "national"]
    have = {(r["round"], r["measure"], r["stat"]) for r in nat_own}
    nat_all = nat_own + [r for r in nat_rows if (r["round"], r["measure"], r["stat"]) not in have
                         and r["source"] == "later_release_T3"]
    rounds.sort(key=lambda r: r.get("round") or "")
    n1 = write_csv_rows(proj.raw / "iesh_rounds.csv", rounds, ROUNDS_FIELDS)
    n2 = write_csv_rows(proj.processed / "iesh_city_round.csv",
                        sorted(long_rows, key=lambda r: (r.get("round") or "", r["geography"])), LONG_FIELDS)
    n3 = write_csv_rows(proj.processed / "iesh_national_round.csv",
                        sorted(nat_all, key=lambda r: r.get("round") or ""), LONG_FIELDS)
    n4 = write_csv_rows(proj.processed / "iesh_distribution_round.csv", dist_rows, DIST_FIELDS)
    n5 = write_csv_rows(proj.processed / "iesh_definitions.csv", defs, DEF_FIELDS)
    print(f"rounds={n1} city/group rows={n2} national rows={n3} distribution rows={n4} definitions={n5}")
    missing = [r["round"] or r["page_id"] for r in rounds if not r.get("fieldwork_start")]
    if missing:
        print("[ACTION] fieldwork dates missing for:", ", ".join(map(str, missing)),
              "\n         Fill them in data/raw/iesh/manual/iesh_rounds_manual.csv from the PDFs "
              "(D3: rounds without dates are excluded, never imputed).")
    if n2 == 0:
        print("[ACTION] no city tables parsed. Use the manual template "
              "(scripts/acquire/templates/iesh_city_round_manual_template.csv).", file=sys.stderr)


if __name__ == "__main__":
    main()
