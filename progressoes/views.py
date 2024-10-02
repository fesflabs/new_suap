# -*- coding: utf-8 -*-

from collections import OrderedDict
from djtools import layout
from django.shortcuts import get_object_or_404
from comum.utils import get_uo
from djtools.templatetags.filters import in_group
from djtools.utils import httprr, rtr, montar_timeline_horizontal, documento, send_notification
from progressoes.forms import (
    ProcessoProgressaoPeriodoForm,
    AvaliacaoServidorFormFactory,
    ProcessoProgressaoPeriodoAvaliadoresForm,
    AssinaturaAvaliadorForm,
    AssinaturaAvaliadoForm,
    AssinaturaChefeForm,
    AssinaturaProcessoForm,
    EstagioProbatorioPeriodoAvaliadoresForm,
    SelecionarProcessoEletronicoForm,
    SelecionarProtocoloForm,
)
from progressoes.models import ProcessoProgressao, ProcessoProgressaoPeriodo, ProcessoProgressaoAvaliacao, AvaliacaoModelo
from django.contrib.auth.decorators import permission_required, login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.template.defaultfilters import pluralize
from os.path import expanduser, join


@layout.quadro('Progressões', icone='users')
def index_quadros(quadro, request):
    eh_rh_sistemico = in_group(request.user, 'Coordenador de Gestão de Pessoas Sistêmico', ignore_if_superuser=False)
    eh_rh_campus = in_group(request.user, 'Coordenador de Gestão de Pessoas,Operador de Gestão de Pessoas', ignore_if_superuser=False)
    if eh_rh_sistemico or eh_rh_campus:
        id_uo_usuario_logado = get_uo(request.user).id if get_uo(request.user) else None
        numero_processos_progressao_a_iniciar = 0
        numero_processos_progressao_a_finalizar = 0
        if eh_rh_sistemico:
            numero_processos_progressao_a_iniciar = ProcessoProgressao.obter_processos_a_iniciar().count()
            numero_processos_progressao_a_finalizar = ProcessoProgressao.obter_processos_a_finalizar().count()
        elif eh_rh_campus and id_uo_usuario_logado:
            numero_processos_progressao_a_iniciar = ProcessoProgressao.obter_processos_a_iniciar().filter(avaliado__setor__uo_id=id_uo_usuario_logado).count()
            numero_processos_progressao_a_finalizar = ProcessoProgressao.obter_processos_a_finalizar().filter(avaliado__setor__uo_id=id_uo_usuario_logado).count()

        if numero_processos_progressao_a_iniciar:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Avaliaç{} de Desempenho'.format(pluralize(numero_processos_progressao_a_iniciar, 'ão,ões')),
                    subtitulo='A iniciar',
                    qtd=numero_processos_progressao_a_iniciar,
                    url='/admin/progressoes/processoprogressao/?tab=a_iniciar',
                )
            )
        if numero_processos_progressao_a_finalizar:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Avaliaç{} de Desempenho'.format(pluralize(numero_processos_progressao_a_finalizar, 'ão,ões')),
                    subtitulo='A finalizar',
                    qtd=numero_processos_progressao_a_finalizar,
                    url='/admin/progressoes/processoprogressao/?tab=em_tramite',
                )
            )

    # Ações do Servidor
    usuario_logado = request.user
    if usuario_logado.eh_servidor:
        servidor_logado = usuario_logado.get_relacionamento()
        numero_meus_processos_progressao_em_tramite = ProcessoProgressao.obter_processos_por_avaliado(servidor_logado).filter(status=ProcessoProgressao.STATUS_EM_TRAMITE).count()
        if numero_meus_processos_progressao_em_tramite:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Avaliaç{} de Desempenho'.format(pluralize(numero_meus_processos_progressao_em_tramite, 'ão,ões')),
                    subtitulo='Em trâmite',
                    qtd=numero_meus_processos_progressao_em_tramite,
                    url='/progressoes/meus_processos/',
                )
            )
        numero_minhas_avaliacoes_pendentes = ProcessoProgressaoAvaliacao.objects.filter(
            avaliador=request.user.get_profile(),
            status_avaliacao=ProcessoProgressaoAvaliacao.STATUS_AVALIACAO_PENDENTE,
            periodo__processo_progressao__status=ProcessoProgressao.STATUS_EM_TRAMITE,
        ).count()
        if numero_minhas_avaliacoes_pendentes:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Avaliaç{} de Desempenho'.format(pluralize(numero_minhas_avaliacoes_pendentes, 'ão,ões')),
                    subtitulo='A ser{} respondida{}'.format(pluralize(numero_minhas_avaliacoes_pendentes, 'em'), pluralize(numero_minhas_avaliacoes_pendentes)),
                    qtd=numero_minhas_avaliacoes_pendentes,
                    url='/progressoes/minhas_avaliacoes/?tab=0',
                )
            )

        # assinaturas pendentes
        avaliacoes_pendentes_a_assinar_como_avaliado = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_avaliado(avaliado=request.user.get_profile())
        avaliacoes_pendentes_a_assinar_como_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_avaliador(avaliador=request.user.get_profile())
        avaliacoes_pendentes_a_assinar_como_chefe = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_chefe(chefe=request.user.get_profile())
        avaliacoes_com_assinaturas_pendentes = (
            avaliacoes_pendentes_a_assinar_como_avaliado | avaliacoes_pendentes_a_assinar_como_avaliador | avaliacoes_pendentes_a_assinar_como_chefe
        )

        numero_avaliacoes_com_assinaturas_pendentes_numero = avaliacoes_com_assinaturas_pendentes.distinct().count()
        if numero_avaliacoes_com_assinaturas_pendentes_numero:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Avaliaç{} de Desempenho'.format(pluralize(numero_avaliacoes_com_assinaturas_pendentes_numero, 'ão,ões')),
                    subtitulo='A ser{} assinada{}'.format(
                        pluralize(numero_avaliacoes_com_assinaturas_pendentes_numero, 'em'), pluralize(numero_avaliacoes_com_assinaturas_pendentes_numero)
                    ),
                    qtd=numero_avaliacoes_com_assinaturas_pendentes_numero,
                    url='/progressoes/minhas_avaliacoes/?tab=2',
                )
            )

    return quadro


