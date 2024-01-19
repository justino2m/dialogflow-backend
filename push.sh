echo "Unsetting local ds emulator env var"
unset -v DATASTORE_EMULATOR_HOST
echo "pushing FAQ entities"
bot upload
echo "pushing synonyms"
bot synonyms