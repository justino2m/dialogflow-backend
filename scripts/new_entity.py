import click
from pprint import pprint
import json

from .config import ENTITY_JSON_FILE, DS_KINDS


@click.command()
def new_entity():
    e = {}

    kind_prompt = "What kind is the entity?\n"
    for i, k in enumerate(DS_KINDS):
        kind_prompt += f"[{i}] {k}\n"

    kind_selection = input(kind_prompt)
    entity_kind = DS_KINDS[int(kind_selection)]
    entity_key = input("What is the name/key?\n")

    e["Category"] = input("What department/category?\n")

    e["Name"] = input("Display Name?\n")
    e["Speech"] = input("Speech response?\n")
    e["TextResponse"] = input("Text response?\n")

    e["ContactName"] = input("Name for contact info?\n")
    e["Web"] = input("Web link?\n")
    e["Web-Title"] = input("Title for web link?\n")
    e["LinkOut"] = input(
        "Additional URL for link out suggestion? (Must be verified domain)\n"
    )
    e["LinkOutTitle"] = input("Title for link out?\n")
    e["Call"] = input("Phone number?\n")
    e["Email"] = input("Email?\n")
    e["Directions"] = input("Address for directions?\n")

    chips_list = []
    c = True
    print("Now please provide suggestions. Hit enter (no input) to continue")
    while c != "":
        c = input("> ")
        if c != "":
            chips_list.append(c)

    e["Chips"] = chips_list

    print(
        "Great, I will now ask for a list of synonyms. Hit enter (no input) to continue"
    )
    synonym_list = []
    s = True
    while s != "":
        s = input("> ")
        if s != "":
            synonym_list.append(s)

    e["synonyms"] = synonym_list

    entity_obj = {}

    for k, v in e.items():
        if v is not None and v != "":
            entity_obj[k] = v

    if entity_obj.get("Name") is None:
        entity_obj["Name"] = entity_key

    pprint(entity_obj, indent=2)
    print(f"Kind: {entity_kind}, key: {entity_key}")
    confirm = input("Does the above entity look correct?(y/n)\n")
    if confirm == "y":
        with open(ENTITY_JSON_FILE, "r") as f:
            entity_dict = json.load(f)
            entity_dict[entity_kind][entity_key] = e

        with open(ENTITY_JSON_FILE, "w") as f:
            json.dump(entity_dict, f, indent=3, sort_keys=True)
            print(f"Entities dumped to {ENTITY_JSON_FILE}")

            print("Entity created and added to JSON file")
            print("To push changes run `bot upload`")
