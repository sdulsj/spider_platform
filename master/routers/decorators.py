#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Date  : 2018/8/16
# @Author: lsj
# @File  : decorators.py
# @Desc  : 
默认Python版本支持：3.6
"""
from functools import wraps

from flask import abort
from flask_login import current_user

from master.models import Permission


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    return permission_required(Permission.ADMINISTRATOR)(f)
