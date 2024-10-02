from comum.models import Configuracao
from django.core.cache import cache
from django.template import Library
from djtools.utils.response import render_to_string
from djtools import layout
from djtools.utils import get_session_cache

register = Library()


@register.simple_tag(takes_context=True)
def render_mensagens(context, messages, classe, id=''):
    """
    Renderiza o quadro de mensagens na index do SUAP.

    Args:
        context:
        messages (string): texto contendo a mensagem;
        classe (string): string com a classe **CSS**;
        id:

    Returns:
        String contendo o componente visual das mensagens.
    """
    if messages:
        return render_to_string(template_name='djtools/templates/components/messages.html', context={'messages': messages, 'classe': classe, 'id': id}, request=context['request'])
    return ''


@register.simple_tag(takes_context=True)
def render_quadro(context, quadro):
    """
    Renderiza o quadro na index do SUAP.

    Args:
        context:
        quadro ():

    Returns:
        String contendo o componente visual das mensagens.
    """
    return render_to_string(template_name='djtools/templates/components/quadro.html', context={'quadro': quadro}, request=context['request'])


@register.simple_tag(takes_context=True)
def render_quick_access(context, quick_access):
    """
    Renderiza o acesso rápido na index do SUAP.

    Args:
        context:
        quick_access ():

    Returns:
        String contendo o componente visual das mensagens.
    """
    timeout = 24 * 60 * 60
    request = context['request']

    def index_quick_access_sessao():
        retorno = []
        for _, data in layout.index_quick_access_data.send(sender=render_quick_access, request=request):
            retorno.extend(data)
        return retorno

    quick_access = get_session_cache(request, 'index_quick_access_data', index_quick_access_sessao, timeout)
    return render_to_string(template_name='djtools/templates/components/quick_access.html', context={'quick_access': quick_access}, request=context['request'])


@register.simple_tag(takes_context=True)
def render_rss(context):
    from comum.views import feed_noticias
    """
    Renderiza RSS na index do SUAP.

    Args:
        context:

    Returns:
        String contendo o componente visual das mensagens.
    """
    rss_configurada = Configuracao.get_valor_por_chave('comum', 'url_rss')

    if rss_configurada:
        noticias = cache.get('feed_noticias')
        if not noticias:
            feed_noticias(context['request'])
            noticias = cache.get('feed_noticias')
        return render_to_string(template_name='djtools/templates/components/rss.html', request=context['request'], context={'noticias': noticias})
    return ''


@register.simple_tag(takes_context=True)
def render_alert(context, titulo, icone, classe, objetos):
    """
    Renderiza os alertas na index do SUAP.

    Args:
        context:
        titulo:
        icone:
        classe:
        objetos:

    Returns:
        String contendo o componente visual das mensagens.
    """
    if objetos:
        return render_to_string(
            template_name='djtools/templates/components/alertas.html', context={'titulo': titulo, 'icone': icone, 'classe': classe, 'objetos': objetos}, request=context['request']
        )
    return ''
