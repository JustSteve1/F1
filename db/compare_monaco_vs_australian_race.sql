-- =============================================================================
-- Monaco vs Australian Grand Prix Race — side-by-side + data-quality comparison
-- Dataset: f1-data-library.f1_data_library_DS
--
-- Purpose:
--   Compare the NEW pipe (Monaco) against the EXISTING baseline (Australian)
--   for sessions / laps / telemetry to judge completeness & accuracy.
--
-- How to run:
--   BigQuery console → paste whole script, or run each labeled query after the
--   preamble (DECLARE + temp session-key resolution) has been executed once.
--
-- Caveats:
--   • "First 100" is an ordered sample for eyeballing schema/shape — not a
--     like-for-like lap match across different circuits.
--   • Different circuits → different lap counts / distances; DQ focuses on
--     relative completeness and telemetry density, not equal absolute volumes.
--   • Change monaco_year / aus_year below if your seasons differ.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PREAMBLE — parameters + resolve Race session_keys
-- -----------------------------------------------------------------------------
DECLARE monaco_year INT64 DEFAULT 2026;
DECLARE aus_year INT64 DEFAULT 2025;
DECLARE monaco_event STRING DEFAULT 'Monaco Grand Prix';
DECLARE aus_event STRING DEFAULT 'Australian Grand Prix';
DECLARE session_type_filter STRING DEFAULT 'R';

CREATE TEMP TABLE _cmp_sessions AS
WITH from_sessions AS (
  SELECT
    CASE
      WHEN event_name = monaco_event AND season = monaco_year THEN 'monaco'
      WHEN event_name = aus_event AND season = aus_year THEN 'australian'
    END AS side,
    session_key,
    meeting_key,
    season,
    event_name,
    circuit,
    circuit_short_name,
    location,
    country_name,
    session_name,
    session_type,
    date_start,
    date_end,
    imported_at
  FROM `f1-data-library.f1_data_library_DS.sessions`
  WHERE session_type = session_type_filter
    AND (
      (event_name = monaco_event AND season = monaco_year)
      OR (event_name = aus_event AND season = aus_year)
    )
),
-- Fallback if sessions row missing: pick a session_key seen in laps / telemetry
from_laps AS (
  SELECT
    CASE
      WHEN event_name = monaco_event AND season = monaco_year THEN 'monaco'
      WHEN event_name = aus_event AND season = aus_year THEN 'australian'
    END AS side,
    ANY_VALUE(session_key) AS session_key
  FROM `f1-data-library.f1_data_library_DS.laps`
  WHERE session_type = session_type_filter
    AND (
      (event_name = monaco_event AND season = monaco_year)
      OR (event_name = aus_event AND season = aus_year)
    )
  GROUP BY side
),
from_telem AS (
  SELECT
    CASE
      WHEN event_name = monaco_event AND season = monaco_year THEN 'monaco'
      WHEN event_name = aus_event AND season = aus_year THEN 'australian'
    END AS side,
    ANY_VALUE(session_key) AS session_key
  FROM `f1-data-library.f1_data_library_DS.telemetry`
  WHERE session_type = session_type_filter
    AND (
      (event_name = monaco_event AND season = monaco_year)
      OR (event_name = aus_event AND season = aus_year)
    )
  GROUP BY side
),
sides AS (
  SELECT side FROM UNNEST(['monaco', 'australian']) AS side
)
SELECT
  s.side,
  COALESCE(fs.session_key, fl.session_key, ft.session_key) AS session_key,
  fs.meeting_key,
  COALESCE(fs.season, IF(s.side = 'monaco', monaco_year, aus_year)) AS season,
  COALESCE(fs.event_name, IF(s.side = 'monaco', monaco_event, aus_event)) AS event_name,
  fs.circuit,
  fs.circuit_short_name,
  fs.location,
  fs.country_name,
  fs.session_name,
  COALESCE(fs.session_type, session_type_filter) AS session_type,
  fs.date_start,
  fs.date_end,
  fs.imported_at,
  fs.session_key IS NOT NULL AS has_sessions_row
FROM sides s
LEFT JOIN from_sessions fs USING (side)
LEFT JOIN from_laps fl USING (side)
LEFT JOIN from_telem ft USING (side);

