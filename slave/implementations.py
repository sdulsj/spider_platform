#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import time
from distutils.version import LooseVersion
from glob import glob
from os import path, makedirs, remove
from shutil import copyfileobj, rmtree

import psutil
from six import iteritems
from six.moves.configparser import NoSectionError
from six.moves.urllib.parse import urlparse, urlunparse
from twisted.internet.defer import DeferredQueue, maybeDeferred
from twisted.internet.defer import inlineCallbacks, returnValue
from w3lib.url import path_to_file_uri
from zope.interface import implementer

from slave.interfaces import IEggStorage
from slave.interfaces import IEnvironment
from slave.interfaces import IPoller, IPerformance
from slave.interfaces import ISpiderQueue
from slave.interfaces import ISpiderScheduler
from slave.sqlite import JsonSqlitePriorityQueue


def get_project_list(config):
    """Get list of projects by inspecting the eggs dir and the ones defined in
    the scrapyd.conf [settings] section
    """
    eggs_dir = config.get('eggs_dir', 'eggs')
    if os.path.exists(eggs_dir):
        projects = os.listdir(eggs_dir)
    else:
        projects = []
    try:
        projects += [x[0] for x in config.cp.items('settings')]
    except NoSectionError:
        pass
    return projects


def get_spider_queues(config):
    """Return a dict of Spider Queues keyed by project name"""
    dbs_dir = config.get('dbs_dir', 'dbs')
    if not os.path.exists(dbs_dir):
        os.makedirs(dbs_dir)
    d = {}
    for project in get_project_list(config):
        db_path = os.path.join(dbs_dir, '%s.db' % project)
        d[project] = SqliteSpiderQueue(db_path)
    return d


@implementer(IEggStorage)
class FilesystemEggStorage(object):

    def __init__(self, config):
        self.basedir = config.get('eggs_dir', 'eggs')

    def put(self, egg_file, project, version):
        egg_path = self._egg_path(project, version)
        egg_dir = path.dirname(egg_path)
        if not path.exists(egg_dir):
            makedirs(egg_dir)
        with open(egg_path, 'wb') as f:
            copyfileobj(egg_file, f)

    def get(self, project, version=None):
        if version is None:
            try:
                version = self.list(project)[-1]
            except IndexError:
                return None, None
        return version, open(self._egg_path(project, version), 'rb')

    def list(self, project):
        egg_dir = path.join(self.basedir, project)
        versions = [path.splitext(path.basename(x))[0] for x in
                    glob("%s/*.egg" % egg_dir)]
        return sorted(versions, key=LooseVersion)

    def delete(self, project, version=None):
        if version is None:
            rmtree(path.join(self.basedir, project))
        else:
            remove(self._egg_path(project, version))
            if not self.list(project):  # remove project if no versions left
                self.delete(project)

    def _egg_path(self, project, version):
        sanitized_version = re.sub(r'[^a-zA-Z0-9_-]', '_', version)
        x = path.join(self.basedir, project, "%s.egg" % sanitized_version)
        return x


@implementer(IEnvironment)
class Environment(object):

    def __init__(self, config, init_env=os.environ):
        self.dbs_dir = config.get('dbs_dir', 'dbs')
        self.logs_dir = config.get('logs_dir', 'logs')
        self.items_dir = config.get('items_dir', '')
        self.jobs_to_keep = config.getint('jobs_to_keep', 5)
        if config.cp.has_section('settings'):
            self.settings = dict(config.cp.items('settings'))
        else:
            self.settings = {}
        self.init_env = init_env

    def get_environment(self, message, slot):
        project = message['_project']
        env = self.init_env.copy()
        env['SCRAPY_SLOT'] = str(slot)
        env['SCRAPY_PROJECT'] = project
        env['SCRAPY_SPIDER'] = message['_spider']
        env['SCRAPY_JOB'] = message['_job']
        if '_version' in message:
            env['SCRAPY_EGG_VERSION'] = message['_version']
        if project in self.settings:
            env['SCRAPY_SETTINGS_MODULE'] = self.settings[project]
        if self.logs_dir:
            env['SCRAPY_LOG_FILE'] = self._get_file(
                message, self.logs_dir, 'log')
        if self.items_dir:
            env['SCRAPY_FEED_URI'] = self._get_feed_uri(message, 'jl')
        return env

    def _get_feed_uri(self, message, ext):
        url = urlparse(self.items_dir)
        if url.scheme.lower() in ['', 'file']:
            return path_to_file_uri(self._get_file(message, url.path, ext))
        return urlunparse((url.scheme,
                           url.netloc,
                           '/'.join([
                               url.path,
                               message['_project'],
                               message['_spider'],
                               '%s.%s' % (message['_job'], ext)]),
                           url.params,
                           url.query,
                           url.fragment))

    def _get_file(self, message, file_dir, ext):
        logs_dir = os.path.join(
            file_dir, message['_project'], message['_spider'])
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        to_delete = sorted(
            (os.path.join(logs_dir, x) for x in os.listdir(logs_dir)),
            key=os.path.getmtime)[:-self.jobs_to_keep]
        for x in to_delete:
            os.remove(x)
        return os.path.join(logs_dir, "%s.%s" % (message['_job'], ext))


