import math
import datetime
from decimal import Decimal

from ckeditor.fields import RichTextField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.utils.safestring import mark_safe

from comum.models import PrestadorServico, User
from comum.utils import get_uo, get_cargo_emprego
from djtools.db import models
from djtools.db.models import ForeignKeyPlus
from djtools.db.models import ModelPlus
from djtools.templatetags.filters import format_money
from edu.models import Aluno
from rh.models import Servidor, UnidadeOrganizacional, PessoaExterna
from dateutil.relativedelta import relativedelta


class TipoAtendimento:
    AVALIACAO_BIOMEDICA = 1
    ENFERMAGEM_MEDICO = 2
    ODONTOLOGICO = 3
    PSICOLOGICO = 4
    NUTRICIONAL = 5
    MULTIDISCIPLINAR = 6
    FISIOTERAPIA = 7

    TIPO_ATENDIMENTO_CHOICES = (
        (AVALIACAO_BIOMEDICA, 'Avaliação Biomédica'),
        (ENFERMAGEM_MEDICO, 'Atendimento Médico/Enfermagem'),
        (ODONTOLOGICO, 'Odontológico'),
        (PSICOLOGICO, 'Atendimento Psicológico'),
        (NUTRICIONAL, 'Atendimento Nutricional'),
        (FISIOTERAPIA, 'Atendimento de Fisioterapia'),
        (MULTIDISCIPLINAR, 'Atendimento Multidisciplinar'),
    )

    TIPO_ATENDIMENTO = {AVALIACAO_BIOMEDICA: 1, ENFERMAGEM_MEDICO: 2, ODONTOLOGICO: 3, PSICOLOGICO: 4, NUTRICIONAL: 5, MULTIDISCIPLINAR: 6, FISIOTERAPIA: 7}


class SituacaoAtendimento:
    ABERTO = 1
    FECHADO = 2
    CANCELADO = 3
    REABERTO = 4

    SITUACAO_ATENDIMENTO_CHOICES = ((ABERTO, 'Aberto'), (FECHADO, 'Fechado'), (CANCELADO, 'Cancelado'), (REABERTO, 'Reaberto'))

    SITUACAO_ATENDIMENTO = {ABERTO: 'Aberto', FECHADO: 'Fechado', CANCELADO: 'Cancelado', REABERTO: 'Reaberto'}


class UsoInternet:
    MENOS_DUAS_HORAS = 1
    DUAS_E_TRES_HORAS = 2
    TRES_E_QUATRO_HORAS = 3
    MAIS_QUATRO_HORAS = 4

    USOINTERNET_CHOICES = (
        (MENOS_DUAS_HORAS, 'Menos de 2 horas/dia'),
        (DUAS_E_TRES_HORAS, '2 a 3 horas/dia'),
        (TRES_E_QUATRO_HORAS, '3 a 4 horas/dia'),
        (MAIS_QUATRO_HORAS, '4 ou mais horas/dia'),
    )


class ObjetivoUsoInternet:
    PESQUISA = 'Pesquisa relacionada a estudo'
    JOGOS = 'Jogos'
    REDES_SOCIAIS = 'Redes Sociais'
    TRABALHO = 'Trabalho'
    OUTROS = 'Outros'

    OBJETIVOUSOINTERNET_CHOICES = ((PESQUISA, 'Pesquisa relacionada a estudo'), (JOGOS, 'Jogos'), (REDES_SOCIAIS, 'Redes Sociais'), (TRABALHO, 'Trabalho'), (OUTROS, 'Outros'))


class GrauDificuldade:
    ALTO = 1
    MEDIO = 2
    BAIXO = 3

    GRAU_CHOICES = ((ALTO, 'Alto'), (MEDIO, 'Médio'), (BAIXO, 'Baixo'))


class DuracaoPsiquiatria:
    MENOS_1_ANO = 1
    ENTRE_1_2_ANOS = 2
    ENTRE_2_3_ANOS = 3
    ENTRE_3_4_ANOS = 4
    ENTRE_4_5_ANOS = 5
    MAIS_5_ANOS = 6

    DURACAOPSIQUIATRIA_CHOICES = (
        (MENOS_1_ANO, 'Menos de 1 ano'),
        (ENTRE_1_2_ANOS, 'Entre 1 e 2 anos'),
        (ENTRE_1_2_ANOS, 'Entre 2 e 3 anos'),
        (ENTRE_3_4_ANOS, 'Entre 3 e 4 anos'),
        (ENTRE_4_5_ANOS, 'Entre 4 e 5 anos'),
        (MAIS_5_ANOS, 'Mais de 5 anos'),
    )


class TempoPsiquiatria:
    SEMANAS = 1
    MESES = 2
    UM_ANO = 3
    DE_2_A_5_ANOS = 4
    MAIS_5_ANOS = 5

    TEMPOPSIQUIATRIA_CHOICES = ((SEMANAS, 'Semanas'), (MESES, 'Meses'), (UM_ANO, '1 ano'), (DE_2_A_5_ANOS, 'De 2 a 5 anos'), (MAIS_5_ANOS, 'Mais de 5 anos'))


class TempoSemDentista:
    MENOS_1_MES = 1
    ENTRE_1_6_MESES = 2
    ENTRE_6_12_MESES = 3
    ENTRE_1_2_ANOS = 4
    MAIS_2_ANOS = 5

    TEMPO_CHOICES = (
        (MENOS_1_MES, 'Menos de 1 mês'),
        (ENTRE_1_6_MESES, 'Entre 1 e 6 meses'),
        (ENTRE_6_12_MESES, 'Entre 6 e 12 meses'),
        (ENTRE_1_2_ANOS, 'Entre 1 a 2 anos'),
        (MAIS_2_ANOS, 'Mais de 2 anos'),
    )


class Vinculo:
    ALUNO = 0
    SERVIDOR = 1
    PRESTADOR_SERVICO = 2
    COMUNIDADE_EXTERNA = 3

    VINCULO_CHOICES = ((0, 'Aluno'), (1, 'Servidor'), (2, 'Prestador de Serviço'), (3, 'Comunidade Externa'))

    VINCULO_OBJ = {ALUNO: Aluno, SERVIDOR: Servidor, PRESTADOR_SERVICO: PrestadorServico, COMUNIDADE_EXTERNA: PessoaExterna}

    @staticmethod
    def get_vinculo(vinculo, vinculo_id):
        if int(vinculo) in (Vinculo.ALUNO, Vinculo.SERVIDOR, Vinculo.PRESTADOR_SERVICO, Vinculo.COMUNIDADE_EXTERNA):
            return Vinculo.VINCULO_OBJ.get(int(vinculo)).objects.get(pk=vinculo_id)
        else:
            raise Exception()

    @staticmethod
    def get_vinculos(pessoa_fisica):
        # Busca vinculos ATIVOS de um CPF
        alunos = Aluno.objects.filter(Q(situacao__ativo=True), Q(pessoa_fisica__cpf=pessoa_fisica.cpf)).extra(select={'vinculo': 0}).all().order_by('id')
        servidor = Servidor.objects.ativos().filter(pessoa_fisica__cpf=pessoa_fisica.cpf).extra(select={'vinculo': 1}).all()
        prestadores = PrestadorServico.objects.filter(ativo=True, pessoa_fisica__cpf=pessoa_fisica.cpf).extra(select={'vinculo': 2}).all()
        externos = PessoaExterna.objects.filter(cpf=pessoa_fisica.cpf).extra(select={'vinculo': 3}).all()
        return list(alunos) + list(servidor) + list(prestadores) + list(externos)


class Especialidades:
    cargo_emprego = None

    MEDICO = 'Médico'
    ODONTOLOGO = 'Odontólogo'
    ENFERMEIRO = 'Enfermeiro'
    TECNICO_ENFERMAGEM = 'Técnico em Enfermagem'
    FISIOTERAPEUTA = 'Fisioterapeuta'
    PSICOLOGO = 'Psicólogo'
    NUTRICIONISTA = 'Nutricionista'
    AUXILIAR_DE_ENFERMAGEM = 'Auxiliar de Enfermagem'
    TODOS = 'Todos'
    AVALIACAO_BIOMEDICA = 'Avaliação Biomédica'
    TECNICO_SAUDE_BUCAL = 'Técnico em Saúde Bucal'
    ASSISTENTE_SOCIAL = 'Assistente Social'

    ESPECIALIDADES_CHOICES = (
        (TODOS, '----------------'),
        (AVALIACAO_BIOMEDICA, AVALIACAO_BIOMEDICA),
        (ASSISTENTE_SOCIAL, ASSISTENTE_SOCIAL),
        (ENFERMEIRO, ENFERMEIRO),
        (FISIOTERAPEUTA, FISIOTERAPEUTA),
        (MEDICO, MEDICO),
        (NUTRICIONISTA, NUTRICIONISTA),
        (ODONTOLOGO, ODONTOLOGO),
        (PSICOLOGO, PSICOLOGO),
        (TECNICO_SAUDE_BUCAL, TECNICO_SAUDE_BUCAL),
    )

    ENFERMAGEM = [ENFERMEIRO, TECNICO_ENFERMAGEM, AUXILIAR_DE_ENFERMAGEM]

    # Codigos: MEDICO-AREA, ODONTOLOGO - 40 HORAS, ODONTOLOGO - 30H - DEC JUD (PCIFE) - 701093, TECNICO EM HIGIENE DENTAL, ENFERMEIRO-AREA, TECNICO EM ENFERMAGEM, FISIOTERAPEUTA,
    # PSICOLOGO-AREA, NUTRICIONISTA-HABILITACAO, AUXILIAR DE ENFERMAGEM
    CARGO_ESPECIALIDADE_GRUPO_ID = {'701047': 1, '701064': 2, '701093': 2, '701241': 2, '701029': 3, '701030': 3, '701233': 3, '701038': 4, '701060': 5, '701055': 6, '701411': 7}

    GRUPOS = [
        'Coordenador de Saúde Sistêmico',
        MEDICO,
        ODONTOLOGO,
        ENFERMEIRO,
        TECNICO_ENFERMAGEM,
        FISIOTERAPEUTA,
        PSICOLOGO,
        NUTRICIONISTA,
        AUXILIAR_DE_ENFERMAGEM,
        TECNICO_SAUDE_BUCAL,
    ]

    GRUPOS_PRONTUARIO = [
        'Coordenador de Saúde Sistêmico',
        'Atendente',
        MEDICO,
        ODONTOLOGO,
        ENFERMEIRO,
        TECNICO_ENFERMAGEM,
        FISIOTERAPEUTA,
        PSICOLOGO,
        NUTRICIONISTA,
        AUXILIAR_DE_ENFERMAGEM,
        TECNICO_SAUDE_BUCAL,
    ]

    GRUPOS_RELATORIOS = [
        'Coordenador de Saúde Sistêmico',
        'Coordenador de Atividades Estudantis Sistêmico',
        'Coordenador de Atividades Estudantis',
        MEDICO,
        ODONTOLOGO,
        ENFERMEIRO,
        TECNICO_ENFERMAGEM,
        FISIOTERAPEUTA,
        PSICOLOGO,
        NUTRICIONISTA,
        AUXILIAR_DE_ENFERMAGEM,
        TECNICO_SAUDE_BUCAL,
    ]

    GRUPOS_RELATORIOS_SISTEMICO = ['Coordenador de Saúde Sistêmico', 'Coordenador de Atividades Estudantis Sistêmico', 'Auditor']

    GRUPOS_ATENDIMENTO_MEDICO_ENF = [MEDICO, ENFERMEIRO, TECNICO_ENFERMAGEM, AUXILIAR_DE_ENFERMAGEM]

    GRUPOS_ATENDIMENTO_ENF = [ENFERMEIRO, TECNICO_ENFERMAGEM, AUXILIAR_DE_ENFERMAGEM]

    GRUPOS_VE_GRAFICOS_TODOS = ['Coordenador de Saúde Sistêmico', 'Coordenador de Atividades Estudantis', 'Auditor', 'Coordenador de Atividades Estudantis Sistêmico']

    def __init__(self, user):
        self.user = user

    def is_medico(self):
        return self.user.groups.filter(name=self.MEDICO).exists()

    def is_odontologo(self):
        return self.user.groups.filter(name=self.ODONTOLOGO).exists()

    def is_enfermeiro(self):
        return self.user.groups.filter(name=self.ENFERMEIRO).exists()

    def is_tecnico_enfermagem(self):
        return self.user.groups.filter(name=self.TECNICO_ENFERMAGEM).exists()

    def is_auxiliar_enfermagem(self):
        return self.user.groups.filter(name=self.AUXILIAR_DE_ENFERMAGEM).exists()

    def is_fisioterapeuta(self):
        return self.user.groups.filter(name=self.FISIOTERAPEUTA).exists()

    def is_psicologo(self):
        return self.user.groups.filter(name=self.PSICOLOGO).exists()

    def is_nutricionista(self):
        return self.user.groups.filter(name=self.NUTRICIONISTA).exists()

    def is_tecnico_saude_bucal(self):
        return self.user.groups.filter(name=self.TECNICO_SAUDE_BUCAL).exists()

    def is_assistente_social(self):
        return self.user.groups.filter(name=self.ASSISTENTE_SOCIAL).exists()

    def eh_profissional_saude(self):
        return (
            self.is_medico()
            or self.is_odontologo()
            or self.is_enfermeiro()
            or self.is_fisioterapeuta()
            or self.is_psicologo()
            or self.is_nutricionista()
            or self.is_tecnico_enfermagem()
            or self.is_auxiliar_enfermagem()
            or self.is_tecnico_saude_bucal()
        )


