# Audit gate report

Mode: A. Primary LLM coder: A. Baseline flag: flag_baseline.
Statuses: PASS, FAIL, NOT_EVALUABLE (missing data, nothing assumed).

| Gate | Statistic (95% CI) | Status | Consequence |
|---|---|---|---|
| D15 relevance kappa (LLM A vs LLM B (no human coding)), threshold 0.7 | 1.000 (1.000, 1.000), n=613 | NOT_APPLICABLE (no human coding by ruling) | NO HUMAN CODING (user ruling): LLM coder A is the truth source; kappa shown is LLM A vs LLM B (reliability only, not validation) |
| D15 direction kappa, threshold 0.6 | 0.941 (0.847, 1.000), n=58 | PASS | usable in E3/E4 claims |
| D15 cause kappa, threshold 0.6 | 0.874 (0.778, 0.979), n=58 | PASS | usable in E3/E4 claims |
| D15 precision >= 0.5 and gating recall >= 0.6 | P NA (NA, NA); R NA (NA, NA) | NOT_EVALUABLE | no decision (not evaluable) |
| D25 kappa(international theme, international cause) >= 0.6 and cause kappa >= 0.6 | 0.223 (-0.081, 0.511), n=32, coded international 7 | FAIL | descriptive only; no regression claims |
| D29 vernacular recall within 0.15 of English (ECON frame) | vern NA, eng 0.461, diff NA (NA, NA) | NOT_EVALUABLE | vernacular or English recall missing (no coded relevant articles or strata); not filled |

## Coverage by stratum x period cell (nothing imputed; MAR assumed within each cell)

| stratum | period | sampled | retrieved | llm_A | llm_B | human | retrieval_rate | llm_A_rate |
|---|---|---|---|---|---|---|---|---|
| econ_unflagged | late | 143 | 132 | 121 | 132 | 0 | 0.923 | 0.846 |
| econ_unflagged | old | 157 | 134 | 125 | 134 | 0 | 0.854 | 0.796 |
| flagged | late | 177 | 165 | 153 | 165 | 0 | 0.932 | 0.864 |
| flagged | old | 123 | 91 | 82 | 91 | 0 | 0.74 | 0.667 |
| hin_econ_unflagged | late | 54 | 51 | 0 | 51 | 0 | 0.944 | 0.0 |
| hin_econ_unflagged | old | 46 | 39 | 0 | 39 | 0 | 0.848 | 0.0 |
| hin_flagged | late | 68 | 65 | 0 | 65 | 0 | 0.956 | 0.0 |
| hin_flagged | old | 32 | 26 | 0 | 26 | 0 | 0.812 | 0.0 |
| nonecon_noslug | late | 41 | 39 | 0 | 0 | 0 | 0.951 | 0.0 |
| nonecon_noslug | old | 59 | 48 | 0 | 0 | 0 | 0.814 | 0.0 |
| nonecon_slug | late | 80 | 76 | 70 | 76 | 0 | 0.95 | 0.875 |
| nonecon_slug | old | 70 | 66 | 62 | 66 | 0 | 0.943 | 0.886 |
| oth_econ_unflagged | late | 62 | 59 | 0 | 59 | 0 | 0.952 | 0.0 |
| oth_econ_unflagged | old | 38 | 31 | 0 | 31 | 0 | 0.816 | 0.0 |
| oth_flagged | late | 66 | 65 | 0 | 65 | 0 | 0.985 | 0.0 |
| oth_flagged | old | 34 | 26 | 0 | 26 | 0 | 0.765 | 0.0 |

## F2 by variant (gating frame, all languages)

- flag_baseline: NA
- flag_price_family: NA
- flag_wb442: NA
- flag_strict: NA

## Files

metrics_prf.csv (precision/recall/F2 by variant, frame, language/retrieval-mode group, truth source), metrics_kappa.csv (human-LLM and LLM-LLM kappas by language and retrieval mode).