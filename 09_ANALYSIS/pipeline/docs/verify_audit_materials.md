# Verification of the audit materials (D9, D15, D16, D25, D26, D29)

Verifier: independent agent, 17 Nov 2026. No network calls were made. The materials were not edited.

Files checked: `docs/coding/{codebook.md, human_coding_instructions.md, coding_sheet_template.csv, audit_key_template.csv}`, `scripts/audit/{sample_audit.py, fetch_texts.py, llm_code.py, audit_metrics.py, audit_common.py}`, `scripts/tests/test_audit.py`, against `docs/design/design_final.md`.

Tests: the existing suite passes (25 of 25). I added 8 synthetic tests in `/home/claude/verify_tests/test_verify.py` (outside the project tree; all data synthetic). All 8 pass. Two of them pass because they confirm a defect (B1 and B2 below). The item-6 simulation is in `/home/claude/verify_sim/sim.py`.

D26 is touched by these materials only through the D15 direction κ rule ("κ < 0.6 on direction or cause → not used in E3/E4 claims"). That rule is implemented. The D26 FV direction coding (rising vs falling phrases on DOC hits) is a separate instrument and is out of scope here.

## Summary

| # | Check | Verdict |
|---|---|---|
| 1 | Sampler (strata, seed, 1.5× oversampling, IPW weights, human 150/40 Hindi, blind sheet, separate key) | **PASS**, with should-fixes |
| 2 | Metrics and gate rules | **FAIL**: 2 blockers (B1, B2); formulas otherwise correct |
| 3 | Nothing imputed or fabricated; missing data → NOT_EVALUABLE | **PASS** |
| 4 | Fetch logging, Wayback, politeness, robots | **PASS**, with should-fixes |
| 5 | Codebook and human instructions | **PASS**, with one should-fix that affects the D25 gate (S9) |
| 6 | 400 cap vs fetching the full sample | Assessment below |

**Overall: not ready to run until B1 and B2 are fixed.** Both fixes are small, a few lines each.

---

## 1. Sampler (`sample_audit.py`): PASS

What is right:
- **Strata** match D15 exactly: 300 flagged, 300 ECON-unflagged, 150 non-ECON with a slug keyword, 100 non-ECON without, and for Hindi and for the larger of Marathi/Bengali, 100 flagged + 100 ECON-unflagged each. The strata are mutually exclusive. The second language is chosen by volume, as D15 says. Total 1,250.
- **Seed**: fixed (`20261116`) and written to the meta file. Sub-seeds (+1 … +5) are deterministic. The existing test confirms that two runs give identical output. D15 and D36 ask only for "seeded".
- **1.5× oversampling of 2015–2018 (Mode A)**: each stratum is split into 2015–18 and later sub-strata, and the allocation is tilted so that π_old / π_new = 1.5. I confirmed this in `test_oversample_ratio_and_weights`: the ratio is 1.500, and the weights sum exactly to N in each sub-stratum. In Mode B the tilt is forced to 1.0, which is reasonable because link rot does not matter there.
- **Inverse-probability weights**: `sampling_weight = N_sub / n_sub`, which is exact under SRS within sub-strata. The Mode B day factor D/K is correct in expectation for the two-stage design.
- **Human 150 incl. 40 Hindi**: the allocation sums to 150 (Hindi 20 + 20). Shortfalls are reported and never topped up.
- **Blind sheet**: columns are `audit_id, language, url, retrieval_mode, text_file` plus the code fields. There is no stratum, flag, weight or rank. Audit IDs are randomly permuted and the sheet order is shuffled.
- **Key kept separate**: written to `private/`. The manifest carries no stratum.

