# Verification of the BigQuery extraction tooling

Verifier: independent agent, 17 Nov 2026. Scope: `scripts/bq_runner.py`, `scripts/sql/*.sql`, `scripts/config.yaml`, `scripts/seeds/top20_indian_outlets.csv`, `scripts/tests/test_runner.py`, `docs/extraction_plan.md`. I checked them against `docs/design/design_final.md`, decisions D1, D2, D3, D4, D9, D10, D11, D13, D17, D34, D36 and D37.

Method: I read the code and SQL line by line, parsed every SQL file with sqlglot (BigQuery dialect), ran the existing tests (20 pass), and added `scripts/tests/test_verifier.py`. That file has 7 passing checks and 5 `xfail(strict=True)` tests. Each xfail test reproduces one defect below and will start to pass, or be reported as XPASS, once that defect is fixed. I ran no BigQuery query, used no credentials and made no network calls. I did not edit the tooling.

**Overall: FAIL.** There are 3 blockers. All of them are small code changes, and the design logic underneath is sound.

---

## Check 1: dry run, caps, quota and failed jobs. **FAIL**

What passes:
- `do_run` refuses a job unless the ledger has a `DRYRUN` row whose hash covers the exact SQL text and parameters. The hash is taken after the optional partition inlining, so a dry run without inlining cannot authorise a run with it. Tested.
- `maximum_bytes_billed = ceil(dry × 1.05)` is set on every real Q2, probe, Q1 and theme job.
- The hard cap is 670 GB and the Q2 stage cap is 650 GB. A per-job scan limit of 60 GB applies to Q2 and to all other jobs by default. Jobs that started but never finished count at their cap. If the quota is unknown, the run is refused.
- A pruning failure is safe: if `IN UNNEST(@param)` does not prune, the dry run shows the full-table bytes and the 60 GB limit refuses the job.

Defects:
- **V1 (blocker).** `Ledger.job_states()` keeps only the latest row for each `(label, hash)`. When a job is re-run, either after a `RUN_FAILED` or with `--allow-rerun`, the earlier job's billed bytes disappear from `committed()`. Test `test_rerun_keeps_earlier_cost`: 48 + 48 GB is counted as 48 GB. This matters because the try block also covers `export_table`. If the query succeeds and is billed but the download fails, the job is recorded as `RUN_FAILED`. A re-run is then allowed without `--allow-rerun`, pays again (the cache is useless because the table is updated every 15 minutes), and the first payment drops out of the ledger total.
- **V2 (blocker, same fix).** A failed job counts at its *actual* billed bytes when the API reports a number. When the API reports 0, it counts at 0, not at its cap. Test `test_failed_counted_at_cap`. The acceptance rule is "failed jobs counted at cap".
- **V3 (blocker, same fix).** The quota-used accounting computes `used = max(quota_used, ledger_actual) + pending`. That is correct when `quota_used` is a live INFORMATION_SCHEMA reading, because the reading already includes the ledger jobs. It is wrong for `quota_used_override_bytes`, which is the static Gate-0 figure the human sets: spend from before the project is dropped as soon as ledger spend exceeds it. Test `test_override_quota_added_to_ledger`: 100 GB used before the project plus 550 GB in the ledger is treated as 550 GB, so a job that brings the true total to 680 GB is allowed.
- **V4 (should-fix).** The 60 GB per-job limit is compared with dry-run bytes, not the cap. A 59.9 GB chunk therefore gets a 62.9 GB `maximum_bytes_billed`, and D4 says "a failed job costs at most 60 GB". Test `test_per_job_cap_not_above_60`. Either compare the cap, or have `plan` split chunks at 60/1.05 GB.
- **V6 (should-fix).** `get_quota_used` runs a *real* INFORMATION_SCHEMA query before every run and in `ladder`. That query has no dry run, no `maximum_bytes_billed` and no ledger row. INFORMATION_SCHEMA jobs bill at least 10 MB each, so the cost is small, but it breaks D36's rule that every job has a ledger check, a dry run and a cap. Ledger it as `quota_check` with a cap, or read it once per session.
- **V7 (should-fix).** `ladder` sets the Q2 limit to 650 GB minus the quota used *now*. Once the probe, Q1 and theme lookup have run, that subtracts about 20 GB of project spend that D4 has already budgeted inside the 670 GB total. The result can be a lower rung than the rule implies. Store the Gate-0 reading once (before the project) and use only that.
- **V8 (should-fix).** `plan` reports the total dry-run bytes of the stage but does not refuse when (Stage A + Stage B + committed Q2) is over 650 GB. The run-time stage cap would then stop the extraction partway through instead of before it starts. Add the check to `plan` and `run-chunk`.
- Nit: the check-then-start sequence is not atomic across processes, because the flock covers only each single append. Two concurrent runners could each pass the cap check. Use one lock around check plus `RUN_STARTED`, or a single-runner lock file.

