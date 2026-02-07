# Pitwall Tool Definitions

## 1. Virtual View (Data Layer)
- **Endpoint**: `GET /api/pitwall/view`
- **Query Params**: `name` (e.g., "sample_laps")
- **Behavior**: Deterministic SQL execution against BigQuery.
- **Returns**: `PitwallDataResponse`
  ```json
  {
    "rows": [{"col": "val"}],
    "columns": ["col1", "col2"],
    "rowCount": 100,
    "bytesProcessed": 1024
  }
  ```

## 2. Viz Generator (AI Layer)
- **Endpoint**: `POST /api/pitwall/viz`
- **Body**:
  ```json
  {
    "prompt": "User's natural language request (e.g. 'Compare lap times')",
    "columns": ["driver_id", "lap_time_ms", ...],
    "sampleRows": [{"driver_id": 44, "lap_time_ms": 90000}, ...]
  }
  ```
- **Behavior**: Uses Gemini to generate a best-fit Vega-Lite spec.
- **Returns**: `PitwallVizResponse`
  ```json
  {
    "vegaLiteSpec": { ... },
    "title": "Chart Title",
    "explanation": "Brief reasoning for the chart choice",
    "caveats": ["Note: only showing top 5 drivers"]
  }
  ```
