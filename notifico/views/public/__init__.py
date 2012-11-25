from flask import (
    Blueprint,
    render_template,
    g,
    url_for,
    redirect
)
from notifico.models import Project, User, Channel, Hook

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    if g.user:
        return redirect(
            url_for('projects.overview', u=g.user.username)
        )
    else:
        return redirect(url_for('account.login'))

    return render_template('landing.html',
        Project=Project,
        User=User,
        Channel=Channel,
        Hook=Hook
    )
