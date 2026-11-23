# BigQuery extraction plan (D1-D4, D9, D10, D34, D37)

Project `[project removed]` (sandbox: 1 TiB queries/month, 10 GiB storage, no billing). Table `gdelt-bq.gdeltv2.gkg_partitioned`, always filtered on `_PARTITIONTIME`. Nothing has been run; all code is untested against BigQuery. Items marked [UNVERIFIED] are checked by the step named.

All commands: `python scripts/bq_runner.py <cmd>` from the repo root. Every job is logged in `logs/budget_ledger.csv` (timestamp, job label, sql file, params hash, dry-run bytes, cap, actual billed bytes, status). Caps live in `scripts/config.yaml`: hard 670 GB, Q2 stage 650 GB, 60 GB scanned per Q2 job, `maximum_bytes_billed = ceil(dry run x 1.05)`. 1 GB is 1e9 bytes, so caps are slightly conservative against the 1 TiB quota.

## Order of work

1. **Auth.** `gcloud auth application-default login` (human) and `gcloud config set project [project removed]`. Install `pip install -r scripts/requirements.txt`.
2. **Quota check (Gate 0 / D4.1).** `quota --record-gate0` (once, before any project job; `ladder` subtracts only this pre-project reading from 650 GB). The reading is itself a ledgered `quota_check` job (dry run, byte cap 100 MB). It reads this month's billed bytes from `INFORMATION_SCHEMA.JOBS_BY_USER` (falls back to printing the manual check). If unreadable, set `quota_used_override_bytes` in `config.yaml`; runs are refused while quota is unknown.
3. **Day-1 probe (D2).** `dryrun --job probe` then `run --job probe`. One partition, about 2 GB. Read: do `*.indiatimes.com` siblings share one `SourceCommonName` (`n_hosts_per_source > 1`)? If pooled, the window-level outlet key is the host parsed from `DocumentIdentifier`. Also confirms that the day in `DATE` equals the partition day [UNVERIFIED].
4. **Q1 (D2).** `dryrun --job q1`, `run --job q1`. 1 day in 6 (step 6, seeded grid), columns `SourceCommonName` and `TranslationInfo` only, about 8-10 GB. Output goes to `data/processed/bq_out/q1_outlets/part-*.parquet`.
5. **Theme lookup (D9).** `dryrun --job theme`, `run --job theme`. One partition per sample year (`theme_lookup_dates`, 12 days, Themes and SourceCommonName only). Confirm `ECON_INFLATION` has `n_all > 0` in every year in the V1 `Themes` column, and fix the price-family alternation `price_alt` in `config.yaml`. The default there is a placeholder. Check the dry-run size first; shrink `theme_lookup_dates` if it is not cheap.
6. **Outlet freeze (Gate 1a, human).**
   - Download GDELT's domain-to-country lookup to `data/raw/gdelt_domain_country_lookup.tsv` (first two columns: domain, country; India rows are `IN`/`India`).
   - `seed-sources` builds `data/processed/source_superset.csv` from: the hand-keyed top-20 (`scripts/seeds/top20_indian_outlets.csv`, plus parent domains such as `indiatimes.com`), the country lookup, `.in` domains from Q1, and Q1 Indian-language hits. It prints the full list for review.
   - Human reviews, edits the CSV, replaces the placeholder `price_alt` in `config.yaml` using the theme-lookup output and sets `price_alt_confirmed: true`, then `freeze-outlets --by <name>` writes `data/processed/gate1a_frozen.json` (outlet-file hash, `price_alt`, theme list, `trim_themes`). It refuses without a `theme_lookup` `RUN_OK` row. **Any job using a `q2_stage_template*.sql` file (whatever its label) is refused unless the probe, Q1 and theme lookup have `RUN_OK` rows, the frozen hash and theme settings match, the label and dates are in a plan, and the first-month check has passed** (D2/D34 fixes).
   - Also run `run --job daycount` (D13 global daily record count over the sampled partitions; about 10 MB).
   - The source list does not reduce billed bytes (table not clustered on source), so a generous superset costs nothing extra in scan, only in output rows.