Should-fix:
- **S1 (should-fix; blocker if DOC passes).** The +60 DOC stratum ("DOC keyword hits unflagged by themes, only if DOC passes") and the "(or a DOC keyword hit)" part of the slug screen are not implemented. Add an optional `--doc-hits` input and a `doc_unflagged` stratum.
- **S2 (should-fix).** D34 draws the audit in two tranches, Stage A first and then Stage B, "under the same seeded D15 rules". The sampler draws once from one input. If it is run on Stage A data and again on Stage B data, it draws two full samples of 1,250, and the audit IDs collide (A0001… in both). Either add tranche support, with a fixed allocation per tranche, a tranche ID prefix and combined weights, or draw once after Stage B. This becomes a blocker if the D34 two-tranche schedule is kept.
- **S3 (should-fix).** The human subsample is drawn before any fetching. If a human-selected text fails, the human n drops below 150. The `--retrieval-log` re-draw exists, but the workflow (when to re-run, and that the sheet must be regenerated before any coding starts) is not documented. Better: replace a failed article with the next `human_rank` in the same stratum.
- **S4 (should-fix).** 15 of the 150 human articles come from the Marathi/Bengali strata. The instructions allow `UNREADABLE` for a language the coder cannot read. That silently shrinks the κ sample and leaves those strata with no human check. Either confirm that the coder reads that language, or move these 15 to English/Hindi and record that the second language has an LLM–LLM check only.
- **N1 (nit).** "1.5× oversampling" is read as a tilt within a fixed stratum n, so the total stays at 1,250. The other reading is +50% extra draws for 2015–18, which gives roughly 1,550 if 2015–18 is about half of window-day articles. The tilt reading is defensible, but state it in `analysis_plan.md`.
- **N2 (nit).** The keyword list (`DEFAULT_KEYWORDS`) defines a stratum. Freeze it at Gate 1a and print it. The meta file records only its length, so record its hash too.
- **N3 (nit).** Window-day filtering happens only if `--window-days` is passed. Make it required, or assert that the input holds window days only.

## 2. Metrics (`audit_metrics.py`, `audit_common.py`): FAIL (2 blockers)

**Hand verification** (`test_hand_ipw_unequal_weights`, with unequal weights inside strata):
- TP weight = 10 + 5 + 5 = 20; flagged weight = 30 + 4 (filler) = 34; relevant weight = 20 + 30 + 10 = 60.
- P = 20/34 = 0.588 and R = 20/60 = 0.333. The script gives exactly these values.
- F2 = 5PR/(4P + R) = 0.4 also matches.

Other checks that hold:
- Clopper–Pearson matches `scipy.stats.beta` quantiles to 1e-6 for (k, n) = (0,100), (1,100), (3,100), (7,150), (50,100), (100,100).
- A three-category κ computed by hand matches both κ implementations.
- The existing toy test, checked by hand: P = R = 2/3, English ECON recall 0.70, vernacular recall 0.75, recall floor = 200/(300 + 100·CP_upper).

Rules implemented as D15/D25/D29 require:
- **κ < 0.7 on relevance** → truth source switches to the human codes. If κ cannot be computed → NOT_EVALUABLE.
- **κ < 0.6 on direction or cause** → "NOT used in E3/E4 claims".
- **Precision ≥ 0.5 and gating recall ≥ 0.6** on point estimates, else the best-F2 variant.
- **Gating frame** = ECON strata + slug-screened non-ECON.
- **Unscreened non-ECON** gives only a bound: exact CP interval plus a recall floor.
- **D25**: κ(theme flag, binary international cause) on the flagged strata, ≥ 0.6, **and** D15 cause κ ≥ 0.6; the CI and the count coded international are reported.
- **D29**: |vernacular − English recall| ≤ 0.15 on point estimates, with a bootstrap CI of the difference. In Mode B, the "not estimable" rule fails the gate.

**Blockers**
- **B1 (blocker): the best-F2 candidate set is not D9's variant list.** `variants` defaults to *every* `flag_*` column except `flag_econ` and `flag_international`. The sampler carries all extraction flags into `gdelt_flags`, and D10 has about 40 of them, including placebos (sports, elections), monetary policy and fuel. The CLI has no `--variants` option, so the set cannot be restricted. `test_variants_include_non_d9_flags` shows the gate failing and the script selecting **`flag_sports`** as the "best-F2 variant". Fix: take the candidate list from D9 only (price-family, World Bank price-stability, strict) through a required `--variants` argument or `config.yaml`, and refuse any other flag.
- **B2 (blocker): the nonresponse adjustment works at stratum level, not stratum × period.** Uncoded articles are handled by scaling coded design weights to the stratum total. Fetch failures from link rot fall mostly on 2015–18 articles, which is the reason for the oversampling. Scaling at stratum level shrinks the 2015–18 share of each stratum, so IPW precision and recall are biased whenever relevance or flag rates differ by period. `test_nonresponse_adjustment_is_stratum_level_not_period_level` shows this: true recall is 0.500, and with half of the old ECON-unflagged articles unretrieved the script reports **0.571**. Adjusting within (stratum × 2015–18/later) cells recovers 0.500. Fix: post-stratify within the sampling sub-strata, which are already in the key through `gkg_date`. Stratify the bootstrap the same way, report per-cell response rates, and state the MAR-within-cell assumption.

