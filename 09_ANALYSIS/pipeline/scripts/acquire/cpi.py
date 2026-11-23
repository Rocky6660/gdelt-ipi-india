#!/usr/bin/env python3
"""MoSPI CPI (base 2012) through Dec 2025: all-India, groups/subgroups, items, state-wise (D7, D26).

Source: the MoSPI open API, https://api.mospi.gov.in (the eSankhyiki back end).
Verified from the swagger spec in MoSPI's own MCP server repo
(github.com/nso-india/esankhyiki-mcp, swagger/swagger_user_cpi.yaml and mospi/client.py, Nov 2026):
  GET /api/cpi/getCPIIndex   base_year=2012|2010|2024 (required), series=Current|Back (required),
                             year=YYYY[,YYYY], month_code=1..12, state_code (1-36, 99 = all India),
                             group_code, subgroup_code, sector_code (1-3), limit, page, Format=JSON|CSV
  GET /api/cpi/getItemIndex  base_year, series, year, month_code, item_code, limit, page, Format
                             (state_code/sector_code only for base_year 2024)
  GET /api/cpi/getCPIData    base 2024 unified endpoint (the MCP client switches to it for 2024)
  GET /api/cpi/getCpiFilterByLevelAndBaseYear?base_year=&level=Group|Item&series_code=Current
  GET /api/cpi/getCpiBaseYear
  The MCP client calls these without a token. An older MoSPI manual (api.mospi.gov.in/API/
  CPI API User Manual.pdf) says that without a login token only the first 10 records are
  returned. [UNVERIFIED which rule applies now] -> the script pages with limit/page, checks
  for a 10-row cap, and if capped tells the user to register and pass --token.
  The MCP client also enables legacy TLS renegotiation for this host. If you get an SSL
  error 'unsafe legacy renegotiation', run with --legacy-tls (still verifies certificates).

Base change (verified, PIB/MoSPI release of 12 Feb 2026): CPI base 2024=100 from Jan 2026;
official y/y inflation for Jan 2026 is published on the new base; linking factors to base
2012 are given for the GENERAL INDEX ONLY (rural 0.5222, urban 0.5320, combined 0.5267).
D7: all subgroup/item analysis ends Dec 2025; 2026 headline y/y is taken only as MoSPI's
official y/y on base 2024 (use --base2024 to fetch it into a separate file; never spliced).

Weights: [UNVERIFIED] the API is not known to return item/subgroup weights. The script keeps
any weight column the API returns; otherwise put MoSPI's base-2012 weighting diagram
(xlsx/pdf->csv) in data/raw/cpi/manual/ and record its URL in the acquisition log.

Outputs
  data/raw/cpi/<endpoint>/<year>_p<page>.(csv|json)   untouched API responses
  data/processed/cpi2012_group_state.csv   tidy: year, month, state, sector, group, subgroup, index, inflation, ...
  data/processed/cpi2012_item.csv          tidy item-level (all-India)
  data/processed/cpi2024_official.csv      (only with --base2024) official base-2024 series, kept separate

Usage: python scripts/acquire/cpi.py [--root PATH] [--start 2013] [--end 2025] [--token TOKEN] [--base2024]
"""
from __future__ import annotations

import io
import json
import ssl
import sys

from acq_common import (Project, banner, base_parser, log_download, make_session, polite_sleep,
                        sha256_bytes)

SOURCE = "cpi"
BASE = "https://api.mospi.gov.in"


class LegacyTLSAdapter:
    """Build an HTTPAdapter that allows legacy renegotiation but keeps certificate checks."""

    @staticmethod
    def mount(session):
        from requests.adapters import HTTPAdapter
        from urllib3.util.ssl_ import create_urllib3_context

        class _A(HTTPAdapter):
            def init_poolmanager(self, *a, **kw):
                ctx = create_urllib3_context()
                ctx.load_default_certs()
                ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
                kw["ssl_context"] = ctx
                return super().init_poolmanager(*a, **kw)
        session.mount("https://api.mospi.gov.in", _A(max_retries=3))


