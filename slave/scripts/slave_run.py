#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os.path import join, dirname
from sys import argv

from twisted.scripts.twistd import run

import slave


def main():
    argv[1:1] = ['-n', '-y', join(dirname(slave.__file__), 'txapp.py')]
    run()


if __name__ == '__main__':
    main()
