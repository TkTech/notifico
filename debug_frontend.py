#!/usr/bin/env python2
# -*- coding: utf8 -*-
"""
Starts a local notifico frontend instance for debugging & developing.
"""
from frontend import start

if __name__ == '__main__':
    app = start(debug=True)
    app.run(host='0.0.0.0')
