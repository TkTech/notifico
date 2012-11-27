# Notifico!

Notifico is my personal open source ([MIT](http://en.wikipedia.org/wiki/MIT_License))
replacement to the now-defunct http://cia.vc service with my own little spin on things.

Please not that this is extremely alpha software and likely has many flaws and
potential exploits. That said, it's safe to run your own copy with registrations
disabled.

## Disk Layout

The disk layout is organized as such:

	| notifico
	|
	|	-> notifico
	|		- The UI.
	|	-> botifico
	|		- The bots that idle in channels.
	|	-> alembic
	|		- SQLAlchemy migration tool.
	|	-> utopia
	|		- Toy IRC library used for botifico.
	|	-> misc
	|		- Deploy tools and scripts.
	|	-> debug_frontend.py
	|		- Starts a local development server.
	|	-> fabfile.py
	|		- That fabric deploy script.
	|	-> README.md
	|		- This file.
	|	-> alembic.ini
	|		- Alembic configuration.


When running, it produces various other files in the running directory:

	|	-> botifico.log
	|		- An incoming IRC message log.
	|	-> notifico.log
	|		-> UI exception log when not running in debugging.
	|	-> testing.db
	|		-> SQLite database used by default.

## Requirements

Notifico is based around:

	- Flask
	- wtforms
	- sqlalchemy
	- redis

Botifico is based around:

	- Redis
	- gevent
	- utopia (bundled irc library)

## Running

Because I built this with myself and my use cases in mind, deployment
requires a bit of work, but is a 30-minute afair if you have any
familiarity with Python & redis.

To start with, copy the ``notifico/default_config.py`` file to the top
level of the project and name it ``local_config.py``. Make any minor
customizations you want here, such as site name and title, or redis
and SQL database settings. If this module exists, it is used to
override the defaults in Notifico and Botifico.

To start the UI for testing,

	python debug_frontend.py

To run the bots for testing,

	python -m botifico

## Deploying

Notifico is designed to run everything within a folder (not really,
but that's the easiest way to do it on a single instance). None
of the notifico tasks should ever run as root and you should instead
run it using a WSGI server like gunicorn and proxy to it from nginx.

You'll need to do a bit of work to get the deploy script running. It
is not well written.

