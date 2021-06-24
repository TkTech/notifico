from flask import abort
from werkzeug.routing import BaseConverter

from notifico.models.user import User
from notifico.models.project import Project


class UserConverter(BaseConverter):
    def to_python(self, value: str) -> User:
        user = User.query.filter(User.username_i == value).first()
        if not user:
            abort(404)

        return user

    def to_url(self, value: User) -> str:
        return value.username


class ProjectConverter(BaseConverter):
    """
    A project is always in the format "<username>/<project>", as a project
    cannot be resolved without a user to provide context.

    To get just a `User`, use the `UserConverter()`.
    """
    regex = r'(?:[^/]+/[^/]+)'

    def to_python(self, value: str) -> Project:
        username, project_name = value.split('/')

        project = Project.query.filter(
            Project.name_i == project_name,
            Project.owner.has(
                User.username_i == username
            )
        ).first()

        if not project:
            abort(404)

        return project

    def to_url(self, value: Project) -> str:
        return f'{value.owner.username}/{value.name}'
