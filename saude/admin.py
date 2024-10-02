import datetime

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.safestring import mark_safe

from ae.models import Participacao, Caracterizacao
from comum.models import Ano, UsuarioGrupo, Vinculo
from comum.utils import get_uo
from djtools.contrib.admin import ModelAdminPlus
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from edu.models import Modalidade, Aluno, SituacaoMatricula
from rh.models import UnidadeOrganizacional, Setor, Servidor
from saude.forms import AtividadeGrupoForm, MetaAcaoEducativaForm, RegistroAdministrativoForm, PlanoAlimentarForm, ProcedimentoOdontologiaForm
from saude.models import (
    Prontuario,
    Doenca,
    Vacina,
    DificuldadeOral,
    MetodoContraceptivo,
    Droga,
    ProcedimentoEnfermagem,
    Cid,
    Anamnese,
    Especialidades,
    Atendimento,
    AtividadeGrupo,
    TipoAtividadeGrupo,
    TipoAtendimento,
    TipoExameLaboratorial,
    CategoriaExameLaboratorial,
    MotivoChegadaPsicologia,
    QueixaPsicologica,
    ProcedimentoMultidisciplinar,
    Antropometria,
    SinaisVitais,
    AntecedentesFamiliares,
    HabitosDeVida,
    DesenvolvimentoPessoal,
    AnoReferenciaAcaoEducativa,
    ObjetivoAcaoEducativa,
    MetaAcaoEducativa,
    MotivoAtendimentoNutricao,
    AvaliacaoGastroIntestinal,
    RestricaoAlimentar,
    DiagnosticoNutricional,
    OrientacaoNutricional,
    ReceitaNutricional,
    FrequenciaPraticaAlimentar,
    PerguntaMarcadorNutricao,
    OpcaoRespostaMarcadorNutricao,
    PlanoAlimentar,
    RegistroAdministrativo,
    BloqueioAtendimentoSaude,
    AtendimentoEspecialidade,
    ProcedimentoOdontologia,
    ProcedimentoIndicado,
    SituacaoAtendimento, PassaporteVacinalCovid, HistoricoValidacaoPassaporte, ResultadoTesteCovid, Sintoma,
    NotificacaoCovid, ValidadorIntercampi,
)


class ProntuarioAdmin(ModelAdminPlus):
    def response_add(self, request, obj):
        return httprr('/saude/prontuarios/', 'Prontuário cadastrado com sucesso.')


admin.site.register(Prontuario, ProntuarioAdmin)


class DoencaAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_display = ('nome', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(Doenca, DoencaAdmin)


class DrogaAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_display = ('nome', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(Droga, DrogaAdmin)


class MetodoContraceptivoAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_display = ('nome', 'ativo')
    ordering = ('nome',)
    list_display_icons = True


admin.site.register(MetodoContraceptivo, MetodoContraceptivoAdmin)


class DificuldadeOralAdmin(ModelAdminPlus):
    search_fields = ('dificuldade',)
    list_display = ('dificuldade', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(DificuldadeOral, DificuldadeOralAdmin)


class VacinaAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_display = ('nome', 'doses', 'ativa', 'eh_covid')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(Vacina, VacinaAdmin)


class ProcedimentoEnfermagemAdmin(ModelAdminPlus):
    search_fields = ('denominacao',)
    list_display = ('denominacao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(ProcedimentoEnfermagem, ProcedimentoEnfermagemAdmin)


class CidAdmin(ModelAdminPlus):
    search_fields = ('codigo', 'denominacao')
    list_display = ('codigo', 'denominacao', 'ativo')
    ordering = ('codigo', 'denominacao')
    list_display_icons = True


admin.site.register(Cid, CidAdmin)


class AnamneseAdmin(ModelAdminPlus):
    search_fields = ('hda',)
    list_display = ('atendimento', 'profissional', 'data_cadastro', 'hda', 'gravida')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(Anamnese, AnamneseAdmin)


class CampusFilter(admin.SimpleListFilter):
    title = "Campus do Atendimento"
    parameter_name = 'campus'

    def lookups(self, request, model_admin):
        if request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
            uo = UnidadeOrganizacional.objects.uo().all()
        else:
            uo = UnidadeOrganizacional.objects.uo().filter(pk=get_uo(request.user).id)
        return uo.values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(usuario_aberto__vinculo__setor__uo=self.value())


class CampusPacienteFilter(admin.SimpleListFilter):
    title = "Campus do Paciente"
    parameter_name = 'campus_paciente'

    def lookups(self, request, model_admin):
        if request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
            uo = UnidadeOrganizacional.objects.uo().all()
        else:
            uo = UnidadeOrganizacional.objects.uo().filter(pk=get_uo(request.user).id)
        return uo.values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            alunos_do_campus = Aluno.objects.filter(situacao=SituacaoMatricula.MATRICULADO, curso_campus__diretoria__setor__uo=self.value())
            return queryset.filter(prontuario__vinculo__setor__uo=self.value()) | queryset.filter(
                prontuario__vinculo__pessoa__pessoafisica__in=alunos_do_campus.values_list('pessoa_fisica', flat=True)
            )


class CategoriaFilter(admin.SimpleListFilter):
    title = "Categoria"
    parameter_name = "categoria"

    def lookups(self, request, model_admin):
        opcoes = Atendimento.CATEGORIAS_VINCULO
        return opcoes

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(aluno__isnull=False)
        elif self.value() == '2':
            return queryset.filter(servidor__isnull=False)
        elif self.value() == '3':
            return queryset.filter(prestador_servico__isnull=False)
        elif self.value() == '4':
            return queryset.filter(pessoa_externa__isnull=False)


class TipoFilter(admin.SimpleListFilter):
    title = "Tipo"
    parameter_name = "tipo"

    def lookups(self, request, model_admin):
        opcoes = (
            ('1', 'Avaliação Biomédica'),
            ('2', 'Atendimento Médico'),
            ('3', 'Atendimento de Enfermagem'),
            ('4', 'Atendimento Odontológico'),
            ('5', 'Atendimento Psicológico'),
            ('6', 'Atendimento Nutricional'),
            ('7', 'Atendimento de Fisioterapia'),
            ('8', 'Atendimento Multidisciplinar'),
        )
        return opcoes

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(tipo=TipoAtendimento.AVALIACAO_BIOMEDICA)
        elif self.value() == '2':
            return queryset.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO, condutamedica__isnull=False).distinct()
        elif self.value() == '3':
            return queryset.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO, intervencaoenfermagem__isnull=False).distinct()
        elif self.value() == '4':
            return queryset.filter(tipo=TipoAtendimento.ODONTOLOGICO)
        elif self.value() == '5':
            return queryset.filter(tipo=TipoAtendimento.PSICOLOGICO)
        elif self.value() == '6':
            return queryset.filter(tipo=TipoAtendimento.NUTRICIONAL)
        elif self.value() == '7':
            return queryset.filter(tipo=TipoAtendimento.FISIOTERAPIA)
        elif self.value() == '8':
            return queryset.filter(tipo=TipoAtendimento.MULTIDISCIPLINAR)


class ModalidadeFilter(admin.SimpleListFilter):
    title = "Modalidade"
    parameter_name = "modalidade"

    def lookups(self, request, model_admin):
        opcoes = Modalidade.objects.all()
        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(aluno__curso_campus__modalidade=self.value())


class AntropometriaFilter(admin.SimpleListFilter):
    title = "Incluir Antropometria no Excel"
    parameter_name = "antropometria"

    def lookups(self, request, model_admin):
        opcoes = (('Sim', 'Sim'), ('Não', 'Não'))

        return opcoes

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'Sim':
                return queryset.filter(aluno__in=Antropometria.objects.all().values_list('atendimento__aluno', flat=True))
            elif self.value() == 'Não':
                return queryset.exclude(aluno__in=Antropometria.objects.all().values_list('atendimento__aluno', flat=True))


class ParticipanteAssistenciaFilter(admin.SimpleListFilter):
    title = "Participantes de Programas da Assistência Estudantil"
    parameter_name = "modalidade"

    def lookups(self, request, model_admin):
        opcoes = (('Sim', 'Sim'), ('Não', 'Não'))
        return opcoes

    def queryset(self, request, queryset):
        if self.value():
            hoje = datetime.datetime.today()
            participantes = Participacao.objects.filter(Q(data_inicio__lte=hoje), Q(data_termino__gte=hoje) | Q(data_termino__isnull=True))
            if self.value() == 'Sim':
                return queryset.filter(aluno__in=participantes.values_list('aluno', flat=True))
            elif self.value() == 'Não':
                return queryset.exclude(aluno__in=participantes.values_list('aluno', flat=True))


class AtendimentoAdmin(ModelAdminPlus):
    list_display = ('get_tipo_paciente', 'tipo', 'get_situacao_display', 'data_aberto', 'get_participa_programa_estudantil', 'get_responsaveis', 'get_visualizar_prontuario')
    list_filter = (CampusFilter, CampusPacienteFilter, TipoFilter, CategoriaFilter, 'situacao', ParticipanteAssistenciaFilter, 'usuario_aberto')
    search_fields = (
        'aluno__matricula',
        'aluno__pessoa_fisica__nome',
        'prontuario__vinculo__pessoa__pessoafisica__nome',
        'prontuario__vinculo__pessoa__pessoafisica__cpf',
        'usuario_aberto__vinculo__pessoa__nome',
    )
    ordering = ('-data_aberto', 'tipo')
    date_hierarchy = 'data_aberto'
    list_display_links = None
    export_to_xls = True

    def to_xls(self, request, queryset, processo):
        exibir_dados_antropometria = request.GET.get('antropometria') and request.GET.get('antropometria') == 'Sim'
        if exibir_dados_antropometria:
            header = [
                '#',
                'Paciente',
                'Tipo',
                'Situação',
                'Data da Abertura',
                'Participação em Programas de Atividades Estudantis',
                'Aberto Por',
                'Data de nascimento',
                'Sexo',
                'Telefone',
                'E-mail',
                'Renda Familiar',
                'Moradia',
                'Pessoas na residência',
                'Escolaridade da mãe',
                'Escolaridade do pai',
                'Etnia',
                'Portador de necessidades especiais',
                'Situação',
                'Curso',
                'Pressão arterial',
                'Estatura',
                'Peso',
                'Circunferência da Cintura',
                'Circunferência do Quadril',
                'Circunferência do Braço',
                'Dobra Cutânea Tricipital',
                'Dobra Cutânea Bicipital',
                'Dobra Cutânea Subescapular',
                'Dobra Cutânea Suprailíaca',
                'Percentual de Gordura',
                'Perda de peso',
                'Ganho de peso',
                'Agravos à saúde com parentesco de 1º grau',
                'Prática de atividade física',
                'Tem dificuldade para dormir',
                'Horas de sono diárias',
                'Refeições por dia',
                'Já teve algum problema de aprendizado',
            ]
        else:
            header = ['#', 'Paciente', 'Tipo', 'Situação', 'Data da Abertura', 'Participação em Programas de Atividades Estudantis', 'Aberto Por']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            aluno = obj.aluno
            if obj.situacao == 1:
                situacao = 'Aberto'
            elif obj.situacao == 2:
                situacao = 'Fechado'
            else:
                situacao = 'Cancelado'

            if aluno:
                hoje = datetime.date.today()
                participacoes_ativas = Participacao.objects.filter(aluno=aluno).filter(Q(data_termino__gte=hoje) | Q(data_termino__isnull=True))
                if participacoes_ativas.exists():
                    lista = list()
                    for item in participacoes_ativas:
                        lista.append(str(item.programa))
                    participante = ', '.join(lista)
                else:
                    participante = 'Não participante'
            else:
                participante = '-'
            pessoa_fisica = obj.get_pessoa_fisica_vinculo()
            if exibir_dados_antropometria:
                sexo = ''
                data_nascimento = pessoa_fisica.nascimento_data
                if pessoa_fisica.sexo == "M":
                    sexo = 'Masculino'
                elif pessoa_fisica.sexo == "F":
                    sexo = 'Feminino'

                renda_familiar = ''
                moradia = ''
                qtd_pessoas_domicilio = ''
                escolaridade_mae = ''
                escolaridade_pai = ''
                raca = ''
                necessidade_especial = ''
                caracterizacao = Caracterizacao.objects.filter(aluno=aluno).order_by('-id')
                if caracterizacao.exists():
                    renda_familiar = caracterizacao[0].renda_bruta_familiar
                    moradia = caracterizacao[0].tipo_imovel_residencial
                    qtd_pessoas_domicilio = caracterizacao[0].qtd_pessoas_domicilio
                    escolaridade_mae = caracterizacao[0].mae_nivel_escolaridade.descricao
                    escolaridade_pai = caracterizacao[0].pai_nivel_escolaridade.descricao
                    raca = caracterizacao[0].raca
                    necessidade_especial = caracterizacao[0].necessidade_especial

                pressao = ''
                sinais = SinaisVitais.objects.filter(atendimento__aluno=aluno, pressao_sistolica__isnull=False, pressao_diastolica__isnull=False).order_by('id')
                if sinais.exists():
                    pressao = f'{sinais[0].pressao_sistolica}x{sinais[0].pressao_diastolica} mmHg'

                antropometria = Antropometria.objects.filter(atendimento__aluno=aluno).order_by('id')
                estatura = peso = cintura = quadril = circunferencia_braco = pc_triciptal = pc_biciptal = pc_subescapular = pc_suprailiaca = percentual_gordura = ''
                perda_peso_total = ganho_peso_total = ''
                if antropometria.exists():
                    estatura = antropometria[0].estatura
                    peso = antropometria[0].peso
                    cintura = antropometria[0].cintura
                    quadril = antropometria[0].quadril
                    circunferencia_braco = antropometria[0].circunferencia_braco
                    pc_triciptal = antropometria[0].pc_triciptal
                    pc_biciptal = antropometria[0].pc_biciptal
                    pc_subescapular = antropometria[0].pc_subescapular
                    pc_suprailiaca = antropometria[0].pc_suprailiaca
                    percentual_gordura = antropometria[0].percentual_gordura
                    perda_peso = antropometria[0].perda_peso
                    quanto_perdeu = antropometria[0].quanto_perdeu
                    tempo_perda = antropometria[0].tempo_perda

                    if perda_peso:
                        perda_peso_total = f'{quanto_perdeu} Kg há {tempo_perda} dias'

                    ganho_peso = antropometria[0].ganho_peso
                    quanto_ganhou = antropometria[0].quanto_ganhou
                    tempo_ganho = antropometria[0].tempo_ganho
                    ganho_peso_total = ''
                    if ganho_peso:
                        ganho_peso_total = f'{quanto_ganhou} Kg há {tempo_ganho} dias'

                antecedentes = ''
                tem_antecedentes = AntecedentesFamiliares.objects.filter(atendimento__aluno=aluno, agravos_primeiro_grau__isnull=False).order_by('id')
                if tem_antecedentes.exists():
                    lista = list()
                    for item in tem_antecedentes[0].agravos_primeiro_grau.all():
                        lista.append(item.nome)
                    antecedentes = ', '.join(lista)

                tem_habito = HabitosDeVida.objects.filter(atendimento__aluno=aluno).order_by('id')
                atividade_fisica = dificuldade_dormir = horas_sono = refeicoes_por_dia = ''
                if tem_habito.exists():
                    atividade_fisica = tem_habito[0].atividade_fisica
                    dificuldade_dormir = tem_habito[0].dificuldade_dormir
                    horas_sono = tem_habito[0].get_horas_sono_display()
                    refeicoes_por_dia = tem_habito[0].get_refeicoes_por_dia_display()

                dificuldade_aprendizado = ''
                tem_dificuldade = DesenvolvimentoPessoal.objects.filter(atendimento__aluno=aluno).order_by('id')
                if tem_dificuldade.exists():
                    dificuldade_aprendizado = tem_dificuldade[0].problema_aprendizado

                row = [
                    idx + 1,
                    obj.get_pessoa_fisica_vinculo(),
                    obj.get_tipo_display(),
                    situacao,
                    obj.data_aberto,
                    participante,
                    obj.usuario_aberto,
                    data_nascimento,
                    sexo,
                    aluno.telefone_principal,
                    aluno.email_academico,
                    renda_familiar,
                    moradia,
                    qtd_pessoas_domicilio,
                    escolaridade_mae,
                    escolaridade_pai,
                    raca,
                    necessidade_especial,
                    aluno.situacao,
                    aluno.curso_campus,
                    pressao,
                    estatura,
                    peso,
                    cintura,
                    quadril,
                    circunferencia_braco,
                    pc_triciptal,
                    pc_biciptal,
                    pc_subescapular,
                    pc_suprailiaca,
                    percentual_gordura,
                    perda_peso_total,
                    ganho_peso_total,
                    antecedentes,
                    atividade_fisica,
                    dificuldade_dormir,
                    horas_sono,
                    refeicoes_por_dia,
                    dificuldade_aprendizado,
                ]
            else:
                row = [idx + 1, obj.get_pessoa_fisica_vinculo(), obj.get_tipo_display(), situacao, obj.data_aberto, participante, obj.usuario_aberto]
            rows.append(row)
        return rows

    def has_add_permission(self, request):
        return False

    def add_view(self, request, form_url='', extra_context=None):
        raise PermissionDenied

    def change_view(self, request, object_id, form_url='', extra_context=None):
        raise PermissionDenied

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        if not request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
            return qs.filter(usuario_aberto__vinculo__setor__uo=get_uo(request.user)).exclude(situacao=SituacaoAtendimento.CANCELADO)
        return qs.exclude(situacao=SituacaoAtendimento.CANCELADO)

    def get_tipo_paciente(self, obj):
        if obj.aluno:
            retorno = f'<a href="/edu/aluno/{obj.aluno.matricula}/">{obj.get_pessoa_fisica_vinculo()}</a>'
        elif obj.servidor:
            retorno = f'<a href="/rh/servidor/{obj.servidor.matricula}/">{obj.get_pessoa_fisica_vinculo()}</a>'
        else:
            retorno = obj.get_pessoa_fisica_vinculo()
        return mark_safe(retorno)

    get_tipo_paciente.short_description = 'Paciente'

    def get_situacao_display(self, obj):
        if obj.situacao == 1:
            retorno = '<span class="status status-info">Aberto</span>'
        elif obj.situacao == 2:
            retorno = '<span class="status status-success">Fechado</span>'
        else:
            retorno = '<span class="status status-error">Cancelado</span>'
        return mark_safe(retorno)

    get_situacao_display.short_description = 'Situação'

    def get_participa_programa_estudantil(self, obj):
        if obj.aluno:
            hoje = datetime.date.today()
            if Participacao.objects.filter(aluno=obj.aluno).filter(Q(data_termino__gte=hoje) | Q(data_termino__isnull=True)).exists():
                retorno = '<span class="status status-success">Participante</span>'
            else:
                retorno = '<span class="status status-error">Não participante</span>'
        else:
            retorno = '-'
        return mark_safe(retorno)

    get_participa_programa_estudantil.short_description = 'Participação em Programas de Atividades Estudantis'

    def get_visualizar_prontuario(self, obj):
        if obj.prontuario and obj.prontuario.vinculo:
            retorno = f'<a class="btn default" href="/saude/prontuario/{obj.prontuario.vinculo_id}/">Visualizar Prontuário</a>'
            return mark_safe(retorno)
        return '-'

    get_visualizar_prontuario.short_description = 'Prontuário'
    get_visualizar_prontuario.allow_tags = True

    def get_responsaveis(self, obj):
        lista = list()
        if AtendimentoEspecialidade.objects.filter(atendimento=obj).exists():
            for atendimento in AtendimentoEspecialidade.objects.filter(atendimento=obj):
                lista.append(atendimento.profissional.get_vinculo().pessoa.nome)

            return ', '.join(lista)
        else:
            return obj.usuario_aberto.get_vinculo().pessoa.nome

    get_responsaveis.short_description = 'Responsáveis pelo Atendimento'
    get_responsaveis.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        list_filter = self.list_filter
        if request.GET.get('categoria') and request.GET.get('categoria') == '1':
            if not ModalidadeFilter in list_filter:
                list_filter = (CampusFilter, CampusPacienteFilter, TipoFilter, CategoriaFilter, ModalidadeFilter, 'situacao', ParticipanteAssistenciaFilter, 'usuario_aberto')
            if request.GET.get('tipo') and request.GET.get('tipo') == '1' and not AntropometriaFilter in list_filter:
                list_filter = (CampusFilter, CampusPacienteFilter, TipoFilter, CategoriaFilter, ModalidadeFilter, 'situacao', ParticipanteAssistenciaFilter, AntropometriaFilter, 'usuario_aberto')
        else:
            list_filter = (CampusFilter, CampusPacienteFilter, TipoFilter, CategoriaFilter, 'situacao', ParticipanteAssistenciaFilter, 'usuario_aberto')

        self.list_filter = list_filter
        return super().changelist_view(request, extra_context=extra_context)


admin.site.register(Atendimento, AtendimentoAdmin)


class MotivoChegadaPsicologiaAdmin(ModelAdminPlus):
    list_display = ('descricao',)
    ordering = ('descricao',)
    list_display_icons = True


admin.site.register(MotivoChegadaPsicologia, MotivoChegadaPsicologiaAdmin)


class QueixaPsicologicaAdmin(ModelAdminPlus):
    list_display = ('descricao',)
    ordering = ('descricao',)
    list_display_icons = True


admin.site.register(QueixaPsicologica, QueixaPsicologicaAdmin)


class AtividadeGrupoAdmin(ModelAdminPlus):
    form = AtividadeGrupoForm
    search_fields = ('nome_evento', 'tema', 'motivo')
    list_display = ('get_acoes', 'nome_evento', 'uo', 'tipo', 'motivo', 'get_responsaveis', 'data_inicio', 'data_termino', 'eh_sistemica', 'cancelada', 'get_opcoes')
    list_filter = ('uo', 'tipo', 'turno', 'meta', 'eh_sistemica', 'cancelada')
    ordering = ('-data_inicio', 'nome_evento')
    list_display_icons = False
    list_display_links = None
    date_hierarchy = 'data_inicio'

    def get_acoes(self, obj):
        pode_editar = self.request.user.get_vinculo() in obj.vinculos_responsaveis.all() or self.request.user.groups.filter(name='Coordenador de Saúde Sistêmico')
        mostra_acoes = icon('view', f'/saude/atividade_em_grupo/{obj.id}/')
        if pode_editar:
            mostra_acoes += icon('edit', f'/admin/saude/atividadegrupo/{obj.id}/change/')
        return mark_safe(mostra_acoes)

    get_acoes.short_description = 'Ações'

    def get_opcoes(self, obj):
        mostra_acoes = ''
        pode_editar = get_uo(self.request.user) == obj.uo
        if pode_editar and not obj.cancelada and self.request.user.has_perm('saude.add_atividadegrupo'):
            mostra_acoes += '''<ul class="action-bar"><li><a href="/saude/cancelar_atividade_grupo/{}/" class="btn danger" title="Cancelar Atividade">Cancelar Atividade</a></li></ul>
                            '''.format(
                obj.id
            )

        return mark_safe(mostra_acoes)

    get_opcoes.short_description = 'Opções'

    def get_responsaveis(self, obj):
        texto = ''
        for item in obj.vinculos_responsaveis.all():
            texto = texto + item.pessoa.nome + ', '
        texto = texto[:-2]
        return mark_safe(texto)

    get_responsaveis.short_description = 'Responsáveis'

    def get_uo(self, obj):
        return mark_safe(obj.uo.sigla)

    get_uo.short_description = 'Campus'

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        if retorno and obj is not None:
            retorno = request.user.get_vinculo() in obj.vinculos_responsaveis.all() or request.user.groups.filter(name='Coordenador de Saúde Sistêmico')
        return retorno


admin.site.register(AtividadeGrupo, AtividadeGrupoAdmin)


class TipoAtividadeGrupoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao',)
    ordering = ('descricao',)
    list_display_icons = True


admin.site.register(TipoAtividadeGrupo, TipoAtividadeGrupoAdmin)


class CategoriaExameLaboratorialAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_display = ('nome',)
    ordering = ('nome',)
    list_display_icons = True


admin.site.register(CategoriaExameLaboratorial, CategoriaExameLaboratorialAdmin)


class TipoExameLaboratorialAdmin(ModelAdminPlus):
    search_fields = ('nome',)
    list_display = ('nome', 'get_valor_referencia', 'ativo')
    ordering = ('nome',)
    list_display_icons = True

    def get_valor_referencia(self, obj):
        return mark_safe(obj.valor_referencia)

    get_valor_referencia.short_description = 'Valores de Referências'


admin.site.register(TipoExameLaboratorial, TipoExameLaboratorialAdmin)


class ProcedimentoMultidisciplinarAdmin(ModelAdminPlus):
    search_fields = ('denominacao',)
    list_display = ('denominacao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(ProcedimentoMultidisciplinar, ProcedimentoMultidisciplinarAdmin)


class MotivoAtendimentoNutricaoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(MotivoAtendimentoNutricao, MotivoAtendimentoNutricaoAdmin)


class AvaliacaoGastroIntestinalAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(AvaliacaoGastroIntestinal, AvaliacaoGastroIntestinalAdmin)


class RestricaoAlimentarAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(RestricaoAlimentar, RestricaoAlimentarAdmin)


class DiagnosticoNutricionalAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(DiagnosticoNutricional, DiagnosticoNutricionalAdmin)


class AnoReferenciaAcaoEducativaAdmin(ModelAdminPlus):
    search_fields = ('ano',)
    list_display = ('ano', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(AnoReferenciaAcaoEducativa, AnoReferenciaAcaoEducativaAdmin)


class ObjetivoAcaoEducativaAdmin(ModelAdminPlus):
    search_fields = ('descricao',)

    list_display = ('descricao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(ObjetivoAcaoEducativa, ObjetivoAcaoEducativaAdmin)


class OrientacaoNutricionalAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(OrientacaoNutricional, OrientacaoNutricionalAdmin)


class ReceitaNutricionalAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('get_descricao', 'ativo')
    ordering = ('id',)
    list_display_icons = True

    def get_descricao(self, obj):
        return str(obj)

    get_descricao.allow_tags = True
    get_descricao.short_description = 'Descrição'


admin.site.register(ReceitaNutricional, ReceitaNutricionalAdmin)


class FrequenciaPraticaAlimentarAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('get_descricao', 'valor_recomendado', 'ativo')
    ordering = ('id',)
    list_display_icons = True

    def get_descricao(self, obj):
        return str(obj)

    get_descricao.allow_tags = True
    get_descricao.short_description = 'Descrição'


admin.site.register(FrequenciaPraticaAlimentar, FrequenciaPraticaAlimentarAdmin)


class PerguntaMarcadorNutricaoAdmin(ModelAdminPlus):
    search_fields = ('pergunta',)
    list_display = ('pergunta', 'tipo_resposta', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(PerguntaMarcadorNutricao, PerguntaMarcadorNutricaoAdmin)


class OpcaoRespostaMarcadorNutricaoAdmin(ModelAdminPlus):
    search_fields = ('pergunta',)
    list_filter = ('pergunta',)
    list_display = ('valor', 'pergunta', 'ativo')
    ordering = ('pergunta__id',)
    list_display_icons = True


admin.site.register(OpcaoRespostaMarcadorNutricao, OpcaoRespostaMarcadorNutricaoAdmin)


class MetaAcaoEducativaAdmin(ModelAdminPlus):
    form = MetaAcaoEducativaForm
    search_fields = ('descricao',)
    list_display = ('icones', 'ano_referencia', 'get_objetivo', 'indicador', 'get_valor', 'descricao', 'get_qtd_acoes_campus', 'ativo', 'get_opcoes')
    list_filter = ('indicador', 'ano_referencia', 'ativo')
    ordering = ('id',)
    list_display_icons = False

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        items.append(dict(url='/saude/adicionar_acao_educativa_sem_meta/', label='Cadastrar Ação Independente'))
        return items

    def icones(self, obj):
        texto = icon('view', f'/saude/visualizar_meta_acao_educativa/{obj.id}/')
        if self.request.user.groups.filter(name='Coordenador de Saúde Sistêmico').exists():
            texto += icon('edit', f'/admin/saude/metaacaoeducativa/{obj.id}/')
        return mark_safe(texto)

    icones.short_description = 'Ações'

    def get_opcoes(self, obj):
        texto = '<ul class="action-bar">'
        if obj.ativo:
            if obj.pode_adicionar_meta():
                texto += f'<li><a href="/saude/adicionar_acao_educativa/{obj.pk}/" class="btn success">Adicionar Ação</a></li>'
        if AtividadeGrupo.objects.filter(meta=obj).exists():
            texto += f'<li><a href="/saude/visualizar_acoes_educativas/{obj.pk}/" class="btn default">Visualizar Ações</a></li>'
        texto += '</ul>'
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'

    def get_objetivo(self, obj):
        lista = list()
        for item in obj.objetivos.all():
            lista.append(item.descricao)
        return ', '.join(lista)

    get_objetivo.short_description = 'Objetivos'

    def get_valor(self, obj):
        if obj.indicador == MetaAcaoEducativa.NUM_ACOES:
            return f'{obj.valor} ações'
        return f'{obj.valor}%'

    get_valor.short_description = 'Quantidade'

    def get_qtd_acoes_campus(self, obj):
        uo = get_uo(self.request.user)
        qtd = AtividadeGrupo.objects.filter(meta=obj.pk, uo=uo).count()
        return f'{qtd}'

    get_qtd_acoes_campus.short_description = 'Quantidade de Ações do Campus'


admin.site.register(MetaAcaoEducativa, MetaAcaoEducativaAdmin)


class RegistroAdministrativoAdmin(ModelAdminPlus):
    form = RegistroAdministrativoForm
    search_fields = ('descricao',)
    list_display = ('descricao', 'data', 'campus', 'vinculo_profissional')
    list_filter = ('campus',)
    ordering = ('id',)
    list_display_icons = True
    date_hierarchy = 'data'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.data = datetime.date.today()
            obj.campus = get_uo(request.user)
            obj.vinculo_profissional = request.user.get_vinculo()
        obj.save()

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        if retorno and obj is not None:
            retorno = request.user.get_vinculo() == obj.vinculo_profissional
        return retorno


admin.site.register(RegistroAdministrativo, RegistroAdministrativoAdmin)


class CampusBloqueioFilter(admin.SimpleListFilter):
    title = "Campus"
    parameter_name = 'campus'

    def lookups(self, request, model_admin):
        return UnidadeOrganizacional.objects.uo().all().values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(vinculo_profissional__setor__uo=self.value())


class AnoFilter(admin.SimpleListFilter):
    title = "Ano"
    parameter_name = "ano"

    def lookups(self, request, model_admin):
        opcoes = Ano.objects.all()

        return [(d.ano, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(data__year=self.value())


class BloqueioAtendimentoSaudeAdmin(ModelAdminPlus):
    list_filter = (CampusBloqueioFilter, AnoFilter, 'vinculo_profissional')
    list_display = ('get_uo_bloqueio', 'vinculo_paciente', 'data', 'vinculo_profissional')
    ordering = ('-data',)
    list_display_icons = False
    date_hierarchy = 'data'
    list_display_links = None
    search_fields = ('vinculo_paciente__pessoa__nome', 'vinculo_profissional__pessoa__nome')

    def get_uo_bloqueio(self, obj):
        return get_uo(obj.vinculo_profissional.user)

    get_uo_bloqueio.short_description = 'Campus'


admin.site.register(BloqueioAtendimentoSaude, BloqueioAtendimentoSaudeAdmin)


class PlanoAlimentarAdmin(ModelAdminPlus):
    form = PlanoAlimentarForm
    search_fields = ('cardapio',)
    list_display = ('cardapio', 'plano_alimentar_liberado')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(PlanoAlimentar, PlanoAlimentarAdmin)


class ProcedimentoOdontologiaAdmin(ModelAdminPlus):
    form = ProcedimentoOdontologiaForm
    search_fields = ('denominacao',)
    list_display = ('denominacao', 'pode_odontologo', 'pode_tecnico', 'get_situacoes_clinicas')
    ordering = ('id',)
    list_display_icons = True

    def get_situacoes_clinicas(self, obj):
        lista = list()
        for indicacao in ProcedimentoIndicado.objects.filter(procedimento=obj):
            lista.append(indicacao.situacao_clinica.descricao)
            return ', '.join(lista)
        return '-'

    get_situacoes_clinicas.short_description = 'Situações Clínicas'


admin.site.register(ProcedimentoOdontologia, ProcedimentoOdontologiaAdmin)


class ResultadoPendenteAvaliacaoFilter(admin.SimpleListFilter):
    title = "Com teste COVID pendente de validação"
    parameter_name = "teste_pendente"

    def lookups(self, request, model_admin):
        opcoes = (('Sim', 'Sim'), ('Não', 'Não'))
        return opcoes

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'Sim':
                return queryset.filter(id__in=ResultadoTesteCovid.objects.filter(situacao=ResultadoTesteCovid.AGUARDANDO_VALIDACAO).values_list('passaporte', flat=True))
            elif self.value() == 'Não':
                return queryset.exclude(id__in=ResultadoTesteCovid.objects.filter(situacao=ResultadoTesteCovid.AGUARDANDO_VALIDACAO).values_list('passaporte', flat=True))


class PassaporteVacinalCovidAdmin(ModelAdminPlus):
    list_filter = ('situacao_declaracao', 'uo', 'situacao_passaporte', 'esquema_completo', ResultadoPendenteAvaliacaoFilter)
    list_display = ('vinculo', 'uo', 'get_situacao_declaracao', 'get_situacao_passaporte', 'recebeu_alguma_dose', 'data_primeira_dose', 'data_segunda_dose', 'data_terceira_dose', 'possui_atestado_medico', 'get_atestado_medico', 'termo_aceito_em', 'get_cartao_vacinal', 'justificativa_indeferimento', 'get_opcoes')
    ordering = ('id',)
    list_display_icons = False
    list_display_links = None

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        if not request.user.has_perm('saude.pode_ver_todos_passaportes') and not request.user.groups.filter(name='Validador de Passaporte Vacinal Sistêmico').exists():
            campi_consulta = []
            campi_consulta.append(get_uo(request.user).id)
            eh_validador_intercampi = ValidadorIntercampi.objects.filter(vinculo=request.user.get_vinculo(),
                                                                         ativo=True)
            if eh_validador_intercampi.exists():
                campi_consulta += eh_validador_intercampi.values_list('campi', flat=True)
            return qs.filter(uo__in=campi_consulta)
        return qs

    def get_atestado_medico(self, obj):
        if obj.atestado_medico:
            return mark_safe(f'<a href="{obj.atestado_medico.url}" class="btn default">Ver Arquivo</a>')
        return '-'
    get_atestado_medico.short_description = 'Atestado Médico'

    def get_cartao_vacinal(self, obj):
        if obj.cartao_vacinal:
            return mark_safe(f'<a href="{obj.cartao_vacinal.url}" class="btn default">Ver Arquivo</a>')
        return '-'
    get_cartao_vacinal.short_description = 'Cartão Vacinal Covid-19'

    def get_opcoes(self, obj):
        texto = '<ul class="action-bar">'
        if not obj.esquema_completo:
            if obj.situacao_declaracao == PassaporteVacinalCovid.AGUARDANDO_VALIDACAO:
                texto += f'<li><a href="/saude/deferir_passaporte_vacinal/{obj.pk}/" class="btn success">Deferir</a></li>'
                texto += '<li><a href="/saude/indeferir_passaporte_vacinal/{}/" class="btn danger confirm">Indeferir</a></li>'.format(
                    obj.pk)
            elif obj.situacao_declaracao == PassaporteVacinalCovid.DEFERIDA:
                texto += '<li><a href="/saude/indeferir_passaporte_vacinal/{}/" class="btn danger confirm">Indeferir</a></li>'.format(
                    obj.pk)
            elif obj.situacao_declaracao == PassaporteVacinalCovid.INDEFERIDA:
                texto += f'<li><a href="/saude/deferir_passaporte_vacinal/{obj.pk}/" class="btn success">Deferir</a></li>'
        especialidade = Especialidades(self.request.user)
        if Especialidades.eh_profissional_saude(especialidade):
            texto += '<li><a href="/saude/prontuario/{}/?tab=aba_cartao_vacinal" class="btn default">Ver Prontuário</a></li>'.format(
                obj.vinculo.pk)
        if HistoricoValidacaoPassaporte.objects.filter(passaporte=obj).exists():
            texto += '<li><a href="/saude/ver_historico_validacao_passaporte/{}/" class="btn default popup">Ver Histórico</a></li>'.format(
                obj.pk)
        if ResultadoTesteCovid.objects.filter(passaporte=obj).exists():
            texto += '<li><a href="/saude/resultados_testes_covid/{}/" class="btn default">Ver Resultados dos Testes</a></li>'.format(
                obj.pk)

        texto += '</ul>'

        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'

    def get_situacao_declaracao(self, obj):
        if obj.situacao_declaracao == PassaporteVacinalCovid.AGUARDANDO_VALIDACAO:
            retorno = '<span class="status status-alert">Aguardando validação</span>'
        elif obj.situacao_declaracao == PassaporteVacinalCovid.DEFERIDA:
            retorno = '<span class="status status-success">Deferida</span>'
        elif obj.situacao_declaracao == PassaporteVacinalCovid.INDEFERIDA:
            retorno = '<span class="status status-error">Indeferida</span>'
        else:
            retorno = '<span class="status status-alert">Aguardando autodeclaração</span>'
        if obj.avaliada_em:
            retorno += f' por {obj.avaliada_por} em {obj.avaliada_em.strftime("%d/%m/%Y")}'
        return mark_safe(retorno)
    get_situacao_declaracao.short_description = 'Situação da Declaração'

    def get_situacao_passaporte(self, obj):
        if obj.situacao_passaporte == PassaporteVacinalCovid.VALIDO:
            retorno = '<span class="status status-success">Válido</span>'
        elif obj.situacao_passaporte == PassaporteVacinalCovid.INVALIDO:
            retorno = '<span class="status status-error">Inválido</span>'
        else:
            retorno = '<span class="status status-info">Pendente</span>'
        return mark_safe(retorno)

    get_situacao_passaporte.short_description = 'Situação do Passaporte'


admin.site.register(PassaporteVacinalCovid, PassaporteVacinalCovidAdmin)


class SintomaAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'ativo')
    ordering = ('id',)
    list_display_icons = True


admin.site.register(Sintoma, SintomaAdmin)


class SetorFilter(admin.SimpleListFilter):
    title = "Setor"
    parameter_name = "setor"

    def lookups(self, request, model_admin):
        return Setor.objects.all().values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            setor = Setor.objects.get(id=self.value())
            servidores_do_setor = Servidor.objects.ativos().filter(setor__in=setor.descendentes)
            return queryset.filter(vinculo__in=servidores_do_setor.values_list('vinculos', flat=True))


class NotificacaoCovidAdmin(ModelAdminPlus):
    search_fields = ('vinculo__pessoa__nome', )
    list_filter = ('uo', SetorFilter, 'situacao', 'monitoramento', )
    list_display = ('get_vinculo', 'get_situacao_vacinal', 'uo', 'situacao', 'monitoramento', 'data_inicio_sintomas', 'get_sintomas', 'data_ultimo_teste', 'resultado_ultimo_teste', 'get_arquivo_ultimo_teste', 'data_contato_suspeito', 'mora_com_suspeito', 'esteve_sem_mascara', 'tempo_exposicao', 'suspeito_fez_teste', 'get_arquivo_teste', 'get_opcoes')
    ordering = ('id',)
    list_display_icons = False
    list_display_links = None

    def get_vinculo(self, obj):

        if obj.vinculo.tipo_relacionamento.model == 'aluno':
            retorno = f'<a href="/edu/aluno/{obj.vinculo.relacionamento.matricula}/?tab=dados_pessoais">{obj.vinculo}</a>'
        elif obj.vinculo.tipo_relacionamento.model == 'servidor':
            retorno = f'<a href="/rh/servidor/{obj.vinculo.relacionamento.matricula}/">{obj.vinculo}</a>'
        elif obj.vinculo.tipo_relacionamento.model == 'prestadorservico':
            retorno = f'<a href="/comum/prestador_servico/{obj.vinculo.relacionamento.id}/">{obj.vinculo}</a>'
        else:
            retorno = obj.vinculo__str__()
        return mark_safe(retorno)

    get_vinculo.short_description = 'Paciente'

    def get_situacao_vacinal(self, obj):
        if PassaporteVacinalCovid.objects.filter(vinculo=obj.vinculo).exists():
            registro = PassaporteVacinalCovid.objects.filter(vinculo=obj.vinculo)[0]
            return registro.situacao_passaporte
        return '-'

    get_situacao_vacinal.short_description = 'Passaporte Vacinal'

    def get_sintomas(self, obj):
        lista = list()
        for sintoma in obj.sintomas.all():
            lista.append(sintoma.descricao)
        return ', '.join(lista)
    get_sintomas.short_description = 'Sintomas'

    def get_arquivo_ultimo_teste(self, obj):
        if obj.arquivo_ultimo_teste:
            return mark_safe(f'<a href="{obj.arquivo_ultimo_teste.url}" class="btn default">Ver Arquivo</a>')
        return '-'

    get_arquivo_ultimo_teste.short_description = 'Último Teste Realizado'

    def get_arquivo_teste(self, obj):
        if obj.arquivo_teste:
            return mark_safe(f'<a href="{obj.arquivo_teste.url}" class="btn default">Ver Arquivo</a>')
        return '-'

    get_arquivo_teste.short_description = 'Resultado do Teste'

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        if request.user.has_perm('saude.add_sintoma'):
            return qs
        return qs.filter(uo=get_uo(request.user))

    def get_opcoes(self, obj):
        texto = '<ul class="action-bar">'
        if obj.pode_monitorar():
            texto += f'<li><a href="/saude/monitorar_notificacao_covid/{obj.pk}/" class="btn success">Monitorar</a></li>'
        if obj.monitoramento != NotificacaoCovid.SEM_MONITORAMENTO:
            texto += '<li><a href="/saude/ver_monitoramentos_covid/{}/" class="btn default">Ver Monitoramentos</a></li>'.format(
                obj.pk)
        especialidade = Especialidades(self.request.user)
        if Especialidades.eh_profissional_saude(especialidade):
            texto += '<li><a href="/saude/prontuario/{}/" class="btn default">Ver Prontuário</a></li>'.format(
                obj.vinculo.pk)
        texto += '</ul>'
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'


admin.site.register(NotificacaoCovid, NotificacaoCovidAdmin)


class ValidadorIntercampiAdmin(ModelAdminPlus):
    search_fields = ('vinculo__pessoa__nome', 'vinculo__pessoa__matricula')
    list_display = ('vinculo', 'get_campi', 'ativo')
    ordering = ('id',)
    list_display_icons = True

    def get_campi(self, obj):
        return ', '.join([campi.__str__() for campi in obj.campi.all()])

    get_campi.short_description = 'Campi'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        ids_usuarios = UsuarioGrupo.objects.filter(group__name__in=Especialidades.GRUPOS_ATENDIMENTO_MEDICO_ENF).only('user').values_list(
            'user_id', flat=True)
        form.base_fields['vinculo'].queryset = Vinculo.objects.filter(user__in=ids_usuarios)
        form.base_fields['campi'].queryset = UnidadeOrganizacional.objects.uo()
        return form


admin.site.register(ValidadorIntercampi, ValidadorIntercampiAdmin)
