---
title: "News attention to inflation in India: an open GDELT index, an LLM audit, and suggestive links to household expectations"
date: "24 November 2026 (draft for review)"
---

## Abstract

We build an open, reproducible index of news attention to inflation for India from the GDELT Global Knowledge Graph,
covering 104 English and vernacular outlets from 2016 to 2026, and measure it in the two weeks before each round of the
Reserve Bank of India's Inflation Expectations Survey of Households (IESH). The index is reliable (split-half
r = 0.89) and tracks Google searches for "inflation" (r = 0.54 to 0.78 across theme definitions), but it does not
peak in three of four pre-specified price episodes, and an audit of 1,250 sampled articles, coded twice by a large
language model with no human validation, finds that GDELT's inflation theme tags have low precision (0.16) and low
recall (0.30). Following a rule fixed before the audit, we switch to a broader "price family" definition and label
the index "audited, not externally validated". In 56 rounds, one standard deviation more attention is associated with
a 0.25 percentage-point higher change in the median one-year expectation, after real-time CPI and food inflation,
the repo rate and survey mode (95% CI 0.07 to 0.43; wild-bootstrap p = 0.058). The estimate depends on the control
set and the outcome, and the index adds nothing to a CPI-based forecast out of sample. Monthly attention rises after
oil-price increases but not after CPI surprises. We read the evidence on expectations as suggestive and non-causal.
The contribution is the measurement: an open pipeline, an audit of GDELT for the Indian press, and a documented set
of its limits.

## 1. Introduction

Household inflation expectations matter for monetary policy. They enter wage and price setting, they shape the
credibility of an inflation target, and in India they have run well above both realised inflation and professional
forecasts for most of the inflation-targeting period. The Reserve Bank of India's Inflation Expectations Survey of
Households (IESH) is the main measure of them. The survey records what households expect but not what they read: the
RBI's own discussion of the survey notes that it does not capture households' exposure to media and social
interactions (Ruhi, Sharma and Sankaran 2025). News is one channel through which households may learn about prices,
and it is the channel this paper tries to measure.

The idea that households learn about inflation from the news has a long history. Carroll (2003) models household
expectations as updating slowly toward the views of professional forecasters as reported in the news, and finds that
more news coverage speeds up that updating. Lamla and Lein (2014) show that both the volume and the tone of inflation
news move German consumers' perceptions and expectations. Larsen, Thorsrud and Zhulanova (2021) extract news topics
from a large newspaper corpus and find that they predict US household expectations, and that the degree of
information rigidity varies with the news. Recent work at the ECB documents that news attention to inflation tracks
consumers' perceived inflation and stays high after inflation falls (Aarab et al. 2025), and Arndt (2024) finds that
different kinds of newspaper predict the expectations of different household groups.

For India, existing news-based measures use a handful of English business dailies with dictionary-based sentiment and
target CPI or professional forecasts rather than household expectations (Kishor and Pratap 2023; Pratap et al.;
Banerjee, Kanodia and Ray 2019). None uses vernacular outlets, which carry most of India's news readership, and none
uses the IESH as the outcome. GDELT, which machine-codes themes for online news in many languages, offers a way to
cover both, but its theme tags are rarely checked against article text for non-US press.

This paper makes three contributions, in decreasing order of weight.

1. **Measurement.** An open, scripted index of news attention to inflation for India, built from GDELT, covering
   English and nine Indian languages, with every step reproducible from public data and a fixed set of design rules.
2. **An audit of the measurement.** We sample 1,250 articles across eight strata, retrieve their text, and code them
   under a fixed codebook to estimate the precision and recall of GDELT's inflation tags, by language and by the
   way the text was retrieved.
3. **Suggestive evidence on expectations.** We ask whether attention in the two weeks before an IESH round is
   associated with the change in households' one-year expectation beyond real-time prices, and whether it improves
   out-of-sample forecasts.

The design, the primary outcome and specification, the validation tests and a rule for switching the index definition
were fixed in an analysis plan before any outcome regression was run. The audit was completed after the first
regressions, and Section 7 reports how that order affects interpretation.

The headline is mixed and we report it as such. The index is reliable and tracks search interest. But the inflation
tag is imprecise, the index fails the pre-specified episode test, and the association with expectations is small,
sensitive to the control set and absent out of sample. We therefore present the index as a measurement with
documented limits, not as a validated predictor.

## 2. Related literature

