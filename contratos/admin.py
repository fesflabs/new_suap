from django.contrib import admin
from django.utils.safestring import mark_safe

from comum.models import Arquivo
from contratos.forms import ContratoForm, FiscalForm, TermoAditivoForm
from contratos.models import Aditivo, Contrato, Fiscal, MotivoConclusaoContrato, PublicacaoContrato, SubtipoContrato, \
    TipoContrato, TipoFiscal, TipoLicitacao, TipoPublicacao, TipoAnexo, TipoDocumentoComprobatorio, \
    DocumentoTextoContrato
from djtools.contrib.admin import CustomTabListFilter, ModelAdminPlus
from djtools.templatetags.tags import icon
from documento_eletronico.models import DocumentoTexto
from rh.models import Pessoa


class FiscalInline(admin.TabularInline):
    exclude = ('data_exclusao',)

    form = FiscalForm
    model = Fiscal
    extra = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_delete = False


class PublicacaoInline(admin.TabularInline):
    can_delete = False
    exclude = ('arquivo',)
    model = PublicacaoContrato
    extra = 1


class FiscalFilter(admin.SimpleListFilter):
    title = "Fiscal"
    parameter_name = "fiscal"

    SOMENTE_EU = 'somente_eu'

    OPCOES = ((SOMENTE_EU, 'Somente eu'),)

    def lookups(self, request, model_admin):
        return FiscalFilter.OPCOES

    def queryset(self, request, queryset):
        if self.value() == FiscalFilter.SOMENTE_EU:
            return queryset.filter(fiscais_set__servidor=request.user.get_relacionamento()).distinct()
        return queryset


class TempoIndeterminadoFilter(admin.SimpleListFilter):
    title = "Tempo Indeterminado"
    parameter_name = "indeterminado"

    SIM = 'Sim'
    NAO = 'Nao'

    OPCOES = ((SIM, 'Sim'), (NAO, 'Não'),)

    def lookups(self, request, model_admin):
        return TempoIndeterminadoFilter.OPCOES

    def queryset(self, request, queryset):
        if self.value() == TempoIndeterminadoFilter.SIM:
            return queryset.filter(data_fim__isnull=True)
        else:
            return queryset.filter(data_fim__isnull=False)
        return queryset


class ContratadaListFilter(admin.SimpleListFilter):
    title = 'Contratada'
    parameter_name = 'pessoa_contratada'

    def lookups(self, request, model_admin):
        campi = request.GET.get('campi__id__exact', None)
        if campi:
            contratadas = Pessoa.objects.filter(id__in=Contrato.objects.filter(campi__in=campi).values_list('pessoa_contratada', flat=True).distinct())
        else:
            contratadas = Pessoa.objects.filter(id__in=Contrato.objects.all().values_list('pessoa_contratada', flat=True).distinct())

        return [(c.id, c) for c in contratadas]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(pessoa_contratada__id=self.value())
        else:
            return queryset


