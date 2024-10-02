import datetime
import html

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from comum.utils import get_uo
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import format_
from djtools.templatetags.tags import icon
from projetos.forms import EditalForm, ComissaoEditalForm, AvaliadorExternoForm, VisitaTecnicaForm, \
    ColaboradorVoluntarioForm, EditarHistoricoEquipeForm, NucleoExtensaoForm, FocoTecnologicoForm
from projetos.models import (
    Projeto,
    Edital,
    FocoTecnologico,
    AreaConhecimento,
    Participacao,
    AreaTematica,
    Tema,
    Parametro,
    TipoBeneficiario,
    AreaLicaoAprendida,
    ProjetoCancelado,
    TipoVinculo,
    ComissaoEdital,
    AvaliadorExterno,
    CriterioAvaliacaoAluno,
    ObjetivoVisitaTecnica,
    VisitaTecnica,
    ColaboradorVoluntario,
    OrigemRecursoEdital,
    HistoricoEquipe,
    NucleoExtensao,
    CaracterizacaoBeneficiario, OfertaProjeto,
)


class EditalListFilter(admin.SimpleListFilter):
    title = "Edital"
    parameter_name = 'descricao'

    def lookups(self, request, model_admin):
        return Edital.objects.values_list('id', 'titulo')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(edital=self.value())


class AnoProjetoListFilter(admin.SimpleListFilter):
    title = "Ano de Início"
    parameter_name = 'ano'

    def lookups(self, request, model_admin):
        anos = []

        for data in Edital.objects.all().dates('inicio_inscricoes', 'year'):
            anos.append((data.year, data.year))
        anos.reverse()
        return anos

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(inicio_execucao__year=self.value())


class NEPPFilter(admin.SimpleListFilter):
    title = "Vinculado ao NEPP"
    parameter_name = 'vinculo_nepp'

    def lookups(self, request, model_admin):
        opcoes = (('1', 'Sim'), ('2', 'Não'))
        return opcoes

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(nucleo_extensao__isnull=False)
        elif self.value() == '2':
            return queryset.filter(nucleo_extensao__isnull=True)


