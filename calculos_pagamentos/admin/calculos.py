# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import path
from django.contrib import admin
from django.utils.safestring import mark_safe

from calculos_pagamentos.forms import (
    NivelVencimentoTAEPorClasseEPadraoForm,
    ValorPorNivelVencimentoDocenteForm,
    ValorPorNivelVencimentoTAEForm,
    CalculoForm,
    PortariaFisicaFormSet,
    PeriodoCalculoProgressaoFormSet,
    ValorRetribuicaoTitulacaoForm,
    FeriasCalculoProgressaoFormSet,
    PeriodoCalculoProgressaoForm,
    PeriodoPericulosidadeFormSet,
    FeriasPericulosidadeFormSet,
    PeriodoForm,
    FeriasForm,
    PeriodoRTFormSet,
    FeriasRTFormSet,
    PeriodoInsalubridadeFormSet,
    FeriasInsalubridadeFormSet,
    PeriodoIQFormSet,
    FeriasIQFormSet,
    PeriodoMudancaRegimeFormSet,
    FeriasMudancaRegimeFormSet,
    PeriodoTransporteFormSet,
    PeriodoPermanenciaFormSet,
    PeriodoFGsCDsFormSet,
    FeriasFGsCDsFormSet,
    CalculoSubstituicaoForm,
    PeriodoSubstituicaoFormSet,
    PeriodoTerminoContratoFormSet,
    CalculoTerminoContratoForm,
)
from calculos_pagamentos.models import (
    ValorPorFuncao,
    NivelVencimento,
    NivelVencimentoTAEPorClasseEPadrao,
    ValorPorNivelVencimento,
    ValorPorNivelVencimentoDocente,
    CalculoProgressao,
    PortariaFisica,
    PeriodoCalculoProgressao,
    ValorRetribuicaoTitulacao,
    FeriasCalculoProgressao,
    CalculoPericulosidade,
    PeriodoPericulosidade,
    DetalhamentoProgressao,
    DetalhamentoPericulosidade,
    FeriasPericulosidade,
    CalculoRT,
    PeriodoRT,
    DetalhamentoRT,
    FeriasRT,
    CalculoIQ,
    PeriodoIQ,
    DetalhamentoIQ,
    FeriasIQ,
    IQ_CHOICES,
    CalculoInsalubridade,
    PeriodoInsalubridade,
    DetalhamentoInsalubridade,
    FeriasInsalubridade,
    INSALUBRIDADE_CHOICES,
    CalculoRSC,
    PeriodoRSC,
    DetalhamentoRSC,
    FeriasRSC,
    CalculoMudancaRegime,
    PeriodoMudancaRegime,
    DetalhamentoMudancaRegime,
    FeriasMudancaRegime,
    CalculoTransporte,
    PeriodoTransporte,
    CalculoPermanencia,
    PeriodoPermanencia,
    DetalhamentoPermanencia,
    ValoresFuncaoDetalhados,
    CalculoFGsCDs,
    CalculoNomeacaoCD,
    CalculoExoneracaoCD,
    CalculoDesignacaoFG,
    CalculoDispensaFG,
    PeriodoFGsCDs,
    DetalhamentoFGsCDs,
    FeriasFGsCDs,
    CalculoSubstituicao,
    PeriodoSubstituicao,
    DetalhamentoSubstituicao,
    ValorAlimentacao,
    CalculoTerminoContratoProfSubs,
    CalculoTerminoContratoInterpLibras,
    PeriodoTerminoContrato,
    MotivoSubstituicao,
)
from calculos_pagamentos.utils import atualizar_tabelas_de_vencimento_tae, atualizar_tabelas_de_vencimento_docente
from comum.admin import InlineSemAddButton
from comum.models import FuncaoCodigo
from comum.utils import get_uo
from djtools import forms
from djtools.contrib.admin import ModelAdminPlus, TabularInlinePlus
from djtools.db import models
from djtools.forms.widgets import AutocompleteWidget, AutocompleteWidgetOld
from djtools.utils import httprr, mask_money
from processo_eletronico.models import Processo as ProcessoEletronico
from protocolo.models import Processo

# from djtools.adminutils import ModelAdminPlus
from rh.models import Titulacao, Servidor


# # # FILTROS # # #


class FeriasFilter(admin.SimpleListFilter):
    title = 'Tem Férias'
    parameter_name = 'ferias'

    def lookups(self, request, model_admin):
        return [[1, "Com férias"], [2, "Sem férias"]]

    def queryset(self, request, queryset):
        ids_com = []
        if queryset.model is CalculoProgressao:
            ids_com = FeriasCalculoProgressao.objects.all().values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoPericulosidade:
            ids_com = FeriasPericulosidade.objects.all().values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoRT:
            ids_com = FeriasRT.objects.all().values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoIQ:
            ids_com = FeriasIQ.objects.all().values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoInsalubridade:
            ids_com = FeriasInsalubridade.objects.all().values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoRSC:
            ids_com = FeriasRSC.objects.all().values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoMudancaRegime:
            ids_com = FeriasMudancaRegime.objects.all().values_list('periodo__calculo__id', flat=True)
        elif issubclass(queryset.model, CalculoFGsCDs):
            ids_com = FeriasFGsCDs.objects.all().values_list('periodo__calculo__id', flat=True)

        if self.value() == "1":
            queryset = queryset.filter(id__in=ids_com)
        elif self.value() == "2":
            queryset = queryset.exclude(id__in=ids_com)

        return queryset


