-- Keep one laps row per (session_key, driver_number, lap_number) for
-- 2026 Dutch Grand Prix race. session_key = MD5("2026-Dutch Grand Prix-R")[:8]
-- as int = 2456128946. Prefers the earliest imported_at.
--
-- Dry-run counts:
--   SELECT CAST(driver_number AS STRING) AS driver_number, lap_number, COUNT(*) c
--   FROM `f1-data-library.f1_data_library_DS.laps`
--   WHERE session_key = 2456128946
--   GROUP BY 1, 2 HAVING c > 1;

DELETE FROM `f1-data-library.f1_data_library_DS.laps` AS t
WHERE t.session_key = 2456128946
  AND EXISTS (
    SELECT 1
    FROM `f1-data-library.f1_data_library_DS.laps` AS o
    WHERE o.session_key = t.session_key
      AND CAST(o.driver_number AS STRING) = CAST(t.driver_number AS STRING)
      AND o.lap_number = t.lap_number
      AND o.imported_at < t.imported_at
  );