@rtr()
@permission_required('progressoes.change_processoprogressao')
def editar_processo(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)

    if processo.is_tipo_progressao_merito:
        title = 'Processo de Progressão'
    else:
        title = 'Processo de Estágio Probatório'

    afastamentos_no_periodo = processo.obtem_afastamentos()

    servidor = processo.avaliado

    historico_setor = servidor.historico_setor_suap(data_inicio=processo.data_inicio_contagem_progressao, data_fim=processo.data_fim_contagem_progressao)
    historico_setor_siape = servidor.historico_setor_siape(data_inicio=processo.data_inicio_contagem_progressao, data_fim=processo.data_fim_contagem_progressao)
    historico_funcao = servidor.historico_funcao(data_inicio=processo.data_inicio_contagem_progressao, data_fim=processo.data_fim_contagem_progressao)
    #
    timeline_historico_setor = montar_timeline_horizontal(
        historico_setor,
        processo.data_inicio_contagem_progressao,
        processo.data_fim_contagem_progressao,
        'data_inicio_no_setor',
        'data_fim_no_setor',
        'setor',
        'Histórico de Setores SUAP',
    )
    #
    timeline_historico_setor_siape = montar_timeline_horizontal(
        historico_setor_siape,
        processo.data_inicio_contagem_progressao,
        processo.data_fim_contagem_progressao,
        'data_inicio_setor_lotacao',
        'data_fim_setor_lotacao',
        'setor_exercicio',
        'Setores Exercício SIAPE',
    )
    #
    timeline_historico_funcao = montar_timeline_horizontal(
        historico_funcao, processo.data_inicio_contagem_progressao, processo.data_fim_contagem_progressao, 'data_inicio_funcao', 'data_fim_funcao', 'funcao_display', 'Funções'
    )
    #

    app_processo_eletronico_instalada = 'processo_eletronico' in settings.INSTALLED_APPS

    return locals()


