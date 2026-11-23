# Review of design_v3 (round 3, reviewer)

Scope: every decision in design_v3.md, including the REMOVED D28.2. I read brief.md, sources_summary.md, design_v3.md and response_v2.md. Web checks this round are marked [V-R3].

- **IESH city tables** [V-R3]: the July 2026 release (RBI PublicationsView id=24077) has city-wise mean and median, with standard errors, for current perception, 3-month and 1-year expectations. It gives one fieldwork range for the whole survey (11–20 July 2026) and covers 19 cities with 5,905 responses. It does **not** publish city-level response counts.
- **Web News NGrams 3.0** [V-R3]: GDELT blog posts describe per-minute JSON files from 1 Jan 2020, also in BigQuery as `gdelt-bq.gdeltv2.webngrams`. Each record is one token with about 7 words of context before and after, plus the URL. GDELT warns that a few dates can need tens to hundreds of GB of bandwidth, or can exhaust the free BigQuery quota. The blog says nothing about full-text reconstruction.
- I tried to read the GKG table metadata with `bq` to check F, but there were no credentials. F stays unverified, so the dry-run ladder matters even more.

Standard applied: ACCEPT when the choice is sound and its residual risk sits behind a stated gate, fallback or wording rule. REVISE only for a real error, an infeasible step, or a claim the design cannot support.

---

## A. Data

**D1 — ACCEPT.** The column logic is right: billed bytes depend on columns times partitions, and the `SourceCommonName` filter saves nothing. Not deduplicating non-window days is acceptable because the window-day comparison with and without deduplication bounds the effect. That comparison is honest about one point: duplicate rates may differ over time, but the bound is computed on window days spread over the whole sample, which captures this. Pricing bytes per column at the dry run handles the uncertainty about URL size. No gap.

**D2 — ACCEPT.** The day-1 probe for pooled `indiatimes.com` siblings, the host-from-URL key on window days, and freezing the panel offline from a superset all hang together. The readership caveat is stated. Q1 at 1 day in 6 over two columns is cheap.

**D3 — ACCEPT.** Pre-fieldwork windows ending the day before fieldwork are the right timing; IESH releases do give fieldwork ranges [V-R3]. Tying window length to the rung, with reliability shown as a diagnostic and an attenuation-adjusted coefficient when reliability is below 0.8, avoids choosing the window after seeing the data. The N table and the rule to exclude rounds without fieldwork dates (no imputation) are adequate.

**D4 — ACCEPT.** The ladder is pre-registered and mechanical, and I checked the D37 arithmetic. Steps of 2, 3, 4 and 6 are all coprime with 7, so weekdays rotate. Byte caps per job, one-month first chunks and a ledger with estimate and actual turn the no-refill budget into an operational procedure. The single-statement form is adopted only if its dry run equals one scan; that is the right test, because BigQuery may bill a CTE referenced twice as two reads. The ≤ 3 GB output per job also keeps anonymous results under BigQuery's response-size limit for queries without a destination table. Two items remain `[UNVERIFIED]`: whether anonymous results avoid sandbox storage, and the download path. Both are tested on the first chunk, which is a fair gate. The escalation for "even L4 > 650 GB" is real and goes to the human. I could not verify F, and Themes may make the reduced/full ratio closer to 0.85 than 0.65. The measured ratio replaces the placeholder at Gate 0b, so this is covered.

**D5 — ACCEPT.** Per-year validation of edition patterns, dropping outlet-years by a mechanical rule, and stating the 8–12-block expectation in advance are honest and gate-driven. Thin coverage before 2022 is reported, not hidden.

**D6 — ACCEPT.** This is a subsample with a clear go/no-go:
- proxy reachability first;
- MB/day measured on both streams;
- the 3-day bandwidth rule;
- a smaller second scope.

A no-go leaves V2Tone, which D12 guarantees. My rough figure is about 1–2 GB/day for full GKG files over 600+ window days, so scope 1 is probably no-go and scope 2 is marginal. The design already expects this.

**D7 — ACCEPT.** The rule for the primary outcome (mean only if one definition holds in every round, else median) is fixed before outcomes are merged, and both statistics are printed. CPI is cut at Dec 2025, with 2026 in a labelled no-CPI exercise. State Trends are used only within state, which is correct. City SEs exist in the releases [V-R3], so the D42 MDE inputs are available. City counts are not published; see D27.

