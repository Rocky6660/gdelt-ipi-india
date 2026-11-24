# Revision round 3: results and change log

25 November 2026. Only `10_OUTPUTS/paper/final/source/content.js`, `appendix.js` and two figure PNGs (`e5_ipi_cpi_peaks_c.png`, `e2_eng_ver_c.png`) were changed; `build.js` and the formatting were not touched.

Every new number comes from a script saved as `09_ANALYSIS/pipeline/scripts/revision/r3_*.py`, with outputs in `09_ANALYSIS/pipeline/data/processed/results_revision3/`. No new BigQuery queries were run and no data were downloaded; existing caches and files only.

## Summary

### Fixed

1. **Control variants that reach 5% (A1).** The claim that no time- or price-control variant reaches 5% was false. Three control variants reach it:
   - headline CPI as the only price control, p = 0.040;
   - next-month CPI added, p = 0.035;
   - intra-window Brent and INR/USD changes, a new check, p = 0.045.

   No time-trend or post-2022 variant does.
2. **Monthly peaks (A2).**
   - The disagreement was between series, not a typo. Table 17 uses the 3-month centred moving average (peaks 4.97% in April 2022 and 6.75% in April 2026), while Figures 2 and 10 plotted the raw series (peaks 5.44% in April 2022 and 8.65% in March 2026).
   - The text now reports both. Figure 10 was regenerated to plot the moving average used for the peaks, with the raw series shown thin behind it, and Table 17 has a note.
   - 6.75 is 6.747 to three decimals, so "6.7" is correct and the review's "6.8" is not.
   - The claim of euro-area-like persistence after 2022 was corrected with period means (2.10%, 3.27% and 2.92%).
3. **Language split (A3).** It uses the baseline tag with the 2018 core. The text was right and Table F1 was mislabelled; F1 is relabelled. Separately, the salience extension's outcome is the change in *current perceived* inflation, not the one-year median; Table F2's title and Section 4.4.3 are corrected.
4. **BVAR sample (A4).** 58 rounds enter the VAR and 56 observations remain after two lags; the text and the Figure 6 caption are fixed. The review's "only 57 have CPI" refers to the sample flow after the lag requirement.
5. **Month-rule rounds (A5).** There are 26 month-rule rounds: 22 before 2020 and 4 in 2020 (Jan, Jul, Sep, Nov). The review's 23/3 was not right either.
6. **Audit accounting (A6).**
   - The gating frame has 1,026 coded and 118 relevant articles. Table 8's language rows sum to 928 and 104 because 98 coded articles (14 relevant) in the main strata come from Bengali, Gujarati, Kannada, Malayalam, Punjabi, Tamil or Telugu outlets. These count in the totals and retrieval rows but in no language row; the Table 8 note now explains this.
   - 119 = 118 in the gating frame + 1 in the unscreened stratum.
7. **Table F3 N (A7).** N = 105 because the language series use the 2018 core and start in January 2018; the note explains this.
8. **GDELT version (A8).** 2.1 everywhere.
9. **Abstract range (B9).** "Stable in size" is replaced by the honest range: 0.11–0.14 for the change in the index, the mean expectation and minimal controls, up to about 0.35 for exact-date rounds and balanced panels. The near-zero slope after 2022 is stated.
10. **Causal and over-strong phrases (B10).** These were softened as instructed:
    - "does not drive / does not inflate / does not merely reflect" now read "is not driven only by …, within the precision available";
    - the VAR "index shock" is now an "orthogonalised innovation in the index (Cholesky ordering, no structural interpretation)";
    - the supervised-classifier remark is now a conjecture.
11. **Price-theme coverage (B11).** The title now reads "Price-Theme News Coverage in India: …". "GDELT price-theme coverage, a noisy proxy for attention to inflation" is defined in the abstract, the introduction and Section 3.2.1, and is used for headings and the measured object.
12. **Definitions and wording (C14, C18, D19).** Definitions were added for:
    - the gating frame;
    - economic articles (any ECON_ theme);
    - word share;
    - the wire-copy filter;
    - the 2018 core (99 outlets, at least 80% of valid windows from January 2018);
    - the salience-weighted median and absolute measures;
    - excess attention during disinflation;
    - the peak, months-of-rise and half-life rules.

    Section 5.2 now states plainly that the missing human audit remains the main limitation, and that 200–300-character excerpts hold fewer words in Indic scripts.
13. **"IPI" (D20).** No "IPI" remains in the text. Figure 10's axis now reads "News index"; Figure 8's legend reads "Indian-language (z)".
14. **Repetition and disclosures (D21).**
    - The plan, the deviations and the order of the analysis are consolidated in Section 3.5.4 (renamed "Analysis Plan, Deviations and Sequence"). The former Section 4.3.10 is folded into it.
    - The introduction, Section 4.2, Section 4.3.1, the eighth limitation and the conclusion now refer back in one clause.
15. **Appendix numbering (D22).** Table E5 is now E4 and the reference to it is updated.
16. **Look-alike characters (D23).** There are no Greek look-alike capitals, no Cyrillic and no "indexx" in the source. The Greek letters present are genuine maths symbols, and "×" was already explicit in Tables 14 and E2. The reviewer's defects are PDF text-extraction artefacts.
17. **Literature (E24).** Six papers were verified on the web (journal, volume, issue, pages, DOI) and added with one sentence each:
    - Das, Lahiri and Zhao (2019);
    - Pfajfar and Santoro (2013);
    - Dräger (2015);
    - Nimark and Pitschner (2019);
    - Baker, Bloom and Davis (2016), cited at the EPU-style count;
    - Ash and Hansen (2023).
18. **Formatting (F25–F31).**
    - "—" is now used in uncomputed cells (Tables 10, 11, E2 and F4), with notes, and in the empty Mode cells of Table C1, with its note matching.
    - The Table F4 note states that the April 2026 half-life is right-censored.
    - MoSPI is now used in the text, the Figure 10 legend and the data statement.
    - The two Coibion et al. references are reordered (2018 first).
    - The GDELT reference no longer has a line-breaking URL prefix.
    - The multiple-testing count is updated from 107 to 113 (20 rows in Table 12).
    - Three review points needed no change. Table 6 already reads 1,113 in the source; the "1.113" was a PDF rendering artefact. Table 8's "Other Indian languages" rows are already separate rows in the source. The Arndt DOI (10.11588/heidok.00034992) was already complete; it was verified.
