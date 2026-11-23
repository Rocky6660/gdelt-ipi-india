# Ledger

## Model rotation plan (user asked to keep changing models)
| Round | Proposer / revisions | Reviewer | Red-team critic |
|---|---|---|---|
| Blind v1 | opus | – | – |
| 1 | – | sonnet | fable |
| 2 | opus (revision) | fable | sonnet |
| 3 | fable (revision) | opus | sonnet |
| 4 | opus (revision) | sonnet | fable |

Agreement rule: decision AGREED only if reviewer and critic both ACCEPT. Stop at ≥80% agreed and no FATAL, or after round 4.

## User constraints recorded 16 Nov 2026
- Paper (not thesis), deadline two weeks.
- BigQuery free sandbox.
- Pause for user approval after the design loop.
- All five extensions wanted.

## Rounds
(filled in as rounds complete)

## Blind round note
Proposer (opus) did not open user_ideas.md but did read the project memory note listing the user's five angles, so the blind round was only partly blind. Its independent overlap on (1) regional index and (2) language split should be weighed accordingly.
Proposer flagged for the user: validation audit would fetch live/Wayback copies of ~400 article URLs for coding — needs user confirmation this fits the "GDELT only" rule.

## Round 1 (reviewer sonnet, critic fable) on design_v1
| Decision | Reviewer | Critic | Status |
|---|---|---|---|
| D1 | REVISE | ACCEPT | open |
| D2 | ACCEPT | REVISE MINOR | open |
| D3 | REVISE | REVISE MINOR | open |
| D4 | REVISE | REVISE FATAL | open |
| D5 | REVISE | REVISE FATAL | open |
| D6 | REVISE | REVISE MINOR | open |
| D7 | ACCEPT | REVISE MINOR | open |
| D8 | REJECT | REVISE MINOR | open |
| D9 | REVISE | REVISE MINOR | open |
| D10 | ACCEPT | REVISE MINOR | open |
| D11 | ACCEPT | REVISE MINOR | open |
| D12 | ACCEPT | ACCEPT | AGREED |
| D13 | ACCEPT | ACCEPT | AGREED |
| D14 | ACCEPT | ACCEPT | AGREED |
| D15 | REVISE | REVISE MINOR | open |
| D16 | REVISE | ACCEPT | open |
| D17 | REVISE | REVISE MINOR | open |
| D18 | ACCEPT | ACCEPT | AGREED |
| D19 | REVISE | REVISE MINOR | open |
| D20 | REVISE | REVISE FATAL | open |
| D21 | ACCEPT | ACCEPT | AGREED |
| D22 | ACCEPT | REVISE MINOR | open |
| D23 | ACCEPT | ACCEPT | AGREED |
| D24 | ACCEPT | REVISE MINOR | open |
| D25 | REVISE | REVISE MINOR | open |
| D26 | REVISE | REVISE MINOR | open |
| D27 | REVISE | REVISE FATAL | open |
| D28 | REVISE | REVISE MINOR | open |
| D29 | ACCEPT | REVISE MINOR | open |
| D30 | ACCEPT | ACCEPT | AGREED |
| D31 | ACCEPT | REVISE MINOR | open |
| D32 | ACCEPT | REVISE MINOR | open |
| D33 | ACCEPT | REVISE MINOR | open |
| D34 | REVISE | REVISE FATAL | open |
| D35 | ACCEPT | REVISE MINOR | open |
| D36 | ACCEPT | ACCEPT | AGREED |
| D37 | REVISE | REVISE MINOR | open |

Agreement: 8/37 = 22%. FATAL: D4, D5, D20, D27, D34. Not stopped.

