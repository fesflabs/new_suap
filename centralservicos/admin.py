from django.contrib import admin
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe

from centralservicos.forms import (
    CategoriaServicoForm,
    GrupoServicoForm,
    ServicoForm,
    GrupoAtendimentoForm,
    BaseConhecimentoForm,
    CentroAtendimentoForm,
    GestorAreaServicoForm,
    TagForm,
    MonitoramentoForm,
    RespostaPadraoForm,
    GrupoInteressadoForm,
)
from centralservicos.models import (
    CategoriaServico,
    GrupoServico,
    Servico,
    GrupoAtendimento,
    BaseConhecimento,
    BaseConhecimentoAnexo,
    AtendimentoAtribuicao,
    CentroAtendimento,
    GestorAreaServico,
    Tag,
    PerguntaAvaliacaoBaseConhecimento,
    Monitoramento,
    RespostaPadrao,
    GrupoInteressado,
)
from comum.models import AreaAtuacao
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.db import models
from djtools.forms.widgets import TreeWidget, FilteredSelectMultiplePlus
from djtools.templatetags.filters import in_group
from djtools.templatetags.tags import icon


class PerguntaAvaliacaoBaseConhecimentoAdmin(ModelAdminPlus):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['area'].queryset = GestorAreaServico.minhas_areas(request.user)
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(area__in=GestorAreaServico.minhas_areas(request.user)).distinct()


admin.site.register(PerguntaAvaliacaoBaseConhecimento, PerguntaAvaliacaoBaseConhecimentoAdmin)


class TagAdmin(ModelAdminPlus):
    form = TagForm
    list_filter = ('area',)
    list_display = ('nome', 'area')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['area'].queryset = GestorAreaServico.minhas_areas(request.user)
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(area__in=GestorAreaServico.minhas_areas(request.user)).distinct()


admin.site.register(Tag, TagAdmin)


class GestorAreaServicoAdmin(ModelAdminPlus):
    form = GestorAreaServicoForm
    list_filter = ('area',)
    list_display = ('get_acoes', 'area', 'gestor')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display_links = None

    def has_delete_permission(self, request, obj=None):
        retorno = super().has_delete_permission(request)
        if retorno and obj is not None:
            if self.request.user.has_perm('centralservicos.add_gestorareaservico') and obj.area in obj.minhas_areas(request.user):
                return True
        return False

    def get_acoes(self, obj):
        if self.request.user.has_perm('centralservicos.add_gestorareaservico') and obj.area in obj.minhas_areas(self.request.user):
            return mark_safe(icon('delete', f'/admin/centralservicos/gestorareaservico/{str(obj.id)}/delete/'))
        return None

    get_acoes.short_description = 'Ações'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.has_perm('centralservicos.add_gestorareaservico'):
            form.base_fields['area'].queryset = AreaAtuacao.objects.filter(pk__in=GestorAreaServico.minhas_areas(request.user))
        return form


admin.site.register(GestorAreaServico, GestorAreaServicoAdmin)


class CentroAtendimentoAdmin(ModelAdminPlus):
    form = CentroAtendimentoForm
    search_fields = ('nome', 'area__nome')
    list_filter = ('area',)
    list_display = ('id', 'nome', 'area', 'eh_local')
    list_display_icons = True
    list_per_page = 25

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['area'].queryset = AreaAtuacao.objects.filter(pk__in=GestorAreaServico.minhas_areas(request.user))
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(area__in=GestorAreaServico.minhas_areas(request.user)).distinct()


admin.site.register(CentroAtendimento, CentroAtendimentoAdmin)


class CategoriaServicoAdmin(ModelAdminPlus):
    form = CategoriaServicoForm
    list_filter = ('area',)
    search_fields = ('nome',)
    list_display = ('nome', 'area')
    list_display_icons = True
    list_per_page = 25
    export_to_xls = True

    def to_xls(self, request, queryset, processo):
        header = ['Código', 'Nome', 'Área']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [obj.pk, obj.nome, obj.area]
            rows.append(row)
        return rows

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        areas = GestorAreaServico.minhas_areas(request.user)
        return qs.filter(area__in=areas).distinct()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['area'].queryset = AreaAtuacao.objects.filter(pk__in=GestorAreaServico.minhas_areas(request.user))
        return form


admin.site.register(CategoriaServico, CategoriaServicoAdmin)


