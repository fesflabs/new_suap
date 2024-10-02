from datetime import date, datetime, timedelta

import gitlab
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.template.defaultfilters import slugify, pluralize
from django.urls import reverse
from django.utils.safestring import mark_safe
from gitlab import GitlabError
from requests.exceptions import ConnectTimeout

from comum.models import Comentario, Configuracao, Log
from demandas.forms import AreaAtuacaoDemandaForm, AtualizacaoForm, DemandaAddForm, DemandaChangeForm, \
    AmbienteHomologacaoForm
from demandas.models import AreaAtuacaoDemanda, Atualizacao, Demanda, Situacao, Tag, AnalistaDesenvolvedor, \
    ProjetoGitlab, AmbienteHomologacao
from demandas.models import SugestaoMelhoria
from demandas.utils import Notificar
from djtools.contrib.admin import CompareVersionAdminPlus, CustomTabListFilter, ModelAdminPlus, unquote
from djtools.templatetags.filters import format_user, in_group
from djtools.templatetags.tags import icon
from djtools.utils import httprr


class TagAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_display = ('nome', 'sigla')
    list_display_icons = True


admin.site.register(Tag, TagAdmin)


class PerfilAtendenteFilter(admin.SimpleListFilter):
    title = "Perfil"
    parameter_name = "perfil"

    def lookups(self, request, model_admin):
        return (('analista', 'Analista'), ('desenvolvedor', 'Desenvolvedor'))

    def queryset(self, request, queryset):
        if self.value():
            perfil = self.value()
            tab = request.GET.get('tab')
            if perfil == 'analista':
                if tab == 'tab_nao_iniciadas':
                    return queryset.exclude(situacao__in=[Situacao.ESTADO_APROVADO, Situacao.ESTADO_HOMOLOGADA])
                elif tab == 'tab_em_andamento':
                    return queryset.exclude(situacao__in=[Situacao.ESTADO_EM_DESENVOLVIMENTO, Situacao.ESTADO_EM_IMPLANTACAO])
                elif tab == 'tab_pendentes':
                    return queryset.exclude(situacao=Situacao.ESTADO_EM_HOMOLOGACAO)
            else:
                if tab == 'tab_nao_iniciadas':
                    return queryset.exclude(situacao=Situacao.ESTADO_ABERTO)
                elif tab == 'tab_em_andamento':
                    return queryset.exclude(situacao=Situacao.ESTADO_EM_NEGOCIACAO)
                elif tab == 'tab_pendentes':
                    return queryset.exclude(situacao__in=[Situacao.ESTADO_EM_ANALISE, Situacao.ESTADO_SUSPENSO])
        return queryset


class UltimoComentarioFilter(admin.SimpleListFilter):
    title = "Último Comentário"
    parameter_name = "ultimo_comentario_em"

    def lookups(self, request, model_admin):
        return (('5', 'Até 5 dias'), ('10', 'Até 10 dias'), ('15', 'Até 15 dias'), ('30', 'Até 30 dias'))

    def queryset(self, request, queryset):
        if self.value():
            demanda_content = ContentType.objects.get(app_label='demandas', model='demanda')
            data = datetime.today() - timedelta(days=int(self.value()))
            comentarios = Comentario.objects.filter(content_type=demanda_content, cadastrado_em__gte=datetime(data.year, data.month, data.day, 0, 0, 0))
            return queryset.filter(pk__in=comentarios.values('object_id'))
        return queryset


class EhPrioritariaFilter(admin.SimpleListFilter):
    title = "É prioritária?"
    parameter_name = "eh_prioritaria"

    def lookups(self, request, model_admin):
        return [('Sim', 'Sim'), ('Não', 'Não')]

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'Sim':
                return queryset.filter(prioridade__lte=5)
            elif self.value() == 'Não':
                return queryset.filter(prioridade__gt=5)


