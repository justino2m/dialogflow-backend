from google.cloud import datastore
from google.api_core.exceptions import FailedPrecondition
import dialogflow_v2 as df
import json
import click

from .config import ENTITY_JSON_FILE, DS_KINDS, DF_ENTITIES, PROJECT_ID
from scripts.create_synonyms import ds_upload_syn_entities

ds = datastore.Client()


with open(ENTITY_JSON_FILE, "r") as f:
    entity_dict = json.load(f)


def ds_upload_kind(kind):
    with open(ENTITY_JSON_FILE, "r") as f:
        entity_dict = json.load(f)

    entities = []
    kind_data = entity_dict[kind]
    click.secho(f"Uploading {kind} datastore entities", fg="green")
    for name, data in kind_data.items():
        key = ds.key(kind, name)
        entity = datastore.Entity(key=key)

        entity.update(data)
        entities.append(entity)

    click.secho(f"Pushing {kind} datastore entities", fg="green")
    ds.put_multi(entities)


def df_create_entity_type(kind):
    """Creates an entity type matching the name of the DS entity kind"""

    #  df_kind refers to enetity type, not ds kind
    # for example KIND_MAP (default) or KIND_LIST
    df_kind = "KIND_LIST"
    entity_types_client = df.EntityTypesClient()

    parent = entity_types_client.project_agent_path(PROJECT_ID)
    entity_type = df.types.EntityType(display_name=kind, kind=df_kind)
    try:
        response = entity_types_client.create_entity_type(parent, entity_type)
        click.secho("Entity type created: {}\n".format(response), fg="cyan")
    except FailedPrecondition:
        click.secho(
            f"Skipping creation of {kind} entity type, already exists", fg="red"
        )


@click.command()
def upload():
    """
    Upload datastore entities for KINDS listed in scripts.config
    This will not upload dialogflow entities, but will create the entity type
    if it does not exist.

    To import dialogflow faq/synonym entitries and the Datstore Synonym Kind,
    run:
    `bot synonyms`
    """
    click.secho(f"Uploading entities")

    # to many synonyms for single "put" call
    for kind in [k for k in DS_KINDS if k != "Synonym"]:
        ds_upload_kind(kind)
        click.secho(f"Uploaded {kind} datastore enties", fg="green")

    for ent in [e for e in DF_ENTITIES]:
        # create DF entity type for kind
        # if it doesnt exist yet
        click.secho(f"Creating {ent} dialogflow entity type", fg="cyan")
        df_create_entity_type(ent)

    click.secho(
        "All non-synonym entities uploaded, to upload synonyms please run", fg="cyan"
    )
    click.secho("`bot synonyms`", fg="yellow")


if __name__ == "__main__":
    upload()
