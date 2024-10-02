import datetime
from operator import itemgetter

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction

from comum.models import (
    Ano, Configuracao, ConselhoProfissional, EmailBlockList, Municipio, NivelEnsino, OrgaoEmissorRg, Pais,
    PrestadorServico, Raca, UnidadeFederativa, UsuarioGrupo, User, Bolsista
)
from comum.utils import somar_data
from djtools import forms
from djtools.forms import ModelChoiceFieldPlus
from djtools.forms.widgets import (
    AutocompleteWidget,
    PhotoCapturePortraitInput, RenderableSelectMultiple, TextareaCloneWidget, CheckboxSelectMultiplePlus, TreeWidget
)
from djtools.forms.wizard import FormWizardPlus
from djtools.templatetags.filters import in_group, format_
from djtools.utils import eh_nome_completo, mask_numbers
from djtools.utils import normalizar_nome_proprio
from ldap_backend.models import LdapConf
from ppe.models import (
    ChefiaPPE, CursoFormacaoPPE, Observacao, SequencialMatriculaTrabalhadorEducando, TrabalhadorEducando,
    FormacaoPPE, EstruturaCurso, Curso, Turma, TutorTurma, ApoiadorTurma, CursoTurma, Anamnese,
    MeioTransporte, ResideCom, MembrosCarteiraAssinada,
    ResidenciaSaneamentoBasico, ItensResidencia, ParticipacaoGruposSociais, CursosTrabalhadorEducando,
    RedeSocial, SituacaoMatricula, MatriculaCursoTurma, ConfiguracaoAvaliacao, NotaAvaliacao, SolicitacaoUsuario,
    SolicitacaoAtendimentoPsicossocial, SolicitacaoContinuidadeAperfeicoamentoProfissional,
    SolicitacaoAmpliacaoPrazoCurso, SolicitacaoRealocacao, SolicitacaoVisitaTecnicaUnidade, HistoricoRelatorioPpe, Aula,
    SolicitacaoDesligamentos, PerguntaAvaliacao, RespostaAvaliacao, OpcaoRespostaAvaliacao, TipoAvaliacao, Avaliacao,
    EtapaMonitoramento, FormacaoTecnica, Setor, Unidade, TrabalhadorSetorHistorico, ChefiaSetorHistorico
)
from rh.enums import Nacionalidade
from rh.forms import get_choices_nome_usual, EmpregadoFesfForm
from rh.models import Pessoa, PessoaFisica, Servidor, Situacao
from rh.models import Setor as SetorRH