# IFMA/Tássio
class GratificacaoFilter(admin.SimpleListFilter):
    title = 'Tem Gratificação Natalina'
    parameter_name = 'gratificacao'

    def lookups(self, request, model_admin):
        return [[1, "Com gratificacao"], [2, "Sem gratificacao"]]

    def queryset(self, request, queryset):
        ids_com = []
        if queryset.model is CalculoProgressao:
            ids_com = DetalhamentoProgressao.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoPericulosidade:
            ids_com = DetalhamentoPericulosidade.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoRT:
            ids_com = DetalhamentoRT.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoIQ:
            ids_com = DetalhamentoIQ.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoInsalubridade:
            ids_com = DetalhamentoInsalubridade.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoRSC:
            ids_com = DetalhamentoRSC.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoMudancaRegime:
            ids_com = DetalhamentoMudancaRegime.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoPermanencia:
            ids_com = DetalhamentoPermanencia.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif issubclass(queryset.model, CalculoFGsCDs):
            ids_com = DetalhamentoFGsCDs.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        elif queryset.model is CalculoSubstituicao:
            ids_com = DetalhamentoSubstituicao.objects.filter(gratificacao=True).values_list('periodo__calculo__id', flat=True)
        if self.value() == "1":
            queryset = queryset.filter(id__in=ids_com)
        elif self.value() == "2":
            queryset = queryset.exclude(id__in=ids_com)
        return queryset


# IFMA/Tássio
class TipoServidorFilter(admin.SimpleListFilter):
    title = 'Tipo de Servidor'
    parameter_name = 'tipo_servidor'

    def lookups(self, request, model_admin):
        return [[1, "Técnico-Administrativo"], [2, "Professor EBTT "], [3, "Professor do Magistério Superior"]]

    def queryset(self, request, queryset):
        if self.value() == "1":
            queryset = queryset.filter(servidor__eh_tecnico_administrativo=True).distinct()
        elif self.value() == "2":
            queryset = queryset.filter(servidor__eh_docente=True).exclude(servidor__cargo_emprego__codigo='705001').distinct()
        elif self.value() == "3":
            queryset = queryset.filter(servidor__cargo_emprego__codigo='705001').distinct()
        return queryset


# # # CLASSES GERAIS PARA CÁLCULOS: ADMINs e INLINEs # # #

# Adicionado por IFMA/Tássio em outubro de 2017.
class NivelVencimentoAdmin(ModelAdminPlus):
    list_display = ('id', 'codigo', 'categoria')
    ordering = ('id',)


admin.site.register(NivelVencimento, NivelVencimentoAdmin)


class MotivoSubstituicaoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')


admin.site.register(MotivoSubstituicao, MotivoSubstituicaoAdmin)


# Adicionado por IFMA/Tássio em outubro de 2017.
class NivelVencimentoTAEPorClasseEPadraoAdmin(ModelAdminPlus):
    list_display = ('cargo_classe', 'nivel_padrao', 'nivel')
    ordering = ('cargo_classe', 'nivel_padrao', 'nivel')
    list_filter = ['nivel', 'cargo_classe', 'nivel_padrao']
    form = NivelVencimentoTAEPorClasseEPadraoForm


admin.site.register(NivelVencimentoTAEPorClasseEPadrao, NivelVencimentoTAEPorClasseEPadraoAdmin)


# Adicionado por IFMA/Tássio em outubro de 2017.
class ValorPorNivelVencimentoTAEAdmin(ModelAdminPlus):
    list_display = ('nivel', 'valor', 'data_inicio', 'data_fim')
    ordering = ('nivel', '-data_fim')
    list_filter = ['nivel']
    date_hierarchy = 'data_inicio'
    list_display_icons = True
    form = ValorPorNivelVencimentoTAEForm

    def get_queryset(self, request):
        queryset = super(ValorPorNivelVencimentoTAEAdmin, self).get_queryset(request)
        return queryset.filter(nivel__categoria='tecnico_administrativo')

    def get_urls(self):
        urls = super(ValorPorNivelVencimentoTAEAdmin, self).get_urls()
        my_urls = [path('atualizar_valores/', self.admin_site.admin_view(self.atualizar_valores))]
        return my_urls + urls

    def atualizar_valores(self, request):
        sucesso, str = atualizar_tabelas_de_vencimento_tae()
        if sucesso:
            str = 'Os valores foram atualizados.'
        return httprr(request.META.get('HTTP_REFERER', '.'), str, tag=sucesso and 'success' or 'error')

    def get_action_bar(self, request):
        items = super(ValorPorNivelVencimentoTAEAdmin, self).get_action_bar(request)
        if 'conteudoportal' in settings.INSTALLED_APPS_SUAP:
            items.append(dict(url='/admin/calculos_pagamentos/valorpornivelvencimento/atualizar_valores/', label='Atualizar valores a partir das Tabelas de Vencimentos de TAEs'))
        return items


admin.site.register(ValorPorNivelVencimento, ValorPorNivelVencimentoTAEAdmin)


