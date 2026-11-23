# D17 external validation (auto-generated; validation of the index only, no outcomes)

Trends pulls: ['20261123'] (min per series 1; PROVISIONAL: D7 needs 3 pulls)

| check   | term      |   N |   r_raw | pass_r_ge_0_5   |   r_after_volume_trend |   r_partial_cpi_food |   partial_ci_lo |   partial_ci_hi | beyond_cpi_supported   |
|:--------|:----------|----:|--------:|:----------------|-----------------------:|---------------------:|----------------:|----------------:|:-----------------------|
| trends  | inflation | 129 |   0.542 | True            |                  0.409 |                0.546 |           0.311 |           0.753 | True                   |
| trends  | mehngai   | 129 |   0.107 | False           |                  0.039 |                0.19  |           0.082 |           0.637 | True                   |
| trends  | महंगाई    | 129 |   0.359 | False           |                  0.252 |                0.286 |           0.1   |           0.494 | True                   |

## Episodes
| term              | months           |   N |   episode_mean |   p90_non_episode |       z | peak   |
|:------------------|:-----------------|----:|---------------:|------------------:|--------:|:-------|
| onion_2019_20     | 2019-09..2019-12 |   4 |         0.0169 |            0.0366 | -0.7161 | False  |
| fuel_2021_22      | 2021-02..2021-10 |   9 |         0.024  |            0.0366 | -0.0571 | False  |
| post_ukraine_2022 | 2022-03..2022-07 |   5 |         0.0472 |            0.0366 |  2.1102 | True   |
| tomato_2023       | 2023-06..2023-08 |   3 |         0.027  |            0.0366 |  0.2244 | False  |
Episodes peaking: 1 of 4 (accept if >= 3).

## Placebos (daily)
| term           | date       |   N |   window_mean |   context_p90 | peak   |
|:---------------|:-----------|----:|--------------:|--------------:|:-------|
| election_2019  | 2019-05-23 |   0 |           nan |           nan | False  |
| election_2024  | 2024-06-04 |   0 |           nan |           nan | False  |
| cwc_final_2023 | 2023-11-19 |   0 |           nan |           nan | False  |

## DOC cross-check
| term            |   N |   r_raw |
|:----------------|----:|--------:|
| kw_inflation    | 117 |   0.777 |
| theme_inflation | 117 |   0.765 |

## Cross-correlogram with CPI y/y (k > 0: IPI leads)
|   lag_ipi_leads |   N |      r |
|----------------:|----:|-------:|
|              -6 | 119 | -0.142 |
|              -5 | 119 | -0.049 |
|              -4 | 119 |  0.058 |
|              -3 | 119 |  0.119 |
|              -2 | 119 |  0.26  |
|              -1 | 119 |  0.286 |
|               0 | 119 |  0.31  |
|               1 | 118 |  0.284 |
|               2 | 117 |  0.229 |
|               3 | 116 |  0.236 |
|               4 | 115 |  0.233 |
|               5 | 114 |  0.25  |
|               6 | 113 |  0.2   |