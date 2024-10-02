import calendar
import collections
import csv
import json
import operator
import os
import subprocess
import tempfile
import urllib.parse
import zipfile
from builtins import sorted
from collections import OrderedDict
from datetime import date, datetime, timedelta
from functools import reduce
from os import stat
from os.path import exists
from xml.etree import ElementTree

from django.apps import apps
from django.apps import apps as apps_django
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.db import connection, transaction
from django.db.models import Q, Count, OuterRef, Subquery
from django.db.models.expressions import Case, F, Value, When
from django.db.models.fields import BooleanField
from django.db.models.functions import Coalesce
from django.http import (
    HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound,
    FileResponse, Http404, HttpResponse,
    HttpResponseRedirect
)
from django.shortcuts import get_object_or_404, render
from django.template import Context, Engine, TemplateDoesNotExist, loader
from django.template.defaultfilters import pluralize
from django.template.loader import get_template
from django.utils.encoding import force_str
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import ERROR_PAGE_TEMPLATE
from django.views.static import serve
from sentry_sdk import last_event_id, capture_exception

from catalogo_provedor_servico.utils import get_cpf_formatado
from comum.forms import (
    AdicionarUsuarioGrupoFormFactory,
    AlterarSenhaForm,
    AtualizarEmailForm,
    AutenticarDocumentoForm,
    AuthenticationFormPlus,
    CalendarioForm,
    CancelarReservasPeriodoForm,
    ComentarioForm,
    ConfiguracaoFormFactory,
    ExcluirRegistroForm,
    ExibirQuadrosForm,
    ExtracaoForm,
    IndisponibilizacaoSalaBuscarForm,
    InscricaoFiscalForm,
    MacroForm,
    MacroHistoricoPCAForm,
    OcupacaoPrestadorForm,
    RegistrarIndisponibilizacaoSalaForm,
    RejeitarSolicitacaoForm,
    ReservaInformarOcorrenciaForm,
    ReservaSalaCancelarForm,
    SalaIndicadoresForm,
    SetorAdicionarTelefoneForm,
    SolicitacaoReservaSalaAvaliarForm,
    SolicitacaoReservaSalaCancelarForm,
    SolicitacaoReservaSalaForm,
    SoliticarTrocarSenhaForm,
    VincularSetorUsuarioGrupoFormFactory, UsuarioExternoForm,
    AssinarDocumentoForm,
    VerificarDocumentoForm,
    ValidarDocumentoForm, DeviceForm, ContatoEmergenciaForm
)
from comum.models import (
    Ano,
    Comentario,
    Configuracao,
    DocumentoControle,
    DocumentoControleHistorico,
    DocumentoControleTipo,
    GerenciamentoGrupo,
    IndexLayout,
    IndisponibilizacaoSala,
    InscricaoFiscal,
    ManutencaoProgramada,
    OcupacaoPrestador,
    Pensionista,
    Predio,
    Preferencia,
    PrestadorServico,
    Publico,
    RegistroEmissaoDocumento,
    ReservaSala,
    Sala,
    SessionInfo,
    SetorTelefone,
    SolicitacaoReservaSala,
    TrocarSenha,
    User,
    UsuarioGrupo,
    RegistroNotificacao,
    PreferenciaNotificacao,
    CategoriaNotificacao,
    UsuarioGrupoSetor,
    Vinculo, UsuarioExterno, GroupDetail, Device, ContatoEmergencia)
from comum.utils import (
    FLAG_LOG_GERENCIAMENTO_GRUPO,
    formata_segundos,
    gera_nomes,
    get_uo,
    tem_permissao_informar_erro,
    somar_data)
from djtools import layout, documentos
from djtools.html.calendarios import Calendario
from djtools.management.permission import GroupPermission
from djtools.storages import get_temp_storage
from djtools.templatetags.filters import format_
from djtools.utils import CsvResponse, JsonResponse, get_client_ip, get_real_sql, get_rss_links, get_session_cache, \
    httprr, permission_required, rtr, get_view_name_from_url, PDFResponse, encrypt, decrypt, group_required
from djtools.utils.session import get_remote_session
from rh.models import PessoaFisica, Servidor, Setor, UnidadeOrganizacional
from comum import signer

URL_AZURE = 'https://portal.azure.com/#home'


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()

    servicos_anonimos.append(dict(categoria='Acessos', url="/accounts/login/", icone="lock", titulo='Login'))
    servicos_anonimos.append(dict(categoria='Acessos', url="/comum/solicitar_trocar_senha/", icone="key", titulo='Alterar Senha'))

    return servicos_anonimos


@layout.quadro('Reserva de Salas', icone='building', pode_esconder=True)
def index_quadros_salas(quadro, request):
    if request.user.has_perm('comum.pode_avaliar_solicitacao_reserva_de_sala'):
        solicitacoes_pendentes = request.user.salas_avaliadas.filter(
            solicitacaoreservasala__status=SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO).count()
        if solicitacoes_pendentes > 0:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Solicitaç{} de Sala'.format(pluralize(solicitacoes_pendentes, 'ão,ões')),
                    subtitulo='Para Avaliar',
                    qtd=solicitacoes_pendentes,
                    url='/admin/comum/solicitacaoreservasala/?tab=tab_solicitacoes_a_avaliar',
                )
            )

    return quadro


@layout.quadro('Calendário Administrativo', icone='calendar-alt', pode_esconder=True)
def index_quadros_calendario(quadro, request):
    def do():
        hoje = datetime.now()
        relacionamento = request.user.get_relacionamento()
        pessoa_fisica = request.user.get_vinculo().pessoa.pessoafisica
        if (pessoa_fisica.eh_servidor or pessoa_fisica.eh_prestador) and relacionamento.setor:
            ano = hoje.year
            mes = hoje.month
            cal = Calendario()
            if 'ponto' in settings.INSTALLED_APPS:
                from ponto.models import Liberacao

                [
                    cal.adicionar_evento_calendario(liberacao.data_inicio, liberacao.data_fim, liberacao.descricao,
                                                    liberacao.get_liberacao_css(), liberacao.descricao)
                    for liberacao in Liberacao.get_liberacoes_calendario(relacionamento.setor.uo, ano)
                ]

            if 'ferias' in settings.INSTALLED_APPS and pessoa_fisica.eh_servidor:
                from ferias.models import Ferias

                data_ini = date(ano, mes, 1)
                data_fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
                periodos = Ferias.get_periodos_pessoa_estava_de_ferias(relacionamento, data_ini, data_fim)
                [cal.adicionar_evento_calendario(periodo_ini, periodo_fim, label, 'ferias', label) for
                 periodo_ini, periodo_fim, label in periodos]

            if 'rh' in settings.INSTALLED_APPS:
                from rh.models import CronogramaFolha

                cronogramafolha = CronogramaFolha.objects.filter(mes=mes, ano__ano=ano)
                if cronogramafolha.exists():
                    cronogramafolha = cronogramafolha.first()
                    cal.adicionar_evento_calendario(
                        cronogramafolha.data_consulta_previa_folha,
                        cronogramafolha.data_consulta_previa_folha,
                        'Consulta da Prévia da Folha',
                        'extra4',
                        'Data da consulta da Prévia da Folha',
                    )
                    cal.adicionar_evento_calendario(
                        cronogramafolha.data_fechamento_processamento_folha,
                        cronogramafolha.data_fechamento_processamento_folha,
                        'Fechamento do SIAPE para Processamento da Folha',
                        'extra4',
                        'Data do fechamento do SIAPE para Processamento da Folha',
                    )
                    cal.adicionar_evento_calendario(
                        cronogramafolha.data_abertura_atualizacao_folha,
                        cronogramafolha.data_abertura_atualizacao_folha,
                        'Abertura do SIAPE para Atualização da Folha',
                        'extra4',
                        'Data da abertura do SIAPE para Atualização da Folha',
                    )
                    cal.adicionar_evento_calendario(
                        cronogramafolha.data_abertura_proxima_folha, cronogramafolha.data_abertura_proxima_folha,
                        'Abertura da Próxima Folha', 'extra4', 'Abertura da Próxima Folha'
                    )

            quadro.add_itens(
                [
                    layout.ItemCalendario(calendario=cal.formato_mes(ano, hoje.month)),
                    layout.ItemAcessoRapido(titulo='Calendário Anual', url='/comum/calendario_administrativo/'),
                ]
            )

        return quadro

    retorno = get_session_cache(request, 'index_quadros_calendario', do, 8 * 3600)
    return retorno


@layout.quick_access()
def index_quick_access(request):
    usuario_logado = request.user
    if not request.user or not request.user.is_authenticated:
        return []

    def do():
        quick_access = list()
        relacionamento = usuario_logado.get_relacionamento()

        if 'documents' in settings.ADMIN_QUICK_ACCESS:
            quick_access.append(
                dict(titulo='Meus Documentos SUAP', icone='file-pdf', url='/comum/documentos_emitidos_suap/'))
        if usuario_logado.eh_servidor:
            if 'webmail' in settings.ADMIN_QUICK_ACCESS:
                quick_access.append(dict(titulo='Webmail', icone='envelope',
                                         url=Configuracao.get_valor_por_chave('comum', 'url_webmail')))

            if 'groups' in settings.ADMIN_QUICK_ACCESS and GerenciamentoGrupo.user_can_manage(usuario_logado):
                quick_access.append(dict(titulo='Gerenciamento de Grupos', icone='users', url='/comum/gerenciamento_grupo/'))

            if 'microsoft_azure' in settings.ADMIN_QUICK_ACCESS and relacionamento.tem_acesso_servicos_microsoft():
                quick_access.append(
                    dict(titulo='Microsoft Azure', icone='windows fab', url=URL_AZURE))

        if 'google_classroom' in settings.ADMIN_QUICK_ACCESS:
            if (hasattr(relacionamento, 'email_google_classroom') and relacionamento.email_google_classroom) or \
                    usuario_logado.groups.filter(name='Usuários do Google Classroom').exists():
                quick_access.append(dict(titulo='Google Sala de Aula', icone='google fab',
                                         url='/ldap_backend/redirecionar_google_classroom/'))

        if 'phones' in settings.ADMIN_QUICK_ACCESS:
            quick_access.append(dict(titulo='Telefones', url='/comum/telefones/', icone='phone'))

        if 'scdp_siape' in settings.ADMIN_QUICK_ACCESS:
            if usuario_logado.has_perm('rh.pode_gerenciar_extracao_scdp') or usuario_logado.has_perm(
                    'rh.pode_gerenciar_extracao_siape'):
                quick_access.append(dict(titulo='Configurações', icone='cog', url='/comum/admin/'))

        if 'mobile' in settings.ADMIN_QUICK_ACCESS:
            quick_access.append(dict(titulo='SUAP Mobile (Android)',
                                     url='https://play.google.com/store/apps/details?id=br.edu.ifrn.suap.mobile',
                                     icone='mobile'))

        return quick_access

    retorno = get_session_cache(request, 'index_quick_access', do, 24 * 3600)
    return retorno


@layout.quadro('Manuais', icone='book', pode_esconder=True)
def index_quadros_manuais(quadro, request):
    def do():

        if bool(Configuracao.get_valor_por_chave('comum', 'quadro_manuais')) is True:
            if request.user.get_vinculo().eh_funcionario():
                if request.user.has_perm('ae.view_demandaalunoatendida'):
                    quadro.add_item(
                        layout.ItemAcessoRapido(titulo='Atividades Estudantis: <strong>Serviço Social</strong>',
                                                url='/manuais/ae/servico_social/index.html'))

                if request.user.groups.filter(name='Coordenador de Atividades Estudantis').exists():
                    quadro.add_item(
                        layout.ItemAcessoRapido(titulo='Atividades Estudantis: <strong>Coordenação</strong>',
                                                url='/manuais/ae/coordenacao/index.html'))

                if 'pdi' in settings.INSTALLED_APPS:
                    quadro.add_item(
                        layout.ItemAcessoRapido(titulo='Desenvolvimento Institucional: <strong>PDI</strong>',
                                                url='/manuais/des_institucional/pdi/index.html'))

                if request.user.groups.filter(name='Servidor').exists():
                    if 'projetos' in settings.INSTALLED_APPS:
                        quadro.add_item(layout.ItemAcessoRapido(titulo='Extensão: <strong>Projetos</strong>',
                                                                url='/manuais/projetos/extensao/index.html'))

                    if 'pesquisa' in settings.INSTALLED_APPS:
                        quadro.add_item(layout.ItemAcessoRapido(titulo='Pesquisa: <strong>Projetos</strong>',
                                                                url='/manuais/projetos/pesquisa/pesquisa/index.html'))
                    if 'documento_eletronico' in settings.INSTALLED_APPS:
                        quadro.add_item(
                            layout.ItemAcessoRapido(titulo='Administração: <strong>Documento Eletrônico</strong>',
                                                    url='/manuais/admin/documento_eletronico/index.html')
                        )
                    if 'processo_eletronico' in settings.INSTALLED_APPS:
                        quadro.add_item(
                            layout.ItemAcessoRapido(titulo='Administração: <strong>Processo Eletrônico</strong>',
                                                    url='/manuais/admin/processo_eletronico/index.html'))

                if (
                        request.user.has_perm('arquivo.pode_fazer_upload_arquivo')
                        or request.user.has_perm('arquivo.pode_identificar_arquivo')
                        or request.user.has_perm('arquivo.pode_validar_arquivo')
                ):
                    quadro.add_item(layout.ItemAcessoRapido(titulo='Gestão de Pessoas', url='/manuais/rh/index.html'))

        return quadro

    retorno = get_session_cache(request, 'index_quadros_manuais', do, 24 * 3600)
    return retorno


@rtr()
@login_required
def index(request):
    if request.user.is_superuser and not request.user.get_profile():
        return httprr('/comum/admin/')
    timeout = 5 * 60
    contexto = dict()

    # Definindo variáveis para evitar ir repetidas vezes no banco de dados
    user_groups = request.user.groups.values_list('name', flat=1)

    is_secretario_edu = 'Secretário Acadêmico' in user_groups

    if is_secretario_edu and 'edu' in settings.INSTALLED_APPS:
        from edu.views import contexto_painel_controle

        contexto['painel_controle'] = contexto_painel_controle(request)

    def index_alertas_sessao():
        retorno = []
        for _, data in layout.index_alertas_data.send(sender=index, request=request):
            retorno.extend(data)
        return retorno

    alertas = get_session_cache(request, 'index_alertas_data', index_alertas_sessao, timeout)

    def index_infos_sessao():
        retorno = []
        for _, data in layout.index_infos_data.send(sender=index, request=request):
            retorno.extend(data)
        return retorno

    infos = get_session_cache(request, 'index_infos_data', index_infos_sessao, timeout)

    def index_inscricoes_sessao():
        retorno = []
        for _, data in layout.index_inscricoes_data.send(sender=index, request=request):
            retorno.extend(data)
        return retorno

    inscricoes = index_inscricoes_sessao()

    def index_atualizacoes_sessao():
        retorno = []
        for _, data in layout.index_atualizacoes_data.send(sender=index, request=request):
            retorno.extend(data)
        return retorno

    atualizacoes = get_session_cache(request, 'index_atualizacoes_data', index_atualizacoes_sessao, timeout)

    dict_quadros = {}
    tem_quadro_escondido = False
    # Quadros centrais não podem ser cacheados automaticamente
    for _, quadro in layout.index_quadros_data.send(sender=index, request=request):
        if quadro:
            if quadro.has_items():
                dict_quadros[quadro.titulo.upper()] = quadro
        else:
            tem_quadro_escondido = True

    quadros = collections.OrderedDict()
    quadros['esquerda'] = list()
    quadros['centro'] = list()
    quadros['direita'] = list()
    layouts_salvos = IndexLayout.get_layouts_usuario(request)

    for chave, quadro_layout in layouts_salvos.items():
        if chave in dict_quadros and quadro_layout and not quadro_layout.get('escondido', False):
            if quadro_layout['coluna'] == 1:
                quadros['esquerda'].append(dict_quadros[chave.upper()])
            elif quadro_layout['coluna'] == 2:
                quadros['centro'].append(dict_quadros[chave.upper()])
            else:
                quadros['direita'].append(dict_quadros[chave.upper()])
            del dict_quadros[chave]

    hoje = datetime.now()

    data_manutencao = None
    previsao_horario_fim_manutencao = None
    if request.GET.get('esconder_manutencao', None) or request.session.get('esconder_manutencao'):
        request.session['esconder_manutencao'] = True
        manutencao = None
    else:
        manutencao = ManutencaoProgramada.proxima_notificacao()
        if manutencao:
            if manutencao.data_hora_atualizacao.date() == hoje.date():
                data_manutencao = 'hoje'
            else:
                data_manutencao = 'no dia {}'.format(manutencao.data_hora_atualizacao.strftime('%d/%m/%Y'))
            previsao_horario_fim_manutencao = manutencao.data_hora_atualizacao + timedelta(
                minutes=manutencao.previsao_minutos_inatividade)

    contexto['infos'] = infos
    contexto['alertas'] = alertas
    contexto['inscricoes'] = inscricoes
    contexto['atualizacoes'] = atualizacoes
    contexto['is_secretario_edu'] = is_secretario_edu
    contexto['quadros'] = quadros
    contexto['title'] = 'Início'
    contexto['tem_quadro_escondido'] = tem_quadro_escondido
    contexto['manutencao'] = manutencao
    contexto['data_manutencao'] = data_manutencao
    contexto['previsao_horario_fim_manutencao'] = previsao_horario_fim_manutencao

    return contexto