# Adicionado por IFMA/Tássio em outubro de 2017.
class ValorPorNivelVencimentoDocenteAdmin(ModelAdminPlus):
    list_display = ('nivel', 'jornada_trabalho', 'valor', 'data_inicio', 'data_fim')
    ordering = ('nivel', 'jornada_trabalho', '-data_fim')
    list_filter = ['nivel', 'jornada_trabalho']
    date_hierarchy = 'data_inicio'
    list_display_icons = True
    form = ValorPorNivelVencimentoDocenteForm
    fieldsets = (('', {'fields': ('nivel', 'jornada_trabalho', 'valor', 'data_inicio', 'data_fim')}),)

    def get_urls(self):
        urls = super(ValorPorNivelVencimentoDocenteAdmin, self).get_urls()
        my_urls = [path('atualizar_valores/', self.admin_site.admin_view(self.atualizar_valores))]
        return my_urls + urls

    def atualizar_valores(self, request):
        sucesso, str = atualizar_tabelas_de_vencimento_docente()
        if sucesso:
            str = 'Os valores foram atualizados.'
        return httprr(request.META.get('HTTP_REFERER', '.'), str, tag=sucesso and 'success' or 'error')

    def get_action_bar(self, request):
        items = super(ValorPorNivelVencimentoDocenteAdmin, self).get_action_bar(request)
        if 'conteudoportal' in settings.INSTALLED_APPS_SUAP:
            items.append(
                dict(url='/admin/calculos_pagamentos/valorpornivelvencimentodocente/atualizar_valores/', label='Atualizar valores a partir das Tabelas de Vencimentos de Docentes')
            )
        return items


admin.site.register(ValorPorNivelVencimentoDocente, ValorPorNivelVencimentoDocenteAdmin)


# Adicionado por IFMA/Tássio em outubro de 2017.
class ValorRetribuicaoTitulacaoAdmin(ModelAdminPlus):
    list_display = ('nivel', 'jornada_trabalho', 'get_titulacoes_as_string', 'valor', 'data_inicio', 'data_fim')
    ordering = ('nivel', 'jornada_trabalho', '-data_inicio')
    list_filter = ['nivel', 'jornada_trabalho', 'titulacoes']
    date_hierarchy = 'data_inicio'
    list_display_icons = True
    form = ValorRetribuicaoTitulacaoForm

    def get_titulacoes_as_string(self, obj):
        return obj.get_titulacoes_as_string()

    get_titulacoes_as_string.short_description = 'Titulações'

    def get_urls(self):
        urls = super(ValorRetribuicaoTitulacaoAdmin, self).get_urls()
        my_urls = [path('atualizar_valores/', self.admin_site.admin_view(self.atualizar_valores))]
        return my_urls + urls

    def atualizar_valores(self, request):
        sucesso, str = atualizar_tabelas_de_vencimento_docente()
        if sucesso:
            str = 'Os valores foram atualizados.'
        return httprr(request.META.get('HTTP_REFERER', '.'), str, tag=sucesso and 'success' or 'error')

    def get_action_bar(self, request):
        items = super(ValorRetribuicaoTitulacaoAdmin, self).get_action_bar(request)
        if 'conteudoportal' in settings.INSTALLED_APPS_SUAP:
            items.append(
                dict(url='/admin/calculos_pagamentos/valorretribuicaotitulacao/atualizar_valores/', label='Atualizar valores a partir das Tabelas de Vencimentos de Docentes')
            )
        return items


admin.site.register(ValorRetribuicaoTitulacao, ValorRetribuicaoTitulacaoAdmin)


# Adicionado por IFMA/Tássio em outubro de 2017.
class PortariaFisicaInline(TabularInlinePlus):
    model = PortariaFisica
    min_num = 1
    extra = 0
    formset = PortariaFisicaFormSet

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'processo':
            kwargs = {'widget': AutocompleteWidgetOld(search_fields=Processo.SEARCH_FIELDS, autoFill=False)}
            return db_field.formfield(**kwargs)
        elif db_field.name == 'processo_eletronico':
            kwargs = {'widget': AutocompleteWidgetOld(search_fields=ProcessoEletronico.SEARCH_FIELDS, autoFill=False)}
            return db_field.formfield(**kwargs)
        return super(PortariaFisicaInline, self).formfield_for_dbfield(db_field, **kwargs)


