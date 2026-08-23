# Kaggle export workflow

Incremental append of new laps onto [stevefza/f1-2026-bahrain-testing-day-2](https://www.kaggle.com/datasets/stevefza/f1-2026-bahrain-testing-day-2).

Kaggle versions replace the file set. Each deploy still uploads one cumulative `All Laps - {date}.csv`: every previous row plus only the new laps.

## One-time machine setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in local paths / token; never commit .env
```

BigQuery (service account `cursorf1@f1-data-library.iam.gserviceaccount.com`):

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/cursorf1.json
```

Or impersonate that SA after a user login:

```bash
gcloud auth application-default login \
  --impersonate-service-account=cursorf1@f1-data-library.iam.gserviceaccount.com
```

Kaggle (API token only — no username/key required):

```bash
export KAGGLE_API_TOKEN=...   # from https://www.kaggle.com/settings/api
```

## Every time you have new laps in BigQuery

1. Import the session(s) into `f1-data-library.f1_data_library_DS` (FastF1 pipeline).
2. Append and publish:

```bash
python kaggle_upload.py deploy
# or
./scripts/kaggle_deploy.sh
```

3. Confirm the log line `N new laps / M already on Kaggle` and the new Kaggle version.
4. Consumers keep using:

```python
import kagglehub
path = kagglehub.dataset_download("stevefza/f1-2026-bahrain-testing-day-2")
```

Optional filters when you only imported one weekend:

```bash
python kaggle_upload.py deploy --event "Dutch Grand Prix" --session-type R
```

Inspect the export SQL without running it:

```bash
python kaggle_upload.py --print-sql
```

## Rare full rebuild

Rebuild the CSV from BigQuery only (does not download or keep the live Kaggle file):

```bash
python kaggle_upload.py deploy --full-refresh
```

## What deploy does by default

1. Download the live Kaggle CSV.
2. Query cheap lap keys from BigQuery (no telemetry aggregation).
3. Diff on `season + event_name + session_type + driver_number + lap_number`.
4. If nothing new: exit 0, no upload.
5. Export only the new laps in the agreed schema, append them, upload one dataset version.
