from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    current_app,
    url_for,
    session,
    flash
)
from flask_babel import lazy_gettext as _

from notifico import db, user_required
from notifico.models.user import User
from notifico.forms.users import (
    UserLoginForm,
    UserRegisterForm
)

users = Blueprint('users', __name__)
# Usernames that cannot be registered because they clash with internal
# routes.
_reserved = ('new', 'api', 'settings')


@users.before_app_request
def set_user():
    g.user = None
    if '_u' in session and '_uu' in session:
        g.user = User.query.filter_by(
            id=session['_u'],
            username=session['_uu']
        ).first()


@users.route('/login', methods=['GET', 'POST'])
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

    return render_template('users/login.html', form=form)


@users.route('/logout')
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


@users.route('/register', methods=['GET', 'POST'])
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
        flash(
            _('Your account has been created, please login.'),
            category='success'
        )
        return redirect(url_for('.login'))

    return render_template('users/register.html', form=form)