@documento(enumerar_paginas=False)
@rtr()
@permission_required('progressoes.view_processoprogressao')
def imprimir_processo(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)
    #
    if processo.status != ProcessoProgressao.STATUS_FINALIZADO:
        return httprr('..', message='Impressão não disponível.', tag='failure')
    #
    avaliacoes = []
    for periodo in processo.processoprogressaoperiodo_set.all().order_by('data_inicio'):
        for avaliacao in periodo.processoprogressaoavaliacao_set.all().order_by('data_avaliacao'):
            avaliacoes.append(avaliacao)  # o objetivo é imprimir as avaliacoes em cada período cronologicamente
    return locals()


@rtr()
@permission_required('progressoes.view_processoprogressao')
def detalhes_processo(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)

    if processo.is_tipo_progressao_merito:
        title = 'Detalhes do Processo de Progressão'
    else:
        title = 'Detalhes do Processo de Estágio Probatório'

    app_processo_eletronico_instalada = 'processo_eletronico' in settings.INSTALLED_APPS

    return locals()


@rtr()
@permission_required('progressoes.view_processoprogressaoavaliacao')
def abrir_avaliacao(request, avaliacao_id):
    title = 'Avaliação de Desempenho'
    #
    avaliacao = get_object_or_404(ProcessoProgressaoAvaliacao, pk=ProcessoProgressaoAvaliacao.id_decoded(avaliacao_id))
    #
    FormClass = AvaliacaoServidorFormFactory(request, avaliacao)
    if not FormClass.usuario_pode_abrir:
        raise PermissionDenied
    else:
        # assinaturas
        assinatura_avaliado = AssinaturaAvaliadoForm(request=request, avaliacao=avaliacao)

        assinatura_avaliador = AssinaturaAvaliadorForm(request=request, avaliacao=avaliacao)

        assinatura_chefe = AssinaturaChefeForm(request=request, avaliacao=avaliacao)
        #
        form = FormClass(request.POST or None)
        if form.is_valid():
            if not form.avaliacao_somente_leitura:
                avaliador_estava_respondendo = form.is_avaliador_respondendo
                form.save()
                if avaliador_estava_respondendo and avaliacao.is_avaliada:
                    # solicita assinatura do avaliador
                    return httprr('/progressoes/assinar_avaliacao/{}/'.format(avaliacao.id_encoded), message='Avaliação salva. Se desejar, pode assiná-la agora.')
                return httprr('..', message='Avaliação salva.')
            else:
                return httprr('..')
        #
        return locals()


@permission_required('progressoes.change_processoprogressao')
def reavaliar_avaliacao(request, avaliacao_id):
    avaliacao = get_object_or_404(ProcessoProgressaoAvaliacao, pk=ProcessoProgressaoAvaliacao.id_decoded(avaliacao_id))
    #
    FormClass = AvaliacaoServidorFormFactory(request, avaliacao)
    if not FormClass.usuario_pode_abrir:
        raise PermissionDenied
    else:
        avaliacao_form = FormClass()
        if avaliacao_form.is_rh_comentando:
            avaliacao.reavaliar()
            return httprr('..', message='Avaliação desbloqueada.')
        #
        return httprr('..', message='Não foi possível desbloquear a avaliação.', tag='failure')


