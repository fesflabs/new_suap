# -*- coding: utf-8 -*-
from datetime import datetime, date

from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.db.models.query_utils import Q
from django.shortcuts import get_object_or_404
from djtools import layout
from djtools.html.calendarios import Calendario
from djtools.utils import rtr, httprr, render
from rh.models import Servidor, Situacao
from temp_rh2.forms import GetInscricaoCompeticaoDesportivaForm, GetValidacaoInscricaoCompeticaoDesportivaForm, FormConfirmaInscricaoCursoSuap
from temp_rh2.models import CompeticaoDesportiva, InscricaoCompeticaoDesportiva, CursoSuap, InscricaoCursoSuap, LogInscricaoCursoSuap, ConteudoEmail
from djtools.utils.calendario import dateToStr
from django.contrib.auth.decorators import login_required
from django.db import transaction
from djtools.utils import send_notification, send_mail
from django.conf import settings


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    hoje = datetime.now()
    if request.user.eh_servidor:
        servidor = request.user.get_relacionamento()
        if servidor.situacao.codigo in Situacao.SITUACOES_EM_EXERCICIO_NO_INSTITUTO:
            competicoes_desportivas_em_aberto = CompeticaoDesportiva.objects.filter(data_inicio_periodo_inscricoes__lte=hoje, data_fim_periodo_inscricoes__gte=hoje)
            competicoes_desportivas_em_aberto = competicoes_desportivas_em_aberto.filter(Q(uo=servidor.setor.uo) | Q(uo__isnull=True))
            inscricoes_realizadas = servidor.inscricaocompeticaodesportiva_set.filter(competicao_desportiva__in=competicoes_desportivas_em_aberto)
            for inscricao in inscricoes_realizadas:
                competicao = inscricao.competicao_desportiva
                inscricoes.append(
                    dict(
                        url='/temp_rh2/competicao_desportiva/inscricao/{}/'.format(competicao.pk),
                        titulo='Inscrição nos <strong>{}</strong>.'.format(competicao),
                        prazo=dateToStr(competicao.data_fim_periodo_inscricoes),
                    )
                )
                competicoes_desportivas_em_aberto = competicoes_desportivas_em_aberto.exclude(pk=competicao.pk)

            for inscricao_competicao in competicoes_desportivas_em_aberto:
                inscricoes.append(
                    dict(
                        url='/temp_rh2/competicao_desportiva/inscricao/{}/'.format(inscricao_competicao.pk),
                        titulo='Inscrição nos <strong>{}</strong>.'.format(inscricao_competicao),
                        prazo=dateToStr(inscricao_competicao.data_fim_periodo_inscricoes),
                    )
                )

    return inscricoes


@layout.quadro('Cursos de Capacitação do SUAP', icone='file')
def index_quadros(quadro, request):
    # Desativando
    cursos_ativos = CursoSuap.objects.none()

    eh_servidor = request.user.eh_servidor
    if cursos_ativos.exists() and eh_servidor:
        quadro.add_item(layout.ItemAcessoRapido(titulo='Inscrições', url='/temp_rh2/listar_minhas_inscricoes/', classe='success'))
    return quadro


