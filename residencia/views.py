import datetime
import xlwt
from django.apps import apps
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.db.models.aggregates import Sum
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.utils import dateformat
from django.template.defaultfilters import pluralize

from comum.forms import BolsistaForm, BolsistaChangeForm
from comum.models import Bolsista, Ano, Configuracao
from djtools import layout, models
from djtools.html.graficos import PieChart
from djtools.templatetags.filters import format_, getattrr, in_group
from djtools.testutils import running_tests
from djtools.utils import (
    FitSheetWrapper,
    JsonResponse,
    XlsResponse,
    documento,
    get_client_ip,
    get_session_cache,
    group_required,
    httprr,
    normalizar_nome_proprio,
    permission_required,
    rtr,
    send_mail,
    int_to_roman,
)
from residencia import perms, utils
from residencia.models import (
    ObservacaoDiario, Diario, MatriculaDiario, Residente, SolicitacaoResidente, SequencialMatriculaResidente,
    Observacao, Matriz, ComponenteCurricular, EstruturaCurso, CursoResidencia, Log, Turma, MatriculaPeriodo,
    SituacaoMatriculaPeriodo, PreceptorDiario, FrequenciaResidente, MatrizCurso, AtaEletronicaResidencia,
    AssinaturaAtaEletronicaResidencia, NotaAvaliacao,
    ProjetoFinalResidencia, SituacaoMatricula, SolicitacaoEletivo, EstagioEletivo, UnidadeAprendizagemTurma,
    NotaAvaliacaoUnidadeAprendizagem, CalendarioAcademico
)
from residencia.forms import (
    EfetuarMatriculaForm,
    SolicitarMatriculaResidenteForm,
    AnalisarSolicitacaoResidenteForm,
    ObservacaoForm,
    AtualizarEmailResidenteForm,
    AtualizarDadosPessoaisForm,
    AtualizarFotoForm, SecretarioResidenciaForm, CoordenadorResidenciaForm, ComponenteCurricularForm,
    ReplicacaoMatrizForm, DefinirCoordenadorCursoForm, MatrizCursoForm, GerarTurmasForm, PreceptorResidenciaForm,
    PreceptorDiarioForm, AdicionarResidentesDiarioForm, ObservacaoDiarioForm,
    ParticipacaoProjetoFinalResidenciaForm, LancarResultadoProjetoFinalResidenciaForm, ProjetoFinalResidenciaForm,
    UploadDocumentoProjetoFinalResidenciaForm,
    FrequenciaResidenteForm, DocumentoFrequenciaMensalResidenteForm, SolicitacaoDesligamentosForm,
    RejeitarSolicitacaoUsuarioForm, SolicitacaoDiplomasForm, SolicitacaoFeriasForm, SolicitacaoLicencasForm,
    SolicitacaoCongressosForm,
    FrequenciaResidenteForm, AnalisarSolicitacaoEletivoForm, SolicitarEletivoForm, EstagioEletivoAnexoForm,
    DocumentoFrequenciaMensalResidenteForm, RelatorioCorpoPedagogicoForm, EstatisticaForm, EstatisticaEletivoForm,
    MatricularAlunoAvulsoUnidadeAprendizagemTurmaForm
)
from residencia.models.solicitacoes import SolicitacaoUsuario, SolicitacaoLicencas
from rh.models import Servidor, PessoaFisica
from suap import settings
from edu.forms import IniciarSessaoAssinaturaSenhaForm


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()

    servicos_anonimos.append(dict(
        categoria='Solicitações',
        url="/residencia/solicitar_matricula_residente/",
        icone="passport",
        titulo='Solicitar Matrícula de Residente'
    ))

    return servicos_anonimos


@layout.quadro('Faça sua matrícula online', icone='users')
def index_quadros_banners_residentes(quadro, request):
    def do():

        if request.user.eh_residente:
            residente = request.user.get_relacionamento()

            # matrícula online
            # if residente.pode_matricula_online():
            #     quadro.add_item(layout.ItemImagem(titulo='Faça sua matrícula online.', path='/static/edu/img/index-banner-aluno.png', url='#'))
        return quadro

    return get_session_cache(request, 'index_quadros_banners_residentes', do, 24 * 3600)


@layout.info()
def index_infos(request):
    infos = list()

    if request.user.eh_residente:
        residente = request.user.get_relacionamento()
        if not residente.pessoa_fisica.nome_usual:
            infos.append(
                dict(url=f"/residencia/atualizar_meus_dados_pessoais/{residente.matricula}", titulo='Você ainda não possui um nome usual no sistema. Edite o seus dados pessoais.')
            )

    return infos


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    if request.user.eh_residente:
        residente = request.user.get_relacionamento()

        # matrícula online
        # if residente.pode_matricula_online():
        #     inscricoes.append(dict(url='#', titulo='Faça sua matrícula online.',))

    return inscricoes


@layout.alerta()
def index_alertas(request):
    alertas = list()

    if request.user.eh_residente:
        residente = request.user.get_relacionamento()
        if not residente.logradouro:
            alertas.append(dict(url=f'/residencia/atualizar_meus_dados_pessoais/{residente.matricula}/', titulo='Atualize seus dados pessoais.'))

    return alertas


@layout.quadro('Ensino', icone='pencil-alt')
def index_quadros(quadro, request):
    # PARA ALUNOS

    return quadro


@rtr()
def solicitar_matricula_residente(request):
    title = 'Solicitação de Matrícula de Residente'
    # alerta = None
    alerta = 'Por favor preste atenção no preenchimento dos campos obrigatórios, com marcação "*"'
    initial = None
    cpf = request.POST.get('cpf')
    if cpf:
        residentes = SolicitacaoResidente.objects.filter(cpf=cpf, situacao=SolicitacaoResidente.STATUS_EM_ANALISE)
        if residentes.exists():
            return httprr(
                f'/residencia/solicitar_matricula_residente/',
                'Já existe Solicitação de Matŕicula de Residente registrada e aguardando análise. Mensagens sobre o andamento da solicitação serão enviadas para o email informado.',
                'error'
            )

    form = SolicitarMatriculaResidenteForm(request, data=request.POST or None, initial=initial, files=request.FILES or None)
    if form.is_valid():
        obj = form.processar()
        return httprr('/residencia/solicitar_matricula_residente/', 'Solicitação de Matrícula de Residente cadastrada com sucesso. Mensagens sobre o andamento da solicitação serão enviadas para o email informado.')

    return locals()


@rtr()
@login_required()
def residente(request, matricula):
    residente = get_object_or_404(
        Residente,
        matricula=matricula,
    )
    title = f'{normalizar_nome_proprio(residente.get_nome())} ({str(residente.matricula)})'
    is_proprio_residente = perms.is_proprio_residente(request, residente)
    is_admin = perms.is_admin(request.user)

    is_responsavel = False
    if request.user.is_anonymous:
        is_responsavel = perms.is_responsavel(request, residente)
        if not is_responsavel:
            return httprr('/', 'Você não tem permissão para acessar está página.', 'error')

    pode_alterar_email_residente = perms.pode_alterar_email_residente(request, residente)
    tem_permissao_realizar_procedimentos = perms.tem_permissao_realizar_procedimentos(request.user, residente)
    pode_ver_dados_residente = perms.pode_ver_dados_residente(request)
    tem_permissao_para_emitir_docs_matricula = (request.user.has_perm('residencia.efetuar_matricula') or in_group(request.user, "Residente"))
    pode_ver_dados_sociais = perms.pode_ver_dados_sociais(request, residente)
    pode_ver_dados_bancarios = perms.pode_ver_dados_bancarios(request)
    pode_realizar_procedimentos = True
    pode_ver_dados_academicos = (
            is_admin
            or is_responsavel
            or is_proprio_residente
            and request.user.has_perm('residencia.view_dados_academicos')
    )
    pode_ver_cpf = (
            is_admin
            or pode_ver_dados_sociais
            or pode_ver_dados_academicos
    )

    # PROJETO FINAL
    projetos = residente.get_projetos_finais()



    return locals()


@rtr()
@login_required()
def atualizar_email(request, residente_pk):
    title = 'Atualização do E-mail'
    residente = Residente.objects.filter(pk=residente_pk).first()
    if not perms.pode_alterar_email_residente(request, residente):
        raise PermissionDenied()
    form = AtualizarEmailResidenteForm(request.POST or None, request=request, residente=residente)
    if form.is_valid():
        form.save()
        return httprr('..', 'E-mail atualizado com sucesso.')
    return locals()


@rtr()
@group_required('Secretário(a) Residência')
def atualizar_dados_pessoais(request, residente_pk):
    title = 'Atualização de Dados Pessoais'
    residente = Residente.objects.filter(pk=residente_pk).first()
    pode_realizar_procedimentos = perms.tem_permissao_realizar_procedimentos(request.user, residente)
    if not pode_realizar_procedimentos:
        raise PermissionDenied()
    initial = dict(
        nome_usual=residente.pessoa_fisica.nome_usual,
        email_secundario=residente.pessoa_fisica.email_secundario,
        logradouro=residente.logradouro,
        numero=residente.numero,
        complemento=residente.complemento,
        bairro=residente.bairro,
        cep=residente.cep,
        cidade=residente.cidade,
        lattes=residente.pessoa_fisica.lattes,
        telefone_principal=residente.telefone_principal,
        telefone_secundario=residente.telefone_secundario,
        telefone_adicional_1=residente.telefone_adicional_1,
        telefone_adicional_2=residente.telefone_adicional_2,
    )

    form = AtualizarDadosPessoaisForm(data=request.POST or None, initial=initial, instance=residente, pode_realizar_procedimentos=pode_realizar_procedimentos)
    if form.is_valid():
        form.save(residente)
        return httprr('..', 'Dados Pessoais atualizados com sucesso.')
    return locals()


@login_required()
@rtr()
def atualizar_meus_dados_pessoais(request, matricula, renovacao_matricula=None):
    title = 'Atualização de Dados Pessoais'
    residente = get_object_or_404(Residente, matricula=matricula)

    if request.user != residente.pessoa_fisica.user:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    initial = dict(
        nome_usual=residente.pessoa_fisica.nome_usual,
        email_secundario=residente.pessoa_fisica.email_secundario,
        logradouro=residente.logradouro,
        numero=residente.numero,
        complemento=residente.complemento,
        bairro=residente.bairro,
        cep=residente.cep,
        cidade=residente.cidade,
        lattes=residente.pessoa_fisica.lattes,
        telefone_principal=residente.telefone_principal,
        telefone_secundario=residente.telefone_secundario,
        utiliza_transporte_escolar_publico=residente.poder_publico_responsavel_transporte is not None and (residente.poder_publico_responsavel_transporte and 'Sim' or 'Não') or None,
        poder_publico_responsavel_transporte=residente.poder_publico_responsavel_transporte,
        tipo_veiculo=residente.tipo_veiculo,
    )
    form = AtualizarDadosPessoaisForm(data=request.POST or None, initial=initial, instance=residente, pode_realizar_procedimentos=False, request=request)
    if form.is_valid():
        form.save(residente)
        return httprr('..', 'Dados Pessoais atualizados com sucesso.')
    return locals()


@permission_required('residencia.change_foto')
@rtr()
def atualizar_foto(request, residente_pk):
    title = 'Atualização de Foto'
    residente = get_object_or_404(Residente, pk=residente_pk)
    if request.method == 'POST':
        form = AtualizarFotoForm(data=request.POST or None, files=request.FILES)
    else:
        form = AtualizarFotoForm()
    form.initial.update(residente=residente_pk)
    if form.is_valid():
        return httprr(residente.get_absolute_url(), form.processar(request))
    return locals()


