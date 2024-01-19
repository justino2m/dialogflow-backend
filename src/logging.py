import logging
from google.cloud import logging as gcp_logging


# logging.getLogger("flask_assistant").setLevel(logging.INFO)


def setup_cloud_logging(app):
    logging_client = gcp_logging.Client()
    logging_handler = logging_client.get_default_handler()

    fa_logger = logging.getLogger("flask_assistant")
    fa_logger.setLevel(logging.INFO)
    # fa_logger.addHandler(logging_handler)

    # root = logging.getLogger()
    # root.addHandler(logging_handler)

    # Attaches a Google Stackdriver
    #  handler to the root logger
    logging_client.setup_logging(logging.INFO, excluded_loggers=("werkzeug",))
