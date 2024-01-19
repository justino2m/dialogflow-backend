# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import Blueprint, redirect
from src import __version__

blueprint = Blueprint("web", __name__, url_prefix="/", static_folder="../static")


@blueprint.route("/", methods=["GET", "POST"])
def home():
    """Landing page for the web/html blueprint"""
    return f"testing Chat Assistant Web Page - Version {__version__}"


@blueprint.route("/call-redirect/<tel_url>", methods=["GET"])
def redirect_call(tel_url):
    return redirect(tel_url)
