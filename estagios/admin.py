import datetime

from django.urls import path
from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.db.models.aggregates import Max
from django.utils.safestring import mark_safe

from comum.utils import get_uo
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter, DateRangeListFilter
from djtools.templatetags.filters import in_group
from djtools.utils import httprr
from estagios import tasks
from estagios.forms import (
    PraticaProfissionalForm,
    OfertaPraticaProfissionalForm,
    VisitaPraticaProfissionalForm,
    AtLeastOneFormSet,
    AprendizagemForm,
    AtividadeProfissionalEfetivaForm,
)
from estagios.models import (
    PraticaProfissional,
    OfertaPraticaProfissional,
    Atividade,
    VisitaPraticaProfissional,
    TipoRemuneracao,
    SituacaoAtividade,
    Aprendizagem,
    ModuloAprendizagem,
    SolicitacaoCancelamentoEncerramentoEstagio,
    AtividadeProfissionalEfetiva,
)
from estagios.utils import (
    SituacaoUltimaMatriculaPeriodoFilter,
    TipoAditivoContratualFilter,
    PossuiAditivoContratualFilter,
    SituacaoUltimaMatriculaPeriodoAprendizagemFilter,
    get_situacoes_irregulares,
    visualiza_todos_estagios_afins,
)


class TipoRemuneracaoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']


admin.site.register(TipoRemuneracao, TipoRemuneracaoAdmin)


class SituacaoAtividadeAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']


admin.site.register(SituacaoAtividade, SituacaoAtividadeAdmin)


class AtividadeInline(admin.TabularInline):
    model = Atividade
    extra = 1
    fields = ['descricao']
    formset = AtLeastOneFormSet

    @property
    def media(self):
        _media = super().media
        _media._js.append('/static/estagios/js/AtividadeInline.js')
        return _media


