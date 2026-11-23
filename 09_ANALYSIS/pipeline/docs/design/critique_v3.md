# Critique of design_v3 (red team)

Web checks done: GDELT's partitioned-table post confirms `gkg_partitioned` with `_PARTITIONTIME` daily partitions (a 15-day query cost 15 GB vs 423 GB unpartitioned, all columns, 2016-era), so the ~1 GB/day full-column scale is consistent with the design's F = 0.8-1.6 TB for a reduced column set. RBI's Sep-2026 IESH release confirms bi-monthly fieldwork (10-20 Sep 2026), 19 cities, ~6,000 responses, and that **estimates are published as medians** ("unless stated otherwise"). Search turned up existing Indian news-inflation work (MPRA 118951, RBI Bulletin food-inflation sentiment, IIM-C WPS 830, an IIMA household-expectations paper), so the "not first" wording in D33 is correct. No FATAL flaws found: every serious risk below already has a gate or fallback. The remaining issues are specification and feasibility fixes.

## A. Data

**D1 ACCEPT.** Column logic is right (SourceCommonName filter does not cut billed bytes; Themes dominates cost). Remaining risk (URL bytes) is priced by the dry run.

**D2 REVISE MINOR.**
- MINOR: Q1 "lists all `.in` domains" but most large Indian outlets are `.com` (thehindu.com, hindustantimes.com, ndtv.com, indiatimes.com, indianexpress.com, livemint.com, business-standard.com). A `.in`-driven superset silently drops the core English panel from Stage A/B, and Stage A/B cannot be rerun on the budget. Fix: seed the Stage A/B `SourceCommonName IN (...)` list from the hand-keyed top-20 plus GDELT's published domain-to-country lookup file (free, offline), then add `.in` and Q1's Indian-language hits. Freeze at Gate 1a with the list printed.

**D3 ACCEPT.** Pre-fieldwork window and reliability rule are sound; mode dummy and 2020 exclusion handle the telephone rounds.

**D4 ACCEPT.** Ladder, dry runs and per-job byte caps handle the no-refill budget. Note (no change needed): a dry run on a CTE referenced twice may report double bytes; the design already adopts form (i) only if dry-run bytes equal one scan.

**D5 ACCEPT.** The block-count caveat (8-12 effective units) is planned for, and D42 gates it.

**D6 ACCEPT.** Go/no-go on the proxy and bandwidth is explicit; V2Tone-only fallback exists.

**D7 REVISE MINOR.**
- MINOR: IESH medians are computed from binned responses and move in coarse steps, so the rule "median is primary unless the mean is consistently defined" may leave the primary outcome with little variation, which hurts power at N≈45. Fix: record in the plan that the median primary is reported with its bin step, and add the share of respondents expecting ≥ 10% (or the published distribution mean) as a continuous variant row. Pre-declare before Gate 2.

**D8 ACCEPT.** Gated, nothing in Phase 1 depends on it.

## B. Measurement

**D9 ACCEPT.** The failure action is pre-registered.

**D10 ACCEPT.**

**D11 ACCEPT.** Two series with one definition each, and the cross-definition correlation is reported. One small note: the monthly series has no deduplication while the window series does, so level differences are possible; the correlation line covers it.

**D12 ACCEPT.** Within-outlet differential is a sensible choice.

**D13 ACCEPT.**

**D14 ACCEPT.** The labelling rule guards the over-reading.

## C. Validation

**D15 ACCEPT.** Strata and gates are well sized. Residual: LLM coders from one model family share errors, so human κ is the real check; the design already uses it.

**D16 ACCEPT.** Works under both modes. The NGrams per-article retrieval cost is flagged UNVERIFIED and the Mode B vernacular rule fails E2 cleanly.

**D17 ACCEPT.** Trends is correctly framed as convergent, not incremental, validity; the action on failure is in D9.

**D18 ACCEPT.**

## D. Econometrics

**D19 REVISE MINOR.**
- MINOR: the LHS is `y_{r+h} − y_{r−1}` but the controls hold only `Δy_{r−1}`, not the level `y_{r−1}`. With a persistent survey and an IPI level that co-moves with the expectation level, the omitted lagged level makes β pick up mean reversion (an error-correction term), biasing the one-sided H1 test. Fix: add `y_{r−1}` as a regressor (or estimate in levels with `y_{r−1}` on the RHS) in the pre-registered primary; keep the ΔIPI variant. This also aligns D19 with D22's AR benchmark.
- Everything else (small core control set, real-time CPI, future-CPI test, HAR/wild bootstrap, "predicts" wording) is fine. Power at N≈45-55 is low, and the design says so.

**D20 ACCEPT.** Labelled exploratory, with leave-one-episode-out.

**D21 ACCEPT.** Appendix only, first on the cut list.

**D22 ACCEPT.** About 25 evaluation rounds against a strong AR(1) is stated as low power. The wording avoids "nowcast".

