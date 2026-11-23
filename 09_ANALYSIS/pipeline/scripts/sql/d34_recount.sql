-- D34 reconciliation: independent Q1-style recount (SourceCommonName, TranslationInfo only) on the days shared by
-- the Q1 grid (step 6) and the L3 sample, per day x source x source language, superset sources only.
-- Compared offline with the Q2 aggregates (S/D n_articles) by scripts/checks/d34_reconcile.py (+/-1% rule).
SELECT DATE(_PARTITIONTIME) AS pdate, SourceCommonName AS source,
       COALESCE(LOWER(REGEXP_EXTRACT(TranslationInfo, r'srclc:([A-Za-z\-]+)')), 'native') AS src_lang,
       COUNT(*) AS n_articles
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME IN UNNEST(@d) AND SourceCommonName IN UNNEST(@sources)
GROUP BY 1, 2, 3