class AreaAtuacaoDemandaAdmin(ModelAdminPlus):
    list_display = ('get_acoes', 'area', 'get_tags_relacionadas', 'demandante_responsavel', 'get_demandantes', 'recebe_sugestoes', 'get_opcoes')
    search_fields = ('area__nome', 'demandantes__first_name', 'demandantes__last_name', 'demandante_responsavel__first_name', 'demandante_responsavel__last_name')
    list_filter = ('recebe_sugestoes',)
    form = AreaAtuacaoDemandaForm
    ordering = ('area__nome',)
    list_display_icons = False
    list_per_page = 20

    def save_model(self, request, obj, form, change):
        grupo_demandante = Group.objects.get(name='Demandante')
        if obj.pk:
            registro_atual = AreaAtuacaoDemanda.objects.get(id=obj.pk)
            for demandante in registro_atual.demandantes.all():
                if demandante not in form.cleaned_data.get('demandantes') and \
                        not AreaAtuacaoDemanda.objects.exclude(id=obj.pk).filter(Q(demandantes=demandante) | Q(demandante_responsavel=demandante)).exists():
                    demandante.groups.remove(grupo_demandante)
            if registro_atual.demandante_responsavel != form.cleaned_data.get('demandante_responsavel') and \
                    not AreaAtuacaoDemanda.objects.exclude(id=obj.pk).filter(Q(demandantes=registro_atual.demandante_responsavel) | Q(demandante_responsavel=registro_atual.demandante_responsavel)).exists():
                registro_atual.demandante_responsavel.groups.remove(grupo_demandante)
        super().save_model(request, obj, form, change)
        form.cleaned_data.get('demandante_responsavel').groups.add(grupo_demandante)
        for demandante in form.cleaned_data.get('demandantes'):
            demandante.groups.add(grupo_demandante)

    def get_acoes(self, obj):
        mostra_acoes = ''
        if in_group(self.request.user, 'Coordenador de TI sistêmico') or obj.demandante_responsavel == self.request.user:
            mostra_acoes += icon('edit', f'/admin/demandas/areaatuacaodemanda/{obj.id}/')
        return mark_safe(mostra_acoes)

    get_acoes.short_description = 'Ações'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if in_group(request.user, 'Coordenador de TI sistêmico') or obj.demandante_responsavel == request.user:
            return super().change_view(request, object_id, form_url, extra_context)
        else:
            raise PermissionDenied()

    def get_form(self, request, obj=None, **kwargs):
        FormClass = super(ModelAdminPlus, self).get_form(request, obj, **kwargs)
        FormClass.request = request
        return FormClass

    def get_demandantes(self, obj):
        lista = list("<ol>")
        for user in obj.demandantes.all():
            lista.append(f"<li>{format_user(user)}</li>")
        lista.append("</ol>")
        return mark_safe(''.join(lista))

    get_demandantes.short_description = 'Demandantes'

    def get_tags_relacionadas(self, obj):
        lista = list("<ul class='tags'>")
        for tag in obj.tags_relacionadas.all():
            lista.append(f"<li>{tag}</li>")
        lista.append("</ul>")
        return mark_safe(''.join(lista))

    get_tags_relacionadas.short_description = 'Tags Relacionadas'

    def get_opcoes(self, obj):
        area = obj.pk
        demandas = Demanda.objects.ativas().filter(area=area).count()
        sugestoes = SugestaoMelhoria.objects.filter(situacao__in=[SugestaoMelhoria.SITUACAO_PENDENTE, SugestaoMelhoria.SITUACAO_EM_ANALISE, SugestaoMelhoria.SITUACAO_SUSPENSA]).filter(area_atuacao=area).count()
        retorno = "<ul class='action-bar'>"
        if demandas > 0:
            retorno += f"<li><a href='/admin/demandas/demanda/?area__id__exact={area}&tab=tab_ativas' class='btn default'><span class='fas fa-search' aria-hidden='true'></span> {demandas} Demanda{pluralize(demandas)} Ativa{pluralize(demandas)}</a></li>"
        if sugestoes > 0:
            retorno += f"<li><a href='/admin/demandas/sugestaomelhoria/?area_atuacao__id__exact={area}&tab=tab_ativas' class='btn default'><span class='fas fa-search' aria-hidden='true'></span> {sugestoes} Sugest{pluralize(sugestoes, 'ão,ões')} de Melhoria{pluralize(sugestoes)} Ativa{pluralize(sugestoes)}</a></li>"
        retorno += "</ul>"
        return mark_safe(retorno)

    get_opcoes.short_description = 'Opções'


admin.site.register(AreaAtuacaoDemanda, AreaAtuacaoDemandaAdmin)


