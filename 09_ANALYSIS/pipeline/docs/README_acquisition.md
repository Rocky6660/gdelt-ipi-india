# Data acquisition: run order, outputs, manual fallbacks

All scripts are in `scripts/acquire/`, take `--root PATH` (default: the repository root), write raw downloads
untouched to `data/raw/<source>/`, tidy files to `data/processed/`, and one line per download to
`logs/acquisition_log.csv` (`timestamp, source, url, status, bytes, sha256, notes`).
Nothing in this folder contains data typed in by hand or from memory: every value comes from a download or from a
file you fill from an official PDF (the templates).

The scripts were written in a cloud workspace that could not reach rbi.org.in, mospi.gov.in, gdeltproject.org,
trends.google.com or Google APIs, so **none has been run against the live sites**. Anything marked
`[UNVERIFIED]` in a docstring is a guess about a page layout or API that the first run will confirm or refute.

## Setup

```bash
cd <repo root>
python -m venv .venv && source .venv/bin/activate
pip install -r scripts/acquire/requirements.txt
cd scripts/acquire          # scripts import acq_common.py from this folder
```

## Run order

| # | Command | Decision | Expected outputs | Typical time |
|---|---|---|---|---|
| 1 | `python net_check.py` | all | table on screen; `logs/net_check.json` | 1 min |
| 2 | `python iesh.py` (add `--scan-ids 14000 24200` if the link crawl finds few rounds) | D3, D7 | `data/raw/iesh_rounds.csv`; `data/processed/iesh_city_round.csv`, `iesh_national_round.csv`, `iesh_distribution_round.csv`, `iesh_definitions.csv`; `data/interim/iesh_tables/` | 10-60 min |
| 3 | `python iesh_microdata.py` | D39 | `data/processed/iesh_microdata_stacked.csv`, `logs/iesh_microdata_report.json` (exit code 2 = manual step needed) | 5 min + manual |
| 4 | `python cpi.py` (`--base2024` for the 2026 official series) | D7, D26 | `data/processed/cpi2012_group_state.csv`, `cpi2012_item.csv` (to Dec 2025) | 10-30 min |
| 5 | `python doca_prices.py` | D38, D42(d) | `data/processed/doca_centre_daily.csv`, `iesh_city_centre_match.csv`; `logs/doca_form_fields.json` | 5 min + manual |
| 6 | `python policy_markets.py` | D7 | `data/processed/markets_daily.csv`, `markets_monthly.csv`; `mpc_meetings.csv`, `repo_rate_daily.csv` after the manual file | 2 min + manual |
| 7 | `python trends.py pull --states` on **three different days**, then `python trends.py combine` | D7, D17, D26 | `data/processed/trends_monthly.csv`, `trends_state_filter.csv` | 1-3 h per pull (rate limits) |
| 8 | `python doc_api_test.py` | D8 | `logs/doc_api_test.json` (overall_pass) | 2 min |
| 9 | `python gcam_pilot.py` (after step 2, so fieldwork dates exist) | D6 | `logs/gcam_pilot.json` (decision), `docs/gcam_ids.md`, `data/processed/gcam_ids.csv` | 1-3 h (3 days of files, several GB) |

Steps 8 and 9 do not depend on 3-7 and can run in parallel with them. Start step 7 on day 1, because it needs
three different days.

## What each script knows and what it guesses

### iesh.py (D3, D7)
- Verified: release pages `https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=<n>` (Sep 2026 round = 24089,
  Jul 2026 = 24077, May 2020 = 19456); opening paragraph gives round, fieldwork dates, city count and N; the Sep 2026
  page has Table 2 (groups and 19 cities, Mean and Median with SE for current perception, 3-month and 1-year),
  Table 3 (recent rounds), Table 5(a)/(b) (respondent counts by 1-pp bins), footnote "median unless stated
  otherwise", and Excel/PDF attachments on rbidocs.rbi.org.in. May 2020 was a telephone survey in 18 cities.
- Guessed: exact HTML markup; that each release links its predecessor (the crawler follows any IESH page link);
  that older releases have the same tables. Unknown formats are flagged in `flags`, never filled.
- D7 dispute (accepted): `iesh_distribution_round.csv` gives, per round and horizon, the share expecting
  >= 10%, a midpoint mean (top bin >= 16 set to 16.5, declared; `top_bin_share` reported), the interpolated
  median and the median bin. The bin step is 1 pp (RBI Bulletin July 2025). Both the >=10% share and the published
  mean must be declared as the continuous variants before Gate 2.
