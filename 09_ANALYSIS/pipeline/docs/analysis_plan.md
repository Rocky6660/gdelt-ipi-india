# Analysis plan (FROZEN at Gate 2, 23 Nov 2026)

Status: **FROZEN by user ruling at Gate 2, 23 Nov 2026** (ledger). Written by Claude Code from the design and the
rulings. When it was frozen, no regression of outcomes on the index had been run. Outcomes are merged with news data
only after this freeze. The SHA-256 of this file at freeze time is recorded in `docs/analysis_plan.sha256`; any later
change is an amendment, dated in §8.

**Order change (user ruling, deadline):** the index is accepted with the D9 baseline flag before the audit. Phase 1 and
the extensions run first; the audit (D15/D16) runs afterwards. If the audit triggers the D9 switch (baseline precision
< 0.5 or gating recall < 0.6), Phase 1 is re-run on the best-F2 flag under the pre-declared rule, and the paper reports
both runs and states that the order was changed.

Sources: `design/design_final.md` (D1–D42), `design/ledger.md` (user rulings 17 Nov and 23 Nov 2026), and
`HANDOFF_FOR_CLAUDE_CODE.md` (user rulings carried over from the earlier sessions).

## 1. Samples
- GKG rung **L3**: 14-day pre-fieldwork windows (full column set) plus a 1-in-4 systematic grid of other days (reduced
  set), from 2016-01-01 to 2026-10-31.
- IESH rounds: 67 rounds since 2015 (`data/raw/iesh_rounds.csv`). Pre-2020 rounds without exact dates use ruling (b):
  fieldwork_start = 1st of the survey-ended month, flagged `fs_rule = month_rule`. Robustness row: exact-date rounds only.
- A round's window enters only if ≥ 60% of its 14 days are valid (D13). Excluded rounds are not imputed (D3).
  Known exclusion: **2025-07**, whose whole window (17–30 Jun 2025) falls in a GDELT GKG gap (no table partitions for
  16 Jun – 1 Jul 2025).
- CPI-controlled regressions use rounds whose real-time CPI print is base 2012 (≤ Dec 2025 data) (D7). Rounds from
  2026 enter only a labelled no-CPI prediction exercise.

## 2. Index (built by `scripts/build/build_index.py`; report in `data/processed/index/build_report.md`)
- **Panel** (D2; ruling 23 Nov): superset of 936 domains, filtered by the GDELT domain-country file, plus the hand
  review in `scripts/build/panel_review.csv` (every call recorded with its reason; low-confidence calls are drops).
- **Primary index `ipi_primary`** (D11 window series): article share = ECON_INFLATION-flagged distinct URLs / all
  distinct URLs per host, over valid outlet-days of the window. Outlet key = URL host (siblings pooled). Equal-weight
  mean over the **balanced core** (hosts present, ≥ 10 articles, in ≥ 80% of valid windows). Dedup is day-level (R5);
  the cross-day duplicate rate is reported.
- **Robustness rows** (D11, D9, D18), in this order: (i) word share (V2Tone word counts; hosts with a > 2× year-on-year
  break in words per article excluded); (ii) pooled ratio; (iii) share among ECON articles; (v) wire-copy filter;
  strict flag (≥ 2 of ECON_INFLATION, WB_442_INFLATION, ECON_COST_OF_LIVING); price family; WB_442; second core from 2018
  including vernacular outlets. **Not computable:** (i-b) 75th-percentile word cap (no per-article word counts for the
  denominator); (iv) readership weights (no readership data).
- Headline claims must survive the word-share row and the strict-flag row to be stated without qualification (D18).
- **Monthly series** (D11): SourceCommonName × source language, no dedup, grid days only; months with < 5 valid
  sampled days are not used in D23/D24.

## 3. Outcome rule (D7)
- **Primary outcome: 1-year-ahead MEDIAN** (handoff ruling; the published mean changed definition in Sep 2018, so the
  mean is not published under one definition in all rounds). The mean is shown in every table.
- **Median bin step:** cannot be recorded from source. The per-round response distributions were not parsed
  (`iesh_distribution_round.csv` is empty), and the published median is interpolated to two decimals, so it does not
  move in whole-bin steps. Stated as a limitation.
- **Continuous variant:** the published 1-year mean (the share expecting ≥ 10% needs the distributions, which are
  unavailable).

## 4. Hypotheses and tests (D31, D19, D22)
- **H1 (primary, one-sided, 5%):** β > 0 on the standardised `ipi_primary` in the D19 local projection at h = 0 for the
  1-year median, with the lagged level, the lagged change, and core controls: real-time CPI y/y, food CPI y/y (DoCA
  unavailable for the full period, so this is the D19 fallback), Δrepo (from `data/raw/policy/repo_rate.csv`, RBI
  releases), survey-mode dummy. Inference: EWC/fixed-b plus wild bootstrap. Wording: "predicts", never "causes".