class AnalistaDesenvolvedorAdmin(ModelAdminPlus):
    list_display = ('usuario', 'username_gitlab', 'eh_analista', 'eh_desenvolvedor', 'ativo')
    search_fields = ('usuario__first_name', 'usuario__last_name')
    list_filter = ('eh_analista', 'eh_desenvolvedor')
    list_display_icons = True
    list_per_page = 20
    ordering = ('usuario',)
    exclude = 'pipeline', 'senha_ide'


admin.site.register(AnalistaDesenvolvedor, AnalistaDesenvolvedorAdmin)


class ProjetoGitlabAdmin(ModelAdminPlus):
    list_display = ('id_projeto_gitlab', 'nome_projeto', 'grupo', 'ativo', 'projeto_online_gitlab')
    search_fields = ('nome_projeto',)
    list_filter = ('ativo',)
    list_display_icons = True
    list_per_page = 20

    def projeto_online_gitlab(self, obj):
        git = gitlab.Gitlab(Configuracao.get_valor_por_chave('demandas', 'gitlab_url'), private_token=Configuracao.get_valor_por_chave('demandas', 'gitlab_token'), timeout=60)
        try:
            git.projects.get(obj.id_projeto_gitlab)
            online = True
        except (GitlabError, ConnectTimeout):
            online = False
        return mark_safe(online and '<span class="status status-success">Sim</span>' or '<span class="status status-error">Não</span>')

    projeto_online_gitlab.short_description = 'O projeto está online no gitlab?'


admin.site.register(ProjetoGitlab, ProjetoGitlabAdmin)