**News and household expectations.** Carroll (2003) is the starting point: households absorb professional views
through the news with a lag. Lamla and Lein (2014) use German media data and find that more inflation news and more
negative tone raise perceived and expected inflation. Larsen, Thorsrud and Zhulanova (2021) use topic models on a
newspaper corpus and show that news topics predict US household expectations and help explain information rigidity.
Aarab et al. (2025) document for the euro area that inflation attention tracks perceptions and is persistent. Arndt
(2024) shows that tabloid and reputable newspapers predict the expectations of different groups.

**India.** Kishor and Pratap (2023) build a sentiment index from five English business dailies and relate it to
professional forecasters' expectations. Pratap et al. use vegetable-price sentiment from English dailies to forecast
CPI. Banerjee, Kanodia and Ray (2019) mine text for CPI baskets and use the IESH as a benchmark forecaster rather than
as the outcome. Our contribution relative to this work is the coverage (vernacular outlets and an open global
database), the audit, and the use of the household survey as the outcome.

**GDELT.** GDELT (Leetaru and Schrodt 2013) is widely used in political science and increasingly in economics. Its
themes come from dictionaries and machine translation, and their accuracy for specific economic concepts outside the
US and Western Europe is largely undocumented. Our audit adds evidence on that question for one concept and one
country.

## 3. Data

### 3.1 News: GDELT Global Knowledge Graph

GDELT GKG 2.0 records, for each online news article it ingests, the outlet, date, language and a set of themes
assigned by dictionary matching (after machine translation for non-English text). We read two kinds of days.

* **Windows.** The 14 days ending the day before each IESH round's fieldwork begins. These are read with the full
  set of fields and give the round-level index.
* **Grid.** A systematic one-in-four sample of all other days from January 2016 to October 2026, read with fewer
  fields, giving a monthly series for validation and for the extensions.

The extraction ran in capped BigQuery chunks under a fixed budget. An independent recount of 147 days reproduced the
extracted counts exactly (no mismatches on 53,335 source-by-day-by-language cells). GDELT has no data for
16 June to 1 July 2025, so the July 2025 round is dropped.

**Outlets.** We keep Indian domains, identified from GDELT's domain-country file plus a documented review of 81
ambiguous domains; foreign outlets made up 29% of raw volume and are excluded. Of 936 candidate domains, 714 remain,
covering about 70% of articles. The index uses a balanced core of 104 outlets present in at least 80% of windows
(Table 1).

**Table 1. Language of the 104 core outlets**

| Language | Outlets |
|---|---|
| English | 50 |
| Hindi | 23 |
| Tamil | 9 |
| Malayalam | 6 |
| Telugu | 4 |
| Marathi, Punjabi, Kannada | 3 each |
| Gujarati | 2 |
| Bengali | 1 |

### 3.2 Household expectations

The IESH, run by the RBI in large cities, reports national medians and means of households' current perceived
inflation and their three-month-ahead and one-year-ahead expectations. We use rounds from March 2016 to September
2026. Responses are recorded in 1-percentage-point bins, so the median moves in discrete steps, which matters for
interpreting magnitudes (Section 6). Before 2020 exact fieldwork dates are not always published; we date those rounds
to the first of the survey month and check that choice with an exact-date-only sample. The 2020–21 rounds were run by
telephone.

### 3.3 Prices, policy and search

CPI (base 2012) headline and food inflation are taken in real time: the latest release available before fieldwork
begins. The policy repo rate comes from 74 RBI decisions collected from press releases. Brent crude prices enter the
monthly analysis. Google Trends gives monthly search interest in India for "inflation", "mehngai" and its Devanagari
spelling. Trends rescales every request, and our plan averages three pulls on different days; at the time of writing
one pull is available, so every Trends number is provisional. GDELT's separate DOC 2.0 interface gives keyword-based
article counts used as a cross-check.

### 3.4 Sample flow

Table 2 traces the estimation sample. The out-of-sample exercise starts after 20 rounds and evaluates 37 forecasts.

**Table 2. Sample flow**

| Step | Rounds |
|---|---|
| IESH rounds since 2015 | 67 |
| Inside the news window file (March 2016 onward, gap excluded) | 63 |
| With a valid news window | 62 |
| With the lagged level and change of the expectation | 61 |
| With real-time CPI on the 2012 base | 57 |
| With every control (estimation sample) | 56 |

