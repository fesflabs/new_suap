from django.urls import path
from django.contrib import admin
from django.contrib.admin.filters import SimpleListFilter
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe

from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import format_, in_group
from edu.models.diretorias import Diretoria
from etep.forms import AcompanhamentoForm, SolicitacaoAcompanhamentoForm
from etep.models import SolicitacaoAcompanhamento, Categoria, Encaminhamento, Acompanhamento, RegistroAcompanhamento, Atividade, Documento, TipoAtividade, TipoDocumento


class AcompanhamentoAdmin(ModelAdminPlus):
    list_display = ('get_foto', 'get_aluno', 'get_situacao', 'get_categorias', 'get_encaminhamentos', 'get_interessados')
    list_filter = (
        CustomTabListFilter,
        'aluno__curso_campus__diretoria__setor__uo',
        'aluno__curso_campus__diretoria',
        'acompanhamentocategoria__categoria',
        'acompanhamentoencaminhamento__encaminhamento',
    )
    list_display_icons = True
    search_fields = ('id', 'aluno__pessoa_fisica__nome', 'aluno__matricula', 'interessado__vinculo__pessoa__nome')
    ordering = ('-data',)
    form = AcompanhamentoForm
    list_per_page = 25

    def get_foto(self, obj):
        img_src = obj.aluno.get_foto_75x100_url()
        return mark_safe('<img class="img-inside-container" src="%s"/>' % img_src)

    get_foto.short_description = 'Foto'

    def get_aluno(self, obj):
        return mark_safe('<a href="{}?tab=acompanhamento_etep">{}</a>'.format(obj.aluno.get_absolute_url(), obj.aluno))

    get_aluno.short_description = 'Aluno'
    get_aluno.admin_order_field = 'aluno__pessoa_fisica__nome'

    def get_situacao(self, obj):
        situacao = obj.get_situacao()
        if situacao == RegistroAcompanhamento.EM_ACOMPANHAMENTO:
            status = 'alert'
        elif situacao == RegistroAcompanhamento.ACOMPANHAMENTO_FINALIZADO:
            status = 'success'
        else:
            status = 'error'
        return mark_safe('<span class="status status-{}">{}</span>'.format(status, obj.get_situacao_display()))

    get_situacao.short_description = 'Situação'

    def get_interessados(self, obj):
        vinculos = obj.get_interessados()
        lista = ''
        if not vinculos:
            return '-'
        for vinculo in vinculos:
            lista += '<li>%s</li>' % format_(vinculo.pessoa)
        return mark_safe('<ul>%s</ul>' % lista)

    get_interessados.short_description = 'Interessados'

    def get_categorias(self, obj):
        categorias = obj.acompanhamentocategoria_set.all().values_list('categoria__nome', flat=True)
        if not categorias:
            return None
        return mark_safe('<ul><li>%s</li></ul>' % '</li><li>'.join(categorias))

    get_categorias.short_description = 'Categorias'

    def get_encaminhamentos(self, obj):
        encaminhamentos = []
        for encaminhamento in obj.acompanhamentoencaminhamento_set.all().values_list('encaminhamento__nome', flat=True):
            encaminhamentos.append(encaminhamento)
        if not encaminhamentos:
            return None
        return mark_safe('<ul><li>%s</li></ul>' % '</li><li>'.join(encaminhamentos))

    get_encaminhamentos.short_description = 'Encaminhamentos'

    def get_tabs(self, request):
        return ['tab_acompanhamento_prioritario', 'tab_em_acompanhamento', 'tab_acompanhamento_finalizado', 'tab_acompanhamento_nao_finalizado']

    def tab_acompanhamento_nao_finalizado(self, request, queryset):
        return queryset.nao_finalizados()

    tab_acompanhamento_nao_finalizado.short_description = 'Não Finalizados'

    def tab_acompanhamento_prioritario(self, request, queryset):
        return queryset.prioritarios()

    tab_acompanhamento_prioritario.short_description = 'Prioritários'

    def tab_em_acompanhamento(self, request, queryset):
        return queryset.em_acompanhamento()

    tab_em_acompanhamento.short_description = 'Em Acompanhamento'

    def tab_acompanhamento_finalizado(self, request, queryset):
        return queryset.finalizados()

    tab_acompanhamento_finalizado.short_description = 'Finalizados'

    def get_queryset(self, request, manager=None, **kwargs):
        return (
            super()
            .get_queryset(request, Acompanhamento.locals)
            .select_related('aluno__curso_campus__diretoria__setor', 'aluno__curso_campus__diretoria__setor__uo', 'aluno', 'aluno__curso_campus', 'aluno__curso_campus__diretoria')
        )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        url = '/admin/etep/acompanhamento/'
        qs_diretoria = Diretoria.locals.filter(setor__uo=request.user.get_vinculo().setor.uo)
        if not in_group(request.user, 'etep Administrador') and qs_diretoria.exists():
            url = '{}?aluno__curso_campus__diretoria__id__exact={}&tab=tab_acompanhamento_nao_finalizado'.format(url, qs_diretoria[0].pk)
        return HttpResponseRedirect(url)


