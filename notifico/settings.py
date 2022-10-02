import os.path
import secrets
import typing as t
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    #: Key used for encrypting or signing various values, such as sessions.
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_hex(30))
    #: Enable CSRF protection on Flask-WTF forms.
    CSRF_ENABLED: bool = True

    SQLALCHEMY_DATABASE_URI: str = Field(
        env='DATABASE_URL',
        default='postgresql://localhost/notifico',
    )
    #: Just keep this disabled.
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    REDIS: str = Field(
        env='REDIS_URL',
        default='redis://localhost:6379/0'
    )

    BROKER_URL: str = 'redis://'
    CELERY_RESULT_BACKEND: str = 'redis://localhost:6379/0'
    CELERY_IMPORTS: t.List[str] = [
        'notifico.services.background'
    ]
    CELERY_TASK_SERIALIZER: str = 'json'

    CACHE_TYPE: str = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT: int = 300
    CACHE_KEY_PREFIX: str = 'cache_'
    CACHE_REDIS_URL: t.Optional[str] = None

    #: Route static assets ourselves, instead of using a proxy like nginx.
    ROUTE_STATIC: bool = True
    #: Allow users to signup.
    NEW_USERS: bool = True
    #: Should Notifico send password reset emails? This requires Flask-Mail to
    #: be properly configured.
    PASSWORD_RESET = False
    #: How long (in seconds) password resets should be valid for.
    PASSWORD_RESET_EXPIRY = 60 * 60 * 24

    IRC_NICKNAME: str = 'Not'
    IRC_USERNAME: str = 'notifico'
    IRC_REALNAME: str = 'Notifico! - https://github.com/tktech/notifico'

    #: DSN for optional Sentry error reporting.
    SENTRY_DSN: Optional[str] = None

    #: Set to n-# of proxies in front of this server setting X-Forwarded-For
    #: headers.
    USE_PROXY_HEADERS: int = 0

    class Config:
        case_sensitive = True
        env_prefix = 'NOTIFICO_'
        env_file = '.env'
        env_file_encoding = 'utf-8'
