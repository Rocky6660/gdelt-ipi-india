-- D13: global daily GKG record count per sampled partition (denominator for the "global count < 50% of its 28-day median" rule).
-- Reads NO table column (COUNT(*) with a partition filter); expected bytes about 0 (10 MB minimum billing). Still dry-run, capped and ledgered.
-- Params: @ts ARRAY<TIMESTAMP> (sampled partitions of the chosen rung; medians are taken over sampled days).
SELECT DATE(_PARTITIONTIME) AS pdate, COUNT(*) AS n_records
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME IN UNNEST(@ts)
GROUP BY pdate
ORDER BY pdate;
