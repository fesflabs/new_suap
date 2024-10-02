from datetime import datetime
from django import forms
from django.db.models.query_utils import Q
from django.urls import path
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from comum.models import UsuarioGrupoSetor
from comum.utils import somar_data, get_sigla_reitoria
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter, unquote, TabularInlinePlus
from djtools.contrib.admin.filters import DateRangeListFilter
from djtools.templatetags.filters import in_group
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from edu import perms
from edu.forms import (
    EstruturaCursoForm,
    CalendarioAcademicoForm,
    CursoCampusForm,
    TurmaForm,
    DiarioForm,
    DiretoriaForm,
    ComponenteForm,
    RegistroEmissaoDiplomaForm,
    HistoricoImportacaoForm,
    LogForm,
    MaterialAulaForm,
    AlunoForm,
    AbonoFaltasForm,
    EquivalenciaComponenteQAcademicoForm,
    MatrizForm,
    ConfiguracaoPedidoMatriculaForm,
    AulaCampoForm,
    ConfiguracaoSeguroForm,
    AtividadePoloForm,
    ConfiguracaoAvaliacaoForm,
    ItemConfiguracaoAvaliacaoFormset,
    SolicitacaoRelancamentoEtapaForm,
    ConfiguracaoCertificadoENEMForm,
    CadastrarSolicitacaoCertificadoENEMForm,
    RegistroEmissaoCertificadoENEMForm,
    ConvocacaoENADEForm,
    ColacaoGrauForm,
    ProfessorExternoForm,
    SolicitacaoProrrogacaoEtapaForm,
    EventoForm,
    DiarioEspecialForm,
    ConfiguracaoLivroForm,
    MinicursoForm,
    ConteudoMinicursoFormset,
    EditarTurmaMinicursoForm,
    ConfiguracaoCreditosEspeciaisForm,
    EstagioDocenteForm,
    RequerimentoForm,
    FormaIngressoForm,
    CertificadoDiplomaForm,
    PlanoEnsinoForm
)
from edu.models import (
    HistoricoImportacao,
    Log,
    MaterialAula,
    Modalidade,
    Convenio,
    NaturezaParticipacao,
    NivelEnsino,
    Turno,
    Diretoria,
    Componente,
    Matriz,
    Nucleo,
    EstruturaCurso,
    CalendarioAcademico,
    Turma,
    HorarioCampus,
    Diario,
    TipoProfessorDiario,
    Professor,
    HorarioAula,
    FormaIngresso,
    Aluno,
    SituacaoMatricula,
    SituacaoMatriculaPeriodo,
    CursoCampus,
    AreaCurso,
    ModeloDocumento,
    ConfiguracaoLivro,
    RegistroEmissaoDiploma,
    TipoComponente,
    EixoTecnologico,
    AbonoFaltas,
    LinhaPesquisa,
    EquivalenciaComponenteQAcademico,
    NucleoCentralEstruturante,
    Disciplina,
    Polo,
    MembroBanca,
    ConfiguracaoAtividadeComplementar,
    TipoAtividadeComplementar,
    RepresentacaoConceitual,
    ConfiguracaoPedidoMatricula,
    PedidoMatriculaDiario,
    ConfiguracaoSeguro,
    AulaCampo,
    RegistroLeitura,
    RegistroExclusao,
    MensagemEntrada,
    MensagemSaida,
    HorarioFuncionamentoPolo,
    AtividadePolo,
    SolicitacaoRelancamentoEtapa,
    ItemConfiguracaoAvaliacao,
    ConfiguracaoAvaliacao,
    ConfiguracaoCertificadoENEM,
    SolicitacaoCertificadoENEM,
    RegistroEmissaoCertificadoENEM,
    AreaCapes,
    Cidade,
    Cartorio,
    ConvocacaoENADE,
    JustificativaDispensaENADE,
    ColacaoGrau,
    VinculoProfessorEAD,
    Evento,
    SolicitacaoProrrogacaoEtapa,
    DiarioEspecial,
    AreaConcentracao,
    Programa,
    SolicitacaoUsuario,
    Minicurso,
    ConteudoMinicurso,
    TurmaMinicurso,
    ConfiguracaoCreditosEspeciais,
    AtividadeComplementar,
    EstagioDocente,
    OrgaoEmissorRg,
    Requerimento,
    TipoMedidaDisciplinar,
    TipoPremiacao,
    TipoAtividadeAprofundamento,
    ConfiguracaoAtividadeAprofundamento,
    Autorizacao,
    Reconhecimento,
    MatrizCurso,
    ProjetoFinal,
    AtividadeCurricularExtensao,
    Credenciamento,
    AssinaturaEletronica,
    SolicitacaoAssinaturaEletronica,
    CodigoAutenticadorSistec,
    AtaEletronica,
    AssinaturaDigital,
    CertificadoDiploma,
    Habilitacao,
    PlanoEnsino,
    ReferenciaBibliograficaBasica,
    ReferenciaBibliograficaComplementar,
    PlanoEstudo,
    ClassificacaoComplementarComponenteCurricular,
    CursoFormacaoSuperior,
    TipoAlunoArquivo,
    GrupoArquivoObrigatorio,
)
from edu.models.atividades_complementares import AtividadeAprofundamento
from edu.models.censos import QuestaoEducacenso, RegistroEducacenso

from edu.utils import SolicitacaoFilter
from edu.models.diarios import Trabalho
from rh.models import UnidadeOrganizacional


class SomenteDescricaoModelAdmin(ModelAdminPlus):
    list_display = ('descricao',)
    ordering = ('descricao',)
    search_fields = ('descricao',)
    list_display_icons = True
    export_to_xls = True


for cls in (
    NaturezaParticipacao,
    Convenio,
    Nucleo,
    TipoProfessorDiario,
    AreaCurso,
    EixoTecnologico,
    AreaCapes,
    NucleoCentralEstruturante,
    Disciplina,
    TipoAtividadeComplementar,
    VinculoProfessorEAD,
    AreaConcentracao,
    Programa,
    TipoMedidaDisciplinar,
    TipoPremiacao,
    ClassificacaoComplementarComponenteCurricular,
    CursoFormacaoSuperior,
    GrupoArquivoObrigatorio,
):
    admin.site.register(cls, SomenteDescricaoModelAdmin)


class TipoAlunoArquivoAdmin(ModelAdminPlus):
    list_display = ('nome',)
    ordering = ('nome',)
    search_fields = ('nome',)
    list_display_icons = True
    export_to_xls = True


admin.site.register(TipoAlunoArquivo, TipoAlunoArquivoAdmin)


class CredenciamentoAdmin(ModelAdminPlus):
    list_display = ('tipo', 'tipo_ato', 'numero_ato', 'data_ato', 'numero_publicacao', 'data_publicacao', 'veiculo_publicacao', 'secao_publicacao', 'pagina_publicacao')
    list_display_icons = True
    fieldsets = (
        ('Dados Gerais', {'fields': ('tipo',)}),
        ('Dados do Ato', {'fields': (('tipo_ato', 'numero_ato', 'data_ato'),)}),
        ('Dados da Publicação', {'fields': (('numero_publicacao', 'data_publicacao'), ('veiculo_publicacao', 'secao_publicacao'), 'pagina_publicacao')}),
    )


admin.site.register(Credenciamento, CredenciamentoAdmin)


class TrabalhoAdmin(ModelAdminPlus):
    list_display = ('diario', 'titulo', 'descricao')
    search_fields = ('diario__componente_curricular__componente__sigla', 'titulo', 'descricao')
    list_display_icons = True

    def get_queryset(self, request):
        return (
            Trabalho.objects.filter(diario__matriculadiario__matricula_periodo__aluno__matricula=request.user.username)
            .exclude(entregatrabalho__isnull=False)
            .exclude(data_limite_entrega__lt=datetime.today())
            .distinct()
        )


admin.site.register(Trabalho, TrabalhoAdmin)


class TipoAtividadeAprofundamentoAdmin(ModelAdminPlus):
    list_display = ('descricao',)
    ordering = ('descricao',)
    list_filter = ('modalidades',)
    search_fields = ('descricao',)
    list_display_icons = True
    export_to_xls = True


admin.site.register(TipoAtividadeAprofundamento, TipoAtividadeAprofundamentoAdmin)


class OrgaoEmissorRgAdmin(ModelAdminPlus):
    list_display = ('nome',)
    ordering = ('nome',)
    search_fields = ('nome',)
    list_display_icons = True
    export_to_xls = True


admin.site.register(OrgaoEmissorRg, OrgaoEmissorRgAdmin)


class LinhaPesquisaAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    ordering = ('descricao',)
    search_fields = ('descricao',)
    list_display_icons = True
    export_to_xls = True


admin.site.register(LinhaPesquisa, LinhaPesquisaAdmin)


class TurnoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    ordering = ('descricao',)
    search_fields = ('descricao',)
    list_display_icons = False
    export_to_xls = True


admin.site.register(Turno, TurnoAdmin)


class SituacaoMatriculaAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'ativo')
    ordering = ('descricao',)
    search_fields = ('descricao',)
    list_display_icons = False
    list_filter = ('ativo',)
    exclude = ('codigo_academico',)
    export_to_xls = True


admin.site.register(SituacaoMatricula, SituacaoMatriculaAdmin)


class SituacaoMatriculaPeriodoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    ordering = ('descricao',)
    search_fields = ('descricao',)
    list_display_icons = False
    exclude = ('codigo_academico',)
    export_to_xls = True


admin.site.register(SituacaoMatriculaPeriodo, SituacaoMatriculaPeriodoAdmin)


class HorarioAulaInline(admin.TabularInline):
    model = HorarioAula
    extra = 3

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'turno':
            kwargs['widget'] = forms.Select
        return super().formfield_for_dbfield(db_field, **kwargs)

    @property
    def media(self):
        _media = super().media
        _media._js.append('/static/djtools/jquery/widgets-core.js')
        _media._js.append('/static/djtools/jquery/jquery.maskedinput.js')
        _media._js.append('/static/edu/js/HorarioAulaInline.js')
        return _media


class HorarioCampusAdmin(ModelAdminPlus):
    list_display = ('descricao', 'uo', 'ativo', 'eh_padrao')
    list_display_icons = True
    export_to_xls = True

    ordering = ('descricao',)
    search_fields = ('descricao',)
    list_filter = ('uo', 'ativo', 'eh_padrao')
    inlines = [HorarioAulaInline]

    def get_queryset(self, request):
        return super().get_queryset(request, HorarioCampus.locals)

    def get_form(self, request, *args, **kwargs):
        form = super().get_form(request, *args, **kwargs)
        form.base_fields['uo'].queryset = UnidadeOrganizacional.objects.campi()
        return form


admin.site.register(HorarioCampus, HorarioCampusAdmin)


class DiretoriaAdmin(ModelAdminPlus):
    list_display = ('setor', 'campus', 'tipo')
    search_fields = ('setor__sigla',)
    form = DiretoriaForm
    fieldsets = DiretoriaForm.fieldsets
    list_filter = (CustomTabListFilter, 'setor__uo', 'tipo')
    list_display_icons = True
    export_to_xls = True

    def campus(self, obj):
        return obj.setor.uo and obj.setor.uo.nome.upper() or '-'

    def get_queryset(self, request):
        return super().get_queryset(request, Diretoria.locals)

    def get_tabs(self, request):
        return ['tab_sem_diretores', 'tab_sem_secretarios', 'tab_sem_coordenadores', 'tab_sem_pedagogos']

    def tab_sem_diretores(self, request, queryset):
        return queryset.sem_diretores()

    tab_sem_diretores.short_description = 'Sem Diretores'

    def tab_sem_secretarios(self, request, queryset):
        return queryset.sem_secretarios()

    tab_sem_secretarios.short_description = 'Sem Secretários'

    def tab_sem_coordenadores(self, request, queryset):
        return queryset.sem_coordenadores()

    tab_sem_coordenadores.short_description = 'Sem Coordenadores'

    def tab_sem_pedagogos(self, request, queryset):
        return queryset.sem_pedagogos()

    tab_sem_pedagogos.short_description = 'Sem Pedagogos'


admin.site.register(Diretoria, DiretoriaAdmin)


class CursoCampusAdmin(ModelAdminPlus):
    list_display = ('codigo', 'descricao', 'ativo', 'modalidade', 'natureza_participacao', 'get_diretoria', 'get_matrizes')
    list_filter = (CustomTabListFilter, 'ativo', 'ano_letivo', 'modalidade', 'diretoria__setor__uo', 'diretoria', 'assinatura_eletronica', 'assinatura_digital')

    list_display_icons = True
    exclude = ('codigo_academico',)
    search_fields = ('descricao', 'codigo', 'diretoria__setor__uo__sigla')
    list_per_page = 15
    export_to_xls = True
    list_xls_display = (
        'id',
        'descricao',
        'descricao_historico',
        'codigo_censup',
        'codigo_emec',
        'codigo_sistec',
        'codigo_educacenso',
        'ano_letivo',
        'periodo_letivo',
        'data_inicio',
        'data_fim',
        'ativo',
        'possui_aluno_cursando',
        'codigo',
        'natureza_participacao',
        'modalidade',
        'area',
        'eixo',
        'area_capes',
        'periodicidade',
        'exige_enade',
        'exige_colacao_grau',
        'emite_diploma',
        'area_concentracao',
        'programa',
        'diretoria',
        'extensao',
        'coordenador',
        'numero_portaria_coordenador',
        'titulo_certificado_masculino',
        'titulo_certificado_feminino',
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
            lista.append(f'<a href="/edu/matriz/{matriz.pk}/">{str(matriz.descricao)}</a>')
            lista.append('</li>')
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_matrizes.short_description = 'Matrizes'

    def get_diretoria(self, obj):
        if not obj.diretoria:
            if self.request.user.has_perm('edu.add_matriz'):
                return mark_safe(f'<a href="/edu/inserir_diretoria_curso/{obj.pk}/" class="btn popup">Definir Diretoria</a>')
            else:
                return '(Nenhum)'
        return mark_safe(str(obj.diretoria))

    get_diretoria.short_description = 'Diretoria'

    form = CursoCampusForm

    fieldsets = (
        (
            'Identificação',
            {
                'fields': (
                    ('descricao',),
                    ('descricao_historico',),
                    ('codigo_censup', 'codigo_emec'),
                    ('codigo_sistec', 'codigo_educacenso'),
                    ('ciencia_sem_fronteira', 'formacao_de_professores'),
                )
            },
        ),
        ('Dados da Criação', {'fields': ('ano_letivo', 'periodo_letivo', ('data_inicio', 'data_fim'), 'ativo')}),
        ('Coordenação', {'fields': ('coordenador', 'numero_portaria_coordenador')}),
        (
            'Dados Gerais',
            {
                'fields': (
                    'codigo',
                    'natureza_participacao',
                    'modalidade',
                    'plano_ensino',
                    'area',
                    'eixo',
                    'area_capes',
                    'periodicidade',
                    'diretoria',
                    ('exige_enade', 'exige_colacao_grau'),
                    ('emite_diploma', 'assinatura_eletronica', 'assinatura_digital'),
                    'area_concentracao',
                    'programa',
                    'fator_esforco_curso',
                )
            },
        ),
        ('Título do Certificado de Conclusão', {'fields': ('titulo_certificado_masculino', 'titulo_certificado_feminino')}),
    )

    def get_queryset(self, request):
        return CursoCampus.locals.exclude(ch_total__gt=0)

    def get_tabs(self, request):
        return ['tab_com_coordenadores', 'tab_sem_coordenadores', 'nao_vinculados_diretoria', 'tab_sob_minha_coordenacao', 'tab_integralizados']

    def tab_com_coordenadores(self, request, queryset):
        return queryset.com_coordenadores()

    tab_com_coordenadores.short_description = 'Com Coordenadores'

    def tab_sem_coordenadores(self, request, queryset):
        return queryset.sem_coordenadores()

    tab_sem_coordenadores.short_description = 'Sem Coordenadores'

    def nao_vinculados_diretoria(self, request, queryset):
        return queryset.nao_vinculados_diretoria()

    nao_vinculados_diretoria.short_description = 'Não-Vinculados à Diretoria'

    def tab_sob_minha_coordenacao(self, request, queryset):
        return queryset.sob_coordenacao_de(request.user.get_profile())

    tab_sob_minha_coordenacao.short_description = 'Sob Minha Coordenação'

    def tab_integralizados(self, request, queryset):
        return queryset.integralizados()

    tab_integralizados.short_description = 'Migrados'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        q = '?ativo__exact=1'
        return HttpResponseRedirect('/admin/edu/cursocampus/' + q)

    def response_add(self, request, obj):
        self.message_user(request, 'Curso cadastrado com sucesso. Por favor, vincule a(s) matriz(es) ao curso.')
        return HttpResponseRedirect(f'/edu/cursocampus/{obj.pk}/')


admin.site.register(CursoCampus, CursoCampusAdmin)


class ConteudoMiniCursoInline(admin.TabularInline):
    formset = ConteudoMinicursoFormset
    model = ConteudoMinicurso
    extra = 0


class MinicursoAdmin(ModelAdminPlus):
    list_display = ('get_codigo', 'descricao', 'ativo', 'ano_letivo', 'periodo_letivo', 'ch_total', 'ch_aula', 'diretoria')
    list_filter = ('ativo', 'ano_letivo', 'modalidade', 'diretoria__setor__uo', 'diretoria', 'extensao')
    search_fields = ('descricao', 'codigo')
    ordering = ('descricao',)
    export_to_xls = True
    list_per_page = 15
    list_display_icons = True

    form = MinicursoForm
    inlines = [ConteudoMiniCursoInline]
    fieldsets = MinicursoForm.fieldsets

    def get_queryset(self, request):
        return self.model.locals.all()


admin.site.register(Minicurso, MinicursoAdmin)


class TurmaMinicursoAdmin(ModelAdminPlus):
    form = EditarTurmaMinicursoForm

    def get_queryset(self, request):
        return self.model.objects.all()

    def response_add(self, request, obj):
        return httprr(f'/edu/minicurso/{obj.minicurso.pk}/', 'Operação realizada com sucesso.')

    def response_change(self, request, obj):
        return self.response_add(request, obj)


admin.site.register(TurmaMinicurso, TurmaMinicursoAdmin)


class TipoComponenteAdmin(ModelAdminPlus):
    list_display = ('descricao',)
    search_fields = ('descricao',)
    ordering = ('descricao',)
    export_to_xls = True
    list_per_page = 15
    list_display_icons = True


admin.site.register(TipoComponente, TipoComponenteAdmin)


class ComponenteAdmin(ModelAdminPlus):
    list_display = ('id', 'sigla', 'descricao', 'nivel_ensino', 'ch_hora_relogio', 'ch_hora_aula', 'ch_qtd_creditos', 'ativo', 'sigla_qacademico', 'observacao')
    list_filter = (CustomTabListFilter, 'ativo', 'tipo', 'nivel_ensino', 'matriz')
    list_filter_multiple_choices = 'tipo',
    search_fields = ('id', 'sigla', 'descricao', 'observacao', 'sigla_qacademico')
    list_display_icons = True
    export_to_xls = True
    list_per_page = 15
    form = ComponenteForm
    fieldsets = (
        ('Dados Gerais', {'fields': ('descricao', 'descricao_historico', 'abreviatura', 'tipo', 'diretoria', 'nivel_ensino', 'ativo')}),
        ('Carga Horária', {'fields': ('ch_hora_relogio', 'ch_hora_aula', 'ch_qtd_creditos')}),
        ('Dados Extras', {'fields': ('observacao',)}),
    )

    def get_tabs(self, request):
        return ['utilizados', 'nao_utilizados']

    def utilizados(self, request, queryset):
        qs_componente_curricular = queryset.filter(componentecurricular__id__isnull=False)
        qs_equivalente = queryset.filter(equivalenciacomponenteqacademico__id__isnull=False)
        qs_registro = queryset.filter(registrohistorico__id__isnull=False)
        return (qs_componente_curricular | qs_equivalente | qs_registro).distinct()

    utilizados.short_description = 'Utilizados'

    def nao_utilizados(self, request, queryset):
        qs_componente_curricular = queryset.filter(componentecurricular__id__isnull=False)
        qs_equivalente = queryset.filter(equivalenciacomponenteqacademico__id__isnull=False)
        qs_registro = queryset.filter(registrohistorico__id__isnull=False)
        qs_vinculados = (qs_componente_curricular | qs_equivalente | qs_registro).distinct()
        return queryset.exclude(id__in=qs_vinculados.values_list("id", flat=True))

    nao_utilizados.short_description = 'Não Utilizados'


admin.site.register(Componente, ComponenteAdmin)


class MatrizAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'nivel_ensino', 'ativo', 'get_diretorias')
    list_filter = (CustomTabListFilter, 'ano_criacao', 'ativo', 'nivel_ensino', 'estrutura', 'cursocampus__diretoria__setor__uo', 'cursocampus__diretoria')
    search_fields = ('id', 'descricao')
    list_display_icons = True
    list_per_page = 15
    export_to_xls = True
    form = MatrizForm
    show_count_on_tabs = True

    fieldsets = (
        (
            'Dados Gerais',
            {'fields': ('descricao', ('ano_criacao', 'periodo_criacao'), 'nivel_ensino', 'ativo', ('data_inicio', 'data_fim'), 'ppp', 'qtd_periodos_letivos', 'estrutura')},
        ),
        (
            'Carga Horária',
            {
                'fields': (
                    ('ch_componentes_obrigatorios', 'ch_componentes_optativos'),
                    ('ch_componentes_eletivos', 'ch_seminarios'),
                    ('ch_pratica_profissional', 'ch_componentes_tcc'),
                    ('ch_atividades_complementares', 'ch_atividades_aprofundamento'),
                    ('ch_atividades_extensao', 'ch_pratica_como_componente'),
                    ('ch_visita_tecnica',)
                )
            },
        ),
        ('Configurações Adicionais', {'fields': ('configuracao_atividade_academica', 'configuracao_atividade_aprofundamento', 'configuracao_creditos_especiais')}),
        ('Trabalho de Conclusão de Curso', {'fields': ('exige_tcc',)}),
        ('Estágio', {'fields': ('exige_estagio', 'ch_minima_estagio', 'periodo_minimo_estagio_obrigatorio', 'periodo_minimo_estagio_nao_obrigatorio'), }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ano_criacao')

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
        return HttpResponseRedirect(f'/edu/matriz/{obj.pk}/')

    def get_diretorias(self, obj):
        diretorias = obj.get_diretorias()
        if diretorias:
            lista = ['<ul>']
            for diretoria in diretorias:
                lista.append('<li>')
                lista.append(str(diretoria))
                lista.append('</li>')
            lista.append('</ul>')
            return mark_safe(''.join(lista))
        else:
            return mark_safe("-")

    get_diretorias.short_description = 'Diretorias'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        url = '/admin/edu/matriz/?&ativo__exact=1'
        return HttpResponseRedirect(url)


admin.site.register(Matriz, MatrizAdmin)


class RepresentacaoConceitualInline(admin.TabularInline):
    model = RepresentacaoConceitual
    extra = 3


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
            'Critérios de Apuração de Resultados por Período',
            {
                'fields': (
                    'tipo_avaliacao',
                    'limite_reprovacao',
                    'qtd_minima_disciplinas',
                    'numero_disciplinas_superior_periodo',
                    'qtd_max_periodos_subsequentes',
                    'numero_max_cancelamento_disciplina',
                    'proitec',
                )
            },
        ),
        (
            'Critérios de Avaliação por Disciplinas',
            {'fields': ('criterio_avaliacao', 'media_aprovacao_sem_prova_final', 'media_evitar_reprovacao_direta', 'media_aprovacao_avaliacao_final')},
        ),
        ('Critérios de Apuração de Frequência ', {'fields': (('percentual_frequencia', 'reprovacao_por_falta_disciplina'), 'limitar_ch_por_tipo_aula',)}),
        ('Índice de Rendimento Acadêmico (I.R.A)', {'fields': ('ira',)}),
        ('Fechamento de Período', {'fields': ('permite_fechamento_com_pendencia',)}),
        ('Configurações de Diário', {'fields': ('pode_entregar_etapa_sem_aula', 'pode_lancar_nota_fora_do_prazo')}),
        ('Critérios de Jubilamento', {'fields': ('qtd_periodos_conclusao', 'qtd_max_reprovacoes_periodo', 'qtd_max_reprovacoes_disciplina')}),
        ('Critérios de Trancamento', {'fields': ('qtd_trancamento_voluntario', 'requer_declaracao_para_cancelamento_matricula')}),
        (
            'Aproveitamento de Disciplinas',
            {
                'fields': (
                    ('quantidade_max_creditos_aproveitamento', 'percentual_max_aproveitamento'),
                    ('numero_max_certificacoes', 'media_certificacao_conhecimento'),
                    'formas_ingresso_ignoradas_aproveitamento',
                )
            },
        ),
        ('Plano de Estudo', {'fields': ('plano_estudo',)}),
        ('Critérios de Matrícula', {'fields': (('numero_min_alunos_diario', 'numero_max_alunos_especiais'))}),
    )


