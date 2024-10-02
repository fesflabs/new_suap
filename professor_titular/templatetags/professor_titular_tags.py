# -*- coding: utf-8 -*-

from django.template import Library
from professor_titular.forms import ProcessoTitularForm

register = Library()


@register.filter
def render_qtd_itens(arquivo):
    return ProcessoTitularForm.factory_field_render_qtd_itens(arquivo)


@register.filter
def render_data_referencia(arquivo):
    return ProcessoTitularForm.factory_field_render_data_referencia(arquivo)


@register.filter
def render_nota_pretendida(arquivo):
    return ProcessoTitularForm.factory_field_render_nota_pretendida(arquivo)


@register.filter
def render_descricao(arquivo):
    return ProcessoTitularForm.factory_field_render_descricao(arquivo)


@register.filter
def human_file_size(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


@register.simple_tag(name="render_file_field", takes_context=True)
def render_file_field(context, processo, criterio):
    request = context['request']
    return ProcessoTitularForm.factory_field_render_arquivo(processo, criterio, request)
