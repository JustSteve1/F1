-- Export views. A lap is joined only to telemetry from the same source.
-- laps_all_legacy  = batch laps  + batch telemetry
-- laps_all_live    = laps_live   + telemetry_live
-- laps_for_export  = one whole source per session: live when that session
--                    has live laps, otherwise legacy.
-- laps_kaggle is the same 13 columns as laps_for_export, for the uploader.

CREATE TABLE IF NOT EXISTS `f1-data-library.f1_data_library_DS.telemetry_live`
LIKE `f1-data-library.f1_data_library_DS.telemetry`;

CREATE OR REPLACE VIEW `f1-data-library.f1_data_library_DS.laps_all_legacy` AS
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
)
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
  CASE
    WHEN l.lap_duration IS NULL THEN '0:00.000'
    ELSE CONCAT(
      CAST(CAST(FLOOR(l.lap_duration / 60) AS INT64) AS STRING),
      ':',
      FORMAT('%06.3f', l.lap_duration - FLOOR(l.lap_duration / 60) * 60)
    )
  END AS lap_time,
  l.lap_duration AS lap_duration,
  l.compound AS compound,
  SAFE_CAST(l.tyre_age_laps AS INT64) AS tyre_age,
  SAFE_CAST(l.stint_number AS INT64) AS stint_number,
  IFNULL(t.telemetry, '[]') AS telemetry,
  l.session_key AS session_key
FROM `f1-data-library.f1_data_library_DS.laps` AS l
JOIN sessions_dim AS s
  ON l.session_key = s.session_key
LEFT JOIN telemetry_json AS t
  ON l.session_key = t.session_key
 AND SAFE_CAST(l.driver_number AS INT64) = t.driver_number
 AND SAFE_CAST(l.lap_number AS INT64) = t.lap_number
WHERE SAFE_CAST(l.lap_number AS INT64) IS NOT NULL
  AND COALESCE(
    NULLIF(l.driver_code, ''),
    CAST(SAFE_CAST(l.driver_number AS INT64) AS STRING)
  ) IS NOT NULL;

CREATE OR REPLACE VIEW `f1-data-library.f1_data_library_DS.laps_all_live` AS
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
        ORDER BY date, imported_at
      )
    ) AS telemetry
  FROM `f1-data-library.f1_data_library_DS.telemetry_live`
  GROUP BY session_key, driver_number, lap_number
)
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
  CASE
    WHEN l.lap_duration IS NULL THEN '0:00.000'
    ELSE CONCAT(
      CAST(CAST(FLOOR(l.lap_duration / 60) AS INT64) AS STRING),
      ':',
      FORMAT('%06.3f', l.lap_duration - FLOOR(l.lap_duration / 60) * 60)
    )
  END AS lap_time,
  l.lap_duration AS lap_duration,
  l.compound AS compound,
  SAFE_CAST(l.tyre_age_laps AS INT64) AS tyre_age,
  SAFE_CAST(l.stint_number AS INT64) AS stint_number,
  IFNULL(t.telemetry, '[]') AS telemetry,
  l.session_key AS session_key
FROM `f1-data-library.f1_data_library_DS.laps_live` AS l
LEFT JOIN sessions_dim AS s
  ON l.session_key = s.session_key
LEFT JOIN telemetry_json AS t
  ON l.session_key = t.session_key
 AND SAFE_CAST(l.driver_number AS INT64) = t.driver_number
 AND SAFE_CAST(l.lap_number AS INT64) = t.lap_number
WHERE SAFE_CAST(l.lap_number AS INT64) IS NOT NULL
  AND COALESCE(
    NULLIF(l.driver_code, ''),
    CAST(SAFE_CAST(l.driver_number AS INT64) AS STRING)
  ) IS NOT NULL;

CREATE OR REPLACE VIEW `f1-data-library.f1_data_library_DS.laps_for_export` AS
SELECT * EXCEPT (session_key)
FROM `f1-data-library.f1_data_library_DS.laps_all_live`
UNION ALL
SELECT * EXCEPT (session_key)
FROM `f1-data-library.f1_data_library_DS.laps_all_legacy`
WHERE session_key NOT IN (
  SELECT session_key
  FROM `f1-data-library.f1_data_library_DS.laps_all_live`
  WHERE session_key IS NOT NULL
);

CREATE OR REPLACE VIEW `f1-data-library.f1_data_library_DS.laps_kaggle` AS
SELECT * FROM `f1-data-library.f1_data_library_DS.laps_for_export`;
