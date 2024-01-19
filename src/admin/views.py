# -*- coding: utf-8 -*-
import os
from flask import Blueprint, request, current_app, jsonify
from flask.helpers import get_debug_flag
import google.auth.transport.requests
from google.oauth2 import id_token
from google.cloud import datastore

from scripts.download_entities import download_entities
from src.utilities.datastore import (
    ds,
    FAQ_KIND,
    build_entity_data,
    upload_ds_entity,
    delete_removed_synonyms,
    delete_ds_entities,
    retrieve_all_kind,
)
from src.utilities.dialogflow import (
    delete_df_entities,
    upload_df_entity,
    update_faq_intent_phrases,
)

blueprint = Blueprint("api", __name__, url_prefix="/api")

HTTP_REQUEST = google.auth.transport.requests.Request()

ADMIN_KIND = "Admins"
if os.getenv("APP_ENV") == "STAGE":
    ADMIN_KIND = "Admins-Stage"


def verify_auth(request):
    token = request.headers["Authorization"].split(" ").pop()
    try:
        claims = id_token.verify_firebase_token(token, HTTP_REQUEST)
    except Exception as e:
        current_app.logger.error(e)
        return False
    if not claims:
        return False

    return True


def verify_admin_status(request):
    user_uid = request.headers.get("User")
    user_key = ds.key(ADMIN_KIND, user_uid)
    entity = ds.get(user_key)
    if entity is None:
        return False

    if not entity.get("approved"):
        return False

    current_app.logger.info("User is authorized admin")
    return True


def verify_user(request):
    if not verify_auth(request):
        return False
    if not verify_admin_status(request):
        return False
    return True


@blueprint.route("/faqs", methods=["GET"])
def list_faqs():
    if not verify_user(request):
        return "Unauthorized", 401

    faqs = retrieve_all_kind(FAQ_KIND)

    return jsonify(faqs)


@blueprint.route("/faqs", methods=["POST"])
def create_faq():
    if not verify_user(request):
        return "Unauthorized", 401

    payload = request.json
    entity_key, entity_dict = build_entity_data(payload)

    delete_removed_synonyms(entity_key, entity_dict)
    upload_ds_entity(entity_key, entity_dict)
    upload_df_entity(entity_key, entity_dict)
    # download to update json file
    if get_debug_flag():
        download_entities()
    return "success", 201


@blueprint.route("/faqs", methods=["DELETE"])
def delete_faq():
    if not verify_user(request):
        return "Unauthorized", 401

    payload = request.json
    entity_key = payload["entityKey"]

    # first get the faq entity
    # so we can get synonyms and delete
    # faq and synonyms from ds and df
    key = ds.key(FAQ_KIND, entity_key)
    faq_entity = ds.get(key)

    delete_df_entities(faq_entity)
    delete_ds_entities(faq_entity)
    if get_debug_flag():
        download_entities()
    return "success", 200


@blueprint.route("/missed-queries", methods=["GET"])
def list_missed_queries():
    if not verify_user(request):
        return "Unauthorized", 401

    queries = retrieve_all_kind("UnmatchedQueries")

    return jsonify(queries)


@blueprint.route("/annotate-query", methods=["POST"])
def annotate_query():
    if not verify_user(request):
        return "Unauthorized", 401

    payload = request.json
    entity_key = payload["entityKey"]
    synonym = payload["synonym"]
    phrase = payload["query"]

    current_app.logger.info("Updating FAQ training phrases with annotated query")
    update_faq_intent_phrases(phrase, synonym)

    current_app.logger.info("Updating Datastore Synonyms")

    ds_faq_key = ds.key(FAQ_KIND, entity_key)
    ds_faq_entity = ds.get(ds_faq_key)
    ds_faq_entity["synonyms"].append(synonym)

    upload_ds_entity(entity_key, ds_faq_entity)
    upload_df_entity(entity_key, ds_faq_entity)

    # mark as resolved
    ds_query = ds.query(kind="UnmatchedQueries")
    ds_query.add_filter("query", "=", phrase)
    results = list(ds_query.fetch(limit=1))

    try:
        query_entity = results[0]
        query_entity.update({"resolved": True})
    except IndexError:
        return "Not Found", 404

    current_app.logger.debug(query_entity)
    ds.put(query_entity)

    # download to update json file
    if get_debug_flag():
        download_entities()
    return "success", 201


