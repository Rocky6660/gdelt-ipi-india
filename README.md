# Media attention to inflation in India: a reproducible GDELT index

This repository builds and audits a **media-attention index of inflation for India** from the GDELT Global Knowledge Graph and relates it to the RBI's Inflation Expectations Survey of Households (IESH).

The index is the share of price-related articles in a balanced core of 104 Indian news outlets, 54 of them in Indian languages, during the two weeks before each survey round from 2016 to 2026.

The project is an **exploratory measurement exercise**: a documented, reproducible pipeline and an account of where it fails. It makes no causal claim.

📄 **Paper (submission version):** [`10_OUTPUTS/paper/final/IPI_Paper_Final_v3.pdf`](10_OUTPUTS/paper/final/IPI_Paper_Final_v3.pdf)

---

## Main findings

The numbers below are as reported in the submission version.

| | Result |
|---|---|
| **Audit of GDELT's inflation tag** | Precision **0.16**, recall **0.30** (1,250 articles coded by a large language model; agreement with one model, not accuracy). The conclusion holds under every assumption about the articles that could not be retrieved. By a rule fixed in advance, the index switches to the broader price family of themes (F2 0.29 vs 0.26). |
| **External validation** | Peaks in only **1 of 4** pre-specified price episodes. When the monthly series is built exactly as the regression index, its correlation with Google searches for "inflation" is **0.42**, below the 0.5 bar. The index is therefore *audited, not externally validated*. |
| **Household expectations (exploratory)** | One SD of additional coverage is associated with a **0.25 pp** larger change in the median one-year-ahead expectation (95% CI 0.07–0.43; bootstrap p = 0.058; N = 56 rounds). The size is stable across time trends, exchange-rate controls, window lengths and outlet composition, but no time- or price-control variant reaches the 5% level. The association is concentrated before 2022. |
| **Forecasting** | No out-of-sample gain: adding the index to AR(1) + CPI + food leaves the RMSE unchanged (ratio 1.00; Clark–West p = 0.100). |
| **What moves coverage** | Monthly responses to oil prices (Brent) and to CPI surprises are **not jointly significant** (block-bootstrap p = 0.20 and 0.93). |

## Repository map

```
10_OUTPUTS/paper/final/       submission version of the paper (PDF, DOCX)
10_OUTPUTS/paper/archive/     superseded drafts (paper_full, paper_short); not the paper of record
10_OUTPUTS/paper/parts/       Markdown sources assembled into the archived drafts
10_OUTPUTS/paper/figures/     figures
10_OUTPUTS/paper/REVISION_RESULTS.md   additional robustness checks with CIs and N
09_ANALYSIS/pipeline/
  scripts/                    all code (see "How to reproduce")
  data/processed/             index series and result tables (CSV/JSON)
  data/interim/audit/         audit manifest and article codes (URLs and codes only)
  outputs/                    audit metrics
  docs/                       design, decision ledger, codebook
  logs/                       BigQuery budget ledger and run logs
  PROGRESS.md                 time-stamped log of every step
02_RBI_IESH/raw/              RBI IESH workbook, as published
requirements.txt              pinned Python environment (Python 3.12)
```

## How to reproduce

Set-up:

* Python 3.12: `pip install -r requirements.txt`
* BigQuery access with **your Google account / your GCP project**: run `gcloud auth application-default login`, then set `project:` in `09_ANALYSIS/pipeline/scripts/config.yaml`.

Run all commands from `09_ANALYSIS/pipeline`, in this order. Every script documents its inputs and outputs in its header.

1. **Inputs** (`scripts/acquire/`)
   * `net_check.py`
   * `iesh.py`, then `iesh_merge_rounds.py`
   * `cpi.py`, then `build_cpi.py` and `build_cpi_items.py`
   * `policy_markets.py` and `repo_rate_rbi.py`
   * `trends.py`
   * `doc_series.py`
2. **GDELT extraction** (BigQuery, about 475 GB of queries; dry-run first, capped and logged)
   * `scripts/bq_runner.py` and `scripts/run_stage.py --stage A` / `--stage B`
   * `scripts/checks/d34_reconcile.py` (independent recount)
3. **Index**
   * `scripts/build/build_index.py`
   * `scripts/build/e1_exposure.py`
4. **Audit** (`scripts/audit/`)
   * `build_audit_population.py`
   * `sample_audit.py`, then `scale_audit_weights.py`
   * `fetch_texts.py`
   * coding with `session_batch.py` or `llm_code.py` (the latter needs your own model API key in an environment variable)
   * `audit_metrics.py --no-human`
5. **Definition switch and validation** (`scripts/analysis/`)
   * `d9_switch.py`
   * `d17_validation.py`
6. **Expectations and extensions** (`scripts/analysis/`)
   * `phase1.py`
   * `extensions_descriptive.py`, `e3_salience.py`
   * `paper_outputs.py`, `paper_extras.py`
7. **Additional checks** (`scripts/revision/`)
   * `r2_audit.py`
   * `r2_index.py`, then `r2_index.py --heavy`
8. **Verification and paper**
   * `scripts/checks/gate3_rerun.py` rebuilds from the cached extraction and compares the outputs.
   * `scripts/checks/assemble_paper.py`, then `check_numbers.py`, then `export_pdf.py archive/paper_full.md --toc` regenerate the archived draft. Its tables are filled from the result files and its numbers are checked against them.

## Licence and data

* **Code:** MIT (see [`LICENSE`](LICENSE)).
* **Derived data** (index series, audit codes, result tables, figures): **CC BY 4.0**.
* **Not redistributed:** raw GDELT extracts and retrieved article texts. Re-create the extracts with step 2; the audit keeps only URLs and codes.
* **Third-party file:** the RBI IESH workbook is included as published and remains under RBI's terms.
* **No credentials:** no API keys or credentials are stored in the repository, and `.gitignore` blocks them.

## Notes

* **Article coding:** the audit was coded by a large language model in two passes, with no human-coded subsample. The paper's AI-use statement gives the details.
* **Sources:** GDELT (Global Knowledge Graph, DOC API), RBI IESH, MoSPI CPI (base 2012), Google Trends, FRED and RBI market data.
