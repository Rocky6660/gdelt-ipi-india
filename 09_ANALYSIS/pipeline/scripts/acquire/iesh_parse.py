"""Parsing helpers for RBI IESH release pages (used by iesh.py).

Kept separate so the parsers can be unit-tested on saved HTML without network.

What is known about the release pages (checked by web search, Nov 2026):
  * Release pages live at https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=<n>
    e.g. id=24089 (September 2026 round, released 07 Oct 2026),
         id=24077 (July 2026 round, released 05 Aug 2026),
         id=19456 (May 2020 round, telephone interviews, May 5-17 2020, 18 cities, 5,761 households).
  * Opening paragraph pattern (verified for May 2020 and Sep 2026):
      "... results of the <Month YYYY> round of the Inflation Expectations Survey of Households (IESH)"
      "... conducted ... during <Month d-d, YYYY> in <NN> major cities ..."
      "The results are based on responses from <N> urban households."
  * Sep 2026 release: "median unless stated otherwise" footnote; Table 2 (groups and the
    19 cities, Mean and Median, Estimate and SE, for Current Perception, Three Months
    ahead and One Year ahead); Table 3 (last 7 rounds, same columns); Table 5(a)/(b)
    cross-tabulations of respondent counts by bins "<1" ... ">=16" plus "No idea".
  * Each release links an Excel time-series file (rbidocs.rbi.org.in/rdocs/content/docs/IESH*.xlsx)
    and a PDF (rbidocs.rbi.org.in/rdocs/Publications/PDFs/IESH*.PDF).
  * Response bins: "0-1 per cent" to "15-16 per cent" in 100 bp steps, ">=16 per cent",
    "No idea" (RBI Bulletin, July 2025, Ruhi, Sharma & Sankaran).
[UNVERIFIED] Exact HTML markup (rowspan/colspan, where table titles sit), and whether
older releases (2015-2019) use the same tables. The parser is therefore heuristic
and flags anything it cannot read instead of guessing.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Optional

from bs4 import BeautifulSoup

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
MON3 = {k[:3]: v for k, v in MONTHS.items()}
MONTH_RE = r"(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?"


def month_num(s: str) -> Optional[int]:
    s = s.lower().rstrip(".")
    return MONTHS.get(s) or MON3.get(s[:3])


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    return clean(soup.get_text(" "))


def is_iesh_page(text: str) -> bool:
    t = text.lower()
    return ("inflation expectations survey of households" in t
            or "households' inflation expectations survey" in t
            or "households’ inflation expectations survey" in t)


def parse_round(text: str) -> Optional[str]:
    """'results of the May 2020 round of the Inflation Expectations Survey' -> '2020-05'."""
    m = re.search(MONTH_RE + r"\s+(\d{4})\s+round", text, re.I)
    if not m:
        m = re.search(r"round\s+of\s+" + MONTH_RE + r"\s+(\d{4})", text, re.I)
    if m:
        mo = month_num(m.group(1))
        if mo:
            return f"{int(m.group(2)):04d}-{mo:02d}"
    return None


def _date(y: int, m: int, d: int) -> Optional[str]:
    try:
        return dt.date(y, m, d).isoformat()
    except ValueError:
        return None


def parse_fieldwork(text: str) -> tuple[Optional[str], Optional[str], str]:
    """Return (start, end, raw_snippet). Never fills a default: unknown -> (None, None, snippet).

    Handles (others are left for the manual template):
      'during May 5-17, 2020'                     -> 2020-05-05, 2020-05-17
      'during September 10-20, 2026'
      'during August 28 - September 6, 2025'     -> cross-month
      'during 1-10 March 2018' / 'March 1 to 10, 2018'
      'during December 28, 2025 - January 6, 2026' -> cross-year
    """
    # look only near the word conducted/during to avoid release dates
    m0 = re.search(r"(conducted|during|between|survey period)(.{0,160})", text, re.I)
    snippet = clean(m0.group(0)) if m0 else ""
    s = snippet
    dash = r"\s*(?:-|–|—|to|and)\s*"
    pats = [
        # Month d, YYYY - Month d, YYYY
        (MONTH_RE + r"\s+(\d{1,2}),?\s+(\d{4})" + dash + MONTH_RE + r"\s+(\d{1,2}),?\s+(\d{4})",
         lambda g: (_date(int(g[2]), month_num(g[0]), int(g[1])), _date(int(g[5]), month_num(g[3]), int(g[4])))),
        # Month d - Month d, YYYY
        (MONTH_RE + r"\s+(\d{1,2})" + dash + MONTH_RE + r"\s+(\d{1,2}),?\s+(\d{4})",
         lambda g: (_date(int(g[4]), month_num(g[0]), int(g[1])), _date(int(g[4]), month_num(g[2]), int(g[3])))),
        # Month d-d, YYYY
        (MONTH_RE + r"\s+(\d{1,2})" + dash + r"(\d{1,2}),?\s+(\d{4})",
         lambda g: (_date(int(g[3]), month_num(g[0]), int(g[1])), _date(int(g[3]), month_num(g[0]), int(g[2])))),
        # d - d Month YYYY
        (r"(\d{1,2})(?:st|nd|rd|th)?" + dash + r"(\d{1,2})(?:st|nd|rd|th)?\s+" + MONTH_RE + r",?\s+(\d{4})",
         lambda g: (_date(int(g[3]), month_num(g[2]), int(g[0])), _date(int(g[3]), month_num(g[2]), int(g[1])))),
        # d Month - d Month YYYY
        (r"(\d{1,2})(?:st|nd|rd|th)?\s+" + MONTH_RE + dash + r"(\d{1,2})(?:st|nd|rd|th)?\s+" + MONTH_RE + r",?\s+(\d{4})",
         lambda g: (_date(int(g[4]), month_num(g[1]), int(g[0])), _date(int(g[4]), month_num(g[3]), int(g[2])))),
    ]
    for pat, fn in pats:
        m = re.search(pat, s, re.I)
        if m:
            try:
                a, b = fn(m.groups())
            except (TypeError, ValueError):
                continue
            if a and b and a <= b:
                return a, b, snippet
            if a and b and a > b:  # cross-year without explicit year on start
                y = int(b[:4])
                a2 = _date(y - 1, int(a[5:7]), int(a[8:10]))
                return a2, b, snippet + " [start year inferred as previous year: CHECK]"
    return None, None, snippet


def parse_mode(text: str) -> str:
    t = text.lower()
    if "telephon" in t or "over phone" in t or "telephone" in t:
        return "telephone"
    if "face-to-face" in t or "face to face" in t or "personal interview" in t or "in-person" in t:
        return "in_person"
    if "online" in t and "survey was conducted" in t:
        return "online_or_mixed[CHECK]"
    return "not_stated"


def parse_n(text: str) -> tuple[Optional[int], str]:
    pats = [r"responses from\s+([\d,]+)\s+(?:urban\s+)?households",
            r"based on (?:the )?responses? (?:of|from)\s+([\d,]+)",
            r"([\d,]{4,})\s+(?:urban\s+)?households",
            r"([\d,]{4,})\s+respon(?:ses|dents)"]
    for p in pats:
        m = re.search(p, text, re.I)
        if m:
            return int(m.group(1).replace(",", "")), clean(m.group(0))
    return None, ""


def parse_cities(text: str) -> tuple[Optional[int], list[str]]:
    n = None
    m = re.search(r"(\d{1,2}|eighteen|nineteen|sixteen|eighteen)\s+(?:major\s+)?cities", text, re.I)
    words = {"sixteen": 16, "eighteen": 18, "nineteen": 19}
    if m:
        g = m.group(1).lower()
        n = int(g) if g.isdigit() else words.get(g)
    names: list[str] = []
    m2 = re.search(r"cities\s*(?:viz\.?|namely|:)?\s*\(([^)]{20,600})\)", text, re.I)
    if m2:
        names = [clean(x) for x in re.split(r",|\band\b", m2.group(1)) if clean(x)]
    return n, names


def parse_release_date(text: str) -> Optional[str]:
    m = re.search(r"Date\s*:\s*" + MONTH_RE + r"\s+(\d{1,2}),\s*(\d{4})", text, re.I)
    if m:
        return _date(int(m.group(3)), month_num(m.group(1)), int(m.group(2)))
    return None


def statistic_footnote(text: str) -> str:
    """Record how the release defines its headline statistic (D7: definition per round)."""
    out = []
    for p in [r"[^.]{0,120}median[^.]{0,120}unless[^.]{0,80}\.",
              r"[^.]{0,160}(?:mean|median)[^.]{0,40}(?:computed|calculated|estimated|defined)[^.]{0,160}\.",
              r"[^.]{0,120}mid-?points?[^.]{0,160}\."]:
        for m in re.finditer(p, text, re.I):
            out.append(clean(m.group(0)))
    return " | ".join(dict.fromkeys(out))[:1500]


# ----------------------------------------------------------------------------- tables

def table_grid(table) -> list[list[str]]:
    """Span-aware grid of cell strings for a bs4 <table>."""
    grid: list[list[Optional[str]]] = []
    pending: dict[tuple[int, int], str] = {}
    for r, tr in enumerate(table.find_all("tr")):
        row: list[Optional[str]] = []
        c = 0
        cells = tr.find_all(["td", "th"])
        ci = 0
        while ci < len(cells) or (r, c) in pending:
            if (r, c) in pending:
                row.append(pending.pop((r, c)))
                c += 1
                continue
            cell = cells[ci]
            ci += 1
            txt = clean(cell.get_text(" "))
            cs = int(cell.get("colspan", 1) or 1)
            rs = int(cell.get("rowspan", 1) or 1)
            for k in range(cs):
                row.append(txt)
                for dr in range(1, rs):
                    pending[(r + dr, c + k)] = txt
            c += cs
        grid.append(row)
    w = max((len(r) for r in grid), default=0)
    return [[(x or "") for x in r] + [""] * (w - len(r)) for r in grid]


NUM_RE = re.compile(r"^-?(?:\d+(?:\.\d+)?|\.\d+)$")


def to_num(s: str) -> Optional[float]:
    s = s.replace(",", "").replace("*", "").strip()
    return float(s) if NUM_RE.match(s) else None


def table_caption(table) -> str:
    """Text just before the table plus its first row: where RBI puts 'Table 2: ...'."""
    parts = []
    prev = table.find_previous(string=re.compile(r"Table\s*\d", re.I))
    if prev:
        parts.append(clean(prev))
    first = table.find("tr")
    if first:
        parts.append(clean(first.get_text(" "))[:300])
    return " || ".join(parts)


def split_header(grid: list[list[str]]) -> tuple[list[list[str]], list[list[str]]]:
    """Header rows = leading rows with no numeric cell outside the first column."""
    h = 0
    for row in grid:
        if any(to_num(x) is not None for x in row[1:]):
            break
        h += 1
    return grid[:h], grid[h:]


def column_labels(header: list[list[str]], width: int) -> list[str]:
    labs = []
    for c in range(width):
        parts = []
        for row in header:
            x = row[c] if c < len(row) else ""
            if x and (not parts or parts[-1] != x):
                parts.append(x)
        labs.append(" / ".join(parts))
    return labs


def classify_col(label: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    l = label.lower()
    measure = None
    if "current" in l or "perception" in l:
        measure = "perception"
    elif "three month" in l or "3 month" in l or "3-month" in l:
        measure = "exp_3m"
    elif "one year" in l or "1 year" in l or "1-year" in l:
        measure = "exp_1y"
    stat = "mean" if re.search(r"\bmean\b", l) else ("median" if "median" in l else None)
    kind = "se" if re.search(r"\bs\.?e\.?\b|standard error", l) else (
        "estimate" if ("estimate" in l or stat) else None)
    return measure, stat, kind


def parse_quant_table(table) -> list[dict]:
    """Table 2 / Table 3 style: rows = groups/cities/rounds; cols = measure x stat x (estimate, se).

    Returns long rows {row_label, section, measure, stat, kind, value, col_label}.
    Columns that cannot be classified are skipped and reported with kind=None by the caller.
    """
    grid = table_grid(table)
    header, body = split_header(grid)
    if not body:
        return []
    width = max(len(r) for r in grid)
    labs = column_labels(header, width)
    out = []
    section = ""
    for row in body:
        label = row[0]
        vals = [to_num(x) for x in row[1:]]
        if label and all(v is None for v in vals):
            section = label
            continue
        for c in range(1, width):
            v = to_num(row[c]) if c < len(row) else None
            if v is None:
                continue
            measure, stat, kind = classify_col(labs[c])
            out.append({"row_label": label, "section": section, "measure": measure,
                        "stat": stat, "kind": kind, "value": v, "col_label": labs[c]})
    return out


BIN_RE = re.compile(r"^(<\s*1|>=?\s*16|≥\s*16|\d{1,2}\s*-\s*\d{1,2}|no idea|total)$", re.I)


def bin_bounds(label: str) -> tuple[Optional[float], Optional[float]]:
    l = label.replace(" ", "").lower()
    if l.startswith("<"):
        return 0.0, float(re.findall(r"\d+", l)[0])
    if l.startswith(">") or l.startswith("≥"):
        return float(re.findall(r"\d+", l)[0]), None  # open top bin
    m = re.match(r"(\d+)-(\d+)", l)
    if m:
        return float(m.group(1)), float(m.group(2))
    if re.match(r"^\d+$", l):  # single-number bin labels, e.g. '1' meaning [1,2)
        return float(l), float(l) + 1
    return None, None


def parse_crosstab(table) -> Optional[dict]:
    """Table 5(a)/(b): rows = current-perception bins, cols = expectation bins + No idea + Total.

    Returns {'row_bins': [...], 'col_bins': [...], 'row_totals': {bin: n}, 'col_totals': {bin: n}}
    using the 'Total' row/column when present, else sums of the body.
    """
    grid = table_grid(table)
    header, body = split_header(grid)
    if not header or not body:
        return None
    hdr = header[-1]
    col_bins = [x for x in hdr[1:]]
    row_totals, col_totals = {}, {}
    tot_row = None
    sums = [0.0] * len(col_bins)
    for row in body:
        lab = row[0]
        nums = [to_num(x) for x in row[1:1 + len(col_bins)]]
        if lab.lower().startswith("total"):
            tot_row = nums
            continue
        if not BIN_RE.match(lab.strip()):
            continue
        if "total" in [c.lower() for c in col_bins]:
            k = [c.lower() for c in col_bins].index("total")
            row_totals[lab] = nums[k]
        else:
            row_totals[lab] = sum(v for v in nums if v is not None)
        for i, v in enumerate(nums):
            if v is not None:
                sums[i] += v
    src = tot_row if tot_row else sums
    for i, b in enumerate(col_bins):
        if i < len(src) and src[i] is not None:
            col_totals[b] = src[i]
    if not row_totals and not col_totals:
        return None
    return {"col_bins": col_bins, "row_totals": row_totals, "col_totals": col_totals}


def distribution_stats(counts: dict[str, float], top_mid: float = 16.5) -> dict:
    """Continuous variants for D7 from binned counts (No idea and Total excluded).

    * share_ge10: share of respondents with a numeric answer whose bin lower bound >= 10.
    * mean_midpoint: mean using bin midpoints; the open top bin (>=16) gets `top_mid`
      (an assumption declared in docs; reported with top_share so it can be varied).
    * median_interp: median by linear interpolation within the median bin.
    * median_bin: label of the bin containing the median (shows the 1 pp step of the
      binned median; D7 dispute).
    """
    items = []
    for lab, n in counts.items():
        if n is None:
            continue
        lo, hi = bin_bounds(lab)
        if lo is None:
            continue
        items.append((lo, hi, float(n), lab))
    items.sort(key=lambda x: x[0])
    tot = sum(n for *_, n, _ in items)
    if tot <= 0:
        return {}
    ge10 = sum(n for lo, hi, n, _ in items if lo >= 10) / tot
    mean = sum(((lo + hi) / 2 if hi is not None else top_mid) * n for lo, hi, n, _ in items) / tot
    top = sum(n for lo, hi, n, _ in items if hi is None) / tot
    cum, med, med_bin = 0.0, None, None
    for lo, hi, n, lab in items:
        if cum + n >= tot / 2:
            med_bin = lab
            if hi is not None and n > 0:
                med = lo + (tot / 2 - cum) / n * (hi - lo)
            else:
                med = lo
            break
        cum += n
    return {"n_numeric": tot, "share_ge10": ge10, "mean_midpoint": mean,
            "top_bin_share": top, "median_interp": med, "median_bin": med_bin}
