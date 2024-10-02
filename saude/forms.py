import datetime
import re
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.forms.widgets import HiddenInput

from comum.models import Ano, UsuarioGrupo, User, Vinculo as VinculoPessoa
from comum.utils import get_uo
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget, FilteredSelectMultiplePlus
from edu.models import Turma, Modalidade, Aluno, CursoCampus
from rh.models import UnidadeOrganizacional, PessoaExterna, Setor
from saude import help_text
from saude.models import (
    Doenca,
    Vacina,
    CartaoVacinal,
    SinaisVitais,
    AcuidadeVisual,
    Antropometria,
    AntecedentesFamiliares,
    ProcessoSaudeDoenca,
    HabitosDeVida,
    DesenvolvimentoPessoal,
    ExameFisico,
    PercepcaoSaudeBucal,
    MetodoContraceptivo,
    UsoInternet,
    Droga,
    ObjetivoUsoInternet,
    DificuldadeOral,
    Vinculo,
    AtendimentoEspecialidade,
    Motivo,
    Anamnese,
    ProcedimentoEnfermagem,
    Cid,
    CondutaMedica,
    Atendimento,
    Especialidades,
    InformacaoAdicional,
    ProcedimentoOdontologia,
    SituacaoClinica,
    ExamePeriodontal,
    ExameEstomatologico,
    PlanoTratamento,
    ProcedimentoIndicado,
    AtividadeGrupo,
    ExameImagem,
    ExameLaboratorial,
    TipoExameLaboratorial,
    CategoriaExameLaboratorial,
    RegiaoBucal,
    HipoteseDiagnostica,
    AtendimentoPsicologia,
    QueixaPsicologica,
    AnamnesePsicologia,
    AtendimentoMultidisciplinar,
    ProcedimentoMultidisciplinar,
    TipoConsultaOdontologia,
    Odontograma,
    AnexoPsicologia,
    HorarioAtendimento,
    ObjetivoAcaoEducativa,
    MetaAcaoEducativa,
    AtendimentoNutricao,
    MotivoAtendimentoNutricao,
    AvaliacaoGastroIntestinal,
    RestricaoAlimentar,
    DiagnosticoNutricional,
    OrientacaoNutricional,
    ReceitaNutricional,
    ConsumoNutricao,
    PlanoAlimentar,
    FrequenciaPraticaAlimentar,
    PerguntaMarcadorNutricao,
    RegistroAdministrativo,
    DocumentoProntuario,
    Prontuario,
    AtendimentoFisioterapia, PassaporteVacinalCovid, ResultadoTesteCovid, NotificacaoCovid, Sintoma,
    MonitoramentoCovid,
)
from pycpfcnpj import cpfcnpj
from django.contrib import auth


class ConfiguracaoForm(forms.FormPlus):
    utiliza_passaporte_vacinal = forms.BooleanField(label='Utiliza Passaporte Vacinal', required=False)
    host_rnmaisvacina = forms.CharFieldPlus(label='Host do RN+Vacina', required=False)
    token_rnmaisvacina = forms.CharFieldPlus(label='Token de Acesso ao RN+Vacina', required=False)
    data_checagem_ponto = forms.DateFieldPlus(label='Data de Início da Verificação do Ponto dos Servidores', required=False)


class BuscaProntuarioForm(forms.FormPlus):
    paciente = forms.CharField(label='Buscar por Nome, Matrícula ou CPF', required=True)
    vinculo = forms.ChoiceField(label='Vínculo', required=False, choices=Vinculo.VINCULO_CHOICES)

    METHOD = 'GET'
    SUBMIT_LABEL = 'Buscar'


class RegistrarVacinacaoForm(forms.FormPlus):
    externo = forms.BooleanField(label='Procedência externa?', initial=False, required=False)
    sem_data = forms.BooleanField(label='Desconhece data de vacinação?', initial=False, required=False)
    data = forms.DateFieldPlus(label='Data da Vacinação', required=False, help_text="Não preencher esta campo caso desconheça a data real de vacinação")
    obs = forms.CharField(label='Observação', widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        registro = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)

        self.fields['data'].initial = registro.data_vacinacao

        self.fields['sem_data'].initial = registro.sem_data
        self.fields['externo'].initial = registro.externo
        self.fields['obs'].initial = registro.obs

    METHOD = 'POST'
    SUBMIT_LABEL = 'Registrar Vacinação'


class RegistrarPrevisaoVacinacaoForm(forms.FormPlus):
    previsao = forms.DateFieldPlus(label='Previsão da Vacinação', required=True)

    def __init__(self, *args, **kwargs):
        registro = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)

        self.fields['previsao'].initial = registro.data_prevista

    METHOD = 'POST'
    SUBMIT_LABEL = 'Salvar'


class AdicionarVacinaForm(forms.FormPlus):
    vacina = forms.ModelChoiceField(label='Vacina', queryset=Vacina.ativas)
    SUBMIT_LABEL = 'Adicionar'

    def __init__(self, *args, **kwargs):
        prontuario = kwargs.pop('prontuario', None)
        super().__init__(*args, **kwargs)

        # Agrupando os registros de vacinação na variável -grupos-
        vacinas = CartaoVacinal.objects.filter(prontuario=prontuario.id)
        grupo_vacina = Vacina.objects.filter(id__in=prontuario.vacinas.all().distinct())
        grupos = []
        for grupo in grupo_vacina:
            lista = []
            for registro_vacina in vacinas:
                if registro_vacina.vacina_id == grupo.id:
                    lista.append(registro_vacina)
            grupos.append(lista)

        # Identificando quais das vacinações de -grupos- já foram completadas, para que possam voltar à disponibilidade
        vacinas_finalizadas = []
        for grupo in grupos:
            vacina_finalizada = True
            for registro_vacina in grupo:
                if not registro_vacina.data_vacinacao and not registro_vacina:
                    vacina_finalizada = False
            if vacina_finalizada:
                vacinas_finalizadas.append(registro_vacina.vacina_id)

        self.fields['vacina'].queryset = Vacina.ativas.exclude(id__in=prontuario.vacinas.all().distinct()) | Vacina.ativas.filter(id__in=vacinas_finalizadas)


