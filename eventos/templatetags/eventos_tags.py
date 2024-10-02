from django.template import Library

from djtools.templatetags.filters import status

register = Library()


@register.simple_tag
def atividade_confirmada(participante, atividade):
    return status(atividade.participantes.filter(id=participante.id).exists())
