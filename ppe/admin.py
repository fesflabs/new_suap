from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import path
from django.utils.safestring import mark_safe

from djtools import forms
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import in_group, format_user
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from ppe.forms import (
    TrabalhadorEducandoForm, FormacaoPPEForm, EstruturaCursoForm, CursoForm, TurmaPPEForm, AnamneseForm,
    ItemConfiguracaoAvaliacaoFormset, ConfiguracaoAvaliacaoForm, SolicitacaoUsuarioForm, OpcaoRespostaAvaliacaoForm,
    TipoAvaliacaoForm, EtapaMonitoramentoForm, SetorForm, SetorAddForm, TrabalhadorSetorHistoricoForm,
    ChefiaSetorHistoricoForm, ChefiaPPEForm
)
from ppe.models import (
    TrabalhadorEducando, ChefiaPPE, FormacaoPPE,
    EstruturaCurso, RepresentacaoConceitual, Curso, Turma, Anamnese,
    TrabalhoAnteriorAoPPE, MeioTransporte, ResideCom, MembrosCarteiraAssinada,
    ResidenciaSaneamentoBasico, ItensResidencia, ParticipacaoGruposSociais, CursosTrabalhadorEducando,
    RedeSocial, ItemConfiguracaoAvaliacao, ConfiguracaoAvaliacao, TutorTurma, SolicitacaoUsuario, PerguntaAvaliacao,
    OpcaoRespostaAvaliacao, TipoAvaliacao, Avaliacao, EtapaMonitoramento, ConfiguracaoMonitoramento,
    FormacaoTecnica, Setor, Unidade, TrabalhadorSetorHistorico, ChefiaSetorHistorico,
)


class FormacaoTecnicaAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']


