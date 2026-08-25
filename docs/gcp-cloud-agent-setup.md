# GCP Cloud Agent setup

Provision a read-only BigQuery service account for Cursor Cloud Agents to query stored F1 telemetry in `f1-data-library.f1_data_library_DS`.

## Prerequisites

1. GCP project **`f1-data-library`** with dataset **`f1_data_library_DS`**
2. A **bootstrap** service account key with permission to:
   - Create service accounts (`roles/iam.serviceAccountAdmin`)
   - Create keys (`roles/iam.serviceAccountKeyAdmin`)
   - Grant project IAM (`roles/resourcemanager.projectIamAdmin` or Owner/Editor)
   - Grant dataset IAM on `f1_data_library_DS` (`roles/bigquery.dataOwner` or dataset admin)

Project Owner/Editor works for a one-time bootstrap.

## Secrets (Cloud Agent environment)

| Secret | Required | Purpose |
|--------|----------|---------|
| `GCP_BOOTSTRAP_SERVICE_ACCOUNT_KEY` | Once | Admin JSON used only to create the reader SA |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | After provisioning | Reader SA JSON for ongoing BigQuery queries |
| `BQ_PROJECT` | Optional | Default `f1-data-library` |
| `BQ_DATASET` | Optional | Default `f1_data_library_DS` |

Add secrets in your [Cloud Agent environment dashboard](https://cursor.com/dashboard/cloud-agents/environments/e/6cdbf699-9e00-11f1-a7d1-d6b4613131ce).

**Never commit key JSON to the repository.**

## Provision the reader service account

From a Cloud Agent on `main` (or `MVP2`):

```bash
chmod +x scripts/gcp/provision-bq-reader-sa.sh scripts/gcp/list-2026-events.sh
./scripts/gcp/provision-bq-reader-sa.sh
```

This creates:

| Item | Value |
|------|-------|
| Service account | `cursor-bq-reader@f1-data-library.iam.gserviceaccount.com` |
| Project role | `roles/bigquery.jobUser` |
| Dataset role | `roles/bigquery.dataViewer` on `f1_data_library_DS` |
| Key file | `/tmp/cursor-bq-reader-key.json` (local only) |

IAM bindings use `--condition=None` to avoid interactive condition prompts when the project policy already has conditional bindings.

## Store the reader key

1. Copy the contents of `/tmp/cursor-bq-reader-key.json`
2. Add as Cloud Agent secret **`GOOGLE_SERVICE_ACCOUNT_KEY`**
3. Optionally remove **`GCP_BOOTSTRAP_SERVICE_ACCOUNT_KEY`** after provisioning

## Verify: list 2026 events

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/tmp/cursor-bq-reader-key.json
./scripts/gcp/list-2026-events.sh 2026
```

Or after `GOOGLE_SERVICE_ACCOUNT_KEY` is set:

```bash
./scripts/gcp/list-2026-events.sh 2026
```

## Conditional IAM troubleshooting

If `gcloud projects add-iam-policy-binding` prompts for a condition:

- Cancel with `Ctrl+C`
- Re-run with `--condition=None` (already in the provisioning script)
- Or grant **BigQuery Data Viewer** on the dataset via BigQuery Console → Sharing → Permissions

## Agent task prompt

Use this when starting a provisioning Cloud Agent:

> Install/verify gcloud, run `scripts/gcp/provision-bq-reader-sa.sh` using `GCP_BOOTSTRAP_SERVICE_ACCOUNT_KEY`, then run `scripts/gcp/list-2026-events.sh` with the new reader key. Request I add the generated JSON as `GOOGLE_SERVICE_ACCOUNT_KEY`. Do not commit keys.

## Security

- Bootstrap key: one-time admin access; revoke when done
- Reader key: read-only (`jobUser` + dataset `dataViewer` only)
- Do not grant Owner, Editor, or `bigquery.admin` to the reader SA