- **D22:** recursive pseudo-real-time prediction against AR(1) and AR(1)+CPI(+food); RMSE ratio with bootstrap CI and
  Clark–West. "Out-of-sample" enters the abstract only if Clark–West rejects.
- **H5** (E1 city panel) is primary only if D42 puts E1 in the top tier; then H1 and H5 are Holm-adjusted.
- **Secondary, Holm-adjusted:** H2 regime (D20, exploratory), H3 E5, H4 E4, H6 E3, H7 E2 (two-sided, exploratory).
- If H1 is null, the paper's contribution is the audited index, the coverage audit and a null with CIs, and the
  abstract says so.

## 5. Validation gates
- **Audit (D15/D16; ruling):** all ~1,550 sampled articles are fetched (no cap) and coded by **two independent LLM
  passes** (Claude Opus, in-session). **No human coding**; the paper states that there is no human validation.
  LLM–LLM agreement (κ with CI) is reported as reliability. Precision ≥ 0.5 and gating recall ≥ 0.6 for the baseline
  flag, otherwise switch to the best-F2 variant (D9). If κ < 0.6 on direction or cause, those codes are not used in
  E3/E4 claims.
- **D25 (E4) mapping** (fixed in `docs/coding/codebook.md`): `international_imported = 1` if cause_primary ∈
  {global_oil_commodities, exchange_rate, international_inflation_abroad}, else 0; missing if not relevant. Gate:
  Cohen's κ between the S^int article flag (flags.csv family `international`) and this binary on the flagged stratum
  ≥ 0.6, and cause-code κ ≥ 0.6.
- **External validation (D17):** Trends r ≥ 0.5; ≥ 3 of 4 episodes above the 90th percentile of non-episode months;
  placebo dates show no peak. Failure action as in D9.

## 6. Deviations from design_final (all by user ruling or data availability)
1. No human coding and no second-model reproduction (rulings 17 Nov 18:40 and handoff); replaced by two LLM passes and a
   scripted rerun check (Gate 3).
2. HLL sketches dropped; day-level dedup (R5).
3. Panel filter rule set on 23 Nov (ledger), before any outcome merge.
4. `build_index.py` rewritten on 23 Nov (the earlier file was not in the project).
5. No sports theme code exists among the extracted ECON/price articles, so only the election co-occurrence placebo
   flag is available. The D17 placebo dates are unaffected.
6. Index rows (i-b) and (iv) are not computable (see §2).
7. GDELT gap 16 Jun – 1 Jul 2025 → round 2025-07 excluded.

8. Index facts from the full build (`data/processed/index/build_report.md`), fixed before outcomes were merged:
   62 of 63 rounds have a valid window. The balanced core (104 hosts) includes 54 vernacular (translated) outlets from
   2016, so the text states the actual language mix instead of "English-only before 2018". `variant_strict` and
   `variant_wb442` correlate 1.00 with the primary (WB_442_INFLATION nearly always co-occurs with ECON_INFLATION), so
   the strict-flag row is reported but is not an independent check under D18. The survey-mode dummy covers the
   6 telephone rounds; the other rounds' mode is not stated in the releases.

## 7. Gate 2 items
- Index: **accepted** with the D9 baseline flag before the audit (order change above).
- D26 round mapping for E3: real-time month = the latest month whose CPI was released before fieldwork start (same
  rule as `cpi_rt` in phase1.py).
- E1 tier (D42): **not yet fixed**, because `edition_patterns.csv` (D40) has not been built. It must be fixed, without
  outcomes, before any E1 regression is run. Until then E1 is descriptive.

## 8. Amendments after freeze
- 2026-11-23 03:12 IST: §3 bin step. The IESH response options are 1-percentage-point bins ("0-1 per cent" to "15-16 per cent", "16 per cent or more", "No idea"), as documented in Ruhi, Sharma & Sankaran (RBI Bulletin, 23 Jul 2025), verified in docs/literature_check.md. The published median is interpolated within these bins. No analysis changes.
- 2026-11-23 14:39 UTC: §5 truth source. Because there is no human coding (ruling), the D15 rule 'human codes replace LLM codes if kappa < 0.7' cannot operate. LLM coder A is the truth source; the A-vs-B kappa is reported as reliability (not validation) and is the kappa used for the direction/cause rule; precision/recall are also reported with B as truth and with A=B agreement as truth. Pass B covers the gating strata only (user instruction); nonecon_noslug is coded by A only.
