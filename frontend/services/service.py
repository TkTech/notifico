# -*- coding: utf8 -*-
__all__ = ('Service',)


class Service(object):
    @staticmethod
    def service_id():
        """
        A unique numeric identifier for this service.
        """
        raise NotImplementedError()

    @staticmethod
    def service_name():
        """
        A unique, human-readable name for this service.
        """
        raise NotImplementedError()

    @staticmethod
    def service_url():
        """
        The URL of the service provider, if one exists.
        """
        raise NotImplementedError()

    @staticmethod
    def service_description():
        """
        A description of this service.
        """
        raise NotImplementedError()

    @staticmethod
    def format_request(user, request):
        """
        Called on each HTTP request.
        """
        raise NotImplementedError()
