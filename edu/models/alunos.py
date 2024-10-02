import uuid
import copy
import datetime
import operator
from collections import OrderedDict
from decimal import Decimal
from random import choice
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import transaction
from django.db.models import Q
from django.db.models.aggregates import Sum, Min
from django.db.transaction import atomic
from djtools.utils import mask_nota
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from rest_framework.authtoken.models import Token
from comum.models import Ano, User, Vinculo, Configuracao
from comum.utils import diferenca_listas, somar_data
from comum.utils import tl, insert_space
from djtools.db import models
from djtools.templatetags.filters import format_iterable
from djtools.testutils import running_tests
from djtools.thumbs import ImageWithThumbsField
from djtools.utils import normalizar_nome_proprio
from djtools.storages import get_overwrite_storage
from edu import perms
from edu.managers import (
    FiltroUnidadeOrganizacionalManager,
    AlunoManager,
    AlunoLocalManager,
    AlunosComMatrizManager,
    AlunosAtivosManager,
    AlunosCaracterizadosManager,
    AlunosNaoFICManager,
    AlunosFICManager,
)
from edu.models.projeto_final import AssinaturaAtaEletronica
from edu.models.atividades_complementares import ItemConfiguracaoAtividadeComplementar
from edu.models.cadastros_gerais import PERIODO_LETIVO_CHOICES, SituacaoMatricula, SituacaoMatriculaPeriodo, Modalidade, TipoAtividadeComplementar, Turno, NivelEnsino
from edu.models.cursos import EstruturaCurso, CursoCampus, ComponenteCurricular, Componente, MatrizCurso
from edu.models.diarios import Diario, ItemConfiguracaoAvaliacao, Aula
from edu.models.diplomas import RegistroEmissaoDiploma, AssinaturaEletronica, AssinaturaDigital
from edu.models.diretorias import Diretoria
from edu.models.enade import RegistroConvocacaoENADE
from edu.models.historico import AproveitamentoEstudo, CertificacaoConhecimento
from edu.models.diarios_especiais import CreditoEspecial
from edu.models.estagio_docente import EstagioDocente
from edu.models.eventos import ColacaoGrau, ParticipanteEvento
from edu.models.logs import LogModel
from edu.models.historico import MatriculaDiarioResumida, MatriculaDiario, MatriculaPeriodo
from edu.models.procedimentos import PedidoMatricula, ProcedimentoMatricula, AproveitamentoComponente
from edu.models.projeto_final import ProjetoFinal
from edu.models.atividades import AtividadeCurricularExtensao
from edu.models.turmas import Turma
from djtools.db.models import ModelPlus
from django.apps import apps


class SequencialMatricula(ModelPlus):
    prefixo = models.CharFieldPlus(max_length=255)
    contador = models.PositiveIntegerField()

    @staticmethod
    def proximo_numero(prefixo):
        qs_sequencial = SequencialMatricula.objects.filter(prefixo=prefixo)
        if qs_sequencial.exists():
            sequencial = qs_sequencial[0]
            contador = sequencial.contador
        else:
            sequencial = SequencialMatricula()
            sequencial.prefixo = prefixo
            contador = 1
        sequencial.contador = contador + 1
        sequencial.save()
        numero = f'000000000{contador}'
        matricula = f'{prefixo}{numero[-4:]}'
        if Aluno.objects.filter(matricula=matricula).exists():
            return SequencialMatricula.proximo_numero(prefixo)
        else:
            return matricula


class Observacao(LogModel):
    observacao = models.TextField('Observação da Matrícula')
    aluno = models.ForeignKeyPlus('edu.Aluno', verbose_name='Aluno')
    data = models.DateFieldPlus(verbose_name='Data')
    usuario = models.ForeignKeyPlus('comum.User', verbose_name='Usuário')

    class Meta:
        permissions = (('adm_delete_observacao', 'Pode deletar observações de outros usuários'),)