# Classe geral para períodos inlines
class PeriodoInline(InlineSemAddButton):
    min_num = 1
    extra = 0

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'titulacao':
            queryset = Titulacao.objects.filter(codigo__gte='24', codigo__lte='27') | Titulacao.objects.filter(codigo__gte='48', codigo__lte='50')
            kwargs = {'queryset': queryset.order_by('id')}
            return db_field.formfield(**kwargs)
        if db_field.name == 'iq':
            kwargs = {'widget': forms.RadioSelect, 'choices': IQ_CHOICES, 'initial': 0}
            return db_field.formfield(**kwargs)
        return super(PeriodoInline, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em maio de 2018 - Classe geral para admins de cálculos.
class CalculoAdmin(ModelAdminPlus):
    change_form_template = (
        'comum/templates/admin/change_form_com_suporte_a_widgets_inlines.html'
    )  # IFMA/Tássio: html com correções de scripts para funcionarem widgets de data e autocompletar.
    list_display_icons = True
    list_display = ('id', 'servidor', 'data_criacao', 'atestador', 'get_portarias', 'justificativa_safe', 'get_total', 'get_situacao_pagamento', 'excluido')
    ordering = ('-id',)
    search_fields = ('id', 'servidor__nome', 'servidor__matricula', 'portariafisica__processo__numero_processo', 'portariafisica__numero')
    list_filter = ['portariafisica__campus', FeriasFilter, GratificacaoFilter, TipoServidorFilter, 'excluido']
    date_hierarchy = 'portariafisica__data_portaria'
    form = CalculoForm

    fieldsets = (
        ('Dados do Servidor', {'fields': ('servidor', 'justificativa')}),
        (None, {'fields': ('observacoes',)}),
        ('Atesto que todas as informações acima estão corretamente preenchidas', {'fields': ('atesto',)}),
    )

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def justificativa_safe(self, obj):
        return mark_safe(obj.justificativa)

    justificativa_safe.short_description = 'Justificativa'

    def response_add(self, request, obj):
        if "_continue" in request.POST or "_addanother" in request.POST or "popup" in request.POST:
            return super(type(self), self).response_add(request, obj)
        else:
            msg = '{} cadastrado com sucesso.'.format(str(obj))
            return httprr(obj.get_absolute_url(), msg)

    def response_change(self, request, obj):
        if "_continue" in request.POST or "_addanother" in request.POST or "popup" in request.POST:
            return super(type(self), self).response_change(request, obj)
        else:
            msg = '{} modificado com sucesso.'.format(str(obj))
            return httprr(obj.get_absolute_url(), msg)

    # Colocado aqui para não ser executado quando da atualização do total do cálculo no save do modelo.
    def save_model(self, request, obj, form, change):
        obj.atestador = request.user
        obj.save()

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'servidor':
            queryset = Servidor.objects.ativos()
            widget = AutocompleteWidgetOld(search_fields=Servidor.SEARCH_FIELDS)
            kwargs = {'queryset': queryset, 'widget': widget}
            return db_field.formfield(**kwargs)
        return super(CalculoAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def get_portarias(self, obj):
        def get_total(self, obj):
            return mask_money(obj.valor_capital + obj.valor_custeio)

        lista = ["<ul>"]
        for portaria in obj.portariafisica_set.all():
            processo = (
                portaria.processo
                if portaria.processo
                else mark_safe('<a href="/protocolo/processo/{}/">{}</a>'.format(portaria.processo_eletronico.id, portaria.processo_eletronico))
            )
            lista.append("<li>Portaria nº {} de {} / {}</li>".format(portaria.numero, portaria.data_portaria.strftime('%d/%m/%Y'), processo))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_portarias.short_description = 'Portaria/Processo'

    def get_situacao_calculo(self, obj):
        if obj.pagamentos.exists():
            return obj.pagamentos.first().get_situacao_pagamento()
        else:
            return '-'

    get_situacao_calculo.short_description = 'Situação do pagamento'

    def get_total(self, obj):
        return mask_money(obj.total)

    get_total.short_description = 'Total'

    def get_situacao_pagamento(self, obj):
        if obj.pagamentos.exists():
            return obj.pagamentos.last().get_situacao_pagamento()
        else:
            return '-'

    get_situacao_pagamento.short_description = 'Pagamento'


# Classe geral para férias inlines.
class FeriasInline(InlineSemAddButton):
    formfield_overrides = {models.PositiveIntegerField: {'widget': forms.IntegerWidget}}
    min_num = 1
    extra = 0
    fields = [('mes', 'ano'), 'ano_referencia']


# Classe geral de admin de periodos; usada para acrescentar as férias referentes a um período.
class PeriodoAdmin(ModelAdminPlus):
    change_form_template = (
        'comum/templates/admin/change_form_com_suporte_a_widgets_inlines.html'
    )  # IFMA/Tássio: html com correções de scripts para funcionarem widgets de data e autocompletar.
    fieldsets = (('', {'fields': []}),)

    def response_change(self, request, obj):
        if "_continue" in request.POST or "_addanother" in request.POST or "popup" in request.POST:
            return super(type(self), self).response_change(request, obj)
        else:
            msg = 'Férias adicionadas com sucesso.'
            return httprr('..', msg)

    def has_delete_permission(self, request, obj=None):
        return False


# Adicionado por IFMA/Tássio em agosto de 2018.
class ValoresFuncaoDetalhadosAdmin(ModelAdminPlus):
    list_display = ('valorporfuncao', 'valor_venc', 'valor_gadf', 'valor_age')
    ordering = ('valorporfuncao__funcao', '-valorporfuncao__data_fim')
    list_filter = ['valorporfuncao__funcao__nome']
    date_hierarchy = 'valorporfuncao__data_inicio'
    list_display_icons = True

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'valorporfuncao':
            kwargs = {'widget': AutocompleteWidget(readonly=True)}
            return db_field.formfield(**kwargs)
        return super(ValoresFuncaoDetalhadosAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    def response_add(self, request, obj):
        if "_continue" in request.POST or "_addanother" in request.POST or "popup" in request.POST:
            return super(ValoresFuncaoDetalhadosAdmin, self).response_add(request, obj)
        else:
            msg = '{0} cadastrados com sucesso.'.format(obj._meta.verbose_name)
            return httprr('..', msg)

    def response_change(self, request, obj):
        if "_continue" in request.POST or "_addanother" in request.POST or "popup" in request.POST:
            return super(ValoresFuncaoDetalhadosAdmin, self).response_change(request, obj)
        else:
            msg = '{0} editados com sucesso.'.format(obj._meta.verbose_name)
            return httprr('..', msg)


admin.site.register(ValoresFuncaoDetalhados, ValoresFuncaoDetalhadosAdmin)


# Adicionado por IFMA/Tássio em maio de 2017.
class ValorPorFuncaoAdmin(ModelAdminPlus):
    list_display = ('funcao', 'valor', 'data_inicio', 'data_fim', 'valores_detalhados')
    ordering = ('funcao', '-data_fim')
    list_filter = ['funcao__nome']
    date_hierarchy = 'data_inicio'
    list_display_icons = True

    def valores_detalhados(self, obj):
        if "FG" not in obj.funcao.nome[:2]:
            return
        valores = ''
        if not ValoresFuncaoDetalhados.objects.filter(valorporfuncao__id=obj.id).exists():
            label = 'Informar Valores Por Rubricas'
            url = '/admin/calculos_pagamentos/valoresfuncaodetalhados/add/?valorporfuncao={}'.format(obj.id)
        else:
            label = 'Editar Valores Por Rubricas'
            url = '/admin/calculos_pagamentos/valoresfuncaodetalhados/{}/change/'.format(obj.valoresfuncaodetalhados.id)
            valores = 'Vencimento: R${}<br/>GADF: R${}<br/>AGE: R${}<br/><br/>'.format(
                obj.valoresfuncaodetalhados.valor_venc, obj.valoresfuncaodetalhados.valor_gadf, obj.valoresfuncaodetalhados.valor_age
            )

        return mark_safe("{0}<a class='btn neutral' title='{1}' href='{2}'>{1}</a> ".format(valores, label, url))

    valores_detalhados.short_description = 'Valores Por Rubricas'


admin.site.register(ValorPorFuncao, ValorPorFuncaoAdmin)


# Adicionado por IFMA/Tássio em fevereiro de 2018.
class ValorAlimentacaoAdmin(ModelAdminPlus):
    list_display = ('valor', 'data_inicio', 'data_fim')
    ordering = ['-data_fim']
    date_hierarchy = 'data_inicio'
    list_display_icons = True


admin.site.register(ValorAlimentacao, ValorAlimentacaoAdmin)


# # # CÁLCULO DE SUBSTITUIÇÃO # # #

# Adicionado por IFMA/Tássio em agosto de 2018.
class PeriodoSubstituicaoInline(PeriodoInline):
    model = PeriodoSubstituicao
    fields = [('data_inicio', 'data_fim')]
    formset = PeriodoSubstituicaoFormSet


# Adicionado por IFMA/Tássio em setembro de 2018.
class CalculoSubstituicaoAdmin(CalculoAdmin):
    # list_display_icons = False
    # list_display = ('icones', 'id', 'get_servidor', 'titular', 'resultado')

    list_display_icons = True

    search_fields = ('id', 'portariafisica__processo__numero_processo', 'portariafisica__numero', 'servidor__nome', 'titular__nome', 'servidor__matricula', 'titular__matricula')
    list_filter = ['campus', 'motivo_substituicao', 'portariafisica__campus', GratificacaoFilter, 'excluido']
    date_hierarchy = 'portariafisica__data_portaria'
    form = CalculoSubstituicaoForm
    inlines = [PortariaFisicaInline, PeriodoSubstituicaoInline]  # Posicionado no local correto via jquery em PosicionaInlines.js

    fieldsets = (
        ('Dados do Servidor Substituto', {'fields': ('servidor', 'funcao_servidor_substituto', ('data_inicio_funcao_servidor_substituto', 'data_fim_funcao_servidor_substituto'))}),
        ('Dados do Servidor Titular', {'fields': ('titular', 'funcao_servidor_titular')}),
        ('Dados da Substituição', {'fields': (('campus', 'motivo_substituicao'),)}),
        (None, {'fields': ('observacoes',)}),
        ('Atesto que todas as informações acima estão corretamente preenchidas', {'fields': ('atesto',)}),
    )

    """
    def icones(self, obj):
        # IFMA - Leonardo
        if obj.documento and obj.documento.tem_assinaturas or obj.pagamentos.exists():
            return mark_safe(icon('view', obj.get_absolute_url(), "Visualizar"))
        # IFMA - Fim
        return mark_safe(
            icon('view', obj.get_absolute_url(), "Visualizar")
            + icon('edit', reverse('admin:calculos_pagamentos_calculosubstituicao_change', args=(obj.id,)), "Editar")
            + icon('delete', reverse('admin:calculos_pagamentos_calculosubstituicao_delete', args=(obj.id,)), "Remover")
        )

    icones.short_description = 'Ações'
    """

    """
    def get_servidor(self, obj):
        return obj.servidor
    get_servidor.short_description = 'Servidor Substituto'
    """

    def get_queryset(self, request):
        queryset = super(CalculoSubstituicaoAdmin, self).get_queryset(request)
        if not request.user.has_perm('rh.eh_rh_sistemico'):
            queryset = queryset.filter(campus=get_uo(request.user))
        return queryset

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'servidor':
            kwargs = {'widget': AutocompleteWidgetOld(search_fields=Servidor.SEARCH_FIELDS, autoFill=False), 'label': 'Servidor Substituto'}
            return db_field.formfield(**kwargs)
        elif db_field.name == 'titular':
            kwargs = {'widget': AutocompleteWidgetOld(search_fields=Servidor.SEARCH_FIELDS, autoFill=False), 'label': 'Servidor Titular'}
            return db_field.formfield(**kwargs)
        return super(CalculoSubstituicaoAdmin, self).formfield_for_dbfield(db_field, **kwargs)


admin.site.register(CalculoSubstituicao, CalculoSubstituicaoAdmin)


# # # CÁLCULO DE PROGRESSÃO # # #

# Adicionado por IFMA/Tássio em outubro de 2017.
class PeriodoCalculoProgressaoInline(PeriodoInline):
    model = PeriodoCalculoProgressao
    fields = [
        ('data_inicio', 'data_fim'),
        ('nivel_passado', 'nivel'),
        ('padrao_vencimento_passado', 'padrao_vencimento_novo'),
        ('jornada_passada', 'jornada'),
        ('titulacao_passada', 'titulacao_nova'),
        'anuenio',
        'adicionais',
        'iq',
    ]
    formset = PeriodoCalculoProgressaoFormSet
    form = PeriodoCalculoProgressaoForm

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'nivel':
            kwargs = {'label': "Nível de Vencimento Novo"}
            return db_field.formfield(**kwargs)
        if db_field.name == 'jornada':
            kwargs = {'label': "Jornada de Trabalho Nova"}
            return db_field.formfield(**kwargs)
        if db_field.name in ('titulacao_passada', 'titulacao_nova'):
            queryset = Titulacao.objects.filter(codigo__gte='24', codigo__lte='27') | Titulacao.objects.filter(codigo__gte='48', codigo__lte='50')
            kwargs = {'queryset': queryset.order_by('id')}
            return db_field.formfield(**kwargs)
        if db_field.name == 'insalubridade':
            kwargs = {'widget': forms.RadioSelect, 'choices': INSALUBRIDADE_CHOICES, 'initial': 0}
            return db_field.formfield(**kwargs)
        if db_field.name == 'iq':
            kwargs = {'widget': forms.RadioSelect, 'choices': IQ_CHOICES, 'initial': 0}
            return db_field.formfield(**kwargs)
        return super(PeriodoCalculoProgressaoInline, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em outubro de 2017.
class CalculoProgressaoAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoCalculoProgressaoInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoProgressao, CalculoProgressaoAdmin)


# Adicionado por IFMA/Tássio em novembro de 2017.
class FeriasCalculoProgressaoInline(FeriasInline):
    model = FeriasCalculoProgressao
    formset = FeriasCalculoProgressaoFormSet
    form = FeriasForm


# Adicionado por IFMA/Tássio em novembro de 2017 para acrescentar as férias referentes a um período.
class PeriodoCalculoProgressaoAdmin(PeriodoAdmin):
    inlines = [FeriasCalculoProgressaoInline]


admin.site.register(PeriodoCalculoProgressao, PeriodoCalculoProgressaoAdmin)


# # # CÁLCULO DE PERICULOSIDADE # # #

# Adicionado por IFMA/Tássio em maio de 2018.
class PeriodoPericulosidadeInline(PeriodoInline):
    model = PeriodoPericulosidade
    fields = [('data_inicio', 'data_fim'), 'nivel', 'padrao_vencimento_novo', 'jornada']
    formset = PeriodoPericulosidadeFormSet
    form = PeriodoForm  # Precisa colocar se o servidor do cálculo puder ser TAE


# Adicionado por IFMA/Tássio em maio de 2018.
class CalculoPericulosidadeAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoPericulosidadeInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoPericulosidade, CalculoPericulosidadeAdmin)


# Adicionado por IFMA/Tássio em maio de 2018.
class FeriasPericulosidadeInline(FeriasInline):
    model = FeriasPericulosidade
    formset = FeriasPericulosidadeFormSet
    form = FeriasForm


# Adicionado por IFMA/Tássio em maio de 2018 para acrescentar as férias referentes a um período.
class PeriodoPericulosidadeAdmin(PeriodoAdmin):
    inlines = [FeriasPericulosidadeInline]


admin.site.register(PeriodoPericulosidade, PeriodoPericulosidadeAdmin)


# # # CÁLCULO DE INSALUBRIDADE # # #

# Adicionado por IFMA/Tássio em maio de 2018.
class PeriodoInsalubridadeInline(PeriodoInline):
    model = PeriodoInsalubridade
    fields = [('data_inicio', 'data_fim'), 'nivel', 'padrao_vencimento_novo', 'jornada', 'insalubridade']
    formset = PeriodoInsalubridadeFormSet
    form = PeriodoForm  # Precisa colocar se o servidor do cálculo puder ser TAE

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'insalubridade':
            kwargs = {'widget': forms.RadioSelect, 'choices': INSALUBRIDADE_CHOICES[1:]}
            return db_field.formfield(**kwargs)
        return super(PeriodoInsalubridadeInline, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em maio de 2018.
class CalculoInsalubridadeAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoInsalubridadeInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoInsalubridade, CalculoInsalubridadeAdmin)


# Adicionado por IFMA/Tássio em maio de 2018.
class FeriasInsalubridadeInline(FeriasInline):
    model = FeriasInsalubridade
    formset = FeriasInsalubridadeFormSet
    form = FeriasForm


# Adicionado por IFMA/Tássio em maio de 2018 para acrescentar as férias referentes a um período.
class PeriodoInsalubridadeAdmin(PeriodoAdmin):
    inlines = [FeriasInsalubridadeInline]


admin.site.register(PeriodoInsalubridade, PeriodoInsalubridadeAdmin)


# # # CÁLCULO DE RETRIBUIÇÃO POR TITULAÇÃO # # #

# Adicionado por IFMA/Tássio em maio de 2018.
class PeriodoRTInline(PeriodoInline):
    model = PeriodoRT
    fields = [('data_inicio', 'data_fim'), 'nivel', 'jornada', ('titulacao_passada', 'titulacao_nova')]
    formset = PeriodoRTFormSet

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in ('titulacao_passada', 'titulacao_nova'):
            queryset = Titulacao.objects.filter(codigo__gte='24', codigo__lte='27')
            kwargs = {'queryset': queryset.order_by('id')}
            return db_field.formfield(**kwargs)
        return super(PeriodoRTInline, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em maio de 2018.
class CalculoRTAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoRTInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoRT, CalculoRTAdmin)


# Adicionado por IFMA/Tássio em maio de 2018.
class FeriasRTInline(FeriasInline):
    model = FeriasRT
    formset = FeriasRTFormSet
    form = FeriasForm


# Adicionado por IFMA/Tássio em maio de 2018 para acrescentar as férias referentes a um período.
class PeriodoRTAdmin(PeriodoAdmin):
    inlines = [FeriasRTInline]


admin.site.register(PeriodoRT, PeriodoRTAdmin)


# # # CÁLCULO DE RSC # # #

# Adicionado por IFMA/Tássio em maio de 2018.
class PeriodoRSCInline(PeriodoInline):
    model = PeriodoRSC
    fields = [('data_inicio', 'data_fim'), 'nivel', 'jornada', ('titulacao_passada', 'titulacao_nova')]
    formset = PeriodoRTFormSet  # Esse formset funciona aqui também

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'titulacao_passada':
            queryset = Titulacao.objects.filter(codigo__gte='24', codigo__lte='27')
            kwargs = {'queryset': queryset.order_by('id')}
            return db_field.formfield(**kwargs)
        if db_field.name == 'titulacao_nova':
            queryset = Titulacao.objects.filter(codigo__gte='48', codigo__lte='50')
            kwargs = {'queryset': queryset.order_by('id')}
            return db_field.formfield(**kwargs)
        return super(PeriodoRSCInline, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em maio de 2018.
class CalculoRSCAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoRSCInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoRSC, CalculoRSCAdmin)


# Adicionado por IFMA/Tássio em maio de 2018.
class FeriasRSCInline(FeriasInline):
    model = FeriasRSC
    formset = FeriasRTFormSet  # Esse formset funciona aqui também
    form = FeriasForm


# Adicionado por IFMA/Tássio em maio de 2018 para acrescentar as férias referentes a um período.
class PeriodoRSCAdmin(PeriodoAdmin):
    inlines = [FeriasRSCInline]


admin.site.register(PeriodoRSC, PeriodoRSCAdmin)


# # # CÁLCULO DE INCENTIVO À QUALIFICAÇÃO # # #

# Adicionado por IFMA/Tássio em maio de 2018.
class PeriodoIQInline(PeriodoInline):
    model = PeriodoIQ
    fields = [('data_inicio', 'data_fim'), 'padrao_vencimento_novo', 'jornada', ('iq_passado', 'iq_novo')]
    formset = PeriodoIQFormSet
    form = PeriodoForm  # Precisa colocar se o servidor do cálculo puder ser TAE

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'iq_passado':
            kwargs = {'widget': forms.RadioSelect, 'choices': IQ_CHOICES, 'initial': 0}
            return db_field.formfield(**kwargs)
        if db_field.name == 'iq_novo':
            kwargs = {'widget': forms.RadioSelect, 'choices': IQ_CHOICES[1:]}
            return db_field.formfield(**kwargs)
        return super(PeriodoIQInline, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em maio de 2018.
class CalculoIQAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoIQInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoIQ, CalculoIQAdmin)


# Adicionado por IFMA/Tássio em maio de 2018.
class FeriasIQInline(FeriasInline):
    model = FeriasIQ
    formset = FeriasIQFormSet
    form = FeriasForm


# Adicionado por IFMA/Tássio em maio de 2018 para acrescentar as férias referentes a um período.
class PeriodoIQAdmin(PeriodoAdmin):
    inlines = [FeriasIQInline]


admin.site.register(PeriodoIQ, PeriodoIQAdmin)


# # # CÁLCULO DE MUDANÇA DE REGIME # # #

# Adicionado por IFMA/Tássio em julho de 2018.
class PeriodoMudancaRegimeInline(PeriodoInline):
    model = PeriodoMudancaRegime
    fields = [('data_inicio', 'data_fim'), 'nivel', 'padrao_vencimento_novo', ('jornada_passada', 'jornada'), 'titulacao_nova', 'anuenio', 'adicionais', 'iq']
    formset = PeriodoMudancaRegimeFormSet
    form = PeriodoCalculoProgressaoForm  # Serve

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'jornada':
            kwargs = {'label': "Jornada de Trabalho Nova"}
            return db_field.formfield(**kwargs)
        if db_field.name == 'titulacao_nova':
            queryset = Titulacao.objects.filter(codigo__gte='24', codigo__lte='27') | Titulacao.objects.filter(codigo__gte='48', codigo__lte='50')
            kwargs = {'queryset': queryset.order_by('id')}
            return db_field.formfield(**kwargs)
        if db_field.name == 'iq':
            kwargs = {'widget': forms.RadioSelect, 'choices': IQ_CHOICES, 'initial': 0}
            return db_field.formfield(**kwargs)
        return super(PeriodoMudancaRegimeInline, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em julho de 2018.
class CalculoMudancaRegimeAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoMudancaRegimeInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoMudancaRegime, CalculoMudancaRegimeAdmin)


# Adicionado por IFMA/Tássio em julho de 2018.
class FeriasMudancaRegimeInline(FeriasInline):
    model = FeriasMudancaRegime
    formset = FeriasMudancaRegimeFormSet
    form = FeriasForm


# Adicionado por IFMA/Tássio em julho de 2018 para acrescentar as férias referentes a um período.
class PeriodoMudancaRegimeAdmin(PeriodoAdmin):
    inlines = [FeriasMudancaRegimeInline]


admin.site.register(PeriodoMudancaRegime, PeriodoMudancaRegimeAdmin)


# # # CÁLCULO DE AUXÍLIO TRANSPORTE # # #

# Adicionado por IFMA/Tássio em julho de 2018.
class PeriodoTransporteInline(PeriodoInline):
    model = PeriodoTransporte
    fields = [('data_inicio', 'data_fim'), 'nivel', 'padrao_vencimento_novo', 'jornada', 'quant_passagens', 'valor_passagem', 'dias_uteis_mes_incompleto']
    formset = PeriodoTransporteFormSet
    form = PeriodoForm  # Precisa colocar se o servidor do cálculo puder ser TAE


# Adicionado por IFMA/Tássio em julho de 2018.
class CalculoTransporteAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoTransporteInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoTransporte, CalculoTransporteAdmin)


# # # CÁLCULO DE ABONO DE PERMANÊNCIA # # #

# Adicionado por IFMA/Tássio em agosto de 2018.
class PeriodoPermanenciaInline(PeriodoInline):
    model = PeriodoPermanencia
    fields = [('data_inicio', 'data_fim'), 'valor_mensal_abono']
    formset = PeriodoPermanenciaFormSet


# Adicionado por IFMA/Tássio em agosto de 2018.
class CalculoPermanenciaAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoPermanenciaInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoPermanencia, CalculoPermanenciaAdmin)


