import datetime
import enum
import secrets

import sqlalchemy as sa
from flask import url_for
from sqlalchemy import orm

from notifico.database import Base
from notifico.service import incoming_services


class Hook(Base):
    class Page(enum.IntEnum):
        TRIGGER = 100

    __tablename__ = "hook"

    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)
    key = sa.Column(
        sa.String(255), nullable=False, default=lambda: secrets.token_hex(24)
    )
    service_id = sa.Column(sa.Integer)
    config = sa.Column(sa.PickleType)

    project_id = sa.Column(sa.Integer, sa.ForeignKey("project.id"))
    project = orm.relationship(
        "Project",
        backref=orm.backref(
            "hooks", order_by=id, lazy="dynamic", cascade="all, delete-orphan"
        ),
    )

    message_count = sa.Column(sa.Integer, default=0)

    @classmethod
    def by_service_and_project(cls, service_id, project_id):
        return cls.query.filter_by(
            service_id=service_id, project_id=project_id
        ).first()

    @property
    def hook(self):
        return incoming_services()[self.service_id]

    def url(self, of: Page = Page.TRIGGER, **kwargs) -> str:
        match of:
            case self.Page.TRIGGER:
                return url_for(
                    "projects.hook_receive",
                    pid=self.project.id,
                    key=self.key,
                    **kwargs,
                )
            case _:
                raise ValueError(f"Don't know how to generate a URL for {of=}.")