admin.site.register(EstruturaCurso, EstruturaCursoAdmin)


class CalendarioAcademicoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'tipo', 'uo', 'diretoria', 'ano_letivo', 'periodo_letivo', 'data_inicio', 'data_fim')
    list_filter = ('tipo', 'ano_letivo', 'periodo_letivo', 'uo', 'diretoria')
    list_display_icons = True
    search_fields = ('descricao', 'id')
    export_to_xls = True
    form = CalendarioAcademicoForm

    fieldsets = (
        ('Dados Gerais', {'fields': (('descricao',), ('uo', 'diretoria', 'tipo'), ('ano_letivo', 'periodo_letivo'))}),
        ('Espaço Pedagógico', {'fields': (('data_inicio_espaco_pedagogico', 'data_fim_espaco_pedagogico'),)}),
        (
            'Período Letivo',
            {
                'fields': (
                    ('data_inicio', 'data_fim'),
                    ('data_inicio_trancamento', 'data_fim_trancamento'),
                    ('data_inicio_certificacao', 'data_fim_certificacao'),
                    ('data_inicio_prova_final', 'data_fim_prova_final'),
                    'data_fechamento_periodo',
                )
            },
        ),
        ('Etapas', {'fields': ('qtd_etapas',)}),
        ('Primera Etapa', {'fields': (('data_inicio_etapa_1', 'data_fim_etapa_1'),)}),
        ('Segunda Etapa', {'fields': (('data_inicio_etapa_2', 'data_fim_etapa_2'),)}),
        ('Terceira Etapa', {'fields': (('data_inicio_etapa_3', 'data_fim_etapa_3'),)}),
        ('Quarta Etapa', {'fields': (('data_inicio_etapa_4', 'data_fim_etapa_4'),)}),
    )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        qs = self.get_queryset(request)
        if qs.exists():
            ano = qs.latest('ano_letivo__ano').ano_letivo.id
            url = f'/admin/edu/calendarioacademico/?ano_letivo__id__exact={ano}'
        else:
            url = '/admin/edu/calendarioacademico/'
        return HttpResponseRedirect(url)

    def get_queryset(self, request):
        return self.model.locals.all()


admin.site.register(CalendarioAcademico, CalendarioAcademicoAdmin)


class TurmaAdmin(ModelAdminPlus):
    list_display = ('codigo', 'descricao', 'sigla', 'ano_letivo', 'periodo_letivo', 'get_campus', 'get_qtd_diarios', 'get_qtd_alunos', 'polo')
    list_filter = (CustomTabListFilter, ('ano_letivo'), 'periodo_letivo', 'curso_campus__diretoria__setor__uo', 'curso_campus__diretoria', 'curso_campus', 'curso_campus__modalidade', 'pertence_ao_plano_retomada',)

    list_display_icons = True
    export_to_xls = True
    list_xls_display = 'id', 'codigo', 'descricao', 'sigla', 'ano_letivo', 'periodo_letivo', 'get_campus', 'get_diretoria', 'get_qtd_diarios', 'get_qtd_alunos', 'polo'
    list_per_page = 15
    search_fields = ('descricao', 'codigo', 'sigla', 'id')
    form = TurmaForm
    show_count_on_tabs = True

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if request.user.has_perm('edu.gerar_turmas'):
            items.append(dict(url='/edu/gerar_turmas/', label='Gerar Turmas'))
            items.append(dict(url='/edu/imprimir_horarios/', label='Imprimir Horários'))
        if request.user.groups.filter(name__in=['Administrador Acadêmico']).exists():
            items.append(
                dict(
                    label='Ações para o TimeTables',
                    subitems=[
                        dict(url='/static/edu/timetables/suap_edu.xml', label='Gerar o Arquivo de configuração do TimeTables'),
                        dict(url='/edu/exportar_xml_time_tables/', label='Exportar XML para o TimeTables'),
                        dict(url='/edu/importar_xml_time_tables/', label='Importar XML do TimeTables'),
                    ],
                )
            )
        return items

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        qs = self.get_queryset(request)
        if qs.exists():
            ano = qs.latest('ano_letivo__ano').ano_letivo.id
            url = f'/admin/edu/turma/?ano_letivo__id__exact={ano}'
            if in_group(request.user, 'Diretor Acadêmico') and hasattr(request.user.get_profile(), 'funcionario'):
                sigla_reitoria = get_sigla_reitoria()
                if request.user.get_relacionamento().setor.uo.sigla != sigla_reitoria:
                    url = f'{url}&curso_campus__diretoria__setor__uo__id__exact={request.user.get_profile().funcionario.setor.uo_id}'
        else:
            url = '/admin/edu/turma/'
        return HttpResponseRedirect(url)

    def get_campus(self, obj):
        return obj.curso_campus.diretoria.setor.uo
    get_campus.short_description = 'Campus'

    def get_diretoria(self, obj):
        return obj.curso_campus.diretoria
    get_diretoria.short_description = 'Diretoria'

    def get_qtd_diarios(self, obj):
        return obj.diario_set.order_by('componente_curricular__componente').count()

    get_qtd_diarios.short_description = 'Qtd de Diários'

    def get_qtd_alunos(self, obj):
        return obj.get_alunos_matriculados().count()

    get_qtd_alunos.short_description = 'Qtd de Alunos'

    def get_tabs(self, request):
        return ['tab_em_andamento', 'tab_pendentes']

    def tab_em_andamento(self, request, queryset):
        return queryset.em_andamento()

    tab_em_andamento.short_description = 'Em Andamento'

    def tab_pendentes(self, request, queryset):
        return queryset.pendentes()

    tab_pendentes.short_description = 'Notas Pendentes'

    def get_queryset(self, request):
        if request.user.groups.filter(name='Diretor Acadêmico').exists():
            manager = Turma.objects
        else:
            manager = Turma.locals
        return super().get_queryset(request, manager).select_related('curso_campus__diretoria__setor__uo')

    def delete_view(self, request, object_id, extra_context=None):
        try:
            turma = Turma.objects.get(pk=object_id)
        except Turma.DoesNotExist:
            msg = 'A turma escolhida não pode ser encontrada.'
            messages.error(request, msg)
            return httprr('/admin/edu/turma/')
        if not request.POST:
            return super().delete_view(request, object_id, extra_context)
        elif request.POST and (request.user.groups.filter(name__in=['edu Administrador']).exists() or turma.pode_ser_excluido()):
            return super().delete_view(request, object_id, extra_context)
        else:
            msg = 'Não é possível realizar a exclusão. Existem diários com alunos para esta turma.'
            messages.error(request, msg)
            return redirect('.')


admin.site.register(Turma, TurmaAdmin)


class DiarioAdmin(ModelAdminPlus):
    list_display = ('id', 'turma', 'componente_curricular', 'ano_letivo', 'periodo_letivo', 'get_outras_informacoes', 'get_datas_etapas')
    list_filter = (
        CustomTabListFilter,
        'ano_letivo',
        'periodo_letivo',
        'turma__curso_campus__diretoria__setor__uo',
        'turma__curso_campus__diretoria',
        'turno',
        'turma',
        'turma__curso_campus',
        'turma__polo',
        'segundo_semestre',
        'entregue_fisicamente',
        'turma__pertence_ao_plano_retomada'
    )
    list_display_icons = True
    list_per_page = 15
    export_to_xls = True
    list_xls_display = 'id', 'turma', 'componente_curricular', 'ano_letivo', 'periodo_letivo', 'get_nomes_professores', 'local_aula', 'get_horario_aulas'
    search_fields = ('id', 'componente_curricular__componente__descricao', 'componente_curricular__componente__sigla', 'professordiario__professor__vinculo__pessoa__nome')
    form = DiarioForm
    actions = ('alternar_primeiro_semestre', 'alternar_segundo_semestre', 'registrar_entrega_fisica', 'cancelar_entrega_fisica', 'habilitar_integracao_com_moodle', 'desabilitar_integracao_com_moodle')

    show_count_on_tabs = True

    def get_actions(self, request):
        if request.GET.get('tab') and request.GET.get('tab') == 'tab_semestrais_em_cursos_anuais':
            return dict()
        else:
            return super().get_actions(request)

    def habilitar_integracao_com_moodle(self, request, queryset):
        queryset.update(integracao_com_moodle=True)
        messages.success(request, 'Habilitação realizada com sucesso.')
    habilitar_integracao_com_moodle.short_description = "Habilitar Integração com Moodle"

    def desabilitar_integracao_com_moodle(self, request, queryset):
        queryset.update(integracao_com_moodle=False)
        messages.success(request, 'Desabilitação realizada com sucesso.')
    desabilitar_integracao_com_moodle.short_description = "Desabilitar Integração com Moodle"

    def alternar_primeiro_semestre(self, request, queryset):
        for diario in queryset.filter(componente_curricular__segundo_semestre=True):
            diario.segundo_semestre = False
            diario.save()
        messages.success(request, 'Diário alterado com sucesso.')

    alternar_primeiro_semestre.short_description = "Alternar para Primeiro Semestre Letivo"

    def alternar_segundo_semestre(self, request, queryset):
        for diario in queryset.filter(componente_curricular__segundo_semestre=False):
            diario.segundo_semestre = True
            diario.save()
        messages.success(request, 'Diário alterado com sucesso.')

    alternar_segundo_semestre.short_description = "Alternar para Segundo Semestre Letivo"

    def registrar_entrega_fisica(self, request, queryset):
        queryset.update(entregue_fisicamente=True)
        messages.success(request, 'Entrega física registrada com sucesso.')

    registrar_entrega_fisica.short_description = 'Registrar Entrega Física'

    def cancelar_entrega_fisica(self, request, queryset):
        queryset.update(entregue_fisicamente=False)
        messages.success(request, 'Entrega física cancelada com sucesso.')

    cancelar_entrega_fisica.short_description = 'Cancelar Entrega Física'

    def get_datas_etapas(self, obj):
        html = []

        if obj.componente_curricular.qtd_avaliacoes > 0:
            etapa1 = []
            if obj.get_inicio_etapa_1() is not None:
                etapa1.append(obj.get_inicio_etapa_1().strftime('%d/%m/%Y'))
            else:
                etapa1.append(' - ')
            etapa1.append(' a ')
            if obj.get_fim_etapa_1() is not None:
                etapa1.append(str(obj.get_fim_etapa_1().strftime('%d/%m/%Y')))
            else:
                etapa1.append(' - ')
            html.append('<strong title=\'')
            html.append(' '.join(etapa1))
            html.append('\'>Etapa ')
            if obj.segundo_semestre:
                html.append('3</strong><br/>')
            else:
                html.append('1</strong><br/>')

            if obj.componente_curricular.qtd_avaliacoes > 1:
                etapa2 = []
                if obj.get_inicio_etapa_2() is not None:
                    etapa2.append(obj.get_inicio_etapa_2().strftime('%d/%m/%Y'))
                else:
                    etapa2.append(' - ')
                etapa2.append(' a ')
                if obj.get_fim_etapa_2() is not None:
                    etapa2.append(str(obj.get_fim_etapa_2().strftime('%d/%m/%Y')))
                else:
                    etapa2.append(' - ')
                html.append('<strong title=\'')
                html.append(' '.join(etapa2))
                html.append('\'>Etapa </span>')
                if obj.segundo_semestre:
                    html.append('4</strong><br/>')
                else:
                    html.append('2</strong><br/>')

                if not obj.is_semestral() and obj.componente_curricular.qtd_avaliacoes > 2:
                    etapa3 = []
                    if obj.get_inicio_etapa_3() is not None:
                        etapa3.append(obj.get_inicio_etapa_3().strftime('%d/%m/%Y'))
                    else:
                        etapa3.append(' - ')
                    etapa3.append(' a ')
                    if obj.get_fim_etapa_3() is not None:
                        etapa3.append(str(obj.get_fim_etapa_3().strftime('%d/%m/%Y')))
                    else:
                        etapa3.append(' - ')
                    html.append('<strong title=\'')
                    html.append(' '.join(etapa3))
                    html.append('\'>Etapa 3</strong><br/>')

                    etapa4 = []
                    if obj.get_inicio_etapa_4() is not None:
                        etapa4.append(obj.get_inicio_etapa_4().strftime('%d/%m/%Y'))
                    else:
                        etapa4.append(' - ')
                    etapa4.append(' a ')
                    if obj.get_fim_etapa_4() is not None:
                        etapa4.append(str(obj.get_fim_etapa_4().strftime('%d/%m/%Y')))
                    else:
                        etapa4.append(' - ')
                    html.append('<strong title=\'')
                    html.append(' '.join(etapa4))
                    html.append('\'>Etapa 4</strong><br/>')

        etapa5 = []
        if obj.get_inicio_etapa_final() is not None:
            etapa5.append(obj.get_inicio_etapa_final().strftime('%d/%m/%Y'))
        else:
            etapa5.append(' - ')
        etapa5.append(' a ')
        if obj.get_fim_etapa_final() is not None:
            etapa5.append(str(obj.get_fim_etapa_final().strftime('%d/%m/%Y')))
        else:
            etapa5.append(' - ')
        html.append('<strong style=\'display:ruby; \' title=\'')
        html.append(' '.join(etapa5))
        html.append('\'>Etapa Final</strong><br />')

        return mark_safe(' '.join(html))

    get_datas_etapas.short_description = 'Etapas'

    def get_outras_informacoes(self, obj):
        html = []

        # Local de Aula
        if obj.local_aula:
            html.append('<strong>Local de Aula:</strong> ')
            html.append(str(obj.local_aula))
            html.append('<br/>')
            html.append('<br/>')

        # Horário de Aula
        if obj.get_horario_aulas():
            html.append('<strong>Horário de Aula:</strong> ')
            html.append(str(obj.get_horario_aulas()))
            html.append('<br/>')

        # Professores
        professores = obj.professordiario_set.all()
        if professores:
            lista_professores = []
            for professor_diario in professores:
                nome = f'{professor_diario.professor.vinculo.pessoa.nome} ({professor_diario.tipo})'
                lista_professores.append(nome)
            html.append('<br/>')
            html.append('<strong>Professores:</strong> ')
            if len(lista_professores) > 1:
                html.append('<ul>')
                for professor in lista_professores:
                    html.append(f'<li>{professor}</li>')
                html.append('<ul>')
            else:
                html.append(', '.join(lista_professores))
            html.append('<br/>')

        # Alunos
        if obj.local_aula:
            html.append('<br/>')
            html.append('<strong>Alunos:</strong> ')
            html.append(str(obj.get_quantidade_alunos_ativos()))

        if not obj.local_aula and not obj.get_horario_aulas() and not professores:
            return '-'
        return mark_safe(' '.join(html))

    get_outras_informacoes.short_description = 'Outras Informações'

    def get_queryset(self, request):
        if request.user.groups.filter(name='Diretor Acadêmico').exists():
            manager = Diario.objects
        else:
            manager = Diario.locals
        return super().get_queryset(request, manager).select_related('componente_curricular__componente__nivel_ensino', 'turma', 'ano_letivo')

    def get_tabs(self, request):
        return [
            'tab_sem_professores',
            'tab_sem_local_aula',
            'tab_sem_horario_aula',
            'tab_em_curso',
            'tab_pendentes',
            'tab_semestrais_em_cursos_anuais',
            'tab_entregues',
            'tab_nao_entregues',
        ]

    def tab_sem_professores(self, request, queryset):
        return queryset.sem_professores()

    tab_sem_professores.short_description = 'Sem Professores'

    def tab_sem_local_aula(self, request, queryset):
        return queryset.sem_local_aula()

    tab_sem_local_aula.short_description = 'Sem Local de Aula'

    def tab_sem_horario_aula(self, request, queryset):
        return queryset.sem_horario_aula()

    tab_sem_horario_aula.short_description = 'Sem Horário de Aula'

    def tab_em_curso(self, request, queryset):
        return queryset.em_curso()

    tab_em_curso.short_description = 'Em Andamento'

    def tab_pendentes(self, request, queryset):
        return queryset.pendentes()

    tab_pendentes.short_description = 'Notas Pendentes'

    def tab_semestrais_em_cursos_anuais(self, request, queryset):
        return queryset.semestrais_em_cursos_anuais()

    tab_semestrais_em_cursos_anuais.short_description = 'Semestrais em Cursos Anuais'

    def tab_entregues(self, request, queryset):
        return queryset.entregues()

    tab_entregues.short_description = 'Entregues'

    def tab_nao_entregues(self, request, queryset):
        return queryset.nao_entregues()

    tab_nao_entregues.short_description = 'Não Entregues'

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if request.user.groups.filter(name__in=['Administrador Acadêmico', 'Diretor Acadêmico', 'Coordenador de Curso', 'Secretário Acadêmico']).exists():
            items.append(
                dict(
                    label='Ações para o TimeTables',
                    subitems=[
                        dict(url='/static/edu/timetables/suap_edu.xml', label='Gerar o Arquivo de configuração do TimeTables'),
                        dict(url='/edu/exportar_xml_time_tables/', label='Exportar XML para o TimeTables'),
                        dict(url='/edu/importar_xml_time_tables/', label='Importar XML do TimeTables'),
                    ],
                )
            )
        return items

    def has_delete_permission(self, request, obj=None):
        if obj and obj.pode_ser_excluido() and perms.realizar_procedimentos_academicos(request.user, obj.turma.curso_campus):
            return True
        return False

    def correntes(self, request):
        url = '/admin/edu/diario/'
        if in_group(request.user, 'Diretor Acadêmico') and hasattr(request.user.get_profile(), 'funcionario'):
            sigla_reitoria = get_sigla_reitoria()
            if request.user.get_relacionamento().setor.uo.sigla != sigla_reitoria:
                url = f'{url}?turma__curso_campus__diretoria__setor__uo__id__exact={request.user.get_profile().funcionario.setor.uo_id}'
        return HttpResponseRedirect(url)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls


admin.site.register(Diario, DiarioAdmin)


class ProfessorAdmin(ModelAdminPlus):
    form = ProfessorExternoForm
    fieldsets = ProfessorExternoForm.fieldsets
    list_display_icons = True
    list_display = ('get_foto', 'get_dados_gerais', 'display_matricula', 'display_uo')
    list_per_page = 15
    search_fields = ('vinculo__pessoa__nome', 'vinculo__user__username')
    list_filter = (CustomTabListFilter, 'vinculo__setor__uo', 'vinculo__setor__diretoria', 'vinculo__pessoa__excluido')
    ordering = ('vinculo__pessoa__nome',)
    export_to_xls = True

    def get_queryset(self, request, manager=None, *args, **kwargs):
        return super().get_queryset(request, manager, *args, **kwargs).select_related('vinculo__pessoa')

    def has_add_permission(self, request):
        return False

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        items.append(dict(url='/edu/cadastrar_professor_nao_servidor/', label='Adicionar Professor Prestador de Serviço'))
        return items

    def get_tabs(self, request):
        return ['tab_servidor_docente', 'tab_servidor_tecnico', 'tab_nao_servidor']

    def tab_servidor_docente(self, request, queryset):
        return queryset.servidores_docentes()

    tab_servidor_docente.short_description = 'Docentes'

    def tab_servidor_tecnico(self, request, queryset):
        return queryset.servidores_tecnicos()

    tab_servidor_tecnico.short_description = 'Técnicos Administrativos'

    def tab_nao_servidor(self, request, queryset):
        return queryset.nao_servidores()

    tab_nao_servidor.short_description = 'Prestadores de Serviço'

    def display_uo(self, obj):
        return obj.get_uo()

    display_uo.short_description = 'Campus'

    def display_nome(self, obj):
        return obj.get_nome()

    display_nome.short_description = 'Nome'

    def response_change(self, request, obj):
        return httprr('..', 'Professor alterado com sucesso.')

    def get_dados_gerais(self, obj):
        show_telefones = ''
        if obj.vinculo.setor and obj.vinculo.setor.setortelefone_set.exists():
            show_telefones = '<dt>Telefones:</dt><dd>{}</dd>'.format(', '.join(obj.vinculo.setor.setortelefone_set.values_list('numero', flat=True)))
        obj_user = obj.vinculo.user
        show_email = obj_user and obj_user.email or ''
        show_cpf = ''
        if self.request.user.has_perm('edu.pode_ver_cpf_professor'):
            show_cpf = f'<dt>CPF:</dt><dd>{obj.vinculo.pessoa.get_cpf_ou_cnpj()}</dd>'
        if obj.vinculo.setor:
            show_setor = obj.vinculo.setor.__str__().format("/")
        else:
            show_setor = '-'
        if show_email:
            show_email = f'<a href="mailto:{show_email}">{show_email}</a>'
        else:
            show_email = '-'
        out = '''
        <dl>
            <dt>Nome:</dt><dd class="negrito">{nome}</dd>
            {show_cpf}
            <dt>Setor:</dt><dd>{setor}</dd>
            <dt>E-mail:</dt><dd>{show_email}</dd>
            {show_telefones}
        </dl>
        '''.format(
            nome=obj.vinculo.pessoa.nome, show_telefones=show_telefones, show_email=show_email, setor=show_setor, show_cpf=show_cpf
        )

        return mark_safe(out)

    get_dados_gerais.short_description = 'Dados Gerais'

    def display_matricula(self, obj):
        return obj.get_matricula()

    display_matricula.short_description = 'Matrícula'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Nome', 'Matrícula', 'Setor', 'E-mail', 'Telefone']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [idx + 1, obj.vinculo.pessoa.nome, obj.get_matricula(), obj.vinculo.setor.__str__().format('/'), obj.vinculo.user.email, ', '.join(obj.get_telefones())]
            rows.append(row)
        return rows

    def get_foto(self, obj):
        return mark_safe(f'<img class="img-inside-container" src="{obj.get_foto_75x100_url()}"/>')

    get_foto.short_description = 'Foto'


admin.site.register(Professor, ProfessorAdmin)


class AlunoAdmin(ModelAdminPlus):
    list_display = ('get_foto', 'get_info_principal', 'periodo_letivo', 'ano_letivo', 'get_pasta')
    list_filter = (CustomTabListFilter, 'ano_letivo', 'periodo_letivo', 'situacao', 'curso_campus__diretoria__setor__uo', 'curso_campus', 'polo')
    list_filter_autocomplete_form_filters = {
        'curso_campus': [('curso_campus__diretoria__setor__uo', 'diretoria__setor__uo')]
    }
    list_display_icons = True
    export_to_xls = True
    list_per_page = 15
    ordering = ('-id',)
    form = AlunoForm
    fieldsets = AlunoForm.fieldsets

    search_fields = ('pessoa_fisica__nome_registro', 'pessoa_fisica__search_fields_optimized', 'registroemissaodiploma__pasta', 'numero_pasta')

    def get_queryset(self, request):
        return super().get_queryset(request, Aluno.locals).exclude(turmaminicurso__gerar_matricula=False).select_related('ano_letivo', 'pessoa_fisica', 'situacao')

    def get_foto(self, obj):
        return mark_safe(f'<img class="img-inside-container" src="{obj.get_foto_75x100_url()}"/>')

    get_foto.short_description = 'Foto'

    def tab_suap(self, request, queryset):
        return queryset.filter(codigo_academico__isnull=True, matriz__id__isnull=False)

    tab_suap.short_description = 'Matriculados no Suap'

    def tab_q_academico(self, request, queryset):
        return queryset.filter(codigo_academico__isnull=False, matriz__id__isnull=True)

    tab_q_academico.short_description = 'Matriculados no Q-Acadêmico'

    def tab_integralizados(self, request, queryset):
        return queryset.filter(codigo_academico__isnull=False, matriz__id__isnull=False)

    tab_integralizados.short_description = 'Migrados'

    def get_tabs(self, request):
        return ['tab_suap', 'tab_q_academico', 'tab_integralizados']

    def correntes(self, request):
        url = '/admin/edu/aluno/'
        if not in_group(request.user, 'Administrador Acadêmico') and hasattr(request.user.get_profile(), 'funcionario'):
            sigla_reitoria = get_sigla_reitoria()
            if request.user.get_relacionamento().setor and request.user.get_relacionamento().setor.uo.sigla != sigla_reitoria:
                url = f'{url}?curso_campus__diretoria__setor__uo__id__exact={request.user.get_relacionamento().setor.uo_id}'
        return HttpResponseRedirect(url)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Nome', 'Matrícula', 'Curso', 'Campus', 'Polo', 'Situação', 'E-mail Acadêmico', 'E-mail Pessoal', 'Ano/Periodo Letivo']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [
                idx + 1,
                obj.get_nome_social_composto(),
                obj.matricula,
                obj.curso_campus,
                obj.curso_campus.diretoria.setor.uo,
                format(obj.polo),
                obj.situacao,
                format(obj.pessoa_fisica.email),
                obj.pessoa_fisica.email_secundario,
                f'{obj.ano_letivo.ano}.{obj.periodo_letivo:d}',
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
        out += '''<dt>Matrícula:</dt><dd>{matricula}</dd>
                    <dt>Curso:</dt><dd>{curso}</dd>
                    <dt>Situação:</dt><dd>{situacao}</dd>
                </dl>
            '''.format(
            matricula=obj.matricula, curso=obj.curso_campus, situacao=obj.situacao
        )
        return mark_safe(out)

    get_info_principal.short_description = 'Dados Principais'
    get_info_principal.admin_order_field = 'pessoa_fisica__nome'

    def get_pasta(self, obj):
        return obj.numero_pasta or '-'

    get_pasta.short_description = 'Nº Pasta'


admin.site.register(Aluno, AlunoAdmin)


class SolicitacaoUsuarioAdmin(ModelAdminPlus):
    list_display = ('id', 'get_solicitante', 'data_solicitacao', 'get_descricao', 'sub_instance_title', 'get_acoes')
    list_display_icons = True
    list_filter = (CustomTabListFilter, 'solicitante', 'avaliador', SolicitacaoFilter)
    search_fields = ('id', 'solicitante__first_name', 'solicitante__username', 'avaliador__first_name', 'avaliador__username')
    ordering = ('-data_avaliacao',)
    form = SolicitacaoRelancamentoEtapaForm
    export_to_xls = True

    actions = ('deferir', 'indeferir')

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.show_actions and request.user.has_perm('edu.change_solicitacaousuario'):
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
            url = '/edu/rejeitar_solicitacao/{}/'.format('_'.join(ids))
            return HttpResponseRedirect(url)

    indeferir.short_description = "Indeferir"

    def get_solicitante(self, obj):
        return mark_safe(obj.solicitante)

    get_solicitante.short_description = 'Solicitante'

    def get_action_bar(self, request):
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
                lista.append('<span class="status status-success">Deferida por {} em {}</span>'.format(obj.avaliador, obj.data_avaliacao.strftime("%d/%m/%y")))
            else:
                lista.append('<span class="status status-error">Indeferida por {} em {}</span>'.format(obj.avaliador, obj.data_avaliacao.strftime("%d/%m/%y")))
        else:
            lista.append('<span class="status status-pendente">Pendente</span>')
        return mark_safe(' '.join(lista))

    get_acoes.short_description = 'Status'

    def get_descricao(self, obj):
        filho = obj.sub_instance()
        if isinstance(filho, SolicitacaoRelancamentoEtapa) and filho.precisa_prorrogar_posse():
            return mark_safe(
                '<p>{}</p><span class="status status-error">Data de posse da etapa já foi ultrapassada, será preciso definir uma nova data limite para a posse.</span>'.format(
                    obj.descricao
                )
            )
        else:
            return obj.descricao

    get_descricao.short_description = 'Descrição'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Solicitante', 'Data da Solicitação', 'Descrição', 'Campus', 'Status', 'Avaliador']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            if obj.data_avaliacao:
                if obj.atendida:
                    atendimento = 'Deferida'
                else:
                    atendimento = 'Indeferida'
            else:
                atendimento = 'Não avaliada'
            row = [idx + 1, obj.solicitante, obj.data_solicitacao, obj.descricao, obj.uo, atendimento, obj.avaliador]
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
            manager = SolicitacaoUsuario.locals.exclude(solicitacaoacompanhamento__isnull=False)
        return super().get_queryset(request, manager).filter(solicitacaoprorrogacaoetapa__isnull=False) | super().get_queryset(request, manager).filter(solicitacaorelancamentoetapa__isnull=False)


admin.site.register(SolicitacaoUsuario, SolicitacaoUsuarioAdmin)


class SolicitacaoRelancamentoEtapaAdmin(ModelAdminPlus):
    list_display = ('id', 'get_solicitante', 'data_solicitacao', 'get_descricao', 'get_diretoria', 'motivo', 'get_acoes')
    list_display_icons = True
    list_filter = (
        CustomTabListFilter,
        'professor_diario__diario__ano_letivo',
        'professor_diario__diario__periodo_letivo',
        'professor_diario__diario__turma__curso_campus__diretoria',
    )
    search_fields = ('id', 'solicitante__first_name', 'solicitante__username', 'avaliador__first_name', 'avaliador__username')
    ordering = ('-data_avaliacao',)
    form = SolicitacaoRelancamentoEtapaForm
    export_to_xls = True

    actions = ('deferir', 'indeferir')

    def get_solicitante(self, obj):
        return mark_safe(obj.solicitante)

    get_solicitante.short_description = 'Solicitante'

    def get_action_bar(self, request):
        self.show_actions = request.GET.get('tab', None) == 'tab_pendentes'
        items = super().get_action_bar(request, True)
        return items

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.show_actions:
            return actions
        else:
            for key in list(actions.keys()):
                del actions[key]
            return actions

    def get_descricao(self, obj):
        filho = obj.sub_instance()
        if isinstance(filho, SolicitacaoRelancamentoEtapa) and filho.precisa_prorrogar_posse():
            return mark_safe(
                '<p>{}</p><span class="status status-error">Data de posse da etapa já foi ultrapassada, será preciso definir uma nova data limite para a posse.</span>'.format(
                    obj.descricao
                )
            )
        else:
            return obj.descricao

    get_descricao.short_description = 'Descrição'

    def get_diretoria(self, obj):
        return mark_safe(obj.get_diretoria())

    get_diretoria.short_description = 'Diretoria'

    def deferir(self, request, queryset):
        for solicitacao in queryset.filter(data_avaliacao__isnull=True):
            solicitacao.atender(request.user)
        messages.success(request, 'Solicitações deferidas com sucesso.')

    deferir.short_description = "Deferir"

    def indeferir(self, request, queryset):
        ids = [str(x) for x in queryset.filter(data_avaliacao__isnull=True).values_list('id', flat=True)]
        if ids:
            url = '/edu/rejeitar_solicitacao/{}/'.format('_'.join(ids))
            return HttpResponseRedirect(url)

    indeferir.short_description = "Indeferir"

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

    get_acoes.short_description = 'Situação'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Solicitante', 'Data da Solicitação', 'Descrição', 'Campus', 'Status', 'Avaliador']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            if obj.data_avaliacao:
                if obj.atendida:
                    atendimento = 'Deferida'
                else:
                    atendimento = 'Indeferida'
            else:
                atendimento = 'Não avaliada'
            row = [idx + 1, obj.solicitante, obj.data_solicitacao, obj.descricao, obj.uo, atendimento, obj.avaliador]
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
            manager = SolicitacaoRelancamentoEtapa.locals
        return super().get_queryset(request, manager)


admin.site.register(SolicitacaoRelancamentoEtapa, SolicitacaoRelancamentoEtapaAdmin)


