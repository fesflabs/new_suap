import datetime
import os
from random import choice
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from rest_framework.authtoken.models import Token
from comum.models import Ano, User, Vinculo, Configuracao
from comum.utils import somar_data
from djtools.db import models
from djtools.thumbs import ImageWithThumbsField
from djtools.utils import normalizar_nome_proprio
from djtools.storages import get_overwrite_storage
from djtools.db.models import ModelPlus
from django.apps import apps

from residencia.models import LogResidenciaModel, MatriculaDiario, SituacaoMatricula
from residencia.models.curso import MatrizCurso, ComponenteCurricular


class SequencialMatriculaResidente(ModelPlus):
    prefixo = models.CharFieldPlus(max_length=255)
    contador = models.PositiveIntegerField()

    @staticmethod
    def proximo_numero(prefixo):
        qs_sequencial = SequencialMatriculaResidente.objects.filter(prefixo=prefixo)
        if qs_sequencial.exists():
            sequencial = qs_sequencial[0]
            contador = sequencial.contador
        else:
            sequencial = SequencialMatriculaResidente()
            sequencial.prefixo = prefixo
            contador = 1
        sequencial.contador = contador + 1
        sequencial.save()
        numero = f'000000000{contador}'
        matricula = f'{prefixo}{numero[-4:]}'
        if Residente.objects.filter(matricula=matricula).exists():
            return SequencialMatriculaResidente.proximo_numero(prefixo)
        else:
            return matricula


