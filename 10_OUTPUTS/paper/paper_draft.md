# News attention to inflation and household inflation expectations in India: an audited GDELT index

DRAFT, 23 Nov 2026. Every number below is read from a pipeline output file (named in brackets). Sections marked
**[PENDING]** wait for the audit (D15/D16) and the D9/D17 switch chain. No result is stated in causal language.

## Abstract
[PENDING: written last, after the audit and the D9/D17 switch chain.]

## 1. Introduction
Households' inflation expectations matter for monetary policy, and the RBI's Inflation Expectations Survey of Households
(IESH) is the main measure of them in India. The survey records what households expect but not what they read. The
RBI's own July 2025 Bulletin article on the IESH notes that it "does not capture information on households' ...
exposure to media and social interactions related to policy or inflation dynamics" (Ruhi, Sharma & Sankaran 2025,
fn. 26). This paper builds an open, reproducible news-attention-to-inflation index for India from GDELT, covering
English and vernacular outlets. It audits how well GDELT's theme tags identify inflation coverage, and asks whether
the index predicts the IESH 1-year expectation of urban households beyond real-time prices.

Contributions (as pre-specified, D33): (1) an audited, reproducible index with a coverage audit of GDELT for the
Indian press; (2) a pre-registered test of its predictive content for household expectations; (3) descriptive
extensions (attention cycle, international framing, salience-weighted inflation, English vs vernacular, city
exposure). Not claimed: a first Indian news-inflation index, causal effects, rural results.

## 2. Related work
Indian news-based inflation measures use a few English business or national dailies and dictionary or rule-based
sentiment, with CPI or professional forecasters as the outcome:
- Kishor & Pratap (MPRA 118951, 2023): five English business dailies, Loughran–McDonald sentiment, professional
  forecasters' expectations.
- Pratap, Ranjan, Kishore & Bhoi (RBI Occasional Papers 42(2)): vegetable-price sentiment from nine English
  dailies, used to forecast CPI.
- Banerjee, Kanodia & Ray (IIM Calcutta WPS 830, 2019): text-mined CPI baskets predicting CPI, with the IESH as a
  benchmark forecaster, not as the outcome.

Internationally:
- Aarab et al. (ECB Economic Bulletin 6/2025): news attention to inflation tracks consumers' perceptions and stays
  high after inflation falls.
- Arndt (2024; 2026 WP): tabloid vs reputable newspapers predict expectations of different household groups.
- Heddaya et al. (2025): a century of US inflation narratives.

None of the Indian papers uses vernacular press, GDELT, or the IESH as the dependent variable. [docs/literature_check.md]

## 3. Data
### 3.1 News: GDELT GKG 2.0
- **Source:** `gdelt-bq.gdeltv2.gkg_partitioned`.
- **Sampling (rung L3, pre-registered ladder):**
  - 14-day windows ending the day before each IESH round's fieldwork, read with the full column set;
  - a 1-in-4 systematic grid of other days from 2016-01-01 to 2026-10-31 (reduced column set);
  - always-sampled placebo dates.
- **Extraction:** 216 capped BigQuery chunks, about 473 GB in total, inside a pre-set 670 GB cap. An independent
  recount on 147 days matched the extracted counts exactly (0 mismatches on 53,335 source×day×language keys).
  [logs/budget_ledger.csv; data/processed/checks/d34_reconcile.json]
- **Outlet panel:** 714 of 936 candidate domains, about 70% of articles. Filter: GDELT's domain-country file plus a
  documented hand review of 81 ambiguous domains; foreign outlets made up 29% of the raw superset. Language codes
  come from GDELT's machine-translation metadata. [data/processed/index/panel_outlets.csv; scripts/build/panel_review.csv]
- **Gap:** GDELT has no GKG partitions for 16 Jun – 1 Jul 2025, so the 2025-07 round is excluded.

