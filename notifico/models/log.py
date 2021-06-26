import sys
import enum
import datetime
import traceback

from sqlalchemy.ext.declarative import declared_attr

from notifico import db


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
    severity = db.Column(db.Enum(LogSeverity))

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


class HasLogs:
    """
    A mixin for database models that adds a convienient `logs` property,
    allowing you to store and retrieve logs.

    Note that this only works when the associated model has a single `id`
    column. To work with more complex models, you'll need to make the
    association table and relationship yourself.

    .. note::

        Database migrations must be run whenver this mixin is added to a model
        in order to generate the association table.
    """
    @declared_attr
    def logs(cls):
        log_assoc = db.Table(
            f'{cls.__tablename__}_logs',
            cls.metadata,
            db.Column(
                'log_id',
                db.ForeignKey('log.id', ondelete='cascade'),
                primary_key=True
            ),
            db.Column(
                f'{cls.__tablename__}_id',
                db.ForeignKey(f'{cls.__tablename__}.id', ondelete='cascade'),
                primary_key=True
            )
        )

        return db.relationship(
            Log,
            secondary=log_assoc,
            lazy='dynamic',
            cascade='all, delete, delete-orphan',
            passive_deletes=True,
            single_parent=True
        )
