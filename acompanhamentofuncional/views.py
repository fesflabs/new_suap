# -*- coding: utf-8 -*

from datetime import datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from djtools import layout
from djtools.templatetags.filters import in_group
from djtools.utils import httprr, rtr
from acompanhamentofuncional.forms import ServidorCessaoArquivoFrequenciaForm
from acompanhamentofuncional.models import ServidorCessao, ServidorCessaoFrequencia, Ato


@layout.alerta()
def index_alertas(request):
    alertas = list()
    user_logado = request.user

    is_gestor_rh = in_group(user_logado, 'Coordenador de Gestão de Pessoas') or \
        in_group(user_logado, 'Coordenador de Gestão de Pessoas Sistêmico')

    if is_gestor_rh:
        # controle de atos de admissão/concessão
        atrasados = Ato.get_atos(
            user_solicitante=user_logado, situacao_prazo=Ato.SITUACAO_PRAZO_ATRASADO)
        enviar_hoje = Ato.get_atos(
            user_solicitante=user_logado, situacao_prazo=Ato.SITUACAO_PRAZO_ENVIAR_HOJE)
        enviar_esta_semana = Ato.get_atos(
            user_solicitante=user_logado, situacao_prazo=Ato.SITUACAO_PRAZO_ENVIAR_ESTA_SEMANA)
        enviar_este_mes = Ato.get_atos(
            user_solicitante=user_logado, situacao_prazo=Ato.SITUACAO_PRAZO_ENVIAR_ESTE_MES)

        if atrasados.exists():
            alertas.append(dict(
                url='/admin/acompanhamentofuncional/ato/?situacao_prazo={}'.format(Ato.SITUACAO_PRAZO_ATRASADO),
                titulo='Você tem <strong>Atos de Admissão/Concessão</strong> com envio atrasado.'
            ))

        if enviar_hoje.exists():
            alertas.append(dict(
                url='/admin/acompanhamentofuncional/ato/?situacao_prazo={}'.format(Ato.SITUACAO_PRAZO_ENVIAR_HOJE),
                titulo='Você tem <strong>Atos de Admissão/Concessão</strong> com envio até hoje.'
            ))

        if enviar_esta_semana.exists():
            alertas.append(dict(
                url='/admin/acompanhamentofuncional/ato/?situacao_prazo={}'.format(Ato.SITUACAO_PRAZO_ENVIAR_ESTA_SEMANA),
                titulo='Você tem <strong>Atos de Admissão/Concessão</strong> com envio até esta semana.'
            ))

        if enviar_este_mes.exists():
            alertas.append(dict(
                url='/admin/acompanhamentofuncional/ato/?situacao_prazo={}'.format(Ato.SITUACAO_PRAZO_ENVIAR_ESTE_MES),
                titulo='Você tem <strong>Atos de Admissão/Concessão</strong> com envio até este mês.'
            ))

    return alertas


@rtr()
@permission_required('acompanhamentofuncional.view_servidorcessao')
def exibir_processo_cessao(request, processo_id):
    processo = get_object_or_404(ServidorCessao, pk=processo_id)
    title = 'Detalhes de Exercício Externo'

    usuario_logado_pode_editar = request.user.has_perm('acompanhamentofuncional.change_servidorcessao') or request.user.is_superuser
    pode_adicionar_frequencia = request.user.has_perm('acompanhamentofuncional.pode_adicionar_frequencia') or request.user.is_superuser
    usuario_logado_pode_visualizar_frequencias = usuario_logado_pode_editar or request.user.get_profile().id == processo.servidor_cedido.id

    return locals()


@rtr()
@login_required()
def adicionar_frequencia(request, processo_id):
    title = 'Adicionar Comprovação de Frequência'
    processo = get_object_or_404(ServidorCessao, pk=processo_id)
    usuario_logado_pode_editar_frequencias = (
        request.user.has_perm('acompanhamentofuncional.change_servidorcessao')
        or request.user.has_perm('acompanhamentofuncional.pode_adicionar_frequencia')
        or request.user.is_superuser
    )

    if not usuario_logado_pode_editar_frequencias:
        raise HttpResponseForbidden('Você não tem permissão para acessar essa tela.')
    frequencia = ServidorCessaoFrequencia()
    frequencia.servidor_cessao = processo
    frequencia.enviado_por = request.user
    frequencia.data_envio = datetime.today()
    form = ServidorCessaoArquivoFrequenciaForm(request.POST or None, files=request.FILES or None, instance=frequencia)
    if form.is_valid():
        form.save()
        return httprr('..')

    return locals()


@permission_required('acompanhamentofuncional.change_servidorcessao')
def excluir_frequencia(request, frequencia_id):
    frequencia = get_object_or_404(ServidorCessaoFrequencia, pk=frequencia_id)
    #
    usuario_logado_enviou_a_frequencia = frequencia.enviado_por.get_profile().id == request.user.get_profile().id
    if usuario_logado_enviou_a_frequencia or request.user.is_superuser:
        try:
            frequencia.delete()
            message = 'Frequência excluída.'
            tag = 'success'
        except Exception:
            message = 'Erro ao excluir frequência.'
            tag = 'failure'
    else:
        raise PermissionDenied
    #
    return httprr(f'/acompanhamentofuncional/exibir_processo_cessao/{frequencia.servidor_cessao_id}/', message=message, tag=tag)


@rtr()
@permission_required('acompanhamentofuncional.view_servidorcessao')
def frequencia_exibir_afastamento(request, frequencia_id):
    title = 'Detalhes do Afastamento'
    frequencia = get_object_or_404(ServidorCessaoFrequencia, pk=frequencia_id)
    pode_editar_afastamento = request.user.has_perm('ponto.change_afastamento')
    return locals()


@permission_required('acompanhamentofuncional.change_servidorcessao')
def frequencia_criar_afastamento(request, frequencia_id):
    frequencia = get_object_or_404(ServidorCessaoFrequencia, pk=frequencia_id)
    frequencia.criar_afastamento()
    return httprr('/acompanhamentofuncional/exibir_processo_cessao/{}/'.format(frequencia.servidor_cessao.id), message='Afastamento criado.')


@permission_required('acompanhamentofuncional.change_servidorcessao')
def frequencia_excluir_afastamento(request, frequencia_id):
    frequencia = get_object_or_404(ServidorCessaoFrequencia, pk=frequencia_id)
    frequencia.excluir_afastamento()
    return httprr(f'/acompanhamentofuncional/exibir_processo_cessao/{frequencia.servidor_cessao_id}/', message='Afastamento excluído.')
