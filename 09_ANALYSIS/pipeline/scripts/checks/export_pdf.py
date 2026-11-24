"""Export 10_OUTPUTS/paper/paper_draft.md to HTML and PDF (headless Chrome). Minimal markdown subset: YAML title,
headings, paragraphs, bullet and numbered lists, pipe tables, images, **bold**, *italic*, `code`. No external packages.
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "10_OUTPUTS/paper/paper_draft.md"
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]


GREEK = {"\\Delta": "Δ", "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ",
         "\\varepsilon": "ε", "\\equiv": "≡", "\\ge": "≥", "\\,": " "}


def math(t: str) -> str:
    for a, b in GREEK.items():
        t = re.sub(re.escape(a) + r"(?![A-Za-z])", lambda m, b=b: b, t)
    t = re.sub(r"_\{([^}]*)\}", r"<sub>\1</sub>", t)
    t = re.sub(r"_([A-Za-z0-9])", r"<sub>\1</sub>", t)
    t = re.sub(r"\^\{([^}]*)\}", r"<sup>\1</sup>", t)
    t = re.sub(r"\^([A-Za-z0-9])", r"<sup>\1</sup>", t)
    return "<i>" + t.replace("'", "′") + "</i>"


def inline(t: str) -> str:
    t = html.escape(t, quote=False)
    t = re.sub(r"\$([^$]+)\$", lambda m: math(m.group(1)), t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", t)
    return t


def convert(md: str, base: Path) -> str:
    title = date = ""
    m = re.match(r"---\n(.*?)\n---\n", md, re.S)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if k.strip() == "title": title = v.strip().strip('"')
            if k.strip() == "date": date = v.strip().strip('"')
        md = md[m.end():]
    out, para, lst, tbl, toc = [], [], None, [], []

    def flush():
        nonlocal para, lst, tbl
        if para: out.append("<p>" + inline(" ".join(para)) + "</p>"); para = []
        if lst: out.append(f"<{lst[0]}>" + "".join(f"<li>{inline(i)}</li>" for i in lst[1]) + f"</{lst[0]}>"); lst = None
        if tbl:
            rows = [r for r in tbl if not re.match(r"^\|[\s\-|:]+\|$", r)]
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            h = "".join(f"<th>{inline(c)}</th>" for c in cells[0])
            b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in cells[1:])
            out.append(f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"); tbl = []

    for line in md.splitlines():
        s = line.rstrip()
        if not s.strip():
            flush(); continue
        if s.startswith("$$") and s.endswith("$$") and len(s) > 4:
            flush(); out.append("<p class='eq'>" + math(html.escape(s[2:-2], quote=False)) + "</p>"); continue
        if s.startswith("#"):
            flush(); n = len(s) - len(s.lstrip("#")); txt = s[n:].strip(); aid = f"s{len(toc)}"
            if n <= 3: toc.append((n, txt, aid))
            out.append(f"<h{n + 1} id='{aid}'>{inline(txt)}</h{n + 1}>"); continue
        im = re.match(r"!\[(.*?)\]\((.*?)\)", s.strip())
        if im:
            flush(); src = (base / im.group(2)).resolve().as_uri()
            out.append(f'<figure><img src="{src}"><figcaption>{inline(im.group(1))}</figcaption></figure>'); continue
        if s.startswith("|"):
            if para or lst: flush()
            tbl.append(s.strip()); continue
        lm = re.match(r"^(\s*)([*-]|\d+\.)\s+(.*)", s)
        if lm and not para:
            kind = "ol" if lm.group(2)[0].isdigit() else "ul"
            if lst is None: lst = (kind, [])
            lst[1].append(lm.group(3)); continue
        if lst is not None and s.startswith("  "):
            lst[1][-1] += " " + s.strip(); continue
        if tbl: flush()
        para.append(s.strip())
    flush()
    css = ("body{font-family:Georgia,serif;font-size:11pt;line-height:1.45;max-width:46em;margin:auto}"
           "h1{font-size:17pt;text-align:center}h2{font-size:13pt;margin-top:1.3em}h3{font-size:11.5pt}"
           ".date{text-align:center;color:#555}table{border-collapse:collapse;font-size:9.5pt;margin:0.8em 0}"
           "th,td{border-top:1px solid #999;border-bottom:1px solid #999;padding:3px 6px;text-align:left}"
           "figure{margin:1em 0;text-align:center}img{max-width:100%}figcaption{font-size:9.5pt;color:#333}"
           "code{font-size:9pt}@page{size:A4;margin:22mm}.eq{text-align:center;font-size:11.5pt}"
           ".toc{page-break-after:always}.toc p{margin:2px 0}.toc .l4{margin-left:1.5em;font-size:10pt}.toc .l3{font-weight:bold;margin-top:4px}.toc a{color:inherit;text-decoration:none}"
           "h2,h3,h4{page-break-after:avoid;break-after:avoid}table,figure{page-break-inside:avoid}"
           "p:has(+ table){break-after:avoid;page-break-after:avoid}")
    head = f"<h1>{inline(title)}</h1><p class='date'>{inline(date)}</p>" if title else ""
    if WITH_TOC and toc:
        items = "".join(f"<p class='l{n + 1}'><a href='#{a}'>{inline(t)}</a></p>" for n, t, a in toc if n >= 2)
        abstract_end = next((i for i, o in enumerate(out) if o.startswith("<h2") and "Abstract" not in o and i > 0), 0)
        out.insert(abstract_end, f"<div class='toc'><h2>Contents</h2>{items}</div>")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{css}</style></head><body>{head}{''.join(out)}</body></html>"


WITH_TOC = False


def main() -> int:
    global SRC, WITH_TOC
    if len(sys.argv) > 1:
        SRC = SRC.parent / sys.argv[1]; WITH_TOC = "--toc" in sys.argv  # e.g. archive/paper_full.md
    page = convert(SRC.read_text(encoding="utf-8"), SRC.parent)
    stem = "paper" if SRC.name == "paper_draft.md" else SRC.stem
    out_html = SRC.with_name(stem + ".html"); out_pdf = SRC.with_name(stem + ".pdf")
    out_html.write_text(page, encoding="utf-8")
    exe = next((c for c in CHROME if Path(c).exists()), None)
    if not exe:
        print("no Chrome/Edge found; HTML written only"); return 1
    subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out_pdf}",
                    out_html.as_uri()], check=True, capture_output=True, timeout=120)
    print(out_pdf, out_pdf.stat().st_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
