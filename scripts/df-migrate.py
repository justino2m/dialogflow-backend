def rename_intent_faq_parent():
    intents_client = df.IntentsClient()
    parent = intents_client.project_agent_path(Config.PROJECT_ID)
    contexts_client = df.ContextsClient()
    print(f"renaming intent FAQ-CDRA")
    intent_id = _get_intent_id(Config.PROJECT_ID, "FAQ-CDRA")

    intent_name = intents_client.intent_path(Config.PROJECT_ID, intent_id)
    old_intent = intents_client.get_intent(
        intent_name, intent_view=df.enums.IntentView.INTENT_VIEW_FULL
    )

    output_context = df.types.Context(
        name=contexts_client.context_path(Config.PROJECT_ID, "-", "FAQ-followup"),
        lifespan_count=1,
    )
    intent_output_contexts = [output_context]

    new_intent = df.types.Intent(
        display_name="FAQ",
        webhook_state=old_intent.webhook_state,
        training_phrases=old_intent.training_phrases,
        messages=old_intent.messages,
        output_contexts=[output_context],
        parameters=old_intent.parameters,
    )
    # update_mask = field_mask_pb2.FieldMask(paths=["display_name"])

    resp = intents_client.create_intent(parent, new_intent)

    print(resp)
    return new_intent.name, output_context.name


def rename_faq_intents():

    intents_client = df.IntentsClient()
    parent = intents_client.project_agent_path(Config.PROJECT_ID)
    targets = [
        "FAQ-CDRA-Followup-No",
        "FAQ-CDRA-Contact-No",
        "FAQ-CDRA-Followup-Yes",
        "FAQ-CDRA-Contact-Followup",
    ]

    parent_intent_name, input_context_name = rename_intent_faq_parent()
    for t in targets:
        print(f"renaming intent {t}")
        intent_id = _get_intent_id(Config.PROJECT_ID, t)
        if intent_id is None:
            continue

        intent_name = intents_client.intent_path(Config.PROJECT_ID, intent_id)
        old_intent = intents_client.get_intent(
            intent_name, intent_view=df.enums.IntentView.INTENT_VIEW_FULL
        )

        parent_intent_id = _get_intent_id(Config.PROJECT_ID, "FAQ")
        parent_intent = intents_client.get_intent(
            intent_name, intent_view=df.enums.IntentView.INTENT_VIEW_FULL
        )

        input_contexts = old_intent.input_context_names.extend(
            parent_intent.output_contexts
        )
        print()
        new_intent = df.types.Intent(
            display_name=t.replace("-CDRA", ""),
            webhook_state=old_intent.webhook_state,
            training_phrases=old_intent.training_phrases,
            messages=old_intent.messages,
            input_context_names=input_contexts,
            parameters=old_intent.parameters,
            parent_followup_intent_name=parent_intent.name,
            # root_followup_intent_name=parent_intent.name,
        )

        # update_mask = field_mask_pb2.FieldMask(paths=["display_name"])

        resp = intents_client.create_intent(
            parent, new_intent, intent_view=df.enums.IntentView.INTENT_VIEW_FULL
        )

        print(resp)
        print()


def list_intents():
    intents_client = df.IntentsClient()

    parent = intents_client.project_agent_path(Config.PROJECT_ID)

    intents = intents_client.list_intents(parent)

    for intent in intents:
        print("=" * 20)
        print("Intent name: {}".format(intent.name))
        print("Intent display_name: {}".format(intent.display_name))
        print("Action: {}\n".format(intent.action))
        print("Root followup intent: {}".format(intent.root_followup_intent_name))
        print("Parent followup intent: {}\n".format(intent.parent_followup_intent_name))

        print("Input contexts:")
        for input_context_name in intent.input_context_names:
            print("\tName: {}".format(input_context_name))

        print("Output contexts:")
        for output_context in intent.output_contexts:
            print("\tName: {}".format(output_context.name))


def delete_intent(intent_name=None):
    intents_client = df.IntentsClient()

    intent_id = _get_intent_id(Config.PROJECT_ID, "FAQ-Followup-No")

    intent_path = intents_client.intent_path(Config.PROJECT_ID, intent_id)

    intents_client.delete_intent(intent_path)
