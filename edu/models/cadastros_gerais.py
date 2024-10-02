from dateutil.parser import parse
from django.core.exceptions import ValidationError
from django.conf import settings
from djtools.db import models
from djtools.utils import normalizar_nome_proprio
from edu.managers import FiltroUnidadeOrganizacionalManager
from edu.models.logs import LogModel

PERIODO_LETIVO_CHOICES = settings.PERIODO_LETIVO_CHOICES


class OrgaoEmissorRg(models.ModelPlus):
    SEARCH_FIELDS = ['nome']
    nome = models.CharFieldPlus(verbose_name='Nome')

    class Meta:
        verbose_name = 'Orgão Emissor de Identidade'
        verbose_name_plural = 'Orgãos Emissores de Identidade'

    def __str__(self):
        return self.nome


class Pais(models.ModelPlus):
    SEARCH_FIELDS = ['sigla', 'nome']
    sigla = models.CharFieldPlus(verbose_name='Código')
    nome = models.CharFieldPlus(verbose_name='Nome')

    class Meta:
        verbose_name = 'País'
        verbose_name_plural = 'Países'

    def __str__(self):
        return self.nome


class Estado(models.ModelPlus):
    SEARCH_FIELDS = ['nome']
    ESTADOS = dict(
        AC=12,
        AL=27,
        AM=13,
        AP=16,
        BA=29,
        CE=23,
        DF=53,
        ES=32,
        GO=52,
        MA=21,
        MG=31,
        MS=50,
        MT=51,
        PA=15,
        PB=25,
        PE=26,
        PI=22,
        PR=41,
        RJ=33,
        RN=24,
        RO=11,
        RR=14,
        RS=43,
        SC=42,
        SE=28,
        SP=35,
        TO=17,
    )

    nome = models.CharFieldPlus('Nome')

    class Meta:
        verbose_name = 'Estado'
        verbose_name_plural = 'Estados'

    def __str__(self):
        return normalizar_nome_proprio(self.nome)

    @classmethod
    def get_estado_por_sigla(self, sigla):
        estados = Estado.ESTADOS
        estado = Estado.objects.filter(id=estados.get(sigla.upper(), 24))
        if estado:
            return estado[0]
        else:
            return None

    @classmethod
    def get_sigla_por_nome(self, nome):
        estado = Estado.objects.filter(nome__unaccent__icontains=nome)
        if estado:
            estado = estado[0]
        else:
            return ''
        for sigla, cod in list(Estado.ESTADOS.items()):
            if cod == estado.id:
                return str(sigla)

    def get_sigla(self):
        for sigla, cod in list(self.ESTADOS.items()):
            if cod == self.id:
                return str(sigla)


