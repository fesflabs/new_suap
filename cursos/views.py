# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal
from threading import Thread

from django.apps.registry import apps
from django.conf import settings
from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import ValidationError
from django.db.models.query_utils import Q
from django.http.response import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize

from comum.models import Ano
from cursos.enums import SituacaoParticipante, SituacaoCurso, TipoCurso
from cursos.forms import (
    ParticipanteForm,
    IndeferimentoParticipanteForm,
    AdicionarHorasTrabalhadasForm,
    RelatorioFinanceiroPagamentoGECCForm,
    CotaAnualServidorGECCForm,
    EditarMesPagamentoGECCForm,
    FiltroPendentesPagamentoForm,
)
from cursos.models import Curso, Participante
from djtools import layout
from djtools.choices import Meses
from djtools.templatetags.filters import in_group
from djtools.utils import rtr, httprr, documento, send_notification, get_session_cache
from rh.models import Servidor


@layout.info()
def index_infos(request):
    infos = list()

    hoje = datetime.today()
    if request.user.eh_servidor:
        servidor = request.user.get_relacionamento()
        qs_participante = Participante.objects.filter(servidor=servidor, mes_pagamento=hoje.month, curso__ano_pagamento=hoje.year)
        if qs_participante.exists():
            infos.append(dict(url='/cursos/horas_trabalhadas/', titulo='Há horas de cursos/concursos registradas para este mês.'))

    return infos


@layout.quadro('Cursos e Concursos', icone='marker', pode_esconder=True)
def index_quadros(quadro, request):
    def do():
        if request.user.eh_servidor:
            servidor_logado = request.user.get_relacionamento()
            if servidor_logado.eh_chefe_do_setor_hoje(servidor_logado.setor):
                qs_participante = (
                    Participante.objects.filter(situacao=SituacaoParticipante.AGUARDANDO_LIBERACAO)
                    .filter(Q(servidor__setor=servidor_logado.setor) | Q(servidor__setor__id__in=servidor_logado.setor.ids_descendentes))
                    .exclude(servidor=servidor_logado)
                )
                qtd = qs_participante.count()
                if qtd:
                    quadro.add_item(
                        layout.ItemContador(
                            titulo='Participante{0} de Curso{0}/Concurso{0}'.format(pluralize(qtd)),
                            subtitulo='Aguardando seu parecer',
                            qtd=qtd,
                            url='/admin/cursos/participante/?tab=tab_aguardando_chefia',
                        )
                    )

        if request.user.has_perm('rh.eh_rh_sistemico') or request.user.has_perm('rh.eh_rh_campus'):
            qs_gecc_pendente = Curso.objects.filter(situacao=SituacaoCurso.AGUARDANDO_CADASTRO_EM_FOLHA).count()
            if qs_gecc_pendente > 0:
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Curso{0}/Concurso{0}'.format(pluralize(qs_gecc_pendente)),
                        subtitulo='Aguardando cadastro em folha',
                        qtd=qs_gecc_pendente,
                        url='/admin/cursos/curso/?situacao__exact=3',
                    )
                )

        return quadro

    return get_session_cache(request, 'index_quadros_cursos', do, 24 * 3600)


@rtr()
@permission_required('cursos.view_curso')
def curso(request, id):
    curso = get_object_or_404(Curso, pk=id)
    title = str(curso)

    horas_previstas_total = curso.horas_previstas_total()
    horas_previstas_total_pendentes = curso.horas_previstas_total([SituacaoParticipante.PENDENTE])

    horas_trabalhadas_total = curso.horas_trabalhadas_total()
    horas_trabalhadas_total_pendentes = curso.horas_trabalhadas_total([SituacaoParticipante.PENDENTE])

    valor_total = curso.valor_total()
    valor_total_pendentes = curso.valor_total([SituacaoParticipante.PENDENTE])

    pode_iniciar_curso = _pode_iniciar_curso(curso, request)
    pode_finalizar_curso = _pode_finalizar_curso(curso, request)
    pode_adicionar_horas_participante = _pode_adicionar_horas_participante(curso, request)
    pode_gerenciar_participante = _pode_gerenciar_participante(curso, request)
    pode_informar_cadastro_folha = _pode_informar_cadastro_folha(curso, request)
    pode_liberar_participantes = _pode_liberar_participantes(request)
    pode_imprimir_listagem = curso.pode_imprimir_listagem()

    return locals()


