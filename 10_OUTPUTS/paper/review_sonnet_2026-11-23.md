# Independent review (Claude Sonnet, 23 Nov 2026) - action list for the paper

## Cut / move to appendix (paper is overkill for a short paper)
- Remove pipeline labels (D-numbers, H1/H5, file paths, hashes, GB/chunk counts) from the main text.
- E1 (gate fails): one sentence. E3, E4, E5: appendix. E2: one paragraph max (monthly r 0.91; window r 0.66; 0.26 each alone).
- Audit apparatus: one table + caveat (LLM-only, no human validation). Extraction/budget/reconciliation details: appendix.

## Fix (claims vs numbers)
- Do not call it "pre-registered"/"audited" where untrue: Phase 1 ran before the audit; title says "audited" while 5.1 is pending.
- Trends: draft says 3 pulls 23-25 Nov; d17_summary shows 1 pull (provisional). Report actual pulls.
- "AR+CPI only" row: 0.089 [-0.16,0.34] vs 0.328 with food CPI/repo/phone controls -> specification dependence; explain it, don't call it fragility only.
- "Drop 2020-21" row also drops mode_phone; point estimate stable (0.297), only CI widens - say so.
- Report the robustness estimates (not only correlations): word share 0.26 p0.066; price family p0.058; core2018 0.28 p0.07; mean outcome 0.25 p0.07; 3m p0.11; current p0.09. Only 1-yr median clears 5% at h=0.
- Report the exact-fieldwork row: N=32, b=0.47 [0.12,0.83], p_wild 0.105.
- D22: also report vs AR1 (RMSE ratio 1.16, worse; CW p 0.045), not only the 1.03 / p 0.68 benchmark.
- Sample flow: 67 -> 63 -> 59 -> 56 -> 37 (D22), explained.
- Units: window index (max 2.16%) vs monthly (peak 0.031) - state the scales.
- IESH median is binned (1 pp): discuss what 0.33 per SD means.

## Add
- Figure: index vs 1-yr median/mean expectations (+CPI). Descriptive stats table. Coefficient plot (horizons, variants).
- Magnitude in context (1 SD of index in pp of article share).
- Multiple-testing paragraph: one pre-specified cell (p=0.036); rest exploratory, non-independent.
- Horse race: index vs Google Trends "inflation" in the D19 spec.
- Caveat: level correlation of persistent series is weak validation.
- Literature: Carroll (2003); Lamla & Lein (2014); Larsen, Thorsrud & Zhulanova (2021); plus ECB/Arndt already cited.
- State plainly that D17 fails (1 of 4 episodes vs >= 3) and the switch-chain outcome. Abstract + conclusion.

## Suggested framing
Measurement contribution: an open, reproducible GDELT news-attention index for India (English + vernacular), reliable (split-half 0.89) and tracking search interest (r 0.78), but not peaking in pre-specified item episodes. In-sample, +1 SD attention is associated with +0.33 pp in the 1-yr median expectation after real-time CPI (CI 0.015-0.641), sensitive to controls and outcome, with no out-of-sample gain over a CPI benchmark. Suggestive, non-causal evidence; not a validated predictor.
