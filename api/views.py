# coding: utf-8

from djtools.utils import rtr


@rtr()
def index(request):
    title = 'API'
    return locals()
