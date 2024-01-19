prod: gunicorn -b :$PORT autoapp:app
dev: flask run --host=localhost --port=5000
push_remote: sh push.sh
push_local: bot upload && bot synonyms
pull_remote: sh pull.sh
pull_local: bot download
migrate_local: python scripts/migrate_ents.py
migrate_remote: sh migrate.sh