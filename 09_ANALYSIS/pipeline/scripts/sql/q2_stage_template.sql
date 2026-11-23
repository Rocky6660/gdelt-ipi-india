-- D4.4(i) SINGLE-STATEMENT form: one pass over the base table, two table references with
-- DIFFERENT column lists (full set on window days, reduced set on non-window days), UNION ALL of
--   (a) article-level rows  (row_type 'A')  for every ECON-tagged OR inflation/price-flagged article, full Themes string;
--                            window-day rows also carry url_section (3 dirs) and the full url_path
--   (b) aggregates          (row_type 'S' window day: outlet x day x host x language x URL-section (first 3 directory segments);
--                            row_type 'D' non-window day: outlet x day x language, no URL so no section)
-- Adopt only if dry-run bytes equal one scan of the listed columns/partitions (checked in `bq_runner.py dryrun`).
-- Params (all REQUIRED, see bq_runner.py build_q2_params):
--   @window_ts       ARRAY<TIMESTAMP>  partitions read with the FULL set  (DATE, SourceCommonName, GKGRECORDID, DocumentIdentifier, Themes, V2Tone, TranslationInfo)
--   @other_ts        ARRAY<TIMESTAMP>  partitions read with the REDUCED set (DATE, SourceCommonName, Themes, TranslationInfo)
--   @sources         ARRAY<STRING>     source superset (Indian outlets). Does NOT reduce billed bytes (table not clustered on source).
--   @price_alt       STRING            regex alternation of price-family theme codes, e.g. 'ECON_INFLATION|WB_...'; fixed at Gate 1a after theme_lookup.sql
--   @trim_themes     BOOL              D4.6: keep only ECON/price tokens + hash of the full string
-- NOTE: partition pruning through `_PARTITIONTIME IN UNNEST(@param)` is [UNVERIFIED]; if the dry run shows more bytes than the
-- partition list implies, rerun with `--inline-partitions` (bq_runner.py substitutes literal TIMESTAMP lists).
-- Baseline flag (D9) = ECON_INFLATION in V1 Themes. V1 Themes is ';'-separated codes without offsets.
WITH
win AS (
  SELECT
    DATE(_PARTITIONTIME) AS pdate,
    `DATE` AS gdelt_date,
    SourceCommonName AS source,
    GKGRECORDID AS gkgrecordid,
    DocumentIdentifier AS document_identifier,
    Themes AS themes,
    V2Tone AS v2tone,
    TranslationInfo AS translation_info
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME IN UNNEST(@window_ts)
    AND SourceCommonName IN UNNEST(@sources)
),
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
win_f AS (
  SELECT
    pdate, gdelt_date, source, gkgrecordid, document_identifier, themes, v2tone, translation_info,
    NET.HOST(document_identifier) AS host,
    -- url_section: up to the first 3 DIRECTORY segments of the path (e.g. 'city/mumbai/', 'local/rajasthan/jaipur/'), so
    -- edition-path city denominators exist for ALL articles (D40, D42a). Truncated at the first slug-like segment
    -- (>30 chars, a 4+ digit run, or 3+ hyphens) so article slugs never enter it (R3).
    (SELECT IF(COUNT(*) = 0, NULL, CONCAT(STRING_AGG(seg, '/' ORDER BY o), '/'))
       FROM UNNEST(SPLIT(REGEXP_EXTRACT(document_identifier, r'^https?://[^/]+/((?:[^/?#]+/){1,3})'), '/')) seg WITH OFFSET o
       WHERE seg != '' AND o < IFNULL((
         SELECT MIN(o2) FROM UNNEST(SPLIT(REGEXP_EXTRACT(document_identifier, r'^https?://[^/]+/((?:[^/?#]+/){1,3})'), '/')) s2 WITH OFFSET o2
         WHERE LENGTH(s2) > 30 OR REGEXP_CONTAINS(s2, r'[0-9]{4,}') OR LENGTH(s2) - LENGTH(REPLACE(s2, '-', '')) >= 3), 3)
    ) AS url_section,
    REGEXP_EXTRACT(document_identifier, r'^https?://[^/]+(/[^?#]*)') AS url_path,
    -- normalised URL: no query/fragment, no scheme, no leading www., no trailing slash
    REGEXP_REPLACE(REGEXP_REPLACE(document_identifier, r'[?#].*$', ''), r'^https?://(?:www\.)?|/+$', '') AS url_norm,
    COALESCE(LOWER(REGEXP_EXTRACT(translation_info, r'srclc:([A-Za-z\-]+)')), 'native') AS src_lang,
    SAFE_CAST(SPLIT(v2tone, ',')[SAFE_OFFSET(6)] AS FLOAT64) AS word_count,
    REGEXP_CONTAINS(COALESCE(themes, ''), r'(^|;)ECON_[A-Z0-9_]*(;|$)') AS is_econ,
    REGEXP_CONTAINS(COALESCE(themes, ''), r'(^|;)ECON_INFLATION(;|$)') AS is_infl,
    REGEXP_CONTAINS(COALESCE(themes, ''), CONCAT('(^|;)(', @price_alt, ')(;|$)')) AS is_price
  FROM win
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
-- (a) article rows, window days: full Themes (or D4.6-trimmed)
a_win AS (
  SELECT
    'A' AS row_type, pdate, TRUE AS window_day, source, host, src_lang, url_section, url_path,
    gkgrecordid, document_identifier, gdelt_date,
    IF(@trim_themes,
       CONCAT(ARRAY_TO_STRING(ARRAY(
                SELECT t FROM UNNEST(SPLIT(COALESCE(themes, ''), ';')) AS t
                WHERE REGEXP_CONTAINS(t, CONCAT('^(ECON_[A-Z0-9_]*|', @price_alt, ')$'))), ';'),
              '|#', CAST(FARM_FINGERPRINT(COALESCE(themes, '')) AS STRING)),
       themes) AS themes,
    v2tone, word_count, translation_info, is_econ, is_infl, is_price,
    CAST(NULL AS INT64) AS n_articles, CAST(NULL AS INT64) AS n_distinct_urls,
    CAST(NULL AS INT64) AS n_econ, CAST(NULL AS INT64) AS n_econ_distinct,
    CAST(NULL AS INT64) AS n_infl, CAST(NULL AS INT64) AS n_infl_distinct,
    CAST(NULL AS INT64) AS n_price, CAST(NULL AS INT64) AS n_price_distinct,
    CAST(NULL AS FLOAT64) AS words_all, CAST(NULL AS FLOAT64) AS words_infl,
    CAST(NULL AS BYTES) AS url_hll, CAST(NULL AS BYTES) AS url_hll_infl
  FROM win_f
  WHERE is_econ OR is_infl OR is_price
),
-- (a) article rows, non-window days: reduced fields (no URL, no record id, no V2Tone)
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
-- (b) window days: outlet x day x host x language x URL-section, over ALL source articles (denominators)
s_win AS (
  SELECT
    'S' AS row_type, pdate, TRUE AS window_day, source, host, src_lang, url_section, CAST(NULL AS STRING) AS url_path,
    CAST(NULL AS STRING) AS gkgrecordid, CAST(NULL AS STRING) AS document_identifier, CAST(NULL AS INT64) AS gdelt_date,
    CAST(NULL AS STRING) AS themes, CAST(NULL AS STRING) AS v2tone, CAST(NULL AS FLOAT64) AS word_count,
    CAST(NULL AS STRING) AS translation_info,
    CAST(NULL AS BOOL) AS is_econ, CAST(NULL AS BOOL) AS is_infl, CAST(NULL AS BOOL) AS is_price,
    COUNT(*) AS n_articles,
    COUNT(DISTINCT url_norm) AS n_distinct_urls,
    COUNTIF(is_econ) AS n_econ,
    COUNT(DISTINCT IF(is_econ, url_norm, NULL)) AS n_econ_distinct,
    COUNTIF(is_infl) AS n_infl,
    COUNT(DISTINCT IF(is_infl, url_norm, NULL)) AS n_infl_distinct,
    COUNTIF(is_price) AS n_price,
    COUNT(DISTINCT IF(is_price, url_norm, NULL)) AS n_price_distinct,
    SUM(word_count) AS words_all,
    SUM(IF(is_infl, word_count, NULL)) AS words_infl,
    -- R5: HLL sketches dropped (no offline merge route). Kept as NULL columns for schema stability.
    -- Window dedup: numerators exact from A rows (URLs); denominators are day-level distinct, with the
    -- cross-day duplicate rate measured on A rows and reported (D11 note).
    CAST(NULL AS BYTES) AS url_hll,
    CAST(NULL AS BYTES) AS url_hll_infl
  FROM win_f
  GROUP BY pdate, source, host, src_lang, url_section
),
-- (b) non-window days: outlet x day x language only (no URL on these days, no dedup, no word counts)
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
SELECT * FROM a_win
UNION ALL SELECT * FROM a_oth
UNION ALL SELECT * FROM s_win
UNION ALL SELECT * FROM d_oth;