@permission_required('residencia.add_residente')
@rtr()
def analisar_solicitresidente(request, solicitresidente_pk):
    title = 'Analisar Solicitação de Matrícula de Residente'
    obj = get_object_or_404(SolicitacaoResidente, pk=solicitresidente_pk)

    residentes = Residente.objects.none()
    residente = None
    if obj.cpf:
        residentes = Residente.objects.filter(pessoa_fisica__cpf=obj.cpf)
        if residentes.exists():
            residente = residentes.latest('id')

    form = AnalisarSolicitacaoResidenteForm(request.POST or None, instance=obj)
    if form.is_valid():
        obj2 = form.save(False)
        if not residente:
            obj2.parecer_autor_vinculo = request.user.get_vinculo()
            obj2.parecer_data = datetime.datetime.now()

        obj2.save()

        if not residente:
            pessoa_fisica = PessoaFisica()
            pessoa_fisica.cpf = obj2.cpf
            pessoa_fisica.nome_registro = obj2.nome_registro
            pessoa_fisica.nome_social = obj2.nome_social
            pessoa_fisica.sexo = obj2.sexo
            pessoa_fisica.nascimento_data = obj2.nascimento_data
            pessoa_fisica.raca = obj2.raca
            pessoa_fisica.save()

            residente = Residente()
            residente.periodo_atual = 1
            residente.pessoa_fisica = pessoa_fisica

            # dados da matrícula
            residente.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
            residente.ano_letivo = form.cleaned_data['ano_letivo']
            residente.periodo_letivo = form.cleaned_data['periodo_letivo']
            residente.curso_campus = form.cleaned_data['matriz_curso'].curso_campus
            residente.matriz = form.cleaned_data['matriz_curso'].matriz

            residente.estado_civil = obj2.estado_civil
            # dados familiares
            residente.nome_pai = obj2.nome_pai
            residente.estado_civil_pai = obj2.estado_civil_pai
            residente.pai_falecido = obj2.pai_falecido
            residente.nome_mae = obj2.nome_mae
            residente.estado_civil_mae = obj2.estado_civil_mae
            residente.mae_falecida = obj2.mae_falecida
            residente.responsavel = obj2.responsavel
            residente.cpf_responsavel = obj2.cpf_responsavel
            residente.parentesco_responsavel = obj2.parentesco_responsavel
            # endereco
            residente.logradouro = obj2.logradouro
            residente.numero = obj2.numero
            residente.complemento = obj2.complemento
            residente.bairro = obj2.bairro
            residente.cep = obj2.cep
            # residente.cidade = obj2.nomecidade
            residente.tipo_zona_residencial = obj2.tipo_zona_residencial
            # contato
            residente.telefone_principal = obj2.telefone_principal
            residente.telefone_secundario = obj2.telefone_secundario
            residente.telefone_adicional_1 = obj2.telefone_adicional_1
            residente.telefone_adicional_2 = obj2.telefone_adicional_2

            # transporte escolar
            if obj2.poder_publico_responsavel_transporte:
                residente.poder_publico_responsavel_transporte = obj2.poder_publico_responsavel_transporte
                residente.tipo_veiculo = obj2.tipo_veiculo
            else:
                residente.poder_publico_responsavel_transporte = None
                residente.tipo_veiculo = None

            # outras informacoes
            residente.tipo_sanguineo = obj2.tipo_sanguineo
            residente.nacionalidade = obj2.nacionalidade
            residente.passaporte = obj2.passaporte
            # residente.naturalidade = obj2.nomenaturalidade

            if obj2.tipo_necessidade_especial:
                residente.tipo_necessidade_especial = obj2.tipo_necessidade_especial
                residente.tipo_transtorno = obj2.tipo_transtorno
                residente.superdotacao = obj2.superdotacao
                residente.outras_necessidades = obj2.outras_necessidades
            else:
                residente.tipo_necessidade_especial = None
                residente.tipo_transtorno = None
                residente.superdotacao = None
                residente.outras_necessidades = None

            # dados escolares
            residente.nivel_ensino_anterior = obj2.nivel_ensino_anterior
            residente.tipo_instituicao_origem = obj2.tipo_instituicao_origem
            residente.nome_instituicao_anterior = obj2.nome_instituicao_anterior
            residente.ano_conclusao_estudo_anterior = obj2.ano_conclusao_estudo_anterior
            residente.categoria = obj2.categoria
            # conselho classe
            residente.numero_registro = obj2.numero_registro
            residente.conselho = obj2.conselho
            # rg
            residente.numero_rg = obj2.numero_rg
            residente.uf_emissao_rg = obj2.uf_emissao_rg
            residente.orgao_emissao_rg = obj2.orgao_emissao_rg
            residente.data_emissao_rg = obj2.data_emissao_rg
            # titulo_eleitor
            residente.numero_titulo_eleitor = obj2.numero_titulo_eleitor
            residente.zona_titulo_eleitor = obj2.zona_titulo_eleitor
            residente.secao = obj2.secao
            residente.data_emissao_titulo_eleitor = obj2.data_emissao_titulo_eleitor
            residente.uf_emissao_titulo_eleitor = obj2.uf_emissao_titulo_eleitor
            # carteira de reservista
            residente.numero_carteira_reservista = obj2.numero_carteira_reservista
            residente.regiao_carteira_reservista = obj2.regiao_carteira_reservista
            residente.serie_carteira_reservista = obj2.serie_carteira_reservista
            residente.estado_emissao_carteira_reservista = obj2.estado_emissao_carteira_reservista
            residente.ano_carteira_reservista = obj2.ano_carteira_reservista
            # certidao_civil
            residente.tipo_certidao = obj2.tipo_certidao
            residente.cartorio = obj2.cartorio
            residente.numero_certidao = obj2.numero_certidao
            residente.folha_certidao = obj2.folha_certidao
            residente.livro_certidao = obj2.livro_certidao
            residente.data_emissao_certidao = obj2.data_emissao_certidao
            residente.matricula_certidao = obj2.matricula_certidao

            hoje = datetime.date.today()
            ano = hoje.year
            prefixo = f'{ano}RES'
            residente.matricula = SequencialMatriculaResidente.proximo_numero(prefixo)
            residente.save()

            residente.pessoa_fisica.username = obj2.cpf.replace('.', '').replace('-', '')
            residente.pessoa_fisica.email_secundario = obj2.email
            residente.pessoa_fisica.save()



            if obj2.foto:
                residente.foto = obj2.foto

            residente.save()

            matricula_periodo = MatriculaPeriodo()
            matricula_periodo.residente = residente
            matricula_periodo.ano_letivo = form.cleaned_data['ano_letivo']
            matricula_periodo.periodo_letivo =form.cleaned_data['periodo_letivo']
            matricula_periodo.periodo_matriz = 1
            matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
            matricula_periodo.save()

        return httprr('..', 'Solicitação analisada com sucesso.')
    return locals()


@rtr()
@login_required()
def efetuarmatricula(request):
    title = 'Adicionar Novo(a) Residente'
    initial = None
    residentes = Residente.objects.none()

    cpf = request.POST.get('cpf')

    if not request.user.has_perm('residencia.efetuar_matricula'):
        return HttpResponseForbidden()

    if cpf:
        residentes = Residente.objects.filter(pessoa_fisica__cpf=cpf)
        if residentes.exists():
            residente = residentes.latest('id')
            initial = dict(
                # dados pessoais
                nome=residente.pessoa_fisica.nome_registro,
                nome_social=residente.pessoa_fisica.nome_social,
                sexo=residente.pessoa_fisica.sexo,
                data_nascimento=residente.pessoa_fisica.nascimento_data,
                estado_civil=residente.pessoa_fisica.estado_civil,
                # dados familiares
                nome_pai=residente.nome_pai,
                estado_civil_pai=residente.estado_civil_pai,
                # pai_falecido = residente.pai_falecido,
                nome_mae=residente.nome_mae,
                estado_civil_mae=residente.estado_civil_mae,
                # mae_falecida = residente.mae_falecida,
                responsavel=residente.responsavel,
                parentesco_responsavel=residente.parentesco_responsavel,
                cpf_responsavel=residente.cpf_responsavel,
                # endereço
                logradouro=residente.logradouro,
                numero=residente.numero,
                complemento=residente.complemento,
                bairro=residente.bairro,
                cep=residente.cep,
                cidade=residente.cidade,
                tipo_zona_residencial=residente.tipo_zona_residencial,
                # informações para contado
                telefone_principal=residente.telefone_principal,
                telefone_secundario=residente.telefone_secundario,
                telefone_adicional_1=residente.telefone_adicional_1,
                telefone_adicional_2=residente.telefone_adicional_2,
                email_pessoal=residente.pessoa_fisica.email_secundario,
                # outras informacoes
                tipo_sanguineo=residente.tipo_sanguineo,
                nacionalidade=residente.nacionalidade,
                pais_origem=residente.pais_origem and residente.pais_origem.id or None,
                naturalidade=residente.naturalidade and residente.naturalidade.id or None,
                raca=residente.pessoa_fisica.raca,
                # dados escolares
                nivel_ensino_anterior=residente.nivel_ensino_anterior and residente.nivel_ensino_anterior.id or None,
                tipo_instituicao_origem=residente.tipo_instituicao_origem,
                nome_instituicao_anterior=residente.nome_instituicao_anterior,
                ano_conclusao_estudo_anterior=residente.ano_conclusao_estudo_anterior and residente.ano_conclusao_estudo_anterior.id or None,
                # rg
                numero_rg=residente.numero_rg,
                uf_emissao_rg=residente.uf_emissao_rg and residente.uf_emissao_rg.id or None,
                orgao_emissao_rg=residente.orgao_emissao_rg and residente.orgao_emissao_rg.id or None,
                data_emissao_rg=residente.data_emissao_rg,
                # titulo_eleitor
                numero_titulo_eleitor=residente.numero_titulo_eleitor,
                zona_titulo_eleitor=residente.zona_titulo_eleitor,
                secao=residente.secao,
                data_emissao_titulo_eleitor=residente.data_emissao_titulo_eleitor,
                uf_emissao_titulo_eleitor=residente.uf_emissao_titulo_eleitor and residente.uf_emissao_titulo_eleitor.id or None,
                # carteira de reservista
                numero_carteira_reservista=residente.numero_carteira_reservista,
                regiao_carteira_reservista=residente.regiao_carteira_reservista,
                serie_carteira_reservista=residente.serie_carteira_reservista,
                estado_emissao_carteira_reservista=residente.estado_emissao_carteira_reservista and residente.estado_emissao_carteira_reservista.id or None,
                ano_carteira_reservista=residente.ano_carteira_reservista,
                # certidao_civil
                tipo_certidao=residente.tipo_certidao,
                cartorio=residente.cartorio,
                numero_certidao=residente.numero_certidao,
                folha_certidao=residente.folha_certidao,
                livro_certidao=residente.livro_certidao,
                data_emissao_certidao=residente.data_emissao_certidao,
                matricula_certidao=residente.matricula_certidao,
            )

    form = EfetuarMatriculaForm(request, data=request.POST or None, initial=initial, files=request.FILES or None)
    if form.is_valid():
        residente = form.processar()

        return httprr(
            '/residencia/efetuarmatricula/',
            mark_safe('Residente adicionado(a) com sucesso.'),
        )
    return locals()


