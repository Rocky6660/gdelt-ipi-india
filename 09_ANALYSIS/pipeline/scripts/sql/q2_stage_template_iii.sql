-- D4.4(iii) FALLBACK, used only if (i) fails the one-scan test AND (ii) temp tables are ruled out.
-- One query per chunk emitting (a) for ALL panel rows, reduced fields only
-- (partition day, DATE, source, language, three flags, Themes only when flagged, TranslationInfo). No URL, no V2Tone, no aggregates:
-- denominators and outlet-day shares are rebuilt offline by counting rows. Output can be large; chunk to stay <= 3 GB.
-- Params: @dates_ts ARRAY<TIMESTAMP>, @sources ARRAY<STRING>, @price_alt STRING
SELECT
  DATE(_PARTITIONTIME) AS pdate,
  `DATE` AS gdelt_date,
  SourceCommonName AS source,
  COALESCE(LOWER(REGEXP_EXTRACT(TranslationInfo, r'srclc:([A-Za-z\-]+)')), 'native') AS src_lang,
  REGEXP_CONTAINS(COALESCE(Themes, ''), r'(^|;)ECON_[A-Z0-9_]*(;|$)') AS is_econ,
  REGEXP_CONTAINS(COALESCE(Themes, ''), r'(^|;)ECON_INFLATION(;|$)') AS is_infl,
  REGEXP_CONTAINS(COALESCE(Themes, ''), CONCAT('(^|;)(', @price_alt, ')(;|$)')) AS is_price,
  IF(REGEXP_CONTAINS(COALESCE(Themes, ''), r'(^|;)ECON_[A-Z0-9_]*(;|$)')
       OR REGEXP_CONTAINS(COALESCE(Themes, ''), CONCAT('(^|;)(', @price_alt, ')(;|$)')),
     Themes, CAST(NULL AS STRING)) AS themes,
  TranslationInfo AS translation_info
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME IN UNNEST(@dates_ts)
  AND SourceCommonName IN UNNEST(@sources);
