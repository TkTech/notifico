# -*- coding: utf8 -*-


class Service(type):
    """
    A simple metclass for services (such as hooks or importers) that
    registers all subclasses.
    """
    def __init__(cls, name, bases, attrs):
        super(Service, cls).__init__(name, bases, attrs)

        if not hasattr(cls, 'services'):
            cls.services = {}
        else:
            cls.services[cls.SERVICE_ID] = cls