@rtr()
@permission_required('rh.view_servidor')
def inscricao_competicoes_desportivas(request, competicao_pk, inscricao_pk=None):
    competicao_desportiva = get_object_or_404(CompeticaoDesportiva.objects, pk=competicao_pk)
    if inscricao_pk:
        inscricao_desportiva = InscricaoCompeticaoDesportiva.objects.get(pk=inscricao_pk)
        return render('inscricao_competicao.html', locals())
    hoje = date.today()
    if not competicao_desportiva.data_inicio_periodo_inscricoes <= hoje <= competicao_desportiva.data_fim_periodo_inscricoes:
        raise PermissionDenied('Competição {} não está em período de inscrições.' % competicao_desportiva)
    servidor = request.user.get_profile().pessoafisica.funcionario.servidor
    if competicao_desportiva.uo:
        if competicao_desportiva.uo != request.user.get_profile().pessoafisica.funcionario.setor.uo:
            raise PermissionDenied('Competição disponível apenas para servidores do(a) {}.' % (competicao_desportiva.uo.nome))
    if (
        not Servidor.objects.em_exercicio().filter(pk=servidor.pk).exists()
        and not Servidor.objects.substitutos_ou_temporarios().filter(pk=servidor.pk)
        and not Servidor.objects.visitantes().filter(pk=servidor.pk)
    ):
        raise PermissionDenied('Competicao disponível apenas para servidores.')

    title = "Formulário de inscrição {}".format(competicao_desportiva.nome)

    inscrito = False
    if InscricaoCompeticaoDesportiva.objects.filter(servidor=servidor, competicao_desportiva=competicao_desportiva).exists():
        inscricao_desportiva = InscricaoCompeticaoDesportiva.objects.get(
            servidor=request.user.get_profile().pessoafisica.funcionario.servidor, competicao_desportiva=competicao_desportiva
        )
        inscrito = True
    else:
        inscricao_desportiva = InscricaoCompeticaoDesportiva(servidor=request.user.get_profile().pessoafisica.funcionario.servidor, competicao_desportiva=competicao_desportiva)
    calendario_jogos = Calendario()

    meses = []

    css = 'recesso'
    if competicao_desportiva.data_inicio_periodo_inscricoes and competicao_desportiva.data_fim_periodo_inscricoes:
        calendario_jogos.adicionar_evento_calendario(
            competicao_desportiva.data_inicio_periodo_inscricoes,
            competicao_desportiva.data_fim_periodo_inscricoes,
            "Período de inscrições {}".format(competicao_desportiva.nome),
            css,
        )
        ano_mes = competicao_desportiva.data_inicio_periodo_inscricoes.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)
        ano_mes = competicao_desportiva.data_fim_periodo_inscricoes.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)
    css = 'feriado'
    if competicao_desportiva.data_inicio_periodo_validacao and competicao_desportiva.data_fim_periodo_validacao:
        calendario_jogos.adicionar_evento_calendario(
            competicao_desportiva.data_inicio_periodo_validacao, competicao_desportiva.data_fim_periodo_validacao, "Período de validação {}".format(competicao_desportiva.nome), css
        )
        ano_mes = competicao_desportiva.data_inicio_periodo_validacao.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)
        ano_mes = competicao_desportiva.data_fim_periodo_validacao.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)

    css = 'recesso'
    if competicao_desportiva.data_inicio_confirmacao_inscritos and competicao_desportiva.data_fim_confirmacao_inscritos:
        calendario_jogos.adicionar_evento_calendario(
            competicao_desportiva.data_inicio_confirmacao_inscritos,
            competicao_desportiva.data_fim_confirmacao_inscritos,
            "Período de confirmação dos inscritos {}".format(competicao_desportiva.nome),
            css,
        )
        ano_mes = competicao_desportiva.data_inicio_confirmacao_inscritos.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)
        ano_mes = competicao_desportiva.data_fim_confirmacao_inscritos.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)

    css = 'feriado'
    if competicao_desportiva.data_inicio_reajustes and competicao_desportiva.data_fim_reajustes:
        calendario_jogos.adicionar_evento_calendario(
            competicao_desportiva.data_inicio_reajustes,
            competicao_desportiva.data_fim_reajustes,
            "Período de de reajustes(pelo representante do campus) {}".format(competicao_desportiva.nome),
            css,
        )
        ano_mes = competicao_desportiva.data_inicio_reajustes.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)
        ano_mes = competicao_desportiva.data_fim_reajustes.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)

    css = 'recesso'
    if competicao_desportiva.data_homologacao_inscricoes:
        calendario_jogos.adicionar_evento_calendario(
            competicao_desportiva.data_homologacao_inscricoes,
            competicao_desportiva.data_homologacao_inscricoes,
            "Data limíte de homologação e consolidação das inscricoes {}".format(competicao_desportiva.nome),
            css,
        )
        ano_mes = competicao_desportiva.data_homologacao_inscricoes.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)

    css = 'evento'
    if competicao_desportiva.data_inicio_periodo1_jogos and competicao_desportiva.data_fim_periodo1_jogos:
        calendario_jogos.adicionar_evento_calendario(
            competicao_desportiva.data_inicio_periodo1_jogos, competicao_desportiva.data_fim_periodo1_jogos, competicao_desportiva.nome, css
        )
        ano_mes = competicao_desportiva.data_inicio_periodo1_jogos.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)
        ano_mes = competicao_desportiva.data_fim_periodo1_jogos.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)

    if competicao_desportiva.data_inicio_periodo2_jogos and competicao_desportiva.data_fim_periodo2_jogos:
        calendario_jogos.adicionar_evento_calendario(
            competicao_desportiva.data_inicio_periodo2_jogos, competicao_desportiva.data_fim_periodo2_jogos, competicao_desportiva.nome, css
        )
        ano_mes = competicao_desportiva.data_inicio_periodo2_jogos.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)
        ano_mes = competicao_desportiva.data_fim_periodo2_jogos.strftime('%Y%m')
        if not ano_mes in meses:
            meses.append(ano_mes)

    calendarios = []
    for anomes in meses:
        calendarios.append(calendario_jogos.formato_mes(int(anomes[:4]), int(anomes[4:])))
    FormClass = GetInscricaoCompeticaoDesportivaForm(inscricao_desportiva, servidor, request)
    form = FormClass(request.POST or None, request.FILES or None, instance=inscricao_desportiva)
    municipios_pks = [9, 44, 8, 25, 17, 11, 2, 89, 1, 21, 318, 77]
    if form.is_valid():
        inscricao_desportiva.situacao = 1
        form.save()
        return httprr('..', 'Inscrição na competição realizada com sucesso!')
    return locals()


