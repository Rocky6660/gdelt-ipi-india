# Design brief

## Objective
Construct an **inflation perception index (IPI) using GDELT data**, validate it, and test its economic information content (in particular for household inflation expectations).

## Constraints (from the user)
- Country: **India** (user is based in India; outcome data from Indian official sources).
- News data: **GDELT only** (GKG 2.0 from Feb 2015 onward; Web News NGrams 3.0 may be used to reconstruct article text). No paid archives (Factiva, LexisNexis).
- Data access: no paid cloud account at present. Options under consideration: Google BigQuery free sandbox, or downloading GDELT raw files. Treat compute and query cost as a real constraint and say what each design choice costs.
- Outcome / control data: public Indian sources only (RBI, MoSPI, Google Trends, market data that is freely downloadable).
- The work will be executed largely by AI agents with a human checking at gates, so every step must be concrete, scripted and reproducible.
- Purpose and deadline: **a research paper (not a thesis), due in two weeks** from 16 Nov 2026. The design must be executable in that time by AI agents, so it must prioritise: a solid baseline first, then the most valuable extensions, with clear cut lines for what drops if time runs short.
- Data route chosen: **Google BigQuery free sandbox** (1 TB of query processing per month, no billing). Queries must be designed to fit that budget (select few columns, use partitioned tables, filter dates).

## Source material (read these)
1. Consoli, Tiozzo Pezzoli & Tosetti (2021), "Emotions in macroeconomic news and their impact on the European bond market", J. Int. Money & Finance. Project doc path: `Base Paper (1).pdf`.
2. Schmidt, Schmidt, Müller, Rieger & Jentsch (2026), "Changing inflation perception and the propagation of news shocks", Empirical Economics. Project doc path: `s00181-026-02964-9 1.pdf`.

If you have the Projects tool, read both with `project_read` using the paths above. A structured summary of both is in `/home/claude/debate/sources_summary.md` for use if you cannot open them.

You may also search the web for further literature.

## Output format required of any design
A numbered list of discrete decisions D1, D2, ... Each decision: **Choice**, **Rationale**, **Alternatives considered**, **Risk / what could go wrong**, **Cost / feasibility note**. Group decisions under headings (Data, Measurement, Validation, Econometrics, Contribution, Execution plan).
