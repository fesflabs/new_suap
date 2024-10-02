from abc import abstractmethod, ABCMeta

from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from djtools.contrib.admin import ModelAdminPlus
from djtools.templatetags.filters import format_money
from tesouro_gerencial.models import (
    ClassificacaoInstitucional,
    UnidadeGestora,
    EsferaOrcamentaria,
    AcaoGoverno,
    ProgramaTrabalhoResumido,
    PlanoInterno,
    FonteRecurso,
    NaturezaDespesa,
    SubElementoNaturezaDespesa,
    NotaCredito,
    NotaCreditoItem,
    RAP,
    RAPItem,
    GRU,
    ReceitaGRU,
    DocumentoEmpenhoEspecifico,
    DocumentoLiquidacao,
    DocumentoLiquidacaoItem, DocumentoEmpenho, DocumentoEmpenhoItem,
    DocumentoPagamento, DocumentoPagamentoItem, TipoDocumentoEmpenhoEspecifico)

admin.site.register(ClassificacaoInstitucional)
admin.site.register(UnidadeGestora)
admin.site.register(EsferaOrcamentaria)
admin.site.register(AcaoGoverno)
admin.site.register(ProgramaTrabalhoResumido)
admin.site.register(PlanoInterno)
admin.site.register(FonteRecurso)
admin.site.register(NaturezaDespesa)
admin.site.register(SubElementoNaturezaDespesa)
admin.site.register(NotaCredito)
admin.site.register(NotaCreditoItem)


class SimpleListFilterExclude(SimpleListFilter, metaclass=ABCMeta):
    @abstractmethod
    def get_model(self):
        return

    @abstractmethod
    def get_filter(self):
        return

    def lookups(self, request, model_admin):
        return [(item.codigo, str(item)) for item in self.get_model().objects.order_by('codigo')]

    def queryset(self, request, queryset):
        if self.value():
            args = {self.get_filter(): self.value()}
            return queryset.exclude(**args)


class UnidadeOrcamentariaExclude(SimpleListFilterExclude):
    title = 'Unidade Orçamentaria(exceto)'
    parameter_name = 'unidade_orcamentaria_exclude'

    def get_model(self):
        return ClassificacaoInstitucional

    def get_filter(self):
        return 'unidade_orcamentaria__codigo'


class AcaoGovernoExclude(SimpleListFilterExclude):
    title = 'Ação Governo(exceto)'
    parameter_name = 'acao_governo_exclude'

    def get_model(self):
        return AcaoGoverno

    def get_filter(self):
        return 'acao_governo_original'


class NaturesaDespesaExclude(SimpleListFilterExclude):
    title = 'Naturesa de Despesa(exceto)'
    parameter_name = 'naturesa_despesa_exclude'

    def get_model(self):
        return NaturezaDespesa

    def get_filter(self):
        return 'naturesa_despesa_original'


class FonteRecursoExclude(SimpleListFilterExclude):
    title = 'Fonte de Recurso(exceto)'
    parameter_name = 'fonte_recurso_exclude'

    def get_model(self):
        return FonteRecurso

    def get_filter(self):
        return 'fonte_recurso_original'


class TipoDocumentoEmpenhoEspecificoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display_links = None
    list_display = ('descricao', 'aplicar_calculo')
    search_fields = ['descricao']


admin.site.register(TipoDocumentoEmpenhoEspecifico, TipoDocumentoEmpenhoEspecificoAdmin)


class DocumentoEmpenhoEspecificoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display_links = None
    list_display = ('documento_empenho', 'tipo', 'observacao')
    search_fields = ['documento_empenho__numero']


admin.site.register(DocumentoEmpenhoEspecifico, DocumentoEmpenhoEspecificoAdmin)


class RAPAdmin(ModelAdminPlus):
    export_to_xls = True
    list_display_icons = False
    list_display_links = None
    list_display = (
        'numero',
        'ano',
        'unidade_orcamentaria',
        'acao_governo_original',
        'fonte_recurso_original',
        'naturesa_despesa_original',
        'grupo_despesa_original',
        'get_subitem_original',
        'get_valor',
    )
    list_filter = (
        'ano',
        'responsavel_ug',
        'unidade_orcamentaria',
        'acao_governo',
        'naturesa_despesa_original',
        'grupo_despesa_original',
        UnidadeOrcamentariaExclude,
        AcaoGovernoExclude,
        NaturesaDespesaExclude,
        FonteRecursoExclude,
    )
    show_count_on_tabs = True

    def get_valor(self, obj):
        return 'R$ {}'.format(format_money(obj.get_valor()))

    get_valor.short_description = 'valor'

    def get_subitem_original(self, obj):
        return ', '.join(obj.itens.values_list('subitem_original', flat=True))

    get_subitem_original.short_description = 'SubItem'


admin.site.register(RAP, RAPAdmin)
admin.site.register(RAPItem)

admin.site.register(GRU)


