# F1 Data Library

Lap-level Formula 1 timing and telemetry for the live season. This repo is the ingest, warehouse, and export for [JustSteve1/F1](https://github.com/JustSteve1/F1). The warehouse is BigQuery project `f1-data-library`, dataset `f1_data_library_DS`. The public file is [stevefza/f1-2026-bahrain-testing-day-2](https://www.kaggle.com/datasets/stevefza/f1-2026-bahrain-testing-day-2).

Two ingest paths write into **separate** tables. They are never joined across sources.

| Path | When | Writes | Runs where |
| --- | --- | --- | --- |
| Live (architecture v2) | During a session, then from F1's static archive after it | `laps_live`, `telemetry_live` | Home / residential host (livetiming blocks datacentres) |
| FastF1 batch (failsafe) | Sessions that were not captured live | `laps`, `telemetry`, `sessions` | Cloud Run job `f1-telemetry-import` |

`laps_for_export` takes a whole session from live if that session has live laps, otherwise from the FastF1 tables. A live lap time is never paired with batch telemetry.

## Architecture v2

Official livetiming is the source. The subscriber talks to `wss://livetiming.formula1.com/signalrcore`, merges `TimingData`, and writes each finished lap plus a 0.5 s car/position grid.

- Live tables: `laps_live` (`LIKE laps`) and `telemetry_live` (`LIKE telemetry`).
- Export views: [`db/bigquery/laps_kaggle.sql`](db/bigquery/laps_kaggle.sql) — `laps_all_legacy`, `laps_all_live`, `laps_for_export`, `laps_kaggle`.
- Telemetry JSON keys: `t`, `speed`, `throttle`, `brake`, `gear`, `rpm`, `drs`, `x`, `y`, `z`.
- After the session, `live_archive.py` replays F1's `StreamPath` files. Laps and full traces already stored are left alone.
- FastF1 skips a session that already has rows in `laps_live`, unless `noSkip` is set. FastF1 still runs for every session that was never captured live.

Details: [`docs/live-timing-sync.md`](docs/live-timing-sync.md).

## FastF1 failsafe

The batch job is unchanged. `worker/pipeline/f1_telemetry_import.py` still loads FastF1, resamples, and writes `laps` / `telemetry`. The Cloud Run trigger still forces `INGEST_SOURCE=fastf1`. The GCS cache at `gs://f1-data-library-fastf1-cache/fastf1` is still pulled before a livetiming download.

Use this path to backfill history and any session the live host missed. Do not delete it.

Jobs admin and Cloud Run setup: [`ADMIN_JOBS.md`](./ADMIN_JOBS.md).

## Auth and the weekend watcher

`CarData.z`, `Position.z`, and the post-session archive need an F1 TV bearer.

```bash
python worker/pipeline/live_token.py ensure   # keep / renew / sign in
python worker/pipeline/live_watch.py          # start the subscriber for each session
```

The token file is `~/.config/interval/f1-subscription-token` (mode 600). The watcher belongs on the same residential host as the subscriber. See [`docs/auth-v2.md`](docs/auth-v2.md).

## Kaggle export

`worker/pipeline/kaggle_upload.py` reads `laps_for_export`, merges with the current public CSV, and publishes `all_laps.csv` with usability metadata. The listing id is locked (`9485317`). Existing rows are not rewritten except when the same lap key is replaced by the view.

```bash
python worker/pipeline/kaggle_upload.py
python worker/pipeline/kaggle_upload.py --republish
```

## Local app

```bash
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

| Route | What it shows |
| --- | --- |
| `/live` | Timing board |
| `/live/laps` | Completed live laps |
| `/live/map` | Speed trace on the circuit |
| `/admin/jobs` | FastF1 → BigQuery → Kaggle job control |

```bash
docker compose up -d postgres
cp .env.example .env.local
pnpm dev
```

Worker tests (from `worker/pipeline`):

```bash
python3 -m unittest test_live_laps.py test_live_telemetry.py test_live_archive.py \
  test_timing_state.py test_kaggle_merge.py test_kaggle_metadata.py \
  test_f1_telemetry_import.py test_live_token.py test_live_watch.py
```

## Deploy

The Next.js app deploys on Vercel. Protect `/admin` with Deployment Protection. The FastF1 worker stays on Cloud Run; the live subscriber does not.