class SinaisVitaisForm(forms.ModelFormPlus):
    pressao_sistolica = forms.IntegerField(label='Pressão Sistólica', required=True, max_value=300, min_value=50)
    pressao_diastolica = forms.IntegerField(label='Pressão Diastólica', required=True, max_value=200, min_value=20, help_text='Em mmHg')
    pulsacao = forms.IntegerField(label='Pulsação', required=True, max_value=160, min_value=35, help_text='Em bpm')

    class Meta:
        model = SinaisVitais
        fields = ('pressao_sistolica', 'pressao_diastolica', 'pulsacao', 'respiracao_categoria', 'temperatura_categoria')

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AntropometriaForm(forms.ModelFormPlus):
    estatura = forms.IntegerField(label='Estatura', required=True, max_value=999, help_text='Em cm')
    peso = forms.DecimalField(label='Peso', required=True, decimal_places=3, max_value=210, min_value=30, help_text='Em kg')
    cintura = forms.DecimalField(label='Circunferência da Cintura', required=False, decimal_places=1, help_text='Em cm')
    quadril = forms.DecimalField(label='Circunferência do Quadril', required=False, decimal_places=1, help_text='Em cm')
    circunferencia_braco = forms.DecimalField(label='Circunferência do Braço', required=False, decimal_places=1, help_text='Em cm')
    quanto_perdeu = forms.DecimalField(label='Quanto perdeu', required=False, decimal_places=1, help_text='Em kg')
    quanto_ganhou = forms.DecimalField(label='Quanto ganhou', required=False, decimal_places=1, help_text='Em kg')
    percentual_gordura = forms.DecimalField(required=False)
    sentimento_relacao_corpo = forms.ChoiceField(label='Como você se sente em relação ao seu corpo?', required=True, choices=Antropometria.RELACAO_CORPO_CHOICES)
    periodo_sem_comida = forms.ChoiceField(label='NOS ÚLTIMOS 30 DIAS, com que frequência você ficou com fome por não ter comida suficiente em sua casa?', required=True, choices=Antropometria.PERIODO_SEM_COMIDA_CHOICES)

    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('estatura', 'peso'),
                    ('cintura', 'quadril', 'circunferencia_braco'),
                    ('pc_triciptal', 'pc_biciptal'),
                    ('pc_subescapular', 'pc_suprailiaca'),
                    ('dobra_cutanea_abdominal', 'dobra_cutanea_supraespinhal'),
                    ('dobra_cutanea_coxa_media', 'dobra_cutanea_panturrilha_medial'),
                    ('percentual_gordura',),
                    'perda_peso',
                    ('quanto_perdeu', 'tempo_perda'),
                    'ganho_peso',
                    ('quanto_ganhou', 'tempo_ganho'),
                    ('sentimento_relacao_corpo'),
                    ('periodo_sem_comida'),
                )
            },
        ),
    )

    class Meta:
        model = Antropometria
        fields = (
            'estatura',
            'peso',
            'cintura',
            'quadril',
            'circunferencia_braco',
            'pc_triciptal',
            'pc_biciptal',
            'pc_subescapular',
            'pc_suprailiaca',
            'percentual_gordura',
            'perda_peso',
            'quanto_perdeu',
            'tempo_perda',
            'ganho_peso',
            'quanto_ganhou',
            'tempo_ganho',
            'dobra_cutanea_abdominal',
            'dobra_cutanea_supraespinhal',
            'dobra_cutanea_coxa_media',
            'dobra_cutanea_panturrilha_medial',
            'sentimento_relacao_corpo',
            'periodo_sem_comida'
        )

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)

        if self.cleaned_data.get('peso') and (self.cleaned_data['peso'] > 210 and self.cleaned_data['peso'] < 30):
            self.add_error("peso", 'O peso deve ser entre 30 e 211.')

        if self.cleaned_data.get('perda_peso') and self.cleaned_data.get('ganho_peso'):
            self.add_error("ganho_peso", 'Não é possível preencher Ganho e Perda de peso na mesma avaliação.')

        return cleaned_data

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.perda_peso:
            self.instance.quanto_perdeu = None
        if not self.instance.ganho_peso:
            self.instance.quanto_ganhou = None
        self.instance.save()

        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AcuidadeVisualForm(forms.ModelFormPlus):
    olho_direito = forms.CharField(label='Olho Direito', help_text='Formato 99/99 ou 99/999', required=False)
    olho_esquerdo = forms.CharField(label='Olho Esquerdo', help_text='Formato 99/99 ou 99/999', required=False)

    class Meta:
        model = AcuidadeVisual
        fields = ('com_correcao', 'olho_esquerdo', 'olho_direito')

    fieldsets = ((None, {'fields': ('com_correcao', ('olho_esquerdo', 'olho_direito'))}),)

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        expressao = re.compile(r'\d\d/\d\d')
        expressao2 = re.compile(r'\d\d/\d\d\d')
        if self.cleaned_data.get('olho_esquerdo'):

            if len(self.cleaned_data.get('olho_esquerdo')) not in (5, 6) or (
                not expressao.match(self.cleaned_data.get('olho_esquerdo')) and not expressao2.match(self.cleaned_data.get('olho_esquerdo'))
            ):
                self.add_error("olho_esquerdo", 'Formato Inválido. Utilize o padrão 99/99 ou 99/999.')

        if self.cleaned_data.get('olho_direito'):
            if len(self.cleaned_data.get('olho_direito')) not in (5, 6) or (
                not expressao.match(self.cleaned_data.get('olho_direito')) and not expressao2.match(self.cleaned_data.get('olho_direito'))
            ):
                self.add_error("olho_direito", 'Formato Inválido. Utilize o padrão 99/99 ou 99/999.')

        return cleaned_data

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AntecedentesFamiliaresForm(forms.ModelFormPlus):
    agravos_primeiro_grau = forms.MultipleModelChoiceFieldPlus(Doenca.objects.all(), required=False, label='Agravos à saúde com parentesco de 1º grau')
    agravos_segundo_grau = forms.MultipleModelChoiceFieldPlus(Doenca.objects.all(), required=False, label='Agravos à saúde com parentesco de 2º grau')

    class Meta:
        model = AntecedentesFamiliares
        fields = ('agravos_primeiro_grau', 'agravos_segundo_grau')

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class ProcessoSaudeDoencaForm(forms.ModelFormPlus):
    doencas_cronicas = forms.MultipleModelChoiceFieldPlus(
        Doenca.objects.all(), required=False, label='Sofre de alguma doença crônica', help_text=help_text.doencas_cronicas
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'fez_cirurgia',
                    ('que_cirurgia', 'tempo_cirurgia'),
                    ('hemorragia', 'tempo_hemorragia'),
                    ('alergia_alimentos', 'que_alimentos'),
                    ('alergia_medicamentos', 'que_medicamentos'),
                    ('usa_medicamentos', 'usa_que_medicamentos'),
                    ('tem_plano_saude', 'tem_plano_odontologico'),
                    ('transtorno_psiquiatrico', 'qual_transtorno_psiquiatrico'),
                    'psiquiatra',
                    ('duracao_psiquiatria', 'tempo_psiquiatria'),
                    ('lesoes_ortopedicas', 'quais_lesoes_ortopedicas'),
                    'doencas_cronicas',
                    ('doencas_previas', 'que_doencas_previas'),
                    'gestante',
                    ('problema_auditivo', 'qual_problema'),
                )
            },
        ),
    )

    class Meta:
        model = ProcessoSaudeDoenca
        fields = (
            'fez_cirurgia',
            'que_cirurgia',
            'tempo_cirurgia',
            'hemorragia',
            'tempo_hemorragia',
            'alergia_alimentos',
            'que_alimentos',
            'alergia_medicamentos',
            'que_medicamentos',
            'tem_plano_saude',
            'tem_plano_odontologico',
            'transtorno_psiquiatrico',
            'qual_transtorno_psiquiatrico',
            'psiquiatra',
            'duracao_psiquiatria',
            'tempo_psiquiatria',
            'usa_medicamentos',
            'usa_que_medicamentos',
            'lesoes_ortopedicas',
            'quais_lesoes_ortopedicas',
            'doencas_cronicas',
            'doencas_previas',
            'que_doencas_previas',
            'gestante',
            'problema_auditivo',
            'qual_problema',
        )

    def __init__(self, *args, **kwargs):
        sexo = kwargs.pop('sexo', None)
        super().__init__(*args, **kwargs)

        if sexo == 'M':
            self.fields.pop('gestante')

        self.instance.pk = None

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.fez_cirurgia:
            self.instance.que_cirurgia = ''
        if not self.instance.hemorragia:
            self.instance.tempo_hemorragia = ''
        if not self.instance.alergia_alimentos:
            self.instance.que_alimentos = ''
        if not self.instance.alergia_medicamentos:
            self.instance.que_medicamentos = ''
        if not self.instance.usa_medicamentos:
            self.instance.usa_que_medicamentos = ''
        if not self.instance.lesoes_ortopedicas:
            self.instance.quais_lesoes_ortopedicas = ''
        if not self.instance.psiquiatra:
            self.instance.duracao_psiquiatria = None
        if not self.instance.problema_auditivo:
            self.instance.qual_problema = ''
        self.instance.save()
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class HabitosDeVidaForm(forms.ModelFormPlus):
    que_drogas = forms.MultipleModelChoiceFieldPlus(Droga.objects.filter(ativo=True), required=False, label='Quais drogas')
    frequencia_semanal = forms.ChoiceField(label='Frequência semanal', required=False, choices=HabitosDeVida.FREQUENCIA_SEMANAL_CHOICES)
    duracao_atividade = forms.ChoiceField(label='Duração da atividade física', required=False, choices=HabitosDeVida.DURACAO_ATIVIDADE_CHOICES)
    frequencia_bebida = forms.ChoiceField(label='Frequência mínima de ingestão de bebidas alcoólicas', required=False, choices=HabitosDeVida.FREQUENCIA_BEBIDA_CHOICES)
    horas_sono = forms.ChoiceField(label='Horas de sono diárias', required=False, choices=HabitosDeVida.HORAS_SONO_CHOICES)
    refeicoes_por_dia = forms.ChoiceField(label='Quantas refeições faz por dia', required=False, choices=HabitosDeVida.REFEICOES_DIA_CHOICES)
    qual_metodo_contraceptivo = forms.MultipleModelChoiceFieldPlus(
        MetodoContraceptivo.objects.filter(ativo=True), required=False, label='Qual método contraceptivo'
    )
    tempo_uso_internet = forms.ChoiceField(label='Qual o tempo de uso', required=False, choices=UsoInternet.USOINTERNET_CHOICES)
    objetivo_uso_internet = forms.MultipleChoiceField(
        choices=ObjetivoUsoInternet.OBJETIVOUSOINTERNET_CHOICES, widget=forms.CheckboxSelectMultiple, required=False, label='Objetivo do uso'
    )
    frequencia_fumo = forms.DecimalField(label='Número de cigarros por dia:', required=False, decimal_places=1)

    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('atividade_fisica', 'qual_atividade'),
                    ('frequencia_semanal', 'duracao_atividade'),
                    ('fuma', 'frequencia_fumo'),
                    ('bebe', 'frequencia_bebida'),
                    'usa_drogas',
                    ('que_drogas'),
                    ('dificuldade_dormir', 'horas_sono'),
                    'refeicoes_por_dia',
                    ('vida_sexual_ativa', 'metodo_contraceptivo', 'qual_metodo_contraceptivo'),
                    ('uso_internet', 'tempo_uso_internet', 'objetivo_uso_internet'),
                )
            },
        ),
    )

    class Meta:
        model = HabitosDeVida
        fields = (
            'atividade_fisica',
            'qual_atividade',
            'frequencia_semanal',
            'duracao_atividade',
            'fuma',
            'frequencia_fumo',
            'usa_drogas',
            'que_drogas',
            'bebe',
            'frequencia_bebida',
            'dificuldade_dormir',
            'horas_sono',
            'refeicoes_por_dia',
            'vida_sexual_ativa',
            'metodo_contraceptivo',
            'qual_metodo_contraceptivo',
            'uso_internet',
            'tempo_uso_internet',
            'objetivo_uso_internet',
        )

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Usado para forcar o INSERT e salva o m2m que_drogas
        self.instance.pk = None

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.atividade_fisica:
            self.instance.frequencia_semanal = 0
            self.instance.qual_atividade = ''
        if not self.instance.vida_sexual_ativa:
            self.instance.metodo_contraceptivo = False
            self.instance.qual_metodo_contraceptivo.clear()
        if not self.instance.usa_drogas:
            self.instance.usa_drogas = False
        if not self.instance.bebe:
            self.instance.frequencia_bebida = None
        if not self.instance.fuma:
            self.instance.frequencia_fumo = None
        if not self.instance.uso_internet:
            self.instance.tempo_uso_internet = None
            self.instance.objetivo_uso_internet = ''
        self.instance.save()
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class DesenvolvimentoPessoalForm(forms.ModelFormPlus):
    fieldsets = ((None, {'fields': (('problema_aprendizado', 'qual_problema_aprendizado'), ('origem_problema',))}),)

    class Meta:
        model = DesenvolvimentoPessoal
        fields = ('problema_aprendizado', 'qual_problema_aprendizado', 'origem_problema')

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.problema_aprendizado:
            self.instance.qual_problema_aprendizado = ''
        self.instance.save()
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class PercepcaoSaudeBucalForm(forms.ModelFormPlus):
    motivo_dificuldade_sorrir = forms.ModelChoiceField(DificuldadeOral.objects.filter(ativo=True), required=False)
    motivo_dificuldade_falar = forms.ModelChoiceField(DificuldadeOral.objects.filter(ativo=True), required=False)
    motivo_dificuldade_comer = forms.ModelChoiceField(DificuldadeOral.objects.filter(ativo=True), required=False)
    motivo_dificuldade_relacionar = forms.ModelChoiceField(DificuldadeOral.objects.filter(ativo=True), required=False)
    motivo_dificuldade_manter_humor = forms.ModelChoiceField(DificuldadeOral.objects.filter(ativo=True), required=False)
    motivo_dificuldade_estudar = forms.ModelChoiceField(DificuldadeOral.objects.filter(ativo=True), required=False)
    motivo_dificuldade_trabalhar = forms.ModelChoiceField(DificuldadeOral.objects.filter(ativo=True), required=False)
    motivo_dificuldade_higienizar = forms.ModelChoiceField(DificuldadeOral.objects.filter(ativo=True), required=False)
    qtd_dias_consumiu_doce_ultima_semana = forms.IntegerField(
        label='Na última semana quantos dias consumiu doces, balas, bolos ou refrigerantes?', min_value=0, max_value=7, required=False
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('foi_dentista_anteriormente', 'tempo_ultima_vez_dentista'),
                    ('qtd_vezes_fio_dental_ultima_semana'),
                    ('qtd_dias_consumiu_doce_ultima_semana'),
                    ('usa_protese'),
                    ('usa_aparelho_ortodontico'),
                    ('dificuldades',),
                    ('grau_dificuldade_sorrir', 'motivo_dificuldade_sorrir'),
                    ('grau_dificuldade_falar', 'motivo_dificuldade_falar'),
                    ('grau_dificuldade_comer', 'motivo_dificuldade_comer'),
                    ('grau_dificuldade_relacionar', 'motivo_dificuldade_relacionar'),
                    ('grau_dificuldade_manter_humor', 'motivo_dificuldade_manter_humor'),
                    ('grau_dificuldade_estudar', 'motivo_dificuldade_estudar'),
                    ('grau_dificuldade_trabalhar', 'motivo_dificuldade_trabalhar'),
                    ('grau_dificuldade_higienizar', 'motivo_dificuldade_higienizar'),
                    ('grau_dificuldade_dormir', 'motivo_dificuldade_dormir'),
                )
            },
        ),
    )

    class Meta:
        model = PercepcaoSaudeBucal
        fields = (
            'foi_dentista_anteriormente',
            'tempo_ultima_vez_dentista',
            'qtd_vezes_fio_dental_ultima_semana',
            'qtd_dias_consumiu_doce_ultima_semana',
            'usa_protese',
            'usa_aparelho_ortodontico',
            'dificuldades',
            'grau_dificuldade_sorrir',
            'grau_dificuldade_falar',
            'grau_dificuldade_comer',
            'grau_dificuldade_relacionar',
            'grau_dificuldade_manter_humor',
            'grau_dificuldade_estudar',
            'grau_dificuldade_trabalhar',
            'grau_dificuldade_higienizar',
            'motivo_dificuldade_sorrir',
            'motivo_dificuldade_falar',
            'motivo_dificuldade_comer',
            'motivo_dificuldade_relacionar',
            'motivo_dificuldade_manter_humor',
            'motivo_dificuldade_estudar',
            'motivo_dificuldade_trabalhar',
            'motivo_dificuldade_higienizar',
            'grau_dificuldade_dormir',
            'motivo_dificuldade_dormir',
        )

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)

        if self.cleaned_data['grau_dificuldade_sorrir'] and not self.cleaned_data['motivo_dificuldade_sorrir']:
            self.add_error("grau_dificuldade_sorrir", 'Motivo de dificuldade de sorrir é obrigatório.')

        if self.cleaned_data['grau_dificuldade_falar'] and not self.cleaned_data['motivo_dificuldade_falar']:
            self.add_error("grau_dificuldade_falar", 'Motivo de dificuldade de falar é obrigatório.')

        if self.cleaned_data['grau_dificuldade_comer'] and not self.cleaned_data['motivo_dificuldade_comer']:
            self.add_error("grau_dificuldade_comer", 'Motivo de dificuldade de comer é obrigatório.')

        if self.cleaned_data['grau_dificuldade_relacionar'] and not self.cleaned_data['motivo_dificuldade_relacionar']:
            self.add_error("grau_dificuldade_relacionar", 'Motivo de dificuldade de relacionar é obrigatório.')

        if self.cleaned_data['grau_dificuldade_manter_humor'] and not self.cleaned_data['motivo_dificuldade_manter_humor']:
            self.add_error("grau_dificuldade_manter_humor", 'Motivo de dificuldade de manter o humor é obrigatório.')

        if self.cleaned_data['grau_dificuldade_estudar'] and not self.cleaned_data['motivo_dificuldade_estudar']:
            self.add_error("grau_dificuldade_estudar", 'Motivo de dificuldade de estudar é obrigatório.')

        if self.cleaned_data['grau_dificuldade_trabalhar'] and not self.cleaned_data['motivo_dificuldade_trabalhar']:
            self.add_error("grau_dificuldade_trabalhar", 'Motivo de dificuldade de trabalhar é obrigatório.')

        if self.cleaned_data['grau_dificuldade_higienizar'] and not self.cleaned_data['motivo_dificuldade_higienizar']:
            self.add_error("grau_dificuldade_higienizar", 'Motivo de dificuldade de higienizar é obrigatório.')

        return cleaned_data

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.foi_dentista_anteriormente:
            self.instance.tempo_ultima_vez_dentista = None
        if not self.instance.dificuldades:
            self.instance.grau_dificuldade_sorrir = None
            self.instance.motivo_dificuldade_sorrir = None
            self.instance.grau_dificuldade_falar = None
            self.instance.motivo_dificuldade_falar = None
            self.instance.grau_dificuldade_comer = None
            self.instance.motivo_dificuldade_comer = None
            self.instance.grau_dificuldade_relacionar = None
            self.instance.motivo_dificuldade_relacionar = None
            self.instance.grau_dificuldade_manter_humor = None
            self.instance.motivo_dificuldade_manter_humor = None
            self.instance.grau_dificuldade_estudar = None
            self.instance.motivo_dificuldade_estudar = None
            self.instance.grau_dificuldade_trabalhar = None
            self.instance.motivo_dificuldade_trabalhar = None
            self.instance.grau_dificuldade_higienizar = None
            self.instance.motivo_dificuldade_higienizar = None
        self.instance.save()
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class ExameFisicoForm(forms.ModelFormPlus):
    class Meta:
        model = ExameFisico
        fields = (
            'ectoscopia_alterada',
            'alteracao_ectoscopia',
            'acv_alterado',
            'alteracao_acv',
            'ar_alterado',
            'alteracao_ar',
            'abdome_alterado',
            'alteracao_abdome',
            'mmi_alterados',
            'alteracao_mmi',
            'mms_alterados',
            'alteracao_mms',
            'outras_alteracoes',
            'outras_alteracoes_descricao',
        )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'ectoscopia_alterada',
                    'alteracao_ectoscopia',
                    'acv_alterado',
                    'alteracao_acv',
                    'ar_alterado',
                    'alteracao_ar',
                    'abdome_alterado',
                    'alteracao_abdome',
                    'mmi_alterados',
                    'alteracao_mmi',
                    'mms_alterados',
                    'alteracao_mms',
                    'outras_alteracoes',
                    'outras_alteracoes_descricao',
                )
            },
        ),
    )

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    def __init__(self, *args, **kwargs):
        medico = kwargs.pop('medico', None)
        super().__init__(*args, **kwargs)

        if not medico:
            self.fields.pop('acv_alterado')
            self.fields.pop('ar_alterado')
            self.fields.pop('abdome_alterado')
            self.fields.pop('mmi_alterados')
            self.fields.pop('mms_alterados')

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        if self.cleaned_data['acv_alterado'] and self.cleaned_data['alteracao_acv'] == '':
            self.add_error("acv_alterado", 'Informe a alteração no aparelho cardiovascular.')
        if self.cleaned_data['ar_alterado'] and self.cleaned_data['alteracao_ar'] == '':
            self.add_error("ar_alterado", 'Informe a alteração no aparelho respiratório.')
        if self.cleaned_data['abdome_alterado'] and self.cleaned_data['alteracao_abdome'] == '':
            self.add_error("abdome_alterado", 'Informe a alteração no abdome.')
        if self.cleaned_data['mmi_alterados'] and self.cleaned_data['alteracao_mmi'] == '':
            self.add_error("mmi_alterados", 'Informe a alteração nos membros inferiores.')
        if self.cleaned_data['mms_alterados'] and self.cleaned_data['alteracao_mms'] == '':
            self.add_error("mms_alterados", 'Informe a alteração nos membros superiores.')
        return cleaned_data

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.abdome_alterado:
            self.instance.alteracao_abdome = ''
        if not self.instance.mmi_alterados:
            self.instance.alteracao_mmi = ''
        if not self.instance.mms_alterados:
            self.instance.alteracao_mms = ''
        if not self.instance.acv_alterado:
            self.instance.alteracao_acv = ''
        if not self.instance.ar_alterado:
            self.instance.alteracao_ar = ''
        self.instance.save()
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class MotivoForm(forms.ModelFormPlus):
    METHOD = 'POST'

    motivo_atendimento = forms.CharField(label='Motivo do Atendimento', widget=forms.Textarea, required=True)
    pressao_sistolica = forms.IntegerField(label='Pressão Sistólica', required=False, max_value=300, min_value=50)
    pressao_diastolica = forms.IntegerField(label='Pressão Diastólica', required=False, max_value=200, min_value=20, help_text='Em mmHg')
    peso = forms.DecimalField(label='Peso', required=False, decimal_places=3, max_value=210, min_value=30, help_text='Em kg')
    pulsacao = forms.IntegerField(label='Pulsação', required=False, max_value=160, min_value=35, help_text='Em bpm')
    respiracao_categoria = forms.ChoiceField(label='Respiração', choices=Motivo.RESPIRACAO_CHOICES, required=False)
    temperatura_categoria = forms.ChoiceField(label='Temperatura', choices=Motivo.TEMPERATURA_CHOICES, required=False)

    ESCALA_DE_DOR_CHOICE = [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [8, 8], [9, 9], [10, 10]]
    escala_dor = forms.ChoiceField(label='Escala de Dor', choices=ESCALA_DE_DOR_CHOICE, required=False, widget=forms.RadioSelect)

    class Meta:
        model = Motivo
        fields = ('motivo_atendimento', 'pressao_sistolica', 'pressao_diastolica', 'estatura', 'peso', 'temperatura_categoria', 'respiracao_categoria', 'pulsacao', 'escala_dor')

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AnamneseForm(forms.ModelFormPlus):
    METHOD = 'POST'

    class Meta:
        model = Anamnese
        fields = (
            'hda',
            'gravida',
            'ectoscopia_alterada',
            'alteracao_ectoscopia',
            'acv_alterado',
            'alteracao_acv',
            'ar_alterado',
            'alteracao_ar',
            'abdome_alterado',
            'alteracao_abdome',
            'mmi_alterados',
            'alteracao_mmi',
            'mms_alterados',
            'alteracao_mms',
            'outras_alteracoes',
            'outras_alteracoes_descricao',
        )

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo == 'M':
            self.fields['gravida'].widget = HiddenInput()
        else:
            self.fields['gravida'] = forms.BooleanField(label='Grávida?', initial=False, required=False)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class IntervencaoEnfermagemForm(forms.FormPlus):
    METHOD = 'POST'

    procedimento_enfermagem = forms.MultipleModelChoiceFieldPlus(ProcedimentoEnfermagem.objects.filter(ativo=True), required=True, label='Procedimento')
    conduta_medica = forms.ModelChoiceField(
        CondutaMedica.objects,
        label='Conduta Médica Associada',
        required=False,
        help_text='Caso esta intervenção esteja associada à alguma conduta médica, informe a conduta médica.',
    )
    descricao = forms.CharField(label='Descrição', required=False, widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        self.atendimento = kwargs.pop('atendimento', None)
        super().__init__(*args, **kwargs)
        if not CondutaMedica.objects.filter(atendimento=self.atendimento, encaminhado_enfermagem=True, atendido=False).exists():
            del self.fields['conduta_medica']
        else:
            self.fields['conduta_medica'].queryset = CondutaMedica.objects.filter(atendimento=self.atendimento, encaminhado_enfermagem=True, atendido=False)


class HipoteseDiagnosticaForm(forms.FormPlus):
    METHOD = 'POST'

    cids = forms.MultipleModelChoiceFieldPlus(queryset=Cid.objects.filter(ativo=True), label='CID', required=True)
    sigilo = forms.CharField(label='Sigilo', required=False, widget=forms.Textarea(), help_text='Esta informação só poderá ser visualizada pela pessoa que cadastrou')


class CondutaMedicaForm(forms.ModelFormPlus):
    METHOD = 'POST'

    class Meta:
        model = CondutaMedica
        fields = ('conduta', 'encaminhado_enfermagem', 'encaminhado_fisioterapia')

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class FecharAtendimentoForm(forms.ModelFormPlus):
    METHOD = 'POST'

    obs_fechado = forms.CharField(label='Observação de Fechamento', widget=forms.Textarea, required=False)

    class Meta:
        model = Atendimento
        fields = ('obs_fechado',)


class CancelarAtendimentoForm(forms.ModelFormPlus):
    METHOD = 'POST'

    obs_cancelado = forms.CharField(label='Observação de Cancelamento', widget=forms.Textarea, required=False)

    class Meta:
        model = Atendimento
        fields = ('obs_cancelado',)


class FiltroEstatisticaGeralForm(forms.FormPlus):
    PERIODO_LETIVO_CHOICES = [[1, '1'], [2, '2']]

    campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=True, empty_label="Todos")
    ano_ingresso = forms.ModelChoiceField(Ano.objects, label='Ano de Ingresso', required=False)
    periodo_ingresso = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período de Ingresso', required=False)
    modalidade = forms.ModelChoiceField(Modalidade.objects, label='Modalidade', required=False)
    METHOD = 'GET'
    SUBMIT_LABEL = 'Buscar'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
            uo_id = get_uo(self.request.user).id
            self.fields['campus'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(pk=uo_id), required=False)
            self.fields['campus'].initial = uo_id


