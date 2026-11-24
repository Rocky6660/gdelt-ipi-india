# Revision round 2: results

24 November 2026. These are additional analyses on the existing data. No primary estimate, flag or specification was changed, and the paper was not edited.

Conventions:

* **Flag and specification.** The flag is the final price-family flag. The expectation regressions use the paper's primary specification: one-year-ahead median expectation, change at h = 0, with the lagged level and lagged change of expectations, real-time CPI and food inflation, the repo-rate change and a phone-mode dummy. The sample is rounds with base-2012 CPI.
* **Inference.** Each regression row reports the coefficient (pp per SD of the index), a 95% EWC fixed-b CI and a restricted wild-bootstrap p (1,999 draws). Every row is re-seeded with the paper's bootstrap seed. The reference rows therefore reproduce the paper exactly: 0.251 [0.068, 0.434], p 0.058, N = 56.
* **Audit metrics.** These use coder-A truth and the paper's weights, which are post-stratified within stratum × period cells (empty cells pooled). CIs are from a stratified bootstrap (1,000 draws, the paper's seed). The reference case reproduces all 42 published gating-frame cells exactly, estimates and CIs.
* **Code and output.** The code is `09_ANALYSIS/pipeline/scripts/revision/r2_audit.py` and `r2_index.py`. Output files are in `outputs/audit_revision2/` and `data/processed/results_revision2/`.

---

## 1. Retrieval bounds (gating frame)

Of the 1,250 sampled articles, 1,113 were retrieved and coded from full text and 137 were not retrieved. All 137 have slug-based codes, and 11 of them are coded relevant by slug.

Thirteen of the 137 are in the "non-economic, other" stratum, which is outside the gating frame. That leaves 124 unretrieved articles in the gating frame.

The four cases below differ only in how the unretrieved articles are labelled:

