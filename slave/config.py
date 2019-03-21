#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
from io import StringIO
from os.path import expanduser
from pkgutil import get_data

from scrapy.utils.conf import closest_scrapy_cfg
from six.moves.configparser import ConfigParser
from six.moves.configparser import NoSectionError, NoOptionError


class Config(object):
    """A ConfigParser wrapper to support defaults when calling instance
    methods, and also tied to a single section"""

    SECTION = 'scrapyd'

    def __init__(self, values=None, extra_sources=()):
        if values is None:
            sources = self._get_sources()
            default_config = get_data(__package__,
                                      'default.conf').decode('utf8')
            self.cp = ConfigParser()
            self.cp.read_file(StringIO(default_config))
            self.cp.read(sources)
            for fp in extra_sources:
                self.cp.read_file(fp)
        else:
            self.cp = ConfigParser(values)
            self.cp.add_section(self.SECTION)

    @staticmethod
    def _get_sources():
        sources = ['/etc/scrapyd/scrapyd.conf', r'c:\scrapyd\scrapyd.conf']
        sources += sorted(glob.glob('/etc/scrapyd/conf.d/*'))
        sources += ['scrapyd.conf']
        sources += [expanduser('~/.scrapyd.conf')]
        scrapy_cfg = closest_scrapy_cfg()
        if scrapy_cfg:
            sources.append(scrapy_cfg)
        return sources

    def _get_any(self, method, option, default):
        try:
            return method(self.SECTION, option)
        except (NoSectionError, NoOptionError):
            if default is not None:
                return default
            raise

    def get(self, option, default=None):
        return self._get_any(self.cp.get, option, default)

    def getint(self, option, default=None):
        return self._get_any(self.cp.getint, option, default)

    def getfloat(self, option, default=None):
        return self._get_any(self.cp.getfloat, option, default)

    def getboolean(self, option, default=None):
        return self._get_any(self.cp.getboolean, option, default)

    def items(self, section, default=None):
        try:
            return self.cp.items(section)
        except (NoSectionError, NoOptionError):
            if default is not None:
                return default
            raise