@rtr()
@permission_required('temp_rh2.pode_validar_inscricaocompeticaodesportiva')
def validar_homologar_inscricoes_desportivas(request, inscricao_pk):
    hoje = date.today()
    inscricao = get_object_or_404(InscricaoCompeticaoDesportiva.objects, pk=inscricao_pk)
    if (inscricao.competicao_desportiva.data_inicio_periodo_validacao <= hoje <= inscricao.competicao_desportiva.data_fim_periodo_validacao) or (
        inscricao.competicao_desportiva.data_inicio_confirmacao_inscritos <= hoje <= inscricao.competicao_desportiva.data_fim_confirmacao_inscritos
    ):
        FormClass = GetValidacaoInscricaoCompeticaoDesportivaForm()
    elif (inscricao.competicao_desportiva.data_inicio_reajustes <= hoje <= inscricao.competicao_desportiva.data_fim_reajustes) or (
        hoje == inscricao.competicao_desportiva.data_homologacao_inscricoes
    ):
        FormClass = GetValidacaoInscricaoCompeticaoDesportivaForm(etapa="homologacao")
    else:
        raise PermissionDenied('Não estamos em período de Validação nem de Homologação de inscrição no {}'.format(inscricao.competicao_desportiva))
    title = "Validar/Homologar Inscrição"
    form = FormClass(request.POST or None, instance=inscricao)
    if form.is_valid():
        if inscricao.situacao == 2:
            inscricao.homologado_por = None
            inscricao.homologado_em = None
            inscricao.rejeitado_em = None
            inscricao.rejeitado_por = None
            inscricao.observacao_rejeicao = ""

            inscricao.validado_por = request.user
            inscricao.validado_em = datetime.now()

        elif inscricao.situacao == 3:
            inscricao.homologado_por = request.user
            inscricao.homologado_em = datetime.now()
            inscricao.rejeitado_em = None
            inscricao.rejeitado_por = None
            inscricao.observacao_rejeicao = ""

        elif inscricao.situacao == 4:
            inscricao.homologado_por = None
            inscricao.homologado_em = None
            inscricao.validado_por = None
            inscricao.validado_em = None
            inscricao.rejeitado_por = request.user
            inscricao.rejeitado_em = datetime.now()

        form.save()
        return httprr('..', 'Inscrição {}.'.format(inscricao.get_situacao_display()))
    return locals()


# ==================================================================================
# Inscricao do curso SUAP
# ==================================================================================
@rtr()
@login_required
def listar_minhas_inscricoes(request):

    # Restrito a servidor
    # --------------------------------------------------------------------------------
    if not request.user.eh_servidor:
        raise PermissionDenied()

    title = 'Inscrição nos cursos de capacitação do SUAP'

    curso_suap_inscricao_aberta = CursoSuap.curso_suap_com_inscricao_aberta()
    curso_suap = None
    _curso_suap = CursoSuap.objects.filter(sigla='CS')
    curso_suap_ativo = False
    if _curso_suap.exists():
        curso_suap = _curso_suap[0]
        curso_suap_ativo = curso_suap.ativo

    curso_proc_doc_inscricao_aberta = CursoSuap.curso_procdoc_com_inscricao_aberta()
    curso_proc_doc = None
    _curso_proc_doc = CursoSuap.objects.filter(sigla='PD')
    curso_procdoc_ativo = False
    if _curso_proc_doc.exists():
        curso_proc_doc = _curso_proc_doc[0]
        curso_procdoc_ativo = curso_proc_doc.ativo

    existe_inscricao_curso_suap = InscricaoCursoSuap.existe_usuario_inscricao(curso_suap, request.user)
    inscricao_curso_suap = None
    if existe_inscricao_curso_suap:
        inscricao_curso_suap = InscricaoCursoSuap.get_usuario_inscricao(curso_suap, request.user)

    existe_inscricao_curso_proc_doc = InscricaoCursoSuap.existe_usuario_inscricao(curso_proc_doc, request.user)
    inscricao_curso_proc_doc = None
    if existe_inscricao_curso_proc_doc:
        inscricao_curso_proc_doc = InscricaoCursoSuap.get_usuario_inscricao(curso_proc_doc, request.user)

    return locals()


