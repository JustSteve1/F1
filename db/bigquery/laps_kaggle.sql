-- Kaggle lap export. One row per lap.
-- laps wins over laps_live when both have the same lap.
-- Batch laps read the FastF1 telemetry table.
-- Live laps read telemetry_live only, written by the livetiming subscriber.
-- Columns match the Kaggle "All Laps" file. No source column.

CREATE OR REPLACE VIEW `f1-data-library.f1_data_library_DS.laps_kaggle` AS
WITH sessions_dim AS (
  SELECT DISTINCT session_key, event_name, circuit, session_type
  FROM `f1-data-library.f1_data_library_DS.sessions`
),
telemetry_json AS (
  SELECT
    session_key,
    SAFE_CAST(driver_number AS INT64) AS driver_number,
    SAFE_CAST(lap_number AS INT64) AS lap_number,
    TO_JSON_STRING(
      ARRAY_AGG(
        JSON_STRIP_NULLS(
          JSON_OBJECT(
            't', ROUND(lap_time_sec, 1),
            'speed', SAFE_CAST(ROUND(speed) AS INT64),
            'throttle', SAFE_CAST(ROUND(throttle) AS INT64),
            'brake', IF(brake, 1, 0),
            'gear', gear,
            'rpm', SAFE_CAST(ROUND(rpm) AS INT64),
            'drs', SAFE_CAST(drs AS INT64),
            'x', ROUND(x, 1),
            'y', ROUND(y, 1),
            'z', ROUND(z, 1)
          )
        )
        ORDER BY lap_time_sec
      )
    ) AS telemetry
  FROM `f1-data-library.f1_data_library_DS.telemetry`
  WHERE MOD(CAST(ROUND(lap_time_sec * 10) AS INT64), 5) = 0
  GROUP BY session_key, driver_number, lap_number
),
live_telemetry_json AS (
  SELECT
    session_key,
    SAFE_CAST(driver_number AS INT64) AS driver_number,
    SAFE_CAST(lap_number AS INT64) AS lap_number,
    TO_JSON_STRING(
      ARRAY_AGG(
        JSON_STRIP_NULLS(
          JSON_OBJECT(
            't', ROUND(lap_time_sec, 1),
            'speed', SAFE_CAST(ROUND(speed) AS INT64),
            'throttle', SAFE_CAST(ROUND(throttle) AS INT64),
            'brake', IF(brake, 1, 0),
            'gear', gear,
            'rpm', SAFE_CAST(ROUND(rpm) AS INT64),
            'drs', SAFE_CAST(drs AS INT64),
            'x', ROUND(x, 1),
            'y', ROUND(y, 1),
            'z', ROUND(z, 1)
          )
        )
        ORDER BY lap_time_sec
      )
    ) AS telemetry
  FROM `f1-data-library.f1_data_library_DS.telemetry_live`
  WHERE MOD(CAST(ROUND(lap_time_sec * 10) AS INT64), 5) = 0
  GROUP BY session_key, driver_number, lap_number
),
batch_laps AS (
  SELECT
    l.season AS season,
    s.event_name AS event_name,
    COALESCE(s.circuit, s.event_name) AS circuit,
    s.session_type AS session_type,
    COALESCE(
      NULLIF(l.driver_code, ''),
      CAST(SAFE_CAST(l.driver_number AS INT64) AS STRING)
    ) AS driver,
    SAFE_CAST(l.driver_number AS INT64) AS driver_number,
    SAFE_CAST(l.lap_number AS INT64) AS lap_number,
    l.lap_duration AS lap_duration,
    l.compound AS compound,
    SAFE_CAST(l.tyre_age_laps AS INT64) AS tyre_age,
    SAFE_CAST(l.stint_number AS INT64) AS stint_number,
    l.session_key AS session_key,
    1 AS source_rank
  FROM `f1-data-library.f1_data_library_DS.laps` AS l
  JOIN sessions_dim AS s
    ON l.session_key = s.session_key
  WHERE SAFE_CAST(l.lap_number AS INT64) IS NOT NULL
),
live_laps AS (
  SELECT
    l.season AS season,
    COALESCE(s.event_name, l.event_name) AS event_name,
    COALESCE(s.circuit, s.event_name, l.event_name) AS circuit,
    COALESCE(s.session_type, l.session_type) AS session_type,
    COALESCE(
      NULLIF(l.driver_code, ''),
      CAST(SAFE_CAST(l.driver_number AS INT64) AS STRING)
    ) AS driver,
    SAFE_CAST(l.driver_number AS INT64) AS driver_number,
    SAFE_CAST(l.lap_number AS INT64) AS lap_number,
    l.lap_duration AS lap_duration,
    l.compound AS compound,
    SAFE_CAST(l.tyre_age_laps AS INT64) AS tyre_age,
    SAFE_CAST(l.stint_number AS INT64) AS stint_number,
    l.session_key AS session_key,
    2 AS source_rank
  FROM `f1-data-library.f1_data_library_DS.laps_live` AS l
  LEFT JOIN sessions_dim AS s
    ON l.session_key = s.session_key
  WHERE SAFE_CAST(l.lap_number AS INT64) IS NOT NULL
),
chosen AS (
  SELECT *
  FROM (
    SELECT * FROM batch_laps
    UNION ALL
    SELECT * FROM live_laps
  )
  WHERE driver IS NOT NULL
    AND driver_number IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY season, event_name, session_type, driver_number, lap_number
    ORDER BY source_rank
  ) = 1
)
SELECT
  c.season,
  c.event_name,
  c.circuit,
  c.session_type,
  c.driver,
  c.driver_number,
  c.lap_number,
  CASE
    WHEN c.lap_duration IS NULL THEN '0:00.000'
    ELSE CONCAT(
      CAST(CAST(FLOOR(c.lap_duration / 60) AS INT64) AS STRING),
      ':',
      FORMAT(
        '%06.3f',
        c.lap_duration - FLOOR(c.lap_duration / 60) * 60
      )
    )
  END AS lap_time,
  c.lap_duration,
  c.compound,
  c.tyre_age,
  c.stint_number,
  IFNULL(COALESCE(t.telemetry, lt.telemetry), '[]') AS telemetry
FROM chosen AS c
LEFT JOIN telemetry_json AS t
  ON c.source_rank = 1
 AND c.session_key = t.session_key
 AND c.driver_number = t.driver_number
 AND c.lap_number = t.lap_number
LEFT JOIN live_telemetry_json AS lt
  ON c.source_rank = 2
 AND c.session_key = lt.session_key
 AND c.driver_number = lt.driver_number
 AND c.lap_number = lt.lap_number