class ProjetoAdmin(ModelAdminPlus):
    title = 'Projetos'
    list_display = ('icones', 'uo', 'edital', 'get_coordenador', 'titulo', 'get_situacao', 'get_pre_aprovado', 'get_aprovado', 'get_pontuacao', 'icone_imprimir')
    ordering = ('classificacao', '-pontuacao')
    search_fields = ('titulo', 'resumo', 'vinculo_coordenador__pessoa__nome')
    export_to_xls = True
    fieldsets = (
        (None, {'fields': ('edital', 'uo')}),
        (
            'Dados do Projeto',
            {
                'fields': (
                    'titulo',
                    'area_conhecimento',
                    'area_tematica',
                    'tema',
                    'publico_alvo',
                    'justificativa',
                    'resumo',
                    'objetivo_geral',
                    'metodologia',
                    'acompanhamento_e_avaliacao',
                    'resultados_esperados',
                    'inicio_execucao',
                    'fim_execucao',
                )
            },
        ),
    )
    list_filter = (
        CustomTabListFilter,
        AnoProjetoListFilter,
        EditalListFilter,
        'uo',
        'area_tematica',
        'tema',
        'area_conhecimento',
        'possui_cunho_social',
        'possui_acoes_empreendedorismo',
        NEPPFilter,
        'nucleo_extensao',
        'possui_cooperacao_internacional',
    )
    list_per_page = 20
    list_display_icons = False
    show_count_on_tabs = True

    def to_xls(self, request, queryset, processo):
        header = [
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            'Quantidade Prevista de Pessoas a Atender',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            'Quantidade de Pessoas Atendidas',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
        ]

        rows = [header]
        tipos_beneficiarios = list()
        for tipo in TipoBeneficiario.objects.all().order_by('descricao'):
            tipos_beneficiarios.append(f'{tipo.descricao}')
        header = [
            '#',
            'Título',
            'Situação',
            'Resumo do Projeto',
            'Edital',
            'Ano do Edital',
            'Coordenador',
            'Email do Coordenador',
            'Área de Conhecimento',
            'Área Temática',
            'Possui Cunho Social',
            'Campus',
            'Período de Execução',
            'Pontuação',
        ]
        for item in tipos_beneficiarios:
            header.append(item)
        for item in tipos_beneficiarios:
            header.append(item)
        rows.append(header)
        for idx, obj in enumerate(processo.iterate(queryset)):
            if obj.vinculo_coordenador:
                coordenador = obj.vinculo_coordenador
            else:
                coordenador = obj.get_responsavel()
            periodo = 'De {} a {}'.format(obj.inicio_execucao.strftime("%d/%m/%Y"), obj.fim_execucao.strftime("%d/%m/%Y"))

            row = [
                idx + 1,
                obj.titulo,
                obj.get_status(),
                strip_tags(html.unescape(obj.resumo)),
                obj.edital.titulo,
                obj.edital.inicio_inscricoes.year,
                coordenador.pessoa.nome,
                coordenador.pessoa.email,
                obj.area_conhecimento,
                obj.area_tematica,
                obj.possui_cunho_social,
                obj.uo,
                periodo,
                mark_safe(obj.pontuacao),
            ]
            for tipo in TipoBeneficiario.objects.all().order_by('descricao'):
                caracterizacao = CaracterizacaoBeneficiario.objects.filter(projeto=obj, tipo_beneficiario=tipo)
                if caracterizacao.exists():
                    row.append(caracterizacao[0].quantidade)
                else:
                    row.append('0')
            for tipo in TipoBeneficiario.objects.all().order_by('descricao'):
                caracterizacao = CaracterizacaoBeneficiario.objects.filter(projeto=obj, tipo_beneficiario=tipo)
                if caracterizacao.exists():
                    row.append(caracterizacao[0].quantidade_atendida)
                else:
                    row.append('0')

            rows.append(row)
        return rows

    def icones(self, obj):
        return mark_safe(icon('view', f'/projetos/projeto/{obj.id}/'))

    icones.short_description = 'Ações'

    def get_pontuacao(self, obj):
        return mark_safe(obj.pontuacao)

    get_pontuacao.short_description = 'Pontuação'

    def has_add_permission(self, request):
        return False

    def get_coordenador(self, obj):
        participacao = obj.participacao_set.get(responsavel=True)
        retorno = participacao.get_nome()
        if participacao.vinculo == TipoVinculo.BOLSISTA and participacao.bolsa_concedida == True:
            retorno = retorno + '<br><b>Bolsista</b>'

        return mark_safe(retorno)

    get_coordenador.short_description = 'Coordenador'

    def get_pre_aprovado(self, obj):
        return mark_safe(obj.get_pre_selecionado())

    get_pre_aprovado.short_description = 'Pré-selecionado'

    def get_aprovado(self, obj):
        return mark_safe(obj.get_selecionado())

    get_aprovado.short_description = 'Selecionado'

    def get_situacao(self, obj):
        if obj.get_status() == Projeto.STATUS_CONCLUIDO:
            retorno = f'<span class="status status-success">{obj.get_status()}</span>'
        elif (
            obj.get_status() == Projeto.STATUS_NAO_SELECIONADO
            or obj.get_status() == Projeto.STATUS_NAO_ACEITO
            or obj.get_status() == Projeto.STATUS_NAO_ENVIADO
            or obj.get_status() == Projeto.STATUS_CANCELADO
            or obj.inativado
        ):
            retorno = f'<span class="status status-error">{obj.get_status()}</span>'
        else:
            retorno = f'<span class="status status-alert">{obj.get_status()}</span>'
        return mark_safe(retorno)

    get_situacao.short_description = 'Situação Atual'

    def icone_imprimir(self, obj):
        return mark_safe(f'<a href="/projetos/imprimir_projeto/{obj.id}/" class="btn">Imprimir</a>')

    icone_imprimir.short_description = 'Opções'

    def get_tabs(self, request):
        return [
            'tab_em_edicao',
            'tab_enviados',
            'tab_pre_selecionados',
            'tab_selecionados',
            'tab_em_execucao',
            'tab_concluidos',
            'tab_nao_enviados',
            'tab_nao_pre_selecionados',
            'tab_nao_selecionados',
            'tab_inativados',
            'tab_cancelados',
        ]

    def tab_selecionados(self, request, queryset):
        hoje = datetime.datetime.now()
        if request.user.groups.filter(name='Gerente Sistêmico de Extensão'):
            return queryset.filter(aprovado=True, pre_aprovado=True)
        else:
            return queryset.filter(aprovado=True, pre_aprovado=True, edital__divulgacao_selecao__lt=hoje)

    tab_selecionados.short_description = 'Selecionados'

    def tab_nao_selecionados(self, request, queryset):
        hoje = datetime.datetime.now()
        if request.user.groups.filter(name='Gerente Sistêmico de Extensão'):
            return queryset.filter(aprovado=False, pre_aprovado=True)
        else:
            return queryset.filter(aprovado=False, pre_aprovado=True, edital__divulgacao_selecao__lt=hoje)

    tab_nao_selecionados.short_description = 'Não Selecionados'

    def tab_pre_selecionados(self, request, queryset):
        return queryset.filter(pre_aprovado=True)

    tab_pre_selecionados.short_description = 'Pré-Selecionados'

    def tab_nao_pre_selecionados(self, request, queryset):
        return queryset.filter(pre_aprovado=False, data_conclusao_planejamento__isnull=False)

    tab_nao_pre_selecionados.short_description = 'Não Pré-Selecionados'

    def tab_em_execucao(self, request, queryset):
        hoje = datetime.datetime.now()
        projetos_cancelados = ProjetoCancelado.objects.filter(cancelado=True).values_list('projeto', flat=True)
        nao_concluidos = queryset.filter(pre_aprovado=True, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, inativado=False).exclude(
            id__in=projetos_cancelados
        )
        return nao_concluidos.filter(edital__divulgacao_selecao__lt=hoje) | nao_concluidos.filter(edital__tipo_fomento=Edital.FOMENTO_EXTERNO)

    tab_em_execucao.short_description = 'Em Execução'

    def tab_concluidos(self, request, queryset):
        return queryset.filter(aprovado=True, pre_aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=False)

    tab_concluidos.short_description = 'Concluídos'

    def tab_em_edicao(self, request, queryset):
        hoje = datetime.datetime.now()
        cancelados = ProjetoCancelado.objects.filter(cancelado=True, data_avaliacao__isnull=False).values_list('projeto', flat=True)
        return queryset.filter(data_conclusao_planejamento__isnull=True, edital__fim_inscricoes__gte=hoje).exclude(id__in=cancelados)

    tab_em_edicao.short_description = 'Em Edição'

    def tab_enviados(self, request, queryset):
        return queryset.filter(Q(data_conclusao_planejamento__isnull=False) | Q(data_conclusao_planejamento__isnull=True, data_pre_avaliacao__isnull=False))

    tab_enviados.short_description = 'Enviados'

    def tab_nao_enviados(self, request, queryset):
        hoje = datetime.datetime.now()
        return queryset.filter(data_conclusao_planejamento__isnull=True, data_pre_avaliacao__isnull=True, edital__fim_inscricoes__lt=hoje)

    tab_nao_enviados.short_description = 'Não Enviados'

    def tab_cancelados(self, request, queryset):
        cancelados = ProjetoCancelado.objects.filter(cancelado=True, data_avaliacao__isnull=False).values_list('projeto', flat=True)
        return queryset.filter(id__in=cancelados, aprovado=True, pre_aprovado=True).filter(
            Q(data_conclusao_planejamento__isnull=False) | Q(data_conclusao_planejamento__isnull=True, data_pre_avaliacao__isnull=False)
        )

    tab_cancelados.short_description = 'Cancelados'

    def tab_inativados(self, request, queryset):
        return queryset.filter(inativado=True)

    tab_inativados.short_description = 'Inativados'

    def response_change(self, request, obj):
        self.message_user(request, 'Projeto alterado com sucesso.')
        return HttpResponseRedirect(f'/projetos/projeto/{obj.pk}/')

    def response_add(self, request, obj):
        self.message_user(request, 'Projeto cadastrado com sucesso.')
        return HttpResponseRedirect(f'/projetos/projeto/{obj.pk}/')

    def response_delete(self, request, obj_display, obj_id):
        self.message_user(request, 'Projeto excluído com sucesso.')
        return HttpResponseRedirect('/projetos/meus_projetos/')

    def add_view(self, request, form_url='', extra_context=None):
        raise PermissionDenied

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return HttpResponseRedirect(f'/projetos/editar_projeto/{object_id}/')

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)

        if request.user.groups.filter(name__in=['Gerente Sistêmico de Extensão', 'Visualizador de Projetos']).exists():
            return qs

        elif request.user.groups.filter(name__in=['Coordenador de Extensão', 'Avaliador de Projetos de Extensão', 'Visualizador de Projetos do Campus']).exists():
            return qs.filter(uo=get_uo(request.user))

        elif request.user.groups.filter(name__in=['Servidor', 'Aposentado']).exists():
            participacoes = Participacao.objects.filter(responsavel=True, vinculo_pessoa=request.user.get_vinculo())
            ids = []
            for participacao in participacoes:
                ids.append(participacao.projeto.id)
            qs = Projeto.objects.filter(id__in=ids)
            return qs
        else:
            return qs.filter(id=0)

    def has_delete_permission(self, request, obj=None):
        return obj and obj.pode_remover_projeto()


