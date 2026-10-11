# Live timing sync

Interval.ai already describes a live Formula 1 sync. The pitwall screen is still mock UI. The only real ingest today is the one-shot FastF1 job. This note is the source comparison, the timing topics, the one-source rule, and the hosting rule for the live path.

The subscriber records the official timing hub and merges `TimingData` on a non-GCP host. Each newly completed lap is appended to `laps_live`, a BigQuery table with the same columns as `laps`. The batch job still owns `laps` and `laps_unified`. The jobs admin and the pitwall are unchanged.

## What each source can do

### Official livetiming

`livetiming.formula1.com` is the source FastF1 itself downloads. There is no public developer API. Live sessions use SignalR Core:

1. `POST https://livetiming.formula1.com/signalrcore/negotiate?negotiateVersion=1`
2. `wss://livetiming.formula1.com/signalrcore`
3. `Subscribe` on the `feed` event

After the session, F1 publishes `static/{year}/Index.json` plus per-feed `KeyFramePath` and `StreamPath` files. `TimingData` is a delta stream: sectors, laps, gaps, and intervals. A later sector patch must be merged into the driver line already stored, or the lap time disappears. `CarData.z` and `Position.z` are the high-rate car streams (base64 and zlib). Those need an F1 TV Access, Pro, or Premium bearer. The hub drops the socket after about two hours, so a subscriber has to reconnect and dedupe.

### FastF1

FastF1 stays the history path. It is a client of the official static archive, not a second data vendor, which is why the warehouse uses FastF1 and not OpenF1. Its live client only records the socket to disk and cannot merge the stream while the session is running.

Cloud Run, Colab, and other datacenter IPs get `Failed to load timing data`. That is why [ADMIN_JOBS.md](../ADMIN_JOBS.md) seeds `gs://f1-data-library-fastf1-cache/fastf1` from a home connection and the worker pulls that cache before any livetiming download. A live recording and a later FastF1 reload of the same session do not line up.

### OpenF1

OpenF1 stays out of the sync path. It is a third-party HTTP API in front of F1. The Cloud Run trigger forces `INGEST_SOURCE=fastf1` because race-length `car_data` returned HTTP 422 (Dutch GP 2026, session `11353`). An earlier OpenF1 load also drifted the BigQuery laps schema and broke NDJSON loads. It is fine for a one-off notebook check. It is not the sync layer.

## Timing topics

The first slice is the timing board. These topics are the real-time time sync: gaps, sectors, lap times, and the session clock.

- `Heartbeat`
- `SessionInfo`
- `SessionStatus`
- `DriverList`
- `TimingData`
- `TimingAppData`
- `TimingStats`
- `TrackStatus`
- `WeatherData`
- `RaceControlMessages`
- `LapCount`
- `ExtrapolatedClock`

`CarData.z` and `Position.z` stay behind an F1 TV token taken from a real browser login. F1 blocks headless username and password. That later slice is what would feed the 10 Hz telemetry the warehouse already resamples at 0.1 s.

The spike stores the subscription JWT from the signed-in browser (`login-session` cookie, `data.subscriptionToken`) outside the repo and sends it as the SignalR bearer. Negotiate-only, with no bearer, is not the path this spike uses.

## One session, one source

A session captured live is not imported again through FastF1.

- If a live archive exists for that session, the FastF1 job must skip it.
- After the session, prefer F1's own `StreamPath` files once `Index.json` sets `Path`.
- Use FastF1 only to backfill sessions that were not captured live.

BigQuery (`sessions`, `laps`, `telemetry`, `laps_unified`) stays the batch path. Live finishes go to `laps_live` (`LIKE laps`). Live position samples go to `telemetry_live` (`LIKE telemetry`). The `_live` suffix marks every architecture-v2 import. A live lap is joined only to live samples, and a batch lap is joined only to batch telemetry. The jobs admin stays the control plane for archive imports: a session captured live is not imported again through FastF1.

### Export views

`laps_all_legacy` reads only the batch tables. It is the `laps_unified` join of `laps` to `telemetry` on `session_key`, `driver_number`, and `lap_number`.

`laps_all_live` reads only the live tables. It is the same join of `laps_live` to `telemetry_live`. Position samples are tagged with the lap in progress (`NumberOfLaps + 1`) as they arrive, so the join key is known before the lap row exists.

`laps_for_export` is the view export reads. For each session it takes `laps_all_live` when that session has live laps, and `laps_all_legacy` otherwise. It never pairs a lap time from one source with telemetry from the other.

## Hosting

Do not run the live subscriber on Cloud Run. Livetiming blocks datacenter IPs, so the process belongs on the same class of connection that already seeds the FastF1 cache: the home machine during a race weekend, or a small always-on host with residential egress. A short probe from GCP can confirm whether the block applies to the websocket as well as to FastF1's HTTP downloads. Until that probe succeeds, GCP is not the live runtime.

The subscriber refuses to start a live connection when `K_SERVICE` or `CLOUD_RUN_JOB` is set. Replaying a local JSONL archive does not open the hub, so that command is allowed on any host.

## Spike

| Piece | Where |
| --- | --- |
| Bearer file | `worker/pipeline/live_token.py` writes `~/.config/interval/f1-subscription-token` (mode 600). Override with `F1_SUBSCRIPTION_TOKEN_FILE`. |
| Subscriber | `worker/pipeline/live_subscriber.py` negotiates SignalR Core, subscribes to the topics above, and appends every message to `~/.local/share/interval/live/<timestamp>-live.jsonl`. |
| Merged state | `worker/pipeline/timing_state.py` deep-merges `TimingData` and writes `timing-snapshot.json` in that same directory. |
| Replay | `python worker/pipeline/live_subscriber.py --replay <file.jsonl>` rebuilds the snapshot and `live-laps.json` offline. |
| Completed laps | `worker/pipeline/live_laps.py` appends each finished lap to `live-laps.json` and inserts it into `f1-data-library.f1_data_library_DS.laps_live`. `/live/laps` lists that file, newest first. |

Raw frames stay on local disk. A GCS archive, under a prefix separate from the FastF1 cache, is the later home for those frames. The pitwall and SSE fan-out are still the following slice.
