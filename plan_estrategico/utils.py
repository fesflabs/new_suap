# -*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied

from comum.utils import get_setor

# verifica na hierarquia de setores qual o setor de nível mais baixo que possui unidade administrativa associada
from plan_estrategico.models import UnidadeGestora


def get_setor_unidade_gestora(user=None):
    try:
        caminho = get_setor(user).get_caminho()
        while len(caminho):
            setor_atual = caminho.pop()
            unidade = UnidadeGestora.objects.filter(setor_equivalente=setor_atual)
            if unidade:
                return unidade[0].setor_equivalente

        return None

    except Exception:
        return None


def iniciar_gerenciamento_acesso(request):
    msg_erro = 'Accesso permitido apenas para Gestores do Plano Estratégico.'

    setor_escolhido = get_setor_unidade_gestora(user=request.user)
    if not setor_escolhido:
        raise PermissionDenied(msg_erro)

    su = True

    msg_orientacao_acesso = 'Você está acessando essa tela por ser Gestor ou ter poder de gestor para cadastrar atividades na unidade {} ou um dos seus descendentes.'.format(
        setor_escolhido
    )
    return su, setor_escolhido, setor_escolhido, msg_orientacao_acesso
