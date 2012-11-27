from flask import (
    Blueprint,
    render_template
)
from notifico.models import Project, User, Channel, Hook

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    return render_template('landing.html',
        Project=Project,
        User=User,
        Channel=Channel,
        Hook=Hook
    )


@public.route('/s/channels/<network>')
def channels(network):
    q = Channel.query.filter_by(host=network, public=True)

    return render_template('channels.html',
        channels=q,
        network=network
    )


@public.route('/s/users/')
@public.route('/s/users/<int:page>')
def users(page=1):
    q = User.query.order_by(False).order_by(User.joined.desc())

    return render_template('users.html',
        users=q
    )
