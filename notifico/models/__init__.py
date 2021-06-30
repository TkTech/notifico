from notifico.models.log import Log
from notifico.models.user import User
from notifico.models.project import Project
from notifico.models.source import Source, SourceInstance
from notifico.models.group import Group, Permission, Limit

#: All models used in the core.
# We use this so tools like alembic can find all the models we use, even if
# they're not necessarily imported by the time it runs.
ALL_MODELS = (
    Log,
    User,
    Project,
    Group,
    Permission,
    Limit,
    Source,
    SourceInstance
)
