from django.contrib import admin
from django.utils.safestring import mark_safe
from comum.utils import get_uo
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import in_group
from djtools.templatetags.tags import icon
from eventos.forms import EventoForm, BannerForm, AtendimentoPublicoForm, AtividadeEventoForm
from djtools.utils import httprr
from eventos.models import (
    Evento,
    Natureza,
    TipoEvento,
    SubtipoEvento,
    Espacialidade,
    ClassificacaoEvento,
    PublicoAlvoEvento,
    Participante,
    Banner,
    TipoAtendimento,
    MotivoAtendimento,
    AssuntoAtendimento,
    PublicoAtendimento,
    SituacaoAtendimento,
    AtendimentoPublico,
    TipoParticipacao,
    TipoParticipante,
    Dimensao,
    AtividadeEvento,
    TipoAtividade,
    PorteEvento,
)


class NaturezaAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao',)


admin.site.register(Natureza, NaturezaAdmin)


class DimensaoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao', 'get_avaliadores_locais', 'get_avaliadores_sistemicos')

    def get_avaliadores_locais(self, obj):
        lista = ['<ul>']
        for grupo in obj.grupos_avaliadores_locais.all():
            lista.append('<li>{}</li>'.format(grupo))
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_avaliadores_locais.short_description = 'Avaliadores Locais'

    def get_avaliadores_sistemicos(self, obj):
        lista = ['<ul>']
        for grupo in obj.grupos_avaliadores_sistemicos.all():
            lista.append('<li>{}</li>'.format(grupo))
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_avaliadores_sistemicos.short_description = 'Avaliadores Sistêmicos'


admin.site.register(Dimensao, DimensaoAdmin)


class TipoEventoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao',)


admin.site.register(TipoEvento, TipoEventoAdmin)


class SubtipoEventoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = 'nome', 'tipo', 'detalhamento', 'multiplas_atividades'
    list_filter = 'tipo', 'multiplas_atividades'


admin.site.register(SubtipoEvento, SubtipoEventoAdmin)


class EspacialidadeAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao',)


admin.site.register(Espacialidade, EspacialidadeAdmin)


class ClassificacaoEventoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao', 'detalhamento')


admin.site.register(ClassificacaoEvento, ClassificacaoEventoAdmin)


class PorteEventoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao', 'detalhamento')


admin.site.register(PorteEvento, PorteEventoAdmin)


class PublicoAlvoEventoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao',)


admin.site.register(PublicoAlvoEvento, PublicoAlvoEventoAdmin)


class TipoParticipacaoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao', 'ch_organizacao')


admin.site.register(TipoParticipacao, TipoParticipacaoAdmin)


class TipoAtividadeAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('descricao',)


admin.site.register(TipoAtividade, TipoAtividadeAdmin)


class TipoParticipanteInline(admin.StackedInline):
    model = TipoParticipante
    extra = 1
    readonly_fields = ()  # 'preview',
    verbose_name = 'Tipo de Participação'
    verbose_name_plural = 'Tipo de Participações'
    fieldsets = (
        ('', {'fields': ('evento', ('tipo_participacao', 'limite_inscricoes'), 'modelo_certificado')}),
    )

    def preview(self, obj):
        return mark_safe('<button class="btn preview-certificado">Testar Certificado</button>')
    preview.short_description = ''


class AtividadeEventoInline(admin.StackedInline):
    model = AtividadeEvento
    extra = 1
    exclude = 'participantes',
    form = AtividadeEventoForm
    fieldsets = (
        ('', {'fields': ('evento', 'tipo', 'descricao', ('data', 'hora'), ('ch', 'limite_inscricoes'))}),
    )


