from flask import current_app
from flask_assistant import ask, context_manager, event
from . import assist, has_screen, PLACEHOLDER_IMG
from src.utilities.datastore import ds
from src.utilities.testing_gis import (
    get_zoning,
    get_jurisdiction,
    UNINCORPORATED,
    WITHIN_JURISDICTION,
    OUTSIDE_JURISDICTION,
)


@assist.action("Zoning")
def zoning_start():
    if has_screen():
        return zoning_start_screen()
    else:
        return zoning_start_voice()


def zoning_start_screen():
    speech = "What kind of zoning information would you like?"
    card_text = "Click the link below for general information on testing Zoning Ordinances.\nYou can also get the zoning info for your address or a list of zoning codes"
    resp = ask(speech).card(
        title="Zoning Ordinances",
        text=card_text,
        link="https://www.testing.ca.gov/departments/communitydevelopment/planning/pchearings",
        link_title="General Info",
    )
    return resp.suggest("What is my zoning", "Zoning Definitions")


def zoning_start_voice():
    speech = """
    Please say the name of the zoning district you would like to learn about or ask
    'What is my zoning' to find the zoning code of a specific address."""
    context_manager.add("zoning-selection", lifespan=1)
    context_manager.add("Zoning-Overview-followup")
    return ask(speech)


@assist.action("Zoning-Overview")
def zoning_info_start():
    if not has_screen():
        return zoning_start_voice()
    ds_query = ds.query(kind="ZoningCode")

    speech = "Please select a zone for more information"
    resp = ask(speech)
    zone_list = resp.build_list("testing Zoning Codes")
    for entity in ds_query.fetch():
        display = f"{entity['displayName']} ({entity['code']})"
        zone_list.add_item(display, key=entity["code"])

    context_manager.add("zoning-selection", lifespan=2)
    return zone_list.suggest("Find my zoning")


@assist.action("Zoning-Code-Info", mapping={"zoning_code": "ZoningCode"})
def zoning_information(zoning_code):
    if has_screen():
        return zoning_info_screen(zoning_code)
    else:
        return zoning_info_voice(zoning_code)


def zoning_info_screen(zoning_code):
    zone_key = ds.key("ZoningCode", zoning_code)
    zone_data = ds.get(zone_key)

    resp = ask("Here's the zoning information")
    resp.card(
        text=zone_data["description"],
        title=zone_data["displayName"],
        link=zone_data["url"].replace("http", "https"),
        link_title="More info",
    )
    context_manager.add("Zoning-Code-Info-followup", lifespan=1)
    return resp.add_msg("Would you like to learn about another zoning district?")


def zoning_info_voice(zoning_code):
    zone_key = ds.key("ZoningCode", zoning_code)
    zone_data = ds.get(zone_key)

    return ask(zone_data["description"]).add_msg(
        "Would you like to hear about another zoning district?"
    )


@assist.action("Zoning-Code-Info-Another-Yes")
def zoning_info_voice_followup_yes():
    return zoning_start_voice()


@assist.action("Zoning-Code-Info-Another-No")
def zoning_info_voice_followup_no():
    return event("prompt-end")


def contains_digits(string):
    return any([c.isdigit() for c in string])


@assist.action("Zoning-by-address", mapping={"location": "sys.location"})
def zoning_by_address(location):
    if location is None or location == "":
        return prompt_address(location)

    address = location.get("street-address")
    if address is None:
        return prompt_address(location)

    if not contains_digits(address):
        context_manager.add(
            "zoning-by-address_dialog_params_location",
            parameters={"street_name": address},
            lifespan=1,
        )
        return ask(
            "For accurate zoning information, I'll need the full street address, including the house number."
        )

    # search requires road abbreviations
    address = (
        address.lower()
        .replace("road", "rd")
        .replace("drive", "dr")
        .replace("boulevard", "blvd")
        .replace("circle", "cir")
        .replace("court", "ct")
    )

    try:
        status, zoning_info = get_zoning(address)
        current_app.logger.info("Retrieved zoning info:")
        current_app.logger.info(zoning_info)
    except Exception:
        return ask(
            "I'm sorry, I'm unable to look up zoning information at the moment. Please try again in a few minutes."
        )
    current_app.logger.debug(f"jurisdiction status: {status}")

    if status == OUTSIDE_JURISDICTION:
        speech = f"I was unable to find zoning information for {location['street-address']} because it appears to be outside of Plasir jurisdiction"
        display_text = speech.replace("Plasir", "testing")
        resp = ask(speech, display_text)
        context_manager.add("display-zoning-followup", lifespan=1)
        resp.add_msg("Would you like to look up another address?")
        return resp

    if zoning_info.get("code") is None:
        speech = "This address appears to be within Plasir County jurisdiction, but I was unable to retrieve zoning info in our system."
        display_text = speech.replace("Plasir", "testing")
        context_manager.add("display-zoning-followup", lifespan=1)
        resp.add_msg("Would you like to look up another address?")
        return ask(speech, display_text)

    # if zoning data retrieved, add followup context
    context_manager.add("Zoning-by-address-followup", lifespan=1)

    if has_screen():
        return zoning_by_address_screen(zoning_info, address)
    else:
        return zoning_by_address_voice(zoning_info, address)


