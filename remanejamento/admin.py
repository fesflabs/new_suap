# -*- coding: utf-8 -*-

import datetime

from django.contrib import admin
from django.db import models
from django.template import defaultfilters
from django.utils.formats import localize
from django.utils.safestring import mark_safe

from djtools.contrib.admin import ModelAdminPlus, DateRangeListFilter
from djtools.templatetags.filters import in_group, format_
from remanejamento.forms import DisciplinaAdminForm, EditalForm
from remanejamento.models import Disciplina, Edital, Inscricao, DisciplinaItem, EditalRecurso
from rh.models import Servidor


class EditalAdmin(ModelAdminPlus):
    form = EditalForm
    list_display = ('titulo', 'show_periodo_inscricoes', 'show_cargos', 'show_acoes')
    list_filter = ('cargos',)
    search_fields = ('titulo',)
    list_display_icons = True

    def has_change_permission(self, request, obj=None):
        has_change_permission = super(EditalAdmin, self).has_change_permission(request, obj)
        if obj:
            has_change_permission = has_change_permission and (
                request.user in obj.coordenadores.all() or request.user.is_superuser)

        return has_change_permission

    def show_cargos(self, obj):
        out = ['<ul>']
        for cargo in obj.cargos.all():
            out.append(f'<li>{str(cargo)}</li>')
        out.append('</ul>')
        return mark_safe(''.join(out))

    show_cargos.short_description = 'Cargos'

    def show_periodo_inscricoes(self, obj):
        return mark_safe(
            f'<span class="{obj.is_em_periodo_de_inscricao()}">{localize(obj.inicio_inscricoes)} a {localize(obj.fim_inscricoes)}</span>')

    show_periodo_inscricoes.admin_order_field = 'inicio_inscricoes'
    show_periodo_inscricoes.short_description = 'Período de Inscrições'

    def show_acoes(self, obj):
        html_acoes = ''
        if self.has_change_permission(self.request, obj):
            usuario_logado = self.request.user
            html_acoes = '<ul class="action-bar">'
            if (
                    (usuario_logado.has_perm('remanejamento.add_disciplina') or usuario_logado.has_perm(
                        'remanejamento.change_disciplina'))
                    and obj.inicio_resultados
                    and obj.inicio_resultados > datetime.datetime.now()
            ):
                html_acoes += f'<li><a class="btn success" href="/remanejamento/adicionar_disciplinas/{obj.pk}/">Adicionar Disciplinas</a></li>'
            html_acoes += f'<li><a class="btn" href="/remanejamento/inscricoes_csv/{obj.pk}/">Gerar CSV</a></li></ul>'
        return mark_safe(html_acoes)

    show_acoes.short_description = 'Ações'

    fieldsets = (
        ('Dados Gerais',
         {'fields': ('titulo', 'descricao', 'url', 'campus', 'cargos', 'coordenadores', 'tem_anexo', 'chave_hash')}),
        ('Recurso ao Edital',
         {'fields': (('inicio_recursos_edital', 'fim_recursos_edital'), 'resultado_recursos_edital')}),
        ('Inscrições', {'fields': ('inicio_inscricoes', 'fim_inscricoes')}),
        ('Avaliações', {'fields': ('inicio_avaliacoes', 'fim_avaliacoes')}),
        ('Desistência do Edital', {'fields': (('inicio_desistencias', 'fim_desistencias'),)}),
        ('Recursos ao Resultado', {'fields': (('inicio_recursos', 'fim_recursos'), 'resultado_recursos')}),
        ('Resultado Final', {'fields': ('inicio_resultados',)}),
    )


admin.site.register(Edital, EditalAdmin)


class EditalRecursoAdmin(ModelAdminPlus):
    list_display_comum = ('edital', 'servidor', 'dh_recurso')
    list_display_coordenador = ('edital', 'servidor', 'dh_recurso', 'recurso_respondido')
    list_filter_comum = ('edital',)
    list_filter_coordenador = ('edital', 'recurso_respondido', 'edital__cargos', ('edital__inicio_resultados', DateRangeListFilter))
    search_fields = [f'servidor__{servidor}' for servidor in Servidor.SEARCH_FIELDS]
    export_to_xls = True
    list_display_icons = True

    # não exibe o botão "Adicionar"
    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        has_view_permission = super().has_view_permission(request, obj)
        if obj:
            sou_coordenador = obj.edital.coordenadores.filter(pk=request.user.pk).exists()
            sou_dono_recurso = obj.servidor == request.user.get_relacionamento()
            has_view_permission = has_view_permission and (
                sou_coordenador or sou_dono_recurso) or request.user.is_superuser
        return has_view_permission

    def changelist_view(self, request, extra_context=None):
        if in_group(request.user, ['Coordenador de Remanejamento', 'Avaliador de Remanejamento',
                                   'Coordenador de Gestão de Pessoas Sistêmico']):
            self.list_display = self.list_display_coordenador
            self.list_filter = self.list_filter_coordenador
        else:
            self.list_display = self.list_display_comum
            self.list_filter = self.list_filter_comum

        return super(EditalRecursoAdmin, self).changelist_view(request, extra_context)

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Edital', 'Servidor', 'Horário de Cadastro do Recurso', 'Texto do Recurso',
                  'Horário de Cadastro da Resposta ao Recurso', 'Resposta ao Recurso']
        rows = [header]
        superusuario = request.user.is_superuser
        relacionamento = request.user.get_relacionamento()
        eh_servidor = relacionamento.eh_servidor
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [idx + 1, obj.edital, obj.servidor, obj.dh_recurso,
                   obj.recurso_texto, obj.dh_resposta, obj.recurso_resposta]
            if superusuario or request.user in obj.edital.coordenadores.all() or \
                    (eh_servidor and relacionamento == obj.servidor):
                rows.append(row)
        return rows


