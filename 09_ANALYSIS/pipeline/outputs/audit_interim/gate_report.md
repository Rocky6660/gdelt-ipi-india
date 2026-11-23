# Audit gate report

Mode: A. Primary LLM coder: A. Baseline flag: flag_baseline.
Statuses: PASS, FAIL, NOT_EVALUABLE (missing data, nothing assumed).

| Gate | Statistic (95% CI) | Status | Consequence |
|---|---|---|---|
| D15 relevance kappa (LLM A vs LLM B (no human coding)), threshold 0.7 | 1.000 (1.000, 1.000), n=485 | NOT_APPLICABLE (no human coding by ruling) | NO HUMAN CODING (user ruling): LLM coder A is the truth source; kappa shown is LLM A vs LLM B (reliability only, not validation) |
| D15 direction kappa, threshold 0.6 | 0.919 (0.809, 1.000), n=45 | PASS | usable in E3/E4 claims |
| D15 cause kappa, threshold 0.6 | 0.892 (0.782, 0.973), n=45 | PASS | usable in E3/E4 claims |
| D15 precision >= 0.5 and gating recall >= 0.6 | P NA (NA, NA); R NA (NA, NA) | NOT_EVALUABLE | no decision (not evaluable) |
| D25 kappa(international theme, international cause) >= 0.6 and cause kappa >= 0.6 | 0.531 (0.250, 0.881), n=23, coded international 5 | FAIL | descriptive only; no regression claims |
| D29 vernacular recall within 0.15 of English (ECON frame) | vern NA, eng 0.396, diff NA (NA, NA) | NOT_EVALUABLE | vernacular or English recall missing (no coded relevant articles or strata); not filled |

## Slug-based metrics (Mode B route)

SLUG-BASED (URL slug only, not full text); reported separately, not used in any gate.
Coded n 60; gating precision NA, recall NA, F2 NA; uninformative slug share 0.069.

## Coverage by stratum x period cell (nothing imputed; MAR assumed within each cell)

| stratum | period | sampled | retrieved | llm_A | llm_B | human | retrieval_rate | llm_A_rate |
|---|---|---|---|---|---|---|---|---|
| econ_unflagged | late | 143 | 99 | 98 | 99 | 0 | 0.692 | 0.685 |
| econ_unflagged | old | 157 | 98 | 94 | 95 | 0 | 0.624 | 0.599 |
| flagged | late | 177 | 124 | 121 | 122 | 0 | 0.701 | 0.684 |
| flagged | old | 123 | 69 | 67 | 67 | 0 | 0.561 | 0.545 |
| hin_econ_unflagged | late | 54 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| hin_econ_unflagged | old | 46 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| hin_flagged | late | 68 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| hin_flagged | old | 32 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| nonecon_noslug | late | 41 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| nonecon_noslug | old | 59 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| nonecon_slug | late | 80 | 57 | 57 | 57 | 0 | 0.712 | 0.712 |
| nonecon_slug | old | 70 | 50 | 48 | 48 | 0 | 0.714 | 0.686 |
| oth_econ_unflagged | late | 62 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| oth_econ_unflagged | old | 38 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| oth_flagged | late | 66 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |
| oth_flagged | old | 34 | 0 | 0 | 0 | 0 | 0.0 | 0.0 |

## F2 by variant (gating frame, all languages)

- flag_baseline: NA
- flag_price_family: NA
- flag_wb442: NA
- flag_strict: NA

## Files

metrics_prf.csv (precision/recall/F2 by variant, frame, language/retrieval-mode group, truth source), metrics_kappa.csv (human-LLM and LLM-LLM kappas by language and retrieval mode).