class Aluno(LogModel):
    SEARCH_FIELDS = ["pessoa_fisica__search_fields_optimized", "matricula"]

    EMPTY_CHOICES = [['', '----']]
    PERIODO_LETIVO_CHOICES = PERIODO_LETIVO_CHOICES
    ESTADO_CIVIL_CHOICES = [['Solteiro', 'Solteiro'], ['Casado', 'Casado'], ['União Estável', 'União Estável'], ['Divorciado', 'Divorciado'], ['Viúvo', 'Viúvo']]
    PARENTESCO_CHOICES = [['Pai/Mãe', 'Pai/Mãe'], ['Avô/Avó', 'Avô/Avó'], ['Tio/Tia', 'Tio/Tia'], ['Sobrinho/Sobrinha', 'Sobrinho/Sobrinha'], ['Outro', 'Outro']]
    TIPO_ZONA_RESIDENCIAL_CHOICES = [['1', 'Urbana'], ['2', 'Rural']]
    TIPO_SANGUINEO_CHOICES = [['O-', 'O-'], ['O+', 'O+'], ['A-', 'A-'], ['A+', 'A+'], ['B-', 'B-'], ['B+', 'B+'], ['AB-', 'AB-'], ['AB+', 'AB+']]
    TIPO_NACIONALIDADE_CHOICES = [
        ['Brasileira', 'Brasileira'],
        ['Brasileira - Nascido no exterior ou naturalizado', 'Brasileira - Nascido no exterior ou naturalizado'],
        ['Estrangeira', 'Estrangeira'],
    ]
    TIPO_INSTITUICAO_ORIGEM_CHOICES = [['Pública', 'Pública'], ['Privada', 'Privada']]
    TIPO_CERTIDAO_CHOICES = [['1', 'Nascimento'], ['2', 'Casamento']]
    COTA_SISTEC_CHOICES = [
        ['1', 'Escola Pública'],
        ['2', 'Cor/Raça'],
        ['3', 'Olimpíada'],
        ['4', 'Indígena'],
        ['5', 'Necessidades Especiais'],
        ['6', 'Zona Rural'],
        ['7', 'Quilombola'],
        ['8', 'Assentamento'],
        ['9', 'Não se aplica'],
    ]
    COTA_MEC_CHOICES = [
        ['1', 'Seleção Geral'],
        ['2', 'Oriundo de escola pública, com renda superior a 1,5 S.M. e declarado preto, pardo ou indígena (PPI)'],
        ['3', 'Oriundo de escola pública, com renda superior a 1,5 S.M., não declarado PPI'],
        ['4', 'Oriundo de escola pública, com renda inferior a 1,5 S.M., declarado PPI'],
        ['5', 'Oriundo de escola pública, com renda inferior a 1,5 S.M., não declarado PPI'],
        ['0', 'Não se aplica'],
    ]
    TIPO_ALUNO_CHOICES = [['Regular', 'Regular'], ['Especial', 'Especial']]

    DEFICIENCIA_VISUAL = '1'
    DEFICIENCIA_VISUAL_TOTAL = '11'
    DEFICIENCIA_AUDITIVA = '2'
    DEFICIENCIA_AUDITIVA_TOTAL = '22'
    DEFICIENCIA_AUDITIVA_VISUAL_TOTAL = '222'
    DEFICIENCIA_FISICA = '3'
    DEFICIENCIA_MENTAL = '4'
    DEFICIENCIA_MULTIPLA = '5'
    DEFICIENCIA_CONDUTAS_TIPICAS = '6'
    OUTRAS_CONDICOES = '8'
    TIPO_NECESSIDADE_ESPECIAL_CHOICES = [
        [DEFICIENCIA_VISUAL, 'Baixa Visão'],
        [DEFICIENCIA_VISUAL_TOTAL, 'Cegueira'],
        [DEFICIENCIA_AUDITIVA, 'Deficiência Auditiva'],
        [DEFICIENCIA_FISICA, 'Deficiência Física'],
        [DEFICIENCIA_MENTAL, 'Deficiência Intelectual'],
        [DEFICIENCIA_MULTIPLA, 'Deficiência Múltipla'],
        [DEFICIENCIA_AUDITIVA_TOTAL, 'Surdez'],
        [DEFICIENCIA_AUDITIVA_VISUAL_TOTAL, 'Surdocegueira'],
    ]

    AUTISMO_INFANTIL = '1'
    SINDROME_ASPERGER = '2'
    SINDROME_DE_RETT = '3'
    TRANSTORNO_DESINTEGRATIVO_DA_INFANCIA = '4'
    TIPO_TRANSTORNO_CHOICES = [
        [AUTISMO_INFANTIL, 'Autismo'],
        [SINDROME_ASPERGER, 'Síndrome de Asperger'],
        [SINDROME_DE_RETT, 'Síndrome de Rett'],
        [TRANSTORNO_DESINTEGRATIVO_DA_INFANCIA, 'Transtorno Desintegrativo da Infância'],
    ]

    MUNICIPAL = '1'
    ESTADUAL = '2'
    PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES = [[MUNICIPAL, 'Municipal'], [ESTADUAL, 'Estadual']]

    VANS_WV = '1'
    KOMBI_MICRO_ONIBUS = '2'
    ONIBUS = '3'
    BICICLETA = '4'
    TRACAO_ANIMAL = '5'
    OUTRO_VEICULO_RODOVIARIO = '6'
    AQUAVIARIO_ATE_5 = '7'
    AQUAVIARIO_ENTRE_5_A_15 = '8'
    AQUALVIARIO_ENTRE_15_E_35 = '9'
    AQUAVIARIO_ACIMA_DE_35 = '10'
    TREM = '11'
    TIPO_VEICULO_CHOICES_FOR_FORM = [
        [
            'Rodoviário',
            [
                [VANS_WV, 'Vans/WV'],
                [KOMBI_MICRO_ONIBUS, 'Kombi Micro-Ônibus'],
                [ONIBUS, 'Ônibus'],
                [BICICLETA, 'Bicicleta'],
                [TRACAO_ANIMAL, 'Tração Animal'],
                [OUTRO_VEICULO_RODOVIARIO, 'Outro tipo de veículo rodoviário'],
            ],
        ],
        [
            'Aquaviário',
            [
                [AQUAVIARIO_ATE_5, 'Capacidade de até 5 alunos'],
                [AQUAVIARIO_ENTRE_5_A_15, 'Capacidade entre 5 a 15 alunos'],
                [AQUALVIARIO_ENTRE_15_E_35, 'Capacidade entre 15 e 35 alunos'],
                [AQUAVIARIO_ACIMA_DE_35, 'Capacidade acima de 35 alunos'],
            ],
        ],
        ['Ferroviário', [[TREM, 'Trem/Metrô']]],
    ]

    TIPO_VEICULO_CHOICES = [
        [VANS_WV, 'Vans/WV'],
        [KOMBI_MICRO_ONIBUS, 'Kombi Micro-Ônibus'],
        [ONIBUS, 'Ônibus'],
        [BICICLETA, 'Bicicleta'],
        [TRACAO_ANIMAL, 'Tração Animal'],
        [OUTRO_VEICULO_RODOVIARIO, 'Outro tipo de veículo rodoviário'],
        [AQUAVIARIO_ATE_5, 'Capacidade de até 5 alunos'],
        [AQUAVIARIO_ENTRE_5_A_15, 'Capacidade entre 5 a 15 alunos'],
        [AQUALVIARIO_ENTRE_15_E_35, 'Capacidade entre 15 e 35 alunos'],
        [AQUAVIARIO_ACIMA_DE_35, 'Capacidade acima de 35 alunos'],
        [TREM, 'Trem/Metrô'],
    ]

    SUPERDOTADO = '1'
    SUPERDOTACAO_CHOICES = [[SUPERDOTADO, 'Altas habilidades/Superdotação']]

    ORDENAR_HISTORICO_POR_PERIODO_LETIVO = 1
    ORDENAR_HISTORICO_POR_PERIODO_MATRIZ = 2
    ORDENAR_HISTORICO_POR_COMPONENTE = 3

    # Managers
    objects = AlunoManager()
    locals = AlunoLocalManager()
    com_matriz = AlunosComMatrizManager()
    ativos = AlunosAtivosManager()
    caracterizados = AlunosCaracterizadosManager()
    nao_fic = AlunosNaoFICManager()
    fic = AlunosFICManager()
    locals_uo = FiltroUnidadeOrganizacionalManager('curso_campus__diretoria__setor__uo')
    locals_diretoria = FiltroUnidadeOrganizacionalManager('curso_campus__diretoria')

    # Fields
    codigo_academico = models.IntegerField(null=True, db_index=True)
    codigo_academico_pf = models.IntegerField('Cód. Acadêmico Pessoa Física', null=True)
    matricula = models.CharFieldPlus('Matrícula', max_length=255, db_index=True)
    foto = ImageWithThumbsField(storage=get_overwrite_storage(), use_id_for_name=True, upload_to='alunos', sizes=((75, 100), (150, 200)), null=True, blank=True)
    pessoa_fisica = models.ForeignKeyPlus('rh.PessoaFisica', verbose_name='Pessoa Física', related_name='aluno_edu_set')
    estado_civil = models.CharFieldPlus(choices=ESTADO_CIVIL_CHOICES, null=True)
    numero_dependentes = models.PositiveIntegerFieldPlus('Número de Dependentes', null=True)

    # endereco
    logradouro = models.CharFieldPlus(max_length=255, verbose_name='Logradouro', null=True)
    numero = models.CharFieldPlus(max_length=255, verbose_name='Número', null=True)
    complemento = models.CharFieldPlus(max_length=255, verbose_name='Complemento', null=True, blank=True)
    bairro = models.CharFieldPlus(max_length=255, verbose_name='Bairro', null=True)
    cep = models.CharFieldPlus(max_length=255, verbose_name='CEP', null=True, blank=True)
    cidade = models.ForeignKeyPlus('edu.Cidade', verbose_name='Cidade', null=True)
    tipo_zona_residencial = models.CharFieldPlus(choices=TIPO_ZONA_RESIDENCIAL_CHOICES, verbose_name='Zona Residencial', null=True, blank=False)

    # endereco profissional
    logradouro_profissional = models.CharFieldPlus(max_length=255, verbose_name='Logradouro Profissional', null=True, blank=True)
    numero_profissional = models.CharFieldPlus(max_length=255, verbose_name='Número Profissional', null=True, blank=True)
    complemento_profissional = models.CharFieldPlus(max_length=255, verbose_name='Complemento Profissional', null=True, blank=True)
    bairro_profissional = models.CharFieldPlus(max_length=255, verbose_name='Bairro Profissional', null=True, blank=True)
    cep_profissional = models.CharFieldPlus(max_length=255, verbose_name='CEP Profissional', null=True, blank=True)
    cidade_profissional = models.ForeignKeyPlus('edu.Cidade', verbose_name='Cidade Profissional', null=True, related_name='aluno_cidade_profissional_set')
    tipo_zona_residencial_profissional = models.CharFieldPlus(choices=TIPO_ZONA_RESIDENCIAL_CHOICES, verbose_name='Zona Residencial Profissional', null=True, blank=True)
    telefone_profissional = models.CharFieldPlus(max_length=255, verbose_name='Telefone Profissional', null=True, blank=True)

    # dados familiares
    nome_pai = models.CharFieldPlus(max_length=255, verbose_name='Nome do Pai', null=True, blank=True)
    estado_civil_pai = models.CharFieldPlus(choices=ESTADO_CIVIL_CHOICES, null=True, blank=True)
    pai_falecido = models.BooleanField(verbose_name='Pai é falecido?', default=False)
    nome_mae = models.CharFieldPlus(max_length=255, verbose_name='Nome da Mãe', null=True, blank=False)
    estado_civil_mae = models.CharFieldPlus(choices=ESTADO_CIVIL_CHOICES, null=True, blank=True)
    mae_falecida = models.BooleanField(verbose_name='Mãe é falecida?', default=False)
    responsavel = models.CharFieldPlus(max_length=255, verbose_name='Nome do Responsável', null=True, blank=True)
    email_responsavel = models.CharFieldPlus(max_length=255, verbose_name='Email do Responsável', null=True, blank=True)
    parentesco_responsavel = models.CharFieldPlus(verbose_name='Parentesco do Responsável', choices=PARENTESCO_CHOICES, null=True, blank=True)
    cpf_responsavel = models.BrCpfField(verbose_name='CPF do Responsável', null=True, blank=True)
    autorizacao_carteira_estudantil = models.BooleanField(
        verbose_name='Autorização para Emissão da Carteira Estudantil',
        help_text='O aluno autoriza o envio de seus dados pessoais para o Sistema Brasileiro de Educação (SEB) para fins de emissão da carteira de estudante digital de acordo com a Medida Provisória Nº 895, de 6 de setembro de 2019',
        default=False,
    )

    # contato
    telefone_principal = models.CharFieldPlus(max_length=255, verbose_name='Telefone Principal', null=True, blank=True)
    telefone_secundario = models.CharFieldPlus(max_length=255, verbose_name='Telefone Secundário', null=True, blank=True)
    telefone_adicional_1 = models.CharFieldPlus(max_length=255, verbose_name='Telefone do Responsável', null=True, blank=True)
    telefone_adicional_2 = models.CharFieldPlus(max_length=255, verbose_name='Telefone do Responsável', null=True, blank=True)
    facebook = models.URLField('Facebook', blank=True, null=True)
    instagram = models.URLField('Instagram', blank=True, null=True)
    twitter = models.URLField('Twitter', blank=True, null=True)
    linkedin = models.URLField('Linkedin', blank=True, null=True)
    skype = models.CharFieldPlus('Skype', blank=True, null=True)

    # outras informacoes
    tipo_sanguineo = models.CharFieldPlus(max_length=255, verbose_name='Tipo Sanguíneo', null=True, blank=True, choices=TIPO_SANGUINEO_CHOICES)
    nacionalidade = models.CharFieldPlus(max_length=255, verbose_name='Nacionalidade', null=True, choices=TIPO_NACIONALIDADE_CHOICES)
    passaporte = models.CharFieldPlus(max_length=50, verbose_name='Nº do Passaporte', default='')
    pais_origem = models.ForeignKeyPlus('edu.Pais', verbose_name='País de Origem', null=True, blank=True, help_text='Obrigatório para estrangeiros')
    naturalidade = models.ForeignKeyPlus(
        'edu.Cidade',
        verbose_name='Naturalidade',
        null=True,
        blank=True,
        related_name='aluno_naturalidade_set',
        help_text='Cidade em que o aluno nasceu. Obrigatório para brasileiros',
    )

    tipo_necessidade_especial = models.CharFieldPlus(verbose_name='Tipo de Necessidade Especial', null=True, blank=True, choices=TIPO_NECESSIDADE_ESPECIAL_CHOICES)
    tipo_transtorno = models.CharFieldPlus(verbose_name='Tipo de Transtorno', null=True, blank=True, choices=TIPO_TRANSTORNO_CHOICES)
    superdotacao = models.CharFieldPlus(verbose_name='Superdotação', null=True, blank=True, choices=SUPERDOTACAO_CHOICES)

    # dados escolares
    nivel_ensino_anterior = models.ForeignKeyPlus('edu.NivelEnsino', null=True, blank=True, on_delete=models.CASCADE)
    tipo_instituicao_origem = models.CharFieldPlus(max_length=255, verbose_name='Tipo de Instituição', null=True, choices=TIPO_INSTITUICAO_ORIGEM_CHOICES, blank=True)
    nome_instituicao_anterior = models.CharFieldPlus(max_length=255, verbose_name='Nome da Instituição', null=True, blank=True)
    ano_conclusao_estudo_anterior = models.ForeignKeyPlus(
        Ano, verbose_name='Ano de Conclusão', null=True, related_name='aluno_ano_conclusao_set', blank=True, on_delete=models.CASCADE
    )
    habilitacao_pedagogica = models.CharFieldPlus(max_length=255, verbose_name='Habilitação para Curso de Formação Pedagógica', null=True, blank=True)

    # rg
    numero_rg = models.CharFieldPlus(max_length=255, verbose_name='Número do RG', null=True, blank=True)
    uf_emissao_rg = models.ForeignKeyPlus('edu.Estado', verbose_name='Estado Emissor', null=True, blank=True, related_name='aluno_emissor_rg_set')
    orgao_emissao_rg = models.ForeignKeyPlus('edu.OrgaoEmissorRg', verbose_name='Orgão Emissor', null=True, blank=True)
    data_emissao_rg = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    # titulo_eleitor
    numero_titulo_eleitor = models.CharFieldPlus(max_length=255, verbose_name='Título de Eleitor', null=True, blank=True)
    zona_titulo_eleitor = models.CharFieldPlus(max_length=255, verbose_name='Zona', null=True, blank=True)
    secao = models.CharFieldPlus(max_length=255, verbose_name='Seção', null=True, blank=True)
    data_emissao_titulo_eleitor = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    uf_emissao_titulo_eleitor = models.ForeignKeyPlus(
        'edu.Estado', verbose_name='Estado Emissor', null=True, blank=True, related_name='aluno_emissor_titulo_eleitor_set', on_delete=models.CASCADE
    )
    # carteira de reservista
    numero_carteira_reservista = models.CharFieldPlus(max_length=255, verbose_name='Número da Carteira de Reservista', null=True, blank=True)
    regiao_carteira_reservista = models.CharFieldPlus(max_length=255, verbose_name='Região', null=True, blank=True)
    serie_carteira_reservista = models.CharFieldPlus(max_length=255, verbose_name='Série', null=True, blank=True)
    estado_emissao_carteira_reservista = models.ForeignKeyPlus(
        'edu.Estado', verbose_name='Estado Emissor', null=True, blank=True, related_name='aluno_emissor_carteira_reservista_set', on_delete=models.CASCADE
    )
    ano_carteira_reservista = models.PositiveIntegerField(verbose_name='Ano', null=True, blank=True)
    # certidao_civil
    tipo_certidao = models.CharFieldPlus(max_length=255, verbose_name='Tipo de Certidão', null=True, blank=True, choices=TIPO_CERTIDAO_CHOICES)
    cartorio = models.ForeignKeyPlus('edu.Cartorio', verbose_name='Cartório', null=True, blank=True)
    numero_certidao = models.CharFieldPlus(max_length=255, verbose_name='Número de Termo', null=True, blank=True)
    folha_certidao = models.CharFieldPlus(max_length=255, verbose_name='Folha', null=True, blank=True)
    livro_certidao = models.CharFieldPlus(max_length=255, verbose_name='Livro', null=True, blank=True)
    data_emissao_certidao = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    matricula_certidao = models.CharFieldPlus(max_length=255, verbose_name='Matrícula', null=True, blank=True)
    # dados da matrícula
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano de Ingresso', on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField(verbose_name='Período de Ingresso', choices=PERIODO_LETIVO_CHOICES)
    data_matricula = models.DateTimeFieldPlus(verbose_name='Data da Matrícula', auto_now_add=True)
    turno = models.ForeignKeyPlus('edu.Turno', verbose_name='Turno', null=True, on_delete=models.CASCADE)
    forma_ingresso = models.ForeignKeyPlus('edu.FormaIngresso', null=True, verbose_name='Forma de Ingresso', on_delete=models.CASCADE)
    cota_sistec = models.CharFieldPlus(max_length=255, verbose_name='Cota SISTEC', null=True, choices=COTA_SISTEC_CHOICES, blank=True)
    cota_mec = models.CharFieldPlus(max_length=255, verbose_name='Cota MEC', null=True, choices=COTA_MEC_CHOICES, blank=True)
    possui_convenio = models.BooleanField(verbose_name='Possui Convênio', null=True)
    convenio = models.ForeignKeyPlus('edu.Convenio', null=True, blank=True, verbose_name='Convênio', on_delete=models.CASCADE)
    data_conclusao_intercambio = models.DateFieldPlus(verbose_name='Conclusão do Intercâmbio', null=True, blank=True)
    curso_campus = models.ForeignKeyPlus('edu.CursoCampus', null=True, verbose_name='Curso')
    habilitacao = models.ForeignKeyPlus('edu.Habilitacao', verbose_name='Habilitação', null=True, blank=True)
    matriz = models.ForeignKeyPlus('edu.Matriz', null=True, verbose_name='Matriz')
    situacao = models.ForeignKeyPlus('edu.SituacaoMatricula', verbose_name='Situação', on_delete=models.CASCADE)
    numero_pasta = models.CharFieldPlus(max_length=255, verbose_name='Número da Pasta', null=True, blank=True)
    linha_pesquisa = models.ForeignKeyPlus('edu.LinhaPesquisa', verbose_name='Linha de Pesquisa', null=True, blank=True)
    aluno_especial = models.BooleanField(verbose_name='Aluno Especial?', default=False)

    ira = models.DecimalFieldPlus(verbose_name='I.R.A', default=0, null=True)
    dt_conclusao_curso = models.DateField(null=True, blank=True, verbose_name='Data de Conclusão do Curso')
    data_expedicao_diploma = models.DateField(null=True, blank=True, verbose_name='Data de Expedição do Diploma')
    data_colacao_grau = models.DateField(null=True, blank=True, verbose_name='Data da Colação de Grau')
    ano_let_prev_conclusao = models.IntegerField(null=True, blank=True, verbose_name='Ano Prev. Conclusão')
    ano_conclusao = models.IntegerField(null=True, blank=True, verbose_name='Ano Conclusão')
    renda_per_capita = models.DecimalField(
        null=True,
        max_digits=15,
        decimal_places=2,
        verbose_name='Renda Per Capita',
        help_text='Número de salários mínimos ganhos pelos integrantes da família dividido pelo número de integrantes',
    )

    candidato_vaga = models.ForeignKeyPlus('processo_seletivo.CandidatoVaga', verbose_name='Candidato Vaga', null=True, blank=True)
    periodo_atual = models.IntegerField('Período Atual', null=True, blank=True)

    observacao_historico = models.TextField('Observação para o Histórico', null=True, blank=True)
    observacao_matricula = models.TextField('Observação da Matrícula', null=True, blank=True)

    polo = models.ForeignKeyPlus('edu.Polo', verbose_name='Polo EAD', null=True, blank=True, on_delete=models.CASCADE)

    comp_obrigatorios_pendentes = models.BooleanField(default=False)
    comp_optativos_pendentes = models.BooleanField(default=False)
    comp_eletivos_pendentes = models.BooleanField(default=False)
    pratica_profissional_pendente = models.BooleanField(default=False)
    seminarios_pendentes = models.BooleanField(default=False)
    atividades_complementares_pendentes = models.BooleanField(default=False)
    tcc_pendente = models.BooleanField(default=False)
    enade_pendente = models.BooleanField(default=False)
    colacao_grau_pendente = models.BooleanField(default=False)

    data_integralizacao = models.DateTimeFieldPlus('Data da Integralização', null=True, blank=True)
    ano_letivo_integralizacao = models.ForeignKeyPlus(
        'comum.Ano', verbose_name='Ano Letivo da Integralização', null=True, blank=True, related_name='aluno_ano_letivo_integralizacao', on_delete=models.CASCADE
    )
    periodo_letivo_integralizacao = models.PositiveIntegerField(verbose_name='Periodo Letivo da Integralização', choices=PERIODO_LETIVO_CHOICES, null=True, blank=True)

    email_academico = models.EmailField('Email Acadêmico', blank=True)
    email_qacademico = models.EmailField('Email Q-Acadêmico', blank=True)
    email_google_classroom = models.EmailField('Email do Google Classroom', blank=True)
    alterado_em = models.DateTimeFieldPlus('Data de Alteração', auto_now=True, null=True, blank=True)

    csf = models.BooleanField(verbose_name='Ciência sem Fronteiras', default=False)

    # caracterizacao_socioeconomica
    documentada = models.BooleanField('Doc. Entregue', default=False)
    data_documentacao = models.DateTimeField('Data de Entrega da Documentação', null=True)

    # pendencias
    pendencia_tcc = models.BooleanField(verbose_name='Registro de TCC', null=True)
    pendencia_enade = models.BooleanField(verbose_name='Registro do ENADE', null=True)
    pendencia_pratica_profissional = models.BooleanField(verbose_name='Registro de Prática Profissional', null=True)
    pendencia_colacao_grau = models.BooleanField(verbose_name='Colação de Grau', null=True)
    pendencia_ch_atividade_complementar = models.BooleanField(verbose_name='Atividades Complementares', null=True)
    pendencia_ch_tcc = models.BooleanField(verbose_name='Caga-Horária de TCC', null=True)
    pendencia_ch_pratica_profissional = models.BooleanField(verbose_name='Caga-Horária de Prática Profissional', null=True)
    pendencia_ch_atividades_aprofundamento = models.BooleanField(verbose_name='Caga-Horária de Aprofundamento', null=True)
    pendencia_ch_atividades_extensao = models.BooleanField(verbose_name='Caga-Horária de Extensão', null=True)
    pendencia_ch_seminario = models.BooleanField(verbose_name='Caga-Horária de Seminário', null=True)
    pendencia_ch_eletiva = models.BooleanField(verbose_name='Caga-Horária Eletiva', null=True)
    pendencia_ch_optativa = models.BooleanField(verbose_name='Caga-Horária Optativa', null=True)
    pendencia_ch_obrigatoria = models.BooleanField(verbose_name='Caga-Horária Obrigatória', null=True)
    pendencia_ch_pratica_como_componente = models.BooleanField(verbose_name='Carga-Horária Prática como Componente Curricular', null=True)
    pendencia_ch_visita_tecnica = models.BooleanField(verbose_name='Carga-Horária Visita Técnica/Aula de Campo', null=True)

    # CH de prática como componente curricular e visita/técnica de aulas registradas em diários
    ch_aulas_pcc = models.IntegerField(verbose_name='CH de Aulas de PCC', default=0, help_text='Prática como componente curricular')
    ch_aulas_visita_tecnica = models.IntegerField(verbose_name='CH de Aulas de VT/AC', default=0, help_text='Visita técnica / aula de campo')

    # saúde
    cartao_sus = models.CharFieldPlus('Cartão SUS', null=True, blank=True)

    codigo_educacenso = models.CharFieldPlus('Código EDUCACENSO', null=True, blank=True)

    nis = models.CharFieldPlus('NIS', null=True, help_text='Número de Identificação Social', blank=True)

    poder_publico_responsavel_transporte = models.CharFieldPlus(
        'Poder Público Responsável pelo Transporte Escolar', choices=PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, null=True, blank=True
    )
    tipo_veiculo = models.CharFieldPlus('Tipo de Veículo Utilizado no Transporte Escolar', choices=TIPO_VEICULO_CHOICES_FOR_FORM, null=True, blank=True)
    vinculos = GenericRelation('comum.Vinculo', related_query_name='alunos', object_id_field='id_relacionamento', content_type_field='tipo_relacionamento')

    percentual_ch_cumprida = models.DecimalFieldPlus('C.H. Cumprida (%)', null=True)

    class Meta:
        ordering = ('pessoa_fisica__nome',)
        verbose_name = 'Aluno'
        verbose_name_plural = 'Alunos'

        permissions = (
            ('emitir_diploma', 'Pode emitir diploma de Aluno'),
            ('emitir_boletim', 'Pode emitir boletim de Aluno'),
            ('emitir_historico', 'Pode emitir histórico de Aluno'),
            ('efetuar_matricula', 'Pode efetuar matricula de Aluno'),
            ('pode_editar_caracterizacao', 'Pode editar caracterização'),
            ('pode_sincronizar_dados', 'Pode sincronizar dados'),
            ('gerar_relatorio', 'Pode gerar relatórios'),
            ('pode_ver_chave_acesso_pais', 'Pode ver chave de acesso dos pais'),
            ('report_dependentes_reprovados', 'Pode gerar relatório de dependentes/reprovados'),
            ('importar_aluno', 'Pode importar aluno de sistemas legados'),
            ('change_foto_aluno', 'Pode editar foto do aluno'),
            ('view_dados_academicos', 'Pode visualizar dados acadêmicos do aluno'),
            ('view_dados_pessoais', 'Pode visualizar dados pessoais do aluno'),
        )

    def get_documentos_obrigatorios(self):
        documentos_obrigatorios = []
        if self.curso_campus.modalidade.grupoarquivoobrigatorio_set.exists():
            grupos_arquivos = self.curso_campus.modalidade.grupoarquivoobrigatorio_set.all()
            aluno_arquivos = self.alunoarquivo_set.filter(tipo__isnull=False).filter(validado=True)
            for grupo_arquivos in grupos_arquivos:
                tipos_obrigatorios_grupo = grupo_arquivos.tipos.all().distinct()
                for arquivo_aluno in aluno_arquivos:
                    if arquivo_aluno.tipo_id and arquivo_aluno.tipo in tipos_obrigatorios_grupo:
                        if arquivo_aluno not in documentos_obrigatorios:
                            documentos_obrigatorios.append(arquivo_aluno)
                            tipos_obrigatorios_grupo = tipos_obrigatorios_grupo.exclude(id=arquivo_aluno.tipo.id)
                        else:
                            for arquivo_obrigatorio in documentos_obrigatorios:
                                if arquivo_obrigatorio.tipo == arquivo_aluno.tipo and arquivo_aluno.data_hora_upload > arquivo_obrigatorio.data_hora_upload:
                                    documentos_obrigatorios.append(arquivo_aluno)
                                    tipos_obrigatorios_grupo = tipos_obrigatorios_grupo.exclude(
                                        id=arquivo_aluno.tipo.id)
        return documentos_obrigatorios

    def possui_todos_documentos_obrigatorios(self):
        for grupo in self.curso_campus.modalidade.grupoarquivoobrigatorio_set.all().distinct():
            if not self.alunoarquivo_set.filter(validado=True).filter(tipo__in=grupo.tipos.all()).exists():
                return False
        return True

    def requer_autenticacao_sistec_para_emissao_diploma(self):
        return self.curso_campus.modalidade_id in (Modalidade.INTEGRADO, Modalidade.INTEGRADO_EJA, Modalidade.CONCOMITANTE, Modalidade.SUBSEQUENTE)

    @property
    def papeis(self):
        return self.pessoa_fisica.papel_set.all()

    @property
    def papeis_ativos(self):
        hoje = datetime.date.today()
        papeis_datas_menores_hoje = self.pessoa_fisica.papel_set.filter(data_inicio__lte=hoje)
        return papeis_datas_menores_hoje.filter(data_fim__isnull=True) | papeis_datas_menores_hoje.filter(data_fim__gte=hoje)

    @property
    def matriz_curso(self):
        return self.matriz_id and MatrizCurso.objects.get(curso_campus=self.curso_campus_id, matriz=self.matriz_id) or None

    @cached_property
    def setor(self):
        return self.curso_campus.diretoria.setor

    def get_observacoes(self):
        return self.observacao_set.all()

    def get_pasta_cra(self):
        registros = self.registroemissaodiploma_set.all()
        pastas = []
        if registros.exists():
            for registro in registros:
                pastas.append(registro.pasta)
        return pastas

    def cumpriu_requisito_tcc(self):
        if self.matriz.exige_tcc and self.pendencia_tcc is not None:
            return not self.pendencia_tcc and not self.situacao_id == SituacaoMatricula.AGUARDANDO_COLACAO_DE_GRAU
        return None

    def cumpriu_requisito_ch_seminario(self):
        if self.get_ch_componentes_seminario_esperada() and self.pendencia_ch_seminario is not None:
            return not self.pendencia_ch_seminario and not self.situacao_id == SituacaoMatricula.AGUARDANDO_SEMINARIO
        return None

    def cumpriu_requisito_enade(self):
        if self.curso_campus.exige_enade and self.pendencia_enade is not None:
            return not self.pendencia_enade and not self.situacao_id == SituacaoMatricula.AGUARDANDO_ENADE
        return None

    def cumpriu_requisito_pratica_profissional(self):
        if self.pendencia_pratica_profissional is not None:
            return not self.pendencia_pratica_profissional
        return None

    def cumpriu_requisito_colacao_grau(self):
        if self.pendencia_colacao_grau is not None:
            return not self.pendencia_colacao_grau
        return None

    def cumpriu_requisito_ch_atividade_complementar(self):
        if self.pendencia_ch_atividade_complementar is not None:
            return not self.pendencia_ch_atividade_complementar
        return None

    def cumpriu_requisito_ch_tcc(self):
        if self.pendencia_ch_tcc is not None:
            return not self.pendencia_ch_tcc
        return None

    def cumpriu_requisito_ch_pratica_profissional(self):
        if self.pendencia_ch_pratica_profissional is not None:
            return not self.pendencia_ch_pratica_profissional
        return None

    def cumpriu_requisito_ch_atividades_aprofundamento(self):
        if self.pendencia_ch_atividades_aprofundamento is not None:
            return not self.pendencia_ch_atividades_aprofundamento
        return None

    def cumpriu_requisito_ch_atividades_extensao(self):
        if self.pendencia_ch_atividades_extensao is not None:
            return not self.pendencia_ch_atividades_extensao
        return None

    def cumpriu_requisito_ch_eletiva(self):
        if self.pendencia_ch_eletiva is not None:
            return not self.pendencia_ch_eletiva
        return None

    def cumpriu_requisito_ch_optativa(self):
        if self.pendencia_ch_optativa is not None:
            return not self.pendencia_ch_optativa
        return None

    def cumpriu_requisito_ch_obrigatoria(self):
        if self.pendencia_ch_obrigatoria is not None:
            return not self.pendencia_ch_obrigatoria
        return None

    def cumpriu_requisito_trancamento_voluntario(self):
        """
        Verifica se o aluno pode realizar Trancamento Voluntário.

        Legislação (Organização Didática):
        Art. 219. O trancamento voluntário somente será autorizado após a integralização de todos os componentes
        curriculares do primeiro período do curso.
            § 1º. Para os estudantes com admissão por reingresso e transferência, o trancamento voluntário só poderá
               ser concedido quando for integralizado o período em que foi posicionado após a realização do
               aproveitamento dos estudos.
        """
        matricula_inicial = self.get_matriculas_periodo(orderbyDesc=False).first()
        periodo_inicial = matricula_inicial and matricula_inicial.periodo_matriz or 1
        ids_componentes_periodo_inicial = set(self.matriz.get_ids_componentes(periodos=periodo_inicial))
        ids_componentes_cumpridos = set(self.get_ids_componentes_cumpridos(ids=ids_componentes_periodo_inicial))

        return len(ids_componentes_periodo_inicial - ids_componentes_cumpridos) == 0

    def em_horario_de_aula(self, data, hora):
        if not hasattr(self, '_mp'):
            mp = self.get_matricula_periodo_na_data(data)
            setattr(self, '_mp', mp)
        else:
            mp = getattr(self, '_mp')
        if mp:
            return mp.em_horario_de_aula(data.weekday() + 1, hora)
        else:
            return False

    def get_mes_ano_processo_seletivo(self):
        meses = ('Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro')
        mes_ano_processo_seletivo = f'{meses[self.data_matricula.month - 1]} de {self.data_matricula.year}'
        if self.candidato_vaga:
            data_encerramento = self.candidato_vaga.oferta_vaga.oferta_vaga_curso.edital.data_encerramento
            if data_encerramento:
                mes_ano_processo_seletivo = f'{meses[data_encerramento.month - 1]} de {data_encerramento.year}'
        return mes_ano_processo_seletivo

    def get_matricula_periodo_na_data(self, data):
        qs = (
            Diario.objects.filter(calendario_academico__data_inicio__lte=data, calendario_academico__data_fim__gte=data, matriculadiario__matricula_periodo__aluno=self)
            .values_list('matriculadiario__matricula_periodo', flat=True)
            .order_by('matriculadiario__matricula_periodo')
            .distinct()
        )
        return qs.exists() and MatriculaPeriodo.objects.get(pk=qs[0]) or None

    def get_ch_componentes_com_percentual_ch_cumprida(self, matricula_periodo=None):
        ch_componentes_regulares_obrigatorios_cumprida = self.get_ch_componentes_regulares_obrigatorios_cumprida(matricula_periodo)
        ch_componentes_regulares_optativos_cumprida = self.get_ch_componentes_regulares_optativos_cumprida(matricula_periodo)
        ch_componentes_seminario_cumprida = self.get_ch_componentes_seminario_cumprida(matricula_periodo)
        ch_componentes_pratica_profissional_cumprida = self.get_ch_componentes_pratica_profissional_cumprida(matricula_periodo)
        ch_atividades_aprofundamento_cumprida = self.get_ch_atividade_aprofundamento_cumprida(matricula_periodo)
        ch_atividades_extensao_cumprida = self.get_ch_atividade_extensao_cumprida(matricula_periodo)
        ch_componentes_tcc_cumprida = self.get_ch_componentes_tcc_cumprida(matricula_periodo)
        ch_atividades_complementares_cumprida = self.get_ch_atividades_complementares_cumprida(matricula_periodo=matricula_periodo)
        ch_pratica_como_componente_cumprida = self.get_ch_componentes_pratica_como_componente_cumprida(matricula_periodo=matricula_periodo)
        ch_visita_tecnica_cumprida = self.get_ch_componentes_visita_tecnica_cumprida(matricula_periodo=matricula_periodo)

        ch_cumprida = 0
        ch_cumprida += (
            ch_componentes_regulares_obrigatorios_cumprida > self.matriz.ch_componentes_obrigatorios
            and self.matriz.ch_componentes_obrigatorios
            or ch_componentes_regulares_obrigatorios_cumprida
        )
        ch_cumprida += (
            ch_componentes_regulares_optativos_cumprida > self.matriz.ch_componentes_optativos
            and self.matriz.ch_componentes_optativos
            or ch_componentes_regulares_optativos_cumprida
        )
        ch_cumprida += ch_componentes_seminario_cumprida > self.matriz.ch_seminarios and self.matriz.ch_seminarios or ch_componentes_seminario_cumprida
        ch_cumprida += (
            ch_componentes_pratica_profissional_cumprida > self.matriz.ch_pratica_profissional
            and self.matriz.ch_pratica_profissional
            or ch_componentes_pratica_profissional_cumprida
        )
        ch_cumprida += (
            ch_atividades_aprofundamento_cumprida > self.matriz.ch_atividades_aprofundamento and self.matriz.ch_atividades_aprofundamento or ch_atividades_aprofundamento_cumprida
        )
        ch_cumprida += ch_atividades_extensao_cumprida > self.matriz.ch_atividades_extensao and self.matriz.ch_atividades_extensao or ch_atividades_extensao_cumprida
        ch_cumprida += ch_componentes_tcc_cumprida > self.matriz.ch_componentes_tcc and self.matriz.ch_componentes_tcc or ch_componentes_tcc_cumprida
        ch_cumprida += (
            ch_atividades_complementares_cumprida > self.matriz.ch_atividades_complementares and self.matriz.ch_atividades_complementares or ch_atividades_complementares_cumprida
        )
        ch_cumprida += min(ch_pratica_como_componente_cumprida, self.matriz.ch_pratica_como_componente)
        ch_cumprida += min(ch_visita_tecnica_cumprida, self.matriz.ch_visita_tecnica)

        ch_total_prevista = self.matriz.get_carga_horaria_total_prevista()
        percentual_ch_cumprida = round(ch_cumprida * 100.0 / float(ch_total_prevista), 2) if ch_total_prevista else 0
        percentual_ch_cumprida = percentual_ch_cumprida > 100 and 100 or percentual_ch_cumprida

        return (
            ch_componentes_regulares_obrigatorios_cumprida,
            ch_componentes_regulares_optativos_cumprida,
            ch_componentes_seminario_cumprida,
            ch_componentes_pratica_profissional_cumprida,
            ch_componentes_tcc_cumprida,
            ch_atividades_complementares_cumprida,
            ch_atividades_aprofundamento_cumprida,
            ch_atividades_extensao_cumprida,
            ch_pratica_como_componente_cumprida,
            ch_visita_tecnica_cumprida,
            percentual_ch_cumprida,
        )

    def get_percentual_carga_horaria_cumprida(self, matricula_periodo=None):
        _, _, _, _, _, _, _, _, _, _, percentual_ch_cumprida = self.get_ch_componentes_com_percentual_ch_cumprida(matricula_periodo)
        return round(percentual_ch_cumprida, 2)

    def atualizar_percentual_ch_cumprida(self):
        percentual_ch_cumprida = 0
        if self.matriz:
            for mp in self.get_matriculas_periodo(orderbyDesc=False):
                if percentual_ch_cumprida < 100:
                    percentual_ch_cumprida = round(percentual_ch_cumprida + self.get_percentual_carga_horaria_cumprida(mp), 2)
                if percentual_ch_cumprida > 100:
                    percentual_ch_cumprida = 100
                mp.percentual_ch_cumprida = percentual_ch_cumprida
                mp.save()
            if hasattr(self, 'ids_componentes_curriculares_cumpridos'):
                del self.ids_componentes_curriculares_cumpridos
            self.percentual_ch_cumprida = round(self.get_percentual_carga_horaria_cumprida(), 2)
            self.save()

    def get_situacao_sistemica(self):
        situacao = [1, 'Matriculado no Q-Acadêmico']
        if self.matriz:
            if self.data_integralizacao:
                situacao = [2, 'Migrado do Q-Acadêmico para o SUAP']
            else:
                situacao = [3, 'Matriculado no SUAP']
        elif self.is_sica():
            situacao = [1, 'Matriculado no SICA']
        else:
            if self.eh_aluno_minicurso():
                situacao = [4, 'Matriculado no SUAP (Minicurso)']
        return situacao

    def eh_aluno_minicurso(self):
        return self.turmaminicurso_set.exists()

    def eh_participante_programa_social(self):
        if self.participacao_set.exists():
            return self.participacao_set.filter(Q(data_termino__isnull=True) | Q(data_termino__gte=datetime.datetime.now().date())).exists()

    def eh_participante_do_programa(self, programa):
        if self.participacao_set.filter(programa=programa).exists():
            return self.participacao_set.filter(programa=programa).filter(Q(data_termino__isnull=True) | Q(data_termino__gte=datetime.datetime.now().date())).exists()

    def get_inscricoes_programas(self):
        if self.inscricao_set.exists():
            resultado = ''
            for inscricao in self.inscricao_set.all():
                resultado = resultado + '<p>{} em {}.</p>'.format(inscricao.programa, inscricao.data_cadastro.strftime('%d/%m/%Y %H:%M'))
            return mark_safe(resultado)
        return ''

    def get_inscricoes_programas_resumido(self):
        if self.inscricao_set.exists():
            resultado = list()
            for inscricao in self.inscricao_set.order_by('programa__tipo_programa'):
                resultado.append(f'{inscricao.programa.tipo_programa}')
            return mark_safe(', '.join(resultado))
        return ''

    def get_situacao_documentacao(self):
        if self.documentada:
            if self.is_documentacao_expirada():
                return mark_safe('<span class="status status-error">Expirada em {}</span>'.format(self.get_expiracao_documentacao().strftime('%d/%m/%Y')))
            else:
                return mark_safe('<span class="status status-success">Entregue em {}</span>'.format(self.data_documentacao.strftime('%d/%m/%Y')))
        elif self.data_documentacao:
            return mark_safe('<span class="status status-alert">Informada em {}</span>'.format(self.data_documentacao.strftime('%d/%m/%Y')))
        else:
            return mark_safe('<span class="status status-error">Não entregue</span>')

    def is_documentacao_expirada(self):
        prazo_expiracao = Configuracao.get_valor_por_chave('ae', 'prazo_expiracao_documentacao')
        total_dias = prazo_expiracao and int(prazo_expiracao) or 365
        return self.data_documentacao and self.data_documentacao < somar_data(datetime.datetime.now(), -total_dias)

    def get_expiracao_documentacao(self):
        if self.data_documentacao:  # IFF: Verificando se data_documentação existe, antes de somá-lo
            prazo_expiracao = Configuracao.get_valor_por_chave('ae', 'prazo_expiracao_documentacao')
            total_dias = prazo_expiracao and int(prazo_expiracao) or 365
            return somar_data(self.data_documentacao, total_dias)

    def get_chave_responsavel(self):
        if self.pessoa_fisica.user:
            try:
                token = Token.objects.get(user=self.pessoa_fisica.user)
            except Token.DoesNotExist:
                token = Token.objects.create(user=self.pessoa_fisica.user)
            return token.key[0:5].lower()
        return None

    def get_dados_bancarios(self, todas=False):
        if 'ae' in settings.INSTALLED_APPS:
            qs = self.dadosbancarios_set.all()
            if not todas:
                qs = qs.exclude(inscricaopasseestudantil__id__isnull=False)
                qs = qs.exclude(inscricaotrabalho__id__isnull=False)
            return qs
        return []

    def get_dados_bancarios_folha_pagamento(self):
        if self.get_dados_bancarios():
            return self.get_dados_bancarios().order_by('-prioritario_servico_social')[0]
        return False

    def get_dados_bancarios_banco(self):
        if self.get_dados_bancarios_folha_pagamento():
            banco = self.get_dados_bancarios_folha_pagamento().instituicao
            return banco.codigo
        return False

    def get_dados_bancarios_numero_agencia(self):
        if self.get_dados_bancarios_folha_pagamento():
            return self.get_dados_bancarios_folha_pagamento().numero_agencia.split("-")[0].replace("/", "").replace("_", "").replace(".", "")
        return False

    def get_dados_bancarios_numero_conta(self):
        if self.get_dados_bancarios_folha_pagamento():
            return self.get_dados_bancarios_folha_pagamento().numero_conta.replace("-", "").replace("/", "").replace("_", "").replace(".", "")
        return False

    def get_participacoes_abertas(self):
        if 'ae' in settings.INSTALLED_APPS:
            Participacao = apps.get_model('ae', 'Participacao')
            hoje = datetime.date.today()
            participacao_aberta = Participacao.objects.filter(aluno=self).filter(Q(data_inicio__lte=hoje), Q(data_termino__isnull=True) | Q(data_termino__gte=hoje))
            texto = ''
            if participacao_aberta.exists():
                for participacao in participacao_aberta:
                    texto += f'{participacao.programa.__str__()}, '
                return texto[:-2]
        return '-'

    def eh_pne(self):
        return bool(self.tipo_necessidade_especial)

    def get_nome(self):
        return self.pessoa_fisica.nome

    def get_nome_social_composto(self):
        if self.pessoa_fisica.nome_social:
            return f'{self.pessoa_fisica.nome_registro} ({self.pessoa_fisica.nome_social})'
        else:
            return self.pessoa_fisica.nome

    def get_componentes_curriculares_por_ids(self, ids_componentes):
        return ComponenteCurricular.objects.filter(matriz=self.matriz, componente__id__in=ids_componentes).order_by('componente__id')

    def get_telefones(self):
        telefones = '-'
        if self.telefone_principal:
            telefones = self.telefone_principal
        if self.telefone_secundario:
            telefones = f'{telefones}, {self.telefone_secundario}'
        if self.telefone_adicional_1:
            telefones = f'{telefones}, {self.telefone_adicional_1}'
        if self.telefone_adicional_2:
            telefones = f'{telefones}, {self.telefone_adicional_2}'
        return telefones

    @staticmethod
    def get_ingressantes_sem_turma(ano_letivo, periodo_letivo, diretoria=None, curso=None):
        ids_diretorias = Diretoria.locals.values_list('id', flat=True)
        ingressantes = Aluno.objects.filter(
            ano_letivo__ano=ano_letivo.ano,
            periodo_letivo=periodo_letivo,
            matriculaperiodo__ano_letivo__ano=ano_letivo.ano,
            matriculaperiodo__periodo_letivo=periodo_letivo,
            matriculaperiodo__turma__isnull=True,
            situacao__id__in=[SituacaoMatricula.MATRICULADO],
            matriculaperiodo__situacao__in=[SituacaoMatriculaPeriodo.MATRICULADO],
        )
        ingressantes = ingressantes.filter(matriz__estrutura__proitec=False, data_integralizacao__isnull=True, matriz__isnull=False, curso_campus__diretoria__id__in=ids_diretorias)

        if diretoria:
            ingressantes = ingressantes.filter(curso_campus__diretoria=diretoria)

        if curso:
            ingressantes = ingressantes.filter(curso_campus=curso)

        return ingressantes

    @staticmethod
    def get_alunos_concluidos_dados_incompletos():
        ids_diretorias = list(Diretoria.locals.values_list('id', flat=True))

        ids_matrizes = list(MatrizCurso.objects.filter(matriz__estrutura__proitec=False, curso_campus__diretoria_id__in=ids_diretorias, curso_campus__ativo=True).values_list('matriz_id', flat=True))

        qs = Aluno.objects.filter(
            Q(
                situacao_id__in=[SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO],
                matriz_id__in=ids_matrizes
            ),
            Q(naturalidade_id__isnull=True) | Q(pessoa_fisica__nascimento_data__isnull=True) | Q(Q(numero_rg=''), ~Q(curso_campus__modalidade_id=Modalidade.FIC))
        )
        return qs.distinct()

    @staticmethod
    def get_alunos_sem_turma(user_coodernador, ano, periodo, curso_id=None):
        qs = Aluno.locals.filter(
            curso_campus__coordenador__username=user_coodernador.username,
            matriculaperiodo__ano_letivo__ano=ano,
            matriz__isnull=False,
            matriculaperiodo__turma__isnull=True,
            situacao__id__in=[SituacaoMatricula.MATRICULADO],
            matriculaperiodo__situacao__in=[SituacaoMatriculaPeriodo.MATRICULADO],
        )
        qs = qs.filter(curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL) | qs.filter(matriculaperiodo__periodo_letivo=periodo).exclude(
            curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL
        )
        qs = qs.filter(matriz__estrutura__tipo_avaliacao__in=(
            EstruturaCurso.TIPO_AVALIACAO_SERIADO, EstruturaCurso.TIPO_AVALIACAO_FIC, EstruturaCurso.TIPO_AVALIACAO_MODULAR
        ))
        if curso_id:
            qs = qs.filter(curso_campus_id=curso_id)
        return qs.distinct()

    def is_concluido_com_dados_incompletos(self):
        return (
            self.matriz
            and self.situacao.id in [SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO]
            and (self.naturalidade is None or self.pessoa_fisica.nascimento_data is None)
        )

    def can_change(self, user):
        return user.has_perm('ae.add_demandaalunoatendida') or perms.tem_permissao_realizar_procedimentos(user, self)

    def can_delete(self, user):
        return self.pode_ser_excluido(user.is_superuser) and perms.realizar_procedimentos_academicos(user, self.curso_campus)

    @atomic()
    def desfazer_migracao(self):
        self.matriz = None
        self.data_integralizacao = None
        self.ano_letivo_integralizacao = None
        self.periodo_letivo_integralizacao = None
        self.save()
        self.atividadecomplementar_set.all().delete()
        self.matriculaperiodo_set.all().update(turma=None)
        RegistroConvocacaoENADE.objects.filter(aluno=self).delete()
        ProjetoFinal.objects.filter(matricula_periodo__aluno=self).delete()
        MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self).delete()
        MatriculaDiario.objects.filter(matricula_periodo__aluno=self).delete()
        PedidoMatricula.objects.filter(matricula_periodo__aluno=self).delete()
        ProcedimentoMatricula.objects.filter(matricula_periodo__aluno=self).delete()
        self.desfazer_migracao_qacademico()

    def desfazer_migracao_qacademico(self):
        from edu.q_academico import DAO

        dao = DAO()
        dao.importar_alunos(self.matricula, False)
        dao.importar_matriculas_periodo(self.matricula, False)
        dao.desfazer_situacao_alunos_integralizados_qacademico(self.matricula)

    @atomic()
    def clonar(self, matriz_curso, forma_ingresso=None, turno=None, data=None):
        # guardando dados

        # === ao clonar um aluno, os dados do e-mail devem ser resetados e transferidos para a nova matrícula ===
        email_academico = self.email_academico
        email_google_classroom = self.email_google_classroom
        self.email_academico = ''
        self.email_google_classroom = ''
        self.save()

        from ldap_backend.models import LdapConf

        ldap_conf = LdapConf.get_active()
        ldap_conf.sync_user(self.pessoa_fisica.username)

        # ========================================================================================================

        matriculas_periodo = self.matriculaperiodo_set.all()
        data_matricula = self.data_matricula
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()
        atividades_complementares = self.atividadecomplementar_set.all()
        ultimo_procedimento_matricula = ProcedimentoMatricula.objects.filter(matricula_periodo__aluno=self).order_by("-id")[0]
        pk = self.id
        # clonando o aluno
        aluno = copy.copy(self)
        aluno.id = None
        aluno.email_academico = email_academico
        aluno.email_google_classroom = email_google_classroom
        aluno.curso_campus = matriz_curso.curso_campus
        aluno.matriz = matriz_curso.matriz
        aluno.ano_letivo = ultima_matricula_periodo.ano_letivo
        aluno.periodo_letivo = ultima_matricula_periodo.periodo_letivo
        prefixo = f'{ultima_matricula_periodo.ano_letivo}{ultima_matricula_periodo.periodo_letivo}{aluno.curso_campus.codigo}'
        aluno.matricula = SequencialMatricula.proximo_numero(prefixo)
        aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL)
        aluno.codigo_academico = None
        aluno.data_integralizacao = None
        aluno.forma_ingresso = forma_ingresso or self.forma_ingresso
        aluno.turno = turno or self.turno
        aluno.save()

        pessoa_fisica = self.pessoa_fisica
        pessoa_fisica.username = aluno.matricula
        pessoa_fisica.id = None
        pessoa_fisica.pk = None
        pessoa_fisica.uuid = uuid.uuid4()
        pessoa_fisica.save()

        aluno.pessoa_fisica = pessoa_fisica
        aluno.data_matricula = data or data_matricula
        aluno.save()

        # salvando no procedimento de matricula a matricula do novo aluno criado
        ultimo_procedimento_matricula.nova_matricula = aluno.matricula
        ultimo_procedimento_matricula.save()

        # clonando as matriculas periodos
        for matricula_periodo in matriculas_periodo:
            nova_matricula_periodo = copy.copy(matricula_periodo)
            nova_matricula_periodo.id = None
            nova_matricula_periodo.aluno = aluno
            nova_matricula_periodo.save()

            # criando os registros do historico
            matricula_periodo.adicionar_registro_historico(nova_matricula_periodo)

        # alterando situacao da ultima matricula periodo do novo aluno para MATRICULADO
        ultima_matricula_periodo = aluno.get_ultima_matricula_periodo()
        ultima_matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.EM_ABERTO)
        ultima_matricula_periodo.turma = None
        ultima_matricula_periodo.save()

        # clonando atividades complementares
        for atividade_complementar in atividades_complementares:
            atividade_complementar.id = None
            atividade_complementar.aluno = aluno
            atividade_complementar.save()

        aluno.atualizar_situacao('Transferência de Curso')

        Aluno.objects.filter(pk=pk).update(email_academico='', email_google_classroom='')
        return aluno

    def periodos_fechados(self):
        matriculas_periodo_abertos = self.matriculaperiodo_set.filter(situacao__pk__in=[SituacaoMatriculaPeriodo.MATRICULADO, SituacaoMatriculaPeriodo.EM_ABERTO])
        return not matriculas_periodo_abertos.exists()

    def possui_historico(self):
        return (self.iniciou_suap() or self.integralizou_suap()) and not self.matriz.estrutura.proitec

    def is_matriculado(self):
        return self.situacao.pk == SituacaoMatricula.MATRICULADO

    def is_matricula_vinculo(self):
        return self.situacao.pk == SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL

    def is_intercambio(self):
        return self.situacao.pk == SituacaoMatricula.INTERCAMBIO

    def possui_vinculo(self):
        situacao_valida = (
            self.situacao.pk == SituacaoMatricula.INTERCAMBIO
            or self.situacao.pk == SituacaoMatricula.TRANCADO
            or self.situacao.pk == SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE
            or self.situacao.pk == SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL
        )
        if situacao_valida:
            return True
        else:
            return self.situacao.pk == SituacaoMatricula.MATRICULADO and not self.get_ultima_matricula_periodo().is_aberto()

    def pode_emitir_declaracao(self):
        if self.curso_campus.modalidade_id is None:
            return False
        # alunos de Curso FIC anterior a 2018
        if self.curso_campus.modalidade.pk == Modalidade.FIC and self.ano_letivo.ano < 2018:
            return False
        # alunos que ainda são do Q-Acadêmico
        if not self.matriz and not self.eh_aluno_minicurso():
            return False
        return True

    # COLAÇÃO DE GRAU
    def colou_grau(self):
        return ColacaoGrau.objects.filter(participacaocolacaograu__aluno=self, deferida=True).exists()

    def get_participacao_colacao_grau(self):
        return self.participacaocolacaograu_set.exists() and self.participacaocolacaograu_set.all()[0] or None

    def get_data_colacao_grau(self):
        participacao_colacao_grau = self.get_participacao_colacao_grau()
        return participacao_colacao_grau and participacao_colacao_grau.colacao_grau.data_colacao or self.data_colacao_grau

    # ENADE
    def cumpriu_enade(self):
        enade_ingressante = self.get_enade_ingressante()
        enade_ingressante = enade_ingressante and enade_ingressante.situacao in [RegistroConvocacaoENADE.SITUACAO_PRESENTE, RegistroConvocacaoENADE.SITUACAO_DISPENSADO] or False
        if self.situacao_id in (SituacaoMatricula.FORMADO, SituacaoMatricula.CONCLUIDO) and self.dt_conclusao_curso and self.dt_conclusao_curso < datetime.date(2018, 8, 27):
            enade_ingressante = True

        enade_concluinte = self.get_enade_concluinte()
        enade_concluinte = enade_concluinte and enade_concluinte.situacao in [RegistroConvocacaoENADE.SITUACAO_PRESENTE, RegistroConvocacaoENADE.SITUACAO_DISPENSADO] or False

        return enade_ingressante and enade_concluinte

    def get_convocacoes_enade(self):
        return RegistroConvocacaoENADE.objects.filter(aluno=self).order_by('tipo_convocacao', 'id')

    def get_enade_ingressante(self):
        return self.get_convocacoes_enade().filter(tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE).last()

    def get_enade_concluinte(self):
        return self.get_convocacoes_enade().filter(tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_CONCLUINTE).last()

    def pode_ser_dispensado_enade(self):
        possui_convocacao = self.get_enade_ingressante() and self.get_enade_concluinte()
        if possui_convocacao:
            return False
        else:
            if not self.matriz_id:
                return False
            return not self.possui_pendencia(incluir_colacao_grau=False, incluir_enade=False) and not self.is_concluido()

    # TCC
    def apresentou_tcc(self):
        projeto_final = ProjetoFinal.objects.filter(
            matricula_periodo__aluno=self, situacao=ProjetoFinal.SITUACAO_APROVADO, resultado_data__isnull=False
        ).first()
        if projeto_final:
            return not AssinaturaAtaEletronica.objects.filter(
                ata__projeto_final=projeto_final, data__isnull=True
            ).exists()
        return False

    def get_projetos_finais(self):
        return ProjetoFinal.objects.filter(matricula_periodo__aluno=self)

    def get_projeto_final_aprovado(self):
        qs = self.get_projetos_finais().filter(situacao=ProjetoFinal.SITUACAO_APROVADO)
        return qs.exists() and qs[0] or None

    def get_projeto_final(self):
        qs = self.get_projetos_finais()
        qs_aprovado = qs.filter(situacao=ProjetoFinal.SITUACAO_APROVADO)
        return qs_aprovado.exists() and qs_aprovado.first() or (qs.exists() and qs.first() or None)

    # ATIVIDADE COMPLEMENTAR
    def get_ultima_atividade_complementar_curricular(self):
        if self.matriz.configuracao_atividade_academica:
            ids = ItemConfiguracaoAtividadeComplementar.objects.filter(configuracao=self.matriz.configuracao_atividade_academica).values_list('tipo__id', flat=True)
            qs = self.atividadecomplementar_set.filter(tipo__id__in=ids).order_by('-data_atividade')
            return qs.exists() and qs[0]
        return None

    # DIPLOMA
    def get_registro_emissao_diploma(self):
        qs = RegistroEmissaoDiploma.objects.filter(aluno=self, cancelado=False)
        return qs.exists() and qs[0] or None

    def get_url_matricula_online(self):
        if self.is_seriado() or self.is_modular():
            return f'/edu/pedido_matricula_seriado/{self.id}/'
        elif self.is_credito():
            return f'/edu/pedido_matricula_credito/{self.id}/'
        else:
            return ''

    def atualizar_periodo_referencia(self):
        estrutura = self.matriz.estrutura
        if estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_CREDITO:
            ids_componentes_pendentes = self.get_componentes_pendentes().values_list('id', flat=True)
            self.periodo_atual = (
                ComponenteCurricular.objects.filter(matriz=self.matriz, componente__id__in=ids_componentes_pendentes).aggregate(Min('periodo_letivo'))['periodo_letivo__min']
                or self.matriz.qtd_periodos_letivos
            )
        elif estrutura.tipo_avaliacao in [EstruturaCurso.TIPO_AVALIACAO_SERIADO, EstruturaCurso.TIPO_AVALIACAO_MODULAR]:
            self.periodo_atual = self.matriculaperiodo_set.order_by('-ano_letivo__ano', '-periodo_letivo')[0].periodo_matriz

    def is_cursando_componente_projeto_final(self):
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()
        return (
            ultima_matricula_periodo
            and ultima_matricula_periodo.matriculadiario_set.filter(
                diario__componente_curricular__tipo__in=[ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO, ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL]
            ).exists()
        )

    def is_credito(self):
        return self.matriz.estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_CREDITO

    def is_seriado(self):
        return self.matriz.estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_SERIADO

    def is_modular(self):
        return self.matriz and self.matriz.estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_MODULAR

    def is_fic(self):
        return self.matriz.estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_FIC

    def is_proitec(self):
        return self.matriz.estrutura.proitec

    def is_sica(self):
        if 'sica' in settings.INSTALLED_APPS:
            return self.historico_set.exists()
        return False

    def is_qacademico(self):
        return self.codigo_academico and not self.matriz_id and not self.is_sica()

    def get_ultima_turma_cursada(self):
        qs = self.matriculaperiodo_set.filter(turma__isnull=False).order_by('-id')
        if qs:
            return qs[0].turma
        return None

    def pode_matricula_online(self):
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()
        com_vinculo = False
        aberto = False
        matriculado = False
        vinculo = False
        if ultima_matricula_periodo:
            aberto = ultima_matricula_periodo.situacao_id == SituacaoMatriculaPeriodo.EM_ABERTO
            matriculado = ultima_matricula_periodo.situacao_id == SituacaoMatriculaPeriodo.MATRICULADO
            vinculo = ultima_matricula_periodo.situacao_id == SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL

        if self.situacao_id in [
            SituacaoMatricula.MATRICULADO,
            SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL,
            SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
            SituacaoMatricula.TRANCADO,
            SituacaoMatricula.INTERCAMBIO,
        ]:
            com_vinculo = True

        return com_vinculo and (aberto or matriculado or vinculo) and self.get_configuracao_pedido_matricula_ativa() and self.matriculaperiodo_set.all().count() > 1 and self.matriz

    def get_configuracao_pedido_matricula_ativa(self):
        hoje = datetime.date.today()
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()
        qs = self.curso_campus.configuracaopedidomatricula_set.filter(
            data_inicio__lte=hoje, data_fim__gte=hoje, ano_letivo=ultima_matricula_periodo.ano_letivo, periodo_letivo=ultima_matricula_periodo.periodo_letivo
        )
        if qs.exists() and not qs[0].is_cancelado():
            return qs[0]
        else:
            return None

    def get_ch_aproveitada(self):
        suap = (
            AproveitamentoEstudo.objects.filter(matricula_periodo__aluno=self)
            .aggregate(Sum('componente_curricular__componente__ch_hora_relogio'))
            .get('componente_curricular__componente__ch_hora_relogio__sum')
            or 0
        )
        q_academico = (
            MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO)
            .aggregate(Sum('equivalencia_componente__componente__ch_qtd_creditos'))
            .get('equivalencia_componente__componente__ch_qtd_creditos__sum')
            or 0
        )
        return suap + q_academico

    def get_ch_certificada(self):
        suap = (
            CertificacaoConhecimento.objects.filter(matricula_periodo__aluno=self)
            .aggregate(Sum('componente_curricular__componente__ch_hora_relogio'))
            .get('componente_curricular__componente__ch_hora_relogio__sum')
            or 0
        )
        q_academico = (
            MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO)
            .aggregate(Sum('equivalencia_componente__componente__ch_qtd_creditos'))
            .get('equivalencia_componente__componente__ch_qtd_creditos__sum')
            or 0
        )
        return suap + q_academico

    def get_ch_certificada_ou_aproveitada(self):
        return self.get_ch_aproveitada() + self.get_ch_certificada()

    def get_percentual_ch_certificada_ou_aproveitada(self):
        return (self.get_ch_certificada_ou_aproveitada() * 100) / self.matriz.get_carga_horaria_total_prevista()

    def get_creditos_certificados(self):
        suap = (
            CertificacaoConhecimento.objects.filter(matricula_periodo__aluno=self)
            .aggregate(Sum('componente_curricular__componente__ch_qtd_creditos'))
            .get('componente_curricular__componente__ch_qtd_creditos__sum')
            or 0
        )
        q_academico = (
            MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO)
            .aggregate(Sum('equivalencia_componente__componente__ch_qtd_creditos'))
            .get('equivalencia_componente__componente__ch_qtd_creditos__sum')
            or 0
        )
        return suap + q_academico

    def get_creditos_aproveitados(self):
        suap = (
            AproveitamentoEstudo.objects.filter(matricula_periodo__aluno=self)
            .aggregate(Sum('componente_curricular__componente__ch_qtd_creditos'))
            .get('componente_curricular__componente__ch_qtd_creditos__sum')
            or 0
        )
        q_academico = (
            MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO)
            .aggregate(Sum('equivalencia_componente__componente__ch_qtd_creditos'))
            .get('equivalencia_componente__componente__ch_qtd_creditos__sum')
            or 0
        )
        return suap + q_academico

    def get_creditos_certificados_ou_aproveitados(self):
        return self.get_creditos_certificados() + self.get_creditos_aproveitados()

    def get_ultimo_procedimento_matricula(self):
        return ProcedimentoMatricula.objects.filter(matricula_periodo__aluno=self).order_by('-id')[0]

    def get_diarios_by_situacao(self, situacao):
        return Diario.objects.filter(matriculadiario__matricula_periodo__aluno=self, matriculadiario__situacao=situacao)

    # utilizada apenas no seriado
    def get_turmas_matricula_online(self, turma_indisponiveis_com_motivo=None):
        ids_componentes_cumpridos = self.get_ids_componentes_curriculares_cumpridos()
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()
        turma_periodo_atual = ultima_matricula_periodo.turma
        turmas = []
        if turma_periodo_atual:
            # inserindo a turma já salva nos períodos de matrícula anteriores
            turmas.append(turma_periodo_atual)
        else:
            # obtendo as turmas disponvíveis do periodo atual
            turmas = Turma.objects.filter(
                ano_letivo=ultima_matricula_periodo.ano_letivo,
                periodo_letivo=ultima_matricula_periodo.periodo_letivo,
                curso_campus=self.curso_campus,
                periodo_matriz=self.periodo_atual,
            )

            # validando a disponibilidade de turmas priorizando as turmas do turno do aluno
            turmas_turno_aluno = turmas.filter(turno=self.turno)
            if turmas_turno_aluno.exists():
                turmas = turmas_turno_aluno

            # removendo turmas que não são do polo do aluno
            if self.polo:
                turmas = turmas.filter(polo=None) | turmas.filter(polo=self.polo)
                turmas = turmas.distinct()

            # removendo turmas incompatíveis com a anterior caso tenha sido informado na configuracao
            configuracao_pedido_matricula_ativa = self.get_configuracao_pedido_matricula_ativa()
            if configuracao_pedido_matricula_ativa and configuracao_pedido_matricula_ativa.impedir_troca_turma:
                turma_anterior = self.get_turma_periodo_anterior()
                if turma_anterior:
                    turmas_compativeis = turmas.filter(sequencial=turma_anterior.sequencial)
                    if turmas_compativeis.exists():
                        turmas = turmas_compativeis

        if turmas:
            # todos os trechos que possuem a verificacao da variável "turma_indisponiveis_com_motivo" se referem ao retorno da lista de componentes pendentes que não
            # estarão disponíveis para o aluno na matrícula online na turma passada
            indisponiveis_com_motivo = []

            # pre requisitos
            # obtendo cc's do periodo atual
            componentes_curriculares_periodo_atual = ComponenteCurricular.objects.filter(matriz=self.matriz, periodo_letivo=self.periodo_atual).order_by('componente__id')
            # obtendo ids dos componentes pendentes anterior ao periodo atual
            periodos = list(range(1, self.periodo_atual))
            id_componentes_pedentes = self.get_componentes_pendentes(periodos, True).values_list('id', flat=True)
            id_componentes_disponiveis = []
            for componente_curricular_periodo_atual in componentes_curriculares_periodo_atual:
                # verificando se existe algum pre_requisito pendente
                if not componente_curricular_periodo_atual.pre_requisitos.filter(componente__id__in=id_componentes_pedentes):
                    # adicionando na lista de ids_componentes_disponiveis
                    id_componentes_disponiveis.append(componente_curricular_periodo_atual.componente.id)
                elif turma_indisponiveis_com_motivo:
                    componente_curricular_periodo_atual.motivo = "Pré-requisito não atendido"
                    indisponiveis_com_motivo.append(componente_curricular_periodo_atual)

            # Criando uma lista diarios para cada turma contendo apenas aqueles cujos componentes possam ser cursados pelo aluno
            for turma in turmas:
                id_componentes_optativos = []
                # adicionando os componentes aptativos, ou seja, aqueles sem definição de período na matriz
                for componente_id in turma.diario_set.filter(componente_curricular__periodo_letivo__isnull=True).values_list('componente_curricular__componente__id', flat=True):
                    id_componentes_optativos.append(componente_id)
                # correquisitos
                id_componentes_disponiveis_prerequisitos = copy.copy(id_componentes_disponiveis)
                # processando correquisitos com base nos ids após processamento dos pre e em cada turma disponível
                id_componentes_disponiveis_correquisitos = self.get_id_componentes_correquisitos_processados(id_componentes_disponiveis, turma=turma)
                if turma_indisponiveis_com_motivo == turma:
                    ids_indisponiveis = diferenca_listas(id_componentes_disponiveis_prerequisitos, id_componentes_disponiveis_correquisitos)
                    for componente_curricular in self.get_componentes_curriculares_por_ids(ids_indisponiveis):
                        componente_curricular.motivo = "Co-requisito não disponível"
                        indisponiveis_com_motivo.append(componente_curricular)

                # diários cujos componentes passaram pelo processsamento do pre e correquisitos
                qs_diarios = turma.diario_set.filter(componente_curricular__componente__id__in=id_componentes_disponiveis_correquisitos + id_componentes_optativos)
                if turma_indisponiveis_com_motivo == turma:
                    ids_componentes_disponiveis_diarios = qs_diarios.values_list("componente_curricular__componente__id", flat=True)
                    ids_indisponiveis = diferenca_listas(id_componentes_disponiveis_correquisitos, ids_componentes_disponiveis_diarios)
                    for componente_curricular in self.get_componentes_curriculares_por_ids(ids_indisponiveis):
                        componente_curricular.motivo = "Diário não gerado nesta turma"
                        indisponiveis_com_motivo.append(componente_curricular)

                # removendo diários que o aluno já se matriculou em períodos de renovação de matricula anteriores
                ids_componentes_matriculados = ultima_matricula_periodo.get_matriculas_diario().values_list('diario__componente_curricular__componente__id', flat=True)
                qs_diarios = qs_diarios.exclude(componente_curricular__componente__id__in=ids_componentes_matriculados)

                # diarios que possuem horário
                if self.curso_campus.modalidade.pk in [Modalidade.INTEGRADO, Modalidade.SUBSEQUENTE]:
                    # diarios do subsequente nao precisam ter horarios definidos
                    qs_diarios_com_horarios = qs_diarios.filter(pk__gt=0)
                else:
                    qs_diarios_com_horarios = qs_diarios.filter(horarioauladiario__isnull=False)

                tipos_componentes_permitidos_sem_horario = [
                    ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                    ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                    ComponenteCurricular.TIPO_SEMINARIO,
                ]
                if turma_indisponiveis_com_motivo == turma:
                    qs_diarios = qs_diarios.filter(horarioauladiario__isnull=True)
                    qs_diarios = qs_diarios.exclude(
                        componente_curricular__componente__id__in=qs_diarios_com_horarios.values_list("componente_curricular__componente__id", flat=True)
                    )
                    qs_diarios = qs_diarios.exclude(componente_curricular__tipo__in=tipos_componentes_permitidos_sem_horario)
                    qs_diarios = qs_diarios.exclude(turno__descricao='EAD')
                    ids_indisponiveis = qs_diarios.values_list("componente_curricular__componente__id", flat=True)
                    for componente_curricular in self.get_componentes_curriculares_por_ids(ids_indisponiveis):
                        componente_curricular.motivo = "Diário sem horário de aula definido"
                        indisponiveis_com_motivo.append(componente_curricular)
                    return indisponiveis_com_motivo
                else:
                    # diarios que não possuem horário mas são de prática profissional
                    qs_diarios_com_pratica_profissional = qs_diarios.filter(componente_curricular__tipo__in=tipos_componentes_permitidos_sem_horario)
                    # diarios do turno ead
                    qs_diarios_ead = qs_diarios.filter(turno__descricao='EAD')
                    qs_diarios = qs_diarios_com_horarios | qs_diarios_com_pratica_profissional | qs_diarios_ead
                    turma.diarios = qs_diarios.exclude(componente_curricular__componente__id__in=ids_componentes_cumpridos).distinct()
        return turmas

    def pode_ser_matriculado_no_diario(self, diario, ignorar_quebra_requisito=False):
        if MatriculaDiario.objects.filter(
            matricula_periodo__aluno=self,
            diario__ano_letivo=diario.ano_letivo,
            diario__periodo_letivo=diario.periodo_letivo,
            diario__componente_curricular__componente=diario.componente_curricular.componente,
            situacao=MatriculaDiario.SITUACAO_CURSANDO,
        ).exists():
            return False, 'O aluno está cursando este componente em outro diário.'
        qs_componente_curricular = self.matriz.componentecurricular_set.filter(componente=diario.componente_curricular.componente)
        if qs_componente_curricular.exists():
            componente_curricular = qs_componente_curricular[0]
            return self.pode_cursar_componente_curricular(componente_curricular, False, ignorar_quebra_requisito)
        else:
            return self.pode_cursar_componente_curricular(diario.componente_curricular, True, ignorar_quebra_requisito)

    def pode_cursar_componente_curricular(self, componente_curricular, outra_matriz=False, ignorar_quebra_requisito=False):

        ids_componentes_cursando = self.get_ids_componentes_cursando()
        ids_componentes_pagos = self.get_ids_componentes_cumpridos(componente_curricular.get_corequisitos())
        for co_requisito in componente_curricular.co_requisitos.all():
            if co_requisito.componente.pk not in ids_componentes_cursando and co_requisito.componente.pk not in ids_componentes_pagos:
                if outra_matriz or ignorar_quebra_requisito:
                    return True, 'O aluno quebrará os correquisitos necessários para essa disciplina.'
                return False, 'O aluno não cursou ou não está cursando os correquisitos necessários para essa disciplina.'
        pre_requisitos = componente_curricular.get_pre_requisitos()

        ids_componentes_pagos_global = []
        for id_componente_pago in self.get_ids_componentes_cumpridos(pre_requisitos):
            ids_componentes_pagos_global.append(id_componente_pago)
        for id_componente_pago in self.get_ids_componentes_extra_curriculares_cumpridos(excluir_equivalencias=False):
            if id_componente_pago in pre_requisitos:
                ids_componentes_pagos_global.append(id_componente_pago)

        if set(pre_requisitos) != set(ids_componentes_pagos_global):
            if outra_matriz or ignorar_quebra_requisito:
                return True, 'O aluno quebrará os pré-requistos necessários para essa disciplina.'
            return False, 'O aluno não cursou todos os pré-requisitos necessários para essa disciplina.'

        return True, ''

    # utilizada para crédito e pelas dependecias do seriado
    def get_diarios_pendentes_matricula_online(
        self, apenas_obrigatorias=False, apenas_optativas=False, ids_componentes_diarios_obrigatorias=[], retorno_indisponiveis_com_motivo=False, ignorar_pendencia_horario=False
    ):
        # todos os trechos que possuem a verificacao da variável "retorno_indisponiveis_com_motivo" se referem ao retorno da lista de componentes pendentes que não
        # estarão disponíveis para o aluno na matrícula online
        indisponiveis_com_motivo = []

        ultima_matricula_periodo = self.get_ultima_matricula_periodo()

        # calculando a quantidade de períodos para a busca de componentes pendentes do aluno
        periodos = []
        if self.is_seriado() or self.is_modular():
            # no SERIADO e MODULAR serão verificados os componentes anteriores ao periodo atual(DEPENDÊNCIAS)
            periodos = list(range(1, self.periodo_atual))
            if not periodos:
                return []
        if self.is_credito():
            # no CRÉDITO
            # nas obrigatorias
            # se foi definido a qtd_max_periodos_subsequentes na estrutura do curso
            # serão verificados os componentes do periodo atual
            # (menor período dos componentes na matriz do aluno que está pendente) somados ao número máximo de períodos
            # subsquentes que a estrutura do seu curso permite
            # se não, serão de todos os períodos possíveis

            # se for apenas os componentes optativos não existem períodos a serem verificados,
            # serão todos os componentes optativos

            if apenas_obrigatorias and self.matriz.estrutura.qtd_max_periodos_subsequentes:
                periodos = list(range(1, (self.periodo_atual + self.matriz.estrutura.qtd_max_periodos_subsequentes) + 1))

        # obtendo ids dos componentes pendentes segundo regra explicada acima
        ids_componentes_pendentes = []
        for componente in self.get_componentes_pendentes(periodos, apenas_obrigatorias, apenas_optativas):
            ids_componentes_pendentes.append(componente.pk)
        for componente in self.get_componentes_em_diarios_pendentes():
            ids_componentes_pendentes.append(componente.pk)

        # pre requisitos
        # obtendo cc's do periodo atual
        componentes_curriculares_pendentes = ComponenteCurricular.objects.filter(matriz=self.matriz, componente__id__in=ids_componentes_pendentes).order_by('componente__id')

        # obtendo todos os componentes pendentes para o caso de apenas_optativas
        if apenas_optativas:
            ids_componentes_pendentes = self.get_componentes_pendentes(periodos).values_list('id', flat=True)

        id_componentes_disponiveis = []
        # percorrendo cc pendentes
        for componente_curricular_pendente in componentes_curriculares_pendentes:
            # verificando se existe algum pre_requisito pendente
            if not componente_curricular_pendente.pre_requisitos.filter(componente__id__in=ids_componentes_pendentes):
                # adicionando na lista de ids_componentes_disponiveis
                id_componentes_disponiveis.append(componente_curricular_pendente.componente.id)
            elif retorno_indisponiveis_com_motivo:
                componente_curricular_pendente.motivo = "Pré-requisito não atendido"
                indisponiveis_com_motivo.append(componente_curricular_pendente)

        # correquisitos
        id_componentes_disponiveis_prerequisitos = copy.copy(id_componentes_disponiveis)

        # processando correquisitos com base nos ids após processamento dos pre e nos componentes disponíveis obrigatórios
        id_componentes_disponiveis_pos_correquisitos = self.get_id_componentes_correquisitos_processados(
            id_componentes_disponiveis, ids_componentes_diarios_obrigatorias=ids_componentes_diarios_obrigatorias
        )

        if retorno_indisponiveis_com_motivo:
            ids_indisponiveis = diferenca_listas(id_componentes_disponiveis_prerequisitos, id_componentes_disponiveis_pos_correquisitos)
            for componente_curricular in self.get_componentes_curriculares_por_ids(ids_indisponiveis):
                componente_curricular.motivo = "Co-requisito não disponível"
                indisponiveis_com_motivo.append(componente_curricular)

        # buscando diários para os componentes diponíveis
        qs_diarios = Diario.objects.filter(
            componente_curricular__componente__id__in=id_componentes_disponiveis_pos_correquisitos,
            turma__ano_letivo=ultima_matricula_periodo.ano_letivo,
            turma__periodo_letivo=ultima_matricula_periodo.periodo_letivo,
            turma__curso_campus__diretoria__setor__uo_id=self.curso_campus.diretoria.setor.uo.id,
        )
        if retorno_indisponiveis_com_motivo:
            ids_componentes_disponiveis_diarios = qs_diarios.values_list("componente_curricular__componente__id", flat=True)
            ids_indisponiveis = diferenca_listas(id_componentes_disponiveis_pos_correquisitos, ids_componentes_disponiveis_diarios)
            for componente_curricular in self.get_componentes_curriculares_por_ids(ids_indisponiveis):
                componente_curricular.motivo = "Diário não gerado na diretoria do seu curso"
                indisponiveis_com_motivo.append(componente_curricular)

        # removendo diários que o aluno já se matriculou em períodos de renovação de matricula anteriores
        ids_componentes_matriculados = ultima_matricula_periodo.get_matriculas_diario().values_list('diario__componente_curricular__componente__id', flat=True)
        qs_diarios = qs_diarios.exclude(componente_curricular__componente__id__in=ids_componentes_matriculados)

        # removendo diários de outros cursos (matrizes) caso esteja configurado no pedido de renovação de matrícula
        configuracao_pedido_matricula_ativa = self.get_configuracao_pedido_matricula_ativa()
        if configuracao_pedido_matricula_ativa and configuracao_pedido_matricula_ativa.restringir_por_curso:
            qs_diarios = qs_diarios.filter(componente_curricular__matriz=self.matriz)

        # removendo diários que não são do polo do aluno
        if self.polo:
            if retorno_indisponiveis_com_motivo:
                ids_componentes_disponiveis_diarios = qs_diarios.values_list("componente_curricular__componente__id", flat=True)
                ids_componentes_disponiveis_diarios_polo = qs_diarios.filter(turma__polo=self.polo).values_list("componente_curricular__componente__id", flat=True)
                ids_indisponiveis = diferenca_listas(ids_componentes_disponiveis_diarios, ids_componentes_disponiveis_diarios_polo)

                ids_componentes_disponiveis_diarios_sem_polo = qs_diarios.filter(turma__polo=None).values_list("componente_curricular__componente__id", flat=True)
                ids_indisponiveis = diferenca_listas(ids_indisponiveis, ids_componentes_disponiveis_diarios_sem_polo)

                for componente_curricular in self.get_componentes_curriculares_por_ids(ids_indisponiveis):
                    componente_curricular.motivo = "Diário não gerado para seu polo"
                    indisponiveis_com_motivo.append(componente_curricular)

            qs_diarios = qs_diarios.filter(turma__polo=self.polo) | qs_diarios.filter(turma__polo=None)
            qs_diarios = qs_diarios.distinct()

        # diarios que possuem horário
        if ignorar_pendencia_horario:
            qs_diarios_com_horarios = qs_diarios.filter(pk__gt=0)
        else:
            qs_diarios_com_horarios = qs_diarios.filter(horarioauladiario__isnull=False)

        tipos_componentes_permitidos_sem_horario = [
            ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
            ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
            ComponenteCurricular.TIPO_SEMINARIO,
        ]
        if retorno_indisponiveis_com_motivo:
            qs_diarios = qs_diarios.filter(horarioauladiario__isnull=True)
            qs_diarios = qs_diarios.exclude(componente_curricular__componente__id__in=qs_diarios_com_horarios.values_list("componente_curricular__componente__id", flat=True))
            qs_diarios = qs_diarios.exclude(componente_curricular__tipo__in=tipos_componentes_permitidos_sem_horario)
            qs_diarios = qs_diarios.exclude(turno__descricao='EAD')
            ids_indisponiveis = qs_diarios.values_list("componente_curricular__componente__id", flat=True)
            for componente_curricular in self.get_componentes_curriculares_por_ids(ids_indisponiveis):
                componente_curricular.motivo = "Diário sem horário de aula definido"
                indisponiveis_com_motivo.append(componente_curricular)
            return indisponiveis_com_motivo
        else:
            # diarios que não possuem horário mas são de prática profissional
            qs_diarios_com_pratica_profissional = qs_diarios.filter(componente_curricular__tipo__in=tipos_componentes_permitidos_sem_horario)
            # diarios do turno ead
            qs_diarios_ead = qs_diarios.filter(turno__descricao='EAD')
            qs_diarios = qs_diarios_com_horarios | qs_diarios_com_pratica_profissional | qs_diarios_ead
            return qs_diarios.distinct().order_by('componente_curricular__periodo_letivo', 'componente_curricular__componente__descricao_historico')

    # função recursiva para o cálculo dos co-requisitos
    def get_id_componentes_correquisitos_processados(self, id_componentes_disponiveis_prerequisitos, turma=None, ids_componentes_diarios_obrigatorias=[]):
        # obtendo cc da lista de ids_componentes_disponiveis. Na primeira vez, chegou após o processamento dos pre, e depois após processamento dos correquisitos
        componentes_curriculares_disponiveis = ComponenteCurricular.objects.filter(componente__id__in=id_componentes_disponiveis_prerequisitos, matriz=self.matriz)
        # obtendo ids dos componenets cumpridos pelo aluno
        ids_componentes_cumpridos = self.get_ids_componentes_cumpridos()
        ids_componentes_cursando = self.get_ids_componentes_cursando()
        # percorrendo a lista para verificar os correquisitos
        for cc_disponivel in componentes_curriculares_disponiveis:
            # obtendo lista de ids do correquisitos do cc_disponivel
            ids_correquisitos = cc_disponivel.co_requisitos.all().values_list('componente__id', flat=True).order_by('componente__id')
            if ids_correquisitos:
                # percorrendo a lista de correquisitos
                for id_correquisito in ids_correquisitos:
                    remover = False
                    # caso aluno de curso do regime SERIADO
                    if self.is_seriado() or self.is_modular():
                        # ativando flag para remover componente que seus correquisitos que não estejam nos componentes disponíveis
                        # e nem na lista de componentes cumpridos e que não estão sendo cursadas
                        if (
                            id_correquisito not in id_componentes_disponiveis_prerequisitos
                            and id_correquisito not in ids_componentes_cumpridos
                            and id_correquisito not in ids_componentes_cursando
                        ):
                            remover = True
                        else:
                            # ativando flag para remover componente que seus correquisitos não possuam diários com HORÁRIOS DEFINIDOS na turma passada
                            if turma and not turma.diario_set.filter(componente_curricular__componente__id=id_correquisito, horarioauladiario__isnull=False).exists():
                                remover = True

                    # caso aluno de curso do regime CREDITO
                    if self.is_credito():
                        # ativando flag para remover componente que seus correquisitos NÃO estejam em id_componentes_disponiveis_prerequisitos ou ids_componentes_diarios_obrigatorias E não foram pagos e que não estão sendo cursadas
                        if (
                            not (id_correquisito in id_componentes_disponiveis_prerequisitos or id_correquisito in ids_componentes_diarios_obrigatorias)
                            and not id_correquisito in ids_componentes_cumpridos
                            and id_correquisito not in ids_componentes_cursando
                        ):
                            remover = True
                        else:
                            # ativando flag para remover componente que seus correquisitos não possuam diários com HORÁRIOS DEFINIDOS
                            qs_diarios = Diario.objects.filter(
                                componente_curricular__componente__id=id_correquisito,
                                turma__ano_letivo=self.get_ultima_matricula_periodo().ano_letivo,
                                turma__periodo_letivo=self.get_ultima_matricula_periodo().periodo_letivo,
                                turma__curso_campus__diretoria=self.curso_campus.diretoria,
                            )

                            qs_diarios = (
                                qs_diarios.filter(horarioauladiario__isnull=False)
                                | qs_diarios.filter(turno__descricao='EAD')
                                | qs_diarios.filter(
                                    componente_curricular__tipo__in=[
                                        ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                                        ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                                        ComponenteCurricular.TIPO_SEMINARIO,
                                    ]
                                )
                            )

                            if self.polo:
                                qs_diarios = qs_diarios.filter(turma__polo=self.polo) | qs_diarios.filter(turma__polo__isnull=True)

                            if not qs_diarios.exists() and id_correquisito not in ids_componentes_cumpridos:
                                remover = True

                    # caso a flag remover seja True e ainda exista id para ser removido de id_componentes_disponiveis_prerequisitos
                    if remover and len(id_componentes_disponiveis_prerequisitos):
                        # removendo id de id_componentes_disponiveis_prerequisitos
                        if cc_disponivel.componente.id in id_componentes_disponiveis_prerequisitos:
                            id_componentes_disponiveis_prerequisitos.remove(cc_disponivel.componente.id)
                        # chamando novamente a função para testar se a remocão dos id do componente não irá influenciar em todas as validações acima
                        self.get_id_componentes_correquisitos_processados(id_componentes_disponiveis_prerequisitos, turma, ids_componentes_diarios_obrigatorias)

        return id_componentes_disponiveis_prerequisitos

    def componentes_nao_disponiveis_matricula_online(self, optativas, turma):
        if self.is_credito():
            if optativas:
                return self.get_diarios_pendentes_matricula_online(apenas_optativas=True, retorno_indisponiveis_com_motivo=True)
            else:
                if self.matriz.estrutura.qtd_max_periodos_subsequentes:
                    periodos = list(range(1, (self.periodo_atual + self.matriz.estrutura.qtd_max_periodos_subsequentes) + 1))
                    componentes_pendentes_ate_qtd_periodos = self.get_componentes_pendentes(periodos=periodos, apenas_obrigatorias=True)
                    componentes_pendentes_pos_qtd_periodos = self.get_componentes_pendentes(apenas_obrigatorias=True).exclude(
                        id__in=componentes_pendentes_ate_qtd_periodos.values_list('id', flat=True)
                    )
                    componentes_nao_disponiveis_motivo = self.get_diarios_pendentes_matricula_online(apenas_obrigatorias=True, retorno_indisponiveis_com_motivo=True)

                    for componente_curricular in ComponenteCurricular.objects.filter(matriz=self.matriz, componente__id__in=componentes_pendentes_pos_qtd_periodos).order_by(
                        'componente__id'
                    ):
                        componente_curricular.motivo = "Quantidade máxima de períodos subsequentes para cursar disciplinas"
                        componentes_nao_disponiveis_motivo.append(componente_curricular)
                else:
                    componentes_nao_disponiveis_motivo = self.get_diarios_pendentes_matricula_online(apenas_obrigatorias=True, retorno_indisponiveis_com_motivo=True)

                return sorted(componentes_nao_disponiveis_motivo, key=operator.methodcaller('get_periodo_letivo'))
        elif self.is_seriado() or self.is_modular():
            if turma:
                return self.get_turmas_matricula_online(turma)
            else:
                componentes_nao_disponiveis_motivo = self.get_diarios_pendentes_matricula_online(apenas_obrigatorias=True, retorno_indisponiveis_com_motivo=True)
                return sorted(componentes_nao_disponiveis_motivo, key=operator.methodcaller('get_periodo_letivo'))

    def get_diarios_eletivas_matricula_online(self):
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()
        qs_diarios = Diario.objects.filter(
            turma__ano_letivo=ultima_matricula_periodo.ano_letivo,
            turma__periodo_letivo=ultima_matricula_periodo.periodo_letivo,
            turma__curso_campus__diretoria=self.curso_campus.diretoria,
        )
        qs_diarios = qs_diarios.filter(turma__curso_campus__modalidade__nivel_ensino=self.curso_campus.modalidade.nivel_ensino)
        qs_diarios = qs_diarios.exclude(componente_curricular__componente__in=self.matriz.get_ids_componentes())

        # diarios que possuem horário
        qs_diarios_com_horarios = qs_diarios.filter(horarioauladiario__isnull=False)

        # diarios que não possuem horário mas são de prática profissional
        qs_diarios_com_pratica_profissional = qs_diarios.filter(
            componente_curricular__tipo__in=[
                ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                ComponenteCurricular.TIPO_SEMINARIO,
            ]
        )

        # diarios do turno ead
        qs_diarios_ead = qs_diarios.filter(turno__descricao='EAD')

        qs_diarios = qs_diarios_com_horarios | qs_diarios_ead | qs_diarios_com_pratica_profissional

        return qs_diarios.distinct().order_by('componente_curricular__componente')

    def get_diarios_disponiveis_matricular_por_diretoria(self, diretoria, outros_componentes=False, outras_matrizes=False, ignorar_futuros=True, componente=None):

        ultima_matricula_periodo = self.get_ultima_matricula_periodo()

        qs_diarios = Diario.objects.filter(
            ano_letivo=ultima_matricula_periodo.ano_letivo, periodo_letivo=ultima_matricula_periodo.periodo_letivo, turma__curso_campus__diretoria=diretoria
        )

        # excluindo já matriculados
        qs_diarios = qs_diarios.exclude(id__in=MatriculaDiario.objects.filter(matricula_periodo=ultima_matricula_periodo).values_list('diario__pk', flat=True))

        # excluindo os pagos
        qs_diarios = qs_diarios.exclude(componente_curricular__componente__in=self.get_componentes_cumpridos().values_list('id', flat=True))

        # excluindo os cursando no ultimo período
        qs_diarios = qs_diarios.exclude(componente_curricular__componente__in=self.get_componentes_cursando().values_list('id', flat=True))

        qs_diarios = qs_diarios.order_by('componente_curricular__componente__descricao')

        # filtrando apenas do componente especificado, se for o caso
        if componente:
            qs_diarios = qs_diarios.filter(componente_curricular__componente=componente)

        if outros_componentes and outras_matrizes:
            qs_diarios = qs_diarios.exclude(componente_curricular__matriz=self.matriz)
        elif outros_componentes:
            componentes = ComponenteCurricular.objects.filter(matriz=self.matriz).values_list('componente__id', flat=True).distinct()
            qs_diarios = qs_diarios.filter(componente_curricular__componente__in=componentes).exclude(componente_curricular__matriz=self.matriz)
        elif outras_matrizes:
            componentes = ComponenteCurricular.objects.filter(matriz=self.matriz).values_list('componente__id', flat=True).distinct()
            qs_diarios = qs_diarios.exclude(componente_curricular__componente__in=componentes)
        else:
            qs_diarios = qs_diarios.filter(componente_curricular__matriz=self.matriz)

        if ignorar_futuros:
            qs_diarios = qs_diarios.filter(componente_curricular__periodo_letivo__lte=self.periodo_atual) | qs_diarios.filter(
                componente_curricular__periodo_letivo__isnull=True
            )
        return qs_diarios.distinct()

    def get_historico(self, final=False, ordernar_por=1, exibir_optativas=False, eletronico=False):
        from edu.models.historico import RegistroHistorico

        if self.iniciou_suap() or self.integralizou_suap():
            grupos_componentes = OrderedDict()
            grupos_componentes['Componentes Curriculares'] = []
            if self.matriz.ch_seminarios:
                grupos_componentes['Seminários'] = []
            if self.matriz.ch_pratica_profissional:
                grupos_componentes['Prática Profissional'] = []
            if self.matriz.ch_atividades_extensao:
                grupos_componentes['Atividade de Extensão'] = []
            if self.matriz.ch_pratica_como_componente:
                grupos_componentes['Prática como Componente Curricular'] = []
            if self.matriz.ch_visita_tecnica:
                grupos_componentes['Visita Técnica / Aula da Campo'] = []
            grupos_componentes['Componentes Extra-Curriculares'] = []

            observacoes = []
            pk_nao_certificaveis = []

            ids_componenentes_associados = list(
                self.matriz.componentecurricular_set.filter(componente_curricular_associado__isnull=False).values_list('componente_curricular_associado__componente', flat=True)
            )
            ids_componenentes_associados_pagos = list(
                MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self, equivalencia_componente__componente__in=ids_componenentes_associados)
                .exclude(situacao__in=(MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA))
                .values_list('equivalencia_componente__componente', flat=True)
            ) + list(
                MatriculaDiario.objects.filter(
                    matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_APROVADO, diario__componente_curricular__componente__in=ids_componenentes_associados
                ).values_list('diario__componente_curricular__componente', flat=True)
            )

            for pk in ids_componenentes_associados:
                pk_nao_certificaveis.append(pk)

            for pk in ids_componenentes_associados_pagos:
                if pk in ids_componenentes_associados:
                    ids_componenentes_associados.remove(pk)

            qs_componentes_curriculares = self.matriz.componentecurricular_set.select_related('componente').exclude(componente__id__in=ids_componenentes_associados)
            if ordernar_por == Aluno.ORDENAR_HISTORICO_POR_COMPONENTE:
                qs_componentes_curriculares = qs_componentes_curriculares.order_by('componente__sigla')
            elif ordernar_por == Aluno.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ:
                qs_componentes_curriculares = qs_componentes_curriculares.order_by('periodo_letivo')

            for pk in (
                MatriculaDiario.objects.exclude(situacao__in=[MatriculaDiario.SITUACAO_CURSANDO, MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_CANCELADO])
                .filter(matricula_periodo__aluno=self)
                .values_list('diario__componente_curricular__componente__id', flat=True)
            ):
                pk_nao_certificaveis.append(pk)
            for pk in MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self).values_list('equivalencia_componente__componente__id', flat=True):
                pk_nao_certificaveis.append(pk)
            for pk in AproveitamentoEstudo.objects.filter(matricula_periodo__aluno=self).values_list('componente_curricular__componente__id', flat=True):
                pk_nao_certificaveis.append(pk)
            for pk in CertificacaoConhecimento.objects.filter(matricula_periodo__aluno=self).values_list('componente_curricular__componente__id', flat=True):
                pk_nao_certificaveis.append(pk)

            for componente_curricular in qs_componentes_curriculares:
                componentes = componente_curricular.get_grupo_componente_historico(grupos_componentes)

                repetir = True
                componente_cursado = None

                if self.matriz.estrutura.proitec:
                    aprovado = self.matriculaperiodo_set.filter(situacao__id=SituacaoMatriculaPeriodo.APROVADO).exists()
                    componente = dict(
                        pk=componente_curricular.pk,
                        matricula_diario=None,
                        matricula_diario_resumida=None,
                        ano_periodo_letivo=f'{self.ano_letivo}/{self.periodo_letivo}',
                        periodo_matriz=1,
                        sigla_componente=componente_curricular.componente.sigla,
                        descricao_componente=componente_curricular.componente.descricao_historico,
                        codigo_turma=None,
                        codigo_diario=None,
                        carga_horaria=componente_curricular.componente.ch_hora_relogio or '-',
                        media_final_disciplina='-',
                        percentual_carga_horaria_frequentada=aprovado and 100 or 0,
                        situacao_display=aprovado and 'Aprovado' or 'Rep. Falta',
                        situacao_legend='',
                        certificavel=False,
                        cursada=True,
                        certificada=False,
                        aproveitada=False,
                    )
                    repetir = False
                    componentes.append(componente)
                for matricula_diario in MatriculaDiario.objects.select_related('diario__componente_curricular__componente').filter(
                    matricula_periodo__aluno=self, diario__componente_curricular__componente=componente_curricular.componente
                ):
                    professores = []
                    for professor_diario in matricula_diario.diario.professordiario_set.exclude(tipo__descricao='Tutor'):
                        professores.append(
                            (
                                matricula_diario.get_sigla_componente(),
                                matricula_diario.get_descricao_componente(),
                                professor_diario.professor.vinculo.pessoa.nome,
                                professor_diario.professor.get_titulacao(),
                            )
                        )

                    if final and matricula_diario.is_componente_integralizado() or not final:
                        componente = dict(
                            pk=componente_curricular.pk,
                            matricula_diario=matricula_diario,
                            matricula_diario_resumida=None,
                            ano_periodo_letivo=f'{matricula_diario.matricula_periodo.ano_letivo}/{matricula_diario.matricula_periodo.periodo_letivo}',
                            periodo_matriz=componente_curricular.periodo_letivo,
                            sigla_componente=matricula_diario.get_sigla_componente(),
                            descricao_componente=matricula_diario.get_descricao_componente(),
                            codigo_turma=matricula_diario.get_codigo_turma(),
                            codigo_diario=matricula_diario.diario.pk,
                            carga_horaria=matricula_diario.get_carga_horaria() or '-',
                            media_final_disciplina=matricula_diario.situacao == MatriculaDiario.SITUACAO_CURSANDO and '-' or matricula_diario.get_media_final_disciplina_exibicao(),
                            percentual_carga_horaria_frequentada=matricula_diario.get_percentual_carga_horaria_frequentada()
                            if matricula_diario.situacao
                            not in [
                                MatriculaDiario.SITUACAO_CURSANDO,
                                MatriculaDiario.SITUACAO_PROVA_FINAL,
                                MatriculaDiario.SITUACAO_CANCELADO,
                                MatriculaDiario.SITUACAO_TRANCADO,
                                MatriculaDiario.SITUACAO_PENDENTE,
                                MatriculaDiario.SITUACAO_DISPENSADO,
                            ]
                            else None,
                            situacao_display=matricula_diario.get_situacao_display(),
                            situacao_legend='',
                            certificavel=matricula_diario.situacao == MatriculaDiario.SITUACAO_CURSANDO and componente_curricular.componente.pk not in pk_nao_certificaveis,
                            cursada=matricula_diario.situacao == MatriculaDiario.SITUACAO_APROVADO,
                            certificada=False,
                            aproveitada=False,
                            equivalente=False,
                            professores=professores,
                            pertence_ao_plano_retomada=matricula_diario.diario.turma.pertence_ao_plano_retomada
                        )
                        componentes.append(componente)
                        if repetir:
                            repetir = not (matricula_diario.situacao == MatriculaDiario.SITUACAO_APROVADO or matricula_diario.situacao == MatriculaDiario.SITUACAO_CURSANDO)
                        if not componente_cursado and not repetir:
                            componente_cursado = componente
                for matricula_diario in MatriculaDiarioResumida.objects.select_related('equivalencia_componente__componente').filter(
                    matricula_periodo__aluno=self, equivalencia_componente__componente=componente_curricular.componente
                ):
                    professores = []
                    professores.append(
                        (
                            matricula_diario.get_sigla_componente(),
                            matricula_diario.get_descricao_componente(),
                            matricula_diario.nome_professor,
                            matricula_diario.titularidade_professor,
                        )
                    )

                    if final and matricula_diario.is_componente_integralizado() or not final:
                        componente = dict(
                            pk=componente_curricular.pk,
                            matricula_diario=None,
                            matricula_diario_resumida=matricula_diario,
                            ano_periodo_letivo=f'{matricula_diario.matricula_periodo.ano_letivo}/{matricula_diario.matricula_periodo.periodo_letivo}',
                            periodo_matriz=componente_curricular.periodo_letivo,
                            sigla_componente=matricula_diario.get_sigla_componente(),
                            descricao_componente=matricula_diario.get_descricao_componente(),
                            codigo_turma=matricula_diario.get_codigo_turma(),
                            codigo_diario=matricula_diario.get_codigo_diario(),
                            carga_horaria=matricula_diario.get_carga_horaria() or '-',
                            media_final_disciplina=matricula_diario.get_media_final_disciplina_exibicao(),
                            percentual_carga_horaria_frequentada=matricula_diario.get_percentual_carga_horaria_frequentada(),
                            situacao_display=matricula_diario.get_situacao_display(),
                            situacao_legend='',
                            certificavel=componente_curricular.componente.pk not in pk_nao_certificaveis,
                            cursada=matricula_diario.situacao == MatriculaDiario.SITUACAO_APROVADO,
                            certificada=False,
                            aproveitada=False,
                            equivalente=False,
                            professores=professores,
                        )
                        componentes.append(componente)
                        if repetir:
                            repetir = not (
                                matricula_diario.situacao == MatriculaDiario.SITUACAO_APROVADO
                                or matricula_diario.situacao == MatriculaDiario.SITUACAO_CURSANDO
                                or matricula_diario.situacao == MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO
                                or matricula_diario.situacao == MatriculaDiario.SITUACAO_DISPENSADO
                                or matricula_diario.situacao == MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO
                            )
                        if not componente_cursado and not repetir:
                            componente_cursado = componente
                for certificacao in CertificacaoConhecimento.objects.select_related('componente_curricular__componente').filter(
                    matricula_periodo__aluno=self, componente_curricular__componente=componente_curricular.componente
                ):
                    professores = []
                    for professor in certificacao.professores.all():
                        professores.append(
                            (
                                certificacao.componente_curricular.componente.sigla,
                                certificacao.componente_curricular.componente.descricao_historico,
                                professor.vinculo.pessoa.nome,
                                professor.get_titulacao(),
                            )
                        )
                    for servidor in certificacao.servidores.all():
                        professores.append(
                            (
                                certificacao.componente_curricular.componente.sigla,
                                certificacao.componente_curricular.componente.descricao_historico,
                                servidor.nome,
                                servidor.get_titulacao(),
                            )
                        )
                    cursada = certificacao.is_aluno_aprovado()
                    componente = dict(
                        pk=componente_curricular.pk,
                        matricula_diario=None,
                        matricula_diario_resumida=None,
                        ano_periodo_letivo=f'{certificacao.matricula_periodo.ano_letivo}/{certificacao.matricula_periodo.periodo_letivo}',
                        periodo_matriz=certificacao.componente_curricular.periodo_letivo,
                        sigla_componente=certificacao.componente_curricular.componente.sigla,
                        descricao_componente=certificacao.componente_curricular.componente.descricao_historico,
                        codigo_turma=None,
                        codigo_diario=None,
                        carga_horaria=certificacao.componente_curricular.componente.ch_hora_relogio or '-',
                        media_final_disciplina=certificacao.get_media_final_disciplina_exibicao(),
                        percentual_carga_horaria_frequentada=not certificacao.ausente and 100 or None,
                        situacao_display=certificacao.get_situacao_certificacao(),
                        situacao_legend='',
                        certificavel=False,
                        cursada=cursada,
                        certificada=certificacao.pk,
                        aproveitada=False,
                        equivalente=False,
                        professores=professores,
                    )
                    if not final or cursada:
                        componentes.append(componente)
                    if repetir:
                        repetir = not cursada
                    if not componente_cursado and not repetir:
                        componente_cursado = componente
                for aproveitamento in AproveitamentoEstudo.objects.select_related('componente_curricular__componente').filter(
                    matricula_periodo__aluno=self, componente_curricular__componente=componente_curricular.componente
                ):
                    professores = []
                    for professor in aproveitamento.professores.all():
                        professores.append(
                            (
                                aproveitamento.componente_curricular.componente.sigla,
                                aproveitamento.componente_curricular.componente.descricao_historico,
                                professor.vinculo.pessoa.nome,
                                professor.get_titulacao(),
                            )
                        )
                    for servidor in aproveitamento.servidores.all():
                        professores.append(
                            (
                                aproveitamento.componente_curricular.componente.sigla,
                                aproveitamento.componente_curricular.componente.descricao_historico,
                                servidor.nome,
                                servidor.get_titulacao(),
                            )
                        )
                    componente = dict(
                        pk=componente_curricular.pk,
                        matricula_diario=None,
                        matricula_diario_resumida=None,
                        ano_periodo_letivo=f'{aproveitamento.matricula_periodo.ano_letivo}/{aproveitamento.matricula_periodo.periodo_letivo}',
                        periodo_matriz=aproveitamento.componente_curricular.periodo_letivo,
                        sigla_componente=aproveitamento.componente_curricular.componente.sigla,
                        descricao_componente=aproveitamento.componente_curricular.componente.descricao_historico,
                        codigo_turma=None,
                        codigo_diario=None,
                        carga_horaria=aproveitamento.componente_curricular.componente.ch_hora_relogio or '-',
                        media_final_disciplina=aproveitamento.get_media_final_disciplina_exibicao(),
                        percentual_carga_horaria_frequentada=aproveitamento.frequencia,
                        situacao_display='Aproveit. Disciplina',
                        situacao_legend=aproveitamento.escola_origem,
                        certificavel=False,
                        cursada=True,
                        certificada=False,
                        aproveitada=aproveitamento.pk,
                        equivalente=False,
                        professores=professores,
                    )
                    componentes.append(componente)
                    if repetir:
                        repetir = False
                    if not componente_cursado and not repetir:
                        componente_cursado = componente
                for aproveitamento in AproveitamentoComponente.objects.select_related('componente_curricular__componente').filter(
                    matricula_periodo__aluno=self, componente_curricular__componente=componente_curricular.componente
                ):
                    componente = dict(
                        pk=componente_curricular.pk,
                        matricula_diario=None,
                        matricula_diario_resumida=None,
                        ano_periodo_letivo=f'{aproveitamento.matricula_periodo.ano_letivo}/{aproveitamento.matricula_periodo.periodo_letivo}',
                        periodo_matriz=aproveitamento.componente_curricular.periodo_letivo,
                        sigla_componente=aproveitamento.componente_curricular.componente.sigla,
                        descricao_componente=aproveitamento.componente_curricular.componente.descricao_historico,
                        codigo_turma=None,
                        codigo_diario=None,
                        carga_horaria=aproveitamento.componente_curricular.componente.ch_hora_relogio or '-',
                        media_final_disciplina=None,
                        percentual_carga_horaria_frequentada=None,
                        situacao_display='Cumprida',
                        situacao_legend='',
                        certificavel=False,
                        cursada=True,
                        certificada=False,
                        aproveitada=False,
                        equivalente=aproveitamento.pk,
                    )
                    componentes.append(componente)
                    if repetir:
                        repetir = False
                    if not componente_cursado and not repetir:
                        componente_cursado = componente
                    observacoes.append(aproveitamento.get_observacao_historico())
                for registro_historico in RegistroHistorico.objects.select_related('componente').filter(matricula_periodo__aluno=self, componente=componente_curricular.componente):
                    cursada = registro_historico.is_cumprida()
                    componente = dict(
                        pk=componente_curricular.pk,
                        matricula_diario=None,
                        matricula_diario_resumida=None,
                        ano_periodo_letivo=f'{registro_historico.matricula_periodo.ano_letivo}/{registro_historico.matricula_periodo.periodo_letivo}',
                        periodo_matriz=componente_curricular.periodo_letivo,
                        sigla_componente=registro_historico.componente.sigla,
                        descricao_componente=registro_historico.componente.descricao_historico,
                        codigo_turma=registro_historico.codigo_turma,
                        codigo_diario=registro_historico.codigo_diario,
                        carga_horaria=registro_historico.componente.ch_hora_relogio or '-',
                        media_final_disciplina=registro_historico.get_media_final_disciplina_exibicao(),
                        percentual_carga_horaria_frequentada=registro_historico.frequencia,
                        situacao_display=registro_historico.get_situacao_display(),
                        situacao_legend='',
                        certificavel=False,
                        cursada=cursada,
                        certificada=False,
                        aproveitada=False,
                        equivalente=False,
                        professores=[(registro_historico.componente.sigla, registro_historico.componente.descricao_historico, registro_historico.nome_professor, registro_historico.titularidade_professor)] if registro_historico.nome_professor else []
                    )
                    componentes.append(componente)
                    if repetir:
                        repetir = not cursada
                    if not componente_cursado and not repetir:
                        componente_cursado = componente
                if repetir:
                    if (exibir_optativas or not componente_curricular.optativo) and not self.is_fic():
                        componente = dict(
                            pk=componente_curricular.pk,
                            matricula_diario=None,
                            matricula_diario_resumida=None,
                            ano_periodo_letivo=None,
                            periodo_matriz=componente_curricular.periodo_letivo,
                            sigla_componente=componente_curricular.componente.sigla,
                            descricao_componente=componente_curricular.componente.descricao_historico,
                            codigo_turma=None,
                            codigo_diario=None,
                            carga_horaria=componente_curricular.componente.ch_hora_relogio or '-',
                            media_final_disciplina=None,
                            percentual_carga_horaria_frequentada=None,
                            situacao_display=None,
                            situacao_legend='',
                            certificavel=componente_curricular.componente.pk not in pk_nao_certificaveis,
                            cursada=False,
                            certificada=False,
                            aproveitada=False,
                            equivalente=False,
                        )
                        componentes.append(componente)

                        if (
                            componente_curricular.componente_curricular_associado
                            and componente_curricular.componente_curricular_associado.componente.id not in ids_componenentes_associados_pagos
                        ):
                            componentes = componente_curricular.componente_curricular_associado.get_grupo_componente_historico(grupos_componentes)
                            componente_associado = dict(
                                pk=componente_curricular.pk,
                                matricula_diario=None,
                                matricula_diario_resumida=None,
                                ano_periodo_letivo=None,
                                periodo_matriz=componente_curricular.componente_curricular_associado.periodo_letivo,
                                sigla_componente=componente_curricular.componente_curricular_associado.componente.sigla,
                                descricao_componente=componente_curricular.componente_curricular_associado.componente.descricao_historico,
                                codigo_turma=None,
                                codigo_diario=None,
                                carga_horaria=componente_curricular.componente_curricular_associado.componente.ch_hora_relogio or '-',
                                media_final_disciplina=None,
                                percentual_carga_horaria_frequentada=None,
                                situacao_display=None,
                                situacao_legend='',
                                certificavel=componente_curricular.componente_curricular_associado.componente.pk not in pk_nao_certificaveis,
                                cursada=False,
                                certificada=False,
                                aproveitada=False,
                                equivalente=False,
                            )
                            componentes.append(componente_associado)
                else:
                    if (
                        componente_curricular.componente_curricular_associado
                        and componente_curricular.componente_curricular_associado.componente.id not in ids_componenentes_associados_pagos
                    ):
                        componentes = componente_curricular.componente_curricular_associado.get_grupo_componente_historico(grupos_componentes)
                        if componente_cursado:
                            componente_associado = dict(
                                pk=componente_curricular.componente_curricular_associado.pk,
                                matricula_diario=None,
                                matricula_diario_resumida=None,
                                ano_periodo_letivo=componente_cursado['ano_periodo_letivo'],
                                periodo_matriz=componente_curricular.componente_curricular_associado.periodo_letivo,
                                sigla_componente=componente_curricular.componente_curricular_associado.componente.sigla,
                                descricao_componente=componente_curricular.componente_curricular_associado.componente.descricao_historico,
                                codigo_turma=componente_cursado['codigo_turma'],
                                codigo_diario=componente_cursado['codigo_diario'],
                                carga_horaria=componente_curricular.componente_curricular_associado.componente.ch_hora_relogio or '-',
                                media_final_disciplina=componente_cursado['media_final_disciplina'],
                                percentual_carga_horaria_frequentada=None,
                                situacao_display=componente_cursado['situacao_display'],
                                situacao_legend='',
                                certificavel=False,
                                cursada=False,
                                certificada=False,
                                aproveitada=False,
                                equivalente=False,
                            )
                        else:
                            componente_associado = dict(
                                pk=componente_curricular.componente_curricular_associado.pk,
                                matricula_diario=None,
                                matricula_diario_resumida=None,
                                ano_periodo_letivo=None,
                                periodo_matriz=componente_curricular.componente_curricular_associado.periodo_letivo,
                                sigla_componente=componente_curricular.componente_curricular_associado.componente.sigla,
                                descricao_componente=componente_curricular.componente_curricular_associado.componente.descricao_historico,
                                codigo_turma=None,
                                codigo_diario=None,
                                carga_horaria=componente_curricular.componente_curricular_associado.componente.ch_hora_relogio or '-',
                                media_final_disciplina=None,
                                percentual_carga_horaria_frequentada=None,
                                situacao_display=None,
                                situacao_legend='',
                                certificavel=componente_curricular.componente_curricular_associado.componente.pk not in pk_nao_certificaveis,
                                cursada=False,
                                certificada=False,
                                aproveitada=False,
                                equivalente=False,
                            )
                        componentes.append(componente_associado)

            # ADICIONANDO OS COMPONENTES EXTRA-CURRICULARES VINDAS DO SUAP
            for matricula_diario in (
                MatriculaDiario.objects.select_related('diario__componente_curricular__componente')
                .filter(matricula_periodo__aluno=self)
                .exclude(diario__componente_curricular__componente__id__in=qs_componentes_curriculares.values_list('componente__id', flat=True))
            ):
                componentes = grupos_componentes['Componentes Extra-Curriculares']
                componente = dict(
                    pk=componente_curricular.pk,
                    matricula_diario=matricula_diario,
                    ano_periodo_letivo=f'{matricula_diario.matricula_periodo.ano_letivo}/{matricula_diario.matricula_periodo.periodo_letivo}',
                    periodo_matriz=componente_curricular.periodo_letivo,
                    sigla_componente=matricula_diario.get_sigla_componente(),
                    descricao_componente=matricula_diario.get_descricao_componente(),
                    codigo_turma=matricula_diario.get_codigo_turma(),
                    codigo_diario=matricula_diario.diario.pk,
                    carga_horaria=matricula_diario.get_carga_horaria() or '-',
                    media_final_disciplina=matricula_diario.situacao == MatriculaDiario.SITUACAO_CURSANDO and '-' or matricula_diario.get_media_final_disciplina_exibicao(),
                    percentual_carga_horaria_frequentada=matricula_diario.get_percentual_carga_horaria_frequentada()
                    if matricula_diario.situacao
                    not in [
                        MatriculaDiario.SITUACAO_CURSANDO,
                        MatriculaDiario.SITUACAO_PROVA_FINAL,
                        MatriculaDiario.SITUACAO_CANCELADO,
                        MatriculaDiario.SITUACAO_TRANCADO,
                        MatriculaDiario.SITUACAO_PENDENTE,
                        MatriculaDiario.SITUACAO_DISPENSADO,
                    ]
                    else None,
                    situacao_display=matricula_diario.get_situacao_display(),
                    situacao_legend='',
                    certificavel=matricula_diario.situacao == MatriculaDiario.SITUACAO_CURSANDO and componente_curricular.componente.pk not in pk_nao_certificaveis,
                    cursada=matricula_diario.situacao == MatriculaDiario.SITUACAO_APROVADO,
                    certificada=False,
                    aproveitada=False,
                    equivalente=False,
                )
                if final and matricula_diario.is_componente_integralizado() or not final:
                    componentes.append(componente)

            # ADICIONANDO OS COMPONENTES EXTRA-CURRICULARES VINDAS DO Q-ACADÊMICO
            for matricula_diario in (
                MatriculaDiarioResumida.objects.exclude(situacao__in=[MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA])
                .select_related('equivalencia_componente')
                .filter(matricula_periodo__aluno=self)
                .exclude(equivalencia_componente__componente__id__in=qs_componentes_curriculares.values_list('componente__id', flat=True))
            ):

                componentes = grupos_componentes['Componentes Extra-Curriculares']
                componente = dict(
                    pk=None,
                    matricula_diario=None,
                    matricula_diario_resumida=matricula_diario,
                    ano_periodo_letivo=f'{matricula_diario.matricula_periodo.ano_letivo}/{matricula_diario.matricula_periodo.periodo_letivo}',
                    periodo_matriz=componente_curricular.periodo_letivo,
                    sigla_componente=matricula_diario.equivalencia_componente.sigla,
                    descricao_componente=matricula_diario.equivalencia_componente.descricao,
                    codigo_turma=matricula_diario.get_codigo_turma(),
                    codigo_diario=matricula_diario.get_codigo_diario(),
                    carga_horaria=matricula_diario.equivalencia_componente.carga_horaria or '-',
                    media_final_disciplina=matricula_diario.get_media_final_disciplina_exibicao(),
                    percentual_carga_horaria_frequentada=matricula_diario.get_percentual_carga_horaria_frequentada(),
                    situacao_display=matricula_diario.get_situacao_display(),
                    situacao_legend='',
                    certificavel=False,
                    cursada=matricula_diario.situacao == MatriculaDiario.SITUACAO_APROVADO,
                    certificada=False,
                    aproveitada=False,
                    equivalente=False,
                )
                componentes.append(componente)

            # ADICIONANDO OS COMPONENTES EXTRA-CURRICULARES VINDAS DO REGISTRO HISTORICO (TRANSFERENCIA DE CURSO)
            for registro_historico in (
                RegistroHistorico.objects.select_related('componente')
                .filter(matricula_periodo__aluno=self)
                .exclude(componente__id__in=qs_componentes_curriculares.values_list('componente__id', flat=True))
            ):
                componentes = grupos_componentes['Componentes Extra-Curriculares']
                componente = dict(
                    pk=None,
                    matricula_diario=None,
                    matricula_diario_resumida=None,
                    ano_periodo_letivo=f'{registro_historico.matricula_periodo.ano_letivo}/{registro_historico.matricula_periodo.periodo_letivo}',
                    periodo_matriz=componente_curricular.periodo_letivo,
                    sigla_componente=registro_historico.componente.sigla,
                    descricao_componente=registro_historico.componente.descricao_historico,
                    codigo_turma=registro_historico.codigo_turma,
                    codigo_diario=registro_historico.codigo_diario,
                    carga_horaria=registro_historico.componente.ch_hora_relogio or '-',
                    media_final_disciplina=registro_historico.get_media_final_disciplina_exibicao(),
                    percentual_carga_horaria_frequentada=registro_historico.frequencia,
                    situacao_display=registro_historico.get_situacao_display(),
                    situacao_legend='',
                    certificavel=False,
                    cursada=False,
                    certificada=False,
                    aproveitada=False,
                    equivalente=False,
                )
                componentes.append(componente)

            for grupo in list(grupos_componentes.values()):
                for componente in grupo:
                    componente['sigla_componente'] = insert_space(componente['sigla_componente'], 9)

            if ordernar_por == Aluno.ORDENAR_HISTORICO_POR_PERIODO_LETIVO:
                for grupo in list(grupos_componentes.keys()):
                    grupos_componentes[grupo] = sorted(grupos_componentes[grupo], key=lambda s: s['ano_periodo_letivo'] or '0')

            if ordernar_por == Aluno.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ:
                for grupo in list(grupos_componentes.keys()):
                    grupos_componentes[grupo] = sorted(
                        grupos_componentes[grupo], key=lambda s: (s['periodo_matriz'] or 0, s['sigla_componente'] or '', s['ano_periodo_letivo'] or '0')
                    )

            uo = self.curso_campus.diretoria.setor.uo
            filiacao = []
            if self.nome_pai:
                filiacao.append(self.nome_pai)
            if self.nome_mae:
                filiacao.append(self.nome_mae)
            filiacao = normalizar_nome_proprio(format_iterable(filiacao))

            if self.observacao_historico:
                observacoes.append(self.observacao_historico)

            historico = dict()
            historico.update(assinatura_eletronica=eletronico)
            # CABEÇALHO
            historico.update(
                nome_campus=uo.nome,
                telefone_campus=uo.telefone,
                endereco_campus=uo.endereco,
                municipio_campus=uo.municipio and uo.municipio.nome or None,
                hoje=datetime.date.today(),
                uf_campus=uo.municipio and uo.municipio.uf or None,
                cep_campus=uo.cep,
                cnpj_campus=uo.cnpj,
                codigo_inep=uo.codigo_inep,
                codigo_emec=uo.codigo_emec,
                novo_modelo=datetime.date.today() >= datetime.date(2019, 4, 25),
                credenciamento=Configuracao.get_valor_por_chave('edu', 'credenciamento'),
                recredenciamento=Configuracao.get_valor_por_chave('edu', 'recredenciamento'),
            )
            # DADOS PESSOAIS
            historico.update(
                sexo=self.pessoa_fisica.sexo,
                nome=self.get_nome_social_composto(),
                cpf=self.pessoa_fisica.cpf,
                data_nascimento=self.pessoa_fisica.nascimento_data,
                nacionalidade=self.nacionalidade and self.get_nacionalidade_display() or None,
                naturalidade=self.naturalidade,
            )
            historico.update(professores=[])
            # RG
            historico.update(numero_rg=self.numero_rg, orgao_emissao_rg=self.orgao_emissao_rg, uf_emissao_rg=self.uf_emissao_rg, data_emissao_rg=self.data_emissao_rg)
            # FILIAÇÃO
            historico.update(nome_pai=self.nome_pai, nome_mae=self.nome_mae)
            # ENDEREÇO
            historico.update(logradouro=self.logradouro, numero=self.numero, complemento=self.complemento, bairro=self.bairro, cidade=self.cidade, cep=self.cep)
            # TÍTULO DE ELEITOR
            historico.update(
                numero_titulo_eleitor=self.numero_titulo_eleitor,
                zona_titulo_eleitor=self.zona_titulo_eleitor,
                secao_titulo_eleitor=self.secao,
                uf_emissao_titulo_eleitor=self.uf_emissao_titulo_eleitor,
                data_emissao_titulo_eleitor=self.data_emissao_titulo_eleitor,
            )
            # CARTEIRA RESERVISTA
            historico.update(
                numero_carteira_reservista=self.numero_carteira_reservista,
                regiao_carteira_reservista=self.regiao_carteira_reservista,
                serie_carteira_reservista=self.serie_carteira_reservista,
                uf_emissao_carteira_reservista=self.estado_emissao_carteira_reservista,
                ano_carteira_reservista=self.ano_carteira_reservista,
            )
            # DADOS ACADEMICOS
            historico.update(
                ira=self.get_ira(),
                matricula=self.matricula,
                situacao=self.situacao,
                forma_ingresso=self.forma_ingresso,
                data_matricula=self.data_matricula,
                ano_periodo_ingresso=f'{self.ano_letivo}/{self.periodo_letivo}',
                mes_ano_processo_seletivo=self.get_mes_ano_processo_seletivo(),
                descricao_linha_pesquisa=self.linha_pesquisa and self.linha_pesquisa.descricao,
            )
            # DADOS DO CURSO
            historico.update(
                codigo_emec_curso=self.curso_campus.codigo_emec,
                descricao_curso=self.curso_campus.descricao_historico,
                regime=self.matriz.estrutura.get_tipo_avaliacao_display,
                periodicidade=self.curso_campus.get_periodicidade_display,
                descricao_matriz=self.matriz.descricao,
                reconhecimento_texto=self.matriz_curso.get_reconhecimento(),
                resolucao_criacao=self.matriz_curso.get_autorizacao()
            )

            # TCC
            projeto_final = self.get_projeto_final()
            historico.update(
                exige_tcc=self.matriz.exige_tcc,
                apresentou_tcc=projeto_final is not None,
                tipo_projeto=projeto_final and projeto_final.tipo,
                titulo_projeto=projeto_final and projeto_final.titulo,
                data_defesa=projeto_final and projeto_final.resultado_data,
                situacao_projeto=projeto_final and projeto_final.get_situacao_display(),
                nota_projeto=projeto_final and projeto_final.nota,
            )
            # ENADE
            convocacoes = []
            for registro_convocacao_enade in self.get_convocacoes_enade():
                registro = {}
                registro.update(
                    data_prova_enade=registro_convocacao_enade.convocacao_enade and registro_convocacao_enade.convocacao_enade.data_prova or '-',
                    ano_letivo_enade=registro_convocacao_enade.convocacao_enade and registro_convocacao_enade.convocacao_enade.ano_letivo.ano or '-',
                    situacao_enade=registro_convocacao_enade.get_situacao_display,
                    justificativa_enade=registro_convocacao_enade.justificativa_dispensa,
                    tipo_convocacao=registro_convocacao_enade.get_tipo_convocacao_display()
                )
                convocacoes.append(registro)
            historico.update(
                exige_enade=self.curso_campus.exige_enade,
                foi_convocado_enade=len(convocacoes) > 0,
                convocacoes=convocacoes,
            )
            # ATIVIDADES COMPLEMENTARES
            historico.update(exige_accs=self.get_ch_atividades_complementares_esperada() > 0, accs=self.get_atividades_complementares().filter(deferida=True))
            # QUADRO RESUMO
            historico.update(
                ch_componentes_obrigatorios=self.matriz and self.get_ch_componentes_regulares_obrigatorios_esperada() or 0,
                ch_componentes_obrigatorios_cumprida=self.matriz and self.get_ch_componentes_regulares_obrigatorios_cumprida() or 0,
                ch_componentes_optativos=self.matriz and self.get_ch_componentes_regulares_optativos_esperada() or 0,
                ch_componentes_optativos_cumprida=self.matriz and self.get_ch_componentes_regulares_optativos_cumprida() or 0,
                ch_componentes_eletivos=self.matriz and self.get_ch_componentes_eletivos_esperada() or 0,
                ch_componentes_eletivos_cumprida=self.matriz and self.get_ch_componentes_eletivos_cumprida() or 0,
                ch_componentes_seminario=self.matriz and self.get_ch_componentes_seminario_esperada() or 0,
                ch_componentes_seminario_cumprida=self.matriz and self.get_ch_componentes_seminario_cumprida() or 0,
                ch_componentes_pratica_como_componente=self.matriz and self.get_ch_pratica_como_componente_esperada() or 0,
                ch_componentes_pratica_como_componente_cumprida=self.matriz and self.get_ch_componentes_pratica_como_componente_cumprida() or 0,
                ch_componentes_visita_tecnica=self.matriz and self.get_ch_visita_tecnica_esperada() or 0,
                ch_componentes_visita_tecnica_cumprida=self.matriz and self.get_ch_componentes_visita_tecnica_cumprida() or 0,
                ch_componentes_pratica_profissional=self.matriz and self.get_ch_componentes_pratica_profissional_esperada(incluir_atpa=True) or 0,
                ch_componentes_pratica_profissional_cumprida=self.matriz and self.get_ch_componentes_pratica_profissional_cumprida(incluir_atpa=True) or 0,
                ch_componentes_tcc=self.matriz and self.get_ch_componentes_tcc_esperada() or 0,
                ch_componentes_tcc_cumprida=self.matriz and self.get_ch_componentes_tcc_cumprida() or 0,
                ch_atividades_complementares=self.matriz and self.get_ch_atividades_complementares_esperada() or 0,
                ch_atividades_complementares_cumprida=self.matriz and self.get_ch_atividades_complementares_cumprida() or 0,
                ch_atividades_extensao=self.matriz and self.get_ch_atividades_extensao_esperada() or 0,
                ch_atividades_extensao_cumprida=self.matriz and self.get_ch_atividade_extensao_cumprida() or 0,
                ch_total=self.matriz and self.matriz.get_carga_horaria_total_prevista() or 0,
                ch_total_cumprida=self.matriz and self.get_carga_horaria_total_cumprida() or 0,
            )
            # DIPLOMA
            registro_emissao_diploma = self.get_registro_emissao_diploma()
            historico.update(
                data_conclusao_curso=self.dt_conclusao_curso,
                data_emissao_diploma=self.data_expedicao_diploma,
                data_colacao_grau=self.get_data_colacao_grau(),
                responsavel_emissao_diploma=registro_emissao_diploma and registro_emissao_diploma.emissor or None,
                emitiu_diploma=registro_emissao_diploma is not None,
                livro=registro_emissao_diploma and registro_emissao_diploma.get_livro(),
                folha=registro_emissao_diploma and registro_emissao_diploma.folha,
                numero_registro=registro_emissao_diploma and registro_emissao_diploma.numero_registro,
                data_expedicao=registro_emissao_diploma and registro_emissao_diploma.data_expedicao,
                dirigente_maximo=registro_emissao_diploma and registro_emissao_diploma.dirigente_maximo or None,
            )
            # DIRETORIA
            historico.update(
                diretor_geral_exercicio=self.curso_campus.diretoria.diretor_geral_exercicio and str(self.curso_campus.diretoria.diretor_geral_exercicio.get_vinculo().relacionamento) or '-',
                diretor_academico_exercicio=self.curso_campus.diretoria.diretor_academico_exercicio and str(self.curso_campus.diretoria.diretor_academico_exercicio.get_vinculo().relacionamento) or '-'
            )
            # COMPONENTES
            historico.update(grupos_componentes=grupos_componentes, observacoes=observacoes)

            return historico

    def get_historico_legado(self, final=True, eletronico=False):
        from edu.q_academico import DAO

        dao = DAO()
        lista_historico_legado = dao.importar_historico_legado_resumo(self)
        q_academico = lista_historico_legado and lista_historico_legado[0] or {}
        grupos_componentes = dict()
        grupos_componentes['Disciplinas'] = []
        grupos_componentes['Prática Profissional'] = []
        observacoes = []
        ch_pratica_profissional_total = 0
        ch_pratica_profissional_total_cumprida = 0
        for linha_historico in lista_historico_legado[1:]:
            componente = dict(
                ano_periodo_letivo=linha_historico['ano_periodo_letivo'],
                periodo_matriz=linha_historico['periodo'],
                sigla_componente=linha_historico['sigla'],
                descricao_componente=linha_historico['descricao'],
                codigo_turma=linha_historico['turma'],
                carga_horaria=linha_historico['carga_horaria'],
                carga_horaria_cumprida=linha_historico['carga_horaria_cumprida'],
                media_final_disciplina=linha_historico['nota'],
                percentual_carga_horaria_frequentada=linha_historico['frequencia'],
                situacao_display=linha_historico['situacao'],
                aproveitada='Aproveit' in linha_historico['situacao'],
                certificada='Certific' in linha_historico['situacao'],
                professores=[[linha_historico['sigla'], linha_historico['descricao'], linha_historico['nome_professor'], linha_historico['titulacao_professor']]],
            )
            if (componente['aproveitada'] or componente['certificada']) and componente['professores']:
                if not componente['professores'][0][2]:
                    componente['professores'][0][2] = 'Não Informado'
                if not componente['professores'][0][3]:
                    componente['professores'][0][3] = 'Graduado(a)'
            if linha_historico['is_pratica_profissional']:
                grupos_componentes['Prática Profissional'].append(componente)
                ch_pratica_profissional_total += linha_historico['carga_horaria'] or 0
                ch_pratica_profissional_total_cumprida += linha_historico['carga_horaria_cumprida'] or 0
            else:
                grupos_componentes['Disciplinas'].append(componente)

            observacao = linha_historico['observacao']
            if observacao:
                observacao = 'A disciplina {} - {} possui a seguinte observação: {}'.format(linha_historico['sigla'], linha_historico['descricao'], observacao)
                observacoes.append(observacao)

        grupos_componentes['Disciplinas'] = sorted(grupos_componentes['Disciplinas'], key=lambda k: k['ano_periodo_letivo'])
        grupos_componentes['Prática Profissional'] = sorted(grupos_componentes['Prática Profissional'], key=lambda k: k['ano_periodo_letivo'])

        historico = dict()
        historico.update(assinatura_eletronica=eletronico)
        uo = self.curso_campus.diretoria.setor.uo
        historico.update(
            nome_campus=uo.nome,
            telefone_campus=uo.telefone,
            endereco_campus=uo.endereco,
            municipio_campus=uo.municipio and uo.municipio.nome or None,
            hoje=datetime.date.today(),
            uf_campus=uo.municipio and uo.municipio.uf or None,
            cep_campus=uo.cep,
            cnpj_campus=uo.cnpj,
            codigo_inep=uo.codigo_inep,
            codigo_emec=uo.codigo_emec,
            novo_modelo=datetime.date.today() >= datetime.date(2019, 4, 25),
            credenciamento=Configuracao.get_valor_por_chave('edu', 'credenciamento'),
            recredenciamento=Configuracao.get_valor_por_chave('edu', 'recredenciamento'),
        )
        # DADOS PESSOAIS
        historico.update(
            sexo=self.pessoa_fisica.sexo,
            nome=self.get_nome_social_composto(),
            cpf=self.pessoa_fisica.cpf,
            data_nascimento=self.pessoa_fisica.nascimento_data,
            nacionalidade=self.nacionalidade and self.get_nacionalidade_display() or None,
            naturalidade=q_academico.get('naturalidade'),
        )
        # RG
        historico.update(numero_rg=self.numero_rg, orgao_emissao_rg=self.orgao_emissao_rg, uf_emissao_rg=self.uf_emissao_rg, data_emissao_rg=self.data_emissao_rg)
        # FILIAÇÃO
        historico.update(nome_pai=self.nome_pai, nome_mae=self.nome_mae)
        # ENDEREÇO
        historico.update(logradouro=self.logradouro, numero=self.numero, complemento=self.complemento, bairro=self.bairro, cidade=self.cidade, cep=self.cep)
        # TÍTULO DE ELEITOR
        historico.update(
            numero_titulo_eleitor=self.numero_titulo_eleitor,
            zona_titulo_eleitor=self.zona_titulo_eleitor,
            secao_titulo_eleitor=self.secao,
            uf_emissao_titulo_eleitor=self.uf_emissao_titulo_eleitor,
            data_emissao_titulo_eleitor=self.data_emissao_titulo_eleitor,
        )
        # CARTEIRA RESERVISTA
        historico.update(
            numero_carteira_reservista=self.numero_carteira_reservista,
            regiao_carteira_reservista=self.regiao_carteira_reservista,
            serie_carteira_reservista=self.serie_carteira_reservista,
            uf_emissao_carteira_reservista=self.estado_emissao_carteira_reservista,
            ano_carteira_reservista=self.ano_carteira_reservista,
        )
        # DADOS ACADEMICOS
        historico.update(
            ira=self.get_ira(),
            matricula=self.matricula,
            situacao=self.situacao,
            forma_ingresso=q_academico.get('forma_ingresso'),
            data_matricula=self.data_matricula,
            ano_periodo_ingresso=f'{self.ano_letivo}/{self.periodo_letivo}',
            mes_ano_processo_seletivo=None,
            descricao_linha_pesquisa=None,
        )
        # DADOS DO CURSO
        historico.update(
            regime=q_academico.get('regime'),
            periodicidade=q_academico.get('periodicidade'),
            descricao_matriz=q_academico.get('matriz'),
            descricao_curso=q_academico.get('curso'),
            resolucao_criacao=q_academico.get('autorizacao'),
            reconhecimento_texto=q_academico.get('reconhecimento'),
        )
        # TCC
        historico.update(
            exige_tcc=q_academico.get('projeto_tipo') is not None,
            apresentou_tcc=q_academico.get('projeto_tipo') is not None,
            tipo_projeto=q_academico.get('projeto_tipo'),
            titulo_projeto=q_academico.get('projeto_titulo'),
            data_defesa=q_academico.get('projeto_data_defesa'),
            situacao_projeto=q_academico.get('projeto_situacao'),
            nota_projeto=q_academico.get('projeto_nota'),
        )
        # ENADE
        convocacao = {}
        justificativas_enade = {
            'Estudante habilitado ao ENADE, devido a sua condição de INGRESSANTE': 'Ingressante / Participante',
            'Estudante dispensado de realização do ENADE, em razão do calendário trienal': 'Dispensado, em razão do calendário trienal',
            'Estudante dispensado conforme Art. 6º, § 2º da Portaria Normativa Nº 8, de 14 de março de 2014': 'Dispensado pelo MEC',
            'Estudante dispensado conforme Art. 9º, § 7º da Portaria Normativa Nº 8, de 14 de março de 2014': 'Dispensado pelo MEC',
            'Estudante dispensado conforme Artº 9, § 7º, da Portaria Normativa nº 8 de 14 de março de 2014': 'Dispensado pelo MEC',
            'Estudante dispensado de realização do ENADE, em razão da natureza do curso': 'Dispensado, em razão da natureza do curso',
            'Estudante dispensado de realização do ENADE, por razão de ordem pessoal': 'Dispensado, por razão de ordem pessoal',
            'Estudante não participante do ENADE, por ato da instituição de ensino': 'Dispensado, por ato da instituição de ensino',
            'Estudante não habilitado ao ENADE em razão do calendário do ciclo avaliativo': 'Estudante não habilitado ao ENADE em razão do calendário do ciclo avaliativo',
            'Estudante não habilitado ao ENADE em razão do calendário do ciclo avaliativo, em razão da pandemia de COVID-19': 'Estudante não habilitado ao ENADE em razão do calendário do ciclo avaliativo'
        }
        convocacao.update(
            situacao_enade=q_academico.get('enade_situacao'),
            data_ultimo_enade=q_academico.get('enade_data_ultimo'),
            data_prova_enade=q_academico.get('enade_data_prova'),
            justificativa_enade=q_academico.get('enade_justificativa'),
            situacao_para_diploma_digital=justificativas_enade.get(q_academico.get('enade_justificativa'), None),
            tipo_convocacao='Concluinte'
        )
        historico.update(
            exige_enade=self.curso_campus.exige_enade,
            foi_convocado_enade=q_academico.get('enade_situacao') is not None,
            convocacoes=[convocacao],
        )
        # DIPLOMA
        registro_emissao_diploma = self.get_registro_emissao_diploma()
        historico.update(
            data_conclusao_curso=self.dt_conclusao_curso,
            data_emissao_diploma=self.data_expedicao_diploma,
            data_colacao_grau=q_academico.get('data_colacao_grau') and q_academico.get('data_colacao_grau').date() or None,
            responsavel_emissao_diploma=registro_emissao_diploma and registro_emissao_diploma.emissor or None,
            emitiu_diploma=registro_emissao_diploma is not None,
            livro=registro_emissao_diploma and registro_emissao_diploma.get_livro(),
            folha=registro_emissao_diploma and registro_emissao_diploma.folha,
            numero_registro=registro_emissao_diploma and registro_emissao_diploma.numero_registro,
            data_expedicao=registro_emissao_diploma and registro_emissao_diploma.data_expedicao,
        )
        # ATIVIDADES COMPLEMENTARES
        accs = q_academico.get('accs')
        ch_accs_total = 0
        if accs:
            for acc in accs:
                acc['ano_letivo'] = Ano.objects.get(ano=acc['ano_letivo'])
                ch_accs_total += acc.get('is_curricular') or 0
        historico.update(accs=accs)
        # CARGAS-HORÁRIAS
        realizou_pcc = (q_academico.get('projeto_tipo', '') or '').encode('utf-8') == 'PCC (Projeto de Conclusão de Curso)'
        historico.update(
            grupos_componentes=grupos_componentes,
            ch_componentes_obrigatorios=int(q_academico.get('ch_obrigatoria_prevista', 0)),
            ch_componentes_optativos=int(q_academico.get('ch_optativa_prevista', 0)),
            ch_componentes_eletivos=0,
            ch_componentes_seminario=0,
            ch_componentes_pratica_profissional=int(q_academico.get('ch_estagio_prevista', 0)) or ch_pratica_profissional_total,
            ch_atividades_complementares=int(q_academico.get('ch_complementar_prevista', 0)),
            ch_componentes_tcc=int(q_academico.get('ch_projeto_prevista', 0)),
            ch_total=int(q_academico.get('ch_prevista', 0)),
            ch_componentes_obrigatorios_cumprida=int(q_academico.get('ch_obrigatoria_cumprida', 0)),
            ch_componentes_optativos_cumprida=int(q_academico.get('ch_optativa_cumprida', 0)),
            ch_componentes_eletivos_cumprida=0,
            ch_componentes_seminario_cumprida=0,
            ch_componentes_pratica_profissional_cumprida=int(q_academico.get('ch_estagio_cumprida', 0) + ch_pratica_profissional_total_cumprida),
            ch_atividades_complementares_cumprida=int(q_academico.get('ch_complementar_cumprida', 0)),
            ch_componentes_tcc_cumprida=int(q_academico.get('projeto_ch', 0)),
            ch_total_cumprida=int(q_academico.get('ch_cumprida', 0)),
        )

        if realizou_pcc:
            historico['ch_componentes_tcc_cumprida'] = 0

        if ch_accs_total > historico['ch_atividades_complementares_cumprida']:
            historico['ch_atividades_complementares_cumprida'] = ch_accs_total

        historico['ch_total_cumprida'] = (
            historico['ch_componentes_obrigatorios_cumprida']
            + historico['ch_componentes_optativos_cumprida']
            + historico['ch_componentes_eletivos_cumprida']
            + historico['ch_componentes_seminario_cumprida']
            + historico['ch_componentes_pratica_profissional_cumprida']
            + historico['ch_atividades_complementares_cumprida']
        )
        historico['ch_total'] = (
            historico['ch_componentes_obrigatorios']
            + historico['ch_componentes_optativos']
            + historico['ch_componentes_eletivos']
            + historico['ch_componentes_seminario']
            + historico['ch_componentes_pratica_profissional']
            + historico['ch_atividades_complementares']
            + historico['ch_componentes_tcc']
        )

        # adicionar TCC apenas se previsto na matriz
        if historico['ch_componentes_tcc']:
            historico['ch_total_cumprida'] += historico['ch_componentes_tcc_cumprida']

        # OBSERVAÇÕES
        historico.update(observacoes=observacoes)
        return historico

    def get_historico_legado_sica(self, final=True, eletronico=False):
        if self.is_sica():
            from sica.models import Historico
            historico_sica = Historico.objects.filter(aluno_id=self.pk).first()
            uo = self.curso_campus.diretoria.setor.uo
            observacoes = []
            if self.observacao_historico:
                observacoes.append(self.observacao_historico)

            grupos_componentes = dict()
            grupos_componentes['Disciplinas Curriculares'] = []

            for registro_historico in historico_sica.get_registros_curriculares():
                componentes = grupos_componentes['Disciplinas Curriculares']
                componente = dict(
                    pk=registro_historico.componente.pk,
                    matricula_diario=None,
                    matricula_diario_resumida=None,
                    ano_periodo_letivo=f'{registro_historico.ano}/{registro_historico.periodo}',
                    periodo_matriz=registro_historico.periodo_matriz,
                    sigla_componente=registro_historico.componente.sigla,
                    descricao_componente=registro_historico.componente.nome,
                    codigo_turma=registro_historico.turma,
                    codigo_diario='',
                    carga_horaria=registro_historico.get_carga_horaria() or '-',
                    media_final_disciplina=registro_historico.get_nota(),
                    percentual_carga_horaria_frequentada=registro_historico.get_frequencia(),
                    situacao_display=registro_historico.get_situacao(),
                    situacao_legend='',
                    certificavel=False,
                    cursada=False,
                    certificada=False,
                    aproveitada=False,
                    equivalente=False,
                )
                componentes.append(componente)

            historico = dict()
            historico.update(assinatura_eletronica=eletronico)
            historico.update(legado_sica=True)

            # CABEÇALHO
            historico.update(
                nome_campus=uo.nome,
                telefone_campus=uo.telefone,
                endereco_campus=uo.endereco,
                municipio_campus=uo.municipio and uo.municipio.nome or None,
                hoje=datetime.date.today(),
                uf_campus=uo.municipio and uo.municipio.uf or None,
                cep_campus=uo.cep,
                cnpj_campus=uo.cnpj,
                codigo_inep=uo.codigo_inep,
                codigo_emec=uo.codigo_emec,
                novo_modelo=datetime.date.today() >= datetime.date(2019, 4, 25),
                credenciamento=Configuracao.get_valor_por_chave('edu', 'credenciamento'),
                recredenciamento=Configuracao.get_valor_por_chave('edu', 'recredenciamento'),
            )
            # DADOS PESSOAIS
            historico.update(
                sexo=self.pessoa_fisica.sexo,
                nome=self.get_nome_social_composto(),
                cpf=self.pessoa_fisica.cpf,
                data_nascimento=self.pessoa_fisica.nascimento_data,
                nacionalidade=self.nacionalidade and self.get_nacionalidade_display() or None,
                naturalidade=self.naturalidade,
            )
            historico.update(professores=[])
            # RG
            historico.update(numero_rg=self.numero_rg, orgao_emissao_rg=self.orgao_emissao_rg, uf_emissao_rg=self.uf_emissao_rg, data_emissao_rg=self.data_emissao_rg)
            # FILIAÇÃO
            historico.update(nome_pai=self.nome_pai, nome_mae=self.nome_mae)
            # ENDEREÇO
            historico.update(logradouro=self.logradouro, numero=self.numero, complemento=self.complemento, bairro=self.bairro, cidade=self.cidade, cep=self.cep)
            # TÍTULO DE ELEITOR
            historico.update(
                numero_titulo_eleitor=self.numero_titulo_eleitor,
                zona_titulo_eleitor=self.zona_titulo_eleitor,
                secao_titulo_eleitor=self.secao,
                uf_emissao_titulo_eleitor=self.uf_emissao_titulo_eleitor,
                data_emissao_titulo_eleitor=self.data_emissao_titulo_eleitor,
            )
            # CARTEIRA RESERVISTA
            historico.update(
                numero_carteira_reservista=self.numero_carteira_reservista,
                regiao_carteira_reservista=self.regiao_carteira_reservista,
                serie_carteira_reservista=self.serie_carteira_reservista,
                uf_emissao_carteira_reservista=self.estado_emissao_carteira_reservista,
                ano_carteira_reservista=self.ano_carteira_reservista,
            )
            # DADOS ACADEMICOS
            historico.update(
                ira=None,
                matricula=self.matricula,
                situacao=self.situacao,
                forma_ingresso='',
                data_matricula='',
                ano_periodo_ingresso=f'{self.ano_letivo}/{self.periodo_letivo}',
                mes_ano_processo_seletivo='',
                descricao_linha_pesquisa=self.linha_pesquisa and self.linha_pesquisa.descricao,
            )
            # DADOS DO CURSO
            historico.update(
                codigo_emec_curso=self.curso_campus.codigo_emec,
                descricao_curso=self.curso_campus.descricao_historico,
                # regime=self.matriz.estrutura.get_tipo_avaliacao_display,
                periodicidade=self.curso_campus.get_periodicidade_display,
                descricao_matriz=historico_sica.matriz.nome,
                reconhecimento_texto=historico_sica.matriz.reconhecimento,
                # resolucao_criacao=self.matriz_curso.get_autorizacao()
            )
            # TCC
            historico.update(
                exige_tcc=False,
                apresentou_tcc=False,
            )
            # ENADE
            historico.update(
                exige_enade=False,
            )
            # DIPLOMA
            registro_emissao_diploma = self.get_registro_emissao_diploma()
            historico.update(
                data_conclusao_curso=self.dt_conclusao_curso,
                data_emissao_diploma=self.data_expedicao_diploma,
                data_colacao_grau=self.get_data_colacao_grau(),
                responsavel_emissao_diploma=registro_emissao_diploma and registro_emissao_diploma.emissor or None,
                emitiu_diploma=registro_emissao_diploma is not None,
                livro=registro_emissao_diploma and registro_emissao_diploma.get_livro(),
                folha=registro_emissao_diploma and registro_emissao_diploma.folha,
                numero_registro=registro_emissao_diploma and registro_emissao_diploma.numero_registro,
                data_expedicao=registro_emissao_diploma and registro_emissao_diploma.data_expedicao,
                dirigente_maximo=registro_emissao_diploma and registro_emissao_diploma.dirigente_maximo or None,
            )
            # DIRETORIA
            historico.update(
                diretor_geral_exercicio=self.curso_campus.diretoria.diretor_geral_exercicio and str(self.curso_campus.diretoria.diretor_geral_exercicio.get_vinculo().relacionamento) or '-',
                diretor_academico_exercicio=self.curso_campus.diretoria.diretor_academico_exercicio and str(self.curso_campus.diretoria.diretor_academico_exercicio.get_vinculo().relacionamento) or '-'
            )
            # COMPONENTES
            historico.update(grupos_componentes=grupos_componentes, observacoes=observacoes)

            # CH
            historico.update(ch_cumprida=historico_sica.get_ch_cumprida() or 0)
            historico.update(ch_geral=historico_sica.get_ch_geral() or 0)
            historico.update(ch_especial=historico_sica.get_ch_especial() or 0)
            historico.update(carga_horaria_estagio=historico_sica.carga_horaria_estagio or 0)

            return historico

    def get_procedimentos_matricula(self):
        return ProcedimentoMatricula.objects.filter(matricula_periodo__aluno=self).order_by('-data')

    def is_user(self, request):
        return request.user.id and request.user.id == self.pessoa_fisica.user_id

    def get_ext_combo_template(self):
        out = [f'<dt class="sr-only">Nome</dt><dd><strong>{self}</strong></dd>']
        img_src = self.get_foto_75x100_url()
        out.append(f'<dt class="sr-only">Curso</dt><dd>{self.curso_campus}</dd>')
        if 'ae' in settings.INSTALLED_APPS:
            Caracterizacao = apps.get_model('ae', 'Caracterizacao')
            caracterizacao_existe = Caracterizacao.objects.filter(aluno=self).exists()
            if not caracterizacao_existe:
                out.append('<dt class="sr-only">Caracterização</dt><dd class="false">Não realizou caracterização</dd>')
            else:
                out.append('<dt class="sr-only">Caracterização</dt><dd class="true">Realizou caracterização</dd>')
            if self.inscricao_set.exists():
                out.append('<dt class="sr-only">Inscrição</dt><dd class="true">Inscrito em programa</dd>')
            else:
                out.append('<dt class="sr-only">Inscrição</dt><dd class="false">Não inscrito em programa</dd>')
        template = '''<div class="person">
            <div class="photo-circle">
                <img src="{}" alt="Foto de {}" />
            </div>
            <dl>{}</dl>
        </div>'''.format(
            img_src, self, ''.join(out)
        )
        return template

    @property
    def username(self):
        return self.pessoa_fisica.username

    @property
    def campus(self):
        return self.curso_campus.diretoria.setor.uo

    def pode_ser_excluido(self, is_superuser=False):
        if is_superuser or self.eh_aluno_minicurso():
            return True
        qs_notas = MatriculaDiario.objects.filter(matricula_periodo__aluno=self, matricula_periodo__aluno__curso_campus__ativo=True).exclude(
            nota_1=None, nota_2=None, nota_3=None, nota_4=None, nota_final=None
        )
        qs_procedimentos = ProcedimentoMatricula.objects.filter(matricula_periodo__aluno=self)
        return (self.is_matriculado() or self.is_matricula_vinculo()) and self.matriz and not qs_notas.exists() and not qs_procedimentos.exists()

    def possui_pendencia(self, incluir_colacao_grau=True, incluir_enade=True):
        return (
            self.pendencia_tcc
            or (incluir_enade and self.pendencia_enade)
            or (incluir_colacao_grau and self.pendencia_colacao_grau)
            or self.pendencia_ch_atividade_complementar
            or self.pendencia_ch_tcc
            or self.pendencia_ch_pratica_profissional
            or self.pendencia_ch_seminario
            or self.pendencia_ch_eletiva
            or self.pendencia_ch_optativa
            or self.pendencia_ch_obrigatoria
            or self.pendencia_pratica_profissional
            or self.pendencia_ch_atividades_extensao
        )

    def pode_realizar_colacao_grau(self, ano_letivo, periodo_letivo):
        if self.matriculaperiodo_set.filter(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo, situacao_id=SituacaoMatriculaPeriodo.EM_ABERTO).exists():
            return False
        if self.matriculaperiodo_set.filter(situacao_id=SituacaoMatriculaPeriodo.MATRICULADO).exists():
            return False
        if self.curso_campus.exige_colacao_grau:
            self.atualizar_situacao('Reprocessamento do Histórico')  # reprocessa o histórico para atualizar os boleanos de pendência.
        return self.curso_campus.exige_colacao_grau and not self.possui_pendencia(incluir_colacao_grau=False)

    def possui_pratica_profissional_pendente(self):
        if self.matriz:
            possui_pratica_profissional_cadastrada = self.praticaprofissional_set.exists() or self.aprendizagem_set.exists() or self.atividadeprofissionalefetiva_set.exists()

            if self.matriz.exige_estagio and not possui_pratica_profissional_cadastrada:
                return True

            if possui_pratica_profissional_cadastrada:
                if self.matriz.exige_estagio:

                    return self.matriz.ch_minima_estagio > self.get_ch_pratica_profissional_concluida()
                else:
                    return (
                        self.praticaprofissional_set.filter(data_fim__isnull=True).exists()
                        or self.aprendizagem_set.filter(data_encerramento__isnull=True).exists()
                        or self.atividadeprofissionalefetiva_set.filter(encerramento__isnull=True).exists()
                    )
            else:
                ch_pratica_profissional_esperada = self.matriz.ch_pratica_profissional
                ch_pratica_profissional_cumprida = self.get_ch_componentes_pratica_profissional_cumprida()
                return ch_pratica_profissional_cumprida < ch_pratica_profissional_esperada
        return False

    def get_ch_pratica_profissional_concluida(self):
        ch_pratica = self.praticaprofissional_set.filter(data_fim__isnull=False).aggregate(Sum('ch_final')).get('ch_final__sum') or 0
        ch_aprendizagem = self.aprendizagem_set.filter(data_encerramento__isnull=False).aggregate(Sum('ch_final')).get('ch_final__sum') or 0
        ch_atividade_efetiva = self.atividadeprofissionalefetiva_set.filter(encerramento__isnull=False).aggregate(Sum('ch_final')).get('ch_final__sum') or 0
        return ch_pratica + ch_aprendizagem + ch_atividade_efetiva

    def get_situacao(self):

        if self.matriz_id and self.curso_campus.is_fic():
            self.pendencia_ch_obrigatoria = self.get_componentes_pendentes().exists()
        elif self.matriz_id:
            if self.matriz.exige_tcc:
                self.pendencia_tcc = not self.apresentou_tcc()
            else:
                self.pendencia_tcc = False
            if self.curso_campus.exige_enade:
                self.pendencia_enade = not self.cumpriu_enade()
            if self.matriz.ch_pratica_profissional >= 1 or self.matriz.exige_estagio:
                self.pendencia_pratica_profissional = self.possui_pratica_profissional_pendente()
            else:
                self.pendencia_pratica_profissional = False
            if self.curso_campus.exige_colacao_grau:
                self.pendencia_colacao_grau = not self.colou_grau()
            self.pendencia_ch_atividade_complementar = self.get_ch_atividades_complementares_esperada() and self.get_ch_atividades_complementares_pendente() > 0 or False
            if self.get_ch_componentes_tcc_esperada():
                self.pendencia_ch_tcc = self.get_ch_componentes_tcc_pendente() > 0
            self.pendencia_ch_pratica_profissional = self.get_ch_componentes_pratica_profissional_esperada() and (self.get_ch_componentes_pratica_profissional_pendente() > 0)
            self.pendencia_ch_atividades_aprofundamento = self.get_ch_atividade_aprofundamento_esperada() and (self.get_ch_atividade_aprofundamento_pendente() > 0)
            self.pendencia_ch_atividades_extensao = self.get_ch_atividade_extensao_esperada() and (self.get_ch_atividade_extensao_pendente() > 0)
            if self.get_ch_componentes_seminario_esperada():
                self.pendencia_ch_seminario = self.get_ch_componentes_seminario_pendente() > 0
            if self.get_ch_pratica_como_componente_esperada():
                self.pendencia_ch_pratica_como_componente = self.get_ch_componentes_pratica_como_componente_pendente() > 0
            if self.get_ch_visita_tecnica_esperada():
                self.pendencia_ch_visita_tecnica = self.get_ch_componentes_visita_tecnica_pendente() > 0

            self.pendencia_ch_eletiva = self.get_ch_componentes_eletivos_pendente() > 0
            self.pendencia_ch_optativa = self.get_ch_componentes_regulares_optativos_pendente() > 0
            self.pendencia_ch_obrigatoria = self.get_ch_componentes_regulares_obrigatorios_pendente() > 0

        # Caso o aluno ainda esteja com algum período letivo aberto, sua situação será "Matriculado"
        if MatriculaPeriodo.objects.filter(aluno=self, situacao__id=SituacaoMatriculaPeriodo.MATRICULADO).exists():
            return SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)

        # Cursos FICs possuem apenas um período letivo e requer, portanto, um tratamentno diferenciado
        if self.curso_campus.is_fic():
            if MatriculaPeriodo.objects.filter(aluno=self, situacao__id=SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA).exists():
                return SituacaoMatricula.objects.get(pk=SituacaoMatricula.NAO_CONCLUIDO)
            else:
                if self.possui_pendencia():
                    return SituacaoMatricula.objects.get(pk=SituacaoMatricula.NAO_CONCLUIDO)
                else:
                    return SituacaoMatricula.objects.get(pk=SituacaoMatricula.CONCLUIDO)
        else:
            # Caso o aluno não possua nenhum período letivo aberto, mas não cumpriu todos os requisitos de conclusão
            if self.possui_pendencia():
                if self.get_ultima_matricula_periodo().situacao == SituacaoMatriculaPeriodo.MATRICULADO:
                    return SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                else:
                    return self.situacao
            else:
                # Caso o aluno possua um matrícula no período com sistuação "Em Aberto", essa matrícula será excluída
                qs_em_aberto = MatriculaPeriodo.objects.filter(aluno=self, situacao__id=SituacaoMatriculaPeriodo.EM_ABERTO)
                if qs_em_aberto.filter(
                    creditoespecial__isnull=True,
                    matriculadiario__isnull=True,
                    matriculadiarioresumida__isnull=True,
                    certificacaoconhecimento__isnull=True,
                    aproveitamentoestudo__isnull=True,
                    projetofinal__isnull=True,
                ).exists():
                    qs_em_aberto.delete()
                if qs_em_aberto.exists():
                    return SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                else:
                    # A situação dos concluintes de cursos que requer colação de graua deve ser "Formado"
                    if self.curso_campus.exige_colacao_grau:
                        return SituacaoMatricula.objects.get(pk=SituacaoMatricula.FORMADO)
                    else:
                        return SituacaoMatricula.objects.get(pk=SituacaoMatricula.CONCLUIDO)

    def calcular_indice_rendimento(self, parcial=False, matriculaperiodo=None):
        # Alunso Proitec não possuem I.R.A calculado pelo sistem
        from edu.models import RegistroHistorico, HistoricoSituacaoMatricula

        if self.matriz and self.matriz.estrutura.proitec:
            return

        numerador = 0
        denominador = 0

        # Consultando os registros de matrícula em diários
        matriculas_diario = MatriculaDiario.objects.filter(matricula_periodo__aluno=self).exclude(diario__componente_curricular__qtd_avaliacoes=0)

        # exclui as mastriculas com situação em aberto se não for parcial
        if not parcial:
            matriculas_diario = matriculas_diario.filter(
                situacao__in=[MatriculaDiario.SITUACAO_APROVADO, MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA]
            ).exclude(matricula_periodo__situacao__id__in=[SituacaoMatriculaPeriodo.MATRICULADO])

        # Consultando os registros de matrícula em diários do Q-Acadêmcio
        matriculas_diario_resumida = MatriculaDiarioResumida.objects.filter(
            media_final_disciplina__isnull=False,
            matricula_periodo__aluno=self,
            situacao__in=[
                MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO,
                MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO,
                MatriculaDiario.SITUACAO_APROVADO,
                MatriculaDiario.SITUACAO_REPROVADO,
                MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA,
            ],
        ).exclude(matricula_periodo__situacao__id__in=[SituacaoMatriculaPeriodo.MATRICULADO])

        # filtra por matrícula período
        if matriculaperiodo is not None:
            matriculas_diario = matriculas_diario.filter(matricula_periodo__ano_letivo__ano__lte=matriculaperiodo.ano_letivo.ano)
            matriculas_diario_resumida = matriculas_diario_resumida.filter(matricula_periodo__ano_letivo__ano__lte=matriculaperiodo.ano_letivo.ano)
            if matriculaperiodo.periodo_letivo == 1:
                matriculas_diario = matriculas_diario.exclude(matricula_periodo__ano_letivo__ano=matriculaperiodo.ano_letivo.ano, matricula_periodo__periodo_letivo=2)
                matriculas_diario_resumida = matriculas_diario_resumida.exclude(
                    matricula_periodo__ano_letivo__ano=matriculaperiodo.ano_letivo.ano, matricula_periodo__periodo_letivo=2
                )

        # Consultando as certificações de conhecimento
        certificacoes_conhecimento = CertificacaoConhecimento.objects.filter(matricula_periodo__aluno=self, ausente=False).exclude(componente_curricular__qtd_avaliacoes=0)
        # Consultando os aproveitamentos de estudo
        aproveitamentos_estudo = AproveitamentoEstudo.objects.filter(matricula_periodo__aluno=self).exclude(componente_curricular__qtd_avaliacoes=0)
        # Consultando os registros de histórico (criados para alunos oriundos de tranferências)
        registros_historico = RegistroHistorico.objects.filter(matricula_periodo__aluno=self).exclude(situacao__in=(MatriculaDiario.SITUACAO_CURSANDO, MatriculaDiario.SITUACAO_PROVA_FINAL))

        # Média aritimética dos componentes
        if self.matriz and self.matriz.estrutura.ira == EstruturaCurso.IRA_ARITMETICA_NOTAS_FINAIS:
            for matricula_diario in matriculas_diario:
                # plano de retomada de aulas em virtude da pandemia (COVID19)
                if not matricula_diario.deve_ser_ignorada_no_calculo_do_ira():
                    numerador += matricula_diario.get_media_final_disciplina() or 0
            denominador += matriculas_diario.count()
            for matricula_diario_resumida in matriculas_diario_resumida:
                numerador += matricula_diario_resumida.media_final_disciplina
            denominador += matriculas_diario_resumida.count()
            for certificacao_conhecimento in certificacoes_conhecimento:
                numerador += certificacao_conhecimento.nota
            denominador += certificacoes_conhecimento.count()
            for aproveitamento_estudo in aproveitamentos_estudo:
                numerador += aproveitamento_estudo.nota
            denominador += aproveitamentos_estudo.count()
            for registro_historico in registros_historico:
                numerador += registro_historico.media_final_disciplina
            denominador += registros_historico.count()

        # Média ponderada em relação as notas e carga-horárias dos componentes
        else:
            for matricula_diario in matriculas_diario:
                # plano de retomada de aulas em virtude da pandemia (COVID19)
                if not matricula_diario.deve_ser_ignorada_no_calculo_do_ira():
                    if matricula_diario.diario.componente_curricular.componente.ch_hora_relogio:
                        numerador += matricula_diario.diario.componente_curricular.componente.ch_hora_relogio * (matricula_diario.get_media_final_disciplina() or 0)
                        denominador += matricula_diario.diario.componente_curricular.componente.ch_hora_relogio
            for matricula_diario_resumida in matriculas_diario_resumida:
                if matricula_diario_resumida.equivalencia_componente.carga_horaria:
                    numerador += matricula_diario_resumida.equivalencia_componente.carga_horaria * matricula_diario_resumida.media_final_disciplina
                    denominador += matricula_diario_resumida.equivalencia_componente.carga_horaria
            for certificacao_conhecimento in certificacoes_conhecimento:
                if certificacao_conhecimento.componente_curricular.componente.ch_hora_relogio:
                    numerador += certificacao_conhecimento.componente_curricular.componente.ch_hora_relogio * certificacao_conhecimento.nota
                    denominador += certificacao_conhecimento.componente_curricular.componente.ch_hora_relogio
            for aproveitamento_estudo in aproveitamentos_estudo:
                if aproveitamento_estudo.componente_curricular.componente.ch_hora_relogio:
                    numerador += aproveitamento_estudo.componente_curricular.componente.ch_hora_relogio * aproveitamento_estudo.nota
                    denominador += aproveitamento_estudo.componente_curricular.componente.ch_hora_relogio
            for registro_historico in registros_historico:
                if registro_historico.componente.ch_hora_relogio and registro_historico.media_final_disciplina:
                    numerador += registro_historico.componente.ch_hora_relogio * registro_historico.media_final_disciplina
                    denominador += registro_historico.componente.ch_hora_relogio

        ira = 0
        if denominador:
            ira = Decimal(str(numerador)) / denominador

        if parcial or matriculaperiodo is not None:
            return ira
        else:
            self.ira = ira
            HistoricoSituacaoMatricula.objects.create(aluno=self, situacao=self.situacao, data=datetime.datetime.now())
            self.save()

    def get_ira(self):
        return mask_nota(self.ira)

    def atualizar_situacao_ultimo_periodo(self):
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()
        if ultima_matricula_periodo.situacao.pk == SituacaoMatriculaPeriodo.EM_ABERTO and (ultima_matricula_periodo.matriculadiario_set.exists() or ultima_matricula_periodo.turma):
            ultima_matricula_periodo.situacao_id = SituacaoMatriculaPeriodo.MATRICULADO
            ultima_matricula_periodo.save()

    def atualizar_situacao(self, descricao_operacao=None):
        if self.situacao.id in [SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL]:
            self.situacao = self.get_situacao()
            self.save()

            self.calcular_indice_rendimento()
            self.atualizar_situacao_ultimo_periodo()
            self.atualizar_periodo_referencia()
            self.atualizar_data_conclusao()
            self.atualizar_percentual_ch_cumprida()
            self.calcular_ch_aulas_visita_tecnica()
            self.calcular_ch_aulas_pcc()

    def atualizar_data_conclusao(self):
        if self.situacao.pk == SituacaoMatricula.CONCLUIDO or self.situacao.pk == SituacaoMatricula.FORMADO:
            # A data de conclusão é a maior data da última ativiade curricular do aluno

            dt_temp = None
            if self.dt_conclusao_curso:
                dt_temp = self.dt_conclusao_curso
            self.dt_conclusao_curso = None

            # Consultando a data de término do último período do aluno (CalendarioAcademico)
            ultima_matricula_periodo = self.get_ultima_matricula_periodo()
            matricula_diario = ultima_matricula_periodo.matriculadiario_set.all().first()
            if matricula_diario and matricula_diario.diario and matricula_diario.diario.calendario_academico and matricula_diario.diario.calendario_academico.data_fim:
                self.dt_conclusao_curso = matricula_diario.diario.calendario_academico.data_fim
                # se o período-letivo ainda não foi concluído
                if self.dt_conclusao_curso > datetime.date.today():
                    ultimos_diarios = ultima_matricula_periodo.matriculadiario_set.values_list('diario', flat=True)
                    ultima_aula = Aula.objects.filter(professor_diario__diario__in=ultimos_diarios, data__lte=datetime.date.today()).order_by('-data').first()
                    # a data de conclusão é o último dia de aula
                    if ultima_aula:
                        self.dt_conclusao_curso = ultima_aula.data
                    # a data de conclusão é o dia atual
                    else:
                        self.dt_conclusao_curso = datetime.date.today()

            # RegistroConvocacaoENADE
            if self.curso_campus.exige_enade:
                registro_convocacao_enade = self.get_enade_concluinte()
                if registro_convocacao_enade and registro_convocacao_enade.convocacao_enade and registro_convocacao_enade.convocacao_enade.data_prova:
                    if self.dt_conclusao_curso is None or registro_convocacao_enade.convocacao_enade.data_prova > self.dt_conclusao_curso:
                        if registro_convocacao_enade.convocacao_enade.data_prova <= datetime.date.today():
                            self.dt_conclusao_curso = registro_convocacao_enade.convocacao_enade.data_prova

            # ProjetoFinal
            if self.matriz.exige_tcc:
                projeto_final = self.get_projeto_final_aprovado()
                if projeto_final and projeto_final.resultado_data:
                    if self.dt_conclusao_curso is None or projeto_final.resultado_data.date() > self.dt_conclusao_curso:
                        self.dt_conclusao_curso = projeto_final.resultado_data.date()

            # AtividadeComplementar
            if self.matriz.configuracao_atividade_academica:
                ultima_atividade_complementar_curricular = self.get_ultima_atividade_complementar_curricular()
                if ultima_atividade_complementar_curricular and ultima_atividade_complementar_curricular.data_atividade:
                    if self.dt_conclusao_curso is None or ultima_atividade_complementar_curricular.data_atividade > self.dt_conclusao_curso:
                        self.dt_conclusao_curso = ultima_atividade_complementar_curricular.data_atividade

            # ParticipacaoColacaoGrau
            if self.curso_campus.exige_colacao_grau:
                participacao_colacao_grau = self.get_participacao_colacao_grau()
                if participacao_colacao_grau and participacao_colacao_grau.colacao_grau.data_colacao:
                    # após 25/04/2019 a data de colação de grau passou a ser desconsiderada como data de conclusão do curso
                    if participacao_colacao_grau.colacao_grau.data_colacao < datetime.date(2019, 4, 25):
                        self.dt_conclusao_curso = participacao_colacao_grau.colacao_grau.data_colacao

            # Estagio
            # TODO

            if self.dt_conclusao_curso is None:
                if dt_temp:
                    self.dt_conclusao_curso = dt_temp
                else:
                    self.dt_conclusao_curso = datetime.date.today()

            self.ano_conclusao = self.get_ultima_matricula_periodo().ano_letivo.ano

        else:
            self.dt_conclusao_curso = None
            self.ano_conclusao = None
        self.save()

    def __str__(self):
        return f'{normalizar_nome_proprio(self.get_nome_social_composto())} ({self.matricula})'

    def get_vinculo(self):
        return self.vinculos.first()

    def get_user(self):
        qs = User.objects.filter(username=self.matricula)
        return qs.exists() and qs[0] or None

    def save(self, *args, **kwargs):
        if not self.ano_let_prev_conclusao:
            self.definir_ano_let_prev_conclusao()
        super().save(*args, **kwargs)

        self.pessoa_fisica.nome = normalizar_nome_proprio(self.pessoa_fisica.nome)
        self.pessoa_fisica.eh_aluno = True
        if self.passaporte:
            self.pessoa_fisica.passaporte = self.passaporte
        if self.eh_aluno_minicurso() and not self.situacao.ativo:
            self.pessoa_fisica.username = None
        self.pessoa_fisica.save()

        user = self.get_user()
        qs = Vinculo.objects.filter(alunos=self)
        if not qs.exists():
            vinculo = Vinculo()
        else:
            vinculo = qs.first()
        vinculo.pessoa = self.pessoa_fisica.pessoa_ptr
        vinculo.user = user
        vinculo.relacionamento = self
        if self.curso_campus:
            vinculo.setor = self.curso_campus.diretoria.setor
        vinculo.save()

    def definir_ano_let_prev_conclusao(self):
        ano_prev_termino = self.ano_letivo.ano
        qtd_periodos_letivos = self.matriz and self.matriz.qtd_periodos_letivos or 0

        # verificando ano previsto de término de cursos semestrais
        if self.curso_campus and self.curso_campus.periodicidade == CursoCampus.PERIODICIDADE_SEMESTRAL:
            count_periodo = int(self.periodo_letivo)
            primeiro = True

            for _ in range(1, qtd_periodos_letivos + 1):
                if count_periodo == 2:
                    count_periodo = 1
                else:
                    if not primeiro:
                        ano_prev_termino += 1
                    count_periodo += 1
                primeiro = False

        # verificando ano previsto de término de cursos anuais
        if self.curso_campus and self.curso_campus.periodicidade == CursoCampus.PERIODICIDADE_ANUAL:
            ano_prev_termino = ano_prev_termino + qtd_periodos_letivos - 1

        self.ano_let_prev_conclusao = ano_prev_termino

    def delete(self, *args, **kwargs):
        self.foto = None
        self.email_academico = ''  # liberando para ser utilizado novamente pelo AD
        self.email_google_classroom = ''  # liberando para ser utilizado novamente pelo google classroom
        self.save()
        user = tl.get_user()
        desfazendo_transferencia = kwargs.pop('desfazendo_transferencia', False)
        if desfazendo_transferencia or not user or (self.pode_ser_excluido(user.is_superuser) and perms.realizar_procedimentos_academicos(user, self.curso_campus)):
            if self.pessoa_fisica and self.pessoa_fisica.user:

                if not running_tests() and not settings.DEBUG:
                    from ldap_backend.models import LdapConf
                    ldap_conf = LdapConf.get_active()
                    if self.pessoa_fisica.username:
                        ldap_conf.sync_user(self.pessoa_fisica.username)  # sincronizando com o AD para liberar o email acadêmico

                self.pessoa_fisica.user = None
                self.pessoa_fisica.username = None
                self.pessoa_fisica.save()
                qs = User.objects.filter(username=self.matricula)
                if qs.exists():
                    qs[0].delete()
            super().delete(*args, **kwargs)
        else:
            raise Exception('Aluno não pode ser excluído.')

    def get_endereco(self):
        if self.logradouro:
            lista = []
            if self.logradouro:
                lista.append(self.logradouro)
            if self.numero:
                lista.append(self.numero)
            if self.bairro:
                lista.append(self.bairro)
            if self.cep:
                lista.append(self.cep)
            if self.cidade:
                lista.append(str(self.cidade))
            return ', '.join(lista)
        else:
            return None

    def get_rg(self):
        rg = '-'
        if self.numero_rg:
            rg = self.numero_rg
            if self.orgao_emissao_rg:
                rg += f' - {self.orgao_emissao_rg}'
            if self.uf_emissao_rg:
                rg += f'({self.uf_emissao_rg.get_sigla()})'
        return rg

    def get_absolute_url(self):
        return f'/edu/aluno/{self.matricula}/'

    def get_urls_documentos(self):
        lista = []
        if self.pode_emitir_declaracao():
            lista.append(('Declaração de Vínculo', f'/edu/declaracaovinculo_pdf/{self.pk}/'))
        if self.possui_historico():
            if self.matriz and not self.is_concluido():
                lista.append(('Histórico Parcial', f'/edu/emitir_historico_parcial_pdf/{self.pk}/'))
            if self.is_matriculado() and self.matriz and self.pode_emitir_declaracao():
                lista.append(('Declaração de Carga Horária Integralizada', f'/edu/declaracao_ch_cumprida_pdf/{self.pk}/'))
                if not self.is_ultima_matricula_em_aberto():
                    lista.append(('Declaração de Matrícula', f'/edu/declaracaomatricula_pdf/{self.pk}/'))
                    lista.append(('Comprovante de Dados Acadêmicos', f'/edu/comprovante_dados_academicos_pdf/{self.pk}'))
        return lista

    def get_ch_componentes_cumpridos(self, apenas_curriculares=False, ano=None):
        ids = apenas_curriculares and self.matriz.get_ids_componentes() or None
        return Componente.objects.filter(pk__in=self.get_ids_componentes_cumpridos(ids, ano=ano)).aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0

    def get_percentual_ch_componentes_cumpridos(self):
        try:
            if not self.matriz:
                return -1
            percentual = 100 * Decimal(self.get_ch_componentes_cumpridos(True)) / Decimal(self.matriz.get_carga_horaria_total_prevista())
            return percentual > 100 and 100 or percentual
        except ZeroDivisionError:
            return 0

    def get_ids_componentes_cumpridos(self, ids=None, ano=None, matricula_periodo=None):
        ids_componentes_curriculares_cumpridos = self.get_ids_componentes_curriculares_cumpridos(ano=ano, matricula_periodo=matricula_periodo)
        if ids is None:
            return ids_componentes_curriculares_cumpridos
        lista = []
        for i in ids:
            if i in ids_componentes_curriculares_cumpridos:
                lista.append(i)
        return lista

    def get_ids_componentes_cursando(self):
        if hasattr(self, 'ids_componentes_cursando'):
            return self.ids_componentes_cursando
        self.ids_componentes_cursando = MatriculaDiario.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_CURSANDO).values_list(
            'diario__componente_curricular__componente__id', flat=True
        )
        return self.ids_componentes_cursando

    def get_ids_componentes_curriculares_cumpridos(self, ano=None, matricula_periodo=None):
        from edu.models.historico import RegistroHistorico

        if hasattr(self, 'ids_componentes_curriculares_cumpridos') and not matricula_periodo:
            return self.ids_componentes_curriculares_cumpridos

        if not self.matriz:
            return []
        if self.matriz.estrutura.proitec:
            if self.situacao.id == SituacaoMatricula.NAO_CONCLUIDO:
                return []
            return self.matriz.get_ids_componentes()

        ids = self.matriz.get_ids_componentes()
        md = MatriculaDiario.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_APROVADO).filter(diario__componente_curricular__componente__id__in=ids)
        mdr = MatriculaDiarioResumida.objects.filter(
            matricula_periodo__aluno=self,
            situacao__in=[
                MatriculaDiario.SITUACAO_APROVADO,
                MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO,
                MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO,
                MatriculaDiario.SITUACAO_DISPENSADO,
            ],
        ).filter(equivalencia_componente__componente__id__in=ids)
        cc = CertificacaoConhecimento.objects.filter(matricula_periodo__aluno=self, nota__gte=self.matriz.estrutura.media_certificacao_conhecimento or 70).filter(
            componente_curricular__componente__id__in=ids
        )
        ae = AproveitamentoEstudo.objects.filter(matricula_periodo__aluno=self).filter(componente_curricular__componente__id__in=ids)
        ac = AproveitamentoComponente.objects.filter(matricula_periodo__aluno=self).filter(componente_curricular__componente__id__in=ids)
        rh = RegistroHistorico.objects.filter(matricula_periodo__aluno=self).filter(componente__id__in=ids).exclude(situacao__in=(MatriculaDiario.SITUACAO_CURSANDO, MatriculaDiario.SITUACAO_PROVA_FINAL))

        if ano:
            md = md.filter(matricula_periodo__ano_letivo__ano__lte=ano)
            mdr = mdr.filter(matricula_periodo__ano_letivo__ano__lte=ano)
            cc = cc.filter(matricula_periodo__ano_letivo__ano__lte=ano)
            ae = ae.filter(matricula_periodo__ano_letivo__ano__lte=ano)
            ac = ac.filter(matricula_periodo__ano_letivo__ano__lte=ano)
            rh = rh.filter(matricula_periodo__ano_letivo__ano__lte=ano)

        if matricula_periodo:
            md = md.filter(matricula_periodo=matricula_periodo)
            mdr = mdr.filter(matricula_periodo=matricula_periodo)
            cc = cc.filter(matricula_periodo=matricula_periodo)
            ae = ae.filter(matricula_periodo=matricula_periodo)
            ac = ac.filter(matricula_periodo=matricula_periodo)
            rh = rh.filter(matricula_periodo=matricula_periodo)

        lista = []
        for i in md.values_list('diario__componente_curricular__componente__id', flat=True):
            lista.append(i)
        for i in mdr.values_list('equivalencia_componente__componente__id', flat=True):
            lista.append(i)
        for i in cc.values_list('componente_curricular__componente__id', flat=True):
            lista.append(i)
        for i in ae.values_list('componente_curricular__componente__id', flat=True):
            lista.append(i)
        for i in ac.values_list('componente_curricular__componente__id', flat=True):
            lista.append(i)
        for i in rh.values_list('componente__id', flat=True):
            lista.append(i)

        for pk, componente_associado_pk in ComponenteCurricular.objects.filter(matriz=self.matriz, componente_curricular_associado__isnull=False).values_list(
            'componente__id', 'componente_curricular_associado__componente__id'
        ):
            if pk in lista:
                lista.append(componente_associado_pk)

        self.ids_componentes_curriculares_cumpridos = lista
        return self.ids_componentes_curriculares_cumpridos

    def get_ids_componentes_extra_curriculares_cumpridos(self, excluir_equivalencias=True):
        from edu.models import RegistroHistorico

        if hasattr(self, 'ids_componentes_extra_curriculares_cumpridos'):
            return self.ids_componentes_extra_curriculares_cumpridos
        if not self.matriz or self.matriz.estrutura.proitec:
            return []

        ids_componentes_matriz = self.matriz.get_ids_componentes()

        md = MatriculaDiario.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_APROVADO).exclude(
            diario__componente_curricular__componente__id__in=ids_componentes_matriz
        )

        mdr = MatriculaDiarioResumida.objects.filter(
            matricula_periodo__aluno=self,
            situacao__in=[MatriculaDiario.SITUACAO_APROVADO, MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO, MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO],
        ).exclude(equivalencia_componente__componente__id__in=ids_componentes_matriz)
        cc = CertificacaoConhecimento.objects.filter(matricula_periodo__aluno=self, nota__gte=self.matriz.estrutura.media_certificacao_conhecimento or 70).exclude(
            componente_curricular__componente__id__in=ids_componentes_matriz
        )
        ae = AproveitamentoEstudo.objects.filter(matricula_periodo__aluno=self).exclude(componente_curricular__componente__id__in=ids_componentes_matriz)
        ac = AproveitamentoComponente.objects.filter(matricula_periodo__aluno=self).exclude(componente_curricular__componente__id__in=ids_componentes_matriz)
        rh = RegistroHistorico.objects.filter(matricula_periodo__aluno=self).exclude(componente__id__in=ids_componentes_matriz)

        if excluir_equivalencias:
            md = md.exclude(equivalencias_set__isnull=False)
            mdr = mdr.exclude(equivalencias_set__isnull=False)
            rh = rh.exclude(equivalencias_set__isnull=False)

        lista = []
        for i in md.values_list('diario__componente_curricular__componente__id', flat=True):
            lista.append(i)
        for i in mdr.values_list('equivalencia_componente__componente__id', flat=True):
            lista.append(i)
        for i in cc.values_list('componente_curricular__componente__id', flat=True):
            lista.append(i)
        for i in ae.values_list('componente_curricular__componente__id', flat=True):
            lista.append(i)
        for i in ac.values_list('componente_curricular__componente__id', flat=True):
            lista.append(i)
        for i in rh.values_list('componente__id', flat=True):
            lista.append(i)

        self.ids_componentes_extra_curriculares_cumpridos = lista
        return self.ids_componentes_extra_curriculares_cumpridos

    # COMPONENTES

    def get_componentes_cumpridos(self):
        return Componente.objects.filter(id__in=self.get_ids_componentes_cumpridos())

    def get_componentes_cursando(self):
        return Componente.objects.filter(
            componentecurricular__diario__matriculadiario__matricula_periodo__aluno=self, componentecurricular__diario__matriculadiario__situacao=MatriculaDiario.SITUACAO_CURSANDO
        )

    def get_matriculas_diario_cursando(self):
        qs = MatriculaDiario.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_CURSANDO)
        if hasattr(self, 'ano_letivo_referencia'):
            qs = qs.filter(diario__ano_letivo=self.ano_letivo_referencia)
        if hasattr(self, 'periodo_letivo_referencia'):
            qs = qs.filter(diario__periodo_letivo=self.periodo_letivo_referencia)
        return qs

    def get_componentes_pendentes(self, periodos=[], apenas_obrigatorias=False, apenas_optativas=False):
        ids = self.matriz and self.matriz.get_ids_componentes(periodos, apenas_obrigatorias, apenas_optativas) or []
        return Componente.objects.filter(id__in=ids).exclude(id__in=self.get_ids_componentes_cumpridos(ids))

    def get_componentes_em_diarios_pendentes(self):
        ids = MatriculaDiario.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_PENDENTE).values_list(
            'diario__componente_curricular__componente', flat=True
        )
        return Componente.objects.filter(id__in=ids).exclude(id__in=self.get_ids_componentes_cumpridos(ids))

    def get_componentes_obrigatorios_pendentes(self, curriculares=False):
        componentes_pendentes = self.get_componentes_pendentes(apenas_obrigatorias=True)
        if curriculares:
            return self.matriz.componentecurricular_set.filter(componente__id__in=componentes_pendentes.values_list('pk', flat=True)).order_by('tipo').order_by('periodo_letivo')
        else:
            return componentes_pendentes

    def get_componentes_em_dependencia(self):
        periodos = list(range(1, self.periodo_atual))
        ids = self.matriz.get_ids_componentes(periodos, True)
        return Componente.objects.filter(id__in=ids).exclude(id__in=self.get_ids_componentes_cumpridos(ids))

    def atingiu_max_disciplinas(self):
        numero_disciplinas_superior_periodo = self.matriz.estrutura.numero_disciplinas_superior_periodo
        if numero_disciplinas_superior_periodo:
            qtd_componentes_periodo_referencia = self.matriz.componentecurricular_set.filter(periodo_letivo=self.periodo_atual).count()
            if (
                qtd_componentes_periodo_referencia + numero_disciplinas_superior_periodo
                <= self.get_ultima_matricula_periodo().matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).count()
            ):
                return True
        return False

    # COMPONENTES REGULARES OBRIGATÓRIOS

    def get_componentes_regulares_obrigatorios_cumpridos(self, matricula_periodo=None):
        ids = self.matriz.get_ids_componentes_regulares_obrigatorios()
        return Componente.objects.filter(id__in=self.get_ids_componentes_cumpridos(ids, matricula_periodo=matricula_periodo))

    def get_componentes_regulares_obrigatorios_pendentes(self):
        id_todos = self.matriz.get_ids_componentes_regulares_obrigatorios()
        id_cumpridos = self.get_ids_componentes_cumpridos(id_todos)
        id_pendentes = []
        for id_componente in id_todos:
            if id_componente not in id_cumpridos:
                id_pendentes.append(id_componente)
        return Componente.objects.filter(id__in=id_pendentes)

    def get_componentes_curriculares_regulares_obrigatorios_cumpridos(self):
        ids = self.matriz.get_ids_componentes_regulares_obrigatorios()
        return ComponenteCurricular.objects.filter(componente__id__in=self.get_ids_componentes_cumpridos(ids))

    def get_ch_componentes_regulares_obrigatorios_cumprida(self, matricula_periodo=None):
        s = self.get_componentes_regulares_obrigatorios_cumpridos(matricula_periodo).aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        return s

    def get_ch_componentes_regulares_obrigatorios_esperada(self):
        return self.matriz.ch_componentes_obrigatorios

    def get_ch_componentes_regulares_obrigatorios_pendente(self):
        ch = self.get_ch_componentes_regulares_obrigatorios_esperada()
        if ch:
            ch = ch - self.get_ch_componentes_regulares_obrigatorios_cumprida()
        return ch > 0 and ch or 0

    def completou_ch_componentes_regulares_obrigatorios(self):
        return self.get_ch_componentes_regulares_obrigatorios_pendente() == 0

    # COMPONENTES REGULARES OPTATIVOS

    def get_componentes_regulares_optativos_cumpridos(self, matricula_periodo=None):
        ids = self.matriz.get_ids_componentes_regulares_optativos()
        return Componente.objects.filter(id__in=self.get_ids_componentes_cumpridos(ids, matricula_periodo=matricula_periodo))

    def get_componentes_regulares_optativos_nao_cumpridos(self):
        id_todos = self.matriz.get_ids_componentes_regulares_optativos()
        id_cumpridos = self.get_ids_componentes_cumpridos(id_todos)
        id_pendentes = []
        for id_componente in id_todos:
            if id_componente not in id_cumpridos:
                id_pendentes.append(id_componente)
        return Componente.objects.filter(id__in=id_pendentes)

    def get_componentes_curriculares_optativos_cumpridos(self):
        ids = self.matriz.get_ids_componentes_regulares_optativos()
        return ComponenteCurricular.objects.filter(componente__id__in=self.get_ids_componentes_cumpridos(ids))

    def get_ch_componentes_regulares_optativos_cumprida(self, matricula_periodo=None):
        ch_horaria_equivalente = 0
        if self.matriz.configuracao_creditos_especiais:
            ch_horaria_equivalente = (
                CreditoEspecial.objects.filter(
                    matricula_periodo__in=matricula_periodo and [matricula_periodo] or self.matriculaperiodo_set.all(),
                    item_configuracao_creditos_especiais__configuracao=self.matriz.configuracao_creditos_especiais,
                )
                .aggregate(Sum('item_configuracao_creditos_especiais__equivalencia_creditos'))
                .get('item_configuracao_creditos_especiais__equivalencia_creditos__sum')
                or 0
            )
            if ch_horaria_equivalente > self.matriz.configuracao_creditos_especiais.quantidade_maxima_creditos_especiais:
                ch_horaria_equivalente = self.matriz.configuracao_creditos_especiais.quantidade_maxima_creditos_especiais
            if not self.curso_campus.modalidade.pk == Modalidade.MESTRADO or not self.curso_campus.modalidade.pk == Modalidade.DOUTORADO:
                ch_horaria_equivalente = ch_horaria_equivalente * 20
            else:
                ch_horaria_equivalente = ch_horaria_equivalente * 15
        return (self.get_componentes_regulares_optativos_cumpridos(matricula_periodo).aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0) + ch_horaria_equivalente

    def get_ch_componentes_regulares_optativos_esperada(self):
        return self.matriz.ch_componentes_optativos

    def get_ch_componentes_regulares_optativos_pendente(self):
        ch = self.get_ch_componentes_regulares_optativos_esperada()
        if ch:
            ch = ch - self.get_ch_componentes_regulares_optativos_cumprida()
        return ch > 0 and ch or 0

    def get_ch_componentes_regulares_optativos_cursando(self):
        return (
            ComponenteCurricular.objects.filter(
                diario__matriculadiario__matricula_periodo__aluno=self,
                diario__matriculadiario__situacao=MatriculaDiario.SITUACAO_CURSANDO,
                optativo=True,
                tipo=ComponenteCurricular.TIPO_REGULAR,
            )
            .aggregate(Sum('componente__ch_hora_relogio'))
            .get('componente__ch_hora_relogio__sum')
            or 0
        )

    def completou_ch_componentes_regulares_optativos(self):
        return self.get_ch_componentes_regulares_optativos_pendente() == 0

    # COMPONENTES ELETIVOS

    def get_componentes_eletivos_cumpridos(self):
        return Componente.objects.filter(id__in=self.get_ids_componentes_extra_curriculares_cumpridos())

    def get_ch_componentes_eletivos_cumprida(self):
        return self.get_componentes_eletivos_cumpridos().aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0

    def get_ch_componentes_eletivos_esperada(self):
        return self.matriz.ch_componentes_eletivos

    def get_ch_componentes_eletivos_pendente(self):
        ch = self.get_ch_componentes_eletivos_esperada()
        if ch:
            ch = ch - self.get_ch_componentes_eletivos_cumprida()
        return ch > 0 and ch or 0

    def cursou_componentes_eletivos(self):
        return self.get_ch_componentes_eletivos_pendente() == 0

    def completou_ch_componentes_eletivos(self):
        return self.get_ch_componentes_eletivos_pendente() == 0

    # COMPONENTES DE PRÁTICA COMO COMPONENTE

    def get_diarios_aulas_pcc(self):
        ids = self.matriculaperiodo_set.filter(
            matriculadiario__diario__componente_curricular__ch_pcc__gt=0,
            matriculadiario__situacao=MatriculaDiario.SITUACAO_APROVADO
        ).exclude(
            matriculadiario__diario__componente_curricular__tipo=ComponenteCurricular.TIPO_PRATICA_COMO_COMPONENTE
        ).values_list('matriculadiario__diario_id', flat=True)
        return Diario.objects.filter(id__in=ids)

    def calcular_ch_aulas_pcc(self):
        if self.matriz.ch_pratica_como_componente:
            self.ch_aulas_pcc = 0
            for diario in self.get_diarios_aulas_pcc():
                self.ch_aulas_pcc += diario.get_carga_horaria_pcc_contabilizada(relogio=True)
        return self.ch_aulas_pcc

    def get_ch_componentes_pratica_como_componente_cumprida(self, matricula_periodo=None):
        return self.ch_aulas_pcc + (self.get_componentes_pratica_como_componente_cumpridos(matricula_periodo).aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0)

    def get_componentes_pratica_como_componente_cumpridos(self, matricula_periodo=None):
        ids = self.matriz.get_ids_componentes_pratica_como_componente()
        return Componente.objects.filter(id__in=self.get_ids_componentes_cumpridos(ids, matricula_periodo=matricula_periodo))

    def get_ch_pratica_como_componente_esperada(self):
        return self.matriz.ch_pratica_como_componente

    def get_componentes_pratica_como_componente_nao_cumpridos(self, apenas_obrigatorio=False):
        id_todos = self.matriz.get_ids_componentes_pratica_como_componente(apenas_obrigatorio)
        id_cumpridos = self.get_ids_componentes_cumpridos(id_todos)
        id_pendentes = []
        for id_componente in id_todos:
            if id_componente not in id_cumpridos:
                id_pendentes.append(id_componente)
        return Componente.objects.filter(id__in=id_pendentes)

    def get_componentes_pratica_como_componente_pendentes(self):
        return self.get_componentes_pratica_como_componente_nao_cumpridos(True)

    def get_ch_componentes_pratica_como_componente_pendente(self):
        ch_obrigatoria_pendente = self.get_componentes_pratica_como_componente_pendentes().aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        ch_cumprida = self.get_ch_componentes_pratica_como_componente_cumprida()
        # se o aluno cumpriu os componentes obrigatórios, a ch pendente é a diferença da esperada e cumprida
        # senão, deve-se acrescentar a ch obrigatória pendente dessa diferença
        ch = self.get_ch_pratica_como_componente_esperada() - ch_cumprida
        ch = ch > ch_obrigatoria_pendente and ch or ch_obrigatoria_pendente
        return ch > 0 and ch or 0

    # COMPONENTES DE VISITA TÉCNICA / AULA DE CAMPO

    def get_diarios_aulas_visita_tecnica(self):
        ids = self.matriculaperiodo_set.filter(
            matriculadiario__diario__componente_curricular__ch_visita_tecnica__gt=0,
            matriculadiario__situacao=MatriculaDiario.SITUACAO_APROVADO
        ).values_list('matriculadiario__diario_id', flat=True)
        return Diario.objects.filter(id__in=ids)

    def calcular_ch_aulas_visita_tecnica(self):
        if self.matriz.ch_visita_tecnica:
            self.ch_aulas_visita_tecnica = 0
            for diario in self.get_diarios_aulas_visita_tecnica():
                self.ch_aulas_visita_tecnica += diario.get_carga_horaria_visita_tecnica_contabilizada(relogio=True)
        return self.ch_aulas_visita_tecnica

    def get_ch_componentes_visita_tecnica_cumprida(self, matricula_periodo=None):
        return self.ch_aulas_visita_tecnica + (self.get_componentes_visita_tecnica_cumpridos(matricula_periodo).aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0)

    def get_componentes_visita_tecnica_cumpridos(self, matricula_periodo=None):
        ids = self.matriz.get_ids_componentes_visita_tecnica()
        return Componente.objects.filter(id__in=self.get_ids_componentes_cumpridos(ids, matricula_periodo=matricula_periodo))

    def get_ch_visita_tecnica_esperada(self):
        return self.matriz.ch_visita_tecnica

    def get_componentes_visita_tecnica_nao_cumpridos(self, apenas_obrigatorio=False):
        id_todos = self.matriz.get_ids_componentes_visita_tecnica(apenas_obrigatorio)
        id_cumpridos = self.get_ids_componentes_cumpridos(id_todos)
        id_pendentes = []
        for id_componente in id_todos:
            if id_componente not in id_cumpridos:
                id_pendentes.append(id_componente)
        return Componente.objects.filter(id__in=id_pendentes)

    def get_componentes_visita_tecnica_pendentes(self):
        return self.get_componentes_visita_tecnica_nao_cumpridos(True)

    def get_ch_componentes_visita_tecnica_pendente(self):
        ch_obrigatoria_pendente = self.get_componentes_visita_tecnica_pendentes().aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        ch_cumprida = self.get_ch_componentes_visita_tecnica_cumprida()
        # se o aluno cumpriu os componentes obrigatórios, a ch pendente é a diferença da esperada e cumprida
        # senão, deve-se acrescentar a ch obrigatória pendente dessa diferença
        ch = self.get_ch_visita_tecnica_esperada() - ch_cumprida
        ch = ch > ch_obrigatoria_pendente and ch or ch_obrigatoria_pendente
        return ch > 0 and ch or 0

    # COMPONENTES DE SEMINÁRIO

    def get_componentes_seminario_cumpridos(self, matricula_periodo=None):
        ids = self.matriz.get_ids_componentes_seminario()
        return Componente.objects.filter(id__in=self.get_ids_componentes_cumpridos(ids, matricula_periodo=matricula_periodo))

    def get_componentes_seminario_nao_cumpridos(self, apenas_obrigatorio=False):
        id_todos = self.matriz.get_ids_componentes_seminario(apenas_obrigatorio)
        id_cumpridos = self.get_ids_componentes_cumpridos(id_todos)
        id_pendentes = []
        for id_componente in id_todos:
            if id_componente not in id_cumpridos:
                id_pendentes.append(id_componente)
        return Componente.objects.filter(id__in=id_pendentes)

    def get_componentes_seminario_pendentes(self):
        return self.get_componentes_seminario_nao_cumpridos(True)

    def get_componentes_curriculares_seminario_cumpridos(self):
        ids = self.matriz.get_ids_componentes_seminario()
        return ComponenteCurricular.objects.filter(componente__id__in=self.get_ids_componentes_cumpridos(ids))

    def get_ch_componentes_seminario_cumprida(self, matricula_periodo=None):
        s = self.get_componentes_seminario_cumpridos(matricula_periodo).aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        return s

    def get_ch_componentes_seminario_esperada(self):
        return self.matriz.ch_seminarios

    def get_ch_componentes_seminario_pendente(self):
        ch_obrigatoria_pendente = self.get_componentes_seminario_pendentes().aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        ch_cumprida = self.get_ch_componentes_seminario_cumprida()
        # se o aluno cumpriu os componentes obrigatórios, a ch pendente é a diferença da esperada e cumprida
        # senão, deve-se acrescentar a ch obrigatória pendente dessa diferença
        ch = self.get_ch_componentes_seminario_esperada() - ch_cumprida
        ch = ch > ch_obrigatoria_pendente and ch or ch_obrigatoria_pendente
        return ch > 0 and ch or 0

    def completou_ch_componentes_seminario(self):
        return self.get_ch_componentes_seminario_pendente() == 0

    # COMPONENTES DE PRÁTICA PROFISSIONAL

    def get_componentes_pratica_profissional_cumpridos(self, matricula_periodo=None):
        ids = self.matriz.get_ids_componentes_pratica_profissional()
        return Componente.objects.filter(id__in=self.get_ids_componentes_cumpridos(ids, matricula_periodo=matricula_periodo))

    def get_componentes_pratica_profissional_nao_cumpridos(self, apenas_obrigatorio=False):
        id_todos = self.matriz.get_ids_componentes_pratica_profissional(apenas_obrigatorio)
        id_cumpridos = self.get_ids_componentes_cumpridos(id_todos)
        id_pendentes = []
        for id_componente in id_todos:
            if id_componente not in id_cumpridos:
                id_pendentes.append(id_componente)
        return Componente.objects.filter(id__in=id_pendentes)

    def get_componentes_pratica_profissional_pendentes(self):
        return self.get_componentes_pratica_profissional_nao_cumpridos(True)

    def get_componentes_curriculares_pratica_profissional_cumpridos(self):
        ids = self.matriz.get_ids_componentes_pratica_profissional()
        return ComponenteCurricular.objects.filter(componente__id__in=self.get_ids_componentes_cumpridos(ids))

    def get_ch_componentes_pratica_profissional_cumprida(self, matricula_periodo=None, incluir_atpa=False):
        s = self.get_componentes_pratica_profissional_cumpridos(matricula_periodo).aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        if incluir_atpa:
            s += self.get_ch_atividade_aprofundamento_cumprida()
        return s

    def get_ch_componentes_pratica_profissional_esperada(self, incluir_atpa=False):
        ch = self.matriz and self.matriz.ch_pratica_profissional or 0
        if incluir_atpa:
            ch += self.get_ch_atividade_aprofundamento_esperada()
        return ch

    def get_ch_atividade_aprofundamento_esperada(self):
        return self.matriz and self.matriz.ch_atividades_aprofundamento or 0

    def get_ch_atividade_extensao_esperada(self):
        return self.matriz and self.matriz.ch_atividades_extensao or 0

    def get_ch_atividade_aprofundamento_cumprida(self, matricula_periodo=None):
        qs = self.atividadeaprofundamento_set.filter(deferida=True)
        if matricula_periodo:
            qs = qs.filter(ano_letivo=matricula_periodo.ano_letivo, periodo_letivo=matricula_periodo.periodo_letivo)
        return qs.aggregate(Sum('carga_horaria')).get('carga_horaria__sum') or 0

    def get_atividades_extensao(self):
        return AtividadeCurricularExtensao.objects.filter(matricula_periodo__aluno=self)

    def get_atividades_extensao_aprovadas(self):
        return self.get_atividades_extensao().filter(aprovada=True)

    def get_ch_atividade_extensao_cumprida(self, matricula_periodo=None):
        qs = self.get_atividades_extensao()
        if matricula_periodo:
            qs = qs.filter(matricula_periodo=matricula_periodo)
        return qs.filter(aprovada=True).aggregate(Sum('carga_horaria')).get('carga_horaria__sum') or 0

    def get_ch_atividade_aprofundamento_pendente(self):
        ch_esperada = self.get_ch_atividade_aprofundamento_esperada()
        if ch_esperada:
            ch_cumprida = self.get_ch_atividade_aprofundamento_cumprida()
            if ch_cumprida < ch_esperada:
                return ch_esperada - ch_cumprida
        return 0

    def get_ch_atividade_extensao_pendente(self):
        ch_esperada = self.get_ch_atividade_extensao_esperada()
        if ch_esperada:
            ch_cumprida = self.get_ch_atividade_extensao_cumprida()
            if ch_cumprida < ch_esperada:
                return ch_esperada - ch_cumprida
        return 0

    def get_ch_componentes_pratica_profissional_pendente(self):
        ch_obrigatoria_pendente = self.get_componentes_pratica_profissional_pendentes().aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        ch_cumprida = self.get_ch_componentes_pratica_profissional_cumprida()
        # se o aluno cumpriu os componentes obrigatórios, a ch pendente é a diferença da esperada e cumprida
        # senão, deve-se acrescentar a ch obrigatória pendente dessa diferença
        ch = self.get_ch_componentes_pratica_profissional_esperada() - ch_cumprida
        ch = ch > ch_obrigatoria_pendente and ch or ch_obrigatoria_pendente
        return ch > 0 and ch or 0

    def completou_ch_componentes_pratica_profissional(self):
        return self.get_ch_componentes_pratica_profissional_pendente() == 0

    # COMPONENTES DE TCC

    def get_componentes_tcc_cumpridos(self, matricula_periodo=None):
        ids = self.matriz.get_ids_componentes_tcc()
        if not ids:
            return Componente.objects.none()
        return Componente.objects.filter(id__in=self.get_ids_componentes_cumpridos(ids, matricula_periodo=matricula_periodo))

    def get_componentes_tcc_nao_cumpridos(self, apenas_obrigatorio=False):
        id_todos = self.matriz.get_ids_componentes_tcc(apenas_obrigatorio)
        id_cumpridos = self.get_ids_componentes_cumpridos(id_todos)
        id_pendentes = []
        for id_componente in id_todos:
            if id_componente not in id_cumpridos:
                id_pendentes.append(id_componente)
        return Componente.objects.filter(id__in=id_pendentes)

    def get_componentes_tcc_pendentes(self):
        return self.get_componentes_tcc_nao_cumpridos(True)

    def get_componentes_curriculares_tcc_cumpridos(self):
        ids = self.matriz.get_ids_componentes_tcc()
        return ComponenteCurricular.objects.filter(componente__id__in=self.get_ids_componentes_cumpridos(ids))

    def get_ch_componentes_tcc_cumprida(self, matricula_periodo=None):
        s = self.get_componentes_tcc_cumpridos(matricula_periodo).aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        return s

    def get_ch_componentes_tcc_esperada(self):
        return self.matriz and self.matriz.ch_componentes_tcc or 0

    def get_ch_componentes_tcc_pendente(self):
        ch_obrigatoria_pendente = self.get_componentes_tcc_pendentes().aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
        ch_cumprida = self.get_ch_componentes_tcc_cumprida()
        # se o aluno cumpriu os componentes obrigatórios, a ch pendente é a diferença da esperada e cumprida
        # senão, deve-se acrescentar a ch obrigatória pendente dessa diferença
        ch = self.get_ch_componentes_tcc_esperada() - ch_cumprida
        ch = ch > ch_obrigatoria_pendente and ch or ch_obrigatoria_pendente
        return ch > 0 and ch or 0

    def completou_ch_componentes_tcc(self):
        return self.get_ch_componentes_tcc_pendente() == 0

    # ATIVIDADES COMPLEMENTARES

    def get_atividades_complementares(self, apenas_curriculares=False):
        qs = self.atividadecomplementar_set.all()
        if apenas_curriculares:
            if self.matriz.configuracao_atividade_academica:
                itens_configuracoes = self.matriz.configuracao_atividade_academica.itemconfiguracaoatividadecomplementar_set.all()
                tipos_curriculares = TipoAtividadeComplementar.objects.filter(id__in=itens_configuracoes.values_list('tipo__id', flat=True))
                qs = qs.filter(tipo__in=tipos_curriculares)
        return qs.order_by('ano_letivo', 'periodo_letivo')

    def get_ch_atividades_complementares_por_tipo(self, incluir_todos=False, tipo=None, apenas_obrigatorias=False, ano=None, matricula_periodo=None):
        tipos_curriculares_cumpridos = []

        if self.matriz and self.matriz.configuracao_atividade_academica:
            if incluir_todos:
                itens_configuracoes = self.matriz.configuracao_atividade_academica.itemconfiguracaoatividadecomplementar_set.all()
            else:
                if tipo:
                    itens_configuracoes = self.matriz.configuracao_atividade_academica.itemconfiguracaoatividadecomplementar_set.filter(pk=tipo.pk)
                else:
                    ids_tipos = set(self.atividadecomplementar_set.values_list('tipo__id', flat=True))
                    itens_configuracoes = self.matriz.configuracao_atividade_academica.itemconfiguracaoatividadecomplementar_set
                    itens_configuracoes = itens_configuracoes.filter(tipo__id__in=ids_tipos) | itens_configuracoes.filter(ch_min_curso__gt=0)

            if apenas_obrigatorias:
                itens_configuracoes = itens_configuracoes.filter(ch_min_curso__gt=0)

            tipos_curriculares = TipoAtividadeComplementar.objects.filter(id__in=itens_configuracoes.values_list('tipo__id', flat=True))
            atividades_complementares = self.atividadecomplementar_set.filter(tipo__in=tipos_curriculares)
            periodos = []
            for ano_referencia, periodo_letivo in self.atividadecomplementar_set.values_list('ano_letivo__ano', 'periodo_letivo').distinct():
                if (
                    not matricula_periodo
                    or ano_referencia < matricula_periodo.ano_letivo.ano
                    or (ano_referencia == matricula_periodo.ano_letivo.ano and periodo_letivo <= matricula_periodo.periodo_letivo)
                ):
                    periodos.append((ano_referencia, periodo_letivo))

            # plano de retomada de aulas em virtude da pandemia (COVID19)
            ignorar_limite_nos_periodos_letivos = [(ano, periodo) for ano, periodo in Diario.objects.filter(
                matriculadiario__matricula_periodo__aluno=self, turma__pertence_ao_plano_retomada=True
            ).order_by(
                'turma__ano_letivo__ano', 'turma__periodo_letivo'
            ).values_list(
                'turma__ano_letivo__ano', 'turma__periodo_letivo'
            ).distinct()]

            for item in itens_configuracoes:
                item.tipo.ch_considerada = 0
                item.tipo.ch_total_cumprida = 0
                item.tipo.ch_min_curso = item.ch_min_curso
                item.tipo.ch_max_periodo = item.ch_max_periodo
                item.tipo.ch_max_curso = item.ch_max_curso
                for ano_referencia, periodo_letivo in periodos:
                    qs_atividades = atividades_complementares.filter(ano_letivo__ano=ano_referencia, periodo_letivo=periodo_letivo, tipo=item.tipo)
                    item.ch_periodo_cumprida = 0
                    if ano:
                        qs_atividades = qs_atividades.filter(ano_letivo__ano__lte=ano)
                    for atividade_complementar in qs_atividades:
                        ch = atividade_complementar.carga_horaria
                        item.tipo.ch_total_cumprida += ch
                        if atividade_complementar.deferida:
                            item.ch_periodo_cumprida += ch
                        ignorar_limite_no_periodo = (ano_referencia, periodo_letivo) in ignorar_limite_nos_periodos_letivos
                        if item.ch_max_periodo and item.ch_periodo_cumprida > item.ch_max_periodo and not ignorar_limite_no_periodo:
                            item.ch_periodo_cumprida = item.ch_max_periodo
                    item.tipo.ch_considerada += item.ch_periodo_cumprida
                if item.ch_max_curso and item.tipo.ch_considerada >= item.ch_max_curso and not ignorar_limite_nos_periodos_letivos:
                    item.tipo.ch_considerada = item.ch_max_curso
                item.tipo.ch_por_evento = item.ch_por_evento
                tipos_curriculares_cumpridos.append(item.tipo)

        return tipos_curriculares_cumpridos

    def get_ch_atividades_complementares_esperada(self):
        if self.matriz:
            return self.matriz.ch_atividades_complementares
        else:
            return 0

    def get_ch_atividades_extensao_esperada(self):
        if self.matriz:
            return self.matriz.ch_atividades_extensao
        else:
            return 0

    def get_ch_atividades_complementares_cumprida(self, tipo=None, ano=None, matricula_periodo=None):
        total = 0
        for tipo in self.get_ch_atividades_complementares_por_tipo(tipo=tipo, ano=ano, matricula_periodo=matricula_periodo):
            total += tipo.ch_considerada

        if matricula_periodo:
            tmp_total = total
            if hasattr(self, 'ch_atividades_complementares_cumprida_anterior'):
                total = total - self.ch_atividades_complementares_cumprida_anterior
            setattr(self, 'ch_atividades_complementares_cumprida_anterior', tmp_total)

        return total

    def get_ch_atividades_complementares_cadastrada(self):
        return self.atividadecomplementar_set.all().aggregate(Sum('carga_horaria')).get('carga_horaria__sum') or 0

    def get_ch_atividades_complementares_pendente(self, tipo=None):
        ch = self.get_ch_atividades_complementares_esperada() - self.get_ch_atividades_complementares_cumprida()
        ch = ch > 0 and ch or 0
        if self.matriz and self.matriz.configuracao_atividade_academica:
            for tipo in self.matriz.configuracao_atividade_academica.itemconfiguracaoatividadecomplementar_set.filter(ch_min_curso__gt=0):
                ch_tipo_obrigatorio = tipo.ch_min_curso - self.get_ch_atividades_complementares_cumprida(tipo=tipo)
                if ch_tipo_obrigatorio > 0:
                    ch += ch_tipo_obrigatorio
        return ch

    def completou_ch_atividades_complementares(self):
        return self.get_ch_atividades_complementares_pendente() == 0

    # CRÉDITOS ESPECIAIS

    def get_creditos_especiais(self):
        return CreditoEspecial.objects.filter(matricula_periodo__aluno=self)

    # CARGA HORARIA TOTAL

    def get_carga_horaria_total_cumprida(self):
        carga_horaria = self.get_ch_componentes_regulares_obrigatorios_cumprida() + self.get_ch_componentes_regulares_optativos_cumprida()
        carga_horaria += self.get_ch_componentes_eletivos_cumprida() + self.get_ch_componentes_seminario_cumprida()
        carga_horaria += self.get_ch_componentes_pratica_profissional_cumprida() + self.get_ch_atividades_complementares_cumprida()
        carga_horaria += self.get_ch_componentes_tcc_cumprida()
        return carga_horaria

    # REQUISITOS CONCLUSÃO

    def get_quantidade_requisitos_conclusao_curso(self):
        contador = 0
        if self.matriz:
            if self.get_ch_componentes_regulares_obrigatorios_esperada():
                contador += 1
            if self.get_ch_componentes_regulares_optativos_esperada():
                contador += 1
            if self.get_ch_componentes_eletivos_esperada():
                contador += 1
            if self.get_ch_componentes_seminario_esperada():
                contador += 1
            if self.get_ch_componentes_pratica_profissional_esperada():
                contador += 1
            if self.get_ch_atividades_complementares_esperada():
                contador += 1
            if self.get_ch_componentes_tcc_esperada():
                contador += 1
            if self.curso_campus.exige_colacao_grau:
                contador += 1
            if self.curso_campus.exige_enade:
                contador += 1
            if self.matriz.exige_tcc:
                contador += 1
        return contador

    def tem_acesso_servicos_microsoft(self):
        from microsoft.models import ConfiguracaoAcessoDreamspark

        return ConfiguracaoAcessoDreamspark.is_liberado(self)

    def get_matriculas_periodo(self, ate_ano_letivo=None, ate_periodo_letivo=None, orderbyDesc=True):
        qs = self.matriculaperiodo_set
        if ate_ano_letivo and ate_periodo_letivo:
            if self.curso_campus.periodicidade == CursoCampus.PERIODICIDADE_SEMESTRAL:
                qs = (
                    qs.filter(ano_letivo__ano__lte=ate_ano_letivo.ano)
                    .exclude(ano_letivo__ano=ate_ano_letivo.ano, periodo_letivo=ate_periodo_letivo)
                    .exclude(ano_letivo__ano=ate_ano_letivo.ano, periodo_letivo=2)
                )
            else:
                qs = qs.filter(ano_letivo__ano__lt=ate_ano_letivo.ano)

        if orderbyDesc:
            return qs.order_by('-ano_letivo__ano', '-periodo_letivo')
        else:
            return qs.order_by('ano_letivo__ano', 'periodo_letivo')

    def get_diarios_especiais(self, ate_ano_letivo=None, ate_periodo_letivo=None, orderbyDesc=True):
        qs = self.diarioespecial_set.all()
        if ate_ano_letivo and ate_periodo_letivo:
            qs = qs.filter(ano_letivo__ano__lte=ate_ano_letivo.ano)
            if ate_periodo_letivo == 1:
                qs = qs.exclude(ano_letivo__ano=ate_ano_letivo.ano, periodo_letivo=2)
        if orderbyDesc:
            return qs.order_by('-ano_letivo__ano', '-periodo_letivo')
        else:
            return qs.order_by('ano_letivo__ano', 'periodo_letivo')

    def get_matricula_periodo(self, ano_letivo, periodo_letivo):
        qs = self.get_matriculas_periodo().filter(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)
        return qs.exists() and qs[0] or None

    def get_periodo_referencia(self):
        if hasattr(self, 'ano_letivo_referencia') and hasattr(self, 'periodo_letivo_referencia'):
            qs = self.matriculaperiodo_set.filter(ano_letivo=self.ano_letivo_referencia, periodo_letivo=self.periodo_letivo_referencia)
            if qs.exists():
                mp = qs[0]
        else:
            mp = self.get_ultima_matricula_periodo()
        return mp

    def get_situacao_periodo_referencia(self):
        mp = self.get_periodo_referencia()
        return mp and mp.situacao or None

    def get_data_ultimo_procedimento_periodo_referencia(self):
        if self.get_periodo_referencia().procedimentomatricula_set.first():
            return self.get_periodo_referencia().procedimentomatricula_set.first().data
        return None

    def get_frequencia_periodo_referencia(self):
        mp = self.get_periodo_referencia()
        if mp:
            if mp.matriculadiario_set.exists():
                return mp.get_percentual_carga_horaria_frequentada()
            return 0
        return None

    def get_ultima_matricula_periodo(self):
        return self.get_matriculas_periodo().first()

    def get_turma_periodo_anterior(self):
        qs = self.get_matriculas_periodo()
        if qs.exists() and len(qs) > 1:
            matricula_periodo = qs[1]
            return matricula_periodo.turma_id and matricula_periodo.turma or None
        return None

    def get_historico_metricula_periodo_referencia(self):
        try:
            from gestao.models import PeriodoReferencia

            registro = self.historicosituacaomatricula_set.filter(data__lte=PeriodoReferencia.get_data_limite()).order_by('-data')[0]
            return (registro.situacao, registro.data)
        except Exception:
            return None

    def get_inscricao_programa_alimentacao(self):
        from django.core.exceptions import MultipleObjectsReturned
        try:
            if 'ae' in settings.INSTALLED_APPS:
                Programa = apps.get_model('ae', 'Programa')
                return self.inscricao_set.get(programa__tipo_programa__sigla=Programa.TIPO_ALIMENTACAO)
            return None
        except MultipleObjectsReturned:
            return self.inscricao_set.filter(programa__tipo_programa__sigla=Programa.TIPO_ALIMENTACAO).order_by('-data_cadastro')[0]
        except Exception:
            return None

    def get_inscricao_programa_idioma(self):
        from django.core.exceptions import MultipleObjectsReturned
        try:
            if 'ae' in settings.INSTALLED_APPS:
                Programa = apps.get_model('ae', 'Programa')
                return self.inscricao_set.get(programa__tipo_programa__sigla=Programa.TIPO_IDIOMA)
            return None
        except MultipleObjectsReturned:
            return self.inscricao_set.filter(programa__tipo_programa__sigla=Programa.TIPO_IDIOMA).order_by('-data_cadastro')[0]
        except Exception:
            return None

    def get_inscricao_programa_passe(self):
        from django.core.exceptions import MultipleObjectsReturned
        try:
            if 'ae' in settings.INSTALLED_APPS:
                Programa = apps.get_model('ae', 'Programa')
                return self.inscricao_set.get(programa__tipo_programa__sigla=Programa.TIPO_TRANSPORTE)
            return None
        except MultipleObjectsReturned:
            return self.inscricao_set.filter(programa__tipo_programa__sigla=Programa.TIPO_TRANSPORTE).order_by('-data_cadastro')[0]
        except Exception:
            return None

    def get_inscricao_programa_trabalho(self):
        from django.core.exceptions import MultipleObjectsReturned
        try:
            if 'ae' in settings.INSTALLED_APPS:
                Programa = apps.get_model('ae', 'Programa')
                return self.inscricao_set.get(programa__tipo_programa__sigla=Programa.TIPO_TRABALHO)
            return None
        except MultipleObjectsReturned:
            return self.inscricao_set.filter(programa__tipo_programa__sigla=Programa.TIPO_TRABALHO).order_by('-data_cadastro')[0]
        except Exception:
            return None

    def get_inscricoes_ativas(self):
        return self.inscricao_set.filter(ativa=True)

    @staticmethod
    def random(size=20, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
        """Returns a randomic string."""
        return ''.join([choice(allowed_chars) for _ in range(size)])

    @staticmethod
    def codificar(s):
        left = Aluno.random(7, '0123456789')
        right = Aluno.random(13, '0123456789')
        s = str(s).encode("utf-8").hex()
        return f'{left}{s}{right}'

    @staticmethod
    def decodificar(s):
        s = s[7:]
        s = s[:-13]
        s = bytes.fromhex(str(s)).decode("utf-8")
        return s

    def get_matricula_codificada(self):
        return Aluno.codificar(self.matricula)

    def get_registros_emissao_diploma(self):
        return self.registroemissaodiploma_set.filter(cancelado=False).order_by('numero_registro', 'livro', 'folha')

    def get_foto_75x100_url(self):
        return self.foto and self.foto.url_75x100 or '/static/comum/img/default.jpg'

    def get_foto_150x200_url(self):
        return self.foto and self.foto.url_150x200 or '/static/comum/img/default.jpg'

    def get_matriculas_periodo_com_diario(self):
        return self.matriculaperiodo_set.all().exclude(matriculadiario=None)

    def integralizou_suap(self):
        return self.matriz and self.matriculaperiodo_set.all().filter(matriculadiarioresumida__isnull=False)

    def iniciou_suap(self):
        return self.matriz and self.matriculaperiodo_set.all().filter(matriculadiarioresumida__isnull=True)

    def is_concluido(self):
        return self.situacao.codigo_academico == SituacaoMatricula.CONCLUIDO or self.situacao.codigo_academico == SituacaoMatricula.EGRESSO

    def is_formado(self):
        return self.situacao.codigo_academico == SituacaoMatricula.FORMADO

    def is_cancelado(self):
        return self.situacao.pk in (
            SituacaoMatricula.CANCELADO,
            SituacaoMatricula.CANCELAMENTO_COMPULSORIO,
            SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE,
            SituacaoMatricula.CANCELAMENTO_POR_DESLIGAMENTO,
            SituacaoMatricula.EVASAO,
            SituacaoMatricula.TRANSFERIDO_EXTERNO,
            SituacaoMatricula.JUBILADO,
        )

    def is_ultima_matricula_em_aberto(self):
        return self.get_ultima_matricula_periodo().situacao.id == SituacaoMatriculaPeriodo.EM_ABERTO

    def get_pedidos_matricula(self):
        return PedidoMatricula.objects.filter(matricula_periodo__aluno=self).order_by('id')

    def get_ultimo_registro_emissao_diploma(self):
        qs = self.registroemissaodiploma_set.filter(cancelado=False).order_by('-id')
        if qs:
            return qs[0]
        return None

    def get_dados_siabi(self):
        dados = dict()

        diretoria = ''
        polo = ''
        uo = ''

        curso = dict(id=self.curso_campus.id, descricao=self.curso_campus.descricao, modalidade=self.curso_campus.modalidade.descricao)

        if self.curso_campus.diretoria:
            diretoria = dict(id=self.curso_campus.diretoria.id, descricao=self.curso_campus.diretoria.setor.sigla)

        if self.curso_campus.diretoria:
            uo = dict(id=self.curso_campus.diretoria.setor.uo.id, descricao=self.curso_campus.diretoria.setor.uo.nome)

        if self.polo:
            polo = dict(id=self.polo.id, descricao=self.polo.descricao)

        dados.update(
            aluno=dict(
                id=self.id,
                matricula=self.matricula,
                nome=self.pessoa_fisica.nome,
                logradouro=self.logradouro or '',
                numero=self.numero or '',
                complemento=self.complemento or '',
                cep=self.cep or '',
                bairro=self.bairro or '',
                cidade=self.cidade_id and str(self.cidade) or '',
                telefone_principal=self.telefone_principal or '',
                telefone_secundario=self.telefone_principal or '',
                email_academico=self.pessoa_fisica.email or '',
                email_pessoal=self.pessoa_fisica.email_secundario or '',
                curso=curso,
                diretoria=diretoria,
                polo=polo,
                campus=uo,
                foto=self.foto and self.foto.url or "",
                sexo=self.pessoa_fisica.sexo,
                rg=self.numero_rg,
                data_nascimento=self.pessoa_fisica.nascimento_data and self.pessoa_fisica.nascimento_data.strftime('%d/%m/%Y'),
                situacao=self.situacao.descricao,
                lattes=self.pessoa_fisica.lattes,
            )
        )
        return dados

    def get_via_diploma(self):
        return RegistroEmissaoDiploma.objects.filter(aluno=self).filter(cancelado=False).count()

    def get_ofertas_pratica_profissional(self):
        if self.matriz and self.periodo_atual and self.periodo_atual >= (self.matriz.periodo_minimo_estagio_obrigatorio or 0):
            qs = self.curso_campus.ofertapraticaprofissional_set.filter(data_fim__gte=datetime.date.today())
            qs = qs.exclude(a_partir_do_periodo__gt=self.periodo_atual)
            if self.turno_id:
                outros_turnos = Turno.objects.exclude(id=self.turno_id)
                qs = qs.exclude(turno__in=outros_turnos)
            return qs.distinct()
        return self.curso_campus.ofertapraticaprofissional_set.all()[0:0]

    def matriculou_em_pratica_profissional(self):
        return MatriculaDiario.objects.filter(matricula_periodo__aluno=self, diario__componente_curricular__tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL).exists()

    def tem_apoio_social(self):
        if 'ae' in settings.INSTALLED_APPS:
            Participacao = apps.get_model('ae', 'Participacao')
            atendimentos = self.demandaalunoatendida_set.filter(quantidade__gt=0)
            participacoes = Participacao.objects.filter(inscricao__aluno=self)
            mensagem = []
            if participacoes.exists():
                texto_participacao = []
                for participacao in participacoes.all():
                    texto_participacao.append(participacao.programa.tipo_programa.titulo)
                texto_participacao = '; '.join(list(set(texto_participacao)))
                mensagem.append(f'Participa(ou) de programa de assistência estudantil ({texto_participacao})')
            if atendimentos.exists():
                texto_demanda = []
                for demanda in atendimentos.all():
                    texto_demanda.append(demanda.demanda.nome)
                texto_demanda = '; '.join(list(set(texto_demanda)))
                mensagem.append(f'Possui atendimento pelo setor do Serviço Social ({texto_demanda})')
            return mensagem or False
        return False

    def tem_cota(self):
        if not self.forma_ingresso:
            return False
        if 'Renda' in self.forma_ingresso.descricao or 'Seleção Diferenciada' in self.forma_ingresso.descricao:
            return self.forma_ingresso.descricao
        return False

    def tem_atividade_extracurricular(self):
        from pesquisa.models import Participacao as ParticipacaoPesquisa
        from projetos.models import Participacao as ParticipacaoExtensao
        from estagios.models import PraticaProfissional

        mensagem = []
        for participacao in ParticipacaoPesquisa.objects.filter(pessoa=self.pessoa_fisica):
            mensagem.append('{} de projeto de pesquisa'.format(participacao.bolsa_concedida and 'Recebe(u) bolsa' or 'Participa(ou)'))
        for participacao in ParticipacaoExtensao.objects.filter(pessoa=self.pessoa_fisica):
            mensagem.append('{} de projeto de extensão'.format(participacao.bolsa_concedida and 'Recebe(u) bolsa' or 'Participa(ou)'))
        if PraticaProfissional.objects.filter(aluno=self, obrigatorio=False).exists():
            mensagem.append(f'Participa(ou) de {PraticaProfissional.objects.filter(aluno=self, obrigatorio=False).count()} práticas profissionais não obrigatórias')
        return mensagem or False

    def get_avaliacoes(self, proximas=True):
        itens = ItemConfiguracaoAvaliacao.objects.filter(configuracao_avaliacao__diario__matriculadiario__matricula_periodo__aluno=self).order_by('data').distinct()
        if proximas:
            itens = itens.filter(data__gte=datetime.datetime.now(), data__lte=datetime.datetime.now() + datetime.timedelta(weeks=1))
        return itens

    def get_participacoes_em_minicursos(self):
        return Aluno.objects.filter(pessoa_fisica__cpf=self.pessoa_fisica.cpf, turmaminicurso__isnull=False)

    def get_participacoes_em_eventos(self):
        return ParticipanteEvento.objects.filter(participante__cpf=self.pessoa_fisica.cpf)

    def get_estagios_docentes(self):
        return EstagioDocente.objects.filter(matricula_diario__matricula_periodo__aluno=self)

    def get_atividade_profissional_efetiva_pendente_relatorio(self):
        from estagios.models import AtividadeProfissionalEfetiva

        return self.atividadeprofissionalefetiva_set.filter(situacao=AtividadeProfissionalEfetiva.EM_ANDAMENTO, relatorio_final_aluno='')

    def get_atividade_profissional_efetiva_reunioes_de_orientacao(self):
        from estagios.models import OrientacaoAtividadeProfissionalEfetiva
        from estagios.models import AtividadeProfissionalEfetiva

        return OrientacaoAtividadeProfissionalEfetiva.objects.filter(
            data__gte=datetime.date.today(), atividade_profissional_efetiva__aluno=self, atividade_profissional_efetiva__situacao=AtividadeProfissionalEfetiva.EM_ANDAMENTO
        )

    def get_estagios_com_avaliacao_pendente(self):
        from estagios.models import PraticaProfissional

        return self.praticaprofissional_set.filter(status=PraticaProfissional.STATUS_AGUARDANDO_AVALIACAO_ESTAGIARIO)

    def get_estagio_com_rel_atividades_pendente(self):
        from estagios.models import PraticaProfissional

        return self.praticaprofissional_set.exclude(
            status__in=[PraticaProfissional.STATUS_APTO_PARA_CONCLUSAO, PraticaProfissional.STATUS_CONCLUIDO, PraticaProfissional.STATUS_RESCINDIDO]
        ).filter(pendente_relatorio_estagiario=True)

    def get_aprendizagem_com_rel_atividades_pendente(self):
        if self.aprendizagem_set.exists():
            aprendizagem = self.aprendizagem_set.all().order_by('-id')[0]
            if aprendizagem.ha_pendencia_relatorio_aprendiz:
                return aprendizagem
            else:
                return None

    def get_estagios_historico(self):
        return self.praticaprofissional_set.filter(data_fim__isnull=False)

    def get_matriculas_anteriores(self):
        if self.nacionalidade:
            if 'Brasileira' in self.nacionalidade:
                return Aluno.objects.filter(pessoa_fisica__cpf=self.pessoa_fisica.cpf).exclude(pk=self.pk)[0:10]
            elif 'Estrangeira' in self.nacionalidade:
                return Aluno.objects.filter(passaporte=self.passaporte).exclude(pk=self.pk)[0:10]
        return Aluno.objects.none()

    def get_periodos_contabilizados_para_jubilar(self):
        # plano de retomada de aulas em virtude da pandemia (COVID19)
        ignorar_ids = []
        ignorar_ids.extend(self.matriculaperiodo_set.filter(situacao__in=(
            SituacaoMatriculaPeriodo.REPROVADO,
            SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA,
            SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE)
        ).order_by('id').values_list('id', flat=True).distinct())
        ignorar_ids.extend(
            self.matriculaperiodo_set.filter(
                matriculadiario__diario__turma__pertence_ao_plano_retomada=True
            ).order_by('id').values_list('id', flat=True).distinct()
        )
        matriculas_periodo = self.matriculaperiodo_set.filter(ano_letivo__ano__gte=self.ano_letivo.ano).exclude(id__in=ignorar_ids)
        if self.periodo_letivo == 2:
            matriculas_periodo = matriculas_periodo.exclude(ano_letivo__ano=self.ano_letivo.ano, periodo_letivo=1)
        return matriculas_periodo.filter(situacao__pk__in=SituacaoMatriculaPeriodo.SITUACOES_CONTABILIZADAS_PARA_JUBILAMENTO)

    def deve_ser_jubilado(self):
        if self.matriz is None:
            return False

        if self.matriz.estrutura.tipo_avaliacao in [EstruturaCurso.TIPO_AVALIACAO_SERIADO, EstruturaCurso.TIPO_AVALIACAO_MODULAR]:
            qtd_periodos_remanescentes_pra_conclusao = self.matriz.qtd_periodos_letivos - self.periodo_atual + 1
            if self.curso_campus.modalidade_id == Modalidade.INTEGRADO_EJA or self.curso_campus.modalidade.nivel_ensino_id == NivelEnsino.GRADUACAO:
                acrescimo = self.matriz.qtd_periodos_letivos
            else:
                acrescimo = self.matriz.qtd_periodos_letivos / 2 + self.matriz.qtd_periodos_letivos % 2
            qtd_periodos_futuros_possiveis = self.matriz.qtd_periodos_letivos + acrescimo - self.get_periodos_contabilizados_para_jubilar().count()
            if qtd_periodos_remanescentes_pra_conclusao > qtd_periodos_futuros_possiveis and self.possui_pendencia(incluir_colacao_grau=False):
                return 'Impossibilidade de conclusão do curso em tempo hábil'

        if (
            self.matriz.estrutura.qtd_periodos_conclusao
            and self.get_periodos_contabilizados_para_jubilar().count() >= self.matriz.estrutura.qtd_periodos_conclusao
            and self.situacao.pk == SituacaoMatricula.MATRICULADO
            and self.possui_pendencia(incluir_colacao_grau=False)
        ):
            return 'Quantidade máxima de matrículas em período para conclusão.'
        if (
            self.matriz.estrutura.tipo_avaliacao in [EstruturaCurso.TIPO_AVALIACAO_SERIADO, EstruturaCurso.TIPO_AVALIACAO_MODULAR]
            and self.matriz.estrutura.qtd_max_reprovacoes_periodo
        ):
            if (
                self.matriculaperiodo_set.filter(
                    periodo_matriz=self.periodo_atual, situacao__id__in=[SituacaoMatriculaPeriodo.REPROVADO, SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA]
                ).count()
                >= self.matriz.estrutura.qtd_max_reprovacoes_periodo
            ):
                return 'Quantidade máxima de reprovações no mesmo período letivo.'
        if self.matriz.estrutura.qtd_max_reprovacoes_disciplina:
            matriculas_diario_resumidas = MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self)
            matriculas_diario_resumidas = matriculas_diario_resumidas.filter(matricula_periodo__ano_letivo__ano__gte=self.ano_letivo.ano)
            if self.periodo_letivo == 2:
                matriculas_diario_resumidas = matriculas_diario_resumidas.exclude(matricula_periodo__ano_letivo__ano=self.ano_letivo.ano, matricula_periodo__periodo_letivo=1)
            matriculas_diario_resumidas = matriculas_diario_resumidas.filter(situacao__in=[MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA])
            componentes_com_reprovacao = matriculas_diario_resumidas.values_list('equivalencia_componente__componente__id', flat=True)
            matriculas_diario = MatriculaDiario.objects.filter(
                matricula_periodo__aluno=self, situacao__in=[MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA]
            )
            componentes_com_reprovacao = set(componentes_com_reprovacao) | set(matriculas_diario.values_list('diario__componente_curricular__componente__id', flat=True))
            for componente in componentes_com_reprovacao:
                reprovacoes_suap = matriculas_diario.filter(diario__componente_curricular__componente=componente).count()
                reprovacoes_qacademico = matriculas_diario_resumidas.filter(equivalencia_componente__componente=componente).count()
                if reprovacoes_suap + reprovacoes_qacademico >= self.matriz.estrutura.qtd_max_reprovacoes_disciplina:
                    return 'Quantidade máxima de reprovações em disciplina.'
        return False

    @transaction.atomic
    def jubilar(self, motivo, automatico=False):
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()

        procedimento_matricula = ProcedimentoMatricula()
        procedimento_matricula.tipo = 'Jubilamento'
        procedimento_matricula.situacao_matricula_anterior = self.situacao
        procedimento_matricula.matricula_periodo = ultima_matricula_periodo
        procedimento_matricula.motivo = motivo
        procedimento_matricula.data = datetime.datetime.now()
        procedimento_matricula.save()
        if automatico:
            ProcedimentoMatricula.objects.filter(pk=procedimento_matricula.pk).update(user=None)

        self.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.JUBILADO)
        ultima_matricula_periodo = self.get_ultima_matricula_periodo()
        ultima_matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.JUBILADO)
        ultima_matricula_periodo.save()
        self.save()

    def pesquisas_egresso(self):
        from egressos.models import Pesquisa

        pesquisas = Pesquisa.objects.filter(inicio__lte=datetime.date.today(), fim__gte=datetime.date.today(), publicada=True)
        pesquisas = pesquisas.filter(modalidade=self.curso_campus.modalidade) | pesquisas.filter(modalidade__isnull=True)
        pesquisas = pesquisas.filter(conclusao__ano=self.ano_conclusao) | pesquisas.filter(conclusao__isnull=True)
        pesquisas = pesquisas.filter(uo__pk=self.curso_campus.diretoria.setor.uo_id) | pesquisas.filter(uo=None)
        pesquisas = pesquisas.filter(curso_campus=self.curso_campus) | pesquisas.filter(curso_campus__isnull=True)
        return pesquisas

    def get_total_medidas_disciplinares_premiacoes(self, data_inicio, data_fim):
        return '{} / {}'.format(
            self.medidadisciplinar_set.filter(Q(data_inicio__lte=data_fim, data_inicio__gte=data_inicio) | Q(data_fim__lte=data_fim, data_fim__gte=data_inicio)).count(),
            self.premiacao_set.filter(data__lte=data_fim, data__gte=data_inicio).count(),
        )

    def get_total_atividades_complementares(self, data_inicio, data_fim):
        return self.atividadecomplementar_set.filter(data_atividade__gte=data_inicio, data_atividade__lte=data_fim).count()

    def get_ira_curso_aluno(self):
        ira = Aluno.objects.filter(curso_campus=self.curso_campus).aggregate(soma=Sum('ira'))['soma'] / Aluno.objects.filter(curso_campus=self.curso_campus).count()
        return mask_nota(ira)

    def get_url_historico_diploma(self):
        if self.situacao_id in (SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO):
            assinatura_eletronica = AssinaturaEletronica.objects.filter(
                registro_emissao_diploma__aluno=self, data_assinatura__isnull=False, data_revogacao__isnull=True
            ).order_by('-id').first()
            if assinatura_eletronica:
                return assinatura_eletronica.get_url_historico(), assinatura_eletronica.get_url_diploma()
            assinatura_digital = AssinaturaDigital.objects.filter(
                registro_emissao_diploma__aluno=self, concluida=True, data_revogacao__isnull=True
            ).order_by('-id').first()
            if assinatura_digital:
                return assinatura_digital.get_url_historico(), assinatura_digital.get_url_diploma()
        return None

    def criar_papel_discente(self):
        if 'rh' in settings.INSTALLED_APPS:
            Papel = apps.get_model('rh', 'Papel')
            ContentType = apps.get_model('contenttypes.ContentType')
            aluno = self.get_vinculo().relacionamento
            if not aluno.papeis_ativos.exists():

                kwargs = dict(
                    detalhamento=f"{aluno.matricula} - Discente",
                    descricao=f"{aluno.matricula} - Discente",
                    data_fim=None
                )
                papel_cargo, criou = Papel.objects.update_or_create(
                    pessoa=aluno.pessoa_fisica,
                    tipo_papel=Papel.TIPO_PAPEL_DISCENTE,
                    data_inicio=datetime.datetime.now(),
                    papel_content_type=ContentType.objects.get_for_model(aluno),
                    papel_content_id=aluno.id,
                    defaults=kwargs,
                )

    def get_dados_receita_federal(self, cpf_operador):
        from djtools.services import consulta_cidadao
        if settings.DEBUG:
            sucesso, resposta_lista = consulta_cidadao(['11111111111'], '89962354234')
        else:
            import re
            sucesso, resposta_lista = consulta_cidadao([re.sub(r'\D', '', str(self.pessoa_fisica.cpf))], cpf_operador and re.sub(r'\D', '', str(cpf_operador)) or None)
        if sucesso and "mensagem" not in resposta_lista[0]:
            return {'Nome': resposta_lista[0]['Nome'], 'DataNascimento': resposta_lista[0]['DataNascimento'], 'NomeMae': resposta_lista[0]['NomeMae']}
        return {}
