Revision round 3 for the GDELT IPI paper. The source of the submission version is in 10_OUTPUTS/paper/final/source/:
- content.js: the main text;
- appendix.js: the appendices;
- build.js: the docx builder;
- the figure PNGs.

Markup used in content.js: **bold**, *italic*, _{sub}, ^{sup}. Items have these forms:
- ["table", title, header[], rows[][], note]
- ["fig", file, caption, note, widthInches]
- ["eq", text, "(n)"]

Edit content.js and appendix.js only. Do NOT change build.js or the formatting. I will rebuild the PDF.

Rules:
- No fabricated numbers. Every number you add must come from a script you ran, saved under 09_ANALYSIS/pipeline/scripts/revision/r3_*.py.
- No causal language.
- Opus only. No subagents.
- Use only the data already on disk; no new BigQuery queries. If a task needs data we don't have, write it as a limitation instead.
- Log every change, with its old and new values, in 10_OUTPUTS/paper/REVISION3_RESULTS.md.

A. Fix internal inconsistencies (must do)
1. Abstract and Section 4.3.2 say "no time- or price-control variant reaches the 5% level". But Table 11 shows "lagged expectation and headline CPI only" (p = 0.040) and "next-month CPI added" (p = 0.035). Rewrite these claims so they are true. Example wording: "two price-control variants reach 5%, and none of the time-control variants does". Verify against the result files first.
2. The monthly-series peaks disagree. The text (Section 3.2.4) and Table 17 give 5.0% in Apr 2022 and 6.7% in Apr 2026. Figures 2 and 10 seem to plot about 8.7% in 2026. Find which series each figure plots (smoothed or not, which grid, which core). Make the text, Table 17 and the figures use the same series, regenerating figures if needed. 6.75 rounds to 6.8, not 6.7. Also check Aarab-style claim in Section 5.1 about "persistence after 2022" against the actual series; delete or correct it.
3. Section 4.4.2 says the language split uses the baseline tag, but Table F1 labels it "Price family". Check the script and fix whichever is wrong.
4. The BVAR is reported as "58 rounds, two lags", but only 57 rounds have CPI. Check the script, report the real effective N, and fix the text and the Figure 6 caption.
5. "26 rounds before 2020" use the month rule, but Table C1 shows 23 before 2020 and 3 during 2020. Fix to the true count and wording everywhere: Sections 3.1.3 and 5.2, and the Table C1 note.
6. Audit accounting: Table 8 sums to 928 coded and 104 relevant articles, while Section 4.1.1 has 1,026 coded and 118 relevant, and Section 4.1.4 has 119. Reconcile the three. Either add the missing rows or explain the frames in the Table 8 note, and explain 118 vs 119.
7. Table F3 has N = 105 while the paper says 129 usable months. Explain why or fix.
8. The GDELT version is 2.1 in Section 3.1.1 but "2.0" in the data statement. Use 2.1 everywhere.

B. Fix overclaims (must do)
9. The abstract says the estimate is "stable in size". Replace this with an honest range. Mention the 0.12–0.14 variants (no food/repo/phone controls, mean expectation, change in index) and the near-zero slope after 2022.
10. Remove the remaining causal or over-strong phrases:
    - "does not drive the result", "does not inflate", "does not merely reflect anticipation". Soften to "is not driven only by… within the precision available".
    - "index shock" in the VAR: say "orthogonalised innovation in the index (Cholesky ordering, no structural interpretation)".
    - "a supervised classifier would likely improve": make it a conjecture.
11. The title and framing call the series "media attention to inflation", but precision is 0.13. Add one sentence in the intro and in Section 3.2 calling the series "GDELT price-theme coverage, a noisy proxy for attention to inflation". Use that term consistently where the measured object is meant. Keep the title, but change "Media Attention to Inflation" to "Price-Theme News Coverage" if it reads well.