@rtr()
@login_required()
@permission_required('comum.change_prestadorservico')
def visualizar_publico(request, id):
    publico = get_object_or_404(Publico, pk=id)
    try:
        lista_publico = publico.get_queryset().all()
    except Exception as e:
        return httprr('/admin/comum/publico/', f'Ocorreu um erro ao realizar a consulta: {str(e)}', 'error')

    return locals()


def feed_noticias(request):
    timeout = 3600
    if Configuracao.get_valor_por_chave('comum', 'url_rss'):
        if not cache.get('feed_noticias'):
            try:
                rss_links = get_rss_links(Configuracao.get_valor_por_chave('comum', 'url_rss'))
                t = get_template('comum/templates/rss.html')
                cache.set('feed_noticias', t.render(dict({'rss_links': rss_links})), timeout)
            except Exception:
                cache.set('feed_noticias', '', timeout)
        return HttpResponse(cache.get('feed_noticias'))
    return HttpResponse('')


@login_required()
def docs(request, path, tipo):
    # é servidor/prestador?
    vinculo = request.user.get_vinculo()
    if not vinculo.eh_servidor() and not vinculo.eh_prestador():
        raise PermissionDenied("Acesso negado.")

    # se não informou qual arquivo abrir sugere index.html
    if len(path) == 0:
        path = "index.html"

    return serve(request, path, os.path.join(settings.BASE_DIR, f"docs/{tipo}/.build/html/"), False)


@rtr()
@login_required()
def telefones(request):
    title = "Telefones"
    eh_aluno = request.user.get_vinculo().eh_aluno()
    setores = Setor.objects.filter(uo__isnull=False).order_by('uo__setor__sigla', 'sigla')
    campi = UnidadeOrganizacional.objects.suap().all().order_by('setor__sigla')
    return locals()


@rtr()
@login_required()
def telefones_csv(request):
    rows = [['Campus', 'Setor Nome', 'Setor Sigla', 'Telefone', 'Ramal']]
    for setortelefone in SetorTelefone.objects.all():
        rows.append([setortelefone.setor.uo, setortelefone.setor.nome, setortelefone.setor.sigla, setortelefone.numero,
                     setortelefone.ramal])

    return CsvResponse(rows)


@rtr()
def admin(request):
    title = 'Administração do SUAP'
    if not (request.user.has_perm('rh.pode_gerenciar_extracao_siape') or request.user.has_perm(
            'rh.pode_gerenciar_extracao_scdp')):
        raise PermissionDenied()
    if Configuracao.get_valor_por_chave("comum", 'instituicao_anterior_identificador'):
        codigos_instituicoes = [codigo_instituicao.strip() for codigo_instituicao in
                                Configuracao.get_valor_por_chave("comum", 'instituicao_anterior_identificador').split(
                                    ';')]

    superusers = User.objects.filter(is_superuser=True).count()

    # Preferencias
    tres_meses = datetime.now() - timedelta(days=90)
    preferencias = Preferencia.objects.filter(usuario__is_active=True, usuario__last_login__gte=tres_meses).aggregate(
        tema_padrao=Count('pk', filter=Q(tema=Preferencia.PADRAO)),
        tema_dunas=Count('pk', filter=Q(tema=Preferencia.DUNAS)),
        tema_aurora=Count('pk', filter=Q(tema=Preferencia.AURORA)),
        tema_luna=Count('pk', filter=Q(tema=Preferencia.LUNA)),
        tema_govbr=Count('pk', filter=Q(tema=Preferencia.GOVBR)),
        tema_alto_contraste=Count('pk', filter=Q(tema=Preferencia.ALTO_CONSTRASTE)),
        tema_ifs=Count('pk', filter=Q(tema=Preferencia.IFS)),
        somente_via_suap=Count('pk', filter=Q(via_suap=True, via_email=False)),
        somente_via_email=Count('pk', filter=Q(via_suap=False, via_email=True)),
        via_ambos=Count('pk', filter=Q(via_suap=True, via_email=True)),
    )
    tema_padrao = preferencias['tema_padrao']
    tema_dunas = preferencias['tema_dunas']
    tema_aurora = preferencias['tema_aurora']
    tema_luna = preferencias['tema_luna']
    tema_govbr = preferencias['tema_govbr']
    tema_alto_contraste = preferencias['tema_alto_contraste']
    tema_ifs = preferencias['tema_ifs']
    somente_via_suap = preferencias['somente_via_suap']
    somente_via_email = preferencias['somente_via_email']
    via_ambos = preferencias['via_ambos']
    total_novos_temas = tema_dunas + tema_aurora + tema_luna + tema_govbr + tema_alto_contraste + tema_ifs
    if not tema_padrao and total_novos_temas == 0:
        total_tema = None
    else:
        total_tema = f'{(total_novos_temas * 100) / (tema_padrao + total_novos_temas):.2f}'

    # Dados sobre o sistema
    out, err = subprocess.Popen(f'cd {settings.BASE_DIR}; git status --porcelain -uno', shell=True,
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE).communicate()
    out = out.decode('utf-8')
    git_info = out.split('\n')[0]

    out, err = subprocess.Popen(f'cd {settings.BASE_DIR}; git log -n 1', shell=True, stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE).communicate()
    out = out.decode('utf-8')
    git_info += '\n\n' + out
    crontab, err = subprocess.Popen('crontab -l', stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    shell=True).communicate()
    return locals()


@rtr()
@login_required()
def maquinas(request):
    title = 'Situação das Máquinas Ativas'

    if not request.user.is_superuser:
        raise PermissionDenied('Você não tem permissão de acesso a essa página')
    from ponto.models import Maquina

    """
    relatorio = {
        "uo": {'inativas':[], 'ativas':[], 'uo_nome':nome},
    }
    """
    relatorio = {}

    maquinas_sem_log = Maquina.objects.select_related("uo", "uo__setor").filter(ativo=True, ultimo_log__isnull=True)
    maquinas_com_log = Maquina.objects.select_related("uo", "uo__setor").filter(ativo=True).exclude(
        ultimo_log__isnull=True)

    for maquina in maquinas_sem_log:
        if maquina.uo not in relatorio:
            relatorio[maquina.uo] = {'inativas': [], 'ativas': [], 'uo_nome': maquina.uo}
        relatorio[maquina.uo]['inativas'].append(maquina)

    for maquina in maquinas_com_log:
        if maquina.uo not in relatorio:
            relatorio[maquina.uo] = {'inativas': [], 'ativas': [], 'uo_nome': maquina.uo}
        relatorio[maquina.uo]['ativas'].append(maquina)

    return dict(title=title, relatorio=relatorio, qtd_maquinas_com_log=maquinas_com_log.count,
                qtd_maquinas_sem_log=maquinas_sem_log.count)


