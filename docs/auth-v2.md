# Auth v2.0 — keeping the live import signed in

The live import (architecture v2) needs an F1 TV bearer for `CarData.z`, `Position.z`, and the post-session archive files. This note explains why that bearer keeps expiring, what the branch does about it, and how the import now starts itself for each session.

## What the 24 October token actually is

The sentence from the previous run — *"The subscription token is stored on this machine. It is active for F1 TV Access Monthly and expires at 11:21 AM UK time on Wednesday 28 October"* — describes four separate limits.

| Limit | What it means |
| --- | --- |
| **It is a four-day JWT.** | `subscriptionToken` is signed by Formula 1 with `exp` about 96 h after sign-in. It was captured at about 11:21 UK on Saturday 24 October, so it dies at 11:21 UK on Wednesday 28 October. That covers Austin (FP3, Q, R) but not Mexico City (FP1 is Friday 30 October). |
| **There is no refresh token.** | F1 issues nothing that extends it. FastF1's own documentation: *"Tokens cannot be automatically refreshed before they expire."* Every third-party tool (FastF1, RaceControl, f1viewer, F1 Sensor) hits the same wall. |
| **"This machine" was a cloud agent VM.** | The token file lived at `~/.config/interval/f1-subscription-token` on the agent's VM. That VM is recycled between runs, so the token goes with it, and its address is a datacenter IP. The archive files downloaded fine from there, but the livetiming hub blocks datacenter IPs, so that machine could never have recorded a live session anyway (see [live-timing-sync.md](./live-timing-sync.md), *Hosting*). |
| **Sign-in needs a real browser.** | `account.formula1.com` sits behind Imperva bot protection. A bare `POST …/authenticate/by-password` gets a captcha page, which is why the previous run opened Chrome over VNC and asked you to type the password yourself. |

So the real question is not "how do we get a token" but "how does a process that runs unattended on a home connection keep a valid token for a whole season".

## What changed since the spike

Two things make unattended renewal possible today.

1. **The token carries its own account session.** The JWT has a `SessionId` claim. Posting that id to `api.formula1.com/v1/account/Subscriber/RetrieveSubscriber` (the call the F1 web client itself makes) returns a *new* `subscriptionToken` with a fresh four-day `exp`. The session behind it has an observed life of about thirty days from the original sign-in. The Home Assistant F1 Sensor integration renews this way in the token's final 24 hours. No password is involved.
2. **The account site moved to PingOne.** Sign-in is now an OAuth Authorization-Code + PKCE flow against `id.formula1.com`. With `response_mode=pi.flow` every step is a JSON call, so email + password are enough from a script. FastF1 3.9.0 ships exactly this as its default `password` method (`F1_USERNAME` / `F1_PASSWORD`).

## The token lifecycle on this branch

`worker/pipeline/live_token.py` now owns the token from capture to renewal. `worker/pipeline/f1_account.py` holds the two network flows.

| Tier | Command | When it is used | Needs | Lifetime it buys |
| --- | --- | --- | --- | --- |
| 0 Keep | `live_token.py check` | Token has more than 24 h left | nothing | — |
| 1 Renew | `live_token.py renew` | Less than 24 h left, session alive | the stored token only | 4 days, repeatable for ~30 days |
| 2 Sign in | `live_token.py login` | Session rejected (401/403) or missing | `F1_USERNAME`+`F1_PASSWORD`, or `F1_CREDENTIALS_FILE`, or the macOS keychain item `interval-f1-account` | 4 days + a new 30-day session |
| 3 Capture | `live_token.py capture` (default) | Nothing else works | you, signed in to the debug Chrome | 4 days + a new 30-day session |

`live_token.py ensure` runs tiers 0 → 1 → 2 and stops at the first that works. If none works but the token is still usable, it keeps it and records why in the status file. If the token is dead it exits 1 with the sign-in instructions; a temporary network failure exits 2.

Every operation writes a **redacted** status file next to the token (`f1-subscription-token.status.json`: state, expiry, product, whether the session is renewable, last action and error — never the token itself). `live_token.py status` prints it.

The token file itself is unchanged: `~/.config/interval/f1-subscription-token`, mode 600, overridable with `F1_SUBSCRIPTION_TOKEN_FILE`. `live_subscriber.py` and `live_archive.py` keep reading it as before.

### Storing credentials for tier 2

Tier 2 is optional. Without it the branch still renews unattended for about a month, then asks you to sign in once. With it the watcher survives the 30-day session expiry on its own.

- `F1_USERNAME` / `F1_PASSWORD` in the environment of the watcher process (launchd `EnvironmentVariables`, or a `.env` you source).
- `F1_CREDENTIALS_FILE=~/.config/interval/f1-credentials.json` containing `{"username": "...", "password": "..."}`, mode 600.
- macOS keychain, no file at all: `security add-generic-password -s interval-f1-account -a you@example.com -w` (it prompts for the password). Set `F1_KEYCHAIN_SERVICE` to use another item name.

