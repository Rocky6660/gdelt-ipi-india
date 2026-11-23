# Extensions E2, E4, E5: descriptive versions (auto-generated; association language only)

Figures: written to ext_figures/.
E4/E2 gates: PENDING audit gate (descriptive only).

## E5 ExcessAttention
| model                                         |   N |     beta |     ci_lo |    ci_hi |   p_wild |
|:----------------------------------------------|----:|---------:|----------:|---------:|---------:|
| E5 ExcessAttention (disinflation) in D19 spec |  56 | 0.257985 | -0.16186  | 0.67783  |   0.2465 |
| E5 IPI with ExcessAttention control           |  56 | 0.213366 | -0.129182 | 0.555914 |   0.117  |

## E5 peaks
| peak_month   |   peak_value |   baseline_prior12 |   rise_months_to_peak |   half_life_months | note                            |
|:-------------|-------------:|-------------------:|----------------------:|-------------------:|:--------------------------------|
| 2022-06      |    0.0312399 |         0.00983181 |                     4 |                  9 | coarse: grid days only under L3 |
| 2025-03      |    0.016355  |         0.0131002  |                     5 |                  2 | coarse: grid days only under L3 |
| 2026-04      |    0.0276271 |         0.0105729  |                     3 |                nan | coarse: grid days only under L3 |

## E4 S^int (corr with IPI 0.01)
| model                             |   N |       beta |      ci_lo |    ci_hi |   p_wild |
|:----------------------------------|----:|-----------:|-----------:|---------:|---------:|
| E4 S^int alongside IPI (D19 spec) |  56 | 0.00152873 | -0.207752  | 0.210809 |    0.989 |
| E4 IPI with S^int control         |  56 | 0.327903   |  0.0138957 | 0.64191  |    0.044 |

## E2 (window corr eng/ver 0.66)
| model                                |   N |      beta |      ci_lo |    ci_hi |   p_wild |
|:-------------------------------------|----:|----------:|-----------:|---------:|---------:|
| E2 eng only, D19 spec (y1_median)    |  56 | 0.258787  |  0.0147753 | 0.502799 |   0.043  |
| E2 ver only, D19 spec (y1_median)    |  56 | 0.264141  |  0.027167  | 0.501115 |   0.036  |
| E2 ver with eng control (y1_median)  |  56 | 0.205649  | -0.0482942 | 0.459592 |   0.0895 |
| E2 eng only, D19 spec (cur_median)   |  56 | 0.157377  |  0.0118174 | 0.302936 |   0.1075 |
| E2 ver only, D19 spec (cur_median)   |  56 | 0.130902  | -0.0406023 | 0.302407 |   0.1325 |
| E2 ver with eng control (cur_median) |  56 | 0.0831747 | -0.0859737 | 0.252323 |   0.306  |

## E2 monthly lead-lag (positive lag: vernacular later)
|   lag_ver_minus_eng |   corr |   N |
|--------------------:|-------:|----:|
|                  -6 |  0.632 |  99 |
|                  -5 |  0.677 | 100 |
|                  -4 |  0.7   | 101 |
|                  -3 |  0.739 | 102 |
|                  -2 |  0.78  | 103 |
|                  -1 |  0.797 | 104 |
|                   0 |  0.905 | 105 |
|                   1 |  0.752 | 104 |
|                   2 |  0.716 | 103 |
|                   3 |  0.671 | 102 |
|                   4 |  0.633 | 101 |
|                   5 |  0.578 | 100 |
|                   6 |  0.499 |  99 |