@rtr()
@login_required()
def configuracao(request):
    if not request.user.is_superuser:
        raise PermissionDenied()
    FormClass = ConfiguracaoFormFactory()
    form = FormClass(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return httprr('.', 'Configuração salva com sucesso.')
    return dict(form=form)


@rtr()
@login_required()
@permission_required('rh.pode_gerenciar_extracao_siape')
def baixar_macro_siape_personalizavel(request):
    title = 'Baixar macro SIAPE'
    form = MacroForm(request.POST or None)
    if form.is_valid():
        uf = Configuracao.get_valor_por_chave("comum", 'instituicao_estado').lower()
        cod_instituicao = Configuracao.get_valor_por_chave("comum", 'instituicao_identificador')
        if not uf or not cod_instituicao:
            return HttpResponse("Defina UF e o Código da Instituição.")
        t = get_template('comum/templates/baixar_macro_siape.mac')
        template_compilado = t.render(dict({"cod_instituicao": cod_instituicao, "uf": uf}))

        arquivos_extrator = form.cleaned_data['arquivos_extrator']

        entryscreen = 'unidadeorganizacional1'
        exitscreen = 'historicosetorfim'
        root = ElementTree.fromstring(template_compilado)
        if not 'unidadeorganizacional' in arquivos_extrator:
            entryscreen = f'{arquivos_extrator[0]}1'
            root[0].attrib['entryscreen'] = 'false'
        if not 'historicosetor' in arquivos_extrator:
            exitscreen = f'{arquivos_extrator[-1]}fim'
            root[-1].attrib['exitscreen'] = 'false'

        telas_finais = [f'{tela}fim' for tela in arquivos_extrator]

        for screen in root.iter('screen'):
            if entryscreen and screen.attrib['name'] == entryscreen:
                screen.attrib['entryscreen'] = 'true'
            if exitscreen and screen.attrib['name'] == exitscreen:
                screen.attrib['exitscreen'] = 'true'

            if screen.attrib['name'] in telas_finais and screen.attrib['name'] != exitscreen:
                screen[-1][0].attrib['name'] = telas_finais[telas_finais.index(screen.attrib['name']) + 1].replace(
                    'fim', '1')
        response = HttpResponse(ElementTree.tostring(root), content_type='plain/mac')
        response['Content-Disposition'] = 'attachment; filename=macro_siape.mac'
        return response
    return locals()


@rtr()
@login_required()
@permission_required('rh.pode_gerenciar_extracao_siape')
def baixar_macro_siape(request):
    uf = Configuracao.get_valor_por_chave("comum", 'instituicao_estado').lower()
    cod_instituicao = Configuracao.get_valor_por_chave("comum", 'instituicao_identificador')
    if not uf or not cod_instituicao:
        return HttpResponse("Defina Uf e o código da instituição")
    t = get_template('comum/templates/baixar_macro_siape.mac')
    if "instituicao_anterior" in request.GET:
        cod_instituicao = request.GET['instituicao_anterior']
        t = get_template('comum/templates/baixar_macro_pca.mac')
    if "extracao_sem_posicionamentos_que_estejam_sem_documento_legal" in request.GET:
        t = get_template('comum/templates/baixar_macro_pca_sem_documento_legal.mac')
    response = HttpResponse(t.render(dict({"cod_instituicao": cod_instituicao, "uf": uf})), content_type='plain/mac')
    response['Content-Disposition'] = 'attachment; filename=macro_siape.mac'
    return response


@rtr()
@login_required()
@permission_required('rh.pode_gerenciar_extracao_siape')
def baixar_macro_siape_historico_pca(request):
    title = "Macro para recuperar históricos de PCAs dos servidores"
    form = MacroHistoricoPCAForm(request.POST or None)
    if form.is_valid():
        t = get_template('comum/templates/baixar_macro_historico_pca.mac')
        servidores = form.cleaned_data.get('servidores')
        matriculas = servidores.values_list('matricula_sipe', flat=True)
        primeira_matricula = matriculas[0]
        response = HttpResponse(
            t.render(dict({"primeira_matricula": primeira_matricula, "matriculas": matriculas[1:]})),
            content_type='plain/mac')
        response['Content-Disposition'] = 'attachment; filename=macro_siape.mac'
        return response

    return locals()


@rtr()
@permission_required('rh.pode_gerenciar_setor_telefone')
def setor_adicionar_telefone(request, objeto_pk):
    setor = Setor.todos.get(pk=objeto_pk)
    form = SetorAdicionarTelefoneForm(request.POST or None)
    if form.is_valid():
        SetorTelefone.objects.create(setor=setor, numero=form.cleaned_data['numero'], ramal=form.cleaned_data['ramal'],
                                     observacao=form.cleaned_data['observacao'])
        return httprr('.', 'Telefone adicionado com sucesso.')
    else:
        return locals()


@rtr()
@permission_required('rh.pode_gerenciar_setor_telefone')
def setor_remover_telefone(request, objeto_pk):
    telefone = SetorTelefone.objects.get(pk=objeto_pk)
    setor_pk = telefone.setor.pk
    telefone.delete()
    return httprr('/comum/setor_adicionar_telefone/%d/' % setor_pk, 'Telefone removido com sucesso.')


@rtr()
@login_required()
def adicionar_contato_de_emergencia(request, pessoa_fisica_pk):
    pessoa_fisica = get_object_or_404(PessoaFisica, pk=pessoa_fisica_pk)
    title = 'Novo Contato de Emergência de {}'.format(pessoa_fisica.nome)
    verificacao_propria = request.user.get_vinculo().eh_servidor() and request.user == pessoa_fisica.user
    if not request.user.has_perm('comum.view_contatoemergencia') and not verificacao_propria:
        raise PermissionDenied
    form = ContatoEmergenciaForm(request.POST or None)
    form.instance.pessoa_fisica = pessoa_fisica
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return httprr('..', 'Contato adicionado com sucesso.')
    return locals()


@rtr()
@login_required()
def listar_contatos_de_emergencia(request, pessoa_fisica_pk):
    pessoa_fisica = get_object_or_404(PessoaFisica, pk=pessoa_fisica_pk)
    contatos = ContatoEmergencia.objects.filter(pessoa_fisica=pessoa_fisica)
    title = 'Contatos de Emergência de {}'.format(pessoa_fisica.nome)
    verificacao_propria = request.user.get_vinculo().eh_servidor() and request.user == pessoa_fisica.user
    pode_gerenciar_contatos = (
        request.user.has_perm('comum.add_contatoemergencia')
        or request.user.has_perm('comum.change_contatoemergencia')
        or request.user.has_perm('comum.delete_contatoemergencia')
        or verificacao_propria
    )
    if not pode_gerenciar_contatos:
        raise PermissionDenied

    return locals()


@rtr()
@login_required()
def fiscal_concurso(request):
    servidor = request.user.get_relacionamento()
    if InscricaoFiscal.objects.filter(servidor=servidor):
        return httprr('/', 'Sua inscrição já foi realizada.')
    if request.method == 'POST':
        form = InscricaoFiscalForm(request.POST, servidor=servidor)
        if form.is_valid():
            form.save()
            return httprr('/', 'Inscrição realizada com sucesso.')
    else:
        form = InscricaoFiscalForm()
    return locals()


def gerar_cvs(request, id_documentocontroletipo):
    documentocontroletipo = DocumentoControleTipo.objects.get(id=id_documentocontroletipo)
    documentoscontroles = DocumentoControle.objects.select_related(
        'solicitante_vinculo', 'solicitante_vinculo__setor', 'solicitante_vinculo__id_relacionamento',
        'solicitante_vinculo__tipo_relacionamento'
    ).filter(documento_tipo=documentocontroletipo, ativo=True)

    controle_csv = HttpResponse(content_type='text/csv')
    controle_csv['Content-Disposition'] = 'attachment; filename=documento_controle.csv'

    writer = csv.writer(controle_csv)
    writer.writerow(['Tipo do Documento', 'Identificação do Documento', 'Matrícula', 'Nome', 'Campus', 'Setor'])

    for documentocontrole in documentoscontroles:
        campus = ''
        if documentocontrole.vinculo_solicitante.setor:
            campus = documentocontrole.vinculo_solicitante.setor.uo
            writer.writerow(
                [
                    documentocontroletipo,
                    documentocontrole.documento_id,
                    documentocontrole.vinculo_solicitante.relacionamento.matricula,
                    documentocontrole.vinculo_solicitante.pessoa.nome,
                    campus,
                    documentocontrole.vinculo_solicitante.setor,
                ]
            )

    return controle_csv


def formatar_ref(arquivo_ref):
    campos = []
    posicao = 1
    for i in arquivo_ref:
        descricao = i[:40].strip()
        tipo = i[40]
        tamanho_int = sum(int(n) for n in i[41:].split(','))
        campos.append(dict(descricao=descricao, tipo=tipo, tamanho=i[41:], tamanho_int=tamanho_int, inicio=posicao - 1,
                           fim=posicao + tamanho_int - 1))  # tamanho puro
        posicao = posicao + tamanho_int
    return campos


def get_itens(arquivo_txt, ref, busca_texto):
    """
    Retorna listagem de itens/linhas do arquivo siafe que contêm o texto buscado.
    Caso o texto seja vazio, a listagem inteira é retornada
    """
    itens = []
    for linha in arquivo_txt:
        linha_decodificada = linha.decode('latin-1')
        linha_decodificada = linha_decodificada.strip()
        if busca_texto.lower() in linha_decodificada.lower():
            item = dict()
            item['conteudo_puro'] = linha_decodificada
            for campo in ref:
                item[campo['descricao']] = linha_decodificada[campo['inicio']: campo['fim']].strip()
            itens.append(item)

    return itens


###########################################
# VISUALIZAÇÃO DE ARQUIVOS SIAFE ##########
###########################################


@rtr()
@login_required()
def ver_arquivo_siafi(request):
    if request.method == 'POST':
        form = ExtracaoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_1 = request.FILES['arquivo_1']
            arquivo_2 = request.FILES['arquivo_2']
            texto = form.cleaned_data['campo_busca'].strip()
            ref = formatar_ref(arquivo_1)
            itens = get_itens(arquivo_2, ref, texto)
            arquivo = arquivo_2.name
            request.session['ref'] = ref
            request.session['itens'] = itens
            request.session['arquivo'] = arquivo
    else:
        form = ExtracaoForm()
        if "page" in request.GET:
            ref = request.session['ref']
            itens = request.session['itens']
            arquivo = request.session['arquivo']

    return locals()


##################################################################
# Funções para o terminal de chaves, ponto e cadastro de digital #
##################################################################


def get_chave_publica_suap(request):
    """
    Esta view é executada na instalação do terminal de ponto para habilitar o
    acesso SSH sem senha a partir do servidor do SUAP.
    """
    chave_publica = Configuracao.get_valor_por_chave('comum', 'chave_publica')
    response = HttpResponse(chave_publica, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=suap-chave-publica.pub'
    return response


def get_pessoa(request, username, versao=None):
    # Ainda falta desconsiderar as uos caso seja ead
    return get_dump_pessoas(request, username, versao)


def get_pessoas(request, versao=None):
    return get_dump_pessoas(request, None, versao)


@transaction.atomic
def get_dump_pessoas(request, username, versao=None):
    from ponto.models import Maquina, MaquinaLog, VersaoTerminal

    try:
        m = Maquina.objects.get(ip=get_client_ip(request), ativo=True)
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')

    if versao:
        m.versao_terminal = VersaoTerminal.objects.get_or_create(numero=versao)[0]
        m.save()

    ARQUIVO_DUMP = '/tmp/tabela_pessoas-%d.zip' % m.id
    if exists(ARQUIVO_DUMP) and datetime.fromtimestamp(stat(ARQUIVO_DUMP)[-1]).date() == datetime.today():
        # Se existe um arquivo gerado no dia, este não precisa ser criado
        pass

    else:
        # Não existe arquivo gerado no dia, então precisa ser criado
        cursor = connection.cursor()

        query = obter_query(versao, username, m.uo_id)
        cursor.execute(query)

        # Gerando o dump
        dump_file = open('/tmp/tabela_terminal.copy', 'w')
        cursor.copy_to(dump_file, 'tabela_terminal_ponto')
        dump_file.close()

        # Removendo tabela temporária
        cursor.execute('DROP TABLE tabela_terminal_ponto')

        # Compactando o dump
        zip_file = zipfile.ZipFile(ARQUIVO_DUMP, 'w', zipfile.ZIP_DEFLATED)
        zip_file.write('/tmp/tabela_terminal.copy', 'tabela_terminal.copy')
        zip_file.close()

    # Abrindo o arquivo zipado
    dump_zip_file = open(ARQUIVO_DUMP, 'rb')
    conteudo_dump = dump_zip_file.read()
    dump_zip_file.close()

    MaquinaLog.objects.create(maquina=m, operacao='comum_get_dump_pessoas')

    response = HttpResponse(conteudo_dump, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=dump_terminal.zip'
    return response


def obter_query(versao, username, uo_id):
    def ajustar_colunas(sql, versao):
        extras = ''
        if versao >= '1.2.0':
            extras = '''
                "pf"."pf_pode_bater_ponto" as "pode_bater_ponto",
                "pf"."pf_senha_ponto" as "senha_ponto",
            '''
        query = '''
            SELECT
              "pf"."pf_id" as "id",
              "pf"."pf_username" as "username",
              "pf"."pf_nome" as "nome",
              "pf"."pf_setor_sigla" as "setor",
              "pf"."pf_campus_sigla" as "campus",
              "pf"."pf_template" as "template",
              "pf"."pf_tem_digital_fraca" as "tem_digital_fraca",
              "pf"."pf_operador_chaves" as "operador_chave",
              "pf"."pf_operador_cadastro" as "operador_cadastro",
              {}
              "pf"."exportada"
            FROM ({}) as "pf"'''.format(
            extras, sql
        )
        return query

    from rh.models import Funcionario

    filters_funcionario = [Q(excluido=False), Q(username__isnull=False)]
    filters_aluno = [Q(pessoa_fisica__username__isnull=False), Q(situacao__ativo=True)]
    if username:
        filters_funcionario.append(Q(username=username))
        # no caso de um novo prestador de serviço que vai precisar cadastrar a digital
        filters_funcionario.append(Q(prestadorservico__ativo=True) | Q(prestadorservico__ativo=None))
        filters_aluno.append(Q(pessoa_fisica__username=username))
        campi_ead = UnidadeOrganizacional.objects.suap().filter(tipo=UnidadeOrganizacional.TIPO_CAMPUS_EAD).values_list(
            'id', flat=True)
        filters_aluno.append(
            Q(curso_campus__diretoria__setor__uo__id__in=campi_ead) | Q(curso_campus__diretoria__setor__uo__id=uo_id))
    else:
        filters_funcionario.append((Q(prestadorservico__ativo=True) & Q(prestadorservico__template__isnull=False)) | Q(
            prestadorservico__isnull=True))
        filters_aluno.append(Q(curso_campus__diretoria__setor__uo__id=uo_id))

    selects_funcionario = {'exportada': True}
    selects_aluno = {'exportada': True, 'pf_operador_cadastro': False, 'pf_operador_chaves': False}

    operadores_chave = User.objects.filter(
        groups__name__in=['Operador de Chaves', 'Coordenador de Chaves Sistêmico']).values_list('username',
                                                                                                flat=True).distinct()
    operadores_cadastro = User.objects.filter(groups__permissions__codename='pode_cadastrar_digital').values_list(
        'username', flat=True).distinct()

    annotations_funcionario = {
        'pf_id': F('id'),
        'pf_username': F('username'),
        'pf_nome': F('nome'),
        'pf_template': F('template'),
        'pf_tem_digital_fraca': F('tem_digital_fraca'),
        'pf_setor_sigla': Coalesce(F('setor__sigla'), Value('N/A')),
        'pf_campus_sigla': Coalesce(F('setor__uo__setor__sigla'), Value('N/A')),
        'pf_operador_cadastro': Case(When(user__username__in=operadores_cadastro, then=Value(True)),
                                     default=Value(False), output_field=BooleanField()),
        'pf_operador_chaves': Case(When(user__username__in=operadores_chave, then=Value(True)), default=Value(False),
                                   output_field=BooleanField()),
    }

    annotations_aluno = {
        'pf_id': F('pessoa_fisica__id'),
        'pf_username': F('pessoa_fisica__username'),
        'pf_nome': F('pessoa_fisica__nome'),
        'pf_template': F('pessoa_fisica__template'),
        'pf_tem_digital_fraca': F('pessoa_fisica__tem_digital_fraca'),
        'pf_setor_sigla': Coalesce(F('curso_campus__diretoria__setor__sigla'), Value('N/A')),
        'pf_campus_sigla': Coalesce(F('curso_campus__diretoria__setor__uo__sigla'), Value('N/A')),
    }

    if versao and versao >= '1.2.0':
        selects_funcionario.update({'pf_pode_bater_ponto': True})
        selects_aluno.update({'pf_pode_bater_ponto': False})

        annotations_funcionario.update({'pf_senha_ponto': F('senha_ponto')})
        annotations_aluno.update({'pf_senha_ponto': F('pessoa_fisica__senha_ponto')})

    qs_funcionario = Funcionario.objects.filter(*filters_funcionario).exclude(username='')
    qs_funcionario = (
        qs_funcionario.annotate(**annotations_funcionario).extra(select=selects_funcionario).values(
            *(list(annotations_funcionario.keys()) + list(selects_funcionario.keys()))).distinct()
    )

    query_funcionario = versao and get_real_sql(qs_funcionario, remove_order_by=True) or get_real_sql(qs_funcionario,
                                                                                                      remove_order_by=False)
    query_funcionario = ajustar_colunas(query_funcionario, versao)
    query = f'CREATE TEMP TABLE tabela_terminal_ponto AS {query_funcionario}'

    if 'edu' in settings.INSTALLED_APPS:
        from edu.models import Aluno

        qs_aluno = Aluno.objects.filter(*filters_aluno).exclude(pessoa_fisica__username='').annotate(
            **annotations_aluno)
        qs_aluno = qs_aluno.extra(select=selects_aluno).values(
            *(list(annotations_aluno.keys()) + list(selects_aluno.keys()))).distinct()
        query_aluno = get_real_sql(qs_aluno)
        query_aluno = ajustar_colunas(query_aluno, versao)
        if versao:
            query = f'{query} UNION {query_aluno}'

    return query


@transaction.atomic
def get_fotos_funcionarios(request):
    from ponto.models import Maquina, MaquinaLog

    try:
        m = Maquina.objects.get(ip=get_client_ip(request), ativo=True)
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')

    storage = get_temp_storage()

    ARQUIVO_DUMP = 'fotos/fotos_funcionarios.zip'
    # gerado pelo comando fotos_funcionarios
    if not storage.exists(ARQUIVO_DUMP):
        raise Http404

    MaquinaLog.objects.create(maquina=m, operacao='comum_get_fotos_funcionarios')
    try:
        response = FileResponse(storage.open(ARQUIVO_DUMP), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=fotos.zip'
        response['Content-Length'] = storage.size(ARQUIVO_DUMP)
        return response
    except FileNotFoundError:
        raise Http404


@transaction.atomic
def get_fotos_alunos(request):
    from ponto.models import Maquina

    try:
        m = Maquina.objects.get(ip=get_client_ip(request), ativo=True, cliente_refeitorio=True)
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')

    storage = get_temp_storage()

    ARQUIVO_DUMP = f'fotos/fotos_alunos_{m.uo.sigla}.zip'
    # gerado pelo comando fotos_alunos
    if not storage.exists(ARQUIVO_DUMP):
        raise Http404

    try:
        response = FileResponse(storage.open(ARQUIVO_DUMP), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=fotos.zip'
        response['Content-Length'] = storage.size(ARQUIVO_DUMP)
        return response
    except FileNotFoundError:
        raise Http404


@rtr()
@login_required()
def grupos_usuario(request, usuario_pk):
    usuario = get_object_or_404(User, pk=usuario_pk)
    usuario_logado = request.user
    title = f'Grupos do Usuário {usuario}'
    grupos = UsuarioGrupo.objects.filter(user=usuario).values_list('group__name', flat=True)
    GROUPS_DICT = {}
    for app in settings.INSTALLED_APPS:
        grupos_da_app = GroupPermission.obter_grupos_por_app_yaml(app)
        if grupos_da_app:
            for nome_grupo in grupos_da_app:
                if nome_grupo in grupos:
                    app_full_name = apps_django.get_app_config(app).get_full_name()
                    if app_full_name not in GROUPS_DICT:
                        GROUPS_DICT[app_full_name] = []
                    objeto_do_grupo = UsuarioGrupo.objects.filter(group__name=nome_grupo, user=usuario)[0]
                    meus_gerenciamentos = usuario_logado.gerenciamento_do_grupo(objeto_do_grupo.group)
                    sou_superusuario = usuario_logado.is_superuser
                    sou_eu_mesmo = usuario_logado == usuario
                    GROUPS_DICT[app_full_name].append(
                        (
                            objeto_do_grupo,
                            meus_gerenciamentos.exists() or sou_superusuario or sou_eu_mesmo,
                            meus_gerenciamentos.filter(eh_local=False).exists() or sou_superusuario or sou_eu_mesmo,
                        )
                    )

    apps = GROUPS_DICT
    apps = collections.OrderedDict(sorted(apps.items()))

    return locals()


@rtr()
@login_required()
def guia(request):
    title = 'Guia do Desenvolvedor'
    return locals()


@rtr()
@login_required()
def maquinas_detalhes(request, maquina_pk):
    if not request.user.is_superuser:
        raise PermissionDenied('Você não tem permissão de acesso a essa página')

    def ping(servidor):
        return os.system(f"ping -c 1 -t 1 {servidor}") == 0

    from ponto.models import Maquina

    maquina = get_object_or_404(Maquina, pk=maquina_pk)
    maquina_ligada = ping(maquina.ip)
    ultimos_logs = maquina.maquinalog_set.all().order_by('-horario')[0:3]
    return locals()


@rtr()
@login_required()
def alterar_senha(request):
    title = 'Alterar Senha'
    form = AlterarSenhaForm(request.POST or None, request=request)
    if form.is_valid():
        obj = TrocarSenha.objects.create(username=request.user.username)
        obj.enviar_email()
        return httprr('/comum/minha_conta/', f'Foi enviado um email para {obj.email} com as instruções para realizar a mudança de senha.')
    return locals()


@rtr()
def solicitar_trocar_senha(request):
    title = 'Alterar Senha'
    category = 'Acessos'
    icon = 'key'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = SoliticarTrocarSenhaForm(request.POST or None)
    if form.is_valid():
        obj = TrocarSenha.objects.create(username=form.cleaned_data['username'])
        obj.enviar_email()
        return httprr('/', 'Foi enviado um email para {} com as instruções para realizar a mudança de senha.'.format(
            obj.email))
    return locals()


@rtr()
def trocar_senha(request, username, token):
    from ldap_backend.forms import TrocarSenhaForm

    title = f'Efetuar mudança de senha do usuário {username}'
    if not TrocarSenha.token_valido(username, token):
        messages.error(request, 'Token inválido. Preencha o fomulário abaixo para cadastrar uma nova senha.')
        return httprr('/comum/solicitar_trocar_senha/')

    form = TrocarSenhaForm(request.POST or None, username=username)
    if form.is_valid():
        return httprr('/', 'Senha alterada com sucesso!')

    return locals()


#####################################
# Gerenciamento de Grupos
#####################################
APP_GROUP_DICT = {}
APP_NAMES_DICT = {}


@rtr()
@login_required()
def grupos_usuarios(request):
    title = 'Grupos de Usuários'

    current_app = request.GET.get('modulo') or None
    campus = request.GET.get('campus') or None
    grupo_escolhido_pk = request.GET.get('grupo') or None

    campus_choices = UnidadeOrganizacional.objects.uo().all()
    grupos_gerenciados = None
    usuarios_grupo = None
    usuarios = User.objects.none()
    contador_dict = dict()
    apps = dict()
    apps_names = dict()

    for app in settings.INSTALLED_APPS_SUAP:
        grupos_da_app = GroupPermission.obter_grupos_por_app_yaml(app)
        if grupos_da_app:
            grupos_da_app.remove(GerenciamentoGrupo.NOME_GRUPO_GERENCIADOR_FORMAT.format(app))

            apps[app] = grupos_da_app
            apps_names[apps_django.get_app_config(app).get_full_name()] = app

    grupos_gerenciados = Group.objects.all()

    apps = collections.OrderedDict(sorted(apps.items()))
    apps_names = collections.OrderedDict(sorted(apps_names.items()))
    url_filters = '?'
    if any([campus, current_app]):

        if current_app:
            url_filters += f'modulo={current_app}&'

        if campus:
            url_filters += f'campus={campus}&'

        if current_app and grupos_gerenciados:
            grupos_gerenciados = grupos_gerenciados.filter(name__in=apps[current_app])
        if (current_app and campus) and grupos_gerenciados:
            grupos_gerenciados = grupos_gerenciados.filter(user__vinculo__setor__uo__sigla=campus)
            usuarios = usuarios.filter(vinculo__setor__uo__sigla=campus).distinct()

        if list(apps.keys()):
            if current_app and grupos_gerenciados.exists():
                grupos_gerenciados = grupos_gerenciados.distinct()
                if grupo_escolhido_pk and grupo_escolhido_pk.isdigit():
                    grupo_escolhido = grupos_gerenciados.filter(pk=int(grupo_escolhido_pk)).first()
                else:
                    grupo_escolhido = grupos_gerenciados[0]

                if not grupo_escolhido:
                    return httprr('.', 'Grupo escolhido não existe', 'error')

                grupos_gerenciados_pelo_grupo_escolhido = GerenciamentoGrupo.get_grupos_gerenciados_por(grupo_escolhido)
                grupos_que_gerenciam_grupo_escolhido = GerenciamentoGrupo.get_grupos_que_gerenciam(grupo_escolhido)

                for grupo in grupos_gerenciados:
                    qs = grupo.user_set.all()
                    if campus:
                        qs = qs.filter(vinculo__setor__uo__sigla=campus)
                    contador_dict[grupo] = qs.count()

                usuarios_grupo = grupo_escolhido.usuariogrupo_set.filter(user__is_active=True)
                usuarios_grupo_qs = usuarios_grupo
                if request.method == 'GET':
                    if campus:
                        usuarios_grupo = usuarios_grupo.filter(user__vinculo__setor__uo__sigla=campus)
                usuarios_grupo = usuarios_grupo.order_by("user__first_name", "user__last_name")

    return locals()


@rtr()
@login_required()
def gerenciamento_grupo(request):
    title = 'Gerenciamento de Grupos'

    # filtro por Nome/Sobrenome do servidor
    usuario = request.GET.get('usuario') or None
    current_app = request.GET.get('modulo') or None
    campus = request.GET.get('campus') or None
    grupo_escolhido_pk = request.GET.get('grupo') or None

    campus_choices = UnidadeOrganizacional.objects.suap().all()
    grupos_gerenciados = None
    usuarios_grupo = UsuarioGrupo.objects.none()
    usuarios = User.objects.none()
    contador_dict = dict()
    apps_names = dict()

    if not APP_GROUP_DICT or not APP_NAMES_DICT:
        for app in settings.INSTALLED_APPS_SUAP:
            grupos_da_app = GroupPermission.obter_grupos_por_app_yaml(app)
            if grupos_da_app:
                # Adição do grupo gerenciador que é criado automaticamente
                APP_GROUP_DICT[app] = grupos_da_app
                APP_NAMES_DICT[apps_django.get_app_config(app).get_full_name()] = app
    if request.user.is_superuser:
        grupos_gerenciados = Group.objects.all()
        apps = APP_GROUP_DICT
        apps_names = APP_NAMES_DICT
    else:
        grupos_gerenciados = Group.objects.filter(
            pk__in=GerenciamentoGrupo.objects.filter(grupo_gerenciador__in=request.user.groups.all()).values(
                'grupos_gerenciados'))

        apps = {}
        if grupos_gerenciados.exists():
            for g in grupos_gerenciados:
                for app in list(APP_GROUP_DICT.keys()):
                    if g.name in APP_GROUP_DICT[app]:
                        if app not in apps:
                            apps[app] = []
                        apps[app].append(g.name)
                        apps_names[apps_django.get_app_config(app).get_full_name()] = app

    apps = collections.OrderedDict(sorted(apps.items()))
    apps_names = collections.OrderedDict(sorted(apps_names.items()))
    url_filters = '?'
    if any([usuario, campus, current_app]):
        if usuario:
            usuarios = User.objects.filter(username=usuario)
            if not usuarios.exists():
                usuarios = User.objects.filter(
                    (Q(pessoafisica__nome__icontains=usuario) | Q(pessoafisica__username__icontains=usuario)) & Q(
                        usuariogrupo__isnull=False)).distinct()
            url_filters += f'usuario={usuario}&'

        if current_app:
            url_filters += f'modulo={current_app}&'

        if campus:
            url_filters += f'campus={campus}&'

        if current_app and grupos_gerenciados:
            grupos_gerenciados = grupos_gerenciados.filter(name__in=apps.get(current_app, []))
        if current_app and usuario and grupos_gerenciados:
            qs_nome = grupos_gerenciados.filter(
                reduce(operator.and_, (Q(user__pessoafisica__nome__icontains=item) for item in usuario.split(' '))))
            qs_username = grupos_gerenciados.filter(user__username__icontains=usuario)
            grupos_gerenciados = (qs_nome | qs_username).distinct()
        if (usuario and campus) or (current_app and campus) and grupos_gerenciados:
            grupos_gerenciados = grupos_gerenciados.filter(user__vinculo__setor__uo__sigla=campus)
            usuarios = usuarios.filter(vinculo__setor__uo__sigla=campus).distinct()

        if list(apps.keys()):
            if current_app and grupos_gerenciados.exists():
                grupos_gerenciados = grupos_gerenciados.distinct()
                if grupo_escolhido_pk and grupo_escolhido_pk.isdigit():
                    grupo_escolhido = grupos_gerenciados.filter(pk=int(grupo_escolhido_pk)).first()
                else:
                    grupo_escolhido = grupos_gerenciados[0]

                    # exclui os superadmin`s das listagens dos grupos (exceto quando o usuário logado for superadmin)
                grupos_gerenciados_pelo_grupo_escolhido = GerenciamentoGrupo.get_grupos_gerenciados_por(grupo_escolhido)
                grupos_que_gerenciam_grupo_escolhido = GerenciamentoGrupo.get_grupos_que_gerenciam(grupo_escolhido)
                for grupo in grupos_gerenciados:
                    qs = grupo.user_set.all()
                    if usuario:
                        qs_nome = qs.filter(reduce(operator.and_, (Q(pessoafisica__nome__icontains=item) for item in
                                                                   usuario.split(' '))))
                        qs_username = qs.filter(username__icontains=usuario)
                        qs = (qs_nome | qs_username).distinct()
                    if campus:
                        qs = qs.filter(vinculo__setor__uo__sigla=campus)
                    contador_dict[grupo] = qs.count()
                if grupo_escolhido:
                    usuarios_grupo = grupo_escolhido.usuariogrupo_set.filter(user__is_active=True)

                usuarios_grupo_qs = usuarios_grupo
                if request.method == 'GET':
                    if usuario:
                        usuarios_grupo_qs = usuarios_grupo_qs.filter(reduce(operator.and_,
                                                                            (Q(user__pessoafisica__nome__icontains=item)
                                                                             for item in usuario.split(' '))))
                        username_grupo_qs = usuarios_grupo.filter(user__username__icontains=usuario)
                        usuarios_grupo = usuarios_grupo_qs | username_grupo_qs
                    if campus:
                        usuarios_grupo = usuarios_grupo.filter(user__vinculo__setor__uo__sigla=campus)
                usuarios_grupo = usuarios_grupo.order_by("user__first_name", "user__last_name")
                gerenciamento_do_grupo_eh_local = False
                if not request.user.gerenciamento_do_grupo(grupo_escolhido).filter(eh_local=False).exists():
                    gerenciamento_do_grupo_eh_local = True

                apps_com_vinculacao_setores = ["edu", "etep"]
                pode_vincular_setores = False
                if current_app in apps_com_vinculacao_setores:
                    pode_vincular_setores = True

    return locals()


@rtr()
@login_required()
def adicionar_usuario_grupo(request, pk_grupo):
    title = "Adicionar Usuário ao Grupo"
    grupo = get_object_or_404(Group, pk=pk_grupo)
    if not request.user.eh_gerenciador_do_grupo(grupo):
        raise PermissionDenied('Você não tem permissão para adicionar um usuário nesse grupo.')

    so_local = False
    if not request.user.gerenciamento_do_grupo(grupo).filter(eh_local=False).exists():
        so_local = True
    FormClass = AdicionarUsuarioGrupoFormFactory(request.user, so_local)
    form = FormClass(data=request.POST or None)
    if form.is_valid():  # somente se for POST
        for user in form.cleaned_data['user']:
            user.groups.add(grupo)
        return httprr('..', 'Usuário(s) adicionado(s) com sucesso.')

    return locals()


@rtr()
@login_required()
def adicionar_setor_usuario_grupo(request, pk_usuario_grupo):
    title = 'Vincular Setores'
    usuario_grupo = UsuarioGrupo.objects.get(pk=pk_usuario_grupo)
    url_origem = request.META.get('HTTP_REFERER')
    if not request.user.eh_gerenciador_do_grupo(usuario_grupo.group):
        raise PermissionDenied('Você não tem permissão para Vincular Setores nesse grupo.')

    FormClass = VincularSetorUsuarioGrupoFormFactory(usuario_grupo)
    form = FormClass(data=request.POST or None)
    if form.is_valid():
        setores_atuais = usuario_grupo.setores.all()
        for setor_atual in setores_atuais:
            if not setor_atual in form.cleaned_data['setores']:
                registro = UsuarioGrupoSetor.objects.filter(usuario_grupo=usuario_grupo, setor=setor_atual)
                registro.delete()

        for setor_form in form.cleaned_data['setores']:
            if not setor_form in setores_atuais:
                registro = UsuarioGrupoSetor()
                registro.usuario_grupo = usuario_grupo
                registro.setor = setor_form
                registro.save()

        return httprr(url_origem, 'Setores vinculados com sucesso.', close_popup=True)
    return locals()


@rtr()
@login_required()
def remover_usuario_grupo(request, pk_usuario_grupo):
    ug = get_object_or_404(UsuarioGrupo, pk=pk_usuario_grupo)
    grupo = ug.group
    usuario = ug.user
    usuario_logado = request.user
    sou_eu_mesmo = usuario_logado == usuario
    if not request.user.eh_gerenciador_do_grupo(grupo) and not sou_eu_mesmo:
        raise PermissionDenied('Você não tem permissão para remover um usuário nesse grupo.')
    if (
            not sou_eu_mesmo
            and not request.user.gerenciamento_do_grupo(grupo).filter(eh_local=False).exists()
            and request.user.get_relacionamento().setor.uo != usuario.get_relacionamento().setor.uo
    ):
        raise PermissionDenied(
            'Você não tem permissão para remover um usuário nesse grupo que não seja do campus: {}.'.format(
                request.user.get_relacionamento().setor.uo))
    ug.setores.clear()
    usuario.groups.remove(grupo)
    ug.delete()

    retorno = request.META.get('HTTP_REFERER', '..')
    if sou_eu_mesmo:
        retorno = usuario.get_relacionamento().get_absolute_url()
    elif '/remover_usuario_grupo/' in request.META.get('HTTP_REFERER', '..'):
        retorno = 'comum/gerenciamento_grupo/'
    return httprr(retorno, f'Usuário foi removido do grupo {grupo} com sucesso.')


@rtr()
@login_required()
def comentario_add(request, aplicacao, modelo, objeto_id, resposta_id=None):
    title = 'Adicionar Comentário'
    form = ComentarioForm(request.POST or None)
    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            content_type = ContentType.objects.get(app_label=aplicacao.lower(), model=modelo.lower())
            comentario = Comentario.objects.create(texto=form.cleaned_data['texto'], content_type=content_type,
                                                   object_id=objeto_id, resposta_id=resposta_id)
            return httprr('..', 'Comentário adicionado com sucesso.')
    return locals()


@rtr()
@permission_required('comum.add_solicitacaoreservasala')
def sala_visualizar(request, sala_pk):
    sala = get_object_or_404(Sala, pk=sala_pk)
    title = f'Visualizar Sala: {sala}'
    eh_avaliador = sala.eh_avaliador(request.user)
    return locals()


@rtr()
@permission_required('comum.add_solicitacaoreservasala')
def sala_solicitar_reserva(request, sala_pk):
    solicitacao = SolicitacaoReservaSala()
    sala = get_object_or_404(Sala, pk=sala_pk)
    title = f'Solicitar Reserva: {sala}'
    if not sala.pode_agendar(request.user):
        raise PermissionDenied("Acesso negado.")

    if not sala.is_agendavel():
        msg = 'Sala não está disponível para agendamento.'
        if not sala.avaliadores_de_agendamentos.exists():
            msg = 'Sala não está disponível para agendamento, pois não tem avaliadores.'

        return httprr(request.META.get('HTTP_REFERER', '..'), msg, tag="error")

    calendario = sala.programacao_atual()
    solicitacao.sala = sala
    solicitacao.solicitante = request.user
    solicitacao.data_solicitacao = datetime.now()
    if request.GET.get('solicitacao'):
        solicitacao_clonada = get_object_or_404(SolicitacaoReservaSala, pk=request.GET.get('solicitacao'))
        solicitacao.recorrencia = solicitacao_clonada.recorrencia
        solicitacao.data_inicio = solicitacao_clonada.data_inicio
        solicitacao.data_fim = solicitacao_clonada.data_fim
        solicitacao.hora_inicio = solicitacao_clonada.hora_inicio
        solicitacao.hora_fim = solicitacao_clonada.hora_fim
        solicitacao.justificativa = solicitacao_clonada.justificativa

        form = SolicitacaoReservaSalaForm(
            request.POST or None, instance=solicitacao, files=request.FILES or None,
            initial={'interessados_vinculos': solicitacao_clonada.interessados_vinculos.all()}, request=request
        )
    else:
        solicitacao.recorrencia = SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO
        form = SolicitacaoReservaSalaForm(request.POST or None, instance=solicitacao, files=request.FILES or None, request=request)

    if form.is_valid():
        form.save()
        msg = 'Solicitação realizada com sucesso.'
        return httprr("/admin/comum/solicitacaoreservasala/", msg)

    return locals()


@rtr()
@permission_required('comum.view_solicitacaoreservasala')
def sala_agenda_atual(request, sala_pk):
    sala = get_object_or_404(Sala, pk=sala_pk)
    calendario = sala.programacao_atual()
    return locals()


@permission_required('comum.view_solicitacaoreservasala')
def sala_informacoes_complementares(request, sala_pk):
    sala = get_object_or_404(Sala, pk=sala_pk)
    return HttpResponse(sala.informacoes_complementares or "")


@rtr()
@permission_required('comum.view_solicitacaoreservasala')
def sala_ver_solicitacao(request, solicitacao_reserva_pk):
    solicitacao = get_object_or_404(SolicitacaoReservaSala, pk=solicitacao_reserva_pk)
    title = f'Solicitação de Reserva de Sala #{solicitacao.pk}'
    if not solicitacao.pode_ver(request.user):
        raise PermissionDenied()

    eh_avaliador = solicitacao.sala.eh_avaliador(request.user)
    reservas = solicitacao.reservasala_set.order_by('data_inicio')
    calendario = solicitacao.sala.programacao_atual(solicitacao)
    return locals()


@permission_required('comum.delete_solicitacaoreservasala')
def sala_excluir_solicitacao(request, solicitacao_reserva_pk):
    solicitacao = get_object_or_404(SolicitacaoReservaSala, pk=solicitacao_reserva_pk)
    if not solicitacao.pode_excluir(request.user):
        raise PermissionDenied()

    solicitacao.status = SolicitacaoReservaSala.STATUS_EXCLUIDA
    solicitacao.save()
    return httprr("/admin/comum/solicitacaoreservasala/", 'Reserva de Sala excluída com sucesso.')


@rtr()
@permission_required('comum.pode_avaliar_solicitacao_reserva_de_sala')
def sala_avaliar_solicitacao(request, solicitacao_reserva_pk):
    title = 'Avaliar Agendamento de Sala'
    solicitacao = get_object_or_404(SolicitacaoReservaSala, pk=solicitacao_reserva_pk)
    if not solicitacao.pode_avaliar(request.user):
        raise PermissionDenied()

    solicitacao.avaliador = request.user
    solicitacao.data_avaliacao = datetime.now()
    form = SolicitacaoReservaSalaAvaliarForm(request.POST or None, instance=solicitacao)
    if form.is_valid():
        form.save()
        return httprr("..", 'Avaliação realizada com sucesso.')

    return locals()


@rtr()
@login_required()
def sala_cancelar_solicitacao(request, solicitacao_reserva_pk):
    title = 'Cancelar Agendamento de Sala'
    solicitacao = get_object_or_404(SolicitacaoReservaSala, pk=solicitacao_reserva_pk)
    if not solicitacao.pode_cancelar(request.user):
        raise PermissionDenied()

    solicitacao.data_cancelamento = datetime.now()
    solicitacao.status = SolicitacaoReservaSala.STATUS_INDEFERIDA
    form = SolicitacaoReservaSalaCancelarForm(request.POST or None, instance=solicitacao, request=request)
    if form.is_valid():
        form.save()
        return httprr("..", 'Avaliação realizada com sucesso.')

    return locals()


@rtr()
@permission_required('comum.view_indisponibilizacaosala')
def sala_listar_indisponibilizacoes(request):
    title = 'Registros de Indisponibilizações de Salas'
    eh_avaliador = Sala.eh_avaliador_salas(request.user)
    qualquer = IndisponibilizacaoSala.objects.all()
    em_manutencao = IndisponibilizacaoSala.em_andamento.all()
    tab = request.GET.get('tab')
    if tab == 'qualquer':
        indisponibilizacoes = qualquer
    elif tab == 'em_manutencao':
        indisponibilizacoes = em_manutencao
    else:
        tab = 'qualquer'
        indisponibilizacoes = qualquer

    params = request.GET.dict()
    if "order_by" in params:
        order_params = params.pop('order_by', '').split('-')
        order_str = order_params[0]
        order_sign = ''
        if len(order_params) > 1:
            order_str = order_params[1]
            order_sign = '-'

        if order_str == 'sala':
            indisponibilizacoes = indisponibilizacoes.order_by(f'{order_sign}sala')
        elif order_str == 'periodo':
            indisponibilizacoes = indisponibilizacoes.order_by(f'{order_sign}data_inicio')

    params = urllib.parse.urlencode(params)
    form = IndisponibilizacaoSalaBuscarForm(request.GET or None, indisponibilizacoes=indisponibilizacoes)
    indisponibilizacoes = form.processar(indisponibilizacoes)
    indisponibilizacoes = indisponibilizacoes.order_by('id')
    return locals()


@rtr()
@permission_required('comum.view_indisponibilizacaosala')
def sala_indicadores(request):
    title = 'Indicadores'
    agendaveis = Sala.objects.filter(agendavel=True)

    form = SalaIndicadoresForm(request.GET or None, request=request, initial={'campus': get_uo(request.user).id})

    if form.is_valid():
        salas = []

        inicio = None
        if 'inicio' in form.cleaned_data and form.cleaned_data['inicio']:
            inicio = form.cleaned_data['inicio']

        final = None
        if 'final' in form.cleaned_data and form.cleaned_data['final']:
            final = form.cleaned_data['final']

        campus = None
        if 'campus' in form.cleaned_data and form.cleaned_data['campus']:
            campus = form.cleaned_data['campus']

        predio = None
        if 'predio' in form.cleaned_data and form.cleaned_data['predio']:
            predio = form.cleaned_data['predio']
            agendaveis = agendaveis.filter(predio=predio)

        dias = (final - inicio).days
        agendaveis = agendaveis.filter(predio__uo=campus)

        for sala in agendaveis:
            reservas = ReservaSala.deferidas.filter(sala=sala, data_inicio__gte=inicio, data_fim__lte=final)
            qtd_canceladas = ReservaSala.objects.filter(sala=sala, data_inicio__gte=inicio, data_fim__lte=final, cancelada=True).count()
            qtd_ocorreu = reservas.filter(ocorreu=True).count()
            qtd_nao_ocorreu = reservas.filter(ocorreu=False).count()
            qtd_desconhecido = reservas.filter(ocorreu=None).count()
            duracao = 0
            for reserva in reservas:
                duracao += (reserva.data_fim - reserva.data_inicio).total_seconds()

            tempo_medio = reservas.exists() and duracao / 3600 / dias or 0
            salas.append([sala, tempo_medio, qtd_canceladas, qtd_ocorreu, qtd_nao_ocorreu, qtd_desconhecido])

        salas = sorted(salas, key=lambda tempo_medio: tempo_medio[1])
    return locals()


@rtr()
@permission_required('comum.add_indisponibilizacaosala')
def sala_registrar_indisponibilizacao(request, sala_pk=None):
    title = 'Indisponibilizar Sala'
    eh_avaliador = Sala.eh_avaliador_salas(request.user)
    if not eh_avaliador:
        raise PermissionDenied()

    indisponibilizacao = IndisponibilizacaoSala()
    sala = None
    if sala_pk:
        sala = get_object_or_404(Sala, pk=sala_pk)
        if not sala.eh_avaliador(request.user):
            raise PermissionDenied()
        indisponibilizacao.sala = sala
        calendario = sala.programacao_atual()

    indisponibilizacao.usuario = request.user
    indisponibilizacao.data = datetime.now()
    form = RegistrarIndisponibilizacaoSalaForm(request.POST or None, instance=indisponibilizacao, request=request)
    if form.is_valid():
        sala = form.cleaned_data.get('sala', None)
        if sala and not sala.eh_avaliador(request.user):
            raise PermissionDenied()
        form.save()
        return httprr("..", 'Cadastro realizado com sucesso.')

    return locals()


@rtr()
@permission_required('comum.view_indisponibilizacaosala')
def sala_ver_indisponibilizacao(request, indisponibilizacao_pk):
    title = 'Visualizar Registro de Indisponibilização'
    indisponibilizao = get_object_or_404(IndisponibilizacaoSala, pk=indisponibilizacao_pk)
    calendario = indisponibilizao.sala.programacao_atual()
    return locals()


@permission_required('comum.delete_indisponibilizacaosala')
def sala_excluir_indisponibilizacao(request, indisponibilizacao_pk):
    indisponibilizao = get_object_or_404(IndisponibilizacaoSala, pk=indisponibilizacao_pk)
    if not indisponibilizao.pode_excluir(request.user):
        raise PermissionDenied()

    indisponibilizao.delete()
    return httprr("/comum/sala/listar_indisponibilizacoes/", 'Indisponibilização removida com sucesso.')


@rtr()
@permission_required('comum.view_solicitacaoreservasala')
def sala_cancelar_reserva(request, reserva_pk):
    reserva = get_object_or_404(ReservaSala, pk=reserva_pk)
    user = request.user
    if not reserva.pode_cancelar(user):
        raise PermissionDenied()

    reserva.cancelada_por = user
    form = ReservaSalaCancelarForm(request.POST or None, instance=reserva)
    if form.is_valid():
        form.cancelar()
        return httprr('..', 'Cancelamento realizado com sucesso.')

    return locals()


@rtr()
@permission_required('comum.view_solicitacaoreservasala')
def sala_informar_ocorrencia_reserva(request, reserva_pk):
    reserva = get_object_or_404(ReservaSala, pk=reserva_pk)
    user = request.user
    if not reserva.sala.eh_avaliador(user):
        raise PermissionDenied()

    reserva.cancelada_por = user
    form = ReservaInformarOcorrenciaForm(request.POST or None, instance=reserva)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada com sucesso.')

    return locals()


@rtr()
@permission_required('comum.view_solicitacaoreservasala')
def sala_cancelar_reservas_periodo(request, sala_pk):
    title = 'Cancelar Reservas por Período'
    sala = get_object_or_404(Sala, pk=sala_pk)
    user = request.user
    if not sala.eh_avaliador(user):
        raise PermissionDenied()

    calendario = sala.programacao_atual()
    form = CancelarReservasPeriodoForm(request.POST or None, request=request, sala=sala)
    if form.is_valid():
        form.cancelar()
        return httprr('..', 'Cancelamento realizado com sucesso.')

    return locals()


@rtr()
@permission_required('comum.change_prestadorservico')
def copiar_digital_de_outra_pessoa_mesmo_cpf(request, pk_pessoa_fisica):
    pessoa_fisica = get_object_or_404(PessoaFisica, pk=pk_pessoa_fisica)
    if pessoa_fisica.pode_reaproveitar_digital():
        pessoa_fisica.template = pessoa_fisica.get_digital_outra_pessoa_fisica_mesmo_cpf()
        pessoa_fisica.save()
        return httprr('..', 'Digital reaproveitada com sucesso.')
    return httprr('..', 'Digital não pode ser reaproveitada.')


@rtr()
def autenticar_documento(request):
    from edu.models import RegistroEmissaoCertificadoENEM

    title = 'Verificação de Autenticação de Documento'
    category = 'Autenticação de Documentos'
    icon = 'lock'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    initial = dict(
        tipo=request.GET.get('tipo'), data_emissao=request.GET.get('data_emissao'),
        codigo_verificador=request.GET.get('codigo_verificador')
    )
    form = AutenticarDocumentoForm(request.POST or None, initial=initial)
    if form.is_valid():
        # os registros de emissão de certificado de evento foram removidos e a autenticação regera certificado em tempo de execução
        if form.cleaned_data['tipo'] == 'Certificado de Participação em Evento':
            Participante = apps.get_model('eventos.Participante')
            if Participante:
                codigo_geracao_certificado = '{}{}'.format(form.cleaned_data['data_emissao'].strftime('%d%m%Y'),
                                                           form.cleaned_data['codigo_verificador'][0:7])
                participante_evento = Participante.objects.filter(
                    codigo_geracao_certificado=codigo_geracao_certificado).first()
                if participante_evento:
                    return HttpResponseRedirect(participante_evento.get_url_download_certificado())
        else:
            registro = form.processar()
            if registro and default_storage.exists(registro.documento.name):
                tmp = tempfile.NamedTemporaryFile(delete=False)
                with registro.documento.open('rb') as f:
                    tmp.write(f.read())
                tmp.close()
                assinaturas = signer.verify(tmp.name)

            if registro:
                if registro.tipo == 'Carteira Funcional Digital':
                    is_carteira_funcional = True
                    servidor = Servidor.objects.get(pk=registro.modelo_pk)
                if registro.tipo == 'Certificado ENEM':
                    if registro.modelo_pk:
                        registro_enem = RegistroEmissaoCertificadoENEM.objects.get(pk=registro.modelo_pk)
                        is_cancelado = registro_enem.cancelado

                        if is_cancelado:
                            responsavel_cancelamento = registro_enem.responsavel_cancelamento
                            data_cancelamento = registro_enem.data_cancelamento
                            razao_cancelamento = registro_enem.razao_cancelamento

    return locals()


@rtr()
def baixar_documento(request, pk, codigo_verificador):
    registro = get_object_or_404(RegistroEmissaoDocumento, pk=pk, codigo_verificador=codigo_verificador)
    return registro.as_pdf_response()


@rtr()
@login_required()
def assinar_documento(request):
    title = 'Assinar Documento'
    form = AssinarDocumentoForm(request=request, data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        caminho_arquivo = form.processar()
        with open(caminho_arquivo, 'rb') as file:
            return PDFResponse(file.read(), nome='Assinado.pdf')
    return locals()


@rtr()
@login_required()
def verificar_documento(request):
    title = 'Verificar Documento'
    form = VerificarDocumentoForm(request=request, data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        try:
            assinantes = form.processar()
        except Exception:
            return httprr('/comum/verificar_documento/', 'Problema ao tentar verificar a assinatura deste documento. Verifique se o arquivo não está danificado e tente novamente.', 'error')
        if assinantes:
            url = '/comum/verificar_documento/'
            return httprr(url, 'Documento assinado digitalmente por {}.'.format(', '.join(assinantes)))
        else:
            return httprr('..', 'Assinatura digital não identificada.', tag='error')
    return locals()


@rtr()
def validar_assinatura(request):
    title = 'Validar Assinatura Digital'
    category = 'Autenticação de Documentos'
    icon = 'lock'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = ValidarDocumentoForm(request=request, data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        try:
            assinantes = form.processar()
        except Exception:
            return httprr('/comum/validar_assinatura/', 'Problema ao tentar verificar a assinatura deste documento. Verifique se o arquivo não está danificado e tente novamente.', 'error')
    return locals()


@login_required()
def retrair_menu(request):
    request.session['retraido'] = True
    return HttpResponse('OK')


@login_required()
def expandir_menu(request):
    request.session['retraido'] = False
    return HttpResponse('OK')


# @rtr(two_factor_authentication=True)
@rtr()
@login_required()
def atualizar_email(request, vinculo_pk):
    title = 'Atualização do E-mail'
    vinculo = get_object_or_404(Vinculo, pk=vinculo_pk)
    if not (
            request.user.get_vinculo().pk == int(vinculo_pk)
            or request.user.has_perm('rh.pode_editar_email_secundario_servidor')
            or request.user.has_perm('rh.pode_editar_email_secundario_prestador')
            or request.user.has_perm('rh.pode_editar_email_institucional')
            or request.user.has_perm('rh.pode_editar_email_academico')
            or request.user.has_perm('rh.pode_editar_email_google_classroom')
    ):
        raise PermissionDenied()

    relacionamento = vinculo.relacionamento
    form = AtualizarEmailForm(request.POST or None, request=request, relacionamento=relacionamento)
    if form.is_valid():
        form.save()
        return httprr('..', 'E-mail atualizado com sucesso.')
    return locals()


@rtr()
@login_required()
def excluir(request, app, model, pks):
    from django.contrib.admin.utils import NestedObjects

    try:
        Model = apps_django.get_model(app, model)
    except Exception:
        return httprr('..', 'Impossível excluir registro.', 'error')

    html = []
    pks = pks.split('_')
    objs = Model.objects.filter(pk__in=pks)
    if hasattr(Model, 'locals'):
        objs = Model.locals.filter(pk__in=pks)

    title = 'Confirmação de Exclusão'

    exclude_pks = []
    for obj in objs:
        if not request.user.is_superuser and hasattr(obj, 'can_delete') and not obj.can_delete(request.user):
            exclude_pks.append(obj.pk)
        objs = objs.exclude(pk__in=exclude_pks)

    has_perm = request.user.has_perm(f'{app}.delete_{model}')
    if not has_perm:
        return httprr('..', 'Você não tem permissão para excluir o(s) registro(s).', 'error')
    else:
        form = ExcluirRegistroForm(data=request.POST or None, request=request)
        if form.is_valid():
            try:
                sid = transaction.savepoint()
                for obj in objs:
                    obj.delete()
                transaction.savepoint_commit(sid)
            except Exception as e:
                transaction.savepoint_rollback(sid)
                return httprr('..', f'{str(e)}', 'error')
            return httprr(request.GET.get('next', '..'), 'Registro(s) excluído(s) com sucesso.')

        collector = NestedObjects('default')
        collector.collect(objs)
        lista = collector.nested()

        def format_html(obj_or_list, has_child=True):
            if type(obj_or_list) == list:
                if obj_or_list:
                    html.append('<ul class="obj-tree">')
                    for i, _obj in enumerate(obj_or_list):
                        has_child = i + 1 < len(obj_or_list) and type(obj_or_list[i + 1]) == list
                        if has_child:
                            next_list = obj_or_list[i + 1]
                            if next_list and next_list[0]._meta.verbose_name.endswith('relationship'):
                                has_child = False
                        format_html(_obj, has_child)
                    html.append('</ul>')
            else:
                if not obj_or_list._meta.verbose_name.endswith('relationship'):
                    css = has_child and 'obj-tree-toggler expandido' or ''
                    html.append(
                        '<li><a href="javascript:void(0)" class="{}"><strong>{} #{}</strong></a> : {}</li>'.format(
                            css, obj_or_list._meta.verbose_name, obj_or_list.pk, str(obj_or_list)
                        )
                    )

        format_html(lista)
    output = ''.join(html)

    return locals()


@login_required()
def popula_nome_sugerido(request):
    # selecionando a pessoa escolhida
    id = request.POST.get('solicitante_vinculo')
    solicitante_escolhido = Vinculo.objects.get(pk=id)
    nome = solicitante_escolhido.pessoa.nome if solicitante_escolhido else ''

    nomes = gera_nomes(nome)
    choice_nomes = [['', 'Selecione umas das opções']]
    for nome in nomes:
        choice_nomes.append([nome, nome])

    return JsonResponse({'nomes': choice_nomes})


@rtr()
@login_required()
def ver_solicitacao_documento(request, solicitacaodocumento_pk):
    solicitacao = get_object_or_404(DocumentoControle, pk=solicitacaodocumento_pk)
    if solicitacao:
        historico = DocumentoControleHistorico.objects.filter(solicitacao=solicitacao).order_by('-data_historico')
        servidor = solicitacao.solicitante_vinculo.relacionamento
        title = f'Solicitação de {servidor}'
        verificacao_propria = request.user == servidor.user
        is_rh = request.user.has_perm('rh.change_servidor')

        pode_atender_solicitacao = solicitacao.pode_atender_solicitacao(request)
        return locals()


@rtr()
@login_required()
@permission_required('comum.change_documentocontrole')
def marcar_solicitacao_atendida(request, solicitacaodocumento_pk):
    url_retorno = request.META.get('HTTP_REFERER')
    if not url_retorno:
        url_retorno = '/admin/comum/documentocontrole/'
    try:
        solicitacao = get_object_or_404(DocumentoControle, pk=solicitacaodocumento_pk)
        # se for do rh, pode marcar a solicitacão como atendida
        if solicitacao.pode_atender_solicitacao(request):
            solicitacao.atender_solicitacao(request)
        return httprr(url_retorno, 'Solicitação atendida com sucesso.')
    except Exception:
        return httprr(url_retorno, 'Erro ao marcar a solicitação como atendida.', 'error')


@rtr()
@login_required()
@permission_required('comum.change_documentocontrole')
def rejeitar_solicitacao(request, solicitacaodocumento_pk):
    try:
        solicitacao = get_object_or_404(DocumentoControle, pk=solicitacaodocumento_pk)
        title = f'Rejeitar Solicitação:  {solicitacao}'
        form = RejeitarSolicitacaoForm(request.POST or None)
        if form.is_valid():
            # se for do rh, pode marcar a solicitacão como rejeitada
            if solicitacao.pode_rejeitar_solicitacao(request):
                solicitacao.rejeitar_solicitacao(request)
            return httprr('..', 'Solicitação rejeitada com sucesso.')
        return locals()
    except Exception:
        return httprr('.', 'Erro ao rejeitar a solicitação.', 'error')


@rtr()
@permission_required('comum.view_pensionista')
def tela_pensionista(request, matricula_pensionista):
    pensionista = get_object_or_404(Pensionista, matricula=matricula_pensionista)
    title = str(pensionista)
    return locals()


@rtr()
@login_required()
def usuario_historico_grupos(request, usuario_id):
    usuario = get_object_or_404(User, pk=usuario_id)
    title = f'Histórico - {usuario}'
    registros = LogEntry.objects.filter(object_id=usuario.id, action_flag=FLAG_LOG_GERENCIAMENTO_GRUPO).order_by(
        '-action_time')

    return locals()


@login_required()
@csrf_exempt
def atualiza_layout(request):
    if request.POST:
        titulo = request.POST.get('titulo', '').strip().upper()
        if not titulo:
            raise PermissionDenied('Erro')
        try:
            ordem = int(request.POST.get('ordem', -1))
            coluna = int(request.POST.get('coluna', 0))
        except Exception:
            raise PermissionDenied('Erro')

        quadro = IndexLayout.objects.filter(usuario=request.user, quadro_nome=titulo)

        if quadro.exists():
            quadro = quadro[0]
            qs = IndexLayout.objects.filter(usuario=request.user, quadro_coluna=coluna).exclude(id=quadro.id).order_by('quadro_ordem')
            sobe = qs[:ordem]
            desce = qs[ordem:]

            nova_ordem = 0
            for q in sobe:
                q.quadro_ordem = nova_ordem
                q.save()
                nova_ordem += 1

            quadro.quadro_coluna = coluna
            quadro.quadro_ordem = nova_ordem
            quadro.save()

            nova_ordem = nova_ordem + 1
            for q in desce:
                q.quadro_ordem = nova_ordem
                q.save()
                nova_ordem += 1

    IndexLayout.recarregar_layouts(request)

    return HttpResponse('Ok')


@login_required()
@csrf_exempt
def esconder_quadro(request):
    titulo = request.POST.get('titulo', '').strip().upper()
    if not titulo:
        raise PermissionDenied('Erro')
    qs = IndexLayout.objects.filter(usuario=request.user, quadro_nome=titulo)
    i = qs.first()
    if not i:
        i = IndexLayout(quadro_nome=titulo, quadro_coluna=1, quadro_ordem=1, usuario=request.user)
        i.save()
    qs.update(escondido=True)
    IndexLayout.recarregar_layouts(request)
    return HttpResponseRedirect('/')


@rtr()
@login_required()
def exibir_quadro(request):
    title = "Gerenciar Quadros"
    form = ExibirQuadrosForm(request.POST or None, request=request, coluna='esquerda')
    if form.is_valid():
        form.processar(request)
        return httprr('..', 'Atualização exibida com sucesso.')
    return locals()


def atualizar_preferencia(usuario, tema=None):
    preferencias = Preferencia.objects.filter(usuario=usuario)
    if not preferencias.exists():
        preferencia = Preferencia()
        preferencia.usuario = usuario
    else:
        preferencia = preferencias[0]
    if tema:
        preferencia.tema = tema
    preferencia.save()

    return locals()


@rtr()
@login_required()
def acessibilidade(request):
    title = 'Acessibilidade'

    return locals()


@rtr()
@login_required()
def temas(request):
    title = 'Seleção de Tema'

    preferencia = Preferencia.objects.filter(usuario=request.user)
    if preferencia.exists():
        preferencia = preferencia[0]
    else:
        preferencia = None

    # Temas
    preferencias = Preferencia.objects.filter(usuario__is_active=True).aggregate(
        tema_padrao=Count('pk', filter=Q(tema=Preferencia.PADRAO)),
        tema_dunas=Count('pk', filter=Q(tema=Preferencia.DUNAS)),
        tema_aurora=Count('pk', filter=Q(tema=Preferencia.AURORA)),
        tema_luna=Count('pk', filter=Q(tema=Preferencia.LUNA)),
        tema_govbr=Count('pk', filter=Q(tema=Preferencia.GOVBR)),
        tema_alto_contraste=Count('pk', filter=Q(tema=Preferencia.ALTO_CONSTRASTE)),
        tema_ifs=Count('pk', filter=Q(tema=Preferencia.IFS)),
    )
    tema_padrao = preferencias['tema_padrao']
    tema_dunas = preferencias['tema_dunas']
    tema_aurora = preferencias['tema_aurora']
    tema_luna = preferencias['tema_luna']
    tema_govbr = preferencias['tema_govbr']
    tema_alto_contraste = preferencias['tema_alto_contraste']
    tema_ifs = preferencias['tema_ifs']

    return locals()


@rtr()
@login_required()
def alterar_tema(request):
    tema = request.GET.get('theme') or None

    padrao = Preferencia.PADRAO
    dunas = Preferencia.DUNAS
    aurora = Preferencia.AURORA
    luna = Preferencia.LUNA
    govbr = Preferencia.GOVBR
    alto_contraste = Preferencia.ALTO_CONSTRASTE
    ifs = Preferencia.IFS

    if tema == padrao:
        novo_tema = padrao
    elif tema == dunas:
        novo_tema = dunas
    elif tema == aurora:
        novo_tema = aurora
    elif tema == luna:
        novo_tema = luna
    elif tema == govbr:
        novo_tema = govbr
    elif tema == alto_contraste:
        novo_tema = alto_contraste
    elif tema == ifs:
        novo_tema = ifs
    else:
        novo_tema = padrao

    request.session['theme'] = novo_tema

    atualizar_preferencia(usuario=request.user, tema=novo_tema)
    return httprr('/comum/temas/', f'Tema alterado para "{novo_tema}" com sucesso.')


@rtr()
@login_required()
def minha_conta(request):
    usuario = get_object_or_404(User, pk=request.user.pk)
    title_usuario = f'{usuario.pessoafisica}' if hasattr(usuario, 'pessoafisica') else f'{usuario}'
    title = f'Minha Conta: {title_usuario}'
    return locals()


@rtr()
@login_required()
def prestador_servico(request, id):
    obj = get_object_or_404(PrestadorServico.objects, id=id)
    title = str(obj)
    hoje = datetime.now().date()
    verificacao_propria = request.user == obj.get_vinculo().user
    if request.user.get_relacionamento() == obj or request.user.has_perm('comum.view_prestadorservico'):
        return locals()
    else:
        raise PermissionDenied


@rtr()
@login_required()
@permission_required('comum.change_prestadorservico')
def ocupacao_prestador(request, prestador_id):
    prestador = get_object_or_404(PrestadorServico.objects, id=prestador_id)
    title = f'Vincular Ocupação do Prestador {prestador}'

    pk = request.GET.get('pk', None)
    ocupacao_dict = dict(data=request.POST or None, prestador=prestador, request=request)
    if pk:
        obj = get_object_or_404(OcupacaoPrestador.objects, id=pk)
        if not obj.pode_editar():
            raise PermissionDenied
        ocupacao_dict['instance'] = obj

    form = OcupacaoPrestadorForm(**ocupacao_dict)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Ocupação vinculada com sucesso.')
    return locals()


@rtr(template='manuais/docs.html')
def manuais_view(request):
    return locals()

def baixar_manuais(request, aplicacao, versao):
    arquivo_nome = f'Manual Fluxo {aplicacao.upper()} v{versao}.pdf'
    with open('deploy/manuais/'+arquivo_nome, "rb") as local_filename:
        content = local_filename.read()

    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename={arquivo_nome}'
    return response

@rtr(template='documentacao/docs.html')
def documentacao_view(request):
    documentacao = None
    if not settings.BEHAVE_AUTO_DOC_PATH:
        return httprr('/', 'A configuração não realizada.', 'error')
    with open(f'{settings.BEHAVE_AUTO_DOC_PATH}/documentacao.json') as fd:
        documentacao_json = json.loads(fd.read())
    documentacao = OrderedDict()
    for aplicacao in documentacao_json['aplicacoes'].values():
        area = aplicacao['area']
        if documentacao.get(area):
            documentacao[area].append(aplicacao)
        else:
            documentacao[area] = [aplicacao]

    documentacao = OrderedDict(sorted(documentacao.items()))

    return locals()


def documentacao_cenario_view(request, aplicacao, funcionalidade, cenario):
    if not settings.BEHAVE_AUTO_DOC_PATH:
        return httprr('/', 'A configuração não realizada.', 'error')
    with open(f'{settings.BEHAVE_AUTO_DOC_PATH}/documentacao.json') as fd:
        documentacao = json.loads(fd.read())

    o_aplicacao = documentacao['aplicacoes'].get(aplicacao)
    for o_funcionalidade in o_aplicacao['funcionalidades']:
        if o_funcionalidade['chave'] == funcionalidade:
            for o_cenario in o_funcionalidade['cenarios']:
                if o_cenario['chave'] == cenario:
                    app_name = o_funcionalidade.get("app_name")
                    feature_name = slugify(o_funcionalidade.get("nome"))
                    cenario_name = slugify(o_cenario.get("nome"))
                    imagem_workflow = f'workflow/{app_name}/{feature_name}.png'
                    if not os.path.isfile(os.path.join(settings.BEHAVE_AUTO_DOC_PATH, imagem_workflow)):
                        imagem_workflow = ''
                    has_bpmn_workflow = os.path.isfile(f'{app_name}/workflows/{cenario_name}.bpmn')
                    context = {'aplicacao_nome': o_aplicacao["nome"], 'aplicacao_sigla': o_aplicacao["sigla"],
                               'funcionalidade': o_funcionalidade, 'cenario': o_cenario, 'workflow': imagem_workflow,
                               'has_bpmn_workflow': has_bpmn_workflow}
                    return render(request, 'comum/templates/documentacao/cenario.html', context)
    return HttpResponseBadRequest('O cenário escolhido não existe na documentação.')


def about_view(request, aplicacao):
    app_config = apps.get_app_config(aplicacao)
    groups = GroupDetail.objects.filter(app=aplicacao)
    perfis_da_app = groups.filter(app_manager=aplicacao).order_by('group__name')
    perfis_fora_app = groups.exclude(app_manager=aplicacao).order_by('group__name')
    with open(f'{settings.BEHAVE_AUTO_DOC_PATH}/documentacao.json') as fd:
        documentacao = json.loads(fd.read())
    documentacao_aplicacao = documentacao['aplicacoes'][aplicacao]
    has_module_bpmn = os.path.isfile(os.path.join(f'{aplicacao}/workflows/{aplicacao}.bpmn'))
    workflows = [(key, value) for key, value in documentacao_aplicacao['workflows'].items()]
    return render(request, 'comum/templates/documentacao/modulo.html', {'aplicacao': aplicacao, 'perfis_da_app': perfis_da_app, 'perfis_fora_app': perfis_fora_app, 'app_config': app_config, 'workflows': workflows, 'has_module_bpmn': has_module_bpmn})


def about_feature_view(request, aplicacao, funcionalidade):
    app_config = apps.get_app_config(aplicacao)
    with open(f'{settings.BEHAVE_AUTO_DOC_PATH}/documentacao.json') as fd:
        documentacao = json.loads(fd.read())
    o_aplicacao = documentacao['aplicacoes'][aplicacao]
    for o_funcionalidade in o_aplicacao['funcionalidades']:
        if o_funcionalidade['chave'] == funcionalidade:
            break

    has_feature_bpmn = os.path.isfile(os.path.join(f'{aplicacao}/workflows/{slugify(funcionalidade)}.bpmn'))
    workflows = [(key, value) for key, value in o_aplicacao['workflows'].items()]
    context = {'aplicacao': o_aplicacao, 'funcionalidade': o_funcionalidade, 'app_config': app_config,
               'workflows': workflows, 'has_feature_bpmn': has_feature_bpmn}
    return render(request, 'comum/templates/documentacao/about_feature.html', context)


def documentacao_imagem_view(request):
    imagem = request.GET.get('i')
    imagem_path = os.path.join(settings.BEHAVE_AUTO_DOC_PATH, imagem)

    if imagem and os.path.exists(imagem_path):
        response = HttpResponse(content_type='image/png')
        with open(imagem_path, 'rb') as fd:
            response.write(fd.read())
        return response
    else:
        return httprr('/', 'Nenhuma imagem encontrada.', 'error')


def documentacao_bpmn_view(request, aplicacao, bpmn):
    return HttpResponse(content=open(os.path.join(f'{aplicacao}/workflows/{bpmn}'), encoding='utf-8').read(),
                        content_type='text/plain')


def login(
        request,
        template_name='comum/templates/login.html',
        redirect_field_name='next',
        authentication_form=AuthenticationFormPlus,
        extra_context=None,
        redirect_authenticated_user=False,
):
    # Verifica se o Login com Gov.BR está habilitado nas configurações do SUAP
    autenticacao_govbr_habilitada = Configuracao.get_valor_por_chave('comum', 'habilitar_autenticacao_govbr')

    if not extra_context:
        extra_context = dict()
    extra_context.update({'settings': settings, 'servicos_anonimos': layout.gerar_servicos_anonimos(request), 'autenticacao_govbr_habilitada': autenticacao_govbr_habilitada})

    response = LoginView.as_view(
        template_name=template_name,
        redirect_field_name=redirect_field_name,
        form_class=authentication_form,
        extra_context=extra_context,
        redirect_authenticated_user=redirect_authenticated_user,
    )(request)

    if request.user.is_authenticated:
        expire_date = datetime.now() + timedelta(days=90)
        try:
            cookie = request.COOKIES.get(settings.SUAP_CONTROL_COOKIE_NAME, '')
            if cookie:
                try:
                    cookie_data = decrypt(cookie)
                except Exception:
                    cookie_data = {}
                usernames = cookie_data.get('usernames', [])
                if request.user.username not in usernames:
                    usernames.append(request.user.username)
            else:
                usernames = [request.user.username]
            suap_control = {
                'usernames': usernames,
                'datetime': expire_date.isoformat()
            }
            suap_control_dump = encrypt(suap_control)
            response.set_cookie(settings.SUAP_CONTROL_COOKIE_NAME, suap_control_dump,
                                expires=expire_date,
                                secure=True,
                                samesite='Strict',
                                )

        except Exception as e:
            if settings.DEBUG:
                raise e
            capture_exception(e)
    return response


def login_exige_captcha(request, username):
    user = User.objects.filter(username=username, login_attempts__gt=3).first()
    if user:
        return HttpResponse('OK')
    else:
        return HttpResponse('ERROR')


@rtr()
@login_required()
def selecionar_vinculo(request):
    '''
    Exibe vínculos ativos do usuário após autenticar com Gov.Br, após seleção do vínculo e clicar no botão Entrar é realizada a autenticação para o user daquele vínculo
    '''
    from django.contrib.auth import login
    title = "Selecionar Vínculo"
    category = 'Acessos'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)

    vinculo_id = request.GET.get('vinculo_id', None)
    message = None

    cpf = get_cpf_formatado(request.user.social_auth.first().uid)
    vinculos_ativos = Vinculo.objects.filter(pessoa__pessoafisica__cpf=cpf, user__is_active=True)
    if vinculos_ativos.exists():
        vinculos = vinculos_ativos
        unico_vinculo = vinculos_ativos.count() == 1
        vinculo_id = request.GET.get('vinculo_id', None) if not unico_vinculo else vinculos_ativos.first().id
        if vinculo_id:
            vinculo = get_object_or_404(Vinculo, pk=vinculo_id)
            request.user = vinculo.user
            request.user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, vinculo.user)
            request.session['autenticou_com_govbr'] = True

            if not unico_vinculo and not vinculo_id:
                message = "Selecione um vínculo para continuar."
                messages.success(request, message)
            return HttpResponseRedirect('/')
    elif not vinculos_ativos.exists() or not request.user.is_authenticated:
        message = "Você não possui vínculo ativo no SUAP."
        messages.error(request, message)
        logout(request)
        return HttpResponseRedirect('/')

    return locals()


@rtr()
def usuarios_ativos(request):
    if not request.user.is_superuser:
        raise Http404
    title = 'Usuários Conectados'
    intervalo = request.GET.get('q', '60')
    if intervalo.isdigit():
        intervalo = int(intervalo)
        if intervalo > 600:
            intervalo = 600
    else:
        raise Http404
    intervalo_formatado = formata_segundos(intervalo, '{h:01.0f} hora(s)', ' {m:01.0f} minuto(s)',
                                           ' {s:01.0f} segundos', True)
    usuarios_list = []

    qtd_um_minuto = 0
    qtd_cinco_minutos = 0
    qtd_dez_minutos = 0
    qtd_uma_hora = 0
    qtd_um_dia = 0

    for uid in request.online_now_ids:
        dados_login = cache.get(f'online-{uid}')
        if dados_login:
            if dados_login[0] + timedelta(minutes=1) > datetime.now():
                qtd_um_minuto += 1
            if dados_login[0] + timedelta(minutes=5) > datetime.now():
                qtd_cinco_minutos += 1
            if dados_login[0] + timedelta(minutes=10) > datetime.now():
                qtd_dez_minutos += 1
            if dados_login[0] + timedelta(hours=1) > datetime.now():
                qtd_uma_hora += 1
            if dados_login[0] + timedelta(days=1) > datetime.now():
                qtd_um_dia += 1

    for usuario in request.online_now:
        dados_login = cache.get(f'online-{usuario.pk}')
        if dados_login:
            usuario.hora_acesso = dados_login[0]
            usuario.url = dados_login[1]
            if usuario.hora_acesso + timedelta(seconds=intervalo) > datetime.now():
                usuarios_list.append(usuario)

    usuarios_list = sorted(usuarios_list, key=lambda user: user.hora_acesso, reverse=True)

    return locals()


def handler500(request):
    """500 error handler which includes ``request`` in the context.

    Templates: `500.html`
    Context: None
    """

    try:  # esta tela não pode quebrar
        servicos_anonimos = layout.gerar_servicos_anonimos(request)
        if request.user.is_authenticated:
            tem_permissao_feedback = None

            full_url = request.build_absolute_uri()
            view = get_view_name_from_url(full_url)
            event_id = last_event_id()

            if all(
                    [tem_permissao_informar_erro(request), full_url, view]
            ):
                tem_permissao_feedback = 'pode_comentar'
    except Exception as e:
        messages.error(request, str(e))
    return render(request, '500.html', locals(), status=500)


@requires_csrf_token
def page_not_found(request, exception, template_name='comum/templates/404.html'):
    """
    Default 404 handler.

    Templates: :template:`404.html`
    Context:
        request_path
            The path of the requested URL (e.g., '/app/pages/bad_page/'). It's
            quoted to prevent a content injection attack.
        exception
            The message from the exception which triggered the 404 (if one was
            supplied), or the exception class name
    """
    exception_repr = exception.__class__.__name__
    # Try to get an "interesting" exception message, if any (and not the ugly
    # Resolver404 dictionary)
    try:
        message = exception.args[0]
    except (AttributeError, IndexError):
        pass
    else:
        if isinstance(message, str):
            exception_repr = message
    context = {
        'request_path': urllib.parse.quote(request.path),
        'exception': exception_repr,
        'servicos_anonimos': layout.gerar_servicos_anonimos(request)
    }
    try:
        template = loader.get_template(template_name)
        body = template.render(context, request)
        content_type = None             # Django will use 'text/html'.
    except TemplateDoesNotExist:
        if template_name != 'comum/templates/404.html':
            # Reraise if it's a missing custom template.
            raise
        # Render template (even though there are no substitutions) to allow
        # inspecting the context in tests.
        template = Engine().from_string(
            ERROR_PAGE_TEMPLATE % {
                'title': 'Not Found',
                'details': 'The requested resource was not found on this server.',
            },
        )
        body = template.render(Context(context))
        content_type = 'text/html'
    return HttpResponseNotFound(body, content_type=content_type)


@requires_csrf_token
def permission_denied(request, exception, template_name='comum/templates/403.html'):
    """
    Permission denied (403) handler.

    Templates: :template:`403.html`
    Context: None

    If the template does not exist, an Http403 response containing the text
    "403 Forbidden" (as per RFC 7231) will be returned.
    """
    try:
        template = loader.get_template(template_name)
        context = {
            'exception': str(exception),
            'servicos_anonimos': layout.gerar_servicos_anonimos(request)
        }
    except TemplateDoesNotExist:
        if template_name != 'comum/templates/403.html':
            # Reraise if it's a missing custom template.
            raise
        return HttpResponseForbidden(
            ERROR_PAGE_TEMPLATE % {'title': '403 Forbidden', 'details': ''},
            content_type='text/html',
        )
    return HttpResponseForbidden(
        template.render(request=request, context=context)
    )

#############################
# Calendário Administrativo #
#############################


@rtr()
@login_required
def calendario_administrativo(request):
    title = 'Calendário Administrativo por Campus'
    uo = request.user.get_relacionamento().setor.uo
    ano = Ano.objects.filter(ano=date.today().year).first()
    form = CalendarioForm(request.POST or None)
    if form.is_valid():
        if form.cleaned_data.get('ano'):
            ano = form.cleaned_data['ano']
        if form.cleaned_data.get('uo'):
            uo = form.cleaned_data['uo']

    calendario = Calendario()
    if 'ponto' in settings.INSTALLED_APPS:
        from ponto.models import Liberacao

        [
            calendario.adicionar_evento_calendario(liberacao.data_inicio, liberacao.data_fim, liberacao.descricao,
                                                   liberacao.get_liberacao_css(), liberacao.descricao)
            for liberacao in Liberacao.get_liberacoes_calendario(uo, ano.ano)
        ]

    if 'ferias' in settings.INSTALLED_APPS and request.user.eh_servidor:
        from ferias.models import Ferias

        data_ini = date(ano.ano, 1, 1)
        data_fim = date(ano.ano, 12, 31)
        periodos = Ferias.get_periodos_pessoa_estava_de_ferias(request.user.get_relacionamento(), data_ini, data_fim)
        for periodo_ini, periodo_fim, label in periodos:
            calendario.adicionar_evento_calendario(periodo_ini, periodo_fim, label, 'ferias', label)

    calendario_ano = calendario.formato_ano(ano.ano)
    return locals()


@rtr()
@login_required
def remote_logout(request, sessioninfo_pk):
    if not request.user.is_superuser:
        session_info = get_object_or_404(SessionInfo, pk=sessioninfo_pk, device__user=request.user)
    else:
        session_info = get_object_or_404(SessionInfo, pk=sessioninfo_pk)
    get_remote_session(session_info.session_id).delete()
    session_info.expired = True
    session_info.save()
    return httprr('/admin/comum/sessioninfo/', 'Sessão remota deslogada com sucesso.')


@rtr()
@login_required
def remote_logout_all(request):
    qs = SessionInfo.objects.filter(device__user=request.user, expired=False).exclude(session_id=request.session.session_key)
    for session_info in qs:
        try:
            get_remote_session(session_info.session_id).delete()
            session_info.expired = True
            session_info.save()
        except Exception as e:
            assert e
            raise e
    return httprr('/admin/comum/sessioninfo/', 'Sessões remotas deslogadas com sucesso.')


@rtr()
@login_required
def deactivate_device(request, device_pk):
    if not request.user.is_superuser:
        device = get_object_or_404(Device, pk=device_pk, user=request.user)
    else:
        device = get_object_or_404(Device, pk=device_pk)

    device.activated = False
    device.save()
    qs = SessionInfo.objects.filter(device=device)
    contador = qs.count()
    for session_info in qs:
        try:
            get_remote_session(session_info.session_id).delete()
        except Exception:
            pass
        session_info.expired = True
        session_info.save()
    return httprr('/admin/comum/device/', f'Dispositivo desativado e {contador} sessões expiradas.')


@rtr()
@login_required
def reactivate_device(request, device_pk):
    if not request.user.is_superuser:
        device = get_object_or_404(Device, pk=device_pk, user=request.user)
    else:
        device = get_object_or_404(Device, pk=device_pk)

    device.activated = True
    device.save()
    return httprr('/admin/comum/device/', 'Dispositivo reativado.')


@rtr()
@login_required
def give_nickname_to_device(request, device_pk):
    device = get_object_or_404(Device, pk=device_pk)

    form = DeviceForm(request.POST or None, request=request, instance=device)
    if form.is_valid():
        form.save()
        return httprr('..', 'Apelido concedido com sucesso.')
    return locals()


@rtr()
@login_required
def webmail(request):
    url_webmail = Configuracao.get_valor_por_chave('comum', 'url_webmail')
    return HttpResponseRedirect(url_webmail)


@rtr()
@login_required
def azure(request):
    servidor = request.user.get_relacionamento()
    if not servidor.tem_acesso_servicos_microsoft():
        return HttpResponseForbidden('Usuário não tem acesso a essa página')
    url = URL_AZURE
    return HttpResponseRedirect(url)


@rtr()
@login_required
def google_classroom(request):
    sub_instance = request.user.get_relacionamento()
    if (hasattr(sub_instance, 'email_google_classroom') and sub_instance.email_google_classroom) or \
            request.user.groups.filter(name='Usuários do Google Classroom').exists():
        return HttpResponseRedirect('/ldap_backend/redirecionar_google_classroom/')
    return HttpResponseForbidden('Usuário não tem acesso a essa página')


@rtr()
@login_required
def documentos_emitidos_suap(request):
    title = 'Meus Documentos SUAP'
    dados = []
    documentos.signal.send(sender=documentos_emitidos_suap, request=request, data=dados)
    areas = {}
    for area, categoria, subcategoria, descricao, url in dados:
        if area not in areas:
            areas[area] = {}
        if categoria not in areas[area]:
            areas[area][categoria] = {}
        if subcategoria not in areas[area][categoria]:
            areas[area][categoria][subcategoria] = []
        areas[area][categoria][subcategoria].append((descricao, url))
    return locals()


@rtr()
@permission_required('comum.view_registronotificacao')
def notificacoes(request):
    title = "Notificações Não Lidas"
    vinculo = request.user.get_vinculo()
    hoje = datetime.now()
    sub = RegistroNotificacao.objects.filter(vinculo=vinculo, lida=False, notificacao__objeto_relacionado=OuterRef('notificacao__objeto_relacionado')).order_by('-data')
    todas_notificacoes_com_objeto = RegistroNotificacao.objects.filter(lida=False, vinculo=vinculo, id__in=Subquery(sub.values('id')[:1]))
    todas_notificacoes_sem_objeto = RegistroNotificacao.objects.filter(lida=False, vinculo=vinculo, notificacao__objeto_relacionado__isnull=True)
    todas_notificacoes = (todas_notificacoes_com_objeto | todas_notificacoes_sem_objeto).order_by('-data')
    notificacoes = list(todas_notificacoes[:10])

    # Seta a Notificação e Marca como Lida
    notificacao = todas_notificacoes.first()
    if notificacao and not notificacao.lida and notificacao.pode_ler():
        notificacao.lida = True
        notificacao.save()

    # Extras
    qtd_notificacoes_antigas = RegistroNotificacao.objects.filter(
        vinculo=request.user.get_vinculo(), lida=True, data__lt=somar_data(datetime.today(), -30)
    ).count()
    return locals()


@rtr()
@permission_required('comum.view_registronotificacao')
def notificacao(request, pk):
    notificacao = get_object_or_404(RegistroNotificacao.objects, pk=pk)
    vinculo = request.user.get_vinculo()
    title = "Notificação"

    if not notificacao.vinculo == vinculo:
        raise PermissionDenied('Você não tem permissão de acesso a essa notificação.')

    # Seta a Notificação e Marca como Lida
    if not notificacao.lida and notificacao.pode_ler():
        notificacao.lida = True
        notificacao.save()

    if request.GET.get("ajax"):
        return render(request, 'notificacao_artigo.html', locals())

    return locals()


@rtr()
@permission_required('comum.view_registronotificacao')
def busca_notificacao(request, counter):
    try:
        registro = RegistroNotificacao.objects.filter(vinculo=request.user.get_vinculo(), lida=False)[counter]
        html = render(request, 'notificacao_ancora.html', {'notificacao': registro, 'counter': counter + 1})
        return JsonResponse(dict(itens=html.content.decode()))
    except Exception:
        return None


@login_required()
def ativar_categoria_notificacao(request, pk):
    categoria = get_object_or_404(CategoriaNotificacao, pk=pk)
    categoria.ativa = True
    categoria.save()

    return httprr('..', 'A Categoria de Notificações foi ativada com sucesso.')


@login_required()
def desativar_categoria_notificacao(request, pk):
    categoria = get_object_or_404(CategoriaNotificacao, pk=pk)
    categoria.ativa = False
    categoria.save()

    return httprr('..', 'A Categoria de Notificações foi desativada com sucesso.')


@login_required()
def atualizar_preferencia_padrao(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    envio = request.GET.get('envio', 'suap')
    is_ajax = request.GET.get('is_ajax', 'False')

    preferencia = Preferencia.objects.filter(usuario=request.user).first()
    if not preferencia:
        preferencia = Preferencia.objects.create(usuario=request.user)

    mensagem_erro = 'Não é possível inativar as duas formas de Notificação.'

    if envio == 'suap':
        if preferencia.via_suap:
            if not preferencia.via_email:
                if is_ajax == "True":
                    return HttpResponseForbidden(mensagem_erro)
                else:
                    return httprr(url_origem, mensagem_erro, 'error')
            else:
                preferencia.via_suap = False
        else:
            preferencia.via_suap = True

    elif envio == 'email':
        if preferencia.via_email:
            if not preferencia.via_suap:
                if is_ajax == "True":
                    return HttpResponseForbidden(mensagem_erro)
                else:
                    return httprr(url_origem, mensagem_erro, 'error')
            else:
                preferencia.via_email = False
        else:
            preferencia.via_email = True

    preferencia.save()

    return httprr(url_origem, 'Preferência atualizada com sucesso.')


@login_required()
def atualizar_via_suap(request, pk):
    url_origem = request.META.get('HTTP_REFERER', '.')
    preferencia = get_object_or_404(PreferenciaNotificacao, pk=pk, categoria__forcar_habilitacao=False)
    if preferencia.via_suap:
        if not preferencia.via_email:
            return httprr(url_origem,
                          'Não é possível inativar as duas formas de Notificação.', 'error')
        else:
            mensagem = 'Envio via SUAP desativado.'
            preferencia.via_suap = False
    else:
        mensagem = 'Envio via SUAP ativado.'
        preferencia.via_suap = True
    preferencia.save()

    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=get_content_type_for_model(preferencia).pk,
        object_id=preferencia.pk,
        object_repr=force_str(preferencia),
        action_flag=CHANGE,
        change_message=mensagem,
    )

    return httprr(url_origem, 'Preferência atualizada com sucesso.')


@login_required()
def ativar_via_suap_em_lote(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    ids = request.GET.get('ids').split(',')
    preferencias = PreferenciaNotificacao.objects.filter(pk__in=ids, categoria__forcar_habilitacao=False)
    for preferencia in preferencias:
        preferencia.via_suap = True
        preferencia.save()

        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=get_content_type_for_model(preferencia).pk,
            object_id=preferencia.pk,
            object_repr=force_str(preferencia),
            action_flag=CHANGE,
            change_message='Envio via SUAP ativado.',
        )

    return httprr(url_origem, 'Preferências atualizadas com sucesso.')


@login_required()
def desativar_via_suap_em_lote(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    ids = request.GET.get('ids').split(',')
    preferencias = PreferenciaNotificacao.objects.filter(pk__in=ids, categoria__forcar_habilitacao=False)
    for preferencia in preferencias:
        if preferencia.via_email:
            preferencia.via_suap = False
            preferencia.save()

            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=get_content_type_for_model(preferencia).pk,
                object_id=preferencia.pk,
                object_repr=force_str(preferencia),
                action_flag=CHANGE,
                change_message='Envio via SUAP desativado.',
            )

    return httprr(url_origem, 'Preferências atualizadas com sucesso.')


@login_required()
def atualizar_via_email(request, pk):
    url_origem = request.META.get('HTTP_REFERER', '.')
    preferencia = get_object_or_404(PreferenciaNotificacao, pk=pk, categoria__forcar_habilitacao=False)
    if preferencia.via_email:
        if not preferencia.via_suap:
            return httprr(url_origem,
                          'Não é possível inativar as duas formas de Notificação.', 'error')
        else:
            mensagem = 'Envio via E-mail desativado.'
            preferencia.via_email = False
    else:
        mensagem = 'Envio via E-mail ativado.'
        preferencia.via_email = True
    preferencia.save()

    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=get_content_type_for_model(preferencia).pk,
        object_id=preferencia.pk,
        object_repr=force_str(preferencia),
        action_flag=CHANGE,
        change_message=mensagem,
    )

    return httprr(url_origem, 'Preferência atualizada com sucesso.')


@login_required()
def ativar_via_email_em_lote(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    ids = request.GET.get('ids').split(',')
    preferencias = PreferenciaNotificacao.objects.filter(pk__in=ids, categoria__forcar_habilitacao=False)
    for preferencia in preferencias:
        preferencia.via_email = True
        preferencia.save()

        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=get_content_type_for_model(preferencia).pk,
            object_id=preferencia.pk,
            object_repr=force_str(preferencia),
            action_flag=CHANGE,
            change_message='Envio via E-mail ativado.',
        )

    return httprr(url_origem, 'Preferências atualizadas com sucesso.')


@login_required()
def desativar_via_email_em_lote(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    ids = request.GET.get('ids').split(',')
    preferencias = PreferenciaNotificacao.objects.filter(pk__in=ids, categoria__forcar_habilitacao=False)
    for preferencia in preferencias:
        if preferencia.via_suap:
            preferencia.via_email = False
            preferencia.save()

            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=get_content_type_for_model(preferencia).pk,
                object_id=preferencia.pk,
                object_repr=force_str(preferencia),
                action_flag=CHANGE,
                change_message='Envio via E-mail desativado.',
            )

    return httprr(url_origem, 'Preferências atualizadas com sucesso.')


@permission_required('comum.view_registronotificacao')
def marcar_como_lida(request, pk):
    registro = get_object_or_404(RegistroNotificacao, pk=pk)

    if registro.vinculo == request.user.get_vinculo() and registro.pode_ler():
        registro.lida = True
        registro.save()
    else:
        raise PermissionDenied('Você não pode marcar esta notificação como lida.')

    RegistroNotificacao.limpar_cache(request.user)
    return HttpResponse('OK')


@permission_required('comum.view_registronotificacao')
def marcar_todas_notificacoes_como_lidas(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    registros = RegistroNotificacao.objects.filter(vinculo=request.user.get_vinculo(), lida=False, data_permite_marcar_lida__gte=datetime.now())
    registros.update(lida=True)
    
    RegistroNotificacao.limpar_cache(request.user)
    return httprr(url_origem, 'Todas as suas notificações foram marcadas como lida com sucesso.')


@permission_required('comum.view_registronotificacao')
def excluir_notificacoes_antigas(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    notificacoes_antigas = RegistroNotificacao.objects.filter(
        vinculo=request.user.get_vinculo(), lida=True, data__lt=somar_data(datetime.today(), -30)
    )
    notificacoes_antigas.delete()

    RegistroNotificacao.limpar_cache(request.user)
    return httprr(url_origem, 'Todas as suas notificações lidas há mais de um mês foram excluídas.')


@permission_required('comum.view_registronotificacao')
def marcar_como_lida_em_lote(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    ids = request.GET.get('ids').split(',')
    for pk in ids:
        registro = get_object_or_404(RegistroNotificacao, pk=pk, vinculo=request.user.get_vinculo())
        if registro.pode_ler():
            registro.lida = True
            registro.save()

    RegistroNotificacao.limpar_cache(request.user)
    return httprr(url_origem, 'Notificações marcadas como lida com sucesso.')


@permission_required('comum.view_registronotificacao')
def marcar_como_nao_lida(request, pk):
    registro = get_object_or_404(RegistroNotificacao, pk=pk)
    if registro.vinculo == request.user.get_vinculo():
        registro.lida = False
        registro.save()
    else:
        raise PermissionDenied('Você não pode marcar esta notificação como não lida.')

    RegistroNotificacao.limpar_cache(request.user)
    return HttpResponse('OK')


@permission_required('comum.view_registronotificacao')
def marcar_como_nao_lida_em_lote(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    ids = request.GET.get('ids').split(',')
    for pk in ids:
        registro = get_object_or_404(RegistroNotificacao, pk=pk, vinculo=request.user.get_vinculo())
        registro.lida = False
        registro.save()

    RegistroNotificacao.limpar_cache(request.user)
    return httprr(url_origem, 'Notificações marcadas como não lidas com sucesso.')


@permission_required('comum.view_registronotificacao')
def remover_notificacao(request, pk):
    opcao = request.GET.get('opcao')
    if opcao == "1":  # veio da url de visualizacao da notificacao
        url = "/"
    else:
        url = request.META.get('HTTP_REFERER', '.')
    registro = get_object_or_404(RegistroNotificacao, pk=pk, vinculo=request.user.get_vinculo())
    if registro.vinculo == request.user.get_vinculo():
        if registro.pode_excluir():
            registro.delete()
        else:
            data = format_(registro.data_permite_excluir)
            return httprr(url, f'O registro só poderá excluído em {data}.', 'error')
    else:
        raise PermissionDenied('Você não tem permissão de acesso a essa página.')

    RegistroNotificacao.limpar_cache(request.user)
    return httprr(url, 'A notificação foi removida com sucesso.')


@permission_required('comum.view_registronotificacao')
def remover_notificacoes_em_lote(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    ids = request.GET.get('ids').split(',')
    agora = datetime.now()
    for pk in ids:
        registro = get_object_or_404(RegistroNotificacao, pk=pk, vinculo=request.user.get_vinculo())
        if registro.data_permite_excluir <= agora:
            registro.delete()

    RegistroNotificacao.limpar_cache(request.user)
    return httprr(url_origem, 'Notificações removidas com sucesso.')


@rtr()
@group_required('Gerente de Usuário Externo')
def cadastrar_usuario_externo(request, pessoafisica_id=None):
    """
    Pré cadastro de Usuário Externo

    :param pessoafisica_id:
    :param request:
    :return:
    """

    title = 'Adicionar Usuário Externo'
    initial = dict()
    if pessoafisica_id:
        pessoafisica = PessoaFisica.objects.filter(pk=pessoafisica_id).first()
        initial['cpf'] = pessoafisica.cpf
        initial['nome'] = pessoafisica.nome
        initial['email'] = pessoafisica.email
        initial['confirma_email'] = pessoafisica.email

    form = UsuarioExternoForm(request.POST or None, request=request, initial=initial)

    if form.is_valid():
        try:
            usuario_externo = UsuarioExterno()
            usuario_externo.nome = form.cleaned_data['nome']
            usuario_externo.cpf = form.cleaned_data['cpf']
            usuario_externo.email = form.cleaned_data['email']
            usuario_externo.email_secundario = form.cleaned_data['email']
            usuario_externo.ativo = False
            usuario_externo.eh_prestador = False
            usuario_externo.usuario_externo = True
            usuario_externo.justificativa_cadastro = form.cleaned_data['justificativa']
            usuario_externo.save()
            usuario_externo.enviar_email_pre_cadastro()

            # Ativa o usuário externo criando o papel caso não possua
            usuario_externo.ativar()

            # Cria um registro para o UserSocialAuth para permitir o login com Gov.BR
            from social_django.models import UserSocialAuth
            num_cpf = usuario_externo.cpf.replace('.', '').replace('-', '')
            if not UserSocialAuth.objects.filter(uid=num_cpf).exists():
                UserSocialAuth.objects.create(user=usuario_externo.get_user(), uid=num_cpf, provider="govbr")

            # Preenche dados pessoais caso tenha obtido via API do CPF
            from djtools.services import consulta_cidadao
            sucesso, dados_cidadao = consulta_cidadao([form.cleaned_data["cpf"]])
            sexo = {1: 'M', 2: 'F', 3: None}
            if sucesso:
                dados_cidadao = dados_cidadao[0]
                usuario_externo.nome = dados_cidadao.get("Nome", None)
                usuario_externo.sexo = sexo.get(dados_cidadao.get("Sexo"), None)
                usuario_externo.nome_mae = dados_cidadao.get("NomeMae", None)
                usuario_externo.nome_pai = dados_cidadao.get("NomePai", None)
                usuario_externo.save()

            return httprr('..', f"Usuário Externo cadastrado com sucesso. Foi enviado um e-mail para "
                          f"{form.cleaned_data['email']} com instruções para acessar o SUAP.")

        except Exception as e:
            if settings.DEBUG:
                raise e
            return httprr('..', message=str(f"Houve um erro ao cadastrar o usuário. Detalhes: {e}"), tag='error')

    return locals()


@rtr()
@group_required('Gerente de Usuário Externo')
def ativar_usuario_externo(request, pk):
    usuarioexterno = get_object_or_404(UsuarioExterno, pk=pk)
    usuarioexterno.ativar()

    if usuarioexterno.ativo:
        return httprr('/admin/comum/usuarioexterno/', message="Usuário Externo Ativado com Sucesso.", tag='success')

    return locals()


@rtr()
@group_required('Gerente de Usuário Externo')
def inativar_usuario_externo(request, pk):
    usuarioexterno = get_object_or_404(UsuarioExterno, pk=pk)
    usuarioexterno.inativar()
    if not usuarioexterno.ativo:
        return httprr('/admin/comum/usuarioexterno/', message="Usuário Externo Desativado com Sucesso.", tag='success')

    return locals()


@rtr()
@group_required('Gerente de Usuário Externo')
def usuario_externo(request, pk):
    obj = get_object_or_404(UsuarioExterno.objects, pk=pk)

    title = f"{obj.nome} - {obj.cpf}"

    return locals()


@rtr()
@permission_required('comum.view_predio')
def predio(request, pk):
    obj = Predio.objects.get(pk=pk)
    obra_original = obj.get_obra_original()
    ampliacoes = obj.get_ampliacoes()
    reformas = obj.get_reformas()
    combates = obj.get_combates_incendio_panico()
    title = str(obj)
    return locals()


def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /', content_type='text/plain')
