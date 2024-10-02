import io
import random
import tempfile
from collections import OrderedDict
from datetime import timedelta
from http.client import HTTPResponse

import xlwt
from PyPDF2 import PdfFileMerger
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.http.response import HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe

from comum.forms import BolsistaForm
from djtools import layout
from djtools.html.calendarios import CalendarioPlus
from djtools.templatetags.filters import getattrr
from djtools.testutils import running_tests
from djtools.utils import (
    documento,
    XlsResponse,
    get_session_cache,
    permission_required,
    send_mail, JsonResponse,
)

from comum.utils import somar_data, insert_space
from comum.forms import UsuarioExternoForm, BolsistaForm
from comum.models import UsuarioExterno, Bolsista
from djtools.utils import rtr, group_required, httprr
from ppe import perms, utils, tasks, moodle
from ppe.forms import *
from ppe.models import Log, RegistroDiferenca, Falta
from suap import settings


@layout.quadro('Tutores', icone='graduation-cap')
def index_quadros_tutores(quadro, request):
    pessoa_fisica_logada = request.user.get_profile()
    if not pessoa_fisica_logada:
        return quadro
    tutor_turma = TutorTurma.objects.filter(tutor__vinculo__user=request.user)
    if tutor_turma:
        if tutor_turma.exists():
            hoje = datetime.datetime.now()
            inicio = hoje - timedelta(days=1)
            diarios = CursoTurma.objects.filter(turma__in=tutor_turma.values_list('turma', flat=True), data_inicio_etapa_1__lt=inicio)
            diarios = diarios.exclude(
                posse_etapa_1=CursoTurma.POSSE_REGISTRO_ESCOLAR,
            )
            pk_diarios = []
            pk_diarios_pendentes = []
            for diario in diarios:
                if diario.matriculacursoturma_set.exists():
                    pk_diarios.append(str(diario.pk))

                fimetapa = hoje - timedelta(days=7)
                if (
                    diario.matriculacursoturma_set.filter(curso_turma__data_fim_etapa_1__lt=fimetapa, curso_turma__posse_etapa_1=CursoTurma.POSSE_TUTOR).exists()
                    or diario.matriculacursoturma_set.filter(curso_turma__data_fim_prova_final__lt=fimetapa, curso_turma__posse_etapa_5=CursoTurma.POSSE_TUTOR).exists()
                ):
                    pk_diarios_pendentes.append(str(diario.pk))

            if pk_diarios:
                turmas = CursoTurma.objects.filter(id__in=pk_diarios).values_list('turma', flat=True)
                quadro.add_item(
                    layout.ItemContador(
                        titulo=len(turmas) == 1 and 'Turma' or 'Turmas',
                        subtitulo='',
                        qtd=len(turmas),
                        url=('/ppe/minhas_turmas/{}'.format('_'.join([str(x) for x in turmas]))),
                    )
                )

        quadro.add_itens(
            [
                layout.ItemAcessoRapido(titulo='Minhas turmas', url='/ppe/minhas_turmas/'),
            ]
        )


    return quadro

@layout.quadro('Faça sua matrícula online', icone='users')
def index_quadros_banners_trabalhadoreseducandos(quadro, request):
    def do():

        if request.user.eh_trabalhadoreducando:
            trabalhadoreducando = request.user.get_relacionamento()

            # matrícula online
            # if trabalhadoreducando.pode_matricula_online():
            #     quadro.add_item(layout.ItemImagem(titulo='Faça sua matrícula online.', path='/static/edu/img/index-banner-trabalhador_educando.png', url='#'))
        return quadro

    return get_session_cache(request, 'index_quadros_banners_trabalhadoreseducandos', do, 24 * 3600)


@layout.info()
def index_infos(request):
    infos = list()

    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()



        if not trabalhadoreducando.pessoa_fisica.nome_usual:
            infos.append(
                dict(url=f"/ppe/atualizar_meus_dados_pessoais/{trabalhadoreducando.matricula}", titulo='Você ainda não possui um nome usual no sistema. Edite o seus dados pessoais.')
            )
        for avaliacao in trabalhadoreducando.get_etapas_disponives():
            print(avaliacao)
            infos.append(
                dict(url=f"/ppe/avaliacao_trabalhador_educando/{trabalhadoreducando.id}/{avaliacao.tipo_avaliacao.id}/",
                     titulo=f"Preencha a Avaliação {avaliacao.tipo_avaliacao}.")
            )

    return infos


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()

        # matrícula online
        # if trabalhadoreducando.pode_matricula_online():
        #     inscricoes.append(dict(url='#', titulo='Faça sua matrícula online.',))

    return inscricoes


@layout.alerta()
def index_alertas(request):
    alertas = list()

    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()
        if not trabalhadoreducando.logradouro:
            alertas.append(dict(url=f'/ppe/atualizar_meus_dados_pessoais/{trabalhadoreducando.matricula}/', titulo='Atualize seus dados pessoais.'))

    return alertas


@layout.quadro('Ensino', icone='pencil-alt')
def index_quadros(quadro, request):
    # PARA ALUNOS

    return quadro


@rtr()
@group_required("RH")
def coordenadores_ppe(request):
    title = 'Coordenadores(as) PPE'

    if 'del_prefil' in request.GET:
        coodenador_ppe = Group.objects.get(name='Coordenador(a) PPE')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])        
        if coodenador_ppe:
            empregado.get_vinculo().user.groups.remove(coodenador_ppe) 
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Coordenador(a) PPE removido(a) com sucesso.')

    coordenadores = Servidor.objects.filter(user__groups__name='Coordenador(a) PPE')

    return locals()

@rtr()
@group_required("RH")
def cadastrar_coordenador_ppe(request):
    title = 'Cadastrar Coordenador(a) PPE'
    form = CoordenadorPpeForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        coodenador_ppe = Group.objects.get(name='Coordenador(a) PPE')
        if registro and coodenador_ppe:
            coodenador_ppe.user_set.add(registro.user)
        return httprr(
            '..',
            'Coordenador(a) PPE cadastrado(a) com sucesso'
        )

    return locals()

@rtr()
@group_required("RH")
def editar_coordenador_ppe(request, empregado_id):
    title = 'Editar Coordenador(a) PPE'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = CoordenadorPpeForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Coordenador(a) PPE atualizado(a) com sucesso'
        )

    return locals()

#SUPERVISORES CAMPO PPE
@rtr()
@group_required("RH,Coordenador(a) PPE")
def supervisores_campo_ppe(request):
    title = 'Supervisores(as) de Campo PPE'

    if 'del_prefil' in request.GET:
        supervisor_campo_ppe = Group.objects.get(name='Supervisor(a) Campo PPE')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])
        if supervisor_campo_ppe:
            empregado.get_vinculo().user.groups.remove(supervisor_campo_ppe)
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Supervisor(a) de Campo PPE removido(a) com sucesso.')

    supervisores = Servidor.objects.filter(user__groups__name='Supervisor(a) Campo PPE')

    return locals()

@rtr()
@group_required("RH,Coordenador(a) PPE")
def cadastrar_supervisor_campo_ppe(request):
    title = 'Cadastrar Supervisor(a) Campo PPE'
    form = SupervisorCampoPpeForm(request.POST or None,instance=None)
    if form.is_valid():
        registro = form.save()
        supervisor_ppe = Group.objects.get(name='Supervisor(a) Campo PPE')
        if registro and supervisor_ppe:
            supervisor_ppe.user_set.add(registro.user)
        return httprr(
            '..',
            'Supervisor(a) de Campo PPE cadastrado(a) com sucesso'
        )

    return locals()

@rtr()
@group_required("RH,Coordenador(a) PPE")
def editar_supervisor_campo_ppe(request, empregado_id):
    title = 'Editar Supervisor(a) Campo PPE'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = SupervisorCampoPpeForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Supervisor(a) de Campo PPE atualizado(a) com sucesso'
        )

    return locals()




@rtr()
@group_required('Coordenador(a) PPE')
def chefia_imediata(request, pk):
    obj = get_object_or_404(ChefiaPPE.objects, pk=pk)

    title = f"{obj.nome} - {obj.cpf}"

    return locals()

@rtr()
@group_required('Coordenador(a) PPE')
def cadastrar_chefia_imediata(request, pessoafisica_id=None):
    """
    Pré cadastro de Chefia imediata

    :param pessoafisica_id:
    :param request:
    :return:
    """

    title = 'Adicionar Chefia imediata'
    initial = dict()
    if pessoafisica_id:
        pessoafisica = PessoaFisica.objects.filter(pk=pessoafisica_id).first()
        initial['cpf'] = pessoafisica.cpf
        initial['nome'] = pessoafisica.nome
        initial['email'] = pessoafisica.email
        initial['confirma_email'] = pessoafisica.email

    form = ChefiaPPEForm(request.POST or None, request=request, initial=initial)

    if form.is_valid():
        chefe = form.save()
        chefia_imediata_ppe = Group.objects.get(name='Chefia imediata PPE')
        if chefia_imediata_ppe:
            chefia_imediata_ppe.user_set.add(chefe.get_vinculo().user)

        return httprr('..', f"Chefia imediata cadastrada com sucesso. Foi enviado um e-mail para "
                          f"{form.cleaned_data['email']} com instruções para acessar o SUAP.")

    return locals()


#FES-33
#------GESTOR PPE
@rtr()
@group_required("RH")
def gestores_ppe(request):
    title = 'Gestor(a) PPE'

    if 'del_prefil' in request.GET:
        gestor_ppe = Group.objects.get(name='Gestor(a) PPE')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])
        if gestor_ppe:
            empregado.get_vinculo().user.groups.remove(gestor_ppe)
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Gestor(a) PPE removido(a) com sucesso.')

    gestores = Servidor.objects.filter(user__groups__name='Gestor(a) PPE')

    return locals()

@rtr()
@group_required("RH")
def cadastrar_gestor_ppe(request):
    title = 'Cadastrar Gestor(a) PPE'
    form = GestorPpeForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Gestor(a) PPE cadastrado(a) com sucesso'
        )

    return locals()

@rtr()
@group_required("RH")
def editar_gestor_ppe(request, empregado_id):
    title = 'Editar Gestor(a) PPE'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = GestorPpeForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Gestor(a) PPE atualizado(a) com sucesso'
        )

    return locals()

#------APOIADOR ADMINISTRATIVO
@rtr()
@group_required("RH")
def apoiadores_administrativos_ppe(request):
    title = 'Apoiador(a) Administrativo PPE'

    if 'del_prefil' in request.GET:
        apoiador_admnistrativo_ppe = Group.objects.get(name='Apoiador(a) Administrativo PPE')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])
        if apoiador_admnistrativo_ppe:
            empregado.get_vinculo().user.groups.remove(apoiador_admnistrativo_ppe)
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Apoiador(a) Adminstrativo PPE removido(a) com sucesso.')

    apoiadores = Servidor.objects.filter(user__groups__name='Apoiador(a) Administrativo PPE')

    return locals()

@rtr()
@group_required("RH")
def cadastrar_apoiador_administrativo_ppe(request):
    title = 'Cadastrar Apoiador(a) Administrativo PPE'
    form = ApoiadorAdministrativoPpeForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Apoiador(a) Adminstrativo PPE cadastrado(a) com sucesso'
        )

    return locals()


@rtr()
@group_required("RH")
def editar_apoiador_administrativo_ppe(request, empregado_id):
    title = 'Editar Apoiador(a) Administrativo PPE'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = ApoiadorAdministrativoPpeForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Apoiador(a) Adminstrativo PPE atualizado(a) com sucesso'
        )

    return locals()

#------SUPERVISOR PEDAGÓGICO
@rtr()
@group_required("RH")
def supervisores_pedagogicos_ppe(request):
    title = 'Supervisor(a) Pedagógico(a) PPE'

    if 'del_prefil' in request.GET:
        supervisor_pedagogico_ppe = Group.objects.get(name='Supervisor(a) Pedagógico(a)')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])
        if supervisor_pedagogico_ppe:
            empregado.get_vinculo().user.groups.remove(supervisor_pedagogico_ppe)
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Supervisor(a) Pedagógico(a) PPE removido(a) com sucesso.')

    supervisores = Servidor.objects.filter(user__groups__name='Supervisor(a) Pedagógico(a)')

    return locals()

@rtr()
@group_required("RH")
def cadastrar_supervisor_pedagogico_ppe(request):
    title = 'Cadastrar Supervisor(a) Pedagógico(a) PPE'
    form = SupervisorPedagogicoPpeForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Supervisor(a) Pedagógico(a) PPE cadastrado(a) com sucesso'
        )

    return locals()

@rtr()
@group_required("RH")
def editar_supervisor_pedagogico_ppe(request, empregado_id):
    title = 'Editar Supervisor(a) Pedagógico(a) PPEE'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = SupervisorPedagogicoPpeForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Supervisor(a) Pedagógico(a) PPE atualizado(a) com sucesso'
        )

    return locals()

#------SUPERVISOR PSICOSSOCIAL
@rtr()
@group_required("RH")
def supervisores_psicossociais_ppe(request):
    title = 'Supervisor(a) Psicossocial PPE'

    if 'del_prefil' in request.GET:
        supervisor_psicossocial_ppe = Group.objects.get(name='Supervisor(a) Psicossocial PPE')
        empregado = Servidor.objects.get(pk=request.GET['del_prefil'])
        if supervisor_psicossocial_ppe:
            empregado.get_vinculo().user.groups.remove(supervisor_psicossocial_ppe)
            empregado.pessoa_fisica.user.delete() 
            empregado.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Supervisor(a) Psicossocial PPE removido(a) com sucesso.')

    supervisores_psicossociais = Servidor.objects.filter(user__groups__name='Supervisor(a) Psicossocial PPE')

    return locals()

@rtr()
@group_required("RH")
def cadastrar_supervisor_psicossocial_ppe(request):
    title = 'Cadastrar Supervisor(a) Psicossocial PPE'
    form = SupervisorPsicossocialPpeForm(request.POST or None)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Supervisor(a) Psicossocial PPE cadastrado(a) com sucesso'
        )

    return locals()

@rtr()
@group_required("RH")
def editar_supervisor_psicossocial_ppe(request, empregado_id):
    title = 'Editar Supervisor(a) Psicossocial PPEE'
    empregado = get_object_or_404(Servidor, pk=empregado_id)
    form = SupervisorPsicossocialPpeForm(request.POST or None, instance=empregado)
    if form.is_valid():
        registro = form.save()
        return httprr(
            '..',
            'Supervisor(a) Psicossocial PPE atualizado(a) com sucesso'
        )

    return locals()


