# -*- coding: utf-8 -*-
import datetime

from django.contrib import admin
from django.utils.safestring import mark_safe

from djtools.contrib.admin import ModelAdminPlus
from djtools.templatetags.filters import status, format_
from rh.models import UnidadeOrganizacional
from temp_rh2.forms import CompeticoesDesportivasForm, ModalidadeDesportivaForm
from temp_rh2.models import (
    CompeticaoDesportiva,
    ModalidadeDesportiva,
    InscricaoCompeticaoDesportiva,
    Prova,
    Categoria,
    CursoSuap,
    InscricaoCursoSuap,
    LogInscricaoCursoSuap,
    ConteudoEmail,
)
from djtools.templatetags.filters import in_group


class CompeticaoDesportivaAdmin(ModelAdminPlus):
    list_filter = ('ano', 'nome')
    list_display = ('ano', 'nome')
    form = CompeticoesDesportivasForm
    fieldsets = (
        ("Competição", {'fields': ('nome', 'descricao', 'ano', 'uo')}),
        (
            "Configuração da Competição",
            {
                'fields': (
                    'modalidades',
                    'max_modalidades_coletivas_por_inscricao',
                    'max_modalidades_por_inscricao',
                    'max_modalidades_individuais_por_inscricao',
                    'provas_natacao',
                    'max_provas_natacao',
                    'provas_atletismo',
                    'max_provas_atletismo',
                    'provas_jogos_eletronicos',
                    'max_provas_jogos_eletronicos',
                    'categorias',
                )
            },
        ),
        (
            "Datas Importantes",
            {
                'fields': (
                    ('data_inicio_periodo_inscricoes', 'data_fim_periodo_inscricoes'),
                    ('data_inicio_periodo_validacao', 'data_fim_periodo_validacao'),
                    ('data_inicio_confirmacao_inscritos', 'data_fim_confirmacao_inscritos'),
                    ('data_inicio_reajustes', 'data_fim_reajustes'),
                    ('data_homologacao_inscricoes',),
                )
            },
        ),
        ("Datas Jogos", {'fields': (('data_inicio_periodo1_jogos', 'data_fim_periodo1_jogos'), ('data_inicio_periodo2_jogos', 'data_fim_periodo2_jogos'))}),
    )


admin.site.register(CompeticaoDesportiva, CompeticaoDesportivaAdmin)


class ServidorUoFilter(admin.SimpleListFilter):
    title = "Campus Servidor"
    parameter_name = "uo"

    def lookups(self, request, model_admin):
        return UnidadeOrganizacional.objects.suap().all().values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            if UnidadeOrganizacional.objects.suap().filter(pk=request.GET.get('uo')).exists():
                return queryset.filter(servidor__setor__uo__id__exact=self.value())
            else:
                self.used_parameters.pop(self.parameter_name)
        return queryset


class ProvasIndividuaisFilter(admin.SimpleListFilter):
    title = "Provas Individuais"
    parameter_name = "prova"

    def lookups(self, request, model_admin):
        provas = Prova.objects.all()
        return [(d.id, '{} - {}'.format(d.modalidade, d.nome)) for d in provas]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(provas_atletismo=self.value()) | queryset.filter(provas_natacao=self.value()) | queryset.filter(provas_jogos_eletronicos=self.value())
        return queryset


