#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/8
# @Author: lsj
# @File  : __init__.py
# @Desc  :
默认Python版本支持：3.6+
Spider Platform Slave
Expand based on Scrapyd v1.2
"""
import pkgutil

from scrapy.utils.misc import load_object

from slave.config import Config

__version__ = pkgutil.get_data(__package__, 'VERSION').decode('ascii').strip()
version_info = tuple(__version__.split('.')[:3])


def get_application(app_conf=None):
    if app_conf is None:
        app_conf = Config()
    app_path = app_conf.get('application', 'slave.app.application')
    app_func = load_object(app_path)
    return app_func(app_conf)