#Apoiador pedagógico
@rtr()
@group_required("Coordenador(a) PPE,Supervisor(a) Pedagógico(a)")
def apoiadores_pedagogicos_ppe(request):
    title = 'Apoiador(a) Pedagógico PPE'


    if 'del_prefil' in request.GET:
        apoiador_pedagogico_ppe = Group.objects.get(name='Apoiador(a) Pedagógico PPE')
        bolsista = Bolsista.objects.get(pk=request.GET['del_prefil'])
        if apoiador_pedagogico_ppe:
            bolsista.get_vinculo().user.groups.remove(apoiador_pedagogico_ppe)
            bolsista.pessoa_fisica.user.delete() 
            bolsista.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Apoiador(a) Pedagógico PPE removido(a) com sucesso.')

    apoiadores = Bolsista.objects.filter(user__groups__name='Apoiador(a) Pedagógico PPE')

    return locals()

@rtr()
@group_required("Coordenador(a) PPE,Supervisor(a) Pedagógico(a)")
def cadastrar_apoiador_pedagogico_ppe(request, pessoafisica_id=None):
    title = 'Cadastrar Apoiador(a) Pedagógico PPE'
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
            bolsita.ativo = False
            bolsita.eh_prestador = False
            bolsita.bolsita = True
            bolsita.save()
            bolsita.enviar_email_pre_cadastro()

            apoiador_pedagogico_ppe = Group.objects.get(name='Apoiador(a) Pedagógico PPE')
            if apoiador_pedagogico_ppe:
                apoiador_pedagogico_ppe.user_set.add(bolsita.get_vinculo().user)

            # Ativa o usuário externo criando o papel caso não possua
            bolsita.ativar()

            return httprr('..', f"Bolsista cadastrada com sucesso. Foi enviado um e-mail para "
                                f"{form.cleaned_data['email']} com instruções para acessar o SUAP.")

        except Exception as e:
            if settings.DEBUG:
                raise e
            return httprr('..', message=str(f"Houve um erro ao cadastrar o usuário. Detalhes: {e}"), tag='error')

    return locals()

#------TRABALHADOR EDUCANDO
@rtr()
@login_required()
def trabalhadoreducando(request, matricula):
    trabalhadoreducando = get_object_or_404(
        TrabalhadorEducando,
        matricula=matricula,
    )
    title = f'{normalizar_nome_proprio(trabalhadoreducando.get_nome())} ({str(trabalhadoreducando.matricula)})'
    is_proprio_trabalhadoreducando = perms.is_proprio_trabalhadoreducando(request, trabalhadoreducando)
    is_admin = perms.is_admin(request.user)

    is_responsavel = False
    if request.user.is_anonymous:
        is_responsavel = perms.is_responsavel(request, trabalhadoreducando)
        if not is_responsavel:
            return httprr('/', 'Você não tem permissão para acessar está página.', 'error')
    tem_permissao_para_emitir_docs_matricula = (request.user.has_perm('ppe.efetuar_matricula') or in_group(request.user, "Trabalhador Educando"))
    pode_alterar_email_trabalhadoreducando = perms.pode_alterar_email_trabalhadoreducando(request, trabalhadoreducando)
    tem_permissao_realizar_procedimentos = perms.tem_permissao_realizar_procedimentos(request.user, trabalhadoreducando)
    pode_ver_dados_trabalhadoreducando = perms.pode_ver_dados_trabalhadoreducando(request)
    pode_ver_dados_sociais = perms.pode_ver_dados_sociais(request, trabalhadoreducando)
    pode_ver_dados_academicos = (
            is_admin
            or is_responsavel
            or is_proprio_trabalhadoreducando
            and request.user.has_perm('ppe.view_dados_academicos')
    )
    pode_ver_cpf = (
            is_admin
            or pode_ver_dados_sociais
            or pode_ver_dados_academicos
    )

    # HISTÓRICO
    if request.GET.get('tab') == 'historico':

        # if 'order_by' in request.GET:
        #     ordenar_por = (
        #             request.GET['order_by'] == 'componente'
        #             and TrabalhadorEducando.ORDENAR_HISTORICO_POR_COMPONENTE
        #             or request.GET['order_by'] == 'periodo_matriz'
        #             and TrabalhadorEducando.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ
        #             or TrabalhadorEducando.ORDENAR_HISTORICO_POR_PERIODO_LETIVO
        #     )
        # else:
        #     ordenar_por = TrabalhadorEducando.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ
        # exibir_optativas = 'optativas' in request.GET
        historico = trabalhadoreducando.get_historico(False,)

    # BOLETIM
    if request.GET.get('tab') == 'boletim':
        matriculas_curso_turma = None
        matriculas_curso_turma = trabalhadoreducando.matriculacursoturma_set.all().order_by(
                        'curso_turma__curso_formacao__curso__descricao')

        if matriculas_curso_turma:
            try:
                etapa = int(request.GET.get('etapa'))
            except Exception:
                etapa = 1

            max_qtd_avaliacoes = 1
            for matricula_curso_turma in matriculas_curso_turma:
                if matricula_curso_turma.curso_turma.curso_formacao.qtd_avaliacoes > max_qtd_avaliacoes:
                    max_qtd_avaliacoes = matricula_curso_turma.curso_turma.curso_formacao.qtd_avaliacoes

    historico_setor = TrabalhadorSetorHistorico.objects.filter(trabalhador_educando=trabalhadoreducando).order_by("-data_inicio")

    return locals()

@rtr()
def detalhar_matricula_curso_turma_boletim(request, trabalhador_educando_pk, matricula_curso_turma_pk):
    if not request.user.is_authenticated and not 'matricula_aluno_como_resposavel' in request.session:
        raise PermissionDenied()

    trabalhador_educando = get_object_or_404(TrabalhadorEducando, pk=trabalhador_educando_pk)
    matricula_diario = get_object_or_404(MatriculaCursoTurma, pk=matricula_curso_turma_pk)
    curso_turma = matricula_diario.curso_turma
    title = f"Notas: {curso_turma.curso_formacao.curso.descricao_historico}"

    is_pai_trabalhador_educando = request.session.get('matricula_trabalhador_educando_como_resposavel')
    is_proprio_trabalhador_educando = trabalhador_educando.is_user(request)
    if is_pai_trabalhador_educando:
        pode_ver_dados_academicos = True
        pode_realizar_procedimentos = False
    else:
        pode_ver_dados_academicos = is_proprio_trabalhador_educando or in_group(
            request.user,
            'Coordenador(a) PPE, Tutor PPE',
        )
        pode_realizar_procedimentos =True

    if not (pode_ver_dados_academicos or pode_realizar_procedimentos or request.user.has_perm('ppe.view_trabalhadoreducando')):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    notas_avaliacoes = NotaAvaliacao.objects.filter(matricula_curso_turma=matricula_diario.pk, matricula_curso_turma__trabalhador_educando__pk=trabalhador_educando.pk).order_by(
        'item_configuracao_avaliacao__configuracao_avaliacao__etapa'
    )
    qtd_avaliacoes = curso_turma.curso_formacao.qtd_avaliacoes
    etapas = list(range(1, qtd_avaliacoes + 1))
    return locals()

@rtr()
@login_required()
def atualizar_email(request, trabalhadoreducando_pk):
    title = 'Atualização do E-mail'
    trabalhadoreducando = TrabalhadorEducando.objects.filter(pk=trabalhadoreducando_pk).first()
    if not perms.pode_alterar_email_trabalhadoreducando(request, trabalhadoreducando):
        raise PermissionDenied()
    form = AtualizarEmailTrabalhadorEducandoForm(request.POST or None, request=request, trabalhadoreducando=trabalhadoreducando)
    if form.is_valid():
        form.save()
        return httprr('..', 'E-mail atualizado com sucesso.')
    return locals()


@rtr()
@group_required('Coordenador(a) PPE')
def atualizar_dados_pessoais(request, trabalhadoreducando_pk):
    title = 'Atualização de Dados Pessoais'
    trabalhadoreducando = TrabalhadorEducando.objects.filter(pk=trabalhadoreducando_pk).first()
    pode_realizar_procedimentos = perms.tem_permissao_realizar_procedimentos(request.user, trabalhadoreducando)
    if not pode_realizar_procedimentos:
        raise PermissionDenied()
    initial = dict(
        nome_usual=trabalhadoreducando.pessoa_fisica.nome_usual,
        email_secundario=trabalhadoreducando.pessoa_fisica.email_secundario,
        logradouro=trabalhadoreducando.logradouro,
        numero=trabalhadoreducando.numero,
        complemento=trabalhadoreducando.complemento,
        bairro=trabalhadoreducando.bairro,
        cep=trabalhadoreducando.cep,
        cidade=trabalhadoreducando.cidade,
        lattes=trabalhadoreducando.pessoa_fisica.lattes,
        telefone_principal=trabalhadoreducando.telefone_principal,
        telefone_secundario=trabalhadoreducando.telefone_secundario,
        telefone_adicional_1=trabalhadoreducando.telefone_adicional_1,
        telefone_adicional_2=trabalhadoreducando.telefone_adicional_2,
    )

    form = AtualizarDadosPessoaisForm(data=request.POST or None, initial=initial, instance=trabalhadoreducando, pode_realizar_procedimentos=pode_realizar_procedimentos)
    if form.is_valid():
        form.save(trabalhadoreducando)
        return httprr('..', 'Dados Pessoais atualizados com sucesso.')
    return locals()


@rtr()
@group_required('Coordenador(a) PPE')
def alterar_trabalhador_setor_historico(request, trabalhadoreducando_pk):
    title = 'Atualização de Setor'
    trabalhadoreducando = TrabalhadorEducando.objects.filter(pk=trabalhadoreducando_pk).first()
    pode_realizar_procedimentos = perms.tem_permissao_realizar_procedimentos(request.user, trabalhadoreducando)
    if not pode_realizar_procedimentos:
        raise PermissionDenied()

    trabalhador_setor_historico = TrabalhadorSetorHistorico()
    trabalhador_setor_historico.trabalhador_educando = trabalhadoreducando

    form = AlterarTrabalhadorSetorHistoricoForm(data=request.POST or None, instance=trabalhador_setor_historico)
    if form.is_valid():
        form.save()
        return httprr('..', 'Setor atualizado com sucesso.')
    return locals()


@login_required()
@rtr()
def atualizar_meus_dados_pessoais(request, matricula, renovacao_matricula=None):
    title = 'Atualização de Dados Pessoais'
    trabalhadoreducando = get_object_or_404(TrabalhadorEducando, matricula=matricula)

    if request.user != trabalhadoreducando.pessoa_fisica.user:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    initial = dict(
        nome_usual=trabalhadoreducando.pessoa_fisica.nome_usual,
        email_secundario=trabalhadoreducando.pessoa_fisica.email_secundario,
        logradouro=trabalhadoreducando.logradouro,
        numero=trabalhadoreducando.numero,
        complemento=trabalhadoreducando.complemento,
        bairro=trabalhadoreducando.bairro,
        cep=trabalhadoreducando.cep,
        cidade=trabalhadoreducando.cidade,
        lattes=trabalhadoreducando.pessoa_fisica.lattes,
        telefone_principal=trabalhadoreducando.telefone_principal,
        telefone_secundario=trabalhadoreducando.telefone_secundario,
        utiliza_transporte_escolar_publico=trabalhadoreducando.poder_publico_responsavel_transporte is not None and (trabalhadoreducando.poder_publico_responsavel_transporte and 'Sim' or 'Não') or None,
        poder_publico_responsavel_transporte=trabalhadoreducando.poder_publico_responsavel_transporte,
        tipo_veiculo=trabalhadoreducando.tipo_veiculo,
    )
    form = AtualizarDadosPessoaisForm(data=request.POST or None, initial=initial, instance=trabalhadoreducando, pode_realizar_procedimentos=False, request=request)
    if form.is_valid():
        form.save(trabalhadoreducando)
        return httprr('..', 'Dados Pessoais atualizados com sucesso.')
    return locals()


@permission_required('ppe.change_foto')
@rtr()
def atualizar_foto(request, trabalhadoreducando_pk):
    title = 'Atualização de Foto'
    trabalhadoreducando = get_object_or_404(TrabalhadorEducando, pk=trabalhadoreducando_pk)
    if request.method == 'POST':
        form = AtualizarFotoForm(data=request.POST or None, files=request.FILES)
    else:
        form = AtualizarFotoForm()
    form.initial.update(trabalhadoreducando=trabalhadoreducando_pk)
    if form.is_valid():
        return httprr(trabalhadoreducando.get_absolute_url(), form.processar(request))
    return locals()


