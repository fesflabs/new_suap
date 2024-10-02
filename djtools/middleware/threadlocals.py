# -*- coding: utf-8 -*-

"""
In settings.py, MIDDLEWARE_CLASSES:
'<project_name>.djtools.middleware.threadlocals.ThreadLocals'

To import:
from <project_name>.djtools.middelware import threadlocals as tl
"""

from django.utils.deprecation import MiddlewareMixin
from threading import local

from djtools.utils import get_client_ip

tl = local()


def get_request():
    return getattr(tl, 'request', None)


def get_user():
    return getattr(tl, 'user', None)


def get_profile():
    try:
        return get_user().get_profile()
    except Exception:
        return None


def get_vinculo():
    try:
        return get_user().get_vinculo()
    except Exception:
        return None


def get_remote_addr():
    request = get_request()
    if request:
        return get_client_ip(request)
    return None


class ThreadLocals(MiddlewareMixin):
    def process_request(self, request):
        tl.user = getattr(request, 'user', None)
        tl.request = request