### 3.2 Outcomes and controls
- **IESH:** national 1-year, 3-month and current-perception medians and means (RBI); 67 rounds since 2015; 63 rounds in
  the analysis sample (2016-03 to 2026-09). Pre-2020 rounds without exact dates use the month rule (fieldwork start =
  1st of the survey month), flagged and checked in an exact-date-only row. Responses are binned in 1-pp steps.
- **CPI:** base 2012 all-India and item level, to Dec 2025.
- **Policy repo rate:** 74 RBI decisions 2015–2026, read from RBI press releases.
- **Markets:** Brent.
- **Google Trends:** India, monthly; three pulls on 23–25 Nov 2026, averaged (D7).
- **GDELT DOC 2.0** series: from 2017.

## 4. The index
- **Primary window index:** the share of ECON_INFLATION-tagged articles among all articles, per outlet (URL host,
  day-level deduplicated), averaged with equal weights over a balanced core of 104 outlets present in ≥ 80% of
  windows.
- **Validity rules (D13):** a day is invalid if its global or panel volume falls below a set share of its 28-day
  median; 9 of 1,654 sampled days are invalid. A window needs ≥ 60% valid days; 62 of 63 windows pass.
- **Language mix:** the core includes 54 vernacular outlets from 2016, so the index is not English-only in early years.
- **Reliability:** split-half (odd vs even days) r = 0.89 (Spearman–Brown 0.94).
- **Duplicates and wire copy:** cross-day duplicate rate 0.3%; wire copies 3.6% of inflation articles.
- **Level:** the mean window index is 1.14% of articles (SD 0.52 pp), ranging from 0.36% (2021-05) to 2.16% (2022-09).
- **Robustness definitions (D11) and correlation with the primary:**

  | Definition | Correlation with primary |
  |---|---|
  | Word share | 0.93 |
  | Pooled ratio | 0.94 |
  | Share among ECON articles | 0.96 |
  | Wire-copy filter | 1.00 |
  | Strict flag | 1.00 |
  | Price family | 0.72 |
  | 2018 core incl. vernacular | 0.99 |

  The strict flag is not an independent check, because GDELT tags WB_442_INFLATION alongside ECON_INFLATION
  almost every time.
- **Monthly series:** source × language, grid days only; 129 usable months.

[data/processed/index/build_report.md]

## 5. Measurement validation
### 5.1 Audit (D15/D16)
- **Sample:** 1,250 articles from window days, stratified:
  - flagged 300;
  - ECON-unflagged 300;
  - non-ECON with a price word in the URL 150; non-ECON without 100;
  - Hindi and Marathi, flagged and ECON-unflagged, 100 each;
  - 2015–18 oversampled 1.5×.
- **Non-ECON strata:** drawn from a 19-day pull. Their weights are scaled up to all window days, and their intervals
  are day-clustered.
- **Texts:** fetched live, with Wayback as fallback; URL-slug coding is used where neither works.
- **Coding:** two independent LLM passes (Claude Opus, in-session) under a frozen codebook (SHA-256 ce3f7deb…).
  **There is no human validation;** LLM–LLM agreement is reported as reliability only.
- **Results:** [PENDING: retrieval rate per stratum; κ; precision; gating recall; best-F2 variant.]

### 5.2 External validation (D17)
- **Trends:** "inflation" searches correlate with the monthly index at r = 0.78 (≥ 0.5 required). The partial
  correlation after removing CPI y/y and food y/y is 0.78 (95% block-bootstrap CI 0.65–0.90). Hindi terms are weak
  (0.26, 0.30). [results/d17_summary.md; provisional until 3 pulls]
- **Episodes:** only 1 of 4 pre-specified episodes peaks above the 90th percentile of non-episode months (post-Ukraine
  2022, z = 2.5). Onion 2019, fuel 2021 and tomato 2023 do not, so the ≥ 3-of-4 rule fails. The index level is
  much higher from 2022, which sets the threshold.
- **Placebos:** 1 of 3 placebo windows (the 2024 election results) shows a peak.
- **Pre-registered consequence:** switch to the best-F2 variant, then the strict flag. If every variant fails, the
  index is "audited, not externally validated" and H1/H5 are exploratory. [PENDING: outcome of the switch chain.]

