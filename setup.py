#!/usr/bin/env python
import os
import os.path

from setuptools import setup, find_packages


root = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(root, 'README.md'), 'rb') as readme:
    long_description = readme.read().decode('utf-8')


if __name__ == '__main__':
    setup(
        name='Notifico',
        version='2.0.0',
        packages=find_packages(),
        include_package_data=True,
        long_description=long_description,
        long_description_content_type='text/markdown',
        author='Tyler Kennedy',
        author_email='tk@tkte.ch',
        url='http://github.com/TkTech/notifico',
        zip_safe=False,
        install_requires=[
            'flask-wtf',
            'flask-gravatar',
            'flask-sqlalchemy',
            'flask-mail',
            'flask-caching',
            'flask-babel',
            'sqlalchemy',
            'email_validator',
            'oauth2',
            'redis',
            'requests',
            'pygithub',
            'xmltodict',
            'unidecode',
            'raven',
            # Click >=8 is broken on Celery 5.1.0. See:
            # https://github.com/celery/celery/issues/6768
            'click<8.0.0',
            'celery',
            # This must be installed at the end to fix a dependency issue
            # with pip.
            'flask'
        ],
        extras_require={
            'tests': [
                'pytest',
                'coverage'
            ]
        },
        entry_points={
            'console_scripts': [
                'notifico=notifico.cli:cli'
            ]
        }
    )