class Residente(LogResidenciaModel):
    SEARCH_FIELDS = ["pessoa_fisica__search_fields_optimized", "matricula"]
    NAO = False
    SIM = True
    SIM_NAO_CHOICES = (
        (NAO, 'Não'),
        (SIM, 'Sim')
    )
    PERIODO_LETIVO_CHOICES = settings.PERIODO_LETIVO_CHOICES
    EMPTY_CHOICES = [['', '----']]
    ESTADO_CIVIL_CHOICES = [['Solteiro', 'Solteiro'], ['Casado', 'Casado'], ['União Estável', 'União Estável'],
                            ['Divorciado', 'Divorciado'], ['Viúvo', 'Viúvo']]
    PARENTESCO_CHOICES = [['Pai/Mãe', 'Pai/Mãe'], ['Avô/Avó', 'Avô/Avó'], ['Tio/Tia', 'Tio/Tia'],
                          ['Sobrinho/Sobrinha', 'Sobrinho/Sobrinha'], ['Outro', 'Outro']]
    TIPO_ZONA_RESIDENCIAL_CHOICES = [['1', 'Urbana'], ['2', 'Rural']]
    TIPO_SANGUINEO_CHOICES = [['O-', 'O-'], ['O+', 'O+'], ['A-', 'A-'], ['A+', 'A+'], ['B-', 'B-'], ['B+', 'B+'],
                              ['AB-', 'AB-'], ['AB+', 'AB+']]
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

    BIOMEDICINA = 'Biomedicina'
    ENFERMAGEM = 'Enfermagem'
    FARMACIA = 'Farmácia'
    FISIOTERAPIA = 'Fisioterapia'
    FONOAUDIOLOGIA = 'Fonoaudiologia'
    MEDICINA = 'Medicina'
    MEDICINA_VETERINARIA = 'Medicina Veterinária'
    NUTRICAO = 'Nutrição'
    ODONTOLOGIA = 'Odontologia'
    PSICOLOGIA = 'Psicologia'
    TERAPIA_OCUPACIONAL = 'Terapia Ocupacional'
    SAUDE_OCUPACIONAL = 'Saúde Ocupacional'
    SANITARISTA = 'Sanitarista / saúde coletiva'

    CATEGORIAS_CHOICES = [
        [BIOMEDICINA, BIOMEDICINA],
        [ENFERMAGEM, ENFERMAGEM],
        [FARMACIA, FARMACIA],
        [FISIOTERAPIA, FISIOTERAPIA],
        [FONOAUDIOLOGIA, FONOAUDIOLOGIA],
        [MEDICINA, MEDICINA],
        [MEDICINA_VETERINARIA, MEDICINA_VETERINARIA],
        [NUTRICAO, NUTRICAO],
        [ODONTOLOGIA, ODONTOLOGIA],
        [PSICOLOGIA, PSICOLOGIA],
        [TERAPIA_OCUPACIONAL, TERAPIA_OCUPACIONAL],
        [SAUDE_OCUPACIONAL, SAUDE_OCUPACIONAL],
        [SANITARISTA, SANITARISTA]
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
                [AQUAVIARIO_ATE_5, 'Capacidade de até 5 pessoas'],
                [AQUAVIARIO_ENTRE_5_A_15, 'Capacidade entre 5 a 15 pessoas'],
                [AQUALVIARIO_ENTRE_15_E_35, 'Capacidade entre 15 e 35 pessoas'],
                [AQUAVIARIO_ACIMA_DE_35, 'Capacidade acima de 35 pessoas'],
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
        [AQUAVIARIO_ATE_5, 'Capacidade de até 5 pessoas'],
        [AQUAVIARIO_ENTRE_5_A_15, 'Capacidade entre 5 a 15 pessoas'],
        [AQUALVIARIO_ENTRE_15_E_35, 'Capacidade entre 15 e 35 pessoas'],
        [AQUAVIARIO_ACIMA_DE_35, 'Capacidade acima de 35 pessoas'],
        [TREM, 'Trem/Metrô'],
    ]

    SUPERDOTADO = '1'
    SUPERDOTACAO_CHOICES = [[SUPERDOTADO, 'Altas habilidades/Superdotação']]

    # Fields
    matricula = models.CharFieldPlus('Matrícula', max_length=255, db_index=True)
    foto = ImageWithThumbsField(storage=get_overwrite_storage(), use_id_for_name=True, upload_to='residentes',
                                sizes=((75, 100), (150, 200)), null=True, blank=True)
    pessoa_fisica = models.ForeignKeyPlus('rh.PessoaFisica', verbose_name='Pessoa Física', related_name='residente_set', on_delete=models.CASCADE)
    estado_civil = models.CharFieldPlus(choices=ESTADO_CIVIL_CHOICES, null=True)
    numero_dependentes = models.PositiveIntegerFieldPlus('Número de Dependentes', null=True, blank=True)

    # endereco
    logradouro = models.CharFieldPlus(max_length=255, verbose_name='Logradouro', null=True)
    numero = models.CharFieldPlus(max_length=255, verbose_name='Número', null=True)
    complemento = models.CharFieldPlus(max_length=255, verbose_name='Complemento', null=True, blank=True)
    bairro = models.CharFieldPlus(max_length=255, verbose_name='Bairro', null=True)
    cep = models.CharFieldPlus(max_length=255, verbose_name='CEP', null=True, blank=True)
    cidade = models.ForeignKeyPlus('comum.Municipio', verbose_name='Cidade', null=True)
    tipo_zona_residencial = models.CharFieldPlus(choices=TIPO_ZONA_RESIDENCIAL_CHOICES, verbose_name='Zona Residencial',
                                                 null=True, blank=True)

    # endereco profissional
    logradouro_profissional = models.CharFieldPlus(max_length=255, verbose_name='Logradouro Profissional', null=True,
                                                   blank=True)
    numero_profissional = models.CharFieldPlus(max_length=255, verbose_name='Número Profissional', null=True,
                                               blank=True)
    complemento_profissional = models.CharFieldPlus(max_length=255, verbose_name='Complemento Profissional', null=True,
                                                    blank=True)
    bairro_profissional = models.CharFieldPlus(max_length=255, verbose_name='Bairro Profissional', null=True,
                                               blank=True)
    cep_profissional = models.CharFieldPlus(max_length=255, verbose_name='CEP Profissional', null=True, blank=True)
    cidade_profissional = models.ForeignKeyPlus('comum.Municipio', verbose_name='Cidade Profissional', null=True, blank=True, 
                                                related_name='residente_cidade_profissional_set')
    tipo_zona_residencial_profissional = models.CharFieldPlus(choices=TIPO_ZONA_RESIDENCIAL_CHOICES,
                                                              verbose_name='Zona Residencial Profissional', null=True,
                                                              blank=True)
    telefone_profissional = models.CharFieldPlus(max_length=255, verbose_name='Telefone Profissional', null=True,
                                                 blank=True)

    # dados familiares
    nome_pai = models.CharFieldPlus(max_length=255, verbose_name='Nome do Pai', null=True, blank=True)
    estado_civil_pai = models.CharFieldPlus(choices=ESTADO_CIVIL_CHOICES, null=True, blank=True)
    pai_falecido = models.BooleanField(verbose_name='Pai é falecido?', default=False)
    nome_mae = models.CharFieldPlus(max_length=255, verbose_name='Nome da Mãe', null=True, blank=False)
    estado_civil_mae = models.CharFieldPlus(verbose_name='Estado Civil da Mãe', choices=ESTADO_CIVIL_CHOICES, null=True, blank=True)
    mae_falecida = models.BooleanField(verbose_name='Mãe é falecida?', default=False)
    responsavel = models.CharFieldPlus(max_length=255, verbose_name='Nome do Responsável', null=True, blank=True)
    email_responsavel = models.CharFieldPlus(max_length=255, verbose_name='Email do Responsável', null=True, blank=True)
    parentesco_responsavel = models.CharFieldPlus(verbose_name='Parentesco do Responsável', choices=PARENTESCO_CHOICES,
                                                  null=True, blank=True)
    cpf_responsavel = models.BrCpfField(verbose_name='CPF do Responsável', null=True, blank=True)
    autorizacao_carteira_estudantil = models.BooleanField(
        verbose_name='Autorização para Emissão da Carteira Estudantil',
        help_text='O aluno autoriza o envio de seus dados pessoais para o Sistema Brasileiro de Educação (SEB) para fins de emissão da carteira de estudante digital de acordo com a Medida Provisória Nº 895, de 6 de setembro de 2019',
        default=False,
    )

    # contato
    telefone_principal = models.CharFieldPlus(max_length=255, verbose_name='Telefone Principal', null=True, blank=True)
    telefone_secundario = models.CharFieldPlus(max_length=255, verbose_name='Celular', null=True,
                                               blank=True)
    telefone_adicional_1 = models.CharFieldPlus(max_length=255, verbose_name='Telefone do Responsável', null=True,
                                                blank=True)
    telefone_adicional_2 = models.CharFieldPlus(max_length=255, verbose_name='Telefone do Responsável', null=True,
                                                blank=True)
    facebook = models.URLField('Facebook', blank=True, null=True)
    instagram = models.URLField('Instagram', blank=True, null=True)
    twitter = models.URLField('Twitter', blank=True, null=True)
    linkedin = models.URLField('Linkedin', blank=True, null=True)
    skype = models.CharFieldPlus('Skype', blank=True, null=True)

    # outras informacoes
    tipo_sanguineo = models.CharFieldPlus(max_length=255, verbose_name='Tipo Sanguíneo', null=True, blank=True,
                                          choices=TIPO_SANGUINEO_CHOICES)
    nacionalidade = models.CharFieldPlus(max_length=255, verbose_name='Nacionalidade', null=True, blank=True,
                                         choices=TIPO_NACIONALIDADE_CHOICES)
    passaporte = models.CharFieldPlus(max_length=50, verbose_name='Nº do Passaporte', default='', null=True, blank=True)
    pais_origem = models.ForeignKeyPlus('comum.Pais', verbose_name='País de Origem', null=True, blank=True,
                                        help_text='Obrigatório para estrangeiros')
    naturalidade = models.ForeignKeyPlus(
        'comum.Municipio',
        verbose_name='Naturalidade',
        null=True,
        blank=True,
        related_name='residente_naturalidade_set',
        help_text='Cidade em que o(a) residente nasceu. Obrigatório para brasileiros',
    )

    tipo_necessidade_especial = models.CharFieldPlus(verbose_name='Tipo de Necessidade Especial', null=True, blank=True,
                                                     choices=TIPO_NECESSIDADE_ESPECIAL_CHOICES)
    tipo_transtorno = models.CharFieldPlus(verbose_name='Tipo de Transtorno', null=True, blank=True,
                                           choices=TIPO_TRANSTORNO_CHOICES)
    superdotacao = models.CharFieldPlus(verbose_name='Superdotação', null=True, blank=True,
                                        choices=SUPERDOTACAO_CHOICES)
    outras_necessidades = models.CharFieldPlus(max_length=255, verbose_name='Outras necessidades especiais', null=True, blank=True)

    possui_problema_saude = models.BooleanField(
        verbose_name='Tem algum problema de Saúde?',
        default=NAO, choices=SIM_NAO_CHOICES, null=True, blank=True,
    )
    possui_alergia = models.BooleanField(
        verbose_name='Alguma alergia?',
        default=NAO, choices=SIM_NAO_CHOICES, null=True, blank=True,
    )
    possui_alergia_qual = models.CharFieldPlus(
        verbose_name="Se marcou 'Sim' para 'Alguma alergia?', informe qual(is):",
        null=True, blank=True,
    )
    em_tratamento_medico = models.BooleanField(
        verbose_name='Está em tratamento médico?',
        default=NAO, choices=SIM_NAO_CHOICES, null=True, blank=True,
    )
    em_tratamento_medico_qual = models.CharFieldPlus(
        verbose_name="Se marcou 'Sim' para 'Está em tratamento médico?', informe qual e para que doença:",
        null=True, blank=True,
    )
    usa_medicacao = models.BooleanField(
        verbose_name='Está em uso de alguma medicação?',
        default=NAO, choices=SIM_NAO_CHOICES, 
        null=True, blank=True
    )
    usa_medicacao_qual = models.CharFieldPlus(
        verbose_name="Se marcou 'Sim' para 'Está em uso de alguma medicação?', informe qual e quando encerrará o uso:",
        null=True, blank=True,
    )
    contato_emergencia = models.CharFieldPlus(
        verbose_name="Em caso de emergência para quem ligar e em qual número?",
        null=True, blank=True,
    )
    outra_info_saude = models.CharFieldPlus(
        verbose_name="Existe alguma outra informação a respeito da sua saúde que queira fazer constar?",
        null=True, blank=True,
    )

    # dados escolares
    nivel_ensino_anterior = models.ForeignKeyPlus('comum.NivelEnsino', null=True, blank=True, on_delete=models.CASCADE)
    tipo_instituicao_origem = models.CharFieldPlus(max_length=255, verbose_name='Tipo de Instituição', null=True,
                                                   choices=TIPO_INSTITUICAO_ORIGEM_CHOICES, blank=True)
    nome_instituicao_anterior = models.CharFieldPlus(max_length=255, verbose_name='Nome da Instituição', null=True,
                                                     blank=True)
    ano_conclusao_estudo_anterior = models.ForeignKeyPlus(
        'comum.Ano', verbose_name='Ano de Conclusão de Estudo Anterior',
        null=True,
        related_name='residente_ano_conclusao_anterior_set',
        blank=True,
        on_delete=models.CASCADE
    )
    habilitacao_pedagogica = models.CharFieldPlus(max_length=255,
                                                  verbose_name='Habilitação para Curso de Formação Pedagógica',
                                                  null=True, blank=True)

    categoria = models.CharFieldPlus('Categoria', max_length=100, choices=CATEGORIAS_CHOICES, null=True, blank=True)

    # conselho classe
    numero_registro = models.CharFieldPlus('Número de Registro no Conselho de Fiscalização Profissional', null=True, blank=True)
    conselho = models.ForeignKeyPlus('comum.ConselhoProfissional', verbose_name='Conselho de Fiscalização Profissional', null=True, blank=True)

    # rg
    numero_rg = models.CharFieldPlus(max_length=255, verbose_name='Número do RG', null=True, blank=True)
    uf_emissao_rg = models.ForeignKeyPlus('comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
                                          related_name='residente_emissor_rg_set')
    orgao_emissao_rg = models.ForeignKeyPlus('comum.OrgaoEmissorRg', verbose_name='Orgão Emissor', null=True, blank=True)
    data_emissao_rg = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)

    # titulo_eleitor
    numero_titulo_eleitor = models.CharFieldPlus(max_length=255, verbose_name='Título de Eleitor', null=True,
                                                 blank=True)
    zona_titulo_eleitor = models.CharFieldPlus(max_length=255, verbose_name='Zona', null=True, blank=True)
    secao = models.CharFieldPlus(max_length=255, verbose_name='Seção', null=True, blank=True)
    data_emissao_titulo_eleitor = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    uf_emissao_titulo_eleitor = models.ForeignKeyPlus(
        'comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
        related_name='residente_emissor_titulo_eleitor_set', on_delete=models.CASCADE
    )

    # carteira de reservista
    numero_carteira_reservista = models.CharFieldPlus(max_length=255, verbose_name='Número da Carteira de Reservista',
                                                      null=True, blank=True)
    regiao_carteira_reservista = models.CharFieldPlus(max_length=255, verbose_name='Região', null=True, blank=True)
    serie_carteira_reservista = models.CharFieldPlus(max_length=255, verbose_name='Série', null=True, blank=True)
    estado_emissao_carteira_reservista = models.ForeignKeyPlus(
        'comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
        related_name='residente_estado_emissor_carteira_reservista_set', on_delete=models.CASCADE
    )
    ano_carteira_reservista = models.PositiveIntegerField(verbose_name='Ano', null=True, blank=True)

    # certidao_civil
    tipo_certidao = models.CharFieldPlus(max_length=255, verbose_name='Tipo de Certidão', null=True, blank=True,
                                         choices=TIPO_CERTIDAO_CHOICES)
    cartorio = models.CharFieldPlus(max_length=255, verbose_name='Cartório', null=True, blank=True)
    numero_certidao = models.CharFieldPlus(max_length=255, verbose_name='Número de Termo', null=True, blank=True)
    folha_certidao = models.CharFieldPlus(max_length=255, verbose_name='Folha', null=True, blank=True)
    livro_certidao = models.CharFieldPlus(max_length=255, verbose_name='Livro', null=True, blank=True)
    data_emissao_certidao = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    matricula_certidao = models.CharFieldPlus(max_length=255, verbose_name='Matrícula', null=True, blank=True)

    # dados da matrícula
    curso_campus = models.ForeignKeyPlus('residencia.CursoResidencia', on_delete=models.CASCADE, verbose_name='Curso', null=True, blank=True)
    matriz = models.ForeignKeyPlus('residencia.Matriz', null=True, verbose_name='Matriz')
    periodo_atual = models.IntegerField('Período Atual', null=True, blank=True)
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano de Ingresso', on_delete=models.CASCADE, null=True, blank=True)
    periodo_letivo = models.PositiveIntegerField(verbose_name='Período de Ingresso', choices=PERIODO_LETIVO_CHOICES, null=True, blank=True)
    situacao = models.ForeignKeyPlus('residencia.SituacaoMatricula', verbose_name='Situação', on_delete=models.CASCADE, null=True, blank=True)

    data_matricula = models.DateTimeFieldPlus(verbose_name='Data da Matrícula', auto_now_add=True)
    cota_sistec = models.CharFieldPlus(max_length=255, verbose_name='Cota SISTEC', null=True,
                                       choices=COTA_SISTEC_CHOICES, blank=True)
    cota_mec = models.CharFieldPlus(max_length=255, verbose_name='Cota MEC', null=True, choices=COTA_MEC_CHOICES,
                                    blank=True)

    renda_per_capita = models.DecimalField(
        null=True, 
        blank=True,
        max_digits=15,
        decimal_places=2,
        verbose_name='Renda Per Capita',
        help_text='Número de salários mínimos ganhos pelos integrantes da família dividido pelo número de integrantes',
    )

    observacao_historico = models.TextField('Observação para o Histórico', null=True, blank=True)
    observacao_matricula = models.TextField('Observação da Matrícula', null=True, blank=True)

    alterado_em = models.DateTimeFieldPlus('Data de Alteração', auto_now=True, null=True, blank=True)
    email_academico = models.EmailField('Email Acadêmico', null=True, blank=True,)
    email_qacademico = models.EmailField('Email Q-Acadêmico', null=True, blank=True,)
    email_google_classroom = models.EmailField('Email do Google Classroom', null=True, blank=True,)

    csf = models.BooleanField(verbose_name='Ciência sem Fronteiras', default=False, null=True, blank=True)

    # caracterizacao_socioeconomica
    documentada = models.BooleanField('Doc. Entregue', default=False)
    data_documentacao = models.DateTimeField('Data de Entrega da Documentação', null=True)

    # saúde
    cartao_sus = models.CharFieldPlus('Cartão SUS', null=True, blank=True)

    codigo_educacenso = models.CharFieldPlus('Código EDUCACENSO', null=True, blank=True)

    nis = models.CharFieldPlus('NIS', null=True, help_text='Número de Identificação Social', blank=True)

    pis_pasep = models.CharField('PIS / PASEP', max_length=20, null=True, blank=True)

    poder_publico_responsavel_transporte = models.CharFieldPlus(
        'Poder Público Responsável pelo Transporte Escolar', choices=PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES,
        null=True, blank=True
    )
    tipo_veiculo = models.CharFieldPlus('Tipo de Veículo Utilizado no Transporte Escolar',
                                        choices=TIPO_VEICULO_CHOICES_FOR_FORM, null=True, blank=True)
    vinculos = GenericRelation('comum.Vinculo', related_query_name='residentes_set', object_id_field='id_relacionamento',
                               content_type_field='tipo_relacionamento')

    class Meta:
        ordering = ('pessoa_fisica__nome',)
        verbose_name = 'Residente'
        verbose_name_plural = 'Residentes'

        permissions = (
            ('emitir_diploma', 'Pode emitir diploma de Residente'),
            ('emitir_boletim', 'Pode emitir boletim de Residente'),
            ('emitir_historico', 'Pode emitir histórico de Residente'),
            ('efetuar_matricula', 'Pode efetuar matricula de Residente'),
            ('pode_sincronizar_dados', 'Pode sincronizar dados de Residente'),
            ('gerar_relatorio', 'Pode gerar relatórios de Residente'),
            ('pode_ver_chave_acesso_pais', 'Pode ver chave de acesso dos pais'),
            ('change_foto', 'Pode editar foto de Residente'),
            ('view_dados_academicos', 'Pode visualizar dados acadêmicos de Residente'),
            ('view_dados_pessoais', 'Pode visualizar dados pessoais de Residente'),
            ('view_dados_bancarios', 'Pode visualizar dados bancários de Residente'),
        )


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

    def get_observacoes(self):
        return self.observacao_set.all()

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

    def eh_pne(self):
        return bool(self.tipo_necessidade_especial)

    def get_nome(self):
        return self.pessoa_fisica.nome

    def get_nome_social_composto(self):
        if self.pessoa_fisica.nome_social:
            return f'{self.pessoa_fisica.nome_registro} ({self.pessoa_fisica.nome_social})'
        else:
            return self.pessoa_fisica.nome

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

    def get_solicitacoes_ferias_aprovadas(self):
        from residencia.models import SolicitacaoFerias
        return SolicitacaoFerias.objects.filter(solicitante=self.get_user(), atendida=True)

    def get_solicitacoes_ferias_aprovadas_datas(self):
        ferias_lista = self.get_solicitacoes_ferias_aprovadas()
        valor = []
        for ferias in ferias_lista:
            valor.append(f'({ferias.data_inicio} - {ferias.data_fim}) ')
        valor = ''.join(valor)
        return valor

    def esta_de_ferias_hoje(self):
        hoje = datetime.datetime.now()
        qs_ferias_hoje = self.get_solicitacoes_ferias_aprovadas().filter(data_inicio__lte=hoje, data_fim__gte=hoje)
        return qs_ferias_hoje.exists()

    def get_solicitacoes_licencas_aprovadas(self):
        from residencia.models import SolicitacaoLicencas
        return SolicitacaoLicencas.objects.filter(solicitante=self.get_user(), atendida=True)

    def get_solicitacoes_licencas_aprovadas_datas(self):
        licencas_lista = self.get_solicitacoes_ferias_aprovadas()
        valor = []
        for licenca in licencas_lista:
            valor.append(f'({licenca.data_inicio} - {licenca.data_fim})')
        valor = ''.join(valor)
        return valor

    def esta_de_licenca_hoje(self):
        hoje = datetime.datetime.now()
        qs_licenca_hoje = self.get_solicitacoes_licencas_aprovadas().filter(data_inicio__lte=hoje, data_fim__gte=hoje)
        return qs_licenca_hoje.exists()

    def is_user(self, request):
        return request.user.id and request.user.id == self.pessoa_fisica.user_id

    def get_ext_combo_template(self):
        out = [f'<dt class="sr-only">Nome</dt><dd><strong>{self}</strong></dd>']
        img_src = self.get_foto_75x100_url()
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

    def __str__(self):
        return f'{normalizar_nome_proprio(self.get_nome_social_composto())} ({self.matricula})'

    def get_vinculo(self):
        return self.vinculos.first()

    def get_user(self):
        qs = User.objects.filter(username=self.pessoa_fisica.cpf.replace('.', '').replace('-', ''))
        return qs.exists() and qs[0] or None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.pessoa_fisica.nome = normalizar_nome_proprio(self.pessoa_fisica.nome)
        self.pessoa_fisica.eh_residente = True
        if self.passaporte:
            self.pessoa_fisica.passaporte = self.passaporte
        self.pessoa_fisica.save()

        user = self.get_user()
        qs = Vinculo.objects.filter(residentes_set=self)  # TO-DO: corrigir lá no model Vinculo
        if not qs.exists():
            vinculo = Vinculo()
        else:
            vinculo = qs.first()
        vinculo.pessoa = self.pessoa_fisica.pessoa_ptr
        vinculo.user = user
        vinculo.relacionamento = self
        vinculo.save()
    
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.pessoa_fisica.user.delete()


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
        return f'/residencia/residente/{self.matricula}/'

    def pode_matricula_online(self):
        return True

    def get_matriculas_periodo(self, ate_ano_letivo=None, ate_periodo_letivo=None, orderbyDesc=True):
        qs = self.matriculas_periodos_residente_residencia_set
        if ate_ano_letivo and ate_periodo_letivo:
                qs = qs.filter(ano_letivo__ano__lt=ate_ano_letivo.ano)

        if orderbyDesc:
            return qs.order_by('-ano_letivo__ano', '-periodo_letivo')
        else:
            return qs.order_by('ano_letivo__ano', 'periodo_letivo')

    @staticmethod
    def random(size=20, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
        """Returns a randomic string."""
        return ''.join([choice(allowed_chars) for _ in range(size)])

    @staticmethod
    def codificar(s):
        left = Residente.random(7, '0123456789')
        right = Residente.random(13, '0123456789')
        s = str(s).encode("utf-8").hex()
        return f'{left}{s}{right}'

    @staticmethod
    def decodificar(s):
        s = s[7:]
        s = s[:-13]
        s = bytes.fromhex(str(s)).decode("utf-8")
        return s

    def get_matricula_codificada(self):
        return Residente.codificar(self.matricula)

    def get_foto_75x100_url(self):
        return self.foto and self.foto.url_75x100 or '/static/comum/img/default.jpg'

    def get_foto_150x200_url(self):
        return self.foto and self.foto.url_150x200 or '/static/comum/img/default.jpg'

    def criar_papel_discente(self):
        if 'rh' in settings.INSTALLED_APPS:
            Papel = apps.get_model('rh', 'Papel')
            ContentType = apps.get_model('contenttypes.ContentType')
            residente = self.get_vinculo().relacionamento
            if not residente.papeis_ativos.exists():

                kwargs = dict(
                    detalhamento=f"{residente.matricula} - Discente",
                    descricao=f"{residente.matricula} - Discente",
                    data_fim=None
                )
                papel_cargo, criou = Papel.objects.update_or_create(
                    pessoa=residente.pessoa_fisica,
                    tipo_papel=Papel.TIPO_PAPEL_DISCENTE,
                    data_inicio=datetime.datetime.now(),
                    papel_content_type=ContentType.objects.get_for_model(residente),
                    papel_content_id=residente.id,
                    defaults=kwargs,
                )

    def get_ids_componentes_curriculares_cumpridos(self, ano=None, matricula_periodo=None):

        if hasattr(self, 'ids_componentes_curriculares_cumpridos') and not matricula_periodo:
            return self.ids_componentes_curriculares_cumpridos

        if not self.matriz:
            return []

        return self.matriz.get_ids_componentes()

        ids = self.matriz.get_ids_componentes()
        md = MatriculaDiario.objects.filter(matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_APROVADO).filter(diario__componente_curricular__componente__id__in=ids)

        if ano:
            md = md.filter(matricula_periodo__ano_letivo__ano__lte=ano)

        if matricula_periodo:
            md = md.filter(matricula_periodo=matricula_periodo)

        lista = []
        for i in md.values_list('diario__componente_curricular__componente__id', flat=True):
            lista.append(i)

        for pk, componente_associado_pk in ComponenteCurricular.objects.filter(matriz=self.matriz, componente_curricular_associado__isnull=False).values_list(
            'componente__id', 'componente_curricular_associado__componente__id'
        ):
            if pk in lista:
                lista.append(componente_associado_pk)

        self.ids_componentes_curriculares_cumpridos = lista
        return self.ids_componentes_curriculares_cumpridos

    def get_ids_componentes_cumpridos(self, ids=None, ano=None, matricula_periodo=None):
        ids_componentes_curriculares_cumpridos = self.get_ids_componentes_curriculares_cumpridos(ano=ano, matricula_periodo=matricula_periodo)
        if ids is None:
            return ids_componentes_curriculares_cumpridos
        lista = []
        for i in ids:
            if i in ids_componentes_curriculares_cumpridos:
                lista.append(i)
        return lista
    def pode_ser_matriculado_no_diario(self, diario, ignorar_quebra_requisito=False):
        if MatriculaDiario.objects.filter(
            matricula_periodo__residente=self,
            diario__ano_letivo=diario.ano_letivo,
            diario__periodo_letivo=diario.periodo_letivo,
            diario__componente_curricular__componente=diario.componente_curricular.componente,
            situacao=MatriculaDiario.SITUACAO_CURSANDO,
        ).exists():
            return False, 'O residente está cursando este componente em outro diário.'

        #TODO
        return True, ''
        # qs_componente_curricular = self.matriz.componentecurricular_set.filter(
        #     componente=diario.componente_curricular.componente)
        # if qs_componente_curricular.exists():
        #     componente_curricular = qs_componente_curricular[0]
        #     return self.pode_cursar_componente_curricular(componente_curricular, False, ignorar_quebra_requisito)
        # else:
        #     return self.pode_cursar_componente_curricular(diario.componente_curricular, True, ignorar_quebra_requisito)
    def get_situacao(self):

        # if self.matriz_id and self.curso_campus.is_fic():
        #     self.pendencia_ch_obrigatoria = self.get_componentes_pendentes().exists()
        # elif self.matriz_id:
        #     if self.matriz.exige_tcc:
        #         self.pendencia_tcc = not self.apresentou_tcc()
        #     else:
        #         self.pendencia_tcc = False
        #     if self.curso_campus.exige_enade:
        #         self.pendencia_enade = not self.cumpriu_enade()
        #     if self.matriz.ch_pratica_profissional >= 1 or self.matriz.exige_estagio:
        #         self.pendencia_pratica_profissional = self.possui_pratica_profissional_pendente()
        #     else:
        #         self.pendencia_pratica_profissional = False
        #     if self.curso_campus.exige_colacao_grau:
        #         self.pendencia_colacao_grau = not self.colou_grau()
        #     self.pendencia_ch_atividade_complementar = self.get_ch_atividades_complementares_esperada() and self.get_ch_atividades_complementares_pendente() > 0 or False
        #     if self.get_ch_componentes_tcc_esperada():
        #         self.pendencia_ch_tcc = self.get_ch_componentes_tcc_pendente() > 0
        #     self.pendencia_ch_pratica_profissional = self.get_ch_componentes_pratica_profissional_esperada() and (self.get_ch_componentes_pratica_profissional_pendente() > 0)
        #     self.pendencia_ch_atividades_aprofundamento = self.get_ch_atividade_aprofundamento_esperada() and (self.get_ch_atividade_aprofundamento_pendente() > 0)
        #     self.pendencia_ch_atividades_extensao = self.get_ch_atividade_extensao_esperada() and (self.get_ch_atividade_extensao_pendente() > 0)
        #     if self.get_ch_componentes_seminario_esperada():
        #         self.pendencia_ch_seminario = self.get_ch_componentes_seminario_pendente() > 0
        #     if self.get_ch_pratica_como_componente_esperada():
        #         self.pendencia_ch_pratica_como_componente = self.get_ch_componentes_pratica_como_componente_pendente() > 0
        #     if self.get_ch_visita_tecnica_esperada():
        #         self.pendencia_ch_visita_tecnica = self.get_ch_componentes_visita_tecnica_pendente() > 0
        #
        #     self.pendencia_ch_eletiva = self.get_ch_componentes_eletivos_pendente() > 0
        #     self.pendencia_ch_optativa = self.get_ch_componentes_regulares_optativos_pendente() > 0
        #     self.pendencia_ch_obrigatoria = self.get_ch_componentes_regulares_obrigatorios_pendente() > 0
        #
        # # Caso o aluno ainda esteja com algum período letivo aberto, sua situação será "Matriculado"
        # if MatriculaPeriodo.objects.filter(aluno=self, situacao__id=SituacaoMatriculaPeriodo.MATRICULADO).exists():
        #     return SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
        #
        # # Cursos FICs possuem apenas um período letivo e requer, portanto, um tratamentno diferenciado
        # if self.curso_campus.is_fic():
        #     if MatriculaPeriodo.objects.filter(aluno=self, situacao__id=SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA).exists():
        #         return SituacaoMatricula.objects.get(pk=SituacaoMatricula.NAO_CONCLUIDO)
        #     else:
        #         if self.possui_pendencia():
        #             return SituacaoMatricula.objects.get(pk=SituacaoMatricula.NAO_CONCLUIDO)
        #         else:
        #             return SituacaoMatricula.objects.get(pk=SituacaoMatricula.CONCLUIDO)
        # else:
        #     # Caso o aluno não possua nenhum período letivo aberto, mas não cumpriu todos os requisitos de conclusão
        #     if self.possui_pendencia():
        #         if self.get_ultima_matricula_periodo().situacao == SituacaoMatriculaPeriodo.MATRICULADO:
        #             return SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
        #         else:
        #             return self.situacao
        #     else:
        #         # Caso o aluno possua um matrícula no período com sistuação "Em Aberto", essa matrícula será excluída
        #         qs_em_aberto = MatriculaPeriodo.objects.filter(aluno=self, situacao__id=SituacaoMatriculaPeriodo.EM_ABERTO)
        #         if qs_em_aberto.filter(
        #             creditoespecial__isnull=True,
        #             matriculadiario__isnull=True,
        #             matriculadiarioresumida__isnull=True,
        #             certificacaoconhecimento__isnull=True,
        #             aproveitamentoestudo__isnull=True,
        #             projetofinal__isnull=True,
        #         ).exists():
        #             qs_em_aberto.delete()
        #         if qs_em_aberto.exists():
        #             return SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
        #         else:
        #             # A situação dos concluintes de cursos que requer colação de graua deve ser "Formado"
        #             if self.curso_campus.exige_colacao_grau:
        #                 return SituacaoMatricula.objects.get(pk=SituacaoMatricula.FORMADO)
        #             else:
        #                 return SituacaoMatricula.objects.get(pk=SituacaoMatricula.CONCLUIDO)

        return SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)

    def atualizar_situacao(self, descricao_operacao=None):
        if self.situacao.id in [SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL]:
            self.situacao = self.get_situacao()
            self.save()

            # self.calcular_indice_rendimento()
            # self.atualizar_situacao_ultimo_periodo()
            # self.atualizar_periodo_referencia()
            # self.atualizar_data_conclusao()
            # self.atualizar_percentual_ch_cumprida()
            # self.calcular_ch_aulas_visita_tecnica()
            # self.calcular_ch_aulas_pcc()

    def get_projetos_finais(self):
        from residencia.models import ProjetoFinalResidencia
        return ProjetoFinalResidencia.objects.filter(matricula_periodo__residente=self)
    
    def is_matriculado(self):
        print(self.situacao.pk == SituacaoMatricula.MATRICULADO)
        return self.situacao.pk == SituacaoMatricula.MATRICULADO
    
    #ver isso depois
    def pode_emitir_declaracao(self):
        return True