def get_pages(proj, s, endpoint, params, tag, args):
    """Page through an endpoint; save every raw response; return list of JSON records."""
    recs, page = [], 1
    limits = [args.limit, 1000, 100, None]  # MoSPI answers HTTP 400 to some limit values; fall back, then no paging
    li = 0
    while True:
        lim = limits[li]
        q = dict(params, Format="JSON") if lim is None else dict(params, limit=lim, page=page, Format="JSON")
        url = f"{BASE}{endpoint}"
        try:
            r = s.get(url, params=q, timeout=args.timeout)
        except Exception as e:
            log_download(proj, SOURCE, url + "?" + json.dumps(q), f"error:{type(e).__name__}", None, "", str(e))
            print(f"[fail] {endpoint} {params}: {e}")
            break
        body = r.content
        d = proj.raw_dir(SOURCE) / endpoint.strip("/").replace("/", "_")
        d.mkdir(parents=True, exist_ok=True)
        fn = d / f"{tag}_p{page}.json"
        fn.write_bytes(body)
        log_download(proj, SOURCE, r.url, r.status_code, len(body), sha256_bytes(body), f"{tag} page {page}")
        if r.status_code == 400 and page == 1 and li < len(limits) - 1:
            li += 1
            print(f"[http 400] {r.url} -> retrying with limit={limits[li]}")
            continue
        if r.status_code != 200:
            print(f"[http {r.status_code}] {r.url}")
            break
        try:
            js = r.json()
        except ValueError:
            print(f"[warn] non-JSON response for {r.url}")
            break
        data = js.get("data") if isinstance(js, dict) else js
        if isinstance(data, dict):  # some MoSPI endpoints nest {'data': {'records': [...]}}
            data = next((v for v in data.values() if isinstance(v, list)), [])
        data = data or []
        recs.extend(data)
        if lim is None:
            print(f"[info] {endpoint} {params}: {len(data)} records without paging parameters")
            break
        if page == 1 and len(data) == 10 and lim > 10:
            print("[WARN] exactly 10 records returned with limit>10: probably the no-token cap. "
                  "Register at api.mospi.gov.in and pass --token.")
        if len(data) < lim:
            break
        page += 1
        polite_sleep(args.sleep)
    return recs


def main():
    p = base_parser(__doc__)
    p.add_argument("--start", type=int, default=2013)
    p.add_argument("--end", type=int, default=2025)
    p.add_argument("--limit", type=int, default=5000, help="records per page [UNVERIFIED max]")
    p.add_argument("--token", default=None, help="Bearer token if the API requires one")
    p.add_argument("--legacy-tls", action="store_true")
    p.add_argument("--base2024", action="store_true", help="also fetch official base-2024 series (2026)")
    args = p.parse_args()
    if args.end > 2025:
        sys.exit("D7: base-2012 analysis ends Dec 2025; use --base2024 for 2026 headline only.")
    proj = Project(args.root)
    s = make_session()
    if args.legacy_tls:
        LegacyTLSAdapter.mount(s)
    if args.token:
        s.headers["Authorization"] = f"Bearer {args.token}"
    banner("MoSPI CPI base 2012")

    # metadata (codes for groups, subgroups, items, states) -- saved raw for the codebook
    for lvl in ("Group", "Item"):
        get_pages(proj, s, "/api/cpi/getCpiFilterByLevelAndBaseYear",
                  {"base_year": "2012", "level": lvl, "series_code": "Current"}, f"filters_{lvl}", args)
    get_pages(proj, s, "/api/cpi/getCpiBaseYear", {}, "baseyears", args)

    import pandas as pd
    grp, itm = [], []
    for y in range(args.start, args.end + 1):
        grp += get_pages(proj, s, "/api/cpi/getCPIIndex",
                         {"base_year": "2012", "series": "Current", "year": str(y)}, f"group_{y}", args)
        polite_sleep(args.sleep)
        itm += get_pages(proj, s, "/api/cpi/getItemIndex",
                         {"base_year": "2012", "series": "Current", "year": str(y)}, f"item_{y}", args)
        polite_sleep(args.sleep)
        print(f"{y}: group/state records so far {len(grp)}, item records so far {len(itm)}")

    def tidy(recs, name):
        if not recs:
            print(f"[WARN] no records for {name}")
            return
        df = pd.DataFrame(recs)
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        # [UNVERIFIED] field names; keep all columns, add a sortable period if year/month exist
        mcol = next((c for c in df.columns if c in ("month", "month_code", "monthcode")), None)
        if "year" in df.columns and mcol:
            mm = df[mcol]
            if mm.dtype == object:
                mm = pd.to_datetime(mm.astype(str).str[:3], format="%b", errors="coerce").dt.month.fillna(
                    pd.to_numeric(df[mcol], errors="coerce"))
            df["period"] = pd.to_datetime(dict(year=pd.to_numeric(df["year"], errors="coerce"),
                                               month=pd.to_numeric(mm, errors="coerce"), day=1),
                                          errors="coerce").dt.strftime("%Y-%m")
            df = df[df["period"] <= "2025-12"]
        out = proj.processed / name
        df.to_csv(out, index=False)
        wcols = [c for c in df.columns if "weight" in c]
        print(f"wrote {out} ({len(df)} rows; weight columns: {wcols or 'none -> see manual weights'})")

    tidy(grp, "cpi2012_group_state.csv")
    tidy(itm, "cpi2012_item.csv")

    if args.base2024:
        b = get_pages(proj, s, "/api/cpi/getCPIData",
                      {"base_year": "2024", "series": "Current", "year": "2026"}, "base2024_2026", args)
        if b:
            pd.DataFrame(b).to_csv(proj.processed / "cpi2024_official.csv", index=False)
            print("wrote cpi2024_official.csv (kept separate; never spliced to base 2012 except "
                  "the general index via MoSPI's linking factor, if at all)")


if __name__ == "__main__":
    main()