admin.site.register(Acompanhamento, AcompanhamentoAdmin)


class SolicitacaoAcompanhamentoFilter(SimpleListFilter):
    title = 'situação'
    parameter_name = 'situacao'

    def lookups(self, request, model_admin):
        return (('deferida', 'Deferida'), ('indeferida', 'Indeferida'), ('pendente', 'Pendente'))

    def queryset(self, request, queryset):
        if self.value() == 'pendente':
            return queryset.filter(data_avaliacao__isnull=True)
        if self.value() == 'deferida':
            return queryset.filter(atendida=True)
        if self.value() == 'indeferida':
            return queryset.filter(atendida=False, data_avaliacao__isnull=False)


class SolicitacaoAcompanhamentoAdmin(ModelAdminPlus):
    list_display = ('id', 'get_aluno', 'descricao', 'get_categorias', 'get_solicitante', 'data_solicitacao', 'get_avaliador', 'get_acoes')
    list_display_icons = True
    list_filter = (CustomTabListFilter, 'solicitante', 'avaliador', 'aluno__curso_campus__diretoria__setor__uo', 'aluno__curso_campus__diretoria', SolicitacaoAcompanhamentoFilter)
    search_fields = ('id', 'solicitante__first_name', 'solicitante__username', 'avaliador__first_name', 'avaliador__username', 'aluno__pessoa_fisica__nome')
    ordering = ('-data_avaliacao',)
    form = SolicitacaoAcompanhamentoForm
    export_to_xls = True
    show_count_on_tabs = True

    def get_solicitante(self, obj):
        img_src = obj.solicitante.get_profile().get_foto_75x100_url()
        return mark_safe('<div class="person"><div class="photo-circle"><img src="{0}" alt="{1}"></div><dl><dt class="sr-only">Solicitante</dt><dd>{1}</dd></dl></div>'.format(img_src, obj.solicitante))

    get_solicitante.short_description = 'Solicitante'

    def get_categorias(self, obj):
        categorias = obj.solicitacaoacompanhamentocategoria_set.all().values_list('categoria__nome', flat=True)
        if not categorias:
            return None
        return mark_safe('<ul><li>%s</li></ul>' % '</li><li>'.join(categorias))

    get_categorias.short_description = 'Categorias'

    def get_avaliador(self, obj):
        return mark_safe(format_(obj.avaliador))

    get_avaliador.short_description = 'Avaliador'

    def get_aluno(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(obj.aluno.get_absolute_url(), obj.aluno))

    get_aluno.short_description = 'Aluno'

    def get_action_bar(self, request, **kwargs):
        self.show_actions = request.GET.get('tab', None) == 'tab_pendentes'
        items = super().get_action_bar(request, True)
        return items

    def get_diretoria(self, obj):
        return mark_safe(obj.get_diretoria())

    get_diretoria.short_description = 'Diretoria'

    def get_acoes(self, obj):
        lista = []
        if obj.data_avaliacao:
            if obj.atendida:
                lista.append('<span class="status status-success">Deferida</span>')
            else:
                lista.append('<span class="status status-error">Indeferida</span>')
        else:
            lista.append('<span class="status status-pendente">Pendente</span>')
        return mark_safe(' '.join(lista))

    get_acoes.short_description = 'Situação'

    def get_tabs(self, request):
        return ['tab_em_acompanhamento', 'tab_finalizados', 'tab_interessados']

    def tab_pendentes(self, request, queryset):
        return queryset.filter(data_avaliacao__isnull=True)

    tab_pendentes.short_description = 'Solicitações Pendentes'

    def tab_em_acompanhamento(self, request, queryset):
        return queryset.em_acompanhamento()

    tab_em_acompanhamento.short_description = 'Solicitações Em acompanhamento'

    def tab_finalizados(self, request, queryset):
        return queryset.finalizados()

    tab_finalizados.short_description = 'Solicitações Finalizadas'

    def tab_interessados(self, request, queryset):
        return queryset.interessados()

    tab_interessados.short_description = 'Solicitações Interessadas'

    def get_queryset(self, request, manager=None, **kwargs):
        if not manager:
            manager = SolicitacaoAcompanhamento.locals
        return super().get_queryset(request, manager)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        url = '/admin/etep/solicitacaoacompanhamento/'
        qs_diretoria = Diretoria.locals.filter(setor__uo=request.user.get_profile().funcionario.setor.uo)
        if not in_group(request.user, 'etep Administrador') and qs_diretoria.exists():
            url = '{}?aluno__curso_campus__diretoria__id__exact={}'.format(url, qs_diretoria[0].pk)
        return HttpResponseRedirect(url)