@login_required()
@rtr()
def assinar_avaliacao(request, avaliacao_id):
    title = 'Assinaturas da Avaliação'
    #
    avaliacao = get_object_or_404(ProcessoProgressaoAvaliacao, pk=ProcessoProgressaoAvaliacao.id_decoded(avaliacao_id))
    #
    avaliacao_pode_abrir = AvaliacaoServidorFormFactory(request, avaliacao).usuario_pode_abrir
    #
    if not avaliacao_pode_abrir:
        raise PermissionDenied
    else:
        avaliacao_avaliada = avaliacao.is_avaliada
        if avaliacao_avaliada:
            #
            # a página de assinatura possui 3 forms, portanto, 3 submissões distintas
            processa_assinatura_avaliado = AssinaturaAvaliadoForm.senha_assinante_field_name in request.POST
            processa_assinatura_avaliador = AssinaturaAvaliadorForm.senha_assinante_field_name in request.POST
            processa_assinatura_chefe = AssinaturaChefeForm.senha_assinante_field_name in request.POST
            #
            form_assinatura_avaliado = AssinaturaAvaliadoForm((processa_assinatura_avaliado and (request.POST or None)) or None, request=request, avaliacao=avaliacao)
            form_assinatura_avaliador = AssinaturaAvaliadorForm((processa_assinatura_avaliador and (request.POST or None)) or None, request=request, avaliacao=avaliacao)
            form_assinatura_chefe = AssinaturaChefeForm((processa_assinatura_chefe and (request.POST or None)) or None, request=request, avaliacao=avaliacao)
            #
            if processa_assinatura_avaliado and form_assinatura_avaliado.is_valid():
                form_assinatura_avaliado.save()
            if processa_assinatura_avaliador and form_assinatura_avaliador.is_valid():
                form_assinatura_avaliador.save()
            if processa_assinatura_chefe and form_assinatura_chefe.is_valid():
                form_assinatura_chefe.save()
    #
    return locals()


@login_required()
@rtr()
def assinar_processo(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)
    #
    if processo.is_tipo_progressao_merito:
        title = 'Assinar Processo de Progressão'
    else:
        title = 'Assinar Processo de Estágio Probatório'
    #
    usuario_logado = request.user.get_profile()
    #
    avaliacoes_avaliado = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_avaliado(usuario_logado).filter(periodo__processo_progressao=processo)
    avaliacoes_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_avaliador(usuario_logado).filter(periodo__processo_progressao=processo)
    avaliacoes_chefe = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_chefe(usuario_logado).filter(periodo__processo_progressao=processo)

    avaliacoes = (avaliacoes_avaliado | avaliacoes_avaliador | avaliacoes_chefe).distinct()
    #
    form_assinante = AssinaturaProcessoForm(request.POST or None, request=request)
    #
    if form_assinante.is_valid():
        for avaliacao in avaliacoes_avaliado:
            form_assinatura_do_avaliado = AssinaturaAvaliadoForm(request.POST or None, avaliacao=avaliacao)
            # confirma se o assinante eh realmente o esperado
            if form_assinatura_do_avaliado.get_assinante().id == form_assinante.assinante.id:
                if form_assinatura_do_avaliado.is_valid():
                    form_assinatura_do_avaliado.gera_assinatura()
                    form_assinatura_do_avaliado.save()

        for avaliacao in avaliacoes_avaliador:
            form_assinatura_do_avaliador = AssinaturaAvaliadorForm(request.POST or None, avaliacao=avaliacao)
            # confirma se o assinante eh realmente o esperado
            if form_assinatura_do_avaliador.get_assinante().id == form_assinante.assinante.id:
                if form_assinatura_do_avaliador.is_valid():
                    form_assinatura_do_avaliador.gera_assinatura()
                    form_assinatura_do_avaliador.save()

        for avaliacao in avaliacoes_chefe:
            form_assinatura_do_chefe = AssinaturaChefeForm(request.POST or None, avaliacao=avaliacao)
            # confirma se o assinante eh realmente o esperado
            if form_assinatura_do_chefe.get_assinante().id == form_assinante.assinante.id:
                if form_assinatura_do_chefe.is_valid():
                    form_assinatura_do_chefe.gera_assinatura()
                    form_assinatura_do_chefe.save()
        #
        return httprr('/progressoes/minhas_avaliacoes/?tab=2')
    #
    return locals()


