import datetime
import secrets

import sqlalchemy as sa
from sqlalchemy import orm

from notifico.database import Base
from notifico.service import available_services


class Hook(Base):
    __tablename__ = 'hook'

    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)
    key = sa.Column(
        sa.String(255),
        nullable=False,
        default=lambda: secrets.token_hex(24)
    )
    service_id = sa.Column(sa.Integer)
    config = sa.Column(sa.PickleType)

    project_id = sa.Column(sa.Integer, sa.ForeignKey('project.id'))
    project = orm.relationship(
        'Project',
        backref=orm.backref(
            'hooks',
            order_by=id,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    message_count = sa.Column(sa.Integer, default=0)

    @classmethod
    def by_service_and_project(cls, service_id, project_id):
        return cls.query.filter_by(
            service_id=service_id,
            project_id=project_id
        ).first()

    @property
    def hook(self):
        return available_services()[self.service_id]