@permission_required('residencia.add_observacao')
@rtr()
def adicionar_observacao(request, residente_pk):
    title = ' Adicionar Observação'
    residente = Residente.objects.filter(pk=residente_pk).first()
    if residente:
        form = ObservacaoForm(residente, request.user, request.POST or None, instance=None)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação adicionada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar os dados deste residente.', 'error')
    return locals()


@permission_required('residencia.change_observacao')
@rtr()
def editar_observacao(request, observacao_pk=None):
    title = ' Editar Observação'
    observacao = Observacao.objects.get(pk=observacao_pk)
    if request.user == observacao.usuario:
        form = ObservacaoForm(observacao.residente, request.user, request.POST or None, instance=observacao)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação atualizada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar a observação de outro usuário.', 'error')
    return locals()


@login_required()
@rtr()
def meus_dados_academicos(request):

    obj = get_object_or_404(Residente, pessoa_fisica__user__username=request.user.username)
    return HttpResponseRedirect(obj.get_absolute_url())


# Secretário(a) Residência
@rtr()
@group_required("RH,Coordenadores(as) Residência")
def secretarios_residencia(request):
    title = 'Secretário(a) Residência'

    if 'del_prefil' in request.GET:
        secretario_residencia = Group.objects.get(name='Secretário(a) Residência')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])
        if secretario_residencia:
            empregado.get_vinculo().user.groups.remove(secretario_residencia)
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Secretário(a) Residência removido(a) com sucesso.')

    secretarios_residencias = Servidor.objects.filter(user__groups__name='Secretário(a) Residência')

    return locals()


@rtr()
@group_required("RH,Coordenadores(as) Residência")
def cadastrar_secretario_residencia(request):
    title = 'Cadastrar Secretário(a) Residência'
    form = SecretarioResidenciaForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        grupo = Group.objects.get(name='Secretário(a) Residência')
        if registro and grupo:
            grupo.user_set.add(registro.user)
        return httprr(
            '..',
            'Secretário(a) Residência cadastrado(a) com sucesso'
        )

    return locals()


@rtr()
@group_required("RH,Coordenadores(as) Residência")
def editar_secretario_residencia(request, empregado_id):
    title = 'Editar Secretário(a) Residência'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = SecretarioResidenciaForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Secretário(a) Residência alterado(a) com sucesso'
        )

    return locals()


# Preceptor(a)
@rtr()
@group_required("Secretário(a) Residência, Coordenadores(as) Residência")
def preceptores(request):
    title = 'Preceptores(as)'

    if 'del_prefil' in request.GET:
        preceptor = Group.objects.get(name='Preceptor(a)')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])
        if preceptor:
            empregado.get_vinculo().user.groups.remove(preceptor)
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Preceptor(a) removido(a) com sucesso.')

    preceptores = Servidor.objects.filter(user__groups__name='Preceptor(a)')

    return locals()


@rtr()
@group_required("Secretário(a) Residência, Coordenadores(as) Residência")
def cadastrar_preceptor(request):
    title = 'Cadastrar Preceptor(a)'
    form = PreceptorResidenciaForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        grupo = Group.objects.get(name='Preceptor(a)')
        if registro and grupo:
            grupo.user_set.add(registro.user)
        return httprr('..', 'Preceptor(a) cadastrado(a) com sucesso.')

    return locals()

@rtr()
@group_required("Secretário(a) Residência, Coordenadores(as) Residência")
def editar_preceptor(request, empregado_id):
    title = 'Editar Preceptor(a)'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = PreceptorResidenciaForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr('..', 'Preceptor(a) atualizado(a) com sucesso.')

    return locals()

#FES-26

@rtr()
@group_required("Secretário(a) Residência,Coordenadores(as) Residência")
def coordenadores_residencia(request):
    title = 'Coordenadores(as) Residência'

    if 'del_prefil' in request.GET:
        coordenador_residencia = Group.objects.get(name='Coordenadores(as) Residência')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])
        if coordenador_residencia:
            empregado.get_vinculo().user.groups.remove(coordenador_residencia)
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Coordenador(a) Residência removido(a) com sucesso.')

    coordenadores_residencia = Servidor.objects.filter(user__groups__name='Coordenadores(as) Residência')

    return locals()

@rtr()
@group_required("Secretário(a) Residência,Coordenadores(as) Residência")
def cadastrar_coordenador_residencia(request):
    title = 'Cadastrar Coordenador(a) Residência'
    form = CoordenadorResidenciaForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        return httprr('..', 'Coordenador(a) Residência cadastrado(a) com sucesso.')

    return locals()


@rtr()
@group_required("Secretário(a) Residência,Coordenadores(as) Residência")
def editar_coordenador_residencia(request, empregado_id):
    title = 'Editar Coordenador(a) Residência'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = CoordenadorResidenciaForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr('..', 'Coordenador(a) Residência atualizado(a) com sucesso.')

    return locals()


#Apoiador pedagógico
@rtr()
@group_required("Secretário(a) Residência,Coordenadores(as) Residência")
def apoiadores_pedagogicos_residencia(request):
    title = 'Apoiador(a) Pedagógico(a) Residência'


    if 'del_prefil' in request.GET:
        apoiador_pedagogico_residencia = Group.objects.get(name='Apoiador(a) Pedagógico Residência')
        bolsista = Bolsista.objects.get(pk=request.GET['del_prefil'])
        if apoiador_pedagogico_residencia:
            bolsista.get_vinculo().user.groups.remove(apoiador_pedagogico_residencia)
            bolsista.pessoa_fisica.user.delete() 
            bolsista.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Apoiador(a) Pedagógico(a) Residência removido com sucesso.')

    apoiadores = Bolsista.objects.filter(user__groups__name='Apoiador(a) Pedagógico Residência')

    return locals()


@rtr()
@group_required("Secretário(a) Residência,Coordenadores(as) Residência")
def cadastrar_apoiador_pedagogico_residencia(request, pessoafisica_id=None):
    title = 'Cadastrar Apoiador(a) Pedagógico(a) Residência'
    """
        Pré cadastro 

        :param pessoafisica_id:
        :param request:
        :return:
        """
    initial = dict()
    if pessoafisica_id:
        pessoafisica = PessoaFisica.objects.filter(pk=pessoafisica_id).first()
        initial['cpf'] = pessoafisica.cpf
        initial['nome'] = pessoafisica.nome
        initial['email'] = pessoafisica.email
        initial['confirma_email'] = pessoafisica.email

    form = BolsistaForm(request.POST or None, request=request, initial=initial)

    if form.is_valid():
        try:
            bolsita = Bolsista()
            bolsita.nome = form.cleaned_data['nome']
            bolsita.cpf = form.cleaned_data['cpf']
            bolsita.email = form.cleaned_data['email']
            bolsita.email_secundario = form.cleaned_data['email']
            bolsita.data_admissao = form.cleaned_data['data_admissao']
            bolsita.data_demissao = form.cleaned_data['data_demissao']
            bolsita.ativo = False
            bolsita.eh_prestador = False
            bolsita.bolsita = True
            bolsita.save()
            bolsita.enviar_email_pre_cadastro()

            apoiador_pedagogico_residencia = Group.objects.get(name='Apoiador(a) Pedagógico Residência')
            if apoiador_pedagogico_residencia:
                apoiador_pedagogico_residencia.user_set.add(bolsita.get_vinculo().user)

            # Ativa o usuário externo criando o papel caso não possua
            bolsita.ativar()

            return httprr('..', f"Bolsista cadastrada com sucesso. Foi enviado um e-mail para "
                                f"{form.cleaned_data['email']} com instruções para acessar o SUAP.")

        except Exception as e:
            if settings.DEBUG:
                raise e
            return httprr('..', message=str(f"Houve um erro ao cadastrar o usuário. Detalhes: {e}"), tag='error')

    return locals()


@rtr()
@group_required("Secretário(a) Residência,Coordenadores(as) Residência")
def editar_apoiador_pedagogico_residencia(request, bolsista_id):
    title = 'Editar Apoiador(a) Pedagógico(a) Residência'
    bolsista = get_object_or_404(Bolsista, pk=bolsista_id)
    form = BolsistaChangeForm(request.POST or None, instance=bolsista)
    if form.is_valid():
        registro = form.save()
        return httprr('..', 'Apoiador(a) Pedagógico(a) Residência atualizado(a) com sucesso.')

    return locals()


@permission_required('residencia.view_matriz')
@rtr()
def matriz(request, pk):
    obj = get_object_or_404(Matriz, pk=pk)
    pode_editar_matriz = request.user.has_perm('residencia.change_matriz')
    componentes_curriculares = obj.componentecurricular_set.select_related('componente').order_by('unidade_aprendizagem__id')
    periodos = list(range(1, obj.qtd_periodos_letivos + 1))
    title = str(obj)

    return locals()

@permission_required('residencia.add_componentecurricular')
@rtr()
def vincular_componente(request, matriz_pk, componente_pk=None):
    title = '{} Atividades de matriz'.format(componente_pk and 'Editar' or 'Vincular')
    matriz = get_object_or_404(Matriz, pk=matriz_pk)

    if not matriz.pode_ser_editada(request.user):
        return httprr(f'/residencia/matriz/{matriz.pk}/?tab=componentes', 'A matriz não pode ser editada.', 'error')

    if componente_pk:
        mc = get_object_or_404(ComponenteCurricular.objects, componente__pk=componente_pk, matriz=matriz)

    form = ComponenteCurricularForm(matriz, data=request.POST or None, instance=componente_pk and mc or None)

    if form.is_valid():
        form.save()
        redirect = '..'
        if 'continuar' in request.POST:
            redirect = '.'
        if not componente_pk:
            return httprr(redirect, 'Componente de matriz adicionado com sucesso.')
        else:
            return httprr(f'/residencia/matriz/{matriz.pk}/?tab=componentes', 'Componente de matriz atualizado com sucesso.')
    return locals()

@permission_required('edu.add_matriz')
@rtr()
def replicar_matriz(request, pk):
    title = 'Replicação de Matriz'
    matriz = get_object_or_404(Matriz, pk=pk)
    form = ReplicacaoMatrizForm(matriz, data=request.POST or None)
    if request.POST and form.is_valid():
        try:
            resultado = form.processar()
            return httprr(f'/residencia/matriz/{resultado.id}/', 'Matriz replicada com sucesso.')
        except ValidationError as e:
            return httprr('..', f'Não foi possível replicar a matriz: {e.messages[0]}', 'error')
    return locals()

@permission_required('residencia.view_matriz')
@documento()
@rtr()
def matriz_pdf(request, pk):
    obj = get_object_or_404(Matriz, pk=pk)
    componentes_curriculares = obj.componentecurricular_set.all()
    periodos = list(range(1, obj.qtd_periodos_letivos + 1))
    title = str(obj)
    # uo = request.user.get_profile().funcionario.setor.uo
    return locals()

@permission_required('residencia.add_matriz')
@rtr()
def adicionar_matriz_curso(request, curso_residencia_pk, matriz_curso_pk=None):
    title = 'Adicionar Matriz'
    curso_residencia = get_object_or_404(CursoResidencia.locals, pk=curso_residencia_pk)
    if matriz_curso_pk:
        matriz_curso = curso_residencia.matrizcurso_set.get(pk=matriz_curso_pk)
    form = MatrizCursoForm(data=request.POST or None, instance=matriz_curso_pk and matriz_curso or None)
    form.initial.update(dict(curso_campus=curso_residencia.pk))
    if form.is_valid():
        form.save()
        return httprr('..', 'Matriz adicionada com sucesso.')
    return locals()

