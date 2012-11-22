from flask import (
    Blueprint,
    render_template,
)
from frontend.models import Project, User

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    return render_template('landing.html',
        Project=Project,
        User=User
    )