admin.site.register(Projeto, ProjetoAdmin)


class AnoListFilter(admin.SimpleListFilter):
    title = "Ano"
    parameter_name = 'Ano'

    def lookups(self, request, model_admin):
        anos = []
        for data in Edital.objects.all().dates('inicio_inscricoes', 'year'):
            anos.append((data.year, data.year))
        anos.reverse()
        return anos

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(inicio_inscricoes__year=self.value())


class EditalAdmin(ModelAdminPlus):
    form = EditalForm
    list_display = ('icones', 'titulo', 'descricao', 'tipo_edital', 'forma_selecao', 'inicio_inscricoes', 'fim_inscricoes', 'get_percentual_executado', 'get_opcoes')
    ordering = ('-inicio_inscricoes', 'titulo')
    search_fields = ('descricao', 'titulo')
    list_filter = [CustomTabListFilter, AnoListFilter, 'tipo_fomento', 'campus_especifico']
    exclude = ['arquivo']

    fieldsets = (
        ('Dados Gerais', {'fields': ('titulo', 'descricao', 'tipo_fomento', 'tipo_edital', 'forma_selecao', 'campus_especifico', 'qtd_projetos_selecionados')}),
        ('Calendário', {'fields': ('inicio_inscricoes', 'fim_inscricoes', 'inicio_pre_selecao', 'inicio_selecao', 'fim_selecao', 'data_recurso', 'divulgacao_selecao')}),
        (
            'Configurações do Edital',
            {
                'fields': (
                    'participa_aluno',
                    'participa_servidor',
                    'valor_financiado_por_projeto',
                    'sistemico_pode_submeter',
                    'exige_licoes_aprendidas',
                    'exige_avaliacao_aluno',
                    'ano_inicial_projeto_pendente',
                    'atividade_todo_mes',
                    'prazo_atividade',
                    'permite_colaborador_voluntario',
                    'colaborador_externo_bolsista',
                    'permite_indicacao_tardia_equipe',
                    'exige_frequencia_aluno',
                    'exige_anuencia',
                )
            },
        ),
        (
            'Termos de Compromisso',
            {
                'fields': (
                    'termo_compromisso_coordenador',
                    'termo_compromisso_servidor',
                    'termo_compromisso_aluno',
                    'termo_compromisso_colaborador_voluntario',
                )
            },
        ),
    )

    def icones(self, obj):
        retorno = icon('view', f'/projetos/edital/{obj.id}/') + icon('edit', f'/admin/projetos/edital/{obj.id}/')
        hoje = datetime.datetime.now()
        if obj.fim_selecao and obj.fim_selecao > hoje:
            retorno = retorno + icon('delete', f'/admin/projetos/edital/{obj.id}/delete/')
        return mark_safe(retorno)

    icones.short_description = '-'

    def get_percentual_executado(self, obj):
        projetos_aprovados = Projeto.objects.filter(edital=obj, aprovado=True)
        total_projetos = projetos_aprovados.count()
        total_projetos_encerrados = projetos_aprovados.filter(data_finalizacao_conclusao__isnull=False).count()
        total = total_projetos
        if total == 0:
            total = 1
        percentual_html = '''
                    %d/%d
                    <div class="progress">
                        <p>%s%%</p>
                    </div>
                    ''' % (
            total_projetos_encerrados,
            total_projetos,
            int(total_projetos_encerrados * 100 / total),
        )
        return mark_safe(percentual_html)

    get_percentual_executado.short_description = 'Proporção de Projetos Encerrados'

    def has_delete_permission(self, request, obj=None):
        hoje = datetime.datetime.now()
        return obj and obj.fim_selecao and obj.fim_selecao > hoje

    def response_change(self, request, obj):
        self.message_user(request, 'Edital alterado com sucesso.')
        return HttpResponseRedirect('/projetos/edital/%s/' % str(obj.pk))

    def response_add(self, request, obj):
        self.message_user(request, 'Edital cadastrado com sucesso.')
        return HttpResponseRedirect('/projetos/edital/%s/' % str(obj.pk))

    def formfield_for_choice_field(self, db_field, request, **kwargs):

        if db_field.name == "forma_selecao":
            if request.user.groups.filter(name='Gerente Sistêmico de Extensão'):
                kwargs['choices'] = Edital.TIPO_FORMA_SELECAO_CHOICES
            else:
                kwargs['choices'] = Edital.TIPO_FORMA_SELECAO_PESQUISA_CHOICES
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = []

        self.exclude = [
            'inclusao_bolsas_ae',
            'arquivo',
            'qtd_maxima_alunos',
            'qtd_maxima_servidores',
            'qtd_maxima_alunos_bolsistas',
            'qtd_maxima_servidores_bolsistas',
            'qtd_anos_anteriores_publicacao',
            'deseja_receber_bolsa',
            'peso_avaliacao_lattes_coordenador',
            'peso_avaliacao_projeto',
            'data_avaliacao_classificacao',
            'coordenador_pode_receber_bolsa',
        ]

        return super().get_form(request, obj, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('projetos.pode_gerenciar_edital'):
            return qs
        else:
            return qs.filter(cadastrado_por__setor__uo=get_uo(request.user)) | qs.filter(autorizado_em__isnull=False, id__in=OfertaProjeto.objects.filter(uo=get_uo(request.user)).values_list('edital', flat=True))

    def get_tabs(self, request):
        return ['tab_abertos', 'tab_em_execucao', 'tab_encerrados']

    def tab_abertos(self, request, queryset):
        '''
        Retorna os editais com resultados ainda não divulgados
        '''
        hoje = datetime.datetime.now()
        return queryset.filter(divulgacao_selecao__gt=hoje)

    tab_abertos.short_description = 'Abertos'

    def tab_em_execucao(self, request, queryset):
        '''
        Retorna os editais que existem ao menos um projeto não encerrado
        '''
        editais_com_projetos_nao_encerrados = Projeto.objects.filter(data_finalizacao_conclusao__isnull=True, aprovado=True).values_list('edital__id', flat=True)
        return queryset.filter(id__in=editais_com_projetos_nao_encerrados)

    tab_em_execucao.short_description = 'Em Execução'

    def tab_encerrados(self, request, queryset):
        '''
        Retorna os editais em que todos os projetos estejam encerrados
        '''
        editais_com_projetos_nao_encerrados = Projeto.objects.filter(data_finalizacao_conclusao__isnull=True, aprovado=True).values_list('edital__id', flat=True)
        editais_com_projetos_encerrados = Projeto.objects.filter(data_finalizacao_conclusao__isnull=False, aprovado=True).values_list('edital__id', flat=True)
        return queryset.filter(id__in=editais_com_projetos_encerrados).exclude(id__in=editais_com_projetos_nao_encerrados)

    tab_encerrados.short_description = 'Encerrados'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.cadastrado_por = request.user.get_vinculo()
            if request.user.groups.filter(name='Coordenador de Extensão').exists():
                obj.autorizado = None
        return super().save_model(request, obj, form, change)

    def get_opcoes(self, obj):
        if self.request.user.has_perm('projetos.pode_gerenciar_edital') and obj.autorizado is None:
            return mark_safe(
                f'''<ul class="action-bar">
                    <li><a href="/projetos/autorizar_edital/{obj.id}/1/" class="btn success confirm">Autorizar</a></li>
                    <li><a href="/projetos/autorizar_edital/{obj.id}/2/" class="btn danger confirm">Rejeitar</a></li>
                </ul>'''
            )
        else:
            return ''

    get_opcoes.short_description = 'Opções'


admin.site.register(Edital, EditalAdmin)


class FocoTecnologicoAdmin(ModelAdminPlus):
    form = FocoTecnologicoForm
    list_display = ('descricao', 'get_campi', 'ativo')
    ordering = ('descricao',)

    def get_queryset(self, request):
        qs = self.model.objects.get_queryset()
        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def get_campi(self, obj):
        return ', '.join([uo.sigla for uo in obj.campi.all()])
    get_campi.short_description = 'Campi'


admin.site.register(FocoTecnologico, FocoTecnologicoAdmin)


class AreaConhecimentoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'superior')
    ordering = ('superior__descricao', 'descricao')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(superior__isnull=False)