@rtr()
@transaction.atomic()
@login_required
def cancelar_inscricao_em_curso_suap(request):

    # Restrito a servidor
    # --------------------------------------------------------------------------------
    if not request.user.eh_servidor:
        raise PermissionDenied()

    # Verifica se existem cursos que podem receber inscricao ou ter inscricao cancelada
    # --------------------------------------------------------------------------------
    cursos_com_inscricao_aberta = CursoSuap.curso_suap_com_inscricao_aberta()
    curso_suap_ativo = CursoSuap.curso_suap_ativo()
    if not (cursos_com_inscricao_aberta and curso_suap_ativo):
        raise PermissionDenied()

    curso_suap = CursoSuap.objects.get(sigla='CS')
    existe_inscricao = InscricaoCursoSuap.existe_usuario_inscricao(curso_suap, request.user)
    if not existe_inscricao:
        raise PermissionDenied()

    inscricao = InscricaoCursoSuap.get_usuario_inscricao(curso_suap, request.user)

    title = 'Cancelar inscrição no {}'.format(curso_suap)

    form = FormConfirmaInscricaoCursoSuap(request.POST or None, request=request)
    if form.is_valid():
        inscricao.delete()

        log = LogInscricaoCursoSuap()
        log.log = '{} CANCELOU inscrição no {}'.format(request.user, curso_suap)
        log.save()

        return httprr("/temp_rh2/listar_minhas_inscricoes/", "Inscrição cancelada com sucesso.")

    return locals()


@rtr()
@transaction.atomic()
@login_required
def efetivar_inscricao_em_curso_suap(request):

    # Restrito a servidor
    # --------------------------------------------------------------------------------
    if not request.user.eh_servidor:
        raise PermissionDenied()

    # Verifica se existem cursos que podem receber inscricao ou ter inscricao cancelada
    # --------------------------------------------------------------------------------
    cursos_com_inscricao_aberta = CursoSuap.curso_suap_com_inscricao_aberta()
    curso_suap_ativo = CursoSuap.curso_suap_ativo()
    if not (cursos_com_inscricao_aberta and curso_suap_ativo):
        raise PermissionDenied()

    curso_suap = CursoSuap.objects.get(sigla='CS')
    existe_inscricao = InscricaoCursoSuap.existe_usuario_inscricao(curso_suap, request.user)
    if existe_inscricao:
        raise PermissionDenied()

    title = 'Efetivar inscrição no {}'.format(curso_suap)

    form = FormConfirmaInscricaoCursoSuap(request.POST or None, request=request)

    if form.is_valid():
        inscricao = InscricaoCursoSuap()
        inscricao.curso = curso_suap
        inscricao.usuario = request.user
        inscricao.data = datetime.now()
        inscricao.save()

        log = LogInscricaoCursoSuap()
        log.log = '{} EFETIVOU inscrição no {}'.format(request.user, curso_suap)
        log.save()

        return httprr("/temp_rh2/listar_minhas_inscricoes/", "Inscrição realizada com sucesso.")

    return locals()


@rtr()
@transaction.atomic()
@login_required
def cancelar_inscricao_em_curso_procdoc(request):

    # Restrito a servidor
    # --------------------------------------------------------------------------------
    if not request.user.eh_servidor:
        raise PermissionDenied()

    # Verifica se existem cursos que podem receber inscricao ou ter inscricao cancelada
    # --------------------------------------------------------------------------------
    cursos_com_inscricao_aberta = CursoSuap.curso_procdoc_com_inscricao_aberta()
    curso_procdoc_ativo = CursoSuap.curso_procdoc_ativo()
    if not (cursos_com_inscricao_aberta and curso_procdoc_ativo):
        raise PermissionDenied()

    curso_suap = CursoSuap.objects.get(sigla='PD')
    existe_inscricao = InscricaoCursoSuap.existe_usuario_inscricao(curso_suap, request.user)
    if not existe_inscricao:
        raise PermissionDenied()

    inscricao = InscricaoCursoSuap.get_usuario_inscricao(curso_suap, request.user)

    title = 'Cancelar inscrição no {}'.format(curso_suap)

    form = FormConfirmaInscricaoCursoSuap(request.POST or None, request=request)
    if form.is_valid():
        inscricao.delete()

        log = LogInscricaoCursoSuap()
        log.log = '{} CANCELOU inscrição no {}'.format(request.user, curso_suap)
        log.save()

        return httprr("/temp_rh2/listar_minhas_inscricoes/", "Inscrição cancelada com sucesso.")

    return locals()