class DemandaAdmin(ModelAdminPlus, CompareVersionAdminPlus):
    list_display = (
        'get_acoes',
        'get_titulo',
        'get_prioridade',
        'area',
        'get_tags',
        'votos',
        'tipo',
        'get_situacao',
        'get_demandantes',
        'get_responsaveis',
    )
    list_filter = (CustomTabListFilter, 'area', 'tipo', 'situacao', EhPrioritariaFilter, 'tags', 'demandantes', 'interessados', 'analistas', 'desenvolvedores', UltimoComentarioFilter)
    search_fields = ('id', 'titulo', 'demandantes__first_name', 'demandantes__last_name')

    compare_template = 'demandas/reversion-compare/compare.html'
    object_history_template = 'demandas/reversion-compare/object_history.html'
    list_display_icons = False
    list_display_links = None
    show_count_on_tabs = True
    list_per_page = 20
    date_hierarchy = 'data_atualizacao'

    add_form = DemandaAddForm
    form = DemandaChangeForm

    fieldsets = (
        ("Dados Gerais", {'fields': ('area', 'tipo', 'titulo', 'descricao', 'prazo_legal', 'tags', 'privada', 'consolidacao_sempre_visivel')}),
        ("Interessados", {'fields': ('demandantes', 'interessados', 'observadores')}),
        ("Atendimento", {'fields': ('analistas', 'desenvolvedores')}),
        ("Dados de Homologação", {'fields': ('ambiente_homologacao', 'id_repositorio', 'url_validacao', 'senha_homologacao')}),
        ("Dados de Implantação", {'fields': ('id_merge_request',)}),
    )
    add_fieldsets = (("Dados Gerais", {'fields': ('area', 'titulo', 'descricao', 'privada')}), ("Interessados", {'fields': ('demandantes', 'interessados', 'observadores')}))

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        """ Se é insert e o próprio usuário nao é demandante, inclua-o como demandante """
        if not change and not form.instance.demandantes.filter(pk=request.user.pk).exists() and in_group(request.user, 'Demandante'):
            form.instance.demandantes.add(request.user)
        if not change:
            Notificar.demanda_aberta(form.instance)

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if request.user.has_perm('demandas.atende_demanda'):
            list_filter = (
                CustomTabListFilter,
                'area',
                'tipo',
                'situacao',
                EhPrioritariaFilter,
                'tags',
                'demandantes',
                'interessados',
                PerfilAtendenteFilter,
                'analistas',
                'desenvolvedores',
                UltimoComentarioFilter,
            )
        return list_filter

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        if request.user.demandanteresponsavelarea.exists():
            area = request.user.demandanteresponsavelarea.first()
            items.append(dict(url=reverse('demandas_prioritarias_por_area', args=(area.pk,)), label=f'Prioridades de {area.area}'))
        items.append(dict(url=reverse('demandas'), label='Dashboard'))
        return items

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if not obj:
            raise PermissionDenied()
        if (in_group(request.user, 'Analista, Desenvolvedor') or (obj and self.has_change_permission(request) and (obj.area and obj.area.demandante_responsavel == request.user or obj.eh_demandante(request.user)))) and obj.situacao not in (Situacao.ESTADO_CANCELADO, Situacao.ESTADO_CONCLUIDO):
            return super().change_view(request, object_id, form_url, extra_context)
        else:
            raise PermissionDenied()

    def get_form(self, request, obj=None, **kwargs):
        """
        Torna o ``request`` disponível no ``FormClass``.
        """
        defaults = {}
        if not request.user.has_perm('demandas.atende_demanda'):
            defaults['form'] = self.add_form
        defaults.update(kwargs)

        FormClass = super(ModelAdminPlus, self).get_form(request, obj, **defaults)
        FormClass.request = request
        return FormClass

    def get_fieldsets(self, request, obj=None):
        if request.user.has_perm('demandas.atende_demanda'):
            return self.fieldsets
        else:
            return self.add_fieldsets

    def get_acoes(self, obj):
        mostra_acoes = ''
        if self.has_view_permission(self.request, obj):
            mostra_acoes += icon('view', f'/demandas/visualizar/{obj.id}/')

        if (in_group(self.request.user, 'Analista, Desenvolvedor') or (self.has_change_permission(self.request) and obj and (obj.area and obj.area.demandante_responsavel == self.request.user or obj.eh_demandante(self.request.user)))) and obj.situacao not in (Situacao.ESTADO_CANCELADO, Situacao.ESTADO_CONCLUIDO):
            mostra_acoes += icon('edit', f'/admin/demandas/demanda/{obj.id}/')
        return mark_safe(mostra_acoes)

    get_acoes.short_description = 'Ações'

    def get_prioridade(self, obj):
        if not obj.prioridade:
            return mark_safe(f'<span class="status status-error">{obj.get_prioridade_display()}</span>')
        if obj.prioridade > 5:
            classname = "error"
        else:
            classname = "success"
        return mark_safe(f'<span class="status status-{classname}">{obj.get_prioridade_display()}º</span>')

    get_prioridade.short_description = 'Prioridade'
    get_prioridade.allow_tags = True
    get_prioridade.admin_order_field = 'prioridade'

    def get_titulo(self, obj):
        if obj.prioridade and obj.prioridade <= 5:
            demanda = f"<dl><dt hidden>Demanda</dt><dd><strong>{obj}</strong></dd>"
        else:
            demanda = f"<dl><dt hidden>Demanda</dt><dd>{obj}</dd>"

        historico_situacao = obj.get_ultimo_historico_situacao()
        hoje = date.today()
        if historico_situacao.data_previsao:
            registro_recente = obj.get_ultimo_historico_situacao()
            if registro_recente.data_previsao < hoje and not registro_recente.data_conclusao:
                demanda += '<dt class="false">Etapa em atraso desde:</dt><dd>{}</dd>'.format(historico_situacao.data_previsao.strftime('%d/%m/%Y'))
            else:
                demanda += '<dt class="true">Etapa prevista para:</dt><dd>{}</dd>'.format(historico_situacao.data_previsao.strftime('%d/%m/%Y'))

        if obj.prazo_legal:
            demanda += f'<dt class={"true" if obj.prazo_legal >= hoje else "false" }>Prazo Legal:</dt><dd>{obj.prazo_legal.strftime("%d/%m/%Y")}</dd>'

        return mark_safe(f"{demanda}</dl>")

    get_titulo.short_description = 'Demanda'
    get_titulo.admin_order_field = 'titulo'

    def get_tags(self, obj):
        tags = list()
        tags.append('<ul class="tags">')
        for tag in obj.tags.all():
            tags.append(f'<li>{tag}</li>')
        tags.append('</ul>')

        return mark_safe('\n'.join(tags))

    get_tags.short_description = 'Tags'
    get_tags.allow_tags = True

    def get_demandantes(self, obj):
        lista = list("<ol>")
        for user in obj.demandantes.all():
            lista.append(f"<li>{format_user(user)}</li>")
        lista.append("</ol>")
        return mark_safe(''.join(lista))

    get_demandantes.short_description = 'Demandantes'

    def get_situacao(self, obj):
        return mark_safe(f'<span class="status status-{slugify(obj.situacao)}">{obj.situacao}</span>')

    get_situacao.short_description = 'Etapa'

    def get_responsaveis(self, obj):
        lista = list()
        lista.append('<dl>')
        if obj.analistas.exists():
            lista.append('<dt>Analista(s):</dt>')
            analistas = list()
            for user in obj.analistas.all():
                analistas.append(format_user(user))
            lista.append('<dd>{}</dd>'.format(mark_safe(', '.join(analistas))))

        if obj.desenvolvedores.exists():
            lista.append('<dt>Desenvolvedor(es):</dt>')
            desenvolvedores = list()
            for user in obj.desenvolvedores.all():
                desenvolvedores.append(format_user(user))
            lista.append('<dd>{}</dd>'.format(mark_safe(', '.join(desenvolvedores))))
        lista.append('</dl>')

        return mark_safe('\n'.join(lista))

    get_responsaveis.short_description = 'Responsáveis'

    def tab_ativas(self, request, queryset):
        return queryset.ativas()

    tab_ativas.short_description = 'Ativas'

    def tab_em_andamento(self, request, queryset):
        return queryset.em_andamento()

    tab_em_andamento.short_description = 'Em Andamento'

    def tab_nao_iniciadas(self, request, queryset):
        return queryset.nao_iniciadas()

    tab_nao_iniciadas.short_description = 'A Iniciar'

    def tab_pendentes(self, request, queryset):
        return queryset.aguardando_feedback()

    tab_pendentes.short_description = 'Aguardando Feedback'

    def tab_como_analista(self, request, queryset):
        return queryset.filter(situacao__in=[Situacao.ESTADO_ABERTO, Situacao.ESTADO_EM_NEGOCIACAO, Situacao.ESTADO_APROVADO, Situacao.ESTADO_EM_IMPLANTACAO]).filter(
            analistas__pk=request.user.pk
        )

    tab_como_analista.short_description = 'Minhas Como Analista'

    def tab_como_desenvolvedor(self, request, queryset):
        return queryset.filter(situacao__in=[Situacao.ESTADO_APROVADO, Situacao.ESTADO_EM_DESENVOLVIMENTO, Situacao.ESTADO_HOMOLOGADA, Situacao.ESTADO_EM_IMPLANTACAO]).filter(
            desenvolvedores__pk=request.user.pk
        )

    tab_como_desenvolvedor.short_description = 'Minhas Como Desenvolvedor'

    def tab_como_demandante(self, request, queryset):
        return queryset.exclude(situacao__in=[Situacao.ESTADO_CONCLUIDO, Situacao.ESTADO_CANCELADO]).filter(demandantes__pk=request.user.pk)

    tab_como_demandante.short_description = 'Minhas Como Demandante'

    def tab_como_interessado(self, request, queryset):
        return queryset.exclude(situacao__in=[Situacao.ESTADO_CONCLUIDO, Situacao.ESTADO_CANCELADO]).filter(interessados__pk=request.user.pk)

    tab_como_interessado.short_description = 'Minhas Como Interessado'

    def tab_como_observador(self, request, queryset):
        return queryset.exclude(situacao__in=[Situacao.ESTADO_CONCLUIDO, Situacao.ESTADO_CANCELADO]).filter(observadores__pk=request.user.pk)

    tab_como_observador.short_description = 'Minhas Como Observador'

    def get_tabs(self, request):
        tabs = ['tab_ativas', 'tab_nao_iniciadas', 'tab_em_andamento', 'tab_pendentes']
        if request.user.has_perm('demandas.add_demanda'):
            tabs.append('tab_como_demandante')
        tabs.append('tab_como_interessado')
        tabs.append('tab_como_observador')
        if request.user.has_perm('demandas.atende_demanda'):
            tabs.append('tab_como_analista')
            tabs.append('tab_como_desenvolvedor')
        tabs.append('tab_any_data')
        return tabs