@rtr()
@login_required()
def efetuarmatriculatrabalhadoreducando(request):
    title = 'Adicionar Novo(a) Trabalhador(a) Educando(a)'
    initial = None
    trabalhadoreseducandos = TrabalhadorEducando.objects.none()

    cpf = request.POST.get('cpf')

    if not request.user.has_perm('ppe.efetuar_matricula'):
        return HttpResponseForbidden()

    if cpf:
        trabalhadoreseducandos = TrabalhadorEducando.objects.filter(pessoa_fisica__cpf=cpf)
        if trabalhadoreseducandos.exists():
            trabalhadoreducando = trabalhadoreseducandos.latest('id')
            initial = dict(
                # dados pessoais
                nome=trabalhadoreducando.pessoa_fisica.nome_registro,
                nome_social=trabalhadoreducando.pessoa_fisica.nome_social,
                sexo=trabalhadoreducando.pessoa_fisica.sexo,
                data_nascimento=trabalhadoreducando.pessoa_fisica.nascimento_data,
                estado_civil=trabalhadoreducando.pessoa_fisica.estado_civil,
                # dados familiares
                nome_pai=trabalhadoreducando.nome_pai,
                # estado_civil_pai=trabalhadoreducando.estado_civil_pai,
                nome_mae=trabalhadoreducando.nome_mae,
                # estado_civil_mae=trabalhadoreducando.estado_civil_mae,
                # responsavel=trabalhadoreducando.responsavel,
                parentesco_responsavel=trabalhadoreducando.parentesco_responsavel,
                # endereço
                logradouro=trabalhadoreducando.logradouro,
                numero=trabalhadoreducando.numero,
                complemento=trabalhadoreducando.complemento,
                bairro=trabalhadoreducando.bairro,
                cep=trabalhadoreducando.cep,
                cidade=trabalhadoreducando.cidade,
                # tipo_zona_residencial=trabalhadoreducando.tipo_zona_residencial,
                # informações para contado
                telefone_principal=trabalhadoreducando.telefone_principal,
                telefone_secundario=trabalhadoreducando.telefone_secundario,
                telefone_adicional_1=trabalhadoreducando.telefone_adicional_1,
                telefone_adicional_2=trabalhadoreducando.telefone_adicional_2,
                email_pessoal=trabalhadoreducando.pessoa_fisica.email_secundario,
                # outras informacoes
                tipo_sanguineo=trabalhadoreducando.tipo_sanguineo,
                nacionalidade=trabalhadoreducando.nacionalidade,
                pais_origem=trabalhadoreducando.pais_origem and trabalhadoreducando.pais_origem.id or None,
                naturalidade=trabalhadoreducando.naturalidade and trabalhadoreducando.naturalidade.id or None,
                raca=trabalhadoreducando.pessoa_fisica.raca,
                # dados escolares
                nivel_ensino_anterior=trabalhadoreducando.nivel_ensino_anterior and trabalhadoreducando.nivel_ensino_anterior.id or None,
                tipo_instituicao_origem=trabalhadoreducando.tipo_instituicao_origem,
                nome_instituicao_anterior=trabalhadoreducando.nome_instituicao_anterior,
                ano_conclusao_estudo_anterior=trabalhadoreducando.ano_conclusao_estudo_anterior and trabalhadoreducando.ano_conclusao_estudo_anterior.id or None,
                # rg
                numero_rg=trabalhadoreducando.numero_rg,
                uf_emissao_rg=trabalhadoreducando.uf_emissao_rg and trabalhadoreducando.uf_emissao_rg.id or None,
                orgao_emissao_rg=trabalhadoreducando.orgao_emissao_rg and trabalhadoreducando.orgao_emissao_rg.id or None,
                data_emissao_rg=trabalhadoreducando.data_emissao_rg,
                # titulo_eleitor
                numero_titulo_eleitor=trabalhadoreducando.numero_titulo_eleitor,
                zona_titulo_eleitor=trabalhadoreducando.zona_titulo_eleitor,
                secao=trabalhadoreducando.secao,
                data_emissao_titulo_eleitor=trabalhadoreducando.data_emissao_titulo_eleitor,
                uf_emissao_titulo_eleitor=trabalhadoreducando.uf_emissao_titulo_eleitor and trabalhadoreducando.uf_emissao_titulo_eleitor.id or None,
                # carteira de reservista
                numero_carteira_reservista=trabalhadoreducando.numero_carteira_reservista,
                regiao_carteira_reservista=trabalhadoreducando.regiao_carteira_reservista,
                serie_carteira_reservista=trabalhadoreducando.serie_carteira_reservista,
                estado_emissao_carteira_reservista=trabalhadoreducando.estado_emissao_carteira_reservista and trabalhadoreducando.estado_emissao_carteira_reservista.id or None,
                ano_carteira_reservista=trabalhadoreducando.ano_carteira_reservista,
                # certidao_civil
                # tipo_certidao=trabalhadoreducando.tipo_certidao,
                cartorio=trabalhadoreducando.cartorio,
                numero_certidao=trabalhadoreducando.numero_certidao,
                folha_certidao=trabalhadoreducando.folha_certidao,
                livro_certidao=trabalhadoreducando.livro_certidao,
                data_emissao_certidao=trabalhadoreducando.data_emissao_certidao,
                matricula_certidao=trabalhadoreducando.matricula_certidao,
                formacao_tecnica=trabalhadoreducando.formacao_tecnica,
                data_admissao = trabalhadoreducando.data_admissao,
                data_demissao = trabalhadoreducando.data_demissao
            )

    form = EfetuarMatriculaForm(request, data=request.POST or None, initial=initial, files=request.FILES or None)
    if form.is_valid():
        trabalhadoreducando = form.processar()

        return httprr(
            '/ppe/efetuarmatriculatrabalhadoreducando/',
            mark_safe('Trabalhador(a) Educando(a) adicionado(a) com sucesso.'),
        )
    return locals()


@permission_required('ppe.add_observacao')
@rtr()
def adicionar_observacao(request, trabalhadoreducando_pk):
    title = ' Adicionar Observação'
    trabalhadoreducando = TrabalhadorEducando.objects.filter(pk=trabalhadoreducando_pk).first()
    if trabalhadoreducando:
        form = ObservacaoForm(trabalhadoreducando, request.user, request.POST or None, instance=None)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação adicionada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar os dados deste trabalhadoreducando.', 'error')
    return locals()


@permission_required('ppe.change_observacao')
@rtr()
def editar_observacao(request, observacao_pk=None):
    title = ' Editar Observação'
    observacao = Observacao.objects.get(pk=observacao_pk)
    if request.user == observacao.usuario:
        form = ObservacaoForm(observacao.trabalhadoreducando, request.user, request.POST or None, instance=observacao)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação atualizada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar a observação de outro usuário.', 'error')
    return locals()

@login_required()
@rtr()
def meus_dados_academicos(request):
    obj = get_object_or_404(TrabalhadorEducando, pessoa_fisica__user__username=request.user.username)
    return HttpResponseRedirect(obj.get_absolute_url())