class EventoAdmin(ModelAdminPlus):
    list_display_icons = False
    list_display_links = None
    list_display = ('get_acoes', 'nome', 'campus', 'local', 'get_dimensoes', 'data_inicio', 'submetido', 'deferido', 'ativo', 'finalizado')
    search_fields = ('nome', 'apresentacao')
    list_filter = (CustomTabListFilter, 'dimensoes', 'classificacao', 'espacialidade', 'tipo', 'subtipo', 'campus', 'deferido', 'finalizado', 'ativo')
    date_hierarchy = 'data_inicio'
    form = EventoForm
    show_count_on_tabs = True
    inlines = [AtividadeEventoInline, TipoParticipanteInline]
    list_per_page = 25
    show_tab_any_data = False

    fieldsets = (
        ('Dados Gerais', {'fields': ('nome', 'dimensoes', 'apresentacao', 'imagem', 'site')}),
        ('Inscrição', {'fields': (('data_inicio_inscricoes', 'hora_inicio_inscricoes'), ('data_fim_inscricoes', 'hora_fim_inscricoes'))}),
        ('Realização', {'fields': ('local', ('hora_inicio', 'hora_fim'), ('data_inicio', 'data_fim'))}),
        ('Coordenação e Organização', {'fields': ('coordenador', 'campus', 'setor', 'organizadores')}),
        ('Configurações', {'fields': ('inscricao_publica', 'gera_certificado', 'registrar_presenca_online')}),
        ('Classificação', {'fields': ('classificacao', 'espacialidade', 'porte', 'tipo', 'subtipo', 'publico_alvo')}),
        ('Carga Horária', {'fields': (('carga_horaria',))}),
        ('Financeiro', {'fields': ('recursos',)}),
    )

    def get_dimensoes(self, obj):
        dimensoes = ['<ul>']
        for dimensao in obj.dimensoes.all():
            dimensoes.append('<li>{}</li>'.format(dimensao))
        dimensoes.append('</ul>')
        return mark_safe(' '.join(dimensoes))
    get_dimensoes.short_description = 'Dimensões'

    get_dimensoes.short_description = 'Dimensões'

    def get_opcoes(self, obj):
        opcoes = list()
        if self.get_tab_corrente() == 'tab_participante':
            opcoes.append('<ul class="action-bar">')
            minhas_participacoes = obj.participantes.filter(cpf=self.request.user.get_vinculo().pessoa.pessoafisica.cpf).order_by('nome')
            for participante in minhas_participacoes:
                if participante.codigo_geracao_certificado:
                    if participante.tipo and participante.tipo.tipo_participacao:
                        tipo_participacao = participante.tipo.tipo_participacao
                        opcoes.append('<li><a href="{}" class="btn default">Imprimir Certificado {}</a></li>'.format(participante.get_url_download_certificado(), tipo_participacao.descricao))
                    else:
                        opcoes.append('<li><a href="{}" class="btn default">Imprimir Certificado</a></li>'.format(participante.get_url_download_certificado()))
            opcoes.append('</ul>')
        return mark_safe(' '.join(opcoes))

    get_opcoes.short_description = 'Opções'

    def get_action_bar(self, request, remove_add_button=False):
        action_bar = super().get_action_bar(request, remove_add_button=remove_add_button)
        action_bar.append(
            {'url': '/static/eventos/Modelo_de_projeto_de_eventos.docx', 'label': 'Baixar Arquivo de Projeto', 'css_class': 'default'}
        )
        return action_bar

    def get_list_display(self, request):
        default_list_display = super().get_list_display(request)
        if self.get_tab_corrente() == 'tab_participante':
            return ('get_acoes', 'nome', 'campus', 'local', 'data_inicio', 'get_opcoes')
        if in_group(request.user, 'Coordenador de Comunicação Sistêmico'):
            return default_list_display + ('cancelado',)

        return default_list_display

    def get_acoes(self, obj):
        out = [icon('view', obj.get_absolute_url())]
        if obj.pode_gerenciar(self.request.user):
            out.append(icon('edit', '/admin/eventos/evento/{}/'.format(obj.id)))
        return mark_safe(''.join(out))

    get_acoes.short_description = 'Ações'

    def response_add(self, request, obj):
        return httprr('/eventos/evento/{}/'.format(obj.pk), 'Ação realizada com sucesso.')

    def response_change(self, request, obj):
        return self.response_add(request, obj)

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        return retorno and (not obj or obj.pode_gerenciar(request.user))

    def tab_ativos(self, request, queryset):
        return queryset.filter(ativo=True, deferido=True).exclude(cancelado=True)

    tab_ativos.short_description = 'Ativos'

    def tab_aguardando_minha_aprovacao(self, request, queryset):
        dimensoes = Dimensao.objects.filter(grupos_avaliadores_locais__in=request.user.groups.values_list('pk', flat=True))
        return queryset.filter(submetido=True, deferido__isnull=True, dimensoes__in=dimensoes, campus=request.user.get_vinculo().setor.uo).exclude(cancelado=True)

    tab_aguardando_minha_aprovacao.short_description = 'Aguardando Minha Aprovação'

    def tab_aguardando_aprovacao(self, request, queryset):
        dimensoes = Dimensao.objects.filter(grupos_avaliadores_sistemicos__in=request.user.groups.values_list('pk', flat=True))
        return queryset.filter(deferido__isnull=True, dimensoes__in=dimensoes).exclude(cancelado=True)

    tab_aguardando_aprovacao.short_description = 'Aguardando Aprovação'

    def tab_sob_minha_organizacao(self, request, queryset):
        pks = Participante.objects.filter(tipo__tipo_participacao__descricao='Organizador', cpf=request.user.get_vinculo().pessoa.pessoafisica.cpf).values_list(
            'evento_id', flat=True
        )
        return queryset.filter(pk__in=pks)

    tab_sob_minha_organizacao.short_description = 'Sob Minha Organização'

    def tab_sob_minha_coordenacao(self, request, queryset):
        return queryset.filter(coordenador_id=request.user.get_vinculo().pessoa_id)

    tab_sob_minha_coordenacao.short_description = 'Sob Minha Coordenação'

    def tab_todos(self, request, queryset):
        return queryset.all()

    tab_todos.short_description = 'Todos'

    def tab_participante(self, request, queryset):
        return queryset.filter(participantes__cpf=self.request.user.get_vinculo().pessoa.pessoafisica.cpf)

    tab_participante.short_description = 'Participante'

    def tab_campus(self, request, queryset):
        return queryset.filter(campus=get_uo(self.request.user))

    tab_campus.short_description = 'Do campus'

    def get_tabs(self, request):
        grupos_avaliadores_sistemicos = Dimensao.objects.values_list('grupos_avaliadores_sistemicos', flat=True)
        is_avaliador_sistemico = request.user.groups.filter(pk__in=grupos_avaliadores_sistemicos)
        grupos_avaliadores_locais = Dimensao.objects.values_list('grupos_avaliadores_locais', flat=True)
        is_avaliador_local = request.user.groups.filter(pk__in=grupos_avaliadores_locais)
        is_organizador = Participante.objects.filter(tipo__tipo_participacao__descricao='Organizador', cpf=request.user.get_vinculo().pessoa.pessoafisica.cpf).exists()
        is_coordenador = Evento.objects.filter(coordenador_id=request.user.get_vinculo().pessoa_id).exists()
        tabs = ['tab_ativos', 'tab_participante']
        if is_avaliador_local:
            tabs.append('tab_aguardando_minha_aprovacao')
        if is_avaliador_sistemico:
            tabs.append('tab_aguardando_aprovacao')
        if is_organizador:
            tabs.append('tab_sob_minha_organizacao')
        if is_coordenador:
            tabs.append('tab_sob_minha_coordenacao')
        if in_group(request.user, 'Coordenador de Comunicação'):
            tabs.append('tab_campus')
        if in_group(request.user, 'Coordenador de Comunicação Sistêmico'):
            tabs.append('tab_todos')
        return tabs

    def render_change_form(self, request, context, **kwargs):
        context['show_save_and_continue'] = False
        return super().render_change_form(request, context, **kwargs)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        evento = form.instance

        tipo_participacao_participante = TipoParticipacao.objects.get(descricao='Participante')
        tipo_participante_participante = TipoParticipante.objects.filter(evento=evento, tipo_participacao=tipo_participacao_participante).first()
        if not tipo_participante_participante:
            TipoParticipante.objects.create(evento=evento, tipo_participacao=tipo_participacao_participante)

        tipo_participacao_organizador = TipoParticipacao.objects.get(descricao='Organizador')
        tipo_participante_organizador = TipoParticipante.objects.filter(evento=evento, tipo_participacao=tipo_participacao_organizador).first()
        if not tipo_participante_organizador:
            tipo_participante_organizador = TipoParticipante.objects.create(evento=evento, tipo_participacao=tipo_participacao_organizador)

        for vinculo in form.cleaned_data['organizadores']:
            participante = Participante.objects.filter(evento=evento, vinculo=vinculo).first()
            if not participante:
                participante = Participante.objects.create(
                    evento=evento,
                    nome=vinculo.pessoa.nome,
                    cpf=vinculo.pessoa.pessoafisica.cpf,
                    email=vinculo.pessoa.email,
                    inscricao_validada=True,
                    tipo=tipo_participante_organizador,
                    vinculo=vinculo,
                )
            participante.checar_publico_alvo()
            participante.save()