## Round 2 (reviewer fable, critic sonnet) on design_v2
| Decision | Reviewer | Critic | Status |
|---|---|---|---|
| D1 | ACCEPT | REVISE MINOR | open |
| D2 | ACCEPT | ACCEPT | AGREED |
| D3 | ACCEPT | REVISE MINOR | open |
| D4 | REVISE | REVISE MINOR | open |
| D5 | ACCEPT | REVISE MINOR | open |
| D6 | ACCEPT | REVISE MINOR | open |
| D7 | ACCEPT | REVISE MINOR | open |
| D8 | ACCEPT | ACCEPT | AGREED |
| D9 | ACCEPT | REVISE MINOR | open |
| D10 | ACCEPT | ACCEPT | AGREED |
| D11 | REVISE | REVISE MINOR | open |
| D12 | ACCEPT | ACCEPT | AGREED |
| D13 | ACCEPT | ACCEPT | AGREED |
| D14 | ACCEPT | ACCEPT | AGREED |
| D15 | REVISE | REVISE MINOR | open |
| D16 | ACCEPT | REVISE MINOR | open |
| D17 | ACCEPT | REVISE MINOR | open |
| D18 | ACCEPT | ACCEPT | AGREED |
| D19 | ACCEPT | REVISE MINOR | open |
| D20 | ACCEPT | REVISE MINOR | open |
| D21 | ACCEPT | ACCEPT | AGREED |
| D22 | ACCEPT | REVISE MINOR | open |
| D23 | ACCEPT | ACCEPT | AGREED |
| D24 | ACCEPT | ACCEPT | AGREED |
| D25 | ACCEPT | REVISE MINOR | open |
| D26 | ACCEPT | REVISE MINOR | open |
| D27 | ACCEPT | REVISE MINOR | open |
| D28 | REVISE | ACCEPT | open |
| D28.2 | - | ACCEPT | open |
| D29 | ACCEPT | REVISE MINOR | open |
| D30 | ACCEPT | REVISE MINOR | open |
| D31 | ACCEPT | ACCEPT | AGREED |
| D32 | ACCEPT | REVISE MINOR | open |
| D33 | ACCEPT | REVISE MINOR | open |
| D34 | REVISE | REVISE MINOR | open |
| D35 | ACCEPT | ACCEPT | AGREED |
| D36 | ACCEPT | ACCEPT | AGREED |
| D37 | ACCEPT | REVISE MINOR | open |
| D38 | ACCEPT | REVISE MINOR | open |
| D39 | ACCEPT | ACCEPT | AGREED |
| D40 | ACCEPT | REVISE MINOR | open |
| D41 | ACCEPT | ACCEPT | AGREED |
| D42 | REVISE | REVISE MINOR | open |

Agreement: 16/43 = 37% (D28.2 removal accepted by reviewer in text). FATAL: none. Not stopped. Reviewer alone 86% ACCEPT; critic gave 26 REVISE MINOR.

## Round 3 (reviewer opus, critic sonnet) on design_v3
| Decision | Reviewer | Critic | Status |
|---|---|---|---|
| D1 | ACCEPT | ACCEPT | AGREED |
| D2 | ACCEPT | REVISE MINOR | open |
| D3 | ACCEPT | ACCEPT | AGREED |
| D4 | ACCEPT | ACCEPT | AGREED |
| D5 | ACCEPT | ACCEPT | AGREED |
| D6 | ACCEPT | ACCEPT | AGREED |
| D7 | ACCEPT | REVISE MINOR | open |
| D8 | ACCEPT | ACCEPT | AGREED |
| D9 | ACCEPT | ACCEPT | AGREED |
| D10 | ACCEPT | ACCEPT | AGREED |
| D11 | ACCEPT | ACCEPT | AGREED |
| D12 | ACCEPT | ACCEPT | AGREED |
| D13 | ACCEPT | ACCEPT | AGREED |
| D14 | ACCEPT | ACCEPT | AGREED |
| D15 | ACCEPT | ACCEPT | AGREED |
| D16 | REVISE | ACCEPT | open |
| D17 | ACCEPT | ACCEPT | AGREED |
| D18 | ACCEPT | ACCEPT | AGREED |
| D19 | ACCEPT | REVISE MINOR | open |
| D20 | ACCEPT | ACCEPT | AGREED |
| D21 | ACCEPT | ACCEPT | AGREED |
| D22 | ACCEPT | ACCEPT | AGREED |
| D23 | ACCEPT | ACCEPT | AGREED |
| D24 | ACCEPT | ACCEPT | AGREED |
| D25 | REVISE | ACCEPT | open |
| D26 | ACCEPT | ACCEPT | AGREED |
| D27 | REVISE | ACCEPT | open |
| D28 | ACCEPT | REVISE MINOR | open |
| D29 | ACCEPT | ACCEPT | AGREED |
| D30 | ACCEPT | ACCEPT | AGREED |
| D31 | ACCEPT | ACCEPT | AGREED |
| D32 | ACCEPT | ACCEPT | AGREED |
| D33 | ACCEPT | ACCEPT | AGREED |
| D34 | ACCEPT | REVISE MINOR | open |
| D35 | ACCEPT | ACCEPT | AGREED |
| D36 | ACCEPT | ACCEPT | AGREED |
| D37 | ACCEPT | ACCEPT | AGREED |
| D38 | ACCEPT | ACCEPT | AGREED |
| D39 | ACCEPT | ACCEPT | AGREED |
| D40 | ACCEPT | ACCEPT | AGREED |
| D41 | ACCEPT | ACCEPT | AGREED |
| D42 | ACCEPT | ACCEPT | AGREED |

Agreement: 35/43 = 81.4% (D28.2 removal accepted by both; critic listed it as REMOVED-shift-share-IV). FATAL: none. STOP RULE MET (≥80%, no FATAL). Extra critic items (demoted/removed sub-choices) not in reviewer's list: []