-- =============================================================================
-- Q0 — Session discovery (sanity)
-- =============================================================================
SELECT
  c.side,
  c.season,
  c.event_name,
  c.session_type,
  c.session_key,
  c.has_sessions_row,
  c.imported_at AS sessions_imported_at,
  (SELECT COUNT(*) FROM `f1-data-library.f1_data_library_DS.sessions` s
   WHERE s.session_key = c.session_key) AS sessions_rows,
  (SELECT COUNT(*) FROM `f1-data-library.f1_data_library_DS.laps` l
   WHERE l.session_key = c.session_key) AS laps_rows,
  (SELECT COUNT(*) FROM `f1-data-library.f1_data_library_DS.telemetry` t
   WHERE t.session_key = c.session_key) AS telemetry_rows,
  (SELECT COUNT(DISTINCT driver_number)
   FROM `f1-data-library.f1_data_library_DS.laps` l
   WHERE l.session_key = c.session_key) AS distinct_drivers_laps,
  (SELECT COUNT(DISTINCT driver_number)
   FROM `f1-data-library.f1_data_library_DS.telemetry` t
   WHERE t.session_key = c.session_key) AS distinct_drivers_telem
FROM _cmp_sessions c
ORDER BY c.side;

-- =============================================================================
-- Q1 — Sessions side-by-side (row-level)
-- =============================================================================
WITH monaco AS (
  SELECT
    ROW_NUMBER() OVER (
      ORDER BY session_key, CAST(date_start AS STRING)
    ) AS rn,
    *
  FROM `f1-data-library.f1_data_library_DS.sessions`
  WHERE session_key IN (SELECT session_key FROM _cmp_sessions WHERE side = 'monaco')
),
australian AS (
  SELECT
    ROW_NUMBER() OVER (
      ORDER BY session_key, CAST(date_start AS STRING)
    ) AS rn,
    *
  FROM `f1-data-library.f1_data_library_DS.sessions`
  WHERE session_key IN (SELECT session_key FROM _cmp_sessions WHERE side = 'australian')
)
SELECT
  COALESCE(m.rn, a.rn) AS rn,
  -- Monaco
  m.session_key AS m_session_key,
  m.meeting_key AS m_meeting_key,
  m.season AS m_season,
  m.event_name AS m_event_name,
  m.circuit AS m_circuit,
  m.circuit_short_name AS m_circuit_short_name,
  m.location AS m_location,
  m.country_name AS m_country_name,
  m.session_name AS m_session_name,
  m.session_type AS m_session_type,
  m.date_start AS m_date_start,
  m.date_end AS m_date_end,
  m.imported_at AS m_imported_at,
  -- Australian
  a.session_key AS a_session_key,
  a.meeting_key AS a_meeting_key,
  a.season AS a_season,
  a.event_name AS a_event_name,
  a.circuit AS a_circuit,
  a.circuit_short_name AS a_circuit_short_name,
  a.location AS a_location,
  a.country_name AS a_country_name,
  a.session_name AS a_session_name,
  a.session_type AS a_session_type,
  a.date_start AS a_date_start,
  a.date_end AS a_date_end,
  a.imported_at AS a_imported_at
FROM monaco m
FULL OUTER JOIN australian a USING (rn)
ORDER BY rn;

