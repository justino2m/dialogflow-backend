BUCKET="testing-datastore-backup"
gcloud datastore export --kinds="FaqCDRA,ZoningCodes,Synonym" gs://${BUCKET}
