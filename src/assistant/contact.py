from random import choice
from flask import url_for, current_app
from flask_assistant import ask, context_manager, event, tell
from . import assist, has_screen
from src.utilities.datastore import (
    save_missed_query_to_datastore,
    get_synonym_entity,
    get_faq_entity,
)
from src.assistant.basic import prompt_for_faq, PROMPTS


def build_call_context(faq_data):
    url = get_tel_url(faq_data["call"])

    context_manager.add(
        name="call",
        lifespan=1,
        parameters={
            "call": url,
            "text": "You may click below to start the call. Please note that the call will be made using your default Phone app and carrier charges may apply.",
            "faq_data": faq_data,
        },
    )


def build_email_context(faq_data):
    url = get_email_url(faq_data["email"])

    context_manager.add(
        name="email",
        lifespan=1,
        parameters={"email": url, "text": "You may click below to send an email"},
    )


def build_directions_context(faq_data):
    address = faq_data["directions"]
    url = get_map_url(address)

    context_manager.add(
        name="directions",
        lifespan=1,
        parameters={
            "directions": url,
            "text": "You may click below to get directions",
            "address": address,
        },
    )


def build_web_context(faq_data):
    url, title = faq_data["web"], faq_data.get("webtitle", "View Online")

    if title is None or title == "":
        title = "View Online"

    context_manager.add(
        name="web",
        lifespan=1,
        parameters={
            "url": url,
            "text": "You may click below to visit online",
            "title": title,
            "faq_data": faq_data,
        },
    )


# @assist.context("call")
@assist.action("Call")
def handle_call_followup():
    tel_url = context_manager.get_param("call", "call")
    tel_text = context_manager.get_param("call", "text")
    faq_data = context_manager.get_param("call", "faq_data")
    resp = tell(tel_text)

    resp.card(
        text=tel_text,
        title=f"Phone Info for {faq_data['name']}",
        link_title="Call",
        link=tel_url,
        # img_url=PLACEHOLDER_IMG,
    )
    return resp.add_msg(choice(PROMPTS))


# @assist.context("email")
@assist.action("Email")
def handle_email_followup():
    email_url = context_manager.get_param("email", "email")
    email_text = context_manager.get_param("email", "text")
    resp = tell(email_text)
    resp.card(
        text=email_text,
        title="Email Info",
        link_title="Email",
        link=email_url,
        # img_url=PLACEHOLDER_IMG,
    )
    return resp.add_msg(choice(PROMPTS))


# @assist.context("directions")
@assist.action("Directions")
def handle_map_followup():
    map_url = context_manager.get_param("directions", "directions")
    map_text = context_manager.get_param("directions", "text")
    map_address = context_manager.get_param("directions", "address")
    resp = tell(map_text)
    resp.card(
        text=map_text,
        title=f"Directions to {map_address}",
        link_title="Open Maps",
        link=map_url,
        # img_url=PLACEHOLDER_IMG,
    )
    return resp.add_msg(choice(PROMPTS))


# @assist.context('web')
@assist.action("Web")
def handle_web_followup():

    web_title = context_manager.get_param("web", "title")
    if web_title is None or web_title == "":
        web_title = "Link"

    text = context_manager.get_param("web", "text")
    faq = context_manager.get_param("web", "faq_data")
    resp = tell(f"Click the link below to view more info about {faq['name']}")

    card_title = f"{faq['name']} Website"
    resp.card(text, title=card_title, link=faq["web"], link_title=web_title)

    if faq.get("linkout"):
        resp.link_out(faq["linkouttitle"], faq["linkout"])

    return resp.add_msg(choice(PROMPTS))


def get_tel_url(number):
    tel_url = "tel:" + number
    return url_for("web.redirect_call", tel_url=tel_url, _external=True)


def get_email_url(email):
    return "https://mail.google.com/mail/?view=cm&fs=1&to=" + email


def get_map_url(address):
    return "https://www.google.com/maps/dir/?api=1&destination=" + address


def ssml_email(email):
    user, domain = email.split("@")

    user_ssml = f"<say-as interpret-as='characters'>{user}@</say-as>"

    if "testing" in domain.lower():
        domain = domain.split("testing")[1]
        end_domain_ssml = f"<say-as interpret-as='characters'>{domain}</say-as>"

        ssml_resp = user_ssml + "plasir" + end_domain_ssml

    else:
        end_domain_ssml = f"<say-as interpret-as='characters'>{domain}</say-as>"
        ssml_resp = user_ssml + end_domain_ssml

    return ssml_resp