## 4. The index

For each outlet and window we compute the share of distinct articles (deduplicated by web address within a day)
carrying an inflation theme among all its articles, and average those shares with equal weights over the core
outlets. Equal weights keep a few high-volume portals from dominating. Days with abnormally low global or panel volume
relative to a 28-day median are dropped (9 of 1,654 sampled days), and a window needs 60% valid days (62 of 63 pass).

**Definitions.** Two definitions matter below, both fixed before the audit.

* The **baseline** flag is GDELT's ECON_INFLATION theme.
* The **price family** adds the World Bank inflation theme and GDELT themes for cost of living, price controls,
  price gouging and manipulation, retail fuel prices, oil, electricity and natural-gas prices, transport costs and
  price subsidies.

A *strict* flag (both inflation themes) and the World Bank theme alone were also pre-specified; in practice GDELT
assigns the World Bank theme alongside ECON_INFLATION almost every time, so these two are nearly identical to the
baseline.

**Scale.** Under the price family the window index averages 2.33% of articles (SD 0.77 percentage points; maximum
4.92%). The baseline index is about half that level (mean 1.14%, SD 0.52 pp; minimum 0.36% in May 2021, maximum 2.16%
in September 2022). The monthly series, built from grid days and pooled by outlet name and language, is on a
different scale (its peak is 0.031 of articles, in June 2022), so window and monthly numbers should not be compared
directly.

**Reliability and robustness.** Indices built separately from odd and even days correlate at 0.89 (Spearman–Brown
0.94). Duplicates across days are 0.3% of articles and wire copies 3.6% of inflation articles. Table 3 shows that
alternative constructions move closely with the baseline; the price family is the only definition that differs
materially.

**Table 3. Correlation of alternative index constructions with the baseline window index**

| Construction | Correlation |
|---|---|
| Word share instead of article share | 0.93 |
| Pooled ratio instead of equal-weight average | 0.94 |
| Share among economic articles only | 0.96 |
| Wire-copy filter | 1.00 |
| Strict flag | 1.00 |
| 2018 core including vernacular outlets | 0.99 |
| Price family | 0.72 |

**Relation to inflation.** The monthly index correlates only modestly with CPI inflation: 0.31 contemporaneously,
falling symmetrically to about 0.1 at six-month leads and lags. Attention is therefore not simply a transform of
measured inflation. Table 4 describes the estimation sample and Figure 1 plots the index against expectations and CPI.

**Table 4. Estimation sample (56 IESH rounds), price-family index**

| Variable | Mean | SD | Min | Max |
|---|---|---|---|---|
| News index, window article share (%) | 2.22 | 0.69 | 0.96 | 4.92 |
| One-year expectation, median (%) | 9.75 | 1.05 | 7.90 | 12.66 |
| One-year expectation, mean (%) | 9.70 | 0.85 | 8.12 | 11.60 |
| Current perceived inflation, median (%) | 8.21 | 1.22 | 6.30 | 10.38 |
| Real-time CPI inflation (%) | 4.75 | 1.64 | 0.71 | 7.59 |
| Real-time food CPI inflation (%) | 4.66 | 3.98 | −3.91 | 13.63 |
| Change in repo rate (pp) | −0.01 | 0.24 | −0.75 | 0.90 |
| Telephone survey (share of rounds) | 0.11 | 0.31 | 0 | 1 |

![Figure 1. News index (window article share, price family) and IESH one-year expectations and real-time CPI inflation, by survey round.](../../09_ANALYSIS/pipeline/data/processed/results_switched/paper_figures/fig_index_expectations.png)

Expectations sit well above CPI inflation throughout, as is familiar for India. The index rises sharply in 2022, when
both CPI and expectations rose, and stays higher afterwards. Unit-root tests support treating the index as stationary
(ADF p < 0.001) but cannot reject a unit root in the median expectation (ADF p = 0.12; KPSS does not reject
stationarity), which is why the specification works with changes in the expectation and controls for its lagged level.

## 5. Validation

### 5.1 Audit of the theme tags

**Sample.** We drew 1,250 articles from window days in eight strata (Table 5): tagged and untagged economic articles in
English, in Hindi and Marathi, and in other vernaculars; non-economic articles whose web address contains a price word;
and other non-economic articles. The years 2015–18 were oversampled because older links are more often dead. Weights
undo the stratification; the non-economic strata were drawn from a 19-day subsample and their weights scaled to all
window days.

