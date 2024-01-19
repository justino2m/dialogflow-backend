import click
import dialogflow_v2 as df

# from .config import get_project_id
from .base import entities, _get_entity_type_ids

PROJECT_ID = "test-county"


@entities.group()
def types():
    pass


@types.command()
def list():
    entity_types_client = df.EntityTypesClient()
    parent = entity_types_client.project_agent_path(PROJECT_ID)

    entity_types = entity_types_client.list_entity_types(parent)

    for entity_type in entity_types:
        print("Entity type name: {}".format(entity_type.name))
        print("Entity type display name: {}".format(entity_type.display_name))
        print("Number of entities: {}\n".format(len(entity_type.entities)))


@types.command()
@click.argument("display-name")
@click.option(
    "kind",
    "-k",
    default="KIND_MAP",
    help="Type of entitiy KIND_MAP (default) or KIND_LIST.",
)
def create(display_name, kind):
    """Create an entity type with the given display name."""

    entity_types_client = df.EntityTypesClient()

    parent = entity_types_client.project_agent_path(PROJECT_ID)
    entity_type = df.types.EntityType(display_name=display_name, kind=kind)

    response = entity_types_client.create_entity_type(parent, entity_type)

    print("Entity type created: \n{}".format(response))


@types.command()
@click.argument("entity_type_name")
def delete(entity_type_name):
    """Delete entity type with the given entity type name."""

    entity_types_client = df.EntityTypesClient()

    # entity_type_ids = _get_entity_type_ids(PROJECT_ID, entity_type_name)
    entity_type_id = _get_entity_type_ids(PROJECT_ID, entity_type_name)
    if entity_type_id is None:
        click.echo(f"No entity types found for {entity_type_name}")
        return

    entity_type_path = entity_types_client.entity_type_path(PROJECT_ID, entity_type_id)

    entity_types_client.delete_entity_type(entity_type_path)
