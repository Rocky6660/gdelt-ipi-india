# Gate 3 verification re-run (auto-generated)

Status: **PASS**

Steps: build_index re-run from cache; phase1 re-run (variant_price_family, ipi_monthly_variant_price_family) vs data/processed/results_switched; d17 re-run; audit_metrics re-run

| file | match | detail |
|---|---|---|
| index/ipi_window.csv | True | identical bytes |
| index/ipi_monthly.csv | True | identical bytes |
| index/ipi_daily.csv | True | identical bytes |
| index/panel_outlets.csv | True | identical bytes |
| phase1/d19_national_lp.csv | True | identical bytes |
| phase1/d20_regime.csv | True | identical bytes |
| phase1/d22_forecast_eval.csv | True | identical bytes |
| phase1/d23_monthly_lp.csv | True | identical bytes |
| phase1/d19_persistence.csv | True | identical bytes |
| d17/d17_validation.csv | True | identical bytes |
| audit/gate_statuses | True | {'D15_relevance_kappa': ('NOT_APPLICABLE (no human coding by ruling)', 'NOT_APPLICABLE (no human coding by ruling)'), 'D15_direction_kappa': ('PASS', 'PASS'), 'D15_cause_kappa': ('PASS', 'PASS'), 'D15_precision_recall': ('FAIL', 'FAIL'), 'D29_vernacular_recall': ('FAIL', 'FAIL'), 'D25_international_kappa': ('FAIL', 'FAIL')} |
| audit/metrics_prf.csv | True | identical bytes |