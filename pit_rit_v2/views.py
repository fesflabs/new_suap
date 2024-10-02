# -*- coding: utf-8 -*-


import datetime

from django.shortcuts import get_object_or_404
from django.conf import settings
from comum.models import Ano
from djtools.utils import rtr, httprr, documento
from edu.models import Professor
from pit_rit_v2.forms import (
    PlanoIndividualTrabalhoProfessorForm,
    RelatorioIndividualTrabalhoProfessorForm,
    EnviarPlanoForm,
    ParecerForm,
    AprovarRelatorioForm,
    EntregarRelatorioForm,
)
from pit_rit_v2.models import PlanoIndividualTrabalhoV2
from djtools import layout, documentos
from django.template.defaultfilters import pluralize
from django.contrib.auth.decorators import login_required


@documentos.emissao_documentos()
def emissao_documentos(request, data):
    for pit in PlanoIndividualTrabalhoV2.objects.filter(professor__vinculo__pessoa__id=request.user.get_vinculo().pessoa.id):
        data.append(
            (
                'Ensino',
                'PIT/RIT',
                'Planos Individuais de Trabalho',
                '{}/{}'.format(pit.ano_letivo, pit.periodo_letivo),
                '/pit_rit_v2/plano_atividade_docente_pdf/{}/'.format(pit.pk),
            )
        )
        if pit.data_envio_relatorio:
            data.append(
                (
                    'Ensino',
                    'PIT/RIT',
                    'Relatórios Individuais de Trabalho',
                    '{}/{}'.format(pit.ano_letivo, pit.periodo_letivo),
                    '/pit_rit_v2/relatorio_atividade_docente_pdf/{}/'.format(pit.pk),
                )
            )


@layout.quadro('Ensino', icone='pencil')
def index_quadros(quadro, request):
    if request.user.has_perm('pit_rit_v2.view_planoindividualtrabalhov2'):
        qtd_plano = PlanoIndividualTrabalhoV2.objects.filter(aprovado__isnull=True, avaliador__pessoa_fisica__user=request.user).count()
        if qtd_plano > 0:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Plano{} Individua{} de Trabalho'.format(pluralize(qtd_plano), pluralize(qtd_plano, 'l,is')),
                    subtitulo='Aguardando avaliação',
                    qtd=qtd_plano,
                    url='/admin/pit_rit_v2/planoindividualtrabalhov2/?tab=tab_aguardando_avaliacao',
                )
            )
        qtd_relatorio = PlanoIndividualTrabalhoV2.objects.filter(
            aprovado=True, relatorio_aprovado__isnull=True, data_envio_relatorio__isnull=False, avaliador_relatorio__pessoa_fisica__user=request.user
        ).count()
        if qtd_relatorio > 0:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Relatório{} Individua{} de Trabalho'.format(pluralize(qtd_relatorio), pluralize(qtd_relatorio, 'l,is')),
                    subtitulo='Aguardando avaliação',
                    qtd=qtd_relatorio,
                    url='/admin/pit_rit_v2/planoindividualtrabalhov2/?tab=tab_aguardando_avaliacao_relatorio',
                )
            )
        qtd_publicacao = PlanoIndividualTrabalhoV2.objects.filter(
            aprovado=True, relatorio_aprovado=True, publicado__isnull=True, responsavel_publicacao__pessoa_fisica__user=request.user
        ).count()
        if qtd_publicacao > 0:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Relatório{} Individua{} de Trabalho'.format(pluralize(qtd_publicacao), pluralize(qtd_publicacao, 'l,is')),
                    subtitulo='Aguardando publicação',
                    qtd=qtd_publicacao,
                    url='/admin/pit_rit_v2/planoindividualtrabalhov2/?tab=tab_aguardando_publicacao',
                )
            )

    return quadro


