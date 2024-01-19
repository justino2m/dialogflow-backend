import click
from scripts.download_entities import download
from scripts.upload_entities import upload
from scripts.new_entity import new_entity
from scripts.create_synonyms import create_all_synonyms


@click.group()
def bot():
    pass


bot.add_command(download)
bot.add_command(upload)
bot.add_command(new_entity)
bot.add_command(create_all_synonyms, "synonyms")