- **Manual fallback:** copy the three templates in `scripts/acquire/templates/` (`iesh_rounds_manual_template.csv`,
  `iesh_city_round_manual_template.csv`, `iesh_distribution_manual_template.csv`) to
  `data/raw/iesh/manual/` as `iesh_rounds_manual.csv`, `iesh_city_round_manual.csv`,
  `iesh_distribution_manual.csv`; delete the EXAMPLE rows; fill from each release PDF
  (Table 2 for cities, Table 5 for bins); put the exact sentence with the dates in `fieldwork_snippet`; run
  `python iesh.py --offline`. Manual values fill gaps; where they disagree with the scrape, a flag is written and
  the scrape is kept. Codes: `measure` = perception | exp_3m | exp_1y; `stat` = mean | median.
- Rounds without fieldwork dates are excluded from window tests (D3), never imputed.
- If rbi.org.in shows a captcha to scripts, the script deletes the captcha page, logs `captcha`, and you use the
  manual route (or save each release page from your browser as `data/raw/iesh/<id>/page.html` and run `--offline`).

### iesh_microdata.py (D39)
- Verified: releases point to DBIE (`https://data.rbi.org.in/DBIE/#/dbie/home`), head "Unit-level Data"; an RBI
  press release on dissemination of IESH unit-level data exists; RBI staff use the unit-level data.
- Guessed: everything about scripted access. The script probes DBIE and its JS bundles for file links, saves them,
  and otherwise prints the manual procedure: download all IESH rounds from DBIE into
  `data/raw/iesh_microdata/manual/`, then `--offline`. The report says whether a city variable exists.
- Fallback if DBIE has nothing: published city tables from iesh.py (D39).