@rtr()
def cadastrar_plano_individual_trabalho(request, pk, ano_letivo, periodo_letivo):
    professor = get_object_or_404(Professor, pk=pk)
    if request.user != professor.vinculo.user:
        return httprr('/', 'Você não tem permissão para acessar essa página', tag='error')
    ano_letivo = get_object_or_404(Ano, ano=ano_letivo)
    qs = PlanoIndividualTrabalhoV2.objects.filter(professor=professor, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)
    instance = qs.first() or PlanoIndividualTrabalhoV2.objects.create(professor=professor, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)
    title = str(instance)
    initial = dict()
    ch_aulas = instance.get_cargas_horarias()[1]
    if instance.ch_preparacao_manutencao_ensino == 0:
        initial = dict(ch_preparacao_manutencao_ensino=ch_aulas)
        instance.ch_preparacao_manutencao_ensino = ch_aulas
    form = PlanoIndividualTrabalhoProfessorForm(data=request.POST or None, instance=instance, initial=initial)
    form.fields[
        'ch_preparacao_manutencao_ensino'
    ].help_text = 'Informe a carga horária que você utilizará para a preparação e manutenção das aulas com um limite de até {} hora(s), que corresponde a sua carga horária de regência no período.'.format(
        ch_aulas
    )
    if not settings.PERMITE_ALTERACAO_CH_PREPARACAO_AULAS_PIT:
        form.fields['ch_preparacao_manutencao_ensino'].widget.attrs.update(readonly='readonly')
        form.fields['ch_preparacao_manutencao_ensino'].help_text = ''
    form.fields['ch_preparacao_manutencao_ensino'].initial = ch_aulas
    if form.is_valid():
        form.save()
        return httprr('..', 'Plano individual de trabalho cadastrado/atualizado com sucesso.')
    return locals()


@rtr()
@login_required()
def preencher_relatorio_individual_trabalho(request, pk):
    title = 'Relatório Individual de Trabalho'
    obj = get_object_or_404(PlanoIndividualTrabalhoV2, pk=pk)
    if not obj.pode_preencher_relatorio(request.user):
        return httprr('/', 'Você não tem permissão para acessar essa página', tag='error')
    form = RelatorioIndividualTrabalhoProfessorForm(data=request.POST or None, instance=obj, files=request.FILES or None)
    if form.is_valid():
        form.save()
        return httprr('..', 'Relatório individual de trabalho preenchido com sucesso.')
    return locals()


@rtr()
@login_required()
def enviar_plano(request, pk):
    title = 'Enviar Plano Individual de Trabalho'
    pit = get_object_or_404(PlanoIndividualTrabalhoV2, pk=pk)
    if not pit.pode_enviar_plano(request.user) and not pit.pode_alterar_avaliador_plano(request.user):
        return httprr('/', 'Você não tem permissão para acessar essa página', tag='error')
    form = EnviarPlanoForm(data=request.POST or None, instance=pit)
    if form.is_valid():
        form.instance.data_envio = datetime.datetime.now()
        form.save()
        return httprr('..', 'Plano enviado com sucesso.')
    return locals()


@rtr()
@login_required()
def aprovar_plano(request, pk):
    title = 'Aprovar Plano'
    pit = get_object_or_404(PlanoIndividualTrabalhoV2, pk=pk)
    if not pit.pode_avaliar_plano(request.user):
        return httprr('/', 'Você não tem permissão para acessar essa página', tag='error')
    form = ParecerForm(data=request.POST or None, request=request)
    if form.is_valid():
        pit.aprovar_plano(request.user, form.instance)
        return httprr('..', 'Plano aprovado com sucesso.')
    return locals()


@rtr()
@login_required()
def devolver_plano(request, pk):
    title = 'Devolver Plano'
    pit = get_object_or_404(PlanoIndividualTrabalhoV2, pk=pk)
    if not pit.pode_avaliar_plano(request.user) and not pit.pode_desfazer_aprovacao_plano(request.user):
        return httprr('/', 'Você não tem permissão para acessar essa página', tag='error')
    form = ParecerForm(data=request.POST or None, request=request)
    if form.is_valid():
        pit.devolver_plano(request.user, form.instance)
        return httprr('..', 'Plano devolvido com sucesso.')
    return locals()


@rtr()
@login_required()
def entregar_relatorio(request, pk):
    pit = get_object_or_404(PlanoIndividualTrabalhoV2, pk=pk)
    if not pit.pode_enviar_relatorio(request.user) and not pit.pode_alterar_avaliador_relatorio(request.user):
        return httprr('/', 'Você não tem permissão para acessar essa página', tag='error')
    form = EntregarRelatorioForm(data=request.POST or None, instance=pit)
    if form.is_valid():
        form.instance.data_envio_relatorio = datetime.datetime.now()
        form.save()
        return httprr('..', 'Plano enviado com sucesso.')
    return locals()


