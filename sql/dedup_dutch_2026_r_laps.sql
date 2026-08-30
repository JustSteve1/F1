-- Keep one laps row per (driver_number, lap_number) for 2026 Dutch GP race.
-- session_key = MD5("2026-Dutch Grand Prix-R")[:8] as int = 2456128946.
-- Prefers the earliest imported_at; ROW_NUMBER still keeps one row on ties.
--
-- Telemetry for this session is not rewritten (R never landed telemetry).
--
-- Preview:
--   bq query --project_id=f1-data-library --use_legacy_sql=false --nouse_cache \
--     < sql/preview_dutch_2026_r.sql
-- Apply:
--   bq query --project_id=f1-data-library --use_legacy_sql=false --nouse_cache \
--     < sql/dedup_dutch_2026_r_laps.sql
-- Or: ./scripts/gcp/dedup-dutch-r-laps.sh --apply

BEGIN
  CREATE TEMP TABLE dutch_r_before AS
  SELECT
    COUNT(*) AS laps_rows,
    COUNT(DISTINCT CONCAT(CAST(driver_number AS STRING), '-', CAST(lap_number AS STRING))) AS unique_driver_laps,
    (
      SELECT COUNT(*)
      FROM `f1-data-library.f1_data_library_DS.telemetry`
      WHERE session_key = 2456128946
    ) AS telemetry_rows,
    (
      SELECT COUNT(*)
      FROM `f1-data-library.f1_data_library_DS.sessions`
      WHERE session_key = 2456128946
    ) AS session_rows
  FROM `f1-data-library.f1_data_library_DS.laps`
  WHERE session_key = 2456128946;

  CREATE TEMP TABLE dutch_r_keep AS
  SELECT * EXCEPT (rn)
  FROM (
    SELECT
      t.*,
      ROW_NUMBER() OVER (
        PARTITION BY CAST(t.driver_number AS STRING), t.lap_number
        ORDER BY t.imported_at ASC NULLS LAST
      ) AS rn
    FROM `f1-data-library.f1_data_library_DS.laps` AS t
    WHERE t.session_key = 2456128946
  )
  WHERE rn = 1;

  BEGIN TRANSACTION;
    DELETE FROM `f1-data-library.f1_data_library_DS.laps`
    WHERE session_key = 2456128946;

    INSERT INTO `f1-data-library.f1_data_library_DS.laps`
    SELECT * FROM dutch_r_keep;
  COMMIT TRANSACTION;

  SELECT
    phase,
    laps_rows,
    unique_driver_laps,
    extra_copies,
    telemetry_rows,
    session_rows
  FROM (
    SELECT
      'before' AS phase,
      laps_rows,
      unique_driver_laps,
      laps_rows - unique_driver_laps AS extra_copies,
      telemetry_rows,
      session_rows
    FROM dutch_r_before

    UNION ALL

    SELECT
      'after' AS phase,
      COUNT(*) AS laps_rows,
      COUNT(DISTINCT CONCAT(CAST(driver_number AS STRING), '-', CAST(lap_number AS STRING))) AS unique_driver_laps,
      COUNT(*) - COUNT(DISTINCT CONCAT(CAST(driver_number AS STRING), '-', CAST(lap_number AS STRING))) AS extra_copies,
      (
        SELECT COUNT(*)
        FROM `f1-data-library.f1_data_library_DS.telemetry`
        WHERE session_key = 2456128946
      ) AS telemetry_rows,
      (
        SELECT COUNT(*)
        FROM `f1-data-library.f1_data_library_DS.sessions`
        WHERE session_key = 2456128946
      ) AS session_rows
    FROM `f1-data-library.f1_data_library_DS.laps`
    WHERE session_key = 2456128946
  )
  ORDER BY phase DESC;
END;