class SolicitacaoProrrogacaoEtapaAdmin(SolicitacaoRelancamentoEtapaAdmin):
    list_filter = (
        CustomTabListFilter,
        'professor_diario__diario__ano_letivo',
        'professor_diario__diario__periodo_letivo',
        'professor_diario__diario__turma__curso_campus__diretoria',
    )
    form = SolicitacaoProrrogacaoEtapaForm

    def get_queryset(self, request):
        return super().get_queryset(request, SolicitacaoProrrogacaoEtapa.locals)


admin.site.register(SolicitacaoProrrogacaoEtapa, SolicitacaoProrrogacaoEtapaAdmin)


class ModeloDocumentoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'tipo', 'ativo')
    list_display_icons = True
    list_per_page = 15
    export_to_xls = True
    search_fields = ('id', 'tipo', 'descricao')


admin.site.register(ModeloDocumento, ModeloDocumentoAdmin)


class ConfiguracaoLivroAdmin(ModelAdminPlus):
    list_display = ('descricao', 'uo', 'numero_livro', 'numero_folha', 'numero_registro')
    list_filter = (CustomTabListFilter, 'uo', 'modalidades')
    search_fields = ('descricao',)
    list_display_icons = True
    export_to_xls = True
    list_per_page = 15
    form = ConfiguracaoLivroForm

    def get_tabs(self, request):
        return ['tab_suap', 'tab_qacademico', 'tab_sica']

    def tab_suap(self, request, queryset):
        return queryset.exclude(descricao='SICA').filter(codigo_qacademico__isnull=True)

    tab_suap.short_description = 'Suap'

    def tab_qacademico(self, request, queryset):
        return queryset.exclude(descricao='SICA').filter(codigo_qacademico__isnull=False)

    tab_qacademico.short_description = 'Q-Acadêmico'

    def tab_sica(self, request, queryset):
        return queryset.filter(descricao='SICA')

    tab_sica.short_description = 'SICA'


admin.site.register(ConfiguracaoLivro, ConfiguracaoLivroAdmin)


class RegistroEmissaoDiplomaAdmin(ModelAdminPlus):
    list_display = (
        'aluno',
        'get_curso',
        'get_detalhe',
        'via',
        'get_situacao',
    )
    list_xls_display = (
        'id',
        'aluno',
        'get_curso',
        'data_expedicao',
        'data_registro',
        'get_livro',
        'folha',
        'numero_registro',
        'pasta',
        'via',
        'emissor',
        'cancelado',
    )
    search_fields = ('aluno__pessoa_fisica__nome_registro', 'aluno__pessoa_fisica__nome_social', 'aluno__matricula', 'aluno__matriculaperiodo__turma__codigo', 'pasta')
    list_filter = (
        CustomTabListFilter,
        'sistema',
        'aluno__curso_campus__diretoria__setor__uo',
        'aluno__curso_campus__diretoria',
        'aluno__curso_campus__modalidade',
        'livro',
        'aluno__curso_campus',
        'aluno__matriz__estrutura',
        'situacao',
    )
    list_display_icons = True
    export_to_xls = True
    list_per_page = 15
    date_hierarchy = 'data_expedicao'
    form = RegistroEmissaoDiplomaForm
    actions = ['imprimir_registros', 'imprimir_diplomas', 'gerar_diplomas', 'gerar_historicos', 'confirmar_assinatura_fisica']
    fieldsets = (('Dados Gerais', {'fields': ('id', 'pasta', 'autenticacao_sistec')}),)

    def get_detalhe(self, obj):
        html = ['<dl>']
        html.append('<dt>Emissão:</dt><dd>{}</dd>'.format(obj.data_expedicao and obj.data_expedicao.strftime('%d/%m/%Y') or '-'))
        html.append(f'<dt>Emissor:</dt><dd>{obj.emissor}</dd>')
        html.append('<dt>Pasta:</dt><dd>{}</dd>'.format(obj.pasta or '-'))
        if obj.numero_registro:
            data_registro = obj.data_registro and obj.data_registro.strftime('%d/%m/%Y') or '-'
            html.append('<dt>Data do Registro:</dt><dd>{}</dd>'.format(data_registro))
            html.append(f'<dt>Número do Registro:</dt><dd>{obj.numero_registro}</dd>')
            html.append(f'<dt>Livro:</dt><dd>{obj.get_livro()}</dd>')
            html.append(f'<dt>Folha:</dt><dd>{obj.folha}</dd>')
        html.append('</dl>')
        return mark_safe(''.join(html))

    get_detalhe.short_description = 'Emissão e Registro'

    def get_tabs(self, request):
        return ['tab_assinados_manualmente', 'tab_assinados_eletronicamente', 'tab_assinados_digitalmente']

    def tab_assinados_manualmente(self, request, queryset):
        return queryset.exclude(configuracao_livro__descricao=ConfiguracaoLivro.NOME_LIVRO_ELETRONICO)
    tab_assinados_manualmente.short_description = 'Assinados Manualmente'

    def tab_assinados_eletronicamente(self, request, queryset):
        return queryset.filter(assinaturaeletronica__isnull=False)
    tab_assinados_eletronicamente.short_description = 'Assinados Eletrônicamente (FIC, Técnicos e Pós)'

    def tab_assinados_digitalmente(self, request, queryset):
        return queryset.filter(assinaturadigital__isnull=False)
    tab_assinados_digitalmente.short_description = 'Assinados Eletrônicamente (Graduação)'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            del actions['gerar_historicos']
        return actions

    def imprimir_registros(self, request, queryset):
        qs = queryset.values_list('id', flat=True)
        ids = []
        for pk in qs:
            ids.append(str(pk))
        url = '/edu/registrosemissaodiploma_pdf/{}/'.format('_'.join(ids))
        if qs.filter(numero_registro__isnull=True).exists():
            messages.error(request, 'Não é possível imprimir diplomas/certificados não registrados')
        else:
            return HttpResponseRedirect(url)

    imprimir_registros.short_description = 'Imprimir Registros Físicos'

    def imprimir_gerar_diplomas(self, request, queryset):
        qs = queryset.values_list('id', flat=True)
        ids = []
        for pk in qs:
            ids.append(str(pk))
        url = '/edu/imprimir_diploma/{}/'.format('_'.join(ids))
        if qs.filter(assinaturaeletronica__isnull=False).exists():
            messages.error(request, 'Não é possível gerar diplomas/certificados com assinatura eletrônica existente.')
        elif qs.filter(assinaturadigital__isnull=False).exists():
            messages.error(request, 'Não é possível gerar diplomas/certificados com assinatura digital existente.')
        elif qs.filter(numero_registro__isnull=True).exists():
            messages.error(request, 'Não é possível imprimir diplomas/certificados não registrados.')
        else:
            return HttpResponseRedirect(url)

    def imprimir_diplomas(self, request, queryset):
        return self.imprimir_gerar_diplomas(request, queryset)

    imprimir_diplomas.short_description = 'Imprimir Diplomas Físicos'

    def gerar_diplomas(self, request, queryset):
        return self.imprimir_gerar_diplomas(request, queryset)

    gerar_diplomas.short_description = 'Gerar Diplomas Eletrônicos'

    def confirmar_assinatura_fisica(self, request, queryset):
        queryset.filter(assinaturaeletronica__isnull=True, assinaturadigital__isnull=True).update(
            situacao=RegistroEmissaoDiploma.FINALIZADO
        )

    confirmar_assinatura_fisica.short_description = 'Confirmar Assinatura Física'

    def gerar_historicos(self, request, queryset):
        from edu.views import gerar_autenticacao_diploma_pdf, emitir_historico_final_eletronico_pdf
        contador = 0
        for obj in queryset:
            for assinatura_digital in obj.assinaturadigital_set.all():
                if assinatura_digital.registro_emissao_documento_historico_id is None:
                    registro_emissao_documento_historico = emitir_historico_final_eletronico_pdf(request, pk=str(obj.aluno.pk))
                    if isinstance(registro_emissao_documento_historico, HttpResponseRedirect):
                        continue
                    assinatura_digital.registro_emissao_documento_historico = registro_emissao_documento_historico
                    if assinatura_digital.registro_emissao_documento_diploma_id is None:
                        registro_emissao_documento_diploma = gerar_autenticacao_diploma_pdf(request, pk=obj.pk)
                        assinatura_digital.registro_emissao_documento_diploma = registro_emissao_documento_diploma
                    assinatura_digital.save()
                    contador += 1
        messages.success(request, f'{contador} histórico(s) gerado(s) com sucesso.')

    gerar_historicos.short_description = 'Gerar Históricos Eletrônicos'

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        return items

    def get_livro(self, obj):
        return obj.get_livro()

    get_livro.short_description = 'Livro'

    def get_curso(self, obj):
        html = [f'<p>{obj.aluno.curso_campus.descricao_historico}</p>']
        html.append('<dl>')
        html.append(f'<dt>Modalidade:</dt><dd>{obj.aluno.curso_campus.modalidade}</dd>')
        html.append(f'<dt>Campus:</dt><dd>{obj.aluno.curso_campus.diretoria.setor.uo}</dd>')
        html.append('</dl>')
        return mark_safe(''.join(html))

    get_curso.short_description = 'Curso'

    def get_situacao(self, obj):
        html = []
        html.append('<span class="status status-{}">{}</span>'.format(
            obj.get_status_situacao(), obj.get_situacao_display()
        )) if obj.situacao is not None else ''
        assinatura_eletronica = obj.aluno.curso_campus.assinatura_eletronica or obj.aluno.curso_campus.assinatura_digital
        if assinatura_eletronica and obj.situacao in (RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_DIPLOMA, RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_DOCUMENTACAO):
            html.append(f'<br><br><a href="/edu/consultar_status_assinaturas/{obj.pk}/" class="btn popup">Consultar Situação das Assinaturas</a>')
        return mark_safe(''.join(html))

    get_situacao.short_description = 'Situação'

    def get_queryset(self, request):
        return super().get_queryset(request, RegistroEmissaoDiploma.locals)

    def has_delete_permission(self, request, obj=None):
        if obj:
            return not obj.numero_formulario
        return True


admin.site.register(RegistroEmissaoDiploma, RegistroEmissaoDiplomaAdmin)


class HistoricoImportacaoAdmin(ModelAdminPlus):
    list_display = ('id', 'data', 'total_alunos_criados', 'total_alunos_atualizados', 'total_matriculas_periodo_criadas', 'total_matriculas_periodo_atualizadas')
    list_display_icons = True
    list_per_page = 15
    form = HistoricoImportacaoForm
    date_hierarchy = 'data'
    export_to_xls = True

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        items.append(dict(url='/edu/importar_alunos/', label='Importar Alunos'))
        return items


admin.site.register(HistoricoImportacao, HistoricoImportacaoAdmin)


class LogAdmin(ModelAdminPlus):
    list_display = ('id', 'user', 'dt', 'nome_modelo', 'ref', 'descricao')
    list_filter = ('nome_modelo', 'tipo')
    search_fields = ('descricao', 'ref', 'id')
    list_display_icons = True
    export_to_xls = True
    form = LogForm


admin.site.register(Log, LogAdmin)


class MaterialAulaAdmin(ModelAdminPlus):
    list_display = ('descricao', 'data_cadastro', 'professor')
    search_fields = ('descricao', 'professor__vinculo__user__username', 'professor__vinculo__pessoa__nome')
    date_hierarchy = 'data_cadastro'
    list_display_icons = True
    form = MaterialAulaForm
    fieldsets = MaterialAulaForm.fieldsets
    list_filter = (CustomTabListFilter,)
    actions = ['remover_selecionadas', 'clonar_selecionadas']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.GET.get('tab') == 'tab_meus_materiais' and 'remover_selecionadas' in actions:
            del actions['remover_selecionadas']
        if not request.GET.get('tab') == 'tab_compartilhados' and 'clonar_selecionadas' in actions:
            del actions['clonar_selecionadas']
        return actions

    def remover_selecionadas(self, request, queryset):
        for element in queryset:
            element.delete()
        messages.success(request, 'Ação realizada com sucesso.')

    remover_selecionadas.short_description = "Remover Materiais Selecionados"

    def clonar_selecionadas(self, request, queryset):
        for element in queryset:
            element.clone(request.user)
        messages.success(request, 'Ação realizada com sucesso.')

    clonar_selecionadas.short_description = "Clonar Materiais Selecionados"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(professor__vinculo__user=request.user) | qs.exclude(professor__vinculo__user=request.user).filter(publico=True)

    def get_tabs(self, request):
        return ['tab_meus_materiais', 'tab_compartilhados']

    def tab_meus_materiais(self, request, queryset):
        return queryset.filter(professor__vinculo__user=request.user)

    tab_meus_materiais.short_description = 'Meus Materiais'

    def tab_compartilhados(self, request, queryset):
        return queryset.exclude(professor__vinculo__user=request.user).filter(publico=True)

    tab_compartilhados.short_description = 'Materiais Públicos'

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if request.user.has_perm('edu.add_materialaula'):
            items.append(dict(url='/edu/adicionar_materiais_aula/', label='Adicionar Material de Aula', css_class='success'))

        professor = Professor.objects.filter(vinculo=request.user.get_vinculo()).first()
        if professor and professor.get_materiais_aula_outros_vinculos().exists():
            items.append(dict(url='/edu/importar_materiais_aula/', label='Importar Materiais de outros Vínculos'))
        return items


admin.site.register(MaterialAula, MaterialAulaAdmin)


class NivelEnsinoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    search_fields = ('descricao',)
    list_display_icons = False
    export_to_xls = True


admin.site.register(NivelEnsino, NivelEnsinoAdmin)


class ModalidadeAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'nivel_ensino')
    search_fields = ('descricao',)
    list_filter = ('nivel_ensino',)
    list_display_icons = False
    export_to_xls = True


admin.site.register(Modalidade, ModalidadeAdmin)


class FormaIngressoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'ativo')
    search_fields = ('descricao',)
    list_filter = ('ativo', 'classificacao_censup')
    list_display_icons = True
    export_to_xls = True
    form = FormaIngressoForm

    fieldsets = (
        ('Dados Gerais', {'fields': ('descricao', 'ativo')}),
        ('Classificação', {'fields': (('classificacao_censup', 'classificacao_educacenso'),)}),
        (
            'Programa de Vagas',
            {
                'fields': (
                    ('programa_vaga_etinico', 'racas'),
                    ('programa_vaga_pessoa_deficiencia', 'programa_vaga_escola_publica'),
                    ('programa_vaga_social', 'programa_vaga_outros'),
                )
            },
        ),
    )


admin.site.register(FormaIngresso, FormaIngressoAdmin)


class EquivalenciaComponenteQAcademicoAdmin(ModelAdminPlus):
    list_display = ('sigla', 'descricao', 'carga_horaria', 'componente')
    list_filter = (CustomTabListFilter,)
    search_fields = ('descricao', 'componente__sigla', 'sigla')
    form = EquivalenciaComponenteQAcademicoForm
    list_per_page = 15
    export_to_xls = True
    list_display_icons = True

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        return items

    def get_tabs(self, request):
        return ['tab_vinculados', 'tab_nao_vinculados']

    def tab_vinculados(self, request, queryset):
        return queryset.exclude(componente__isnull=True)

    tab_vinculados.short_description = 'Vinculados'

    def tab_nao_vinculados(self, request, queryset):
        return queryset.filter(componente__isnull=True)

    tab_nao_vinculados.short_description = 'Não-Vinculados'


admin.site.register(EquivalenciaComponenteQAcademico, EquivalenciaComponenteQAcademicoAdmin)


class AbonoFaltasAdmin(ModelAdminPlus):
    list_filter = ('aluno__curso_campus__diretoria__setor__uo', 'aluno__curso_campus__diretoria', ('data_inicio', DateRangeListFilter))
    list_display = ('aluno', 'responsavel_abono', 'data_inicio', 'data_fim')
    list_display_icons = True
    search_fields = ('aluno__pessoa_fisica__nome_registro', 'aluno__pessoa_fisica__nome_social', 'aluno__matricula')
    ordering = ('aluno__pessoa_fisica__nome',)
    form = AbonoFaltasForm
    date_hierarchy = 'data_inicio'
    export_to_xls = True

    def get_action_bar(self, request):
        items = [
            dict(url='/admin/edu/abonofaltas/add/', label='Adicionar Justificativa de Falta', css_class='success'),
            dict(url='/edu/abonar_faltas_lote/', label='Adicionar em Lote', css_class='success'),
        ]
        items.extend(super(self.__class__, self).get_action_bar(request, True))
        return items

    def get_queryset(self, request):
        return AbonoFaltas.locals

    def get_form(self, request, *args, **kwargs):
        form = super().get_form(request, *args, **kwargs)

        # Initial values
        form.base_fields['responsavel_abono'].initial = request.user
        return form


admin.site.register(AbonoFaltas, AbonoFaltasAdmin)


class HorarioFuncionamentoPoloInline(admin.TabularInline):
    model = HorarioFuncionamentoPolo
    extra = 3


class PoloAdmin(ModelAdminPlus):
    list_filter = ('sigla', 'diretoria')
    list_display = ('descricao', 'sigla', 'cidade', 'codigo_censup')
    list_display_icons = True
    search_fields = ('descricao', 'sigla')
    ordering = ('descricao',)
    exclude = ('codigo_academico',)
    inlines = [HorarioFuncionamentoPoloInline]

    fieldsets = (
        (
            'Informações Gerais',
            {'fields': ('descricao', 'sigla', 'cidade', 'codigo_censup', 'estrutura_disponivel', 'do_municipio', 'diretoria', 'telefone_principal', 'telefone_secundario')},
        ),
        ('Endereço', {'fields': (('logradouro', 'numero'), 'complemento', 'bairro', 'cep')}),
        ('Assistência Estudantil', {'fields': ('campus_atendimento',)}),
    )

    def get_inline_instances(self, request, obj=None):
        instances = super().get_inline_instances(request, obj=None)
        if not request.user.is_superuser:
            return []
        return instances

    def get_queryset(self, request):
        return super().get_queryset(request, Polo.locals)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj=obj)
        if not request.user.is_superuser:
            if not request.user.groups.filter(name='Administrador Acadêmico').exists():
                fieldsets[0][1]['fields'] = fieldsets[0][1]['fields'][1:]
        return fieldsets


admin.site.register(Polo, PoloAdmin)


class HabilitacaoAdmin(ModelAdminPlus):
    list_display = ('descricao',)
    list_display_icons = True
    search_fields = ('descricao',)
    ordering = ('descricao',)

    fieldsets = (
        ('Dados Gerais', {'fields': ('descricao',)}),
    )


admin.site.register(Habilitacao, HabilitacaoAdmin)


class MembroBancaAdmin(ModelAdminPlus):
    list_filter = ('instituicao',)
    list_display = ('nome', 'email', 'instituicao', 'formacao')
    list_display_icons = True
    search_fields = ('nome', 'instituicao')
    ordering = ('nome',)


