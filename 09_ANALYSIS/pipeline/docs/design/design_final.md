# Final research design

Inflation perception index for India from GDELT, tested against RBI household inflation expectations.

## Status and user rulings (17 Nov 2026)

- **Source:** `agreed_design.md` (after 3 review rounds), with the eight outstanding fixes from `disputes.md` incorporated as proposed. No decision is open.
- **Agreement:** 35 of 43 decisions accepted by both reviewer and red-team critic in round 3 (81%), no fatal flaws. The remaining 8 (D2, D7, D16, D19, D25, D27, D28, D34) were settled by the user's ruling below. Rounds: 1 (Sonnet reviewer, Fable critic) 22%; 2 (Fable reviewer, Sonnet critic) 37%; 3 (Opus reviewer, Sonnet critic) 81%. Proposer: Opus (blind draft, merge, v2), Fable (v3).
- **User rulings, 17 Nov 2026 (13:44 IST), as recorded in `ledger.md`:**
  - All eight proposed fixes (D2, D7, D16, D19, D25, D27, D28, D34) **accepted**.
  - D16: **Mode A approved**: live + archived fetch of article texts (the ruling says ~400), for validation only, with success/failure logged; GDELT/NGrams fallback where needed.
  - Human coding approved: about 4.5 hours across days 4–5.
  - BigQuery sandbox project ID: `[project removed]`. Project folder `GDELT_IPI` prepared by the user; attachment pending verification.
  - Full scope retained: all five extensions, no downgrades for the deadline. Budget 0.55–0.67 TB; dry run and hard byte cap on every job; outlets and query plan frozen before major extraction; separate raw/processed/scripts/logs/docs; gates before claims; descriptive versions of extensions even if gates fail; no fabrication; no causal claims; blockers reported.
  - **Deadline: 25 Nov 2026.** Execution starts 17 Nov 2026. D34 is therefore compressed to 9 calendar days (Day 1 = 17 Nov, Day 9 = 25 Nov) with no component removed or downgraded, and D35's time-based cut order is replaced by a schedule-risk note under which nothing is cut without the user's approval.
- **Point for the user to confirm (not changed here):** the ruling's "~400 articles" is the blind-round figure. D15's LLM-coded strata total about 1,250 articles (1,310 if DOC passes). This design applies Mode A to the D15 sample as specified; if the user meant a cap of 400 fetches, D15 would need a ruling.

See "Changes from agreed_design" at the end of this file.

---

### D1. News source and columns [blind] (v3)
- **Choice:** `gdelt-bq.gdeltv2.gkg_partitioned`, always with `_PARTITIONTIME` filters, Feb 2015 to Oct 2026. Two column sets:
  - **Full set** (window days): `DATE, SourceCommonName, GKGRECORDID, DocumentIdentifier, Themes (V1), V2Tone, TranslationInfo`.
  - **Reduced set** (sampled non-window days): `DATE, SourceCommonName, Themes, TranslationInfo`.
  - Never read in BigQuery: `GCAM`, `Locations`/`V2Locations`, `V2Themes`.
  - Non-window days have no URL, so they are **not deduplicated** and carry no URL-section aggregates. A window-day check reports the article share with and without deduplication, which bounds the effect of the omission.
- **Rationale:** BigQuery bills every column read, in full, for every scanned partition. The table is not clustered on source, so **the `SourceCommonName` filter does not reduce billed bytes**; only the column list and the partition list do. GCAM and Locations are unaffordable. The URL is needed on window days for the audit, deduplication, edition paths (D40) and the outlet key (D2).
- **Alternatives:** Drop `DocumentIdentifier` everywhere (cheaper, but loses the audit and E1). Full set on all days (unaffordable).
- **Risk:** URL and record-ID strings may add 15–25% to window-day bytes (C). The dry run reports bytes per column, and the ladder is priced with them.
- **Cost:** See D4 and D37.

### D2. Corpus = frozen panel of Indian outlets [merged] (v3 note; fix accepted 17 Nov 2026)
- **Choice:** `outlets.csv` has columns `outlet_key, domain/host, language, outlet_type, single_state (Y/N), home_state (only if single-state), readership_rank (optional)`.
  - **Day-1 probe** (one partition): do `*.indiatimes.com` siblings appear separately in `SourceCommonName`? Pooling is the expected case. If pooled, the window-level `outlet_key` is the host parsed from `DocumentIdentifier`.
  - Q1 lists all `.in` domains and the top Indian-language domains from 1 day in 6, two columns (`SourceCommonName, TranslationInfo`).
  - `readership_rank` from public IRS summaries if obtainable, else a hand-keyed top-20 list; panel coverage of the top 20 is reported.
  - **Stage A/B source list:** seeded from the hand-keyed top-20 outlets and GDELT's domain-to-country lookup file (free, offline), so the major `.com` outlets (e.g. thehindu.com, hindustantimes.com) are named directly; the `.in` domains and Q1's Indian-language hits are then added. The list is printed at Gate 1a.
  - Frozen at Gate 1a. Stage A/B scans keep a generous superset of Indian sources; the frozen panel is applied offline (D34).
- **Rationale:** Domain filtering gives an interpretable panel. Multi-state Hindi dailies get no single home state; their geography comes from edition paths (D40).
- **Alternatives:** GDELT source-country field (noisy); all sources mentioning India (not the Indian press).
- **Risk:** The panel reflects what GDELT crawls, not readership. Reported, not fixed.
- **Cost:** Probe about 2 GB. Q1 about 8–10 GB. About 0.5 agent-day.

### D3. Sample, frequency, survey alignment [blind] (v3)
- **Choice:** Daily indices, aggregated to month (D11) and to **pre-fieldwork windows**: the days ending the day before fieldwork starts, with the length set by the ladder rung (30, 21 or 14 days). The fieldwork-inclusive window is a variant.
  - `iesh_rounds.csv`: round, fieldwork start/end (scraped from each release, no defaults), mode, cities, N.
  - **N table** (day 2, repeated in the paper): rounds in total; by survey mode; by inflation regime; and rounds whose window has ≥ 60% valid days. Expected 40–55 usable rounds.
  - The 2020 rounds get a telephone/COVID dummy, plus a drop-2020–21 robustness check.
  - **Window reliability:** on Stage A data, split-half reliability (odd vs even days) of the window IPI is reported for nested lengths (7, 14, 21, 30 days, as far as the rung allows). The primary window is the rung's window. The shortest window with reliability ≥ 0.8 is a robustness variant. If the primary window is below 0.8, D19 also shows the attenuation-adjusted coefficient.
- **Rationale:** The window must end before respondents are interviewed. Its length is fixed by a rule, not chosen after seeing results.
- **Alternatives:** Calendar-month alignment (mixes pre- and post-interview news). Choosing the window by reliability (adds a choice and discards days).
- **Risk:** Missing fieldwork dates for early rounds; those rounds are excluded, not imputed. Short windows under L3/L4 are noisy; the reliability figure shows how noisy.
- **Cost:** Part of WP2.

### D4. BigQuery extraction: pre-registered ladder, exact dry runs, capped chunks [merged] (v3)
- **Choice:**
  1. **Gate 0 check:** read the quota already used this month; the cap below is reduced by that amount.
  2. **Exact dry runs (free):** each rung's real query (real partition list, real columns) is dry-run and logged in `budget_ledger.csv`, with bytes per column.
  3. **Pre-registered ladder:** choose the lowest-numbered rung whose dry-run Q2 total is ≤ 650 GB. With Q1, the probe and tests (≤ 20 GB), the plan stays ≤ 670 GB, leaving about a third of the budget in reserve.

     | Rung | Window days (full set) | Non-window days (reduced set) | Start |
     |---|---|---|---|
     | L0 | all 30-day windows | all days | 2015-02 |
     | L1 | all 30-day windows | 1 in 2 days | 2015-02 |
     | L2 | 21 days before fieldwork | 1 in 3 days | 2015-02 |
     | L3 | 14 days before fieldwork | 1 in 4 days | 2016-01 |
     | L4 | 14 days before fieldwork | 1 in 6 days | 2017-01 |

     Systematic sampling uses a fixed seeded offset, the same for all outlets. No step is a multiple of 7, so every rung rotates through weekdays. **Always-sampled list** (reduced set): the D17 placebo dates ± 3 days. If even L4 exceeds 650 GB, Gate 0b escalates to the human: raw files for non-window days (D6 route) or a window-only design.
  4. **Query form, in order of preference:**
     - **(i) Single statement:** one CTE over the base table, then `UNION ALL` of (a) article-level rows for every ECON-tagged or inflation/price-flagged article, with the full `Themes` string, and (b) outlet × day × URL-section aggregates (counts and word sums), cast to a common schema. Adopted only if its dry-run bytes equal one scan. Results stay in anonymous result tables, outside sandbox storage [UNVERIFIED; tested on the first chunk]. Flags are derived offline from the `Themes` string.
     - **(ii) Temp tables:** only if (i) fails. A day-1 test runs a 1-day `CREATE TABLE AS` and reads the storage meter before and after. Chunks keep the temp table under 3 GB.
     - **(iii)** One query per chunk emitting (a) for all panel rows with reduced fields.
  5. **Chunks and safety:** chunk size comes from the probe: ≤ 60 GB scanned and ≤ 3 GB of output per job. Every job sets `maximum_bytes_billed` to its dry-run figure plus 5%. The first chunk of each stage is one month; its output is checked before the rest run (it is part of the stage, not a duplicate scan). The ledger holds a pre-run estimate and a post-run actual for every job.
  6. **Output size:** if Stage A's article rows project to more than 5 GB for the full run, the stored `Themes` string is cut to ECON-family and price-family tokens plus a hash of the remainder (D10).
  7. **Staging:** Stage A = 2022–2026 window days (day 2): early index, E1 cell counts, theme stability. Stage B = everything else on the rung (days 3–4). The partitions are disjoint, so the stages add and do not duplicate.
  8. **DOC-API contingency:** if D8 passes, an outlet-level `theme:ECON_INFLATION domain:<outlet>` share series is built at zero bytes, as a cross-check, and as the national monthly series if the ladder forces L4.
