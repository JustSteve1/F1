-- Narrow Kaggle source of truth. One row per lap; telemetry is a JSON array STRING at 2 Hz.
-- Avoids BQ JSON type so Parquet / dataframe loads cannot fail on that column.
--
--   bq query --project_id=f1-data-library --use_legacy_sql=false \
--     < sql/create_for_kaggle_export.sql

CREATE TABLE IF NOT EXISTS `f1-data-library.f1_data_library_DS.for_kaggle_export` (
  season INT64,
  event_name STRING,
  circuit STRING,
  session_type STRING,
  driver STRING,
  driver_number INT64,
  lap_number INT64,
  lap_time STRING,
  lap_duration FLOAT64,
  compound STRING,
  tyre_age INT64,
  stint_number INT64,
  telemetry STRING
)
CLUSTER BY season, event_name, session_type;
