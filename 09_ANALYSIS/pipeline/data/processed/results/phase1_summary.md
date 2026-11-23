# Phase 1 summary (auto-generated; prediction language only)

Rounds in panel: 63; CPI-controlled sample: 59

## Primary cell (D19: 1-year median, h=0, IPI per 1 SD)
| model                | outcome      | focus   |   N |    beta |   se_ewc |   dof_B |     ci_lo |    ci_hi |       t |   p_wild |   partial_r2 |       r2 | controls                                                       |
|:---------------------|:-------------|:--------|----:|--------:|---------:|--------:|----------:|---------:|--------:|---------:|-------------:|---------:|:---------------------------------------------------------------|
| D19 primary-spec h=0 | y1_median_h0 | ipi_z   |  56 | 0.32791 | 0.127986 |       6 | 0.0147384 | 0.641082 | 2.56207 |   0.0365 |     0.142147 | 0.454302 | y1_median_lag;d_y1_median_lag;cpi_rt;food_rt;d_repo;mode_phone |

## D22 pseudo-real-time
| benchmark    | model                     |   n_eval |   rmse_ratio |    ci_lo |   ci_hi |   clark_west_t |   clark_west_p_one_sided |
|:-------------|:--------------------------|---------:|-------------:|---------:|--------:|---------------:|-------------------------:|
| AR1          | HEADLINE AR1+CPI+food+IPI |       37 |      1.16459 | 0.921418 | 1.60215 |       2.09316  |                0.0452678 |
| AR1+CPI+food | HEADLINE AR1+CPI+food+IPI |       37 |      1.03213 | 0.98385  | 1.11898 |      -0.511188 |                0.684508  |