admin.site.register(AreaConhecimento, AreaConhecimentoAdmin)


class AreaTematicaAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    ordering = ('id',)


admin.site.register(AreaTematica, AreaTematicaAdmin)


class TemaAdmin(ModelAdminPlus):
    list_filter = ('areatematica',)
    list_display = ('id', 'descricao', 'areatematica')
    ordering = ('id',)


admin.site.register(Tema, TemaAdmin)


class ParametroAdmin(ModelAdminPlus):
    list_display = ('grupo', 'codigo', 'descricao')
    ordering = ('id',)


admin.site.register(Parametro, ParametroAdmin)


class TipoBeneficiarioAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    ordering = ('id',)


admin.site.register(TipoBeneficiario, TipoBeneficiarioAdmin)


class AreaLicaoAprendidaAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    ordering = ('id',)


admin.site.register(AreaLicaoAprendida, AreaLicaoAprendidaAdmin)


class AnoComissaoListFilter(admin.SimpleListFilter):
    title = "Ano"
    parameter_name = 'ano'

    def lookups(self, request, model_admin):
        anos = []

        for data in ComissaoEdital.objects.all().dates('edital__inicio_inscricoes', 'year'):
            anos.append((data.year, data.year))
        anos.reverse()
        return anos

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(edital__inicio_inscricoes__year=self.value())