19. **Errors found by the new number check, not in the review.**
    - Table 11, 60% core: upper CI 0.51 → 0.50 (the file has 0.5046).
    - Table 15, baseline vs AR(1): RMSE ratio 1.17 → 1.16 (the file has 1.1646).
    - Table 11, change in index: 0.12 → 0.11 (the file has 0.1145).
    - Bootstrap p-values are multiples of 0.0005; eleven printed values had been rounded down at a tie and are now rounded half up, as for the primary 0.058:
      - baseline primary 0.036 → 0.037 (Table 11, Sections 4.3.1 and 4.3.9);
      - volume-weighted 0.010 → 0.011;
      - change in index 0.272 → 0.273;
      - INR/USD 0.064 → 0.065;
      - three-month median 0.146 → 0.147;
      - Index × High 0.015 → 0.016 (Tables 14 and E2, Section 4.3.5);
      - wire-copy filter 0.036 → 0.037 (E1);
      - 2018 core 0.071 → 0.072 (E1);
      - F1 0.089 → 0.090, 0.107 → 0.108, 0.669 → 0.670, 0.184 → 0.185 and 0.246 → 0.247;
      - F2 0.428 → 0.429.

      The Bonferroni bound is now 0.121 (it was 0.122).

### New results (price family, one-year median, h = 0; EWC 95% CI; wild-bootstrap p)

| Check | N | Coefficient | 95% CI | p | Script |
|---|---|---|---|---|---|
| Primary (reference) | 56 | 0.251 | (0.068, 0.434) | 0.058 | — |
| Outlets de-duplicated, 9 lifestyle domains dropped (89 outlets) | 56 | 0.264 | (0.053, 0.474) | 0.090 | r3_index.py |
| Non-energy price family | 56 | 0.314 | (0.012, 0.616) | 0.042 | r3_index.py |
| No lagged dependent variable | 57 | 0.175 | (−0.122, 0.473) | 0.233 | r3_lp.py |
| Months between rounds added | 56 | 0.339 | (0.125, 0.553) | 0.031 | r3_lp.py |
| Outcome per two months | 56 | 0.243 | (0.020, 0.466) | 0.102 | r3_lp.py |
| Intra-window Brent and INR/USD changes | 56 | 0.269 | (0.104, 0.435) | 0.045 | r3_lp.py |

Notes on these checks:

* **Outlet de-duplication.** The five economictimes.indiatimes.com subdomains and haryana.punjabkesari.in are pooled with their parent outlet in the same language. These nine domains are dropped: bollywoodhungama, bollywoodtadka, cinema.dinamalar, cinema.vikatan, desimartini, femina, food.ndtv, temple.dinamalar and vogue. The resulting index correlates 0.97 with the published one, and the identity rebuild reproduces the published index exactly (maximum difference 0.0).
* **Non-energy family.** The cache keeps exact bits for ECON_INFLATION, WB_442, cost of living, price controls and gouging. It does not separate FUELPRICES from the gasoline/diesel codes, or WB_1623 from other subsidy codes, so those are excluded too. The index has a mean of 1.21% of articles and correlates 0.72 with the price family.
  - In the audit sample, the non-energy flag tags exactly the 500 baseline-tagged articles. The 32 sampled articles tagged only by the price family carry only energy, transport or subsidy codes.
  - Its audit precision and recall therefore equal the baseline's: precision 0.164 (0.128, 0.201), recall 0.302 (0.202, 0.469).
* **Recall bound across the binomial CI (C14).** The share is 1/87 = 0.011, with exact CI 0.0003–0.062. Whole-flow recall:
  - baseline: 0.29 (lower limit), 0.14 (point), 0.04 (upper limit);
  - price family: 0.41, 0.20 and 0.06.

  Script: r3_audit.py.
* **Tone and direction (C16).** Among relevant audited articles there are 79 rising, 26 falling, 6 mixed and 8 with no direction. GDELT V2Tone does not track direction: articles coded falling have a lower mean tone than those coded rising (−2.42, n = 20, against −1.17, n = 69; Mann–Whitney p = 0.079). Rising and falling sub-indices were therefore not built; this is now a limitation and future work. Script: r3_index.py.
* **Months between rounds (C15).** Gaps range from 0.99 to 3.02 months (median 2.0). The VAR's equal-spacing assumption is now stated in Section 4.3.6.

### Remaining limitations, and why

* **Human audit (C18).** There is still no human-coded audit. It cannot be produced from data on disk.
* **Tone split (C16).** Not built. The audit codes cover only 119 relevant articles, and V2Tone does not separate rising from falling prices.
* **Regional panel (C17).** Not built. The city-exposure condition already fails (Section 4.4.1), so it is listed as future work. The intra-window Brent/INR check *was* done, from daily FRED-based data already on disk.
* **Non-energy family (C13).** It is slightly stricter than requested (it also drops FUELPRICES and WB_1623) because the cache does not separate those codes. Exact code-level counts would need a new extraction.
* **Pratap et al. (2021) pages (F30).** Page numbers could not be found on the RBI site or in indexes; the reference is left without pages.
* **Fully matched validation series.** It still covers only 68 months, because de-duplicated counts exist only on window days.
* **Things not checked visually.** The docx could not be built here (the `docx` Node package is not installed); both source files load and keep their structure. Figure 4's x-axis label is clipped on the right in the existing PNG; it was not regenerated, because it was not on the list.

### Number check (r3_numcheck.py)

The check has three layers:

1. **Tables.** All 837 numbers in tables were checked against each table's own result files: none unmatched.
2. **Targeted claims.** 49 claims were checked: every number added or changed in this round, rebuilt from its file and required verbatim in the source, with p-values rounded half up. None is unmatched.
3. **Prose screen.** 243 prose numbers were checked against all result files: none unmatched. On its own this screen is uninformative, because a random 2-decimal number in [0, 1] matches the pooled files 100% of the time. It is reported only for completeness.

Per-table chance-match rates are in `results_revision3/r3_numcheck.json`. They are high (0.87–0.90) for the audit Tables 7–9, which were cross-checked exactly in round 2.

## Scripts

* `r3_checks.py`: facts for A1–A8 (Table 11 p-values, raw vs moving-average peaks, period means, BVAR rows, month-rule counts, F3 months, E3 outcome).
* `r3_audit.py`: audit accounting (A6) and the recall bound across the binomial CI (C14).
* `r3_lp.py`: C15 and C17 local projections.
* `r3_index.py`: C12 de-duplicated outlets, C13 non-energy index with audit precision/recall, C16 tone vs direction (cached extraction).
* `r3_figs.py`: Figures 10 and 8 (300 dpi, no titles).
* `r3_numcheck.py`: the number check.

