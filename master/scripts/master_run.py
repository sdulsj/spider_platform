#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os


def main():
    os.system("twistd web --wsgi master.run.app")
    pass


if __name__ == '__main__':
    main()