@rtr()
@permission_required('progressoes.change_processoprogressao')
def adicionar_periodo(request, processo_id):
    title = 'Adicionar Período ao Processo'
    #
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)
    if processo.is_a_iniciar:
        periodo_novo = ProcessoProgressaoPeriodo()
        periodo_novo.processo_progressao = processo

        #
        form = ProcessoProgressaoPeriodoForm(request.POST or None, instance=periodo_novo, processo_tipo=processo.tipo)
        if form.is_valid():
            #
            form.save()
            #
            return httprr('..', message='Período cadastrado com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('progressoes.change_processoprogressao')
def adicionar_avaliadores(request, periodo_id):
    periodo = get_object_or_404(ProcessoProgressaoPeriodo, pk=periodo_id)
    processo = periodo.processo_progressao
    #
    if processo.is_a_iniciar:
        if request.POST:
            if periodo.processo_progressao.is_tipo_progressao_merito:
                form = ProcessoProgressaoPeriodoAvaliadoresForm(request.POST, instance=periodo)
            elif periodo.processo_progressao.is_tipo_estagio_probatorio:
                form = EstagioProbatorioPeriodoAvaliadoresForm(request.POST, instance=periodo)
            #
            if form.is_valid():
                form.save()
                #
                return httprr('..', message='Avaliadores cadastrados com sucesso.')
        else:
            if processo.is_tipo_progressao_merito:
                form = ProcessoProgressaoPeriodoAvaliadoresForm(instance=periodo)
            elif processo.is_tipo_estagio_probatorio:
                form = EstagioProbatorioPeriodoAvaliadoresForm(instance=periodo)
        #
        if processo.is_tipo_progressao_merito:
            title = 'Adicionar/Editar Avaliadores do Período'
        else:
            title = 'Adicionar/Editar Avaliador do Período'
        #
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('progressoes.change_processoprogressao')
def editar_periodo(request, periodo_id):
    title = 'Editar Período'
    #
    periodo = get_object_or_404(ProcessoProgressaoPeriodo, pk=periodo_id)
    if periodo.processo_progressao.is_a_iniciar:
        form = ProcessoProgressaoPeriodoForm(request.POST or None, instance=periodo)
        if request.POST:
            if form.is_valid():
                form.save()
                return httprr('..', message='Período atualizado com sucesso.')
        #
        return locals()
    else:
        raise PermissionDenied


@permission_required('progressoes.change_processoprogressao')
def remover_periodo(request, periodo_id):
    periodo = get_object_or_404(ProcessoProgressaoPeriodo, pk=periodo_id)
    if periodo.processo_progressao.is_a_iniciar:
        # "guarda" o processo
        processo = periodo.processo_progressao
        # exclui o período
        periodo.delete()
        # recalcula média do processo
        processo.calcular_media_processo()

        return httprr('/progressoes/editar_processo/{:d}/'.format(periodo.processo_progressao_id), message='Período removido com sucesso.')
    else:
        raise PermissionDenied


@permission_required('progressoes.change_processoprogressao')
def liberar_avaliacoes(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)

    if processo.status == ProcessoProgressao.STATUS_A_INICIAR:
        periodos_validos, periodos_mensagem = processo.validar_periodos()
        if periodos_validos:
            processo.status = ProcessoProgressao.STATUS_EM_TRAMITE
            processo.save()

            # definindo o tipo do processo
            tipo_processo = "Avaliação de Desempenho"
            if processo.tipo == ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO:
                tipo_processo = "Estágio Probatório"

            assunto = "[SUAP] Processo de {}".format(tipo_processo)
            vinculos_avaliadores = processo.obter_vinculos_avaliadores(incluir_avaliado=False)
            url = '{}/progressoes/minhas_avaliacoes/?tab=0'.format(settings.SITE_URL)
            mensagem = '''
                <h1>Avaliação de Processo de {}</h1>
                <p>Você foi selecionado como avaliador no <strong>Processo de {}</strong> do servidor 
                <strong>{}</strong>.</p>
                <p>--</p>
                <p>Para responder a avaliação, acesse: <a href="{}">{}</a></p>
                '''.format(
                tipo_processo, tipo_processo, processo.avaliado.nome, url, url
            )
            if vinculos_avaliadores:
                send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, vinculos_avaliadores)

            # enviar e-mail de auto-avaliação apenas no processo de avaliação de desempenho
            if processo.tipo == ProcessoProgressao.TIPO_PROGRESSAO_MERITO:
                mensagem = '''
                    <h1>Avaliação de Processo de {}</h1>
                    <p>{}, o seu Processo de {} foi iniciado.</p>
                    <p>--</p>
                    <p>Para responder a autoavaliação, acesse: <a href="{}">{}</a></p>'''.format(
                    tipo_processo, processo.avaliado.nome, tipo_processo, url, url
                )
                if processo.avaliado:
                    send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [processo.avaliado.get_vinculo()])

            avaliacoes_liberadas = processo.obter_avaliacoes()
            for avaliacao_liberada in avaliacoes_liberadas:
                avaliacao_liberada.numero_liberacoes += 1  # incrementa o número de liberações
                avaliacao_liberada.save()
            return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message='Avaliações liberadas com sucesso. Os avaliadores foram notificados por email.')
        else:
            return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message=periodos_mensagem, tag='warning')
    else:
        return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message='Avaliações já liberadas.', tag='warning')