admin.site.register(Demanda, DemandaAdmin)


class AtualizacaoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'get_tags', 'get_grupos', 'get_tipo', 'data')
    list_display_icons = True
    list_filter = (CustomTabListFilter, 'tags', 'tipo', 'grupos', 'responsaveis')
    date_hierarchy = 'data'
    ordering = ('-data',)

    form = AtualizacaoForm

    def get_tabs(self, request):
        return ['tab_proxima_atualizacao_ifrn']

    def tab_proxima_atualizacao_ifrn(self, request, queryset):
        log = Log.objects.filter(titulo='Atualização do Sistema').order_by('-id').first()
        ultima_atualizacao = log.horario
        return queryset.filter(data__gt=ultima_atualizacao)

    tab_proxima_atualizacao_ifrn.short_description = 'Próxima Atualização com IFRN'

    def get_tipo(self, obj):
        return mark_safe(f'<span class="status status-{slugify(obj.tipo)}">{obj.tipo}</span>')

    get_tipo.short_description = 'Tipo'

    def get_tags(self, obj):
        strOut = '<ul class="tags">'
        for tag in obj.tags.all():
            strOut += f'<li>{tag.nome}</li>'
        strOut += '</ul>'
        return mark_safe(strOut)

    get_tags.short_description = 'Tags'

    def get_grupos(self, obj):
        strOut = '<ul>'
        for grupo in obj.grupos.all():
            strOut += f'<li>{grupo.name}</li>'
        strOut += '</ul>'
        return mark_safe(strOut)

    get_grupos.short_description = 'Grupos Envolvidos'


