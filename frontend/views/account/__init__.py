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

from frontend import user_required
from frontend.models import User

account = Blueprint('account', __name__, template_folder='templates')


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


class UserPasswordForm(wtf.Form):
    old = wtf.PasswordField('Old Password', validators=[
        wtf.Required()
    ])
    password = wtf.PasswordField('Password', validators=[
        wtf.Required(),
        wtf.Length(5),
        wtf.EqualTo('confirm', 'Passwords do not match.'),
    ])
    confirm = wtf.PasswordField('Confirm Password')

    def validate_old(form, field):
        if not User.login(g.user.email, field.data):
            raise wtf.ValidationError('Old Password is incorrect.')


class UserDeleteForm(wtf.Form):
    password = wtf.PasswordField('Password', validators=[
        wtf.Required(),
        wtf.Length(5),
        wtf.EqualTo('confirm', 'Passwords do not match.'),
    ])
    confirm = wtf.PasswordField('Confirm Password')

    def validate_password(form, field):
        if not User.login(g.user.email, field.data):
            raise wtf.ValidationError('Password is incorrect.')


@account.before_app_request
def set_user():
    g.user = None
    if '_u' in session and '_ue' in session:
        g.user = User.query.filter_by(
            id=session['_u'],
            email=session['_ue']
        ).first()


@account.route('/login', methods=['GET', 'POST'])
def login():
    """
    Standard login form.
    """
    if g.user:
        flash('You must logout before logging in.', 'error')
        return redirect(url_for('public.landing'))

    form = UserLoginForm()
    if form.validate_on_submit():
        u = User.by_email(form.email.data)
        session['_u'] = u.id
        session['_ue'] = u.email
        flash('Welcome back!', 'success')
        return redirect(url_for('public.landing'))

    return render_template('login.html', form=form)


@account.route('/logout')
@user_required
def logout():
    """
    Logout the current user.
    """
    if '_u' in session:
        del session['_u']
    if '_ue' in session:
        del session['_ue']

    return redirect(url_for('.login'))


@account.route('/register', methods=['GET', 'POST'])
def register():
    """
    If new user registrations are enabled, provides a registration form
    and validation.
    """
    if g.user:
        return redirect(url_for('public.landing'))

    # Make sure this instance is allowing new users.
    if not current_app.config.get('PUBLIC_NEW_USERS', True):
        flash('New registrations are currently disabled.', 'error')
        return redirect(url_for('public.landing'))

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
        flash('Your password has been changed.', 'success')
        g.db.session.commit()
    elif do == 'd' and delete_form.validate_on_submit():
        # Delete this users account and all related data.
        # Clear the session.
        if '_u' in session:
            del session['_u']
        if '_ue' in session:
            del session['_ue']
        # Remove the user from the DB.
        g.db.session.delete(g.user)
        g.db.session.commit()

        flash('Your account has been deleted.', 'success')
        return redirect(url_for('.login'))

    return render_template('settings.html',
        password_form=password_form,
        delete_form=delete_form
    )