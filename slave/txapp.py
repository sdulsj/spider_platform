#!/usr/bin/env python
# -*- coding: utf-8 -*-
# this file is used to start scrapyd with twistd -y
from slave import get_application

application = get_application()
