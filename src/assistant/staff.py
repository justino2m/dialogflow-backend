from random import choice
from flask import url_for, current_app
from flask_assistant import ask, tell, context_manager, event, request as fa_request
from . import assist, has_screen, has_web_browser, from_alexa, PLACEHOLDER_IMG
from src.assistant.basic import PROMPTS
from src.utilities.datastore import (
    ds,
    get_staff_entity
)

@assist.prompt_for("staff", "Staff")
def prompt_staff(staff):
    if staff is None or staff == "":
        return ask("What is the name of the staff member you are searching for?")
    return staff_start(staff)

@assist.action("Staff")
def staff_start(staff):
    if staff is None or staff == "":
        return prompt_staff(staff)
    staff = get_staff_entity(staff)

    if(staff is None):
         return staff_not_found()
    
    resp = ask(staff[0].get("speech"))
    
    if has_screen():
        resp.card(
            title = staff[0].get("title"),
            text = staff[0].get("text"),
            img_url=staff[0].get("img_url"),
            subtitle=staff[0].get("full_name"),
        )

    resp.add_msg(choice(PROMPTS), display_text="")
    context_manager.add("faq-followup", lifespan = 1)
    return resp
    
def staff_not_found():
    resp = ask("I am sorry I couldn't find the staff member in our system")
    resp.add_msg(choice(PROMPTS), display_text="")
    context_manager.add("faq-followup", lifespan = 1)
    return resp  