@login_required()
@rtr()
def grade_curricular(request, matriz_pk):
    obj = get_object_or_404(Matriz, pk=matriz_pk)
    title = f'Grade Curricular: {str(obj)}'
    if (
        not request.user.has_perm('residencia.view_matriz')
        and len(Residente.objects.filter(pessoa_fisica=request.user.get_profile(), matriz=obj)) == 0
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    return locals()

@rtr()
@login_required()
@permission_required('residencia.view_estruturacurso')
def visualizar_estrutura_curso(request, estrutura_curso_pk):
    title = 'Estrutura de Curso'
    obj = get_object_or_404(EstruturaCurso, pk=estrutura_curso_pk)
    if 'replicar' in request.GET:
        obj.pk = None
        obj.descricao = f'{obj.descricao} [REPLICADA]'
        obj.save()
        return httprr(f'/admin/residencia/estruturacurso/{obj.pk}/', 'Estrutura replicada com sucesso. Edite a descrição e os demais dados necessários.')
    matrizes_ativas = obj.get_matrizes_ativas()
    matrizes_inativas = obj.get_matrizes_inativas()

    return locals()

@permission_required('residencia.view_cursoresidencia')
@rtr()
def cursoresidencia(request, pk):
    obj = get_object_or_404(CursoResidencia, pk=pk)
    title = str(obj)
    pode_visualizar_estatistica = in_group(request.user, 'Coordenadores(as) Residência,Secretário(a) Residência')
    pode_definir_coordenador_estagio_docente = in_group(request.user, 'Coordenadores(as) Residência,Secretário(a) Residência')
    tab = request.GET.get('tab', '')
    if tab == 'coordenacao':
        logs = (
            Log.objects.filter(modelo='CursoResidencia', ref=pk, registrodiferenca__campo__in=['Coordenador', ])
            .order_by('-pk')
            .values_list('dt', 'registrodiferenca__valor_anterior', 'registrodiferenca__valor_atual', 'registrodiferenca__campo')
        )
    return locals()

@rtr()
@permission_required('residencia.add_cursoresidencia')
def definir_coordenador_residencia(request, pk):
    title = 'Definir Coordenador'
    curso_residencia = get_object_or_404(CursoResidencia, pk=pk)
    form = DefinirCoordenadorCursoForm(request.POST or None, instance=curso_residencia)
    if form.is_valid():
        form.processar(curso_residencia)
        return httprr('..', 'Coordenador definido com sucesso.')
    return locals()


@permission_required('residencia.gerar_turmas')
@rtr()
def gerar_turmas(request):
    title = 'Gerar Turmas'
    form = GerarTurmasForm(request, data=request.GET or None, initial=dict(periodo_letivo=1))
    if form.is_valid():
        form.processar(commit=True)
        ids = []
        for turma in form.turmas:
            ids.append(str(turma.id))
        ano = get_object_or_404(Ano, ano=datetime.datetime.now().year)
        return httprr('/admin/residencia/turma/?id__in={}'.format(','.join(ids)), 'Turmas geradas com sucesso.')
    return locals()

@permission_required('residencia.view_turma')
@rtr()
def turma(request, pk):
    manager = Turma.objects
    obj = get_object_or_404(manager, pk=pk)
    title = f'Turma {obj}'
    is_administrador = in_group(request.user, 'resisdenca Administrador')
    pode_realizar_procedimentos = True

    diarios = obj.diarios_turma_residencia_set.order_by('componente_curricular__componente')

    unidades = obj.unidadeaprendizagemturma_set.all()

    residentes = obj.get_residentes_matriculados()
    # alunos_diarios = obj.get_alunos_matriculados_diarios()
    # diarios_pendentes = obj.diarios_pendentes()
    situacoes_inativas = (
        SituacaoMatriculaPeriodo.CANCELADA,
        SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO,
        SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO,
        SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE,
        SituacaoMatriculaPeriodo.TRANCADA,
        SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE,
        SituacaoMatriculaPeriodo.TRANSF_CURSO,
    )
    qtd_residentes_ativos = residentes.exclude(situacao__in=situacoes_inativas).count()
    # qtd_alunos_ativos += alunos_diarios.exclude(situacao__in=situacoes_inativas).count()

    ids = request.GET.get('matriculas_periodo')
    if ids:
        if not pode_realizar_procedimentos:
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
        matriculas_periodo = MatriculaPeriodo.objects.filter(id__in=ids.split('_'), turma=obj)
        obj.remover_residentes(matriculas_periodo, request.user)

        return httprr(f'/residencia/turma/{obj.pk}/?tab=dados_residentes', 'Residente(s) removido(s) com sucesso.')

    semestre = request.GET.get('semestre') or '1'

    return locals()

@permission_required('residencia.change_turma')
@rtr()
def adicionar_residente_turma(request, pk):
    turma = get_object_or_404(Turma.objects, pk=pk)
    title = 'Adicionar Residente à Turma'

    if 'matriculas_periodo' in request.POST:
        matriculas_periodo = MatriculaPeriodo.objects.filter(id__in=request.POST.getlist('matriculas_periodo'))
        turma.matricular_residentes(matriculas_periodo)
        return httprr(f'/residencia/turma/{turma.pk}/?tab=dados_residentes', 'Residente(s) matriculado(s) com sucesso.')

    matriculas_periodo = turma.get_residentes_apto_matricula()

    return locals()


@permission_required('residencia.view_diario')
@rtr()
def diario(request, pk):
    NOTA_DECIMAL = settings.NOTA_DECIMAL
    CASA_DECIMAL = settings.CASA_DECIMAL
    MULTIPLICADOR_DECIMAL = NOTA_DECIMAL and CASA_DECIMAL == 1 and 10 or 100
    MATRICULADO = SituacaoMatriculaPeriodo.MATRICULADO
    obj = get_object_or_404(Diario.objects, pk=pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, obj.turma.curso_campus)
    acesso_total = pode_realizar_procedimentos
    # qtd_avaliacoes = obj.componente_curricular.qtd_avaliacoes
    qtd_avaliacoes = 4  # quantidade de etapas

    title = f'Diário ({obj.pk}) - {obj.componente_curricular.componente.sigla}'
    pode_manipular_etapa_1 = obj.em_posse_do_registro(1) and acesso_total
    pode_manipular_etapa_2 = obj.em_posse_do_registro(2) and acesso_total
    pode_manipular_etapa_3 = obj.em_posse_do_registro(3) and acesso_total
    pode_manipular_etapa_4 = obj.em_posse_do_registro(4) and acesso_total
    pode_manipular_etapa_5 = obj.em_posse_do_registro(5) and acesso_total
    etapa = 5
    quantidade_vagas_estourada = obj.matriculas_diarios_diario_residencia_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).count() > obj.quantidade_vagas

    if 'abrir' in request.GET:
        obj.situacao = Diario.SITUACAO_ABERTO
        obj.save()
        return httprr('.', 'Diário aberto com sucesso.')

    if 'fechar' in request.GET:
        obj.situacao = Diario.SITUACAO_FECHADO
        obj.save()
        return httprr('.', 'Diário fechado com sucesso.')

    if request.method == 'POST' and request.user.has_perm('residencia.add_preceptordiario'):
        if 'lancamento_nota' in request.POST:
            if running_tests():
                try:
                    obj.processar_notas(request.POST)
                    return httprr('.', 'Notas registradas com sucesso.')
                except Exception as e:
                    return httprr('..', str(e), 'error', anchor='etapa')

    exibir_todos_alunos = not obj.matriculas_diarios_diario_residencia_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).exists()

    matriculas_diario_por_polo = obj.get_matriculas_diario_por_polo()
    return locals()


@permission_required('residencia.lancar_nota_diario')
@rtr()
def registrar_nota_ajax(request, id_nota_avaliacao, nota=None):
    nota_avaliacao = get_object_or_404(NotaAvaliacao, pk=id_nota_avaliacao)
    etapa = nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa
    diario = nota_avaliacao.matricula_diario.diario
    pode_registrar_nota = True
    # pode_registrar_nota = False
    # se a situação do aluno no diário for "Cursando"
    # if nota_avaliacao.matricula_diario.is_cursando():
    #     qs_professor_diario = diario.professordiario_set.filter(professor__vinculo__user=request.user)
    #
    #     if perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus) and diario.em_posse_do_registro(etapa):
    #         pode_registrar_nota = True
    #
    #     elif qs_professor_diario.exists() and not diario.em_posse_do_registro(etapa):
    #         unico_professor = diario.professordiario_set.filter(ativo=True).count() == 1
    #         if unico_professor or diario.estrutura_curso.pode_lancar_nota_fora_do_prazo:
    #             pode_registrar_nota = True
    #         else:
    #             data_atual = datetime.date.today()
    #             etapa_string = etapa == 5 and 'final' or str(etapa)
    #             professor_diario = qs_professor_diario[0]
    #             data_inicio_etapa = getattr(professor_diario, f'data_inicio_etapa_{etapa_string}', None)
    #             data_fim_etapa = getattr(professor_diario, f'data_fim_etapa_{etapa_string}', None)
    #             if data_inicio_etapa and data_fim_etapa and data_inicio_etapa <= data_atual <= data_fim_etapa:
    #                 pode_registrar_nota = True

    if pode_registrar_nota:
        nota_avaliacao.nota = None if nota is None else float(nota)
        nota_avaliacao.save()
        nota_avaliacao.matricula_diario.registrar_nota_etapa(nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa)
        attr_nota = 'nota_{}'.format(int(etapa) == 5 and 'final' or etapa)
        attr_etapa = f'posse_etapa_{etapa}'
        nota_etapa = getattrr(nota_avaliacao.matricula_diario, attr_nota)
        posse_etapa = getattrr(nota_avaliacao.matricula_diario.diario, attr_etapa)
        dict_resposta = {
            'etapa': '-' if nota_etapa is None else nota_etapa,
            # 'media': nota_avaliacao.matricula_diario.get_media_disciplina() or '-',
            # 'media_final': nota_avaliacao.matricula_diario.get_media_final_disciplina() or '-',
            'situacao': nota_avaliacao.matricula_diario.get_situacao_nota(),
            'posse': posse_etapa,
            # 'em_prova_final': nota_avaliacao.matricula_diario.is_em_prova_final(),
            # 'prova_final_invalida': not nota_avaliacao.matricula_diario.is_em_prova_final() and nota_avaliacao.matricula_diario.nota_final,
        }
        return JsonResponse(dict_resposta)


