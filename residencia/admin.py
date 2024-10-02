from django.contrib.admin import SimpleListFilter
from django.contrib.admin.utils import unquote
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import path

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import in_group
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from residencia import perms
from residencia.models import (
    Residente, SolicitacaoResidente, Matriz, Componente, RepresentacaoConceitual, EstruturaCurso, CursoResidencia,
    Turma, CalendarioAcademico, ProjetoFinalResidencia, AtaEletronicaResidencia, SolicitacaoEletivo, EstagioEletivo,
    Diario, ComponenteCurricular, MatriculaDiario, MatriculaPeriodo, SituacaoMatriculaPeriodo, TipoPreceptorDiario,
    UnidadeAprendizagem, UnidadeAprendizagemTurma, ItemConfiguracaoAvaliacaoUnidadeAprendizagem,
    ConfiguracaoAvaliacaoUnidadeAprendizagem
)
from residencia.forms import (
    ResidenteForm, ResidenteEditarForm, MatrizForm, ComponenteForm, EstruturaCursoForm, CursoResidenciaForm, TurmaForm,
    CalendarioAcademicoForm, DiarioForm, PreceptorDiario, SolicitacaoUsuarioForm, UnidadeAprendizagemTurmaForm,
    ConfiguracaoAvaliacaoUnidadeAprendizagemForm, ItemConfiguracaoAvaliacaoUnidadeAprendizagemFormset
)
from residencia.models.solicitacoes import SolicitacaoUsuario


class ResidenteAdmin(ModelAdminPlus):
    list_display = ('get_foto', 'get_info_principal', 'data_matricula')
    list_display_icons = True
    export_to_xls = True
    list_per_page = 15
    ordering = ('-id',)
    form = ResidenteForm
    change_form = ResidenteEditarForm
    # fieldsets = ResidenteForm.fieldsets

    search_fields = ('pessoa_fisica__nome_registro', 'pessoa_fisica__search_fields_optimized',)

    def has_add_permission(self, request):
        return False

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if request.user.has_perm('residencia.efetuar_matricula'):
            items.append(dict(url='/residencia/efetuarmatricula/', label='Adicionar Novo(a) Residente', css_class='success'))
        return items

    def get_queryset(self, request, manager=None, *args, **kwargs):
        return super().get_queryset(
            request, Residente.objects
        ).select_related('pessoa_fisica')

    def get_foto(self, obj):
        return mark_safe(f'<img class="img-inside-container" src="{obj.get_foto_75x100_url()}"/>')

    get_foto.short_description = 'Foto'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Nome', 'Matrícula', 'E-mail Acadêmico', 'E-mail Pessoal']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [
                idx + 1,
                obj.get_nome_social_composto(),
                obj.matricula,
                format(obj.pessoa_fisica.email),
                obj.pessoa_fisica.email_secundario,
            ]
            rows.append(row)
        return rows

    def get_info_principal(self, obj):
        out = '''
                <dl>
                    <dt class="hidden">Nome:</dt><dd class="negrito">{}</dd>'''.format(
            obj.pessoa_fisica.nome_registro
        )
        if obj.pessoa_fisica.nome_social:
            out += f'<dt>Nome Social:</dt><dd>{obj.pessoa_fisica.nome_social}</dd>'
        if in_group(self.request.user, 'Administrador Acadêmico, Secretário Acadêmico'):
            out += f'<dt>CPF:</dt><dd>{obj.pessoa_fisica.cpf}</dd>'
        out += '''<dt>Matrícula:</dt><dd>{}</dd>
                </dl>
            '''.format(obj.matricula)
        return mark_safe(out)

    get_info_principal.short_description = 'Dados Principais'
    get_info_principal.admin_order_field = 'pessoa_fisica__nome'


admin.site.register(Residente, ResidenteAdmin)


class RepresentacaoConceitualInline(admin.TabularInline):
    model = RepresentacaoConceitual
    extra = 3



class UnidadeAprendizagemAdmin(ModelAdminPlus):
    list_display = ('descricao', 'qtd_avaliacoes', 'ciclo',)
    list_display_icons = True
    search_fields = ('descricao',)
    ordering = ('ciclo',)

admin.site.register(UnidadeAprendizagem, UnidadeAprendizagemAdmin)

class EstruturaCursoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'ativo')
    list_filter = ('ativo',)
    list_display_icons = True
    search_fields = ('descricao',)
    form = EstruturaCursoForm
    inlines = [RepresentacaoConceitualInline]
    export_to_xls = True

    fieldsets = (
        ('Dados Gerais', {'fields': ('descricao', 'ativo')}),
        (
            'Critérios de Avaliação por Disciplinas',
            {'fields': ('criterio_avaliacao', 'media_aprovacao_sem_prova_final', )},
        ),
    )


admin.site.register(EstruturaCurso, EstruturaCursoAdmin)