class GrupoServicoAdmin(ModelAdminPlus):
    form = GrupoServicoForm
    list_filter = ('categorias__area', 'categorias')
    search_fields = ('nome', 'detalhamento')
    list_display = ('nome', 'detalhamento', 'icone', 'get_categorias')
    list_display_icons = True
    list_per_page = 25
    export_to_xls = True

    def to_xls(self, request, queryset, processo):
        header = ['Código', 'Nome', 'Descrição', 'Código Categoria', 'Descrição Categoria']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            for item in obj.categorias.all():
                row = [obj.pk, obj.nome, obj.detalhamento, item.pk, item.nome]
                rows.append(row)
        return rows

    def get_categorias(self, obj):
        lista = ["<ul>"]
        for categoria in obj.categorias.all():
            lista.append("<li>{}</li>".format(categoria))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_categorias.short_description = "Categorias"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        areas = GestorAreaServico.minhas_areas(request.user)
        form.base_fields['categorias'].queryset = CategoriaServico.objects.filter(area__in=areas)
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        areas = GestorAreaServico.minhas_areas(request.user)
        return qs.filter(categorias__area__in=areas).distinct()


admin.site.register(GrupoServico, GrupoServicoAdmin)


class CentroAtendimentoListFilter(admin.SimpleListFilter):
    title = 'Centro de Atendimento'
    parameter_name = 'centro_atendimento'

    def lookups(self, request, model_admin):
        meus_centros = CentroAtendimento.objects.filter(
            id__in=GrupoAtendimento.objects.filter(models.Q(atendentes=request.user) | models.Q(responsaveis=request.user))
            .order_by('centro_atendimento')
            .values_list('centro_atendimento')
            .distinct()
        )
        centros1 = [(c.id, '* ' + c.nome) for c in meus_centros]
        centros2 = []
        if request.user.is_superuser or request.user.groups.filter(models.Q(name='centralservicos Administrador') | models.Q(name='Auditor')).exists():
            todos_centros = CentroAtendimento.objects.exclude(id__in=meus_centros)
            centros2 = [(c.id, c.nome) for c in todos_centros]

        return centros1 + centros2

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(centros_atendimento__id=self.value())
        else:
            return queryset


class ServicoAdmin(ModelAdminPlus):
    form = ServicoForm
    list_filter = ('area', 'grupo_servico', 'tipo', 'ativo', 'interno', CentroAtendimentoListFilter)
    search_fields = ('nome',)
    list_display = ('nome', 'grupo_servico', 'tipo', 'get_centros_atendimento', 'get_publico_direcionado', 'ativo', 'interno', 'get_quantidade_chamados')
    list_display_icons = True
    list_per_page = 25
    export_to_xls = True

    fieldsets = (
        ('Dados Gerais', {'fields': ('nome', 'tipo', 'area', 'grupo_servico')}),
        ('Atendimento', {'fields': ('centros_atendimento', 'sla_em_horas', 'publico_direcionado')}),
        ('Instruções para Abertura de Chamado', {'fields': ('texto_ajuda', 'texto_modelo')}),
        ('Configurações', {'fields': ('permite_anexos', 'requer_numero_patrimonio', 'permite_abertura_terceiros', 'permite_telefone_adicional')}),
        ('Visibilidade', {'fields': ('interno', 'ativo')}),
    )

    def to_xls(self, request, queryset, processo):
        header = ['Nome', 'Grupo de Serviço', 'Tipo', 'Chamados Realizados']
        rows = [header]

        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [obj.nome, obj.grupo_servico, obj.tipo, obj.get_quantidade_chamados()]
            rows.append(row)
        return rows

    def get_centros_atendimento(self, obj):
        lista = ["<ul>"]
        for centro in obj.centros_atendimento.all():
            lista.append("<li>{}</li>".format(centro))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_centros_atendimento.short_description = "Centros de Atendimento"

    def get_quantidade_chamados(self, obj):
        return Servico.get_quantidade_chamados(obj)

    get_quantidade_chamados.short_description = "Chamados Realizados"

    def get_publico_direcionado(self, obj):
        lista = ["<ul>"]
        if obj.publico_direcionado.exists():
            for publico in obj.publico_direcionado.all():
                lista.append("<li>{}</li>".format(publico.nome))
        else:
            lista.append("<li>Todos</li>")
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_publico_direcionado.short_description = "Público Direcionado"

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pk:
            return self.readonly_fields + ('area',)
        return self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        areas = GestorAreaServico.minhas_areas(request.user)
        grupos_servico = GrupoServico.objects.filter(categorias__area__in=areas)
        form.base_fields['grupo_servico'].queryset = grupos_servico.distinct()
        if obj and obj.id:
            form.base_fields['centros_atendimento'].queryset = CentroAtendimento.objects.filter(area=obj.area)
        else:
            form.base_fields['area'].queryset = areas
            if areas.count() == 1:
                form.base_fields['area'].initial = areas[0]
            form.base_fields['centros_atendimento'].queryset = CentroAtendimento.objects.filter(area__in=areas)
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if in_group(request.user, 'Atendente da Central de Serviços') and not in_group(request.user, 'Gestor da Central de Serviços'):
            areas = GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user)
        else:
            areas = GestorAreaServico.minhas_areas(request.user)
        return qs.filter(grupo_servico__categorias__area__in=areas).distinct()