@documento(enumerar_paginas=False)
@rtr()
@permission_required('cursos.view_curso')
def imprimir_listagem(request, curso_id):
    curso = get_object_or_404(Curso, pk=curso_id)

    return locals()


@rtr()
def adicionar_horas(request, id):
    title = 'Adicionar Horas Trabalhadas'
    instance = get_object_or_404(Participante, id=id)

    if not _pode_adicionar_horas_participante(instance.curso, request):
        return httprr('..', 'Você não tem permissão para adicionar horas.', 'error')

    form = AdicionarHorasTrabalhadasForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return httprr('..', 'Horas adicionadas com sucesso.')

    return locals()


@login_required()
@permission_required('cursos.delete_curso')
def curso_remover(request, id):
    curso = Curso.objects.get(id=id)
    if curso.pode_excluir_curso():
        curso.delete()
        return httprr('/admin/cursos/curso/', 'Curso/Concurso removido com sucesso.')
    return locals()


@rtr()
@login_required()
def editar_participante(request, participante_id):
    participante = get_object_or_404(Participante, id=participante_id)

    if not participante.curso.pode_gerenciar_participante(request.user):
        return httprr('..', 'Você não tem permissão para editar participantes.', 'error')

    title = 'Editar Participante {}'.format(participante.servidor)
    form = ParticipanteForm(request.POST or None, instance=participante)
    if form.is_valid():
        form.save()
        return httprr('..', 'Participante editado com sucesso.')
    return locals()


@login_required()
def curso_iniciar(request, id):
    try:
        curso = get_object_or_404(Curso, id=id)

        if not _pode_iniciar_curso(curso, request):
            return HttpResponseForbidden('Você não tem permissão para iniciar o curso.')

        curso.iniciar()
        return httprr(request.META.get('HTTP_REFERER'), 'Curso iniciado com sucesso.')
    except ValidationError as e:
        return httprr(request.META.get('HTTP_REFERER'), e.message, 'error')


@login_required()
def curso_finalizar(request, id):
    try:
        curso = get_object_or_404(Curso, id=id)

        if not _pode_finalizar_curso(curso, request):
            return httprr('..', 'Você não tem permissão para finalizar um curso.', 'error')

        curso.finalizar()
        return httprr(request.META.get('HTTP_REFERER'), 'Curso finalizado com sucesso.')
    except ValidationError as e:
        return httprr(request.META.get('HTTP_REFERER'), e.message, 'error')


@rtr('cursos/templates/tela_horas_trabalhadas.html')
@permission_required('cursos.pode_ver_seu_relatorio')
def horas_trabalhadas(request, matricula_servidor=None):
    logado = request.user.get_relacionamento()
    if (
        matricula_servidor
        and matricula_servidor != logado.matricula
        and not in_group(
            request.user, 'Coordenador de Gestão de Pessoas Sistêmico, Coordenador de Gestão de Pessoas, Operador de Gestão de Pessoas, Operador de Cursos e Concursos'
        )
    ):
        return HttpResponseForbidden()

    if not matricula_servidor:
        matricula_servidor = logado.matricula

    servidor = Servidor.objects.get(matricula=matricula_servidor)
    title = 'Horas Trabalhadas - {}'.format(servidor)

    dicionario = {}
    for participante in servidor.participante_set.filter(situacao=SituacaoParticipante.LIBERADO).order_by(
        '-curso__ano_pagamento__ano'
    ):
        dados = list()
        totais = {'hora': 0.0, 'valor': 0.0}
        if participante.curso.ano_pagamento.ano not in dicionario:
            dicionario[participante.curso.ano_pagamento.ano] = {'dados': dados, 'totais': totais}
        dict_dados = {
            'curso': participante.curso,
            'mes': Meses.get_mes(participante.mes_pagamento) if participante.mes_pagamento else '-',
            'atividade': participante.atividade.descricao,
            'valor_hora': participante.atividade.valor_hora,
            'qtd_horas_previstas': participante.horas_prevista,
            'qtd_horas': participante.horas_trabalhada,
            'valor_total': participante.valor_total,
        }
        dicionario.get(participante.curso.ano_pagamento.ano).get('dados').append(dict_dados)
        dicionario.get(participante.curso.ano_pagamento.ano).get('totais')['horas_prevista'] = Decimal(
            dicionario.get(participante.curso.ano_pagamento.ano).get('totais').get('horas_prevista') or 0
        ) + Decimal(participante.horas_prevista or 0)
        dicionario.get(participante.curso.ano_pagamento.ano).get('totais')['hora'] = Decimal(
            dicionario.get(participante.curso.ano_pagamento.ano).get('totais').get('hora') or 0
        ) + Decimal(participante.horas_trabalhada or 0)
        dicionario.get(participante.curso.ano_pagamento.ano).get('totais')['valor'] = Decimal(
            dicionario.get(participante.curso.ano_pagamento.ano).get('totais').get('valor') or 0
        ) + Decimal(participante.valor_total or 0)

    dicionario = sorted(dicionario.items())

    return locals()