## Check 2: Q2 gating and the first-month check. **FAIL**

What passes: `gate_q2_prereqs` requires `RUN_OK` rows for `probe_one_partition` and `q1_outlets`, plus `gate1a_frozen.json` whose SHA-256 matches `source_superset.csv`. Tested. `run-chunk` refuses any chunk outside the first month until `mark-checked`, and `mark-checked` requires every first-month chunk to be `RUN_OK`.

Defects:
- **V5 (blocker).** Both gates are keyed only on the label prefix `q2_`, and the first-month check sits only in the `run-chunk` CLI, not in `do_run`. Running `run --sql scripts/sql/q2_stage_template.sql --label stageA_2022 --params-file p.json` after a matching `dryrun` therefore skips the probe/Q1/freeze gate, the Q2 stage cap and the first-month check. Test `test_q2_gate_by_sql_file`: execution reaches the client. Fix: in `do_run`, treat a job as Q2 whenever `sql_file` is `q2_stage_template*.sql`, *or* the label starts with `q2_`. Require that Q2 labels match the plan, and move the first-month check into `do_run`.
- **V9 (should-fix).** Gate 1a freezes "outlets **and themes**" (D34), but the freeze hash covers only `source_superset.csv`. `price_alt` is still the config placeholder, and nothing stops Stage A from running with it. Nothing requires `theme_lookup` to have run either. Add `price_alt`, `trim_themes` and the `theme_lookup` `RUN_OK` to the freeze record and check all of them in the Q2 gate.

## Check 3: SQL. **PASS on D1 and D4.4; one blocker on output granularity (V10)**

- **`_PARTITIONTIME`:** every table reference is filtered, either `IN UNNEST(@…)` or `= TIMESTAMP(@probe_day)`. No expression wraps `_PARTITIONTIME` on the filter side, so nothing defeats pruning. Parameter pruning is [UNVERIFIED], but the inlining fallback produces valid literals (`[TIMESTAMP '…']`, `ARRAY<TIMESTAMP>[]`). I checked this on the real Q2 file.
- **Columns (checked with a sqlglot AST test):**
  - The `win` CTE reads exactly D1's full set and `oth` reads exactly the reduced set.
  - The probe reads `DATE`, `SourceCommonName` and `DocumentIdentifier` on one day.
  - Q1 reads only `SourceCommonName` and `TranslationInfo`, as D2 requires.
  - The theme lookup reads `SourceCommonName` and `Themes`.
  - `GCAM`, `Locations`, `V2Locations` and `V2Themes` are never referenced.
- **Outputs:**
  - (a) `A` rows cover every ECON / ECON_INFLATION / price-flagged article, with the full V1 `Themes` string, or the D4.6 trim plus a FARM_FINGERPRINT when `trim_themes` is set.
  - (b) `S` rows are outlet × day × host × language × section counts on window days, with distinct-URL counts and word sums from V2Tone field 7 (offset 6, which is correct). `D` rows are outlet × day × language counts on non-window days, with no URL.
  - All four UNION ALL branches have 27 columns in the same order with compatible types. I checked this by reading and with an AST test.
  - Theme flags are derivable offline from `Themes` (D9, D10, D14).
