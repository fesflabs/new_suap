import datetime
import operator
import hashlib
import math
import os
import csv
import re
import tempfile
import threading
from collections import OrderedDict
from datetime import date, timedelta
from operator import itemgetter
from xml.dom import minidom
import xlrd
import xlwt

from ckeditor.fields import RichTextFormField
from djtools.forms.fields.captcha import ReCaptchaField
from dateutil import relativedelta
from django.apps.registry import apps
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import transaction
from django.db.models import Q, F
from django.db.models.aggregates import Count, Max, Sum
from django.forms.widgets import Select
from django.http import HttpResponse
from django.template import defaultfilters
from django.utils.safestring import mark_safe
from xlrd.biffh import XLRDError

from djtools.storages import cache_file
from edu.models.censos import QuestaoEducacenso, RegistroEducacenso, RespostaEducacenso
from ldap_backend.models import LdapConf
from rh.enums import Nacionalidade
from rh.models import ArquivoUnico
from comum import utils
from comum.models import Ano, Configuracao, Municipio, PessoaEndereco, PessoaTelefone, PrestadorServico, Raca, Sala, \
    User, UsuarioGrupo, UsuarioGrupoSetor, Vinculo, EmailBlockList, CertificadoDigital

from comum.utils import adicionar_mes, get_uo, somar_data, retira_acentos
from djtools import forms
from djtools.forms.fields import BrCpfField
from djtools.forms.widgets import (
    AjaxSelectMultiplePopup,
    AutocompleteWidget,
    CheckboxSelectMultiplePlus,
    PhotoCapturePortraitInput,
    RenderableRadioSelect,
    RenderableSelectMultiple,
    TextareaCloneWidget,
    TreeWidget,
)
from djtools.forms.wizard import FormWizardPlus
from djtools.html.graficos import ColumnChart, LineChart, PieChart
from djtools.templatetags.filters import format_, format_iterable, in_group
from djtools.testutils import running_tests
from djtools.utils import CsvResponse, eh_nome_completo, send_mail, httprr
from djtools.utils import human_str, normalizar_nome_proprio, mask_cpf, cpf_valido, email_valido
from edu import tasks
from edu.models import Autorizacao, Reconhecimento, ItemPlanoEstudo
from edu.models import (
    ComponenteCurricular,
    Matriz,
    EstruturaCurso,
    CalendarioAcademico,
    Turno,
    HorarioCampus,
    Diario,
    ProfessorDiario,
    Professor,
    NivelEnsino,
    FormaIngresso,
    Aluno,
    MatriculaPeriodo,
    MatriculaDiario,
    SituacaoMatriculaPeriodo,
    SequencialMatricula,
    Aula,
    CursoCampus,
    HistoricoSituacaoMatriculaPeriodo,
    HistoricoSituacaoMatricula,
    Convenio,
    MatrizCurso,
    Cidade,
    Pais,
    Estado,
    Cartorio,
    OrgaoEmissorRg,
    Diretoria,
    PERIODO_LETIVO_CHOICES,
    SituacaoMatricula,
    Turma,
    RegistroEmissaoDiploma,
    ConfiguracaoLivro,
    ModeloDocumento,
    HistoricoImportacao,
    Log,
    MaterialAula,
    MaterialDiario,
    AbonoFaltas,
    EquivalenciaComponenteQAcademico,
    Componente,
    ProcedimentoMatricula,
    CertificacaoConhecimento,
    AproveitamentoEstudo,
    Disciplina,
    NucleoCentralEstruturante,
    Modalidade,
    ProjetoFinal,
    HistoricoRelatorio,
    LinhaPesquisa,
    TipoAtividadeComplementar,
    AtividadeComplementar,
    ItemConfiguracaoAtividadeComplementar,
    ConfiguracaoAtividadeComplementar,
    ConfiguracaoPedidoMatricula,
    AulaCampo,
    AlunoAulaCampo,
    ConfiguracaoSeguro,
    TipoProfessorDiario,
    Mensagem,
    Polo,
    CoordenadorPolo,
    AtividadePolo,
    TutorPolo,
    ConfiguracaoAvaliacao,
    NotaAvaliacao,
    SolicitacaoRelancamentoEtapa,
    ConfiguracaoCertificadoENEM,
    RegistroAlunoINEP,
    SolicitacaoCertificadoENEM,
    RegistroEmissaoCertificadoENEM,
    CoordenadorRegistroAcademico,
    TipoComponente,
    Nucleo,
    AproveitamentoComponente,
    MatriculaDiarioResumida,
    ConvocacaoENADE,
    RegistroConvocacaoENADE,
    JustificativaDispensaENADE,
    ColacaoGrau,
    ParticipacaoColacaoGrau,
    VinculoProfessorEAD,
    Evento,
    ParticipanteEvento,
    SolicitacaoProrrogacaoEtapa,
    HorarioAulaDiario,
    DiarioEspecial,
    Encontro,
    CoordenadorModalidade,
    Minicurso,
    TurmaMinicurso,
    ConfiguracaoCreditosEspeciais,
    CreditoEspecial,
    ItemConfiguracaoCreditosEspeciais,
    EstagioDocente,
    VisitaEstagioDocente,
    RegistroHistorico,
    PedidoMatriculaDiario,
    Requerimento,
    Premiacao,
    MedidaDisciplinar,
    TipoAtividadeAprofundamento,
    ItemConfiguracaoAtividadeAprofundamento,
    ConfiguracaoAtividadeAprofundamento,
    OcorrenciaDiario,
    RequerimentoCancelamentoDisciplina,
    RequerimentoMatriculaDisciplina,
    ItemConfiguracaoAvaliacao,
    AtividadeCurricularExtensao,
    PeriodoLetivoAtual,
    MonitorMinicurso,
    CodigoAutenticadorSistec,
    AtaEletronica,
    AlunoArquivo,
    CertificadoDiploma,
    TipoAlunoArquivo,
    ClassificacaoComplementarComponenteCurricular,
    PlanoEnsino,
)
from edu.models.alunos import Observacao
from edu.models.atividades_complementares import AtividadeAprofundamento
from edu.models.cadastros_gerais import TipoMedidaDisciplinar, HorarioAula
from edu.models.diarios import ObservacaoDiario
from edu.models.diarios import TopicoDiscussao, RespostaDiscussao, Trabalho, EntregaTrabalho
from edu.models.diarios_especiais import HorarioAulaDiarioEspecial
from edu.models.turmas import ProfessorMinicurso
from edu.q_academico import DAO, MockDAO
from processo_seletivo.models import CandidatoVaga, Edital
# from protocolo.models import Processo
from rh.forms import get_choices_nome_usual
from rh.models import Funcionario, JornadaTrabalho, Pessoa, PessoaFisica, Servidor, Setor, Situacao, UnidadeOrganizacional
from _functools import reduce
from edu.models.atividades import HorarioAtividadeExtra
from comum import signer


class AlunoForm(forms.ModelFormPlus):
    nome = forms.CharFieldPlus(width=500)
    nome_social = forms.CharFieldPlus(required=False, label='Nome Social', width=255)
    data_nascimento = forms.DateFieldPlus()
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    cpf = forms.BrCpfField(label='CPF', required=False)
    passaporte = forms.CharField(required=False, label='Nº do Passaporte')
    cartorio = forms.ModelChoiceFieldPlus(
        Cartorio.objects,
        required=False,
        label='Cartório',
        help_text='Digite o nome do cartório ou cidade para listar os catórios cadastrados',
        widget=AutocompleteWidget(search_fields=Cartorio.SEARCH_FIELDS),
    )

    telefone_principal = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Principal', help_text='(XX) XXXX-XXXX')
    telefone_secundario = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Secundário', help_text='(XX) XXXX-XXXX')
    telefone_adicional_1 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    telefone_adicional_2 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')

    raca = forms.ModelChoiceField(Raca.objects.all(), required=True, label='Raça')
    tipo_instituicao_origem = forms.ChoiceField(required=True, label='Tipo da Instituição', choices=[['', '----']] + Aluno.TIPO_INSTITUICAO_ORIGEM_CHOICES)

    estado = forms.ModelChoiceField(Estado.objects, label='Estado', required=False)

    cidade = forms.ModelChoiceFieldPlus(
        Cidade.objects, label='Cidade', required=True, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS, form_filters=[('estado', 'estado__in')])
    )

    estado_naturalidade = forms.ModelChoiceField(Estado.objects, label='Estado de Origem', required=False)

    naturalidade = forms.ModelChoiceFieldPlus(
        Cidade.objects, label='Naturalidade', required=False, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS, form_filters=[('estado_naturalidade', 'estado__in')])
    )

    possui_convenio = forms.BooleanRequiredField(label='Possui Convênio?')

    fieldsets = (
        ('Identificação', {'fields': ('nome', 'nome_social', ('cpf', 'passaporte'), ('data_nascimento', 'estado_civil', 'sexo'))}),
        (
            'Dados Familiares',
            {
                'fields': (
                    'nome_pai',
                    'estado_civil_pai',
                    'pai_falecido',
                    'nome_mae',
                    'estado_civil_mae',
                    'mae_falecida',
                    'responsavel',
                    'email_responsavel',
                    'parentesco_responsavel',
                    'cpf_responsavel',
                )
            },
        ),
        ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'estado', 'cidade', 'tipo_zona_residencial')}),
        ('Contato', {'fields': (('telefone_principal', 'telefone_secundario'), ('telefone_adicional_1', 'telefone_adicional_2'))}),
        ('Deficiências, Transtornos e Superdotação', {'fields': ('tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao')}),
        ('Outras Informações', {'fields': ('tipo_sanguineo', 'nacionalidade', 'pais_origem', 'estado_naturalidade', 'naturalidade', 'raca')}),
        ('Dados Escolares', {'fields': ('nivel_ensino_anterior', 'tipo_instituicao_origem', 'nome_instituicao_anterior', 'ano_conclusao_estudo_anterior', 'habilitacao_pedagogica')}),
        ('RG', {'fields': ('numero_rg', 'uf_emissao_rg', 'orgao_emissao_rg', 'data_emissao_rg')}),
        ('Título de Eleitor', {'fields': ('numero_titulo_eleitor', 'zona_titulo_eleitor', 'secao', 'data_emissao_titulo_eleitor', 'uf_emissao_titulo_eleitor')}),
        (
            'Carteira de Reservista',
            {'fields': ('numero_carteira_reservista', 'regiao_carteira_reservista', 'serie_carteira_reservista', 'estado_emissao_carteira_reservista', 'ano_carteira_reservista')},
        ),
        ('Certidão Civil', {'fields': ('tipo_certidao', 'cartorio', 'numero_certidao', 'folha_certidao', 'livro_certidao', 'data_emissao_certidao', 'matricula_certidao')}),
        ('Registro', {'fields': ('numero_pasta',)}),
        ('Dados da Matrícula', {'fields': ('turno', 'linha_pesquisa', 'habilitacao', 'forma_ingresso', 'aluno_especial', 'polo', 'possui_convenio', 'convenio')}),
        ('Dados do MEC', {'fields': ('codigo_educacenso', 'nis')}),
        ('Transporte Escolar', {'fields': ('poder_publico_responsavel_transporte', 'tipo_veiculo')}),
    )

    class Meta:
        model = Aluno
        exclude = ()

    class Media:
        js = ('/static/edu/js/AlunoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['nome'] = self.instance.pessoa_fisica.nome_registro
            self.initial['nome_social'] = self.instance.pessoa_fisica.nome_social
            self.initial['data_nascimento'] = self.instance.pessoa_fisica.nascimento_data
            self.initial['sexo'] = self.instance.pessoa_fisica.sexo
            self.initial['cpf'] = self.instance.pessoa_fisica.cpf
            self.initial['raca'] = self.instance.pessoa_fisica.raca_id

    def save(self, *args, **kwargs):
        self.instance.pessoa_fisica.nome_registro = self.cleaned_data['nome']
        self.instance.pessoa_fisica.nome_social = self.cleaned_data['nome_social']
        self.instance.pessoa_fisica.nascimento_data = self.cleaned_data['data_nascimento']
        self.instance.pessoa_fisica.sexo = self.cleaned_data['sexo']
        self.instance.pessoa_fisica.cpf = self.cleaned_data['cpf']
        self.instance.pessoa_fisica.raca = self.cleaned_data['raca']
        self.instance.pessoa_fisica.save()
        return super().save(*args, **kwargs)

    def clean_poder_publico_responsavel_transporte(self):
        poder_publico_responsavel_transporte = self.data.get('poder_publico_responsavel_transporte')
        tipo_veiculo = self.data.get('tipo_veiculo')
        if poder_publico_responsavel_transporte and not self.data.get('tipo_veiculo'):
            raise forms.ValidationError('Informe o tipo transporte público')
        if tipo_veiculo and not self.data.get('poder_publico_responsavel_transporte'):
            raise forms.ValidationError('Informe o responsável pelo transporte público')
        return poder_publico_responsavel_transporte

    def clean_passaporte(self):
        nacionalidade = self.data.get('nacionalidade')
        passaporte = self.data.get('passaporte')
        if nacionalidade == 'Estrangeira' and not passaporte:
            raise forms.ValidationError('Informe o passaporte do aluno.')
        return passaporte

    def clean_cpf(self):
        nacionalidade = self.data.get('nacionalidade')
        cpf = self.data.get('cpf')
        if nacionalidade != 'Estrangeira' and not cpf:
            raise forms.ValidationError('Informe o CPF do aluno.')
        return cpf

    def clean_aluno_pne(self):
        aluno_pne = self.cleaned_data.get('aluno_pne')

        if aluno_pne and not (self.data.get('tipo_necessidade_especial') or self.data.get('tipo_transtorno') or self.data.get('superdotacao')):
            raise forms.ValidationError('Informe a deficiência, transtorno ou superdotação do aluno')
        return aluno_pne

    def clean_polo(self):
        curso_campus = self.instance.curso_campus
        polo = self.cleaned_data.get('polo')

        if curso_campus.diretoria.ead and not polo:
            raise ValidationError('É necessário informar o Polo do Aluno.')

        if not curso_campus.diretoria.ead and polo:
            raise ValidationError('Remova o polo do aluno.')

        return self.cleaned_data.get('polo')

    def clean_pais_origem(self):
        if 'nacionalidade' in self.cleaned_data:
            nacionalidade = self.cleaned_data['nacionalidade']

            if not nacionalidade == 'Brasileira':
                if not self.cleaned_data.get('pais_origem'):
                    raise forms.ValidationError('O campo país de origem é obrigatório quando a pessoa nasceu no exterior.')

        return self.cleaned_data.get('pais_origem')

    def clean_naturalidade(self):
        if 'nacionalidade' in self.cleaned_data:
            nacionalidade = self.cleaned_data['nacionalidade']
            naturalidade = self.cleaned_data.get('naturalidade')
            nome_pais = naturalidade and naturalidade.pais and naturalidade.pais.nome
            if nacionalidade == 'Brasileira':
                if not naturalidade:
                    raise forms.ValidationError('O campo naturalidade é obrigatório quando a pessoa nasceu no Brasil.')

                if nome_pais != 'Brasil':
                    raise forms.ValidationError('Não pode ser informado uma naturalidade fora do Brasil para aluno com nacionalidade Brasileira.')

            elif nome_pais == 'Brasil':
                raise forms.ValidationError('Não pode ser informado uma naturalidade do Brasil para aluno com nacionalidade Estrangeira ou Brasileira - Nascido no exterior ou naturalizado.')

        return self.cleaned_data.get('naturalidade')

    def clean_convenio(self):
        possui_convenio = self.cleaned_data.get('possui_convenio')
        if possui_convenio and not self.data.get('convenio'):
            raise forms.ValidationError('Informe o convênio')
        elif not possui_convenio and self.data.get('convenio'):
            raise forms.ValidationError('Não é possível selecionar um convênio quando o valor do campo "Possui Convênio?" é "Não".')
        return self.cleaned_data.get('convenio')


class AlunoCRAForm(AlunoForm):
    fieldsets = (
        ('Identificação', {'fields': (('nome', 'data_nascimento'), ('cpf', 'passaporte'), ('sexo', 'raca'))}),
        ('Dados Familiares', {'fields': ('nome_pai', 'nome_mae')}),
        ('Endereço', {'fields': (('cep', 'bairro'), 'logradouro', ('numero', 'complemento'), ('cidade', 'tipo_zona_residencial'))}),
        ('Contato', {'fields': ('telefone_principal',)}),
        ('Deficiências, Transtornos e Superdotação', {'fields': ('tipo_necessidade_especial', ('tipo_transtorno', 'superdotacao'))}),
        ('Outras Informações', {'fields': ('nacionalidade', 'pais_origem', 'naturalidade', 'tipo_sanguineo')}),
        ('Dados Escolares', {'fields': ('nivel_ensino_anterior', ('tipo_instituicao_origem', 'ano_conclusao_estudo_anterior'))}),
        ('RG', {'fields': (('numero_rg', 'uf_emissao_rg'), ('orgao_emissao_rg', 'data_emissao_rg'))}),
        ('Título de Eleitor', {'fields': ('numero_titulo_eleitor', 'zona_titulo_eleitor', 'secao', 'data_emissao_titulo_eleitor', 'uf_emissao_titulo_eleitor')}),
        ('Registro', {'fields': ('numero_pasta',)}),
        ('Dados da Matrícula', {'fields': ('turno', 'habilitacao', 'linha_pesquisa', 'forma_ingresso', ('aluno_especial', 'polo'), ('possui_convenio', 'convenio'))}),
    )

    class Meta:
        model = Aluno
        fields = (
            'nome',
            'cpf',
            'data_nascimento',
            'sexo',
            'nome_pai',
            'nome_mae',
            'logradouro',
            'numero',
            'complemento',
            'bairro',
            'cep',
            'cidade',
            'tipo_zona_residencial',
            'telefone_principal',
            'telefone_secundario',
            'telefone_adicional_1',
            'telefone_adicional_2',
            'nacionalidade',
            'pais_origem',
            'naturalidade',
            'nivel_ensino_anterior',
            'tipo_instituicao_origem',
            'raca',
            'ano_conclusao_estudo_anterior',
            'numero_rg',
            'uf_emissao_rg',
            'orgao_emissao_rg',
            'data_emissao_rg',
            'numero_titulo_eleitor',
            'zona_titulo_eleitor',
            'secao',
            'data_emissao_titulo_eleitor',
            'uf_emissao_titulo_eleitor',
            'numero_pasta',
            'observacao_historico',
            'turno',
            'habilitacao',
            'linha_pesquisa',
            'forma_ingresso',
            'aluno_especial',
            'polo',
            'tipo_necessidade_especial',
            'tipo_transtorno',
            'superdotacao',
            'possui_convenio',
            'convenio'
        )

    class Media:
        js = ('/static/edu/js/AlunoCRAForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['raca'].required = False
        self.fields['cidade'].required = False
        self.fields['logradouro'].required = False
        self.fields['numero'].required = False
        self.fields['bairro'].required = False
        self.fields['tipo_instituicao_origem'].required = False
        self.fields['tipo_zona_residencial'].required = False

        self.fields['naturalidade'].required = True
        self.fields['cpf'].required = True
        self.fields['numero_rg'].required = True
        self.fields['uf_emissao_rg'].required = True
        self.fields['orgao_emissao_rg'].required = True

    def clean_convenio(self):
        possui_convenio = self.cleaned_data.get('possui_convenio')
        if possui_convenio and not self.data.get('convenio'):
            raise forms.ValidationError('Informe o convênio')
        elif not possui_convenio and self.data.get('convenio'):
            raise forms.ValidationError('Não é possível selecionar um convênio quando o valor do campo "Possui Convênio?" é "Não".')
        return self.cleaned_data.get('convenio')


class SituacaoMatriculaPeriodoForm(forms.ModelFormPlus):
    periodo_matriz = forms.ChoiceField(label='Período da Matriz', choices=[[x, x] for x in range(1, 10)])
    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Turma', required=False)
    METHOD = 'POST'

    class Meta:
        model = MatriculaPeriodo
        fields = ('situacao', 'periodo_matriz', 'turma')

    def __init__(self, matricula_periodo, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def processar(self):
        self.instance.situacao = self.cleaned_data.get('situacao')
        self.instance.save()
        self.instance.aluno.atualizar_situacao()


class SituacaoMatriculaForm(forms.ModelFormPlus):
    METHOD = 'POST'

    class Meta:
        model = Aluno
        fields = ('situacao',)

    def processar(self):
        self.instance.situacao = self.cleaned_data.get('situacao')
        self.instance.save()


class RejeitarSolicitacaoUsuarioForm(forms.FormPlus):
    SUBMIT_LABEL = 'Rejeitar Solicitação do Usuário'
    razao_indeferimento = forms.CharField(widget=forms.Textarea(), required=True, label='Razão do Indeferimento')
    fieldsets = (('', {'fields': ('razao_indeferimento',)}),)


class AtenderSolicitacaoProrrogacaoEtapaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Atender Solicitação do Usuário'
    data_prorrogacao = forms.DateFieldPlus(label='Data limite da Prorrogação', required=True)


class ReplicacaoCalendarioForm(forms.FormPlus):
    SUBMIT_LABEL = 'Replicar Calendário'
    uos = forms.MultipleModelChoiceFieldPlus(
        UnidadeOrganizacional.objects.campi().all(),
        label='Campus',
        required=True,
        help_text='Informe os campi para os quais você deseja replicar o calendário',
    )

    def processar(self, calendario):
        return calendario.replicar(self.cleaned_data['uos'])


class ReplicacaoCursoCampusForm(forms.FormPlus):
    SUBMIT_LABEL = 'Replicar Curso'
    diretoria = forms.ModelChoiceField(Diretoria.objects, label='Diretoria', required=True, help_text='Informe o campus para o qual você deseja replicar o curso')
    codigo = forms.CharField(label='Código')
    coordenador = forms.ModelChoiceFieldPlus(Funcionario.objects, label='Coordenador', required=False, help_text='Informe o coordenador do curso')
    coordenador_2 = forms.ModelChoiceFieldPlus(Funcionario.objects, label='Vice-Coordenador', required=False, help_text='Informe o vice-coordenador do curso')

    def __init__(self, *args, **kwargs):
        curso_campus = kwargs.pop('curso_campus')
        super().__init__(*args, **kwargs)
        self.fields['codigo'].initial = curso_campus.codigo

    def processar(self, campus_curso):
        campus_curso.replicar(self.cleaned_data['diretoria'], self.cleaned_data['codigo'], self.cleaned_data['coordenador'], self.cleaned_data['coordenador_2'])
        return campus_curso


class ReplicacaoConfiguracaoPedidoMatriculaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Replicar'
    descricao = forms.CharFieldPlus(required=True, label='Descrição', width=500)
    data_inicio = forms.DateFieldPlus(required=True, label='Data de Início')
    data_fim = forms.DateFieldPlus(required=True, label='Data do Fim')

    impedir_troca_turma = forms.BooleanField(
        label='Impedir troca de turma', required=False, help_text='Marque essa opção caso deseje impedir que alunos do regime seriado possam trocar de turma dentro do seu respectivo turno.',
    )
    restringir_por_curso = forms.BooleanField(
        label='Restringir por curso', required=False, help_text='Marque essa opção caso deseje impedir que os alunos se matriculem em disciplinas de outros cursos.'
    )
    requer_atualizacao_dados = forms.BooleanField(
        label='Requer atualização do cadastro', required=False, help_text='Marque essa opção caso deseje que o aluno atualize seus dados cadastrais no ato do pedido de matrícula.',
    )
    requer_atualizacao_caracterizacao = forms.BooleanField(
        label='Requer atualização da caracterização social', required=False, help_text='Marque essa opção caso deseje que o aluno atualize seus dados da caracterização social no ato do pedido de matrícula.',
    )

    permite_cancelamento_matricula_diario = forms.BooleanField(
        label='Permite o cancelamento de matrículas em diário já deferidas', required=False, help_text='Marque essa opção caso o aluno possa solicitar o cancelamento de matrículas em diários nos quais ele já se encontra matriculado.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.NOTA_DECIMAL:
            self.fields['permite_cancelamento_matricula_diario'].widget = forms.HiddenInput()

    def clean_data_fim(self):
        if 'data_inicio' in self.cleaned_data and 'data_fim' in self.cleaned_data:
            if self.cleaned_data['data_fim'] < self.cleaned_data['data_inicio']:
                raise ValidationError('A data de fim deve ser maior que a data de início.')
        return self.cleaned_data['data_fim']

    def processar(self, configuracao_pedido_matricula):
        configuracao_pedido_matricula.replicar(
            self.cleaned_data['descricao'],
            self.cleaned_data['data_inicio'],
            self.cleaned_data['data_fim'],
            self.cleaned_data['impedir_troca_turma'],
            self.cleaned_data['restringir_por_curso'],
            self.cleaned_data['requer_atualizacao_dados'],
            self.cleaned_data['requer_atualizacao_caracterizacao'],
            self.cleaned_data['permite_cancelamento_matricula_diario']
        )
        return configuracao_pedido_matricula


class ReplicacaoHorarioCampusForm(forms.FormPlus):
    SUBMIT_LABEL = 'Replicar Horário'
    descricao = forms.CharFieldPlus(width=500, label='Descrição', required=True)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.campi().all(), label='Campus', required=True, help_text='Informe o campus para o qual você deseja replicar o curso')

    def processar(self, horario_campus):
        horario_campus.replicar(self.cleaned_data['descricao'], self.cleaned_data['uo'])
        return horario_campus


class ReplicacaoMatrizForm(forms.FormPlus):
    SUBMIT_LABEL = 'Replicar Matriz'
    descricao = forms.CharFieldPlus(width=500, label='Descrição', required=True)

    def __init__(self, matriz, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matriz = matriz
        self.fields['descricao'].initial = f'{self.matriz.descricao} [REPLICADO]'

    def processar(self):
        self.matriz.replicar(self.cleaned_data['descricao'])
        return self.matriz


class ReplicacaoConfiguracaoAvaliacaoForm(forms.FormPlus):
    SUBMIT_LABEL = 'Replicar Configuração de Avaliação'
    descricao = forms.CharFieldPlus(width=500, label='Descrição', required=True)

    def __init__(self, configuracao_avaliacao, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configuracao_avaliacao = configuracao_avaliacao
        self.fields['descricao'].initial = f'{self.configuracao_avaliacao.descricao} [REPLICADO]'

    def processar(self):
        self.configuracao_avaliacao.replicar(self.cleaned_data['descricao'])
        return self.configuracao_avaliacao


class MatriculaForm(forms.FormPlus):
    numero = forms.CharField(label='Matrícula Nº')


class ComponenteCurricularForm(forms.ModelFormPlus):
    periodo_letivo = forms.ChoiceField(required=False)
    matriz = forms.ModelChoiceField(queryset=Matriz.objects, widget=forms.HiddenInput())
    componente = forms.ModelChoiceFieldPlus(Componente.objects)
    componente_curricular_associado = forms.ModelChoiceField(
        queryset=ComponenteCurricular.objects,
        widget=AutocompleteWidget(search_fields=ComponenteCurricular.SEARCH_FIELDS),
        label='Componente Associado',
        required=False,
        help_text='Caso a nota desse componente não precise ser lançada no sistema em virtude de estar associado a um outro, informe aqui o componente cuja nota será registrada através de um diário, aproveitamento de estudo ou certificação do conhecimento.',
    )

    SUBMIT_LABEL = 'Vincular Componente'
    EXTRA_BUTTONS = [dict(name='continuar', value='Vincular Componente e continuar vinculando')]

    class Meta:
        model = ComponenteCurricular
        exclude = ()

    class Media:
        js = ('/static/edu/js/ComponenteCurricularForm.js',)

    def __init__(self, matriz, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matriz = matriz
        self.fields['componente'].queryset = self.fields['componente'].queryset.filter(nivel_ensino=self.matriz.nivel_ensino)
        self.fields['pre_requisitos'].queryset = self.fields['pre_requisitos'].queryset.filter(matriz=self.matriz)
        self.fields['periodo_letivo'].choices = [['', '-----']] + [[x, x] for x in range(1, self.matriz.qtd_periodos_letivos + 1)]
        self.fields['componente_curricular_associado'].queryset = self.fields['componente_curricular_associado'].queryset.filter(matriz=self.matriz)
        self.fields['matriz'].initial = self.matriz.pk
        self.fields['ch_pratica'].initial = 0
        if not ClassificacaoComplementarComponenteCurricular.objects.exists():
            self.fields['classificacao_complementar'].widget = forms.HiddenInput()
        if matriz.estrutura.tipo_avaliacao != EstruturaCurso.TIPO_AVALIACAO_MODULAR:
            self.fields['tipo_modulo'].widget = forms.HiddenInput()

    def clean_periodo_letivo(self):
        if self.cleaned_data.get('periodo_letivo') and self.data.get('optativo'):
            raise forms.ValidationError('Componentes Optativos não devem possuir um período letivo.')
        if not self.cleaned_data.get('periodo_letivo') and not self.data.get('optativo'):
            raise forms.ValidationError('Componentes Obrigatórios devem possuir um período letivo.')
        return self.cleaned_data['periodo_letivo'] or None

    fieldsets = (
        (
            'Dados Gerais',
            {
                'fields': (
                    'matriz',
                    'componente',
                    'classificacao_complementar',
                    ('optativo', 'pode_fechar_pendencia'),
                    ('periodo_letivo', 'tipo'),
                    ('qtd_avaliacoes', 'nucleo'),
                    ('avaliacao_por_conceito', 'is_dinamico', 'segundo_semestre'),
                )
            },
        ),
        ('Estágio Docente', {'fields': ('is_seminario_estagio_docente', 'tipo_estagio_docente')}),
        ('Carga Horária', {'fields': (('ch_presencial', 'ch_pratica'), ('ch_pcc', 'ch_visita_tecnica'), 'ch_extensao')}),
        ('Aula à Distância (EAD)', {'fields': ('percentual_maximo_ead',)}),
        ('Regime Modular', {'fields': ('tipo_modulo',)}),
        ('Associação', {'fields': ('componente_curricular_associado',)}),
        ('Plano de Ensino', {'fields': ('ementa',)}),
    )

    def clean_ch_extensao(self):
        if self.cleaned_data.get('tipo') == ComponenteCurricular.TIPO_ATIVIDADE_EXTENSAO and not self.matriz.ch_atividades_extensao:
            raise forms.ValidationError('Só é possível vincular componente de atividade de extensão em matrizes que requer carga horária desse tipo de componente.')
        return self.cleaned_data['ch_extensao']

    def clean_componente(self):
        if ComponenteCurricular.objects.filter(matriz=self.matriz, componente=self.cleaned_data['componente']).exists() and not self.instance.pk:
            raise forms.ValidationError('Componente já vinculado a esta matriz.')
        return self.cleaned_data['componente']

    def clean_componente_curricular_associado(self):
        cc_associado = self.cleaned_data['componente_curricular_associado']
        if self.instance.pk and cc_associado:
            if self.instance.pk == cc_associado.id:
                raise forms.ValidationError('Não é permitido associar um Componente Curricular a si mesmo.')
            if Diario.objects.filter(turma__matriz=self.matriz, componente_curricular=cc_associado).exists():
                raise forms.ValidationError('Não é possível associar componente, pois ele já está vinculado a um ou mais diários desta matriz.')
        return cc_associado

    def clean_tipo(self):
        if self.cleaned_data['tipo'] == ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL and self.cleaned_data['matriz'].ch_pratica_profissional <= 0:
            raise forms.ValidationError('Não foi possível vincular o componente, pois na matriz não foi informada a carga horária de prática profissional.')
        return self.cleaned_data['tipo']

    def clean_tipo_modulo(self):
        if self.cleaned_data['matriz'].estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_MODULAR and not self.cleaned_data['tipo_modulo']:
            raise forms.ValidationError('Este campo é obrigatório quando a estrutura de curso da matriz é modular.')
        return self.cleaned_data['tipo_modulo']

    def clean(self):
        if self.instance.pk:
            cc_salvo = ComponenteCurricular.objects.get(pk=self.instance.pk)
            periodo_letivo = self.cleaned_data.get('periodo_letivo')
            if periodo_letivo and int(periodo_letivo) != cc_salvo.periodo_letivo and (cc_salvo.co_requisitos.all() or cc_salvo.pre_requisitos.all()):
                raise forms.ValidationError('Não é possível alterar o período do componente na matriz, pois ele possui pré/co-requisitos.')
        if self.cleaned_data.get('segundo_semestre') and self.cleaned_data.get('qtd_avaliacoes') != 2:
            raise forms.ValidationError('Componentes semestrais devem ter apenas 2 avaliações.')

        return self.cleaned_data


class RequisitosComponenteCurricularForm(forms.ModelForm):
    SUBMIT_LABEL = 'Salvar'

    pre_requisitos = forms.MultipleModelChoiceField(ComponenteCurricular.objects, required=False, label='', widget=RenderableSelectMultiple('widgets/componentes_widget.html'))
    co_requisitos = forms.MultipleModelChoiceField(ComponenteCurricular.objects, required=False, label='', widget=RenderableSelectMultiple('widgets/componentes_widget.html'))
    componente_curricular_associado = forms.ModelChoiceField(
        queryset=ComponenteCurricular.objects,
        widget=AutocompleteWidget(search_fields=ComponenteCurricular.SEARCH_FIELDS),
        label='Componente Associado',
        required=False,
        help_text='Caso a nota desse componente não precise ser lançada no sistema em virtude de estar associado a um outro, informe aqui o componente cuja nota será registrada através de um diário, aproveitamento de estudo ou certificação do conhecimento.',
    )

    class Meta:
        model = ComponenteCurricular
        fields = ('pre_requisitos', 'co_requisitos', 'componente_curricular_associado')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.periodo_letivo:
            self.fields['pre_requisitos'].queryset = ComponenteCurricular.objects.filter(periodo_letivo__lt=self.instance.periodo_letivo, matriz=self.instance.matriz)
            self.fields['co_requisitos'].queryset = ComponenteCurricular.objects.filter(periodo_letivo__lte=self.instance.periodo_letivo, matriz=self.instance.matriz).exclude(
                id=self.instance.id
            )
        else:
            qs = ComponenteCurricular.objects.filter(matriz=self.instance.matriz).exclude(id=self.instance.id)
            self.fields['pre_requisitos'].queryset = qs
            self.fields['co_requisitos'].queryset = qs

        self.fields['componente_curricular_associado'].queryset = self.fields['componente_curricular_associado'].queryset.filter(matriz=self.instance.matriz)

    fieldsets = (
        ('Pré-requisitos', {'fields': (('pre_requisitos'),)}),
        ('Co-requisitos', {'fields': (('co_requisitos'),)}),
        ('Componente Associado', {'fields': (('componente_curricular_associado'),)}),
    )


class DiretoriaForm(forms.ModelFormPlus):
    setor = forms.ModelChoiceFieldPlus(Setor.objects)

    class Meta:
        model = Diretoria
        exclude = ()
        fields = ('setor', 'ead', 'tipo')

    fieldsets = (
        ('Dados Gerais', {'fields': (('setor', 'tipo'), 'ead')}),
        ('Nomenclatura para Diploma', {'fields': (
            ('titulo_autoridade_maxima_masculino', 'titulo_autoridade_maxima_feminino'),
            ('titulo_autoridade_uo_masculino', 'titulo_autoridade_uo_feminino'),
            ('titulo_autoridade_diretoria_masculino', 'titulo_autoridade_diretoria_feminino'),
        )}),
    )


class ProfessorDiarioForm(forms.ModelFormPlus):
    diario = forms.ModelChoiceField(queryset=Diario.objects, widget=forms.HiddenInput())
    vinculo = forms.ModelChoiceField(queryset=Vinculo.objects, label='Professor', required=True, widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS))
    periodo_letivo_ch = forms.ChoiceField(label='Período Letivo da Carga Horária', required=False, help_text='Informar caso o percentual da carga horária ministrada se refira a apenas um período letivo.', choices=[[None, 'Ambos']] + PERIODO_LETIVO_CHOICES)

    class Meta:
        model = ProfessorDiario
        exclude = ('professor',)

    fieldsets = (('', {'fields': ('diario', 'vinculo', ('tipo', 'ativo'), 'financiamento_externo')}), ('Carga Horária', {'fields': (('percentual_ch', 'periodo_letivo_ch'),)}))

    def __init__(self, diario, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs_prestadores = Vinculo.objects.prestadores().filter(pessoa__excluido=False, professor__isnull=False)
        qs_docentes = Vinculo.objects.servidores().filter(id_relacionamento__in=Servidor.objects.filter(eh_docente=True).values_list('id', flat=True))
        qs_tecnicos = Vinculo.objects.servidores().filter(id_relacionamento__in=Servidor.objects.filter(eh_tecnico_administrativo=True).values_list('id', flat=True))
        if self.instance.pk:
            qs_docentes = qs_docentes.filter(pessoa__excluido=False) | qs_docentes.filter(
                pessoa__excluido=True, pk__in=self.instance.diario.professordiario_set.values_list('professor__vinculo__id', flat=True)
            )
            qs_tecnicos = qs_tecnicos.filter(pessoa__excluido=False) | qs_tecnicos.filter(
                pessoa__excluido=True, pk__in=self.instance.diario.professordiario_set.values_list('professor__vinculo__id', flat=True)
            )
        else:
            qs_docentes = qs_docentes.filter(pessoa__excluido=False)
            qs_tecnicos = qs_tecnicos.filter(pessoa__excluido=False)
        self.fields['vinculo'].queryset = (qs_docentes | qs_tecnicos | qs_prestadores).distinct()
        self.fields['diario'].queryset = Diario.locals.all()

        if self.instance.pk:
            self.fields['vinculo'].initial = self.instance.professor.vinculo.pk

        is_administrador = in_group(self.request.user, 'Administrador Acadêmico')
        if not is_administrador:
            self.fields['ativo'].widget = forms.HiddenInput()

        self.diario = diario
        if self.diario:
            self.fields['diario'].initial = self.diario.pk

        if self.diario.componente_curricular:
            qtd_avaliacoes = self.diario.componente_curricular.qtd_avaliacoes
            descricao_etapa_1 = 'Terceira Etapa' if self.diario.is_semestral_segundo_semestre() else 'Primeira Etapa'
            self.fieldsets += ((descricao_etapa_1, {'fields': (('data_inicio_etapa_1', 'data_fim_etapa_1'),)}),)
            self.fields['data_inicio_etapa_1'].initial = self.diario.get_inicio_etapa_1()
            self.fields['data_fim_etapa_1'].initial = self.flexibilizar_data(self.diario.get_fim_etapa_1())

            if qtd_avaliacoes >= 2:
                descricao_etapa_2 = 'Quarta Etapa' if self.diario.is_semestral_segundo_semestre() else 'Segunda Etapa'
                self.fieldsets += ((descricao_etapa_2, {'fields': (('data_inicio_etapa_2', 'data_fim_etapa_2'),)}),)
                self.fields['data_inicio_etapa_2'].initial = self.diario.get_inicio_etapa_2()
                self.fields['data_fim_etapa_2'].initial = self.flexibilizar_data(self.diario.get_fim_etapa_2())

            if qtd_avaliacoes >= 4:
                self.fieldsets += (('Terceira Etapa', {'fields': (('data_inicio_etapa_3', 'data_fim_etapa_3'),)}),)
                self.fieldsets += (('Quarta Etapa', {'fields': (('data_inicio_etapa_4', 'data_fim_etapa_4'),)}),)
                self.fields['data_inicio_etapa_3'].initial = self.diario.get_inicio_etapa_3()
                self.fields['data_fim_etapa_3'].initial = self.flexibilizar_data(self.diario.get_fim_etapa_3())
                self.fields['data_inicio_etapa_4'].initial = self.diario.get_inicio_etapa_4()
                self.fields['data_fim_etapa_4'].initial = self.flexibilizar_data(self.diario.get_fim_etapa_4())

            if qtd_avaliacoes > 0:
                self.fieldsets += (('Etapa Final', {'fields': (('data_inicio_etapa_final', 'data_fim_etapa_final'),)}),)
                self.fields['data_inicio_etapa_final'].initial = self.diario.get_inicio_etapa_final()
                self.fields['data_fim_etapa_final'].initial = self.flexibilizar_data(self.diario.get_fim_etapa_final())
        for field_name in self.fields:
            if 'data_' in field_name:
                self.fields[field_name].help_text = ''

    def flexibilizar_data(self, data):
        if not data:
            return None
        return somar_data(data, 7)

    def save(self, *args, **kwargs):
        vinculo = self.cleaned_data['vinculo']
        obj = super().save(False)
        qs = Professor.objects.filter(vinculo__id=vinculo.pk)
        if qs.exists():
            obj.professor = qs[0]
        else:
            professor = Professor()
            professor.vinculo = vinculo
            professor.save()
            obj.professor = professor
            Group.objects.get(name='Professor').user_set.add(professor.vinculo.user)
        obj.save()

    def clean_percentual_ch(self):
        if self.cleaned_data.get('percentual_ch') > 100:
            raise forms.ValidationError('O percentual de CH ministrada não pode ser maior que 100%.')
        return self.cleaned_data.get('percentual_ch')

    def clean_vinculo(self):
        qs = self.diario.professordiario_set
        if self.instance.id:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists() and self.cleaned_data.get('vinculo').id in qs.values_list('professor__vinculo__id', flat=True):
            raise forms.ValidationError('Professor já cadastrado neste diário.')
        return self.cleaned_data.get('vinculo')

    def clean(self):
        if self.cleaned_data.get('vinculo') and self.instance.is_rit_publicado(self.cleaned_data.get('vinculo'), self.diario, self.cleaned_data.get('periodo_letivo_ch'), self.cleaned_data.get('financiamento_externo')):
            raise forms.ValidationError('Não é possível alterar o vínculo de um professor com RIT publicado no período letivo deste diário.')

        data_inicio_etapa_1 = self.cleaned_data.get('data_inicio_etapa_1')
        data_fim_etapa_1 = self.cleaned_data.get('data_fim_etapa_1')
        # verificando se a data de início da etapa 1 é maior que a data de encerramento da mesma etapa
        if data_inicio_etapa_1 and data_fim_etapa_1 and data_inicio_etapa_1 > data_fim_etapa_1:
            raise forms.ValidationError('A data de início da etapa 1 não pode ser maior que a data de encerramento da mesma etapa.')
        # verificando se o usuário preencheu a data de inicio da etapa 1 e não preencheu a data de encerramento da mesma etapa
        if data_inicio_etapa_1 and not data_fim_etapa_1:
            raise forms.ValidationError('Favor preencher a data de encerramento da etapa 1.')
        # verificando se o usuário preencheu a data de encerramento da etapa 1 e não preencheu a data inicio da mesma etapa
        if data_fim_etapa_1 and not data_inicio_etapa_1:
            raise forms.ValidationError('Favor preencher a data de início da etapa 1.')

        data_inicio_etapa_2 = self.cleaned_data.get('data_inicio_etapa_2')
        data_fim_etapa_2 = self.cleaned_data.get('data_fim_etapa_2')
        # verificando se a data de início da etapa 2 é maior que a data de encerramento da mesma etapa
        if data_inicio_etapa_2 and data_fim_etapa_2 and data_inicio_etapa_2 > data_fim_etapa_2:
            raise forms.ValidationError('A data de início da etapa 2 não pode ser maior que a data de encerramento da mesma etapa.')
        # verificando se o usuário preencheu a data de inicio da etapa 2 e não preencheu a data de encerramento da mesma etapa
        if data_inicio_etapa_2 and not data_fim_etapa_2:
            raise forms.ValidationError('Favor preencher a data de encerramento da etapa 2.')
        # verificando se o usuário preencheu a data de encerramento da etapa 2 e não preencheu a data inicio da mesma etapa
        if data_fim_etapa_2 and not data_inicio_etapa_2:
            raise forms.ValidationError('Favor preencher a data de início da etapa 2.')

        data_inicio_etapa_3 = self.cleaned_data.get('data_inicio_etapa_3')
        data_fim_etapa_3 = self.cleaned_data.get('data_fim_etapa_3')
        # verificando se a data de início da etapa 3 é maior que a data de encerramento da mesma etapa
        if data_inicio_etapa_3 and data_fim_etapa_3 and data_inicio_etapa_3 > data_fim_etapa_3:
            raise forms.ValidationError('A data de início da etapa 3 não pode ser maior que a data de encerramento da mesma etapa.')
        # verificando se o usuário preencheu a data de inicio da etapa 3 e não preencheu a data de encerramento da mesma etapa
        if data_inicio_etapa_3 and not data_fim_etapa_3:
            raise forms.ValidationError('Favor preencher a data de encerramento da etapa 3.')
        # verificando se o usuário preencheu a data de encerramento da etapa 3 e não preencheu a data inicio da mesma etapa
        if data_fim_etapa_3 and not data_inicio_etapa_3:
            raise forms.ValidationError('Favor preencher a data de início da etapa 3.')

        data_inicio_etapa_4 = self.cleaned_data.get('data_inicio_etapa_4')
        data_fim_etapa_4 = self.cleaned_data.get('data_fim_etapa_4')
        # verificando se a data de início da etapa 4 é maior que a data de encerramento da mesma etapa
        if data_inicio_etapa_4 and data_fim_etapa_4 and data_inicio_etapa_4 > data_fim_etapa_4:
            raise forms.ValidationError('A data de início da etapa 4 não pode ser maior que a data de encerramento da mesma etapa.')
        # verificando se o usuário preencheu a data de inicio da etapa 4 e não preencheu a data de encerramento da mesma etapa
        if data_inicio_etapa_4 and not data_fim_etapa_4:
            raise forms.ValidationError('Favor preencher a data de encerramento da etapa 4.')
        # verificando se o usuário preencheu a data de encerramento da etapa 4 e não preencheu a data inicio da mesma etapa
        if data_fim_etapa_4 and not data_inicio_etapa_4:
            raise forms.ValidationError('Favor preencher a data de início da etapa 4.')

        data_inicio_etapa_final = self.cleaned_data.get('data_inicio_etapa_final')
        data_fim_etapa_final = self.cleaned_data.get('data_fim_etapa_final')
        # verificando se a data de início da etapa final é maior que a data de encerramento da mesma etapa
        if data_inicio_etapa_final and data_fim_etapa_final and data_inicio_etapa_final > data_fim_etapa_final:
            raise forms.ValidationError('A data de início da etapa final não pode ser maior que a data de encerramento da mesma etapa.')
        # verificando se o usuário preencheu a data de inicio da etapa final e não preencheu a data de encerramento da mesma etapa
        if data_inicio_etapa_final and not data_fim_etapa_final:
            raise forms.ValidationError('Favor preencher a data de encerramento da etapa final.')
        # verificando se o usuário preencheu a data de encerramento da etapa final e não preencheu a data inicio da mesma etapa
        if data_fim_etapa_final and not data_inicio_etapa_final:
            raise forms.ValidationError('Favor preencher a data de início da etapa final.')
        # verificando choque de horário com outros diário no mesmo período letivo
        if settings.IMPEDIR_CHOQUE_HORARIOS_PROFESSOR:
            diarios_choque_horario = self.instance.get_diarios_choque_horario()
            if diarios_choque_horario:
                raise forms.ValidationError('Não é possível adicionar esse professor ao diário, pois há choque de horário com o(s) diário(s): {}'.format(', '.join(str(id) for id in diarios_choque_horario)))
        return self.cleaned_data

    def clean_periodo_letivo_ch(self):
        return self.cleaned_data.get('periodo_letivo_ch') or None


class MatrizCursoForm(forms.ModelFormPlus):
    curso_campus = forms.ModelChoiceField(queryset=CursoCampus.objects, widget=forms.HiddenInput())
    matriz = forms.ModelChoiceField(queryset=Matriz.objects, widget=AutocompleteWidget(search_fields=Matriz.SEARCH_FIELDS), label='Matriz', required=True)

    class Meta:
        model = MatrizCurso
        exclude = ()

    fieldsets = (
        ('Dados Gerais', {'fields': ('curso_campus', 'matriz')}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso_campus'].queryset = CursoCampus.locals.all()

    def clean_matriz(self):
        if MatrizCurso.locals.exclude(pk=self.instance.pk or 0).filter(matriz=self.cleaned_data['matriz'], curso_campus=self.cleaned_data['curso_campus']).exists():
            raise forms.ValidationError('Par matriz/curso já cadastrado.')
        else:
            return self.cleaned_data['matriz']


class TurmaForm(forms.ModelFormPlus):
    codigo = forms.CharField(label='Código', widget=forms.TextInput(attrs=dict(readonly='readonly')))
    descricao = forms.CharField(label='Descrição', widget=forms.Textarea(attrs=dict(readonly='readonly')))
    sigla = forms.CharFieldPlus(label='Sigla', required=False)
    calendario_academico = forms.ModelChoiceField(queryset=CalendarioAcademico.locals, label='Calendário Acadêmico', required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance.calendario_academico, 'uo'):
            self.fields['calendario_academico'].queryset = CalendarioAcademico.objects.filter(
                uo=self.instance.calendario_academico.uo, ano_letivo=self.instance.ano_letivo, periodo_letivo=self.instance.periodo_letivo
            )
            if self.instance.turno.pk != Turno.EAD:
                self.fields['polo'].widget = forms.Select(attrs=dict(readonly='readonly'))

    @transaction.atomic()
    def save(self, *args, **kwargs):
        turma = super().save(*args, **kwargs)
        for diario in turma.diario_set.all():
            if diario.quantidade_vagas != turma.quantidade_vagas:
                diario.quantidade_vagas = turma.quantidade_vagas
                diario.save()
        return turma

    class Meta:
        model = Turma
        exclude = ('ano_letivo', 'periodo_letivo', 'periodo_matriz', 'turno', 'curso_campus', 'matriz', 'sequencial',)


class TransferirTurmaForm(FormWizardPlus):
    METHOD = 'POST'
    LAST_SUBMIT_LABEL = 'Transferir Alunos Selecionados'
    turma_destino = forms.ModelChoiceFieldPlus(None, label='Turma de Destino', widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS))
    confirmacao = forms.BooleanField(label='Confirmação', required=False, help_text='Marque a opção acima e clique no botão "Finalizar".')

    steps = ([('Turma de Destino', {'fields': ('turma_destino',)})], [('Confirmação dos Dados', {'fields': ('confirmacao',)})])

    def __init__(self, turma_origem, *args, **kwargs):
        self.turma_origem = turma_origem
        super().__init__(*args, **kwargs)

    def first_step(self):
        self.fields['turma_destino'].queryset = Turma.locals.get_queryset().filter(curso_campus=self.turma_origem.curso_campus).exclude(pk=self.turma_origem.pk)


class TransferirDiarioForm(FormWizardPlus):
    METHOD = 'POST'
    LAST_SUBMIT_LABEL = 'Transferir Alunos Selecionados.'
    diario_destino = forms.ModelChoiceField(Diario.objects.none(), label='Diário de Destino', widget=forms.RadioSelect(), empty_label=None)
    confirmacao = forms.BooleanField(label='Confirmação', required=False, help_text='Marque a opção acima e clique no botão "Finalizar".')

    steps = ([('Diário de Destino', {'fields': ('diario_destino',)})], [('Confirmação dos Dados', {'fields': ('confirmacao',)})])

    def __init__(self, diario_origem, *args, **kwargs):
        self.diario_origem = diario_origem
        super().__init__(*args, **kwargs)

    def first_step(self):
        self.fields['diario_destino'].queryset = Diario.locals.filter(
            componente_curricular__componente=self.diario_origem.componente_curricular.componente,
            ano_letivo=self.diario_origem.ano_letivo,
            periodo_letivo=self.diario_origem.periodo_letivo,
        ).exclude(pk=self.diario_origem.pk)


class DiarioForm(forms.ModelFormPlus):
    class Meta:
        model = Diario
        exclude = (
            'turma',
            'componente_curricular',
            'ano_letivo',
            'periodo_letivo',
            'situacao',
            'horario_campus',
            'turno',
            'estrutura_curso',
            'calendario_academico',
            'local_aula',
            'locais_aula_secundarios',
            'posse_etapa_1',
            'posse_etapa_2',
            'posse_etapa_3',
            'posse_etapa_4',
            'posse_etapa_5',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.componente_curricular and not self.instance.componente_curricular.is_dinamico:
            self.fields['descricao_dinamica'].widget = forms.HiddenInput()

    def clean_segundo_semestre(self):
        segundo_semestre = self.cleaned_data['segundo_semestre']
        if segundo_semestre and self.instance.turma.curso_campus.periodicidade == CursoCampus.PERIODICIDADE_ANUAL \
                and self.instance.componente_curricular.qtd_avaliacoes != 2:
            raise forms.ValidationError(
                'Somente diário com duas etapas de um curso de periodicidade anual pode ser marcado como de Segundo Semestre'
            )
        return segundo_semestre


class ComponenteForm(forms.ModelFormPlus):
    class Meta:
        model = Componente
        exclude = ('sigla',)

    class Media:
        js = ('/static/edu/js/ComponenteForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        situacoes = [SituacaoMatricula.FORMADO, SituacaoMatricula.CONCLUIDO]
        qs_componente_curricular = ComponenteCurricular.objects.filter(componente=self.instance)
        # desabilita a edição da carga horária caso já exista algum aluno formado
        md = MatriculaDiario.objects.filter(matricula_periodo__aluno__situacao__in=situacoes).filter(diario__componente_curricular__componente=self.instance).exists()
        mdr = MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno__situacao__in=situacoes).filter(equivalencia_componente__componente=self.instance).exists()
        cc = CertificacaoConhecimento.objects.filter(matricula_periodo__aluno__situacao__in=situacoes).filter(componente_curricular__componente=self.instance).exists()
        ae = AproveitamentoEstudo.objects.filter(matricula_periodo__aluno__situacao__in=situacoes).filter(componente_curricular__componente=self.instance).exists()
        ac = AproveitamentoComponente.objects.filter(matricula_periodo__aluno__situacao__in=situacoes).filter(componente_curricular__componente=self.instance).exists()
        rh = RegistroHistorico.objects.filter(matricula_periodo__aluno__situacao__in=situacoes).filter(componente=self.instance).exists()
        if self.instance.pk and (md or mdr or cc or ae or ac or rh):
            self.fields['ch_hora_relogio'].widget.attrs.update(readonly='readonly')
            self.fields['ch_hora_relogio'].help_text = 'Impossível editar este campo. Componente já vinculado a uma matriz com aluno formado.'
            self.fields['ch_hora_aula'].widget.attrs.update(readonly='readonly')
            self.fields['ch_hora_aula'].help_text = 'Impossível editar este campo. Componente já vinculado a uma matriz com aluno formado.'
            self.fields['ch_qtd_creditos'].widget.attrs.update(readonly='readonly')
            self.fields['ch_qtd_creditos'].help_text = 'Impossível editar este campo. Componente já vinculado a uma matriz com aluno formado.'
        else:
            self.fields[
                'ch_hora_relogio'
            ].help_text = 'Esta carga horária não pode ser 0 e não poderá ser editada caso este componente já esteja vinculado a uma matriz que possua um aluno formado.'
            self.fields[
                'ch_hora_aula'
            ].help_text = 'Esta carga horária não pode ser 0 e não poderá ser editada caso este componente já esteja vinculado a uma matriz que possua um aluno formado.'

            if qs_componente_curricular.filter(ch_pratica__gt=0).exists():
                self.fields['ch_hora_relogio'].help_text = mark_safe(
                    '<strong>Atenção! Este componente já está vinculado com carga horária prática a uma matriz. Não será possível atualizar automaticamente os campos Carga Horária Teórica e Prática do componente na matriz.</strong><br/>{}'.format(
                        self.fields['ch_hora_relogio'].help_text
                    )
                )

        if not self.instance.pk:
            qs_diretoria = Diretoria.objects.filter(setor__sigla=Configuracao.get_valor_por_chave('comum', 'reitoria_sigla'))
            if qs_diretoria.exists():
                self.fields['diretoria'].initial = qs_diretoria[0].id

    def save(self, *args, **kwargs):
        componente = super().save(*args, **kwargs)
        ComponenteCurricular.objects.filter(componente=componente, ch_pratica=0).update(ch_presencial=componente.ch_hora_relogio)
        return componente


class CursoCampusForm(forms.ModelFormPlus):
    titulo_certificado_masculino = forms.CharField(label='Masculino', required=True)
    titulo_certificado_feminino = forms.CharFieldPlus(label='Feminino', required=True)

    class Meta:
        model = CursoCampus
        exclude = ()

    class Media:
        js = ('/static/edu/js/CursoCampusForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['coordenador'].queryset = Funcionario.objects.filter(excluido=False)

    def clean_modalidade(self):
        modalidade = self.cleaned_data['modalidade']
        if 4 < modalidade.pk < 9:
            if 'eixo' not in self.data or not self.data['eixo']:
                raise forms.ValidationError('O campo "Eixo Tecnológico" é obrigatório para cursos tecnológicos e FIC.')
        elif modalidade.pk in [9, 10, 16]:
            if 'area_capes' not in self.data or not self.data['area_capes']:
                raise forms.ValidationError('O campo "Área Capes" é obrigatório para cursos de pós-graduação.')
        else:
            if 'area' not in self.data or not self.data['area']:
                raise forms.ValidationError('O campo "Área" é obrigatório para a modalidade selecionada.')
        return modalidade

    def clean_assinatura_eletronica(self):
        modalidade_id = int(self.data.get('modalidade', 0))
        assinatura_eletronica = self.cleaned_data['assinatura_eletronica']
        if assinatura_eletronica and modalidade_id and modalidade_id not in (Modalidade.FIC, Modalidade.INTEGRADO, Modalidade.INTEGRADO_EJA, Modalidade.SUBSEQUENTE, Modalidade.CONCOMITANTE, Modalidade.ESPECIALIZACAO, Modalidade.MESTRADO, Modalidade.DOUTORADO, Modalidade.APERFEICOAMENTO, Modalidade.PROEJA_FIC_FUNDAMENTAL):
            raise forms.ValidationError('Apenas cursos FIC, técnicos e de pós-graduação podem ter certificados assinados eletronicamente')
        return assinatura_eletronica

    def save(self, *args, **kwargs):
        curso_campus = super().save(*args, **kwargs)
        if curso_campus.coordenador:
            user = User.objects.get(username=curso_campus.coordenador.username)
            group = Group.objects.get(name='Coordenador de Curso')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(user=user, group=group)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=curso_campus.diretoria.setor)
        return curso_campus


class AulaForm(forms.ModelFormPlus):
    professor_diario = forms.ModelChoiceField(queryset=ProfessorDiario.objects, label='Professor', required=True)
    conteudo = forms.CharField(label='Conteúdo', widget=TextareaCloneWidget())
    url = forms.CharField(label='URL', required=False, help_text='Link disponbilizado na turma virtual para os alunos caso a transmissão seja realizada através de alguma plataforma multi-media ou streaming')
    outros_professor_diario = forms.MultipleModelChoiceField(ProfessorDiario.objects, label='Outros Professores', required=False, help_text="A CH desta aula será compartilhada com os professores selecionados")

    class Meta:
        model = Aula
        exclude = ()

    fieldsets = (('Dados da Aula', {'fields': ('professor_diario', ('quantidade', 'tipo'), ('etapa', 'data'), 'conteudo', 'ead', 'url', 'outros_professor_diario')}),)

    def __init__(self, diario, etapa, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.diario = diario
        self.etapa = etapa

        outros_professores_qs = self.diario.professordiario_set.exclude(professor__vinculo__user=self.request.user)
        if outros_professores_qs.exists():
            self.fields['outros_professor_diario'].queryset = outros_professores_qs
            self.fields['outros_professor_diario'].label_from_instance = lambda obj: f'{obj.professor}'
        else:
            del(self.fields['outros_professor_diario'])

        if hasattr(self.instance, 'outros_professor_diario') and self.instance.outros_professor_diario.exists():
            self.initial['outros_professor_diario'] = list(self.instance.outros_professor_diario.values_list('id', flat=True))

        professor_qs = self.diario.professordiario_set.filter(professor__vinculo__user=self.request.user)
        professor_diario = None
        if professor_qs.exists():
            professor_diario = professor_qs[0]
            self.fields['professor_diario'].queryset = professor_qs
        else:
            qs = diario.professordiario_set.all()
            self.fields['professor_diario'].queryset = qs
            if qs.count() == 1:
                professor_diario = qs[0]

        if self.fields['professor_diario'].queryset.count() == 1:
            self.fields['professor_diario'].widget = forms.HiddenInput()
        else:
            self.fields['professor_diario'].label_from_instance = lambda obj: f'{obj.professor}'

        if self.diario.componente_curricular.qtd_avaliacoes == 1:
            if self.diario.is_semestral_segundo_semestre():
                self.fields['etapa'].choices = Aula.ETAPA_CHOICES_SEGUNGO_SEMESTRE[0:1] + Aula.ETAPA_CHOICES[4:5]
            else:
                self.fields['etapa'].choices = Aula.ETAPA_CHOICES[0:1] + Aula.ETAPA_CHOICES[4:5]
        elif self.diario.componente_curricular.qtd_avaliacoes == 2:
            if self.diario.is_semestral_segundo_semestre():
                self.fields['etapa'].choices = Aula.ETAPA_CHOICES_SEGUNGO_SEMESTRE + Aula.ETAPA_CHOICES[4:5]
            else:
                self.fields['etapa'].choices = Aula.ETAPA_CHOICES[0:2] + Aula.ETAPA_CHOICES[4:5]
        if not self.instance.data:
            self.fields['data'].initial = datetime.date.today()
        if not self.instance.pk:
            self.fields['etapa'].initial = etapa

        if professor_diario:
            self.fields['professor_diario'].initial = professor_diario.pk
            lista = []
            for diario in Diario.objects.filter(
                professordiario__professor=professor_diario.professor, componente_curricular=professor_diario.diario.componente_curricular
            ).order_by('-id')[0:3]:
                qs = Aula.objects.filter(professor_diario__professor=professor_diario.professor, professor_diario__diario=diario)
                if qs.exists():
                    lista.append(f'<strong>{diario}</strong>')
                for aula in qs:
                    lista.append('<div><strong>{}</strong> <p>{}</p></div>'.format(format_(aula.data), aula.conteudo.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')))

            if not lista:
                lista.append('<strong>Atenção</strong>: Nenhum registro de aula relacionado a esta disciplina foi encontrado.')
            self.fields['conteudo'].widget.clones = ''.join(lista)

        if diario.componente_curricular.matriz.estrutura.limitar_ch_por_tipo_aula:
            tipo_choices = [[Aula.AULA, 'Aula Teórica']]
            if diario.componente_curricular.ch_pratica:
                tipo_choices.append([Aula.PRATICA, 'Aula Prática'])
            if diario.componente_curricular.ch_extensao:
                tipo_choices.append([Aula.EXTENSAO, 'Atividade de Extensão'])
            if diario.componente_curricular.ch_pcc:
                tipo_choices.append([Aula.PRATICA_COMO_COMPONENTE_CURRICULAR, 'Prática como Componente Curricular'])
            if diario.componente_curricular.ch_visita_tecnica:
                tipo_choices.append([Aula.VISITA_TECNICA, 'Visita Técnica / Aula de Campo'])
            self.fields['tipo'].choices = tipo_choices
        else:
            self.fields['tipo'].widget = forms.HiddenInput()
            self.fields['tipo'].initial = Aula.AULA

        if diario.componente_curricular.percentual_maximo_ead == 0:
            self.fields['ead'].widget = forms.HiddenInput()

    def clean_ead(self):
        ead = self.cleaned_data.get('ead')
        quantidade = self.cleaned_data.get('quantidade')
        if self.diario.componente_curricular.percentual_maximo_ead:
            qtd_disponivel = self.diario.get_carga_horaria_ead_disponivel()
            if quantidade > qtd_disponivel:
                raise forms.ValidationError(f'A quantidade disponível de aula EAD para esse diário é de {qtd_disponivel} aula(s).')
        return ead

    def clean_data(self):
        data = self.cleaned_data['data']
        professor_diario = self.cleaned_data.get('professor_diario')
        if not professor_diario:
            return data
        if (
            professor_diario.diario.calendario_academico.data_inicio_espaco_pedagogico
            and professor_diario.diario.calendario_academico.data_fim_espaco_pedagogico
            and data >= professor_diario.diario.calendario_academico.data_inicio_espaco_pedagogico
            and data <= professor_diario.diario.calendario_academico.data_fim_espaco_pedagogico
        ):
            return data
        if (
            professor_diario.diario.calendario_academico.data_inicio_etapa_1
            and professor_diario.diario.calendario_academico.data_fim_etapa_1
            and data >= professor_diario.diario.calendario_academico.data_inicio_etapa_1
            and data <= professor_diario.diario.calendario_academico.data_fim_etapa_1
        ):
            return data
        if (
            professor_diario.diario.calendario_academico.data_inicio_etapa_2
            and professor_diario.diario.calendario_academico.data_fim_etapa_2
            and data >= professor_diario.diario.calendario_academico.data_inicio_etapa_2
            and data <= professor_diario.diario.calendario_academico.data_fim_etapa_2
        ):
            return data
        if (
            professor_diario.diario.calendario_academico.data_inicio_etapa_3
            and professor_diario.diario.calendario_academico.data_fim_etapa_3
            and data >= professor_diario.diario.calendario_academico.data_inicio_etapa_3
            and data <= professor_diario.diario.calendario_academico.data_fim_etapa_3
        ):
            return data
        if (
            professor_diario.diario.calendario_academico.data_inicio_etapa_4
            and professor_diario.diario.calendario_academico.data_fim_etapa_4
            and data >= professor_diario.diario.calendario_academico.data_inicio_etapa_4
            and data <= professor_diario.diario.calendario_academico.data_fim_etapa_4
        ):
            return data
        if (
            professor_diario.diario.get_inicio_etapa_final()
            and professor_diario.diario.get_fim_etapa_final()
            and data >= professor_diario.diario.get_inicio_etapa_final()
            and data <= professor_diario.diario.get_fim_etapa_final()
        ):
            return data
        if professor_diario.diario.componente_curricular.qtd_avaliacoes == 1 and professor_diario.diario.calendario_academico.qtd_etapas == 2:
            return data
        raise forms.ValidationError('A data não compreende o intervalo do calendário acadêmico.')

    def clean_outros_professor_diario(self):
        outros_professor_diario = self.cleaned_data['outros_professor_diario']
        professor_diario = self.cleaned_data.get('professor_diario')
        if professor_diario in outros_professor_diario:
            raise forms.ValidationError(f'O professor {professor_diario.professor} é o responsável pela aula e não pode ser selecionado para receber o compartilhamento da CH dessa aula.')
        return outros_professor_diario


class DefinirLocalAulaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Salvar'
    sala = forms.ModelChoiceFieldPlus(Sala.ativas, required=False)
    salas_secundarias = forms.MultipleModelChoiceFieldPlus(Sala.ativas, label='Salas Secundárias', required=False)

    def __init__(self, diario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diario = diario
        uo = diario.calendario_academico.uo
        self.fields['sala'].queryset = self.fields['sala'].queryset.filter(predio__uo=uo)
        self.fields['salas_secundarias'].queryset = self.fields['salas_secundarias'].queryset.filter(predio__uo=uo)
        self.initial['sala'] = diario.local_aula_id
        self.initial['salas_secundarias'] = diario.locais_aula_secundarios.values_list('id', flat=True)

    def processar(self):
        self.diario.local_aula = self.cleaned_data['sala']
        self.diario.locais_aula_secundarios.set(self.cleaned_data['salas_secundarias'])
        self.diario.save()


class DefinirLocalAulaTurmaForm(forms.FormPlus):
    sala = forms.ModelChoiceFieldPlus(Sala.ativas, required=False)
    todos_diarios = forms.BooleanField(
        label='Alterar já Definidos',
        help_text='Marque essa opção caso deseje que todos os diários dessa turma sejam alterados, incluse aqueles que já possuem sala definida.',
        required=False,
    )

    def __init__(self, turma, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turma = turma
        uo = turma.calendario_academico.uo
        self.fields['sala'].queryset = self.fields['sala'].queryset.filter(predio__uo=uo)

    def processar(self):
        qs_diarios = self.turma.diario_set.all()
        if not self.cleaned_data['todos_diarios']:
            qs_diarios = qs_diarios.filter(local_aula__isnull=True)
        qs_diarios.update(local_aula=self.cleaned_data['sala'])


class AlterarNotaForm(forms.FormPlus):
    nota = forms.IntegerFieldPlus(required=False, help_text='Valor entre 0 e 100')


def grupos():
    DIRETOR_GERAL = Group.objects.get_or_create(name='Diretor Geral')[0]
    DIRETOR = Group.objects.get_or_create(name='Diretor Acadêmico')[0]
    COORDENADOR = Group.objects.get_or_create(name='Coordenador de Curso')[0]
    SECRETARIO = Group.objects.get_or_create(name='Secretário Acadêmico')[0]
    PEDAGOGO = Group.objects.get_or_create(name='Pedagogo')[0]
    ESTAGIARIO = Group.objects.get_or_create(name='Estagiário')[0]
    AGENDADOR_AULA_CAMPO = Group.objects.get_or_create(name='Agendador de Aula de Campo EDU')[0]
    TUTOR_POLO = Group.objects.get_or_create(name='Tutor de Polo EAD')[0]
    COORDENADOR_POLO = Group.objects.get_or_create(name='Coordenador de Polo EAD')[0]
    COORDENADOR_REGISTROS_ACADEMICOS = Group.objects.get_or_create(name='Coordenador de Registros Acadêmicos')[0]
    COORDENADOR_ESTAGIO_DOCENTE = Group.objects.get_or_create(name='Coordenador de Estágio Docente')[0]
    COORDENADOR_MODALIDADE = Group.objects.get_or_create(name='Coordenador de Modalidade Acadêmica')[0]
    COORDENADOR_DESPORTO = Group.objects.get_or_create(name='Coordenador de Desporto')[0]
    ORGANIZADOR_FORMATURA = Group.objects.get_or_create(name='Organizador de Formatura')[0]
    BIBLIOTECARIO = Group.objects.get_or_create(name='Bibliotecário')[0]
    INTERESSADO_ETEP = Group.objects.get_or_create(name='Interessado ETEP')[0]
    return locals()


class AdicionarMembroDiretoriaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Salvar'
    funcionario = forms.ModelChoiceField(Funcionario.objects, required=True, label='Usuário', widget=AutocompleteWidget(search_fields=Funcionario.SEARCH_FIELDS))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['funcionario'].queryset = Funcionario.objects.filter(excluido=False)

    def processar(self, diretoria, grupo):
        funcionario = self.cleaned_data['funcionario']
        user = User.objects.get(username=funcionario.username)
        usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupo, user=user)[0]
        UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)

        if grupo.name == 'Diretor Geral':
            diretorias = Diretoria.objects.filter(setor__uo=diretoria.setor.uo)
            for diretoria in diretorias:
                if not diretoria.diretor_geral:
                    diretoria.diretor_geral = funcionario
                    diretoria.diretor_geral_exercicio = funcionario
                    diretoria.save()
                UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)
        if grupo.name == 'Diretor Acadêmico':
            if not diretoria.diretor_academico:
                diretoria.diretor_academico = funcionario
                diretoria.diretor_academico_exercicio = funcionario
                diretoria.save()


class AdicionarCoordenadorForm(forms.FormPlus):
    funcionario = forms.ModelChoiceField(Funcionario.objects, required=True, label='Usuário', widget=AutocompleteWidget(search_fields=Funcionario.SEARCH_FIELDS))
    cursos = forms.ModelMultipleChoiceField(CursoCampus.objects, required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        self.diretoria = kwargs.pop('diretoria', None)
        self.tipo_coordenador = kwargs.pop('tipo_coordenador', 'coordenador')
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['funcionario'].queryset = Funcionario.objects.filter(excluido=False)
        self.fields['cursos'].queryset = CursoCampus.objects.filter(ativo=True, diretoria=self.diretoria)
        if user:
            self.fields['funcionario'].initial = user.get_relacionamento().id
            if self.tipo_coordenador == 'coordenador':
                self.fields['cursos'].initial = list(user.get_relacionamento().cursocampus_set.filter(ativo=True, diretoria=self.diretoria).values_list('id', flat=True))
            else:
                self.fields['cursos'].initial = list(
                    user.get_relacionamento().cursocampus_vicecoordenador_set.filter(ativo=True, diretoria=self.diretoria).values_list('id', flat=True)
                )

    def processar(self, diretoria, usuario_grupo):
        funcionario = self.cleaned_data['funcionario']
        user = User.objects.get(username=funcionario.username)
        cursos = self.cleaned_data['cursos']
        if not usuario_grupo:
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR'], user=user)[0]
        usuario_grupo.user = user
        usuario_grupo.save()
        if self.tipo_coordenador == 'coordenador':
            usuario_grupo.user.get_relacionamento().cursocampus_set.filter(diretoria=self.diretoria).update(coordenador=None)
            for curso in cursos:
                curso.coordenador = funcionario
                curso.save()
        else:
            usuario_grupo.user.get_relacionamento().cursocampus_vicecoordenador_set.filter(diretoria=self.diretoria).update(coordenador_2=None)
            for curso in cursos:
                curso.coordenador_2 = funcionario
                curso.save()
        ugs = UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)[0]
        if (
            not cursos
            and not usuario_grupo.user.get_relacionamento().cursocampus_set.exists()
            and not usuario_grupo.user.get_relacionamento().cursocampus_vicecoordenador_set.filter(diretoria=self.diretoria).exists()
        ):
            ugs.delete()


class DefinirCoordenadorCursoForm(forms.ModelFormPlus):
    class Meta:
        model = CursoCampus
        fields = ('coordenador', 'numero_portaria_coordenador', 'coordenador_2', 'numero_portaria_coordenador_2')

    def processar(self, curso_campus):
        funcionario = self.cleaned_data['coordenador']
        if funcionario:
            user = User.objects.get(username=funcionario.username)
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR'], user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=curso_campus.diretoria.setor)[0]

        funcionario_2 = self.cleaned_data['coordenador_2']
        if funcionario_2:
            user_2 = User.objects.get(username=funcionario_2.username)
            usuario_grupo_2 = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR'], user=user_2)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo_2, setor=curso_campus.diretoria.setor)[0]

        self.save()


class EstruturaCursoForm(forms.ModelFormPlus):
    tipo_avaliacao = forms.ChoiceField(label='Tipo de Avaliação', widget=forms.RadioSelect(), choices=EstruturaCurso.TIPO_AVALIACAO_CHOICES)
    criterio_avaliacao = forms.ChoiceField(label='Critério de Avaliação', widget=forms.RadioSelect(), choices=EstruturaCurso.CRITERIO_AVALIACAO_CHOICES)
    ira = forms.ChoiceField(label='Forma de Cálculo', widget=forms.RadioSelect(), choices=EstruturaCurso.IRA_CHOICES)

    class Meta:
        model = EstruturaCurso
        exclude = ()

    class Media:
        js = ('/static/edu/js/EstruturaCursoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.numero_max_certificacoes is None:
            self.initial.update(numero_max_certificacoes=4)


class CalendarioAcademicoForm(forms.ModelFormPlus):
    qtd_etapas = forms.ChoiceField(widget=forms.RadioSelect(), choices=CalendarioAcademico.QTD_ETAPAS_CHOICES, initial=1)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus')
    diretoria = forms.ChainedModelChoiceField(Diretoria.objects.none(), label='Diretoria', obj_label='setor__sigla', form_filters=[('uo', 'setor__uo__id')], required=False)

    class Meta:
        model = CalendarioAcademico
        exclude = ()

    class Media:
        js = ('/static/edu/js/CalendarioAcademicoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals


class GerarTurmasForm(FormWizardPlus):
    METHOD = 'GET'
    QTD_TURMAS_CHOICES = [[0, '0'], [1, '1'], [2, '2'], [3, '3'], [4, '4'], [5, '5'], [6, '6'], [7, '7'], [8, '8'], [9, '9']]

    class Media:
        js = ('/static/edu/js/GerarTurmasForm.js',)

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', help_text='Formato: <strong>[2014]</strong>1.1.011004.1M')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES, help_text='Formato: 2014<strong>[1]</strong>.1.011004.1M')
    tipo_componente = forms.ChoiceField(label='Tipo dos Componentes', choices=[[1, 'Obrigatório'], [0, 'Optativo']])
    matriz_curso = forms.ModelChoiceFieldPlus(
        MatrizCurso.objects, label='Matriz/Curso', help_text='Formato: 20141.1.<strong>[011004]</strong>.1M', widget=AutocompleteWidget(search_fields=MatrizCurso.SEARCH_FIELDS)
    )
    turno = forms.ModelChoiceField(Turno.objects)

    qtd_periodo_1 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_2 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_3 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_4 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_5 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_6 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_7 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_8 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_9 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_10 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_11 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_12 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)

    turno_periodo_1 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_2 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_3 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_4 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_5 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_6 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_7 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_8 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_9 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_10 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_11 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )
    turno_periodo_12 = forms.ModelChoiceField(
        label='Turno', queryset=Turno.objects.all(), required=False, empty_label=None, help_text='Formato: 20141.1.011004.1<strong>[M]</strong>'
    )

    vagas_periodo_1 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_2 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_3 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_4 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_5 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_6 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_7 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_8 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_9 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_10 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_11 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_12 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)

    horario_campus = forms.ModelChoiceField(HorarioCampus.objects, label='Horário do Campus')
    calendario_academico = forms.ModelChoiceField(CalendarioAcademico.objects, label='Calendário Acadêmico')
    componentes = forms.MultipleModelChoiceField(ComponenteCurricular.objects, label='', widget=RenderableSelectMultiple('widgets/componentes_widget.html'))
    confirmacao = forms.BooleanField(
        label='Confirmação', required=True, help_text='Marque a opção acima e clique no botão "Finalizar" caso deseje que as turmas/diários identificados acima sejam criados.'
    )
    # plano de retomada de aulas em virtude da pandemia (COVID19)
    pertence_ao_plano_retomada = forms.BooleanField(
        label='Plano de Retomada',
        help_text='Relacionar a(s) turma(s) ao plano de retomada de aulas em virtude da pandemia (COVID19)',
        required=False
    )

    steps = (
        [('Dados do Curso', {'fields': ('ano_letivo', 'periodo_letivo', 'tipo_componente', 'matriz_curso')})],
        [
            ('1º Período', {'fields': ('qtd_periodo_1', 'turno_periodo_1', 'vagas_periodo_1')}),
            ('2º Período', {'fields': ('qtd_periodo_2', 'turno_periodo_2', 'vagas_periodo_2')}),
            ('3º Período', {'fields': ('qtd_periodo_3', 'turno_periodo_3', 'vagas_periodo_3')}),
            ('4º Período', {'fields': ('qtd_periodo_4', 'turno_periodo_4', 'vagas_periodo_4')}),
            ('5º Período', {'fields': ('qtd_periodo_5', 'turno_periodo_5', 'vagas_periodo_5')}),
            ('6º Período', {'fields': ('qtd_periodo_6', 'turno_periodo_6', 'vagas_periodo_6')}),
            ('7º Período', {'fields': ('qtd_periodo_7', 'turno_periodo_7', 'vagas_periodo_7')}),
            ('8º Período', {'fields': ('qtd_periodo_8', 'turno_periodo_8', 'vagas_periodo_8')}),
            ('9º Período', {'fields': ('qtd_periodo_9', 'turno_periodo_9', 'vagas_periodo_9')}),
            ('10º Período', {'fields': ('qtd_periodo_10', 'turno_periodo_10', 'vagas_periodo_10')}),
            ('11º Período', {'fields': ('qtd_periodo_11', 'turno_periodo_11', 'vagas_periodo_11')}),
            ('12º Período', {'fields': ('qtd_periodo_12', 'turno_periodo_12', 'vagas_periodo_12')}),
        ],
        [('Horário/Calendário e Componentes', {'fields': ('horario_campus', 'calendario_academico')}), ('Seleção de Componentes', {'fields': ('componentes',)})],
        [('Confirmação dos Dados', {'fields': ('pertence_ao_plano_retomada', 'confirmacao')})],
    )

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_matriz_curso(self):
        if not self.data.get('ano_letivo') or not self.data.get('periodo_letivo'):
            return forms.ValidationError(mark_safe('Matriz Curso inválida.'))
        matriz_curso = MatrizCurso.objects.get(id=self.data['matriz_curso'])
        is_secretario = in_group(self.request.user, 'Secretário Acadêmico, Administrador Acadêmico')
        if not is_secretario:
            if not matriz_curso.curso_campus.is_coordenador(self.request.user):
                raise forms.ValidationError('Coordenadores só podem gerar turmas para os cursos sob sua coordenação')
        if not (matriz_curso.curso_campus.diretoria.setor.uo.horariocampus_set.exists()):
            link = is_secretario and '<a href="/admin/edu/horariocampus/add/">Adicione um novo horário</a>' or ''
            raise forms.ValidationError(mark_safe(f'Não existe horário confirmado para o campus {matriz_curso.curso_campus.diretoria.setor.uo}. {link}'))
        if not (
            matriz_curso.curso_campus.diretoria.setor.uo.calendarioacademico_set.filter(ano_letivo__id=self.data['ano_letivo'], periodo_letivo=self.data['periodo_letivo']).exists()
        ):
            link = is_secretario and '<a href="/admin/edu/calendarioacademico/add/">Adicione um novo calendário</a>' or ''
            raise forms.ValidationError(
                mark_safe(f'Não existe calendário acadêmico para o campus {matriz_curso.curso_campus.diretoria.setor.uo} no período/ano informado. {link}')
            )
        return matriz_curso

    def clean_calendario_academico(self):
        calendario_academico = self.cleaned_data['calendario_academico']
        matriz_curso = self.cleaned_data['matriz_curso']
        if calendario_academico:
            qtd_avaliacoes = matriz_curso.matriz.componentecurricular_set.all().aggregate(Max('qtd_avaliacoes')).get('qtd_avaliacoes__max') or 0
            if calendario_academico.qtd_etapas < qtd_avaliacoes:
                raise ValidationError(
                    f'A matriz possui componentes com {qtd_avaliacoes} etapas, mas o calendário selecionado possui apenas {calendario_academico.qtd_etapas}.'
                )
        return calendario_academico

    def next_step(self):
        ano_letivo = self.get_entered_data('ano_letivo')
        periodo_letivo = self.get_entered_data('periodo_letivo')
        matriz_curso = self.get_entered_data('matriz_curso')

        if 'matriz_curso' in self.fields:
            self.fields['matriz_curso'].queryset = MatrizCurso.locals.filter(curso_campus__ativo=True, matriz__ativo=True)
        if 'horario_campus' in self.fields and matriz_curso:
            self.fields['horario_campus'].queryset = HorarioCampus.locals.filter(uo=matriz_curso.curso_campus.diretoria.setor.uo, ativo=True)
        if 'calendario_academico' in self.fields and matriz_curso and ano_letivo and periodo_letivo:
            qs_calendario_academico = CalendarioAcademico.locals.filter(
                uo=matriz_curso.curso_campus.diretoria.setor.uo, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo, tipo=matriz_curso.curso_campus.periodicidade
            )
            qs_calendario_academico = qs_calendario_academico.filter(diretoria__isnull=True) | qs_calendario_academico.filter(diretoria=matriz_curso.curso_campus.diretoria)
            self.fields['calendario_academico'].queryset = qs_calendario_academico
        if matriz_curso:
            for i in range(matriz_curso.matriz.qtd_periodos_letivos + 1, 13):
                if f'qtd_periodo_{i}' in self.fields:
                    self.fields[f'qtd_periodo_{i}'].required = False
                    self.fields[f'turno_periodo_{i}'].required = False
                    self.fields[f'vagas_periodo_{i}'].required = False
                    self.fields[f'qtd_periodo_{i}'].widget = forms.HiddenInput()
                    self.fields[f'turno_periodo_{i}'].widget = forms.HiddenInput()
                    self.fields[f'vagas_periodo_{i}'].widget = forms.HiddenInput()
        if 'componentes' in self.fields and matriz_curso:
            matriz_curso = matriz_curso
            periodos = []
            for i in range(1, matriz_curso.matriz.qtd_periodos_letivos + 1):
                if int(self.get_entered_data(f'qtd_periodo_{i}') or 0):
                    periodos.append(i)
            ids_componenentes_curriculares_associados = matriz_curso.matriz.componentecurricular_set.filter(componente_curricular_associado__isnull=False).values_list(
                'componente_curricular_associado', flat=True
            )
            qs = matriz_curso.matriz.componentecurricular_set.exclude(id__in=ids_componenentes_curriculares_associados)
            if int(self.get_entered_data('tipo_componente')) == 1:
                qs = qs.filter(periodo_letivo__in=periodos)
            else:
                qs = qs.filter(periodo_letivo__isnull=True)
            self.fields['componentes'].queryset = qs.order_by('periodo_letivo')

        if 'componentes' in self.cleaned_data:
            self.processar(False)

    def processar(self, commit=True):
        ano_letivo = self.cleaned_data['ano_letivo']
        periodo_letivo = self.cleaned_data['periodo_letivo']
        matriz_curso = self.cleaned_data['matriz_curso']

        numero_turmas_dict = {}
        turnos_dict = {}
        numero_vagas_dict = {}
        for i in range(1, matriz_curso.matriz.qtd_periodos_letivos + 1):
            numero_turmas_dict[i] = int(self.cleaned_data[f'qtd_periodo_{i}'] or 0)
            turnos_dict[i] = self.cleaned_data[f'turno_periodo_{i}'] or None
            numero_vagas_dict[i] = self.cleaned_data[f'vagas_periodo_{i}'] or 0

        horario_campus = self.cleaned_data['horario_campus']
        calendario_academico = self.cleaned_data['calendario_academico']
        componentes = self.cleaned_data['componentes']
        pertence_ao_plano_retomada = self.cleaned_data.get('pertence_ao_plano_retomada', False)
        confirmacao = self.cleaned_data.get('confirmacao')
        commit = commit and confirmacao
        self.turmas = Turma.gerar_turmas(
            ano_letivo,
            periodo_letivo,
            turnos_dict,
            numero_vagas_dict,
            numero_turmas_dict,
            matriz_curso.curso_campus,
            matriz_curso.matriz,
            horario_campus,
            calendario_academico,
            componentes,
            pertence_ao_plano_retomada,
            commit,
        )


class BuscaPessoaFisicaForm(forms.FormPlus):
    cpf = forms.BrCpfField()
    fieldsets = (('Identificação', {'fields': ('cpf',)}),)


class IdentificacaoCandidatoForm(FormWizardPlus):
    METHOD = 'GET'
    LAST_SUBMIT_LABEL = 'Finalizar Identificação do Candidato'

    ano = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano', required=True)
    semestre = periodo_letivo = forms.ChoiceField(choices=[['', '----']] + PERIODO_LETIVO_CHOICES, label='Semestre', required=True)
    edital = forms.ModelChoiceField(Edital.objects, label='Edital', widget=forms.Select(attrs=dict(style='width:600px')))
    cpf = forms.BrCpfField()

    candidato_vaga = forms.ModelChoiceField(CandidatoVaga.objects, label='Classificação', empty_label=None, widget=forms.RadioSelect())

    steps = (
        [('Identificação do Período', {'fields': ('ano', 'semestre')})],
        [('Seleção do Edital', {'fields': ('edital',)})],
        [('Identificação do Candidato', {'fields': ('cpf',)})],
        [('Indicação da Classificação', {'fields': ('candidato_vaga',)})],
    )

    def next_step(self):
        if 'edital' in self.fields:
            self.fields['edital'].queryset = self.get_edital_queryset()
        if 'candidato_vaga' in self.fields:
            self.fields['candidato_vaga'].queryset = self.get_candidato_vaga_queryset().all()
            if '_candidato_vaga' in self.request.GET:
                self.fields['candidato_vaga'].queryset = self.fields['candidato_vaga'].queryset.filter(pk=self.request.GET['_candidato_vaga'])

    def get_edital_queryset(self):
        ano = self.get_entered_data('ano')
        semestre = self.get_entered_data('semestre')
        return ano and semestre and Edital.locals.filter(ano=ano, semestre=semestre).distinct() or Edital.objects.none()

    def get_candidato(self):
        return self.get_candidato_vaga_queryset().all()[0].candidato

    def get_candidato_vaga_queryset(self):
        cpf = self.get_entered_data('cpf')
        edital = self.get_entered_data('edital')
        if cpf:
            return CandidatoVaga.objects.filter(oferta_vaga__oferta_vaga_curso__edital=edital, candidato__cpf=cpf)
        else:
            return CandidatoVaga.objects.none()

    def processar(self):
        return self.cleaned_data['candidato_vaga']

    def clean_cpf(self):
        if not self.get_candidato_vaga_queryset().exists():
            raise forms.ValidationError('Nenhum candidato habilitado foi encontrado com este CPF.')
        return self.cleaned_data['cpf']


class EfetuarMatriculaForm(FormWizardPlus):
    METHOD = 'POST'
    LAST_SUBMIT_LABEL = 'Finalizar Matrícula Institucional'

    foto = forms.PhotoCaptureField(required=False, widget=PhotoCapturePortraitInput)
    arquivo_foto = forms.ImageFieldPlus(label='Arquivo', required=False)

    nacionalidade = forms.ChoiceField(required=True, label='Nacionalidade', choices=Aluno.TIPO_NACIONALIDADE_CHOICES)
    cpf = forms.BrCpfField(required=False)
    passaporte = forms.CharField(required=False, label='Nº do Passaporte')
    nome = forms.CharFieldPlus(required=True, label='Nome', width=500)
    nome_social = forms.CharFieldPlus(required=False, label='Nome Social', help_text='Só preencher este campo a pedido do aluno e de acordo com a legislação vigente.', width=500)
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    data_nascimento = forms.DateFieldPlus(required=True, label='Data de Nascimento')
    estado_civil = forms.ChoiceField(required=True, choices=Aluno.ESTADO_CIVIL_CHOICES)

    # endereco
    logradouro = forms.CharFieldPlus(max_length=255, required=True, label='Logradouro', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=True, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=True, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='Cep')

    estado = forms.ModelChoiceField(Estado.objects, label='Estado', required=False)
    cidade = forms.ModelChoiceFieldPlus(
        Cidade.objects,
        label='Cidade',
        required=True,
        help_text='Preencha o nome da cidade sem acento.',
        widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS, form_filters=[('estado', 'estado__in')]),
    )

    tipo_zona_residencial = forms.ChoiceField(required=True, label='Zona Residencial', choices=[['', '-----']] + Aluno.TIPO_ZONA_RESIDENCIAL_CHOICES)

    # dados familiares
    nome_pai = forms.CharFieldPlus(max_length=255, label='Nome do Pai', required=False, width=500)
    estado_civil_pai = forms.ChoiceField(choices=Aluno.EMPTY_CHOICES + Aluno.ESTADO_CIVIL_CHOICES, required=False)
    pai_falecido = forms.BooleanField(label='Pai é falecido?', required=False)
    nome_mae = forms.CharFieldPlus(max_length=255, label='Nome da Mãe', required=True, width=500)
    estado_civil_mae = forms.ChoiceField(choices=Aluno.EMPTY_CHOICES + Aluno.ESTADO_CIVIL_CHOICES, required=False)
    mae_falecida = forms.BooleanField(label='Mãe é falecida?', required=False)
    responsavel = forms.CharFieldPlus(max_length=255, label='Nome do Responsável', required=False, width=500, help_text='Obrigatório para menores de idade.')
    email_responsavel = forms.CharFieldPlus(max_length=255, label='Email do Responsável', required=False, width=500)
    parentesco_responsavel = forms.ChoiceField(label='Parenteste com Responsável', choices=[['', '---------']] + Aluno.PARENTESCO_CHOICES, required=False)
    cpf_responsavel = forms.BrCpfField(label='CPF do Responsável', required=False)

    # contato
    telefone_principal = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Principal', help_text='(XX) XXXX-XXXX')
    telefone_secundario = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Secundário', help_text='(XX) XXXX-XXXX')
    telefone_adicional_1 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    telefone_adicional_2 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    email_pessoal = forms.EmailField(max_length=255, required=False, label='E-mail Pessoal')

    # outras informacoes
    tipo_sanguineo = forms.ChoiceField(required=False, label='Tipo Sanguíneo', choices=Aluno.EMPTY_CHOICES + Aluno.TIPO_SANGUINEO_CHOICES)
    pais_origem = forms.ModelChoiceField(Pais.objects, required=False, label='País de Origem', help_text='Obrigatório para estrangeiros')

    estado_naturalidade = forms.ModelChoiceField(Estado.objects, label='Estado de Origem', required=False)
    naturalidade = forms.ModelChoiceFieldPlus(
        Cidade.objects,
        label='Naturalidade',
        required=False,
        widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS, form_filters=[('estado_naturalidade', 'estado__in')]),
    )

    raca = forms.ModelChoiceField(Raca.objects.all(), required=True, label='Raça')

    # necessidades especiais
    aluno_pne = forms.ChoiceField(label='Portador de Necessidades Especiais', required=True, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    tipo_necessidade_especial = forms.ChoiceField(required=False, label='Deficiência', choices=[['', '---------']] + Aluno.TIPO_NECESSIDADE_ESPECIAL_CHOICES)
    tipo_transtorno = forms.ChoiceField(required=False, label='Transtorno', choices=[['', '---------']] + Aluno.TIPO_TRANSTORNO_CHOICES)
    superdotacao = forms.ChoiceField(required=False, label='Superdotação', choices=[['', '---------']] + Aluno.SUPERDOTACAO_CHOICES)

    # dados escolares
    nivel_ensino_anterior = forms.ModelChoiceField(NivelEnsino.objects, required=True, label='Nível de Ensino')
    tipo_instituicao_origem = forms.ChoiceField(required=True, label='Tipo da Instituição', choices=[['', '---------']] + Aluno.TIPO_INSTITUICAO_ORIGEM_CHOICES)
    nome_instituicao_anterior = forms.CharField(max_length=255, required=False, label='Nome da Instituição')
    ano_conclusao_estudo_anterior = forms.ModelChoiceField(Ano.objects, required=False, label='Ano de Conclusão', help_text='Obrigatório para alunos com nível médio')

    # rg
    numero_rg = forms.CharField(max_length=255, required=False, label='Número do RG')
    uf_emissao_rg = forms.ModelChoiceField(Estado.objects, required=False, label='Estado Emissor')
    orgao_emissao_rg = forms.ModelChoiceField(OrgaoEmissorRg.objects, required=False, label='Orgão Emissor')
    data_emissao_rg = forms.DateFieldPlus(required=False, label='Data de Emissão')

    # titulo_eleitor
    numero_titulo_eleitor = forms.CharField(max_length=255, required=False, label='Título de Eleitor')
    zona_titulo_eleitor = forms.CharField(max_length=255, required=False, label='Zona')
    secao = forms.CharField(max_length=255, required=False, label='Seção')
    data_emissao_titulo_eleitor = forms.DateFieldPlus(required=False, label='Data de Emissão')
    uf_emissao_titulo_eleitor = forms.ModelChoiceField(Estado.objects, required=False, label='Estado Emissor')

    # carteira de reservista
    numero_carteira_reservista = forms.CharField(max_length=255, required=False, label='Número da Carteira de Reservista')
    regiao_carteira_reservista = forms.CharField(max_length=255, required=False, label='Região')
    serie_carteira_reservista = forms.CharField(max_length=255, required=False, label='Série')
    estado_emissao_carteira_reservista = forms.ModelChoiceField(Estado.objects, required=False, label='Estado Emissor')
    ano_carteira_reservista = forms.IntegerField(required=False, label='Ano')

    # certidao_civil
    tipo_certidao = forms.ChoiceField(required=True, label='Tipo de Certidão', choices=Aluno.TIPO_CERTIDAO_CHOICES)
    cartorio = forms.ModelChoiceFieldPlus(
        Cartorio.objects,
        required=False,
        label='Cartório',
        help_text='Digite o nome do catório ou cidade para listar os catórios cadastrados',
        widget=AutocompleteWidget(search_fields=Cartorio.SEARCH_FIELDS),
    )
    numero_certidao = forms.CharField(max_length=255, required=False, label='Número de Termo')
    folha_certidao = forms.CharField(max_length=255, required=False, label='Folha')
    livro_certidao = forms.CharField(max_length=255, required=False, label='Livro')
    data_emissao_certidao = forms.DateFieldPlus(required=False, label='Data de Emissão')
    matricula_certidao = forms.CharField(max_length=255, required=False, label='Matrícula', help_text='Obrigatório para certidões realizadas a partir de 01/01/2010')

    # dados da matrícula
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), required=True, label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(required=True, label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)
    turno = forms.ModelChoiceField(Turno.objects, required=True, label='Turno')
    polo = forms.ModelChoiceField(Polo.objects, required=False, label='Polo EAD', help_text='Apenas para o Turno EAD.')
    forma_ingresso = forms.ModelChoiceField(FormaIngresso.objects, required=True, label='Forma de Ingresso')
    cota_sistec = forms.ChoiceField(label='Cota SISTEC', choices=Aluno.COTA_SISTEC_CHOICES, required=False, widget=forms.HiddenInput())
    cota_mec = forms.ChoiceField(label='Cota MEC', choices=Aluno.COTA_MEC_CHOICES, required=False, widget=forms.HiddenInput())
    possui_convenio = forms.BooleanRequiredField(label='Possui Convênio')
    convenio = forms.ModelChoiceField(Convenio.objects, required=False, label='Convênio')
    data_conclusao_intercambio = forms.DateFieldPlus(
        required=False, label='Conclusão do Intercâmbio', help_text='Preencha esse campo com a data de conclusão do intercâmbio caso se trate de um aluno de intercâmbio'
    )
    matriz_curso = forms.ModelChoiceFieldPlus(MatrizCurso.objects, required=True, label='Matriz/Curso')
    linha_pesquisa = forms.ModelChoiceFieldPlus(
        LinhaPesquisa.objects, required=False, label='Linha de Pesquisa', help_text='Obrigatório para alunos de Mestrado e Doutourado. Caso não saiba, escreva "A definir".'
    )
    aluno_especial = forms.BooleanField(required=False, label='Aluno Especial?', help_text='Marque essa opção caso se trate de um aluno especial em curso de Pós-Graduação')
    numero_pasta = forms.CharFieldPlus(label='Número da Pasta', required=False, max_length=255)

    observacao_matricula = forms.CharField(widget=forms.Textarea(), required=False, label='Observação')

    utiliza_transporte_escolar_publico = forms.ChoiceField(label='Utiliza Transporte Escolar Público', required=False, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    poder_publico_responsavel_transporte = forms.ChoiceField(
        label='Poder Público Responsável pelo Transporte Escolar', choices=[['', '---------']] + Aluno.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, required=False
    )
    tipo_veiculo = forms.ChoiceField(label='Tipo de Veículo Utilizado no Transporte Escolar', choices=[['', '---------']] + Aluno.TIPO_VEICULO_CHOICES_FOR_FORM, required=False)

    steps = (
        [('Identificação', {'fields': ('nacionalidade', 'cpf', 'passaporte')})],
        [
            ('Dados Pessoais', {'fields': ('nome', 'nome_social', 'sexo', 'data_nascimento', 'estado_civil')}),
            (
                'Dados Familiares',
                {
                    'fields': (
                        'nome_pai',
                        'estado_civil_pai',
                        'pai_falecido',
                        'nome_mae',
                        'estado_civil_mae',
                        'mae_falecida',
                        'responsavel',
                        'parentesco_responsavel',
                        'cpf_responsavel',
                    )
                },
            ),
            ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'estado', 'cidade', 'tipo_zona_residencial')}),
        ],
        [
            ('Informações para Contato', {'fields': ('telefone_principal', 'telefone_secundario', 'telefone_adicional_1', 'telefone_adicional_2', 'email_pessoal')}),
            ('Deficiências, Transtornos e Superdotação', {'fields': ('aluno_pne', 'tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao')}),
            ('Transporte Escolar Utilizado', {'fields': ('utiliza_transporte_escolar_publico', 'poder_publico_responsavel_transporte', 'tipo_veiculo')}),
            ('Outras Informações', {'fields': ('tipo_sanguineo', 'pais_origem', 'estado_naturalidade', 'naturalidade', 'raca')}),
            ('Dados Escolares Anteriores', {'fields': ('nivel_ensino_anterior', 'tipo_instituicao_origem', 'nome_instituicao_anterior', 'ano_conclusao_estudo_anterior')}),
        ],
        [
            ('RG', {'fields': ('numero_rg', 'uf_emissao_rg', 'orgao_emissao_rg', 'data_emissao_rg')}),
            ('Título de Eleitor', {'fields': ('numero_titulo_eleitor', 'zona_titulo_eleitor', 'secao', 'data_emissao_titulo_eleitor', 'uf_emissao_titulo_eleitor')}),
            (
                'Carteira de Reservista',
                {
                    'fields': (
                        'numero_carteira_reservista',
                        'regiao_carteira_reservista',
                        'serie_carteira_reservista',
                        'estado_emissao_carteira_reservista',
                        'ano_carteira_reservista',
                    )
                },
            ),
            ('Certidão Civil', {'fields': ('tipo_certidao', 'cartorio', 'numero_certidao', 'folha_certidao', 'livro_certidao', 'data_emissao_certidao', 'matricula_certidao')}),
        ],
        [
            ('Foto  (captura com câmera ou upload de arquivo)', {'fields': ('foto', 'arquivo_foto')}),
            (
                'Dados da Matrícula',
                {
                    'fields': (
                        'ano_letivo',
                        'periodo_letivo',
                        'turno',
                        'forma_ingresso',
                        'polo',
                        'cota_sistec',
                        'cota_mec',
                        'possui_convenio',
                        'convenio',
                        'data_conclusao_intercambio',
                        'matriz_curso',
                        'linha_pesquisa',
                        'aluno_especial',
                        'numero_pasta',
                    )
                },
            ),
            ('Observação', {'fields': ('observacao_matricula',)}),
        ],
    )

    def __init__(self, request, candidato_vaga, *args, **kwargs):
        self.candidato_vaga = candidato_vaga
        super().__init__(*args, **kwargs)
        self.request = request
        if self.candidato_vaga:
            self.initial['cpf'] = self.candidato_vaga.candidato.cpf
            self.initial['nome'] = self.candidato_vaga.candidato.nome

    def clean_ano_conclusao_estudo_anterior(self):
        ano_conclusao_estudo_anterior = self.cleaned_data.get('ano_conclusao_estudo_anterior')
        nivel_ensino_anterior = self.data.get('nivel_ensino_anterior')
        if nivel_ensino_anterior == str(NivelEnsino.MEDIO) and not ano_conclusao_estudo_anterior:
            raise forms.ValidationError('O Ano de Conclusão é de preenchimento obrigatório.')
        return ano_conclusao_estudo_anterior

    def clean_ano_letivo(self):
        ano_letivo = self.cleaned_data.get('ano_letivo')
        if ano_letivo and self.candidato_vaga:
            if ano_letivo != self.candidato_vaga.candidato.edital.ano:
                raise forms.ValidationError(f'Ano incompatível com o do edital do candidato, que é {self.candidato_vaga.candidato.edital.ano}')
        return ano_letivo

    def clean_tipo_instituicao_origem(self):
        tipo_instituicao_origem = self.cleaned_data.get('tipo_instituicao_origem')

        if (
            self.candidato_vaga
            and self.candidato_vaga.oferta_vaga.lista.forma_ingresso_id
            and self.candidato_vaga.oferta_vaga.lista.forma_ingresso.programa_vaga_escola_publica
            and not tipo_instituicao_origem == 'Pública'
        ):
            raise forms.ValidationError('O candidato está ingressando como aluno de escola pública.')

        return tipo_instituicao_origem

    def clean_utiliza_transporte_escolar_publico(self):
        utiliza_transporte_escolar_publico = self.cleaned_data.get('utiliza_transporte_escolar_publico')
        if utiliza_transporte_escolar_publico == 'Sim':
            if not self.data.get('poder_publico_responsavel_transporte') or not self.data.get('tipo_veiculo'):
                raise forms.ValidationError('Informe o responsável pelo transporte público e o tipo utilizado')
        else:
            if self.data.get('poder_publico_responsavel_transporte') or self.data.get('tipo_veiculo'):
                raise forms.ValidationError('Marque a opção "Utiliza Transporte Escolar Público" caso deseje informar o responsável ou tipo de transporte público utilizado.')
        return utiliza_transporte_escolar_publico

    def clean_aluno_pne(self):
        aluno_pne = self.cleaned_data.get('aluno_pne')

        if (
            self.candidato_vaga
            and self.candidato_vaga.oferta_vaga.lista.forma_ingresso_id
            and self.candidato_vaga.oferta_vaga.lista.forma_ingresso.programa_vaga_pessoa_deficiencia
            and not aluno_pne == 'Sim'
        ):
            raise forms.ValidationError('O candidato está ingressando como deficiente. Informe sua necessidade especial.')

        if aluno_pne == 'Sim' and not (self.data.get('tipo_necessidade_especial') or self.data.get('tipo_transtorno') or self.data.get('superdotacao')):
            raise forms.ValidationError('Informe a deficiência, transtorno ou superdotação do aluno.')
        return aluno_pne

    def clean_periodo_letivo(self):
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        if periodo_letivo and self.candidato_vaga:
            if int(periodo_letivo) != self.candidato_vaga.candidato.edital.semestre:
                raise forms.ValidationError(f'Período incompatível com o do edital do candidato, que é {self.candidato_vaga.candidato.edital.semestre}')
        return periodo_letivo

    def clean_nacionalidade(self):
        nacionalidade = self.get_entered_data('nacionalidade')
        if nacionalidade == 'Estrangeira':
            if not self.get_entered_data('passaporte'):
                raise forms.ValidationError('Informe o passaporte do aluno intercambista.')
        else:
            if not self.get_entered_data('cpf'):
                raise forms.ValidationError('Informe o CPF do aluno.')
        return nacionalidade

    def clean_nome(self):
        nome = self.get_entered_data('nome')

        if nome and not eh_nome_completo(nome):
            raise ValidationError('O nome do aluno precisa ser completo e não pode conter números.')

        return self.cleaned_data.get('nome')

    def clean_nome_social(self):
        nome = self.get_entered_data('nome_social')

        if nome and not eh_nome_completo(nome):
            raise ValidationError('O nome social do aluno precisa ser completo e não pode conter números.')

        return self.cleaned_data.get('nome_social')

    def clean_nome_pai(self):
        nome = self.get_entered_data('nome_pai')

        if nome and not eh_nome_completo(nome):
            raise ValidationError('O nome do pai precisa ser completo e não pode conter números.')

        return self.cleaned_data.get('nome_pai')

    def clean_nome_mae(self):
        nome = self.get_entered_data('nome_mae')

        if nome and not eh_nome_completo(nome):
            raise ValidationError('O nome da mãe precisa ser completo e não pode conter números.')

        return self.cleaned_data.get('nome_mae')

    def clean_responsavel(self):
        nome = self.get_entered_data('responsavel')

        if nome and not eh_nome_completo(nome):
            raise ValidationError('O nome do responsável precisa ser completo e não pode conter números.')

        p = PessoaFisica()
        p.nascimento_data = self.get_entered_data('data_nascimento')

        if p.nascimento_data and p.idade < 18 and not nome:
            raise ValidationError('Campo obrigatório para menores de idade.')

        return nome

    def clean_parentesco_responsavel(self):
        responsavel = self.data.get('responsavel')
        parentesco_responsavel = self.data.get('parentesco_responsavel')
        if responsavel and not parentesco_responsavel:
            raise ValidationError('O parentesco do responsável é necessário quando o responsável é informado.')
        return parentesco_responsavel

    def clean_polo(self):
        matriz_curso = self.get_entered_data('matriz_curso')
        polo = self.get_entered_data('polo')

        if matriz_curso:
            if polo:
                if not matriz_curso.curso_campus.diretoria.ead:
                    raise forms.ValidationError('O campo Polo deve ser definido apenas para cursos EAD.')
            elif matriz_curso.curso_campus.diretoria.ead:
                raise ValidationError('É necessário informar o Polo do aluno.')

        return self.cleaned_data.get('polo')

    def clean_data_nascimento(self):
        menor_data_valida = datetime.datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S').date()
        if 'data_nascimento' in self.cleaned_data and self.cleaned_data['data_nascimento'] < menor_data_valida:
            raise forms.ValidationError('Data de nascimento deve ser maior que 01/01/1900.')
        p = PessoaFisica()
        p.nascimento_data = self.get_entered_data('data_nascimento')
        if p.nascimento_data and p.idade < 18 and self.candidato_vaga and self.candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus.modalidade.pk == Modalidade.INTEGRADO_EJA:
            raise ValidationError('O candidato não pode se matricular neste curso por que ainda é menor de idade.')
        return self.cleaned_data['data_nascimento']

    def clean_pais_origem(self):
        nacionalidade = self.get_entered_data('nacionalidade')
        if nacionalidade and not nacionalidade == 'Brasileira' and not self.cleaned_data['pais_origem']:
            raise forms.ValidationError('O campo "País de Origem" possui preenchimento obrigatório quando a pessoa nasceu no exterior.')

        return 'pais_origem' in self.cleaned_data and self.cleaned_data['pais_origem'] or None

    def clean_naturalidade(self):
        nacionalidade = self.get_entered_data('nacionalidade')
        eh_brasileiro = nacionalidade and nacionalidade == 'Brasileira'
        if (self.exige_naturalidade_estrangeiro or eh_brasileiro) and 'naturalidade' not in self.cleaned_data or not self.cleaned_data['naturalidade']:
            raise forms.ValidationError('O campo "Naturalidade" possui preenchimento obrigatório.')

        naturalidade = self.get_entered_data('naturalidade')
        nome_pais = naturalidade and naturalidade.pais and naturalidade.pais.nome
        if eh_brasileiro and nome_pais != 'Brasil':
            raise forms.ValidationError('Não pode ser informado uma naturalidade fora do Brasil para aluno com nacionalidade Brasileira.')
        if not eh_brasileiro and nome_pais == 'Brasil':
            raise forms.ValidationError('Não pode ser informado uma naturalidade do Brasil para aluno com nacionalidade Estrangeira ou Brasileira - Nascido no exterior ou naturalizado.')

        return 'naturalidade' in self.cleaned_data and self.cleaned_data['naturalidade'] or None

    def clean_email_pessoal(self):
        if 'email_pessoal' in self.cleaned_data:
            email_pessoal = self.cleaned_data['email_pessoal']

            if not Configuracao.get_valor_por_chave('comum', 'permite_email_institucional_email_secundario') and Configuracao.eh_email_institucional(email_pessoal):
                raise forms.ValidationError("Escolha um e-mail que não seja institucional.")

        return 'email_pessoal' in self.cleaned_data and self.cleaned_data['email_pessoal'] or ''

    def clean_matricula_certidao(self):
        if 'data_emissao_certidao' in self.cleaned_data:
            data_emissao_certidao = self.cleaned_data['data_emissao_certidao']

            if not data_emissao_certidao or data_emissao_certidao < datetime.date(2010, 1, 1):
                pass
            else:
                if 'matricula_certidao' not in self.cleaned_data or not self.cleaned_data['matricula_certidao']:
                    raise forms.ValidationError('O campo matrícula é de preenchimento obrigatório para certidões realizadas a partir de 01/01/2010.')

        return 'matricula_certidao' in self.cleaned_data and self.cleaned_data['matricula_certidao'] or None

    def clean_linha_pesquisa(self):
        if 'matriz_curso' in self.data and self.data['matriz_curso']:
            qs_matriz_curso = MatrizCurso.objects.filter(pk=self.data['matriz_curso'])
            if qs_matriz_curso:
                matriz_curso = qs_matriz_curso[0]
                if (matriz_curso.curso_campus.modalidade.pk in [Modalidade.MESTRADO, Modalidade.DOUTORADO]) and not self.cleaned_data['linha_pesquisa']:
                    raise forms.ValidationError(f'Este campo é obrigatório por se tratar de um aluno de um curso de  {matriz_curso.curso_campus.modalidade}.')
        return 'linha_pesquisa' in self.cleaned_data and self.cleaned_data['linha_pesquisa'] or None

    def clean_matriz_curso(self):
        matriz_curso = self.cleaned_data.get('matriz_curso')
        if matriz_curso:
            if self.candidato_vaga and not matriz_curso.curso_campus == self.candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus:
                raise forms.ValidationError('Esta matriz não é válida.')
        return matriz_curso

    def clean_convenio(self):
        possui_convenio = self.cleaned_data.get('possui_convenio')
        if possui_convenio and not self.data.get('convenio'):
            raise forms.ValidationError('Informe o convênio')
        elif not possui_convenio and self.data.get('convenio'):
            raise forms.ValidationError('Não é possível selecionar um convênio quando o valor do campo "Possui Convênio?" é "Não".')
        return self.cleaned_data.get('convenio')

    def next_step(self):
        if 'forma_ingresso' in self.fields:
            if self.candidato_vaga:
                if self.candidato_vaga.oferta_vaga.lista.forma_ingresso:
                    self.fields['forma_ingresso'].queryset = FormaIngresso.objects.filter(pk=self.candidato_vaga.oferta_vaga.lista.forma_ingresso.pk)
                    self.fields['forma_ingresso'].initial = self.candidato_vaga.oferta_vaga.lista.forma_ingresso.pk
                else:
                    self.fields['forma_ingresso'].queryset = FormaIngresso.objects.none()
            else:
                self.fields['forma_ingresso'].queryset = FormaIngresso.objects.exclude(descricao='Processo Seletivo').filter(ativo=True)
        if 'matriz_curso' in self.fields:
            self.fields['matriz_curso'].queryset = MatrizCurso.locals.filter(matriz__ativo=True)
            if self.candidato_vaga:
                self.fields['matriz_curso'].queryset = self.fields['matriz_curso'].queryset.filter(curso_campus=self.candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus)
        if 'cpf' in self.cleaned_data:
            qs = PessoaFisica.objects.filter(cpf=self.cleaned_data['cpf'])
            if qs:
                pessoa_fisica = qs[0]
                self.initial.update(nome=pessoa_fisica.nome, sexo=pessoa_fisica.sexo, data_nascimento=pessoa_fisica.nascimento_data)
        if 'pais_origem' in self.fields:
            self.fields['pais_origem'].queryset = Pais.objects.all().exclude(nome='Brasil')
        if 'naturalidade' in self.fields:
            self.exige_naturalidade_estrangeiro = Configuracao.get_valor_por_chave('edu', 'exige_naturalidade_estrangeiro')
            if self.exige_naturalidade_estrangeiro:
                self.fields['naturalidade'].required = True
            nacionalidade = self.get_entered_data('nacionalidade')
            if nacionalidade and nacionalidade == 'Brasileira':
                self.fields['naturalidade'].queryset = Cidade.objects.filter(codigo__isnull=False)
                self.fields['naturalidade'].help_text = 'Cidade em que o aluno nasceu. Obrigatório para brasileiros'
            elif nacionalidade and nacionalidade == 'Estrangeira':
                self.fields['naturalidade'].queryset = Cidade.objects.filter(codigo__isnull=True)
                self.fields['naturalidade'].help_text = 'Cidade/Província em que o aluno nasceu.'

    def clean_aluno_especial(self):
        aluno_especial = self.cleaned_data['aluno_especial']
        if aluno_especial:
            matriz_curso = self.cleaned_data['matriz_curso']
            limite = matriz_curso.matriz.estrutura.numero_max_alunos_especiais
            if limite:
                qs = Aluno.objects.filter(
                    situacao_id=SituacaoMatricula.MATRICULADO, curso_campus=matriz_curso.curso_campus,
                    aluno_especial=True
                )
                if qs.count() >= limite:
                    raise ValidationError('Limite de alunos especiais, que é de {} aluno(s), já atingido.'.format(
                        limite
                    ))
        return aluno_especial

    def clean(self):

        matriz_curso = self.cleaned_data.get('matriz_curso')
        cpf = self.cleaned_data.get('cpf')
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        if matriz_curso and cpf and ano_letivo and periodo_letivo:
            qs_alunos = Aluno.objects.filter(
                curso_campus=matriz_curso.curso_campus, matriz=matriz_curso.matriz, pessoa_fisica__cpf=cpf, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo
            ).exclude(situacao__id__in=[SituacaoMatricula.CANCELADO, SituacaoMatricula.CANCELAMENTO_COMPULSORIO])
            if qs_alunos.exists():
                raise forms.ValidationError('Matrícula duplicada')

        if (
            'turno' in self.cleaned_data
            and 'ano_letivo' in self.cleaned_data
            and 'periodo_letivo' in self.cleaned_data
            and 'turno' in self.cleaned_data
            and 'matriz_curso' in self.cleaned_data
            and self.is_curso_fic()
        ):
            if not Turma.locals.filter(
                ano_letivo=self.cleaned_data['ano_letivo'],
                periodo_letivo=self.cleaned_data['periodo_letivo'],
                turno=self.cleaned_data['turno'],
                curso_campus=self.cleaned_data['matriz_curso'].curso_campus,
                matriz=self.cleaned_data['matriz_curso'].matriz,
            ).exists():
                raise forms.ValidationError('Não há turmas para o ano, período, turno, curso e matriz selecionados.')

        forma_ingresso = self.cleaned_data.get('forma_ingresso')
        raca = self.cleaned_data.get('raca')
        if raca and forma_ingresso and forma_ingresso.racas.exists():
            if not forma_ingresso.racas.filter(pk=raca.pk).exists():
                raise forms.ValidationError('A raça/etnia do aluno não é compatível com a forma as raças/etnias associados à forma de ingresso.')

        return self.cleaned_data

    def is_curso_fic(self):
        matriz_curso = self.cleaned_data.get('matriz_curso')
        return matriz_curso and matriz_curso.curso_campus.is_fic()

    @transaction.atomic
    def processar(self):
        pessoa_fisica = PessoaFisica()
        pessoa_fisica.cpf = self.cleaned_data['cpf']
        pessoa_fisica.nome_registro = self.cleaned_data['nome']
        pessoa_fisica.nome_social = self.cleaned_data['nome_social']
        pessoa_fisica.sexo = self.cleaned_data['sexo']
        pessoa_fisica.nascimento_data = self.cleaned_data['data_nascimento']
        pessoa_fisica.save()

        aluno = Aluno()
        aluno.periodo_atual = 1
        aluno.pessoa_fisica = pessoa_fisica
        aluno.estado_civil = self.cleaned_data['estado_civil']
        # dados familiares
        aluno.nome_pai = self.cleaned_data['nome_pai']
        aluno.estado_civil_pai = self.cleaned_data['estado_civil_pai']
        aluno.pai_falecido = self.cleaned_data['pai_falecido']
        aluno.nome_mae = self.cleaned_data['nome_mae']
        aluno.estado_civil_mae = self.cleaned_data['estado_civil_mae']
        aluno.mae_falecida = self.cleaned_data['mae_falecida']
        aluno.responsavel = self.cleaned_data['responsavel']
        aluno.cpf_responsavel = self.cleaned_data['cpf_responsavel']
        aluno.parentesco_responsavel = self.cleaned_data['parentesco_responsavel']
        # endereco
        aluno.logradouro = self.cleaned_data['logradouro']
        aluno.numero = self.cleaned_data['numero']
        aluno.complemento = self.cleaned_data['complemento']
        aluno.bairro = self.cleaned_data['bairro']
        aluno.cep = self.cleaned_data['cep']
        aluno.cidade = self.cleaned_data['cidade']
        aluno.tipo_zona_residencial = self.cleaned_data['tipo_zona_residencial']
        # contato
        aluno.telefone_principal = self.cleaned_data['telefone_principal']
        aluno.telefone_secundario = self.cleaned_data['telefone_secundario']
        aluno.telefone_adicional_1 = self.cleaned_data['telefone_adicional_1']
        aluno.telefone_adicional_2 = self.cleaned_data['telefone_adicional_2']
        # TODO INSERIR CÓDIGO PARA CRIAÇÃO DO E-MAIL E ATUALIZAÇÃO NO AD

        # transporte escolar
        if self.cleaned_data['utiliza_transporte_escolar_publico']:
            aluno.poder_publico_responsavel_transporte = self.cleaned_data['poder_publico_responsavel_transporte']
            aluno.tipo_veiculo = self.cleaned_data['tipo_veiculo']
        else:
            aluno.poder_publico_responsavel_transporte = None
            aluno.tipo_veiculo = None

        # outras informacoes
        aluno.tipo_sanguineo = self.cleaned_data['tipo_sanguineo']
        aluno.nacionalidade = self.cleaned_data['nacionalidade']
        aluno.passaporte = self.cleaned_data['passaporte']
        aluno.naturalidade = self.cleaned_data['naturalidade']
        aluno.pessoa_fisica.raca = self.cleaned_data['raca']
        aluno.aluno_especial = self.cleaned_data['aluno_especial']

        if self.cleaned_data['aluno_pne']:
            aluno.tipo_necessidade_especial = self.cleaned_data['tipo_necessidade_especial']
            aluno.tipo_transtorno = self.cleaned_data['tipo_transtorno']
            aluno.superdotacao = self.cleaned_data['superdotacao']
        else:
            aluno.tipo_necessidade_especial = None
            aluno.tipo_transtorno = None
            aluno.superdotacao = None

        # dados escolares
        aluno.nivel_ensino_anterior = self.cleaned_data['nivel_ensino_anterior']
        aluno.tipo_instituicao_origem = self.cleaned_data['tipo_instituicao_origem']
        aluno.nome_instituicao_anterior = self.cleaned_data['nome_instituicao_anterior']
        aluno.ano_conclusao_estudo_anterior = self.cleaned_data['ano_conclusao_estudo_anterior']
        # rg
        aluno.numero_rg = self.cleaned_data['numero_rg']
        aluno.uf_emissao_rg = self.cleaned_data['uf_emissao_rg']
        aluno.orgao_emissao_rg = self.cleaned_data['orgao_emissao_rg']
        aluno.data_emissao_rg = self.cleaned_data['data_emissao_rg']
        # titulo_eleitor
        aluno.numero_titulo_eleitor = self.cleaned_data['numero_titulo_eleitor']
        aluno.zona_titulo_eleitor = self.cleaned_data['zona_titulo_eleitor']
        aluno.secao = self.cleaned_data['secao']
        aluno.data_emissao_titulo_eleitor = self.cleaned_data['data_emissao_titulo_eleitor']
        aluno.uf_emissao_titulo_eleitor = self.cleaned_data['uf_emissao_titulo_eleitor']
        # carteira de reservista
        aluno.numero_carteira_reservista = self.cleaned_data['numero_carteira_reservista']
        aluno.regiao_carteira_reservista = self.cleaned_data['regiao_carteira_reservista']
        aluno.serie_carteira_reservista = self.cleaned_data['serie_carteira_reservista']
        aluno.estado_emissao_carteira_reservista = self.cleaned_data['estado_emissao_carteira_reservista']
        aluno.ano_carteira_reservista = self.cleaned_data['ano_carteira_reservista']
        # certidao_civil
        aluno.tipo_certidao = self.cleaned_data['tipo_certidao']
        aluno.cartorio = self.cleaned_data['cartorio']
        aluno.numero_certidao = self.cleaned_data['numero_certidao']
        aluno.folha_certidao = self.cleaned_data['folha_certidao']
        aluno.livro_certidao = self.cleaned_data['livro_certidao']
        aluno.data_emissao_certidao = self.cleaned_data['data_emissao_certidao']
        aluno.matricula_certidao = self.cleaned_data['matricula_certidao']
        # dados da matrícula
        aluno.ano_letivo = self.cleaned_data['ano_letivo']
        aluno.periodo_letivo = self.cleaned_data['periodo_letivo']
        aluno.turno = self.cleaned_data['turno']
        aluno.polo = self.cleaned_data['polo']
        aluno.forma_ingresso = self.cleaned_data['forma_ingresso']
        aluno.cota_sistec = self.cleaned_data['cota_sistec']
        aluno.cota_mec = self.cleaned_data['cota_mec']
        aluno.possui_convenio = self.cleaned_data['possui_convenio']
        aluno.convenio = self.cleaned_data['convenio']
        aluno.data_conclusao_intercambio = self.cleaned_data['data_conclusao_intercambio']
        aluno.curso_campus = self.cleaned_data['matriz_curso'].curso_campus
        aluno.matriz = self.cleaned_data['matriz_curso'].matriz
        aluno.linha_pesquisa = self.cleaned_data['linha_pesquisa']
        aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
        # ano_let_prev_conclusao será calculado no save do aluno
        aluno.ano_let_prev_conclusao = None
        aluno.numero_pasta = self.cleaned_data['numero_pasta']
        prefixo = f'{aluno.ano_letivo}{aluno.periodo_letivo}{aluno.curso_campus.codigo}'
        aluno.matricula = SequencialMatricula.proximo_numero(prefixo)
        aluno.candidato_vaga = self.candidato_vaga
        aluno.email_scholar = ''
        aluno.save()

        observacao = self.cleaned_data['observacao_matricula']
        if observacao:
            obs = Observacao()
            obs.aluno = aluno
            obs.data = datetime.datetime.now()
            obs.observacao = observacao
            obs.usuario = self.request.user
            obs.save()

        aluno.pessoa_fisica.username = aluno.matricula
        aluno.pessoa_fisica.email_secundario = self.cleaned_data['email_pessoal']
        aluno.pessoa_fisica.save()

        if 'foto' in self.cleaned_data and self.cleaned_data.get('foto'):
            aluno.foto.save(f'{aluno.pk}.jpg', ContentFile(self.cleaned_data['foto']))
        elif 'arquivo_foto' in self.cleaned_data and self.cleaned_data.get('arquivo_foto'):
            aluno.foto.save(f'{aluno.pk}.jpg', ContentFile(self.cleaned_data.get('arquivo_foto').read()))

        aluno.save()

        hsm = HistoricoSituacaoMatricula()
        hsm.aluno = aluno
        hsm.situacao = aluno.situacao
        hsm.data = datetime.datetime.now()
        hsm.save()

        matricula_periodo = MatriculaPeriodo()
        matricula_periodo.aluno = aluno
        matricula_periodo.ano_letivo = aluno.ano_letivo
        matricula_periodo.periodo_letivo = aluno.periodo_letivo
        matricula_periodo.periodo_matriz = 1
        matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
        matricula_periodo.save()

        hsmp = HistoricoSituacaoMatriculaPeriodo()
        hsmp.matricula_periodo = matricula_periodo
        hsmp.situacao = matricula_periodo.situacao
        hsmp.data = aluno.data_matricula
        hsmp.save()

        return aluno


class EfetuarMatriculaTurmaForm(FormWizardPlus):
    METHOD = 'POST'
    LAST_SUBMIT_LABEL = 'Finalizar Matrícula em Turma'

    turma = forms.ModelChoiceField(Turma.objects, required=False, label='', widget=RenderableRadioSelect('widgets/turmas_widget.html'))

    steps = ([('Seleção da Turma', {'fields': ('turma',)})],)

    def __init__(self, aluno, *args, **kwargs):
        self.aluno = aluno
        super().__init__(*args, **kwargs)

    def first_step(self):
        self.fields['turma'].queryset = Turma.locals.filter(
            ano_letivo=self.aluno.ano_letivo, periodo_letivo=self.aluno.periodo_letivo, turno=self.aluno.turno, curso_campus=self.aluno.curso_campus, matriz=self.aluno.matriz
        )

    def next_step(self):
        pass

    def clean_turma(self):
        turma = self.cleaned_data.get('turma')
        if not turma:
            raise forms.ValidationError('Você deve selecionar uma turma.')
        else:
            return turma

    @transaction.atomic
    def processar(self, aluno):
        matricula_periodo = MatriculaPeriodo.objects.get(aluno=aluno)
        matricula_periodo.turma = self.cleaned_data['turma']
        matricula_periodo.save()

        for diario in matricula_periodo.turma.diario_set.all():
            if not MatriculaDiario.objects.filter(diario=diario, matricula_periodo=matricula_periodo).exists():
                matricula_diario = MatriculaDiario()
                matricula_diario.matricula_periodo = matricula_periodo
                matricula_diario.diario = diario
                matricula_diario.save()

        return matricula_periodo


class EfetuarMatriculasTurmaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Matricular Selecionados'
    matricula_periodo = forms.MultipleModelChoiceField(MatriculaPeriodo.objects, label='', widget=RenderableSelectMultiple('widgets/matriculas_periodo_widget.html'))

    def __init__(self, turma, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turma = turma
        self.fields['matricula_periodo'].queryset = MatriculaPeriodo.objects.filter(
            aluno__curso_campus=turma.curso_campus, periodo_letivo=turma.periodo_letivo, ano_letivo=turma.ano_letivo
        )

    def processar(self, commit=True):
        for matricula_periodo in self.cleaned_data['matricula_periodo']:
            matricula_periodo.turma = self.turma
            matricula_periodo.save()
            for diario in self.turma.diario_set.all():
                if not MatriculaDiario.objects.filter(matricula_periodo=matricula_periodo, diario=diario).exists():
                    matricula_diario = MatriculaDiario()
                    matricula_diario.matricula_periodo = matricula_periodo
                    matricula_diario.diario = diario
                    matricula_diario.save()


class ProcessarPeriodoLetivoForm(FormWizardPlus):
    FECHAMENTO_POR_MATRICULA = 'MATRICULA'
    FECHAMENTO_POR_TURMA = 'TURMA'
    FECHAMENTO_POR_CURSO = 'CURSO'
    FECHAMENTO_POR_DIARIO = 'DIARIO'
    TIPO_FECHAMENTO_CHOICES = [
        [FECHAMENTO_POR_MATRICULA, 'Por Matrícula'],
        [FECHAMENTO_POR_TURMA, 'Por Turma'],
        [FECHAMENTO_POR_CURSO, 'Por Curso'],
        [FECHAMENTO_POR_DIARIO, 'Por Diário'],
    ]

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)
    tipo = forms.ChoiceField(choices=TIPO_FECHAMENTO_CHOICES, widget=forms.RadioSelect())
    aluno = forms.ModelChoiceFieldPlus(Aluno.objects.none(), label='Matrícula', required=False)
    turma = forms.ModelChoiceFieldPlus(Turma.objects.none(), label='Turma', required=False)
    curso = forms.ModelChoiceFieldPlus(CursoCampus.objects.none(), label='Curso', required=False)
    diario = forms.ModelChoiceFieldPlus(Diario.objects.none(), label='Diário', required=False)
    forcar_fechamento = forms.BooleanField(
        label='Forçar fechamento?',
        help_text='Marque essa opção caso deseje que o diário seja fechado ainda que ele se encontre na posse do professor. Nesse caso, as notas pedentes serão computadas como zero e a posse do diário será transferida para o registro escolar.',
        required=False,
    )
    confirmado = forms.BooleanField(help_text='Marque a opção acima e em seguida clique no botão "Finalizar" para realizar o processamento do período para os diários listados.')

    class Media:
        js = ('/static/edu/js/FecharPeriodoLetivoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matriculas_periodo = []
        self.processado = False
        self.exibir_forcar_fechamento = False

    def first_step(self):
        if 'aluno' in self.fields:
            self.fields['aluno'].queryset = Aluno.locals.filter(matriz__isnull=False)
        if 'turma' in self.fields:
            self.fields['turma'].queryset = Turma.locals.filter(curso_campus__ativo=True)
        if 'curso' in self.fields:
            self.fields['curso'].queryset = CursoCampus.locals.filter(ativo=True)
        if 'diario' in self.fields:
            self.fields['diario'].queryset = Diario.locals.all()

    steps = (
        [('Fechar Período', {'fields': ('ano_letivo', 'periodo_letivo', 'tipo', 'aluno', 'turma', 'curso', 'diario')})],
        [('Confirmação dos Dados', {'fields': ('forcar_fechamento', 'confirmado')})],
    )

    def next_step(self):
        if self.get_entered_data('ano_letivo'):
            tipo = self.get_entered_data('tipo')
            matriculas_periodo = self.get_matriculas_periodo()
            if tipo == ProcessarPeriodoLetivoForm.FECHAMENTO_POR_MATRICULA and self.get_entered_data('aluno'):
                matriculas_periodo = matriculas_periodo.filter(aluno_id=self.get_entered_data('aluno').id)
                self.exibir_forcar_fechamento = self.get_entered_data('aluno').matriz.estrutura.permite_fechamento_com_pendencia
            elif tipo == ProcessarPeriodoLetivoForm.FECHAMENTO_POR_TURMA and self.get_entered_data('turma'):
                matriculas_periodo = matriculas_periodo.filter(matriculadiario__diario__turma_id=self.get_entered_data('turma').id)
                self.exibir_forcar_fechamento = self.get_entered_data('turma').matriz.estrutura.permite_fechamento_com_pendencia
            elif tipo == ProcessarPeriodoLetivoForm.FECHAMENTO_POR_CURSO and self.get_entered_data('curso'):
                matriculas_periodo = matriculas_periodo.filter(aluno__curso_campus_id=self.get_entered_data('curso').id)
                self.exibir_forcar_fechamento = False
            elif tipo == ProcessarPeriodoLetivoForm.FECHAMENTO_POR_DIARIO and self.get_entered_data('diario'):
                matriculas_periodo = matriculas_periodo.filter(matriculadiario__diario_id=self.get_entered_data('diario').id)
                self.exibir_forcar_fechamento = self.get_entered_data('diario').estrutura_curso.permite_fechamento_com_pendencia
            else:
                matriculas_periodo = MatriculaPeriodo.objects.none()
                self.exibir_forcar_fechamento = False
            self.matriculas_periodo = matriculas_periodo.order_by('id')

    def get_matriculas_periodo(self):
        qs = MatriculaPeriodo.objects.filter(
            ano_letivo_id=self.get_entered_data('ano_letivo').id, periodo_letivo=self.get_entered_data('periodo_letivo'), aluno__matriz__isnull=False
        ).order_by('id')
        qs = qs.exclude(aluno__matriz__estrutura__proitec=True).exclude(matriculadiarioresumida__isnull=False)
        return qs

    def get_diarios(self):
        diarios_ids = MatriculaDiario.objects.filter(matricula_periodo__in=self.matriculas_periodo).exclude(situacao__in=[6, 7, 8, 9]).values_list('diario', flat=True)
        return Diario.locals.filter(id__in=diarios_ids).distinct()


class FecharPeriodoLetivoForm(ProcessarPeriodoLetivoForm):
    METHOD = 'GET'

    @transaction.atomic
    def processar(self, request):
        return tasks.fechar_periodo(
            self.cleaned_data.get('confirmado'), self.cleaned_data['forcar_fechamento'], self.matriculas_periodo.distinct(), self.get_diarios(), request.META.get('QUERY_STRING', '')
        )

    def get_matriculas_periodo(self):
        return super().get_matriculas_periodo().filter(situacao=SituacaoMatriculaPeriodo.MATRICULADO)


class AbrirPeriodoLetivoForm(ProcessarPeriodoLetivoForm):
    METHOD = 'GET'
    steps = (
        [('Abrir Período', {'fields': ('ano_letivo', 'periodo_letivo', 'tipo', 'aluno', 'turma', 'curso', 'diario')})],
        [('Confirmação dos Dados', {'fields': ('confirmado',)})],
    )

    def get_matriculas_periodo(self):
        situacoes_periodo = []
        situacoes_periodo.append(SituacaoMatriculaPeriodo.MATRICULADO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.EM_ABERTO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.CANCELADA)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.TRANCADA)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.EVASAO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.JUBILADO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.INTERCAMBIO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.TRANSF_EXTERNA)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.TRANSF_CURSO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.TRANSF_INSTITUICAO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.TRANSF_TURNO)
        situacoes_periodo.append(SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL)
        situacoes_curso = []
        situacoes_curso.append(SituacaoMatricula.MATRICULADO)
        situacoes_curso.append(SituacaoMatricula.CONCLUIDO)
        situacoes_curso.append(SituacaoMatricula.NAO_CONCLUIDO)
        situacoes_curso.append(SituacaoMatricula.FORMADO)
        qs = (
            super()
            .get_matriculas_periodo()
            .filter(aluno__situacao__in=situacoes_curso)
            .exclude(situacao__in=situacoes_periodo)
            .exclude(aluno__registroemissaodiploma__isnull=False, aluno__registroemissaodiploma__cancelado=False)
        )
        qs_pedido = PedidoMatriculaDiario.objects.filter(data_processamento__isnull=True)
        if self.get_entered_data('aluno'):
            qs_pedido = qs_pedido.filter(pedido_matricula__matricula_periodo__aluno_id=self.get_entered_data('aluno').id)
        elif self.get_entered_data('turma'):
            qs_pedido = qs_pedido.filter(pedido_matricula__matricula_periodo__matriculadiario__diario__turma_id=self.get_entered_data('turma').id)
        elif self.get_entered_data('curso'):
            qs_pedido = qs_pedido.filter(pedido_matricula__matricula_periodo__aluno__curso_campus_id=self.get_entered_data('curso').id)
        elif self.get_entered_data('diario'):
            qs_pedido = qs_pedido.filter(pedido_matricula__matricula_periodo__matriculadiario__diario_id=self.get_entered_data('diario').id)
        qs_pedido = qs_pedido.values_list('pedido_matricula__matricula_periodo', flat=True).order_by('pedido_matricula__matricula_periodo').distinct()
        if qs_pedido.exists():
            return qs.exclude(pk__in=qs_pedido)
        return qs

    @transaction.atomic
    def processar(self, request):
        matriculas_periodo = self.matriculas_periodo.distinct()
        diarios = self.get_diarios()
        querystring = request.META.get('QUERY_STRING', '')
        # self.processado = True
        return tasks.abrir_periodo(diarios, matriculas_periodo, querystring)


class RelatorioForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    SITUACAO_SISTEMA_TODOS = 'TODOS'
    SITUACAO_SISTEMA_SUAP = 'SUAP'
    SITUACAO_SISTEMA_MIGRADOS = 'MIGRADOS'
    SITUACAO_SISTEMA_NAO_MIGRADOS = 'NAO_MIGRADOS'
    SITUACAO_SISTEMA_CHOICES = [
        [SITUACAO_SISTEMA_TODOS, 'Todos'],
        [SITUACAO_SISTEMA_SUAP, 'Alunos que iniciaram no SUAP'],
        [SITUACAO_SISTEMA_MIGRADOS, 'Alunos migrados do Q-Acadêmico'],
        [SITUACAO_SISTEMA_NAO_MIGRADOS, 'Alunos NÃO migrados do Q-Acadêmico'],
    ]

    uo = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.objects.campi().all(), label='Campus', required=False)
    diretoria = forms.ModelMultiplePopupChoiceField(Diretoria.objects, label='Diretoria', required=False)
    estrutura_curso = forms.ModelMultiplePopupChoiceField(EstruturaCurso.objects, label='Estrutura', required=False)
    modalidade = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidade', required=False)
    convenio = forms.ModelMultiplePopupChoiceField(Convenio.objects, label='Convênio', required=False)
    nivel_ensino = forms.ModelMultiplePopupChoiceField(NivelEnsino.objects, label='Nível de Ensino', required=False)
    matriz = forms.ModelChoiceFieldPlus(Matriz.objects, label='Matriz', required=False)
    curso_campus = forms.ModelChoiceFieldPlus(
        CursoCampus.objects, label='Curso', required=False, widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('uo', 'diretoria__setor__uo__in')])
    )
    situacao_matricula = forms.ModelMultiplePopupChoiceField(SituacaoMatricula.objects, label='Situação da Matrícula', required=False)

    turma = forms.MultipleModelChoiceField(
        Turma.objects,
        label='Turma',
        required=False,
        widget=AutocompleteWidget(
            search_fields=Turma.SEARCH_FIELDS,
            multiple=True,
            form_filters=[('curso_campus', 'curso_campus'), ('uo', 'curso_campus__diretoria__setor__uo__in'), ('polo', 'polo__in')],
        ),
    )

    diario_da_turma = forms.ModelChoiceFieldPlus(
        Turma.objects,
        label='Em diário da Turma',
        required=False,
        widget=AutocompleteWidget(
            search_fields=Turma.SEARCH_FIELDS, form_filters=[('curso_campus', 'curso_campus'), ('uo', 'curso_campus__diretoria__setor__uo__in'), ('polo', 'polo__in')]
        ),
    )

    diario = forms.MultipleModelChoiceField(
        Diario.objects,
        label='Diário',
        required=False,
        widget=AutocompleteWidget(
            search_fields=Diario.SEARCH_FIELDS,
            multiple=True,
            form_filters=[
                ('turma', 'turma'),
                ('uo', 'turma__curso_campus__diretoria__setor__uo__in'),
                ('polo', 'turma__polo__in'),
                ('curso_campus', 'turma__curso_campus'),
                ('estrutura_curso', 'turma__matriz__estrutura__in'),
                ('modalidade', 'turma__curso_campus__modalidade__in'),
            ],
        ),
    )

    estado = forms.ModelChoiceFieldPlus(Estado.objects, label='Estado', required=False, widget=AutocompleteWidget(search_fields=Estado.SEARCH_FIELDS))
    cidade = forms.ModelChoiceFieldPlus(
        Cidade.objects, label='Cidade', required=False, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS, form_filters=[('estado', 'estado')])
    )

    situacao_matricula_periodo = forms.ModelMultiplePopupChoiceField(SituacaoMatriculaPeriodo.objects, label='Situação no Período', required=False)
    situacao_diario = forms.ChoiceField(choices=[[0, '----']] + MatriculaDiario.SITUACAO_CHOICES, label='Situação no Diário', required=False)
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=False)
    periodo_letivo = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False)
    periodo_referencia = forms.ChoiceField(label='Período de Referência Atual', required=False, choices=[[0, '----']] + [[x, x] for x in range(1, 11)])
    periodo_matriz = forms.ChoiceField(label='Período da Matriz', required=False, choices=[[0, '----']] + [[x, x] for x in range(1, 11)])
    aluno_especial = forms.ChoiceField(choices=[['', '----']] + Aluno.TIPO_ALUNO_CHOICES, required=False, label='Tipo de Aluno')

    ano_ingresso_inicio = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano de Ingresso a Partir de', required=False)
    ano_ingresso_fim = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano de Ingresso Até', required=False)
    periodo_ingresso_inicio = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período de Ingresso a Partir de', required=False)
    periodo_ingresso_fim = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período de Ingresso Até', required=False)

    forma_ingresso = forms.ModelPopupChoiceField(FormaIngresso.objects, label='Forma de Ingresso', required=False)
    polo = forms.ModelMultiplePopupChoiceField(Polo.objects, label='Polo', required=False)
    situacao_sistema = forms.ChoiceField(choices=SITUACAO_SISTEMA_CHOICES, label='Situação no Sistema', required=False)

    medida_disciplinar = forms.ChoiceField(choices=[], label='Medida Disciplinar', required=False)

    tipo_necessidade_especial = forms.ChoiceField(
        choices=[[0, '---------'], ['TODAS', 'Todas']] + Aluno.TIPO_NECESSIDADE_ESPECIAL_CHOICES, label='Tipo de Necessidade Especial', required=False
    )
    tipo_transtorno = forms.ChoiceField(choices=[[0, '---------'], ['TODAS', 'Todas']] + Aluno.TIPO_TRANSTORNO_CHOICES, label='Tipo de Transtorno', required=False)
    superdotacao = forms.ChoiceField(choices=[[0, '---------'], ['TODAS', 'Todas']] + Aluno.SUPERDOTACAO_CHOICES, label='Superdotação', required=False)
    todos_tipos_de_ne = forms.BooleanField(
        label='Todos os Tipos', required=False, initial=False, help_text="Pesquisa por Todos os Tipos de Deficiência, Transtorno ou Superdotação"
    )

    ano_conclusao = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano de Conclusão', required=False)

    turno = forms.ModelChoiceField(Turno.objects, label='Turno', required=False)

    percentual_conclusao_curso_inicial = forms.IntegerField(label='Percentual de Progresso Inicial', max_value=100, min_value=0, required=False)
    percentual_conclusao_curso_final = forms.IntegerField(label='Percentual de Progresso Final', max_value=100, min_value=0, required=False)

    formatacao = forms.ChoiceField(
        choices=[
            ['simples', 'Listagem Simples'],
            ['educacenso', 'Relatório Educacenso'],
            ['censup', 'Relatório Censup'],
            ['tcc', 'Relatório de TCCs'],
            ['pordisciplinacursando', 'Relatório de Disciplinas Cursando'],
            ['pordisciplinapendente', 'Relatório de Disciplinas Pendentes'],
        ],
        label='Tipo',
        help_text='O tipo de formatação "Listagem Simples" permitirá a impressão de etiquetas, carômetros e assinatura dos alunos.',
    )
    quantidade_itens = forms.ChoiceField(choices=[[25, '25'], [50, '50'], [100, '100'], [200, '200'], [500, '500']], label='Quantidade de Itens')
    ordenacao = forms.ChoiceField(choices=[['Nome', 'Nome'], ['Matrícula', 'Matrícula']], label='Ordenação')
    agrupamento = forms.ChoiceField(choices=[['Campus', 'Campus'], ['Curso', 'Curso'], ['Turma', 'Turma']], label='Agrupamento')
    EXIBICAO_CHOICES = [
        ['curso_campus.diretoria.setor.uo', 'Campus'],
        ['curso_campus.codigo', 'Código Curso'],
        ['curso_campus.descricao', 'Descrição do Curso'],
        ['situacao', 'Situação no Curso'],
        ['get_situacao_periodo_referencia', 'Situação no Período'],
        ['get_frequencia_periodo_referencia', 'Frequência no Período'],
        ['get_ultima_matricula_periodo.turma', 'Turma'],
        ['pessoa_fisica.email', 'Email Acadêmico'],
        ['email_google_classroom', 'Email Google Classroom'],
        ['polo', 'Polo'],
        ['nacionalidade', 'Nacionalidade'],
        ['pais_origem', 'País de Origem'],
        ['ano_letivo', 'Ano de Ingresso'],
        ['periodo_letivo', 'Período de Ingresso'],
        ['data_matricula', 'Data de Matrícula'],
        ['turno', 'Turno'],
        ['forma_ingresso', 'Forma de Ingresso'],
        ['cota_sistec', 'Cota Sistec'],
        ['cota_mec', 'Cota MEC'],
        ['convenio', 'Convênio'],
        ['data_conclusao_intercambio', 'Data de Conclusão do Intercâmbio'],
        ['matriz', 'Matriz'],
        ['dt_conclusao_curso', 'Data de Conclusão de Curso'],
        ['ano_let_prev_conclusao', 'Ano Letivo de Previsão de Conclusão'],
        ['tipo_instituicao_origem', 'Tipo de Escola de Origem'],
        ['periodo_atual', 'Período Atual'],
        ['data_integralizacao', 'Data de Integralização'],
        ['ano_letivo_integralizacao', 'Ano Letivo de Integralização'],
        ['periodo_letivo_integralizacao', 'Período Letivo de Integralização'],
        ['pendencias', 'Pendências de Requisitos de Conclusão'],
        ['pessoa_fisica.raca', 'Etnia/Raça'],
        ['codigo_educacenso', 'Código Educacenso'],
        ['get_data_ultimo_procedimento_periodo_referencia', 'Data do Último Procedimento'],
        ['curso_campus.diretoria', 'Diretoria'],
        ['numero_pasta', 'Nº da Pasta'],
        ['curso_campus.modalidade', 'Modalidade'],
        ['curso_campus.modalidade.nivel_ensino', 'Nível de Ensino'],
        ['get_poder_publico_responsavel_transporte_display', 'Transporte Escolar: Poder Público'],
        ['percentual_ch_cumprida', 'Percentual de Progresso'],
        ['get_tipo_veiculo_display', 'Transporte Escolar: Tipo de Veículo'],
        ['get_projeto_final_aprovado.data_defesa', 'Data da Defesa do TCC'],
        ['curso_campus.natureza_participacao', 'Natureza de Participação'],
        ['candidato_vaga.candidato.edital', 'Edital de Ingresso'],
        ['ano_conclusao', 'Ano de Conclusão'],
    ]

    EXIBICAO_COMUNICACAO = [['pessoa_fisica.email_secundario', 'Email Pessoal']]

    EXIBICAO_DADOS_PESSOAIS = [
        ['pessoa_fisica.cpf', 'CPF'],
        ['pessoa_fisica.nascimento_data', 'Data de Nascimento'],
        ['get_endereco', 'Endereço'],
        ['cidade', 'Município de Residência'],
        ['cidade.codigo', 'Município de Residência (Código IBGE)'],
        ['get_rg', 'RG'],
        ['get_telefones', 'Telefone'],
        ['pessoa_fisica.sexo', 'Sexo'],
        ['estado_civil', 'Estado Civil'],
        ['nome_pai', 'Nome do Pai'],
        ['nome_mae', 'Nome da Mãe'],
        ['responsavel', 'Responsável'],
        ['email_responsavel', 'Email do Responsável'],
        ['naturalidade', 'Naturalidade'],
        ['naturalidade.codigo', 'Naturalidade (Código IBGE)'],
        ['ira', 'I.R.A.'],
        ['caracterizacao.renda_per_capita', 'Renda Per Capita'],
        ['observacao_historico', 'Observação Histórico'],
        ['cidade.nome', 'Cidade'],
        ['get_tipo_necessidade_especial_display', 'Deficiência'],
        ['get_tipo_transtorno_display', 'Transtorno'],
        ['get_superdotacao_display', 'Superdotação'],
        ['cidade.estado.get_sigla', 'Estado'],
        ['get_chave_responsavel', 'Chave do Responsável'],
        ['get_observacoes', 'Observações'],
        ['get_tipo_zona_residencial_display', 'Zona Residencial'],
    ]

    EXIBICAO_INICIAS = [
        ['curso_campus.diretoria.setor.uo', 'Campus'],
        ['curso_campus.codigo', 'Código Curso'],
        ['curso_campus.descricao', 'Descrição do Curso'],
        ['situacao', 'Situação no Curso'],
        ['get_situacao_periodo_referencia', 'Situação no Período'],
        ['tipo_instituicao_origem', 'Tipo de Escola de Origem'],
    ]

    PENDENCIAS_EXIBICAO_CHOICES = [
        ('pendencia_pratica_profissional', 'Prática Profissional Pendente'),
        ('pendencia_colacao_grau', 'Colação de Grau Pendente'),
        ('pendencia_ch_atividade_complementar', 'Atividades Complementares Pendente'),
        ('pendencia_ch_tcc', 'Carga Horária de TCC Pendente'),
        ('pendencia_ch_pratica_profissional', 'Carga Horária de Prática Profissional Pendente'),
        ('pendencia_tcc', 'Registro de TCC Pendente'),
        ('pendencia_ch_seminario', 'Carga Horária de Seminário Pendente'),
        ('pendencia_ch_eletiva', 'Carga Horária Eletiva Pendente'),
        ('pendencia_ch_optativa', 'Carga Horária Optativa Pendente'),
        ('pendencia_ch_obrigatoria', 'Carga Horária Obrigatória Pendente'),
        ('pendencia_enade', 'Registro do ENADE'),
    ]

    exibicao = forms.MultipleChoiceField(label="Campos Adicionais", choices=[], widget=CheckboxSelectMultiplePlus(), required=False)

    PENDENCIA_CHOICES = [
        ('colacao_grau', 'Colação de Grau'),
        ('pratica_profissional', 'Prática Profissional'),
        ('tcc', 'Trabalho de conclusão de curso - TCC'),
        ('seminarios', 'Carga Horária de Seminário'),
        ('disciplinas_optativa', 'Carga Horária Optativa'),
        ('enad', 'Registro de ENADE'),
        ('atividades_complementares', 'Atividades Complementares'),
    ]

    pendencias = forms.ChoiceField(label='Requisitos de Conclusão Pendentes (apenas)', choices=[('', '--------------')] + PENDENCIA_CHOICES, required=False)

    fieldsets = (
        (
            'Filtros de Pesquisa',
            {
                'fields': (
                    ('uo', 'diretoria'),
                    ('estrutura_curso', 'modalidade'),
                    ('convenio', 'polo'),
                    ('estado', 'cidade'),
                    ('matriz', 'curso_campus'),
                    ('turma', 'diario', 'diario_da_turma'),
                    ('ano_letivo', 'periodo_letivo', 'periodo_matriz'),
                    ('periodo_referencia', 'ano_conclusao'),
                    ('situacao_diario', 'turno'),
                    ('situacao_matricula', 'situacao_matricula_periodo'),
                    ('ano_ingresso_inicio', 'periodo_ingresso_inicio'),
                    ('ano_ingresso_fim', 'periodo_ingresso_fim'),
                    ('aluno_especial', 'forma_ingresso'),
                    ('situacao_sistema', 'medida_disciplinar'),
                )
            },
        ),
        ('Percentual de Progresso', {'fields': (('percentual_conclusao_curso_inicial', 'percentual_conclusao_curso_final'),)}),
        ('Deficiências, Transtornos e Superdotação', {'fields': (('todos_tipos_de_ne'), ('tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao'))}),
        ('Requisitos de Conclusão', {'fields': ('pendencias',)}),
        ('Formatação', {'fields': ('formatacao', ('quantidade_itens', 'ordenacao', 'agrupamento'))}),
        ('Exibição', {'fields': (('exibicao',),)}),
    )

    class Media:
        js = ('/static/edu/js/RelatorioForm.js',)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pessoa_fisica = request.user.get_profile()
        uo = None
        if pessoa_fisica and hasattr(pessoa_fisica, 'funcionario'):
            if pessoa_fisica.funcionario and pessoa_fisica.funcionario.setor:
                uo = pessoa_fisica.funcionario.setor.uo

        if uo and not in_group(request.user, 'Administrador Acadêmico'):
            self.fields['uo'].initial = [uo.pk]

        exibicao_final_choices = []
        exibicao_final_choices.extend(self.EXIBICAO_CHOICES)
        if request.user.has_perm('edu.view_dados_pessoais'):
            exibicao_final_choices.extend(self.EXIBICAO_DADOS_PESSOAIS)

        if in_group(
            request.user,
            'Assistente Social, Coordenador de Atividades Estudantis, Coordenador de Atividades Estudantis Sistêmico, Coordenador de Curso,Administrador Acadêmico,Secretário Acadêmico,Diretor Acadêmico, Pedagogo',
        ):
            exibicao_final_choices.extend(self.EXIBICAO_COMUNICACAO)

        self.fields['exibicao'].choices = sorted(exibicao_final_choices, key=itemgetter(1))
        self.fields['exibicao'].initial = [campo[0] for campo in self.EXIBICAO_INICIAS]

        self.fields['curso_campus'].queryset = self.fields['curso_campus'].queryset.all()
        self.fields['situacao_matricula'].queryset = self.fields['situacao_matricula'].queryset.exclude(
            pk__in=(
                SituacaoMatricula.AGUARDANDO_COLACAO_DE_GRAU,
                SituacaoMatricula.CERTIFICADO_ENEM,
                SituacaoMatricula.AGUARDANDO_SEMINARIO,
                SituacaoMatricula.AGUARDANDO_ENADE,
                SituacaoMatricula.TRANSFERIDO_SUAP,
            )
        )

        if request.user.has_perm('edu.view_medidadisciplinar'):
            self.fields['medida_disciplinar'].choices = [[0, '---------'], ['TODOS', 'Todos']] + [[tipo.pk, tipo.descricao] for tipo in TipoMedidaDisciplinar.objects.all()]
        else:
            self.fields['medida_disciplinar'].widget = forms.HiddenInput()

        formatacao_choices = []
        for choice in self.fields['formatacao'].choices:
            _, valor = choice
            if 'Resumo' in valor:
                if request.user.is_superuser or in_group(request.user, 'Administrador Acadêmico'):
                    formatacao_choices.append(choice)
            else:
                formatacao_choices.append(choice)
        self.fields['formatacao'].choices = formatacao_choices

    def get_periodo(self):
        ano_letivo = self.cleaned_data['ano_letivo']
        periodo_letivo = self.cleaned_data['periodo_letivo'] or 0
        if ano_letivo and int(periodo_letivo):
            return [ano_letivo, periodo_letivo]

    def processar(self):
        qs = MatriculaPeriodo.objects.exclude(aluno__turmaminicurso__gerar_matricula=False)

        uo = self.cleaned_data['uo']
        diretoria = self.cleaned_data['diretoria']
        estrutura_curso = self.cleaned_data['estrutura_curso']
        modalidade = self.cleaned_data['modalidade']
        convenio = self.cleaned_data['convenio']
        matriz = self.cleaned_data['matriz']
        curso_campus = self.cleaned_data['curso_campus']
        diario = self.cleaned_data['diario']
        situacao_matricula = self.cleaned_data['situacao_matricula']
        turma = self.cleaned_data['turma']
        diario_da_turma = self.cleaned_data['diario_da_turma']
        cidade = self.cleaned_data['cidade']
        estado = self.cleaned_data['estado']
        situacao_matricula_periodo = self.cleaned_data['situacao_matricula_periodo']
        percentual_conclusao_curso_inicial = self.cleaned_data['percentual_conclusao_curso_inicial']
        percentual_conclusao_curso_final = self.cleaned_data['percentual_conclusao_curso_final']
        situacao_diario = self.cleaned_data['situacao_diario'] or 0
        ano_letivo = self.cleaned_data['ano_letivo']
        periodo_letivo = self.cleaned_data['periodo_letivo'] or 0
        ano_ingresso_inicio = self.cleaned_data['ano_ingresso_inicio']
        ano_ingresso_fim = self.cleaned_data['ano_ingresso_fim']
        periodo_ingresso_inicio = self.cleaned_data['periodo_ingresso_inicio'] or 0
        periodo_ingresso_fim = self.cleaned_data['periodo_ingresso_fim'] or 0
        periodo_referencia = self.cleaned_data['periodo_referencia'] or 0
        periodo_matriz = self.cleaned_data['periodo_matriz'] or 0
        forma_ingresso = self.cleaned_data['forma_ingresso']
        turno = self.cleaned_data['turno']
        polo = self.cleaned_data['polo']
        aluno_especial = self.cleaned_data['aluno_especial']
        situacao_sistema = self.cleaned_data['situacao_sistema']
        medida_disciplinar = self.cleaned_data['medida_disciplinar']
        todos_tipos_de_ne = self.cleaned_data['todos_tipos_de_ne']
        tipo_necessidade_especial = self.cleaned_data['tipo_necessidade_especial']
        tipo_transtorno = self.cleaned_data['tipo_transtorno']
        superdotacao = self.cleaned_data['superdotacao']
        ano_conclusao = self.cleaned_data['ano_conclusao']
        pendencias = self.cleaned_data['pendencias']
        filtros = []

        if uo:
            qs = qs.filter(aluno__curso_campus__diretoria__setor__uo__in=uo)
            filtros.append(dict(chave='Campus', valor=format_iterable(uo)))
        if diretoria:
            qs = qs.filter(aluno__curso_campus__diretoria__in=diretoria)
            filtros.append(dict(chave='Diretoria', valor=format_iterable(diretoria)))
        if estrutura_curso:
            qs = qs.filter(aluno__matriz__estrutura__id__in=estrutura_curso)
            filtros.append(dict(chave='Estrutura de Curso', valor=format_iterable(estrutura_curso)))
        if modalidade:
            qs = qs.filter(aluno__curso_campus__modalidade__id__in=modalidade)
            filtros.append(dict(chave='Modalidade', valor=format_iterable(modalidade)))
        if convenio:
            qs = qs.filter(aluno__convenio__id__in=convenio)
            filtros.append(dict(chave='Convênio', valor=format_iterable(convenio)))
        if situacao_matricula:
            qs = qs.filter(aluno__situacao__id__in=situacao_matricula)
            filtros.append(dict(chave='Situação no Curso', valor=format_iterable(situacao_matricula)))
        if matriz:
            qs = qs.filter(aluno__matriz=matriz)
            filtros.append(dict(chave='Matriz', valor=str(matriz)))
        if curso_campus:
            qs = qs.filter(aluno__curso_campus=curso_campus)
            filtros.append(dict(chave='Curso', valor=str(curso_campus)))
        if diario:
            qs = qs.filter(matriculadiario__diario__in=diario)
            filtros.append(dict(chave='Diário', valor=format_iterable(diario)))
        if turma:
            qs = qs.filter(turma__in=turma)
            filtros.append(dict(chave='Turma', valor=format_iterable(turma)))
        if diario_da_turma:
            qs = qs.filter(aluno__curso_campus__ativo=True, matriculadiario__diario__turma=diario_da_turma).exclude(matriculadiario__situacao=MatriculaDiario.SITUACAO_TRANSFERIDO)
            filtros.append(dict(chave='Em diário da Turma', valor=str(diario_da_turma)))
        if cidade:
            qs = qs.filter(aluno__cidade=cidade)
            filtros.append(dict(chave='Cidade', valor=str(cidade)))
        if estado:
            qs = qs.filter(aluno__cidade__estado=estado)
            filtros.append(dict(chave='Estado', valor=str(estado)))
        if situacao_matricula_periodo:
            qs = qs.filter(situacao__id__in=situacao_matricula_periodo)
            filtros.append(dict(chave='Situação no Período', valor=format_iterable(situacao_matricula_periodo)))
        if (percentual_conclusao_curso_inicial and percentual_conclusao_curso_inicial >= 0) or (percentual_conclusao_curso_final and percentual_conclusao_curso_final <= 100):
            percentual_conclusao_curso_inicial = percentual_conclusao_curso_inicial or 0
            percentual_conclusao_curso_final = percentual_conclusao_curso_final or 100
            qs = qs.filter(aluno__percentual_ch_cumprida__gte=percentual_conclusao_curso_inicial, aluno__percentual_ch_cumprida__lte=percentual_conclusao_curso_final)
            filtros.append(dict(chave='Percentual de Progresso', valor=f'{percentual_conclusao_curso_inicial}% a {percentual_conclusao_curso_final}% '))
        if int(situacao_diario):
            qs = qs.filter(aluno__curso_campus__ativo=True, matriculadiario__situacao=situacao_diario)
            filtros.append(dict(chave='Situação no Diário', valor=str(situacao_diario)))
        if ano_letivo:
            qs = qs.filter(ano_letivo=ano_letivo)
            filtros.append(dict(chave='Ano Letivo', valor=str(ano_letivo)))
        if int(periodo_letivo):
            qs = qs.filter(periodo_letivo=periodo_letivo)
            filtros.append(dict(chave='Período Letivo', valor=str(periodo_letivo)))
        if int(periodo_matriz):
            qs = qs.filter(periodo_matriz=periodo_matriz)
            filtros.append(dict(chave='Período da Matriz', valor=str(periodo_matriz)))
        if ano_conclusao:
            qs = qs.filter(aluno__ano_conclusao=ano_conclusao.ano)
            filtros.append(dict(chave='Ano de Conclusão', valor=str(ano_conclusao)))
        if int(periodo_referencia):
            qs = qs.filter(aluno__periodo_atual=periodo_referencia)
            filtros.append(dict(chave='Período de Referência', valor=str(periodo_referencia)))
        if ano_ingresso_inicio:
            qs = qs.filter(aluno__ano_letivo__gte=ano_ingresso_inicio)
            filtros.append(dict(chave='Ano de Ingresso a Partir de', valor=str(ano_ingresso_inicio)))
            if int(periodo_ingresso_inicio) == 2:
                qs = qs.exclude(aluno__ano_letivo=ano_ingresso_inicio, aluno__periodo_letivo=1)
            if int(periodo_ingresso_inicio) != 0:
                filtros.append(dict(chave='Período de Ingresso a Partir de', valor=int(periodo_ingresso_inicio)))
        if ano_ingresso_fim:
            qs = qs.filter(aluno__ano_letivo__lte=ano_ingresso_fim)
            filtros.append(dict(chave='Ano de Ingresso Até', valor=str(ano_ingresso_fim)))
            if int(periodo_ingresso_fim) == 1:
                qs = qs.exclude(aluno__ano_letivo=ano_ingresso_fim, aluno__periodo_letivo=2)
            if int(periodo_ingresso_fim) != 0:
                filtros.append(dict(chave='Período de Ingresso Até', valor=int(periodo_ingresso_fim)))
        if forma_ingresso:
            qs = qs.filter(aluno__forma_ingresso=forma_ingresso)
            filtros.append(dict(chave='Forma de Ingresso', valor=str(forma_ingresso)))
        if turno:
            qs = qs.filter(aluno__turno=turno)
            filtros.append(dict(chave='Turno', valor=str(turno)))
        if polo:
            qs = qs.filter(aluno__polo__in=polo)
            filtros.append(dict(chave='Polo', valor=format_iterable(polo)))
        if aluno_especial:
            if aluno_especial == 'Especial':
                qs = qs.filter(aluno__aluno_especial=True)
            if aluno_especial == 'Regular':
                qs = qs.filter(aluno__aluno_especial=False)
            filtros.append(dict(chave='Aluno Especial', valor=format_(aluno_especial)))
        if situacao_sistema and not situacao_sistema == self.SITUACAO_SISTEMA_TODOS:
            if situacao_sistema == self.SITUACAO_SISTEMA_SUAP:
                qs = qs.filter(aluno__matriz__isnull=False, aluno__data_integralizacao__isnull=True)
                filtros.append(dict(chave='Situação no Sistema', valor="Alunos que iniciaram no SUAP"))
            elif situacao_sistema == self.SITUACAO_SISTEMA_MIGRADOS:
                qs = qs.filter(aluno__matriz__isnull=False, aluno__data_integralizacao__isnull=False)
                filtros.append(dict(chave='Situação no Sistema', valor="Alunos migrados do Q-Acadêmico"))
            elif situacao_sistema == self.SITUACAO_SISTEMA_NAO_MIGRADOS:
                qs = qs.filter(aluno__matriz__isnull=True, aluno__data_integralizacao__isnull=True)
                filtros.append(dict(chave='Situação no Sistema', valor="Alunos NÃO migrados do Q-Acadêmico"))

        if medida_disciplinar and medida_disciplinar != '0':
            if medida_disciplinar == 'TODOS':
                qs = qs.filter(aluno__medidadisciplinar__isnull=False)
            else:
                qs = qs.filter(aluno__medidadisciplinar__tipo=medida_disciplinar)
            filtros.append(dict(chave='Medida Disciplinar', valor=format_(medida_disciplinar)))

        if todos_tipos_de_ne:
            qs_nee = []
            qs_nee.append(Q(aluno__tipo_necessidade_especial__in=[a[0] for a in Aluno.TIPO_NECESSIDADE_ESPECIAL_CHOICES]))
            qs_nee.append(Q(aluno__tipo_transtorno__in=[a[0] for a in Aluno.TIPO_TRANSTORNO_CHOICES]))
            qs_nee.append(Q(aluno__superdotacao__in=[a[0] for a in Aluno.SUPERDOTACAO_CHOICES]))
            qs = qs.filter(reduce(operator.or_, qs_nee)).distinct()
            filtros.append(dict(chave='Tipos de Deficiências, Transtornos e Superdotação', valor='Todos'))
        else:
            if tipo_necessidade_especial and tipo_necessidade_especial != '0':
                if tipo_necessidade_especial == 'TODAS':
                    qs = qs.filter(aluno__tipo_necessidade_especial__in=[a[0] for a in Aluno.TIPO_NECESSIDADE_ESPECIAL_CHOICES])
                else:
                    qs = qs.filter(aluno__tipo_necessidade_especial=tipo_necessidade_especial)
                instance = Aluno.objects.filter(tipo_necessidade_especial=tipo_necessidade_especial).first()
                valor = instance and instance.get_tipo_necessidade_especial_display() or 'Todos'
                filtros.append(dict(chave='Tipo de Necessidade Especial', valor=valor))

            if tipo_transtorno and tipo_transtorno != '0':
                if tipo_transtorno == 'TODAS':
                    qs = qs.filter(aluno__tipo_transtorno__in=[a[0] for a in Aluno.TIPO_TRANSTORNO_CHOICES])
                else:
                    qs = qs.filter(aluno__tipo_transtorno=tipo_transtorno)
                instance = Aluno.objects.filter(tipo_transtorno=tipo_transtorno).first()
                valor = instance and instance.get_tipo_transtorno_display() or 'Todos'
                filtros.append(dict(chave='Tipo de Transtorno', valor=valor))

            if superdotacao and superdotacao != '0':
                if superdotacao == 'TODAS':
                    qs = qs.filter(aluno__superdotacao__in=[a[0] for a in Aluno.SUPERDOTACAO_CHOICES])
                else:
                    qs = qs.filter(aluno__superdotacao=superdotacao)
                instance = Aluno.objects.filter(superdotacao=superdotacao).first()
                valor = instance and instance.get_superdotacao_display() or 'Todos'
                filtros.append(dict(chave='Superdotação', valor=valor))

        if pendencias:
            d = dict(
                aluno__pendencia_tcc=True,
                aluno__pendencia_enade=True,
                aluno__pendencia_pratica_profissional=True,
                aluno__pendencia_colacao_grau=True,
                aluno__pendencia_ch_atividade_complementar=True,
                aluno__pendencia_ch_tcc=True,
                aluno__pendencia_ch_pratica_profissional=True,
                aluno__pendencia_ch_seminario=True,
                aluno__pendencia_ch_eletiva=True,
                aluno__pendencia_ch_optativa=True,
                aluno__pendencia_ch_obrigatoria=True,
            )
            if pendencias == 'colacao_grau':
                del d['aluno__pendencia_colacao_grau']
                qs1 = qs.filter(aluno__situacao=SituacaoMatricula.AGUARDANDO_COLACAO_DE_GRAU)
                qs2 = qs.exclude(aluno__situacao=SituacaoMatricula.AGUARDANDO_COLACAO_DE_GRAU)
                for lookup in d:
                    qs2 = qs2.exclude(**{lookup: True})
                qs2 = qs2.filter(aluno__pendencia_colacao_grau=True)
                qs = qs1 | qs2
                pendencias = 'Aguardando colação de grau'
            elif pendencias == 'pratica_profissional':
                del d['aluno__pendencia_colacao_grau']
                del d['aluno__pendencia_ch_pratica_profissional']
                del d['aluno__pendencia_pratica_profissional']
                for lookup in d:
                    qs = qs.exclude(**{lookup: True})
                qs = qs.filter(aluno__pendencia_ch_pratica_profissional=True) | qs.filter(aluno__pendencia_pratica_profissional=True)
                pendencias = 'Prática profissional pendente'
            elif pendencias == 'tcc':
                del d['aluno__pendencia_colacao_grau']
                del d['aluno__pendencia_tcc']
                del d['aluno__pendencia_ch_tcc']
                for lookup in d:
                    qs = qs.exclude(**{lookup: True})
                qs = qs.filter(aluno__pendencia_tcc=True) | qs.filter(aluno__pendencia_ch_tcc=True)
                pendencias = 'Trabalho de conclusão de curso (TCC) endente'
            elif pendencias == 'seminarios':
                del d['aluno__pendencia_colacao_grau']
                del d['aluno__pendencia_ch_seminario']
                qs1 = qs.filter(aluno__situacao=SituacaoMatricula.AGUARDANDO_SEMINARIO)
                qs2 = qs.exclude(aluno__situacao=SituacaoMatricula.AGUARDANDO_SEMINARIO)
                for lookup in d:
                    qs2 = qs2.exclude(**{lookup: True})
                qs2 = qs2.filter(aluno__pendencia_ch_seminario=True)
                qs = qs1 | qs2
                pendencias = 'Seminários pendentes'
            elif pendencias == 'disciplinas_optativa':
                del d['aluno__pendencia_colacao_grau']
                del d['aluno__pendencia_ch_optativa']
                for lookup in d:
                    qs = qs.exclude(**{lookup: True})
                qs = qs.filter(aluno__pendencia_ch_optativa=True)
                pendencias = 'Carga horária de disciplinas optativas pendentes'
            elif pendencias == 'enad':
                del d['aluno__pendencia_colacao_grau']
                del d['aluno__pendencia_enade']
                qs1 = qs.filter(aluno__situacao=SituacaoMatricula.AGUARDANDO_ENADE)
                qs2 = qs.exclude(aluno__situacao=SituacaoMatricula.AGUARDANDO_ENADE)
                for lookup in d:
                    qs2 = qs2.exclude(**{lookup: True})
                qs2 = qs2.filter(aluno__pendencia_enade=True)
                qs = qs1 | qs2
                pendencias = 'Registro de participação/dispensa do ENAD pendente'
            elif pendencias == 'atividades_complementares':
                del d['aluno__pendencia_colacao_grau']
                del d['aluno__pendencia_ch_atividade_complementar']
                for lookup in d:
                    qs = qs.exclude(**{lookup: True})
                qs = qs.filter(aluno__pendencia_ch_atividade_complementar=True)
                pendencias = 'Carga horária de atividades complementares pendentes'
            filtros.append(dict(chave='Pendências', valor=pendencias))

        # open('/tmp/query.txt', 'w').write(str(qs.query))
        alunos = Aluno.objects.filter(id__in=qs.order_by('aluno__id').values_list('aluno__id', flat=True).distinct())

        ordenacao = ['curso_campus__diretoria__setor__uo', 'curso_campus']
        if self.cleaned_data.get('ordenacao') == 'Matrícula':
            ordenacao.append('matricula')
        if self.cleaned_data.get('ordenacao') == 'Nome':
            ordenacao.append('pessoa_fisica__nome')

        alunos = alunos.order_by(*ordenacao).select_related('curso_campus', 'curso_campus__diretoria__setor__uo', 'pessoa_fisica')

        alunos.filtros = filtros
        return alunos


class RelatorioDependenteForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    PERIODO_CURSO_CHOICES = [[x, x] for x in range(1, 13)]

    curso_campus = forms.ModelChoiceFieldPlus(
        CursoCampus.locals,
        label='Curso',
        required=False,
        widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[
            ('diretoria', 'diretoria')
        ]),
    )
    periodo_matriz = forms.ChoiceField(choices=[[0, '----']] + PERIODO_CURSO_CHOICES, label='Período da Matriz', required=False)

    diretoria = forms.ModelChoiceFieldPlus(Diretoria.objects.none(), label='Diretoria', required=False)
    turma = forms.ModelChoiceFieldPlus(
        Turma.objects,
        label='Turma',
        required=False,
        widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS, form_filters=[
            ('diretoria', 'curso_campus__diretoria'),
            ('curso_campus', 'curso_campus')
        ])
    )

    diario = forms.ModelChoiceFieldPlus(
        Diario.objects,
        label='Diário',
        required=False,
        widget=AutocompleteWidget(search_fields=Diario.SEARCH_FIELDS, form_filters=[
            ('diretoria', 'turma__curso_campus__diretoria'),
            ('curso_campus', 'turma__curso_campus'),
            ('turma', 'turma')
        ]),
        help_text='Para encontrar um diário entre com a sigla do componente ou o código do diário.',
    )

    componente = forms.ModelChoiceFieldPlus(
        Componente.objects, label='Componente', required=False, widget=AutocompleteWidget(search_fields=Componente.SEARCH_FIELDS, form_filters=[('uo', 'diretoria__setor__uo__in')])
    )

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo')
    situacao = forms.MultipleModelChoiceField(SituacaoMatriculaPeriodo.objects, label='Situação no Período', required=False, initial=[SituacaoMatriculaPeriodo.DEPENDENCIA])

    fieldsets = (
        ('Período', {'fields': (('ano_letivo', 'periodo_letivo'), ('situacao', 'periodo_matriz'))}),
        ('Filtros de Pesquisa', {'fields': ('diretoria', 'curso_campus', 'turma', 'diario', 'componente')}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['situacao'].queryset = SituacaoMatriculaPeriodo.objects.filter(
            id__in=[SituacaoMatriculaPeriodo.DEPENDENCIA, SituacaoMatriculaPeriodo.REPROVADO, SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA]
        )
        self.fields['diretoria'].queryset = Diretoria.locals.all()
        self.fields['curso_campus'].queryset = CursoCampus.locals.filter(diretoria__in=Diretoria.locals.values_list('id', flat=True))
        self.fields['turma'].queryset = Turma.locals.all()
        self.fields['diario'].queryset = Diario.locals.all()
        if 'ae' in settings.INSTALLED_APPS:
            BeneficioGovernoFederal = apps.get_model('ae', 'BeneficioGovernoFederal')
            ProgramaSocial = apps.get_model('ae', 'Programa')
            self.fields['beneficio'] = forms.ModelChoiceField(
                BeneficioGovernoFederal.objects.all(),
                label='Programa Social',
                required=False,
                help_text='O aluno deverá ter informado a participação no programa social em sua caracterização social.',
            )
            self.fields['programa'] = forms.ModelMultiplePopupChoiceField(
                ProgramaSocial.objects.all(),
                label='Programa de Assistência Estudantil',
                required=False,
                help_text='Serão exibidos todos os alunos com participação ativa ou inativa nos programas selecionados',
            )
            self.fieldsets = self.fieldsets + (('Filtros Adicionais', {'fields': ('beneficio', 'programa')}),)

    def clean(self):
        filtros = []
        qs = MatriculaDiario.objects.all()
        qs_resumida = MatriculaDiarioResumida.objects.all()

        diretoria = self.cleaned_data.get('diretoria')
        curso_campus = self.cleaned_data.get('curso_campus')
        periodo_matriz = self.cleaned_data.get('periodo_matriz')
        turma = self.cleaned_data.get('turma')
        diario = self.cleaned_data.get('diario')
        componente = self.cleaned_data.get('componente')
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        situacao = self.cleaned_data.get('situacao')
        programa = self.cleaned_data.get('programa')
        beneficio = self.cleaned_data.get('beneficio')

        if diretoria:
            qs = qs.filter(matricula_periodo__aluno__curso_campus__diretoria=diretoria)
            qs_resumida = qs_resumida.filter(matricula_periodo__aluno__curso_campus__diretoria=diretoria)
            filtros.append(dict(chave='Diretoria', valor=diretoria))
        if curso_campus:
            qs = qs.filter(matricula_periodo__aluno__curso_campus=curso_campus)
            qs_resumida = qs_resumida.filter(matricula_periodo__aluno__curso_campus=curso_campus)
            filtros.append(dict(chave='Curso', valor=curso_campus))
        if turma:
            qs = qs.filter(matricula_periodo__turma=turma)
            qs_resumida = qs_resumida.filter(matricula_periodo__turma=turma)
            filtros.append(dict(chave='Turma', valor=turma))
        if diario:
            qs = qs.filter(diario=diario)
            filtros.append(dict(chave='Diário', valor=diario))
        if componente:
            qs = qs.filter(diario__componente_curricular__componente=componente)
            filtros.append(dict(chave='Componente', valor=componente))
        if not filtros:
            raise forms.ValidationError('Por favor, selecione, uma diretoria, curso, turma ou diário.')

        if int(periodo_matriz) > 0:
            qs = qs.filter(matricula_periodo__periodo_matriz=periodo_matriz)
            qs_resumida = qs_resumida.filter(matricula_periodo__aluno__curso_campus=curso_campus)
            filtros.append(dict(chave='Período da Matriz', valor=periodo_matriz))

        qs = qs.filter(
            matricula_periodo__ano_letivo=ano_letivo,
            matricula_periodo__periodo_letivo=periodo_letivo,
            situacao__in=[MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA, MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_CANCELADO],
        )
        qs_resumida = qs_resumida.filter(
            matricula_periodo__ano_letivo=ano_letivo,
            matricula_periodo__periodo_letivo=periodo_letivo,
            situacao__in=[MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA, MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_CANCELADO],
        )
        filtros.append(dict(chave='Ano Letivo', valor=ano_letivo))
        filtros.append(dict(chave='Período Letivo', valor=periodo_letivo))

        if situacao:
            qs = qs.filter(matricula_periodo__situacao__id__in=situacao)
            qs_resumida = qs_resumida.filter(matricula_periodo__situacao__id__in=situacao)
            filtros.append(dict(chave='Situação na Matrícula Período', valor=situacao))
        else:
            raise forms.ValidationError('Selecione pelo menos uma situação no período')

        if programa:
            qs = qs.filter(matricula_periodo__aluno__participacao__programa__in=programa)
            qs_resumida = qs_resumida.filter(matricula_periodo__aluno__participacao__programa__in=programa)
            filtros.append(dict(chave='Programa', valor=programa))
        if beneficio:
            qs = qs.filter(matricula_periodo__aluno__caracterizacao__beneficiario_programa_social=beneficio)

        ordenacao = ['matricula_periodo__situacao', 'matricula_periodo__aluno__pessoa_fisica__nome']
        ordenacao_resumida = ['matricula_periodo__situacao', 'matricula_periodo__aluno__pessoa_fisica__nome']
        qs = qs.order_by(*ordenacao).distinct()
        qs_resumida = qs_resumida.order_by(*ordenacao_resumida).distinct()

        self.qs = list(qs) + list(qs_resumida)
        self.filtros = filtros
        return self.cleaned_data

    def processar(self):
        return self.qs, self.filtros


class RelatorioProfessorForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    categoria = forms.ChoiceField(
        choices=[['Todos', 'Todos'], ['Docente', 'Docente'], ['Técnico-Administrativo', 'Técnico-Administrativo'], ['Prestador de Serviço', 'Prestador de Serviço']],
        label='Categorias',
        required=False,
    )
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=False, help_text='Ano/Período letivo em que o professor possuiu algum diário')
    periodo_letivo = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False)
    tipo_professor = forms.ModelChoiceField(TipoProfessorDiario.objects, label='Tipo no Diário', required=False, help_text='Tipo de vínculo do professor no diário')
    modalidades = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidades Lecionadas', required=False)
    setor_suap = forms.ModelChoiceField(
        Setor.objects, label='Setor de Exercício (SUAP)', widget=TreeWidget(), required=False, help_text='Setor no qual o servidor se encontra em exercício no SUAP'
    )
    setor_lotacao = forms.ModelMultiplePopupChoiceField(
        Setor.siape, label='Setor de Lotação (SIAPE)', required=False, help_text='Setor no qual o servidor se encontra lotado no SIAPE'
    )
    disciplina_ingresso = forms.ModelMultiplePopupChoiceField(Disciplina.objects, label='Disciplina de Ingresso', required=False)
    jornada_trabalho = forms.ModelMultiplePopupChoiceField(JornadaTrabalho.objects, label='Jornada de Trabalho', required=False)
    regime = forms.ChoiceField(
        choices=[['Todos', 'Todos'], ['Efetivo', 'Efetivo'], ['Substituto', 'Substituto'], ['Temporário', 'Temporário'], ['Visitante', 'Visitante']], label='Regime', required=False
    )
    nce = forms.ModelMultiplePopupChoiceField(NucleoCentralEstruturante.objects, label='Núcleo Central Estruturante', required=False)
    apenas_ativo = forms.BooleanField(label='Apenas Ativo', required=False, initial=True)

    ordenacao = forms.ChoiceField(choices=[['Nome', 'Nome']], label='Ordenação')

    EXIBICAO_CHOICES = sorted(
        [
            ['vinculo.setor.uo', 'Campus'],
            ['vinculo.pessoa.email', 'E-mail'],
            ['vinculo.setor', 'Setor de Lotação SUAP'],
            ['vinculo.relacionamento.setor_exercicio', 'Setor de Exercício SIAPE'],
            ['vinculo.relacionamento.setor_lotacao', 'Setor de Lotação SIAPE'],
            ['disciplina', 'Disciplina de Ingresso'],
            ['vinculo.relacionamento.jornada_trabalho', 'Jornada de Trabalho'],
            ['vinculo.relacionamento.cargo_emprego', 'Cargo'],
            ['nce', 'Núcleo Central Estruturante'],
            ['vinculo.realacionamento.pessoa_fisica.lattes', 'Currículo Lattes'],
            ['titulacao', 'Titulação'],
            ['get_qtd_alunos', 'Quantidade de Alunos em Diários'],
            ['instituicao_ensino_superior', 'Formação - Instituição de Ensino Superior'],
            ['curso_superior.descricao', 'Formação - Nome do Curso Superior'],
            ['curso_superior.grau', 'Formação - Grau do Curso Superior'],
            ['possui_formacao_complementar', 'Formação - Possui formação/complementação pedagógica'],
        ],
        key=itemgetter(1),
    )
    EXIBICAO_INICIAS = [['vinculo.setor.uo', 'Campus'], ['disciplina', 'Disciplina de Ingresso']]
    exibicao = forms.MultipleChoiceField(label="Campos Adicionais", choices=EXIBICAO_CHOICES, widget=CheckboxSelectMultiplePlus(), required=False)
    fieldsets = (
        (
            'Filtros de Pesquisa',
            {
                'fields': (
                    'categoria',
                    ('ano_letivo', 'periodo_letivo'),
                    'tipo_professor',
                    'modalidades',
                    'setor_lotacao',
                    'setor_suap',
                    'disciplina_ingresso',
                    'jornada_trabalho',
                    'regime',
                    'nce',
                    'apenas_ativo',
                )
            },
        ),
        ('Formatação', {'fields': (('ordenacao'),)}),
        ('Exibição', {'fields': (('exibicao',),)}),
    )

    def __init__(self, pode_ver_endereco, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs_setores_siape_lotacao = Setor.siape.filter(id__in=Servidor.objects.docentes().values_list('setor_lotacao__id', flat=True).distinct())
        self.fields['setor_lotacao'].queryset = qs_setores_siape_lotacao

        qs_jornada_trabalho = JornadaTrabalho.objects.filter(id__in=Servidor.objects.docentes().values_list('jornada_trabalho__id', flat=True).distinct())
        self.fields['jornada_trabalho'].queryset = qs_jornada_trabalho

        if pode_ver_endereco:
            self.EXIBICAO_CHOICES = self.EXIBICAO_CHOICES + [['vinculo.pessoa.pessoaendereco', 'Endereço'], ['vinculo.pessoa.pessoaendereco.municipio', 'Cidade']]
            self.fields['exibicao'].choices = sorted(self.EXIBICAO_CHOICES, key=itemgetter(1))
        self.fields['exibicao'].initial = [campo[0] for campo in self.EXIBICAO_INICIAS]
        self.fields['tipo_professor'].queryset = TipoProfessorDiario.objects.order_by('descricao')
        self.fields['disciplina_ingresso'].queryset = Disciplina.objects.order_by('pk')

    def clean(self):

        filtros = []

        categoria = self.cleaned_data['categoria']
        filtros.append(dict(chave='Categorias', valor=categoria))

        qs_docentes = Professor.servidores_docentes.all()
        qs_tecnicos = Professor.servidores_tecnicos.filter(professordiario__isnull=False)
        qs_prestadores = Professor.nao_servidores.all()

        apenas_ativo = self.cleaned_data['apenas_ativo']
        filtros.append(dict(chave='Apenas Ativo', valor=apenas_ativo))

        if apenas_ativo:
            qs_docentes = qs_docentes.filter(
                vinculo__pessoa__id__in=Servidor.objects.filter(situacao__codigo__in=Situacao.SITUACOES_ATIVOS, data_fim_servico_na_instituicao__isnull=True).values_list(
                    'pessoa_fisica__id', flat=True
                )
            )

            qs_tecnicos = qs_tecnicos.filter(
                vinculo__pessoa__id__in=Servidor.objects.filter(situacao__codigo__in=Situacao.SITUACOES_ATIVOS, data_fim_servico_na_instituicao__isnull=True).values_list(
                    'pessoa_fisica__id', flat=True
                )
            )

        if categoria == 'Docente':
            qs = qs_docentes
        elif categoria == 'Técnico-Administrativo':
            qs = qs_tecnicos
        elif categoria == 'Prestador de Serviço':
            qs = qs_prestadores
        else:
            qs = qs_docentes | qs_tecnicos | qs_prestadores
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        tipo_professor = self.cleaned_data.get('tipo_professor')
        modalidades = self.cleaned_data['modalidades']
        setor_suap = self.cleaned_data.get('setor_suap')
        setor_lotacao = self.cleaned_data.get('setor_lotacao')
        disciplina_ingresso = self.cleaned_data.get('disciplina_ingresso')
        jornada_trabalho = self.cleaned_data.get('jornada_trabalho')
        regime = self.cleaned_data.get('regime')
        nce = self.cleaned_data.get('nce')

        if ano_letivo:
            qs = qs.filter(professordiario__diario__ano_letivo=ano_letivo)
            filtros.append(dict(chave='Ano Letivo', valor=str(ano_letivo)))
        if periodo_letivo != '' and int(periodo_letivo):
            qs = qs.filter(professordiario__diario__periodo_letivo=periodo_letivo)
            filtros.append(dict(chave='Período Letivo', valor=str(periodo_letivo)))
        if modalidades:
            qs = qs.filter(professordiario__diario__turma__curso_campus__modalidade__in=modalidades)
            filtros.append(dict(chave='Modalidades', valor=', '.join(modalidades.values_list('descricao', flat=True))))
        if tipo_professor:
            qs = qs.filter(professordiario__tipo=tipo_professor)
            filtros.append(dict(chave='Tipo', valor=str(tipo_professor)))
        if setor_suap:
            qs = qs.filter(vinculo__setor__in=setor_suap.descendentes)
            filtros.append(dict(chave='Setor de Exercício', valor=(f'{setor_suap}')))
        if setor_lotacao:
            qs = qs.filter(vinculo__pessoa__id__in=Servidor.objects.filter(setor_lotacao__in=setor_lotacao).values_list('pessoa_fisica__id', flat=True))
            filtros.append(dict(chave='Setor de Lotação SIAPE', valor=format_iterable(setor_lotacao)))
        if disciplina_ingresso:
            qs = qs.filter(disciplina__in=disciplina_ingresso)
            filtros.append(dict(chave='Disciplina de Ingresso', valor=format_iterable(disciplina_ingresso)))
        if jornada_trabalho:
            qs = qs.filter(vinculo__pessoa__id__in=Servidor.objects.filter(jornada_trabalho__in=jornada_trabalho).values_list('pessoa_fisica__id', flat=True))
            filtros.append(dict(chave='Jornada de Trabalho', valor=format_iterable(jornada_trabalho)))
        if regime:
            if regime == 'Efetivo':
                qs = qs.filter(vinculo__pessoa__id__in=Servidor.objects.filter(situacao__nome_siape__in=Situacao.SITUACOES_EFETIVOS).values_list('pessoa_fisica__id', flat=True))
            elif regime == 'Substituto':
                qs = qs.filter(vinculo__pessoa__id__in=Servidor.objects.filter(situacao__codigo=Situacao.CONT_PROF_SUBSTITUTO).values_list('pessoa_fisica__id', flat=True))
            elif regime == 'Temporário':
                qs = qs.filter(vinculo__pessoa__id__in=Servidor.objects.filter(situacao__codigo=Situacao.CONT_PROF_TEMPORARIO).values_list('pessoa_fisica__id', flat=True))
            elif regime == 'Visitante':
                qs = qs.filter(vinculo__pessoa__id__in=Servidor.objects.filter(situacao__codigo=Situacao.CONTR_PROF_VISITANTE).values_list('pessoa_fisica__id', flat=True))
            filtros.append(dict(chave='Regime', valor=regime))
        if nce:
            qs = qs.filter(nce__in=nce)
            filtros.append(dict(chave='Núcleo Central Estruturante', valor=format_iterable(nce)))

        ordenacao = []
        if self.cleaned_data.get('ordenacao') == 'Nome':
            ordenacao.append('vinculo__pessoa__nome')

        qs = qs.order_by(*ordenacao).distinct()
        qs.filtros = filtros

        if not qs.filtros:
            raise forms.ValidationError('Por favor, selecione, no mínimo, um filtro.')
        else:
            self.qs = qs
            return self.cleaned_data

    def processar(self):
        return self.qs


class RelatorioDiarioForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    nivel_ensino = forms.ModelMultiplePopupChoiceField(NivelEnsino.objects, label='Nível de Ensino', required=False)
    modalidade = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidade', required=False)
    estrutura_curso = forms.ModelMultiplePopupChoiceField(EstruturaCurso.objects, label='Estrutura', required=False)
    diretoria = forms.ModelMultiplePopupChoiceField(Diretoria.objects, label='Diretoria', required=False)
    curso_campus = forms.ModelChoiceFieldPlus(
        CursoCampus.objects, label='Curso', required=False, widget=AutocompleteWidget(
            search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[
                ('diretoria', 'diretoria__in'), ('nivel_ensino', 'modalidade__nivel_ensino__in'),
                ('modalidade', 'modalidade__in'),
                ('estrutura_curso', 'matrizcurso__matriz__estrutura__in')
            ]
        )
    )
    turma = forms.ModelChoiceFieldPlus(
        Turma.objects,
        label='Turma',
        required=False,
        widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS, form_filters=[
            ('curso_campus', 'curso_campus'), ('diretoria', 'curso_campus__diretoria__in'),
            ('nivel_ensino', 'curso_campus__modalidade__nivel_ensino__in'),
            ('modalidade', 'curso_campus__modalidade__in'), ('ano_letivo', 'ano_letivo'), ('turno', 'turno'),
            ('periodo_letivo', 'periodo_letivo')
        ]),
    )
    componente = forms.ModelChoiceFieldPlus(
        Componente.objects,
        label='Componente',
        required=False,
        widget=AutocompleteWidget(search_fields=Componente.SEARCH_FIELDS, form_filters=[
            ('nivel_ensino', 'nivel_ensino__in'), ('diretoria', 'diretoria__in'), ('modalidade', 'componentecurricular__matriz__matrizcurso__curso_campus__modalidade__in')
        ]),
    )
    professor = forms.ModelChoiceFieldPlus(
        Professor.objects,
        label='Professor',
        required=False,
        widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS, form_filters=[('diretoria', 'vinculo__setor__diretoria__in')]),
    )
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=False)
    periodo_letivo = forms.ChoiceField(choices=[['', '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False)
    turno = forms.ModelChoiceField(Turno.objects, label='Turno', required=False)
    etapa = forms.ChoiceField(choices=Aula.ETAPA_CHOICES, label='Etapa', required=False, help_text='A etapa selecionada será exportada para PDF.')
    quantidade_etapa = forms.MultipleChoiceField(
        choices=[[1, 'Uma'], [2, 'Duas'], [4, 'Quatro']], label='Quantidade de Etapas', widget=forms.CheckboxSelectMultiple(), required=False
    )
    etapa_entregue = forms.MultipleChoiceField(choices=Aula.ETAPA_CHOICES, label='Etapas Entregues', widget=forms.CheckboxSelectMultiple(), required=False)
    etapa_posse_professor = forms.MultipleChoiceField(choices=Aula.ETAPA_CHOICES, label='Etapas em Posse do Professor', widget=forms.CheckboxSelectMultiple(), required=False)
    alunos_pendentes = forms.BooleanField(label='Diários com Alunos Dependentes', required=False)
    numero_alunos_abaixo_limite = forms.BooleanField(label='Número de Alunos abaixo do Limite', required=False)
    ordenacao = forms.ChoiceField(choices=[['Nome', 'Nome do Componente'], ['Período', 'Período Letivo']], label='Ordenação')
    agrupamento = forms.ChoiceField(choices=[['Campus', 'Campus'], ['Curso', 'Curso']], label='Agrupamento')

    EXIBICAO_CHOICES = [
        ['componente_curricular.componente.ch_hora_relogio', 'CH Relógio'],
        ['componente_curricular.componente.ch_hora_aula', 'CH Aula'],
        ['turma', 'Turma'],
        ['turma.curso_campus', 'Curso'],
        ['ano_letivo', 'Ano Letivo'],
        ['periodo_letivo', 'Período Letivo'],
        ['quantidade_vagas', 'Quantidade de Vagas'],
        ['estrutura_curso', 'Estrutura do Curso'],
        ['componente_curricular.qtd_avaliacoes', 'Quantidade de Etapas'],
        ['componente_curricular.componente.tipo', 'Tipo de Componente'],
        ['turma.curso_campus.diretoria', 'Diretoria'],
        ['turno', 'Turno'],
        ['turma.curso_campus.diretoria.setor.uo', 'Campus'],
        ['horario_campus', 'Horário do Campus'],
        ['local_aula', 'Local da Aula'],
        ['get_carga_horaria_cumprida', 'Quantidade de Aulas Ministradas'],
        ['get_quantidade_alunos_ativos', 'Quantidade de Alunos Ativos'],
    ]

    EXIBICAO_INICIAS = [
        ['componente_curricular.componente.ch_hora_relogio', 'CH Relógio'],
        ['componente_curricular.componente.ch_hora_aula', 'CH Aula'],
        ['turma', 'Turma'],
        ['turma.curso_campus', 'Curso'],
        ['get_professores', 'Professores'],
    ]

    exibicao = forms.MultipleChoiceField(label="Campos Adicionais", choices=EXIBICAO_CHOICES, widget=CheckboxSelectMultiplePlus(), required=False)

    fieldsets = (
        (
            'Filtros de Pesquisa',
            {
                'fields': (
                    'nivel_ensino',
                    'modalidade',
                    'estrutura_curso',
                    'diretoria',
                    'curso_campus',
                    ('ano_letivo', 'periodo_letivo'),
                    ('turno'),
                    'turma',
                    'componente',
                    'professor',
                    ('alunos_pendentes', 'numero_alunos_abaixo_limite'),
                )
            },
        ),
        ('Etapa', {'fields': (('quantidade_etapa',), ('etapa_entregue'), ('etapa_posse_professor'), ('etapa'))}),
        ('Formatação', {'fields': (('ordenacao', 'agrupamento'),)}),
        ('Exibição', {'fields': (('exibicao',),)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso_campus'].queryset = self.fields['curso_campus'].queryset.all().filter(ativo=True)
        self.fields['exibicao'].initial = [campo[0] for campo in self.EXIBICAO_INICIAS]

    def clean(self):
        qs = Diario.objects.all()
        diretoria = self.cleaned_data['diretoria']
        professor = self.cleaned_data['professor']
        turma = self.cleaned_data['turma']
        curso_campus = self.cleaned_data['curso_campus']
        componente = self.cleaned_data['componente']
        estrutura_curso = self.cleaned_data['estrutura_curso']
        modalidade = self.cleaned_data['modalidade']
        nivel_ensino = self.cleaned_data['nivel_ensino']
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        turno = self.cleaned_data['turno']
        etapa = self.cleaned_data.get('etapa')
        quantidade_etapa = self.cleaned_data.get('quantidade_etapa')
        etapa_entregue = self.cleaned_data.get('etapa_entregue')
        etapa_posse_professor = self.cleaned_data.get('etapa_posse_professor')
        alunos_pendentes = self.cleaned_data.get('alunos_pendentes')
        numero_alunos_abaixo_limite = self.cleaned_data.get('numero_alunos_abaixo_limite')
        filtros = []

        if diretoria:
            qs = qs.filter(turma__curso_campus__diretoria__in=diretoria)
            filtros.append(dict(chave='Diretoria', valor=format_iterable(diretoria)))
        if professor:
            qs = qs.filter(professordiario__professor=professor)
            filtros.append(dict(chave='Professor', valor=str(professor)))
        if estrutura_curso:
            qs = qs.filter(turma__matriz__estrutura__id__in=estrutura_curso)
            filtros.append(dict(chave='Estrutura de Curso', valor=format_iterable(estrutura_curso)))
        if modalidade:
            qs = qs.filter(turma__curso_campus__modalidade__id__in=modalidade)
            filtros.append(dict(chave='Modalidade', valor=format_iterable(modalidade)))
        if nivel_ensino:
            qs = qs.filter(turma__curso_campus__modalidade__nivel_ensino__id__in=nivel_ensino)
            filtros.append(dict(chave='Nível de Ensino', valor=format_iterable(nivel_ensino)))
        if componente:
            qs = qs.filter(componente_curricular__componente=componente)
            filtros.append(dict(chave='Componente', valor=str(componente)))
        if curso_campus:
            qs = qs.filter(turma__curso_campus=curso_campus)
            filtros.append(dict(chave='Curso', valor=str(curso_campus)))
        if turma:
            qs = qs.filter(turma__curso_campus__ativo=True, matriculadiario__diario__turma=turma)
            filtros.append(dict(chave='Turma', valor=str(turma)))
        if ano_letivo:
            qs = qs.filter(ano_letivo=ano_letivo)
            filtros.append(dict(chave='Ano Letivo', valor=str(ano_letivo)))
        if periodo_letivo and int(periodo_letivo):
            qs = qs.filter(periodo_letivo=periodo_letivo)
            filtros.append(dict(chave='Período Letivo', valor=str(periodo_letivo)))
        if turno:
            qs = qs.filter(turno=turno)
            filtros.append(dict(chave='Turno', valor=str(turno)))
        if etapa:
            if int(etapa) == 5:
                filtros.append(dict(chave='Etapa', valor='Final'))
            else:
                filtros.append(dict(chave='Etapa', valor=str(etapa)))
        if quantidade_etapa:
            qs = qs.filter(componente_curricular__qtd_avaliacoes__in=quantidade_etapa)
            filtros.append(dict(chave='Quantidade de Etapas', valor=', '.join(quantidade_etapa)))
        if etapa_entregue:
            if '1' in etapa_entregue:
                qs = qs.filter(posse_etapa_1=Diario.POSSE_REGISTRO_ESCOLAR)
            if '2' in etapa_entregue:
                qs = qs.filter(posse_etapa_2=Diario.POSSE_REGISTRO_ESCOLAR)
            if '3' in etapa_entregue:
                qs = qs.filter(posse_etapa_3=Diario.POSSE_REGISTRO_ESCOLAR)
            if '4' in etapa_entregue:
                qs = qs.filter(posse_etapa_4=Diario.POSSE_REGISTRO_ESCOLAR)
            if '5' in etapa_entregue:
                qs = qs.filter(posse_etapa_5=Diario.POSSE_REGISTRO_ESCOLAR)
            filtros.append(dict(chave='Etapas Entregues', valor=', '.join(etapa_entregue)))
        if etapa_posse_professor:
            if '1' in etapa_posse_professor:
                qs = qs.filter(posse_etapa_1=Diario.POSSE_PROFESSOR)
            if '2' in etapa_posse_professor:
                qs = qs.filter(posse_etapa_2=Diario.POSSE_PROFESSOR)
            if '3' in etapa_posse_professor:
                qs = qs.filter(posse_etapa_3=Diario.POSSE_PROFESSOR)
            if '4' in etapa_posse_professor:
                qs = qs.filter(posse_etapa_4=Diario.POSSE_PROFESSOR)
            if '5' in etapa_posse_professor:
                qs = qs.filter(posse_etapa_5=Diario.POSSE_PROFESSOR)
            filtros.append(dict(chave='Etapas em Posse do Professor', valor=', '.join(etapa_posse_professor)))
        if alunos_pendentes:
            qs = qs.filter(estrutura_curso__tipo_avaliacao__in=[EstruturaCurso.TIPO_AVALIACAO_SERIADO, EstruturaCurso.TIPO_AVALIACAO_MODULAR])
            componentes_curriculares = qs.values_list('componente_curricular')
            alunos_componente_curricular_reprovados = (
                Aluno.objects.filter(
                    matriculaperiodo__matriculadiario__diario__componente_curricular_id__in=componentes_curriculares,
                    matriculaperiodo__matriculadiario__situacao__in=[MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA],
                )
                .distinct()
                .values_list('id', 'matriculaperiodo__matriculadiario__diario__componente_curricular')
            )

            matriculas_diario_dependentes = set()
            for aluno, componente_curricular in alunos_componente_curricular_reprovados:
                matriculas_diario = MatriculaDiario.objects.filter(
                    diario__componente_curricular_id=componente_curricular,
                    matricula_periodo__aluno_id=aluno,
                    situacao__in=[MatriculaDiario.SITUACAO_CURSANDO, MatriculaDiario.SITUACAO_PROVA_FINAL],
                )
                for matricula_diario in matriculas_diario:
                    matriculas_diario_dependentes.add(matricula_diario)

            qs = qs.filter(matriculadiario__in=matriculas_diario_dependentes).distinct()
            filtros.append(dict(chave='Aluno Pendente', valor=format_(alunos_pendentes)))

        if numero_alunos_abaixo_limite:
            filtros.append(dict(chave='Número de Alunos abaixo do Limite', valor=format_(numero_alunos_abaixo_limite)))
            qs = qs.filter(
                turma__matriz__estrutura__numero_min_alunos_diario__isnull=False
            ).annotate(matriculas=Count('matriculadiario')).filter(
                matriculas__lt=F('turma__matriz__estrutura__numero_min_alunos_diario')
            )
        ordenacao = ['turma__curso_campus', 'turma__curso_campus__diretoria__setor__uo']
        if self.cleaned_data.get('ordenacao') == 'Período':
            ordenacao.append('ano_letivo')
            ordenacao.append('periodo_letivo')
        if self.cleaned_data.get('ordenacao') == 'Nome':
            ordenacao.append('componente_curricular__componente__descricao')

        qs = qs.order_by(*ordenacao).distinct()
        qs.filtros = filtros

        self.qs = qs
        return self.cleaned_data

    def processar(self):
        return self.qs


class ImprimirHorariosForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=True)
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, label='Período Letivo', required=True)

    diretoria = forms.ModelChoiceFieldPlus(
        Diretoria.objects.none(), required=True, label='Diretoria Acadêmica', widget=AutocompleteWidget(search_fields=Diretoria.SEARCH_FIELDS)
    )

    turma = forms.ModelChoiceFieldPlus(
        Turma.objects, label='Turma', required=False,
        widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS, form_filters=[('ano_letivo', 'ano_letivo'), ('periodo_letivo', 'periodo_letivo'), ('diretoria', 'curso_campus__diretoria')])
    )

    fieldsets = (('Filtros', {'fields': (('ano_letivo', 'periodo_letivo'), 'diretoria', 'turma',)}),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals

    def processar(self):
        ano_letivo = self.cleaned_data['ano_letivo']
        periodo_letivo = self.cleaned_data['periodo_letivo']
        diretoria = self.cleaned_data['diretoria']
        turma = self.cleaned_data['turma']
        qs = Turma.objects.filter(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo, curso_campus__diretoria=diretoria)
        if turma:
            qs = qs.filter(pk=turma.pk)
        return qs


class RelatorioHorarioForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Turma', required=False, widget=AutocompleteWidget(form_filters=[('ano_letivo', 'ano_letivo'), ('periodo_letivo', 'periodo_letivo')], search_fields=Turma.SEARCH_FIELDS))
    professor = forms.ModelChoiceFieldPlus(Professor.objects, label='Professor', required=False, widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS))
    sala = forms.ModelChoiceFieldPlus(Sala.ativas, required=False)
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=True)
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, label='Período Letivo', required=True)

    fieldsets = (('Filtros de Pesquisa', {'fields': (('ano_letivo', 'periodo_letivo'), 'turma', 'professor', 'sala')}),)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sala'].queryset = self.fields['sala'].queryset.all().filter(ativa=True, predio__uo=get_uo(user))

    def clean(self):
        professor = self.cleaned_data['professor']
        turma = self.cleaned_data['turma']
        sala = self.cleaned_data['sala']
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data['periodo_letivo']

        if not (professor or turma or sala):
            raise forms.ValidationError('Informe turma, professor ou sala.')

        filtros = []
        qs = HorarioAulaDiario.objects.all()
        if professor:
            qs = qs.filter(diario__professordiario__professor=professor)
            filtros.append(dict(chave='Professor', valor=str(professor)))
        if turma:
            qs = qs.filter(diario__turma=turma)
            filtros.append(dict(chave='Turma', valor=str(turma)))
        if sala:
            qs = qs.filter(diario__local_aula=sala)
            filtros.append(dict(chave='Sala', valor=str(sala)))
        if ano_letivo:
            qs = qs.filter(diario__ano_letivo=ano_letivo)
            filtros.append(dict(chave='Ano Letivo', valor=str(ano_letivo)))
        if int(periodo_letivo):
            qs = qs.filter(diario__periodo_letivo=periodo_letivo)
            filtros.append(dict(chave='Período Letivo', valor=str(periodo_letivo)))
        qs.filtros = filtros
        self.qs = qs
        return self.cleaned_data

    def processar(self):
        return self.qs


class RelatorioHorarioDiarioEspecialForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    diretoria = forms.ModelChoiceFieldPlus(Diretoria.objects.none(), label='Diretoria', required=False, widget=AutocompleteWidget(search_fields=Diretoria.SEARCH_FIELDS))
    professor = forms.ModelChoiceFieldPlus(Professor.objects, label='Professor', required=False, widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS))
    sala = forms.ModelChoiceFieldPlus(Sala.ativas, required=False)
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=True)
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, label='Período Letivo', required=True)

    fieldsets = (('Filtros de Pesquisa', {'fields': (('ano_letivo', 'periodo_letivo'), 'diretoria', 'professor', 'sala')}),)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals
        self.fields['sala'].queryset = self.fields['sala'].queryset.all().filter(ativa=True, predio__uo=get_uo(user))

    def clean(self):
        professor = self.cleaned_data['professor']
        diretoria = self.cleaned_data['diretoria']
        sala = self.cleaned_data['sala']
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data['periodo_letivo']

        if not (professor or diretoria or sala):
            raise forms.ValidationError('Informe turma, professor ou sala.')

        filtros = []
        qs = HorarioAulaDiarioEspecial.objects.all()
        if professor:
            qs = qs.filter(diario_especial__professores=professor)
            filtros.append(dict(chave='Professor', valor=str(professor)))
        if diretoria:
            qs = qs.filter(diario_especial__diretoria=diretoria)
            filtros.append(dict(chave='Diretoria', valor=str(diretoria)))
        if sala:
            qs = qs.filter(diario_especial__sala=sala)
            filtros.append(dict(chave='Sala', valor=str(sala)))
        if ano_letivo:
            qs = qs.filter(diario_especial__ano_letivo=ano_letivo)
            filtros.append(dict(chave='Ano Letivo', valor=str(ano_letivo)))
        if int(periodo_letivo):
            qs = qs.filter(diario_especial__periodo_letivo=periodo_letivo)
            filtros.append(dict(chave='Período Letivo', valor=str(periodo_letivo)))
        qs.filtros = filtros
        self.qs = qs
        return self.cleaned_data

    def processar(self):
        return self.qs


class AtualizarDadosPessoaisForm(forms.FormPlus):
    nome_usual = forms.ChoiceField(label="Nome Usual", required=False, help_text='Nome que será exibido no SUAP')
    lattes = forms.URLField(label='Lattes', help_text='Endereço do currículo lattes', required=False)
    logradouro = forms.CharFieldPlus(max_length=255, required=True, label='Logradouro', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=True, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=True, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='CEP')
    cidade = forms.ModelChoiceFieldPlus(Cidade.objects, required=True, label='Cidade', widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS))

    telefone_principal = forms.CharFieldPlus(max_length=255, label='Telefone Principal', required=False)
    telefone_secundario = forms.CharFieldPlus(max_length=255, label='Telefone Secundário', required=False)
    esconde_telefone = forms.CharFieldPlus(max_length=1, label='esconde_telefone', required=False, widget=forms.HiddenInput())

    utiliza_transporte_escolar_publico = forms.ChoiceField(label='Utiliza Transporte Escolar Público', required=True, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    poder_publico_responsavel_transporte = forms.ChoiceField(
        label='Poder Público Responsável pelo Transporte Escolar', choices=[['', '---------']] + Aluno.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, required=False
    )
    tipo_veiculo = forms.ChoiceField(label='Tipo de Veículo Utilizado no Transporte Escolar', choices=[['', '---------']] + Aluno.TIPO_VEICULO_CHOICES_FOR_FORM, required=False)

    fieldsets = (
        ('Dados Pessoais', {'fields': ('nome_usual',)}),
        ('Lattes', {'fields': ('lattes',)}),
        ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade')}),
        ('Telefones', {'fields': ('telefone_principal', 'telefone_secundario', 'esconde_telefone')}),
        ('Transporte Escolar Utilizado', {'fields': ('utiliza_transporte_escolar_publico', 'poder_publico_responsavel_transporte', 'tipo_veiculo')}),
    )

    def __init__(self, instance=None, pode_realizar_procedimentos=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pode_realizar_procedimentos = pode_realizar_procedimentos
        self.fields["nome_usual"].choices = get_choices_nome_usual(instance.pessoa_fisica.nome)
        if hasattr(instance, 'nome_social'):
            [self.fields['nome_usual'].choices.append(nome) for nome in get_choices_nome_usual(instance.nome_social)]
        # adicionado o nome usual atual caso ele não seja nenhuma combinação retornada pela função acima
        choice = [instance.pessoa_fisica.nome_usual, instance.pessoa_fisica.nome_usual]
        if instance.pessoa_fisica.nome_usual and choice not in self.fields["nome_usual"].choices:
            self.fields["nome_usual"].choices.append(choice)
        if not self.pode_realizar_procedimentos:
            del self.fields['telefone_principal']
            del self.fields['telefone_secundario']
        else:
            del self.fields['esconde_telefone']

    def save(self, instance=None):
        instance.logradouro = self.cleaned_data['logradouro']
        instance.numero = self.cleaned_data['numero']
        instance.complemento = self.cleaned_data['complemento']
        instance.bairro = self.cleaned_data['bairro']
        instance.cep = self.cleaned_data['cep']
        instance.cidade = self.cleaned_data['cidade']
        instance.pessoa_fisica.nome_usual = self.cleaned_data['nome_usual']
        instance.pessoa_fisica.lattes = self.cleaned_data['lattes']
        if self.pode_realizar_procedimentos:
            instance.telefone_principal = self.cleaned_data['telefone_principal']
            instance.telefone_secundario = self.cleaned_data['telefone_secundario']
        instance.pessoa_fisica.save()
        if self.cleaned_data['utiliza_transporte_escolar_publico']:
            instance.poder_publico_responsavel_transporte = self.cleaned_data['poder_publico_responsavel_transporte']
            instance.tipo_veiculo = self.cleaned_data['tipo_veiculo']
        else:
            instance.poder_publico_responsavel_transporte = None
            instance.tipo_veiculo = None
        instance.save()

    def clean_lattes(self):
        lattes = self.cleaned_data.get('lattes')
        if lattes and len(lattes) > 200:
            raise forms.ValidationError(
                'Endereço do currículo lattes inválido. Informe a URL curta, por exemplo, http://buscatextual.cnpq.br/buscatextual/visualizacv.do?id=123456'
            )
        return lattes

    def clean_utiliza_transporte_escolar_publico(self):
        utiliza_transporte_escolar_publico = self.cleaned_data.get('utiliza_transporte_escolar_publico')
        if utiliza_transporte_escolar_publico == 'Sim':
            if not self.data.get('poder_publico_responsavel_transporte') or not self.data.get('tipo_veiculo'):
                raise forms.ValidationError('Informe o responsável pelo transporte público e o tipo utilizado')
        elif utiliza_transporte_escolar_publico == 'Não':
            if self.data.get('poder_publico_responsavel_transporte') or self.data.get('tipo_veiculo'):
                raise forms.ValidationError('Se não utiliza transporte público, os campos "Poder Público Responsável pelo Transporte Escolar" e "Tipo de Veículo Utilizado no Transporte Escolar" não podem estar preenchidos.')
        else:
            if self.data.get('poder_publico_responsavel_transporte') or self.data.get('tipo_veiculo'):
                raise forms.ValidationError('Marque a opção "Utiliza Transporte Escolar Público" caso deseje informar o responsável ou tipo de transporte público utilizado.')
        return utiliza_transporte_escolar_publico

    class Media:
        js = ('/static/edu/js/AtualizarDadosPessoaisForm.js',)

    class Meta:
        fields = ('nome_social', 'logradouro', 'numero', 'complemento', 'bairro', 'cep', 'cidade')


class AtualizarFotoForm(forms.FormPlus):
    aluno = forms.ModelChoiceField(Aluno.objects, widget=forms.HiddenInput())
    foto = forms.PhotoCaptureField(required=False, widget=PhotoCapturePortraitInput)
    arquivo = forms.ImageFieldPlus(required=False)

    fieldsets = (('Captura da Foto com Câmera', {'fields': ('aluno', 'foto')}), ('Upload de Arquivo', {'fields': ('arquivo',)}))

    def clean(self):
        if not self.cleaned_data.get('foto') and not self.cleaned_data.get('arquivo'):
            raise forms.ValidationError('Retire a foto com a câmera ou forneça um arquivo.')
        else:
            return self.cleaned_data

    def processar(self, request):
        aluno = self.cleaned_data.get('aluno')
        if 'foto' in self.cleaned_data and self.cleaned_data.get('foto'):
            dados = self.cleaned_data.get('foto')
        else:
            dados = self.cleaned_data.get('arquivo').read()

        if request.user.has_perm('edu.efetuar_matricula'):
            aluno.foto.save(f'{aluno.pk}.jpg', ContentFile(dados))
            aluno.pessoa_fisica.foto.save(f'{aluno.pk}.jpg', ContentFile(dados))
            return 'Foto atualizada com sucesso.'
        else:
            return 'Esta funcionalidade encontra-se temporariamente indisponível.'


class AtualizarFotoProfessorForm(forms.FormPlus):
    professor = forms.ModelChoiceField(Professor.objects, widget=forms.HiddenInput())
    foto = forms.PhotoCaptureField(required=False)
    arquivo = forms.ImageFieldPlus(required=False)

    fieldsets = (('Captura da Foto com Câmera', {'fields': ('professor', 'foto')}), ('Upload de Arquivo', {'fields': ('arquivo',)}))

    def clean(self):
        if not self.cleaned_data['foto'] and not self.cleaned_data['arquivo']:
            raise forms.ValidationError('Retire a foto com a câmera ou forneça um arquivo.')
        else:
            return self.cleaned_data

    def processar(self, request):
        professor = self.cleaned_data['professor']
        if 'foto' in self.cleaned_data and self.cleaned_data['foto']:
            dados = self.cleaned_data['foto']
        else:
            dados = self.cleaned_data['arquivo'].read()
        if request.user.has_perm('edu.efetuar_matricula'):
            professor.foto.save(f'{professor.pk}.jpg', ContentFile(dados))
            return 'Foto atualizada com sucesso.'
        else:
            return 'Esta funcionalidade encontra-se temporariamente indisponível.'


class ProfessorExternoForm(forms.ModelFormPlus):
    nome = forms.CharFieldPlus(width=300, label='Nome')
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    cpf = forms.BrCpfField(required=False)
    passaporte = forms.CharField(label='Nº do Passaporte', required=False,
                                 help_text='Esse campo é obrigatório para estrangeiros. Ex: BR123456')
    nacionalidade = forms.ChoiceField(choices=Nacionalidade.get_choices(), required=True, label='Nacionalidade')
    rg = forms.CharFieldPlus(label='Registro Geral', required=False)
    rg_orgao = forms.CharFieldPlus(label='Órgão Emissor', required=False, max_length=10)
    rg_data = forms.DateFieldPlus(label='Data de Emissão', required=False)
    rg_uf = forms.BrEstadoBrasileiroField(label='Unidade da Federação', required=False)
    nascimento_data = forms.DateFieldPlus(label='Data de Nascimento', required=False)
    nome_pai = forms.CharFieldPlus(label='Nome do Pai', required=False)
    nome_mae = forms.CharFieldPlus(label='Nome da Mãe', required=False)
    naturalidade = forms.ModelChoiceFieldPlus(Municipio.objects, required=False, label='Naturalidade')

    logradouro = forms.CharFieldPlus(max_length=255, required=False, label='Logradouro', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=False, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=False, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='CEP')
    municipio = forms.ModelChoiceFieldPlus(Municipio.objects.all().order_by('pk'), required=False, label='Cidade', help_text='Preencha o nome da cidade sem acento.')

    email = forms.EmailField(max_length=255, label='E-mail')
    telefone = forms.BrTelefoneField(max_length=255, required=False, label='Telefone', help_text='Formato: "(XX) XXXXX-XXXX"')
    uo = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus')
    titulacao = forms.ChoiceField(label='Titulação', choices=[['', '-----']] + Professor.TITULACAO_CHOICES, required=False)
    ultima_instituicao_de_titulacao = forms.CharFieldPlus(label='Instituição', required=False, help_text='Instituição onde recebeu a última titulação')
    area_ultima_titulacao = forms.ChoiceField(label='Área da Última Titulação', required=False, choices=[['', '-----']] + Professor.AREA_ULTIMA_TITULACAO_CHOICES)
    ano_ultima_titulacao = forms.ModelChoiceField(Ano.objects, label='Ano', required=False, help_text='Ano em que obteu a última titulação')
    vinculo_professor_ead = forms.ModelChoiceField(VinculoProfessorEAD.objects, label='Vínculo', required=False, help_text='Vínculo EAD caso seja professor à distância')
    nce = forms.MultipleModelChoiceFieldPlus(NucleoCentralEstruturante.objects, label='NCE', required=False)

    fieldsets = (
        ('Dados Pessoais', {'fields': ('nome', 'cpf', 'passaporte', 'nacionalidade', 'sexo', 'nascimento_data', 'nome_pai', 'nome_mae', 'naturalidade')}),
        ('RG', {'fields': ('rg', 'rg_orgao', 'rg_data', 'rg_uf')}),
        ('Endereço', {'fields': ('cep', 'municipio', 'logradouro', 'numero', 'complemento', 'bairro')}),
        ('Dados para Contato', {'fields': ('email', 'telefone')}),
        ('Dados do Professor', {'fields': ('uo', 'nce')}),
        (
            'Dados da Formação',
            {
                'fields': (
                    ('ano_inicio_curso_superior', 'ano_conclusao_curso_superior'),
                    ('curso_superior', 'instituicao_ensino_superior'),
                    ('titulacao', 'possui_formacao_complementar'),
                    ('ultima_instituicao_de_titulacao', 'area_ultima_titulacao', 'ano_ultima_titulacao'),
                )
            },
        ),
        ('EAD', {'fields': ('vinculo_professor_ead',)}),
    )

    class Meta:
        model = Professor
        exclude = ('pessoa_fisica_remover', 'vinculo', 'foto', 'cursos_lecionados')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nce'].queryset = NucleoCentralEstruturante.objects.all().order_by('descricao')
        if self.instance.pk:

            self.fields['nome'].initial = self.instance.vinculo.pessoa.nome
            self.fields['cpf'].initial = self.instance.vinculo.pessoa.pessoafisica.cpf
            self.fields['passaporte'].initial = self.instance.vinculo.pessoa.pessoafisica.cpf
            self.fields['nacionalidade'].initial = self.instance.vinculo.pessoa.pessoafisica.nacionalidade
            self.fields['sexo'].initial = self.instance.vinculo.pessoa.pessoafisica.sexo
            self.fields['email'].initial = self.instance.vinculo.pessoa.pessoafisica.email
            if self.instance.vinculo.pessoa.pessoatelefone_set.all().exists():
                self.fields['telefone'].initial = self.instance.vinculo.pessoa.pessoatelefone_set.all()[0].numero
            self.fields['rg'].initial = self.instance.vinculo.pessoa.pessoafisica.rg
            self.fields['rg_orgao'].initial = self.instance.vinculo.pessoa.pessoafisica.rg_orgao
            self.fields['rg_data'].initial = self.instance.vinculo.pessoa.pessoafisica.rg_data
            self.fields['rg_uf'].initial = self.instance.vinculo.pessoa.pessoafisica.rg_uf
            self.fields['nascimento_data'].initial = self.instance.vinculo.pessoa.pessoafisica.nascimento_data
            self.fields['naturalidade'].initial = self.instance.vinculo.pessoa.pessoafisica.nascimento_municipio
            self.fields['nome_pai'].initial = self.instance.vinculo.pessoa.pessoafisica.nome_pai
            self.fields['nome_mae'].initial = self.instance.vinculo.pessoa.pessoafisica.nome_mae
            self.fields['municipio'].initial = self.instance.vinculo.pessoa.endereco_municipio
            self.fields['logradouro'].initial = self.instance.vinculo.pessoa.endereco_logradouro
            self.fields['numero'].initial = self.instance.vinculo.pessoa.endereco_numero
            self.fields['bairro'].initial = self.instance.vinculo.pessoa.endereco_bairro
            self.fields['complemento'].initial = self.instance.vinculo.pessoa.endereco_complemento
            self.fields['cep'].initial = self.instance.vinculo.pessoa.endereco_cep

            if self.instance.vinculo.setor:
                self.fields['uo'].initial = self.instance.vinculo.setor.uo

            if self.is_servidor():
                for field_name in [
                    'nome',
                    'cpf',
                    'passaporte',
                    'nacionalidade',
                    'sexo',
                    'email',
                    'rg',
                    'rg_orgao',
                    'rg_data',
                    'rg_uf',
                    'nascimento_data',
                    'naturalidade',
                    'nome_pai',
                    'nome_mae',
                    'uo',
                    'cep',
                    'municipio',
                    'logradouro',
                    'numero',
                    'complemento',
                    'bairro',
                ]:
                    self.fields[field_name].widget.attrs.update(readonly='readonly')

    def is_servidor(self):
        return self.instance.pk and self.instance.vinculo.eh_servidor()

    def clean_email(self):
        if not self.is_servidor():
            if not Configuracao.get_valor_por_chave('comum', 'permite_email_institucional_email_secundario') and Configuracao.eh_email_institucional(self.cleaned_data['email']):
                raise forms.ValidationError('Escolha um e-mail que não seja institucional.')
        return self.cleaned_data['email']

    def clean_cpf(self):
        if self.instance.pk is None:
            prestador = PrestadorServico.objects.filter(pessoa_fisica__cpf=self.cleaned_data['cpf']).first()
            if prestador and Professor.objects.filter(vinculo=prestador.get_vinculo()):
                raise forms.ValidationError('Já existe um professor externo cadastrado com este CPF.')
        return self.cleaned_data['cpf']

    def clean_passaporte(self):
        passaporte = self.data.get('passaporte')
        nacionalidade = self.data.get('nacionalidade')
        eh_estrangeiro = int(nacionalidade) == Nacionalidade.ESTRANGEIRO if nacionalidade else False
        if eh_estrangeiro and not passaporte:
            self.add_error('passaporte', 'Informe o passaporte.')
        return passaporte

    def clean(self):
        cpf = self.cleaned_data.get('cpf')
        passaporte = self.cleaned_data.get('passaporte')
        nacionalidade = self.data.get('nacionalidade')
        eh_estrangeiro = int(nacionalidade) == Nacionalidade.ESTRANGEIRO if nacionalidade else False
        prestador_ja_cadastrado = False
        if not cpf and not eh_estrangeiro:
            self.add_error('cpf', "O campo CPF é obrigatório para nacionalidades Brasileira")
        if eh_estrangeiro and not cpf:
            username = re.sub(r'\W', '', str(passaporte))
            campo_erro = 'passaporte'
        else:
            username = re.sub(r'\D', '', str(cpf))
            campo_erro = 'cpf'

        # será vinculado a um cadastro de pretador existente
        if cpf and PrestadorServico.objects.filter(cpf=cpf).first():
            prestador_ja_cadastrado = True
        if passaporte and PrestadorServico.objects.filter(passaporte=passaporte).first():
            prestador_ja_cadastrado = True

        if not self.instance.pk and User.objects.filter(username=username).exists() and not prestador_ja_cadastrado:
            self.add_error(campo_erro, f"O usuário {username} já existe.")
        return super().clean()

    def save(self, *args, **kwargs):
        nacionalidade = self.data.get('nacionalidade')
        eh_estrangeiro = int(nacionalidade) == Nacionalidade.ESTRANGEIRO if nacionalidade else False
        if self.instance.pk is None:
            professor = super().save(commit=False)
        else:
            professor = self.instance
        if self.is_servidor():

            professor.save()
        else:
            prestador = None
            cpf = self.cleaned_data.get('cpf')
            passaporte = self.cleaned_data.get('passaporte')
            if cpf:
                prestador = PrestadorServico.objects.filter(cpf=cpf).first()
            elif eh_estrangeiro and passaporte:
                prestador = PrestadorServico.objects.filter(passaporte=passaporte).first()
            if not prestador:
                prestador = PrestadorServico()
            prestador.cpf = cpf
            prestador.passaporte = passaporte
            prestador.nacionalidade = int(self.cleaned_data.get('nacionalidade'))
            prestador.nome_registro = self.cleaned_data['nome']
            prestador.sexo = self.cleaned_data['sexo']
            prestador.rg = self.cleaned_data['rg']
            if not prestador.email_secundario:
                prestador.email_secundario = self.cleaned_data['email']
            prestador.email = self.cleaned_data['email']
            prestador.setor = self.cleaned_data['uo'].setor
            prestador.rg_orgao = self.cleaned_data['rg_orgao']
            prestador.rg_data = self.cleaned_data['rg_data']
            prestador.rg_uf = self.cleaned_data['rg_uf']
            prestador.nascimento_data = self.cleaned_data['nascimento_data']
            prestador.nome_pai = self.cleaned_data['nome_pai']
            prestador.nome_mae = self.cleaned_data['nome_mae']
            prestador.nascimento_municipio = self.cleaned_data['naturalidade']
            if prestador.pessoaendereco_set.all().exists():
                pessoa_endereco = prestador.pessoaendereco_set.all()[0]
            else:
                pessoa_endereco = PessoaEndereco()
            pessoa_endereco.municipio = self.cleaned_data['municipio']
            pessoa_endereco.logradouro = self.cleaned_data['logradouro']
            pessoa_endereco.numero = self.cleaned_data['numero']
            pessoa_endereco.bairro = self.cleaned_data['bairro']
            pessoa_endereco.complemento = self.cleaned_data['complemento']
            pessoa_endereco.cep = self.cleaned_data['cep']

            if prestador.pessoatelefone_set.all().exists():
                pessoa_telefone = prestador.pessoatelefone_set.all()[0]
            else:
                pessoa_telefone = PessoaTelefone()
            pessoa_telefone.numero = self.cleaned_data['telefone']

            prestador.save()
            pessoa_endereco.pessoa = prestador
            pessoa_telefone.pessoa = prestador
            pessoa_endereco.save()
            pessoa_telefone.save()
            professor.vinculo = prestador.get_vinculo()

            try:
                LdapConf = apps.get_model('ldap_backend', 'LdapConf')
                conf = LdapConf.get_active()
                conf.sync_user(prestador)
            except Exception:
                pass
                # TODO Verificar se essa exceçao deve ser, de fato, silenciada
        super().save(*args, **kwargs)
        return self.instance


class RegistroEmissaoDiplomaForm(forms.ModelFormPlus):
    id = forms.CharField(label='Código', widget=forms.TextInput(attrs=dict(readonly='readonly')))
    pasta = forms.CharField(label='Pasta', required=True)

    class Meta:
        model = RegistroEmissaoDiploma
        fields = ['id', 'pasta', 'autenticacao_sistec', 'observacao']


class PublicaoDOURegistroEmissaoDiplomaForm(forms.ModelFormPlus):
    class Meta:
        model = RegistroEmissaoDiploma
        fields = ['data_publicacao_dou', 'url_publicacao_dou']


class RegistroEmissaoDiplomaPublicForm(forms.FormPlus):
    SUBMIT_LABEL = 'Filtrar'
    METHOD = 'GET'

    aluno = forms.CharField(label='Nome, Matrícula ou CPF', required=False, widget=forms.TextInput(attrs={'size': 20}))
    campus = forms.ModelChoiceField(required=False, queryset=UnidadeOrganizacional.objects.campi().all(), label='Campus')
    modalidade = forms.ModelChoiceField(required=False, queryset=Modalidade.objects.all(), label='Modalidade')

    def processar(self):
        qs = RegistroEmissaoDiploma.objects.exclude(cancelado=True)
        nome = self.cleaned_data['aluno']
        campus = self.cleaned_data['campus']
        modalidade = self.cleaned_data['modalidade']
        if nome:
            qs = qs.filter(aluno__pessoa_fisica__nome__icontains=nome) | qs.filter(aluno__pessoa_fisica__cpf=nome) | qs.filter(aluno__matricula=nome)
        if campus:
            qs = qs.filter(aluno__curso_campus__diretoria__setor__uo=campus)
        if modalidade:
            qs = qs.filter(aluno__curso_campus__modalidade=modalidade)
        return qs


class EmitirSegundaViaDiploma(forms.FormPlus):
    # processo = forms.ModelChoiceFieldPlus(Processo.objects, label='Processo')
    numero_formulario = forms.CharField(label='Número do Formulário', required=False, help_text='Número de série do papel em caso de utilização de papel moeda/timbrado.')
    autenticacao_sistec = forms.CharField(label='Autenticação SISTEC', required=False, help_text='Código de autenticação SISTEC. Obrigatório para alunos de cursos técnicos.')

    def processar(self, registro):
        processo = self.cleaned_data['processo']
        numero_formulario = self.cleaned_data['numero_formulario']
        autenticacao_sistec = self.cleaned_data['autenticacao_sistec']
        return RegistroEmissaoDiploma.gerar_registro(registro.aluno, processo, numero_formulario, registro.pasta, autenticacao_sistec)


class EmitirDiplomaForm(FormWizardPlus):
    # processo = forms.ModelChoiceFieldPlus(Processo.objects, label='Processo')
    numero_pasta = forms.CharField(label='Nome da Pasta', required=False, help_text='Nome da pasta na qual o registro de emissão de diploma será guardado')

    def validar(self, aluno):

        link_edicao_aluno = f"<a href='/admin/edu/aluno/{aluno.id}/'>Clique aqui para informá-la.</a>"

        if not aluno.is_fic() and not self.usuario_pode_emitir_para_cursos_regulares():
            raise forms.ValidationError('Apenas Diretores e Coordenadores de Registro Acadêmico podem emitir diplomas de cursos regulares.')

        if not aluno.pessoa_fisica.nascimento_data:
            raise forms.ValidationError(mark_safe(f'Aluno sem data de nascimento definida. {link_edicao_aluno}'))

        if not aluno.naturalidade:
            raise forms.ValidationError(mark_safe(f'Aluno sem naturalidade definida. {link_edicao_aluno}'))

        if not ConfiguracaoLivro.objects.filter(uo=aluno.curso_campus.diretoria.setor.uo, modalidades__in=[aluno.curso_campus.modalidade]).exists():
            raise forms.ValidationError('Não há configuração de livro para o campus e modalidade do curso do aluno.')

        if aluno.situacao.pk not in [SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO]:
            raise forms.ValidationError('Apenas alunos que concluíram podem ter seu diploma/certificado emitido.')

        if not aluno.curso_campus.emite_diploma:
            raise ValidationError(
                'O diploma não pode ser emitido pois o curso do aluno não permite a emissão de diploma. Caso deseje emitir o diploma para este curso, altere o cadastro do mesmo.'
            )

        return aluno

    def usuario_pode_emitir_para_cursos_regulares(self):
        return self.request.user.groups.filter(name__in=['Coordenador de Registros Acadêmicos', 'Diretor Acadêmico', 'Administrador Acadêmico']).exists()

    @transaction.atomic
    def processar(self):
        ids = []
        if 'aluno' in self.fields:
            alunos = [self.cleaned_data['aluno']]
        else:
            alunos = self.cleaned_data['alunos']
        numero_pasta = None
        numero_formulario = 'numero_formulario' in self.cleaned_data and self.cleaned_data['numero_formulario'] or None
        autenticacao_sistec = 'autenticacao_sistec' in self.cleaned_data and self.cleaned_data['autenticacao_sistec'] or None
        processo = self.cleaned_data['processo']

        for aluno in alunos:
            # Emissão de diploma em lote
            if 'prefixo' in self.cleaned_data:
                if numero_pasta is None and self.cleaned_data['numero_pasta']:
                    numero_pasta = int(self.cleaned_data['numero_pasta'])
                pasta = '{}{}'.format(self.cleaned_data['prefixo'], numero_pasta or '')
                if numero_pasta is not None:
                    numero_pasta += 1
            # Emissão de diploma individualizado
            else:
                pasta = self.cleaned_data['numero_pasta']
            registro = RegistroEmissaoDiploma.gerar_registro(aluno, processo, numero_formulario, pasta, autenticacao_sistec)
            if self.is_emissao_em_lote() or aluno.curso_campus.assinatura_eletronica or aluno.curso_campus.assinatura_digital:
                registro.registrar()
            ids.append(str(registro.id))
        return ids


class EmitirDiplomaAlunoForm(EmitirDiplomaForm):
    aluno = forms.ModelChoiceFieldPlus(
        Aluno.locals, label='Aluno', widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS), help_text='Lista alunos com cursos ativos e situação "CONCLUÍDO" ou "FORMADO"'
    )
    numero_formulario = forms.CharField(label='Número do Formulário', required=False, help_text='Número de série do papel em caso de utilização de papel moeda/timbrado.')
    autenticacao_sistec = forms.CharField(label='Autenticação SISTEC', required=False, help_text='Código de autenticação SISTEC. Obrigatório para alunos de cursos técnicos.')

    steps = ([('Seleção do Aluno', {'fields': ('aluno',)})], [('Dados da Emissão', {'fields': ('processo', 'numero_formulario', 'numero_pasta', 'autenticacao_sistec')})])

    def next_step(self):
        if 'autenticacao_sistec' in self.fields:
            aluno = self.get_entered_data('aluno')
            if aluno:
                if aluno.requer_autenticacao_sistec_para_emissao_diploma():
                    if not self.get_entered_data('autenticacao_sistec'):
                        list_codigo_sistec = aluno.curso_campus.codigo_sistec.split(';')
                        codigo = CodigoAutenticadorSistec.objects.filter(
                            cpf=aluno.pessoa_fisica.cpf,
                            codigo_unidade=aluno.curso_campus.diretoria.setor.uo.codigo_sistec,
                            codigo_curso__in=list_codigo_sistec
                        ).values_list('codigo_autenticacao', flat=True).first()
                        if codigo:
                            self.initial['autenticacao_sistec'] = codigo
                            self.fields['autenticacao_sistec'].initial = codigo

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Aluno.locals.filter(situacao__id__in=[SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO])
        qs = qs.filter(matriz__isnull=False, curso_campus__ativo=True) | qs.filter(codigo_academico__isnull=False)
        if 'sica' in settings.INSTALLED_APPS:
            qs = qs | Aluno.objects.filter(historico__isnull=False)
        if not in_group(self.request.user, 'Administrador Acadêmico') and not in_group(self.request.user, 'Coordenador de Registro Acadêmico - SICA'):
            qs = qs.filter(curso_campus__diretoria__setor__uo=get_uo(self.request.user))

        self.fields['aluno'].queryset = qs

    def clean_aluno(self):
        aluno = self.get_entered_data('aluno')
        if 'sica' in settings.INSTALLED_APPS and aluno.historico_set.exists() and aluno.matriz and aluno.matriz.estrutura and not aluno.matriz.estrutura.proitec:
            self.validar(aluno)
        else:
            if not ConfiguracaoLivro.objects.filter(uo=aluno.curso_campus.diretoria.setor.uo, modalidades__in=[aluno.curso_campus.modalidade]).exists():
                raise forms.ValidationError('Não há configuração de livro para o campus e modalidade do curso do aluno.')
        return aluno

    def is_emissao_em_lote(self):
        return False

    def _clean_autenticacao_sistec(self):
        autenticacao_sistec = self.cleaned_data.get('autenticacao_sistec')
        aluno = self.get_entered_data('aluno')
        if aluno:
            if aluno.requer_autenticacao_sistec_para_emissao_diploma():
                if not autenticacao_sistec:
                    raise forms.ValidationError('A autenticação SISTEC é necessária para alunos dos cursos técnicos.')
        return autenticacao_sistec


class EmitirDiplomaLoteForm(EmitirDiplomaForm):
    alunos = forms.MultipleModelChoiceField(Aluno.locals, label='', widget=RenderableSelectMultiple('widgets/diploma_alunos_widget.html'))
    apenas_primeira_via = forms.BooleanField(
        label='1º Via', required=False, help_text='Listar apenas alunos sem registros de emissão de diploma.'
    )
    turma = forms.ModelChoiceFieldPlus(
        Turma.objects.none(), label='Turma', widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS), help_text="Apenas para turmas de cursos da modalidade FIC."
    )
    prefixo = forms.CharField(
        label='Prefixo da Pasta',
        required=False,
        help_text='Prefixo que será usado para composição do nome da pasta na qual o registro de emissão de diploma será guardado. Ex: Caso deseje\
        que os registros de emissão de diploma sejam distribuídos nas pastas com numeração PASTA100, PASTA101, PASTA103, etc., informe o prefixo PASTA nesse campo e o número 100\
        no campo a seguir.',
    )

    numero_pasta = forms.CharField(
        label='Número da Pasta', required=False, help_text='Número inteiro que será utilizado na composição do nome da pasta no qual o registro de emissão de diploma será guardado'
    )

    steps = (
        [('Seleção da Turma', {'fields': ('turma', 'apenas_primeira_via')})],
        [('Seleção dos Alunos', {'fields': ('alunos',)})],
        [('Dados da Emissão', {'fields': ('processo', 'prefixo', 'numero_pasta')})],
    )

    def first_step(self, *args, **kwargs):
        qs = Turma.locals.filter(
            matriculaperiodo__aluno__situacao__id__in=[SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO]
        )
        qs = qs.filter(curso_campus__modalidade__id=Modalidade.FIC) | qs.filter(curso_campus__assinatura_eletronica=True) | qs.filter(curso_campus__assinatura_digital=True)
        self.fields['turma'].queryset = qs.distinct()

    def next_step(self):
        turma = self.get_entered_data('turma')
        if 'alunos' in self.fields:
            self.fields['alunos'].queryset = Aluno.locals.all()
        if 'alunos' in self.fields and turma:
            self.fields['alunos'].queryset = (
                self.fields['alunos']
                .queryset.filter(
                    matriz__isnull=False, matriculaperiodo__turma=turma, situacao__id__in=[SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO], curso_campus__emite_diploma=True
                )
                .distinct()
            )
            apenas_primeira_via = self.get_entered_data('apenas_primeira_via')
            if(apenas_primeira_via):
                self.fields['alunos'].queryset = self.fields['alunos'].queryset.filter(registroemissaodiploma__isnull=True)

    def clean_numero_pasta(self):
        numero_pasta = self.get_entered_data('numero_pasta')
        if numero_pasta:
            try:
                int(numero_pasta)
            except Exception:
                raise forms.ValidationError('Informe um valor inteiro para esse campo.')
        return numero_pasta

    def clean_alunos(self):
        alunos = self.cleaned_data['alunos']
        for aluno in alunos:
            self.validar(aluno)
        return alunos

    def is_emissao_em_lote(self):
        return True


class ImprimirDiplomaForm(forms.FormPlus):
    reitor = forms.ModelChoiceField(Servidor.objects, required=True, label='Reitor')
    reitor_protempore = forms.BooleanField(label='Reitor Pro tempore?', required=False)
    diretor_geral = forms.ModelChoiceField(Funcionario.objects, label='Diretor Geral')
    diretor_geral_protempore = forms.BooleanField(label='Diretor Geral Pro tempore?', required=False)
    diretor_academico = forms.ModelChoiceField(Funcionario.objects, label='Diretor Acadêmico', required=False)
    diretor_ensino = forms.ModelChoiceField(Funcionario.objects, label='Diretor de Ensino', required=False)
    coordenador_registro_academico = forms.ModelChoiceField(CoordenadorRegistroAcademico.objects, required=False, label='Coordenador de Registro Acadêmico')

    modelo_documento = forms.ModelChoiceField(ModeloDocumento.objects, label='Modelo')

    fieldsets = (
        ('Reitor', {'fields': (('reitor', 'reitor_protempore'),)}),
        ('Diretores', {'fields': (('diretor_geral', 'diretor_geral_protempore'), ('diretor_academico', 'diretor_ensino'))}),
        ('Registro Escolar', {'fields': ('coordenador_registro_academico',)}),
        ('Modelo', {'fields': ('modelo_documento',)}),
    )

    SUBMIT_STYLE = 'success dontdisable'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs_diretoria_reitoria = Diretoria.objects.filter(setor__uo__sigla=utils.get_sigla_reitoria())
        if qs_diretoria_reitoria.exists():
            self.fields['reitor'].queryset = qs_diretoria_reitoria[0].get_reitores()
        else:
            qs_diretores_gerais = Servidor.objects.none()
            for diretoria in Diretoria.objects.all():
                qs_diretores_gerais = qs_diretores_gerais | diretoria.get_diretores_gerais()
            self.fields['reitor'].queryset = qs_diretores_gerais
        self.fields['modelo_documento'].queryset = self.fields['modelo_documento'].queryset.filter(ativo=True)

    def clean(self):
        if not self.cleaned_data.get('diretor_academico') and not self.cleaned_data.get('diretor_ensino'):
            raise forms.ValidationError('Infome o Diretor Acadêmico ou o Diretor de Ensino.')
        return self.cleaned_data


class CancelarRegistroEmissaoDiplomaForm(forms.ModelFormPlus):
    class Meta:
        model = RegistroEmissaoDiploma
        fields = ('motivo_cancelamento',)


class HistoricoImportacaoForm(forms.ModelFormPlus):
    id = forms.CharField(label='Identificador', widget=forms.TextInput(attrs=dict(readonly='readonly')))

    class Meta:
        model = HistoricoImportacao
        fields = ['id']


class LogForm(forms.ModelFormPlus):
    id = forms.CharField(label='Identificador', widget=forms.TextInput(attrs=dict(readonly='readonly')))

    class Meta:
        model = Log
        fields = ['id']


class RealizarAuditoriaForm(forms.FormPlus):
    METHOD = 'GET'
    user = forms.ModelChoiceFieldPlus(User.objects, label='Usuário', required=False)
    aluno = forms.ModelChoiceFieldPlus(Aluno.objects.autocomplete(), label='Aluno', required=False, widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS))
    diario = forms.ModelChoiceFieldPlus(
        Diario.objects,
        label='Diário',
        required=False,
        help_text='Para encontrar um diário entre com a sigla do componente ou o id do diário.',
        widget=AutocompleteWidget(search_fields=Diario.SEARCH_FIELDS),
    )
    professor = forms.ModelChoiceFieldPlus(Professor.objects, label='Professor', required=False, widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS))
    data_inicio = forms.DateFieldPlus(label='Data de Início', required=False)
    data_fim = forms.DateFieldPlus(label='Data de Fim', required=False)

    acao = forms.ChoiceField(label='Ação', choices=[['', '-----------']] + Log.TIPO_CHOICES, required=False)
    modelo = forms.CharField(label='Modelo', required=False)
    ref = forms.CharField(label='Referência', required=False)

    def processar(self):
        user = 'user' in self.cleaned_data and self.cleaned_data['user'] or None
        aluno = 'aluno' in self.cleaned_data and self.cleaned_data['aluno'] or None
        diario = 'diario' in self.cleaned_data and self.cleaned_data['diario'] or None
        data_inicio = 'data_inicio' in self.cleaned_data and self.cleaned_data['data_inicio'] or None
        data_fim = 'data_fim' in self.cleaned_data and self.cleaned_data['data_fim'] or None
        professor = 'professor' in self.cleaned_data and self.cleaned_data['professor'] or None

        acao = 'acao' in self.cleaned_data and self.cleaned_data['acao'] or None
        modelo = 'modelo' in self.cleaned_data and self.cleaned_data['modelo'] or None
        ref = 'ref' in self.cleaned_data and self.cleaned_data['ref'] or None

        qs = Log.objects.all()

        if user:
            qs = qs.filter(user=user)
        if aluno:
            qs = qs.filter(ref_aluno=aluno.pk) | qs.filter(ref=aluno.pk, modelo='Aluno')
        if diario:
            qs = qs.filter(ref_diario=diario.pk) | qs.filter(ref=diario.pk, modelo='Diario')
        if data_inicio:
            qs = qs.filter(dt__gt=data_inicio)
        if data_fim:
            qs = qs.filter(dt__lt=data_fim + timedelta(days=1))
        if professor:
            qs = qs.filter(modelo="Professor", ref=professor.pk)

        if acao:
            qs = qs.filter(tipo=acao)
        if ref and modelo:
            if modelo == 'Aluno':
                qs = qs.filter(ref=ref, modelo=modelo) | qs.filter(ref_aluno=ref).exclude(modelo=modelo)
            elif modelo == 'Diario':
                qs = qs.filter(ref=ref, modelo=modelo) | qs.filter(ref_diario=ref).exclude(modelo=modelo)
            else:
                qs = qs.filter(ref=ref, modelo=modelo)
        else:
            if ref:
                qs = qs.filter(ref=ref)
            if modelo:
                qs = qs.filter(modelo=modelo)

        return qs.distinct().order_by('-dt')


class RedirectForm(forms.FormPlus):
    def get_url(self):
        pass

    def processar(self):
        return HttpResponse(f'<script>parent.close_fancybox_noreload();parent.document.location.href="{self.get_url()}"</script>')


class BuscaAlunoForm(RedirectForm):
    aluno = forms.ModelChoiceFieldPlus(Aluno.objects, label='Matrícula/Nome', widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS))

    def get_url(self):
        return self.cleaned_data['aluno'].get_absolute_url()


class BuscaDiarioForm(RedirectForm):
    diario = forms.ModelChoiceFieldPlus(
        Diario.objects.none(),
        label='Código/Descrição',
        help_text='Para encontrar um diário entre com a sigla do componente ou o id do diário',
        widget=AutocompleteWidget(search_fields=Diario.SEARCH_FIELDS),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diario'].queryset = Diario.locals.all()

    def get_url(self):
        return self.cleaned_data['diario'].get_absolute_url()


class BuscaMatrizForm(RedirectForm):
    matriz = forms.ModelChoiceFieldPlus(Matriz.objects, label='Código/Descrição', widget=AutocompleteWidget(search_fields=Matriz.SEARCH_FIELDS))

    def get_url(self):
        return self.cleaned_data['matriz'].get_absolute_url()


class BuscaCalendarioForm(RedirectForm):
    calendario = forms.ModelChoiceFieldPlus(CalendarioAcademico.objects, label='Código/Descrição', widget=AutocompleteWidget(search_fields=CalendarioAcademico.SEARCH_FIELDS))

    def get_url(self):
        return self.cleaned_data['calendario'].get_absolute_url()


class ImprimirHistoricoParcialForm(RedirectForm):
    aluno = forms.ModelChoiceFieldPlus(Aluno.objects, label='Matrícula/Nome', widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS))

    def get_url(self):
        return '/edu/emitir_historico_parcial_pdf/{}/'.format(self.cleaned_data['aluno'].pk)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aluno'].queryset = Aluno.objects.filter(matriz__estrutura__proitec=False, matriz__isnull=False)


class ImprimirHistoricoFinalForm(RedirectForm):
    aluno = forms.ModelChoiceFieldPlus(Aluno.objects, label='Matrícula/Nome', widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS))

    def get_url(self):
        return '/edu/emitir_historico_final_pdf/{}/'.format(self.cleaned_data['aluno'].pk)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aluno'].queryset = Aluno.objects.filter(
            matriz__estrutura__proitec=False, matriz__isnull=False, situacao__id__in=[SituacaoMatricula.CONCLUIDO, SituacaoMatricula.EGRESSO]
        )


class ImprimirHistoricoFinalEmLoteForm(FormWizardPlus):
    FECHAMENTO_POR_MATRICULA = 'MATRICULA'
    FECHAMENTO_POR_TURMA = 'TURMA'
    FECHAMENTO_POR_CURSO = 'CURSO'
    TIPO_FECHAMENTO_CHOICES = [[FECHAMENTO_POR_TURMA, 'Por Turma'], [FECHAMENTO_POR_CURSO, 'Por Curso']]

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)
    tipo = forms.ChoiceField(choices=TIPO_FECHAMENTO_CHOICES, widget=forms.RadioSelect())
    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Turma', required=False, help_text="Apenas para turmas de cursos da modalidade FIC.")
    curso = forms.ModelChoiceFieldPlus(CursoCampus.objects, label='Curso', required=False, help_text="Apenas para cursos da modalidade FIC.")
    alunos = forms.MultipleModelChoiceField(Aluno.objects, label='', widget=RenderableSelectMultiple('widgets/alunos_widget.html'))

    class Media:
        js = ('/static/edu/js/ImprimirHistoricoFinalEmLoteForm.js',)

    steps = ([('Filtro', {'fields': ('ano_letivo', 'periodo_letivo', 'tipo', 'turma', 'curso')})], [('Seleção dos Alunos', {'fields': ('alunos',)})])

    def clean_tipo(self):
        curso = self.get_entered_data('curso')
        turma = self.get_entered_data('turma')

        if not (curso or turma):
            raise ValidationError('Você precisa informar o Curso ou a Turma.')

        return self.cleaned_data['tipo']

    def next_step(self):
        curso = self.get_entered_data('curso')
        turma = self.get_entered_data('turma')
        ano_letivo = self.get_entered_data('ano_letivo')
        periodo_letivo = self.get_entered_data('periodo_letivo')
        if 'turma' in self.fields:
            self.fields['turma'].queryset = Turma.locals.all()
        if 'alunos' in self.fields:
            qs = Aluno.objects.filter(situacao__id=SituacaoMatricula.CONCLUIDO).exclude(matriz__id__isnull=True)
            if ano_letivo:
                qs = qs.filter(matriculaperiodo__ano_letivo=ano_letivo)
            if periodo_letivo:
                qs = qs.filter(matriculaperiodo__periodo_letivo=periodo_letivo)
            if curso:
                qs = qs.filter(curso_campus=curso)
            if turma:
                qs = qs.filter(matriculaperiodo__turma=turma)

            self.fields['alunos'].queryset = qs.distinct()

    def processar(self):
        return self.cleaned_data.get('alunos')


class ImprimirBoletinsEmLoteForm(FormWizardPlus):
    FECHAMENTO_POR_MATRICULA = 'MATRICULA'
    FECHAMENTO_POR_TURMA = 'TURMA'
    FECHAMENTO_POR_CURSO = 'CURSO'
    TIPO_FECHAMENTO_CHOICES = [[FECHAMENTO_POR_TURMA, 'Por Turma'], [FECHAMENTO_POR_CURSO, 'Por Curso']]

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)
    tipo = forms.ChoiceField(choices=TIPO_FECHAMENTO_CHOICES, widget=forms.RadioSelect())
    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Turma', required=False)
    curso = forms.ModelChoiceFieldPlus(CursoCampus.objects, label='Curso', required=False)
    alunos = forms.MultipleModelChoiceField(Aluno.objects, label='', widget=RenderableSelectMultiple('widgets/alunos_widget.html', max_result=500))

    class Media:
        js = ('/static/edu/js/ImprimirHistoricoFinalEmLoteForm.js',)

    steps = ([('Filtro', {'fields': ('ano_letivo', 'periodo_letivo', 'tipo', 'turma', 'curso')})], [('Seleção dos Alunos', {'fields': ('alunos',)})])

    def clean_tipo(self):
        curso = self.get_entered_data('curso')
        turma = self.get_entered_data('turma')

        if not (curso or turma):
            raise ValidationError('Você precisa informar o Curso ou a Turma.')

        return self.cleaned_data['tipo']

    def next_step(self):
        curso = self.get_entered_data('curso')
        turma = self.get_entered_data('turma')
        ano_letivo = self.get_entered_data('ano_letivo')
        periodo_letivo = self.get_entered_data('periodo_letivo')

        if 'alunos' in self.fields:
            qs = MatriculaPeriodo.objects.filter(matriculadiario__isnull=False, aluno__matriz_id__isnull=False, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)
            if curso:
                qs = qs.filter(aluno__curso_campus=curso)
            if turma:
                qs = qs.filter(turma=turma)
            qs = qs.values_list('aluno_id', flat=True)
            qs = Aluno.objects.filter(pk__in=qs)
            self.fields['alunos'].queryset = qs.distinct()

    def processar(self):

        return MatriculaPeriodo.objects.filter(
            aluno__in=self.cleaned_data.get('alunos'), ano_letivo=self.cleaned_data.get('ano_letivo'), periodo_letivo=self.cleaned_data.get('periodo_letivo')
        )


class ImprimirBoletimAlunoForm(RedirectForm):
    matricula_periodo = forms.ModelChoiceFieldPlus(MatriculaPeriodo.objects, label='Matrícula/Nome', widget=AutocompleteWidget(search_fields=MatriculaPeriodo.SEARCH_FIELDS))

    def get_url(self):
        return '/edu/emitir_boletim_pdf/{}/'.format(self.cleaned_data['matricula_periodo'].pk)


class ImprimirRegistroDiplomaAlunoForm(RedirectForm):
    registro = forms.ModelChoiceFieldPlus(RegistroEmissaoDiploma.objects, label='Matrícula/Nome', widget=AutocompleteWidget(search_fields=RegistroEmissaoDiploma.SEARCH_FIELDS))

    def get_url(self):
        return '/edu/registroemissaodiploma_pdf/{}/'.format(self.cleaned_data['registro'].pk)


class MateriaisAulaForm(forms.FormPlus):
    diarios = forms.MultipleModelChoiceField(Diario.objects.none(), label='', widget=RenderableSelectMultiple('widgets/diarios_cadastro_material_widget.html'), required=False)

    quantidade = forms.ChoiceField(
        choices=[[1, 1], [2, 2], [3, 3], [4, 4], [5, 5]],
        label='Quantidade',
        help_text='Informe a quantidade de materiais de aula que deseja cadastrar',
        widget=forms.RadioSelect(),
        initial=1,
        required=False,
    )

    publico = forms.BooleanField(label='Público', required=False, help_text='Marque essa opção caso deseje que outros professores visualizem o material')

    descricao1 = forms.CharFieldPlus(label='Descrição', required=False)
    tipo1 = forms.ChoiceField(choices=[[1, 'Upload'], [2, 'Link']], label='Tipo', widget=forms.RadioSelect(), initial=1, required=False)
    arquivo1 = forms.FileFieldPlus(label='Arquivo', help_text='Tamanho máximo permitido: 15MB.', required=False)
    url1 = forms.CharFieldPlus(label='URL do Arquivo', required=False)

    descricao2 = forms.CharFieldPlus(label='Descrição', required=False)
    tipo2 = forms.ChoiceField(choices=[[1, 'Upload'], [2, 'Link']], label='Tipo', widget=forms.RadioSelect(), initial=1, required=False)
    arquivo2 = forms.FileFieldPlus(label='Arquivo', help_text='Tamanho máximo permitido: 15MB.', required=False)
    url2 = forms.CharFieldPlus(label='URL do Arquivo', required=False)

    descricao3 = forms.CharFieldPlus(label='Descrição', required=False)
    tipo3 = forms.ChoiceField(choices=[[1, 'Upload'], [2, 'Link']], label='Tipo', widget=forms.RadioSelect(), initial=1, required=False)
    arquivo3 = forms.FileFieldPlus(label='Arquivo', help_text='Tamanho máximo permitido: 15MB.', required=False)
    url3 = forms.CharFieldPlus(label='URL do Arquivo', required=False)

    descricao4 = forms.CharFieldPlus(label='Descrição', required=False)
    tipo4 = forms.ChoiceField(choices=[[1, 'Upload'], [2, 'Link']], label='Tipo', widget=forms.RadioSelect(), initial=1, required=False)
    arquivo4 = forms.FileFieldPlus(label='Arquivo', help_text='Tamanho máximo permitido: 15MB.', required=False)
    url4 = forms.CharFieldPlus(label='URL do Arquivo', required=False)

    descricao5 = forms.CharFieldPlus(label='Descrição', required=False)
    tipo5 = forms.ChoiceField(choices=[[1, 'Upload'], [2, 'Link']], label='Tipo', widget=forms.RadioSelect(), initial=1, required=False)
    arquivo5 = forms.FileFieldPlus(label='Arquivo', help_text='Tamanho máximo permitido: 15MB.', required=False)
    url5 = forms.CharFieldPlus(label='URL do Arquivo', required=False)

    notificar_aluno = forms.BooleanField(
        label='Notificar alunos',
        help_text='Marque essa opção caso deseje que os alunos dos diários selecionados recebam a notificação do cadastro deste material de aula.',
        required=False,
    )

    fieldsets = (
        ('Dados Gerais', {'fields': ('quantidade', 'publico')}),
        ('Material 1', {'fields': ('descricao1', 'tipo1', 'arquivo1', 'url1')}),
        ('Material 2', {'fields': ('descricao2', 'tipo2', 'arquivo2', 'url2')}),
        ('Material 3', {'fields': ('descricao3', 'tipo3', 'arquivo3', 'url3')}),
        ('Material 4', {'fields': ('descricao4', 'tipo4', 'arquivo4', 'url4')}),
        ('Material 5', {'fields': ('descricao5', 'tipo5', 'arquivo5', 'url5')}),
        ('Diários', {'fields': ('diarios',)}),
        ('Notificação', {'fields': ('notificar_aluno',)}),
    )

    class Media:
        js = ('/static/edu/js/MateriaisAulaForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diarios'].queryset = self.qs_diarios()
        if 'diario' in self.request.GET and self.request.GET['diario']:
            self.fields['diarios'].initial = Diario.objects.filter(pk=self.request.GET['diario']).values_list('pk', flat=True)

    def qs_diarios(self):
        qs = Diario.objects.filter(professordiario__professor__vinculo__user__username=self.request.user.username)
        pk = self.request.GET.get('diario')
        if pk:
            diario = Diario.objects.get(pk=pk)
            qs = qs.filter(ano_letivo=diario.ano_letivo, periodo_letivo=diario.periodo_letivo)
        return qs.order_by('ano_letivo', '-pk')

    def processar(self):
        hoje = datetime.datetime.now()
        professor = Professor.objects.get(vinculo__user=self.request.user)
        materiais = []

        for quantidade in range(1, int(self.cleaned_data.get('quantidade')) + 1):
            material = MaterialAula()
            material.data_cadastro = hoje
            material.publico = self.cleaned_data.get('publico')
            material.descricao = self.cleaned_data.get(f'descricao{quantidade}')
            material.arquivo = self.cleaned_data.get(f'arquivo{quantidade}')
            material.url = self.cleaned_data.get(f'url{quantidade}')
            material.professor = professor
            material.save()
            materiais.append(material)

        todos_diarios = self.qs_diarios()
        diarios_selecionados = self.cleaned_data.get('diarios')

        for diario in todos_diarios:
            professor_diario = ProfessorDiario.objects.get(professor=professor, diario=diario)
            for material in materiais:
                material_diario = MaterialDiario.objects.filter(professor_diario=professor_diario, material_aula=material)
                if material_diario.exists() and diario not in diarios_selecionados:
                    material_diario.delete()
                elif not material_diario.exists() and diario in diarios_selecionados:
                    material_diario = MaterialDiario()
                    material_diario.professor_diario = professor_diario
                    material_diario.material_aula = material
                    material_diario.save()
        return self.cleaned_data.get('notificar_aluno') or False, diarios_selecionados, materiais

    def clean(self):
        for quantidade in range(1, int(self.cleaned_data.get('quantidade')) + 1):
            arquivo = self.cleaned_data.get(f'arquivo{quantidade}')
            url = self.cleaned_data.get(f'url{quantidade}')
            if arquivo:
                if hasattr(arquivo, 'path') and not os.path.exists(arquivo.path):
                    raise forms.ValidationError('Arquivo inexistente.')
                tamanho_maximo_permitido = 15 * 1024 * 1024
                if len(arquivo.name) > 70:
                    raise forms.ValidationError(f'O nome do arquivo no Material {quantidade} deve conter no máximo 70 caracteres.')
                if arquivo.size > tamanho_maximo_permitido:
                    raise forms.ValidationError(f'O tamanho máximo permitido para o arquivo do Material {quantidade} é 15MB.')
            if not arquivo and not url:
                raise forms.ValidationError(f'Faça o upload ou insira a URL do Material {quantidade}.')
        return self.cleaned_data


class MaterialAulaForm(forms.ModelFormPlus):
    tipo = forms.ChoiceField(choices=[[1, 'Upload'], [2, 'Link']], widget=forms.RadioSelect(), initial=1)
    arquivo = forms.FileFieldPlus(help_text='Tamanho máximo permitido: 15MB.', required=False)
    diarios = forms.MultipleModelChoiceField(Diario.objects.none(), label='', widget=RenderableSelectMultiple('widgets/diarios_cadastro_material_widget.html'), required=False)

    class Meta:
        model = MaterialAula
        fields = ['descricao', 'arquivo', 'url', 'publico']

    class Media:
        js = ('/static/edu/js/MaterialAulaForm.js',)

    fieldsets = (('Dados Gerais', {'fields': ('descricao', 'tipo', 'publico')}), ('Arquivo', {'fields': ('arquivo', 'url')}), ('Diários', {'fields': ('diarios',)}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].initial = self.instance.arquivo and 1 or 2

        self.fields['diarios'].queryset = self.qs_diarios()
        self.fields['diarios'].initial = MaterialDiario.objects.filter(material_aula=self.instance.pk).values_list('professor_diario__diario', flat=True)

    def clean(self):
        arquivo = self.cleaned_data.get('arquivo')
        url = self.cleaned_data.get('url')

        if arquivo:
            tamanho_maximo_permitido = 15 * 1024 * 1024
            if len(arquivo.name) > 70:
                raise forms.ValidationError('O nome do arquivo deve conter no máximo 70 caracteres.')
            if arquivo.size > tamanho_maximo_permitido:
                raise forms.ValidationError('O tamanho máximo permitido para o arquivo é 15MB.')

        if not arquivo and not url:
            raise forms.ValidationError('Faça upload ou insira uma url.')
        else:
            return self.cleaned_data

    def save(self, *args, **kwargs):
        obj = super().save(False)
        obj.professor = Professor.objects.get(vinculo__user=self.request.user)
        obj.save()

        professor = Professor.objects.get(vinculo__user=self.request.user)
        todos_diarios = self.qs_diarios()

        for diario in todos_diarios:
            professor_diario = ProfessorDiario.objects.get(professor=professor, diario=diario)
            material_diario = MaterialDiario.objects.filter(professor_diario=professor_diario, material_aula=obj)
            if material_diario.exists() and diario not in self.cleaned_data['diarios']:
                material_diario.delete()
            elif not material_diario.exists() and diario in self.cleaned_data['diarios']:
                material_diario = MaterialDiario()
                material_diario.professor_diario = professor_diario
                material_diario.material_aula = obj
                material_diario.save()

        return obj

    def qs_diarios(self):
        professor = Professor.objects.get(vinculo=self.request.user.get_vinculo())
        qs = Diario.objects.filter(professordiario__professor=professor).order_by('ano_letivo', '-pk')
        return qs


class EntregaEtapaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Confirmar Entrega'

    sem_aula = forms.BooleanField(
        label='Confirmar entrega sem aula', required=True, help_text='Quero entregar a etapa sem aula lançada. A carga horária mínima deverá ser cumprida até a entrega da última etapa.'
    )

    zerar_notas = forms.BooleanField(
        label='Confirmar entrega sem nota', required=False, help_text='Quero entregar a etapa sem nota lançada para o(s) aluno(s) abaixo. As notas em branco serão consideradas como zero.'
    )

    def __init__(self, tem_nota_vazia, pode_entregar_sem_aula, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not pode_entregar_sem_aula:
            self.fields['sem_aula'].widget = forms.HiddenInput()
            self.fields['sem_aula'].required = False
        if not tem_nota_vazia:
            self.fields['zerar_notas'].widget = forms.HiddenInput()


class VincularMaterialAulaForm(forms.FormPlus):
    materiais_aula = forms.MultipleModelChoiceFieldPlus(
        queryset=MaterialAula.objects,
        label='Materiais de aula',
        help_text=mark_safe(
            'Se você não lembra da descrição do material desejado, <a target="_blank" href="/admin/edu/materialaula/?tab=tab_meus_materiais"><strong>liste seus materiais cadastrados</strong></a> em uma nova aba.'
        ),
    )
    diarios = forms.MultipleModelChoiceField(
        Diario.objects.none(),
        label='Outros Diários',
        required=False,
        help_text='Informe os diários relacionados nos quais você também gostaria de vincular o material ou materiais selecionados.',
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        self.professor_diario = kwargs.pop('professor_diario')
        super().__init__(*args, **kwargs)
        professor = self.professor_diario.professor
        self.fields['materiais_aula'].queryset = self.fields['materiais_aula'].queryset.filter(professor=professor)
        self.fields['diarios'].queryset = Diario.objects.filter(
            professordiario__professor=professor, ano_letivo=self.professor_diario.diario.ano_letivo, periodo_letivo=self.professor_diario.diario.periodo_letivo
        ).exclude(pk=self.professor_diario.diario.pk)
        if not self.fields['diarios'].queryset.exists():
            del self.fields['diarios']

    def save(self, etapa):
        professores_diario = [self.professor_diario]
        diarios = self.cleaned_data.get('diarios')
        if diarios:
            for diario in diarios:
                professores_diario.append(diario.professordiario_set.get(professor=self.professor_diario.professor))
        for professor_diario in professores_diario:
            for material_aula in self.cleaned_data['materiais_aula']:
                if not MaterialDiario.objects.filter(professor_diario=professor_diario, material_aula=material_aula).exists():
                    obj = MaterialDiario()
                    obj.professor_diario = professor_diario
                    obj.material_aula = material_aula
                    obj.etapa = int(etapa)
                    obj.save()


class SolicitacaoRelancamentoEtapaForm(forms.ModelFormPlus):
    id = forms.CharField(label='Id', widget=forms.TextInput(attrs=dict(readonly='readonly')))

    class Meta:
        model = SolicitacaoRelancamentoEtapa
        fields = ('id',)


class SolicitacaoProrrogacaoEtapaForm(forms.ModelFormPlus):
    id = forms.CharField(label='Id', widget=forms.TextInput(attrs=dict(readonly='readonly')))

    class Meta:
        model = SolicitacaoProrrogacaoEtapa
        fields = ('id',)


class SolicitarRelancamentoEtapaForm(forms.ModelFormPlus):
    def __init__(self, professor_diario, etapa, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.instance.professor_diario = professor_diario
        self.instance.etapa = etapa

    class Meta:
        model = SolicitacaoRelancamentoEtapa
        fields = ('motivo',)


class SolicitarProrrogacaoEtapaForm(forms.ModelFormPlus):
    def __init__(self, professor_diario, etapa, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.instance.professor_diario = professor_diario
        self.instance.etapa = etapa

    class Meta:
        model = SolicitacaoProrrogacaoEtapa
        fields = ('motivo',)


class EquivalenciaComponenteQAcademicoForm(forms.ModelFormPlus):
    componente = forms.ModelChoiceField(queryset=Componente.objects, widget=AutocompleteWidget(search_fields=Componente.SEARCH_FIELDS))

    class Meta:
        model = EquivalenciaComponenteQAcademico
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sigla'].widget.attrs.update(readonly='readonly')
        self.fields['descricao'].widget.attrs.update(readonly='readonly')
        self.fields['q_academico'].widget.attrs.update(readonly='readonly')
        self.fields['carga_horaria'].widget.attrs.update(readonly='readonly')


class ImportarAlunosAtivosForm(forms.FormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos())
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES)
    arquivo = forms.FileFieldPlus(help_text='O arquivo deve ser no formato "xlsx", sem cabeçalho, e contendo a matrícula na primeira coluna.', required=False)
    matricula = forms.CharFieldPlus(required=False)

    def __init__(self, matriz_id, *args, **kwargs):
        self.matriz_id = matriz_id
        self.matriculas = []
        super().__init__(*args, **kwargs)

    def clean(self):
        arquivo_up = self.cleaned_data.get('arquivo')
        matricula_up = self.cleaned_data.get('matricula')
        matriculas = []
        matriculas_validas = []

        if not arquivo_up and not matricula_up:
            raise forms.ValidationError('Preencha o campo arquivo ou o campo matrícula.')

        if matricula_up:
            matriculas.append(matricula_up)

        if arquivo_up:
            workbook = xlrd.open_workbook(file_contents=arquivo_up.read())
            sheet = workbook.sheet_by_index(0)
            for i in range(0, sheet.nrows):
                # testando se o fluxo da integração foi seguido corretamente
                matricula = sheet.cell_value(i, 0)
                try:
                    matricula = str(int(sheet.cell_value(i, 0)))
                except Exception:
                    raise forms.ValidationError(f'A matrícula ({matricula}) está incorreta.')

                matriculas.append(matricula)

        for matricula in matriculas:
            qs_aluno = Aluno.objects.filter(matricula=matricula)
            if qs_aluno.exists():
                aluno = qs_aluno[0]
                if not aluno.curso_campus.ativo:
                    raise forms.ValidationError(f'Aluno ({aluno.matricula}) com curso ({aluno.curso_campus}) não ativo.')

                qs_matrizcurso = MatrizCurso.objects.filter(curso_campus=aluno.curso_campus, matriz__id=self.matriz_id)
                if qs_matrizcurso.exists():
                    if not ComponenteCurricular.objects.filter(matriz=qs_matrizcurso[0].matriz).exists():
                        raise forms.ValidationError('A matriz escolhida não possui nenhum componente vinculado.')
                else:
                    raise forms.ValidationError(
                        f'Curso ({aluno.curso_campus}) do aluno ({aluno.matricula}) não possui nenhuma matriz ou a migração está sendo feita na matriz errada.'
                    )
            else:
                raise forms.ValidationError(f'Matrícula({matricula}) inexistente no SUAP.')
            matriculas_validas.append(matricula)

        self.matriculas = matriculas_validas

        if running_tests():
            dao = MockDAO()
        else:
            dao = DAO()

        self.erros = dao.importar_historico_resumo(self.matriculas, self.matriz_id, self.cleaned_data['ano_letivo'], int(self.cleaned_data['periodo_letivo']))
        if self.erros:
            raise ValidationError('')
        else:
            return self.cleaned_data

    def processar(self, request):
        ano_letivo = self.cleaned_data['ano_letivo']
        periodo_letivo = int(self.cleaned_data['periodo_letivo'])
        return tasks.migrar_alunos(self.matriculas, self.matriz_id, ano_letivo, periodo_letivo)


class RelatorioFaltasForm(forms.FormPlus):
    SUBMIT_LABEL = 'Visualizar'
    METHOD = 'GET'

    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.campi(), label='Campus', required=False)

    diretoria = forms.ModelChoiceFieldPlus(Diretoria.objects, label='Diretoria', widget=AutocompleteWidget(form_filters=[('uo', 'setor__uo__in')]), required=False)

    curso_campus = forms.ModelChoiceFieldPlus(
        CursoCampus.objects, label='Curso', widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('uo', 'diretoria__setor__uo__in')]), required=False
    )

    turma = forms.ModelChoiceFieldPlus(
        Turma.objects.none(), widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS, form_filters=[('uo', 'curso_campus__diretoria__setor__uo__in')]), required=False
    )

    diario = forms.ModelChoiceFieldPlus(
        Diario.objects.none(),
        label='Diário',
        help_text='Para encontrar um diário entre com a sigla do componente ou o código do diário.',
        widget=AutocompleteWidget(search_fields=Diario.SEARCH_FIELDS, form_filters=[('uo', 'turma__curso_campus__diretoria__setor__uo__in')]),
        required=False,
    )
    aluno = forms.ModelChoiceFieldPlus(
        Aluno.locals, required=False, widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS, form_filters=[('uo', 'curso_campus__diretoria__setor__uo__in')])
    )

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=False)
    periodo_letivo = forms.ChoiceField(choices=[[None, '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False, initial=1)
    situacao_periodo = forms.ModelMultiplePopupChoiceField(SituacaoMatriculaPeriodo.objects, label="Situação no Período", required=False)
    intervalo_inicio = forms.DateFieldPlus(label='Início do Intervalo', required=False)
    intervalo_fim = forms.DateFieldPlus(label='Fim do Intervalo', required=False)

    situacoes_inativas = forms.BooleanField(
        label='Desconsiderar Situações Inativas',
        required=False,
        help_text='Exclui do relatório aulas e faltas de alunos que estão com situação Cancelado, Dispensado, Trancado ou Transferido no diário.',
        initial=True,
    )
    fieldsets = (
        ('Período', {'fields': (('ano_letivo', 'periodo_letivo'), ('intervalo_inicio', 'intervalo_fim'))}),
        ('Filtros de Pesquisa', {'fields': ('uo', 'diretoria', 'curso_campus', 'turma', 'diario')}),
        ('Filtros Adicionais', {'fields': ('aluno', ('situacao_periodo', 'situacoes_inativas'))}),
    )

    if 'ae' in settings.INSTALLED_APPS:
        fieldsets = (
            ('Período', {'fields': (('ano_letivo', 'periodo_letivo'), ('intervalo_inicio', 'intervalo_fim'))}),
            ('Filtros de Pesquisa', {'fields': ('uo', 'diretoria', 'curso_campus', 'turma', 'diario')}),
            ('Filtros Adicionais', {'fields': ('aluno', ('situacao_periodo', 'situacoes_inativas'))}),
            ('Filtros Assistenciais', {'fields': ('beneficio', 'programa')}),
        )

    def __init__(self, campus, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if campus:
            self.fields['uo'] = forms.ModelChoiceFieldPlus(UnidadeOrganizacional.objects.campi(), label='Campus', required=False)
            self.fields['uo'].initial = campus
            self.fields['uo'].widget.readonly = True

        if 'ae' in settings.INSTALLED_APPS:
            ProgramaSocial = apps.get_model('ae', 'Programa')
            BeneficioGovernoFederal = apps.get_model('ae', 'BeneficioGovernoFederal')

            self.fields['programa'] = forms.ModelMultiplePopupChoiceField(
                ProgramaSocial.objects.all(),
                label='Participação nos programa de assistência estudantil',
                required=False,
                help_text='Serão exibidos todos os alunos com participação ativa ou inativa nos programas selecionados',
            )
            if campus:
                qs = ProgramaSocial.objects.filter(instituicao=campus)
            else:
                qs = ProgramaSocial.objects.all()
            self.fields['programa'].queryset = qs

            self.fields['beneficio'] = forms.ModelChoiceField(
                BeneficioGovernoFederal.objects.all(),
                label='Programa Social',
                required=False,
                help_text='O aluno deverá ter informado a participação no programa social em sua caracterização social.',
            )

        self.fields['periodo_letivo'].initial = None

        self.fields['diario'].queryset = Diario.locals.all()
        self.fields['turma'].queryset = Turma.locals.all()

    def clean(self):
        if (
            not self.cleaned_data.get('turma')
            and not self.cleaned_data.get('diario')
            and not self.cleaned_data.get('aluno')
            and not self.cleaned_data.get('curso_campus')
            and not self.cleaned_data.get('uo')
            and not self.cleaned_data.get('diretoria')
        ):
            raise forms.ValidationError('Insira ao menos o campus, diretoria, curso, turma, diário ou aluno nos filtros.')
        filtro_periodo = (self.cleaned_data.get('curso_campus') or self.cleaned_data.get('uo')) and not (
            self.cleaned_data.get('ano_letivo') and self.cleaned_data.get('periodo_letivo')
        )
        if filtro_periodo and not self.cleaned_data.get('aluno'):
            raise forms.ValidationError('Insira ano letivo e período letivo para filtrar por campus ou curso.')

        return self.cleaned_data

    def clean_intervalo_fim(self):
        if not self.cleaned_data.get('intervalo_inicio') and self.cleaned_data.get('intervalo_fim'):
            raise forms.ValidationError('Insira uma data válida no início do intervalo.')
        else:
            return self.cleaned_data['intervalo_fim']


class AbonoFaltasForm(forms.ModelFormPlus):
    aluno = forms.ModelChoiceFieldPlus(
        Aluno.objects,
        help_text='Somente alunos com situação no período "Matriculado" serão listados.',
        label='Aluno',
        required=True,
        widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS),
    )

    diarios = forms.MultipleModelChoiceFieldPlus(
        Diario.objects,
        label='Diário',
        help_text='Para abonar todos os diários deixe este campo vazio',
        required=False,
        widget=AjaxSelectMultiplePopup(
            required_form_filters=True,
            form_filters=[
                ('data_inicio', 'calendario_academico__data_inicio__lte'),
                ('data_fim', 'calendario_academico__data_fim__gte'),
                ('aluno', 'matriculadiario__matricula_periodo__aluno'),
            ],
        ),
    )

    responsavel_abono = forms.ModelChoiceFieldPlus(
        User.objects, label='Responsável por Abono', required=True, widget=AutocompleteWidget(search_fields=User.SEARCH_FIELDS, readonly='readonly')
    )

    class Meta:
        model = AbonoFaltas
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['diarios'].initial = list(Diario.objects.filter(matriculadiario__falta__abono_faltas=self.instance.pk).values_list('id', flat=True))

            # O secretário só pode criar, alterar ou excluir os abonos de alunos de seus campus.
        # Apenas alunos cujo período letivo encontra-se aberto (matriculado) podem ter faltas abonadas ou rejeitadas.
        self.fields['aluno'].queryset = Aluno.locals.filter(matriculaperiodo__situacao=SituacaoMatriculaPeriodo.MATRICULADO, matriz__isnull=False).order_by('pk').distinct()

    def clean(self):
        aluno = self.cleaned_data.get('aluno')
        data_inicio = self.cleaned_data.get('data_inicio')
        data_fim = self.cleaned_data.get('data_fim')
        if aluno and data_inicio and data_fim:
            # Não permitir cadastro de abono de faltas em matrícula períodos não abertos.
            qs_matricula_periodos = (
                MatriculaPeriodo.objects.filter(aluno=aluno, matriculadiario__falta__aula__data__gte=data_inicio, matriculadiario__falta__aula__data__lte=data_fim)
                .exclude(situacao=SituacaoMatriculaPeriodo.MATRICULADO)
                .distinct()
            )
            if qs_matricula_periodos:
                str_mp_fechados = ', '.join(f'{matricula_periodo.ano_letivo} / {matricula_periodo.periodo_letivo}' for matricula_periodo in qs_matricula_periodos)
                str_mp_fechados = f'No intervalo informado existem períodos já fechados: {str_mp_fechados}.'
                raise ValidationError(str_mp_fechados)

        return self.cleaned_data

    def save(self, *args, **kwargs):
        obj = super().save(False)
        diarios = self.cleaned_data['diarios']
        if diarios:
            obj.diarios = diarios
        return obj


class AbonoFaltasLoteForm(forms.ModelFormPlus):
    METHOD = 'POST'
    alunos = forms.MultipleModelChoiceField(
        Aluno.objects,
        label='Alunos',
        help_text='Somente alunos com situação no período "Matriculado" serão listados.',
        required=True,
        widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS, multiple=True),
    )

    responsavel_abono = forms.ModelChoiceFieldPlus(
        User.objects, label='Responsável por Abono', required=True, widget=AutocompleteWidget(search_fields=User.SEARCH_FIELDS, readonly='readonly')
    )

    fieldsets = (('', {'fields': ('alunos', 'data_inicio', 'data_fim', 'justificativa', 'anexo', 'responsavel_abono')}),)

    class Meta:
        model = AbonoFaltas
        exclude = ('aluno',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsavel_abono'].initial = self.request.user
        # O secretário só pode criar, alterar ou excluir os abonos de alunos de seus campus.
        # Apenas alunos cujo período letivo encontra-se aberto (matriculado) podem ter faltas abonadas ou rejeitadas.
        self.fields['alunos'].queryset = Aluno.locals.filter(matriculaperiodo__situacao=SituacaoMatriculaPeriodo.MATRICULADO, matriz__isnull=False).order_by('pk').distinct()

    def clean(self):
        alunos = self.cleaned_data.get('alunos')
        data_inicio = self.cleaned_data.get('data_inicio')
        data_fim = self.cleaned_data.get('data_fim')
        if alunos and data_inicio and data_fim:
            for aluno in alunos:
                # Não permitir cadastro de abono de faltas em matrícula períodos não abertos.
                qs_matricula_periodos = (
                    MatriculaPeriodo.objects.filter(aluno=aluno, matriculadiario__falta__aula__data__gte=data_inicio, matriculadiario__falta__aula__data__lte=data_fim)
                    .exclude(situacao=SituacaoMatriculaPeriodo.MATRICULADO)
                    .distinct()
                )
                if qs_matricula_periodos.exists():
                    str_mp_fechados = ', '.join(f'{matricula_periodo.ano_letivo} / {matricula_periodo.periodo_letivo}' for matricula_periodo in qs_matricula_periodos)
                    str_mp_fechados = f'No intervalo informado para o aluno {aluno} existem períodos já fechados: {str_mp_fechados}.'
                    raise ValidationError(str_mp_fechados)

        return self.cleaned_data

    def processar(self, *args, **kwargs):
        alunos = self.cleaned_data['alunos']
        for aluno in alunos:
            abono = AbonoFaltas()
            abono.aluno = aluno
            abono.data_inicio = self.cleaned_data.get('data_inicio')
            abono.data_fim = self.cleaned_data.get('data_fim')
            abono.justificativa = self.cleaned_data.get('justificativa')
            abono.anexo = self.cleaned_data.get('anexo')
            abono.responsavel_abono = self.cleaned_data.get('responsavel_abono')
            abono.save()


class ProcedimentoMatriculaForm(forms.ModelFormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', initial=1, required=False, widget=Select(attrs={'disabled': 'disabled'}))
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES, required=False, widget=Select(attrs={'disabled': 'disabled'}))
    opcoes = forms.ChoiceField(label='Tipo')

    def __init__(self, matricula_periodo_pk, *args, **kwargs):
        self.matricula_periodo = MatriculaPeriodo.objects.get(pk=matricula_periodo_pk)
        super().__init__(*args, **kwargs)
        self.fields['ano_letivo'].initial = self.matricula_periodo.ano_letivo.pk
        self.fields['periodo_letivo'].initial = self.matricula_periodo.periodo_letivo
        self.fields['opcoes'].choices = [['', '-------------']] + self.get_choices()
        if self.instance.pk:
            self.fields['ano_letivo'].initial = self.instance.matricula_periodo.ano_letivo.pk
            self.fields['periodo_letivo'].initial = self.instance.matricula_periodo.periodo_letivo

    def get_choices(self):
        return []

    class Meta:
        model = ProcedimentoMatricula
        fields = (#'processo',
                  'data', 'motivo')

    fieldsets = (('Procedimento de Matrícula', {'fields': ('ano_letivo', 'periodo_letivo', 'data', 'opcoes', 'motivo', 'matricula_periodo')}),)

    def save(self, *args, **kwargs):
        situacao_matricula_pk, situacao_matricula_periodo_pk, situacao_matricula_diario_pk = self.cleaned_data['opcoes'].split(';')
        situacao_matricula = SituacaoMatricula.objects.get(pk=situacao_matricula_pk)
        situacao_matricula_periodo = SituacaoMatriculaPeriodo.objects.get(pk=situacao_matricula_periodo_pk)
        situacao_matricula_anterior = self.matricula_periodo.aluno.situacao

        procedimento = super().save(commit=False)
        for choice in self.get_choices():
            if choice[0] == self.cleaned_data['opcoes']:
                procedimento.tipo = choice[1]
        procedimento.matricula_periodo = self.matricula_periodo
        procedimento.situacao_matricula_anterior = situacao_matricula_anterior

        self.matricula_periodo.realizar_procedimento_matricula(procedimento, situacao_matricula, situacao_matricula_periodo, situacao_matricula_diario_pk)

        if 'excluir_pedido_matricula' in self.cleaned_data and self.cleaned_data['excluir_pedido_matricula']:
            qs_pedido = PedidoMatriculaDiario.objects.filter(pedido_matricula__matricula_periodo_id=self.matricula_periodo.id, data_processamento__isnull=True)
            if qs_pedido.exists():
                qs_pedido.delete()

        return procedimento

    def clean(self):
        mps = MatriculaPeriodo.objects.filter(
            aluno=self.matricula_periodo.aluno, situacao__id__in=[SituacaoMatriculaPeriodo.EM_ABERTO, SituacaoMatriculaPeriodo.MATRICULADO]
        ).exclude(pk=self.matricula_periodo.pk)
        if mps.exists():
            raise forms.ValidationError('É necessário fechar os períodos anteriores antes de realizar o procedimento.')
        if self.matricula_periodo.aluno.matriz.estrutura.requer_declaracao_para_cancelamento_matricula:
            if not self.matricula_periodo.aluno.alunoarquivo_set.filter(tipo=15).exists():
                raise forms.ValidationError('Para realizar o cancelamento da matrícula, é necessário realizar previamente o upload da "Declaração de Pedido de Cancelamento de Matrícula" na pasta documental do aluno.')
        return self.cleaned_data


class CancelarMatriculaForm(ProcedimentoMatriculaForm):
    def get_choices(self):
        return [
            [
                f'{SituacaoMatricula.CANCELAMENTO_COMPULSORIO};{SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO};{MatriculaDiario.SITUACAO_CANCELADO}',
                ProcedimentoMatricula.CANCELAMENTO_COMPULSORIO,
            ],
            [f'{SituacaoMatricula.CANCELADO};{SituacaoMatriculaPeriodo.CANCELADA};{MatriculaDiario.SITUACAO_CANCELADO}', ProcedimentoMatricula.CANCELAMENTO_VOLUNTARIO],
            [
                f'{SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE};{SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE};{MatriculaDiario.SITUACAO_CANCELADO}',
                ProcedimentoMatricula.CANCELAMENTO_POR_DUPLICIDADE,
            ],
            [
                f'{SituacaoMatricula.CANCELAMENTO_POR_DESLIGAMENTO};{SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO};{MatriculaDiario.SITUACAO_CANCELADO}',
                ProcedimentoMatricula.CANCELAMENTO_POR_DESLIGAMENTO,
            ],
            [f'{SituacaoMatricula.EVASAO};{SituacaoMatriculaPeriodo.EVASAO};{MatriculaDiario.SITUACAO_CANCELADO}', ProcedimentoMatricula.EVASAO],
            [f'{SituacaoMatricula.JUBILADO};{SituacaoMatriculaPeriodo.JUBILADO};{MatriculaDiario.SITUACAO_CANCELADO}', ProcedimentoMatricula.JUBILAMENTO],
        ]


class TrancarMatriculaForm(ProcedimentoMatriculaForm):

    excluir_pedido_matricula = forms.BooleanField(label='Excluir Pedido de Renovação de Matrícula', required=False, help_text='Marque esta opção caso o aluno tenha realizado um pedido de renovação de matrícula que não foi processado.')

    fieldsets = (('Procedimento de Matrícula', {'fields': ('ano_letivo', 'periodo_letivo', 'processo', 'data', 'opcoes', 'motivo', 'excluir_pedido_matricula', 'matricula_periodo')}),)

    def clean(self):

        aluno = self.matricula_periodo.aluno
        estrutura = self.matricula_periodo.aluno.matriz.estrutura
        is_trancamento_voluntario = False
        if 'opcoes' in self.cleaned_data:
            is_trancamento_voluntario = int(self.cleaned_data['opcoes'].split(';')[1]) == SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE

        # Verificando integralização do período inicial do aluno
        if is_trancamento_voluntario and aluno and not aluno.cumpriu_requisito_trancamento_voluntario():
            raise forms.ValidationError('Não é possível realizar o trancamento voluntário pois o aluno não integralizou'
                                        'todos os componentes curriculares de seu período de ingresso.')

        if is_trancamento_voluntario and estrutura and estrutura.qtd_trancamento_voluntario is not None:
            # plano de retomada de aulas em virtude da pandemia (COVID19)
            if estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_CREDITO:
                ignorar_ids = self.matricula_periodo.aluno.matriculaperiodo_set.filter(matriculadiario__diario__turma__pertence_ao_plano_retomada=True).order_by('id').values_list('id', flat=True).distinct()
            else:
                ignorar_ids = self.matricula_periodo.aluno.matriculaperiodo_set.filter(turma__pertence_ao_plano_retomada=True).order_by('id').values_list('id', flat=True).distinct()
            if self.matricula_periodo.pk not in list(ignorar_ids):
                qtd_trancamentos = MatriculaPeriodo.objects.exclude(id__in=ignorar_ids).filter(situacao=SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE, aluno=self.matricula_periodo.aluno).count()
                if qtd_trancamentos >= estrutura.qtd_trancamento_voluntario:
                    raise forms.ValidationError('Não é possível realizar outro trancamento voluntário. O limite do curso já foi atingido.')

            if not self.cleaned_data.get('excluir_pedido_matricula') and PedidoMatriculaDiario.objects.filter(pedido_matricula__matricula_periodo_id=self.matricula_periodo.id, data_processamento__isnull=True).exists():
                raise forms.ValidationError('Não é possível realizar o trancamento pois o aluno possui pedido de matrícula em andamento.')

        return super().clean()

    def clean_excluir_pedido_matricula(self):
        excluir = self.cleaned_data.get('excluir_pedido_matricula')
        if not excluir and PedidoMatriculaDiario.objects.filter(pedido_matricula__matricula_periodo_id=self.matricula_periodo.id, data_processamento__isnull=True).exists():
            raise forms.ValidationError('Não é possível realizar o trancamento pois o aluno possui pedido de renovação de matrícula não processada no período letivo.')
        return excluir

    def get_choices(self):

        return [
            [f'{SituacaoMatricula.INTERCAMBIO};{SituacaoMatriculaPeriodo.INTERCAMBIO};{MatriculaDiario.SITUACAO_TRANCADO}', ProcedimentoMatricula.INTERCAMBIO],
            [f'{SituacaoMatricula.TRANCADO};{SituacaoMatriculaPeriodo.TRANCADA};{MatriculaDiario.SITUACAO_TRANCADO}', ProcedimentoMatricula.TRANCAMENTO_COMPULSORIO],
            [
                f'{SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE};{SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE};{MatriculaDiario.SITUACAO_TRANCADO}',
                ProcedimentoMatricula.TRANCAMENTO_VOLUNTARIO,
            ],
        ]


class TransferenciaCursoForm(ProcedimentoMatriculaForm):
    matriz_curso = forms.ModelChoiceFieldPlus(MatrizCurso.objects, label='Matriz/Curso de Destino')
    forma_ingresso = forms.ModelChoiceField(FormaIngresso.objects, label='Forma de Ingresso')
    turno = forms.ModelChoiceFieldPlus(Turno.objects, label='Turno')

    fieldsets = (
        ('Procedimento de Matrícula', {'fields': ('ano_letivo', 'periodo_letivo', 'processo', 'data', 'opcoes', 'matriz_curso', 'forma_ingresso', 'turno', 'motivo', 'matricula_periodo')}),
    )

    def __init__(self, matricula_periodo_pk, tipo, *args, **kwargs):
        self.tipo = tipo
        super().__init__(matricula_periodo_pk, *args, **kwargs)

        matricula_periodo = MatriculaPeriodo.objects.get(pk=matricula_periodo_pk)
        curso_campus = matricula_periodo.aluno.curso_campus

        if tipo == "Intercampus":
            qs_matriz_curso = MatrizCurso.objects.exclude(curso_campus__diretoria__setor__uo=curso_campus.diretoria.setor.uo)
        else:
            qs_matriz_curso = MatrizCurso.objects.filter(curso_campus__diretoria__setor__uo=curso_campus.diretoria.setor.uo)

        if self.instance.user and in_group(self.instance.user, 'Administrador Acadêmico'):
            qs_matriz_curso = qs_matriz_curso.filter(curso_campus__modalidade__nivel_ensino=matricula_periodo.aluno.curso_campus.modalidade.nivel_ensino)
        else:
            qs_matriz_curso = qs_matriz_curso.filter(curso_campus__modalidade=matricula_periodo.aluno.curso_campus.modalidade)

        self.fields['matriz_curso'].queryset = qs_matriz_curso.exclude(curso_campus=curso_campus)
        self.fields['forma_ingresso'].queryset = self.fields['forma_ingresso'].queryset.filter(ativo=True, descricao__contains='Transf')
        self.initial['turno'] = matricula_periodo.aluno.turno_id

    def get_choices(self):
        tipo_procedimento = self.tipo == "Intercampus" and ProcedimentoMatricula.TRANSFERENCIA_INTERCAMPUS or ProcedimentoMatricula.TRANSFERENCIA_CURSO
        return [[f'{SituacaoMatricula.TRANSFERIDO_INTERNO};{SituacaoMatriculaPeriodo.TRANSF_CURSO};{MatriculaDiario.SITUACAO_CANCELADO}', tipo_procedimento]]


class TransferenciaExternaForm(ProcedimentoMatriculaForm):
    def get_choices(self):
        return [
            [
                f'{SituacaoMatricula.TRANSFERIDO_EXTERNO};{SituacaoMatriculaPeriodo.TRANSF_EXTERNA};{MatriculaDiario.SITUACAO_CANCELADO}',
                ProcedimentoMatricula.TRANSFERENCIA_EXTERNA,
            ]
        ]


class MatriculaVinculoForm(ProcedimentoMatriculaForm):
    def get_choices(self):
        return [
            [
                f'{SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL};{SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL};{MatriculaDiario.SITUACAO_CANCELADO}',
                ProcedimentoMatricula.MATRICULA_VINCULO,
            ]
        ]


class ReintegrarAlunoForm(forms.ModelFormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)

    class Meta:
        model = ProcedimentoMatricula
        fields = (
            #'processo',
            'data', 'motivo')

    def __init__(self, matricula_periodo, *args, **kwargs):
        self.matricula_periodo = matricula_periodo
        super().__init__(*args, **kwargs)

    def clean(self):
        if not self.cleaned_data.get('ano_letivo'):
            return self.cleaned_data
        elif (self.cleaned_data['ano_letivo'].ano < self.matricula_periodo.ano_letivo.ano) or (
            self.cleaned_data['ano_letivo'].ano == self.matricula_periodo.ano_letivo.ano and int(self.cleaned_data['periodo_letivo']) <= self.matricula_periodo.periodo_letivo
        ):
            raise forms.ValidationError('Período de reintegração inválido.')
        else:
            return self.cleaned_data


class EvasaoEmLoteForm(forms.FormPlus):
    SUBMIT_LABEL = 'Pesquisar'
    METHOD = 'GET'

    ano_letivo = forms.ModelChoiceField(Ano.objects, label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES, help_text='Período letivo no qual a disciplina está sendo/foi certificada.')
    uo = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.locals, label='Campus', required=False)
    curso_campus = forms.ModelChoiceFieldPlus(
        CursoCampus.objects, label='Curso', required=False, widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('uo', 'diretoria__setor__uo__in')])
    )
    modalidade = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidade', required=False)

    def processar(self):

        ano_letivo = self.cleaned_data['ano_letivo']
        periodo_letivo = self.cleaned_data['periodo_letivo']
        uo = self.cleaned_data['uo']
        curso_campus = self.cleaned_data['curso_campus']
        modalidade = self.cleaned_data['modalidade']

        qs = Aluno.locals_uo.filter(
            matriculaperiodo__ano_letivo=ano_letivo,
            matriculaperiodo__periodo_letivo=periodo_letivo,
            matriculaperiodo__situacao__id=SituacaoMatriculaPeriodo.EM_ABERTO,
            matriz__isnull=False,
        )

        if uo:
            qs = qs.filter(curso_campus__diretoria__setor__uo__in=uo)
        if curso_campus:
            qs = qs.filter(curso_campus=curso_campus)
        if modalidade:
            qs = qs.filter(curso_campus__modalidade__in=modalidade)

        return qs.order_by('curso_campus')


class CertificarConhecimentoForm(forms.ModelFormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', help_text='Ano letivo da certificação.')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES, help_text='Período letivo no qual a disciplina está sendo/foi certificada.')

    class Meta:
        model = CertificacaoConhecimento
        fields = ('ano_letivo', 'periodo_letivo', 'data', 'nota', 'professores', 'servidores', 'ausente')

    fieldsets = (('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo'), ('data', 'ausente', 'nota'))}), ('Comissão', {'fields': ('professores', 'servidores')}))

    def __init__(self, aluno, componente_curricular, *args, **kwargs):
        self.aluno = aluno
        self.componente_curricular = componente_curricular
        super().__init__(*args, **kwargs)
        if componente_curricular.qtd_avaliacoes == 0:
            del self.fields['nota']
            self.fieldsets = (('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo'), ('data',))}), ('Comissão', {'fields': ('professores', 'servidores')}))
        self.fields['ano_letivo'].queryset = Ano.objects.filter(id__in=self.aluno.matriculaperiodo_set.values_list('ano_letivo_id', flat=True))
        if self.instance.pk:
            self.fields['ano_letivo'].initial = self.instance.matricula_periodo.ano_letivo.pk
            self.fields['periodo_letivo'].initial = self.instance.matricula_periodo.periodo_letivo

    def get_matricula_periodo_queryset(self):
        return self.aluno.matriculaperiodo_set.filter(ano_letivo=self.cleaned_data['ano_letivo'], periodo_letivo=self.cleaned_data['periodo_letivo'])

    def clean(self):
        if 'ano_letivo' not in self.cleaned_data:
            raise forms.ValidationError('O campo "Ano Letivo" é de preenchimento obrigatório.')

        if 'data' not in self.cleaned_data:
            raise forms.ValidationError('O campo "Data" é de preenchimento obrigatório.')

        nota = self.cleaned_data.get('nota')
        ausente = self.cleaned_data.get('ausente')
        if ausente and nota:
            raise forms.ValidationError('O campo "Nota" não pode ser preenchido se o campo "Ausente" estiver marcado.')
        if not ausente and nota is None:
            raise forms.ValidationError('O campo "Nota" é de preenchimento obrigatório se o campo "Ausente" não estiver marcado.')

        qs = self.get_matricula_periodo_queryset()
        if not qs.exists():
            raise forms.ValidationError('O aluno não está matriculado no ano/período informado.')

        matricula_periodo = qs[0]

        if PedidoMatriculaDiario.objects.filter(
            pedido_matricula__matricula_periodo__aluno=self.aluno, data_processamento__isnull=True, diario__componente_curricular=self.componente_curricular
        ).exists():
            raise forms.ValidationError('O aluno solicitou matrícula nessa disciplina. Aguarde o processamento do pedido de matrícula para realizar esse procedimeto.')

        if self.aluno.matriz.estrutura.numero_max_certificacoes > 0 and matricula_periodo.get_numero_certificacoes() >= self.aluno.matriz.estrutura.numero_max_certificacoes:
            raise forms.ValidationError(
                f'O aluno já atingiu o número de certificações no período que são de {self.aluno.matriz.estrutura.numero_max_certificacoes} certificações.'
            )

        if self.aluno.matriz.estrutura.percentual_max_aproveitamento:
            ch_componentes_aproveitaveis = (
                self.aluno.matriz.ch_componentes_obrigatorios
                + self.aluno.matriz.ch_componentes_optativos
                + self.aluno.matriz.ch_componentes_eletivos
                + self.aluno.matriz.ch_seminarios
            )
            pode_aproveitar = (
                self.aluno.get_ch_certificada_ou_aproveitada() + (self.componente_curricular.ch_presencial + self.componente_curricular.ch_pratica)
                <= self.aluno.matriz.estrutura.percentual_max_aproveitamento * ch_componentes_aproveitaveis / 100
            )
            if not pode_aproveitar:
                raise forms.ValidationError(
                    'Ao certificar essa disciplina, o aluno extrapola o percentual máximo de carga horária aproveitada/certificada que é de {}%%.'.format(
                        self.aluno.matriz.estrutura.percentual_max_aproveitamento
                    )
                )
        pode_cursar, msg = self.aluno.pode_cursar_componente_curricular(self.componente_curricular)
        if not pode_cursar:
            raise forms.ValidationError(f'Essa disciplina não pode ser certificada, pois não atende a todos os critérios de co/pré-requisitos: {msg}.')

        if self.aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento:
            pode_aproveitar = (
                self.aluno.get_creditos_certificados_ou_aproveitados() + self.componente_curricular.componente.ch_qtd_creditos
                <= self.aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento
            )
            if not pode_aproveitar:
                raise forms.ValidationError(
                    'Ao certificar essa disciplina, o aluno extrapola a quantidade máxima de créditos aproveitados/certificados que é de {}.'.format(
                        self.aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento
                    )
                )

        if self.aluno.curso_campus.modalidade.descricao == 'Integrado':
            if self.componente_curricular.nucleo.descricao in ['Fundamental', 'Estruturante', 'Tecnológico']:
                raise forms.ValidationError(
                    'Para os cursos técnicos na forma integrada, é vedada a certificação de conhecimentos de disciplinas referentes aos núcleos fundamental e estruturante.'
                )

        if self.componente_curricular.tipo in [
            ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
            ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
            ComponenteCurricular.TIPO_SEMINARIO,
        ]:
            if not in_group(self.request.user, 'edu Administrador'):
                raise forms.ValidationError(
                    'Não é possível fazer certificação do conhecimento para componentes curriculares de prática profissional ou de trabalho de conclusão de curso ou de seminário.'
                )

        matriculas_periodo = MatriculaPeriodo.objects.filter(
            aluno=self.aluno, ano_letivo=self.cleaned_data.get('ano_letivo'), periodo_letivo=self.cleaned_data.get('periodo_letivo')
        )
        qs1 = MatriculaDiario.objects.filter(
            situacao__in=[MatriculaDiario.SITUACAO_TRANCADO], diario__componente_curricular=self.componente_curricular, matricula_periodo__in=matriculas_periodo
        )
        qs2 = MatriculaDiarioResumida.objects.filter(
            situacao__in=[MatriculaDiario.SITUACAO_TRANCADO], equivalencia_componente__componente=self.componente_curricular.componente, matricula_periodo__in=matriculas_periodo
        )
        if qs1.exists() or qs2.exists():
            raise forms.ValidationError(
                'Não é possível realizar certificação de conhecimento no período letivo informado, pois o aluno trancou a disciplina nesse período. Informe um período letivo diferente.'
            )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        self.instance.matricula_periodo = self.get_matricula_periodo_queryset()[0]
        self.instance.componente_curricular = self.componente_curricular
        return super().save(*args, **kwargs)


class AproveitamentoEstudoForm(forms.ModelFormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', help_text='Ano letivo do aproveitamento.')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES, help_text='Período letivo do aproveitamento.')

    class Meta:
        model = AproveitamentoEstudo
        fields = ('ano_letivo', 'periodo_letivo', 'data', 'escola_origem', 'frequencia', 'nota', 'professores', 'servidores')

    fieldsets = (
        ('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo'), ('data', 'escola_origem'), ('frequencia', 'nota'))}),
        ('Comissão', {'fields': ('professores', 'servidores')}),
    )

    def __init__(self, aluno, componente_curricular, *args, **kwargs):
        self.aluno = aluno
        self.componente_curricular = componente_curricular

        super().__init__(*args, **kwargs)
        if componente_curricular.qtd_avaliacoes == 0:
            del self.fields['nota']
            self.fieldsets = (
                ('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo'), ('data', 'escola_origem'), ('frequencia',))}),
                ('Comissão', {'fields': ('professores', 'servidores')}),
            )
        self.fields['ano_letivo'].queryset = Ano.objects.filter(id__in=self.aluno.matriculaperiodo_set.values_list('ano_letivo_id', flat=True))
        if self.instance and self.instance.pk:
            self.fields['ano_letivo'].initial = self.instance.matricula_periodo.ano_letivo.pk
            self.fields['periodo_letivo'].initial = self.instance.matricula_periodo.periodo_letivo

    def get_matricula_periodo_queryset(self):
        return self.aluno.matriculaperiodo_set.filter(ano_letivo=self.cleaned_data['ano_letivo'], periodo_letivo=self.cleaned_data['periodo_letivo'])

    def clean(self):

        if not 'ano_letivo' in self.cleaned_data or 'periodo_letivo' not in self.cleaned_data:
            return self.cleaned_data

        if PedidoMatriculaDiario.objects.filter(
            pedido_matricula__matricula_periodo__aluno=self.aluno, data_processamento__isnull=True, diario__componente_curricular=self.componente_curricular
        ).exists():
            raise forms.ValidationError('O aluno solicitou matrícula nessa disciplina. Aguarde o processamento do pedido de matrícula para realizar esse procedimeto.')

        if not self.get_matricula_periodo_queryset().exists():
            raise forms.ValidationError('O aluno não está matriculado no ano/período informado.')

        if (
            self.aluno.matriz.estrutura.percentual_max_aproveitamento
            and not self.aluno.matriz.estrutura.formas_ingresso_ignoradas_aproveitamento.filter(pk=self.aluno.forma_ingresso.pk).exists()
        ):
            ch_componentes_aproveitaveis = (
                self.aluno.matriz.ch_componentes_obrigatorios
                + self.aluno.matriz.ch_componentes_optativos
                + self.aluno.matriz.ch_componentes_eletivos
                + self.aluno.matriz.ch_seminarios
            )
            pode_aproveitar = (
                self.aluno.get_ch_certificada_ou_aproveitada() + (self.componente_curricular.ch_presencial + self.componente_curricular.ch_pratica)
                <= self.aluno.matriz.estrutura.percentual_max_aproveitamento * ch_componentes_aproveitaveis / 100
            )
            if not pode_aproveitar:
                raise forms.ValidationError(
                    'Ao aproveitar essa disciplina, o aluno extrapola o percentual máximo de carga horária aproveitada/certificada que é de {}%%.'.format(
                        self.aluno.matriz.estrutura.percentual_max_aproveitamento
                    )
                )
        pode_cursar, msg = self.aluno.pode_cursar_componente_curricular(self.componente_curricular)
        if not pode_cursar:
            raise forms.ValidationError(f'Essa disciplina não pode ser aproveitada, pois não atende a todos os critérios de co/pré-requisitos: {msg}.')

        if self.aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento:
            pode_aproveitar = (
                self.aluno.get_creditos_certificados_ou_aproveitados() + self.componente_curricular.componente.ch_qtd_creditos
                <= self.aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento
            )
            if not pode_aproveitar:
                raise forms.ValidationError(
                    'Ao aproveitar essa disciplina, o aluno extrapola a quantidade máxima de créditos aproveitados/certificados que é de {}.'.format(
                        self.aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento
                    )
                )

        if self.componente_curricular.tipo in [ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL, ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO]:
            if not in_group(self.request.user, 'edu Administrador'):
                raise forms.ValidationError(
                    'Não é possível fazer aproveitamento de estudos de componentes curriculares de prática profissional ou de trabalho de conclusão de curso.'
                )

        matriculas_periodo = MatriculaPeriodo.objects.filter(
            aluno=self.aluno, ano_letivo=self.cleaned_data.get('ano_letivo'), periodo_letivo=self.cleaned_data.get('periodo_letivo')
        )
        qs1 = MatriculaDiario.objects.filter(
            situacao__in=[MatriculaDiario.SITUACAO_TRANCADO], diario__componente_curricular=self.componente_curricular, matricula_periodo__in=matriculas_periodo
        )
        qs2 = MatriculaDiarioResumida.objects.filter(
            situacao__in=[MatriculaDiario.SITUACAO_TRANCADO], equivalencia_componente__componente=self.componente_curricular.componente, matricula_periodo__in=matriculas_periodo
        )
        if qs1.exists() or qs2.exists():
            raise forms.ValidationError(
                'Não é possível realizar aproveitamento de estudos no período letivo informado, pois o aluno trancou a disciplina nesse período. Informe um período letivo diferente.'
            )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        self.instance.matricula_periodo = self.get_matricula_periodo_queryset()[0]
        self.instance.componente_curricular = self.componente_curricular
        super().save(*args, **kwargs)


class ImportacaoAlunosForm(forms.FormPlus):
    prefixo = forms.CharField(
        label='Prefixo', required=False, help_text='Caso o prefixo não seja informado, serão importados todos os alunos que foram atualizados desde a última importação.'
    )

    def processar(self):
        if self.cleaned_data['prefixo']:
            call_command('edu_importar_dados', self.cleaned_data['prefixo'], verbosity='0')
        else:
            call_command('edu_importar_dados', verbosity='0')

    def clean_prefixo(self):
        if 5 > len(self.cleaned_data['prefixo']) > 0:
            raise forms.ValidationError("Insira um prefixo com no mínimo 5 (cinco) dígitos")
        else:
            return self.cleaned_data['prefixo']


class ListarDiarioMatriculaAlunoForm(forms.Form):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Listar Diários'

    fieldsets = (('Filtros', {'fields': (('diretoria', 'componente'), ('outros_componentes',), ('outras_matrizes',), ('ignorar_futuros'))}),)

    diretoria = forms.ModelChoiceField(Diretoria.objects.none(), label='Diretoria', required=True)
    componente = forms.ModelChoiceFieldPlus(Componente.objects, label='Componente', required=False)
    outros_componentes = forms.BooleanField(label='Diários em Outras Matrizes', required=False, help_text='Apenas diários de componentes em outras matrizes comuns à matriz do aluno.')
    outras_matrizes = forms.BooleanField(label='Outros Diários', required=False, help_text='Apenas diários de componentes que não fazem parte da matriz do aluno. Poderá haver quebra de pré e co requisito.')
    ignorar_futuros = forms.BooleanField(
        label='Excluir Períodos Futuros', required=False, help_text='Apenas diários de componentes relacionados a períodos igual ou inferior ao período atual do aluno no curso.'
    )

    def __init__(self, matricula_periodo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.objects.filter(setor__uo_id=matricula_periodo.aluno.curso_campus.diretoria.setor.uo.pk)
        self.matricula_periodo = matricula_periodo
        self.fields['diretoria'].initial = matricula_periodo.aluno.curso_campus.diretoria.pk
        self.fields['ignorar_futuros'].initial = True

    def clean(self):
        if self.matricula_periodo.situacao.pk not in [SituacaoMatriculaPeriodo.MATRICULADO, SituacaoMatriculaPeriodo.EM_ABERTO]:
            raise forms.ValidationError('A situação do aluno no período deve ser Matriculado ou Em Aberto.')
        return self.cleaned_data

    def processar(self):
        if not self.matricula_periodo.aluno.matriz:
            return Diario.objects.none()

        diarios = self.matricula_periodo.aluno.get_diarios_disponiveis_matricular_por_diretoria(
            self.cleaned_data.get('diretoria'), self.cleaned_data.get('outros_componentes'), self.cleaned_data.get('outras_matrizes'), self.cleaned_data.get('ignorar_futuros'), self.cleaned_data.get('componente')
        )

        return diarios


class MatricularDiarioForm(forms.Form):
    SUBMIT_LABEL = 'Matricular'
    confirmar = forms.BooleanField(label='Confirmar Matrícula', required=False)

    def clean_confirmar(self):
        confirmar = self.cleaned_data.get('confirmar')
        if not confirmar:
            raise ValidationError('Clique em Confirmar Matrícula para concluir a matrícula do aluno no diário.')

    def processar(self, matricula_periodo, diario):
        if not MatriculaDiario.objects.filter(matricula_periodo=matricula_periodo, diario=diario).exists():
            matricula_diario = MatriculaDiario()
            matricula_diario.diario = diario
            matricula_diario.matricula_periodo = matricula_periodo
            matricula_diario.situacao = MatriculaDiario.SITUACAO_CURSANDO
            matricula_diario.save()
            matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
            matricula_periodo.save()
            if matricula_periodo.aluno.situacao.pk != SituacaoMatricula.MATRICULADO:
                matricula_periodo.aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                matricula_periodo.aluno.save()


class MatricularAlunoTurmaForm(forms.Form):
    METHOD = 'POST'
    turma = forms.ModelChoiceField(Turma.objects, label='Turma', widget=forms.RadioSelect(), empty_label=None)

    def __init__(self, matricula_periodo, *args, **kwargs):
        self.matricula_periodo = matricula_periodo
        super().__init__(*args, **kwargs)
        pks = []
        for turma in matricula_periodo.aluno.get_turmas_matricula_online():
            pks.append(turma.pk)
        self.fields['turma'].queryset = Turma.objects.filter(pk__in=pks)
        # self.fields['turma'].queryset = Turma.objects.filter(curso_campus=self.matricula_periodo.aluno.curso_campus, ano_letivo=self.matricula_periodo.ano_letivo, periodo_letivo=self.matricula_periodo.periodo_letivo, periodo_matriz=self.matricula_periodo.aluno.periodo_atual)

    def processar(self):
        turma = self.cleaned_data.get('turma')
        matriculas_periodo = MatriculaPeriodo.objects.filter(pk=self.matricula_periodo.pk)
        turma.matricular_alunos(matriculas_periodo)


class MatricularAlunoAvulsoDiarioForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Inserir Aluno'
    aluno = forms.ModelChoiceFieldPlus(Aluno.locals, label='Aluno', widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS), required=True)

    def __init__(self, diario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diario = diario
        self.fields['aluno'].queryset = (
            Aluno.locals.filter(
                situacao__pk__in=[
                    SituacaoMatricula.MATRICULADO,
                    SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
                    SituacaoMatricula.TRANCADO,
                    SituacaoMatricula.INTERCAMBIO,
                    SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL,
                ],
                matriculaperiodo__situacao__pk__in=[
                    SituacaoMatriculaPeriodo.MATRICULADO,
                    SituacaoMatriculaPeriodo.EM_ABERTO,
                    SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
                ],
                matriz__isnull=False,
            )
            .exclude(matriculaperiodo__matriculadiario__diario=diario)
            .distinct()
        )

    def clean(self):
        aluno = self.cleaned_data.get('aluno')
        if not aluno:
            return self.cleaned_data
        ignorar_quebra_requisito = in_group(self.request.user, 'Administrador Acadêmico')
        pode_ser_matriculado, msg = aluno.pode_ser_matriculado_no_diario(self.diario, ignorar_quebra_requisito)
        if not pode_ser_matriculado:
            raise forms.ValidationError(msg)
        matricula_periodo = self.cleaned_data['aluno'].get_ultima_matricula_periodo()
        if not in_group(self.request.user, 'Administrador Acadêmico') and (
            matricula_periodo.ano_letivo != self.diario.ano_letivo or matricula_periodo.periodo_letivo != self.diario.periodo_letivo
        ):
            raise forms.ValidationError('Alunos com última matrícula período diferente do período letivo do diário não podem ser inseridos.')

        if self.diario.componente_curricular.componente.pk in aluno.get_ids_componentes_cumpridos():
            raise forms.ValidationError('O aluno já cursou o componente deste diário.')

        return self.cleaned_data

    def processar(self):
        matricula_periodo = self.cleaned_data['aluno'].matriculaperiodo_set.get(ano_letivo=self.diario.ano_letivo, periodo_letivo=self.diario.periodo_letivo)
        if not MatriculaDiario.objects.filter(matricula_periodo=matricula_periodo, diario=self.diario).exists():
            matricula_diario = MatriculaDiario()
            matricula_diario.diario = self.diario
            matricula_diario.matricula_periodo = matricula_periodo
            matricula_diario.situacao = MatriculaDiario.SITUACAO_CURSANDO
            matricula_diario.save()
            if not matricula_periodo.aluno.situacao.pk == SituacaoMatricula.MATRICULADO:
                matricula_periodo.aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                matricula_periodo.aluno.save()
            if not matricula_periodo.situacao == SituacaoMatriculaPeriodo.MATRICULADO:
                matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
                matricula_periodo.save()


class ProjetoFinalForm(forms.ModelFormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus', required=False)
    local_defesa = forms.ModelChoiceFieldPlus(
        Sala.ativas, label='Local', required=False, widget=AutocompleteWidget(search_fields=Sala.SEARCH_FIELDS, form_filters=[('uo', 'predio__uo__in')])
    )
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, required=True, label='Período Letivo')
    orientador = forms.ModelChoiceField(queryset=Vinculo.objects, widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS), label='Orientador', required=True)
    presidente = forms.ModelChoiceField(queryset=Professor.objects, widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS), label='Presidente', required=True)

    fieldsets = (
        ('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo'), 'titulo', 'resumo', 'tipo', 'informacao_complementar')}),
        ('Dados da Orientação', {'fields': ('orientador', 'coorientadores')}),
        ('Dados da Defesa', {'fields': ('data_defesa', 'data_deposito', 'uo', 'local_defesa', 'defesa_online')}),
        (
            'Dados da Banca',
            {'fields': ('presidente', 'examinador_interno', ('examinador_externo', 'is_examinador_externo'), ('terceiro_examinador', 'is_terceiro_examinador_externo'))},
        ),
        ('Dados da Suplência da Banca', {'fields': ('suplente_interno', ('suplente_externo', 'is_suplente_externo'), ('terceiro_suplente', 'is_terceiro_suplente_externo'))}),
    )

    class Meta:
        model = ProjetoFinal
        fields = (
            'titulo',
            'resumo',
            'tipo',
            'informacao_complementar',
            'suplente_interno',
            'is_suplente_externo',
            'suplente_externo',
            'data_defesa',
            'data_deposito',
            'local_defesa',
            'defesa_online',
            'presidente',
            'examinador_interno',
            'is_examinador_externo',
            'examinador_externo',
            'terceiro_suplente',
            'is_terceiro_suplente_externo',
            'terceiro_examinador',
            'is_terceiro_examinador_externo',
            'coorientadores'
        )

    def __init__(self, aluno, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not aluno.matriz or not aluno.matriz.exige_tcc:
            self.fields['tipo'].choices = [['Relatório de Projeto', 'Relatório de Projeto']]
        uo = aluno.curso_campus.diretoria.setor.uo
        self.fields['uo'].initial = uo.id
        if self.instance.pk:
            self.fields['ano_letivo'].initial = self.instance.matricula_periodo.ano_letivo.pk
            self.fields['periodo_letivo'].initial = self.instance.matricula_periodo.periodo_letivo
            if self.instance.local_defesa:
                self.fields['uo'].initial = self.instance.local_defesa.predio.uo.id
        self.aluno = aluno
        qs_prestadores = Vinculo.objects.prestadores()
        qs_servidores = Vinculo.objects.servidores()
        if not in_group(self.request.user, 'Administrador Acadêmico'):
            if not self.instance.pk:
                qs_servidores = qs_servidores.filter(pessoa__excluido=False)
            else:
                qs_servidores = qs_servidores.filter(pessoa__excluido=False) | qs_servidores.filter(pessoa__excluido=True, pk__in=[self.instance.orientador.vinculo.pk])
            qs_prestadores = qs_prestadores.filter(pessoa__excluido=False)
        self.fields['orientador'].queryset = (qs_servidores | qs_prestadores).distinct()
        if self.instance.pk:
            self.fields['orientador'].initial = self.instance.orientador.vinculo.pk

        qs_pessoafisica = PessoaFisica.objects.filter(excluido=False).exclude(eh_aluno=True)
        if Configuracao.get_valor_por_chave('edu', 'tipo_ata_projeto_final') == 'eletronica':
            qs_pessoafisica = qs_pessoafisica.filter(username__isnull=False)
        self.fields['examinador_interno'].queryset = qs_pessoafisica.filter(funcionario__isnull=False)
        self.fields['examinador_externo'].queryset = qs_pessoafisica
        self.fields['terceiro_examinador'].queryset = qs_pessoafisica
        self.fields['suplente_interno'].queryset = qs_pessoafisica
        self.fields['suplente_externo'].queryset = qs_pessoafisica
        self.fields['terceiro_suplente'].queryset = qs_pessoafisica
        self.fields['coorientadores'].queryset = qs_pessoafisica

    def clean(self):
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')

        if ano_letivo and periodo_letivo:
            qs_matricula_periodo = MatriculaPeriodo.objects.filter(aluno=self.aluno, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)
            if not qs_matricula_periodo.exists():
                raise forms.ValidationError('O aluno não possui matrícula no período ano/período letivo selecionado.')
            else:
                self.matricula_periodo = qs_matricula_periodo[0]
                if self.matricula_periodo.situacao.pk == SituacaoMatriculaPeriodo.EM_ABERTO:
                    raise forms.ValidationError('A situação do aluno no período selecionado é "Em Aberto".')
                if ProjetoFinal.objects.filter(matricula_periodo=self.matricula_periodo).exclude(pk=self.instance.pk).exists():
                    raise forms.ValidationError('O aluno já possui um trabalho de conclusão de curso no ano/período letivo selecionado.')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        orientador = self.cleaned_data['orientador']
        obj = super().save(False)
        qs = Professor.objects.filter(vinculo__id=orientador.pk)
        if qs.exists():
            obj.orientador = qs[0]
        else:
            professor = Professor()
            professor.vinculo = orientador
            professor.save()
            obj.orientador = professor
            Group.objects.get(name='Professor').user_set.add(professor.vinculo.user)
        obj.matricula_periodo = self.matricula_periodo
        obj.save()
        for coorientador in self.cleaned_data['coorientadores']:
            obj.coorientadores.add(coorientador)

        if Configuracao.get_valor_por_chave('edu', 'tipo_ata_projeto_final') == 'eletronica':
            ata = AtaEletronica.objects.filter(projeto_final=obj).first()
            if ata:
                ata.criar_assinaturas()


class ParticipacaoProjetoFinalForm(forms.Form):
    METHOD = 'GET'
    participante = forms.ChoiceField(choices=[])

    def __init__(self, projeto_final, *args, **kwargs):
        super().__init__(*args, **kwargs)
        participantes = []
        if projeto_final.orientador:
            participantes.append(['orientador', 'Orientador - ' + projeto_final.orientador.vinculo.pessoa.nome])
        if projeto_final.presidente:
            participantes.append(['presidente', 'Presidente - ' + projeto_final.presidente.vinculo.pessoa.nome])
        if projeto_final.examinador_interno:
            participantes.append(['examinador_interno', 'Examinador (Interno) - ' + projeto_final.examinador_interno.nome])
        if projeto_final.examinador_externo:
            if projeto_final.is_examinador_externo:
                participantes.append(['examinador_externo', 'Segundo Examinador (Externo) - ' + projeto_final.examinador_externo.nome])
            else:
                participantes.append(['examinador_externo', 'Segudno Examinador (Interno) - ' + projeto_final.examinador_externo.nome])
        if projeto_final.terceiro_examinador:
            if projeto_final.is_terceiro_examinador_externo:
                participantes.append(['terceiro_examinador', 'Terceiro Examinador (Externo) - ' + projeto_final.terceiro_examinador.nome])
            else:
                participantes.append(['terceiro_examinador', 'Terceiro Examinador (Interno) - ' + projeto_final.terceiro_examinador.nome])
        if projeto_final.suplente_interno:
            participantes.append(['suplente_interno', 'Examinador Suplente Interno - ' + projeto_final.suplente_interno.nome])
        if projeto_final.suplente_externo:
            if projeto_final.is_suplente_externo:
                participantes.append(['suplente_externo', 'Primeiro Suplente (Externo) - ' + projeto_final.suplente_externo.nome])
            else:
                participantes.append(['suplente_externo', 'Primeiro Suplente (Interno) - ' + projeto_final.suplente_externo.nome])
        if projeto_final.terceiro_suplente:
            if projeto_final.is_terceiro_suplente_externo:
                participantes.append(['suplente_externo', 'Segundo Suplente (Externo) - ' + projeto_final.terceiro_suplente.nome])
            else:
                participantes.append(['suplente_externo', 'Segundo Suplente (Interno) - ' + projeto_final.terceiro_suplente.nome])

        self.fields['participante'].choices = participantes


class LancarResultadoProjetoFinalForm(forms.ModelForm):
    DOCUMENTO_URL = 1
    DOCUMENTO_ARQUIVO = 2
    TIPO_DOCUMENTO_CHOICES = [[DOCUMENTO_URL, 'URL'], [DOCUMENTO_ARQUIVO, 'Arquivo']]

    resultado_data = forms.DateTimeFieldPlus(label='Data da Apresentação', required=True)
    situacao = forms.ChoiceField(label="Situação", choices=ProjetoFinal.SITUACAO_CHOICES, required=True)
    tipo_documento = forms.ChoiceField(choices=TIPO_DOCUMENTO_CHOICES, widget=forms.RadioSelect(), label='Tipo de Documento')
    ata = forms.FileFieldPlus(label='Ata de Defesa / Documento Comprobatório de Prática', required=True)
    documento = forms.FileFieldPlus(label='Arquivo do TCC / Relatório', required=False, filetypes=['pdf'])

    class Meta:
        model = ProjetoFinal
        fields = ('resultado_data', 'nota', 'situacao', 'tipo_documento', 'documento', 'documento_url', 'ata')

    class Media:
        js = ('/static/edu/js/LancarResultadoProjetoFinalForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_ata = Configuracao.get_valor_por_chave('edu', 'tipo_ata_projeto_final') or 'fisica'
        if self.tipo_ata == 'eletronica':
            self.fields['consideracoes'] = forms.CharFieldPlus(label='Observação / Apreciações', widget=forms.Textarea())
            self.fields['ata'].required = False
            self.fieldsets = (
                ('Resultado', {'fields': (('resultado_data', 'situacao'), 'nota', 'consideracoes')}),
                ('Arquivos', {'fields': ('tipo_documento', 'documento', 'documento_url')}),
            )
        else:
            self.fieldsets = (
                ('Resultado', {'fields': (('resultado_data', 'situacao'), 'nota')}),
                ('Arquivos', {'fields': ('tipo_documento', 'documento', 'documento_url', 'ata')}),
            )

    def save(self, *args, **kwargs):
        projeto_final = super().save(*args, **kwargs)
        if self.tipo_ata == 'eletronica':
            consideracoes = self.cleaned_data['consideracoes']
            if not AtaEletronica.objects.filter(projeto_final=projeto_final).exists():
                ata = AtaEletronica.objects.create(projeto_final=projeto_final, consideracoes=consideracoes)
                ata.criar_assinaturas()


class UploadDocumentoProjetoFinalForm(forms.ModelForm):
    DOCUMENTO_URL = 1
    DOCUMENTO_ARQUIVO = 2
    TIPO_DOCUMENTO_CHOICES = [[DOCUMENTO_URL, 'URL'], [DOCUMENTO_ARQUIVO, 'Arquivo']]

    tipo_documento_final = forms.ChoiceField(choices=TIPO_DOCUMENTO_CHOICES, widget=forms.RadioSelect(), label='Tipo de Documento')
    documento_final = forms.FileFieldPlus(label='Arquivo do TCC / Relatório', required=False, filetypes=['pdf'])

    class Meta:
        model = ProjetoFinal
        fields = ('tipo_documento_final', 'documento_final', 'documento_final_url',)

    class Media:
        js = ('/static/edu/js/UploadDocumentoProjetoFinalForm.js',)

    fieldsets = (
        ('Arquivo', {'fields': ('tipo_documento_final', 'documento_final', 'documento_final_url')}),
    )


class SalvarRelatorioForm(forms.Form):
    descricao = forms.CharFieldPlus(label='Descrição')

    def __init__(self, *args, **kwargs):
        self.tipo = kwargs.pop('tipo')
        super().__init__(*args, **kwargs)

    def processar(self, query_string):
        h = HistoricoRelatorio()
        h.descricao = self.cleaned_data['descricao']
        h.query_string = query_string
        h.tipo = self.tipo
        h.save()
        return h


class IndeferirAtividadeComplementarForm(forms.ModelFormPlus):
    razao_indeferimento = forms.CharField(widget=forms.Textarea(), required=True, label='Razão do Indeferimento')

    class Meta:
        model = AtividadeComplementar
        fields = ('razao_indeferimento',)

    def save(self, *args, **kwargs):
        self.instance.deferida = False
        super().save(*args, **kwargs)


class AtividadeComplementarForm(forms.ModelFormPlus):
    VINCULADO_CURSO = 1
    NAO_VINCULADO_CURSO = 2
    VINCULADO_CHOICES = [[VINCULADO_CURSO, 'Curricular'], [NAO_VINCULADO_CURSO, 'Não curricular']]
    ano_letivo = forms.ModelChoiceField(Ano.objects, label='Ano Letivo')
    aluno = forms.ModelChoiceField(Aluno.objects, widget=forms.HiddenInput())
    tipo = forms.ModelChoiceField(TipoAtividadeComplementar.objects)
    vinculacao = forms.ChoiceField(label='Vinculação', choices=VINCULADO_CHOICES, widget=forms.RadioSelect(), initial=VINCULADO_CURSO, required=True)

    fieldsets = (
        ('Tipo e Período Letivo', {'fields': (('ano_letivo', 'periodo_letivo'), 'vinculacao', 'tipo')}),
        ('Dados da Atividade', {'fields': ('aluno', 'descricao', 'data_atividade', 'carga_horaria', 'informacoes_complementares', 'documento')}),
    )

    class Meta:
        model = AtividadeComplementar
        exclude = ('deferida', 'razao_indeferimento')

    class Media:
        js = ('/static/edu/js/AtividadeComplementarForm.js',)

    def __init__(self, *args, **kwargs):
        self.as_aluno = kwargs.pop('as_aluno', False)
        super().__init__(*args, **kwargs)

        self.aluno_obj = Aluno.objects.get(pk=self.initial['aluno'])
        self.tipos_vinculados = TipoAtividadeComplementar.objects.filter(itemconfiguracaoatividadecomplementar__configuracao__matriz__aluno=self.aluno_obj).distinct()
        self.tipos_nao_vinculados = TipoAtividadeComplementar.objects.exclude(itemconfiguracaoatividadecomplementar__configuracao__matriz__aluno=self.aluno_obj).distinct()
        self.fields['ano_letivo'].queryset = Ano.objects.filter(matriculaperiodo__aluno=self.aluno_obj).distinct()
        self.fields['tipo'].queryset = TipoAtividadeComplementar.objects.all()

        if self.instance.pk and self.instance.tipo in self.tipos_nao_vinculados:
            self.fields['vinculacao'].initial = self.NAO_VINCULADO_CURSO

        if self.as_aluno:
            self.fields['documento'].required = True

    def clean_tipo(self):
        tipo = self.cleaned_data.get('tipo')
        vinculacao = int(self.data.get('vinculacao'))
        if vinculacao == self.VINCULADO_CURSO and tipo not in self.tipos_vinculados:
            raise ValidationError('Selecione um tipo vinculado.')
        if vinculacao == self.NAO_VINCULADO_CURSO and tipo not in self.tipos_nao_vinculados:
            raise ValidationError('Selecione um tipo não vinculado.')
        return self.cleaned_data['tipo']

    def clean_deferida(self):
        deferida = self.cleaned_data.get('deferida')
        razao_indeferimento = self.data.get('razao_indeferimento')
        if self.pode_realizar_procedimentos:
            if deferida and razao_indeferimento:
                raise ValidationError('Remova a razão de indeferimento.')
            if not deferida and not razao_indeferimento:
                raise ValidationError('Adicione uma razão de indeferimento.')
        return deferida

    def clean(self):
        aluno = (self.cleaned_data.get('aluno'),)
        ano_letivo = (self.cleaned_data.get('ano_letivo'),)
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        qs_matricula_periodo = MatriculaPeriodo.objects.filter(aluno=aluno[0], ano_letivo=ano_letivo[0], periodo_letivo=periodo_letivo)

        if not qs_matricula_periodo.exists():
            raise ValidationError('Ano/Período Letivo inválidos')

        if qs_matricula_periodo[0].situacao.pk == SituacaoMatriculaPeriodo.EM_ABERTO:
            raise forms.ValidationError('A situação do aluno no período selecionado é "Em aberto".')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        if not self.as_aluno:
            self.instance.deferida = True
            self.instance.save()
        else:
            self.instance.save()
            self.instance.enviar_email_coordenador()


class AtividadeAprofundamentoForm(forms.ModelFormPlus):
    aluno = forms.ModelChoiceField(Aluno.objects, widget=forms.HiddenInput())

    fieldsets = (
        ('Tipo e Período Letivo', {'fields': (('ano_letivo', 'periodo_letivo'), 'tipo')}),
        ('Dados da Atividade', {'fields': ('aluno', 'descricao', ('data_atividade', 'carga_horaria'), 'informacoes_complementares', 'documento')}),
    )

    class Meta:
        model = AtividadeAprofundamento
        exclude = ('deferida', 'razao_indeferimento')

    def __init__(self, *args, **kwargs):
        self.as_aluno = kwargs.pop('as_aluno', False)
        super().__init__(*args, **kwargs)
        self.aluno_obj = Aluno.objects.get(pk=self.initial['aluno'])
        pks = ItemConfiguracaoAtividadeAprofundamento.objects.filter(configuracao=self.aluno_obj.matriz.configuracao_atividade_aprofundamento_id).values_list('tipo', flat=True)
        self.fields['tipo'].queryset = self.fields['tipo'].queryset.filter(pk__in=pks)

    def clean_deferida(self):
        deferida = self.cleaned_data.get('deferida')
        razao_indeferimento = self.data.get('razao_indeferimento')
        if self.pode_realizar_procedimentos:
            if deferida and razao_indeferimento:
                raise ValidationError('Remova a razão de indeferimento.')
            if not deferida and not razao_indeferimento:
                raise ValidationError('Adicione uma razão de indeferimento.')
        return deferida

    def clean_carga_horaria(self):
        carga_horaria = self.cleaned_data.get('carga_horaria')
        tipo = self.cleaned_data.get('tipo')
        if tipo:
            item_configuracao = ItemConfiguracaoAtividadeAprofundamento.objects.get(configuracao=self.aluno_obj.matriz.configuracao_atividade_aprofundamento_id, tipo=tipo)
            if carga_horaria and tipo and item_configuracao.carga_horaria and carga_horaria > item_configuracao.carga_horaria:
                raise forms.ValidationError(f'A carga horária dessa atividade deve ser de {item_configuracao.carga_horaria} horas')
        return carga_horaria

    def clean(self):
        aluno = self.cleaned_data.get('aluno')
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        qs_matricula_periodo = MatriculaPeriodo.objects.filter(aluno=aluno, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)

        if not qs_matricula_periodo.exists():
            raise ValidationError('Ano/Período Letivo inválidos')

        if qs_matricula_periodo[0].situacao.pk == SituacaoMatriculaPeriodo.EM_ABERTO:
            raise forms.ValidationError('A situação do aluno no período selecionado é "Em aberto".')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        if not self.as_aluno:
            self.instance.deferida = True
            self.instance.save()
        else:
            self.instance.save()
            self.instance.enviar_email_coordenador()


class VincularConfiguracaoAtividadeComplementarForm(forms.Form):
    matrizes = forms.MultipleModelChoiceFieldPlus(Matriz.objects)


class VincularConfiguracaoAtividadeAprofundamentoForm(forms.Form):
    matrizes = forms.MultipleModelChoiceFieldPlus(Matriz.objects)


class ItemConfiguracaoAtividadeComplementarForm(forms.ModelForm):
    tipo = forms.ModelChoiceField(TipoAtividadeComplementar.objects, widget=forms.Select(attrs=dict(style='width:600px')))

    def __init__(self, *args, **kwargs):
        configuracao_pk = kwargs.pop('configuracao_pk')
        super(self.__class__, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tipo'].widget = forms.HiddenInput()
        else:
            self.fields['tipo'].queryset = TipoAtividadeComplementar.objects.exclude(itemconfiguracaoatividadecomplementar__configuracao__pk=configuracao_pk)

    class Meta:
        model = ItemConfiguracaoAtividadeComplementar
        exclude = ('configuracao', 'ch_max_periodo', 'ch_max_curso', 'ch_min_curso', 'ch_por_evento')


class ItemConfiguracaoAtividadeAprofundamentoForm(forms.ModelForm):
    tipo = forms.ModelChoiceField(TipoAtividadeAprofundamento.objects, widget=forms.Select(attrs=dict(style='width:600px')))

    def __init__(self, *args, **kwargs):
        configuracao_pk = kwargs.pop('configuracao_pk')
        super(self.__class__, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['tipo'].widget = forms.HiddenInput()
        else:
            self.fields['tipo'].queryset = TipoAtividadeAprofundamento.objects.exclude(itemconfiguracaoatividadeaprofundamento__configuracao__pk=configuracao_pk)

    class Meta:
        model = ItemConfiguracaoAtividadeAprofundamento
        exclude = ('configuracao',)


class ReplicarConfiguracaoAACCForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoAtividadeComplementar
        exclude = ()

    def processar(self, configuracao):
        return configuracao.replicar(self.cleaned_data['descricao'])


class ReplicarConfiguracaoATPAForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoAtividadeAprofundamento
        exclude = ()

    def processar(self, configuracao):
        return configuracao.replicar(self.cleaned_data['descricao'])


class MatrizForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['configuracao_creditos_especiais'].queryset = ConfiguracaoCreditosEspeciais.objects.filter(ativo=True)

    class Meta:
        model = Matriz
        exclude = ()

    def clean(self):
        try:
            ch_complementares = int(self.cleaned_data.get('ch_atividades_complementares', 0))
            ch_aprofundamento = int(self.cleaned_data.get('ch_atividades_aprofundamento', 0))
        except Exception:
            raise forms.ValidationError("Cargas horárias inválidas.")

        configuracao_academica = self.cleaned_data.get('configuracao_atividade_academica')
        configuracao_aprofundamento = self.cleaned_data.get('configuracao_atividade_aprofundamento')

        if ch_complementares > 0 and not configuracao_academica:
            raise forms.ValidationError("Selecione a configuração de AACC. Existe carga horária de atividades complementares.")
        if ch_aprofundamento > 0 and not configuracao_aprofundamento:
            raise forms.ValidationError("Selecione a configuração de ATPA. Existe carga horária de atividades de aprofundamento.")

        if self.cleaned_data.get('exige_estagio') and not self.cleaned_data.get('ch_minima_estagio'):
            raise forms.ValidationError("Informe a Carga Horária Mínima de Estágio e Afins quando a opção Exige Estágio e Afins estiver marcada.")

        return self.cleaned_data


class DividirDiarioForm(forms.Form):
    matriculas_diario = forms.MultipleModelChoiceField(MatriculaDiario.objects, label='', widget=RenderableSelectMultiple('widgets/alunos_dividir_diario_widget.html'))

    fieldsets = (('Alunos', {'fields': ('matriculas_diario',)}),)

    def __init__(self, matriculas_diario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['matriculas_diario'].queryset = matriculas_diario


class MapaTurmaForm(forms.Form):
    diarios = forms.MultipleModelChoiceField(Diario.objects, label='', widget=RenderableSelectMultiple('widgets/diarios_widget.html'))

    def __init__(self, diarios, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diarios'].queryset = diarios.order_by('componente_curricular__componente__sigla', 'id')


class AdicionarAlunosDiarioForm(forms.Form):
    matriculas_periodo = forms.MultipleModelChoiceField(MatriculaPeriodo.objects, label='', widget=RenderableSelectMultiple('widgets/matriculas_periodo_widget.html'))

    def __init__(self, matriculas_periodo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['matriculas_periodo'].queryset = matriculas_periodo

    def processar(self, diario):
        count = 0
        for matricula_periodo in self.cleaned_data['matriculas_periodo']:
            if matricula_periodo.aluno.pode_ser_matriculado_no_diario(diario)[0]:
                if not MatriculaDiario.objects.filter(matricula_periodo=matricula_periodo, diario=diario).exists():
                    matricula_diario = MatriculaDiario()
                    matricula_diario.matricula_periodo = matricula_periodo
                    matricula_diario.diario = diario
                    matricula_diario.save()
                    count += 1
                if not matricula_periodo.aluno.situacao.pk == SituacaoMatricula.MATRICULADO:
                    matricula_periodo.aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                    matricula_periodo.aluno.save()
                if not matricula_periodo.situacao == SituacaoMatriculaPeriodo.MATRICULADO:
                    matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
                    matricula_periodo.save()
        return count


class ConfiguracaoPedidoMatriculaForm(forms.ModelForm):
    descricao = forms.CharFieldPlus(width=500, label='Descrição', required=True)
    diretorias = forms.MultipleModelChoiceField(Diretoria.objects.none(), label='Diretorias', widget=forms.CheckboxSelectMultiple(), required=True)

    class Meta:
        model = ConfiguracaoPedidoMatricula
        exclude = ('cursos',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Diretoria.locals
        if qs.count() == 1:
            self.fields['diretorias'] = forms.ModelChoiceField(qs)
            diretoria = self.fields['diretorias'].queryset.first()
            self.fields['diretorias'].initial = diretoria.pk
            self.initial['diretorias'] = diretoria.pk
            self.fields['diretorias'].widget = forms.HiddenInput()
        else:
            self.fields['diretorias'].queryset = qs
        if not settings.NOTA_DECIMAL:
            self.fields['permite_cancelamento_matricula_diario'].widget = forms.HiddenInput()

    def clean_data_fim(self):
        if 'data_inicio' in self.cleaned_data and 'data_fim' in self.cleaned_data:
            if self.cleaned_data['data_fim'] < self.cleaned_data['data_inicio']:
                raise ValidationError('A data de fim deve ser maior que a data de início.')
        return self.cleaned_data['data_fim']

    def clean_diretorias(self):
        diretorias = self.cleaned_data['diretorias']
        if type(self.fields['diretorias'].widget) == forms.HiddenInput:
            return [diretorias]
        return diretorias

    def clean(self):
        if self.instance.is_processado():
            raise ValidationError('Os pedidos de renovação de matrícula já foram processados.')


class AddCursoConfiguracaoPedidoMatriculaForm(forms.ModelFormPlus):
    novos_cursos = forms.MultipleModelChoiceFieldPlus(CursoCampus.objects, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if in_group(self.request.user, 'Secretário Acadêmico') and not in_group(self.request.user, 'Administrador Acadêmico'):
            if not running_tests():
                ids_setores_user = Setor.objects.filter(usuariogrupo__user=self.request.user).values_list('id', flat=True)
                queryset = CursoCampus.objects.filter(ativo=True, diretoria__setor__id__in=ids_setores_user)
                queryset = queryset.filter(diretoria__in=self.instance.diretorias.all())
                self.fields['novos_cursos'].queryset = queryset

        if in_group(self.request.user, 'Coordenador de Curso') and not in_group(self.request.user, ['Administrador Acadêmico', 'Secretário Acadêmico']):
            if not running_tests():
                self.fields['novos_cursos'].queryset = CursoCampus.objects.filter(ativo=True, coordenador=self.request.user.get_vinculo().pessoa_id) | CursoCampus.objects.filter(ativo=True, coordenador_2=self.request.user.get_vinculo().pessoa_id)

    class Meta:
        model = ConfiguracaoPedidoMatricula
        fields = ()

    def clean(self):
        if 'novos_cursos' in self.cleaned_data:
            for curso in self.cleaned_data['novos_cursos']:
                qs = curso.configuracaopedidomatricula_set.filter(ano_letivo=self.instance.ano_letivo, periodo_letivo=self.instance.periodo_letivo)
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.filter(data_inicio__lte=self.instance.data_inicio, data_fim__gte=self.instance.data_inicio) or qs.filter(
                    data_inicio__lte=self.instance.data_fim, data_fim__gte=self.instance.data_fim
                ):
                    raise forms.ValidationError(
                        f'Existe uma configuração cadastrada para o curso ({curso}) no período inserido que impede o cadastro neste intervalo de datas.'
                    )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for curso in self.cleaned_data['novos_cursos']:
            self.instance.cursos.add(curso)


class ConfiguracaoSeguroForm(forms.ModelFormPlus):
    valor_repasse_pessoa = forms.CharFieldPlus(
        label='Valor do Repasse por Pessoa', help_text='Esse campo pode ter várias casas decimais e devem ser separadas por "." ao invés de ",'
    )
    fiscais = forms.MultipleModelChoiceFieldPlus(Servidor.objects, required=True, label='Responsáveis pela Fiscalização')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fiscais'].queryset = Servidor.objects.filter(excluido=False)

    def clean_data_fim_contrato(self):
        if self.cleaned_data['data_fim_contrato'] < self.cleaned_data['data_inicio_contrato']:
            raise ValidationError('A data de término do contrato não pode ser menor que a data de início do contrato.')

        return self.cleaned_data['data_fim_contrato']

    def clean_valor_contrato(self):
        if self.cleaned_data['valor_contrato'] < 0:
            raise ValidationError('O valor do contrato deve ser maior que zero.')

        return self.cleaned_data['valor_contrato']

    def clean_valor_repasse_pessoa(self):
        try:
            from decimal import Decimal

            valor_repasse_pessoa = Decimal(self.cleaned_data['valor_repasse_pessoa'].replace(',', '.'))

            if valor_repasse_pessoa < 0:
                raise ValidationError('O valor do repasse por pessoa deve ser maior que zero.')

            return valor_repasse_pessoa
        except Exception:
            raise ValidationError('O valor do repasse por pessoa deve ser um número decimal')

    class Meta:
        model = ConfiguracaoSeguro
        exclude = ()


class AulaCampoForm(forms.ModelFormPlus):
    configuracao_seguro = forms.ModelChoiceField(ConfiguracaoSeguro.objects, label='Configuração de Seguro')
    uo = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus')
    descricao = forms.CharFieldPlus(label='Descrição', max_length=300, width=500)
    responsaveis = forms.MultipleModelChoiceFieldPlus(Servidor.objects, required=True, label='Servidores responsáveis pela Aula')
    arquivo = forms.FileFieldPlus(
        label='Relação de Alunos Participantes', help_text='O arquivo deve ser no formato "xlsx", sem cabeçalho, e contendo a matrícula na primeira coluna.', required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not in_group(self.request.user, 'Administrador Acadêmico'):
            if not self.instance.situacao == AulaCampo.SITUACAO_AGENDADA:
                self.fields['configuracao_seguro'].widget.attrs['disabled'] = 'disabled'
                self.fields['uo'].widget.attrs['disabled'] = 'disabled'
                self.fields['descricao'].widget.attrs['readonly'] = 'readonly'
                self.fields['finalidade'].widget.attrs['readonly'] = 'readonly'
                self.fields['roteiro'].widget.attrs['readonly'] = 'readonly'
                self.fields['data_partida'].widget.attrs['readonly'] = 'readonly'
                self.fields['data_chegada'].widget.attrs['readonly'] = 'readonly'
                self.fields['responsaveis'].widget.attrs['disabled'] = 'disabled'
                self.fields['arquivo'].widget.attrs['disabled'] = 'disabled'

        self.fields['configuracao_seguro'].queryset = ConfiguracaoSeguro.objects.filter(ativa=True)
        self.fields['responsaveis'].queryset = Servidor.objects.filter(excluido=False)
        self.matriculas_alunos = []

    def clean_responsaveis(self):
        if 'configuracao_seguro' in self.cleaned_data and 'data_partida' in self.cleaned_data and 'data_chegada' in self.cleaned_data:
            configuracao_seguro = self.cleaned_data['configuracao_seguro']
            data_partida = self.cleaned_data['data_partida']
            data_chegada = self.cleaned_data['data_chegada']
            responsaveis = self.cleaned_data['responsaveis']

            qs = configuracao_seguro.aulacampo_set.filter(situacao=AulaCampo.SITUACAO_AGENDADA)
            qs = qs.exclude(data_chegada__lt=data_partida)
            qs = qs.exclude(data_partida__gt=data_chegada)

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            for responsavel in responsaveis:
                qs = qs.filter(responsaveis__pk=responsavel.pk)

                if qs.exists():
                    aulas_conflitos = qs.values_list('pk', flat=True).distinct()
                    raise ValidationError(f'Existe conflito de datas para o(a) servidor(a) {responsavel}  nas aulas de campo {aulas_conflitos}.')

        return self.cleaned_data['responsaveis']

    def clean_arquivo(self):
        if self.cleaned_data['arquivo']:
            if 'configuracao_seguro' in self.cleaned_data and 'data_partida' in self.cleaned_data and 'data_chegada' in self.cleaned_data:
                try:
                    self.matriculas_alunos = []
                    matriculas_erro = []
                    arquivo = self.cleaned_data['arquivo'].file
                    workbook = xlrd.open_workbook(file_contents=arquivo.read())
                    sheet = workbook.sheet_by_index(0)

                    for i in range(0, sheet.nrows):
                        try:
                            matricula = int(sheet.cell_value(i, 0))
                        except ValueError:
                            matricula = str(sheet.cell_value(i, 0))

                        self.matriculas_alunos.append(matricula)
                except XLRDError:
                    raise ValidationError(
                        'Não foi possível processar a planilha. Verfique se o formato do arquivo é .xls ou .xlsx e se a primeira coluna contém as matrículas dos alunos.'
                    )
                except UnicodeEncodeError:
                    raise ValidationError('Não foi possível processar a planilha. Verfique se a primeira coluna contém somente as matrículas dos alunos.')

                matriculas_encontradas = Aluno.objects.filter(matricula__in=self.matriculas_alunos).values_list('matricula', flat=True)
                for matricula in self.matriculas_alunos:
                    if not str(matricula) in matriculas_encontradas:
                        matriculas_erro.append(matricula)

                if matriculas_erro:
                    raise forms.ValidationError(f'As matrículas {matriculas_erro} não foram encontradas.')

                qtd_alunos_selecionados = len(self.matriculas_alunos)
                configuracao_seguro = self.cleaned_data['configuracao_seguro']
                data_partida = self.cleaned_data['data_partida']
                data_chegada = self.cleaned_data['data_chegada']
                qtd_dias = (data_chegada - data_partida).days + 1
                gasto_previsto_aula = qtd_alunos_selecionados * qtd_dias * configuracao_seguro.valor_repasse_pessoa

                # Verificando conflitos de datas para os alunos
                qs = configuracao_seguro.aulacampo_set.filter(situacao=AulaCampo.SITUACAO_AGENDADA)
                qs = qs.exclude(data_chegada__lt=data_partida)
                qs = qs.exclude(data_partida__gt=data_chegada)

                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)

                for aluno in self.matriculas_alunos:
                    qs = qs.filter(alunos__matricula=aluno)

                    if qs.exists():
                        aulas_conflitos = qs.values_list('pk', flat=True).distinct()
                        aluno = Aluno.objects.get(matricula=aluno)
                        raise ValidationError(f'Existe conflito de datas para o(a) aluno(a) {aluno} nas aulas de campo {aulas_conflitos}.')

                if not configuracao_seguro.possui_saldo_suficiente(gasto_previsto_aula):
                    num_participantes_disponivel = configuracao_seguro.get_participantes_disponiveis(qtd_dias)
                    raise ValidationError(
                        f'Não existe saldo disponível para a quantidade de alunos selecionados. Você pode incluir até {num_participantes_disponivel:d} alunos.'
                    )
            else:
                raise ValidationError('Você precisa informar a configuração de seguro, a data de partida e a data de chegada.')

        return self.cleaned_data['arquivo']

    def clean(self):
        if 'configuracao_seguro' in self.cleaned_data and 'data_partida' in self.cleaned_data and 'data_chegada' in self.cleaned_data and 'responsaveis' in self.cleaned_data:
            configuracao_seguro = self.cleaned_data['configuracao_seguro']

            if not in_group(self.request.user, 'Administrador Acadêmico'):
                if self.cleaned_data['data_partida'] < (datetime.datetime.today() + datetime.timedelta(days=1)).date():
                    raise ValidationError('A data de partida não pode ser menor que a data de amanhã.')

            if self.cleaned_data['data_chegada'] < self.cleaned_data['data_partida']:
                raise ValidationError('A data de chegada não pode ser menor que a data de partida.')

            if self.cleaned_data['data_chegada'] > configuracao_seguro.data_fim_contrato:
                raise ValidationError('A configuração de Seguro selecionada não estará mais vigente para a data da Aula.')

            qtd_responsaveis_atual = self.cleaned_data['responsaveis'].count()

            if self.instance.pk:
                qtd_responsaveis_anterior = self.instance.responsaveis.count()
            else:
                qtd_responsaveis_anterior = 0

            if qtd_responsaveis_anterior < qtd_responsaveis_atual:
                qtd_responsaveis = int(math.fabs(qtd_responsaveis_atual - qtd_responsaveis_anterior))

                data_partida = self.cleaned_data['data_partida']
                data_chegada = self.cleaned_data['data_chegada']
                qtd_dias = (data_chegada - data_partida).days + 1
                gasto_previsto_aula = qtd_responsaveis * qtd_dias * configuracao_seguro.valor_repasse_pessoa

                if not configuracao_seguro.possui_saldo_suficiente(gasto_previsto_aula):
                    num_participantes_disponivel = configuracao_seguro.get_participantes_disponiveis(qtd_dias)
                    raise ValidationError(
                        f'Não existe saldo disponível para a quantidade de responsáveis selecionados. Você pode incluir até {num_participantes_disponivel:d} responsáveis.',
                        'error',
                    )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.instance.save()

        for aluno in Aluno.objects.filter(matricula__in=self.matriculas_alunos).exclude(pk__in=self.instance.alunos.values_list('pk', flat=True)):
            aluno_aula = AlunoAulaCampo()
            aluno_aula.aluno = aluno
            aluno_aula.aula_campo = self.instance
            aluno_aula.save()

        return self.instance

    class Meta:
        model = AulaCampo
        exclude = ('situacao',)


class PesquisarAlunosForm(forms.FormPlus):
    SUBMIT_LABEL = 'Pesquisar'
    METHOD = 'GET'

    curso_campus = forms.ModelChoiceFieldPlus(
        CursoCampus.objects, label='Curso', required=False, widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('uo', 'diretoria__setor__uo__in')])
    )
    turma = forms.ModelChoiceFieldPlus(Turma.objects.none(), required=False)
    diario = forms.ModelChoiceFieldPlus(
        Diario.objects.none(),
        help_text='Para encontrar um diário entre com a sigla do componente ou o id do diário.',
        widget=AutocompleteWidget(search_fields=Diario.SEARCH_FIELDS),
        required=False,
        label='Diário',
    )
    aluno = forms.ModelChoiceFieldPlus(Aluno.locals, required=False, widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals
        self.fields['turma'].queryset = Turma.locals

    def clean(self):
        if not self.cleaned_data['curso_campus'] and not self.cleaned_data['turma'] and not self.cleaned_data['diario'] and not self.cleaned_data['aluno']:
            raise forms.ValidationError('Insira, no mínimo o curso, a turma, o diário ou o aluno nos filtros.')

        return self.cleaned_data

    def processar(self):
        qs = Aluno.objects.all()
        aluno = self.cleaned_data['aluno']
        curso_campus = self.cleaned_data['curso_campus']
        turma = self.cleaned_data['turma']
        diario = self.cleaned_data['diario']

        if curso_campus:
            qs = qs.filter(curso_campus=curso_campus)
        if turma:
            qs = qs.filter(curso_campus__ativo=True, matriculaperiodo__matriculadiario__diario__turma=turma)
        if diario:
            qs = qs.filter(matriculaperiodo__matriculadiario=diario)
        if aluno:
            qs = qs.filter(pk=aluno.pk)

        retorno = qs.distinct()

        return retorno


class MensagemComplementarForm(forms.FormPlus):
    LAST_SUBMIT_LABEL = 'Enviar Mensagem Complementar'
    METHOD = 'POST'
    assunto = forms.CharFieldPlus(width=500)
    conteudo = forms.CharField(widget=forms.Textarea(), label='Conteúdo', required=True)
    anexo = forms.FileFieldPlus(
        required=False, help_text='Caso deseje adicionar mais de um anexo, compacte-os utilizando uma ferramenta de zip. Tamanho máximo de 2,5Mb.', max_file_size=2621440
    )

    def __init__(self, mensagem_original, *args, **kwargs):
        self.mensagem_original = mensagem_original
        super().__init__(*args, **kwargs)

    def processar(self):
        anexo = self.cleaned_data['anexo']
        filename = None
        if anexo:
            extensao = '.' + anexo.name.split('.')[-1]
            filename = tempfile.mktemp(extensao)
            temp = open(filename, 'wb+')
            for chunk in anexo.chunks():
                temp.write(chunk)
            temp.close()

        mensagem = Mensagem()
        mensagem.remetente = self.mensagem_original.remetente
        mensagem.assunto = self.cleaned_data['assunto']
        mensagem.conteudo = self.cleaned_data['conteudo']
        mensagem.anexo = anexo
        mensagem.via_suap = self.mensagem_original.via_suap
        mensagem.via_email = self.mensagem_original.via_email
        mensagem.save()
        emails = []
        for destinatario in self.mensagem_original.destinatarios.all():
            emails.append(destinatario.email)
            mensagem.destinatarios.add(destinatario)
        mensagem.save()
        if mensagem.via_email:

            def do():
                files = []
                if filename:
                    files.append(filename)
                send_mail(mensagem.assunto, mensagem.conteudo, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=True, files=files)
            thread = threading.Thread(target=do)
            thread.start()
        return mensagem


class MensagemForm(FormWizardPlus):
    LAST_SUBMIT_LABEL = 'Enviar Mensagem para Alunos Selecionados'
    METHOD = 'POST'
    assunto = forms.CharFieldPlus(width=500)
    anexo = forms.FileFieldPlus(
        required=False, help_text='Caso deseje adicionar mais de um anexo, compacte-os utilizando uma ferramenta de zip. Tamanho máximo de 2,5Mb.', max_file_size=2621440
    )

    via_suap = forms.BooleanField(label='Via Suap', required=False)
    via_email = forms.BooleanField(label='Via E-mail', required=False, help_text='Será enviada uma cópia do email para você.')
    enviar_coordenador = forms.BooleanField(
        label='Copiar Coordenador', required=False, help_text='Será enviada uma cópia do email para cada coordenador de curso dos alunos selecionados.'
    )
    enviar_diretor = forms.BooleanField(
        label='Copiar Diretor Acadêmico', required=False, help_text='Será enviada uma cópia do email para o diretor acadêmico dos alunos selecionados.'
    )

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=False)
    periodo_letivo = forms.ChoiceField(choices=[['', '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False)
    uo = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.objects.campi().all(), label='Campus', required=False)
    diretoria = forms.ModelMultiplePopupChoiceField(Diretoria.objects.none(), label='Diretoria', required=False)
    modalidade = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidade', required=False)
    situacao_matricula = forms.ModelMultiplePopupChoiceField(SituacaoMatricula.objects, label='Situação do Aluno', required=False)
    situacao_matricula_periodo = forms.ModelMultiplePopupChoiceField(SituacaoMatriculaPeriodo.objects, label='Situação da Matrícula Período', required=False)
    curso_campus = forms.MultipleModelChoiceFieldPlus(
        CursoCampus.objects,
        label='Curso',
        required=False,
        widget=AutocompleteWidget(
            multiple=True,
            search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[
                ('uo', 'diretoria__setor__uo__in'),
                ('diretoria', 'diretoria__in'),
                ('modalidade', 'modalidade_id__in'),
            ]
        ),
    )

    turmas_atuais = forms.MultipleModelChoiceFieldPlus(Turma.objects.none(), label='Turmas Atuais', required=False, widget=forms.CheckboxSelectMultiple())

    turma = forms.MultipleModelChoiceField(
        Turma.objects,
        label='Outras Turmas',
        required=False,
        widget=AutocompleteWidget(
            multiple=True,
            search_fields=Turma.SEARCH_FIELDS,
            form_filters=[
                ('uo', 'curso_campus__diretoria__setor__uo__in'),
                ('diretoria', 'curso_campus__diretoria__in'),
                ('modalidade', 'curso_campus__modalidade_id__in'),
                ('ano_letivo', 'ano_letivo__pk'),
                ('perido_letivo', 'periodo_letivo'),
                ('curso_campus', 'curso_campus__in'),
            ],
        ),
    )

    diarios_atuais = forms.MultipleModelChoiceField(
        Diario.objects.none(),
        required=False,
        label='Diários Atuais',
        help_text='Para encontrar um diário entre com a sigla do componente ou o id do diário.',
        widget=forms.CheckboxSelectMultiple(),
    )

    diario = forms.MultipleModelChoiceFieldPlus(
        Diario.objects,
        required=False,
        label='Outros Diários',
        help_text='Para encontrar um diário entre com a sigla do componente ou o id do diário.',
        widget=AutocompleteWidget(
            multiple=True,
            search_fields=Diario.SEARCH_FIELDS,
            form_filters=[
                ('uo', 'turma__curso_campus__diretoria__setor__uo__in'),
                ('diretoria', 'turma__curso_campus__diretoria__in'),
                ('modalidade', 'turma__curso_campus__modalidade_id__in'),
                ('curso_campus', 'turma__curso_campus__in'),
                ('ano_letivo', 'ano_letivo__pk'),
                ('periodo_letivo', 'periodo_letivo'),
                ('turma', 'turma__in')
            ],
        ),
    )

    aluno = forms.MultipleModelChoiceFieldPlus(
        queryset=Aluno.objects,
        required=False,
        widget=AutocompleteWidget(
            multiple=True,
            search_fields=Aluno.SEARCH_FIELDS,
            form_filters=[
                ('uo', 'curso_campus__diretoria__setor__uo__in'),
                ('diretoria', 'curso_campus__diretoria__in'),
                ('curso_campus', 'curso_campus__in'),
                ('turma', 'matriculaperiodo__matriculadiario__diario__turma__pk__in'),
                ('situacao_matricula', 'situacao__id__in'),
                ('ano_letivo', 'ano_letivo__pk'),
                ('periodo_letivo', 'periodo_letivo'),
            ],
        ),
    )

    polo = forms.MultipleModelChoiceFieldPlus(Polo.objects, required=False, label='Polo EAD')

    conteudo = RichTextFormField(label='Conteúdo', config_name='basico_sem_imagem', required=True)

    alunos = forms.MultipleModelChoiceFieldPlus(Aluno.objects, required=False, label='', widget=RenderableSelectMultiple('widgets/alunos_widget.html'))
    confirmacao = forms.BooleanField(label='Confirmação', required=True, help_text='Marque a opção acima e clique no botão enviar a mensagem.')

    steps = (
        [
            (
                'Filtros de Destinatários',
                {
                    'fields': (
                        'uo',
                        'diretoria',
                        'modalidade',
                        'programa',
                        'situacao_matricula',
                        'ano_letivo',
                        'periodo_letivo',
                        'situacao_matricula_periodo',
                        'curso_campus',
                        'turmas_atuais',
                        'diarios_atuais',
                        'turma',
                        'diario',
                        'aluno',
                        'polo',
                    )
                },
            )
        ],
        [
            ('Forma de Envio', {'fields': ('via_suap', 'via_email')}),
            ('Enviar Cópias', {'fields': ('enviar_coordenador', 'enviar_diretor')}),
            ('Destinatários', {'fields': ('alunos',)}),
        ],
        [('Corpo da Mensagem', {'fields': ('assunto', 'conteudo', 'anexo')}), ('Confirmação do Envio', {'fields': ('confirmacao',)})],
    )

    def first_step(self):
        if 'ae' in settings.INSTALLED_APPS:
            ProgramaSocial = apps.get_model('ae', 'Programa')
            self.fields['programa'] = forms.ModelMultiplePopupChoiceField(ProgramaSocial.objects, label='Participantes do Programa', required=False)
        self.fields['aluno'].queryset = Aluno.objects.filter(pessoa_fisica__user__isnull=False)
        self.fields['curso_campus'].queryset = CursoCampus.objects.filter(ativo=True)
        self.fields['diretoria'].queryset = Diretoria.locals.all()
        self.fields['polo'].queryset = Polo.locals.all()
        self.fields['diario'].queryset = Diario.locals.all()

        periodo_letivo_atual = PeriodoLetivoAtual.get_instance(self.request)
        professor = Professor.objects.filter(vinculo=self.request.user.get_vinculo()).first()
        if periodo_letivo_atual and professor:
            qs_diarios_atuais = Diario.objects.filter(ano_letivo__ano=periodo_letivo_atual.ano, periodo_letivo=periodo_letivo_atual.periodo, professordiario__professor=professor)
            self.fields['diarios_atuais'].queryset = qs_diarios_atuais
            qs_turmas_atuais = Turma.objects.filter(pk__in=qs_diarios_atuais.values_list('turma', flat=True).distinct())
            self.fields['turmas_atuais'].queryset = qs_turmas_atuais

        if not self.request.GET:
            self.fields['situacao_matricula'].initial = (SituacaoMatricula.MATRICULADO,)
            self.fields['situacao_matricula_periodo'].initial = (SituacaoMatriculaPeriodo.MATRICULADO,)
            try:
                if not self.request.user.get_profile().funcionario.setor.uo.eh_reitoria:
                    self.fields['uo'].queryset = UnidadeOrganizacional.objects.campi().filter(id=self.request.user.get_vinculo().setor.uo_id)
                    self.fields['uo'].initial = (self.request.user.get_profile().funcionario.setor.uo_id,)
            except Exception:
                pass

    def next_step(self):
        ano_letivo = self.get_entered_data('ano_letivo')
        periodo_letivo = self.get_entered_data('periodo_letivo') or 0
        uo = self.get_entered_data('uo', is_list=True)
        diretoria = self.get_entered_data('diretoria', is_list=True)
        programa = self.get_entered_data('programa', is_list=True)
        modalidade = self.get_entered_data('modalidade', is_list=True)
        situacao_matricula = self.get_entered_data('situacao_matricula', is_list=True)
        situacao_matricula_periodo = self.get_entered_data('situacao_matricula_periodo', is_list=True)
        curso_campus = self.get_entered_data('curso_campus', is_list=True)
        turmas_atuais = self.get_entered_data('turmas_atuais', is_list=True) or []
        diarios_atuais = self.get_entered_data('diarios_atuais', is_list=True) or []
        turmas = self.get_entered_data('turma', is_list=True) or []
        diarios = self.get_entered_data('diario', is_list=True) or []
        polos = self.get_entered_data('polo', is_list=True)
        matriculas = self.get_entered_data('aluno', is_list=True)

        if 'conteudo' in self.fields:
            user = self.request.user
            setor = f'{user.get_profile().funcionario.setor}/{user.get_profile().funcionario.setor.superior}'
            assinatura = f'{user.get_profile().nome} ({user.username}) <br /> {setor}'
            self.fields['conteudo'].initial = f'<br />Atenciosamente,<br /> {assinatura}'

        if 'curso_campus' in self.fields:
            self.fields['curso_campus'].queryset = CursoCampus.objects.filter(ativo=True)

        if 'alunos' in self.fields:

            qs_mp = MatriculaPeriodo.objects.all()

            if ano_letivo:
                qs_mp = qs_mp.filter(ano_letivo=ano_letivo)

            if int(periodo_letivo):
                qs_mp = qs_mp.filter(periodo_letivo=periodo_letivo)

            if uo:
                qs_mp = qs_mp.filter(aluno__curso_campus__diretoria__setor__uo__in=uo)

            if diretoria:
                qs_mp = qs_mp.filter(aluno__curso_campus__diretoria__in=diretoria)

            if programa and 'ae' in settings.INSTALLED_APPS:
                ProgramaSocial = apps.get_model('ae', 'Programa')
                ids_alunos = list()
                for item in ProgramaSocial.objects.filter(id__in=programa):
                    ids_alunos += item.get_participacoes_abertas().values_list('aluno', flat=True)
                qs_mp = qs_mp.filter(aluno__id__in=ids_alunos)

            if modalidade:
                qs_mp = qs_mp.filter(aluno__curso_campus__modalidade__id__in=modalidade)

            if situacao_matricula:
                qs_mp = qs_mp.filter(aluno__situacao__id__in=situacao_matricula)

            if situacao_matricula_periodo:
                qs_mp = qs_mp.filter(situacao__id__in=situacao_matricula_periodo)

            if curso_campus:
                ids_cursos = [curso.id for curso in curso_campus]
                qs_mp = qs_mp.filter(aluno__curso_campus__id__in=ids_cursos)

            if turmas or turmas_atuais:
                ids_turmas = [turma.id for turma in turmas] + [turma.id for turma in turmas_atuais]
                qs_mp = qs_mp.filter(aluno__curso_campus__ativo=True, matriculadiario__diario__turma__in=ids_turmas)

            if diarios or diarios_atuais:
                ids_diarios = [diario.id for diario in diarios] + [diario.id for diario in diarios_atuais]
                qs_mp = qs_mp.filter(aluno__curso_campus__ativo=True, matriculadiario__diario__in=ids_diarios)
                qs_md = MatriculaDiario.objects.none()
                for diario in Diario.objects.filter(pk__in=ids_diarios):
                    qs_md = qs_md | MatriculaDiario.objects.filter(diario__id=diario.id).exclude(
                        situacao__in=[MatriculaDiario.SITUACAO_TRANSFERIDO, MatriculaDiario.SITUACAO_CANCELADO, MatriculaDiario.SITUACAO_TRANCADO]
                    )
                qs_mp = qs_mp.filter(matriculadiario__in=qs_md.distinct())

            if polos:
                ids_polos = [polo.id for polo in polos]
                qs_mp = qs_mp.filter(aluno__polo__in=ids_polos)

            if matriculas:
                ids_alunos = [matricula.id for matricula in matriculas]
                qs_mp = qs_mp.filter(aluno__pk__in=ids_alunos)

            qs_a = Aluno.objects.filter(id__in=qs_mp.order_by('aluno__id').values_list('aluno__id', flat=True).distinct())

            self.qs = qs_a

            self.fields['alunos'].queryset = qs_a
            if self.fields['alunos'].queryset.count() > 100:
                self.fields['alunos'].widget = forms.HiddenInput()

    def clean(self):
        uo = self.get_entered_data('uo', is_list=True)
        programa = self.get_entered_data('programa', is_list=True)
        modalidade = self.get_entered_data('modalidade', is_list=True)
        situacao_matricula = self.get_entered_data('situacao_matricula', is_list=True)
        situacao_matricula_periodo = self.get_entered_data('situacao_matricula_periodo', is_list=True)
        curso_campus = self.get_entered_data('curso_campus', is_list=True)
        turma = self.get_entered_data('turma', is_list=True) or self.get_entered_data('turmas_atuais', is_list=True)
        diario = self.get_entered_data('diario', is_list=True) or self.get_entered_data('diarios_atuais', is_list=True)
        aluno = self.get_entered_data('aluno', is_list=True)
        if not (uo or programa or modalidade or situacao_matricula or situacao_matricula_periodo or curso_campus or turma or diario or aluno):
            raise forms.ValidationError('Selecione, no mínimo, um filtro para os destinatários da mensagem.')
        else:
            if 'via_suap' in self.fields and not self.cleaned_data.get('via_suap') and not self.cleaned_data.get('via_email'):
                raise forms.ValidationError('Informe se a mensagem será enviada pelo Suap, e-mail ou ambos os meios.')
        return self.cleaned_data

    def processar(self, request):
        alunos = self.get_entered_data('alunos', is_list=True)
        if alunos and alunos.exists():
            self.qs = alunos
        coordenadores = []
        if self.get_entered_data('enviar_coordenador'):
            coordenadores = self.qs.values_list('curso_campus__coordenador__user__id', flat=True).distinct()
            coordenadores = User.objects.filter(id__in=coordenadores)
        diretores = []
        if self.get_entered_data('enviar_diretor'):
            setores_diretorias = self.qs.values_list('curso_campus__diretoria__setor__id', flat=True).distinct()
            ids_usuarios = (
                UsuarioGrupoSetor.objects.filter(setor__in=setores_diretorias, usuario_grupo__group__name='Diretor Acadêmico')
                .values_list('usuario_grupo__user', flat=True)
                .order_by('usuario_grupo__user')
                .distinct()
            )
            diretores = User.objects.filter(id__in=ids_usuarios)

        total = self.qs.count()
        if total:

            anexo = self.cleaned_data.get('anexo')
            filename = None
            if anexo:
                extensao = '.' + anexo.name.split('.')[-1]
                filename = tempfile.mktemp(extensao)
                temp = open(filename, 'wb+')
                for chunk in anexo.chunks():
                    temp.write(chunk)
                temp.close()

            mensagem = Mensagem()
            mensagem.remetente = request.user
            mensagem.assunto = self.cleaned_data['assunto']
            mensagem.conteudo = self.cleaned_data['conteudo']
            mensagem.anexo = anexo
            mensagem.via_suap = self.cleaned_data['via_suap']
            mensagem.via_email = self.cleaned_data['via_email']
            mensagem.save()
            for aluno in self.qs:
                if aluno.pessoa_fisica.user:
                    mensagem.destinatarios.add(aluno.pessoa_fisica.user)
            for coordenador in coordenadores:
                if coordenador:
                    mensagem.destinatarios.add(coordenador)
            mensagem.save()

            if mensagem.via_email:
                return mensagem.enviar_emails(self.qs, filename, coordenadores, diretores)

        if total:
            return httprr('.', f'{total} mensagens enviadas com sucesso.')
        else:
            return httprr('.', 'Não foi enviada a mensagem, pois não foi encontrada nenhuma pessoa nos campos do destinatário.', 'error')


class CoordenadorPoloForm(forms.FormPlus):
    funcionario = forms.ModelChoiceField(Funcionario.objects, required=True, label='Funcionário', widget=AutocompleteWidget(search_fields=Funcionario.SEARCH_FIELDS))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['funcionario'].queryset = Funcionario.objects.filter(excluido=False)

    def processar(self, polo):
        funcionario = self.cleaned_data['funcionario']
        coordenador_polo = CoordenadorPolo.objects.get_or_create(funcionario=funcionario, polo=polo, titular=False)
        user = User.objects.get(username=funcionario.username)
        usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR_POLO'], user=user)[0]
        UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=polo.diretoria.setor)
        return coordenador_polo


class TutorPoloForm(forms.FormPlus):
    funcionario = forms.ModelChoiceField(Funcionario.objects, required=True, label='Funcionário', widget=AutocompleteWidget(search_fields=Funcionario.SEARCH_FIELDS))
    cursos = forms.MultipleModelChoiceFieldPlus(CursoCampus.objects, required=True, label='Cursos')

    def __init__(self, polo, tutor_polo, *args, **kwargs):
        self.polo = polo
        self.tutor_polo = tutor_polo
        super().__init__(*args, **kwargs)
        self.fields['funcionario'].queryset = Funcionario.objects.filter(excluido=False)

    def processar(self):
        funcionario = self.cleaned_data['funcionario']
        cursos = self.cleaned_data['cursos']
        if self.tutor_polo:
            tutor_polo = self.tutor_polo
            tutor_polo.funcionario = funcionario
            tutor_polo.save()
        else:
            tutor_polo = TutorPolo.objects.get_or_create(funcionario=funcionario, polo=self.polo)[0]
        for curso_campus in cursos.all():
            tutor_polo.cursos.add(curso_campus)
        user = User.objects.get(username=funcionario.username)
        usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['TUTOR_POLO'], user=user)[0]
        UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=self.polo.diretoria.setor)
        return tutor_polo


class AtividadePoloForm(forms.ModelFormPlus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs_polos = Polo.locals.all()
        self.fields['polo'].queryset = qs_polos.order_by("descricao")
        self.fields['sala'].queryset = Sala.ativas.filter(predio__uo__id__in=qs_polos.values_list('diretoria__setor__uo__id', flat=True))

    class Meta:
        model = AtividadePolo
        exclude = ('confirmada',)


class HorarioAtendimentoPoloForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    polos = forms.ModelMultiplePopupChoiceField(Polo.objects, label='Polo', required=False)
    tutor_polo = forms.ModelChoiceFieldPlus(TutorPolo.objects, label='Tutor', widget=AutocompleteWidget(search_fields=TutorPolo.SEARCH_FIELDS), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['polos'].queryset = Polo.objects.all().order_by("descricao")

    def clean(self):
        qs = Polo.objects.all()
        polos = self.cleaned_data['polos']
        tutor_polo = self.cleaned_data['tutor_polo']

        filtros = []

        if polos:
            qs = polos
            filtros.append(dict(chave='Polos', valor=format_iterable(polos)))
        if tutor_polo:
            qs = qs.filter(tutorpolo__polo=tutor_polo.polo)
            filtros.append(dict(chave='Tutor Polo', valor=str(tutor_polo)))

        qs = qs.annotate(null_position=Count('horariopolo')).order_by('-null_position').distinct()
        qs.filtros = filtros

        self.qs = qs
        return self.cleaned_data

    def processar(self):
        return self.qs


class EnviarPlanilhaMensalSeguroAulaCampoForm(forms.FormPlus):
    ano = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano', widget=forms.Select())
    mes = forms.MesField(label='Mês', empty_label=None)

    def __init__(self, configuracao_seguro, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configuracao_seguro = configuracao_seguro

    def processar(self):
        ano_desejado = self.cleaned_data['ano']
        mes_desejado = self.cleaned_data['mes']
        primeiro_dia_mes = date(ano_desejado.ano, mes_desejado, 1)
        ultimo_dia_mes = adicionar_mes(date(ano_desejado.ano, mes_desejado, 1), 1) - timedelta(days=1)

        aulas_campo_mes = self.configuracao_seguro.aulacampo_set.filter(situacao=AulaCampo.SITUACAO_REALIZADA, data_partida__range=(primeiro_dia_mes, ultimo_dia_mes)).order_by(
            'data_partida'
        )
        datas_aulas_campo = aulas_campo_mes.values_list('data_partida', 'data_chegada').distinct()

        if aulas_campo_mes.exists():
            subject = '[SUAP] Planilha de Participantes - Aula de Campo - {} a {}'.format(primeiro_dia_mes.strftime('%d/%m'), ultimo_dia_mes.strftime('%d/%m'))
            body = """
                Seguem em anexo as planilhas referentes às aulas de campo.
            """
            from_email = settings.DEFAULT_FROM_EMAIL
            to = self.configuracao_seguro.email_disparo_planilha.split(',')

            # Criando a planilha
            instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
            filename = '/tmp/{}_RelatorioMensal_{}_{}.xls'.format(instituicao, datetime.datetime.today().strftime('%Y'), primeiro_dia_mes.strftime('%m'))

            wb = xlwt.Workbook(encoding='iso8859-1')

            # Percorrendo as datas e gerando as abas das planilhas com dias de chegada e partida iguais
            for data_partida, data_chegada in datas_aulas_campo:
                aulas_campo_dia = aulas_campo_mes.filter(data_partida=data_partida, data_chegada=data_chegada)

                # Nomeando a aba a partir da data de partida e chegada
                if data_partida == data_chegada:
                    sheet = wb.add_sheet(data_partida.strftime('%d_%m_%Y'))
                else:
                    sheet = wb.add_sheet('{}_a_{}'.format(data_partida.strftime('%d_%m_%Y'), data_chegada.strftime('%d_%m_%Y')))

                rows_agrupada = [['#', 'Matrícula', 'CPF', 'Nome', 'Data de Nascimento', 'Sexo', 'Tipo', 'Roteiro']]
                count = 0

                for aula_campo in aulas_campo_dia:
                    # Inserindo os Responsáveis
                    for responsavel in aula_campo.responsaveis.all():
                        count += 1
                        row = [
                            count,
                            format_(responsavel.matricula),
                            format_(responsavel.cpf),
                            format_(responsavel.nome),
                            format_(responsavel.nascimento_data),
                            format_(responsavel.sexo),
                            format_('Servidor'),
                        ]
                        row.append(aula_campo.roteiro)
                        rows_agrupada.append(row)

                    # Inserindo os Alunos
                    for aluno in aula_campo.alunos.all():
                        count += 1
                        row = [
                            count,
                            format_(aluno.matricula),
                            format_(aluno.pessoa_fisica.cpf),
                            format_(aluno.get_nome_social_composto()),
                            format_(aluno.pessoa_fisica.nascimento_data),
                            format_(aluno.pessoa_fisica.sexo),
                            format_('Aluno'),
                        ]
                        row.append(aula_campo.roteiro)
                        rows_agrupada.append(row)

                for row_idx, row in enumerate(rows_agrupada):
                    row = [human_str(i, encoding='iso8859-1', blank='-') for i in row]
                    for col_idx, col in enumerate(row):
                        sheet.write(row_idx, col_idx, label=col)

            # Salvando e Anexando a planilha
            wb.save(filename)
            files = []
            files.append(filename)

            # Enviando o email para a seguradora
            send_mail(subject, body, from_email, to, files=files)
            return True
        return False


class ConfiguracaoCertificadoENEMForm(forms.ModelForm):
    responsaveis = forms.MultipleModelChoiceFieldPlus(Funcionario.objects, required=True, label='Responsáveis pela Certificação do ENEM')
    planilha_inep = forms.FileFieldPlus(
        required=False, label='Planilha do INEP', help_text='Arquivo .xls gerado no sistema do INEP que contém os pedidos de Certificação do ENEM para a Instituição'
    )
    uo_planilha = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus da Planilha', required=False)

    class Meta:
        exclude = ()
        model = ConfiguracaoCertificadoENEM

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsaveis'].queryset = Funcionario.objects.filter(excluido=False)

    def clean_uo_planilha(self):
        planilha_inep = self.cleaned_data.get('planilha_inep')
        uo_planilha = self.cleaned_data.get('uo_planilha')

        if planilha_inep and not uo_planilha:
            raise ValidationError('Você precisa informar o Campus da Planilha.')
        return self.cleaned_data.get('uo_planilha')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.instance.save()

        # Adicionando os responsáveis pela certificação no grupo Certificador ENEM
        responsaveis = self.cleaned_data['responsaveis']
        grupo = Group.objects.get_or_create(name='Certificador ENEM')[0]

        for responsavel in responsaveis:
            responsavel.user.groups.add(grupo)

        if self.cleaned_data['planilha_inep']:
            planilha_inep = self.cleaned_data['planilha_inep'].file
            uo_planilha = self.cleaned_data.get('uo_planilha')

            workbook = xlrd.open_workbook(file_contents=planilha_inep.read())
            sheet = workbook.sheet_by_index(0)

            for i in range(1, sheet.nrows):
                inscricao = int(sheet.cell_value(i, 0))
                nome = normalizar_nome_proprio(sheet.cell_value(i, 1))
                nome_mae = normalizar_nome_proprio(sheet.cell_value(i, 2))

                # Tratando o RG
                rg = str(sheet.cell_value(i, 3)).replace(',', '').replace('.', '').replace('-', '').replace(' ', '')

                # Tratando o CPF
                cpf = str(int(sheet.cell_value(i, 4)))
                cpf = cpf.rjust(11, '0')
                cpf = mask_cpf(cpf)

                # Lendo o campo de data do Excel para o formato do Python
                year, month, day, hour, minute, second = xlrd.xldate_as_tuple(sheet.cell_value(i, 5), workbook.datemode)
                data_nascimento = datetime.datetime(year, month, day)

                nota_cn = sheet.cell_value(i, 6)
                if nota_cn == '-':
                    nota_cn = 0

                nota_ch = sheet.cell_value(i, 7)
                if nota_ch == '-':
                    nota_ch = 0

                nota_lc = sheet.cell_value(i, 8)
                if nota_lc == '-':
                    nota_lc = 0

                nota_mt = sheet.cell_value(i, 9)
                if nota_mt == '-':
                    nota_mt = 0

                nota_redacao = sheet.cell_value(i, 10)
                if nota_redacao == '-':
                    nota_redacao = 0

                # Criando ou capturando o objeto RegistroAlunoINEP
                r = RegistroAlunoINEP.objects.filter(cpf=cpf, configuracao_certificado_enem=self.instance)

                if not r.exists():
                    r = RegistroAlunoINEP()
                else:
                    r = r[0]

                r.numero_inscricao = inscricao
                r.nome = nome
                r.nome_mae = nome_mae
                r.rg = rg
                r.cpf = cpf
                r.data_nascimento = data_nascimento
                r.nota_ch = nota_ch
                r.nota_cn = nota_cn
                r.nota_lc = nota_lc
                r.nota_mt = nota_mt
                r.nota_redacao = nota_redacao
                r.configuracao_certificado_enem = self.instance
                r.uo = uo_planilha
                r.save()

        return self.instance


class SolicitacaoCertificadoENEMForm(forms.ModelForm):
    id = forms.CharField(label='Id', widget=forms.TextInput(attrs=dict(readonly=True)))

    class Meta:
        model = SolicitacaoCertificadoENEM
        fields = ('id',)


class SolicitarCertificadoENEMForm(forms.ModelForm):
    cpf = forms.BrCpfField()
    email = forms.EmailField()
    confirmacao_email = forms.EmailField(label='Confirmação do Email')
    telefone = forms.BrTelefoneField(max_length=255, required=False, label='Telefone', help_text='Formato: "(XX) XXXX-XXXX"')
    documento_identidade_frente = forms.FileFieldPlus(
        label='Documento de Identidade - Frente',
        max_file_size=10485760,
        filetypes=['pdf', 'jpeg', 'jpg', 'png'],
        help_text='Cópia do documento de identidade - Frente. O formato do arquivo deve ser ".pdf", ".jpeg", ".jpg" ou ".png"',
    )
    documento_identidade_verso = forms.FileFieldPlus(
        label='Documento de Identidade - Verso',
        max_file_size=10485760,
        filetypes=['pdf', 'jpeg', 'jpg', 'png'],
        help_text='Cópia do documento de identidade - Verso. O formato do arquivo deve ser ".pdf", ".jpeg", ".jpg" ou ".png"',
    )
    recaptcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['configuracao_certificado_enem'].queryset = ConfiguracaoCertificadoENEM.objects.filter(manual=False)

        if running_tests():
            self.fields.pop('recaptcha')

    def clean_confirmacao_email(self):
        email = self.cleaned_data.get('email')
        confirmacao_email = self.cleaned_data.get('confirmacao_email')

        if email is not None and confirmacao_email is not None:
            if email != confirmacao_email:
                raise ValidationError('Os emails informados não conferem.')

        return confirmacao_email

    def clean(self):
        if (
            not running_tests()
            and self.cleaned_data.get('configuracao_certificado_enem') is not None
            and self.cleaned_data.get('tipo_certificado') is not None
            and self.cleaned_data.get('cpf') is not None
            and self.cleaned_data.get('email') is not None
            and self.cleaned_data.get('confirmacao_email') is not None
            and self.cleaned_data.get('documento_identidade_frente') is not None
            and self.cleaned_data.get('documento_identidade_verso') is not None
            and self.cleaned_data.get('recaptcha') is not None
        ):
            qs_candidato_habilitado = RegistroAlunoINEP.objects.filter(
                configuracao_certificado_enem=self.cleaned_data['configuracao_certificado_enem'], cpf=self.cleaned_data['cpf']
            )

            # O candidato está habilitado a emitir o certificado pela instituição?
            if qs_candidato_habilitado.exists():
                # O candidato já possui um registro de certificado não cancelada para esta edição do ENEM?
                qs_candidato_possui_certificado = RegistroEmissaoCertificadoENEM.objects.filter(
                    solicitacao__cpf=self.cleaned_data.get('cpf'),
                    solicitacao__configuracao_certificado_enem=self.cleaned_data['configuracao_certificado_enem'],
                    solicitacao__tipo_certificado=self.cleaned_data['tipo_certificado'],
                    cancelado=False,
                )
                if qs_candidato_possui_certificado.exists():
                    raise ValidationError(
                        'O candidado já possui um certificado emitido para esta edição do ENEM. <a href="/edu/gerar_certificado_enem/{}/">Não recebeu o certificado por email ou deseja reimprimir?</a>'.format(
                            qs_candidato_possui_certificado.latest('via').codigo_geracao_certificado
                        )
                    )

                # O candidato possui alguma solicitação em aberto?
                qs_candidato_possui_solicitacao_aberta = SolicitacaoCertificadoENEM.objects.filter(
                    cpf=self.cleaned_data.get('cpf'),
                    configuracao_certificado_enem=self.cleaned_data['configuracao_certificado_enem'],
                    tipo_certificado=self.cleaned_data['tipo_certificado'],
                    avaliador__isnull=True,
                )
                if qs_candidato_possui_solicitacao_aberta.exists():
                    raise ValidationError('O candidado já possui uma solicitação em aberto para esta edição do ENEM.')

                configuracao_enem = self.cleaned_data['configuracao_certificado_enem']
                candidato = qs_candidato_habilitado[0]
                diferenca_em_anos = relativedelta.relativedelta(configuracao_enem.data_primeira_prova, candidato.data_nascimento).years

                # O candidado é maior de idade?
                if diferenca_em_anos < 18:
                    raise ValidationError(
                        'O candidato não está habilitado para solicitar o Certificado ENEM pois não completou 18 anos antes da data de realização da primeira prova.'
                    )

                # O tipo do certificado é completo?
                if self.cleaned_data['tipo_certificado'] == 1:
                    # O candidato atingiu a nota mínima em cada uma das áreas de conhecimento e redação?
                    if not candidato.apto_certificado_completo():
                        raise ValidationError(
                            'O candidato não está habilitado para solicitar o Certificado ENEM pois não atingiu a pontuação mínima necessária em cada uma das áreas de conhecimento e na redação.'
                        )
                else:
                    # O candidato selecionou a opção certificado "Parcial" porém tem nota suficiente para emitir o certificado "Completo"
                    if candidato.apto_certificado_completo():
                        raise ValidationError(
                            'Atenção: Você atingiu a pontuação necessária para a emissão do certificado completo. Portanto a solocitação do certificado parcial não pode ser concluída.'
                        )

                    # O candidato atingiu a nota mínima em alguma das áreas de conhecimento ou redação?
                    if not candidato.apto_certificado_parcial():
                        raise ValidationError(
                            'O candidato não está habilitado para solicitar o Certificado ENEM pois não atingiu a pontuação mínima necessária em nenhuma das áreas de conhecimento ou na redação.'
                        )
            else:
                # O candidato não está apto a solicitar o certificado.
                raise ValidationError('O candidato não está habilitado para solicitar o Certificado ENEM por esta instituição.')

        return self.cleaned_data

    def processar(self):
        self.instance.nome = normalizar_nome_proprio(self.instance.nome)
        self.instance.codigo_geracao_solicitacao = hashlib.sha1(
            f'{self.instance.cpf}{self.instance.tipo_certificado}{datetime.datetime.now()}{settings.SECRET_KEY}'.encode()
        ).hexdigest()[0:16]
        self.instance.save()
        return self.instance

    class Meta:
        model = SolicitacaoCertificadoENEM
        fields = (
            'configuracao_certificado_enem',
            'tipo_certificado',
            'nome',
            'cpf',
            'email',
            'confirmacao_email',
            'telefone',
            'documento_identidade_frente',
            'documento_identidade_verso',
        )


class ConsultarAndamentoSolicitacaoCertificadoENEMForm(forms.FormPlus):
    codigo_autenticacao = forms.CharFieldPlus(
        width=130,
        max_length=16,
        label='Código de Autenticação',
        help_text='O código é composto de 16 dígitos alfanuméricos e se encontra na parte inferior do comprovante da solicitação.',
    )
    cpf = forms.BrCpfField(label='CPF do Solicitante')

    def processar(self):
        try:
            obj = SolicitacaoCertificadoENEM.objects.get(codigo_geracao_solicitacao=self.cleaned_data.get('codigo_autenticacao'), cpf=self.cleaned_data.get('cpf'))
        except SolicitacaoCertificadoENEM.DoesNotExist:
            return None

        return obj


class CadastrarSolicitacaoCertificadoENEMForm(forms.ModelFormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus')
    nome_mae = forms.CharFieldPlus(width=500, label='Nome da Mãe')
    numero_rg = forms.CharField(max_length=255, label='Número do RG')
    cpf = forms.BrCpfField()
    data_nascimento = forms.DateFieldPlus(label='Data de Nascimento')
    email = forms.EmailField(required=False)
    telefone = forms.BrTelefoneField(max_length=255, required=False, label='Telefone', help_text='Formato: "(XX) XXXX-XXXX"')
    numero_inscricao = forms.CharField(max_length=255, label='Número de Inscrição')
    nota_ch = forms.DecimalFieldPlus(label='Nota - Ciências Humanas e suas Tecnologias', help_text='Formato: 500,00')
    nota_cn = forms.DecimalFieldPlus(label='Nota - Ciências da Natureza e suas Tecnologias', help_text='Formato: 500,00')
    nota_lc = forms.DecimalFieldPlus(label='Nota - Linguagens, Códigos e suas Tecnologias', help_text='Formato: 500,00')
    nota_mt = forms.DecimalFieldPlus(label='Nota - Matemática e suas Tecnologias', help_text='Formato: 500,00')
    nota_redacao = forms.DecimalFieldPlus(label='Nota - Redação', help_text='Formato: 500,00')
    # processo = forms.ModelChoiceFieldPlus(Processo.objects, label='Processo', required=False)

    fieldsets = (
        ('Dados da Solicitação', {'fields': (('configuracao_certificado_enem', 'uo'), ('tipo_certificado'))}),
        ('Dados do Solicitante', {'fields': ('nome', 'nome_mae', 'numero_rg', 'cpf', 'data_nascimento', 'email', 'telefone')}),
        ('Dados do Extrato de Desempenho do ENEM', {'fields': ('numero_inscricao', 'nota_cn', 'nota_ch', 'nota_lc', 'nota_mt', 'nota_redacao')}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['processo'].required = False

            registro_inep = RegistroAlunoINEP.objects.get(configuracao_certificado_enem=self.instance.configuracao_certificado_enem, cpf=self.instance.cpf)
            self.initial['nome_mae'] = registro_inep.nome_mae
            self.initial['numero_rg'] = registro_inep.rg
            self.initial['data_nascimento'] = registro_inep.data_nascimento
            self.initial['numero_inscricao'] = registro_inep.numero_inscricao
            self.initial['nota_ch'] = registro_inep.nota_ch
            self.initial['nota_cn'] = registro_inep.nota_cn
            self.initial['nota_lc'] = registro_inep.nota_lc
            self.initial['nota_mt'] = registro_inep.nota_mt
            self.initial['nota_redacao'] = registro_inep.nota_redacao

    def clean(self):
        if (
            not self.instance.pk
            and 'configuracao_certificado_enem' in self.cleaned_data
            and 'uo' in self.cleaned_data
            and 'tipo_certificado' in self.cleaned_data
            and 'cpf' in self.cleaned_data
            and 'data_nascimento' in self.cleaned_data
            and 'nota_ch' in self.cleaned_data
            and 'nota_lc' in self.cleaned_data
            and 'nota_mt' in self.cleaned_data
            and 'nota_redacao' in self.cleaned_data
        ):
            # O candidato já possui um registro de certificado não cancelada para esta edição do ENEM?
            qs_candidato_possui_certificado = RegistroEmissaoCertificadoENEM.objects.filter(
                solicitacao__cpf=self.cleaned_data.get('cpf'),
                solicitacao__configuracao_certificado_enem=self.cleaned_data['configuracao_certificado_enem'],
                solicitacao__tipo_certificado=self.cleaned_data['tipo_certificado'],
                cancelado=False,
            )
            if qs_candidato_possui_certificado.exists():
                raise ValidationError(
                    'O candidado já possui um certificado emitido para esta edição do ENEM. <a href="/edu/gerar_certificado_enem/{}/">Não recebeu o certificado por email ou deseja reimprimir?</a>'.format(
                        qs_candidato_possui_certificado.latest('via').codigo_geracao_certificado
                    )
                )

            qs_candidato_possui_solicitacao_aberta = SolicitacaoCertificadoENEM.objects.filter(
                cpf=self.cleaned_data.get('cpf'),
                configuracao_certificado_enem=self.cleaned_data['configuracao_certificado_enem'],
                tipo_certificado=self.cleaned_data['tipo_certificado'],
                avaliada=False,
            ).exclude(pk=self.instance.pk)
            if qs_candidato_possui_solicitacao_aberta.exists():
                raise ValidationError('O candidado já possui uma solicitação em aberto para esta edição do ENEM.')

            configuracao_enem = self.cleaned_data['configuracao_certificado_enem']
            nota_minima_necessaria_areas_conhecimento = configuracao_enem.pontuacao_necessaria_areas_conhecimento
            nota_minima_necessaria_redacao = configuracao_enem.pontuacao_necessaria_redacao
            # diferenca_em_anos = relativedelta.relativedelta(configuracao_enem.data_primeira_prova, self.cleaned_data.get('data_nascimento')).years

            # O candidado é maior de idade?
            # if diferenca_em_anos < 18:
            # raise ValidationError(u'O candidato não está habilitado para solicitar o Certificado ENEM pois não completou 18 anos antes da data de realização da primeira prova.')

            # O tipo do certificado é completo?
            if self.cleaned_data['tipo_certificado'] == 1:
                # O candidato atingiu a nota mínima em cada uma das áreas de conhecimento e redação?
                if not (
                    self.cleaned_data['nota_ch'] >= nota_minima_necessaria_areas_conhecimento
                    and self.cleaned_data['nota_cn'] >= nota_minima_necessaria_areas_conhecimento
                    and self.cleaned_data['nota_lc'] >= nota_minima_necessaria_areas_conhecimento
                    and self.cleaned_data['nota_mt'] >= nota_minima_necessaria_areas_conhecimento
                    and self.cleaned_data['nota_redacao'] >= nota_minima_necessaria_redacao
                ):
                    raise ValidationError(
                        'O candidato não está habilitado para solicitar o Certificado ENEM pois não atingiu a pontuação mínima necessária em cada uma das áreas de conhecimento e na redação.'
                    )
            else:
                # O candidato atingiu a nota mínima em alguma das áreas de conhecimento ou na redação?
                if not (
                    self.cleaned_data['nota_ch'] >= nota_minima_necessaria_areas_conhecimento
                    or self.cleaned_data['nota_cn'] >= nota_minima_necessaria_areas_conhecimento
                    or (self.cleaned_data['nota_lc'] >= nota_minima_necessaria_areas_conhecimento and self.cleaned_data['nota_redacao'] >= nota_minima_necessaria_redacao)
                    or self.cleaned_data['nota_mt'] >= nota_minima_necessaria_areas_conhecimento
                ):
                    raise ValidationError(
                        'O candidato não está habilitado para solicitar o Certificado ENEM pois não atingiu a pontuação mínima necessária em nenhuma das áreas de conhecimento ou na redação.'
                    )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        self.instance.nome = normalizar_nome_proprio(self.instance.nome)
        self.instance.solicitacao_manual = True

        if not self.instance.codigo_geracao_solicitacao:
            self.instance.codigo_geracao_solicitacao = hashlib.sha1(
                f'{self.instance.cpf}{self.instance.tipo_certificado}{datetime.datetime.now()}{settings.SECRET_KEY}'.encode()
            ).hexdigest()[0:16]

        configuracao_certificado_enem = self.cleaned_data['configuracao_certificado_enem']
        numero_inscricao = self.cleaned_data['numero_inscricao']
        nome = self.cleaned_data['nome']
        nome_mae = self.cleaned_data['nome_mae']
        rg = self.cleaned_data['numero_rg']
        cpf = self.cleaned_data['cpf']
        data_nascimento = self.cleaned_data['data_nascimento']
        nota_ch = self.cleaned_data['nota_ch']
        nota_cn = self.cleaned_data['nota_cn']
        nota_lc = self.cleaned_data['nota_lc']
        nota_mt = self.cleaned_data['nota_mt']
        nota_redacao = self.cleaned_data['nota_redacao']

        # Criando ou capturando o objeto RegistroAlunoINEP
        r = RegistroAlunoINEP.objects.filter(cpf=cpf, configuracao_certificado_enem=configuracao_certificado_enem)

        if not r.exists():
            r = RegistroAlunoINEP()
        else:
            r = r[0]

        r.numero_inscricao = numero_inscricao
        r.nome = nome
        r.nome_mae = nome_mae
        r.rg = rg
        r.cpf = cpf
        r.data_nascimento = data_nascimento
        r.nota_ch = nota_ch
        r.nota_cn = nota_cn
        r.nota_lc = nota_lc
        r.nota_mt = nota_mt
        r.nota_redacao = nota_redacao
        r.configuracao_certificado_enem = configuracao_certificado_enem
        r.save()

        return super().save(*args, **kwargs)

    class Meta:
        model = SolicitacaoCertificadoENEM
        exclude = ('avaliada', 'data_solicitacao', 'solicitacao_manual')


class EditarDadosPessoaisSolicitacaoCertificadoENEM(forms.ModelFormPlus):
    class Meta:
        model = RegistroAlunoINEP
        exclude = ('nome', 'cpf', 'configuracao_certificado_enem', 'numero_inscricao', 'nota_ch', 'nota_cn', 'nota_lc', 'nota_mt', 'nota_redacao')


class FiltroAlunosForm(forms.Form):
    METHOD = 'GET'
    diretoria = forms.ModelChoiceField(Diretoria.objects.none(), label='Diretoria', required=False)
    curso_campus = forms.ModelChoiceFieldPlus(CursoCampus.locals, label='Curso', required=False)
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo de Ingresso', required=False)
    periodo_letivo = forms.ChoiceField(choices=[['', '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo de Ingresso', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals

    def filtrar(self, alunos):
        diretoria = self.cleaned_data.get('diretoria')
        curso_campus = self.cleaned_data.get('curso_campus')
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        if diretoria:
            alunos = alunos.filter(curso_campus__diretoria=diretoria)
        if curso_campus:
            alunos = alunos.filter(curso_campus=curso_campus)
        if ano_letivo:
            alunos = alunos.filter(ano_letivo=ano_letivo)
        if periodo_letivo:
            alunos = alunos.filter(periodo_letivo=periodo_letivo)
        return alunos


class EditarDadosResponsavelForm(forms.ModelFormPlus):

    fieldsets = (('Dados do Responsável', {'fields': (('parentesco_responsavel', 'cpf_responsavel'), 'responsavel', 'email_responsavel')}),)

    class Meta:
        model = Aluno
        fields = ('parentesco_responsavel', 'cpf_responsavel', 'responsavel', 'email_responsavel')


class RejeitarSolicitacaoCertificadoENEMForm(forms.Form):
    TITLE = 'Rejeitar Solicitação de Certificado ENEM'
    SUBMIT_LABEL = 'Rejeitar Solicitação'
    razao_indeferimento = forms.CharField(widget=forms.Textarea(), required=True, label='Razão do Indeferimento')
    fieldsets = (('Razão do Indeferimento', {'fields': ('razao_indeferimento',)}),)


class ReplicarSolicitacaoCertificadoENEMForm(forms.ModelFormPlus):
    TITLE = 'Replicar Solicitação de Certificado ENEM'
    SUBMIT_LABEL = 'Replicar'

    class Meta:
        model = SolicitacaoCertificadoENEM
        fields = ('nome', 'cpf', 'email', 'telefone',
                  # 'processo'
                  )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        if not self.cleaned_data['processo']:
            raise ValidationError('O número do processo é obrigatório para replicar esta solicitação.')

    def save(self, *args, **kwargs):
        self.instance.replicar(self.request.user)
        return self.instance


class AtenderComRessalvaSolicitacaoCertificadoENEMForm(forms.Form):
    TITLE = 'Atender com Ressalva a Solicitação de Certificado ENEM'
    SUBMIT_LABEL = 'Atender com Ressalva a Solicitação'
    razao_ressalva = forms.CharField(widget=forms.Textarea(), required=True, label='Razão da Ressalva')
    fieldsets = (('Razão da Ressalva', {'fields': ('razao_ressalva',)}),)


class CancelarRegistroEmissaoCertificadoENEMForm(forms.Form):
    TITLE = 'Cancelar o Registro de Emissão de Certificado ENEM'
    SUBMIT_LABEL = 'Cancelar Registro'
    razao_cancelamento = forms.CharField(widget=forms.Textarea(), required=True, label='Razão do Cancelamento')
    fieldsets = (('Razão do Cancelamento', {'fields': ('razao_cancelamento',)}),)

    def __init__(self, *args, **kwargs):
        self.registro = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

    def clean(self):
        if not self.registro.eh_ultima_via():
            raise ValidationError('Apenas a última via pode ser cancelada.')


class RegistroEmissaoCertificadoENEMForm(forms.ModelForm):
    id = forms.CharField(label='Código', widget=forms.TextInput(attrs=dict(readonly=True)))

    class Meta:
        model = RegistroEmissaoDiploma
        fields = ['id']


class PesquisarRegistroAlunoINEPForm(forms.Form):
    METHOD = 'GET'
    TITLE = 'Buscar Candidadatos'
    SUBMIT_LABEL = 'Buscar'
    candidato = forms.ModelChoiceFieldPlus(RegistroAlunoINEP.objects, required=False, widget=AutocompleteWidget(search_fields=RegistroAlunoINEP.SEARCH_FIELDS))
    uo = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus', required=False)

    def __init__(self, configuracao_certificado_enem=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if configuracao_certificado_enem:
            self.fields['candidato'].queryset = RegistroAlunoINEP.objects.filter(configuracao_certificado_enem=configuracao_certificado_enem.pk)

    def processar(self, configuracao_certificado_enem):
        qs = RegistroAlunoINEP.objects.filter(configuracao_certificado_enem=configuracao_certificado_enem.pk).order_by('nome')
        candidato = self.cleaned_data['candidato']
        uo = self.cleaned_data['uo']

        if candidato:
            qs = qs.filter(pk=candidato.pk)

        if uo:
            qs = qs.filter(uo=uo.pk)

        return qs


class EditarRegistroAlunoINEPForm(forms.ModelForm):
    class Meta:
        model = RegistroAlunoINEP
        fields = ['nome', 'rg', 'cpf', 'numero_inscricao', 'data_nascimento', 'nome_mae']


class ConfiguracaoAvaliacaoForm(forms.ModelFormPlus):

    class Media:
        js = ('/static/edu/js/ConfiguracaoAvaliacaoForm.js',)

    class Meta:
        model = ConfiguracaoAvaliacao
        exclude = ('professor',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.NOTA_DECIMAL:
            self.fields['observacao'].widget.attrs['class'] = 'notas-decimais'
        forma_atitudinal = [ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_ATITUDINAL, 'Média Atitudinal']
        if self.instance and self.instance.diario and self.instance.diario.utiliza_nota_atitudinal():
            self.fields['forma_calculo'].choices = [forma_atitudinal, ]
        else:
            choices = ConfiguracaoAvaliacao.FORMA_CALCULO_CHOICES.copy()
            if forma_atitudinal in choices:
                choices.remove(forma_atitudinal)
            self.fields['forma_calculo'].choices = choices

    def clean_divisor(self):
        if self.cleaned_data['forma_calculo'] == ConfiguracaoAvaliacao.FORMA_CALCULO_SOMA_DIVISOR:
            if not self.cleaned_data.get('divisor') or self.cleaned_data['divisor'] < 1:
                raise forms.ValidationError('Insira o valor do divisor, maior que 0, a ser utilizado no cálculo.')
        return self.cleaned_data['divisor']

    def clean(self):
        if self.instance.pk == 1 and not in_group(self.request.user, 'Administrador Acadêmico'):
            raise forms.ValidationError('Não é possível alterar a configuração padrão do sistema. Caso necessite, adicione um nova configuração de avaliação para você.')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)


class ItemConfiguracaoAvaliacaoFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        eh_nota_atitudinal = self.instance.diario.utiliza_nota_atitudinal()

        ids_delete = []
        tem_avaliacao_atitudinal = False
        if hasattr(self, 'cleaned_data'):
            for item in self.cleaned_data:
                if 'DELETE' in item and item['DELETE']:
                    if 'id' in item:
                        ids_delete.append(item['id'].id)
                if eh_nota_atitudinal and 'tipo' in item and item['tipo'] and item['tipo'] == ItemConfiguracaoAvaliacao.TIPO_ATITUDINAL:
                    if not tem_avaliacao_atitudinal:
                        tem_avaliacao_atitudinal = True
                    else:
                        raise ValidationError('Não pode existir mais de uma avaliação do tipo atitudinal.')

            if eh_nota_atitudinal:
                if not tem_avaliacao_atitudinal:
                    raise ValidationError('É obrigatório o cadastro de uma avaliação do tipo Atitudinal.')
                if ids_delete and ItemConfiguracaoAvaliacao.objects.filter(id__in=ids_delete, tipo=ItemConfiguracaoAvaliacao.TIPO_ATITUDINAL).exists():
                    raise ValidationError('Não é possível excluir o item de avaliação Atitudinal.')

            if ids_delete and NotaAvaliacao.objects.filter(item_configuracao_avaliacao__id__in=ids_delete).exclude(nota__isnull=True).exists():
                raise ValidationError('Não é possível excluir o item marcado enquanto houver notas lançadas neste item.')

            qtd_avaliacoes_minimo = eh_nota_atitudinal and 2 or 1
            if (len(ids_delete) + qtd_avaliacoes_minimo) > len(self.cleaned_data):
                raise ValidationError(f'A quantidade de avaliações não pode ser menor que {qtd_avaliacoes_minimo}.')

        soma_nota = 0
        soma_peso = 0
        qtd_itens = 0
        configuracao_avaliacao = None
        divisor = 0
        siglas = []
        MULTIPLICADOR_DECIMAL = 1
        if settings.NOTA_DECIMAL:
            MULTIPLICADOR_DECIMAL = settings.CASA_DECIMAL == 1 and 10 or 100
        for form in self.forms:
            if form.cleaned_data:
                if not configuracao_avaliacao:
                    configuracao_avaliacao = form.cleaned_data['configuracao_avaliacao']
                    divisor = form.cleaned_data['configuracao_avaliacao'].divisor

                if configuracao_avaliacao.forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_PONDERADA and form.cleaned_data.get('peso') is None:
                    raise ValidationError('Informe o peso dos itens de configuração de avaliação.')

                if not form.cleaned_data.get('DELETE'):
                    soma_nota += form.cleaned_data.get('nota_maxima') or 0
                    soma_peso += form.cleaned_data.get('peso') or 0
                    siglas.append(form.cleaned_data.get('sigla'))
                    qtd_itens += 1

                if NotaAvaliacao.objects.filter(
                    matricula_diario__diario=configuracao_avaliacao.diario, item_configuracao_avaliacao=form.instance, nota__gt=(form.instance.nota_maxima * MULTIPLICADOR_DECIMAL)
                ):
                    raise ValidationError(
                        f'Existe uma nota referente ao item de avaliação {form.instance.sigla} maior do que a nota máxima informada: {form.instance.nota_maxima}'
                    )

        for sigla in siglas:
            if not sigla or len(sigla) > 2:
                raise forms.ValidationError('A sigla das avaliações devem ter 1 ou 2 caracteres')

        if configuracao_avaliacao:
            # validando qtd mínima de itens
            minimo_itens = 1
            if configuracao_avaliacao.menor_nota:
                minimo_itens += 1

            if configuracao_avaliacao.maior_nota:
                minimo_itens += 1

            if qtd_itens < minimo_itens:
                raise forms.ValidationError('É necessário a escolha de mais itens devido a escolha das opções: Ignorar Menor Nota e/ou Ignorar Maior Nota.')

            nota_maxima = settings.NOTA_DECIMAL and 10 or 100

            # validando somas por forma de calculo
            forma_calculo = configuracao_avaliacao.forma_calculo

            if forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_SOMA_SIMPLES:
                if soma_nota != nota_maxima:
                    raise forms.ValidationError(f'O somatório das notas das avaliações deve ser {nota_maxima}, mas o resultado da soma foi {soma_nota}.')

            if (
                forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_MAIOR_NOTA
                or forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_PONDERADA
                or forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_ARITMETICA
            ):
                if soma_nota / qtd_itens != nota_maxima:
                    raise forms.ValidationError(f'As notas máximas para esta forma de cálculo devem ser {nota_maxima}.')

            if forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_SOMA_DIVISOR:
                if not divisor:
                    return
                if soma_nota / divisor != nota_maxima:
                    raise forms.ValidationError(f'A soma das notas máximas das avaliações deve ser {divisor * nota_maxima}.')

            if eh_nota_atitudinal and forma_calculo != ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_ATITUDINAL:
                raise forms.ValidationError('Somente a forma de cálculo Atitudinal é permitida para esta configuração.')

        else:
            raise forms.ValidationError('Informe ao menos um item de configuração da avaliação.')


class MonitoramentoForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=True)
    periodo_letivo = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=True)
    diretorias = forms.ModelMultiplePopupChoiceField(Diretoria.objects.all(), label='Diretoria', required=False)
    modalidades = forms.ModelMultiplePopupChoiceField(Modalidade.objects.all(), label='Modalidade', required=False)
    agrupamento = forms.ChoiceField(choices=[['Professor', 'Professor'], ['Data de Fechamento Período', 'Data de Fechamento Período']], label='Agrupamento')

    fieldsets = (('', {'fields': (('ano_letivo', 'periodo_letivo', 'agrupamento'), 'diretorias', 'modalidades')}),)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['diretorias'].queryset = Diretoria.locals.all()

    def clean_periodo_letivo(self):
        if not self.cleaned_data.get('periodo_letivo') or int(self.cleaned_data.get('periodo_letivo')) == 0:
            raise forms.ValidationError('Este campo é obrigatório.')
        return self.cleaned_data.get('periodo_letivo')


class MonitoramentoFechamentoPeriodoForm(MonitoramentoForm):
    agrupamento = forms.ChoiceField(choices=[['Curso', 'Curso'], ['Data de Fechamento Período', 'Data de Fechamento Período']], label='Agrupamento')

    def processar(self, cleaned_data=None):
        compacto = True
        if not cleaned_data:
            compacto = False
            cleaned_data = self.cleaned_data

        # Tratando filtros da tela de monitoramento
        agrupamento = cleaned_data.get('agrupamento')
        ano_letivo = cleaned_data.get('ano_letivo')
        periodo_letivo = cleaned_data.get('periodo_letivo')
        diretorias = cleaned_data.get('diretorias', [])
        modalidades = cleaned_data.get('modalidades', [])

        turmas_ids = list(CalendarioAcademico.objects.filter(
            data_fechamento_periodo__lt=datetime.datetime.now(),
            ano_letivo_id=ano_letivo.id,
            periodo_letivo=periodo_letivo).distinct().values_list('turma__id', flat=True))

        qs = MatriculaPeriodo.objects.filter(
            ano_letivo_id=ano_letivo.id,
            periodo_letivo=periodo_letivo,
            situacao=SituacaoMatriculaPeriodo.MATRICULADO,
            turma_id__in=turmas_ids
        )

        if agrupamento == 'Data de Fechamento Período':
            qs = qs.order_by('turma__calendario_academico__data_fechamento_periodo')
        else:
            qs = qs.order_by('aluno__curso_campus__codigo')

        if diretorias:
            qs = qs.filter(aluno__curso_campus__diretoria_id__in=diretorias)
        if modalidades:
            qs = qs.filter(aluno__curso_campus__modalidade_id__in=modalidades)

        self.qs = qs

        # fechamento de período por diretoria

        graficos = []
        inicial = 0
        qtd_por_grafico = 6
        qtd_cursos = qs.values_list('aluno__curso_campus_id', flat=True).distinct().count()

        for i in range(0, int(qtd_cursos / qtd_por_grafico) + 1):

            series_fechamento = []

            if compacto:
                tmp = qs[0:3]
            else:
                tmp = qs[inicial: inicial + qtd_por_grafico]
            inicial += qtd_por_grafico

            for matricula_periodo in tmp.values('aluno__curso_campus__descricao_historico', 'aluno__curso_campus__codigo').annotate(qtd_aluno=Count('id')):
                nome_curso = '{} - {}'.format(matricula_periodo['aluno__curso_campus__codigo'], matricula_periodo['aluno__curso_campus__descricao_historico'])
                if compacto:
                    nome_curso = defaultfilters.truncatechars(nome_curso, 33)
                series_fechamento.append([nome_curso, matricula_periodo['qtd_aluno']])

            id_grafico_fechamento = f'graficoFechamentoPeriodo_{i}'
            grafico_fechamento = ColumnChart(
                id_grafico_fechamento, title='Períodos Abertos', subtitle='Alunos com período letivo não-fechado após o prazo de fechamento', data=series_fechamento
            )
            grafico_fechamento.series[0]['dataLabels'] = dict(enabled=True, color='#0A0A0A', align='center', y=30)
            grafico_fechamento.id = id_grafico_fechamento

            graficos.append(grafico_fechamento)
            if compacto:
                break

        return self.qs, graficos


class MonitoramentoEntregaDiariosForm(MonitoramentoForm):
    def processar(self, com_grafico, cleaned_data=None):

        compacto = True
        if not cleaned_data:
            compacto = False
            cleaned_data = self.cleaned_data

        qs = ProfessorDiario.objects.filter(ativo=True)

        # Tratando filtros da tela de monitoramento
        agrupamento = cleaned_data.get('agrupamento')

        ano_letivo = cleaned_data.get('ano_letivo')
        periodo_letivo = cleaned_data.get('periodo_letivo')
        diretorias = cleaned_data.get('diretorias', [])
        modalidades = cleaned_data.get('modalidades', [])

        if diretorias:
            qs = qs.filter(diario__turma__curso_campus__diretoria__id__in=diretorias)

        if modalidades:
            qs = qs.filter(diario__turma__curso_campus__modalidade__id__in=modalidades)

        # diários com etapa(s) em posse do professor na data de fechamento do período
        qs = qs.filter(diario__calendario_academico__data_fechamento_periodo__lte=datetime.datetime.now(), diario__ano_letivo=ano_letivo, diario__periodo_letivo=periodo_letivo)

        qs1 = (
            qs.exclude(diario__componente_curricular__qtd_avaliacoes__in=[0, 1], diario__posse_etapa_1=Diario.POSSE_REGISTRO_ESCOLAR)
            .exclude(diario__componente_curricular__qtd_avaliacoes=2, diario__posse_etapa_1=Diario.POSSE_REGISTRO_ESCOLAR, diario__posse_etapa_2=Diario.POSSE_REGISTRO_ESCOLAR)
            .exclude(
                diario__componente_curricular__qtd_avaliacoes=4,
                diario__posse_etapa_1=Diario.POSSE_REGISTRO_ESCOLAR,
                diario__posse_etapa_2=Diario.POSSE_REGISTRO_ESCOLAR,
                diario__posse_etapa_3=Diario.POSSE_REGISTRO_ESCOLAR,
                diario__posse_etapa_4=Diario.POSSE_REGISTRO_ESCOLAR,
            )
        )

        qs2 = qs.filter(diario__posse_etapa_5=Diario.POSSE_PROFESSOR)

        qs = (qs1 | qs2).distinct()

        if agrupamento == 'Data de Fechamento Período':
            qs = qs.order_by('diario__calendario_academico__data_fechamento_periodo')
        else:
            qs = qs.order_by('professor')

        graficos = []
        if com_grafico:
            inicial = 0
            qtd_por_grafico = 15
            qtd_professores = qs.values_list('professor__id', flat=True).distinct().count()

            for i in range(0, (qtd_professores // qtd_por_grafico) + 1):

                series_diarios = []

                if compacto:
                    tmp = qs[0:5]
                else:
                    tmp = qs[inicial: inicial + qtd_por_grafico]
                inicial += qtd_por_grafico

                for professor_diario in tmp.values('professor__vinculo__pessoa__nome').annotate(qtd_diario=Count('id')):
                    nome_professor = professor_diario['professor__vinculo__pessoa__nome']
                    if compacto:
                        nome_professor = nome_professor.split(' ')[0]
                    series_diarios.append([nome_professor, professor_diario['qtd_diario']])

                id_grafico = f'graficoDiarioProfessor_{i}'
                grafico = PieChart(
                    id_grafico, title='Diários Não-Entregues', subtitle='Diários com professor após o prazo de fechamento do período', data=series_diarios, groups=['Professores']
                )
                grafico = grafico
                grafico.id = id_grafico
                graficos.append(grafico)

        return qs, graficos


class InserirDiretoriaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Salvar'
    diretoria = forms.ModelChoiceField(Diretoria.objects, label='Diretoria', required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.objects.order_by('setor')


class RelatorioPeriodosAbertosForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    modalidades = forms.ModelMultiplePopupChoiceField(Modalidade.objects, required=False)
    cursos = forms.MultipleModelChoiceFieldPlus(CursoCampus.objects, required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


class EstatisticaForm(forms.FormPlus):
    class Media:
        js = ('/static/edu/js/EstatisticaForm.js',)

    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    FILTRO_CHOICES = [['por_ano_letivo', 'Ano Letivo'], ['por_periodo_letivo', 'Ano/Período Letivo']]

    MAPA_SITUACAO = dict(
        SITUACAO_MATRICULADO=[
            SituacaoMatriculaPeriodo.APROVADO,
            SituacaoMatriculaPeriodo.APROVEITA_MODULO,
            SituacaoMatriculaPeriodo.DEPENDENCIA,
            SituacaoMatriculaPeriodo.ESTAGIO_MONOGRAFIA,
            SituacaoMatriculaPeriodo.FECHADO_COM_PENDENCIA,
            SituacaoMatriculaPeriodo.MATRICULADO,
            SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
            SituacaoMatriculaPeriodo.PERIODO_FECHADO,
            SituacaoMatriculaPeriodo.VINDO_DE_TRANSFERENCIA,
            SituacaoMatriculaPeriodo.REPROVADO,
            SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA,
        ],
        SITUACAO_CANCELADO=[
            SituacaoMatriculaPeriodo.CANCELADA,
            SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO,
        ],
        SITUACAO_EVALIDO=[SituacaoMatriculaPeriodo.EVASAO],
        SITUACAO_JUBILADO=[SituacaoMatriculaPeriodo.JUBILADO],
        SITUACAO_CANCELADO_EVADIDO_JUBILADO=[
            SituacaoMatriculaPeriodo.CANCELADA,
            SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO,
            SituacaoMatriculaPeriodo.JUBILADO,
            SituacaoMatriculaPeriodo.EVASAO,
        ],
        SITUACAO_RETIDO=[SituacaoMatriculaPeriodo.REPROVADO, SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA],
        SITUACAO_TRANCADO=[
            SituacaoMatriculaPeriodo.AFASTADO,
            SituacaoMatriculaPeriodo.TRANCADA,
            SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE,
            SituacaoMatriculaPeriodo.INTERCAMBIO,
        ],
        SITUACAO_DEPENDENCIA=[SituacaoMatriculaPeriodo.DEPENDENCIA],
        SITUACAO_TRANSFERIDO=[SituacaoMatriculaPeriodo.TRANSF_CURSO, SituacaoMatriculaPeriodo.TRANSF_EXTERNA, SituacaoMatriculaPeriodo.TRANSF_INSTITUICAO],
        SITUACAO_INGRESSANTES=[],
        SITUACAO_CONCLUIDOS=[],
    )

    SITUACOES_CHOICES = [
        ['SITUACAO_MATRICULADO', 'Matriculado'],
        ['SITUACAO_CANCELADO', 'Cancelado'],
        ['SITUACAO_EVALIDO', 'Evadido'],
        ['SITUACAO_JUBILADO', 'Jubiliado'],
        ['SITUACAO_CANCELADO_EVADIDO_JUBILADO', 'Cancelado + Evadido + Jubiliado'],
        ['SITUACAO_RETIDO', 'Retido'],
        ['SITUACAO_TRANCADO', 'Trancado'],
        ['SITUACAO_DEPENDENCIA', 'Dependência'],
        ['SITUACAO_TRANSFERIDO', 'Transferido'],
        ['SITUACAO_INGRESSANTES', 'Ingressante'],
        ['SITUACAO_CONCLUIDOS', 'Concluídos'],
    ]

    RENDA_PER_CAPITA_CHOICES = [
        ['', '---------'],
        ['0', 'Nenhum Salário Mínimo'],
        ['0.5', '0,5 Salário Mínimo'],
        ['1', '1 Salário Mínimo'],
        ['1.5', '1,5 Salários Mínimos'],
        ['2', '2 Salários Mínimos'],
        ['2.5', '2,5 Salários Mínimos'],
        ['3', '3 Salários Mínimos'],
        ['3.5', '3,5 Salários Mínimos']
    ]

    situacao_matricula_periodo = forms.ChoiceField(choices=SITUACOES_CHOICES, label='Situação')

    periodicidade = forms.ChoiceField(label='Periodicidade', choices=FILTRO_CHOICES, required=True, initial='por_ano_letivo')
    apartir_do_ano = forms.ModelChoiceField(Ano.objects.ultimos(), label='A Partir de', required=True)
    ate_ano = forms.ModelChoiceField(Ano.objects.ultimos(), label='Até', required=False)
    excluir_proitec = forms.BooleanField(label='PROITEC', required=False)

    cursos_campus = forms.MultipleModelChoiceField(
        CursoCampus.objects,
        label='Curso', required=False,
        widget=AutocompleteWidget(
            search_fields=CursoCampus.SEARCH_FIELDS,
            form_filters=[('uo', 'diretoria__setor__uo__in')],
            multiple=True)
    )

    modalidades = forms.MultipleModelChoiceField(
        Modalidade.objects.all(), label='Modalidades', required=False,
        widget=CheckboxSelectMultiplePlus())

    sexo = forms.ChoiceField(
        label='Sexo', required=False,
        choices=[['', '---------'], ['M', 'Masculino'], ['F', 'Feminino']])
    racas = forms.ModelMultiplePopupChoiceField(Raca.objects, label='Raça', required=False)
    faixas_de_renda_per_capita = forms.MultipleChoiceField(label='Renda Familiar per Capita',
                                                           required=False, choices=RENDA_PER_CAPITA_CHOICES,
                                                           widget=CheckboxSelectMultiplePlus())

    ira_apartir_de = forms.IntegerField(label='A Partir de', max_value=100, min_value=0, required=False)
    ira_ate = forms.IntegerField(label='Até', max_value=100, min_value=0, required=False)

    renda_apartir_de = forms.ChoiceField(label='A Partir de', choices=RENDA_PER_CAPITA_CHOICES, required=False)
    renda_ate = forms.ChoiceField(label='Até', choices=RENDA_PER_CAPITA_CHOICES, required=False)

    tipos_necessidade_especial = forms.MultipleChoiceField(
        label='Deficiência', required=False,
        choices=Aluno.TIPO_NECESSIDADE_ESPECIAL_CHOICES,
        widget=CheckboxSelectMultiplePlus()
    )
    tipos_transtorno = forms.MultipleChoiceField(label='Transtorno', required=False,
                                                 choices=Aluno.TIPO_TRANSTORNO_CHOICES,
                                                 widget=CheckboxSelectMultiplePlus())
    superdotacao = forms.MultipleChoiceField(label='Superdotação', required=False,
                                             choices=Aluno.SUPERDOTACAO_CHOICES,
                                             widget=CheckboxSelectMultiplePlus())

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        convenios_field_name = ['excluir_proitec']
        for convenio in Convenio.objects.all():
            convenio_field_name = f'{convenio.pk}'
            convenios_field_name.append(convenio_field_name)
            self.fields[convenio_field_name] = forms.BooleanField(label=f'{convenio}', required=False)

        self.fieldsets = (
            ('Filtros Gerais', {'fields': (('situacao_matricula_periodo', 'periodicidade'),
                                           ('apartir_do_ano', 'ate_ano'),
                                           ('cursos_campus'),
                                           ('sexo', 'racas'),
                                           ('modalidades'),
                                           )}),
            ('Índice de Rendimento Acadêmico', {'fields': (('ira_apartir_de', 'ira_ate'),)}),
            ('Renda Familiar per Capita', {'fields': (('renda_apartir_de', 'renda_ate'),)}),
            ('Necessidades Educacionais Específicas', {'fields': ('tipos_necessidade_especial', 'tipos_transtorno', 'superdotacao',)}),
            ('Excluir', {'fields': (convenios_field_name,)}),
        )

    def processar(self):
        qs = (
            MatriculaPeriodo.objects.filter(aluno__ano_letivo__ano__lte=datetime.date.today().year)
            .exclude(aluno__turmaminicurso__gerar_matricula=False)
            .exclude(aluno__curso_campus__modalidade__isnull=True)
        )

        # filtar por convenio
        if self.cleaned_data['excluir_proitec']:
            qs = qs.filter(aluno__matriz__estrutura_id=None) | qs.filter(aluno__matriz__estrutura__proitec=False)

        for convenio in Convenio.objects.all():
            convenio_field_name = f'{convenio.pk}'
            if self.cleaned_data.get(convenio_field_name, False):
                qs = qs.exclude(aluno__convenio=convenio.pk)

        periodicidade = self.cleaned_data.get('periodicidade')

        # filtro por diretoria
        if in_group(self.request.user, 'Secretário Acadêmico'):
            ids_diretorias = Diretoria.locals.all().values_list('id', flat=True)
            qs = qs.filter(aluno__curso_campus__diretoria__id__in=ids_diretorias)

        # filtro por situacao da matricula no periodo
        situacao = self.cleaned_data.get('situacao_matricula_periodo')
        situacoes = EstatisticaForm.MAPA_SITUACAO[situacao]

        if situacoes:
            qs = qs.filter(situacao__id__in=situacoes)

        # filtros por curso, modalidades, sexo, raça, renda per capita e I.R.A
        cursos = self.cleaned_data.get('cursos_campus')
        modalidades = self.cleaned_data.get('modalidades')
        sexo = self.cleaned_data.get('sexo')
        racas = self.cleaned_data.get('racas')
        ira_apartir_de = self.cleaned_data.get('ira_apartir_de')
        ira_ate = self.cleaned_data.get('ira_ate')
        renda_apartir_de = self.cleaned_data.get('renda_apartir_de')
        renda_ate = self.cleaned_data.get('renda_ate')

        if cursos:
            qs = qs.filter(aluno__curso_campus__in=cursos)
        if modalidades:
            qs = qs.filter(aluno__curso_campus__modalidade__in=modalidades)
        if sexo:
            qs = qs.filter(aluno__pessoa_fisica__sexo__exact=sexo)
        if racas:
            qs = qs.filter(aluno__pessoa_fisica__raca__in=racas)

        if renda_apartir_de:
            qs = qs.filter(aluno__renda_per_capita__gte=renda_apartir_de)

        if renda_ate:
            qs = qs.filter(aluno__renda_per_capita__lte=renda_ate)

        if ira_apartir_de or ira_ate:
            ira_apartir_de = ira_apartir_de or 0
            ira_ate = ira_ate or 100
            qs = qs.filter(aluno__ira__gte=ira_apartir_de, aluno__ira__lte=ira_ate)

        # filtros por Necessidades Educacionais Específicas
        tipos_necessidade_especial = self.cleaned_data.get('tipos_necessidade_especial')
        tipos_transtorno = self.cleaned_data.get('tipos_transtorno')
        superdotacao = self.cleaned_data.get('superdotacao')

        qs_nee = []
        if tipos_necessidade_especial:
            qs_nee.append(Q(aluno__tipo_necessidade_especial__in=tipos_necessidade_especial))

        if tipos_transtorno:
            qs_nee.append(Q(aluno__tipo_transtorno__in=tipos_transtorno))

        if superdotacao:
            qs_nee.append(Q(aluno__superdotacao__in=superdotacao))
        if qs_nee:
            qs = qs.filter(reduce(operator.or_, qs_nee)).distinct()

        # montando a lista de campi
        uos = UnidadeOrganizacional.objects.suap().filter(id__in=qs.values_list('aluno__curso_campus__diretoria__setor__uo__id', flat=True).distinct())
        uo_selecionada = None
        if 'uo_selecionada' in self.request.GET:
            uo_id = self.request.GET.get('uo_selecionada', 0)
            if uo_id:
                uo_selecionada = UnidadeOrganizacional.objects.suap().get(pk=uo_id)

        if uo_selecionada:
            qs = qs.filter(aluno__curso_campus__diretoria__setor__uo=uo_selecionada)

        # motando a lista de anos letivos a partir do ano informado pelo usuário
        anos = []
        apartir_do_ano = self.cleaned_data.get('apartir_do_ano')
        ate_ano = self.cleaned_data.get('ate_ano') or Ano.objects.get_or_create(ano=datetime.date.today().year)[0]
        if self.cleaned_data.get('apartir_do_ano'):
            anos = Ano.objects.filter(ano__gte=apartir_do_ano.ano, ano__lte=ate_ano.ano).order_by('ano')

        ano_selecionado = datetime.datetime.now().year
        if anos:
            ano_selecionado = anos[0]

        if self.request and self.request.GET.get('ano_selecionado'):
            ano_selecionado = Ano.objects.get(pk=self.request.GET.get('ano_selecionado'))

        # motando a lista de períodos letivos a partir do ano informado pelo usuário
        periodos = []
        if apartir_do_ano:
            anos_periodo_letivo = Ano.objects.filter(ano__gte=apartir_do_ano.ano, ano__lte=ate_ano.ano).order_by('ano')
            for ano in anos_periodo_letivo:
                periodos.append(f'{ano}.{1}')
                periodos.append(f'{ano}.{2}')
            if not periodos:
                periodos.append(f'{date.today().year}.{1}')

        periodo_selecionado = periodos[0]
        if self.request and self.request.GET.get('periodo_selecionado'):
            ano_periodo_split = self.request.GET.get('periodo_selecionado').split('.')
            periodo_selecionado = f'{ano_periodo_split[0]}.{ano_periodo_split[1]}'

        # montando o gráfico de evolução anual

        series_ano = []
        qtd_alunos_ano = 0
        qtd_alunos_ano_selecionado = 0
        qs_alunos_ano_selecionado = None
        tabela_resumo = []

        if situacao == 'SITUACAO_CONCLUIDOS':
            situacoes = [SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO, SituacaoMatricula.EGRESSO]
            qs = qs.filter(aluno__situacao__id__in=situacoes)
            aluno_ids = qs.values_list('aluno__pk', flat=True).distinct()
            alunos_concluidos = Aluno.objects.filter(pk__in=aluno_ids)
            for ano in anos:
                alunos_concluidos_ano = alunos_concluidos.filter(ano_conclusao=ano.ano)
                qtd_alunos = alunos_concluidos_ano.order_by('id').values_list('id', flat=True).distinct().count()
                series_ano.append([ano.ano, qtd_alunos])
                tabela_resumo.append([ano.ano, qtd_alunos])
                if ano_selecionado == ano:
                    qtd_alunos_ano_selecionado = qtd_alunos
                    qs_alunos_ano_selecionado = alunos_concluidos_ano
            if qs_alunos_ano_selecionado:
                alunos_concluidos = qs_alunos_ano_selecionado
            qs = MatriculaPeriodo.objects.filter(
                pk__in=[aluno.get_ultima_matricula_periodo().pk for aluno in alunos_concluidos.filter(dt_conclusao_curso__year__gte=ano_selecionado.ano)]
            )
            qs = qs.order_by('aluno__id').annotate(qtd_aluno=Count('aluno', distinct=True))
        elif situacao == 'SITUACAO_INGRESSANTES':
            qs = qs.filter(aluno__ano_letivo__in=anos)
            if periodicidade == 'por_ano_letivo':

                for item in qs.values('aluno__ano_letivo__ano').order_by('aluno__ano_letivo__ano').annotate(qtd_aluno=Count('aluno', distinct=True)):
                    ano = int(item['aluno__ano_letivo__ano'])
                    qtd_alunos = item['qtd_aluno'] or 0
                    qtd_alunos_ano = qtd_alunos
                    series_ano.append([ano, qtd_alunos_ano])
                    tabela_resumo.append([ano, qtd_alunos])
                    if ano_selecionado.ano == ano:
                        qtd_alunos_ano_selecionado = qtd_alunos

                qs = qs.filter(aluno__ano_letivo=ano_selecionado).order_by('aluno__id').distinct()

            else:
                for item in (
                    qs.values('aluno__ano_letivo__ano', 'aluno__periodo_letivo')
                    .order_by('aluno__ano_letivo__ano', 'aluno__periodo_letivo')
                    .annotate(qtd_aluno=Count('aluno', distinct=True))
                ):
                    ano_periodo_letivo = '{}.{}'.format(item['aluno__ano_letivo__ano'], item['aluno__periodo_letivo'])
                    qtd_alunos = item['qtd_aluno'] or 0
                    qtd_alunos_ano = qtd_alunos
                    series_ano.append([ano_periodo_letivo, qtd_alunos_ano])
                    tabela_resumo.append([ano_periodo_letivo, qtd_alunos])
                    if periodo_selecionado == ano_periodo_letivo:
                        qtd_alunos_ano_selecionado = qtd_alunos

                ano_periodo_letivo = periodo_selecionado.split('.')
                qs = qs.filter(aluno__ano_letivo__ano=ano_periodo_letivo[0], aluno__periodo_letivo=ano_periodo_letivo[1]).order_by('aluno__id').distinct()

        else:
            qs = qs.filter(ano_letivo__in=anos)
            if periodicidade == 'por_ano_letivo':

                for item in qs.values('ano_letivo__ano').order_by('ano_letivo__ano').annotate(qtd_aluno=Count('aluno', distinct=True)):
                    ano = int(item['ano_letivo__ano'])
                    qtd_alunos = item['qtd_aluno'] or 0
                    qtd_alunos_ano = qtd_alunos
                    series_ano.append([ano, qtd_alunos_ano])
                    tabela_resumo.append([ano, qtd_alunos])
                    if ano_selecionado.ano == ano:
                        qtd_alunos_ano_selecionado = qtd_alunos

                qs = qs.filter(ano_letivo=ano_selecionado).order_by('aluno__id').distinct()

            else:
                for item in qs.values('ano_letivo__ano', 'periodo_letivo').annotate(qtd_aluno=Count('aluno')):
                    ano_periodo_letivo = '{}.{}'.format(item['ano_letivo__ano'], item['periodo_letivo'])
                    qtd_alunos = item['qtd_aluno'] or 0
                    qtd_alunos_ano = qtd_alunos
                    series_ano.append([ano_periodo_letivo, qtd_alunos_ano])
                    tabela_resumo.append([ano_periodo_letivo, qtd_alunos])
                    if periodo_selecionado == ano_periodo_letivo:
                        qtd_alunos_ano_selecionado = qtd_alunos

                ano_periodo_letivo = periodo_selecionado.split('.')
                qs = qs.filter(ano_letivo__ano=ano_periodo_letivo[0], periodo_letivo=ano_periodo_letivo[1])
        id_grafico_evolucao_anual = 'id_grafico_evolucao_anual'
        grafico_evolucao_anual = LineChart(id_grafico_evolucao_anual, title='Total de Alunos por Ano', data=series_ano, groups=['Alunos'])
        grafico_evolucao_anual.id = id_grafico_evolucao_anual
        grafico_evolucao_anual.tabela_resumo = tabela_resumo
        grafico_evolucao_anual.qtd_alunos_ano_selecionado = qtd_alunos_ano_selecionado

        alunos = Aluno.objects.filter(id__in=qs.order_by('aluno__id').values_list('aluno__id', flat=True).distinct()).select_related(
            'curso_campus__diretoria__setor__uo', 'curso_campus__modalidade', 'pessoa_fisica__pessoa_ptr'
        )

        return uos, anos, periodos, uo_selecionada, ano_selecionado, periodo_selecionado, grafico_evolucao_anual, alunos


class IndicadoresForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    MAPA_SITUACAO = dict(
        ATENDIDOS=[
            SituacaoMatriculaPeriodo.EM_ABERTO,
            SituacaoMatriculaPeriodo.MATRICULADO,
            SituacaoMatriculaPeriodo.TRANCADA,
            SituacaoMatriculaPeriodo.AFASTADO,
            SituacaoMatriculaPeriodo.DEPENDENCIA,
            SituacaoMatriculaPeriodo.DEPENDENCIA,
            SituacaoMatriculaPeriodo.APROVADO,
            SituacaoMatriculaPeriodo.REPROVADO,
            SituacaoMatriculaPeriodo.VINDO_DE_TRANSFERENCIA,
            SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA,
            SituacaoMatriculaPeriodo.ESTAGIO_MONOGRAFIA,
            SituacaoMatriculaPeriodo.PERIODO_FECHADO,
            SituacaoMatriculaPeriodo.INTERCAMBIO,
            SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
            SituacaoMatriculaPeriodo.APROVEITA_MODULO,
            SituacaoMatriculaPeriodo.FECHADO_COM_PENDENCIA,
        ],
        CONCLUIDOS=[
            SituacaoMatricula.EGRESSO,
            SituacaoMatricula.CONCLUIDO,
            SituacaoMatricula.AGUARDANDO_COLACAO_DE_GRAU,
            SituacaoMatricula.AGUARDANDO_ENADE,
            SituacaoMatricula.AGUARDANDO_SEMINARIO,
        ],
        EVADIDOS=[
            SituacaoMatriculaPeriodo.CANCELADA,
            SituacaoMatriculaPeriodo.TRANSF_EXTERNA,
            SituacaoMatriculaPeriodo.TRANSF_INSTITUICAO,
            SituacaoMatriculaPeriodo.JUBILADO,
            SituacaoMatriculaPeriodo.EVASAO,
            SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO,
        ],
        RETIDOS=[
            SituacaoMatriculaPeriodo.REPROVADO,
            SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA,
            SituacaoMatriculaPeriodo.TRANCADA,
            SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE,
            SituacaoMatriculaPeriodo.AFASTADO,
            SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
        ],
        REGULARES=[SituacaoMatriculaPeriodo.MATRICULADO, SituacaoMatriculaPeriodo.APROVADO, SituacaoMatriculaPeriodo.ESTAGIO_MONOGRAFIA],
    )

    SITUACOES_CHOICES = [
        ['SITUACAO_MATRICULADO', 'Matriculado'],
        ['SITUACAO_CANCELADO', 'Cancelado'],
        ['SITUACAO_RETIDO', 'Retido'],
        ['SITUACAO_TRANCADO', 'Trancado'],
        ['SITUACAO_DEPENDENCIA', 'Dependência'],
        ['SITUACAO_TRANSFERIDO', 'Transferido'],
        ['SITUACAO_INGRESSANTES', 'Ingressante'],
        ['SITUACAO_CONCLUIDOS', 'Concluído'],
    ]

    INDICADORES = {
        '01_TAXA_RETENCAO': [
            '01 - Taxa de Retenção',
            'Este indicador mede o percentual de alunos retidos em relação ao total de matrículas atendidas. '
            + 'O resultado desse indicador mostra, do universo total de matrículas atendidas em cada período, '
            + 'o percentual de alunos que atrasaram a conclusão do seu curso. Esse indicador só dará 100% se '
            + 'todos as matrículas do curso estiverem retidas. O resultado deste indicador possui relação '
            + 'direta com a duração dos cursos.',
        ],
        '02_TAXA_CONCLUSAO': [
            '02 - Taxa de Conclusão',
            'Este indicador mede o percentual de conclusão em relação ao total de matrículas atendidas. '
            + 'O resultado deste indicador possui relação direta com a duração dos cursos e com a quantidade '
            + 'de vagas ofertadas em cada período de análise. Por exemplo, em um curso com duração de 4 anos, '
            + 'que oferta em todos os período a mesma quantidade de vagas, e todos os alunos concluem no prazo, '
            + 'o resultado será de 25%, ou seja, este indicador somente atingirá 100% em curso com início e '
            + 'término no mesmo ano. Por este motivo, não é recomendável analisá-lo de maneira isolada, mas em '
            + 'conjunto com os indicadores nº 3, 4, 5 e 6, tendo em vista que os cinco indicadores somados '
            + 'contemplam todas as matrículas atendidas da instituição no ano, totalizando 100%,',
        ],
        '03_TAXA_EVASAO': [
            '03 - Taxa de Evasão',
            'Este indicador mede o percentual de matrículas finalizadas evadidas em relação ao total de matrículas '
            + 'atendidas. O resultado deste indicador possui relação direta com a duração dos cursos. Este indicador '
            + 'é influenciado pela taxa de crescimento das matrículas no período. Somado aos indicadores nº 2, 4, 5 e '
            + '6 contempla todas as matrículas atendidas da instituição no ano, totalizando 100%,',
        ],
        '04_TAXA_REPROVACOES': [
            '04 - Taxa de Reprovações',
            'Este indicador mede o percentual de reprovação em relação ao total de matrículas atendidas. O '
            + 'resultado deste indicador possui relação direta com a duração dos cursos e com a quantidade de '
            + 'vagas ofertadas em cada ano. Por exemplo, em um curso com duração de 4 anos, que oferta em todos '
            + 'os anos a mesma quantidade de vagas, que não há retenção e todos os alunos reprovam, o resultado '
            + 'será de 25%, ou seja, este indicador somente atingirá 100% em curso com início e término no mesmo '
            + 'ano. Por este motivo, não é recomendável analisá-lo de maneira isolada, mas em conjunto com os '
            + 'indicadores nº 2, 3, 5 e 6, tendo em vista que os cinco indicadores somados contemplam todas as '
            + 'matrículas atendidas da instituição no ano, totalizando 100%,',
        ],
        '05_TAXA_ATIVOS_REGULARES': [
            '05 - Taxa de Matrícula Ativa Regular',
            'Este indicador mede o percentual de matrículas que ao final de cada período analisado '
            + 'continuam ativas sem retenção em relação ao total de matrículas atendidas. O resultado '
            + 'deste indicador possui relação direta com a duração dos cursos. Este indicador é '
            + 'influenciado pela taxa de crescimento das matrículas no período. Somado aos indicadores '
            + 'nº 2, 3, 4 e 6 contempla todas as matrículas atendidas da instituição no ano, totalizando 100%,',
        ],
        '06_TAXA_ATIVOS_RETIDOS': [
            '06 - Taxa de Matrícula Ativa Retida',
            'Este indicador mede o percentual de matrículas retidas que ao final de cada período analisado '
            + 'continuam ativas em relação ao total de matrículas atendidas. O resultado deste indicador possui '
            + 'relação direta com a duração dos cursos. Este indicador é influenciado pela taxa de crescimento '
            + 'das matrículas no período. Somado aos indicadores nº 2, 3, 4 e 5 contempla todas as matrículas '
            + 'atendidas da instituição no ano, totalizando 100%,',
        ],
        '07_TAXA_EFETIVIDADE': [
            '07 - Índice de Efetividade Acadêmica',
            'Este indicador mede o percentual de conclusão efetiva em relação à conclusão prevista no início do '
            + 'curso. O resultado deste indicador não depende da duração do curso nem da taxa de crescimento da '
            + 'matricula no período. Apresenta assim o percentual de concluintes dentro do prazo em relação à '
            + 'previsão de concluintes para o período. Em uma situação hipotética onde todos os alunos '
            + 'ingressantes de uma instituição concluem o seu curso no prazo previsto, o resultado desse '
            + 'indicador será 100.',
        ],
        '08_TAXA_SAIDA_EXITO': [
            '08 - Taxa de Saída com Êxito',
            'Este indicador mede o percentual de alunos que alcançaram êxito no curso dentre aqueles que '
            + 'finalizam o mesmo. Este indicador não é influenciado pela taxa de crescimento da instituição '
            + 'nem pela duração do curso.',
        ],
        '09_TAXA_PERMANENCIA_EXITO': [
            '09 - Índice de Permanência e Êxito',
            'Este indicador mede a permanência e o êxito dos estudantes da instituição a partir do '
            + 'somatório da Taxa de Conclusão e da Taxa de Matrícula Continuada Regular. Quanto menor '
            + 'for o número de matrículas finalizadas sem êxito, e menor for o número de matrículas '
            + 'retidas, mais o resultado desse indicador se aproximará de 100%.',
        ],
        '10_INDICE_EFICACIA': [
            '10 - Índice de Eficácia',
            'Este indicador quantifica a eficiência das ofertas educacionais da Instituição, através da relação entre o número de alunos concluintes e o número de vagas ofertadas no processo seletivo para suas respectivas turmas.',
        ],
        '11_INDICE_EFICIENCIA': [
            '11 - Índice de Eficiência',
            'Este indicador quantifica a eficiência das ofertas educacionais da Instituição, através da relação entre o número de alunos concluintes e onúmero de alunos ingressantes nas respectivas turmas.',
        ],
    }

    ano_inicio = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo Inicial', required=True)
    ano_fim = forms.ModelChoiceField(Ano.objects.filter(matriculaperiodo__isnull=False).distinct(), label='Ano Letivo Final')
    uos = forms.MultipleModelChoiceField(UnidadeOrganizacional.objects.campi().all(), label='Campi', widget=CheckboxSelectMultiplePlus())
    modalidades = forms.MultipleModelChoiceField(Modalidade.objects.all(), label='Modalidades', widget=CheckboxSelectMultiplePlus())
    tipos_necessidade_especial = forms.MultipleChoiceField(
        required=False, label='Deficiência', choices=Aluno.TIPO_NECESSIDADE_ESPECIAL_CHOICES, widget=CheckboxSelectMultiplePlus()
    )
    tipos_transtorno = forms.MultipleChoiceField(required=False, label='Transtorno', choices=Aluno.TIPO_TRANSTORNO_CHOICES, widget=CheckboxSelectMultiplePlus())
    superdotacao = forms.MultipleChoiceField(required=False, label='Superdotação', choices=Aluno.SUPERDOTACAO_CHOICES, widget=CheckboxSelectMultiplePlus())

    fieldsets = (
        ('', {'fields': (('ano_inicio', 'ano_fim'), 'uos', 'modalidades')}),
        ('Necessidades Educacionais Específicas', {'fields': ('tipos_necessidade_especial', 'tipos_transtorno', 'superdotacao')}),
    )

    # escolher as modalidades para aparecer nos bullets
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['modalidades'].initial = [campo.pk for campo in Modalidade.objects.all()]
        self.fields['uos'].initial = [campo.pk for campo in UnidadeOrganizacional.objects.campi().all()]

    def clean(self):
        if self.cleaned_data.get('ano_inicio') and self.cleaned_data.get('ano_fim') and self.cleaned_data.get('ano_inicio').ano > self.cleaned_data.get('ano_fim').ano:
            raise ValidationError('Ano letivo inicial deve ser menor que o final.')
        return self.cleaned_data

    @staticmethod
    def processar_variaveis(ano_inicio, ano_fim, modalidades_id, uos_id, uo_id=None, curso_id=None, tipos_necessidade_especial=None, tipos_transtorno=None, superdotacao=None):
        REPROVADOS = [SituacaoMatriculaPeriodo.REPROVADO, SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA]

        RETIDOS = [
            SituacaoMatriculaPeriodo.REPROVADO,
            SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA,
            SituacaoMatriculaPeriodo.AFASTADO,
            SituacaoMatriculaPeriodo.TRANCADA,
            SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
        ]

        FINALIZADOS = [
            SituacaoMatriculaPeriodo.TRANCADA,
            SituacaoMatriculaPeriodo.CANCELADA,
            SituacaoMatriculaPeriodo.AFASTADO,
            SituacaoMatriculaPeriodo.TRANSF_EXTERNA,
            SituacaoMatriculaPeriodo.TRANSF_INSTITUICAO,
            SituacaoMatriculaPeriodo.TRANSF_TURNO,
            SituacaoMatriculaPeriodo.TRANSF_CURSO,
            SituacaoMatriculaPeriodo.JUBILADO,
            SituacaoMatriculaPeriodo.EVASAO,
            SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO,
        ]

        CONCLUINTES = (
            SituacaoMatricula.CONCLUIDO,
            SituacaoMatricula.EGRESSO,
            SituacaoMatricula.FORMADO
        )
        # no gestao nao aplica filtro de exclusão abaixo
        qs = MatriculaPeriodo.objects.exclude(aluno__turmaminicurso__gerar_matricula=False)
        qs = qs.filter(aluno__curso_campus__modalidade_id__in=modalidades_id)
        qs = qs.filter(aluno__curso_campus__diretoria__setor__uo_id__in=uos_id)

        qs_nee = []
        if tipos_necessidade_especial:
            qs_nee.append(Q(aluno__tipo_necessidade_especial__in=tipos_necessidade_especial))

        if tipos_transtorno:
            qs_nee.append(Q(aluno__tipo_transtorno__in=tipos_transtorno))

        if superdotacao:
            qs_nee.append(Q(aluno__superdotacao__in=superdotacao))

        if qs_nee:
            qs = qs.filter(reduce(operator.or_, qs_nee)).distinct()

        if uo_id:
            qs = qs.filter(aluno__curso_campus__diretoria__setor__uo_id=uo_id)

        if curso_id:
            qs = qs.filter(aluno__curso_campus_id=curso_id)

        qs = qs.select_related('ano_letivo', 'aluno')
        mp = dict()
        mp['CONTINUADOS_RETIDOS'] = dict()
        mp['CONTINUADOS_REGULARES'] = dict()
        mp['RETIDOS'] = dict()
        mp['ATENDIDOS'] = dict()
        mp['CONCLUIDOS'] = dict()
        mp['CONCLUIDOS_PRAZO'] = dict()
        mp['EVADIDOS'] = dict()
        mp['FINALIZADOS'] = dict()
        mp['REPROVADOS'] = dict()
        mp['PREVISTOS'] = dict()
        mp['CONCLUINTES'] = dict()
        mp['INGRESSOS'] = dict()
        mp['INGRESSANTES'] = dict()

        for ano in range(ano_inicio, ano_fim + 1):
            # filtrando apenas alunos com matrícula período no ano de análise
            tmp = qs.filter(ano_letivo__ano=ano, periodo_letivo=2)
            qs_atendidos = tmp | qs.filter(ano_letivo__ano=ano, periodo_letivo=1).exclude(aluno__in=tmp.values_list('aluno__id', flat=True))
            # obtendo os que já tiveram ao menos uma reprovação até o período de análise
            qs_alunos_retidos = qs.filter(ano_letivo__ano__gt=2000, ano_letivo__ano__lte=ano, situacao__in=RETIDOS).values_list('aluno_id', flat=True)
            # filtrando os alunos que continuam ativos
            qs_continuadas = qs_atendidos.exclude(aluno__ano_conclusao=ano).exclude(situacao__in=FINALIZADOS)
            # filtrando os alunos que concluíram no ano de análise
            qs_finalizadas_com_exito = qs_atendidos.filter(aluno__ano_conclusao=ano)
            # filtrando os alunos que se deixaram o instituto sem concluir o curso
            qs_finalizadas_sem_exito = qs_atendidos.filter(situacao__in=FINALIZADOS)
            # identificando os alunos que deixam o instituo
            qs_finalizados = qs_finalizadas_com_exito | qs_finalizadas_sem_exito
            # filtrando apenas os alunos que nunca reprovaram no período
            qs_continuadas_regulares = qs_continuadas.exclude(aluno__in=qs_alunos_retidos)
            # filtrando os alunos que já reprovaram ao menos um período
            qs_continuadas_retidos = qs_continuadas.filter(aluno__in=qs_alunos_retidos)
            # filtrando os alunos que concluíram no ano de análise e dentro do prazo previsto
            qs_finalizadas_com_exito_no_prazo = qs_finalizadas_com_exito.extra(where=["EXTRACT(YEAR FROM edu_aluno.dt_conclusao_curso) <= edu_aluno.ano_let_prev_conclusao"])
            qs_dentro_prazo = qs_atendidos.filter(aluno__ano_let_prev_conclusao=ano)
            qs_fora_prazo = qs_atendidos.filter(aluno__ano_let_prev_conclusao__lt=ano)
            # filtrando os alunos que reprovaram no período de análise
            qs_reprovados = qs_atendidos.filter(situacao__in=REPROVADOS)
            # variável AC_OR - calculo copiado do gestao
            qs_concluintes = qs.filter(
                aluno__dt_conclusao_curso__year=ano,
                aluno__situacao_id__in=CONCLUINTES,
                aluno__convenio__isnull=True
            ).distinct()
            # variável AICOR_OR - calculo copiado do gestao
            situacao_matricula_periodo_codigo = (0, 1, 2, 3, 4, 9, 10, 11, 15, 18, 19, 23, 25)
            sql = f'(select t2.codigo_academico from edu_historicosituacaomatriculaperiodo t1 inner join edu_situacaomatriculaperiodo t2 on t1.situacao_id = t2.id where matricula_periodo_id = edu_matriculaperiodo.id and data >= \'{ano}-01-01\' and data <= \'{ano}-12-31\' order by data desc limit 1)'
            qs_ingressos = qs.extra(where=[sql + ' IN ' + str(situacao_matricula_periodo_codigo)])
            qs_AICOR_OR_1 = qs_ingressos.filter(ano_letivo__ano=ano, periodo_letivo=1)
            qs_AICOR_OR_2 = qs_ingressos.filter(aluno__ano_letivo__ano=ano, aluno__situacao__ativo=True).exclude(aluno__periodo_letivo=1)
            qs_AICOR_OR_3 = qs_ingressos.filter(aluno__ano_letivo__ano=ano - 1, aluno__curso_campus__modalidade__id__in=[8, 1], aluno__situacao__codigo_academico=0)
            qs_ingressos = qs_AICOR_OR_1 | qs_AICOR_OR_2 | qs_AICOR_OR_3
            qs_ingressos = qs_ingressos.values('aluno__curso_campus', 'ano_letivo', 'periodo_letivo').distinct()
            qs_tmp = MatriculaPeriodo.objects.none()
            for aip in qs_ingressos:
                qs_tmp = qs_tmp | MatriculaPeriodo.objects.filter(aluno__curso_campus=aip['aluno__curso_campus'], ano_letivo=aip['ano_letivo'], periodo_letivo=aip['periodo_letivo'])
            # no gestao retorna mais de uma matricula periodo de um mesmo aluno
            qs_ingressos = qs_tmp.filter(aluno__convenio__isnull=True)  # .distinct()

            # variável AIC_OR - calculo copiado do gestao
            qs_ingressantes = qs.filter(aluno__ano_let_prev_conclusao=ano, aluno__curso_campus__modalidade__id__isnull=False)
            qs_ingressantes = qs_ingressantes | qs.filter(aluno__curso_campus__descricao__unaccent__icontains='PROITEC', aluno__ano_letivo__ano=ano)
            qs_ingressantes = qs_ingressantes.filter(aluno__convenio__isnull=True).distinct()

            mp['ATENDIDOS'][ano] = qs_atendidos.values_list('aluno_id', flat=True)
            mp['RETIDOS'][ano] = qs_fora_prazo.values_list('aluno_id', flat=True)
            mp['EVADIDOS'][ano] = qs_finalizadas_sem_exito.values_list('aluno_id', flat=True)
            mp['FINALIZADOS'][ano] = qs_finalizados.values_list('aluno_id', flat=True)
            mp['CONCLUIDOS'][ano] = qs_finalizadas_com_exito.values_list('aluno_id', flat=True)
            mp['REPROVADOS'][ano] = qs_reprovados.values_list('aluno_id', flat=True)
            mp['CONTINUADOS_REGULARES'][ano] = qs_continuadas_regulares.values_list('aluno_id', flat=True)
            mp['CONTINUADOS_RETIDOS'][ano] = qs_continuadas_retidos.values_list('aluno_id', flat=True)
            mp['CONCLUIDOS_PRAZO'][ano] = qs_finalizadas_com_exito_no_prazo.values_list('aluno_id', flat=True)
            mp['PREVISTOS'][ano] = qs_dentro_prazo.values_list('aluno_id', flat=True)
            mp['CONCLUINTES'][ano] = qs_concluintes.values_list('aluno_id', flat=True)
            mp['INGRESSOS'][ano] = qs_ingressos.values_list('aluno_id', flat=True)
            mp['INGRESSANTES'][ano] = qs_ingressantes.values_list('aluno_id', flat=True)

            # indicadores 2,3,4,5,6 somados deveriam dar 100%
        return mp

    @staticmethod
    def gerar_indicadores(anos, variaveis):
        indicadores = dict()
        indicadores['01_TAXA_RETENCAO'] = OrderedDict()
        indicadores['02_TAXA_CONCLUSAO'] = OrderedDict()
        indicadores['03_TAXA_EVASAO'] = OrderedDict()
        indicadores['04_TAXA_REPROVACOES'] = OrderedDict()
        indicadores['05_TAXA_ATIVOS_REGULARES'] = OrderedDict()
        indicadores['06_TAXA_ATIVOS_RETIDOS'] = OrderedDict()
        indicadores['07_TAXA_EFETIVIDADE'] = OrderedDict()
        indicadores['08_TAXA_SAIDA_EXITO'] = OrderedDict()
        indicadores['09_TAXA_PERMANENCIA_EXITO'] = OrderedDict()
        indicadores['10_INDICE_EFICACIA'] = OrderedDict()
        indicadores['11_INDICE_EFICIENCIA'] = OrderedDict()

        for ano in anos:
            atendidos = float(variaveis['ATENDIDOS'][ano].count())
            retidos = float(variaveis['RETIDOS'][ano].count())
            concluidos = float(variaveis['CONCLUIDOS'][ano].count())
            evadidos = float(variaveis['EVADIDOS'][ano].count())
            previstos = float(variaveis['PREVISTOS'][ano].count())
            reprovados = float(variaveis['REPROVADOS'][ano].count())
            continuados_regulares = float(variaveis['CONTINUADOS_REGULARES'][ano].count())
            continuados_retidos = float(variaveis['CONTINUADOS_RETIDOS'][ano].count())
            concluidos_prazo = float(variaveis['CONCLUIDOS_PRAZO'][ano].count())
            finalizados = float(variaveis['FINALIZADOS'][ano].count())
            concluintes = float(variaveis['CONCLUINTES'][ano].count())
            ingressos = float(variaveis['INGRESSOS'][ano].count())
            ingressantes = float(variaveis['INGRESSANTES'][ano].count())

            indicadores['01_TAXA_RETENCAO'][ano] = (retidos / (atendidos or 1)) * 100
            indicadores['02_TAXA_CONCLUSAO'][ano] = (concluidos / (atendidos or 1)) * 100
            indicadores['03_TAXA_EVASAO'][ano] = (evadidos / (atendidos or 1)) * 100
            indicadores['04_TAXA_REPROVACOES'][ano] = (reprovados / (atendidos or 1)) * 100
            indicadores['05_TAXA_ATIVOS_REGULARES'][ano] = (continuados_regulares / (atendidos or 1)) * 100
            indicadores['06_TAXA_ATIVOS_RETIDOS'][ano] = (continuados_retidos / (atendidos or 1)) * 100
            indicadores['07_TAXA_EFETIVIDADE'][ano] = (concluidos_prazo / (previstos or 1)) * 100
            indicadores['08_TAXA_SAIDA_EXITO'][ano] = (concluidos / (finalizados or 1)) * 100
            indicadores['09_TAXA_PERMANENCIA_EXITO'][ano] = indicadores['02_TAXA_CONCLUSAO'][ano] + indicadores['05_TAXA_ATIVOS_REGULARES'][ano]
            indicadores['10_INDICE_EFICACIA'][ano] = (concluintes / (ingressos or 1)) * 100
            indicadores['11_INDICE_EFICIENCIA'][ano] = (concluintes / (ingressantes or 1)) * 100
        return indicadores

    def processar_indicadores(self):

        ano_inicio = self.cleaned_data.get('ano_inicio').ano
        ano_fim = self.cleaned_data.get('ano_fim', Ano.objects.latest('ano')).ano
        modalidade_selecionada = self.request.GET.get('modalidade_selecionada', None)
        modalidades = self.cleaned_data.get('modalidades', None)
        uo_selecionada = self.request.GET.get('uo_selecionada', None)
        uos = self.cleaned_data['uos']
        curso_selecionado = self.request.GET.get('curso_selecionado', None)
        cursos = None

        tipos_necessidade_especial = self.cleaned_data.get('tipos_necessidade_especial')
        tipos_transtorno = self.cleaned_data.get('tipos_transtorno')
        superdotacao = self.cleaned_data.get('superdotacao')

        anos = list(range(ano_inicio, ano_fim + 1))
        if uo_selecionada:
            uo_selecionada = int(uo_selecionada)
            cursos = CursoCampus.objects.filter(diretoria__setor__uo_id=uo_selecionada, modalidade_id__in=modalidades)
        else:
            uo_selecionada = 0

        if curso_selecionado:
            curso_selecionado = int(curso_selecionado)
        else:
            curso_selecionado = 0

        variaveis = IndicadoresForm.processar_variaveis(
            ano_inicio,
            ano_fim,
            modalidades,
            uos,
            uo_id=uo_selecionada,
            curso_id=curso_selecionado,
            tipos_necessidade_especial=tipos_necessidade_especial,
            tipos_transtorno=tipos_transtorno,
            superdotacao=superdotacao,
        )

        indicadores = IndicadoresForm.gerar_indicadores(anos, variaveis)
        return (
            uos,
            anos,
            uo_selecionada,
            OrderedDict(sorted(list(indicadores.items()), key=lambda t: t[0])),
            modalidade_selecionada,
            modalidades,
            curso_selecionado,
            cursos,
            tipos_necessidade_especial,
            tipos_transtorno,
            superdotacao,
        )


class MatriculaIngressosTurmaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Pesquisar'
    METHOD = 'GET'

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, label='Período Letivo')
    diretoria = forms.ModelChoiceField(Diretoria.objects.none())
    curso = forms.ModelChoiceFieldPlus(CursoCampus.objects, label='Curso', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals
        self.fields['curso'].queryset = CursoCampus.objects.filter(ativo=True, diretoria__in=Diretoria.locals.all())

    def processar(self):
        qs_turmas = Turma.locals.filter(
            ano_letivo=self.cleaned_data.get("ano_letivo"), periodo_letivo=self.cleaned_data.get("periodo_letivo"), curso_campus__diretoria=self.cleaned_data.get("diretoria")
        )

        if self.cleaned_data.get("curso"):
            qs_turmas = qs_turmas.filter(curso_campus=self.cleaned_data.get("curso"))

        turmas = []
        alunos_aptos_matricular = []
        for turma in qs_turmas:
            alunos_nao_matriculados = turma.get_alunos_apto_matricula(apenas_ingressantes=True)
            turma.total_nao_matriculados = alunos_nao_matriculados.count()
            if turma.total_nao_matriculados:
                alunos_aptos_matricular = alunos_aptos_matricular + list(alunos_nao_matriculados.values_list("aluno__id", flat=True))
                turma.total_matriculados = turma.get_alunos_matriculados().count()
                turma.total_aptos_matricula = turma.get_alunos_apto_matricula(ignorar_matriculados=False, apenas_ingressantes=True).count()
                turmas.append(turma)

        return turmas, list(set(alunos_aptos_matricular))


class EscolherReitorDiretorGeralForm(forms.FormPlus):
    reitor = forms.ModelChoiceField(Servidor.objects, required=True, label='Servidor')
    diretor_geral = forms.ModelChoiceField(Servidor.objects, required=True, label='Servidor')

    fieldsets = (('Reitor', {'fields': ('reitor', 'reitor_em_exercicio')}), ('Diretor Geral', {'fields': ('diretor_geral', 'diretor_geral_em_exercicio')}))

    def __init__(self, diretores_gerais, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reitor'].queryset = Servidor.objects.filter(excluido=False, funcao__codigo='CD', funcao_codigo__in=[1, 2])

        self.fields['diretor_geral'].queryset = diretores_gerais


class CoordenadorRegistroAcademicoForm(forms.ModelFormPlus):
    def __init__(self, *args, **kwargs):
        diretoria = kwargs.pop('diretoria')
        super().__init__(*args, **kwargs)
        pks_coordenadores_cadastrados = CoordenadorRegistroAcademico.objects.exclude(pk=self.instance.pk).filter(diretoria=diretoria).values_list('servidor__pk', flat=True)
        self.fields['servidor'].queryset = Servidor.objects.all().exclude(pk__in=pks_coordenadores_cadastrados)

    class Meta:
        model = CoordenadorRegistroAcademico
        exclude = ['diretoria']


class CoordenadorModalidadeForm(forms.ModelFormPlus):
    def __init__(self, *args, **kwargs):
        diretoria = kwargs.pop('diretoria')
        super().__init__(*args, **kwargs)
        pks_coordenadores_cadastrados = CoordenadorModalidade.objects.filter(diretoria=diretoria).values_list('servidor__pk', flat=True)
        self.fields['servidor'].queryset = Servidor.objects.all().exclude(pk__in=pks_coordenadores_cadastrados)
        if self.instance and self.instance.pk and self.instance.servidor:
            self.fields['servidor'].queryset = self.fields['servidor'].queryset | Servidor.objects.filter(pk=self.instance.servidor.pk)
            self.fields['servidor'].initial = self.instance.servidor.pk

    class Meta:
        model = CoordenadorModalidade
        exclude = ['diretoria']


class ImportarComponentesForm(forms.FormPlus):
    planilha = forms.FileFieldPlus(
        required=True,
        help_text='O arquivo deve ser no formato "xlsx", sem cabeçalho, contendo as seguintes colunas: Descrição, Núcleo, Carga Horária - Relógio, Carga Horária - Aula, Qtd. de Créditos, Tipo do Componente e Nível de Ensino.',
    )

    def clean(self):
        try:
            self.componentes = []
            planilha = self.cleaned_data['planilha'].file
            workbook = xlrd.open_workbook(file_contents=planilha.read())
            sheet = workbook.sheet_by_index(0)

            for i in range(0, sheet.nrows):
                descricao = str(sheet.cell_value(i, 0))
                nucleo = str(sheet.cell_value(i, 1))
                carga_horaria_relogio = int(sheet.cell_value(i, 2))
                carga_horaria_aula = int(sheet.cell_value(i, 3))
                qtd_creditos = int(sheet.cell_value(i, 4))
                tipo_componente = str(sheet.cell_value(i, 5))
                nivel_ensino = str(sheet.cell_value(i, 6))

                try:
                    componente = dict(
                        descricao=f'{descricao} ({nucleo})',
                        descricao_historico=descricao,
                        ch_hora_relogio=carga_horaria_relogio,
                        ch_hora_aula=carga_horaria_aula,
                        ch_qtd_creditos=qtd_creditos,
                        tipo=TipoComponente.objects.get(descricao=tipo_componente),
                        nivel_ensino=NivelEnsino.objects.get(descricao=nivel_ensino),
                        diretoria=Diretoria.objects.get(setor__sigla=utils.get_sigla_reitoria()),
                    )

                    self.componentes.append(componente)
                except TipoComponente.DoesNotExist:
                    raise ValidationError(f'O Tipo do Componente "{tipo_componente}" não foi encontrado.')
                except NivelEnsino.DoesNotExist:
                    raise ValidationError(f'O Nível de Ensino "{nivel_ensino}" não foi encontrado.')
        except XLRDError:
            raise ValidationError(
                'Não foi possível processar a planilha. Verfique se o formato do arquivo é .xlsx, sem cabeçalho e se contém as seguintes colunas: Descrição, Núcleo, Carga Horária - Relógio, Carga Horária - Aula, Qtd. de Créditos, Tipo do Componente e Nível de Ensino.'
            )

        return self.cleaned_data

    def processar(self):
        for componente in self.componentes:
            Componente.objects.get_or_create(**componente)


class ImportarComponentesMatrizForm(forms.FormPlus):
    tipo_componente = forms.ModelChoiceField(TipoComponente.objects, required=True, label='Tipo dos Componentes')
    planilha = forms.FileFieldPlus(
        filetypes=['xlsx', ],
        required=True,
    )

    def __init__(self, matriz, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matriz = matriz
        self.componentes_curriculares = []

    def clean(self):
        try:
            planilha = self.cleaned_data['planilha'].file
            workbook = xlrd.open_workbook(file_contents=planilha.read())
            sheet = workbook.sheet_by_index(0)

            nivel_ensino = self.matriz.nivel_ensino
            tipo_componente = self.cleaned_data['tipo_componente']
            componentes_duplicados = []

            for i in range(0, sheet.nrows):
                try:
                    periodo_letivo = int(sheet.cell_value(i, 0))
                    descricao = str(sheet.cell_value(i, 1))
                    observacao = str(sheet.cell_value(i, 2))
                    carga_horaria_relogio = int(sheet.cell_value(i, 3))
                    carga_horaria_aula = int(sheet.cell_value(i, 4))
                    qtd_creditos = int(sheet.cell_value(i, 5))
                    optativo = int(sheet.cell_value(i, 6))
                    nucleo = str(sheet.cell_value(i, 7))
                    qtd_avaliacoes = int(sheet.cell_value(i, 8))
                    tipo_componente_curricular_descricao = str(sheet.cell_value(i, 9))
                    avaliacao_por_conceito = int(sheet.cell_value(i, 10))
                    carga_horaria_pratica = int(sheet.cell_value(i, 11))
                    abreviatura = str(sheet.cell_value(i, 12))
                    try:
                        sigla_qacademico = str(sheet.cell_value(i, 13))
                    except Exception:
                        sigla_qacademico = None
                    ch_presencial = carga_horaria_relogio - carga_horaria_pratica

                    # validando periodo_letivo
                    if periodo_letivo < 1 and not optativo:
                        raise ValidationError(f'Componente ({descricao}) obrigatório com período letivo menor que 1.')
                    if periodo_letivo != 0 and optativo:
                        raise ValidationError(f'Componente ({descricao}) optativo com período letivo diferente de 0.')
                    if periodo_letivo > self.matriz.qtd_periodos_letivos:
                        raise ValidationError(f'Componente ({descricao}) com período letivo maior que a quantidade de periodos letivos cadastrado na matriz.')

                    # validando descricao
                    if not descricao:
                        raise ValidationError('Componente sem descrição.')

                    # validando carga_horaria_relogio
                    if carga_horaria_relogio < 0:
                        raise ValidationError(f'Componente({descricao}) com Carga Horária - Relógio menor que 0.')

                    # validando carga_horaria_aula
                    if carga_horaria_aula < 0:
                        raise ValidationError(f'Componente({descricao}) com Carga Horária - Aula menor que 0.')

                    # validando qtd_creditos
                    if qtd_creditos < 0:
                        raise ValidationError(f'Componente({descricao}) com quantiade de créditos menor que 0.')

                    # validando carga_horaria_relogio e carga_horaria_aula e qtd_creditos
                    if carga_horaria_relogio > 0 and carga_horaria_aula < 1:
                        raise ValidationError(f'Componente({descricao}) com Carga Horária - Relógio informada sem Carga Horária - Aula.')
                    if carga_horaria_aula > 0 and carga_horaria_relogio < 1:
                        raise ValidationError(f'Componente({descricao}) com Carga Horária - Aula informada sem Carga Horária - Relógio.')

                    # validando optativo
                    if optativo not in [0, 1]:
                        raise ValidationError(f'Componente({descricao}) com coluna Optativo diferente de 0 ou 1.')

                    # validando qtd de avaliações
                    if not (0 <= qtd_avaliacoes < 5):
                        raise ValidationError(f'A quantidade de avaliações do componente({descricao}) esta incorreta.')

                    # validando avaliacao_por_conceito
                    if avaliacao_por_conceito not in [0, 1]:
                        raise ValidationError(f'Componente({descricao}) com coluna Avaliação por Conceito diferente de 0 ou 1.')

                    # validando carga_horaria_pratica
                    if carga_horaria_pratica < 0:
                        raise ValidationError(f'Componente({descricao}) com Carga Horária Prática menor que 0.')

                    # validando ch_presencial
                    if ch_presencial < 0:
                        raise ValidationError(f'Componente({descricao}) com Carga Horária Prática maior que a Carga Horária - Relógio.')

                    # validando tipo de componente curricular
                    tipo_componente_curricular = None
                    for tpc in ComponenteCurricular.TIPO_CHOICES:
                        if tpc[1] == tipo_componente_curricular_descricao:
                            tipo_componente_curricular = tpc[0]

                    if not tipo_componente_curricular:
                        raise ValidationError(f'O Tipo do Componente Curricular "{tipo_componente_curricular_descricao}" não foi encontrado.')

                    # recuperando componente único
                    chaves = dict(
                        descricao=descricao,
                        ch_hora_relogio=carga_horaria_relogio,
                        ch_hora_aula=carga_horaria_aula,
                        nivel_ensino=NivelEnsino.objects.get(descricao=nivel_ensino),
                        observacao=observacao,
                    )
                    qs_componente = Componente.objects.filter(**chaves)
                    componente = None
                    if not qs_componente.exists():
                        # criando novo componente caso não exista
                        chaves2 = dict(
                            descricao_historico=descricao,
                            ch_qtd_creditos=qtd_creditos,
                            tipo=TipoComponente.objects.get(descricao=tipo_componente),
                            diretoria=Diretoria.objects.get(setor__sigla=utils.get_sigla_reitoria()),
                            abreviatura=abreviatura
                        )
                        chaves.update(chaves2)
                        if sigla_qacademico is not None:
                            chaves.update(sigla_qacademico=sigla_qacademico)
                        componente = Componente.objects.get_or_create(**chaves)[0]
                    elif qs_componente.count() == 1:
                        componente = qs_componente[0]
                        if componente.tipo != tipo_componente:
                            raise ValidationError(f'O Componente Curricular encontrado "{componente}" é de um tipo diferente do informado na importação ({tipo_componente.descricao}).')
                    else:
                        componentes_duplicados.append(descricao)

                    if componente and not componentes_duplicados:
                        if sigla_qacademico is not None:
                            componente.sigla_qacademico = sigla_qacademico
                        componente.save()

                        # vinculando o componente a matriz
                        componente_curricular = dict(
                            matriz=self.matriz,
                            componente=componente,
                            optativo=optativo,
                            periodo_letivo=periodo_letivo > 0 and periodo_letivo or None,
                            tipo=tipo_componente_curricular,
                            qtd_avaliacoes=qtd_avaliacoes,
                            nucleo=Nucleo.objects.get(descricao=nucleo),
                            avaliacao_por_conceito=avaliacao_por_conceito,
                            ch_presencial=ch_presencial,
                            ch_pratica=carga_horaria_pratica,
                        )

                        qs_componente_curricular = ComponenteCurricular.objects.filter(componente=componente, matriz=self.matriz)
                        if not qs_componente_curricular.exists():
                            self.componentes_curriculares.append(componente_curricular)

                except ValueError:
                    raise ValidationError('Alguma coluna da planilha possui o valor incorreto.')
                except TipoComponente.DoesNotExist:
                    raise ValidationError(f'O Tipo do Componente "{tipo_componente}" não foi encontrado.')
                except NivelEnsino.DoesNotExist:
                    raise ValidationError(f'O Nível de Ensino "{nivel_ensino}" não foi encontrado.')
                except Nucleo.DoesNotExist:
                    raise ValidationError(f'O Núcleo "{nucleo}" não foi encontrado.')
            if componentes_duplicados:
                raise ValidationError(f'Existe mais de um cadastro de componente para os seguintes dados informados na planilha: {componentes_duplicados}.')
        except Exception as e:
            raise ValidationError(e)

        return self.cleaned_data

    def processar(self):
        for componente_curricular in self.componentes_curriculares:
            ComponenteCurricular.objects.get_or_create(**componente_curricular)


class DefinirCoordenadoresEstagioDocente(forms.ModelFormPlus):
    coordenadores_estagio_docente = forms.MultipleModelChoiceFieldPlus(
        Professor.objects, label='Coordenadores de Estágio Docente', required=True
    )

    class Meta:
        model = CursoCampus
        fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['coordenadores_estagio_docente'] = [professor.pk for professor in self.instance.coordenadores_estagio_docente.all()]

    @transaction.atomic
    def save(self, *args, **kwargs):
        for professor in self.instance.coordenadores_estagio_docente.all():
            user = User.objects.filter(username=professor.vinculo.user.username)[0]
            if professor.cursos_coordenacao_estagio_docente_set.all().count() == 1:
                UsuarioGrupo.objects.filter(group=grupos()['COORDENADOR_ESTAGIO_DOCENTE'], user=user).delete()
        self.instance.coordenadores_estagio_docente.clear()
        for professor in self.cleaned_data['coordenadores_estagio_docente'].all():
            user = User.objects.filter(username=professor.vinculo.user.username)[0]
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR_ESTAGIO_DOCENTE'], user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=self.instance.diretoria.setor)
            self.instance.coordenadores_estagio_docente.add(professor)
        self.instance.save()

        return super().save(*args, **kwargs)


class EditarDiretoriaCurso(forms.ModelFormPlus):
    class Meta:
        model = CursoCampus
        fields = ('diretoria',)


class TransferirPoloAlunoForm(FormWizardPlus):
    TRANSFERIR_POR_TURMA = 'TURMA'
    TRANSFERIR_POR_CURSO = 'CURSO'
    TIPO_TRANSFERENCIA_CHOICES = [[TRANSFERIR_POR_TURMA, 'Por Turma'], [TRANSFERIR_POR_CURSO, 'Por Curso']]

    tipo = forms.ChoiceField(label='Filtrar Alunos', choices=TIPO_TRANSFERENCIA_CHOICES, widget=forms.RadioSelect())
    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Turma', required=False)
    curso = forms.ModelChoiceFieldPlus(CursoCampus.objects, label='Curso', required=False, widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS))
    polo = forms.ModelChoiceFieldPlus(Polo.objects, label='Polo')
    alunos = forms.MultipleModelChoiceField(Aluno.objects, label='', widget=RenderableSelectMultiple('widgets/alunos_widget.html'))

    steps = ([('Filtro', {'fields': ('tipo', 'turma', 'curso')})], [('Polo de Destino', {'fields': ('polo',)}), ('Seleção dos Alunos', {'fields': ('alunos',)})])

    class Media:
        js = ('/static/edu/js/ImprimirHistoricoFinalEmLoteForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def first_step(self):
        self.fields['turma'].queryset = Turma.objects.filter(matriculaperiodo__aluno__curso_campus__diretoria__ead=True).distinct()
        self.fields['curso'].queryset = CursoCampus.objects.filter(diretoria__ead=True)

    def next_step(self):
        curso = self.get_entered_data('curso')
        turma = self.get_entered_data('turma')

        if 'alunos' in self.fields:
            qs = self.fields['alunos'].queryset

            if curso:
                qs = qs.filter(curso_campus=curso)
            if turma:
                qs = qs.filter(matriculaperiodo__turma=turma)

            self.fields['alunos'].queryset = qs

    def clean_turma(self):
        if self.cleaned_data.get('tipo') == self.TRANSFERIR_POR_TURMA and not self.cleaned_data.get('turma'):
            raise ValidationError('Informe a turma dos alunos.')
        return self.cleaned_data['turma']

    def clean_curso(self):
        if self.cleaned_data.get('tipo') == self.TRANSFERIR_POR_CURSO and not self.cleaned_data.get('curso'):
            raise ValidationError('Informe o curso dos alunos.')
        return self.cleaned_data['curso']

    def processar(self):
        polo = self.cleaned_data['polo']
        alunos = self.cleaned_data['alunos']

        for aluno in alunos:
            aluno.polo = polo
            aluno.save()


class AlterarMatrizAlunoForm(forms.ModelFormPlus):
    matriz = forms.ModelChoiceField(Matriz.objects, label='Nova Matriz')

    class Meta:
        model = Aluno
        fields = ['matriz']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['matriz'].queryset = (
            self.fields['matriz'].queryset.filter(matrizcurso__curso_campus=self.instance.curso_campus).exclude(matrizcurso__matriz=self.instance.matriz)
        )


class AproveitamentoComponenteForm(forms.ModelFormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', help_text='Ano letivo no qual a equivalência da disciplina está sendo registrada')
    periodo_letivo = forms.ChoiceField(
        label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES, help_text='Período letivo no qual a equivalência da disciplina está sendo registrada'
    )
    matriculas_diario_resumidas = forms.MultipleModelChoiceField(
        MatriculaDiarioResumida.objects.all(), required=False, label='', widget=RenderableSelectMultiple('widgets/matricula_diario_resumida_widget.html')
    )
    matriculas_diario = forms.MultipleModelChoiceField(
        MatriculaDiario.objects.all(), required=False, label='', widget=RenderableSelectMultiple('widgets/matricula_diario_widget.html')
    )
    registros_historico = forms.MultipleModelChoiceField(
        RegistroHistorico.objects.all(), required=False, label='', widget=RenderableSelectMultiple('widgets/registro_historico_widget.html')
    )

    class Meta:
        model = AproveitamentoComponente
        fields = ['matriculas_diario_resumidas', 'matriculas_diario', 'registros_historico']

    fieldsets = (
        ('Período Letivo', {'fields': ('ano_letivo', 'periodo_letivo')}),
        ('Componentes Cursados no Q-Acadêmico', {'fields': (('matriculas_diario_resumidas'),)}),
        ('Componentes Cursados no Suap', {'fields': (('matriculas_diario'),)}),
        ('Outros Componentes', {'fields': (('registros_historico'),)}),
    )

    def __init__(self, aluno, componente_curricular, *args, **kwargs):
        self.aluno = aluno
        self.componente_curricular = componente_curricular
        super().__init__(*args, **kwargs)
        self.fields['ano_letivo'].queryset = Ano.objects.filter(id__in=self.aluno.matriculaperiodo_set.values_list('ano_letivo_id', flat=True))
        qs_componentes = aluno.matriz.componentecurricular_set.select_related('componente').all()
        self.fields['matriculas_diario_resumidas'].queryset = MatriculaDiarioResumida.objects.filter(
            matricula_periodo__aluno=aluno,
            situacao__in=[MatriculaDiario.SITUACAO_APROVADO, MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO, MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO],
        ).exclude(equivalencia_componente__componente__id__in=qs_componentes.values_list('componente__id', flat=True))
        self.fields['matriculas_diario'].queryset = MatriculaDiario.objects.filter(matricula_periodo__aluno=aluno, situacao__in=[MatriculaDiario.SITUACAO_APROVADO]).exclude(
            diario__componente_curricular__componente__id__in=qs_componentes.values_list('componente__id', flat=True)
        )
        self.fields['registros_historico'].queryset = RegistroHistorico.objects.filter(
            matricula_periodo__aluno=aluno,
            situacao__in=[MatriculaDiario.SITUACAO_APROVADO, MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO, MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO],
        ).exclude(componente__id__in=qs_componentes.values_list('componente__id', flat=True))
        if self.instance.pk:
            self.fields['ano_letivo'].initial = self.instance.matricula_periodo.ano_letivo.pk
            self.fields['periodo_letivo'].initial = self.instance.matricula_periodo.periodo_letivo

    def clean(self):
        if 'ano_letivo' not in self.cleaned_data or 'periodo_letivo' not in self.cleaned_data:
            return self.cleaned_data

        if PedidoMatriculaDiario.objects.filter(
            pedido_matricula__matricula_periodo__aluno=self.aluno, data_processamento__isnull=True, diario__componente_curricular=self.componente_curricular
        ).exists():
            raise forms.ValidationError('O aluno solicitou matrícula nessa disciplina. Aguarde o processamento do pedido de matrícula para realizar esse procedimeto.')

        if not self.get_matricula_periodo_queryset().exists():
            raise forms.ValidationError('O aluno não está matriculado no ano/período informado.')

        if not self.cleaned_data['matriculas_diario_resumidas'] and not self.cleaned_data['matriculas_diario'] and not self.cleaned_data['registros_historico']:
            raise forms.ValidationError('Selecione ao menos um componente')
        return self.cleaned_data

    def get_matricula_periodo_queryset(self):
        return self.aluno.matriculaperiodo_set.filter(ano_letivo=self.cleaned_data['ano_letivo'], periodo_letivo=self.cleaned_data['periodo_letivo'])

    def save(self, *args, **kwargs):
        self.instance.matricula_periodo = self.get_matricula_periodo_queryset()[0]
        self.instance.componente_curricular = self.componente_curricular
        super().save(*args, **kwargs)


class ConvocacaoENADEForm(forms.ModelForm):
    class Meta:
        model = ConvocacaoENADE
        fields = (
            'ano_letivo',
            'portaria',
            'edital',
            'data_prova',
            'cursos',
            'percentual_minimo_ingressantes',
            'percentual_maximo_ingressantes',
            'percentual_minimo_concluintes',
            'percentual_maximo_concluintes',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cursos'].queryset = CursoCampus.locals.filter(exige_enade=True, ativo=True)
        if not self.instance.pk:
            self.fields['data_prova'].widget = forms.HiddenInput()

    def clean_cursos(self):
        qs = ConvocacaoENADE.objects.filter(ano_letivo=self.cleaned_data['ano_letivo']).values_list('cursos', flat=True).distinct()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        for curso in self.cleaned_data['cursos']:
            if curso.pk in qs:
                raise forms.ValidationError('O curso {} já foi adicionado em outra convocação do ano letivo {}.'.format(curso, self.cleaned_data['ano_letivo']))
        return self.cleaned_data['cursos']


class AtualizarListaConvocadosENADEForm(forms.Form):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Atualizar Lista de Convocados'

    curso_campus = forms.ModelChoiceField(
        CursoCampus.locals,
        required=False,
        label='Curso',
        empty_label='-----------',
        help_text='Não selecione o curso caso deseje atualizar a lista para todos os cursos cadastrados.',
    )

    def __init__(self, convocao_enade, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.convocao_enade = convocao_enade
        self.fields['curso_campus'].queryset = convocao_enade.cursos.all()

    def processar(self, request):
        curso_campus = self.cleaned_data.get('curso_campus')
        situacao_ids = (SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL, SituacaoMatricula.TRANCADO)
        if curso_campus:
            qs = Aluno.com_matriz.filter(matriculaperiodo__ano_letivo=self.convocao_enade.ano_letivo, curso_campus=curso_campus, situacao__pk__in=situacao_ids)
        else:
            qs = Aluno.com_matriz.filter(
                matriculaperiodo__ano_letivo=self.convocao_enade.ano_letivo,
                curso_campus__in=self.convocao_enade.cursos.all().values_list('pk', flat=True),
                situacao__pk__in=situacao_ids,
            )

        return tasks.atulizar_lista_convocacao_enade(qs.distinct(), self.convocao_enade)


class LancarSituacaoAlunoENADEForm(forms.ModelForm):
    justificativa_dispensa = forms.ModelChoiceField(queryset=JustificativaDispensaENADE.objects.filter(ativo=True), label='Justificativa de Dispensa', required=False)

    class Meta:
        model = RegistroConvocacaoENADE
        fields = ('situacao', 'justificativa_dispensa')

    class Media:
        js = ('/static/edu/js/LancarSituacaoAlunoENADEForm.js',)

    def clean_justificativa_dispensa(self):
        if self.cleaned_data.get('situacao') == RegistroConvocacaoENADE.SITUACAO_DISPENSADO:
            if not self.cleaned_data.get('justificativa_dispensa'):
                raise forms.ValidationError('O campo Justificativa de Dispensa é obrigatório.')
        elif self.cleaned_data.get('justificativa_dispensa'):
            raise forms.ValidationError('O campo Justificativa de Dispensa deve ser preenchido apenas quando a Situação for Dispensado.')
        return self.cleaned_data.get('justificativa_dispensa')

    def clean(self):
        if self.instance.convocacao_enade and not self.instance.convocacao_enade.data_prova and self.cleaned_data.get('situacao') != RegistroConvocacaoENADE.SITUACAO_DISPENSADO:
            raise forms.ValidationError('Você precisa definir a data de realização da prova na convocação do ENADE.')
        if not self.instance.convocacao_enade and self.cleaned_data.get('situacao') != RegistroConvocacaoENADE.SITUACAO_DISPENSADO:
            raise forms.ValidationError('A situação do aluno no ENADE deve ser "Dispensado"')
        if (
            self.instance.convocacao_enade
            and not self.instance.convocacao_enade.cursos.filter(pk=self.instance.aluno.curso_campus.pk).exists()
            and self.cleaned_data.get('situacao') != RegistroConvocacaoENADE.SITUACAO_DISPENSADO
        ):
            raise forms.ValidationError('A situação do aluno no ENADE deve ser "Dispensado"')
        return self.cleaned_data


class LancarSituacaoAlunoEmLoteENADEForm(forms.Form):
    situacao = forms.ChoiceField(choices=RegistroConvocacaoENADE.SITUACAO_CHOICES, label='Situação')
    justificativa_dispensa = forms.ModelChoiceField(queryset=JustificativaDispensaENADE.objects.filter(ativo=True), label='Justificativa de Dispensa', required=False)

    def __init__(self, registros_convocacoes_enade, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registros_convocacoes_enade = registros_convocacoes_enade
        self.convocacao_enade = self.registros_convocacoes_enade[0].convocacao_enade

    def clean_justificativa_dispensa(self):
        if self.cleaned_data.get('situacao') == RegistroConvocacaoENADE.SITUACAO_DISPENSADO:
            if not self.cleaned_data.get('justificativa_dispensa'):
                raise forms.ValidationError('O campo Justificativa de Dispensa é obrigatório.')

        return self.cleaned_data.get('justificativa_dispensa')

    def clean(self):
        if not self.convocacao_enade.data_prova:
            raise forms.ValidationError('Você precisa definir a data de realização da prova na convocação do ENADE.')
        return self.cleaned_data

    def processar(self):
        for registro_convocacao_enade in self.registros_convocacoes_enade:
            registro_convocacao_enade.situacao = self.cleaned_data.get('situacao')
            registro_convocacao_enade.justificativa_dispensa = self.cleaned_data.get('justificativa_dispensa')
            registro_convocacao_enade.save()

    class Media:
        js = ('/static/edu/js/LancarSituacaoAlunoENADEForm.js',)


class AdicionarAlunosColacaoGrauForm(FormWizardPlus):
    METHOD = 'GET'

    ano_letivo_aluno = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=True)
    periodo_letivo_aluno = forms.ChoiceField(label='Período Letivo', choices=[[None, '----']] + Aluno.PERIODO_LETIVO_CHOICES, required=True)
    cursos_campus = forms.MultipleModelChoiceFieldPlus(CursoCampus.locals, label='Curso', required=False)
    turma = forms.ModelChoiceFieldPlus(Turma.objects, required=False, label='Turma')
    aluno = forms.ModelChoiceFieldPlus(Aluno.locals, label='Aluno', required=False)

    alunos = forms.MultipleModelChoiceField(Aluno.locals.none(), label='', widget=RenderableSelectMultiple('widgets/alunos_widget.html'), required=True)

    steps = (
        [('Ano/Período Letivo', {'fields': ('ano_letivo_aluno', 'periodo_letivo_aluno')})],
        [('Filtros', {'fields': ('cursos_campus', 'turma', 'aluno')})],
        [('Escolha os alunos', {'fields': ('alunos',)})],
    )

    def __init__(self, request, colacao_grau, *args, **kwargs):
        self.request = request
        self.colacao_grau = colacao_grau
        super().__init__(*args, **kwargs)

    def clean(self):
        cursos_campus = self.cleaned_data.get('cursos_campus')
        turma = self.cleaned_data.get('turma')
        aluno = self.cleaned_data.get('aluno')
        if 'cursos_campus' in self.fields and not cursos_campus and not turma and not aluno:
            raise forms.ValidationError('Escolha pelo menos um curso, ou turma ou aluno.')
        return self.cleaned_data

    def clean_aluno(self):
        ano_letivo_aluno = self.get_entered_data('ano_letivo_aluno')
        periodo_letivo_aluno = self.get_entered_data('periodo_letivo_aluno')
        aluno = self.cleaned_data.get('aluno')
        if aluno and not aluno.pode_realizar_colacao_grau(ano_letivo_aluno, periodo_letivo_aluno):
            raise forms.ValidationError(
                mark_safe(
                    'Aluno escolhido ainda não pode colar grau. <a href="/edu/aluno/{}/?tab=requisitos">Reveja os requisitos</a>'.format(self.cleaned_data['aluno'].matricula)
                )
            )
        return self.cleaned_data['aluno']

    def next_step(self):
        ano_letivo_aluno = self.get_entered_data('ano_letivo_aluno')
        periodo_letivo_aluno = self.get_entered_data('periodo_letivo_aluno')
        cursos_campus = self.request.GET.getlist('cursos_campus')
        turma = self.get_entered_data('turma')
        aluno = self.get_entered_data('aluno')

        qs_alunos = (
            Aluno.objects.filter(
                curso_campus__ativo=True,
                curso_campus__exige_colacao_grau=True,
                situacao__in=[SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL],
                matriz__isnull=False,
                participacaocolacaograu__isnull=True,
                curso_campus__diretoria=self.colacao_grau.diretoria,
                pendencia_colacao_grau=True
            )
            .exclude(pendencia_tcc=True)
            .exclude(pendencia_enade=True)
            .exclude(pendencia_ch_atividade_complementar=True)
            .exclude(pendencia_ch_tcc=True, pendencia_ch_pratica_profissional=True)
            .exclude(pendencia_ch_seminario=True)
            .exclude(pendencia_ch_eletiva=True)
            .exclude(pendencia_ch_optativa=True)
            .exclude(pendencia_ch_obrigatoria=True)
            .exclude(pendencia_pratica_profissional=True)
            .exclude(curso_campus__modalidade=Modalidade.FIC)
        )
        if 'cursos_campus' in self.fields:
            self.fields['cursos_campus'].queryset = CursoCampus.locals.filter(ativo=True, exige_colacao_grau=True, diretoria=self.colacao_grau.diretoria)
            self.fields['turma'].queryset = Turma.locals.filter(
                curso_campus__ativo=True, curso_campus__exige_colacao_grau=True, matriculaperiodo__isnull=False, curso_campus__diretoria=self.colacao_grau.diretoria
            ).distinct()
            self.fields['aluno'].queryset = qs_alunos
        if (cursos_campus or turma or aluno) and 'alunos' in self.fields:
            if cursos_campus:
                qs_alunos = qs_alunos.filter(curso_campus__in=cursos_campus)
            if turma:
                qs_alunos = qs_alunos.filter(matriculaperiodo__in=turma.get_alunos_matriculados())
            if aluno:
                qs_alunos = qs_alunos.filter(id=aluno.id)
            if ano_letivo_aluno:
                qs_alunos = qs_alunos.filter(matriculaperiodo__ano_letivo=ano_letivo_aluno)
            if periodo_letivo_aluno:
                qs_alunos = qs_alunos.filter(matriculaperiodo__periodo_letivo=periodo_letivo_aluno)
                qs_mps = MatriculaPeriodo.objects.filter(
                    aluno__in=qs_alunos.values('id'),
                    ano_letivo__ano__lte=ano_letivo_aluno.ano,
                    situacao_id__in=[SituacaoMatriculaPeriodo.MATRICULADO, SituacaoMatriculaPeriodo.EM_ABERTO],
                )
                if periodo_letivo_aluno == 1:
                    qs_mps = qs_mps.exclude(ano_letivo__ano=ano_letivo_aluno.ano, periodo_letivo=2)
                ids_alunos_matriculas_abertas = set(qs_mps.values_list('aluno_id', flat=True))
                qs_alunos = qs_alunos.exclude(id__in=ids_alunos_matriculas_abertas)

            qs_alunos = qs_alunos.distinct()
            for aluno in qs_alunos:
                aluno.atualizar_situacao('Reprocessamento do Histórico')
            self.fields['alunos'].queryset = qs_alunos

    def processar(self):
        alunos = self.cleaned_data.get('alunos')

        for aluno in alunos:
            qs = ParticipacaoColacaoGrau.objects.filter(aluno=aluno, colacao_grau=self.colacao_grau)
            if qs.exists():
                qs[0].save()
            else:
                participacao_colacao_grau = ParticipacaoColacaoGrau()
                participacao_colacao_grau.aluno = aluno
                participacao_colacao_grau.colacao_grau = self.colacao_grau
                participacao_colacao_grau.save()


class ColacaoGrauForm(forms.ModelForm):
    diretoria = forms.ModelChoiceField(queryset=Diretoria.objects.none())

    class Meta:
        model = ColacaoGrau
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals


class DeferirColacaoGrauForm(forms.FormPlus):
    laureados = forms.MultipleModelChoiceFieldPlus(ParticipacaoColacaoGrau.objects, label='Laureados', required=False)

    def __init__(self, colacao_grau, *args, **kwargs):
        self.colacao_grau = colacao_grau
        super().__init__(*args, **kwargs)
        self.fields['laureados'].queryset = colacao_grau.participacaocolacaograu_set.all()
        self.fields['laureados'].initial = list(colacao_grau.participacaocolacaograu_set.filter(laureado=True).values_list('pk', flat=True))

    def processar(self):
        self.colacao_grau.deferida = True
        self.colacao_grau.participacaocolacaograu_set.update(laureado=False)
        for participacao in self.cleaned_data['laureados']:
            participacao.laureado = True
            participacao.save()
        self.colacao_grau.save()


class EditarMatriculaDiarioResumidaForm(forms.ModelForm):
    media_final_disciplina = forms.IntegerField(label='Média Final')
    frequencia = forms.IntegerField(label='Frequência')
    titularidade_professor = forms.ChoiceField(label='Titulação', choices=[['', '-----']] + Professor.TITULACAO_CHOICES, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.matricula_periodo.aluno.situacao.ativo:
            del self.fields['media_final_disciplina']
            del self.fields['frequencia']

    def save(self, *args, **kwargs):
        if self.instance.matricula_periodo.aluno.situacao.ativo:
            media_final_disciplina = self.cleaned_data.get('media_final_disciplina')
            frequencia = self.cleaned_data.get('frequencia')
            estrutura_curso = self.instance.matricula_periodo.aluno.matriz.estrutura

            if estrutura_curso.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
                # Avaliação por Nota
                if media_final_disciplina < estrutura_curso.media_aprovacao_sem_prova_final:
                    self.instance.situacao = MatriculaDiario.SITUACAO_REPROVADO
                else:
                    self.instance.situacao = MatriculaDiario.SITUACAO_APROVADO
            else:
                # Avaliação por Frequência
                if frequencia < estrutura_curso.percentual_frequencia:
                    self.instance.situacao = MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA
                else:
                    self.instance.situacao = MatriculaDiario.SITUACAO_APROVADO

        if self.instance.codigo_professor and self.instance.codigo_diario_pauta:
            MatriculaDiarioResumida.objects.filter(codigo_professor=self.instance.codigo_professor, codigo_diario_pauta=self.instance.codigo_diario_pauta).update(
                titularidade_professor=self.instance.titularidade_professor, nome_professor=self.instance.nome_professor
            )

        super().save(*args, **kwargs)

    class Meta:
        model = MatriculaDiarioResumida
        fields = ('frequencia', 'media_final_disciplina', 'nome_professor', 'titularidade_professor')


class EventoForm(forms.ModelFormPlus):
    modelo_certificado_participacao = forms.FileFieldPlus(
        filetypes=['docx'],
        label='Modelo do Certificado de Participação',
        check_mimetype=False,
        help_text='O arquivo de modelo deve ser uma arquivo .docx contendo as marcações #PARTICIPANTE#, #CPF#, #CAMPUS#, #CIDADE#, #UF#, #DATA#, #CODIGOVERIFICADOR#.',
    )
    uo = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus')

    class Meta:
        model = Evento
        exclude = ('participantes', 'modelo_certificado_palestrante', 'modelo_certificado_convidado')


class OcorrenciaDiarioForm(forms.ModelFormPlus):
    class Meta:
        model = OcorrenciaDiario
        exclude = ('professor_diario',)


class ModeloCertificadoEventoForm(forms.FormPlus):
    modelo = forms.FileFieldPlus(
        filetypes=['docx'],
        label='Modelo do Certificado',
        check_mimetype=False,
        required=False,
        help_text='O arquivo de modelo deve ser uma arquivo .docx contendo as marcações #PARTICIPANTE#, #CPF#, #CAMPUS#, #CIDADE#, #UF#, #DATA#, #CODIGOVERIFICADOR#.',
    )

    def __init__(self, evento, *args, **kwargs):
        self.tipo = kwargs.pop('tipo', ParticipanteEvento.PARTICIPANTE)
        super().__init__(*args, **kwargs)
        self.evento = evento
        if self.tipo == ParticipanteEvento.PARTICIPANTE:
            self.initial['modelo'] = self.evento.modelo_certificado_participacao
            self.fields['modelo'].required = True
        elif self.tipo == ParticipanteEvento.PALESTRANTE:
            self.initial['modelo'] = self.evento.modelo_certificado_palestrante
        elif self.tipo == ParticipanteEvento.CONVIDADO:
            self.initial['modelo'] = self.evento.modelo_certificado_convidado

    def clean_modelo(self):
        if self.cleaned_data.get('modelo') is False:
            return None
        return self.cleaned_data.get('modelo')

    def processar(self):
        if self.tipo == ParticipanteEvento.PARTICIPANTE:
            self.evento.modelo_certificado_participacao = self.cleaned_data['modelo']
        elif self.tipo == ParticipanteEvento.PALESTRANTE:
            self.evento.modelo_certificado_palestrante = self.cleaned_data['modelo']
        elif self.tipo == ParticipanteEvento.CONVIDADO:
            self.evento.modelo_certificado_convidado = self.cleaned_data['modelo']
        self.evento.save()


class AdicionarParticipanteEventoForm(forms.FormPlus):
    cpf = forms.BrCpfField()
    nome = forms.CharFieldPlus()
    email = forms.EmailField()

    def __init__(self, evento, *args, **kwargs):
        self.tipo = kwargs.pop('tipo', ParticipanteEvento.PARTICIPANTE)
        super().__init__(*args, **kwargs)
        self.evento = evento

    def clean_cpf(self):
        qs = self.evento.participanteevento_set.filter(evento=self.evento, participante__cpf=self.cleaned_data.get('cpf'), tipo_participacao=self.tipo)
        if qs.exists():
            raise forms.ValidationError(f'Já existe um {self.tipo} com o CPF informado.')
        return self.cleaned_data.get('cpf')

    @transaction.atomic
    def processar(self):
        pessoa_fisica = PessoaFisica.objects.filter(cpf=self.cleaned_data['cpf']).order_by('-eh_servidor', '-eh_aluno', '-eh_prestador')
        if not pessoa_fisica.exists():
            pessoa_fisica = PessoaFisica()
            pessoa_fisica.cpf = self.cleaned_data['cpf']
            pessoa_fisica.nome_registro = self.cleaned_data['nome']
            pessoa_fisica.email = self.cleaned_data['email']
            pessoa_fisica.save()
        else:
            pessoa_fisica = pessoa_fisica[0]
            if not pessoa_fisica.eh_aluno and not pessoa_fisica.eh_servidor and not pessoa_fisica.eh_prestador:
                pessoa_fisica.email = self.cleaned_data['email']
                pessoa_fisica.nome_registro = self.cleaned_data['nome']
                pessoa_fisica.save()

        participante_evento = ParticipanteEvento()
        participante_evento.participante = pessoa_fisica
        participante_evento.evento = self.evento
        participante_evento.tipo_participacao = self.tipo
        participante_evento.save()
        self.evento.participanteevento_set.add(participante_evento)
        self.evento.save()


class EditarParticipanteEventoForm(forms.ModelFormPlus):
    email = forms.EmailField()
    cpf = forms.CharFieldPlus(label='CPF', required=False, widget=forms.TextInput(attrs=dict(readonly='readonly')))
    nome_registro = forms.CharFieldPlus(label='Nome')

    class Meta:
        model = PessoaFisica
        fields = ('cpf', 'nome_registro', 'email')

    def clean(self):
        if self.instance.eh_aluno or self.instance.eh_servidor or self.instance.eh_prestador:
            raise ValidationError('Não é possível editar o nome e email de um servidor, prestador de serviço ou aluno.')
        else:
            return self.cleaned_data


class AlterarVinculoParticipanteEventoForm(forms.ModelFormPlus):
    class Meta:
        model = ParticipanteEvento
        fields = ('participante',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['participante'].queryset = PessoaFisica.objects.filter(cpf=self.instance.participante.cpf).exclude(pk=self.instance.participante.pk).order_by('user__username')
        self.initial['participante'] = self.instance.participante


class ImportarParticipantesEventoForm(forms.FormPlus):
    planilha = forms.FileFieldPlus(help_text='O arquivo deve ser no formato "xlsx", sem cabeçalho, contendo as seguintes colunas: CPF, Nome e E-mail.')

    def __init__(self, evento, *args, **kwargs):
        self.tipo = kwargs.pop('tipo', ParticipanteEvento.PARTICIPANTE)
        super().__init__(*args, **kwargs)
        self.evento = evento
        self.participantes = []

    def clean(self):
        arquivo = self.cleaned_data.get('planilha')
        if arquivo:
            try:
                planilha = arquivo.file
                workbook = xlrd.open_workbook(file_contents=planilha.read())
                sheet = workbook.sheet_by_index(0)
                cpfs_invalidos = []
                for i in range(0, sheet.nrows):
                    nome = str(sheet.cell_value(i, 1))
                    try:
                        cpf = str(sheet.cell_value(i, 0))
                        cpf_field = BrCpfField()
                        cpf = cpf_field.clean(cpf)
                    except ValidationError:
                        cpfs_invalidos.append(f'{nome}({cpf})')
                        continue

                    email = str(sheet.cell_value(i, 2))
                    participante = dict(cpf=cpf, nome=nome, email=email)

                    qs = self.evento.participanteevento_set.filter(evento=self.evento, participante__cpf=cpf)
                    if not qs.exists():
                        self.participantes.append(participante)
            except Exception:
                raise ValidationError(
                    'Não foi possível processar a planilha. Verfique se o formato do arquivo é .xlsx, sem cabeçalho e se contém as seguintes colunas: CPF, Nome e E-mail.'
                )
            if cpfs_invalidos:
                raise ValidationError('A planilha contém os participantes com CPF inválido: {}. Faça a correção antes de importar a planilha.'.format(', '.join(cpfs_invalidos)))

        return self.cleaned_data

    @transaction.atomic
    def processar(self):

        for participante in self.participantes:
            pessoa_fisica = PessoaFisica.objects.filter(cpf=participante['cpf'], email__isnull=False).order_by('-eh_servidor', '-eh_aluno', '-eh_prestador')
            if not pessoa_fisica.exists():
                pessoa_fisica = PessoaFisica()

                cpf_field = BrCpfField()
                try:
                    pessoa_fisica.cpf = cpf_field.clean(participante['cpf'])
                except ValidationError:
                    pessoa_fisica.cpf = "-"

                pessoa_fisica.nome_registro = participante['nome']
                if participante['email']:
                    pessoa_fisica.email = participante['email']
                pessoa_fisica.save()
            else:
                pessoa_fisica = pessoa_fisica[0]
                if not pessoa_fisica.eh_aluno and not pessoa_fisica.eh_servidor and not pessoa_fisica.eh_prestador:
                    pessoa_fisica.email = participante['email']
                    pessoa_fisica.nome_registro = participante['nome']
                    pessoa_fisica.save()

            participante_evento = ParticipanteEvento()
            participante_evento.participante = pessoa_fisica
            participante_evento.evento = self.evento
            participante_evento.tipo_participacao = self.tipo
            participante_evento.save()
            self.evento.participanteevento_set.add(participante_evento)
            self.evento.save()


class ConfiguracaoForm(forms.FormPlus):
    caminho_libreoffice = forms.CharFieldPlus(
        label='Caminho para o executável do LibreOffice', help_text='Ex: /Applications/LibreOffice.app/Contents/MacOS/soffice', required=False
    )
    credenciamento = forms.CharFieldPlus(
        label='Ato de Credenciamento',
        required=False,
        widget=forms.Textarea(),
        help_text='Registro de credenciamento da instituição de educação superior, constando o número, a data, a seção e a página de publicação no DOU',
    )
    recredenciamento = forms.CharFieldPlus(
        label='Ato de Recredenciamento',
        required=False,
        widget=forms.Textarea(),
        help_text='Registro de recredenciamento da instituição de educação superior, constando o número, a data, a seção e a página de publicação no DOU',
    )
    codigo_mec = forms.CharField(label='Código MEC', required=False)
    ano_letivo_atual = forms.IntegerField(label='Ano Letivo Atual', required=False)
    periodo_letivo_atual = forms.ChoiceField(label='Período Letivo Atual', choices=Aluno.PERIODO_LETIVO_CHOICES, required=False)
    tipo_ata_projeto_final = forms.ChoiceField(label='Tipo de Ata de Projeto Final', choices=[['fisica', 'Física'], ['eletronica', 'Eletrônica']])

    exige_naturalidade_estrangeiro = forms.BooleanField(label='Exige Naturalidade de Aluno Estrangeiro', required=False, help_text='Marque essa opção para tornar obrigatório o cadastro da naturalidade do aluno estrangeiro',)

    rap_client_id = forms.CharField(label='RAP Client ID', required=False)
    rap_api_url = forms.CharField(label='RAP API URL', required=False)
    rap_api_user = forms.CharField(label='RAP API User', required=False)
    rap_api_password = forms.CharField(label='RAP API Password', required=False)

    nota_atitudinal = forms.BooleanField(label='Nota Atitudinal', required=False, help_text='Aplicará exclusivamente a forma de cáclulo Média Atitudinal para os cursos do nível de ensino médio.')


class AtualizarFotosAlunosForm(forms.FormPlus):
    fotos = forms.MultiFileField(help_text="Os nomes dos arquivos devem conter apenas a MATRÍCULA do aluno. Só serão aceitos arquivos com a extensão JPG.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def processar(self):
        arquivos_problemas = []
        arquivos = self.request.FILES.getlist('fotos')
        for arquivo in arquivos:
            try:
                matricula = arquivo.name.lower().split(".jpg")[0]
                qs_aluno = Aluno.objects.filter(matricula=matricula)
                if qs_aluno.exists():
                    aluno = qs_aluno[0]
                    aluno.foto.save(f'{aluno.pk}.jpg', ContentFile(arquivo.read()))
                else:
                    arquivos_problemas.append(arquivo.name)
            except Exception:
                arquivos_problemas.append(arquivo.name)
        return arquivos_problemas


class SelecionarHorarioCampusExportarXMLTimeTables(forms.FormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), required=True, label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(required=True, label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)
    diretoria = forms.ModelChoiceField(Diretoria.objects, label='Diretoria', required=True)
    horario_campus = forms.ModelChoiceField(queryset=HorarioCampus.objects, label='Selecione o Horário do Campus')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['horario_campus'].queryset = HorarioCampus.locals.all()
        self.fields['diretoria'].queryset = Diretoria.locals.all()

    def processar(self):
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        horario_campus = self.cleaned_data.get('horario_campus')
        diretoria = self.cleaned_data.get('diretoria')

        return ano_letivo, periodo_letivo, horario_campus, diretoria


class ImportarXMLTimeTables(forms.FormPlus):
    horario_campus = forms.ModelChoiceField(queryset=HorarioCampus.objects, label='Selecione o Horário do Campus')
    arquivo = forms.FileFieldPlus(help_text='Arquivo XML exportado do TimeTables.', required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['horario_campus'].queryset = HorarioCampus.locals.all()
        self.documento_xml = None

    def clean(self):
        if 'horario_campus' in self.cleaned_data and 'arquivo' in self.cleaned_data:
            arquivo = self.cleaned_data.get('arquivo')
            exception_msg = 'Arquivo inválido. Por favor verifique o formato do arquivo e tente novamente'
            try:
                self.documento_xml = minidom.parseString(arquivo.read())
                # Validando se o horário selecionado condiz com o horário vindo do TimeTables.
                for _period in self.documento_xml.getElementsByTagName('period'):
                    horario_inicio_aula = _period.attributes['starttime'].value
                    horario_termino_aula = _period.attributes['endtime'].value

                    # O padrão do TimeTables é H:MM, logo é preciso transformar para HH:MM.
                    if len(horario_inicio_aula) == 4:
                        horario_inicio_aula = '0' + horario_inicio_aula
                    if len(horario_termino_aula) == 4:
                        horario_termino_aula = '0' + horario_termino_aula

                    qs = self.cleaned_data.get('horario_campus').horarioaula_set.filter(inicio=horario_inicio_aula, termino=horario_termino_aula)
                    if not qs.exists():
                        raise forms.ValidationError('O horário selecionado não condiz com o horário vindo no arquivo XML.')
            except KeyError as e:
                raise forms.ValidationError(f'{exception_msg}. Chave {str(e)} não encontrada.')
            except Exception as e:
                raise forms.ValidationError(f'{exception_msg}. Detalhe: {str(e)}')

        return self.cleaned_data

    def processar(self):
        horario_campus = self.cleaned_data.get('horario_campus')

        # Apagando os horários de aula e os professores registrados para os diários que serão manipulados no XML.
        lista_diarios_manipulados = set()
        for _card in self.documento_xml.getElementsByTagName('card'):
            lista_diarios_manipulados.add(_card.attributes['subjectid'].value)
        HorarioAulaDiario.objects.filter(diario__in=lista_diarios_manipulados).delete()
        ProfessorDiario.objects.filter(diario__pk__in=lista_diarios_manipulados).delete()

        for _card in self.documento_xml.getElementsByTagName('card'):
            # Pegando os valores do XML
            id_diario = _card.attributes['subjectid'].value
            ids_professores = _card.attributes['teacherids'].value.split(',')
            id_sala = _card.attributes['classroomids'].value
            dia = _card.attributes['day'].value
            horario = _card.attributes['period'].value

            # Pegando os objetos
            professores = Professor.objects.filter(Q(vinculo__user__usename__in=ids_professores) | Q(vinculo__pessoa__pessoa_fisica__cpf__in=ids_professores))
            diario = Diario.objects.get(pk=id_diario)
            horario_aula = None

            if id_sala or id_sala != '':
                sala = Sala.objects.get(pk=id_sala)
            else:
                sala = None

            # Pesquisando o horário a partir da data de início da aula
            for _period in self.documento_xml.getElementsByTagName('period'):
                if _period.attributes['period'].value == horario:
                    horario_inicio_aula = _period.attributes['starttime'].value
                    horario_termino_aula = _period.attributes['endtime'].value

                    # O padrão do TimeTables é H:MM, logo é preciso transformar para HH:MM.
                    if len(horario_inicio_aula) == 4:
                        horario_inicio_aula = '0' + horario_inicio_aula
                    if len(horario_termino_aula) == 4:
                        horario_termino_aula = '0' + horario_termino_aula

                    qs = horario_campus.horarioaula_set.filter(inicio=horario_inicio_aula, termino=horario_termino_aula)
                    if qs.exists():
                        horario_aula = qs[0]

            # Setando os professores no Diário
            if not diario.professordiario_set.exists():
                for professor in professores:
                    professor_diario = ProfessorDiario()
                    professor_diario.professor = professor
                    professor_diario.diario = diario
                    professor_diario.tipo = TipoProfessorDiario.objects.get(descricao='Principal')
                    professor_diario.save()

            # Setando o horário de aula
            if horario_aula:
                HorarioAulaDiario.objects.get_or_create(diario=diario, dia_semana=int(dia) + 1, horario_aula=horario_aula)

            # Setando a sala de aula
            if sala:
                diario.local_aula = sala
                diario.save()


class EditarAbreviaturaComponenteForm(forms.ModelForm):
    class Meta:
        model = Componente
        fields = ('abreviatura',)


class DiarioEspecialForm(forms.ModelForm):
    professores = forms.MultipleModelChoiceFieldPlus(
        Professor.objects, label='Professores', required=True
    )
    participantes = forms.MultipleModelChoiceFieldPlus(
        Aluno.objects, label='Participantes', required=False
    )

    # def clean_data_fim(self):
    #     if 'data_inicio' in self.cleaned_data and 'data_fim' in self.cleaned_data:
    #         if self.cleaned_data['data_fim'] < self.cleaned_data['data_inicio']:
    #             raise ValidationError(u'A data de fim deve ser maior que a data de início.')
    #     return self.cleaned_data['data_fim']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['horario_campus'].queryset = HorarioCampus.locals.all()
        self.fields['diretoria'].queryset = Diretoria.locals.all()
        self.fields['participantes'].queryset = Aluno.locals.filter(situacao=SituacaoMatricula.MATRICULADO)
        self.fields['componente'].queryset = Componente.objects.filter(tipo__descricao='ATV')

    def clean_descricao(self):
        descricao = self.cleaned_data.get('descricao')
        if self.cleaned_data.get('is_centro_aprendizagem') and not descricao:
            raise forms.ValidationError('Informe a descrição do centro de aprendizagem.')
        return descricao

    class Meta:
        model = DiarioEspecial
        exclude = ('sala',)


class DefinirLocalAulaDiarioEspecialForm(forms.FormPlus):
    sala = forms.ModelChoiceFieldPlus(Sala.objects, required=False)

    def __init__(self, diario_especial, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diario_especial = diario_especial
        uo = diario_especial.diretoria.setor.uo
        self.fields['sala'].queryset = self.fields['sala'].queryset.filter(predio__uo=uo)

    def processar(self):
        self.diario_especial.sala = self.cleaned_data['sala']
        self.diario_especial.save()


class AdicionarAlunosDiarioEspecialForm(forms.FormPlus):
    alunos = forms.MultipleModelChoiceFieldPlus(Aluno.objects, label='Alunos')

    def __init__(self, diario_especial, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alunos'].queryset = Aluno.locals.filter(situacao=SituacaoMatricula.MATRICULADO)
        self.diario_especial = diario_especial

    def processar(self):
        for aluno in self.cleaned_data.get('alunos'):
            self.diario_especial.participantes.add(aluno)
        self.diario_especial.save()


class AdicionarAlunosDiarioEspecialWizard(FormWizardPlus):
    METHOD = 'GET'

    diario = forms.ModelChoiceFieldPlus(Diario.objects, required=False, label='Diário')

    alunos = forms.MultipleModelChoiceField(Aluno.locals.none(), label='', widget=RenderableSelectMultiple('widgets/alunos_widget.html'), required=True)

    steps = ([('Diário', {'fields': ('diario',)})], [('Alunos', {'fields': ('alunos',)})])

    def __init__(self, request, diario_especial, *args, **kwargs):
        self.request = request
        self.diario_especial = diario_especial
        super().__init__(*args, **kwargs)

        semestrais = Diario.objects.filter(
            ano_letivo=diario_especial.ano_letivo,
            periodo_letivo=diario_especial.periodo_letivo,
            turma__curso_campus__diretoria__setor__uo=diario_especial.diretoria.setor.uo,
            turma__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_SEMESTRAL,
        )

        anuais = Diario.objects.filter(
            ano_letivo=diario_especial.ano_letivo,
            turma__curso_campus__diretoria__setor__uo=diario_especial.diretoria.setor.uo,
            turma__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL,
        )

        self.fields['diario'].queryset = semestrais | anuais

    def next_step(self):
        diario = self.get_entered_data('diario')
        if 'alunos' in self.fields:
            self.fields['alunos'].queryset = Aluno.objects.filter(matriculaperiodo__matriculadiario__diario=diario)

    def processar(self):
        for aluno in self.cleaned_data.get('alunos'):
            self.diario_especial.participantes.add(aluno)
        self.diario_especial.save()


class AdicionarProfessorDiarioEspecialForm(forms.FormPlus):
    professor = forms.ModelChoiceField(queryset=Professor.objects, widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS), label='Professor')

    def __init__(self, diario_especial, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['professor'].queryset = Professor.objects.all()
        self.diario_especial = diario_especial

    def processar(self):
        self.diario_especial.professores.add(self.cleaned_data.get('professor'))
        self.diario_especial.save()


class AdicionarEncontroDiarioEspecialForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Data')
    conteudo = forms.CharField(widget=forms.Textarea(), label='Atividade')
    participantes = forms.MultipleModelChoiceField(Aluno.locals.none(), label='Participantes', widget=RenderableSelectMultiple('widgets/alunos_widget.html'), required=False)

    def __init__(self, diario_especial, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diario_especial = diario_especial
        self.fields['participantes'].queryset = self.diario_especial.participantes.all()
        self.fields['participantes'].widget.max_result = self.diario_especial.participantes.count()

    def processar(self):
        encontro = Encontro()
        encontro.data = self.cleaned_data.get('data')
        encontro.conteudo = self.cleaned_data.get('conteudo')
        encontro.diario_especial = self.diario_especial
        encontro.save()

        encontro.participantes.set(self.cleaned_data.get('participantes'))
        encontro.save()


class AtualizarEncontroDiarioEspecialForm(forms.ModelForm):
    participantes = forms.MultipleModelChoiceField(Aluno.locals.none(), label='', widget=RenderableSelectMultiple('widgets/alunos_widget.html'), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['participantes'].queryset = self.instance.diario_especial.participantes.all()
        self.fields['participantes'].widget.max_result = self.instance.diario_especial.participantes.count()
        self.fields['participantes'].initial = list(self.instance.participantes.values_list('pk', flat=True))

    class Meta:
        model = Encontro
        exclude = ('diario_especial',)


class AlunosConflitosHorariosForm(forms.FormPlus):
    SUBMIT_LABEL = 'Pesquisar'
    METHOD = 'GET'

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, label='Período Letivo')
    diretoria = forms.ModelChoiceField(Diretoria.objects.none())
    curso = forms.ModelChoiceFieldPlus(
        CursoCampus.objects, label='Curso', required=False, widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('diretoria', 'diretoria__in')])
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals
        self.fields['curso'].queryset = CursoCampus.objects.filter(ativo=True, diretoria__in=Diretoria.locals.all())

    def processar(self):
        qs_matriculas_periodos = MatriculaPeriodo.objects.filter(
            aluno__matriz__isnull=False,
            aluno__curso_campus__diretoria=self.cleaned_data['diretoria'],
            ano_letivo=self.cleaned_data['ano_letivo'],
            periodo_letivo=self.cleaned_data['periodo_letivo'],
            matriculadiario__situacao=MatriculaDiario.SITUACAO_CURSANDO,
        ).distinct()

        if self.cleaned_data['curso']:
            qs_matriculas_periodos = qs_matriculas_periodos.filter(aluno__curso_campus=self.cleaned_data['curso'])

        alunos_conflitos_horarios = dict()
        for matricula_periodo in qs_matriculas_periodos:
            horarios_conflitos = matricula_periodo.get_horarios_com_choque()
            if horarios_conflitos:
                alunos_conflitos_horarios.update({matricula_periodo.aluno: horarios_conflitos})
        return alunos_conflitos_horarios


class ConfiguracaoLivroForm(forms.ModelFormPlus):
    class Meta:
        model = ConfiguracaoLivro
        exclude = ('codigo_qacademico',)

    def clean(self):
        invalido = False
        modalidades = []
        uo = self.cleaned_data.get('uo', None)
        if uo:
            for modalidade in self.cleaned_data.get('modalidades', []):
                modalidades.append(modalidade)

            if self.instance.pk is None:
                if ConfiguracaoLivro.objects.filter(uo=uo, modalidades__in=modalidades).exists():
                    invalido = True
            elif ConfiguracaoLivro.objects.filter(uo=uo, modalidades__in=modalidades).exclude(pk=self.instance.pk).exists():
                invalido = True

            if invalido:
                raise ValidationError('A(s) modalidade(s) escolhida(s) já possui(em) uma configuração de livro no campus selecionado.')

            return self.cleaned_data


class ConteudoMinicursoFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        ch_somada = 0
        for form in self.forms:
            if form.cleaned_data:
                ch_somada += form.cleaned_data.get('ch') or 0
                if ch_somada > 160:
                    raise forms.ValidationError('O limite para carga horária total é de 160 horas.')


class MinicursoForm(forms.ModelFormPlus):
    descricao_certificado = forms.CharFieldPlus(label='Descrição para o certificado', widget=forms.TextInput(attrs={'class': ''}))
    diretoria = forms.ModelChoiceField(Diretoria.objects.none(), widget=forms.Select())
    ppc = forms.FileFieldPlus(label='PPC', required=False)
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=True)
    periodo_letivo = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=True)
    ch_total = forms.NumericField(label='Carga Horária Total h/r')
    tipo_hora_aula = forms.ChoiceField(choices=[[0, '----'], [45, '45 min'], [60, '60 min']], label='Tipo Hora Aula')

    class Meta:
        model = Minicurso
        exclude = ()

    fieldsets = (
        ('Informações Gerais', {'fields': ('descricao_certificado', ('diretoria', 'extensao'), 'resolucao_criacao', 'codigo_sistec')}),
        ('Dados de Criação', {'fields': (('ano_letivo', 'periodo_letivo'), 'ppc')}),
        ('Informação da Carga Horária', {'fields': (('ch_total', 'tipo_hora_aula'),)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diretoria'].queryset = Diretoria.locals
        self.initial['diretoria'] = self.instance.diretoria
        self.initial['descricao_certificado'] = self.instance.descricao_historico
        self.initial['ano_letivo'] = self.instance.ano_letivo
        self.initial['periodo_letivo'] = self.instance.periodo_letivo

        is_administrador = in_group(self.request.user, 'Administrador Acadêmico')
        if not is_administrador:
            self.fields['codigo_sistec'].widget.attrs['disabled'] = 'disabled'

        for field_name in ['descricao_certificado']:
            self.fields[field_name].widget.attrs['class'] = self.fields[field_name].widget.attrs.get('class')

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.instance.descricao = 'FIC- {}'.format(self.cleaned_data['descricao_certificado'])
        self.instance.descricao_historico = self.cleaned_data['descricao_certificado']
        self.instance.modalidade = Modalidade.objects.get(id=Modalidade.FIC)
        self.instance.ano_letivo = self.cleaned_data['ano_letivo']
        self.instance.periodo_letivo = self.cleaned_data['periodo_letivo']
        self.instance.ppc = self.cleaned_data['ppc']
        return super().save(*args, **kwargs)


class ProfessorMinicursoFormset(forms.models.BaseInlineFormSet):
    professor = forms.ModelChoiceFieldPlus(Funcionario.objects, label='Professor', required=False, widget=AutocompleteWidget(search_fields=Funcionario.SEARCH_FIELDS))

    def clean(self):
        cleaned_data = super().clean()
        total = 0
        for form in self.forms:
            if not form.is_valid():
                return cleaned_data
            if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                total += form.cleaned_data['carga_horaria'] or 0

        if total > self.instance.minicurso.ch_total:
            raise ValidationError(f'A soma das cargas-horárias dos professores não pode ultrapassar {self.instance.minicurso.ch_total}.')
        return cleaned_data


class TurmaMinicursoForm(forms.ModelFormPlus):
    professores = forms.MultipleModelChoiceFieldPlus(Vinculo.objects, label='Professores', required=True)
    planilha = forms.FileFieldPlus(help_text='O arquivo deve ser no formato "xlsx", sem cabeçalho, contendo as seguintes colunas: CPF, Nome e E-mail.', required=False)

    class Meta:
        model = TurmaMinicurso
        exclude = ('minicurso', 'participantes', 'codigo')

    def __init__(self, minicurso=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.minicurso = minicurso
        self.participantes = []
        for field_name in ['descricao']:
            self.fields[field_name].widget.attrs['class'] = self.fields[field_name].widget.attrs.get('class')

    def clean_professores(self):
        for vinculo in self.cleaned_data['professores'].all():
            if not hasattr(vinculo, 'user'):
                raise forms.ValidationError('O funcionário {} não pode ser adicionado pois não possui usuário no sistema.')
        return self.cleaned_data['professores']

    def clean(self):
        if self.cleaned_data['planilha']:
            try:
                planilha = self.cleaned_data['planilha'].file
                workbook = xlrd.open_workbook(file_contents=planilha.read())
                sheet = workbook.sheet_by_index(0)
                for i in range(0, sheet.nrows):
                    cpf = str(sheet.cell_value(i, 0))
                    if not cpf_valido(cpf):
                        raise ValidationError(f'O cpf {cpf} é inválido.')
                    nome = str(sheet.cell_value(i, 1))
                    email = str(sheet.cell_value(i, 2))
                    if not email_valido(email):
                        raise ValidationError(f'O e-mail {email} é inválido.')
                    participante = dict(cpf=cpf, nome=nome, email=email)
                    if self.instance.pk:
                        qs = self.instance.participantes.filter(turma_minicurso=self.instance, participante__cpf=cpf)
                        if not qs.exists():
                            self.participantes.append(participante)
                    else:
                        self.participantes.append(participante)
            except XLRDError:
                raise ValidationError(
                    'Não foi possível processar a planilha. Verfique se o formato do arquivo é .xlsx, sem cabeçalho e se contém as seguintes colunas: CPF, Nome e E-mail.'
                )
        return self.cleaned_data

    @transaction.atomic
    def processar(self):
        self.instance.minicurso = self.minicurso
        if self.instance.pk:
            self.instance.professores.clear()
        self.instance.minicurso = self.minicurso
        self.instance.ano_letivo = self.cleaned_data['ano_letivo']
        self.instance.periodo_letivo = self.cleaned_data['periodo_letivo']
        self.instance.data_inicio = self.cleaned_data['data_inicio']
        self.instance.data_fim = self.cleaned_data['data_fim']
        self.instance.gerar_matricula = self.cleaned_data['gerar_matricula']
        self.instance.save()
        for vinculo in self.cleaned_data['professores'].all():
            qs = Professor.objects.filter(vinculo__id=vinculo.pk)
            if qs.exists():
                professor = qs[0]
                self.instance.professores.add(professor)
            else:
                professor = Professor()
                professor.vinculo = vinculo
                professor.save()
                self.instance.professores.add(professor)
        for participante in self.participantes:
            pessoa_fisica = PessoaFisica()
            pessoa_fisica.cpf = participante['cpf']
            pessoa_fisica.nome = participante['nome']
            if participante['email']:
                pessoa_fisica.email = participante['email']
            self.instance.adicionar_novo_aluno(pessoa_fisica)


class EditarTurmaMinicursoForm(forms.ModelFormPlus):
    class Meta:
        model = TurmaMinicurso
        exclude = ('participantes',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        minicurso_id = self.request.GET.get('minicurso')
        self.participantes = []
        if minicurso_id:
            self.fields['minicurso'].initial = minicurso_id
            self.fields['minicurso'].widget = forms.HiddenInput()
        for field_name in ['descricao']:
            self.fields[field_name].widget.attrs['class'] = self.fields[field_name].widget.attrs.get('class')

    def clean(self):
        if not self.request.user.is_superuser and self.instance.pk and self.instance.participantes.exists():
            raise forms.ValidationError('Esta turma de minicurso não pode ser editada pois já possui aluno cadastrado.')

        return self.cleaned_data

    @transaction.atomic
    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)


class MonitorMinicursoForm(forms.ModelFormPlus):
    class Meta:
        model = MonitorMinicurso
        fields = ('aluno', 'carga_horaria')


class ProfessorMinicursoForm(forms.ModelFormPlus):

    vinculo = forms.ModelChoiceField(queryset=Vinculo.objects, label='Professor', required=True, widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS))

    fieldsets = (('', {'fields': ('vinculo', 'carga_horaria')}),)

    class Meta:
        model = ProfessorMinicurso
        fields = ('carga_horaria',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs_prestadores = Vinculo.objects.prestadores().filter(pessoa__excluido=False, professor__isnull=False)
        qs_docentes = Vinculo.objects.servidores_docentes().filter(pessoa__excluido=False)
        qs_tecnicos = Vinculo.objects.servidores_tecnicos_administrativos().filter(pessoa__excluido=False)

        if self.instance.pk:
            qs_docentes = qs_docentes | qs_docentes.filter(pessoa__excluido=True, pk=self.instance.professor.vinculo.id)
            qs_tecnicos = qs_tecnicos | qs_tecnicos.filter(pessoa__excluido=True, pk=self.instance.professor.vinculo.id)
        self.fields['vinculo'].queryset = (qs_docentes | qs_tecnicos | qs_prestadores).distinct()

        if self.instance.pk:
            self.fields['vinculo'].initial = self.instance.professor.vinculo.pk

    def save(self, *args, **kwargs):
        vinculo = self.cleaned_data['vinculo']
        obj = super().save(False)
        qs = Professor.objects.filter(vinculo__id=vinculo.pk)
        if qs.exists():
            obj.professor = qs[0]
        else:
            professor = Professor()
            professor.vinculo = vinculo
            professor.save()
            obj.professor = professor
            Group.objects.get(name='Professor').user_set.add(professor.vinculo.user)
        obj.save()


class EditarParticipanteTurmaMinicursoForm(forms.ModelFormPlus):
    class Meta:
        model = PessoaFisica
        fields = ('nome', 'cpf', 'email')

    def clean(self):
        if not cpf_valido(self.data.get('cpf')):
            raise ValidationError({'cpf': 'O cpf {} é inválido.'.format(self.data['cpf'])})

    def save(self, *args, **kwargs):
        if isinstance(self.instance.sub_instance(), Servidor):
            return None
        else:
            self.instance.nome_registro = self.cleaned_data['nome']
            if self.cleaned_data['email']:
                self.instance.email = self.cleaned_data['email']
            self.instance.cpf = self.cleaned_data['cpf']
            self.instance.save()
            return super().save(*args, **kwargs)


class AutenticarCertificadoMinicursoForm(forms.FormPlus):
    SUBMIT_LABEL = 'Autenticar Certificado'
    METHOD = 'get'
    cpf = forms.BrCpfField(label='CPF')
    data_conclusao = forms.DateFieldPlus(label='Data de Conclusão')
    codigo_turma = forms.IntegerField(label='Código da Turma')

    def processar(self):
        aluno = Aluno.objects.filter(
            pessoa_fisica__cpf=self.cleaned_data['cpf'],
            situacao__codigo_academico=SituacaoMatricula.CONCLUIDO,
            turmaminicurso__data_fim__lte=self.cleaned_data['data_conclusao'],
            turmaminicurso__data_fim__gte=self.cleaned_data['data_conclusao'],
            turmaminicurso__pk=int(self.cleaned_data['codigo_turma']),
        )
        if aluno.exists():
            return aluno[0], aluno[0].turmaminicurso_set.all()[0]
        else:
            return None, None


class AdicionarParticipanteTurmaMinicursoForm(forms.FormPlus):
    cpf = forms.BrCpfField()
    nome = forms.CharFieldPlus()
    email = forms.EmailField()

    def __init__(self, turma_minicurso, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turma_minicurso = turma_minicurso

    def clean_cpf(self):
        qs = self.turma_minicurso.participantes.filter(pessoa_fisica__cpf=self.cleaned_data.get('cpf'))
        if qs.exists():
            raise forms.ValidationError('Já existe um participante com o CPF informado.')
        return self.cleaned_data.get('cpf')

    @transaction.atomic
    def processar(self):
        pessoa_fisica = PessoaFisica()
        pessoa_fisica.cpf = self.cleaned_data['cpf']
        pessoa_fisica.nome = self.cleaned_data['nome']
        pessoa_fisica.email = self.cleaned_data['email']
        self.turma_minicurso.adicionar_novo_aluno(pessoa_fisica)


class ImportarParticipantesTurmaMinicursoForm(forms.FormPlus):
    planilha = forms.FileFieldPlus(help_text='O arquivo deve ser no formato "xlsx", sem cabeçalho, contendo as seguintes colunas: CPF, Nome e E-mail.')

    def __init__(self, turma_minicurso, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turma_minicurso = turma_minicurso
        self.participantes = []

    def clean(self):
        try:
            cpfs_importados = []
            if self.cleaned_data.get('planilha'):
                planilha = self.cleaned_data['planilha'].file
                workbook = xlrd.open_workbook(file_contents=planilha.read())
                sheet = workbook.sheet_by_index(0)
                for i in range(0, sheet.nrows):
                    cpf = str(sheet.cell_value(i, 0)).strip()
                    if not cpf_valido(cpf):
                        raise ValidationError(f'O cpf {cpf} é inválido.')
                    nome = str(sheet.cell_value(i, 1))
                    email = str(sheet.cell_value(i, 2))
                    if not email_valido(email):
                        raise ValidationError(f'O e-mail {email} é inválido.')
                    qs = self.turma_minicurso.participantes.filter(pessoa_fisica__cpf=cpf)
                    if not qs.exists() and cpf not in cpfs_importados:
                        cpfs_importados.append(cpf)
                        participante = dict(cpf=cpf, nome=nome, email=email)
                        self.participantes.append(participante)
        except XLRDError:
            raise ValidationError(
                'Não foi possível processar a planilha. Verfique se o formato do arquivo é .xlsx, sem cabeçalho e se contém as seguintes colunas: CPF, Nome e E-mail.'
            )
        except IndexError:
            raise ValidationError('O arquivo deve ser no formato "xlsx", sem cabeçalho, contendo as seguintes colunas: CPF, Nome e E-mail.')
        return self.cleaned_data

    def processar(self):
        for participante in self.participantes:
            pessoa_fisica = PessoaFisica()
            pessoa_fisica.cpf = participante['cpf']
            pessoa_fisica.nome = participante['nome']
            if participante['email']:
                pessoa_fisica.email = participante['email']
            self.turma_minicurso.adicionar_novo_aluno(pessoa_fisica)


class RelatorioMigracaoForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    fieldsets = (('', {'fields': (('diretoria', 'ano_letivo', 'periodo_letivo'), 'ignorar_ultimo_periodo', 'modalidades')}),)

    diretoria = forms.ModelChoiceField(Diretoria.objects, label='Diretoria', required=True)
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos().order_by('-ano'), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=PERIODO_LETIVO_CHOICES)
    ignorar_ultimo_periodo = forms.BooleanField(label='Ignorar pendências do último período', initial=True, required=False)
    modalidades = forms.MultipleModelChoiceField(
        Modalidade.objects, label='Modalidades', required=True, widget=forms.CheckboxSelectMultiple(), initial=Modalidade.objects.all().values_list('id', flat=True)
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modalidades'].queryset = self.fields['modalidades'].queryset.exclude(id=Modalidade.FIC)
        self.fields['diretoria'].initial = Diretoria.objects.all()[0].pk

    def filtrar(self, qs):
        diretoria = self.cleaned_data['diretoria']
        ano_letivo = self.cleaned_data['ano_letivo']
        periodo_letivo = self.cleaned_data['periodo_letivo']
        modalidades = self.cleaned_data['modalidades']

        qs = qs.filter(aluno__curso_campus__diretoria=diretoria)
        qs = qs.filter(aluno__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL, ano_letivo=ano_letivo) | qs.filter(
            aluno__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_SEMESTRAL, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo
        )

        if modalidades.count() != Modalidade.objects.count():
            qs = qs.filter(aluno__curso_campus__modalidade__in=modalidades.values_list('id', flat=True))

        return qs


class ItemConfiguracaoCreditosEspeciaisForm(forms.ModelFormPlus):
    class Meta:
        model = ItemConfiguracaoCreditosEspeciais
        exclude = ('configuracao',)


class ConfiguracaoCreditosEspeciaisForm(forms.ModelFormPlus):
    fieldsets = (('Dados Gerais', {'fields': ('descricao', 'quantidade_maxima_creditos_especiais', 'ativo')}),)

    class Meta:
        model = ConfiguracaoCreditosEspeciais
        exclude = ()


class CreditoEspecialForm(forms.ModelFormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)
    item_configuracao_creditos_especiais = forms.ModelChoiceField(ItemConfiguracaoCreditosEspeciais.objects, label='Tipo de Atividade')

    class Meta:
        model = CreditoEspecial
        exclude = ('matricula_periodo',)

    fieldsets = (('Período Letivo', {'fields': (('ano_letivo', 'periodo_letivo'),)}), ('Atividade', {'fields': ('item_configuracao_creditos_especiais',)}))

    def __init__(self, aluno, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aluno = aluno
        self.fields['ano_letivo'].queryset = Ano.objects.filter(pk__in=aluno.matriculaperiodo_set.order_by('ano_letivo').values_list('ano_letivo', flat=True).distinct())
        self.fields['item_configuracao_creditos_especiais'].queryset = self.fields['item_configuracao_creditos_especiais'].queryset.filter(
            configuracao=aluno.matriz.configuracao_creditos_especiais
        )
        if self.instance.pk:
            self.initial['ano_letivo'] = self.instance.matricula_periodo.ano_letivo.pk
            self.initial['periodo_letivo'] = self.instance.matricula_periodo.periodo_letivo

    def clean(self):
        if not self.instance.pk:
            creditos_ja_cadastrados = (
                CreditoEspecial.objects.filter(matricula_periodo__aluno=self.aluno)
                .aggregate(Sum('item_configuracao_creditos_especiais__equivalencia_creditos'))
                .get('item_configuracao_creditos_especiais__equivalencia_creditos__sum')
                or 0
            )
            if creditos_ja_cadastrados >= self.aluno.matriz.configuracao_creditos_especiais.quantidade_maxima_creditos_especiais:
                raise ValidationError(
                    'Não é possível cadastrar este crédito especial, pois o aluno já atingiu o limite de {} créditos especiais estipulados na matriz.'.format(
                        self.aluno.matriz.configuracao_creditos_especiais.quantidade_maxima_creditos_especiais
                    )
                )
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        if not self.aluno.matriculaperiodo_set.filter(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo).exists():
            raise ValidationError('O aluno não possui matrícula no ano/período selecionado.')
        return self.cleaned_data

    def save(self, *args, **kwargs):
        ano_letivo = self.cleaned_data.get('ano_letivo')
        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        self.instance.matricula_periodo = self.aluno.matriculaperiodo_set.get(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)
        super().save(*args, **kwargs)


class PreencherRelatorioCensupForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Pesquisar'
    CAMPUS_CURSO = 1
    CAMPUS_PROFESSOR = 2
    CAMPUS_ALUNO = 3
    CURSO_ALUNO = 4

    tipo_relatorio = forms.ChoiceField(choices=[[CAMPUS_CURSO, 'Campus do Curso'], [CAMPUS_PROFESSOR, 'Campus do Professor'], [CAMPUS_ALUNO, 'Campus do Aluno'], [CURSO_ALUNO, 'Curso do Aluno']], required=True)
    planilha = forms.FileFieldPlus(required=True, filetypes=['xls'])
    coluna_busca = forms.IntegerFieldPlus(label='Coluna de Busca', help_text='Número da coluna que o sistema buscará.', required=True)
    coluna_salva = forms.IntegerFieldPlus(label='Coluna de Salvamento', help_text='Número da coluna que o sistema salvará.', required=True)

    def clean_coluna_busca(self):
        if self.cleaned_data.get('coluna_busca') < 1:
            return ValidationError('Coluna inválida.')
        return self.cleaned_data.get('coluna_busca')

    def clean_coluna_salva(self):
        if self.cleaned_data.get('coluna_salva') < 1:
            return ValidationError('Coluna inválida.')
        return self.cleaned_data.get('coluna_salva')


class AtualizarCodigoEducacensoForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Pesquisar'

    arquivo = forms.FileFieldPlus(required=True, help_text='Arquivo TXT de retorno do MEC contendo os prováveis registros.')

    def processar(self):
        arquivo = self.cleaned_data['arquivo'].file
        registros = []
        for line in arquivo.readlines():
            registros.append(line)
        return tasks.atualizar_codigo_educacenso(registros)


class PreencherRelatorioSistecForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Pesquisar'

    campus = forms.ModelChoiceFieldPlus(UnidadeOrganizacional.objects.campi().all(), label='Campus')
    planilha = forms.FileFieldPlus(label='Planilha', required=True, filetypes=['csv'], max_file_size='20971520', help_text='O arquivo deve possuir uma coluna chamada "NO_STATUS_MATRICULA".')


class PreencherRelatorioAlunosNaoExistentesNoSistecForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Pesquisar'

    campus = forms.ModelChoiceFieldPlus(UnidadeOrganizacional.objects.campi().all(), label='Campus')
    ano_letivo = forms.ModelMultiplePopupChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    excluir_convenio = forms.ModelMultiplePopupChoiceField(Convenio.objects, label='Excluir Convênios', required=False)
    planilha = forms.FileFieldPlus(label='Planilha', required=True, filetypes=['csv'], max_file_size='20971520', help_text='O arquivo deve possuir as coluna "NU_CPF e CO_CURSO".')


class RelatorioIsFForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Gerar Relatório XLS'

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)

    def processar(self):
        return self.cleaned_data['ano_letivo'], self.cleaned_data['periodo_letivo']


class AuditoriaCensoForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Gerar Relatório'
    TIPOS_RELATORIO = [
        [1, 'Dados Divergentes com a Receita Federal'],
        [2, 'Matrículas na mesma Modalidade'],
        [3, 'Nome com Pontuação/Caracter Especial']
    ]

    tipo_relatorio = forms.ChoiceField(label='Tipo de Relatório', choices=TIPOS_RELATORIO, required=True)
    uo = forms.ModelChoiceFieldPlus(UnidadeOrganizacional.locals, label='Campus', required=False)
    curso = forms.ModelChoiceFieldPlus(
        CursoCampus.locals, label='Curso', required=False, widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('uo', 'diretoria__setor__uo')])
    )
    nivel_ensino = forms.MultipleModelChoiceFieldPlus(NivelEnsino.objects, label='Nível de Ensino', required=False)
    modalidade = forms.MultipleModelChoiceFieldPlus(Modalidade.objects, label='Modalidade', required=False)
    situacao = forms.MultipleModelChoiceFieldPlus(SituacaoMatricula.objects, label='Situação', required=False)

    def clean_situacao(self):
        tipo = self.cleaned_data.get('tipo_relatorio')
        situacao = self.cleaned_data.get('situacao')
        if int(tipo) == 2 and not situacao:
            raise ValidationError('Informe pelo menos uma situação de matrícula.')
        return situacao

    def processar(self):
        tipo = int(self.cleaned_data['tipo_relatorio'])
        uo = self.cleaned_data.get('uo') or None
        curso = self.cleaned_data.get('curso') or None
        nivel_ensino = self.cleaned_data.get('nivel_ensino') or None
        modalidade = self.cleaned_data.get('modalidade') or None
        situacao = self.cleaned_data.get('situacao') or None
        cpf_operador = self.request.user.get_vinculo().pessoa.pessoafisica.cpf
        return tasks.exportar_auditoria_censos(tipo, uo, curso, nivel_ensino, modalidade, situacao, cpf_operador)


class RelatorioSTTUForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Gerar Relatório STTU'
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=[[None, '----']] + Aluno.PERIODO_LETIVO_CHOICES, required=False)
    ano_letivo_ingresso = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo de Ingresso', required=False)
    periodo_letivo_ingresso = forms.ChoiceField(label='Período Letivo de Ingresso', required=False, choices=[[None, '----']] + Aluno.PERIODO_LETIVO_CHOICES)
    uos = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.locals, label='Campus', required=False)
    curso_campus = forms.ModelChoiceFieldPlus(
        CursoCampus.locals, label='Curso', required=False, widget=AutocompleteWidget(search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('uos', 'diretoria__setor__uo__in')])
    )
    turma = forms.ModelChoiceFieldPlus(
        Turma.objects.none(),
        label='Turma',
        required=False,
        widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS, form_filters=[('curso_campus', 'curso_campus'), ('uos', 'curso_campus__diretoria__setor__uo__in')]),
    )
    cidade = forms.ModelChoiceFieldPlus(Cidade.objects, label='Cidade', required=False)
    polos = forms.ModelMultiplePopupChoiceField(Polo.objects, required=False, label='Polo EAD', help_text='Apenas para o Turno EAD.')

    fieldsets = (
        ('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo'),)}),
        ('Filtros', {'fields': (('ano_letivo_ingresso', 'periodo_letivo_ingresso'), 'uos', ('curso_campus', 'turma'), 'cidade', 'polos')})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        MUNICIPIO_NATAL = '1761'
        MUNICIPIO_CEARA_MIRIM = '1651'
        MUNICIPIO_SAO_GONCALO = '1837'
        MUNICIPIO_PARNAMIRIM = '1779'
        self.MUNICIPIO_ABRANGENCIA_STTU = (MUNICIPIO_NATAL, MUNICIPIO_CEARA_MIRIM, MUNICIPIO_SAO_GONCALO, MUNICIPIO_PARNAMIRIM)
        uos = UnidadeOrganizacional.locals.filter(municipio__codigo__in=self.MUNICIPIO_ABRANGENCIA_STTU)
        self.fields['uos'].queryset = uos
        self.fields['curso_campus'].queryset = CursoCampus.locals.filter(diretoria__setor__uo__in=uos)
        self.fields['turma'].queryset = Turma.locals.filter(curso_campus__diretoria__setor__uo__in=uos)

        if not self.request.user.get_vinculo().setor.uo.eh_reitoria:
            self.fields['uos'].initial = (self.request.user.get_vinculo().setor.uo_id,)

    def clean(self):
        data = self.cleaned_data.copy()
        data.pop('ano_letivo', '')
        empty = True
        for key, value in data.items():
            if value:
                empty = False
                break
        if empty:
            raise forms.ValidationError('Escolha pelo menos um filtro')
        return self.cleaned_data

    def processar(self):
        situacoes_matricula = (SituacaoMatriculaPeriodo.MATRICULADO, SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL)
        modalidades = (
            Modalidade.INTEGRADO_EJA,
            Modalidade.INTEGRADO,
            Modalidade.SUBSEQUENTE,
            Modalidade.CONCOMITANTE,
            Modalidade.LICENCIATURA,
            Modalidade.APERFEICOAMENTO,
            Modalidade.ENGENHARIA,
            Modalidade.BACHARELADO,
            Modalidade.MESTRADO,
            Modalidade.ESPECIALIZACAO,
            Modalidade.DOUTORADO,
            Modalidade.TECNOLOGIA,
        )
        ano_letivo = self.cleaned_data.get('ano_letivo')

        qs = MatriculaPeriodo.objects.filter(
            aluno__matriz__isnull=False,
            aluno__curso_campus__modalidade__in=modalidades,
            situacao__in=situacoes_matricula,
            aluno__pessoa_fisica__nascimento_data__isnull=False,
            ano_letivo=ano_letivo
        )

        qs = qs.exclude(aluno__nome_mae__isnull=True).exclude(aluno__nome_mae='').select_related('aluno__pessoa_fisica')

        periodo_letivo = self.cleaned_data.get('periodo_letivo')
        if periodo_letivo:
            qs = qs.filter(periodo_letivo=periodo_letivo)

        polos = self.cleaned_data.get('polos')
        if polos:
            qs = qs.filter(aluno__polo__in=polos)

        uos = self.cleaned_data.get('uos')
        if not uos:
            uos = UnidadeOrganizacional.locals.filter(municipio__codigo=self.MUNICIPIO_ABRANGENCIA_STTU)
        qs = qs.filter(aluno__curso_campus__diretoria__setor__uo__in=uos)

        curso = self.cleaned_data.get('curso_campus')
        if curso:
            qs = qs.filter(aluno__curso_campus=curso)

        turma = self.cleaned_data.get('turma')
        if turma:
            qs = qs.filter(turma=turma)

        cidade = self.cleaned_data.get('cidade')
        if cidade:
            qs = qs.filter(aluno__cidade_id=cidade)

        ano_letivo_ingresso = self.cleaned_data.get('ano_letivo_ingresso')
        if ano_letivo_ingresso:
            qs = qs.filter(aluno__ano_letivo=ano_letivo_ingresso)

        periodo_letivo_ingresso = self.cleaned_data.get('periodo_letivo_ingresso')
        if periodo_letivo_ingresso:
            qs = qs.filter(aluno__periodo_letivo=periodo_letivo_ingresso)
        return qs


class RelatorioCensupForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Gerar Relatório CENSUP'

    tipo = forms.ChoiceField(choices=[[1, 'Docente'], [2, 'Aluno']], required=True)
    uos = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.objects.campi().all(), label='Campus', required=False)
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')

    amostra = forms.BooleanField(label='Amostra?', help_text='Marque essa opção caso deseje gerar uma amostra contendo apenas 10 registros', required=False)
    cpfs = forms.CharField(
        label='Selecionar CPFs', help_text='Informe os CPFs (sem pontuação e em linhas separadas) que deverão ser mantidos na listagem.', required=False, widget=forms.Textarea()
    )
    ignorar_cpfs = forms.CharField(
        label='Ignorar CPFs', help_text='Informe os CPFs (sem pontuação e em linhas separadas) que deverão ser excluídos da listagem.', required=False, widget=forms.Textarea()
    )

    fieldsets = (('Dados Gerais', {'fields': (('tipo', 'ano_letivo'),)}), ('Outras Informações', {'fields': ('uos', 'amostra', 'ignorar_cpfs', 'cpfs')}))

    def processar(self):
        cpfs = self.cleaned_data['cpfs'].replace(' ', '').replace('\r', '')
        ignorar_cpfs = self.cleaned_data['ignorar_cpfs'].replace(' ', '').replace('\r', '')
        amostra = self.cleaned_data['amostra']
        tipo = int(self.cleaned_data['tipo'])
        uos = list(self.cleaned_data['uos'].values_list('id', flat=True))
        ano = self.cleaned_data['ano_letivo'].ano
        cpfs = cpfs and cpfs.split('\n') or ''
        ignorar_cpfs = ignorar_cpfs and ignorar_cpfs.split('\n') or []
        return tasks.exportar_dados_censup(tipo, ano, uos, amostra, cpfs, ignorar_cpfs)


class RegistroConvocacaoENADEForm(forms.ModelFormPlus):
    SUBMIT_LABEL = 'Salvar'

    aluno = forms.ModelChoiceFieldPlus(Aluno.ativos, label='Aluno', widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS), help_text='Lista alunos ativos.')

    class Meta:
        model = RegistroConvocacaoENADE
        exclude = ('situacao', 'percentual_ch_cumprida', 'justificativa_dispensa')

    def clean(self):
        aluno = self.cleaned_data.get('aluno')
        convocacao_enade = self.cleaned_data.get('convocacao_enade')
        if aluno and convocacao_enade:
            if convocacao_enade.registroconvocacaoenade_set.filter(aluno=aluno).exists():
                raise ValidationError(f'O(A) aluno(a) {aluno} já está cadastrado(a) na convocação atual.')
        return self.cleaned_data

    def __init__(self, convocacao, curso_campus, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if convocacao:
            self.convocacao = convocacao
            self.fields['convocacao_enade'].initial = self.convocacao.pk
            self.fields['convocacao_enade'].widget = forms.HiddenInput()

        if curso_campus:
            self.fields['aluno'].queryset = Aluno.ativos.filter(curso_campus=curso_campus)


class EstagioDocenteForm(forms.ModelFormPlus):
    professor_coordenador = forms.ModelChoiceField(queryset=Professor.objects.none(), label='Professor Coordenador')
    professor_orientador = forms.ModelChoiceField(queryset=Professor.objects, widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS), label='Professor Orientador')

    class Meta:
        model = EstagioDocente
        exclude = ('matricula_diario',)

    fieldsets = (
        ('Dados Gerais', {'fields': ('turno', 'convenio', 'escola', 'nivel', 'professor_coordenador', 'professor_orientador')}),
        ('Período', {'fields': (('data_inicio', 'data_fim'), 'data_final_envio_portfolio')}),
        ('Documentação', {'fields': (('plano_estagio', 'termo_compromisso'), 'documentacao_comprobatoria')}),
        ('Seguro', {'fields': ('nome_seguradora', 'numero_seguro')}),
        (
            'Professor Colaborador',
            {
                'fields': (
                    'nome_professor_colaborador',
                    'cpf_professor_colaborador',
                    'telefone_professor_colaborador',
                    'cargo_professor_colaborador',
                    'formacao_professor_colaborador',
                    'email_professor_colaborador',
                )
            },
        ),
        ('Observações', {'fields': ('observacoes',)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['professor_coordenador'].queryset = Professor.servidores_docentes
        if self.instance.matricula_diario_id:
            self.fields['professor_coordenador'].queryset = self.instance.matricula_diario.matricula_periodo.aluno.curso_campus.coordenadores_estagio_docente

    def clean(self, *args, **kwargs):
        cleaned_data = self.cleaned_data
        plano_estagio = cleaned_data.get('plano_estagio')
        termo_compromisso = cleaned_data.get('termo_compromisso')
        documentacao_comprobatoria = cleaned_data.get('documentacao_comprobatoria')
        if not (plano_estagio and termo_compromisso) and not documentacao_comprobatoria:
            raise ValidationError(
                dict(
                    plano_estagio='Obrigatório preencher Plano de Estágio e Termo de Compromisso conjuntamente ou Documentação Comprobatória de Prática Anterior em substituição a estes documentos.'
                )
            )
        return cleaned_data

    def save(self, *args, **kwargs):
        self.instance.professor_coordenador = self.cleaned_data.get('professor_coordenador')
        self.instance.professor_orientador = self.cleaned_data.get('professor_orientador')
        return super().save(*args, **kwargs)


class VisitaEstagioDocenteForm(forms.ModelFormPlus):
    class Meta:
        model = VisitaEstagioDocente
        exclude = ('estagio_docente',)

    fieldsets = (('Dados Gerais', {'fields': ('data_visita', 'relatorio')}), ('Atividades', {'fields': ('desenvolvendo_atividades_previstas', 'informacoes_complementares')}))

    def __init__(self, estagio_docente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.estagio_docente = estagio_docente


class EnviarPortfolioEstagioDocenteForm(forms.ModelFormPlus):
    class Meta:
        model = EstagioDocente
        fields = ('portfolio',)


class CadastrarEstagioDocenteConcomitanteForm(forms.ModelFormPlus):
    professor_coordenador = forms.ModelChoiceField(queryset=Professor.objects.none(), label='Professor Coordenador')
    professor_orientador = forms.ModelChoiceField(queryset=Professor.objects, widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS), label='Professor Orientador')

    class Meta:
        model = EstagioDocente
        exclude = ('matricula_diario', 'justificativa')

    fieldsets = (
        ('Dados Gerais', {'fields': ('turno', 'convenio', 'escola', 'nivel', 'professor_coordenador', 'professor_orientador')}),
        ('Período', {'fields': (('data_inicio', 'data_fim'), 'data_final_envio_portfolio')}),
        ('Documentação', {'fields': (('plano_estagio', 'termo_compromisso'), 'documentacao_comprobatoria')}),
        ('Seguro', {'fields': ('nome_seguradora', 'numero_seguro')}),
        (
            'Professor Colaborador',
            {
                'fields': (
                    'nome_professor_colaborador',
                    'cpf_professor_colaborador',
                    'telefone_professor_colaborador',
                    'cargo_professor_colaborador',
                    'formacao_professor_colaborador',
                    'email_professor_colaborador',
                )
            },
        ),
        ('Observações', {'fields': ('observacoes',)}),
    )

    def __init__(self, estagio_docente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['professor_coordenador'].queryset = estagio_docente.matricula_diario.matricula_periodo.aluno.curso_campus.coordenadores_estagio_docente
        self.estagio_docente = estagio_docente

    def clean(self, *args, **kwargs):
        cleaned_data = self.cleaned_data
        plano_estagio = cleaned_data.get('plano_estagio')
        termo_compromisso = cleaned_data.get('termo_compromisso')
        documentacao_comprobatoria = cleaned_data.get('documentacao_comprobatoria')
        if not (plano_estagio and termo_compromisso) and not documentacao_comprobatoria:
            raise ValidationError(
                dict(
                    plano_estagio='Obrigatório preencher Plano de Estágio e Termo de Compromisso conjuntamente ou Documentação Comprobatória de Prática Anterior em substituição a estes documentos.'
                )
            )
        return cleaned_data

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.instance.matricula_diario = self.estagio_docente.matricula_diario
        self.instance.professor_coordenador = self.cleaned_data.get('professor_coordenador')
        self.instance.professor_orientador = self.cleaned_data.get('professor_orientador')
        return super().save(*args, **kwargs)


class EncerrarEstagioDocenteForm(forms.ModelFormPlus):
    class Meta:
        model = EstagioDocente
        fields = ('avaliacao_do_orientador', 'avaliacao_do_professor_colaborador', 'portfolio', 'ch_final')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avaliacao_do_orientador'].required = True
        self.fields['avaliacao_do_professor_colaborador'].required = True
        self.fields['ch_final'].required = True
        self.fields['portfolio'].required = True
        if self.instance.matricula_diario.estagiodocente_set.exclude(pk=self.instance.pk).exists():
            mensagem = 'Atenção para a situação dos outros estágios (a soma das cargas horárias deve ser igual a {}h):\n'.format(
                self.instance.matricula_diario.diario.componente_curricular.componente_curricular_associado.get_carga_horaria_total()
            )
            mensagem = mensagem + '<table><thead><tr><th>Escola</th><th>Carga Horária Já Registrada</th><th>Situação</th></thead><tbody>'
            for estagio_docente in self.instance.matricula_diario.estagiodocente_set.exclude(pk=self.instance.pk):
                mensagem = mensagem + '<tr> <td>{}</td> <td>{}</td> <td>{}</td> </tr>'.format(
                    estagio_docente.escola, format_(estagio_docente.ch_final), estagio_docente.get_situacao_display()
                )
            mensagem = mensagem + '</tbody></table>'
            self.fields['ch_final'].help_text = mensagem

    fieldsets = (('Documentação', {'fields': ('avaliacao_do_orientador', 'avaliacao_do_professor_colaborador', 'portfolio')}), ('Documentação', {'fields': ('ch_final',)}))

    def clean(self):
        if not self.instance.visitaestagiodocente_set.exists():
            raise forms.ValidationError('Para encerrar estágio docente é necessário que o professor orientador tenha feito o cadastro de pelo menos uma visita.')


class EncerrarEstagioDocenteNaoConcluidoForm(forms.ModelFormPlus):
    estagio_nao_concluido = forms.BooleanField(label='Estágio não concluído', help_text='O estágio não foi concluído pelo aluno.', required=False)

    class Meta:
        model = EstagioDocente
        fields = ('estagio_nao_concluido',)

    fieldsets = (('Encerrar sem conclusão', {'fields': ('estagio_nao_concluido',)}),)

    def clean(self):
        if not self.cleaned_data.get('estagio_nao_concluido'):
            raise ValidationError('Para encerrar o estágio por não conclusão marque a opção estágio não concluído.')

    def save(self, *args, **kwargs):
        if self.cleaned_data.get('estagio_nao_concluido'):
            self.instance.encerrar_sem_conclusao()


class RegistrarMundancaEscolaEstagioDocenteForm(forms.ModelFormPlus):
    class Meta:
        model = EstagioDocente
        fields = ('data_inicio', 'data_fim', 'justificativa', 'ch_final')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['justificativa'].required = True
        self.fields['ch_final'].required = True

    fieldsets = (
        ('Registrar Período Cursado na Escola Anterior', {'fields': (('data_inicio', 'data_fim'),)}),
        ('Justificativa', {'fields': ('justificativa',)}),
        ('Registrar Carga Horária Cursada na Escola Anterior', {'fields': ('ch_final',)}),
    )

    def save(self, *args, **kwargs):
        self.instance.situacao = EstagioDocente.SITUACAO_MUDANCA
        self.instance.save()
        return super().save(*args, **kwargs)


class EnviarAvaliacaoEstagioDocenteForm(forms.ModelFormPlus):
    class Meta:
        model = EstagioDocente
        fields = ('avaliacao_do_orientador',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    fieldsets = (('Documentação', {'fields': ('avaliacao_do_orientador',)}),)

    def clean(self):
        if self.instance.situacao == EstagioDocente.SITUACAO_ENCERRADO:
            raise forms.ValidationError('Estágio já encerrado.')


class AcessoResponsavelForm(forms.FormPlus):
    SUBMIT_LABEL = 'Acessar'

    matricula = forms.CharField(label='Matrícula', help_text='Informe a matrícula do aluno.', widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    chave = forms.CharField(label='Chave', help_text='Informe a chave de acesso do aluno.', widget=forms.PasswordInput(attrs={'autocomplete': 'off'}))

    recaptcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recaptcha'].public_key = settings.RECAPTCHA_PUBLIC_KEY
        self.fields['recaptcha'].private_key = settings.RECAPTCHA_PRIVATE_KEY

    def get_chave(self, matricula):
        qs = Aluno.objects.filter(matricula=matricula)
        if qs.exists():
            return qs[0].get_chave_responsavel()
        return None

    def clean(self):
        matricula = self.cleaned_data.get('matricula')
        chave = self.cleaned_data.get('chave')
        if matricula and chave:
            if chave.lower() != self.get_chave(matricula):
                raise ValidationError('Chave de acesso é incompatível com matrícula do aluno.')
        return self.cleaned_data


class DispensaConvocacaoENADEForm(forms.ModelFormPlus):
    SUBMIT_LABEL = 'Salvar'

    class Meta:
        model = RegistroConvocacaoENADE
        fields = ('tipo_convocacao', 'convocacao_enade', 'justificativa_dispensa')

    def __init__(self, aluno, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['convocacao_enade'].queryset = self.fields['convocacao_enade'].queryset.filter(
            pk__in=ConvocacaoENADE.objects.all().order_by('-id').values_list('pk', flat=True)
        )
        choices = []
        if aluno.get_enade_ingressante() is None:
            choices.append((RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE, 'Ingressante'))
        if aluno.get_enade_concluinte() is None:
            choices.append((RegistroConvocacaoENADE.TIPO_CONVOCACAO_CONCLUINTE, 'Concluinte'))
        self.fields['tipo_convocacao'].choices = choices


class RequerimentoForm(forms.ModelFormPlus):
    class Meta:
        model = Requerimento
        exclude = ('situacao', 'deferido', 'observacao')

    class Media:
        js = ('/static/edu/js/RequerimentoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        automatizados = [choice[0] for choice in Requerimento.TIPO_AUTOMATIZADO_CHOICES]
        choices = []
        for choice in Requerimento.TIPO_CHOICES:
            if choice[0] not in automatizados:
                choices.append(choice)
        self.fields['tipo'].choices = choices

    def save(self, *args, **kwargs):
        conteudo = """
Caro(a) aluno(a),

Foi realizado o cadastro do seu requerimento para {}. Para mais informações procure a secretaria acadêmica.

""".format(
            self.instance.get_tipo_display()
        )
        mensagem = Mensagem()
        mensagem.remetente = self.request.user
        mensagem.assunto = f'Novo Requerimento - {self.instance.get_tipo_display()}'
        mensagem.conteudo = conteudo
        mensagem.via_suap = True
        mensagem.via_email = False
        mensagem.save()
        mensagem.destinatarios.add(self.instance.aluno.pessoa_fisica.user)
        mensagem.save()
        return super().save(*args, **kwargs)


class RequerimentoMatriculaDiarioForm(forms.ModelFormPlus):
    class Meta:
        model = RequerimentoMatriculaDisciplina
        fields = ('descricao', 'diario')

    def __init__(self, aluno, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.aluno = aluno
        self.instance.data = datetime.date.today()
        mp = aluno.get_ultima_matricula_periodo()
        qs_diario = Diario.objects.filter(ano_letivo=mp.ano_letivo, periodo_letivo=mp.periodo_letivo, turma__curso_campus__modalidade=aluno.curso_campus.modalidade, turma__curso_campus_id=aluno.curso_campus.id)
        qs_diario = qs_diario.exclude(componente_curricular__componente_id__in=aluno.get_ids_componentes_cumpridos()).exclude(componente_curricular__componente_id__in=aluno.get_ids_componentes_cursando())
        self.fields['diario'].queryset = qs_diario
        self.fields['diario'].required = True


class RequerimentoCancelamentoDisciplinaForm(forms.ModelFormPlus):
    matriculas_diario = forms.MultipleChoiceField(label='Disciplinas', widget=forms.CheckboxSelectMultiple())

    class Meta:
        model = RequerimentoCancelamentoDisciplina
        fields = ('descricao', 'matriculas_diario')

    def __init__(self, aluno, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.aluno = aluno
        self.instance.data = datetime.date.today()
        qs = aluno.get_ultima_matricula_periodo().matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO)
        choices = []
        for md in qs:
            choices.append((md.pk, md.diario.componente_curricular.componente.descricao_historico))
        self.fields['matriculas_diario'].choices = choices

    def clean_matriculas_diario(self):
        pks = self.cleaned_data['matriculas_diario']
        matriculas_diario = MatriculaDiario.objects.filter(pk__in=pks)
        for matricula_diario in matriculas_diario:
            matricula_diario.cancelar(False)
        return matriculas_diario


class AvaliacaoRequerimentoForm(forms.ModelFormPlus):
    TITLE = 'Alterar Situação'

    deferido = forms.ChoiceField(label='Deferido', choices=(('None', '-----'), (True, 'Sim'), (False, 'Não')), required=False)

    class Meta:
        model = Requerimento
        fields = ('deferido', 'situacao', 'observacao')

    def clean_situacao(self):
        if self.cleaned_data.get('deferido') is not None:
            if self.cleaned_data.get('situacao') != 'Arquivado':
                raise forms.ValidationError('A situação do requerimento deve ser "Arquivado"')
        if self.cleaned_data.get('situacao') == 'Arquivado' and self.cleaned_data.get('deferido') == 'None':
            raise forms.ValidationError('É necessário deferir ou indeferir o requerimento antes de arquivá-lo.')
        return self.cleaned_data.get('situacao')

    def save(self, user, *args, **kwargs):
        self.instance.atendente = user
        instance = super().save(*args, **kwargs)
        self.instance.enviar_email()
        return instance


class BuscarAlunoForm(RedirectForm):
    matricula = forms.CharFieldPlus(label='Matrícula')

    def processar(self, request):
        matricula = self.cleaned_data.get('matricula')
        senha = self.data.get('senha')
        qs = Aluno.objects.filter(matricula=matricula)
        if qs.exists() and auth.authenticate(username=matricula, password=senha):
            request.session['matricula-servico-impressao'] = str(qs[0].pk)
            request.session.save()
            return qs[0]
        return None


class ObservacaoForm(forms.ModelForm):
    class Meta:
        model = Observacao
        exclude = ('aluno', 'usuario', 'data')

    def __init__(self, aluno, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aluno = aluno
        self.usuario = usuario

    def save(self, *args, **kwargs):
        self.instance.aluno = self.aluno
        self.instance.usuario = self.usuario
        self.instance.data = datetime.datetime.now()
        self.instance.save()


class ObservacaoDiarioForm(forms.ModelForm):
    class Meta:
        model = ObservacaoDiario
        exclude = ('diario', 'usuario', 'data')

    def __init__(self, diario, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diario = diario
        self.usuario = usuario

    def save(self, *args, **kwargs):
        self.instance.diario = self.diario
        self.instance.usuario = self.usuario
        self.instance.data = datetime.datetime.now()
        self.instance.save()


class PremiacaoForm(forms.ModelForm):
    class Meta:
        model = Premiacao
        exclude = ('aluno',)

    def __init__(self, aluno, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aluno = aluno

    def save(self, *args, **kwargs):
        self.instance.aluno = self.aluno
        self.instance.save()


class MedidaDisciplinarForm(forms.ModelForm):
    class Meta:
        model = MedidaDisciplinar
        exclude = ('aluno',)

    def __init__(self, aluno, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aluno = aluno

    def save(self, *args, **kwargs):
        self.instance.aluno = self.aluno
        self.instance.save()


class FormaIngressoForm(forms.ModelForm):
    class Meta:
        model = FormaIngresso
        exclude = ()

    def clean_racas(self):
        if self.cleaned_data['programa_vaga_etinico'] and not self.cleaned_data['racas']:
            raise forms.ValidationError('Informe as raças/etnias correspondente.')
        return self.cleaned_data['racas']


class RelatorioEducacensoForm(forms.FormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.campi().all(), label='Campus')
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    ignorar_erros = forms.BooleanField(
        label='Ignorar Erros',
        required=False,
        help_text='Marque essa opção caso deseje que o arquivo de exportação seja gerado independentemente se todos os registros de alunos e professores tiverem sido validados ou não.',
    )

    def processar(self):
        ano_letivo = self.cleaned_data['ano_letivo']
        uo = self.cleaned_data['uo']
        ignorar_erros = self.cleaned_data['ignorar_erros']
        return tasks.exportar_dados_educacenso(ano_letivo.ano, uo, ignorar_erros)


class RelatorioEducacensoEtapa2Form(forms.FormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.campi().all(), label='Campus')
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    ignorar_erros = forms.BooleanField(
        label='Ignorar Erros',
        required=False,
        help_text='Marque essa opção caso deseje que o arquivo de exportação seja gerado independentemente se todos os registros de alunos e professores tiverem sido validados ou não.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ignorar_erros'].initial = True

    def processar(self):
        ano_letivo = self.cleaned_data['ano_letivo']
        uo = self.cleaned_data['uo']
        ignorar_erros = self.cleaned_data['ignorar_erros']
        return tasks.exportar_dados_educacenso2(ano_letivo.ano, uo, ignorar_erros)


class ImportarEducacensoEtapa2Form(forms.FormPlus):
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    arquivo = forms.FileFieldPlus(label='Arquivo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def processar(self):
        ano_letivo = self.cleaned_data['ano_letivo']
        conteudo = self.cleaned_data['arquivo'].read().decode('latin1')
        return tasks.importar_dados_educacenso2(ano_letivo, conteudo)


class RelatorioCoordenacaoCursoForm(forms.FormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.campi(), label='Campus', required=False)
    diretoria = forms.ModelChoiceField(Diretoria.objects, label='Diretoria', required=False)
    modalidades = forms.MultipleModelChoiceFieldPlus(Modalidade.objects, label='Modalidades', required=False, widget=CheckboxSelectMultiplePlus())
    apenas_ativo = forms.BooleanField(label='Apenas Ativos', required=False)

    def processar(self):
        uo = self.cleaned_data['uo']
        diretoria = self.cleaned_data['diretoria']
        apenas_ativo = self.cleaned_data['apenas_ativo']
        modalidades = self.cleaned_data['modalidades']
        qs = CursoCampus.objects.all()
        if apenas_ativo:
            qs = qs.filter(ativo=True)
        if diretoria:
            qs = qs.filter(diretoria=diretoria)
        if uo:
            qs = qs.filter(diretoria__setor__uo=uo)
        if modalidades:
            qs = qs.filter(modalidade__in=modalidades)
        return qs


class AtualizarEmailAlunoForm(forms.FormPlus):
    email_secundario = forms.EmailField(max_length=255, required=False, label='E-mail Secundário')
    email_academico = forms.EmailField(max_length=255, required=False, label='E-mail Acadêmico')
    email_google_classroom = forms.EmailField(max_length=255, required=False, label='E-mail Google ClassRoom')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.aluno = kwargs.pop('aluno')

        super().__init__(*args, **kwargs)

        if self.aluno.get_vinculo() is None:
            self.aluno.save()  # força criação de vínculo
        self.fields['email_secundario'].initial = self.aluno.get_vinculo().pessoa.email_secundario
        self.fields['email_academico'].initial = self.aluno.email_academico
        self.fields['email_google_classroom'].initial = self.aluno.email_google_classroom
        cra = UsuarioGrupo.objects.filter(
            user=self.request.user, group__name='Coordenador de Registros Acadêmicos',
            setores__uo=self.aluno.curso_campus.diretoria.setor.uo_id
        ).exists()
        if not self.request.user.has_perm('rh.pode_editar_email_secundario_aluno') and not cra:
            del self.fields['email_secundario']
        if not self.request.user.has_perm('rh.pode_editar_email_academico'):
            del self.fields['email_academico']
        if not self.request.user.has_perm('rh.pode_editar_email_google_classroom'):
            del self.fields['email_google_classroom']

    def clean_email_secundario(self):
        if not Configuracao.get_valor_por_chave('comum', 'permite_email_institucional_email_secundario') and Configuracao.eh_email_institucional(
            self.cleaned_data['email_secundario']
        ):
            raise forms.ValidationError("Escolha um e-mail que não seja institucional.")
        return self.cleaned_data['email_secundario']

    def clean_email_academico(self):
        email_academico = self.cleaned_data['email_academico']
        if email_academico:
            if Aluno.objects.exclude(pk=self.aluno.id).filter(email_academico=email_academico).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if Servidor.objects.filter(email_academico=email_academico).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if EmailBlockList.objects.filter(email=email_academico).exists():
                raise forms.ValidationError("O e-mail informado está bloqueado.")
            if not settings.DEBUG and 'ldap_backend' in settings.INSTALLED_APPS:
                ldap_conf = LdapConf.get_active()
                usernames = ldap_conf.get_usernames_from_principalname(email_academico)
                if usernames and self.aluno.matricula not in usernames:
                    raise forms.ValidationError("O e-email informado já é utilizado por outro usuário.")
        return email_academico

    def clean_email_google_classroom(self):
        if self.cleaned_data['email_google_classroom']:
            if Aluno.objects.exclude(pk=self.aluno.id).filter(email_google_classroom=self.cleaned_data['email_google_classroom']).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if Servidor.objects.filter(email_google_classroom=self.cleaned_data['email_google_classroom']).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if PrestadorServico.objects.filter(email_google_classroom=self.cleaned_data['email_google_classroom']).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if EmailBlockList.objects.filter(email=self.cleaned_data['email_google_classroom']).exists():
                raise forms.ValidationError("O e-mail informado está bloqueado.")
        return self.cleaned_data['email_google_classroom']

    def save(self):
        if 'email_academico' in self.cleaned_data:
            self.aluno.email_academico = self.cleaned_data.get('email_academico')
        if 'email_google_classroom' in self.cleaned_data:
            self.aluno.email_google_classroom = self.cleaned_data.get('email_google_classroom')
        self.aluno.save()
        if 'email_secundario' in self.cleaned_data:
            Pessoa.objects.filter(pk=self.aluno.get_vinculo().pessoa.id).update(email_secundario=self.cleaned_data.get('email_secundario'))


class EditarLegislacaoForm(forms.ModelForm):
    class Meta:
        model = MatrizCurso
        fields = ('resolucao_criacao', 'resolucao_data', 'reconhecimento_texto', 'reconhecimento_data')

    fieldsets = (('Ato Normativo', {'fields': ('resolucao_criacao', 'resolucao_data')}), ('Ato de Reconhecimento', {'fields': ('reconhecimento_texto', 'reconhecimento_data')}))


class DisciplinaIngressoProfessorForm(forms.ModelFormPlus):
    disciplina = forms.ModelChoiceFieldPlus(
        Disciplina.objects.all(), label='Disciplina de Ingresso', widget=AutocompleteWidget(search_fields=Disciplina.SEARCH_FIELDS), required=True
    )

    class Meta:
        model = Professor
        fields = ('disciplina',)


class ExportarDadosPNP(forms.Form):
    RENDA = 'Renda dos alunos'
    ETNIA = 'Etnia dos alunos'
    TITULACAO = 'Titulação dos servidores'

    tipo = forms.ChoiceField(label='Tipo', choices=[[x, x] for x in (RENDA, ETNIA, TITULACAO)])
    cpfs = forms.CharField(label='CPFs', widget=forms.Textarea(), help_text='Informar CPFs separados por linha.')

    def clean_cpfs(self):
        cpfs = self.cleaned_data['cpfs']
        for cpf in cpfs.split('\n'):
            if len(cpf.strip()) < 11:
                cpf = cpf.strip().zfill(11)
            if len(cpf.strip()) != 11 and len(cpf.strip()) != 14:
                raise forms.ValidationError(f'O CPF "{cpf}" é inválido')
        return cpfs

    def processar(self):
        def remover_pontuacao(cpf):
            return cpf.replace('.', '').replace('-', '')
        tipo = self.cleaned_data['tipo']
        cpfs = [mask_cpf(remover_pontuacao(cpf)) for cpf in self.cleaned_data['cpfs'].split('\n') if cpf]
        lista = []
        if tipo == ExportarDadosPNP.RENDA and 'ae' in settings.INSTALLED_APPS:
            Caracterizacao = apps.get_model('ae', 'Caracterizacao')
            qs = Caracterizacao.objects.filter(aluno__pessoa_fisica__cpf__in=cpfs).order_by('-id')
            for caracterizacao in qs:
                cpf = caracterizacao.aluno.pessoa_fisica.cpf
                if cpf in cpfs:
                    renda_per_capita = caracterizacao.renda_per_capita
                    s = 'Nao Declarada'
                    if renda_per_capita is not None:
                        if renda_per_capita <= 0.5:
                            s = '0<RFP<=0,5'
                        elif renda_per_capita >= 0.5 and renda_per_capita <= 1.0:
                            s = '0,5<RFP<=1'
                        elif renda_per_capita >= 1.0 and renda_per_capita <= 1.5:
                            s = '1,0<RFP<=1,5'
                        elif renda_per_capita >= 1.5 and renda_per_capita <= 2.5:
                            s = '1,5<RFP<=2,5'
                        elif renda_per_capita >= 2.5 and renda_per_capita <= 3.5:
                            s = '2,5<RFP<=3,5'
                        elif renda_per_capita >= 3.5:
                            s = 'RFP>3,5'
                    lista.append([remover_pontuacao(cpf), s])
                    cpfs.remove(cpf)
            for cpf in cpfs:
                lista.append([remover_pontuacao(cpf), 'Nao Declarada'])
        elif tipo == ExportarDadosPNP.ETNIA and 'ae' in settings.INSTALLED_APPS:
            Caracterizacao = apps.get_model('ae', 'Caracterizacao')
            for cpf in cpfs:
                etnia = Caracterizacao.objects.filter(aluno__pessoa_fisica__cpf=remover_pontuacao(cpf)).exclude(raca__isnull=True).exclude(raca__descricao='Não declarado').order_by('-id').values_list('raca__descricao', flat=True).first()
                if etnia is None:
                    etnia = Aluno.objects.filter(pessoa_fisica__cpf=cpf).exclude(pessoa_fisica__raca__isnull=True).exclude(pessoa_fisica__raca__descricao='Não declarado').order_by('-id').values_list('pessoa_fisica__raca__descricao', flat=True).first()
                    if etnia is None:
                        etnia = 'Nao Declarada'
                lista.append([remover_pontuacao(cpf), retira_acentos(etnia)])
        elif tipo == ExportarDadosPNP.TITULACAO:
            qs = Servidor.objects.ativos().filter(cpf__in=cpfs)
            rsc = ''
            for cpf, nome_siape, nome_suap, titulacao_edu, nivel_escolaridade in qs.values_list(
                'cpf', 'titulacao__nome', 'titulacao__titulo_masculino', 'professor__titulacao', 'nivel_escolaridade__nome'
            ):
                if nome_siape:
                    if 'RSC-I ' in nome_siape:
                        rsc = 'RSC-I'
                    elif 'RSC-II ' in nome_siape:
                        rsc = 'RSC-II'
                    elif 'RSC-III ' in nome_siape:
                        rsc = 'RSC-III'
                titulacao = (nome_suap or titulacao_edu or nivel_escolaridade or 'Nao Declarada').upper()
                if 'FUNDAMENTAL' in titulacao:
                    titulacao = 'ENSINO FUNDAMENTAL'
                if 'MÉDIO' in titulacao or 'MEDIO' in titulacao:
                    titulacao = 'ENSINO MEDIO'
                if 'TÉCNICO' in titulacao or 'TECNICO' in titulacao:
                    titulacao = 'TECNICO'
                if 'GRADUA' in titulacao:
                    titulacao = 'GRADUACAO'
                if 'APERFEI' in titulacao:
                    titulacao = 'APERFEICOAMENTO'
                if 'ESPECIAL' in titulacao:
                    titulacao = 'ESPECIALIZACAO'
                if 'MESTR' in titulacao:
                    titulacao = 'MESTRADO'
                if 'DOUTOR' in titulacao:
                    titulacao = 'DOUTORADO'
                if ('PÓS' in titulacao or 'POS' in titulacao) and 'DOUTOR' in titulacao:
                    titulacao = 'POS-DOUTORADO'
                lista.append([remover_pontuacao(cpf), titulacao, rsc])
        return CsvResponse(lista, delimiter=';')


class IndeferirRequerimentoForm(forms.ModelFormPlus):
    class Meta:
        model = Requerimento
        fields = ('observacao',)


class AgendarAvaliacaoForm(forms.ModelFormPlus):
    class Meta:
        model = ItemConfiguracaoAvaliacao
        fields = ['data']


class TopicoDiscussaoForm(forms.ModelFormPlus):
    etapa = forms.ChoiceField(label='Etapa', choices=[[1, 'Etapa 1'], [2, 'Etapa 2'], [3, 'Etapa 3'], [4, 'Etapa 4']])

    class Meta:
        model = TopicoDiscussao
        fields = ('titulo', 'etapa', 'descricao')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.initial.get('etapa'):
            self.fields['etapa'].widget = forms.HiddenInput()

    def save(self, diario, etapa, *args, **kwargs):
        self.instance.diario = diario
        self.instance.data = datetime.date.today()
        self.instance.user = self.request.user
        if etapa:
            self.instance.etapa = etapa
        return super().save(*args, **kwargs)


class RespostaDiscussaoForm(forms.ModelFormPlus):
    class Meta:
        model = RespostaDiscussao
        fields = ('comentario',)

    def save(self, topico, *args, **kwargs):
        self.instance.topico = topico
        self.instance.data = datetime.date.today()
        self.instance.user = self.request.user
        return super().save(*args, **kwargs)


class TrabalhoForm(forms.ModelFormPlus):
    class Meta:
        model = Trabalho
        fields = ('titulo', 'descricao', 'data_limite_entrega', 'arquivo')

    def save(self, diario, etapa, *args, **kwargs):
        self.instance.diario = diario
        self.instance.etapa = etapa
        self.instance.data_solicitacao = datetime.date.today()
        self.instance.user = self.request.user
        return super().save(*args, **kwargs)


class EntregaTrabalhoForm(forms.ModelFormPlus):
    class Meta:
        model = EntregaTrabalho
        fields = ('comentario', 'arquivo')

    def save(self, trabalho, aluno, *args, **kwargs):
        self.instance.trabalho = trabalho
        if self.instance.trabalho.pode_entregar_trabalho():
            md = MatriculaDiario.objects.get(diario=trabalho.diario, matricula_periodo__aluno=aluno)
            if not EntregaTrabalho.objects.filter(trabalho=trabalho, matricula_diario=md).exists():
                self.instance.matricula_diario = md
                self.instance.data_solicitacao = datetime.date.today()
                return super().save(*args, **kwargs)


class AutorizacaoForm(forms.ModelFormPlus):
    class Meta:
        model = Autorizacao
        fields = 'tipo', 'data', 'numero', 'numero_publicacao', 'data_publicacao', 'veiculo_publicacao', 'secao_publicacao', 'pagina_publicacao', 'funcionamento_tipo', 'funcionamento_data', 'funcionamento_numero'

    fieldsets = (
        ('Dados Gerais', {'fields': ('tipo', ('data', 'numero'), 'adequacao')}),
        ('Funcionamento', {'fields': ('funcionamento_tipo', ('funcionamento_data', 'funcionamento_numero'))}),
        ('Dados da Publicação', {'fields': ('veiculo_publicacao', ('numero_publicacao', 'data_publicacao'), ('pagina_publicacao', 'secao_publicacao'))}),
    )


class ReconhecimentoForm(forms.ModelFormPlus):
    class Meta:
        model = Reconhecimento
        fields = 'tipo', 'data', 'numero', 'renovacao', 'veiculo_publicacao', 'numero_publicao', 'data_publicacao', 'pagina_publicao', 'secao_publicao', 'validade'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['validade'].required = False

    fieldsets = (
        ('Dados do Documento', {'fields': ('tipo', ('data', 'numero'), ('validade', 'renovacao'))}),
        ('Dados da Publicação', {'fields': ('veiculo_publicacao', ('numero_publicao', 'data_publicacao'), ('pagina_publicao', 'secao_publicao'))}),
    )


class HorarioAtividadeExtraForm(forms.ModelFormPlus):
    class Meta:
        model = HorarioAtividadeExtra
        fields = ('descricao_atividade', 'tipo_atividade')

    def __init__(self, *args, **kwargs):
        self.matricula_periodo = kwargs.pop('matricula_periodo')
        super().__init__(*args, **kwargs)

    def clean(self):
        if not dict(self.request.POST).get("horario"):
            raise forms.ValidationError('É necessário informar pelo menos um horário.')
        return self.cleaned_data

    def save(self, horarios, *args, **kwargs):
        descricao_atividade = self.cleaned_data.get('descricao_atividade')
        tipo_atividade = self.cleaned_data.get('tipo_atividade')
        HorarioAtividadeExtra.objects.filter(descricao_atividade=descricao_atividade, tipo_atividade=tipo_atividade, matricula_periodo=self.matricula_periodo).delete()
        if horarios:
            for horario in horarios:
                horario_split = horario.split(";")
                horario_aula = HorarioAula.objects.get(pk=horario_split[0])
                dia_semana = horario_split[1]
                HorarioAtividadeExtra.objects.create(
                    descricao_atividade=descricao_atividade,
                    tipo_atividade=tipo_atividade,
                    matricula_periodo=self.matricula_periodo,
                    dia_semana=dia_semana,
                    horario_aula=horario_aula,
                )
        else:
            raise ValidationError('É necessário informar pelo menos um horário.')


class EditarHorarioAtividadeExtraForm(forms.ModelFormPlus):

    atividade_tipo = forms.CharField(label='Tipo de Atividade', widget=forms.TextInput(attrs=dict(readonly='readonly')), required=False)

    class Meta:
        model = HorarioAtividadeExtra
        fields = ('descricao_atividade', 'atividade_tipo')

    def __init__(self, *args, **kwargs):
        self.matricula_periodo = kwargs.pop('matricula_periodo')
        super().__init__(*args, **kwargs)
        self.fields['descricao_atividade'].widget = forms.TextInput(attrs=dict(readonly='readonly'))
        self.fields['atividade_tipo'].initial = self.instance.get_tipo_atividade_display()

    def save(self, horarios, *args, **kwargs):
        HorarioAtividadeExtra.objects.filter(
            descricao_atividade=self.instance.descricao_atividade, tipo_atividade=self.instance.tipo_atividade, matricula_periodo=self.matricula_periodo
        ).delete()
        if horarios:
            for horario in horarios:
                horario_split = horario.split(";")
                horario_aula = HorarioAula.objects.get(pk=horario_split[0])
                dia_semana = horario_split[1]
                HorarioAtividadeExtra.objects.create(
                    descricao_atividade=self.instance.descricao_atividade,
                    tipo_atividade=self.instance.tipo_atividade,
                    matricula_periodo=self.matricula_periodo,
                    dia_semana=dia_semana,
                    horario_aula=horario_aula,
                )


class EstatisticaTurmaForm(forms.Form):

    SUBMIT_LABEL = 'Exibir Estatística'

    etapas = forms.MultipleChoiceField(
        choices=[[1, '1ª Etapa'], [2, '2ª Etapa'], [3, '3ª Etapa'], [4, '4ª Etapa'], [5, 'Final']], label='', widget=forms.CheckboxSelectMultiplePlus()
    )
    diarios = forms.MultipleModelChoiceField(Diario.objects.none(), label='', widget=forms.CheckboxSelectMultiplePlus())
    abreviar = forms.BooleanField(label='Abreviar', help_text='Exibir "sigla" do componente ao invés da descrição completa do diário.', required=False)

    fieldsets = (('Etapas', {'fields': ('etapas',)}), ('Diários', {'fields': ('diarios',)}), ('Exibição', {'fields': ('abreviar',)}))


class AtividadeCurricularExtensaoForm(forms.ModelForm):
    ano_letivo = forms.ModelChoiceFieldPlus(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, label='Período Letivo')

    fieldsets = (('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo', 'carga_horaria'), 'descricao')}),)

    def __init__(self, aluno, *args, **kwargs):
        self.aluno = aluno
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['ano_letivo'].initial = self.instance.matricula_periodo.ano_letivo.pk
            self.fields['periodo_letivo'].initial = self.instance.matricula_periodo.periodo_letivo

    def clean(self):
        matricula_periodo = self.aluno.matriculaperiodo_set.filter(ano_letivo=self.cleaned_data.get('ano_letivo'), periodo_letivo=self.cleaned_data.get('periodo_letivo'))
        if not matricula_periodo:
            raise forms.ValidationError('Ano/Período letivo inválido.')
        return self.cleaned_data

    class Meta:
        model = AtividadeCurricularExtensao
        fields = ('descricao', 'carga_horaria')

    def save(self, *args, **kwargs):
        self.instance.matricula_periodo = self.aluno.matriculaperiodo_set.filter(
            ano_letivo=self.cleaned_data.get('ano_letivo'), periodo_letivo=self.cleaned_data.get('periodo_letivo')
        ).first()
        super().save(*args, **kwargs)


class ImportarMaterialAulaForm(forms.FormPlus):
    materiais_aula = forms.MultipleModelChoiceField(MaterialAula.objects.none(), required=False, label='', widget=RenderableSelectMultiple('widgets/materiais_aula_widget.html'))

    SUBMIT_LABEL = 'Importar Materiais Selecionados'

    def __init__(self, professor, *args, **kwargs):
        self.professor = professor
        super().__init__(*args, **kwargs)
        self.fields['materiais_aula'].queryset = professor.get_materiais_aula_outros_vinculos()

    def processar(self):
        for material_aula in self.cleaned_data['materiais_aula']:
            material_aula.pk = None
            material_aula.professor = self.professor
            material_aula.save()


class ConfigurarAmbienteVirtualDiarioForm(forms.ModelFormPlus):
    fieldsets = (('Ambiente Virtual', {'fields': ('url_ambiente_virtual', )}),)

    class Meta:
        model = Diario
        fields = ('url_ambiente_virtual',)


class IniciarSessaoAssinaturaSenhaForm(forms.FormPlus):
    senha = forms.CharField(label='Senha do SUAP', widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data and not auth.authenticate(username=self.request.user.username, password=cleaned_data['senha']):
            raise forms.ValidationError('A senha não confere com a do usuário logado.')
        return cleaned_data


class IniciarSessaoAssinaturaEletronicaForm(forms.FormPlus):
    senha = forms.CharField(label='Senha do SUAP', widget=forms.PasswordInput)
    certificado = forms.ModelChoiceFieldPlus(CertificadoDigital.objects, label='Certificado')
    senha_certificado = forms.CharField(label='Senha do Certificado', widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['certificado'].queryset = CertificadoDigital.objects.filter(user=self.request.user)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data and not auth.authenticate(username=self.request.user.username, password=cleaned_data['senha']):
            raise forms.ValidationError('A senha não confere com a do usuário logado.')
        try:
            certificado = cleaned_data['certificado']
            senha_certificado = cleaned_data['senha_certificado']
            local_filename = cache_file(certificado.arquivo.name)
            validade = signer.expiration_date(local_filename, senha_certificado)
            os.unlink(local_filename)
            if validade < datetime.date.today():
                raise forms.ValidationError('Certificado com prazo de validade expirado')
            self.request.session['sessao_assinatura_eletronica'] = (certificado.pk, senha_certificado)
            self.request.session.save()
        except BaseException as e:
            print(e)
            raise forms.ValidationError('Senha do certificado inválida.')
        return cleaned_data


class RevogarDiplomaForm(forms.FormPlus):
    motivo = forms.CharFieldPlus(label='Motivo', widget=forms.Textarea())


class ImportarAutenticacaoSistecForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus(label='Arquivo CSV')

    def processar(self):
        c = 0
        file_path = tempfile.mktemp()
        temp = open(file_path, 'wb+')
        temp.write(self.cleaned_data['arquivo'].read())
        temp.close()
        csv_reader = csv.reader(open(file_path, encoding='iso-8859-1'), delimiter=";", quotechar='"')
        for row in csv_reader:
            cpf, codigo_unidade, codigo_curso, codigo_autenticacao = row[1], row[16], row[21], row[17]
            CodigoAutenticadorSistec.objects.get_or_create(
                codigo_unidade=codigo_unidade,
                codigo_curso=codigo_curso,
                cpf=mask_cpf(cpf),
                codigo_autenticacao=codigo_autenticacao
            )
            c += 1
        return c


class UploadAlunoArquivoUnicoForm(forms.ModelFormPlus):
    conteudo = forms.FileFieldPlus(
        required=True,
        label='Arquivo',
        filetypes=['pdf', 'jpg', 'png']
    )
    tipo = forms.ModelChoiceFieldPlus(
        TipoAlunoArquivo.objects.filter(ativo=True).exclude(nome="Outro"),
        required=True,
        label='Tipo',
        widget=AutocompleteWidget(search_fields=TipoAlunoArquivo.SEARCH_FIELDS)
    )

    class Meta:
        model = ArquivoUnico
        fields = 'conteudo',

    def save(self, *args, **kwargs):
        kwargs.update(commit=False)
        return super().save(*args, **kwargs)


class AvaliarArquivoUnicoForm(forms.ModelFormPlus):
    validado = forms.ChoiceField(label='Validado', choices=[[True, 'Sim'], [False, 'Não']], initial=True, widget=forms.RadioSelect(), help_text="Esta escolha não poderá ser desfeita após salvar a avaliação.")

    class Meta:
        model = AlunoArquivo
        fields = 'validado', 'observacao',

    def save(self, *args, **kwargs):
        kwargs.update(commit=False)
        return super().save(*args, **kwargs)


class CertificadoDiplomaForm(forms.ModelFormPlus):

    class Meta:
        model = CertificadoDiploma
        fields = ('aluno',
                  # 'processo',
                  )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aluno'].queryset = Aluno.objects.filter(
            matriz__isnull=False,
            situacao__in=(SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO),
            curso_campus__modalidade__nivel_ensino__pk__in=[
                NivelEnsino.GRADUACAO, NivelEnsino.POS_GRADUACAO, NivelEnsino.MEDIO
            ]
        )


class DevolverPlanoEnsino(forms.FormPlus):
    justificativa = forms.CharField(label='Justificativa', widget=forms.Textarea())


class DefinirPlanoEstudoForm(forms.FormPlus):

    def __init__(self, *args, **kwargs):
        self.plano_estudo = kwargs.pop('plano_estudo')
        super().__init__(*args, **kwargs)
        aluno = self.plano_estudo.pedido_matricula.matricula_periodo.aluno
        ignorar_ids = []
        ignorar_ids.extend(aluno.get_ids_componentes_cumpridos())
        ignorar_ids.extend(aluno.get_ids_componentes_cursando())
        qs = aluno.matriz.componentecurricular_set.filter(optativo=False).exclude(componente__id__in=ignorar_ids)
        self.qs = qs.order_by('id')
        self.fieldsets = []
        anos_letivos = Ano.objects.filter(ano__gte=date.today().year, ano__lte=date.today().year + 5).order_by('ano')
        ids = []
        for cc in self.qs:
            ids.append(cc.id)
            item = self.plano_estudo.itemplanoestudo_set.filter(
                plano_estudo=self.plano_estudo, componente_curricular=cc
            ).first()
            ignorar_ids.append(cc.componente_id)
            ano_letivo_field_name = f'ano_letivo-{cc.pk}'
            periodo_letivo_field_name = f'periodo_letivo-{cc.pk}'
            self.fields[ano_letivo_field_name] = forms.ModelChoiceFieldPlus(anos_letivos, label='Ano Letivo', required=False)
            self.fields[periodo_letivo_field_name] = forms.ChoiceField(choices=[['', '']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False)
            self.fieldsets.append((str(cc), {'fields': ((ano_letivo_field_name, periodo_letivo_field_name),)}))
            if item:
                self.initial[ano_letivo_field_name] = item.ano_letivo_id
                self.initial[periodo_letivo_field_name] = item.periodo_letivo

        componentes_curriculares_opcionais = aluno.matriz.componentecurricular_set.filter(optativo=True).exclude(
            componente__id__in=ignorar_ids
        )
        itens = self.plano_estudo.itemplanoestudo_set.filter(
            plano_estudo=self.plano_estudo
        ).exclude(componente_curricular__id__in=ids)
        for i in range(0, 10):
            componente_curricular_field_name = f'componente_curricular--{i}'
            ano_letivo_field_name = f'ano_letivo--{i}'
            periodo_letivo_field_name = f'periodo_letivo--{i}'
            self.fields[componente_curricular_field_name] = forms.ModelChoiceFieldPlus(
                componentes_curriculares_opcionais, label='Componente Curricular', required=False
            )
            self.fields[ano_letivo_field_name] = forms.ModelChoiceFieldPlus(anos_letivos, label='Ano Letivo', required=False)
            self.fields[periodo_letivo_field_name] = forms.ChoiceField(choices=[['', '']] + PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False)
            self.fieldsets.append((
                f'Disciplina Optativa {i + 1}',
                {'fields': (componente_curricular_field_name, (ano_letivo_field_name, periodo_letivo_field_name))}
            ))
            item = itens[i] if len(itens) > i else None
            if item:
                self.initial[componente_curricular_field_name] = item.componente_curricular_id
                self.initial[ano_letivo_field_name] = item.ano_letivo_id
                self.initial[periodo_letivo_field_name] = item.periodo_letivo

    def processar(self):
        ids = []
        for cc in self.qs:
            ids.append(cc.id)
            ano_letivo_field_name = f'ano_letivo-{cc.pk}'
            periodo_letivo_field_name = f'periodo_letivo-{cc.pk}'
            item = self.plano_estudo.itemplanoestudo_set.filter(
                plano_estudo=self.plano_estudo, componente_curricular=cc
            ).first()
            if item is None:
                item = ItemPlanoEstudo(plano_estudo=self.plano_estudo, componente_curricular=cc)
            ano_letivo = self.cleaned_data.get(ano_letivo_field_name)
            periodo_letivo = self.cleaned_data.get(periodo_letivo_field_name)
            if ano_letivo and periodo_letivo:
                item.ano_letivo = ano_letivo
                item.periodo_letivo = periodo_letivo
                item.save()

        for i in range(0, 10):
            componente_curricular_field_name = f'componente_curricular--{i}'
            ano_letivo_field_name = f'ano_letivo--{i}'
            periodo_letivo_field_name = f'periodo_letivo--{i}'
            cc = self.cleaned_data.get(componente_curricular_field_name)
            item = self.plano_estudo.itemplanoestudo_set.filter(
                plano_estudo=self.plano_estudo, componente_curricular=cc
            ).first()
            if item is None:
                item = ItemPlanoEstudo(plano_estudo=self.plano_estudo, componente_curricular=cc)
            ano_letivo = self.cleaned_data.get(ano_letivo_field_name)
            periodo_letivo = self.cleaned_data.get(periodo_letivo_field_name)
            if cc and ano_letivo and periodo_letivo:
                ids.append(cc.id)
                item.ano_letivo = ano_letivo
                item.periodo_letivo = periodo_letivo
                item.save()

        self.plano_estudo.itemplanoestudo_set.filter(
            plano_estudo=self.plano_estudo
        ).exclude(componente_curricular__id__in=ids).delete()


class AvaliarPlanoEstudoForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Data')
    resultado = forms.ChoiceField(label='Resultado', choices=[['', ''], ['Homologado', 'Homologado'], ['Não-Homologado', 'Não-Homologado']])
    numero_ata = forms.CharField(label='Número da Ata')
    observacao = forms.CharField(label='Observação', required=False, widget=forms.Textarea())

    def processar(self, planos_estudo):
        planos_estudo.update(
            homologado=self.cleaned_data['resultado'] == 'Homologado',
            data_homologacao=self.cleaned_data['data'],
            observacao_homologacao=self.cleaned_data['observacao'],
            numero_ata_homologacao=self.cleaned_data['numero_ata'],
        )


class PlanoEnsinoForm(forms.ModelFormPlus):
    class Meta:
        model = PlanoEnsino
        fields = 'diario', 'ementa', 'justificativa', 'objetivo_geral', 'objetivos_especificos', 'conteudo_programatico', 'metodologia', 'informacoes_adicionais'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.diario.componente_curricular.ementa:
            self.initial['ementa'] = self.instance.diario.componente_curricular.ementa
            self.instance.ementa = self.instance.diario.componente_curricular.ementa
            self.fields['ementa'].initial = self.instance.diario.componente_curricular.ementa
            self.fields['ementa'].widget.attrs.update(readonly='readonly')


class QuestaoEducacensoForm(forms.ModelFormPlus):
    class Meta:
        model = QuestaoEducacenso
        fields = 'registro', 'numero_campo', 'nome_campo', 'tipo_resposta', 'tipo_obrigatoriedade', 'resposta_privada', 'regra_resposta'

    def __init__(self, clone=None, *args, **kwargs):
        registro = kwargs.pop('registro')
        super().__init__(*args, **kwargs)
        if registro:
            self.initial['registro'] = registro
        if clone:
            self.initial['resposta_privada'] = clone.resposta_privada
            self.initial['regra_resposta'] = clone.regra_resposta
            self.initial['tipo_resposta'] = clone.tipo_resposta
            self.initial['tipo_obrigatoriedade'] = clone.tipo_obrigatoriedade


def RespostaQuestaoEducacensoFormFactory(request, pk_questao, pk_campus=None):
    fields = dict()
    questao = QuestaoEducacenso.objects.get(pk=pk_questao)
    qs_resposta = RespostaEducacenso.objects.filter(questao__pk=pk_questao)
    if pk_campus:
        qs_resposta = qs_resposta.filter(campus__pk=pk_campus)

    label = f'{questao}'
    if questao.tipo_resposta == QuestaoEducacenso.TIPO_REPOSTA_SIM_NAO:
        fields[f'resposta_{questao.numero_campo}'] = forms.NullBooleanField(label=label)
    else:
        fields[f'resposta_{questao.numero_campo}'] = forms.IntegerFieldPlus(label=label)

    if questao.tipo_obrigatoriedade == QuestaoEducacenso.TIPO_OBRIGATORIEDADE_OBRIGATORIO:
        fields[f'resposta_{questao.numero_campo}'].required = True
    else:
        fields[f'resposta_{questao.numero_campo}'].required = False
    if questao.tipo_obrigatoriedade == QuestaoEducacenso.TIPO_OBRIGATORIEDADE_CONDICIONAL:
        fields[f'resposta_{questao.numero_campo}'].help_text = questao.regra_resposta

    if pk_campus:
        fields[f'resposta_{questao.numero_campo}'].initial = str(qs_resposta.first().resposta).lower()

    def save(self, *args, **kwargs):
        field_name = f'resposta_{questao.numero_campo}'
        qs_resposta.update(resposta=self.cleaned_data.get(field_name))

    return type('EducacensoForm', (forms.BaseForm,), {'base_fields': fields, 'METHOD': 'POST', 'SUBMIT_LABEL': 'Salvar', 'save': save, })


def RespostaEducacensoFormFactory(request, registroeducacenso_id, uo_id):
    fields = dict()
    registro = RegistroEducacenso.objects.get(pk=registroeducacenso_id)
    questionario = registro.get_questoes_para_resposta(uo_id)
    for resposta in questionario:
        label = f'{resposta.questao}'
        if resposta.questao.tipo_resposta == QuestaoEducacenso.TIPO_REPOSTA_SIM_NAO:
            fields[f'resposta_{resposta.questao.numero_campo}'] = forms.NullBooleanField(label=label)
        else:
            fields[f'resposta_{resposta.questao.numero_campo}'] = forms.IntegerFieldPlus(label=label)

        if resposta.questao.tipo_obrigatoriedade == QuestaoEducacenso.TIPO_OBRIGATORIEDADE_OBRIGATORIO:
            fields[f'resposta_{resposta.questao.numero_campo}'].required = True
        else:
            fields[f'resposta_{resposta.questao.numero_campo}'].required = False
        if resposta.questao.tipo_obrigatoriedade == QuestaoEducacenso.TIPO_OBRIGATORIEDADE_CONDICIONAL:
            fields[f'resposta_{resposta.questao.numero_campo}'].help_text = resposta.questao.regra_resposta
        if resposta.questao.resposta_privada and not request.user.has_perm('edu.add_registroeducacenso'):
            fields[f'resposta_{resposta.questao.numero_campo}'].widget.attrs.update(readonly='readonly')
            fields[f'resposta_{resposta.questao.numero_campo}'].required = False
        if resposta.resposta:
            fields[f'resposta_{resposta.questao.numero_campo}'].initial = resposta.resposta.lower()

    def save(self, *args, **kwargs):
        for resposta in questionario:
            field_name = f'resposta_{resposta.questao.numero_campo}'
            resposta.resposta = self.cleaned_data.get(field_name)
            resposta.save()

    return type('EducacensoForm', (forms.BaseForm,), {'base_fields': fields, 'METHOD': 'POST', 'SUBMIT_LABEL': 'Salvar', 'save': save, })


class InformarDadosTitulacaoForm(forms.ModelFormPlus):

    ALERT = 'De acordo com a exigência do Censo da Educação Básica (EDUCACENSO) 2022 é necessário informar a sua titulação mais elevada, instituição onde obteve a titulação, área de conhecimento e ano de conclusão.'

    titulacao = forms.ChoiceField(label='Titulação', choices=[['', '-----']] + Professor.TITULACAO_CHOICES, required=True)
    ultima_instituicao_de_titulacao = forms.CharFieldPlus(label='Instituição', required=True, help_text='Instituição onde recebeu a última titulação')
    area_ultima_titulacao = forms.ChoiceField(label='Área da Última Titulação', required=True, choices=[['', '-----']] + Professor.AREA_ULTIMA_TITULACAO_CHOICES)
    ano_ultima_titulacao = forms.ModelChoiceField(Ano.objects, label='Ano', required=True, help_text='Ano em que obteu a última titulação')

    class Meta:
        model = Professor
        fields = 'titulacao', 'ultima_instituicao_de_titulacao', 'area_ultima_titulacao', 'ano_ultima_titulacao'