class EstatisticasAtendimentosOld1Form(forms.FormPlus):
    data_inicio = forms.DateFieldPlus(label='Início')
    data_termino = forms.DateFieldPlus(label='Término')
    uo = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label="Todos")

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(EstatisticasAtendimentosForm, self).__init__(*args, **kwargs)
        if not self.request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.uo().filter(pk=get_uo(self.request.user).id)


class OdontogramaForm(forms.FormPlus):
    queixa_principal = forms.CharFieldPlus(label='Queixa Principal', required=False, widget=forms.Textarea())
    situacao_clinica = forms.ModelChoiceField(
        label='Situação Clínica', required=False, queryset=SituacaoClinica.objects.exclude(id__in=[SituacaoClinica.CALCULO, SituacaoClinica.SANGRAMENTO]), initial=1
    )
    faces = forms.CharField(widget=forms.HiddenInput(), required=False, label='Faces de dentes')

    SUBMIT_LABEL = 'Salvar'

    def __init__(self, *args, **kwargs):
        self.queixa_principal = kwargs.pop('queixa_principal', None)
        self.mostra_queixa = kwargs.pop('mostra_queixa', None)
        super().__init__(*args, **kwargs)
        if self.mostra_queixa:
            self.fields['queixa_principal'].initial = self.queixa_principal
        else:
            del self.fields['queixa_principal']


