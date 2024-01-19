# -*- coding: utf-8 -*-
import os


class Config(object):
    """Base configuration."""

    SECRET_KEY = os.getenv("ASSIST_SECRET", "secret-key")  # TODO: Change me
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))

    INTEGRATIONS = ["ACTIONS_ON_GOOGLE"]
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "test-county")


class ProdConfig(Config):
    """Production configuration."""

    ENV = "production"
    DEBUG = False

    # set in app engine
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "test-county")
    ALLOW_UNAPPROVED = False


class StagingConfig(Config):
    """Production configuration."""

    ENV = "staging"
    DEBUG = False

    # set in app engine
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "test-county-staging")
    ALLOW_UNAPPROVED = True


class DevConfig(Config):
    """Development configuration."""

    ENV = "dev"
    DEBUG = True

    # set locally
    PROJECT_ID = "test-county-staging"
    ALLOW_UNAPPROVED = True


class TestConfig(Config):
    """Test configuration."""

    TESTING = True
    DEBUG = True
