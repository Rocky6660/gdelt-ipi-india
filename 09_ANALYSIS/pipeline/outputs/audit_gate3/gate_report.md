# Audit gate report

Mode: A. Primary LLM coder: A. Baseline flag: flag_baseline.
Statuses: PASS, FAIL, NOT_EVALUABLE (missing data, nothing assumed).

| Gate | Statistic (95% CI) | Status | Consequence |
|---|---|---|---|
| D15 relevance kappa (LLM A vs LLM B (no human coding)), threshold 0.7 | 1.000 (1.000, 1.000), n=1026 | NOT_APPLICABLE (no human coding by ruling) | NO HUMAN CODING (user ruling): LLM coder A is the truth source; kappa shown is LLM A vs LLM B (reliability only, not validation) |
| D15 direction kappa, threshold 0.6 | 0.967 (0.915, 1.000), n=118 | PASS | usable in E3/E4 claims |
| D15 cause kappa, threshold 0.6 | 0.938 (0.885, 0.979), n=118 | PASS | usable in E3/E4 claims |
| D15 precision >= 0.5 and gating recall >= 0.6 | P 0.164 (0.128, 0.201); R 0.302 (0.202, 0.469) | FAIL | switch to best-F2 variant: flag_price_family |
| D25 kappa(international theme, international cause) >= 0.6 and cause kappa >= 0.6 | 0.331 (0.122, 0.534), n=86, coded international 14 | FAIL | descriptive only; no regression claims |
| D29 vernacular recall within 0.15 of English (ECON frame) | vern 0.881, eng 0.332, diff 0.549 (0.197, 0.759) | FAIL | gap > 0.15: E2 reported as a measurement result (differential theme recall under machine translation) |

## Unscreened non-ECON stratum (upper bound only)

1 of 87 coded articles relevant; share 0.011, exact 95% CI (0.000, 0.062). Recall floor if the upper limit applied to the whole stratum: 0.042. upper bound on the missed-relevant share outside ECON and price-keyword slugs; not an estimate.

## Slug-based metrics (Mode B route)

SLUG-BASED (URL slug only, not full text); reported separately, not used in any gate.
Coded n 137; gating precision 0.130, recall 0.563, F2 0.339; uninformative slug share 0.069.

## Coverage by stratum x period cell (nothing imputed; MAR assumed within each cell)

| stratum | period | sampled | retrieved | llm_A | llm_B | human | retrieval_rate | llm_A_rate |
|---|---|---|---|---|---|---|---|---|
| econ_unflagged | late | 143 | 132 | 132 | 132 | 0 | 0.923 | 0.923 |
| econ_unflagged | old | 157 | 134 | 134 | 134 | 0 | 0.854 | 0.854 |
| flagged | late | 177 | 165 | 165 | 165 | 0 | 0.932 | 0.932 |
| flagged | old | 123 | 91 | 91 | 91 | 0 | 0.74 | 0.74 |
| hin_econ_unflagged | late | 54 | 51 | 51 | 51 | 0 | 0.944 | 0.944 |
| hin_econ_unflagged | old | 46 | 39 | 39 | 39 | 0 | 0.848 | 0.848 |
| hin_flagged | late | 68 | 65 | 65 | 65 | 0 | 0.956 | 0.956 |
| hin_flagged | old | 32 | 26 | 26 | 26 | 0 | 0.812 | 0.812 |
| nonecon_noslug | late | 41 | 39 | 39 | 0 | 0 | 0.951 | 0.951 |
| nonecon_noslug | old | 59 | 48 | 48 | 0 | 0 | 0.814 | 0.814 |
| nonecon_slug | late | 80 | 76 | 76 | 76 | 0 | 0.95 | 0.95 |
| nonecon_slug | old | 70 | 66 | 66 | 66 | 0 | 0.943 | 0.943 |
| oth_econ_unflagged | late | 62 | 59 | 59 | 59 | 0 | 0.952 | 0.952 |
| oth_econ_unflagged | old | 38 | 31 | 31 | 31 | 0 | 0.816 | 0.816 |
| oth_flagged | late | 66 | 65 | 65 | 65 | 0 | 0.985 | 0.985 |
| oth_flagged | old | 34 | 26 | 26 | 26 | 0 | 0.765 | 0.765 |

## F2 by variant (gating frame, all languages)

- flag_baseline: 0.258
- flag_price_family: 0.288
- flag_wb442: 0.250
- flag_strict: 0.250

## Files

metrics_prf.csv (precision/recall/F2 by variant, frame, language/retrieval-mode group, truth source), metrics_kappa.csv (human-LLM and LLM-LLM kappas by language and retrieval mode).