admin.site.register(MembroBanca, MembroBancaAdmin)


class ConfiguracaoAtividadeComplementarAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    list_filter = (CustomTabListFilter,)
    list_display_icons = True
    search_fields = ('descricao',)
    ordering = ('-id',)

    def get_tabs(self, request):
        return ['tab_vinculadas', 'tab_nao_vinculadas']

    def tab_vinculadas(self, request, queryset):
        return queryset.filter(matriz__isnull=False).distinct()

    tab_vinculadas.short_description = 'Vinculadas'

    def tab_nao_vinculadas(self, request, queryset):
        return queryset.filter(matriz__isnull=True).distinct()

    tab_nao_vinculadas.short_description = 'Não Vinculadas'

    def response_add(self, request, obj):
        return httprr(f'/edu/configuracaoatividadecomplementar/{obj.pk}/', 'Configuração cadastrada com sucesso. Adicione os tipos de atividades complementares.')


admin.site.register(ConfiguracaoAtividadeComplementar, ConfiguracaoAtividadeComplementarAdmin)


class ConfiguracaoAtividadeAprofundamentoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    list_filter = (CustomTabListFilter,)
    list_display_icons = True
    search_fields = ('descricao',)
    ordering = ('-id',)

    def get_tabs(self, request):
        return ['tab_vinculadas', 'tab_nao_vinculadas']

    def tab_vinculadas(self, request, queryset):
        return queryset.filter(matriz__isnull=False).distinct()

    tab_vinculadas.short_description = 'Vinculadas'

    def tab_nao_vinculadas(self, request, queryset):
        return queryset.filter(matriz__isnull=True).distinct()

    tab_nao_vinculadas.short_description = 'Não Vinculadas'

    def response_add(self, request, obj):
        return httprr(f'/edu/configuracaoatividadeaprofundamento/{obj.pk}/', 'Configuração cadastrada com sucesso. Adicione os tipos de atividades.')


admin.site.register(ConfiguracaoAtividadeAprofundamento, ConfiguracaoAtividadeAprofundamentoAdmin)


class ConfiguracaoPedidoMatriculaAdmin(ModelAdminPlus):
    list_filter = (CustomTabListFilter, 'ano_letivo', 'periodo_letivo', 'diretorias')
    list_display = ('id', 'ano_letivo', 'periodo_letivo', 'descricao', 'get_status', 'get_diretorias', 'data_inicio', 'data_fim')
    list_display_icons = True
    search_fields = ('descricao',)
    ordering = ('-id',)
    form = ConfiguracaoPedidoMatriculaForm

    fieldsets = (
        ('Informações Gerais', {'fields': ('descricao', ('ano_letivo', 'periodo_letivo'), 'diretorias')}),
        ('Período de Matrícula', {'fields': (('data_inicio', 'data_fim'),)}),
        ('Configuração', {'fields': ('impedir_troca_turma', 'restringir_por_curso', 'requer_atualizacao_dados', 'requer_atualizacao_caracterizacao', 'permite_cancelamento_matricula_diario')}),
    )

    def get_status(self, obj):
        tokens = obj.get_status()
        return mark_safe(f'<span class="status {tokens[1]}">{tokens[0]}</span></td>')

    get_status.short_description = 'Situação'

    def get_tabs(self, request):
        return ['tab_aguardando_inicio_matricula', 'tab_aguardando_matriculas', 'tab_aguardando_processamento', 'tab_finalizados', 'tab_cancelados']

    def get_queryset(self, request):
        return super().get_queryset(request, ConfiguracaoPedidoMatricula.locals).distinct()

    def tab_aguardando_inicio_matricula(self, request, queryset):
        return queryset.exclude(data_inicio__lte=datetime.today()).exclude(pedidomatricula__pedidomatriculadiario__motivo=PedidoMatriculaDiario.MOTIVO_CANCELADO).distinct()

    tab_aguardando_inicio_matricula.short_description = 'Agendadas'

    def tab_aguardando_matriculas(self, request, queryset):
        return (
            queryset.filter(data_inicio__lt=somar_data(datetime.today(), 1), data_fim__gte=datetime.today())
            .exclude(pedidomatricula__pedidomatriculadiario__motivo=PedidoMatriculaDiario.MOTIVO_CANCELADO)
        )

    tab_aguardando_matriculas.short_description = 'Em Andamento'

    def tab_aguardando_processamento(self, request, queryset):
        return (
            queryset.filter(data_fim__lt=datetime.today())
            .exclude(pedidomatricula__pedidomatriculadiario__data_processamento__isnull=False)
            .exclude(pedidomatricula__pedidomatriculadiario__motivo=PedidoMatriculaDiario.MOTIVO_CANCELADO)
        )

    tab_aguardando_processamento.short_description = 'Aguardando Processamento'

    def tab_finalizados(self, request, queryset):
        return (
            queryset.filter(data_fim__lt=datetime.today(), pedidomatricula__pedidomatriculadiario__data_processamento__isnull=False)
            .exclude(pedidomatricula__pedidomatriculadiario__motivo=PedidoMatriculaDiario.MOTIVO_CANCELADO)
        )

    tab_finalizados.short_description = 'Processadas'

    def tab_cancelados(self, request, queryset):
        return queryset.filter(pedidomatricula__pedidomatriculadiario__motivo=PedidoMatriculaDiario.MOTIVO_CANCELADO)

    tab_cancelados.short_description = 'Cancelados'

    def delete_view(self, request, object_id, extra_context=None):
        configuracao_pedido_matricula = ConfiguracaoPedidoMatricula.objects.get(pk=object_id)
        if not request.POST:
            return super().delete_view(request, object_id, extra_context)
        elif request.POST and configuracao_pedido_matricula.pode_ser_excluido():
            configuracao_pedido_matricula.enviar_emails_alunos()
            return super().delete_view(request, object_id, extra_context)
        else:
            msg = 'Não é possível realizar a exclusão. Existem pedidos de matrícula já processados para esta configuração.'
            messages.error(request, msg)
            return redirect('.')

    def response_add(self, request, obj):
        return httprr(f'/edu/configuracao_pedido_matricula/{obj.pk}/', 'Cadastro realizado com sucesso. Adicione os cursos para os quais os pedidos serão realizados.')

    def get_diretorias(self, obj):
        if obj.diretorias.all().exists():
            lista = ["<ul>"]
            for diretoria in obj.diretorias.all():
                lista.append(f'<li>{diretoria}</li>')
            lista.append('</ul>')
            return mark_safe("".join(lista))
        else:
            return mark_safe('-')

    get_diretorias.short_description = 'Diretorias'


admin.site.register(ConfiguracaoPedidoMatricula, ConfiguracaoPedidoMatriculaAdmin)


class PedidoMatriculaDiarioAdmin(ModelAdminPlus):
    list_filter = (
        'id',
        'pedido_matricula__configuracao_pedido_matricula__ano_letivo',
        'pedido_matricula__configuracao_pedido_matricula__periodo_letivo',
        'deferido',
        'pedido_matricula__matricula_periodo__aluno__curso_campus',
    )
    list_display = ('get_aluno', 'get_curso', 'get_ano_periodo', 'get_turma', 'diario', 'deferido', 'data_processamento')
    search_fields = ('pedido_matricula__matricula_periodo__aluno__matricula', 'pedido_matricula__matricula_periodo__aluno__pessoa_fisica__nome')
    ordering = ('-pedido_matricula__matricula_periodo__aluno__pessoa_fisica__nome',)
    list_display_icons = True

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        return items

    def get_aluno(self, obj):
        return obj.pedido_matricula.matricula_periodo.aluno

    get_aluno.short_description = 'Aluno'

    def get_turma(self, obj):
        return obj.pedido_matricula.turma

    get_turma.short_description = 'Turma'

    def get_ano_periodo(self, obj):
        return f"{obj.pedido_matricula.configuracao_pedido_matricula.ano_letivo}/{obj.pedido_matricula.configuracao_pedido_matricula.periodo_letivo}"

    get_ano_periodo.short_description = 'Ano/Período'

    def get_curso(self, obj):
        return obj.pedido_matricula.matricula_periodo.aluno.curso_campus.descricao_historico

    get_curso.short_description = 'Curso'


admin.site.register(PedidoMatriculaDiario, PedidoMatriculaDiarioAdmin)


class ConfiguracaoSeguroAdmin(ModelAdminPlus):
    list_display = ('seguradora', 'data_inicio_contrato', 'data_fim_contrato', 'valor_contrato', 'valor_repasse_pessoa')
    search_fields = ('seguradora__nome',)
    ordering = ('id',)
    list_display_icons = True
    form = ConfiguracaoSeguroForm

    fieldsets = (
        ('Dados Gerais', {'fields': (('seguradora',), ('data_inicio_contrato', 'data_fim_contrato'), ('valor_contrato',), ('valor_repasse_pessoa',), 'fiscais', 'ativa')}),
        ('Dados para Envio da Planilha', {'fields': ('email_disparo_planilha',)}),
    )


admin.site.register(ConfiguracaoSeguro, ConfiguracaoSeguroAdmin)


class AulaCampoAdmin(ModelAdminPlus):
    list_filter = (CustomTabListFilter, 'uo', 'configuracao_seguro', 'situacao')
    list_display = (
        'id',
        'uo',
        'descricao',
        'finalidade',
        'data_partida',
        'data_chegada',
        'roteiro',
        'situacao',
        'get_qtd_servidores_participantes',
        'get_qtd_alunos_participantes',
    )
    search_fields = ('descricao', 'roteiro')
    ordering = ('data_partida',)
    list_display_icons = True
    form = AulaCampoForm
    date_hierarchy = 'data_partida'

    def get_tabs(self, request):
        return ['tab_com_alunos', 'tab_sem_alunos']

    def tab_sem_alunos(self, request, queryset):
        return queryset.filter(alunos__isnull=True)

    tab_sem_alunos.short_description = 'Sem Alunos Participantes'

    def tab_com_alunos(self, request, queryset):
        return queryset.exclude(alunos__isnull=True)

    tab_com_alunos.short_description = 'Com Alunos Participantes'

    def get_qtd_servidores_participantes(self, obj):
        return obj.responsaveis.count()

    get_qtd_servidores_participantes.short_description = 'Qtd. de Servidores Participantes'

    def get_qtd_alunos_participantes(self, obj):
        return obj.alunos.count()

    get_qtd_alunos_participantes.short_description = 'Qtd. de Alunos Participantes'

    fieldsets = (
        ('Dados Gerais', {'fields': (('configuracao_seguro',), ('uo',), ('descricao',), ('finalidade',), ('roteiro',), ('data_partida', 'data_chegada'))}),
        ('Participantes', {'fields': ('responsaveis', 'arquivo')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request, AulaCampo.locals)


admin.site.register(AulaCampo, AulaCampoAdmin)


class MensagemEntradaAdmin(ModelAdminPlus):
    list_display = ('get_icone', 'remetente', 'assunto', 'data_envio')
    search_fields = ('assunto', 'remetente__pessoafisica__nome', 'remetente__username')
    ordering = ('-data_envio',)
    list_display_icons = False
    list_filter = (CustomTabListFilter, 'via_suap', 'via_email')
    actions = ('marcar_como_lida', 'enviar_para_lixeira')
    date_hierarchy = 'data_envio'
    show_tab_any_data = False

    def marcar_como_lida(self, request, queryset):
        for mensagem in queryset.exclude(registroleitura__isnull=False, registroexclusao__destinatario__pk=request.user.pk):
            RegistroLeitura.objects.create(mensagem=mensagem, destinatario=request.user, data_leitura=datetime.today())
        RegistroExclusao.objects.filter(mensagem__in=queryset, destinatario=request.user).delete()

    marcar_como_lida.short_description = "Marcar como lida"

    def enviar_para_lixeira(self, request, queryset):
        for mensagem in queryset.exclude(registroexclusao__isnull=False, registroexclusao__destinatario__pk=request.user.pk):
            RegistroExclusao.objects.create(mensagem=mensagem, destinatario=request.user, data_exclusao=datetime.today())

    enviar_para_lixeira.short_description = "Enviar para lixeira"

    def get_icone(self, obj):
        return mark_safe(icon('view', obj.get_absolute_url()))

    get_icone.short_description = 'Ações'

    def get_action_bar(self, request):
        return super(self.__class__, self).get_action_bar(request, True)

    def get_tabs(self, request):
        return ['tab_nao_lidas', 'tab_lidas', 'tab_todas', 'tab_lixeira']

    def tab_todas(self, request, queryset):
        return queryset.exclude(registroexclusao__destinatario__pk=request.user.pk)

    tab_todas.short_description = 'Todas'

    def tab_nao_lidas(self, request, queryset):
        return (
            queryset.exclude(remetente=request.user)
            .exclude(registroexclusao__destinatario__pk=request.user.pk)
            .exclude(registroleitura__destinatario__pk=request.user.pk)
            .distinct()
        )

    tab_nao_lidas.short_description = 'Não Lidas'

    def tab_lidas(self, request, queryset):
        return (
            queryset.exclude(remetente=request.user)
            .exclude(registroexclusao__destinatario__pk=request.user.pk)
            .filter(registroleitura__destinatario__pk=request.user.pk)
            .distinct()
        )

    tab_lidas.short_description = 'Lidas'

    def tab_lixeira(self, request, queryset):
        return queryset.exclude(remetente=request.user).filter(registroexclusao__destinatario__pk=request.user.pk)

    tab_lixeira.short_description = 'Lixeira'

    def get_queryset(self, request):
        return super().get_queryset(request).filter(destinatarios=request.user).distinct()


admin.site.register(MensagemEntrada, MensagemEntradaAdmin)


class MensagemSaidaAdmin(ModelAdminPlus):
    list_display = ('get_icone', 'remetente', 'assunto', 'data_envio', 'get_qtd_destinatarios', 'get_qtd_leitura')
    search_fields = ('assunto', 'remetente__pessoafisica__nome', 'remetente__username')
    ordering = ('-data_envio',)
    list_display_icons = False
    list_filter = ('via_suap', 'via_email')
    date_hierarchy = 'data_envio'

    def get_qtd_destinatarios(self, obj):
        return mark_safe(obj.get_quantidade_destinatarios())

    get_qtd_destinatarios.short_description = 'Quantidade de Destinatários'

    def get_qtd_leitura(self, obj):
        return mark_safe(obj.get_quantidade_leitura())

    get_qtd_leitura.short_description = 'Quantidade de Leitura'

    def get_icone(self, obj):
        return mark_safe(icon('view', obj.get_absolute_url()))

    get_icone.short_description = 'Ações'

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if request.user.has_perm('edu.add_mensagem'):
            items.append(dict(url='/edu/enviar_mensagem/', label='Nova Mensagem'))
        return items

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.groups.filter(name__in=['Administrador Acadêmico']).exists():
            return qs.filter(remetente=request.user)
        return qs.distinct()


admin.site.register(MensagemSaida, MensagemSaidaAdmin)


class AtividadePoloAdmin(ModelAdminPlus):
    list_filter = ('polo', 'confirmada')
    list_display = ('nome', 'descricao', 'data_inicio', 'data_fim', 'polo', 'user', 'confirmada')
    search_fields = ('nome', 'descricao')
    ordering = ('data_inicio', 'data_fim')
    list_display_icons = True
    date_hierarchy = 'data_inicio'
    model = AtividadePolo
    form = AtividadePoloForm

    actions = ('confirmar',)

    def confirmar(self, request, queryset):
        queryset.update(confirmada=True)

    def get_queryset(self, request):
        return super().get_queryset(request, AtividadePolo.locals)


admin.site.register(AtividadePolo, AtividadePoloAdmin)


class ItemConfiguracaoAvaliacaoInline(admin.TabularInline):
    formset = ItemConfiguracaoAvaliacaoFormset
    model = ItemConfiguracaoAvaliacao
    extra = 0

    def has_delete_permission(self, request, obj=None):
        has_permission = super().has_delete_permission(request, obj=obj)
        return has_permission


class ConfiguracaoAvaliacaoAdmin(ModelAdminPlus):
    list_display = ('forma_calculo', 'maior_nota', 'menor_nota', 'get_avaliacoes')
    list_display_icons = True
    export_to_xls = True
    form = ConfiguracaoAvaliacaoForm

    inlines = [ItemConfiguracaoAvaliacaoInline]

    fieldsets = (('', {'fields': (('forma_calculo', 'divisor'), ('menor_nota', 'maior_nota'), 'autopublicar', 'observacao')}),)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.diario and obj.diario.pode_ser_excluido() and perms.realizar_procedimentos_academicos(request.user, obj.diario.turma.curso_campus):
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
        for matricula_diario in obj.diario.matriculadiario_set.all():
            matricula_diario.criar_registros_notas_etapa(obj.etapa, ItemConfiguracaoAvaliacao.objects.filter(configuracao_avaliacao=obj))
        return obj

    def response_change(self, request, obj):
        obj = self.after_saving_model_and_related_inlines(obj)
        return super().response_change(request, obj)

    def get_avaliacoes(self, obj):
        if obj.itemconfiguracaoavaliacao_set.exists():
            lista = ['<ul>']
            for item in obj.itemconfiguracaoavaliacao_set.all():
                lista.append(f'<li>{item.get_tipo_display()}({item.sigla}): {item.nota_maxima}</li>')
            lista.append('</ul>')
        else:
            return mark_safe('-')

        return mark_safe(''.join(lista))

    get_avaliacoes.short_description = 'Avaliações'


admin.site.register(ConfiguracaoAvaliacao, ConfiguracaoAvaliacaoAdmin)


class ConfiguracaoCertificadoENEMAdmin(ModelAdminPlus):
    list_filter = ('ano',)
    list_display = ('ano', 'data_primeira_prova', 'numero_portaria', 'get_total_registros_alunos')
    list_display_icons = True
    ordering = ('ano',)
    form = ConfiguracaoCertificadoENEMForm

    def get_total_registros_alunos(self, obj):
        return obj.registroalunoinep_set.all().count()

    get_total_registros_alunos.short_description = 'Nº de pedidos de certificados ENEM na Planilha do INEP'


admin.site.register(ConfiguracaoCertificadoENEM, ConfiguracaoCertificadoENEMAdmin)


class SolicitacaoCertificadoENEMAdmin(ModelAdminPlus):
    export_to_xls = True
    list_filter = (CustomTabListFilter, 'configuracao_certificado_enem__ano', 'avaliador', 'tipo_certificado')
    list_display = ('nome', 'cpf', 'email', 'configuracao_certificado_enem', 'get_tipo_certificacao', 'data_solicitacao', 'get_data_primeira_prova', 'get_acoes')
    list_xls_display = ('nome', 'cpf', 'email', 'configuracao_certificado_enem', 'get_tipo_certificado_display', 'data_solicitacao', 'avaliador')
    list_display_icons = True
    search_fields = ('nome', 'cpf')
    ordering = ('nome', 'configuracao_certificado_enem__ano', 'data_solicitacao')
    date_hierarchy = 'data_solicitacao'
    form = CadastrarSolicitacaoCertificadoENEMForm
    fieldsets = CadastrarSolicitacaoCertificadoENEMForm.fieldsets

    def get_data_primeira_prova(self, obj):
        return obj.configuracao_certificado_enem.data_primeira_prova

    get_data_primeira_prova.short_description = 'Data da Primeira Prova'

    def get_tipo_certificacao(self, obj):
        return mark_safe(obj.get_tipo_certificacao(True))

    get_tipo_certificacao.short_description = 'Tipo de Certificado'

    def get_acoes(self, obj):
        lista = []
        if obj.data_avaliacao:
            if obj.avaliada:
                if not obj.razao_ressalva:
                    lista.append('<span class="status status-success">Atendida por {} em {}</span>'.format(obj.avaliador, obj.data_avaliacao.strftime("%d/%m/%y")))
                else:
                    lista.append('<span class="status status-success">Atendida com Ressalva por {} em {}</span>'.format(obj.avaliador, obj.data_avaliacao.strftime("%d/%m/%y")))

                if obj.registroemissaocertificadoenem_set.all().exists():
                    if obj.get_registro_emissao_certificado_enem().cancelado:
                        lista.append(
                            '<span class="status status-error">Certificado Cancelado por {} em {}</span>'.format(
                                obj.get_registro_emissao_certificado_enem().responsavel_cancelamento,
                                obj.get_registro_emissao_certificado_enem().data_cancelamento.strftime("%d/%m/%y"),
                            )
                        )

            else:
                lista.append('<span class="status status-error">Rejeitada por {} em {}</span>'.format(obj.avaliador, obj.data_avaliacao.strftime("%d/%m/%y")))
        else:
            lista.append('<span class="status status-info">Não avaliada</span>')
        return mark_safe(' '.join(lista))

    get_acoes.short_description = 'Situação'

    def get_tabs(self, request):
        return ['tab_pendentes', 'tab_avaliadas']

    def tab_pendentes(self, request, queryset):
        return queryset.filter(data_avaliacao__isnull=True)

    tab_pendentes.short_description = 'Pendentes'

    def tab_avaliadas(self, request, queryset):
        return queryset.filter(data_avaliacao__isnull=False)

    tab_avaliadas.short_description = 'Avaliadas'


admin.site.register(SolicitacaoCertificadoENEM, SolicitacaoCertificadoENEMAdmin)


class RegistroEmissaoCertificadoENEMAdmin(ModelAdminPlus):
    list_display = ('id', 'get_solicitante', 'get_edicao_enem', 'livro', 'numero_registro', 'data_expedicao', 'via', 'cancelado')
    search_fields = ('id', 'solicitacao__nome', 'solicitacao__email', 'solicitacao__cpf', 'livro', 'folha', 'numero_registro', 'data_expedicao')
    list_filter = ('cancelado', 'solicitacao__configuracao_certificado_enem__ano')
    list_display_icons = True
    list_per_page = 15
    date_hierarchy = 'data_expedicao'
    form = RegistroEmissaoCertificadoENEMForm

    def get_solicitante(self, obj):
        return f'{obj.solicitacao.nome} ({obj.solicitacao.cpf})'

    get_solicitante.short_description = 'Solicitante'

    def get_edicao_enem(self, obj):
        return obj.solicitacao.configuracao_certificado_enem.ano

    get_edicao_enem.short_description = 'Edição'


admin.site.register(RegistroEmissaoCertificadoENEM, RegistroEmissaoCertificadoENEMAdmin)


class CidadeAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_filter = ('estado',)
    list_display = ('nome', 'estado', 'codigo', 'cep_inicial', 'cep_final')
    list_display_icons = True
    list_per_page = 15
    fieldsets = (('Dados Gerais', {'fields': ('nome', 'estado', 'pais')}), ('CEP', {'fields': (('cep_inicial', 'cep_final'),)}), ('Código', {'fields': (('codigo',),)}))


admin.site.register(Cidade, CidadeAdmin)


class CartorioAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_display = ('nome', 'cidade', 'serventia')
    list_filter = ('cidade__estado', 'cidade',)
    list_display_icons = True
    list_per_page = 15


admin.site.register(Cartorio, CartorioAdmin)


class ConvocacaoENADEAdmin(ModelAdminPlus):
    search_fields = ('ano_letivo__ano', 'cursos__descricao')
    list_display = ('ano_letivo', 'descricao', 'percentual_minimo_ingressantes', 'percentual_maximo_ingressantes', 'percentual_minimo_concluintes', 'percentual_maximo_concluintes', )
    list_filter = ('cursos',)
    list_display_icons = True
    list_per_page = 15
    form = ConvocacaoENADEForm

    fieldsets = (
        ('Dados Gerais', {'fields': ('ano_letivo', 'descricao', 'portaria', 'edital', 'cursos', 'data_prova')}),
        ('Carga Horária - Ingressantes', {'fields': (('percentual_minimo_ingressantes', 'percentual_maximo_ingressantes'),)}),
        ('Carga Horária - Concluintes', {'fields': (('percentual_minimo_concluintes', 'percentual_maximo_concluintes'),)}),
    )


admin.site.register(ConvocacaoENADE, ConvocacaoENADEAdmin)


class JustificativaDispensaENADEAdmin(ModelAdminPlus):
    list_display = ('descricao', 'ativo')
    list_display_icons = True
    list_per_page = 15


admin.site.register(JustificativaDispensaENADE, JustificativaDispensaENADEAdmin)


class ColacaoGrauAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_filter = (CustomTabListFilter, 'ano_letivo', 'periodo_letivo', 'diretoria')
    list_display = ('id', 'descricao', 'data_colacao', 'ano_letivo', 'periodo_letivo', 'diretoria')
    list_display_icons = True
    list_per_page = 15
    exclude = ('deferida',)
    form = ColacaoGrauForm

    def response_add(self, request, obj):
        return httprr(
            f'/edu/adicionar_alunos_colacao_grau/{obj.pk}/?ano_letivo_aluno={obj.ano_letivo.pk}&periodo_letivo_aluno={obj.periodo_letivo}',
            'Colação de Grau cadastrada com sucesso. Adicione os alunos.',
        )

    def get_tabs(self, request):
        return ['tab_agendadas', 'tab_realizadas']

    def tab_agendadas(self, request, queryset):
        return queryset.filter(deferida=False)

    tab_agendadas.short_description = 'Agendadas'

    def tab_realizadas(self, request, queryset):
        return queryset.filter(deferida=True)

    tab_realizadas.short_description = 'Realizadas'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        result = super().change_view(request, object_id, form_url, extra_context)
        if not in_group(request.user, 'Administrador Acadêmico'):
            obj = self.get_object(request, unquote(object_id))
            if obj and obj.deferida:
                return httprr('..', 'Você não tem permissão para editar uma colação de grau já deferida.', 'error')
        return result

    def get_queryset(self, request):
        return super().get_queryset(request, ColacaoGrau.locals)


admin.site.register(ColacaoGrau, ColacaoGrauAdmin)


class EventoAdmin(ModelAdminPlus):
    search_fields = ('titulo', 'descricao')
    list_filter = ('uo',)
    list_display = ('titulo', 'tipo', 'data', 'uo', 'titulo')
    list_display_icons = True
    list_per_page = 15
    date_hierarchy = 'data'
    export_to_xls = True
    form = EventoForm

    def get_queryset(self, request):
        return self.model.locals.all()

    def response_add(self, request, obj):
        return httprr(f'/edu/evento/{obj.pk}/', 'Cadastro realizado com sucesso. Por favor, adicione os participantes do evento/palestra.')

    def response_change(self, request, obj):
        return httprr(f'/edu/evento/{obj.pk}/', 'Cadastro realizado com sucesso. Por favor, adicione os participantes do evento/palestra.')


admin.site.register(Evento, EventoAdmin)


class DiarioEspecialAdmin(ModelAdminPlus):
    search_fields = ('componente__descricao', 'professores__vinculo__user__username', 'professores__vinculo__pessoa__nome')
    list_filter = ('ano_letivo', 'periodo_letivo')
    list_display = ('ano_letivo', 'periodo_letivo', 'componente', 'get_professores', 'sala', 'get_horario_aulas')
    list_display_icons = True
    form = DiarioEspecialForm

    fieldsets = (
        ('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo'), 'diretoria', 'componente')}),
        ('Centro de Aprendizagem', {'fields': ('is_centro_aprendizagem', 'descricao')}),
        ('Professores', {'fields': ('professores',)}),
        ('Participantes', {'fields': ('participantes',)}),
        ('Configuração de Horário', {'fields': ('horario_campus',)}),
    )

    def get_professores(self, obj):
        return obj.get_nomes_professores()

    get_professores.short_description = 'Professores'

    def get_horario_aulas(self, obj):
        return obj.get_horario_aulas()

    get_horario_aulas.short_description = 'Horários de Aula'

    def get_queryset(self, request):
        qs = super().get_queryset(request, DiarioEspecial.locals).select_related('ano_letivo')
        return qs


