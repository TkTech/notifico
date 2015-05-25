#!/usr/bin/env python
# -*- coding: utf8 -*-
"""
Notifico is my personal open source MIT replacement to the
now-defunct http://cia.vc service with my own little spin on things.
"""
from setuptools import setup, find_packages


def get_version():
    """
    Load and return the current Notifico version.
    """
    local_results = {}
    execfile('notifico/version.py', {}, local_results)
    return local_results['__version__']


if __name__ == '__main__':
    setup(
        name='Notifico',
        version=get_version(),
        long_description=__doc__,
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        install_requires=[
            'Flask',
            'Flask-WTF==0.8.4',
            'Flask-Gravatar',
            'Flask-SQLAlchemy',
            'Flask-XML-RPC',
            'Flask-Mail',
            'Flask-Cache',
            'fabric',
            'sqlalchemy',
            'utopia',
            'gevent',
            'oauth2',
            'redis',
            'gunicorn',
            'requests',
            'pygithub',
            'xmltodict',
            'unidecode',
            'raven',
            'blinker',
            'docopt',
            'celery'
        ],
        dependency_links=[
            'https://github.com/notifico/utopia/tarball/master#egg=utopia'
        ]
    )
