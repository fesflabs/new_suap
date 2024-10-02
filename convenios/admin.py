# -*- coding: utf-8 -*-

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe

from comum.utils import get_uo, get_sigla_reitoria
from convenios.forms import ConvenioForm, ProfissionalLiberalForm
from convenios.models import Convenio, TipoConvenio, TipoAnexo, SituacaoConvenio, AnexoConvenio, ProfissionalLiberal, ConselhoProfissional
from djtools.contrib.admin import ModelAdminPlus
from djtools.templatetags.filters import in_group, format_
from djtools.templatetags.tags import icon
from rh.models import UnidadeOrganizacional, PessoaExterna


class CampusFilter(admin.SimpleListFilter):
    title = "Campus"
    parameter_name = 'descricao'

    def lookups(self, request, model_admin):
        campus = UnidadeOrganizacional.objects.suap().all()
        if in_group(request.user, ['Operador de Convênios']):
            sigla_reitoria = get_sigla_reitoria()
            if UnidadeOrganizacional.objects.suap().filter(sigla=sigla_reitoria).exists():
                reitoria = UnidadeOrganizacional.objects.suap().get(sigla=sigla_reitoria)
                campus = UnidadeOrganizacional.objects.suap().filter(id__in=[get_uo(request.user).id, reitoria.id])
            else:
                campus = UnidadeOrganizacional.objects.suap().filter(id=get_uo(request.user).id)
        return campus.values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(uo=self.value())


class TipoConveniadoFilter(admin.SimpleListFilter):
    title = "Tipo de Conveniada"
    parameter_name = 'conveniada'

    def lookups(self, request, model_admin):
        opcoes = (('Profissionais Liberais', 'Profissionais Liberais'), ('Pessoas Jurídicas', 'Pessoas Jurídicas'))

        return opcoes

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'Profissionais Liberais':
                return queryset.filter(vinculos_conveniadas__in=ProfissionalLiberal.objects.values_list('vinculo_pessoa', flat=True))
            elif self.value() == 'Pessoas Jurídicas':
                return queryset.filter(vinculos_conveniadas__pessoa__pessoajuridica__isnull=False).distinct()


class AnoConvenioFilter(admin.SimpleListFilter):
    title = "Ano de Início"
    parameter_name = 'ano'

    def lookups(self, request, model_admin):
        anos = []
        for data in Convenio.objects.all().dates('data_inicio', 'year'):
            anos.append((data.year, data.year))
        anos.reverse()
        return anos

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(data_inicio__year=self.value())


