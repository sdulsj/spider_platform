#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from subprocess import Popen, PIPE

import six

from slave.config import Config
from slave.sqlite import JsonSqliteDict


class UtilsCache:
    # array of project name that need to be invalided
    invalid_cached_projects = []

    def __init__(self):
        self.cache_manager = JsonSqliteDict(table="utils_cache_manager")

    # Invalid the spider's list's cache of a given project (by name)
    @staticmethod
    def invalid_cache(project):
        UtilsCache.invalid_cached_projects.append(project)

    def __getitem__(self, key):
        for p in UtilsCache.invalid_cached_projects:
            if p in self.cache_manager:
                del self.cache_manager[p]
        UtilsCache.invalid_cached_projects[:] = []
        return self.cache_manager[key]

    def __setitem__(self, key, value):
        self.cache_manager[key] = value


def native_stringify_dict(dct_or_tuples, encoding='utf-8', keys_only=True):
    """Return a (new) dict with unicode keys (and values when "keys_only" is
    False) of the given dict converted to strings. `dct_or_tuples` can be a
    dict or a list of tuples, like any dict constructor supports.
    """
    d = {}
    for k, v in six.iteritems(dict(dct_or_tuples)):
        k = _to_native_str(k, encoding)
        if not keys_only:
            if isinstance(v, dict):
                v = native_stringify_dict(
                    v, encoding=encoding, keys_only=keys_only)
            elif isinstance(v, list):
                v = [_to_native_str(e, encoding) for e in v]
            else:
                v = _to_native_str(v, encoding)
        d[k] = v
    return d


def get_crawl_args(message):
    """Return the command-line arguments to use for the scrapy crawl process
    that will be started for this message
    """
    msg = message.copy()
    args = [_to_native_str(msg['_spider'])]
    del msg['_project'], msg['_spider']
    settings = msg.pop('settings', {})
    for k, v in native_stringify_dict(msg, keys_only=False).items():
        args += ['-a']
        args += ['%s=%s' % (k, v)]
    for k, v in native_stringify_dict(settings, keys_only=False).items():
        args += ['-s']
        args += ['%s=%s' % (k, v)]
    return args


def get_spider_list(project, runner=None, python_path=None, version=''):
    """Return the spider list from the given project, using the given runner"""
    if "cache" not in get_spider_list.__dict__:
        get_spider_list.cache = UtilsCache()
    try:
        return get_spider_list.cache[project][version]
    except KeyError:
        pass
    if runner is None:
        runner = Config().get('runner')
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'UTF-8'
    env['SCRAPY_PROJECT'] = project
    if python_path:
        env['PYTHONPATH'] = python_path
    if version:
        env['SCRAPY_EGG_VERSION'] = version
    pargs = [sys.executable, '-m', runner, 'list']
    proc = Popen(pargs, stdout=PIPE, stderr=PIPE, env=env)
    out, err = proc.communicate()
    if proc.returncode:
        msg = err or out or ''
        msg = msg.decode('utf8')
        raise RuntimeError(msg.encode('unicode_escape') if six.PY2 else msg)
    # FIXME: can we reliably decode as UTF-8?
    # scrapy list does `print(list)`
    tmp = out.decode('utf-8').splitlines()
    try:
        project_cache = get_spider_list.cache[project]
        project_cache[version] = tmp
    except KeyError:
        project_cache = {version: tmp}
    get_spider_list.cache[project] = project_cache
    return tmp


def _to_native_str(text, encoding='utf-8', errors='strict'):
    if isinstance(text, str):
        return text
    if not isinstance(text, (bytes, six.text_type)):
        raise TypeError('_to_native_str must receive a bytes, str or unicode '
                        'object, got %s' % type(text).__name__)
    if six.PY2:
        return text.encode(encoding, errors)
    else:
        return text.decode(encoding, errors)