class ContratoAdmin(ModelAdminPlus):
    change_form_template = 'contratos/templates/admin/contrato/change_form.html'
    list_display = ('numero', 'pessoa_contratada', 'objeto', 'get_uos_as_string', 'get_contratada', 'data_inicio', 'get_data_fim_contrato', 'aditivos')
    list_filter = (CustomTabListFilter, 'campi', ContratadaListFilter, 'tipo', 'subtipo', 'concluido', 'exige_garantia_contratual', FiscalFilter, TempoIndeterminadoFilter)
    ordering = ('-data_inicio',)
    search_fields = Contrato.SEARCH_FIELDS
    list_display_icons = True
    form = ContratoForm
    date_hierarchy = 'data_inicio'
    show_count_on_tabs = True
    export_to_xls = True
    fieldsets = (
        (
            'Dados Gerais',
            {
                'fields': (
                    ('tipo', 'subtipo'),
                    'continuado',
                    'arrecadacao_receita',
                    'numero',
                    'valor',
                    ('data_inicio', 'data_fim', 'tempo_indeterminado'),
                    'objeto',
                    'processo',
                    'empenho',
                    'campi',
                    'pessoa_contratada',
                    'qtd_parcelas',
                )
            },
        ),
        ('Documento do Contrato', {'fields': ('arquivo_contrato', 'documento_digital_contrato')}),
        ('Dados da Licitação', {'fields': (('tipo_licitacao', 'pregao'), 'estimativa_licitacao')}),
        ('Conclusão', {'fields': ('concluido', 'data_conclusao', 'motivo_conclusao')}),
        ('Garantia', {'fields': ('exige_garantia_contratual',)}),
    )

    def get_tabs(self, request):
        return [
            'tab_ativos',
            'tab_proximos_a_vencer',
            'tab_proximos_a_vencer_com_garantias',
            'tab_com_vigencia_expirada',
            'tab_com_ocorrencias_expiradas',
            'tab_concluidos',
            'tab_any_data',
        ]

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Número', 'Contratada', 'Campi', 'Percentual Executado', 'Data de Início', 'Data de Término', 'Termos Aditivos']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):

            porcentagem_dias = f"{obj.get_percentual_dias_executado()}%"
            porcentagem_valor = f"{obj.get_percentual_executado()}%"
            executado = f'Valor Executado: {porcentagem_valor} / Período Executado:{porcentagem_dias}'
            retorno = list()
            for aditivo in obj.aditivos_set.all():
                retorno.append(str(aditivo))
            descricao_aditivos = ', '.join(retorno)

            if obj.data_vencimento == obj.data_fim:
                fim_contrato = mark_safe(obj.data_fim.strftime('%d/%m/%Y'))
            else:
                fim_contrato = mark_safe('Prorrogado de {}  <br> para {}'.format(obj.data_fim.strftime('%d/%m/%Y'), obj.get_data_fim().strftime('%d/%m/%Y')))
            row = [idx + 1, obj.numero, obj.pessoa_contratada, obj.get_uos_as_string(), executado, obj.data_inicio, fim_contrato, descricao_aditivos]
            rows.append(row)
        return rows

    def tab_ativos(self, request, queryset):
        return queryset.ativos()

    tab_ativos.short_description = 'Ativos'

    def tab_concluidos(self, request, queryset):
        return queryset.concluidos()

    tab_concluidos.short_description = 'Concluídos'

    def tab_proximos_a_vencer(self, request, queryset):
        return queryset.proximos_a_vencer()

    tab_proximos_a_vencer.short_description = 'Próximos a Vencer'

    def tab_proximos_a_vencer_com_garantias(self, request, queryset):
        return queryset.proximos_a_vencer_com_garantias()

    tab_proximos_a_vencer_com_garantias.short_description = 'Próximos a Vencer com Garantias'

    def tab_com_vigencia_expirada(self, request, queryset):
        return queryset.com_vigencia_expirada()

    tab_com_vigencia_expirada.short_description = 'Com Vigência Expirada'

    def tab_com_ocorrencias_expiradas(self, request, queryset):
        return queryset.com_ocorrencias_expiradas()

    tab_com_ocorrencias_expiradas.short_description = 'Com Ocorrências Expiradas'

    def get_data_inicio_display(self, obj):
        return mark_safe(obj.data_inicio.strftime('%d/%m/%Y'))

    get_data_inicio_display.short_description = 'Data de Início'
    get_data_inicio_display.admin_order_field = 'data_inicio'

    def get_contratada(self, obj):
        porcentagem_dias = f"{obj.get_percentual_dias_executado()}%"
        porcentagem_valor = f"{obj.get_percentual_executado()}%"
        return mark_safe(
            '''
        <dl>
            <dt>Valor Executado:</dt>
            <dd><div class="progress" data-progress="{0}"><p style="width: {0};">{0}</p></div></dd>
            <dt>Período Executado:</dt>
            <dd><div class="progress" data-progress="{1}"><p style="width: {1};">{1}</p></div></dd>
        </dl>'''.format(
                porcentagem_valor, porcentagem_dias
            )
        )

    get_contratada.short_description = 'Percentual Executado'

    def save_model(self, request, obj, form, change):
        if request.POST.get('tempo_indeterminado', 'off') == 'on':
            obj.data_fim = None
        if request.POST.get('documento_digital_contrato', None):
            # Cria/atualiza instancia de DocumentoTextoContrato para vincular o documento
            documento_contrato = DocumentoTextoContrato() if not obj.documentos_texto_tipo_contato_relacionados().exists() else obj.documentos_texto_tipo_contato_relacionados().first()
            documento_contrato.documento = DocumentoTexto.objects.get(pk=int(request.POST.get('documento_digital_contrato')))
            documento_contrato.contrato = obj
            documento_contrato.save()

        arquivo_up = request.FILES.get('arquivo_contrato')
        if arquivo_up:
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            obj.arquivo = arquivo
            obj.save()
            arquivo.store(request.user, content)
        super().save_model(request, obj, form, change)

    def get_data_fim_contrato(self, obj):
        if not obj.data_fim:
            return mark_safe('Tempo Indeterminado')
        elif obj.data_vencimento == obj.data_fim:
            return mark_safe(obj.data_fim.strftime('%d/%m/%Y'))
        else:
            return mark_safe('<span class="line-through">Prorrogado de {} para:</span> {}'.format(obj.data_fim.strftime('%d/%m/%Y'), obj.data_vencimento.strftime('%d/%m/%Y')))

    get_data_fim_contrato.short_description = 'Data de Término'
    get_data_fim_contrato.admin_order_field = 'data_vencimento'

    def get_uos_as_string(self, obj):
        return obj.get_uos_as_string()

    get_uos_as_string.short_description = 'Campi'
    get_uos_as_string.admin_order_field = 'campi'

    def aditivos(self, obj):
        retorno = '<ul>'
        for aditivo in obj.aditivos_set.all():
            retorno += '<li>' + str(aditivo) + '</li>'
        retorno += '</ul>'
        return mark_safe(retorno)

    aditivos.short_description = 'Termos Aditivos'


