import datetime
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max, Count, Q
from django.utils.safestring import mark_safe

from djtools.html.graficos import LineChart
from djtools.utils import normalizar_nome_proprio
import hashlib

from djtools import forms
from djtools.forms.widgets import (
    AutocompleteWidget,
    PhotoCapturePortraitInput, RenderableSelectMultiple,
)
from djtools.forms.wizard import FormWizardPlus
from djtools.templatetags.filters import in_group
from djtools.utils import eh_nome_completo
from comum.models import (
    Ano, Configuracao, ConselhoProfissional, EmailBlockList, Municipio, NivelEnsino, OrgaoEmissorRg, Pais,
    PrestadorServico, Raca, UnidadeFederativa, UsuarioGrupo, UsuarioGrupoSetor, User, Vinculo
)
from ldap_backend.models import LdapConf
from residencia.models.solicitacoes import SolicitacaoUsuario, SolicitacaoDesligamentos, SolicitacaoDiplomas, \
    SolicitacaoFerias, SolicitacaoLicencas, SolicitacaoCongressos
from rh.models import Banco, DadosBancariosPF, Pessoa, PessoaFisica, Servidor, Funcionario
from residencia.models import (
    PERIODO_LETIVO_CHOICES,
    Residente, Observacao, SequencialMatriculaResidente, Matriz, Componente, ComponenteCurricular, EstruturaCurso,
    CursoResidencia, MatrizCurso, SolicitacaoResidente, CalendarioAcademico, Turma, MatriculaPeriodo,
    ProjetoFinalResidencia, AtaEletronicaResidencia, SituacaoMatriculaPeriodo, SituacaoMatricula, Diario,
    ObservacaoDiario, PreceptorDiario, MatriculaDiario,
    FrequenciaResidente, SolicitacaoEletivo, EstagioEletivoAnexo, EstagioEletivo,
    DocumentoFrequenciaMensalResidente, UnidadeAprendizagem, UnidadeAprendizagemTurma,
    MatriculaUnidadeAprendizagemTurma, ItemConfiguracaoAvaliacaoUnidadeAprendizagem,
    ConfiguracaoAvaliacaoUnidadeAprendizagem, NotaAvaliacaoUnidadeAprendizagem
)
from rh.forms import get_choices_nome_usual, EmpregadoFesfForm


def grupos():
    COORDENADOR = Group.objects.get_or_create(name='Coordenadores(as) Residência')[0]
    return locals()


class ResidenteForm(forms.ModelFormPlus):
    nome = forms.CharFieldPlus(width=500)
    nome_social = forms.CharFieldPlus(required=False, label='Nome Social', width=255)
    data_nascimento = forms.DateFieldPlus()
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    cpf = forms.BrCpfField(label='CPF', required=False)
    passaporte = forms.CharField(required=False, label='Nº do Passaporte')
    cartorio = forms.CharField(required=False, label='Cartório')

    telefone_principal = forms.BrTelefoneField(max_length=255, required=True, label='Telefone Principal', help_text='(XX) XXXX-XXXX')
    telefone_secundario = forms.BrTelefoneField(max_length=255, required=False, label='Celular', help_text='(XX) XXXX-XXXX')
    telefone_adicional_1 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    telefone_adicional_2 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')

    raca = forms.ModelChoiceField(Raca.objects.all(), required=False, label='Raça')
    tipo_instituicao_origem = forms.ChoiceField(required=True, label='Tipo da Instituição', choices=[['', '----']] + Residente.TIPO_INSTITUICAO_ORIGEM_CHOICES)

    estado = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado', required=False)

    cidade = forms.ModelChoiceFieldPlus(
        Municipio.objects, label='Cidade', required=True, widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS)
    )

    estado_naturalidade = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado de Origem', required=False)

    naturalidade = forms.ModelChoiceFieldPlus(
        Municipio.objects, label='Naturalidade', required=False, widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS)
    )

    categoria = forms.ChoiceField(choices=Residente.EMPTY_CHOICES + Residente.CATEGORIAS_CHOICES, required=True, label='Categoria')
    # conselho classe
    numero_registro = forms.CharField(max_length=255, required=False, label='Número de Registro')
    conselho = forms.ModelChoiceField(ConselhoProfissional.objects, required=False, label='Conselho')

    db_banco = forms.ChoiceField(label="Banco", choices=Residente.EMPTY_CHOICES + DadosBancariosPF.BANCO_CHOICES, required=False)
    db_numero_agencia = forms.CharField(label="Número da Agência", required=False, max_length=50, help_text="Ex: 3293-X")
    db_tipo_conta = forms.ChoiceField(label="Tipo da Conta", required=False, choices=Residente.EMPTY_CHOICES + DadosBancariosPF.TIPOCONTA_CHOICES)
    db_numero_conta = forms.CharField(label='Número da Conta', required=False, widget=forms.TextInput(attrs={'pattern': '[0-9a-zA-Z]+'}), help_text='Utilize apenas números e letras')
    db_operacao = forms.CharField(label="Operação", max_length=50, required=False)

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
        ('Deficiências, Transtornos e Superdotação', {'fields': ('tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao', 'outras_necessidades')}),
        ('Outras Informações', {'fields': ('tipo_sanguineo', 'nacionalidade', 'pais_origem', 'estado_naturalidade', 'naturalidade', 'raca')}),
        (
            'Saúde',
            {
                'fields': ('possui_problema_saude', 'possui_alergia', 'possui_alergia_qual', 'em_tratamento_medico', 'em_tratamento_medico_qual', 'usa_medicacao', 'usa_medicacao_qual', 'contato_emergencia', 'outra_info_saude',)
            }
        ),
        ('Dados Escolares', {'fields': ('nivel_ensino_anterior', 'tipo_instituicao_origem', 'nome_instituicao_anterior', 'ano_conclusao_estudo_anterior', 'habilitacao_pedagogica')}),
        ('Conselho de Fiscalização Profissional', {'fields': ('categoria','conselho', 'numero_registro')}),
        ('RG', {'fields': ('numero_rg', 'uf_emissao_rg', 'orgao_emissao_rg', 'data_emissao_rg')}),
        ('Título de Eleitor', {'fields': ('numero_titulo_eleitor', 'zona_titulo_eleitor', 'secao', 'data_emissao_titulo_eleitor', 'uf_emissao_titulo_eleitor')}),
        (
            'Carteira de Reservista',
            {'fields': ('numero_carteira_reservista', 'regiao_carteira_reservista', 'serie_carteira_reservista', 'estado_emissao_carteira_reservista', 'ano_carteira_reservista')},
        ),
        ('Certidão Civil', {'fields': ('tipo_certidao', 'cartorio', 'numero_certidao', 'folha_certidao', 'livro_certidao', 'data_emissao_certidao', 'matricula_certidao')}),
        ('Outros Documentos', {'fields': ('codigo_educacenso', 'nis', 'pis_pasep')}),
        ('Transporte Escolar', {'fields': ('poder_publico_responsavel_transporte', 'tipo_veiculo')}),
        ('Dados Bancários', {'fields': ('db_banco', 'db_numero_agencia', 'db_tipo_conta', 'db_numero_conta', 'db_operacao')}),
    )

    class Meta:
        model = Residente
        exclude = ()

    class Media:
        js = ('/static/residencia/js/ResidenteForm.js',)

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
        if not self.instance.pk:
            DadosBancariosPF.objects.create(
                pessoa_fisica=self.instance.pessoa_fisica,
                banco=self.cleaned_data['db_banco'],
                numero_agencia=self.cleaned_data['db_numero_agencia'],
                tipo_conta=self.cleaned_data['db_tipo_conta'],
                numero_conta=self.cleaned_data['db_numero_conta'],
                operacao=self.cleaned_data['db_operacao'],
            )
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
            raise forms.ValidationError('Informe o passaporte do(a) Residente.')
        return passaporte

    def clean_cpf(self):
        nacionalidade = self.data.get('nacionalidade')
        cpf = self.data.get('cpf')
        if nacionalidade != 'Estrangeira' and not cpf:
            raise forms.ValidationError('Informe o CPF do(a) Residente.')
        return cpf

    def clean_aluno_pne(self):
        aluno_pne = self.cleaned_data.get('aluno_pne')

        if aluno_pne and not (self.data.get('tipo_necessidade_especial') or self.data.get('tipo_transtorno') or self.data.get('superdotacao') or self.data.get('outras_necessidades')):
            raise forms.ValidationError('Informe a deficiência, transtorno ou superdotação do(a) Residente')
        return aluno_pne

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
            nome_pais = 'Brasil'
            if naturalidade and hasattr(naturalidade, 'pais'):
                nome_pais = naturalidade.pais.nome
            if nacionalidade == 'Brasileira':
                if not naturalidade:
                    raise forms.ValidationError('O campo naturalidade é obrigatório quando a pessoa nasceu no Brasil.')

                if nome_pais != 'Brasil':
                    raise forms.ValidationError('Não pode ser informado uma naturalidade fora do Brasil para aluno com nacionalidade Brasileira.')

            elif nome_pais == 'Brasil':
                raise forms.ValidationError('Não pode ser informado uma naturalidade do Brasil para aluno com nacionalidade Estrangeira ou Brasileira - Nascido no exterior ou naturalizado.')

        return self.cleaned_data.get('naturalidade')

    def clean(self):
        if 'db_banco' in self.cleaned_data and self.cleaned_data['db_banco']:
            if (
                    'db_numero_agencia' not in self.cleaned_data
                    or ('db_numero_agencia' in self.cleaned_data and not self.cleaned_data['db_numero_agencia'])
            ):
                raise forms.ValidationError("Não é possível adicionar uma conta bancária sem número da agência.")
            if (
                    'db_tipo_conta' not in self.cleaned_data
                    or ('db_tipo_conta' in self.cleaned_data and not self.cleaned_data['db_tipo_conta'])
            ):
                raise forms.ValidationError("Não é possível adicionar uma conta bancária sem tipo da conta.")
            if (
                    'db_numero_conta' not in self.cleaned_data
                    or ('db_numero_conta' in self.cleaned_data and not self.cleaned_data['db_numero_conta'])
            ):
                raise forms.ValidationError("Não é possível adicionar uma conta bancária sem número da conta.")
        return self.cleaned_data


class ResidenteEditarForm(forms.ModelFormPlus):
    nome = forms.CharFieldPlus(width=500)
    nome_social = forms.CharFieldPlus(required=False, label='Nome Social', width=255)
    data_nascimento = forms.DateFieldPlus()
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    cpf = forms.BrCpfField(label='CPF', required=False)
    passaporte = forms.CharField(required=False, label='Nº do Passaporte')
    cartorio = forms.CharField(required=False, label='Cartório')

    telefone_principal = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Principal', help_text='(XX) XXXX-XXXX')
    telefone_secundario = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Secundário', help_text='(XX) XXXX-XXXX')
    telefone_adicional_1 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    telefone_adicional_2 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')

    raca = forms.ModelChoiceField(Raca.objects.all(), required=False, label='Raça')
    tipo_instituicao_origem = forms.ChoiceField(required=True, label='Tipo da Instituição', choices=[['', '----']] + Residente.TIPO_INSTITUICAO_ORIGEM_CHOICES)

    estado = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado', required=False)

    cidade = forms.ModelChoiceFieldPlus(
        Municipio.objects, label='Cidade', required=True, widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS)
    )

    estado_naturalidade = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado de Origem', required=False)

    naturalidade = forms.ModelChoiceFieldPlus(
        Municipio.objects, label='Naturalidade', required=False, widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS)
    )

    categoria = forms.ChoiceField(choices=Residente.EMPTY_CHOICES + Residente.CATEGORIAS_CHOICES, required=True, label='Categoria')
    # conselho classe
    numero_registro = forms.CharField(max_length=255, required=False, label='Número de Registro')
    conselho = forms.ModelChoiceField(ConselhoProfissional.objects, required=False, label='Conselho')
    lotacao = forms.CharField(max_length=255, required=False, label='Lotação')

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
        ('Deficiências, Transtornos e Superdotação', {'fields': ('tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao', 'outras_necessidades')}),
        ('Outras Informações', {'fields': ('tipo_sanguineo', 'nacionalidade', 'pais_origem', 'estado_naturalidade', 'naturalidade', 'raca')}),
        (
            'Saúde',
            {
                'fields': ('possui_problema_saude', 'possui_alergia', 'possui_alergia_qual', 'em_tratamento_medico', 'em_tratamento_medico_qual', 'usa_medicacao', 'usa_medicacao_qual', 'contato_emergencia', 'outra_info_saude',)
            }
        ),
        ('Dados Escolares', {'fields': ('nivel_ensino_anterior', 'tipo_instituicao_origem', 'nome_instituicao_anterior', 'ano_conclusao_estudo_anterior', 'habilitacao_pedagogica')}),
        ('Conselho de Fiscalização Profissional', {'fields': ('categoria','conselho', 'numero_registro', 'lotacao')}),
        ('RG', {'fields': ('numero_rg', 'uf_emissao_rg', 'orgao_emissao_rg', 'data_emissao_rg')}),
        ('Título de Eleitor', {'fields': ('numero_titulo_eleitor', 'zona_titulo_eleitor', 'secao', 'data_emissao_titulo_eleitor', 'uf_emissao_titulo_eleitor')}),
        (
            'Carteira de Reservista',
            {'fields': ('numero_carteira_reservista', 'regiao_carteira_reservista', 'serie_carteira_reservista', 'estado_emissao_carteira_reservista', 'ano_carteira_reservista')},
        ),
        ('Certidão Civil', {'fields': ('tipo_certidao', 'cartorio', 'numero_certidao', 'folha_certidao', 'livro_certidao', 'data_emissao_certidao', 'matricula_certidao')}),
        ('Outros Documentos', {'fields': ('codigo_educacenso', 'nis', 'pis_pasep')}),
        ('Transporte Escolar', {'fields': ('poder_publico_responsavel_transporte', 'tipo_veiculo')}),
    )

    class Meta:
        model = Residente
        exclude = ()

    class Media:
        js = ('/static/residencia/js/ResidenteForm.js',)

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
            raise forms.ValidationError('Informe o passaporte do(a) Residente.')
        return passaporte

    def clean_cpf(self):
        nacionalidade = self.data.get('nacionalidade')
        cpf = self.data.get('cpf')
        if nacionalidade != 'Estrangeira' and not cpf:
            raise forms.ValidationError('Informe o CPF do(a) Residente.')
        return cpf

    def clean_aluno_pne(self):
        aluno_pne = self.cleaned_data.get('aluno_pne')

        if aluno_pne and not (self.data.get('tipo_necessidade_especial') or self.data.get('tipo_transtorno') or self.data.get('superdotacao') or self.data.get('outras_necessidades')):
            raise forms.ValidationError('Informe a deficiência, transtorno ou superdotação do(a) Residente')
        return aluno_pne

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
            nome_pais = 'Brasil'
            if naturalidade and hasattr(naturalidade, 'pais'):
                nome_pais = naturalidade.pais.nome
            if nacionalidade == 'Brasileira':
                if not naturalidade:
                    raise forms.ValidationError('O campo naturalidade é obrigatório quando a pessoa nasceu no Brasil.')

                if nome_pais != 'Brasil':
                    raise forms.ValidationError('Não pode ser informado uma naturalidade fora do Brasil para aluno com nacionalidade Brasileira.')

            elif nome_pais == 'Brasil':
                raise forms.ValidationError('Não pode ser informado uma naturalidade do Brasil para aluno com nacionalidade Estrangeira ou Brasileira - Nascido no exterior ou naturalizado.')

        return self.cleaned_data.get('naturalidade')