admin.site.register(EditalRecurso, EditalRecursoAdmin)


class DisciplinaItemInline(admin.StackedInline):
    model = DisciplinaItem


class DisciplinaAdmin(ModelAdminPlus):
    list_display = ['descricao', 'edital', 'show_avaliadores']
    search_fields = ['descricao']
    inlines = [DisciplinaItemInline]
    form = DisciplinaAdminForm
    list_filter = ['edital']

    def show_avaliadores(self, obj):
        out = ['<ul>']
        for avaliador in obj.avaliadores.all():
            out.append('<li class="text-nowrap">%s (%s)</li>' % (str(avaliador), avaliador.get_profile().nome))
        out.append('<ul>')
        return mark_safe(''.join(out))

    show_avaliadores.short_description = 'Avaliadores'


admin.site.register(Disciplina, DisciplinaAdmin)


class DisciplinaItemAdmin(ModelAdminPlus):
    list_display = ['disciplina', 'descricao', 'sequencia', 'nao_avaliar']


admin.site.register(DisciplinaItem, DisciplinaItemAdmin)


def restringir_inscricoes(self, request):
    if request.user.is_superuser:
        return admin.ModelAdmin.get_queryset(self, request)
    else:
        return (
            admin.ModelAdmin.get_queryset(self, request)
            .filter(
                models.Q(edital__coordenadores=request.user)
                | models.Q(avaliacao_avaliador=request.user)
                | models.Q(disciplina__avaliadores=request.user)
                | models.Q(servidor=request.user.get_relacionamento())
            )
            .distinct()
        )


class InscricaoDisciplinaFilter(admin.SimpleListFilter):
    title = "disciplina"
    parameter_name = "disciplina"

    def lookups(self, request, model_admin):
        edital = request.GET.get('edital__id__exact')
        disciplinas = Disciplina.objects.filter(edital__id__exact=edital)
        if edital and disciplinas.exists():
            return [(d.id, d.descricao) for d in Disciplina.objects.filter(edital__id__exact=edital)]
        return None

    def queryset(self, request, queryset):
        if self.value():
            edital = Edital.objects.filter(pk=request.GET.get('edital__id__exact'))
            if edital.exists() and edital[0].disciplina_set.filter(id=self.value()).exists():
                return queryset.filter(disciplina__id__exact=self.value())
            else:
                self.used_parameters.pop(self.parameter_name)
        return queryset


class RecursoFilter(admin.SimpleListFilter):
    title = 'Tem Recurso?'
    parameter_name = 'recurso'

    def lookups(self, request, model_admin):
        return (('s', 'Sim'), ('n', 'Não'))

    def queryset(self, request, queryset):
        if self.value() == 's':
            return queryset.exclude(recurso_texto='')
        elif self.value() == 'n':
            return queryset.filter(recurso_texto='')
        return queryset


class RecursoRespondidoFilter(admin.SimpleListFilter):
    title = 'Recurso Respondido?'
    parameter_name = 'recurso_respondido'

    def lookups(self, request, model_admin):
        return (('s', 'Sim'), ('n', 'Não'))

    def queryset(self, request, queryset):
        if self.value() == 'n':
            return queryset.filter(avaliacao_recurso='').exclude(recurso_texto='')
        elif self.value() == 's':
            return queryset.exclude(avaliacao_recurso='')
        return queryset


