from google.cloud import datastore
import click

ds = datastore.Client()


@click.command()
@click.argument("kind")
@click.argument("old-property")
@click.argument("new-property")
def rename_entity_property(kind, old_property, new_property):
    query = ds.query(kind=kind)
    updated_entities = []
    for e in query.fetch():
        if not e.get(old_property):
            continue
        e[new_property] = e.pop(old_property)
        updated_entities.append(e)

    ds.put_multi(updated_entities)


if __name__ == "__main__":
    rename_entity_property()
