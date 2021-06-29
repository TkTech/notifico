from typing import Any
from functools import wraps
from dataclasses import dataclass
from collections.abc import Callable

from flask import render_template, request
from flask_wtf import FlaskForm
from flask_babel import lazy_gettext as _


@dataclass
class ConfirmPrompt:
    #: A function which accepts the route's arguments, and returns a URL
    #: for the user to be redirected on failure.
    cancel_url: Callable[Any, Any]

    #: Message to prompt the user with.
    message: str = _('Are you sure?')
    #: Template to use when rendering the prompt.
    template: str = 'confirm.html'

    #: Text used for the 'Yes' button.
    yes_text: str = _('Yes')
    #: CSS class string to use for the 'Yes' button instead of the template's
    #: default.
    yes_btn_class: str = None
    #: CSS class string to use for the 'Cancel' button instead of the
    #: template's default.
    cancel_btn_class: str = None


class ConfirmForm(FlaskForm):
    """This form is just a shim to inject a CSRF into the page."""


def confirmation_view(prompt: ConfirmPrompt):
    """
    Creates a view that can be used for confirmation of an action.

    On success, calls the function it wraps with the normal URL arguments as
    if it was a normal view.
    """
    def _wrap(f):
        @wraps(f)
        def _wrapped(*args, **kwargs):
            form = ConfirmForm()
            if 'confirm-yes' in request.form and form.validate_on_submit():
                return f(*args, **kwargs)

            return render_template(
                prompt.template,
                prompt=prompt,
                form=form,
                cancel_url=prompt.cancel_url(*args, **kwargs)
            )

        return _wrapped
    return _wrap