## Change log (every edit, old → new)

**1. [B11] content.js**

- Old: title: "Media Attention to Inflation in India: A Reproducible GDELT Index,
- New: title: "Price-Theme News Coverage in India: A Reproducible GDELT Index,

**2. [B11] content.js**

- Old: This paper constructs a scripted, reproducible index of media attention to inflation, that is, the share of news coverage devoted to prices, for India
- New: This paper constructs a scripted, reproducible index of price-theme news coverage for India, that is, the share of news articles that GDELT tags with price-related themes, a noisy proxy for media attention to inflation,

**3. [B9/A1] content.js**

- Old: The estimate is stable in size across time trends, exchange-rate controls, window lengths and outlet composition, but no time- or price-control variant reaches the 5% level, the association is concentrated before 2022, and it yields no out-of-sample forecasting gain.
- New: Across the reported specifications the coefficient ranges from 0.11–0.14 (index in changes, mean expectation, or no food-price, repo-rate and survey-mode controls) to about 0.35 (exact-date rounds, balanced outlet panels); some control variants reach the 5% level and none of the time-trend or post-2022 variants does, the slope after 2022 is close to zero, and the index yields no out-of-sample forecasting gain.

**4. [B11] content.js**

- Old: Throughout the paper, *media attention* means the share of news coverage devoted to prices; it is a property of what outlets publish, not of what households read, remember or believe.
- New: Throughout the paper, the measured object is *GDELT price-theme coverage*: the share of articles that GDELT tags with price-related themes. It is a noisy proxy for attention to inflation (at most 0.16 of tagged articles are judged relevant in the audit below), and it is a property of what outlets publish, not of what households read, remember or believe.

**5. [D21] content.js**

- Old: The plan was not publicly registered; its relation to the order of the analysis is set out once, in Section 4.3.10.
- New: The plan was not publicly registered; it, the deviations from it and the order of the analysis are set out once, in Section 3.5.4.

**6. [D21] content.js**

- Old: The findings are mixed, and the paper reports them as such. The index is repeatable, and its paper construction co-moves in levels with English-language search interest for \"inflation\". However, by the model-based audit GDELT's inflation tag is imprecise and misses most relevant articles; the broader theme family selected by the audit is only slightly better; the index fails the pre-specified episode test; and the aggregate association with household expectations is small, sensitive to the choice of controls and outcome, at the margin of what the sample can detect, and absent out of sample. The paper is therefore positioned as an exploratory data-construction exercise: it documents a reproducible measurement pipeline and its failures, makes no claim that the audit establishes accuracy, and treats all results on expectations as exploratory.
- New: The findings are mixed: the index is repeatable, but by the model-based audit the tags are imprecise, the index fails the episode test, and the association with expectations is small and fragile. The caveats are stated in full in the abstract and in Section 5.2; the paper is an exploratory data-construction exercise.

**7. [E24] content.js**

- Old: These studies identify effects of information or price exposure at the household level;
- New: Pfajfar and Santoro (2013) find, for US households, only weak support for the epidemiological view that news coverage moves expectations towards professional forecasts, and Dräger (2015) finds small and asymmetric effects of Swedish media reports on inflation perceptions and expectations. Nimark and Pitschner (2019) model news media as a delegated filter that selects which events readers learn about, which is the sense in which coverage, rather than events, is measured here. These studies identify effects of information or price exposure at the household level;

**8. [E24] content.js**

- Old: More broadly, Gentzkow et al. (2019) review the use of text as data in economics and stress that automated text measures must be validated against human judgement before they are used as variables;
- New: More broadly, Gentzkow et al. (2019) and Ash and Hansen (2023) review the use of text as data in economics and stress that automated text measures must be validated against human judgement before they are used as variables;

**9. [E24] content.js**

- Old: Pattanaik et al. (2019) examine whether household expectations
- New: Das et al. (2019) use the IESH to study how Indian households form expectations and how well the survey forecasts inflation. Pattanaik et al. (2019) examine whether household expectations

**10. [E24] content.js**

- Old: or against an economic-policy-uncertainty-style newspaper count, because neither was available in comparable form.
- New: or against a newspaper count in the style of the economic policy uncertainty index (Baker et al., 2016), because neither was available in comparable form.

**11. [A5] content.js**

- Old: For 26 rounds before 2020 for which exact fieldwork dates are not published,
- New: For 26 rounds for which exact fieldwork dates are not published (22 rounds before 2020 and 4 in 2020: January, July, September and November),

**12. [A5] content.js**

- Old: and pre-2020 fieldwork dates are set by rule for 26 rounds.
- New: and fieldwork dates are set by rule for 26 rounds (22 before 2020 and 4 in 2020).

**13. [B11/D19] content.js**

- Old: For each outlet and window, the index is the share of distinct articles (web addresses de-duplicated within a day) that carry an inflation theme among all of the outlet's articles.
- New: For each outlet and window, the index is the share of distinct articles (web addresses de-duplicated within a day) that carry an inflation theme among all of the outlet's articles. The series is therefore GDELT price-theme coverage, a noisy proxy for attention to inflation; \"attention\" is used below only as shorthand for this measured share.

**14. [D19] content.js**

- Old: Table 4 shows that alternative constructions move closely with the baseline index; only the price family differs materially.
- New: Table 4 shows that alternative constructions move closely with the baseline index; only the price family differs materially. In Table 4, an *economic* article is one carrying at least one GDELT theme beginning with ECON_; the *word share* divides the GDELT word count of tagged articles by the word count of all articles of the outlet; the *wire-copy filter* removes from the numerator any tagged article whose word count and first six tone values match an article published on the same day by another host; and the *2018 core* is the set of 99 outlets present in at least 80% of valid windows from January 2018, which admits Indian-language outlets that joined GDELT after 2016.

**15. [A2] content.js**

- Old: On scale, the baseline monthly series peaks at 3.1% of articles in June 2022, while the price-family series peaks at 5.0% in April 2022 and 6.7% in April 2026.
- New: On scale, the raw monthly baseline series peaks at 3.4% of articles in July 2022, and the raw price-family series reaches 5.4% in April 2022 and 8.7% in March 2026 (Figure 2). The attention-cycle extension (Section 4.4.5, Table 17 and Figure 10) uses a 3-month centred moving average of the same series, which peaks at 5.0% in April 2022 and 6.7% in April 2026.

**16. [D19] content.js**

- Old: where *C* is the set of core outlets,
- New: where *C* is the set of core outlets present in the window,

