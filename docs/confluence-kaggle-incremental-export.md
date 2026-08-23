# Kaggle incremental export (BigQuery → All Laps)

**Space:** Interval.ai / Data  
**Status:** Live  
**Owner:** Steve Fortuin  
**Last updated:** 23 August 2026  
**Code:** [JustSteve1/F1](https://github.com/JustSteve1/F1) · `kaggle_upload.py`

---

## Summary

After FastF1 data is in BigQuery, this job **appends new laps** onto the public Kaggle dataset [Formula One (F1) - All Laps & Telemetry Dataset](https://www.kaggle.com/datasets/stevefza/f1-2026-bahrain-testing-day-2) (`stevefza/f1-2026-bahrain-testing-day-2`).

It does **not** rebuild the whole season from BigQuery each time. It downloads the live Kaggle CSV, finds laps that are not already on Kaggle, exports only those rows from BigQuery (agreed schema, telemetry at 0.5s), concatenates them onto the existing file, and publishes **one new dataset version**.

Kaggle versions replace the file set. “Append” means the new version’s CSV still contains every previous row, plus the new ones.

Consumers keep using:

```python
import kagglehub
path = kagglehub.dataset_download("stevefza/f1-2026-bahrain-testing-day-2")
```

---

## Where this sits

FastF1 import writes sessions, laps, and telemetry into BigQuery `f1-data-library.f1_data_library_DS`. The Kaggle job is a **downstream snapshot** of that warehouse, not the live API.

| Step | System | What happens |
| --- | --- | --- |
| 1 | FastF1 → BigQuery | `f1_telemetry_import.py` loads a session |
| 2 | BigQuery | Source of truth: `telemetry`, `laps`, `driver_number_mapping` |
| 3 | `kaggle_upload.py deploy` | Incremental append + new Kaggle version |
| 4 | Kaggle | Public file `All Laps - {date}.csv` |
| 5 | Analysts / notebooks | `kagglehub.dataset_download(...)` |

Typical cadence: import a race weekend (or test day) into BigQuery, then run `deploy` once.

---

## How incremental append works

Default command: `python kaggle_upload.py deploy` (same as `./scripts/kaggle_deploy.sh`).

1. **Download** the current Kaggle dataset (kagglehub, falling back to the Kaggle CLI) and load every `All Laps*.csv`.
2. **Cheap key query** against BigQuery (`sql/kaggle_lap_keys.sql`). This returns only lap identity columns — no telemetry JSON aggregation.
3. **Diff** BigQuery keys vs the live CSV on:

   `season + event_name + session_type + driver_number + lap_number`

4. **If nothing new:** print that Kaggle is up to date and **exit 0** (no upload).
5. **If there are new laps:** run the agreed export SQL (`sql/kaggle_laps_export.sql`) filtered to those laps only (session_key / driver / lap). Telemetry is packed as JSON at **0.5 second / 2 Hz**.
6. **Validate** column order, `lap_time` as `M:SS.mmm`, and telemetry JSON keys.
7. **Append:** existing Kaggle rows are kept as-is; only unseen keys are added. Duplicate keys keep the existing row.
8. **Write** `All Laps - {D Month YYYY}.csv` plus `dataset-metadata.json`.
9. **Upload** a new dataset version (kagglehub when `KAGGLE_API_TOKEN` is set; otherwise `kaggle datasets version`).

Optional filters when you only imported one weekend: `--event "Dutch Grand Prix" --session-type R`.

Rare rebuild from BigQuery only (drops the live file, does not append): `--full-refresh`.

---

## Agreed schema (contract)

One **row per lap**. Column order is part of the contract.

| Column | Type | Meaning |
| --- | --- | --- |
| `season` | integer | Season year (default filter: 2026) |
| `event_name` | string | Grand Prix or test event |
| `circuit` | string | Circuit / location |
| `session_type` | string | FP1, FP2, FP3, Q, SQ, R, or test day |
| `driver` | string | Driver code (e.g. LEC); falls back to driver number via `driver_number_mapping` |
| `driver_number` | integer | Car number |
| `lap_number` | integer | Lap within the session |
| `lap_time` | string | Formatted `M:SS.mmm` (e.g. `1:34.273`) |
| `lap_duration` | decimal | Lap time in seconds (for ML) |
| `compound` | string | Tyre compound |
| `tyre_age` | integer | Tyre age in laps |
| `stint_number` | integer | Stint number |
| `telemetry` | string (JSON) | Array of 0.5s samples |

Each telemetry point:

| Key | Meaning |
| --- | --- |
| `t` | Time into the lap (seconds) |
| `speed` | Speed |
| `throttle` | Throttle |
| `brake` | Brake |
| `gear` | Gear |
| `rpm` | RPM |
| `drs` | DRS |
| `x`, `y`, `z` | Position (rounded to 1 decimal) |

Sampling rule in SQL: keep rows where `MOD(CAST(ROUND(lap_time_sec * 10) AS INT64), 5) = 0` and `speed IS NOT NULL`.

---

## Ways of working (every export)

### One-time setup (per machine)

```bash
pip install -r requirements.txt
cp .env.example .env   # never commit .env or keys
```

**BigQuery** — service account `cursorf1@f1-data-library.iam.gserviceaccount.com`:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/cursorf1.json
```

Or impersonate after a user login:

```bash
gcloud auth application-default login \
  --impersonate-service-account=cursorf1@f1-data-library.iam.gserviceaccount.com
```

**Kaggle** — API token only (no username / legacy key required):

```bash
export KAGGLE_API_TOKEN=...   # https://www.kaggle.com/settings/api
```

### After each BigQuery import

1. Confirm the session landed in `f1-data-library.f1_data_library_DS`.
2. Run:

   ```bash
   python kaggle_upload.py deploy
   ```

3. Check the log line `N new laps / M already on Kaggle` and the new version on the [dataset page](https://www.kaggle.com/datasets/stevefza/f1-2026-bahrain-testing-day-2).
4. Notebooks do not change — they always download the latest version via kagglehub.

Inspect SQL without running BigQuery:

```bash
python kaggle_upload.py --print-sql
```

Export locally without uploading: `python kaggle_upload.py export`  
Upload a folder you already built: `python kaggle_upload.py upload --dir exports/kaggle`

---

## Repository map

| Path | Role |
| --- | --- |
| `kaggle_upload.py` | CLI: `deploy` / `export` / `upload` |
| `scripts/kaggle_deploy.sh` | Thin wrapper around `deploy` |
| `sql/kaggle_lap_keys.sql` | Cheap identity query for the diff |
| `sql/kaggle_laps_export.sql` | Agreed-schema export (telemetry JSON) |
| `kaggle/dataset-metadata.json` | Title, license, field docs for the Kaggle CLI |
| `docs/kaggle-export.md` | Short operator runbook |

Do not commit `kaggle.json`, `KAGGLE_API_TOKEN`, or the `cursorf1` JSON key.

---

## What “up to date” looks like

| Log / outcome | Meaning |
| --- | --- |
| `N new laps / M already on Kaggle` then upload | New rows appended; new Kaggle version |
| `Nothing new to export. Kaggle dataset is already up to date.` | Diff was empty; **no upload** |
| `Full refresh from BigQuery` | `--full-refresh`; live CSV is not kept |

If a lap is already on Kaggle, a later BigQuery re-import of the same key does **not** overwrite it on incremental deploy. Use `--full-refresh` only when you intend to replace the published file from warehouse data.

---

## Auth and permissions

| Secret / account | Used for |
| --- | --- |
| `cursorf1@f1-data-library.iam.gserviceaccount.com` | BigQuery Job User + Data Viewer on `f1_data_library_DS` |
| `KAGGLE_API_TOKEN` | Download + create a new version as user `stevefza` |

The service account email is not enough on its own: the JSON key (or impersonation) must be available as Application Default Credentials.

---

## Notes

- Kaggle exports are point-in-time snapshots. Live / warehouse data may be newer until the next `deploy`.
- Expected Kaggle update frequency on the dataset is weekly; run `deploy` whenever a weekend (or test day) has been imported.
- Dataset slug is historical (`f1-2026-bahrain-testing-day-2`); the published title is the full-season All Laps dataset.
- Related import pipeline: `f1_telemetry_import.py` (FastF1 → BigQuery). This page covers **export only**.

---

## Related links

- [Kaggle dataset](https://www.kaggle.com/datasets/stevefza/f1-2026-bahrain-testing-day-2)
- [GitHub — JustSteve1/F1](https://github.com/JustSteve1/F1)
- Operator runbook in repo: `docs/kaggle-export.md`