class PraticaProfissionalAdmin(ModelAdminPlus):
    form = PraticaProfissionalForm
    list_display_icons = True
    export_to_xls = True
    list_per_page = 25
    list_display = [
        'tipo',
        'aluno',
        'get_situacao_aluno',
        'get_situacao_ultima_matricula_periodo',
        'get_campus',
        'empresa',
        'orientador',
        'data_inicio',
        'data_prevista_fim',
        'data_fim',
        'get_aditivo',
    ]
    search_fields = (
        'empresa__pessoafisica__cpf',
        'empresa__pessoafisica__nome',
        'empresa__pessoajuridica__cnpj',
        'aluno__matricula',
        'empresa__pessoajuridica__nome',
        'empresa__pessoajuridica__nome',
        'aluno__pessoa_fisica__nome',
        'aluno__pessoa_fisica__nome_registro',
        'orientador__vinculo__user__username',
        'orientador__vinculo__pessoa__nome',
    )
    list_filter = [
        CustomTabListFilter,
        'obrigatorio',
        'aluno__situacao',
        SituacaoUltimaMatriculaPeriodoFilter,
        'aluno__curso_campus__diretoria__setor__uo',
        PossuiAditivoContratualFilter,
        TipoAditivoContratualFilter,
        ('data_inicio', DateRangeListFilter),
        ('data_prevista_fim', DateRangeListFilter),
        ('data_fim', DateRangeListFilter),
    ]
    inlines = [AtividadeInline]
    show_count_on_tabs = True
    fieldsets = PraticaProfissionalForm.fieldsets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not visualiza_todos_estagios_afins(request.user):
            uo = get_uo(request.user)
            if not in_group(request.user, ['Coordenador de Estágio', 'Visualizador de Estágios']):
                return qs.filter(aluno__curso_campus__coordenador_id=request.user.get_profile().pk) | qs.filter(aluno__curso_campus__coordenador_2_id=request.user.get_profile().pk)
            else:
                return qs.filter(aluno__curso_campus__diretoria__setor__uo=uo)
        return qs

    def get_tabs(self, request):
        return [
            'tab_em_curso',
            'tab_matriculas_irregulares',
            'tab_atingiu_data_encerramento',
            # 'tab_com_visita_pendente',
            'tab_aguardando_relatorio_estagiario',
            'tab_aguardando_relatorio_supervisor',
            'tab_apto_conclusao',
            'tab_concluido',
        ]

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if request.GET.get('tab') and request.GET.get('tab') == 'tab_matriculas_irregulares':
            list_display += ('prazo_final_regularizacao_matricula_irregular',)
        return list_display

    def tab_em_curso(self, request, queryset):
        return queryset.filter(data_fim__isnull=True, data_prevista_fim__gte=datetime.date.today())

    tab_em_curso.short_description = 'Em Andamento'

    def tab_matriculas_irregulares(self, request, queryset):
        return (
            queryset.filter(data_fim__isnull=True, data_prevista_fim__gte=datetime.date.today())
            .filter(aluno__situacao__in=get_situacoes_irregulares())
            .distinct()
            .order_by('-prazo_final_regularizacao_matricula_irregular')
        )

    tab_matriculas_irregulares.short_description = 'Matrículas Irregulares'

    def tab_atingiu_data_encerramento(self, request, queryset):
        return queryset.filter(data_prevista_fim__lt=datetime.date.today(), data_fim__isnull=True)

    tab_atingiu_data_encerramento.short_description = 'Atingiu a Data de Prevista de Encerramento'

    def tab_com_visita_pendente(self, request, queryset):
        qs = queryset.filter(data_fim__isnull=True, data_inicio__lte=datetime.date.today())
        qs = qs.filter(pendente_visita=True)
        return qs

    tab_com_visita_pendente.short_description = 'Pendência de Visita'

    def tab_aguardando_relatorio_estagiario(self, request, queryset):
        qs = queryset.filter(data_fim__isnull=True, data_inicio__lte=datetime.date.today())
        qs = qs.filter(pendente_relatorio_estagiario=True)
        return qs

    tab_aguardando_relatorio_estagiario.short_description = 'Pendência de Relatório de Atividades do Estagiário'

    def tab_aguardando_relatorio_supervisor(self, request, queryset):
        qs = queryset.filter(data_fim__isnull=True, data_inicio__lte=datetime.date.today())
        qs = qs.filter(pendente_relatorio_supervisor=True)
        return qs

    tab_aguardando_relatorio_supervisor.short_description = 'Pendência de Relatório de Atividades do Supervisor'

    def tab_apto_conclusao(self, request, queryset):
        return queryset.filter(
            data_fim__isnull=True, pendente_visita=False, pendente_relatorio_estagiario=False, pendente_relatorio_supervisor=False, data_prevista_fim__lt=datetime.date.today()
        )

    tab_apto_conclusao.short_description = 'Apto para Encerramento'

    def tab_concluido(self, request, queryset):
        return queryset.filter(status__in=[PraticaProfissional.STATUS_CONCLUIDO, PraticaProfissional.STATUS_RESCINDIDO])

    tab_concluido.short_description = 'Encerrados'

    def response_add(self, request, obj):
        if obj.data_prevista_fim < datetime.date.today():
            self.message_user(
                request,
                'Cadastro realizado com sucesso. Foi cadastrado um estágio com data prevista de encerramento anterior a data de '
                'hoje, por isso você foi encaminhado para esta tela de encerramento.',
            )
            return HttpResponseRedirect('/estagios/encerrar_pratica_profissional/{}/'.format(obj.pk))
        else:
            self.message_user(request, 'Cadastro realizado com sucesso.')
            return HttpResponseRedirect('/admin/estagios/praticaprofissional/')

    def to_xls(self, request, queryset, processo):
        header = [
            '#',
            'Tipo',
            'Estagiário',
            'Situação de Matrícula',
            'E-mail Pessoal do Estagiário',
            'E-mail Acadêmico do Estagiário',
            'Data de Expedição do Diploma',
            'Período de Referência',
            'Percentual de Progresso no Curso',
            'Percentual de Disciplinas Obrigatórias Cursadas',
            'Curso',
            'Estrutura de Curso',
            'Modalidade',
            'Período Mínimo para Estágio Obrigatório',
            'Período Mínimo para Estágio Não Obrigatório',
            'Campus',
            'Concedente',
            'Concedente CNPJ',
            'Concedente Endereço',
            'Concedente Bairro',
            'Concedente Cidade',
            'Nome do Supervisor',
            'E-mail do Supervisor',
            'Telefone do Supervisor',
            'Nome do Orientador',
            'Matrícula do Orientador',
            'E-mail do Orientador',
            'Nome do Agente de Integração',
            'CNPJ do Agente de Integração',
            'Data de Início',
            'Data Prevista de Fim',
            'Nome da Seguradora',
            'Número da Apólice do Seguro',
            'Status',
            'Visitas Realizadas',
            'Visitas Justificadas',
            'Visitas a Vencer',
            'Visitas Não Realizadas',
            'Resumo de Pendências',
            'Data de Fim',
            'Tem aditivo?',
            'Tipos de Aditivo',
            'Encerramento por',
            'Motivação do Desligamento/ Encerramento',
            'Motivo da Rescisão',
            'Média das Notas de Avaliações Semestrais do Supervisor',
            'C.H. Final',
            'Foi/será contratado pela concedente?',
        ]

        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            tem_aditivo = obj.estagioaditivocontratual_set.exists() and 'Sim' or 'Não'
            tipos_aditivo = set()
            for aditivo in obj.estagioaditivocontratual_set.all():
                tipos_aditivo = tipos_aditivo.union(aditivo.tipos_aditivo.all())
            lista = []
            for tipo_aditivo in tipos_aditivo:
                lista.append(str(tipo_aditivo))
            tipos_aditivo = ', '.join(lista)
            if obj.aluno.matriz:
                percentual_carga_horaria_cumprida = obj.aluno.get_percentual_carga_horaria_cumprida()
                percentual_disciplinas_obrigatorias = (
                    obj.aluno.get_ch_componentes_regulares_obrigatorios_cumprida() * 100 / obj.aluno.get_ch_componentes_regulares_obrigatorios_esperada()
                )
                periodo_minimo_estagio_obrigatorio = obj.aluno.matriz.periodo_minimo_estagio_obrigatorio
                periodo_minimo_estagio_nao_obrigatorio = obj.aluno.matriz.periodo_minimo_estagio_nao_obrigatorio
            else:
                percentual_carga_horaria_cumprida = 'Aluno sem matriz'
                percentual_disciplinas_obrigatorias = 'Aluno sem matriz'
                periodo_minimo_estagio_obrigatorio = 'Aluno sem matriz'
                periodo_minimo_estagio_nao_obrigatorio = 'Aluno sem matriz'

            concedente = obj.empresa.nome
            concedente_cnpj = obj.empresa.pessoajuridica.cnpj if hasattr(obj.empresa, 'pessoajuridica') else ''
            endereco = ''
            bairro = ''
            cidade = ''
            pessoa_endereco = obj.empresa.pessoaendereco_set.all().first()
            if pessoa_endereco:
                endereco = '{} {}'.format(pessoa_endereco.logradouro or '', pessoa_endereco.numero or '')
                bairro = pessoa_endereco.bairro or ''
                cidade = pessoa_endereco.municipio or ''
            if obj.motivacao_desligamento_encerramento == PraticaProfissional.MOTIVO_CONTRATACAO:
                foi_sera_contrado = 'Sim'
            elif obj.motivacao_desligamento_encerramento is None:
                foi_sera_contrado = '-'
            else:
                foi_sera_contrado = 'Não'

            agente_integracao = obj.agente_integracao.nome if obj.agente_integracao else ''
            agente_integracao_cnpj = obj.agente_integracao.cnpj if obj.agente_integracao else ''

            # Visitas
            visitas_realizadas = visitas_nao_realizadas = visitas_justificadas = visitas_pendentes = 0
            for periodo in obj.get_periodos_trimestrais():
                if periodo['visitas']:
                    visitas_realizadas += 1
                elif periodo['justificativa']:
                    visitas_justificadas += 1
                else:
                    # Não deve exibir visitas canceladas (não foi encerrado ou foi encerrado mas o trimestre foi anterior ao encerramento)
                    if not obj.data_fim or obj.data_fim and periodo['fim'] < obj.data_fim:
                        if periodo['fim'] < datetime.date.today():
                            visitas_nao_realizadas += 1
                        else:
                            # Visitas a Vencer
                            visitas_pendentes += 1

            pendencias = []
            if obj.ha_pendencia_de_visita():
                pendencias.append('de visita do orientador')
            if obj.ha_pendencia_relatorio_estagiario():
                pendencias.append('de relatório do estagiário')
            if obj.ha_pendencia_relatorio_supervisor():
                pendencias.append('de relatório do supervisor')
            if pendencias:
                pendencias = ', '.join(pendencias)
                retorno = 'Pendências: {}'.format(pendencias)
            else:
                retorno = 'Sem Pendências.'

            row = [
                idx + 1,
                obj.get_tipo_display(),
                obj.aluno,
                obj.aluno.situacao.descricao,
                obj.aluno.pessoa_fisica.email_secundario,
                obj.aluno.email_academico,
                obj.aluno.data_expedicao_diploma,
                obj.aluno.periodo_atual,
                percentual_carga_horaria_cumprida,
                percentual_disciplinas_obrigatorias,
                obj.aluno.curso_campus.descricao_historico,
                obj.aluno.matriz.estrutura.descricao,
                obj.aluno.curso_campus.modalidade.descricao,
                periodo_minimo_estagio_obrigatorio,
                periodo_minimo_estagio_nao_obrigatorio,
                obj.aluno.curso_campus.diretoria.setor.uo,
                concedente,
                concedente_cnpj,
                endereco,
                bairro,
                cidade,
                obj.nome_supervisor,
                obj.email_supervisor,
                obj.telefone_supervisor,
                obj.orientador.get_nome(),
                obj.orientador.get_matricula(),
                obj.orientador.vinculo.user.email,
                agente_integracao,
                agente_integracao_cnpj,
                obj.data_inicio,
                obj.data_prevista_fim,
                obj.nome_da_seguradora,
                obj.numero_seguro,
                obj.get_status_display(),
                visitas_realizadas,
                visitas_justificadas,
                visitas_pendentes,
                visitas_nao_realizadas,
                retorno,
                obj.data_fim,
                tem_aditivo,
                tipos_aditivo,
                obj.get_movito_encerramento_display(),
                obj.get_motivacao_desligamento_encerramento_display(),
                obj.motivo_rescisao,
                obj.get_nota_media_relatorios_supervisor,
                obj.ch_final,
                foi_sera_contrado,
            ]
            rows.append(row)
        return rows

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        if in_group(request.user, ['Coordenador de Estágio Sistêmico', 'Coordenador de Estágio']):
            items.append(dict(url='/admin/estagios/praticaprofissional/notificacao/', label='Enviar Notificações de Pendências'))
        return items

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('notificacao/', self.admin_site.admin_view(self.notificacao))]
        return my_urls + urls

    def notificacao(self, request):
        qs = self.get_queryset(request).filter(data_fim__isnull=True)
        for obj in qs.distinct().order_by('-id'):
            obj.notificar()
        return httprr(request.META.get('HTTP_REFERER', '..'), 'Foram enviados e-mails referentes aos estágios com ' 'pendências.')