class ComissaoEditalAdmin(ModelAdminPlus):
    list_display = ('edital', 'get_membros', 'get_lista_emails')
    list_filter = (AnoComissaoListFilter, EditalListFilter)
    list_display_icons = True
    ordering = ('id',)
    form = ComissaoEditalForm

    def get_membros(self, obj):
        return mark_safe(obj.get_membros())

    get_membros.short_description = 'Membros'

    def get_lista_emails(self, obj):
        return mark_safe('''<ul class="action-bar"><li><a class="btn" href="/projetos/lista_emails_comissao/%s/">Lista de Emails dos Membros </a></li></ul>''' % obj.id)

    get_lista_emails.short_description = 'Lista de Emails dos Membros'


admin.site.register(ComissaoEdital, ComissaoEditalAdmin)


class AvaliadorExternoAdmin(ModelAdminPlus):
    title = 'Avaliadores Externos'
    list_display = ('icones', 'nome', 'titulacao', 'instituicao_origem', 'get_areas_tematicas', 'email')
    list_filter = ['titulacao', 'instituicao_origem']
    form = AvaliadorExternoForm

    def icones(self, obj):
        if self.request.user.groups.filter(name='Gerente Sistêmico de Extensão').exists():

            return mark_safe(
                icon('view', f'/admin/projetos/avaliadorexterno/{obj.id}/')
                + icon('edit', f'/admin/projetos/avaliadorexterno/{obj.id}/')
                + icon('delete', f'/admin/projetos/avaliadorexterno/{obj.id}/delete/')
            )
        else:
            return '-'

    icones.short_description = 'Ações'

    def get_areas_tematicas(self, obj):
        return obj.vinculo.get_areas_tematicas_interesse()

    get_areas_tematicas.short_description = 'Áreas Temáticas'