class AtualizarEmailResidenteForm(forms.FormPlus):
    email_secundario = forms.EmailField(max_length=255, required=False, label='E-mail Secundário')
    email_academico = forms.EmailField(max_length=255, required=False, label='E-mail Acadêmico')
    email_google_classroom = forms.EmailField(max_length=255, required=False, label='E-mail Google ClassRoom')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.residente = kwargs.pop('residente')

        super().__init__(*args, **kwargs)

        if self.residente.get_vinculo() is None:
            self.residente.save()  # força criação de vínculo
        self.fields['email_secundario'].initial = self.residente.get_vinculo().pessoa.email_secundario
        self.fields['email_academico'].initial = self.residente.email_academico
        self.fields['email_google_classroom'].initial = self.residente.email_google_classroom
        cra = UsuarioGrupo.objects.filter(
            user=self.request.user, group__name='Secretário(a) Residência'
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
            if Residente.objects.exclude(pk=self.residente.id).filter(email_academico=email_academico).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if Servidor.objects.filter(email_academico=email_academico).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if EmailBlockList.objects.filter(email=email_academico).exists():
                raise forms.ValidationError("O e-mail informado está bloqueado.")
            if not settings.DEBUG and 'ldap_backend' in settings.INSTALLED_APPS:
                ldap_conf = LdapConf.get_active()
                usernames = ldap_conf.get_usernames_from_principalname(email_academico)
                if usernames and self.residente.matricula not in usernames:
                    raise forms.ValidationError("O e-email informado já é utilizado por outro usuário.")
        return email_academico

    def clean_email_google_classroom(self):
        if self.cleaned_data['email_google_classroom']:
            if Residente.objects.exclude(pk=self.residente.id).filter(email_google_classroom=self.cleaned_data['email_google_classroom']).exists():
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
            self.residente.email_academico = self.cleaned_data.get('email_academico')
        if 'email_google_classroom' in self.cleaned_data:
            self.residente.email_google_classroom = self.cleaned_data.get('email_google_classroom')
        self.residente.save()
        if 'email_secundario' in self.cleaned_data:
            Pessoa.objects.filter(
                pk=self.residente.get_vinculo().pessoa.id
            ).update(email_secundario=self.cleaned_data.get('email_secundario'))


class AtualizarDadosPessoaisForm(forms.FormPlus):
    nome_usual = forms.ChoiceField(label="Nome Usual", required=False, help_text='Nome que será exibido no SUAP')
    lattes = forms.URLField(label='Lattes', help_text='Endereço do currículo lattes', required=False)
    logradouro = forms.CharFieldPlus(max_length=255, required=True, label='Logradouro', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=True, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=True, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='CEP')
    cidade = forms.ModelChoiceFieldPlus(Municipio.objects, required=True, label='Cidade', widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS))

    telefone_principal = forms.CharFieldPlus(max_length=255, label='Telefone Principal', required=False)
    telefone_secundario = forms.CharFieldPlus(max_length=255, label='Telefone Secundário', required=False)
    esconde_telefone = forms.CharFieldPlus(max_length=1, label='esconde_telefone', required=False, widget=forms.HiddenInput())

    utiliza_transporte_escolar_publico = forms.ChoiceField(label='Utiliza Transporte Escolar Público', required=True, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    poder_publico_responsavel_transporte = forms.ChoiceField(
        label='Poder Público Responsável pelo Transporte Escolar', choices=[['', '---------']] + Residente.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, required=False
    )
    tipo_veiculo = forms.ChoiceField(label='Tipo de Veículo Utilizado no Transporte Escolar', choices=[['', '---------']] + Residente.TIPO_VEICULO_CHOICES_FOR_FORM, required=False)

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
        js = ('/static/residencia/js/AtualizarDadosPessoaisForm.js',)

    class Meta:
        fields = ('nome_social', 'logradouro', 'numero', 'complemento', 'bairro', 'cep', 'cidade')


class AtualizarFotoForm(forms.FormPlus):
    residente = forms.ModelChoiceField(Residente.objects, widget=forms.HiddenInput())
    foto = forms.PhotoCaptureField(required=False, widget=PhotoCapturePortraitInput)
    arquivo = forms.ImageFieldPlus(required=False)

    fieldsets = (
        ('Captura da Foto com Câmera', {'fields': ('residente', 'foto')}),
        ('Upload de Arquivo', {'fields': ('arquivo',)})
    )

    def clean(self):
        if not self.cleaned_data.get('foto') and not self.cleaned_data.get('arquivo'):
            raise forms.ValidationError('Retire a foto com a câmera ou forneça um arquivo.')
        else:
            return self.cleaned_data

    def processar(self, request):
        residente = self.cleaned_data.get('residente')
        if 'foto' in self.cleaned_data and self.cleaned_data.get('foto'):
            dados = self.cleaned_data.get('foto')
        else:
            dados = self.cleaned_data.get('arquivo').read()

        if request.user.has_perm('residencia.efetuar_matricula'):
            residente.foto.save(f'{residente.pk}.jpg', ContentFile(dados))
            residente.pessoa_fisica.foto.save(f'{residente.pk}.jpg', ContentFile(dados))
            return 'Foto atualizada com sucesso.'
        else:
            return 'Esta funcionalidade encontra-se temporariamente indisponível.'


class SolicitarMatriculaResidenteForm(FormWizardPlus):
    METHOD = 'POST'
    LAST_SUBMIT_LABEL = 'Finalizar'

    foto = forms.PhotoCaptureField(required=False, widget=PhotoCapturePortraitInput)
    arquivo_foto = forms.ImageFieldPlus(label='Arquivo', required=False)

    nacionalidade = forms.ChoiceField(required=True, label='Nacionalidade', choices=Residente.TIPO_NACIONALIDADE_CHOICES)
    cpf = forms.BrCpfField(required=False)
    passaporte = forms.CharField(required=False, label='Nº do Passaporte')
    nome = forms.CharFieldPlus(required=True, label='Nome', width=500)
    nome_social = forms.CharFieldPlus(required=False, label='Nome Social', width=500)
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    data_nascimento = forms.DateFieldPlus(required=True, label='Data de Nascimento')
    estado_civil = forms.ChoiceField(required=True, choices=Residente.ESTADO_CIVIL_CHOICES)

    # endereco
    logradouro = forms.CharFieldPlus(max_length=255, required=True, label='Logradouro', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=True, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=True, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='Cep')

    estado = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado', required=False)
    nomecidade = forms.CharField(max_length=255, required=True, label='Cidade')
    # cidade = forms.ModelChoiceFieldPlus(
    #     Municipio.objects,
    #     label='Cidade',
    #     required=True,
    #     help_text='Preencha o nome da cidade sem acento.',
    #     widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS),
    # )

    tipo_zona_residencial = forms.ChoiceField(required=False, label='Zona Residencial', choices=[['', '-----']] + Residente.TIPO_ZONA_RESIDENCIAL_CHOICES)

    # dados familiares
    nome_pai = forms.CharFieldPlus(max_length=255, label='Nome do Pai', required=False, width=500)
    estado_civil_pai = forms.ChoiceField(choices=Residente.EMPTY_CHOICES + Residente.ESTADO_CIVIL_CHOICES, required=False)
    pai_falecido = forms.BooleanField(label='Pai é falecido?', required=False)
    nome_mae = forms.CharFieldPlus(max_length=255, label='Nome da Mãe', required=True, width=500)
    estado_civil_mae = forms.ChoiceField(choices=Residente.EMPTY_CHOICES + Residente.ESTADO_CIVIL_CHOICES, required=False)
    mae_falecida = forms.BooleanField(label='Mãe é falecida?', required=False)
    responsavel = forms.CharFieldPlus(max_length=255, label='Nome do Responsável', required=False, width=500, help_text='Obrigatório para menores de idade.')
    email_responsavel = forms.CharFieldPlus(max_length=255, label='Email do Responsável', required=False, width=500)
    parentesco_responsavel = forms.ChoiceField(label='Parenteste com Responsável', choices=[['', '---------']] + Residente.PARENTESCO_CHOICES, required=False)
    cpf_responsavel = forms.BrCpfField(label='CPF do Responsável', required=False)

    # contato
    telefone_principal = forms.BrTelefoneField(max_length=255, required=True, label='Telefone Principal', help_text='(XX) XXXX-XXXX')
    telefone_secundario = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Secundário', help_text='(XX) XXXX-XXXX')
    telefone_adicional_1 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    telefone_adicional_2 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    email_pessoal = forms.EmailField(max_length=255, required=True, label='E-mail Pessoal')

    # outras informacoes
    tipo_sanguineo = forms.ChoiceField(required=False, label='Tipo Sanguíneo', choices=Residente.EMPTY_CHOICES + Residente.TIPO_SANGUINEO_CHOICES)
    pais_origem = forms.ModelChoiceField(Pais.objects, required=False, label='País de Origem', help_text='Obrigatório para estrangeiros')

    estado_naturalidade = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado de Origem', required=False)

    nomenaturalidade = forms.CharField(max_length=255, required=True, label='Naturalidade')
    # naturalidade = forms.ModelChoiceFieldPlus(
    #     Municipio.objects,
    #     label='Naturalidade',
    #     required=False,
    #     widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS),
    # )

    raca = forms.ModelChoiceField(Raca.objects.all(), required=False, label='Raça')

    # necessidades especiais
    aluno_pne = forms.ChoiceField(label='Portador de Necessidades Especiais', required=True, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    tipo_necessidade_especial = forms.ChoiceField(required=False, label='Deficiência', choices=[['', '---------']] + Residente.TIPO_NECESSIDADE_ESPECIAL_CHOICES)
    tipo_transtorno = forms.ChoiceField(required=False, label='Transtorno', choices=[['', '---------']] + Residente.TIPO_TRANSTORNO_CHOICES)
    superdotacao = forms.ChoiceField(required=False, label='Superdotação', choices=[['', '---------']] + Residente.SUPERDOTACAO_CHOICES)
    outras_necessidades = forms.CharField(max_length=255, required=False, label='Outras Necessidades')

    # dados escolares
    nivel_ensino_anterior = forms.ModelChoiceField(NivelEnsino.objects, required=True, label='Nível de Ensino')
    tipo_instituicao_origem = forms.ChoiceField(required=True, label='Tipo da Instituição', choices=[['', '---------']] + Residente.TIPO_INSTITUICAO_ORIGEM_CHOICES)
    nome_instituicao_anterior = forms.CharField(max_length=255, required=False, label='Nome da Instituição')
    ano_conclusao_estudo_anterior = forms.ModelChoiceField(Ano.objects, required=False, label='Ano de Conclusão', help_text='Obrigatório para alunos com nível médio')

    categoria = forms.ChoiceField(choices=Residente.EMPTY_CHOICES + Residente.CATEGORIAS_CHOICES, required=True, label='Categoria')
    # conselho classe
    numero_registro = forms.CharField(max_length=255, required=False, label='Número de Registro')
    conselho = forms.ModelChoiceField(ConselhoProfissional.objects, required=False, label='Conselho')

    # rg
    numero_rg = forms.CharField(max_length=255, required=False, label='Número do RG')
    uf_emissao_rg = forms.ModelChoiceField(UnidadeFederativa.objects, required=False, label='Estado Emissor')
    orgao_emissao_rg = forms.ModelChoiceField(OrgaoEmissorRg.objects, required=False, label='Orgão Emissor')
    data_emissao_rg = forms.DateFieldPlus(required=False, label='Data de Emissão')

    # titulo_eleitor
    numero_titulo_eleitor = forms.CharField(max_length=255, required=False, label='Título de Eleitor')
    zona_titulo_eleitor = forms.CharField(max_length=255, required=False, label='Zona')
    secao = forms.CharField(max_length=255, required=False, label='Seção')
    data_emissao_titulo_eleitor = forms.DateFieldPlus(required=False, label='Data de Emissão')
    uf_emissao_titulo_eleitor = forms.ModelChoiceField(UnidadeFederativa.objects, required=False, label='Estado Emissor')

    # carteira de reservista
    numero_carteira_reservista = forms.CharField(max_length=255, required=False, label='Número da Carteira de Reservista')
    regiao_carteira_reservista = forms.CharField(max_length=255, required=False, label='Região')
    serie_carteira_reservista = forms.CharField(max_length=255, required=False, label='Série')
    estado_emissao_carteira_reservista = forms.ModelChoiceField(UnidadeFederativa.objects, required=False, label='Estado Emissor')
    ano_carteira_reservista = forms.IntegerField(required=False, label='Ano')

    # certidao_civil
    tipo_certidao = forms.ChoiceField(required=True, label='Tipo de Certidão', choices=Residente.TIPO_CERTIDAO_CHOICES)
    cartorio = forms.CharField(max_length=255, required=False,label='Cartório')
    numero_certidao = forms.CharField(max_length=255, required=False, label='Número de Termo')
    folha_certidao = forms.CharField(max_length=255, required=False, label='Folha')
    livro_certidao = forms.CharField(max_length=255, required=False, label='Livro')
    data_emissao_certidao = forms.DateFieldPlus(required=False, label='Data de Emissão')
    matricula_certidao = forms.CharField(max_length=255, required=False, label='Matrícula', help_text='Obrigatório para certidões realizadas a partir de 01/01/2010')

    utiliza_transporte_escolar_publico = forms.ChoiceField(label='Utiliza Transporte Escolar Público', required=False, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    poder_publico_responsavel_transporte = forms.ChoiceField(
        label='Poder Público Responsável pelo Transporte Escolar', choices=[['', '---------']] + Residente.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, required=False
    )
    tipo_veiculo = forms.ChoiceField(label='Tipo de Veículo Utilizado no Transporte Escolar', choices=[['', '---------']] + Residente.TIPO_VEICULO_CHOICES_FOR_FORM, required=False)

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
                        'email_responsavel',
                        'parentesco_responsavel',
                        'cpf_responsavel',
                    )
                },
            ),
            ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'estado', 'nomecidade', 'tipo_zona_residencial')}),
        ],
        [
            ('Informações para Contato', {'fields': ('telefone_principal', 'telefone_secundario', 'telefone_adicional_1', 'telefone_adicional_2', 'email_pessoal')}),
            ('Deficiências, Transtornos e Superdotação', {'fields': ('aluno_pne', 'tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao', 'outras_necessidades')}),
            ('Transporte Escolar Utilizado', {'fields': ('utiliza_transporte_escolar_publico', 'poder_publico_responsavel_transporte', 'tipo_veiculo')}),
            ('Outras Informações', {'fields': ('tipo_sanguineo', 'pais_origem', 'estado_naturalidade', 'nomenaturalidade', 'raca')}),
            ('Dados Escolares Anteriores', {'fields': ('nivel_ensino_anterior', 'tipo_instituicao_origem', 'nome_instituicao_anterior', 'ano_conclusao_estudo_anterior')}),
        ],
        [
            ('Conselho de Fiscalização Profissional', {'fields': ('categoria', 'conselho', 'numero_registro')}),
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
        ],
    )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_ano_conclusao_estudo_anterior(self):
        ano_conclusao_estudo_anterior = self.cleaned_data.get('ano_conclusao_estudo_anterior')
        nivel_ensino_anterior = self.data.get('nivel_ensino_anterior')
        if nivel_ensino_anterior == str(NivelEnsino.MEDIO) and not ano_conclusao_estudo_anterior:
            raise forms.ValidationError('O Ano de Conclusão é de preenchimento obrigatório.')
        return ano_conclusao_estudo_anterior

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

        if aluno_pne == 'Sim' and not (self.data.get('tipo_necessidade_especial') or self.data.get('tipo_transtorno') or self.data.get('superdotacao') or self.data.get('outras_necessidades')):
            raise forms.ValidationError('Informe a deficiência, transtorno ou superdotação do aluno.')
        return aluno_pne

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
            raise ValidationError('O nome do(a) Residente precisa ser completo e não pode conter números.')

        return self.cleaned_data.get('nome')

    def clean_nome_social(self):
        nome = self.get_entered_data('nome_social')

        if nome and not eh_nome_completo(nome):
            raise ValidationError('O nome social do(a) Residente precisa ser completo e não pode conter números.')

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

    def clean_data_nascimento(self):
        menor_data_valida = datetime.datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S').date()
        if 'data_nascimento' in self.cleaned_data and self.cleaned_data['data_nascimento'] < menor_data_valida:
            raise forms.ValidationError('Data de nascimento deve ser maior que 01/01/1900.')
        return self.cleaned_data['data_nascimento']

    def clean_pais_origem(self):
        nacionalidade = self.get_entered_data('nacionalidade')
        if nacionalidade and not nacionalidade == 'Brasileira' and not self.cleaned_data['pais_origem']:
            raise forms.ValidationError('O campo "País de Origem" possui preenchimento obrigatório quando a pessoa nasceu no exterior.')

        return 'pais_origem' in self.cleaned_data and self.cleaned_data['pais_origem'] or None

    # def clean_naturalidade(self):
    #     nacionalidade = self.get_entered_data('nacionalidade')
    #     eh_brasileiro = nacionalidade and nacionalidade == 'Brasileira'
    #     if (self.exige_naturalidade_estrangeiro or eh_brasileiro) and 'naturalidade' not in self.cleaned_data or not self.cleaned_data['naturalidade']:
    #         raise forms.ValidationError('O campo "Naturalidade" possui preenchimento obrigatório.')
    #
    #     naturalidade = self.get_entered_data('naturalidade')
    #     nome_pais = 'Brasil'
    #     if naturalidade and hasattr(naturalidade, 'pais'):
    #         nome_pais = naturalidade.pais.nome
    #     if eh_brasileiro and nome_pais != 'Brasil':
    #         raise forms.ValidationError('Não pode ser informado uma naturalidade fora do Brasil para aluno com nacionalidade Brasileira.')
    #     if not eh_brasileiro and nome_pais == 'Brasil':
    #         raise forms.ValidationError('Não pode ser informado uma naturalidade do Brasil para aluno com nacionalidade Estrangeira ou Brasileira - Nascido no exterior ou naturalizado.')
    #
    #     return 'naturalidade' in self.cleaned_data and self.cleaned_data['naturalidade'] or None

    def clean_email_pessoal(self):
        if 'email_pessoal' in self.cleaned_data:
            email_pessoal = self.cleaned_data['email_pessoal']

            if not Configuracao.get_valor_por_chave('comum', 'permite_email_institucional_email_secundario') and Configuracao.eh_email_institucional(email_pessoal):
                raise forms.ValidationError("Escolha um e-mail que não seja institucional.")

        return 'email_pessoal' in self.cleaned_data and self.cleaned_data['email_pessoal'] or ''

    def next_step(self):
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
                self.fields['naturalidade'].queryset = Municipio.objects.filter(codigo__isnull=False)
                self.fields['naturalidade'].help_text = 'Cidade em que o aluno nasceu. Obrigatório para brasileiros'
            elif nacionalidade and nacionalidade == 'Estrangeira':
                self.fields['naturalidade'].queryset = Municipio.objects.filter(codigo__isnull=True)
                self.fields['naturalidade'].help_text = 'Cidade/Província em que o aluno nasceu.'

    @transaction.atomic
    def processar(self):

        residente = SolicitacaoResidente()
        residente.situacao = SolicitacaoResidente.STATUS_EM_ANALISE
        residente.alterado_em = datetime.datetime.now()
        residente.cpf = self.cleaned_data['cpf']
        residente.nome_registro = self.cleaned_data['nome']
        residente.nome_social = self.cleaned_data['nome_social']
        residente.sexo = self.cleaned_data['sexo']
        residente.nascimento_data = self.cleaned_data['data_nascimento']
        residente.email = self.cleaned_data['email_pessoal']

        residente.estado_civil = self.cleaned_data['estado_civil']
        # dados familiares
        residente.nome_pai = self.cleaned_data['nome_pai']
        residente.estado_civil_pai = self.cleaned_data['estado_civil_pai']
        residente.pai_falecido = self.cleaned_data['pai_falecido']
        residente.nome_mae = self.cleaned_data['nome_mae']
        residente.estado_civil_mae = self.cleaned_data['estado_civil_mae']
        residente.mae_falecida = self.cleaned_data['mae_falecida']
        residente.responsavel = self.cleaned_data['responsavel']
        residente.cpf_responsavel = self.cleaned_data['cpf_responsavel']
        residente.parentesco_responsavel = self.cleaned_data['parentesco_responsavel']
        # endereco
        residente.logradouro = self.cleaned_data['logradouro']
        residente.numero = self.cleaned_data['numero']
        residente.complemento = self.cleaned_data['complemento']
        residente.bairro = self.cleaned_data['bairro']
        residente.cep = self.cleaned_data['cep']
        residente.nomecidade = self.cleaned_data['nomecidade']
        residente.tipo_zona_residencial = self.cleaned_data['tipo_zona_residencial']
        # contato
        residente.telefone_principal = self.cleaned_data['telefone_principal']
        residente.telefone_secundario = self.cleaned_data['telefone_secundario']
        residente.telefone_adicional_1 = self.cleaned_data['telefone_adicional_1']
        residente.telefone_adicional_2 = self.cleaned_data['telefone_adicional_2']

        # transporte escolar
        if self.cleaned_data['utiliza_transporte_escolar_publico']:
            residente.poder_publico_responsavel_transporte = self.cleaned_data['poder_publico_responsavel_transporte']
            residente.tipo_veiculo = self.cleaned_data['tipo_veiculo']
        else:
            residente.poder_publico_responsavel_transporte = None
            residente.tipo_veiculo = None

        # outras informacoes
        residente.tipo_sanguineo = self.cleaned_data['tipo_sanguineo']
        residente.nacionalidade = self.cleaned_data['nacionalidade']
        residente.passaporte = self.cleaned_data['passaporte']
        residente.nomenaturalidade = self.cleaned_data['nomenaturalidade']
        residente.raca = self.cleaned_data['raca']

        if self.cleaned_data['aluno_pne']:
            residente.tipo_necessidade_especial = self.cleaned_data['tipo_necessidade_especial']
            residente.tipo_transtorno = self.cleaned_data['tipo_transtorno']
            residente.superdotacao = self.cleaned_data['superdotacao']
            residente.outras_necessidades = self.cleaned_data['outras_necessidades']
        else:
            residente.tipo_necessidade_especial = None
            residente.tipo_transtorno = None
            residente.superdotacao = None
            residente.outras_necessidades = None

        # dados escolares
        residente.nivel_ensino_anterior = self.cleaned_data['nivel_ensino_anterior']
        residente.tipo_instituicao_origem = self.cleaned_data['tipo_instituicao_origem']
        residente.nome_instituicao_anterior = self.cleaned_data['nome_instituicao_anterior']
        residente.ano_conclusao_estudo_anterior = self.cleaned_data['ano_conclusao_estudo_anterior']
        residente.categoria = self.cleaned_data['categoria']
        # conselho classe
        residente.numero_registro = self.cleaned_data['numero_registro']
        residente.conselho = self.cleaned_data['conselho']
        # rg
        residente.numero_rg = self.cleaned_data['numero_rg']
        residente.uf_emissao_rg = self.cleaned_data['uf_emissao_rg']
        residente.orgao_emissao_rg = self.cleaned_data['orgao_emissao_rg']
        residente.data_emissao_rg = self.cleaned_data['data_emissao_rg']
        # titulo_eleitor
        residente.numero_titulo_eleitor = self.cleaned_data['numero_titulo_eleitor']
        residente.zona_titulo_eleitor = self.cleaned_data['zona_titulo_eleitor']
        residente.secao = self.cleaned_data['secao']
        residente.data_emissao_titulo_eleitor = self.cleaned_data['data_emissao_titulo_eleitor']
        residente.uf_emissao_titulo_eleitor = self.cleaned_data['uf_emissao_titulo_eleitor']
        # carteira de reservista
        residente.numero_carteira_reservista = self.cleaned_data['numero_carteira_reservista']
        residente.regiao_carteira_reservista = self.cleaned_data['regiao_carteira_reservista']
        residente.serie_carteira_reservista = self.cleaned_data['serie_carteira_reservista']
        residente.estado_emissao_carteira_reservista = self.cleaned_data['estado_emissao_carteira_reservista']
        residente.ano_carteira_reservista = self.cleaned_data['ano_carteira_reservista']
        # certidao_civil
        residente.tipo_certidao = self.cleaned_data['tipo_certidao']
        residente.cartorio = self.cleaned_data['cartorio']
        residente.numero_certidao = self.cleaned_data['numero_certidao']
        residente.folha_certidao = self.cleaned_data['folha_certidao']
        residente.livro_certidao = self.cleaned_data['livro_certidao']
        residente.data_emissao_certidao = self.cleaned_data['data_emissao_certidao']
        residente.matricula_certidao = self.cleaned_data['matricula_certidao']
        # prefixo = f'{residente.ano_letivo}{residente.periodo_letivo}{residente.curso_residencia.codigo}'
        prefixo_temp = '20221RES'
        residente.matricula = SequencialMatriculaResidente.proximo_numero(prefixo_temp)
        residente.email_scholar = ''
        residente.save()

        if 'foto' in self.cleaned_data and self.cleaned_data.get('foto'):
            residente.foto.save(f'{residente.pk}.jpg', ContentFile(self.cleaned_data['foto']))
        elif 'arquivo_foto' in self.cleaned_data and self.cleaned_data.get('arquivo_foto'):
            residente.foto.save(f'{residente.pk}.jpg', ContentFile(self.cleaned_data.get('arquivo_foto').read()))

        residente.save()

        return residente


