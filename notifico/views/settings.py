from typing import Optional

import flask_wtf as wtf
from flask import g, redirect, url_for, session, render_template, Blueprint, \
    flash, request, abort
from flask_babel import lazy_gettext as lg
from wtforms import fields, validators
from sqlalchemy import func, or_

from notifico import user_required, db_session, Action, has_permission, \
    Permission
from notifico.models import IRCNetwork
from notifico.views.account_forms import UserPasswordForm, UserDeleteForm


settings_view = Blueprint('settings', __name__)


class NetworkDeleteForm(wtf.FlaskForm):
    confirm_host = fields.StringField(
        lg('Host'),
        validators=[
            validators.InputRequired()
        ]
    )

    def validate_confirm_host(self, field: fields.StringField):
        if self.meta.network.host != field.data:
            raise validators.ValidationError(lg('Host does not match.'))


class NetworkDetailsForm(wtf.FlaskForm):
    host = fields.StringField(
        lg('Host'),
        validators=[
            validators.InputRequired(),
            validators.Length(min=1, max=255),
            validators.Regexp(
                r'^(?!.*://).*$',
                message=lg('The host should not include a schema.')
            )
        ],
        default='irc.libera.chat'
    )
    port = fields.IntegerField(
        lg('Port'),
        validators=[
            validators.NumberRange(1024, 66552)
        ],
        default=6697
    )
    ssl = fields.BooleanField(
        lg('Use SSL'),
        default=True
    )

    def validate_host(self, field: fields.StringField):
        # Check to see if a global network or a user's custom network already
        # exists for this host.
        existing: IRCNetwork = db_session.query(IRCNetwork).filter(
            func.lower(IRCNetwork.host) == func.lower(field.data),
            IRCNetwork.port == self.port.data,
            IRCNetwork.ssl == self.ssl.data,
            or_(
                IRCNetwork.owner_id == g.user.id,
                IRCNetwork.public > 0
            )
        ).first()

        if existing:
            if existing.public > 0:
                raise validators.ValidationError(
                    lg(
                        'An identical global network already exists, please'
                        ' use that instead.'
                    )
                )
            else:
                raise validators.ValidationError(
                    lg('You already have an identical custom network.')
                )


@settings_view.route('/', methods=['GET', 'POST'])
@settings_view.route('/security', methods=['GET', 'POST'])
@user_required
def security():
    """
    Settings related to account security, such as changing passwords and
    deleting accounts.
    """
    password_form = UserPasswordForm()
    delete_form = UserDeleteForm()

    if request.method == 'POST':
        match request.form['action']:
            case 'change-password':
                if password_form.validate_on_submit():
                    # Change the user's password.
                    g.user.set_password(password_form.password.data)
                    db_session.commit()
                    flash(
                        lg('Your password has been changed.'),
                        category='success'
                    )
                    return redirect(url_for('.security'))
            case 'delete-account':
                if delete_form.validate_on_submit():
                    session.clear()
                    db_session.delete(g.user)
                    db_session.commit()
                    flash(
                        lg('Your account has been deleted. Goodbye.'),
                        category='success'
                    )
                    return redirect(url_for('.login'))

    return render_template(
        'settings/security.html',
        password_form=password_form,
        delete_form=delete_form
    )


@settings_view.route('/irc', methods=['GET', 'POST'])
@user_required
def irc():
    """
    Allows a user to manage their custom IRC networks. For superusers, this
    displays all networks and not just custom networks.
    """
    if has_permission(Permission.SUPERUSER):
        networks = db_session.query(IRCNetwork).all()
    else:
        networks = g.user.networks

    return render_template('settings/irc.html', networks=networks)


@settings_view.route('/irc/networks/new', methods=['GET', 'POST'])
@user_required
def irc_network_new():
    form = NetworkDetailsForm()
    if form.validate_on_submit():
        if IRCNetwork.can(Action.CREATE):
            db_session.add(
                IRCNetwork(
                    host=form.host.data,
                    port=form.port.data,
                    ssl=form.ssl.data,
                    owner_id=g.user.id,
                    public=0
                )
            )
            db_session.commit()

            flash(
                lg('Your custom network has been created.'),
                category='success'
            )

        return redirect(url_for('.irc'))

    return render_template(
        'settings/irc_network.html',
        network_form=form,
        action='new'
    )


@settings_view.route('/irc/networks/<int:network_id>', methods=['GET', 'POST'])
@user_required
def irc_network_edit(network_id: int):
    network: Optional[IRCNetwork] = db_session.query(
        IRCNetwork
    ).filter(
        IRCNetwork.id == network_id
    ).first()
    if network is None:
        abort(404)

    if not IRCNetwork.can(Action.UPDATE, obj=network):
        abort(403)

    network_form = NetworkDetailsForm(prefix='network', obj=network)
    delete_form = NetworkDeleteForm(prefix='delete', meta={
        'network': network
    })
    delete_form.confirm_host.render_kw = {
        'placeholder': network.host
    }

    if request.method == 'POST':
        match request.form['action']:
            case 'edit':
                if network_form.validate_on_submit():
                    network_form.populate_obj(network)
                    db_session.add(network)
                    db_session.commit()

                    flash(
                        lg('Your custom network has been updated.'),
                        category='success'
                    )

                    return redirect(url_for('.irc'))
            case 'delete':
                if delete_form.validate_on_submit():
                    db_session.delete(network)
                    db_session.commit()

                    flash(
                        lg('Your custom network has been deleted.'),
                        category='success'
                    )

                    return redirect(url_for('.irc'))

    return render_template(
        'settings/irc_network.html',
        network_form=network_form,
        delete_form=delete_form,
        action='edit',
        network=network
    )