admin.site.register(Atualizacao, AtualizacaoAdmin)


class SugestaoMelhoriaAdmin(ModelAdminPlus):
    search_fields = ('titulo', 'descricao')
    list_display = ('titulo', 'area_atuacao', 'get_modulo', 'votos', 'get_requisitante', 'get_responsavel', 'get_situacao', 'get_opcoes')
    list_display_icons = True
    list_filter = (CustomTabListFilter, 'area_atuacao', 'tags', 'situacao')
    ordering = ('situacao', '-votos')
    show_tab_any_data = False
    show_count_on_tabs = True

    def get_action_bar(self, request, remove_add_button=False):
        actions = super().get_action_bar(request, remove_add_button=True)
        return actions

    def has_add_permission(self, request):
        return False  # adição personalizada

    def has_change_permission(self, request, obj=None):
        return False  # edição personalizada

    def has_delete_permission(self, request, obj=None):
        return False  # exclusão personalizada

    def get_modulo(self, obj):
        tags = list()
        for tag in obj.tags.all():
            tags.append(f'{tag}')
        return mark_safe('\n'.join(tags))
    get_modulo.short_description = 'Módulo'
    get_modulo.allow_tags = True

    def get_requisitante(self, obj):
        return mark_safe(format_user(obj.requisitante))
    get_requisitante.short_description = 'Requisitante'
    get_requisitante.admin_order_field = 'requisitante'
    get_requisitante.allow_tags = True

    def get_responsavel(self, obj):
        return mark_safe(format_user(obj.responsavel) if obj.responsavel else '-')
    get_responsavel.short_description = 'Responsável'
    get_responsavel.allow_tags = True

    def get_situacao(self, obj):
        retorno = f'<span class="status status-{slugify(obj.get_situacao_display())}">{obj.get_situacao_display()}</span>'
        if obj.demanda_gerada:
            retorno += f'<span class="status status-{slugify(obj.demanda_gerada.get_situacao_display())}">Demanda: {obj.demanda_gerada.get_situacao_display()}</span>'
        return mark_safe(retorno)
    get_situacao.short_description = 'Situação'
    get_situacao.allow_tags = True

    def get_tabs(self, request):
        if request.user.groups.filter(name__in=['Coordenador de TI sistêmico', 'Analista', 'Desenvolvedor', 'Demandante']).exists():
            return [
                'tab_ativas',
                'tab_como_requisitante',
                'tab_como_interessado',
                'tab_como_demandante',
                'tab_como_responsavel',
                'tab_todas'
            ]
        else:
            return [
                'tab_ativas',
                'tab_como_requisitante',
                'tab_como_interessado',
                'tab_todas'
            ]

    def tab_ativas(self, request, queryset):
        return SugestaoMelhoria.sugestoes_ativas()
    tab_ativas.short_description = 'Ativas'

    def tab_como_requisitante(self, request, queryset):
        return SugestaoMelhoria.sugestoes_por_papel_usuario(
            user_requisitante=request.user, qs_sugestoes_initial=queryset)
    tab_como_requisitante.short_description = 'Como Requisitante'

    def tab_como_interessado(self, request, queryset):
        return SugestaoMelhoria.sugestoes_por_papel_usuario(
            user_interessado=request.user, qs_sugestoes_initial=queryset)
    tab_como_interessado.short_description = 'Como Interessado'

    def tab_como_demandante(self, request, queryset):
        return SugestaoMelhoria.sugestoes_por_papel_usuario(
            user_demandante=request.user, qs_sugestoes_initial=queryset)
    tab_como_demandante.short_description = 'Como Demandante'

    def tab_como_responsavel(self, request, queryset):
        return SugestaoMelhoria.sugestoes_por_papel_usuario(
            user_responsavel=request.user, qs_sugestoes_initial=queryset)
    tab_como_responsavel.short_description = 'Como Responsável'

    def tab_todas(self, request, queryset):
        return queryset
    tab_todas.short_description = 'Todas'

    def get_opcoes(self, obj):
        if obj.pode_votar():
            opcoes = '<ul class="action-bar d-flex flex-nowrap">'
            if not obj.ja_concordou:
                opcoes += f'<li><a href="/demandas/concordar_sugestao/{obj.pk}" class="btn success" title="Concordar com a sugestão"><span class="fas fa-thumbs-up" aria-hidden="true"></span><span class="sr-only">Concordar</span></a></li>'
            if not obj.ja_discordou:
                opcoes += f'<li><a href="/demandas/discordar_sugestao/{obj.pk}" class="btn danger no-confirm" title="Discordar da sugestão"><span class="fas fa-thumbs-down" aria-hidden="true"></span><span class="sr-only">Discordar</span></a></li>'
            opcoes += '</ul>'
        else:
            opcoes = ''
        return mark_safe(opcoes)

    get_opcoes.short_description = 'Opções'


