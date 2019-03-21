#!/usr/bin/env python
# -*- coding: utf-8 -*-
import functools
import traceback
import warnings

from twisted.python import log


class SlaveDeprecationWarning(Warning):
    """Warning category for deprecated features, since the default
    DeprecationWarning is silenced on Python 2.7+
    """
    pass


class WarningMeta(type):
    def __init__(cls, name, bases, cls_dict):
        offending_wrapper_classes = tuple(c.__bases__ for c in bases
                                          if isinstance(c, WarningMeta))
        offending_classes = tuple(c for c, in offending_wrapper_classes)
        if offending_classes:
            warnings.warn(
                '%r inherits from %r which %s deprecated'
                ' and will be removed from a later slave release'
                % (cls, offending_classes,
                   ['is', 'are'][min(2, len(offending_classes)) - 1]),
                SlaveDeprecationWarning,
            )
        super(WarningMeta, cls).__init__(name, bases, cls_dict)


def deprecate_class(cls):
    class WarningMeta2(WarningMeta):
        pass

    for b in cls.__bases__:
        if type(b) not in WarningMeta2.__bases__:
            WarningMeta2.__bases__ += (type(b),)

    def new_init(*args, **kwargs):
        warnings.warn('%r will be removed from a later slave release' % cls,
                      SlaveDeprecationWarning)
        return cls.__init__(*args, **kwargs)

    return WarningMeta2(cls.__name__, (cls,), {'__init__': new_init})


# WEB服务认证装饰器
def decorator_auth(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        try:
            self, request = args[0], args[1]
            if self.root.auth:
                if request.getHeader(b"authorization") != self.root.auth:
                    return {
                        "node_name": self.root.node_name,
                        "status": "error",
                        "message": "Authentication exception!"
                    }
            return func(*args, **kw)
        except Exception as e:
            log.err()
            return {
                "status": "error",
                "message": str(e),
                "detail": traceback.format_exc().encode('utf-8')
            }

    return wrapper