class InscricaoCompeticaoDesportivaAdmin(ModelAdminPlus):
    list_filter = (
        'competicao_desportiva',
        'uo',
        ServidorUoFilter,
        'servidor__sexo',
        'preferencia_camisa',
        'preferencia_short',
        'termo_recebimento_hospedagem',
        'modalidades',
        ProvasIndividuaisFilter,
        'categoria',
        'situacao',
    )
    list_display = (
        'competicao_desportiva',
        'get_servidor',
        'uo',
        'get_uo',
        'get_modalidades_inscritas',
        'categoria',
        'get_outras_informacoes',
        'termo_recebimento_hospedagem',
        'get_situacao',
        'get_acoes',
        'get_atestado',
    )

    export_to_xls = True
    list_display_icons = True

    def get_atestado(self, obj):
        retorno = ''
        if obj.atestado_medico:
            retorno = mark_safe('<a href="{}">Atestado médico anexado</a>'.format(obj.atestado_medico.url))
        return retorno

    get_atestado.short_description = 'Atestado Médico'

    def get_servidor(self, obj):
        return mark_safe('{}'.format(format_(obj.servidor)))

    get_servidor.admin_order_field = 'servidor'
    get_servidor.short_description = 'Servidor'

    def get_outras_informacoes(self, obj):
        retorno = '<ul>'
        retorno += '<li> Camisa : {}</li>'.format(obj.get_preferencia_camisa_display())
        retorno += '<li> Short : {}</li>'.format(obj.get_preferencia_short_display())
        retorno += '</ul>'
        return mark_safe(retorno)

    get_outras_informacoes.short_description = 'Tamanhos do Uniforme'

    def get_modalidades_inscritas(self, obj):
        retorno = '<ul>'
        for modalidade in obj.modalidades.only('pk', 'nome'):
            if modalidade.pk == ModalidadeDesportiva.CODIGO_ATLETISMO:
                if obj.provas_atletismo.all().exists():
                    retorno += '<li class="has-child">{}'.format(modalidade.nome)
                    retorno += '<ul>'
                    for prova_atletismo in obj.provas_atletismo.all().values_list('nome', flat=True):
                        retorno += '<li>{}</li>'.format(prova_atletismo)
                    retorno += '</ul>'
                else:
                    retorno += '<li>{}'.format(modalidade)
                retorno += '</li>'
            elif modalidade.pk == ModalidadeDesportiva.CODIGO_NATACAO:
                retorno += '<li>{}'.format(modalidade.nome)
                if obj.provas_natacao.all().exists():
                    retorno += '<ul>'
                    for prova_natacao in obj.provas_natacao.all().values_list('nome', flat=True):
                        retorno += '<li>{}</li>'.format(prova_natacao)
                    retorno += '</ul>'
                retorno += '</li>'
            elif modalidade.pk == ModalidadeDesportiva.CODIGO_JOGOS_ELETRONICOS:
                retorno += '<li>{}'.format(modalidade.nome)
                if obj.provas_jogos_eletronicos.all().exists():
                    retorno += '<ul>'
                    for prova_jogos_eletronicos in obj.provas_jogos_eletronicos.all().values_list('nome', flat=True):
                        retorno += '<li>{}</li>'.format(prova_jogos_eletronicos)
                    retorno += '</ul>'
                retorno += '</li>'
            else:
                retorno += '<li>{}</li>'.format(modalidade.nome)
        retorno += '</ul>'
        return mark_safe(retorno)

    get_modalidades_inscritas.short_description = 'Modalidades'

    def get_uo(self, obj):
        if obj.servidor.setor:
            return mark_safe(obj.servidor.setor.uo)
        return 'Sem campus'

    get_uo.admin_order_field = 'servidor__setor__uo'
    get_uo.short_description = 'Campus do Servidor'

    def get_situacao(self, obj):
        if obj.situacao:
            return mark_safe(status(obj.get_situacao_display()))
        return '-'

    get_situacao.admin_order_field = 'situacao'
    get_situacao.short_description = 'Situação'

    def get_acoes(self, obj):
        txt = ''
        usuario_logado = self.request.user
        servidor_logado = usuario_logado.get_relacionamento()
        hoje = datetime.date.today()
        campus_servidor_logado = None
        if servidor_logado.setor:
            campus_servidor_logado = servidor_logado.setor.uo
        if (usuario_logado.has_perm('temp_rh2.pode_validar_inscricaocompeticaodesportiva') and campus_servidor_logado == obj.uo) or usuario_logado.has_perm(
            'temp_rh2.change_inscricaocompeticaodesportiva'
        ):
            if (obj.competicao_desportiva.data_inicio_periodo_validacao <= hoje <= obj.competicao_desportiva.data_fim_periodo_validacao) or (
                obj.competicao_desportiva.data_inicio_confirmacao_inscritos <= hoje <= obj.competicao_desportiva.data_fim_confirmacao_inscritos
            ):
                txt += '<a class="btn popup" href="/temp_rh2/validar/{}/">Avaliar</a>'.format(obj.pk)
            elif (obj.competicao_desportiva.data_inicio_reajustes <= hoje <= obj.competicao_desportiva.data_fim_reajustes) or (
                hoje == obj.competicao_desportiva.data_homologacao_inscricoes
            ):
                txt += '<a class="btn popup success" href="/temp_rh2/validar/{}/">Homologar</a>'.format(obj.pk)
        return mark_safe(txt)

    get_acoes.short_description = 'Opções'

    def to_xls(self, request, queryset, processo):
        rows = [[]]
        if request.user.has_perm('temp_rh2.add_competicaodesportiva'):
            header = [
                '#',
                'Competição',
                'Matrícula',
                'cpf',
                'Nome',
                'Data de Nascimento',
                'E-mail para contato',
                'Campus Lotado',
                'Campus Inscrito',
                'Sexo',
                'Tamanho da Camisa',
                'Tamanho do Short',
                'Deseja receber Hospedagem',
                'Situação',
                'Modalidades',
                'Provas de Atletismo',
                'Provas de Natação',
                'Provas Jogos Eletrônicos',
            ]

            rows = [header]
            queryset = queryset.order_by('servidor__pessoafisica_ptr__nome')
            for idx, obj in enumerate(queryset, 1):
                row = [
                    idx,
                    obj.competicao_desportiva,
                    obj.servidor.matricula,
                    obj.servidor.pessoa_fisica.cpf,
                    obj.servidor.nome,
                    obj.servidor.nascimento_data,
                    obj.servidor.email,
                    self.get_uo(obj),
                    obj.uo,
                    obj.servidor.sexo,
                    obj.get_preferencia_camisa_display(),
                    obj.get_preferencia_short_display(),
                    'Sim' if obj.termo_recebimento_hospedagem else 'Não',
                    obj.get_situacao_display(),
                    ', '.join(obj.modalidades.all().values_list('nome', flat=True)),
                    ', '.join(obj.provas_atletismo.all().values_list('nome', flat=True)),
                    ', '.join(obj.provas_natacao.all().values_list('nome', flat=True)),
                    ', '.join(obj.provas_jogos_eletronicos.all().values_list('nome', flat=True)),
                ]
                rows.append(row)
        return rows