**Should-fix**
- **S5.** D25 drops flagged articles coded relevance = N, because `international_imported` is set only for relevant articles. Coding them 0 would be the other reading. This choice changes κ, so pre-register it in `analysis_plan.md` with the cause mapping at Gate 2. Also, D25 pools the vernacular flagged strata with the general stratum, while D25 names "the flagged audit stratum". The general-only κ is computed, but it is not the gating number. Pre-register which one gates.
- **S6.** The gating frame contains no focal-language non-ECON slug articles, because D15 defines no such stratum. Gating recall therefore covers non-focal languages' slug articles plus ECON in all languages. State this next to the number.
- **S7.** The κ rule uses human vs LLM coder A only (`--primary-coder`). D15 says "human-vs-LLM κ". Pre-register coder A as primary, or require both coders to clear the threshold.
- **N4 (nit).** If the gate fails and the baseline is itself the best-F2 variant, the action reads "switch to best-F2 variant: flag_baseline". It should say that D9's next step (strict flag) applies.
- **N5 (nit).** D15 says "every figure carries a CI". The recall floor has none, and κ with n < 10 gets no interval. Label these explicitly in the report.
- **N6 (nit).** The `D15_relevance_kappa` CI is built in a convoluted way. It works, but simplify it.

## 3. No imputation or fabrication: PASS

- Invalid codes become missing and are never repaired (`clean_code`; case-only normalisation is acceptable).
- LLM replies that cannot be parsed are stored as missing. API errors are recorded and never turned into codes.
- With no API key, `llm_code.py` exits with status 2 and writes nothing. The NGrams fallback is a stub that raises, and the attempt is logged as a failure.
- If an entire stratum is uncoded, the frame becomes NaN with a reason. With no human codes, every gate is NOT_EVALUABLE (existing tests). Undefined κ (no variation) also gives NOT_EVALUABLE.
- Uncoded articles are excluded and the rest are reweighted. That is not imputation, but it rests on an assumption (MAR within the adjustment cell). See B2 for the level, and disclose it in the report.

## 4. Fetching (`fetch_texts.py`): PASS with should-fixes

What is right:
- Every live, robots-blocked, Wayback-availability, Wayback-fetch and NGrams attempt appends a log row with mode, HTTP status, success, character count, error, UTC time and snapshot URL.
- Wayback uses the availability API correctly (`https://archive.org/wayback/available?url=…&timestamp=<GKG 14-digit>`) and then fetches the `id_` raw capture.
- Politeness: descriptive User-Agent (contact optional, none hard-coded), 5 s per host, 1.5 s globally, 20 s timeout, no retry loops.
- robots.txt is checked before live fetches.
- The run is resumable. `--max-success 400` enforces the approved ceiling, and the human subsample is fetched first.

Should-fix:
- **S8a.** Redirects and wrong captures can be accepted as successes. Live fetches follow redirects, so a dead article that redirects to the home page or a section page returns 200 with more than 300 characters and is logged `live` = success. Wayback's `closest` snapshot can be years after publication, or a capture of a redirect, and neither its `status` nor its timestamp distance is checked. Fix: record `r.url` and `r.history`, and reject the fetch if the final path differs materially. Require `closest.status == "200"` and log the snapshot timestamp, with a maximum distance such as ±365 days. The coder rule (`UNREADABLE` for lists of links) only partly guards against this.
- **S8b.** robots.txt handling does not follow RFC 9309. An unreachable robots.txt or a 5xx response is treated as "allow all". RFC 9309 requires assuming complete disallow for 5xx or unreachable; 4xx may be treated as allow, as now.
- **S8c.** D16 says that articles whose text cannot be fetched "fall back to Mode B". The URL-slug coding part of Mode B, which needs no network, is not implemented anywhere. Nothing codes slugs and no slug-based metrics are produced. As a result, the per-mode precision/recall table that D16 requires (live / archived / NGrams / slug) cannot be complete.
- **N7 (nit).** An exception raised inside text extraction or the file write would stop the run without a log row. Wrap it. Also, robots.txt fetches are not throttled.

## 5. Codebook and human instructions: PASS with should-fix

- The codebook is clear. Edge cases are numbered, examples are labelled hypothetical, unreadable text is kept separate from N, and secondary cause is excluded from the binary.
- The international mapping (global oil/commodities, exchange rate, abroad) matches the D25 theme families (oil, commodities, FX, foreign central banks).
- The LLM receives the codebook verbatim, with no strata or flags.