**Retrieval.** Texts were retrieved live or, failing that, from the Internet Archive. Of 1,250 articles, 1,113 (89%)
were retrieved, 417 of them from the archive; retrieval ranged from 85% to 95% by stratum. The 137 articles with no
retrievable text were coded from their web address alone and are reported separately (below).

**Table 5. Audit sample and retrieval by stratum**

| Stratum | Sampled | Retrieved | Via archive | Rate |
|---|---|---|---|---|
| English, tagged | 300 | 256 | 104 | 0.85 |
| English, economic, untagged | 300 | 266 | 133 | 0.89 |
| Hindi/Marathi, tagged | 100 | 91 | 23 | 0.91 |
| Hindi/Marathi, economic, untagged | 100 | 90 | 31 | 0.90 |
| Other vernacular, tagged | 100 | 91 | 14 | 0.91 |
| Other vernacular, economic, untagged | 100 | 90 | 19 | 0.90 |
| Non-economic, price word in address | 150 | 142 | 57 | 0.95 |
| Non-economic, other | 100 | 87 | 36 | 0.87 |
| **Total** | **1,250** | **1,113** | **417** | **0.89** |

**Coding.** Each article was coded for relevance (does it substantially discuss price levels, inflation or the cost
of living affecting Indian consumers), direction (rising, falling, mixed, none) and stated cause (domestic food supply,
domestic fuel and energy, global commodities, exchange rate, monetary policy, taxes and administered prices, wages and
demand, inflation abroad, other), under a codebook fixed and hashed before coding. **There was no human coding.** By
the author's ruling, coding was done twice, in separate passes, by the same large language model (Claude), and the
first pass is treated as the truth. The first pass coded all 1,113 retrieved articles; the second coded the 1,026 in
the strata that decide the gates. After the first 613 articles of the first pass and 610 of the second, for time and
cost, the model coded from shorter excerpts (200–300 characters, against 800–1,100 before), which may understate
relevance for long articles.

Agreement between passes was very high: relevance κ = 1.00 (n = 1,026), direction 0.97 and cause 0.94 (n = 118
articles coded relevant by both). Two passes of one model are not independent coders, so this is reliability, not
validation.

**Precision and recall.** Weighted to the sampled population, the baseline tag has precision 0.16 (95% CI 0.13 to
0.20) and recall 0.30 (0.20 to 0.47) in the frame of economic and price-word articles (Table 6). The plan required
precision ≥ 0.5 and recall ≥ 0.6; the tag fails both. In the coding, most tagged articles that were not relevant were
market reports, company results and foreign-economy stories that mention prices in passing. Among the pre-specified
alternatives the price family has the highest F2 (0.29 against 0.26), trading lower precision for higher recall, so
by the plan's rule it becomes the primary definition. No definition comes close to the precision bar.

**Table 6. Precision, recall and F2 of the flag definitions (gating frame, weighted)**

| Group | Definition | Precision | Recall | F2 |
|---|---|---|---|---|
| All languages | Baseline | 0.16 | 0.30 | 0.26 |
| | Price family | 0.13 | 0.42 | 0.29 |
| | Strict / World Bank | 0.16 | 0.29 | 0.25 |
| English | Baseline | 0.14 | 0.29 | 0.24 |
| | Price family | 0.11 | 0.45 | 0.28 |
| Hindi/Marathi | Baseline | 0.24 | 1.00 | 0.61 |
| | Price family | 0.13 | 1.00 | 0.43 |
| Other vernacular | Baseline | 0.31 | 0.62 | 0.52 |
| | Price family | 0.35 | 1.00 | 0.73 |
| Retrieved live | Baseline | 0.16 | 0.37 | 0.29 |
| Retrieved from archive | Baseline | 0.17 | 0.23 | 0.21 |

Two patterns stand out. First, recall is much higher in the vernacular strata (0.88 pooled) than in English (0.33),
and the difference is far outside the plan's tolerance of 0.15. GDELT's translation pipeline appears to tag vernacular
price stories more readily, so comparisons of English and vernacular attention (Appendix A) are measurement results,
not evidence about audiences. Second, recall is lower for archived texts, which are older, consistent with the tag
behaving differently in earlier years.

**Address-only coding.** For the 137 articles without text, coding from the web address alone gives precision 0.13 and
recall 0.56. Only 7% of addresses were uninformative, but address coding is cruder than text coding and is not used in
any gate.