class TrabalhadorEducandoAdmin(ModelAdminPlus):
    list_display = ('get_foto', 'get_info_principal', 'data_matricula')
    list_display_icons = True
    export_to_xls = True
    list_per_page = 15
    ordering = ('-id',)
    form = TrabalhadorEducandoForm
    fieldsets = TrabalhadorEducandoForm.fieldsets

    search_fields = ('pessoa_fisica__nome_registro', 'pessoa_fisica__search_fields_optimized',)

    def has_add_permission(self, request):
        return False

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if request.user.has_perm('ppe.efetuarmatriculatrabalhadoreducando'):
            items.append(dict(url='/ppe/efetuarmatriculatrabalhadoreducando/', label='Adicionar Novo(a) Trabalhador(a) Educando(a)', css_class='success'))
        return items

    def get_queryset(self, request, manager=None, *args, **kwargs):
        return super().get_queryset(
            request, TrabalhadorEducando.objects
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
        if in_group(self.request.user, ['Coordenador(a) PPE', 'Supervisor(a) Pedagógico(a)']):
            out += f'<dt>CPF:</dt><dd>{obj.pessoa_fisica.cpf}</dd>'
        out += '''<dt>Matrícula:</dt><dd>{}</dd>
                </dl>
            '''.format(obj.matricula)
        return mark_safe(out)

    get_info_principal.short_description = 'Dados Principais'
    get_info_principal.admin_order_field = 'pessoa_fisica__nome'





class ChefiaPPEAdmin(ModelAdminPlus):
    list_display = ('cpf', 'nome', 'email', 'get_opcoes')
    list_display_icons = True
    list_per_page = 30
    search_fields = ('nome', 'cpf', 'pesssoa_fisica__username')
    form = ChefiaPPEForm

    def has_add_permission(self, request):
        if in_group(request.user, 'Coordenador(a) PPE'):
            return True
        return False

    def has_view_permission(self, request, obj=None):
        if in_group(request.user, 'Coordenador(a) PPE'):
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if in_group(request.user, 'Coordenador(a) PPE'):
            return True
        return False

    def add_view(self, request):
        return httprr('/ppe/nova_chefia_imediata')

    def get_opcoes(self, obj):
        mostra_acoes = ''
        if (in_group(self.request.user, 'Coordenador(a) PPE,Coordenador(a) Aperfeiçoamento Profissional PPE')) or self.request.user.is_superuser:
            # if obj.ativo:
            #     mostra_acoes = f'<a href="/comum/usuario_externo/inativar/{obj.id}/" class="btn danger">Inativar</a>'
            # elif obj.pode_ser_ativado():
            #     mostra_acoes = f'<a href="/comum/usuario_externo/ativar/{obj.id}/" class="btn success">Ativar</a>'
            return mark_safe(mostra_acoes)

    get_opcoes.short_description = 'Opções'


class FormacaoPPEAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'ativo')
    list_filter = (CustomTabListFilter,  'ativo')
    search_fields = ('id', 'descricao')
    list_display_icons = True
    list_per_page = 15
    export_to_xls = True
    form = FormacaoPPEForm
    show_count_on_tabs = True

    fieldsets = (
        (
            'Dados Gerais',
            {'fields': ('descricao',  'ativo', ('data_inicio', 'data_fim'), 'ppp')},
        ),
        (
            'Carga Horária',
            {
                'fields': (
                    ('ch_componentes_obrigatorios', 'ch_especifica'),
                )
            },
        ),
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
        self.message_user(request, 'Formação PPE cadastrada com sucesso. Por favor, vincule os cursos à Formação PPE.')
        return HttpResponseRedirect(f'/ppe/formacaoppe/{obj.pk}/')

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        url = '/admin/ppe/formacaoppe/?&ativo__exact=1'
        return HttpResponseRedirect(url)


admin.site.register(FormacaoPPE, FormacaoPPEAdmin)

#FES-37

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

admin.site.register(EstruturaCurso, EstruturaCursoAdmin)

#FES-39

class CursoAdmin(ModelAdminPlus):
    list_display = ('codigo', 'descricao', 'ativo')
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
        'codigo',
    )
    show_count_on_tabs = True
    form = CursoForm

    fieldsets = (
        ('Identificação',{'fields': (('descricao',),('descricao_historico',),)},),
        ('Dados da Criação', {'fields': ( ('data_inicio', 'data_fim'), 'ativo')}),
        ('Dados Gerais',{'fields': ('codigo', 'ch_total', 'ch_aula')},),
    )

    def get_queryset(self, request):
        queryset = super(CursoAdmin, self).get_queryset(request)
        return queryset

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        q = '?ativo__exact=1'
        return HttpResponseRedirect('/admin/ppe/curso/' + q)

    def response_add(self, request, obj):
        self.message_user(request, 'Curso cadastrado com sucesso. ')
        return HttpResponseRedirect('/admin/ppe/curso/{:d}/view'.format(obj.pk))


admin.site.register(Curso, CursoAdmin)