class EfetuarMatriculaForm(FormWizardPlus):
    METHOD = 'POST'
    LAST_SUBMIT_LABEL = 'Finalizar'

    foto = forms.PhotoCaptureField(required=False, widget=PhotoCapturePortraitInput)
    arquivo_foto = forms.ImageFieldPlus(label='Arquivo', required=False)

    nacionalidade = forms.ChoiceField(required=True, label='Nacionalidade', choices=Residente.TIPO_NACIONALIDADE_CHOICES)
    cpf = forms.BrCpfField(required=False)
    passaporte = forms.CharField(required=False, label='Nº do Passaporte')
    nome = forms.CharFieldPlus(required=True, label='Nome', width=500)
    nome_social = forms.CharFieldPlus(required=False, label='Nome Social', help_text='Só preencher este campo a pedido do residente e de acordo com a legislação vigente.', width=500)
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    data_nascimento = forms.DateFieldPlus(required=True, label='Data de Nascimento')
    estado_civil = forms.ChoiceField(required=True, choices=Residente.ESTADO_CIVIL_CHOICES)

    # endereco
    logradouro = forms.CharFieldPlus(max_length=255, required=True, label='Logradouro', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=True, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=True, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='Cep')

    estado = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado', required=False)
    cidade = forms.ModelChoiceFieldPlus(
        Municipio.objects,
        label='Cidade',
        required=True,
        help_text='Preencha o nome da cidade sem acento.',
        widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS),
    )

    tipo_zona_residencial = forms.ChoiceField(required=False, label='Zona Residencial', choices=[['', '-----']] + Residente.TIPO_ZONA_RESIDENCIAL_CHOICES)

    # dados familiares
    nome_pai = forms.CharFieldPlus(max_length=255, label='Nome do Pai', required=False, width=500)
    estado_civil_pai = forms.ChoiceField(choices=Residente.EMPTY_CHOICES + Residente.ESTADO_CIVIL_CHOICES, required=False)
    pai_falecido = forms.BooleanField(label='Pai é falecido?', required=False)
    nome_mae = forms.CharFieldPlus(max_length=255, label='Nome da Mãe', required=True, width=500)
    estado_civil_mae = forms.ChoiceField(choices=Residente.EMPTY_CHOICES + Residente.ESTADO_CIVIL_CHOICES, required=False)
    mae_falecida = forms.BooleanField(label='Mãe é falecida?', required=False)
    responsavel = forms.CharFieldPlus(max_length=255, label='Nome do Responsável', required=False, width=500, help_text='Obrigatório para menores de idade.')
    email_responsavel = forms.CharFieldPlus(max_length=255, label='Email do Responsável', required=False, width=500)
    parentesco_responsavel = forms.ChoiceField(label='Parenteste com Responsável', choices=[['', '---------']] + Residente.PARENTESCO_CHOICES, required=False)
    cpf_responsavel = forms.BrCpfField(label='CPF do Responsável', required=False)

    # contato
    telefone_principal = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Principal', help_text='(XX) XXXX-XXXX')
    telefone_secundario = forms.BrTelefoneField(max_length=255, required=False, label='Telefone Secundário', help_text='(XX) XXXX-XXXX')
    telefone_adicional_1 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    telefone_adicional_2 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    email_pessoal = forms.EmailField(max_length=255, required=False, label='E-mail Pessoal')

    # outras informacoes
    tipo_sanguineo = forms.ChoiceField(required=False, label='Tipo Sanguíneo', choices=Residente.EMPTY_CHOICES + Residente.TIPO_SANGUINEO_CHOICES)
    pais_origem = forms.ModelChoiceField(Pais.objects, required=False, label='País de Origem', help_text='Obrigatório para estrangeiros')

    estado_naturalidade = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado de Origem', required=False)
    naturalidade = forms.ModelChoiceFieldPlus(
        Municipio.objects,
        label='Naturalidade',
        required=True,
        widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS),
    )

    raca = forms.ModelChoiceField(Raca.objects.all(), required=False, label='Raça')

    # necessidades especiais
    aluno_pne = forms.ChoiceField(label='Portador de Necessidades Especiais', required=True, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    tipo_necessidade_especial = forms.ChoiceField(required=False, label='Deficiência', choices=[['', '---------']] + Residente.TIPO_NECESSIDADE_ESPECIAL_CHOICES)
    tipo_transtorno = forms.ChoiceField(required=False, label='Transtorno', choices=[['', '---------']] + Residente.TIPO_TRANSTORNO_CHOICES)
    superdotacao = forms.ChoiceField(required=False, label='Superdotação', choices=[['', '---------']] + Residente.SUPERDOTACAO_CHOICES)
    outras_necessidades = forms.CharField(max_length=255, required=False, label='Outras necessidades')

    # dados escolares
    nivel_ensino_anterior = forms.ModelChoiceField(NivelEnsino.objects, required=True, label='Nível de Ensino')
    tipo_instituicao_origem = forms.ChoiceField(required=True, label='Tipo da Instituição', choices=[['', '---------']] + Residente.TIPO_INSTITUICAO_ORIGEM_CHOICES)
    nome_instituicao_anterior = forms.CharField(max_length=255, required=False, label='Nome da Instituição')
    ano_conclusao_estudo_anterior = forms.ModelChoiceField(Ano.objects, required=True, label='Ano de Conclusão', help_text='Obrigatório para alunos com nível médio')

    categoria = forms.ChoiceField(choices=Residente.EMPTY_CHOICES + Residente.CATEGORIAS_CHOICES, required=True, label='Categoria')
    # conselho classe
    numero_registro = forms.CharField(max_length=255, required=False, label='Número de Registro')
    conselho = forms.ModelChoiceField(ConselhoProfissional.objects, required=False, label='Conselho')
    lotacao = forms.CharField(max_length=255, required=False, label='Lotação')

    # rg
    numero_rg = forms.CharField(max_length=255, required=False, label='Número do RG')
    uf_emissao_rg = forms.ModelChoiceField(UnidadeFederativa.objects, required=False, label='Estado Emissor')
    orgao_emissao_rg = forms.ModelChoiceField(OrgaoEmissorRg.objects, required=False, label='Orgão Emissor')
    data_emissao_rg = forms.DateFieldPlus(required=False, label='Data de Emissão')

    # titulo_eleitor
    numero_titulo_eleitor = forms.CharField(max_length=255, required=False, label='Título de Eleitor')
    zona_titulo_eleitor = forms.CharField(max_length=255, required=False, label='Zona')
    secao = forms.CharField(max_length=255, required=False, label='Seção')
    data_emissao_titulo_eleitor = forms.DateFieldPlus(required=False, label='Data de Emissão')
    uf_emissao_titulo_eleitor = forms.ModelChoiceField(UnidadeFederativa.objects, required=False, label='Estado Emissor')

    # carteira de reservista
    numero_carteira_reservista = forms.CharField(max_length=255, required=False, label='Número da Carteira de Reservista')
    regiao_carteira_reservista = forms.CharField(max_length=255, required=False, label='Região')
    serie_carteira_reservista = forms.CharField(max_length=255, required=False, label='Série')
    estado_emissao_carteira_reservista = forms.ModelChoiceField(UnidadeFederativa.objects, required=False, label='Estado Emissor')
    ano_carteira_reservista = forms.IntegerField(required=False, label='Ano')

    # certidao_civil
    tipo_certidao = forms.ChoiceField(required=True, label='Tipo de Certidão', choices=Residente.TIPO_CERTIDAO_CHOICES)
    cartorio = forms.CharField(max_length=255, required=False,label='Cartório')
    numero_certidao = forms.CharField(max_length=255, required=False, label='Número de Termo')
    folha_certidao = forms.CharField(max_length=255, required=False, label='Folha')
    livro_certidao = forms.CharField(max_length=255, required=False, label='Livro')
    data_emissao_certidao = forms.DateFieldPlus(required=False, label='Data de Emissão')
    matricula_certidao = forms.CharField(max_length=255, required=False, label='Matrícula', help_text='Obrigatório para certidões realizadas a partir de 01/01/2010')

    observacao_matricula = forms.CharField(widget=forms.Textarea(), required=False, label='Observação')

    utiliza_transporte_escolar_publico = forms.ChoiceField(label='Utiliza Transporte Escolar Público', required=False, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    poder_publico_responsavel_transporte = forms.ChoiceField(
        label='Poder Público Responsável pelo Transporte Escolar', choices=[['', '---------']] + Residente.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, required=False
    )
    tipo_veiculo = forms.ChoiceField(label='Tipo de Veículo Utilizado no Transporte Escolar', choices=[['', '---------']] + Residente.TIPO_VEICULO_CHOICES_FOR_FORM, required=False)

    db_banco = forms.ChoiceField(label="Banco", choices=Residente.EMPTY_CHOICES + DadosBancariosPF.BANCO_CHOICES, required=False)
    db_numero_agencia = forms.CharField(label="Número da Agência", required=False, max_length=50, help_text="Ex: 3293-X")
    db_tipo_conta = forms.ChoiceField(label="Tipo da Conta", required=False, choices=Residente.EMPTY_CHOICES + DadosBancariosPF.TIPOCONTA_CHOICES)
    db_numero_conta = forms.CharField(label='Número da Conta', required=False, widget=forms.TextInput(attrs={'pattern': '[0-9a-zA-Z]+'}), help_text='Utilize apenas números e letras')
    db_operacao = forms.CharField(label="Operação", max_length=50, required=False)

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), required=True, label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(required=True, label='Período Letivo', choices=Residente.PERIODO_LETIVO_CHOICES)
    matriz_curso = forms.ModelChoiceFieldPlus(MatrizCurso.objects, required=True, label='Matriz/Curso')

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
                        'email_responsavel',
                        'parentesco_responsavel',
                        'cpf_responsavel',
                    )
                },
            ),
            ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'estado', 'cidade', 'tipo_zona_residencial')}),
        ],
        [
            ('Informações para Contato', {'fields': ('telefone_principal', 'telefone_secundario', 'telefone_adicional_1', 'telefone_adicional_2', 'email_pessoal')}),
            ('Deficiências, Transtornos e Superdotação', {'fields': ('aluno_pne', 'tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao', 'outras_necessidades')}),
            ('Transporte Escolar Utilizado', {'fields': ('utiliza_transporte_escolar_publico', 'poder_publico_responsavel_transporte', 'tipo_veiculo')}),
            ('Outras Informações', {'fields': ('tipo_sanguineo', 'pais_origem', 'estado_naturalidade', 'naturalidade', 'raca')}),
            ('Dados Escolares Anteriores', {'fields': ('nivel_ensino_anterior', 'tipo_instituicao_origem', 'nome_instituicao_anterior', 'ano_conclusao_estudo_anterior')}),
        ],
        [
            ('Conselho de Fiscalização Profissional', {'fields': ('categoria', 'conselho', 'numero_registro', 'lotacao')}),
            ('Dados Bancários', {'fields': ('db_banco', 'db_numero_agencia', 'db_tipo_conta', 'db_numero_conta', 'db_operacao')}),
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
                        'matriz_curso',
                    )
                },
            ),
            ('Observação', {'fields': ('observacao_matricula',)}),
        ],
    )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_ano_conclusao_estudo_anterior(self):
        ano_conclusao_estudo_anterior = self.cleaned_data.get('ano_conclusao_estudo_anterior')
        nivel_ensino_anterior = self.data.get('nivel_ensino_anterior')
        if nivel_ensino_anterior == str(NivelEnsino.MEDIO) and not ano_conclusao_estudo_anterior:
            raise forms.ValidationError('O Ano de Conclusão é de preenchimento obrigatório.')
        return ano_conclusao_estudo_anterior

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

        if aluno_pne == 'Sim' and not (self.data.get('tipo_necessidade_especial') or self.data.get('tipo_transtorno') or self.data.get('superdotacao') or self.data.get('outras_necessidades')):
            raise forms.ValidationError('Informe a deficiência, transtorno ou superdotação do aluno.')
        return aluno_pne

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

    def clean_data_nascimento(self):
        menor_data_valida = datetime.datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S').date()
        if 'data_nascimento' in self.cleaned_data and self.cleaned_data['data_nascimento'] < menor_data_valida:
            raise forms.ValidationError('Data de nascimento deve ser maior que 01/01/1900.')
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
        nome_pais = 'Brasil'
        if naturalidade and hasattr(naturalidade, 'pais'):
            nome_pais = naturalidade.pais.nome
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

    def clean(self):
        if 'db_banco' in self.cleaned_data and self.cleaned_data['db_banco']:
            if (
                    'db_numero_agencia' not in self.cleaned_data
                    or ('db_numero_agencia' in self.cleaned_data and not self.cleaned_data['db_numero_agencia'])
            ):
                raise forms.ValidationError("Não é possível adicionar uma conta bancária sem número da agência.")
            if (
                    'db_tipo_conta' not in self.cleaned_data
                    or ('db_tipo_conta' in self.cleaned_data and not self.cleaned_data['db_tipo_conta'])
            ):
                raise forms.ValidationError("Não é possível adicionar uma conta bancária sem tipo da conta.")
            if (
                    'db_numero_conta' not in self.cleaned_data
                    or ('db_numero_conta' in self.cleaned_data and not self.cleaned_data['db_numero_conta'])
            ):
                raise forms.ValidationError("Não é possível adicionar uma conta bancária sem número da conta.")
        return self.cleaned_data

    def next_step(self):
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
                self.fields['naturalidade'].queryset = Municipio.objects.filter(codigo__isnull=False)
                self.fields['naturalidade'].help_text = 'Cidade em que o aluno nasceu. Obrigatório para brasileiros'
            elif nacionalidade and nacionalidade == 'Estrangeira':
                self.fields['naturalidade'].queryset = Municipio.objects.filter(codigo__isnull=True)
                self.fields['naturalidade'].help_text = 'Cidade/Província em que o aluno nasceu.'

    @transaction.atomic
    def processar(self):
        pessoa_fisica = PessoaFisica()
        pessoa_fisica.cpf = self.cleaned_data['cpf']
        pessoa_fisica.nome_registro = self.cleaned_data['nome']
        pessoa_fisica.nome_social = self.cleaned_data['nome_social']
        pessoa_fisica.sexo = self.cleaned_data['sexo']
        pessoa_fisica.nascimento_data = self.cleaned_data['data_nascimento']
        pessoa_fisica.save()

        residente = Residente()
        residente.periodo_atual = 1
        residente.pessoa_fisica = pessoa_fisica

        residente.curso_campus = self.cleaned_data['matriz_curso'].curso_campus
        residente.matriz = self.cleaned_data['matriz_curso'].matriz

        residente.estado_civil = self.cleaned_data['estado_civil']
        # dados familiares
        residente.nome_pai = self.cleaned_data['nome_pai']
        residente.estado_civil_pai = self.cleaned_data['estado_civil_pai']
        residente.pai_falecido = self.cleaned_data['pai_falecido']
        residente.nome_mae = self.cleaned_data['nome_mae']
        residente.estado_civil_mae = self.cleaned_data['estado_civil_mae']
        residente.mae_falecida = self.cleaned_data['mae_falecida']
        residente.responsavel = self.cleaned_data['responsavel']
        residente.cpf_responsavel = self.cleaned_data['cpf_responsavel']
        residente.parentesco_responsavel = self.cleaned_data['parentesco_responsavel']
        # endereco
        residente.logradouro = self.cleaned_data['logradouro']
        residente.numero = self.cleaned_data['numero']
        residente.complemento = self.cleaned_data['complemento']
        residente.bairro = self.cleaned_data['bairro']
        residente.cep = self.cleaned_data['cep']
        residente.cidade = self.cleaned_data['cidade']
        residente.tipo_zona_residencial = self.cleaned_data['tipo_zona_residencial']
        # contato
        residente.telefone_principal = self.cleaned_data['telefone_principal']
        residente.telefone_secundario = self.cleaned_data['telefone_secundario']
        residente.telefone_adicional_1 = self.cleaned_data['telefone_adicional_1']
        residente.telefone_adicional_2 = self.cleaned_data['telefone_adicional_2']

        # transporte escolar
        if self.cleaned_data['utiliza_transporte_escolar_publico']:
            residente.poder_publico_responsavel_transporte = self.cleaned_data['poder_publico_responsavel_transporte']
            residente.tipo_veiculo = self.cleaned_data['tipo_veiculo']
        else:
            residente.poder_publico_responsavel_transporte = None
            residente.tipo_veiculo = None

        # outras informacoes
        residente.tipo_sanguineo = self.cleaned_data['tipo_sanguineo']
        residente.nacionalidade = self.cleaned_data['nacionalidade']
        residente.passaporte = self.cleaned_data['passaporte']
        residente.naturalidade = self.cleaned_data['naturalidade']
        residente.pessoa_fisica.raca = self.cleaned_data['raca']

        if self.cleaned_data['aluno_pne']:
            residente.tipo_necessidade_especial = self.cleaned_data['tipo_necessidade_especial']
            residente.tipo_transtorno = self.cleaned_data['tipo_transtorno']
            residente.superdotacao = self.cleaned_data['superdotacao']
            residente.outras_necessidades = self.cleaned_data['outras_necessidades']
        else:
            residente.tipo_necessidade_especial = None
            residente.tipo_transtorno = None
            residente.superdotacao = None
            residente.outras_necessidades = None

        # dados escolares
        residente.nivel_ensino_anterior = self.cleaned_data['nivel_ensino_anterior']
        residente.tipo_instituicao_origem = self.cleaned_data['tipo_instituicao_origem']
        residente.nome_instituicao_anterior = self.cleaned_data['nome_instituicao_anterior']
        residente.ano_conclusao_estudo_anterior = self.cleaned_data['ano_conclusao_estudo_anterior']
        residente.categoria = self.cleaned_data['categoria']
        # conselho classe
        residente.numero_registro = self.cleaned_data['numero_registro']
        residente.conselho = self.cleaned_data['conselho']
        # rg
        residente.numero_rg = self.cleaned_data['numero_rg']
        residente.uf_emissao_rg = self.cleaned_data['uf_emissao_rg']
        residente.orgao_emissao_rg = self.cleaned_data['orgao_emissao_rg']
        residente.data_emissao_rg = self.cleaned_data['data_emissao_rg']
        # titulo_eleitor
        residente.numero_titulo_eleitor = self.cleaned_data['numero_titulo_eleitor']
        residente.zona_titulo_eleitor = self.cleaned_data['zona_titulo_eleitor']
        residente.secao = self.cleaned_data['secao']
        residente.data_emissao_titulo_eleitor = self.cleaned_data['data_emissao_titulo_eleitor']
        residente.uf_emissao_titulo_eleitor = self.cleaned_data['uf_emissao_titulo_eleitor']
        # carteira de reservista
        residente.numero_carteira_reservista = self.cleaned_data['numero_carteira_reservista']
        residente.regiao_carteira_reservista = self.cleaned_data['regiao_carteira_reservista']
        residente.serie_carteira_reservista = self.cleaned_data['serie_carteira_reservista']
        residente.estado_emissao_carteira_reservista = self.cleaned_data['estado_emissao_carteira_reservista']
        residente.ano_carteira_reservista = self.cleaned_data['ano_carteira_reservista']
        # certidao_civil
        residente.tipo_certidao = self.cleaned_data['tipo_certidao']
        residente.cartorio = self.cleaned_data['cartorio']
        residente.numero_certidao = self.cleaned_data['numero_certidao']
        residente.folha_certidao = self.cleaned_data['folha_certidao']
        residente.livro_certidao = self.cleaned_data['livro_certidao']
        residente.data_emissao_certidao = self.cleaned_data['data_emissao_certidao']
        residente.matricula_certidao = self.cleaned_data['matricula_certidao']

        # dados da matrícula
        residente.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
        residente.ano_letivo = self.cleaned_data['ano_letivo']
        residente.periodo_letivo = self.cleaned_data['periodo_letivo']
        residente.matriz = self.cleaned_data['matriz_curso'].matriz


        hoje = datetime.date.today()
        ano = hoje.year
        prefixo = f'{ano}RES'
        residente.matricula = SequencialMatriculaResidente.proximo_numero(prefixo)
        residente.email_scholar = ''
        residente.save()

        observacao = self.cleaned_data['observacao_matricula']
        if observacao:
            obs = Observacao()
            obs.residente = residente
            obs.data = datetime.datetime.now()
            obs.observacao = observacao
            obs.usuario = self.request.user
            obs.save()

        residente.pessoa_fisica.username = self.cleaned_data['cpf'].replace('.', '').replace('-', '')
        residente.pessoa_fisica.email_secundario = self.cleaned_data['email_pessoal']
        residente.pessoa_fisica.save()

        if 'db_banco' in self.cleaned_data:
            DadosBancariosPF.objects.create(
                pessoa_fisica=residente.pessoa_fisica,
                banco=self.cleaned_data['db_banco'],
                numero_agencia=self.cleaned_data['db_numero_agencia'],
                tipo_conta=self.cleaned_data['db_tipo_conta'],
                numero_conta=self.cleaned_data['db_numero_conta'],
                operacao=self.cleaned_data['db_operacao'],
            )

        if 'foto' in self.cleaned_data and self.cleaned_data.get('foto'):
            residente.foto.save(f'{residente.pk}.jpg', ContentFile(self.cleaned_data['foto']))
        elif 'arquivo_foto' in self.cleaned_data and self.cleaned_data.get('arquivo_foto'):
            residente.foto.save(f'{residente.pk}.jpg', ContentFile(self.cleaned_data.get('arquivo_foto').read()))

        residente.save()

        matricula_periodo = MatriculaPeriodo()
        matricula_periodo.residente = residente
        matricula_periodo.ano_letivo = residente.ano_letivo
        matricula_periodo.periodo_letivo = residente.periodo_letivo
        matricula_periodo.periodo_matriz = 1
        matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
        matricula_periodo.save()

        return residente