Credentials are sent to `id.formula1.com` only and are never logged or written by the pipeline. Use a dedicated F1 account password and keep 2FA off that account, or tier 2 cannot complete.

## Auto-starting the import

`worker/pipeline/live_watch.py` is the long-running process for the home machine. It replaces "say when the session starts and I'll start it".

1. Loads the FastF1 event schedule for the season and caches it in the live directory for a day (`schedule-2026.json`). A stale cache is still used if FastF1 is unreachable.
2. Picks the next session that has not been recorded. The recording window is `--lead-minutes` (default 60, FastF1's recommendation) before the session until the nominal length plus `--grace-minutes` (default 30): FP/Q 60 min, SQ 45, Sprint 60, Race 180.
3. Runs `live_token.py ensure` every `--token-check-hours` (default 6) while armed, again 15 minutes before the window, and before every start. Renewals, sign-ins, and failures are reported once, not on every check.
4. Starts `live_subscriber.py --dir <live dir>` at the window start. Output goes to `watcher-subscriber.log`.
5. If the subscriber exits (the hub drops sockets after about two hours) it is restarted with a short backoff, up to `--max-restarts` (12). The lap and telemetry writers already dedupe, so a restart does not double-write.
6. Stops `--finalised-minutes` (10) after the snapshot reports `SessionStatus` `Finished`, `Finalised`, or `Ends`, or at the hard end of the window. SIGINT is used so the subscriber flushes telemetry and prints its topic rates.
7. Marks the session recorded in `watcher-state.json` so a watcher restart mid-weekend does not re-record it, and moves on.

```bash
python3 worker/pipeline/live_watch.py --plan          # show the next windows and the token state
python3 worker/pipeline/live_watch.py                 # run the watcher
python3 worker/pipeline/live_watch.py --record-now 15 # smoke test: record for 15 minutes now
```

The watcher refuses to run on Cloud Run (`K_SERVICE` / `CLOUD_RUN_JOB`) for the same reason the subscriber does.

### Keeping you informed

`worker/pipeline/notify.py` posts every watcher event:

- always to stdout and to `events.jsonl` in the live directory;
- to Slack or Discord when `INTERVAL_NOTIFY_WEBHOOK` is set (payload shape is picked from the URL);
- to Notification Center (macOS) or `notify-send` (Linux) when `INTERVAL_NOTIFY_DESKTOP=1`.

Events: watcher started/stopped, token renewed, signed in, token could not be renewed, sign-in required, recording started, subscriber restarted, session finished, recording stopped (with the number of completed laps), session missed.

`GET /api/live-status` merges `watcher-status.json`, the token status file, and the last eight events. The `/live` page shows them in a strip above the timing board: watcher state, next or current session with a countdown, token state with time left (green > 24 h, amber < 24 h, red expired or missing), and the latest event.

### Running it on the Mac

The watcher has to be on the same connection that records: your Mac or a small always-on box at home. `worker/scripts/com.interval.live-watch.plist` is a launchd template; edit the paths and credentials, then:

```bash
cp worker/scripts/com.interval.live-watch.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.interval.live-watch.plist
launchctl kickstart -k gui/$(id -u)/com.interval.live-watch
tail -f ~/.local/share/interval/live/watcher.log
```

The Mac must be awake during sessions. `caffeinate -s` in the plist, or Energy Saver → prevent sleep, covers that. If the machine is asleep when a window opens, the watcher starts recording as soon as it wakes, because the window is still open.

## Decisions to make together

1. **Store the F1 password or not.** Without it: renew for ~30 days, then one browser sign-in a month, which the watcher asks for a day ahead. With it: fully unattended. Keychain is the least exposed option on a Mac.
2. **Where the notifications go.** A Slack or Discord webhook URL is the fastest; desktop notifications only help if you are at the machine.
3. **Which machine runs the watcher.** Your Mac is fine for a weekend; a Raspberry Pi or NUC on home Wi-Fi is better for a season. The code has no macOS dependency except the keychain lookup.
4. **Lead time.** 60 minutes matches FastF1's advice for a complete `DriverList`/`SessionInfo` picture; 30 would do if the Mac is otherwise busy.
5. **Backfill after a session.** `live_archive.py` can replay the official archive once `Index.json` lists the session. The watcher does not call it yet; it would be a natural post-stop step when restarts left a gap.

## Known limits and the first thing to verify

- `RetrieveSubscriber` and the PingOne flow are the web client's own calls, read from F1 Sensor and FastF1 3.9.0. F1 can change either without notice. Both live in `f1_account.py` only; browser capture stays as the fallback and the watcher tells you when it is needed.
- Neither flow has been exercised from this branch against formula1.com yet: the cloud agent VM that holds the 24 October token is not this one. The first real check should be on the Mac that holds the token, before Wednesday 11:21 UK:

```bash
python3 worker/pipeline/live_token.py check          # confirms the current token
python3 worker/pipeline/live_token.py renew --force  # proves the session path; prints the new expiry
python3 worker/pipeline/live_token.py status
```

If `renew --force` succeeds, the Mexico City weekend needs no sign-in at all.
