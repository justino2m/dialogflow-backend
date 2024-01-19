from flask import current_app
import dialogflow_v2 as df
from google.protobuf import field_mask_pb2

from src.settings import Config
from src.utilities.datastore import FAQ_KIND, ds


def upload_df_entity(entity_key, entity_dict):
    entity_types_client = df.EntityTypesClient()

    # Note: synonyms must be exactly [entity_value] if the
    # entity_type's kind is KIND_LIST
    entity_name = entity_dict["Name"]
    synonyms = set(entity_dict.get("synonyms", [entity_name.lower()]))
    synonyms.add(entity_name.lower())

    entity_type_id = _get_entity_type_id(Config.PROJECT_ID, FAQ_KIND)

    entity_type_path = entity_types_client.entity_type_path(
        Config.PROJECT_ID, entity_type_id
    )

    df_entities = []
    # adding all synonyms to entity entries
    # synonyms can then be matched via datastore
    for s in synonyms:
        entity = df.types.EntityType.Entity()
        entity.value = s.lower()
        entity.synonyms.append(s.lower())
        if entity not in df_entities:
            df_entities.append(entity)

    response = entity_types_client.batch_update_entities(
        entity_type_path, list(df_entities)
    )

    print(f"DF synonyms added for {entity_key}: {response}")


def delete_df_entities(faq_entity):
    entity_types_client = df.EntityTypesClient()

    entity_type_id = _get_entity_type_id(Config.PROJECT_ID, FAQ_KIND)
    entity_type_path = entity_types_client.entity_type_path(
        Config.PROJECT_ID, entity_type_id
    )

    df_entity_values = [faq_entity["Name"].lower()]

    # mark each synonym key for deletion
    syns = faq_entity.get("synonyms", [])
    for s in syns:
        # don't delete the synonym if belong
        # to multiple faqs
        syn_key = ds.key("Synonym", s.lower())
        syn_entity = ds.get(syn_key)
        if len(syn_entity["faq_keys"]) > 1:
            continue

        df_entity_values.append(s.lower())

    response = entity_types_client.batch_delete_entities(
        entity_type_path, df_entity_values
    )

    print(f"Dialogflow entities deleted for {faq_entity.key.name}: {response}")


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
        raise ValueError(f"Found multiple entity_type ids for {display_name}")
    else:
        entity_type_id = entity_type_names[0].split("/")[-1]

    return entity_type_id


def _get_intent_id(project_id, display_name):
    intents_client = df.IntentsClient()

    parent = intents_client.project_agent_path(project_id)
    intents = intents_client.list_intents(parent)
    intent_names = [
        intent.name for intent in intents if intent.display_name == display_name
    ]

    if len(intent_names) == 0:
        return

    if len(intent_names) > 1:
        raise ValueError(f"Found multiple intent ids for {display_name}")
    else:
        intent_id = intent_names[0].split("/")[-1]

    return intent_id

    intent_ids = [intent_name.split("/")[-1] for intent_name in intent_names]

    return intent_ids


def update_faq_intent_phrases(phrase, synonym):
    intents_client = df.IntentsClient()
    intent_id = _get_intent_id(Config.PROJECT_ID, "FAQ")
    intent_name = intents_client.intent_path(Config.PROJECT_ID, intent_id)
    intent = intents_client.get_intent(
        intent_name, intent_view=df.enums.IntentView.INTENT_VIEW_FULL
    )

    phrase, synonym = phrase.lower(), synonym.lower()

    if synonym not in phrase:
        return "synonym must contained within query", 422

    # replace synonym with specific chars to split and preserve order
    phrase = phrase.replace(synonym, f"**&&{synonym}&&**")

    # split the query into parts to annotate the synonym
    # keep && in phrase to know
    # which part gets annotated
    parts = []
    segments = phrase.split("**")
    current_app.logger.debug(f"phrase segments: {segments}")

    for p in segments:
        current_app.logger.debug(f"building part for {p}")

        if p[-2:] == "&&" and p[:2] == "&&":
            current_app.logger.debug(f"annotating '{synonym}' as faq entity")
            part = df.types.Intent.TrainingPhrase.Part(
                text=synonym, entity_type="@FAQ", alias="faq", user_defined=True
            )

        else:
            current_app.logger.debug(f"adding '{p}' as non-annotated part")
            part = df.types.Intent.TrainingPhrase.Part(text=p)

        parts.append(part)

    training_phrase = df.types.Intent.TrainingPhrase(parts=parts)
    current_app.logger.debug(f"Created traing phrase:\n{training_phrase}")

    intent.training_phrases.extend([training_phrase])

    update_mask = field_mask_pb2.FieldMask(paths=["training_phrases"])

    resp = intents_client.update_intent(
        intent, language_code="en", update_mask=update_mask
    )

    print(resp)


def delete_df_entity_synonyms(entity_key, syns_to_delete):
    current_app.logger.debug(f"Removing {syns_to_delete} from dialogflow")
    entity_types_client = df.EntityTypesClient()
    entity_type_id = _get_entity_type_id(Config.PROJECT_ID, FAQ_KIND)
    entity_type_path = entity_types_client.entity_type_path(
        Config.PROJECT_ID, entity_type_id
    )

    response = entity_types_client.batch_delete_entities(
        entity_type_path, syns_to_delete
    )

    current_app.logger.info(f"Deleted removed synonyms for {entity_key}: {response}")