- **Rationale:** A full pass is estimated at 1.1–1.6 TB. Window days are what the IESH tests need; a systematic grid keeps the monthly index at a fraction of the cost. A ladder fixed before the dry run removes discretion. With no refill, one failed 100 GB job is the main operational risk, hence small capped chunks.
- **Alternatives:** Full pass with fallback (unaffordable). Raw files only (too slow as the main path). Year-sized scripts into temp tables (may exhaust a storage quota that is not refunded [V-R]).
- **Risk:** Monthly shares from 1-in-3 or 1-in-4 days are noisy. Months with fewer than 5 sampled valid days are not used in D23/D24, and days used are reported. Download of large results is slow; (b) is aggregated in SQL to keep output at a few GB. The download method (Storage Read API vs paged `tabledata.list`) is tested on the first chunk [UNVERIFIED].
- **Cost:** Q2 ≤ 650 GB by construction. Dry runs are free. A failed job costs at most 60 GB.

### D5. Geography for E1: edition-path audience exposure [merged] (v3)
- **Choice:** Local exposure for city c = panel articles whose URL path maps to c (or to state(c) for state-level pages) via `edition_patterns.csv` (D40), plus articles from single-state outlets whose home state = state(c). Multi-state outlets contribute only through edition paths. `Locations` is not used in BigQuery.
  - Patterns are validated **per calendar year** on window-day output. An outlet-year is dropped when its match rate falls below half of the outlet's 2022–26 rate. E1 uses only the years in which the D42 gates hold.
  - **Expected outcome, planned for:** the Hindi-belt cities share outlets and editions, so the effective number of independent units is about 8–12 exposure blocks, not 19 cities.
- **Rationale:** Domain home state collapses the Hindi-belt cities into one series. Edition paths give city variation where it exists; D42 decides whether it is enough.
- **Alternatives:** Geocoded mentions (unaffordable in BigQuery; measures where news is about, not who reads it). Domain home state (rejected in round 1).
- **Risk:** Sites change URL schemes, so 2015–21 coverage may be thin; cities without edition paths (Jammu, Raipur, Guwahati are candidates) drop out. Both are reported.
- **Cost:** Needs `DocumentIdentifier` on window days. About 1 agent-day for the pattern table.

### D6. GCAM emotions and geocoding: raw-file subsample [merged] (v3)
- **Choice:** Before downloading, verify the GCAM codebook IDs for WordNet-Affect and Loughran–McDonald [UNVERIFIED].
  - **Day-1 pilot (3 days of files):** first test that the proxy reaches the GDELT file host (if not, **no-go**). Then measure MB/day for both streams, `gkg` and `translation.gkg`.
  - **Scope 1:** pre-fieldwork windows, 2020–2026, inflation-flagged panel articles only (matched on Stage A/B `GKGRECORDID`s). **Scope 2** (tried if scope 1 fails the rule): last 7 days before fieldwork, 2022–2026.
  - **Go** if the projected download for a scope is ≤ 3 days of background running; otherwise **no-go** and V2Tone only.
  - Bandwidth priority: any D4 escalation first, GCAM second.
- **Rationale:** Keeps the user's emotion layer and base paper 1's measures as a subsample exercise, without spending BigQuery budget.
- **Alternatives:** GCAM in BigQuery (unaffordable). Dropping emotions (loses a user requirement before it is tested).
- **Risk:** R expects scope 1 to be no-go. Vernacular GCAM scores depend on machine translation and are reported as secondary.
- **Cost:** About 1 agent-day of scripting plus background bandwidth.

### D7. Outcome and control data [merged] (v3; fix accepted 17 Nov 2026)
- **Choice:**
  - **IESH** releases: national and city mean/median with standard errors for current perception, 3-month and 1-year expectations; product-group expectations; fieldwork dates. The scrape also records how the mean and median are defined and published in each round.
    - **Primary-outcome rule (fixed at Gate 2, before outcomes are merged):** the 1-year **mean** is primary only if published under one definition in all rounds; otherwise the 1-year **median** is primary. Both appear in every table.
    - **Median bin step and continuous variant:** if the median is primary, `analysis_plan.md` records its bin step (IESH medians come from binned responses and move in coarse steps). A continuous variant row is added: the share of respondents expecting 10% or more, or the published distribution mean. Both are declared before Gate 2.
  - **MoSPI CPI base 2012** through **Dec 2025**: all-India, subgroups, items with weights; state-wise series. All subgroup and item analysis ends Dec 2025. E1 ends Dec 2025 unless WP2 confirms a consistent state series.
    - **2026:** headline y/y is used only if MoSPI publishes an official y/y on the new base [V-C: base 2024 series from Jan 2026]. Otherwise all CPI-controlled regressions end Dec 2025, and the 2026 rounds enter only a labelled no-CPI prediction exercise.
  - **Policy/markets:** repo rate and MPC dates; Brent; INR/USD; 10-year G-sec.
  - **City-level daily prices (D38).** **Unit-level IESH (D39).**
  - **Google Trends:** India and states, monthly, "inflation", "mehngai/महंगाई", item terms. Each series fetched 3× on different days and averaged. States with more than 20% zero months are dropped. State series are used **within state only** (state fixed effects), never compared across states.
  - Secondary outcome: SPF (Tier C).
- **Rationale:** RBI headlines the median while the mean is more sensitive to news in the tails; a rule chosen before seeing results keeps one primary cell.
- **Alternatives:** Mean and median as co-primary (doubles the primary tests). Splicing CPI across the base change ourselves (not defensible in two weeks).
- **Risk:** IESH covers urban households in 19 cities [V-C]; the city list changed over time and is recorded per round.
- **Cost:** About 1.5 agent-days, started day 1.

### D8. GDELT DOC 2.0 API: gated component [merged] (v3 note)
- **Choice:** A day-1 test with 4 logged queries:
  - (i) `timelinevolraw` for `inflation sourcecountry:india`, 2017-01 to 2026-10;
  - (ii) operator-only `domain:thehindu.com`;
  - (iii) `theme:ECON_INFLATION domain:thehindu.com`;
  - (iv) `(inflation OR "price rise" OR costlier OR dearness) sourcelang:hindi`.

  The log also records the rate limit. Denominators come from matched operator-only queries. Hindi uses English-equivalent terms, since the API searches English machine translations [V-C].
  - **Pass** (depth back to 2017 at daily or weekly resolution): build the keyword IPI, outlet-level theme series, E3 item series and E3 direction FV.
  - **Fail:** named fallbacks. Validation uses Trends; E3 weights use Trends item attention and GKG item themes; E3 direction is cut. **No Phase-1 element depends on DOC.**
- **Rationale:** Documentation conflicts on depth; GDELT's blog says timeline modes reach back to Jan 2017 [V-R], so a pass is likely but must be tested.
- **Alternatives:** Rely on DOC for the baseline (rejected in round 1).
- **Risk:** Rate limits may slow E3's several hundred calls; responses are cached.
- **Cost:** About 0.5 day.

---

## B. Measurement

### D9. Inflation classifier [merged] (v3)
- **Choice:** Baseline flag = `ECON_INFLATION` in V1 Themes. The day-1 lookup confirms the exact code and that it appears in the **V1 `Themes` column** in every sample year. Variants: price-family themes; a World Bank price-stability theme [UNVERIFIED]; a strict variant (≥ 2 inflation-family themes).
  - The baseline is chosen by F2 on the audit (D15). Headline results are also shown for the strict variant.
  - **Theme stability:** only themes present in the panel in every sample year are used. A theme introduced mid-sample is excluded, or used from its start with a level-shift dummy.
  - **Failure action (pre-registered, joint with D17):** if the baseline fails the Trends check or shows fewer than 3 of 4 episodes, switch to the best-F2 variant, then the strict flag. If every variant fails, the index is described as "audited, not externally validated" and H1/H5 are reported as exploratory.
