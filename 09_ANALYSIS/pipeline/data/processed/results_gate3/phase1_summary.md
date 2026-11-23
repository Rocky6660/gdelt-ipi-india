# Phase 1 summary (auto-generated; prediction language only)

Rounds in panel: 63; CPI-controlled sample: 59

## Primary cell (D19: 1-year median, h=0, IPI per 1 SD)
| model                | outcome      | focus   |   N |     beta |    se_ewc |   dof_B |    ci_lo |    ci_hi |       t |   p_wild |   partial_r2 |       r2 | controls                                                       |
|:---------------------|:-------------|:--------|----:|---------:|----------:|--------:|---------:|---------:|--------:|---------:|-------------:|---------:|:---------------------------------------------------------------|
| D19 primary-spec h=0 | y1_median_h0 | ipi_z   |  56 | 0.251151 | 0.0748136 |       6 | 0.068089 | 0.434213 | 3.35703 |   0.0575 |     0.111616 | 0.434881 | y1_median_lag;d_y1_median_lag;cpi_rt;food_rt;d_repo;mode_phone |

## D22 pseudo-real-time
| benchmark    | model                     |   n_eval |   rmse_ratio |    ci_lo |   ci_hi |   clark_west_t |   clark_west_p_one_sided |
|:-------------|:--------------------------|---------:|-------------:|---------:|--------:|---------------:|-------------------------:|
| AR1          | HEADLINE AR1+CPI+food+IPI |       37 |     1.12359  | 0.868872 | 1.54801 |        2.28589 |                0.0355064 |
| AR1+CPI+food | HEADLINE AR1+CPI+food+IPI |       37 |     0.995788 | 0.947064 | 1.07    |        1.47399 |                0.100244  |