- **Correctness by reading:**
  - `DIV(DATE, 1000000)`, the window function after GROUP BY in the probe, `SPLIT(...)[SAFE_OFFSET(6)]`, the `ARRAY(SELECT … UNNEST(SPLIT…))` trim, `REGEXP_CONTAINS` with a `CONCAT(@price_alt)` pattern, and `FROM rows_, UNNEST(SPLIT(...))` are all valid BigQuery.
  - I found no expression that is likely to fail. All five files parse in sqlglot.
- **V10 (blocker; it cannot be repaired after Stage A without a rescan).** `url_section` is only the *first* path segment, `^https?://[^/]+/([^/?#]+)`. D40 builds edition patterns from "the 200 most frequent URL path prefixes per outlet", and D42(a) needs *all-article* local counts per city (median ≥ 100 local articles per window). For the main Hindi and English dailies the city sits in the second or third segment (for example TOI `/city/<city>/`, Bhaskar `/local/<state>/<city>/`, Amar Ujala `/<state>/<city>/`). City-level denominators would therefore exist only for flagged (`A`) articles, not for all articles. Fix: group `S` rows by the first 2–3 path segments, for example `REGEXP_EXTRACT(document_identifier, r'^https?://[^/]+/((?:[^/?#]+/){0,2}[^/?#]*)')`, or emit a path-prefix column at depth 3. Then check the effect on the Stage A output size on the first chunk.
- **V11 (should-fix).** D4.4(i) is "adopted only if its dry-run bytes equal one scan". The query references `gkg_partitioned` twice, and the CTEs `win_f` and `oth_f` are each referenced twice. Whether BigQuery bills each reference's own column × partition set is exactly the [UNVERIFIED] point. Today the check is manual. Automate it: compare the Q2 dry run against Σ `colbytes` (full columns over window days + reduced columns over other days), refuse form (i) if the difference is above about 1%, and record the result. Also, `colbytes` ignores `--inline-partitions`.
- **V12 (should-fix, D13).** D13's first exclusion is "global count < 50% of its 28-day median". Q2 filters on `@sources`, so no global daily GKG count is produced anywhere. Add a query `SELECT DATE(_PARTITIONTIME) d, COUNT(*) n … GROUP BY d` over the sampled partitions. It reads only the pseudo-column, costs about 10 MB, and needs a dry run and cap like any other job.
- **V13 (should-fix, D11).** Deduplication is only within one day and one `(source, host, lang, section)` group: `COUNT(DISTINCT url_norm)` cannot be added up across days. D11's window share is "on deduplicated articles (normalised URL within outlet)". Either state that deduplication is day-level, or add `HLL_COUNT.INIT(url_norm)` sketches, which can be merged offline across a window. `url_norm` also leaves `http`/`https` and trailing-slash variants as separate URLs.
- Nit: the theme lookup scans global `Themes` on 12 days, which may cost 10–25 GB. D2 and D4 count it in the "tests ≤ 20 GB" line, so check its dry run before running it (the plan already says so).
- Nit: the source filter matches exact `SourceCommonName` values. Unpooled subdomains that are absent from the superset (for example `profit.ndtv.com`) are dropped. A suffix match on the registered domain costs no extra bytes.

## Check 4: sampling grid. **PASS**

