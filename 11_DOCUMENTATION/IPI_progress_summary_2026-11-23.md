# GDELT Inflation Perception Index (India): progress summary
*As of 23 Nov 2026, 21:00 IST. Deadline: 25 Nov 2026.*

## 1. What the project is
A daily/monthly **news-attention-to-inflation index for India** built from GDELT (English plus vernacular outlets, 2016–2026), tested against the **RBI household inflation expectations survey (IESH)**, with five extensions: city panel, English vs vernacular, salience basket, imported vs domestic narratives, and attention cycle.

## 2. Done
| Area | Status |
|---|---|
| Research design | Final (`docs/design/design_final.md`); every ruling in `ledger.md` |
| GDELT extraction (BigQuery) | **Complete**: 216 chunks; **~475 GB of the 670 GB cap**; integrity check (D34) passed |
| RBI IESH | 67 rounds since 2015. Exact fieldwork dates from 2020; pre-2020 rounds use the month rule (your ruling b), flagged |
| CPI (MoSPI, base 2012) | Jan 2013–Dec 2025, all-India, items and states |
| Repo rate | 74 MPC decisions (2015–2026), each from RBI press-release text |
| Markets | Brent, INR/USD, 10-year G-sec |
| GDELT DOC API, Google Trends | DOC national series done; Trends: pull 1 of 3 |
| Outlet panel | 714 of 936 domains (foreign outlets removed) |
| Index | Built; 62 of 63 rounds valid (one falls in a GDELT outage); split-half reliability 0.89 |
| Phase 1 econometrics | Done (results below) |
| Extensions E1–E5 | Descriptive versions done |
| Paper | Draft written; 10 sections PENDING on the audit |
| Independent review | Sonnet review saved: `10_OUTPUTS/paper/review_sonnet_2026-11-23.md` |
| GitHub | Private repo `Rocky6660/gdelt-ipi-india` (first commit only; later work **not yet pushed**) |

## 3. Results so far (prediction language, not causal)
- **Index validity:** correlates **0.78** with Google searches for "inflation" (0.26–0.30 with "mehngai"). **Fails the episode test**: it peaks only in 2022 (post-Ukraine), not for the onion, fuel or tomato episodes (1 of 4; ≥3 required).
- **Main result:** +1 SD in the news index goes with **+0.33 pp** in the 1-year median household expectation (95% CI 0.01–0.64; wild bootstrap p = 0.037; N = 56).
- **But fragile:**
  - 0.09 (not significant) with only CPI as a control;
  - weaker at later horizons and without 2020–21;
  - other outcomes (mean, 3-month, current) at p ≈ 0.07–0.11.
- **No out-of-sample forecasting gain** over CPI plus food (RMSE ratio 1.03, Clark–West p = 0.68).
- **Extensions:**
  - **E2:** English and vernacular indices move together (r = 0.91) and relate to expectations about equally.
  - **E4:** the "imported" narrative adds nothing.
  - **E5:** attention peaks in 2022, 2025 and 2026; no asymmetric effect.
  - **E1:** gate fails (too few local inflation articles), descriptive only.
  - **E3:** built.
- **Likely framing:** a *measurement contribution*, an open, reproducible news-attention index, with suggestive, in-sample-only links to expectations.

## 4. Article audit (in progress)
- 1,250 articles sampled (the planned DOC stratum was dropped because the DOC API was down at sampling time).
- ~480 texts retrieved so far (~54%); failures go to the URL-slug fallback.
- LLM coding: about 475 articles in each of passes A and B. No human coding (your ruling); A–B agreement measures reliability, not validation.

## 5. What's left (full list: `TODO_REMAINING.md`)
1. **Finish the audit:** coding (pass B on gating strata only), metrics, best-F2 flag, switch chain, Phase 1 rerun if the flag changes. *The biggest credit cost.*
2. **Trends pulls 2 and 3**, or state honestly how many were done.
3. **Fix the review's points:** wording, the Trends count, specification dependence, full robustness and forecast tables, sample flow.
4. **Finish the paper in short form:** cut the pipeline jargon, add figures and tables, literature (Carroll 2003; Lamla & Lein 2014; Larsen et al. 2021), abstract and conclusion.
5. **Gate 3** reproducibility rerun; **commit and push** after each step.
6. **You:** read and approve.

## 6. How to resume
In PowerShell: `cd C:\Users\ragha\Documents\GDELT_IPI`, then `claude --continue`, then tell it to work through `TODO_REMAINING.md` in order A → D, committing and pushing after each section.