admin.site.register(DiarioEspecial, DiarioEspecialAdmin)


class ConfiguracaoCreditosEspeciaisAdmin(ModelAdminPlus):
    list_display = ('descricao', 'quantidade_maxima_creditos_especiais', 'ativo')
    search_fields = ('descricao',)
    ordering = ('descricao',)
    export_to_xls = True
    list_per_page = 15
    list_display_icons = True

    form = ConfiguracaoCreditosEspeciaisForm
    fieldsets = ConfiguracaoCreditosEspeciaisForm.fieldsets

    def get_queryset(self, request):
        return self.model.objects.all()

    def response_add(self, request, obj):
        return httprr(obj.get_absolute_url(), 'Configuração cadastrada com sucesso. Adicione os tipos de atividades relacionadas e seus respectivos créditos.')

    def delete_view(self, request, object_id, extra_context=None):
        configuracao = ConfiguracaoCreditosEspeciais.objects.get(pk=object_id)
        if configuracao.matriz_set.all():
            msg = 'Não é possível realizar a exclusão. Existem matrizes vinculadas a esta configuração.'
        elif configuracao.tem_alunos_vinculados():
            msg = 'Não é possível realizar a exclusão. Existem alunos com créditos especiais que utilizam esta configuracão.'
        else:
            return super().delete_view(request, object_id, extra_context)
        messages.error(request, msg)
        return redirect('..')


admin.site.register(ConfiguracaoCreditosEspeciais, ConfiguracaoCreditosEspeciaisAdmin)


class EstagioDocenteAdmin(ModelAdminPlus):
    form = EstagioDocenteForm
    fieldsets = EstagioDocenteForm.fieldsets
    search_fields = ('matricula_diario__matricula_periodo__aluno__matricula', 'matricula_diario__matricula_periodo__aluno__pessoa_fisica__nome')
    list_display = (
        'nome_aluno',
        'tipo_estagio_docente',
        'get_escola',
        'ch_final',
        'turno',
        'professor_orientador',
        'professor_coordenador',
        'data_inicio',
        'data_fim',
        'get_situacao_estagio',
        'get_situacao_diario',
        'get_opcoes',
    )
    list_display_icons = True
    export_to_xls = True
    list_filter = (
        CustomTabListFilter,
        'matricula_diario__diario__componente_curricular__tipo_estagio_docente',
        'matricula_diario__matricula_periodo__aluno__curso_campus__diretoria__setor__uo',
        'matricula_diario__matricula_periodo__aluno__polo',
        'matricula_diario__matricula_periodo__ano_letivo',
        'matricula_diario__diario__periodo_letivo',
    )
    change_form_template = 'estagiodocente_change_form.html'
    add_form_template = 'estagiodocente_change_form.html'
    show_count_on_tabs = True

    def get_queryset(self, request, *args, **kwargs):
        return super().get_queryset(request, EstagioDocente.locals)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('notificacao/', self.admin_site.admin_view(self.notificacao))]
        return my_urls + urls

    def notificacao(self, request):
        qs = (
            self.get_queryset(request)
            .exclude(visitaestagiodocente__isnull=False)
            .filter(situacao__in=[EstagioDocente.SITUACAO_AGUARDANDO_ENCERRAMENTO, EstagioDocente.SITUACAO_EM_ANDAMENTO])
        )
        contador = 0
        for obj in qs:
            contador += obj.notificar()
        return httprr(request.META.get('HTTP_REFERER', '..'), f'Foram enviados e-mails referentes à {contador} prática(s) com pendências.')

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        if 'tab' in request.GET:
            items.append(dict(url='/admin/edu/estagiodocente/notificacao/?tab={}'.format(request.GET['tab']), label='Enviar Notificações de Pendências'))
        else:
            items.append(dict(url='/admin/edu/estagiodocente/notificacao/', label='Enviar Notificações de Pendências'))
        return items

    def get_tabs(self, request):
        return ['tab_aguardando_informacoes_cadastrais', 'tab_em_andamento', 'tab_aguardando_visita', 'tab_aguardando_portfolio', 'tab_aguardando_encerramento', 'tab_encerrado']

    def tab_aguardando_informacoes_cadastrais(self, request, queryset):
        return queryset.filter(situacao=EstagioDocente.SITUACAO_AGUARDANDO_INFORMACOES_CADASTRAIS)

    tab_aguardando_informacoes_cadastrais.short_description = 'Aguardando Informações Cadastrais'

    def tab_em_andamento(self, request, queryset):
        return queryset.filter(situacao=EstagioDocente.SITUACAO_EM_ANDAMENTO)

    tab_em_andamento.short_description = 'Em Andamento'

    def tab_aguardando_visita(self, request, queryset):
        return queryset.filter(visitaestagiodocente=None, situacao__in=[EstagioDocente.SITUACAO_EM_ANDAMENTO, EstagioDocente.SITUACAO_AGUARDANDO_ENCERRAMENTO])

    tab_aguardando_visita.short_description = 'Aguardando Visita'

    def tab_aguardando_portfolio(self, request, queryset):
        return queryset.filter(portfolio='', situacao__in=[EstagioDocente.SITUACAO_EM_ANDAMENTO, EstagioDocente.SITUACAO_AGUARDANDO_ENCERRAMENTO])

    tab_aguardando_portfolio.short_description = 'Aguardando Portfólio'

    def tab_aguardando_encerramento(self, request, queryset):
        return queryset.filter(situacao=EstagioDocente.SITUACAO_AGUARDANDO_ENCERRAMENTO)

    tab_aguardando_encerramento.short_description = 'Aguardando Encerramento'

    def tab_encerrado(self, request, queryset):
        return queryset.filter(situacao__in=[EstagioDocente.SITUACAO_ENCERRADO, EstagioDocente.SITUACAO_NAO_CONCLUIDO])

    tab_encerrado.short_description = 'Encerrado'

    def get_situacao_diario(self, obj):
        return obj.matricula_diario.get_situacao_display()

    get_situacao_diario.short_description = 'Situação no Diário'

    def get_situacao_estagio(self, obj):
        if obj.matricula_diario.estagiodocente_set.exclude(situacao__in=[EstagioDocente.SITUACAO_MUDANCA]).count() > 1:
            return obj.get_situacao_display() + ' / ' + 'Concomitante'
        else:
            return obj.get_situacao_display()

    get_situacao_estagio.short_description = 'Situação do Estágio'

    def get_opcoes(self, obj):
        texto = '<ul class="action-bar">'
        if obj.situacao in [obj.SITUACAO_AGUARDANDO_ENCERRAMENTO, obj.SITUACAO_EM_ANDAMENTO]:
            texto = texto + f'<li><a class="btn success popup" href="/edu/cadastrar_estagio_docente_concomitante/{obj.pk}/">Adicionar Estágio Concomitante</a></li>'
            texto = texto + f'<li><a class="btn primary popup" href="/edu/mudanca_escola_estagio_docente/{obj.pk}/">Registrar Mudança de Escola</a></li>'
            texto = texto + f'<li><a class="btn warning popup" href="/edu/encerrar_estagio_docente/{obj.pk}/">Encerrar</a></li>'
        texto = texto + '</ul>'
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if obj:
            aluno = obj.matricula_diario.matricula_periodo.aluno
            email_aluno = None
            if aluno.pessoa_fisica.email:
                email_aluno = aluno.pessoa_fisica.email
            elif aluno.pessoa_fisica.email_secundario:
                email_aluno = aluno.pessoa_fisica.email_secundario
            elif aluno.email_google_classroom:
                email_aluno = aluno.email_google_classroom
            elif aluno.email_academico:
                email_aluno = aluno.email_academico
            context.update({'email_aluno': email_aluno})
        return super().render_change_form(request, context, add, change, form_url, obj)


admin.site.register(EstagioDocente, EstagioDocenteAdmin)


class AtividadeComplementarAdmin(ModelAdminPlus):
    list_display = ('get_ano_periodo', 'get_nome_aluno', 'tipo', 'descricao', 'get_curso', 'deferida')
    list_filter = ('tipo', 'deferida', 'aluno__curso_campus', 'aluno__matriz')
    search_fields = ('aluno__pessoa_fisica__nome_registro', 'aluno__matricula', 'aluno__pessoa_fisica__nome_social', 'descricao')
    list_display_icons = True

    def get_nome_aluno(self, obj):
        return mark_safe(f'(<a href="/edu/aluno/{obj.aluno.matricula}/">{obj.aluno.matricula}</a>) {obj.aluno.get_nome()}')

    get_nome_aluno.short_description = 'Aluno'
    get_nome_aluno.admin_order_field = 'aluno__pessoa_fisica__nome'

    def get_ano_periodo(self, obj):
        return mark_safe(f'{obj.ano_letivo.ano}.{obj.periodo_letivo}')

    get_ano_periodo.short_description = 'Ano/Período'

    def get_curso(self, obj):
        return obj.aluno.curso_campus

    get_curso.short_description = 'Curso'

    def get_tabs(self, request):
        return ['tab_aguardando_deferimento']

    def get_queryset(self, request):
        return super().get_queryset(request, AtividadeComplementar.locals)

    def tab_aguardando_deferimento(self, request, queryset):
        return queryset.filter(deferida__isnull=True)

    tab_aguardando_deferimento.short_description = 'Aguardando Avaliação'

    def get_action_bar(self, request):
        return []


admin.site.register(AtividadeComplementar, AtividadeComplementarAdmin)