- **Rationale:** Themes are the only affordable content signal. A single theme hit cannot carry intensity, so the article share is the headline (D11).
- **Alternatives:** Keyword classifier on full text (not available at scale within GDELT-only and the budget).
- **Risk:** Recall for vernacular articles depends on machine translation (D29's gate).
- **Cost:** Included.

### D10. Theme flags and the full theme string [merged]
- **Choice:** About 40 boolean flags (monetary policy; fuel/energy; food/agriculture/commodities; international-theme markers; domestic markers; administered prices; any-ECON; placebo: sports, elections), derived offline from the full `Themes` string kept for every ECON or inflation/price-flagged row. If output size forces it, the string is trimmed as in D4.6.
- **Rationale:** India-specific causes (MSP, GST, hoarding, monsoon) may have no dedicated theme; with the string, co-occurrence definitions can be rebuilt without a rescan.
- **Alternatives:** Flags computed in SQL only (a missed theme would cost a rescan).
- **Risk:** Output size (handled in D4.6).
- **Cost:** Output only.

### D11. Index formulas [merged] (v3)
- **Choice:** Two series, each with one definition.
  - **Window series (enters H1 and H5):** article share `a_{o,w}` = flagged articles / all articles, on deduplicated articles (normalised URL within outlet), outlet key = host if siblings are pooled. `IPI^w = Σ_o ω_o a_{o,w}` with fixed ω over a balanced core (outlets present in ≥ 80% of windows).
  - **Monthly series (D17, D23, D24, figures):** outlet key = `SourceCommonName` × source language from `TranslationInfo`, no deduplication, so the definition is identical on every day. Monthly value = mean of daily outlet shares over the systematic sampling grid only; window days off the grid and always-sampled days are not used. Days used are reported.
  - The correlation between the two definitions on window days is a robustness line.
  - **A second core from 2018** includes vernacular outlets. The text states that before 2018 the IPI is an English-outlet series.
  - **Robustness rows, in this order:** (i) **word share** (flagged words / all words, from V2Tone field 7; the user's original formula; window days only), with a variant capping word counts at the outlet's 75th percentile; (ii) pooled ratio across outlets; (iii) share among ECON articles; (iv) readership-weighted, if D2 data exist; (v) cross-outlet wire-copy filter (same day, word count and tone vector).
  - Outlets with paywall/teaser breaks in median word count use the article share only.
- **Rationale:** R: a monthly series that mixes deduplicated host-level days with raw pooled-domain days would shift level at window boundaries, in step with the survey calendar. C: two co-headline indices plus variants multiply choices, so one index is named for the primary tests. The word share is demoted, not dropped: a single theme hit cannot measure word intensity, and word counts exist only on window days.
- **Alternatives:** Word share as headline (user's original; kept as row (i)). One series for both uses (not definable identically on all days).
- **Risk:** If the word share and the article share disagree in sign on H1, the paper says so in the main text.
- **Cost:** Local.

### D12. Tone/emotion layer [merged]
- **Choice:** Guaranteed on window days: V2Tone negativity, tone, polarity and activity density, as word-weighted means within inflation articles. Also a **within-outlet differential** (inflation-article negativity minus negativity of non-inflation ECON articles, same outlet and window), entered separately from the IPI. GCAM Panic/Distress and LM negativity come from the D6 subsample if it goes ahead.
- **Rationale:** The differential strips out the mechanical negativity of the word "inflation" and avoids a near-collinear product term.
- **Alternatives:** IPI × tone interaction (collinear). GCAM for the full sample (unaffordable).
- **Risk:** Tone is a dictionary measure on translated text for vernacular outlets; stated.
- **Cost:** Included.

### D13. Outages, crawl breaks and crawl transparency [blind] (v3 note)
- **Choice:** Day-level exclusions: global count < 50% of its 28-day median; core volume < 30% of its median; outlet-day volume < 30% of the outlet's own 28-day median. On sampled days the medians are taken over sampled days. Windows need ≥ 60% valid days. Main-text figure: monthly article counts per panel outlet. A global GKG volume plot and Bai–Perron breaks on core volume as figures.
- **Rationale:** GDELT has known gaps and crawl changes (base paper 1 documents one); a share index is robust to volume only if both numerator and denominator are crawled alike.
- **Alternatives:** Interpolating gaps (hides them).
- **Risk:** Thresholds are judgement calls; fixed before outcomes are merged.
- **Cost:** Trivial.

### D14. Co-occurrence subindices [blind]
- **Choice:** Shares of inflation articles that also carry a given flag family (D10). Always labelled "co-occurrence shares", non-exclusive, never "topics".
- **Rationale:** Themes tag presence, not what the article is about.
- **Alternatives:** Topic models (need full text).
- **Risk:** Readers may read them as causes; the label rule guards against that.
- **Cost:** Local.

---

## C. Validation

### D15. Audit sample and coding [merged] (v3)
- **Choice:** Drawn from window days (the only days with URLs). LLM-coded strata:
  - 300 flagged;
  - 300 ECON-unflagged;
  - non-ECON: 150 with a price keyword in the URL slug (or a DOC keyword hit) + 100 without;
  - vernacular: Hindi and one other language (Marathi or Bengali, whichever has more volume), each 100 flagged + 100 ECON-unflagged;
  - +60 DOC keyword hits unflagged by themes (only if DOC passes).

  Coding:
  - **Coders:** two LLM coders on native text where available; one human codes **150** articles (incl. 40 Hindi).
  - **Codebook:** about inflation or cost of living in India Y/N; direction; cause.
  - **Validation statistic:** human-vs-LLM κ with a 95% CI. LLM–LLM agreement is reported as reliability only.
  - **Estimation:** precision; recall with inverse-probability weights. The **gating recall** is recall within ECON plus slug-screened non-ECON. The unscreened non-ECON stratum is reported only as an upper bound on the miss rate, with an exact binomial interval. Every figure carries a CI.
  - **Pre-set rules:**
    - κ < 0.7 on relevance → human codes replace LLM codes for the estimates;
    - κ < 0.6 on direction or cause → those codes are not used in E3/E4 claims;
    - baseline precision ≥ 0.5 and gating recall ≥ 0.6, otherwise switch to the best-F2 variant.
- **Rationale:** R: 100 random non-ECON articles contain zero or one relevant article, so one article would decide the recall gate; and 25 per vernacular cell cannot resolve a 0.15 recall difference. LLM coding is cheap, so those strata are scaled; the human sample rises by half so κ's interval narrows.
- **Alternatives:** Human coding of everything (not feasible). Applying the κ rule to the CI's lower bound (C's other option; the larger human sample was chosen instead).
- **Risk:** Recall outside ECON and outside price-keyword slugs is bounded, not estimated. Even at 200 per language the vernacular recall difference has a wide interval; it is reported.
- **Cost:** About 1.5 agent-days + about 4.5 human hours.

### D16. Audit text source: Mode A approved, GDELT/NGrams fallback [merged] (v3; fix accepted and Mode A approved by the user 17 Nov 2026)
- **Choice:** The user approved **Mode A** on 17 Nov 2026. Mode B is the fallback.
  - **Hour-1 access test (Gate 0a):** fetch 20 audit-type URLs (live, then Wayback Machine). If more than half fail, Mode B is forced despite the approval.
  - **Mode A (approved):** live URL, falling back to the Wayback Machine, all years; 2015–2018 oversampled 1.5× for link rot. Used **only for validation**, never for index construction, and disclosed. Every fetch is logged with its outcome (live / archived / failed). Articles whose text cannot be fetched fall back to Mode B.
  - **Mode B (GDELT-only fallback):** (i) text reconstructed from **Web News NGrams 3.0** for 2020+ articles; (ii) **URL-slug coding** for all years (`DocumentIdentifier` is GDELT data).
    - **NGrams retrieval rule:** text is taken from the raw per-minute files around each audit article's GKG 15-minute timestamp (only the minute files around that timestamp are downloaded). The BigQuery `webngrams` table is used only if a one-day dry run fits a pre-set reserve of ≤ 60 GB.
    - **Sampling:** the 2020+ Mode B sample is drawn on a fixed, seeded set of k window days. k is set from the day-1 retrieval pilot's measured MB per minute file, with a cap of one day of background download. The 2020+ full-text metrics are reported as coming from a date-clustered sample, and their CIs are widened for clustering by day.
    - **Budget:** the retrieval is a line in `budget_ledger.csv`.
    - **Approximate text:** reconstructed text is stitched from overlapping pre/post snippets and is marked approximate; the coder codebook says so.
    - **Vernacular rule in Mode B:** if more than 50% of vernacular slugs are uninformative (numeric IDs, bare transliteration) and NGrams text cannot be retrieved, vernacular precision and recall are reported as "not estimable" and the E2 gate (D29) fails by rule.
  - The precision/recall table states the mode per article (Mode A live, Mode A archived, Mode B NGrams, Mode B slug); for Mode B it reports full-text metrics for 2020+ and slug-based metrics for all years, plus the share of uninformative slugs.
- **Rationale:** Full text gives the strongest audit; the user has approved fetching it for validation only. The agent's network may still not reach the sites, so the design must not stall. Per-article NGrams retrieval is not feasible without the file-based, date-clustered rule (GDELT warns some dates cost tens to hundreds of GB).
- **Alternatives:** Mode B only (weaker, especially for Hindi). Skip the audit (no measurement validity). BigQuery `webngrams` by default (unpriced; may exhaust the reserve).
- **Risk:** Link rot and blocked fetches push articles into Mode B, which is weaker, especially for Hindi. Mode B 2020+ intervals are wider because of day clustering.
- **Cost:** Mode A about 1 day. Mode B about 1–1.5 days. Day-1 retrieval pilot small (D6's raw pilot already tests file-host reachability).

### D17. External validation [merged] (v3)
- **Choice:**
  - **Google Trends** "inflation" and "mehngai" against the monthly IPI.
    - Necessary check: raw r ≥ 0.5, also reported after removing each series' trend in GDELT panel volume.
    - Reported with its interval: the partial correlation after removing CPI y/y and food CPI y/y. The phrase "supported by search data beyond co-movement with CPI" is used only if that interval excludes zero.
  - Correlations and cross-correlograms with CPI y/y and food CPI. The text says these check the index and are not evidence of information beyond CPI.
  - DOC keyword IPI, if D8 passes.
  - **Episodes:** onion 2019–20, fuel 2021–22, post-Ukraine 2022, tomato 2023. Peak = episode-window mean above the 90th percentile of **non-episode months**; acceptance in ≥ 3 of 4; episode z-scores reported.
  - **Non-price placebos:** general-election result days (23 May 2019, 4 June 2024) and the Cricket World Cup final (19 Nov 2023), where the daily IPI should show no peak. These dates ± 3 days are on the always-sampled list (D4).
  - **If the checks fail:** the action in D9.
- **Rationale:** C: Trends and the IPI both respond to CPI and to the same events, so a raw correlation shows co-movement with attention, not that the classifier is right. The audit (D15) carries content validity; Trends carries convergent validity.
- **Alternatives:** CPI correlation as the main validation (circular for a paper asking what the index adds to CPI).
- **Risk:** Trends is itself noisy and rescaled per request (hence three pulls).
- **Cost:** About 0.5 day.

### D18. Construction robustness [blind]
- **Choice:** Headline results are re-run on D11's robustness rows and D9's strict flag. They must survive the word-share and strict-flag rows to be stated without qualification.
- **Rationale:** The index involves several construction choices.
- **Alternatives:** A specification curve over all combinations (too many for N ≈ 45).
- **Risk:** Rows may disagree; reported in the main text.
- **Cost:** Local.

---

## D. Econometrics

All national claims refer to **urban households** (IESH covers 19 cities).

### Phase 1

### D19. National in-sample test [merged] (v3; fix accepted 17 Nov 2026)
- **Choice:** Round-level local projections, h = 0..3:
  `y_{r+h} − y_{r−1} = α_h + β_h IPI^w_r + λ_h y_{r−1} + Γ_h' X_r + ρ_h Δy_{r−1} + ε`
  - **Lagged level:** the lagged expectation level `y_{r−1}` is a regressor in the primary, so β does not pick up mean reversion. The ΔIPI variant is kept.
  - **Primary cell:** y = 1-year expectation (mean or median by the D7 rule), h = 0, `IPI^w` = window article share (D11). Other outcomes are secondary; other horizons are a figure.
  - **Pre-registered core controls X (real-time, as known at window end):** latest released CPI y/y; window-average DoCA food price change for the 22 essentials (food CPI y/y if DoCA is unavailable); Δrepo; survey-mode dummy.
  - **Rows shown beside the primary:** AR + CPI only; full set (adding food CPI y/y, pump-price change, Δln Brent).
  - **Reported:** β with CI, the partial R² of the IPI, and N.
  - **Persistence:** ADF/KPSS results for y and the IPI (low power at this N, stated); a ΔIPI variant.
  - **Future-CPI test:** add the CPI print for the survey month (published later). If β_0 vanishes, the result is reported as "the IPI behaves as a price nowcast".
  - **Inference:** EWC/fixed-b HAR critical values plus wild bootstrap. One-step estimation.
  - **Wording:** "predicts"; never "causes" or "drives".
- **Rationale:** Households see prices before CPI is printed, so real-time prices are the relevant control. With N ≈ 45, eight near-collinear controls overfit; a small core is fixed in advance and the larger set shown beside it.
- **Alternatives:** Levels VAR as the main test (too many parameters). Monthly interpolation of IESH (manufactures observations).
- **Risk:** Low power. The CI is the result; a null is reported as such (D31).
- **Cost:** Local.

### D20. Regime dependence [merged] (v3)
- **Choice:** Interact **only the IPI** (and the intercept) with `High_{r−1} = 1[CPI y/y > 6%]`; controls are common. A continuous version uses IPI × (CPI_{r−1} − 4). Rows: excluding 2020–21; **leave-one-episode-out**. The table prints high-regime and low-regime N. H2 is exploratory.
- **Rationale:** High-inflation rounds cluster in 2019–20, 2022 and mid-2023; with perhaps 6–10 of them outside the pandemic, one episode can drive the estimate.
- **Alternatives:** Threshold search (removed in v2). Fully interacted model (too few observations).
- **Risk:** The regime split may coincide with the telephone-survey rounds; the exclusion row shows it.
- **Cost:** Small.

### D21. Small VAR [user]
- **Choice:** Appendix only. Bimonthly [Brent, CPI, IPI, IESH 1-year, repo], ≤ 2 lags, Minnesota prior, two Cholesky orderings.
- **Rationale:** The user asked for it as robustness; it matches base paper 2.
- **Alternatives:** Main-text VAR (over-parameterised at this N).
- **Risk:** Identification by ordering is weak; described as illustrative.
- **Cost:** Small. Named in D35's schedule-risk note (slips early if a blocker occurs; not cut without user approval).

### D22. Pseudo-real-time prediction of the next survey release [blind] (v3)
- **Choice:** The IPI at the end of the pre-fieldwork window predicts the round's 1-year expectation, which RBI publishes some weeks later. Benchmarks: AR(1), and AR(1) + CPI + DoCA. One pre-declared model is the headline. Recursive estimation from about 20 rounds.
  - **Reported:** RMSE ratio with a bootstrap CI; Clark–West test.
  - Variants and extensions are compared with the headline model by pairwise Clark–West tests, Holm-adjusted. No model confidence set.
  - A null is described as low power: the survey is very persistent, so AR(1) is a strong benchmark, and there are about 25 evaluation rounds.
  - Giacomini–Rossi only if the window is at least 15.
  - **Wording:** "pseudo-real-time prediction" or "short-horizon forecast". "Nowcast" is not used for the IESH target.
- **Rationale:** The index is available before the survey is fielded, which is a real timing advantage, but the target is a 1–3 week ahead survey outcome, so "nowcast" over-states it (C).
- **Alternatives:** In-sample fit only (no evidence of usable content).
- **Risk:** GDELT data are not revised but the panel and theme choices were made with hindsight, hence "pseudo".
- **Cost:** Small.

### D23. Monthly attention dynamics [blind]
- **Choice:** Monthly LP of the IPI (monthly series, D11) on recursively computed AR(12) CPI surprises and on Brent shocks, h = 0..12. Months with fewer than 5 sampled valid days are excluded.
- **Rationale:** Shows what moves coverage; base paper 2's question at monthly frequency.
- **Alternatives:** Daily event study (CPI release days only; an FV if time allows).
- **Risk:** Sampling noise under L2–L4.
- **Cost:** Small.

### Phase 2 (all five attempted; MV guaranteed, FV if time permits; each with a data gate)

Common incremental-content rule: each extension adds its object to D19 (national) or D27 (panel). One summary table gives, per extension, the coefficient with CI, a Holm-adjusted p-value across extensions, and the pairwise Clark–West result against the D22 headline model. Extensions whose test cannot have power at this N are reported descriptively and say so (E5, E2's national comparison, E4 unless its gate passes).

### D24. E5 Attention cycle [user] (v3 note)
- **MV (descriptive):** asymmetric LP of the IPI on ΔCPI⁺ / ΔCPI⁻ (y/y and seasonally adjusted m/m); decay half-life after peaks; `ExcessAttention` during disinflation entered in the D19 specification with a bootstrapped CI.
- **FV:** Peak-aligned episode study.
- **Positioning:** an emerging-market replication of the ECB (2025) attention finding. No p-value in the abstract. Under L3/L4, half-lives are labelled coarse.
- **Rationale:** The user's fast-rise/slow-decay question; a handful of cycles since 2015 supports description, not testing.
- **Alternatives:** A structural attention model (out of scope).
- **Risk:** Few cycles.
- **Cost:** Half a day.

### D25. E4 Imported vs domestic narratives [merged] (v3; fix accepted 17 Nov 2026)
- **MV:** `S^{int}_t` = **share of inflation articles co-occurring with international themes** (oil, global commodities, exchange rate, foreign central banks), entered alongside the total IPI in D19. This name is used in all tables.
- **Gate:** **Cohen's κ** between the binary `S^{int}` article flag (any international theme co-occurring) and the binary D15 cause code "international/imported", on the flagged audit stratum (human codes where D15's κ rule replaced LLM codes).
  - **Pass:** κ ≥ 0.6 on the point estimate, **and** the D15 cause-code κ itself ≥ 0.6 (otherwise the gate fails by D15's rule). A pass → the text may call it "international framing of inflation". A fail → descriptive only, no regression claims.
  - **Reported:** the 95% CI of κ and the number of articles coded "international".
  - The cause-code → binary mapping is fixed in `analysis_plan.md` at Gate 2.
- No claim that the measure identifies the cause of inflation, and no exogeneity claim.
- **FV:** Split by English/vernacular.
- **Rationale:** A theme co-occurrence shows what else the article mentions, not what it blames (C).
- **Alternatives:** LLM cause coding of all articles (needs full text).
- **Risk:** The gate may fail; the extension is then a descriptive figure and table.
- **Cost:** Half a day.

### D26. E3 Salience basket and media-implied inflation [user] (v3)
- **MV:** About 10–12 CPI items/groups, Jan 2017 (2015 for Trends) to Dec 2025. Attention `m_{i,t}`:
  - **if DOC passes:** item-price article share, with queries requiring a price phrase, checked on 20 hits per item, dropping items with precision < 0.5;
  - **otherwise:** Google Trends item-price search attention plus any GKG item themes. The object is then called **"search-implied inflation"** in every table.

  Media weights are lagged one month and period-averaged. `π^{med}_t = Σ_i w^{med}_{i,t−1} π_{i,t}`. Benchmarks: `π^{CPI}` (official weights) and `π^{abs}` (items weighted by their own absolute inflation).
  - **Test:** change in IESH current perception on `π^{med}`, `π^{CPI}` and `π^{abs}` **in the same specification**, reported as a horse race. The regression of the perception gap on `π^{med} − π^{CPI}` is removed.
- **Wording:** a coverage-selection decomposition, not a structural explanation.
- **FV (only if DOC passes):** direction coding (rising vs falling phrases) and an asymmetry test.
- **Rationale:** C: CPI enters both sides of the removed regression with opposite signs, so it would show a relation with no media effect at all.
- **Alternatives:** Weights from GKG themes only (too few item themes).
- **Risk:** The three inflation measures are collinear; the horse race may be uninformative, which is reported.
- **Cost:** One day.

### D27. E1 City panel [merged] (v3; fix accepted 17 Nov 2026)
- **MV:** Two levels.
  - **(a) City × round:**
    `y_{c,r} = μ_c + τ_r + β IPI^{loc}_{c,r} + γ' P_{c,r} + δ π^{state}_{s(c),r−1} + ε`
    y = city 1-year expectation (same statistic as D19's primary), weighted by the **inverse squared published standard error** of the city statistic (IESH releases do not publish city counts). Microdata counts are used only if D39 succeeds; the text states which weighting applies. `P_{c,r}` = window-average DoCA retail food price change for city c's centre (D38); pump-price change if available. `IPI^{loc}` follows D5/D40 and is built from a **balanced set of city-edition sources** (present in ≥ 80% of the city's windows); the share of local articles from that set is reported.
  - **(b) Respondent level (D39)**, same regressors plus age, gender, occupation, if the microdata carry city and round.

  **Inference:**
  - **Primary p-value: block-level randomisation inference.** Collapse to block × round (cities within a block averaged with the weights above) and permute block exposure series across blocks (999 draws; with 8 blocks there are 40,320 permutations). The smallest attainable p-value is reported.
  - Secondary: the city-level permutation (whole exposure series across cities, 999 draws); wild cluster bootstrap at exposure-block level with Webb weights.
  - Blocks are defined by shared source (D42).

  Robustness rows: language-block × year FE; outlet-level panel with outlet FE; drop 2020–21; the rows in D28.

  h = 0 only. Sample ends Dec 2025 at the latest (earlier if D38's centre data end earlier).
- **Gates (pre-outcome, D42):** four gates and three tiers. If E1 is not inferential, it is reported descriptively (exposure maps, correlations).
- **Wording:** "association conditional on observed local prices". The 22 essentials do not cover rents, services or all local fuel variation, so unobserved local prices remain a stated alternative reading.
- **FV:** Geocoded exposure from the D6 subsample; interactions by occupation/education in the microdata.
- **Rationale:** Round effects absorb everything national; city-level prices absorb what households see in the market. With 8–12 blocks the wild bootstrap is unreliable, so RI leads (R, C). Cities in one block share sources and press-market shocks, so city-level permutations would break the blocks and give an anti-conservative p-value; permutation is therefore at block level (R).
- **Alternatives:** State panel on state CPI only (no survey outcome at state level). Geocoded exposure (unaffordable).
- **Risk:** Any gate may fail. Compositional drift in sources is limited, not removed, by the balanced set.
- **Cost:** One day of analysis; data prep runs in parallel from day 1.

### D28. E1 robustness rows [blind] (v3; shift-share IV REMOVED in v2; fix accepted 17 Nov 2026)
- **Choice:**
  1. **Common-shock robustness row:** recompute `IPI^{loc}` from local-edition articles co-flagged with national-policy themes (RBI/monetary policy, union budget, GST council). A cell-count check for this row is run before outcomes are merged, with D42.
     - **If cells are too thin (pre-declared substitute):** city exposure to outlet-level national-section inflation coverage, weighted by each outlet's share of the city's local articles in the first 12 sample months (those months are dropped from this row). It is a regressor, not an instrument.
     - This row tests whether the association survives when local price stories are excluded. It is **not** exogenous variation: national stories in city editions may be shared wire copy.
  2. **REMOVED (v2):** shift-share IV.
  3. **Placebos:**
     - **Lead exposure (the key check):** `IPI^{loc}` built from the **next round's pre-fieldwork window**, which carries URLs (days +1 to +30 after fieldwork are mostly reduced-set days with no URL, so local exposure cannot be built for them). The text states the lead window's overlap with days +21 to +50 after fieldwork. Its cell counts are part of the D42 cell-count check.
     - Local sports share; local total volume.

  **Wording rule:** no causal language for E1 under any outcome. If the main β, row 1 (same sign, RI interval excluding 0) and the row-3 placebos (null) all hold, the strongest permitted sentence is "consistent with a news channel, and not explained by next-round (lead-window) news, local news volume or observed local prices". If row 1 has no usable cells in either form, the text says the association could not be separated from local price coverage.
- **Rationale:** R: national-policy stories rarely run in local editions, so the v2 rule for causal language could never be met. C: the row addresses common shocks, not exogeneity. Dropping the causal tier removes the over-claim.
- **Alternatives:** An instrument (removed; no defensible exclusion restriction in two weeks).
- **Risk:** Row 1 may be empty.
- **Cost:** Half a day.

### D29. E2 English vs vernacular [merged] (v3)
- **Gate:** vernacular recall (D15) within 0.15 of English recall on the point estimates, intervals reported. Otherwise, or if "not estimable" (D16), E2 is reported as a measurement result (differential theme recall under machine translation).
- **MV:** z-scored national `IPI^{eng}`, `IPI^{ver}`; lead-lag; **same-city horse race in the D27 panel as the main evidence** (only if E1 is at least in the middle tier of D42). If microdata are available: interaction with occupation/education.
- **H7 (two-sided, exploratory):** β^{ver} ≠ β^{eng} for current perception. The national difference is reported descriptively, with a statement that it has almost no power: the two series are likely correlated above 0.8 and N ≈ 45.
- **Stated confound:** IESH does not record which language respondents read, so differences may reflect city composition (Hindi vs English markets), not exposure channels.
- **FV:** Per-language series.
- Cite Arndt (2024, 2026).
- **Rationale:** The user's question stays in the paper; the claim is sized to what the data can show.
- **Alternatives:** One-sided strict test at national level (v2; no power).
- **Risk:** If both the recall gate and E1 fail, E2 is two lines on a chart and a recall table. That is still a useful result about GDELT translingual coverage.
- **Cost:** Half a day.

### D30. Perceived-inflation gap [blind] (v3)
- **Choice:** `gap_r` = IESH current-perception median in round r (mean as variant) minus the latest CPI y/y released before fieldwork starts; variant with the survey-month CPI. Reported as a descriptive series and in changes only, never as a level to be explained. The text notes that perception sits persistently above CPI, so gap changes have little variance. The gap is not a dependent variable in E3 (D26).
- **Rationale:** The level of the gap reflects survey design and household baskets as much as news.
- **Alternatives:** Explaining the level (not identified).
- **Risk:** Little variance to describe.
- **Cost:** Trivial.

### D31. Hypotheses [merged] (v3 note)
- **Choice:** **Primary:**
  - H1: the window IPI predicts the IESH 1-year expectation of urban households beyond real-time prices (one-sided). D19 is the in-sample test and decides H1; D22 is its out-of-sample counterpart. "Out-of-sample" appears in the abstract only if D22's Clark–West test also rejects.
  - H5: β > 0 in the city panel (D27), primary only in D42's top tier.

  H1 alone is tested at 5%. If H5 is also tested, the two are Holm-adjusted.

  **Secondary**, Holm-adjusted: H2 regime (exploratory); H3 E5; H4 E4; H6 E3; H7 E2 (two-sided, exploratory).

  **If H1 is null:** the paper's contribution is the audited index, the coverage audit and a null with confidence intervals, and the abstract says so.

  Frozen in `analysis_plan.md` at Gate 2, before outcomes are merged with news data.
- **Rationale:** One index, one outcome, one in-sample test for the main claim.
- **Alternatives:** Treating D19 and D22 as two primaries (tests one effect twice).
- **Risk:** None beyond low power.
- **Cost:** Trivial.

---

## E. Contribution

### D32. Prior work [merged] (v3)
- **Choice:** The v2 list plus, for day-1 verification:
  - Kishor & Pratap (2023), news-sentiment inflation index from Indian business dailies [V-C that it exists; content to be read];
  - RBI Bulletin (2022), "Forecasting Food Inflation using News-based Sentiment Indicators";
  - IIM Calcutta WPS 830 [UNVERIFIED].

  A comparison sentence (few English business dailies, dictionary sentiment, CPI or forecaster outcomes; no household survey, no vernacular press) is written **only after each paper is read**.
  - The Ruhi–Sharma–Sankaran (RBI Bulletin, July 2025) claim that IESH lacks media exposure is quoted only once verified.
  - **To resolve on day 1:** C attributes MPRA 118951 to Kishor & Pratap; the user's list describes MPRA 118951 as a paper on inflation targeting and anchoring. One label is wrong.
- **Rationale:** The claims in D33 depend on what these papers did.
- **Alternatives:** None.
- **Risk:** A closer precedent may turn up; D33's wording does not depend on being first.
- **Cost:** Part of day 1.

### D33. Contributions [merged] (v3)
- **Choice:**
  1. **An open, reproducible, audited news-based inflation perception index for India**, with (a) a test of its content for urban household expectations beyond real-time prices, and (b) an audit of how GDELT covers the Indian press, English and vernacular (panel coverage, theme precision/recall by language, crawl breaks). "Validated" is used only if D15 and D17 pass.
  2. **Conditional on gates:** city-level association between local news exposure and expectations (E1); English vs vernacular coverage (E2).
  3. **Applications to India of known mechanisms, mostly descriptive:** attention cycle (E5), international framing (E4), salience-weighted media-implied inflation (E3).
- **Not claimed:** first Indian news-inflation index; first GDELT-based index; causal effects at national or city level; a structural explanation of the perception gap; results for rural households.
- A literature-search note states what was searched and when.
- **Rationale:** C: the "first ... GDELT-based ... including vernacular" sentence was true but narrow. The household-expectations test and the coverage audit are the parts other researchers can use.
- **Alternatives:** Leading with E1 (depends on four gates).
- **Risk:** If H1 is null and E1 is descriptive, the paper is a data and measurement paper. That outcome is stated in advance (D31).
- **Cost:** None.

---

## F. Execution

### D34. Work plan (9 days, 17–25 Nov 2026) [merged] (v3; fix accepted 17 Nov 2026; compressed from 14 days per the user's deadline)

Day 1 = Tue 17 Nov; Day 9 = Wed 25 Nov (deadline). Days 5–6 are Sat 21 and Sun 22 Nov. Nothing is removed or downgraded from the 14-day plan: the same components and gates run, with independent workstreams in parallel.

**Workstreams (run by separate agents in parallel):**
- **W1 BigQuery and index:** dry runs, probe, Q1, Stage A/B, download, indices.
- **W2 Outcomes and controls:** IESH, CPI, policy/markets, Trends, DoCA/CEDA, DBIE microdata, SPF.
- **W3 Audit:** Mode A retrieval, Mode B fallback, LLM coding, human coding, κ and precision/recall.
- **W4 Geography and E1 gates:** edition patterns, cell counts, D38 coverage, D42 gates and blocks.
- **W5 DOC, raw files and E3 inputs:** DOC test and series, GCAM pilot and background download, E3 item attention.
- **W6 Literature and writing.**
- **W7 Estimation code and reproduction:** D19–D30 scripts written and unit-tested on simulated data before Gate 2 (no news data merged with outcomes); second-agent reproduction after Gate 2.

| Day | Workstreams in parallel | Gate / acceptance |
|---|---|---|
| **1 — Tue 17 Nov** (hour 1) | Human: confirm sandbox access (`[project removed]`) and the project folder. Agent: 20-URL access test (D16; Mode A already approved); read quota used (D4) | **Gate 0a** |
| **1 — Tue 17 Nov** | W1: exact dry runs per rung (D4); probe (D2); single-statement and CTAS tests (D4.4); theme lookup (D9); Q1; Stage A/B source list seeded from top-20 + domain-to-country file, then `.in` and Q1 hits (D2). ‖ W2: IESH fieldwork dates, definitions and bin step (D3, D7); CPI and policy/market downloads; Trends pull 1; DoCA/CEDA download start (D38); DBIE microdata attempt (D39). ‖ W3: D16 retrieval pilot (NGrams MB per minute file → k); fetch log set up. ‖ W5: DOC test (D8); GCAM codebook and raw pilot (D6). ‖ W6: literature verification (D32) | **Gate 0b (human):** rung (mechanical), query form, DOC pass/fail, GCAM go/no-go, recorded. **Gate 1a (end of Day 1):** freeze outlets and themes; source list printed. **Rule: the Q1 probe and the Gate 1a freeze finish before Stage A starts.** |
| **2 — Wed 18 Nov** | W1: Stage A (2022–26 windows): one-month chunk first, then the rest → early index; theme stability; N table and window reliability (D3). ‖ W2: IESH national/city scrape; CPI subgroups, items, states; Trends pull 2; DoCA/CEDA; microdata; SPF. ‖ W3: audit tranche 1 drawn from Stage A by D15's seeded strata; Mode A fetching and LLM coding start. ‖ W5: GCAM background download if go; DOC series if passed (keyword IPI, outlet theme series, E3 item queries, cached), else Trends item series. ‖ W7: estimation code on simulated data | Chunk check; ledger estimate vs actual. **Checkpoint:** Stage A finished by end of Day 2 (slip rule below) |
| **3 — Thu 19 Nov** | W1: Stage B starts (one-month chunk first), download. ‖ W4: `edition_patterns.csv` from Stage A (D40), agent-verified, human spot-check; E1 cell counts incl. D28 row 1 and the D28 lead-exposure placebo; D38 coverage. ‖ W2: Trends pull 3; scrape completion. ‖ W3: Mode A fetching and LLM coding continue; Mode B fallback retrieval for failed articles. ‖ W6: data-section draft; comparison sentences for read papers | **Gate 1b (human):** freeze patterns for 2022–26; gates (a), (d) computed (no outcomes). **D38 deadline:** centre-level prices by end of Day 3 |
| **4 — Fri 20 Nov** | W1: Stage B completes; pattern extension to earlier years (mechanical rule, D40); indices (D11–D14), window series then monthly series; D13 exclusions. ‖ W3: audit tranche 2 (pre-2022, from Stage B, 2015–18 oversampled 1.5×) drawn, fetched, LLM-coded; **human coding session 1 (~2.25 h)**. ‖ W4: D42 reliability (b); exposure blocks. ‖ W2: 10% spot-check | Row reconciliation with Q1 (±1%); ledger ≤ 670 GB. Unit tests. Spot-check: 0 mismatches |
| **5 — Sat 21 Nov** | W3: **human coding session 2 (~2.25 h, incl. 40 Hindi)**; κ, precision, recall with CIs; best-F2 choice (D9, D15). ‖ W1/W6: validation (D17–D18): Trends, episodes, placebos. ‖ W4: MDE (c) and tiers (D42). ‖ `analysis_plan.md`: D7 primary rule, bin step and continuous variant; D25 cause-code mapping; D26 round mapping; hypotheses (D31) | **Gate 2 (human, end of Day 5):** accept the index, freeze the plan, E1 tier fixed. Outcomes merged with news data only after this gate |
| **6 — Sun 22 Nov** | Phase 1 (D19–D23, incl. D20 regime and D21 VAR). ‖ W7: second-agent reproduction of Phase 1 from scratch starts. ‖ Extension MVs in parallel: E5 (D24), E4 (D25), E1 (D27–D28; block-level RI) and E3 (D26) start. ‖ W5: GCAM subsample into D12 if go. ‖ W6: data and validation sections | Unit tests on each estimation script |
| **7 — Mon 23 Nov** | E1 MV and E3 MV finish; E2 MV (D29; needs E1 tier and the recall gate); E1(b) if microdata. ‖ FVs start: E5 episode study; E4 English/vernacular split. ‖ W6: results sections. ‖ Common incremental-content summary table (Holm, Clark–West vs D22) | **Second-agent reproduction of Phase 1 complete. All five MVs done by end of Day 7** |
| **8 — Tue 24 Nov** | Remaining FVs in parallel: E1 (geocoded exposure from D6 subsample; occupation/education interactions), E2 (per-language series), E3 (direction coding, if DOC passed), E4, E5. ‖ SPF secondary outcome; D41 coverage table. ‖ W6: full draft; every number traced to an output. ‖ Verification re-run starts | Numbers traced to outputs |
| **9 — Wed 25 Nov** | Verification re-run completes; human review; fixes; submission | **Gate 3** |

‖ = parallel.

- **Gate 1a ordering rule (fix):** the Q1 probe and the Gate 1a outlet freeze finish before Stage A starts, because a wrong source list cannot be repaired without a rescan.
- **Human time:** hour 1 of Day 1 (Gate 0a); Gate 0b and Gate 1a on Day 1; Gate 1b spot-check on Day 3; human coding about 4.5 h over Days 4–5 (Fri 20 and Sat 21 Nov), as approved; Gate 2 on Day 5; review and Gate 3 on Day 9.
- **Slip rule (checkpoints kept, adjustments need user approval):** if Stage A has not finished by end of Day 2, the pre-declared adjustment is that E1 becomes descriptive and the rung moves one step down; if not finished by end of Day 3, the rung is L4. Under the user's 17 Nov ruling (no downgrades for the deadline), the agent escalates at each checkpoint with the blocker and this adjustment, and applies it only if the user approves.
- **Rationale:** R: v2 froze edition patterns before the data that build them existed. C: Stage A must not start before the outlet freeze. The 25 Nov deadline leaves 9 calendar days; the 14-day plan is compressed by running independent workstreams at the same time, writing estimation code before Gate 2 on simulated data, splitting the audit draw into a Stage A tranche and a Stage B tranche under the same seeded D15 rules, running the five extension MVs in parallel instead of in sequence, and removing the 2–3 day buffer.
- **Alternatives:** The 14-day plan (misses the deadline). Cutting scope to fit (rejected by the user). C's "straight to L4 at end of day 2" (a few hours' delay would cost most of the monthly sample).
- **Risks created by the compression (stated honestly):**
  1. **No buffer.** The 14-day plan had 2–3 buffer days; this one has none. Any blocker of more than a few hours on the critical path (Gate 1a → Stage A → Stage B → indices → Gate 2 → Phase 1 → MVs → Gate 3) moves the deadline or forces a cut (D35).
  2. **Day 1 is heavier than before:** about twelve tasks, now including Q1 and Gate 1a, plus two human gates. Because Stage A waits for Gate 1a, a late freeze delays Stage A directly.
  3. **Weekend gates.** Human coding session 2 and Gate 2 fall on Sat 21 Nov. If the human is not available, Gate 2 moves to Day 6 or Day 7, and Phase 1 plus all five MVs must fit into Days 7–8.
  4. **Audit timing.** κ is known only at the end of Day 5. If κ < 0.7, human codes replace LLM codes (D15) and the best-F2 switch (D9) is decided the same day, immediately before Gate 2. The κ and cause-code results also feed the E4 gate (D25).
  5. **BigQuery download speed.** Stage B and its download must finish on Day 4. D4 notes that large downloads are slow and the download method is [UNVERIFIED] until the first chunk.
  6. **Bandwidth contention.** Mode A fetches, Mode B minute files and any GCAM raw download overlap on Days 2–5.
  7. **Parallel analysis.** Second-agent reproduction (Days 6–7) runs alongside the extensions; an error it finds forces reruns of extensions built on Phase 1. E2's MV depends on E1's tier and the recall gate, so it cannot start before Day 7.
  8. **Writing and verification compressed.** Writing runs alongside analysis from Day 3; the verification re-run and human review fall on Days 8–9, with Gate 3 on the deadline day.
  9. **Concurrency.** The plan assumes 5–7 agent workstreams running at once and agent work on Sat–Sun.
- **Cost:** 9 calendar days (7 weekdays and one weekend), no buffer.

### D35. Cut lines and schedule risk [merged] (v3 note; time-based cut order replaced 17 Nov 2026)
- **Never cut:**
  - Phase 1: index (article share), audit (whichever mode), Trends check, D19 primary cell, D22 prediction;
  - each extension's MV at its smallest form: one table + one figure.
- **Data-gated rules (pre-declared validation gates, not deadline cuts):**
  - ladder rung from D4; Stage A slip-rule checkpoints from D34 (adjustment applied only with user approval);
  - DOC fail → keyword IPI, E3 direction FV and the DOC stratum are cut;
  - GCAM no-go → V2Tone only;
  - any E1 gate (a)–(d) fails → E1 descriptive; headline = D22 prediction + coverage audit;
  - centre-level prices not obtained by end of Day 3 (19 Nov) → gate (d) fails;
  - vernacular recall gate fails or is not estimable → E2 measurement-only;
  - E4 κ gate (D25) fails → descriptive;
  - microdata unavailable → city-level only.
- **Schedule risk (replaces the time-based cut order; nothing is cut without the user's approval):**
  - **Escalation checkpoints:** Gate 1a not closed by the morning of Day 2; Stage A not finished by end of Day 2; Stage B reconciliation not done by end of Day 4; Gate 2 not closed by end of Day 5; Phase 1 not reproduced, or the five MVs not done, by end of Day 7. At any of these, the agent reports the blocker, the expected delay and the options: (a) let the affected items slip past 25 Nov as stated follow-ups, (b) cut them, or (c) move the deadline. The user decides.
  - **What would slip first if a blocker occurs** (the parts scheduled last and least tied to the primary claim): GCAM subsample analysis → VAR appendix (D21) → E2-FV → E3-FV → E1-FV → E4-FV → E5-FV → SPF. Each is a proposal requiring the user's approval before it is cut.
  - If the five MVs themselves are at risk, the proposal is to protect E1-MV over E5-MV (flagged against the user's ordering: E1 carries the cross-sectional variation). This also requires the user's approval.
- **Rationale / Alternatives / Risk / Cost:** data-gated rules are fixed in advance so they are not chosen after seeing results; deadline cuts are not pre-authorised, because the user asked for full scope with no downgrades. Risk: several gates fail together, in which case the paper is Phase 1 plus five descriptive sections; or a blocker forces a user decision late in the week. No cost.

### D36. Reproducibility and agent rules [blind] (v3 note)
- **Choice:** One repository; every table and figure produced by a script from raw downloads; seeds fixed; `config.yaml` holds the rung, window length, panel and theme list. No BigQuery job without a ledger check, a dry run and `maximum_bytes_billed`. The ledger records estimate and actual per job. A second agent reproduces Phase 1 from scratch.
- **Rationale:** The work is done by agents with a human at the gates.
- **Alternatives:** Notebooks (not reproducible enough).
- **Risk:** None material.
- **Cost:** Built in.

### D37. Budget scenarios [merged] (v3)

Full-pass Q2 (all days, full set) is assumed to cost F. Share of window days: about 50% (30-day windows, bimonthly), 35% (21-day), 23% (14-day). Reduced/full ratio: 0.65 is a **placeholder**, replaced by the measured ratio at Gate 0b.

| Scenario | F | Likely rung | Est. Q2 | + Q1/probe/tests | Total |
|---|---|---|---|---|---|
| Low | 0.8 TB | L1 | 0.40 + 0.13 ≈ 0.53 TB | 0.02 | ~0.55 TB |
| Mid | 1.2 TB | L2 | 0.42 + 0.17 ≈ 0.59 TB | 0.02 | ~0.61 TB |
| Mid, ratio 0.8 | 1.2 TB | L2 | 0.42 + 0.21 ≈ 0.63 TB | 0.02 | ~0.65 TB |
| High | 1.6 TB | L3 | 0.37 + 0.20 ≈ 0.57 TB (from 2016) | 0.02 | ~0.59 TB |
| Extreme | > 2.2 TB | L4 or escalation | ≤ 0.65 TB or raw route | 0.02 | ≤ 0.67 TB |

- **Choice:** These numbers only set expectations; the rung is chosen from exact dry runs.
- **Rationale:** Shows the ladder holds across a wide range of table sizes.
- **Alternatives:** None.
- **Risk (top feasibility risks):** (1) Themes bytes; (2) no refill of the 1 TB before the deadline, so a wasted job cannot be recovered; (3) the 10 GiB storage quota, not refunded on deletion; (4) DOC API depth; (5) DBIE microdata access; (6) centre-level DoCA prices; (7) raw-file bandwidth.
- **Cost:** As tabulated.

---

## G. Decisions added in v2

### D38. City-level real-time price controls [merged; from C] (v3)
- **Choice:** Department of Consumer Affairs daily retail prices of 22 essential commodities by reporting centre.
  - **Source order:** (1) the CEDA (Ashoka) cleaned mirror: daily, about 180 centres, from 2009; centre-level until Aug 2023, state-level aggregates after [V-R]. (2) The DoCA site for centre-level data after Aug 2023 [UNVERIFIED that per-date reports can be scraped in time].
  - Map each IESH city to its centre. Compute the window-average log change of a fixed food basket (equal-weighted and CPI-weighted).
  - **Deadline:** end of day 3. This feeds **gate (d)** in D42. If centre-level data stop at Aug 2023, the E1 sample ends there.
  - Pump prices for IESH cities (oil-company or PPAC archives [UNVERIFIED]) are an optional control, not part of the gate.
  - For D19, national averages suffice and are available throughout.
  - The v2 fallback for E1 (state CPI food) is removed.
- **Rationale:** This control separates "news" from "prices households see". Replacing it with state CPI would restore the confound it was added to remove (C).
- **Alternatives:** State CPI food (lagged, published late, not city-level).
- **Risk:** Centre coverage of all IESH cities is unconfirmed; the basket omits rents and services.
- **Cost:** About 1 agent-day.

### D39. IESH unit-level microdata [merged; from C]
- **Choice:** Download from DBIE "Unit-level Data" [V-C that releases point there; UNVERIFIED: scripted download, city identifier, latest rounds]. Variables: round, city, perception, 3-month, 1-year, demographics. Used in D27(b) and D29. **Fallback:** published city-level statistics.
- **Rationale:** Respondent-level variation and demographic splits at low cost.
- **Alternatives:** City tables only (the fallback).
- **Risk:** Access may need registration or lack city IDs.
- **Cost:** About 0.5 day, if accessible.

### D40. Edition-path mapping table [merged; from C] (v3)
- **Choice:** `edition_patterns.csv` = (outlet_key, regex on URL path, IESH city or state, granularity, valid years). Built from the 200 most frequent URL path prefixes per outlet in Stage A output, verified by an agent and spot-checked by a human; frozen for 2022–26 at **Gate 1b** (day 3). On day 4 it is extended to earlier years from Stage B output by a mechanical rule: per outlet-year, keep the pattern if its match rate is at least half the outlet's 2022–26 rate; otherwise that outlet-year is dropped. No outcome data are involved. Coverage is reported per city and year.
- **Rationale:** Sites redesign their URLs; a pattern checked on 2022+ may fail or mis-match earlier (C).
- **Alternatives:** Hand-built patterns per year (too slow).
- **Risk:** Early years may drop out for many outlets; E1 then covers a shorter period, which is reported.
- **Cost:** About 1 agent-day (days 3–4).

### D41. Sample-coverage table [merged; from C]
- **Choice:** One table listing, for each result, its source and sample: GKG rung and dates; IESH rounds; CPI to Dec 2025 for subgroups; E1 years and cities; DOC from 2017 if passed; NGrams 2020+; GCAM subsample.
- **Rationale:** The paper uses many sub-samples.
- **Alternatives:** Notes under each table (kept as well).
- **Risk:** None.
- **Cost:** Trivial.

### D42. E1 pre-outcome gates [merged; from R and C] (v3)
- **Choice:** Computed before IESH outcomes are merged, per year; E1 uses only passing years.
  - **(a) Cell counts:** at least 12 IESH cities with a median of ≥ 100 local articles and **≥ 30** inflation-flagged local articles per window. (≥ 10 flagged suffices for inclusion in descriptive maps only.) Cell counts are also reported for the D28 lead-exposure placebo (next round's pre-fieldwork window).
  - **(b) Reliability:** split each city-window's articles into odd and even days, compute `IPI^{loc}` on each half, residualise on city and round effects; the split-half correlation must be ≥ 0.5. The Spearman–Brown reliability is reported.
  - **(c) MDE:** minimum detectable β at 80% power, from the IESH city standard errors, the number of exposure blocks and the reliability in (b) (attenuation-adjusted). Always reported next to a plausible effect of 0.1–0.2 survey points per SD.
  - **(d) Price coverage (D38):** at least 12 IESH cities with centre-level prices in ≥ 80% of windows of the E1 sample.
  - **Exposure blocks:** cities whose local articles come mostly from the same outlet-state pages form one block. Fixed before outcomes are merged.
  - **Tiers:**
    - (a), (b), (d) pass and MDE ≤ 0.3 → E1 is inferential and H5 is primary;
    - (a), (b), (d) pass and 0.3 < MDE ≤ 0.5 → estimates and RI p-values are reported, E1 is not a headline, and the text states which effect sizes cannot be ruled out;
    - otherwise → descriptive.
  - The city list, years, blocks and tier are frozen at Gate 2.
- **Rationale:** R: the v2 variance gate rewarded noise, since sampling error raises within-city variance. C: an MDE of 0.5 is far above plausible effects, so a pass could still be uninformative; and price coverage must be a gate, not a fallback.
- **Alternatives:** A single 0.5 threshold (v2). A single 0.3 threshold (would hide estimates that are still worth showing with a caveat).
- **Risk:** The likeliest outcome is the middle or bottom tier. The paper is designed to stand without E1 as a headline (D33).
- **Cost:** Half a day.

---

## Changes from agreed_design

Eight accepted fixes (user ruling, 17 Nov 2026):
1. **D2:** Stage A/B source list seeded from the hand-keyed top-20 outlets and GDELT's domain-to-country lookup file, then `.in` domains and Q1 Indian-language hits added; list printed at Gate 1a.
2. **D7:** bin step of the median primary recorded in the plan; continuous variant row added (share expecting ≥ 10%, or published distribution mean); both declared before Gate 2.
3. **D16:** Mode A approved and made the default with fetch outcomes logged; Mode B NGrams text comes from minute files around each article's timestamp (BigQuery `webngrams` only if a one-day dry run ≤ 60 GB), on a seeded k-day cluster capped at one day of download, with day-clustered CIs, a budget-ledger line and text marked approximate.
4. **D19:** lagged expectation level `y_{r−1}` added to the primary specification; ΔIPI variant kept.
5. **D25:** E4 gate defined as Cohen's κ (international flag vs "international/imported" cause code, flagged audit stratum), pass at κ ≥ 0.6 with D15 cause-code κ ≥ 0.6; CI and count reported; mapping fixed at Gate 2.
6. **D27:** primary RI permutes at exposure-block level (block × round), smallest attainable p-value reported, city-level permutation kept as secondary; weights changed to inverse squared published SE (microdata counts only if D39 succeeds).
7. **D28:** key placebo redefined as lead exposure from the next round's pre-fieldwork window, with its overlap with days +21 to +50 stated; wording rule changed to match; its cell counts added to the D42 check (one sentence added to D42(a)).
8. **D34:** rule added that the Q1 probe and the Gate 1a outlet freeze finish before Stage A starts.

Required edits beyond the eight fixes (user instruction, 17 Nov 2026):
- **D34:** 14-day table replaced by a 9-day plan (Day 1 = 17 Nov, Day 9 = 25 Nov) with seven parallel workstreams; every component and gate kept; human coding on Days 4–5; slip-rule adjustments now need user approval; schedule risks listed.
- **D35:** data-gated rules kept; time-based cut order and the day-8 trigger replaced by a schedule-risk note (escalation checkpoints and the order in which items would slip), with any cut requiring user approval; E4 rule reworded to the D25 κ gate.
- **Consequential wording:** D21's cost line now points to D35's schedule-risk note instead of the removed cut list; OPEN markers removed from all eight headings; header records the user's rulings.