@rtr()
@login_required()
def add_participante(request, curso_id):
    title = 'Adicionar um Participante'
    curso_concurso = get_object_or_404(Curso, id=curso_id)

    if not curso_concurso.pode_gerenciar_participante(request.user):
        return httprr('..', 'Você não tem permissão para adicionar participantes.', 'error')

    form = ParticipanteForm(request.POST or None, curso=curso_concurso)
    if form.is_valid():
        form.save()
        return httprr('..', 'Participante adicionado com sucesso.')

    return locals()


@rtr()
@login_required()
def remover_participante(request, participante_id):
    participante = get_object_or_404(Participante, id=participante_id)

    if not participante.curso.pode_gerenciar_participante(request.user):
        return httprr('..', 'Você não tem permissão para remover participantes.', 'error')

    participante.delete()
    return httprr(request.META.get('HTTP_REFERER'), 'Participante removido com sucesso.')


@rtr()
@login_required()
def deferir_participacao(request, participante_id):
    participante = get_object_or_404(Participante, id=participante_id)
    try:
        responsavel = request.user.get_relacionamento()
        participante.deferir_participacao(responsavel)

        # email
        titulo = '[SUAP] GECC: Participação em Curso/Concurso'
        texto = (
            '<h1>GECC: Participação em Curso/Concurso</h1>'
            '<h2>Participação deferida pela chefia imediata</h2>'
            '<p>{},</p>'
            '<p>Sua participação em <strong>{}</strong> foi deferida pela chefia imediata.</p>'.format(participante.servidor.nome, participante.curso.descricao)
        )

        t1 = Thread(send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [participante.servidor.get_vinculo()]))
        t1.start()

        return httprr(request.META.get('HTTP_REFERER'), 'A participação do(a) servidor(a) {} foi deferida com sucesso.'.format(participante.servidor))
    except ValidationError as e:
        return httprr(request.META.get('HTTP_REFERER'), e.message, 'error')


@rtr()
@login_required()
def indeferir_participacao(request, participante_id):
    title = 'Indeferimento de Participante'
    participante = get_object_or_404(Participante, id=participante_id)
    form = IndeferimentoParticipanteForm(request.POST or None, participante=participante)
    if form.is_valid():
        form.processar()
        return httprr('..', 'A participação do(a) servidor(a) {} foi indeferida.'.format(participante.servidor))

    return locals()


@login_required()
def informar_cadastro_folha(request, id):
    try:
        curso = get_object_or_404(Curso, id=id)

        if not _pode_informar_cadastro_folha(curso, request):
            return HttpResponseForbidden('Você não tem permissão para esta ação.')

        curso.informar_cadastro_folha(request)
        return httprr(request.META.get('HTTP_REFERER'), 'A ação foi realizada com sucesso.')
    except ValidationError as e:
        return httprr(request.META.get('HTTP_REFERER'), e.message, 'error')


@rtr()
@login_required()
@permission_required('cursos.pode_ver_relatorio_pagamento_gecc')
def relatorio_pagamento(request):
    title = 'Relatório Financeiro para Pagamento de GECC'

    form = RelatorioFinanceiroPagamentoGECCForm(request.POST or None)
    if form.is_valid():
        ano = form.cleaned_data.get('ano')
        mes = form.cleaned_data.get('mes')
        return httprr('/cursos/relatorio_pagamento_gecc_pdf/{}/{}/'.format(mes, ano))

    return locals()


