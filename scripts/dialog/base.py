import click
import dialogflow_v2 as df

from scripts.config import PROJECT_ID


@click.group()
def dialogflow():
    pass


@dialogflow.group()
def entities():
    pass


# Helper to get entity_type_id from display name.
def _get_entity_type_ids(project_id, display_name):

    entity_types_client = df.EntityTypesClient()

    parent = entity_types_client.project_agent_path(project_id)
    entity_types = entity_types_client.list_entity_types(parent)
    entity_type_names = [
        entity_type.name
        for entity_type in entity_types
        if entity_type.display_name == display_name
    ]

    if len(entity_type_names) == 0:
        return

    if len(entity_type_names) > 1:
        prompt = """Which entity type?\n"""
        for i, e in enumerate(entity_type_names):
            prompt += f"[{i}]  {e}\n"

        prompt += "Please select an option (0-{i})"
        choice = input(prompt)

        entity_type_id = entity_type_names[int(choice)].split("/")[-1]
    else:
        entity_type_id = entity_type_names[0].split("/")[-1]

    return entity_type_id

    entity_type_ids = [
        entity_type_name.split("/")[-1] for entity_type_name in entity_type_names
    ]

    return entity_type_ids


from .entities import *
from .entity_types import *
