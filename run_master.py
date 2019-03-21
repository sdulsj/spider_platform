#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

DIR_CURR = os.path.dirname(os.path.realpath(__file__))  # 当前目录


def main():
    os.getcwd()
    os.chdir(os.path.join(DIR_CURR, "master", "scripts"))
    os.system("python master_run.py")
    pass


if __name__ == '__main__':
    main()
