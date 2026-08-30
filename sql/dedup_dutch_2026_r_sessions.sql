-- Keep one sessions row for 2026 Dutch GP race (session_key 2456128946).
-- Two failed R jobs inserted two session rows; laps dedup does not touch sessions.
--
--   bq query --project_id=f1-data-library --use_legacy_sql=false --nouse_cache \
--     < sql/dedup_dutch_2026_r_sessions.sql

BEGIN
  CREATE TEMP TABLE dutch_r_session_keep AS
  SELECT * EXCEPT (rn)
  FROM (
    SELECT
      s.*,
      ROW_NUMBER() OVER (ORDER BY s.imported_at ASC NULLS LAST) AS rn
    FROM `f1-data-library.f1_data_library_DS.sessions` AS s
    WHERE s.session_key = 2456128946
  )
  WHERE rn = 1;

  BEGIN TRANSACTION;
    DELETE FROM `f1-data-library.f1_data_library_DS.sessions`
    WHERE session_key = 2456128946;

    INSERT INTO `f1-data-library.f1_data_library_DS.sessions`
    SELECT * FROM dutch_r_session_keep;
  COMMIT TRANSACTION;

  SELECT COUNT(*) AS session_rows
  FROM `f1-data-library.f1_data_library_DS.sessions`
  WHERE session_key = 2456128946;
END;