class AtividadeAprofundamentoAdmin(ModelAdminPlus):
    list_display = ('get_ano_periodo', 'get_nome_aluno', 'tipo', 'descricao', 'get_curso', 'deferida')
    list_filter = ('tipo', 'deferida', 'aluno__curso_campus', 'aluno__matriz')
    search_fields = ('aluno__pessoa_fisica__nome_registro', 'aluno__matricula', 'aluno__pessoa_fisica__nome_social', 'descricao')
    list_display_icons = True

    def get_nome_aluno(self, obj):
        return mark_safe(f'(<a href="/edu/aluno/{obj.aluno.matricula}/">{obj.aluno.matricula}</a>) {obj.aluno.get_nome()}')

    get_nome_aluno.short_description = 'Aluno'
    get_nome_aluno.admin_order_field = 'aluno__pessoa_fisica__nome'

    def get_ano_periodo(self, obj):
        return mark_safe(f'{obj.ano_letivo.ano}.{obj.periodo_letivo}')

    get_ano_periodo.short_description = 'Ano/Período'

    def get_curso(self, obj):
        return obj.aluno.curso_campus

    get_curso.short_description = 'Curso'

    def get_tabs(self, request):
        return ['tab_aguardando_deferimento']

    def get_queryset(self, request):
        return super().get_queryset(request, AtividadeAprofundamento.locals)

    def tab_aguardando_deferimento(self, request, queryset):
        return queryset.filter(deferida__isnull=True)

    tab_aguardando_deferimento.short_description = 'Aguardando Avaliação'

    def get_action_bar(self, request):
        return []


admin.site.register(AtividadeAprofundamento, AtividadeAprofundamentoAdmin)


class RequerimentoAdmin(ModelAdminPlus):
    search_fields = ('id', 'aluno__pessoa_fisica__nome', 'aluno__matricula')
    list_display = ('id', 'aluno', 'tipo', 'data', 'descricao', 'get_detalhamento', 'situacao', 'deferido', 'atendente')
    date_hierarchy = 'data'
    list_filter = (CustomTabListFilter, 'tipo', 'situacao', 'aluno__curso_campus', 'aluno__curso_campus__diretoria', 'aluno__curso_campus__diretoria__setor__uo')
    list_display_icons = True
    list_per_page = 15
    form = RequerimentoForm
    export_to_xls = True

    def get_tabs(self, request):
        return ['tab_em_andamento']

    def get_detalhamento(self, obj):
        return str(obj.get_detalhamento() or '-')

    get_detalhamento.short_description = 'Detalhamento'

    def tab_em_andamento(self, request, queryset):
        return queryset.exclude(situacao='Arquivado')

    tab_em_andamento.short_description = 'Em Andamento'

    def to_xls(self, request, queryset, processo):
        rows = []
        rows.append(['MATRÍCULA', 'ALUNO', 'TURMA', 'CURSO', 'TIPO', 'DATA', 'LOCALIZAÇÃO', 'SITUAÇÃO', 'DESCRIÇÃO/JUSTIFICATIVA'])
        for requerimento in queryset.select_related('curso_campus', 'aluno__pessoa_fisica'):
            rows.append(
                [
                    requerimento.aluno.matricula,
                    requerimento.aluno.pessoa_fisica.nome,
                    requerimento.aluno.get_ultima_matricula_periodo().turma or '',
                    requerimento.aluno.curso_campus.descricao,
                    requerimento.get_tipo_display(),
                    requerimento.data,
                    requerimento.localizacao,
                    requerimento.situacao,
                    requerimento.descricao,
                ]
            )
        return rows

    def get_queryset(self, request):
        if request.user.eh_aluno:
            raise PermissionDenied()
        queryset = super().get_queryset(request)
        groups = ('Estagiário', 'Estagiário Acadêmico Sistêmico', 'Secretário Acadêmico', 'Administrador Acadêmico', 'Auxiliar de Secretaria Acadêmica')
        if in_group(request.user, 'Coordenador de Curso') and not in_group(request.user, groups):
            queryset = queryset.filter(aluno__curso_campus__coordenador=request.user.get_vinculo().pessoa_id).filter(
                tipo__in=(Requerimento.MATRICULA_DISCIPLINA, Requerimento.TRANCAMENTO_DISCIPLINA)
            )
        return queryset


admin.site.register(Requerimento, RequerimentoAdmin)


class AutorizacaoInline(TabularInlinePlus):
    model = Autorizacao
    extra = 1


class ReconhecimentoInline(TabularInlinePlus):
    model = Reconhecimento
    extra = 1


class MatrizCursoAdmin(ModelAdminPlus):
    list_display = 'curso_campus', 'matriz', 'get_autorizacao', 'get_reconhecimento'
    list_display_icons = True
    list_filter = CustomTabListFilter, 'curso_campus__ativo', 'curso_campus__modalidade__nivel_ensino', 'curso_campus',
    list_per_page = 15
    inlines = AutorizacaoInline, ReconhecimentoInline
    fields = 'curso_campus', 'matriz'

    def get_queryset(self, request):
        return super().get_queryset(request, MatrizCurso.locals)

    def get_tabs(self, request):
        return ['tab_sem_autorizacao', 'tab_sem_reconhecimento', 'tab_reconhecimento_expirado']

    def tab_sem_autorizacao(self, request, queryset):
        return queryset.filter(autorizacao__isnull=True)

    tab_sem_autorizacao.short_description = 'Autorização Não-Cadadastrada'

    def tab_sem_reconhecimento(self, request, queryset):
        return queryset.filter(reconhecimento__isnull=True)

    tab_sem_reconhecimento.short_description = 'Reconhecimento Não-Cadadastrado'

    def tab_reconhecimento_expirado(self, request, queryset):
        return queryset.filter(Q(reconhecimento__validade__isnull=True) | Q(reconhecimento__validade__lt=datetime.date.today()))

    tab_reconhecimento_expirado.short_description = 'Reconhecimento Expirado'

    def get_autorizacao(self, obj):
        lista = ['<ul>']
        for autorizacao in obj.autorizacao_set.all():
            lista.append(f'<li>{autorizacao}</li>')
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_autorizacao.short_description = 'Autorização'

    def get_reconhecimento(self, obj):
        lista = ['<ul>']
        for reconhecimento in obj.reconhecimento_set.all():
            lista.append(f'<li>{reconhecimento}</li>')
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_reconhecimento.short_description = 'Reconhecimento'


admin.site.register(MatrizCurso, MatrizCursoAdmin)


class ProjetoFinalAdmin(ModelAdminPlus):
    list_display = 'get_aluno', 'get_ano_letivo', 'get_periodo_letivo', 'tipo', 'titulo'
    list_display_icons = True
    list_filter = ('matricula_periodo__ano_letivo', 'matricula_periodo__periodo_letivo', 'tipo', 'matricula_periodo__aluno__curso_campus__diretoria', 'matricula_periodo__aluno__curso_campus',)
    search_fields = ('matricula_periodo__aluno__matricula', 'matricula_periodo__aluno__pessoa_fisica__nome', 'titulo')
    list_per_page = 15

    def get_action_bar(self, request):
        return super(self.__class__, self).get_action_bar(request, True)

    def get_aluno(self, obj):
        return obj.matricula_periodo.aluno

    get_aluno.short_description = 'Aluno'

    def get_ano_letivo(self, obj):
        return obj.matricula_periodo.ano_letivo

    get_ano_letivo.short_description = 'Ano Letivo'

    def get_periodo_letivo(self, obj):
        return obj.matricula_periodo.periodo_letivo

    get_periodo_letivo.short_description = 'Período Letivo'

    def get_curso(self, obj):
        return obj.matricula_periodo.aluno.curso_campus

    get_aluno.short_description = 'Curso'


admin.site.register(ProjetoFinal, ProjetoFinalAdmin)


