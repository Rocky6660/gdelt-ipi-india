# Handoff: GDELT Inflation Perception Index (IPI), state on 23 Nov 2026

Deadline: 25 Nov 2026. Research design: 09_ANALYSIS/pipeline/docs/design/design_final.md (+ ledger.md for all user rulings).
Code: 09_ANALYSIS/pipeline/scripts. Python env: %LOCALAPPDATA%\gdelt_ipi_py312\Scripts\python.exe (Python 3.12, all packages).
Run everything from 09_ANALYSIS/pipeline. BigQuery auth is cached (your Google account / your GCP project).

## User rulings to respect (see docs/design/ledger.md)
- Opus only; no subagents/reviewer agents. No causal claims. No fabricated data. Report blockers.
- Audit: fetch all ~1,550 sampled articles; LLM-code all languages (Marathi/Bengali by model); NO human coding
  (two independent LLM passes + agreement instead; paper states no human validation).
- IESH pre-2020 rounds: ruling (b) month rule (fieldwork_start = 1st of survey-ended month), flagged fs_rule;
  robustness on exact-date rounds only. Built by scripts/acquire/iesh_merge_rounds.py (67 rounds since 2015).
- Primary outcome: 1-year MEDIAN (D7 rule). Rung L3 (14-day windows, 1-in-4 grid, from 2016) chosen by the ladder.
- R5: HLL sketches dropped; denominators day-level distinct; report cross-day duplicate rate.

## Done
- Gate 0/1a: quota recorded; outlets (source_superset.csv, 936 domains) + 15 price themes frozen (gate1a_frozen.json).
- BigQuery: probe, Q1, theme lookup, daycount; Stage A COMPLETE (49 chunks, data/processed/bq_out/q2_A_L3_*). ~110 GB billed.
- Data: IESH national (iesh_national_excel.csv, from RBI Excel in 02_RBI_IESH/raw), city tables (iesh_city_round.csv),
  CPI base 2012 2013-01..2025-12 (cpi2012_allindia.csv, cpi2012_state.csv via build_cpi.py), markets (Brent, INR, G-sec).
- Code tested: scripts/build/build_index.py (synthetic), scripts/analysis/phase1.py (D19-D23; real CPI/IESH, dummy IPI).

## Next steps, in order
1. Stage B extraction (00_RUN/next.json id 14_stageB is queued; or run directly):
   python scripts/bq_runner.py plan --rung L3 --stage B
   python scripts/bq_runner.py run-chunk --rung L3 --stage B --label q2_B_L3_2016-01 --allow-rerun
   python scripts/check_chunk.py data/processed/bq_out/q2_B_L3_2016-01      (must PASS: A rows > 0)
   python scripts/bq_runner.py mark-checked --rung L3 --stage B --by "<who>"
   python scripts/run_stage.py --stage B --rest        (~350 GB, several hours)
   NOTE: other-day chunks use sql/q2_stage_other.sql; line 70 must read
   "WHERE COALESCE(ARRAY_LENGTH(@window_ts), 0) >= 0" (empty array params arrive as NULL).
2. build_index.py expects Q2 parquet under data/raw/q2/ but outputs are in data/processed/bq_out/q2_*: fix the glob.
   Set siblings_pooled true; write scripts/build/flags.csv (D10 families) from theme_lookup output.
3. Repo rate: create data/raw/policy/repo_rate.csv (date,repo) from RBI MPC decisions, verified from rbi.org.in.
4. Run phase1.py --root . ; then extensions E1-E5 (design_final D24+), descriptive versions even if gates fail.
5. Audit: scripts/audit/sample_audit.py -> fetch_texts.py (no cap) -> LLM coding x2 -> audit_metrics.py.
6. Paper + scripted rerun check (Gate 3).