admin.site.register(AvaliadorExterno, AvaliadorExternoAdmin)


class CriterioAvaliacaoAlunoAdmin(ModelAdminPlus):
    list_display = ('nome', 'ativo')
    ordering = ('nome', 'ativo')


admin.site.register(CriterioAvaliacaoAluno, CriterioAvaliacaoAlunoAdmin)


class ObjetivoVisitaTecnicaAdmin(ModelAdminPlus):
    list_display = ('descricao', 'ativo')
    ordering = ('descricao', 'ativo')


admin.site.register(ObjetivoVisitaTecnica, ObjetivoVisitaTecnicaAdmin)


class VisitaTecnicaAdmin(ModelAdminPlus):
    form = VisitaTecnicaForm
    list_display = ('campus', 'data', 'instituicao_visitada', 'get_municipio', 'get_objetivos', 'get_participantes', 'encaminhamentos', 'get_dados_contato')
    list_filter = ('campus',)
    ordering = ('campus', 'instituicao_visitada', 'data')
    list_display_icons = True
    date_hierarchy = 'data'
    export_to_xls = True
    search_fields = ('instituicao_visitada', 'encaminhamentos', 'nome_contato')

    def get_dados_contato(self, obj):
        texto = f'<dl><dt>Nome:</dt><dd>{obj.nome_contato}</dd>'
        texto += f'<dt>Telefone:</dt><dd>{obj.telefone_contato}</dd>'
        texto += f'<dt>Email:</dt><dd>{obj.email_contato}</dd></dl>'
        return mark_safe(texto)

    get_dados_contato.short_description = 'Dados do Contato'

    def get_municipio(self, obj):
        return mark_safe('%s ' % obj.municipio)

    get_municipio.short_description = 'Município'

    def get_objetivos(self, obj):
        retorno = '<ul>'
        for objetivo in obj.objetivos.all():
            retorno += '<li>' + str(objetivo) + '</li>'
        retorno += '</ul>'
        return mark_safe(retorno)

    get_objetivos.short_description = 'Objetivos'

    def get_participantes(self, obj):
        retorno = '<ul>'
        for participante in obj.participantes.all():
            retorno += '<li>' + str(participante) + '</li>'
        retorno += '</ul>'
        return mark_safe(retorno)

    get_participantes.short_description = 'Participantes'

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        if retorno and obj is not None:
            retorno = obj.campus == get_uo(request.user)
        return retorno

    def to_xls(self, request, queryset, processo):
        header = [
            '#',
            'Campus',
            'Data',
            'Instituição Visitada',
            'Município',
            'Objetivos',
            'Participantes',
            'Encaminhamentos',
            'Nome do Contato',
            'Telefone do Contato',
            'Email do Contato',
        ]
        rows = [header]

        for idx, obj in enumerate(processo.iterate(queryset)):
            objetivos = list()
            participantes = list()
            for objetivo in obj.objetivos.all():
                objetivos.append(objetivo.descricao)

            for participante in obj.participantes.all():
                participantes.append(participante.nome)

            lista_objetivos = ', '.join(objetivos)
            lista_participantes = ', '.join(participantes)
            row = [
                idx + 1,
                obj.campus,
                format_(obj.data),
                obj.instituicao_visitada,
                obj.municipio,
                lista_objetivos,
                lista_participantes,
                obj.encaminhamentos,
                obj.nome_contato,
                obj.telefone_contato,
                obj.email_contato,
            ]
            rows.append(row)
        return rows