admin.site.register(Evento, EventoAdmin)


class ParticipanteAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('nome', 'email', 'evento', 'data_cadastro')
    search_fields = ('nome', 'email')
    list_filter = ('evento',)
    date_hierarchy = 'data_cadastro'


admin.site.register(Participante, ParticipanteAdmin)


class BannerAdmin(ModelAdminPlus):
    form = BannerForm
    list_display_icons = True
    list_display = ('titulo', 'data_inicio', 'data_termino')
    search_fields = ('titulo',)
    date_hierarchy = 'data_inicio'


admin.site.register(Banner, BannerAdmin)


class TipoAtendimentoAdmin(ModelAdminPlus):
    list_display = ('descricao',)


admin.site.register(TipoAtendimento, TipoAtendimentoAdmin)


class MotivoAtendimentoAdmin(ModelAdminPlus):
    list_display = ('descricao',)


admin.site.register(MotivoAtendimento, MotivoAtendimentoAdmin)


class AssuntoAtendimentoAdmin(ModelAdminPlus):
    list_display = ('descricao',)


admin.site.register(AssuntoAtendimento, AssuntoAtendimentoAdmin)


class PublicoAtendimentoAdmin(ModelAdminPlus):
    list_display = ('descricao',)


admin.site.register(PublicoAtendimento, PublicoAtendimentoAdmin)


class SituacaoAtendimentoAdmin(ModelAdminPlus):
    list_display = ('descricao',)


admin.site.register(SituacaoAtendimento, SituacaoAtendimentoAdmin)


class AtendimentoPublicoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('data_cadastro', 'campus', 'tipo', 'motivo', 'assunto', 'publico', 'situacao')
    list_filter = ('tipo', 'motivo', 'assunto', 'publico', 'situacao')
    date_hierarchy = 'data_cadastro'
    form = AtendimentoPublicoForm

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if request.user.has_perm('ae.add_tipoatendimento'):
            list_filter = ('campus',) + self.list_filter
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.add_tipoatendimento'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs


admin.site.register(AtendimentoPublico, AtendimentoPublicoAdmin)
