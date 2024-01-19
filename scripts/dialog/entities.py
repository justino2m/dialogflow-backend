import click
import dialogflow_v2 as df

# from .config import get_project_id
from .base import entities, _get_entity_type_ids, PROJECT_ID


@entities.command()
@click.argument("entity_type")
def list(entity_type):
    entity_types_client = df.EntityTypesClient()

    entity_type_id = _get_entity_type_ids(PROJECT_ID, entity_type)

    parent = entity_types_client.entity_type_path(PROJECT_ID, entity_type_id)

    entities = entity_types_client.get_entity_type(parent).entities

    for entity in entities:
        print("Entity value: {}".format(entity.value))
        print("Entity synonyms: {}\n".format(entity.synonyms))


@entities.command()
@click.argument("entity-type")
@click.argument("entity-value")
@click.option("--synonyms", "-s", multiple=True)
def create(entity_type, entity_value, synonyms):
    synonyms = list(synonyms)

    entity_types_client = df.EntityTypesClient()

    # Note: synonyms must be exactly [entity_value] if the
    # entity_type's kind is KIND_LIST
    synonyms = synonyms or [entity_value]

    entity_type_id = _get_entity_type_ids(entity_type)

    entity_type_path = entity_types_client.entity_type_path(PROJECT_ID, entity_type_id)

    entity = df.types.EntityType.Entity()
    entity.value = entity_value
    entity.synonyms.extend(synonyms)

    response = entity_types_client.batch_create_entities(entity_type_path, [entity])

    print("Entity created: {}".format(response))
