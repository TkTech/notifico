import sys
import enum
import datetime
import traceback

from flask import url_for

from notifico.extensions import db


class LogSeverity(enum.Enum):
    """
    The seveirty of a logged message.

    These are 1:1 for both key and value to the default levels of the Python
    logging module. This is to make it easy to emit events to both the Log
    model and to other standard loggers.
    """
    NOTSETG = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogContextType(enum.Enum):
    """
    Used to specify what type of ID is in the context container.
    """
    #: The ID of a specific user.
    USER = 10
    #: The ID of a specific project.
    PROJECT = 20
    #: The ID of a source instance.
    SOURCE_INST = 30
    #: The ID of a source implementation.
    SOURCE_IMPL = 40


class LogContext(db.Model):
    """
    Used to provide additional context on the who or what of a log error.

    Useful for showing all events related to a user, or a project with no
    more than a single JOIN.
    """
    __tablename__ = 'log_context'

    log_id = db.Column(db.Integer, db.ForeignKey('log.id'), primary_key=True)
    log = db.relationship(
        'Log',
        backref=db.backref(
            'related',
            lazy='dynamic',
            cascade='all, delete, delete-orphan',
        )
    )

    context_type = db.Column(
        db.Enum(LogContextType),
        nullable=False,
        primary_key=True
    )
    context_id = db.Column(db.BigInteger, nullable=False, primary_key=True)


class Log(db.Model):
    """
    A simple table for logging system events.

    Keep in mind the Log table is not highly performant. It is not meant
    to replace system logging for high volumes like DEBUG or INFO. It may
    be truncated at any time.
    """
    __tablename__ = 'log'

    id = db.Column(db.Integer, primary_key=True)

    #: The severity of the issued message.
    severity = db.Column(db.Enum(LogSeverity), nullable=False)

    #: The time this log event was *saved*, not emitted..
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)

    #: A short summary that can be used to display this log message when no
    #: other context is available. It will be interpolated with the values in
    #: `payload` for translation.
    summary = db.Column(db.String(1024))

    #: Any arbitrary data that the logger chooses to include. These values
    #: be passed when rendering the `summary` string and can be used for
    #: translation values.
    payload = db.Column(db.JSON, default=dict, server_default='{}')

    #: A possible exception traceback that caused this log event. Should
    #: only be present for severities of error and critical.
    trace = db.Column(db.Text())

    @classmethod
    def debug(cls, **kwargs):
        return cls(severity=LogSeverity.DEBUG, **kwargs)

    @classmethod
    def info(cls, **kwargs):
        return cls(severity=LogSeverity.INFO, **kwargs)

    @classmethod
    def warning(cls, **kwargs):
        return cls(severity=LogSeverity.WARNING, **kwargs)

    @classmethod
    def error(cls, **kwargs):
        type_, _, _ = sys.exc_info()
        if type_ is not None:
            kwargs['trace'] = traceback.format_exc()

        return cls(severity=LogSeverity.ERROR, **kwargs)

    @classmethod
    def critical(cls, **kwargs):
        type_, _, _ = sys.exc_info()
        if type_ is not None:
            kwargs['trace'] = traceback.format_exc()

        return cls(severity=LogSeverity.CRITICAL, **kwargs)

    @property
    def admin_get_url(self):
        return url_for('admin.logs_get', log_id=self.id)
