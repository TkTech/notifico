from flask import (
    Blueprint,
    url_for,
    redirect,
    request,
    render_template,
    abort
)
import flask_wtf as wtf
from wtforms import fields, validators

from notifico import db, group_required
from notifico.models import Project, Channel, Hook, User

admin = Blueprint('admin', __name__, template_folder='templates')


class UserPasswordForm(wtf.Form):
    password = fields.PasswordField('Password', validators=[
        validators.DataRequired(),
        validators.Length(5),
        validators.EqualTo('confirm', 'Passwords do not match.'),
    ])
    confirm = fields.PasswordField('Confirm Password')


@admin.route('/projects/', defaults={'page': 1})
@admin.route('/projects/<int:page>')
@group_required('admin')
def admin_projects(page=1):
    per_page = min(int(request.args.get('l', 25)), 100)
    sort_by = request.args.get('s', 'created')

    q = Project.query.order_by(False)
    q = q.order_by({
        'created': Project.created.desc(),
        'messages': Project.message_count.desc()
    }.get(sort_by, Project.created.desc()))

    pagination = q.paginate(page, per_page, False)

    return render_template(
        'admin_projects.html',
        pagination=pagination,
        per_page=per_page
    )


@admin.route('/user/<username>/', methods=['GET', 'POST'])
@group_required('admin')
def admin_user(username):
    do = request.args.get('do', None)
    u = User.by_username(username)
    if u is None:
        return abort(404)

    password_form = UserPasswordForm()

    if do == 'p' and password_form.validate_on_submit():
        u.set_password(password_form.password.data)
        db.session.commit()
        return redirect(url_for('.admin_user', username=username))

    return render_template(
        'admin_user.html',
        u=u,
        password_form=password_form
    )


@admin.route('/projects/delete/<int:pid>')
@group_required('admin')
def delete_project(pid):
    p = Project.query.get(pid)
    if not p:
        return redirect(url_for('.admin_projects'))

    db.session.delete(p)
    db.session.commit()

    return redirect(url_for('.admin_projects'))


@admin.route('/orphan')
@group_required('admin')
def admin_orphans():
    """
    Murders all orphans.
    """
    # Clean up orphaned channels.
    db.session.query(Channel).\
        filter(~Channel.project.has()).\
        delete(synchronize_session=False)

    # Clean up orphaned hooks.
    db.session.query(Hook).\
        filter(~Hook.project.has()).\
        delete(synchronize_session=False)

    db.session.commit()

    return 'Orphans cleaned.'


@admin.route('/error/<int:code>')
@group_required('admin')
def admin_error(code):
    """
    Raise the error code provided in `code`. This is an internal
    method used to test custom error handlers.
    """
    return abort(code)