class CursoResidenciaAdmin(ModelAdminPlus):
    list_display = ('codigo', 'descricao', 'ativo', 'get_matrizes')
    list_filter = (CustomTabListFilter, 'ativo')

    list_display_icons = True
    exclude = ('codigo_academico',)
    search_fields = ('descricao', 'codigo',)
    list_per_page = 15
    export_to_xls = True
    list_xls_display = (
        'id',
        'descricao',
        'descricao_historico',
        'data_inicio',
        'data_fim',
        'ativo',
        'possui_residente_cursando',
        'codigo',
        'coordenador',
        'get_matrizes',
    )
    show_count_on_tabs = True

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        list_display = list(list_display) + ['coordenador']
        return list_display

    def get_matrizes(self, obj):
        if hasattr(obj, 'export_to_xls'):
            return ', '.join([str(f'{matriz} - {matriz.get_ch_total()} horas') for matriz in obj.matrizes.all()])
        lista = ['<ul>']
        for matriz in obj.matrizes.all():
            lista.append('<li> ')
            lista.append(f'<a href="/residencia/matriz/{matriz.pk}/">{str(matriz.descricao)}</a>')
            lista.append('</li>')
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_matrizes.short_description = 'Matrizes'

    form = CursoResidenciaForm

    fieldsets = (
        (
            'Identificação',
            {
                'fields': (
                    ('descricao',),
                    ('descricao_historico',),
                )
            },
        ),
        ('Dados da Criação', {'fields': ( ('data_inicio', 'data_fim'), 'ativo')}),
        ('Coordenação', {'fields': ('coordenador', )}),
        (
            'Dados Gerais',
            {
                'fields': (
                    'codigo',
                )
            },
        ),
    )

    def get_queryset(self, request):
        return CursoResidencia.locals.all()

    def get_tabs(self, request):
        return ['tab_com_coordenadores', 'tab_sem_coordenadores', ]

    def tab_com_coordenadores(self, request, queryset):
        return queryset.com_coordenadores()

    tab_com_coordenadores.short_description = 'Com Coordenadores'

    def tab_sem_coordenadores(self, request, queryset):
        return queryset.sem_coordenadores()

    tab_sem_coordenadores.short_description = 'Sem Coordenadores'

    def tab_sob_minha_coordenacao(self, request, queryset):
        return queryset.sob_coordenacao_de(request.user.get_profile())

    tab_sob_minha_coordenacao.short_description = 'Sob Minha Coordenação'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        q = '?ativo__exact=1'
        return HttpResponseRedirect('/admin/residencia/cursoresidencia/' + q)

    def response_add(self, request, obj):
        self.message_user(request, 'Curso cadastrado com sucesso. Por favor, vincule a(s) matriz(es) ao curso.')
        return HttpResponseRedirect(f'/residencia/cursoresidencia/{obj.pk}/')


admin.site.register(CursoResidencia, CursoResidenciaAdmin)


class ComponenteAdmin(ModelAdminPlus):
    list_display = ('id', 'sigla', 'descricao', 'ch_hora_relogio',  'ativo',  'observacao')
    list_filter = (CustomTabListFilter, 'ativo',  'matriz')
    search_fields = ('id', 'sigla', 'descricao', 'observacao',)
    list_display_icons = True
    export_to_xls = True
    list_per_page = 15
    form = ComponenteForm
    fieldsets = (
        ('Dados Gerais', {'fields': ('descricao', 'descricao_historico', 'abreviatura', 'ativo')}),
        ('Carga Horária', {'fields': ('ch_hora_relogio', )}),
        ('Dados Extras', {'fields': ('observacao',)}),
    )

    def get_tabs(self, request):
        return ['utilizados', 'nao_utilizados']

    def utilizados(self, request, queryset):
        qs_componente_curricular = queryset.filter(componentecurricular__id__isnull=False)
        return (qs_componente_curricular).distinct()

    utilizados.short_description = 'Utilizados'

    def nao_utilizados(self, request, queryset):
        qs_componente_curricular = queryset.filter(componentecurricular__id__isnull=False)
        qs_vinculados = (qs_componente_curricular ).distinct()
        return queryset.exclude(id__in=qs_vinculados.values_list("id", flat=True))

    nao_utilizados.short_description = 'Não Utilizados'


admin.site.register(Componente, ComponenteAdmin)


class MatrizAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'ativo')
    list_filter = (CustomTabListFilter,  'ativo', 'estrutura')
    search_fields = ('id', 'descricao')
    list_display_icons = True
    list_per_page = 15
    export_to_xls = True
    form = MatrizForm
    show_count_on_tabs = True

    fieldsets = (
        (
            'Dados Gerais',
            {'fields': ('descricao',  'ativo', ('data_inicio', 'data_fim'), 'ppp', 'qtd_periodos_letivos', 'estrutura')},
        ),
        (
            'Carga Horária',
            {
                'fields': (
                    ('ch_pratica', 'ch_teorica', 'ch_teorico_pratica'),
                )
            },
        ),
        ('Critérios', {'fields': ('porcetagem_cumprimento_ch_teorica',)}),
        ('Trabalho de Conclusão de Residência', {'fields': ('exige_tcr',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request)

    def get_tabs(self, request):
        return ['tab_vazias', 'tab_incompletas']

    def tab_vazias(self, request, queryset):
        return queryset.vazias()

    tab_vazias.short_description = 'Vazias'

    def tab_incompletas(self, request, queryset):
        return queryset.incompletas()

    tab_incompletas.short_description = 'Inconsistentes'

    def response_add(self, request, obj):
        self.message_user(request, 'Matriz cadastrada com sucesso. Por favor, vincule os componentes à matriz.')
        return HttpResponseRedirect(f'/residencia/matriz/{obj.pk}/')

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        url = '/admin/residencia/matriz/?&ativo__exact=1'
        return HttpResponseRedirect(url)


admin.site.register(Matriz, MatrizAdmin)


class SolicitacaoResidenteAdmin(ModelAdminPlus):
    list_display = ('get_foto', 'get_info_principal', 'situacao', 'alterado_em', 'get_opcoes')
    list_display_icons = False
    export_to_xls = True
    list_per_page = 15
    ordering = ('-id',)
    date_hierarchy = 'alterado_em'
    search_fields = ('nome_registro', 'cpf',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        raise PermissionDenied()

    def get_queryset(self, request, manager=None, *args, **kwargs):
        return super().get_queryset(
            request, SolicitacaoResidente.objects
        )

    def get_foto(self, obj):
        return mark_safe(f'<img class="img-inside-container" src="{obj.get_foto_75x100_url()}"/>')

    get_foto.short_description = 'Foto'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Nome', 'CPF', 'E-mail Acadêmico', 'E-mail Pessoal']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [
                idx + 1,
                obj.get_nome_social_composto(),
                obj.cpf,
                format(obj.email_academico),
                obj.email,
            ]
            rows.append(row)
        return rows

    def get_info_principal(self, obj):
        out = '''
                <dl>
                    <dt class="hidden">Nome:</dt><dd class="negrito">{}</dd>'''.format(
            obj.nome_registro
        )
        if obj.nome_social:
            out += f'<dt>Nome Social:</dt><dd>{obj.nome_social}</dd>'
        out += '''<dt>CPF:</dt><dd>{}</dd>
                </dl>
            '''.format(obj.cpf)
        return mark_safe(out)

    get_info_principal.short_description = 'Dados Principais'
    get_info_principal.admin_order_field = 'nome_registro'

    def get_opcoes(self, obj):
        if self.request.user.has_perm('residencia.efetuar_matricula'):
            texto = '<ul class="action-bar">'
            if obj.parecer:
                texto += '<li><a href="/residencia/analisar_solicitresidente/{:d}/" class="btn primary"><span class="fas fa-edit" aria-hidden="true"></span> Editar Análise</a></li>'.format(obj.pk)
            else:
                texto += '<li><a href="/residencia/analisar_solicitresidente/{:d}/" class="btn success"><span class="fas fa-plus" aria-hidden="true"></span> Analisar</a></li>'.format(obj.pk)

        else:
            texto = '-'
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'


admin.site.register(SolicitacaoResidente, SolicitacaoResidenteAdmin)


class CalendarioAcademicoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'tipo', 'ano_letivo', 'periodo_letivo', 'data_inicio', 'data_fim')
    list_filter = ('tipo', 'ano_letivo', 'periodo_letivo', )
    list_display_icons = True
    search_fields = ('descricao', 'id')
    export_to_xls = True
    form = CalendarioAcademicoForm

    fieldsets = (
        ('Dados Gerais', {'fields': (('descricao',), ('tipo',), ('ano_letivo', 'periodo_letivo'))}),
        (
            'Período Letivo',
            {
                'fields': (
                    ('data_inicio', 'data_fim'),
                    ('data_inicio_trancamento', 'data_fim_trancamento'),
                    'data_fechamento_periodo',
                )
            },
        ),
        ('Ciclos de Avaliações', {'fields': ('qtd_etapas',)}),
        ('1º Ciclos', {'fields': (('data_inicio_etapa_1', 'data_fim_etapa_1'),)}),
        ('2º Ciclos', {'fields': (('data_inicio_etapa_2', 'data_fim_etapa_2'),)}),
        ('3º Ciclos', {'fields': (('data_inicio_etapa_3', 'data_fim_etapa_3'),)}),
        ('4º Ciclos', {'fields': (('data_inicio_etapa_4', 'data_fim_etapa_4'),)}),

    )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        qs = self.get_queryset(request)
        if qs.exists():
            ano = qs.latest('ano_letivo__ano').ano_letivo.id
            url = f'/admin/residencia/calendarioacademico/?ano_letivo__id__exact={ano}'
        else:
            url = '/admin/residencia/calendarioacademico/'
        return HttpResponseRedirect(url)

    def get_queryset(self, request):
        return self.model.objects.all()


admin.site.register(CalendarioAcademico, CalendarioAcademicoAdmin)

class TurmaAdmin(ModelAdminPlus):
    list_display = ('codigo', 'descricao', 'sigla', 'ano_letivo', 'periodo_letivo', 'get_qtd_diarios', 'get_qtd_residentes')
    list_filter = (CustomTabListFilter, ('ano_letivo'), 'periodo_letivo',  'curso_campus', )

    list_display_icons = True
    export_to_xls = True
    list_xls_display = 'id', 'codigo', 'descricao', 'sigla', 'ano_letivo', 'periodo_letivo', 'get_qtd_diarios', 'get_qtd_residentes',
    list_per_page = 15
    search_fields = ('descricao', 'codigo', 'sigla', 'id')
    form = TurmaForm
    show_count_on_tabs = True

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if request.user.has_perm('residencia.gerar_turmas'):
            items.append(dict(url='/residencia/gerar_turmas/', label='Gerar Turmas'))
        return items

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        qs = self.get_queryset(request)
        if qs.exists():
            ano = qs.latest('ano_letivo__ano').ano_letivo.id
            url = f'/admin/residencia/turma/?ano_letivo__id__exact={ano}'
        else:
            url = '/admin/residencia/turma/'
        return HttpResponseRedirect(url)

    def get_qtd_diarios(self, obj):
        return obj.diarios_turma_residencia_set.order_by('componente_curricular__componente').count()

    get_qtd_diarios.short_description = 'Qtd de Diários'

    def get_qtd_residentes(self, obj):
        return obj.get_residentes_matriculados().count()

    get_qtd_residentes.short_description = 'Qtd de Residentes'

    def get_queryset(self, request):
        return super().get_queryset(request, Turma.objects)

    def delete_view(self, request, object_id, extra_context=None):
        try:
            turma = Turma.objects.get(pk=object_id)
        except Turma.DoesNotExist:
            msg = 'A turma escolhida não pode ser encontrada.'
            messages.error(request, msg)
            return httprr('/admin/residencia/turma/')
        if not request.POST:
            return super().delete_view(request, object_id, extra_context)
        elif request.POST and (request.user.groups.filter(name__in=['residencia Administrador']).exists() or turma.pode_ser_excluido()):
            return super().delete_view(request, object_id, extra_context)
        else:
            msg = 'Não é possível realizar a exclusão. Existem diários com residentes para esta turma.'
            messages.error(request, msg)
            return redirect('.')


admin.site.register(Turma, TurmaAdmin)

#FES-68

class ProjetoFinalResidenciaAdmin(ModelAdminPlus):
    list_display = 'get_residente', 'get_ano_letivo', 'get_periodo_letivo', 'tipo', 'titulo'
    list_display_icons = True
    #list_filter = ('matricula_periodo__ano_letivo', 'matricula_periodo__periodo_letivo', 'tipo', 'matricula_periodo__aluno__curso_campus__diretoria', 'matricula_periodo__aluno__curso_campus',)
    search_fields = ('matricula_periodo__aluno__matricula', 'matricula_periodo__aluno__pessoa_fisica__nome', 'titulo')
    list_per_page = 15

    def get_action_bar(self, request):
        return super(self.__class__, self).get_action_bar(request, True)

    def get_residente(self, obj):
        return obj.matricula_periodo.residente

    get_residente.short_description = 'Residente'

    def get_ano_letivo(self, obj):
        return obj.matricula_periodo.ano_letivo

    get_ano_letivo.short_description = 'Ano Letivo'

    def get_periodo_letivo(self, obj):
        return obj.matricula_periodo.periodo_letivo

    get_periodo_letivo.short_description = 'Período Letivo'

    def get_curso(self, obj):
        return obj.matricula_periodo.aluno.curso_campus

    get_curso.short_description = 'Curso'


admin.site.register(ProjetoFinalResidencia, ProjetoFinalResidenciaAdmin)


class AtaEletronicaResidenciaAdmin(ModelAdminPlus):
    list_display = 'get_aluno', 'get_ano_letivo', 'get_periodo_letivo', 'get_tipo', 'get_titulo', 'get_responsaveis', 'get_acoes'
    list_display_icons = True
    #list_filter = (CustomTabListFilter, 'projeto_final__matricula_periodo__ano_letivo', 'projeto_final__matricula_periodo__periodo_letivo', 'projeto_final__tipo', 'projeto_final__matricula_periodo__aluno__curso_campus__diretoria', 'projeto_final__matricula_periodo__aluno__curso_campus',)
    search_fields = ('projeto_final__matricula_periodo__aluno__matricula', 'projeto_final__matricula_periodo__aluno__pessoa_fisica__nome')
    list_per_page = 15

    def get_action_bar(self, request):
        return super(self.__class__, self).get_action_bar(request, True)

    def get_aluno(self, obj):
        return obj.projeto_final.matricula_periodo.aluno

    get_aluno.short_description = 'Aluno'

    def get_ano_letivo(self, obj):
        return obj.projeto_final.matricula_periodo.ano_letivo

    get_ano_letivo.short_description = 'Ano Letivo'

    def get_periodo_letivo(self, obj):
        return obj.projeto_final.matricula_periodo.periodo_letivo

    get_periodo_letivo.short_description = 'Período Letivo'

    def get_curso(self, obj):
        return obj.projeto_final.matricula_periodo.aluno.curso_campus

    get_aluno.short_description = 'Curso'

    def get_tipo(self, obj):
        return obj.projeto_final.tipo

    get_tipo.short_description = 'Tipo'

    def get_titulo(self, obj):
        return obj.projeto_final.titulo

    get_titulo.short_description = 'Título'

    def get_resultado(self, obj):
        return obj.projeto_final.resultado

    get_resultado.short_description = 'Resultado'

    def get_responsaveis(self, obj):
        html = []
        html.append('<ul>')
        for assinatura in obj.get_assinaturas():
            html.append(f'<li>{assinatura.pessoa_fisica}</li>')
        html.append('</ul>')
        return mark_safe(''.join(html))

    get_responsaveis.short_description = 'Signatários'

    def get_acoes(self, obj):
        html = []
        html.append('<ul class="action-bar">')
        html.append('<li><a target="_blank" class="btn default" href="{}">{}</a></li>'.format(
            f'/residencia/visualizar_ata_eletronica/{obj.pk}/', 'Visualizar Ata')
        )
        assinatura_pendente = obj.get_assinaturas().filter(data__isnull=True).filter(
            pessoa_fisica_id=self.request.user.get_vinculo().pessoa.id
        ).first()
        if assinatura_pendente:
            html.append('<li><a class="btn popup" href="{}">{}</a></li>'.format(
                f'/residencia/assinar_ata_eletronica/{assinatura_pendente.pk}/', 'Assinar Eletronicamente')
            )
        html.append('</ul>')
        return mark_safe(''.join(html))

    get_acoes.short_description = 'Ações'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.user.groups.filter(name__in=('Secretário Acadêmico', 'Administrador Acadêmico', 'Estagiário Acadêmico Sistêmico')).exists():
            queryset = queryset.filter(
                assinaturaataeletronica__pessoa_fisica__cpf=request.user.get_vinculo().pessoa.pessoafisica.cpf
            )
        return queryset

    def get_tabs(self, request):
        return ['tab_pendentes', 'tab_assinadas']

    def tab_pendentes(self, request, queryset):
        if request.user.groups.filter(name__in=('Secretário Acadêmico', 'Administrador Acadêmico', 'Estagiário Acadêmico Sistêmico')).exists():
            pks = queryset.filter(assinaturaataeletronica__data__isnull=True).values_list('pk', flat=True).distinct()
        else:
            pks = queryset.filter(
                assinaturaataeletronica__data__isnull=True,
                assinaturaataeletronica__pessoa_fisica__cpf=request.user.get_vinculo().pessoa.pessoafisica.cpf
            ).values_list('pk', flat=True).distinct()
        return queryset.filter(pk__in=pks)

    tab_pendentes.short_description = 'Pendentes'

    def tab_assinadas(self, request, queryset):
        if request.user.groups.filter(name__in=('Secretário Acadêmico', 'Administrador Acadêmico', 'Estagiário Acadêmico Sistêmico')).exists():
            pks = queryset.filter(assinaturaataeletronica__data__isnull=False).values_list('pk', flat=True).distinct()
        else:
            pks = queryset.filter(
                assinaturaataeletronica__data__isnull=False,
                assinaturaataeletronica__pessoa_fisica__cpf=request.user.get_vinculo().pessoa.pessoafisica.cpf
            ).values_list('pk', flat=True).distinct()
        return queryset.filter(pk__in=pks)

    tab_assinadas.short_description = 'Assinadas'


admin.site.register(AtaEletronicaResidencia, AtaEletronicaResidenciaAdmin)


class DiarioAdmin(ModelAdminPlus):
    list_display = ('id', 'turma', 'componente_curricular', 'ano_letivo', 'periodo_letivo', 'get_outras_informacoes')
    list_filter = (
        CustomTabListFilter,
        'ano_letivo',
        'periodo_letivo',
        'turma',
        'turma__curso_campus',
    )
    list_display_icons = True
    list_per_page = 15
    export_to_xls = True
    list_xls_display = 'id', 'turma', 'componente_curricular', 'ano_letivo', 'periodo_letivo', 'get_nomes_preceptores'
    search_fields = ('id', 'componente_curricular__componente__descricao', 'componente_curricular__componente__sigla')
    form = DiarioForm

    show_count_on_tabs = True

    def get_outras_informacoes(self, obj):
        html = []

        # Preceptores
        preceptores = obj.preceptordiario_set.all()
        if preceptores:
            lista_preceptores = []
            for preceptor_diario in preceptores:
                nome = f'{preceptor_diario.preceptor.nome} ({preceptor_diario.tipo})'
                lista_preceptores.append(nome)
            html.append('<br/>')
            html.append('<strong>Preceptores:</strong> ')
            if len(lista_preceptores) > 1:
                html.append('<ul>')
                for preceptor in lista_preceptores:
                    html.append(f'<li>{preceptor}</li>')
                html.append('<ul>')
            else:
                html.append(', '.join(lista_preceptores))
            html.append('<br/>')

        if not preceptores:
            return '-'
        return mark_safe(' '.join(html))

    get_outras_informacoes.short_description = 'Outras Informações'

    def get_queryset(self, request):
        return super().get_queryset(request, Diario.objects).select_related('turma', 'ano_letivo')

    def correntes(self, request):
        url = '/admin/residencia/diario/'
        return HttpResponseRedirect(url)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls


admin.site.register(Diario, DiarioAdmin)


#Wanderson - Parte da FES-65
class ComponenteCurricularAdmin (ModelAdminPlus):
    list_display_icons = True
    #list_display = ['nome']

admin.site.register(ComponenteCurricular, ComponenteCurricularAdmin)

class MatriculaDiarioAdmin (ModelAdminPlus):
    list_display_icons = True
    #list_display = ['nome']

admin.site.register(MatriculaDiario, MatriculaDiarioAdmin)

class MatriculaPeriodoAdmin(ModelAdminPlus):
    list_display_icons = True

admin.site.register(MatriculaPeriodo, MatriculaPeriodoAdmin)

class SituacaoMatriculaPeriodoAdmin(ModelAdminPlus):
    list_display_icons = True

admin.site.register(SituacaoMatriculaPeriodo, SituacaoMatriculaPeriodoAdmin)

class TipoPreceptorDiarioAdmin(ModelAdminPlus):
    list_display_icons = True

admin.site.register(TipoPreceptorDiario, TipoPreceptorDiarioAdmin)


class SolicitacaoFilter(SimpleListFilter):
    title = 'tipo'
    parameter_name = 'tipo'

    def lookups(self, request, model_admin):
        return (('solicitacao_ferias', 'Solicitação de Férias'), ('solicitacao_congressos', 'Solicitação de Congressos'),
                ('solicitacao_diplomas', 'Solicitação de Diplomas'),('solicitacao_desligamentos', 'Solicitação de Desligamentos'),
                ('solicitacao_licencas', 'Solicitação de Licenças'))
    def queryset(self, request, queryset):
        if self.value() == 'solicitacao_ferias':
            return queryset.filter(solicitacao_ferias__isnull=False)
        if self.value() == 'solicitacao_congressos':
            return queryset.filter(solicitacao_congressos__isnull=False)
        if self.value() == 'solicitacao_diplomas':
            return queryset.filter(solicitacao_diplomas__isnull=False)
        if self.value() == 'solicitacao_desligamentos':
            return queryset.filter(solicitacao_desligamentos__isnull=False)
        if self.value() == 'solicitacao_licencas':
            return queryset.filter(solicitacao_licencas__isnull=False)

class SolicitacaoUsuarioAdmin(ModelAdminPlus):
    list_display = ('id', 'get_solicitante', 'data_solicitacao', 'get_descricao', 'sub_instance_title', 'get_acoes')
    list_display_icons = True
    list_filter = (CustomTabListFilter, 'solicitante', 'avaliador', SolicitacaoFilter)
    search_fields = ('id', 'solicitante__first_name', 'solicitante__username', 'avaliador__first_name', 'avaliador__username')
    ordering = ('-data_avaliacao',)
    form = SolicitacaoUsuarioForm
    export_to_xls = True

    actions = ('deferir', 'indeferir')

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.show_actions and request.user.has_perm('residencia.change_solicitacaousuario'):
            return actions
        else:
            for key in list(actions.keys()):
                del actions[key]
            return actions

    def deferir(self, request, queryset):
        for solicitacao in queryset.filter(data_avaliacao__isnull=True):
            solicitacao.sub_instance().atender(request.user)
        messages.success(request, 'Solicitações deferidas com sucesso.')

    deferir.short_description = "Deferir"

    def indeferir(self, request, queryset):
        ids = [str(x) for x in queryset.filter(data_avaliacao__isnull=True).values_list('id', flat=True)]
        if ids:
            url = '/residencia/rejeitar_solicitacao/{}/'.format('_'.join(ids))
            return HttpResponseRedirect(url)

    indeferir.short_description = "Indeferir"

    def get_solicitante(self, obj):
        return mark_safe(obj.solicitante)

    get_solicitante.short_description = 'Solicitante'

    def get_action_bar(self, request):
        self.show_actions = request.GET.get('tab', None) == 'tab_pendentes'
        items = super().get_action_bar(request, True)
        return items

    def get_acoes(self, obj):
        lista = []
        if obj.data_avaliacao:
            if obj.atendida:
                lista.append('<span class="status status-success">Deferida por {} em {}</span>'.format(obj.avaliador, obj.data_avaliacao.strftime("%d/%m/%y")))
            else:
                lista.append('<span class="status status-error">Indeferida por {} em {}</span>'.format(obj.avaliador, obj.data_avaliacao.strftime("%d/%m/%y")))
        else:
            lista.append('<span class="status status-pendente">Pendente</span>')
        return mark_safe(' '.join(lista))

    get_acoes.short_description = 'Status'

    def get_descricao(self, obj):
        filho = obj.sub_instance()
        # if isinstance(filho, SolicitacaoRelancamentoEtapa) and filho.precisa_prorrogar_posse():
        #     return mark_safe(
        #         '<p>{}</p><span class="status status-error">Data de posse da etapa já foi ultrapassada, será preciso definir uma nova data limite para a posse.</span>'.format(
        #             obj.descricao
        #         )
        #     )
        # else:
        #     return obj.descricao
        return obj.descricao

    get_descricao.short_description = 'Descrição'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Solicitante', 'Data da Solicitação', 'Descrição',  'Status', 'Avaliador']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            if obj.data_avaliacao:
                if obj.atendida:
                    atendimento = 'Deferida'
                else:
                    atendimento = 'Indeferida'
            else:
                atendimento = 'Não avaliada'
            row = [idx + 1, obj.solicitante, obj.data_solicitacao, obj.descricao, atendimento, obj.avaliador]
            rows.append(row)
        return rows

    def get_tabs(self, request):
        return ['tab_pendentes', 'tab_avaliados']

    def tab_pendentes(self, request, queryset):
        return queryset.filter(data_avaliacao__isnull=True)

    tab_pendentes.short_description = 'Pendentes'

    def tab_avaliados(self, request, queryset):
        return queryset.filter(data_avaliacao__isnull=False)

    tab_avaliados.short_description = 'Avaliados'

    def get_queryset(self, request, manager=None):
        if not manager:
            manager = SolicitacaoUsuario.locals

        return super().get_queryset(request, manager)
        # return super().get_queryset(request, manager).filter(solicitacaoprorrogacaoetapa__isnull=False) | \
        #     super().get_queryset(request, manager).filter(solicitacaorelancamentoetapa__isnull=False)


admin.site.register(SolicitacaoUsuario, SolicitacaoUsuarioAdmin)


class SolicitacaoEletivoAdmin(ModelAdminPlus):
    list_display = ('get_icone', 'get_foto', 'get_info_principal', 'nome_servico', 'situacao', 'alterado_em', 'get_opcoes')
    list_display_icons = False
    list_per_page = 15
    ordering = ('-id',)
    date_hierarchy = 'alterado_em'
    search_fields = ('residente__pessoa_fisica__nome_registro', 'residente__pessoa_fisica__cpf',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        raise PermissionDenied()

    def get_queryset(self, request, manager=None, *args, **kwargs):
        return super().get_queryset(
            request, SolicitacaoEletivo.objects
        )

    def get_icone(self, obj):
        return mark_safe(icon('view', obj.get_absolute_url()))

    get_icone.short_description = 'Ações'

    def get_foto(self, obj):
        return mark_safe(f'<img class="img-inside-container" src="{obj.residente.get_foto_75x100_url()}"/>')

    get_foto.short_description = 'Foto'

    def get_info_principal(self, obj):
        out = '''
                <dl>
                    <dt class="hidden">Nome:</dt><dd class="negrito">{}</dd>'''.format(
            obj.residente.pessoa_fisica.nome_registro
        )
        if obj.residente.pessoa_fisica.nome_social:
            out += f'<dt>Nome Social:</dt><dd>{obj.residente.pessoa_fisica.nome_social}</dd>'
        out += '''<dt>CPF:</dt><dd>{}</dd>
                </dl>
            '''.format(obj.residente.pessoa_fisica.cpf)
        return mark_safe(out)

    get_info_principal.short_description = 'Residente'
    get_info_principal.admin_order_field = 'residente__pessoa_fisica__nome_registro'

    def get_opcoes(self, obj):
        if self.request.user.has_perm('residencia.efetuar_matricula'):
            texto = '<ul class="action-bar">'
            if obj.parecer:
                texto += '<li><a href="/residencia/analisar_soliciteletivo/{:d}/" class="btn primary"><span class="fas fa-edit" aria-hidden="true"></span> Editar Análise</a></li>'.format(obj.pk)
            else:
                texto += '<li><a href="/residencia/analisar_soliciteletivo/{:d}/" class="btn success"><span class="fas fa-plus" aria-hidden="true"></span> Analisar</a></li>'.format(obj.pk)

        else:
            texto = '-'
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'


admin.site.register(SolicitacaoEletivo, SolicitacaoEletivoAdmin)


class EstagioEletivoAdmin(ModelAdminPlus):
    list_display = ('get_icone', 'get_foto', 'get_info_principal', 'nome_servico', 'situacao', 'alterado_em')
    list_display_icons = False
    list_per_page = 15
    ordering = ('-id',)
    date_hierarchy = 'alterado_em'
    search_fields = ('residente__pessoa_fisica__nome_registro', 'residente__pessoa_fisica__cpf',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        raise PermissionDenied()

    def get_queryset(self, request, manager=None, *args, **kwargs):
        return super().get_queryset(
            request, EstagioEletivo.objects
        )

    def get_icone(self, obj):
        return mark_safe(icon('view', obj.get_absolute_url()))

    get_icone.short_description = 'Ações'

    def get_foto(self, obj):
        return mark_safe(f'<img class="img-inside-container" src="{obj.residente.get_foto_75x100_url()}"/>')

    get_foto.short_description = 'Foto'

    def get_info_principal(self, obj):
        out = '''
                <dl>
                    <dt class="hidden">Nome:</dt><dd class="negrito">{}</dd>'''.format(
            obj.residente.pessoa_fisica.nome_registro
        )
        if obj.residente.pessoa_fisica.nome_social:
            out += f'<dt>Nome Social:</dt><dd>{obj.residente.pessoa_fisica.nome_social}</dd>'
        out += '''<dt>CPF:</dt><dd>{}</dd>
                </dl>
            '''.format(obj.residente.pessoa_fisica.cpf)
        return mark_safe(out)

    get_info_principal.short_description = 'Residente'
    get_info_principal.admin_order_field = 'residente__pessoa_fisica__nome_registro'


admin.site.register(EstagioEletivo, EstagioEletivoAdmin)


class UnidadeAprendizagemTurmaAdmin(ModelAdminPlus):
    list_display = ('id', 'turma', 'unidade_aprendizagem', 'ano_letivo', 'periodo_letivo', 'get_outras_informacoes')
    list_filter = (
        CustomTabListFilter,
        'ano_letivo',
        'periodo_letivo',
        'turma',
        'turma__curso_campus',
    )
    list_display_icons = True
    list_per_page = 15
    export_to_xls = True
    list_xls_display = 'id', 'turma', 'unidade_aprendizagem', 'ano_letivo', 'periodo_letivo', 'get_nomes_preceptores'
    search_fields = ('id', 'unidade_aprendizagem__descricao', 'unidade_aprendizagem__ciclo')
    form = UnidadeAprendizagemTurmaForm

    show_count_on_tabs = True

    def get_outras_informacoes(self, obj):
        html = []

        # Preceptores
        # preceptores = obj.preceptordiario_set.all()
        # if preceptores:
        #     lista_preceptores = []
        #     for preceptor_diario in preceptores:
        #         nome = f'{preceptor_diario.preceptor.nome} ({preceptor_diario.tipo})'
        #         lista_preceptores.append(nome)
        #     html.append('<br/>')
        #     html.append('<strong>Preceptores:</strong> ')
        #     if len(lista_preceptores) > 1:
        #         html.append('<ul>')
        #         for preceptor in lista_preceptores:
        #             html.append(f'<li>{preceptor}</li>')
        #         html.append('<ul>')
        #     else:
        #         html.append(', '.join(lista_preceptores))
        #     html.append('<br/>')

        # if not preceptores:
        #     return '-'
        # return mark_safe(' '.join(html))

    get_outras_informacoes.short_description = 'Outras Informações'

    def get_queryset(self, request):
        return super().get_queryset(request, UnidadeAprendizagemTurma.objects).select_related('turma', 'ano_letivo')

    def correntes(self, request):
        url = '/admin/residencia/unidadeaprendizagemturma/'
        return HttpResponseRedirect(url)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls


admin.site.register(UnidadeAprendizagemTurma, UnidadeAprendizagemTurmaAdmin)


class ItemConfiguracaoAvaliacaoUnidadeAprendizagemInline(admin.TabularInline):
    formset = ItemConfiguracaoAvaliacaoUnidadeAprendizagemFormset
    model = ItemConfiguracaoAvaliacaoUnidadeAprendizagem
    extra = 0

    def has_delete_permission(self, request, obj=None):
        has_permission = super().has_delete_permission(request, obj=obj)
        return has_permission


class ConfiguracaoAvaliacaoUnidadeAprendizagemAdmin(ModelAdminPlus):
    list_display = ('forma_calculo', 'maior_nota', 'menor_nota', 'get_avaliacoes')
    list_display_icons = True
    export_to_xls = True
    form = ConfiguracaoAvaliacaoUnidadeAprendizagemForm

    inlines = [ItemConfiguracaoAvaliacaoUnidadeAprendizagemInline]

    fieldsets = (('', {'fields': (('forma_calculo', 'divisor'), ('menor_nota', 'maior_nota'), 'autopublicar', 'observacao')}),)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.unidadeaprendizagemturma and obj.unidadeaprendizagemturma.pode_ser_excluido():
            return True
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        result = super().change_view(request, object_id, form_url, extra_context)
        if not in_group(request.user, 'Administrador Acadêmico,Secretário Acadêmico'):
            obj = self.get_object(request, unquote(object_id))
            prof = request.user.get_profile().professor_set.all()
            if not prof or (obj and prof[0].pk not in obj.diario.professordiario_set.values_list('professor__id', flat=True).distinct()):
                raise PermissionDenied()
        return result

    @transaction.atomic
    def after_saving_model_and_related_inlines(self, obj):
        for matricula_unidade_aprendizagem_turma in obj.unidadeaprendizagemturma.matriculas_unidadeaprendizagemturma_unidade_aprendizagem_turma_set.all():
            matricula_unidade_aprendizagem_turma.criar_registros_notas_etapa(obj.etapa, ItemConfiguracaoAvaliacaoUnidadeAprendizagem.objects.filter(configuracao_avaliacao=obj))
        return obj

    def response_change(self, request, obj):
        obj = self.after_saving_model_and_related_inlines(obj)
        return super().response_change(request, obj)

    def get_avaliacoes(self, obj):
        if obj.itemconfiguracaoavaliacaounidadeaprendizagem_set.exists():
            lista = ['<ul>']
            for item in obj.itemconfiguracaoavaliacaounidadeaprendizagem_set.all():
                lista.append(f'<li>{item.get_tipo_display()}({item.sigla}): {item.nota_maxima}</li>')
            lista.append('</ul>')
        else:
            return mark_safe('-')

        return mark_safe(''.join(lista))

    get_avaliacoes.short_description = 'Avaliações'


admin.site.register(ConfiguracaoAvaliacaoUnidadeAprendizagem, ConfiguracaoAvaliacaoUnidadeAprendizagemAdmin)