@permission_required('residencia.lancar_nota_diario')
@rtr()
def registrar_nota_unidade_ajax(request, id_nota_avaliacao, nota=None):
    nota_avaliacao = get_object_or_404(NotaAvaliacaoUnidadeAprendizagem, pk=id_nota_avaliacao)
    etapa = nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa
    unidade_aprendizagem_turma = nota_avaliacao.matricula_unidade_aprendizagem_turma.unidade_aprendizagem_turma
    pode_registrar_nota = True
    # pode_registrar_nota = False
    # se a situação do aluno no diário for "Cursando"
    # if nota_avaliacao.matricula_diario.is_cursando():
    #     qs_professor_diario = diario.professordiario_set.filter(professor__vinculo__user=request.user)
    #
    #     if perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus) and diario.em_posse_do_registro(etapa):
    #         pode_registrar_nota = True
    #
    #     elif qs_professor_diario.exists() and not diario.em_posse_do_registro(etapa):
    #         unico_professor = diario.professordiario_set.filter(ativo=True).count() == 1
    #         if unico_professor or diario.estrutura_curso.pode_lancar_nota_fora_do_prazo:
    #             pode_registrar_nota = True
    #         else:
    #             data_atual = datetime.date.today()
    #             etapa_string = etapa == 5 and 'final' or str(etapa)
    #             professor_diario = qs_professor_diario[0]
    #             data_inicio_etapa = getattr(professor_diario, f'data_inicio_etapa_{etapa_string}', None)
    #             data_fim_etapa = getattr(professor_diario, f'data_fim_etapa_{etapa_string}', None)
    #             if data_inicio_etapa and data_fim_etapa and data_inicio_etapa <= data_atual <= data_fim_etapa:
    #                 pode_registrar_nota = True

    if pode_registrar_nota:
        nota_avaliacao.nota = None if nota is None else float(nota)
        nota_avaliacao.save()
        nota_avaliacao.matricula_unidade_aprendizagem_turma.registrar_nota_etapa(nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa)
        attr_nota = 'nota_{}'.format(int(etapa) == 5 and 'final' or etapa)
        attr_etapa = f'posse_etapa_{etapa}'
        nota_etapa = getattrr(nota_avaliacao.matricula_unidade_aprendizagem_turma, attr_nota)
        posse_etapa = getattrr(nota_avaliacao.matricula_unidade_aprendizagem_turma.unidade_aprendizagem_turma, attr_etapa)
        dict_resposta = {
            'etapa': '-' if nota_etapa is None else nota_etapa,
            'media': nota_avaliacao.matricula_unidade_aprendizagem_turma.get_media_disciplina() or '-',
            # 'media_final': nota_avaliacao.matricula_unidade_aprendizagem_turma.get_media_final_disciplina() or '-',
            'situacao': nota_avaliacao.matricula_unidade_aprendizagem_turma.get_situacao_nota(),
            'posse': posse_etapa,
            # 'em_prova_final': nota_avaliacao.matricula_unidade_aprendizagem_turma.is_em_prova_final(),
            # 'prova_final_invalida': not nota_avaliacao.matricula_unidade_aprendizagem_turma.is_em_prova_final() and nota_avaliacao.matricula_unidade_aprendizagem_turma.nota_final,
        }
        return JsonResponse(dict_resposta)


@permission_required('residencia.add_observacaodiario')
@rtr()
def adicionar_observacaodiario(request, diario_pk):
    title = ' Adicionar Observação'
    diario = Diario.objects.filter(pk=diario_pk).first()
    if diario:
        form = ObservacaoDiarioForm(diario, request.user, request.POST or None, instance=None)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação adicionada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar os dados deste diário.', 'error')
    return locals()


@permission_required('residencia.change_observacaodiario')
@rtr()
def editar_observacaodiario(request, observacao_pk=None):
    title = ' Editar Observação'
    observacao = ObservacaoDiario.objects.get(pk=observacao_pk)
    if request.user == observacao.usuario:
        form = ObservacaoDiarioForm(observacao.diario, request.user, request.POST or None, instance=observacao)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação atualizada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar a obervação de outro usuário.', 'error')
    return locals()


@permission_required('residencia.emitir_boletins')
@documento()
@rtr('diario_pdf.html')
def diario_pdf(request, pk, etapa):
    diarios = []
    etapa = int(etapa)
    diario = get_object_or_404(Diario, pk=pk)
    # etapas = etapa and [etapa] or (list(range(1, diario.componente_curricular.qtd_avaliacoes + 1)) + [5])
    etapas = etapa and [etapa] or (list(range(1, 5)) + [5])
    uo = diario.turma.curso_campus.diretoria.setor.uo
    orientation = 'portrait'
    for i, etapa in enumerate(etapas):
        diario = i == 0 and diario or get_object_or_404(Diario, pk=pk)
        diario.hoje = datetime.date.today()
        diario.uo = diario.turma.curso_campus.diretoria.setor.uo
        diario.etapa = etapa
        diario.map = {}
        diario.matriculas_diario = diario.matriculas_diarios_diario_residencia_set.all().exclude(
            situacao__in=[MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_TRANSFERIDO, MatriculaDiario.SITUACAO_CANCELADO]
        )
        if not running_tests():
            diario.matriculas_diario = diario.matriculas_diario.order_by('matricula_periodo__aluno__pessoa_fisica__nome')
        diario.etapa_s = diario.etapa
        if int(diario.etapa) == 5:
            diario.etapa_s = 'final'
        for i, matricula_diario in enumerate(diario.matriculas_diario):
            matricula_diario.nota = getattr(matricula_diario, f'nota_{diario.etapa_s}')
            matricula_diario.faltas = []
            matricula_diario.total = 0
            datas_verificadas = []
            for contador, aula in enumerate(diario.aulas):
                # adicionando as datas das aulas sem repetição com a respectiva quantidade
                if i == 0:
                    if aula.data not in diario.datas_aulas:
                        diario.datas_aulas[aula.data] = aula.quantidade
                    else:
                        diario.datas_aulas[aula.data] += aula.quantidade
                # calculando o número de faltas em uma data
                if aula.data not in datas_verificadas:
                    key = f'{aula.data};{matricula_diario.id}'
                    quantidade = key in diario.map and diario.map[key]
                    matricula_diario.total += quantidade
                    if not quantidade and contador < len(diario.get_aulas(diario.etapa)):
                        quantidade = '-'
                    matricula_diario.faltas.append(quantidade or '')
                datas_verificadas.append(aula.data)
        diarios.append(diario)
        if orientation == 'portrait' and len(diario.aulas) > 17:
            orientation = 'landscape'
    return locals()


@permission_required('residencia.add_preceptordiario')
@rtr()
def adicionar_preceptor_diario(request, diario_pk, preceptordiario_pk=None):
    title = 'Adicionar Preceptor(a)'
    diario = get_object_or_404(Diario.objects, pk=diario_pk)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    preceptordiario = None
    if preceptordiario_pk:
        preceptordiario = get_object_or_404(PreceptorDiario, pk=preceptordiario_pk)
    form = PreceptorDiarioForm(diario, data=request.POST or None, instance=preceptordiario_pk and preceptordiario or None, request=request)
    if form.is_valid():
        form.save()
        if preceptordiario:
            emails = [preceptordiario.preceptor.email]
            mensagem = """
            Caro(a) Preceptor(a),

            Informamos que houve uma alteração do seu vínculo no diário {} que pode afetar o seu Plano/Relatório Individual de Trabalho de {}.{}.
            """.format(
                diario, diario.ano_letivo.ano, diario.periodo_letivo
            )

            send_mail(
                f'[SUAP] Alteração de Vínculo - Diário {diario}',
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                emails,
                fail_silently=True
            )
        return httprr('..', 'Preceptor(a) adicionado/atualizado com sucesso.')
    return locals()


@login_required()
@rtr()
def visualizar(request, app, modelo, pk):
    if not request.user.has_perm(f'{app}.view_{modelo}'):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    classe = apps.get_model(app, modelo)
    objeto = get_object_or_404(classe, pk=pk)
    metadata = utils.metadata(objeto)
    title = objeto
    return locals()


@permission_required('residencia.change_turma')
@rtr()
def adicionar_residentes_diario(request, diario_pk):
    diario = get_object_or_404(Diario.objects, pk=diario_pk)
    title = 'Matricular Residentes da Turma no Diário'
    qs_matriculas_periodo_turma = diario.turma.get_matriculas_aptas_adicao_turma(diario)
    form = AdicionarResidentesDiarioForm(qs_matriculas_periodo_turma, request.POST or None)
    if form.is_valid():
        count = form.processar(diario)
        if count:
            return httprr('..', f'{count} residente(s) matriculado(s) no diário com sucesso.')
        else:
            return httprr('..', 'Nenhum residente foi matriculado no diário.')
    return locals()


@rtr()
@login_required()
def meus_diarios(request, diarios=None):
    preceptor = get_object_or_404(Servidor, pessoa_fisica__user=request.user)
    if diarios:
        try:
            preceptores_diario = PreceptorDiario.objects.filter(preceptor=preceptor, ativo=True, diario__id__in=diarios.split('_'))
        except Exception:
            return httprr('..', 'Diários inválidos.', 'error')
        title = f'Meus Diários Pendentes ({len(preceptores_diario)})'
    else:
        preceptores_diario = PreceptorDiario.objects.filter(preceptor=preceptor, ativo=True).order_by('diario__turma__curso_campus', 'diario__turma', 'diario')
        qtd_diarios = preceptores_diario.count()
        title = f'Meus Diários ({qtd_diarios})'
    return locals()


@rtr()
@login_required()
def meu_diario(request, diario_pk, etapa=1):
    NOTA_DECIMAL = settings.NOTA_DECIMAL
    CASA_DECIMAL = settings.CASA_DECIMAL
    MULTIPLICADOR_DECIMAL = NOTA_DECIMAL and CASA_DECIMAL == 1 and 10 or 100
    obj = get_object_or_404(Diario.objects, pk=diario_pk)

    etapa = int(etapa)
    if etapa > 5 or etapa < 1:
        return httprr('/residencia/meus_diarios/', 'Escolha uma Etapa Válida', 'error')
    title = f'{str(obj)} - Etapa Única'

    MATRICULADO = SituacaoMatriculaPeriodo.MATRICULADO
    qtd_avaliacoes = 4
    preceptor_diario = get_object_or_404(obj.preceptordiario_set, preceptor__pessoa_fisica__user=request.user)
    if not preceptor_diario.ativo:
        return httprr('/residencia/meus_diarios/', f'Vínculo com o diário {diario_pk} inativo', 'error')

    pode_manipular_etapa_1 = True
    pode_manipular_etapa_2 = True
    pode_manipular_etapa_3 = True
    pode_manipular_etapa_4 = True
    pode_manipular_etapa_5 = True
    pode_realizar_procedimentos = False

    qtd_preceptores = obj.preceptordiario_set.filter(ativo=True).count()

    acesso_total = True
    if not preceptor_diario and not in_group(
        request.user, 'Coordenadores(as) Residência,Secretário(a) Residência'
    ):
        raise PermissionDenied()

    if request.method == 'POST':

        if 'lancamento_nota' in request.POST:
            url = f'/residencia/meu_diario/{obj.pk}/{etapa}/?tab=notas'
            try:
                if running_tests():
                    obj.processar_notas(request.POST)
                return httprr(url, 'Notas registradas com sucesso.', anchor='etapa')
            except Exception as e:
                return httprr(url, str(e), 'error', anchor='etapa')

    exibir_todos_alunos = not obj.matriculas_diarios_diario_residencia_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).exists()
    matriculas_diario_por_polo = obj.get_matriculas_diario_por_polo()
    return locals()


#FES-68
#TODO ProjetoFinalForm,
# LancarResultadoProjetoFinalResidenteForm,
# UploadDocumentoProjetoFinalForm,
# ParticipacaoProjetoFinalResidenteForm

