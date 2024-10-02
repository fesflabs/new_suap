import datetime

from djtools.utils.response import render_to_string
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404
from comum.models import UsuarioGrupoSetor
from comum.utils import somar_data, get_uo
from edu.models import CoordenadorPolo, CursoCampus
from djtools import layout
from djtools.templatetags.filters import format_, in_group
from djtools.utils import rtr, httprr, permission_required, XlsResponse, normalizar_nome_proprio, JsonResponse
from edu.models import Diretoria
from processo_seletivo.forms import (
    ImportarEditalForm,
    ImportarEditalXMLForm,
    MatricularAlunoProitecForm,
    ListaForm,
    InscricaoFiscalForm,
    PrecedenciaMigracaoForm,
    RealizarAcaoLote,
    DefinirPrecedenciaMatriculaForm,
    DefinirConfiguracaoMigracaoVagaForm,
    VincularMatriculaForm,
    CriacaoVagaRemanescenteForm,
    EditalAusentarCandidatosForm, EditalLiberacaoForm, EditarOfertaVagaCursoForm)
from processo_seletivo.models import (
    Edital,
    OfertaVaga,
    Candidato,
    Lista,
    InscricaoFiscal,
    EditalAdesaoCampus,
    ConfiguracaoMigracaoVaga,
    PrecedenciaMigracao,
    CandidatoVaga,
    OfertaVagaCurso, EditalPeriodoLiberacao, EditalPeriodoLiberacaoHistorico)
from rh.models import UnidadeOrganizacional


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    for edital in EditalAdesaoCampus.editais_abertos(request.user):
        inscricoes.append(dict(url='/processo_seletivo/inscricao_em_edital/{}'.format(edital.pk), titulo='Inscrição para Fiscal de Concurso para Edital: {}'.format(edital)))

    return inscricoes


@rtr()
@permission_required('processo_seletivo.add_edital')
def importar_edital_xml(request, pk):
    title = 'Importar Edital - XML'
    obj = get_object_or_404(Edital, pk=pk)
    form = ImportarEditalXMLForm(data=request.POST or None, files=request.POST and request.FILES or None)
    if form.is_valid():
        return form.processar(obj)
    return locals()


@rtr()
@permission_required('processo_seletivo.add_edital')
def importar_edital(request):
    title = 'Importar Edital'
    form = ImportarEditalForm(request.POST or None)
    if form.is_valid():
        edital = form.editais_disponiveis_webservices[form.cleaned_data['edital']]
        return form.processar(request)
    return locals()


@permission_required('processo_seletivo.view_edital')
def oferta_vaga_curso_ajax(request, pk):
    oferta_vaga_curso = OfertaVagaCurso.objects.get(pk=pk)
    total_vagas = oferta_vaga_curso.get_total_vagas(True)
    total_matriculados = oferta_vaga_curso.get_total_matriculados()
    html = render_to_string('processo_seletivo/templates/oferta_vaga_curso_ajax.html', locals())
    return JsonResponse({'html': html})