admin.site.register(PraticaProfissional, PraticaProfissionalAdmin)


class OfertaPraticaProfissionalAdmin(ModelAdminPlus):
    form = OfertaPraticaProfissionalForm
    list_display_icons = True
    export_to_xls = True
    list_per_page = 25
    list_display = ['concedente', 'data_inicio', 'data_fim', 'qtd_vagas', 'ch_semanal']
    list_filter = [CustomTabListFilter]
    search_fields = ('concedente',)
    show_count_on_tabs = True

    def get_tabs(self, request):
        return ['tab_em_andamento']

    def tab_em_andamento(self, request, queryset):
        hoje = datetime.date.today()
        return queryset.filter(data_fim__gte=hoje, data_inicio__lte=hoje)

    tab_em_andamento.short_description = 'Com Inscrições em andamento'

    fieldsets = OfertaPraticaProfissionalForm.fieldsets

    def response_add(self, request, obj, post_url_continue=None):
        if obj.data_fim >= datetime.date.today():
            return tasks.enviar_emails(obj)
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if obj.data_fim >= datetime.date.today():
            return tasks.enviar_emails(obj)
        return super().response_change(request, obj)


admin.site.register(OfertaPraticaProfissional, OfertaPraticaProfissionalAdmin)


class VisitaPraticaProfissionalAdmin(ModelAdminPlus):
    form = VisitaPraticaProfissionalForm
    exclude = ('pratica_profissional', 'orientador,')
    fieldsets = VisitaPraticaProfissionalForm.fieldsets

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        qs = qs.filter(orientador__vinculo__user=request.user)
        return qs


