import csv
import os
from google.cloud import datastore
from scripts.config import DATA_DIR


ds = datastore.Client()
query = ds.query(kind="FaqCDRA")

csv_path = os.path.join(DATA_DIR, "faqs.csv")

with open(csv_path, "w", newline="") as f:
    field_names = ["Name", "Speech", "TextResponse"]
    writer = csv.DictWriter(f, field_names, extrasaction="ignore")

    writer.writeheader()

    for entity in query.fetch():
        print("writing f{entity.key.name}")
        writer.writerow(entity)
