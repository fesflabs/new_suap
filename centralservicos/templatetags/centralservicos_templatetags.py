# -*- coding: utf-8 -*-

from django.template import Library
from django.utils.safestring import mark_safe

from centralservicos.models import AvaliaBaseConhecimento, PerguntaAvaliacaoBaseConhecimento, Servico, GrupoAtendimento

register = Library()


@register.simple_tag
def obtem_servicos_disponiveis_usuario_area(user, area):
    """ Deve retornar os serviços que o usuario tem acesso em determinada area """
    servicos = Servico.objects.filter(area=area, ativo=True)
    return [s for s in servicos if s.pode_acessar_servico(user)]


@register.simple_tag
def obtem_grupos_por_categoria(categoria, servicos):
    """ Deve retornar os grupos da categoria informada que possuam servicos da lista """
    ids = [s.id for s in servicos]
    return categoria.gruposervico_set.filter(servico__id__in=ids).distinct()


@register.simple_tag
def obtem_servicos_por_grupo(user, area, grupo, servicos):
    ids = [s.id for s in servicos]
    servicos = grupo.servico_set.filter(id__in=ids)
    if not GrupoAtendimento.meus_grupos(user, area).exists():
        servicos = servicos.filter(interno=False).distinct()
    return servicos.distinct()


@register.simple_tag(name="media_avaliacao_base_conhecimento")
def media_avaliacao_base_conhecimento(base_conhecimento, pergunta):
    return AvaliaBaseConhecimento.get_media_avaliacao(base_conhecimento, pergunta)


@register.simple_tag(name="minha_avaliacao_base_conhecimento", takes_context=True)
def minha_avaliacao_base_conhecimento(context, base_conhecimento, pergunta):
    request = context['request']
    try:
        avalia = AvaliaBaseConhecimento.objects.get(base_conhecimento=base_conhecimento, pergunta=pergunta, avaliado_por=request.user)
        return avalia.nota
    except AvaliaBaseConhecimento.DoesNotExist:
        return None


@register.simple_tag(name="tem_avaliacao_pendente", takes_context=True)
def tem_avaliacao_pendente(context, base_conhecimento):
    """ Verifica se o usuário tem avaliacao pendente para a base de conhecimento informada """
    request = context['request']
    perguntas = PerguntaAvaliacaoBaseConhecimento.objects.filter(area=base_conhecimento.area, ativo=True)
    for pergunta in perguntas:
        if not AvaliaBaseConhecimento.objects.filter(
            base_conhecimento=base_conhecimento, pergunta=pergunta, avaliado_por=request.user, data__gte=base_conhecimento.atualizado_em
        ).exists():
            return True
    return False


@register.inclusion_tag('avaliar_base_conhecimento.html', takes_context=True)
def avaliar_base_conhecimento(context, base_conhecimento, extra_class=""):
    request = context['request']
    avaliacoes = list()
    if request.user.has_perm('centralservicos.change_chamado'):
        perguntas_avaliacao = PerguntaAvaliacaoBaseConhecimento.objects.filter(area=base_conhecimento.area, ativo=True)
        for pergunta in perguntas_avaliacao:
            try:
                avalia = AvaliaBaseConhecimento.objects.get(
                    base_conhecimento=base_conhecimento, pergunta=pergunta, avaliado_por=request.user, data__gte=base_conhecimento.atualizado_em
                )
            except AvaliaBaseConhecimento.DoesNotExist:
                avalia = AvaliaBaseConhecimento(base_conhecimento=base_conhecimento, pergunta=pergunta)

            avaliacoes.append(avalia)

    return {'avaliacoes': avaliacoes, 'extra_class': extra_class}


@register.simple_tag()
def exibe_estrelas_avaliacao(nota):
    retorno = list()
    retorno.append("<ul class=\"stars\">")
    for i in range(1, 6):
        if nota < i:
            retorno.append("<li><span class=\"fas fa-star disabled\"></span></li>")
        else:
            retorno.append("<li><span class=\"fas fa-star\"></span></li>")
    retorno.append("</ul>")
    return mark_safe(''.join(retorno))