7. **Ladder dry runs (Gate 0b).** Put `data/raw/iesh_rounds.csv` (round, fieldwork_start, fieldwork_end; rounds without dates are skipped, not imputed) in place. `ladder` dry-runs the full Q2 for L0 to L4 (real partition lists, real columns) and recommends the lowest rung with Q2 <= 650 GB minus quota used. `ladder --columns` also logs bytes per column and runs the D4.4(i) one-scan test (Q2 dry run vs the sum of column dry runs, tolerance 1%); `plan` refuses without a passing result for the rung. Check the query form (D4.4): the single-statement dry-run bytes must equal the sum of the listed column-partitions. If `_PARTITIONTIME IN UNNEST(@param)` does not prune [UNVERIFIED], pass `--inline-partitions` or set `inline_partitions: true`. Human records rung, query form, and the measured reduced/full ratio (replaces the 0.65 placeholder in D37). Set `rung:` in `config.yaml`. If no rung fits, escalate (raw files for non-window days, or window-only design).
8. **Stage A, first one-month chunk.** `plan --rung L? --stage A` makes monthly chunks, dry-runs each, and halves any chunk whose cap (dry run x 1.05) would exceed 60 GB. `plan` also refuses if committed Q2 plus all still-planned Q2 bytes exceed 650 GB. Then `run-chunk --rung L? --stage A --label <first label>`. Check the output (row counts, theme string size, HLL sketch columns and the added `url_section`/`url_path` columns against the D4.6 5 GB projection, ledger estimate vs actual, download method), then `mark-checked --rung L? --stage A --by <name>`.
9. **Rest of Stage A, then Stage B.** `run-chunk` for each remaining label; chunks other than the first month are refused until `mark-checked`. Repeat `plan` and the same one-month check for Stage B. Stage A is window days from 2022-01-01; Stage B is all other window days plus the sampled non-window days on the rung. The partitions are disjoint. Slip rule (D34): if Stage A is not done by end of day 2, move the rung down one step; by end of day 3, L4.

## Query forms (D4.4)

- `sql/q2_stage_template.sql` is form (i). One statement, two table references: full set (`DATE, SourceCommonName, GKGRECORDID, DocumentIdentifier, Themes, V2Tone, TranslationInfo`) on `@window_ts`; reduced set (`DATE, SourceCommonName, Themes, TranslationInfo`) on `@other_ts`. Output rows, one schema:
  - `A`: article rows for every ECON-tagged or ECON_INFLATION/price-flagged article, full `Themes` (or the D4.6 trimmed string plus a hash if `trim_themes`).
  - `S`: window days, outlet x day x host x language x URL-section counts over all source articles (incl. distinct-URL counts for deduplication) and word sums from V2Tone field 7.
  - `D`: non-window days, outlet x day x language counts only (no URL on those days).
- `sql/q2_stage_template_iii.sql` is form (iii), the fallback: one row per panel article with reduced fields, no aggregates.
- Form (ii) (temp tables / CTAS) is not scripted. It is used only if (i) fails the one-scan test, with a 1-day storage-meter test first.

## Failure handling

- Ledger accounting adds every run (re-runs pay again). `RUN_FAILED` and `EXPORT_FAILED` count at billed bytes if above 0, else at the cap; unfinished `RUN_STARTED` jobs count at their cap; the quota override is pre-project spend and is added to ledger spend. A failed download is `EXPORT_FAILED` (query already paid); recover with `export --job-id J --label L` (adds 0 bytes).
- `job_id` and `destination` are ledger columns; `logs/bq_runner.log` keeps quota readings, plan totals, export method and rows expected vs written.
- Results are read through the Storage Read API; on any error the runner discards partial parts and re-reads from row 0 with `list_rows` paging; rows written must equal rows expected. The method used is in `manifest.json` next to the parquet parts.
- Results sit in anonymous result tables (not sandbox storage) [UNVERIFIED; the first chunk shows whether this holds].
- Tests: `python -m pytest scripts/tests -q`.

## Notes on the Q2 output
- `S` rows are grouped by the first up to 3 URL directory segments (`url_section`); `A` rows on window days also carry the full `url_path`. Window-level deduplication uses mergeable HLL++ sketches (`url_hll`, `url_hll_infl`, precision 12) of normalised URLs (no scheme, www, query or trailing slash); `n_distinct_urls` is day-level only. Check output size on the first chunk; if too large, drop the sketches (a rescan is then needed for dedup).
- The source filter is an exact match on `SourceCommonName`; unpooled subdomains absent from the superset (e.g. `profit.ndtv.com`) are dropped, so add them at Gate 1a from the Q1 list.
- `seeds/top20_indian_outlets.csv` is a hand-keyed list of 36 outlets, not an IRS ranking; `readership_rank` is blank until IRS figures are obtained. The theme lookup may cost 10-25 GB: check its dry run before running.
