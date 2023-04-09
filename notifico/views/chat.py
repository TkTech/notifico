import datetime
from calendar import HTMLCalendar

from flask import (
    Blueprint,
    abort,
    render_template,
    url_for,
)

from notifico import db_session
from notifico.models import ChatLog, ChatMessage
from notifico.util.colorhash import ColorHash
from notifico.util.irc import to_html

chat_view = Blueprint("chat", __name__, template_folder="templates")


class LoggerCalendar(HTMLCalendar):
    # This probably isn't the right way to do this, but it works. We have to
    # add a bit to this to generate the links and get the context for
    # formatday().
    def __init__(self, *args, date: datetime.date, log: ChatLog, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = log
        self.date = date

    def formatmonthname(
        self, theyear: int, themonth: int, withyear: bool = True
    ) -> str:
        date = datetime.date(self.date.year, self.date.month, 1)
        prev_month = (date - datetime.timedelta(days=1)).replace(day=1)
        # This will break if they change a month to have 32 days in 3089 :P
        next_month = (date + datetime.timedelta(days=32)).replace(day=1)

        prev_url = url_for(
            ".details", log_id=self.log.id, date=prev_month.strftime("%Y-%m-%d")
        )
        next_url = url_for(
            ".details", log_id=self.log.id, date=next_month.strftime("%Y-%m-%d")
        )

        if next_month > datetime.date.today():
            return (
                f"<tr>"
                f'<th colspan="7" class="month">'
                f'<a href="{ prev_url }">&lt;&lt;</a> '
                f'{ self.date.strftime("%B %Y") } '
                f"&gt;&gt;"
                f"</th>"
                f"</tr>"
            )
        else:
            return (
                f"<tr>"
                f'<th colspan="7" class="month">'
                f'<a href="{ prev_url }">&lt;&lt;</a> '
                f'{ self.date.strftime("%B %Y") } '
                f'<a href="{ next_url }">&gt;&gt;</a>'
                f"</th>"
                f"</tr>"
            )

    def formatday(self, day: int, weekday: int) -> str:
        if day == 0:
            return '<td class="noday">&nbsp;</td>'
        else:
            date = datetime.date(self.date.year, self.date.month, day)
            if date > datetime.date.today():
                # No point making links for future days, won't be any logging
                # yet.
                return f'<td class="day text-muted">{day}</td>'

            url = url_for(
                ".details", log_id=self.log.id, date=date.strftime("%Y-%m-%d")
            )
            if date == self.date:
                return (
                    f'<td class="day">'
                    f'<a href="{url}" class="selected-day">{day}</a>'
                    f"</td>"
                )
            else:
                return (
                    f'<td class="day">' f'<a href="{ url }">{day}</a>' f"</td>"
                )


@chat_view.route("/<int:log_id>")
@chat_view.route("/<int:log_id>/<date>")
def details(log_id: int, date: str | None = None):
    """
    Show a chat log.
    """
    chat_log = db_session.query(ChatLog).filter(ChatLog.id == log_id).first()
    if chat_log is None:
        return abort(404)

    if date is None:
        date = datetime.date.today()
    else:
        try:
            date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return abort(404)

    lines = chat_log.messages.filter(
        ChatMessage.timestamp
        >= datetime.datetime.combine(date, datetime.time.min),
        ChatMessage.timestamp
        <= datetime.datetime.combine(date, datetime.time.max),
    ).order_by(ChatMessage.timestamp.asc())

    return render_template(
        "chat/details.html",
        date=date,
        chat_log=chat_log,
        lines=lines,
        channel=chat_log.channels.first(),
        calendar=LoggerCalendar(log=chat_log, date=date),
        to_html=to_html,
        color_hash=ColorHash,
    )
