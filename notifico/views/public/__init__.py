from flask import (
    Blueprint,
    render_template,
)

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    """
    Show a landing page giving a short intro blurb to unregistered users
    and very basic metrics such as total users.
    """
    return render_template('landing.html')