* **Reference:** missing at random within each cell (the paper's assumption).
* **All relevant:** every unretrieved article is coded relevant.
* **None relevant:** every unretrieved article is coded not relevant.
* **Slug labels imputed:** the slug-based relevance codes are used for the unretrieved articles.

The worst case for precision is "none relevant"; the worst case for recall is "all relevant".

**Unretrieved articles by stratum**

| Stratum | Unretrieved | Slug-coded | Slug-coded relevant |
|---|---|---|---|
| English, tagged | 44 | 44 | 3 |
| English, economic, untagged | 34 | 34 | 0 |
| Hindi/Marathi, tagged | 9 | 9 | 4 |
| Hindi/Marathi, economic, untagged | 10 | 10 | 0 |
| Other vernacular, tagged | 9 | 9 | 2 |
| Other vernacular, economic, untagged | 10 | 10 | 0 |
| Non-economic, price word in address | 8 | 8 | 2 |
| Non-economic, other (outside frame) | 13 | 13 | 0 |

**Whole gating frame** (n coded = 1,026; 118 relevant; 438 baseline-flagged, 464 price-family-flagged)

| Case | Flag | Precision | Recall | F2 |
|---|---|---|---|---|
| Reference (missing at random) | baseline | 0.164 [0.128, 0.201] | 0.302 [0.202, 0.469] | 0.258 [0.188, 0.349] |
| | price family | 0.128 [0.084, 0.194] | 0.420 [0.270, 0.636] | 0.288 [0.194, 0.405] |
| Slug labels imputed | baseline | 0.160 [0.126, 0.196] | 0.314 [0.212, 0.482] | 0.264 [0.192, 0.356] |
| | price family | 0.118 [0.079, 0.173] | 0.434 [0.278, 0.642] | 0.282 [0.198, 0.385] |
| Unretrieved all relevant | baseline | 0.264 [0.222, 0.308] | 0.094 [0.069, 0.128] | 0.108 [0.081, 0.144] |
| | price family | 0.258 [0.182, 0.348] | 0.172 [0.113, 0.254] | 0.185 [0.122, 0.262] |
| Unretrieved none relevant | baseline | 0.146 [0.112, 0.183] | 0.299 [0.199, 0.473] | 0.247 [0.176, 0.341] |
| | price family | 0.109 [0.072, 0.165] | 0.418 [0.267, 0.634] | 0.267 [0.183, 0.372] |

Under every assumption, precision stays below 0.27 and recall below 0.44, so the audit failure does not depend on how the unretrieved articles are labelled. Price family beats baseline on F2 in every case.

**By stratum.** Precision is shown for tagged strata. Recall is 1 by construction inside a stratum where every article is tagged, and precision is undefined where none is. n is coded / flagged / relevant in the reference case.

| Stratum | Flag | n | Reference | Slug imputed | All relevant | None relevant |
|---|---|---|---|---|---|---|
| English, tagged (precision) | both | 256 / 256 / 35 | 0.138 [0.097, 0.182] | 0.131 [0.091, 0.171] | 0.251 [0.202, 0.303] | 0.122 [0.084, 0.162] |
| Hindi/Marathi, tagged (precision) | both | 91 / 91 / 22 | 0.240 [0.154, 0.331] | 0.254 [0.172, 0.354] | 0.299 [0.213, 0.393] | 0.220 [0.145, 0.313] |
| Other vernacular, tagged (precision) | both | 91 / 91 / 29 | 0.311 [0.223, 0.403] | 0.294 [0.211, 0.380] | 0.350 [0.260, 0.440] | 0.278 [0.196, 0.365] |
| English, economic, untagged (price-family precision) | price family | 266 / 16 / 8 | 0.071 [0.000, 0.229] | 0.057 [0.000, 0.182] | 0.283 [0.105, 0.485] | 0.057 [0.000, 0.182] |
| English, economic, untagged (price-family recall) | price family | 266 / 16 / 8 | 0.140 [0.000, 0.450] | 0.143 [0.000, 0.450] | 0.150 [0.045, 0.281] | 0.143 [0.000, 0.450] |
| Other vernacular, economic, untagged (price-family recall) | price family | 90 / 4 / 2 | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.148 [0.000, 0.385] | 1.000 [1.000, 1.000] |
| Hindi/Marathi, economic, untagged | price family | 90 / 1 / 0 | no relevant articles | no relevant articles | recall 0.000 | no relevant articles |
| Non-economic, price word in address (price-family recall) | price family | 142 / 5 / 22 | 0.215 [0.051, 0.391] | 0.230 [0.071, 0.405] | 0.184 [0.059, 0.337] | 0.215 [0.055, 0.404] |

"Both" means baseline and price family give the same value in tagged strata, because every article in those strata carries both tags.

The baseline flag tags no article in the untagged strata, so its recall there is 0.000. The full stratum × case × metric table, including the econ frame, is in `outputs/audit_revision2/prf_revision2.csv`.

## 2. Precision, recall and F2 by language and retrieval route (gating frame, reference case)

| Group | Flag | n coded / flagged / relevant | Precision | Recall | F2 |
|---|---|---|---|---|---|
| All | baseline | 1,026 / 438 / 118 | 0.164 [0.128, 0.201] | 0.302 [0.202, 0.469] | 0.258 [0.188, 0.349] |
| | price family | 1,026 / 464 / 118 | 0.128 [0.084, 0.194] | 0.420 [0.270, 0.636] | 0.288 [0.194, 0.405] |
| English | baseline | 566 / 231 / 51 | 0.136 [0.094, 0.179] | 0.291 [0.167, 0.543] | 0.237 [0.152, 0.357] |
| | price family | 566 / 249 / 51 | 0.114 [0.061, 0.195] | 0.447 [0.249, 0.742] | 0.282 [0.166, 0.425] |
| Hindi/Marathi | baseline | 181 / 91 / 22 | 0.240 [0.154, 0.331] | 1.000 [1.000, 1.000] | 0.612 [0.476, 0.712] |
| | price family | 181 / 92 / 22 | 0.131 [0.057, 0.301] | 1.000 [1.000, 1.000] | 0.430 [0.232, 0.683] |
| Other Indian languages | baseline | 181 / 91 / 31 | 0.311 [0.223, 0.403] | 0.620 [0.379, 1.000] | 0.517 [0.352, 0.733] |
| | price family | 181 / 95 / 31 | 0.350 [0.198, 0.494] | 1.000 [1.000, 1.000] | 0.729 [0.552, 0.830] |
| All Indian languages | baseline | 362 / 182 / 53 | 0.253 [0.184, 0.327] | 0.881 [0.732, 1.000] | 0.589 [0.477, 0.678] |
| | price family | 362 / 187 / 53 | 0.163 [0.080, 0.328] | 1.000 [1.000, 1.000] | 0.493 [0.303, 0.709] |
| Live retrieval | baseline | 645 / 297 / 77 | 0.162 [0.120, 0.210] | 0.369 [0.223, 0.681] | 0.294 [0.198, 0.424] |
| | price family | 645 / 308 / 77 | 0.125 [0.085, 0.174] | 0.408 [0.246, 0.745] | 0.280 [0.192, 0.395] |
| Archive (Wayback) retrieval | baseline | 381 / 141 / 41 | 0.167 [0.106, 0.233] | 0.229 [0.122, 0.490] | 0.213 [0.123, 0.367] |
| | price family | 381 / 156 / 41 | 0.131 [0.056, 0.260] | 0.434 [0.194, 0.789] | 0.296 [0.137, 0.502] |

Notes:

* The "all" and "English" rows include the non-economic slug stratum, which is coded as English.
* Within the Indian-language groups, recall of 1.000 with a degenerate CI means no relevant article was found in the sampled untagged strata. It is not evidence of perfect recall: those strata were sampled at 90 articles each, and the vernacular frame has no non-economic stratum.
* Live and archive CIs overlap almost completely for both flags.

## 3. Expectation robustness (price family, primary specification, h = 0)

"Post-2022" means fieldwork starting on or after 1 January 2022. The INR/USD change uses the same timing as the Brent control: the 2-month log change in the monthly average, ending in the month before fieldwork.

| Specification | N | Coefficient | 95% EWC CI | Wild-bootstrap p |
|---|---|---|---|---|
| Primary (reference) | 56 | 0.251 | [0.068, 0.434] | 0.058 |
| Add linear time trend | 56 | 0.237 | [0.043, 0.430] | 0.068 |
| Post-2022 dummy + interaction: index (slope before 2022) | 56 | 0.284 | [0.016, 0.551] | 0.085 |
| Post-2022 dummy + interaction: index × post-2022 | 56 | −0.273 | [−0.606, 0.059] | 0.052 |
| Subsample: fieldwork before 2022 | 32 | 0.255 | [−0.166, 0.676] | 0.114 |
| Subsample: fieldwork 2022 onward | 24 | 0.105 | [−0.302, 0.513] | 0.628 |
| Add change in INR/USD | 56 | 0.235 | [0.019, 0.450] | 0.064 |
| Excl. 2020–21 + post-2022 regime: index (slope before 2022) | 46 | 0.174 | [0.028, 0.320] | 0.130 |
| Excl. 2020–21 + post-2022 regime: index × post-2022 | 46 | −0.183 | [−0.630, 0.264] | 0.266 |

The phone-mode dummy is constant within two samples, so it drops out of: the 2022-onward subsample (all phone rounds) and the excl.-2020–21 rows.

The point estimate is stable at 0.24–0.28 when a trend, a post-2022 regime or INR/USD is added. The post-2022 slope is 0.284 − 0.273 ≈ 0.01. None of the variants has a bootstrap p below 0.05.

## 4. Window length

The windows were rebuilt from the cached extraction using the last 10 and the last 7 days before fieldwork. Every other rule is the paper's:

* the day-validity rule;
* the outlet-day rule, recomputed over the shorter window's days;
* the 10-article presence rule;
* the 80% core, re-derived for each length;
* the equal-weight mean.

The 14-day rebuild reproduces the published series exactly (maximum absolute difference 0.0).

| Window | Core outlets | Valid windows | Core present per window (min / median) | Corr. with 14-day series | N | Coefficient | 95% EWC CI | p |
|---|---|---|---|---|---|---|---|---|
| 14 days (paper) | 104 | 62 | 84 / 97.5 | 1.000 | 56 | 0.251 | [0.068, 0.434] | 0.058 |
| 10 days | 93 | 62 | 76 / 88 | 0.960 | 56 | 0.293 | [0.046, 0.539] | 0.058 |
| 7 days | 87 | 62 | 71 / 82 | 0.943 | 56 | 0.260 | [0.040, 0.480] | 0.059 |

## 5. Outlet composition

Of the 104 core outlets, the number contributing to each valid window (62 windows) is:

| | Min | Median | Max |
|---|---|---|---|
| All windows | 84 | 97.5 | 103 |

| Year | Windows | Min | Median | Max |
|---|---|---|---|---|
| 2016 | 5 | 92 | 99 | 101 |
| 2017 | 6 | 97 | 98 | 101 |
| 2018 | 6 | 97 | 98 | 100 |
| 2019 | 5 | 101 | 103 | 103 |
| 2020 | 6 | 99 | 100 | 101 |
| 2021 | 6 | 91 | 96 | 103 |
| 2022 | 6 | 91 | 92 | 93 |
| 2023 | 6 | 86 | 102.5 | 103 |
| 2024 | 6 | 96 | 97.5 | 101 |
| 2025 | 5 | 91 | 94 | 95 |
| 2026 | 5 | 84 | 88 | 92 |

| Version | N | Coefficient | 95% EWC CI | p | Corr. with paper series |
|---|---|---|---|---|---|
| All valid windows (reference) | 56 | 0.251 | [0.068, 0.434] | 0.058 | 1.000 |
| Windows with ≥ median (97.5) core outlets (31 windows) | 30 | 0.192 | [0.071, 0.314] | 0.018 | 1.000 |
| Balanced: 37 outlets present in every valid window | 56 | 0.352 | [0.143, 0.560] | 0.012 | 0.891 |
| Balanced: 44 outlets present in every window of the regression sample | 56 | 0.346 | [0.157, 0.536] | 0.008 | 0.929 |

In the ≥ median row, z-scores use the remaining windows only. Its correlation is 1.000 because the series is identical where it exists.

## 6. Matched validation (monthly series with the window construction)

**Data limitation.** The extraction stored within-day distinct-URL counts per host only on window days (S rows). On non-window days it kept raw article counts per source (D rows): no de-duplicated denominator and no host. The window construction can therefore be applied exactly only on grid days that fall inside survey windows. All 172,670 D rows lack distinct counts.

The matched series:

* covers 68 months, 2016-02 to 2026-09 (5–8 months per year);
* uses host-day distinct URLs, valid days and the outlet-day rule;
* treats an outlet as present if it has ≥ 10 distinct URLs in the month;
* takes the equal-weight mean of the price-family share over the 104 window-core outlets, with 52–97 outlets per month (median 85.5).

Its correlation with the paper's monthly series on the same months is 0.799.

A fully matched series on all grid days would need a new extraction.

The checks below are the same as the paper's validation (Trends correlations: raw, after removing a linear trend and log core volume, and partial on CPI and food inflation, with block-bootstrap CI; episode z-scores relative to non-episode months, with peak = above the non-episode 90th percentile). The paper's monthly series is shown on all its months and on the same 68 months.

**Trends correlations**

| Series | Term | N | r raw | r after volume/trend | r partial (CPI, food) | 95% CI (partial) |
|---|---|---|---|---|---|---|
| Matched (window construction) | inflation | 68 | 0.416 | 0.268 | 0.330 | [0.101, 0.617] |
| | mehngai | 68 | 0.260 | 0.216 | 0.306 | [0.189, 0.675] |
| | महंगाई | 68 | 0.491 | 0.393 | 0.244 | [0.004, 0.488] |
| Paper monthly, same 68 months | inflation | 68 | 0.587 | 0.420 | 0.642 | [0.405, 0.797] |
| | mehngai | 68 | 0.169 | 0.102 | 0.249 | [0.088, 0.726] |
| | महंगाई | 68 | 0.520 | 0.387 | 0.340 | [0.058, 0.547] |
| Paper monthly, all months | inflation | 129 | 0.542 | 0.409 | 0.546 | [0.311, 0.753] |
| | mehngai | 129 | 0.107 | 0.039 | 0.190 | [0.082, 0.637] |
| | महंगाई | 129 | 0.359 | 0.252 | 0.286 | [0.100, 0.494] |

**Episodes**

| Series | Onion 2019–20 | Fuel 2021–22 | Post-Ukraine 2022 | Tomato 2023 | Peaks |
|---|---|---|---|---|---|
| Matched (months in episode) | z −1.06 (2) | 0.15 (5) | 1.91 (3), peak | 0.98 (2) | 1 of 4 |
| Paper, same 68 months | −0.81 (2) | 0.05 (5) | 2.47 (3), peak | 0.60 (2) | 1 of 4 |
| Paper, all months | −0.72 (4) | −0.06 (9) | 2.11 (5), peak | 0.22 (3) | 1 of 4 |

The 90th-percentile thresholds are 0.031, 0.035 and 0.037 respectively.

The matched construction does not change the validation result: one of four episodes peaks (post-Ukraine), the same as in the paper. Its raw Trends correlation with "inflation" (0.416) is below the paper's 0.5 bar and below the paper series on the same months (0.587).

## 7. Joint test: all monthly LP responses h = 0–12 are zero

The regressions are the paper's monthly LPs: the price-family monthly index (z) at t+h regressed on the shock at t and the index at t−1. To define the stacked covariance they are estimated on the common sample where all 13 horizons exist (N = 92 for CPI surprises, N = 103 for Brent; the paper's per-horizon N is 103–106 and 114–127). The common-sample coefficients differ from the paper's by at most 0.106 (CPI) and 0.010 (Brent).

| Shock | N (common) | Newey–West Wald χ²(13) | p (asymptotic) | p (moving-block bootstrap, block 12, 4,999 draws) | Bonferroni p (13 paper horizons) | Cumulative response h = 0–12 [95% EWC CI], p |
|---|---|---|---|---|---|---|
| CPI surprise (1 pp) | 92 | 52.3 | < 0.001 | 0.926 | 1.000 | 0.641 [−2.584, 3.866], p 0.664 |
| Brent (1%) | 103 | 198.6 | < 0.001 | 0.203 | 0.122 | 0.090 [−0.060, 0.239], p 0.208 |

The asymptotic Newey–West Wald test should not be relied on here. It estimates a 39 × 39 long-run covariance (13 horizons × 3 regressors) from about 100 overlapping monthly observations, a setting in which HAC Wald tests are known to over-reject severely.

The block bootstrap of the same statistic, the Bonferroni bound and the fixed-b test on the cumulative response all fail to reject. The joint null that all responses are zero is not rejected at 5% for either shock:

* CPI surprise: bootstrap p 0.926.
* Brent: bootstrap p 0.203. The smallest single-horizon p is 0.009 (Bonferroni 0.122).
