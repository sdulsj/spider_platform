#!/usr/bin/env python
# -*- coding: utf-8 -*-
from scrapy.utils.misc import load_object
from twisted.application.internet import TimerService, TCPServer
from twisted.application.service import Application
from twisted.python import log
from twisted.web import server

from slave.implementations import Environment
from slave.implementations import FilesystemEggStorage
from slave.implementations import Performance
from slave.implementations import QueuePoller
from slave.implementations import SpiderScheduler
from slave.interfaces import IEggStorage
from slave.interfaces import IEnvironment
from slave.interfaces import IPerformance
from slave.interfaces import IPoller
from slave.interfaces import ISpiderScheduler


def application(config):
    app = Application("Spider Platform Slave")
    http_port = config.getint('http_port', 6800)
    bind_address = config.get('bind_address', '127.0.0.1')
    poll_interval = config.getfloat('poll_interval', 5)

    poller = QueuePoller(config)
    performance = Performance()
    egg_storage = FilesystemEggStorage(config)
    scheduler = SpiderScheduler(config)
    environment = Environment(config)

    app.setComponent(IPoller, poller)
    app.setComponent(IPerformance, performance)
    app.setComponent(IEggStorage, egg_storage)
    app.setComponent(ISpiderScheduler, scheduler)
    app.setComponent(IEnvironment, environment)

    lau_path = config.get('launcher', 'slave.launcher.Launcher')
    lau_cls = load_object(lau_path)
    launcher = lau_cls(config, app)

    web_path = config.get('web_root', 'slave.website.Root')
    web_cls = load_object(web_path)

    timer_queue = TimerService(poll_interval, poller.poll)
    timer_performance = TimerService(1, performance.poll)
    webservice = TCPServer(http_port, server.Site(web_cls(config, app)),
                           interface=bind_address)
    log.msg(
        format="Spider Platform Slave web console available at "
               "http://%(bind_address)s:%(http_port)s/",
        bind_address=bind_address, http_port=http_port)

    launcher.setServiceParent(app)
    timer_queue.setServiceParent(app)
    timer_performance.setServiceParent(app)
    webservice.setServiceParent(app)

    return app