class ProcedimentoOdontologicoForm(forms.FormPlus):
    procedimento = forms.ModelMultipleChoiceField(
        label='Procedimento', required=True, widget=FilteredSelectMultiplePlus('', True), queryset=ProcedimentoOdontologia.objects.order_by('denominacao')
    )
    regiao_bucal = forms.ChoiceField(label='Região Bucal', choices=RegiaoBucal.REGIAOBUCAL_CHOICES, required=False)
    observacao = forms.CharField(label='Observações', widget=forms.Textarea(), required=False)
    faces_marcadas = forms.CharField(widget=forms.HiddenInput(), required=False, label='Faces de dentes')

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        if not self.errors:
            procedimentos = cleaned_data['procedimento']
            if not cleaned_data['faces_marcadas'] and not cleaned_data['regiao_bucal'] and procedimentos.exclude(id=ProcedimentoOdontologia.EXAME_CLINICO).exists():
                raise forms.ValidationError('Selecione, no mínimo, um dente, face ou região bucal, para registrar o procedimento.')
        else:
            self.data = self.data.copy()
            self.data.clear()

        return cleaned_data

    def __init__(self, *args, **kwargs):
        self.eh_dentista = kwargs.pop('eh_dentista', None)
        super().__init__(*args, **kwargs)
        if self.eh_dentista:
            self.fields['procedimento'].queryset = ProcedimentoOdontologia.objects.filter(pode_odontologo=True).order_by('denominacao')
        else:
            self.fields['procedimento'].queryset = ProcedimentoOdontologia.objects.filter(pode_tecnico=True).order_by('denominacao')


class ExamePeriodontalForm(forms.ModelFormPlus):
    sextante = forms.MultipleChoiceField(choices=ExamePeriodontal.SEXTANTE_CHOICES[1:], label='Sextante', widget=FilteredSelectMultiplePlus('', True))

    class Meta:
        model = ExamePeriodontal
        fields = ('ocorrencia', 'sextante')

    def __init__(self, *args, **kwargs):
        self.atendimento = kwargs.pop('atendimento', None)
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        if not self.cleaned_data.get('ocorrencia'):
            raise forms.ValidationError('Informe a ocorrência.')
        if not self.cleaned_data.get('sextante'):
            raise forms.ValidationError('Selecione um ou mais sextantes.')

        texto = ''
        for item in self.cleaned_data.get('sextante'):
            texto = texto + item + '; '
        texto = texto[:-2]
        if ExamePeriodontal.objects.filter(atendimento=self.atendimento, ocorrencia=self.cleaned_data['ocorrencia'], sextante=texto).exists():
            raise forms.ValidationError('Esta ocorrência já foi cadastrada.')


class ExameEstomatologicoForm(forms.ModelFormPlus):
    class Meta:
        model = ExameEstomatologico
        fields = ('labios', 'lingua', 'gengiva', 'assoalho', 'mucosa_jugal', 'palato_duro', 'palato_mole', 'rebordo', 'cadeia_ganglionar', 'tonsilas_palatinas', 'atm', 'oclusao')


class IndicarProcedimentoForm(forms.ModelFormPlus):
    dente = forms.ChoiceField(label='Dente', choices=PlanoTratamento.DENTES_CHOICE, required=False)
    face = forms.ChoiceField(label='Face', choices=PlanoTratamento.FACES_CHOICES, required=False)
    sextante = forms.ChoiceField(label='Sextante', choices=ExamePeriodontal.SEXTANTE_CHOICES, required=False)
    situacao_clinica = forms.ModelChoiceField(SituacaoClinica.objects.order_by('descricao'), required=False)
    procedimento = forms.ModelChoiceField(ProcedimentoOdontologia.objects.order_by('denominacao'))

    class Meta:
        model = PlanoTratamento
        fields = ('dente', 'face', 'sextante', 'situacao_clinica', 'procedimento')

    def __init__(self, *args, **kwargs):
        self.edicao = kwargs.pop('edicao', None)
        self.situacao_clinica = kwargs.pop('situacao_clinica', None)
        super().__init__(*args, **kwargs)
        procedimentos_indicados = ProcedimentoIndicado.objects.filter(situacao_clinica=self.situacao_clinica)
        self.fields['situacao_clinica'].label = 'Situação Clínica'
        if self.edicao:
            self.fields['procedimento'].queryset = ProcedimentoOdontologia.objects.filter(id__in=procedimentos_indicados.values_list('procedimento__id', flat=True))
            del self.fields['dente']
            del self.fields['situacao_clinica']
            del self.fields['face']
            del self.fields['sextante']

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        if not self.edicao and self.cleaned_data.get('dente') == '0' and self.cleaned_data.get('sextante') == '0':
            self.add_error("dente", 'Selecione um dente ou um sextante')
        return cleaned_data


class InformacaoAdicionalForm(forms.ModelFormPlus):
    informacao = forms.CharField(label='Informação Adicional', widget=forms.Textarea, required=True)

    class Meta:
        model = InformacaoAdicional
        fields = ('informacao',)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class PessoaExternaForm(forms.ModelFormPlus):
    cpf = forms.BrCpfField()

    class Meta:
        model = PessoaExterna
        fields = ('nome', 'cpf', 'nascimento_data', 'nome_mae', 'sexo')

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not cpfcnpj.validate(cpf):
            self.add_error('cpf', 'O CPF informado não é válido.')
        if self.instance and not self.instance.pk and PessoaExterna.objects.filter(cpf=cpf):
            self.add_error('cpf', 'O CPF informado já está cadastrado.')

        return cpf


class EstatisticasAtendimentosOld2Form(forms.FormPlus):
    data_inicio = forms.DateFieldPlus(label='Início')
    data_termino = forms.DateFieldPlus(label='Término')
    uo = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label="Todos")

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(EstatisticasAtendimentosForm, self).__init__(*args, **kwargs)
        if not self.request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.uo().filter(pk=get_uo(self.request.user).id)


class AtendimentoPsicologicoForm(forms.ModelFormPlus):
    queixa_principal = forms.MultipleModelChoiceField(QueixaPsicologica.objects.filter(ativo=True), label='Queixa Principal', required=False)
    queixa_identificada = forms.MultipleModelChoiceField(QueixaPsicologica.objects.filter(ativo=True), label='Queixa Identificada', required=False)
    descricao_encaminhamento_externo = forms.CharField(label='Descrição do Encaminhamento Externo', required=False, widget=forms.Textarea)
    intervencao = forms.CharField(
        label='Intervenção / Encaminhamento',
        required=False,
        widget=forms.Textarea,
        help_text='Informar que recursos utilizou. Entrevista individual com o aluno, pais e/ou colegas de turma. Uso de testes, observação, análise de registros do aluno (desenho, carta), análise de produções do aluno.',
    )

    class Meta:
        model = AtendimentoPsicologia
        fields = (
            'motivo_chegada',
            'descricao_encaminhamento_externo',
            'queixa_principal',
            'descricao_queixa_outros',
            'queixa_identificada',
            'descricao_queixa_identificada_outros',
            'intervencao',
        )

    class Media:
        js = ('/static/saude/js/form_hide.js',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['motivo_chegada'].required = True
        if self.instance.pk:
            self.initial['queixa_principal'] = [queixa.pk for queixa in self.instance.queixa_principal.filter(ativo=True)]
            self.initial['queixa_identificada'] = [queixa.pk for queixa in self.instance.queixa_identificada.filter(ativo=True)]

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        if not self.cleaned_data.get('queixa_principal'):
            self.add_error("queixa_principal", 'Selecione pelo menos um motivo de queixa.')
        return cleaned_data

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AnamnesePsicologiaForm(forms.ModelFormPlus):
    historico_queixa = forms.CharField(
        label='Histórico da Queixa',
        required=False,
        widget=forms.Textarea,
        help_text='Impressão diagnóstica: Registrar a compleição e suas impressões acerca da queixa, dos conteúdos abordados e da condução do atendimento.',
    )
    dimensao_familiar = forms.CharField(
        label='Dimensão Familiar',
        required=False,
        widget=forms.Textarea,
        help_text='Relacionamento familiar, árvore genealógica, moradores na residência, escolaridade, emprego/renda, apoio às atividades discentes, condições para dedicar-se aos estudos (bolsas, estrutura física), presença de alcoolismo, entorpecentes, violência doméstica, condições de moradia. Verificar se a mãe do aluno desejou a gravidez, se houve acompanhamento médico, presença de patologias na família.',
    )
    dimensao_escolar = forms.CharField(
        label='Dimensão Escolar',
        required=False,
        widget=forms.Textarea,
        help_text='Identificação com o curso, critérios de escolha do curso, interferência familiar nessa escolha. Observar comportamentos no ambiente escolar (em sala e fora dela), percepções dos professores e ETEP, relacionamento com colegas e professores, notas e frequência, uso do espaço escolar (onde senta em sala, que espaços frequenta na escola), participação dos pais na vida escolar, percepção do aluno acerca dos professores (estratégia de ensino aprendizagem), da Instituição e demais aspectos curriculares e pedagógicos.',
    )
    dimensao_emocional = forms.CharField(
        label='Dimensão Emocional (saúde mental/física)',
        required=False,
        widget=forms.Textarea,
        help_text='Avaliar indícios de desarranjo emocional/mental (ansiedade, torpor, alterações de humor – observar unhas, cabelos, presença de espinhas, compleição física, imagem corporal que o aluno tem de si, cuidado com corpo e a higiene de maneira geral).Verificar qualidade do sono e alimentação. Observar presença de erupções na pele, por exemplo. Observar habilidades sensório-motora, perceptivas-motora e conceituais.',
    )
    dimensao_projetos_vida = forms.CharField(
        label='Dimensão dos Projetos de Vida',
        required=False,
        widget=forms.Textarea,
        help_text='Observar planos de vida (objetivos, estratégias para atingimento de metas), desejo e busca por mudanças, interesse pela vida (tendência suicida), dedicação aos estudos. Outras atividades que desenvolve (religião, grupos, música, esporte, lazer, atividades domésticas)',
    )
    dimensao_social = forms.CharField(
        label='Dimensão Social',
        required=False,
        widget=forms.Textarea,
        help_text='Rotina de vida (pedir para falar resumidamente), interação social, desenvolvimento da linguagem (uso de gírias, voz nasalizada, dicção ruim, disfemia (gagueira)).',
    )

    class Meta:
        model = AnamnesePsicologia
        fields = ('historico_queixa', 'dimensao_familiar', 'dimensao_escolar', 'dimensao_emocional', 'dimensao_projetos_vida', 'dimensao_social')

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        if (
            not self.cleaned_data.get('historico_queixa')
            and not self.cleaned_data.get('dimensao_familiar')
            and not self.cleaned_data.get('dimensao_escolar')
            and not self.cleaned_data.get('dimensao_emocional')
            and not self.cleaned_data.get('dimensao_projetos_vida')
            and not self.cleaned_data.get('dimensao_social')
        ):
            self.add_error("historico_queixa", 'Preencha pelo menos um campo para salvar o registro.')
        return cleaned_data


class EstatisticasAtendimentosForm(forms.FormPlus):
    METHOD = 'GET'
    data_inicio = forms.DateFieldPlus(label='Início', required=False)
    data_termino = forms.DateFieldPlus(label='Término', required=False)
    uo = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label="Todos")
    vinculo = forms.ChoiceField(label='Vínculo', required=False, choices=Vinculo.VINCULO_CHOICES)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.exibe_vinculo = kwargs.pop('exibe_vinculo', None)
        super().__init__(*args, **kwargs)
        if not self.exibe_vinculo:
            del self.fields['vinculo']

        if not self.request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
            uo_id = get_uo(self.request.user).id
            self.fields['uo'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(pk=uo_id), required=False)
            self.fields['uo'].initial = uo_id

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)

        if self.cleaned_data.get('data_inicio') and not self.cleaned_data.get('data_termino'):
            self.add_error("data_termino", 'Informe a data final.')

        if self.cleaned_data.get('data_inicio') and self.cleaned_data.get('data_termino') and (self.cleaned_data.get('data_termino') < self.cleaned_data.get('data_inicio')):
            self.add_error("data_termino", 'A data final deve ser maior do que a data inicial.')

        return cleaned_data