**D8 — ACCEPT.** A day-1 test with four logged queries and named fallbacks, and no Phase-1 dependence on DOC. Nothing to add.

## B. Measurement

**D9 — ACCEPT.** The baseline theme is checked on day 1 for its presence in V1 `Themes` in every year, and variants are chosen by F2 on the audit. The failure path is pre-registered and joint with D17, and its fallback wording ("audited, not externally validated"; H1/H5 exploratory) is honest. All switching happens before Gate 2, so before outcomes are merged.

**D10 — ACCEPT.** Keeping the full theme string for ECON/price rows avoids a rescan. The trim rule in D4.6 covers the output-size risk.

**D11 — ACCEPT.** The v2 problem (a level shift at window boundaries) is solved by using two series with one definition each: the monthly series on a key that exists every day, the window series deduplicated. Naming one primary index for H1/H5 removes the doubled tests. The word share stays as the first robustness row, with sign disagreement reported in the main text. V2Tone field 7 is the word count, so row (i) is constructible on window days.

**D12 — ACCEPT.** Using a within-outlet negativity differential rather than an IPI × tone product is sound. The caveat about translated text is stated.

**D13 — ACCEPT.** Thresholds are fixed before outcomes are merged, medians are taken on sampled days, and the volume figures and Bai–Perron breaks make crawl changes visible. Adequate.

**D14 — ACCEPT.** The labelling rule ("co-occurrence shares", never "topics") is the right guard.

## C. Validation

**D15 — ACCEPT.** The strata now have workable sizes:
- the gating recall excludes the near-empty unscreened non-ECON stratum, which is reported as an upper bound with an exact interval;
- the human sample of 150, including 40 Hindi, gives κ a usable interval;
- all metrics carry CIs.

The κ rules have stated consequences. One residual weakness is that recall outside ECON and price slugs is bounded, not estimated. The design says so openly.

**D16 — REVISE.** Mode B's full-text arm is not feasible as written.
- NGrams 3.0 stores one record per token with about 7-word context, in per-minute files and in `gdelt-bq.gdeltv2.webngrams` [V-R3]. GDELT itself warns that a few dates cost tens to hundreds of GB of bandwidth, or exhaust the free BigQuery quota.
- D15's audit is drawn at random across all 2020+ window days. Retrieving text for those articles means scanning `webngrams` partitions, or downloading minute files, for hundreds of distinct dates. Even a modest share of those dates exceeds both the ~330 GB reserve and the 3-day bandwidth rule used in D6.
- None of this is in D37's budget or the ledger plan. The D36 dry-run rule would stop a runaway job, but only after the full-text arm has silently failed, leaving Mode B with slug coding only. Slug coding is weakest for vernacular articles, which is exactly where the E2 gate needs evidence.

**Fix:**
1. Pre-declare that NGrams text is retrieved from **raw minute files keyed to each audit article's GKG 15-minute timestamp**, downloading only the 15 minute files around that timestamp. BigQuery `webngrams` is not used unless a one-day dry run fits a pre-set reserve line, say ≤ 60 GB.
2. **Cluster the 2020+ Mode-B audit sample on a fixed, seeded set of k window days**, with k set from the day-1 pilot's measured MB per minute file and a bandwidth cap of 1 day of background download. Report that the 2020+ full-text metrics come from a date-clustered sample, and widen their CIs for clustering by day.
3. Add a line to `budget_ledger.csv` and to D37 for this retrieval.
4. Treat reconstruction as approximate. Text is stitched from overlapping pre/post snippets ordered by decile, and the coder codebook should say that.

**D17 — ACCEPT.** Raw r ≥ 0.5 is a necessary check only. The "beyond CPI" phrase is allowed only if the partial-correlation interval excludes zero. The episode benchmark uses non-episode months, and the placebo dates are always sampled. That is a clean split between convergent validity (here) and content validity (D15).

**D18 — ACCEPT.** Requiring headline results to survive the word-share and strict-flag rows before they are stated without qualification is the right discipline at N ≈ 45.

## D. Econometrics

**D19 — ACCEPT.**
- The primary cell is single and pre-declared.
- The real-time core is small, with richer rows beside it.
- The future-CPI test has a pre-written "price nowcast" interpretation.
- HAR fixed-b plus wild bootstrap is appropriate at this N.

