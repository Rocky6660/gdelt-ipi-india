# Open disputes in design_v3

Eight decisions are still open after round 3. Each has one proposed fix. None carries a FATAL flag.

Who objected: **Reviewer** means review_v3.md (Opus). **Critic** means critique_v3.md (Sonnet).

---

## D2. Corpus = frozen panel of Indian outlets

**(a) What v3 says.** The outlet panel is frozen at Gate 1a. The candidate list (Q1) covers all `.in` domains and the top Indian-language domains. Stage A and B scans use a wider superset, and the frozen panel is applied offline.

**(b) Objection.** Critic: REVISE MINOR. Most large Indian outlets sit on `.com` domains (for example thehindu.com and hindustantimes.com), so a `.in`-based list could leave the core English outlets out of the Stage A and B scans. Those scans cannot be rerun on the budget. Reviewer: ACCEPT.

**(c) Proposed fix.** Seed the Stage A and B source list from the hand-keyed top-20 outlets and GDELT's domain-to-country lookup file. Then add the `.in` domains and the Q1 Indian-language hits. Print the list at Gate 1a.

**(d) Effect.**
- Accept: the major outlets are named directly in the scan list, and `.in` and Q1 hits are added on top.
- Keep v3: the scan list depends on the `.in` filter, and a missed `.com` outlet could only be added back with a rescan.

---

## D7. Outcome and control data

**(a) What v3 says.** The primary outcome is the one-year expectation. The mean is primary only if RBI publishes it under one definition in every round. Otherwise the median is primary. Both appear in every table.

**(b) Objection.** Critic: REVISE MINOR. The critic says median estimates come from binned responses and move in coarse steps, so a median primary may have little variation at about 45 rounds. The critic's own search found that the September 2026 release states its estimates are medians unless stated otherwise. Reviewer: ACCEPT.

**(c) Proposed fix.** Record the bin step in the plan for the median primary. Add a continuous variant: the share of respondents expecting 10% or more, or the published distribution mean. Declare both before Gate 2.

**(d) Effect.**
- Accept: one extra variant row and a note on the bin step. The primary rule stays the same.
- Keep v3: no extra row. The median primary may move in coarse steps with limited variation.

---

## D16. Audit text source (decision for the user)

**(a) What v3 says.** The validation audit has two modes, chosen at Gate 0a. Mode A fetches live or archived article text, only if the user approves. Mode B rebuilds text from GDELT's Web News NGrams for 2020 onward and codes URL slugs for all years.

**(b) Objection.** Reviewer: REVISE. The reviewer says per-article NGrams retrieval is not feasible as written. The data come as per-token records in per-minute files, GDELT warns that some dates cost tens to hundreds of GB, and the cost is not in the budget. The 2020+ audit draws on many dates, so the retrieval would hit many of them. Critic: ACCEPT, and it marks the per-article retrieval cost as UNVERIFIED.

**(c) Proposed fix.**
- Take text from the minute files around each audit article's timestamp.
- Use the BigQuery NGrams table only if a one-day dry run fits a set reserve of 60 GB or less.
- Draw the 2020+ Mode B sample on a fixed, seeded set of window days. Set the number of days from a pilot, with a cap of one day of background download.
- Widen the confidence intervals for clustering by day.
- Add the retrieval to the budget ledger, and mark the reconstructed text as approximate.

**(d) Effect.**
- Accept: Mode B text comes from files, the audit days are clustered, and the 2020+ intervals get wider.
- Keep v3: the full-text route is unpriced and may fail quietly. The audit would then rely on slug coding, which is weakest for vernacular articles, where the E2 gate needs evidence.

---

## D19. National in-sample test

**(a) What v3 says.** Round-level local projections for horizons 0 to 3. The primary cell regresses the change in the one-year expectation on the window article share. Controls are CPI, food prices, the repo change and survey mode. The model has a lagged change in the outcome, but no lagged level.

**(b) Objection.** Critic: REVISE MINOR. Without the lagged level, the coefficient may pick up mean reversion and bias the H1 test. Reviewer: ACCEPT, with a note that a level index against a differenced outcome needs watching. The reviewer says the ΔIPI variant and the unit-root checks handle this.

**(c) Proposed fix.** Add the lagged expectation level as a regressor in the primary. Keep the ΔIPI variant.

