# -*- coding: utf-8 -*-

# A virtual Assistant for testing County
from random import choice, sample
from datetime import datetime
from google.cloud import datastore
from flask import current_app
from flask_assistant import ask, tell, context_manager, event, request as fa_request


from . import assist, has_screen, from_alexa
from src.utilities.datastore import ds, save_missed_query_to_datastore, FAQ_KIND

PROMPTS = [
    "Anything else?",
    "Is there anything else I can help you with?",
    "Is there anything else I can help with?",
    "Anything else you need?",
    "Can I assist with anything else?",
]


def build_example_list(resp, filter_params=None):
    ds_query = ds.query(kind=FAQ_KIND)

    filter_dept, filter_cat = None, None

    if filter_params is not None:
        current_app.logger.info(f"Filtering FAQS by {filter_params}")
        filter_dept = filter_params.get("dept")
        filter_cat = filter_params.get("cat")

    if filter_dept:
        ds_query.add_filter("department", "=", filter_dept.upper())

    if filter_cat:
        ds_query.add_filter("category", "=", filter_cat.upper())

    faq_list = list(ds_query.fetch())

    approved_faqs = [f for f in faq_list if f.get("approved", False)]
    if current_app.config["ALLOW_UNAPPROVED"]:
        approved_faqs = faq_list
    sample_size = 4
    if len(approved_faqs) < 4:
        sample_size = len(approved_faqs)

    examples = sample(approved_faqs, sample_size)
    faq_list = resp.build_list("Example Topics")
    for entity in examples:
        if not entity["approved"]:
            entity["name"] += " (Unapproved)"
        entity_id = entity.id
        faq_list.add_item(title=entity["name"], key=entity["name"])

    context_manager.add("faq-selection", lifespan=1)
    return faq_list.suggest("FAQs", "Zoning")


@assist.action("Default Welcome Intent")
def welcome():
    speech = "Welcome to the Plasir County Chat Assistant! "
    payload = fa_request["originalDetectIntentRequest"].get("payload", {})
    filter_params = payload.get("filterParams")

    if has_screen() and not from_alexa():
        speech += "Take a look at some examples of what you can ask me or say FAQ to get a list of questions you can ask."
        display_text = speech.replace("Plasir", "testing")
        resp = ask(speech, display_text)
        return build_example_list(resp, filter_params)
    else:
        speech += (
            "I'm here to answer any questions you may have about our county resources."
        )
        speech += " How can I help?"
        return ask(speech)


@assist.action("WhoAreYou")
def who_are_you():
    speech = "I am the Plasir County Chat assistant. You can ask me things like 'What is my zoning', or 'How do I check the status of my application' "
    display_text = speech.replace("Plasir", "testing")
    return ask(speech, display_text=display_text).add_msg("How can I help you today?")


@assist.action("Default Fallback Intent")
def fallback():
    save_missed_query_to_datastore()

    responses = [
        "What was that?",
        "I didn't quite catch that.",
        "Sorry, I didn't get that. Can you rephrase?",
        "Sorry, what was that?",
        "I missed that, say that again?",
        "Sorry I missed what you said",
        "Sorry, I missed that. Mind rephrasing your question?",
        "I missed that, one more time?",
    ]

    return ask(choice(responses))


@assist.prompt_for("faq", FAQ_KIND)
def prompt_for_faq(faq):
    prompts = [
        "Sorry I'm still learning, can you rephrase your question?",
        "I didn't get that. Could you rephrase?",
        "Sorry, I missed that. Mind rephrasing your question?",
    ]

    return ask(choice(prompts))


@assist.action("thank-you")
def thanks():
    responses = [
        "No problem!",
        "Anytime",
        "My pleasure",
        "That's what I'm here for",
        "No problem",
        "Sure thing",
    ]
    for c in context_manager._cache:
        con = context_manager.get(c)
        con.lifespan = 0
    return event("prompt-end", pre_phrase=choice(responses))


# The following faq followup intents are invoked
# in response to the actions_intent_NO_INPUT event
# this means they will not be called when
# when user is on surface with screen,
# as only speaker surfaces will send that event


@assist.action("Prompt-End", mapping={"pre_phrase": "sys.any"})
def prompt_end(pre_phrase=None):
    if pre_phrase:
        return ask(pre_phrase).add_msg(choice(PROMPTS))
    return ask(choice(PROMPTS))


@assist.action("Prompt-End-End")
def end_conv():
    # shorter response if user not responding
    if fa_request["queryResult"]["queryText"] == "actions_intent_NO_INPUT":
        return tell("Goodbye!")

    speech = "Thanks for chatting with Plasir County"
    display_text = speech.replace("Plasir", "testing")
    return tell(speech, display_text)


@assist.action("Prompt-End-Continue")
def continue_conv():
    return ask("Ok, what else would you like to know?")


# may be able to use just context for correct
# option-select action, but simulator doesn't
# follow docs about using "key"
# so here we just check active contexts
# to determine which action to take


@assist.action("Option-Select")
def handle_option_selection():
    c = context_manager.get("actions_intent_option")
    c.lifespan = 0
    key = c.get("OPTION")
    synonym = c.get("text")

    if "contact-selection" in context_manager._cache:
        c = context_manager.get("contact-selection")
        c.lifespan = 0
        from src.assistant.contact import handle_contact_option_selection

        return handle_contact_option_selection(key)

    if "faq-category-selection" in context_manager._cache:
        c = context_manager.get("faq-category-selection")
        c.lifespan = 0
        from src.assistant.faq import category_questions

        return category_questions(key)

    if "faq-dept-selection" in context_manager._cache:

        c = context_manager.get("faq-dept-selection")
        c.lifespan = 0
        faq = c.get("faq")
        from src.assistant.faq import faq_answer

        return faq_answer(faq, department=key)

    if "faq-selection" in context_manager._cache:
        c = context_manager.get("faq-selection")
        c.lifespan = 0

        from src.assistant.faq import faq_answer

        return faq_answer(synonym, department=None, key=key)

    if "zoning-selection" in context_manager._cache:
        c = context_manager.get("zoning-selection")
        c.lifespan = 0
        from src.assistant.zoning import zoning_information

        return zoning_information(key)


# @assist.context("zoning-selection")
# @assist.action("Option-Select")
# def handle_zone_option_selection():
#     """Special intent to handle option selection when using Google Assistant

#     Intent needs to have the actions_intent_OPTION event,
#     which will be invoked when an item is selected.
#     The action func parses the option key and then calls
#     the corresponding action function for the selection
#     """

#     c = context_manager.get("actions_intent_option")
#     c.lifespan = 0
#     key = c.get("OPTION")
#     return zoning_information(key)

# @assist.context("contact-selection")
# @assist.action("Option-Select")
# def handle_contact_option_selection():
#     c = context_manager.get("actions_intent_option")
#     c.lifespan = 0
#     key = c.get("OPTION")

#     if key == "Call":
#         return handle_call_followup()

#     if key == "Email":
#         return handle_email_followup()

#     if key == "Directions":
#         return handle_map_followup()

#     if key == "Web":
#         return handle_web_followup()


# @assist.context("faq-category-selection")
# @assist.action("Option-Select")
# def handle_faq_category_option_selection():
#     c = context_manager.get("actions_intent_option")
#     c.lifespan = 0
#     key = c.get("OPTION")
#     return category_questions(key)


# @assist.context("faq-selection")
# @assist.action("Option-Select")
# def handle_faq_option_selection():
#     c = context_manager.get("actions_intent_option")
#     c.lifespan = 0
#     key = c.get("OPTION")
#     return faq_answer(key)
