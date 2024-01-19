# -*- coding: utf-8 -*-
"""The assistant module"""

import logging
import json
from flask import Blueprint, Response, request, current_app
from flask_assistant import Assistant, request as fa_request

from src.settings import Config
from src.utilities.datastore import ds

blueprint = Blueprint("assist", __name__, url_prefix="/assist")
assist = Assistant(blueprint=blueprint, project_id=Config.PROJECT_ID)

PLACEHOLDER_IMG = "https://www.testing.ca.gov/images/2015/pc-seal-color-web.png"


@blueprint.before_request
def verify_auth():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        current_app.logger.info("Unauthorized Request")
        return Response(
            "Invalid login", 401, {"WWW-Authenticate": 'Basic realm="Login Required"'}
        )


def check_auth(username, password):
    creds_key = ds.key("Credentials", "WebhookCredentials")
    creds_entity = ds.get(creds_key)

    uname = creds_entity["username"]
    pwd = creds_entity["password"]

    return username == uname and password == pwd


def from_google():
    source = fa_request["originalDetectIntentRequest"].get("source")
    return source == "google"


def from_alexa():
    payload = fa_request["originalDetectIntentRequest"].get("payload", {})
    source = payload.get("source")
    result = source == "alexa"
    if result:
        current_app.logger.debug("Request from alexa")
    return result


def capabilities():
    if from_google():
        surface = fa_request["originalDetectIntentRequest"]["payload"]["surface"]
        return surface.get("capabilities", [])


def has_audio():
    if from_google():
        return {"name": "actions.capability.AUDIO_OUTPUT"} in capabilities()
    else:
        return True


def has_screen():
    if from_google():
        return {"name": "actions.capability.SCREEN_OUTPUT"} in capabilities()
    elif from_alexa():
        alexa_payload = fa_request["originalDetectIntentRequest"]["payload"]
        result = alexa_payload.get("alexaHasDisplay")
        if result:
            current_app.logger.debug("Alexa device has screen")
        return result
    else:
        return True


def has_web_browser():
    if from_google():
        return {"name": "actions.capability.WEB_BROWSER"} in capabilities()
    elif from_alexa():
        return False
    else:
        return True


# need to import action functions after assist created
# so they views can be registered
from . import zoning, faq, basic, contact, staff
