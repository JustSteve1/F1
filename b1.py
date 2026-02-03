import pandas as pd
from google.cloud import bigquery
from google.cloud import bigquery
import matplotlib.pyplot as plt

PROJECT_ID = "f1-data-library"
client = bigquery.Client(project="f1-data-library")
print("Using project:", client.project)

DATASET = "f1_data_library_DS"
client = bigquery.Client(project=PROJECT_ID, location="EU")

sql = """
SELECT *
FROM `f1-data-library.f1_data_library_DS.public_laps`
LIMIT 10
"""


client = bigquery.Client(project="f1-data-library")
job = client.query(sql, location="EU")
df = job.to_dataframe()
print(df.head())
print("hello world")

df = client.query(sql).to_dataframe()

print(df)


#print(df.head())
#print(f"\nTotal years: {len(df)}")

