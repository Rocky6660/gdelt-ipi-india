# D17 external validation (auto-generated; validation of the index only, no outcomes)

Trends pulls: ['20261123'] (min per series 1; PROVISIONAL: D7 needs 3 pulls)

| check   | term      |   N |   r_raw | pass_r_ge_0_5   |   r_after_volume_trend |   r_partial_cpi_food |   partial_ci_lo |   partial_ci_hi | beyond_cpi_supported   |
|:--------|:----------|----:|--------:|:----------------|-----------------------:|---------------------:|----------------:|----------------:|:-----------------------|
| trends  | inflation | 129 |   0.776 | True            |                  0.669 |                0.778 |           0.645 |           0.893 | True                   |
| trends  | mehngai   | 129 |   0.26  | False           |                  0.187 |                0.297 |           0.184 |           0.673 | True                   |
| trends  | महंगाई    | 129 |   0.304 | False           |                  0.117 |                0.249 |          -0.008 |           0.431 | False                  |

## Episodes
| term              | months           |   N |   episode_mean |   p90_non_episode |       z | peak   |
|:------------------|:-----------------|----:|---------------:|------------------:|--------:|:-------|
| onion_2019_20     | 2019-09..2019-12 |   4 |         0.0073 |            0.0224 | -0.8925 | False  |
| fuel_2021_22      | 2021-02..2021-10 |   9 |         0.0106 |            0.0224 | -0.3536 | False  |
| post_ukraine_2022 | 2022-03..2022-07 |   5 |         0.0283 |            0.0224 |  2.5154 | True   |
| tomato_2023       | 2023-06..2023-08 |   3 |         0.0187 |            0.0224 |  0.9527 | False  |
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
| kw_inflation    | 117 |   0.962 |
| theme_inflation | 117 |   0.965 |

## Cross-correlogram with CPI y/y (k > 0: IPI leads)
|   lag_ipi_leads |   N |     r |
|----------------:|----:|------:|
|              -6 | 119 | 0.07  |
|              -5 | 119 | 0.146 |
|              -4 | 119 | 0.21  |
|              -3 | 119 | 0.222 |
|              -2 | 119 | 0.263 |
|              -1 | 119 | 0.297 |
|               0 | 119 | 0.307 |
|               1 | 118 | 0.276 |
|               2 | 117 | 0.228 |
|               3 | 116 | 0.21  |
|               4 | 115 | 0.192 |
|               5 | 114 | 0.156 |
|               6 | 113 | 0.1   |