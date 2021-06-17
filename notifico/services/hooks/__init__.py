from notifico.services.hooks.hook import HookService
from notifico.services.hooks.bitbucket import BitbucketHook
from notifico.services.hooks.github import GithubHook
from notifico.services.hooks.plain import PlainTextHook
from notifico.services.hooks.jenkins import JenkinsHook
from notifico.services.hooks.jira import JIRAHook
from notifico.services.hooks.travisci import TravisHook
from notifico.services.hooks.appveyor import AppVeyorHook
from notifico.services.hooks.gitlab import GitlabHook

ALL_HOOKS = [
    HookService,
    BitbucketHook,
    GithubHook,
    PlainTextHook,
    JenkinsHook,
    JIRAHook,
    TravisHook,
    AppVeyorHook,
    GitlabHook
]