@documento(enumerar_paginas=False)
@rtr()
@login_required()
@permission_required('cursos.pode_ver_relatorio_pagamento_gecc')
def relatorio_pagamento_gecc_pdf(request, mes, ano):
    mes_nome = Meses.get_mes(mes)
    ano = Ano.objects.get(ano=ano)

    relatorio = {}
    gecc_curso_valor = 0
    gecc_concurso_valor = 0
    gecc_atividade_extra_valor = 0
    gecc_total_valor = 0

    for p in Participante.objects.filter(mes_pagamento__isnull=False, mes_pagamento=mes, curso__ano_pagamento=ano).exclude(situacao=SituacaoParticipante.PENDENTE):
        if not relatorio.get(p.curso.campus.sigla):
            relatorio[p.curso.campus.sigla] = {}
            relatorio[p.curso.campus.sigla]['gecc_curso_valor'] = 0
            relatorio[p.curso.campus.sigla]['gecc_concurso_valor'] = 0
            relatorio[p.curso.campus.sigla]['gecc_atividade_extra_valor'] = 0
            relatorio[p.curso.campus.sigla]['gecc_total_valor'] = 0

        _valor_total = p.valor_total or 0

        if p.curso.tipo == TipoCurso.CURSO:
            relatorio[p.curso.campus.sigla]['gecc_curso_valor'] += _valor_total
            gecc_curso_valor += _valor_total

        if p.curso.tipo == TipoCurso.CONCURSO:
            relatorio[p.curso.campus.sigla]['gecc_concurso_valor'] += _valor_total
            gecc_concurso_valor += _valor_total

        if p.curso.tipo == TipoCurso.ATIVIDADE_EXTERNA:
            relatorio[p.curso.campus.sigla]['gecc_atividade_extra_valor'] += _valor_total
            gecc_atividade_extra_valor += _valor_total

        relatorio[p.curso.campus.sigla]['gecc_total_valor'] += _valor_total
        gecc_total_valor += _valor_total

    relatorio_final = dict()
    relatorio_final['gecc_curso_valor'] = gecc_curso_valor
    relatorio_final['gecc_concurso_valor'] = gecc_concurso_valor
    relatorio_final['gecc_atividade_extra_valor'] = gecc_atividade_extra_valor
    relatorio_final['gecc_total_valor'] = gecc_total_valor

    return locals()


@rtr()
@login_required()
def cota_anual_servidor(request):
    title = 'Cota Anual do Servidor'
    qs_participantes = Participante.objects.all().order_by('servidor__nome', 'curso__ano_pagamento__ano').distinct('servidor__nome', 'curso__ano_pagamento__ano')

    form = CotaAnualServidorGECCForm(request.GET or None)
    if form.is_valid():
        if form.cleaned_data.get('ano'):
            qs_participantes = qs_participantes.filter(curso__ano_pagamento=form.cleaned_data.get('ano'))
        if form.cleaned_data.get('texto_busca'):
            strings = form.cleaned_data.get('texto_busca').split(' ')
            for string in strings:
                qs_participantes = qs_participantes.filter(servidor__nome__icontains=string)

    return locals()


@rtr()
@login_required()
def liberar_participantes(request, curso_id):
    try:
        if not _pode_liberar_participantes(request):
            raise ValidationError('Você não tem permissão para executar esta ação.')

        curso = get_object_or_404(Curso, id=curso_id)
        #
        # consultando os participantes que ainda não foram liberados
        for p in curso.participante_set.filter(situacao=SituacaoParticipante.AGUARDANDO_LIBERACAO):
            #
            # se o participante tiver problemas com horas, NÃO será liberado automaticamente
            if p.problema_com_horas:
                continue
            p.situacao = SituacaoParticipante.LIBERADO
            p.data_liberacao = datetime.today()
            p.save()

        return httprr(request.META.get('HTTP_REFERER'), 'A ação foi realizada com sucesso.')
    except ValidationError as e:
        return httprr(request.META.get('HTTP_REFERER'), e.message, 'error')


