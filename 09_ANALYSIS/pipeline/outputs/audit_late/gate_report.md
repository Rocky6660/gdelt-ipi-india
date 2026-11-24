# Audit gate report

Mode: A. Primary LLM coder: A. Baseline flag: flag_baseline.
Statuses: PASS, FAIL, NOT_EVALUABLE (missing data, nothing assumed).

| Gate | Statistic (95% CI) | Status | Consequence |
|---|---|---|---|
| D15 relevance kappa (LLM A vs LLM B (no human coding)), threshold 0.7 | 1.000 (1.000, 1.000), n=413 | NOT_APPLICABLE (no human coding by ruling) | NO HUMAN CODING (user ruling): LLM coder A is the truth source; kappa shown is LLM A vs LLM B (reliability only, not validation) |
| D15 direction kappa, threshold 0.6 | 1.000 (1.000, 1.000), n=60 | PASS | usable in E3/E4 claims |
| D15 cause kappa, threshold 0.6 | 1.000 (1.000, 1.000), n=60 | PASS | usable in E3/E4 claims |
| D15 precision >= 0.5 and gating recall >= 0.6 | P 0.155 (0.073, 0.266); R 0.092 (0.030, 0.765) | FAIL | switch to best-F2 variant: flag_price_family |
| D25 kappa(international theme, international cause) >= 0.6 and cause kappa >= 0.6 | 0.399 (0.106, 0.682), n=54, coded international 7 | FAIL | descriptive only; no regression claims |
| D29 vernacular recall within 0.15 of English (ECON frame) | vern 0.881, eng 0.065, diff 0.817 (-0.170, 0.980) | FAIL | gap > 0.15: E2 reported as a measurement result (differential theme recall under machine translation) |

## Unscreened non-ECON stratum (upper bound only)

1 of 87 coded articles relevant; share 0.011, exact 95% CI (0.000, 0.062). Recall floor if the upper limit applied to the whole stratum: 0.031. upper bound on the missed-relevant share outside ECON and price-keyword slugs; not an estimate.

## Coverage by stratum x period cell (nothing imputed; MAR assumed within each cell)

| stratum | period | sampled | retrieved | llm_A | llm_B | human | retrieval_rate | llm_A_rate |
|---|---|---|---|---|---|---|---|---|
| econ_unflagged | late | 143 | 132 | 11 | 132 | 0 | 0.923 | 0.077 |
| econ_unflagged | old | 157 | 134 | 9 | 134 | 0 | 0.854 | 0.057 |
| flagged | late | 177 | 165 | 12 | 165 | 0 | 0.932 | 0.068 |
| flagged | old | 123 | 91 | 9 | 91 | 0 | 0.74 | 0.073 |
| hin_econ_unflagged | late | 54 | 51 | 51 | 51 | 0 | 0.944 | 0.944 |
| hin_econ_unflagged | old | 46 | 39 | 39 | 39 | 0 | 0.848 | 0.848 |
| hin_flagged | late | 68 | 65 | 65 | 65 | 0 | 0.956 | 0.956 |
| hin_flagged | old | 32 | 26 | 26 | 26 | 0 | 0.812 | 0.812 |
| nonecon_noslug | late | 41 | 39 | 39 | 0 | 0 | 0.951 | 0.951 |
| nonecon_noslug | old | 59 | 48 | 48 | 0 | 0 | 0.814 | 0.814 |
| nonecon_slug | late | 80 | 76 | 6 | 76 | 0 | 0.95 | 0.075 |
| nonecon_slug | old | 70 | 66 | 4 | 66 | 0 | 0.943 | 0.057 |
| oth_econ_unflagged | late | 62 | 59 | 59 | 59 | 0 | 0.952 | 0.952 |
| oth_econ_unflagged | old | 38 | 31 | 31 | 31 | 0 | 0.816 | 0.816 |
| oth_flagged | late | 66 | 65 | 65 | 65 | 0 | 0.985 | 0.985 |
| oth_flagged | old | 34 | 26 | 26 | 26 | 0 | 0.765 | 0.765 |

## F2 by variant (gating frame, all languages)

- flag_baseline: 0.100
- flag_price_family: 0.119
- flag_wb442: 0.072
- flag_strict: 0.072

## Files

metrics_prf.csv (precision/recall/F2 by variant, frame, language/retrieval-mode group, truth source), metrics_kappa.csv (human-LLM and LLM-LLM kappas by language and retrieval mode).