class CoordenadorPpeForm(EmpregadoFesfForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        empregado = super().save(*args, **kwargs)
        return empregado


class SupervisorCampoPpeForm(forms.ModelFormPlus):
    nome_registro = forms.CharFieldPlus(width=300, label='Nome')
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    matricula = forms.CharFieldPlus(width=300, label="Matrícula")
    cpf = forms.BrCpfField(required=True)
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

    logradouro = forms.CharFieldPlus(max_length=255, required=False, label='Logradouro (Avenida, Rua, etc)', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=False, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=False, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='CEP')
    municipio = forms.ModelChoiceFieldPlus(Municipio.objects.all().order_by('pk'), required=False, label='Cidade',
                                           help_text='Preencha o nome da cidade sem acento.')

    setor = forms.ModelChoiceField(label='Lotação', queryset=SetorRH.objects.all(), widget=forms.HiddenInput(),required=False)
    email = forms.EmailField(max_length=255, label='E-mail')
    telefone = forms.BrTelefoneField(max_length=255, required=False, label='Telefone',
                                     help_text='Formato: "(XX) XXXXX-XXXX"')
    telefone_celular = forms.BrTelefoneField(max_length=45, label="Telefone Celular", required=False)

    titulo_data_emissao = forms.DateFieldPlus(label='Data da Emissão', required=False)
    # conselho classe
    numero_registro = forms.CharField(max_length=255, required=False, label='Número de Registro Conselho Profissional')
    situacao = forms.ModelChoiceField(label="Situação", queryset=Situacao.objects.all(), widget=forms.HiddenInput(), required=False)
    data_inicio_exercicio_na_instituicao = forms.DateFieldPlus(label='Data de admissão', required=False)

    formacao_complementar_1 = forms.CharFieldPlus(max_length=255, label='Formação Complementar ou Experiência Profissional 1', required=False)
    formacao_complementar_2 = forms.CharFieldPlus(max_length=255, label='Formação Complementar ou Experiência Profissional 2', required=False)
    formacao_complementar_3 = forms.CharFieldPlus(max_length=255, label='Formação Complementar ou Experiência Profissional 3', required=False)

    fieldsets = (
        ('Dados Pessoais', {'fields': (
        'nome_registro', 'cpf', 'matricula', 'passaporte', 'nacionalidade', 'sexo', 'nascimento_data', 'nome_pai',
        'nome_mae', 'naturalidade')}),
        ('RG', {'fields': ('rg', 'rg_orgao', 'rg_data', 'rg_uf')}),
        ('Endereço', {'fields': ('cep', 'municipio', 'logradouro', 'numero', 'complemento', 'bairro')}),
        ('Dados para Contato', {'fields': ('email', 'telefone')}),
        ('Dados funcionais', {'fields': ('data_inicio_exercicio_na_instituicao','formacao_complementar_1','formacao_complementar_2','formacao_complementar_3')}),
    )


    class Meta:
        model = Servidor
        fields = ('nome_registro', 'cpf', 'matricula', 'passaporte', 'nacionalidade', 'sexo', 'nascimento_data', 'nome_pai','setor',
                  'nome_mae', 'naturalidade','rg', 'rg_orgao', 'rg_data', 'rg_uf', 'cep', 'municipio', 'logradouro', 'numero', 'complemento', 'bairro',
                  'email', 'telefone','situacao','data_inicio_exercicio_na_instituicao','formacao_complementar_1','formacao_complementar_2','formacao_complementar_3')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['nome_registro'].initial = self.instance.get_vinculo().pessoa.nome
            self.fields['cpf'].initial = self.instance.get_vinculo().pessoa.pessoafisica.cpf
            self.fields['passaporte'].initial = self.instance.get_vinculo().pessoa.pessoafisica.cpf
            self.fields['nacionalidade'].initial = self.instance.get_vinculo().pessoa.pessoafisica.nacionalidade
            self.fields['sexo'].initial = self.instance.get_vinculo().pessoa.pessoafisica.sexo
            self.fields['email'].initial = self.instance.get_vinculo().pessoa.pessoafisica.email
            if self.instance.get_vinculo().pessoa.pessoatelefone_set.all().exists():
                self.fields['telefone'].initial = self.instance.get_vinculo().pessoa.pessoatelefone_set.all()[0].numero
            self.fields['rg'].initial = self.instance.get_vinculo().pessoa.pessoafisica.rg
            self.fields['rg_orgao'].initial = self.instance.get_vinculo().pessoa.pessoafisica.rg_orgao
            self.fields['rg_data'].initial = self.instance.get_vinculo().pessoa.pessoafisica.rg_data
            self.fields['rg_uf'].initial = self.instance.get_vinculo().pessoa.pessoafisica.rg_uf
            self.fields['nascimento_data'].initial = self.instance.get_vinculo().pessoa.pessoafisica.nascimento_data
            self.fields['naturalidade'].initial = self.instance.get_vinculo().pessoa.pessoafisica.nascimento_municipio
            self.fields['nome_pai'].initial = self.instance.get_vinculo().pessoa.pessoafisica.nome_pai
            self.fields['nome_mae'].initial = self.instance.get_vinculo().pessoa.pessoafisica.nome_mae
            self.fields['municipio'].initial = self.instance.get_vinculo().pessoa.endereco_municipio
            self.fields['logradouro'].initial = self.instance.get_vinculo().pessoa.endereco_logradouro
            self.fields['numero'].initial = self.instance.get_vinculo().pessoa.endereco_numero
            self.fields['bairro'].initial = self.instance.get_vinculo().pessoa.endereco_bairro
            self.fields['complemento'].initial = self.instance.get_vinculo().pessoa.endereco_complemento
            self.fields['cep'].initial = self.instance.get_vinculo().pessoa.endereco_cep

    def clean(self):
        cpf = self.cleaned_data.get('cpf')
        nacionalidade = self.data.get('nacionalidade')
        eh_estrangeiro = int(nacionalidade) == Nacionalidade.ESTRANGEIRO if nacionalidade else False
        empregado_ja_cadastrado = False
        if not cpf and not eh_estrangeiro:
            self.add_error('cpf', "O campo CPF é obrigatório para nacionalidades Brasileira")

        cpf_formatado = cpf.replace(".", "").replace("-", "")
        if not self.instance.pk and User.objects.filter(username=cpf_formatado).exists():
            self.add_error('matricula', f"O usuário {cpf_formatado} já existe.")
        return self.cleaned_data

    def save(self, *args, **kwargs):
        self.instance.situacao = Situacao.objects.get(codigo='01')  ##ATIVO
        empregado = super().save(*args, **kwargs)
        return empregado


class ChefiaPPEForm(forms.ModelFormPlus):
    cpf = forms.BrCpfField(label='CPF')
    nome = forms.CharFieldPlus(label='Nome Completo')
    funcao = forms.CharFieldPlus(label='Função')
    formacao = forms.CharFieldPlus(label='Formação')
    email = forms.EmailField(label='Email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = ChefiaPPE
        fields = ('cpf', 'nome', 'funcao', 'funcao', 'formacao', 'email')

# class ChefiaPPEForm(forms.FormPlus):
#     cpf = forms.BrCpfField(label='CPF')
#     nome = forms.CharFieldPlus(label='Nome Completo')
#     funcao = forms.CharFieldPlus(label='Função')
#     formacao = forms.CharFieldPlus(label='Formação')
#     email = forms.EmailField(label='Email')
#     confirma_email = forms.EmailField(label='Confirmação de E-mail')
#
#     def clean_confirma_email(self):
#         email = self.cleaned_data.get('email').strip()
#         confirma_email = self.cleaned_data.get('confirma_email').strip()
#         if email != confirma_email:
#             raise forms.ValidationError("E-mails informados não são iguais!")
#         if ChefiaPPE.objects.filter(email=email).exists():
#             raise forms.ValidationError("Existe um Usuário cadastrado com este e-mail!")
#         return self.cleaned_data['confirma_email']
#
#     def clean(self):
#         cpf = self.cleaned_data.get('cpf')
#         if User.objects.filter(username=mask_numbers(cpf), is_active=False).exists():
#             self.add_error('cpf', f"Existe um Usuário ativo cadastrado com o CPF {cpf}.")


#FES-33
class GestorPpeForm(EmpregadoFesfForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        empregado = super().save(*args, **kwargs)
        gestor_ppe = Group.objects.get(name='Gestor(a) PPE')
        if gestor_ppe:
            gestor_ppe.user_set.add(empregado.get_vinculo().user)

        return empregado


class ApoiadorAdministrativoPpeForm(EmpregadoFesfForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        empregado = super().save(*args, **kwargs)
        apoio_administrativo_ppe = Group.objects.get(name='Apoiador(a) Administrativo PPE')
        if apoio_administrativo_ppe:
            apoio_administrativo_ppe.user_set.add(empregado.get_vinculo().user)

        return empregado


class SupervisorPedagogicoPpeForm(EmpregadoFesfForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        empregado = super().save(*args, **kwargs)
        supervisor_pedagogico_ppe = Group.objects.get(name='Supervisor(a) Pedagógico(a)')
        if supervisor_pedagogico_ppe:
            supervisor_pedagogico_ppe.user_set.add(empregado.get_vinculo().user)

        return empregado


class SupervisorPsicossocialPpeForm(EmpregadoFesfForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        empregado = super().save(*args, **kwargs)
        supervisor_psicossocial_ppe = Group.objects.get(name='Supervisor(a) Psicossocial PPE')
        if supervisor_psicossocial_ppe:
            supervisor_psicossocial_ppe.user_set.add(empregado.get_vinculo().user)

        return empregado


# ------TRABALHADOR EDUCANDO
class TrabalhadorEducandoForm(forms.ModelFormPlus):
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

    raca = forms.ModelChoiceField(Raca.objects.all(), required=True, label='Raça')
    tipo_instituicao_origem = forms.ChoiceField(required=True, label='Tipo da Instituição', choices=[['', '----']] + TrabalhadorEducando.TIPO_INSTITUICAO_ORIGEM_CHOICES)

    estado = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado', required=False)

    cidade = forms.ModelChoiceFieldPlus(
        Municipio.objects, label='Cidade', required=True, widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS)
    )

    estado_naturalidade = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado de Origem', required=False)

    naturalidade = forms.ModelChoiceFieldPlus(
        Municipio.objects, label='Naturalidade', required=False, widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS)
    )

    categoria = forms.ChoiceField(choices=TrabalhadorEducando.EMPTY_CHOICES + TrabalhadorEducando.CATEGORIAS_CHOICES, required=False, label='Categoria')
    formacao_tecnica = forms.ModelChoiceField(FormacaoTecnica.objects, required=True, label='Formação técnica')
    data_admissao = forms.DateFieldPlus(required=True, label='Data de Admissão')
    data_demissao = forms.DateFieldPlus(required=False, label='Data de Demissão')
    # conselho classe
    numero_registro = forms.CharField(max_length=255, required=False, label='Número de Registro')
    conselho = forms.ModelChoiceField(ConselhoProfissional.objects, required=False, label='Conselho')

    fieldsets = (
        ('Identificação', {'fields': ('nome', 'nome_social', ('cpf', 'passaporte'), ('data_nascimento', 'estado_civil', 'sexo'))}),
        (
            'Dados Familiares',
            {
                'fields': (
                    'nome_pai',
                    # 'estado_civil_pai',
                    'nome_mae',
                    # 'estado_civil_mae',
                    # 'responsavel',
                    'parentesco_responsavel',
                )
            },
        ),
        ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'estado', 'cidade')}),
        ('Contato', {'fields': (('telefone_principal', 'telefone_secundario'), ('telefone_adicional_1', 'telefone_adicional_2'))}),
        ('Deficiências, Transtornos e Superdotação', {'fields': ('tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao')}),
        ('Outras Informações', {'fields': ('tipo_sanguineo', 'nacionalidade', 'pais_origem', 'estado_naturalidade', 'naturalidade', 'raca')}),
        (
            'Dados Escolares', 
            {
                'fields': (
                    'nivel_ensino_anterior', 
                    'tipo_instituicao_origem', 
                    'nome_instituicao_anterior', 
                    'ano_conclusao_estudo_anterior', 
                    'habilitacao_pedagogica', 
                    'categoria', 
                    'conselho', 
                    'numero_registro'
                )
            }
        ),
        ('Informações Profissionais', {'fields': ('formacao_tecnica','data_admissao', 'data_demissao')}),
        ('RG', {'fields': ('numero_rg', 'uf_emissao_rg', 'orgao_emissao_rg', 'data_emissao_rg')}),
        ('Título de Eleitor', {'fields': ('numero_titulo_eleitor', 'zona_titulo_eleitor', 'secao', 'data_emissao_titulo_eleitor', 'uf_emissao_titulo_eleitor')}),
        (
            'Carteira de Reservista',
            {'fields': ('numero_carteira_reservista', 'regiao_carteira_reservista', 'serie_carteira_reservista', 'estado_emissao_carteira_reservista', 'ano_carteira_reservista')},
        ),
        # ('Certidão Civil', {'fields': ('tipo_certidao', 'cartorio', 'numero_certidao', 'folha_certidao', 'livro_certidao', 'data_emissao_certidao', 'matricula_certidao')}),
        ('Dados do MEC', {'fields': ('codigo_educacenso', 'nis')}),
        # ('Transporte Escolar', {'fields': ('poder_publico_responsavel_transporte', 'tipo_veiculo')}),
    )

    class Meta:
        model = TrabalhadorEducando
        exclude = ()

    class Media:
        js = ('/static/residencia/js/TrabalhadorEducandoForm.js',)

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
            raise forms.ValidationError('Informe o passaporte do(a) Trabalhador(a) Educando(a).')
        return passaporte
    
    def clean_numero_registro(self):
        categoria = self.data.get('categoria')
        numero_registro = self.data.get('numero_registro')
        if categoria == 'Enfermagem' or 'Nutrição' or 'Análises Clínicas' and not numero_registro:
            raise forms.ValidationError('O campo Número de Registro é obrigatório caso a categoria seja Enfermagem, Nutrição ou Análises Clínicas')
        return numero_registro

    def clean_cpf(self):
        nacionalidade = self.data.get('nacionalidade')
        cpf = self.data.get('cpf')
        if nacionalidade != 'Estrangeira' and not cpf:
            raise forms.ValidationError('Informe o CPF do(a) Trabalhador(a) Educando(a).')
        return cpf

    def clean_aluno_pne(self):
        aluno_pne = self.cleaned_data.get('aluno_pne')

        if aluno_pne and not (self.data.get('tipo_necessidade_especial') or self.data.get('tipo_transtorno') or self.data.get('superdotacao')):
            raise forms.ValidationError('Informe a deficiência, transtorno ou superdotação do(a) Trabalhador(a) Educando(a)')
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


class AtualizarEmailTrabalhadorEducandoForm(forms.FormPlus):
    email_secundario = forms.EmailField(max_length=255, required=False, label='E-mail Secundário')
    email_academico = forms.EmailField(max_length=255, required=False, label='E-mail Acadêmico')
    email_google_classroom = forms.EmailField(max_length=255, required=False, label='E-mail Google ClassRoom')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.trabalhadoreducando = kwargs.pop('trabalhadoreducando')

        super().__init__(*args, **kwargs)

        if self.trabalhadoreducando.get_vinculo() is None:
            self.trabalhadoreducando.save()  # força criação de vínculo
        self.fields['email_secundario'].initial = self.trabalhadoreducando.get_vinculo().pessoa.email_secundario
        self.fields['email_academico'].initial = self.trabalhadoreducando.email_academico
        self.fields['email_google_classroom'].initial = self.trabalhadoreducando.email_google_classroom
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
            if TrabalhadorEducando.objects.exclude(pk=self.trabalhadoreducando.id).filter(email_academico=email_academico).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if Servidor.objects.filter(email_academico=email_academico).exists():
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if EmailBlockList.objects.filter(email=email_academico).exists():
                raise forms.ValidationError("O e-mail informado está bloqueado.")
            if not settings.DEBUG and 'ldap_backend' in settings.INSTALLED_APPS:
                ldap_conf = LdapConf.get_active()
                usernames = ldap_conf.get_usernames_from_principalname(email_academico)
                if usernames and self.trabalhadoreducando.matricula not in usernames:
                    raise forms.ValidationError("O e-email informado já é utilizado por outro usuário.")
        return email_academico

    def clean_email_google_classroom(self):
        if self.cleaned_data['email_google_classroom']:
            if TrabalhadorEducando.objects.exclude(pk=self.trabalhadoreducando.id).filter(email_google_classroom=self.cleaned_data['email_google_classroom']).exists():
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
            self.trabalhadoreducando.email_academico = self.cleaned_data.get('email_academico')
        if 'email_google_classroom' in self.cleaned_data:
            self.trabalhadoreducando.email_google_classroom = self.cleaned_data.get('email_google_classroom')
        self.trabalhadoreducando.save()
        if 'email_secundario' in self.cleaned_data:
            Pessoa.objects.filter(
                pk=self.trabalhadoreducando.get_vinculo().pessoa.id
            ).update(email_secundario=self.cleaned_data.get('email_secundario'))


class AtualizarDadosPessoaisForm(forms.FormPlus):
    nome_usual = forms.ChoiceField(label="Nome Usual", required=False, help_text='Nome que será exibido no SUAP')
    lattes = forms.URLField(label='Lattes', help_text='Endereço do currículo lattes', required=False)
    logradouro = forms.CharFieldPlus(max_length=255, required=True, label='Logradouro (Avenida, Rua, etc)', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=True, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=True, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='CEP')
    cidade = forms.ModelChoiceFieldPlus(Municipio.objects, required=True, label='Cidade', widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS))

    telefone_principal = forms.CharFieldPlus(max_length=255, label='Telefone Principal', required=True)
    telefone_secundario = forms.CharFieldPlus(max_length=255, label='Celular', required=False)
    esconde_telefone = forms.CharFieldPlus(max_length=1, label='esconde_telefone', required=False, widget=forms.HiddenInput())

    utiliza_transporte_escolar_publico = forms.ChoiceField(label='Utiliza Transporte Escolar Público', required=True, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    poder_publico_responsavel_transporte = forms.ChoiceField(
        label='Poder Público Responsável pelo Transporte Escolar', choices=[['', '---------']] + TrabalhadorEducando.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, required=False
    )
    tipo_veiculo = forms.ChoiceField(label='Tipo de Veículo Utilizado no Transporte Escolar', choices=[['', '---------']] + TrabalhadorEducando.TIPO_VEICULO_CHOICES_FOR_FORM, required=False)

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
    trabalhadoreducando = forms.ModelChoiceField(TrabalhadorEducando.objects, widget=forms.HiddenInput())
    foto = forms.PhotoCaptureField(required=False, widget=PhotoCapturePortraitInput)
    arquivo = forms.ImageFieldPlus(required=False)

    fieldsets = (
        ('Captura da Foto com Câmera', {'fields': ('trabalhadoreducando', 'foto')}),
        ('Upload de Arquivo', {'fields': ('arquivo',)})
    )

    def clean(self):
        if not self.cleaned_data.get('foto') and not self.cleaned_data.get('arquivo'):
            raise forms.ValidationError('Retire a foto com a câmera ou forneça um arquivo.')
        else:
            return self.cleaned_data

    def processar(self, request):
        trabalhadoreducando = self.cleaned_data.get('trabalhadoreducando')
        if 'foto' in self.cleaned_data and self.cleaned_data.get('foto'):
            dados = self.cleaned_data.get('foto')
        else:
            dados = self.cleaned_data.get('arquivo').read()

        if request.user.has_perm('ppe.efetuar_matricula'):
            trabalhadoreducando.foto.save(f'{trabalhadoreducando.pk}.jpg', ContentFile(dados))
            trabalhadoreducando.pessoa_fisica.foto.save(f'{trabalhadoreducando.pk}.jpg', ContentFile(dados))
            return 'Foto atualizada com sucesso.'
        else:
            return 'Esta funcionalidade encontra-se temporariamente indisponível.'


class EfetuarMatriculaForm(FormWizardPlus):
    METHOD = 'POST'
    LAST_SUBMIT_LABEL = 'Finalizar'

    foto = forms.PhotoCaptureField(required=False, widget=PhotoCapturePortraitInput)
    arquivo_foto = forms.ImageFieldPlus(label='Arquivo', required=False)

    nacionalidade = forms.ChoiceField(required=True, label='Nacionalidade', choices=TrabalhadorEducando.TIPO_NACIONALIDADE_CHOICES)
    cpf = forms.BrCpfField(required=False)
    passaporte = forms.CharField(required=False, label='Nº do Passaporte')
    nome = forms.CharFieldPlus(required=True, label='Nome', width=500)
    nome_social = forms.CharFieldPlus(required=False, label='Nome Social', help_text='Nome social é a designação pela qual a pessoa travesti ou transexual se identifica e é socialmente reconhecida', width=500)
    sexo = forms.ChoiceField(choices=[['M', 'Masculino'], ['F', 'Feminino']])
    data_nascimento = forms.DateFieldPlus(required=True, label='Data de Nascimento')
    estado_civil = forms.ChoiceField(required=True, choices=TrabalhadorEducando.ESTADO_CIVIL_CHOICES)

    # endereco
    logradouro = forms.CharFieldPlus(max_length=255, required=True, label='Logradouro (Avenida, Rua, etc)', width=500)
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

    tipo_zona_residencial = forms.ChoiceField(required=False, label='Zona Residencial', choices=[['', '-----']] + TrabalhadorEducando.TIPO_ZONA_RESIDENCIAL_CHOICES)

    # dados familiares
    nome_pai = forms.CharFieldPlus(max_length=255, label='Nome do Pai', required=False, width=500)
    estado_civil_pai = forms.ChoiceField(choices=TrabalhadorEducando.EMPTY_CHOICES + TrabalhadorEducando.ESTADO_CIVIL_CHOICES, required=False)
    nome_mae = forms.CharFieldPlus(max_length=255, label='Nome da Mãe', required=True, width=500)
    # estado_civil_mae = forms.ChoiceField(choices=TrabalhadorEducando.EMPTY_CHOICES + TrabalhadorEducando.ESTADO_CIVIL_CHOICES, required=False)
    # responsavel = forms.CharFieldPlus(max_length=255, label='Nome do Responsável', required=False, width=500, help_text='Obrigatório para menores de idade.')
    parentesco_responsavel = forms.ChoiceField(label='Parentesco com Responsável', choices=[['', '---------']] + TrabalhadorEducando.PARENTESCO_CHOICES, required=False)

    # contato
    telefone_principal = forms.BrTelefoneField(max_length=255, required=True, label='Telefone Principal', help_text='(XX) XXXX-XXXX')
    telefone_secundario = forms.BrTelefoneField(max_length=255, required=False, label='Celular', help_text='(XX) XXXX-XXXX')
    telefone_adicional_1 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    telefone_adicional_2 = forms.BrTelefoneField(max_length=255, required=False, label='Telefone do Responsável', help_text='(XX) XXXX-XXXX')
    email_pessoal = forms.EmailField(max_length=255, required=False, label='E-mail Pessoal')

    # outras informacoes
    tipo_sanguineo = forms.ChoiceField(required=False, label='Tipo Sanguíneo', choices=TrabalhadorEducando.EMPTY_CHOICES + TrabalhadorEducando.TIPO_SANGUINEO_CHOICES)
    pais_origem = forms.ModelChoiceField(Pais.objects, required=False, label='País de Origem', help_text='Obrigatório para estrangeiros')

    estado_naturalidade = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado de Origem', required=False)
    naturalidade = forms.ModelChoiceFieldPlus(
        Municipio.objects,
        label='Naturalidade',
        required=False,
        widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS),
    )

    raca = forms.ModelChoiceField(Raca.objects.all(), required=True, label='Raça')

    # necessidades especiais
    aluno_pne = forms.ChoiceField(label='Portador de Necessidades Especiais', required=True, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    tipo_necessidade_especial = forms.ChoiceField(required=False, label='Deficiência', choices=[['', '---------']] + TrabalhadorEducando.TIPO_NECESSIDADE_ESPECIAL_CHOICES)
    tipo_transtorno = forms.ChoiceField(required=False, label='Transtorno', choices=[['', '---------']] + TrabalhadorEducando.TIPO_TRANSTORNO_CHOICES)
    superdotacao = forms.ChoiceField(required=False, label='Superdotação', choices=[['', '---------']] + TrabalhadorEducando.SUPERDOTACAO_CHOICES)

    # dados escolares
    nivel_ensino_anterior = forms.ModelChoiceField(NivelEnsino.objects, required=True, label='Nível de Ensino')
    tipo_instituicao_origem = forms.ChoiceField(required=True, label='Tipo da Instituição', choices=[['', '---------']] + TrabalhadorEducando.TIPO_INSTITUICAO_ORIGEM_CHOICES)
    nome_instituicao_anterior = forms.CharField(max_length=255, required=False, label='Nome da Instituição')
    ano_conclusao_estudo_anterior = forms.ModelChoiceField(Ano.objects, required=False, label='Ano de Conclusão', help_text='Obrigatório para alunos com nível médio')

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
    tipo_certidao = forms.ChoiceField(required=False, label='Tipo de Certidão', choices=TrabalhadorEducando.TIPO_CERTIDAO_CHOICES)
    cartorio = forms.CharField(max_length=255, required=False,label='Cartório')
    numero_certidao = forms.CharField(max_length=255, required=False, label='Número de Termo')
    folha_certidao = forms.CharField(max_length=255, required=False, label='Folha')
    livro_certidao = forms.CharField(max_length=255, required=False, label='Livro')
    data_emissao_certidao = forms.DateFieldPlus(required=False, label='Data de Emissão')
    matricula_certidao = forms.CharField(max_length=255, required=False, label='Matrícula', help_text='Obrigatório para certidões realizadas a partir de 01/01/2010')

    observacao_matricula = forms.CharField(widget=forms.Textarea(), required=False, label='Observação')

    utiliza_transporte_escolar_publico = forms.ChoiceField(label='Utiliza Transporte Escolar Público', required=False, choices=[['', '---------'], ['Sim', 'Sim'], ['Não', 'Não']])
    poder_publico_responsavel_transporte = forms.ChoiceField(
        label='Poder Público Responsável pelo Transporte Escolar', choices=[['', '---------']] + TrabalhadorEducando.PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES, required=False
    )
    tipo_veiculo = forms.ChoiceField(label='Tipo de Veículo Utilizado no Transporte Escolar', choices=[['', '---------']] + TrabalhadorEducando.TIPO_VEICULO_CHOICES_FOR_FORM, required=False)

    formacao = forms.ModelChoiceFieldPlus(
        FormacaoPPE.objects, label='Formação', required=True, widget=AutocompleteWidget(search_fields=FormacaoPPE.SEARCH_FIELDS)
    )
    formacao_tecnica = forms.ModelChoiceField(FormacaoTecnica.objects, required=True, label='Formação técnica')
    data_admissao = forms.DateFieldPlus(required=True, label='Data de Admissão')
    data_demissao = forms.DateFieldPlus(required=False, label='Data de Demissão')
    categoria = forms.ChoiceField(choices=TrabalhadorEducando.EMPTY_CHOICES + TrabalhadorEducando.CATEGORIAS_CHOICES, required=False, label='Categoria')
    # conselho classe
    numero_registro = forms.CharField(max_length=255, required=False, label='Número de Registro')
    conselho = forms.ModelChoiceField(ConselhoProfissional.objects, required=False, label='Conselho')

    steps = (
        [('Identificação', {'fields': ('nacionalidade','naturalidade', 'cpf', 'passaporte')})],
        [
            ('Dados Pessoais', {'fields': ('nome', 'nome_social', 'sexo', 'data_nascimento', 'estado_civil')}),
            (
                'Dados Familiares',
                {
                    'fields': (
                        'nome_pai',
                        # 'estado_civil_pai',
                        'nome_mae',
                        # 'estado_civil_mae',
                        # 'responsavel',
                        'parentesco_responsavel',
                    )
                },
            ),
            ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'estado', 'cidade')}),
        ],
        [
            ('Informações para Contato', {'fields': ('telefone_principal', 'telefone_secundario', 'telefone_adicional_1', 'telefone_adicional_2', 'email_pessoal')}),
            ('Deficiências, Transtornos e Superdotação', {'fields': ('aluno_pne', 'tipo_necessidade_especial', 'tipo_transtorno', 'superdotacao')}),
            # ('Transporte Escolar Utilizado', {'fields': ('utiliza_transporte_escolar_publico', 'poder_publico_responsavel_transporte', 'tipo_veiculo')}),
            ('Outras Informações', {'fields': ('tipo_sanguineo', 'pais_origem', 'estado_naturalidade', 'raca')}),
            ('Dados Escolares Anteriores', {'fields': ('nivel_ensino_anterior', 'tipo_instituicao_origem', 'nome_instituicao_anterior', 'ano_conclusao_estudo_anterior','categoria', 'conselho', 'numero_registro')}),
        ],
        [
            ('Informações Profissionais', {'fields': ('formacao_tecnica','data_admissao', 'data_demissao')}),
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
            # ('Certidão Civil', {'fields': ('tipo_certidao', 'cartorio', 'numero_certidao', 'folha_certidao', 'livro_certidao', 'data_emissao_certidao', 'matricula_certidao')}),
        ],
        [
            ('Foto  (captura com câmera ou upload de arquivo)', {'fields': ('foto', 'arquivo_foto')}),
            (
                'Dados da Matrícula',
                {
                    'fields': (
                        'formacao',
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
            raise forms.ValidationError('O Ano de Conclusão é de preenchimento obrigatório para Nível Médio.')
        return ano_conclusao_estudo_anterior

    # def clean_utiliza_transporte_escolar_publico(self):
    #     utiliza_transporte_escolar_publico = self.cleaned_data.get('utiliza_transporte_escolar_publico')
    #     if utiliza_transporte_escolar_publico == 'Sim':
    #         if not self.data.get('poder_publico_responsavel_transporte') or not self.data.get('tipo_veiculo'):
    #             raise forms.ValidationError('Informe o responsável pelo transporte público e o tipo utilizado')
    #     else:
    #         if self.data.get('poder_publico_responsavel_transporte') or self.data.get('tipo_veiculo'):
    #             raise forms.ValidationError('Marque a opção "Utiliza Transporte Escolar Público" caso deseje informar o responsável ou tipo de transporte público utilizado.')
    #     return utiliza_transporte_escolar_publico

    def clean_aluno_pne(self):
        aluno_pne = self.cleaned_data.get('aluno_pne')

        if aluno_pne == 'Sim' and not (self.data.get('tipo_necessidade_especial') or self.data.get('tipo_transtorno') or self.data.get('superdotacao')):
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

    # def clean_responsavel(self):
    #     nome = self.get_entered_data('responsavel')

    #     if nome and not eh_nome_completo(nome):
    #         raise ValidationError('O nome do responsável precisa ser completo e não pode conter números.')

    #     p = PessoaFisica()
    #     p.nascimento_data = self.get_entered_data('data_nascimento')

    #     if p.nascimento_data and p.idade < 18 and not nome:
    #         raise ValidationError('Campo obrigatório para menores de idade.')

    #     return nome

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
    
    def clean_numero_registro(self):
        if 'categoria' in self.cleaned_data:
            categoria = self.cleaned_data.get('categoria')
            numero_registro = self.cleaned_data.get('numero_registro')
            if not numero_registro and categoria in ['Enfermagem', 'Nutrição', 'Análises Clínicas']:
                raise forms.ValidationError(
                    'O campo Número de Registro é obrigatório caso a categoria seja Enfermagem, Nutrição ou Análises Clínicas'
                )
        return numero_registro

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

    def clean(self):

        formacao = self.cleaned_data.get('formacao')
        cpf = self.cleaned_data.get('cpf')
        if formacao and cpf:
            qs_te = TrabalhadorEducando.objects.filter(formacao=formacao,  pessoa_fisica__cpf=cpf)
            if qs_te.exists():
                raise forms.ValidationError('Matrícula duplicada')


        return self.cleaned_data

    @transaction.atomic
    def processar(self):
        pessoa_fisica = PessoaFisica()
        pessoa_fisica.cpf = self.cleaned_data['cpf']
        pessoa_fisica.nome_registro = self.cleaned_data['nome']
        pessoa_fisica.nome_social = self.cleaned_data['nome_social']
        pessoa_fisica.sexo = self.cleaned_data['sexo']
        pessoa_fisica.nascimento_data = self.cleaned_data['data_nascimento']
        pessoa_fisica.save()

        trabalhadoreducando = TrabalhadorEducando()
        trabalhadoreducando.periodo_atual = 1
        trabalhadoreducando.pessoa_fisica = pessoa_fisica
        trabalhadoreducando.estado_civil = self.cleaned_data['estado_civil']
        # dados familiares
        trabalhadoreducando.nome_pai = self.cleaned_data['nome_pai']
        # trabalhadoreducando.estado_civil_pai = self.cleaned_data['estado_civil_pai']
        trabalhadoreducando.nome_mae = self.cleaned_data['nome_mae']
        # trabalhadoreducando.estado_civil_mae = self.cleaned_data['estado_civil_mae']
        # trabalhadoreducando.responsavel = self.cleaned_data['responsavel']
        trabalhadoreducando.parentesco_responsavel = self.cleaned_data['parentesco_responsavel']
        # endereco
        trabalhadoreducando.logradouro = self.cleaned_data['logradouro']
        trabalhadoreducando.numero = self.cleaned_data['numero']
        trabalhadoreducando.complemento = self.cleaned_data['complemento']
        trabalhadoreducando.bairro = self.cleaned_data['bairro']
        trabalhadoreducando.cep = self.cleaned_data['cep']
        trabalhadoreducando.cidade = self.cleaned_data['cidade']
        # trabalhadoreducando.tipo_zona_residencial = self.cleaned_data['tipo_zona_residencial']
        # contato
        trabalhadoreducando.telefone_principal = self.cleaned_data['telefone_principal']
        trabalhadoreducando.telefone_secundario = self.cleaned_data['telefone_secundario']
        trabalhadoreducando.telefone_adicional_1 = self.cleaned_data['telefone_adicional_1']
        trabalhadoreducando.telefone_adicional_2 = self.cleaned_data['telefone_adicional_2']

        # transporte escolar
        # if self.cleaned_data['utiliza_transporte_escolar_publico']:
        #     trabalhadoreducando.poder_publico_responsavel_transporte = self.cleaned_data['poder_publico_responsavel_transporte']
        #     trabalhadoreducando.tipo_veiculo = self.cleaned_data['tipo_veiculo']
        # else:
        #     trabalhadoreducando.poder_publico_responsavel_transporte = None
        #     trabalhadoreducando.tipo_veiculo = None

        # outras informacoes
        trabalhadoreducando.tipo_sanguineo = self.cleaned_data['tipo_sanguineo']
        trabalhadoreducando.nacionalidade = self.cleaned_data['nacionalidade']
        trabalhadoreducando.passaporte = self.cleaned_data['passaporte']
        trabalhadoreducando.naturalidade = self.cleaned_data['naturalidade']
        trabalhadoreducando.pessoa_fisica.raca = self.cleaned_data['raca']

        if self.cleaned_data['aluno_pne']:
            trabalhadoreducando.tipo_necessidade_especial = self.cleaned_data['tipo_necessidade_especial']
            trabalhadoreducando.tipo_transtorno = self.cleaned_data['tipo_transtorno']
            trabalhadoreducando.superdotacao = self.cleaned_data['superdotacao']
        else:
            trabalhadoreducando.tipo_necessidade_especial = None
            trabalhadoreducando.tipo_transtorno = None
            trabalhadoreducando.superdotacao = None

        # dados escolares
        trabalhadoreducando.nivel_ensino_anterior = self.cleaned_data['nivel_ensino_anterior']
        trabalhadoreducando.tipo_instituicao_origem = self.cleaned_data['tipo_instituicao_origem']
        trabalhadoreducando.nome_instituicao_anterior = self.cleaned_data['nome_instituicao_anterior']
        trabalhadoreducando.ano_conclusao_estudo_anterior = self.cleaned_data['ano_conclusao_estudo_anterior']
        trabalhadoreducando.categoria = self.cleaned_data['categoria']

        trabalhadoreducando.formacao_tecnica = self.cleaned_data['formacao_tecnica']
        trabalhadoreducando.data_admissao = self.cleaned_data['data_admissao']
        trabalhadoreducando.data_demissao = self.cleaned_data['data_demissao']

        # conselho classe
        trabalhadoreducando.numero_registro = self.cleaned_data['numero_registro']
        trabalhadoreducando.conselho = self.cleaned_data['conselho']
        # rg
        trabalhadoreducando.numero_rg = self.cleaned_data['numero_rg']
        trabalhadoreducando.uf_emissao_rg = self.cleaned_data['uf_emissao_rg']
        trabalhadoreducando.orgao_emissao_rg = self.cleaned_data['orgao_emissao_rg']
        trabalhadoreducando.data_emissao_rg = self.cleaned_data['data_emissao_rg']
        # titulo_eleitor
        trabalhadoreducando.numero_titulo_eleitor = self.cleaned_data['numero_titulo_eleitor']
        trabalhadoreducando.zona_titulo_eleitor = self.cleaned_data['zona_titulo_eleitor']
        trabalhadoreducando.secao = self.cleaned_data['secao']
        trabalhadoreducando.data_emissao_titulo_eleitor = self.cleaned_data['data_emissao_titulo_eleitor']
        trabalhadoreducando.uf_emissao_titulo_eleitor = self.cleaned_data['uf_emissao_titulo_eleitor']
        # carteira de reservista
        trabalhadoreducando.numero_carteira_reservista = self.cleaned_data['numero_carteira_reservista']
        trabalhadoreducando.regiao_carteira_reservista = self.cleaned_data['regiao_carteira_reservista']
        trabalhadoreducando.serie_carteira_reservista = self.cleaned_data['serie_carteira_reservista']
        trabalhadoreducando.estado_emissao_carteira_reservista = self.cleaned_data['estado_emissao_carteira_reservista']
        trabalhadoreducando.ano_carteira_reservista = self.cleaned_data['ano_carteira_reservista']
        # certidao_civil
        # trabalhadoreducando.tipo_certidao = self.cleaned_data['tipo_certidao']
        # trabalhadoreducando.cartorio = self.cleaned_data['cartorio']
        # trabalhadoreducando.numero_certidao = self.cleaned_data['numero_certidao']
        # trabalhadoreducando.folha_certidao = self.cleaned_data['folha_certidao']
        # trabalhadoreducando.livro_certidao = self.cleaned_data['livro_certidao']
        # trabalhadoreducando.data_emissao_certidao = self.cleaned_data['data_emissao_certidao']
        # trabalhadoreducando.matricula_certidao = self.cleaned_data['matricula_certidao']

        trabalhadoreducando.formacao = self.cleaned_data['formacao']
        trabalhadoreducando.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
        hoje = datetime.date.today()
        ano= hoje.year
        prefixo = f'{ano}PPE'
        trabalhadoreducando.matricula = SequencialMatriculaTrabalhadorEducando.proximo_numero(prefixo)

        trabalhadoreducando.email_scholar = ''
        trabalhadoreducando.save()

        observacao = self.cleaned_data['observacao_matricula']
        if observacao:
            obs = Observacao()
            obs.trabalhadoreducando = trabalhadoreducando
            obs.data = datetime.datetime.now()
            obs.observacao = observacao
            obs.usuario = self.request.user
            obs.save()

        trabalhadoreducando.pessoa_fisica.username = self.cleaned_data['cpf'].replace('.', '').replace('-', '')
        trabalhadoreducando.pessoa_fisica.email_secundario = self.cleaned_data['email_pessoal']
        trabalhadoreducando.pessoa_fisica.save()

        if 'foto' in self.cleaned_data and self.cleaned_data.get('foto'):
            trabalhadoreducando.foto.save(f'{trabalhadoreducando.pk}.jpg', ContentFile(self.cleaned_data['foto']))
        elif 'arquivo_foto' in self.cleaned_data and self.cleaned_data.get('arquivo_foto'):
            trabalhadoreducando.foto.save(f'{trabalhadoreducando.pk}.jpg', ContentFile(self.cleaned_data.get('arquivo_foto').read()))

        trabalhadoreducando.save()

        return trabalhadoreducando


class ObservacaoForm(forms.ModelForm):
    class Meta:
        model = Observacao
        exclude = ('trabalhadoreducando', 'usuario', 'data')

    def __init__(self, trabalhadoreducando, usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trabalhadoreducando = trabalhadoreducando
        self.usuario = usuario

    def save(self, *args, **kwargs):
        self.instance.trabalhadoreducando = self.trabalhadoreducando
        self.instance.usuario = self.usuario
        self.instance.data = datetime.datetime.now()
        self.instance.save()


class FormacaoPPEForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = FormacaoPPE
        exclude = ()

    def clean(self):
        try:
            ch_componentes_obrigatorios = int(self.cleaned_data.get('ch_componentes_obrigatorios', 0))
        except Exception:
            raise forms.ValidationError("Cargas horárias inválidas.")

        return self.cleaned_data

#FES-37
class EstruturaCursoForm(forms.ModelFormPlus):
    #tipo_avaliacao = forms.ChoiceField(label='Tipo de Avaliação', widget=forms.RadioSelect(), choices=EstruturaCurso.TIPO_AVALIACAO_CHOICES)
    criterio_avaliacao = forms.ChoiceField(label='Critério de Avaliação', widget=forms.RadioSelect(), choices=EstruturaCurso.CRITERIO_AVALIACAO_CHOICES)
    #ira = forms.ChoiceField(label='Forma de Cálculo', widget=forms.RadioSelect(), choices=EstruturaCurso.IRA_CHOICES)

    class Meta:
        model = EstruturaCurso
        exclude = ()

    class Media:
        js = ('/static/edu/js/EstruturaCursoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # if self.instance.numero_max_certificacoes is None:
        #     self.initial.update(numero_max_certificacoes=4)

#FES-39
class CursoForm(forms.ModelFormPlus):

    class Meta:
        model = Curso
        exclude = ()

    class Media:
        js = ('/static/edu/js/CursoCampusForm.js',)


class ReplicacaFormacaoPPEForm(forms.FormPlus):
    SUBMIT_LABEL = 'Replicar Formação PPE'
    descricao = forms.CharFieldPlus(width=500, label='Descrição', required=True)

    def __init__(self, formacao_ppe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formacao_ppe = formacao_ppe
        self.fields['descricao'].initial = f'{self.formacao_ppe.descricao} [REPLICADO]'

    def processar(self):
        self.formacao_ppe.replicar(self.cleaned_data['descricao'])
        return self.formacao_ppe


class CursoFormacaoPPEForm(forms.ModelFormPlus):
    formacao_ppe = forms.ModelChoiceField(queryset=FormacaoPPE.objects, widget=forms.HiddenInput())
    curso = forms.ModelChoiceFieldPlus(Curso.objects)
    estrutura = forms.ModelChoiceFieldPlus(
        EstruturaCurso.objects, label='Estrutura de curso', widget=AutocompleteWidget(), required= True)


    class Meta:
        model = CursoFormacaoPPE
        exclude = ()

    def __init__(self, formacao_ppe, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formacao_ppe = formacao_ppe
        self.fields['curso'].queryset = self.fields['curso'].queryset.all()
        self.fields['pre_requisitos'].queryset = self.fields['pre_requisitos'].queryset.filter(formacao_ppe=self.formacao_ppe)
        self.fields['formacao_ppe'].initial = self.formacao_ppe.pk
        self.fields['ch_pratica'].initial = 0

    fieldsets = (
        (
            'Dados Gerais',
            {
                'fields': (
                    'formacao_ppe',
                    'curso',
                    ('tipo', 'estrutura', 'qtd_avaliacoes'),
                )
            },
        ),
        ('Carga Horária', {'fields': (('ch_presencial', 'ch_pratica')),}),
        ('Plano de Ensino', {'fields': ('ementa',)}),
    )

    def clean(self):
        formacao = self.formacao_ppe
        curso = self.cleaned_data.get('curso')
        existentes = CursoFormacaoPPE.objects.filter(formacao_ppe=formacao, curso=curso)
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            self.add_error('curso', f"O curso já está vinculado a esta formação")


class GerarTurmasPPEForm(FormWizardPlus):
    METHOD = 'GET'
    QTD_TURMAS_CHOICES = [[0, '0'], [1, '1'], [2, '2'], [3, '3'], [4, '4'], [5, '5'], [6, '6'], [7, '7'], [8, '8'], [9, '9']]

    class Media:
        js = ('/static/ppe/js/GerarTurmasForm.js',)

    grupo = forms.CharField(required=True, label='Grupo', help_text='Formato: AA<strong>1</strong>')
    formacao = forms.ModelChoiceFieldPlus(
        FormacaoPPE.objects, label='Formação', widget=AutocompleteWidget(search_fields=FormacaoPPE.SEARCH_FIELDS)
    )
    qtd_tumas = forms.ChoiceField(label='Nº de Turmas', required=True, choices=QTD_TURMAS_CHOICES)
    vagas = forms.IntegerFieldPlus(label='Nº de Vagas', required=True)

    cursos = forms.MultipleModelChoiceField(CursoFormacaoPPE.objects, label='', widget=RenderableSelectMultiple('widgets/cursos_widget.html'))
    confirmacao = forms.BooleanField(
        label='Confirmação', required=True, help_text='Marque a opção acima e clique no botão "Finalizar" caso deseje que as turmas/cursos identificados acima sejam criados.'
    )

    steps = (
        [('Dados da oferta', {'fields': ('grupo',  'formacao')}),
         ('Turmas', {'fields': ('qtd_tumas', 'vagas')}),],
        [('Seleção de cursos', {'fields': ('cursos',)})],
        [('Confirmação dos Dados', {'fields': ('confirmacao',)})],
    )

    def __init__(self, request, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)


    def next_step(self):

        formacao = self.get_entered_data('formacao')

        if 'formacao' in self.fields:
            self.fields['formacao'].queryset = FormacaoPPE.objects.filter(ativo=True)

        if 'cursos' in self.fields and formacao:
            formacao = formacao
            qs = formacao.cursoformacaoppe_set.all()
            self.fields['cursos'].queryset = qs.order_by('tipo')

        if 'cursos' in self.cleaned_data:
            self.processar(False)

    def processar(self, commit=True):
        formacao = self.cleaned_data['formacao']

        numero_turmas_dict = {}
        numero_vagas_dict = {}
        # for i in range(1, matriz_curso.matriz.qtd_periodos_letivos + 1):
        #     numero_turmas_dict[i] = int(self.cleaned_data[f'qtd_periodo_{i}'] or 0)
        #     turnos_dict[i] = self.cleaned_data[f'turno_periodo_{i}'] or None
        #     numero_vagas_dict[i] = self.cleaned_data[f'vagas_periodo_{i}'] or 0
        #
        grupo = self.cleaned_data['grupo']
        qtd_tumas = self.cleaned_data['qtd_tumas']
        vagas = self.cleaned_data['vagas']
        cursos = self.cleaned_data['cursos']
        confirmacao = self.cleaned_data.get('confirmacao')
        commit = commit and confirmacao

        self.turmas = Turma.gerar_turmas(
            grupo,
            qtd_tumas,
            vagas,
            formacao,
            cursos,
            commit,
        )

class TurmaPPEForm(forms.ModelFormPlus):
    # codigo = forms.CharField(label='Código', widget=forms.TextInput(attrs=dict(readonly='readonly')))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        turma = super().save(*args, **kwargs)
        # for diario in turma.diario_set.all():
        #     if diario.quantidade_vagas != turma.quantidade_vagas:
        #         diario.quantidade_vagas = turma.quantidade_vagas
        #         diario.save()
        return turma

    class Meta:
        model = Turma
        exclude = ('grupo', 'sequencial', 'codigo' )


class TutorTurmaForm(forms.ModelFormPlus):
    turma = forms.ModelChoiceField(queryset=Turma.objects, widget=forms.HiddenInput())
    tutor = forms.ModelChoiceField(queryset=Bolsista.objects, label='Tutor', required=True, widget=AutocompleteWidget(search_fields=Bolsista.SEARCH_FIELDS))

    class Meta:
        model = TutorTurma
        fields = ('turma', 'tutor', 'ativo')

    fieldsets = (('', {'fields': ('turma', 'tutor', ('ativo',), )}),)

    def __init__(self, turma, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs_bolsista = Bolsista.objects.filter(user__groups__name='Tutor PPE')
        if self.instance.pk:
            qs_bolsista = Bolsista.objects.filter(user__groups__name='Tutor PPE')

        self.fields['tutor'].queryset = qs_bolsista.distinct()
        self.fields['turma'].queryset = Turma.objects.all()

        if self.instance.pk:
            self.fields['tutor'].initial = self.instance.tutor.pk

        is_administrador = in_group(self.request.user, 'Coordenador(a) PPE')
        if not is_administrador:
            self.fields['ativo'].widget = forms.HiddenInput()

        self.turma = turma
        if self.turma:
            self.fields['turma'].initial = self.turma.pk

        for field_name in self.fields:
            if 'data_' in field_name:
                self.fields[field_name].help_text = ''

    def flexibilizar_data(self, data):
        if not data:
            return None
        return somar_data(data, 7)

    def save(self, *args, **kwargs):
        obj = super().save(False)
        obj.turma = self.cleaned_data['turma']
        obj.tutor = self.cleaned_data['tutor']
        obj.save()
    def clean_tutor(self):
        qs = self.turma.tutorturma_set
        if self.instance.id:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists() and self.cleaned_data.get('tutor').id in qs.values_list('tutor__id', flat=True):
            raise forms.ValidationError('Tutor já cadastrado nessa turma.')
        return self.cleaned_data.get('tutor')

    def clean(self):

        return self.cleaned_data


class ApoiadorTurmaForm(forms.ModelFormPlus):
    turma = forms.ModelChoiceField(queryset=Turma.objects, widget=forms.HiddenInput())
    apoiador = forms.ModelChoiceField(queryset=Bolsista.objects, label='Apoiador(a) Pedagógico(a)', required=True,
                                      widget=AutocompleteWidget(search_fields=Bolsista.SEARCH_FIELDS))

    class Meta:
        model = ApoiadorTurma
        fields = ('turma', 'apoiador', 'ativo')

    fieldsets = (('', {'fields': ('turma', 'apoiador', ('ativo',),)}),)

    def __init__(self, turma, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs_bolsista = Bolsista.objects.filter(user__groups__name='Apoiador(a) Pedagógico PPE')
        if self.instance.pk:
            qs_bolsista = Bolsista.objects.filter(user__groups__name='Apoiador(a) Pedagógico PPE')

        self.fields['apoiador'].queryset = qs_bolsista.distinct()
        self.fields['turma'].queryset = Turma.objects.all()

        if self.instance.pk:
            self.fields['apoiador'].initial = self.instance.apoiador.pk

        is_administrador = in_group(self.request.user, 'Coordenador(a) PPE')
        if not is_administrador:
            self.fields['ativo'].widget = forms.HiddenInput()

        self.turma = turma
        if self.turma:
            self.fields['turma'].initial = self.turma.pk

        for field_name in self.fields:
            if 'data_' in field_name:
                self.fields[field_name].help_text = ''

    def save(self, *args, **kwargs):
        obj = super().save(False)
        obj.turma = self.cleaned_data['turma']
        obj.apoiador = self.cleaned_data['apoiador']
        obj.save()

    def clean_apoiador(self):
        qs = self.turma.apoiadorturma_set
        if self.instance.id:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists() and self.cleaned_data.get('apoiador').id in qs.values_list('apoiador__id', flat=True):
            raise forms.ValidationError('Apoiador já cadastrado nessa turma.')
        return self.cleaned_data.get('apoiador')

    def clean(self):

        return self.cleaned_data


class AlterarDataCursoTurmaForm(forms.FormPlus):
    # curso_turma = forms.ModelChoiceField(queryset=CursoTurma.objects, widget=forms.HiddenInput())
    data_inicio_etapa_1 = forms.DateFieldPlus(label='Data Inicial')
    data_fim_etapa_1 = forms.DateFieldPlus(label='Data Final')
    replicar = forms.BooleanField(label='Replicar datas em todos os cursos iguais do grupo', required= False)
    def __init__(self, curso_turma, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if curso_turma:
            self.curso_turma = curso_turma

    def clean(self):
        data_inicio_etapa_1 = self.cleaned_data.get('data_inicio_etapa_1')
        data_fim_etapa_1 = self.cleaned_data.get('data_fim_etapa_1')
        # verificando se a data de início da etapa 1 é maior que a data de encerramento da mesma etapa
        if data_inicio_etapa_1 and data_fim_etapa_1 and data_inicio_etapa_1 > data_fim_etapa_1:
            raise forms.ValidationError(
                'A data de início da etapa 1 não pode ser maior que a data de encerramento da mesma etapa.')
        # verificando se o usuário preencheu a data de inicio da etapa 1 e não preencheu a data de encerramento da mesma etapa
        if data_inicio_etapa_1 and not data_fim_etapa_1:
            raise forms.ValidationError('Favor preencher a data de encerramento da etapa 1.')
        # verificando se o usuário preencheu a data de encerramento da etapa 1 e não preencheu a data inicio da mesma etapa
        if data_fim_etapa_1 and not data_inicio_etapa_1:
            raise forms.ValidationError('Favor preencher a data de início da etapa 1.')

        return self.cleaned_data
    def processar(self):
        data_inicio_etapa_1 = self.cleaned_data['data_inicio_etapa_1']
        data_fim_etapa_1 = self.cleaned_data['data_fim_etapa_1']
        self.curso_turma.data_inicio_etapa_1 =data_inicio_etapa_1
        self.curso_turma.data_fim_etapa_1 =data_fim_etapa_1
        self.curso_turma.save()

        replicar = self.cleaned_data['replicar']
        if replicar:
            qs_cursos = CursoTurma.objects.filter(turma__grupo__exact=self.curso_turma.turma.grupo, curso_formacao=self.curso_turma.curso_formacao)
            for curso in qs_cursos:
                curso.data_inicio_etapa_1 = data_inicio_etapa_1
                curso.data_fim_etapa_1 = data_fim_etapa_1
                curso.data_inicio_prova_final = data_inicio_etapa_1
                curso.data_fim_prova_final = data_fim_etapa_1
                curso.save()

class AnamneseForm(forms.ModelFormPlus):
    participa_rede_social = forms.ModelMultipleChoiceField(label='Participa de alguma rede social?', 
                                                            queryset=RedeSocial.objects.all(), 
                                                            required=True, widget=forms.CheckboxSelectMultiple)
    #TROCAR PARA REQUIRED = TRUE DEPOIS
    estado = forms.ModelChoiceField(UnidadeFederativa.objects, label='Estado de Nascimento', required=False)
    identidade_genero = forms.ChoiceField(label='Sexo/identidade de gênero', required=True, 
                                            widget=forms.RadioSelect, choices=Anamnese.SEXO_IDENTIDADE_GENERO_CHOICES)
    orientacao_sexual = forms.ChoiceField(label='Qual a sua orientação sexual?', required=True, widget=forms.RadioSelect, 
                                            choices=Anamnese.ORIENTACAO_SEXUAL_CHOICES)
    raça = forms.ChoiceField(label='Raça/Cor', required=True, widget=forms.RadioSelect, choices=Anamnese.RACA_COR_CHOICES)
    religiao = forms.ChoiceField(label='Religião', required=True, widget=forms.RadioSelect, choices=Anamnese.RELIGIAO_CHOICES)
    denominacao_evangelica = forms.ChoiceField(label='Se for evangélica, informe a denominação a qual está vinculado(a)', 
                                                required=False, widget=forms.RadioSelect, 
                                                choices=Anamnese.DENOMINACAO_EVANGELICA_CHOICES)
    trabalhou_anteriormente = forms.ChoiceField(label='Você já trabalhou antes do PPE?', required=True, widget=forms.RadioSelect, 
                                                choices=Anamnese.SIM_NAO_CHOICES)
    onde_trabalhou_anteriormente = forms.ChoiceField(label='Caso você tenha trabalhado antes de ingressar no PPE, onde foi?', 
                                                    required=False, widget=forms.RadioSelect, 
                                                    choices=Anamnese.TRABALHO_ANTERIOR_PPE_CHOICES)

    meio_transporte = forms.ModelMultipleChoiceField(label='Qual o meio de transporte utilizadoem seu deslocamento para o trabalho?',
                                        queryset=MeioTransporte.objects.all(), 
                                        required=True, widget=forms.CheckboxSelectMultiple)

    chefe_parental = forms.ChoiceField(label='Você era chefa de família monoparental (sozinha)? (pergunta exclusiva para mulheres)', 
                                        required=False, widget=forms.RadioSelect, choices=Anamnese.SIM_NAO_CHOICES)
    estado_civil = forms.ChoiceField(label='Estado Civil', required=True, widget=forms.RadioSelect, choices=Anamnese.ESTADO_CIVIL_CHOICES)
    tem_filhos = forms.ChoiceField(label='Tem filhos?', required=True, widget=forms.RadioSelect, choices=Anamnese.SIM_NAO_CHOICES)
    reside_com = forms.ModelMultipleChoiceField(label='Reside Com', required=True, widget=forms.CheckboxSelectMultiple, queryset=ResideCom.objects.all(),)
    membros_familia_carteira_assinada = forms.ModelMultipleChoiceField(label='Quais membros da sua família trabalham com carteira assinada?', 
                                                            queryset=MembrosCarteiraAssinada.objects.all(), 
                                                            required=True, widget=forms.CheckboxSelectMultiple, 
                                                            )
    renda_familiar = forms.ChoiceField(label='Renda familiar mensal', 
                                        required=True, widget=forms.RadioSelect, choices=Anamnese.RENDA_FAMILIAR_CHOICES)
    responsabilidade_financeira = forms.ChoiceField(label='Qual a sua responsabilidade financeira pela manutenção da sua família?', 
                                                    required=True, widget=forms.RadioSelect, 
                                                    choices=Anamnese.RESPONSABILIDADE_FINANCEIRA_CHOICES)
    veiculo_automotor = forms.ChoiceField(label='Veículo Automotor', required=True, widget=forms.RadioSelect, 
                                            choices=Anamnese.VEICULO_CHOICES)

    moradia = forms.ChoiceField(label='Moradia', required=True, widget=forms.RadioSelect, choices=Anamnese.MORADIA_CHOICES)
    tipo_moradia = forms.ChoiceField(label='Tipo de Moradia', required=True, widget=forms.RadioSelect, 
                                    choices=Anamnese.TIPO_MORADIA_CHOICES)
    estrutura_moradia = forms.ChoiceField(label='Estutura da Moradia', required=True, widget=forms.RadioSelect, 
                                            choices=Anamnese.ESTRUTURA_MORADIA_CHOICES) 
    residencia_saneamento_basico = forms.ModelMultipleChoiceField(label='Sua residência tem (*pode escolher mais de uma opção)',  
                                                                    queryset=ResidenciaSaneamentoBasico.objects.all(), required=True, 
                                                                    widget=forms.CheckboxSelectMultiple)
    itens_residencia = forms.ModelMultipleChoiceField(label='Sua residência tem (*pode escolher mais de uma opção)', 
                                                        queryset=ItensResidencia.objects.all(), 
                                                        required=True, widget=forms.CheckboxSelectMultiple)
    fumante = forms.ChoiceField(label='Fumo?', required=True, widget=forms.RadioSelect, choices=Anamnese.SIM_NAO_CHOICES)
    
    bebida_alcoolica = forms.ChoiceField(label='Consumo de bebida alcoólica', required=True, widget=forms.RadioSelect, 
                                        choices=Anamnese.CONSUMO_BEBIDA_ALCOOLICA_CHOICES)
    substancias_psicoativas = forms.ChoiceField(label='Uso de substâncias psicoativas (drogas não permitidas)', required=True, 
                                                    widget=forms.RadioSelect, choices=Anamnese.CONSUMO_BEBIDA_ALCOOLICA_CHOICES)
    atividade_fisica = forms.ChoiceField(label='Pratica atividade física', required=True, widget=forms.RadioSelect, 
                                            choices=Anamnese.CONSUMO_BEBIDA_ALCOOLICA_CHOICES)
    participa_grupos_sociais = forms.ModelMultipleChoiceField(label='Participação em grupos sociais (*pode escolher mais de uma opção)', 
                                                                queryset=ParticipacaoGruposSociais.objects.all(), required=True, 
                                                                widget=forms.CheckboxSelectMultiple)

    fez_cursos = forms.ModelMultipleChoiceField(label='Você fez ou faz algum desses cursos?', 
                                                queryset=CursosTrabalhadorEducando.objects.all(), 
                                                required=True, widget=forms.CheckboxSelectMultiple)
    tentou_faculdade = forms.ChoiceField(label='Tentou acesso à faculdade/universidade?', 
                                                required=True, widget=forms.RadioSelect, 
                                                choices=Anamnese.SIM_NAO_CHOICES)
    ingressou_faculdade = forms.ChoiceField(label='Ingressou em alguma faculdade/universidade?', 
                                                required=True, widget=forms.RadioSelect, 
                                                choices=Anamnese.SIM_NAO_CHOICES)

    fieldsets = (        
            ('Caracterizacao Pessoal', {'fields': (('nome', 'cpf', 'telefone', 'numero_whatsapp', 
                                                    'email', 'participa_rede_social', 'link_facebook', 'link_instagram', 'outra_rede_social', 
                                                    'identidade_genero', 'outro_genero', 'orientacao_sexual', 'outra_orientacao', 
                                                    'idade', 'raça', 'religiao', 'outra_religiao', 'denominacao_evangelica', 
                                                    'outra_denominacao_evangelica', 'cidade', 'estado', 'trabalhou_anteriormente', 
                                                    'onde_trabalhou_anteriormente', 'outro_tipo_trabalho')),}),
            
            ('Caracterização Geral PPE', {'fields': (('ano_conclusao_tecnico_medio', 'ano_ingresso_ppe', 'formacao_tecnica', 
                                                        'municipio_antes_ppe', 'municipio_ppe', 'unidade_trabalho', 
                                                        'meio_transporte', 'outro_meio')),}),
            
            ('Estrutura Familiar', {'fields': (('chefe_parental', 'estado_civil', 'outro_estado_civil', 'tem_filhos', 
                                                'quantidade_filhos', 'local_residencia', 'cidade_residencia', 'reside_com', 
                                                'ouras_pessoas_moradia', 'total_moradores', 'membros_familia_carteira_assinada', 
                                                'outros_membros_carteira_assinada', 'renda_familiar', 'responsabilidade_financeira', 
                                                'veiculo_automotor')),}),
            ('Estrutura Residencial', {'fields': (('moradia', 'tipo_moradia', 'estrutura_moradia', 'outro_tipo_moradia', 
                                                    'quantidade_quartos', 'quantidade_banheiros', 'residencia_saneamento_basico', 
                                                    'outra_fonte_agua', 'outro_tipo_esgoto', 'outra_fonte_energia', 
                                                    'itens_residencia', 'quantidade_tvs', 'quantidade_celulares', 
                                                    'quantidade_computadores', 'quantidade_notebooks', 'quantidade_tablets')),}),
            ('Estilo de Vida', {'fields': (('fumante', 'bebida_alcoolica', 'substancias_psicoativas', 'atividade_fisica', 
                                            'participa_grupos_sociais', 'participa_conselho_politica', 'participa_outros_grupos')),}),
            ('Hábitos de Estudo', {'fields': (('fez_cursos', 'outro_curso_tecnico', 'outro_curso_profissional', 'outro_curso', 
                                                'tentou_faculdade', 'ingressou_faculdade', 'ano_faculdade', 'forma_ingresso_faculdade', 
                                                'modalidade_faculdade', 'tipo_faculdade', 'beneficio_faculdade', 'outro_beneficio')),}),
    )    

    class Meta:
        model = Anamnese
        exclude = ('trabalhador_educando',)
    
    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data
        
        return self.cleaned_data
    
    def __init__(self, trabalhador_educando, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trabalhador_educando = trabalhador_educando

class MatricularTrabalhadorEducandoTurmaForm(forms.Form):
    METHOD = 'POST'
    turma = forms.ModelChoiceField(Turma.objects, label='Turma', widget=forms.RadioSelect(), empty_label=None)

    def __init__(self, trabalhador_educando, *args, **kwargs):
        self.trabalhador_educando = trabalhador_educando
        super().__init__(*args, **kwargs)
        pks = []
        for turma in trabalhador_educando.get_turmas_matricula_online():
            pks.append(turma.pk)
        self.fields['turma'].queryset = Turma.objects.filter(pk__in=pks)

    def processar(self):
        turma = self.cleaned_data.get('turma')
        trabalhadores_educando = TrabalhadorEducando.objects.filter(pk=self.trabalhador_educando.pk)
        turma.matricular_trabalhadores_educando(trabalhadores_educando)


class MatricularTrabalhadorEducandoAvulsoCursoTurmaoForm(forms.FormPlus):
    METHOD = 'POST'
    SUBMIT_LABEL = 'Inserir trabalhador educando'
    trabalhador_educando = forms.ModelChoiceFieldPlus(TrabalhadorEducando.objects, label='Aluno', widget=AutocompleteWidget(search_fields=TrabalhadorEducando.SEARCH_FIELDS), required=True)

    def __init__(self, curso_turma, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.curso_turma = curso_turma
        self.fields['trabalhador_educando'].queryset = (
            TrabalhadorEducando.objects.filter(
                situacao__pk__in=[
                    SituacaoMatricula.MATRICULADO,
                    SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
                    SituacaoMatricula.TRANCADO,
                ],
                formacao__isnull=False,
            ).exclude(matriculacursoturma__curso_turma=curso_turma)
            .distinct()
        )

    def clean(self):
        trabalhador_educando = self.cleaned_data.get('trabalhador_educando')
        if not trabalhador_educando:
            return self.cleaned_data
        ignorar_quebra_requisito = in_group(self.request.user, 'Coordenador(a) PPE')
        pode_ser_matriculado, msg = trabalhador_educando.pode_ser_matriculado_no_curso_turma(self.curso_turma, ignorar_quebra_requisito)
        if not pode_ser_matriculado:
            raise forms.ValidationError(msg)
        # matricula_periodo = self.cleaned_data['trabalhador_educando'].get_ultima_matricula_periodo()
        # if not in_group(self.request.user, 'Coordenador(a) PPE') and (
        #     matricula_periodo.ano_letivo != self.diario.ano_letivo or matricula_periodo.periodo_letivo != self.diario.periodo_letivo
        # ):
        #     raise forms.ValidationError('Alunos com última matrícula período diferente do período letivo do diário não podem ser inseridos.')
        #
        # if self.diario.componente_curricular.componente.pk in trabalhador_educando.get_ids_componentes_cumpridos():
        #     raise forms.ValidationError('O aluno já cursou o componente deste diário.')

        return self.cleaned_data

    def processar(self):
        trabalhador_educando = self.cleaned_data.get('trabalhador_educando')
        matricula_curso_turma = MatriculaCursoTurma()
        matricula_curso_turma.curso_turma = self.curso_turma
        matricula_curso_turma.trabalhador_educando = trabalhador_educando
        matricula_curso_turma.situacao = MatriculaCursoTurma.SITUACAO_CURSANDO
        matricula_curso_turma.save()

        trabalhador_educando.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
        trabalhador_educando.save()



class ConfiguracaoAvaliacaoForm(forms.ModelFormPlus):

    class Media:
        js = ('/static/ppe/js/ConfiguracaoAvaliacaoForm.js',)

    class Meta:
        model = ConfiguracaoAvaliacao
        exclude = ('',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.NOTA_DECIMAL:
            self.fields['observacao'].widget.attrs['class'] = 'notas-decimais'
        forma_atitudinal = [ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_ATITUDINAL, 'Média Atitudinal']
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
        # if self.instance.pk == 1 and not in_group(self.request.user, 'Administrador Acadêmico'):
        #     raise forms.ValidationError('Não é possível alterar a configuração padrão do sistema. Caso necessite, adicione um nova configuração de avaliação para você.')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)

class ItemConfiguracaoAvaliacaoFormset(forms.models.BaseInlineFormSet):
    def clean(self):

        ids_delete = []
        tem_avaliacao_atitudinal = False
        if hasattr(self, 'cleaned_data'):
            for item in self.cleaned_data:
                if 'DELETE' in item and item['DELETE']:
                    if 'id' in item:
                        ids_delete.append(item['id'].id)


            if ids_delete and NotaAvaliacao.objects.filter(item_configuracao_avaliacao__id__in=ids_delete).exclude(nota__isnull=True).exists():
                raise ValidationError('Não é possível excluir o item marcado enquanto houver notas lançadas neste item.')

            qtd_avaliacoes_minimo =  1
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
                    matricula_curso_turma__curso_turma=configuracao_avaliacao.curso_turma, item_configuracao_avaliacao=form.instance, nota__gt=(form.instance.nota_maxima * MULTIPLICADOR_DECIMAL)
                ):
                    raise ValidationError(
                        f'Existe uma nota referente ao item de avaliação {form.instance.sigla} maior do que a nota máxima informada: {form.instance.nota_maxima}'
                    )

        for sigla in siglas:
            if not sigla or len(sigla) > 3:
                raise forms.ValidationError('A sigla das avaliações devem ter até 3 caracteres')

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

        else:
            raise forms.ValidationError('Informe ao menos um item de configuração da avaliação.')


class SolicitacaoUsuarioForm(forms.ModelFormPlus):
    id = forms.CharField(label='Id', widget=forms.TextInput(attrs=dict(readonly='readonly')))

    class Meta:
        model = SolicitacaoUsuario
        fields = ('id',)

class SolicitacaoAtendimentoPsicossocialForm(forms.ModelFormPlus):
    def __init__(self, trabalhadoreducando, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.trabalhadoreducando = trabalhadoreducando


    class Meta:
        model = SolicitacaoAtendimentoPsicossocial
        fields = ('motivo','preferencia_contato')

class SolicitacaoContinuidadeAperfeicoamentoProfissionalForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoContinuidadeAperfeicoamentoProfissional
        fields = ('anexo_termo', 'observacao',)

    def __init__(self, trabalhadoreducando, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.trabalhadoreducando = trabalhadoreducando

    def clean_anexo_termo(self):

        arquivo = self.cleaned_data['anexo_termo']
        if arquivo:
            filename = f'{normalizar_nome_proprio(self.instance.trabalhadoreducando.get_nome_social_composto())}  - Upload em {datetime.datetime.now()})'

            arquivo.name = filename

        return arquivo


class SolicitacaoAmpliacaoPrazoCursoForm(forms.ModelFormPlus):
    def __init__(self, trabalhadoreducando, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.trabalhadoreducando = trabalhadoreducando
        self.fields['email'].initial = self.instance.trabalhadoreducando.pessoa_fisica.email

    class Meta:
        model = SolicitacaoAmpliacaoPrazoCurso
        fields = ('email', 'observacao',)


class SolicitacaoRealocacaoForm(forms.ModelFormPlus):
    def __init__(self, trabalhadoreducando, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.trabalhadoreducando = trabalhadoreducando
        self.fields['a_partir_quando'] = forms.DateFieldPlus()

    class Meta:
        model = SolicitacaoRealocacao
        fields = ('unidade_lotacao', 'novo_setor_trabalho', 'motivo','nome_nova_chefia', 'cargo_nova_chefia','indicacao_nova_unidade', 'a_partir_quando')


class SolicitacaoVisitaTecnicaUnidadeForm(forms.ModelFormPlus):
    def __init__(self, trabalhadoreducando, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.trabalhadoreducando = trabalhadoreducando

    class Meta:
        model = SolicitacaoVisitaTecnicaUnidade
        fields = ('unidade', 'visitante', 'data', 'observacao', 'opcoes')


class RejeitarSolicitacaoUsuarioForm(forms.FormPlus):
    SUBMIT_LABEL = 'Rejeitar Solicitação do Usuário'
    razao_indeferimento = forms.CharField(widget=forms.Textarea(), required=True, label='Razão do Indeferimento')
    fieldsets = (('', {'fields': ('razao_indeferimento',)}),)


class SolicitacaoDesligamentosForm(forms.ModelFormPlus):
    def __init__(self, trabalhadoreducando, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.trabalhadoreducando = trabalhadoreducando
        self.fields['data'] = forms.DateFieldPlus()

    class Meta:
        model = SolicitacaoDesligamentos
        fields = ('motivo', 'data')


class RelatorioPpeForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    SITUACAO_SISTEMA_TODOS = 'TODOS'
    SITUACAO_SISTEMA_SUAP = 'SUAP'
    SITUACAO_SISTEMA_MIGRADOS = 'MIGRADOS'
    SITUACAO_SISTEMA_NAO_MIGRADOS = 'NAO_MIGRADOS'
    # SITUACAO_SISTEMA_CHOICES = [
    #     [SITUACAO_SISTEMA_TODOS, 'Todos'],
    #     [SITUACAO_SISTEMA_SUAP, 'Alunos que iniciaram no SUAP'],
    #     [SITUACAO_SISTEMA_MIGRADOS, 'Alunos migrados do Q-Acadêmico'],
    #     [SITUACAO_SISTEMA_NAO_MIGRADOS, 'Alunos NÃO migrados do Q-Acadêmico'],
    # ]
    #nome
    #data_admissao
    #data_demissao
    unidade_lotacao = forms.ModelChoiceFieldPlus(Unidade.objects.all(), label='Unidade Lotação', required=False) #, widget=AutocompleteWidget(search_fields=UnidadeLotacao.SEARCH_FIELDS))
    municipio = forms.ModelChoiceFieldPlus(Municipio.objects.all(), label='Municipio', required=False) #, widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS))
    #territorio_identidade
    tutor = forms.ModelChoiceFieldPlus(Bolsista.objects.filter(user__groups__name='Tutor PPE'), label='Tutor', required=False)#, widget=AutocompleteWidget(search_fields=TutorTurma.SEARCH_FIELDS))
    supervisor = forms.ModelChoiceFieldPlus(Servidor.objects.filter(user__groups__name='Supervisor(a) Pedagógico PPE'), label='Supervisor(a) Pedagógico', required=False)#, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))
    apoiador_pedagogico = forms.ModelChoiceFieldPlus(Servidor.objects.filter(user__groups__name='Apoiador(a) Pedagógico PPE'), label='Apoiador(a) Pedagógico', required=False)#, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))
    curso = forms.ModelChoiceFieldPlus(Curso.objects, label='Curso', required=False)#, widget=AutocompleteWidget(search_fields=MatriculaCursoTurma.SEARCH_FIELDS))
    formacao = forms.ModelChoiceFieldPlus(FormacaoPPE.objects, label='Formação PPE', required=False)#, widget=AutocompleteWidget(search_fields=FormacaoPPE.SEARCH_FIELDS))
    situacao_matricula = forms.ModelMultiplePopupChoiceField(SituacaoMatricula.objects, label='Situação',
                                                             required=False)
    #formatacao
    formatacao = forms.ChoiceField(
        choices=[
            ['simples', 'Listagem Simples'],
        ],
        label='Tipo',
        help_text='O tipo de formatação "Listagem Simples" permitirá a impressão de etiquetas, carômetros e assinatura dos alunos.',
    )
    quantidade_itens = forms.ChoiceField(choices=[[25, '25'], [50, '50'], [100, '100'], [200, '200'], [500, '500']], label='Quantidade de Itens')
    ordenacao = forms.ChoiceField(choices=[['Nome', 'Nome'], ['Matrícula', 'Matrícula']], label='Ordenação')
    agrupamento = forms.ChoiceField(choices=[['Município', 'Município'], ['Curso', 'Curso'], ['Formação Técnica', 'Formação Técnica']], label='Agrupamento')
    EXIBICAO_CHOICES = [
        ['curso.descricao', 'Descrição do Curso'],
        ['municipio', 'Município'],
        ['tutor', 'Tutor'],
        ['supervisor', 'Supervisor'],
        ['apoiador_pedagogico', 'Apoiador Pedagógico'],
        ['formacao', 'Formação PPE'],
        ['curso', 'Curso'],
        ['situacao_matricula', 'Situação'],

    ]

    EXIBICAO_COMUNICACAO = [['pessoa_fisica.email_secundario', 'Email Pessoal']]

    EXIBICAO_DADOS_PESSOAIS = [
        ['pessoa_fisica.cpf', 'CPF'],
        ['pessoa_fisica.nascimento_data', 'Data de Nascimento'],
        ['logradouro', 'Logradouro'],
        ['cidade', 'Município de Residência'],
        ['numero_rg', 'RG'],
        ['telefone_principal', 'Telefone Principal'],
        ['pessoa_fisica.sexo', 'Sexo'],
        ['estado_civil', 'Estado Civil'],
        ['nome_pai', 'Nome do Pai'],
        ['nome_mae', 'Nome da Mãe'],
        ['responsavel', 'Responsável'],
        ['naturalidade', 'Naturalidade'],
        ['naturalidade.codigo', 'Naturalidade (Código IBGE)'],

        ['observacao_historico', 'Observação Histórico'],
        ['cidade.nome', 'Cidade'],

        ['cidade.estado.get_sigla', 'Estado'],
        ['get_observacoes', 'Observações'],
        ['zona_residencial', 'Zona Residencial'],
    ]

    EXIBICAO_INICIAS = [
        ['tutor', 'Tutor'],
        ['curso', 'Curso'],
    ]

    exibicao = forms.MultipleChoiceField(label="Campos Adicionais", choices=[], widget=CheckboxSelectMultiplePlus(), required=False)

    fieldsets = (
        (
            'Filtros de Pesquisa',
            {
                'fields': (
                   # ('unidade_lotacao', 'municipio'),
                    ('tutor', 'supervisor'),
                    ('apoiador_pedagogico', 'curso'),
                    ('formacao','municipio'),
                )
            },
        ),
        ('Formatação', {'fields': ('formatacao', ('quantidade_itens', 'ordenacao', 'agrupamento'))}),
        ('Exibição', {'fields': (('exibicao',),)}),
    )

    class Media:
        js = ('/static/edu/js/RelatorioForm.js',)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        exibicao_final_choices = []
        exibicao_final_choices.extend(self.EXIBICAO_CHOICES)
        if request.user.has_perm('ppe.view_dados_pessoais'):
            exibicao_final_choices.extend(self.EXIBICAO_DADOS_PESSOAIS)

        if in_group(
            request.user,
            'Supervisor(a) Pedagógico', 'Coordenador(a) Pedagógico',
        ):
            exibicao_final_choices.extend(self.EXIBICAO_COMUNICACAO)

        self.fields['exibicao'].choices = sorted(exibicao_final_choices, key=itemgetter(1))
        self.fields['exibicao'].initial = [campo[0] for campo in self.EXIBICAO_INICIAS]

        self.fields['curso'].queryset = self.fields['curso'].queryset.all()

        formatacao_choices = []
        for choice in self.fields['formatacao'].choices:
            _, valor = choice
            if 'Resumo' in valor:
                if request.user.is_superuser or in_group(request.user, 'Administrador Acadêmico'):
                    formatacao_choices.append(choice)
            else:
                formatacao_choices.append(choice)
        self.fields['formatacao'].choices = formatacao_choices

    def processar(self):
        qs = MatriculaCursoTurma.objects.all()

        unidade_lotacao = self.cleaned_data['unidade_lotacao']
        municipio = self.cleaned_data['municipio']
        tutor = self.cleaned_data['tutor']
        supervisor = self.cleaned_data['supervisor']
        apoiador_pedagogico = self.cleaned_data['apoiador_pedagogico']
        curso = self.cleaned_data['curso']
        formacao = self.cleaned_data['formacao']
        situacao_matricula = self.cleaned_data['situacao_matricula']

        filtros = []

        # if unidade_lotacao:
        #     qs = qs.filter(trabalhador_educando__unidade_lotacao=unidade_lotacao)
        #     filtros.append(dict(chave='Unidade Lotação', valor=format_iterable(unidade_lotacao)))
        if municipio:
            qs = qs.filter(trabalhador_educando__cidade=municipio)
            filtros.append(dict(chave='Município', valor=str(municipio)))
        if tutor:
            qs = qs.filter(trabalhador_educando__turma__tutorturma__tutor=tutor)
            filtros.append(dict(chave='Tutor', valor=str(tutor)))
        if situacao_matricula:
            qs = qs.filter(trabalhador_educando__situacao=situacao_matricula)
            filtros.append(dict(chave='Situação', valor=str(situacao_matricula)))

        # if supervisor:
        #     qs = qs.filter(aluno__curso_campus__modalidade__id__in=modalidade)
        #     filtros.append(dict(chave='Supervisor(a)', valor=format_iterable(supervisor)))
        # if apoiador_pedagogico:
        #     qs = qs.filter(aluno__convenio__id__in=convenio)
        #     filtros.append(dict(chave='Apoiador(a) Pedagógico', valor=format_iterable(apoiador_pedagogico)))
        if curso:
            #qs = qs.filter(trabalhador_educando__turma__formacao__cursoformacao__curso__in=curso)
            qs = qs.filter(curso_turma__curso_formacao__curso=curso)
            filtros.append(dict(chave='Curso', valor=str(curso)))
        if formacao:
            qs = qs.filter(trabalhador_educando__formacao=formacao)
            filtros.append(dict(chave='Formação Técnica', valor=str(formacao)))

        # open('/tmp/query.txt', 'w').write(str(qs.query))
        trabalhadores_educando = TrabalhadorEducando.objects.filter(id__in=qs.order_by('trabalhador_educando__id').values_list('trabalhador_educando__id', flat=True).distinct())

        ordenacao = ['curso', ]
        if self.cleaned_data.get('ordenacao') == 'Matrícula':
            ordenacao.append('matricula')
        if self.cleaned_data.get('ordenacao') == 'Nome':
            ordenacao.append('pessoa_fisica__nome')

        #trabalhadores_educando = trabalhadores_educando.order_by(*ordenacao).select_related('pessoa_fisica')

        trabalhadores_educando.filtros = filtros
        return trabalhadores_educando

class SalvarRelatorioPpeForm(forms.Form):
    descricao = forms.CharFieldPlus(label='Descrição')

    def __init__(self, *args, **kwargs):
        self.tipo = kwargs.pop('tipo')
        super().__init__(*args, **kwargs)

    def processar(self, query_string):
        h = HistoricoRelatorioPpe()
        h.descricao = self.cleaned_data['descricao']
        h.query_string = query_string
        h.tipo = self.tipo
        h.save()
        return h



class AulaForm(forms.ModelFormPlus):
    tutor_turma = forms.ModelChoiceField(queryset=TutorTurma.objects, label='Tutor', required=True)
    conteudo = forms.CharField(label='Conteúdo', widget=TextareaCloneWidget())
    url = forms.CharField(label='URL', required=False, help_text='Link disponbilizado na turma virtual para os alunos caso a transmissão seja realizada através de alguma plataforma multi-media ou streaming')
    # outros_tutor_turma = forms.MultipleModelChoiceField(TutorTurma.objects, label='Outros Tutores', required=False, help_text="A CH desta aula será compartilhada com os tutores selecionados")

    class Meta:
        model = Aula
        exclude = ()

    fieldsets = (('Dados da Aula', {'fields': ('tutor_turma', ('quantidade', 'tipo'), ('etapa', 'data'), 'conteudo',  'url', )}),)

    def __init__(self, curso_turma, etapa, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.curso_turma = curso_turma
        self.etapa = etapa

        tutor_turma_qs = self.curso_turma.turma.tutorturma_set.filter(tutor__vinculo__user=self.request.user)
        tutor_turma = None
        if tutor_turma_qs.exists():
            tutor_turma = tutor_turma_qs[0]
            self.fields['tutor_turma'].queryset = tutor_turma_qs
        else:
            qs = self.curso_turma.turma.tutorturma_set.all()
            self.fields['tutor_turma'].queryset = qs
            if qs.count() == 1:
                tutor_turma = qs[0]

        if self.fields['tutor_turma'].queryset.count() == 1:
            self.fields['tutor_turma'].widget = forms.HiddenInput()
        else:
            self.fields['tutor_turma'].label_from_instance = lambda obj: f'{obj.tutor}'

        self.fields['etapa'].choices = Aula.ETAPA_CHOICES[0:1]
        if not self.instance.data:
            self.fields['data'].initial = datetime.date.today()
        if not self.instance.pk:
            self.fields['etapa'].initial = etapa

        if tutor_turma:
            self.fields['tutor_turma'].initial = tutor_turma.pk
            lista = []
            # for curso_turma in CursoTurma.objects.filter(
            #     turma__tutorturma__set__in=tutor_turma.tutor, curso_formacao=self.curso_turma.curso_formacao
            # ).order_by('-id')[0:3]:
            self.curso_turma.turma.tutorturma_set.all()
            qs = Aula.objects.filter(curso_turma=curso_turma)
            if qs.exists():
                lista.append(f'<strong>{curso_turma}</strong>')
            for aula in qs:
                lista.append('<div><strong>{}</strong> <p>{}</p></div>'.format(format_(aula.data), aula.conteudo.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')))

            if not lista:
                lista.append('<strong>Atenção</strong>: Nenhum registro de aula relacionado a esta disciplina foi encontrado.')
            self.fields['conteudo'].widget.clones = ''.join(lista)

        # if curso_turma.componente_curricular.matriz.estrutura.limitar_ch_por_tipo_aula:
        #     tipo_choices = [[Aula.AULA, 'Aula Teórica']]
        #     if curso_turma.componente_curricular.ch_pratica:
        #         tipo_choices.append([Aula.PRATICA, 'Aula Prática'])
        #     if curso_turma.componente_curricular.ch_extensao:
        #         tipo_choices.append([Aula.EXTENSAO, 'Atividade de Extensão'])
        #     if curso_turma.componente_curricular.ch_pcc:
        #         tipo_choices.append([Aula.PRATICA_COMO_COMPONENTE_CURRICULAR, 'Prática como Componente Curricular'])
        #     if curso_turma.componente_curricular.ch_visita_tecnica:
        #         tipo_choices.append([Aula.VISITA_TECNICA, 'Visita Técnica / Aula de Campo'])
        #     self.fields['tipo'].choices = tipo_choices
        # else:
        #     self.fields['tipo'].widget = forms.HiddenInput()
        #     self.fields['tipo'].initial = Aula.AULA

        # if curso_turma.componente_curricular.percentual_maximo_ead == 0:
        #     self.fields['ead'].widget = forms.HiddenInput()

    # def clean_ead(self):
    #     ead = self.cleaned_data.get('ead')
    #     quantidade = self.cleaned_data.get('quantidade')
    #     if self.curso_turma.componente_curricular.percentual_maximo_ead:
    #         qtd_disponivel = self.curso_turma.get_carga_horaria_ead_disponivel()
    #         if quantidade > qtd_disponivel:
    #             raise forms.ValidationError(f'A quantidade disponível de aula EAD para esse diário é de {qtd_disponivel} aula(s).')
    #     return ead

    def clean_data(self):
        data = self.cleaned_data['data']
        tutor_turma = self.cleaned_data.get('tutor_turma')
        if not tutor_turma:
            return data
        # if (
        #     tutor_turma.curso_turma.calendario_academico.data_inicio_espaco_pedagogico
        #     and tutor_turma.curso_turma.calendario_academico.data_fim_espaco_pedagogico
        #     and data >= tutor_turma.curso_turma.calendario_academico.data_inicio_espaco_pedagogico
        #     and data <= tutor_turma.curso_turma.calendario_academico.data_fim_espaco_pedagogico
        # ):
        #     return data
        # if (
        #     tutor_turma.curso_turma.calendario_academico.data_inicio_etapa_1
        #     and tutor_turma.curso_turma.calendario_academico.data_fim_etapa_1
        #     and data >= tutor_turma.curso_turma.calendario_academico.data_inicio_etapa_1
        #     and data <= tutor_turma.curso_turma.calendario_academico.data_fim_etapa_1
        # ):
        #     return data
        # if (
        #     tutor_turma.curso_turma.calendario_academico.data_inicio_etapa_2
        #     and tutor_turma.curso_turma.calendario_academico.data_fim_etapa_2
        #     and data >= tutor_turma.curso_turma.calendario_academico.data_inicio_etapa_2
        #     and data <= tutor_turma.curso_turma.calendario_academico.data_fim_etapa_2
        # ):
        #     return data
        # if (
        #     tutor_turma.curso_turma.calendario_academico.data_inicio_etapa_3
        #     and tutor_turma.curso_turma.calendario_academico.data_fim_etapa_3
        #     and data >= tutor_turma.curso_turma.calendario_academico.data_inicio_etapa_3
        #     and data <= tutor_turma.curso_turma.calendario_academico.data_fim_etapa_3
        # ):
        #     return data
        # if (
        #     tutor_turma.curso_turma.calendario_academico.data_inicio_etapa_4
        #     and tutor_turma.curso_turma.calendario_academico.data_fim_etapa_4
        #     and data >= tutor_turma.curso_turma.calendario_academico.data_inicio_etapa_4
        #     and data <= tutor_turma.curso_turma.calendario_academico.data_fim_etapa_4
        # ):
        #     return data
        # if (
        #     tutor_turma.curso_turma.get_inicio_etapa_final()
        #     and tutor_turma.curso_turma.get_fim_etapa_final()
        #     and data >= tutor_turma.curso_turma.get_inicio_etapa_final()
        #     and data <= tutor_turma.curso_turma.get_fim_etapa_final()
        # ):
        #     return data
        # if tutor_turma.curso_turma.componente_curricular.qtd_avaliacoes == 1 and tutor_turma.curso_turma.calendario_academico.qtd_etapas == 2:
        #     return data
        # raise forms.ValidationError('A data não compreende o intervalo do calendário acadêmico.')
    #
    # def clean_outros_tutor_turma(self):
    #     outros_tutor_turma = self.cleaned_data['outros_tutor_turma']
    #     tutor_turma = self.cleaned_data.get('tutor_turma')
    #     if tutor_turma in outros_tutor_turma:
    #         raise forms.ValidationError(f'O professor {tutor_turma.professor} é o responsável pela aula e não pode ser selecionado para receber o compartilhamento da CH dessa aula.')
    #     return outros_tutor_turma


class RelatorioFaltasForm(forms.FormPlus):
    SUBMIT_LABEL = 'Visualizar'
    METHOD = 'GET'


    turma = forms.ModelChoiceFieldPlus(
        Turma.objects.none(), widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS, form_filters=[('uo', 'curso_campus__diretoria__setor__uo__in')]), required=False
    )

    curso_turma = forms.ModelChoiceFieldPlus(
        CursoTurma.objects.none(),
        label='Curso',
        help_text='Para encontrar um curso entre com a sigla do componente ou o código do diário.',
        required=False,
    )
    trabalhador_educando = forms.ModelChoiceFieldPlus(TrabalhadorEducando.objects, required=False)

    intervalo_inicio = forms.DateFieldPlus(label='Início do Intervalo', required=False)
    intervalo_fim = forms.DateFieldPlus(label='Fim do Intervalo', required=False)

    situacoes_inativas = forms.BooleanField(
        label='Desconsiderar Situações Inativas',
        required=False,
        help_text='Exclui do relatório aulas e faltas de alunos que estão com situação Cancelado, Dispensado, Trancado ou Transferido no diário.',
        initial=True,
    )
    fieldsets = (
        ('Período', {'fields': (('intervalo_inicio', 'intervalo_fim'))}),
        ('Filtros de Pesquisa', {'fields': ('turma', 'curso_turma')}),
        ('Filtros Adicionais', {'fields': ('trabalhador_educando', ('situacoes_inativas'))}))
    def __init__(self, campus, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso_turma'].queryset = CursoTurma.objects.all()
        self.fields['turma'].queryset = Turma.objects.all()
    def clean(self):
        if (
            not self.cleaned_data.get('turma')
            and not self.cleaned_data.get('curso_turma')
            and not self.cleaned_data.get('trabalhador_educando')
        ):
            raise forms.ValidationError('Insira ao menos  curso, turma, trabalhador educando nos filtros.')

        return self.cleaned_data

    def clean_intervalo_fim(self):
        if not self.cleaned_data.get('intervalo_inicio') and self.cleaned_data.get('intervalo_fim'):
            raise forms.ValidationError('Insira uma data válida no início do intervalo.')
        else:
            return self.cleaned_data['intervalo_fim']

class MapaTurmaPpeForm(forms.Form):
    diarios = forms.MultipleModelChoiceField(CursoTurma.objects, label='', widget=RenderableSelectMultiple('widgets/diarios_widget.html'))

    def __init__(self, diarios, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diarios'].queryset = diarios.order_by('id')


class RelatorioAprovadosPpeForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    SITUACAO_SISTEMA_TODOS = 'TODOS'
    SITUACAO_SISTEMA_SUAP = 'SUAP'
    SITUACAO_SISTEMA_MIGRADOS = 'MIGRADOS'
    SITUACAO_SISTEMA_NAO_MIGRADOS = 'NAO_MIGRADOS'
    # SITUACAO_SISTEMA_CHOICES = [
    #     [SITUACAO_SISTEMA_TODOS, 'Todos'],
    #     [SITUACAO_SISTEMA_SUAP, 'Alunos que iniciaram no SUAP'],
    #     [SITUACAO_SISTEMA_MIGRADOS, 'Alunos migrados do Q-Acadêmico'],
    #     [SITUACAO_SISTEMA_NAO_MIGRADOS, 'Alunos NÃO migrados do Q-Acadêmico'],
    # ]
    SITUACAO_CURSANDO = 1
    SITUACAO_APROVADO = 2
    SITUACAO_REPROVADO = 3
    SITUACAO_PROVA_FINAL = 4
    SITUACAO_REPROVADO_POR_FALTA = 5
    SITUACAO_TRANCADO = 6
    SITUACAO_CANCELADO = 7
    SITUACAO_DISPENSADO = 8
    SITUACAO_PENDENTE = 9

    SITUACAO_CHOICES = [
        [SITUACAO_CURSANDO, 'Cursando'],
        [SITUACAO_APROVADO, 'Aprovado'],
        [SITUACAO_REPROVADO, 'Reprovado'],
        [SITUACAO_PROVA_FINAL, 'Prova Final'],
        [SITUACAO_REPROVADO_POR_FALTA, 'Reprovado por falta'],
        [SITUACAO_TRANCADO, 'Trancado'],
        [SITUACAO_CANCELADO, 'Cancelado'],
        [SITUACAO_DISPENSADO, 'Dispensado'],
        [SITUACAO_PENDENTE, 'Pendente'],
    ]
    #nome
    #data_admissao
    #data_demissao
    unidade_lotacao = forms.ModelChoiceFieldPlus(Unidade.objects.all(), label='Unidade Lotação', required=False) #, widget=AutocompleteWidget(search_fields=UnidadeLotacao.SEARCH_FIELDS))
    municipio = forms.ModelChoiceFieldPlus(Municipio.objects.all(), label='Municipio', required=False) #, widget=AutocompleteWidget(search_fields=Municipio.SEARCH_FIELDS))
    #territorio_identidade
    tutor = forms.ModelChoiceFieldPlus(Bolsista.objects.filter(user__groups__name='Tutor PPE'), label='Tutor', required=False)#, widget=AutocompleteWidget(search_fields=TutorTurma.SEARCH_FIELDS))
    supervisor = forms.ModelChoiceFieldPlus(Bolsista.objects.filter(user__groups__name='Supervisor(a) Pedagógico PPE'), label='Supervisor(a) Pedagógico', required=False)#, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))
    apoiador_pedagogico = forms.ModelChoiceFieldPlus(Bolsista.objects.filter(user__groups__name='Apoiador(a) Pedagógico PPE'), label='Apoiador(a) Pedagógico', required=False)#, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))
    curso = forms.ModelChoiceFieldPlus(Curso.objects, label='Curso', required=False)#, widget=AutocompleteWidget(search_fields=MatriculaCursoTurma.SEARCH_FIELDS))
    formacao = forms.ModelChoiceFieldPlus(FormacaoPPE.objects, label='Formação PPE', required=False)#, widget=AutocompleteWidget(search_fields=FormacaoPPE.SEARCH_FIELDS))
    situacao = forms.ChoiceField(
        choices = [
            [SITUACAO_CURSANDO, 'Cursando'],
            [SITUACAO_APROVADO, 'Aprovado'],
            [SITUACAO_REPROVADO, 'Reprovado'],
            [SITUACAO_PROVA_FINAL, 'Prova Final'],
            [SITUACAO_REPROVADO_POR_FALTA, 'Reprovado por falta'],
            [SITUACAO_TRANCADO, 'Trancado'],
            [SITUACAO_CANCELADO, 'Cancelado'],
            [SITUACAO_DISPENSADO, 'Dispensado'],
            [SITUACAO_PENDENTE, 'Pendente'],
        ],
        label='Situação (Aprovado, Reprovado, etc)',
        initial=SITUACAO_APROVADO,
    )

    #formatacao
    formatacao = forms.ChoiceField(
        choices=[
            ['simples', 'Listagem Simples'],
        ],
        label='Tipo',
        help_text='O tipo de formatação "Listagem Simples" permitirá a impressão de etiquetas, carômetros e assinatura dos alunos.',
    )
    quantidade_itens = forms.ChoiceField(choices=[[25, '25'], [50, '50'], [100, '100'], [200, '200'], [500, '500']], label='Quantidade de Itens')
    ordenacao = forms.ChoiceField(choices=[['Nome', 'Nome'], ['Matrícula', 'Matrícula']], label='Ordenação')
    agrupamento = forms.ChoiceField(choices=[['Município', 'Município'], ['Curso', 'Curso'], ['Formação Técnica', 'Formação Técnica']], label='Agrupamento')
    EXIBICAO_CHOICES = [
        ['curso.descricao', 'Descrição do Curso'],
        ['municipio', 'Município'],
        ['tutor', 'Tutor'],
        ['supervisor', 'Supervisor'],
        ['apoiador_pedagogico', 'Apoiador Pedagógico'],
        ['formacao', 'Formação PPE'],
        ['curso', 'Curso'],
        ['situacao', 'Situação']
    ]

    EXIBICAO_COMUNICACAO = [['pessoa_fisica.email_secundario', 'Email Pessoal']]

    EXIBICAO_DADOS_PESSOAIS = [
        ['pessoa_fisica.cpf', 'CPF'],
        ['pessoa_fisica.nascimento_data', 'Data de Nascimento'],
        ['logradouro', 'Logradouro'],
        ['cidade', 'Município de Residência'],
        ['numero_rg', 'RG'],
        ['telefone_principal', 'Telefone Principal'],
        ['pessoa_fisica.sexo', 'Sexo'],
        ['estado_civil', 'Estado Civil'],
        ['nome_pai', 'Nome do Pai'],
        ['nome_mae', 'Nome da Mãe'],
        ['responsavel', 'Responsável'],
        ['naturalidade', 'Naturalidade'],
        ['naturalidade.codigo', 'Naturalidade (Código IBGE)'],
        ['observacao_historico', 'Observação Histórico'],
        ['cidade.nome', 'Cidade'],
        ['cidade.estado.get_sigla', 'Estado'],
        ['get_observacoes', 'Observações'],
        ['zona_residencial', 'Zona Residencial'],
    ]

    EXIBICAO_INICIAS = [
        ['tutor', 'Tutor'],
        ['curso', 'Curso'],
        ['situacao', 'Situação']
    ]

    exibicao = forms.MultipleChoiceField(label="Campos Adicionais", choices=[], widget=CheckboxSelectMultiplePlus(), required=False)

    fieldsets = (
        (
            'Filtros de Pesquisa',
            {
                'fields': (
                   # ('unidade_lotacao', 'municipio'),
                    ('tutor', 'supervisor'),
                    ('apoiador_pedagogico', 'curso'),
                    ('formacao','municipio'),
                    ('situacao'),
                )
            },
        ),
        ('Formatação', {'fields': ('formatacao', ('quantidade_itens', 'ordenacao', 'agrupamento'))}),
        ('Exibição', {'fields': (('exibicao',),)}),
    )

    class Media:
        js = ('/static/edu/js/RelatorioForm.js',)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        exibicao_final_choices = []
        exibicao_final_choices.extend(self.EXIBICAO_CHOICES)
        if request.user.has_perm('ppe.view_dados_pessoais'):
            exibicao_final_choices.extend(self.EXIBICAO_DADOS_PESSOAIS)

        if in_group(
            request.user,
            'Supervisor(a) Pedagógico', 'Coordenador(a) Pedagógico',
        ):
            exibicao_final_choices.extend(self.EXIBICAO_COMUNICACAO)

        self.fields['exibicao'].choices = sorted(exibicao_final_choices, key=itemgetter(1))
        self.fields['exibicao'].initial = [campo[0] for campo in self.EXIBICAO_INICIAS]

        self.fields['curso'].queryset = self.fields['curso'].queryset.all()

        formatacao_choices = []
        for choice in self.fields['formatacao'].choices:
            _, valor = choice
            if 'Resumo' in valor:
                if request.user.is_superuser or in_group(request.user, 'Administrador Acadêmico'):
                    formatacao_choices.append(choice)
            else:
                formatacao_choices.append(choice)
        self.fields['formatacao'].choices = formatacao_choices

    def processar(self):
        qs = MatriculaCursoTurma.objects.all()

        unidade_lotacao = self.cleaned_data['unidade_lotacao']
        municipio = self.cleaned_data['municipio']
        tutor = self.cleaned_data['tutor']
        supervisor = self.cleaned_data['supervisor']
        apoiador_pedagogico = self.cleaned_data['apoiador_pedagogico']
        curso = self.cleaned_data['curso']
        formacao = self.cleaned_data['formacao']
        situacao = self.cleaned_data['situacao']

        filtros = []

        if municipio:
            qs = qs.filter(trabalhador_educando__cidade=municipio)
            filtros.append(dict(chave='Município', valor=str(municipio)))
        if tutor:
            qs = qs.filter(trabalhador_educando__turma__tutorturma__tutor=tutor)
            filtros.append(dict(chave='Tutor', valor=str(tutor)))        
        if curso:
            qs = qs.filter(curso_turma__curso_formacao__curso=curso)
            filtros.append(dict(chave='curso', valor=str(curso)))
        if formacao:
            qs = qs.filter(trabalhador_educando__formacao=formacao)
            filtros.append(dict(chave='Formação Técnica', valor=str(formacao)))
        if apoiador_pedagogico:
            qs = qs.filter(trabalhador_educando__turma__apoiadorturma__apoiador=apoiador_pedagogico)
            filtros.append(dict(chave='Apoiador(a) Pedagógico', valor=str(municipio)))
        # if supervisor:
        #     qs = qs.filter(aluno__curso_campus__modalidade__id__in=modalidade)
        #     filtros.append(dict(chave='Supervisor(a)', valor=format_iterable(supervisor)))
        
        # if unidade_lotacao:
        #     qs = qs.filter(trabalhador_educando__unidade_lotacao=unidade_lotacao)
        #     filtros.append(dict(chave='Unidade Lotação', valor=format_iterable(unidade_lotacao)))

        # open('/tmp/query.txt', 'w').write(str(qs.query))
        qs = qs.filter(situacao = situacao)
        filtros.append(dict(chave='Aprovado', valor=str(situacao)))
        trabalhadores_educando = TrabalhadorEducando.objects.filter(id__in=qs.order_by('trabalhador_educando__id').values_list('trabalhador_educando__id', flat=True).distinct())

        ordenacao = ['curso', ]
        if self.cleaned_data.get('ordenacao') == 'Matrícula':
            ordenacao.append('matricula')
        if self.cleaned_data.get('ordenacao') == 'Nome':
            ordenacao.append('pessoa_fisica__nome')

        #trabalhadores_educando = trabalhadores_educando.order_by(*ordenacao).select_related('pessoa_fisica')

        trabalhadores_educando.filtros = filtros
        return trabalhadores_educando

class PerguntaAvaliacaoForm(forms.FormPlus):
    # justificativa = forms.CharField(label='Avaliação', widget=forms.Textarea, required=True)

    class Media:
        css = {'all': ("/static/ppe/css/pergunta_avaliacao.css",)}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.tipo_avaliacao = kwargs.pop('tipo_avaliacao', None)
        self.avaliacao = kwargs.pop('avaliacao', None)
        self.formacao_tecnica = kwargs.pop('formacao_tecnica', None),
        super().__init__(*args, **kwargs)
        for i in PerguntaAvaliacao.objects.filter(ativo=True, tipo_avaliacao=self.tipo_avaliacao, formacao_tecnica= self.formacao_tecnica[0] ):
            label = '{}'.format(i.pergunta)
            if i.tipo_resposta == PerguntaAvaliacao.TEXTO:
                self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label=label, widget=forms.Textarea, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaAvaliacao.TEXTO_AVALIACAO:
                if self.avaliacao.papel_avalidor == Avaliacao.AUTOAVALIACAO:
                    self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label="AUTOAVALIAÇÃO", widget=forms.Textarea, required=i.obrigatoria, help_text='COMENTÁRIOS SOBRE A ATUAÇÃO PROFISSIONAL (SUGESTÕES DE MELHORIAS, CRÍTICAS E DÚVIDAS)')
                if self.avaliacao.papel_avalidor == Avaliacao.AVALIACAO_CHEFIA:
                    self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label="AVALIAÇÃO DA CHEFIA", widget=forms.Textarea, required=i.obrigatoria, help_text='COMENTÁRIOS SOBRE A ATUAÇÃO PROFISSIONAL (SUGESTÕES DE MELHORIAS, CRÍTICAS E DÚVIDAS)')

            if i.tipo_resposta == PerguntaAvaliacao.PARAGRAFO:
                self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label=label, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaAvaliacao.NUMERO:
                self.fields["texto_{}".format(i.id)] = forms.DecimalFieldPlus(label=label, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaAvaliacao.SIM_NAO:
                self.fields["texto_{}".format(i.id)] = forms.ChoiceField(label=label, required=i.obrigatoria, choices=[('Sim', 'Sim'), ('Não', 'Não')])

            if i.tipo_resposta == PerguntaAvaliacao.SIM_NAO_NA:
                self.fields["texto_{}".format(i.id)] = forms.ChoiceField(label=label, required=i.obrigatoria, choices=[('Sim', 'Sim'), ('Não', 'Não'), ('NA', 'NA')])

            if i.tipo_resposta == PerguntaAvaliacao.ESCALA_0_5_COMPETENCIA:
                self.fields["texto_{}".format(i.id)] = forms.ChoiceField(label=label, required=i.obrigatoria, choices=[('0', '0'),('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),], help_text='CONSIDERANDO (0) NENHUMA COMPETÊNCIA E (5) TOTAL COMPETÊNCIA')

            if i.tipo_resposta == PerguntaAvaliacao.ESCALA_0_5:
                self.fields["texto_{}".format(i.id)] = forms.ChoiceField(label=label, required=i.obrigatoria, choices=[('0', '0'),('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),], help_text='CONSIDERANDO (0) NUNCA E (5) SEMPRE')

            if i.tipo_resposta == PerguntaAvaliacao.UNICA_ESCOLHA:
                self.fields["pergunta_{}".format(i.id)] = forms.ModelPopupAvaliacaoChoiceField(queryset=i.pergunta_avaliacao, label=label)
                # self.fields["pergunta_{}".format(i.id)] = forms.ModelChoiceField(queryset=i.pergunta_avaliacao, label=label, required=i.obrigatoria)

            elif i.tipo_resposta == PerguntaAvaliacao.MULTIPLA_ESCOLHA:
                self.fields["pergunta_{}".format(i.id)] = forms.MultipleModelChoiceField(queryset=i.pergunta_avaliacao, label=label, required=i.obrigatoria)

            if self.avaliacao:
                if RespostaAvaliacao.objects.filter(pergunta=i, avaliacao=self.avaliacao).exists():
                    resposta_anterior = RespostaAvaliacao.objects.filter(pergunta=i, avaliacao=self.avaliacao)
                    if resposta_anterior.exists():
                        resposta_atual = resposta_anterior[0]
                        if resposta_atual.resposta and not resposta_atual.eh_multipla_escolha():
                            self.initial["pergunta_{}".format(i.id)] = resposta_atual.resposta.id
                        elif resposta_atual.resposta:
                            ids_multipla_escolha = list()
                            for resposta in resposta_anterior:
                                ids_multipla_escolha.append(resposta.resposta.id)
                            self.initial["pergunta_{}".format(i.id)] = ids_multipla_escolha
                        else:
                            self.initial["texto_{}".format(i.id)] = resposta_atual.valor_informado



class OpcaoRespostaAvaliacaoForm(forms.ModelFormPlus):
    pergunta = forms.ModelChoiceField(
        queryset=PerguntaAvaliacao.objects.filter(ativo=True, tipo_resposta__in=[PerguntaAvaliacao.UNICA_ESCOLHA, PerguntaAvaliacao.MULTIPLA_ESCOLHA]), label='Pergunta'
    )

    class Meta:
        model = OpcaoRespostaAvaliacao
        fields = ('pergunta', 'valor','pontuacao', 'ativo')


class TipoAvaliacaoForm(forms.ModelFormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', widget=forms.Textarea())

    class Meta:
        models = TipoAvaliacao
        fields = ('titulo', 'descricao', 'pre_requisito', 'ativo')


class EtapaMonitoramentoForm(forms.ModelFormPlus):
    data_inicio = forms.DateFieldPlus(label='Data de início', required=True)
    class Meta:
        model = EtapaMonitoramento
        fields = ('tipo_avaliacao', 'data_inicio')


class SetorForm(forms.ModelFormPlus):
    superior = forms.ModelChoiceField(label="Setor Superior", queryset=Setor.objects.all(), widget=TreeWidget(), required=False)

    class Meta:
        model = Setor
        exclude = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fieldsets = [
            ("Dados Gerais", {"fields": ["superior", "sigla", "nome", "excluido"]}),
        ]

        if not self.request.user.is_superuser:
            del self.fieldsets[0][1]["fields"][0]

    def clean_superior(self):
        if self.cleaned_data["superior"] and self.instance.id == self.cleaned_data["superior"].id:
            raise forms.ValidationError("O setor superior não pode ser o próprio setor.")
        return self.cleaned_data["superior"]

class SetorAddForm(SetorForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data

    def _save_m2m(self):
        super()._save_m2m()


class AlterarTrabalhadorSetorHistoricoForm(forms.ModelFormPlus):
    class Meta:
        model = TrabalhadorSetorHistorico
        fields = ("trabalhador_educando", "setor", "data_inicio")

    # trabalhador_educando = forms.ModelChoiceField(
    #     label="Trabalhador educando", queryset=TrabalhadorEducando.objects.all(), required=True, widget=forms.HiddenInput())
    setor = forms.ModelChoiceField(label="Setor SUAP", queryset=Setor.objects.all(), widget=TreeWidget(), required=True)
    fieldsets = [("", {"fields": ["trabalhador_educando", "setor", "data_inicio",]})]

    def __init__(self, *args, **kwargs):
        self.instance = kwargs['instance']
        super().__init__(*args, **kwargs)
        self.fields["trabalhador_educando"].widget.readonly = True

    def save(self, *args, **kwargs):

        for setor_trabalhador in self.instance.trabalhador_educando.trabalhadorsetorhistorico_set.filter(data_fim__isnull=True):
            setor_trabalhador.data_fim=self.instance.data_inicio
            setor_trabalhador.save()

        return super().save(*args, **kwargs)
class TrabalhadorSetorHistoricoForm(forms.ModelFormPlus):
    class Meta:
        model = TrabalhadorSetorHistorico
        fields = ("trabalhador_educando", "setor", "data_inicio", "data_fim")

    trabalhador_educando = forms.ModelChoiceField(
        label="Trabalhador educando", queryset=TrabalhadorEducando.objects.all(), required=True, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS)
    )
    setor = forms.ModelChoiceField(label="Setor SUAP", queryset=Setor.objects.all(), widget=TreeWidget(), required=True)
    fieldsets = [("", {"fields": ["servidor", "setor", "data_inicio", "data_fim"]})]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["trabalhador_educando"].widget.readonly = True

    def clean(self):
        super().clean()
        if not self.errors:
            if not self.instance.pk:
                trabalhador_educando = self.cleaned_data["trabalhador_educando"]
                data_inicio = self.cleaned_data["data_inicio"]
                setor = self.cleaned_data["setor"]
                historico = TrabalhadorSetorHistorico.objects.filter(trabalhador_educando=trabalhador_educando).order_by("-data_inicio")
                if historico:
                    historico_atual = historico[0]
                    if setor != historico_atual.setor:
                        if data_inicio > historico_atual.data_inicio:
                            #
                            # atualizando a data fim do então período mais atual
                            dia_subtr = datetime.timedelta(days=1)
                            TrabalhadorSetorHistorico.objects.filter(pk=historico_atual.pk).update(
                                data_fim=(data_inicio - dia_subtr)
                            )

                            # raise forms.ValidationError(
                            #     u'Não é possível criar Histórico para periodos a frente do mais atual')
            else:
                trabalhador_educando = self.cleaned_data["trabalhador_educando"]
                trabalhador_educando_historico_atual = TrabalhadorSetorHistorico.objects.filter(trabalhador_educando=trabalhador_educando).order_by("-data_inicio")[0]
                if trabalhador_educando_historico_atual.pk == self.instance.pk:
                    if self.cleaned_data["data_fim"]:
                        raise forms.ValidationError("Não é possível fechar o este periodo. Ele é o mais atual")
        return self.cleaned_data



class ChefiaSetorHistoricoForm(forms.ModelFormPlus):
    chefe_imediato = ModelChoiceFieldPlus(
        ChefiaPPE.objects,
        label="Chefe Imediato", required=True,
    )
    setor = forms.ModelChoiceField(
        label="Setor", queryset=Setor.objects.filter(excluido=False), widget=TreeWidget(), required=True
    )
    nome_amigavel = forms.CharFieldPlus(label="Nome Amigável da Função", required=False)
    data_fim_funcao = forms.DateFieldPlus(
        label="Data Fim na Função", required=False, help_text="Deixar em branco caso essa seja a função atual do servidor."
    )

    class Meta:
        model = ChefiaSetorHistorico
        fields = ( "setor", "chefe_imediato", "data_inicio_funcao", "data_fim_funcao", "nome_amigavel", )


class AlterarNomeBreveCursoMoodleForm(forms.FormPlus):
    nome_breve_curso_moodle = forms.CharFieldPlus(label='Nome breve curso moodle ')
    def __init__(self, curso_turma, *args, **kwargs):
        self.curso_turma = curso_turma
        super(AlterarNomeBreveCursoMoodleForm, self).__init__(*args, **kwargs)
        self.initial['nome_breve_curso_moodle'] = curso_turma.nome_breve_curso_moodle

    def processar(self):
        self.curso_turma.nome_breve_curso_moodle = self.cleaned_data['nome_breve_curso_moodle']
        self.curso_turma.save()