@rtr()
@login_required()
def editar_mes_pagamento(request, participante_id):
    if not request.user.is_superuser:
        return httprr('..', 'Você não tem permissão para acessar esta funcionalidade.', 'error')

    participante = get_object_or_404(Participante, id=participante_id)
    title = 'Editar Mês de Pagamento - {}'.format(participante)
    form = EditarMesPagamentoGECCForm(request.POST or None, participante=participante)
    if form.is_valid():
        form.processar()
        return httprr('..', 'O mês de pagamento do participante {} foi atualizado com sucesso.'.format(participante.servidor))

    return locals()


@rtr()
@login_required()
def hora_prevista_to_hora_trabalhada(request, curso_id):
    try:
        curso = get_object_or_404(Curso, id=curso_id)
        if not _pode_adicionar_horas_participante(curso, request):
            raise ValidationError('Você não tem permissão para executar esta ação.')
        #
        # consultando os participantes que tem horas previstas
        for p in curso.participante_set.filter(horas_prevista__isnull=False):
            p.horas_trabalhada = p.horas_prevista
            p.save()

        return httprr(request.META.get('HTTP_REFERER'), 'A ação foi realizada com sucesso.')
    except ValidationError as e:
        return httprr(request.META.get('HTTP_REFERER'), e.message, 'error')


@rtr()
@login_required()
@permission_required('cursos.pode_informar_cadastro_em_folha')
def realizar_pagamento_participante_pendente(request, curso_id, participante_id):
    curso = get_object_or_404(Curso, id=curso_id)
    participante = get_object_or_404(Participante, id=participante_id)

    try:
        #
        # verificando permissão de acesso
        if not request.user.has_perm('cursos.pode_informar_cadastro_em_folha'):
            raise ValidationError('Você não tem permissão para acessar esta funcionalidade.')

        #
        # verificando se o participante passado está no curso que também foi passado
        tem_participante = curso.participante_set.filter(id=participante.id).exists()
        if not tem_participante:
            raise ValidationError('O participante {} não pertence ao curso {}.'.format(curso, participante))

        #
        # verificando se existe cronograma válido
        CronogramaFolha = apps.get_model('rh', 'CronogramaFolha')
        cronograma = CronogramaFolha.get_cronograma_hoje()
        if not cronograma:
            raise ValidationError('Não existe cadastrado um cronograma para fechamento de folha que seja válido para os cálculos de pagamento.')

        #
        # chamando rotina para atualizar participante
        Participante.gerencia_participantes_no_cadastro_em_folha(curso, [participante.id], cronograma, True)

        return httprr(request.META.get('HTTP_REFERER'), 'A ação foi realizada com sucesso.')
    except ValidationError as e:
        return httprr(request.META.get('HTTP_REFERER'), e.message, 'error')


@rtr()
@login_required()
@permission_required('cursos.pode_informar_cadastro_em_folha')
def participantes_pendentes_pagamento(request):
    title = 'Lista de Participantes com Pendência de Pagamento'
    participantes = Participante.pendentes.all()

    form = FiltroPendentesPagamentoForm(request.GET or None)
    if form.is_valid():
        if form.cleaned_data.get('participante'):
            participantes = participantes.filter(servidor__nome__icontains=form.cleaned_data.get('participante'))

        if form.cleaned_data.get('evento'):
            participantes = participantes.filter(curso__id=form.cleaned_data.get('evento'))

    return locals()


#################
# Permissões    #
#################
def _pode_iniciar_curso(curso, request):
    return curso.pode_iniciar_curso() and (curso.eh_responsavel(request.user.get_relacionamento()) or request.user.has_perm('cursos.pode_gerenciar_curso_concurso'))


def _pode_finalizar_curso(curso, request):
    return curso.pode_finalizar_curso() and (curso.eh_responsavel(request.user.get_relacionamento()) or request.user.has_perm('cursos.pode_gerenciar_curso_concurso'))


def _pode_adicionar_horas_participante(curso, request):
    return curso.pode_adicionar_horas_participante() and (curso.eh_responsavel(request.user.get_relacionamento()) or request.user.has_perm('cursos.pode_gerenciar_curso_concurso'))


def _pode_gerenciar_participante(curso, request):
    return curso.pode_gerenciar_participante(request.user)


def _pode_informar_cadastro_folha(curso, request):
    return curso.situacao == SituacaoCurso.AGUARDANDO_CADASTRO_EM_FOLHA and request.user.has_perm('cursos.pode_informar_cadastro_em_folha')


def _pode_liberar_participantes(request):
    return request.user.is_superuser