- `ALLOWED_STEPS = {1,2,3,4,6}`. Any other step, including 7 and 14, raises an error.
- The offset is seeded and deterministic (`random.Random(f"{seed}-{step}")`) with a fixed epoch, and is the same for all outlets. Tested: every weekday is covered at each step.
- The rung table matches D4: L0/L1 30 days with steps 1/2 from 2015-02; L2 21 days, step 3; L3 14 days, step 4, from 2016-01; L4 14 days, step 6, from 2017-01. Tested.
- The always-sampled dates 2019-05-23, 2024-06-04 and 2023-11-19 ± 3 days are present on every rung. Tested.
- Windows are the L days ending the day before `fieldwork_start`. Tested on all rungs. Rounds without dates are skipped, not imputed.
- Window and other days are disjoint, and Stage A and Stage B are disjoint.
- Nit: `read_rounds` also drops a round whose `fieldwork_end` is missing, although only the start is needed.
- Nit: write grid membership (`on_grid`) into the plan JSON, so that D11's "grid days only" monthly series does not depend on re-running the Python.

## Check 5: ledger and logs. **PASS, with should-fixes**

- The columns are exactly `timestamp, job_label, sql_file, params_hash, dry_run_bytes, cap_bytes, actual_billed_bytes, status`, with pre-run estimate and post-run actual (D4.5, D36). The file is opened only in append mode under flock, and refusals are logged as `REFUSED: …` rows. It lives at `logs/budget_ledger.csv`.
- Should-fix: add a `job_id` column (and `destination`), so that you can reconcile with INFORMATION_SCHEMA and re-download a finished result without a re-run.
- Should-fix (V14): split `RUN_FAILED` into a query failure and `EXPORT_FAILED`, and add an `export --job-id` command.
- Should-fix: write a per-run text log to `logs/` with the quota reading, plan totals, the export method and the rows expected versus written. Today these go only to stdout. Only the ledger is in `logs/`.
- Should-fix (export): if the Storage Read API fails partway, `list_rows` resumes from `start_index=flushed`. Storage-API stream order is not the `tabledata.list` order, so the resumed download can duplicate or skip rows. On fallback, discard the partial parts and restart from row 0. Also treat `rows_written != rows_expected` as a failure, not just a manifest field.
- Nit: the header is written based on an existence check made before the lock, so two first writers could both write a header.

## Check 6: outlet seed list. **PASS, with should-fix**

- All 23 domains are real and correctly spelled: timesofindia.indiatimes.com, thehindu.com, hindustantimes.com, indianexpress.com, ndtv.com, livemint.com, economictimes.indiatimes.com, business-standard.com, moneycontrol.com, news18.com, indiatoday.in, deccanherald.com, tribuneindia.com, bhaskar.com, jagran.com, amarujala.com, livehindustan.com, navbharattimes.indiatimes.com, lokmat.com, anandabazar.com, mathrubhumi.com, dinamalar.com and eenadu.net. I found no errors.
- The single-state and home-state labels are plausible, and the uncertain ones are marked [UNVERIFIED].
- The D2 fix is met: the major `.com` outlets are seeded directly, the parent `indiatimes.com` is added automatically, and the GDELT domain-to-country file is read. Its column 2 is the FIPS code; India is `IN` in FIPS too, so the matching works.
- Should-fix: the list is called "top-20" but it is not a readership top 20. Several of the largest IRS dailies are missing: Malayala Manorama (manoramaonline.com), Daily Thanthi (dailythanthi.com), Rajasthan Patrika (patrika.com), Dinakaran (dinakaran.com), Sakshi (sakshi.com), Prabhat Khabar (prabhatkhabar.com), Gujarat Samachar (gujaratsamachar.com), Divya Bhaskar (divyabhaskar.co.in), Sakal (esakal.com) and Punjab Kesari (punjabkesari.in). Q1's Indian-language hits may pick some of them up, but D2 reports coverage of the top 20, so the seed should be the IRS list, with `readership_rank` filled in. The English list could also add telegraphindia.com, deccanchronicle.com and financialexpress.com.

---

## Required fixes