@rtr()
@transaction.atomic()
@login_required
def efetivar_inscricao_em_curso_procdoc(request):

    # Restrito a servidor
    # --------------------------------------------------------------------------------
    if not request.user.eh_servidor:
        raise PermissionDenied()

    # Verifica se existem cursos que podem receber inscricao ou ter inscricao cancelada
    # --------------------------------------------------------------------------------
    cursos_com_inscricao_aberta = CursoSuap.curso_procdoc_com_inscricao_aberta()
    curso_procdoc_ativo = CursoSuap.curso_procdoc_ativo()
    if not (cursos_com_inscricao_aberta and curso_procdoc_ativo):
        raise PermissionDenied()

    curso_suap = CursoSuap.objects.get(sigla='PD')
    existe_inscricao = InscricaoCursoSuap.existe_usuario_inscricao(curso_suap, request.user)
    if existe_inscricao:
        raise PermissionDenied()

    title = 'Efetivar inscrição no {}'.format(curso_suap)

    form = FormConfirmaInscricaoCursoSuap(request.POST or None, request=request)

    if form.is_valid():
        inscricao = InscricaoCursoSuap()
        inscricao.curso = curso_suap
        inscricao.usuario = request.user
        inscricao.data = datetime.now()
        inscricao.save()

        log = LogInscricaoCursoSuap()
        log.log = '{} EFETIVOU inscrição no {}'.format(request.user, curso_suap)
        log.save()

        return httprr("/temp_rh2/listar_minhas_inscricoes/", "Inscrição realizada com sucesso.")

    return locals()


@rtr()
@permission_required('temp_rh2.change_inscricaocursosuap')
def enviar_email_confirmacao(request, inscricao_id):
    insc = InscricaoCursoSuap.objects.get(id=inscricao_id)

    ce = ConteudoEmail.objects.last()
    titulo = ce.assunto
    texto = ce.corpo

    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [insc.usuario.get_vinculo()], categoria='Inscrição para Curso SUAP')
    insc.enviou_email_solinsc = True
    insc.save()

    return httprr("/admin/temp_rh2/inscricaocursosuap/", "Email enviado com sucesso.")


@rtr()
@permission_required('temp_rh2.change_inscricaocursosuap')
def enviar_email_confirmacao_quem_nao_recebeu(request):
    ce = ConteudoEmail.objects.last()
    titulo = ce.assunto
    texto = ce.corpo

    inscricoes = InscricaoCursoSuap.objects.filter(enviou_email_solinsc=False)
    for insc in inscricoes:
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [insc.usuario.get_vinculo()], categoria='Inscrição para Curso SUAP')
        insc.enviou_email_solinsc = True
        insc.save()

    return httprr("/admin/temp_rh2/inscricaocursosuap/", "Emails enviados com sucesso.")


@rtr()
@permission_required('temp_rh2.change_inscricaocursosuap')
def enviar_email_teste(request):
    ce = ConteudoEmail.objects.last()
    titulo = ce.assunto
    texto = ce.corpo

    send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, ['eriton.farias@ifrn.edu.br'])
    send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, ['tarso.latorraca@ifrn.edu.br'])

    return httprr("/admin/temp_rh2/inscricaocursosuap/", "Email de TESTE enviado com sucesso.")


@rtr()
@permission_required('temp_rh2.change_inscricaocursosuap')
def enviar_email_confirmacao_para_todos(request):
    ce = ConteudoEmail.objects.last()
    titulo = ce.assunto
    texto = ce.corpo

    inscricoes = InscricaoCursoSuap.objects.all()
    for insc in inscricoes:
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [insc.usuario.get_vinculo()], categoria='Inscrição para Curso SUAP')

    return httprr("/admin/temp_rh2/inscricaocursosuap/", "Emails enviados para TODOS com sucesso.")


@rtr()
@permission_required('temp_rh2.change_inscricaocursosuap')
def enviar_email_confirmacao_para_quem_nao_confirmou(request):
    ce = ConteudoEmail.objects.last()
    titulo = ce.assunto
    texto = ce.corpo

    inscricoes = InscricaoCursoSuap.objects.filter(data_confirmacao_inscricao__isnull=True)
    for insc in inscricoes:
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [insc.usuario.get_vinculo()], categoria='Inscrição para Curso SUAP')
        insc.enviou_email_solinsc = True
        insc.save()

    return httprr("/admin/temp_rh2/inscricaocursosuap/", "Emails enviados com sucesso.")
