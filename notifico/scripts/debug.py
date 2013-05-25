#!/usr/bin/env python2
# -*- coding: utf8 -*-
"""
Starts a local notifico notifico instance for debugging & developing.
"""
from notifico import create_instance

if __name__ == '__main__':
    app = create_instance(debug=True)
    app.run()
