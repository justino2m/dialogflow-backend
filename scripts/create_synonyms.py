# This script is only used to create a set of synonym entities
# for already defined FaqCDRAs. So this should not be run often,
# Usually only for the first time when creating the Synonym Kind

# However this can be run at any time to make sure
# all synonyms defined in an Faq entities "synonyms" property
# have been added to both the DS Synonym kind and as dialogflow entries
# This usually won't be necessary because they are added automatically
# when creating an FAQ from the admin UI

# We are migrating our synonym definitions and usage from diaslogflows NLP
# to a datastore lookup in the webhook

# This way we can allow automated expansion of dialogflow entities
# and then get the correct Faq entitiy in the webhook by first
# querying the Synonym Kind for the received querytext parameter
# We then use that synyonym key to find the corresponding FAQ

from google.cloud import datastore
import dialogflow_v2 as df
import click
from src.settings import Config
from src.utilities.datastore import ds, FAQ_KIND


def ds_create_syn_entities_from_faq(faq_entity):
    # print(f"Grabbing synonyms for {faq_entity.key.name}")
    faq_syn_entities = []
    faq_dept = faq_entity.get("Department")

    # first add the actualy faq entity name as a synonym for direct match
    self_synonym_key = ds.key("Synonym", faq_entity["Name"].lower().strip())

    # self_synonym_entity = ds.get(self_synonym_key)
    # if self_synonym_entity is None:
    self_synonym_entity = datastore.Entity(key=self_synonym_key)

    if self_synonym_entity.get("faq_keys") is None:
        self_synonym_entity["faq_keys"] = {}

    self_synonym_entity["faq_keys"][faq_dept] = faq_entity.key.name
    faq_syn_entities.append(self_synonym_entity)

    # now we create a new key and entity for each
    # Faq's defined synonyms and set the faq_key property to the FAQ
    defined_synonyms = faq_entity["synonyms"]
    if not defined_synonyms or defined_synonyms == "":
        return []

    syn_keys = [self_synonym_key]
    for s in defined_synonyms:
        key = ds.key("Synonym", s.lower())
        if key in syn_keys:
            print(f"Skipping DUPLICATE KEY: {key}")
            continue

        syn_keys.append(key)  # track for duplicates

        syn_entity = ds.get(key)
        if syn_entity is None:
            syn_entity = datastore.Entity(key=key)

        if syn_entity.get("faq_keys") is None:
            syn_entity["faq_keys"] = {}

        syn_entity["faq_keys"][faq_dept] = faq_entity.key.name
        faq_syn_entities.append(syn_entity)

    return faq_syn_entities


def df_create_syn_entities_from_faq(faq_entity):
    # Note: synonyms must be exactly [entity_value] if the
    # entity_type's kind is KIND_LIST

    clean_name = faq_entity["Name"].replace("(", "").replace(")", "")

    synonyms = set(faq_entity.get("synonyms", [clean_name.lower()]))
    synonyms.add(clean_name.lower())

    df_entities = []
    # adding all synonyms to entity entries
    # synonyms can then be matched via datastore
    for s in synonyms:
        entity = df.types.EntityType.Entity()
        entity.value = s.lower().replace("(", "").replace(")", "")
        entity.synonyms.append(s.lower().replace("(", "").replace(")", ""))
        if entity not in df_entities:
            df_entities.append(entity)

    return df_entities


def ds_upload_syn_entities(ds_syn_entities):
    print("Putting synonyms in chunks of 400")

    for i in range(0, len(ds_syn_entities), 400):
        print(f"Putting {i} through {i+400}")
        ds.put_multi(ds_syn_entities[i : i + 400])

    print("Datastore entities created")


def df_upload_syn_entities(df_syn_entities):
    entity_types_client = df.EntityTypesClient()
    entity_type_id = _get_entity_type_id(Config.PROJECT_ID, FAQ_KIND)

    entity_type_path = entity_types_client.entity_type_path(
        Config.PROJECT_ID, entity_type_id
    )

    # entity.synonyms.extend(synonyms)
    response = entity_types_client.batch_update_entities(
        entity_type_path, list(df_syn_entities)
    )

    print(f"Dialogflow Entities created: {response}")


def _get_entity_type_id(project_id, display_name):

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
        raise ValueError("Could not find entity_type id")
    else:
        entity_type_id = entity_type_names[0].split("/")[-1]

    return entity_type_id


@click.command()
@click.argument("env", default="staging")
def create_all_synonyms(env):
    """
    Syncs FAQ synonym properties with Synonym Kind and Dialogflow
    Fetches all FAQ kind entities from datastore and
    creates new Synonym kind enties and dialogflow entity ENTRIES
    based of an FAQ kind's synonyms property

    This essentially allows you to quickly sync then
    Synyonym Kinds (used in webhook) and
    Dialogflow entries with any updated FAQ entities
    """
    print("About to fetch faqs")
    query = ds.query(kind=FAQ_KIND)
    ds_syn_entities = []
    df_syn_entities = []
    for f in query.fetch():
        df_faq_syns = df_create_syn_entities_from_faq(f)
        ds_faq_syns = ds_create_syn_entities_from_faq(f)

        ds_syn_entities.extend(ds_faq_syns)
        df_syn_entities.extend(df_faq_syns)

    ds_upload_syn_entities(ds_syn_entities)
    df_upload_syn_entities(df_syn_entities)


if __name__ == "__main__":
    create_all_synonyms()
