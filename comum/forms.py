# pylint: disable=undefined-variable
import datetime
import os
from collections import OrderedDict
import re

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.forms import FileField
from django.forms.fields import DateField, MultipleChoiceField
from django.forms.widgets import PasswordInput
from django.utils.formats import localize
from comum import signer
import tempfile

from comum.models import (
    AcabamentoExternoPredio,
    AcabamentoParedeSala,
    Ano,
    AreaAtuacao,
    ClimatizacaoSala,
    CoberturaPredio,
    Configuracao,
    ConfiguracaoImpressaoDocumento,
    DocumentoControle,
    DocumentoControleHistorico,
    DocumentoControleTipo,
    EsquadriasSala,
    EstruturaPredio,
    ForroSala,
    GerenciamentoGrupo,
    IndexLayout,
    IndisponibilizacaoSala,
    InscricaoFiscal,
    InstalacaoEletricaSala,
    InstalacaoGasesSala,
    InstalacaoHidraulicaSala,
    InstalacaoLogicaSala,
    Obra,
    OcupacaoPrestador,
    Pensionista,
    PisoSala,
    Predio,
    PrestadorServico,
    Publico,
    RegistroEmissaoDocumento,
    ReservaSala,
    Sala,
    SetorTelefone,
    SistemaAbastecimentoPredio,
    SistemaAlimentacaoEletricaPredio,
    SistemaProtecaoDescargaAtmosfericaPredio,
    SistemaSanitarioPredio,
    SolicitacaoReservaSala,
    TipoCarteiraFuncional,
    User,
    VedacaoPredio,
    Vinculo,
    CategoriaNotificacao,
    EmailBlockList,
    CertificadoDigital,
    JustificativaUsuarioExterno,
    Device, UsuarioExterno,
    ContatoEmergencia, Bolsista
)
from comum.utils import gera_nomes, get_uo, get_logo_instituicao_file_path, get_logo_instituicao_fundo_transparente_file_path
from djtools import forms
from djtools.choices import SituacaoSolicitacaoDocumento
from djtools.forms import PositionedPdfInput
from djtools.forms.fields import MultipleModelChoiceFieldPlus
from djtools.forms.fields.captcha import ReCaptchaField
from djtools.forms.widgets import AutocompleteWidget, BrTelefoneWidget, CheckboxSelectMultiplePlus, \
    FilteredSelectMultiplePlus, TreeWidget
from djtools.utils import SpanField, class_herdar, mask_cpf, mask_numbers
from djtools.storages import cache_file
from rh.enums import Nacionalidade
from rh.forms import get_choices_nome_usual
from rh.models import Pessoa, PessoaFisica, PessoaJuridica, Servidor, Setor, Situacao, UnidadeOrganizacional


class PublicoAdminForm(forms.ModelFormPlus):
    class Meta:
        model = Publico
        exclude = ()

    def clean_filtro(self):
        filtro = self.cleaned_data.get('filtro', None)
        if filtro:
            try:
                import json

                json.loads(filtro)
            except ValueError:
                raise forms.ValidationError('Formato inválido.')

        return filtro

    def clean_filtro_exclusao(self):
        filtro_exclusao = self.cleaned_data.get('filtro_exclusao', None)
        if filtro_exclusao:
            try:
                import json

                json.loads(filtro_exclusao)
            except ValueError:
                raise forms.ValidationError('Formato inválido.')

        return filtro_exclusao