**D23 ACCEPT.**

## Phase 2

**D24 ACCEPT.** Descriptive, honest about few cycles.

**D25 ACCEPT.** Gate on cause-code agreement.

**D26 ACCEPT.** Horse race in one specification and the "search-implied" relabel on DOC failure are well handled. Collinearity is acknowledged.

**D27 ACCEPT.** RI as the primary p-value fits 8-12 blocks, and the gates fix tiers before outcomes.

**D28 REVISE MINOR.**
- MINOR: the "key check" placebo uses post-fieldwork news, days +1 to +30. Only pre-fieldwork window days carry the full column set with `DocumentIdentifier`, and edition-path exposure needs URLs. With ~50 days between fieldwork end and the next fieldwork start, and windows of 14-30 days ending just before the next fieldwork, most days +1..+30 are reduced-set days with no URL, so `IPI^{loc}` cannot be built for them. As written, the placebo is mostly uncomputable and the strongest permitted sentence could never be reached. Fix: define the placebo as the lead exposure, i.e. `IPI^{loc}` from the next round's pre-fieldwork window (which is URL-bearing), and state its overlap with days +21..+50. Add this to the D42 cell-count check.
- Otherwise the wording rule and the removal of the IV are sound.

**D29 ACCEPT.** Sized to the data, with the language-composition confound stated.

**D30 ACCEPT.**

**D31 ACCEPT.** One primary in-sample test and the null contribution stated in advance.

## E. Contribution

**D32 ACCEPT.** Verification list is right; the MPRA 118951 attribution conflict is flagged for day 1 (my search shows the MPRA 118951 paper exists, but its content is not read here).

**D33 ACCEPT.** Claims are modest, and the paper stands as a measurement paper if E1 and H1 fail.

## F. Execution

**D34 REVISE MINOR.**
- MINOR: day 1 carries about ten parallel tasks, and the human's hour-1 tasks are a single point of failure for the "no refill" budget. The design acknowledges this; the slip rule and cut lines absorb it. Fix: add a one-line rule that the Q1 probe and the outlet-list freeze (Gate 1a) cannot slip behind Stage A start, because a wrong superset (see D2) cannot be repaired without a rescan.

**D35 ACCEPT.** Fixed in advance, with a trigger at day 8.

**D36 ACCEPT.**

**D37 ACCEPT.** Scenario table is only expectation-setting; the ladder uses exact dry runs.

## G. Added in v2

**D38 ACCEPT.** Deadline and gate (d) mean a failure only demotes E1.

**D39 ACCEPT.** Fallback is city tables.

**D40 ACCEPT.** The mechanical extension rule has no outcome contact.

**D41 ACCEPT.**

**D42 ACCEPT.** Tiering fixed before outcomes is right. One note carried from D28: the cell-count check should include the placebo (lead) exposure.

## REMOVED decisions

**Shift-share IV (D28 item 2) ACCEPT (removal correct).** No defensible exclusion restriction in two weeks.

**Fully interacted regime model and threshold search (D20) ACCEPT (removal correct).** Too few observations.

**One-sided national E2 test (v2) ACCEPT (removal correct).** No power; replaced by a descriptive statement and the same-city horse race.

**Regression of the perception gap on `π^{med} − π^{CPI}` (D26) ACCEPT (removal correct).** CPI enters both sides.

**State-CPI fallback for E1 prices (D38) ACCEPT (removal correct).** It would restore the confound.

**Word share as headline (D11) ACCEPT (demotion correct).**

SCORES
D1: ACCEPT
D2: REVISE MINOR
D3: ACCEPT
D4: ACCEPT
D5: ACCEPT
D6: ACCEPT
D7: REVISE MINOR
D8: ACCEPT
D9: ACCEPT
D10: ACCEPT
D11: ACCEPT
D12: ACCEPT
D13: ACCEPT
D14: ACCEPT
D15: ACCEPT
D16: ACCEPT
D17: ACCEPT
D18: ACCEPT
D19: REVISE MINOR
D20: ACCEPT
D21: ACCEPT
D22: ACCEPT
D23: ACCEPT
D24: ACCEPT
D25: ACCEPT
D26: ACCEPT
D27: ACCEPT
D28: REVISE MINOR
D29: ACCEPT
D30: ACCEPT
D31: ACCEPT
D32: ACCEPT
D33: ACCEPT
D34: REVISE MINOR
D35: ACCEPT
D36: ACCEPT
D37: ACCEPT
D38: ACCEPT
D39: ACCEPT
D40: ACCEPT
D41: ACCEPT
D42: ACCEPT
REMOVED-shift-share-IV: ACCEPT
REMOVED-threshold-search: ACCEPT
REMOVED-national-one-sided-E2: ACCEPT
REMOVED-gap-regression: ACCEPT
REMOVED-state-CPI-fallback: ACCEPT