class AtividadeGrupoForm(forms.ModelFormPlus):
    motivo = forms.CharField(label='Motivo', widget=forms.Textarea, required=False)
    detalhamento = forms.CharField(label='Detalhamento', widget=forms.Textarea, required=False)
    num_participantes = forms.IntegerField(label='Número de Participantes', min_value=0, required=True)
    vinculos_responsaveis = forms.MultipleModelChoiceFieldPlus(VinculoPessoa.objects, label='Responsáveis')
    data_inicio = forms.DateTimeFieldPlus(label='Data de Início')
    data_termino = forms.DateTimeFieldPlus(label='Data de Término')
    recurso_necessario = forms.CharFieldPlus(label='Recurso Necessário', widget=forms.Textarea())
    uo = forms.ModelChoiceFieldPlus(label='Campus', queryset=UnidadeOrganizacional.objects.uo())

    class Meta:
        model = AtividadeGrupo
        fields = (
            'nome_evento',
            'tipo',
            'eh_sistemica',
            'tema',
            'uo',
            'motivo',
            'detalhamento',
            'publico_alvo',
            'recurso_necessario',
            'num_participantes',
            'data_inicio',
            'data_termino',
            'turno',
            'solicitante',
            'vinculos_responsaveis',
            'anexo',
        )

    def __init__(self, *args, **kwargs):
        self.eh_acao_educativa = kwargs.pop('eh_acao_educativa', None)
        super().__init__(*args, **kwargs)
        if self.eh_acao_educativa:
            del self.fields['uo']
            if not self.instance.pk:
                del self.fields['tipo']
                del self.fields['tema']
                del self.fields['num_participantes']
                del self.fields['vinculos_responsaveis']
            self.fields['nome_evento'].required = True
            self.fields['recurso_necessario'].required = True
        else:
            self.fields['tipo'].required = True
            self.fields['tema'].required = True

    def clean(self):
        cleaned_data = super().clean()
        if self.cleaned_data.get('data_inicio') and self.cleaned_data.get('data_termino') and self.cleaned_data.get('data_inicio') > self.cleaned_data.get('data_termino'):
            self.add_error('data_termino', 'A data de término deve ser maior do que a data de início.')
        return cleaned_data


class AnotacaoInterdisciplinarForm(forms.Form):
    anotacao = forms.CharField(label='Anotação', widget=forms.Textarea, required=True)


class TipoVacinaForm(forms.Form):
    METHOD = 'GET'
    vacina = forms.ModelChoiceField(Vacina.objects.order_by('nome'), label='Vacina', required=False)
    campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label="Todos")
    data_inicial = forms.DateFieldPlus(label='Data Inicial', required=False)
    data_final = forms.DateFieldPlus(label='Data Final', required=False)
    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Alunos por Turma', required=False, widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if not self.request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            uo_id = get_uo(self.request.user).id
            self.fields['campus'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(pk=uo_id), required=False)
            self.fields['campus'].initial = uo_id

    def clean(self):
        if not any([v for k, v in self.cleaned_data.items() if v]):
            raise forms.ValidationError('Escolha algum filtro.')
        return self.cleaned_data


class CartaoVacinalForm(forms.Form):
    METHOD = 'GET'
    campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label="Todos")
    categoria = forms.ChoiceField(label='Categoria', required=False, choices=(('1', 'Aluno'), ('2', 'Servidor'), ('3', 'Prestador de Serviço'), ('4', 'Comunidade Externa')))
    ano_ingresso = forms.ModelChoiceField(Ano.objects.ultimos(), label='Alunos por Ano de Ingresso', required=False)
    modalidade = forms.ModelChoiceField(label='Alunos por Modalidade', required=False, queryset=Modalidade.objects.all(), empty_label='Todos')
    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Alunos por Turma', required=False, widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if not self.request.user.groups.filter(name__in=Especialidades.GRUPOS_VE_GRAFICOS_TODOS):
            uo_id = get_uo(self.request.user).id
            self.fields['campus'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(pk=uo_id), required=False)
            self.fields['campus'].initial = uo_id


class TipoConsultaForm(forms.ModelFormPlus):
    tipo_consulta = forms.ModelMultipleChoiceField(
        label='Tipos de Consulta', required=True, widget=FilteredSelectMultiplePlus('', True), queryset=TipoConsultaOdontologia.objects.filter(ativo=True).order_by('descricao')
    )

    class Meta:
        model = Odontograma
        fields = ('tipo_consulta',)


class ExameImagemForm(forms.ModelFormPlus):
    data_realizado = forms.DateFieldPlus(label='Data de Realização', required=True)
    resultado = forms.CharFieldPlus(label='Resultado', widget=forms.Textarea(), required=False)

    class Meta:
        model = ExameImagem
        fields = ('nome', 'data_realizado', 'resultado', 'sigiloso')


class ExameLaboratorialForm(forms.ModelFormPlus):
    data_realizado = forms.DateFieldPlus(label='Data de Realização', required=True)
    observacao = forms.CharFieldPlus(label='Observação', widget=forms.Textarea(), required=False)

    SUBMIT_LABEL = 'Continuar >>'
    fieldsets = (('Dados do Exame', {'fields': ('categoria', 'data_realizado', 'observacao', 'sigiloso', 'url_origem')}),)
    url_origem = forms.CharFieldPlus(label='URL de origem', widget=forms.HiddenInput(), required=False)

    class Meta:
        model = ExameLaboratorial
        fields = ('categoria', 'data_realizado', 'observacao', 'sigiloso')

    def __init__(self, *args, **kwargs):
        self.exame_anterior = kwargs.pop('exame_anterior', None)
        self.url_origem = kwargs.pop('url', None)
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = True
        if self.exame_anterior:
            self.fields['data_realizado'].initial = self.exame_anterior.data_realizado
            self.fields['observacao'].initial = self.exame_anterior.observacao
            self.fields['sigiloso'].initial = self.exame_anterior.sigiloso
        self.fields['url_origem'].initial = self.url_origem


