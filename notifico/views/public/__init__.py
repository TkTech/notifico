from flask import (
    Blueprint,
    render_template,
    g,
    url_for
)
from notifico.models import Project, User, Channel, Hook

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    g.add_breadcrumb('Home', url_for('.landing'))
    return render_template('landing.html',
        Project=Project,
        User=User,
        Channel=Channel,
        Hook=Hook
    )
