from google.cloud import bigquery

PROJECT_ID = "f1-data-library"

client = bigquery.Client(project=PROJECT_ID)

datasets = list(client.list_datasets())
print("Datasets:")
for d in datasets:
    print("-", d.dataset_id)