#Tutor
@rtr()
@group_required("Coordenador(a) PPE,Supervisor(a) Pedagógico(a)")
def tutores_ppe(request):
    title = 'Tutor PPE'


    if 'del_prefil' in request.GET:
        apoiador_pedagogico_ppe = Group.objects.get(name='Tutor PPE')
        bolsista = Bolsista.objects.get(pk=request.GET['del_prefil'])
        if apoiador_pedagogico_ppe:
            bolsista.get_vinculo().user.groups.remove(apoiador_pedagogico_ppe)
            bolsista.pessoa_fisica.user.delete() 
            bolsista.pessoa_fisica.delete()

        return httprr('HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '.', 'Perfil de Tutor PPE removido com sucesso.')

    tutores = Bolsista.objects.filter(user__groups__name='Tutor PPE')

    return locals()

@rtr()
@group_required("Coordenador(a) PPE,Supervisor(a) Pedagógico(a)")
def cadastrar_tutor_ppe(request, pessoafisica_id=None):
    title = 'Cadastrar Tutor PPE'
    """
        Pré cadastro de Chefia imediata

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
            bolsita.ativo = False
            bolsita.eh_prestador = False
            bolsita.bolsita = True
            bolsita.save()
            bolsita.enviar_email_pre_cadastro()

            tutor_ppe = Group.objects.get(name='Tutor PPE')
            if tutor_ppe:
                tutor_ppe.user_set.add(bolsita.get_vinculo().user)

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
@login_required()
@permission_required('ppe.view_estruturacurso')
def visualizar_estrutura_curso(request, estrutura_curso_pk):
    title = 'Estrutura de Curso'
    obj = get_object_or_404(EstruturaCurso, pk=estrutura_curso_pk)
    if 'replicar' in request.GET:
        obj.pk = None
        obj.descricao = f'{obj.descricao} [REPLICADA]'
        obj.save()
        return httprr(f'/admin/ppe/estruturacurso/{obj.pk}/', 'Estrutura replicada com sucesso. Edite a descrição e os demais dados necessários.')
    # formacoes_ativas = obj.get_formacoes_ppe_ativas()
    # formacoes_inativas = obj.get_formacoes_ppe_inativas()

    return locals()

@permission_required('ppe.view_curso')
@rtr()
def curso(request, pk):
    obj = get_object_or_404(Curso, pk=pk)
    title = str(obj)
    pode_visualizar_estatistica = in_group(request.user, 'Coordenador(a) PPE, Supervisor(a) Pedagógico(a)')
    #pode_definir_coordenador_estagio_docente = in_group(request.user, 'Coordenador(a) PPE, Supervisor(a) Pedagógico(a)')
    tab = request.GET.get('tab', '')
    # if tab == 'coordenacao':
    #     logs = (
    #         Log.objects.filter(modelo='CursoResidencia', ref=pk, registrodiferenca__campo__in=['Coordenador', ])
    #         .order_by('-pk')
    #         .values_list('dt', 'registrodiferenca__valor_anterior', 'registrodiferenca__valor_atual', 'registrodiferenca__campo')
    #     )
    return locals()


@permission_required('ppe.view_formacaoppe')
@rtr()
def formacaoppe(request, pk):
    obj = get_object_or_404(FormacaoPPE, pk=pk)
    pode_editar_formacaoppe = request.user.has_perm('ppe.change_formacappe')
    cursos = obj.cursoformacaoppe_set.select_related('curso')
    title = str(obj)

    return locals()


@permission_required('ppe.add_formacaoppe')
@rtr()
def replicar_formacaoppe(request, formacaoppe_pk):
    title = 'Replicação de Formação PPE'
    obj = get_object_or_404(FormacaoPPE, pk=formacaoppe_pk)
    form = ReplicacaFormacaoPPEForm(obj, data=request.POST or None)
    if request.POST and form.is_valid():
        try:
            resultado = form.processar()
            return httprr(f'/ppe/formacaoppe/{resultado.id}/', 'Formação PPE replicada com sucesso.')
        except ValidationError as e:
            return httprr('..', f'Não foi possível replicar a Formação PPE: {e.messages[0]}', 'error')
    return locals()


@permission_required('ppe.add_cursoformacaoppe')
@rtr()
def vincular_curso_ppe(request, formacaoppe_pk, curso_pk=None):
    title = '{} Curso da Formação PPE '.format(curso_pk and 'Editar' or 'Vincular')
    formacao_ppe = get_object_or_404(FormacaoPPE, pk=formacaoppe_pk)

    if not formacao_ppe.pode_ser_editada(request.user):
        return httprr(f'/ppe/formacaoppe/{formacao_ppe.pk}/?tab=cursos', 'A formação PPE não pode ser editada.', 'error')

    if curso_pk:
        mc = get_object_or_404(CursoFormacaoPPE.objects, curso__pk=curso_pk, formacao_ppe=formacao_ppe)

    form = CursoFormacaoPPEForm(formacao_ppe, data=request.POST or None, instance=curso_pk and mc or None)
    if curso_pk:
        form.SUBMIT_LABEL = 'Salvar Vínculo'
    else:
        form.SUBMIT_LABEL = 'Vincular Curso'
        form.EXTRA_BUTTONS = [dict(name='continuar', value='Vincular Curso e continuar vinculando')]

    if form.is_valid():
        form.save()
        redirect = '..'
        if 'continuar' in request.POST:
            redirect = '.'
        if not curso_pk:
            return httprr(redirect, 'Curso da Formação PPE adicionado com sucesso.')
        else:
            return httprr(f'/ppe/formacaoppe/{formacao_ppe.pk}/?tab=componentes', 'Curso da Formação PPE atualizado com sucesso.')
    return locals()

@permission_required('ppe.gerar_turmas')
@rtr()
def gerar_turmas(request):
    title = 'Gerar Turmas'
    form = GerarTurmasPPEForm(request, data=request.GET or None, initial=dict())
    if form.is_valid():
        form.processar(commit=True)
        ids = []
        for turma in form.turmas:
            ids.append(str(turma.id))
        return httprr('/admin/ppe/turma/'.format(','.join(ids)), 'Turmas geradas com sucesso.')
    return locals()

@permission_required('ppe.view_turma')
@rtr()
def turma(request, pk):
    obj = get_object_or_404(Turma.objects, pk=pk)
    title = f'Turma {obj.codigo}'
    is_coordenador = in_group(request.user, 'Coordenador(a) PPE')
    pode_realizar_procedimentos = True
    cursos_turma = obj.cursoturma_set.order_by('data_inicio_etapa_1')

    trabalhadores_educando = obj.trabalhadoreducando_set.all()

    qtd_trabalhadores_educando_ativos = obj.trabalhadoreducando_set.all().count()




    # trabalhador_educandos = obj.get_trabalhador_educandos_matriculados()
    # trabalhador_educandos_diarios = obj.get_trabalhador_educandos_matriculados_diarios()
    # diarios_pendentes = obj.diarios_pendentes()
    # situacoes_inativas = (
    #     SituacaoMatriculaPeriodo.CANCELADA,
    #     SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO,
    #     SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO,
    #     SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE,
    #     SituacaoMatriculaPeriodo.TRANCADA,
    #     SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE,
    #     SituacaoMatriculaPeriodo.TRANSF_CURSO,
    # )
    # qtd_trabalhador_educandos_ativos = trabalhador_educandos.exclude(situacao__in=situacoes_inativas).count()
    # qtd_trabalhador_educandos_ativos += trabalhador_educandos_diarios.exclude(situacao__in=situacoes_inativas).count()

    ids = request.GET.get('id_te')
    if ids:
        if not pode_realizar_procedimentos:
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
        te_turma = TrabalhadorEducando.objects.filter(id__in=ids.split('_'), turma=obj)
        obj.remover_trabalhadores_educandos(te_turma, request.user)

        return httprr(f'/ppe/turma/{obj.pk}/?tab=dados_trabalhador_educandos', 'Trabalhadores(s) removido(s) com sucesso.')

    return locals()

@permission_required('ppe.view_turma')
@rtr()
def calendario_turma(request, pk):
    obj = get_object_or_404(Turma.objects, pk=pk)
    title = f'Turma {obj.codigo}'

    calendario = CalendarioPlus()
    calendario.mostrar_mes_e_ano = True
    calendario.envolve_mes_em_um_box = True
    calendario.destacar_hoje = True
    css = ['success','info','alert','error']
    hoje = datetime.date.today()
    min_date =hoje
    max_date =hoje
    for curso in obj.cursoturma_set.order_by('data_inicio_etapa_1'):

        if curso.data_inicio_etapa_1 and curso.data_fim_etapa_1:
                data_inicio = curso.data_inicio_etapa_1
                data_final = curso.data_fim_etapa_1

                if data_inicio < min_date:
                    min_date = data_inicio

                if data_final > max_date:
                    max_date = data_inicio

                descricao = '{}'.format(curso)
                calendario.adicionar_evento_calendario(
                    data_inicio=data_inicio,
                    data_fim=data_final,
                    descricao=descricao,
                    css_class=random.choice(css),
                    title=f'Calendario {title}',
                    url= None,
        )

        calendario_periodo = calendario.formato_periodo(min_date.month, min_date.year, max_date.month, max_date.year,True)

    return locals()


@permission_required('ppe.add_tutorturma')
@rtr()
def adicionar_tutor_turma(request, turma_pk, tutorturma_pk=None):
    title = 'Adicionar Tutor'
    turma = get_object_or_404(Turma.objects, pk=turma_pk)

    pode_realizar_procedimentos = True

    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    tutor_turma = None
    if tutorturma_pk:
        tutor_turma = get_object_or_404(TutorTurma, pk=tutorturma_pk)
    form = TutorTurmaForm(turma, data=request.POST or None, instance=tutorturma_pk and tutor_turma or None, request=request)
    if form.is_valid():
        form.save()
        if tutor_turma:
            emails = [tutor_turma.tutor.pessoa_fisica.email]
            mensagem = """
            Caro(a) Tutor(a),

            Informamos que houve uma alteração do seu vínculo na turma {}.
            """.format(
                turma,
            )

            send_mail(
                f'[SUAP] Alteração de Vínculo - Turma {turma}',
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                emails,
                fail_silently=True
            )
        return httprr('..', 'Tutor adicionado/atualizado com sucesso.')
    return locals()

@permission_required('ppe.add_apoiadorturma')
@rtr()
def adicionar_apoiador_turma(request, turma_pk, apoiadorturma_pk=None):
    title = 'Adicionar Apoiador'
    turma = get_object_or_404(Turma.objects, pk=turma_pk)

    pode_realizar_procedimentos = True

    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    apoiador_turma = None
    if apoiadorturma_pk:
        apoiador_turma = get_object_or_404(ApoiadorTurma, pk=apoiadorturma_pk)
    form = ApoiadorTurmaForm(turma, data=request.POST or None, instance=apoiadorturma_pk and apoiador_turma or None, request=request)
    if form.is_valid():
        form.save()
        if apoiador_turma:
            emails = [apoiador_turma.apoiador.pessoa_fisica.email]
            mensagem = """
            Caro(a) Apoiador(a),

            Informamos que houve uma alteração do seu vínculo na turma {}.
            """.format(
                turma,
            )

            send_mail(
                f'[SUAP] Alteração de Vínculo - Turma {turma}',
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                emails,
                fail_silently=True
            )
        return httprr('..', 'Apoiador adicionado/atualizado com sucesso.')
    return locals()


@permission_required('ppe.add_turma')
@rtr()
def alterar_data_curso_turma(request, curso_turma_pk):
    title = 'Alterar data'
    curso_turma = get_object_or_404(CursoTurma.objects, pk=curso_turma_pk)

    pode_realizar_procedimentos = True

    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = AlterarDataCursoTurmaForm(curso_turma, data=request.POST or None, request=request)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Data alterada com sucesso.')
    return locals()

@rtr()
def anamnese(request, trabalhador_educando_id=None):

    title = "Anamnese do Trabalhador Educando"

    trabalhador_educando = None

    if trabalhador_educando_id:
        trabalhador_educando = get_object_or_404(TrabalhadorEducando, pk=trabalhador_educando_id)
    else:
        trabalhador_educando = get_object_or_404(TrabalhadorEducando, pessoa_fisica_user_username=request.user.username)

    # if request.user.is_user and trabalhador_educando and request.user.get_relacionamento() != trabalhador_educando:
    #     raise PermissionDenied()

    form = AnamneseForm(trabalhador_educando, data=request.POST or None)

    if Anamnese.objects.filter(trabalhador_educando=trabalhador_educando).exists():
        anamnese = Anamnese.objects.get(trabalhador_educando=trabalhador_educando)
        title = "Editar Anamnese"
        form = AnamneseForm(trabalhador_educando, instance=anamnese, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            anamnese = form.save(False)
            anamnese.trabalhador_educando = trabalhador_educando

            anamnese.save()
            form.save_m2m()
            url = trabalhador_educando.get_absolute_url()
            return httprr(url, 'Anamnese realizada com sucesso.')
    return locals()


@login_required()
def matricular_trabalhador_educando_turma(request, trabalhador_educando_pk):
    title = 'Matricular em Turma'
    trabalhador_educando = get_object_or_404(TrabalhadorEducando, pk=trabalhador_educando_pk)

    pode_realizar_procedimentos = True
    if (
        not pode_realizar_procedimentos
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if trabalhador_educando.turma:
        return httprr('..', 'O Trabalhador Educando selecionado já possui uma turma.', 'error')

    form = MatricularTrabalhadorEducandoTurmaForm(trabalhador_educando, data=request.POST or None)

    if form.is_valid():
        form.processar()
        return httprr('..', 'O Trabalhador Educando foi matriculado na turma com sucesso.')

    return locals()

@permission_required('ppe.change_turma')
@rtr()
def adicionar_trabalhadores_educando_turma(request, pk):
    turma = get_object_or_404(Turma.objects, pk=pk)
    title = 'Adicionar Trabalhador Educando à Turma'
    if 'trabalhadores_educando' in request.POST:
        trabalhadores_educando = TrabalhadorEducando.objects.filter(id__in=request.POST.getlist('trabalhadores_educando'))
        turma.matricular_trabalhadores_educando(trabalhadores_educando)
        return httprr(f'/ppe/turma/{turma.pk}/?tab=dados_trabalhadores_educando', 'Trabalhadores educando(s) matriculado(s) com sucesso.')

    trabalhadores_educando = turma.get_trabalhadores_educando_apto_matricula()

    return locals()

@rtr()
@permission_required('ppe.reabrir_cursoturma')
def matricular_trabalhador_educando_avulso_curso_turma(request, curso_turma_pk):
    title = 'Matricular Aluno Avulso em Diário'

    curso_turma = get_object_or_404(CursoTurma, pk=curso_turma_pk)
    form = MatricularTrabalhadorEducandoAvulsoCursoTurmaoForm(curso_turma, request.POST or None, request=request)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Aluno matriculado com sucesso.')

    return locals()

@group_required('Coordenador(a) PPE,Tutor PPE')
@rtr()
@login_required()
def configuracao_avaliacao(request, pk):
    obj = get_object_or_404(ConfiguracaoAvaliacao, pk=pk)
    title = obj.__str__()
    return locals()


permission_required('ppe.cursoturma')
@rtr()
def curso_turma(request, pk):
    NOTA_DECIMAL = settings.NOTA_DECIMAL
    CASA_DECIMAL = settings.CASA_DECIMAL
    MULTIPLICADOR_DECIMAL = NOTA_DECIMAL and CASA_DECIMAL == 1 and 10 or 100

    manager = CursoTurma.objects
    obj = get_object_or_404(manager, pk=pk)
    qtd_avaliacoes = obj.curso_formacao.qtd_avaliacoes

    pode_realizar_procedimentos = True
    acesso_total = pode_realizar_procedimentos

    title = f'Diário do Curso ({obj.pk}) - {obj.curso_formacao.curso.codigo}'
    pode_manipular_etapa_1 = obj.em_posse_do_registro(1) and acesso_total
    pode_manipular_etapa_5 = obj.em_posse_do_registro(5) and acesso_total
    etapa = 5

    # quantidade_vagas_estourada = obj.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).count() > obj.quantidade_vagas
    matriculas_diario_por_polo = obj.get_matriculas_diario_por_polo()

    if 'verificar_moodle' in request.GET and obj.nome_breve_curso_moodle:
        try:
            dados_curso = moodle.verificar_curso(obj.nome_breve_curso_moodle)
            obj.integracao_com_moodle = True
            obj.url_moodle = dados_curso['url']
            obj.save()
            return httprr('.', f'Curso encontrado.')
        except BaseException as e:
            return httprr('.', f'Curso com nome curso {obj.nome_breve_curso_moodle} não encontrado. Favor criar o curso no moodle', tag='error')


    if 'sincronizar_moodle' in request.GET and obj.integracao_com_moodle:
        try:
            url = moodle.enviar_dados_curso(obj)
            return httprr('.', f'Dados enviados com sucesso!')
        except BaseException as e:
            return httprr('.', f'Problemas ao enviar os dados para o Moodle: {e}', tag='error')

    if 'sincronizar_notas_moodle' in request.GET and obj.integracao_com_moodle:
        try:
            url = moodle.baixar_notas(obj)
            return httprr('.', f'Notas sincronizadas com sucesso!')
        except BaseException as e:
            return httprr('.', f'Problemas ao sincronizar notas  do Moodle: {e}', tag='error')

    if 'abrir' in request.GET:
        obj.situacao = CursoTurma.SITUACAO_ABERTO
        obj.save()
        return httprr('.', 'Diário do curso aberto com sucesso.')

    if 'fechar' in request.GET:
        obj.situacao = CursoTurma.SITUACAO_FECHADO
        obj.save()
        return httprr('.', 'Diário do curso fechado com sucesso.')

    # if request.GET.get('xls'):
    #     response = HttpResponse(content_type='application/ms-excel')
    #     response['Content-Disposition'] = f'attachment; filename=diario_{pk}.xls'
    #
    #     wb = xlwt.Workbook(encoding='utf-8')
    #     sheet1 = wb.add_sheet('Dados Gerais')
    #     sheet2 = wb.add_sheet('Registros de Aulas')
    #
    #     rows_agrupada = []
    #     cabecalho = ['#', 'Matrícula', 'Nome', 'T. Faltas', '%Freq', 'Situação']
    #     for avaliacao in range(1, obj.componente_curricular.qtd_avaliacoes + 1):
    #         cabecalho.append(f'Nota Etapa {avaliacao}')
    #         cabecalho.append(f'Falta Etapa {avaliacao}')
    #     cabecalho += ['MD', 'Nota Etapa Final', 'MFD/Conceito']
    #     rows_agrupada.append(cabecalho)
    #     count = 0
    #
    #     for matricula_diario in obj.matriculadiario_set.all():
    #         count += 1
    #         row = [
    #             format_(count),
    #             format_(matricula_diario.matricula_periodo.trabalhador_educando.matricula),
    #             format_(normalizar_nome_proprio(matricula_diario.matricula_periodo.trabalhador_educando.get_nome_social_composto())),
    #             format_(matricula_diario.get_numero_faltas()),
    #             format_(matricula_diario.get_percentual_carga_horaria_frequentada()),
    #             format_(matricula_diario.get_situacao_diario()['rotulo']),
    #         ]
    #         if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 0:
    #             row.append(format_(matricula_diario.get_nota_1_boletim()))
    #             row.append(format_(matricula_diario.get_numero_faltas_primeira_etapa()))
    #         if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 1:
    #             row.append(format_(matricula_diario.get_nota_2_boletim()))
    #             row.append(format_(matricula_diario.get_numero_faltas_segunda_etapa()))
    #         if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 2:
    #             row.append(format_(matricula_diario.get_nota_3_boletim()))
    #             row.append(format_(matricula_diario.get_numero_faltas_terceira_etapa()))
    #             row.append(format_(matricula_diario.get_nota_4_boletim()))
    #             row.append(format_(matricula_diario.get_numero_faltas_quarta_etapa()))
    #         if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 0:
    #             row.append(format_(matricula_diario.get_media_disciplina_boletim()))
    #             row.append(format_(matricula_diario.get_nota_final_boletim()))
    #             row.append(format_(matricula_diario.get_media_final_disciplina_boletim()))
    #         rows_agrupada.append(row)
    #
    #     for row_idx, row in enumerate(rows_agrupada):
    #         row = [i for i in row]
    #         for col_idx, col in enumerate(row):
    #             sheet1.write(row_idx, col_idx, label=col)
    #
    #     rows_agrupada = [['#', 'Etapa', 'Qtd.', 'Data', 'Professor', 'Conteúdo']]
    #     count = 0
    #
    #     for aula in obj.get_aulas():
    #         count += 1
    #         row = [format_(count), format_(aula.etapa), format_(aula.quantidade), format_(aula.data), format_(str(aula.professor_diario.professor)), format_(aula.conteudo)]
    #         rows_agrupada.append(row)
    #
    #     for row_idx, row in enumerate(rows_agrupada):
    #         row = [i for i in row]
    #         for col_idx, col in enumerate(row):
    #             sheet2.write(row_idx, col_idx, label=col)
    #
    #     wb.save(response)
    #     return response
    #
    # if request.method == 'POST' and request.user.has_perm('edu.add_professordiario'):
    #     if 'lancamento_nota' in request.POST:
    #         if running_tests():
    #             try:
    #                 obj.processar_notas(request.POST)
    #                 return httprr('.', 'Notas registradas com sucesso.')
    #             except Exception as e:
    #                 return httprr('..', str(e), 'error', anchor='etapa')
    #


    tab = request.GET.get('tab', '')

    #
    # if tab == 'estatisticas':
    #     estatisticas = get_estatisticas_diario(obj)
    #
    exibir_todos_alunos = not obj.matriculacursoturma_set.filter(situacao=MatriculaCursoTurma.SITUACAO_CURSANDO).exists()
    return locals()

@permission_required('ppe.lancar_nota_curso_turma')
@rtr()
def registrar_nota_ajax(request, id_nota_avaliacao, nota=None):
    nota_avaliacao = get_object_or_404(NotaAvaliacao, pk=id_nota_avaliacao)
    etapa = nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa
    curso_turma = nota_avaliacao.matricula_curso_turma.curso_turma
    pode_registrar_nota = False
    # se a situação do aluno no diário for "Cursando"
    if nota_avaliacao.matricula_curso_turma.is_cursando():
        qs_tutor_curso_turma= curso_turma.turma.tutorturma_set.filter(tutor__vinculo__user=request.user)

        if curso_turma.em_posse_do_registro(etapa):
            pode_registrar_nota = True

        elif qs_tutor_curso_turma.exists() and not curso_turma.em_posse_do_registro(etapa):
            unico_professor = curso_turma.turma.tutorturma_set.filter(ativo=True).count() == 1
            if unico_professor:
                pode_registrar_nota = True
            else:
                data_atual = datetime.date.today()
                etapa_string = etapa == 5 and 'final' or str(etapa)
                professor_diario = qs_tutor_curso_turma[0]
                data_inicio_etapa = getattr(professor_diario, f'data_inicio_etapa_{etapa_string}', None)
                data_fim_etapa = getattr(professor_diario, f'data_fim_etapa_{etapa_string}', None)
                if data_inicio_etapa and data_fim_etapa and data_inicio_etapa <= data_atual <= data_fim_etapa:
                    pode_registrar_nota = True

    if pode_registrar_nota:
        nota_avaliacao.nota = None if nota is None else float(nota)
        nota_avaliacao.save()
        nota_avaliacao.matricula_curso_turma.registrar_nota_etapa(nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa)
        nota_avaliacao.matricula_curso_turma.registrar_situacao_se_aprovado()
        attr_nota = 'nota_{}'.format(int(etapa) == 5 and 'final' or etapa)
        attr_etapa = f'posse_etapa_{etapa}'
        nota_etapa = getattrr(nota_avaliacao.matricula_curso_turma, attr_nota)
        posse_etapa = getattrr(nota_avaliacao.matricula_curso_turma.curso_turma, attr_etapa)
        dict_resposta = {
            'etapa': '-' if nota_etapa is None else nota_etapa,
            'media': nota_avaliacao.matricula_curso_turma.get_media_disciplina() or '-',
            'media_final': nota_avaliacao.matricula_curso_turma.get_media_final_disciplina() or '-',
            'situacao': nota_avaliacao.matricula_curso_turma.get_situacao_nota(),
            'posse': posse_etapa,
            'em_prova_final': nota_avaliacao.matricula_curso_turma.is_em_prova_final(),
            'prova_final_invalida': not nota_avaliacao.matricula_curso_turma.is_em_prova_final() and nota_avaliacao.matricula_curso_turma.nota_final,
        }
        return JsonResponse(dict_resposta)

@permission_required('ppe.change_cursoturma')
@rtr()
def transferir_posse_curso_turma(request, curso_turma_pk, etapa, destino):
    curso_turma = get_object_or_404(CursoTurma.objects, pk=curso_turma_pk)

    pode_realizar_procedimentos = True
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    destino = int(destino)
    etapa = int(etapa)
    if etapa == 1:
        curso_turma.posse_etapa_1 = destino
    elif etapa == 5:
        curso_turma.posse_etapa_5 = destino
    curso_turma.save()
    for matricula_diario in curso_turma.matriculacursoturma_set.all():
        matricula_diario.registrar_nota_etapa(etapa)
    return httprr(f'/ppe/curso_turma/{curso_turma.pk:d}', 'Posse transferida com sucesso.')


@permission_required('ppe.view_log')
@rtr('logs_ppe.html')
def log_curso_turma(request, pk):
    qs_log = Log.objects.filter(ref_curso_turma=pk) | Log.objects.filter(ref=pk, modelo='CursoTurma')
    logs = qs_log.distinct().order_by('-id')
    title = f'Log do diário do curso {pk}'
    return locals()

@rtr()
@permission_required('ppe.view_log')
def log(request, pk):
    title = f'Visualização do Log #{pk}'
    obj = get_object_or_404(Log, pk=pk)
    tipo = str(Log.TIPO_CHOICES[obj.tipo - 1][1])
    diff = RegistroDiferenca.objects.filter(log=obj)
    cls = apps.get_model(obj.app, obj.modelo)
    instancia = None
    qs = cls.objects.filter(pk=obj.ref)
    if qs.exists():
        instancia = qs[0]
        metadata = utils.metadata(instancia)
    return locals()

@rtr()
@login_required()
def minhas_turmas(request, turmas=None):
    if turmas:
        try:
            tutor_turmas = TutorTurma.objects.filter(tutor__vinculo__user=request.user,  ativo=True, turma__id__in=turmas.split('_'))
        except Exception:
            return httprr('..', 'Turmas dos cursos inválidos.', 'error')
        title = f'Minhas Turmas Pendentes ({len(tutor_turmas)})'
    else:
        tutor_turmas = TutorTurma.objects.filter(tutor__vinculo__user=request.user, ativo=True)

        title = f'Minhas Turmas  Diários ({len(tutor_turmas)})'
    return locals()

@rtr()
@login_required()
def meu_curso_turma(request, curso_turma_pk, etapa=0, polo_pk=None):
    NOTA_DECIMAL = settings.NOTA_DECIMAL
    CASA_DECIMAL = settings.CASA_DECIMAL
    MULTIPLICADOR_DECIMAL = NOTA_DECIMAL and CASA_DECIMAL == 1 and 10 or 100
    obj = get_object_or_404(CursoTurma.objects, pk=curso_turma_pk)

    # if 'moodle' in request.GET and obj.integracao_com_moodle:
    #     try:
    #         url = moodle.sincronizar(obj)
    #         obj.url_moodle = url
    #         obj.save()
    #         return httprr('.', f'Dados enviados com sucesso! A URL de acesso para o ambiente virtual é: {url}')
    #     except BaseException as e:
    #         return httprr('.', f'Problemas ao enviar os dados para o Moodle: {e}', tag='error')

    etapa = int(etapa)
    if etapa == 0:
        return httprr(f'/ppe/meu_curso_turma/{obj.pk}/{obj.get_num_etapa_posse_tutor()}/')
    if etapa > 5 or etapa < 1:
        return httprr('/ppe/meu_curso_turma/', 'Escolha uma Etapa Válida', 'error')
    etapa_str = obj.get_label_etapa(etapa)
    descricao_etapa = f'Etapa {etapa_str}'
    title = f'{str(obj)} - {descricao_etapa}'
    tab = request.GET.get('tab', '')

    qtd_avaliacoes = obj.curso_formacao.qtd_avaliacoes
    tutor_turma = get_object_or_404(obj.turma.tutorturma_set, tutor__vinculo__user=request.user)
    if not tutor_turma.ativo:
        return httprr('/ppe/meus_cursos_turma/', f'Vínculo com o diário inativo', 'error')

    data_atual = datetime.date.today()

    q = request.GET.get('q')

    em_posse_do_registro = obj.em_posse_do_registro(etapa)
    etapas_anteriores_entegues = obj.etapas_anteriores_entegues(etapa)

    qtd_tutores = obj.turma.tutorturma_set.filter(ativo=True).count()

    pode_manipular_etapa_1 = (
        etapa == 1
        and tutor_turma.ativo
        and not em_posse_do_registro
        and (
                qtd_tutores == 1
                or (
                tutor_turma.data_inicio_etapa_1
                and tutor_turma.data_fim_etapa_1
                and data_atual >= tutor_turma.data_inicio_etapa_1
                and data_atual <= tutor_turma.data_fim_etapa_1
            )
        )
    )

    pode_manipular_etapa_5 = (
        etapa == 5
        and tutor_turma.ativo
        and not em_posse_do_registro
        and (
                qtd_tutores == 1
                or (
                tutor_turma.data_inicio_etapa_final
                and tutor_turma.data_fim_etapa_final
                and data_atual >= tutor_turma.data_inicio_etapa_final
                and data_atual <= tutor_turma.data_fim_etapa_final
            )
        )
    )

    configuracao_avaliacao_selecionada = getattr(obj, f'configuracao_avaliacao_{etapa}')()

    if etapa == 1:
        inicio_etapa = obj.data_inicio_etapa_1
        fim_etapa = obj.data_fim_etapa_1
        pode_manipular_etapa = pode_manipular_etapa_1

    if etapa == 5:
        inicio_etapa = obj.data_inicio_prova_final
        fim_etapa = obj.data_fim_prova_final
        pode_manipular_etapa = pode_manipular_etapa_5

    # solicitacao_prorrogacao_pendente = SolicitacaoProrrogacaoEtapa.locals.pendentes().filter(professor_diario=professor_diario, etapa=etapa).exists()

    # exibição das etapas
    etapas = dict()
    for numero_etapa in obj.get_lista_etapas():
        dados_etapa = obj.get_etapas().get(numero_etapa)

        dados_etapa.update(inicio_etapa=getattr(obj, 'data_inicio_etapa_{}'.format(dados_etapa['numero_etapa_exibicao'])))
        dados_etapa.update(fim_etapa=getattr(obj, 'data_fim_etapa_{}'.format(dados_etapa['numero_etapa_exibicao'])))
        dados_etapa.update(inicio_posse=getattr(obj, f'data_inicio_etapa_{numero_etapa}'))
        dados_etapa.update(fim_posse=getattr(obj, f'data_fim_etapa_{numero_etapa}'))
        etapas.update({numero_etapa: dados_etapa})

    dados_etapa_5 = obj.get_etapas().get(5)
    dados_etapa_5.update(inicio_etapa=obj.get_inicio_etapa_final())
    dados_etapa_5.update(fim_etapa=obj.get_fim_etapa_final())
    dados_etapa_5.update(inicio_posse=obj.data_inicio_prova_final)
    dados_etapa_5.update(fim_posse=obj.data_fim_prova_final)
    etapas.update({'Final': dados_etapa_5})

    acesso_total = True

    if not tutor_turma and not in_group(
        request.user, 'Coordenador PPE'
    ):
        raise PermissionDenied()

    matriculas_diario_por_polo = obj.get_matriculas_diario_por_polo()

    if request.method == 'POST':

        if 'lancamento_nota' in request.POST:
            url = f'/ppe/meu_curso_turma/{obj.pk}/{etapa}/?tab=notas'
            try:
                if running_tests():
                    obj.processar_notas(request.POST)
                return httprr(url, 'Notas registradas com sucesso.', anchor='etapa')
            except Exception as e:
                return httprr(url, str(e), 'error', anchor='etapa')



    # possui_solicitacao_pendente = SolicitacaoRelancamentoEtapa.objects.filter(etapa=etapa, professor_diario=professor_diario, data_avaliacao__isnull=True).exists()
    # possui_solicitacao_prorrogacao_pendente = SolicitacaoProrrogacaoEtapa.objects.filter(etapa=etapa, professor_diario=professor_diario, data_avaliacao__isnull=True).exists()

    exibir_todos_alunos = not obj.matriculacursoturma_set.filter(situacao=MatriculaCursoTurma.SITUACAO_CURSANDO).exists()
    return locals()


@rtr()
@permission_required('ppe.view_solicitacaousuario')
def solicitacaousuario(request, pk):
    obj = get_object_or_404(SolicitacaoUsuario.locals, pk=pk)

    filho_verbose_name = obj.sub_instance_title()
    filho = obj.sub_instance()
    title = f'{filho_verbose_name} {pk}'

    obj = get_object_or_404(filho.__class__.locals, pk=pk)

    eh_atendimentopsicossocial= filho_verbose_name == 'Solicitação de Atendimento pelo Núcleo de Atenção Psicossocial'
    eh_continuidadeaperfeicoamentoprofissional = filho_verbose_name == 'Solicitação de continuidade no Aperfeiçoamento Profissional'
    eh_ampliacaoprazocurso = filho_verbose_name == 'Solicitação de ampliação de prazo para execução de curso'
    eh_realocacao= filho_verbose_name == 'Solicitação de realocação'
    eh_visitatecnicaunidade = filho_verbose_name == 'Solicitação de visita técnica na unidade'

    trabalhadoreducando = TrabalhadorEducando.objects.filter(pessoa_fisica__user=obj.solicitante)
    if trabalhadoreducando:
        trabalhador_educando = trabalhadoreducando[0]
    atender = request.GET.get('atender', False)
    if request.user.has_perm('ppe.change_solicitacaousuario'):
        # if 'avisar_coordenador' in request.GET and eh_atividade_complementar:
        #     if filho.enviar_email_coordenador():
        #         filho.atender(request.user)
        #         return httprr('..', 'Email enviado com sucesso.')
        #     else:
        #         return httprr('..', 'Falha ao tentar enviar email.')
        if atender:
            filho.atender(request.user)
            return httprr('..', 'Solicitação deferida com sucesso.')
    return locals()


@rtr()
@login_required()
def solicitar_atendimentopsicossocial(request):
    title = 'Solicitação de Atendimento pelo Núcleo de Atenção Psicossocial'
    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoAtendimentoPsicossocialForm(data=request.POST or None, trabalhadoreducando=trabalhadoreducando)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()
@rtr()
@login_required()
def solicitar_continuidadeaperfeicoamentoprofissional(request):
    title = 'Solicitação de continuidade no Aperfeiçoamento Profissional'
    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoContinuidadeAperfeicoamentoProfissionalForm(data=request.POST or None, trabalhadoreducando=trabalhadoreducando)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()


@rtr()
@login_required()
def solicitar_ampliacaoprazocurso(request):
    title = 'Solicitação de ampliação de prazo para execução de curso'
    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoAmpliacaoPrazoCursoForm(data=request.POST or None, trabalhadoreducando=trabalhadoreducando)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()


@rtr()
@login_required()
def solicitar_realocacao(request):
    title = 'Solicitação de Realocação'
    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoRealocacaoForm(data=request.POST or None, trabalhadoreducando=trabalhadoreducando)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()


@rtr()
@login_required()
def solicitar_visitatecnicaunidade(request):
    title = 'Solicitação de visita técnica na unidade'
    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoVisitaTecnicaUnidadeForm(data=request.POST or None, trabalhadoreducando=trabalhadoreducando)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()

@rtr()
@permission_required('ppe.change_solicitacaousuario')
def atender_solicitacaousuario(request, pks):
    title = 'Atender Solicitação'
    solicitacoes = SolicitacaoUsuario.objects.filter(pk__in=pks.split('_'))
    for solicitacao in solicitacoes:
        solicitacao.sub_instance().atender(request.user, trabalhadoreducando=solicitacao.solicitante.get_relacionamento())
    return httprr('..', 'Solicitações deferidas com sucesso.')
    return locals()

@rtr()
@permission_required('ppe.change_solicitacaousuario')
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
@login_required()
def solicitar_desligamento(request):
    title = 'Solicitação de Desligamentos'
    if request.user.eh_trabalhadoreducando:
        trabalhadoreducando = request.user.get_relacionamento()
    else:
        return httprr('..', f'Você não tem permissão para realizar uma solicitação.', 'error')

    form = SolicitacaoDesligamentosForm(data=request.POST or None, trabalhadoreducando=trabalhadoreducando)
    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.',)
    return locals()

@transaction.atomic
@permission_required('ppe.view_cursoturma')
@rtr()
def registrar_chamada(request, curso_turma_pk, etapa=0, matricula_diario_pk=0):
    curso_turma = get_object_or_404(CursoTurma.objects, pk=curso_turma_pk)
    title = 'Registro de Frequência'

    is_proprio_professor = curso_turma.turma.tutorturma_set.filter(tutor__vinculo__user=request.user).exists()

    pode_realizar_procedimentos = True
    if not pode_realizar_procedimentos and not is_proprio_professor and not in_group(request.user, 'Coordenador(a) PPE'):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not curso_turma.turma.tutorturma_set.exists():
        return httprr(f'/ppe/curso_turma/{curso_turma.pk}/', 'Não é possível registrar as aulas pois o tutor do curso ainda não foi definido.', 'error')

    if is_proprio_professor:
        acesso_total = True
    else:
        acesso_total = request.user.groups.filter(name='Coordenador(a) PPE').exists()
    data_atual = datetime.date.today()
    aulas = curso_turma.get_aulas().all()
    etapa = int(etapa)
    if not etapa or etapa == 1:
        aulas = curso_turma.get_aulas_etapa_1().all()

    pode_manipular_etapa = curso_turma.em_posse_do_registro(etapa) or is_proprio_professor

    form = AulaForm(curso_turma, etapa, request=request)
    if request.POST:
        return httprr('..', 'Faltas registradas com sucesso.')

    boxes_matriculas = []
    for matriculas in curso_turma.get_matriculas_diario_por_polo():
        if matricula_diario_pk:
            matriculas = matriculas.filter(id=matricula_diario_pk)
        for matricula_diario in matriculas:
            matricula_diario.set_faltas(aulas)
        boxes_matriculas.append(matriculas)

    return locals()


@rtr()
@permission_required('ppe.gerar_relatorio')
def relatorio_faltas(request):
    title = 'Relatório de Faltas'
    campus = None

    form = RelatorioFaltasForm(campus, request.GET or None)
    if form.is_valid():
        turma = form.cleaned_data['turma']
        curso_turma = form.cleaned_data['curso_turma']
        trabalhador_educando = form.cleaned_data['trabalhador_educando']
        # situacao_periodo = form.cleaned_data['situacao_periodo']
        intervalo_inicio = form.cleaned_data['intervalo_inicio']
        intervalo_fim = form.cleaned_data['intervalo_fim']
        situacoes_inativas = form.cleaned_data['situacoes_inativas']

        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

        qs_aulas = Aula.objects.all()
        qs_matriculas_curso_turma = MatriculaCursoTurma.objects.all()

        if trabalhador_educando:
            # qs_aulas = qs_aulas.filter(curso_turma__id=trabalhador_educando.id)
            qs_aulas = qs_aulas.filter(curso_turma__in=trabalhador_educando.matriculacursoturma_set.all().values_list('curso_turma'))
            qs_matriculas_curso_turma = qs_matriculas_curso_turma.filter(trabalhador_educando_id=trabalhador_educando.id)

        if curso_turma:
            qs_aulas = qs_aulas.filter(curso_turma_id=curso_turma.id)
            qs_matriculas_curso_turma = qs_matriculas_curso_turma.filter(curso_turma_id=curso_turma.id)

        if turma:
            qs_aulas = qs_aulas.filter(curso_turma__turma=turma.id)
            qs_matriculas_curso_turma = qs_matriculas_curso_turma.filter(curso_turma__turma_id=turma.id)

        # if situacao_periodo:
        #     qs_aulas = qs_aulas.filter(professor_diario__diario__matriculadiario__matricula_periodo__situacao__in=situacao_periodo)
        #     qs_matriculas_periodo = qs_matriculas_periodo.filter(situacao__in=situacao_periodo)

        if intervalo_inicio:
            qs_aulas = qs_aulas.filter(data__gte=intervalo_inicio)

        if intervalo_fim:
            qs_aulas = qs_aulas.filter(data__lte=intervalo_fim)

        if qs_aulas.exists():
            data_primeira_aula = qs_aulas.order_by('data')[0].data
            data_ultima_aula = qs_aulas.latest('data').data
            data_primeira_aula = data_primeira_aula.replace(day=1)
            data_ultima_aula = data_ultima_aula.replace(day=1)
            qtd_meses = relativedelta(data_ultima_aula, data_primeira_aula).months + 1

            lista1 = [
                [
                    (data_primeira_aula + relativedelta(months=n)).year,
                    (data_primeira_aula + relativedelta(months=n)).month,
                    meses[(data_primeira_aula + relativedelta(months=n)).month - 1],
                ]
                for n in range(qtd_meses)
            ]

            matriculas_curso_turmas = []
            for matriculas_curso_turma in qs_matriculas_curso_turma:
                faltas = []
                # qs_aulas_mp = Aula.objects.filter(curso_turma=matriculas_curso_turma.trabalhador_educando.id)
                qs_aulas_mp = Aula.objects.filter(curso_turma=matriculas_curso_turma.curso_turma)
                qs_faltas = Falta.objects.filter(matricula_curso_turma__curso_turma=matriculas_curso_turma.curso_turma, matricula_curso_turma_id=matriculas_curso_turma.id)

                if intervalo_inicio:
                    qs_aulas_mp = qs_aulas_mp.filter(data__gte=intervalo_inicio)
                    qs_faltas = qs_faltas.filter(aula__data__gte=intervalo_inicio)

                if intervalo_fim:
                    qs_aulas_mp = qs_aulas_mp.filter(data__lte=intervalo_fim)
                    qs_faltas = qs_faltas.filter(aula__data__lte=intervalo_fim)

                if curso_turma:
                    qs_aulas_mp = qs_aulas_mp.filter(curso_turma_id=curso_turma.id)
                    qs_faltas = qs_faltas.filter(matricula_curso_turma__curso_turma=curso_turma)

                aulas_faltas_abonos = []
                aulas_total = 0
                faltas_total = 0
                abonos_total = 0
                for ano, mes, descricao in lista1:
                    aula, pks = matriculas_curso_turma.get_qtd_aulas(qs_aulas_mp, mes, ano, situacoes_inativas) or 0
                    falta = aula and matriculas_curso_turma.get_qtd_faltas(pks, qs_faltas) or 0
                    # abono = falta and matriculas_curso_turma.get_qtd_faltas(pks, qs_faltas, True) or 0
                    abono = 0
                    aulas_faltas_abonos.append({'aula': aula, 'falta': falta, 'abono': abono})
                    aulas_total += aula
                    faltas_total += falta
                    # abonos_total += abono

                matriculas_curso_turma.aulas_faltas_abonos = aulas_faltas_abonos
                matriculas_curso_turma.aulas_total = aulas_total
                matriculas_curso_turma.faltas_total = faltas_total
                matriculas_curso_turma.abonos_total = abonos_total
                percentual_faltas = 0
                percentual_presenca = 0
                if matriculas_curso_turma.aulas_total:
                    percentual_faltas = matriculas_curso_turma.faltas_total * 100 / matriculas_curso_turma.aulas_total
                    percentual_presenca = 100 - percentual_faltas

                matriculas_curso_turma.percentual_faltas = '{number:.{digits}f}%'.format(number=percentual_faltas, digits=2)
                matriculas_curso_turma.percentual_presenca = '{number:.{digits}f}%'.format(number=percentual_presenca, digits=2)
                matriculas_curso_turmas.append(matriculas_curso_turma)

            matriculas_curso_turmas = sorted(matriculas_curso_turmas, key=lambda x: x.percentual_presenca, reverse=True)

            # if 'exportar' in request.GET:
            #     lista = []
            #     matriculas_periodos_ids = request.POST.getlist('select_aluno')
            #     if matriculas_periodos_ids:
            #         ids = list(map(int, matriculas_periodos_ids))
            #         for matricula_periodo in matriculas_curso_turmas:
            #             if matricula_periodo.id in ids:
            #                 lista.append(matricula_periodo)
            #         matriculas_periodos = lista
            #
            #     response = HttpResponse(content_type='application/ms-excel')
            #     response['Content-Disposition'] = 'attachment; filename=relatorio_de_faltas.xls'
            #
            #     wb = xlwt.Workbook(encoding='utf-8')
            #     sheet1 = FitSheetWrapper(wb.add_sheet('Relatório de Faltas'))
            #     style = xlwt.easyxf(
            #         'pattern: pattern solid, fore_colour gray25; borders: left thin, right thin, top thin, bottom thin; '
            #         'font: colour black, bold True; align: wrap on, vert centre, horiz center;'
            #     )
            #
            #     col = 0
            #     line = 0
            #
            #     sheet1.write_merge(line, line + 1, col, col, 'Matrícula', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Aluno', style)
            #     col += 1
            #
            #     if aluno:
            #         sheet1.write_merge(line, line + 1, col, col, 'Período Letivo', style)
            #         col += 1
            #
            #     for ano, mes, descricao in lista1:
            #         sheet1.write_merge(line, line, col, col + 2, f'{descricao}/{ano}', style)
            #         sheet1.write_merge(line + 1, line + 1, col, col, 'Aulas', style)
            #         col += 1
            #         sheet1.write_merge(line + 1, line + 1, col, col, 'Faltas', style)
            #         col += 1
            #         sheet1.write_merge(line + 1, line + 1, col, col, 'Abonos', style)
            #         col += 1
            #
            #     sheet1.write_merge(line, line + 1, col, col, 'Total de Aulas', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Total de Faltas', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Percentual de Presença', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Percentual de Faltas', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Total de Justificativas', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Email do Aluno', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Telefone do Aluno', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Email do Responsável', style)
            #     col += 1
            #     sheet1.write_merge(line, line + 1, col, col, 'Telefone do Responsável', style)
            #
            #     line = 1
            #
            #     for matricula_periodo in matriculas_periodos:
            #         line += 1
            #         col = 0
            #         sheet1.row(line).write(col, matricula_periodo.aluno.matricula)
            #         col += 1
            #         sheet1.row(line).write(col, matricula_periodo.aluno.pessoa_fisica.nome)
            #         col += 1
            #         if aluno:
            #             sheet1.row(line).write(col, f'{matricula_periodo.ano_letivo.ano}/{matricula_periodo.periodo_letivo}')
            #             col += 1
            #         for n in matricula_periodo.aulas_faltas_abonos:
            #             sheet1.row(line).write(col, n['aula'])
            #             col += 1
            #             sheet1.row(line).write(col, n['falta'])
            #             col += 1
            #             sheet1.row(line).write(col, n['abono'])
            #             col += 1
            #
            #         sheet1.row(line).write(col, matricula_periodo.aulas_total)
            #         col += 1
            #         sheet1.row(line).write(col, matricula_periodo.faltas_total)
            #         col += 1
            #         sheet1.row(line).write(col, matricula_periodo.percentual_presenca)
            #         col += 1
            #         sheet1.row(line).write(col, matricula_periodo.percentual_faltas)
            #         col += 1
            #         sheet1.row(line).write(col, matricula_periodo.abonos_total)
            #         col += 1
            #         email_trabalhador_educando = matricula_periodo.trabalhador_educando.email_academico or matricula_periodo.trabalhador_educando.pessoa_fisica.email or '-'
            #         sheet1.row(line).write(col, email_trabalhador_educando)
            #         col += 1
            #         sheet1.row(line).write(col, matricula_periodo.trabalhador_educando.get_telefones() or '-')
            #         col += 1
            #         sheet1.row(line).write(col, matricula_periodo.trabalhador_educando.email_responsavel or '-')
            #         col += 1
            #         sheet1.row(line).write(col, '-')
            #
            #     wb.save(response)

                # return response

            # if 'notificar' in request.GET:
            #     for matricula_periodo in matriculas_periodos:
            #         faltas_nao_justificadas = matricula_periodo.faltas_total - matricula_periodo.abonos_total
            #         if matricula_periodo.trabalhador_educando.email_responsavel and faltas_nao_justificadas > 0:
            #             titulo = '[SUAP] Alerta de Frequência de Aluno'
            #             texto = (
            #                 '<h1>Ensino</h1>'
            #                 '<h2>Alerta de Frequência de Aluno</h2>'
            #                 '<p>O trabalhador_educando {} ({}) tem {:d} falta(s) não justificadas.</p>'.format(
            #                     matricula_periodo.trabalhador_educando.pessoa_fisica.nome, matricula_periodo.trabalhador_educando.matricula, faltas_nao_justificadas
            #                 )
            #             )
            #             email_destino = [matricula_periodo.aluno.email_responsavel]
            #             send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, email_destino)
            #     return httprr(request.META.get('HTTP_REFERER') or '.', 'Notificação enviada com sucesso')
    return locals()

@rtr()
@login_required()
#@permission_required('edu.gerar_relatorio')
def relatorio_ppe(request):
    title = 'Listagem de Matriculados'
    tabela = None
    quantidade_itens = 25

    form = RelatorioPpeForm(request, data=request.GET or None)
    if 'editar' in request.GET:
        formatacao = None
    else:
        if form.is_valid():
            exibicao_choices = form.EXIBICAO_CHOICES + form.EXIBICAO_COMUNICACAO + form.EXIBICAO_DADOS_PESSOAIS
            #ano_letivo = form.cleaned_data.get('ano_letivo')
            #periodo_letivo = int(form.cleaned_data.get('periodo_letivo', 0) or 0)
            query_string = request.META.get('QUERY_STRING', '').encode("utf-8").hex()
            trabalhadores_educando = form.processar()
            trabalhadores_educando_list = request.POST.getlist('select_trabalhador_educando')
            quantidade_itens = form.cleaned_data['quantidade_itens']
            if trabalhadores_educando_list:
                filtros = trabalhadores_educando.filtros
                trabalhadores_educando = TrabalhadorEducando.objects.filter(id__in=trabalhadores_educando_list)
                trabalhadores_educando.filtros = filtros
            formatacao = form.cleaned_data['formatacao']

            filtros = trabalhadores_educando.filtros
            agrupamento = form.cleaned_data['agrupamento']

            campos_exibicao = form.cleaned_data['exibicao']
            # if (ano_letivo and not periodo_letivo) or (periodo_letivo and not ano_letivo):
            #     if 'get_situacao_periodo_referencia' in campos_exibicao:
            #         campos_exibicao.remove('get_situacao_periodo_referencia')
            #     if 'get_frequencia_periodo_referencia' in campos_exibicao:
            #         campos_exibicao.remove('get_frequencia_periodo_referencia')
            # if 'pendencias' in campos_exibicao:
            #     campos_exibicao.remove('pendencias')
            #     for chave, valor in RelatorioForm.PENDENCIAS_EXIBICAO_CHOICES:
            #         campos_exibicao.append(chave)

            if 'imprimir' in request.POST:
                title = 'Listagem de Trabalhadores Educando'
                return relatorio_ppe_pdf(request, trabalhadores_educando, formatacao, campos_exibicao, title)
            if 'xls' in request.POST and tabela:
                rows = [tabela.colunas]
                for registro in tabela.registros:
                    row = []
                    for key in registro:
                        row.append(registro[key])
                    rows.append(row)
                return XlsResponse(rows)

            if 'xls' in request.POST:
                # Se for qualquer outra formatação
                cabecalhos = exibicao_choices
                return tasks.exportar_listagem_trabalhadores_educando_xls(trabalhadores_educando, filtros, campos_exibicao, cabecalhos)

    return locals()

@documento()
@rtr('relatorio_impressao_ppe_pdf.html')
@login_required()
def relatorio_ppe_pdf(request, trabalhadores_educando, formatacao, campos_exibicao, title):
    title = title
    campos_exibicao = campos_exibicao[0:3]
    campos_exibicao_choices = RelatorioPpeForm.EXIBICAO_CHOICES
    filtros = trabalhadores_educando.filtros
    return locals()

@login_required()
@rtr()
def salvar_relatorio_ppe(request, tipo, query_string):
    title = 'Salvar Consulta'
    form = SalvarRelatorioPpeForm(request.POST or None, tipo=tipo)
    if form.is_valid():
        form.processar(query_string)
        return httprr(f'/ppe/meus_relatorios/{tipo}/', 'Consulta salva com sucesso.', close_popup=True)
    return locals()

@rtr()
@login_required()
#@permission_required('edu.gerar_relatorio')
def relatorio_aprovados_ppe(request):
    title = 'Listagem de Aprovados'
    tabela = None
    quantidade_itens = 25

    form = RelatorioAprovadosPpeForm(request, data=request.GET or None)
    if 'editar' in request.GET:
        formatacao = None
    else:
        if form.is_valid():
            exibicao_choices = form.EXIBICAO_CHOICES + form.EXIBICAO_COMUNICACAO + form.EXIBICAO_DADOS_PESSOAIS
            query_string = request.META.get('QUERY_STRING', '').encode("utf-8").hex()
            trabalhadores_educando = form.processar()
            trabalhadores_educando_list = request.POST.getlist('select_trabalhador_educando')
            quantidade_itens = form.cleaned_data['quantidade_itens']
            if trabalhadores_educando_list:
                filtros = trabalhadores_educando.filtros
                trabalhadores_educando = TrabalhadorEducando.objects.filter(id__in=trabalhadores_educando_list)
                trabalhadores_educando.filtros = filtros
            formatacao = form.cleaned_data['formatacao']

            filtros = trabalhadores_educando.filtros
            agrupamento = form.cleaned_data['agrupamento']

            campos_exibicao = form.cleaned_data['exibicao']
            # if (ano_letivo and not periodo_letivo) or (periodo_letivo and not ano_letivo):
            #     if 'get_situacao_periodo_referencia' in campos_exibicao:
            #         campos_exibicao.remove('get_situacao_periodo_referencia')
            #     if 'get_frequencia_periodo_referencia' in campos_exibicao:
            #         campos_exibicao.remove('get_frequencia_periodo_referencia')
            # if 'pendencias' in campos_exibicao:
            #     campos_exibicao.remove('pendencias')
            #     for chave, valor in RelatorioForm.PENDENCIAS_EXIBICAO_CHOICES:
            #         campos_exibicao.append(chave)

            if 'imprimir' in request.POST:
                title = 'Relatório de Aprovados PPE'
                return relatorio_aprovados_ppe_pdf(request, trabalhadores_educando, formatacao, campos_exibicao, title)
            if 'xls' in request.POST and tabela:
                rows = [tabela.colunas]
                for registro in tabela.registros:
                    row = []
                    for key in registro:
                        row.append(registro[key])
                    rows.append(row)
                return XlsResponse(rows)

            if 'xls' in request.POST:
                # Se for qualquer outra formatação
                cabecalhos = exibicao_choices
                return tasks.exportar_listagem_trabalhadores_educando_xls(trabalhadores_educando, filtros, campos_exibicao, cabecalhos)
            
    return locals()

@documento()
@rtr('relatorio_impressao_ppe_pdf.html')
@login_required()
def relatorio_aprovados_ppe_pdf(request, trabalhadores_educando, formatacao, campos_exibicao, title):
    title = title
    campos_exibicao = campos_exibicao[0:3]
    if request.user.has_perm('ppe.view_dados_pessoais'):
        campos_exibicao_choices = RelatorioAprovadosPpeForm.EXIBICAO_CHOICES + RelatorioAprovadosPpeForm.EXIBICAO_DADOS_PESSOAIS
    else:
        campos_exibicao_choices = RelatorioAprovadosPpeForm.EXIBICAO_DADOS_PESSOAIS
    filtros = trabalhadores_educando.filtros
    return locals()

@permission_required('ppe.view_turma')
@rtr()
def mapa_notas_ppe(request, pk):
    turma = get_object_or_404(Turma, pk=pk)

    title = f'Mapa de Notas da Turma - {turma}'
    form = MapaTurmaPpeForm(turma.cursoturma_set.all(), request.POST or None)
    diarios = None
    if form.is_valid():
        diarios = form.cleaned_data['diarios']

        quantidade = 1
        for diario in diarios:
            if len(diario.get_lista_etapas()) > quantidade:
                quantidade = len(diario.get_lista_etapas())
        etapas = OrderedDict()
        for etapa in range(1, quantidade + 1):
            etapas[f'etapa_{etapa}'] = f'Etapa {etapa}'
        etapas['etapa_final'] = 'Etapa Final'

        matriculas_curso_turma = turma.get_trabalhadores_educando_relacionados(diarios = diarios)
        tabela_mapa = []
        count = 0
        situacoes_diario = [md.get_situacao_diario_resumida() for md in matriculas_curso_turma]
        for matricula_curso_turma in matriculas_curso_turma:
            #situacoes_diario = [md.get_situacao_diario_resumida() for md in matriculas_curso_turma]
            trabalhador_educando_diarios = []            
            #TODO renomear diario.pk          
            for diario in diarios:
                if count < matriculas_curso_turma.count() and matriculas_curso_turma[count].curso_turma.pk == diario.pk:                
                    trabalhador_educando_diarios.append(
                        {
                            'md': matriculas_curso_turma[count],
                            'rotulo': situacoes_diario[count]['rotulo'],
                            # 'faltasetapa1': matriculas_diario[count].total_faltas,
                            # 'percentualfrequencia': matriculas_diario[count].get_percentual_carga_horaria_frequentada(),
                        }
                    )
                    count += 1
                else:
                    trabalhador_educando_diarios.append({'md': None})
            tabela_mapa.append([matricula_curso_turma, trabalhador_educando_diarios])
        

    if request.POST.get('xls'):
        response = HTTPResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=mapa_turma.xls'

        wb = xlwt.Workbook(encoding='utf-8')
        sheet1 = wb.add_sheet('Etapa 1')
        sheet2 = wb.add_sheet('Etapa 2')
        sheet3 = wb.add_sheet('Etapa 3')
        sheet4 = wb.add_sheet('Etapa 4')
        sheetfinal = wb.add_sheet('Etapa Final')
        style = xlwt.easyxf('pattern: pattern solid, fore_colour gray25;' 'borders: left thin, right thin, top thin, bottom thin;' 'font: colour black, bold True;')

        sheet1.row(0).write(0, '', style)
        sheet2.row(0).write(0, '', style)
        sheet3.row(0).write(0, '', style)
        sheet4.row(0).write(0, '', style)
        sheetfinal.row(0).write(0, '', style)

        colspan = 3
        count = 1
        for diario in diarios:
            sheet1.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            sheet2.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            sheet3.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            sheet4.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            sheetfinal.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            count += 1

        sheet1.row(1).write(0, 'Carga Horária', style)
        sheet2.row(1).write(0, 'Carga Horária', style)
        sheet3.row(1).write(0, 'Carga Horária', style)
        sheet4.row(1).write(0, 'Carga Horária', style)
        sheetfinal.row(1).write(0, 'Carga Horária', style)
        count = 1
        for diario in diarios:
            sheet1.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheet2.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheet3.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheet4.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheetfinal.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheet1.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheet2.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheet3.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheet4.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheetfinal.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheet1.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheet2.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheet3.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheet4.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheetfinal.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheet1.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            sheet2.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            sheet3.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            sheet4.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            sheetfinal.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            count += 1

        sheet1.row(2).write(0, 'Aluno', style)
        sheet2.row(2).write(0, 'Aluno', style)
        sheet3.row(2).write(0, 'Aluno', style)
        sheet4.row(2).write(0, 'Aluno', style)
        sheetfinal.row(2).write(0, 'Aluno', style)
        posicao_media = (diarios.count() * colspan) + 1
        sheet1.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        sheet2.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        sheet3.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        sheet4.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        sheetfinal.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        count = 3
        for item in tabela_mapa:
            sheet1.row(count).write(0, item[0].trabalhador_educando.get_nome_social_composto())
            sheet2.row(count).write(0, item[0].trabalhador_educando.get_nome_social_composto())
            sheet3.row(count).write(0, item[0].trabalhador_educando.get_nome_social_composto())
            sheet4.row(count).write(0, item[0].trabalhador_educando.get_nome_social_composto())
            sheetfinal.row(count).write(0, item[0].trabalhador_educando.get_nome_social_composto())

            count_etapa1 = 1
            # Etapa 1
            for value in item[1]:
                if value.get('md'):
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1), value.get('md').nota_1 or '-')
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1) + 1, value.get('faltasetapa1') or '-')
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1), '-')
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1) + 1, '-')
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1) + 2, '-')
                count_etapa1 += 1
            sheet1.row(count).write(posicao_media, format_(item[0].get_media_na_primeira_etapa()))

            count_etapa2 = 1
            # Etapa 2
            for value in item[1]:
                if value.get('md'):
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1), value.get('md').nota_2 or '-')
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1) + 1, value.get('faltasetapa2') or '-')
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1), '-')
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1) + 1, '-')
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1) + 2, '-')
                count_etapa2 += 1
            sheet2.row(count).write(posicao_media, format_(item[0].get_media_na_segunda_etapa()))

            count_etapa3 = 1
            # Etapa 3
            for value in item[1]:
                if value.get('md'):
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1), value.get('md').nota_3 or '-')
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1) + 1, value.get('faltasetapa3') or '-')
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1), '-')
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1) + 1, '-')
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1) + 2, '-')
                count_etapa3 += 1
            sheet3.row(count).write(posicao_media, format_(item[0].get_media_na_terceira_etapa()))

            count_etapa4 = 1
            # Etapa 4
            for value in item[1]:
                if value.get('md'):
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1), value.get('md').nota_4 or '-')
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1) + 1, value.get('faltasetapa4') or '-')
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1), '-')
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1) + 1, '-')
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1) + 2, '-')
                count_etapa4 += 1
            sheet4.row(count).write(posicao_media, format_(item[0].get_media_na_quarta_etapa()))

            # Etapa Final
            count_etapa_final = 1
            for value in item[1]:
                if value.get('md'):
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1), value.get('md').nota_final or '-')
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1) + 1, '-')
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1), '-')
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1) + 1, '-')
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1) + 2, '-')
                count_etapa_final += 1
            sheetfinal.row(count).write(posicao_media, format_(item[0].get_media_na_etapa_final()))

            count += 1

        wb.save(response)

        return response

    return locals()

@documento('Declaração de Matrícula', False, validade=30, enumerar_paginas=False, modelo='ppe.TrabalhadorEducando')
@rtr('declaracaomatriculappe_pdf.html')
def declaracaomatriculappe_pdf(request, pk):
    trabalhador_educando = get_object_or_404(TrabalhadorEducando, pk=pk)
    situacao = trabalhador_educando.situacao
    #exibir_modalidade = 'Técnico' in aluno.curso_campus.modalidade.descricao
    eh_masculino = trabalhador_educando.pessoa_fisica.sexo == 'M'

    is_usuario_proprio_trabalhador_educando = trabalhador_educando.is_user(request)
    if (
        not is_usuario_proprio_trabalhador_educando
        and not request.user.has_perm('ppe.efetuar_matricula')
        and not in_group(request.user, 'Trabalhador(a) Educando(a), Coordenador(a) PPE, Gestor(a) PPE')
        and not request.session.get('matricula-servico-impressao') == pk
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    # if not aluno.possui_historico():
    #     return httprr('.', 'Aluno importado. Não possui diários no SUAP.', 'error')

    if not trabalhador_educando.is_matriculado(): #and not aluno.is_intercambio():
        return httprr('..', 'Não possível emitir a declaração, pois o aluno não está matriculado.', 'error')

    matricula_curso_turma = MatriculaCursoTurma.objects.filter(trabalhador_educando=trabalhador_educando).latest('id')
    # uo = aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    # polo = aluno.polo
    return locals()



@rtr()
@login_required
def avaliacao_trabalhador_educando(request, trabalhador_educando_id, tipo_avaliacao_id):
    initial = {}

    tipo_avaliacao = get_object_or_404(TipoAvaliacao, pk=tipo_avaliacao_id)

    # periodo_escolhido = get_object_or_404(PeriodoInscricao, pk=periodo_id)
    trabalhador_educando = get_object_or_404(TrabalhadorEducando, pk=trabalhador_educando_id)

    if not request.user == trabalhador_educando.pessoa_fisica.user and tipo_avaliacao_id == Avaliacao.AUTOAVALIACAO:
        return httprr('/', 'A autoaviação não pode ser realizada.', tag='error')

    if trabalhador_educando.get_chefe_atual() and not request.user == trabalhador_educando.get_chefe_atual().pessoa_fisica.user and tipo_avaliacao_id == Avaliacao.AVALIACAO_CHEFIA:
        return httprr('/', 'A aviação não pode ser realizada.', tag='error')

    sigla_tipo_avaliacao = tipo_avaliacao.sigla

    eh_trabalhador_educando = request.user.eh_trabalhadoreducando
    if eh_trabalhador_educando:
        tipo_display = 'AUTOAVALIAÇÃO'
        papel_avalidor = Avaliacao.AUTOAVALIACAO
    else:
        tipo_display = 'AVALIAÇÃO CHEFIA'
        papel_avalidor = Avaliacao.AVALIACAO_CHEFIA
        qs_autoavaliacao = Avaliacao.objects.filter(tipo_avaliacao=tipo_avaliacao, papel_avalidor=Avaliacao.AUTOAVALIACAO)
        if qs_autoavaliacao.exists():
            respostasautoavaliacao = qs_autoavaliacao[0].get_respostas()
        else:
            return httprr('/', 'Autoavaliação do trabalhador educando ainda não preenchida.', tag='error')

    title = f'Avaliação {tipo_avaliacao}: {tipo_display}'

    is_trabalhador_educando = TrabalhadorEducando.objects.filter(pessoa_fisica=request.user.get_profile()).exists()
    avaliacao = None
    if Avaliacao.objects.filter(trabalhador_educando=trabalhador_educando_id, tipo_avaliacao=tipo_avaliacao_id, papel_avalidor=papel_avalidor).exists():
            avaliacao = Avaliacao.objects.filter(trabalhador_educando=trabalhador_educando_id, tipo_avaliacao=tipo_avaliacao_id,papel_avalidor=papel_avalidor).latest('id')
    else:
        avaliacao = Avaliacao()
        avaliacao.papel_avalidor = papel_avalidor

    respostas_previas = RespostaAvaliacao.objects.filter(pergunta__tipo_avaliacao=tipo_avaliacao, pergunta__formacao_tecnica=trabalhador_educando.formacao_tecnica, avaliacao=avaliacao)
    ids_respostas_atuais = list()
    if request.method == 'POST':
        form = PerguntaAvaliacaoForm(request.POST or None, request=request, avaliacao=avaliacao, tipo_avaliacao=tipo_avaliacao, formacao_tecnica=trabalhador_educando.formacao_tecnica)

        if form.is_valid():

            trabalhador_educando = TrabalhadorEducando.objects.get(pk=trabalhador_educando_id)
            if not avaliacao:
                avaliacao = Avaliacao()

            avaliacao.tipo_avaliacao = TipoAvaliacao.objects.get(pk=tipo_avaliacao_id)
            avaliacao.trabalhador_educando = trabalhador_educando
            avaliacao.atualizado_por = request.user.get_vinculo()
            avaliacao.data_atualizacao = datetime.datetime.now()
            avaliacao.save()

            chaves = list(request.POST.keys())

            for item in chaves:
                valores = request.POST.getlist(item)
                if 'pergunta_' in item:
                    id = item.split('_')[1]
                    pergunta_respondida = get_object_or_404(PerguntaAvaliacao, pk=id)
                    for valor in valores:
                        valor_foi_informado = None
                        try:
                            valor_foi_informado = int(valor)
                        except Exception:
                            pass
                        if valor_foi_informado:
                            resposta_informada = get_object_or_404(OpcaoRespostaAvaliacao, pk=valor_foi_informado)
                            if PerguntaAvaliacao.objects.filter(id=id, ativo=True).exists():
                                if respostas_previas.filter(pergunta=pergunta_respondida, resposta=resposta_informada).exists():
                                    o = RespostaAvaliacao.objects.filter(pergunta=pergunta_respondida, avaliacao=avaliacao, resposta__isnull=False)[0]
                                else:
                                    o = RespostaAvaliacao()
                                    o.avaliacao = avaliacao
                                    o.pergunta = pergunta_respondida
                                o.resposta = resposta_informada
                                o.save()
                                ids_respostas_atuais.append(o.id)

                elif 'texto_' in item:
                    id = item.split('_')[1]
                    pergunta_respondida = get_object_or_404(PerguntaAvaliacao, pk=id)
                    valor_informado = valores[0]
                    if pergunta_respondida.tipo_resposta == PerguntaAvaliacao.NUMERO:
                        valor_informado = valor_informado.replace('.', '').replace(',', '.')
                    if RespostaAvaliacao.objects.filter(pergunta=pergunta_respondida, avaliacao=avaliacao).exists():
                        o = RespostaAvaliacao.objects.filter(pergunta=pergunta_respondida, avaliacao=avaliacao)[0]
                    else:
                        o = RespostaAvaliacao()
                        o.avaliacao = avaliacao
                        o.pergunta = pergunta_respondida
                    o.valor_informado = valor_informado
                    o.save()
                    ids_respostas_atuais.append(o.id)

            respostas_previas.exclude(id__in=ids_respostas_atuais).delete()
            return httprr(f"/ppe/avaliacao_trabalhador_educando_confirmacao/{avaliacao.pk:d}/", 'Avaliação realizada com sucesso.')
    else:
        # if avaliacao:
        #     initial['justificativa'] = avaliacao.motivo
        form = PerguntaAvaliacaoForm(avaliacao=avaliacao, tipo_avaliacao=tipo_avaliacao, formacao_tecnica=trabalhador_educando.formacao_tecnica)
    return locals()


@rtr()
@login_required
def avaliacao_trabalhador_educando_confirmacao(request,avaliacao_id):

    respostas = None
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)
    trabalhador_educando = avaliacao.trabalhador_educando
    respostas = avaliacao.get_respostas()

    title = f'Resumo da {avaliacao.get_papel_avalidor_display()}'

    te_logado = TrabalhadorEducando.objects.filter(pessoa_fisica=request.user.get_profile())
    eh_aluno = request.user.eh_trabalhadoreducando
    if te_logado and te_logado[0] != avaliacao.trabalhador_educando:
        if not request.user.has_perm('pee.view_avaliacao'):
            raise PermissionDenied()

    return locals()




@documento()
@rtr()
def avaliacao_trabalhador_educando_resumo_pdf(request, avaliacao_id):

    respostas = []
    avaliacao = get_object_or_404(Avaliacao, pk=avaliacao_id)
    trabalhador_educando = avaliacao.trabalhador_educando
    qs_avaliacao = avaliacao.get_respostas()
    autoavaliacao = Avaliacao.objects.filter(tipo_avaliacao=avaliacao.tipo_avaliacao,
                                                trabalhador_educando=trabalhador_educando,
                                                papel_avalidor=Avaliacao.AUTOAVALIACAO).first()
    if autoavaliacao:
        respostasautoavaliacao = autoavaliacao.get_respostas()

    for resposta in qs_avaliacao:
        temp_resposta = resposta
        temp_resposta.respostaauto = respostasautoavaliacao.filter(pergunta=resposta.pergunta).first()
        respostas.append(temp_resposta)

    te_logado = TrabalhadorEducando.objects.filter(pessoa_fisica=request.user.get_profile())
    eh_aluno = request.user.eh_trabalhadoreducando
    if te_logado and te_logado[0] != avaliacao.trabalhador_educando:
        if not request.user.has_perm('pee.view_avaliacao'):
            raise PermissionDenied()

    return locals()


def gerar_pdf_trabalhador_educando_resumo(request, avaliacao_id):
        merger = PdfFileMerger()
        response = avaliacao_trabalhador_educando_resumo_pdf(request, avaliacao_id)
        merger.append(io.BytesIO(response.content))
        merged_file = tempfile.NamedTemporaryFile(suffix=".pdf", dir=settings.TEMP_DIR, delete=False)
        merger.write(merged_file.name)
        return HttpResponse(open(merged_file.name, 'r+b').read(), content_type='application/pdf')
@rtr()
@permission_required("ppe.view_setor")
def setor(request, pk):
    setor = get_object_or_404(Setor.objects, pk=pk)
    vinculo = request.user.get_relacionamento()
    # eh_chefe_do_setor_hoje = hasattr(vinculo, "eh_chefe_do_setor_hoje") and vinculo.eh_chefe_do_setor_hoje(setor)
    title = "{} - {}".format(setor.sigla, setor.nome)
    # servidores = Servidor.objects.ativos().filter(setor=setor, cargo_emprego__isnull=False).exclude(
    #     situacao__codigo__in=Situacao.situacoes_siape_estagiarios()
    # ) | Servidor.objects.em_exercicio().filter(setor=setor, cargo_emprego__isnull=False).exclude(
    #     situacao__codigo__in=Situacao.situacoes_siape_estagiarios()
    # )
    # estagiarios = Servidor.objects.estagiarios().filter(setor=setor)
    # prestadores = PrestadorServico.objects.filter(setor=setor, ativo=True)
    # if "ae" in settings.INSTALLED_APPS:
    #     from ae.models import ParticipacaoTrabalho
    #
    #     bolsistas = ParticipacaoTrabalho.objects.filter(
    #         (Q(participacao__data_termino__gte=datetime.today()) | Q(participacao__data_termino__isnull=True))
    #         & Q(bolsa_concedida__setor=setor)
    #     )
    # filhos = Setor.objects.filter(pk__in=setor.filhos.values_list("pk", flat=True))
    # chefes_atuais = Servidor.objects.filter(
    #     pk__in=ServidorFuncaoHistorico.objects.atuais()
    #     .filter(setor_suap=setor, funcao__codigo__in=Funcao.get_codigos_funcao_chefia())
    #     .values_list("servidor", flat=True)
    #     .distinct()
    # )
    # funcoes_chefes_atuais = []
    # for chefe in chefes_atuais:
    #     funcoes_chefes_atuais.append(
    #         dict(servidor=chefe, funcoes=ServidorFuncaoHistorico.objects.atuais().filter(setor_suap=setor, servidor=chefe))
    #     )
    # servidores_com_acesso = Servidor.objects.ativos().filter(setores_adicionais=setor)
    # estagiarios_com_acesso = Servidor.objects.estagiarios().filter(setores_adicionais=setor)
    # prestadores_com_acesso = PrestadorServico.objects.filter(setores_adicionais=setor, ativo=True)
    #
    # servidores_inativos = ServidorSetorHistorico.objects.filter(setor=setor, data_fim_no_setor__isnull=False).order_by(
    #     "-data_inicio_no_setor"
    # )

    return locals()

@rtr()
@group_required("Chefia imediata PPE")
def avaliacoes_chefia(request):
    title = u'Avaliações pela Chefia'
    chefe = request.user.get_relacionamento()
    trabalhadores =[]
    for setor_chefiados in chefe.chefiasetorhistorico_set.all():
        for setor_trabalhador in setor_chefiados.setor.setor_trabalhador.all():
            trabalhadores.append(setor_trabalhador.trabalhador_educando)

    avaliacoes = Avaliacao.objects.filter(trabalhador_educando__in=trabalhadores)

    pendentes_avaliacao_ids = []
    avaliadas_ids = []
    for avaliacao in avaliacoes:
        if avaliacao.pode_ser_avaliada_chefia() and avaliacao.papel_avalidor == Avaliacao.AUTOAVALIACAO:
            pendentes_avaliacao_ids.append(avaliacao.id)

    pendentes_avaliacao = Avaliacao.objects.filter(id__in=pendentes_avaliacao_ids,
                                                papel_avalidor=Avaliacao.AUTOAVALIACAO)

    avaliadas = Avaliacao.objects.filter(papel_avalidor=Avaliacao.AVALIACAO_CHEFIA, trabalhador_educando__in=trabalhadores)

    return locals()


@rtr()
def alterar_nome_breve_curso_moodle(request, pk_curso_turma):
    curso_turma = get_object_or_404(CursoTurma.objects, pk=pk_curso_turma)
    title = f'Alterar nome breve curso moodle - {curso_turma}'
    form = AlterarNomeBreveCursoMoodleForm(data=request.POST or None, curso_turma=curso_turma)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Nome breve curso moodle alterado com sucesso.')
    return locals()


@rtr()
@login_required
def certconclusaoporcursoppe(request, pk):
    title = u'Certificados de Conclusão por Curso'
    trabalhadoreducando = get_object_or_404(TrabalhadorEducando, pk=pk)

    is_proprio_trabalhadoreducando = perms.is_proprio_trabalhadoreducando(request, trabalhadoreducando)
    is_admin = perms.is_admin(request.user)

    tem_permissao_para_emitir_docs_matricula = (request.user.has_perm('ppe.efetuar_matricula') or in_group(request.user, "Trabalhador Educando"))
    pode_alterar_email_trabalhadoreducando = perms.pode_alterar_email_trabalhadoreducando(request, trabalhadoreducando)
    tem_permissao_realizar_procedimentos = perms.tem_permissao_realizar_procedimentos(request.user, trabalhadoreducando)
    pode_ver_dados_trabalhadoreducando = perms.pode_ver_dados_trabalhadoreducando(request)
    pode_ver_dados_sociais = perms.pode_ver_dados_sociais(request, trabalhadoreducando)
    pode_ver_dados_academicos = (
            is_admin
            or is_proprio_trabalhadoreducando
            and request.user.has_perm('ppe.view_dados_academicos')
    )
    pode_ver_cpf = (
            is_admin
            or pode_ver_dados_sociais
            or pode_ver_dados_academicos
    )

    mcts = trabalhadoreducando.matriculacursoturma_set.all()

    grupos_cursos = OrderedDict()
    grupos_cursos['Formação Permanente'] = []
    grupos_cursos['Transversais'] = []
    grupos_cursos['Específicos'] = []

    cursos = trabalhadoreducando.formacao.cursoformacaoppe_set.all()
    for curso in cursos:
        cursos_formacao = curso.get_grupo_componente_historico(grupos_cursos)

        situacao_no_curso_display = None
        mct = None
        if mcts.filter(curso_turma__curso_formacao__id=curso.id).exists():
            mct = mcts.filter(curso_turma__curso_formacao__id=curso.id).latest('id')
            situacao_no_curso_display = mct.get_situacao_display()

        componente = dict(
            sigla_componente=curso.curso.codigo,
            mct=mct or None,
            descricao_componente=curso.curso.descricao,
            carga_horaria=curso.get_carga_horaria_total or '-',
            situacao_display=situacao_no_curso_display or '-',
        )
        cursos_formacao.append(componente)

    for grupo in list(grupos_cursos.values()):
        for componente in grupo:
            componente['sigla_componente'] = insert_space(componente['sigla_componente'], 9)

    cursos_trabalhador_educando = dict()

    cursos_trabalhador_educando.update(grupos_cursos=grupos_cursos)
    return locals()


@documento('Certificado de Conclusão do Curso', False, validade=30, enumerar_paginas=False, modelo='ppe.TrabalhadorEducando')
@rtr('certconclusaoporcursoppe_pdf.html')
@login_required
def certconclusaoporcursoppe_pdf(request, pk):
    mct = get_object_or_404(MatriculaCursoTurma, pk=pk)
    trabalhador_educando = mct.trabalhador_educando
    situacao = trabalhador_educando.situacao
    eh_masculino = trabalhador_educando.pessoa_fisica.sexo == 'M'

    is_usuario_proprio_trabalhador_educando = trabalhador_educando.is_user(request)
    if (
            not is_usuario_proprio_trabalhador_educando
            and not request.user.has_perm('ppe.efetuar_matricula')
            and not in_group(request.user, 'Supervisor(a) Pedagógico(a), Coordenador(a) PPE, Gestor(a) PPE')
            and not request.session.get('matricula-servico-impressao') == pk
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    hoje = datetime.datetime.now()
    return locals()


@documento('Certificado de Conclusão de 300 horas', False, validade=30, enumerar_paginas=False, modelo='ppe.TrabalhadorEducando')
@rtr('certtrezentashorasppe_pdf.html')
@login_required
def certtrezentashorasppe_pdf(request, pk):
    trabalhador_educando = get_object_or_404(TrabalhadorEducando, pk=pk)
    situacao = trabalhador_educando.situacao
    eh_masculino = trabalhador_educando.pessoa_fisica.sexo == 'M'

    is_usuario_proprio_trabalhador_educando = trabalhador_educando.is_user(request)
    if (
        not is_usuario_proprio_trabalhador_educando
        and not in_group(request.user, 'Supervisor(a) Pedagógico(a), Coordenador(a) PPE, Gestor(a) PPE')
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    mcts = trabalhador_educando.matriculacursoturma_set.all()  # .filter(situacao=MatriculaCursoTurma.SITUACAO_APROVADO)

    ch_pratica_total = mcts.aggregate(Sum('curso_turma__curso_formacao__ch_pratica')).get('curso_turma__curso_formacao__ch_pratica__sum') or 0
    ch_presencial_total = mcts.aggregate(Sum('curso_turma__curso_formacao__ch_presencial')).get('curso_turma__curso_formacao__ch_presencial__sum') or 0
    ch_total = ch_pratica_total + ch_presencial_total
    if ch_total < 300:
        return httprr(
            'HTTP_REFERER' in request.META and request.META['HTTP_REFERER'] or '..',
            'Ainda não foi atingida a quantidade de 300 horas de carga horária',
            'error'
        )

    ultima_data = mcts.filter(curso_turma__data_fim_etapa_1__isnull=False).order_by('curso_turma__data_fim_etapa_1').last().curso_turma.data_fim_etapa_1

    hoje = datetime.datetime.now()
    return locals()