admin.site.register(VisitaPraticaProfissional, VisitaPraticaProfissionalAdmin)


class AprendizagemAdmin(ModelAdminPlus):
    form = AprendizagemForm
    fieldsets = AprendizagemForm.fieldsets
    exclude = ('encerramento_por', 'motivo_encerramento', 'motivacao_rescisao', 'data_encerramento', 'ch_final', 'laudo_avaliacao')

    list_display_icons = True
    export_to_xls = True
    list_per_page = 25
    list_display = [
        'aprendiz',
        'get_situacao_aluno',
        'get_situacao_ultima_matricula_periodo',
        'get_campus',
        'empresa',
        'orientador',
        'data_inicio',
        'data_prevista_encerramento',
        'resumo_pendencias',
        'data_encerramento',
        'get_aditivo',
    ]
    search_fields = (
        'aprendiz__matricula',
        'empresa__nome',
        'empresa__cnpj',
        'aprendiz__pessoa_fisica__nome',
        'aprendiz__pessoa_fisica__nome_registro',
        'orientador__vinculo__user__username',
        'orientador__vinculo__pessoa__nome',
    )
    list_filter = [CustomTabListFilter, 'aprendiz__situacao', SituacaoUltimaMatriculaPeriodoAprendizagemFilter, 'aprendiz__curso_campus__diretoria__setor__uo']

    show_count_on_tabs = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not visualiza_todos_estagios_afins(request.user):
            uo = get_uo(request.user)
            if not in_group(request.user, ['Coordenador de Estágio', 'Visualizador de Estágios']):
                return qs.filter(aprendiz__curso_campus__coordenador_id=request.user.get_profile().pk) | qs.filter(aprendiz__curso_campus__coordenador_2_id=request.user.get_profile().pk)
            else:
                return qs.filter(aprendiz__curso_campus__diretoria__setor__uo=uo)
        return qs

    def get_tabs(self, request):
        return [
            'tab_em_curso',
            'tab_matriculas_irregulares',
            'tab_atingiu_data_encerramento',
            # 'tab_com_visita_pendente',
            'tab_aguardando_relatorio_aprendiz',
            'tab_aguardando_relatorio_monitor',
            'tab_apto_conclusao',
            'tab_concluido',
        ]

    def tab_em_curso(self, request, queryset):
        qs = queryset.filter(data_encerramento__isnull=True).annotate(fim=Max('moduloaprendizagem__fim')).exclude(fim__lt=datetime.date.today())
        return qs

    tab_em_curso.short_description = 'Em Andamento'

    def tab_matriculas_irregulares(self, request, queryset):
        qs = (
            queryset.filter(data_encerramento__isnull=True)
            .annotate(fim=Max('moduloaprendizagem__fim'))
            .exclude(fim__lt=datetime.date.today())
            .filter(aprendiz__situacao__in=get_situacoes_irregulares())
        )
        return qs

    tab_matriculas_irregulares.short_description = 'Matrículas Irregulares'

    def tab_atingiu_data_encerramento(self, request, queryset):
        qs = queryset.filter(data_encerramento__isnull=True).exclude(moduloaprendizagem__fim__gte=datetime.date.today())
        return qs.distinct()

    tab_atingiu_data_encerramento.short_description = 'Atingiu a Data de Prevista de Encerramento'

    # def tab_com_visita_pendente(self, request, queryset):
    # qs = queryset.filter(data_encerramento__isnull=True, moduloaprendizagem__fim__lt=datetime.date.today(), moduloaprendizagem__visitaaprendizagem__isnull=True, moduloaprendizagem__justificativavisitamoduloaprendizagem__isnull=True)
    # return qs.distinct()
    # tab_com_visita_pendente.short_description = u'Pendência de Visita'

    def tab_aguardando_relatorio_aprendiz(self, request, queryset):
        qs = queryset.filter(data_encerramento__isnull=True)
        return (
            qs.filter(moduloaprendizagem__fim__lt=datetime.date.today())
            .exclude(moduloaprendizagem__relatoriomoduloaprendizagem__eh_relatorio_do_empregado_monitor=False)
            .distinct()
        )

    tab_aguardando_relatorio_aprendiz.short_description = 'Pendência de Relatório de Atividades do Aprendiz'

    def tab_aguardando_relatorio_monitor(self, request, queryset):
        qs = queryset.filter(data_encerramento__isnull=True)
        return (
            qs.filter(moduloaprendizagem__fim__lt=datetime.date.today()).exclude(moduloaprendizagem__relatoriomoduloaprendizagem__eh_relatorio_do_empregado_monitor=True).distinct()
        )

    tab_aguardando_relatorio_monitor.short_description = 'Pendência de Relatório de Atividades do Empregado Monitor'

    def tab_apto_conclusao(self, request, queryset):
        qs = queryset.filter(data_encerramento__isnull=True)
        mas = ModuloAprendizagem.objects.filter(aprendizagem__in=qs, fim__gte=datetime.date.today())
        qs = qs.exclude(moduloaprendizagem__id__in=mas).distinct()
        # tem ao menos uma visita ou todos os módulos tem justificativa de decurso
        # qs = qs.filter(visitaaprendizagem__isnull=False) | qs.exclude(moduloaprendizagem__justificativavisitamoduloaprendizagem__isnull=True)
        # qs = qs.distinct()

        nao_tem_relatorio_algum = ModuloAprendizagem.objects.filter(aprendizagem__in=qs, relatoriomoduloaprendizagem__isnull=True)
        qs = qs.exclude(moduloaprendizagem__in=nao_tem_relatorio_algum)
        # excluir quem nao tem relatorio aprendiz
        mas_sem_relatorio_aprendiz = ModuloAprendizagem.objects.filter(aprendizagem__in=qs).exclude(relatoriomoduloaprendizagem__eh_relatorio_do_empregado_monitor=False)
        qs = qs.exclude(moduloaprendizagem__id__in=mas_sem_relatorio_aprendiz)

        # excluir quem nao tem relatorio monitor
        mas_sem_relatorio_monitor = ModuloAprendizagem.objects.filter(aprendizagem__in=qs).exclude(relatoriomoduloaprendizagem__eh_relatorio_do_empregado_monitor=True)
        qs = qs.exclude(moduloaprendizagem__id__in=mas_sem_relatorio_monitor)

        return qs.distinct()

    tab_apto_conclusao.short_description = 'Apto para Conclusão'

    def tab_concluido(self, request, queryset):
        return queryset.filter(data_encerramento__isnull=False)

    tab_concluido.short_description = 'Concluídos'

    def to_xls(self, request, queryset, processo):
        header = [
            '#',
            'Matrícula',
            'Nome',
            'Data de Nascimento',
            'Situação da Matrícula no Curso',
            'Situação da Matrícula no Período',
            'E-mail Pessoal do Aprendiz',
            'E-mail Acadêmico do Aprendiz',
            'Data de Expedição do Diploma',
            'Período de Referência',
            'Percentual de Progresso no Curso',
            'Percentual de Disciplinas Obrigatórias Cursadas',
            'Curso',
            'Estrutura de Curso',
            'Modalidade',
            'Campus',
            'Concedente',
            'Nome do Empregado Monitor',
            'E-mail do Empregado Monitor',
            'Telefone do Empregado Monitor',
            'Nome do Orientador',
            'Matrícula do Orientador',
            'Email do Orientador',
            'Data de Início',
            'Data Prevista para Encerramento',
            'Módulo I Data de Início',
            'Módulo I Data de Fim',
            'Módulo II Data de Início',
            'Módulo II Data de Fim',
            'Módulo III Data de Início',
            'Módulo III Data de Fim',
            'Módulo IV Data de Início',
            'Módulo IV Data de Fim',
            'Tem aditivo?',
            'Tipos de Aditivo',
            'Encerramento por',
            'Motivação do Desligamento/ Encerramento',
            'Motivo da Rescisão',
            'Média das Notas de Avaliações Semestrais Empregado Monitor',
            'Resumo de Pendências',
            'C.H. Final',
            'Foi/será contratado pela concedente?',
        ]
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            tipos_aditivo = set()
            for aditivo in obj.aditivocontratualaprendizagem_set.all():
                tipos_aditivo = tipos_aditivo.union(aditivo.tipos_aditivo.all())
            lista = []
            for tipo_aditivo in tipos_aditivo:
                lista.append(str(tipo_aditivo))
            tipos_aditivo = ', '.join(lista)
            if obj.aprendiz.matriz:
                percentual_carga_horaria_cumprida = obj.aprendiz.get_percentual_carga_horaria_cumprida()
                percentual_disciplinas_obrigatorias = (
                    obj.aprendiz.get_ch_componentes_regulares_obrigatorios_cumprida() * 100 / obj.aprendiz.get_ch_componentes_regulares_obrigatorios_esperada()
                )
            else:
                percentual_carga_horaria_cumprida = 'Aluno sem matriz'
                percentual_disciplinas_obrigatorias = 'Aluno sem matriz'
            if obj.motivo_encerramento == Aprendizagem.MOTIVO_CONTRATACAO_CONCEDENTE:
                foi_sera_contrado = 'Sim'
            elif obj.motivo_encerramento is None:
                foi_sera_contrado = '-'
            else:
                foi_sera_contrado = 'Não'

            row = [
                idx + 1,
                obj.aprendiz.matricula,
                obj.aprendiz.get_nome(),
                obj.aprendiz.pessoa_fisica.nascimento_data.strftime('%d/%m/%Y'),
                obj.aprendiz.situacao.descricao,
                obj.aprendiz.get_ultima_matricula_periodo().situacao.descricao,
                obj.aprendiz.pessoa_fisica.email_secundario,
                obj.aprendiz.email_academico,
                obj.aprendiz.data_expedicao_diploma,
                obj.aprendiz.periodo_atual,
                percentual_carga_horaria_cumprida,
                percentual_disciplinas_obrigatorias,
                obj.aprendiz.curso_campus.descricao_historico,
                obj.aprendiz.matriz.estrutura.descricao,
                obj.aprendiz.curso_campus.modalidade.descricao,
                obj.aprendiz.curso_campus.diretoria.setor.uo,
                obj.empresa,
                obj.nome_monitor,
                obj.email_monitor,
                obj.telefone_monitor,
                obj.orientador.get_nome(),
                obj.orientador.get_matricula(),
                obj.orientador.vinculo.user.email,
                obj.get_data_inicio(),
                obj.get_data_prevista_encerramento(),
                not obj.modulo_1 and '-' or obj.get_modulo_1().inicio,
                not obj.modulo_1 and '-' or obj.get_modulo_1().fim,
                not obj.modulo_2 and '-' or obj.get_modulo_2().inicio,
                not obj.modulo_2 and '-' or obj.get_modulo_2().fim,
                not obj.modulo_3 and '-' or obj.get_modulo_3().inicio,
                not obj.modulo_3 and '-' or obj.get_modulo_3().fim,
                not obj.modulo_4 and '-' or obj.get_modulo_4().inicio,
                not obj.modulo_4 and '-' or obj.get_modulo_4().fim,
                obj.aditivocontratualaprendizagem_set.exists() and 'Sim' or 'Não',
                tipos_aditivo,
                obj.get_encerramento_por_display(),
                obj.get_motivo_encerramento_display(),
                obj.motivacao_rescisao,
                obj.get_media_notas_avaliacoes_empregado_monitor(),
                obj.resumo_pendencias(),
                obj.ch_final,
                foi_sera_contrado,
            ]
            rows.append(row)
        return rows

    def data_inicio(self, obj):
        data_inicio = obj.get_data_inicio()
        if data_inicio:
            return mark_safe(data_inicio.strftime('%d/%m/%Y'))
        else:
            return mark_safe('-')

    data_inicio.short_description = 'Data de Início'
    data_inicio.admin_order_field = 'moduloaprendizagem__inicio'

    def data_prevista_encerramento(self, obj):
        data_prevista_encerramento = obj.get_data_prevista_encerramento()
        if data_prevista_encerramento:
            return mark_safe(data_prevista_encerramento.strftime('%d/%m/%Y'))
        else:
            return mark_safe('-')

    data_prevista_encerramento.short_description = 'Data Prevista para Encerramento'
    data_prevista_encerramento.admin_order_field = 'moduloaprendizagem__fim'

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        if in_group(request.user, ['Coordenador de Estágio Sistêmico', 'Coordenador de Estágio']):
            items.append(dict(url='/admin/estagios/aprendizagem/notificacao/', label='Enviar Notificações de Pendências'))
        return items

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('notificacao/', self.admin_site.admin_view(self.notificacao))]
        return my_urls + urls

    def notificacao(self, request):
        qs = self.get_queryset(request).filter(data_encerramento__isnull=True)
        for obj in qs.distinct().order_by('-id'):
            obj.notificar()
        return httprr(request.META.get('HTTP_REFERER', '..'), 'Foram enviados e-mails referentes às aprendizagens com ' 'pendências.')