**Causes.** Among articles coded relevant, agreement on whether the stated cause was international was too low
(κ = 0.33) to support claims about international framing (Appendix A, E4).

### 5.2 External validation

The plan required the monthly index (i) to correlate at least 0.5 with Google searches for "inflation", and (ii) to
peak above the 90th percentile of other months in at least three of four price episodes (onion 2019–20, fuel 2021,
the months after the Ukraine invasion in 2022, tomato 2023), with episode months fixed before inspection. It also
required no peak at three placebo dates (election results in 2019 and 2024; the 2023 Cricket World Cup final).
Table 7 reports both definitions.

**Table 7. External validation of the monthly index**

| Check | Baseline | Price family |
|---|---|---|
| Correlation with "inflation" searches | 0.78 | 0.54 |
| … after CPI and food inflation removed (95% CI) | 0.78 (0.65, 0.90) | 0.55 (0.31, 0.75) |
| … after trend and log volume removed | 0.67 | 0.41 |
| Correlation with "mehngai" searches | 0.26 | 0.11 |
| Correlation with Devanagari search term | 0.30 | 0.36 |
| Correlation with GDELT DOC keyword series | – | 0.78 |
| Onion 2019–20 episode (z) | −0.91, no peak | −0.72, no peak |
| Fuel 2021 episode (z) | −0.36, no peak | −0.06, no peak |
| Post-Ukraine 2022 episode (z) | 2.51, peak | 2.11, peak |
| Tomato 2023 episode (z) | no peak | 0.22, no peak |
| Episodes peaking (need ≥ 3 of 4) | 1 | 1 |
| Placebos with a peak (daily index) | 1 of 3 (2024 election) | n/a |

The search correlations pass. The episode test fails for every definition: only 2022 peaks. The level of attention
rose after 2022 and stayed high, which raises the 90th-percentile threshold for the earlier episodes, and the onion,
fuel and tomato episodes were concentrated in a few items, while the index counts all price themes. The plan's rule
was to try the best-F2 definition and then the strict flag, and, if all failed, to label the index "audited, not
externally validated" and treat the expectation tests as exploratory. All failed, and that is the label we use.

Two cautions apply to the correlations that pass. They are correlations of levels of persistent series, which is weak
validation. And the Trends figures rest on one pull; Hindi search terms correlate weakly, which may reflect search
behaviour as much as the index.

## 6. Specification

For round *t* we estimate a local projection:

change in median one-year expectation from round *t−1* to *t+h* = α + β · (standardised window index before round
*t*) + γ₁ · lagged level + γ₂ · lagged change + δ′ · controls + error,

where the controls are real-time CPI and food inflation, the change in the repo rate, and the telephone-survey dummy.
β is the association, in percentage points, of one standard deviation more attention. Inference uses
equal-weighted cosine (EWC) standard errors with fixed-b critical values, which are designed for small samples with
serial correlation, and a wild bootstrap. One cell was designated primary in advance: one-year median, *h* = 0.
Everything else is secondary.

We also report a regime interaction (lagged CPI inflation above 6%), a Bayesian VAR, a recursive pseudo-real-time
forecast comparison with Clark–West tests, and monthly local projections of the index on price shocks.

## 7. Results

### 7.1 Primary estimate

Under the price-family index, one standard deviation more attention (0.77 percentage points of articles) is associated
with a 0.25 percentage-point higher change in the median one-year expectation (95% CI 0.07 to 0.43; wild-bootstrap
p = 0.058; N = 56). Under the baseline tag, which the audit rejected, the same cell is 0.33 (0.015 to 0.64;
p = 0.036).

Because the median is recorded in 1-pp bins, an effect of 0.25 pp is best read as a shift in the probability that the
median moves up a bin, not as a continuous movement. For scale, the change in the median has a standard deviation of
0.72 pp in the estimation sample, so the estimate is about a third of a typical round-to-round move.

### 7.2 Robustness

Table 8 and Figure 2 report the variants.

**Table 8. Coefficient on the news index (pp per SD), one-year median, h = 0 unless stated**

