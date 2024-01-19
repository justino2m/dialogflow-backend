echo "Unsetting local ds emulator env var"
unset -v DATASTORE_EMULATOR_HOST
echo "Migrating entities for departments"
python scripts/migrate_ents.py