class ValoresExameLaboratorialForm(forms.Form):
    url_origem = forms.CharFieldPlus(label='URL de origem', widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        self.exame = kwargs.pop('exame', None)
        self.url_origem = kwargs.pop('url', None)
        super().__init__(*args, **kwargs)
        self.fields['url_origem'].initial = self.url_origem
        nome_campos = ''
        for i in TipoExameLaboratorial.objects.filter(ativo=True, categoria=self.exame.categoria).order_by('nome'):
            label = f'{i.nome} ({i.unidade})'
            self.fields[f"{i.id}"] = forms.CharField(label=label, required=False)
            nome_campos = nome_campos + f'{i.id}, '


class EditarExameLaboratorialForm(forms.ModelFormPlus):
    categoria = forms.ModelChoiceField(label='Categoria', queryset=CategoriaExameLaboratorial.objects, widget=AutocompleteWidget(readonly=True))
    data_realizado = forms.DateFieldPlus(label='Data de Realização', required=True)
    observacao = forms.CharFieldPlus(label='Observação', widget=forms.Textarea(), required=False)

    fieldsets = (('Dados do Exame', {'fields': ('categoria', 'data_realizado', 'observacao', 'sigiloso')}),)

    class Meta:
        model = ExameLaboratorial
        fields = ('categoria', 'data_realizado', 'observacao', 'sigiloso')

    def __init__(self, *args, **kwargs):
        self.valores = kwargs.pop('valores', None)
        super().__init__(*args, **kwargs)
        lista = list()
        for i in self.valores:
            label = f'{i.tipo.nome} ({i.tipo.unidade})'
            self.fields["%d" % i.id] = forms.CharField(label=label, required=False, initial=i.valor)
            lista.append(f'{i.id}')

        self.fieldsets = self.fieldsets + (('Valores do Exame', {'fields': (lista)}),)


class HipoteseDiagnosticaModelForm(forms.ModelFormPlus):
    sigilo = forms.CharField(label='Sigilo', required=False, widget=forms.Textarea(), help_text='Esta informação só poderá ser visualizada pela pessoa que cadastrou')

    class Meta:
        model = HipoteseDiagnostica
        fields = ('cid', 'sigilo')


class AtendimentoMultidisciplinarForm(forms.ModelFormPlus):
    procedimento = forms.ModelMultipleChoiceField(
        queryset=ProcedimentoMultidisciplinar.objects.filter(ativo=True), label='Procedimentos', widget=FilteredSelectMultiplePlus('', True)
    )

    class Meta:
        model = AtendimentoMultidisciplinar
        fields = ('procedimento', 'observacao')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['procedimento'] = [t.pk for t in self.instance.procedimento.all()]

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AtendimentoNutricaoMotivoForm(forms.ModelFormPlus):
    motivo = forms.ModelMultipleChoiceField(
        MotivoAtendimentoNutricao.objects.filter(ativo=True), label='Motivo do Atendimento', required=True, widget=FilteredSelectMultiplePlus('', True)
    )
    observacoes = forms.CharFieldPlus(label='Observações', required=False, widget=forms.Textarea())

    class Meta:
        model = AtendimentoNutricao
        fields = ('motivo', 'observacoes')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['motivo'] = self.instance.motivo.values_list('id', flat=True)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AtendimentoNutricaoAvalGastroForm(forms.ModelFormPlus):
    avaliacao_gastrointestinal = forms.ModelMultipleChoiceField(
        AvaliacaoGastroIntestinal.objects.filter(ativo=True), label='Avaliação Gastrointestinal', required=True, widget=FilteredSelectMultiplePlus('', True)
    )

    class Meta:
        model = AtendimentoNutricao
        fields = ('avaliacao_gastrointestinal',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['avaliacao_gastrointestinal'] = self.instance.avaliacao_gastrointestinal.values_list('id', flat=True)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AtendimentoNutricaoDadosAlimentacaoForm(forms.ModelFormPlus):
    apetite = forms.CharFieldPlus(label='Apetite', widget=forms.Textarea())
    aversoes = forms.CharFieldPlus(label='Aversões', widget=forms.Textarea())
    preferencias = forms.CharFieldPlus(label='Preferências', widget=forms.Textarea())
    consumo_liquidos = forms.CharFieldPlus(label='Consumo de Água/Líquidos', widget=forms.Textarea())

    class Meta:
        model = AtendimentoNutricao
        fields = ('apetite', 'aversoes', 'preferencias', 'consumo_liquidos')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AtendimentoNutricaoRestricaoAlimentarForm(forms.ModelFormPlus):
    restricao_alimentar = forms.ModelMultipleChoiceField(
        RestricaoAlimentar.objects.filter(ativo=True), label='Restrição Alimentar', required=True, widget=FilteredSelectMultiplePlus('', True)
    )

    class Meta:
        model = AtendimentoNutricao
        fields = ('restricao_alimentar',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['restricao_alimentar'] = self.instance.restricao_alimentar.values_list('id', flat=True)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AtendimentoNutricaoConsumoForm(forms.ModelFormPlus):
    refeicao = forms.CharFieldPlus(label='Refeição')
    horario_consumo_alimentacao = forms.TimeFieldPlus(label='Horário de Consumo')
    local_consumo_alimentacao = forms.CharFieldPlus(label='Local de Consumo')
    alimentos_consumidos = forms.CharFieldPlus(label='Alimentos Consumidos / Medidas Caseiras', widget=forms.Textarea(), help_text='Separe as informações com ";"')

    class Meta:
        model = ConsumoNutricao
        fields = ('refeicao', 'horario_consumo_alimentacao', 'local_consumo_alimentacao', 'alimentos_consumidos')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AtendimentoNutricaoDiagnosticoForm(forms.ModelFormPlus):
    diagnostico_nutricional = forms.ModelMultipleChoiceField(
        DiagnosticoNutricional.objects.filter(ativo=True), label='Diagnóstico Nutricional', required=True, widget=FilteredSelectMultiplePlus('', True)
    )
    diagnostico_nutricional_obs = forms.CharFieldPlus(label='Observações', required=False, widget=forms.Textarea())

    class Meta:
        model = AtendimentoNutricao
        fields = ('diagnostico_nutricional', 'diagnostico_nutricional_obs')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['diagnostico_nutricional'] = self.instance.diagnostico_nutricional.values_list('id', flat=True)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AtendimentoNutricaoCategoriaTrabalhoForm(forms.ModelFormPlus):
    class Meta:
        model = AtendimentoNutricao
        fields = ('categoria_trabalho',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class AtendimentoNutricaoCondutaForm(forms.ModelFormPlus):
    class Meta:
        model = AtendimentoNutricao
        fields = ('conduta',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AtendimentoEspecialidade.cadastrar(self.instance.atendimento, self.request)


class PlanoAlimentarForm(forms.ModelFormPlus):
    orientacao_nutricional = forms.ModelMultipleChoiceField(
        label='Orientação Nutricional', required=True, widget=FilteredSelectMultiplePlus('', True), queryset=OrientacaoNutricional.objects.filter(ativo=True).order_by('descricao')
    )
    receita_nutricional = forms.ModelMultipleChoiceField(
        label='Receitas', required=False, widget=FilteredSelectMultiplePlus('', True), queryset=ReceitaNutricional.objects.filter(ativo=True).order_by('descricao')
    )

    class Meta:
        model = PlanoAlimentar
        fields = ('orientacao_nutricional', 'cardapio', 'receita_nutricional', 'sugestoes_leitura', 'plano_alimentar_liberado')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['orientacao_nutricional'] = self.instance.orientacao_nutricional.values_list('id', flat=True)
            self.initial['receita_nutricional'] = self.instance.receita_nutricional.values_list('id', flat=True)


class RelatorioOdontologicoForm(forms.FormPlus):
    METHOD = 'GET'
    campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label="Todos")
    categoria = forms.ChoiceField(label='Categoria', choices=Atendimento.CATEGORIAS_VINCULO, required=False)
    data_inicial = forms.DateFieldPlus(label='Data Inicial', required=False)
    data_final = forms.DateFieldPlus(label='Data Final', required=False)


class CartaoSUSAlunoForm(forms.ModelFormPlus):
    class Meta:
        model = Aluno
        fields = ('cartao_sus',)


class ObsRegistroExecucaoForm(forms.FormPlus):
    obs = forms.CharFieldPlus(label='Observação', widget=forms.Textarea(), required=False)


class MarcadorConsumoAlimentarForm(forms.FormPlus):
    CHOICES = (
        ('Não comi nos últimos 7 dias', 'Não comi nos últimos 7 dias'),
        ('1 dia nos últimos 7 dias', '1 dia nos últimos 7 dias'),
        ('2 dias nos últimos 7 dias', '2 dias nos últimos 7 dias'),
        ('3 dias nos últimos 7 dias', '3 dias nos últimos 7 dias'),
        ('4 dias nos últimos 7 dias', '4 dias nos últimos 7 dias'),
        ('5 dias nos últimos 7 dias', '5 dias nos últimos 7 dias'),
        ('6 dias nos últimos 7 dias', '6 dias nos últimos 7 dias'),
        ('Todos os 7 últimos dias', 'Todos os 7 últimos dias'),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        for i in PerguntaMarcadorNutricao.objects.filter(ativo=True):
            label = f'{i.pergunta}'
            if i.tipo_resposta == PerguntaMarcadorNutricao.UNICA_ESCOLHA:
                self.fields[f"pergunta_{i.id}"] = forms.ModelChoiceField(queryset=i.pergunta_marcador, label=label, required=True)
            elif i.tipo_resposta == PerguntaMarcadorNutricao.MULTIPLA_ESCOLHA:
                self.fields[f"pergunta_{i.id}"] = forms.MultipleModelChoiceField(queryset=i.pergunta_marcador, label=label, required=True)

        for i in FrequenciaPraticaAlimentar.objects.filter(ativo=True):
            label = f'Nos últimos sete dias, em quantos dias você consumiu os seguintes alimentos ou bebidas: {i.descricao}'
            self.fields[f"frequencia_{i.id}"] = forms.ChoiceField(label=label, required=True, choices=MarcadorConsumoAlimentarForm.CHOICES)


class DataHoraAtendimentoPsicologicoForm(forms.ModelFormPlus):
    class Meta:
        model = AtendimentoPsicologia
        fields = ('data_atendimento',)


class AnexoPsicologiaForm(forms.ModelFormPlus):
    class Meta:
        model = AnexoPsicologia
        fields = ('descricao', 'arquivo')


class RelatorioAtendimentoForm(forms.FormPlus):
    METHOD = 'GET'
    data_inicial = forms.DateFieldPlus(label='Data Inicial', required=False)
    data_final = forms.DateFieldPlus(label='Data Final', required=False)
    campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label="Todos")
    modalidade = forms.ModelChoiceField(label='Modalidade de Ensino', queryset=Modalidade.objects, required=False, empty_label="Todos")
    curso = forms.ModelChoiceField(
        label='Curso',
        queryset=CursoCampus.objects.all(),
        required=False,
        widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS),
        help_text='Permite buscar todos os cursos, inclusive os de modalidade FIC',
    )
    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Filtrar por Turma', required=False, widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS))
    sexo = forms.ChoiceField(label='Sexo', choices=[['', 'Todos'], ['M', 'Masculino'], ['F', 'Feminino']], required=False)
    idade = forms.CharFieldPlus(label='Idade', required=False)
    participante = forms.BooleanField(label='Participantes de Programas da Assistência Estudantil', required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if not self.request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
            uo_id = get_uo(self.request.user).id
            self.fields['campus'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(pk=uo_id), required=False)
            self.fields['campus'].initial = uo_id


class HorarioAtendimentoForm(forms.FormPlus):
    METHOD = 'GET'
    data = forms.DateFieldPlus(label='Data Inicial')
    data_fim = forms.DateFieldPlus(label='Data Final', required=False, help_text='Deixar em branco quando não for gerar horários para um período.')
    hora_inicio_1 = forms.TimeFieldPlus(label='Horário de Início')
    hora_termino_1 = forms.TimeFieldPlus(label='Horário de Término')
    duracao = forms.IntegerField(label='Duração de cada atendimento (em minutos')
    especialidade = forms.ChoiceField(label='Especialidade')
    profissional = forms.ModelChoiceFieldPlus(queryset=User.objects, label='Odontólogo')
    campus_escolhido = forms.ModelChoiceFieldPlus(queryset=UnidadeOrganizacional.objects.uo(), label='Campus do Atendimento')
    SUBMIT_LABEL = 'Gerar Horários'

    fieldsets = (
        ('Especialidade', {'fields': ('profissional', 'especialidade')}),
        ('Data', {'fields': ('data', 'data_fim')}),
        ('Gerar Horários', {'fields': (('hora_inicio_1', 'hora_termino_1', 'duracao'),)}),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.especialidade_professional = kwargs.pop('especialidade_professional', None)
        self.eh_atendente = kwargs.pop('eh_atendente', None)
        super().__init__(*args, **kwargs)
        if self.eh_atendente:
            del self.fields['campus_escolhido']
            self.fields['especialidade'].choices = [(self.especialidade_professional, self.especialidade_professional)]

            self.fields['profissional'].queryset = User.objects.filter(id__in=UsuarioGrupo.objects.filter(group__name='Odontólogo').values_list('user', flat=True))
        else:
            del self.fields['profissional']
            self.fieldsets = (
                ('Campus do Atendimento', {'fields': ('campus_escolhido',)}),
                ('Especialidade', {'fields': ('profissional', 'especialidade')}),
                ('Data', {'fields': (('data', 'data_fim'),)}),
                ('Gerar Horários', {'fields': (('hora_inicio_1', 'hora_termino_1', 'duracao'),)}),
            )
            self.fields['campus_escolhido'].initial = get_uo(self.request.user).id
            if self.request.user.has_perm('ae.save_caracterizacao_do_campus'):
                self.fields['especialidade'].choices = [(self.especialidade_professional, self.especialidade_professional)]
            else:
                self.fields['especialidade'].choices = [
                    (self.especialidade_professional, self.especialidade_professional),
                    (Especialidades.AVALIACAO_BIOMEDICA, Especialidades.AVALIACAO_BIOMEDICA),
                ]
        if HorarioAtendimento.objects.filter(cadastrado_por_vinculo=self.request.user.get_vinculo()).exists():
            registro = HorarioAtendimento.objects.filter(cadastrado_por_vinculo=self.request.user.get_vinculo()).order_by('-id')[0]
            diferenca = datetime.datetime.combine(registro.data, registro.hora_termino) - datetime.datetime.combine(registro.data, registro.hora_inicio)
            valor = diferenca.seconds // 60 % 60
            self.fields['duracao'].initial = valor

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        data = self.cleaned_data.get('data')
        data_fim = self.cleaned_data.get('data_fim')
        if data:
            hora_inicio = self.cleaned_data.get('hora_inicio_1')
            hora_termino = self.cleaned_data.get('hora_termino_1')
            if hora_inicio and not hora_termino:
                self.add_error("hora_termino_1", 'Informe a hora de término deste agendamento.')
            elif not hora_inicio and hora_termino:
                self.add_error("hora_inicio_1", 'Informe a hora de início deste agendamento.')
            elif hora_inicio and hora_termino:
                if hora_inicio > hora_termino:
                    self.add_error("hora_inicio_1", 'A hora de início deve ser menor do que a hora de término.')
            if data_fim and data_fim < data:
                self.add_error("data_fim", 'A data de término deve ser maior do que a data de início.')
        return cleaned_data


def GetConfirmarHorarioAtendimentoForm(lista=None):
    fields = dict()
    if lista:
        lista_nomes = list()
        for contador, elemento in enumerate(lista, start=1):
            texto = f'{elemento}'
            label = f'{contador}° Horário'
            field_name = f'campo_{contador}'

            fields[field_name] = forms.CharFieldPlus(label=label, required=False, initial=texto)
            fields[field_name].widget.attrs['readonly'] = True

            lista_nomes.append(field_name)

        fields['fieldsets'] = (('Horários Definidos', {'fields': (lista_nomes,)}),)

    return type('ConfirmarHorarioAtendimentoForm', (forms.FormPlus,), fields)


class FiltrarAtendimentosForm(forms.FormPlus):
    METHOD = 'GET'
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=False)
    especialidade = forms.ChoiceField(label='Especialidade', required=False, choices=Especialidades.ESPECIALIDADES_CHOICES)
    data_inicio = forms.DateFieldPlus(label='Data Inicial', required=False)
    data_final = forms.DateFieldPlus(label='Data Final', required=False)
    meus_agendamentos = forms.BooleanField(label='Somente Meus Agendamentos', required=False, initial=False)
    disponivel = forms.BooleanField(label='Somente Disponíveis', required=False, initial=False)

    def __init__(self, *args, **kwargs):
        self.eh_aluno = kwargs.pop('eh_aluno', None)
        self.uo_ids = kwargs.pop('uo_ids', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        hoje = datetime.datetime.today()
        inicio_semana = hoje - timedelta(hoje.weekday())
        fim_semana = inicio_semana + timedelta(4)
        self.fields['data_inicio'].initial = inicio_semana
        self.fields['data_final'].initial = fim_semana
        if not self.request.user.groups.filter(name__in=Especialidades.GRUPOS_RELATORIOS_SISTEMICO):
            self.fields['campus'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(pk__in=self.uo_ids), required=False)
            self.fields['campus'].initial = self.uo_ids[0]
        if self.eh_aluno:
            self.fields['meus_agendamentos'].initial = False

        if self.request.user.has_perm('ae.save_caracterizacao_do_campus'):
            self.fields['especialidade'].choices = [(Especialidades.ASSISTENTE_SOCIAL, Especialidades.ASSISTENTE_SOCIAL)]
        elif not self.request.user.has_perm('saude.add_prontuario') and not self.eh_aluno:
            self.fields['especialidade'].choices = [
                (Especialidades.ODONTOLOGO, Especialidades.ODONTOLOGO),
                (Especialidades.AVALIACAO_BIOMEDICA, Especialidades.AVALIACAO_BIOMEDICA),
            ]
            self.fields['meus_agendamentos'].initial = False

    def clean(self):
        data_inicial = self.cleaned_data.get('data_inicio')
        data_final = self.cleaned_data.get('data_final')
        if bool(data_inicial) != bool(data_final):
            raise forms.ValidationError('Você precisa preencher as duas datas ou nenhuma.')
        if data_inicial and data_inicial > data_final:
            raise forms.ValidationError('Data inicial maior que a final.')
        if data_inicial and data_inicial + datetime.timedelta(days=60) < data_final:
            raise forms.ValidationError('A data final deverá estar até 60 dias da inicial.')
        return self.cleaned_data


class JustificativaCancelamentoHorarioForm(forms.ModelFormPlus):
    motivo_cancelamento = forms.CharFieldPlus(label='Justificativa', widget=forms.Textarea())

    class Meta:
        model = HorarioAtendimento
        fields = ('motivo_cancelamento',)


class MensagemVacinaAtrasadaForm(forms.FormPlus):
    titulo = forms.CharFieldPlus(label='Assunto')
    mensagem = forms.CharFieldPlus(label='Mensagem', widget=forms.Textarea())


class MetaAcaoEducativaForm(forms.ModelFormPlus):
    objetivos = forms.MultipleModelChoiceFieldPlus(ObjetivoAcaoEducativa.objects.filter(ativo=True), label='Objetivos')
    descricao = forms.CharFieldPlus(label='Descrição', required=False, widget=forms.Textarea(), max_length=10000)
    valor = forms.IntegerField(label='Quantidade')

    class Meta:
        model = MetaAcaoEducativa
        fields = ('ano_referencia', 'objetivos', 'descricao', 'indicador', 'valor', 'ativo')

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)
        indicador = self.cleaned_data.get('indicador')
        valor = self.cleaned_data.get('valor')

        if indicador and valor:
            if indicador == MetaAcaoEducativa.PERCENTUAL and (valor < 0 or valor > 100):
                self.add_error("valor", 'O valor do percentual deve ser entre 0 e 100.')
            elif indicador == MetaAcaoEducativa.NUM_ACOES and (valor < 0 or valor > 10):
                self.add_error("valor", 'O número de ações deve ser entre 0 e 10.')

        return cleaned_data


class RegistroAdministrativoForm(forms.ModelFormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', widget=forms.Textarea(), max_length=10000)

    class Meta:
        model = RegistroAdministrativo
        fields = ('descricao',)


class ListaAlunosForm(forms.FormPlus):
    METHOD = 'GET'

    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=True)
    curso = forms.ModelChoiceField(
        label='Curso',
        queryset=CursoCampus.objects.all(),
        required=False,
        widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS),
        help_text='Permite buscar todos os cursos, inclusive os de modalidade FIC',
    )
    alergia_alimentos = forms.BooleanField(label='Alergias à Alimentos', initial=False, required=False)
    alergia_medicamentos = forms.BooleanField(label='Alergias à Medicamentos', initial=False, required=False)
    ver_nome = forms.BooleanField(label='Nome', initial=False, required=False)
    ver_matricula = forms.BooleanField(label='Matrícula', initial=False, required=False)
    ver_curso = forms.BooleanField(label='Curso', initial=False, required=False)
    ver_turma = forms.BooleanField(label='Turma', initial=False, required=False)
    ver_rg = forms.BooleanField(label='RG', initial=False, required=False)
    ver_cpf = forms.BooleanField(label='CPF', initial=False, required=False)

    fieldsets = (
        ('Filtros Gerais', {'fields': (('campus', 'curso'),)}),
        ('Filtros de Dados de Processo Saúde-Doença', {'fields': (('alergia_alimentos', 'alergia_medicamentos'),)}),
        ('Opções de Visualização - Gerais', {'fields': (('ver_nome', 'ver_matricula'), ('ver_curso', 'ver_turma'), ('ver_rg', 'ver_cpf'))}),
    )


class PacienteAgendamentoForm(forms.FormPlus):
    pessoa = forms.ModelChoiceFieldPlus(
        queryset=VinculoPessoa.objects.filter(Q(tipo_relacionamento__model='aluno') | Q(tipo_relacionamento__model='servidor')),
        required=True,
        label='Paciente',
        widget=AutocompleteWidget(search_fields=VinculoPessoa.SEARCH_FIELDS),
    )
    url_origem = forms.CharFieldPlus(label='URL de origem', widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        self.url_origem = kwargs.pop('url_origem', None)
        super().__init__(*args, **kwargs)
        self.fields['url_origem'].initial = self.url_origem


class ProcedimentoOdontologiaForm(forms.ModelFormPlus):
    class Meta:
        model = ProcedimentoOdontologia
        fields = ('pode_odontologo', 'pode_tecnico')


class JustificativaCancelamentoHorariosForm(forms.FormPlus):
    motivo_cancelamento = forms.CharFieldPlus(label='Justificativa', widget=forms.Textarea())


class TipoDocumentoForm(forms.FormPlus):
    tipo = forms.ChoiceField(label='Tipo do Documento', choices=DocumentoProntuario.TIPO_DOCUMENTO_CHOICES)
    SUBMIT_LABEL = 'Continuar >>'

    def __init__(self, *args, **kwargs):
        self.eh_medico_ou_odontologo = kwargs.pop('eh_medico_ou_odontologo', None)
        super().__init__(*args, **kwargs)
        if not self.eh_medico_ou_odontologo:
            self.fields['tipo'].choices = [(1, DocumentoProntuario.DECLARACAO_COMPARECIMENTO)]


class PreencherDocumentoForm(forms.ModelFormPlus):

    EXTRA_BUTTONS = [dict(name='visualizar', value='Pré-visualizar')]

    class Meta:
        model = DocumentoProntuario
        fields = ('data', 'texto')

    class Media:
        js = ['/static/saude/js/PreencherDocumentoForm.js']

    def __init__(self, *args, **kwargs):
        self.tipo = kwargs.pop('tipo', None)
        self.nome_paciente = kwargs.pop('nome_paciente', None)
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            if DocumentoProntuario.TIPO_DOCUMENTO_CHOICES[int(self.tipo)][1] == DocumentoProntuario.ATESTADO:
                self.fields[
                    'texto'
                ].initial = '''
                    Atesto para os devidos fins que {}
                    esteve sob meus cuidados profissionais necessitando ausentar-se de suas
                    atividades estudantis por ______ (________) dia (s), com CID _________.
                '''.format(
                    self.nome_paciente
                )
            elif DocumentoProntuario.TIPO_DOCUMENTO_CHOICES[int(self.tipo)][1] == DocumentoProntuario.DECLARACAO_COMPARECIMENTO:
                self.fields[
                    'texto'
                ].initial = '''
                    Declaro para fins educacionais que {} compareceu a este serviço de saúde, onde
                    foi realizado o atendimento pelo profissional da saúde no período
                    de ___:___h às ___:___h do dia ___/____/___.    Após este atendimento, o mesmo foi encaminhado
                    para ___________________________
                    ____________________________________________________________________________________ .
                '''.format(
                    self.nome_paciente
                )
            else:
                self.fields['texto'].initial = f'''{self.nome_paciente}'''


class AdicionarCartaoVacinalForm(forms.ModelFormPlus):
    class Meta:
        model = Prontuario
        fields = ('cartao_vacinal',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cartao_vacinal'].help_text = 'Se possui cartão vacinal infantil e adulto, favor enviar os dois cartões em um arquivo somente, sendo frente e verso de ambos os cartões.'


class AnamneseFisioterapiaForm(forms.ModelFormPlus):
    class Meta:
        model = AtendimentoFisioterapia
        fields = ('anamnese',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['anamnese'].required = True


class RetornoFisioterapiaForm(forms.ModelFormPlus):
    class Meta:
        model = AtendimentoFisioterapia
        fields = ('descricao_evolucao',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao_evolucao'].required = True


class CondutaFisioterapiaForm(forms.ModelFormPlus):
    class Meta:
        model = AtendimentoFisioterapia
        fields = ('conduta', 'data_retorno')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conduta'].required = True


class HipoteseFisioterapiaForm(forms.ModelFormPlus):
    class Meta:
        model = AtendimentoFisioterapia
        fields = ('hipotese',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hipotese'].required = True


class IntervencaoFisioterapiaForm(forms.FormPlus):
    METHOD = 'POST'

    conduta_medica = forms.ModelChoiceField(
        CondutaMedica.objects,
        label='Conduta Médica Associada',
        required=False,
        help_text='Caso esta intervenção esteja associada à alguma conduta médica, informe a conduta médica.',
    )
    descricao = forms.CharField(label='Descrição', required=False, widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        self.atendimento = kwargs.pop('atendimento', None)
        super().__init__(*args, **kwargs)
        if not CondutaMedica.objects.filter(atendimento=self.atendimento, encaminhado_fisioterapia=True, atendido_fisioterapia=False).exists():
            del self.fields['conduta_medica']
        else:
            self.fields['conduta_medica'].queryset = CondutaMedica.objects.filter(atendimento=self.atendimento, encaminhado_fisioterapia=True, atendido_fisioterapia=False)


class EnviarMensagemForm(forms.FormPlus):
    titulo = forms.CharFieldPlus(label='Título do Email')
    mensagem = forms.CharFieldPlus(label='Mensagem do Email', widget=forms.Textarea())


class PassaporteVacinalCovidForm(forms.ModelFormPlus):
    tem_atestado_medico = forms.ChoiceField(label='Você possui atestado/laudo médico ou técnico indicando contraindicação para tomar a vacina?', choices=[('', 'Selecione uma opção'), ('sim', 'Sim'), ('não', 'Não'), ])
    texto_termo_ciencia = forms.CharFieldPlus(label='Termo de ciência com a indicação voluntária de não ser vacinado', max_length=10000, required=False, widget=forms.Textarea())
    aceite_termo = forms.BooleanField(label='Aceite do Termo de Ciência', required=False)
    senha = forms.CharField(label='Senha para confirmar', widget=forms.PasswordInput)

    class Meta:
        model = PassaporteVacinalCovid
        fields = ('tem_atestado_medico', 'atestado_medico', 'texto_termo_ciencia', 'aceite_termo', 'senha')

    class Media:
        js = ('/static/saude/js/passaportevacinal_covid.js',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['texto_termo_ciencia'].widget.attrs['readonly'] = True
        if self.request.user.eh_aluno:
            self.fields['texto_termo_ciencia'].initial = '''
                TERMO DE CIÊNCIA
                - Declaro que estou ciente das medidas gerais de prevenção contra a Covid-19 adotadas pelo Instituto Federal do Rio Grande do Norte,
                incluindo a solicitação obrigatória de comprovação da realização de esquema vacinal contra a Covid-19, como medida essencial para a segurança individual e coletiva.
                - Declaro, ainda, que me responsabilizo pelos possíveis riscos em relação à Covid-19 e afirmo estar ciente dos termos do Plano de
                Contingência contra o Coronavírus do Instituto Federal do Rio Grande do Norte. Dessa forma, isento o IFRN de quaisquer
                problemas que a falta de imunização possa vir a trazer para a saúde e da coletividade.
                - Registro, ainda, que as implicações acadêmicas e disciplinares referentes a minha decisão voluntária estarão submetidas às normas
                estabelecidas pela Organização Didática do IFRN.
                - São medidas de prevenção da Covid-19: uso obrigatório de máscara; distanciamento físico mínimo de 1,5 metro; higienização
                frequente das mãos; não compartilhamento de objetos de uso pessoal; não promover aglomerações.
                '''
        else:
            self.fields['texto_termo_ciencia'].initial = '''
                TERMO DE CIÊNCIA
                - Declaro que optei por NÃO receber a vacina contra o vírus Sars-Cov-2 (Coronavírus) recomendada pelo Ministério da Saúde.
                - Declaro ainda que me responsabilizo pelos possíveis riscos em relação à Covid-19 e afirmo estar ciente dos termos do Plano de
                Contingência contra o Coronavírus do Instituto Federal do Rio Grande do Norte. Dessa forma, isento o IFRN de quaisquer
                problemas que a falta de imunização possa vir a trazer para minha saúde e da coletividade.
                - Registro, ainda, que as implicações legais referentes a minha decisão voluntária de não assumir a vacinação estarão submetidas ao
                que determina a Lei 8.112/1990.
                - São medidas de prevenção da Covid-19: uso obrigatório de máscara; distanciamento físico mínimo de 1 metro; higienização
                frequente das mãos; não compartilhamento de objetos de uso pessoal; não promover aglomerações.
            '''

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.cleaned_data.get('tem_atestado_medico') is None:
            self.add_error('tem_atestado_medico', 'Informe se você possui atestado/laudo médico ou técnico indicando contraindicação para tomar a vacina.')

        if self.cleaned_data.get('tem_atestado_medico') == 'não' and not self.cleaned_data.get('aceite_termo'):
            self.add_error('aceite_termo', 'Você precisa aceitar o termo de ciência com a indicação voluntária de não ser vacinado.')

        if self.cleaned_data.get('tem_atestado_medico') == 'sim' and self.cleaned_data.get('atestado_medico') is None:
            self.add_error('atestado_medico', 'Você precisa anexar o atestado/laudo médico ou técnico.')

        if self.cleaned_data.get('senha') and not auth.authenticate(username=self.request.user.username, password=cleaned_data['senha']):
            raise forms.ValidationError('A senha não confere com a do usuário logado.')
        return cleaned_data


class RelatorioPassaporteCovidForm(forms.FormPlus):
    METHOD = 'GET'
    nome = forms.CharField(label='Nome ou Matrícula', required=False)
    situacao = forms.ChoiceField(label='Situação do Passaporte Vacinal', choices=(('', 'Todas'),) + PassaporteVacinalCovid.SITUACAO_PASSAPORTE_CHOICES, required=False)
    situacao_declaracao = forms.ChoiceField(label='Situação da Declaração', choices=(('', 'Todas'),) + PassaporteVacinalCovid.SITUACAO_CHOICES, required=False)
    categoria = forms.ChoiceField(label='Categoria', required=False, choices=(('', 'Todos'), ('1', 'Aluno'), ('2', 'Servidor'), ('3', 'Prestador de Serviço'), ('4', 'Docente'), ('5', 'Técnico-Administrativo')))
    uo = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False,
                                empty_label="Todos")
    curso = forms.ChainedModelChoiceField(
        CursoCampus.objects.order_by('descricao'),
        label='Curso:',
        empty_label='Selecione o Campus',
        required=False,
        obj_label='descricao',
        form_filters=[('uo', 'diretoria__setor__uo_id')]
    )

    turma = forms.ChainedModelChoiceField(
        Turma.objects.order_by('descricao'),
        label='Turma:',
        empty_label='Selecione o Curso',
        required=False,
        obj_label='descricao',
        form_filters=[('curso', 'curso_campus_id')]
    )
    faixa_etaria = forms.ChoiceField(label='Faixa Etária', required=False, choices=(
        ('', 'Todas'), ('1', 'Menores de 18 anos'), ('2', 'Entre 18 e 60 anos'), ('3', 'Maiores de 60 anos')))

    def __init__(self, *args, **kwargs):
        self.todos_campi = kwargs.pop('todos_campi', None)
        self.request = kwargs.pop('request', None)
        self.busca_nome = kwargs.pop('busca_nome')
        self.campi_consulta = kwargs.pop('campi_consulta')
        super().__init__(*args, **kwargs)
        if not self.busca_nome:
            del self.fields['nome']
        if not self.todos_campi:
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.filter(id__in=self.campi_consulta)
            self.fields['uo'].initial = get_uo(self.request.user).id
            self.fields['uo'].empty_label = None
            self.fields['curso'].queryset = CursoCampus.locals


class RelatorioPassaporteCovidChefiaForm(forms.FormPlus):
    METHOD = 'GET'
    nome = forms.CharField(label='Nome ou Matrícula', required=False)
    situacao = forms.ChoiceField(label='Situação do Passaporte Vacinal', choices=(('', 'Todas'),) + PassaporteVacinalCovid.SITUACAO_PASSAPORTE_CHOICES, required=False)
    situacao_declaracao = forms.ChoiceField(label='Situação da Declaração', choices=(('', 'Todas'),) + PassaporteVacinalCovid.SITUACAO_CHOICES, required=False)
    categoria = forms.ChoiceField(label='Categoria', required=False, choices=(('', 'Todos'), ('2', 'Servidor'), ('3', 'Prestador de Serviço'), ('4', 'Docente'), ('5', 'Técnico-Administrativo')))
    faixa_etaria = forms.ChoiceField(label='Faixa Etária', required=False, choices=(
        ('', 'Todas'), ('1', 'Menores de 18 anos'), ('2', 'Entre 18 e 60 anos'), ('3', 'Maiores de 60 anos')))
    registrou_frequencia = forms.BooleanField(label='Registraram frequência com passaporte inválido', required=False)


class JustificativaIndeferirPassaporteForm(forms.FormPlus):
    justificativa = forms.CharFieldPlus(label='Justificativa para o Indeferimento', widget=forms.Textarea())
    url_origem = forms.CharFieldPlus(label='URL de origem', widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        self.url_origem = kwargs.pop('url_origem', None)
        super().__init__(*args, **kwargs)
        self.fields['url_origem'].initial = self.url_origem


class CadastroResultadoTesteCovidForm(forms.ModelFormPlus):
    senha = forms.CharField(label='Senha para confirmar', widget=forms.PasswordInput)

    class Meta:
        model = ResultadoTesteCovid
        fields = ('realizado_em', 'arquivo', 'senha')

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.cleaned_data.get('senha') and not auth.authenticate(username=self.request.user.username, password=cleaned_data['senha']):
            raise forms.ValidationError('A senha não confere com a do usuário logado.')
        return cleaned_data


class CadastroCartaoVacinalCovidForm(forms.ModelFormPlus):
    senha = forms.CharField(label='Senha para confirmar', widget=forms.PasswordInput)

    class Meta:
        model = PassaporteVacinalCovid
        fields = ('cartao_vacinal', 'senha')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cartao_vacinal'].required = True

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.cleaned_data.get('senha') and not auth.authenticate(username=self.request.user.username, password=cleaned_data['senha']):
            raise forms.ValidationError('A senha não confere com a do usuário logado.')
        return cleaned_data


class NotificarCovidForm(forms.ModelFormPlus):
    DECLARACAO_CHOICES = (
        ('', 'Selecione uma opção'),
        ('Suspeito sintomático', 'Suspeito sintomático'),
        ('Suspeito contactante', 'Suspeito contactante'),
        ('Confirmado', 'Confirmado'),
    )
    declaracao = forms.ChoiceField(label='Informe sua situação', choices=DECLARACAO_CHOICES)
    usuario = forms.ModelChoiceField(queryset=VinculoPessoa.objects, label='Paciente', widget=AutocompleteWidget(search_fields=VinculoPessoa.SEARCH_FIELDS))

    class Meta:
        model = NotificacaoCovid
        fields = ('usuario', 'declaracao', 'data_inicio_sintomas', 'sintomas', 'data_ultimo_teste', 'resultado_ultimo_teste', 'arquivo_ultimo_teste', 'data_contato_suspeito', 'mora_com_suspeito', 'esteve_sem_mascara', 'tempo_exposicao', 'suspeito_fez_teste', 'arquivo_teste')

    class Media:
        js = ('/static/saude/js/notificacao_covid.js',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.pode_indicar_usuario = kwargs.pop('pode_indicar_usuario')
        super().__init__(*args, **kwargs)
        self.fields['sintomas'].queryset = Sintoma.objects.filter(ativo=True)
        if self.pode_indicar_usuario:
            self.fields['usuario'].queryset = VinculoPessoa.objects.filter(setor__uo=get_uo(self.user))
        else:
            del self.fields['usuario']

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.cleaned_data.get('declaracao'):
            if self.cleaned_data.get('declaracao') in ('Suspeito sintomático', 'Confirmado'):
                if not self.cleaned_data.get('data_inicio_sintomas'):
                    self.add_error('data_inicio_sintomas', 'Este campo é obrigatório.')
                if not self.cleaned_data.get('sintomas'):
                    self.add_error('sintomas', 'Este campo é obrigatório.')
            elif self.cleaned_data.get('declaracao') == 'Suspeito contactante':

                if not self.cleaned_data.get('data_contato_suspeito'):
                    self.add_error('data_contato_suspeito', 'Este campo é obrigatório.')
                if not self.cleaned_data.get('mora_com_suspeito'):
                    self.add_error('mora_com_suspeito', 'Este campo é obrigatório.')
                if not self.cleaned_data.get('esteve_sem_mascara'):
                    self.add_error('esteve_sem_mascara', 'Este campo é obrigatório.')
                if not self.cleaned_data.get('tempo_exposicao'):
                    self.add_error('tempo_exposicao', 'Este campo é obrigatório.')
                if not self.cleaned_data.get('suspeito_fez_teste'):
                    self.add_error('suspeito_fez_teste', 'Este campo é obrigatório.')
        return cleaned_data


class MonitorarNotificacaoForm(forms.ModelFormPlus):
    SITUACAO_MONITORAMENTO_CHOICES = (
        ('Suspeito em monitoramento', 'Suspeito em monitoramento'),
        ('Confirmado em monitoramento', 'Confirmado em monitoramento'),
        ('Descartado', 'Descartado'),
        ('Recuperado', 'Recuperado'),
        ('Óbito', 'Óbito'),
    )
    url_origem = forms.CharFieldPlus(label='URL de origem', widget=forms.HiddenInput(), required=False)

    class Meta:
        model = MonitoramentoCovid
        fields = ('situacao', 'monitoramento')

    def __init__(self, *args, **kwargs):
        self.url_origem = kwargs.pop('url', None)
        super().__init__(*args, **kwargs)
        self.fields['url_origem'].initial = self.url_origem
        self.fields['situacao'].choices = MonitorarNotificacaoForm.SITUACAO_MONITORAMENTO_CHOICES


class RelatorioNotificacaoCovidForm(forms.FormPlus):
    METHOD = 'GET'

    categoria = forms.ChoiceField(label='Categoria', required=False, choices=(
        ('', 'Todos'), ('1', 'Aluno'), ('2', 'Servidor'), ('3', 'Prestador de Serviço'),))
    uo = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False,
                                empty_label="Todos")
    setor = forms.ModelChoiceField(label='Setor', queryset=Setor.objects.all(), required=False)
    curso = forms.ChainedModelChoiceField(
        CursoCampus.objects.order_by('descricao'),
        label='Curso:',
        empty_label='Selecione o Campus',
        required=False,
        obj_label='descricao',
        form_filters=[('uo', 'diretoria__setor__uo_id')]
    )

    turma = forms.ChainedModelChoiceField(
        Turma.objects.order_by('descricao'),
        label='Turma:',
        empty_label='Selecione o Curso',
        required=False,
        obj_label='descricao',
        form_filters=[('curso', 'curso_campus_id')]
    )

    def __init__(self, *args, **kwargs):
        self.todos_campi = kwargs.pop('todos_campi', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if not self.todos_campi:
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.filter(id=get_uo(self.request.user).id)
            self.fields['uo'].initial = get_uo(self.request.user).id
            self.fields['uo'].empty_label = None
            self.fields['curso'].queryset = CursoCampus.locals
            self.fields['setor'].queryset = Setor.objects.filter(uo=get_uo(self.request.user))
            if not self.request.user.groups.filter(name__in=['Chefe de Setor', 'Diretor Geral', 'Médico', 'Enfermeiro', 'Técnico em Enfermagem', 'Auxiliar em Enfermagem']):
                del self.fields['setor']
            if not self.request.user.groups.filter(name='Coordenador de Curso'):
                del self.fields['curso']
                del self.fields['turma']


class VerificaPassaporteForm(forms.FormPlus):
    nome = forms.CharField(label='Nome ou Matrícula', required=True)