@rtr()
@permission_required('processo_seletivo.view_edital')
def edital(request, pk):
    obj = get_object_or_404(Edital, pk=pk)
    conf = obj.configuracao_migracao_vagas
    pks_uos_edital = OfertaVagaCurso.locals.filter(edital=obj).values_list('curso_campus__diretoria__setor__uo', flat=True)
    polos = OfertaVagaCurso.locals.filter(edital=obj).exclude(campus_polo='').values_list('campus_polo', flat=True).distinct()
    is_administrador = in_group(request.user, 'Administrador Acadêmico')
    uos = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_edital)
    if not is_administrador:
        groups_user = request.user.get_groups('processo_seletivo.view_edital').values_list('name', flat=True)
        uos_pk = UsuarioGrupoSetor.objects.filter(usuario_grupo__user=request.user, usuario_grupo__group__name__in=groups_user).values_list('setor__uo', flat=True)
        uos = uos.filter(pk__in=uos_pk)
    configuracao_chamada_id = request.GET.get('del_configuracao_chamada_id')
    candidato = request.GET.get('candidato')
    uo_selecionada = int(request.GET.get('uo_selecionada') or uos.count() == 1 and uos.first().pk or 0)
    polo_selecionado = request.GET.get('polo_selecionado') or polos.count() == 1 and polos.first() or ''
    xls_candidatos = request.GET.get('xls_candidatos')
    pk_diretorias = Diretoria.locals.values_list('pk', flat=True)
    ofertas_vagas_curso_resumo = []
    for curso_campus in CursoCampus.objects.filter(pk__in=obj.ofertavagacurso_set.values_list('curso_campus', flat=True).distinct(), diretoria__in=pk_diretorias).order_by(
        'diretoria'
    ):
        ofertas_vagas_curso_resumo.append(
            dict(curso_campus=curso_campus, qtd_inscritos=sum(obj.ofertavagacurso_set.filter(curso_campus=curso_campus).values_list('qtd_inscritos', flat=True)))
        )
    candidatos = obj.candidato_set.all().order_by('nome')
    pendencias = obj.get_pendencias()

    nova_chamada = request.GET.get('nova_chamada')
    if nova_chamada:
        oferta_vaga_curso = OfertaVagaCurso.objects.get(pk=nova_chamada)
        convocados = oferta_vaga_curso.realizar_nova_chamada()
        return httprr(
            '/processo_seletivo/edital/{}/?tab=vagas&uo_selecionada={}&polo_selecionado={}'.format(pk, uo_selecionada, polo_selecionado),
            'Convocação realizada com sucesso. {} candidato(s) convocado(s).'.format(len(convocados)),
        )
    cancelar_chamada = request.GET.get('cancelar_chamada')
    if cancelar_chamada:
        oferta_vaga_curso = OfertaVagaCurso.objects.get(pk=cancelar_chamada)
        oferta_vaga_curso.cancelar_ultima_chamada()
        return httprr(
            '/processo_seletivo/edital/{}/?tab=vagas&uo_selecionada={}&polo_selecionado={}'.format(pk, uo_selecionada, polo_selecionado), 'Última chamada cancelada com sucesso.'
        )

    if candidato:
        candidatos = (candidatos.filter(nome__unaccent__icontains=candidato) | candidatos.filter(cpf__icontains=candidato)).distinct()
    else:
        candidato = ''

    pks_polos = None
    ofertas_vagas_curso = OfertaVagaCurso.objects.none()
    if request.user.groups.filter(name='Coordenador de Polo EAD').exists():
        polos = CoordenadorPolo.objects.filter(funcionario=request.user.get_profile()).values_list('polo__descricao', flat=True)
        pks_polos = CandidatoVaga.objects.filter(candidato__campus_polo__in=polos).values_list('oferta_vaga__oferta_vaga_curso', flat=True).distinct()
        candidatos = candidatos.filter(campus_polo__in=polos)
        ofertas_vagas_curso_resumo = ofertas_vagas_curso_resumo.filter(campus_polo__in=polos)

    if request.GET.get('tab') == 'vagas' and uo_selecionada:
        ofertas_vagas_curso = OfertaVagaCurso.locals.filter(edital_id=obj.pk, curso_campus__diretoria__setor__uo_id=uo_selecionada).order_by('curso_campus__diretoria__setor__uo__nome', 'turno', 'curso_campus__descricao')

        if not obj.possui_curso_proitec():
            ofertas_vagas_curso = ofertas_vagas_curso.filter(campus_polo=polo_selecionado)

        if pks_polos:
            ofertas_vagas_curso = ofertas_vagas_curso.filter(pk__in=pks_polos)

    if request.GET.get('tab') == 'candidatos':
        if uo_selecionada:
            candidatos = (candidatos.filter(candidatovaga__oferta_vaga__oferta_vaga_curso__curso_campus__diretoria__setor__uo__pk=uo_selecionada)).distinct()

        if not obj.possui_curso_proitec() and polo_selecionado:
            candidatos = candidatos.filter(campus_polo=polo_selecionado)

    lista_convocados = request.GET.get('lista_convocados')
    if lista_convocados:
        convocados = []
        if lista_convocados == '0':
            rows = [['Curso', 'Chamada', 'Lista', 'Classificação', 'CPF', 'Nome', 'Telefone', 'E-mail', 'Nº Inscrição', 'Situação', 'Matrícula', 'Situação da Matrícula']]
            for oferta_vaga_curso in ofertas_vagas_curso:
                convocados_chamada = oferta_vaga_curso.get_numero_ultima_chamada()
                qs_convocados = CandidatoVaga.objects.filter(convocacao=convocados_chamada, oferta_vaga__oferta_vaga_curso=oferta_vaga_curso).order_by('oferta_vaga__oferta_vaga_curso', 'oferta_vaga', 'classificacao')
                for candidato_vaga in qs_convocados:
                    convocados.append((oferta_vaga_curso, candidato_vaga, convocados_chamada))

        else:
            rows = [['Chamada', 'Lista', 'Classificação', 'CPF', 'Nome', 'Telefone', 'E-mail', 'Nº Inscrição']]
            convocados_chamada = request.GET.get('chamada')
            qs_convocados = CandidatoVaga.objects.filter(convocacao=convocados_chamada, oferta_vaga__oferta_vaga_curso=lista_convocados).order_by('oferta_vaga', 'classificacao')
            for candidato_vaga in qs_convocados:
                convocados.append((None, candidato_vaga, convocados_chamada))

        for oferta_vaga_curso, candidato_vaga, convocados_chamada in convocados:
            row = []
            if oferta_vaga_curso:
                row.append('{} - {} - {}'.format(
                    oferta_vaga_curso.curso_campus.codigo,
                    oferta_vaga_curso.curso_campus.descricao_historico,
                    oferta_vaga_curso.turno
                ))
            row.extend((
                convocados_chamada,
                format_(candidato_vaga.oferta_vaga.lista),
                format_(candidato_vaga.classificacao),
                format_(candidato_vaga.candidato.cpf),
                format_(candidato_vaga.candidato.nome),
                format_(candidato_vaga.candidato.telefone),
                format_(candidato_vaga.candidato.email),
                format_(candidato_vaga.candidato.inscricao),
            ))
            if oferta_vaga_curso:
                aluno = candidato_vaga.get_aluno()
                row.extend((
                    candidato_vaga.get_situacao_display(),
                    format_(aluno and aluno.matricula or ''),
                    format_(aluno and aluno.situacao.descricao or ''),
                ))
            rows.append(row)
        return XlsResponse(rows)

    if xls_candidatos:
        rows = [['#', 'Nº Inscrição', 'CPF', 'Nome', 'Telefone', 'E-mail', 'Código do Curso', 'Nome do Curso',
                 'Diretoria', 'Lista', 'Classificação', 'Situação']]
        count = 0
        for cv in CandidatoVaga.objects.filter(candidato__in=candidatos.values_list('pk', flat=True)).order_by(
            'candidato'
        ):
            count += 1
            row = [
                count,
                format_(cv.candidato.inscricao),
                format_(cv.candidato.cpf),
                format_(cv.candidato.nome),
                format_(cv.candidato.telefone),
                format_(cv.candidato.email),
                format_(cv.oferta_vaga.oferta_vaga_curso.curso_campus.codigo),
                format_(cv.oferta_vaga.oferta_vaga_curso.curso_campus.descricao),
                format_(cv.oferta_vaga.oferta_vaga_curso.curso_campus.diretoria),
                format_(cv.oferta_vaga.lista),
                format_(cv.classificacao),
                format_(cv.get_situacao_display()),
            ]
            rows.append(row)
        return XlsResponse(rows)

    if request.GET.get('tab') == 'liberacao':
        liberacoes = EditalPeriodoLiberacao.objects.filter(edital=obj).order_by('uo__sigla')
        if uo_selecionada:
            liberacoes = liberacoes.filter(uo=uo_selecionada)

    title = str(obj)
    return locals()


