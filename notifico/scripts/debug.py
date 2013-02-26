#!/usr/bin/env python2
# -*- coding: utf8 -*-
"""
Starts a local notifico notifico instance for debugging & developing.
"""
from notifico import start

if __name__ == '__main__':
    app = start(debug=True)
    app.run()