**17. [A8] content.js**

- Old: the GDELT Global Knowledge Graph 2.0 (via Google BigQuery)
- New: the GDELT Global Knowledge Graph 2.1 (via Google BigQuery)

**18. [D19] content.js**

- Old: computed in the *gating frame*, which consists of economic articles plus non-economic articles with a price word in their address,
- New: computed in the *gating frame*, which consists of the six economic strata (articles with at least one ECON_ theme, tagged or untagged, in all three language groups) plus non-economic articles with a price word in their address, and excludes only the unscreened non-economic stratum,

**19. [C14] content.js**

- Old: Only 1 of 87 coded articles in that stratum was relevant (exact 95% CI 0.000 to 0.062). Because the stratum is very large, however, even this low share implies that recall measured over the whole news flow could be as low as 0.04, so the recall figures reported above are upper bounds for the whole news flow.
- New: Only 1 of 87 coded articles in that stratum was relevant (share 0.011; exact Clopper–Pearson 95% CI 0.0003 to 0.062). Because the stratum is very large, the implied recall over the whole news flow is sensitive to this share: for the baseline tag it is 0.29 at the lower limit of the interval, 0.14 at the point estimate and 0.04 at the upper limit (price family: 0.41, 0.20 and 0.06). The recall figures reported above are therefore upper bounds for the whole news flow.

**20. [A6] content.js**

- Old: Live and archive intervals overlap almost completely."],
- New: Live and archive intervals overlap almost completely. The language rows do not sum to the gating frame (1,026 coded, 118 relevant): 98 coded articles (14 relevant) in the main strata come from outlets whose source language is Bengali, Gujarati, Kannada, Malayalam, Punjabi, Tamil or Telugu; they enter the totals and the retrieval rows but no language row."],

**21. [A6] content.js**

- Old: Among the 119 articles that the first pass coded as relevant,
- New: Among the 119 articles that the first pass coded as relevant (the 118 in the gating frame plus 1 in the unscreened stratum),

**22. [A6] content.js**

- Old: and the direction and cause kappas are 0.97 and 0.94 on the 118 articles that both passes coded as relevant.
- New: and the direction and cause kappas are 0.97 and 0.94 on the 118 gating-frame articles that both passes coded as relevant.

**23. [B10] content.js**

- Old: so the dating rule for the pre-2020 rounds does not drive the result.
- New: so the result is not driven only by the dating rule for the month-rule rounds, within the precision available.

**24. [B10] content.js**

- Old: so variation in outlet composition does not inflate the primary estimate.
- New: so the primary estimate is not driven only by variation in outlet composition, within the precision available.

**25. [B10] content.js**

- Old: so the association does not merely reflect anticipation of the next CPI release.
- New: so the association is not driven only by anticipation of the next CPI release, within the precision available.

**26. [B10] content.js**

- Old: a supervised text classifier trained on a human-coded sample would likely improve both precision and recall.
- New: a supervised text classifier trained on a human-coded sample might improve precision and recall, a conjecture this paper does not test.

**27. [A1] content.js**

- Old: none of the time or price-control variants reaches the 5% level.
- New: among the control variants, three reach the 5% level (headline CPI as the only price control, p = 0.040; next-month CPI added, p = 0.035; intra-window Brent and INR/USD changes added, p = 0.045), while none of the time-trend or post-2022 variants does.

**28. [A1/F] content.js**

- Old: or the two-month change in the rupee–dollar rate (0.24, p = 0.064)
- New: or the two-month change in the rupee–dollar rate (0.24, p = 0.065)

**29. [F] content.js**

- Old: ["Change in INR/USD added","56","0.235","(0.019, 0.450)","0.064"]
- New: ["Change in INR/USD added","56","0.235","(0.019, 0.450)","0.065"]

**30. [F] content.js**