@rtr()
@permission_required('processo_seletivo.pode_liberar_periodos')
def edital_periodo_liberacao(request, edital_pk, pk=None):
    edital = get_object_or_404(Edital, pk=edital_pk)

    editar = pk is not None

    title = 'Adicionar Período'

    pks_uos_edital = OfertaVagaCurso.locals.filter(edital=edital).values_list('curso_campus__diretoria__setor__uo', flat=True)
    pks_uos_cadastradas = EditalPeriodoLiberacao.objects.filter(edital=edital).values_list('uo')

    form = None

    if not editar:
        form = EditalLiberacaoForm(request.POST or None, request=request, edital=edital, uos_edital=pks_uos_edital)
    else:
        title = 'Alterar Período'
        liberacao = get_object_or_404(EditalPeriodoLiberacao, pk=pk)
        form = EditalLiberacaoForm(request.POST or None, request=request, edital=edital, uos_edital=pks_uos_edital, instance=liberacao)

    if form.is_valid():
        form.save()
        return httprr('..', 'Período de Liberação salvo.')

    return locals()


@rtr()
@permission_required('processo_seletivo.pode_liberar_periodos')
def historico_edital_periodo_liberacao(request, edital_liberacao_periodo_pk):
    edital_liberacao_periodo = get_object_or_404(EditalPeriodoLiberacao, pk=edital_liberacao_periodo_pk)
    title = 'Histórico de Liberação de Período'
    historico_liberacoes = EditalPeriodoLiberacaoHistorico.objects.filter(periodo_liberacao=edital_liberacao_periodo)
    return locals()