def parse_zoning_code_data(zoning_info):
    current_app.logger.debug("Parsing Zone Code data from GIS")
    code_groups = zoning_info["code"].split(", ")
    top_codes = [c.split("-")[0] for c in code_groups]
    zoning_data = []

    # remove any duplicate codes
    top_codes = list(set(top_codes))

    if len(top_codes) > 1:
        current_app.logger.debug("Address has multiple zones")
        speech = "This address appears to fall under the "
        for i, c in enumerate(top_codes):
            zone_key = ds.key("ZoningCode", c)
            zone_data = ds.get(zone_key)

            zoning_data.append(zone_data)

            if i == len(top_codes) - 1:
                speech += "and "
                speech += f"{zone_data['displayName']}"
            else:
                speech += f"{zone_data['displayName']}, "

    elif len(top_codes) == 1:
        zone_key = ds.key("ZoningCode", top_codes[0])
        zone_data = ds.get(zone_key)
        zoning_data.append(zone_data)
        speech = f"This address appears to fall within the {zone_data['displayName']}"

    return speech, zoning_data


def zoning_by_address_screen(zoning_info, address):
    # Tahoe zones don't provide a zoning url
    # or a standard testing County zoning code
    context_manager.add('display-zoning-followup', lifespan=2)
    if zoning_info.get("tahoe_zoning"):
        resp = ask("This address appears to fall under Tahoe Zoning")
        resp.card(
            text=zoning_info["tahoe_zoning"],
            title=zoning_info["code"],
            subtitle=f"{address.title()} Zoning",
            img_url=PLACEHOLDER_IMG,
            img_alt="Alt text",
        )
        resp.link_out("View map", zoning_info["bkpg_url"]).add_msg(
            "Would you like to look up another address?"
        )
        return resp

    speech, zoning_data = parse_zoning_code_data(zoning_info)

    current_app.logger.debug("Building response from parsed zone data")
    resp = ask(speech)
    if len(zoning_data) > 1:
        zone_list = resp.build_list("Select a zone to learn more")
        for z in zoning_data:
            display = f"{z['displayName']} ({z['code']})"
            zone_list.add_item(display, key=z["code"])

        context_manager.add("zoning-selection", lifespan=2)
        context_manager.add("Zoning-overview-followup", lifespan=2)
        return zone_list.add_msg("Which zone would you like to hear about?")

    else:
        zone_data = zoning_data[0]
        resp.card(
            text=zone_data["description"],
            subtitle=f"{address.title()} Zoning",
            title=zone_data["displayName"],
            link=zone_data["url"],
            link_title="More info",
        )
        resp.link_out("View map", zoning_info["bkpg_url"])
        return resp.suggest("All Zoning codes").add_msg(
            "Would you like to look up another address?"
        )


def zoning_by_address_voice(zoning_info, address):
    speech, zoning_data = parse_zoning_code_data(zoning_info)
    resp = ask(speech)
    if len(zoning_data) > 1:
        resp.add_msg("Say the name of the zone if you'd like to learn more")
        context_manager.add("zoning-selection", lifespan=2)
        context_manager.add("Zoning-overview-followup", lifespan=2)
        return resp
    else:
        code = zoning_data[0]["code"]
        context = context_manager.add("voice-zone-info")
        context.set("zone_code", code)
        return resp.add_msg("Would you like to learn more about the zone?")

@assist.context("display-zoning-followup")
@assist.action("Zoning-by-address-screen-yes")
def zoning_new_address():
    return event('zoning-by-address')

@assist.context("display-zoning-followup")
@assist.action("Zoning-by-address-screen-no")
def zoning_new_address_no():
    return event('prompt-end')


@assist.context("Zoning-by-address-followup", "voice-zone-info")
@assist.action("Zoning-by-address-voice-followup-yes")
def zoning_more_info_followup_yes():
    zone_code = context_manager.get_param("voice-zone-info", "zone_code")
    context_manager.add("Prompt-End-followup")
    resp = zoning_info_voice(zone_code)
    return resp.add_msg("Is there anything else I can help with?")


@assist.context("voice-zone-info")
@assist.action("Zoning-by-address-voice-followup-no")
def zoning_more_info_followup_no():
    return event('prompt-end')


@assist.prompt_for("location", "Zoning-by-address")
@assist.prompt_for("location", "CDRA_WithinJurisdiction")
def prompt_address(location):
    return ask("Can I have the street address?")


@assist.action("CDRA_WithinJurisdiction", mapping={"location": "sys.location"})
def within_jurisdiction(location):
    address = location.get("street-address")
    if address is None:
        return prompt_address(location)
    try:
        result = get_jurisdiction(address)
    except Exception as e:
        current_app.logger.error(e)
        return ask(
            "I'm sorry, there was a problem when looking up your address. Can I get the address again?"
        )

    if result == WITHIN_JURISDICTION:
        resp = ask(
            "That address appears to be within the Jurisdiction of testing County"
        )
    elif result == UNINCORPORATED:
        resp = ask(
            "This address appears to be within an unincorporated area of testing County jurisdiction"
        )
    else:
        resp = ask(
            "That address does not appear to be within the Jurisdiction of testing County"
        )

        return resp.add_msg("Can I help with anything else?")



