from functools import wraps
from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    current_app,
    flash,
    url_for,
    session
)
from flask.ext import wtf

from frontend.models import User

public = Blueprint('public', __name__, template_folder='templates')


class UserRegisterForm(wtf.Form):
    email = wtf.TextField('Email', validators=[
        wtf.Required(),
        wtf.validators.Email()
    ])
    password = wtf.PasswordField('Password', validators=[
        wtf.Required(),
        wtf.Length(5),
        wtf.EqualTo('confirm', 'Passwords do not match.'),
    ])
    confirm = wtf.PasswordField('Confirm Password')

    def validate_email(form, field):
        email = field.data.strip().lower()
        if User.exists_email(email):
            raise wtf.ValidationError(
                'A user already exists for that email.'
            )


class UserLoginForm(wtf.Form):
    email = wtf.TextField('Email', validators=[
        wtf.Required(),
        wtf.validators.Email()
    ])
    password = wtf.PasswordField('Password', validators=[
        wtf.Required()
    ])

    def validate_password(form, field):
        if not User.login(form.email.data, field.data):
            raise wtf.ValidationError('Incorrect email and/or password.')


def user_required(f):
    """
    A decorator for views which required a logged in user.
    """
    @wraps(f)
    def _wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('.login'))
        return f(*args, **kwargs)
    return _wrapped


@public.route('/login', methods=['GET', 'POST'])
def login():
    """
    Standard login form.
    """
    if g.user:
        flash('You must logout before logging in.', 'error')
        return redirect(url_for('.landing'))

    form = UserLoginForm()
    if form.validate_on_submit():
        u = User.by_email(form.email.data)
        session['_u'] = u.id
        session['_ue'] = u.email
        flash('Welcome back!', 'success')
        return redirect(url_for('.landing'))

    return render_template('login.html', form=form)


@public.route('/logout')
def logout():
    """
    Logout the current user.
    """
    if '_u' in session:
        del session['_u']
    if '_ue' in session:
        del session['_ue']

    return redirect(url_for('.login'))


@public.route('/register', methods=['GET', 'POST'])
def register():
    """
    If new user registrations are enabled, provides a registration form
    and validation.
    """
    # Make sure this instance is allowing new users.
    if not current_app.config.get('PUBLIC_NEW_USERS', True):
        flash('New registrations are currently disabled.', 'error')
        return redirect(url_for('.landing'))

    form = UserRegisterForm()
    if form.validate_on_submit():
        # Checks out, go ahead and create our new user.
        u = User.new(form.email.data, form.password.data)
        g.db.session.add(u)
        g.db.session.commit()
        # ... and send them back to the login screen.
        flash('Your account has been created!', 'success')
        return redirect(url_for('.login'))

    return render_template('register.html', form=form)


@public.route('/')
@user_required
def landing():
    return render_template('landing.html')