@rtr()
@permission_required('processo_seletivo.pode_ausentar_candidatos')
def edital_ausentar_candidatos(request, pk):
    edital = get_object_or_404(Edital, pk=pk)

    uo_usuario = None

    if not in_group(request.user, 'Administrador Acadêmico'):
        uo_usuario = get_uo(request.user)

    if not edital.pode_ausentar(request.user, uo_usuario):
        raise PermissionDenied

    title = 'Ausentar Candidatos em Chamadas'

    form = EditalAusentarCandidatosForm(request.POST or None, edital=edital, request=request)

    if form.is_valid():
        candidatos_vaga = CandidatoVaga.objects.filter(
            candidato__edital=edital,
            convocacao=form.cleaned_data['chamada'],
            oferta_vaga__oferta_vaga_curso__curso_campus__diretoria__setor__uo=form.cleaned_data['campus']
        ).filter(Q(situacao__isnull=True) | Q(situacao=CandidatoVaga.AUSENTE))
        for candidato_vaga in candidatos_vaga:
            candidato_vaga.registrar_ausencia()
        return httprr('.', 'Candidatos ausentados com sucesso.')
    return locals()


@rtr()
@permission_required('processo_seletivo.view_edital')
def oferta_vaga(request, pk):
    obj = get_object_or_404(OfertaVaga, pk=pk)
    title = '{} - {} ({})'.format(obj.oferta_vaga_curso.edital, obj.oferta_vaga_curso.curso_campus.descricao, obj.lista.descricao)
    candidatos = obj.get_candidatos_classificados()

    return locals()


@rtr()
@permission_required('processo_seletivo.view_edital')
def visualizar_vagas(request, pk, tipo):
    oferta_vaga = get_object_or_404(OfertaVaga, pk=pk)
    title = str(oferta_vaga.lista)
    vagas = oferta_vaga.vaga_set.none()
    if tipo == 0:
        vagas = oferta_vaga.vaga_set.all()
    elif tipo == 1:
        vagas = oferta_vaga.vaga_set.filter(candidatovaga__situacao=CandidatoVaga.MATRICULADO)
    elif tipo == 2:
        vagas = oferta_vaga.get_vagas_usadas_de_migracao()
    elif tipo == 3:
        vagas = oferta_vaga.get_vagas_usadas_em_migracao()
    vagas_ordenadas = vagas.order_by('candidatovaga__convocacao', 'candidatovaga__classificacao')
    if oferta_vaga.oferta_vaga_curso.edital.configuracao_migracao_vagas_id:
        listas = oferta_vaga.oferta_vaga_curso.edital.configuracao_migracao_vagas.get_nomes_listas_ordenadas_por_restricao()
        vagas_ordenadas = []
        for descricao in listas:
            for vaga in vagas.filter(oferta_vaga__lista__descricao=descricao).order_by('id'):
                vagas_ordenadas.append(vaga)
    return locals()


