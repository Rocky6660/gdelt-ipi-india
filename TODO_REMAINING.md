# What is left (as of 23 Nov 2026, 20:55 IST)

Done: all GDELT extraction (475 GB of 670), RBI IESH (67 rounds), CPI 2013-2025, repo rate, markets, DOC API,
Trends pull 1, index built, Phase 1 run, E1-E5 descriptive, D34 integrity check, private GitHub repo.
Review of the draft: 10_OUTPUTS/paper/review_sonnet_2026-11-23.md

## A. Finish the audit (biggest credit cost) — done 23 Nov except Trends pull 2 (needs a different calendar day; runs after local midnight)
[x] 1. Finish fetch_texts.py; slug fallback (D16) for failures; report retrieval rate per stratum.
[x] 2. Coding: pass B on gating strata only; pass A on the rest. Report A-B kappa (reliability, not validation).
[x] 3. audit_metrics.py --no-human: precision, recall, F2 per flag variant; best-F2.
[x] 4. d9_switch.py: D17 on best-F2, then strict. If all fail -> "audited, not externally validated"; H1/H5 exploratory.
[x] 5. Rerun phase1.py only if the flag changed.
6. [x] Trends: pull 2 declined by user at run time (24 Nov); paper states 1 pull, provisional.

## B. Fix what the Sonnet review found
1. [x] Remove "pre-registered"/"audited" wording where untrue (Phase 1 ran before the audit).
2. [x] Trends: report the actual number of pulls.
3. [x] Explain specification dependence: AR+CPI only 0.089 [-0.16,0.34] vs 0.328 with food CPI/repo/phone controls.
4. [x] Drop-2020-21 row also drops the phone dummy; say the point estimate (0.297) is stable.
5. [x] Report robustness estimates with CIs (word share, price family, core2018, mean, 3m, current), not only correlations.
6. [x] Report the exact-fieldwork row (N=32, 0.47 [0.12,0.83], p_wild 0.105).
7. [x] D22: also report vs AR1 (RMSE ratio 1.16, CW p 0.045).
8. [x] Sample flow 67 -> 63 -> 59 -> 56 -> 37 explained; units of window vs monthly index stated.
9. [x] Discuss the binned (1 pp) IESH median.

## C. Complete the paper (short-paper format)
1. [x] Cut pipeline labels (D-numbers, file paths, hashes, GB counts) from the main text; move details to an appendix.
2. [x] Main text: data, index, validation (split-half 0.89, Trends r 0.78, episode test fails), primary result,
   robustness coefficient plot, forecasting null, limitations, conclusion.
3. [x] E1 one sentence; E2 one paragraph; E3/E4/E5 appendix.
4. [x] Add: figure of index vs expectations (+CPI); descriptive-stats table; coefficient plot; magnitude in context;
   multiple-testing paragraph; horse race vs Google Trends; persistence caveat.
5. [x] Literature: Carroll (2003); Lamla & Lein (2014); Larsen, Thorsrud & Zhulanova (2021); ECB (2025); Arndt.
6. [x] Framing: measurement contribution with suggestive, non-causal in-sample evidence; no forecasting gain.
7. [x] Abstract and conclusion last.

## D. Close out
1. [x] Gate 3: scripted rerun from raw data; confirm key numbers reproduce.
2. [x] Commit and push after each of A, B, C, D.
3. [x] User reads and approves the final paper.