admin.site.register(Servico, ServicoAdmin)


class GrupoAtendimentoAdmin(ModelAdminPlus):
    form = GrupoAtendimentoForm
    list_filter = ('centro_atendimento__area', 'centro_atendimento', 'campus')
    search_fields = ('nome', 'responsaveis__first_name', 'responsaveis__last_name', 'atendentes__first_name', 'atendentes__last_name')
    list_display = ('nome', 'grupo_atendimento_superior', 'campus', 'get_responsaveis', 'centro_atendimento', 'get_atendentes', 'get_servicos_ativos')
    list_display_icons = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('comum.is_gestor_da_central_de_servicos'):
            areas = GestorAreaServico.minhas_areas(request.user)
        else:
            areas = GrupoAtendimento.objects.filter(responsaveis=request.user).values_list('centro_atendimento__area', flat=True)
        return qs.filter(centro_atendimento__area__in=areas).distinct()

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        return retorno and (not obj or obj.pode_editar(request.user))

    def get_responsaveis(self, obj):
        lista = ["<ul>"]
        for user in obj.responsaveis.all():
            lista.append("<li>{} ({})</li>".format(user, user.pessoafisica.funcionario.setor))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_responsaveis.short_description = "Responsáveis"

    def get_atendentes(self, obj):
        lista = ["<ul>"]
        for user in obj.atendentes.all().order_by('first_name'):
            lista.append("<li>{} ({})</li>".format(user, user.pessoafisica.funcionario.setor))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_atendentes.short_description = "Atendentes"

    def get_servicos_ativos(self, obj):
        servicos_ativos = Servico.objects.filter(ativo=True, centros_atendimento=obj.centro_atendimento)
        if servicos_ativos.exists():
            return servicos_ativos.count()
        else:
            return mark_safe('<span class="false">Nenhum</span>')

    get_servicos_ativos.short_description = "Serviços Ativos"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        if 'grupo_atendimento_superior' in form.base_fields:
            areas = GestorAreaServico.minhas_areas(request.user)
            raizes = GrupoAtendimento.objects.filter(grupo_atendimento_superior__isnull=True, centro_atendimento__area__in=areas)
            form.base_fields['grupo_atendimento_superior'].widget = TreeWidget(root_nodes=list(raizes))

        if request.user.has_perm('comum.is_gestor_da_central_de_servicos'):
            areas = GestorAreaServico.minhas_areas(request.user)
        else:
            areas = GrupoAtendimento.objects.filter(responsaveis=request.user).values_list('centro_atendimento__area', flat=True)
        form.base_fields['centro_atendimento'].queryset = CentroAtendimento.objects.filter(area__in=areas)
        return form


admin.site.register(GrupoAtendimento, GrupoAtendimentoAdmin)


class BaseConhecimentoAnexoInline(admin.StackedInline):
    model = BaseConhecimentoAnexo
    fields = ('anexo',)
    extra = 1