admin.site.register(VisitaTecnica, VisitaTecnicaAdmin)


class ColaboradorVoluntarioAdmin(ModelAdminPlus):
    title = 'Colaboradores Externos'
    list_display = ('icones', 'nome', 'titulacao', 'instituicao_origem', 'email', 'get_documentacao')
    list_filter = ['titulacao', 'instituicao_origem']
    search_fields = ['nome', 'prestador__username', 'prestador__cpf', 'prestador__passaporte', ]
    form = ColaboradorVoluntarioForm

    fieldsets = (
        ('Dados Pessoais', {'fields': ('nome', 'nacionalidade', 'pais_origem', 'cpf', 'passaporte', 'email', 'telefone')}),
        ('Dados Profissionais', {'fields': ('instituicao_origem', 'titulacao', 'lattes')}),
        ('Outras Informações', {'fields': ('documentacao', )}),
    )

    def icones(self, obj):
        if self.request.user.has_perm('projetos.pode_avaliar_cancelamento_projeto'):
            return mark_safe(
                icon('view', f'/admin/projetos/colaboradorvoluntario/{obj.id}/')
                + icon('edit', f'/admin/projetos/colaboradorvoluntario/{obj.id}/')
                + icon('delete', f'/admin/projetos/colaboradorvoluntario/{obj.id}/delete/')
            )
        else:
            return '-'

    icones.short_description = 'Ações'

    def get_documentacao(self, obj):
        if obj.documentacao:
            return mark_safe(f'<a href="/djtools/private_media/?media={obj.documentacao}" class="btn default">Ver Arquivo</a>')
    get_documentacao.short_description = 'Documentação'


admin.site.register(ColaboradorVoluntario, ColaboradorVoluntarioAdmin)


class OrigemRecursoEditalAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'ativo')
    ordering = ('id',)


admin.site.register(OrigemRecursoEdital, OrigemRecursoEditalAdmin)


class HistoricoEquipeAdmin(ModelAdminPlus):
    title = 'Histórico da Equipe'
    list_display = ('projeto', 'participante', 'data_movimentacao', 'data_movimentacao_saida')
    form = EditarHistoricoEquipeForm

    def has_delete_permission(self, request, obj=None):
        return obj and obj.projeto.pode_remover_projeto()


admin.site.register(HistoricoEquipe, HistoricoEquipeAdmin)


class NucleoExtensaoAdmin(ModelAdminPlus):
    title = 'Núcleos de Extensão e Prática Profissional'
    list_display = ('uo', 'nome', 'area_atuacao', 'ativo')
    list_filter = ('uo', 'ativo')
    search_fields = ('nome', 'area_atuacao')
    form = NucleoExtensaoForm


admin.site.register(NucleoExtensao, NucleoExtensaoAdmin)