@login_required()
@rtr()
def adicionar_projeto_final_residente(request, residente_pk, projetofinal_residente_pk=None):
    title = '{} Trabalho de Conclusão de Curso / Relatório'.format(projetofinal_residente_pk and 'Editar' or 'Adicionar')

    projeto_final_residente = None
    if projetofinal_residente_pk:
        projeto_final_residente = get_object_or_404(ProjetoFinalResidencia, pk=projetofinal_residente_pk)

    residente = get_object_or_404(Residente, pk=residente_pk)

    pode_realizar_procedimentos = True
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = ProjetoFinalResidenciaForm(residente, request.POST or None, instance=projeto_final_residente, request=request)

    if form.is_valid():
        obj = form.save()

        if not projetofinal_residente_pk:
            return httprr(f'/residencia/residente/{residente.matricula}/?tab=projeto', 'TCR / Relatório adicionado com sucesso.')
        else:
            return httprr(f'/residencia/residente/{residente.matricula}/?tab=projeto', 'TCR / Relatório atualizado com sucesso.')

    return locals()


@login_required()
@rtr()
def lancar_resultado_projeto_final_residente(request, projetofinal_residente_pk=None):
    title = 'Lançar Resultado de TCC / Relatório'
    projeto_final_residente = get_object_or_404(ProjetoFinalResidencia.objects, pk=projetofinal_residente_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, projeto_final_residente.matricula_periodo.residente.curso_campus)
    if not pode_realizar_procedimentos:
        if not projeto_final_residente.presidente.vinculo == request.user.get_vinculo():
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    if not projeto_final_residente.pode_ser_editado():
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    initial = dict(resultado_nota=projeto_final_residente.nota, tipo_documento=(projeto_final_residente.documento_url and 1 or 2))

    form = LancarResultadoProjetoFinalResidenciaForm(request.POST or None, files=request.FILES or None, instance=projeto_final_residente, initial=initial)
    if form.is_valid():
        complemento = ''
        form.save()

        if form.tipo_ata == 'eletronica':
            if projeto_final_residente.presidente and projeto_final_residente.presidente.vinculo == request.user.get_vinculo():
                return httprr(
                    '/admin/residencia/ataeletronicaresidente/?tab=tab_pendentes',
                    'Resultado registrado com sucesso. Realize a assinatura da ata eletrônica'
                )
            complemento = 'A ata eletrônica foi gerada e as solicitações de assinatura foram enviadas para os membros da banca por e-mail.'

        return httprr('/residencia/residente/{}/?tab=projeto'.format(
            projeto_final_residente.matricula_periodo.residente.matricula), f'Resultado registrado com sucesso. {complemento}'
        )

    return locals()


@login_required()
@rtr()
def upload_documento_projeto_final_residente(request, projetofinal_residente_pk=None):
    title = 'Upload Documento Final de TCC/Relatório'
    projeto_final_residente = get_object_or_404(ProjetoFinalResidencia.objects, pk=projetofinal_residente_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, projeto_final_residente.matricula_periodo.residente.curso_campus)
    if not pode_realizar_procedimentos:
        if not projeto_final_residente.presidente.vinculo == request.user.get_vinculo():
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = UploadDocumentoProjetoFinalResidenciaForm(request.POST or None, files=request.FILES or None, instance=projeto_final_residente)
    if form.is_valid():
        form.save()
        return httprr('/residencia/residente/{}/?tab=projeto'.format(
            projeto_final_residente.matricula_periodo.residente.matricula), 'Resultado registrado com sucesso.'
        )

    return locals()


@documento('Ata de Projeto Final')
@login_required()
@rtr('ata_projeto_final_pdf.html')
def ata_eletronica_projeto_final_residente_pdf(request, pk):
    obj = get_object_or_404(AtaEletronicaResidencia, pk=pk)
    dados_assinatura = []
    for assinatura in obj.get_assinaturas().filter(data__isnull=False):
        dados_assinatura.append(
            dict(
                nome=assinatura.pessoa_fisica.nome,
                matricula=assinatura.pessoa_fisica.cpf,
                data=assinatura.data.strftime('%d/%m/%Y %H:%M:%S'),
                chave=assinatura.chave
            )
        )
    request.GET._mutable = True
    request.GET['dados_assinatura'] = json.dumps(dados_assinatura)
    request.GET._mutable = False
    return imprimir_ata_projeto_final_residente_pdf(request, obj.projeto_final_residente.pk)


def visualizar_ata_eletronica_residente(request, pk):
    obj = get_object_or_404(AtaEletronicaResidencia, pk=pk)
    if not obj.get_assinaturas().filter(data__isnull=True).exists():
        return HttpResponseRedirect(f'/residencia/ata_eletronica_projeto_final_residente_pdf/{obj.pk}/')
    else:
        return HttpResponseRedirect(f'/residencia/ata_projeto_final_residente_pdf/{obj.projeto_final_residente.pk}/')


@documento()
@login_required()
@rtr()
def ata_projeto_final_residente_pdf(request, projetofinal_residente_pk):
    return imprimir_ata_projeto_final_residente_pdf(request, projetofinal_residente_pk)


def imprimir_ata_projeto_final_residente_pdf(request, projetofinal_residente_pk):
    title = 'Lançar Resultado de Trabalho de Conclusão de Curso'
    obj = get_object_or_404(ProjetoFinalResidencia.objects, pk=projetofinal_residente_pk)
    ata_eletronica = obj.get_ata_eletronica_residente()
    artigo_aluno = obj.matricula_periodo.residente.pessoa_fisica.sexo == 'F' and 'a' or 'o'
    artigo_presidente = obj.presidente and obj.presidente.vinculo and obj.presidente.vinculo.pessoa.pessoafisica.sexo == 'F' and 'a' or 'o'
    artigo_tipo = obj.tipo in ('Monografia', 'Dissertação', 'Tese') and 'da' or 'do'
    uo = obj.matricula_periodo.residente.curso_campus.diretoria.setor.uo
    hoje = dateformat.format(datetime.date.today(), r'd \d\e F \d\e Y')
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    lista_preceptores = []
    lista_assinaturas = set()
    coorienadores = obj.coorientadores.all().values_list('nome', flat=True)
    if obj.presidente:
        preceptor = obj.get_titulo_participante('presidente')
        lista_preceptores.append(preceptor)
        lista_assinaturas.add(preceptor[2])
    if obj.examinador_interno:
        preceptor = obj.get_titulo_participante('examinador_interno')
        lista_preceptores.append(preceptor)
        lista_assinaturas.add(preceptor[2])
    if obj.examinador_externo:
        preceptor = obj.get_titulo_participante('examinador_externo')
        lista_preceptores.append(preceptor)
        lista_assinaturas.add(preceptor[2])
    if obj.terceiro_examinador:
        preceptor = obj.get_titulo_participante('terceiro_examinador')
        lista_preceptores.append(preceptor)
        lista_assinaturas.add(preceptor[2])
    if obj.suplente_interno:
        preceptor = obj.get_titulo_participante('suplente_interno')
        lista_preceptores.append(preceptor)
        lista_assinaturas.add(preceptor[2])
    if obj.suplente_externo:
        preceptor = obj.get_titulo_participante('suplente_externo')
        lista_preceptores.append(preceptor)
        lista_assinaturas.add(preceptor[2])
    if obj.terceiro_suplente:
        preceptor = obj.get_titulo_participante('terceiro_suplente')
        lista_preceptores.append(preceptor)
        lista_assinaturas.add(preceptor[2])
    return locals()