Should-fix:
- **S9 (should-fix; affects the D25 gate).** The cause codes are not fully mutually exclusive.
  - Petrol or diesel **excise duty** is `fiscal_tax_administered` in the table ("excise duty cut") but `fuel_energy_domestic` under decision rule 1 ("…if it is a domestic pricing decision or tax"). These directly contradict each other.
  - Trader **hoarding** is listed under `domestic_food_supply`, while **cartels** are under `corporate_pricing`.
  - **MSP** sits in fiscal, while the food-supply cues overlap with it.
  - **Edible-oil import duty** could be fiscal or global commodities.

  These confusions do not change the international binary, but they lower the 10-category **cause κ**, and D25 needs cause κ ≥ 0.6. Add precedence rules: fuel tax → fiscal; hoarding by traders → food supply unless a named firm or cartel; MSP → fiscal; import duty → fiscal.
- **S10.** The codebook says "do not edit after Gate 2", but LLM coding starts on Day 2 and Gate 2 is at the end of Day 5. Freeze the codebook before the first LLM call and record its hash in the LLM output.
- **N8 (nit).** The instructions describe NGrams text as "rebuilt from word counts". It is stitched n-gram snippets, and the codebook should say "approximate text" as D16 requires.

**Time check.** 30 non-ECON articles × about 0.75 min (mostly quick N) + 80 English ECON × about 2 min + 40 Hindi × about 2.25 min ≈ 272 min ≈ 4.5 h, plus about 30 min of breaks and 20 min of codebook reading. That is feasible over two sessions of about 2.25 to 2.5 h, but there is no slack. The 4-minute cap per article and the 30-second rule for clearly irrelevant articles are what make it work. S4 (Marathi/Bengali rows) applies here too.

## Required fixes, by priority

| ID | Severity | Fix |
|---|---|---|
| B1 | **Blocker** | Restrict best-F2 candidates to the D9 variants (required `--variants` / config); refuse other flags |
| B2 | **Blocker** | Nonresponse post-stratification and bootstrap within stratum × period (2015–18 / later) cells; report response rates per cell |
| S1 | Should-fix (blocker if DOC passes) | DOC +60 stratum and DOC hit in the slug screen |
| S2 | Should-fix (blocker if the D34 tranches are kept) | Two-tranche draw under one seed, without ID collisions |
| S3 | Should-fix | Replacement rule for human-selected articles that fail to fetch |
| S4 | Should-fix | Confirm the coder reads Marathi/Bengali, or reallocate those 15 rows |
| S5 | Should-fix | Pre-register how D25 treats flagged-irrelevant articles and which flagged set gates |
| S6 | Should-fix | Document that the gating frame has no focal-language slug stratum |
| S7 | Should-fix | Pre-register which LLM coder the κ rule uses |
| S8a–c | Should-fix | Redirect and snapshot checks; RFC 9309 robots handling; Mode B slug coding |
| S9 | Should-fix | Precedence rules for overlapping cause codes |
| S10 | Should-fix | Freeze and hash the codebook before LLM coding |
| N1–N8 | Nit | As listed above |

---

## 6. Open issue: about 400 fetched texts (user approval) vs the D15 sample of about 1,250 (or about 1,550)

**What the code does now.** `fetch_texts.py` stops at 400 *saved* texts. The fetch order is the 150 human articles first, then the remaining 1,100 interleaved in proportion to stratum size. With a cap of 400, each stratum therefore gets its human articles plus about 22.7% of the rest.

Expected coded n under the cap:

| Stratum | Coded n (cap 400) |
|---|---|
| flagged | 95 |
| ECON-unflagged | 91 |
| slug | 50 |
| no-slug | 30 |
| hin flagged | 38 |
| hin unflagged | 38 |
| oth flagged | 29 |
| oth unflagged | 28 |
| **Total** | **≈ 400** |

Fetching the full sample at 70% or 85% success gives about 875 or 1,060 coded articles.

The figure of about 1,550 corresponds to reading the 1.5× oversampling as extra draws (see N1). Everything below scales by about √n. The sampler as written gives 1,250.

**Two structural facts decide most of the answer.**
1. **Human-based gates do not depend on the option.** The human 150 are fetched first under either option. The relevance, direction and cause κ, and therefore the D15 κ < 0.7 switch and the "cause κ ≥ 0.6" half of D25, have the same CIs either way. For binary relevance with n = 150, prevalence 0.35 and κ = 0.7, the 95% width is about 0.24, and P(κ̂ ≥ 0.7) is only about 0.51.
2. **If relevance κ < 0.7, the option does not matter for precision and recall at all.** The truth source becomes the 150 human codes, so precision, recall and D29 rest on those 150. Widths in that case: precision 0.25, gating recall 0.52, vernacular − English difference 1.20, which is uninformative. The full fetch only helps in the branch where the LLM codes are accepted.

