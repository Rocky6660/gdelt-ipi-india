-- D2 Q1: outlet candidate list from 1 day in 6 (seeded systematic grid, step 6, never a multiple of 7).
-- Columns read: SourceCommonName, TranslationInfo ONLY (expected 8-10 GB). Partition list from bq_runner.py.
-- Params: @q1_ts ARRAY<TIMESTAMP>, @indian_langs ARRAY<STRING>, @min_articles INT64
-- Output: one row per (domain, source language). Flags .in domains and Indian-language translations.
-- src_lang = 'native' means TranslationInfo is empty (original-language GKG record, mostly English).
-- Join GDELT's domain-to-country lookup and the top-20 seed OFFLINE (bq_runner.py seed-sources).
WITH base AS (
  SELECT
    DATE(_PARTITIONTIME) AS pday,
    SourceCommonName AS domain,
    COALESCE(LOWER(REGEXP_EXTRACT(TranslationInfo, r'srclc:([A-Za-z\-]+)')), 'native') AS src_lang
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME IN UNNEST(@q1_ts)
)
SELECT
  domain,
  src_lang,
  COUNT(*) AS n_articles,
  COUNT(DISTINCT pday) AS n_days,
  MIN(pday) AS first_day,
  MAX(pday) AS last_day,
  ENDS_WITH(domain, '.in') AS is_in_domain,
  src_lang IN UNNEST(@indian_langs) AS is_indian_lang
FROM base
GROUP BY domain, src_lang
HAVING COUNT(*) >= @min_articles
ORDER BY n_articles DESC;