admin.site.register(Aprendizagem, AprendizagemAdmin)


class AtividadeProfissionalEfetivaAdmin(ModelAdminPlus):
    form = AtividadeProfissionalEfetivaForm
    list_display_icons = True
    export_to_xls = True
    list_per_page = 25
    list_display = [
        'aluno',
        'get_situacao_aluno',
        'get_situacao_ultima_matricula_periodo',
        'get_campus',
        'instituicao',
        'razao_social',
        'orientador',
        'inicio',
        'data_prevista_encerramento',
        'encerramento',
        'situacao',
    ]
    search_fields = ('instituicao', 'razao_social', 'aluno__matricula', 'aluno__pessoa_fisica__nome', 'orientador__vinculo__user__username', 'orientador__vinculo__pessoa__nome')
    list_filter = [CustomTabListFilter, 'tipo', 'aluno__situacao', SituacaoUltimaMatriculaPeriodoFilter, 'aluno__curso_campus__diretoria__setor__uo']
    exclude = ()
    show_count_on_tabs = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not visualiza_todos_estagios_afins(request.user):
            uo = get_uo(request.user)
            if not in_group(request.user, ['Coordenador de Estágio', 'Visualizador de Estágios']):
                return qs.filter(aluno__curso_campus__coordenador_id=request.user.get_profile().pk) | qs.filter(aluno__curso_campus__coordenador_2_id=request.user.get_profile().pk)
            else:
                return qs.filter(aluno__curso_campus__diretoria__setor__uo=uo)
        return qs

    def get_fieldsets(self, request, obj=None):
        if obj:
            return (
                ('Dados Gerais', {'fields': ('aluno', 'instituicao', 'razao_social', 'vinculo', 'tipo', 'descricao_outro_tipo')}),
                ('Período e Carga Horária', {'fields': ('inicio', 'data_prevista_encerramento', 'ch_semanal')}),
                ('Documentação', {'fields': ('documentacao_comprobatoria', 'plano_atividades')}),
                ('Relação das Atividades', {'fields': ('atividades',)}),
                ('Encerramento', {'fields': tuple()}),
            )
        else:
            return (
                ('Dados Gerais', {'fields': ('aluno', 'instituicao', 'razao_social', 'vinculo', 'tipo', 'descricao_outro_tipo', 'situacao_atividade')}),
                ('Período e Carga Horária', {'fields': ('inicio', 'data_prevista_encerramento', 'ch_semanal')}),
                ('Documentação', {'fields': ('documentacao_comprobatoria', 'plano_atividades')}),
                ('Relação das Atividades', {'fields': ('atividades',)}),
                ('Encerramento', {'fields': ('anterior_20171', 'encerramento', 'ch_final', 'relatorio_final_aluno', 'observacoes')}),
            )

    def get_tabs(self, request):
        return ['tab_em_andamento', 'tab_matriculas_irregulares', 'tab_atingiu_data_encerramento', 'tab_apto_para_conclusao', 'tab_concluida']

    def tab_em_andamento(self, request, queryset):
        qs = queryset.filter(situacao=AtividadeProfissionalEfetiva.EM_ANDAMENTO).filter(data_prevista_encerramento__gte=datetime.date.today())
        return qs

    tab_em_andamento.short_description = 'Em Andamento'

    def tab_matriculas_irregulares(self, request, queryset):
        qs = (
            queryset.filter(situacao=AtividadeProfissionalEfetiva.EM_ANDAMENTO)
            .filter(data_prevista_encerramento__gte=datetime.date.today())
            .filter(aluno__situacao__in=get_situacoes_irregulares())
        )
        return qs

    tab_matriculas_irregulares.short_description = 'Matrículas Irregulares'

    def tab_atingiu_data_encerramento(self, request, queryset):
        qs = queryset.filter(situacao=AtividadeProfissionalEfetiva.EM_ANDAMENTO).filter(data_prevista_encerramento__lte=datetime.date.today())
        return qs

    tab_atingiu_data_encerramento.short_description = 'Atingiram Data Prevista para Encerramento'

    def tab_apto_para_conclusao(self, request, queryset):
        qs = queryset.filter(situacao=AtividadeProfissionalEfetiva.EM_ANDAMENTO, data_prevista_encerramento__lte=datetime.date.today()).exclude(relatorio_final_aluno='')
        return qs

    tab_apto_para_conclusao.short_description = 'Aptas para Conclusão'

    def tab_concluida(self, request, queryset):
        qs = queryset.filter(situacao__in=[AtividadeProfissionalEfetiva.CONCLUIDA, AtividadeProfissionalEfetiva.NAO_CONCLUIDA])
        return qs

    tab_concluida.short_description = 'Concluídas'

    def to_xls(self, request, queryset, processo):
        header = [
            '#',
            'Aluno',
            'E-mail Pessoal Aluno',
            'E-mail Acadêmico Aluno',
            'Tipo',
            'Curso',
            'Campus',
            'Instituição de Realização da Atividade',
            'Razão Social',
            'Orientador',
            'Início',
            'Data Prevista para Encerramento',
            'Encerramento',
            'C.H. Semanal',
            'C.H. Final',
        ]
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [
                idx + 1,
                obj.aluno,
                obj.aluno.pessoa_fisica.email_secundario,
                obj.aluno.email_academico,
                obj.get_tipo_display(),
                obj.aluno.curso_campus,
                obj.aluno.curso_campus.diretoria.setor.uo,
                obj.instituicao,
                obj.razao_social,
                obj.orientador,
                obj.inicio,
                obj.data_prevista_encerramento,
                obj.encerramento,
                obj.ch_semanal,
                obj.ch_final,
            ]
            rows.append(row)
        return rows

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        if in_group(request.user, ['Coordenador de Estágio Sistêmico', 'Coordenador de Estágio']):
            items.append(dict(url='/admin/estagios/atividadeprofissionalefetiva/notificacao/', label='Enviar Notificações de Pendências'))
        return items

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('notificacao/', self.admin_site.admin_view(self.notificacao))]
        return my_urls + urls

    def notificacao(self, request):
        qs = self.get_queryset(request).filter(situacao__in=[AtividadeProfissionalEfetiva.EM_ANDAMENTO])
        for obj in qs.distinct().order_by('-id'):
            obj.notificar()
        return httprr(request.META.get('HTTP_REFERER', '..'), 'Foram enviados e-mails referentes às atividades profissionais efetivas com ' 'pendências. {}'.format(qs.distinct().count()))