## 6. Econometric design (frozen plan, docs/analysis_plan.md)
- **H1 specification (D19):** round-level local projection of the change in the 1-year median expectation on the
  standardised window index, controlling for:
  - the lagged level and change of the expectation;
  - real-time CPI y/y and food CPI y/y;
  - the repo-rate change;
  - a telephone-survey dummy.
- **Inference:** EWC fixed-b plus wild bootstrap.
- **D22:** recursive pseudo-real-time prediction against AR(1) and AR(1)+CPI+food benchmarks (Clark–West).
- **Order change:** the plan was frozen before any outcome regression. Phase 1 was run before the audit to meet the
  deadline; a flag switch would trigger a pre-declared re-run.

## 7. Results
### 7.1 Phase 1 (baseline flag)
[PENDING final status after the switch chain. Baseline-flag results, from results/d19_national_lp.csv:]
- **Primary cell:** β = 0.33 survey points per SD of the index (N = 56), 95% CI [0.015, 0.641], wild-bootstrap
  p = 0.036, partial R² 0.14.
- **The word-share row's interval includes zero** (0.26 [−0.01, 0.54]), so under D18 the result is stated with
  qualification.
- **The estimate is fragile:**
  - lagged expectations + CPI only: 0.09;
  - dropping 2020–21: 0.30 [−0.09, 0.68];
  - ΔIPI version: 0.15;
  - future-CPI test: 0.30 [−0.06, 0.66];
  - horizons h = 1–3: intervals include 0.
- **Regime (D20):** no difference detected (IPI × High 0.12 [−0.16, 0.40]).
- **D22:** no gain over the AR(1)+CPI+food benchmark (RMSE ratio 1.03; Clark–West p = 0.68). "Out-of-sample" is
  therefore not claimed.

### 7.2 Extensions (descriptive; gates noted)
- **E5 attention cycle:** three attention peaks (2022-06, half-life 9 months; 2025-03; 2026-04). ExcessAttention in
  the D19 specification: 0.26 [−0.16, 0.68]. Asymmetric monthly local projections are in results/e5_asym_lp.csv.
- **E4 international framing:** the share of inflation articles co-occurring with international themes is
  uncorrelated with the index (r = 0.01) and adds nothing alongside it (0.00 [−0.21, 0.21]). [Gate: audit κ, PENDING]
- **E3 salience basket:** the search-implied version (Trends) shows no clear association in the horse race. [DOC
  media-implied version and precision check PENDING]
- **E2 English vs vernacular:** monthly correlation 0.91, peaking at lag 0. In the D19 specification each version
  alone is about 0.26; the vernacular index controlling for English is 0.21 [−0.05, 0.46]. The national comparison has
  almost no power. [Recall gate PENDING]
- **E1 city panel:** descriptive only. Local articles are assigned to 19 IESH cities by the outlet edition-path
  rule (D40).
  - **Gate D42(a) fails in every year.** The median number of flagged local articles per fieldwork window is 0–8.
  - **Thresholds:** 10 of 209 city-years meet the descriptive threshold (Mumbai, Delhi, Chandigarh); none meet the
    inferential one.
  - **Flagged shares** of local articles are 0.1–0.9%.
  - **No city-level estimate is reported.** [results/e1_summary.md, e1_exposure_table.csv]

## 8. Limitations
- No human validation of the audit coding.
- LLM coding was done in-session by one model in two passes, which limits the coders' independence.
- Monthly series come from a 1-in-4 day grid.
- Pre-2020 IESH dates use the month rule.
- The GDELT gap in June 2025.
- There is no published media-exposure measure in the IESH.
- Urban households only.

## 9. Reproducibility
All steps run from scripts in 09_ANALYSIS/pipeline/scripts. Rulings are in docs/design/ledger.md; the step log is
PROGRESS.md. [PENDING: scripted rerun check, Gate 3.]