**(d) Effect.**
- Accept: the primary gets one extra control, and the ΔIPI variant stays.
- Keep v3: the primary omits the lagged level, which the critic says can bias the H1 test.

---

## D25. E4 Imported vs domestic narratives

**(a) What v3 says.** The measure is the share of inflation articles that also carry an international theme. Calling it "international framing" requires an agreement of 0.6 or more between theme labels and the D15 cause codes. The design does not name the statistic.

**(b) Objection.** Reviewer: REVISE. If the gate is raw percent agreement, most flagged articles are "not international" on both measures, so the base rate alone could push agreement past 0.6. Agents also need a deterministic statistic to run. Critic: ACCEPT.

**(c) Proposed fix.** Use Cohen's kappa between the binary international flag and the binary "international/imported" cause code, on the flagged audit stratum. Pass requires kappa of at least 0.6 on the point estimate, and the D15 cause-code kappa must also be at least 0.6. Report the interval and the number of articles coded international. Fix the cause-code mapping at Gate 2.

**(d) Effect.**
- Accept: the gate becomes a kappa with a stated pass rule, so the label is harder to earn.
- Keep v3: the gate has no defined statistic, so the label could be applied on base-rate agreement alone.

---

## D27. E1 City panel

**(a) What v3 says.** The primary p-value comes from randomisation inference, which permutes exposure series across cities (999 draws). City regressions are weighted by city sample size.

**(b) Objection.** Reviewer: REVISE, on two points.
1. Cities in one exposure block share sources and press-market shocks. City-level permutations break those blocks, which gives a narrow null and an anti-conservative p-value.
2. IESH releases publish city means, medians and standard errors, but not city sample counts. Sample-size weights cannot be built from the releases.

Critic: ACCEPT.

**(c) Proposed fix.**
- Permute at block level. For example, collapse to block by round and permute block exposure series across blocks. With 8 blocks there are 40,320 permutations, enough for 999 draws. Report the smallest attainable p-value.
- Keep the city-level permutation as a secondary row.
- Weight by the inverse squared published standard error. Use microdata counts only if D39 succeeds.

**(d) Effect.**
- Accept: the primary p-value moves to block level, the weights change, and the city-level test becomes secondary.
- Keep v3: the primary p-value is anti-conservative and the weights cannot be built from published data.

---

## D28. E1 robustness rows

**(a) What v3 says.** Three rows. A common-shock row uses local articles co-flagged with national-policy themes, with a substitute if cells are thin. The shift-share instrument was removed in v2. The key placebo is post-fieldwork news on days +1 to +30. The strongest permitted sentence depends on that placebo.

**(b) Objection.** Critic: REVISE MINOR. Days +1 to +30 are mostly reduced-set days with no URL, so local exposure cannot be built for most of them. The key placebo is therefore mostly uncomputable. Reviewer: ACCEPT, and calls the post-fieldwork placebo "the right key check".

**(c) Proposed fix.** Define the key placebo as a lead exposure: local exposure built from the next round's pre-fieldwork window, which carries URLs. State its overlap with days +21 to +50. Add it to the D42 cell-count check.

**(d) Effect.**
- Accept: the placebo changes to the next round's window, and the wording rule changes to match.
- Keep v3: the placebo is mostly uncomputable, so the strongest permitted sentence cannot be reached.

---

## D34. Work plan (14 days)

**(a) What v3 says.** Gate 1a (outlet list and theme freeze) runs on days 1 and 2, alongside Stage A on day 2. Day 1 holds about ten parallel tasks. A slip rule moves the rung down if Stage A is late.

**(b) Objection.** Critic: REVISE MINOR. The Q1 probe and the outlet freeze could slip behind the start of Stage A, and a wrong list cannot be fixed without a rescan. Reviewer: ACCEPT, and notes that the D16 pilot added to day 1 costs little.

**(c) Proposed fix.** Add a one-line rule: the Q1 probe and the Gate 1a outlet freeze finish before Stage A starts.

**(d) Effect.**
- Accept: Stage A waits for the freeze, so Stage A may start later.
- Keep v3: Stage A can start before the freeze, so a wrong list could force a rescan the budget cannot afford.

---

No FATAL flags on any of the eight. The critic's six are REVISE MINOR. The reviewer's REVISE items on D16, D25 and D27 are substantive, so "minor" applies only to the critic's six.