| # | Severity | Fix |
|---|---|---|
| V1–V3 | **blocker** | Ledger accounting: sum *every* finished run row (never drop earlier runs of the same label and hash); count `RUN_FAILED` at `max(actual, cap)` when the query failed; treat the quota override as pre-project spend that is *added* to ledger spend. Remove the `xfail` marks in `test_verifier.py` once fixed. |
| V5 | **blocker** | Enforce the Q2 gate, the stage cap and the first-month check inside `do_run` for any job using a `q2_stage_template*.sql` file, whatever its label. |
| V10 | **blocker** | `S`-row URL section must keep the first 2–3 path segments, so that edition-path city denominators (D40, D42a) exist for all articles. It cannot be fixed after the scan. |
| V4 | should-fix | Per-job limit on `cap` (≤ 60 GB), or split chunks at 60/1.05. |
| V6 | should-fix | Ledger and cap the INFORMATION_SCHEMA quota query, or run it once. |
| V7 | should-fix | Ladder: subtract only the Gate-0 (pre-project) quota from 650 GB. |
| V8 | should-fix | `plan` and `run-chunk` refuse when the planned Q2 total plus committed Q2 is over 650 GB. |
| V9 | should-fix | Gate 1a freeze also covers `price_alt` and `trim_themes`, and requires a `theme_lookup` `RUN_OK`. |
| V11 | should-fix | Automate the D4.4(i) one-scan test (Q2 dry run versus Σ column bytes) and make `colbytes` respect inlining. |
| V12 | should-fix | Add the global daily GKG count query for D13. |
| V13 | should-fix | HLL sketches, or a documented day-level definition, for window deduplication; normalise scheme and trailing slash. |
| V14 | should-fix | Separate export failure from query failure; add `job_id` and destination to the ledger; add an export-retry command; restart the fallback download from 0; fail on a row-count mismatch. |
| — | should-fix | Persistent run log in `logs/`. |
| — | should-fix | Make the seed list a real IRS top 20, with `readership_rank`. |
| — | nit | Lock around check plus start; header race; `read_rounds` needs only the start date; `on_grid` in the plan; suffix-match sources; check the theme-lookup dry-run size. |

---

## Re-verification (round 2, 17 Nov 2026)

Scope: the executor's fixes to `bq_runner.py` (now 1,069 lines), `sql/q2_stage_template.sql`, the new `sql/global_daily_count.sql`, `config.yaml`, the 36-row seed list and `docs/extraction_plan.md`.

What I did:
- I checked that the executor had removed the five round-1 xfail marks without weakening the test bodies. The tests are unchanged.
- I read the new code and SQL.
- I added round-2 tests to `scripts/tests/test_verifier.py`. Three new tests pass. Four strict xfail tests reproduce R1–R4 below.

Results: `test_runner.py` and `test_verifier.py` give 39 passed and 4 xfailed. One failure, `test_audit.py::test_fetch_main_logs_every_attempt_and_respects_ceiling`, is in the audit workstream (W3). It is outside this scope and not caused by the BigQuery tooling, but it should be reported to W3.

I ran no BigQuery query, used no credentials and made no edits to the tooling.

**Overall: PASS. No blockers remain.** Four should-fix items (R1–R3 and R5) should be done before Stage A starts, because each is cheap now and costly once Stage A has run.

### Round-1 items