class BaseConhecimentoAdmin(ModelAdminPlus):
    form = BaseConhecimentoForm
    search_fields = ('id', 'titulo', 'resumo', 'solucao', 'tags')
    list_filter = (
        CustomTabListFilter,
        'area',
        'visibilidade',
        'grupos_atendimento',
        'servicos__grupo_servico',
        'servicos__grupo_servico__categorias',
        'servicos',
        'necessita_correcao',
        'atualizado_por',
        'ativo',
    )
    list_display = (
        'id',
        'titulo',
        'area',
        'visibilidade',
        'get_grupos_atendimento',
        'get_servicos',
        'get_supervisionado',
        'get_corrigido',
        'get_estah_disponivel_para_uso',
        'get_situacao',
    )
    list_display_icons = True
    list_per_page = 25
    show_count_on_tabs = True

    fieldsets = (
        ('Dados Gerais', {'fields': ('area', 'titulo', 'resumo', 'solucao', 'tags', 'ativo')}),
        ('Visibilidade', {'fields': ('visibilidade', 'grupos_atendimento', 'servicos')}),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pk:
            return self.readonly_fields + ('area',)
        return self.readonly_fields

    def get_grupos_atendimento(self, obj):
        lista = ["<ul>"]
        if not obj.grupos_atendimento.all().exists():
            lista.append("<li>Todos</li>")
        else:
            for grupo in obj.grupos_atendimento.all():
                lista.append("<li>{}</li>".format(grupo))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_grupos_atendimento.short_description = "Grupos de Atendimento"

    def get_servicos(self, obj):
        lista = ["<ul>"]
        if not obj.servicos.all().exists():
            lista.append("<li>Todos</li>")
        else:
            for servico in obj.servicos.all():
                lista.append("<li>{}</li>".format(servico))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_servicos.short_description = "Serviços"

    def get_supervisionado(self, obj):
        if obj.supervisao_pendente:
            retorno = '<span class="status status-error">Não</span>'
        else:
            retorno = '<span class="status status-success">Sim</span>'
        return mark_safe(retorno)

    get_supervisionado.short_description = 'Supervisionado?'

    def get_corrigido(self, obj):
        if obj.necessita_correcao:
            retorno = '<span class="status status-error">Não</span>'
        else:
            retorno = '<span class="status status-success">Sim</span>'
        return mark_safe(retorno)

    get_corrigido.short_description = 'Corrigido?'

    def get_estah_disponivel_para_uso(self, obj):
        if obj.estah_disponivel_para_uso():
            retorno = '<span class="status status-success">Sim</span>'
        else:
            retorno = '<span class="status status-error">Não</span>'
        return mark_safe(retorno)

    get_estah_disponivel_para_uso.short_description = "Disponível?"

    def get_situacao(self, obj):
        if obj.ativo:
            retorno = '<span class="status status-success">Ativo</span>'
        else:
            retorno = '<span class="status status-error">Inativo</span>'
        return mark_safe(retorno)

    get_situacao.short_description = "Situação"

    inlines = [BaseConhecimentoAnexoInline]

    actions = ['unificar_bases', 'revisar_bases']

    def unificar_bases(self, request, queryset):
        bases = queryset.values_list('id', flat=True)
        ids = ','.join(str(id) for id in bases)
        return HttpResponseRedirect('/centralservicos/baseconhecimento/unificar/?bases={}'.format(ids))

    unificar_bases.short_description = 'Unificar Bases'

    def revisar_bases(self, request, queryset):
        bases = queryset.values_list('id', flat=True)
        ids = ','.join(str(id) for id in bases)
        return HttpResponseRedirect('/centralservicos/baseconhecimento/revisar/?bases={}'.format(ids))

    revisar_bases.short_description = 'Revisar Bases'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm('centralservicos.pode_unificar_baseconhecimento'):
            del actions['unificar_bases']
        if not request.user.has_perm('centralservicos.review_baseconhecimento'):
            del actions['revisar_bases']
        return actions

    def tab_supervisao_pendente(self, request, queryset):
        return queryset.filter(supervisao_pendente=True)

    tab_supervisao_pendente.short_description = 'Pendente de Supervisão'

    def tab_necessita_correcao(self, request, queryset):
        return queryset.filter(necessita_correcao=True)

    tab_necessita_correcao.short_description = 'Pendente de Correção'

    def get_tabs(self, request):
        return ['tab_supervisao_pendente', 'tab_necessita_correcao']

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        areas = GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user)
        meus_grupos = GrupoAtendimento.meus_grupos(request.user)
        return qs.filter(area__in=areas).filter(models.Q(grupos_atendimento__isnull=True) | models.Q(grupos_atendimento__in=meus_grupos)).distinct()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        if not request.user.has_perm('centralservicos.add_public_baseconhecimento'):
            form.base_fields['visibilidade'].choices = BaseConhecimento.VISIBILIDADE_CHOICES_PRIVADA_OU_SIGILOSA
        if 'servico' in request.GET:
            form.base_fields['servicos'].initial = [request.GET['servico']]
        if 'grupo_atendimento' in request.GET:
            form.base_fields['grupos_atendimento'].initial = [request.GET['grupo_atendimento']]
        form.base_fields['grupos_atendimento'].widget = FilteredSelectMultiplePlus('', True)
        form.base_fields['servicos'].widget = FilteredSelectMultiplePlus('', True)

        if 'area' in form.base_fields:
            areas = GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user)
            form.base_fields['area'].queryset = areas
            if areas.count() == 1:
                form.base_fields['area'].initial = areas[0]
            form.base_fields['servicos'].queryset = Servico.objects.filter(centros_atendimento__area__in=areas).order_by('grupo_servico', 'nome').distinct()
            form.base_fields['grupos_atendimento'].queryset = GrupoAtendimento.objects.filter(centro_atendimento__area__in=areas).distinct()
        else:
            form.base_fields['servicos'].queryset = Servico.objects.filter(centros_atendimento__area=obj.area).order_by('grupo_servico', 'nome').distinct()
            form.base_fields['grupos_atendimento'].queryset = GrupoAtendimento.objects.filter(centro_atendimento__area=obj.area).distinct()

        return form


