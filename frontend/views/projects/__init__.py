from flask import (
    Blueprint,
    render_template,
    g,
    redirect,
    current_app,
    flash,
    url_for,
    session,
    abort
)
from flask.ext import wtf

from frontend import user_required
from frontend.models import User, Project

projects = Blueprint('projects', __name__, template_folder='templates')


class ProjectDetailsForm(wtf.Form):
    name = wtf.TextField('Project Name', validators=[
        wtf.Required(),
        wtf.Length(2, 50)
    ])
    public = wtf.BooleanField('Public', validators=[
    ], default=True)
    website = wtf.TextField('Project URL', validators=[
        wtf.Optional(),
        wtf.Length(max=1024),
        wtf.validators.URL()
    ])


@projects.route('/')
@user_required
def overview():
    return render_template('overview.html')


@projects.route('/new', methods=['GET', 'POST'])
@user_required
def new():
    form = ProjectDetailsForm()
    if form.validate_on_submit():
        p = Project.new(
            form.name.data,
            public=form.public.data,
            website=form.website.data
        )
        g.db.session.add(p)
        g.user.projects.append(p)
        g.db.session.commit()
        flash('Your project has been created.', 'success')
        return redirect(url_for('.overview'))

    return render_template('new_project.html', form=form)
