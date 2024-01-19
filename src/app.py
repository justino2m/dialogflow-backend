# -*- coding: utf-8 -*-
"""The flask app module, containing the app factory function."""
from flask import Flask, request
from flask.logging import default_handler
import logging


from src import assistant, web, admin

from src.extensions import cors
from src.settings import ProdConfig
from src.logging import setup_cloud_logging


def create_app(config_object):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """

    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)

    if not app.debug:
        app.logger.removeHandler(default_handler)
        setup_cloud_logging(app)


    app.logger.debug(
        f"app created with {config_object.__name__} for project {app.config['PROJECT_ID']}"
    )

    register_extensions(app)
    register_blueprints(app)

    return app


def register_extensions(app):
    """Register Flask extensions.

    Flask-Assistant does not need to be initalized here if declared as a blueprint.
    Other extensions such as flask-sqlalchemy and flask-migrate are reigstered here.
    If the entire flask app consists of only the Assistant, uncomment the code below.
    """
    # assist.init_app(app, route="/")
    cors.init_app(app, resources={r"/*": {"origins": "*"}})
    return None


def register_blueprints(app):
    """Register Flask blueprints.

    When Flask-Assistant is used to create a blueprint within a standard flask app,
    it must be registered as such, rather that with init_app().

    If the entire flask app consists of only the Assistant, comment out the code below.
    """
    app.register_blueprint(assistant.blueprint)
    app.register_blueprint(web.views.blueprint)
    app.register_blueprint(admin.views.blueprint)
    return None