| Specification | N | Price family | Baseline tag |
|---|---|---|---|
| Primary (pre-specified) | 56 | 0.25 [0.07, 0.43] p=0.058 | 0.33 [0.02, 0.64] p=0.036 |
| Lagged expectation + CPI only | 56 | 0.14 [0.05, 0.23] p=0.040 | 0.09 [−0.16, 0.34] |
| Brent added | 56 | 0.24 [0.07, 0.42] p=0.062 | – |
| Drop 2020–21 | 46 | 0.17 [0.01, 0.33] p=0.115 | 0.30 [−0.09, 0.68] |
| Exact fieldwork dates only | 32 | 0.35 [0.13, 0.58] p=0.040 | 0.47 [0.12, 0.83] p=0.105 |
| Next-month CPI added | 55 | 0.23 [0.07, 0.40] p=0.035 | 0.30 [−0.06, 0.66] |
| Change in index instead of level | 55 | 0.12 [−0.06, 0.29] p=0.27 | 0.15 |
| Word-share construction | 56 | 0.26 [−0.01, 0.54] p=0.066 | – |
| Pooled-ratio construction | 56 | 0.33 [0.11, 0.55] p=0.020 | – |
| 2018 core incl. vernacular | 47 | 0.28 [−0.02, 0.58] p=0.072 | – |

Four points stand out.

* **Controls matter.** With only the lagged expectation and headline CPI, the coefficient falls to 0.14 under the
  price family and to 0.09 (−0.16 to 0.34) under the baseline. Adding food inflation, the repo rate and the
  survey-mode dummy raises it. The estimate is conditional on that control set; we read this as specification
  dependence, not as evidence for either value.
* **Dropping 2020–21** also drops all telephone rounds, so the mode dummy falls out. Under the price family the point
  estimate shrinks to 0.17 and the interval widens; under the baseline the point estimate is almost unchanged (0.30)
  and only the interval widens.
* **Exact fieldwork dates** (N = 32) give larger estimates, 0.35 and 0.47, with wide intervals.
* **Information timing.** Adding next month's CPI, which households could not know at fieldwork, leaves the
  coefficient at 0.23, so the association is not just anticipation of the next CPI print.

![Figure 2. Coefficient on the news index with 95% EWC intervals: horizons, construction variants and outcomes (price-family index).](../../09_ANALYSIS/pipeline/data/processed/results_switched/paper_figures/fig_coefficients.png)

### 7.3 Other outcomes and horizons

Table 9 reports all four expectation measures at horizons of zero to three rounds. Only the one-year median at *h* = 0
and *h* = 2 have intervals that exclude zero; the pattern across horizons alternates in sign and size, which is what
one expects from noise in a short sample with overlapping changes rather than from a smooth dynamic response.

**Table 9. Coefficient on the news index by outcome and horizon (price family; 95% CI)**

| Outcome | h = 0 | h = 1 | h = 2 | h = 3 |
|---|---|---|---|---|
| One-year median | 0.25 (0.07, 0.43) | 0.08 (−0.12, 0.29) | 0.26 (0.05, 0.46) | 0.00 (−0.22, 0.23) |
| One-year mean | 0.12 (−0.00, 0.24) | 0.06 (−0.13, 0.26) | 0.18 (0.03, 0.34) | 0.02 (−0.22, 0.26) |
| Three-month median | 0.22 (−0.07, 0.50) | 0.16 (−0.07, 0.39) | 0.23 (−0.01, 0.47) | −0.03 (−0.22, 0.15) |
| Current perception, median | 0.15 (−0.05, 0.35) | 0.25 (−0.11, 0.61) | 0.26 (0.03, 0.50) | 0.01 (−0.31, 0.32) |

### 7.4 Horse race with search

Searches for "inflation" alone give 0.10 (−0.07 to 0.28). With both regressors, the news index is 0.24 (0.04 to 0.43;
p = 0.092) and searches 0.07 (−0.10 to 0.23). The news index carries information that this search measure does not,
but the Trends series is provisional.

### 7.5 State dependence

The association is larger when lagged CPI inflation exceeds 6%: the interaction is 0.18 (0.06 to 0.30; p = 0.016;
14 high-inflation rounds), and a continuous interaction with CPI inflation minus 4% gives 0.12 (0.03 to 0.22;
p = 0.062). The binary interaction disappears once 2020–21 is excluded (0.04, −0.26 to 0.33), so it rests largely on
the pandemic rounds.

### 7.6 Dynamics

