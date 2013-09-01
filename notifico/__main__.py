# -*- coding: utf-8 -*-
"""Notifico

Usage:
    notifico www [options]
    notifico init

Options:
    --debug                 Enable debugging.
                            (DO NOT USE ON PRODUCTION)
    --port=<port>           Port to listen on. [default: 5000]
    --host=<host>           Host to bind to. [default: localhost]
"""
import sys

from docopt import docopt

from notifico import create_instance, db
from notifico.models import *


def main(argv):
    args = docopt(__doc__, argv=argv[1:])

    if args['www']:
        app = create_instance()
        app.run(
            debug=args['--debug'],
            port=int(args['--port']),
            host=args['--host']
        )
    elif args['init']:
        app = create_instance()
        with app.app_context():
            # Let SQLAlchemy create any missing tables.
            db.create_all()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
