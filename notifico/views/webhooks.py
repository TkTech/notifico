from flask import Blueprint

webhooks = Blueprint('webhooks', __name__)


@webhooks.route('/<int:project>/<key>')
def trigger(project, key):
    """
    """