-- =============================================================================
-- Q2 — Laps side-by-side (first 100 rows each)
-- =============================================================================
WITH monaco AS (
  SELECT
    ROW_NUMBER() OVER (
      ORDER BY SAFE_CAST(driver_number AS INT64), lap_number
    ) AS rn,
    *
  FROM `f1-data-library.f1_data_library_DS.laps`
  WHERE session_key IN (SELECT session_key FROM _cmp_sessions WHERE side = 'monaco')
  QUALIFY rn <= 100
),
australian AS (
  SELECT
    ROW_NUMBER() OVER (
      ORDER BY SAFE_CAST(driver_number AS INT64), lap_number
    ) AS rn,
    *
  FROM `f1-data-library.f1_data_library_DS.laps`
  WHERE session_key IN (SELECT session_key FROM _cmp_sessions WHERE side = 'australian')
  QUALIFY rn <= 100
)
SELECT
  COALESCE(m.rn, a.rn) AS rn,
  -- Monaco core
  m.session_key AS m_session_key,
  m.driver_number AS m_driver_number,
  m.driver_code AS m_driver_code,
  m.team AS m_team,
  m.position AS m_position,
  m.lap_number AS m_lap_number,
  m.lap_duration AS m_lap_duration,
  m.lap_start_time AS m_lap_start_time,
  m.sector_1_time AS m_sector_1_time,
  m.sector_2_time AS m_sector_2_time,
  m.sector_3_time AS m_sector_3_time,
  m.sector_1_session_time AS m_sector_1_session_time,
  m.sector_2_session_time AS m_sector_2_session_time,
  m.sector_3_session_time AS m_sector_3_session_time,
  m.pit_out_time AS m_pit_out_time,
  m.pit_in_time AS m_pit_in_time,
  m.speed_i1 AS m_speed_i1,
  m.speed_i2 AS m_speed_i2,
  m.speed_st AS m_speed_st,
  m.compound AS m_compound,
  m.tyre_age_laps AS m_tyre_age_laps,
  m.stint_number AS m_stint_number,
  m.fresh_tyre AS m_fresh_tyre,
  m.is_accurate AS m_is_accurate,
  m.is_personal_best AS m_is_personal_best,
  m.deleted AS m_deleted,
  m.deleted_reason AS m_deleted_reason,
  m.fastf1_generated AS m_fastf1_generated,
  m.track_status AS m_track_status,
  m.lap_start_date AS m_lap_start_date,
  m.imported_at AS m_imported_at,
  (
    IF(m.lap_duration IS NULL, 1, 0)
    + IF(m.sector_1_time IS NULL, 1, 0)
    + IF(m.sector_2_time IS NULL, 1, 0)
    + IF(m.sector_3_time IS NULL, 1, 0)
    + IF(m.driver_code IS NULL, 1, 0)
    + IF(m.team IS NULL, 1, 0)
    + IF(m.compound IS NULL, 1, 0)
    + IF(m.speed_i1 IS NULL, 1, 0)
    + IF(m.speed_i2 IS NULL, 1, 0)
    + IF(m.speed_st IS NULL, 1, 0)
  ) AS m_null_count,
  -- Australian core
  a.session_key AS a_session_key,
  a.driver_number AS a_driver_number,
  a.driver_code AS a_driver_code,
  a.team AS a_team,
  a.position AS a_position,
  a.lap_number AS a_lap_number,
  a.lap_duration AS a_lap_duration,
  a.lap_start_time AS a_lap_start_time,
  a.sector_1_time AS a_sector_1_time,
  a.sector_2_time AS a_sector_2_time,
  a.sector_3_time AS a_sector_3_time,
  a.sector_1_session_time AS a_sector_1_session_time,
  a.sector_2_session_time AS a_sector_2_session_time,
  a.sector_3_session_time AS a_sector_3_session_time,
  a.pit_out_time AS a_pit_out_time,
  a.pit_in_time AS a_pit_in_time,
  a.speed_i1 AS a_speed_i1,
  a.speed_i2 AS a_speed_i2,
  a.speed_st AS a_speed_st,
  a.compound AS a_compound,
  a.tyre_age_laps AS a_tyre_age_laps,
  a.stint_number AS a_stint_number,
  a.fresh_tyre AS a_fresh_tyre,
  a.is_accurate AS a_is_accurate,
  a.is_personal_best AS a_is_personal_best,
  a.deleted AS a_deleted,
  a.deleted_reason AS a_deleted_reason,
  a.fastf1_generated AS a_fastf1_generated,
  a.track_status AS a_track_status,
  a.lap_start_date AS a_lap_start_date,
  a.imported_at AS a_imported_at,
  (
    IF(a.lap_duration IS NULL, 1, 0)
    + IF(a.sector_1_time IS NULL, 1, 0)
    + IF(a.sector_2_time IS NULL, 1, 0)
    + IF(a.sector_3_time IS NULL, 1, 0)
    + IF(a.driver_code IS NULL, 1, 0)
    + IF(a.team IS NULL, 1, 0)
    + IF(a.compound IS NULL, 1, 0)
    + IF(a.speed_i1 IS NULL, 1, 0)
    + IF(a.speed_i2 IS NULL, 1, 0)
    + IF(a.speed_st IS NULL, 1, 0)
  ) AS a_null_count
FROM monaco m
FULL OUTER JOIN australian a USING (rn)
ORDER BY rn;

