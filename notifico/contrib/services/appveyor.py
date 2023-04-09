import flask_wtf as wtf
from wtforms import fields, validators

from notifico.contrib.services import EnvironmentMixin
from notifico.services.hook import IncomingHookService


class AppVeyorConfigForm(wtf.FlaskForm):
    use_colors = fields.BooleanField(
        "Use Colors",
        validators=[validators.Optional()],
        default=True,
        description=(
            "If checked, commit messages will include minor mIRC coloring."
        ),
    )


class AppVeyorHook(EnvironmentMixin, IncomingHookService):
    """
    IncomingHookService hook for https://ci.appveyor.com
    """

    SERVICE_NAME = "AppVeyor"
    SERVICE_ID = 80

    @classmethod
    def service_description(cls):
        return cls.env().get_template("appveyor_desc.html").render()

    @classmethod
    def handle_request(cls, user, request, hook):
        payload = request.get_json()
        if not payload:
            return

        # event_name = payload['eventName']
        event_data = payload["eventData"]

        strip = not hook.config.get("use_colors", True)

        summary = cls._create_summary(event_data)
        details = "Details: {0}".format(event_data["buildUrl"])
        details = cls._prefix_line(details, event_data)

        yield cls.message(summary, strip)
        yield cls.message(details, strip)

    @classmethod
    def _prefix_line(cls, line, event_data):
        """
        Prefixes lines with [RepoName] and adds colours
        """

        prefix = "{RESET}[{BLUE}{name}{RESET}] ".format(
            name=event_data["projectName"], **cls.colors
        )
        return prefix + line

    @classmethod
    def _create_summary(cls, payload):
        """
        Create and return a one-line summary of the build
        """
        if payload["failed"] == True:
            status_colour = cls.colors["RED"]
        elif payload["passed"] == True:
            status_colour = cls.colors["GREEN"]

        lines = []

        # Build number
        lines.append(
            "AppVeyor - build {number}:".format(
                number=payload["buildVersion"],
            )
        )

        # Status and correct colours
        lines.append(
            "{status}{message}{RESET}.".format(
                status=status_colour, message=payload["status"], **cls.colors
            )
        )

        # branch & commit hash
        lines.append(
            "({G}{branch}{R} @ {G}{commit}{R})".format(
                branch=payload["branch"],
                commit=payload["commitId"][:7],
                G=cls.colors["GREEN"],
                R=cls.colors["RESET"],
            )
        )

        if payload["isPullRequest"] == True:
            lines.append(
                "(pull request {G}#{n}{R})".format(
                    n=payload["pullRequestId"],
                    G=cls.colors["GREEN"],
                    R=cls.colors["RESET"],
                )
            )

        line = " ".join(lines)
        return cls._prefix_line(line, payload)

    @classmethod
    def form(cls):
        return AppVeyorConfigForm