class Cidade(models.ModelPlus):
    SEARCH_FIELDS = ['nome']

    nome = models.UnaccentField(verbose_name='Nome', db_index=True, max_length=255)
    estado = models.ForeignKey('edu.Estado', null=True, blank=True, on_delete=models.CASCADE)
    cep_inicial = models.CharFieldPlus(verbose_name='CEP Inicial', null=True, blank=True)
    cep_final = models.CharFieldPlus(verbose_name='CEP Final', null=True, blank=True)
    codigo = models.CharField(max_length=10, verbose_name='Código', null=True, blank=True, help_text='Código IBGE')
    pais = models.ForeignKeyPlus('edu.Pais', verbose_name='País', null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Cidade'
        verbose_name_plural = 'Cidades'
        ordering = ('nome',)

    def get_absolute_url(self):
        return '/edu/visualizar/edu/cidade/{}/'.format(self.pk)

    def __str__(self):
        result = normalizar_nome_proprio(self.nome)
        if self.pais and not self.codigo:
            result = f'{result} ({self.pais})'
        elif self.estado:
            result = f'{result}-{self.estado.get_sigla()}'
        return result

    def clean(self):
        if self.codigo and self.pais and self.pais.nome != 'Brasil':
            raise ValidationError('Informe o código do IBGE somente para cidades do Brasil.')
        if not self.codigo and not self.pais:
            raise ValidationError('Informe o código do IBGE caso seja uma cidade do Brasil. Caso seja uma cidade estrangeira, informe o seu país.')

    @classmethod
    def get_cidade_by_municipio(cls, municipio):
        if municipio:
            estado = Estado.get_estado_por_sigla(municipio.uf)
            return Cidade.objects.filter(nome=municipio.nome.upper(), estado=estado).first()
        return None


class Cartorio(models.ModelPlus):
    SEARCH_FIELDS = ['nome', 'cidade__nome', 'cidade__estado__nome']

    nome = models.CharFieldPlus('Nome')
    cidade = models.ForeignKeyPlus('edu.Cidade')
    serventia = models.CharFieldPlus('Serventia', blank=True)

    class Meta:
        verbose_name = 'Cartório'
        verbose_name_plural = 'Cartórios'

    def __str__(self):
        return '{} ({})'.format(self.nome, str(self.cidade))

    def get_absolute_url(self):
        return '/edu/visualizar/edu/cartorio/{}/'.format(self.pk)


class FormaIngresso(LogModel):
    VESTIBULAR = 1
    ENEM = 2
    AVALIACAO_SERIADA = 3
    SELECAO_SIMPLIFICADA = 4
    EGRESSO_BI_LI = 5
    PEC_G = 6
    TRANSFERENCIA_EX_OFICIO = 7
    DECISAO_JUDICIAL = 8
    VAGAS_REMANESCENTES = 9
    PROGRAMAS_ESPECIAIS = 10

    CLASSIFICACAO_CENSUP_CHOICES = [
        [VESTIBULAR, 'Vestibular'],
        [ENEM, 'Enem'],
        [AVALIACAO_SERIADA, 'Avaliação Seriada'],
        [SELECAO_SIMPLIFICADA, 'Seleção Simplificada'],
        [EGRESSO_BI_LI, 'Egresso BI/LI'],
        [PEC_G, 'PEC-G'],
        [TRANSFERENCIA_EX_OFICIO, 'Transferência Ex Officio'],
        [DECISAO_JUDICIAL, 'Decisão judicial'],
        [VAGAS_REMANESCENTES, 'Vagas Remanescentes'],
        [PROGRAMAS_ESPECIAIS, 'Programas Especiais'],
    ]

    CLASSIFICACAO_EDUCACENSO_CHOICES = [
        [1, 'Sem processo seletivo'],
        [2, 'Sorteio'],
        [3, 'Transferência'],
        [4, 'Exame de seleção sem reserva de vaga'],
        [5, 'Exame de seleção, vaga reservada para alunos da rede pública de ensino'],
        [6, 'Exame de seleção, vaga reservada para alunos da rede pública de ensino, com baixa renda e autodeclarado preto, pardo ou indígena'],
        [7, 'Exame de seleção, vaga reservada para outros programas de ação afirmativa '],
        [8, 'Outra forma de ingresso'],
        [9, 'Exame de seleção, vaga reservada para alunos da rede pública de ensino, com baixa renda'],
    ]

    descricao = models.CharFieldPlus('Descrição', unique=True)
    ativo = models.BooleanField(verbose_name='Ativo', default=False)
    classificacao_censup = models.IntegerField(verbose_name='Classificação CENSUP', null=True, blank=True, choices=CLASSIFICACAO_CENSUP_CHOICES)
    classificacao_educacenso = models.IntegerField(verbose_name='Classificação EDUCACENSO', null=True, blank=True, choices=CLASSIFICACAO_EDUCACENSO_CHOICES)

    programa_vaga_etinico = models.BooleanField(verbose_name='Étnico', default=False)
    racas = models.ManyToManyField('comum.Raca', verbose_name='Raças/Etnias', blank=True)
    programa_vaga_pessoa_deficiencia = models.BooleanField(verbose_name='Pessoa com Deficiência', default=False)
    programa_vaga_escola_publica = models.BooleanField(verbose_name='Estudante procedente de escola pública', default=False)
    programa_vaga_social = models.BooleanField(verbose_name='Social/renda familiar', default=False)
    programa_vaga_outros = models.BooleanField(verbose_name='Outros programas de vaga', default=False)

    class Meta:
        verbose_name = 'Forma de Ingresso'
        verbose_name_plural = 'Formas de Ingresso'
        ordering = ('-ativo', 'descricao')

    def __str__(self):
        if self.ativo:
            return self.descricao
        else:
            return '{} (Inativa)'.format(self.descricao)

    def get_absolute_url(self):
        return '/edu/visualizar/edu/formaingresso/{}/'.format(self.pk)


class AreaCurso(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Área de Curso'
        verbose_name_plural = 'Áreas de Cursos'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/areacurso/{}/'.format(self.pk)


class ClassificacaoComplementarComponenteCurricular(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Classificação Complementar de Componente Curricular'
        verbose_name_plural = 'Classificações Complementares de Componente Curricular'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/classificacaocomplementarcomponentecurricular/{}/'.format(self.pk)


class EixoTecnologico(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Eixo Tecnológico'
        verbose_name_plural = 'Eixos Tecnológicos'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/eixotecnologico/{}/'.format(self.pk)


class AreaCapes(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Área Capes'
        verbose_name_plural = 'Áreas Capes'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/areacapes/{}/'.format(self.pk)


class AreaConcentracao(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Área de Concentração'
        verbose_name_plural = 'Áreas de Concentração'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/areaconcentracao/{}/'.format(self.pk)


class Programa(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Programa'
        verbose_name_plural = 'Programas'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/programa/{}/'.format(self.pk)


class NaturezaParticipacao(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Natureza de Participação'
        verbose_name_plural = 'Naturezas de Participação'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/naturezaparticipacao/{}/'.format(self.pk)


class Turno(LogModel):
    NOTURNO = 1
    VESPERTINO = 2
    MATUTINO = 3
    EAD = 5
    DIURNO = 6

    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Turno'
        verbose_name_plural = 'Turnos'
        ordering = ('-id',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/turno/{}/'.format(self.pk)


class SituacaoMatricula(LogModel):
    MATRICULADO = 1
    TRANCADO = 2
    JUBILADO = 3
    TRANSFERIDO_INTERNO = 4
    CONCLUDENTE = 5
    CONCLUIDO = 6
    FALECIDO = 7
    AFASTADO = 8
    EVASAO = 9
    CANCELADO = 10
    TRANSFERIDO_EXTERNO = 11
    ESTAGIARIO_CONCLUDENTE = 12
    AGUARDANDO_COLACAO_DE_GRAU = 13
    CERTIFICADO_ENEM = 14
    AGUARDANDO_SEMINARIO = 15
    AGUARDANDO_ENADE = 16
    INTERCAMBIO = 17
    EGRESSO = 18
    FORMADO = 19
    CANCELAMENTO_COMPULSORIO = 20
    MATRICULA_VINCULO_INSTITUCIONAL = 21
    CANCELAMENTO_POR_DESLIGAMENTO = 97
    CANCELAMENTO_POR_DUPLICIDADE = 98
    TRANCADO_VOLUNTARIAMENTE = 99
    NAO_CONCLUIDO = 100
    TRANSFERIDO_SUAP = 101

    SITUACOES_INATIVAS_PARA_EXCLUSAO_TURMA = [
        TRANCADO,
        EVASAO,
        CANCELADO,
        CANCELAMENTO_COMPULSORIO,
        CANCELAMENTO_POR_DESLIGAMENTO,
        CANCELAMENTO_POR_DUPLICIDADE,
        TRANCADO_VOLUNTARIAMENTE,
    ]

    codigo_academico = models.IntegerField(null=True)
    descricao = models.CharFieldPlus('Descrição', unique=True)
    ativo = models.BooleanField(verbose_name='Ativo', default=False)

    class Meta:
        verbose_name = 'Situação de Matrícula'
        verbose_name_plural = 'Situações de Matrículas'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/situacaomatricula/{}/'.format(self.pk)


class SituacaoMatriculaPeriodo(LogModel):
    EM_ABERTO = 1
    MATRICULADO = 2
    TRANCADA = 3
    CANCELADA = 4
    AFASTADO = 5
    TRANSF_EXTERNA = 6
    TRANSF_INSTITUICAO = 7
    TRANSF_TURNO = 8
    TRANSF_CURSO = 9
    DEPENDENCIA = 10  #
    APROVADO = 11  #
    REPROVADO = 12  #
    VINDO_DE_TRANSFERENCIA = 13  #
    JUBILADO = 14
    EVASAO = 15
    REPROVADO_POR_FALTA = 16  #
    ESTAGIO_MONOGRAFIA = 17  #
    PERIODO_FECHADO = 18  #
    FECHADO_COM_PENDENCIA = 19  #
    APROVEITA_MODULO = 20  #
    MATRICULA_VINCULO_INSTITUCIONAL = 21  #
    CERTIFICADO_ENEM = 22
    CANCELAMENTO_COMPULSORIO = 23
    INTERCAMBIO = 24

    CANCELAMENTO_POR_DESLIGAMENTO = 97
    CANCELAMENTO_POR_DUPLICIDADE = 98
    TRANCADA_VOLUNTARIAMENTE = 99
    TRANSFERIDO_SUAP = 100

    SITUACOES_CONTABILIZADAS_PARA_JUBILAMENTO = [
        MATRICULADO,
        DEPENDENCIA,
        AFASTADO,
        APROVADO,
        VINDO_DE_TRANSFERENCIA,
        REPROVADO,
        REPROVADO_POR_FALTA,
        PERIODO_FECHADO,
        FECHADO_COM_PENDENCIA,
        APROVEITA_MODULO,
        TRANCADA_VOLUNTARIAMENTE,
    ]

    SITUACOES_MATRICULADO = [
        APROVADO,
        APROVEITA_MODULO,
        DEPENDENCIA,
        ESTAGIO_MONOGRAFIA,
        FECHADO_COM_PENDENCIA,
        MATRICULADO,
        MATRICULA_VINCULO_INSTITUCIONAL,
        PERIODO_FECHADO,
        VINDO_DE_TRANSFERENCIA,
        REPROVADO,
        REPROVADO_POR_FALTA,
    ]

    SITUACOES_INATIVAS_PARA_EXCLUSAO_DIARIO = [
        CANCELADA,
        CANCELAMENTO_COMPULSORIO,
        CANCELAMENTO_POR_DESLIGAMENTO,
        CANCELAMENTO_POR_DUPLICIDADE,
        EVASAO,
        JUBILADO,
        INTERCAMBIO,
        TRANCADA,
        TRANCADA_VOLUNTARIAMENTE,
    ]

    codigo_academico = models.IntegerField(null=True)
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Situação de Matrícula no Período'
        verbose_name_plural = 'Situações de Matrículas no Período'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/situacaomatriculaperiodo/{}/'.format(self.pk)


class HorarioCampus(LogModel):
    descricao = models.CharFieldPlus('Descrição')
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Campus', on_delete=models.CASCADE)
    ativo = models.BooleanField('Ativo', default=True)
    eh_padrao = models.BooleanField('Horário Padrão', default=False)

    objects = models.Manager()
    locals = FiltroUnidadeOrganizacionalManager('uo')

    class Meta:
        verbose_name = 'Horário do Campus'
        verbose_name_plural = 'Horários dos Campi'
        ordering = ('descricao',)

    def __str__(self):
        return '{} ({})'.format(self.descricao, self.uo.sigla)

    def get_absolute_url(self):
        return '/edu/horariocampus/{}'.format(self.id)

    def replicar(self, descricao, uo):
        horarios_aulas = list(self.horarioaula_set.all())
        self.id = None
        self.descricao = descricao
        self.uo = uo
        self.clean()
        self.save()
        for horario_aula in horarios_aulas:
            horario_aula.id = None
            horario_aula.horario_campus = self
            horario_aula.save()
        return self


class HorarioAula(LogModel):
    HORARIO_1 = 1
    HORARIO_2 = 2
    HORARIO_3 = 3
    HORARIO_4 = 4
    HORARIO_5 = 5
    HORARIO_6 = 6
    HORARIO_7 = 7
    HORARIO_CHOICES = [[HORARIO_1, '1'], [HORARIO_2, '2'], [HORARIO_3, '3'], [HORARIO_4, '4'], [HORARIO_5, '5'], [HORARIO_6, '6'], [HORARIO_7, '7']]
    horario_campus = models.ForeignKeyPlus('edu.HorarioCampus', on_delete=models.CASCADE)
    numero = models.PositiveIntegerField(verbose_name='Número', choices=HORARIO_CHOICES)
    turno = models.ForeignKeyPlus('edu.Turno', on_delete=models.CASCADE)
    inicio = models.CharFieldPlus(verbose_name='Início', max_length=5)
    termino = models.CharFieldPlus(verbose_name='Término', max_length=5)

    class Meta:
        verbose_name = 'Horário de Aula'
        verbose_name_plural = 'Horários das Aulas'
        ordering = ('turno', 'numero')

    def __str__(self):
        return '{} - {}'.format(self.inicio, self.termino)

    def preencher_zeros(self, horario):
        if len(horario) < 5:
            try:
                hora, minuto = horario.split(':')
            except ValueError:
                hora, minuto = [horario, '0']
            try:
                int(hora)
                int(minuto)
            except Exception:
                raise ValidationError('Formato de hora inválido')
            horario = '{}:{}'.format(hora.zfill(2), minuto.zfill(2))
        return horario

    def clean(self):
        self.inicio = self.preencher_zeros(self.inicio)
        self.termino = self.preencher_zeros(self.termino)

        try:
            parse('01/01/2012 {}:00'.format(self.inicio), dayfirst=True)
        except Exception:
            raise ValidationError('Hora de início inválida: {}.'.format(self.inicio))

        try:
            parse('01/01/2012 {}:00'.format(self.termino), dayfirst=True)
        except Exception:
            raise ValidationError('Hora de término inválida: {}.'.format(self.termino))


class HorarioAulaDiario(LogModel):
    DIA_SEMANA_SEG = 1
    DIA_SEMANA_TER = 2
    DIA_SEMANA_QUA = 3
    DIA_SEMANA_QUI = 4
    DIA_SEMANA_SEX = 5
    DIA_SEMANA_SAB = 6
    DIA_SEMANA_DOM = 7
    DIA_SEMANA_CHOICES = [
        [DIA_SEMANA_SEG, 'Segunda'],
        [DIA_SEMANA_TER, 'Terça'],
        [DIA_SEMANA_QUA, 'Quarta'],
        [DIA_SEMANA_QUI, 'Quinta'],
        [DIA_SEMANA_SEX, 'Sexta'],
        [DIA_SEMANA_SAB, 'Sábado'],
        [DIA_SEMANA_DOM, 'Domingo'],
    ]

    diario = models.ForeignKeyPlus('edu.Diario', on_delete=models.CASCADE)
    dia_semana = models.PositiveIntegerField(choices=DIA_SEMANA_CHOICES)
    horario_aula = models.ForeignKeyPlus('edu.HorarioAula', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Horário de Aula no Diário'
        verbose_name_plural = 'Horários das Aulas no Diário'

    def __str__(self):
        return 'Aula às {} no diário {}'.format(self.horario_aula, self.diario.pk)

    def get_diario(self):
        return self.diario

    @staticmethod
    def get_dias_semana_seg_a_sex():
        dias_semana = []
        for dia in HorarioAulaDiario.DIA_SEMANA_CHOICES:
            if dia[0] < 6:
                dias_semana.append(dia)
        return dias_semana

    def get_horario_formatado(self):
        return "{}{}{}".format((self.dia_semana + 1), self.horario_aula.turno.descricao[0], self.horario_aula.numero)

    def engloba_hora(self, hora='00:00'):
        inicio = int(self.horario_aula.inicio.replace(':', ''))
        termino = int(self.horario_aula.termino.replace(':', ''))
        hora = int(hora.replace(':', ''))
        return hora > inicio and hora < termino


class NivelEnsino(LogModel):
    SEARCH_FIELDS = ['descricao']
    FUNDAMENTAL = 1
    GRADUACAO = 3
    MEDIO = 2
    POS_GRADUACAO = 4

    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Nível de Ensino'
        verbose_name_plural = 'Níveis de Ensino'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/nivelensino/{}/'.format(self.pk)


class Modalidade(LogModel):
    LICENCIATURA = 2
    ENGENHARIA = 4
    FIC = 8
    MESTRADO = 9
    ESPECIALIZACAO = 10
    INTEGRADO = 11
    INTEGRADO_EJA = 12
    SUBSEQUENTE = 13
    TECNOLOGIA = 14
    APERFEICOAMENTO = 15
    DOUTORADO = 16
    PROEJA_FIC_FUNDAMENTAL = 17
    CONCOMITANTE = 18
    BACHARELADO = 19

    descricao = models.CharFieldPlus('Descrição', unique=True)
    nivel_ensino = models.ForeignKeyPlus('edu.NivelEnsino', verbose_name='Nível de Ensino', null=True, related_name='modalidades', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Modalidade/Forma de Ensino'
        verbose_name_plural = 'Modalidades/Formas de Ensino'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/modalidade/{}/'.format(self.pk)

    @staticmethod
    def modalidades_que_fazem_estagio():
        return [Modalidade.LICENCIATURA, Modalidade.ENGENHARIA, Modalidade.BACHARELADO, Modalidade.INTEGRADO, Modalidade.SUBSEQUENTE, Modalidade.TECNOLOGIA]


class Convenio(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Convênio'
        verbose_name_plural = 'Convênios'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/convenio/{}/'.format(self.pk)


class Nucleo(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Núcleo'
        verbose_name_plural = 'Núcleos'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/nucleo/{}/'.format(self.pk)


class ConfiguracaoGestao(LogModel):
    class Meta:
        verbose_name = 'Configuração Computadores/Campus'
        verbose_name_plural = 'Configurações Computadores/Campus'

    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', on_delete=models.CASCADE)
    qtd_computadores = models.IntegerField()


class ModeloDocumento(LogModel):
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    tipo = models.IntegerField(verbose_name='Tipo', choices=[[1, 'DIPLOMA/CERTIFICADO'], [2, 'DECLARAÇÃO DE MATRÍCULA']])
    modalidade = models.ForeignKeyPlus('edu.Modalidade', verbose_name='Modalidade de Ensino', null=True, on_delete=models.CASCADE)
    template = models.FileFieldPlus(
        upload_to='edu/modelos_documento/',
        filetypes=['docx'],
        null=True,
        blank=True,
        verbose_name='Template',
        check_mimetype=False,
        help_text='''O arquivo de modelo deve ser uma arquivo .docx contendo as marcações
            #CHGERAL#, #CHESPECIAL#, #CHESTAGIO#, #EMPRESAESTAGIO#, #LEI#, #NOMECAMPUS#, #ALUNO#, #CREDENCIAMENTO#, #RECREDENCIAMENTO#, #COLACAO#,
            #NACIONALIDADE#, #NATURALIDADE#, #DATANASCIMENTO#, #CPF#, #PASSAPORTE#, #RG#, #UFRG#, #EMISSORRG#, #DATARG#, #CURSO#,
            #HABILITACAOPEDAGOGICA#, #AREACONCENTRACAO#, #PROGRAMA#, #INICIO#, #FIM#, '#TITULO#,   #CHTOTAL#, #CIDADE#, #UF#,
            #DATA#, #COORDENADOR#, #AREA#, #TITULOCOORDENADOR#, #OREITOR#, #REITOR#, #TITULOREITOR#, #EMEXERCICIO#, #DIRETORGERAL#,
            #TITULODIRETORGERAL#, #DIRETORACADEMICO#, #TITULODIRETORACADEMICO#, #DISCIPLINAS#, #PROFESSORES#, #TITULACOES#, #NOTAS#,
            #CH#, #REGISTRO#, #LIVRO#, #FOLHA#, #DATAEXPEDICAO#, #PROCESSO#, #CODIGOVERIFICADOR#, #NASCIDO#, #PORTADOR#, #DIPLOMADO#,
            #AUTORIZACAO#, #RECONHECIMENTO#, #DIATCC#, #MESTCC#, #ANOTCC#, #TIPOTCC#, #TEMATCC#, #ORIENTADOR#, #TITULACAOORIENTADOR#,
            #CHTCC#, #NOTATCC#, #VIA#, #SERVIDORREGISTROESCOLAR#, #PORTARIAREGISTROESCOLAR#, #NOMEPAI#, #NOMEMAE#, #ANOCONCLUSAOFIC#,
            #AUTENTICACAOSISTEC#, #COORDENADORREGISTROESCOLAR#, #HABILITACAO#''',
    )
    ativo = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Modelo de Documento'
        verbose_name_plural = 'Modelos de Documento'

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/modelo_documento/{}/'.format(self.pk)


class ConfiguracaoLivro(LogModel):
    NOME_LIVRO_ELETRONICO = 'Diplomas/Certificados Eletrônicos'

    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Campus', on_delete=models.CASCADE)
    modalidades = models.ManyToManyFieldPlus('edu.Modalidade', verbose_name='Modalidades de Ensino', blank=True)
    numero_livro = models.PositiveIntegerField(verbose_name='Nº do Livro Atual')
    folhas_por_livro = models.PositiveIntegerField(verbose_name='Folhas por Livro')
    numero_folha = models.PositiveIntegerField(verbose_name='Nº da Folha Atual')
    numero_registro = models.PositiveIntegerField(verbose_name='Nº do Registro Atual')
    codigo_qacademico = models.IntegerField(verbose_name='Código Q-Acadêmico', null=True, blank=True)

    class Meta:
        verbose_name = 'Configuração de Livro de Registros'
        verbose_name_plural = 'Configurações de Livro de Registros'

    def __str__(self):
        return self.descricao

    def gerar_proximo_numero(self):
        self.numero_registro += 1
        if self.numero_folha == self.folhas_por_livro:
            self.numero_folha = 1
            self.numero_livro += 1
        else:
            self.numero_folha += 1
        self.save()


class LinhaPesquisa(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Linha de Pesquisa'
        verbose_name_plural = 'Linhas de Pesquisa'

        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/linhapesquisa/{}/'.format(self.pk)


class VinculoProfessorEAD(LogModel):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Vínculo dos Professores EAD'
        verbose_name_plural = 'Vínculos dos Professores EAD'

    def __str__(self):
        return self.descricao


class NucleoCentralEstruturante(LogModel):
    descricao = models.CharFieldPlus('Descrição', max_length=255)

    class Meta:
        verbose_name = 'Núcleo Central Estruturante'
        verbose_name_plural = 'Núcleos Centrais Estruturantes'

    def __str__(self):
        return self.descricao


class Disciplina(LogModel):
    SEARCH_FIELDS = ['descricao']
    descricao = models.CharFieldPlus('Descrição', max_length=255)

    class Meta:
        verbose_name = 'Disciplina de Ingresso'
        verbose_name_plural = 'Disciplinas de Ingresso'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao


class TipoProfessorDiario(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Tipo de Professor em Diário'
        verbose_name_plural = 'Tipos de Professor em Diário'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/tipoprofessordiario/{}/'.format(self.pk)


class TipoComponente(LogModel):
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=100)

    class Meta:
        verbose_name = 'Tipo de Componente'
        verbose_name_plural = 'Tipos de Componente'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/tipo_componente/{}/'.format(self.pk)

    def delete(self, *args, **kwargs):
        if not self.componente_set.exists():
            super().delete(*args, **kwargs)
        else:
            raise Exception('Este tipo de componente já possui componentes cadastrados.')


class TipoAtividadeAprofundamento(LogModel):
    descricao = models.CharFieldPlus('Descrição')
    modalidades = models.ManyToManyFieldPlus('edu.Modalidade', blank=True, verbose_name='Modalidades de Ensino')

    class Meta:
        verbose_name = 'Tipo de Atividade Teórico-Práticas de Aprofundamento'
        verbose_name_plural = 'Tipos de Atividades Teórico-Práticas de Aprofundamento'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao


class TipoAtividadeComplementar(LogModel):
    descricao = models.CharFieldPlus('Descrição')
    modalidades = models.ManyToManyFieldPlus('edu.Modalidade', blank=True, verbose_name='Modalidades de Ensino')

    class Meta:
        verbose_name = 'Tipo de Atividade Complementar'
        verbose_name_plural = 'Tipos de Atividades Complementares'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/tipoatividadecomplementar/{}/'.format(self.pk)


class JustificativaDispensaENADE(LogModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)
    ativo = models.BooleanField('Ativo', default=True)

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name = 'Justif. de Dispensa do ENADE'
        verbose_name_plural = 'Justif. de Dispensa do ENADE'


class TipoMedidaDisciplinar(LogModel):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Tipo de Medida Disciplinar'
        verbose_name_plural = 'Tipos de Medidas Disciplinares'

        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/tipomedidadisciplinar/{}/'.format(self.pk)


class TipoPremiacao(LogModel):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Tipo de Premiação'
        verbose_name_plural = 'Tipos de Premiações'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/visualizar/edu/tipopremiacao/{}/'.format(self.pk)


class CursoFormacaoSuperior(LogModel):
    area = models.CharFieldPlus(
        'Área',
        choices=[
            [x, x]
            for x in (
                'Outros',
                'Humanidades e Artes',
                'Ciências, Matemática e Computação',
                'Educação',
                'Ciências Sociais, Negócios e Direitos',
                'Engenharia, Produção e Construção',
                'Saúde e Bem-estar Social',
                'Agricultura e Veterinária',
                'Serviços',
            )
        ],
    )
    codigo = models.CharFieldPlus('Código')
    descricao = models.CharFieldPlus('Descrição')
    grau = models.CharFieldPlus('Grau', choices=[[x, x] for x in ('Licenciatura', 'Tecnológico', 'Bacharelado')])

    class Meta:
        verbose_name = 'Curso de Formação Superior'
        verbose_name_plural = 'Cursos de Formação Superior'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao


class InstituicaoEnsinoSuperior(LogModel):
    SEARCH_FIELDS = ['nome', 'codigo']
    nome = models.CharFieldPlus('Nome')
    codigo = models.CharFieldPlus('Código')
    cidade = models.ForeignKey(Cidade, verbose_name='Cidade', null=True, on_delete=models.CASCADE)
    tipo = models.CharFieldPlus('Tipo', choices=[[x, x] for x in ('Pública', 'Privada')])
    dependencia_administrativa = models.IntegerField('Dependência Administrativa', choices=[[1, 'Federal'], [2, 'Estadual'], [3, 'Municipal'], [4, 'Privada']])

    class Meta:
        verbose_name = 'Instituição de Ensino Superior'
        verbose_name_plural = 'Instituições de Ensino Superior'
        ordering = ('nome',)

    def __str__(self):
        return '{} - {}'.format(self.codigo, self.nome)