The level IPI on a differenced outcome is an imbalance worth watching. The ΔIPI variant and the unit-root diagnostics, with their low power stated, handle it.

**D20 — ACCEPT.** Only the IPI and intercept are interacted, regime Ns are printed, and leave-one-episode-out shows dependence on a single episode. Labelled exploratory. Sufficient.

**D21 — ACCEPT.** Appendix only, small, Minnesota prior, described as illustrative, and first on the time-based cut list. Matches the user's request without over-claiming.

**D22 — ACCEPT.** The name is now accurate. The RMSE ratio has a bootstrap CI, Clark–West is used, and pairwise Holm replaces the MCS. A null is framed as low power against a strong AR benchmark. "Out-of-sample" reaches the abstract only if Clark–West rejects (D31). Sound.

**D23 — ACCEPT.** A monthly LP on recursive CPI surprises and Brent shocks, excluding thin months. Sampling noise is acknowledged.

**D24 — ACCEPT.** Descriptive framing with no abstract p-value, and coarse half-lives labelled as such under L3/L4. Proportionate to the few cycles available.

**D25 — REVISE.** The gate that permits the phrase "international framing" and regression claims is "agreement between theme labels and the D15 cause codes ≥ 0.6", but the statistic is not defined. If it is raw percent agreement, the gate is close to automatic: most flagged articles will be "not international" under both the theme flag and the cause code, so agreement above 0.6 can come from the base rate alone. The gate would then license a label the data have not earned. Agents also need a deterministic statistic to execute it.

**Fix:**
- Define the gate as **Cohen's κ** between the binary `S^{int}` article flag (any international theme co-occurring) and the binary D15 cause code "international/imported", on the flagged audit stratum. Use human codes where D15's κ rule replaced LLM codes.
- Pass requires κ ≥ 0.6 on the point estimate, and the D15 cause-code κ must itself be ≥ 0.6. If not, the gate fails by D15's rule.
- Report the 95% CI and the number of articles coded "international".
- Fix the cause-code → binary mapping in `analysis_plan.md` at Gate 2.