@permission_required('progressoes.change_processoprogressao')
def finalizar_processo(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)
    #
    if processo.pode_finalizar:
        finalizado, mensagem = processo.finalizar_processo()
        if finalizado:
            return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message=mensagem)
        else:
            return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message=mensagem, tag='warning')
    #
    return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message='Processo já finalizado ou ' 'ainda pendente.', tag='warning')


@permission_required('progressoes.change_processoprogressao')
def gerar_protocolo_processo_eletronico(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)
    if not processo.is_finalizado:
        raise PermissionDenied
    try:
        if 'processo_eletronico' in settings.INSTALLED_APPS:
            avaliacoes_pdf_content = imprimir_processo(request, processo_id).content

            file_tmp = None

            if settings.DEBUG:
                try:
                    # home do usuário (windows ou linux)
                    dir_home = expanduser("~")
                    file_tmp = join(dir_home, "progressao_processo_{}.pdf".format(processo_id))
                except Exception:
                    # padrão produção (linux)
                    file_tmp = "/tmp/progressao_processo_{}.pdf".format(processo_id)

            if not file_tmp:
                file_tmp = "/tmp/progressao_processo_{}.pdf".format(processo_id)

            avaliacoes_pdf_arquivo_em_disco = open(file_tmp, 'wb+')
            avaliacoes_pdf_arquivo_em_disco.write(avaliacoes_pdf_content)

            processo.gerar_processo_eletronico(avaliacoes_pdf_arquivo_em_disco)

            mensagem = 'Processo eletrônico gerado com sucesso.'
        else:
            processo.gerar_protocolo()

            mensagem = 'Protocolo gerado com sucesso.'
        return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message=mensagem)
    except Exception as erro:
        return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message=str(erro), tag='warning')


@rtr()
@permission_required('progressoes.change_processoprogressao')
def selecionar_protocolo_processo_eletronico(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)

    if not processo.is_finalizado:
        raise PermissionDenied

    if 'processo_eletronico' in settings.INSTALLED_APPS:
        form = SelecionarProcessoEletronicoForm(request.POST or None, instance=processo)
        processo_tipo = 'Processo Eletrônico'
    else:
        form = SelecionarProtocoloForm(request.POST or None, instance=processo)
        processo_tipo = 'Protocolo'

    title = 'Selecionar {}'.format(processo_tipo)

    if form.is_valid():
        form.save()
        return httprr('..', message='{} salvo.'.format(processo_tipo))

    return locals()


@permission_required('progressoes.change_processoprogressao')
def reabrir_processo(request, processo_id):
    #
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)
    #
    if processo.status == ProcessoProgressao.STATUS_FINALIZADO:
        processo.status = ProcessoProgressao.STATUS_EM_TRAMITE
        processo.save()
        return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message='Processo reaberto.')
    #
    return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message='Processo não finalizado.', tag='warning')


@permission_required('progressoes.change_processoprogressao')
def cancelar_tramite(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)

    if processo.status == ProcessoProgressao.STATUS_EM_TRAMITE:
        processo.status = ProcessoProgressao.STATUS_A_INICIAR
        processo.save()
        return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message='Processo com trâmite ' 'cancelado.')

    return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id), message='Processo não está em trâmite.', tag='warning')