-- =============================================================================
-- Q3 — Telemetry side-by-side (first 100 rows each)
-- =============================================================================
WITH monaco AS (
  SELECT
    ROW_NUMBER() OVER (
      ORDER BY SAFE_CAST(driver_number AS INT64), lap_number, lap_time_sec
    ) AS rn,
    *
  FROM `f1-data-library.f1_data_library_DS.telemetry`
  WHERE session_key IN (SELECT session_key FROM _cmp_sessions WHERE side = 'monaco')
  QUALIFY rn <= 100
),
australian AS (
  SELECT
    ROW_NUMBER() OVER (
      ORDER BY SAFE_CAST(driver_number AS INT64), lap_number, lap_time_sec
    ) AS rn,
    *
  FROM `f1-data-library.f1_data_library_DS.telemetry`
  WHERE session_key IN (SELECT session_key FROM _cmp_sessions WHERE side = 'australian')
  QUALIFY rn <= 100
)
SELECT
  COALESCE(m.rn, a.rn) AS rn,
  -- Monaco
  m.session_key AS m_session_key,
  m.driver_number AS m_driver_number,
  m.lap_number AS m_lap_number,
  m.lap_time_sec AS m_lap_time_sec,
  m.interval_sec AS m_interval_sec,
  m.speed AS m_speed,
  m.throttle AS m_throttle,
  m.brake AS m_brake,
  m.gear AS m_gear,
  m.rpm AS m_rpm,
  m.drs AS m_drs,
  m.x AS m_x,
  m.y AS m_y,
  m.z AS m_z,
  m.deceleration AS m_deceleration,
  m.distance_m AS m_distance_m,
  m.cumulative_distance AS m_cumulative_distance,
  m.circuit AS m_circuit,
  m.event_name AS m_event_name,
  m.session_type AS m_session_type,
  m.date AS m_date,
  m.imported_at AS m_imported_at,
  (
    IF(m.speed IS NULL, 1, 0)
    + IF(m.throttle IS NULL, 1, 0)
    + IF(m.brake IS NULL, 1, 0)
    + IF(m.gear IS NULL, 1, 0)
    + IF(m.rpm IS NULL, 1, 0)
    + IF(m.x IS NULL, 1, 0)
    + IF(m.y IS NULL, 1, 0)
    + IF(m.z IS NULL, 1, 0)
    + IF(m.distance_m IS NULL, 1, 0)
    + IF(m.interval_sec IS NULL, 1, 0)
  ) AS m_null_count,
  -- Australian
  a.session_key AS a_session_key,
  a.driver_number AS a_driver_number,
  a.lap_number AS a_lap_number,
  a.lap_time_sec AS a_lap_time_sec,
  a.interval_sec AS a_interval_sec,
  a.speed AS a_speed,
  a.throttle AS a_throttle,
  a.brake AS a_brake,
  a.gear AS a_gear,
  a.rpm AS a_rpm,
  a.drs AS a_drs,
  a.x AS a_x,
  a.y AS a_y,
  a.z AS a_z,
  a.deceleration AS a_deceleration,
  a.distance_m AS a_distance_m,
  a.cumulative_distance AS a_cumulative_distance,
  a.circuit AS a_circuit,
  a.event_name AS a_event_name,
  a.session_type AS a_session_type,
  a.date AS a_date,
  a.imported_at AS a_imported_at,
  (
    IF(a.speed IS NULL, 1, 0)
    + IF(a.throttle IS NULL, 1, 0)
    + IF(a.brake IS NULL, 1, 0)
    + IF(a.gear IS NULL, 1, 0)
    + IF(a.rpm IS NULL, 1, 0)
    + IF(a.x IS NULL, 1, 0)
    + IF(a.y IS NULL, 1, 0)
    + IF(a.z IS NULL, 1, 0)
    + IF(a.distance_m IS NULL, 1, 0)
    + IF(a.interval_sec IS NULL, 1, 0)
  ) AS a_null_count
FROM monaco m
FULL OUTER JOIN australian a USING (rn)
ORDER BY rn;