class TurmaAdmin(ModelAdminPlus):
    list_display = ('grupo','codigo', 'get_qtd_cursos', 'get_qtd_te')
    list_filter = (CustomTabListFilter, 'grupo' )

    list_display_icons = True
    export_to_xls = True
    list_xls_display = 'id', 'grupo', 'codigo',
    list_per_page = 15
    search_fields = ('grupo', 'codigo', 'id')
    form = TurmaPPEForm
    show_count_on_tabs = True

    def get_action_bar(self, request):
        items = super(self.__class__, self).get_action_bar(request, True)
        if request.user.has_perm('ppe.gerar_turmas'):
            items.append(dict(url='/ppe/gerar_turmas/', label='Gerar Turmas'))
            # items.append(dict(url='/edu/imprimir_horarios/', label='Imprimir Horários'))
        # if request.user.has_group_cached('Administrador Acadêmico'):
        #     items.append(
        #         dict(
        #             label='Ações para o TimeTables',
        #             subitems=[
        #                 dict(url='/static/edu/timetables/suap_edu.xml', label='Gerar o Arquivo de configuração do TimeTables'),
        #                 dict(url='/edu/exportar_xml_time_tables/', label='Exportar XML para o TimeTables'),
        #                 dict(url='/edu/importar_xml_time_tables/', label='Importar XML do TimeTables'),
        #             ],
        #         )
        #     )
        return items

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('correntes/', self.admin_site.admin_view(self.correntes))]
        return my_urls + urls

    def correntes(self, request):
        qs = self.get_queryset(request)
        if qs.exists():
            # ano = qs.latest('ano_letivo__ano').ano_letivo.id
            # # url = f'/admin/edu/turma/?ano_letivo__id__exact={ano}'
            url = '/admin/ppe/turma/'
        else:
            url = '/admin/ppe/turma/'
        return HttpResponseRedirect(url)


    def get_qtd_cursos(self, obj):
        return obj.cursoturma_set.order_by('id').count()
    get_qtd_cursos.short_description = 'Qtd de Cursos'

    def get_qtd_te(self, obj):
        return obj.trabalhadoreducando_set.all().count()
    get_qtd_te.short_description = 'Qtd de TE'

    def get_tabs(self, request):
        return ['tab_em_andamento', ]

    def tab_em_andamento(self, request, queryset):
        return queryset.em_andamento()

    tab_em_andamento.short_description = 'Em Andamento'

    def get_queryset(self, request):
        if in_group(request.user, ('Coordenador(a) PPE')):
            manager = Turma.objects
        else:
            manager = Turma.objects.none()
        return super().get_queryset(request, manager)

    def delete_view(self, request, object_id, extra_context=None):
        try:
            turma = Turma.objects.get(pk=object_id)
        except Turma.DoesNotExist:
            msg = 'A turma escolhida não pode ser encontrada.'
            messages.error(request, msg)
            return httprr('/admin/edu/turma/')
        if not request.POST:
            return super().delete_view(request, object_id, extra_context)
        elif request.POST and (in_group(request.user, ('Coordenador(a) PPE')) or turma.pode_ser_excluido()):
            return super().delete_view(request, object_id, extra_context)
        else:
            msg = 'Não é possível realizar a exclusão. Existem diários com alunos para esta turma.'
            messages.error(request, msg)
            return redirect('.')


admin.site.register(Turma, TurmaAdmin)

#FES-49

class AnamneseAdmin(ModelAdminPlus):
    search_fields = ('trabalhador_educando',)
    form = AnamneseForm
    export_to_xls = True

admin.site.register(Anamnese, AnamneseAdmin)

class TrabalhoAnteriorAoPPEAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

