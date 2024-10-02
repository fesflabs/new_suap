from importlib import import_module

from django.conf import settings

__all__ = ['get_remote_session']


def get_remote_session(key):
    return import_module(settings.SESSION_ENGINE).SessionStore(session_key=key)
