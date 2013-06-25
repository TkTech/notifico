# -*- coding: utf-8 -*-
import json

from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    current_app,
    url_for,
    session,
    abort,
    make_response,
    request,
    flash
)
from notifico import db, user_required
from notifico.models import User, AuthToken
from notifico.services import reset, background
from notifico.views.account.forms import (
    UserLoginForm,
    UserRegisterForm,
    UserDeleteForm,
    UserForgotForm,
    UserResetForm,
    UserPasswordForm
)

account = Blueprint('account', __name__, template_folder='templates')
# Usernames that cannot be registered because they clash with internal
# routes.
_reserved = ('new',)


@account.before_app_request
def set_user():
    g.user = None
    if '_u' in session and '_uu' in session:
        g.user = User.query.filter_by(
            id=session['_u'],
            username=session['_uu']
        ).first()


@account.route('/login', methods=['GET', 'POST'])
def login():
    """
    Standard login form.
    """
    if g.user:
        return redirect(url_for('public.landing'))

    form = UserLoginForm()
    if form.validate_on_submit():
        u = User.by_username(form.username.data)
        session['_u'] = u.id
        session['_uu'] = u.username
        return redirect(url_for('projects.dashboard', u=u.username))

    return render_template('login.html', form=form)


@account.route('/logout')
@user_required
def logout():
    """
    Logout the current user.
    """
    if '_u' in session:
        del session['_u']
    if '_uu' in session:
        del session['_uu']
    return redirect(url_for('.login'))


@account.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    """
    If NOTIFICO_PASSWORD_RESET is enabled and Flask-Mail is configured,
    this view allows you to request a password reset email. It also
    handles accepting those tokens.
    """
    # Because this functionality depends on Flask-Mail and
    # celery being properly configured, we default to disabled.
    if not current_app.config.get('NOTIFICO_PASSWORD_RESET'):
        flash(
            'Password resets have been disabled by the administrator.',
            category='warning'
        )
        return redirect('.login')

    # How long should reset tokens last? We default
    # to 24 hours.
    token_expiry = current_app.config.get(
        'NOTIFICO_PASSWORD_RESET_EXPIRY',
        60 * 60 * 24
    )

    form = UserForgotForm()
    if form.validate_on_submit():
        user = User.by_username(form.username.data)
        new_token = reset.add_token(user, expire=token_expiry)

        # Send the email as a background job so we don't block
        # up the browser (and to use celery's built-in rate
        # limiting).
        background.send_mail.delay(
            'Notifico - Password Reset for {username}'.format(
                username=user.username
            ),
            # We're already using Jinja2, so we might as well use
            # it to render our email templates as well.
            html=render_template(
                'email_reset.html',
                user=user,
                reset_link=url_for(
                    '.reset_password',
                    token=new_token,
                    uid=user.id,
                    _external=True
                ),
                hours=token_expiry / 60 / 60
            ),
            recipients=[user.email],
            sender=current_app.config['NOTIFICO_MAIL_SENDER']
        )
        flash('A reset email has been sent.', category='success')
        return redirect(url_for('.login'))

    return render_template('forgot.html', form=form)


@account.route('/reset')
def reset_password():
    """
    Endpoint for password reset emails, which validates the token
    and UID pair, then redirects to the password set form.
    """
    token = request.args.get('token')
    uid = request.args.get('uid')

    u = User.query.get(int(uid))
    if not u or not reset.valid_token(u, token):
        flash('Your reset request is invalid or expired.', category='warning')
        return redirect(url_for('.login'))

    session['reset_token'] = token
    session['reset_user_id'] = uid

    return redirect(url_for('.reset_pick_password'))


@account.route('/reset/password', methods=['GET', 'POST'])
def reset_pick_password():
    token = session.get('reset_token')
    user_id = session.get('reset_user_id')

    if not token or not user_id:
        return redirect(url_for('.login'))

    u = User.query.get(int(user_id))
    if not u or not reset.valid_token(u, token):
        flash(
            'Your reset request is invalid or expired.',
            category='warning'
        )
        return redirect(url_for('.login'))

    form = UserResetForm()
    if form.validate_on_submit():
        u.set_password(form.password.data)
        db.session.commit()

        # The user has successfully reset their password,
        # so we want to clean up any other reset tokens as
        # well as our stashed session token.
        reset.clear_tokens(u)
        session.pop('reset_token', None)
        session.pop('reset_user_id', None)

        flash(
            'The password for {username} has been reset.'.format(
                username=u.username
            ),
            category='success'
        )
        return redirect(url_for('.login'))

    return render_template('reset.html', form=form)


@account.route('/register', methods=['GET', 'POST'])
def register():
    """
    If new user registrations are enabled, provides a registration form
    and validation.
    """
    if g.user:
        return redirect(url_for('public.landing'))

    # Make sure this instance is allowing new users.
    if not current_app.config.get('NOTIFICO_NEW_USERS', True):
        return redirect(url_for('public.landing'))

    form = UserRegisterForm()
    if form.validate_on_submit():
        # Checks out, go ahead and create our new user.
        u = User.new(form.username.data, form.email.data, form.password.data)
        db.session.add(u)
        db.session.commit()
        # ... and send them back to the login screen.
        return redirect(url_for('.login'))

    return render_template('register.html', form=form)


@account.route('/settings', methods=['GET', 'POST'])
@account.route('/settings/<do>', methods=['GET', 'POST'])
@user_required
def settings(do=None):
    """
    Provides forms allowing a user to change various settings.
    """
    password_form = UserPasswordForm()
    delete_form = UserDeleteForm()

    if do == 'p' and password_form.validate_on_submit():
        # Change the users password.
        g.user.set_password(password_form.password.data)
        db.session.commit()
        return redirect(url_for('.settings'))
    elif do == 'd' and delete_form.validate_on_submit():
        # Delete this users account and all related data.
        # Clear the session.
        if '_u' in session:
            del session['_u']
        if '_ue' in session:
            del session['_ue']
        # Remove the user from the DB.
        g.user.projects.order_by(False).delete()
        db.session.delete(g.user)
        db.session.commit()

        return redirect(url_for('.login'))

    return render_template(
        'settings.html',
        password_form=password_form,
        delete_form=delete_form
    )


@account.route('/user.json')
@user_required
def user_export():
    """
    Provides the user, their projects, channels, and hooks as a JSON
    file.
    """
    response = make_response(
        json.dumps(
            g.user.export(), sort_keys=True, indent=4
        )
    )
    response.headers['Content-Type'] = 'application/json'
    return response


@account.route('/tokens/')
@account.route('/tokens/<int:tid>')
@user_required
def tokens(tid=None):
    """
    Allows the user to view their OAuth tokens stored with Notifico.
    """
    if tid is not None:
        t = AuthToken.query.get(tid)
        if t is None:
            # The token no longer exists.
            return abort(404)

        if t.owner.id != g.user.id:
            # Forbidden, you don't own this token.
            return abort(403)

        t.owner.tokens.remove(t)
        db.session.delete(t)
        db.session.commit()

        return redirect(url_for('.tokens'))

    return render_template('tokens.html')