- Old: ["Change in index instead of level","55","0.12 [−0.06, 0.29] p = 0.272"
- New: ["Change in index instead of level","55","0.11 [−0.06, 0.29] p = 0.273"

**31. [F] content.js**

- Old: (moving-block bootstrap p = 0.203; Bonferroni p = 0.122)
- New: (moving-block bootstrap p = 0.203; Bonferroni p = 0.121)

**32. [A4/B10/C15] content.js**

- Old: A small Bayesian VAR in Brent crude, CPI inflation, the index, the median expectation and the repo rate (58 rounds, two lags) yields small responses of expectations to an index shock (Figure 6).
- New: A small Bayesian VAR in Brent crude, CPI inflation, the index, the median expectation and the repo rate (58 rounds from March 2016 to January 2026 enter; with two lags, 56 observations are used in estimation) yields small responses of expectations to an orthogonalised innovation in the index (Cholesky ordering, no structural interpretation; Figure 6). The VAR treats survey rounds as equally spaced, although the gap between rounds ranges from one to three months.

**33. [A4/B10] content.js**

- Old: Response of the one-year median expectation (pp) to a one-standard-deviation shock to the news index under two orderings (58 rounds, two lags).
- New: Response of the one-year median expectation (pp) to a one-standard-deviation orthogonalised innovation in the news index (Cholesky ordering, no structural interpretation) under two orderings (58 rounds, 56 observations after two lags).

**34. [B11] content.js**

- Old: ["h2","4.3 Media Attention and Household Expectations"]
- New: ["h2","4.3 Price-Theme Coverage and Household Expectations"]

**35. [B11] content.js**

- Old: Under the price-family index, one standard deviation of additional attention (0.77 percentage points of articles)
- New: Under the price-family index, one standard deviation of additional price-theme coverage (0.77 percentage points of articles)

**36. [D21] content.js**

- Old: The EWC interval and the bootstrap p-value come from different procedures, so an interval that excludes zero can coexist with p > 0.05; the decision statistic is the bootstrap p-value.
- New: (Section 3.5.3 explains why an EWC interval that excludes zero can coexist with p > 0.05.)

**37. [D21] content.js**

- Old: The correlations that pass are correlations between the levels of persistent series, which is a weak form of validation, and the Trends evidence rests on a single pull.
- New: The correlations that pass are weak validation for the reasons given in Section 5.2.

**38. [A3] content.js**

- Old: In a horse race with published CPI inflation, the salience-weighted measure shows no association with expectations (coefficient −0.006, 95% CI −0.019 to 0.007, p = 0.43, N = 54; Appendix Table F2).
- New: The *salience-weighted median* weights each item's year-on-year inflation by its search share over the previous three months (lagged one month), and the *absolute* measure weights each item by the absolute size of its own inflation rate. In a horse race with published CPI inflation, the salience-weighted measure shows no association with the change in current perceived inflation (coefficient −0.006, 95% CI −0.019 to 0.007, p = 0.43, N = 54; Appendix Table F2); this extension uses current perception, not the one-year expectation, as its outcome.

**39. [A3] content.js**

- Old: The language split is built from the baseline tag, since no price-family language split was constructed.
- New: The language split is built from the baseline tag and the 2018 core (99 outlets), since no price-family language split was constructed; Appendix Table F1 labels these rows accordingly.

**40. [A7/D19] content.js**

- Old: with no sign that one leads the other (Appendix Table F3);
- New: with no sign that one leads the other (Appendix Table F3, 105 months from January 2018, when the 2018 core starts);

**41. [D19/A2] content.js**

- Old: Monthly price-family attention has four identified peaks (Table 17 and Figure 10), the largest in April 2022 and April 2026. Peaks build up over one to three months and decay with half-lives of one to seven months; the baseline series gives peaks in June 2022 (half-life of nine months), March 2025 and April 2026. Excess attention during disinflation, defined in the analysis plan as attention above what CPI inflation predicts when inflation is falling, is not associated with expectations (0.29, −0.03 to 0.61; p = 0.18). With only 56 rounds, this null result is under-powered and therefore uninformative.
- New: Peaks are identified on the 3-month centred moving average of the monthly price-family series (Figure 10): a month is a *peak* if the average is in its top quartile and is the highest within six months on either side. *Months of rise* counts the months back to the last month at or below half-way between the peak and the lowest value in the preceding twelve months; the *half-life* counts the months forward until the average first falls back to that half-way level. The series has four peaks (Table 17), the largest in April 2022 and April 2026. Peaks build up over one to three months and decay with half-lives of one to seven months; the baseline series gives peaks in June 2022 (half-life of nine months), March 2025 and April 2026. *Excess attention during disinflation* is the standardised residual of a regression of the window index on real-time CPI inflation, set to zero in rounds in which real-time CPI inflation did not fall from the previous round; entered in equation (1), it is not associated with expectations (0.29, −0.03 to 0.61; p = 0.18). With only 56 rounds, this null result is under-powered and therefore uninformative.

**42. [A2/D20] content.js**

- Old: Blue line: monthly news index (price family, % of articles; left axis). Red line: CPI inflation (%, right axis). Dotted vertical lines mark the identified attention peaks.
- New: Dark blue: 3-month centred moving average of the monthly news index (price family, % of articles; left axis), the series used for the peaks in Table 17; light blue: the raw monthly series plotted in Figure 2. Red: CPI inflation (MoSPI, % y/y, right axis). Dotted vertical lines mark the identified peaks.

**43. [A2] content.js**

- Old: ["April 2026","6.75","1.78","3","4"]],""]
- New: ["April 2026","6.75","1.78","3","4"]],"Peaks, prior levels and durations are computed on the 3-month centred moving average of the monthly price-family series; the raw monthly series reaches 8.65% in March 2026."]

**44. [A2] content.js**

- Old: The Indian index shows the same rise in 2022 and the same persistence afterwards. That persistence is also one possible reason why the episode test fails here: when the general level of attention shifts, fixed percentile thresholds no longer pick out shorter, item-specific episodes.
- New: The Indian price-family series also rises in 2022 but only partly persists: its monthly mean is 2.10% of articles in 2016–21, 3.27% in 2022–23 and 2.92% in 2024–26, and the 3-month average falls back to about half-way within seven months of the April 2022 peak (Table 17). A higher post-2022 level is one possible reason why the episode test fails: when the general level of coverage shifts, fixed percentile thresholds pick out shorter, item-specific episodes less easily.

**45. [D20] content.js**

- Old: Window news index for English (blue) and Indian-language (red) core outlets, 2018 core, standardised.
- New: Window news index (baseline tag) for English (blue) and Indian-language (red) outlets of the 2018 core, standardised, estimation-sample rounds.

**46. [C14/C18] content.js**

- Old: First, there is no human validation: the audit relies on two passes of one language model, whose agreement shows the model's consistency with itself rather than its accuracy, and the later batches were coded from short excerpts.
- New: First, there is no human validation, and it remains the main limitation: no article was coded by a human, the audit relies on two passes of one language model, whose agreement shows the model's consistency with itself rather than its accuracy, and the later batches were coded from short excerpts of 200–300 characters, which hold fewer words in Indic scripts than in English, so the short-excerpt codes for Indian-language articles rest on less text.

**47. [D21] content.js**

- Old: Eighth, there are deviations from the analysis plan: the pump-price control was dropped for lack of data, one Trends pull was taken instead of three, the media-implied salience measure was not completed, and the English–Indian-language split exists only for the baseline tag.
- New: Eighth, the deviations from the analysis plan listed in Section 3.5.4 remain.

**48. [D21] content.js**

- Old: ["h3","3.5.4 Deviations from the Analysis Plan"],
["p","Two deviations are disclosed; all others are listed in Section 5.2. The planned retail pump-price control was dropped because no consistent series exists, so Brent crude enters only as a robustness check. In addition, the plan called for three Google Trends pulls, but only one was taken."],
- New: ["h3","3.5.4 Analysis Plan, Deviations and Sequence"],
["p","The analysis plan (17 November 2026, recorded hash, not publicly registered) fixed the design, the primary cell, the validation tests and the switching rule before any outcome regression. Four deviations are disclosed here and only referred to elsewhere: the planned retail pump-price control was dropped because no consistent series exists, so Brent crude enters only as a robustness check; one Google Trends pull was taken instead of three; the media-implied salience measure was constructed but its precision check was not completed; and the English–Indian-language split exists only for the baseline tag. The sequence of the analysis is also disclosed: the first outcome regressions used the baseline tag and were run before the audit was complete; the audit then selected the price family under the rule fixed in the plan, and the analysis was re-estimated with it. Because the switch followed a rule that did not depend on the regression results, and both definitions are reported throughout, this sequence does not allow the definition to be chosen for its results, but the baseline results were seen first. The checks in Table 12 were added in review, after the primary result was seen."],

**49. [D21] content.js**

- Old: ["h3","4.3.10 Sequence of the Analysis"],
["p","The analysis plan was fixed before any outcome regression was estimated, but the first outcome regressions used the baseline tag and were run before the audit was complete. The audit then selected the price family under the rule fixed in the plan, and the analysis was re-estimated with it. Because the switch followed a rule that did not depend on the regression results, and because both definitions are reported throughout, this sequence does not allow the definition to be chosen for its results. Nevertheless, the reader should know that the baseline results were seen first."],
- New: (removed)