# TODO
# querying datastore based on query
# should be able to just use the key
# but querying with key/id
# doesn't return the entity for some reason
# may need to change the key type/set explicitly
@blueprint.route("/resolve-query", methods=["PUT"])
def resolve_query():
    if not verify_user(request):
        return "Unauthorized", 401

    queries = request.json
    query_ents = []
    for q in queries:
        current_app.logger.debug(f"Fetching UnmatchedQuery: {q.get('query')}")
        ds_query = ds.query(kind="UnmatchedQueries")
        ds_query.add_filter("query", "=", q["query"])
        results = list(ds_query.fetch(limit=1))
        query_ents.append(results[0])

    for e in query_ents:
        e.update({"resolved": True})

    current_app.logger.debug(f"Updating {len(query_ents)} queries as resolved")
    ds.put_multi(query_ents)

    return "Updated", 200


@blueprint.route("/delete-query", methods=["DELETE"])
def dismiss_query():
    if not verify_user(request):
        return "Unauthorized", 401

    queries = request.json
    query_ents = []
    for q in queries:
        current_app.logger.debug(f"Fetching UnmatchedQuery: {q.get('query')}")
        ds_query = ds.query(kind="UnmatchedQueries")
        ds_query.add_filter("query", "=", q["query"])
        results = list(ds_query.fetch(limit=1))
        query_ents.append(results[0])

    query_keys = [e.key for e in query_ents]

    current_app.logger.debug(f"Deleting {len(query_keys)} missed queries")
    ds.delete_multi(query_keys)

    current_app.logger.info(f"Deleted missed queries")
    return "deleted", 201


@blueprint.route("/admins", methods=["POST"])
def post_admin():
    """This endpoint is hit when a user logs in. If it is the first time, add them to datastore as unapproved"""

    # only verify headers, not admin status
    # because this endpoint will create the
    # entitiy to be checked
    if not verify_auth(request):
        return "Unauthorized", 401

    payload = request.json
    uid, email, name = payload["uid"], payload["email"], payload["displayName"]

    ds_key = ds.key(ADMIN_KIND, uid)
    entity = ds.get(ds_key)

    if entity is None:
        current_app.logger.debug("Adding new unapproved admin")
        entity = datastore.Entity(ds_key)
        entity["email"] = email
        entity["displayName"] = name
        entity["approved"] = False

        ds.put(entity)
        return jsonify({"msg": "Admin added", "admin": entity}), 201

    else:
        current_app.logger.debug("Admin user already added to datastore")
        return jsonify({"msg": "Already added", "admin": entity}), 200


@blueprint.route("/admins", methods=["PUT"])
def update_admin():
    if not verify_user(request):
        return "Unauthorized", 401

    payload = request.json

    if payload.get("uid") is None:
        return "Missing user UID", 400

    current_app.logger.debug(f"Updating admin {payload['email']}")
    ds_key = ds.key(ADMIN_KIND, payload["uid"])
    entity = datastore.Entity(ds_key)
    entity.update(payload)
    ds.put(entity)

    return "Updated", 201


@blueprint.route("/admins", methods=["GET"])
def get_admins():
    if not verify_user(request):
        return "Unauthorized", 401

    resp = {"Admins": []}

    query = ds.query(kind=ADMIN_KIND)
    for entity in query.fetch():
        admin_info = {
            "email": entity.get("email"),
            "displayName": entity.get("displayName"),
            "approved": entity.get("approved", False),
            "uid": entity.key.name,
        }
        resp["Admins"].append(admin_info)

    return jsonify(resp), 200