class MeioTransporteAdmin  (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

class ResideComAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

class MembrosCarteiraAssinadaAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

class ResidenciaSaneamentoBasicoAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

class ItensResidenciaAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

class ParticipacaoGruposSociaisAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

class CursosTrabalhadorEducandoAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

class RedeSocialAdmin (ModelAdminPlus):
    list_display_icons = True
    list_display = ['descricao']

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
        if obj and obj.curso_turma and obj.curso_turma.pode_ser_excluido():
            return True
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        result = super().change_view(request, object_id, form_url, extra_context)
        if not in_group(request.user, 'Coordenador(a) PPE'):
            obj = self.get_object(request, unquote(object_id))
            tutor_turma = TutorTurma.objects.filter(tutor__vinculo__user=request.user)
            if not tutor_turma or (obj and tutor_turma[0].tutor.pk not in obj.curso_turma.turma.tutorturma_set.values_list('tutor__id', flat=True).distinct()):
                raise PermissionDenied()
        return result

    @transaction.atomic
    def after_saving_model_and_related_inlines(self, obj):
        if not obj.pk == 1:
            for matricula_diario in obj.curso_turma.matriculacursoturma_set.all():
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

class SolicitacaoFilter(SimpleListFilter):
    title = 'tipo'
    parameter_name = 'tipo'

    def lookups(self, request, model_admin):
        return (('atendimentopsicossocial', 'Solicitação de Atendimento pelo Núcleo de Atenção Psicossocial'), ('continuidadeaperfeicoamentoprofissional', 'Solicitação de continuidade no Aperfeiçoamento Profissional'),
                ('ampliacaoprazocurso', 'Solicitação de ampliação de prazo para execução de curso'), ('realocacao', 'Solicitação de realocação'),('visita', 'Solicitação de visita técnica na unidade'),
                ('desligamento', 'Solicitação de Desligamento'))
    def queryset(self, request, queryset):
        if self.value() == 'atendimentopsicossocial':
            return queryset.filter(solicitacaoatendimentopsicossocial__isnull=False)
        if self.value() == 'continuidadeaperfeicoamentoprofissional':
            return queryset.filter(solicitacaocontinuidadeaperfeicoamentoprofissional__isnull=False)
        if self.value() == 'realocacao':
            return queryset.filter(solicitacaorealocacao__isnull=False)
        if self.value() == 'ampliacaoprazocurso':
            return queryset.filter(solicitacaoampliacaoprazocurso__isnull=False)
        if self.value() == 'visita':
            return queryset.filter(solicitacaovisitatecnicaunidade__isnull=False)
        if self.value() == 'desligamento':
            return queryset.filter(solicitacaodesligamentos__isnull=False)

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
        if self.show_actions and request.user.has_perm('ppe.change_solicitacaousuario'):
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
            url = '/ppe/rejeitar_solicitacao/{}/'.format('_'.join(ids))
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


class PerguntaAvaliacaoAdmin(ModelAdminPlus):
    list_display = ('ordem', 'tipo_avaliacao', 'formacao_tecnica', 'pergunta', 'tipo_resposta', 'obrigatoria', 'ativo')
    ordering = ('tipo_avaliacao', 'formacao_tecnica', 'pergunta')
    search_fields = ('pergunta__pergunta', 'descricao')
    list_filter = ('tipo_avaliacao','formacao_tecnica', 'tipo_resposta', 'obrigatoria', 'ativo')
    list_display_icons = True


admin.site.register(PerguntaAvaliacao, PerguntaAvaliacaoAdmin)


class OpcaoRespostaAvaliacaoAdmin(ModelAdminPlus):
    list_display = ('get_tipo_avalaicao', 'pergunta', 'valor', 'pontuacao','ativo')
    ordering = ('pergunta',)
    search_fields = ('pergunta__pergunta', 'valor', )
    list_filter = ('pergunta', 'ativo')
    list_display_icons = True
    form = OpcaoRespostaAvaliacaoForm

    def get_tipo_avalaicao(self, obj):
        return obj.pergunta.tipo_avaliacao.titulo

    get_tipo_avalaicao.short_description = 'Tipo Avaliação'

class TipoAvaliacaoAdmin(ModelAdminPlus):
    list_display = ('titulo', 'descricao', 'pre_requisito', 'ativo')
    ordering = ('titulo',)
    search_fields = ('titulo', 'descricao')
    list_display_icons = True
    form = TipoAvaliacaoForm
class AvaliacaoAdmin(ModelAdminPlus):
    list_display = ('get_tipo_avalaicao', 'trabalhador_educando', 'papel_avalidor','atualizado_por', 'data_atualizacao','get_validacao_supervidor', 'get_acoes')
    ordering = ('trabalhador_educando','tipo_avaliacao')
    search_fields = ('trabalhador_educando__pessoa_fisica__nome','papel_avalidor',)
    list_filter = ('tipo_avaliacao','papel_avalidor','trabalhador_educando__formacao_tecnica')
    list_display_icons = True

    def get_tipo_avalaicao(self, obj):
        return obj.tipo_avaliacao

    get_tipo_avalaicao.short_description = 'Avaliação'
    def get_validacao_supervidor(self, obj):
        html = []

        if obj.papel_avalidor == Avaliacao.AVALIACAO_CHEFIA and obj.data_validacao:
            html.append('<strong>Validada:</strong> ')
            html.append('Sim' if obj.aprovada else 'Não')
            html.append('<br/>')
            html.append('<strong>Validada por:</strong> ')
            html.append(str(obj.supervisor.get_vinculo().pessoa.nome) if obj.supervisor else '')
            html.append('<br/>')
            html.append('<strong>Validada em:</strong> ')
            html.append(str(obj.data_validacao.strftime("%d/%m/%y")))
            html.append('<br/>')

        return mark_safe(' '.join(html))

    get_validacao_supervidor.short_description = 'Validação Supervidor'

    def get_acoes(self, obj):
        mostra_acoes = ''
        if self.has_view_permission(self.request, obj):
            mostra_acoes += icon('download', f'/ppe/gerar_pdf_trabalhador_educando_resumo/{obj.id}/')
        return mark_safe(mostra_acoes)

    get_acoes.short_description = 'Ações'

    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False




class EtapaMonitoramentoInline(admin.TabularInline):
    model = EtapaMonitoramento
    form = EtapaMonitoramentoForm
    extra = 1


class ConfiguracaoMonitoramentoAdmin(ModelAdminPlus):
    list_filter = ('ano',)
    list_display = ('ano',)
    list_display_icons = True
    search_fields = ('ano',)
    ordering = ('ano',)
    inlines = [EtapaMonitoramentoInline]


class SetorAdmin(ModelAdminPlus):
    form = SetorForm
    add_form = SetorAddForm
    list_display = ("show_info_principal", "get_chefes", )
    list_filter = ("unidade", "excluido", )
    list_display_icons = True
    list_per_page = 20
    export_to_xls = True
    ordering = ("sigla", "nome")
    search_fields = ("sigla", "nome", "codigo")
    # inlines = [SetorTelefoneInline]

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        self.list_filter = list_filter if request.user.is_superuser else list_filter
        return self.list_filter

    def restringir_queryset(self, request):
        """
        Superusuários podem ver todos os setores, os outros apenas os SUAP.
        """
        return Setor.objects

    get_queryset = restringir_queryset

    def show_info_principal(self, obj):
        # Principal
        out = [
            """
        <p><strong>%(sigla)s</strong> (%(nome)s)</p>
        <p>%(caminho)s</p>"""
            % dict(sigla=obj.sigla, caminho=obj.get_caminho_as_html(), nome=obj.nome)
        ]

        return mark_safe("".join(out))

    show_info_principal.short_description = "Informações Principais"
    show_info_principal.admin_order_field = "sigla"


    # def get_qtd_servidores(self, obj):
    #
    #     # Servidores
    #     qtd_servidores = Servidor.objects.filter(excluido=False, setor=obj).count()
    #     if qtd_servidores == 0:
    #         info_servidores = '<span class="status status-error">Nenhum servidor</span>'
    #     else:
    #         info_servidores = """
    #         <a href="/admin/rh/servidor/?excluido__exact=0&setor__id__exact=%d"
    #            title="Listar servidores">
    #             %d servidor%s
    #         </a>""" % (
    #             obj.pk,
    #             qtd_servidores,
    #             qtd_servidores > 1 and "es" or "",
    #         )
    #     return mark_safe("%(info_servidores)s" % dict(info_servidores=info_servidores))
    #
    # get_qtd_servidores.short_description = "Qtd. de Servidores"

    def get_chefes(self, obj):
        out = []
        for chefia in ChefiaPPE.objects.filter(pk__in=obj.historico_funcao().values_list("chefe_imediato", flat=True).distinct()):
            out.append(f"<li>{format_user(chefia.get_user())}</li>")
        return mark_safe("<ul>{}</ul>".format("".join(out)))

    get_chefes.short_description = "Chefes"

    def get_form(self, request, obj=None, **kwargs):
        if request.user.is_superuser:
            kwargs["exclude"] = []
        else:
            kwargs["exclude"] = ["codigo"]
        return super().get_form(request, obj=obj, **kwargs)

    # def to_xls(self, request, queryset, task):
    #     header = ["#", "Setor", "Campus", "Telefones", "Chefes do Setor", "Tipo de Jornada Trabalho", "Quantidade de Servidores"]
    #     rows = [header]
    #     for idx, obj in enumerate(task.iterate(queryset)):
    #         uo = obj.uo
    #         row = [
    #             idx + 1,
    #             f"{obj.nome} ({obj.sigla})",
    #             f"{obj.uo.nome} ({obj.uo.sigla})" if uo else "",
    #             ",".join([f"{st.numero}(ramal:{st.ramal})" for st in obj.setortelefone_set.all()]),
    #             ",".join([str(chefe) for chefe in obj.chefes.all()]),
    #             obj.tipo_jornada_trabalho_por_data(),
    #             Servidor.objects.filter(excluido=False, setor=obj).count(),
    #         ]
    #         rows.append(row)
    #     return rows


class UnidadeAdmin(ModelAdminPlus):
    list_display = ("id", "nome", "sigla", "setor", "municipio")
    search_fields = ("setor__sigla", "setor__nome")
    list_display_icons = True

    def has_change_permission(self, request, obj=None):
        if in_group(request.user, 'Coordenador(a) PPE'):
            return True
        return False

    def get_queryset(self, request, manager=None, *args, **kwargs):
        queryset = Unidade.objects
        return queryset

    def get_form(self, request, obj=None, **kwargs):
        setor_qs = Setor.objects.all()
        help_text = "Favor cadastar um setor com a mesma sigla da unidade."
        self.fieldsets = (
            ("Dados Gerais", {"fields": (("nome", "sigla"), ("setor", "cnpj"),)}),
            ("Endereço", {"fields": (("endereco", "numero"), ("municipio", "zona_rual"), ("cep", "bairro"))}),
            ("Contato", {"fields": (("telefone", "fax"),)}),
        )

        class UnidadeForm(forms.ModelFormPlus):
            class Meta:
                model = Unidade
                exclude = ()

            setor = forms.ModelChoiceFieldPlus2(
                queryset=setor_qs, help_text=help_text, label_template="{{ obj }} ({% if obj.codigo %}SIAPE{% else %}SUAP{% endif %})"
            )


        return UnidadeForm

class TrabalhadorSetorHistoricoAdmin(ModelAdminPlus):
    form = TrabalhadorSetorHistoricoForm
    list_display = ("trabalhador_educando", "setor", "data_inicio", "data_fim")
    list_filter = ["setor"]
    search_fields = ["trabalhador_educando__nome", "trabalhador_educando__matricula", "setor__nome"]
    list_per_page = 20
    list_display_icons = True

    ordering = ("-data_inicio", "data_fim")

class ChefiaSetorHistoricoAdmin(ModelAdminPlus):
    list_display = (
        "chefe_imediato",
        "data_inicio_funcao",
        "data_fim_funcao",
        "setor"
    )
    form = ChefiaSetorHistoricoForm
    ordering = ("-data_inicio_funcao",)
    search_fields = ("chefe_imediato__nome", "chefe_imediato__matricula")
    list_display_icons = True
    date_hierarchy = "data_inicio_funcao"


admin.site.register(ChefiaSetorHistorico, ChefiaSetorHistoricoAdmin)
admin.site.register(TrabalhadorSetorHistorico, TrabalhadorSetorHistoricoAdmin)
admin.site.register(Unidade, UnidadeAdmin)
admin.site.register(Setor, SetorAdmin)
admin.site.register(ConfiguracaoMonitoramento, ConfiguracaoMonitoramentoAdmin)
admin.site.register(Avaliacao, AvaliacaoAdmin)
admin.site.register(TipoAvaliacao, TipoAvaliacaoAdmin)
admin.site.register(OpcaoRespostaAvaliacao, OpcaoRespostaAvaliacaoAdmin)
admin.site.register(TrabalhoAnteriorAoPPE, TrabalhoAnteriorAoPPEAdmin)
admin.site.register(MeioTransporte, MeioTransporteAdmin)
admin.site.register(ResideCom, ResideComAdmin)
admin.site.register(MembrosCarteiraAssinada, MembrosCarteiraAssinadaAdmin)
admin.site.register(ResidenciaSaneamentoBasico, ResidenciaSaneamentoBasicoAdmin)
admin.site.register(ItensResidencia, ItensResidenciaAdmin)
admin.site.register(ParticipacaoGruposSociais, ParticipacaoGruposSociaisAdmin)
admin.site.register(CursosTrabalhadorEducando, CursosTrabalhadorEducandoAdmin)
admin.site.register(RedeSocial, RedeSocialAdmin)
admin.site.register(ConfiguracaoAvaliacao, ConfiguracaoAvaliacaoAdmin)
admin.site.register(SolicitacaoUsuario, SolicitacaoUsuarioAdmin)
admin.site.register(FormacaoTecnica, FormacaoTecnicaAdmin)
admin.site.register(TrabalhadorEducando, TrabalhadorEducandoAdmin)
admin.site.register(ChefiaPPE, ChefiaPPEAdmin)