**50. [D21] content.js**

- Old: Fourth, the audit's excerpt length changed
- New: Fourth, the deviations and the order of the analysis are disclosed in Section 3.5.4; the audit's excerpt length changed

**51. [D21] content.js**

- Old: However, GDELT's inflation tag captures many articles that are not about consumer prices and misses most that are; the index does not reproduce known price episodes; and its aggregate association with household inflation expectations is small, sensitive to the choice of controls, at the margin of what the sample can detect, short of the 5% significance level absent out of sample, and concentrated in the years before 2022. The evidence on expectations is therefore exploratory.
- New: The tag is imprecise, the index does not reproduce known price episodes, and its association with household expectations is small, fragile and concentrated before 2022, for the reasons set out in Section 5.2; the evidence on expectations is exploratory.

**52. [D21] content.js**

- Old: Further extensions include a supervised classifier in place of dictionary-based theme tags, alternative window lengths, controls for the exchange rate and retail fuel prices, item-level coverage measures for food and fuel, and a Trends comparison based on three independent pulls.
- New: Further extensions include a supervised classifier in place of dictionary-based theme tags, item-level coverage measures for food and fuel, a regional panel of outlets matched to survey cities, retail fuel-price controls, and a Trends comparison based on three independent pulls.

**53. [E24] content.js**

- Old: "Banerjee, A., Kanodia, A., & Ray, P. (2021).
- New: "Ash, E., & Hansen, S. (2023). Text algorithms in economics. *Annual Review of Economics*, 15, 659–688. https://doi.org/10.1146/annurev-economics-082222-074352",
"Baker, S. R., Bloom, N., & Davis, S. J. (2016). Measuring economic policy uncertainty. *Quarterly Journal of Economics*, 131(4), 1593–1636. https://doi.org/10.1093/qje/qjw024",
"Banerjee, A., Kanodia, A., & Ray, P. (2021).

**54. [F30] content.js**

- Old: "Coibion, O., Gorodnichenko, Y., & Weber, M. (2022). Monetary policy communications and their effects on household inflation expectations. *Journal of Political Economy*, 130(6), 1537–1584.",
"Coibion, O., Gorodnichenko, Y., & Kamdar, R. (2018). The formation of expectations, inflation, and the Phillips curve. *Journal of Economic Literature*, 56(4), 1447–1491.",
- New: "Coibion, O., Gorodnichenko, Y., & Kamdar, R. (2018). The formation of expectations, inflation, and the Phillips curve. *Journal of Economic Literature*, 56(4), 1447–1491.",
"Coibion, O., Gorodnichenko, Y., & Weber, M. (2022). Monetary policy communications and their effects on household inflation expectations. *Journal of Political Economy*, 130(6), 1537–1584.",

**55. [E24] content.js**

- Old: "D'Acunto, F., Malmendier, U.,
- New: "Das, A., Lahiri, K., & Zhao, Y. (2019). Inflation expectations in India: Learning from household tendency surveys. *International Journal of Forecasting*, 35(3), 980–993. https://doi.org/10.1016/j.ijforecast.2019.03.007",
"D'Acunto, F., Malmendier, U.,

**56. [E24] content.js**

- Old: "GDELT Project (2015).
- New: "Dräger, L. (2015). Inflation perceptions and expectations in Sweden – Are media reports the missing link? *Oxford Bulletin of Economics and Statistics*, 77(5), 681–700.",
"GDELT Project (2015).

**57. [E24] content.js**

- Old: "Pattanaik, S., Muduli, S.,
- New: "Nimark, K. P., & Pitschner, S. (2019). News media and delegated information choice. *Journal of Economic Theory*, 181, 160–196. https://doi.org/10.1016/j.jet.2019.02.001",
"Pattanaik, S., Muduli, S.,

**58. [E24] content.js**

- Old: "Pratap, B., Ranjan, A.,
- New: "Pfajfar, D., & Santoro, E. (2013). News on inflation and the epidemiology of inflation expectations. *Journal of Money, Credit and Banking*, 45(6), 1045–1067. https://doi.org/10.1111/jmcb.12043",
"Pratap, B., Ranjan, A.,

**59. [F30] content.js**

- Old: "GDELT Project (2015). The GDELT Global Knowledge Graph (GKG) data format codebook, version 2.1. http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf",
- New: "GDELT Project (2015). The GDELT Global Knowledge Graph (GKG) data format codebook, version 2.1. data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf",

**60. [C12/C13/C15/C17] content.js**

- Old: ["Balanced: 44 outlets present in every regression window","56","0.346","(0.157, 0.536)","0.008"]]
- New: ["Balanced: 44 outlets present in every regression window","56","0.346","(0.157, 0.536)","0.008"],["Outlets de-duplicated, lifestyle domains dropped (89 outlets)","56","0.264","(0.053, 0.474)","0.090"],["Non-energy price family","56","0.314","(0.012, 0.616)","0.042"],["No lagged dependent variable","57","0.175","(−0.122, 0.473)","0.233"],["Months between rounds added","56","0.339","(0.125, 0.553)","0.031"],["Outcome per two months (divided by the months between rounds)","56","0.243","(0.020, 0.466)","0.102"],["Intra-window Brent and INR/USD changes added","56","0.269","(0.104, 0.435)","0.045"]]

**61. [C12/C13/C15/C17] content.js**

- Old: their indices correlate at 0.96 and 0.94 with the 14-day index."],
- New: their indices correlate at 0.96 and 0.94 with the 14-day index. De-duplicated outlets: the five economictimes.indiatimes.com subdomains and haryana.punjabkesari.in are pooled with their parent outlet in the same language, and nine lifestyle and entertainment domains are dropped (bollywoodhungama.com, bollywoodtadka.in, cinema.dinamalar.com, cinema.vikatan.com, desimartini.com, femina.in, food.ndtv.com, temple.dinamalar.com, vogue.in); the index correlates at 0.97 with the published one. Non-energy price family: price-family articles carrying ECON_INFLATION, WB_442_INFLATION, ECON_COST_OF_LIVING, a price-control code or a price-gouging code; fuel, oil, electricity, gas, transport and price-subsidy codes are excluded (mean 1.21% of articles; correlation 0.72 with the price family). Months between rounds range from one to three (median 2.0). Intra-window market changes are log changes from the first to the last trading day of the 14-day window."],