admin.site.register(InscricaoCompeticaoDesportiva, InscricaoCompeticaoDesportivaAdmin)


class ProvaInline(admin.StackedInline):
    model = Prova
    fields = ('nome',)
    extra = 1


class ModalidadeDesportivaAdmin(ModelAdminPlus):
    list_filter = ('nome',)
    form = ModalidadeDesportivaForm
    inlines = [ProvaInline]


admin.site.register(ModalidadeDesportiva, ModalidadeDesportivaAdmin)


class CategoriaAdmin(ModelAdminPlus):
    list_filter = ('nome', 'idade_inferior', 'idade_superior', 'excluido')


admin.site.register(Categoria, CategoriaAdmin)


class CursoSuapAdmin(ModelAdminPlus):
    list_display = ('sigla', 'denominacao', 'data_inicio_periodo_inscricoes', 'data_fim_periodo_inscricoes', 'ativo')


admin.site.register(CursoSuap, CursoSuapAdmin)


class InscricaoCursoSuapAdmin(ModelAdminPlus):
    list_display = (
        'id',
        'curso',
        'usuario',
        'data',
        'get_email',
        'get_username',
        'get_logado_campus_sigla',
        'get_eh_rh_sistemico',
        'get_eh_rh_campus',
        'enviou_email_solinsc',
        'data_confirmacao_inscricao',
        'solicitou_diaria',
        'get_acoes',
    )
    list_filter = ('curso', 'enviou_email_solinsc', 'data_confirmacao_inscricao', 'solicitou_diaria')
    change_list_template = 'temp_rh2/templates/admin/change_list_inscricao.html'
    search_fields = ['usuario__username', 'usuario__email']

    def get_email(self, obj):
        return obj.usuario.email

    get_email.short_description = 'Email'

    def get_username(self, obj):
        return obj.usuario.username

    get_username.short_description = 'Usuário'

    def get_logado_campus_sigla(self, obj):
        return obj.usuario.get_relacionamento().setor.uo.sigla

    get_logado_campus_sigla.short_description = 'Campus'

    def get_eh_rh_sistemico(self, obj):
        return in_group(obj.usuario, 'Coordenador de Gestão de Pessoas Sistêmico')

    get_eh_rh_sistemico.short_description = 'RH Sistêmico'

    def get_eh_rh_campus(self, obj):
        return in_group(obj.usuario, 'Coordenador de Gestão de Pessoas')

    get_eh_rh_campus.short_description = 'Coordenador RH Campus'

    def get_acoes(self, obj):
        retorno = '<a class="btn danger" href="/temp_rh2/enviar_email_confirmacao/{}/">Enviar Email de Confirmação</a>'.format(obj.pk)
        return mark_safe(retorno)

    get_acoes.short_description = 'Ações'


admin.site.register(InscricaoCursoSuap, InscricaoCursoSuapAdmin)


class LogInscricaoCursoSuapAdmin(ModelAdminPlus):
    pass


admin.site.register(LogInscricaoCursoSuap, LogInscricaoCursoSuapAdmin)


class ConteudoEmailAdmin(ModelAdminPlus):
    list_display = ('assunto',)


admin.site.register(ConteudoEmail, ConteudoEmailAdmin)
