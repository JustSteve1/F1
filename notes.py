from google.cloud import bigquery

client = bigquery.Client(project="f1-data-library")

datasets = list(client.list_datasets())
for d in datasets:
    print(d.dataset_id)



client = bigquery.Client(project="f1-data-library")

for ds in client.list_datasets():
    dataset = client.get_dataset(ds.reference)
    print(dataset.dataset_id, "→ location:", dataset.location)

PROJECT_ID = "f1-data-library"
DATASET_ID = "f1_data_library_DS"   # confirm from Step 1

client = bigquery.Client(project=PROJECT_ID)

tables = list(client.list_tables(f"{PROJECT_ID}.{DATASET_ID}"))
print("Tables found:")
for t in tables:
    print("-", t.table_id)