-- =============================================================================
-- Q4 — Completeness / accuracy DQ (pipeline validation)
-- Metrics as rows; Monaco vs Australian as columns + gap helpers.
-- =============================================================================
WITH keys AS (
  SELECT
    MAX(IF(side = 'monaco', session_key, NULL)) AS monaco_sk,
    MAX(IF(side = 'australian', session_key, NULL)) AS aus_sk
  FROM _cmp_sessions
),
laps_m AS (
  SELECT * FROM `f1-data-library.f1_data_library_DS.laps`, keys
  WHERE session_key = keys.monaco_sk
),
laps_a AS (
  SELECT * FROM `f1-data-library.f1_data_library_DS.laps`, keys
  WHERE session_key = keys.aus_sk
),
telem_m AS (
  SELECT * FROM `f1-data-library.f1_data_library_DS.telemetry`, keys
  WHERE session_key = keys.monaco_sk
),
telem_a AS (
  SELECT * FROM `f1-data-library.f1_data_library_DS.telemetry`, keys
  WHERE session_key = keys.aus_sk
),
sess_m AS (
  SELECT * FROM `f1-data-library.f1_data_library_DS.sessions`, keys
  WHERE session_key = keys.monaco_sk
),
sess_a AS (
  SELECT * FROM `f1-data-library.f1_data_library_DS.sessions`, keys
  WHERE session_key = keys.aus_sk
),
-- Per-lap telemetry density
telem_by_lap_m AS (
  SELECT driver_number, lap_number, COUNT(*) AS pts
  FROM telem_m
  GROUP BY 1, 2
),
telem_by_lap_a AS (
  SELECT driver_number, lap_number, COUNT(*) AS pts
  FROM telem_a
  GROUP BY 1, 2
),
-- Interval mode (~0.1 expected for 10Hz resample)
interval_mode_m AS (
  SELECT CAST(interval_sec AS STRING) AS v, COUNT(*) AS c
  FROM telem_m
  WHERE interval_sec IS NOT NULL
  GROUP BY 1
  ORDER BY c DESC
  LIMIT 1
),
interval_mode_a AS (
  SELECT CAST(interval_sec AS STRING) AS v, COUNT(*) AS c
  FROM telem_a
  WHERE interval_sec IS NOT NULL
  GROUP BY 1
  ORDER BY c DESC
  LIMIT 1
),
-- Duplicate lap keys
dup_laps_m AS (
  SELECT COUNT(*) AS n FROM (
    SELECT driver_number, lap_number, COUNT(*) AS c
    FROM laps_m
    GROUP BY 1, 2
    HAVING c > 1
  )
),
dup_laps_a AS (
  SELECT COUNT(*) AS n FROM (
    SELECT driver_number, lap_number, COUNT(*) AS c
    FROM laps_a
    GROUP BY 1, 2
    HAVING c > 1
  )
),
-- Join integrity
laps_missing_telem_m AS (
  SELECT COUNT(*) AS n
  FROM laps_m l
  LEFT JOIN telem_by_lap_m t
    ON l.driver_number = t.driver_number AND l.lap_number = t.lap_number
  WHERE t.pts IS NULL
),
laps_missing_telem_a AS (
  SELECT COUNT(*) AS n
  FROM laps_a l
  LEFT JOIN telem_by_lap_a t
    ON l.driver_number = t.driver_number AND l.lap_number = t.lap_number
  WHERE t.pts IS NULL
),
telem_orphans_m AS (
  SELECT COUNT(*) AS n
  FROM telem_by_lap_m t
  LEFT JOIN laps_m l
    ON l.driver_number = t.driver_number AND l.lap_number = t.lap_number
  WHERE l.lap_number IS NULL
),
telem_orphans_a AS (
  SELECT COUNT(*) AS n
  FROM telem_by_lap_a t
  LEFT JOIN laps_a l
    ON l.driver_number = t.driver_number AND l.lap_number = t.lap_number
  WHERE l.lap_number IS NULL
),
metrics AS (
  SELECT 'volume' AS family, 'sessions_rows' AS metric,
    CAST((SELECT COUNT(*) FROM sess_m) AS FLOAT64) AS monaco,
    CAST((SELECT COUNT(*) FROM sess_a) AS FLOAT64) AS australian
  UNION ALL SELECT 'volume', 'laps_rows',
    CAST((SELECT COUNT(*) FROM laps_m) AS FLOAT64),
    CAST((SELECT COUNT(*) FROM laps_a) AS FLOAT64)
  UNION ALL SELECT 'volume', 'telemetry_rows',
    CAST((SELECT COUNT(*) FROM telem_m) AS FLOAT64),
    CAST((SELECT COUNT(*) FROM telem_a) AS FLOAT64)
  UNION ALL SELECT 'volume', 'distinct_drivers_laps',
    CAST((SELECT COUNT(DISTINCT driver_number) FROM laps_m) AS FLOAT64),
    CAST((SELECT COUNT(DISTINCT driver_number) FROM laps_a) AS FLOAT64)
  UNION ALL SELECT 'volume', 'distinct_drivers_telem',
    CAST((SELECT COUNT(DISTINCT driver_number) FROM telem_m) AS FLOAT64),
    CAST((SELECT COUNT(DISTINCT driver_number) FROM telem_a) AS FLOAT64)
  UNION ALL SELECT 'volume', 'distinct_lap_numbers',
    CAST((SELECT COUNT(DISTINCT lap_number) FROM laps_m) AS FLOAT64),
    CAST((SELECT COUNT(DISTINCT lap_number) FROM laps_a) AS FLOAT64)
  UNION ALL SELECT 'volume', 'max_lap_number',
    CAST((SELECT MAX(lap_number) FROM laps_m) AS FLOAT64),
    CAST((SELECT MAX(lap_number) FROM laps_a) AS FLOAT64)

  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_lap_duration',
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(lap_duration IS NOT NULL), COUNT(*)), 100),
    NULL
  FROM laps_m
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_lap_duration',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(lap_duration IS NOT NULL), COUNT(*)), 100)
  FROM laps_a
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_all_sectors',
    SAFE_MULTIPLY(SAFE_DIVIDE(
      COUNTIF(sector_1_time IS NOT NULL AND sector_2_time IS NOT NULL AND sector_3_time IS NOT NULL),
      COUNT(*)), 100),
    NULL
  FROM laps_m
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_all_sectors',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(
      COUNTIF(sector_1_time IS NOT NULL AND sector_2_time IS NOT NULL AND sector_3_time IS NOT NULL),
      COUNT(*)), 100)
  FROM laps_a
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_compound',
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(compound IS NOT NULL), COUNT(*)), 100),
    NULL
  FROM laps_m
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_compound',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(compound IS NOT NULL), COUNT(*)), 100)
  FROM laps_a
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_speed_traps',
    SAFE_MULTIPLY(SAFE_DIVIDE(
      COUNTIF(speed_i1 IS NOT NULL OR speed_i2 IS NOT NULL OR speed_st IS NOT NULL),
      COUNT(*)), 100),
    NULL
  FROM laps_m
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_speed_traps',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(
      COUNTIF(speed_i1 IS NOT NULL OR speed_i2 IS NOT NULL OR speed_st IS NOT NULL),
      COUNT(*)), 100)
  FROM laps_a
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_driver_code',
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(driver_code IS NOT NULL), COUNT(*)), 100),
    NULL
  FROM laps_m
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_driver_code',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(driver_code IS NOT NULL), COUNT(*)), 100)
  FROM laps_a
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_team',
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(team IS NOT NULL), COUNT(*)), 100),
    NULL
  FROM laps_m
  UNION ALL SELECT 'laps_completeness', 'pct_nonnull_team',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(team IS NOT NULL), COUNT(*)), 100)
  FROM laps_a
  -- Rich Cell-7 schema fill: share of "rich" fields that are non-null (avg across rows)
  UNION ALL SELECT 'laps_completeness', 'rich_laps_schema_pct',
    (
      SELECT ROUND(AVG(
        (
          IF(driver_code IS NOT NULL, 1, 0) + IF(team IS NOT NULL, 1, 0)
          + IF(position IS NOT NULL, 1, 0) + IF(lap_start_time IS NOT NULL, 1, 0)
          + IF(sector_1_time IS NOT NULL, 1, 0) + IF(sector_2_time IS NOT NULL, 1, 0)
          + IF(sector_3_time IS NOT NULL, 1, 0) + IF(speed_i1 IS NOT NULL, 1, 0)
          + IF(speed_i2 IS NOT NULL, 1, 0) + IF(speed_st IS NOT NULL, 1, 0)
          + IF(fresh_tyre IS NOT NULL, 1, 0) + IF(is_accurate IS NOT NULL, 1, 0)
          + IF(track_status IS NOT NULL, 1, 0) + IF(lap_start_date IS NOT NULL, 1, 0)
        ) / 14.0 * 100
      ), 2)
      FROM laps_m
    ),
    (
      SELECT ROUND(AVG(
        (
          IF(driver_code IS NOT NULL, 1, 0) + IF(team IS NOT NULL, 1, 0)
          + IF(position IS NOT NULL, 1, 0) + IF(lap_start_time IS NOT NULL, 1, 0)
          + IF(sector_1_time IS NOT NULL, 1, 0) + IF(sector_2_time IS NOT NULL, 1, 0)
          + IF(sector_3_time IS NOT NULL, 1, 0) + IF(speed_i1 IS NOT NULL, 1, 0)
          + IF(speed_i2 IS NOT NULL, 1, 0) + IF(speed_st IS NOT NULL, 1, 0)
          + IF(fresh_tyre IS NOT NULL, 1, 0) + IF(is_accurate IS NOT NULL, 1, 0)
          + IF(track_status IS NOT NULL, 1, 0) + IF(lap_start_date IS NOT NULL, 1, 0)
        ) / 14.0 * 100
      ), 2)
      FROM laps_a
    )

  UNION ALL SELECT 'telemetry_density', 'avg_points_per_lap',
    (SELECT ROUND(AVG(pts), 2) FROM telem_by_lap_m),
    (SELECT ROUND(AVG(pts), 2) FROM telem_by_lap_a)
  UNION ALL SELECT 'telemetry_density', 'median_points_per_lap',
    (SELECT ROUND(APPROX_QUANTILES(pts, 100)[OFFSET(50)], 2) FROM telem_by_lap_m),
    (SELECT ROUND(APPROX_QUANTILES(pts, 100)[OFFSET(50)], 2) FROM telem_by_lap_a)
  UNION ALL SELECT 'telemetry_density', 'laps_with_telem_pct',
    (
      SELECT SAFE_MULTIPLY(SAFE_DIVIDE(
        COUNTIF(t.pts IS NOT NULL), COUNT(*)
      ), 100)
      FROM laps_m l
      LEFT JOIN telem_by_lap_m t
        ON l.driver_number = t.driver_number AND l.lap_number = t.lap_number
    ),
    (
      SELECT SAFE_MULTIPLY(SAFE_DIVIDE(
        COUNTIF(t.pts IS NOT NULL), COUNT(*)
      ), 100)
      FROM laps_a l
      LEFT JOIN telem_by_lap_a t
        ON l.driver_number = t.driver_number AND l.lap_number = t.lap_number
    )
  UNION ALL SELECT 'telemetry_density', 'avg_points_per_driver',
    (
      SELECT ROUND(AVG(c), 2) FROM (
        SELECT driver_number, COUNT(*) AS c FROM telem_m GROUP BY 1
      )
    ),
    (
      SELECT ROUND(AVG(c), 2) FROM (
        SELECT driver_number, COUNT(*) AS c FROM telem_a GROUP BY 1
      )
    )

  UNION ALL SELECT 'telemetry_quality', 'pct_null_speed',
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(speed IS NULL), COUNT(*)), 100),
    NULL
  FROM telem_m
  UNION ALL SELECT 'telemetry_quality', 'pct_null_speed',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(speed IS NULL), COUNT(*)), 100)
  FROM telem_a
  UNION ALL SELECT 'telemetry_quality', 'pct_null_throttle',
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(throttle IS NULL), COUNT(*)), 100),
    NULL
  FROM telem_m
  UNION ALL SELECT 'telemetry_quality', 'pct_null_throttle',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(throttle IS NULL), COUNT(*)), 100)
  FROM telem_a
  UNION ALL SELECT 'telemetry_quality', 'pct_null_brake',
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(brake IS NULL), COUNT(*)), 100),
    NULL
  FROM telem_m
  UNION ALL SELECT 'telemetry_quality', 'pct_null_brake',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(COUNTIF(brake IS NULL), COUNT(*)), 100)
  FROM telem_a
  UNION ALL SELECT 'telemetry_quality', 'pct_null_xyz',
    SAFE_MULTIPLY(SAFE_DIVIDE(
      COUNTIF(x IS NULL OR y IS NULL OR z IS NULL), COUNT(*)
    ), 100),
    NULL
  FROM telem_m
  UNION ALL SELECT 'telemetry_quality', 'pct_null_xyz',
    NULL,
    SAFE_MULTIPLY(SAFE_DIVIDE(
      COUNTIF(x IS NULL OR y IS NULL OR z IS NULL), COUNT(*)
    ), 100)
  FROM telem_a
  UNION ALL SELECT 'telemetry_quality', 'interval_sec_mode',
    SAFE_CAST((SELECT SAFE_CAST(v AS FLOAT64) FROM interval_mode_m) AS FLOAT64),
    SAFE_CAST((SELECT SAFE_CAST(v AS FLOAT64) FROM interval_mode_a) AS FLOAT64)
  UNION ALL SELECT 'telemetry_quality', 'min_speed',
    (SELECT MIN(speed) FROM telem_m),
    (SELECT MIN(speed) FROM telem_a)
  UNION ALL SELECT 'telemetry_quality', 'max_speed',
    (SELECT MAX(speed) FROM telem_m),
    (SELECT MAX(speed) FROM telem_a)
  UNION ALL SELECT 'telemetry_quality', 'avg_speed',
    (SELECT ROUND(AVG(speed), 2) FROM telem_m),
    (SELECT ROUND(AVG(speed), 2) FROM telem_a)

  UNION ALL SELECT 'join_integrity', 'laps_missing_telemetry',
    CAST((SELECT n FROM laps_missing_telem_m) AS FLOAT64),
    CAST((SELECT n FROM laps_missing_telem_a) AS FLOAT64)
  UNION ALL SELECT 'join_integrity', 'telemetry_orphan_laps',
    CAST((SELECT n FROM telem_orphans_m) AS FLOAT64),
    CAST((SELECT n FROM telem_orphans_a) AS FLOAT64)
  UNION ALL SELECT 'join_integrity', 'duplicate_lap_keys',
    CAST((SELECT n FROM dup_laps_m) AS FLOAT64),
    CAST((SELECT n FROM dup_laps_a) AS FLOAT64)

  UNION ALL SELECT 'import_freshness', 'imported_at_min_unix',
    CAST(UNIX_SECONDS((
      SELECT MIN(ts) FROM (
        SELECT COALESCE(
          SAFE_CAST(imported_at AS TIMESTAMP),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', CAST(imported_at AS STRING)),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S', CAST(imported_at AS STRING))
        ) AS ts
        FROM (
          SELECT imported_at FROM sess_m
          UNION ALL SELECT imported_at FROM laps_m
          UNION ALL SELECT imported_at FROM telem_m
        )
      )
    )) AS FLOAT64),
    CAST(UNIX_SECONDS((
      SELECT MIN(ts) FROM (
        SELECT COALESCE(
          SAFE_CAST(imported_at AS TIMESTAMP),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', CAST(imported_at AS STRING)),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S', CAST(imported_at AS STRING))
        ) AS ts
        FROM (
          SELECT imported_at FROM sess_a
          UNION ALL SELECT imported_at FROM laps_a
          UNION ALL SELECT imported_at FROM telem_a
        )
      )
    )) AS FLOAT64)
  UNION ALL SELECT 'import_freshness', 'imported_at_max_unix',
    CAST(UNIX_SECONDS((
      SELECT MAX(ts) FROM (
        SELECT COALESCE(
          SAFE_CAST(imported_at AS TIMESTAMP),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', CAST(imported_at AS STRING)),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S', CAST(imported_at AS STRING))
        ) AS ts
        FROM (
          SELECT imported_at FROM sess_m
          UNION ALL SELECT imported_at FROM laps_m
          UNION ALL SELECT imported_at FROM telem_m
        )
      )
    )) AS FLOAT64),
    CAST(UNIX_SECONDS((
      SELECT MAX(ts) FROM (
        SELECT COALESCE(
          SAFE_CAST(imported_at AS TIMESTAMP),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S%Ez', CAST(imported_at AS STRING)),
          SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%E*S', CAST(imported_at AS STRING))
        ) AS ts
        FROM (
          SELECT imported_at FROM sess_a
          UNION ALL SELECT imported_at FROM laps_a
          UNION ALL SELECT imported_at FROM telem_a
        )
      )
    )) AS FLOAT64)
),
rolled AS (
  SELECT
    family,
    metric,
    MAX(monaco) AS monaco,
    MAX(australian) AS australian
  FROM metrics
  GROUP BY family, metric
)
SELECT
  family,
  metric,
  monaco,
  australian,
  ROUND(monaco - australian, 4) AS monaco_minus_australian,
  CASE
    WHEN metric IN (
      'laps_with_telem_pct',
      'avg_points_per_lap',
      'median_points_per_lap',
      'rich_laps_schema_pct',
      'pct_nonnull_lap_duration',
      'pct_nonnull_all_sectors',
      'pct_nonnull_compound',
      'pct_nonnull_speed_traps',
      'pct_nonnull_driver_code',
      'pct_nonnull_team'
    )
      AND australian IS NOT NULL AND australian != 0
      THEN ROUND(SAFE_MULTIPLY(SAFE_DIVIDE(monaco - australian, ABS(australian)), 100), 2)
    ELSE NULL
  END AS monaco_pct_gap_vs_aus,
  CASE
    WHEN metric = 'interval_sec_mode'
      AND monaco IS NOT NULL
      AND ABS(monaco - 0.1) <= 0.01
      THEN 'ok_near_0.1'
    WHEN metric = 'interval_sec_mode'
      THEN 'check_resample_interval'
    WHEN metric IN ('laps_missing_telemetry', 'telemetry_orphan_laps', 'duplicate_lap_keys')
      AND IFNULL(monaco, 0) = 0
      THEN 'ok'
    WHEN metric IN ('laps_missing_telemetry', 'telemetry_orphan_laps', 'duplicate_lap_keys')
      AND IFNULL(monaco, 0) > 0
      THEN 'investigate'
    WHEN metric IN (
      'laps_with_telem_pct',
      'pct_nonnull_lap_duration',
      'rich_laps_schema_pct'
    )
      AND monaco IS NOT NULL
      AND australian IS NOT NULL
      AND monaco >= australian - 5
      THEN 'parity_or_better'
    WHEN metric IN (
      'laps_with_telem_pct',
      'pct_nonnull_lap_duration',
      'rich_laps_schema_pct'
    )
      AND monaco IS NOT NULL
      AND australian IS NOT NULL
      AND monaco < australian - 5
      THEN 'below_baseline'
    WHEN metric = 'avg_points_per_lap'
      AND monaco IS NOT NULL
      AND australian IS NOT NULL
      AND SAFE_DIVIDE(ABS(monaco - australian), NULLIF(australian, 0)) <= 0.25
      THEN 'density_comparable'
    WHEN metric = 'avg_points_per_lap'
      AND monaco IS NOT NULL
      AND australian IS NOT NULL
      THEN 'density_diverges'
    ELSE NULL
  END AS verdict_hint
FROM rolled
ORDER BY
  CASE family
    WHEN 'volume' THEN 1
    WHEN 'laps_completeness' THEN 2
    WHEN 'telemetry_density' THEN 3
    WHEN 'telemetry_quality' THEN 4
    WHEN 'join_integrity' THEN 5
    WHEN 'import_freshness' THEN 6
    ELSE 9
  END,
  metric;