## User rulings (17 Nov 2026, 13:44 IST)
- Disputes D2, D7, D16, D19, D25, D27, D28, D34: ALL proposed fixes ACCEPTED.
- D16 audit text: Mode A APPROVED (live + archived fetch of ~400 articles, validation only, log success/failure), GDELT/NGrams fallback where needed.
- BigQuery project ID: [project removed] (sandbox).
- Project folder GDELT_IPI: prepared by user; attachment PENDING verification.
- Human coding: APPROVED, ~4.5 h across days 4–5.
- Requirements: full scope retained, all five extensions, no downgrades for deadline; budget 0.55–0.67 TB; dry-run + hard byte caps on every job; freeze outlets and query plan before major extraction; separate raw/processed/scripts/logs/docs; gates before claims; descriptive versions of extensions even if gates fail; no fabrication; no causal claims; report blockers.
- Deadline: 25 Nov 2026.

## User rulings, 17 Nov 2026 18:40 IST
- Audit fetch: all ~1,550 sampled articles (no 400 cap).
- Languages: Marathi/Bengali articles stay in the dataset; classified by LLM only (user does not read them). Human sheet stays English + Hindi (110 + 40).
- LLM coding: option B, done in-session by Claude Opus directly; no agent workflow.
- Execution: Opus only; no subagents, reviewer/verifier agents, or parallel model reviews. Second-agent reproduction (verification by a different model) is dropped by user instruction; replaced by a scripted self-check (rerun from raw, compare hashes/figures).
- Blocker logged: both the cloud workspace and the desktop sandbox block GDELT, BigQuery, RBI, MoSPI, FRED, Wayback and news hosts (only PyPI/Anthropic reachable).

## User rulings, 23 Nov 2026 (Claude Code session)
- build_index.py missing from the project (scripts/build/ empty): REWRITE from design (D10, D11, D13), matched to phase1.py inputs.
- Panel rule (D2 offline panel; no rule had been frozen): keep GDELT domain-country lookup = India, .in TLD, top-20 seeds, *.indiatimes.com; drop lookup-foreign; hand-review the ambiguous domains (unlisted non-.in; foreign-listed but not South Asian; any South-Asian-listed domain that looks Indian) and keep only Indian-headquartered outlets, each call recorded with its reason in scripts/build/panel_review.csv before any outcome merge.
- Audit non-ECON recall strata (D15): Stage A/B keep article URLs only for ECON/price-flagged rows, so the non-ECON strata need an extra pull. APPROVED by user (23 Nov): ~5.3 GB dry-run, 20 seeded window days (seed 20261123), panel sources, non-ECON articles only; job label audit_nonecon.
- Gate 2 (23 Nov 2026): index ACCEPTED with the D9 baseline flag before the audit; docs/analysis_plan.md FROZEN (hash in docs/analysis_plan.sha256). Phase 1 and extensions run before the audit for the deadline; if the audit triggers the D9 switch, Phase 1 is re-run on the best-F2 flag and both are reported.
- 23 Nov 2026 (after Phase 1): (1) run the D34 row-count reconciliation with Q1 now; (2) NO change of flag or specification in response to Phase 1 results; the flag switches only through the audit's best-F2 rule (D9/D15); (3) audit: code the gating strata first in both LLM passes, report the Gate 2 metrics, then code the remaining strata if time allows; build E2–E5 descriptive versions in parallel.
- D8 DOC gate (23 Nov 2026): the 17 Nov FAIL was four sandbox ConnectionErrors. Re-test from the user's machine: queries (i) and (iii) returned daily data from Jan 2017 (depth criterion met); ~50% of calls fail at connection level. User ruling: PASS; build what is feasible with retries/caching (national keyword IPI for D17, E3 item series); skip the +60 DOC audit stratum (would need a re-draw) and per-outlet series; report what is skipped.
- User instructions, 2026-11-22 21:40 IST: (1) PROGRESS.md timestamps from the system clock; (2) D17 failure stands as pre-registered; run the D9/D17 switch chain mechanically after the audit's best-F2; no tuning; if every variant fails, label the index "audited, not externally validated" and treat H1/H5 as exploratory; (3) 403-blocked articles: retry via Wayback, then D16 slug fallback; report retrieval rate per stratum; (4) order today: gating strata both passes -> Gate 2 metrics -> D9/D17 switch -> Phase 1 rerun if the flag changes -> full paper draft with E1-E5 descriptive sections; if short of time, code the non-gating strata in one pass only and say so; no gate skipped. Install matplotlib (approved).
- User instruction 23 Nov 14:37 UTC: pass B on gating strata only, pass A on all strata; then Gate 2 metrics, kappa on overlap, best-F2, D9/D17 switch chain, Phase 1 rerun if flag changes, paper, Gate 3, git + private GitHub repo.
- 2026-11-23 14:39 UTC: D15 truth-source rule under the no-human ruling: LLM coder A = truth; LLM-LLM kappa as reliability (audit_metrics --no-human). Recorded as plan amendment.