class AtaEletronicaAdmin(ModelAdminPlus):
    list_display = 'get_aluno', 'get_ano_letivo', 'get_periodo_letivo', 'get_tipo', 'get_titulo', 'get_responsaveis', 'get_acoes'
    list_display_icons = True
    list_filter = (CustomTabListFilter, 'projeto_final__matricula_periodo__ano_letivo', 'projeto_final__matricula_periodo__periodo_letivo', 'projeto_final__tipo', 'projeto_final__matricula_periodo__aluno__curso_campus__diretoria', 'projeto_final__matricula_periodo__aluno__curso_campus',)
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
            f'/edu/visualizar_ata_eletronica/{obj.pk}/', 'Visualizar Ata')
        )
        assinatura_pendente = obj.get_assinaturas().filter(data__isnull=True).filter(
            pessoa_fisica_id=self.request.user.get_vinculo().pessoa.id
        ).first()
        if assinatura_pendente:
            html.append('<li><a class="btn popup" href="{}">{}</a></li>'.format(
                f'/edu/assinar_ata_eletronica/{assinatura_pendente.pk}/', 'Assinar Eletronicamente')
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


admin.site.register(AtaEletronica, AtaEletronicaAdmin)


class AtividadeCurricularExtensaoAdmin(ModelAdminPlus):

    list_display = 'get_aluno', 'get_ano_letivo', 'get_periodo_letivo', 'tipo_referencia', 'descricao', 'concluida', 'aprovada'
    list_display_icons = True
    list_filter = (CustomTabListFilter, 'matricula_periodo__ano_letivo', 'matricula_periodo__periodo_letivo', 'tipo_referencia', 'descricao', 'concluida', 'aprovada', 'matricula_periodo__aluno__curso_campus',)
    search_fields = ('matricula_periodo__aluno__matricula', 'matricula_periodo__aluno__pessoa_fisica__nome')
    list_per_page = 15
    show_count_on_tabs = True
    actions = 'aprovar', 'rejeitar', 'cancelar_avaliacao'

    def get_aluno(self, obj):
        return obj.matricula_periodo.aluno

    get_aluno.short_description = 'Aluno'

    def get_ano_letivo(self, obj):
        return obj.matricula_periodo.ano_letivo

    get_ano_letivo.short_description = 'Ano Letivo'

    def get_periodo_letivo(self, obj):
        return obj.matricula_periodo.periodo_letivo

    get_periodo_letivo.short_description = 'Período Letivo'

    def get_curso(self, obj):
        return obj.matricula_periodo.aluno.curso_campus

    get_aluno.short_description = 'Curso'

    def get_tabs(self, request):
        return ['tab_aguardando_avaliacao', 'tab_aprovadas', 'tab_rejeitadas']

    def tab_aprovadas(self, request, queryset):
        return queryset.filter(aprovada=True)

    tab_aprovadas.short_description = 'Deferidas'

    def tab_rejeitadas(self, request, queryset):
        return queryset.filter(aprovada=False)

    tab_rejeitadas.short_description = 'Indeferidas'

    def tab_aguardando_avaliacao(self, request, queryset):
        return queryset.filter(aprovada__isnull=True, concluida=True)

    tab_aguardando_avaliacao.short_description = 'Aguardando Avaliação'

    def get_actions(self, request):
        tab = request.GET.get('tab')
        actions = super().get_actions(request)
        if tab == 'tab_aguardando_avaliacao':
            actions.pop('cancelar_avaliacao')
        elif tab == 'tab_aprovadas':
            actions.pop('aprovar')
            actions.pop('rejeitar')
        elif tab == 'tab_rejeitadas':
            actions.pop('aprovar')
            actions.pop('rejeitar')
        else:
            actions.clear()
        return actions

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        cursos_coordenados = CursoCampus.objects.filter(coordenador=request.user.get_vinculo().pessoa_id).values_list('pk', flat=True)
        return queryset.filter(matricula_periodo__aluno__curso_campus__in=cursos_coordenados)

    def aprovar(self, request, queryset):
        queryset.update(aprovada=True)
        messages.success(request, 'Atividade(s) deferida(s) com sucesso.')

    aprovar.short_description = "Deferir atividades selecionadas"

    def rejeitar(self, request, queryset):
        queryset.update(aprovada=False)
        messages.success(request, 'Atividade(s) indeferida(s) com sucesso.')

    rejeitar.short_description = "Indeferir atividades selecionadas"

    def cancelar_avaliacao(self, request, queryset):
        queryset.update(aprovada=None)
        messages.success(request, 'Cancelamento realizado com sucesso.')

    cancelar_avaliacao.short_description = "Cancelar avaliação das atividades selecionadas"


admin.site.register(AtividadeCurricularExtensao, AtividadeCurricularExtensaoAdmin)


class AssinaturaEletronicaAdmin(ModelAdminPlus):
    list_filter = (CustomTabListFilter, 'registro_emissao_diploma__aluno__curso_campus__diretoria')
    list_display = ('get_matricula', 'get_nome_aluno', 'get_curso_aluno', 'get_assinantes', 'get_situacao', 'get_acoes')
    search_fields = ('registro_emissao_diploma__aluno__matricula',
                     'registro_emissao_diploma__aluno__pessoa_fisica__nome')
    list_display_icons = True
    list_per_page = 10
    actions = 'assinar', 'excluir', 'revogar'

    def get_situacao(self, obj):
        if obj.data_revogacao:
            return mark_safe('<span class="status status-error">Solicitação Revogada</span>')
        if obj.data_assinatura:
            return mark_safe('<span class="status status-success">Concluída em {}</span>'.format(
                obj.data_assinatura.strftime('%d/%m/%Y')
            ))
        else:
            return mark_safe('<span class="status status-alert">Em Andamento</span>')

    get_situacao.short_description = 'Situação'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if request.GET.get('tab') == 'tab_pendentes_usuario':
            actions.pop('revogar')
            if not request.session.get('sessao_assinatura_eletronica'):
                actions.pop('assinar')
            if not in_group(request.user, 'Secretário Acadêmico'):
                actions.pop('excluir')
        elif request.GET.get('tab') == 'tab_assinadas':
            actions.pop('assinar')
            actions.pop('excluir')
            if not in_group(request.user, 'Diretor Geral, Diretor Acadêmico, Diretor de Ensino, Reitor'):
                actions.pop('revogar')
        else:
            actions.pop('assinar')
            actions.pop('excluir')
            actions.pop('revogar')
        return actions

    get_actions.short_description = 'Ações'

    def assinar(self, request, queryset):
        if queryset.order_by('registro_emissao_diploma__aluno__curso_campus__modalidade_id').values_list('registro_emissao_diploma__aluno__curso_campus__modalidade_id', flat=True).distinct().count() > 1:
            messages.error(request, 'Por favor, selecione alunos de uma única modalidade de ensino.')
        else:
            qs = queryset.values_list('id', flat=True)
            ids = []
            for pk in qs:
                ids.append(str(pk))
            url = '/edu/assinar_diplomas_eletronicos/{}/'.format('_'.join(ids))
            return HttpResponseRedirect(url)

    assinar.short_description = 'Assinar Eletronicamente'

    def excluir(self, request, queryset):
        queryset.delete()
        messages.success(request, 'Assinaturas excluídas com sucesso.')

    excluir.short_description = 'Excluir Assinaturas'

    def revogar(self, request, queryset):
        qs = queryset.values_list('id', flat=True)
        ids = []
        for pk in qs:
            ids.append(str(pk))
        url = '/edu/revogar_assinatura_eletronica/{}/'.format('_'.join(ids))
        return HttpResponseRedirect(url)

    revogar.short_description = 'Revogar Assinaturas'

    def get_matricula(self, obj):
        return obj.get_matricula()

    get_matricula.short_description = 'Matrícula'

    def get_nome_aluno(self, obj):
        return obj.get_nome_aluno()

    get_nome_aluno.short_description = 'Nome'

    def get_curso_aluno(self, obj):
        return obj.get_curso_aluno()

    get_curso_aluno.short_description = 'Curso'

    def get_assinantes(self, obj):
        html = []
        html.append('<ul>')
        for solicitacao in obj.solicitacaoassinaturaeletronica_set.all():
            if solicitacao.data_assinatura:
                html.append('<li>{} <font style="color:green">{}</font></li>'.format(solicitacao.vinculo, solicitacao.data_assinatura.strftime('%d/%m/%Y')))
            else:
                html.append(f'<li>{solicitacao.vinculo}Aguardando Assinatura</li>')
        html.append('</ul>')
        return mark_safe(''.join(html))

    get_assinantes.short_description = 'Assinantes'

    def get_acoes(self, obj):
        html = []
        html.append('<ul class="action-bar">')
        if obj.registro_emissao_documento_historico:
            html.append('<li><a target="_blank" class="btn default" href="{}">Visualizar {}</a></li>'.format(obj.get_url_historico(), 'Histórico'))
        if obj.registro_emissao_documento_diploma:
            html.append('<li><a target="_blank" class="btn default" href="{}">Visualizar {}</a></li>'.format(obj.get_url_registro(), 'Registro'))
            html.append('<li><a target="_blank" class="btn default" href="{}">Visualizar {}</a></li>'.format(obj.get_url_diploma(), 'Diploma'))
        return mark_safe(''.join(html))

    get_acoes.short_description = 'Ações'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if in_group(request.user, ('Administrador Acadêmico', 'Reitor')):
            return qs
        elif in_group(request.user, ('Coordenador de Registros Acadêmicos', 'Diretor Geral')):
            return qs.filter(registro_emissao_diploma__aluno__curso_campus__diretoria__setor__uo=request.user.get_vinculo().setor.uo)
        elif in_group(request.user, 'Secretário Acadêmico'):
            setores = UsuarioGrupoSetor.objects.filter(
                usuario_grupo__user=request.user, usuario_grupo__group__name__in=('Secretário Acadêmico',)
            ).values_list('setor', flat=True)
            return qs.filter(registro_emissao_diploma__aluno__curso_campus__diretoria__setor__in=setores)
        else:
            return qs.filter(solicitacaoassinaturaeletronica__vinculo__user=request.user)

    def get_tabs(self, request):
        return ['tab_pendentes_usuario', 'tab_pendentes', 'tab_assinadas', 'tab_revogados']

    def tab_pendentes(self, request, queryset):
        return queryset.filter(data_assinatura__isnull=True, data_revogacao__isnull=True)

    tab_pendentes.short_description = 'Pendentes de Assinatura'

    def tab_pendentes_usuario(self, request, queryset):
        ids = SolicitacaoAssinaturaEletronica.objects.filter(vinculo=request.user.get_vinculo(), data_assinatura__isnull=True, assinatura_eletronica__data_revogacao__isnull=True).values_list('assinatura_eletronica', flat=True)
        return queryset.filter(id__in=ids)

    tab_pendentes_usuario.short_description = 'Pendentes de Minha Assinatura'

    def tab_assinadas(self, request, queryset):
        return queryset.filter(data_assinatura__isnull=False, data_revogacao__isnull=True)

    tab_assinadas.short_description = 'Assinadas'

    def tab_revogados(self, request, queryset):
        return queryset.filter(data_revogacao__isnull=False)

    tab_revogados.short_description = 'Revogados'

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if in_group(request.user, 'Diretor Geral, Diretor Acadêmico, Diretor de Ensino, Reitor'):
            if request.session.get('sessao_assinatura_eletronica'):
                items.append(
                    dict(url='/edu/finalizar_sessao_assinatura_eletronica/', label='Finaliza Sessão de Assinatura')
                )
            else:
                items.append(
                    dict(url='/edu/iniciar_sessao_assinatura_eletronica/', label='Iniciar Sessão de Assinatura')
                )
        return items


admin.site.register(AssinaturaEletronica, AssinaturaEletronicaAdmin)


class AssinaturaDigitalAdmin(ModelAdminPlus):
    list_filter = (CustomTabListFilter, 'registro_emissao_diploma__aluno__curso_campus__diretoria', 'concluida')
    list_display = ('get_matricula', 'get_nome_aluno', 'get_curso_aluno', 'get_situacao', 'get_acoes')
    search_fields = ('registro_emissao_diploma__aluno__matricula',
                     'registro_emissao_diploma__aluno__pessoa_fisica__nome')
    list_display_icons = True
    list_per_page = 10
    actions = 'sincronizar_assinatura_digital', 'reiniciar_assinatura_digital'

    def get_action_bar(self, request, remove_add_button=False):
        return super().get_action_bar(request, remove_add_button=True)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if request.GET.get('tab') == 'tab_pendentes':
            pass
        elif request.GET.get('tab') == 'tab_assinadas':
            actions.pop('sincronizar_assinatura_digital')
        else:
            actions.pop('reiniciar_assinatura_digital')
            actions.pop('sincronizar_assinatura_digital')
        return actions

    get_actions.short_description = 'Ações'

    def sincronizar_assinatura_digital(self, request, queryset):
        from edu.diploma_digital.rap import AssinadorDigital
        assinador = AssinadorDigital()
        for obj in queryset:
            assinador.sincronizar(obj)
        messages.success(request, 'Sincronização realizada com sucesso.')

    sincronizar_assinatura_digital.short_description = 'Sincronizar Assinatura'

    def reiniciar_assinatura_digital(self, request, queryset):
        from edu.diploma_digital.rap import AssinadorDigital
        assinador = AssinadorDigital()
        for obj in queryset:
            assinador.reiniciar(obj)
        messages.success(request, 'Reinicialização realizada com sucesso.')

    reiniciar_assinatura_digital.short_description = 'Reiniciar Assinatura'

    def get_matricula(self, obj):
        return obj.get_matricula()

    get_matricula.short_description = 'Matrícula'

    def get_nome_aluno(self, obj):
        return obj.get_nome_aluno()

    get_nome_aluno.short_description = 'Nome'

    def get_curso_aluno(self, obj):
        return obj.get_curso_aluno()

    get_curso_aluno.short_description = 'Curso'

    def get_situacao(self, obj):
        if obj.data_revogacao:
            return mark_safe('<span class="status status-error">Solicitação revogada</span>')
        if obj.concluida:
            return mark_safe('<span class="status status-success">Concluída</span>')
        else:
            return mark_safe('<span class="status status-alert">Em andamento</span>')

    get_situacao.short_description = 'Situação'

    def get_acoes(self, obj):
        html = []
        html.append('<ul class="action-bar">')
        html.append(f'<li><a target="_blank" class="btn default" href="/edu/registroemissaodiploma/{obj.registro_emissao_diploma_id}/">Acessar Registro</a></li>')
        html.append(f'<li><a target="_blank" class="btn default" href="{obj.get_url_historico()}">Visualizar Histórico</a></li>')
        html.append(f'<li><a target="_blank" class="btn default" href="{obj.get_url_registro()}">Visualizar Registro</a></li>')
        if obj.diploma:
            html.append(f'<li><a target="_blank" class="btn default" href="{obj.get_url_diploma()}">Visualizar Diploma</a></li>')
        html.append(f'<li><a class="btn popup" href="{obj.get_url_status_assinaturas()}">Consultar Situação das Assinaturas</a></li>')
        if obj.status_documentacao_academica_digital:
            html.append(f'<li><a target="_blank" class="btn" href="{obj.get_url_xml_documentacao_academica()}">Baixar XML da Documentação Acadêmica</a></li>')
        if obj.status_historico_escolar:
            html.append(f'<li><a target="_blank" class="btn" href="{obj.get_url_xml_historico_escolar()}">Baixar XML do Histórico</a></li>')
        if obj.status_dados_diploma_digital:
            html.append(f'<li><a target="_blank" class="btn" href="{obj.get_url_xml_dados_diploma()}">Baixar XML do Diploma</a></li>')
        if obj.status_representacao_diploma_digital:
            html.append(f'<li><a target="_blank" class="btn" href="{obj.get_url_pdf_representacao_visual()}">Baixar PDF do Diploma</a></li>')

        return mark_safe(''.join(html))

    get_acoes.short_description = 'Opções'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if in_group(request.user, ('Administrador Acadêmico', 'Reitor')):
            return qs
        elif in_group(request.user, ('Coordenador de Registros Acadêmicos', 'Diretor Geral')):
            return qs.filter(registro_emissao_diploma__aluno__curso_campus__diretoria__setor__uo=request.user.get_vinculo().setor.uo)
        elif in_group(request.user, 'Secretário Acadêmico'):
            setores = UsuarioGrupoSetor.objects.filter(
                usuario_grupo__user=request.user, usuario_grupo__group__name__in=('Secretário Acadêmico',)
            ).values_list('setor', flat=True)
            return qs.filter(registro_emissao_diploma__aluno__curso_campus__diretoria__setor__in=setores)
        else:
            return qs.none()

    def get_tabs(self, request):
        return ['tab_pendentes', 'tab_assinadas', 'tab_revogados']

    def tab_pendentes(self, request, queryset):
        return queryset.filter(concluida=False, data_revogacao__isnull=True)

    tab_pendentes.short_description = 'Pendentes de Assinatura'

    def tab_assinadas(self, request, queryset):
        return queryset.filter(concluida=True, data_revogacao__isnull=True)

    tab_assinadas.short_description = 'Assinadas'

    def tab_revogados(self, request, queryset):
        return queryset.filter(data_revogacao__isnull=False)

    tab_revogados.short_description = 'Revogadas'


admin.site.register(AssinaturaDigital, AssinaturaDigitalAdmin)


class CodigoAutenticadorSistecAdmin(ModelAdminPlus):
    list_display = 'cpf', 'codigo_unidade', 'codigo_curso', 'codigo_autenticacao'
    search_fields = 'cpf',
    list_display_icons = True
    export_to_xls = True
    list_per_page = 15

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        items.append(dict(url='/edu/importar_autenticacao_sistec/', label='Importar Autenticação SISTEC'))
        return items


admin.site.register(CodigoAutenticadorSistec, CodigoAutenticadorSistecAdmin)


class CertificadoDiplomaAdmin(ModelAdminPlus):
    list_display = 'get_matricula_aluno', 'get_nome_aluno', 'get_curso',  'validade', 'get_acoes'
    search_fields = 'aluno__matricula', 'aluno__pessoa_fisica__cpf', 'aluno__pessoa_fisica__nome', 'processo__numero_protocolo'
    list_display_icons = True
    filter_filter = 'aluno__curso_campus__diretoria', 'aluno__curso_campus__diretoria__setor__uo'
    form = CertificadoDiplomaForm
    export_to_xls = True
    list_per_page = 15

    def get_matricula_aluno(self, obj):
        return obj.aluno.matricula

    get_matricula_aluno.short_description = 'Matrícula'

    def get_nome_aluno(self, obj):
        return obj.aluno.pessoa_fisica.nome

    get_nome_aluno.short_description = 'Aluno'

    def get_curso(self, obj):
        return f'{obj.aluno.curso_campus.codigo} - {obj.aluno.curso_campus.descricao_historico}'

    get_curso.short_description = 'Curso'

    def get_acoes(self, obj):
        html = []
        html.append('<ul class="action-bar">')
        html.append('<li><a target="_blank" class="btn default" href="{}">{}</a></li>'.format(
            f'/edu/certificado_diploma_pdf/{obj.pk}/', 'Imprimir')
        )
        html.append('</ul>')
        return mark_safe(''.join(html))

    get_acoes.short_description = 'Ações'


admin.site.register(CertificadoDiploma, CertificadoDiplomaAdmin)


class ReferenciaBibliograficaBasicaInline(TabularInlinePlus):
    model = ReferenciaBibliograficaBasica
    extra = 1


class ReferenciaBibliograficaComplementarInline(TabularInlinePlus):
    model = ReferenciaBibliograficaComplementar
    extra = 1


class PlanoEnsinoAdmin(ModelAdminPlus):
    list_display = 'diario', 'coordenador_curso', 'data_submissao', 'data_homologacao'
    list_display_icons = True
    list_filter = CustomTabListFilter, 'diario__ano_letivo', 'diario__periodo_letivo', 'diario', 'diario__turma'
    list_per_page = 15
    inlines = ReferenciaBibliograficaBasicaInline, ReferenciaBibliograficaComplementarInline
    form = PlanoEnsinoForm
    actions = ('submeter', 'aprovar', 'homologar', 'cancelar_submissao', 'cancelar_homologacao', 'devolver_professor', 'devolver_coordenador')
    show_count_on_tabs = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            ids = []
            ids.extend(qs.filter(diario__professordiario__professor__vinculo=request.user.get_vinculo()).values_list('id', flat=True))
            ids.extend(qs.filter(coordenador_curso=request.user.get_profile()).values_list('id', flat=True))
            if in_group(request.user, 'Diretor Acadêmico'):
                ids.extend(qs.filter(diario__turma__curso_campus__diretoria__setor__uo=request.user.get_vinculo().setor.uo).values_list('id', flat=True))
            return qs.filter(id__in=ids)
        return qs

    def get_actions(self, request):
        actions = super().get_actions(request)
        active = {}
        if request.GET.get('tab'):
            if request.GET.get('tab') == 'tab_aguardando_minha_subissao' and in_group(request.user, 'Professor'):
                active['submeter'] = actions['submeter']
            elif request.GET.get('tab') == 'tab_aguardando_aprovacao' and in_group(request.user, 'Professor'):
                active['cancelar_submissao'] = actions['cancelar_submissao']
            elif request.GET.get('tab') == 'tab_aguardando_minha_aprovacao' and in_group(request.user, 'Coordenador de Curso'):
                active['aprovar'] = actions['aprovar']
                active['devolver_professor'] = actions['devolver_professor']
            elif request.GET.get('tab') == 'tab_aguardando_homologacao' and in_group(request.user, 'Diretor Acadêmico'):
                active['homologar'] = actions['homologar']
                active['devolver_coordenador'] = actions['devolver_coordenador']
            elif request.GET.get('tab') == 'tab_homologados' and in_group(request.user, 'Diretor Acadêmico'):
                active['cancelar_homologacao'] = actions['cancelar_homologacao']
        return active

    def submeter(self, request, queryset):
        queryset.update(data_submissao=datetime.today())
        messages.success(request, 'Submissão realizada com sucesso.')

    submeter.short_description = 'Submeter'

    def cancelar_submissao(self, request, queryset):
        queryset.update(data_submissao=None)
        messages.success(request, 'Ação realizada com sucesso.')

    cancelar_submissao.short_description = 'Cancelar Submissão'

    def aprovar(self, request, queryset):
        queryset.update(data_aprovacao=datetime.today())
        messages.success(request, 'Aprovação realizada com sucesso.')

    aprovar.short_description = 'Aprovar'

    def homologar(self, request, queryset):
        queryset.update(data_homologacao=datetime.today())
        messages.success(request, 'Homologação realizada com sucesso.')

    homologar.short_description = 'Homologar'

    def cancelar_homologacao(self, request, queryset):
        queryset.update(data_homologacao=None)
        messages.success(request, 'Ação realizada com sucesso.')

    cancelar_homologacao.short_description = 'Cancelar Homologação'

    def devolver_professor(self, request, queryset):
        pks = [str(pk) for pk in queryset.values_list('pk', flat=True)]
        url = '/edu/devolver_plano_ensino/professor/{}/'.format('_'.join(pks))
        return HttpResponseRedirect(url)

    devolver_professor.short_description = 'Devolver'

    def devolver_coordenador(self, request, queryset):
        pks = [str(pk) for pk in queryset.values_list('pk', flat=True)]
        url = '/edu/devolver_plano_ensino/coordenador/{}/'.format('_'.join(pks))
        return HttpResponseRedirect(url)

    devolver_coordenador.short_description = 'Devolver'

    def get_tabs(self, request):
        tabs = []
        if in_group(request.user, 'Professor'):
            tabs.append('tab_aguardando_minha_subissao')
            tabs.append('tab_aguardando_aprovacao')
        if in_group(request.user, 'Coordenador de Curso'):
            tabs.append('tab_aguardando_minha_aprovacao')
        tabs.append('tab_aguardando_homologacao')
        tabs.append('tab_homologados')
        return tabs

    def tab_aguardando_minha_subissao(self, request, queryset):
        return queryset.filter(data_submissao__isnull=True, diario__professordiario__professor__vinculo=request.user.get_vinculo())

    tab_aguardando_minha_subissao.short_description = 'Meus planos Aguardando Submissão'

    def tab_aguardando_minha_aprovacao(self, request, queryset):
        return queryset.filter(data_submissao__isnull=False, data_aprovacao__isnull=True, coordenador_curso=request.user.get_profile())

    tab_aguardando_minha_aprovacao.short_description = 'Aguardando Minha Aprovação'

    def tab_aguardando_aprovacao(self, request, queryset):
        return queryset.filter(data_submissao__isnull=False, data_aprovacao__isnull=True).filter(diario__professordiario__professor__vinculo=request.user.get_vinculo())

    tab_aguardando_aprovacao.short_description = 'Meus planos Aguardando Aprovação'

    def tab_aguardando_homologacao(self, request, queryset):
        return queryset.filter(data_aprovacao__isnull=False, data_homologacao__isnull=True)

    tab_aguardando_homologacao.short_description = 'Aguardando Homologação'

    def tab_homologados(self, request, queryset):
        return queryset.filter(data_homologacao__isnull=False)

    tab_homologados.short_description = 'Homologados'


admin.site.register(PlanoEnsino, PlanoEnsinoAdmin)


class PlanoEstudoAdmin(ModelAdminPlus):
    list_display = 'tipo', 'get_ano_periodo_letivo', 'get_matricula', 'get_aluno', 'get_curso', 'data_homologacao', 'numero_ata_homologacao'
    list_display_icons = True
    list_filter = CustomTabListFilter, 'pedido_matricula__matricula_periodo__ano_letivo', 'pedido_matricula__matricula_periodo__periodo_letivo', 'planejamento_concluido', 'homologado', 'descumprido', 'pedido_matricula__matricula_periodo__aluno__curso_campus',
    list_per_page = 15
    search_fields = 'pedido_matricula__matricula_periodo__aluno__matricula', 'pedido_matricula__matricula_periodo__aluno__pessoa_fisica__nome'
    actions = ['avaliar', 'cancelar_avaliacao']

    def get_matricula(self, obj):
        return obj.pedido_matricula.matricula_periodo.aluno.matricula

    get_matricula.short_description = 'Matrícula'

    def get_aluno(self, obj):
        return obj.pedido_matricula.matricula_periodo.aluno

    get_aluno.short_description = 'Aluno'

    def get_curso(self, obj):
        return obj.pedido_matricula.matricula_periodo.aluno.curso_campus

    get_aluno.short_description = 'Curso'

    def get_ano_periodo_letivo(self, obj):
        return '{}/{}'.format(
            obj.pedido_matricula.matricula_periodo.ano_letivo,
            obj.pedido_matricula.matricula_periodo.periodo_letivo
        )

    get_ano_periodo_letivo.short_description = 'Ano/Período Letivo'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            ids = []
            ids.extend(qs.filter(pedido_matricula__matricula_periodo__aluno__curso_campus__coordenador=request.user.get_profile()).values_list('id', flat=True))
            if in_group(request.user, 'Diretor Acadêmico'):
                ids.extend(qs.filter(pedido_matricula__matricula_periodo__aluno__curso_campus__diretoria__setor__uo=request.user.get_vinculo().setor.uo).values_list('id', flat=True))
            return qs.filter(id__in=ids)
        return qs

    def tab_dispensados(self, request, queryset):
        return queryset.filter(tipo='Dispensa')

    tab_dispensados.short_description = 'Dispensas'

    def tab_aguardando_planejamento(self, request, queryset):
        return queryset.filter(tipo='Planejamento').filter(planejamento_concluido__isnull=True)

    tab_aguardando_planejamento.short_description = 'Aguardando Planejamento'

    def tab_aguardando_avaliacao(self, request, queryset):
        qs1 = queryset.filter(tipo='Planejamento').filter(planejamento_concluido=True).filter(homologado__isnull=True)
        qs2 = queryset.filter(tipo='Dispensa').filter(homologado__isnull=True)
        return qs1 | qs2

    tab_aguardando_avaliacao.short_description = 'Aguardando Avaliação'

    def tab_homologados(self, request, queryset):
        return queryset.filter(homologado=True)

    tab_homologados.short_description = 'Homologados'

    def tab_nao_homologados(self, request, queryset):
        return queryset.filter(homologado=False)

    tab_nao_homologados.short_description = 'Não-Homologados'

    def tab_descumpridos(self, request, queryset):
        return queryset.filter(tipo='Planejamento', planejamento_concluido=True, homologado=True, descumprido=True)

    tab_descumpridos.short_description = 'Descumpridos'

    def get_tabs(self, request):
        return ['tab_dispensados', 'tab_aguardando_planejamento', 'tab_aguardando_avaliacao', 'tab_homologados', 'tab_nao_homologados', 'tab_descumpridos']

    def avaliar(self, request, queryset):
        pks = [str(pk) for pk in queryset.values_list('pk', flat=True)]
        url = '/edu/avaliar_plano_estudo/{}/'.format('_'.join(pks))
        return HttpResponseRedirect(url)

    avaliar.short_description = 'Avaliar'

    def cancelar_avaliacao(self, request, queryset):
        queryset.update(
            homologado=None,
            data_homologacao=None,
            observacao_homologacao='',
            numero_ata_homologacao=None,
        )

    cancelar_avaliacao.short_description = 'Cancelar Avaliação'

    def get_actions(self, request):
        actions = super().get_actions(request)
        active = {}
        if request.GET.get('tab'):
            if request.GET.get('tab') == 'tab_aguardando_avaliacao' and (in_group(request.user, 'Diretor Acadêmico') or request.user.is_superuser):
                active['avaliar'] = actions['avaliar']
            if request.GET.get('tab') in ('tab_homologados', 'tab_nao_homologados') and (in_group(request.user, 'Diretor Acadêmico') or request.user.is_superuser):
                active['cancelar_avaliacao'] = actions['cancelar_avaliacao']
        return active


admin.site.register(PlanoEstudo, PlanoEstudoAdmin)


class RegistroEducacensoAdmin(ModelAdminPlus):
    list_display = 'ano_censo', 'numero_registro', 'privado'
    list_display_icons = True
    list_filter = 'ano_censo', 'numero_registro', 'privado'
    list_per_page = 15


admin.site.register(RegistroEducacenso, RegistroEducacensoAdmin)


class QuestaoEducacensoAdmin(ModelAdminPlus):
    list_display_icons = True


admin.site.register(QuestaoEducacenso, QuestaoEducacensoAdmin)
