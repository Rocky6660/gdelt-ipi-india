-- D15 non-ECON audit population (user approval 23 Nov 2026, ledger). Article-level rows for panel-source articles
-- WITHOUT any ECON_ theme, on a seeded set of window days (@days). Stage A/B keep URLs only for ECON/price rows,
-- so the non-ECON recall strata (slug-screened 150, unscreened 100) are drawn from this table.
-- Billed bytes depend only on the partitions and columns read; the source and theme filters only cut output size.
SELECT
  DATE(_PARTITIONTIME) AS pdate, GKGRECORDID, `DATE`, SourceCommonName, DocumentIdentifier, Themes, TranslationInfo
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME IN UNNEST(@days)
  AND SourceCommonName IN UNNEST(@sources)
  AND NOT REGEXP_CONTAINS(COALESCE(Themes, ''), r'(^|;)ECON_[A-Z0-9_]*(;|$)')
