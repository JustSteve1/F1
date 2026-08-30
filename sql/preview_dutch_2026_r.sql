-- Preview only: 2026 Dutch Grand Prix race (session_key 2456128946).
-- Does not write. Run apply SQL only after extras > 0 (or to confirm already clean).
--
--   bq query --project_id=f1-data-library --use_legacy_sql=false --nouse_cache \
--     < sql/preview_dutch_2026_r.sql

SELECT
  table_name,
  row_count,
  unique_keys,
  extra_copies
FROM (
  SELECT
    'laps' AS table_name,
    COUNT(*) AS row_count,
    COUNT(DISTINCT CONCAT(CAST(driver_number AS STRING), '-', CAST(lap_number AS STRING))) AS unique_keys,
    COUNT(*) - COUNT(DISTINCT CONCAT(CAST(driver_number AS STRING), '-', CAST(lap_number AS STRING))) AS extra_copies
  FROM `f1-data-library.f1_data_library_DS.laps`
  WHERE session_key = 2456128946

  UNION ALL

  SELECT
    'telemetry' AS table_name,
    COUNT(*) AS row_count,
    CAST(NULL AS INT64) AS unique_keys,
    CAST(NULL AS INT64) AS extra_copies
  FROM `f1-data-library.f1_data_library_DS.telemetry`
  WHERE session_key = 2456128946

  UNION ALL

  SELECT
    'sessions' AS table_name,
    COUNT(*) AS row_count,
    CAST(NULL AS INT64) AS unique_keys,
    CAST(NULL AS INT64) AS extra_copies
  FROM `f1-data-library.f1_data_library_DS.sessions`
  WHERE session_key = 2456128946
)
ORDER BY table_name;

-- Sample of duplicated driver/lap pairs (empty if already unique).
SELECT
  CAST(driver_number AS STRING) AS driver_number,
  lap_number,
  COUNT(*) AS copies
FROM `f1-data-library.f1_data_library_DS.laps`
WHERE session_key = 2456128946
GROUP BY 1, 2
HAVING COUNT(*) > 1
ORDER BY copies DESC, driver_number, lap_number
LIMIT 20;