def contact_info_screen_response(faq_data):
    name = faq_data.get("contactname") or faq_data.get("name")
    call, email, directions, web = (
        faq_data.get("call"),
        faq_data.get("email"),
        faq_data.get("directions"),
        faq_data.get("web"),
    )

    contact_options = [c for c in [call, email, directions, web] if c]

    if len(contact_options) == 0:
        return ask(
            f"I'm afraid I don't have any contact information for {name}. Can I help with anything else?"
        )

    # list responses must have at least 2 items
    # skip list building and just show the one contact option
    if len(contact_options) == 1:
        contact = contact_options[0]
        if contact == web:
            build_web_context(faq_data)
            return handle_web_followup()

        if contact == call:
            build_call_context(faq_data)
            return handle_call_followup()

        if contact == email:
            build_email_context(faq_data)
            return handle_email_followup()

        if contact == directions:
            build_directions_context(faq_data)
            return handle_map_followup()

    speech = f"You can find contact info for {name} in the items below"
    resp = ask(speech)
    contact_list = resp.build_list(f"{name} Contact Info")

    if call:
        build_call_context(faq_data)
        syns = ["phone", "make a call", "telephone"]
        contact_list.add_item(
            title="Phone", key="Call", synonyms=syns, description=call
        )

    if email:
        build_email_context(faq_data)
        syns = ["send email"]
        contact_list.add_item(
            title="Email", key="Email", synonyms=syns, description=email
        )

    if directions:
        build_directions_context(faq_data)
        syns = ["map", "maps", "get directions", "address"]
        contact_list.add_item(
            title="Directions", key="Directions", synonyms=syns, description=directions
        )

    if web:
        build_web_context(faq_data)
        syns = ["website", "online", "web page", "web"]
        contact_list.add_item(
            title="Website", key="Web", synonyms=syns, description=web
        )

    context_manager.add("contact-selection", lifespan=1)

    return contact_list


def contact_info_voice_response(faq_data):
    name = faq_data.get("contactname") or faq_data.get("name")
    call, email, directions, web = (
        faq_data.get("call"),
        faq_data.get("email"),
        faq_data.get("directions"),
        faq_data.get("web"),
    )

    if not any([call, email, directions]):
        speech = f"I'm afraid I don't have any contact information for {name}. "
        if web:
            speech += f"However, you can find more information online at {web}."

        speech += " Can I help with anything else?"
        return ask(speech)

    speech = f"To contact us about {name} "

    # ensure testing is lowercase in emails
    # to prevent replacing to "Plasir"
    if email:
        email = email.lower()

    # format speech for contact
    if call or email:
        speech += f"you can reach us"
        if call and email:
            speech += f" by phone at {call} or by email at {ssml_email(email)}."
        elif call:
            speech += f" by phone at {call}."
        elif email:
            speech += f" by email at {ssml_email(email)}."

        if directions:
            speech += f" Or you can visit in person by going to {directions}"

    elif directions:
        speech = f"You can visit in person by going to {directions}"

    display_text = speech
    if email and has_screen():
        display_text = speech.replace(ssml_email(email), email)

    speech = speech.replace("testing", "Plasir")
    return ask(speech, display_text=display_text, is_ssml=True)


@assist.context("voice-faq-contact")
@assist.action("FAQ-Contact-No")
def faq_no_contact():
    return event("prompt-end")


@assist.context("voice-faq-contact")
@assist.action("FAQ-Contact-Followup")
def faq_contact_info():
    current_app.logger.debug("Invoked contact followup on voice platform")
    data = context_manager.get_param("voice-faq-contact", "faq_data")
    return contact_info_voice_response(data)


# Contact-Info intent is used to directly
# get contact info, instead of an answer
# as apposed to the FAQ-Contact-Followup intent
# which provides contact info for voice-only
# after an answer is provided


@assist.prompt_for("department", "Contact-Info")
def prompt_dept_for_contact(faq, department):

    if faq is None or faq == "":
        current_app.logger.warning("No faq entity received, prompting for faq")
        save_missed_query_to_datastore()
        return prompt_for_faq(faq)

    syn_entities = get_synonym_entity(faq)
    if not syn_entities:
        return prompt_for_faq(faq)

    if len(syn_entities) > 1:
        resp = ask("Which department would you like the contact info for?")
        dept_list = resp.build_list("Select a Department")
        for syn_entity in syn_entities:
            dept_list.add_item(syn_entity.get("department"), syn_entity.get("department"))

        return dept_list

    else:
        department = syn_entities[0].get("department")
        current_app.logger.debug("Cearing slot fill contexts")
        for name, context in context_manager._cache.items():
            if "dialog" in name:
                current_app.logger.debug(f"Setting department for {name} context")
                context.set("department", department)
                context.lifespan = 1

        current_app.logger.info(
            "Triggering contact-info event with faq and department params"
        )
        return event("contact-info", faq=faq, department=department)


@assist.action("Contact-Info")
def contact_for_faq(faq, department):
    c = context_manager.get("faq-selection")
    if c is not None:
        c.lifespan = 0

    if faq is None or faq == "":
        current_app.logger.warning("No faq entity received, prompting for faq")
        save_missed_query_to_datastore()
        return prompt_for_faq(faq)

    syn_entities = get_synonym_entity(faq)
    if not syn_entities:
        return prompt_for_faq(faq)

    if len(syn_entities) > 1:
        # department will be filled by prompt
        if department is None: 
            return prompt_dept_for_contact(faq, department)
        for syn_entity in syn_entities:
            if syn_entity.get("department") == department:
                faq_key = syn_entity.get("faqkey")
    else:
        # department slot will be None for
        # faqs w/ only one department
        faq_key = syn_entities[0].get("faqkey")

    current_app.logger.info(f"Synonym maps to {faq_key}")
    faq_data = get_faq_entity(faq_key)
    if faq_data is None:
        return prompt_for_faq(faq)

    if not has_screen():
        return contact_info_voice_response(faq_data)
    return contact_info_screen_response(faq_data)


def handle_contact_option_selection(key):
    c = context_manager.get("actions_intent_option")
    c.lifespan = 0
    key = c.get("OPTION")

    if key == "Call":
        return handle_call_followup()

    if key == "Email":
        return handle_email_followup()

    if key == "Directions":
        return handle_map_followup()

    if key == "Web":
        return handle_web_followup()
