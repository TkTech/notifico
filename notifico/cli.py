import click
from flask import Flask
from flask.cli import FlaskGroup

from notifico import create_instance


@click.group(cls=FlaskGroup, create_app=create_instance)
def cli():
    """
    Management tool for Notifico.
    """