admin.site.register(Contrato, ContratoAdmin)


class AditivoAdmin(ModelAdminPlus):
    list_display = ('icone_editar', 'numero', 'data_inicio', 'data_fim')
    list_display_links = tuple()
    ordering = ('data_fim',)
    search_fields = ('numero',)
    form = TermoAditivoForm

    def icone_editar(self, obj):
        return mark_safe(icon('edit', f'/admin/contratos/aditivo/{obj.id}/'))

    icone_editar.short_description = ''


admin.site.register(Aditivo, AditivoAdmin)


class TipoPublicacaoAdmin(ModelAdminPlus):
    pass


admin.site.register(TipoPublicacao, TipoPublicacaoAdmin)


class TipoFiscalAdmin(ModelAdminPlus):
    list_display = ('descricao', 'eh_gestor_contrato', 'pode_gerenciar_todas_medicoes_contrato',)


admin.site.register(TipoFiscal, TipoFiscalAdmin)


class TipoContratoAdmin(ModelAdminPlus):
    pass


admin.site.register(TipoContrato, TipoContratoAdmin)


class SubtipoContratoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'tipo')
    list_filter = ('tipo',)


admin.site.register(SubtipoContrato, SubtipoContratoAdmin)


class MotivoConclusaoContratoAdmin(ModelAdminPlus):
    pass


admin.site.register(MotivoConclusaoContrato, MotivoConclusaoContratoAdmin)


class FiscalAdmin(ModelAdminPlus):
    pass


admin.site.register(Fiscal, FiscalAdmin)


class TipoLicitacaoAdmin(ModelAdminPlus):
    pass


admin.site.register(TipoLicitacao, TipoLicitacaoAdmin)


class TipoDocumentoComprobatorioMedicaoAdmin(ModelAdminPlus):
    pass


admin.site.register(TipoDocumentoComprobatorio, TipoDocumentoComprobatorioMedicaoAdmin)


class TipoAnexoAdmin(ModelAdminPlus):
    list_display_icons = True


admin.site.register(TipoAnexo, TipoAnexoAdmin)