admin.site.register(AtividadeProfissionalEfetiva, AtividadeProfissionalEfetivaAdmin)


class SolicitacaoCancelamentoEncerramentoEstagioAdmin(ModelAdminPlus):
    list_display = ('get_estagio', 'user', 'data', 'situacao', 'justificativa')
    list_filter = (CustomTabListFilter,)
    list_display_icons = True
    list_per_page = 25
    search_fields = ('estagio__aluno__matricula', 'estagio__aluno__pessoa_fisica__nome_registro', 'estagio__aluno__pessoa_fisica__nome')
    show_count_on_tabs = True

    def get_acoes(self, obj):
        texto = ''
        if obj.estagio:
            if obj.situacao == SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA:
                texto = '<ul class="action-bar">'
                texto = (
                    texto
                    + '<li><a href="/estagios/cancelar_encerramento_estagio/{}/?scee_pk={}" class="btn danger" data-confirm="Tem certeza que deseja cancelar o encerramento deste estágio?">Cancelar Encerramento</a></li>'.format(
                        obj.estagio.pk, obj.pk
                    )
                )
                texto = (
                    texto
                    + '<li><a href="/estagios/indeferir_cancelar_encerramento_estagio/{}/" class="btn danger" data-confirm="Tem certeza que deseja indeferir o cancelamento do encerramento deste estágio?">Indeferir</a></li>'.format(
                        obj.pk
                    )
                )
                texto = texto + '</ul>'
        elif obj.aprendizagem:
            if obj.situacao == SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA:
                texto = '<ul class="action-bar">'
                texto = (
                    texto
                    + '<li><a href="/estagios/cancelar_encerramento_estagio/{}/?scee_pk={}" class="btn danger" data-confirm="Tem certeza que deseja cancelar o encerramento desta aprendizagem?">Cancelar Encerramento</a></li>'.format(
                        obj.aprendizagem.pk, obj.pk
                    )
                )
                texto = (
                    texto
                    + '<li><a href="/estagios/indeferir_cancelar_encerramento_estagio/{}/" class="btn danger" data-confirm="Tem certeza que deseja indeferir o cancelamento do encerramento desta aprendizagem?">Indeferir</a></li>'.format(
                        obj.pk
                    )
                )
                texto = texto + '</ul>'
        elif obj.atividade_profissional_efetiva:
            if obj.situacao == SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA:
                texto = '<ul class="action-bar">'
                texto = (
                    texto
                    + '<li><a href="/estagios/cancelar_encerramento_estagio/{}/?scee_pk={}" class="btn danger" data-confirm="Tem certeza que deseja cancelar o encerramento deste estágio?">Cancelar Encerramento</a></li>'.format(
                        obj.atividade_profissional_efetiva.pk, obj.pk
                    )
                )
                texto = (
                    texto
                    + '<li><a href="/estagios/indeferir_cancelar_encerramento_estagio/{}/" class="btn danger" data-confirm="Tem certeza que deseja indeferir o cancelamento do encerramento deste estágio?">Indeferir</a></li>'.format(
                        obj.pk
                    )
                )
                texto = texto + '</ul>'
        return mark_safe(texto)

    get_acoes.short_description = 'Ações'

    def get_estagio(self, obj):
        if obj.estagio:
            return mark_safe(str(obj.estagio))
        elif obj.aprendizagem:
            return mark_safe(str(obj.aprendizagem))
        elif obj.atividade_profissional_efetiva:
            return mark_safe(str(obj.atividade_profissional_efetiva))

    get_estagio.short_description = 'Estágio ou afim'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not visualiza_todos_estagios_afins(request.user):
            return qs.filter(user=request.user)
        return qs.order_by('-situacao')

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if in_group(request.user, ['Coordenador de Estágio Sistêmico']):
            list_display = list_display + ('get_acoes',)
        return list_display

    def get_tabs(self, request):
        if visualiza_todos_estagios_afins(request.user):
            return ['tab_aguardando_resposta', 'tab_deferidas', 'tab_indeferidas']
        else:
            return ['tab_minhas_solicitacoes']

    def tab_aguardando_resposta(self, request, queryset):
        return queryset.filter(situacao=SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA)

    tab_aguardando_resposta.short_description = 'Aguardando Resposta'

    def tab_deferidas(self, request, queryset):
        return queryset.filter(situacao=SolicitacaoCancelamentoEncerramentoEstagio.DEFERIDA)

    tab_deferidas.short_description = 'Deferidas'

    def tab_indeferidas(self, request, queryset):
        return queryset.filter(situacao=SolicitacaoCancelamentoEncerramentoEstagio.INDEFERIDA)

    tab_indeferidas.short_description = 'Indeferidas'

    def tab_minhas_solicitacoes(self, request, queryset):
        return queryset.filter(user=request.user)

    tab_minhas_solicitacoes.short_description = 'Minhas Solicitações '


admin.site.register(SolicitacaoCancelamentoEncerramentoEstagio, SolicitacaoCancelamentoEncerramentoEstagioAdmin)
