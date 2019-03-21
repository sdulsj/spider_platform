#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager

import pkg_resources

from slave import get_application
from slave.interfaces import IEggStorage


def activate_egg(egg_path):
    """Activate a Scrapy egg file. This is meant to be used from egg runners
    to activate a Scrapy egg file. Don't use it from other code as it may
    leave unwanted side effects.
    """
    try:
        d = next(pkg_resources.find_distributions(egg_path))
    except StopIteration:
        raise ValueError("Unknown or corrupt egg")
    d.activate()
    settings_module = d.get_entry_info('scrapy', 'settings').module_name
    os.environ.setdefault('SCRAPY_SETTINGS_MODULE', settings_module)


@contextmanager
def project_environment(project):
    app = get_application()
    egg_storage = app.getComponent(IEggStorage)
    egg_version = os.environ.get('SCRAPY_EGG_VERSION', None)
    version, egg_file = egg_storage.get(project, egg_version)
    if egg_file:
        prefix = '%s-%s-' % (project, version)
        fd, egg_path = tempfile.mkstemp(prefix=prefix, suffix='.egg')
        lf = os.fdopen(fd, 'wb')
        shutil.copyfileobj(egg_file, lf)
        lf.close()
        activate_egg(egg_path)
    else:
        egg_path = None
    try:
        assert 'scrapy.conf' not in sys.modules, "Scrapy settings already loaded"
        yield
    finally:
        if egg_path:
            os.remove(egg_path)


def main():
    project = os.environ['SCRAPY_PROJECT']
    with project_environment(project):
        from scrapy.cmdline import execute
        execute()


if __name__ == '__main__':
    main()
