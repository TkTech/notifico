from flask import (
    Blueprint,
    render_template,
    g,
    url_for
)
from frontend.models import Project, User

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    g.add_breadcrumb('Home', url_for('.landing'))
    return render_template('landing.html',
        Project=Project,
        User=User
    )
