import json
import click

from .config import ENTITY_JSON_FILE, DS_KINDS
from src.utilities.datastore import retrieve_all_kind

# JSON structure will look like
# {
#     'Kind': {
#         entity-name: {
#             entity-data
#         }
#     }
# }


def download_entities():
    all_entities = {}
    for k in DS_KINDS:
        kind_data = retrieve_all_kind(k)
        all_entities[k] = kind_data
        print(f"Retrieved {len(kind_data)} {k} entities")

    with open(ENTITY_JSON_FILE, "w") as f:
        json.dump(all_entities, f, indent=3, sort_keys=True)
        print(f"Entities dumped to {ENTITY_JSON_FILE}")


@click.command()
def download():
    """Downloads datastore entities for kinds listed in scripts.config.
    The entities are then saved to a JSON file and can be edited/uploaded
    by running:
    `bot upload`
    """
    click.secho(f"Downloading entities from datastore", fg="cyan")
    download_entities()


if __name__ == "__main__":
    download()
