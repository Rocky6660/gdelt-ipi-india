# News attention to inflation in India: a GDELT index

This repository builds and audits a **news-attention index of inflation for India** from the GDELT Global Knowledge Graph (2016–2026; a panel of 714 Indian news domains, with a core of 104 outlets in English and nine Indian languages). It then compares the index with the RBI Inflation Expectations Survey of Households (IESH).

The paper is a **measurement contribution**. The evidence on household expectations is exploratory and makes no causal claim.

📄 **Paper:** [`10_OUTPUTS/paper/paper_full.pdf`](10_OUTPUTS/paper/paper_full.pdf) (full, about 46 pp) · [`paper_short.pdf`](10_OUTPUTS/paper/paper_short.pdf) (short) · submission version: [`final/IPI_Paper_Final_v3.pdf`](10_OUTPUTS/paper/final/IPI_Paper_Final_v3.pdf)

---

## What the index is

For each IESH survey round, the index is the share of articles carrying price-related GDELT themes in the 14 days before fieldwork. It has these properties:

* **Outlets:** an equal-weight mean over the 104 "core" outlets, those present in at least 80% of windows.
* **De-duplication:** web addresses are de-duplicated within each day.
* **Validity rules:** day-level and outlet-level validity rules apply.
* **Monthly companion:** a monthly series is built on a sampled grid of days.

The theme definition was chosen by a pre-registered rule after an audit of 1,250 articles.

## Main findings (in brief)

| | Result |
|---|---|
| **Audit of GDELT's inflation tags** | Precision 0.16, recall 0.30 (gating frame); the broader price family has the best F2 (0.29) and becomes the primary definition. The audit failure holds under worst/best-case bounds for unretrieved articles. |
| **External validation** | Correlates 0.54 with Google searches for "inflation", but peaks in only 1 of 4 known price episodes, so the index is labelled *audited, not externally validated*. |
| **Expectations (exploratory)** | +0.25 pp per SD of the index in the next round's 1-year median expectation (95% CI 0.07–0.43, bootstrap p = 0.058, N = 56). Stable under trend, exchange-rate, window-length and outlet-panel checks; concentrated before 2022. |
| **Forecasting** | No out-of-sample gain over AR(1) + CPI + food. |
| **What moves attention** | Oil prices (Brent), not CPI surprises; joint tests over horizons 0–12 months do not reject. |

The full robustness record, with CIs and N, is in [`10_OUTPUTS/paper/REVISION_RESULTS.md`](10_OUTPUTS/paper/REVISION_RESULTS.md).

## Repository map

```
09_ANALYSIS/pipeline/
  scripts/
    bq_runner.py, sql/        BigQuery extraction (dry-run first, capped chunks, logged)
    build/build_index.py      outlet panel, window and monthly indices
    acquire/                  IESH, CPI, Trends, markets, policy-rate inputs
    audit/                    audit sample, text retrieval, LLM coding, precision/recall
    analysis/                 local projections, validation, forecasts, extensions
    revision/                 additional robustness checks
    checks/                   re-run check, paper assembly, number check, PDF export
  data/processed/             index series and all result tables (CSV/JSON)
  data/interim/audit/         audit manifest and article codes (no article texts)
  outputs/audit*/             audit metrics
  docs/                       design, decision ledger, codebook
  logs/                       BigQuery budget ledger, run logs
  PROGRESS.md                 time-stamped log of every step
10_OUTPUTS/paper/             paper (Markdown parts → assembled MD/HTML/PDF) and figures
02_RBI_IESH/raw/              IESH release workbook
```

## Reproducing

1. Install the requirements: `pip install -r 09_ANALYSIS/pipeline/scripts/requirements.txt` (Python 3.12).
2. Authenticate BigQuery with your own Google account: `gcloud auth application-default login`. Then set **your GCP project** in `09_ANALYSIS/pipeline/scripts/config.yaml`.
3. From `09_ANALYSIS/pipeline`, run the extraction (`scripts/bq_runner.py`, about 475 GB of queries) and then `scripts/build/build_index.py`.
4. Run the analysis scripts in `scripts/analysis/` and `scripts/revision/`.
5. Run `scripts/checks/gate3_rerun.py` to rebuild everything from the cached extraction and compare it with the reported outputs.
6. Build the paper:
   * `python scripts/checks/assemble_paper.py` fills every table from the result files;
   * `python scripts/checks/check_numbers.py` verifies the numbers in the text;
   * `python scripts/checks/export_pdf.py paper_full.md --toc` exports the PDF.

## What is *not* in the repository

* Raw GDELT extracts (Parquet) and the extraction cache. They are large; re-create them with step 3.
* Retrieved article texts (copyright). Only URLs and codes are kept.
* Credentials of any kind. No API keys or service-account files are stored, and `.gitignore` blocks them.

## Notes

* **Article coding:** audit coding was done by a large language model in two independent passes, with no human-coded subsample. The paper's AI-use statement gives the details.
* **Sources:** GDELT (Global Knowledge Graph and DOC API), RBI IESH, MoSPI CPI (base 2012), Google Trends, FRED / RBI market data.