class MetodoContraceptivo(models.ModelPlus):
    nome = models.CharField('Nome', max_length=250, null=False, unique=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Método Contraceptivo'
        verbose_name_plural = 'Métodos Contraceptivos'

    def __str__(self):
        return self.nome


class Doenca(models.ModelPlus):
    nome = models.CharField('Nome', max_length=100, null=False, unique=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Doença'
        verbose_name_plural = 'Doenças'

    def __str__(self):
        return self.nome


class DificuldadeOral(models.ModelPlus):
    dificuldade = models.CharField('Dificuldade Oral', max_length=200, null=False, unique=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Dificuldade Oral'
        verbose_name_plural = 'Dificuldades Orais'

    def __str__(self):
        return self.dificuldade


class Droga(models.ModelPlus):
    nome = models.CharField('Nome', max_length=200, null=False, unique=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Droga'
        verbose_name_plural = 'Drogas'

    def __str__(self):
        return self.nome


class Prontuario(models.ModelPlus):
    vinculo = models.OneToOneFieldPlus('comum.Vinculo', verbose_name='Vínculo', null=True, related_name='vinculo_paciente_prontuario')
    vacinas = models.ManyToManyField('saude.Vacina', through='CartaoVacinal')
    cartao_vacinal = models.FileFieldPlus('Cartão Vacinal', null=True, upload_to='saude/prontuario', max_length=255)
    cadastrado_por_vinculo = models.ForeignKeyPlus('comum.Vinculo', null=True, on_delete=models.CASCADE)
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado Em', null=True)

    class Meta:
        verbose_name = 'Prontuário'
        verbose_name_plural = 'Prontuários'

    @staticmethod
    def get_prontuario(vinculo):
        if isinstance(vinculo.relacionamento, Aluno) and Atendimento.objects.filter(
                aluno=vinculo.relacionamento).exists():
            return Atendimento.objects.filter(aluno=vinculo.relacionamento)[0].prontuario
        elif isinstance(vinculo.relacionamento, Servidor) and Atendimento.objects.filter(
                servidor=vinculo.relacionamento).exists():
            return Atendimento.objects.filter(servidor=vinculo.relacionamento)[0].prontuario
        elif isinstance(vinculo.relacionamento, PrestadorServico) and Atendimento.objects.filter(
                prestador_servico=vinculo.relacionamento).exists():
            return Atendimento.objects.filter(prestador_servico=vinculo.relacionamento)[0].prontuario
        elif isinstance(vinculo.relacionamento, PessoaExterna) and Atendimento.objects.filter(
                pessoa_externa=vinculo.relacionamento).exists():
            return Atendimento.objects.filter(pessoa_externa=vinculo.relacionamento)[0].prontuario
        prontuarios = Prontuario.objects.filter(vinculo=vinculo)
        if not prontuarios.exists():
            try:
                prontuario = Prontuario()
                prontuario.vinculo = vinculo
                prontuario.cadastrado_em = datetime.datetime.now()
                prontuario.save()
                return prontuario
            except IntegrityError:
                return Prontuario.objects.filter(vinculo=vinculo).order_by('-id').first()
        else:
            return prontuarios[0]


class Atendimento(models.ModelPlus):
    CATEGORIA_ALUNO = '1'
    CATEGORIA_SERVIDOR = '2'
    CATEGORIA_PRESTADOR_SERVICO = '3'
    CATEGORIA_COMUNIDADE_EXTERNA = '4'

    CATEGORIAS_VINCULO = (
        (CATEGORIA_ALUNO, 'Aluno'),
        (CATEGORIA_SERVIDOR, 'Servidor'),
        (CATEGORIA_PRESTADOR_SERVICO, 'Prestador de Serviço'),
        (CATEGORIA_COMUNIDADE_EXTERNA, 'Comunidade Externa'),
    )

    prontuario = ForeignKeyPlus(Prontuario)
    tipo = models.IntegerField('Tipo', choices=TipoAtendimento.TIPO_ATENDIMENTO_CHOICES)
    situacao = models.IntegerField('Situação', choices=SituacaoAtendimento.SITUACAO_ATENDIMENTO_CHOICES)

    data_aberto = models.DateTimeField('Data de Abertura')
    data_fechado = models.DateTimeField('Data de Fechamento', null=True, blank=True)
    data_cancelado = models.DateTimeField('Data de Cancelamento', null=True, blank=True)
    data_reaberto = models.DateTimeField('Data de Reabertura', null=True, blank=True)

    obs_fechado = models.CharField('Observação de Fechamento', max_length=200, blank=True)
    obs_cancelado = models.CharField('Observação de Cancelamento', max_length=200, blank=True)

    usuario_aberto = models.ForeignKeyPlus(User, verbose_name='Aberto por', null=True, related_name='user_usuario_aberto', on_delete=models.CASCADE)
    usuario_fechado = models.ForeignKeyPlus(User, verbose_name='Fechado por', null=True, related_name='user_usuario_fechado', on_delete=models.CASCADE)
    usuario_cancelado = models.ForeignKeyPlus(User, verbose_name='Cancelado por', null=True, related_name='user_usuario_cancelado', on_delete=models.CASCADE)
    usuario_reaberto = models.ForeignKeyPlus(User, verbose_name='Reaberto por', null=True, related_name='user_usuario_reaberto', on_delete=models.CASCADE)
    aluno = models.ForeignKeyPlus(Aluno, null=True, blank=True)
    servidor = ForeignKeyPlus(Servidor, null=True, blank=True)
    prestador_servico = ForeignKeyPlus(PrestadorServico, null=True, blank=True)
    pessoa_externa = ForeignKeyPlus(PessoaExterna, null=True, blank=True)

    class Meta:
        verbose_name = 'Atendimento'
        verbose_name_plural = 'Atendimentos'
        permissions = (("pode_ver_relatorio_gestao", "Pode ver relatórios de gestão do AE"),)

    def is_atendimento_avaliacao_biomedica(self):
        return self.tipo == TipoAtendimento.AVALIACAO_BIOMEDICA

    def is_atendimento_enfermagem_medico(self):
        return self.tipo == TipoAtendimento.ENFERMAGEM_MEDICO

    def is_atendimento_odontologico(self):
        return self.tipo == TipoAtendimento.ODONTOLOGICO

    def is_atendimento_psicologico(self):
        return self.tipo == TipoAtendimento.PSICOLOGICO

    def is_atendimento_nutricional(self):
        return self.tipo == TipoAtendimento.NUTRICIONAL

    def is_atendimento_fisioterapia(self):
        return self.tipo == TipoAtendimento.FISIOTERAPIA

    def is_atendimento_multidisciplinar(self):
        return self.tipo == TipoAtendimento.MULTIDISCIPLINAR

    def get_situacao(self):
        return SituacaoAtendimento.SITUACAO_ATENDIMENTO.get(self.situacao)

    def is_aberto(self):
        return self.situacao in [SituacaoAtendimento.ABERTO, SituacaoAtendimento.REABERTO]

    def is_cancelado(self):
        return SituacaoAtendimento.CANCELADO == self.situacao

    def is_fechado(self):
        return SituacaoAtendimento.FECHADO == self.situacao

    def is_reaberto(self):
        return SituacaoAtendimento.REABERTO == self.situacao

    def get_vinculo_title(self):
        if self.aluno:
            return f'Aluno ({self.aluno.matricula})'
        elif self.servidor:
            return f'Servidor ({self.servidor.matricula})'
        elif self.prestador_servico:
            return f'Prestador de Serviço ({self.prestador_servico.cpf})'
        else:
            return 'Comunidade Externa'

    def get_pessoa_fisica_vinculo(self):
        if self.aluno:
            return self.aluno.pessoa_fisica
        elif self.servidor:
            return self.servidor
        elif self.prestador_servico:
            return self.prestador_servico
        elif self.pessoa_externa:
            return self.pessoa_externa
        else:
            return self.prontuario.vinculo.pessoa.pessoafisica

    def get_vinculo(self):
        if self.aluno:
            return self.aluno
        elif self.servidor:
            return self.servidor
        elif self.prestador_servico:
            return self.prestador_servico
        elif self.pessoa_externa:
            return self.pessoa_externa
        else:
            return self.prontuario.vinculo.pessoa.nome

    def get_id_vinculo(self):
        if self.aluno:
            return 0
        elif self.servidor:
            return 1
        elif self.prestador_servico:
            return 2
        else:
            return 3

    def set_vinculo(self, vinculo_obj):
        if type(vinculo_obj) == Aluno:
            self.aluno = vinculo_obj
        elif type(vinculo_obj) == Servidor:
            self.servidor = vinculo_obj
        elif type(vinculo_obj) == PrestadorServico:
            self.prestador_servico = vinculo_obj
        elif type(vinculo_obj) == PessoaExterna:
            self.pessoa_externa = vinculo_obj

    def get_tipo_consulta(self):
        if self.get_odontograma():
            return self.get_odontograma().tipo_consulta
        else:
            return 'Não Informado'

    def get_procedimentos_odontologicos(self):
        texto = ''
        if ProcedimentoOdontologico.objects.filter(atendimento=self).exists():
            for item in ProcedimentoOdontologico.objects.filter(atendimento=self).distinct('procedimento'):
                texto += item.procedimento.denominacao + ', '
            return texto[:-2]
        else:
            return '-'

    def get_queryset_procedimentos_odontologicoss(self):
        if ProcedimentoOdontologico.objects.filter(atendimento=self).exists():
            return ProcedimentoOdontologico.objects.filter(atendimento=self)
        return None

    def get_hda(self):
        if Anamnese.objects.filter(atendimento=self).exists():
            return Anamnese.objects.filter(atendimento=self).order_by('-id')[0].hda
        return None

    def get_processo_saude_doenca(self):
        if ProcessoSaudeDoenca.objects.filter(atendimento=self).exists():
            return ProcessoSaudeDoenca.objects.filter(atendimento=self).order_by('-id')[0]
        return None

    def get_hipoteses_diagnosticas(self):
        texto = list()
        if HipoteseDiagnostica.objects.filter(atendimento=self).exists():
            for item in HipoteseDiagnostica.objects.filter(atendimento=self):
                novo_item = item.cid.denominacao + f' (<b>{item.cid.codigo}</b>)'
                texto.append(novo_item)
            return ', '.join(texto)
        else:
            return '-'

    def get_condutas(self):
        texto = list()
        if CondutaMedica.objects.filter(atendimento=self).exists():
            for item in CondutaMedica.objects.filter(atendimento=self):
                novo_item = item.conduta + f' (<b>Responsável:</b> {item.profissional.get_vinculo().pessoa.nome})'
                texto.append(novo_item)
            return ', '.join(texto)
        else:
            return '-'

    def get_motivo_consulta(self):
        texto = list()
        if Motivo.objects.filter(atendimento=self).exists():
            for item in Motivo.objects.filter(atendimento=self):
                novo_item = item.motivo_atendimento
                texto.append(novo_item)
            return ', '.join(texto)
        else:
            return '-'

    def get_intervencoes_enfermagem(self):
        texto = list()
        if IntervencaoEnfermagem.objects.filter(atendimento=self).exists():
            for item in IntervencaoEnfermagem.objects.filter(atendimento=self):
                novo_item = item.procedimento_enfermagem.denominacao
                texto.append(novo_item)
            return ', '.join(texto)
        else:
            return '-'

    def get_tipo_atendimento(self):
        if self.is_atendimento_avaliacao_biomedica():
            return 'Avaliação Biomédica'
        elif self.is_atendimento_enfermagem_medico():
            return 'Atendimento Médico/Enfermagem'
        elif self.is_atendimento_odontologico():
            return 'Atendimento Odontológico'
        elif self.is_atendimento_psicologico():
            return 'Atendimento Psicológico'
        elif self.is_atendimento_nutricional():
            return 'Atendimento Nutricional'
        elif self.is_atendimento_fisioterapia():
            return 'Atendimento de Fisioterapia'
        elif self.is_atendimento_multidisciplinar():
            return 'Atendimento Multidisciplinar'
        else:
            return 'Especialidade Não Informada'

    def get_url_tipo_atendimento(self):
        if self.is_atendimento_avaliacao_biomedica():
            return '{}{}'.format(settings.SITE_URL, f'/saude/avaliacao_biomedica/{self.id}/')
        elif self.is_atendimento_enfermagem_medico():
            return '{}{}'.format(settings.SITE_URL, f'/saude/atendimento_medico_enfermagem/{self.id}/')
        elif self.is_atendimento_odontologico():
            return '{}{}'.format(settings.SITE_URL, f'/saude/atendimento_odontologico/{self.id}/')
        elif self.is_atendimento_psicologico():
            return '{}{}'.format(settings.SITE_URL, f'/saude/atendimento_psicologico/{self.id}/')
        elif self.is_atendimento_nutricional():
            return '{}{}'.format(settings.SITE_URL, f'/saude/atendimento_nutricional/{self.id}/')
        elif self.is_atendimento_multidisciplinar():
            return '{}{}'.format(settings.SITE_URL, f'/saude/atendimento_multidisciplinar/{self.id}/')
        else:
            return ''

    def get_odontograma(self):
        if Odontograma.objects.filter(atendimento=self).exists():
            return Odontograma.objects.filter(atendimento=self).order_by('-id')[0]
        return False

    def get_exames_periodontais(self, sextante=None):
        exames = list()
        if sextante:
            if ExamePeriodontal.objects.filter(atendimento=self, sextante=sextante).exists():
                for item in ExamePeriodontal.objects.filter(atendimento=self, sextante=sextante):
                    exames.append([item.get_ocorrencia_display()])
                return exames
        else:
            if ExamePeriodontal.objects.filter(atendimento=self).exists():
                for item in ExamePeriodontal.objects.filter(atendimento=self):
                    descricao = f'{item.get_ocorrencia_display()} ({item.sextante})'
                    exames.append([descricao])
                return exames

        return '-'

    def get_exames_periodontais_s1(self):
        return self.get_exames_periodontais(ExamePeriodontal.S1)

    def get_exames_periodontais_s2(self):
        return self.get_exames_periodontais(ExamePeriodontal.S2)

    def get_exames_periodontais_s3(self):
        return self.get_exames_periodontais(ExamePeriodontal.S3)

    def get_exames_periodontais_s4(self):
        return self.get_exames_periodontais(ExamePeriodontal.S4)

    def get_exames_periodontais_s5(self):
        return self.get_exames_periodontais(ExamePeriodontal.S5)

    def get_exames_periodontais_s6(self):
        return self.get_exames_periodontais(ExamePeriodontal.S6)

    def get_exames_periodontais_s1_s3(self):
        return self.get_exames_periodontais(ExamePeriodontal.S1_S3)

    def get_exames_periodontais_s4_s6(self):
        return self.get_exames_periodontais(ExamePeriodontal.S4_S6)

    def get_exames_periodontais_s1_s6(self):
        return self.get_exames_periodontais(ExamePeriodontal.S1_S6)

    def get_alteracoes_estomatologicas(self):
        if ExameEstomatologico.objects.filter(atendimento=self).exists():
            return ExameEstomatologico.objects.filter(atendimento=self).order_by('-id')[0]
        return False

    @staticmethod
    def abrir(tipo_atendimento, prontuario, vinculo, user):
        pode_criar_atendimento = user.groups.filter(name__in=Especialidades.GRUPOS_ATENDIMENTO_MEDICO_ENF)
        # Não pode abrir um atendimento do tipo AVALIACAO_BIOMEDICA se já tiver um aberto para o mesmo prontuario
        if tipo_atendimento == TipoAtendimento.AVALIACAO_BIOMEDICA:
            if Atendimento.objects.filter(prontuario__pk=prontuario.id, tipo=TipoAtendimento.AVALIACAO_BIOMEDICA, situacao=SituacaoAtendimento.ABERTO).exists():
                raise ValidationError('Já existe uma avaliação biomédica em aberto.')
            if not isinstance(vinculo, Aluno):
                raise ValidationError('A avaliação biomédica é realizada apenas para alunos.')

        if tipo_atendimento == TipoAtendimento.ENFERMAGEM_MEDICO:
            if not pode_criar_atendimento:
                raise ValidationError('Você não tem permissão para iniciar um atendimento.')

            if Atendimento.objects.filter(prontuario__pk=prontuario.id, tipo=TipoAtendimento.ENFERMAGEM_MEDICO, situacao=SituacaoAtendimento.ABERTO).exists():
                raise ValidationError('Já existe um atendimento médico/enfermagem em aberto.')

        if (
            tipo_atendimento == TipoAtendimento.ODONTOLOGICO
            and Atendimento.objects.filter(prontuario__pk=prontuario.id, tipo=TipoAtendimento.ODONTOLOGICO, situacao=SituacaoAtendimento.ABERTO).exists()
        ):
            raise ValidationError('Já existe um atendimento odontológico em aberto.')

        if tipo_atendimento == TipoAtendimento.PSICOLOGICO:
            if not user.groups.filter(name=Especialidades.PSICOLOGO).exists():
                raise ValidationError('Você não tem permissão para iniciar um atendimento.')

            if Atendimento.objects.filter(prontuario__pk=prontuario.id, tipo=TipoAtendimento.PSICOLOGICO, situacao=SituacaoAtendimento.ABERTO).exists():
                raise ValidationError('Já existe um atendimento em aberto.')

        if (
            tipo_atendimento == TipoAtendimento.NUTRICIONAL
            and Atendimento.objects.filter(prontuario__pk=prontuario.id, tipo=TipoAtendimento.NUTRICIONAL, situacao=SituacaoAtendimento.ABERTO).exists()
        ):
            raise ValidationError('Já existe um atendimento nutricional em aberto.')

        if (
            tipo_atendimento == TipoAtendimento.FISIOTERAPIA
            and Atendimento.objects.filter(prontuario__pk=prontuario.id, tipo=TipoAtendimento.FISIOTERAPIA, situacao=SituacaoAtendimento.ABERTO).exists()
        ):
            raise ValidationError('Já existe um atendimento de fisioterapia em aberto.')

        if tipo_atendimento == TipoAtendimento.MULTIDISCIPLINAR:
            if not user.groups.filter(name__in=[Especialidades.ODONTOLOGO, Especialidades.MEDICO, Especialidades.NUTRICIONISTA]).exists():
                raise ValidationError('Você não tem permissão para iniciar um atendimento.')

            if Atendimento.objects.filter(prontuario__pk=prontuario.id, tipo=TipoAtendimento.MULTIDISCIPLINAR, situacao=SituacaoAtendimento.ABERTO).exists():
                raise ValidationError('Já existe um atendimento em aberto.')

        atendimento = Atendimento()
        atendimento.tipo = tipo_atendimento
        atendimento.prontuario = prontuario
        atendimento.situacao = SituacaoAtendimento.ABERTO
        atendimento.set_vinculo(vinculo)
        atendimento.usuario_aberto = user
        atendimento.data_aberto = datetime.datetime.today()
        atendimento.save()

        if tipo_atendimento in [
            TipoAtendimento.ENFERMAGEM_MEDICO,
            TipoAtendimento.ODONTOLOGICO,
            TipoAtendimento.NUTRICIONAL,
            TipoAtendimento.FISIOTERAPIA,
            TipoAtendimento.MULTIDISCIPLINAR,
        ]:
            processosaude_recente = Atendimento.objects.filter(processosaudedoenca__isnull=False, prontuario__pk=prontuario.id, situacao=SituacaoAtendimento.FECHADO).order_by(
                '-data_fechado'
            ) | Atendimento.objects.filter(
                situacao=SituacaoAtendimento.ABERTO, tipo=TipoAtendimento.AVALIACAO_BIOMEDICA, processosaudedoenca__isnull=False, prontuario__pk=prontuario.id
            )

            if processosaude_recente.exists():
                processo_recente = processosaude_recente.order_by('-id')[0].processosaudedoenca_set.all()[0]
                processo_recente.profissional = user
                processo_recente.data_cadastro = datetime.datetime.now()
                processo_recente.pk = None
                processo_recente.atendimento = atendimento
                processo_recente.save()
                processo_recente.doencas_cronicas.set(processosaude_recente[0].processosaudedoenca_set.all()[0].doencas_cronicas.all())
                processo_recente.save()

            if tipo_atendimento in [TipoAtendimento.ENFERMAGEM_MEDICO, TipoAtendimento.FISIOTERAPIA]:
                antecedentes_recente = Atendimento.objects.filter(
                    antecedentesfamiliares__isnull=False, prontuario__pk=prontuario.id, situacao=SituacaoAtendimento.FECHADO
                ).order_by('-data_fechado') | Atendimento.objects.filter(
                    situacao=SituacaoAtendimento.ABERTO, tipo=TipoAtendimento.AVALIACAO_BIOMEDICA, antecedentesfamiliares__isnull=False, prontuario__pk=prontuario.id
                )
                if antecedentes_recente.exists():
                    registro = antecedentes_recente.order_by('-id')[0].antecedentesfamiliares_set.all()[0]
                    processo_recente = registro
                    processo_recente.profissional = user
                    processo_recente.data_cadastro = datetime.datetime.now()
                    processo_recente.pk = None
                    processo_recente.atendimento = atendimento
                    processo_recente.save()
                    processo_recente.agravos_primeiro_grau.set(antecedentes_recente.order_by('-id')[0].antecedentesfamiliares_set.all()[0].agravos_primeiro_grau.all())
                    processo_recente.agravos_segundo_grau.set(antecedentes_recente.order_by('-id')[0].antecedentesfamiliares_set.all()[0].agravos_segundo_grau.all())
                    processo_recente.save()

        if tipo_atendimento in [TipoAtendimento.AVALIACAO_BIOMEDICA, TipoAtendimento.ODONTOLOGICO]:
            if tipo_atendimento == TipoAtendimento.AVALIACAO_BIOMEDICA:
                odontograma_mais_recente = Atendimento.objects.filter(odontograma__isnull=False, prontuario__pk=prontuario.id, situacao=SituacaoAtendimento.FECHADO).order_by(
                    '-data_fechado'
                )
            else:
                odontograma_mais_recente = Atendimento.objects.filter(
                    odontograma__isnull=False, prontuario__pk=prontuario.id, situacao__in=[SituacaoAtendimento.ABERTO, SituacaoAtendimento.FECHADO]
                ).order_by('-id')
            if odontograma_mais_recente.exists():
                odontograma_recente = odontograma_mais_recente[0].odontograma_set.all()[0]
            else:
                odontograma_recente = Odontograma()
            odontograma_recente.profissional = user
            odontograma_recente.data_cadastro = datetime.datetime.now()
            odontograma_recente.pk = None
            odontograma_recente.queixa_principal = None
            odontograma_recente.atendimento = atendimento
            odontograma_recente.salvo = False
            odontograma_recente.save()

            if tipo_atendimento == TipoAtendimento.ODONTOLOGICO:
                atendimento_mais_recente = (
                    Atendimento.objects.filter(tipo__in=[TipoAtendimento.AVALIACAO_BIOMEDICA, TipoAtendimento.ODONTOLOGICO], prontuario__pk=prontuario.id)
                    .exclude(id=atendimento.id)
                    .order_by('-id')
                )
                if atendimento_mais_recente.exists():
                    exames_estomatologicos = ExameEstomatologico.objects.filter(atendimento=atendimento_mais_recente[0])
                    if exames_estomatologicos.exists():
                        for exame in exames_estomatologicos.order_by('id'):
                            novo_exame = exame
                            novo_exame.id = None
                            novo_exame.atendimento = atendimento
                            novo_exame.save()
                    exames_periodontal = ExamePeriodontal.objects.filter(atendimento=atendimento_mais_recente[0], resolvido=False).order_by('id')
                    if exames_periodontal.exists():
                        for exame in exames_periodontal:
                            novo_exame = exame
                            novo_exame.id = None
                            novo_exame.atendimento = atendimento
                            novo_exame.save()
                atendimento_mais_recente = Atendimento.objects.filter(
                    tipo=TipoAtendimento.ODONTOLOGICO, prontuario__pk=prontuario.id, situacao=SituacaoAtendimento.FECHADO
                ).order_by('-data_fechado')
                if atendimento_mais_recente.exists():
                    plano_tratamento = PlanoTratamento.objects.filter(atendimento=atendimento_mais_recente[0])
                    if plano_tratamento.exists():
                        if not Odontograma.objects.filter(atendimento=atendimento_mais_recente[0], tipo_consulta__descricao=ProcedimentoOdontologico.CONCLUSAO_TRATAMENTO).exists():
                            for plano in plano_tratamento:
                                novo_plano = plano
                                novo_plano.id = None
                                novo_plano.atendimento = atendimento
                                novo_plano.save()

        if tipo_atendimento == TipoAtendimento.NUTRICIONAL:
            novo_atendimento = AtendimentoNutricao()
            novo_atendimento.profissional = user
            novo_atendimento.data_cadastro = datetime.datetime.now()
            novo_atendimento.atendimento = atendimento
            novo_atendimento.save()
            atendimento_recente = AtendimentoNutricao.objects.filter(atendimento__prontuario__pk=prontuario.id, atendimento__situacao=SituacaoAtendimento.FECHADO).order_by(
                '-atendimento__data_fechado'
            )
            if atendimento_recente.exists():
                atendimento_recente = atendimento_recente[0]
                novo_atendimento.apetite = atendimento_recente.apetite
                novo_atendimento.aversoes = atendimento_recente.aversoes
                novo_atendimento.preferencias = atendimento_recente.preferencias
                novo_atendimento.consumo_liquidos = atendimento_recente.consumo_liquidos
                novo_atendimento.save()

                if PlanoAlimentar.objects.filter(atendimento=atendimento_recente.atendimento).exists():
                    for plano in PlanoAlimentar.objects.filter(atendimento=atendimento_recente.atendimento):
                        novo_plano = PlanoAlimentar()
                        novo_plano.cardapio = plano.cardapio
                        novo_plano.sugestoes_leitura = plano.sugestoes_leitura
                        novo_plano.plano_alimentar_liberado = plano.plano_alimentar_liberado
                        novo_plano.atendimento = novo_atendimento.atendimento
                        novo_plano.save()
                        novo_plano.orientacao_nutricional.set(plano.orientacao_nutricional.all())
                        novo_plano.receita_nutricional.set(plano.receita_nutricional.all())
                        novo_plano.save()

        if tipo_atendimento == TipoAtendimento.FISIOTERAPIA:
            novo_atendimento = AtendimentoFisioterapia()
            novo_atendimento.profissional = user
            novo_atendimento.data_cadastro = datetime.datetime.now()
            novo_atendimento.atendimento = atendimento
            novo_atendimento.save()

        return atendimento

    def tem_pendencia(self, request):
        erros = []
        # Para fechar um atendimento é preciso que tenha participado do atendimento
        if not self.usuario_aberto == request.user and not AtendimentoEspecialidade.objects.filter(atendimento_id=self.id, profissional=request.user).exists():
            erros.append('O atendimento só pode ser fechado por um dos profissionais vinculados a ele.')
            return erros

        if self.tipo == TipoAtendimento.AVALIACAO_BIOMEDICA:
            if not Antropometria.objects.filter(atendimento_id=self.id).exists():
                erros.append('Não é possível fechar a Avaliação Biomédica sem a ficha de Atropometria ter sido preenchida.')

            if not ProcessoSaudeDoenca.objects.filter(atendimento_id=self.id).exists():
                erros.append('Não é possível fechar a Avaliação Biomédica sem a ficha de Processo Saúde-Doença ter sido preenchida.')

            if not HabitosDeVida.objects.filter(atendimento_id=self.id).exists():
                erros.append('Não é possível fechar a Avaliação Biomédica sem a ficha de Hábitos de Vida ter sido preenchida.')

            if not DesenvolvimentoPessoal.objects.filter(atendimento_id=self.id).exists():
                erros.append('Não é possível fechar a Avaliação Biomédica sem a ficha de Desenvolvimento Pessoal ter sido preenchida.')

        if self.tipo == TipoAtendimento.ENFERMAGEM_MEDICO:

            if not (
                (Motivo.objects.filter(atendimento_id=self.id).exists() and IntervencaoEnfermagem.objects.filter(atendimento_id=self.id).exists())
                or (Anamnese.objects.filter(atendimento_id=self.id).exists() and CondutaMedica.objects.filter(atendimento_id=self.id).exists())
            ):
                erros.append(
                    'Não é possível fechar o Atendimento sem que (Motivo do Atendimento e a Intervenção de enfermagem) ou (Anamnese e a Conduta Médica) tenham sido cadastrados.'
                )

            if CondutaMedica.objects.filter(atendimento_id=self.id, encaminhado_enfermagem=True, atendido=False).exists():
                erros.append('Não é possível fechar Atendimento com conduta médica pendente de intervenção de enfermagem.')

        if self.tipo == TipoAtendimento.ODONTOLOGICO:
            if (
                not ExameEstomatologico.objects.filter(atendimento_id=self.id).exists()
                and not ExamePeriodontal.objects.filter(atendimento_id=self.id).exists()
                and not ProcedimentoOdontologico.objects.filter(atendimento_id=self.id).exists()
            ):
                erros.append('Não é possível fechar o Atendimento Odontológico sem informar a situação clínica ou o procedimento realizado.')

        if self.tipo == TipoAtendimento.PSICOLOGICO:
            if not AtendimentoPsicologia.objects.filter(atendimento_id=self.id).exists():
                erros.append('Não é possível fechar Atendimento sem preencher as informações do atendimento.')

        if self.tipo == TipoAtendimento.NUTRICIONAL:
            if not AtendimentoNutricao.objects.filter(atendimento_id=self.id, motivo__isnull=False, conduta__isnull=False).exists():
                erros.append('Não é possível fechar Atendimento sem preencher o Motivo e a Conduta.')

        if self.tipo == TipoAtendimento.FISIOTERAPIA:
            if AtendimentoFisioterapia.objects.filter(atendimento_id=self.id, anamnese__isnull=True).exists():
                erros.append('Não é possível fechar Atendimento sem preencher a anamnese.')

        if self.tipo == TipoAtendimento.MULTIDISCIPLINAR:
            if not AtendimentoMultidisciplinar.objects.filter(atendimento_id=self.id).exists():
                erros.append('Não é possível fechar Atendimento sem preencher os procedimentos do atendimento.')

        if erros:
            return erros

    @transaction.atomic
    def fechar(self, request):
        if not self.tem_pendencia(request):
            self.data_fechado = datetime.datetime.today()
            self.situacao = SituacaoAtendimento.FECHADO
            self.usuario_fechado = request.user
            self.save()

        return None

    @transaction.atomic
    def cancelar(self, request):
        self.data_cancelado = datetime.datetime.today()
        self.situacao = SituacaoAtendimento.CANCELADO
        self.usuario_cancelado = request.user
        self.save()


class ModelSaudeFicha(ModelPlus):
    atendimento = ForeignKeyPlus(Atendimento, verbose_name='Atendimento', null=True)
    profissional = models.CurrentUserField(verbose_name='Cadastrado por', null=False)
    data_cadastro = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def get_responsavel(self):
        return 'Última atualização por {} em {}'.format(self.profissional, self.data_cadastro.strftime('%d/%m/%Y %H:%M'))

    def get_cadastro_display(self):
        return '{} em {}'.format(self.profissional, self.data_cadastro.strftime('%d/%m/%Y %H:%M'))

    def get_atendimento_id_display(self):
        return str(self.atendimento.id)


class AtendimentoEspecialidade(models.ModelPlus):
    atendimento = ForeignKeyPlus(Atendimento, verbose_name='Atendimento', null=True)
    especialidade = models.IntegerField(verbose_name='Especialidade')
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', on_delete=models.CASCADE)
    profissional = models.CurrentUserField(verbose_name='Profissional')

    @staticmethod
    def cadastrar(atendimento, request):
        if not AtendimentoEspecialidade.objects.filter(
            atendimento_id=atendimento.id,
            campus__sigla=get_uo(request.user).sigla,
            profissional=request.user,
            especialidade=Especialidades.CARGO_ESPECIALIDADE_GRUPO_ID[get_cargo_emprego(request.user).codigo],
        ).exists():
            ae = AtendimentoEspecialidade()
            ae.atendimento = atendimento
            ae.campus = get_uo(request.user)
            ae.especialidade = Especialidades.CARGO_ESPECIALIDADE_GRUPO_ID[get_cargo_emprego(request.user).codigo]
            ae.save()


class SinaisVitais(ModelSaudeFicha):
    EUPNEICO = '1'
    DISPNEICO = '2'
    ORTOPNEICO = '3'
    TAQUIPNEICO = '4'
    BRADIPNEICO = '5'
    APNEIA = '6'

    RESPIRACAO_CHOICES = (
        (EUPNEICO, 'Eupnéica'),
        (DISPNEICO, 'Dispnéica'),
        (ORTOPNEICO, 'Ortopnéica'),
        (TAQUIPNEICO, 'Taquipnéica'),
        (BRADIPNEICO, 'Bradipnéica'),
        (APNEIA, 'Apnéia'),
    )

    HIPOTERMIA = '1'
    NORMAL_AFEBRIL = '2'
    HIPERTERMIA = '3'
    PIREXIA = '4'
    HIPERPIREXIA = '5'

    TEMPERATURA_CHOICES = ((HIPOTERMIA, 'Hipotermia'), (NORMAL_AFEBRIL, 'Normal/Afebril'), (HIPERTERMIA, 'Hipertemia'), (PIREXIA, 'Pirexia'), (HIPERPIREXIA, 'Hiperpirexia'))

    pressao_sistolica = models.PositiveIntegerField('Pressão Sistólica', null=True, blank=True)
    pressao_diastolica = models.PositiveIntegerField('Pressão Diastólica', null=True, blank=True, help_text='Em mmHg')
    pulsacao = models.PositiveIntegerField('Pulsação', null=True, blank=True, help_text='Em bpm')
    respiracao = models.PositiveIntegerField('Respiração', null=True, blank=True, help_text='Em rpm')
    temperatura = models.DecimalFieldPlus('Temperatura', decimal_places=1, null=True, blank=True, help_text='Em °C')
    temperatura_categoria = models.CharFieldPlus('Temperatura', choices=TEMPERATURA_CHOICES, max_length=2, null=True, blank=True)
    respiracao_categoria = models.CharFieldPlus('Respiração', choices=RESPIRACAO_CHOICES, max_length=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Sinais Vitais'

    def get_pressao_display(self):
        if self.pressao_sistolica and self.pressao_diastolica:
            return f'{self.pressao_sistolica}x{self.pressao_diastolica} mmHg'
        return None

    def get_pulsacao_display(self):
        if self.pulsacao:
            return f'{self.pulsacao} bpm'
        return None

    def get_respiracao_display(self):
        if self.respiracao:
            return f'{self.respiracao} rpm'
        return None

    def get_temperatura_display(self):
        if self.temperatura:
            return f'{format_money(self.temperatura)} °C'
        return None

    def get_respiracao_categoria_display(self):
        if self.respiracao_categoria == Motivo.EUPNEICO:
            return 'Eupnéica'
        elif self.respiracao_categoria == Motivo.DISPNEICO:
            return 'Dispnéica'
        elif self.respiracao_categoria == Motivo.ORTOPNEICO:
            return 'Ortopnéica'
        elif self.respiracao_categoria == Motivo.TAQUIPNEICO:
            return 'Taquipnéica'
        elif self.respiracao_categoria == Motivo.BRADIPNEICO:
            return 'Bradipnéica'
        elif self.respiracao_categoria == Motivo.APNEIA:
            return 'Apnéia'

    def get_temperatura_categoria_display(self):
        if self.temperatura_categoria == Motivo.HIPOTERMIA:
            return 'Hipotermia'
        elif self.temperatura_categoria == Motivo.NORMAL_AFEBRIL:
            return 'Normal/Afebril'
        elif self.temperatura_categoria == Motivo.HIPERTERMIA:
            return 'Hipertermia'
        elif self.temperatura_categoria == Motivo.PIREXIA:
            return 'Pirexia'
        elif self.temperatura_categoria == Motivo.HIPERPIREXIA:
            return 'Hiperpirexia'


class Antropometria(ModelSaudeFicha):
    z_index_homem = {}
    z_index_homem[10] = dict(l=-1.7407, m=16.4433, s=0.10566)  # noqa
    z_index_homem[11] = dict(l=-1.7862, m=16.9392, s=0.11070)  # noqa
    z_index_homem[12] = dict(l=-1.7751, m=17.5334, s=0.11522)  # noqa
    z_index_homem[13] = dict(l=-1.7168, m=18.2330, s=0.11898)  # noqa
    z_index_homem[14] = dict(l=-1.6211, m=19.0050, s=0.12191)  # noqa
    z_index_homem[15] = dict(l=-1.4961, m=19.7744, s=0.12412)  # noqa
    z_index_homem[16] = dict(l=-1.3529, m=20.4951, s=0.12579)  # noqa
    z_index_homem[17] = dict(l=-1.1962, m=21.1423, s=0.12715)  # noqa
    z_index_homem[18] = dict(l=-1.0260, m=21.7077, s=0.12836)  # noqa
    z_index_homem[19] = dict(l=-0.8419, m=22.1883, s=0.12948)  # noqa

    z_index_mulher = {}
    z_index_mulher[10] = dict(l=-1.4864, m=16.6133, s=0.12307)  # noqa
    z_index_mulher[11] = dict(l=-1.4606, m=17.2459, s=0.12748)  # noqa
    z_index_mulher[12] = dict(l=-1.4006, m=17.9966, s=0.13129)  # noqa
    z_index_mulher[13] = dict(l=-1.3195, m=18.8012, s=0.13445)  # noqa
    z_index_mulher[14] = dict(l=-1.2266, m=19.5647, s=0.13700)  # noqa
    z_index_mulher[15] = dict(l=-1.1311, m=20.2125, s=0.13904)  # noqa
    z_index_mulher[16] = dict(l=-1.0368, m=20.7008, s=0.14070)  # noqa
    z_index_mulher[17] = dict(l=-0.9423, m=21.0367, s=0.14208)  # noqa
    z_index_mulher[18] = dict(l=-0.8462, m=21.2603, s=0.14330)  # noqa
    z_index_mulher[19] = dict(l=-0.7496, m=21.4269, s=0.14441)  # noqa

    MAGREZA_ACENTUADA = 'Magreza acentuada'
    MAGREZA = 'Magreza'
    EUTROFIA = 'Eutrofia'
    SOBREPESO = 'Sobrepeso'
    OBESIDADE = 'Obesidade'
    OBESIDADE_GRAVE = 'Obesidade grave'

    CLASSIFICACAO_IMC_CHOICES = (
        (MAGREZA_ACENTUADA, MAGREZA_ACENTUADA),
        (MAGREZA, MAGREZA),
        (EUTROFIA, EUTROFIA),
        (SOBREPESO, SOBREPESO),
        (OBESIDADE, OBESIDADE),
        (OBESIDADE_GRAVE, OBESIDADE_GRAVE),
    )

    RELACAO_CORPO_CHOICES = (

        ('Muito satisfeito(a)', 'Muito satisfeito(a)'),
        ('Satisfeito(a)', 'Satisfeito(a)'),
        ('Indiferente', 'Indiferente'),
        ('Insatisfeito(a)', 'Insatisfeito(a)'),
        ('Muito insatisfeito(a)', 'Muito insatisfeito(a)'),
    )

    PERIODO_SEM_COMIDA_CHOICES = (
        ('Nunca', 'Nunca'),
        ('Raramente', 'Raramente'),
        ('Muitas vezes', 'Muitas vezes'),
        ('Sempre', 'Sempre'),
    )

    # Avaliação

    estatura = models.PositiveIntegerField('Estatura', null=True, blank=True, help_text='Em cm')
    peso = models.DecimalFieldPlus('Peso', null=True, blank=True, decimal_places=3, help_text='Em kg')
    cintura = models.DecimalFieldPlus('Circunferência da Cintura', decimal_places=1, null=True, blank=True, help_text='Em cm')
    quadril = models.DecimalFieldPlus('Circunferência do Quadril', decimal_places=1, null=True, blank=True, help_text='Em cm')
    circunferencia_braco = models.DecimalFieldPlus('Circunferência do Braço', decimal_places=1, null=True, blank=True, help_text='Em cm')
    pc_triciptal = models.DecimalFieldPlus('Dobra Cutânea Tricipital', null=True, blank=True, help_text='Em mm')
    pc_biciptal = models.DecimalFieldPlus('Dobra Cutânea Bicipital', null=True, blank=True, help_text='Em mm')
    pc_subescapular = models.DecimalFieldPlus('Dobra Cutânea Subescapular', null=True, blank=True, help_text='Em mm')
    pc_suprailiaca = models.DecimalFieldPlus('Dobra Cutânea Suprailíaca', null=True, blank=True, help_text='Em mm')
    percentual_gordura = models.DecimalFieldPlus('Percentual de Gordura', null=True, blank=True, help_text='Em %')
    perda_peso = models.BooleanField('Perda de peso', default=False)
    quanto_perdeu = models.DecimalFieldPlus('Quanto perdeu', null=True, blank=True, help_text='Em kg')
    tempo_perda = models.PositiveIntegerField('Há quanto tempo vem perdendo peso?', null=True, blank=True, help_text='Em dias')
    ganho_peso = models.BooleanField('Ganho de peso', default=False)
    quanto_ganhou = models.DecimalFieldPlus('Quanto ganhou', null=True, blank=True, decimal_places=1, help_text='Em kg')
    tempo_ganho = models.PositiveIntegerField('Há quanto tempo vem ganhando peso?', null=True, blank=True, help_text='Em dias')
    dobra_cutanea_abdominal = models.DecimalFieldPlus('Dobra Cutânea Abdominal', null=True, blank=True, help_text='Em mm')
    dobra_cutanea_supraespinhal = models.DecimalFieldPlus('Dobra Cutânea Supraespinhal', null=True, blank=True, help_text='Em mm')
    dobra_cutanea_coxa_media = models.DecimalFieldPlus('Dobra Cutânea Coxa Média', null=True, blank=True, help_text='Em mm')
    dobra_cutanea_panturrilha_medial = models.DecimalFieldPlus('Dobra Cutânea Panturrilha Medial', null=True, blank=True, help_text='Em mm')
    sentimento_relacao_corpo = models.CharFieldPlus('Como você se sente em relação ao seu corpo?', max_length=50, null=True, blank=True, choices=RELACAO_CORPO_CHOICES)
    periodo_sem_comida = models.CharFieldPlus('NOS ÚLTIMOS 30 DIAS, com que frequência você ficou com fome por não ter comida suficiente em sua casa?', max_length=50, null=True, blank=True, choices=PERIODO_SEM_COMIDA_CHOICES)

    class Meta:
        verbose_name = 'Antropometria'

    def get_estatura_display(self):
        if self.estatura:
            return f'{self.estatura} cm'
        return None

    def get_peso_display(self):
        if self.peso:
            return f'{Decimal(self.peso).quantize(Decimal(10) ** -2)} kg'
        return None

    def get_cintura_display(self):
        if self.cintura:
            return f'{self.cintura} cm'
        return None

    def get_complicacao_metabolica(self):
        if self.cintura:
            if self.atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo == 'M':
                if self.cintura >= 102:
                    return 'Risco de Complicação Metabólica Aumentado Substancialmente'
                if self.cintura >= 94:
                    return 'Risco de Complicação Metabólica Aumentado'

            elif self.atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo == 'F':
                if self.cintura >= 88:
                    return 'Risco de Complicação Metabólica Aumentado Substancialmente'
                if self.cintura >= 80:
                    return 'Risco de Complicação Metabólica Aumentado'
            return None
        return None

    def get_quadril_display(self):
        if self.quadril:
            return f'{self.quadril} cm'
        return None

    def get_circunferencia_braco_display(self):
        if self.circunferencia_braco:
            return f'{self.circunferencia_braco} cm'
        return None

    def get_pc_triciptal_display(self):
        if self.pc_triciptal:
            return f'{self.pc_triciptal} mm'
        return None

    def get_pc_biciptal_display(self):
        if self.pc_biciptal:
            return f'{self.pc_biciptal} mm'
        return None

    def get_pc_subescapular_display(self):
        if self.pc_subescapular:
            return f'{self.pc_subescapular} mm'
        return None

    def get_pc_suprailiaca_display(self):
        if self.pc_suprailiaca:
            return f'{self.pc_suprailiaca} mm'
        return None

    def get_percentual_gordura_display(self):
        if self.percentual_gordura:
            return f'{self.percentual_gordura} %'
        return None

    def get_quanto_perdeu_display(self):
        if self.quanto_perdeu:
            return f'{self.quanto_perdeu} kg'
        return None

    def get_tempo_perda_display(self):
        if self.tempo_perda:
            return f'{self.tempo_perda} dias'
        return None

    def get_quanto_ganhou_display(self):
        if self.quanto_ganhou:
            return f'{self.quanto_ganhou} kg'
        return None

    def get_tempo_ganho_display(self):
        if self.tempo_ganho:
            return f'{self.tempo_ganho} dias'
        return None

    def get_dobra_cutanea_abdominal_display(self):
        if self.dobra_cutanea_abdominal:
            return f'{self.dobra_cutanea_abdominal} mm'
        return None

    def get_dobra_cutanea_supraespinhal_display(self):
        if self.dobra_cutanea_supraespinhal:
            return f'{self.dobra_cutanea_supraespinhal} mm'
        return None

    def get_dobra_cutanea_coxa_media_display(self):
        if self.dobra_cutanea_coxa_media:
            return f'{self.dobra_cutanea_coxa_media} mm'
        return None

    def get_dobra_cutanea_panturrilha_medial_display(self):
        if self.dobra_cutanea_panturrilha_medial:
            return f'{self.dobra_cutanea_panturrilha_medial} mm'
        return None

    def get_RCQ(self):
        # Razão Cintura-Quadril
        if self.cintura and self.quadril:
            RCQ = float(self.cintura / self.quadril)
            sexo = self.atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo
            idade = 0
            try:
                idade = int(self.atendimento.prontuario.vinculo.pessoa.pessoafisica.idade)
            except Exception:
                pass
            classificacao = ''
            if sexo == 'M':
                if idade < 30:
                    if RCQ < 0.83:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.83 and RCQ <= 0.88:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.89 and RCQ <= 0.94:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
                elif idade > 29 and idade < 40:
                    if RCQ < 0.84:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.84 and RCQ <= 0.91:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.92 and RCQ <= 0.96:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
                elif idade > 39 and idade < 50:
                    if RCQ < 0.88:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.88 and RCQ <= 0.95:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.96 and RCQ <= 1.00:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
                elif idade > 49 and idade < 60:
                    if RCQ < 0.90:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.90 and RCQ <= 0.96:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.97 and RCQ <= 1.02:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
                else:
                    if RCQ < 0.91:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.91 and RCQ <= 0.98:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.99 and RCQ <= 1.03:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
            else:
                if idade < 30:
                    if RCQ < 0.71:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.71 and RCQ <= 0.77:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.78 and RCQ <= 0.82:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
                elif idade > 29 and idade < 40:
                    if RCQ < 0.72:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.72 and RCQ <= 0.78:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.79 and RCQ <= 0.84:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
                elif idade > 39 and idade < 50:
                    if RCQ < 0.73:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.73 and RCQ <= 0.79:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.80 and RCQ <= 0.87:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
                elif idade > 49 and idade < 60:
                    if RCQ < 0.74:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.74 and RCQ <= 0.81:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.82 and RCQ <= 0.88:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'
                else:
                    if RCQ < 0.76:
                        classificacao = 'Baixo'
                    elif RCQ >= 0.76 and RCQ <= 0.83:
                        classificacao = 'Moderado'
                    elif RCQ >= 0.84 and RCQ <= 0.90:
                        classificacao = 'Alto'
                    else:
                        classificacao = 'Muito alto'

            return f'{RCQ:.2f} ({classificacao})'
        return None

    def get_IMC(self):
        # Índice de Massa Corporal
        if self.peso and self.estatura:
            IMC = float(self.peso) / ((self.estatura / 100) * (self.estatura / 100))
            return Decimal(IMC).quantize(Decimal(10) ** -2)
        return None

    def get_classificacao_IMC(self):
        if self.atendimento.aluno and (self.atendimento.aluno.pessoa_fisica.sexo == 'M' or self.atendimento.aluno.pessoa_fisica.sexo == 'F'):
            idade = 0
            try:
                idade = int(self.atendimento.prontuario.vinculo.pessoa.pessoafisica.idade)
            except Exception:
                pass
            if idade and idade >= 10 and idade <= 19:
                indice_z = self.get_imc_jovens()
                if indice_z < -3:
                    return Antropometria.MAGREZA_ACENTUADA
                elif indice_z >= -3 and indice_z < -2:
                    return Antropometria.MAGREZA
                elif indice_z >= -2 and indice_z < 1:
                    return Antropometria.EUTROFIA
                elif indice_z >= 1 and indice_z < 2:
                    return Antropometria.SOBREPESO
                elif indice_z >= 2 and indice_z < 3:
                    return Antropometria.OBESIDADE
                elif indice_z > 3:
                    return Antropometria.OBESIDADE_GRAVE

        return None

    def get_imc_jovens(self):
        imc = self.get_IMC()
        idade = 0
        try:
            idade = int(self.atendimento.prontuario.vinculo.pessoa.pessoafisica.idade)
        except Exception:
            pass
        if idade and self.atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo == 'M':
            return ((pow((imc / Decimal(Antropometria.z_index_homem[idade]['m'])), Decimal(Antropometria.z_index_homem[idade]['l']))) - 1) / (
                Decimal(Antropometria.z_index_homem[idade]['s']) * Decimal(Antropometria.z_index_homem[idade]['l'])
            )
        elif idade and self.atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo == 'F':
            return ((pow((imc / Decimal(Antropometria.z_index_mulher[idade]['m'])), Decimal(Antropometria.z_index_mulher[idade]['l']))) - 1) / (
                Decimal(Antropometria.z_index_mulher[idade]['s']) * Decimal(Antropometria.z_index_mulher[idade]['l'])
            )

    def get_IAC(self):
        # Índice de Adiposidade Corporal
        if self.quadril and self.estatura:
            estatura_em_metro = self.estatura / 100
            IAC = (float(self.quadril) / (math.sqrt(estatura_em_metro) * estatura_em_metro)) - 18
            return IAC
        return None


class AcuidadeVisual(ModelSaudeFicha):
    com_correcao = models.BooleanField('Com correção', default=False)
    olho_direito = models.CharFieldPlus('Olho Direito', null=True, blank=True)
    olho_esquerdo = models.CharFieldPlus('Olho Esquerdo', null=True, blank=True)

    class Meta:
        verbose_name = 'Acuidade Visual'


class AntecedentesFamiliares(ModelSaudeFicha):
    agravos_primeiro_grau = models.ManyToManyField(Doenca, verbose_name='Agravos à saúde com parentesco de 1º grau', blank=True, related_name="agravos_primeiro_grau")
    agravos_segundo_grau = models.ManyToManyField(Doenca, verbose_name='Agravos à saúde com parentesco de 2º grau', blank=True, related_name="agravos_segundo_grau")


class ProcessoSaudeDoenca(ModelSaudeFicha):
    # Avaliação
    fez_cirurgia = models.BooleanField('Já fez alguma cirurgia', default=False)
    que_cirurgia = models.TextField('Que cirurgia', null=True, blank=True)
    tempo_cirurgia = models.CharField('Quanto tempo da cirurgia', max_length=100, null=True, blank=True)
    hemorragia = models.BooleanField('Histórico de hemorragia', default=False)
    tempo_hemorragia = models.CharField('Há quanto tempo apresentou hemorragia', max_length=100, null=True, blank=True)
    alergia_alimentos = models.BooleanField('Alergia a alimentos', default=False)
    que_alimentos = models.TextField('Quais alimentos', null=True, blank=True)
    doencas_previas = models.BooleanField('Doenças Prévias', default=False)
    que_doencas_previas = models.TextField('Quais Doenças Prévias', null=True, blank=True)
    alergia_medicamentos = models.BooleanField('Alergia a medicamentos', default=False)
    que_medicamentos = models.TextField('Quais medicamentos', null=True, blank=True)
    usa_medicamentos = models.BooleanField('Faz uso de medicamentos rotineiramente', default=False)
    usa_que_medicamentos = models.TextField('Usa quais medicamentos', null=True, blank=True)
    tem_plano_saude = models.BooleanField('Tem Plano de Saúde', default=False)
    tem_plano_odontologico = models.BooleanField('Tem Plano Odontológico', default=False)
    transtorno_psiquiatrico = models.BooleanField('Já teve transtorno psiquiátrico?', default=False)
    qual_transtorno_psiquiatrico = models.CharField('Qual transtorno psiquiátrico?', max_length=255, null=True, blank=True)

    psiquiatra = models.BooleanField('Já passou por psiquiatra?', default=False)
    duracao_psiquiatria = models.PositiveIntegerField('Tempo na psiquiatria', choices=DuracaoPsiquiatria.DURACAOPSIQUIATRIA_CHOICES, null=True, blank=True)
    tempo_psiquiatria = models.PositiveIntegerField('Há quanto tempo esteve no psiquiatra', choices=TempoPsiquiatria.TEMPOPSIQUIATRIA_CHOICES, null=True, blank=True)

    lesoes_ortopedicas = models.BooleanField('Teve lesões ortopédicas', default=False)
    quais_lesoes_ortopedicas = models.TextField('Quais lesões ortopédicas', null=True, blank=True)
    doencas_cronicas = models.ManyToManyField(Doenca, verbose_name='Sofre de alguma doença crônica', blank=True)
    gestante = models.BooleanField('Gestante', default=False)
    problema_auditivo = models.BooleanField('Problemas Auditivos', default=False)
    qual_problema = models.CharField('Qual problema auditivo', max_length=255, null=True, blank=True)


class HabitosDeVida(ModelSaudeFicha):
    FREQUENCIA_SEMANAL_CHOICES = ((1, ''), (2, 'Menos de 3x/semana'), (3, '3 ou mais x/semana'))
    DURACAO_ATIVIDADE_CHOICES = ((1, ''), (2, 'Menos de 50 min/dia'), (3, '50 min ou mais/dia'))
    FREQUENCIA_BEBIDA_CHOICES = ((1, ''), (2, '1x/dia'), (3, '1x/semana'), (4, '1x/mês'), (5, '1x/ano'))

    HORAS_SONO_CHOICES = ((1, ''), (2, 'Menos de 8 horas/dia'), (3, '8 ou mais horas/dia'))

    REFEICOES_DIA_CHOICES = (
        (1, ''),
        (2, '1 refeição'),
        (3, '2 refeições'),
        (4, '3 refeições'),
        (5, '4 refeições'),
        (6, '5 refeições'),
        (7, '6 refeições'),
        (8, 'Mais de 6 refeições'),
    )

    # Avaliação
    atividade_fisica = models.BooleanField('Pratica atividade física', default=False)
    qual_atividade = models.CharField('Qual atividade', max_length=250, null=True, blank=True)
    frequencia_semanal = models.PositiveIntegerField('Qual a frequência semanal', null=True, blank=True, choices=FREQUENCIA_SEMANAL_CHOICES)
    duracao_atividade = models.PositiveIntegerField('Duração da atividade física', null=True, blank=True, choices=DURACAO_ATIVIDADE_CHOICES)
    fuma = models.BooleanField('Fuma', default=False)
    frequencia_fumo = models.DecimalFieldPlus('Número de cigarros por dia', decimal_places=1, null=True, blank=True)
    usa_drogas = models.BooleanField('Faz uso ou já usou drogas ilícitas', default=False)
    que_drogas = models.ManyToManyField(Droga, verbose_name='Quais drogas', blank=True)
    outras_drogas = models.CharField('Outras drogas', max_length=250, null=True, blank=True)
    bebe = models.BooleanField('Ingere bebidas alcoólicas', default=False)
    frequencia_bebida = models.PositiveIntegerField('Frequência mínima de ingestão de bebidas alcoólicas', null=True, blank=True, choices=FREQUENCIA_BEBIDA_CHOICES)
    dificuldade_dormir = models.BooleanField('Tem dificuldade para dormir', default=False)
    horas_sono = models.PositiveIntegerField('Horas de sono diárias', null=True, blank=True, choices=HORAS_SONO_CHOICES)
    refeicoes_por_dia = models.PositiveIntegerField('Quantas refeições faz por dia', null=True, blank=True, choices=REFEICOES_DIA_CHOICES)
    vida_sexual_ativa = models.BooleanField('Tem vida sexual ativa', default=False)
    metodo_contraceptivo = models.BooleanField('Faz uso de algum método contraceptivo', default=False)
    qual_metodo_contraceptivo = models.ManyToManyField(MetodoContraceptivo, verbose_name='Qual método contraceptivo', blank=True)
    uso_internet = models.BooleanField('Faz uso da internet?', default=False)
    tempo_uso_internet = models.PositiveIntegerField('Qual o tempo de uso', null=True, blank=True, choices=UsoInternet.USOINTERNET_CHOICES)
    objetivo_uso_internet = models.CharField('Objetivo do uso', max_length=250, null=True, blank=True)

    class Meta:
        verbose_name = 'Hábitos de Vida'

    def get_tempo_uso_internet(self):
        if self.tempo_uso_internet == 1:
            return 'Menos de 2 horas/dia'
        elif self.tempo_uso_internet == 2:
            return '2 a 3 horas/dia'
        elif self.tempo_uso_internet == 3:
            return '3 a 4 horas/dia'
        elif self.tempo_uso_internet == 4:
            return '4 ou mais horas/dia'
        return None

    def get_objetivo_uso_internet(self):
        lista = self.objetivo_uso_internet.split(',')
        objetivo = []
        for codigo in lista:
            if 'Pesquisa relacionada a estudo' in codigo:
                objetivo.append('Pesquisa relacionada a estudo')
            elif 'Jogos' in codigo:
                objetivo.append('Jogos')
            elif 'Redes Sociais' in codigo:
                objetivo.append('Redes Sociais')
            elif 'Trabalho' in codigo:
                objetivo.append('Trabalho')
            elif 'Outros' in codigo:
                objetivo.append('Outros')
        return objetivo

    def get_frequencia_atividade(self):
        if self.frequencia_semanal == 2:
            return 'Menos de 3x/semana'
        elif self.frequencia_semanal == 3:
            return '3 ou mais x/semana'
        return None

    def get_duracao_atividade(self):
        if self.duracao_atividade == 2:
            return 'Menos de 50 min/dia'
        elif self.duracao_atividade == 3:
            return '50 min ou mais/dia'
        return None

    def get_frequencia_bebida(self):
        if self.frequencia_bebida == 2:
            return '1x/dia'
        elif self.frequencia_bebida == 3:
            return '1x/semana'
        elif self.frequencia_bebida == 4:
            return '1x/mês'
        elif self.frequencia_bebida == 5:
            return '1x/ano'
        return None

    def get_horas_sono(self):
        if self.horas_sono == 2:
            return 'Menos de 8 horas/dia'
        elif self.horas_sono == 3:
            return '8 ou mais horas/dia'
        return None

    def get_refeicoes(self):
        if self.refeicoes_por_dia and not self.refeicoes_por_dia == 1:
            if self.refeicoes_por_dia == 2:
                return '1 refeição'
            elif self.refeicoes_por_dia == 8:
                return 'Mais de 6 refeições'
            else:
                return str(self.refeicoes_por_dia - 1) + ' refeições'
        return None


class DesenvolvimentoPessoal(ModelSaudeFicha):
    AUTO_REFERIDO = 'Problema auto-referido'
    DIAGNOSTICO_PREVIO = 'Problema com diagnóstico prévio'
    DESENVOLVIMENTO_CHOICES = ((AUTO_REFERIDO, AUTO_REFERIDO), (DIAGNOSTICO_PREVIO, DIAGNOSTICO_PREVIO))
    # Avaliação
    problema_aprendizado = models.BooleanField('Já teve ou tem algum problema de aprendizado', default=False)
    qual_problema_aprendizado = models.CharField('Qual problema de aprendizado', max_length=255, null=True, blank=True)
    origem_problema = models.CharFieldPlus('Origem do Problema', max_length=50, null=True, blank=True, choices=DESENVOLVIMENTO_CHOICES)

    class Meta:
        verbose_name = 'Desenvolvimento Pessoal'


class PercepcaoSaudeBucal(ModelSaudeFicha):
    # Avaliação
    qtd_vezes_fio_dental_ultima_semana = models.PositiveIntegerField('Quantas vezes usou fio dental na última semana?', null=True, blank=True)
    qtd_dias_consumiu_doce_ultima_semana = models.PositiveIntegerField('Na última semana quantos dias consumiu doces, balas, bolos ou refrigerantes?', null=True, blank=True)
    usa_protese = models.BooleanField('Usa prótese?', default=False)
    usa_aparelho_ortodontico = models.BooleanField('Usa aparelho ortodôntico?', default=False)

    foi_dentista_anteriormente = models.BooleanField('Já foi a um dentista anteriormente', default=False)
    tempo_ultima_vez_dentista = models.PositiveIntegerField('Quanto tempo faz que foi a última vez ao dentista', choices=TempoSemDentista.TEMPO_CHOICES, null=True, blank=True)
    dificuldades = models.BooleanField(
        'Nos últimos 6 meses teve alguma dificuldade relacionada à boca, dente, prótese ou aparelho ortodôntico que lhe causou alguma dificuldade', default=False
    )
    grau_dificuldade_sorrir = models.PositiveIntegerField('Grau de dificuldade em sorrir', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_sorrir = ForeignKeyPlus(
        'saude.DificuldadeOral', verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_sorrir"
    )
    grau_dificuldade_falar = models.PositiveIntegerField('Grau de dificuldade em falar', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_falar = ForeignKeyPlus(
        DificuldadeOral, verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_falar"
    )
    grau_dificuldade_comer = models.PositiveIntegerField('Grau de dificuldade em comer', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_comer = ForeignKeyPlus(
        DificuldadeOral, verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_comer"
    )
    grau_dificuldade_relacionar = models.PositiveIntegerField('Grau de dificuldade em relacionar-se socialmente', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_relacionar = ForeignKeyPlus(
        DificuldadeOral, verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_relacionar"
    )
    grau_dificuldade_manter_humor = models.PositiveIntegerField('Grau de dificuldade em manter o humor habitual', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_manter_humor = ForeignKeyPlus(
        DificuldadeOral, verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_manter_humor"
    )
    grau_dificuldade_estudar = models.PositiveIntegerField('Grau de dificuldade em estudar', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_estudar = ForeignKeyPlus(
        DificuldadeOral, verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_estudar"
    )
    grau_dificuldade_trabalhar = models.PositiveIntegerField('Grau de dificuldade em trabalhar', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_trabalhar = ForeignKeyPlus(
        DificuldadeOral, verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_trabalhar"
    )
    grau_dificuldade_higienizar = models.PositiveIntegerField('Grau de dificuldade em higienizar a boca', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_higienizar = ForeignKeyPlus(
        DificuldadeOral, verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_higienizar"
    )
    grau_dificuldade_dormir = models.PositiveIntegerField('Grau de dificuldade em dormir', choices=GrauDificuldade.GRAU_CHOICES, null=True, blank=True)
    motivo_dificuldade_dormir = ForeignKeyPlus(
        DificuldadeOral, verbose_name='Qual motivo você atribui como responsável?', null=True, blank=True, related_name="motivo_dificuldade_dormir"
    )

    class Meta:
        verbose_name = 'Percepção de Saúde Bucal'


class ExameFisico(ModelSaudeFicha):
    # Avaliação
    ectoscopia_alterada = models.BooleanField('Ectoscopia alterada', default=False)
    alteracao_ectoscopia = models.CharField('Alteração na ectoscopia', max_length=255, null=True, blank=True)
    acv_alterado = models.BooleanField('Aparelho cardiovascular alterado', default=False)
    alteracao_acv = models.CharField('Alteração no aparelho cardiovascular', max_length=255, null=True, blank=True)
    ar_alterado = models.BooleanField('Aparelho respiratório alterado', default=False)
    alteracao_ar = models.CharField('Alteração no aparelho respiratório', max_length=255, null=True, blank=True)
    abdome_alterado = models.BooleanField('Abdome alterado', default=False)
    alteracao_abdome = models.CharField('Alteração no abdome', max_length=255, null=True, blank=True)
    mmi_alterados = models.BooleanField('Membros inferiores alterados', default=False)
    alteracao_mmi = models.CharField('Alteração nos membros inferiores', max_length=255, null=True, blank=True)
    mms_alterados = models.BooleanField('Membros superiores alterados', default=False)
    alteracao_mms = models.CharField('Alteração nos membros superiores', max_length=255, null=True, blank=True)
    outras_alteracoes = models.BooleanField('Outros órgãos/sistemas alterados', default=False)
    outras_alteracoes_descricao = models.CharField('Descrição das outras alterações', max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = 'Exame Pessoal'


class VacinasAtivasManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ativa=True)


class Vacina(models.ModelPlus):
    objects = models.Manager()
    ativas = VacinasAtivasManager()

    nome = models.CharField('Nome', max_length=200, null=False)
    doses = models.PositiveIntegerField('Número de Doses', null=False)
    eh_covid = models.BooleanField('É de COVID-19?', default=False)
    ativa = models.BooleanField('Ativa', default=True)

    class Meta:
        verbose_name = 'Vacina'
        verbose_name_plural = 'Vacinas'

    def __str__(self):
        return self.nome

    def clean(self, *args, **kwargs):
        if self.doses == 0:
            raise ValidationError('O Número de Doses deve ser maior que 0.')
        if self.pk and self.eh_covid and Vacina.objects.filter(eh_covid=True).exclude(id=self.pk).exists():
            raise ValidationError('Já existe uma vacina de COVID cadastrada.')
        if not self.pk and self.eh_covid and Vacina.objects.filter(eh_covid=True).exists():
            raise ValidationError('Já existe uma vacina de COVID cadastrada.')

        return super().clean(*args, **kwargs)


class CartaoVacinal(models.ModelPlus):
    prontuario = ForeignKeyPlus(Prontuario, verbose_name='Prontuário')
    vacina = ForeignKeyPlus(Vacina, verbose_name='Vacina')
    # Aplicação da vacina
    profissional = ForeignKeyPlus(Servidor, verbose_name='Profissional', null=True, blank=True)
    data_prevista = models.DateField('Aprazamento', null=True, blank=True)
    data_vacinacao = models.DateField('Data da Vacinação', null=True, blank=True)
    sem_data = models.BooleanField('Desconhece data de vacinação', default=None, null=True)
    externo = models.BooleanField('Aplicação Externa', default=False)
    numero_dose = models.PositiveIntegerField('Número da Dose', null=False)
    obs = models.CharField('Observação', max_length=500, null=True, blank=True)

    class Meta:
        verbose_name = 'Cartão Vacinal'
        verbose_name_plural = 'Cartões Vacinais'

    def get_numero_dose(self):
        if self.numero_dose == 0:
            return 'Reforço'
        return str(self.numero_dose) + 'ª'

    def get_aplicacao_externa(self):
        if self.externo:
            return 'Sim'
        return 'Não'

    def pode_vacinar(self):
        if self.numero_dose in [0, 1]:
            return True
        else:
            registro_vacina = CartaoVacinal.objects.filter(vacina=self.vacina, prontuario=self.prontuario, numero_dose=self.numero_dose - 1).latest('id')
            data_vacinacao_anterior = registro_vacina.data_vacinacao
            numero_dose = CartaoVacinal.objects.get(pk=self.pk).numero_dose
            sem_data = registro_vacina.sem_data
            if numero_dose != 0 and data_vacinacao_anterior or sem_data:
                return True
        return False

    def pode_alterar_registro_vacina(self, user):
        if self.profissional:
            return self.profissional.id == Servidor.objects.get(pk=user.get_profile().id).id
        else:
            return False

    def teve_primeira_dose(self):
        vacinacao_anterior = CartaoVacinal.objects.filter(vacina=self.vacina, prontuario=self.prontuario, pk__lt=self.pk)
        if self.numero_dose == 0:
            # Reforços não precisam da primeira vacinação para permitirem o agendamento da previsão
            return True
        elif vacinacao_anterior:
            vacinacao_anterior = vacinacao_anterior.latest('id')
            if vacinacao_anterior.data_vacinacao or (vacinacao_anterior.sem_data and not vacinacao_anterior.data_vacinacao):
                return True
        return False

    def nao_pode_deletar_vacina(self, user):
        return (
            CartaoVacinal.objects.filter(profissional__isnull=False)
            .filter(Q(prontuario=self.prontuario), Q(vacina=self.vacina), ~Q(profissional=user.get_vinculo().relacionamento))
            .exists()
        )

    def pode_remover_dose(self, user):
        return (not self.data_vacinacao and not self.sem_data) or (self.data_vacinacao and ((user.get_vinculo().relacionamento == self.profissional) or (not self.profissional and get_uo(user) == get_uo(self.prontuario.vinculo.user))))

    def get_aluno(self):
        if Aluno.objects.filter(pessoa_fisica=self.prontuario.vinculo.pessoa.pessoafisica).exists():
            return Aluno.objects.get(pessoa_fisica=self.prontuario.vinculo.pessoa.pessoafisica)
        return None

    def get_vacinas(self):
        texto = list()
        cartoes = CartaoVacinal.objects.filter(prontuario__vinculo=self.prontuario.vinculo).distinct('vacina')
        if cartoes.exists():
            for cartao in cartoes:
                texto.append(cartao.vacina.nome)
        return ', '.join(texto)

    def get_vacinas_atrasadas(self):
        texto = list()
        hoje = datetime.datetime.today().date()
        cartoes = CartaoVacinal.objects.filter(prontuario__vinculo=self.prontuario.vinculo, data_prevista__lt=hoje).distinct('vacina')
        if cartoes.exists():
            for cartao in cartoes:
                texto.append(cartao.vacina.nome)
        return ', '.join(texto)

    def get_vacinas_atrasadas_com_previsao(self):
        texto = list()
        hoje = datetime.datetime.today().date()
        cartoes = CartaoVacinal.objects.filter(prontuario__vinculo=self.prontuario.vinculo, data_prevista__lt=hoje, data_vacinacao__isnull=True).distinct('vacina')
        if cartoes.exists():
            for cartao in cartoes:
                string = '{} (Previsão: {})'.format(cartao.vacina.nome, cartao.data_prevista.strftime('%d/%m/%Y'))
                texto.append(string)
        return ', '.join(texto)

    def get_vacinas_aprazadas_proximos_15dias(self):
        texto = list()
        hoje = datetime.datetime.today().date()
        proximos_15_dias = hoje + relativedelta(days=15)
        cartoes = CartaoVacinal.objects.filter(prontuario__vinculo=self.prontuario.vinculo, data_prevista__gte=hoje, data_prevista__lte=proximos_15_dias).distinct('vacina')
        if cartoes.exists():
            for cartao in cartoes:
                texto.append(cartao.vacina.nome)
        return ', '.join(texto)


class Motivo(ModelSaudeFicha):
    EUPNEICO = '1'
    DISPNEICO = '2'
    ORTOPNEICO = '3'
    TAQUIPNEICO = '4'
    BRADIPNEICO = '5'
    APNEIA = '6'

    RESPIRACAO_CHOICES = (
        (EUPNEICO, 'Eupnéica'),
        (DISPNEICO, 'Dispnéica'),
        (ORTOPNEICO, 'Ortopnéica'),
        (TAQUIPNEICO, 'Taquipnéica'),
        (BRADIPNEICO, 'Bradipnéica'),
        (APNEIA, 'Apnéia'),
    )

    HIPOTERMIA = '1'
    NORMAL_AFEBRIL = '2'
    HIPERTERMIA = '3'
    PIREXIA = '4'
    HIPERPIREXIA = '5'

    TEMPERATURA_CHOICES = ((HIPOTERMIA, 'Hipotermia'), (NORMAL_AFEBRIL, 'Normal/Afebril'), (HIPERTERMIA, 'Hipertemia'), (PIREXIA, 'Pirexia'), (HIPERPIREXIA, 'Hiperpirexia'))

    motivo_atendimento = models.TextField('Motivo do Atendimento', null=True, blank=True)
    pressao_sistolica = models.PositiveIntegerField('Pressão Sistólica', null=True, blank=True)
    pressao_diastolica = models.PositiveIntegerField('Pressão Diastólica', help_text='Em mmHg', null=True, blank=True)
    temperatura = models.DecimalFieldPlus('Temperatura', decimal_places=1, help_text='Em °C', null=True, blank=True)
    respiracao = models.PositiveIntegerField('Respiração', help_text='Em rpm', null=True, blank=True)
    pulsacao = models.PositiveIntegerField('Pulsação', help_text='Em bpm', null=True, blank=True)
    escala_dor = models.PositiveIntegerField('Escala de Dor', null=True, blank=True)
    temperatura_categoria = models.CharFieldPlus('Temperatura', max_length=2, null=True, blank=True, choices=TEMPERATURA_CHOICES)
    respiracao_categoria = models.CharFieldPlus('Respiração', max_length=2, null=True, blank=True, choices=RESPIRACAO_CHOICES)
    estatura = models.PositiveIntegerField('Estatura', null=True, blank=True, help_text='Em cm')
    peso = models.DecimalFieldPlus('Peso', null=True, blank=True, decimal_places=3, help_text='Em kg')

    class Meta:
        verbose_name = 'Motivo do Atendimento'
        verbose_name_plural = 'Motivos do Atendimentos'

    def get_pressao_display(self):
        if self.pressao_sistolica and self.pressao_diastolica:
            return f'{self.pressao_sistolica}x{self.pressao_diastolica} mmHg'
        return None

    def get_pulsacao_display(self):
        if self.pulsacao:
            return f'{self.pulsacao} bpm'
        return None

    def get_respiracao_display(self):
        if self.respiracao:
            return f'{self.respiracao} rpm'
        return None

    def get_estatura_display(self):
        if self.estatura:
            return f'{self.estatura} cm'
        return None

    def get_temperatura_display(self):
        if self.temperatura:
            return f'{format_money(self.temperatura)} °C'
        return None

    def get_respiracao_categoria_display(self):
        if self.respiracao_categoria == Motivo.EUPNEICO:
            return 'Eupnéica'
        elif self.respiracao_categoria == Motivo.DISPNEICO:
            return 'Dispnéica'
        elif self.respiracao_categoria == Motivo.ORTOPNEICO:
            return 'Ortopnéica'
        elif self.respiracao_categoria == Motivo.TAQUIPNEICO:
            return 'Taquipnéica'
        elif self.respiracao_categoria == Motivo.BRADIPNEICO:
            return 'Bradipnéica'
        elif self.respiracao_categoria == Motivo.APNEIA:
            return 'Apnéia'

    def get_temperatura_categoria_display(self):
        if self.temperatura_categoria == Motivo.HIPOTERMIA:
            return 'Hipotermia'
        elif self.temperatura_categoria == Motivo.NORMAL_AFEBRIL:
            return 'Normal/Afebril'
        elif self.temperatura_categoria == Motivo.HIPERTERMIA:
            return 'Hipertermia'
        elif self.temperatura_categoria == Motivo.PIREXIA:
            return 'Pirexia'
        elif self.temperatura_categoria == Motivo.HIPERPIREXIA:
            return 'Hiperpirexia'


class Anamnese(ModelSaudeFicha):
    hda = models.TextField('HDA')
    gravida = models.BooleanField('Grávida?', null=True)
    ectoscopia_alterada = models.BooleanField('Ectoscopia alterada', default=False)
    alteracao_ectoscopia = models.CharField('Alteração na ectoscopia', max_length=255, null=True, blank=True)
    acv_alterado = models.BooleanField('Aparelho cardiovascular alterado', default=False)
    alteracao_acv = models.CharField('Alteração no aparelho cardiovascular', max_length=255, null=True, blank=True)
    ar_alterado = models.BooleanField('Aparelho respiratório alterado', default=False)
    alteracao_ar = models.CharField('Alteração no aparelho respiratório', max_length=255, null=True, blank=True)
    abdome_alterado = models.BooleanField('Abdome alterado', default=False)
    alteracao_abdome = models.CharField('Alteração no abdome', max_length=255, null=True, blank=True)
    mmi_alterados = models.BooleanField('Membros inferiores alterados', default=False)
    alteracao_mmi = models.CharField('Alteração nos membros inferiores', max_length=255, null=True, blank=True)
    mms_alterados = models.BooleanField('Membros superiores alterados', default=False)
    alteracao_mms = models.CharField('Alteração nos membros superiores', max_length=255, null=True, blank=True)
    outras_alteracoes = models.BooleanField('Outros órgãos/sistemas alterados', default=False)
    outras_alteracoes_descricao = models.CharField('Descrição das outras alterações', max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = 'Anamnese'
        verbose_name_plural = 'Anamneses'


class CondutaMedica(ModelSaudeFicha):
    conduta = models.TextField('Conduta')
    encaminhado_enfermagem = models.BooleanField(
        'Encaminhado para Enfermagem', help_text='Marque esta opção caso esta conduta médica necessite de uma intervenção de enfermagem.', default=False
    )
    atendido = models.BooleanField('Atendido', default=False)
    encaminhado_fisioterapia = models.BooleanField(
        'Encaminhado para Fisioterapia', help_text='Marque esta opção caso esta conduta médica necessite de uma intervenção de fisioterapia.', default=False
    )
    atendido_fisioterapia = models.BooleanField('Atendido', default=False)

    class Meta:
        verbose_name = 'Conduta Médica'
        verbose_name_plural = 'Condutas Médicas'

    def __str__(self):
        return self.conduta[:40] + (self.conduta[40:] and '...')


class ProcedimentoEnfermagem(models.ModelPlus):
    denominacao = models.CharField('Denominação', max_length=255)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Procedimento de Enfermagem'
        verbose_name_plural = 'Procedimentos de Enfermagem'

    def __str__(self):
        return self.denominacao


class IntervencaoEnfermagem(ModelSaudeFicha):
    procedimento_enfermagem = ForeignKeyPlus(ProcedimentoEnfermagem, verbose_name='Procedimento')
    descricao = models.TextField('Descrição', null=True, blank=True)
    conduta_medica = ForeignKeyPlus(CondutaMedica, verbose_name='Conduta Médica', null=True)

    class Meta:
        verbose_name = 'Intervenção de Enfermagem'
        verbose_name_plural = 'Intervenções de Enfermagem'


class Cid(models.ModelPlus):
    SEARCH_FIELDS = ['codigo', 'denominacao']
    codigo = models.CharField('Código', max_length=4, null=False)
    denominacao = models.CharField('Denominação', max_length=255, null=False)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Doença'
        verbose_name_plural = 'Doenças'

    def __str__(self):
        return f'{self.codigo} - {self.denominacao}'


class HipoteseDiagnostica(ModelSaudeFicha):
    cid = ForeignKeyPlus(Cid, verbose_name='CID')
    sigilo = models.CharFieldPlus('Sigilo', max_length=5000, null=True, blank=True)

    class Meta:
        verbose_name = 'Hipótese Diagnóstica'
        verbose_name_plural = 'Hipóteses Diagnósticas'

    def __str__(self):
        return str(self.cid)


class RegiaoBucal:
    REGIAOBUCAL_CHOICES = (
        (None, '---------------------'),
        ('Arcada Dentária', 'Arcada Dentária'),
        ('Assoalho', 'Assoalho'),
        ('ATM', 'ATM'),
        ('Lábio Inferior Externo', 'Lábio Inferior Externo'),
        ('Lábio Inferior Interno', 'Lábio Inferior Interno'),
        ('Lábio Superior Externo', 'Lábio Superior Externo'),
        ('Lábio Superior Interno', 'Lábio Superior Interno'),
        ('Língua', 'Língua'),
        ('Mucosa Jugal Direita', 'Mucosa Jugal Direita'),
        ('Mucosa Jugal Esquerda', 'Mucosa Jugal Esquerda'),
        ('Palato', 'Palato'),
        ('Trígono Retromolar', 'Trígono Retromolar'),
        ('S1', 'S1'),
        ('S2', 'S2'),
        ('S3', 'S3'),
        ('S4', 'S4'),
        ('S5', 'S5'),
        ('S6', 'S6'),
        ('S1 - S3', 'S1 - S3'),
        ('S4 - S6', 'S4 - S6'),
        ('S1 - S6', 'S1 - S6'),
    )


class CategoriaSituacaoClinica:
    CATEGORIASITUACAOCLINICA_CHOICES = (
        ('#2ecc71', '#2ecc71'),  # verde
        ('#f1c40f', '#f1c40f'),  # amarelo escuro
        ('#2a84bf', '#2a84bf'),  # azul
        ('#8e44ad', '#8e44ad'),  # roxo
        ('#FF0000', '#FF0000'),  # vermelho
        ('#7f8c8d', '#7f8c8d'),  # cinza escuro
        ('#FF8C00', '#FF8C00'),  # laranja
        ('#16a085', '#16a085'),  # verde escuro
        ('#2c3e50', '#2c3e50'),  # azul marinho
        ('#bdc3c7', '#bdc3c7'),  # cinza claro
    )


class ProcedimentoOdontologia(models.ModelPlus):
    APLICACAO_TOPICA_FLUOR = 3
    EXAME_CLINICO = 5
    PROFILAXIA = 10
    ORIENTACAO_HIGIENE_BUCAL = 8

    denominacao = models.CharField('Denominação', max_length=255)
    ativo = models.BooleanField('Ativo', default=True)
    pode_odontologo = models.BooleanField('Pode ser realizado por Odontólogo', default=True)
    pode_tecnico = models.BooleanField('Pode ser realizado por Técnico de Saúde Bucal', default=False)

    class Meta:
        verbose_name = 'Procedimento de Odontologia'
        verbose_name_plural = 'Procedimentos de Odontologia'

    def __str__(self):
        return self.denominacao


class SituacaoClinica(models.ModelPlus):
    CHEIO = '1'
    CONTORNO = '2'

    PREENCHIMENTO_CHOICES = ((CHEIO, 'Cheio'), (CONTORNO, 'Contorno'))

    C = 'C'
    P = 'P'
    O = 'O'  # noqa

    CPOD_CHOICES = ((C, 'C'), (P, 'P'), (O, 'O'))

    DENTE_AUSENTE_EXTRAIDO_OUTRAS_RAZOES = 11
    DENTE_EXTRAIDO_CARIE = 12
    EXODONTIA_POR_CARIE = 13
    EXODONTIA_POR_OUTROS_MOTIVOS = 14
    CALCULO = 16
    RESTAURACAO_COROA_SATISFATORIA = 19
    TRAT_ENDODONTICO_CONCLUIDO = 20
    TRAT_ENDODONTICO_INDICADO = 21
    SANGRAMENTO = 22

    descricao = models.CharField(verbose_name='Descrição', max_length=200, null=False)
    categoria = models.CharField('Categoria', max_length=10, choices=CategoriaSituacaoClinica.CATEGORIASITUACAOCLINICA_CHOICES, null=False)
    preenchimento = models.CharField(verbose_name='Preenchimento', max_length=2, choices=PREENCHIMENTO_CHOICES, default=CHEIO)
    cpod = models.CharField(verbose_name='CPOD', max_length=2, choices=CPOD_CHOICES, null=True, blank=True)

    class Meta:
        verbose_name = 'Situação Clínica'
        verbose_name_plural = 'Situações Clínicas'
        unique_together = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_categoria(self):
        return mark_safe(
            '<span id=\''
            + self.descricao
            + '\'></span><script>document.getElementById(\''
            + self.descricao
            + '\').parentNode.style.background=\''
            + self.categoria
            + '\';</script>'
        )

    get_categoria.short_description = 'Categoria'


class Odontograma(ModelSaudeFicha):
    dentes_alterados = models.TextField('Marcações do Odontograma', null=False)
    queixa_principal = models.CharFieldPlus('Queixa Principal', max_length=5000, null=True, blank=True)
    tipo_consulta = models.ManyToManyFieldPlus('saude.TipoConsultaOdontologia', related_name='tipo_consulta_odontologia')
    encaminhado_enfermagem = models.BooleanField(
        'Encaminhado para Enfermagem', help_text='Marque esta opção caso este atendimento necessite de uma intervenção de enfermagem.', default=False
    )
    atendido = models.BooleanField('Atendido', default=False)
    atendido_por_vinculo = models.ForeignKeyPlus('comum.Vinculo', null=True, blank=True, on_delete=models.SET_NULL)
    atendido_em = models.DateTimeFieldPlus('Atendido Em', null=True, blank=True)
    salvo = models.BooleanField('Salvo', default=False)

    '''
    Descrição do atributo dentes alterados:
    dentes_alterados é uma concatenação por hífen (-) de códigos representando as alterações nas faces dos dentes
    x = A_F_NN_ID
    x[0]   -> A (Arcada) - A = Adulto, I = Infantil
    x[2]   -> F (Face do dente) - V = Vestibular, D = Distal, O = Oclusal/Incisal, M = Mesial, P = Palatal/Lingual, C = Cervical, R = Raiz
    x[4:6] -> NN (Número do dente) - Número de dois dígitos que identifica o dente
    x[7:]  -> ID - Identificador da SITUAÇÃO CLÍNICA associada para aquela face
    Victor Hugo(2103241), 10/11/2014
    '''

    class Meta:
        verbose_name = 'Odontograma'
        verbose_name_plural = 'Odontogramas'

    def dentes_alterados_lista(self):
        lista = self.dentes_alterados.split('-')
        lista.remove('')  # Retira a última face vazia gerada pelo split

        teste = {}
        for idx, item in enumerate(lista):
            teste[idx] = item[4:6]
        import operator

        ordenou = sorted(list(teste.items()), key=operator.itemgetter(1))
        lista_ordenada = list()
        for idx, item in enumerate(ordenou):
            lista_ordenada.append(lista[item[0]])
        return lista_ordenada

    def get_dentes_alterados(self):
        # Retorna uma lista com todos os dentes que estão marcados com alguma situação clínica.
        faces = self.dentes_alterados_lista()
        dentes_alterados = []
        for codigo in faces:
            if not codigo[4:6] in dentes_alterados:
                dentes_alterados.append(codigo[4:6])
        dentes_alterados.sort()
        return dentes_alterados

    def get_situacoes_clinicas(self):
        # Retorna uma lista com todas as situações clínicas marcadas neste odontograma.
        faces = self.dentes_alterados_lista()
        situacoes_clinicas = []
        for codigo in faces:
            if not codigo[7:] in situacoes_clinicas:
                situacoes_clinicas.append(codigo[7:])
        return SituacaoClinica.objects.filter(id__in=situacoes_clinicas)

    def get_dentes_cariados(self):
        # Retorna uma lista com os dentes que possuem cárie em qualquer uma de suas faces.
        faces = self.dentes_alterados_lista()
        id_carie = 1
        dentes_cariados = []
        for codigo in faces:
            if codigo[7:] == str(id_carie) and (not codigo[4:6] in dentes_cariados):
                dentes_cariados.append(codigo[4:6])
        return dentes_cariados

    def get_qtd_dentes_cariados(self):
        # Retorna a quantidade de dentes cariados
        return len(self.get_dentes_cariados())

    def get_indice_cpod(self):
        p = c = o = 0
        dentes_alterados = self.get_dentes_alterados()
        for dente in dentes_alterados:
            situacoes_clinicas = []
            alteracoes = [s for s in self.dentes_alterados_lista() if dente in s]
            for alteracao in alteracoes:
                situacoes_clinicas.append(alteracao[7:])

            if SituacaoClinica.objects.filter(cpod=SituacaoClinica.P).filter(id__in=situacoes_clinicas).exists():
                p = p + 1
            elif SituacaoClinica.objects.filter(cpod=SituacaoClinica.C).filter(id__in=situacoes_clinicas).exists():
                c = c + 1

            elif SituacaoClinica.objects.filter(cpod=SituacaoClinica.O).filter(id__in=situacoes_clinicas).exists():
                o = o + 1

        return c + p + o, c, p, o


class ProcedimentoOdontologico(ModelSaudeFicha):
    AVALIACAO_CLINICA_INICIAL = 'Avaliação Clínica Inicial'
    CONSULTA = 'Consulta'
    URGENCIA = 'Urgência'
    CONTINUACAO_TRATAMENTO = 'Continuação de Tratamento'
    CONCLUSAO_TRATAMENTO = 'Conclusão de tratamento'
    REAVALIACAO = 'Reavaliação'

    TIPOCONSULTA_CHOICES = (
        (AVALIACAO_CLINICA_INICIAL, AVALIACAO_CLINICA_INICIAL),
        (CONCLUSAO_TRATAMENTO, CONCLUSAO_TRATAMENTO),
        (CONSULTA, CONSULTA),
        (CONTINUACAO_TRATAMENTO, CONTINUACAO_TRATAMENTO),
        (REAVALIACAO, REAVALIACAO),
        (URGENCIA, URGENCIA),
    )

    procedimento = models.ForeignKeyPlus(ProcedimentoOdontologia, on_delete=models.CASCADE)
    tipo_consulta = models.CharField('Tipo de Consulta', max_length=50, choices=TIPOCONSULTA_CHOICES, default=AVALIACAO_CLINICA_INICIAL)
    faces_marcadas = models.TextField('Faces', null=False)
    regiao_bucal = models.CharField('Região Bucal', max_length=100, choices=RegiaoBucal.REGIAOBUCAL_CHOICES, null=True, blank=True)
    observacao = models.TextField('Observações', null=True, blank=True)

    class Meta:
        verbose_name = 'Procedimento Odontológico'
        verbose_name_plural = 'Procedimentos Odontológicos'

    def get_elementos(self):
        if not self.faces_marcadas:
            return None
        faces = self.faces_marcadas.split('-')
        faces.remove('')  # Retira a última face vazia gerada pelo split
        dentes = []
        while len(faces) > 0:
            arcada_dente = faces[0][0]
            numero_dente = faces[0][4:6]
            dente = '<strong>' + numero_dente + '</strong>'
            faces_alteradas = ' '
            contador = 0
            if arcada_dente + '_T_' + numero_dente in faces:
                faces_alteradas += 'Todas'
                faces.remove(arcada_dente + '_T_' + numero_dente)
                contador += 1
            if arcada_dente + '_V_' + numero_dente in faces:
                faces_alteradas += 'V'
                faces.remove(arcada_dente + '_V_' + numero_dente)
                contador += 1
            if arcada_dente + '_P_' + numero_dente in faces:
                faces_alteradas += 'L'
                faces.remove(arcada_dente + '_P_' + numero_dente)
                contador += 1
            if arcada_dente + '_M_' + numero_dente in faces:
                faces_alteradas += 'M'
                faces.remove(arcada_dente + '_M_' + numero_dente)
                contador += 1
            if arcada_dente + '_D_' + numero_dente in faces:
                faces_alteradas += 'D'
                faces.remove(arcada_dente + '_D_' + numero_dente)
                contador += 1
            if arcada_dente + '_O_' + numero_dente in faces:
                if numero_dente in ['11', '12', '13', '21', '22', '23', '31', '32', '33', '41', '42', '43']:
                    faces_alteradas += 'I'
                else:
                    faces_alteradas += 'O'
                faces.remove(arcada_dente + '_O_' + numero_dente)
                contador += 1

            if arcada_dente + '_C_' + numero_dente in faces:
                faces_alteradas += 'C'
                faces.remove(arcada_dente + '_C_' + numero_dente)
                contador += 1
            if arcada_dente + '_R_' + numero_dente in faces:
                faces_alteradas += 'R'
                faces.remove(arcada_dente + '_R_' + numero_dente)
                contador += 1
            if contador == 0:
                return
            if faces_alteradas:
                dente += ' - ' + faces_alteradas
            dentes.append(dente)

        return dentes


class ExamePeriodontal(ModelSaudeFicha):
    S1 = 'S1'
    S2 = 'S2'
    S3 = 'S3'
    S4 = 'S4'
    S5 = 'S5'
    S6 = 'S6'
    S1_S3 = 'S1 - S3'
    S4_S6 = 'S4 - S6'
    S1_S6 = 'S1 - S6'
    NAO_SELECIONADO = '0'

    SEXTANTE_CHOICES = (
        (NAO_SELECIONADO, 'Selecione um sextante'),
        (S1, 'S1'),
        (S2, 'S2'),
        (S3, 'S3'),
        (S4, 'S4'),
        (S5, 'S5'),
        (S6, 'S6'),
        (S1_S3, 'S1 - S3'),
        (S4_S6, 'S4 - S6'),
        (S1_S6, 'S1 - S6'),
    )

    SANGRAMENTO = '1'
    CALCULO = '2'
    RECESSAO = '3'
    BIOFILME_BACTERIANO = '4'

    OCORRENCIA_CHOICES = ((BIOFILME_BACTERIANO, 'Biofilme Bacteriano'), (CALCULO, 'Cálculo'), (RECESSAO, 'Recessão'), (SANGRAMENTO, 'Sangramento'))

    sextante = models.CharField('Sextante', max_length=100)
    ocorrencia = models.CharField('Ocorrência', max_length=2, choices=OCORRENCIA_CHOICES)
    resolvido = models.BooleanField('Resolvido', default=False)

    class Meta:
        verbose_name = 'Exame Periodontal'
        verbose_name_plural = 'Exames Periodontais'
        unique_together = ('atendimento', 'sextante', 'ocorrencia')

    def get_ocorrencia(self):
        if self.ocorrencia == ExamePeriodontal.SANGRAMENTO:
            return 'Sangramento'
        elif self.ocorrencia == ExamePeriodontal.CALCULO:
            return 'Cálculo'
        elif self.ocorrencia == ExamePeriodontal.RECESSAO:
            return 'Recessão'
        elif self.ocorrencia == ExamePeriodontal.BIOFILME_BACTERIANO:
            return 'Biofilme Bacteriano'


class ExameEstomatologico(ModelSaudeFicha):
    labios = models.CharField('Alteração nos lábios', max_length=500, null=True, blank=True)
    lingua = models.CharField('Alteração na língua', max_length=500, null=True, blank=True)
    gengiva = models.CharField('Alteração na gengiva', max_length=500, null=True, blank=True)
    assoalho = models.CharField('Alteração no assoalho', max_length=500, null=True, blank=True)
    mucosa_jugal = models.CharField('Alteração na mucosa jugal', max_length=500, null=True, blank=True)
    palato_duro = models.CharField('Alteração no palato duro', max_length=500, null=True, blank=True)
    palato_mole = models.CharField('Alteração no palato mole', max_length=500, null=True, blank=True)
    rebordo = models.CharField('Alteração no rebordo', max_length=500, null=True, blank=True)
    cadeia_ganglionar = models.CharField('Alteração na cadeia ganglionar', max_length=500, null=True, blank=True)
    tonsilas_palatinas = models.CharField('Alteração nas tonsilas palatinas', max_length=500, null=True, blank=True)
    atm = models.CharField('Alteração na ATM', max_length=500, null=True, blank=True)
    oclusao = models.CharField('Alteração na Oclusão', max_length=500, null=True, blank=True)

    class Meta:
        verbose_name = 'Exame Estomatológico'
        verbose_name_plural = 'Exames Estomatológicos'

    def get_alteracoes(self):
        lista = list()
        if self.labios:
            lista.append(self.labios)
        if self.lingua:
            lista.append(self.lingua)
        if self.gengiva:
            lista.append(self.gengiva)
        if self.assoalho:
            lista.append(self.assoalho)
        if self.mucosa_jugal:
            lista.append(self.mucosa_jugal)
        if self.palato_duro:
            lista.append(self.palato_duro)
        if self.palato_mole:
            lista.append(self.palato_mole)
        if self.rebordo:
            lista.append(self.rebordo)
        if self.cadeia_ganglionar:
            lista.append(self.cadeia_ganglionar)
        if self.tonsilas_palatinas:
            lista.append(self.tonsilas_palatinas)
        if self.atm:
            lista.append(self.atm)
        if self.oclusao:
            lista.append(self.oclusao)

        return lista


class PlanoTratamento(ModelSaudeFicha):
    NAO_SELECIONADO = '0'
    DENTES_CHOICE = (
        (NAO_SELECIONADO, 'Selecione um dente'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('21', '21'),
        ('22', '22'),
        ('23', '23'),
        ('24', '24'),
        ('25', '25'),
        ('26', '26'),
        ('27', '27'),
        ('28', '28'),
        ('31', '31'),
        ('32', '32'),
        ('33', '33'),
        ('34', '34'),
        ('35', '35'),
        ('36', '36'),
        ('37', '37'),
        ('38', '38'),
        ('41', '41'),
        ('42', '42'),
        ('43', '43'),
        ('44', '44'),
        ('45', '45'),
        ('46', '46'),
        ('47', '47'),
        ('48', '48'),
        ('51', '51'),
        ('52', '52'),
        ('53', '53'),
        ('54', '54'),
        ('55', '55'),
        ('61', '61'),
        ('62', '62'),
        ('63', '63'),
        ('64', '64'),
        ('65', '65'),
        ('71', '71'),
        ('72', '72'),
        ('73', '73'),
        ('74', '74'),
        ('75', '75'),
        ('81', '81'),
        ('82', '82'),
        ('83', '83'),
        ('84', '84'),
        ('85', '85'),
    )
    TODAS_FACES = 'Todas as Faces'
    VESTIBULAR = 'Vestibular'
    PALATAL = 'Lingual'
    MESSIAL = 'Mesial'
    DISTAL = 'Distal'
    OCLUSAL = 'Oclusal/Incisal'
    CERVICAL = 'Cervical'
    RAIZ = 'Raiz'

    FACES_CHOICES = (
        (TODAS_FACES, 'Todas as Faces'),
        (VESTIBULAR, 'Vestibular'),
        (PALATAL, 'Palatal/Lingual'),
        (MESSIAL, 'Mesial'),
        (DISTAL, 'Distal'),
        (OCLUSAL, 'Oclusal/Incisal'),
        (CERVICAL, 'Cervical'),
        (RAIZ, 'Raiz'),
    )

    ARCADA_INFANTIL = ('51', '52', '53', '54', '55', '61', '62', '63', '64', '65', '71', '72', '73', '74', '75', '81', '82', '83', '84', '85')

    dente = models.CharField('Dente', null=True, blank=True, max_length=10)
    face = models.CharField('Face', null=True, blank=True, max_length=100)
    sextante = models.CharField('Sextante', null=True, blank=True, max_length=20)
    situacao_clinica = models.ForeignKeyPlus(SituacaoClinica, null=True, on_delete=models.CASCADE)
    procedimento = models.ForeignKeyPlus(ProcedimentoOdontologia, null=True, on_delete=models.CASCADE)
    realizado = models.BooleanField('Realizado', default=False)
    ordem = models.IntegerField(verbose_name='Ordem', null=True, default=1)

    class Meta:
        verbose_name = 'Plano de Tratamento'
        verbose_name_plural = 'Planos de Tratamento'

    def get_face(self):
        lista = list()
        if self.face:
            if '_T_' in self.face:
                lista.append(PlanoTratamento.TODAS_FACES)
            if '_V_' in self.face:
                lista.append(PlanoTratamento.VESTIBULAR)
            if '_P_' in self.face:
                lista.append(PlanoTratamento.PALATAL)
            if '_M_' in self.face:
                lista.append(PlanoTratamento.MESSIAL)
            if '_D_' in self.face:
                lista.append(PlanoTratamento.DISTAL)
            if '_O_' in self.face:
                if self.dente in ['11', '12', '13', '21', '22', '23', '31', '32', '33', '41', '42', '43']:
                    lista.append('Incisal')
                else:
                    lista.append('Oclusal')
            if '_C_' in self.face:
                lista.append(PlanoTratamento.CERVICAL)
            if '_R_' in self.face:
                lista.append(PlanoTratamento.RAIZ)
        return lista

    def get_ordem(self):
        if PlanoTratamento.objects.filter(atendimento=self.atendimento).exists():
            ordem = PlanoTratamento.objects.filter(atendimento=self.atendimento).order_by('-ordem')[0].ordem
            return ordem + 1
        return 1

    def pode_subir(self):
        return PlanoTratamento.objects.filter(atendimento=self.atendimento, ordem__lt=self.ordem).exists()

    def pode_descer(self):
        return PlanoTratamento.objects.filter(atendimento=self.atendimento, ordem__gt=self.ordem).exists()

    def __str__(self):
        return f'Plano de Tratamento {self.pk}'


class ProcedimentoIndicado(models.ModelPlus):
    situacao_clinica = models.ForeignKeyPlus(SituacaoClinica, on_delete=models.CASCADE)
    procedimento = models.ForeignKeyPlus(ProcedimentoOdontologia, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Procedimento Indicado'
        verbose_name_plural = 'Procedimentos Indicados'


class ResultadoProcedimento(models.ModelPlus):
    situacao_clinica = models.ForeignKeyPlus(SituacaoClinica, on_delete=models.CASCADE)
    procedimento = models.ForeignKeyPlus(ProcedimentoOdontologia, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Resultado do Procedimento'
        verbose_name_plural = 'Resultados do Procedimento'


class InformacaoAdicional(ModelSaudeFicha):
    informacao = models.CharField('Informação Adicional', max_length=500)

    class Meta:
        verbose_name = 'Informação Adicional'
        verbose_name_plural = 'Informações Adicionais'

    def __str__(self):
        return self.informacao


class AnotacaoInterdisciplinar(models.ModelPlus):
    prontuario = ForeignKeyPlus(Prontuario, verbose_name='Prontuário')
    profissional = ForeignKeyPlus(Servidor, verbose_name='Profissional')
    data = models.DateTimeField('Data')
    anotacao = models.CharField('Anotação', max_length=5000)

    class Meta:
        verbose_name = 'Anotação Interdisciplinar'
        verbose_name_plural = 'Anotações Interdisciplinares'

    def __str__(self):
        return self.anotacao


class TipoAtividadeGrupo(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=500)

    class Meta:
        verbose_name = 'Tipo de Atividade em Grupo'
        verbose_name_plural = 'Tipos de Atividade em Grupo'

    def __str__(self):
        return self.descricao


class AtividadeGrupo(models.ModelPlus):
    MATUTINO = 'Matutino'
    VESPERTINO = 'Vespertino'
    DIURNO = 'Diurno'
    NOTURNO = 'Noturno'

    TURNO_CHOICES = ((MATUTINO, 'Matutino'), (VESPERTINO, 'Vespertino'), (DIURNO, 'Diurno'), (NOTURNO, 'Noturno'))
    nome_evento = models.CharField('Nome do Evento/Atividade', max_length=500, null=True, blank=True)
    uo = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', on_delete=models.CASCADE)
    tipo = models.ForeignKeyPlus(TipoAtividadeGrupo, verbose_name='Tipo', on_delete=models.CASCADE, null=True)
    tema = models.CharField('Tema', max_length=500, null=True)
    motivo = models.CharField('Motivo', max_length=1000, null=True, blank=True)
    detalhamento = models.CharField('Detalhamento', max_length=5000, null=True, blank=True)
    publico_alvo = models.CharField('Público-Alvo', max_length=500, null=True, blank=True)
    num_participantes = models.IntegerField(verbose_name='Número de Participantes', null=True)
    data_inicio = models.DateTimeField(verbose_name='Data/Hora de Início')
    data_termino = models.DateTimeField(verbose_name='Data/Hora de Término')
    turno = models.CharField('Turno', max_length=15, choices=TURNO_CHOICES, null=True, blank=True)
    solicitante = models.CharField('Solicitante', max_length=500, null=True, blank=True)
    vinculos_responsaveis = models.ManyToManyField('comum.Vinculo', related_name='vinculos_responsaveis_atividades_grupo')
    anexo = models.FileFieldPlus(verbose_name='Anexo', max_length=255, upload_to='upload/saude/atividades_grupo/', null=True, blank=True)
    eh_sistemica = models.BooleanField('Atividade Sistêmica', default=False)
    cancelada = models.BooleanField('Cancelada', default=False)
    meta = models.ForeignKeyPlus('saude.MetaAcaoEducativa', null=True, on_delete=models.CASCADE)
    recurso_necessario = models.CharFieldPlus('Recurso Necessário', null=True, max_length=5000)
    cadastrado_por = models.CurrentUserField(verbose_name='Cadastrado Por', null=True)

    class Meta:
        verbose_name = 'Atividade em Grupo'
        verbose_name_plural = 'Atividades em Grupo'

    def __str__(self):
        return self.nome_evento


class CategoriaExameLaboratorial(models.ModelPlus):
    nome = models.CharField('Nome', max_length=200)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Categoria de Exame Laboratorial'
        verbose_name_plural = 'Categorias de Exames Laboratoriais'

    def __str__(self):
        return self.nome


class TipoExameLaboratorial(models.ModelPlus):
    categoria = models.ForeignKeyPlus(CategoriaExameLaboratorial, on_delete=models.CASCADE)
    nome = models.CharField('Nome', max_length=200)
    unidade = models.CharField('Unidade de Medida', max_length=200)
    valor_referencia = RichTextField('Valores de Referência')
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Exame Laboratorial'
        verbose_name_plural = 'Tipos de Exames Laboratoriais'

    def __str__(self):
        return self.nome


class ExameLaboratorial(models.ModelPlus):
    prontuario = ForeignKeyPlus(Prontuario, verbose_name='Prontuário')
    profissional = ForeignKeyPlus(Servidor, verbose_name='Profissional', null=True, blank=True)
    categoria = ForeignKeyPlus(CategoriaExameLaboratorial, verbose_name='Categoria', null=True, blank=True)
    data_realizado = models.DateField('Data de Realização', null=True, blank=True)
    data_cadastro = models.DateField('Data de Cadastro', null=True, blank=True)
    observacao = models.CharField('Observação', max_length=1000, null=True, blank=True)
    sigiloso = models.BooleanField('Sigiloso', default=False)

    class Meta:
        verbose_name = 'Exame Laboratorial'
        verbose_name_plural = 'Exames Laboratoriais'


class ValorExameLaboratorial(models.ModelPlus):
    exame = models.ForeignKeyPlus(ExameLaboratorial, on_delete=models.CASCADE)
    tipo = models.ForeignKeyPlus(TipoExameLaboratorial, on_delete=models.CASCADE)
    valor = models.CharField('Valor', max_length=100)

    class Meta:
        verbose_name = 'Valor do Exame Complementar'
        verbose_name_plural = 'Valores do Exame Complementar'


class ExameImagem(models.ModelPlus):
    prontuario = ForeignKeyPlus(Prontuario, verbose_name='Prontuário')
    profissional = ForeignKeyPlus(Servidor, verbose_name='Profissional', null=True, blank=True)
    nome = models.CharFieldPlus('Nome', max_length=200)
    data_realizado = models.DateField('Data de Realização', null=True, blank=True)
    data_cadastro = models.DateField('Data de Cadastro', null=True, blank=True)
    resultado = models.CharField('Resultado', max_length=1000, null=True, blank=True)
    sigiloso = models.BooleanField('Sigiloso', default=False)

    class Meta:
        verbose_name = 'Exame de Imagem'
        verbose_name_plural = 'Exames de Imagem'


class QueixaPsicologica(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=255, null=False)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Queixa'
        verbose_name_plural = 'Queixas'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class AnamnesePsicologia(ModelSaudeFicha):
    prontuario = models.ForeignKeyPlus(Prontuario, on_delete=models.CASCADE)
    historico_queixa = models.TextField('Histórico da Queixa', null=True, blank=True)
    dimensao_familiar = models.TextField('Dimensão Familiar', null=True, blank=True)
    dimensao_escolar = models.TextField('Dimensão Escolar', null=True, blank=True)
    dimensao_emocional = models.TextField('Dimensão Emocional', null=True, blank=True)
    dimensao_projetos_vida = models.TextField('Dimensão dos Projetos de Vida', null=True, blank=True)
    dimensao_social = models.TextField('Dimensão Social', null=True, blank=True)

    class Meta:
        verbose_name = 'Anamnese Psicológica'
        verbose_name_plural = 'Anamneses Psicológicas'


class MotivoChegadaPsicologia(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=100)

    class Meta:
        verbose_name = 'Motivo da Chegada'
        verbose_name_plural = 'Motivos da Chegada'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class AtendimentoPsicologia(ModelSaudeFicha):
    motivo_chegada = models.ForeignKeyPlus(
        MotivoChegadaPsicologia, verbose_name='Motivo da Chegada', related_name='motivo_chegada_psicologia', on_delete=models.CASCADE, null=True, blank=True
    )
    descricao_encaminhamento_externo = models.CharField(verbose_name='Descrição do Encaminhamento Externo', max_length=255, null=True, blank=True)
    queixa_principal = models.ManyToManyField(QueixaPsicologica, verbose_name='Queixa Principal', related_name='queixa_principal')
    queixa_identificada = models.ManyToManyField(QueixaPsicologica, verbose_name='Queixa Identificada', related_name='queixa_identificada')
    descricao_queixa_outros = models.CharField(verbose_name='Queixa Principal - Outros', max_length=255, null=True, blank=True)
    descricao_queixa_identificada_outros = models.CharField(verbose_name='Queixa Identificada - Outros', max_length=255, null=True, blank=True)
    intervencao = models.TextField('Intervenção / Encaminhamento', null=True, blank=True)
    data_atendimento = models.DateTimeFieldPlus('Data/Hora do Atendimento', null=True, blank=True)

    class Meta:
        verbose_name = 'Atendimento Psicológico'
        verbose_name_plural = 'Atendimentos Psicológicos'


class ProcedimentoMultidisciplinar(models.ModelPlus):
    denominacao = models.CharField('Denominação', max_length=255)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Procedimento Multidisciplinar'
        verbose_name_plural = 'Procedimentos Multidisciplinares'

    def __str__(self):
        return self.denominacao


class AtendimentoMultidisciplinar(ModelSaudeFicha):
    procedimento = models.ManyToManyFieldPlus(ProcedimentoMultidisciplinar, verbose_name='Procedimentos')
    observacao = models.TextField('Observação', null=True, blank=True)

    class Meta:
        verbose_name = 'Atendimento Multidisciplinar'
        verbose_name_plural = 'Atendimentos Multidisciplinares'

    def __str__(self):
        linha = []
        for p in self.procedimento.all():
            linha.append(p.denominacao)
        return ', '.join(linha)


class MotivoAtendimentoNutricao(models.Model):
    descricao = models.CharField('Descrição', max_length=200)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Motivo do Atendimento'
        verbose_name_plural = 'Motivos do Atendimento'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class AvaliacaoGastroIntestinal(models.Model):
    descricao = models.CharField('Descrição', max_length=200)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Avaliação Gastrointestinal'
        verbose_name_plural = 'Avaliações Gastrointestinais'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class RestricaoAlimentar(models.Model):
    descricao = models.CharField('Descrição', max_length=200)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Restrição Alimentar'
        verbose_name_plural = 'Restrições Alimentares'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class DiagnosticoNutricional(models.Model):
    descricao = models.CharField('Descrição', max_length=200)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Diagnóstico Nutricional'
        verbose_name_plural = 'Diagnósticos Nutricionais'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class OrientacaoNutricional(models.Model):
    titulo = models.CharField('Título', max_length=200)
    descricao = RichTextField('Descrição')
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Orientação Nutricional'
        verbose_name_plural = 'Orientações Nutricionais'
        ordering = ['descricao']

    def __str__(self):
        return self.titulo


class ReceitaNutricional(models.Model):
    titulo = models.CharField('Título', max_length=200)
    descricao = RichTextField('Descrição')
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Receita'
        verbose_name_plural = 'Receitas'
        ordering = ['descricao']

    def __str__(self):
        return self.titulo


class FrequenciaPraticaAlimentar(models.Model):
    descricao = models.CharFieldPlus('Descrição', max_length=500)
    valor_recomendado = models.IntegerField('Valor Recomendado')
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Alimento/Bebida para Frequência de Prática Alimentar'
        verbose_name_plural = 'Alimentos/Bebidas para Frequência de Prática Alimentar'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class AtendimentoNutricao(ModelSaudeFicha):
    LEVE = 'Leve'
    MODERADA = 'Moderada'
    PESADA = 'Pesada'
    CATEGORIA_TRABALHO_CHOICES = ((LEVE, LEVE), (MODERADA, MODERADA), (PESADA, PESADA))
    motivo = models.ManyToManyField(MotivoAtendimentoNutricao, verbose_name='Motivo do Atendimento', related_name='motivo_atendimento_nutricao')
    observacoes = models.CharFieldPlus('Observações', max_length=5000, null=True, blank=True)
    avaliacao_gastrointestinal = models.ManyToManyField(AvaliacaoGastroIntestinal, verbose_name='Avaliação Gastrointestinal', related_name='avaliacao_gastrointestinal')
    restricao_alimentar = models.ManyToManyField(RestricaoAlimentar, verbose_name='Restrição Alimentar', related_name='restricao_alimentar')
    diagnostico_nutricional = models.ManyToManyField(DiagnosticoNutricional, verbose_name='Diagnóstico Nutricional', related_name='diagnostico_nutricional')
    diagnostico_nutricional_obs = models.CharFieldPlus('Observações', max_length=5000, null=True, blank=True)

    apetite = models.CharFieldPlus('Apetite', max_length=1000, null=True, blank=True)
    aversoes = models.CharFieldPlus('Aversões', max_length=1000, null=True, blank=True)
    preferencias = models.CharFieldPlus('Preferências', max_length=1000, null=True, blank=True)
    consumo_liquidos = models.CharFieldPlus('Consumo de Água/Líquidos', max_length=1000, null=True, blank=True)
    categoria_trabalho = models.CharFieldPlus('Categoria de Trabalho', max_length=30, choices=CATEGORIA_TRABALHO_CHOICES, null=True, blank=True)
    conduta = RichTextField('Conduta', null=True)

    class Meta:
        verbose_name = 'Atendimento Nutricional'
        verbose_name_plural = 'Atendimentos Nutricionais'

    def tem_dados_gerais_alimentacao(self):
        return self.apetite or self.aversoes or self.preferencias or self.consumo_liquidos

    def get_tmb(self):
        idade = 0
        try:
            idade = int(self.atendimento.prontuario.vinculo.pessoa.pessoafisica.idade)
        except Exception:
            pass
        antropometria = Antropometria.objects.filter(atendimento=self.atendimento)
        tmb = Decimal()
        if antropometria.exists():
            antropometria = antropometria[0]
            if self.atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo == 'M':
                tmb = (
                    Decimal(88.36).quantize(Decimal(10) ** -2)
                    + (Decimal(13.4).quantize(Decimal(10) ** -2) * antropometria.peso)
                    + (Decimal(4.8).quantize(Decimal(10) ** -2) * antropometria.estatura)
                    - (Decimal(5.7).quantize(Decimal(10) ** -2) * idade)
                )
                if self.categoria_trabalho == AtendimentoNutricao.LEVE:
                    tmb = tmb * Decimal(1.55).quantize(Decimal(10) ** -2)
                elif self.categoria_trabalho == AtendimentoNutricao.MODERADA:
                    tmb = tmb * Decimal(1.78).quantize(Decimal(10) ** -2)
                elif self.categoria_trabalho == AtendimentoNutricao.PESADA:
                    tmb = tmb * Decimal(2.10).quantize(Decimal(10) ** -2)

            elif self.atendimento.prontuario.vinculo.pessoa.pessoafisica.sexo == 'F':
                tmb = (
                    Decimal(447.6).quantize(Decimal(10) ** -2)
                    + (Decimal(9.2).quantize(Decimal(10) ** -2) * antropometria.peso)
                    + (Decimal(3.1).quantize(Decimal(10) ** -2) * antropometria.estatura)
                    - (Decimal(4.3).quantize(Decimal(10) ** -2) * idade)
                )
                if self.categoria_trabalho == AtendimentoNutricao.LEVE:
                    tmb = tmb * Decimal(1.56).quantize(Decimal(10) ** -2)
                elif self.categoria_trabalho == AtendimentoNutricao.MODERADA:
                    tmb = tmb * Decimal(1.64).quantize(Decimal(10) ** -2)
                elif self.categoria_trabalho == AtendimentoNutricao.PESADA:
                    tmb = tmb * Decimal(1.82).quantize(Decimal(10) ** -2)

        return tmb


class PlanoAlimentar(ModelSaudeFicha):
    orientacao_nutricional = models.ManyToManyField(OrientacaoNutricional, verbose_name='Orientação Nutricional', related_name='diagnostico_nutricional')
    cardapio = RichTextField('Cardápio', null=True, blank=True)
    receita_nutricional = models.ManyToManyField(ReceitaNutricional, verbose_name='Receita Nutricional', related_name='diagnostico_nutricional')
    sugestoes_leitura = RichTextField('Sugestões de Leituras e Links', null=True, blank=True)
    plano_alimentar_liberado = models.BooleanField('Plano Alimentar Liberado', default=False)

    class Meta:
        verbose_name = 'Plano Alimentar'
        verbose_name_plural = 'Planos Alimentares'

    def __str__(self):
        return 'Plano Alimentar'


class ConsumoNutricao(ModelSaudeFicha):
    refeicao = models.CharFieldPlus('Refeição', max_length=100, null=True, blank=True)
    horario_consumo_alimentacao = models.TimeFieldPlus('Horário de Consumo', null=True, blank=True)
    local_consumo_alimentacao = models.CharFieldPlus('Local de Consumo', max_length=1000, null=True, blank=True)
    alimentos_consumidos = models.CharFieldPlus('Alimentos Consumidos / Medidas Caseiras', max_length=1000, null=True, blank=True)

    class Meta:
        verbose_name = 'Informação sobre o Consumo'
        verbose_name_plural = 'Informações sobre o Consumo'

    def __str__(self):
        return self.refeicao

    def get_descricao_alimentos(self):
        if self.alimentos_consumidos:
            todos_alimentos = self.alimentos_consumidos.split(';')[:-1]
            texto = '''<ul>'''
            for item in todos_alimentos:
                texto += f'<li>{item}</li>'
            texto += '''</ul>'''
            return texto
        return '-'


class TipoConsultaOdontologia(models.ModelPlus):
    CONCLUIDO = 2
    descricao = models.CharFieldPlus('Descrição', max_length=200)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Consulta de Odontologia'
        verbose_name_plural = 'Tipos de Consulta de Odontologia'

    def __str__(self):
        return self.descricao


class FrequenciaAlimentarNutricao(ModelSaudeFicha):
    frequencia = models.ForeignKeyPlus(FrequenciaPraticaAlimentar, related_name='frequencia_pratica_alimentar', on_delete=models.CASCADE)
    valor = models.CharFieldPlus('Valor Informado')

    class Meta:
        verbose_name = 'Frequência Alimentar do Atendimento Nutricional'
        verbose_name_plural = 'Frequências Alimentares dos Atendimentos Nutricionais'

    def __str__(self):
        return self.valor


class PerguntaMarcadorNutricao(models.Model):
    UNICA_ESCOLHA = 'Única Escolha'
    MULTIPLA_ESCOLHA = 'Múltipla Escolha'
    TIPO_RESPOSTA_CHOICES = ((UNICA_ESCOLHA, UNICA_ESCOLHA), (MULTIPLA_ESCOLHA, MULTIPLA_ESCOLHA))
    pergunta = models.CharFieldPlus('Pergunta', max_length=2000)
    tipo_resposta = models.CharFieldPlus('Tipo de Resposta', max_length=100, choices=TIPO_RESPOSTA_CHOICES)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Pergunta de Marcador Alimentar'
        verbose_name_plural = 'Perguntas de Marcador Alimentar'

    def __str__(self):
        return self.pergunta


class OpcaoRespostaMarcadorNutricao(models.Model):
    pergunta = models.ForeignKeyPlus(PerguntaMarcadorNutricao, related_name='pergunta_marcador', verbose_name='Pergunta', on_delete=models.CASCADE)
    valor = models.CharFieldPlus('Opção de Resposta', max_length=200)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Opção de Resposta de Marcador Alimentar'
        verbose_name_plural = 'Opções de Resposta de Marcador Alimentar'

    def __str__(self):
        return self.valor


class RespostaMarcadorNutricao(ModelSaudeFicha):
    pergunta = models.ForeignKeyPlus(PerguntaMarcadorNutricao, related_name='resposta_pergunta_marcador', verbose_name='Pergunta', on_delete=models.CASCADE)
    resposta = models.ForeignKeyPlus(OpcaoRespostaMarcadorNutricao, related_name='resposta_escolhida', verbose_name='Resposta', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Resposta de Marcador Alimentar'
        verbose_name_plural = 'Respostas de Marcador Alimentar'

    def __str__(self):
        return self.resposta


class AnexoPsicologia(models.ModelPlus):
    atendimento = models.ForeignKeyPlus(Atendimento, on_delete=models.CASCADE)
    descricao = models.CharFieldPlus('Descrição', max_length=2000)
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado Em', auto_now_add=True)
    cadastrado_por_vinculo = models.ForeignKeyPlus('comum.Vinculo', on_delete=models.CASCADE, null=True)
    arquivo = models.FileFieldPlus('Arquivo', upload_to='upload/saude/psicologia/anexos/')

    class Meta:
        verbose_name = 'Anexo de Psicologia'
        verbose_name_plural = 'Anexos de Psicologia'

    def __str__(self):
        return self.descricao


class HorarioAtendimento(models.ModelPlus):
    data = models.DateFieldPlus('Data do Atendimento')
    hora_inicio = models.TimeFieldPlus('Hora de Início')
    hora_termino = models.TimeFieldPlus('Hora de Término')
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado Em')
    cadastrado_por_vinculo = models.ForeignKeyPlus('comum.Vinculo', on_delete=models.CASCADE, null=True)
    especialidade = models.CharField('Especialidade', max_length=100, choices=Especialidades.ESPECIALIDADES_CHOICES)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, on_delete=models.CASCADE)
    disponivel = models.BooleanField('Disponível', default=True)
    cancelado = models.BooleanField('Cancelado', default=False)
    motivo_cancelamento = models.CharField('Justificativa', max_length=2000, null=True, blank=True)
    vinculo_paciente = models.ForeignKeyPlus('comum.Vinculo', on_delete=models.CASCADE, null=True, related_name='vinculo_paciente_agendamento')

    class Meta:
        ordering = ['-data', 'hora_inicio', 'hora_termino']
        verbose_name = 'Horário de Atendimento'
        verbose_name_plural = 'Horários de Atendimentos'
        permissions = (("pode_ver_agenda_atendimento", "Pode ver agenda de atendimentos"),)

    def __str__(self):
        return f'{self.especialidade} - {self.data} ({self.hora_inicio} - {self.hora_termino})'

    def dentro_prazo_agendamento(self):
        limite = self.data - datetime.timedelta(1)
        data_limite = datetime.datetime(limite.year, limite.month, limite.day, self.hora_inicio.hour, self.hora_inicio.minute)
        return datetime.datetime.today().now() <= data_limite

    def pode_cancelar(self, user):
        if not self.cancelado:
            vinculo = user.get_vinculo()
            if (vinculo == self.cadastrado_por_vinculo) or (
                get_uo(user) == self.campus and self.especialidade == Especialidades.ODONTOLOGO and user.groups.filter(name='Atendente').exists()
            ):
                return True
            elif vinculo == self.vinculo_paciente and self.dentro_prazo_agendamento():
                return True
            return False
        else:
            return False

    def pode_bloquear_aluno(self, user):
        especialidade = Especialidades(user)
        pode_cadastrar_horario = Especialidades.eh_profissional_saude(especialidade)
        return pode_cadastrar_horario and self.vinculo_paciente and self.cadastrado_por_vinculo == user.get_vinculo()

    def aluno_tem_aula(self, user):
        alunos = Aluno.objects.filter(vinculos=user.get_vinculo()).order_by('-id')
        if alunos.exists():
            aluno = alunos[0]
            if aluno.em_horario_de_aula(self.data, str(self.hora_inicio)[:5]) or aluno.em_horario_de_aula(self.data, str(self.hora_termino)[:5]):
                return True
        return False

    def paciente_bloqueado(self):
        return self.vinculo_paciente and BloqueioAtendimentoSaude.objects.filter(vinculo_paciente=self.vinculo_paciente, data__gte=datetime.datetime.today().date())

    def pode_agendar(self, user):
        if self.especialidade == Especialidades.AVALIACAO_BIOMEDICA:
            return self.campus == get_uo(user)
        else:
            return self.cadastrado_por_vinculo == user.get_vinculo()


class BloqueioAtendimentoSaude(models.ModelPlus):
    vinculo_paciente = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Paciente', on_delete=models.CASCADE, related_name='vinculo_paciente_bloqueio_agendamento', null=True)
    vinculo_profissional = models.ForeignKeyPlus(
        'comum.Vinculo', verbose_name='Profissional', on_delete=models.CASCADE, related_name='vinculo_profissional_bloqueio_agendamento', null=True
    )
    data = models.DateField('Bloqueado Até')

    class Meta:
        verbose_name = 'Paciente Bloqueado'
        verbose_name_plural = 'Pacientes Bloqueados'

    def __unicode__(self):
        return f'{self.vinculo_paciente} - Bloqueado até: {self.data}'


class AnoReferenciaAcaoEducativa(models.ModelPlus):
    ano = models.CharFieldPlus('Ano', max_length=200)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Ano de Referência'
        verbose_name_plural = 'Anos de Referências'

    def __str__(self):
        return self.ano


class ObjetivoAcaoEducativa(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', max_length=10000)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Objetivo da Ação Educativa'
        verbose_name_plural = 'Objetivos da Ação Educativa'

    def __str__(self):
        return self.descricao


class MetaAcaoEducativa(models.ModelPlus):
    PERCENTUAL = 'Percentual'
    NUM_ACOES = 'Número de Ações'
    INDICADOR_CHOICES = ((NUM_ACOES, NUM_ACOES), (PERCENTUAL, PERCENTUAL))
    ano_referencia = models.ForeignKeyPlus(AnoReferenciaAcaoEducativa, on_delete=models.CASCADE, verbose_name='Ano de Referência')
    objetivos = models.ManyToManyFieldPlus(ObjetivoAcaoEducativa, verbose_name='Objetivo')
    indicador = models.CharFieldPlus('Tipo de Indicador', max_length=50, choices=INDICADOR_CHOICES)
    valor = models.CharFieldPlus('Valor', max_length=20)
    descricao = models.CharFieldPlus('Descrição', max_length=10000, null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        ordering = ['-ano_referencia__ano']
        verbose_name = 'Meta da Ação Educativa'
        verbose_name_plural = 'Metas da Ação Educativa'

    def __str__(self):
        return f'{self.ano_referencia} - {self.descricao}'

    def pode_adicionar_meta(self):
        return self.ativo and self.ano_referencia.ano and (int(self.ano_referencia.ano) >= datetime.datetime.now().year)


class RegistroAdministrativo(models.ModelPlus):
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, on_delete=models.CASCADE)
    vinculo_profissional = models.ForeignKeyPlus('comum.Vinculo', on_delete=models.CASCADE, null=True)

    data = models.DateField('Data')
    descricao = models.CharFieldPlus('Descrição', max_length=10000)

    class Meta:
        verbose_name = 'Registro Administrativo'
        verbose_name_plural = 'Registros Administrativos'

    def __str__(self):
        return self.descricao


class DocumentoProntuario(models.ModelPlus):
    DECLARACAO_COMPARECIMENTO = 'Declaração de Comparecimento'
    ATESTADO = 'Atestado'
    RECEITUARIO = 'Receituário'
    TIPO_DOCUMENTO_CHOICES = ((0, ATESTADO), (1, DECLARACAO_COMPARECIMENTO), (2, RECEITUARIO))

    prontuario = models.ForeignKeyPlus(Prontuario, on_delete=models.CASCADE)
    tipo = models.CharFieldPlus('Tipo', choices=TIPO_DOCUMENTO_CHOICES)
    data = models.DateFieldPlus('Data')
    texto = RichTextField('Texto')
    cadastrado_por_vinculo = models.ForeignKeyPlus('comum.Vinculo', on_delete=models.CASCADE, null=True)
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado Em', auto_now_add=True)

    class Meta:
        verbose_name = 'Documento do Prontuário'
        verbose_name_plural = 'Documentos do Prontuário'

    def __str__(self):
        return f'{self.tipo} - {self.prontuario.vinculo}'


class AtendimentoFisioterapia(ModelSaudeFicha):
    anamnese = models.TextField('Anamnese', null=True, blank=True)
    conduta = models.TextField('Conduta de Fisioterapia', null=True, blank=True)
    hipotese = models.TextField('Hipótese Diagnóstica', null=True, blank=True)
    descricao_evolucao = models.TextField('Descrição da Evolução', null=True, blank=True)
    data_retorno = models.DateFieldPlus('Data do Retorno', null=True, blank=True)

    class Meta:
        verbose_name = 'Atendimento de Fisioterapia'
        verbose_name_plural = 'Atendimentos de Fisioterapia'


class IntervencaoFisioterapia(ModelSaudeFicha):
    descricao = models.TextField('Descrição', null=True, blank=True)
    conduta_medica = ForeignKeyPlus(CondutaMedica, verbose_name='Conduta Médica', null=True)

    class Meta:
        verbose_name = 'Intervenção de Fisioterapia'
        verbose_name_plural = 'Intervenções de Fisioterapia'


class HistoricoCartaoVacinal(models.ModelPlus):
    prontuario = models.ForeignKeyPlus(Prontuario, on_delete=models.CASCADE)
    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Vínculo', related_name='vinculo_cadastro_cartao_vacinal')
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado Em', null=True)

    class Meta:
        verbose_name = 'Histórico de Cartão Vacinal'
        verbose_name_plural = 'Históricos de Cartão Vacinal'


class PassaporteVacinalCovid(models.ModelPlus):
    AGUARDANDO_VALIDACAO = 'Aguardando validação'
    DEFERIDA = 'Deferida'
    INDEFERIDA = 'Indeferida'
    AGUARDANDO_AUTODECLARACAO = 'Aguardando autodeclaração'
    SITUACAO_CHOICES = (
        (AGUARDANDO_VALIDACAO, AGUARDANDO_VALIDACAO),
        (AGUARDANDO_AUTODECLARACAO, AGUARDANDO_AUTODECLARACAO),
        (DEFERIDA, DEFERIDA),
        (INDEFERIDA, INDEFERIDA),
    )
    VALIDO = 'Válido'
    INVALIDO = 'Inválido'
    PENDENTE = 'Pendente'
    SITUACAO_PASSAPORTE_CHOICES = (
        (VALIDO, VALIDO),
        (INVALIDO, INVALIDO),
        (PENDENTE, PENDENTE),
    )
    uo = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', on_delete=models.CASCADE)
    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Vínculo', related_name='vinculo_autodeclaracao_covid')
    cpf = models.CharFieldPlus('CPF', null=True, blank=True, max_length=11)
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado Em', auto_now_add=True)
    atualizado_em = models.DateTimeFieldPlus('Atualizado Em', null=True)
    recebeu_alguma_dose = models.BooleanField('Você já tomou alguma dose de vacina contra a COVID?', null=True)
    data_primeira_dose = models.DateFieldPlus('Data da 1ª Dose', null=True, blank=True)
    data_segunda_dose = models.DateFieldPlus('Data da 2ª Dose', null=True, blank=True)
    data_terceira_dose = models.DateFieldPlus('Data da Dose de Reforço', null=True, blank=True)
    esquema_completo = models.BooleanField('Esquema vacinal completo', default=False)
    possui_atestado_medico = models.BooleanField('Você possui atestado/laudo médico ou técnico indicando contraindicação para tomar a vacina?', null=True, blank=True)
    atestado_medico = models.FileFieldPlus('Atestado/Laudo', null=True, upload_to='upload/saude/prontuario', max_length=255, blank=True)
    termo_aceito_em = models.DateTimeFieldPlus('Termo de ciência aceito em', null=True)
    situacao_declaracao = models.CharFieldPlus('Situação da Autodeclaração', choices=SITUACAO_CHOICES, max_length=50, default=AGUARDANDO_VALIDACAO)
    situacao_passaporte = models.CharFieldPlus('Situação do Passaporte Vacinal', choices=SITUACAO_PASSAPORTE_CHOICES, max_length=50,
                                               default=INVALIDO)
    avaliada_por = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Avaliada por',
                                         related_name='vinculo_autodeclaracao_avaliada_por', null=True)
    avaliada_em = models.DateTimeFieldPlus('Avaliada em', null=True)
    justificativa_indeferimento = models.TextField('Justificativa do Indeferimento', null=True)
    data_expiracao = models.DateTimeFieldPlus('Data da Expiração do Passaporte', null=True)
    tem_pendencia = models.BooleanField('Tem pendência', default=False)
    tem_cadastro = models.BooleanField('Tem cadastro no RN+Vacina', default=False)
    cartao_vacinal = models.FileFieldPlus('Cartão Vacinal Covid-19', null=True, upload_to='upload/saude/prontuario', max_length=255,
                                          blank=True)
    cartao_vacinal_cadastrado_em = models.DateTimeFieldPlus('Cartão vacinal cadastrado em', null=True)

    class Meta:
        verbose_name = 'Passaporte Vacinal da COVID'
        verbose_name_plural = 'Passaportes Vacinais da COVID'
        permissions = (
            ("pode_ver_todos_passaportes", "Pode ver Relatório de Passaporte Vacinal"),
            ("pode_ver_passaportes_do_campus", "Pode ver Relatório de Passaporte Vacinal do campus"),
            ("pode_ver_passaportes_dos_prestadores_do_campus", "Pode ver Relatório de Passaporte Vacinal dos Prestadores de Serviço do campus"),
            ("pode_ver_passaportes_dos_alunos_do_curso", "Pode ver Relatório de Passaporte Vacinal dos Alunos do campus"),
            ("pode_verificar_passaportes", "Pode verificar situação do passaporte vacinal"),
        )

    def get_categoria(self):
        return f'{type(self.vinculo.relacionamento)._meta.verbose_name}'

    def data_ultima_aplicacao(self):
        return self.data_terceira_dose or self.data_segunda_dose or self.data_primeira_dose

    def __str__(self):
        return self.vinculo.__str__()

    def get_faixa_etaria(self):
        try:
            idade = int(self.vinculo.pessoa.pessoafisica.idade)
        except Exception:
            idade = None
        if idade:
            if idade < 18:
                return 'Menores de 18 anos'
            elif idade >= 18 and idade < 60:
                return 'Entre 18 e 60 anos'
            elif idade >= 60:
                return 'Maiores de 60 anos'
        return '-'


class HistoricoValidacaoPassaporte(models.ModelPlus):
    passaporte = models.ForeignKeyPlus(PassaporteVacinalCovid, verbose_name='Passaporte Vacinal', on_delete=models.CASCADE)
    avaliado_em = models.DateTimeFieldPlus('Avaliado Em', auto_now_add=True)
    avaliado_por = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Avaliado por',
                                         related_name='historico_validacao_avaliado_por', null=True)
    situacao_declaracao = models.CharFieldPlus('Situação da Autodeclaração', choices=PassaporteVacinalCovid.SITUACAO_CHOICES, max_length=50, default=PassaporteVacinalCovid.AGUARDANDO_VALIDACAO)
    situacao_passaporte = models.CharFieldPlus('Situação do Passaporte Vacinal', choices=PassaporteVacinalCovid.SITUACAO_PASSAPORTE_CHOICES, max_length=50,
                                               default=PassaporteVacinalCovid.INVALIDO)
    justificativa_indeferimento = models.TextField('Justificativa do Indeferimento', null=True)
    possui_atestado_medico = models.BooleanField('Você possui atestado/laudo médico ou técnico indicando contraindicação para tomar a vacina?', null=True, blank=True)
    termo_aceito_em = models.DateTimeFieldPlus('Termo de ciência aceito em', null=True)

    class Meta:
        verbose_name = 'Histórico de Validação do Passaporte Vacinal da COVID'
        verbose_name_plural = 'Históricos de Validação dos Passaportes Vacinais da COVID'


class ResultadoTesteCovid(models.ModelPlus):
    AGUARDANDO_VALIDACAO = 'Aguardando validação'
    DEFERIDO = 'Deferido'
    INDEFERIDO = 'Indeferido'
    SITUACAO_CHOICES = (
        (AGUARDANDO_VALIDACAO, AGUARDANDO_VALIDACAO),
        (DEFERIDO, DEFERIDO),
        (INDEFERIDO, INDEFERIDO),
    )
    passaporte = models.ForeignKeyPlus(PassaporteVacinalCovid, verbose_name='Passaporte Vacinal', on_delete=models.CASCADE)
    arquivo = models.FileFieldPlus('Resultado do Teste COVID', upload_to='upload/saude/prontuario', max_length=255)
    realizado_em = models.DateTimeFieldPlus('Realizado em', null=True)
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado Em', auto_now_add=True)
    situacao = models.CharFieldPlus('Situação', choices=SITUACAO_CHOICES, max_length=50, default=AGUARDANDO_VALIDACAO)
    justificativa_indeferimento = models.TextField('Justificativa do Indeferimento', null=True)
    avaliado_em = models.DateTimeFieldPlus('Avaliado Em', null=True)
    avaliado_por = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Avaliado por',
                                         related_name='resultadotestecovid_avaliado_por', null=True)

    class Meta:
        verbose_name = 'Resultado de Teste COVID'
        verbose_name_plural = 'Resultados de Teste COVID'


class Sintoma(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', max_length=500)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Sintoma'
        verbose_name_plural = 'Sintomas'

    def __str__(self):
        return self.descricao


class NotificacaoCovid(models.ModelPlus):
    SITUACAO_CHOICES = (
        ('Suspeito sintomático', 'Suspeito sintomático'),
        ('Suspeito contactante', 'Suspeito contactante'),
        ('Confirmado', 'Confirmado'),
    )
    RESULTADO_TESTE_CHOICES = (
        ('Positivo', 'Positivo'),
        ('Negativo', 'Negativo'),
    )

    SIM_NAO_CHOICES = (
        ('Sim', 'Sim'),
        ('Não', 'Não'),
    )
    SIM_NAO_NSEI_CHOICES = (
        ('Sim', 'Sim'),
        ('Não', 'Não'),
        ('Não sei', 'Não sei'),
    )

    SEM_MONITORAMENTO = 'Sem monitoramento'
    SITUACAO_MONITORAMENTO_CHOICES = (
        (SEM_MONITORAMENTO, SEM_MONITORAMENTO),
        ('Suspeito em monitoramento', 'Suspeito em monitoramento'),
        ('Confirmado em monitoramento', 'Confirmado em monitoramento'),
        ('Descartado', 'Descartado'),
        ('Recuperado', 'Recuperado'),
        ('Óbito', 'Óbito'),
    )
    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Vínculo', on_delete=models.CASCADE)
    uo = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', on_delete=models.CASCADE)
    situacao = models.CharFieldPlus('Situação', choices=SITUACAO_CHOICES, max_length=100)
    data_inicio_sintomas = models.DateFieldPlus('Data de Início dos Sintomas', null=True, blank=True)
    sintomas = models.ManyToManyFieldPlus(Sintoma, blank=True)
    data_ultimo_teste = models.DateFieldPlus('Data do Último Teste Realizado', null=True, blank=True)
    resultado_ultimo_teste = models.CharFieldPlus('Resultado do Último Teste Realizado', choices=RESULTADO_TESTE_CHOICES, max_length=15, null=True, blank=True)
    arquivo_ultimo_teste = models.FileFieldPlus('Arquivo do Último Teste Realizado', upload_to='upload/saude/covid', max_length=255, null=True, blank=True)
    data_contato_suspeito = models.DateFieldPlus('Data do Contato Suspeito', null=True, blank=True)
    mora_com_suspeito = models.CharFieldPlus('A pessoa com quem você teve contato mora na mesma casa que você?', choices=SIM_NAO_CHOICES, max_length=15, null=True, blank=True)
    esteve_sem_mascara = models.CharFieldPlus('Durante esse contato você esteve sem máscara?', choices=SIM_NAO_CHOICES, max_length=15, null=True, blank=True)
    tempo_exposicao = models.CharFieldPlus('Qual foi o tempo de exposição que você teve com essa pessoa?', max_length=200, null=True, blank=True)
    suspeito_fez_teste = models.CharFieldPlus('A pessoa com que você teve contato realizou teste COVID?', choices=SIM_NAO_NSEI_CHOICES, max_length=15, null=True, blank=True)
    arquivo_teste = models.FileFieldPlus('Resultado do Teste', upload_to='upload/saude/covid',
                                         max_length=255, null=True, blank=True)
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado em', auto_now_add=True)
    monitoramento = models.CharFieldPlus('Monitoramento', choices=SITUACAO_MONITORAMENTO_CHOICES, max_length=100, default=SEM_MONITORAMENTO)

    class Meta:
        verbose_name = 'Notificação de COVID-19'
        verbose_name_plural = 'Notificações de COVID-19'

    def get_sintomas(self):
        return ', '.join(list(sintoma.descricao for sintoma in self.sintomas.all()))

    def pode_monitorar(self):
        return self.monitoramento not in ['Descartado', 'Recuperado', 'Óbito']


class MonitoramentoCovid(models.ModelPlus):
    notificacao = models.ForeignKeyPlus(NotificacaoCovid, verbose_name='Notificação Covid-19', on_delete=models.CASCADE)
    monitoramento = models.TextField('Monitoramento')
    situacao = models.CharFieldPlus('Situação', choices=NotificacaoCovid.SITUACAO_MONITORAMENTO_CHOICES, max_length=50)
    cadastrado_por = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Cadastrado por')
    cadastrado_em = models.DateTimeFieldPlus('Cadastrado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Monitoramento de COVID-19'
        verbose_name_plural = 'Monitoramentos de COVID-19'


class ValidadorIntercampi(models.ModelPlus):
    vinculo = models.OneToOneFieldPlus('comum.Vinculo', verbose_name='Validador', related_name='vinculo_validacao_intercampi')
    campi = models.ManyToManyFieldPlus(UnidadeOrganizacional, verbose_name='Campi')
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Validador Intercampi de Passaportes Vacinais'
        verbose_name_plural = 'Validadores Intercampi de Passaportes Vacinais'
