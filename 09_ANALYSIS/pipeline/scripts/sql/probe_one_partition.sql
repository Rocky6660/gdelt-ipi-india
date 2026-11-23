-- D2 day-1 probe: does SourceCommonName pool sibling hosts (e.g. *.indiatimes.com)?
-- ONE partition only. Columns read: SourceCommonName, DocumentIdentifier, DATE (expected ~2 GB).
-- Params: @probe_day DATE   (config.yaml: probe_day)
-- Reading guide:
--   n_hosts_per_source > 1 for source 'indiatimes.com' => siblings are POOLED in SourceCommonName
--   (window-level outlet_key must then be the host parsed from DocumentIdentifier, D2/D11).
--   min_date_day / max_date_day must equal probe_day => _PARTITIONTIME matches the DATE field [UNVERIFIED until run].
WITH base AS (
  SELECT
    SourceCommonName AS source,
    NET.HOST(DocumentIdentifier) AS host,
    `DATE` AS gdelt_date
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME = TIMESTAMP(@probe_day)
),
flagged AS (
  SELECT *
  FROM base
  WHERE source LIKE '%indiatimes%'
     OR host LIKE '%indiatimes%'
     OR source LIKE '%hindustantimes%'
     OR host LIKE '%hindustantimes%'
     OR source LIKE '%ndtv%'
     OR host LIKE '%ndtv%'
     OR source LIKE '%news18%'
     OR host LIKE '%news18%'
     OR source LIKE '%thehindu%'
     OR host LIKE '%thehindu%'
     OR ENDS_WITH(source, '.in')
     OR ENDS_WITH(host, '.in')
)
SELECT
  source,
  host,
  COUNT(*) AS n_articles,
  COUNT(*) OVER (PARTITION BY source) AS n_hosts_per_source,
  host = source AS host_equals_source,
  MIN(DIV(gdelt_date, 1000000)) AS min_date_day,
  MAX(DIV(gdelt_date, 1000000)) AS max_date_day
FROM flagged
GROUP BY source, host
ORDER BY source, n_articles DESC;