@rtr()
@permission_required('processo_seletivo.view_edital')
def classificados(request, pk, polo=None):
    oferta_vaga = get_object_or_404(OfertaVaga, pk=pk)
    candidatos_vagas = oferta_vaga.candidatovaga_set.all().order_by('-aprovado', 'candidato__campus_polo', 'classificacao', 'candidato__turno')
    polos = (
        candidatos_vagas.filter(candidato__campus_polo__isnull=False)
        .exclude(candidato__campus_polo='')
        .order_by('candidato__campus_polo')
        .values_list('candidato__campus_polo', flat=True)
        .distinct()
    )

    data_fim_matricula = None
    pode_realizar_acao = True
    is_administrador = in_group(request.user, 'Administrador Acadêmico')

    if request.user.groups.filter(name='Coordenador de Polo EAD').exists():
        polos = CoordenadorPolo.objects.filter(funcionario=request.user.get_profile()).values_list('polo__descricao', flat=True)
        if oferta_vaga.oferta_vaga_curso.edital.matricula_no_polo:
            pode_realizar_acao = True

    liberacao = EditalPeriodoLiberacao.objects.filter(
        edital=oferta_vaga.oferta_vaga_curso.edital, uo=oferta_vaga.oferta_vaga_curso.curso_campus.diretoria.setor.uo
    ).first()
    if liberacao:
        pode_realizar_acao = liberacao.data_limite_avaliacao and datetime.datetime.now() <= somar_data(liberacao.data_limite_avaliacao, 30)
    else:
        pode_realizar_acao = True

    if not polo and polos:
        polo = polos[0]
    if polo:
        candidatos_vagas = candidatos_vagas.filter(candidato__campus_polo=polo)
    q = request.GET.get('q', None)
    if q:
        candidatos_vagas = candidatos_vagas.filter(candidato__cpf=q) | candidatos_vagas.filter(candidato__nome__unaccent__icontains=q)
    page = 1
    is_debug = settings.DEBUG
    if 'page' in request.GET:
        page = request.GET['page']

    if 'ausencia' in request.GET and (is_debug or pode_realizar_acao):
        candidato_vaga = CandidatoVaga.objects.get(pk=request.GET['ausencia'])
        candidato_vaga.registrar_ausencia()

        url = '/processo_seletivo/classificados/{}/?page={}#{}'.format(pk, page, candidato_vaga.pk)
        if polo:
            url = '/processo_seletivo/classificados/{}/{}/?page={}#{}'.format(pk, polo, page, candidato_vaga.pk)

        return httprr(url, 'Ausência registrada com sucesso.')
    if 'inaptidao' in request.GET and (is_debug or pode_realizar_acao):
        candidato_vaga = CandidatoVaga.objects.get(pk=request.GET['inaptidao'])
        candidato_vaga.registrar_inaptidao()

        url = '/processo_seletivo/classificados/{}/?page={}#{}'.format(pk, page, candidato_vaga.pk)
        if polo:
            url = '/processo_seletivo/classificados/{}/{}/?page={}#{}'.format(pk, polo, page, candidato_vaga.pk)

        return httprr(url, 'Inaptidão registrada com sucesso.')

    if 'simular' in request.GET and (is_debug or pode_realizar_acao):
        candidato_vaga = CandidatoVaga.objects.get(pk=request.GET['simular'])
        candidato_vaga.simular_matricula()
        url = '/processo_seletivo/classificados/{}/?page={}#{}'.format(pk, page, candidato_vaga.pk)
        if polo:
            url = '/processo_seletivo/classificados/{}/{}/?page={}#{}'.format(pk, polo, page, candidato_vaga.pk)

        return httprr(url, 'Simulação de matrícula realizada com sucesso.')
    if 'desfazer' in request.GET and (is_debug or pode_realizar_acao):
        candidato_vaga = CandidatoVaga.objects.get(pk=request.GET['desfazer'])
        if request.user.is_superuser or is_debug or is_administrador:
            candidato_vaga.desfazer_procedimento()
        elif candidato_vaga.situacao in (CandidatoVaga.AUSENTE, CandidatoVaga.INAPTO):
            candidato_vaga.desfazer_procedimento()
        url = '/processo_seletivo/classificados/{}/?page={}#{}'.format(pk, page, candidato_vaga.pk)
        if polo:
            url = '/processo_seletivo/classificados/{}/{}/?page={}#{}'.format(pk, polo, page, candidato_vaga.pk)

        return httprr(url, 'Procedimento desfeito com sucesso.')

    xls_candidatos = request.GET.get('xls_candidatos')
    if xls_candidatos:
        rows = [['Classificação', 'Turno', 'CPF', 'Nome', 'Telefone', 'E-mail', 'Nº Inscrição', 'Matriculado', 'Situação', 'Lista', 'Aprovado', 'Eliminado', 'Convocação']]
        count = 0
        for candidato_vaga in candidatos_vagas:
            row = [
                format_(candidato_vaga.classificacao),
                format_(candidato_vaga.candidato.turno),
                format_(candidato_vaga.candidato.cpf),
                normalizar_nome_proprio(format_(candidato_vaga.candidato.nome)),
                format_(candidato_vaga.candidato.telefone),
                format_(candidato_vaga.candidato.email),
                format_(candidato_vaga.candidato.inscricao),
                format_(candidato_vaga.is_matriculado() and 'Sim' or 'Não'),
                format_(candidato_vaga.get_situacao_display()),
                format_(candidato_vaga.candidato.get_lista_candidato()),
                format_(candidato_vaga.aprovado and 'Sim' or 'Não'),
                format_(candidato_vaga.eliminado and 'Sim' or 'Não'),
                format_(candidato_vaga.convocacao or ''),
            ]
            rows.append(row)
        return XlsResponse(rows)

    title = 'Candidatos Classificados na Lista'
    ultima_chamada = oferta_vaga.oferta_vaga_curso.get_numero_ultima_chamada()

    grupos_candidatos_vaga = [('Aprovados', candidatos_vagas.filter(aprovado=True)), ('Habilitados', candidatos_vagas.filter(aprovado=False))]

    return locals()