**62. [C12/C13/C15/C17] content.js**

- Old: These composition checks are reported for completeness and are not used to claim significance, since they were chosen after the primary result was seen;
- New: Six further checks added in this revision are in the lower rows of Table 12. Pooling subdomains of the same outlet and dropping lifestyle and entertainment domains leaves 89 outlets and gives 0.26 (p = 0.090). An index that keeps only the non-energy price codes gives 0.31 (p = 0.042). Dropping the lagged dependent variable gives 0.18 (p = 0.233, N = 57); controlling for the months between rounds gives 0.34 (p = 0.031), and dividing the outcome by that gap gives 0.24 (p = 0.102). Adding the changes in Brent and the rupee–dollar rate within the 14-day window gives 0.27 (p = 0.045). These composition and specification checks are reported for completeness and are not used to claim significance, since they were chosen after the primary result was seen;

**63. [C13] content.js**

- Old: Its confidence intervals overlap those of the baseline, so the choice reflects the pre-specified rule rather than a clear statistical ranking.
- New: Its confidence intervals overlap those of the baseline, so the choice reflects the pre-specified rule rather than a clear statistical ranking. A non-energy version of the price family (Table 12) cannot be distinguished from the baseline in the audit: every sampled article it tags also carries ECON_INFLATION, and the 32 sampled articles tagged only by the price family carry only fuel, energy, transport or subsidy codes, so its audit precision and recall equal the baseline's (0.16 and 0.30).

**64. [C12/C16] content.js**

- Old: the equal outlet weights do not reflect readership;
- New: the equal outlet weights do not reflect readership, and the core counts subdomains of one outlet separately and includes some lifestyle and entertainment domains (pooling and dropping them changes the primary estimate from 0.25 to 0.26, p = 0.090; Table 12); the index does not separate rising from falling prices, and GDELT tone cannot stand in for direction: among relevant audited articles (79 rising, 26 falling), those coded falling have a lower mean tone than those coded rising (−2.42 against −1.17; Mann–Whitney p = 0.079);

**65. [C17] content.js**

- Old: Further extensions include a supervised classifier in place of dictionary-based theme tags,
- New: Further extensions include a supervised classifier in place of dictionary-based theme tags, separate indices for rising and falling prices built from human direction codes,

**66. [F31] content.js**

- Old: Sections 4.3.2–4.3.8 and Appendix E report 107 estimated coefficients or test statistics: 20 in Table 11, 14 in Table 12,
- New: Sections 4.3.2–4.3.8 and Appendix E report 113 estimated coefficients or test statistics: 20 in Table 11, 20 in Table 12,

**67. [F25] content.js**

- Old: "0.78 (0.65, 0.90)","0.55 (0.31, 0.75)","–"]
- New: "0.78 (0.65, 0.90)","0.55 (0.31, 0.75)","—"]

**68. [F25] content.js**

- Old: "0.67","0.41","–"]
- New: "0.67","0.41","—"]

**69. [F25] content.js**

- Old: ["Correlation with GDELT DOC keyword series","–","0.78","–"]
- New: ["Correlation with GDELT DOC keyword series","—","0.78","—"]

**70. [F25] content.js**

- Old: ["Correlation with GDELT DOC theme series","–","0.77","–"]
- New: ["Correlation with GDELT DOC theme series","—","0.77","—"]

**71. [F25] content.js**

- Old: "0.30 [0.09, 0.51] p = 0.023","–"]
- New: "0.30 [0.09, 0.51] p = 0.023","—"]

**72. [F25] content.js**

- Old: "0.28 [0.10, 0.46] p = 0.031","–"]
- New: "0.28 [0.10, 0.46] p = 0.031","—"]

**73. [F25] content.js**

- Old: "0.34 [0.15, 0.53] p = 0.010","–"]
- New: "0.34 [0.15, 0.53] p = 0.010","—"]

**74. [F25] content.js**

- Old: "0.09 [−0.20, 0.39] p = 0.50","–"]
- New: "0.09 [−0.20, 0.39] p = 0.50","—"]

**75. [F25] content.js**

- Old: Construction variants of the baseline index are reported in Appendix Table E1."],
- New: Construction variants of the baseline index are reported in Appendix Table E1. \"—\": not computed."],

**76. [F25] content.js**

- Old: The DOC comparison was computed for the price-family series only."],
- New: The DOC comparison was computed for the price-family series only. \"—\": not computed."],

**77. [D22] content.js**

- Old: (Appendix Table E5)
- New: (Appendix Table E4)

**78. [D22] appendix.js**