@rtr()
@permission_required('progressoes.view_processoprogressao')
def meus_processos(request):
    title = 'Meus Processos'
    #
    avaliado = request.user.get_relacionamento()
    lista_processos = ProcessoProgressao.obter_processos_por_avaliado(avaliado)
    #
    return locals()


@rtr()
@permission_required('progressoes.view_processoprogressaoavaliacao')
def minhas_avaliacoes(request):
    title = 'Minhas Avaliações'

    # usuário logado
    usuario_logado = request.user.get_relacionamento()

    ##########################################
    # universo das avaliações (processos em tramite ou finalizados)

    # avaliações como avaliado
    lista_avaliacoes_como_avaliado = ProcessoProgressaoAvaliacao.avaliacoes_como_avaliado(usuario_logado).exclude(
        periodo__processo_progressao__status=ProcessoProgressao.STATUS_A_INICIAR
    )

    # avaliações como avaliador
    lista_avaliacoes_como_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_como_avaliador(usuario_logado).exclude(
        periodo__processo_progressao__status=ProcessoProgressao.STATUS_A_INICIAR
    )

    # avaliações como chefe
    lista_avaliacoes_como_chefe = ProcessoProgressaoAvaliacao.avaliacoes_como_chefe(usuario_logado).exclude(
        periodo__processo_progressao__status=ProcessoProgressao.STATUS_A_INICIAR
    )

    ##########################################
    # PENDENTES DE AVALIAÇÃO
    ############
    lista_avaliacoes_pendentes_avaliar = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_avaliar(qs_avaliacoes_como_avaliador=lista_avaliacoes_como_avaliador)

    ##########################################
    # AVALIADAS
    lista_avaliacoes_avaliadas = ProcessoProgressaoAvaliacao.avaliacoes_avaliadas(qs_avaliacoes_como_avaliador=lista_avaliacoes_como_avaliador).order_by('-data_avaliacao')

    ##########################################
    # PENDENTES DE ASSINATURA
    ############

    # pendentes de assinatura como avaliado
    lista_avaliacoes_pendentes_assinar_como_avaliado = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_avaliado(
        qs_avaliacoes_como_avaliado=lista_avaliacoes_como_avaliado
    ).filter(
        periodo__processo_progressao__status=ProcessoProgressao.STATUS_EM_TRAMITE  # processos em tramite
    )

    # pendentes de assinatura como avaliador
    lista_avaliacoes_pendentes_assinar_como_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_avaliador(
        qs_avaliacoes_como_avaliador=lista_avaliacoes_como_avaliador
    ).filter(
        periodo__processo_progressao__status=ProcessoProgressao.STATUS_EM_TRAMITE  # processos em tramite
    )

    # pendentes de assinatura como chefe
    lista_avaliacoes_pendentes_assinar_como_chefe = ProcessoProgressaoAvaliacao.avaliacoes_pendentes_a_assinar_como_chefe(
        qs_avaliacoes_como_chefe=lista_avaliacoes_como_chefe
    ).filter(
        periodo__processo_progressao__status=ProcessoProgressao.STATUS_EM_TRAMITE  # processos em tramite
    )

    # pendentes de assinatura (todas)
    lista_avaliacoes_pendentes_assinar = (
        (lista_avaliacoes_pendentes_assinar_como_avaliado | lista_avaliacoes_pendentes_assinar_como_avaliador | lista_avaliacoes_pendentes_assinar_como_chefe)
        .order_by('periodo__processo_progressao__avaliado__nome', 'avaliador__nome')
        .distinct()
    )

    # pendentes de assinatura por processo
    lista_avaliacoes_pendentes_assinar_por_processo = OrderedDict()  # {'id_processo': (processo, avaliacoes)}
    for avaliacao in lista_avaliacoes_pendentes_assinar:
        processo = avaliacao.periodo.processo_progressao
        if processo.id not in lista_avaliacoes_pendentes_assinar_por_processo:
            lista_avaliacoes_pendentes_assinar_por_processo[processo.id] = (processo, [])
        lista_avaliacoes_pendentes_assinar_por_processo[processo.id][1].append(avaliacao)

    ##########################################
    # ASSINADAS
    ############

    # assinadas como avaliado
    lista_avaliacoes_assinadas_como_avaliado = ProcessoProgressaoAvaliacao.avaliacoes_assinadas_como_avaliado(qs_avaliacoes_como_avaliado=lista_avaliacoes_como_avaliado)

    # assinadas como avaliador
    lista_avaliacoes_assinadas_como_avaliador = ProcessoProgressaoAvaliacao.avaliacoes_assinadas_como_avaliador(qs_avaliacoes_como_avaliador=lista_avaliacoes_como_avaliador)

    # assinadas como chefe
    lista_avaliacoes_assinadas_como_chefe = ProcessoProgressaoAvaliacao.avaliacoes_assinadas_como_chefe(qs_avaliacoes_como_chefe=lista_avaliacoes_como_chefe)

    # assinadas (todas)
    lista_avaliacoes_assinadas_todas = (lista_avaliacoes_assinadas_como_avaliado | lista_avaliacoes_assinadas_como_avaliador | lista_avaliacoes_assinadas_como_chefe).distinct()

    # ordena as avaliações assinadas pela última data de assinatura (são 3 assinaturas possíveis por avaliação)
    lista_avaliacoes_assinadas_temp = {}  # {key_data_assinatura: [última_data_assinatura, avaliacao], ...}
    for avaliacao_assinada in lista_avaliacoes_assinadas_todas:
        datas_assinatura = []
        if avaliacao_assinada in lista_avaliacoes_assinadas_como_avaliado:
            if avaliacao_assinada.data_assinatura_avaliado:
                datas_assinatura.append(avaliacao_assinada.data_assinatura_avaliado)
        if avaliacao_assinada in lista_avaliacoes_assinadas_como_avaliador:
            if avaliacao_assinada.data_assinatura_avaliador:
                datas_assinatura.append(avaliacao_assinada.data_assinatura_avaliador)
        if avaliacao_assinada in lista_avaliacoes_assinadas_como_chefe:
            if avaliacao_assinada.data_assinatura_chefe_imediato:
                datas_assinatura.append(avaliacao_assinada.data_assinatura_chefe_imediato)
        #
        if datas_assinatura:
            data_assinatura = max(datas_assinatura)
            key_data_assinatura = '{}_{}'.format(data_assinatura.strftime('%Y%m%d'), avaliacao_assinada.id)
        else:
            data_assinatura = None
            key_data_assinatura = '00000000_{}'.format(avaliacao_assinada.id)
        #
        lista_avaliacoes_assinadas_temp[key_data_assinatura] = [data_assinatura, avaliacao_assinada]

    lista_avaliacoes_assinadas = []  # [[última_data_assinatura, avaliacao], [última_data_assinatura, avaliacao], ...]
    for key_data_assinatura in sorted(list(lista_avaliacoes_assinadas_temp.keys()), reverse=True):
        lista_avaliacoes_assinadas.append(lista_avaliacoes_assinadas_temp[key_data_assinatura])

    return locals()


@rtr()
@permission_required('progressoes.view_avaliacaomodelo')
def avaliacao_modelo_visualizar(request, avaliacao_modelo_id):
    avaliacao = AvaliacaoModelo.objects.get(pk=avaliacao_modelo_id)
    title = 'Visualização de Modelo de Avaliação'
    return locals()


@rtr()
@permission_required('progressoes.change_processoprogressao')
def calcular_novos_processos(request):
    title = 'Novos Processos de Progressão'
    novos_processos = ProcessoProgressao.calcular_servidores_a_progredir()
    return locals()


@rtr()
@permission_required('progressoes.change_processoprogressao')
def recalcular_medias(request, processo_id):
    processo = get_object_or_404(ProcessoProgressao, pk=processo_id)
    #
    processo_periodos = processo.processoprogressaoperiodo_set.all()
    for processo_periodo in processo_periodos:
        processo_periodo.calcular_media_periodo()  # a média do processo também será atualizada
    #
    return httprr('/progressoes/editar_processo/{:d}/'.format(processo.id))
