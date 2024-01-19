from random import choice
from flask import url_for, current_app
from flask_assistant import ask, tell, context_manager, event, request as fa_request
from . import assist, has_screen, has_web_browser, from_alexa, PLACEHOLDER_IMG
from src.assistant.basic import PROMPTS, prompt_for_faq
from src.assistant.contact import prompt_dept_for_contact
from src.utilities.datastore import (
    ds,
    save_missed_query_to_datastore,
    get_synonym_entity,
    get_faq_entity,
    FAQ_KIND,
)

from src.assistant.contact import (
    get_tel_url,
    get_email_url,
    get_map_url,
    build_call_context,
    build_email_context,
    build_directions_context,
)

from ast import literal_eval


@assist.action("Community-FAQ")
def faq_start():
    categories = [
        "General",
        "Planning",
        "Building",
        "Engineering",
        "Environmental",
        "Geographic Information Systems",
    ]
    if has_screen():
        speech = "Please select a category below for specific questions, or simply ask your question"
        resp = ask(speech)
        faq_list = resp.build_list("Frequently Asked Questions")
        for c in categories:
            faq_list.add_item(title=c, key=c, img_url=PLACEHOLDER_IMG)

        context_manager.add("faq-category-selection", lifespan=1)
        return faq_list.suggest("All FAQs")

    else:
        speech = "Go ahead and ask your question."
        # speech = "Which department does your question relate to?"
        # speech += " Planning, Building, or general"
        # speech += "Available departments "
        return ask(speech)


@assist.action("Community-FAQ-All")
def all_faq_questions():
    if not has_screen():
        return faq_start()
    ds_query = ds.query(kind=FAQ_KIND)
    if not current_app.config["ALLOW_UNAPPROVED"]:
        ds_query.add_filter("approved", "=", True)
    list_title = f"All Frequenctly Asked Questions"

    resp = ask("Select a question below or ask me something else")
    faq_list = resp.build_list(list_title)

    for entity in ds_query.fetch():
        if not entity["approved"]:
            entity["name"] += " (Unapproved)"
        faq_list.add_item(
            title=entity["name"], key=entity["name"], img_url=PLACEHOLDER_IMG
        )

    context_manager.add("faq-selection", lifespan=1)
    return faq_list


@assist.action("Community-FAQ-Category")
def category_questions(faq_category):
    if not has_screen():
        return faq_start()
    ds_query = ds.query(kind=FAQ_KIND, order=["name"])
    ds_query.add_filter("category", "=", faq_category.upper())
    list_title = f"{faq_category.title()} Questions"

    resp = ask("Select a question below or ask me something else")
    faq_list = resp.build_list(list_title)

    for entity in ds_query.fetch():
        faq_list.add_item(title=entity["name"], key=entity.id, img_url=PLACEHOLDER_IMG)

    context_manager.add("faq-selection", lifespan=1)
    return faq_list


def faq_answer_screen(faq_data):
    # when building the faq response the following must be kept in mind
    # cards can have one link/button
    # link out is supported only for verified URLs
    # if multiple  actions (call, email, web)
    # must use one button, and set up context to handle the others
    current_app.logger.debug("Building FAQ response for screen-capable platform")
    display_text = faq_data.get("speech", "Here's what I found")
    speech = display_text.replace("testing", "Plasir")  # for speech pronounciation
    resp = ask(speech, display_text=display_text)
    if current_app.config["ALLOW_UNAPPROVED"]:
        if not faq_data["approved"]:
            faq_data["name"] += " (Unapproved)"
        else:
            faq_data["name"] += " (Approved)"

    if faq_data.get("web"):
        title = faq_data.get("webtitle", "More Info")

        if title is None or title == "":
            title = "More Info"

        resp.card(
            title=faq_data["name"],
            text=faq_data["textresponse"],
            link=faq_data["web"],
            link_title=title,
        )
        faq_data.pop("web")

    elif faq_data.get("email"):
        resp.card(
            title=faq_data["name"],
            text=faq_data["textresponse"],
            link=get_email_url(faq_data["email"]),
            link_title="send email",
        )
        faq_data.pop("email")

    elif faq_data.get("call"):
        resp.card(
            title=faq_data["name"],
            text=faq_data["textresponse"],
            link=get_tel_url(faq_data["call"]),
            link_title="call",
        )
        faq_data.pop("call")

    elif faq_data.get("directions"):
        resp.card(
            title=faq_data["name"],
            text=faq_data["textresponse"],
            link=get_map_url(faq_data["directions"]),
            link_title="directions",
        )
        faq_data.pop("directions")

    # no button to include card/ build card with only text response
    else:
      resp.card(
        title=faq_data["name"],
        text=faq_data["textresponse"],
      )

    chips = faq_data.get("chips", [])

    # transform into array if string
    if chips == "":
        chips = []
    elif isinstance(chips, str):
        chips = literal_eval(chips)

    for c in chips:
        resp.suggest(c)

    # the following keys (email/call)
    # will only remain in faq_data if they weren't
    # used as the button link above

    if faq_data.get("call"):
        build_call_context(faq_data)
        resp.suggest("call")

    if faq_data.get("email"):
        build_email_context(faq_data)
        resp.suggest("email")

    if faq_data.get("directions"):
        build_directions_context(faq_data)
        resp.suggest("directions")

    if faq_data.get("linkout"):
        link_name = faq_data.get("linkouttitle", "More info")

        if link_name is None or link_name == "":
            link_name = "More Info"

        url = faq_data["linkout"]
        resp.link_out(link_name, url)
    return resp.add_msg(choice(PROMPTS), display_text="")


