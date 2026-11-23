-- Q2, OTHER-DAYS-ONLY form (D4.4(i) one-scan fix, 21 Nov 2026). Identical output schema and row logic to
-- q2_stage_template.sql rows 'A' (non-window) and 'D'; the window branch is removed because BigQuery billed its
-- columns over the other-day partitions too (dry run +72 GB at L3). Window days run with q2_stage_template.sql
-- and an empty @other_ts. @window_ts and @trim_themes are referenced only so the parameter set stays identical.
WITH
oth AS (
  SELECT
    DATE(_PARTITIONTIME) AS pdate,
    `DATE` AS gdelt_date,
    SourceCommonName AS source,
    Themes AS themes,
    TranslationInfo AS translation_info
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME IN UNNEST(@other_ts)
    AND SourceCommonName IN UNNEST(@sources)
),
oth_f AS (
  SELECT
    pdate, gdelt_date, source, themes, translation_info,
    COALESCE(LOWER(REGEXP_EXTRACT(translation_info, r'srclc:([A-Za-z\-]+)')), 'native') AS src_lang,
    REGEXP_CONTAINS(COALESCE(themes, ''), r'(^|;)ECON_[A-Z0-9_]*(;|$)') AS is_econ,
    REGEXP_CONTAINS(COALESCE(themes, ''), r'(^|;)ECON_INFLATION(;|$)') AS is_infl,
    REGEXP_CONTAINS(COALESCE(themes, ''), CONCAT('(^|;)(', @price_alt, ')(;|$)')) AS is_price
  FROM oth
),
a_oth AS (
  SELECT
    'A' AS row_type, pdate, FALSE AS window_day, source,
    CAST(NULL AS STRING) AS host, src_lang, CAST(NULL AS STRING) AS url_section, CAST(NULL AS STRING) AS url_path,
    CAST(NULL AS STRING) AS gkgrecordid, CAST(NULL AS STRING) AS document_identifier, gdelt_date,
    IF(@trim_themes,
       CONCAT(ARRAY_TO_STRING(ARRAY(
                SELECT t FROM UNNEST(SPLIT(COALESCE(themes, ''), ';')) AS t
                WHERE REGEXP_CONTAINS(t, CONCAT('^(ECON_[A-Z0-9_]*|', @price_alt, ')$'))), ';'),
              '|#', CAST(FARM_FINGERPRINT(COALESCE(themes, '')) AS STRING)),
       themes) AS themes,
    CAST(NULL AS STRING) AS v2tone, CAST(NULL AS FLOAT64) AS word_count, translation_info,
    is_econ, is_infl, is_price,
    CAST(NULL AS INT64) AS n_articles, CAST(NULL AS INT64) AS n_distinct_urls,
    CAST(NULL AS INT64) AS n_econ, CAST(NULL AS INT64) AS n_econ_distinct,
    CAST(NULL AS INT64) AS n_infl, CAST(NULL AS INT64) AS n_infl_distinct,
    CAST(NULL AS INT64) AS n_price, CAST(NULL AS INT64) AS n_price_distinct,
    CAST(NULL AS FLOAT64) AS words_all, CAST(NULL AS FLOAT64) AS words_infl,
    CAST(NULL AS BYTES) AS url_hll, CAST(NULL AS BYTES) AS url_hll_infl
  FROM oth_f
  WHERE is_econ OR is_infl OR is_price
),
d_oth AS (
  SELECT
    'D' AS row_type, pdate, FALSE AS window_day, source,
    CAST(NULL AS STRING) AS host, src_lang, CAST(NULL AS STRING) AS url_section, CAST(NULL AS STRING) AS url_path,
    CAST(NULL AS STRING) AS gkgrecordid, CAST(NULL AS STRING) AS document_identifier, CAST(NULL AS INT64) AS gdelt_date,
    CAST(NULL AS STRING) AS themes, CAST(NULL AS STRING) AS v2tone, CAST(NULL AS FLOAT64) AS word_count,
    CAST(NULL AS STRING) AS translation_info,
    CAST(NULL AS BOOL) AS is_econ, CAST(NULL AS BOOL) AS is_infl, CAST(NULL AS BOOL) AS is_price,
    COUNT(*) AS n_articles,
    CAST(NULL AS INT64) AS n_distinct_urls,
    COUNTIF(is_econ) AS n_econ,
    CAST(NULL AS INT64) AS n_econ_distinct,
    COUNTIF(is_infl) AS n_infl,
    CAST(NULL AS INT64) AS n_infl_distinct,
    COUNTIF(is_price) AS n_price,
    CAST(NULL AS INT64) AS n_price_distinct,
    CAST(NULL AS FLOAT64) AS words_all,
    CAST(NULL AS FLOAT64) AS words_infl,
    CAST(NULL AS BYTES) AS url_hll, CAST(NULL AS BYTES) AS url_hll_infl
  FROM oth_f
  GROUP BY pdate, source, src_lang
)
SELECT * FROM a_oth WHERE COALESCE(ARRAY_LENGTH(@window_ts), 0) >= 0  -- empty ARRAY params arrive as NULL
UNION ALL SELECT * FROM d_oth;