- Old: ["h2","E.4 Outlet Composition"],
["table","Table E5. Core outlets
- New: ["h2","E.4 Outlet Composition"],
["table","Table E4. Core outlets

**79. [F29] content.js**

- Old: obtained from the data service of the Ministry of Statistics and Programme Implementation,
- New: obtained from the data service of the Ministry of Statistics and Programme Implementation (MoSPI),

**80. [F29] content.js**

- Old: CPI data from the Ministry of Statistics and Programme Implementation;
- New: CPI data from MoSPI;

**81. [A3] appendix.js**

- Old: ["Price family","English index alone (one-year median)"
- New: ["Baseline, 2018 core","English index alone (one-year median)"

**82. [A3] appendix.js**

- Old: ["Price family","Indian-language index alone (one-year median)"
- New: ["Baseline, 2018 core","Indian-language index alone (one-year median)"

**83. [A3] appendix.js**

- Old: ["Price family","Indian-language index with English control"
- New: ["Baseline, 2018 core","Indian-language index with English control"

**84. [A3] appendix.js**

- Old: ["Price family","English index alone (current perception)"
- New: ["Baseline, 2018 core","English index alone (current perception)"

**85. [A3] appendix.js**

- Old: ["Price family","Indian-language index alone (current perception)"
- New: ["Baseline, 2018 core","Indian-language index alone (current perception)"

**86. [A3] appendix.js**

- Old: ["Price family","Indian-language with English control (current perception)"
- New: ["Baseline, 2018 core","Indian-language with English control (current perception)"

**87. [A3] appendix.js**

- Old: Reported for completeness; the international-framing regressions are not interpreted because the audit agreement condition was not met.
- New: Reported for completeness; the international-framing regressions are not interpreted because the audit agreement condition was not met. The English and Indian-language series use the baseline tag and the 2018 core (99 outlets).

**88. [A3/E3] appendix.js**

- Old: Table F2. Salience-weighted inflation: horse race with published CPI (one-year median, h = 0; search-implied version)
- New: Table F2. Salience-weighted inflation: horse race with published CPI (outcome: change in current perceived inflation, median; search-implied version)

**89. [A7] appendix.js**

- Old: A positive lag means the Indian-language series moves later.
- New: A positive lag means the Indian-language series moves later. N is 105 rather than 129 because the language series use the 2018 core and start in January 2018; N falls by one per month of lead or lag.

**90. [F25] appendix.js**

- Old: ["Apr 2026","2.76","1.06","3","–"]],""]
- New: ["Apr 2026","2.76","1.06","3","—"]],"Computed on the 3-month centred moving average of the monthly baseline series. The half-life for April 2026 is right-censored: the series had not fallen back to the half-way level by the end of the sample (\"—\")."]

**91. [F25] appendix.js**

- Old: Bootstrap p-values were not computed for the leave-one-out rows."]
- New: Bootstrap p-values were not computed for the leave-one-out rows (\"—\")."]

**92. [F26] appendix.js**

- Old: const rounds = `
- New: const rounds = `

**93. [B11] content.js**

- Old: a measurement: a scripted, reproducible index of media attention to inflation for India,
- New: a measurement: a scripted, reproducible index of GDELT price-theme coverage for India, a noisy proxy for media attention to inflation,

**94. [B11] content.js**

- Old: "Figure 8: English and Indian-Language Media Attention"
- New: "Figure 8: English and Indian-Language Price-Theme Coverage"

**95. [B11] content.js**

- Old: ["h3","4.4.2 English versus Indian-Language Attention"]
- New: ["h3","4.4.2 English versus Indian-Language Coverage"]

**96. [B11] content.js**

- Old: ["h2","5.1 What an Attention Index Can Offer a Central Bank"]
- New: ["h2","5.1 What a Coverage Index Can Offer a Central Bank"]

**97. [B11] content.js**

- Old: An attention index measures how much of the news flow concerns prices,
- New: A price-theme coverage index measures how much of the news flow GDELT tags as concerning prices,

**98. [NUM (found by r3_numcheck)] content.js**

- Old: ["Core at 60% presence (180 outlets)","56","0.30 [0.09, 0.51] p = 0.023"
- New: ["Core at 60% presence (180 outlets)","56","0.30 [0.09, 0.50] p = 0.023"

**99. [NUM (found by r3_numcheck)] content.js**

- Old: ["AR(1)","Baseline","1.17","(0.92, 1.60)"
- New: ["AR(1)","Baseline","1.16","(0.92, 1.60)"

**100. [NUM (found by r3_numcheck)] content.js**

- Old: "0.34 [0.15, 0.53] p = 0.010"
- New: "0.34 [0.15, 0.53] p = 0.011"

**101. [NUM (found by r3_numcheck)] content.js**

- Old: with bootstrap p-values between 0.010 and 0.031.
- New: with bootstrap p-values between 0.011 and 0.031.

**102. [NUM (found by r3_numcheck)] content.js**

- Old: "0.33 [0.02, 0.64] p = 0.036"
- New: "0.33 [0.02, 0.64] p = 0.037"

**103. [NUM (found by r3_numcheck)] content.js**

- Old: the same cell gives 0.33 (0.02 to 0.64; p = 0.036).
- New: the same cell gives 0.33 (0.02 to 0.64; p = 0.037).

**104. [NUM (found by r3_numcheck)] content.js**

- Old: (0.036 under the rejected baseline)
- New: (0.037 under the rejected baseline)

**105. [NUM (found by r3_numcheck)] content.js**

- Old: 0.058, 0.054, 0.146 and 0.108
- New: 0.058, 0.054, 0.147 and 0.108

**106. [NUM (found by r3_numcheck)] content.js**

- Old: ["Index × (lagged CPI > 6%)","0.18","(0.06, 0.30)","0.015"]
- New: ["Index × (lagged CPI > 6%)","0.18","(0.06, 0.30)","0.016"]

**107. [NUM (found by r3_numcheck)] content.js**

- Old: the interaction coefficient is 0.18 (p = 0.015).
- New: the interaction coefficient is 0.18 (p = 0.016).

**108. [NUM (found by r3_numcheck)] appendix.js**

- Old: ["Index × High","56","0.179","(0.057, 0.301)","0.015"]
- New: ["Index × High","56","0.179","(0.057, 0.301)","0.016"]

**109. [NUM (found by r3_numcheck)] appendix.js**

- Old: ["Wire-copy filter","56","0.325","(0.009, 0.641)","0.036"]
- New: ["Wire-copy filter","56","0.325","(0.009, 0.641)","0.037"]

**110. [NUM (found by r3_numcheck)] appendix.js**

- Old: "47","0.282","(−0.015, 0.579)","0.071"]
- New: "47","0.282","(−0.015, 0.579)","0.072"]

**111. [NUM (found by r3_numcheck)] appendix.js**

- Old: "Indian-language index with English control","56","0.206","(−0.048, 0.460)","0.089"]
- New: "Indian-language index with English control","56","0.206","(−0.048, 0.460)","0.090"]

**112. [NUM (found by r3_numcheck)] appendix.js**

- Old: "English index alone (current perception)","56","0.157","(0.012, 0.303)","0.107"]
- New: "English index alone (current perception)","56","0.157","(0.012, 0.303)","0.108"]

**113. [NUM (found by r3_numcheck)] appendix.js**

- Old: "International share alongside index","56","−0.053","(−0.285, 0.179)","0.669"]
- New: "International share alongside index","56","−0.053","(−0.285, 0.179)","0.670"]

**114. [NUM (found by r3_numcheck)] appendix.js**

- Old: "Excess attention during disinflation","56","0.291","(−0.027, 0.610)","0.184"]
- New: "Excess attention during disinflation","56","0.291","(−0.027, 0.610)","0.185"]

**115. [NUM (found by r3_numcheck)] appendix.js**

- Old: "Excess attention during disinflation","56","0.258","(−0.162, 0.678)","0.246"]
- New: "Excess attention during disinflation","56","0.258","(−0.162, 0.678)","0.247"]

**116. [NUM (found by r3_numcheck)] appendix.js**

- Old: "54","−0.006","(−0.019, 0.007)","0.428"]
- New: "54","−0.006","(−0.019, 0.007)","0.429"]

Additionally (applied by script, not one-by-one): appendix.js "–" → "—" in 7 uncomputed table cells (Table E2 p column, Table F4) and in 57 Mode cells of Table C1; regenerated figures e5_ipi_cpi_peaks_c.png and e2_eng_ver_c.png.
