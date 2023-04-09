from flask import (
    Blueprint,
    render_template,
)

from notifico.service import incoming_services
from notifico.services import stats

public = Blueprint("public", __name__, template_folder="templates")


@public.route("/")
def landing():
    """
    Show a landing page giving a short intro blurb to unregistered users
    and very basic metrics such as total users.
    """
    return render_template(
        "public/landing.html",
        services=incoming_services(),
        total_networks=stats.total_networks(),
        total_users=stats.total_users(),
        total_messages=stats.total_messages(),
        total_projects=stats.total_projects(),
        total_channels=stats.total_channels(),
    )