A Bayesian VAR in Brent, CPI, the index, the median expectation and the repo rate (58 rounds, two lags) gives small
responses of the expectation to an index shock: 0.09 pp on impact when the index is ordered before expectations,
fading to zero within four rounds and turning slightly negative after five. With expectations ordered first the
impact response is zero by construction and the later responses range from −0.06 to 0.02 pp. The ordering therefore drives
the impact response, and the VAR adds no evidence beyond the local projections.

At the monthly level, the index responds to oil prices but not to CPI surprises. A 10% rise in Brent is followed by
about 0.16 to 0.20 standard deviations more attention in the same and next two months, with intervals excluding zero
at several horizons up to nine months. A one-point surprise in CPI inflation (relative to a recursive AR(12) forecast)
is followed by responses of 0.01 to 0.14 standard deviations, none distinguishable from zero. News attention in India
appears to follow visible fuel-price pressure more than surprises in the headline index.

### 7.7 Out of sample

In a recursive pseudo-real-time exercise (37 forecasts), adding the index to an AR(1) model with CPI and food inflation
leaves the root mean squared error unchanged (ratio 1.00; Clark–West p = 0.10). Against a pure AR(1), the model with
the index has a higher RMSE (ratio 1.12), although the Clark–West test, which adjusts for estimation noise in nested
models, rejects equal accuracy (p = 0.036). We do not claim out-of-sample predictive content.

### 7.8 Multiple testing

We report many estimates, and they are not independent: they share the outcome, the sample and most regressors. Only
one cell was designated primary. Under the definition the audit selected, that cell's wild-bootstrap p-value is
0.058; under the rejected baseline it is 0.036. No correction is applied to the secondary results, which should be
read as descriptive. Given the failed validation, the plan treats all expectation results as exploratory.

## 8. Limitations

1. **No human validation.** The audit relies on two passes of one language model; their agreement is not evidence of
   accuracy. Later batches were coded from short excerpts.
2. **Measurement.** The inflation tag is imprecise and the price family only slightly better; the index measures
   attention to price-related themes as GDELT tags them, not reading by households. Recall differs sharply by
   language.
3. **Validation failed.** The index does not peak in most pre-specified episodes; the Trends comparison uses one pull.
4. **Order of work.** The plan was frozen before any outcome regression, but the first regressions (baseline tag) were
   run before the audit selected the price family. The switch followed the pre-specified rule; we report both.
5. **Small, persistent samples.** 56 rounds, overlapping fieldwork, binned medians, and a pandemic period with a
   change of survey mode.
6. **Coverage.** Urban households only; online outlets in GDELT; one-in-four grid days for the monthly series; a gap in
   mid-2025; extensions built on the baseline tag.
7. **No causal interpretation.** Attention may respond to the same price shocks households experience, as the oil-price
   responses suggest; controls for real-time CPI do not remove that.

## 9. Conclusion

GDELT can be turned into an open, reliable, multilingual index of news attention to inflation for India, and the
index tracks search interest and responds to oil prices. But GDELT's inflation tag captures many articles that are not
about consumer prices and misses most that are; the index does not reproduce known price episodes; and its
association with household expectations is small, sensitive to the control set and absent out of sample. The
measurement and its documented limits are the contribution. A human-coded audit, a text classifier in place of theme
tags, item-level attention measures for food and fuel, and three Trends pulls are the obvious next steps.

## References

Aarab, A. et al. (2025). ECB Economic Bulletin, Issue 6/2025 [title to be checked].
Arndt, S. (2024; 2026). Working papers on newspaper types and household inflation expectations [full reference to be
checked].
Banerjee, S., Kanodia, A. and Ray, P. (2019). IIM Calcutta Working Paper Series No. 830 [title to be checked].
Carroll, C. D. (2003). Macroeconomic expectations of households and professional forecasters. Quarterly Journal of
Economics 118(1), 269–298.
Kishor, N. K. and Pratap, B. (2023). MPRA Paper No. 118951 [title to be checked].
Lamla, M. J. and Lein, S. M. (2014). The role of media for consumers' inflation expectation formation. Journal of
Economic Behavior & Organization 106, 62–77.
Larsen, V. H., Thorsrud, L. A. and Zhulanova, J. (2021). News-driven inflation expectations and information
rigidities. Journal of Monetary Economics 117, 507–520.
Leetaru, K. and Schrodt, P. A. (2013). GDELT: Global data on events, location, and tone, 1979–2012. ISA Annual
Convention.
Pratap, B., Ranjan, A., Kishore, V. and Bhoi, B. Reserve Bank of India Occasional Papers 42(2) [title and year to be
checked].
Ruhi, Sharma and Sankaran (2025). RBI Bulletin, July 2025 [title to be checked].

