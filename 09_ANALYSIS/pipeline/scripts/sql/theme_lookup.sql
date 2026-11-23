-- D9: confirm ECON_INFLATION and price-family theme codes exist in the V1 Themes column in each sample year.
-- Cheap sample: ONE partition per sample year (config.yaml: theme_lookup_dates). Columns read: SourceCommonName, Themes.
-- Params: @sample_ts ARRAY<TIMESTAMP>, @sources ARRAY<STRING> (Indian superset or top-20), @candidate_regex STRING
-- Output: per year x theme code, global and Indian-source counts. Check that ECON_INFLATION has n_all > 0 in EVERY year,
-- and see which price-family codes (ECON_*PRICE*, WB_*PRICE*, WB_*INFLATION*, ...) actually exist. [UNVERIFIED until run]
WITH rows_ AS (
  SELECT
    EXTRACT(YEAR FROM _PARTITIONTIME) AS yr,
    SourceCommonName AS source,
    Themes
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME IN UNNEST(@sample_ts)
),
tokens AS (
  SELECT
    yr,
    source,
    token
  FROM rows_, UNNEST(SPLIT(COALESCE(Themes, ''), ';')) AS token
  WHERE token != '' AND REGEXP_CONTAINS(token, @candidate_regex)
)
SELECT
  yr,
  token AS theme_code,
  COUNT(*) AS n_all,
  COUNTIF(source IN UNNEST(@sources)) AS n_indian_sources
FROM tokens
GROUP BY yr, token
HAVING COUNT(*) >= 5
ORDER BY yr, n_all DESC;