admin.site.register(BaseConhecimento, BaseConhecimentoAdmin)


class GrupoAtendimentoFilter(admin.SimpleListFilter):
    title = "Grupo de Atendimento"
    parameter_name = "grupo_atendimento"

    def lookups(self, request, model_admin):
        return [(grupo.id, grupo.nome) for grupo in GrupoAtendimento.meus_grupos(request.user)]

    def queryset(self, request, queryset):
        if self.value():
            if GrupoAtendimento.meus_grupos(request.user).filter(id=self.value()).exists():
                qs = AtendimentoAtribuicao.objects.filter(grupo_atendimento__id=self.value(), cancelado_em__isnull=True)
                return queryset.filter(pk__in=qs.values('chamado'))
            else:
                return queryset.none()


class MinhasAtribuicoesFilter(admin.SimpleListFilter):
    title = "Atribuições"
    parameter_name = "minhas_atribuicoes"

    def lookups(self, request, model_admin):
        return (('1', 'Atribuídos a mim'), ('2', 'Atribuídos a outros'))

    def queryset(self, request, queryset):
        if self.value() == '1':
            qs = AtendimentoAtribuicao.objects.filter(atribuido_para=request.user, cancelado_em__isnull=True)
            return queryset.filter(pk__in=qs.values('chamado'))

        if self.value() == '2':
            qs = AtendimentoAtribuicao.objects.filter(cancelado_em__isnull=True).exclude(atribuido_para=request.user)
            return queryset.filter(pk__in=qs.values('chamado'))


class MonitoramentoAdmin(ModelAdminPlus):
    form = MonitoramentoForm
    search_fields = ('titulo', 'grupos__nome', 'token')
    list_filter = ('grupos__centro_atendimento__area',)
    list_display = ('titulo', 'get_grupos_atendimento', 'organizar_por_tipo', 'cadastrado_por', 'cadastrado_em')
    list_display_icons = True
    list_per_page = 25

    def get_grupos_atendimento(self, obj):
        lista = ["<ul>"]
        for grupo in obj.grupos.all():
            lista.append("<li>{}</li>".format(grupo))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_grupos_atendimento.short_description = "Grupos de Atendimento"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['grupos'].queryset = GrupoAtendimento.meus_grupos(request.user)
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(grupos__in=GrupoAtendimento.meus_grupos(request.user)).distinct()


admin.site.register(Monitoramento, MonitoramentoAdmin)


class RespostaPadraoAdmin(ModelAdminPlus):
    form = RespostaPadraoForm
    search_fields = ('texto',)
    list_filter = ('atendente',)
    list_display = ('atendente', 'texto')
    list_display_icons = True
    list_per_page = 25

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not (request.user.is_superuser or request.user.groups.filter(name='centralservicos Administrador').exists()):
            return qs.filter(atendente__id=request.user.id)
        return qs

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.atendente = request.user
        super().save_model(request, obj, form, change)


admin.site.register(RespostaPadrao, RespostaPadraoAdmin)


class GrupoInteressadoAdmin(ModelAdminPlus):
    form = GrupoInteressadoForm
    search_fields = ('titulo',)
    list_filter = ('grupo_atendimento',)
    list_display = ('titulo', 'grupo_atendimento', 'get_interessados')
    list_display_icons = True
    list_per_page = 25

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not (request.user.is_superuser or request.user.groups.filter(name='centralservicos Administrador').exists()):
            meus_grupos = GrupoAtendimento.meus_grupos(request.user)
            return qs.filter(grupo_atendimento__in=meus_grupos)
        return qs

    def get_interessados(self, obj):
        lista = ["<ul>"]
        for grupo in obj.interessados.all():
            lista.append("<li>{}</li>".format(grupo))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_interessados.short_description = "Interessados"


admin.site.register(GrupoInteressado, GrupoInteressadoAdmin)
