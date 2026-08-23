-- Agreed Kaggle export schema: one row per lap, telemetry JSON at 0.5s (2 Hz).
-- Output columns (order is part of the contract):
--   season, event_name, circuit, session_type, driver, driver_number,
--   lap_number, lap_time, lap_duration, compound, tyre_age, stint_number, telemetry

WITH
  telemetry_filtered AS (
    -- Telemetry at 0.5s intervals only
    SELECT
      session_key,
      driver_number,
      lap_number,
      lap_time_sec,
      speed,
      throttle,
      brake,
      gear,
      rpm,
      drs,
      x,
      y,
      z
    FROM `{{PROJECT}}.{{DATASET}}.telemetry`
    WHERE
      {{SEASON_PREDICATE}}
      AND {{EVENT_PREDICATE}}
      AND {{SESSION_PREDICATE}}
      AND {{NEW_LAPS_PREDICATE}}
      AND MOD(CAST(ROUND(lap_time_sec * 10) AS INT64), 5) = 0
      AND speed IS NOT NULL
  ),
  telemetry_aggregated AS (
    SELECT
      session_key,
      driver_number,
      lap_number,
      ARRAY_AGG(
        STRUCT(
          lap_time_sec AS t,
          CAST(speed AS INT64) AS speed,
          CAST(throttle AS INT64) AS throttle,
          CAST(brake AS INT64) AS brake,
          gear,
          CAST(rpm AS INT64) AS rpm,
          CAST(drs AS INT64) AS drs,
          CAST(ROUND(x, 1) AS FLOAT64) AS x,
          CAST(ROUND(y, 1) AS FLOAT64) AS y,
          CAST(ROUND(z, 1) AS FLOAT64) AS z)
        ORDER BY lap_time_sec)
        AS telemetry
    FROM telemetry_filtered
    GROUP BY session_key, driver_number, lap_number
  ),
  lap_keys AS (
    SELECT DISTINCT
      session_key,
      driver_number,
      lap_number,
      season,
      event_name,
      circuit,
      session_type
    FROM `{{PROJECT}}.{{DATASET}}.telemetry`
    WHERE
      {{SEASON_PREDICATE}}
      AND {{EVENT_PREDICATE}}
      AND {{SESSION_PREDICATE}}
      AND {{NEW_LAPS_PREDICATE}}
  )

SELECT
  t.season,
  t.event_name,
  t.circuit,
  t.session_type,
  COALESCE(dm.driver_code, CAST(t.driver_number AS STRING)) AS driver,
  CAST(t.driver_number AS INT64) AS driver_number,
  t.lap_number,

  CONCAT(
    CAST(FLOOR(COALESCE(l.lap_duration, 0) / 60) AS INT64),
    ':',
    LPAD(
      CAST(
        FLOOR(
          COALESCE(l.lap_duration, 0)
          - (FLOOR(COALESCE(l.lap_duration, 0) / 60) * 60))
        AS STRING),
      2,
      '0'),
    '.',
    LPAD(
      CAST(
        ROUND(
          (COALESCE(l.lap_duration, 0) - FLOOR(COALESCE(l.lap_duration, 0)))
          * 1000)
        AS STRING),
      3,
      '0'))
    AS lap_time,

  l.lap_duration,
  l.compound,
  l.tyre_age_laps AS tyre_age,
  l.stint_number,
  TO_JSON_STRING(ta.telemetry) AS telemetry
FROM lap_keys t
INNER JOIN telemetry_aggregated ta
  ON t.session_key = ta.session_key
  AND t.driver_number = ta.driver_number
  AND t.lap_number = ta.lap_number
LEFT JOIN `{{PROJECT}}.{{DATASET}}.laps` l
  ON t.session_key = l.session_key
  AND t.driver_number = l.driver_number
  AND t.lap_number = l.lap_number
LEFT JOIN `{{PROJECT}}.{{DATASET}}.driver_number_mapping` dm
  ON t.season = dm.season
  AND SAFE_CAST(t.driver_number AS INT64)
    = SAFE_CAST(dm.driver_number AS INT64)
ORDER BY t.event_name, t.session_type, t.driver_number, t.lap_number