@rtr()
@permission_required('processo_seletivo.view_edital')
def candidato(request, pk):
    obj = get_object_or_404(Candidato, pk=pk)
    title = str(obj)
    return locals()


@login_required()
@rtr()
@permission_required('processo_seletivo.pode_matricular_proitec')
def matricular_alunos_proitec(request, pk, ano, periodo):
    edital = get_object_or_404(Edital, pk=pk)
    title = 'Matricular Alunos Proitec - %s' % edital.descricao

    form = MatricularAlunoProitecForm(edital=edital, data=request.POST or None, initial=dict(ano=ano, periodo=periodo))

    if form.is_valid():
        return form.processar(request)

    return locals()


@rtr()
@permission_required('processo_seletivo.change_lista')
def definir_forma_ingresso(request, pk):
    lista = get_object_or_404(Lista, pk=pk)
    title = 'Forma de Ingresso'
    form = ListaForm(data=request.POST or None, request=request, instance=lista)
    if form.is_valid():
        obj = form.save()
        return httprr('..', 'Forma de ingresso definida com sucesso.')
    return locals()


@rtr()
@login_required()
def inscricao_em_edital(request, edital_id):
    edital = get_object_or_404(EditalAdesaoCampus, pk=edital_id)
    pode_efetuar_inscricao, msg = InscricaoFiscal.pode_efetuar_inscricao(request.user, edital)
    if not pode_efetuar_inscricao:
        return httprr('/', message="A sua incrição foi indeferida, pois {}".format(msg), tag='error')
    title = 'Formulário de Inscrição para o edital {}'.format(edital)
    form = InscricaoFiscalForm(request.POST or None, user=request.user, edital=edital)
    pessoa_fisica = request.user.get_profile()
    if form.is_valid():
        form.save()
        return httprr('/', msg)
    return locals()


