# Indian Inflation Perception Index (IPI) Research

Google Cloud Project ID: `[project removed]`

## Folder conventions
- `raw/`: source files exactly as downloaded; never overwrite.
- `processed/`: cleaned or transformed data.
- `07_ARTICLE_AUDIT/`: sampled articles, human/LLM coding and audit outputs.
- `08_MASTER_DATASETS/`: analysis-ready merged datasets.
- `09_ANALYSIS/`: scripts and notebooks.
- `10_OUTPUTS/`: tables and figures used in the paper.
- `11_DOCUMENTATION/`: data dictionary, source log, methods and decisions.

## Reproducibility rules
1. Preserve raw source files.
2. Record source URL, access date, date coverage, units, transformations and missingness.
3. Log every BigQuery dry run and execution, including estimated and actual bytes processed.
4. Do not store passwords, API keys, service-account keys or other credentials in this folder.
5. Do not claim an article was audited unless its text was actually retrieved and coded.
6. Do not silently splice incompatible CPI base-year series.

## Project status
This is a starter directory structure. It does not contain downloaded research data.
