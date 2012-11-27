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