| Item | Status | Evidence |
|---|---|---|
| V1 rerun undercount | **fixed** | `committed()` now adds every terminal row and never replaces one. Test passes (48 + 48 = 96 GB). |
| V2 failed job at cap | **fixed** | `RUN_FAILED` and `EXPORT_FAILED` count at billed bytes if above 0, else at the cap. I accept counting at billed bytes when they are above 0: that is the true charge, and it never undercounts. |
| V3 quota override | **fixed** | `used = max(live reading, override + ledger, ledger) + pending`. Test passes. |
| V4 per-job 60 GB | **fixed** | `check_run_allowed` compares the cap, and `plan` splits chunks at 60/1.05 GB. |
| V5 Q2 gate bypass | **fixed** | `is_q2_job` is true for any `q2_stage_template*.sql` file (form iii included) or any `q2_` label. In `do_run`, every run path now requires probe, Q1 and theme lookup to be `RUN_OK`. It also checks the outlet hash and the frozen `price_alt`/`trim_themes`, requires the label to be in a plan with dates matching the planned chunk, applies the first-month check, and checks the plan budget. The test now ends in `Refused`. |
| V6 quota query | **fixed** | The quota query is dry-run, capped (20–100 MB), ledgered as `quota_check`, and read once per process. |
| V7 ladder quota | **fixed** | `quota --record-gate0` stores the pre-project reading, and `ladder` uses it. |
| V8 plan budget | **fixed** | `check_plan_budget` checks committed Q2 plus the remaining chunks of both stage plans against 650 GB, in both `plan` and `do_run`. An `EXPORT_FAILED` chunk is counted in both terms, which errs on the safe side. |
| V9 theme freeze | **fixed** | The freeze needs a `theme_lookup` `RUN_OK` and `price_alt_confirmed: true`. It records `price_alt` and `trim_themes`, and the Q2 gate compares them with the config. |
| V10 URL granularity | **fixed (blocker cleared)**, see R3 | `url_section` keeps up to 3 directory segments, and `A` rows carry `url_path`. City denominators now exist for all articles. |
| V11 one-scan test | **fixed** | `colbytes` and `ladder --columns` write `onescan_<rung>.json` (tolerance 1%), and `plan` refuses without a passing result. `colbytes` now respects inlining. |
| V12 D13 global count | **added**, see R2 | `global_daily_count.sql` reads no column, only `_PARTITIONTIME`. |
| V13 dedup | **added**, see R5 | Normalisation now strips scheme, `www.`, query and trailing slash. HLL++ sketches are added. |
| V14 export | **fixed** | `EXPORT_FAILED` is separate from `RUN_FAILED` and carries `job_id` and `destination`. `export --job-id` re-downloads without paying again (its row adds 0 bytes). A run is refused while an `EXPORT_FAILED` row exists. The fallback restarts from row 0, and a row-count mismatch raises an error. |
| Run log | **fixed** | `logs/bq_runner.log`. |
| Seeds | **fixed** | 36 rows, see check 6. |
| Nits | **fixed** | One lock (`logs/.runner.lock`) now covers check plus `RUN_STARTED`; the header-race check happens under the lock; `on_grid` is in the plan. The `read_rounds` end-date nit is unchanged and harmless. |

### Checks

1. **Dry run, caps, quota, failed jobs: PASS.** One should-fix remains (R1).
2. **Q2 gating and first-month check: PASS.**
3. **SQL: PASS.**
   - `_PARTITIONTIME` is filtered everywhere, and no expression defeats pruning.
   - The column sets are unchanged and exact (AST test passes). GCAM, Locations, V2Locations and V2Themes are never read.
   - All 29 UNION ALL columns line up by position and type, and all files parse.
   - `HLL_COUNT.INIT(expr, 12)` uses a valid constant precision and ignores NULL inputs.
   - The `url_norm` alternation regex strips both ends.
   - Should-fix items remain (R2, R3, R5).
4. **Sampling grid: PASS.** Unchanged; tests pass.
5. **Ledger and logs: PASS.** The new columns are `job_id` and `destination`; the file is still append-only, and the run log is in `logs/`.
6. **Outlet seeds: PASS.**
   - The 13 added domains are real and correctly spelled: manoramaonline.com, dailythanthi.com, patrika.com, dinakaran.com, sakshi.com, prabhatkhabar.com, gujaratsamachar.com, divyabhaskar.co.in, esakal.com, punjabkesari.in, telegraphindia.com, deccanchronicle.com, financialexpress.com.
   - The single-state labels are plausible and marked [UNVERIFIED].
   - The list is honestly described in the plan as hand-keyed, not an IRS ranking, with `readership_rank` blank. D2 allows that.
   - One defect remains (R4).

### Remaining items (none are blockers)