class InscricaoAdmin(ModelAdminPlus):
    list_display = ['show_informacoes', 'horario', 'servidor', 'show_disciplina',
                    'show_data_inicio_exercicio_no_cargo', 'show_recurso', 'confirmada', 'show_cancelar']
    get_queryset = restringir_inscricoes
    search_fields = ['id'] + [f'servidor__{servidor}' for servidor in Servidor.SEARCH_FIELDS]
    list_display_icons = True
    export_to_xls = True

    def get_list_filter(self, request):
        if request.user.is_superuser or in_group(request.user,
                                                 ['Coordenador de Remanejamento', 'Avaliador de Remanejamento']):
            return ('edital', 'confirmada', InscricaoDisciplinaFilter, RecursoFilter, RecursoRespondidoFilter)
        else:
            return ('edital', 'confirmada', InscricaoDisciplinaFilter)

    def show_informacoes(self, obj):
        out = ['<dl><dt>Edital:</dt><dd>%s</dd>' % str(obj.edital)]
        if obj.disciplina:
            out.append('<dt>Disciplina:</dt><dd>%s</dd>' % str(obj.disciplina.descricao))
        if obj.avaliacao_avaliador:
            out.append('<dt>Avaliador:</dt><dd>%s (%s)</dd>' % (
                str(obj.avaliacao_avaliador), str(obj.avaliacao_avaliador.get_profile().nome)))
        out.append('</dl>')
        if obj.data_desistencia:
            out.append('<span class="status status-error">Desistência em %s</span>' % format_(obj.data_desistencia))

        return mark_safe(''.join(out))

    show_informacoes.short_description = 'Informações'

    def show_recurso(self, obj):

        html = '<dl><dt>Tem Recurso:</dt>'
        if obj.recurso_texto:
            html += '<dd><span class="status status-success">Sim</span></dd>'
            html += '<dt>Recurso Respondido:</dt>'
            if obj.avaliacao_recurso:
                html += '<dd><span class="status status-success">Sim</span></dd>'
            else:
                html += '<dd><span class="status status-error">Não</span></dd>'
        else:
            html += '<dd><span class="status status-error">Não</span></dd>'
        html += '</dt>'

        return mark_safe(html)

    show_recurso.short_description = 'Recurso'

    def show_cancelar(self, obj):
        if obj.confirmada and obj.is_pode_desistir(self.request.user):
            return mark_safe(
                '<a title="Cancelar Inscrição (Desistência)" class="btn danger text-center" href="/remanejamento/inscricao/%s/desistir/">Cancelar Inscrição </br>(Desistência)</a>'
                % obj.pk
            )
        return '-'

    show_cancelar.short_description = 'Ações'

    def show_data_inicio_exercicio_no_cargo(self, obj):
        return obj.servidor.data_inicio_exercicio_no_cargo

    show_data_inicio_exercicio_no_cargo.short_description = 'Data de Início do Exercício no Cargo'
    show_data_inicio_exercicio_no_cargo.admin_order_field = 'servidor__data_inicio_exercicio_no_cargo'

    def show_disciplina(self, obj):
        retorno = ''
        servidor = obj.servidor
        if servidor.eh_docente:
            retorno += '<dl>'
            retorno += '<dt>Disciplina de Ingresso:</dt><dd>{}</dd>'.format(
                obj.servidor.disciplina_ingresso or 'Não definido')
            if obj.disciplina:
                retorno += '<dt>Disciplina Inscrita:</dt><dd>{}</dd>'.format(obj.disciplina.descricao or 'Não definido')
            retorno += '</dl>'
        return mark_safe(retorno)

    show_disciplina.short_description = 'Disciplina'
    show_disciplina.admin_order_field = 'disciplina'

    def show_score(self, obj):
        if obj.avaliacao_score is not None:
            return defaultfilters.floatformat(obj.avaliacao_score, 2)
        else:
            return '-'

    show_score.admin_order_field = 'avaliacao_score'
    show_score.short_description = 'Score'

    def has_change_permission(self, request, obj=None):
        if obj and not request.user.is_superuser:
            return False
        return super(InscricaoAdmin, self).has_change_permission(request, obj)

    def to_xls(self, request, queryset, processo):
        header = [
            '#',
            'Edital',
            'Candidato',
            'Disciplina de Ingresso',
            'Disciplina',
            'Data de Início do Exercício no Cargo',
            'Data Usada para Cálculo do Tempo de Serviço',
            'Tempo de Serviço no Cargo',
            'Tempo de Serviço no Cargo(Retirando Afastamentos)',
            'Texto do Recurso',
            'Confirmada',
        ]
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            data_referencia_edital = datetime.date.today()
            if obj.edital.inicio_resultados:
                data_referencia_edital = obj.edital.inicio_inscricoes.date()
            tempo_servico_no_cargo = obj.servidor.tempo_servico_no_cargo(
                data_referencia=data_referencia_edital)
            tempo_servico_no_cargo_via_pca = obj.servidor.tempo_servico_no_cargo_via_pca(
                data_referencia=data_referencia_edital)
            row = [
                idx + 1,
                obj.edital,
                obj.servidor,
                obj.servidor.disciplina_ingresso,
                obj.disciplina,
                obj.servidor.data_inicio_exercicio_no_cargo,
                data_referencia_edital,
                '%s - %s dias' % (format_(tempo_servico_no_cargo), tempo_servico_no_cargo.days),
                '%s - %s dias' % (format_(tempo_servico_no_cargo_via_pca), tempo_servico_no_cargo_via_pca.days),
                obj.recurso_texto,
                obj.confirmada,
            ]
            rows.append(row)
        return rows


admin.site.register(Inscricao, InscricaoAdmin)
