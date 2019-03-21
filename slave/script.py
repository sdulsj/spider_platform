#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""This module can be used to execute Scrapyd from a Scrapy command"""

import os
import sys

try:  # PY2
    from cStringIO import StringIO
except ImportError:  # PY3
    from io import StringIO

from twisted.python import log
from twisted.internet import reactor
from twisted.application import app

from scrapy.utils.project import project_data_dir
from scrapy.exceptions import NotConfigured

from slave import get_application
from slave.config import Config


def _get_config():
    data_dir = os.path.join(project_data_dir(), 'slave')
    conf = {
        'eggs_dir': os.path.join(data_dir, 'eggs'),
        'logs_dir': os.path.join(data_dir, 'logs'),
        'items_dir': os.path.join(data_dir, 'items'),
        'dbs_dir': os.path.join(data_dir, 'dbs'),
    }
    for k in ['eggs_dir', 'logs_dir', 'items_dir', 'dbs_dir']:  # create dirs
        d = conf[k]
        if not os.path.exists(d):
            os.makedirs(d)
    slave_conf = """
[slave]
eggs_dir = %(eggs_dir)s
logs_dir = %(logs_dir)s
items_dir = %(items_dir)s
dbs_dir  = %(dbs_dir)s
    """ % conf
    return Config(extra_sources=[StringIO(slave_conf)])


def execute():
    try:
        config = _get_config()
    except NotConfigured:
        config = None
    log.startLogging(sys.stderr)
    application = get_application(config)
    app.startApplication(application, False)
    reactor.run()
