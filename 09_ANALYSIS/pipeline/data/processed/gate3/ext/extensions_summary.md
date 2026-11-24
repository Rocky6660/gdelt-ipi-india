# Extensions E2, E4, E5: descriptive versions (auto-generated; association language only)

Figures: written to ext_figures/.
Index column: variant_price_family; E2 language splits use the baseline tag (no price-family language split built).

## E5 ExcessAttention
| model                                         |   N |     beta |      ci_lo |    ci_hi |   p_wild |
|:----------------------------------------------|----:|---------:|-----------:|---------:|---------:|
| E5 ExcessAttention (disinflation) in D19 spec |  56 | 0.291419 | -0.0274126 | 0.610251 |   0.1845 |
| E5 IPI with ExcessAttention control           |  56 | 0.153954 |  0.0396818 | 0.268225 |   0.056  |

## E5 peaks
| peak_month   |   peak_value |   baseline_prior12 |   rise_months_to_peak |   half_life_months | note                            |
|:-------------|-------------:|-------------------:|----------------------:|-------------------:|:--------------------------------|
| 2016-05      |    0.0277623 |          0.023883  |                     1 |                  1 | coarse: grid days only under L3 |
| 2018-10      |    0.0346641 |          0.0167071 |                     3 |                  3 | coarse: grid days only under L3 |
| 2022-04      |    0.0496796 |          0.0167816 |                     3 |                  7 | coarse: grid days only under L3 |
| 2026-04      |    0.0674698 |          0.0177571 |                     3 |                  4 | coarse: grid days only under L3 |

## E4 S^int (corr with IPI 0.28)
| model                             |   N |       beta |      ci_lo |    ci_hi |   p_wild |
|:----------------------------------|----:|-----------:|-----------:|---------:|---------:|
| E4 S^int alongside IPI (D19 spec) |  56 | -0.0530348 | -0.285261  | 0.179192 |   0.6695 |
| E4 IPI with S^int control         |  56 |  0.261826  |  0.0803151 | 0.443337 |   0.0325 |

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