@implementer(IPoller)
class QueuePoller(object):

    def __init__(self, config):
        self.config = config
        self.update_projects()
        self.dq = DeferredQueue(size=1)
        self.queues = dict()

    @inlineCallbacks
    def poll(self):
        if self.dq.pending:
            return
        for p, q in iteritems(self.queues):
            c = yield maybeDeferred(q.count)
            if c:
                msg = yield maybeDeferred(q.pop)
                if msg is not None:  # In case of a concurrently accessed queue
                    d = msg.copy()
                    d['_project'] = p
                    d['_spider'] = d.pop('name')
                    returnValue(self.dq.put(d))

    def next(self):
        return self.dq.get()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)


@implementer(IPerformance)
class Performance(object):
    """Statistical system performance."""

    def __init__(self):
        self.disk_io_read_speed = None
        self.disk_io_write_speed = None
        self.net_io_sent_speed = None
        self.net_io_receive_speed = None
        # system performance indicators
        self._last_time = None
        # Disk I/O
        self._last_disk_io_read_bytes = None
        self._last_disk_io_write_bytes = None
        # Net I/O
        self._last_net_io_sent_bytes = None
        self._last_net_io_receive_bytes = None
        pass

    def poll(self):
        curr_time = time.time()  # 当前时间
        disk_io = psutil.disk_io_counters()  # 磁盘IO状态
        net_io = psutil.net_io_counters()  # 网络IO状态

        timedelta = curr_time - self._last_time if self._last_time else None
        if timedelta:
            # 分母 单位：KB/s
            denominator = 1024 * timedelta
            read_bytes = disk_io.read_bytes - self._last_disk_io_read_bytes
            write_bytes = disk_io.write_bytes - self._last_disk_io_write_bytes
            self.disk_io_read_speed = round(read_bytes / denominator, 2)
            self.disk_io_write_speed = round(write_bytes / denominator, 2)
            # 分母 单位：Kb/s
            denominator = 1000 * timedelta
            sent_bytes = net_io.bytes_sent - self._last_net_io_sent_bytes
            receive_bytes = net_io.bytes_recv - self._last_net_io_receive_bytes
            self.net_io_sent_speed = round(sent_bytes / denominator, 2)
            self.net_io_receive_speed = round(receive_bytes / denominator, 2)

        self._last_time = curr_time
        self._last_disk_io_read_bytes = disk_io.read_bytes
        self._last_disk_io_write_bytes = disk_io.write_bytes
        self._last_net_io_sent_bytes = net_io.bytes_sent
        self._last_net_io_receive_bytes = net_io.bytes_recv

        pass

    @property
    def cpu_percent(self):
        return psutil.cpu_percent()
        pass

    @property
    def virtual_memory_percent(self):
        return psutil.virtual_memory().percent
        pass

    @property
    def swap_memory_percent(self):
        return psutil.swap_memory().percent
        pass

    @property
    def disk_usage_percent(self):
        return psutil.disk_usage('/').percent
        pass

    pass


@implementer(ISpiderScheduler)
class SpiderScheduler(object):

    def __init__(self, config):
        self.config = config
        self.queues = dict()
        self.update_projects()

    def schedule(self, project, spider_name, **spider_args):
        q = self.queues[project]
        q.add(spider_name, **spider_args)

    def list_projects(self):
        return self.queues.keys()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)


@implementer(ISpiderQueue)
class SqliteSpiderQueue(object):

    def __init__(self, database=None, table='spider_queue'):
        self.q = JsonSqlitePriorityQueue(database, table)

    def add(self, name, **spider_args):
        d = spider_args.copy()
        d['name'] = name
        priority = float(d.pop('priority', 0))
        self.q.put(d, priority)

    def pop(self):
        return self.q.pop()

    def count(self):
        return len(self.q)

    def list(self):
        return [x[0] for x in self.q]

    def remove(self, func):
        return self.q.remove(func)

    def clear(self):
        self.q.clear()