## Appendix A. Extensions (descriptive, baseline tag)

These were planned as extensions and are reported descriptively. They use the baseline tag because they were built
before the switch; given the failed validation, none is a test.

**E1, city exposure.** We assigned local articles to 19 IESH cities using outlet edition paths in web addresses.
Coverage is too thin for analysis: the median window has 0 to 8 tagged local articles depending on the city, only 10
of 209 city-years meet the descriptive threshold (Mumbai, Delhi, Chandigarh) and none the inferential one. Tagged
articles are 0.1% to 0.9% of local articles. No city-level estimate is reported.

**E2, English vs vernacular.** The English and vernacular monthly series correlate 0.91 at lag zero, falling to about
0.5–0.6 at six-month leads and lags in either direction, with no evidence that one leads the other (Figure A1). At
the window level they correlate 0.66. Each alone gives about 0.26 in the primary specification (English 0.26, 0.01 to
0.50; vernacular 0.26, 0.03 to 0.50); the vernacular index controlling for English gives 0.21 (−0.05 to 0.46). Because
vernacular recall in the audit is much higher than English recall, this comparison reflects how GDELT tags translated
text as much as what outlets cover.

![Figure A1. English and vernacular monthly attention series.](../../09_ANALYSIS/pipeline/data/processed/results/ext_figures/e2_eng_ver.png)

**E3, salience basket.** We built a search-implied salience-weighted inflation measure from Google Trends item terms.
In a horse race with published CPI inflation it shows no association (coefficient −0.01, −0.02 to 0.01), and on its
own it is weakly negative (−0.008, p = 0.04). A media-implied version from GDELT DOC item counts was built, but its
precision check was not completed, so it is not reported.

**E4, international framing.** The share of inflation articles that also carry international themes is uncorrelated
with the index (0.01) and adds nothing in the primary specification (0.00, −0.21 to 0.21; the index stays at 0.33).
The audit's agreement on international causes was too low (κ = 0.33) for claims.

**E5, attention cycle.** Attention peaked in June 2022 (rising over four months; half-life about nine months), March
2025 and April 2026 (Figure A2). Excess attention during disinflation is not associated with expectations (0.26,
−0.16 to 0.68). In monthly local projections, responses to rises and falls in CPI inflation are imprecise; only the
immediate response to falls has an interval excluding zero (0.24, 0.04 to 0.44).

![Figure A2. Monthly attention, CPI inflation and identified peaks.](../../09_ANALYSIS/pipeline/data/processed/results/ext_figures/e5_ipi_cpi_peaks.png)

## Appendix B. Audit design details

* **Strata and weights.** Eight strata as in Table 5; 2015–18 oversampled by 1.5. Estimates are post-stratified
  within stratum-by-period cells (2015–18 and 2019 onward). Unretrieved articles are not imputed; they reweight the
  rest of their cell (missing at random within cell). Confidence intervals come from a stratified bootstrap.
* **Frames.** The gating frame contains all economic strata plus non-economic articles with a price word in the
  address; the remaining non-economic stratum gives only an upper bound on missed relevant articles.
* **Codebook.** Relevance, direction (rising, falling, mixed, none) and primary and secondary cause from nine
  categories, with an uncertainty flag. The codebook was hashed before coding. Coders saw article text and address
  only, never the stratum, the GDELT tags or the weights.
* **Order of coding.** The first pass coded in a fixed order, gating strata first; the second pass coded the gating
  strata in a seeded random order within blocks.

## Appendix C. Pipeline and reproducibility

All steps run from scripts in `09_ANALYSIS/pipeline/scripts`. The analysis plan was frozen (hash recorded) before
outcome regressions; design decisions are logged, and the step log records each run with time, result and BigQuery
volume. BigQuery extraction used about 475 GB of a 670 GB budget in capped chunks. The switch decision is in
`data/processed/results/d9_switch.json`; switched-flag estimates are in `data/processed/results_switched/`; audit
outputs in `outputs/audit/`. A scripted re-run rebuilds the index from the cached extraction and re-estimates the main
results, the validation and the audit metrics; every compared file was byte-identical
(`data/processed/gate3/gate3_report.md`). Article texts are not redistributed.