# # # CÁLCULOS DE DESIGNAÇÃO/DISPENSA DE FG/FUC E NOMEAÇÃO/EXONERAÇÃO DE CD # # #

# Adicionado por IFMA/Tássio em agosto de 2018.
class PeriodoFGsCDsInline(PeriodoInline):
    model = PeriodoFGsCDs
    formset = PeriodoFGsCDsFormSet

    def __init__(self, parent_model, admin_site):
        super(PeriodoFGsCDsInline, self).__init__(parent_model, admin_site)
        if self.parent_model in [CalculoExoneracaoCD, CalculoDispensaFG]:
            self.fields = [('data_inicio', 'data_fim'), 'funcao', 'meses_devidos_grat_nat', 'meses_indevidos_grat_nat']
        else:
            self.fields = [('data_inicio', 'data_fim'), 'funcao', 'meses_devidos_grat_nat']

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'funcao':
            if 'CD' in self.parent_model._meta.verbose_name:
                queryset = FuncaoCodigo.objects.filter(nome__contains='CD')
            else:
                queryset = FuncaoCodigo.objects.exclude(nome__contains='CD')
            kwargs = {'queryset': queryset}
            return db_field.formfield(**kwargs)
        return super(PeriodoFGsCDsInline, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em agosto de 2018.
class CalculoNomeacaoCDAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoFGsCDsInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoNomeacaoCD, CalculoNomeacaoCDAdmin)