**Simulated 95% interval widths, LLM codes accepted.** The populations and relevance rates are illustrative assumptions, not data (see `sim.py`): flagged 30k at 70% relevant; ECON-unflagged 300k at 4%; slug 20k at 25%; Hindi 6k/60k; other language 3k/30k; vernacular rates 65%/5%. True values under these assumptions: precision 0.69, gating recall 0.555, vernacular − English = −0.07.

| Gate statistic | Cap 400 (as coded) | Cap 400, reallocated toward unflagged strata | Full fetch, 70% success | Full fetch, 85% success |
|---|---|---|---|---|
| Precision (gate ≥ 0.5) | 0.150 | 0.176 | 0.102 | 0.093 |
| Gating recall (gate ≥ 0.6) | 0.312; P(wrong side) 0.32 | 0.282; 0.30 | 0.207; 0.22 | 0.187; 0.19 |
| English ECON recall | 0.43 | 0.43 | 0.32 | 0.28 |
| Vernacular ECON recall | 0.63 | 0.46 | 0.40 | 0.35 |
| D29 difference (gate \|d\| ≤ 0.15) | 0.76; P(pass, true d = −0.07) 0.54 | 0.66; 0.60 | 0.51; 0.69 | 0.46; 0.73 |
| D25 κ (flag vs international cause; flagged relevant ≈ 113 vs ≈ 250; prevalence 0.25, true κ 0.65) | 0.33; P(κ̂ ≥ 0.6) 0.72 | similar | 0.21; 0.80 | 0.21; 0.80 |
| Unscreened bound (0 relevant: CP upper) | n = 30: 0.116 | n = 20: 0.168 | n = 70: 0.051 | n = 85: 0.043 |

**Gate by gate.**
- **Precision (D15/D9).** Decided under either option, because precision is far above 0.5 in plausible cases. The cap costs about 1.5× in width and no decision.
- **Gating recall (D15/D9).** This gate matters most for the classifier switch. With the true value near the 0.6 threshold, the cap raises the chance of landing on the wrong side from about 0.2 to about 0.3. The width rises from about 0.20 to about 0.31. Width is driven by the ECON-unflagged stratum, which carries large weight and a low relevance rate.
- **Unscreened upper bound.** With the cap the bound is about 0.12; with the full fetch about 0.05. Multiplied by the very large non-ECON population, the implied recall floor is near zero under both options, so this stays a disclosure, not a decision.
- **D25.** The cap raises the κ CI width from about 0.21 to about 0.33. Because the cause-κ half of the gate rests on the fixed human sample, the full fetch cannot rescue a failure on that half.
- **D29.** Underpowered under either option, as D15's own risk note says. The interval for the difference (0.46 to 0.76 wide) is two to five times the ±0.15 band, so the pass/fail result is close to a coin flip (0.54 to 0.73 at a true gap of −0.07). Under the cap, the other-language unflagged stratum has about 28 articles at about 5% relevance. P(zero relevant) ≈ 0.24, in which case that language's recall is mechanically 1.0. **With the cap, D29 should be pre-declared as descriptive.**

**Cost of fetching everything.** About 1,250 articles at 2 to 3 requests each, with 1.5 s global and 5 s per-host spacing (Wayback on one host at 5 s), is about 2 to 3 hours of wall-clock fetching. LLM coding of about 2,500 calls is minor. This fits D16's "about 1 day". The constraint is therefore the user's approval, not feasibility.

**Recommendation.**
1. Ask the user to choose; design_final.md line 16 already flags this. Fetching the full D15 sample is the statistically preferred option. It narrows every LLM-branch gate by about 1.5× and moves D25 and the recall gate to usable precision.
2. If the cap of 400 stands:
   - (a) reallocate the 250 non-human slots toward the variance-driving unflagged strata (ECON-unflagged, Hindi and other-language unflagged), for example 70/110/40/20/30/50/25/55;
   - (b) pre-declare D29 as descriptive;
   - (c) code the remaining roughly 850 articles by URL slug (Mode B slug coding needs no fetching, but it is not implemented, see S8c), so the stratum totals are at least covered at slug level and reported separately;
   - (d) state in `analysis_plan.md` that D15's precision rationale ("LLM coding is cheap, so those strata are scaled") is only partly met.

   B2 matters more under the cap, because the per-cell nonresponse is larger.
