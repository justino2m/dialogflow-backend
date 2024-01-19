from setuptools import setup, find_packages
from src import __version__

setup(
    name="testingchat",
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=["flask", "flask-assistant", "google-cloud-datastore"],
    entry_points="""
        [console_scripts]
        download-entities=scripts.download_entities:download
        upload-entities=scripts.upload_entities:upload
        bot=scripts.__init__:bot
        dialogflow=scripts.dialog.base:dialogflow
    """,
)
