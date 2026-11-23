# FINAL TOUCHES: full-length paper (24 Nov 2026)

Reviews: Claude Opus (this document's author) and Claude Sonnet (Part 5). Apply everything below to
`10_OUTPUTS/paper/paper_draft.md` and save the result as `10_OUTPUTS/paper/paper_full.md`. Keep the short version.
Every number must be read from the result files; do not retype numbers from memory.

## Part 0. User decisions (24 Nov)
- The paper becomes **FULL-LENGTH (target 30–40 pages including appendices)**. Include every result, table, figure and
  method detail. The short 9-page version stays as `paper_short.md` / `paper_short.pdf`.
- **Remove all progress/pipeline links from the paper**: no `PROGRESS.md`, no file paths, no D-numbers, no "Gate",
  no "PENDING", no "[title to be checked]", no hashes. Replace them with one Data and Code Availability statement that
  points to the GitHub repository.
- Title page date: "24 November 2026". Drop "(draft for review)".

## Part 1. Errors and inconsistencies (Opus review)
1. **Wrong cross-reference.** The Introduction says the order-of-work issue is discussed in "Section 6"; it is in
   Limitations (Section 7, item 4). Fix, or add a short subsection in Results.
2. **SD of the index is inconsistent.** Section 6 says "one SD (0.77 pp)"; Table 1 says SD 0.69 (estimation sample,
   N = 56). State which sample the standardisation uses (it is the full panel of rounds in phase1.py) and say so in a
   table note.
3. **Units.** The window index is in % of articles; the monthly series is written as "0.031 of articles". Use % throughout
   (3.1%).
4. **Abstract: "104 outlets" versus 714 panel outlets.** Say: "a balanced core of 104 outlets (54 vernacular) drawn from
   a panel of 714 Indian domains".
5. **Table 2, baseline column gaps:** "Change in index 0.15" has no CI or p; "Outcome: mean 0.25 p≈0.07" needs the
   exact CI and p. Fill both from results/d19_national_lp.csv.
6. **EWC and bootstrap disagree in places** (e.g. horse race: CI 0.04–0.43, which excludes zero, but p = 0.092). Add one
   sentence in Specification: the intervals are EWC fixed-b, the p-values are wild-bootstrap, and the two can disagree in
   small samples; the bootstrap p is the decision statistic.
7. **The audit kappa n is missing.** Direction and cause kappa were computed on n = 118 (relevant articles coded in
   both passes). State it.
8. **Results computed but not reported anywhere in the paper; add them (Results or appendix):**
   - small Bayesian VAR impulse responses (results/d21_bvar_irf.csv), two orderings;
   - monthly local projections of the index on CPI surprises and Brent shocks (d23_monthly_lp.csv);
   - persistence tests, ADF/KPSS for the index and expectations (d19_persistence.csv);
   - **audit: the unscreened non-economic stratum** (1 of 87 relevant; exact CI 0.000–0.062; recall floor 0.042);
   - **audit: the URL-slug fallback** (137 articles; precision 0.13, recall 0.56, F2 0.34; uninformative-slug share 0.069);
   - audit: retrieval by stratum and period (gate_report.md table; the lowest is "flagged, old" at 0.74);
   - audit: precision, recall and F2 for **every** variant (metrics_prf.csv), not only the winner;
   - D20 leave-one-episode-out rows;
   - Trends: the "mehngai"/"महंगाई" rows and partial correlations (d17_summary.md);
   - the placebo dates and the episode table (z-scores);
   - E1 exposure table by city (e1_exposure_table.csv);
   - E3 horse race (e3_horse_race.csv) and E5 peak table (e5_peaks.csv).
9. **References: corrected from primary sources (use exactly these):**
   - Aarab, I., Bańbura, M., Bobeica, E. and Leguay, E. (2025). Monitoring attention to inflation in the news. *ECB Economic Bulletin*, Issue 6/2025, Box 5.
   - Arndt, S. (2024). Different Newspapers – Different Inflation Perceptions. AWI Discussion Paper Series No. 748, Heidelberg University. doi:10.11588/heidok.00034992. (Drop the "2026" item unless a separate citable version exists.)
   - Banerjee, **A.**, Kanodia, A. and Ray, P. (2021). Deciphering Indian inflationary expectations through text mining: an exploratory approach. *Indian Economic Review* 56, 49–66. (Earlier version: IIM Calcutta WPS No. 830, July 2019.) **The draft's initial "S." is wrong.**
   - Kishor, N. K. and Pratap, B. (2023). The Role of Inflation Targeting in Anchoring Long-Run Inflation Expectations: Evidence from India. MPRA Paper No. 118951.
   - Pratap, B., Ranjan, A., Kishore, V. and Bhoi, B. B. (2021). Forecasting Food Inflation using News-based Sentiment Indicators. *Reserve Bank of India Occasional Papers* 42(2) (published October 2022).
   - Ruhi, A., Sharma, K. and Sankaran, S. (2025). Household Inflation Expectations in India: Emerging Trends, Determinants and Impact of Monetary Policy. *RBI Bulletin*, July 2025.
   - Add: Pattanaik, S., Muduli, S. and Ray, S. (2019). Inflation Expectations of Households: Do They Influence Wage-Price Dynamics in India? RBI Working Paper Series No. 01/2019.
   - Add, verifying each against its source before citing: Coibion, Gorodnichenko and Kamdar (2018, JEL) on survey expectations; the EWC/fixed-b inference papers (Lazarus, Lewis, Stock and Watson 2018, JBES); Clark and West (2007, J. Econometrics); Jordà (2005, AER) for local projections.
10. **Required disclosure: AI use.** Add an "AI use statement":
    - article relevance coding was done by a large language model (Claude), in two passes, with no human coding;
    - the code, analysis and drafting were assisted by AI tools (Claude);
    - the author designed the study, made every methodological ruling, and is responsible for the content.

    Check your institution's or journal's policy on AI disclosure.
11. **Data and code availability:** one paragraph naming the GitHub repository and listing the public sources (GDELT
    GKG via BigQuery, RBI IESH, MoSPI CPI API, RBI press releases, FRED, Google Trends). State that article texts are not
    redistributed.
12. **Pre-registration wording.** Say "analysis plan fixed before outcome regressions (dated, hashed)". Never say
    "pre-registered" without a registry.

## Part 2. Full-length structure (target 30–40 pages)
1. **Abstract** (≤ 250 words). **Keywords and JEL** (E31, E58, C55, C81, D84).
2. **Introduction** (2–3 pp): motivation, the gap for India, three contributions, preview of findings, roadmap.
3. **Related literature** (3–4 pp, its own section):
   - (a) household expectations and information: Carroll; Coibion et al.; Lamla & Lein; Larsen et al.; Arndt; ECB 2025;
   - (b) news-based inflation measures for India: Banerjee et al.; Pratap et al.; Kishor & Pratap;
   - (c) the IESH literature: Pattanaik et al.; Ruhi et al.;
   - (d) GDELT as a research source, and its known limitations.
4. **Institutional background** (1–2 pp): India's inflation targeting since 2016 (the 4% ± 2% target); the IESH design
   (19 cities, about 6,000 households, bimonthly since 2016, binned responses, the telephone rounds of 2020–21); the
   inflation episodes of 2016–2026.
5. **Data** (4–5 pp):
   - 5.1 GDELT GKG: extraction, sampling design (windows plus the 1-in-4 grid), budget, the GDELT outage, the integrity recount;
   - 5.2 outlet panel: domain filter, review of the 81 ambiguous domains, the balanced core, language mix (table);
   - 5.3 IESH, including the fieldwork-date rule for pre-2020 rounds;
   - 5.4 CPI, repo rate, markets;
   - 5.5 Google Trends and the GDELT DOC API;
   - 5.6 sample flow (flow table 67 → 63 → 62 → 61 → 57 → 56 → 37).
6. **Constructing the index** (3–4 pp): the article-share definition; the baseline and price-family theme lists (full
   table of theme codes, in the appendix); validity rules; reliability; construction variants and their correlation
   table; the monthly series; Figure 1 plus a figure of the monthly series.
7. **Auditing GDELT's inflation tags** (4–5 pp):
   - sample design (strata table);
   - retrieval (live versus Wayback, by stratum and period);
   - codebook summary;
   - LLM coding protocol, excerpt lengths, and the two passes with their agreement;
   - precision, recall and F2 for every variant (table);
   - vernacular versus English recall;
   - the unscreened stratum; the slug fallback;
   - what the tags pick up (examples of the false-positive types, described in words, without reproducing article text);
   - the switch rule and its outcome.
8. **External validation** (2–3 pp): Trends correlations (all three terms, raw, detrended and partial); the DOC
   comparison; the episode table; placebos; why the 2022 shift raises thresholds; caveats.
9. **Empirical specification** (2 pp): the equation written in LaTeX-style math; controls; real-time CPI timing;
   inference (EWC fixed-b, wild bootstrap); the primary cell; the order of work.
10. **Results** (6–8 pp):
    - 10.1 primary estimate;
    - 10.2 robustness (Table 2 completed for both definitions, plus the coefficient plot);
    - 10.3 horizons and outcomes;
    - 10.4 horse race with search;
    - 10.5 state dependence (D20, including leave-one-episode-out);
    - 10.6 VAR impulse responses;
    - 10.7 out-of-sample forecasts (both benchmarks; forecast-error figure);
    - 10.8 what drives the index (monthly local projections on CPI surprises and Brent shocks);
    - 10.9 persistence;
    - 10.10 multiple testing.
11. **Extensions** (5–6 pp, each with its own subsection, table or figure, and stated gate status):
    - E1 city exposure, with a city table (why it fails);
    - E2 English vs vernacular, with figure and lead–lag table, framed as a measurement result;
    - E3 salience basket, with item mapping table and horse race;
    - E4 international framing (κ fails);
    - E5 attention cycle, with peak table, figure and the excess-attention result.
12. **Discussion** (1–2 pp): what an attention index can and cannot tell a central bank; comparison with the ECB 2025
    attention index; implications for using GDELT on Indian or vernacular press.
13. **Limitations** (expand the current 7 items), **Conclusion**, **AI use statement**, **Data and code availability**,
    **References**.
14. **Appendices:**
    - A: full theme lists and flag families;
    - B: outlet panel (core list, language counts);
    - C: IESH round table (round, fieldwork dates, date rule);
    - D: audit codebook summary and strata weights;
    - E: all robustness tables;
    - F: extension tables;
    - G: reproducibility (pipeline overview diagram, budget, integrity checks, rerun check).

## Part 3. Tables and figures checklist
- **Tables:** 1 descriptives; 2 sample flow; 3 outlet panel by language; 4 theme definitions; 5 audit strata and
  retrieval; 6 precision/recall/F2 by variant; 7 external validation; 8 main and robustness results; 9 horse race and
  state dependence; 10 forecast evaluation; 11–15 extensions.
- **Figures:** 1 index vs expectations and CPI; 2 monthly index with episode shading; 3 coefficient plot; 4 horizon
  profile; 5 VAR IRFs; 6 forecast errors; 7 E2 English vs vernacular; 8 E4; 9 E5 peaks; 10 E3 items; 11 audit
  precision/recall by variant (bar chart).
- Every figure gets a caption with its source, sample and units. Embed figures in the PDF.

## Part 4. Process
1. Write `paper_full.md` section by section, filling every number from the result files.
2. Export to PDF (pandoc), with a table of contents, numbered sections, and figures embedded.
3. Run a consistency script that extracts every number in the abstract and Results and compares it with the result
   files; fix any mismatch.
4. Commit and push after each major section and at the end.
5. Do not change any estimate, flag or specification. This pass is presentation, completeness and correctness only.

## Part 5. Sonnet review: additional errors (verify each against results_switched/ before fixing)
Sonnet verified every baseline number against the result files (all match). It could not see results_switched/, so
check each price-family number there.

**Errors**
1. **"0.78 with GDELT's own keyword-based DOC series" (§4.2) looks unsupported:** d17_summary.md says the DOC series was
   not available, and 0.777 is the baseline-vs-Trends correlation. Delete it, or substantiate it from a DOC result file.
2. **Abstract "r = 0.54 to 0.78 across theme definitions"** mixes price family (0.54) and baseline (0.78). Label each,
   and add that the Hindi-term correlations fail.
3. **"Hindi terms 0.11 to 0.36"** is not reproducible from the baseline file: raw 0.257 (mehngai), 0.302 (Devanagari),
   0.113 post-trend. State which definition and which statistic.
4. **"At longer horizons the estimates alternate in sign (h=1: 0.08; h=2: 0.26; h=3: 0.00)":** none is negative, so
   there is no sign alternation. Rewrite as "smaller and imprecise".
5. **"Starts after 20 rounds and evaluates 37 forecasts"** while 56 − 20 = 36. Reconcile from d22_predictions.csv.
6. **Binned medians vs Table 1 values (9.75, 7.90, 12.66):** the published median is interpolated within bins. Explain,
   and drop or rephrase the "probability the median moves up a bin" reading.
7. **Monthly "peak 0.031 in June 2022"** is the baseline monthly value, but it sits in price-family context. Label it.
8. **Rounding:** "0.015 to 0.64" in the text vs [0.02, 0.64] in Table 2. Use one rounding.
9. **Brent** is listed as a control but is absent from the specification and Table 1, and the planned pump-price
   control was dropped (no data). Disclose both deviations.
10. **Aarab (2025) and Arndt (2024) are listed but never cited in the text.** Cite them in the literature section.
11. **"Bilingual" (conclusion)** is wrong: it is English plus several vernaculars ("multilingual").
12. **Extensions use the baseline tag** while the primary index is price family, and the rerun check did not cover the
    extensions or the switch. Rerun E2–E5 under price family (keep baseline versions in the appendix) and rerun the
    reproducibility check to cover them.

**Overclaims: soften these**
- Split-half r = 0.89 shows reliability, not validity.
- κ = 1.00 between two passes of one model shows non-independence. State n = 118 for direction and cause.
- "Machine translation tags vernacular stories more readily" is a hypothesis; say "differential theme recall,
  possibly related to machine translation".
- "Attention rose after 2022 ... raises the threshold" is untested; label it as a possible explanation.
- "For every definition we tried" covers only price family and strict.
- "The news index carries information that search does not" rests on p = 0.092 and a single Trends pull. Weaken it.
- E4 is reported as a regression although its gate (D25) says no regression claims. Make it descriptive only.
- E4 and E5 nulls are underpowered; say so.
- "Most tagged articles are market/corporate/foreign stories" needs a table of false-positive categories with counts,
  or remove it.
- "Existing measures use a handful of English dailies" and "rarely checked" need citations.
- Verify the attribution to Ruhi et al. about media exposure before quoting it. (An earlier check found a footnote
  saying the IESH does not capture media exposure; confirm the wording in the PDF.)
- Headline p = 0.058 misses 5%. The title, abstract and conclusion should say the evidence is "exploratory" and that
  the primary estimate does not clear the 5% level.

**Artefacts to remove** (on top of Part 0): the two figure links into the pipeline folders (copy the figures into
10_OUTPUTS/paper/figures/ and link there); all Appendix B paths; "By the author's ruling" (say "by design");
"the plan" (define it once as "the analysis plan, dated 17 Nov 2026"); "At the time of writing"; "(draft for review)".
Do not copy stale phrases from upstream files ("PENDING audit gate", "PROVISIONAL", "DOC series not yet available").

**Missing items a referee would demand.** Do the cheap ones; list the rest as limitations or future work.
- Do: price-family precision and recall with CI (not only F2); precision and recall split by early (long-excerpt) vs
  late (short-excerpt) batches; state the recall weighting and the missing-at-random assumption.
- Do: robustness excluding the 2024 election-peak window; a placebo-outcome test (e.g. lagged expectations);
  sensitivity to equal weights vs volume weights and to the 80% presence threshold (60%/90%); a minimum-detectable-effect
  statement for N = 56.
- Do: report how many tests were run; optionally Romano–Wolf adjusted p-values for the main robustness family.
- Do: a coverage statement (missing July 2025 round; phone rounds of 2020–21).
- Limitation or future work: a human-coded subsample (≥ 100 articles), three Trends pulls, a comparison with existing
  Indian CPI-news indices and an EPU-style benchmark.