@login_required()
@documento('Declaração de Participação em Projeto Final', False, validade=30, enumerar_paginas=False, modelo='edu.projetofinal')
@rtr()
def declaracao_participacao_projeto_final_residente_pdf(request, pk, participante):
    title = 'Imprimir Declaração de Participação em Projeto Final'
    obj = get_object_or_404(ProjetoFinalResidencia.objects, pk=pk)
    if participante == 'coorientador':
        preceptor = obj.coorientadores.get(pk=request.GET['coorientador'])
        sexo = preceptor.sexo
        participacao = 'Coorientador'
    else:
        sexo, participacao, _ = obj.get_titulo_participante(participante)
        preceptor = None
        if hasattr(obj, participante):
            preceptor = getattr(obj, participante)
        else:
            return httprr('..', 'Escolha um participante válido.', 'error')
    pessoa_fisica = hasattr(preceptor, 'vinculo') and preceptor.vinculo.relacionamento.pessoa_fisica or preceptor
    artigo_professor = sexo == 'F' and 'a' or 'o'
    artigo_aluno = obj.matricula_periodo.residente.pessoa_fisica.sexo == 'F' and 'a' or 'o'
    lista_preceptores = []
    if obj.presidente and obj.orientador != obj.presidente:
        lista_preceptores.append(obj.get_titulo_participante('presidente'))
    if obj.orientador:
        lista_preceptores.append(obj.get_titulo_participante('orientador'))
    if obj.examinador_interno:
        lista_preceptores.append(obj.get_titulo_participante('examinador_interno'))
    if obj.examinador_externo:
        lista_preceptores.append(obj.get_titulo_participante('examinador_externo'))
    if obj.terceiro_examinador:
        lista_preceptores.append(obj.get_titulo_participante('terceiro_examinador'))
    if obj.suplente_interno:
        lista_preceptores.append(obj.get_titulo_participante('suplente_interno'))
    if obj.suplente_externo:
        lista_preceptores.append(obj.get_titulo_participante('suplente_externo'))
    if obj.terceiro_suplente:
        lista_preceptores.append(obj.get_titulo_participante('terceiro_suplente'))
    pks = [item[2].pk for item in lista_preceptores]
    for coorientador in obj.coorientadores.exclude(pk__in=pks):
        sexo = coorientador.sexo or 'M'
        if sexo == 'M':
            lista_preceptores.append(('M', 'Coorientador', coorientador))
        else:
            lista_preceptores.append(('F', 'Coorientadora', coorientador))
    if (
        not perms.tem_permissao_realizar_procedimentos(request.user, obj.matricula_periodo.residente)
        and not perms.is_orientador(request, obj.matricula_periodo.residente)
        and not perms.is_coorientador(request, obj.matricula_periodo.residente)
        and not perms.is_examinador(request, obj.matricula_periodo.residente)
        and not perms.is_presidente(request, obj.matricula_periodo.residente)
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    uo = obj.matricula_periodo.residente.curso_campus.diretoria.setor.uo
    hoje = dateformat.format(datetime.date.today(), r'd \d\e F \d\e Y')
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    return locals()


@login_required()
@rtr()
def declaracao_participacao_projeto_final_residente(request, projetofinal_residente_pk):
    title = 'Imprimir Declaração de Participação em Projeto Final'
    obj = get_object_or_404(ProjetoFinalResidencia.objects, pk=projetofinal_residente_pk)

    if not perms.tem_permissao_realizar_procedimentos(request.user, obj.matricula_periodo.residente) and not perms.is_orientador(request, obj.matricula_periodo.residente):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = ParticipacaoProjetoFinalResidenciaForm(projeto_final=obj)

    participante = request.GET.get('participante')
    if participante:
        return HttpResponseRedirect(f'/residencia/declaracao_participacao_projeto_final_residente_pdf/{projetofinal_residente_pk}/{participante}/')
    return locals()


@rtr()
@login_required()
def visualizar_projetofinal_residente(request, projetofinal_residente_pk=None):
    obj = get_object_or_404(ProjetoFinalResidencia, pk=projetofinal_residente_pk)
    return locals()

@login_required()
@rtr()
def assinar_ata_eletronica_residencia(request, pk):
    title = 'Assinar Ata Eletrônica'
    assinatura = get_object_or_404(AssinaturaAtaEletronicaResidencia, pk=pk)
    if assinatura.pessoa_fisica.user != request.user:
        return HttpResponseForbidden()
    form = IniciarSessaoAssinaturaSenhaForm(data=request.POST or None, request=request)
    if form.is_valid():
        assinatura.assinar()
        return httprr('..', 'Assinatura eletrônica realizada com sucesso.')
    return locals()
# @permission_required('residencia.add_observacao')
@rtr()
def adicionar_frequencia_residente(request, residente_pk):
    title = 'Adicionar Frequencia do Residente'
    residente = Residente.objects.filter(pk=residente_pk).first()
    if residente:
        form = FrequenciaResidenteForm(residente, request.POST or None, instance=None)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Frequencia Registrada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar os dados deste residente.', 'error')
    return locals()

@rtr()
def upload_documento_frequencia_residente(request, residente_pk):
    title = 'Upload Documento de Frequencia Mensal do Residente'
    residente = Residente.objects.filter(pk=residente_pk).first()
    if residente:
        form = DocumentoFrequenciaMensalResidenteForm(residente, request.POST or None, request.FILES or None, instance=None)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Documento Mensal de Frequencia Registrada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar os dados deste residente.', 'error')
    return locals()


@rtr()
@group_required("Preceptor(a), Secretário(a) Residência")
def confirmar_frequencia_residente(request, frequencia_pk):
    obj = get_object_or_404(FrequenciaResidente, pk=frequencia_pk)
    obj.confirmacao = True
    obj.preceptor_confirmador = request.user.get_relacionamento()
    obj.save()
    return httprr('/residencia/diario/{}/?tab=frequencias'.format(obj.diario.diario.id), 'Frequencia Confirmada com sucesso.')


@rtr()
def editar_frequencia_residente(request, frequencia_pk=None):
    title = ' Editar Frequencia'
    frequencia = FrequenciaResidente.objects.get(pk=frequencia_pk)
    if request.user == frequencia.residente:
        form = FrequenciaResidenteForm(frequencia.residente, request.POST or None, instance=frequencia)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação atualizada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar a observação de outro usuário.', 'error')
    return locals()


@permission_required('residencia.add_residente')
@rtr()
def analisar_soliciteletivo(request, solicitresidente_pk):
    title = 'Analisar Solicitação de Estágio Eletivo'
    obj = get_object_or_404(SolicitacaoEletivo, pk=solicitresidente_pk)

    residente = obj.residente
    estagio = obj.estagio

    form = AnalisarSolicitacaoEletivoForm(request.POST or None, instance=obj)
    if form.is_valid():

        situacao = int(form.cleaned_data['situacao'])

        obj2 = form.save(False)
        novo_estagio = None
        if not estagio:
            if situacao == SolicitacaoEletivo.SITUACAO_ATENDIDO:
                novo_estagio = EstagioEletivo()
                novo_estagio.numero_seguro = obj2.numero_seguro
                novo_estagio.nome_servico = obj2.nome_servico
                novo_estagio.cidade_servico = obj2.cidade_servico
                novo_estagio.data_inicio = obj2.data_inicio
                novo_estagio.data_fim = obj2.data_fim
                novo_estagio.local_estagio = obj2.local_estagio
                novo_estagio.justificativa_estagio = obj2.justificativa_estagio
                novo_estagio.residente = obj2.residente

                novo_estagio.save()
            if novo_estagio:
                obj2.estagio = novo_estagio
            obj2.parecer_autor_vinculo = request.user.get_vinculo()
            obj2.parecer_data = datetime.datetime.now()

        obj2.save()

        return httprr('..', 'Solicitação analisada com sucesso.')
    return locals()


@rtr()
@group_required("Residente")
def minhas_solicitacoes_eletivo(request):
    title = 'Minhas Solicitações de Estágio Eletivo'
    solicitacoes = SolicitacaoEletivo.objects.filter(residente__pessoa_fisica__user__username=request.user.username)
    return locals()


@rtr()
@group_required("Residente")
def solicitar_eletivo(request):
    title = 'Solicitação de Estágio Eletivo'
    residente = get_object_or_404(Residente, pessoa_fisica__user__username=request.user.username)

    form = SolicitarEletivoForm(request.POST or None)
    if form.is_valid():
        obj2 = form.save(False)
        obj2.residente = residente

        obj2.save()

        return httprr('..', 'Solicitação cadastrada com sucesso.')

    return locals()


@login_required()
@rtr()
def visualizar_solicitacao_eletivo(request, pk):
    title = 'Visualizar Solicitação de Estágio Eletivo'
    obj = get_object_or_404(SolicitacaoEletivo, pk=pk)
    return locals()


@rtr()
@group_required("Residente")
def meus_estagios_eletivos(request):
    title = 'Meus Estágios Eletivos'
    meus_estagios = EstagioEletivo.objects.filter(residente__pessoa_fisica__user__username=request.user.username)
    return locals()


@login_required()
@rtr()
def visualizar_estagio_eletivo(request, pk):
    title = 'Visualizar Estágio Eletivo'
    obj = get_object_or_404(EstagioEletivo, pk=pk)
    pode_anexar = perms.is_proprio_residente(request, obj.residente)
    return locals()


@rtr()
@login_required
def adicionar_anexo_eletivo(request, pk, tipo=1):
    obj = get_object_or_404(EstagioEletivo, pk=pk)
    if tipo==1:
        doc = 'Relatório'
        url_retorno = f'{obj.get_absolute_url()}?tab=relat'
    elif tipo==2:
        doc = 'Avaliação'
        url_retorno = f'{obj.get_absolute_url()}?tab=aval'
    else:
        doc = 'Frequência'
        url_retorno = f'{obj.get_absolute_url()}?tab=freq'

    title = f'Adicionar {doc}'
    pode_anexar = perms.is_proprio_residente(request, obj.residente)
    if not pode_anexar:
        raise PermissionDenied(f'Você não tem permissão para adicionar {doc}.')
    form = EstagioEletivoAnexoForm(request.POST or None, request.FILES or None)
    form.instance.estagio = obj
    form.instance.tipo_arquivo = tipo
    form.instance.anexado_por = request.user
    if form.is_valid():
        form.save()
        return httprr(url_retorno, f'{doc} adicionado com sucesso.')
    return locals()

@rtr()
@permission_required('residencia.view_solicitacaousuario')
def solicitacaousuario(request, pk):
    obj = get_object_or_404(SolicitacaoUsuario.locals, pk=pk)

    filho_verbose_name = obj.sub_instance_title()
    filho = obj.sub_instance()
    title = f'{filho_verbose_name} {pk}'

    obj = get_object_or_404(filho.__class__.locals, pk=pk)

    eh_solicitacao_desligamentos = filho_verbose_name == 'Solicitação de Desligamentos'
    eh_solicitacao_diplomas = filho_verbose_name == 'Solicitação de Diplomas'
    eh_solicitacao_ferias = filho_verbose_name == 'Solicitação de Férias'
    eh_solicitacao_licencas= filho_verbose_name == 'Solicitação de Licenças'
    eh_solicitacao_congressos = filho_verbose_name == 'Solicitação de Congressos'

    residente = Residente.objects.filter(pessoa_fisica__user=obj.solicitante)
    if residente:
        residente = residente[0]
    atender = request.GET.get('atender', False)
    if request.user.has_perm('residencia.change_solicitacaousuario'):
        # if 'avisar_coordenador' in request.GET and eh_atividade_complementar:
        #     if filho.enviar_email_coordenador():
        #         filho.atender(request.user)
        #         return httprr('..', 'Email enviado com sucesso.')
        #     else:
        #         return httprr('..', 'Falha ao tentar enviar email.')
        if atender:
            filho.atender(request.user, residente)
            return httprr('..', 'Solicitação deferida com sucesso.')
    return locals()


@rtr()
@login_required()
def solicitar_desligamento(request):
    title = 'Solicitação de Desligamentos'
    if request.user.eh_residente:
        residente = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoDesligamentosForm(data=request.POST or None, residente=residente)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()
@rtr()
@login_required()
def solicitar_diplomas(request):
    title = 'Solicitação de Diplomas'
    if request.user.eh_residente:
        residente = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoDiplomasForm(data=request.POST or None, residente=residente)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()


@rtr()
@login_required()
def solicitar_ferias(request):
    title = 'Solicitação de Férias'
    if request.user.eh_residente:
        residente = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoFeriasForm(data=request.POST or None, residente=residente)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()


@rtr()
@login_required()
def solicitar_licencas(request):
    title = 'Solicitação de Licenças'
    if request.user.eh_residente:
        residente = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoLicencasForm(data=request.POST or None, residente=residente)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()


@rtr()
@login_required()
def solicitar_congressos(request):
    title = 'Solicitação de Congressos e afins'
    if request.user.eh_residente:
        residente = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoCongressosForm(data=request.POST or None, residente=residente)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()

@rtr()
@permission_required('residencia.change_solicitacaousuario')
def atender_solicitacaousuario(request, pks):
    title = 'Atender Solicitação'
    solicitacoes = SolicitacaoUsuario.objects.filter(pk__in=pks.split('_'))
    for solicitacao in solicitacoes:
        solicitacao.sub_instance().atender(request.user, residente=solicitacao.solicitante.get_relacionamento())
    return httprr('..', 'Solicitações deferidas com sucesso.')
    return locals()

@rtr()
@permission_required('residencia.change_solicitacaousuario')
def rejeitar_solicitacao(request, pks):
    title = 'Rejeitar Solicitação'
    solicitacoes = SolicitacaoUsuario.objects.filter(pk__in=pks.split('_'))
    for solicitacao in solicitacoes:
        filho_verbose_name = solicitacao.sub_instance_title()
        filho = solicitacao.sub_instance()
        solicitacao = get_object_or_404(filho.__class__.locals, pk=solicitacao.pk)

    form = RejeitarSolicitacaoUsuarioForm(data=request.POST or None)

    if form.is_valid():
        for solicitacao in solicitacoes:
            solicitacao.rejeitar(request.user, request.POST['razao_indeferimento'])
        return httprr('..', 'Solicitações indeferidas com sucesso.')

    return locals()

@rtr()
@permission_required('residencia.gerar_relatorio')
def relatorio_corpo_pedagogico(request):
    title = 'Relatório do corpo pedagógico'
    campus = None
    if not in_group(request.user,
                    'Secretário(a) Residência, Coordenadores(as) Residência'):
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = RelatorioCorpoPedagogicoForm(campus, request.GET or None)

    if form.is_valid():
        turma = form.cleaned_data['turma']
        matriz = form.cleaned_data['matriz']
        ano_letivo = form.cleaned_data['ano_letivo']
        periodo_letivo = form.cleaned_data['periodo_letivo']


        qs_matriculas_periodo = MatriculaPeriodo.objects.all()

        if ano_letivo:
            qs_matriculas_periodo = qs_matriculas_periodo.filter(ano_letivo=ano_letivo)

        if periodo_letivo != '' and int(periodo_letivo):
            qs_matriculas_periodo = qs_matriculas_periodo.filter(periodo_letivo=periodo_letivo)

        if matriz:
            qs_matriculas_periodo = qs_matriculas_periodo.filter(residente__matriz=matriz)

        if turma:
            qs_matriculas_periodo = qs_matriculas_periodo.filter(turma=turma)


        qs_matriculas_periodo = qs_matriculas_periodo.order_by('residente__pessoa_fisica__nome').distinct('residente__pessoa_fisica__nome')

        total_residentes_ativos = qs_matriculas_periodo.filter(residente__situacao__pk=SituacaoMatricula.MATRICULADO).count()
        total_residentes_desligados = qs_matriculas_periodo.filter(residente__situacao=SituacaoMatricula.DESLIGADO).count()
        total_residentes_ferias = 0
        total_residentes_licencas = 0
        hoje = datetime.datetime.now()

        for mp in qs_matriculas_periodo:
            if mp.residente.esta_de_ferias_hoje():
                total_residentes_ferias=+1

            qs_licenca_hoje = mp.residente.get_solicitacoes_licencas_aprovadas().filter(data_inicio__lte=hoje,
                                                                                        data_fim__gte=hoje)
            if qs_licenca_hoje.exists():
                total_residentes_licencas=total_residentes_licencas+1

        # Grafrico licenças
        # grafico 1
        dados_licenca = list()
        groups_licenca = []


        series_licenca = SolicitacaoLicencas.objects.filter(data_inicio__lte=hoje, data_fim__gte=hoje, atendida=True).values_list('tipo').annotate(
            qtd=Count('tipo')).order_by('tipo')

        for s in series_licenca:

            tipos = dict(SolicitacaoLicencas.TIPO_LICENCA_CHOICES)
            dados_licenca.append([tipos[s[0]], s[1]])
            groups_licenca.append(tipos[s[0]])

        id_grafico_licenca = 'grafico_licenca'
        grafico_licenca = PieChart('grafico_licenca', title='Tipos de licenças (Hoje)', subtitle='Total por tipo de licença', minPointLength=0,
                            data=dados_licenca)
        grafico_licenca.id = id_grafico_licenca

    if 'exportar' in request.GET:
            lista = []
            matriculas_periodos_ids = request.POST.getlist('select_residente')
            if matriculas_periodos_ids:
                ids = map(int, matriculas_periodos_ids)
                for matricula_periodo in qs_matriculas_periodo:
                    if matricula_periodo.id in ids:
                        lista.append(matricula_periodo)
                matriculas_periodos = lista

            response = HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition'] = 'attachment; filename=relatorio_corpo_pedagogico.xls'

            wb = xlwt.Workbook(encoding='utf-8')
            sheet1 = FitSheetWrapper(wb.add_sheet('Relatório de Alunos'))
            style = xlwt.easyxf(
                'pattern: pattern solid, fore_colour gray25; borders: left thin, right thin, top thin, bottom thin; '
                'font: colour black, bold True; align: wrap on, vert centre, horiz center;')

            col = 0
            line = 0

            sheet1.write_merge(line, line + 1, col, col, 'Matrícula', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Residente', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Situação', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Férias', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Licenças', style)
            col += 1
            line = 1

            for matricula_periodo in qs_matriculas_periodo:
                line += 1
                col = 0
                sheet1.row(line).write(col, matricula_periodo.residente.matricula)
                col += 1
                sheet1.row(line).write(col, matricula_periodo.residente.pessoa_fisica.nome)
                col += 1
                sheet1.row(line).write(col, str(matricula_periodo.residente.situacao))
                col += 1
                sheet1.row(line).write(col, matricula_periodo.residente.get_solicitacoes_ferias_aprovadas_datas())
                col += 1
                sheet1.row(line).write(col, matricula_periodo.residente.get_solicitacoes_licencas_aprovadas_datas())
                col += 1
            wb.save(response)

            return response

    return locals()


@permission_required('residencia.gerar_relatorio')
@rtr()
def estatistica(request):
    title = 'Quantitativo de Residentes'
    form = EstatisticaForm(request.GET or None, request=request)

    if form.is_valid():
        anos, periodos, ano_selecionado, periodo_selecionado, grafico_ano, residentes = form.processar()


        alunos = residentes[0:25]
    return locals()


@permission_required('residencia.gerar_relatorio')
@rtr()
def estatistica_eletivo(request):
    title = 'Quantitativo de Residentes em Estágios Eletivos'
    form = EstatisticaEletivoForm(request.GET or None, request=request)

    if form.is_valid():
        anos, periodos, ano_selecionado, periodo_selecionado, grafico_ano, residentes = form.processar()


        alunos = residentes[0:25]
    return locals()


@documento('Declaração de Matrícula', False, validade=30, enumerar_paginas=False, modelo='residencia.residente')
@rtr('declaracaomatricularesidente_pdf.html')
def declaracaomatricularesidente_pdf(request, pk):
    residente = get_object_or_404(Residente, pk=pk)
    situacao = residente.situacao
    #exibir_modalidade = 'Técnico' in aluno.curso_campus.modalidade.descricao
    eh_masculino = residente.pessoa_fisica.sexo == 'M'

    is_usuario_proprio_residente = residente.is_user(request)
    if (
        not is_usuario_proprio_residente
        and not request.user.has_perm('residente.efetuar_matricula')
        and not in_group(request.user, 'Coordenadores(as) Residência','Secretário(a) Residência')
        #and not request.session.get('matricula-servico-impressao') == pk
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not residente.is_matriculado():
        return httprr('..', 'Não possível emitir a declaração, pois o aluno não está matriculado.', 'error')

    matricula_periodo = MatriculaPeriodo.objects.filter(residente=residente).latest('id')
    # uo = aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    # polo = aluno.polo
    return locals()


@documento('Declaração de Orientação TCR', False, validade=30, enumerar_paginas=False, modelo='residencia.residente')
@rtr('declaracao_orientacao_tcr.html')
def declaracao_orientacao_tcr(request, pk):
    residente = get_object_or_404(Residente, pk=pk)
    situacao = residente.situacao
    #exibir_modalidade = 'Técnico' in aluno.curso_campus.modalidade.descricao
    eh_masculino = residente.pessoa_fisica.sexo == 'M'

    is_usuario_proprio_residente = residente.is_user(request)
    if (
        not is_usuario_proprio_residente
        and not request.user.has_perm('residente.efetuar_matricula')
        and not in_group(request.user, 'Coordenadores(as) Residência','Secretário(a) Residência')
        #and not request.session.get('matricula-servico-impressao') == pk
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not residente.is_matriculado():
        return httprr('..', 'Não possível emitir a declaração, pois o aluno não está matriculado.', 'error')

    matricula_periodo = MatriculaPeriodo.objects.filter(residente=residente).latest('id')
    projeto_final = ProjetoFinalResidencia.objects.get(matricula_periodo = matricula_periodo)
    # uo = aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    # polo = aluno.polo
    return locals()


@permission_required('residencia.view_unidadeaprendizagemturma')
@rtr()
def unidadeaprendizagemturma(request, pk):
    NOTA_DECIMAL = settings.NOTA_DECIMAL
    CASA_DECIMAL = settings.CASA_DECIMAL
    MULTIPLICADOR_DECIMAL = NOTA_DECIMAL and CASA_DECIMAL == 1 and 10 or 100
    MATRICULADO = SituacaoMatriculaPeriodo.MATRICULADO
    obj = get_object_or_404(UnidadeAprendizagemTurma.objects, pk=pk)

    # pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, obj.turma.curso_campus)
    acesso_total = True
    # # qtd_avaliacoes = obj.componente_curricular.qtd_avaliacoes
    qtd_avaliacoes = obj.unidade_aprendizagem.qtd_avaliacoes  # quantidade de etapas
    #
    title = f' Unidade de Aprendizagem ({obj.pk}) - {obj.unidade_aprendizagem.descricao}'
    pode_manipular_etapa_1 = obj.em_posse_do_registro(1) and acesso_total
    pode_manipular_etapa_2 = obj.em_posse_do_registro(2) and acesso_total
    # pode_manipular_etapa_3 = obj.em_posse_do_registro(3) and acesso_total
    # pode_manipular_etapa_4 = obj.em_posse_do_registro(4) and acesso_total
    # pode_manipular_etapa_5 = obj.em_posse_do_registro(5) and acesso_total
    # etapa = 5
    # quantidade_vagas_estourada = obj.matriculas_diarios_diario_residencia_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).count() > obj.quantidade_vagas

    if 'abrir' in request.GET:
        obj.situacao = Diario.SITUACAO_ABERTO
        obj.save()
        return httprr('.', 'Diário aberto com sucesso.')

    if 'fechar' in request.GET:
        obj.situacao = Diario.SITUACAO_FECHADO
        obj.save()
        return httprr('.', 'Diário fechado com sucesso.')

    if request.method == 'POST' and request.user.has_perm('residencia.add_preceptordiario'):
        if 'lancamento_nota' in request.POST:
            if running_tests():
                try:
                    obj.processar_notas(request.POST)
                    return httprr('.', 'Notas registradas com sucesso.')
                except Exception as e:
                    return httprr('..', str(e), 'error', anchor='etapa')

    # exibir_todos_alunos = not obj.matriculas_diarios_diario_residencia_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).exists()

    matriculas_unidadeaprendizagemturma = obj.get_matriculas_unidadeaprendizagemturma_por_polo()
    return locals()

@rtr()
@permission_required('edu.reabrir_diario')
def matricular_avulso_unidadeaprendizagemturma(request, unidadeaprendizagemturma_pk):
    title = 'Matricular Residente  Unidade'

    unidadeaprendizagemturma = get_object_or_404(UnidadeAprendizagemTurma, pk=unidadeaprendizagemturma_pk)
    form = MatricularAlunoAvulsoUnidadeAprendizagemTurmaForm(unidadeaprendizagemturma, request.POST or None, request=request)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Residente matriculado com sucesso.')

    return locals()


@login_required()
@rtr()
def calendarioacademico(request, pk):
    obj = get_object_or_404(CalendarioAcademico.objects, pk=pk)
    residente = Residente.objects.filter(pessoa_fisica__user__username=request.user.username)
    residente = residente and residente[0] or None
    calendario = obj.anual()
    title = str(obj)
    is_popup = request.GET.get('_popup')
    return locals()

@permission_required('residencia.change_unidadeaprendizagemturma')
@rtr()
def transferir_posse_unidadeaprendizagemturma(request, unidadeaprendizagemturma_pk, etapa, destino):
    unidadeaprendizagemturma = get_object_or_404(UnidadeAprendizagemTurma.objects, pk=unidadeaprendizagemturma_pk)

    pode_realizar_procedimentos = True
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    destino = int(destino)
    etapa = int(etapa)
    if etapa == 1:
        unidadeaprendizagemturma.posse_etapa_1 = destino
    elif etapa == 2:
        unidadeaprendizagemturma.posse_etapa_2 = destino
    elif etapa == 3:
        unidadeaprendizagemturma.posse_etapa_3 = destino
    elif etapa == 4:
        unidadeaprendizagemturma.posse_etapa_4 = destino
    elif etapa == 5:
        unidadeaprendizagemturma.posse_etapa_5 = destino
    unidadeaprendizagemturma.save()
    for matricula_unidadeaprendizagemturma in unidadeaprendizagemturma.matriculas_unidadeaprendizagemturma_unidade_aprendizagem_turma_set.all():
        matricula_unidadeaprendizagemturma.registrar_nota_etapa(etapa)
    return httprr(f'/residencia/unidadeaprendizagemturma/{unidadeaprendizagemturma.pk:d}', 'Posse transferida com sucesso.')