class CertificadoDigitalForm(forms.ModelFormPlus):
    senha = forms.CharField(label='Senha do Certificado', widget=forms.PasswordInput, help_text='<br>Importante:</b> A senha do certificado não é salva no banco de dados. Ela é utilizada apenas para fins de validação do cadastro e extração da chave pública contida no arquivo.')

    class Meta:
        model = CertificadoDigital
        fields = ('user', 'arquivo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.is_superuser:
            self.fields['user'].initial = self.request.user.pk
            self.fields['user'].widget = forms.HiddenInput()
            self.instance.user = self.request.user
        self.arquivo_pfx = None

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        senha = cleaned_data.get('senha')
        conteudo = cleaned_data.get('arquivo').read()
        self.pfx_file = tempfile.NamedTemporaryFile(suffix='.pfx', delete=False)
        self.pfx_file.write(conteudo)
        self.pfx_file.close()
        try:
            signer.subject(self.pfx_file.name, senha)
        except ValueError:
            self.add_error('senha', 'Senha inválida.')
        return cleaned_data

    def save(self, *args, **kwargs):
        subject = signer.subject(self.pfx_file.name, self.cleaned_data['senha'])
        certificado_digital = super().save(commit=False)
        certificado_digital.nome = subject['CN']
        certificado_digital.organizacao = subject['O']
        certificado_digital.unidade = subject['OU']
        certificado_digital.validade = signer.expiration_date(self.pfx_file.name, self.cleaned_data['senha'])
        certificado_digital.conteudo = signer.dump_certificate(self.pfx_file.name, self.cleaned_data['senha'])
        certificado_digital.save()
        return certificado_digital


class AssinarDocumentoForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus(label='Arquivo PDF', max_file_size=5 * 1024 * 1024, filetypes=('pdf',), widget_custom_cls=PositionedPdfInput)
    certificado = forms.ModelChoiceField(CertificadoDigital.objects, label='Certificado')
    senha = forms.CharField(label='Senha do Certificado', widget=forms.PasswordInput)

    fieldsets = (
        ('Arquivo', {'fields': ('arquivo',)}),
        ('Assinatura', {'fields': (('certificado', 'senha'),)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['certificado'].queryset = CertificadoDigital.objects.filter(user=self.request.user)

    def clean_senha(self):
        certificado = self.cleaned_data.get('certificado')
        if not certificado:
            raise ValidationError('Escolha o certificado.')
        senha = self.cleaned_data.get('senha')
        try:
            local_filename = cache_file(certificado.arquivo.name)
            signer.subject(local_filename, senha)
            os.unlink(local_filename)
        except ValueError:
            raise ValidationError('Senha inválida.')
        return senha

    def processar(self):
        arquivo = self.cleaned_data.get('arquivo')
        certificado = self.cleaned_data.get('certificado')
        senha = self.cleaned_data.get('senha')
        arquivo.seek(0)
        conteudo_arquivo = arquivo.read()
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as fp:
            fp.write(conteudo_arquivo)
        py, px = self.request.POST.get('pdf-coords').split(':')
        page = int(self.request.POST.get('pdf-page', 1))
        local_filename = cache_file(certificado.arquivo.name)
        signed = signer.sign(
            local_filename, senha, fp.name, sign_img=True, page=page, px=px, py=py
        )
        os.unlink(local_filename)
        return signed


class VerificarDocumentoForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus(label='Arquivo', filetypes=('pdf',))

    def processar(self):
        arquivo = self.cleaned_data.get('arquivo')
        arquivo.seek(0)
        conteudo_arquivo = arquivo.read()
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as fp:
            fp.write(conteudo_arquivo)
        return signer.verify(fp.name)


class ValidarDocumentoForm(VerificarDocumentoForm):
    recaptcha = ReCaptchaField(label='')


class AreaAtuacaoForm(forms.ModelForm):
    class Meta:
        model = AreaAtuacao
        exclude = ('slug',)


class AtualizarEmailForm(forms.FormPlus):
    email_secundario = forms.EmailField(max_length=255, required=False, label='E-mail Secundário')
    email_institucional = forms.EmailField(max_length=255, required=False, label='E-mail Institucional')
    email_academico = forms.EmailField(max_length=255, required=False, label='E-mail Acadêmico')
    email_google_classroom = forms.EmailField(max_length=255, required=False, label='E-mail Google ClassRoom')

    def clean_email_secundario(self):
        if Configuracao.eh_email_institucional(self.cleaned_data['email_secundario']):
            raise forms.ValidationError("Escolha um e-mail que não seja institucional.")
        return self.cleaned_data['email_secundario']

    def clean_email_institucional(self):
        if (
            self.cleaned_data['email_institucional']
            and Servidor.objects.exclude(pessoa_fisica__id=self.pessoa_fisica.id).filter(email_institucional=self.cleaned_data['email_institucional']).exists()
        ):
            raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
        return self.cleaned_data['email_institucional']

    def clean_email_academico(self):
        if self.cleaned_data['email_academico']:
            tem_email_em_outro_usuario = False
            Aluno = apps.get_model('edu', 'aluno')
            q_exclude = Q(pk=self.relacionamento.id)
            qs_servidor = Servidor.objects.filter(email_academico=self.cleaned_data['email_academico'])
            if Aluno:
                qs_aluno = Aluno.objects.filter(email_academico=self.cleaned_data['email_academico'])
                if self.relacionamento.eh_aluno:
                    qs_aluno = qs_aluno.exclude(q_exclude)
                if qs_aluno.exists():
                    tem_email_em_outro_usuario = True

            if self.relacionamento.eh_servidor:
                qs_servidor = qs_servidor.exclude(q_exclude)
                if qs_servidor.exists():
                    tem_email_em_outro_usuario = True
            if tem_email_em_outro_usuario:
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if EmailBlockList.objects.filter(email=self.cleaned_data['email_academico']).exists():
                raise forms.ValidationError("O e-mail informado está bloqueado.")
        return self.cleaned_data['email_academico']

    def clean_email_google_classroom(self):
        if self.cleaned_data['email_google_classroom']:
            tem_email_em_outro_usuario = False
            Aluno = apps.get_model('edu', 'aluno')
            q_exclude = Q(pk=self.relacionamento.id)

            qs_servidor = Servidor.objects.filter(email_google_classroom=self.cleaned_data['email_google_classroom'])
            qs_prestador = PrestadorServico.objects.filter(email_google_classroom=self.cleaned_data['email_google_classroom'])
            if Aluno:
                qs_aluno = Aluno.objects.filter(email_google_classroom=self.cleaned_data['email_google_classroom'])
                if self.relacionamento.eh_aluno:
                    qs_aluno = qs_aluno.exclude(q_exclude)
                if qs_aluno.exists():
                    tem_email_em_outro_usuario = True
            if self.relacionamento.eh_servidor:
                qs_servidor = qs_servidor.exclude(q_exclude)
                if qs_servidor.exists():
                    tem_email_em_outro_usuario = True
            if self.relacionamento.eh_prestador:
                qs_prestador = qs_prestador.exclude(q_exclude)
                if qs_prestador.exists():
                    tem_email_em_outro_usuario = True
            if tem_email_em_outro_usuario:
                raise forms.ValidationError("O e-mail informado já existe para outro usuário.")
            if EmailBlockList.objects.filter(email=self.cleaned_data['email_google_classroom']).exists():
                raise forms.ValidationError("O e-mail informado está bloqueado.")
        return self.cleaned_data['email_google_classroom']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.relacionamento = kwargs.pop('relacionamento')
        self.pessoa_fisica = self.relacionamento.pessoa_fisica
        super().__init__(*args, **kwargs)
        eh_servidor = self.pessoa_fisica.eh_servidor
        eh_prestador = self.pessoa_fisica.eh_prestador
        self.fields['email_secundario'].initial = self.pessoa_fisica.email_secundario
        if (not self.request.user.get_profile().pk == int(self.pessoa_fisica.pk)) and (
            (eh_servidor and not self.request.user.has_perm('rh.pode_editar_email_secundario_servidor'))
            or (eh_prestador and not self.request.user.has_perm('rh.pode_editar_email_secundario_prestador'))
        ):
            del self.fields['email_secundario']

        """ Só exibe os demais campos se for servidor """
        if eh_servidor:
            self.fields['email_institucional'].initial = self.relacionamento.email_institucional
            self.fields['email_academico'].initial = self.relacionamento.email_academico
            self.fields['email_google_classroom'].initial = self.relacionamento.email_google_classroom

            if not self.request.user.has_perm('rh.pode_editar_email_institucional'):
                del self.fields['email_institucional']
            if not self.request.user.has_perm('rh.pode_editar_email_academico'):
                del self.fields['email_academico']
            if not self.request.user.has_perm('rh.pode_editar_email_google_classroom'):
                del self.fields['email_google_classroom']

        elif eh_prestador and self.relacionamento.get_vinculo().user.has_perm('edu.eh_professor'):
            self.fields['email_google_classroom'].initial = self.relacionamento.email_google_classroom
            del self.fields['email_institucional']
            del self.fields['email_academico']
            if not self.request.user.has_perm('rh.pode_editar_email_google_classroom'):
                del self.fields['email_google_classroom']
        else:
            del self.fields['email_institucional']
            del self.fields['email_academico']
            del self.fields['email_google_classroom']

    def save(self):
        instancia = self.relacionamento
        if 'email_institucional' in self.cleaned_data:
            instancia.email_institucional = self.cleaned_data.get('email_institucional')
        if 'email_academico' in self.cleaned_data:
            instancia.email_academico = self.cleaned_data.get('email_academico')
        if 'email_google_classroom' in self.cleaned_data:
            instancia.email_google_classroom = self.cleaned_data.get('email_google_classroom')
        instancia.save()

        if 'email_secundario' in self.cleaned_data:
            Pessoa.objects.filter(pk=self.pessoa_fisica.id).update(email_secundario=self.cleaned_data.get('email_secundario'))


class ConfiguracaoForm(forms.FormPlus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Municipio = apps.get_model('comum', 'municipio')
        estados = list(set(Municipio.objects.all().values_list('uf', flat=True)))
        estados.sort()

    instituicao_sigla = forms.CharField(label='Sigla da Instituição', help_text='Sigla da instituição em que o SUAP está instalado')
    reitoria_sigla = forms.CharField(label='Sigla da Reitoria', help_text='Sigla da reitoria em que o SUAP está instalado')
    dominios_institucionais = forms.CharField(label='Domínios Institucionais', help_text='Domínios Institucionais separados por ";".')
    instituicao = forms.CharField(label='Instituição', widget=forms.Textarea, help_text='Nome da instituição em que o SUAP está instalado')
    instituicao_estado = forms.BrEstadoBrasileiroField(label='Estado da Instituição', help_text='Sigla do estado da Instituição utilizada em Endereços e Macros do Extrator')
    setores = forms.ChoiceField(label='Setores', help_text='Forma de tratamento de setores', choices=(('', ''), ('SIAPE', 'SIAPE'), ('SUAP', 'SUAP')))
    instituicao_identificador = forms.CharField(
        label='Identificador SIAPE da Instituição', help_text='Faz parte da matrícula de 12 caracteres dos servidores e é' ' usado para filtrar os dados nas Macros do Extrator'
    )
    instituicao_codigo_siorg = forms.CharField(
        label='Código SIORG da Instituição', help_text='Disponível em https://siorg.planejamento.gov.br/siorg-cidadao-webapp/pages/listar_orgaos_estruturas/listar_orgaos_estruturas.jsf'
    )

    instituicao_anterior_identificador = forms.CharField(
        label='Identificador SIAPE das Instituições Anteriores',
        help_text='Faz parte da matrícula de 12 caracteres dos servidores e é'
        ' usado para filtrar os dados nas Macros do Extrator. Se houver mais de uma instituição anterior, separar por ponto e vírgula',
        required=False,
    )
    siape_usuario = forms.CharField(label='SiapeNet usuário', help_text='Usuário para extração do SiapeNet', required=False)
    siape_senha = forms.CharField(label='SiapeNet senha', help_text='Senha para extração do SiapeNet', required=False)
    url_rss = forms.URLField(label='URL do RSS', help_text='URL do RSS para exibição na página inicial do SUAP', required=False)
    salario_minimo = forms.DecimalField(label='Salário Mínimo', help_text='Valor atual do salário mínimo')
    chave_publica = forms.CharField(label='Chave Pública', widget=forms.Textarea, help_text='Conteúdo da chave pública da máquina do SUAP', required=False)
    url_webmail = forms.URLField(label='URL do Webmail', help_text='URL do Webmail da instituição', required=False)
    sentry_token = forms.CharField(label='Token Bearer do Sentry para integração de APIs', help_text='Ex: a06631308fc54c68f86a54f2c8ecc61ece35c38181f1fc104c5998be2961c0fb', required=False)
    sentry_url = forms.CharField(label='URL do Sentry sem barra no final', help_text='Ex: https://sentry.ifrn.edu.br', required=False)
    sentry_organization = forms.CharField(label='Organização do Sentry para o Projeto SUAP', help_text='Ex: sentry', required=False)
    sentry_project = forms.CharField(label='Projeto SUAP no Sentry', help_text='Ex: suap', required=False)

    logo_instituicao = forms.FileFieldPlus(
        label='Logotipo da instituição',
        required=False,
    )
    logo_instituicao_fundo_transparente = forms.FileFieldPlus(
        label='Logotipo da instituição com fundo transparente',
        required=False,
    )
    quadro_banner = forms.BooleanField(label='Quadro de banner', help_text='Apresenta o quadro de banner na index', required=False)
    quadro_manuais = forms.BooleanField(label='Quadro de manuais', help_text='Apresenta o quadro de manuais na index', required=False)

    # Autenticação com Login Gov.BR
    habilitar_autenticacao_govbr = forms.BooleanField(label='Habilitar Autenticação com Gov.BR', help_text='É necessário configurar os tokens e habilitar a plataforma Notifica para envio dos códigos de verificação na assinatura de documentos', required=False)

    def clean(self):
        cleaned_data = super().clean()

        # if not os.environ.get('SOCIAL_AUTH_GOVBR_KEY', 'False') or os.environ.get('SOCIAL_AUTH_GOVBR_SECRET', 'False'):
        #     raise forms.ValidationError('Todas as configurações referentes ao Login Gov.Br devem ser informadas para ativar a autenticação.')

        return cleaned_data


class PensionistaForm(forms.ModelFormPlus):
    class Meta:
        model = Pensionista
        fields = ('matricula', 'numero_processo', 'representante_legal', 'grau_parentesco', 'data_inicio_pagto_beneficio', 'data_fim_pagto_beneficio')


class ConfiguracaoFormBase(forms.FormPlus):
    """
    É a superclasse do formulário de Configuração e trata a sincronia
    do form com o banco de dados.
    """

    TITLE = 'Configuração do SUAP'

    def __init__(self, *args, **kwargs):
        # Definindo os valores iniciais dos campos
        for obj in Configuracao.objects.all():
            field_name = obj.chave
            if field_name in self.base_fields:
                field = self.base_fields[field_name]
                if hasattr(field, 'queryset'):
                    valor = obj.valor
                elif issubclass(self.base_fields[field_name].__class__, DateField) and obj.valor:
                    valor = datetime.datetime.strptime(obj.valor, "%Y-%m-%d").date()
                elif issubclass(self.base_fields[field_name].__class__, FileField) and obj.valor:
                    obj.url = default_storage.url(obj.valor)
                    valor = obj
                else:
                    valor = obj.valor
                field.initial = valor
        super().__init__(*args, **kwargs)

    def save(self):
        with transaction.atomic():
            for nome, valor in list(self.cleaned_data.items()):
                if hasattr(valor, 'file'):
                    relative_path = f'configuracao/{valor.name}'
                    file_name = default_storage.save(relative_path, valor)
                    valor = file_name
                elif isinstance(valor, Configuracao):
                    continue
                elif hasattr(valor, '__iter__') and type(valor) != str:  # queryset or any iterable
                    valor = ','.join([str(getattr(v, 'pk', v)) for v in valor])
                else:
                    valor = str(getattr(valor, 'pk', valor if valor else ''))
                Configuracao.objects.update_or_create(app=self.fields[nome]._app, chave=nome, defaults={'valor': valor, 'descricao': self.__class__.base_fields[nome].label})
        get_logo_instituicao_file_path(force=True)
        get_logo_instituicao_fundo_transparente_file_path(force=True)
        Configuracao.clear_cache()


def __add_prefix_to_fields(klass, prefix):
    """
    Apenas retorna a lista de campos com o nome formatado com o prefixo
    """
    new_base_fields = OrderedDict()
    for name, field in list(klass.base_fields.items()):
        new_base_fields[f'{prefix}__{name}'] = field
    return new_base_fields


def ConfiguracaoFormFactory():
    """
    Monta o formulário para configuração de acordo com ConfiguracaoForm definidos nas apps em INSTALLED_APPS
    """
    cls = None
    fieldsets = []
    for app in settings.INSTALLED_APPS:
        try:
            mod = __import__(f'{app}.forms', fromlist=['ConfiguracaoForm'])
            ConfiguracaoFormApp = getattr(mod, 'ConfiguracaoForm')
            # exec 'from %s.forms import ConfiguracaoForm as ConfiguracaoFormApp' % app in locals() #Solução pep 227: http://www.python.org/dev/peps/pep-0227/
        except AttributeError:
            continue
        except ImportError:
            continue
        if cls:
            cls = class_herdar(ConfiguracaoFormBase, cls)
        cls = ConfiguracaoFormApp

        # Mecanismo usado para identificar a app do field
        for name, field in list(cls.base_fields.items()):
            field._app = app

        # Agrupando os campos de acordo com suas respectivas apps
        fieldsets.append((f'Aplicação {app.capitalize()}', dict(fields=list(cls.base_fields.keys()))))

    cls = class_herdar(ConfiguracaoFormBase, cls)

    class FormClass(ConfiguracaoFormBase):
        pass

    FormClass.fieldsets = fieldsets

    return FormClass


class PrestadorServicoForm(forms.ModelFormPlus):
    nome_usual = forms.ChoiceField(label="Nome Usual", required=True, help_text='Nome que será exibido no SUAP')
    empresa = forms.ModelChoiceFieldPlus(queryset=PessoaJuridica.objects.all(), required=False)
    setor = forms.ModelChoiceField(queryset=Setor.objects.all(), widget=TreeWidget())
    setores_adicionais = forms.MultipleModelChoiceFieldPlus(
        required=False, queryset=Setor.objects.all(), label='Setores visíveis no sistema de protocolo'
    )
    cpf = forms.BrCpfField(required=False)
    passaporte = forms.CharField(label='Nº do Passaporte', required=False, help_text='Esse campo é obrigatório para estrangeiros. Ex: BR123456')
    username = forms.CharField(required=False)  # Só é visível para super usuarios na edição

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = get_choices_nome_usual(self.instance.nome)
        self.fields['setor'].initial = self.request.user.get_vinculo().setor
        self.fields["nome_usual"].choices = choices
        if len(choices) == 1:
            self.fields["nome_usual"].required = False

    class Meta:
        model = PrestadorServico
        fields = ('nome_registro', 'nome_social', 'nome_usual', 'cpf', 'sexo', 'nacionalidade', 'passaporte', 'setor', 'setores_adicionais', 'ativo')
        # exclude = ('template', 'template_importado_terminal')

    def clean_cpf(self):
        nacionalidade = self.data.get('nacionalidade')
        cpf = self.cleaned_data.get('cpf')
        if nacionalidade and int(nacionalidade) in [Nacionalidade.BRASILEIRO_NATO, Nacionalidade.BRASILEIRO_NATZ]:
            if not cpf:
                self.add_error('cpf', 'Informe o cpf.')
            qs = PrestadorServico.objects.filter(cpf=cpf)
            if self.instance:
                qs = qs.exclude(id=self.instance.pk)
            if qs.exists():
                self.add_error('cpf', 'Este CPF já está sendo usado por outro prestador.')
        return cpf

    def clean_passaporte(self):
        nacionalidade = self.data.get('nacionalidade')
        passaporte = self.data.get('passaporte')
        if nacionalidade and int(nacionalidade) == Nacionalidade.ESTRANGEIRO:
            if not passaporte:
                self.add_error('passaporte', 'Informe o passaporte.')
            qs = PrestadorServico.objects.filter(passaporte=passaporte)
            if self.instance:
                qs = qs.exclude(id=self.instance.pk)
            if qs.exists():
                self.add_error('passaporte', 'Este passaporte já está sendo usado por outro prestador.')
        return passaporte

    def clean_email_secundario(self):
        email_secundario = self.cleaned_data['email_secundario']
        if Configuracao.eh_email_institucional(email_secundario):
            self.add_error('email_secundario', 'O email secundário não pode ser um email institucional dos seguintes domínios: {}'.format(Configuracao.get_valor_por_chave("comum", "dominios_institucionais")))
        return email_secundario

    def clean(self):
        nacionalidade = self.cleaned_data.get('nacionalidade')
        cpf = self.cleaned_data.get('cpf')
        passaporte = self.cleaned_data.get('passaporte')
        ativo = self.cleaned_data.get('ativo')
        setor = self.cleaned_data.get('setor')

        if not ativo and self.instance.setor != setor:
            raise forms.ValidationError('Não é possível desativar e alterar o setor ao mesmo tempo.')

        try:
            eh_estrangeiro = int(nacionalidade) == Nacionalidade.ESTRANGEIRO
        except Exception:
            eh_estrangeiro = False
        if not cpf and not eh_estrangeiro:
            self.add_error('cpf', "O campo CPF é obrigatório para nacionalidades Brasileira")

        if eh_estrangeiro and not cpf:
            username = re.sub(r'\W', '', str(passaporte))
            campo_erro = 'passaporte'
        else:
            username = re.sub(r'\D', '', str(cpf))
            campo_erro = 'cpf'
        if not self.instance.pk and User.objects.filter(username=username).exists():
            self.add_error(campo_erro, f'O usuário {username} já existe.')
        return super().clean()


class OcupacaoPrestadorForm(forms.ModelFormPlus):
    class Meta:
        model = OcupacaoPrestador
        exclude = ('prestador',)

    def __init__(self, *args, **kwargs):
        self.prestador = kwargs.pop('prestador')
        self.instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

    def processar(self):
        if self.instance:
            ocupacao_prestador = self.instance
        else:
            ocupacao_prestador = OcupacaoPrestador()

        ocupacao_prestador.prestador = self.prestador
        ocupacao_prestador.ocupacao = self.cleaned_data.get('ocupacao')
        ocupacao_prestador.empresa = self.cleaned_data.get('empresa')
        ocupacao_prestador.data_inicio = self.cleaned_data.get('data_inicio')
        ocupacao_prestador.data_fim = self.cleaned_data.get('data_fim')
        ocupacao_prestador.setor_suap = self.cleaned_data.get('setor_suap')
        ocupacao_prestador.save()


# TODO: rever se o documento controle é para ficar dentro de comum
def DocumentoControleAdminFormFactory(request, obj):
    pessoa_fisica = request.user.get_profile()
    s = request.user.get_relacionamento()
    # Documento suportado hj no ifrn é apenas o cracha
    documento_suportado = DocumentoControleTipo.objects.get(identificador=DocumentoControleTipo.CRACHA)

    class DocumentoBaseForm(forms.ModelFormPlus):
        class Meta:
            model = DocumentoControle
            fields = ('documento_tipo',)
            exclude = ()

        class Media:
            js = ('/static/comum/js/solicitacao_documento.js',)

        def __init__(self, *args, **kwargs):
            self.instance = kwargs.get('instance')
            super().__init__(*args, **kwargs)

            fields_removidos = self.fields.keys() - self.get_fields()
            for field_removido in fields_removidos:
                self.fields.pop(field_removido)

            # Pode solicitar apenas os documentos suportados pelo seu campus (que exista algum campus que imprima o documento);
            uo_usuario = get_uo(request.user)
            doc_suportados = []
            for conf in ConfiguracaoImpressaoDocumento.objects.all():
                if conf.relacao_impressao.filter(id=uo_usuario.id).exists():
                    doc_suportados += [doc.id for doc in conf.tipos_documento.all()]

            self.fields['documento_tipo'].queryset = DocumentoControleTipo.objects.filter(id__in=doc_suportados)
            documento_tipo = documento_suportado.id
            if documento_tipo:
                self.fields['documento_tipo'].initial = documento_tipo

            # Solicitante
            if 'solicitante_vinculo' in self.fields:
                self.fields['solicitante_vinculo'].widget = forms.HiddenInput()
                if request.user.has_perm('comum.change_documentocontrole'):
                    self.fields['solicitante_vinculo'].widget = AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS, help_text='Você pode selecionar outro solicitante.')

                # verificando a abrangência do documento
                if documento_suportado:
                    abrangencia = documento_suportado.abrangencia.values_list('codigo', flat=True)
                    self.fields['solicitante_vinculo'].queryset = Vinculo.objects.filter(
                        tipo_relacionamento__model='servidor', id_relacionamento__in=(
                            Servidor.objects.filter(situacao__codigo__in=abrangencia).values_list('id', flat=True))
                    )
                if self.instance and self.instance.id:
                    self.fields['solicitante_vinculo'].initial = self.instance.solicitante_vinculo.id
                else:
                    self.fields['solicitante_vinculo'].initial = request.user.get_vinculo()

            # Justificativa
            if 'justificativa' in self.fields:
                self.fields['justificativa'].widget = forms.Textarea(attrs={'rows': 2, 'cols': 20})
                if self.instance:
                    self.fields['justificativa'].initial = self.instance.justificativa

        @staticmethod
        def get_fields():
            return ('documento_tipo',)

        def clean(self):
            documento_tipo = self.cleaned_data.get('documento_tipo')
            solicitante_vinculo = self.cleaned_data.get('solicitante_vinculo')

            if not documento_tipo:
                raise ValidationError('Não foi possível identificar o tipo do documento.')

            if not solicitante_vinculo:
                raise ValidationError('Não foi possível identificar o solicitante.')

            '''
            verificando se já existe uma solicitação não atendida para este tipo de documento
            '''
            qs_solicitacao = DocumentoControle.objects.filter(
                solicitante_vinculo=solicitante_vinculo, status_solicitacao=SituacaoSolicitacaoDocumento.NAO_ATENDIDA, ativo=True, documento_tipo=documento_tipo
            ).exclude(pk=self.instance.id)
            if qs_solicitacao.exists():
                raise ValidationError(
                    'PROBLEMA: Não é possível solicitar um(a) {} para o usuário {} pois já existe uma solicitação pendente.'.format(
                        documento_tipo.descricao, solicitante_vinculo.pessoa.nome
                    )
                )

            '''
            verificando se o usuário tem foto, grupo sanguíneo e fator rh cadastrado (informações necessárias para a confecção de crachá e carteira funcional)
            '''
            if documento_tipo and documento_tipo.id in [DocumentoControleTipo.CARTEIRA_FUNCIONAL, DocumentoControleTipo.CRACHA]:
                try:
                    mensagens = []
                    solicitante_vinculo = Vinculo.objects.get(pk=solicitante_vinculo)
                    if solicitante_vinculo.pessoa.pessoafisica.foto is None or solicitante_vinculo.pessoa.pessoafisica.foto == '':
                        mensagens.append(' - Você não tem uma foto cadastrada.')
                    if solicitante_vinculo.pessoa.pessoafisica.grupo_sanguineo is None or solicitante_vinculo.pessoa.pessoafisica.grupo_sanguineo == '':
                        mensagens.append(' - Você não tem um grupo sanguíneo cadastrado.')
                    if solicitante_vinculo.pessoa.pessoafisica.fator_rh is None or solicitante_vinculo.pessoa.pessoafisica.fator_rh == '':
                        mensagens.append(' - Você não tem um fator rh cadastrado.')

                    if mensagens:
                        mensagens.append('Favor comparecer à Gestão de Pessoas do Campus para atualização das suas informações.')
                        mensagens = ['PROBLEMAS ENCONTRADOS:'] + mensagens
                        raise ValidationError(mensagens)

                except Vinculo.DoesNotExist:
                    raise ValidationError('Ocorreu um erro na sua solicitação. Entre em contato com o setor pessoal de seu campus para verificar sua situação cadastral.')

    class CrachaForm(DocumentoBaseForm):
        nome_sugerido = forms.ChoiceField(choices=(), widget=forms.Select(), required=False)

        class Meta:
            model = DocumentoControle
            fields = ('documento_tipo', 'solicitante_vinculo', 'nome_sugerido', 'nome_social', 'justificativa', 'status_solicitacao', 'ativo')

        def __init__(self, *args, **kwargs):
            self.instance = kwargs.get('instance')
            super().__init__(*args, **kwargs)

            vinculo_usuario_request = None
            if self.request and self.request.POST.get('solicitante_vinculo'):
                id_usuario_request = self.request.POST.get('solicitante_vinculo')
                vinculo_usuario_request = Vinculo.objects.get(pk=id_usuario_request)

            # Nome sugerido
            if 'nome_sugerido' in self.fields:
                nome = pessoa_fisica.nome
                if vinculo_usuario_request:
                    nome = vinculo_usuario_request.pessoa.nome
                if self.instance and self.instance.id:
                    nome = self.instance.solicitante_vinculo.pessoa.nome
                nomes = gera_nomes(nome)
                choice_nomes = [['', 'Selecione umas das opções']]
                for nome in nomes:
                    choice_nomes.append([nome, nome])
                self.fields['nome_sugerido'].choices = choice_nomes

        @staticmethod
        def get_fields():
            campos = ('documento_tipo', 'solicitante_vinculo', 'nome_sugerido', 'nome_social', 'justificativa')
            if request.user.has_perm('comum.change_documentocontrole'):
                campos = campos + ('status_solicitacao', 'ativo')
            return campos

        def clean(self):
            super().clean()

            nome_sugerido = self.cleaned_data.get('nome_sugerido')
            nome_social = self.cleaned_data.get('nome_social')

            if (nome_social is None or nome_social == '') and (nome_sugerido is None or nome_sugerido == ''):
                raise ValidationError('Por favor, selecione um nome sugerido ou descreva um nome social.')

            return self.cleaned_data

    # verificando se o usuário é um servidor ativo, um estagiário, um professor substituto ou temporário
    if isinstance(s, Servidor):
        if (s.situacao.codigo,) in documento_suportado.abrangencia.values_list('codigo'):
            return CrachaForm
        else:
            messages.error(request, 'Você não pode solicitar um crachá.')
    elif isinstance(s, PrestadorServico):
        return CrachaForm

    return DocumentoBaseForm


class ConfiguracaoImpressaoDocumentoForm(forms.ModelFormPlus):
    uo = forms.ModelChoiceFieldPlus(
        queryset=UnidadeOrganizacional.objects.suap(),
        label='Unidade Organizacional',
        required=True,
    )
    relacao_impressao = forms.ModelMultipleChoiceField(
        queryset=UnidadeOrganizacional.objects.suap(),
        label='Relação de Impressão',
        widget=FilteredSelectMultiplePlus('', True),
        required=True,
        help_text="Escolha para quais campi o campus acima selecionado poderá imprimir.",
    )
    tipos_documento = forms.ModelMultipleChoiceField(queryset=DocumentoControleTipo.objects, label='Tipos de Documentos', widget=CheckboxSelectMultiplePlus())

    class Meta:
        model = ConfiguracaoImpressaoDocumento
        exclude = ()


class DocumentoControleTipoForm(forms.ModelFormPlus):
    identificador = forms.ChoiceField(label='Documento', choices=DocumentoControleTipo.TIPO_DOCUMENTO_CHOICES, widget=forms.Select(), required=True)
    abrangencia = forms.ModelMultipleChoiceField(queryset=Situacao.objects, label='Abrangência', widget=FilteredSelectMultiplePlus('', True), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = DocumentoControleTipo
        fields = ('identificador', 'abrangencia')


class RejeitarSolicitacaoForm(forms.ModelFormPlus):
    class Meta:
        model = DocumentoControleHistorico
        fields = ('motivo',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['motivo'].widget = forms.Textarea(attrs={'rows': 2, 'cols': 20})


class SetorAdicionarTelefoneForm(forms.FormPlus):
    numero = forms.BrTelefoneField(label='Número telefônico', required=False)
    ramal = forms.CharField(max_length=5, help_text='O ramal é obrigatório mesmo para telefones sem "número telefônico".')
    observacao = forms.CharField(label='Observação', required=False, max_length=50)

    def clean_ramal(self):
        if not self.cleaned_data['ramal'].isdigit():
            raise forms.ValidationError('Certifique-se de que o ramal é um número')
        return self.cleaned_data['ramal']


class InscricaoFiscalForm(forms.ModelFormPlus):
    class Meta:
        model = InscricaoFiscal
        exclude = ['servidor']

    def clean_data_inicio_servico_na_instituicao(self):
        data = self.cleaned_data['data_inicio_servico_na_instituicao']
        if data > datetime.date.today():
            raise forms.ValidationError('A data deve estar no passado.')
        return data


class ExtracaoForm(forms.FormPlus):
    arquivo_1 = forms.FileFieldPlus(required=True, label='Arquivo Ref')
    arquivo_2 = forms.FileFieldPlus(required=True, label='Arquivo Siafe')
    campo_busca = forms.CharField(label='Buscar item:', required=False)
    METHOD = 'post'
    ACTION = '/comum/ver_arquivo_siafi/'
    TITLE = 'Visualizar Arquivos SIAFI'
    VALUE = 'Visualizar'
    ENCTYPE = 'multipart/form-data'


class SetorTelefoneForm(forms.ModelFormPlus):
    numero = forms.BrTelefoneField(max_length=14, label='Número', widget=BrTelefoneWidget())

    class Meta:
        model = SetorTelefone
        exclude = ()


class ContatoEmergenciaForm(forms.ModelFormPlus):
    nome_contato = forms.CharFieldPlus(label='Nome do Contato', required=True, max_length=200)
    telefone = forms.BrTelefoneField(label='Telefone', required=True, widget=BrTelefoneWidget())

    class Meta:
        model = ContatoEmergencia
        exclude = ('pessoa_fisica',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        if not self.instance.pk and ContatoEmergencia.objects.filter(
            pessoa_fisica=self.instance.pessoa_fisica,
            telefone=self.cleaned_data.get('telefone')
        ).exists():
            raise forms.ValidationError("O número de telefone já foi adicionado aos contatos de emergência desta pessoa.")


class UploadArquivoForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus()
    descricao = forms.CharField(label="Descrição", required=True)
    data = forms.DateFieldPlus(label='Data', required=True, help_text='Data em que a foto foi tirada no formato dd/mm/aaaa')


class PredioForm(forms.ModelFormPlus):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.is_superuser:
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.campi().filter(id=get_uo(self.request.user).id)

        self.fields['estrutura'].queryset = EstruturaPredio.objects.filter(ativo=True)
        self.fields['cobertura'].queryset = CoberturaPredio.objects.filter(ativo=True)
        self.fields['vedacao'].queryset = VedacaoPredio.objects.filter(ativo=True)
        self.fields['sistema_sanitario'].queryset = SistemaSanitarioPredio.objects.filter(ativo=True)
        self.fields['sistema_abastecimento'].queryset = SistemaAbastecimentoPredio.objects.filter(ativo=True)
        self.fields['sistema_alimentacao_eletrica'].queryset = SistemaAlimentacaoEletricaPredio.objects.filter(ativo=True)
        self.fields['sistema_protecao_descarga_atmosferica'].queryset = SistemaProtecaoDescargaAtmosfericaPredio.objects.filter(ativo=True)
        self.fields['acabamento_externo'].queryset = AcabamentoExternoPredio.objects.filter(ativo=True)


class ObraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        exclude = ()

    class Media:
        js = ('/static/comum/js/CadastrarObra.js',)


class SalaForm(forms.ModelFormPlus):
    class Meta:
        model = Sala
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        servidores_ativos = Servidor.objects.ativos().values_list('pessoa_fisica__id', flat=True)
        if self.request.user.has_perm('comum.change_sala'):
            self.fields['avaliadores_de_agendamentos'].queryset = User.objects.filter(pessoafisica__in=servidores_ativos)
            if not self.request.user.is_superuser:
                self.fields['predio'].queryset = Predio.objects.filter(uo=get_uo(self.request.user)).order_by('nome')

        self.fields['instalacao_eletrica'].queryset = InstalacaoEletricaSala.objects.filter(ativo=True)
        self.fields['instalacao_logica'].queryset = InstalacaoLogicaSala.objects.filter(ativo=True)
        self.fields['instalacao_hidraulica'].queryset = InstalacaoHidraulicaSala.objects.filter(ativo=True)
        self.fields['instalacao_gases'].queryset = InstalacaoGasesSala.objects.filter(ativo=True)
        self.fields['climatizacao'].queryset = ClimatizacaoSala.objects.filter(ativo=True)
        self.fields['acabamento_parede'].queryset = AcabamentoParedeSala.objects.filter(ativo=True)
        self.fields['piso'].queryset = PisoSala.objects.filter(ativo=True)
        self.fields['forro'].queryset = ForroSala.objects.filter(ativo=True)
        self.fields['esquadrias'].queryset = EsquadriasSala.objects.filter(ativo=True)


class AlterarSenhaForm(forms.FormPlus):
    senha = forms.CharFieldPlus(label='Senha Atual', widget=PasswordInput, required=True, max_length=255)
    recaptcha = ReCaptchaField(label='Verificação')

    def clean_senha(self):
        if not authenticate(username=self.request.user.username, password=self.cleaned_data['senha']):
            raise ValidationError('Senha Atual incorreta.')


class SoliticarTrocarSenhaForm(forms.FormPlus):
    username = forms.CharField(label='Usuário', help_text='Informe a sua matrícula, caso seja servidor ou aluno, ou o seu CPF.', required=True)
    cpf_passaporte = forms.CharField(label='CPF/Passaporte', help_text='Brasileiros ou Naturalizados devem informar o CPF. Estrangeiros devem informar o Passaporte (Formato: BR123456).', required=True)
    recaptcha = ReCaptchaField(label='Verificação')

    def clean(self):
        cpf_passaporte = self.cleaned_data.get('cpf_passaporte')
        username = self.cleaned_data.get('username')
        pessoa_fisica = PessoaFisica.objects.filter(username=username).filter(Q(cpf=mask_cpf(cpf_passaporte)) | Q(passaporte=cpf_passaporte)).first()
        if not pessoa_fisica:
            if username and len(username) == 14:
                username = username.replace('.', '').replace('-', '')
                self.cleaned_data['username'] = username
                pessoa_fisica = PessoaFisica.objects.filter(username=username).filter(Q(cpf=mask_cpf(cpf_passaporte)) | Q(passaporte=cpf_passaporte)).first()
                if not pessoa_fisica:
                    raise forms.ValidationError('Nenhum usuário encontrado com os dados especificados.')
            else:
                raise forms.ValidationError('Nenhum usuário encontrado com os dados especificados.')

        # if not pessoa_fisica.email_secundario:
        #     raise forms.ValidationError('Usuário sem email secundário cadastrado.')

        # verifica se usuário tem conta no AD
        utiliza_autenticacao_ldap = Configuracao.get_valor_por_chave("ldap_backend", "utilizar_autenticacao_via_ldap")
        if 'ldap_backend' in settings.INSTALLED_APPS and utiliza_autenticacao_ldap:
            if not pessoa_fisica.get_usuario_ldap(attrs=['dn']):
                raise forms.ValidationError('Usuário não tem conta sincronizada com o AD. Favor entrar em contato com a TI do Campus.')
        return self.cleaned_data


class BuscaUsuarioGrupoForm(forms.FormPlus):
    nome = forms.CharField(label='Filtrar por Nome/Matrícula/CPF', required=False, widget=forms.TextInput(attrs={'size': 20}))
    grupo = forms.ModelChoiceField(required=False, queryset=Group.objects.all(), widget=forms.HiddenInput())
    campus = forms.ModelChoiceField(required=False, queryset=UnidadeOrganizacional.objects.campi().all(), label='Filtrar por Campus')


class GrupoGerenciamentoForm(forms.ModelFormPlus):
    grupo_gerenciador = forms.ModelChoiceFieldPlus(label="Grupo Gerenciador", queryset=Group.objects.all(), widget=AutocompleteWidget())
    grupos_gerenciados = forms.ModelMultipleChoiceField(label="Grupos", queryset=Group.objects.all(), widget=FilteredSelectMultiple('', True))

    class Meta:
        model = GerenciamentoGrupo
        exclude = ()


class AdicionarUsuarioGrupoForm(forms.FormPlus):
    user = forms.MultipleModelChoiceFieldPlus(
        queryset=User.objects.filter(Q(pessoafisica__eh_servidor=True) | Q(pessoafisica__eh_prestador=True), is_active=True),
        label='Usuário',
        help_text="Informe parte do Nome ou Matrícula ou CPF ou E-mail Institucional",
    )


def AdicionarUsuarioGrupoFormFactory(usuario, so_local):
    class AdicionarUsuarioGrupoForm(forms.FormPlus):
        user = forms.MultipleModelChoiceFieldPlus(
            queryset=User.objects.filter(Q(pessoafisica__eh_servidor=True) | Q(pessoafisica__eh_prestador=True), is_active=True),
            label='Usuário',
            help_text="Informe parte do Nome ou Matrícula ou CPF ou E-mail Institucional",
        )

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if so_local:
                self.fields['user'].queryset = User.objects.filter(
                    vinculo__tipo_relacionamento__model__in=['prestadorservico', 'servidor'], is_active=True, vinculo__setor__uo=usuario.get_relacionamento().setor.uo
                )

    return AdicionarUsuarioGrupoForm


def VincularSetorUsuarioGrupoFormFactory(usuario_grupo):
    class VincularSetorUsuarioGrupoForm(forms.FormPlus):
        setores = forms.MultipleModelChoiceFieldPlus(
            required=False,
            queryset=Setor.objects.all(),
            help_text='Informe o setor vinculado a esse usuário para o respectivo grupo',
        )

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['setores'].initial = usuario_grupo.setores.all().values_list("id", flat=True)

    return VincularSetorUsuarioGrupoForm


class ComentarioForm(forms.FormPlus):
    texto = forms.CharField(label='Texto', widget=forms.Textarea())


class AutenticarDocumentoForm(forms.FormPlus):
    tipo = forms.ModelChoiceFieldPlus(
        label="Tipo de Documento",
        queryset=Group.objects,
        widget=AutocompleteWidget(
            search_fields=['tipo', ]
        )
    )
    data_emissao = forms.DateFieldPlus(label='Data da Emissão')
    codigo_verificador = forms.CharField(label='Código Verificador')
    recaptcha = ReCaptchaField(label='')
    tipo_objeto = forms.IntegerField(label='Informação Auxiliar', required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = RegistroEmissaoDocumento.objects.all().order_by('tipo').distinct('tipo')

    def clean_tipo_objeto(self):
        registros = self.get_registros()
        if registros.count() > 1:
            content_types = ContentType.objects.filter(pk__in=registros.values_list('tipo_objeto', flat=True))
            self.fields['tipo_objeto'] = forms.ModelChoiceField(content_types, label='Informação Auxiliar', required=False)
            if not self.cleaned_data.get('tipo_objeto'):
                raise forms.ValidationError('Este campo é obrigatório')
        return self.cleaned_data.get('tipo_objeto')

    def clean_codigo_verificador(self):
        codigo_verificador = self.cleaned_data.get('codigo_verificador')
        if len(codigo_verificador) < 6:
            raise forms.ValidationError('Informe pelo menos 6 dígitos para o código verificador.')
        return codigo_verificador

    def get_registros(self):
        data_emissao = self.cleaned_data.get('data_emissao')
        tipo = self.cleaned_data.get('tipo')
        codigo_verificador = self.cleaned_data.get('codigo_verificador')
        if data_emissao and tipo and codigo_verificador:
            registros = RegistroEmissaoDocumento.objects.filter(tipo=tipo, codigo_verificador__startswith=codigo_verificador)
            registros = registros.filter(data_emissao__gte=data_emissao, data_emissao__lte=data_emissao + datetime.timedelta(1))
            registros = registros.filter(cancelado=False)
            return registros
        return RegistroEmissaoDocumento.objects.none()

    def processar(self):
        registros = self.get_registros()
        tipo_objeto = self.cleaned_data.get('tipo_objeto')
        if tipo_objeto:
            return registros.get(tipo_objeto=tipo_objeto)
        return registros.first()


class SolicitacaoReservaSalaForm(forms.ModelFormPlus):
    sala = SpanField('Sala')
    capacidade = SpanField('Capacidade da sala (em número de pessoas)')
    interessados_vinculos = forms.MultipleModelChoiceFieldPlus(
        Vinculo.objects.all(),
        label='Interessados',
        required=False,
        help_text='Informe aqui as pessoas interessadas nessa solicitação; elas serão notificadas por email.',
    )

    fieldsets = (
        (
            'Dados Gerais',
            {'fields': (('solicitante'), ('sala', 'capacidade'), ('recorrencia'), ('data_inicio', 'data_fim'), ('hora_inicio', 'hora_fim'), 'justificativa', 'interessados_vinculos', 'anexo')},
        ),
        (
            'Dias da Semana',
            {
                'fields': (
                    ('recorrencia_segunda', 'recorrencia_terca', 'recorrencia_quarta', 'recorrencia_quinta', 'recorrencia_sexta', 'recorrencia_sabado', 'recorrencia_domingo'),
                )
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sala'].widget.original_value = self.instance.sala
        self.fields['sala'].widget.label_value = self.instance.sala
        self.fields['capacidade'].widget.original_value = self.instance.sala.capacidade
        self.fields['capacidade'].widget.label_value = self.instance.sala.capacidade or '-'
        self.fields['solicitante'].queryset = self.fields['solicitante'].queryset.filter(is_active=True, is_staff=True)
        if not self.request.user.groups.filter(name='Avaliador de Sala').exists():
            del self.fields['solicitante']

    class Meta:
        model = SolicitacaoReservaSala
        fields = (
            'solicitante',
            'sala',
            'recorrencia',
            'data_inicio',
            'data_fim',
            'hora_inicio',
            'hora_fim',
            'justificativa',
            'interessados_vinculos',
            'anexo',
            'recorrencia_segunda',
            'recorrencia_terca',
            'recorrencia_quarta',
            'recorrencia_quinta',
            'recorrencia_sexta',
            'recorrencia_sabado',
            'recorrencia_domingo',
        )

    class Media:
        js = ('/static/comum/js/SolicitacaoReservaSalaForm.js',)

    def clean(self):
        cleaned_data = super().clean()
        recorrencia = cleaned_data.get("recorrencia")
        if not self.errors:
            data_inicio = cleaned_data.get("data_inicio")
            data_fim = cleaned_data.get("data_fim")
            hora_inicio = cleaned_data.get("hora_inicio")
            hora_fim = cleaned_data.get("hora_fim")
            data_solicitacao = self.instance.data_solicitacao
            sala = cleaned_data.get("sala")

            if data_fim < data_inicio:
                self.errors['data_fim'] = ["Data de Fim deve ser maior ou igual a Data de Início."]
                del cleaned_data['data_fim']

            if hora_inicio > hora_fim and not (data_inicio < data_fim and recorrencia == SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO):
                self.errors['hora_fim'] = ["Hora de Fim deve ser maior ou igual a Hora de Início."]
                del cleaned_data['hora_fim']

            if data_inicio <= data_solicitacao.date() and hora_inicio < data_solicitacao.time():
                self.errors["data_inicio"] = ["Data/Hora de Início deve ser maior ou igual a Data/Hora da solicitação."]
                del cleaned_data['data_inicio']

            solicitacao = SolicitacaoReservaSala(
                recorrencia=recorrencia,
                data_inicio=data_inicio,
                data_fim=data_fim,
                hora_inicio=hora_inicio,
                recorrencia_segunda=self.cleaned_data.get('recorrencia_segunda'),
                recorrencia_terca=self.cleaned_data.get('recorrencia_terca'),
                recorrencia_quarta=self.cleaned_data.get('recorrencia_quarta'),
                recorrencia_quinta=self.cleaned_data.get('recorrencia_quinta'),
                recorrencia_sexta=self.cleaned_data.get('recorrencia_sexta'),
                recorrencia_sabado=self.cleaned_data.get('recorrencia_sabado'),
                recorrencia_domingo=self.cleaned_data.get('recorrencia_domingo'),
                hora_fim=hora_fim,
            )

            if sala.tem_conflito_reserva(solicitacao):
                self.errors["data_inicio"] = ["Sala já está reservada para a data e hora especificadas."]

            if not sala.is_agendavel():
                self.errors["sala"] = ["Sala não está disponível para agendamento."]

        if not recorrencia or recorrencia == SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO:
            cleaned_data["recorrencia_segunda"] = False
            cleaned_data["recorrencia_terca"] = False
            cleaned_data["recorrencia_quarta"] = False
            cleaned_data["recorrencia_quinta"] = False
            cleaned_data["recorrencia_sexta"] = False
            cleaned_data["recorrencia_sabado"] = False
            cleaned_data["recorrencia_domingo"] = False
        elif not (
            cleaned_data["recorrencia_segunda"]
            or cleaned_data["recorrencia_terca"]
            or cleaned_data["recorrencia_quarta"]
            or cleaned_data["recorrencia_quinta"]
            or cleaned_data["recorrencia_sexta"]
            or cleaned_data["recorrencia_sabado"]
            or cleaned_data["recorrencia_domingo"]
        ):
            self.errors["recorrencia_segunda"] = ["Este tipo de recorrência exige a marcação de ao menos um dia da semana."]

        return cleaned_data

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.instance.notificar_cadastro()


class SolicitacaoReservaSalaAvaliarForm(forms.ModelFormPlus):
    avaliador = SpanField('Avaliador')
    data_avaliacao = SpanField('Data da Avaliação')
    fieldsets = ((None, {'fields': (('avaliador'), ('data_avaliacao'), ('status'), ('observacao_avaliador'))}),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avaliador'].widget.original_value = self.instance.avaliador
        self.fields['data_avaliacao'].widget.original_value = self.instance.data_avaliacao
        self.fields['data_avaliacao'].widget.label_value = localize(self.instance.data_avaliacao)
        self.fields['status'].widget.choices = ((SolicitacaoReservaSala.STATUS_DEFERIDA, 'Deferida'), (SolicitacaoReservaSala.STATUS_INDEFERIDA, 'Indeferida'))

    class Meta:
        model = SolicitacaoReservaSala
        fields = ('status', 'observacao_avaliador')

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            if cleaned_data.get('status') == SolicitacaoReservaSala.STATUS_DEFERIDA:
                solicitacao = self.instance
                sala = solicitacao.sala

                if sala.tem_conflito_reserva(solicitacao):
                    self.errors["status"] = ["Sala já está reservada para a data e hora especificadas."]
                    del cleaned_data['status']

            elif cleaned_data.get('status') == SolicitacaoReservaSala.STATUS_INDEFERIDA:
                if len(cleaned_data['observacao_avaliador'].strip()) == 0:
                    self._errors['observacao_avaliador'] = self.error_class(['A observação é obrigatória para a situação indeferida.'])
                    del cleaned_data['observacao_avaliador']

        return cleaned_data

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.instance.status == SolicitacaoReservaSala.STATUS_DEFERIDA:
            self.instance.gerar_reservas()

        self.instance.notificar_avaliacao()


class SolicitacaoReservaSalaCancelarForm(forms.ModelFormPlus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['justificativa_cancelamento'].required = True

    class Meta:
        model = SolicitacaoReservaSala
        fields = ('justificativa_cancelamento',)

    @transaction.atomic()
    def save(self, *args, **kwargs):
        self.instance.cancelada = True
        super().save(*args, **kwargs)
        for reserva in self.instance.reservasala_set.exclude(cancelada=True):
            reserva.cancelada_por = self.request.user
            reserva.justificativa_cancelamento = self.instance.justificativa_cancelamento
            reserva.cancelar(notificar=False)

        self.instance.notificar_cancelamento()


class IndisponibilizacaoSalaBuscarForm(forms.FormPlus):
    METHOD = 'GET'
    sala = forms.ModelChoiceField(label='Sala', queryset=Sala.ativas, required=False)

    def __init__(self, *args, **kwargs):
        indisponibilizacoes = kwargs.pop('indisponibilizacoes')
        super().__init__(*args, **kwargs)
        self.fields['sala'].queryset = Sala.ativas.filter(reservasala__indisponibilizacaosala__id__in=indisponibilizacoes.values_list('id', flat=True)).distinct()

    def processar(self, indisponibilizacoes):
        if self.is_valid():
            sala = self.cleaned_data.get('sala')
            if sala:
                indisponibilizacoes = indisponibilizacoes.filter(sala=sala)
        return indisponibilizacoes


class RegistrarIndisponibilizacaoSalaForm(forms.ModelFormPlus):
    registrado_por = SpanField('Registado por')
    data = SpanField('Data do Registro')
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo().all(), required=False)
    predio = forms.ChainedModelChoiceField(
        Predio.objects.all(), label='Prédio', empty_label='Selecione o Campus', required=False, obj_label='nome', form_filters=[('campus', 'uo_id')]
    )
    sala = forms.ChainedModelChoiceField(
        Sala.ativas, label='Sala', empty_label='Selecione o Prédio', obj_label='nome', form_filters=[('campus', 'predio__uo_id'), ('predio', 'predio_id')]
    )

    fieldsets = ((None, {'fields': (('registrado_por'), ('data'), ('campus'), ('predio'), ('sala'), ('data_inicio'), ('data_fim'), ('justificativa'))}),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['registrado_por'].widget.original_value = self.instance.usuario
        self.fields['data'].widget.original_value = self.instance.data
        self.fields['data'].widget.label_value = localize(self.instance.data)
        self.fields['campus'].queryset = (
            UnidadeOrganizacional.objects.uo()
            .filter(predio__sala__agendavel=True, predio__sala__ativa=True, predio__sala__avaliadores_de_agendamentos=self.request.user.id)
            .distinct()
        )
        self.fields['predio'].widget.queryset = Predio.objects.filter(sala__agendavel=True, sala__ativa=True, sala__avaliadores_de_agendamentos=self.request.user.id).distinct()
        self.fields['predio'].widget.initial = self.request.POST.get('predio')
        self.fields['sala'].widget.queryset = Sala.ativas.filter(agendavel=True, avaliadores_de_agendamentos=self.request.user.id).distinct()
        self.fields['sala'].widget.initial = self.request.POST.get('sala')

    class Meta:
        model = IndisponibilizacaoSala
        fields = ('sala', 'data_inicio', 'data_fim', 'justificativa')

    class Media:
        js = ('/static/comum/js/RegistrarIndisponibilizacaoSalaForm.js',)

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            data_inicio = cleaned_data.get("data_inicio")
            data_fim = cleaned_data.get("data_fim")
            data = self.instance.data
            sala = cleaned_data.get("sala")

            if data_fim < data_inicio:
                self.add_error("data_fim", "Data final deve ser maior ou igual a Data inicial.")

            if data_inicio < data:
                self.add_error("data_inicio", "Data e Hora inicial deve ser maior ou igual a Data/Hora da solicitação.")

            # RN1 Não deve existir duas agendas de salas na mesma data/hora.
            if sala.get_reservas(data_inicio, data_fim).exists():
                self.add_error("data_inicio", "Sala já está reservada para a data e hora especificadas, exclua antes a reserva.")

            # RN2 Requisições de reserva de sala na mesa data/hora será indeferida.
            if sala.get_solicitacoes_conflitantes(data_inicio, data_fim).exists():
                self.add_error("data_inicio", "Existem requisições de reserva para esta sala no período solicitado, indefira antes as requisições.")

            if not sala.is_agendavel():
                self.add_error("sala", "Sala não está disponível para agendamento.")

        return cleaned_data


class ReservaSalaCancelarForm(forms.ModelFormPlus):
    class Meta:
        model = ReservaSala
        fields = ('justificativa_cancelamento',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['justificativa_cancelamento'].required = True

    def cancelar(self):
        self.instance.cancelar()


class SalaIndicadoresForm(forms.FormPlus):
    METHOD = 'GET'

    inicio = forms.DateFieldPlus(label='Data Inicial', required=True)
    final = forms.DateFieldPlus(label='Data Final', required=True)
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=True)
    predio = forms.ChainedModelChoiceField(
        Predio.objects, label='Prédio', empty_label='Selecione o Campus', required=False, obj_label='nome', form_filters=[('campus', 'uo_id')]
    )


class ReservaInformarOcorrenciaForm(forms.ModelFormPlus):
    class Meta:
        model = ReservaSala
        fields = ('ocorreu', 'motivo_nao_ocorreu')

    def clean(self):
        cleaned_data = super().clean()
        ocorreu = cleaned_data.get('ocorreu')
        motivo_nao_ocorreu = cleaned_data.get('motivo_nao_ocorreu')
        if ocorreu == False and not motivo_nao_ocorreu:
            self.add_error('motivo_nao_ocorreu', 'Este campo é obrigatório no caso do evento não tiver ocorrido.')

        return cleaned_data


ARQUIVOS_EXTRATOR_CHOICES = (
    ('unidadeorganizacional', 'Unidades Organizacionais'),
    ('atividade', 'Atividades'),
    ('afastamentos', 'Afastamentos'),
    ('grupocargoemprego', 'Grupo dos Cargos Emprego'),
    ('cargoemprego', 'Cargos Emprego'),
    ('classe', 'Classes'),
    ('diplomalegal', 'Diplomas Legais'),
    ('estadocivil', 'Estados Cívís'),
    ('funcao', 'Funções'),
    ('grupoocorrencias', 'Grupo Ocorrências'),
    ('ocorrencias', 'Ocorrências'),
    ('jornadatrabalho', 'Jornadas de Trabalho'),
    ('nivelescolaridade', 'Níveis de Escolaridade'),
    ('pais', 'País'),
    ('regimejuridico', 'Regimes Jurídicos'),
    ('situacaoservidor', 'Situações do Servidor'),
    ('banco', 'Bancos'),
    ('rubrica', 'Rubricas'),
    ('titulacao', 'Titulações'),
    ('servidor1', 'Dados do Servidor(1)'),
    ('servidor2', 'Dados do Servidor(2)'),
    ('servidor3', 'Dados do Servidor(3)'),
    ('servidor4', 'Dados do Servidor(4)'),
    ('servidor5', 'Dados do Servidor(5)'),
    ('servidorafastamentos', 'Afastamentos dos Servidores'),
    ('historicoferias', 'Histórico de Férias dos Servidores'),
    ('historicoafastamentos', 'Histórico de Afastamentos dos Servidores'),
    ('historicofuncoes', 'Histórico de Funções dos Servidores'),
    ('ferias', 'Férias dos Servidores'),
    ('matriculasservidor', 'Matriculas dos Servidores'),
    ('pca', 'Provimentos dos Cargos dos Servidores'),
    ('posicionamentopca', 'Posicionamentos dos Provimentos dos Cargos dos Servidores'),
    ('historicosetor', 'Histórico dos Setores dos Servidores'),
)


class MacroForm(forms.Form):
    arquivos_extrator = MultipleChoiceField(
        label='Arquivos do Extrator', choices=ARQUIVOS_EXTRATOR_CHOICES, initial=[i[0] for i in ARQUIVOS_EXTRATOR_CHOICES], widget=CheckboxSelectMultiplePlus, required=True
    )


class MacroHistoricoPCAForm(forms.Form):
    servidores = MultipleModelChoiceFieldPlus(
        queryset=Servidor.objects.filter(matricula_sipe__isnull=False),
        label='Servidores',
        required=True,
        help_text="Escolha os Servidores para realizar a extração dos históricos do PCA",
    )


class ExcluirRegistroForm(forms.FormPlus):
    SUBMIT_LABEL = 'Excluir'
    senha = forms.CharFieldPlus(widget=PasswordInput, required=True, max_length=255)

    def clean_senha(self):
        if not self.cleaned_data['senha']:
            raise ValidationError('Preencha a senha para confirmar a exclusão.')
        if not authenticate(username=self.request.user.username, password=self.cleaned_data['senha']):
            raise ValidationError('Senha incorreta.')


class TipoCarteiraFuncionalForm(forms.ModelFormPlus):
    template = forms.ChoiceField(choices=TipoCarteiraFuncional.MODELOS_CHOICES, required=True)

    fieldsets = ((None, {'fields': (('nome'), ('template'), ('modelo'), ('ativo'))}),)

    class Meta:
        model = TipoCarteiraFuncional
        fields = ('nome', 'template')


class VinculoForm(forms.ModelFormPlus):
    pessoa = forms.ModelChoiceFieldPlus(Pessoa.objects)
    user = forms.ModelChoiceFieldPlus(User.objects)

    class Meta:
        model = Vinculo
        exclude = ()


class CancelarReservasPeriodoForm(forms.FormPlus):
    data_inicio = forms.DateFieldPlus(label='Data de Início do Cancelamento')
    data_termino = forms.DateFieldPlus(
        label='Data de Término do Cancelamento', required=False, help_text='Se você deseja cancelar as reservas de apenas um dia, não preencha este campo.'
    )
    justificativa = forms.CharField(label='Justificativa do Cancelamento', widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        if 'sala' in kwargs:
            self.sala = kwargs.pop('sala')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            data_inicio = cleaned_data.get('data_inicio')
            data_termino = cleaned_data.get('data_termino')
            if data_inicio < datetime.date.today():
                self.add_error('data_inicio', 'A Data de Início do Cancelamento deve ser maior ou igual a data atual.')

            if data_termino and data_termino < data_inicio:
                self.add_error('data_termino', 'Data de Término do Cancelamento deve ser maior ou igual a Data de Início do Cancelamento.')

        return cleaned_data

    def cancelar(self):
        data_inicio = self.cleaned_data.get('data_inicio')
        data_termino = self.cleaned_data.get('data_termino')
        justificativa = self.cleaned_data.get('justificativa')
        reservas = ReservaSala.deferidas.filter(sala=self.sala)
        if not data_termino:
            data_termino = data_inicio

        reservas = reservas.filter(data_inicio__date__gte=data_inicio, data_fim__date__lte=data_termino)
        for reserva in reservas:
            reserva.justificativa_cancelamento = justificativa
            reserva.cancelar()


class AuthenticationFormPlus(AuthenticationForm):
    recaptcha = ReCaptchaField(label='Verificação', required=False)

    def clean(self):
        user = User.objects.filter(username=self.cleaned_data.get('username')).first()
        if getattr(settings, "RECAPTCHA_PUBLIC_KEY", False) and user and user.login_attempts > 3 and not self.cleaned_data.get('recaptcha'):
            raise forms.ValidationError('Preencha o captcha.')
        super().clean()
        return self.cleaned_data


class ExibirQuadrosForm(forms.FormPlus):
    SUBMIT_LABEL = 'Exibir'
    quadros = forms.ModelMultipleChoiceField(IndexLayout.objects, label='Quadros Escondidos', required=False, widget=CheckboxSelectMultiplePlus())

    def __init__(self, *args, **kwargs):
        self.coluna = kwargs.pop('coluna')
        super().__init__(*args, **kwargs)
        self.fields['quadros'].queryset = IndexLayout.objects.filter(escondido=True, usuario=self.request.user)

    def processar(self, request):
        quadros = self.cleaned_data.get('quadros')
        for quadro in quadros:
            quadro.delete()
            IndexLayout.recarregar_layouts(request)


class CalendarioForm(forms.FormPlus):
    ano = forms.ModelChoiceField(label='Ano', queryset=Ano.objects, required=False)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Unidade Organizacional', empty_label='Todas', required=False)


class CategoriaNotificacaoForm(forms.ModelFormPlus):
    class Meta:
        model = CategoriaNotificacao
        exclude = ()


class DeviceForm(forms.ModelFormPlus):
    class Meta:
        model = Device
        fields = ('nickname',)


class UsuarioExternoForm(forms.FormPlus):
    cpf = forms.BrCpfField(label='CPF')
    nome = forms.CharFieldPlus(label='Nome Completo')
    email = forms.EmailField(label='Email')
    confirma_email = forms.EmailField(label='Confirmação de E-mail')
    justificativa = forms.ModelChoiceField(label='Perfil',
                                           queryset=JustificativaUsuarioExterno.objects.filter(ativo=True),
                                           required=True)

    def clean_confirma_email(self):
        email = self.cleaned_data.get('email').strip()
        confirma_email = self.cleaned_data.get('confirma_email').strip()
        if email != confirma_email:
            raise forms.ValidationError("E-mails informados não são iguais!")
        if UsuarioExterno.objects.filter(email=email).exists():
            raise forms.ValidationError("Existe um Usuário Externo cadastrado com este e-mail!")
        return self.cleaned_data['confirma_email']

    def clean(self):
        cpf = self.cleaned_data.get('cpf')
        if User.objects.filter(username=mask_numbers(cpf), is_active=False).exists():
            self.add_error('cpf', f"Existe um Usuário ativo cadastrado com o CPF {cpf}.")


class BolsistaChangeForm(forms.ModelFormPlus):
    cpf = forms.BrCpfField(label='CPF')
    nome = forms.CharFieldPlus(label='Nome Completo')
    email = forms.EmailField(label='Email')
    data_admissao = forms.DateFieldPlus(required=True, label='Data de Admissão')
    data_demissao = forms.DateFieldPlus(required=False, label='Data de Demissão')

    class Meta:
        model = Bolsista
        fields = ('cpf', 'nome', 'email', 'data_admissao', 'data_demissao')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cpf'].widget.attrs['readonly'] = 'readonly'


class BolsistaForm(forms.FormPlus):
    cpf = forms.BrCpfField(label='CPF')
    nome = forms.CharFieldPlus(label='Nome Completo')
    email = forms.EmailField(label='Email')
    confirma_email = forms.EmailField(label='Confirmação de E-mail')
    data_admissao = forms.DateFieldPlus(required=True, label='Data de Admissão')
    data_demissao = forms.DateFieldPlus(required=False, label='Data de Demissão')

    def clean_confirma_email(self):
        email = self.cleaned_data.get('email').strip()
        confirma_email = self.cleaned_data.get('confirma_email').strip()
        if email != confirma_email:
            raise forms.ValidationError("E-mails informados não são iguais!")
        if Bolsista.objects.filter(email=email).exists():
            raise forms.ValidationError("Existe um Usuário cadastrado com este e-mail!")
        return self.cleaned_data['confirma_email']

    def clean(self):
        cpf = self.cleaned_data.get('cpf')
        if User.objects.filter(username=mask_numbers(cpf)).exists():
            self.add_error('cpf', f"Existe um Usuário ativo cadastrado com o CPF {cpf}.")