# -*- coding: utf-8 -*-
"""Create an application instance."""
import os
from flask.helpers import get_debug_flag

from src.app import create_app
from src.settings import DevConfig, ProdConfig, StagingConfig

APP_ENV = os.getenv("APP_ENV")
ENV_CONFIG = StagingConfig

if APP_ENV == "PROD":
    ENV_CONFIG = ProdConfig

CONFIG = DevConfig if get_debug_flag() else ENV_CONFIG


app = create_app(CONFIG)
