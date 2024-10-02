# -*- coding: utf-8 -*-
import markdown
from django.template import Library

from demandas.models import Situacao

register = Library()


@register.filter()
def gfm(texto):
    from mdx_gfm import GithubFlavoredMarkdownExtension

    html = markdown.markdown(texto, extensions=[GithubFlavoredMarkdownExtension()])
    return html


@register.filter()
def status_dashboard(situacao):
    if situacao == Situacao.ESTADO_ABERTO:
        return 'info'
    elif situacao in [Situacao.ESTADO_APROVADO, Situacao.ESTADO_HOMOLOGADA]:
        return 'success'
    elif situacao == Situacao.ESTADO_SUSPENSO:
        return 'error'
    elif situacao in [Situacao.ESTADO_EM_ANALISE, Situacao.ESTADO_EM_HOMOLOGACAO]:
        return 'warning'
    else:
        return 'alert'