# Adicionado por IFMA/Tássio em agosto de 2018.
class CalculoExoneracaoCDAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoFGsCDsInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoExoneracaoCD, CalculoExoneracaoCDAdmin)


# Adicionado por IFMA/Tássio em agosto de 2018.
class CalculoDesignacaoFGAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoFGsCDsInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoDesignacaoFG, CalculoDesignacaoFGAdmin)


# Adicionado por IFMA/Tássio em agosto de 2018.
class CalculoDispensaFGAdmin(CalculoAdmin):
    inlines = [PortariaFisicaInline, PeriodoFGsCDsInline]  # Posicionado no local correto via jquery em PosicionaInlines.js


admin.site.register(CalculoDispensaFG, CalculoDispensaFGAdmin)


# Adicionado por IFMA/Tássio em agosto de 2018.
class FeriasFGsCDsInline(FeriasInline):
    model = FeriasFGsCDs
    formset = FeriasFGsCDsFormSet
    form = FeriasForm


# Adicionado por IFMA/Tássio em agosto de 2018 para acrescentar as férias referentes a um período.
class PeriodoFGsCDsAdmin(PeriodoAdmin):
    inlines = [FeriasFGsCDsInline]


admin.site.register(PeriodoFGsCDs, PeriodoFGsCDsAdmin)


