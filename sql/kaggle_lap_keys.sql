-- Cheap lap identity query for incremental Kaggle exports.
-- No telemetry aggregation — used only to diff against the live Kaggle CSV.
-- Placeholders: {{PROJECT}} {{DATASET}} {{SEASON_PREDICATE}} {{EVENT_PREDICATE}} {{SESSION_PREDICATE}}

SELECT DISTINCT
  session_key,
  season,
  event_name,
  session_type,
  CAST(driver_number AS INT64) AS driver_number,
  CAST(lap_number AS INT64) AS lap_number
FROM `{{PROJECT}}.{{DATASET}}.telemetry`
WHERE
  {{SEASON_PREDICATE}}
  AND {{EVENT_PREDICATE}}
  AND {{SESSION_PREDICATE}}
  AND MOD(CAST(ROUND(lap_time_sec * 10) AS INT64), 5) = 0
  AND speed IS NOT NULL
  AND lap_number IS NOT NULL
