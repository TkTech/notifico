import abc

from jinja2 import Environment, PackageLoader

from notifico.services.hook import HookService


class BundledService(HookService, abc.ABC):
    @staticmethod
    def env():
        """
        Returns a Jinja2 `Environment` for template rendering.
        """
        return Environment(
            loader=PackageLoader(
                'notifico.contrib.services',
                'templates'
            )
        )