# # # CÁLCULOS DE ACERTO DE TÉRMINO DE CONTRATO TEMPORÁRIO # # #

# Adicionado por IFMA/Tássio em março de 2018.
class PeriodoTerminoContratoInline(PeriodoInline):
    model = PeriodoTerminoContrato
    formset = PeriodoTerminoContratoFormSet

    def __init__(self, parent_model, admin_site):
        super(PeriodoTerminoContratoInline, self).__init__(parent_model, admin_site)
        self.fields = [
            ('data_inicio', 'data_fim', 'dias_uteis'),
            'jornada',
            'titulacao',
            'iq',
            'periculosidade',
            'insalubridade',
            'transporte',
            ('data_inicio_desc_alim', 'data_fim_desc_alim'),
        ]


# Adicionado por IFMA/Tássio em março de 2018.
class CalculoTerminoContratoAdmin(CalculoAdmin):
    form = CalculoTerminoContratoForm
    list_filter = ['portariafisica__campus', TipoServidorFilter, 'excluido']
    inlines = [PortariaFisicaInline, PeriodoTerminoContratoInline]  # Posicionado no local correto via jquery em PosicionaInlines.js

    fieldsets = (
        ('Dados do Servidor', {'fields': ('servidor', 'justificativa')}),
        ('Dados do Cálculo', {'fields': ('contrato', 'meses_devidos_ferias', 'meses_devidos_grat_nat', 'total_adiantamento_grat_nat', 'pss_grat_nat')}),
        (None, {'fields': ('observacoes',)}),
        ('Atesto que todas as informações acima estão corretamente preenchidas', {'fields': ('atesto',)}),
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'servidor':
            queryset = Servidor.objects.all()
            widget = AutocompleteWidgetOld(search_fields=Servidor.SEARCH_FIELDS)
            kwargs = {'queryset': queryset, 'widget': widget}
            return db_field.formfield(**kwargs)
        return super(CalculoTerminoContratoAdmin, self).formfield_for_dbfield(db_field, **kwargs)


# Adicionado por IFMA/Tássio em março de 2018.
class CalculoTerminoContratoProfSubsAdmin(CalculoTerminoContratoAdmin):
    pass


admin.site.register(CalculoTerminoContratoProfSubs, CalculoTerminoContratoProfSubsAdmin)


# Adicionado por IFMA/Tássio em março de 2018.
class CalculoTerminoContratoInterpLibrasAdmin(CalculoTerminoContratoAdmin):
    pass


admin.site.register(CalculoTerminoContratoInterpLibras, CalculoTerminoContratoInterpLibrasAdmin)