| # | Severity | Finding | Fix |
|---|---|---|---|
| R1 | **should-fix before Stage A** | `committed()` tracks open `RUN_STARTED` rows in a dict keyed by `(label, hash)`. Suppose a runner is killed after submitting (the BigQuery job continues and bills) and the same chunk is re-run (allowed, because there is no `RUN_OK` or `EXPORT_FAILED` row). The second `RUN_STARTED` overwrites the first and the `RUN_OK` pops it, so the killed job's cost, up to 60 GB, disappears. Test `test_crashed_start_then_rerun_keeps_cap`. A live INFORMATION_SCHEMA reading covers this through `max()`, but the override path does not. This environment does kill long-running processes. | Count each `RUN_STARTED` that has no terminal row before the next `RUN_STARTED` of the same key. Better still, set `job_id` before submitting (`client.query(job_id=…)`), log it in `RUN_STARTED`, and have a re-run refuse until `reconcile --job-id` records that job's real outcome. |
| R2 | **should-fix** | `global_daily_count.sql` reads no column, so its dry run is about 0 B, and the cap is `ceil(0 × 1.05) = 0`. BigQuery bills at least 10 MiB per query, so the job will most likely fail ("10485760 or higher required"). If 0 is instead treated as unset, the job would run uncapped. The D13 global count then never arrives. Test `test_zero_byte_job_cap_meets_minimum_billing`. | Apply a cap floor in `do_run` of `max(ceil(dry × 1.05), 10 MiB × number of table references)`. Check the floor against the hard cap as usual. |
| R3 | **should-fix (output size)** | The `{1,3}` directory pattern captures the article slug when a URL has 3 or more directories before the file. The TOI city format `/city/<city>/<slug>/articleshow/<id>.cms` gives `city/mumbai/<slug>/`, so TOI city `S` rows become one row per article, each with HLL sketches. Totals are still correct, and prefixes can be truncated and summed offline, so the problem is size only. Test `test_url_section_excludes_slug[TOI]`. | Stop the section at the first segment that looks like a slug, for example one containing a digit, or longer than 30 characters, or with 3 or more hyphens. Or use depth 2 plus a separate depth-3 column for known multi-level outlets. Check the result on the first chunk. |
| R4 | nit | `parent_domain("divyabhaskar.co.in")` returns `co.in`, which adds a junk entry to the superset. It is harmless for bytes but visible at Gate 1a. Test `test_parent_domain_not_public_suffix`. | Skip parents that are public suffixes (`co.in`, `org.in`, `net.in`, …). |
| R5 | **should-fix before Stage A** | The HLL++ sketches use BigQuery's ZetaSketch format, and nothing in `requirements.txt` or the code can merge them offline. No maintained Python decoder exists; Java zetasketch does. The plan says "mergeable offline", but no route is specified. Without one, the cross-day dedup that D11's primary window series relies on cannot be computed, and the sketches only add output bytes. | Before Stage A, document and test a merge route. One option is to load the `S` parquet into a sandbox dataset (load jobs are free, within the 10 GiB storage limit) and run `HLL_COUNT.MERGE` over the sketch columns only, capped and ledgered like any other job. The other is a Java zetasketch step. Otherwise, declare D11's dedup to be day-level and drop the sketches. |
| R6 | nit | `export --job-id J --label L` with no matching `EXPORT_FAILED` row still writes a `RUN_OK` row under any label, so `export … --label q1_outlets` could satisfy a Gate-1a prerequisite or `mark-checked`. | Require a matching `EXPORT_FAILED` row (same `job_id`) and take the label from that row. |
| R7 | nit | HLL output size is unmeasured. A precision-12 sketch is sparse for small groups (a few bytes per distinct URL) and up to about 3–4 KB per group when dense. This is likely within the 3 GB per-job limit, but the first-chunk check must report it, as the plan now says. | Report the sketch bytes on the first chunk. |

**Verdict: PASS. No blockers.** Before `run-chunk` on Stage A, fix R1, R2, R3 and R5 (all small). R4, R6 and R7 are nits.