admin.site.register(SolicitacaoAcompanhamento, SolicitacaoAcompanhamentoAdmin)


class CategoriaAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao')
    ordering = ('nome', 'descricao')
    search_fields = ('nome', 'descricao')
    list_display_icons = True
    export_to_xls = True


admin.site.register(Categoria, CategoriaAdmin)


class EncaminhamentoAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao')
    ordering = ('nome', 'descricao')
    search_fields = ('nome', 'descricao')
    list_display_icons = True
    export_to_xls = True


admin.site.register(Encaminhamento, EncaminhamentoAdmin)


class TipoAtividadeAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao')
    ordering = ('nome', 'descricao')
    search_fields = ('nome', 'descricao')
    list_display_icons = True
    export_to_xls = True


admin.site.register(TipoAtividade, TipoAtividadeAdmin)


class TipoDocumentoAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao')
    ordering = ('nome', 'descricao')
    search_fields = ('nome', 'descricao')
    list_display_icons = True
    export_to_xls = True


admin.site.register(TipoDocumento, TipoDocumentoAdmin)


class AtividadeAdmin(ModelAdminPlus):
    list_display = ('titulo', 'descricao', 'tipo', 'data_inclusao', 'data_inicio_atividade', 'data_fim_atividade', 'get_visibilidade', 'usuario')
    ordering = ('-id',)
    list_filter = (CustomTabListFilter, 'tipo')
    search_fields = ('titulo', 'descricao')
    date_hierarchy = 'data_inicio_atividade'
    list_display_icons = True
    export_to_xls = True

    def get_tabs(self, request):
        return ['tab_meu_campus', 'tab_compartilhadas']

    def tab_meu_campus(self, request, queryset):
        return queryset.filter(usuario__pessoafisica__funcionario__setor__uo=request.user.pessoafisica.funcionario.setor.uo)

    tab_meu_campus.short_description = 'Meu Campus'

    def tab_compartilhadas(self, request, queryset):
        return queryset.exclude(usuario__pessoafisica__funcionario__setor__uo=request.user.pessoafisica.funcionario.setor.uo)

    tab_compartilhadas.short_description = 'Compartilhadas'

    def get_queryset(self, request, manager=None, **kwargs):
        if not manager:
            manager = Atividade.locals
        return super().get_queryset(request, manager)


admin.site.register(Atividade, AtividadeAdmin)


class DocumentoAdmin(ModelAdminPlus):
    list_display = ('arquivo', 'tipo', 'get_atividade')
    search_fields = ('arquivo',)
    ordering = ('-id',)
    list_filter = (CustomTabListFilter, 'tipo', 'atividade__tipo')
    list_display_icons = True
    export_to_xls = True

    def get_atividade(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(obj.atividade.get_absolute_url(), obj.atividade))

    get_atividade.short_description = 'Atividade'
    get_atividade.admin_order_field = 'atividade__pk'

    def get_tabs(self, request):
        return ['tab_meu_campus', 'tab_compartilhadas']

    def tab_meu_campus(self, request, queryset):
        return queryset.filter(atividade__usuario__pessoafisica__funcionario__setor__uo=request.user.pessoafisica.funcionario.setor.uo)

    tab_meu_campus.short_description = 'Meu Campus'

    def tab_compartilhadas(self, request, queryset):
        return queryset.exclude(atividade__usuario__pessoafisica__funcionario__setor__uo=request.user.pessoafisica.funcionario.setor.uo)

    tab_compartilhadas.short_description = 'Compartilhadas'

    def get_queryset(self, request, manager=None, **kwargs):
        if not manager:
            manager = Documento.locals
        return super().get_queryset(request, manager)


admin.site.register(Documento, DocumentoAdmin)