admin.site.register(SugestaoMelhoria, SugestaoMelhoriaAdmin)


class AmbienteHomologacaoAdmin(ModelAdminPlus):
    search_fields = ('branch',)
    list_display = ('branch', 'banco', 'data_criacao', 'data_expiracao', 'senha', 'ativo')
    list_display_icons = True
    list_filter = (CustomTabListFilter, 'banco', 'ativo', 'criador')
    date_hierarchy = 'data_criacao'
    ordering = '-data_criacao',
    actions = 'excluir_container',
    form = AmbienteHomologacaoForm
    fieldsets = (
        ("Dados Gerais", {'fields': (('criador', 'branch'), ('banco', 'data_expiracao'), 'senha')}),
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if request.GET.get('tab') != 'tab_inativos':
            del actions['excluir_container']
        return actions

    def excluir_container(self, request, queryset):
        for ambiente in queryset:
            ambiente.excluir_container()
            ambiente.get_job_log('destroy')

    def get_tabs(self, request):
        return ['tab_meus_ambientes', 'tab_ativos', 'tab_inativos', 'tab_any_data']

    def tab_meus_ambientes(self, request, queryset):
        return queryset.filter(criador__usuario=request.user)

    tab_meus_ambientes.short_description = 'Meus Ambientes'

    def tab_ativos(self, request, queryset):
        return queryset.filter(senha__isnull=False)

    tab_ativos.short_description = 'Ativos'

    def tab_inativos(self, request, queryset):
        return queryset.filter(senha__isnull=True)

    tab_inativos.short_description = 'Inativos'

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if self.get_tab_corrente() and self.get_tab_corrente() != 'tab_meus_ambientes':
            list_display = list_display + ('criador',)
        return list_display

    def add_view(self, *args, **kwargs):
        try:
            return super().add_view(*args, **kwargs)
        except Exception as e:
            return httprr('/admin/demandas/ambientehomologacao/', str(e), 'error')


admin.site.register(AmbienteHomologacao, AmbienteHomologacaoAdmin)