C. Methodological issues: new analyses only if the existing data allow; otherwise add to the limitations section
12. Outlet duplication: collapse economictimes.* subdomains (and other subdomains of the same parent, e.g. dinamalar) into one outlet each. Drop lifestyle and entertainment domains (bollywoodhungama, femina, vogue, temple/cinema subdomains). Recompute the window index from the cached outlet-by-window counts and re-run the primary local projection (LP). Add the result as a row in Table 12 and say what changed in Section 5.2.
13. Sectoral codes: build an index from the price family excluding the energy/sector codes ECON_OILPRICE, GASOLINEPRICE, DIESELPRICE, ELECTRICALPRICE, NATGASPRICE and TRANSPORT_COST, if the window counts by theme exist. If they do, report its audit precision and recall from the existing codes and run the LP. If not, add it as a limitation.
14. Note in Section 5.2 that 200–300-character excerpts hold fewer words in Indic scripts. In Section 4.1.3, add a binomial CI for the 1 of 87 non-economic stratum and show how the recall lower bound of 0.04 moves across that CI.
15. Irregular survey spacing: add an LP without the lagged dependent variable, and one that controls for the months between rounds (or divides by the gap). Add both to Table 12. In Section 4.3.6, state that the VAR treats rounds as equally spaced.
16. Tone split: if V2Tone or the audit direction codes allow, build rising and falling sub-indices. Otherwise, add this as a limitation and report the audit direction counts (79 rising vs 26 falling).
17. Regional panel and intra-window daily Brent/INR changes: do these only if quick with data on disk. Otherwise, list them as future work. Do not download new data unless it is FRED daily series.
18. The missing human audit stays a limitation. Make sure Section 5.2 says so plainly.

D. Clarity (must do)
19. Define these in the text, each with its rule or formula:
    - "gating frame";
    - economic vs non-economic articles (the GDELT theme prefixes);
    - the wire-copy filter;
    - word share;
    - the "2018 core" (number of outlets and rule);
    - the salience-weighted median and absolute measure;
    - "excess attention during disinflation";
    - the peak, months-of-rise and half-life rules.
20. Replace "IPI" on the Figure 10 axis and anywhere in the text with "news index" (IPI usually means industrial production). Regenerate that figure if needed.
21. Cut the repetition. State the headline caveats in full once, in the abstract and in Section 5.2. Elsewhere, refer back to them in one clause. Move all analysis-plan and deviation disclosures into Section 3.5.4.
22. Relabel the appendix tables so there is no gap (E4 is missing). Update all references to them.
23. Equations and symbols: the reviewer read the PDF as text, so check whether these defects are real or extraction artefacts:
    - Greek Α instead of A;
    - Cyrillic "по";
    - "indexx";
    - missing × signs.
    Grep content.js and appendix.js for non-ASCII look-alike characters (Greek, Cyrillic) and replace them with the right characters. Use "×" explicitly in the interaction labels in Tables 14 and E2. Fix "indexx".

E. Literature (add with full, verified references; do not invent bibliographic details)
24. Add these papers:
    - Das, Lahiri & Zhao (2019, IJF): Indian IESH;
    - Pfajfar & Santoro (2013, JMCB);
    - Dräger (2015, OBES);
    - Nimark & Pitschner (2019, JET);
    - Baker, Bloom & Davis (2016, QJE): cite where the "EPU-style count" is mentioned;
    - Ash & Hansen (2023, Annual Review of Economics).
    Check each on the web before adding it. Put each in the literature review in one sentence each.

F. Formatting (must do)
25. Write "—" in uncomputed table cells (Tables 10, 11, F4). Add a note to F4 that the half-life is right-censored for Apr 2026.
26. Table C1: put "—" in empty Mode cells to match its note.
27. Table 6: change 1.113 to 1,113.
28. Table 8: put the baseline and price-family rows for "Other Indian languages" on separate lines, like the other groups.
29. Use "MoSPI" everywhere, including the figures. Change "Vernacular (z)" in the Figure 8 legend to "Indian-language (z)", regenerating the PNG.
30. References:
    - complete the Arndt DOI;
    - put the GDELT entry on one line;
    - add page numbers for Pratap et al. if they can be found;
    - list Coibion, Gorodnichenko & Kamdar (2018) before Coibion, Gorodnichenko & Weber (2022).
31. Renumber the multiple-testing count to cover the new tests.
32. Regenerate any figure you touch at 300 dpi with large fonts and no title inside the image. Save it in source/ under the same name.

When done:
- Run a script that checks every number in content.js and appendix.js against the result files.
- Commit with the message "Revision round 3" and push.
- Write a short summary at the top of REVISION3_RESULTS.md: what was fixed, the new results, and what stayed a limitation and why.