class ReceitaGRUAdmin(ModelAdminPlus):
    export_to_xls = True
    list_display_icons = False
    list_display_links = None
    list_display = ('gru', 'ano', 'emitente_ug', 'get_valor')
    list_filter = ('ano', 'gru', 'emitente_ug')
    show_count_on_tabs = True

    def get_valor(self, obj):
        return 'R$ {}'.format(format_money(obj.get_valor()))

    get_valor.short_description = 'valor'


admin.site.register(ReceitaGRU, ReceitaGRUAdmin)


class DocumentoAdmin(ModelAdminPlus):
    search_fields = ['numero']
    export_to_xls = True
    list_display_icons = False
    list_display = (
        'numero',
        'data_emissao',
        'unidade_orcamentaria',
        'acao_governo_original',
        'fonte_recurso_original',
        'naturesa_despesa_original',
        'grupo_despesa_original',
        'get_subitem_original',
        'get_valor',
    )
    list_filter = (
        'tipo',
        'responsavel_ug',
        'unidade_orcamentaria',
        'acao_governo',
        'naturesa_despesa_original',
        'grupo_despesa_original',
        UnidadeOrcamentariaExclude,
        AcaoGovernoExclude,
        NaturesaDespesaExclude,
        FonteRecursoExclude,
    )
    show_count_on_tabs = True
    date_hierarchy = 'data_emissao'

    def get_valor(self, obj):
        return 'R$ {}'.format(format_money(obj.get_valor()))

    get_valor.short_description = 'valor'

    def get_subitem_original(self, obj):
        return ', '.join(obj.itens.values_list('subitem_original', flat=True))

    get_subitem_original.short_description = 'SubItem'


class DocumentoEmpenhoAdmin(DocumentoAdmin):
    search_fields = ['numero', 'documento_empenho_inicial__numero']


admin.site.register(DocumentoEmpenho, DocumentoEmpenhoAdmin)


class DocumentoEmpenhoItemAdmin(ModelAdminPlus):
    search_fields = ['documento_empenho__numero', 'documento_empenho__documento_empenho_inicial__numero', 'valor']
    export_to_xls = True
    list_display_icons = False
    list_display = (
        'get_documento_empenho_inicial',
        'documento_empenho',
        'subitem',
        'get_valor',
        'subitem_original',
    )
    list_filter = (
        'documento_empenho__documento_empenho_inicial',
        'documento_empenho',
        'subitem',
    )
    show_count_on_tabs = True
    date_hierarchy = 'documento_empenho__data_emissao'

    def get_documento_empenho_inicial(self, obj):
        return obj.documento_empenho.documento_empenho_inicial
    get_documento_empenho_inicial.short_description = 'Documento Empenho Inicial'
    get_documento_empenho_inicial.admin_order_field = 'documento_empenho__documento_empenho_inicial__numero'

    def get_valor(self, obj):
        return 'R$ {}'.format(format_money(obj.valor))
    get_valor.short_description = 'Valor'
    get_valor.admin_order_field = 'valor'


admin.site.register(DocumentoEmpenhoItem, DocumentoEmpenhoItemAdmin)
admin.site.register(DocumentoLiquidacao, DocumentoAdmin)


class DocumentoLiquidacaoItemAdmin(ModelAdminPlus):
    search_fields = ['documento_empenho_inicial__numero', 'documento_liquidacao__numero', 'valor']
    export_to_xls = True
    list_display_icons = False
    list_display = (
        'documento_empenho_inicial',
        'documento_liquidacao',
        'subitem',
        'get_valor',
        'subitem_original',
    )
    list_filter = (
        'documento_empenho_inicial',
        'documento_liquidacao',
        'subitem',
    )
    show_count_on_tabs = True
    date_hierarchy = 'documento_liquidacao__data_emissao'

    def get_valor(self, obj):
        return 'R$ {}'.format(format_money(obj.valor))
    get_valor.short_description = 'Valor'
    get_valor.admin_order_field = 'valor'


admin.site.register(DocumentoLiquidacaoItem, DocumentoLiquidacaoItemAdmin)
admin.site.register(DocumentoPagamento, DocumentoAdmin)


class DocumentoPagamentoItemAdmin(ModelAdminPlus):
    search_fields = ['documento_empenho_inicial__numero', 'documento_pagamento__numero', 'valor']
    export_to_xls = True
    list_display_icons = False
    list_display = (
        'documento_empenho_inicial',
        'documento_pagamento',
        'subitem',
        'get_valor',
        'subitem_original',
    )
    list_filter = (
        'documento_empenho_inicial',
        'documento_pagamento',
        'subitem',
    )
    show_count_on_tabs = True
    date_hierarchy = 'documento_pagamento__data_emissao'

    def get_valor(self, obj):
        return 'R$ {}'.format(format_money(obj.valor))
    get_valor.short_description = 'Valor'
    get_valor.admin_order_field = 'valor'


admin.site.register(DocumentoPagamentoItem, DocumentoPagamentoItemAdmin)