class ConvenioAdmin(ModelAdminPlus):
    form = ConvenioForm
    list_display = ['get_acoes', 'numero', 'uo', 'get_conveniadas_as_string', 'tipo', 'data_inicio', 'get_data_vencimento', 'get_situacao']
    ordering = ('-data_fim',)
    search_fields = ('numero', 'vinculos_conveniadas__pessoa__pessoajuridica__nome_fantasia', 'vinculos_conveniadas__pessoa__pessoajuridica__cnpj', 'vinculos_conveniadas__pessoa__pessoafisica__cpf', 'vinculos_conveniadas__pessoa__nome')
    list_filter = ['situacao', 'tipo', 'uo', TipoConveniadoFilter, AnoConvenioFilter]
    export_to_xls = True
    list_display_icons = False

    def get_acoes(self, obj):
        return mark_safe(''.join([icon('view', '/convenios/convenio/{}/'.format(obj.id)), icon('edit', '/admin/convenios/convenio/{}/change/'.format(obj.id))]))

    get_acoes.short_description = 'Ações'
    get_acoes.allow_tags = 'Ações'

    def get_conveniadas_as_string(self, obj):
        return obj.get_conveniadas_as_string()

    get_conveniadas_as_string.short_description = 'Conveniadas'

    def get_data_vencimento(self, obj):
        return obj.get_data_vencimento().strftime("%d/%m/%y")

    get_data_vencimento.short_description = 'Data de Vencimento'

    def get_situacao(self, obj):
        situacao = obj.get_situacao()
        retorno = '-'
        if situacao.pk == SituacaoConvenio.VIGENTE:
            retorno = '<span class="status status-success">{}</span>'.format(situacao.descricao)
        elif situacao.pk == SituacaoConvenio.VINCENDO:
            retorno = '<span class="status status-alert">{}</span>'.format(situacao.descricao)
        elif situacao.pk == SituacaoConvenio.VENCIDO:
            retorno = '<span class="status status-error">{}</span>'.format(situacao.descricao)
        elif situacao.pk == SituacaoConvenio.RESCINDIDO:
            retorno = '<span class="status status-success">{}</span>'.format(situacao.descricao)
        return mark_safe(retorno)

    get_situacao.short_description = 'Situação'

    def response_change(self, request, obj):
        self.message_user(request, 'Convênio atualizado com sucesso.')
        return HttpResponseRedirect('/convenios/convenio/{}/'.format(obj.pk))

    def response_add(self, request, obj):
        self.message_user(request, 'Convênio cadastrado com sucesso.')
        return HttpResponseRedirect('/convenios/convenio/{}/'.format(obj.pk))

    def get_queryset(self, request, *args, **kwargs):
        qs = super(ConvenioAdmin, self).get_queryset(request, *args, **kwargs)
        if in_group(request.user, ['Operador de Convênios']):
            sigla_reitoria = get_sigla_reitoria()
            if UnidadeOrganizacional.objects.suap().filter(sigla=sigla_reitoria).exists():
                reitoria = UnidadeOrganizacional.objects.suap().get(sigla=sigla_reitoria)
                return qs.filter(uo__in=[get_uo(request.user), reitoria.id])
            else:
                return qs.filter(uo=get_uo(request.user))
        return qs

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super(ConvenioAdmin, self).get_form(request, obj=obj, **kwargs)
        if in_group(request.user, ['Operador de Convênios']):
            qs_uo = UnidadeOrganizacional.objects.suap().filter(id=get_uo(request.user).id)
        else:
            qs_uo = UnidadeOrganizacional.objects.suap().all()
        FormClass.base_fields['uo'].queryset = qs_uo
        return FormClass

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Número', 'Campus', 'Conveniadas', 'Tipo', 'Data de Início', 'Data de Vencimento', 'Situação', 'Possui Anexo Cadastrado']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            tem_anexo = 'Não'
            if AnexoConvenio.objects.filter(convenio=obj).exists():
                tem_anexo = 'Sim'
            empresas = list()
            for empresa in obj.vinculos_conveniadas.all():
                texto = '{}'.format(empresa.pessoa)
                empresas.append(texto)
            conveniadas = ', '.join(empresas)
            row = [idx + 1, obj.numero, obj.uo, conveniadas, obj.tipo, format_(obj.data_inicio), format_(obj.data_fim), obj.situacao, tem_anexo]
            rows.append(row)
        return rows


admin.site.register(Convenio, ConvenioAdmin)


class ProfissionalLiberalAdmin(ModelAdminPlus):
    form = ProfissionalLiberalForm
    list_display = ['vinculo_pessoa', 'numero_registro', 'conselho', 'telefone', 'email']
    search_fields = ('vinculo_pessoa__pessoa__nome', 'vinculo_pessoa__pessoa__pessoafisica__cpf')
    list_display_icons = False
    fieldsets = (
        ('Dados Pessoais', {'fields': ('nome', 'cpf', 'sexo', 'nascimento_data', ('numero_registro', 'conselho'), 'telefone', 'email')}),
        ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'municipio')}),
    )

    def save_model(self, request, obj, form, change):
        if PessoaExterna.objects.filter(cpf=form.cleaned_data.get('cpf')).exists():
            pessoaexterna = PessoaExterna.objects.filter(cpf=form.cleaned_data.get('cpf')).order_by('-id')[0]
        else:
            pessoaexterna = PessoaExterna()
            pessoaexterna.cpf = form.cleaned_data.get('cpf')
        pessoaexterna.nome = form.cleaned_data.get('nome')
        pessoaexterna.sexo = form.cleaned_data.get('sexo')
        pessoaexterna.nascimento_data = form.cleaned_data.get('nascimento_data')
        pessoaexterna.save()
        obj.vinculo_pessoa = pessoaexterna.get_vinculo()
        return super(ProfissionalLiberalAdmin, self).save_model(request, obj, form, change)


admin.site.register(ProfissionalLiberal, ProfissionalLiberalAdmin)


class ConselhoProfissionalAdmin(ModelAdminPlus):
    list_display = ['nome', 'sigla', 'ativo']
    search_fields = ('nome', 'sigla')

    list_display_icons = False


admin.site.register(ConselhoProfissional, ConselhoProfissionalAdmin)


class TipoConvenioAdmin(ModelAdminPlus):
    pass


class TipoAnexoAdmin(ModelAdminPlus):
    pass


class SituacaoConvenioAdmin(ModelAdminPlus):
    pass


admin.site.register(TipoConvenio, TipoConvenioAdmin)
admin.site.register(TipoAnexo, TipoAnexoAdmin)
admin.site.register(SituacaoConvenio, SituacaoConvenioAdmin)
