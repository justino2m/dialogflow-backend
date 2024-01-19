echo "Unsetting local ds emulator env var"
unset -v DATASTORE_EMULATOR_HOST
echo "Downloading all datastore entities defined in config.KINDS"
bot download
