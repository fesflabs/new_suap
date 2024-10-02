from django import template

from djtools.utils import is_ajax

register = template.Library()


@register.filter(name='is_ajax')
def ajax(request):
    return is_ajax(request)