class Observacao(LogResidenciaModel):
    observacao = models.TextField('Observação da Matrícula')
    residente = models.ForeignKeyPlus(Residente, verbose_name='Residente')
    data = models.DateFieldPlus(verbose_name='Data')
    usuario = models.ForeignKeyPlus('comum.User', verbose_name='Usuário', related_name='residente_observacao_set')

    class Meta:
        permissions = (('adm_delete_observacao', 'Pode deletar observações de outros usuários'),)


class SolicitacaoResidente(LogResidenciaModel):
    SEARCH_FIELDS = ['id', 'cpf', 'nome']

    STATUS_INCOMPLETO = 'INCOMPLETO'
    STATUS_EM_ANALISE = 'EM_ANALISE'
    STATUS_PRONTO_PARA_EXECUCAO = 'PRONTO_PARA_EXECUCAO'
    STATUS_AGUARDANDO_CORRECAO_DE_DADOS = 'AGUARDANDO_CORRECAO_DE_DADOS'
    STATUS_DADOS_CORRIGIDOS = 'DADOS_CORRIGIDOS'
    STATUS_ATENDIDO = 'ATENDIDO'
    STATUS_NAO_ATENDIDO = 'NAO_ATENDIDO'
    STATUS_EXPIRADO = 'EXPIRADO'
    STATUS_CHOICES = (
        (STATUS_INCOMPLETO, 'Incompleto'),
        (STATUS_EM_ANALISE, 'Em Análise'),
        (STATUS_AGUARDANDO_CORRECAO_DE_DADOS, 'Aguardando Correção de Dados'),
        (STATUS_DADOS_CORRIGIDOS, 'Dados Corrigidos'),
        (STATUS_PRONTO_PARA_EXECUCAO, 'Pronto Para Execução'),
        (STATUS_ATENDIDO, 'Atendido'),
        (STATUS_NAO_ATENDIDO, 'Não Atendido'),
        (STATUS_EXPIRADO, 'Expirado'),
    )

    # Fields
    nome = models.UnaccentField(max_length=200, db_index=True)
    nome_social = models.UnaccentField("Nome Social", max_length=200, blank=True, db_index=True)
    nome_registro = models.UnaccentField("Nome de Registro", max_length=200, blank=True, db_index=True)
    email = models.EmailField(blank=True, verbose_name="E-mail Principal")
    cpf = models.CharField(max_length=20, null=True, verbose_name="CPF", blank=False, db_index=True)
    nascimento_data = models.DateFieldPlus("Data de Nascimento", null=True)
    sexo = models.CharField(max_length=1, null=True, choices=[["M", "Masculino"], ["F", "Feminino"]])

    situacao = models.CharFieldPlus('Situação', choices=STATUS_CHOICES, null=True)
    alterado_em = models.DateTimeFieldPlus('Data de Alteração', auto_now=True, null=True, blank=True)
    parecer = models.CharField('Parecer da Solicitação', max_length=1000, null=True, blank=True)
    parecer_autor_vinculo = models.ForeignKeyPlus(
        'comum.Vinculo',
        verbose_name='Autor do Parecer',
        related_name='residencia_autor_parecer_vinculo',
        null=True, blank=True, on_delete=models.CASCADE
    )
    parecer_data = models.DateTimeFieldPlus('Data do Parecer', null=True, blank=True)

    foto = ImageWithThumbsField(storage=get_overwrite_storage(), use_id_for_name=True, upload_to='solicitresidentes',
                                sizes=((75, 100), (150, 200)), null=True, blank=True)
    estado_civil = models.CharFieldPlus(choices=Residente.ESTADO_CIVIL_CHOICES, null=True)
    raca = models.ForeignKeyPlus("comum.Raca", null=True, on_delete=models.CASCADE)

    # endereco
    logradouro = models.CharFieldPlus(max_length=255, verbose_name='Logradouro', null=True)
    numero = models.CharFieldPlus(max_length=255, verbose_name='Número', null=True)
    complemento = models.CharFieldPlus(max_length=255, verbose_name='Complemento', null=True, blank=True)
    bairro = models.CharFieldPlus(max_length=255, verbose_name='Bairro', null=True)
    cep = models.CharFieldPlus(max_length=255, verbose_name='CEP', null=True, blank=True)
    nomecidade = models.CharFieldPlus(max_length=255, verbose_name='Cidade', null=True)
    # cidade = models.ForeignKeyPlus('comum.Municipio', verbose_name='Cidade', null=True)
    tipo_zona_residencial = models.CharFieldPlus(
        choices=Residente.TIPO_ZONA_RESIDENCIAL_CHOICES, verbose_name='Zona Residencial',
        null=True, blank=True
    )

    # dados familiares
    nome_pai = models.CharFieldPlus(max_length=255, verbose_name='Nome do Pai', null=True, blank=True)
    estado_civil_pai = models.CharFieldPlus(choices=Residente.ESTADO_CIVIL_CHOICES, null=True, blank=True)
    pai_falecido = models.BooleanField(verbose_name='Pai é falecido?', default=False)
    nome_mae = models.CharFieldPlus(max_length=255, verbose_name='Nome da Mãe', null=True, blank=False)
    estado_civil_mae = models.CharFieldPlus(verbose_name='Estado Civil da Mãe', choices=Residente.ESTADO_CIVIL_CHOICES, null=True, blank=True)
    mae_falecida = models.BooleanField(verbose_name='Mãe é falecida?', default=False)
    responsavel = models.CharFieldPlus(max_length=255, verbose_name='Nome do Responsável', null=True, blank=True)
    email_responsavel = models.CharFieldPlus(max_length=255, verbose_name='Email do Responsável', null=True, blank=True)
    parentesco_responsavel = models.CharFieldPlus(
        verbose_name='Parentesco do Responsável', choices=Residente.PARENTESCO_CHOICES, null=True, blank=True
    )
    cpf_responsavel = models.BrCpfField(verbose_name='CPF do Responsável', null=True, blank=True)

    # contato
    telefone_principal = models.CharFieldPlus(max_length=255, verbose_name='Telefone Principal', null=True, blank=True)
    telefone_secundario = models.CharFieldPlus(max_length=255, verbose_name='Celular', null=True,
                                               blank=True)
    telefone_adicional_1 = models.CharFieldPlus(max_length=255, verbose_name='Telefone do Responsável', null=True,
                                                blank=True)
    telefone_adicional_2 = models.CharFieldPlus(max_length=255, verbose_name='Telefone do Responsável', null=True,
                                                blank=True)

    # outras informacoes
    tipo_sanguineo = models.CharFieldPlus(max_length=255, verbose_name='Tipo Sanguíneo', null=True, blank=True,
                                          choices=Residente.TIPO_SANGUINEO_CHOICES)
    nacionalidade = models.CharFieldPlus(max_length=255, verbose_name='Nacionalidade', null=True,
                                         choices=Residente.TIPO_NACIONALIDADE_CHOICES)
    passaporte = models.CharFieldPlus(max_length=50, verbose_name='Nº do Passaporte', default='')
    pais_origem = models.ForeignKeyPlus('comum.Pais', verbose_name='País de Origem', null=True, blank=True,
                                        help_text='Obrigatório para estrangeiros')
    nomenaturalidade = models.CharFieldPlus(max_length=255, verbose_name='Naturalidade', null=True)
    # naturalidade = models.ForeignKeyPlus(
    #     'comum.Municipio',
    #     verbose_name='Naturalidade',
    #     null=True,
    #     blank=True,
    #     related_name='solicitresidente_naturalidade_set',
    #     help_text='Cidade em que o(a) residente nasceu. Obrigatório para brasileiros',
    # )

    tipo_necessidade_especial = models.CharFieldPlus(
        verbose_name='Tipo de Necessidade Especial', null=True, blank=True,
        choices=Residente.TIPO_NECESSIDADE_ESPECIAL_CHOICES
    )
    tipo_transtorno = models.CharFieldPlus(
        verbose_name='Tipo de Transtorno', null=True, blank=True, choices=Residente.TIPO_TRANSTORNO_CHOICES
    )
    superdotacao = models.CharFieldPlus(
        verbose_name='Superdotação', null=True, blank=True, choices=Residente.SUPERDOTACAO_CHOICES
    )
    outras_necessidades = models.CharFieldPlus(max_length=255, 
        verbose_name='Outras necessidades', null=True, blank=True
    )

    # dados escolares
    nivel_ensino_anterior = models.ForeignKeyPlus('comum.NivelEnsino', null=True, blank=True, on_delete=models.CASCADE)
    tipo_instituicao_origem = models.CharFieldPlus(
        max_length=255, verbose_name='Tipo de Instituição', null=True,
        choices=Residente.TIPO_INSTITUICAO_ORIGEM_CHOICES, blank=True
    )
    nome_instituicao_anterior = models.CharFieldPlus(
        max_length=255, verbose_name='Nome da Instituição', null=True, blank=True
    )
    ano_conclusao_estudo_anterior = models.ForeignKeyPlus(
        'comum.Ano', verbose_name='Ano de Conclusão de Estudo Anterior',
        null=True,
        related_name='solicitresidente_ano_conclusao_anterior_set',
        blank=True,
        on_delete=models.CASCADE
    )

    categoria = models.CharFieldPlus(
        'Categoria', max_length=100, choices=Residente.CATEGORIAS_CHOICES, null=True, blank=True
    )

    # conselho classe
    numero_registro = models.CharFieldPlus(
        'Número de Registro no Conselho de Fiscalização Profissional', null=True, blank=True
    )
    conselho = models.ForeignKeyPlus(
        'comum.ConselhoProfissional', verbose_name='Conselho de Fiscalização Profissional', null=True, blank=True
    )

    # rg
    numero_rg = models.CharFieldPlus(max_length=255, verbose_name='Número do RG', null=True, blank=True)
    uf_emissao_rg = models.ForeignKeyPlus(
        'comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
        related_name='solicitresidente_emissor_rg_set'
    )
    orgao_emissao_rg = models.ForeignKeyPlus(
        'comum.OrgaoEmissorRg', verbose_name='Orgão Emissor', null=True, blank=True
    )
    data_emissao_rg = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)

    # titulo_eleitor
    numero_titulo_eleitor = models.CharFieldPlus(
        max_length=255, verbose_name='Título de Eleitor', null=True, blank=True
    )
    zona_titulo_eleitor = models.CharFieldPlus(max_length=255, verbose_name='Zona', null=True, blank=True)
    secao = models.CharFieldPlus(max_length=255, verbose_name='Seção', null=True, blank=True)
    data_emissao_titulo_eleitor = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    uf_emissao_titulo_eleitor = models.ForeignKeyPlus(
        'comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
        related_name='solicitresidente_emissor_titulo_eleitor_set', on_delete=models.CASCADE
    )

    # carteira de reservista
    numero_carteira_reservista = models.CharFieldPlus(
        max_length=255, verbose_name='Número da Carteira de Reservista', null=True, blank=True
    )
    regiao_carteira_reservista = models.CharFieldPlus(max_length=255, verbose_name='Região', null=True, blank=True)
    serie_carteira_reservista = models.CharFieldPlus(max_length=255, verbose_name='Série', null=True, blank=True)
    estado_emissao_carteira_reservista = models.ForeignKeyPlus(
        'comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
        related_name='solicitresidente_estado_emissor_carteira_reservista_set', on_delete=models.CASCADE
    )
    ano_carteira_reservista = models.PositiveIntegerField(verbose_name='Ano', null=True, blank=True)

    # certidao_civil
    tipo_certidao = models.CharFieldPlus(
        max_length=255, verbose_name='Tipo de Certidão', null=True, blank=True, choices=Residente.TIPO_CERTIDAO_CHOICES
    )
    cartorio = models.CharFieldPlus(max_length=255, verbose_name='Cartório', null=True, blank=True)
    numero_certidao = models.CharFieldPlus(max_length=255, verbose_name='Número de Termo', null=True, blank=True)
    folha_certidao = models.CharFieldPlus(max_length=255, verbose_name='Folha', null=True, blank=True)
    livro_certidao = models.CharFieldPlus(max_length=255, verbose_name='Livro', null=True, blank=True)
    data_emissao_certidao = models.DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    matricula_certidao = models.CharFieldPlus(max_length=255, verbose_name='Matrícula', null=True, blank=True)

    poder_publico_responsavel_transporte = models.CharFieldPlus(
        'Poder Público Responsável pelo Transporte Escolar',
        choices=Residente.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, null=True, blank=True
    )
    tipo_veiculo = models.CharFieldPlus(
        'Tipo de Veículo Utilizado no Transporte Escolar', choices=Residente.TIPO_VEICULO_CHOICES_FOR_FORM, null=True,
        blank=True
    )

    class Meta:
        ordering = ('nome',)
        verbose_name = 'Solicitação de Residente'
        verbose_name_plural = 'Solicitações de Residente'

    def eh_pne(self):
        return bool(self.tipo_necessidade_especial)

    def get_nome(self):
        return self.nome

    def get_nome_social_composto(self):
        if self.nome_social:
            return f'{self.nome_registro} ({self.nome_social})'
        else:
            return self.nome

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

    def __str__(self):
        return f'{normalizar_nome_proprio(self.get_nome_social_composto())}'

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
            if self.nomecidade:
                lista.append(str(self.nomecidade))
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
        return f'/residencia/solicitresidente/{self.pk}/'

    def get_foto_75x100_url(self):
        return self.foto and self.foto.url_75x100 or '/static/comum/img/default.jpg'

    def get_foto_150x200_url(self):
        return self.foto and self.foto.url_150x200 or '/static/comum/img/default.jpg'