def faq_answer_voice(faq_data):
    current_app.logger.debug("Building FAQ response for voice platform")
    speech = faq_data.get("speech", "I'm sorry I couldn't find an answer for that")
    speech = speech.replace("testing", "Plasir")  # to fix pronounciation
    resp = ask(speech)

    chips = faq_data.get("chips", [])

    if chips == "":
        chips = []
    elif isinstance(chips, str):
        chips = literal_eval(chips)

    # include contact info prompt as suggestion
    # instead of an add-on msg to cut verbosity
    call, email = faq_data.get("call"), faq_data.get("email")
    directions = faq_data.get("directions")

    if any([call, email, directions]):
        current_app.logger.debug("Adding contact info to chips for voice")
        context = context_manager.add("voice-faq-contact", lifespan=1)
        context.set("faq_data", faq_data)
        chips.append("Contact Info")

    if chips:
        prompts = [
            " For more info, you can ask __chips__",
            # " For related information you can ask __chips__",
            # " You can ask __chips__ for more info",
            # " Ask __chips__ for more info",
        ]
        suggest_speech = choice(prompts)
        if len(chips) > 1:
            chips.insert(-1, "or")

        suggests = ", ".join(chips)
        suggest_speech = suggest_speech.replace("__chips__", suggests)
        resp.add_msg(suggest_speech)

    else:
        resp = resp.add_msg(choice(PROMPTS))

    return resp


def faq_answer_display(faq_data):
    current_app.logger.info("Building response for smart display platform")
    speech = faq_data.get("speech", "I'm sorry I couldn't find an answer for that")

    chips = faq_data.get("chips", [])

    if chips == "":
        chips = []
    elif isinstance(chips, str):
        chips = literal_eval(chips)

    # include contact info prompt as suggestion
    # instead of an add-on msg to cut verbosity
    call, email = faq_data.get("call"), faq_data.get("email")
    directions = faq_data.get("directions")

    if any([call, email, directions]):
        context = context_manager.add("voice-faq-contact", lifespan=1)
        context.set("faq_data", faq_data)
        chips.append("Contact Info")

    display_text = speech
    speech = speech.replace("testing", "Plasir")
    resp = ask(speech, display_text=display_text)
    for c in chips:
        resp.suggest(c)

    return resp.add_msg("Anything else?")


# CAPABILITY SPECIFIC RESPONSES

# Phone/Tablet/Web UI have screen and browser
# so can provide cards w/ btns and suggestions

# Smart Display have screen but no broswer
# so responses have speech and display text
# but don't render buttons/links
# They do render suggestion chips though
# so contact followup can use them

# Speakers dont have screen or browser
# So they only render speech response
# b/c no chips will be rendered, need to
# handle contact info via voice with followups