class ObservacaoForm(forms.ModelForm):
    class Meta:
        model = Observacao
        exclude = ('residente', 'usuario', 'data')

    def __init__(self, residente, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.residente = residente
        self.usuario = usuario

    def save(self, *args, **kwargs):
        self.instance.residente = self.residente
        self.instance.usuario = self.usuario
        self.instance.data = datetime.datetime.now()
        self.instance.save()


class SecretarioResidenciaForm(EmpregadoFesfForm):

    fieldsets = (
        ('Dados Pessoais', {'fields': ('nome_registro', 'cpf', 'matricula', 'passaporte', 'nacionalidade', 'sexo', 'nascimento_data', 'nome_pai', 'nome_mae', 'naturalidade')}),
        ('RG', {'fields': ('rg', 'rg_orgao', 'rg_data', 'rg_uf')}),
        ('Endereço', {'fields': ('cep', 'municipio', 'logradouro', 'numero', 'complemento', 'bairro')}),
        ('Dados para Contato', {'fields': ('email', 'telefone')}),
        ('Dados funcionais', {'fields': ('setor','situacao',)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        empregado = super().save(*args, **kwargs)
        return empregado


#FES-26

class CoordenadorResidenciaForm(EmpregadoFesfForm):

    fieldsets = (
        ('Dados Pessoais', {'fields': ('nome_registro', 'cpf', 'matricula', 'passaporte', 'nacionalidade', 'sexo', 'nascimento_data', 'nome_pai', 'nome_mae', 'naturalidade')}),
        ('RG', {'fields': ('rg', 'rg_orgao', 'rg_data', 'rg_uf')}),
        ('Endereço', {'fields': ('cep', 'municipio', 'logradouro', 'numero', 'complemento', 'bairro')}),
        ('Dados para Contato', {'fields': ('email', 'telefone')}),
        ('Dados funcionais', {'fields': ('setor','situacao',)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        empregado = super().save(*args, **kwargs)
        coordenador_residencia = Group.objects.get(name='Coordenadores(as) Residência')
        if coordenador_residencia:
            coordenador_residencia.user_set.add(empregado.get_vinculo().user)

        return empregado


class PreceptorResidenciaForm(EmpregadoFesfForm):

    fieldsets = (
        ('Dados Pessoais', {'fields': ('nome_registro', 'cpf', 'matricula', 'passaporte', 'nacionalidade', 'sexo', 'nascimento_data', 'nome_pai', 'nome_mae', 'naturalidade')}),
        ('RG', {'fields': ('rg', 'rg_orgao', 'rg_data', 'rg_uf')}),
        ('Endereço', {'fields': ('cep', 'municipio', 'logradouro', 'numero', 'complemento', 'bairro')}),
        ('Dados para Contato', {'fields': ('email', 'telefone')}),
        ('Dados funcionais', {'fields': ('setor','situacao',)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        empregado = super().save(*args, **kwargs)
        return empregado


class ComponenteForm(forms.ModelFormPlus):
    class Meta:
        model = Componente
        exclude = ('sigla',)

    class Media:
        js = ('/static/residencia/js/ComponenteForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #     componente = super().save(*args, **kwargs)
    #     ComponenteCurricular.objects.filter(componente=componente, ch_pratica=0).update(ch_presencial=componente.ch_hora_relogio)
    #     return componente


class ComponenteCurricularForm(forms.ModelFormPlus):
    periodo_letivo = forms.ChoiceField(required=False)
    matriz = forms.ModelChoiceField(queryset=Matriz.objects, widget=forms.HiddenInput())
    componente = forms.ModelChoiceFieldPlus(Componente.objects)
    unidade_aprendizagem = forms.ModelChoiceFieldPlus(UnidadeAprendizagem.objects)

    SUBMIT_LABEL = 'Vincular Atividade'
    EXTRA_BUTTONS = [dict(name='continuar', value='Vincular Componente e continuar vinculando')]

    class Meta:
        model = ComponenteCurricular
        exclude = ('avaliacao_por_conceito', )

    class Media:
        js = ('/static/edu/js/ComponenteCurricularForm.js',)

    def __init__(self, matriz, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.matriz = matriz
        self.fields['componente'].queryset = self.fields['componente'].queryset.all()
        self.fields['pre_requisitos'].queryset = self.fields['pre_requisitos'].queryset.filter(matriz=self.matriz)
        self.fields['periodo_letivo'].choices = [['', '-----']] + [[x, x] for x in range(1, self.matriz.qtd_periodos_letivos + 1)]
        self.fields['matriz'].initial = self.matriz.pk
        self.fields['ch_total'].initial = 0
        self.fields['ch_total'].required = True

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
                    'unidade_aprendizagem',
                    ('periodo_letivo', 'tipo'),
                )
            },
        ),
        ('Carga Horária', {'fields': (('ch_total', 'ch_cumprimento')),}),
        ('Frequência', {'fields': (('registro_freq',)),}),
        ('Plano de Ensino', {'fields': ('ementa',)}),
    )

    def clean_componente(self):
        if ComponenteCurricular.objects.filter(matriz=self.matriz, componente=self.cleaned_data['componente']).exists() and not self.instance.pk:
            raise forms.ValidationError('Componente já vinculado a esta matriz.')
        return self.cleaned_data['componente']

    def clean(self):
        if self.instance.pk:
            cc_salvo = ComponenteCurricular.objects.get(pk=self.instance.pk)
            periodo_letivo = self.cleaned_data.get('periodo_letivo')
            if periodo_letivo and int(periodo_letivo) != cc_salvo.periodo_letivo and (cc_salvo.co_requisitos.all() or cc_salvo.pre_requisitos.all()):
                raise forms.ValidationError('Não é possível alterar o período do componente na matriz, pois ele possui pré/co-requisitos.')
        return self.cleaned_data


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


class MatrizForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Matriz
        exclude = ()

    def clean(self):

        return self.cleaned_data


class MatrizCursoForm(forms.ModelFormPlus):
    curso_campus = forms.ModelChoiceField(queryset=CursoResidencia.objects, widget=forms.HiddenInput())
    matriz = forms.ModelChoiceField(queryset=Matriz.objects, widget=AutocompleteWidget(search_fields=Matriz.SEARCH_FIELDS), label='Matriz', required=True)

    class Meta:
        model = MatrizCurso
        exclude = ()

    fieldsets = (
        ('Dados Gerais', {'fields': ('curso_campus', 'matriz')}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso_campus'].queryset = CursoResidencia.locals.all()

    def clean_matriz(self):
        if MatrizCurso.objects.exclude(pk=self.instance.pk or 0).filter(matriz=self.cleaned_data['matriz'], curso_campus=self.cleaned_data['curso_campus']).exists():
            raise forms.ValidationError('Par matriz/curso já cadastrado.')
        else:
            return self.cleaned_data['matriz']


class EstruturaCursoForm(forms.ModelFormPlus):
    criterio_avaliacao = forms.ChoiceField(label='Critério de Avaliação', widget=forms.RadioSelect(), choices=EstruturaCurso.CRITERIO_AVALIACAO_CHOICES)

    class Meta:
        model = EstruturaCurso
        exclude = ()

    class Media:
        js = ('/static/residenca/js/EstruturaCursoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CursoResidenciaForm(forms.ModelFormPlus):

    class Meta:
        model = CursoResidencia
        exclude = ()

    class Media:
        js = ('/static/edu/js/CursoCampusForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['coordenador'].queryset = Funcionario.objects.filter(excluido=False)

    def save(self, *args, **kwargs):
        curso_residencia = super().save(*args, **kwargs)
        if curso_residencia.coordenador:
            user = User.objects.get(username=curso_residencia.coordenador.username)
            group = Group.objects.get(name='Coordenadores(as) Residência')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(user=user, group=group)[0]   
        return curso_residencia


class DefinirCoordenadorCursoForm(forms.ModelFormPlus):
    class Meta:
        model = CursoResidencia
        fields = ('coordenador',)

    def processar(self, curso_residencia):
        funcionario = self.cleaned_data['coordenador']
        if funcionario:
            user = User.objects.get(username=funcionario.username)
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR'], user=user)[0]

        self.save()


class AnalisarSolicitacaoResidenteForm(forms.ModelForm):
    SUBMIT_LABEL = 'Salvar Análise'

    situacao = forms.ChoiceField(
        required=True, choices=SolicitacaoResidente.STATUS_CHOICES,
        widget=forms.RadioSelect(), label='Situação da Solicitação'
    )
    parecer = forms.CharField(widget=forms.Textarea(), label='Parecer da Solicitação')
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), required=True, label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(required=True, label='Período Letivo', choices=Residente.PERIODO_LETIVO_CHOICES)
    matriz_curso = forms.ModelChoiceFieldPlus(MatrizCurso.objects, required=True, label='Matriz/Curso')


    class Meta:
        model = SolicitacaoResidente
        fields = ('situacao', 'parecer', 'matriz_curso')

#Wanderson - Comentei algumas linhas por causa de alguns erros
#as linhas do init pq tavam dando RelatedObjectDoesNotExist at /admin/residencia/turma/add/
#Turma has no ano_letivo.
#e comentei as do formulario pq estavam como readonly
class TurmaForm(forms.ModelFormPlus):
    codigo = forms.CharField(label='Código', widget=forms.TextInput())
    descricao = forms.CharField(label='Descrição', widget=forms.Textarea())
    #codigo = forms.CharField(label='Código', widget=forms.TextInput(attrs=dict(readonly='readonly')))
    #descricao = forms.CharField(label='Descrição', widget=forms.Textarea(attrs=dict(readonly='readonly')))
    sigla = forms.CharFieldPlus(label='Sigla', required=False)
    calendario_academico = forms.ModelChoiceField(queryset=CalendarioAcademico.objects, label='Calendário Acadêmico', required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['calendario_academico'].queryset = CalendarioAcademico.objects.filter(
        #      ano_letivo=self.instance.ano_letivo, periodo_letivo=self.instance.periodo_letivo
        # )


    @transaction.atomic()
    def save(self, *args, **kwargs):
        turma = super().save(*args, **kwargs)
        for diario in turma.diarios_turma_residencia_set.all():
            if diario.quantidade_vagas != turma.quantidade_vagas:
                diario.quantidade_vagas = turma.quantidade_vagas
                diario.save()
        return turma

    class Meta:
        model = Turma
        exclude = (
            #'ano_letivo', 
            #'periodo_letivo', 
            #'periodo_matriz', 
            #'turno', 
            #'curso_campus', 
            #'matriz', 
            #'sequencial',
            )


class CalendarioAcademicoForm(forms.ModelFormPlus):
    qtd_etapas = forms.ChoiceField(widget=forms.RadioSelect(), choices=CalendarioAcademico.QTD_ETAPAS_CHOICES, initial=1)
    class Meta:
        model = CalendarioAcademico
        exclude = ()

    class Media:
        js = ('/static/residencia/js/CalendarioAcademicoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class GerarTurmasForm(FormWizardPlus):
    METHOD = 'GET'
    QTD_TURMAS_CHOICES = [[0, '0'], [1, '1'], [2, '2'], [3, '3'], [4, '4'], [5, '5'], [6, '6'], [7, '7'], [8, '8'], [9, '9']]

    class Media:
        js = ('/static/residencia/js/GerarTurmasForm.js',)

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', help_text='Formato: <strong>[2014]</strong>1.1.011004.1M')
    periodo_letivo = forms.ChoiceField(label='Período Letivo', choices=Residente.PERIODO_LETIVO_CHOICES, help_text='Formato: 2014<strong>[1]</strong>.1.011004.1M')
    tipo_componente = forms.ChoiceField(label='Tipo dos Componentes', choices=[[1, 'Obrigatório'], [0, 'Optativo']])
    matriz_curso = forms.ModelChoiceFieldPlus(
        MatrizCurso.objects, label='Matriz/Curso', help_text='Formato: 20141.1.<strong>[011004]</strong>.1M', widget=AutocompleteWidget(search_fields=MatrizCurso.SEARCH_FIELDS)
    )

    qtd_periodo_1 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)
    qtd_periodo_2 = forms.ChoiceField(label='Nº de Turmas', required=False, choices=QTD_TURMAS_CHOICES)

    vagas_periodo_1 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    vagas_periodo_2 = forms.IntegerFieldPlus(label='Nº de Vagas', required=False)
    calendario_academico = forms.ModelChoiceField(CalendarioAcademico.objects, label='Calendário Acadêmico')
    componentes = forms.MultipleModelChoiceField(ComponenteCurricular.objects, label='', widget=RenderableSelectMultiple('widgets/componentes_residencia_widget.html'))
    confirmacao = forms.BooleanField(
        label='Confirmação', required=True, help_text='Marque a opção acima e clique no botão "Finalizar" caso deseje que as turmas/diários identificados acima sejam criados.'
    )

    steps = (
        [('Dados do Curso', {'fields': ('ano_letivo',
                                        'periodo_letivo',
                                        'tipo_componente',
                                        'matriz_curso')})],
        [
            ('1º Ano', {'fields': ('qtd_periodo_1',  'vagas_periodo_1')}),
            ('2º Ano', {'fields': ('qtd_periodo_2', 'vagas_periodo_2')}),
        ],
        [
            ('Calendário e Componentes', {'fields': ( 'calendario_academico',)}), 
            ('Seleção de Componentes', {'fields': ('componentes',)})
        ],
        [('Confirmação dos Dados', {'fields': ('confirmacao',)})],
    )

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_matriz_curso(self):
        if not self.data.get('ano_letivo') or not self.data.get('periodo_letivo'):
            return forms.ValidationError(mark_safe('Matriz Curso inválida.'))
        matriz_curso = MatrizCurso.objects.get(id=self.data['matriz_curso'])
        is_secretario = in_group(self.request.user, 'Secretário(a) Residência,Coordenadores(as) Residência')

        return matriz_curso

    def clean_calendario_academico(self):
        calendario_academico = self.cleaned_data['calendario_academico']
        matriz_curso = self.cleaned_data['matriz_curso']
        # if calendario_academico:
        #     qtd_avaliacoes = matriz_curso.matriz.componentecurricular_set.all().aggregate(Max('qtd_avaliacoes')).get('qtd_avaliacoes__max') or 0
        #     if calendario_academico.qtd_etapas < qtd_avaliacoes:
        #         raise ValidationError(
        #             f'A matriz possui componentes com {qtd_avaliacoes} etapas, mas o calendário selecionado possui apenas {calendario_academico.qtd_etapas}.'
        #         )
        return calendario_academico

    def next_step(self):
        ano_letivo = self.get_entered_data('ano_letivo')
        periodo_letivo = self.get_entered_data('periodo_letivo')
        matriz_curso = self.get_entered_data('matriz_curso')

        if 'matriz_curso' in self.fields:
            self.fields['matriz_curso'].queryset = MatrizCurso.objects.filter(curso_campus__ativo=True, matriz__ativo=True)
        if 'calendario_academico' in self.fields and matriz_curso and ano_letivo and periodo_letivo:
            qs_calendario_academico = CalendarioAcademico.objects.filter(
                ano_letivo=ano_letivo, periodo_letivo=periodo_letivo, tipo=CalendarioAcademico.TIPO_ANUAL
            )
            self.fields['calendario_academico'].queryset = qs_calendario_academico
        if matriz_curso:
            for i in range(matriz_curso.matriz.qtd_periodos_letivos + 1, 3):
                if f'qtd_periodo_{i}' in self.fields:
                    self.fields[f'qtd_periodo_{i}'].required = False
                    self.fields[f'turno_periodo_{i}'].required = False
                    self.fields[f'vagas_periodo_{i}'].required = False
                    self.fields[f'qtd_periodo_{i}'].widget = forms.HiddenInput()
                    self.fields[f'vagas_periodo_{i}'].widget = forms.HiddenInput()
        if 'componentes' in self.fields and matriz_curso:
            matriz_curso = matriz_curso
            periodos = []
            for i in range(1, matriz_curso.matriz.qtd_periodos_letivos + 1):
                if int(self.get_entered_data(f'qtd_periodo_{i}') or 0):
                    periodos.append(i)

            qs = matriz_curso.matriz.componentecurricular_set.all()
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
            numero_vagas_dict[i] = self.cleaned_data[f'vagas_periodo_{i}'] or 0

        calendario_academico = self.cleaned_data['calendario_academico']
        componentes = self.cleaned_data['componentes']
        confirmacao = self.cleaned_data.get('confirmacao')
        commit = commit and confirmacao
        self.turmas = Turma.gerar_turmas(
            ano_letivo,
            periodo_letivo,
            numero_vagas_dict,
            numero_turmas_dict,
            matriz_curso.curso_campus,
            matriz_curso.matriz,
            calendario_academico,
            componentes,
            commit,
        )

#FES-68

class ProjetoFinalResidenciaForm(forms.ModelFormPlus):
    #uo = forms.ModelChoiceField(UnidadeOrganizacional.locals, label='Campus', required=False)
    # local_defesa = forms.ModelChoiceFieldPlus(
    #     Sala.ativas, label='Local', required=False, widget=AutocompleteWidget(search_fields=Sala.SEARCH_FIELDS, form_filters=[('uo', 'predio__uo__in')])
    # )
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, required=True, label='Período Letivo')
    orientador = forms.ModelChoiceField(queryset=Vinculo.objects, widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS), label='Orientador', required=True)
    presidente = forms.ModelChoiceField(queryset=Servidor.objects.filter(user__groups__name = "Preceptor(a)"), widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS), label='Preceptor', required=True)
    
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
        model = ProjetoFinalResidencia
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

    def __init__(self, residente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not residente.matriz or not residente.matriz.exige_tcr:
            self.fields['tipo'].choices = [['Memorial de Formação', 'Relato de Experiência','Orientação do Trabalho de Conclusão de Residência']]
        if self.instance.pk:
            self.fields['ano_letivo'].initial = self.instance.matricula_periodo.ano_letivo.pk
            self.fields['periodo_letivo'].initial = self.instance.matricula_periodo.periodo_letivo
        self.residente = residente
        qs_prestadores = Vinculo.objects.prestadores()
        qs_servidores = Vinculo.objects.servidores()
        if not in_group(self.request.user, 'Coordenadores(as) Residênciao,Secretário(a) Residência'):
            if not self.instance.pk:
                qs_servidores = qs_servidores.filter(pessoa__excluido=False)
            else:
                qs_servidores = qs_servidores.filter(pessoa__excluido=False) | qs_servidores.filter(pessoa__excluido=True, pk__in=[self.instance.orientador.vinculo.pk])
            qs_prestadores = qs_prestadores.filter(pessoa__excluido=False)
        self.fields['orientador'].queryset = (qs_servidores | qs_prestadores).distinct()
        if self.instance.pk:
            self.fields['orientador'].initial = self.instance.orientador.get_vinculo().id

        qs_pessoafisica = PessoaFisica.objects.filter(excluido=False).exclude(eh_aluno=True)
        if Configuracao.get_valor_por_chave('residencia', 'tipo_ata_projeto_final') == 'eletronica':
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
            qs_matricula_periodo = MatriculaPeriodo.objects.filter(residente=self.residente, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)
            if not qs_matricula_periodo.exists():
                raise forms.ValidationError('O residente não possui matrícula no período ano/período letivo selecionado.')
            else:
                self.matricula_periodo = qs_matricula_periodo[0]
                if not self.matricula_periodo.situacao.pk == SituacaoMatriculaPeriodo.MATRICULADO:
                    raise forms.ValidationError('A situação do residente no período selecionado não é Matriculado".')
                if ProjetoFinalResidencia.objects.filter(matricula_periodo=self.matricula_periodo).exclude(pk=self.instance.pk).exists():
                    raise forms.ValidationError('O residente já possui um trabalho de conclusão de curso no ano/período letivo selecionado.')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        orientador = self.cleaned_data['orientador']
        obj = super().save(False)
        qs = Servidor.objects.filter(user__groups__name = "Preceptor(a)", vinculo__id=orientador.pk)
        if qs.exists():
            obj.orientador = qs[0]
        else:
            preceptor = Servidor()
            preceptor.vinculo = orientador
            preceptor.save()
            obj.orientador = preceptor
            Group.objects.get(name='Preceptor(a)').user_set.add(preceptor.vinculo.user)
        obj.matricula_periodo = self.matricula_periodo
        obj.save()
        for coorientador in self.cleaned_data['coorientadores']:
            obj.coorientadores.add(coorientador)

        if Configuracao.get_valor_por_chave('residencia', 'tipo_ata_projeto_final') == 'eletronica':
            ata = AtaEletronicaResidencia.objects.filter(projeto_final=obj).first()
            if ata:
                ata.criar_assinaturas()


class ParticipacaoProjetoFinalResidenciaForm(forms.Form):
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


class LancarResultadoProjetoFinalResidenciaForm(forms.ModelForm):
    DOCUMENTO_URL = 1
    DOCUMENTO_ARQUIVO = 2
    TIPO_DOCUMENTO_CHOICES = [[DOCUMENTO_URL, 'URL'], [DOCUMENTO_ARQUIVO, 'Arquivo']]

    resultado_data = forms.DateTimeFieldPlus(label='Data da Apresentação', required=True)
    situacao = forms.ChoiceField(label="Situação", choices=ProjetoFinalResidencia.SITUACAO_CHOICES, required=True)
    tipo_documento = forms.ChoiceField(choices=TIPO_DOCUMENTO_CHOICES, widget=forms.RadioSelect(), label='Tipo de Documento')
    ata = forms.FileFieldPlus(label='Ata de Defesa / Documento Comprobatório de Prática', required=True)
    documento = forms.FileFieldPlus(label='Arquivo do TCR / Relatório', required=False, filetypes=['pdf'])

    class Meta:
        model = ProjetoFinalResidencia
        fields = ('resultado_data', 'nota', 'situacao', 'tipo_documento', 'documento', 'documento_url', 'ata')

    class Media:
        js = ('/static/edu/js/LancarResultadoProjetoFinalForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo_ata = Configuracao.get_valor_por_chave('residencia', 'tipo_ata_projeto_final') or 'fisica'
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
        projeto_final_residencia = super().save(*args, **kwargs)
        if self.tipo_ata == 'eletronica':
            consideracoes = self.cleaned_data['consideracoes']
            if not AtaEletronicaResidencia.objects.filter(projeto_final_residencia=projeto_final_residencia).exists():
                ata = AtaEletronicaResidencia.objects.create(projeto_final_residencia=projeto_final_residencia, consideracoes=consideracoes)
                ata.criar_assinaturas()


class UploadDocumentoProjetoFinalResidenciaForm(forms.ModelForm):
    DOCUMENTO_URL = 1
    DOCUMENTO_ARQUIVO = 2
    TIPO_DOCUMENTO_CHOICES = [[DOCUMENTO_URL, 'URL'], [DOCUMENTO_ARQUIVO, 'Arquivo']]

    tipo_documento_final = forms.ChoiceField(choices=TIPO_DOCUMENTO_CHOICES, widget=forms.RadioSelect(), label='Tipo de Documento')
    documento_final = forms.FileFieldPlus(label='Arquivo do TCR / Relatório', required=False, filetypes=['pdf'])

    class Meta:
        model = ProjetoFinalResidencia
        fields = ('tipo_documento_final', 'documento_final', 'documento_final_url',)

    class Media:
        js = ('/static/edu/js/UploadDocumentoProjetoFinalForm.js',)

    fieldsets = (
        ('Arquivo', {'fields': ('tipo_documento_final', 'documento_final', 'documento_final_url')}),
    )

class DiarioForm(forms.ModelFormPlus):
    class Meta:
        model = Diario
        exclude = (
            #'turma',
            #'componente_curricular',
            #'ano_letivo',
            #'periodo_letivo',
            #'situacao',
            #'estrutura_curso',
            #'calendario_academico',
            #'local_aula',
            #'locais_aula_secundarios',
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


class PreceptorDiarioForm(forms.ModelFormPlus):
    diario = forms.ModelChoiceField(queryset=Diario.objects, widget=forms.HiddenInput())
    preceptor = forms.ModelChoiceField(
        queryset=Servidor.objects,
        label='Preceptor(a)', required=True, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS)
    )

    class Meta:
        model = PreceptorDiario
        exclude = ()

    fieldsets = (('', {'fields': ('diario', 'preceptor', ('tipo', 'ativo'))}), ('Carga Horária', {'fields': (('percentual_ch', ),)}))

    def __init__(self, diario, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['preceptor'].queryset = Servidor.objects.filter(user__groups__name='Preceptor(a)')
        self.fields['diario'].queryset = Diario.objects.all()

        is_administrador = in_group(self.request.user, 'Secretário(a) Residência')
        if not is_administrador:
            self.fields['ativo'].widget = forms.HiddenInput()

        self.diario = diario
        if self.diario:
            self.fields['diario'].initial = self.diario.pk

        for field_name in self.fields:
            if 'data_' in field_name:
                self.fields[field_name].help_text = ''

    def clean_percentual_ch(self):
        if self.cleaned_data.get('percentual_ch') > 100:
            raise forms.ValidationError('O percentual de CH ministrada não pode ser maior que 100%.')
        return self.cleaned_data.get('percentual_ch')

    def clean_preceptor(self):
        qs = self.diario.preceptordiario_set.all()
        if self.instance.id:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists() and self.cleaned_data.get('preceptor').id in qs.values_list('preceptor__id', flat=True):
            raise forms.ValidationError('Preceptor(a) já cadastrado(a) neste diário.')
        return self.cleaned_data.get('preceptor')


class AdicionarResidentesDiarioForm(forms.Form):
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

class DocumentoFrequenciaMensalResidenteForm(forms.ModelForm):
    class Meta:
        model = DocumentoFrequenciaMensalResidente
        fields = ('documento_fisico', 'mes_referencia', 'ano_referencia' )
    
    def __init__(self, residente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.residente = residente

    def clean_documento_fisico(self):
        documento_fisico = self.cleaned_data['documento_fisico']
        filename = f'{normalizar_nome_proprio(self.instance.residente.get_nome_social_composto())}  - Upload em {datetime.datetime.now()})'

        documento_fisico.name = filename

        return documento_fisico

class FrequenciaResidenteForm(forms.ModelForm):
    class Meta:
        model = FrequenciaResidente
        fields = ('data_hora_entrada', 'data_hora_saida')

    def __init__(self, residente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.residente = residente
        self.fields['data_hora_entrada'] = forms.DateTimeFieldPlus()
        self.fields['data_hora_saida'] = forms.DateTimeFieldPlus()
    
    def save(self, *args, **kwargs):
        self.instance.residente = self.residente
        matricula_periodo = MatriculaPeriodo.objects.filter(residente_id = self.residente.id).last()
        matricula_diario = MatriculaDiario.objects.filter(matricula_periodo_id = matricula_periodo.id ,diario__componente_curricular__tipo=ComponenteCurricular.PRATICA).last()
        self.instance.diario = matricula_diario
        self.instance.save()


class SolicitacaoUsuarioForm(forms.ModelFormPlus):
    id = forms.CharField(label='Id', widget=forms.TextInput(attrs=dict(readonly='readonly')))

    class Meta:
        model = SolicitacaoUsuario
        fields = ('id',)

class SolicitacaoDesligamentosForm(forms.ModelFormPlus):
    def __init__(self, residente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.residente = residente
        self.fields['data'] = forms.DateFieldPlus()


    class Meta:
        model = SolicitacaoDesligamentos
        fields = ('motivo', 'data')

class SolicitacaoDiplomasForm(forms.ModelFormPlus):
    def __init__(self, residente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.residente = residente


    class Meta:
        model = SolicitacaoDiplomas
        fields = ('observacao',)

class SolicitacaoFeriasForm(forms.ModelFormPlus):
    def __init__(self, residente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.residente = residente
        self.fields['email'].initial = self.instance.residente.pessoa_fisica.email


    class Meta:
        model = SolicitacaoFerias
        fields = ('data_inicio', 'data_fim', 'email', 'observacao',)

class SolicitacaoLicencasForm(forms.ModelFormPlus):
    tipo = forms.ChoiceField(label='Tipo de licença', choices=SolicitacaoLicencas.TIPO_LICENCA_CHOICES, required=True)
    def __init__(self, residente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.residente = residente
        self.fields['email'].initial = self.instance.residente.pessoa_fisica.email
    class Meta:
        model = SolicitacaoLicencas
        fields = ('tipo','data_inicio', 'data_fim', 'email', 'observacao',)

class SolicitacaoCongressosForm(forms.ModelFormPlus):
    def __init__(self, residente, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.residente = residente
        self.fields['email'].initial = self.instance.residente.pessoa_fisica.email
    class Meta:
        model = SolicitacaoCongressos
        fields = ('descricao_evento','condicao_participacao','modalidade','data_inicio', 'data_fim', 'hora_inicio','email', 'turma', 'estagio')

class RejeitarSolicitacaoUsuarioForm(forms.FormPlus):
    SUBMIT_LABEL = 'Rejeitar Solicitação do Usuário'
    razao_indeferimento = forms.CharField(widget=forms.Textarea(), required=True, label='Razão do Indeferimento')
    fieldsets = (('', {'fields': ('razao_indeferimento',)}),)

class AnalisarSolicitacaoEletivoForm(forms.ModelForm):
    SUBMIT_LABEL = 'Salvar Análise'

    situacao = forms.ChoiceField(
        required=True, choices=SolicitacaoEletivo.SITUACAO_CHOICES,
        widget=forms.RadioSelect(), label='Situação da Solicitação'
    )
    parecer = forms.CharField(widget=forms.Textarea(), label='Parecer da Solicitação', required=True)

    class Meta:
        model = SolicitacaoEletivo
        fields = ('situacao', 'parecer')


class SolicitarEletivoForm(forms.ModelForm):

    fieldsets = (
        ('Dados Pessoais', {'fields': ('numero_seguro',)}),
        ('Serviço de Interesse ao Estágio Eletivo', {'fields': ('nome_servico', 'cidade_servico', 'data_inicio', 'data_fim', 'local_estagio', 'justificativa_estagio')}),
    )

    class Meta:
        model = SolicitacaoEletivo
        fields = ('numero_seguro', 'nome_servico', 'cidade_servico', 'data_inicio', 'data_fim', 'local_estagio', 'justificativa_estagio')


class EstagioEletivoAnexoForm(forms.ModelForm):
    class Meta:
        model = EstagioEletivoAnexo
        fields = ['descricao', 'anexo']


class RelatorioCorpoPedagogicoForm(forms.FormPlus):
    SUBMIT_LABEL = 'Visualizar'
    METHOD = 'GET'

    matriz = forms.ModelChoiceFieldPlus(
        Matriz.objects, label='Curso', required=False
    )

    turma = forms.ModelChoiceFieldPlus(
        Turma.objects,
        required=False
    )

    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), label='Ano Letivo', required=False)
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False, initial=1)
    # situacao = forms.ModelMultiplePopupChoiceField(SituacaoMatricula.objects,
    #                                                        label="Situação no Período", required=False)

    fieldsets = (
        ('Período', {'fields': (('ano_letivo', 'periodo_letivo'),)}),
        ('Filtros de Pesquisa', {
            'fields': (
                'matriz', 'turma',
            )
        }),
    )

    def __init__(self, campus, *args, **kwargs):
        super(RelatorioCorpoPedagogicoForm, self).__init__(*args, **kwargs)
        qs_ano = Ano.objects.filter(ano=datetime.datetime.now().year)
        if qs_ano.exists():
            self.fields['ano_letivo'].initial = qs_ano[0].pk

    def clean(self):
        # if not self.cleaned_data.get('turma') and not self.cleaned_data.get('diario') and not self.cleaned_data.get(
        #         'matriz'):
        #     raise forms.ValidationError('Insira ao menos curso, turma ou diário nos filtros.')
        # filtro_periodo = (self.cleaned_data.get('matriz')) and not (
        #         self.cleaned_data.get('ano_letivo') and self.cleaned_data.get('periodo_letivo'))
        # if filtro_periodo:
        #     raise forms.ValidationError('Insira ano letivo e período letivo para filtrar por campus ou curso.')

        return self.cleaned_data

class EstatisticaForm(forms.FormPlus):

    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    FILTRO_CHOICES = [['por_ano_letivo', 'Ano Letivo'],]

    MAPA_SITUACAO = dict(
        SITUACAO_MATRICULADO=[
            SituacaoMatriculaPeriodo.MATRICULADO,
            SituacaoMatriculaPeriodo.EM_ABERTO,

        ],
        SITUACAO_CANCELADO=[
            SituacaoMatriculaPeriodo.DESLIGADO,
        ],
        SITUACAO_RETIDO=[SituacaoMatriculaPeriodo.REPROVADO, SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA],
        SITUACAO_TRANCADO=[
            SituacaoMatriculaPeriodo.TRANCADA,
        ],
      )

    SITUACOES_CHOICES = [
        ['SITUACAO_MATRICULADO', 'Matriculado'],
        ['SITUACAO_CANCELADO', 'Desligado'],
    ]

    periodicidade = forms.ChoiceField(label='Periodicidade', choices=FILTRO_CHOICES, required=True,
                                      initial='por_ano_letivo')
    situacao_matricula_periodo = forms.ChoiceField(choices=SITUACOES_CHOICES, label='Situação')

    apartir_do_ano = forms.ModelChoiceField(Ano.objects.ultimos(), label='A Partir de', required=True)
    ate_ano = forms.ModelChoiceField(Ano.objects.ultimos(), label='Até', required=False)

    cursos_campus = forms.MultipleModelChoiceField(
        CursoResidencia.objects,
        label='Curso', required=False,
    )
    matrizes = forms.MultipleModelChoiceField(
        Matriz.objects,
        label='Matriz', required=False,
    )


    ira_apartir_de = forms.IntegerField(label='A Partir de', max_value=100, min_value=0, required=False)
    ira_ate = forms.IntegerField(label='Até', max_value=100, min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fieldsets = (
            ('Filtros', {'fields': (('situacao_matricula_periodo','periodicidade'),
                                           ('apartir_do_ano', 'ate_ano'),
                                           ('cursos_campus',),
                                           ( 'matrizes',),
                                           )}),

        )

    def processar(self):
        qs = (
            MatriculaPeriodo.objects.filter(residente__ano_letivo__ano__lte=datetime.date.today().year)
        )



        # filtro por situacao da matricula no periodo
        situacao = self.cleaned_data.get('situacao_matricula_periodo')
        situacoes = EstatisticaForm.MAPA_SITUACAO[situacao]

        if situacoes:
            qs = qs.filter(situacao__id__in=situacoes)

        cursos = self.cleaned_data.get('cursos_campus')
        ira_apartir_de = self.cleaned_data.get('ira_apartir_de')
        ira_ate = self.cleaned_data.get('ira_ate')

        if cursos:
            qs = qs.filter(residente__curso_campus__in=cursos)

        matrizes = self.cleaned_data.get('matrizes')

        if matrizes:
            qs = qs.filter(residente__matriz__in=matrizes)

        if ira_apartir_de or ira_ate:
            ira_apartir_de = ira_apartir_de or 0
            ira_ate = ira_ate or 100
            qs = qs.filter(residente__ira__gte=ira_apartir_de, residente__ira__lte=ira_ate)

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
                periodos.append(f'{datetime.date.today().year}.{1}')

        periodo_selecionado = periodos[0]
        if self.request and self.request.GET.get('periodo_selecionado'):
            ano_periodo_split = self.request.GET.get('periodo_selecionado').split('.')
            periodo_selecionado = f'{ano_periodo_split[0]}.{ano_periodo_split[1]}'

        # montando o gráfico de evolução anual

        series_ano = []
        qtd_residentes_ano = 0
        qtd_residentes_ano_selecionado = 0
        qs_residentes_ano_selecionado = None
        tabela_resumo = []

        if situacao == 'SITUACAO_CONCLUIDOS':
            situacoes = [SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO, SituacaoMatricula.EGRESSO]
            qs = qs.filter(residente__situacao__id__in=situacoes)
            residente_ids = qs.values_list('residente__pk', flat=True).distinct()
            residentes_concluidos = Residente.objects.filter(pk__in=residente_ids)
            for ano in anos:
                residentes_concluidos_ano = residentes_concluidos.filter(ano_conclusao=ano.ano)
                qtd_residentes = residentes_concluidos_ano.order_by('id').values_list('id', flat=True).distinct().count()
                series_ano.append([ano.ano, qtd_residentes])
                tabela_resumo.append([ano.ano, qtd_residentes])
                if ano_selecionado == ano:
                    qtd_residentes_ano_selecionado = qtd_residentes
                    qs_residentes_ano_selecionado = residentes_concluidos_ano
            if qs_residentes_ano_selecionado:
                residentes_concluidos = qs_residentes_ano_selecionado
            qs = MatriculaPeriodo.objects.filter(
                pk__in=[residente.get_ultima_matricula_periodo().pk for residente in residentes_concluidos.filter(dt_conclusao_curso__year__gte=ano_selecionado.ano)]
            )
            qs = qs.order_by('residente__id').annotate(qtd_residente=Count('residente', distinct=True))
        elif situacao == 'SITUACAO_INGRESSANTES':
            qs = qs.filter(residente__ano_letivo__in=anos)


            for item in qs.values('residente__ano_letivo__ano').order_by('residente__ano_letivo__ano').annotate(qtd_residente=Count('residente', distinct=True)):
                ano = int(item['residente__ano_letivo__ano'])
                qtd_residentes = item['qtd_residente'] or 0
                qtd_residentes_ano = qtd_residentes
                series_ano.append([ano, qtd_residentes_ano])
                tabela_resumo.append([ano, qtd_residentes])
                if ano_selecionado.ano == ano:
                    qtd_residentes_ano_selecionado = qtd_residentes

            qs = qs.filter(residente__ano_letivo=ano_selecionado).order_by('residente__id').distinct()



        else:
            qs = qs.filter(ano_letivo__in=anos)


            for item in qs.values('ano_letivo__ano').order_by('ano_letivo__ano').annotate(qtd_residente=Count('residente', distinct=True)):
                ano = int(item['ano_letivo__ano'])
                qtd_residentes = item['qtd_residente'] or 0
                qtd_residentes_ano = qtd_residentes
                series_ano.append([ano, qtd_residentes_ano])
                tabela_resumo.append([ano, qtd_residentes])
                if ano_selecionado.ano == ano:
                    qtd_residentes_ano_selecionado = qtd_residentes

            qs = qs.filter(ano_letivo=ano_selecionado).order_by('residente__id').distinct()


        id_grafico_evolucao_anual = 'id_grafico_evolucao_anual'
        grafico_evolucao_anual = LineChart(id_grafico_evolucao_anual, title='Total de Residentes por Ano', data=series_ano, groups=['Residentes'])
        grafico_evolucao_anual.id = id_grafico_evolucao_anual
        grafico_evolucao_anual.tabela_resumo = tabela_resumo
        grafico_evolucao_anual.qtd_residentes_ano_selecionado = qtd_residentes_ano_selecionado

        residentes = Residente.objects.filter(id__in=qs.order_by('residente__id').values_list('residente__id', flat=True).distinct()).select_related('pessoa_fisica__pessoa_ptr'
        )

        return anos, periodos, ano_selecionado, periodo_selecionado, grafico_evolucao_anual, residentes


class EstatisticaEletivoForm(forms.FormPlus):

    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'
    FILTRO_CHOICES = [['por_ano_letivo', 'Ano Letivo'],]

    MAPA_SITUACAO = dict(
        SITUACAO_MATRICULADO=[
            SituacaoMatriculaPeriodo.MATRICULADO,
            SituacaoMatriculaPeriodo.EM_ABERTO,

        ],
        SITUACAO_CANCELADO=[
            SituacaoMatriculaPeriodo.DESLIGADO,
        ],
        SITUACAO_RETIDO=[SituacaoMatriculaPeriodo.REPROVADO, SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA],
        SITUACAO_TRANCADO=[
            SituacaoMatriculaPeriodo.TRANCADA,
        ],
      )

    SITUACOES_CHOICES = [
        ['SITUACAO_MATRICULADO', 'Matriculado'],
        ['SITUACAO_CANCELADO', 'Desligado'],
    ]

    periodicidade = forms.ChoiceField(label='Periodicidade', choices=FILTRO_CHOICES, required=True,
                                      initial='por_ano_letivo')
    situacao_matricula_periodo = forms.ChoiceField(choices=SITUACOES_CHOICES, label='Situação')

    apartir_do_ano = forms.ModelChoiceField(Ano.objects.ultimos(), label='A Partir de', required=True)
    ate_ano = forms.ModelChoiceField(Ano.objects.ultimos(), label='Até', required=False)

    cursos_campus = forms.MultipleModelChoiceField(
        CursoResidencia.objects,
        label='Curso', required=False,
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fieldsets = (
            ('Filtros', {'fields': (('situacao_matricula_periodo','periodicidade'),
                                           ('apartir_do_ano', 'ate_ano'),
                                           ('cursos_campus'),
                                           )}),

        )

    def processar(self):
        qs = (
            EstagioEletivo.objects.all()
        )
        # residente_eletivo_ids = qs.values_list('residente__pk', flat=True).distinct()
        # qs = (
        #     MatriculaPeriodo.objects.filter(residente__pk__in=residente_eletivo_ids)
        # )

        # filtro por situacao da matricula no periodo
        situacao = self.cleaned_data.get('situacao_matricula_periodo')

        cursos = self.cleaned_data.get('cursos_campus')

        if cursos:
            qs = qs.filter(residente__curso_campus__in=cursos)

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
                periodos.append(f'{datetime.date.today().year}.{1}')

        periodo_selecionado = periodos[0]
        if self.request and self.request.GET.get('periodo_selecionado'):
            ano_periodo_split = self.request.GET.get('periodo_selecionado').split('.')
            periodo_selecionado = f'{ano_periodo_split[0]}.{ano_periodo_split[1]}'

        # montando o gráfico de evolução anual

        series_ano = []
        qtd_residentes_ano = 0
        qtd_residentes_ano_selecionado = 0
        qs_residentes_ano_selecionado = None
        tabela_resumo = []

        if situacao == 'SITUACAO_CONCLUIDOS':
            situacoes = [SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO, SituacaoMatricula.EGRESSO]
            qs = qs.filter(residente__situacao__id__in=situacoes)

        for ano in anos:
            data_inicio = datetime.datetime(ano.ano, 1, 1).date()
            data_fim = datetime.datetime(ano.ano + 1, 1, 1).date()
            qs2 = qs.filter(Q(data_fim__gt=data_inicio, data_inicio__lt=data_fim) | Q(data_fim__isnull=True, data_inicio__lt=data_fim))

            residente_ids = qs2.values_list('residente__pk', flat=True).distinct()
            residentes = Residente.objects.filter(pk__in=residente_ids)
            qtd_residentes = residentes.order_by('id').values_list('id', flat=True).distinct().count()
            series_ano.append([ano.ano, qtd_residentes])
            tabela_resumo.append([ano.ano, qtd_residentes])
            if ano_selecionado == ano:
                qtd_residentes_ano_selecionado = qtd_residentes

        data_inicio = datetime.datetime(ano_selecionado.ano, 1, 1).date()
        data_fim = datetime.datetime(ano_selecionado.ano + 1, 1, 1).date()
        qs = qs.filter(Q(data_fim__gt=data_inicio, data_inicio__lt=data_fim) | Q(data_fim__isnull=True, data_inicio__lt=data_fim))


        id_grafico_evolucao_anual = 'id_grafico_evolucao_anual'
        grafico_evolucao_anual = LineChart(id_grafico_evolucao_anual, title='Total de Residentes em Estágios Eletivos por Ano', data=series_ano, groups=['Residentes'])
        grafico_evolucao_anual.id = id_grafico_evolucao_anual
        grafico_evolucao_anual.tabela_resumo = tabela_resumo
        grafico_evolucao_anual.qtd_residentes_ano_selecionado = qtd_residentes_ano_selecionado

        residentes = Residente.objects.filter(id__in=qs.order_by('residente__id').values_list('residente__id', flat=True).distinct()).select_related('pessoa_fisica__pessoa_ptr'
        )

        return anos, periodos, ano_selecionado, periodo_selecionado, grafico_evolucao_anual, residentes


class MatricularAlunoAvulsoUnidadeAprendizagemTurmaForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Inserir Residente'
    residente = forms.ModelChoiceFieldPlus(Residente.objects, label='Residente', widget=AutocompleteWidget(search_fields=Residente.SEARCH_FIELDS), required=True)

    def __init__(self, unidadeaprendizagemturma, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unidadeaprendizagemturma = unidadeaprendizagemturma
        self.fields['residente'].queryset = (
            Residente.objects.filter(
                situacao__pk__in=[
                    SituacaoMatricula.MATRICULADO,
                    SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
                    SituacaoMatricula.TRANCADO,
                    SituacaoMatricula.INTERCAMBIO,
                    SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL,
                ],
                matriz__isnull=False,
            ).distinct()
        )

    def clean(self):
        # aluno = self.cleaned_data.get('aluno')
        # if not aluno:
        #     return self.cleaned_data
        # ignorar_quebra_requisito = in_group(self.request.user, 'Administrador Acadêmico')
        # pode_ser_matriculado, msg = aluno.pode_ser_matriculado_no_diario(self.diario, ignorar_quebra_requisito)
        # if not pode_ser_matriculado:
        #     raise forms.ValidationError(msg)
        # matricula_periodo = self.cleaned_data['aluno'].get_ultima_matricula_periodo()
        # if not in_group(self.request.user, 'Administrador Acadêmico') and (
        #     matricula_periodo.ano_letivo != self.diario.ano_letivo or matricula_periodo.periodo_letivo != self.diario.periodo_letivo
        # ):
        #     raise forms.ValidationError('Alunos com última matrícula período diferente do período letivo do diário não podem ser inseridos.')
        #
        # if self.diario.componente_curricular.componente.pk in aluno.get_ids_componentes_cumpridos():
        #     raise forms.ValidationError('O aluno já cursou o componente deste diário.')

        return self.cleaned_data

    def processar(self):
        matricula_periodo = self.cleaned_data['residente'].matriculas_periodos_residente_residencia_set.get(ano_letivo=self.unidadeaprendizagemturma.ano_letivo, periodo_letivo=self.unidadeaprendizagemturma.periodo_letivo)
        if not MatriculaUnidadeAprendizagemTurma.objects.filter(matricula_periodo=matricula_periodo, unidade_aprendizagem_turma=self.unidadeaprendizagemturma).exists():
            matricula_unidade_aprendizagem_turma = MatriculaUnidadeAprendizagemTurma()
            matricula_unidade_aprendizagem_turma.unidade_aprendizagem_turma = self.unidadeaprendizagemturma
            matricula_unidade_aprendizagem_turma.matricula_periodo = matricula_periodo
            matricula_unidade_aprendizagem_turma.situacao = MatriculaDiario.SITUACAO_CURSANDO
            matricula_unidade_aprendizagem_turma.save()
            if not matricula_periodo.residente.situacao.pk == SituacaoMatricula.MATRICULADO:
                matricula_periodo.residente.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                matricula_periodo.residente.save()
            if not matricula_periodo.situacao == SituacaoMatriculaPeriodo.MATRICULADO:
                matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
                matricula_periodo.save()

class UnidadeAprendizagemTurmaForm(forms.ModelFormPlus):
    class Meta:
        model = UnidadeAprendizagemTurma
        exclude = (
            #'turma',
            #'componente_curricular',
            #'ano_letivo',
            #'periodo_letivo',
            #'situacao',
            #'estrutura_curso',
            #'calendario_academico',
            #'local_aula',
            #'locais_aula_secundarios',
            'posse_etapa_1',
            'posse_etapa_2',
            'posse_etapa_3',
            'posse_etapa_4',
            'posse_etapa_5',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ConfiguracaoAvaliacaoUnidadeAprendizagemForm(forms.ModelFormPlus):

    class Media:
        js = ('/static/edu/js/ConfiguracaoAvaliacaoUnidadeAprendizagemForm.js',)

    class Meta:
        model = ConfiguracaoAvaliacaoUnidadeAprendizagem
        exclude = ('professor',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.NOTA_DECIMAL:
            self.fields['observacao'].widget.attrs['class'] = 'notas-decimais'
        forma_atitudinal = [ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_MEDIA_ATITUDINAL, 'Média Atitudinal']
        choices = ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_CHOICES.copy()
        if forma_atitudinal in choices:
            choices.remove(forma_atitudinal)
        self.fields['forma_calculo'].choices = choices

    def clean_divisor(self):
        if self.cleaned_data['forma_calculo'] == ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_SOMA_DIVISOR:
            if not self.cleaned_data.get('divisor') or self.cleaned_data['divisor'] < 1:
                raise forms.ValidationError('Insira o valor do divisor, maior que 0, a ser utilizado no cálculo.')
        return self.cleaned_data['divisor']

    def clean(self):
        if self.instance.pk == 1 and not in_group(self.request.user, 'Administrador Acadêmico'):
            raise forms.ValidationError('Não é possível alterar a configuração padrão do sistema. Caso necessite, adicione um nova configuração de avaliação para você.')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)


class ItemConfiguracaoAvaliacaoUnidadeAprendizagemFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        eh_nota_atitudinal = False

        ids_delete = []
        tem_avaliacao_atitudinal = False
        if hasattr(self, 'cleaned_data'):
            for item in self.cleaned_data:
                if 'DELETE' in item and item['DELETE']:
                    if 'id' in item:
                        ids_delete.append(item['id'].id)
                if eh_nota_atitudinal and 'tipo' in item and item['tipo'] and item['tipo'] == ItemConfiguracaoAvaliacaoUnidadeAprendizagem.TIPO_ATITUDINAL:
                    if not tem_avaliacao_atitudinal:
                        tem_avaliacao_atitudinal = True
                    else:
                        raise ValidationError('Não pode existir mais de uma avaliação do tipo atitudinal.')

            if eh_nota_atitudinal:
                if not tem_avaliacao_atitudinal:
                    raise ValidationError('É obrigatório o cadastro de uma avaliação do tipo Atitudinal.')
                if ids_delete and ItemConfiguracaoAvaliacaoUnidadeAprendizagem.objects.filter(id__in=ids_delete, tipo=ItemConfiguracaoAvaliacaoUnidadeAprendizagem.TIPO_ATITUDINAL).exists():
                    raise ValidationError('Não é possível excluir o item de avaliação Atitudinal.')

            if ids_delete and NotaAvaliacaoUnidadeAprendizagem.objects.filter(item_configuracao_avaliacao__id__in=ids_delete).exclude(nota__isnull=True).exists():
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

                if configuracao_avaliacao.forma_calculo == ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_MEDIA_PONDERADA and form.cleaned_data.get('peso') is None:
                    raise ValidationError('Informe o peso dos itens de configuração de avaliação.')

                if not form.cleaned_data.get('DELETE'):
                    soma_nota += form.cleaned_data.get('nota_maxima') or 0
                    soma_peso += form.cleaned_data.get('peso') or 0
                    siglas.append(form.cleaned_data.get('sigla'))
                    qtd_itens += 1

                if NotaAvaliacaoUnidadeAprendizagem.objects.filter(
                    matricula_unidade_aprendizagem_turma__unidade_aprendizagem_turma=configuracao_avaliacao.unidadeaprendizagemturma, item_configuracao_avaliacao=form.instance, nota__gt=(form.instance.nota_maxima * MULTIPLICADOR_DECIMAL)
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

            if forma_calculo == ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_SOMA_SIMPLES:
                if soma_nota != nota_maxima:
                    raise forms.ValidationError(f'O somatório das notas das avaliações deve ser {nota_maxima}, mas o resultado da soma foi {soma_nota}.')

            if (
                forma_calculo == ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_MAIOR_NOTA
                or forma_calculo == ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_MEDIA_PONDERADA
                or forma_calculo == ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_MEDIA_ARITMETICA
            ):
                if soma_nota / qtd_itens != nota_maxima:
                    raise forms.ValidationError(f'As notas máximas para esta forma de cálculo devem ser {nota_maxima}.')

            if forma_calculo == ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_SOMA_DIVISOR:
                if not divisor:
                    return
                if soma_nota / divisor != nota_maxima:
                    raise forms.ValidationError(f'A soma das notas máximas das avaliações deve ser {divisor * nota_maxima}.')

            if eh_nota_atitudinal and forma_calculo != ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_MEDIA_ATITUDINAL:
                raise forms.ValidationError('Somente a forma de cálculo Atitudinal é permitida para esta configuração.')

        else:
            raise forms.ValidationError('Informe ao menos um item de configuração da avaliação.')