@permission_required('processo_seletivo.change_inscricaofiscal')
def inscricao_em_edital_xls(request):
    #
    rows = [
        [
            ' Edital',
            'Tipo',
            'Nome',
            'Mátricula',
            'CPF',
            'Nascimento',
            'Banco',
            'Tipo de conta',
            'Agência',
            'Conta',
            'Operação',
            'PIS/PASEP',
            'Telefones',
            'Participou de outros processos?',
            'Início na instituição',
            'Período/ano atual',
            'Renda per Capita',
            'Ensino Fundamental',
            'Ensino Médio',
            'Participação em programas socias',
            'Participação na assistência estudantil',
            'Curso',
            'IRA',
            'Idade no dia da prova',
        ]
    ]
    queryset = InscricaoFiscal.objects.all()
    filters = dict()
    for key, value in list(request.GET.items()):
        if key not in ('ot', 'o'):
            filters[str(key)] = str(value)
    if len(filters):
        queryset = queryset.filter(**filters)

    for inscricao in queryset.select_related('pessoa_fisica'):
        inicio_na_instituicao, ira, renda_per_capita = '-', '-', '-'
        periodo_atual, escola_ensino_fundamental, escola_ensino_medio = '-', '-', '-'
        eh_participante = False
        eh_beneficiario = False
        curso = "-"
        if hasattr(inscricao.pessoa_fisica, 'funcionario'):
            inicio_na_instituicao = inscricao.pessoa_fisica.funcionario.servidor.data_inicio_exercicio_na_instituicao.strftime("%d/%m/%Y")
        if inscricao.pessoa_fisica.aluno_edu_set.exists():
            aluno = inscricao.pessoa_fisica.aluno_edu_set.latest('id')
            curso = aluno.curso_campus
            ira = aluno.get_ira()
            if hasattr(aluno, 'caracterizacao'):
                renda_per_capita = aluno.caracterizacao.renda_per_capita
                eh_beneficiario = aluno.caracterizacao.beneficiario_programa_social.all().exists()
                eh_participante = aluno.eh_participante_programa_social()
                periodo_atual = aluno.periodo_atual
                escola_ensino_fundamental = "%s" % (aluno.caracterizacao.escola_ensino_fundamental or '-')
                escola_ensino_medio = "%s" % (aluno.caracterizacao.escola_ensino_medio or '-')
        #
        rows.append(
            [
                inscricao.edital,
                inscricao.tipo,
                inscricao.pessoa_fisica.nome,
                inscricao.matricula,
                inscricao.pessoa_fisica.cpf,
                inscricao.pessoa_fisica.nascimento_data.strftime("%d/%m/%Y"),
                inscricao.banco,
                inscricao.tipo_conta,
                inscricao.numero_agencia,
                inscricao.numero_conta,
                inscricao.operacao,
                inscricao.pessoa_fisica.pis_pasep,
                inscricao.telefones,
                inscricao.outros_processos,
                # Apenas para servidores
                inicio_na_instituicao,
                # Apenas para alunos
                periodo_atual,
                renda_per_capita,
                escola_ensino_fundamental,
                escola_ensino_medio,
                eh_beneficiario,
                eh_participante,
                curso,
                ira,
                inscricao.idade_no_dia_prova(),
            ]
        )
    return XlsResponse(rows)


@rtr()
@permission_required('processo_seletivo.view_edital')
def configuracaomigracaovaga(request, pk):
    conf = get_object_or_404(ConfiguracaoMigracaoVaga, pk=pk)
    title = str(conf)
    if 'replicar' in request.GET:
        precedencias = conf.precedenciamigracao_set.all()
        configuracao = conf
        configuracao.descricao = ''
        configuracao.pk = None
        configuracao.save()
        for precedencia in precedencias:
            precedencia.configuracao = configuracao
            precedencia.pk = None
            precedencia.save()

        return httprr('/admin/processo_seletivo/configuracaomigracaovaga/{}/'.format(configuracao.pk), 'Replicação realizada com sucesso')
    precedencias = conf.get_precedencias()
    return locals()


