from flask import (
    Blueprint,
    render_template,
    abort
)
from notifico.models import Project, User, Channel, Hook, BotEvent

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
    status_cache = {}

    def channel_status(channel):
        if channel.id not in status_cache:
            last_event = channel.last_event()
            if last_event is None:
                status_cache[channel.id] = '-'
            else:
                status_cache[channel.id] = last_event.status
        return status_cache[channel.id]

    return render_template('channels.html',
        channels=q,
        network=network,
        channel_status=channel_status
    )


@public.route('/s/users/')
@public.route('/s/users/<int:page>')
def users(page=1):
    q = User.query.order_by(False).order_by(User.joined.desc())

    return render_template('users.html',
        users=q
    )


def events(network, channel):
    q = Channel.query.filter_by(
        public=True,
        channel=channel,
        host=network
    ).first()
    if q is None:
        # If there isn't at least one public channel listing
        # for this channel, we display nothing.
        return abort(404)

    q = BotEvent.query.filter_by(
        host=network,
        channel=channel
    ).order_by(BotEvent.created.desc())

    return render_template('events.html',
        events=q
    )
