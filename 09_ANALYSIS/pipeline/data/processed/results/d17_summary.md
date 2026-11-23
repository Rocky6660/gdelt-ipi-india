# D17 external validation (auto-generated; validation of the index only, no outcomes)

Trends pulls: ['20261123'] (min per series 1; PROVISIONAL: D7 needs 3 pulls)

| check   | term      |   N |   r_raw | pass_r_ge_0_5   |   r_after_volume_trend |   r_partial_cpi_food |   partial_ci_lo |   partial_ci_hi | beyond_cpi_supported   |
|:--------|:----------|----:|--------:|:----------------|-----------------------:|---------------------:|----------------:|----------------:|:-----------------------|
| trends  | inflation | 129 |   0.777 | True            |                  0.668 |                0.78  |           0.651 |           0.895 | True                   |
| trends  | mehngai   | 129 |   0.257 | False           |                  0.183 |                0.295 |           0.182 |           0.673 | True                   |
| trends  | महंगाई    | 129 |   0.302 | False           |                  0.113 |                0.252 |          -0.008 |           0.434 | False                  |

## Episodes
| term              | months           |   N |   episode_mean |   p90_non_episode |       z | peak   |
|:------------------|:-----------------|----:|---------------:|------------------:|--------:|:-------|
| onion_2019_20     | 2019-09..2019-12 |   4 |         0.0074 |            0.0232 | -0.9061 | False  |
| fuel_2021_22      | 2021-02..2021-10 |   9 |         0.0108 |            0.0232 | -0.3571 | False  |
| post_ukraine_2022 | 2022-03..2022-07 |   5 |         0.029  |            0.0232 |  2.5103 | True   |
| tomato_2023       | 2023-06..2023-08 |   3 |         0.019  |            0.0232 |  0.9323 | False  |
Episodes peaking: 1 of 4 (accept if >= 3).

## Placebos (daily)
| term           | date       |   N |   window_mean |   context_p90 | peak   |
|:---------------|:-----------|----:|--------------:|--------------:|:-------|
| election_2019  | 2019-05-23 |   7 |        0.0067 |        0.0111 | False  |
| election_2024  | 2024-06-04 |   7 |        0.0231 |        0.0203 | True   |
| cwc_final_2023 | 2023-11-19 |   7 |        0.0149 |        0.0204 | False  |

## DOC cross-check
DOC series not yet available

## Cross-correlogram with CPI y/y (k > 0: IPI leads)
|   lag_ipi_leads |   N |     r |
|----------------:|----:|------:|
|              -6 | 119 | 0.068 |
|              -5 | 119 | 0.144 |
|              -4 | 119 | 0.209 |
|              -3 | 119 | 0.222 |
|              -2 | 119 | 0.264 |
|              -1 | 119 | 0.296 |
|               0 | 119 | 0.305 |
|               1 | 118 | 0.274 |
|               2 | 117 | 0.228 |
|               3 | 116 | 0.209 |
|               4 | 115 | 0.192 |
|               5 | 114 | 0.157 |
|               6 | 113 | 0.101 |