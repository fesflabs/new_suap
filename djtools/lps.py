# -*- coding: utf-8 -*-
from functools import wraps, WRAPPER_ASSIGNMENTS

from django import forms
from django.conf import settings
from django.db import models
from django.forms import forms as fforms
from django.forms import models as fmodels


# TODO: criar LPS para as URLs
# TODO: resolver provlemas de novas views

def set_attrs_klass(attrs, items):
    for key, value in items:
        if key in ['__module__', '__doc__', '__dict__', '__weakref__']:
            continue
        attrs[key] = value


class MetaModelPlus(models.base.ModelBase):
    def __new__(mcs, name, bases, attrs):
        if is_lps(attrs):
            s_m = attrs['__module__'].split('.')[0]
            parents = [b for b in bases if isinstance(b, models.base.ModelBase)]

            if parents:
                try:

                    mdl = __import__('{}.lps.{}.models'.format(s_m, settings.LPS), fromlist=[('models')])

                    if hasattr(mdl, name):
                        Klass = getattr(mdl, name)
                        set_attrs_klass(attrs, Klass.__dict__.items())

                except SyntaxError:
                    raise SyntaxError
                except Exception:
                    pass

        return super(MetaModelPlus, mcs).__new__(mcs, name, bases, attrs)


class MetaModelAdminPlus(forms.MediaDefiningClass):
    def __new__(mcs, name, bases, attrs):

        if is_lps(attrs):
            s_m = attrs['__module__'].split('.')
            s_m = '.'.join(s_m[:-1])

            parents = [b for b in bases if isinstance(b, forms.MediaDefiningClass)]

            if parents:
                try:
                    mdl = __import__('{}.lps.{}.admin'.format(s_m, settings.LPS), fromlist=[('admin')])

                    if hasattr(mdl, name):
                        Klass = getattr(mdl, name)
                        set_attrs_klass(attrs, list(Klass.__dict__.items()))

                except Exception:
                    pass

        return super(MetaModelAdminPlus, mcs).__new__(mcs, name, bases, attrs)


class MetaFormPlus(fforms.DeclarativeFieldsMetaclass):
    def __new__(mcs, name, bases, attrs):

        if is_lps(attrs):
            s_m = attrs['__module__'].split('.')
            s_m = '.'.join(s_m[:-1])
            parents = [b for b in bases if isinstance(b, fforms.DeclarativeFieldsMetaclass)]

            if parents:
                try:
                    mdl = __import__('{}.lps.{}.forms'.format(s_m, settings.LPS), fromlist=[('forms')])

                    if hasattr(mdl, name):
                        Klass = getattr(mdl, name)
                        set_attrs_klass(attrs, list(Klass.__dict__.items()))

                except Exception:
                    pass

        return super(MetaFormPlus, mcs).__new__(mcs, name, bases, attrs)


class MetaModelFormPlus(fmodels.ModelFormMetaclass):
    def __new__(mcs, name, bases, attrs):

        if is_lps(attrs):
            s_m = attrs['__module__'].split('.')
            s_m = '.'.join(s_m[:-1])

            parents = [b for b in bases if isinstance(b, fmodels.ModelFormMetaclass)]

            if parents:
                try:
                    mdl = __import__('{}.lps.{}.forms'.format(s_m, settings.LPS), fromlist=[('forms')])

                    if hasattr(mdl, name):
                        Klass = getattr(mdl, name)
                        set_attrs_klass(attrs, list(Klass.__dict__.items()))

                except Exception:
                    pass

        return super(MetaModelFormPlus, mcs).__new__(mcs, name, bases, attrs)


def is_lps(attrs):
    if settings.LPS:
        module_name = attrs.get('__module__')
        if module_name and module_name.split('.')[0] in settings.INSTALLED_APPS:
            return True
    return False


def lps(func):
    @wraps(func, assigned=WRAPPER_ASSIGNMENTS)
    def inner_func(*args, **kwargs):
        running_func = func
        if settings.LPS:
            try:
                s_m = func.__module__.split('.')
                s_f = s_m[-1]
                s_m = '.'.join(s_m[:-1])
                mdl = __import__('{}.lps.{}.{}'.format(s_m, settings.LPS, s_f), fromlist=[(s_f)])

                if hasattr(mdl, func.__name__):
                    running_func = getattr(mdl, func.__name__)
            except Exception:
                pass
        return running_func(*args, **kwargs)

    return inner_func
