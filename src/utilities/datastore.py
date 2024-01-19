from flask import current_app
from flask_assistant import request as fa_request
from google.cloud import datastore
from datetime import datetime

ds = datastore.Client()
FAQ_KIND = "FAQs"


def retrieve_all_kind(kind):
    kind_data = {}
    query = ds.query(kind=kind)
    for entity in query.fetch():
        e_data = {}
        # we use a name for entity key, not generated ID
        entity_id = entity.key.id_or_name
        for k, v in entity.items():
            e_data[k] = v
            kind_data[entity_id] = e_data

    return kind_data


def build_entity_data(data):
    entity_dict = {}
    entity_key = None
    entity_dept = data["Department"]

    entity_key = data.pop("key")

    for k, v in data.items():
        if v is not None and v != "" and v != []:
            entity_dict[k] = v

    if entity_dict.get("synonyms") is None:
        entity_dict["synonyms"] = [entity_dict["Name"]]

    return entity_key, entity_dict


def upload_ds_entity(entity_key, entity_dict):
    ent_dept = entity_dict["Department"]
    current_app.logger.info(f"Uploading {entity_key} entity to datastore")
    key = ds.key(FAQ_KIND, entity_key)
    entity = datastore.Entity(key=key)
    entity.update(entity_dict)
    ds.put(entity)

    syn_entities = []
    syn_keys = []
    for s in entity_dict.get("synonyms", [entity_dict["Name"].lower()]):
        syn_key = ds.key("Synonym", s.lower())
        if syn_key in syn_keys:
            continue
        syn_keys.append(syn_key)

        syn_entity = ds.get(syn_key)
        if syn_entity is None:
            syn_entity = datastore.Entity(key=syn_key)

        if syn_entity.get("faq_keys") is None:
            syn_entity["faq_keys"] = {}
        syn_entity["faq_keys"][ent_dept] = entity_key
        syn_entities.append(syn_entity)

    ds.put_multi(syn_entities)


def delete_ds_entities(faq_entity):
    current_app.logger.info(
        f"Deleting {faq_entity.key.name} entity and synonyms from datastore"
    )
    to_delete_keys = [faq_entity.key]

    # mark each synonym key for deletion
    syns = faq_entity.get("synonyms", [])
    syn_keys = []
    for s in syns:
        syn_key = ds.key("Synonym", s.lower())
        syn_entity = ds.get(syn_key)

        # don't delete the synonym if belong
        # to multiple faqs
        if len(syn_entity["faq_keys"]) > 1:
            syn_entity["faq_keys"].pop(faq_entity["Department"])
            ds.put(syn_entity)

        else:
            syn_keys.append(syn_key)

    to_delete_keys.extend(syn_keys)

    ds.delete_multi(to_delete_keys)


def delete_removed_synonyms(entity_key, entity_dict):
    key = ds.key(FAQ_KIND, entity_key)
    current_entity = ds.get(key)
    if current_entity is None:
        return
    current_syn_list = current_entity.get("synonyms", [])
    new_syn_list = entity_dict.get("synonyms", [])
    syns_to_delete = []
    for s in current_syn_list:
        if s not in new_syn_list:
            syns_to_delete.append(s)

    if len(syns_to_delete) == 0:
        return

    current_app.logger.debug(f"Admin removed synonyms: {syns_to_delete}")

    # avoid circular import
    from src.utilities.dialogflow import delete_df_entity_synonyms

    delete_df_entity_synonyms(entity_key, syns_to_delete)

    current_app.logger.debug(f"Removing {syns_to_delete} from datastore")
    syn_keys = []
    for s in syns_to_delete:
        key = ds.key("Synonym", s)
        syn_keys.append(key)

    ds.delete_multi(syn_keys)
    current_app.logger.debug(f"Deleted {syns_to_delete} from datastore")

    return syns_to_delete


def save_missed_query_to_datastore(query=None):
    if query is None:
        query = fa_request["queryResult"]["queryText"]

    intent_request = fa_request.get("originalDetectIntentRequest", {})
    platform_source = intent_request.get("payload", {}).get("source")

    current_app.logger.info("Saving missed query to datastore")
    ds_query = ds.query(kind="UnansweredQueries")
    ds_query.add_filter("query", "=", query)
    ds_query.add_filter("platform", "=", platform_source)
    results = list(ds_query.fetch(limit=1))

    dt = datetime.utcnow()

    if len(results) > 0:
        query_id = results[0].id
        key = ds.key("UnansweredQueries", query_id)
        count = results[0]["count"] + 1
    else:
        key = ds.key("UnansweredQueries")
        count = 1

    entity = datastore.Entity(key)
    entity.update(
        {
            "query": query,
            "created": dt,
            "modified": dt,
            "createdby": "SYSTEM",
            "modifiedby": "SYSTEM",
            "resolved": False,
            "count": count,
            "platform": platform_source,
            "department": []
        }
    )
    ds.put(entity)
    current_app.logger.info("Saved query to datastore")


def get_synonym_entity(syn_phrase):
    current_app.logger.debug(f"Getting synonym entity for {syn_phrase}")
    ds_query = ds.query(kind="Synonyms")
    ds_query.add_filter("value", "=", syn_phrase.strip().lower())
    results = list(ds_query.fetch())

    if results is None:
        current_app.logger.error(
            f"Could not find synonym entity for {syn_phrase.strip().lower()}"
        )
        save_missed_query_to_datastore()

    return results


def get_faq_entity(faq_key):
    current_app.logger.info("fetching FAQ entity")
    faq_key = ds.key(FAQ_KIND, int(faq_key))
    faq_data = ds.get(faq_key)
    if not current_app.config["ALLOW_UNAPPROVED"]:
        if not faq_data.get("approved", False):
            current_app.logger.info(f"Matched FAQ {faq_key.id_or_name} is not approved")
            return None
        else:
            current_app.logger.debug("FAQ is approved")
    if faq_data is None:
        current_app.logger.error(f"No Faq entity found for {faq_key}")
        save_missed_query_to_datastore()
    return faq_data


def get_staff_entity(staff):
    current_app.logger.info("fetching staff entity")
    ds_query = ds.query(kind="StaffDirectory")
    ds_query.add_filter("code", "=", staff)
    return list(ds_query.fetch())

