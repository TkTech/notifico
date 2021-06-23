from flask import Blueprint, request, render_template

webhooks = Blueprint('webhooks', __name__)


@webhooks.route('/<int:project>/<key>', methods=['GET', 'POST'])
def trigger(project, key):
    """
    Dispatches incoming webhooks to their respective projects and associated
    provider.
    """
    # Since we don't currently have any providers that issue a completely
    # empty GET request, we handle that case and return a help page. Users
    # keep clicking on the URLs.
    if request.method == 'GET' and not request.args:
        # Currently, this page is very minimal, but it's better than nothing or
        # a cryptic error. We should provide actual help.
        return render_template('errors/this_is_a_webhook.html')