@rtr()
@permission_required('processo_seletivo.add_configuracaomigracaovaga')
def definir_configuracao_migracao_vaga(request, pk):
    title = 'Definir Configuração de Migração de Vagas'
    obj = get_object_or_404(Edital, pk=pk)
    form = DefinirConfiguracaoMigracaoVagaForm(data=request.POST or None, request=request, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Configuração de migração de vagas definida com sucesso.')
    return locals()


@rtr()
@permission_required('processo_seletivo.add_configuracaomigracaovaga')
def definir_precedencia_matricula(request, pk):
    title = 'Definir Precedência de Matrícula'
    obj = get_object_or_404(ConfiguracaoMigracaoVaga, pk=pk)
    form = DefinirPrecedenciaMatriculaForm(data=request.POST or None, request=request, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Precedência de matrícula definida com sucesso.')
    return locals()


@rtr()
@permission_required('processo_seletivo.add_configuracaomigracaovaga')
def definir_precedencia(request, pk):
    title = 'Definir Precedência de Migração de Vagas'
    obj = get_object_or_404(ConfiguracaoMigracaoVaga, pk=pk)
    form = PrecedenciaMigracaoForm(data=request.POST or None, request=request, configuracao=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Precedência de migração de vaga definida com sucesso.')
    return locals()


@rtr()
@permission_required('processo_seletivo.add_configuracaomigracaovaga')
def editar_precedencia(request, pk, lista_origem):
    obj = get_object_or_404(ConfiguracaoMigracaoVaga, pk=pk)
    form = PrecedenciaMigracaoForm(data=request.POST or None, request=request, configuracao=obj, lista_origem=lista_origem)
    if form.is_valid():
        form.save()
        return httprr('..', 'Precedência de migração de vaga editada com sucesso.')
    return locals()


@rtr()
@permission_required('processo_seletivo.add_configuracaomigracaovaga')
def remover_precedencia(request, pk, lista_origem):
    PrecedenciaMigracao.objects.filter(configuracao__pk=pk, origem__nome=lista_origem).delete()
    return httprr('/processo_seletivo/configuracaomigracaovaga/{}/'.format(pk), 'Precedência de migração de vaga removida com sucesso.')


@rtr()
@permission_required('processo_seletivo.view_edital')
def realizar_acao_lote(request, pk):
    oferta_vaga = get_object_or_404(OfertaVaga, pk=pk)
    title = 'Realizar Ação em Lote'
    form = RealizarAcaoLote(data=request.POST or None, request=request, oferta_vaga=oferta_vaga)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Ação realizada com sucesso.')
    return locals()


@rtr()
@permission_required('processo_seletivo.change_candidatovaga')
def vincular_vaga(request, pk):
    candidato_vaga = get_object_or_404(CandidatoVaga, pk=pk)
    candidato_vaga.vincular_vaga()
    return httprr('..', 'Ação realizada com sucesso.')


@rtr()
@permission_required('processo_seletivo.change_candidatovaga')
def vincular_matricula(request, pk):
    candidato_vaga = get_object_or_404(CandidatoVaga, pk=pk)
    title = 'Vincular Candidato à Matrícula de Aluno'
    form = VincularMatriculaForm(candidato_vaga=candidato_vaga, data=request.POST or None)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Vinculação realizada com sucesso.')
    return locals()


@rtr()
@permission_required('processo_seletivo.change_ofertavagacurso')
def editar_oferta_vaga_curso(request, pk):
    title = 'Editar Oferta Vaga'
    obj = get_object_or_404(OfertaVagaCurso, pk=pk)
    form = EditarOfertaVagaCursoForm(request=request, instance=obj, data=request.POST or None)
    if form.is_valid():
        form.save()
        return httprr('..', 'Oferta vaga atualizada com sucesso')
    return locals()


@rtr()
@permission_required('processo_seletivo.view_edital')
def criar_vaga_remanescente(request, pk):
    title = 'Criar Vaga Remanescente'
    obj = get_object_or_404(OfertaVaga, pk=pk)
    form = CriacaoVagaRemanescenteForm(request=request, data=request.POST or None)
    if form.is_valid():
        form.instance.oferta_vaga = obj
        form.save()
        return httprr('..', 'Vaga criada com sucesso')
    return locals()