**D26 — ACCEPT.** Removing the gap-on-difference regression fixes the mechanical relation. The three-way horse race is honest about collinearity, the "search-implied" relabelling under DOC failure is right, and the 20-hit precision check per item is a sensible screen. Agents will need to map monthly `π` to rounds (latest month before fieldwork, following D19's real-time logic). That is a mapping choice to settle in `analysis_plan.md`, not a flaw in the decision.

**D27 — REVISE.** Two errors in the inference and weighting, both in a design that can make H5 primary.

1. **Randomisation inference at the wrong level.** D27 permutes whole exposure series **across cities**. By construction (D5, D42), cities in one exposure block share most of their local sources, so their exposure series are nearly identical. Their outcomes also share block-level shocks (same press market, same region).
   - The observed assignment is "blocky": identical series given to cities with correlated errors.
   - Most city-level permutations break the blocks, so they produce a narrower null distribution of β̂ than the one the actual assignment faces.
   - The RI p-value is therefore anti-conservative: the same problem that city-clustered SEs have with 8–12 effective units, which is why RI was made primary.

   **Fix:** permute at the **exposure-block level**. Either:
   - (preferred) collapse to block × round (cities within a block averaged with the weights below) and permute block exposure series across blocks; with 8–12 blocks, 8! = 40,320 or more distinct permutations are enough for 999 draws, and the minimum attainable p-value should be reported; or
   - permute series among blocks of equal size and keep the city-to-block mapping fixed.

   The city-level permutation can stay as a secondary row.
2. **Weights that cannot be built from releases.** "Weighted by city sample size": IESH releases do not publish city counts [V-R3], only city means and medians with standard errors. **Fix:** weight by the inverse squared published SE of the city statistic (which D42(c) already uses). Use microdata counts only if D39 succeeds, and state which applies.

The rest of D27 is sound: round and city FE, the balanced source set, the wording rule, and h = 0.

**D28 — ACCEPT.** Removing the causal tier fixes the v2 problem of a rule that could never be met. Row 1 is honestly labelled a common-shock row, it has a pre-declared, pre-outcome substitute when cells are thin, and the post-fieldwork placebo is the right key check. The ceiling sentence is honest.

**D28.2 (REMOVED: shift-share IV) — ACCEPT the removal.** Nothing in the design gives a defensible exclusion restriction in two weeks, and the regressor substitute in D28.1 is correctly not called an instrument.

**D29 — ACCEPT.** The test is two-sided and exploratory, the lack of national power is stated, and the same-city horse race is the main evidence only when E1 reaches the middle tier. The language-of-readership confound is stated, and the fallback to a measurement result is explicit and useful.

**D30 — ACCEPT.** Descriptive, in changes, with the low variance stated and no use as a dependent variable. Correct.

**D31 — ACCEPT.** One primary test (D19) with D22 as its out-of-sample counterpart, abstract wording conditional on Clark–West, Holm for H1/H5 when H5 is live, a pre-stated null outcome, and a freeze at Gate 2. Sound.

## E. Contribution

**D32 — ACCEPT.** The precedents are read on day 1, comparison sentences are written only after reading, and the MPRA 118951 label conflict is flagged for resolution. No claim depends on an unverified paper.

**D33 — ACCEPT.** The claims are sized to what the gates can deliver. "Validated" is conditional, the "not claimed" list is explicit, and the paper stands as a measurement and audit paper if H1 is null.

## F. Execution

**D34 — ACCEPT.** Splitting Gate 1 into 1a and 1b fixes the v2 ordering error. The slip rule is mechanical, and Gate 2 comes before any outcome merge. Day 1 is crowded, but most of it is free dry runs and downloads running in parallel, and D35 absorbs overruns. Adding the D16 retrieval pilot (see D16) to day 1 costs little, since D6's raw pilot already tests file-host reachability.

**D35 — ACCEPT.** Data-gated and time-based cuts are pre-declared and ordered, and the day-8 trigger protects Phase 1. Protecting E1-MV over E5-MV is flagged against the user's ordering rather than done silently.

**D36 — ACCEPT.** Ledger, dry run and `maximum_bytes_billed` on every job, scripted outputs, and a second-agent reproduction. These enforce D4.

**D37 — ACCEPT.** I re-derived each scenario's rung under the 650 GB rule (Low → L1, Mid → L2, High → L3) and the arithmetic holds. The High row is slightly conservative because it does not scale the windows to the 2016 start. The figures are expectations only; the dry runs decide. The risk list is complete except for the D16 retrieval line, which is handled under D16.

## G. Decisions added in v2

**D38 — ACCEPT.** The source order is clear and the deadline feeds gate (d). Removing the state-CPI fallback for E1 is correct, since it would restore the confound. The possible Aug 2023 truncation of E1 is stated.

**D39 — ACCEPT.** An attempt on day 1 with a city-table fallback. Low cost, clear failure path.

**D40 — ACCEPT.** Built from data that exist by day 3, frozen at Gate 1b, extended mechanically before outcomes are merged, with coverage reported. Resolves the v2 ordering problem.

**D41 — ACCEPT.** Necessary given the many sub-samples.

**D42 — ACCEPT.**
- Cell counts, reliability residualised on FE, an attenuation-adjusted MDE against a stated plausible effect, and the price-coverage gate are all computed before outcomes are merged.
- The three tiers give each threshold a stated consequence.
- Blocks defined by shared source and frozen at Gate 2 are exactly what the block-level RI in my D27 fix needs.
- The MDE inputs (city SEs) are published [V-R3].

---

SCORES
D1: ACCEPT
D2: ACCEPT
D3: ACCEPT
D4: ACCEPT
D5: ACCEPT
D6: ACCEPT
D7: ACCEPT
D8: ACCEPT
D9: ACCEPT
D10: ACCEPT
D11: ACCEPT
D12: ACCEPT
D13: ACCEPT
D14: ACCEPT
D15: ACCEPT
D16: REVISE
D17: ACCEPT
D18: ACCEPT
D19: ACCEPT
D20: ACCEPT
D21: ACCEPT
D22: ACCEPT
D23: ACCEPT
D24: ACCEPT
D25: REVISE
D26: ACCEPT
D27: REVISE
D28: ACCEPT
D28.2: ACCEPT
D29: ACCEPT
D30: ACCEPT
D31: ACCEPT
D32: ACCEPT
D33: ACCEPT
D34: ACCEPT
D35: ACCEPT
D36: ACCEPT
D37: ACCEPT
D38: ACCEPT
D39: ACCEPT
D40: ACCEPT
D41: ACCEPT
D42: ACCEPT
