import os
from google.cloud import datastore

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
AGENT_DIR = os.path.join(DATA_DIR, "agent")
ENTITY_JSON_FILE = os.path.join(DATA_DIR, "entities.json")

# List all datastore kinds to be synced
DS_KINDS = ["FAQ", "ZoningCode", "PipeType", "Credentials", "Synonym"]

# List only entities to be synced with dialogflow
DF_ENTITIES = ["FAQ", "ZoningCode", "PipeType"]


PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "test-county-staging")


def get_ds_client():
    return datastore.Client()
