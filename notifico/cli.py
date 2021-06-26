import click
from flask.cli import FlaskGroup

from notifico.app import create_app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Management script for the notifico service."""