@rtr()
@login_required()
def aprovar_relatorio(request, pk):
    title = 'Aprovar Relatório'
    pit = get_object_or_404(PlanoIndividualTrabalhoV2, pk=pk)
    if not pit.pode_avaliar_relatorio(request.user):
        return httprr('/', 'Você não tem permissão para acessar essa página', tag='error')
    form = AprovarRelatorioForm(data=request.POST or None, request=request)
    if form.is_valid():
        pit.aprovar_relatorio(request.user, form.instance, form.cleaned_data.get('responsavel_publicacao'))
        return httprr('..', 'Relatório aprovado com sucesso.')
    return locals()


@rtr()
@login_required()
def devolver_relatorio(request, pk):
    title = 'Devolver Relatório'
    pit = get_object_or_404(PlanoIndividualTrabalhoV2, pk=pk)
    if not pit.pode_avaliar_relatorio(request.user) and not pit.pode_desfazer_aprovacao_relatorio(request.user):
        return httprr('/', 'Você não tem permissão para acessar essa página', tag='error')
    form = ParecerForm(data=request.POST or None, request=request)
    if form.is_valid():
        pit.devolver_relatorio(request.user, form.instance)
        return httprr('..', 'Relatório devolvido com sucesso.')
    return locals()


def relatorio_atividade_docente_pdf(request, pk):
    return plano_atividade_docente_pdf(request, pk, True)


@documento()
@rtr()
@login_required()
def plano_atividade_docente_pdf(request, pk, relatorio=False):
    title = relatorio and 'RELATÓRIO INDIVIDUAL DE TRABALHO' or 'PLANO INDIVIDUAL DE TRABALHO'
    pit = get_object_or_404(PlanoIndividualTrabalhoV2, pk=pk)
    uo = (pit.professor.vinculo.setor and pit.professor.vinculo.setor.uo) or (pit.professor.vinculo.relacionamento.setor_lotacao and pit.professor.vinculo.relacionamento.setor_lotacao.uo.equivalente) or None

    hoje = datetime.date.today()
    is_servidor = pit.professor.vinculo.eh_servidor()
    funcao_servidor = None
    url = None

    if is_servidor:
        data_inicio = None
        data_fim = None

        servidor = pit.professor.vinculo.relacionamento
        historico_funcoes = servidor.historico_funcao(data_inicio=data_inicio, data_fim=data_fim)
        funcao_servidor = historico_funcoes.last().funcao_display if historico_funcoes.exists() else None
        carga_horaria_servidor = servidor.jornada_trabalho.nome

    vinculos_diarios = pit.get_vinculo_diarios()
    vinculos_diarios_regulares = pit.get_vinculo_diarios(False)
    vinculos_diarios_fics = pit.get_vinculo_diarios(True)
    vinculos_turmas_minicurso = pit.get_vinculos_minicurso()
    diarios_especiais = pit.get_vinculos_diarios_especiais()

    ch_semanal_aulas, ch_aulas, ch_semanal_diarios, ch_semanal_diarios_fic, ch_semanal_minicursos, ch_semanal_diarios_especiais, ch_preparacao_manutencao_ensino, ch_apoio_ensino, ch_programas_projetos_ensino, ch_orientacao_alunos, ch_reunioes, ch_pesquisa, ch_extensao, ch_gestao, ch_total = (
        pit.get_cargas_horarias()
    )
    ch_ensino = ch_aulas + ch_preparacao_manutencao_ensino + ch_apoio_ensino + ch_programas_projetos_ensino + ch_orientacao_alunos + ch_reunioes
    ch_resumo = [
        (ch_aulas, 'AULAS'),
        (ch_preparacao_manutencao_ensino, 'PREPARAÇÃO E MANUTENÇÃO DO ENSINO'),
        (ch_apoio_ensino, 'APOIO AO ENSINO'),
        (ch_programas_projetos_ensino, 'PROGRAMAS OU PROJETOS DE ENSINO'),
        (ch_orientacao_alunos, 'ATENDIMENTO, ACOMPANHAMENTO, AVALIAÇÃO E ORIENTAÇÃO DE ALUNOS'),
        (ch_reunioes, 'REUNIÕES PEDAGÓGICAS, DE GRUPO E AFINS'),
        (ch_pesquisa, 'PESQUISA E INOVAÇÃO'),
        (ch_extensao, 'EXTENSÃO'),
        (ch_gestao, 'GESTÃO E REPRESENTAÇÃO INSTITUCIONAL'),
    ]

    return locals()