class DocumentoFrequenciaMensalResidente(LogResidenciaModel):
    YEAR_CHOICES = []
    for ano in range(2015, (datetime.datetime.now().year+1)):
        YEAR_CHOICES.append((ano,ano))
    
    residente = models.ForeignKeyPlus(Residente, related_name='documento_frequencia_residente_set',)
    documento_fisico = models.FileFieldPlus(upload_to='residencia/frequencias_fisicas/', max_length=250,null=True, blank=True,)
    mes_referencia = models.PositiveIntegerFieldPlus("Mês de Referência", choices=list(zip(range(1, 13), range(1, 13))), db_index=True, null=True, blank=True, default=datetime.datetime.now().month)
    ano_referencia = models.PositiveIntegerFieldPlus("Ano de Referência", db_index=True, null=True, blank=True, choices=YEAR_CHOICES, default=datetime.datetime.now().year)
    data_hora_upload = models.DateTimeField(db_index=True, null=True, blank=True, auto_now_add=True)

    @property 
    def filename(self):
        return os.path.basename(self.documento_fisico.name)

    class Meta:        
        verbose_name = 'Documento de Frequencia Mensal'
        verbose_name_plural = 'Documentos de Frequencia Mensal'


class FrequenciaResidente(LogResidenciaModel):
    residente = models.ForeignKeyPlus(Residente, related_name='frequencia_residente_set',)
    data_hora_entrada = models.DateTimeField(db_index=True, null=True, blank=True)
    data_hora_saida = models.DateTimeField(db_index=True, null=True, blank=True)
    confirmacao = models.BooleanField(verbose_name="Confirmado?", null=True, blank=True)
    preceptor_confirmador = models.ForeignKeyPlus('rh.Servidor', verbose_name='Preceptor', null=True, blank=True)
    diario = models.ForeignKeyPlus('residencia.MatriculaDiario', related_name='matriculadiario_frequencia_residente_set', verbose_name='Matricula Diario', null=True, blank=True)

    class History:
        disabled = True

    class Meta:        
        verbose_name = 'Frequência'
        verbose_name_plural = 'Frequências'

    def get_horas(self):
        total = 0
        delta = self.data_hora_saida - self.data_hora_entrada
        segundos = delta.seconds
        total += segundos
        if total > 0:
            return round(total / 60 / 60, 1)
        else:
            return total


    @staticmethod
    def segundos_para_time(segundos=0):
        """ segundos para Time """
        if segundos >= 0:
            minutos, segundos = divmod(segundos, 60)
            horas, minutos = divmod(minutos, 60)
            #
            return datetime.time(hour=horas, minute=minutos, second=segundos)
        return datetime.time(second=0)

    @staticmethod
    def time_para_segundos(time=None):
        """ Time para segundos """
        if time:
            return time.hour * 60 * 60 + time.minute * 60 + time.second
        #
        return 0