### cpi.py (D7, D26)
- Verified (swagger in MoSPI's own MCP repo `nso-india/esankhyiki-mcp`): `https://api.mospi.gov.in/api/cpi/getCPIIndex`
  and `/getItemIndex` with `base_year=2012&series=Current&year=...&Format=JSON&limit=&page=`; state codes 1-36,
  99 = all-India; base 2024 via `/api/cpi/getCPIData`.
- Verified (MoSPI/PIB release 12 Feb 2026): base 2024 from Jan 2026; official y/y published on the new base;
  linking factors for the general index only (rural 0.5222, urban 0.5320, combined 0.5267).
- Guessed: whether a token is needed (an older manual says no-token calls return 10 records; the script warns),
  maximum page size, response field names, whether weights are returned. **Weights:** if not in the API, download
  MoSPI's base-2012 weighting diagram and put it in `data/raw/cpi/manual/`.
- TLS: if you see "unsafe legacy renegotiation", add `--legacy-tls` (certificates are still verified).

### doca_prices.py (D38)
- Verified (CEDA README and landing page): 22 commodities, from 2009; centre-level archive 2009-2023; from Sep
  2023 DoCA reports state/UT aggregates and CEDA says centre-level data are no longer published. So E1 with a
  centre-level control most likely ends Aug 2023 (D38), unless the DoCA site still serves centre reports.
- Guessed: any CEDA direct-download URL; DoCA form semantics. The script saves DoCA's form fields to
  `logs/doca_form_fields.json`; if you write `scripts/acquire/doca_form_config.json`
  (`{"static": {...}, "date_field": "...", "dates": ["dd/mm/yyyy", ...]}`), it replays the form for those dates.
- **Manual fallback (expected):** CEDA portal, centre-level retail prices, all commodities, download CSV(s) into
  `data/raw/doca/ceda_manual/`, then `--offline`. `iesh_city_centre_match.csv` reports first/last date per IESH
  city; this is the evidence for D42 gate (d), due end of day 3.
- City-to-centre map: `scripts/acquire/iesh_city_centre_map.csv`. The 19 cities and their states are known
  (Sep 2026 release); the DoCA centre names are candidates (same name, alternative spellings listed) marked
  `UNVERIFIED-candidate` until the match file confirms them.

### policy_markets.py (D7)
- FRED CSVs (no key): `DCOILBRENTEU` Brent daily, `DEXINUS` INR/USD daily, `INDIRLTLT01STM` 10-year G-sec monthly
  (OECD). MoSPI API RBI indicator 33 (monthly INR rates) is saved as a cross-check.
- **Repo rate and MPC dates: manual.** Fill `scripts/acquire/templates/mpc_decisions_template.csv` from RBI MPC
  resolution press releases (one row per meeting, with the press-release URL), save as
  `data/raw/policy/manual/mpc_decisions.csv`, re-run. The script checks the file and builds a daily repo series.
- Pump prices (optional): PPAC pages are saved and candidate files listed; the "RSP of Petrol and Diesel in Metro
  Cities since 16.6.2017" file URL is unverified. Metro cities only, so it does not cover most IESH cities.

### trends.py (D7, D17, D26)
- pytrends is unofficial and reportedly archived (Apr 2025); 429 errors are likely. The script backs off and
  resumes (files already pulled today are skipped). Terms are in `scripts/acquire/trends_terms.csv`.
- **Manual fallback:** in trends.google.com download `multiTimeline.csv` for each term and geo, time range
  2015-01-01 to 2026-10-31, and save as `data/raw/trends/manual/pull_YYYYMMDD/<GEO>__<term>.csv`
  (e.g. `IN__inflation.csv`, `IN-UP__महंगाई.csv`). Three different days, then `combine`.
- State rule: states with > 20% zero months are dropped (`trends_state_filter.csv`); state series are used
  within state only.

### doc_api_test.py (D8)
- Runs the four D8 queries for 2017-01 to 2026-10 with `timelinevolraw`, saves raw JSON, records first date,
  resolution, share of non-zero points, response headers, any throttling text, and a back-to-back probe for the
  rate limit. Pass = reaches Jan 2017 at daily or weekly resolution. The GDELT blog says both "back to January 1,
  2017" and "within the last 3 months"; this test decides.

### gcam_pilot.py (D6)
- No-go at once if `data.gdeltproject.org` is unreachable. Otherwise downloads both master file lists
  (`size md5 url` per line, format verified), computes MB/day for every day from the listed sizes, downloads all
  15-minute GKG and translation GKG files for 3 pilot days (md5-checked), measures throughput and unzip/scan time,
  and projects download hours for scope 1 (30-day windows, 2020-2026) and scope 2 (7 days, 2022-2026) from the
  exact file sizes on the window days in `data/raw/iesh_rounds.csv`. Go if <= 72 h.
- Also downloads the GCAM codebook and regenerates `docs/gcam_ids.md` from it. The current `docs/gcam_ids.md`
  (Loughran-McDonald = c6.1-c6.6; WordNet Affect 1.0 = c14.1-c14.11; WordNet Affect 1.1 = c15.1-c15.280) was read
  through a summarising web tool and is marked unverified until regenerated.
- Pilot downloads are several GB; pick other `--days` if needed, or `--skip-download` for a size-only projection
  (then no throughput, so no decision).

## After the run: what to check by hand
1. `logs/net_check.json`: any host that failed; a 403 may be a captcha (open it in a browser).
2. `data/raw/iesh_rounds.csv`: every round has dates, mode and N; `flags` empty or explained. Mode is
   `not_stated` when the release does not say; fill it only from an official statement.
3. `data/processed/iesh_definitions.csv`: how the mean/median are defined per round (D7 Gate 2 rule).
4. `logs/acquisition_log.csv`: non-200 statuses.
5. `logs/doc_api_test.json` and `logs/gcam_pilot.json`: the D8 and D6 decisions.

## Known external facts used (with sources; see also docs/literature_check.md)
- IESH bins 1 pp wide, ">= 16", "No idea"; about 6,000 households, 19 cities, bi-monthly since 2016: RBI Bulletin
  Jul 2025 (Ruhi, Sharma, Sankaran), https://rbi.org.in/scripts/BS_ViewBulletin.aspx?Id=23518
- Sep 2026 IESH release: https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=24089
- CPI base 2024 and linking factors: https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc2026212787501.pdf
- MoSPI API spec: https://github.com/nso-india/esankhyiki-mcp (swagger/swagger_user_cpi.yaml)
- CEDA DoCA mirror: https://dca.ceda.ashoka.edu.in and /README.html
- GDELT DOC 2.0: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- GCAM codebook: http://data.gdeltproject.org/documentation/GCAM-MASTER-CODEBOOK.TXT