@assist.prompt_for("department", "FAQ")
def prompt_dept(faq, department):

    if faq is None or faq == "":
        current_app.logger.warning("No faq entity received, prompting for faq")
        save_missed_query_to_datastore()
        return prompt_for_faq(faq)

    syn_entities = get_synonym_entity(faq)
    if not syn_entities:
        return prompt_for_faq(faq)

    if len(syn_entities) > 1:
        resp = ask("Which department would you like the info for?")
        dept_list = resp.build_list("Select a Department")
        for syn_entity in syn_entities:
            dept_list.add_item(
                syn_entity.get("department"), syn_entity.get("department")
            )

        c = context_manager.add("faq-dept-selection", lifespan=1)
        c.set("faq", faq)
        return dept_list

    else:
        department = syn_entities[0].get("department")
        current_app.logger.debug("Cearing slot fill contexts")
        for name, context in context_manager._cache.items():
            if "dialog" in name:
                current_app.logger.debug(f"Setting department for {name} context")
                context.set("department", department)
                context.lifespan = 1

    if "contact" in fa_request["queryResult"]["queryText"]:
        return prompt_dept_for_contact(faq, department)

    else:
        current_app.logger.info(
            "Triggering faq-answer event with faq and department params"
        )
        return event("faq-answer", faq=faq, department=department)


@assist.action("FAQ")
def faq_answer(faq, department, key=None):
    current_app.logger.info(f"Triggered FAQ intent")

    # key will be the entity name, which
    # no longer matches the FAQs entity id/key type
    # so we need to fetch the FAQ from datastore
    # via the typical method of phrase -> syn -> FAQ
    if not isinstance(key, int):
        key = None

    if faq is None or faq == "":
        current_app.logger.warning("No faq entity received, prompting for faq")
        save_missed_query_to_datastore()
        return prompt_for_faq(faq)

    syn_entities = get_synonym_entity(faq)

    if not syn_entities and key is None:
        return prompt_for_faq(faq)

    # check if there are more than one synonyms
    if syn_entities and len(syn_entities) > 1:
        # department will be filled by prompt
        if department is None:
            return prompt_dept(faq, department)
        for syn_entity in syn_entities:
            if syn_entity.get("department") == department:
                faq_key = syn_entity.get("faqkey")
    else:
        # department slot will be None for
        # faqs w/ only one department
        if key is None:
            faq_key = syn_entities[0].get("faqkey")
        else:
            faq_key = key

    current_app.logger.info(f"Synonym maps to {faq_key}")
    faq_data = get_faq_entity(faq_key)
    if faq_data is None:
        return prompt_for_faq(faq)

    current_app.logger.debug(f"Retrieved FAQ entity data for {faq}")

    faq_summary = {
        "key": faq_key,
        "Name": faq_data.get("name"),
        "Category": faq_data.get("category"),
        "Department": faq_data.get("department"),
        "Email": faq_data.get("email"),
        "Call": faq_data.get("call"),
        "Directions": faq_data.get("directions"),
    }

    context = context_manager.add("faq-answer", lifespan=1)
    context.set("faq_data", faq_summary)
    context.set("department", faq_data.get("department"))
    context_manager.add("faq-followup", lifespan=1)

    if from_alexa():
        return faq_answer_voice(faq_data)

    # phone/tablet/web
    if has_screen() and has_web_browser():
        return faq_answer_screen(faq_data)

    # smart display
    elif has_screen():
        return faq_answer_display(faq_data)

    # speaker
    else:
        return faq_answer_voice(faq_data)


@assist.context("faq-followup")
@assist.action("FAQ-Followup-Yes")
def no_faq_followup():
    return ask("Go ahead and ask your question, I'm listening")


@assist.context("faq-followup")
@assist.action("FAQ-Followup-No")
def no_faq_followup():
    speech = "Ok, thanks for chatting with Plasir County"
    display_text = speech.replace("Plasir", "testing")
    return tell(speech, display_text)


@assist.action("Minimum-Depth-Requirement")
def depth_requirement(PipeType):
    speech = "The minimum depth requirement is "
    if PipeType in ["sewer", "iron", "water"]:
        speech += "12 inches of cover measured from the top of the pipe."
    elif PipeType in ["poly", "electrical"]:
        speech += "18 inches of cover measured from the top of the pipe"
    else:
        speech = (
            f"I'm sorry I couldn't find the requirements for a {PipeType} pipe line"
        )
    context_manager.add("faq-followup", lifespan=1)
    resp = ask(speech)
    resp.add_msg(choice(PROMPTS), display_text="")
    return resp


@assist.prompt_for("PipeType", "Minimum-Depth-Requirement")
def prompt_for_pipe_type(PipeType):
    return ask('What kind of pipe or line? For example, "sewer" or "electrical"')


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

