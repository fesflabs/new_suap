from datetime import datetime, timedelta
from itertools import chain

import dateutil.parser
from ckeditor.widgets import CKEditorWidget
from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.forms.formsets import formset_factory
from django.utils.safestring import mark_safe
from reversion import revisions as reversion

from comum.models import Configuracao
from comum.utils import get_setor, get_todos_setores, tl
from djtools import forms
from djtools.forms.fields.captcha import ReCaptchaField
from djtools.forms.widgets import AutocompleteWidget, TextareaCounterWidget, RadioSelectPlus
from djtools.testutils import running_tests
from djtools.utils import get_datetime_now
from djtools.utils.pdf import check_pdf_with_pypdf, check_pdf_with_gs
from documento_eletronico.models import (
    RegistroAcaoDocumentoTexto,
    TipoDocumentoTexto,
    DocumentoTexto,
    ModeloDocumento,
    CompartilhamentoSetorPessoa,
    CompartilhamentoDocumentoPessoa,
    NivelPermissao,
    SolicitacaoAssinatura,
    RegistroAcaoDocumento,
    Classificacao,
    TipoDocumento,
    VinculoDocumentoTexto,
    AssinaturaDocumentoTexto,
    RestricaoAssinatura,
    DocumentoDigitalizado,
    TipoVinculoDocumento,
    SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa,
    CompartilhamentoDocumentoDigitalizadoPessoa,
    HipoteseLegal,
    DocumentoTextoPessoal,
    DocumentoDigitalizadoPessoal,
    TipoConferencia, Documento, NivelAcesso
)
from documento_eletronico.status import DocumentoStatus
from documento_eletronico.status import SolicitacaoStatus
from documento_eletronico.utils import get_setores_compartilhados, random_with_N_digits
from rh.models import CargoEmprego, Funcao, PessoaFisica, Pessoa
from rh.models import Setor, Servidor, UnidadeOrganizacional, Papel
from djtools.utils import SpanField, SpanWidget


class ConfiguracaoForm(forms.FormPlus):
    if 'centralservicos' in settings.INSTALLED_APPS:
        BaseConhecimento = apps.get_model('centralservicos', 'BaseConhecimento')
        base_conhecimento_permissao_acesso_documento = forms.ModelChoiceField(
            BaseConhecimento.objects.filter(ativo=True, visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA),
            label='Base de conhecimento com instruções de como dar permissão leitura e/ou criação/edição de documentos',
            required=False,
        )
    tipo_documento_requerimento = forms.ModelChoiceField(
        TipoDocumento.objects.filter(ativo=True),
        label='Tipo de Documento para Requerimento',
        required=False,
    )


# Form utilizado no cadastro de DocumentoTexto, para inclusão e edição dos dados básicos.
class DocumentoTextoForm(forms.ModelFormPlus):
    tipo = forms.ModelChoiceField(TipoDocumentoTexto.ativos, label='Tipo do Documento', required=True)
    modelo = forms.ModelChoiceField(ModeloDocumento.ativos.all(), label='Modelo', required=True)
    hipotese_legal = forms.ModelChoiceField(
        HipoteseLegal.objects.all(), label='Hipótese Legal', required=False, help_text='A hipótese legal só é obrigatória para documentos sigilosos ou restritos'
    )
    assunto = forms.CharField(widget=TextareaCounterWidget(max_length=255), label='Assunto')
    classificacao = forms.ModelMultiplePopupChoiceField(Classificacao.objects, label='Classificações', required=False, disabled=True)
    setor_dono = forms.ModelChoiceField(label='Setor Dono', queryset=Setor.objects.none(), required=True)

    instrucoes_gerais = forms.CharFieldPlus(label='', max_length=100000,
                                            required=False,
                                            widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': '30', 'cols': '80'}))

    ciencia_instrucoes_gerais = forms.BooleanField(widget=forms.CheckboxInput,
                                                   required=True,
                                                   label='Estou ciente sobre as instruções gerais.')

    class Meta:
        model = DocumentoTexto
        fields = ('tipo', 'modelo', 'nivel_acesso', 'hipotese_legal', 'setor_dono', 'assunto')

    class Media:
        js = ['/static/documento_eletronico/js/DocumentoTextoForm.js']

    def clean_nivel_acesso(self):
        nivel_acesso = self.cleaned_data.get('nivel_acesso')
        if self.instance.id:
            old_version = DocumentoTexto.objects.get(id=self.instance.id)
            self.instance.nivel_acesso = nivel_acesso
            if self.instance.nivel_acesso != old_version.nivel_acesso:
                self.instance.validar_auteracao_nivel_acesso(self.request.user)
        return nivel_acesso

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        edit_mode = bool(self.instance.pk)

        # Montando o combo com os setores pertinentes.
        if edit_mode and self.instance.estah_em_revisao:
            qs_setores_usuario = Setor.objects.filter(id=self.instance.setor_dono_id)
        else:
            qs_setores_usuario = get_setores_compartilhados(self.request.user, NivelPermissao.EDITAR)
        self.fields['setor_dono'].queryset = qs_setores_usuario

        # Se só tem um setor disponível, então ele já é logo setado no combobox.
        if qs_setores_usuario.count() == 1:
            self.fields['setor_dono'].initial = qs_setores_usuario[0]
            self.fields['setor_dono'].widget.original_value = qs_setores_usuario[0]

        if edit_mode:
            # Ajuste para impedir a edição do tipo de documento. Obs: Nesse caso se faz necessário colocar
            # "required = False" para que o form não reclame que a informaçãon não está fornecida, já que
            # ela está!
            self.fields['tipo'].initial = self.instance.modelo.tipo_documento_texto
            self.fields['tipo'].widget = forms.widgets.HiddenInput()
            self.fields['tipo'].required = False
            self.fields['tipo'].help_text = 'O tipo de documento não pode ser alterado'

        setor_dono_help_text = 'Se o setor desejado não está listado, solicite permissão ao chefe desse setor'
        base_conhecimento_permissao_acesso_documento_id = Configuracao.get_valor_por_chave('documento_eletronico', 'base_conhecimento_permissao_acesso_documento')
        if base_conhecimento_permissao_acesso_documento_id and 'centralservicos' in settings.INSTALLED_APPS:
            BaseConhecimento = apps.get_model('centralservicos', 'BaseConhecimento')
            base_conhecimento_permissao_acesso_documento = BaseConhecimento.objects.filter(id=base_conhecimento_permissao_acesso_documento_id).first()
            if base_conhecimento_permissao_acesso_documento:
                setor_dono_help_text += mark_safe(' (<a href="{}">link com instruções para o chefe</a>)'.format(base_conhecimento_permissao_acesso_documento.get_absolute_url()))
        self.fields['setor_dono'].help_text = setor_dono_help_text

        if 'processo_eletronico' in settings.INSTALLED_APPS:
            ConfiguracaoInstrucaoNivelAcesso = apps.get_model('processo_eletronico', 'ConfiguracaoInstrucaoNivelAcesso')

        conf_orientacao = ConfiguracaoInstrucaoNivelAcesso.get_orientacao()
        if conf_orientacao:
            self.fields['ciencia_instrucoes_gerais'].required = True
            self.fields['instrucoes_gerais'] = SpanField(widget=SpanWidget(), label='')
            self.fields['instrucoes_gerais'].widget.label_value = mark_safe('<br>{}'.format(conf_orientacao))
            self.fields['instrucoes_gerais'].widget.original_value = conf_orientacao
            self.fields['instrucoes_gerais'].required = False
        else:
            self.fields['ciencia_instrucoes_gerais'].widget = forms.HiddenInput()
            self.fields['ciencia_instrucoes_gerais'].required = False
            self.fields['instrucoes_gerais'].widget = forms.HiddenInput()

    def save(self, commit=True):
        if not self.instance.id:
            self.instance.data_criacao = datetime.now()
            self.instance.usuario_criacao = self.request.user

        self.instance.data_ultima_modificacao = datetime.now()
        self.instance.usuario_ultima_modificacao = self.request.user
        return super().save(commit)


class DocumentoTextoEditarCorpoForm(forms.ModelFormPlus):
    corpo = forms.CharField(widget=CKEditorWidget(config_name='default'), required=False)

    class Meta:
        model = DocumentoTexto
        fields = ('corpo',)

    def clean(self):
        self.instance.corpo = self.cleaned_data.get('corpo')

        # Os atributos "corpo" e "data_ultima_modificacao__isoformat" são atributos colocados "manualmente" na página.
        # Como não podem ser definidos no atributo "fields" do Meta, seu estado terá que ser mantido manualmente, em
        # caso de erro.
        #
        # O motivo pelo qual esses campos não podem ser definidos em "fields" do Meta são:
        # - corpo: por conta de ser um campo rico de texto.
        # - data_ultima_modificacao__isoformat: por ser "editable=false", o que impede dele ser definido no "fields"do Meta.
        # No caso trata-se de um campo hidden criado para guardar, sem exibir, a data da última modificação realizada no
        # momento em que o usuário carregou o documento para edição.
        #
        # Obs: Os campos definidos no atributo "fields" do Meta tem seu estado mantido no form pelo próprio Django.

        # O self.instance é um objeto Documento do jeito que está no banco de dados atualmente. Por isso aqui setamos
        # o valor do corpo com base no que o usuário está submetendo. Dando erro ou não, o corpo tem que ser mantido
        # da mesma forma como o usuário submeteu.
        self._verficar_data_ultima_modificacao()

        return self.cleaned_data

    def save(self, *args, **kwargs):
        # Atualizado os dados sobre a última modificação realizada antes do save().
        self.instance.data_ultima_modificacao = datetime.now()
        self.instance.usuario_ultima_modificacao = self.request.user
        return super().save(*args, **kwargs)

    def _verficar_data_ultima_modificacao(self):
        # Se data_ultima_modificacao atual (vinda do banco de dados) difere da data_ultima_modificacao quando o usuário
        # resgatou o objeto do banco para iniciar a edição...
        if self.data['data_ultima_modificacao__isoformat'] != self.instance.data_ultima_modificacao.isoformat():
            usuario_ultima_modificacao = self.instance.usuario_ultima_modificacao
            data_ultima_modificacao = self.instance.data_ultima_modificacao

            # Ajustando a data_ultima_modificacao para que ela se mantenha com o mesmo valor de quando o usuário carregou
            # a página de edição do documento pela primeira vez, mantendo assim o mesmo estado desse atributo. Isso vai
            # impedir que o usuário consiga burlar o controle de edição concorrente apenas clicando duas ou mais vezes
            # em "Salvar".
            self.instance.data_ultima_modificacao = dateutil.parser.parse(self.data['data_ultima_modificacao__isoformat'])
            #
            raise forms.ValidationError(
                'Este documento foi modificado por {} às {}. Copie as alterações realizadas '
                'e carregue novamente o documento.'.format(usuario_ultima_modificacao, data_ultima_modificacao.strftime('%d/%m/%Y - %H:%M'))
            )


class TipoDocumentoForm(forms.ModelFormPlus):
    class Meta:
        model = TipoDocumento
        fields = ('nome', 'sigla', 'ativo', 'permite_documentos_pessoais')


class TipoDocumentoTextoForm(forms.ModelFormPlus):
    cabecalho_padrao = forms.CharField(widget=CKEditorWidget(config_name='default'))
    rodape_padrao = forms.CharField(widget=CKEditorWidget(config_name='default'), required=False)

    class Meta:
        model = TipoDocumentoTexto
        fields = (
            'nome', 'sigla', 'tipo_sequencia', 'ativo',
            'vincular_pessoa', 'cabecalho_padrao', 'rodape_padrao',
            'permite_documentos_pessoais', 'permite_documentos_anexos'
        )

    class Media:
        js = ['/static/documento_eletronico/js/ckeditor_toolbar.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.instance.usa_sequencial_anual:
            self.fields['tipo_sequencia'].widget.attrs['readonly'] = True

    def clean_tipo_sequencia(self):
        tipo_sequencia = self.cleaned_data.get('tipo_sequencia')
        if self.instance.pk and not self.instance.usa_sequencial_anual:
            if tipo_sequencia != self.instance.tipo_sequencia:
                self.add_error('tipo_sequencia', 'A conversão entre os tipos de numeração não é permitido.')
        #
        return tipo_sequencia

    def clean_cabecalho_padrao(self):
        cabecalho_padrao = self.cleaned_data.get('cabecalho_padrao')
        if len(cabecalho_padrao) > 100 * 1024:
            raise ValidationError('Cabeçalho padrão muito grande')
        return cabecalho_padrao

    def clean_rodape_padrao(self):
        rodape_padrao = self.cleaned_data.get('rodape_padrao')
        if len(rodape_padrao) > 100 * 1024:
            raise ValidationError('Rodapé padrão muito grande')
        return rodape_padrao


class TipoDocumentoTextoAddForm(TipoDocumentoTextoForm):
    class Meta:
        model = TipoDocumentoTexto
        fields = (
            'nome', 'sigla', 'tipo_sequencia', 'ativo',
            'vincular_pessoa', 'cabecalho_padrao', 'rodape_padrao',
            'permite_documentos_pessoais', 'permite_documentos_anexos'
        )


class ModeloDocumentoForm(forms.ModelFormPlus):
    tipo_documento_texto = forms.ModelChoiceFieldPlus(TipoDocumentoTexto.ativos, label='Tipo do Documento', required=True)
    classificacao = forms.ModelMultiplePopupChoiceField(Classificacao.objects.all(), label='Classificações', required=False)

    fieldsets = (
        ('Dados Principais', {'fields': ('tipo_documento_texto', 'nome', 'classificacao')}),
        ('Níveis de Acesso Permitidos', {'fields': ('permite_nivel_acesso_sigiloso', 'permite_nivel_acesso_restrito', 'permite_nivel_acesso_publico')}),
        ('', {'fields': ('nivel_acesso_padrao',)}),
        ('', {'fields': ('ativo',)}),
    )

    class Meta:
        model = ModeloDocumento
        fields = (
            'nome',
            'tipo_documento_texto',
            'permite_nivel_acesso_sigiloso',
            'permite_nivel_acesso_restrito',
            'permite_nivel_acesso_publico',
            'nivel_acesso_padrao',
            'classificacao',
            'ativo',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classificacao'].queryset = Classificacao.podem_classificar.all()


class EditarModeloDocumentoForm(forms.ModelFormPlus):
    classificacao = forms.ModelMultiplePopupChoiceField(Classificacao.objects.all(), label='Classificações', required=False)

    class Meta:
        model = ModeloDocumento
        fields = (
            'nome',
            'tipo_documento_texto',
            'permite_nivel_acesso_sigiloso',
            'permite_nivel_acesso_restrito',
            'permite_nivel_acesso_publico',
            'nivel_acesso_padrao',
            'classificacao',
            'corpo_padrao',
            'ativo',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classificacao'].queryset = Classificacao.podem_classificar.all()


class GerenciarCompartilhamentoPessoaForm(forms.FormPlus):
    pessoas_permitidas_podem_ler = forms.MultipleModelChoiceFieldPlus(label='Servidores que podem ler', queryset=Servidor.objects.all(), required=False)
    pessoas_permitidas_podem_escrever = forms.MultipleModelChoiceFieldPlus(label='Servidores que podem editar', queryset=Servidor.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pessoas_permitidas_podem_ler'].initial = self.pessoas_permitidas.filter(nivel_permissao=NivelPermissao.LER)
        self.fields['pessoas_permitidas_podem_escrever'].initial = self.pessoas_permitidas.filter(nivel_permissao=NivelPermissao.EDITAR)
        self.compartilhamentos = ''
        self.descompartilhamentos = ''

    @transaction.atomic()
    def save(self):
        cleaned_data = self.cleaned_data

        self.adicionar_compartilhamento_pessoa(cleaned_data['pessoas_permitidas_podem_ler'], NivelPermissao.LER)
        self.adicionar_compartilhamento_pessoa(cleaned_data['pessoas_permitidas_podem_escrever'], NivelPermissao.EDITAR)

    def adicionar_compartilhamento_pessoa(self, pessoas_permitidas, nivel_permissao):
        pessoas_permitidas_a_remover = self.pessoas_com_acesso.exclude(pessoa_permitida__in=pessoas_permitidas)
        if pessoas_permitidas_a_remover.exists():
            self.__preparar_descompartilhamento_observacao(pessoas_permitidas_a_remover, self.get_model_pessoa(), nivel_permissao)
            pessoas_permitidas_a_remover.delete()

        pessoas_permitidas_a_adicionar = pessoas_permitidas.exclude(id__in=self.pessoas_com_acesso.values_list('pessoa_permitida_id', flat=True))
        if pessoas_permitidas_a_adicionar.exists():
            for pessoa_permitida_a_adicionar in pessoas_permitidas_a_adicionar:
                model = self.get_model_pessoa()
                model.pessoa_permitida = pessoa_permitida_a_adicionar
                model.nivel_permissao = nivel_permissao
                model.save()
            self.__preparar_compartilhamento_observacao(pessoas_permitidas_a_adicionar, self.get_model_pessoa(), nivel_permissao)

    def __preparar_compartilhamento_observacao(self, permitidos_a_adicionar, model, nivel_permissao):
        self.compartilhamentos += ' a(s) pessoa(s): ('
        self.compartilhamentos += ', '.join([str(permitido) for permitido in permitidos_a_adicionar])
        self.compartilhamentos += ') para {};'.format(dict(NivelPermissao.CHOICES)[nivel_permissao])

    def __preparar_descompartilhamento_observacao(self, permitidos_a_remover, model, nivel_permissao):
        self.descompartilhamentos += ' a(s) pessoa(s): ('
        self.descompartilhamentos += ', '.join([str(permitido.pessoa_permitida) for permitido in permitidos_a_remover])
        self.descompartilhamentos += ') para {};'.format(dict(NivelPermissao.CHOICES)[nivel_permissao])


class GerenciarCompartilhamentoForm(forms.FormPlus):
    qs_prestadores_servidores = PessoaFisica.objects.filter(eh_servidor=True) | PessoaFisica.objects.filter(eh_prestador=True)

    pessoas_permitidas_podem_ler = forms.MultipleModelChoiceFieldPlus(label='Servidores/Prestadores de Serviço que podem ler', queryset=qs_prestadores_servidores, required=False)
    pessoas_permitidas_podem_escrever = forms.MultipleModelChoiceFieldPlus(
        label='Servidores/Prestadores de Serviço que podem editar e ler', queryset=qs_prestadores_servidores, required=False
    )
    setores_permitidos_podem_ler = forms.MultipleModelChoiceFieldPlus(
        label='Setores que podem ler',
        queryset=Setor.objects.all(),
        required=False,
        help_text='Somente os servidores do(s) setor(es) selecionado(s) poderão ler documentos eletrônicos')
    setores_permitidos_podem_escrever = forms.MultipleModelChoiceFieldPlus(
        label='Setores que podem editar e ler',
        queryset=Setor.objects.all(),
        required=False,
        help_text='Somente os servidores do(s) setor(es) selecionado(s) poderão adicionar, operar e ler documentos eletrônicos')

    fieldsets = (
        ('Com Setores', {'fields': ('setores_permitidos_podem_ler', 'setores_permitidos_podem_escrever')}),
        ('Com Pessoas', {'fields': ('pessoas_permitidas_podem_ler', 'pessoas_permitidas_podem_escrever')}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pessoas_permitidas_podem_ler'].initial = self.pessoas_permitidas.filter(nivel_permissao=NivelPermissao.LER)
        self.fields['pessoas_permitidas_podem_escrever'].initial = self.pessoas_permitidas.filter(nivel_permissao=NivelPermissao.EDITAR)

        self.compartilhamentos = ''
        self.descompartilhamentos = ''

    @transaction.atomic()
    def save(self):
        cleaned_data = self.cleaned_data

        self.adicionar_compartilhamento_pessoa(cleaned_data['pessoas_permitidas_podem_ler'], NivelPermissao.LER)
        self.adicionar_compartilhamento_pessoa(cleaned_data['pessoas_permitidas_podem_escrever'], NivelPermissao.EDITAR)

        self.adicionar_compartilhamento_setores(cleaned_data['setores_permitidos_podem_ler'], NivelPermissao.LER)
        self.adicionar_compartilhamento_setores(cleaned_data['setores_permitidos_podem_escrever'], NivelPermissao.EDITAR)

        self._salvar_acesso()

    def get_model_pessoa(self):
        raise NotImplementedError

    def get_model_setor(self):
        raise NotImplementedError

    def adicionar_compartilhamento_pessoa(self, pessoas_permitidas, nivel_permissao):
        pessoas_permitidas_a_remover = self.pessoas_com_acesso.exclude(pessoa_permitida__in=pessoas_permitidas)
        if pessoas_permitidas_a_remover.exists():
            self.__preparar_descompartilhamento_observacao(pessoas_permitidas_a_remover, self.get_model_pessoa(), nivel_permissao)
            for pessoa_permitida_a_remover in pessoas_permitidas_a_remover:
                pessoa_permitida_a_remover.delete()

        pessoas_permitidas_a_adicionar = pessoas_permitidas.exclude(id__in=self.pessoas_com_acesso.values_list('pessoa_permitida_id', flat=True))
        if pessoas_permitidas_a_adicionar.exists():
            for pessoa_permitida_a_adicionar in pessoas_permitidas_a_adicionar:
                model = self.get_model_pessoa()
                model.pessoa_permitida = pessoa_permitida_a_adicionar
                model.nivel_permissao = nivel_permissao
                model.save()

            self.__preparar_compartilhamento_observacao(pessoas_permitidas_a_adicionar, self.get_model_pessoa(), nivel_permissao)

    def adicionar_compartilhamento_setores(self, setores_permitidos, nivel_permissao):

        setores_permitidos_a_adicionar = setores_permitidos
        pessoas = []
        for setor_permitido_a_adicionar in setores_permitidos_a_adicionar:
            for servidor in setor_permitido_a_adicionar.get_servidores(recursivo=False):
                model = self.get_model_pessoa()
                model.pessoa_permitida = servidor.pessoa_fisica
                model.nivel_permissao = nivel_permissao
                model.save()
                pessoas.append(servidor.pessoa_fisica)

        self.__preparar_compartilhamento_observacao(pessoas, self.get_model_pessoa(), nivel_permissao)

    def __preparar_compartilhamento_observacao(self, permitidos_a_adicionar, model, nivel_permissao):
        if model.__class__ in [CompartilhamentoDocumentoPessoa, CompartilhamentoSetorPessoa]:
            self.compartilhamentos += ' a(s) pessoa(s): ('

        self.compartilhamentos += ', '.join([str(permitido) for permitido in permitidos_a_adicionar])
        self.compartilhamentos += ') para {};'.format(dict(NivelPermissao.CHOICES)[nivel_permissao])

    def __preparar_descompartilhamento_observacao(self, permitidos_a_remover, model, nivel_permissao):
        if model.__class__ in [CompartilhamentoDocumentoPessoa, CompartilhamentoSetorPessoa]:
            self.descompartilhamentos += ' a(s) pessoa(s): ('
            self.descompartilhamentos += ', '.join([str(permitido.pessoa_permitida) for permitido in permitidos_a_remover])

        self.descompartilhamentos += ') para {};'.format(dict(NivelPermissao.CHOICES)[nivel_permissao])

    def _salvar_acesso(self):
        documento = None
        compartilhamentos = None
        descompartilhamentos = None

        if self.__class__ == GerenciarCompartilhamentoDocumentoForm:
            documento = self.documento
            compartilhamentos = 'Compartilhamento do documento com{}'.format(self.compartilhamentos)
            descompartilhamentos = 'Descompartilhamento do documento com{}'.format(self.descompartilhamentos)
        elif self.__class__ == GerenciarCompartilhamentoSetorForm:
            setor = self.setor
            compartilhamentos = 'Compartilhamento dos documentos do setor {} com{}'.format(setor, self.compartilhamentos)
            descompartilhamentos = 'Descompartilhado dos documentos do setor {} com{}'.format(setor, self.descompartilhamentos)

        user = self.request.user
        ip = self.request.META.get('REMOTE_ADDR', '')
        if self.compartilhamentos:
            RegistroAcaoDocumentoTexto.registrar_acao(documento, RegistroAcaoDocumento.TIPO_COMPARTILHAMENTO, user, ip, compartilhamentos)
        #
        if self.descompartilhamentos:
            RegistroAcaoDocumentoTexto.registrar_acao(documento, RegistroAcaoDocumento.TIPO_DESCOMPARTILHAMENTO, user, ip, descompartilhamentos)


class GerenciarCompartilhamentoSetorForm(GerenciarCompartilhamentoForm):
    CLASSNAME = "featured-form normal-label"

    def __init__(self, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        if 'setor' in kwargs:
            self.setor = kwargs.pop('setor')
        else:
            self.setor = get_setor(self.request.user)
        self.pessoas_permitidas = CompartilhamentoSetorPessoa.objects.filter(setor_dono=self.setor).values_list('pessoa_permitida_id', flat=True)
        super().__init__(*args, **kwargs)

        self.fields['setores_permitidos_podem_ler'].label = 'Setores que podem ler documentos do(a) {}'.format(self.setor)
        self.fields['setores_permitidos_podem_escrever'].label = 'Setores que podem adicionar, operar e ler documentos do(a) {}'.format(self.setor)

        self.fields['pessoas_permitidas_podem_ler'].label = 'Servidores/Prestadores de Serviço que podem ler documentos do(a) {}'.format(self.setor)
        self.fields['pessoas_permitidas_podem_escrever'].label = 'Servidores/Prestadores de Serviço que podem adicionar, operar e ler documentos do(a) {}'.format(self.setor)

    def get_model_pessoa(self):
        return CompartilhamentoSetorPessoa(setor_dono=self.setor)

    def adicionar_compartilhamento_pessoa(self, pessoas_permitidas, nivel_permissao):
        self.pessoas_com_acesso = CompartilhamentoSetorPessoa.objects.filter(setor_dono=self.setor, nivel_permissao=nivel_permissao, pessoa_permitida__isnull=False)
        super().adicionar_compartilhamento_pessoa(pessoas_permitidas, nivel_permissao)

    def adicionar_compartilhamento_setores(self, setores_permitidos, nivel_permissao):
        super().adicionar_compartilhamento_setores(setores_permitidos, nivel_permissao)

    def clean(self):
        cleaned_data = super().clean()
        pessoas_permitidas_podem_ler = cleaned_data.get('pessoas_permitidas_podem_ler')
        pessoas_permitidas_podem_escrever = cleaned_data.get('pessoas_permitidas_podem_escrever')
        setores_permitidos_podem_ler = cleaned_data.get('setores_permitidos_podem_ler')
        setores_permitidos_podem_escrever = cleaned_data.get('setores_permitidos_podem_escrever')

        for pessoa_permitida_pode_ler in pessoas_permitidas_podem_ler:
            # Se já estiver nas para ser incluida como pode escrever ignora ela das que podem ler
            if pessoa_permitida_pode_ler in pessoas_permitidas_podem_escrever:
                cleaned_data['pessoas_permitidas_podem_ler'] = pessoas_permitidas_podem_ler.exclude(id=pessoa_permitida_pode_ler.id)

        for setor_permitido_pode_ler in setores_permitidos_podem_ler:
            # Se já estiver nas para ser incluido como pode escrever ignora ele das que podem ler
            if setor_permitido_pode_ler in setores_permitidos_podem_escrever:
                cleaned_data['setores_permitidos_podem_ler'] = setores_permitidos_podem_ler.exclude(id=setor_permitido_pode_ler.id)

        return cleaned_data


class GerenciarCompartilhamentoDocumentoForm(GerenciarCompartilhamentoForm):
    def __init__(self, *args, **kwargs):
        self.documento = kwargs.pop('documento')
        self.pessoas_permitidas = CompartilhamentoDocumentoPessoa.objects.filter(documento=self.documento, solicitacao_assinatura__isnull=True).values_list('pessoa_permitida_id', flat=True)
        super().__init__(*args, **kwargs)
        # Compartilhamento de Documento:
        #  SIGILOSO: aparecem tanto a opção de compartilhar leitura e edição (só pessoa)
        # No caso de documentos pessoais temos apenas compartilhamento com pessoas
        if self.documento.eh_documento_pessoal or self.documento.nivel_acesso == DocumentoTexto.NIVEL_ACESSO_SIGILOSO:
            self.fields.pop('setores_permitidos_podem_ler')
            self.fields.pop('setores_permitidos_podem_escrever')
        if self.documento.eh_documento_pessoal:
            self.fieldsets = (('Com Pessoas', {'fields': ('pessoas_permitidas_podem_ler', 'pessoas_permitidas_podem_escrever')}),)

    def get_model_pessoa(self):
        return CompartilhamentoDocumentoPessoa(documento=self.documento)

    def adicionar_compartilhamento_pessoa(self, pessoas_permitidas, nivel_permissao):
        self.pessoas_com_acesso = CompartilhamentoDocumentoPessoa.objects.filter(documento=self.documento, nivel_permissao=nivel_permissao, pessoa_permitida__isnull=False, solicitacao_assinatura__isnull=True)
        super().adicionar_compartilhamento_pessoa(pessoas_permitidas, nivel_permissao)

    def adicionar_compartilhamento_setores(self, setores_permitidos, nivel_permissao):
        super().adicionar_compartilhamento_setores(setores_permitidos, nivel_permissao)

    @transaction.atomic()
    def save(self):
        user = self.request.user
        setor = get_setor(user)
        cleaned_data = self.cleaned_data
        # Compartilhamento de Documento:
        #  SIGILOSO: aparecem tanto a opção de compartilhar leitura e edição (só pessoa)
        if (self.documento.eh_documento_pessoal or self.documento.nivel_acesso == DocumentoTexto.NIVEL_ACESSO_SIGILOSO) and self.documento.usuario_criacao == user:
            self.adicionar_compartilhamento_pessoa(cleaned_data['pessoas_permitidas_podem_ler'], NivelPermissao.LER)
            self.adicionar_compartilhamento_pessoa(cleaned_data['pessoas_permitidas_podem_escrever'], NivelPermissao.EDITAR)

        elif (self.documento.nivel_acesso == DocumentoTexto.NIVEL_ACESSO_RESTRITO and self.documento.setor_dono == setor) or (
            self.documento.nivel_acesso == DocumentoTexto.NIVEL_ACESSO_PUBLICO
        ):
            self.adicionar_compartilhamento_pessoa(cleaned_data['pessoas_permitidas_podem_ler'], NivelPermissao.LER)
            self.adicionar_compartilhamento_pessoa(cleaned_data['pessoas_permitidas_podem_escrever'], NivelPermissao.EDITAR)

            self.adicionar_compartilhamento_setores(cleaned_data['setores_permitidos_podem_ler'], NivelPermissao.LER)
            self.adicionar_compartilhamento_setores(cleaned_data['setores_permitidos_podem_escrever'], NivelPermissao.EDITAR)

        self._salvar_acesso()

    def clean(self):
        """
            O clean verifica se o conjunto de permissoes fornecidas ao usuario constitui um conjunto valido.
            Um usuario com permissao de escrita concede permissao de leitura e escrita.
            A listas pessoas_permitidas_podem_ler e pessoas_permitidas_podem_escrever contem o conjunto atual
            de usuario com as permissoes de leitura e escrita respectivamente. O mesmo vale para as listas
            dos setores.
            Dado que o usuario pode tanto conceder uma permissao maior quanto menor, os testes devem comparar
            as listas do cleaned_data com os dados do banco de dados.

        """
        cleaned_data = super().clean()
        pessoas_permitidas_podem_ler = cleaned_data.get('pessoas_permitidas_podem_ler') or ()
        pessoas_permitidas_podem_escrever = cleaned_data.get('pessoas_permitidas_podem_escrever') or ()

        for pessoa_permitida_pode_ler in pessoas_permitidas_podem_ler:
            eh_documento_sigiloso = self.documento.nivel_acesso == DocumentoTexto.NIVEL_ACESSO_SIGILOSO
            if (
                not self.documento.eh_documento_pessoal
                and not eh_documento_sigiloso
                and self.documento.setor_dono.compartilhamentosetorpessoa_set.filter(pessoa_permitida=pessoa_permitida_pode_ler, nivel_permissao=NivelPermissao.LER).exists()
            ):
                self.add_error('pessoas_permitidas_podem_ler', '{} já tem permissão de Leitura aos documentos do setor.'.format(pessoa_permitida_pode_ler))

            elif (
                not self.documento.eh_documento_pessoal
                and not eh_documento_sigiloso
                and self.documento.setor_dono.compartilhamentosetorpessoa_set.filter(pessoa_permitida=pessoa_permitida_pode_ler, nivel_permissao=NivelPermissao.EDITAR).exists()
            ):
                self.add_error('pessoas_permitidas_podem_ler', '{} já tem permissão de Leitura e Edição aos documentos do setor.'.format(pessoa_permitida_pode_ler))

            # Se já não tiver sido incluido
            elif not self.documento.compartilhamento_pessoa_documento.filter(pessoa_permitida=pessoa_permitida_pode_ler, nivel_permissao=NivelPermissao.LER):
                # Uma pessoa possuia permissao de escrita e esta sendo rebaixada a apenas leitura, portanto, deve-se
                # verifica se a pessoa que esta pedindo acesso de leitura esta na lista das pessoas que mantem o status
                # de escrita. Se não estiver, deve-se verificar se ela ja possuia a permissão ou se esta sendo concedida
                # no momento.
                if pessoa_permitida_pode_ler in pessoas_permitidas_podem_escrever:
                    if self.documento.tem_permissao_estrita_leitura(pessoa_permitida_pode_ler):
                        self.add_error('pessoas_permitidas_podem_ler', '{} já tem permissão de Leitura.'.format(pessoa_permitida_pode_ler))

            # Se já estiver nas para ser incluida como pode escrever ignora ela das que podem ler
            if pessoa_permitida_pode_ler in pessoas_permitidas_podem_escrever:
                cleaned_data['pessoas_permitidas_podem_ler'] = pessoas_permitidas_podem_ler.exclude(id=pessoa_permitida_pode_ler.id)

        for pessoa_permitida_pode_escrever in pessoas_permitidas_podem_escrever:
            eh_documento_sigiloso = self.documento.nivel_acesso == DocumentoTexto.NIVEL_ACESSO_SIGILOSO
            if (
                not self.documento.eh_documento_pessoal
                and not eh_documento_sigiloso
                and self.documento.setor_dono.compartilhamentosetorpessoa_set.filter(
                    pessoa_permitida=pessoa_permitida_pode_escrever, nivel_permissao=NivelPermissao.EDITAR
                ).exists()
            ):
                self.add_error('pessoas_permitidas_podem_escrever', '{} já tem permissão de Leitura e Edição aos documentos do setor.'.format(pessoa_permitida_pode_escrever))

            # Se já não tiver sido incluido
            elif not self.documento.compartilhamento_pessoa_documento.filter(
                pessoa_permitida=pessoa_permitida_pode_escrever, nivel_permissao=NivelPermissao.EDITAR
            ) and self.documento.tem_permissao_editar(pessoa_permitida_pode_escrever.user):
                self.add_error('pessoas_permitidas_podem_escrever', '{} já tem permissão de Leitura e Edição.'.format(pessoa_permitida_pode_escrever))

        if self.documento.nivel_acesso == DocumentoTexto.NIVEL_ACESSO_SIGILOSO:
            cleaned_data['setores_permitidos_podem_ler'] = []
            cleaned_data['setores_permitidos_podem_escrever'] = []

        return cleaned_data


class ListarDocumentosForm(forms.FormPlus):
    METHOD = 'GET'

    pesquisa = forms.CharField(label='Por Número/Conteúdo:', required=False)
    tipo = forms.ModelChoiceField(label='Por Tipo:', required=False, queryset=TipoDocumentoTexto.objects.all(), empty_label='Todos')
    campus = forms.ModelChoiceField(label='Por Campus:', required=False, queryset=UnidadeOrganizacional.objects.suap().all(), empty_label='Todos')
    setor = forms.ChainedModelChoiceField(Setor.objects.all(), label='Por Setor:', empty_label='Todos', required=False, obj_label='sigla', form_filters=[('campus', 'uo_id')])
    data_criacao = forms.DateFieldPlus(label='Por Data de Criação', required=False)
    ano = forms.IntegerField(label='Filtrar por Ano', widget=forms.Select())
    mes = forms.MesField(label='Filtrar por Mês:', required=False, choices=[], empty_label="Todos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ano_limite = get_datetime_now().year
        ANO_CHOICES = [(ano, '{}'.format(ano)) for ano in range(ano_limite, 2015, -1)]
        self.fields['ano'].widget.choices = ANO_CHOICES

        # Se há um parâmetro de nome "setores" enão não há necessidade dos filtros
        # por campus e/ou setor.
        if self.request.GET.get('setores'):
            del self.fields['setor']
            del self.fields['campus']

    def filtrar_documentos(self, retorno, aplicar_filtro_setor_dono=True):
        params = self.request.GET.dict()
        order_str = ''
        if self.is_valid():
            cleaned_data = self.cleaned_data

            campus = cleaned_data.get('campus')
            if campus:
                retorno = retorno.filter(setor_dono__uo=campus)

            if aplicar_filtro_setor_dono:
                setores = self.request.GET.get('setores')
                if setores:
                    try:
                        retorno = retorno.filter(setor_dono=setores)
                    except Exception:
                        if setores == 'todos_setores_usuario':
                            retorno = retorno.filter(setor_dono__in=get_todos_setores(self.request.user))
                else:
                    setor = cleaned_data.get('setor')
                    if setor:
                        retorno = retorno.filter(setor_dono=setor)

            tipo = cleaned_data.get('tipo')
            if tipo:
                retorno = retorno.filter(modelo__tipo_documento_texto=tipo)

            data_criacao = cleaned_data.get('data_criacao')
            if data_criacao:
                retorno = retorno.filter(data_criacao__year=data_criacao.year, data_criacao__month=data_criacao.month, data_criacao__day=data_criacao.day)

            ano = cleaned_data.get('ano')
            mes = cleaned_data.get('mes')
            if not data_criacao and ano != 0:
                retorno = retorno.filter(data_criacao__year=ano)

                mes = self.cleaned_data.get('mes', None)
                if mes and mes != 0:
                    retorno = retorno.filter(data_criacao__month=mes)

            pesquisa = cleaned_data.get('pesquisa')
            if pesquisa:
                filtro_identificador = (
                    retorno.filter(identificador_tipo_documento_sigla__icontains=pesquisa)
                    | retorno.filter(identificador_numero__icontains=pesquisa)
                    | retorno.filter(identificador_ano__icontains=pesquisa)
                    | retorno.filter(identificador_setor_sigla__icontains=pesquisa)
                )
                filtro_assunto = retorno.filter(assunto__icontains=pesquisa)
                filtro_cabecalho = retorno.filter(cabecalho__icontains=pesquisa)
                filtro_corpo = retorno.filter(corpo__icontains=pesquisa)
                filtro_rodape = retorno.filter(rodape__icontains=pesquisa)
                retorno = filtro_identificador | filtro_cabecalho | filtro_corpo | filtro_rodape | filtro_assunto

            if "order_by" in params:
                order_str = params.pop('order_by', '')
                order_tratado = order_str.replace(' ', '')
                if order_tratado[0] == '-':
                    order_tratado = order_tratado.replace(',', ',-')

                retorno = retorno.order_by(*order_tratado.split(','))
        else:
            retorno = retorno.none()
        return retorno, params, order_str


class ListarDocumentosTextoForm(ListarDocumentosForm):
    fieldsets = (('', {'fields': ('campus', 'setor', 'tipo', 'data_criacao', 'ano', 'mes', 'pesquisa')}),)

    def __init__(self, *args, **kwargs):
        self.exceto_documento = None
        if 'exceto_documento' in kwargs:
            self.exceto_documento = kwargs.pop('exceto_documento')
        super().__init__(*args, **kwargs)
        self.fields['campus'].required = True
        self.fields['setor'].required = True

    def processar(self):
        request = self.request
        retorno = DocumentoTexto.objects.by_user(self.request.user).defer('cabecalho', 'rodape', 'corpo')
        todos, params, order_str = self.filtrar_documentos(retorno)
        order_by = todos.query.order_by
        if not order_by:
            order_by = ['-data_criacao', 'modelo__tipo_documento_texto__nome', 'identificador_setor_sigla']

        documentos = retorno.filter(id__in=todos).order_by(*order_by)
        documentos_compartilhados = retorno.compartilhados(request.user).filter(id__in=todos).order_by(*order_by)

        if self.exceto_documento:
            documentos = documentos.exclude(pk=self.exceto_documento.id)

        return documentos, documentos_compartilhados, params, order_str


class AuthenticationForm(forms.FormPlus):
    senha = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        user = self.request.user
        senha = self.cleaned_data.get('senha')
        usuario_autenticado = None
        if senha:
            usuario_autenticado = authenticate(username=user.username, password=senha)

        if not usuario_autenticado or usuario_autenticado != user:
            self.add_error('senha', 'Senha não confere.')

        return self.cleaned_data


class AuthenticationGovBRForm(forms.FormPlus):
    codigo_verificacao = forms.CharField(help_text="Código enviado para seu aplicativo Gov.BR!")
    EXTRA_BUTTONS = [dict(type='button', value='Enviar Novo Código', name='enviar_novo_codigo_govbr', onclick='enviar_codigo_verificacao_govbr();')]

    class Media:
        js = ['/static/documento_eletronico/js/AuthenticationGovBRForm.js']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

    def clean(self):
        cod_verificacao_ = self.cleaned_data.get('codigo_verificacao')

        if not self.request.session.get('autenticou_com_govbr', False):
            self.add_error('codigo_verificacao', 'Não autenticado com Gov.BR')

        if not self.request.session.get('confiabilidade_govbr', 0) in ["2", "3"]:  # níveis  2 - prata e 3 - ouro
            raise forms.ValidationError("Sua conta Gov.BR não possui o nível Prata que é o mínimo exigido para assinar documentos no SUAP. Acesse o seu aplicativo Gov.BR para atualizar seu nível de confiabilidade!")

        if not cache.get(f'govbr_check_{self.request.user.get_vinculo().id}', None):
            self.gerar_codigo_verificacao()
            self.add_error('codigo_verificacao', 'Código de Verificação Expirou. Foi gerado um novo código e enviado para o App Gov.BR!')

        if int(cod_verificacao_) != cache.get(f'govbr_check_{self.request.user.get_vinculo().id}'):
            self.add_error('codigo_verificacao', 'Código de Verificação não confere!')

        return self.cleaned_data

    def gerar_codigo_verificacao(self, force=False):
        # API NOTIFICA GOV BR
        API_KEY_NOTIFICA_GOVBR = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'api_key_notifica_govbr') or "balcao_digital-c4764905-0bb2-4259-ae69-cc8efa2f7402-12ed59cf-b52b-4655-b0c1-242858612cc5"
        TEMPLATE_PADRAO_SUAP_APP_GOVBR = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'id_template_notifica_padrao_suap_app_govbr') or "4c4e7279-755e-40e9-8040-f0cd0b64c48e"
        HABILITAR_NOTIFICA_GOVBR = Configuracao.get_valor_por_chave('catalogo_provedor_servico',
                                                                    'habilitar_notifica_govbr') or False

        if not settings.DEBUG and not HABILITAR_NOTIFICA_GOVBR:
            raise forms.ValidationError(
                'Não é possível enviar o código de verificação pois a integração do SUAP com a Plataforma Notifica está desativada!')

        if not cache.get(f'govbr_check_{self.request.user.get_vinculo().id}', None) or force:
            self.codigo_verificacao = random_with_N_digits(5)
            cache.set(f'govbr_check_{self.request.user.get_vinculo().id}', self.codigo_verificacao, 300)
            mensagem_app_govbr = f"Código de verificação - SUAP/IFRN: {self.codigo_verificacao}"
            try:
                from notifications_python_client.notifications import NotificationsAPIClient
                cliente_notifica_govbr = NotificationsAPIClient(API_KEY_NOTIFICA_GOVBR)
                cpf = self.request.user.get_profile().cpf.replace('.', '').replace('-', '')
                cliente_notifica_govbr.send_app_govbr_cpf_notification(
                    cpf=cpf,
                    template_id=TEMPLATE_PADRAO_SUAP_APP_GOVBR,
                    personalisation={'mensagem': mensagem_app_govbr, })
            except Exception:
                raise forms.ValidationError('Houve um erro ao enviar código de verificação, certifique-se que possui o aplicativo Gov.BR instalado!')
            if settings.DEBUG:
                print(f"Código: {self.codigo_verificacao}")


class SolicitacaoAssinaturaForm(forms.FormPlus):
    # TODO: Mudar nome para servidor_solicitado
    solicitacao = forms.ModelChoiceFieldPlus(queryset=PessoaFisica.objects, required=True, widget=AutocompleteWidget(search_fields=PessoaFisica.SEARCH_FIELDS), label='Pessoa')

    def __init__(self, *args, **kwargs):
        self.documento = kwargs.pop('documento')
        self.solicitado = None
        super().__init__(*args, **kwargs)
        self.solicitacao = self.get_solicitacao_balizadora()

        # Se existe alguma solicitação balizadora, o form será exibido com os dados do servidor solicitado apenas a
        # título de informação. Esse form está sendo usado em conjunto com outro form, que exibe as solicitações de
        # assinatura complementares.

        if self.solicitacao:
            self.solicitado = self.solicitacao.solicitado
            #
            self.fields['solicitacao'].widget = forms.TextInput()
            self.fields['solicitacao'].initial = str(self.solicitacao.solicitado)
            self.fields['solicitacao'].widget.attrs.update(readonly='readonly')
            self.fields['solicitacao'].widget.attrs.update(disabled='disabled')
            self.fields['solicitacao'].required = False
        else:
            data_para_maioridade = datetime.now() - timedelta(days=365 * 18)
            self.fields['solicitacao'].queryset = (
                self.fields['solicitacao'].queryset.filter(
                    Q(eh_aluno=False, papel__isnull=False) | Q(eh_aluno=True, aluno_edu_set__situacao__ativo=True,
                                                               aluno_edu_set__pessoa_fisica__nascimento_data__lte=data_para_maioridade)).distinct()
            )

    def get_solicitacao_balizadora(self):
        if self.documento.possui_assinatura():
            return self.documento.get_solicitacao_balizadora()
        else:
            return SolicitacaoAssinatura.objects.filter(~Q(status=SolicitacaoStatus.STATUS_INDEFERIDA), documento=self.documento, condicionantes__isnull=True).first()

    def get_solicitacao(self):
        return self.solicitado

    def clean_solicitacao(self):
        if not self['solicitacao'].html_name in self.data:
            self.cleaned_data['solicitacao'] = self.solicitado
        return self.cleaned_data['solicitacao']


class SolicitacaoAssinaturaFormSet(forms.FormPlus):
    solicitacao = forms.ModelChoiceFieldPlus(queryset=PessoaFisica.objects, required=True, widget=AutocompleteWidget(search_fields=PessoaFisica.SEARCH_FIELDS), label='Pessoa')

    ordem = forms.IntegerField(required=True, min_value=1, initial=1, help_text='Use um mesmo número de ordem para realizar solicitações simultâneas.')

    class Media:
        js = ('comum/js/jquery.formset.js',)

    def __init__(self, *args, **kwargs):
        self.documento = kwargs.pop('documento')
        super().__init__(*args, **kwargs)
        self.fields['solicitacao'].queryset = (
            self.fields['solicitacao'].queryset.filter(Q(eh_aluno=False, papel__isnull=False) | Q(eh_aluno=True, aluno_edu_set__situacao__ativo=True)).distinct()
        )

    def clean(self):
        solicitado = self.cleaned_data.get('solicitacao', None)
        documento = self.documento
        if solicitado and AssinaturaDocumentoTexto.objects.filter(assinatura__pessoa=solicitado, documento=documento).exists():
            self.add_error('solicitacao', "{} já assinou o documento.".format(solicitado))
        return self.cleaned_data


SolicitacaoComplementaresFormSet = formset_factory(SolicitacaoAssinaturaFormSet, can_delete=True)


class SolicitacaoAssinaturaComAnexacaoForm(forms.FormPlus):
    # TODO: Mudar nome para servidor_solicitado
    solicitacao = forms.ModelChoiceFieldPlus(queryset=PessoaFisica.objects, required=True, widget=AutocompleteWidget(search_fields=PessoaFisica.SEARCH_FIELDS), label='Pessoa')

    if 'processo_eletronico' in settings.INSTALLED_APPS:
        Processo = apps.get_model('processo_eletronico', 'Processo')
        processo_para_anexar = forms.ModelChoiceFieldPlus(queryset=Processo.objects, required=True, widget=AutocompleteWidget(), label='Anexar ao Processo')

    # Dados para encaminhar para setor
    TIPO_BUSCA_SETOR_CHOICE = (('sem_despacho', 'Sem despacho'), ('com_despacho', 'Com despacho'))

    tipo_busca_encaminhar = forms.ChoiceField(widget=RadioSelectPlus(), required=False, choices=TIPO_BUSCA_SETOR_CHOICE, label="Encaminhar Processo")

    destinatario_setor_autocompletar = forms.ModelChoiceField(label="Setor de Destino do Trâmite", queryset=Setor.objects, required=False, widget=AutocompleteWidget())

    despacho_corpo = forms.CharField(label="Despacho do Trâmite", required=False, widget=forms.Textarea())

    papel = forms.ModelChoiceField(label='Perfil', required=False, queryset=Papel.objects.none())
    senha = forms.CharFieldPlus(label='Senha', required=False, widget=forms.PasswordInput())

    class Media:
        js = ('documento_eletronico/js/SolicitarAssinaturaComAnexacao.js',)

    def __init__(self, *args, **kwargs):
        self.documento = kwargs.pop('documento')
        self.solicitado = None
        super().__init__(*args, **kwargs)
        self.solicitacao = self.get_solicitacao_balizadora()

        # Se existe alguma solicitação balizadora, o form será exibido com os dados do servidor solicitado apenas a
        # título de informação. Esse form está sendo usado em conjunto com outro form, que exibe as solicitações de
        # assinatura complementares.

        if self.solicitacao:
            self.solicitado = self.solicitacao.solicitado
            #
            self.fields['solicitacao'].widget = forms.TextInput()
            self.fields['solicitacao'].initial = str(self.solicitacao.solicitado)
            self.fields['solicitacao'].widget.attrs.update(readonly='readonly')
            self.fields['solicitacao'].widget.attrs.update(disabled='disabled')
            self.fields['solicitacao'].required = False
        else:
            self.fields['solicitacao'].queryset = (
                self.fields['solicitacao'].queryset.filter(Q(eh_aluno=False, papel__isnull=False) | Q(eh_aluno=True, aluno_edu_set__situacao__ativo=True)).distinct()
            )

        vinculo = self.request.user.get_relacionamento()
        self.fields['papel'].queryset = vinculo.papeis_ativos

    def get_destino(self):
        return self.cleaned_data.get('destinatario_setor_autocompletar', None)

    def get_solicitacao_balizadora(self):
        if self.documento.possui_assinatura():
            return self.documento.get_solicitacao_balizadora()
        else:
            return SolicitacaoAssinatura.objects.filter(~Q(status=SolicitacaoStatus.STATUS_INDEFERIDA), documento=self.documento, condicionantes__isnull=True).first()

    def get_solicitacao(self):
        return self.solicitado

    def clean_solicitacao(self):
        if not self['solicitacao'].html_name in self.data:
            self.cleaned_data['solicitacao'] = self.solicitado
        return self.cleaned_data['solicitacao']

    def clean_senha(self):
        senha = self.cleaned_data['senha']
        if senha:
            usuario_autenticado = authenticate(username=self.request.user.username, password=senha)
            if not usuario_autenticado:
                raise forms.ValidationError('Senha inválida')
        return self.cleaned_data.get('senha')

    def clean(self):
        processo_anexar = self.cleaned_data.get('processo_para_anexar', None)
        if not processo_anexar:
            self.errors['processo_para_anexar'] = forms.ValidationError(
                ['Nenhum processo foi selecionado. Por favor, indique o processo ao qual o ' 'presente processo deve ser anexado.']
            )
        else:
            if processo_anexar.esta_finalizado():
                self.errors['processo_para_anexar'] = forms.ValidationError(['O processo {} encontra-se finalizado e não pode receber novos documentos.'.format(processo_anexar)])
            if processo_anexar.tem_solicitacoes_assinatura_com_tramite_pendentes():
                self.errors['processo_para_anexar'] = forms.ValidationError(
                    ['O processo {} não pode receber novos anexos pois possui solicitações de assinatura com ' 'trâmites pendentes.'.format(processo_anexar)]
                )
            if processo_anexar.eh_privado() and self.get_destino():
                self.errors['processo_para_anexar'] = forms.ValidationError(
                    ['O processo {} não pode tramitar para um setor pois possui nível de acesso ' 'privado.'.format(processo_anexar)]
                )
            if not processo_anexar.esta_nos_meus_setores(self.request.user):
                self.errors['processo_para_anexar'] = forms.ValidationError(['Não é possível adicionar documentos a um processo que não está em seus setores.'])
        if self.is_tipo_busca_com_despacho() and not self.cleaned_data.get('despacho_corpo'):
            self._errors['despacho_corpo'] = forms.ValidationError(['É obrigatório informar o despacho.'])
        if self.is_tipo_busca_com_despacho() and not self.cleaned_data.get('papel'):
            self._errors['papel'] = forms.ValidationError(['É obrigatório informar um papel.'])
        if self.is_tipo_busca_com_despacho() and not self.cleaned_data.get('senha'):
            self._errors['senha'] = forms.ValidationError(['É obrigatório informar uma senha.'])
        return self.cleaned_data

    def is_tipo_busca_sem_despacho(self):
        return self.cleaned_data.get('tipo_busca_encaminhar') == 'sem_despacho'

    def is_tipo_busca_com_despacho(self):
        return self.cleaned_data.get('tipo_busca_encaminhar') == 'com_despacho'


class SolicitacaoAssinaturaComAnexacaoFormSet(forms.FormPlus):
    solicitacao = forms.ModelChoiceFieldPlus(queryset=PessoaFisica.objects, required=True, widget=AutocompleteWidget(search_fields=PessoaFisica.SEARCH_FIELDS), label='Pessoa')

    ordem = forms.IntegerField(required=True, min_value=1, initial=1, help_text='Use um mesmo número de ordem para realizar solicitações simultâneas.')

    class Media:
        js = ('comum/js/jquery.formset.js',)

    def __init__(self, *args, **kwargs):
        self.documento = kwargs.pop('documento')
        super().__init__(*args, **kwargs)
        self.fields['solicitacao'].queryset = (
            self.fields['solicitacao'].queryset.filter(Q(eh_aluno=False, papel__isnull=False) | Q(eh_aluno=True, aluno_edu_set__situacao__ativo=True)).distinct()
        )

    def clean(self):
        solicitado = self.cleaned_data.get('solicitacao', None)
        documento = self.documento
        if solicitado and AssinaturaDocumentoTexto.objects.filter(assinatura__pessoa=solicitado, documento=documento).exists():
            self.add_error('solicitacao', "{} já assinou o documento.".format(solicitado))
        return self.cleaned_data


SolicitacaoComplementaresComAnexacaoFormSet = formset_factory(SolicitacaoAssinaturaComAnexacaoFormSet, can_delete=True)


class SolicitacaoRevisaoForm(forms.FormPlus):
    revisor = forms.ModelChoiceFieldPlus(queryset=Servidor.objects, required=True, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))
    observacao = forms.CharField(label="Observação", widget=forms.Textarea, required=False)


class RevisarDocumentoForm(forms.FormPlus):
    notas_revisor = forms.CharField(label="Observação", widget=forms.Textarea, required=False)


class AutenticacaoDocumento(forms.FormPlus):
    codigo_verificador = forms.IntegerField(label='Código Verificador')
    codigo_autenticacao = forms.CharField(label='Código de Autenticação', max_length=10)

    def __init__(self, *args, **kwargs):
        codigo_verificador = kwargs.pop('codigo_verificador')
        codigo_autenticacao = kwargs.pop('codigo_autenticacao')
        super().__init__(*args, **kwargs)
        self.fields['codigo_verificador'].initial = codigo_verificador
        self.fields['codigo_autenticacao'].initial = codigo_autenticacao
        if not settings.DEBUG:
            self.fields['recaptcha'] = ReCaptchaField(label='')


class AutenticacaoDocumentoTexto(AutenticacaoDocumento):
    recaptcha = ReCaptchaField(label='')

    def processar(self):
        cleaned_data = self.cleaned_data
        codigo_verificador = cleaned_data.get('codigo_verificador')
        codigo_autenticacao = cleaned_data.get('codigo_autenticacao')
        documento = DocumentoTexto.objects.filter(id=codigo_verificador)
        if not documento:
            documento = DocumentoTextoPessoal.objects.filter(id=codigo_verificador)
        if documento.exists():
            documento = documento.latest('id')
            if documento.codigo_autenticacao == codigo_autenticacao:
                return documento

        return None


class AutenticacaoDocumentoDigitalizado(AutenticacaoDocumento):
    def processar(self):
        cleaned_data = self.cleaned_data
        codigo_verificador = cleaned_data.get('codigo_verificador')
        codigo_autenticacao = cleaned_data.get('codigo_autenticacao')
        documento = DocumentoDigitalizado.objects.filter(id=codigo_verificador)
        if documento.exists():
            documento = documento.latest('id')
            if documento.codigo_autenticacao == codigo_autenticacao:
                return documento

        return None


class RejeitarSolicitacaoAssinaturaForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoAssinatura
        fields = ('justificativa_rejeicao',)

    def save(self, *args, **kwargs):
        self.instance.data_resposta = get_datetime_now()
        self.instance.indeferir_solicitacao()
        return super().save(*args, **kwargs)


class PapelForm(forms.FormPlus):
    papel = forms.ModelChoiceField(label='Perfil', queryset=Papel.objects.none(), required=True)
    SUBMIT_LABEL = 'Assinar'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'request'):
            self.request = tl.get_request()

        vinculo = self.request.user.get_relacionamento()
        self.fields['papel'].queryset = vinculo.papeis_ativos
        if vinculo.papeis_ativos.count() == 1:
            self.fields['papel'].initial = vinculo.papeis_ativos.first().id


class AssinarDocumentoForm(AuthenticationForm, PapelForm):
    SUBMIT_LABEL = 'Assinar Documento'


class AssinarDocumentoGovBRForm(AuthenticationGovBRForm, PapelForm):
    SUBMIT_LABEL = 'Assinar Documento - Gov.BR'


class GeradorIdentificadorDocumentoForm(forms.FormPlus):
    SUBMIT_LABEL = 'Definir Identificador'
    identificador_tipo_documento_sigla = forms.CharFieldPlus(label='Sigla do Tipo de Documento', max_length=50, required=True)
    identificador_numero = forms.IntegerField(label='Número', required=True)
    identificador_ano = forms.IntegerField(label='Ano', required=True)
    identificador_setor_sigla = forms.CharFieldPlus(label='Sigla do Setor', max_length=100, required=True)

    def __init__(self, *args, **kwargs):
        self.documento_id = kwargs.pop('documento_id')
        documento = DocumentoTexto.objects.get(pk=self.documento_id)

        super().__init__(*args, **kwargs)
        identificador_tipo_documento_sigla, identificador_numero, identificador_ano, identificador_setor_sigla = documento.get_sugestao_identificador_definitivo(
            tipo_documento_texto=documento.modelo.tipo_documento_texto, setor_dono=documento.setor_dono
        )
        #
        self.fields['identificador_tipo_documento_sigla'].initial = identificador_tipo_documento_sigla
        self.fields['identificador_tipo_documento_sigla'].widget.attrs['readonly'] = True
        self.fields['identificador_tipo_documento_sigla'].required = True

        self.fields['identificador_numero'].initial = identificador_numero
        self.fields['identificador_numero'].widget.attrs['readonly'] = True
        self.fields['identificador_numero'].required = True

        if documento.usa_sequencial_anual:
            self.fields['identificador_ano'].initial = identificador_ano
            self.fields['identificador_ano'].widget.attrs['readonly'] = True
            self.fields['identificador_ano'].required = True
        else:
            del self.fields['identificador_ano']

        #
        self.fields['identificador_setor_sigla'].initial = identificador_setor_sigla
        self.fields['identificador_setor_sigla'].widget.attrs['readonly'] = True
        self.fields['identificador_setor_sigla'].required = True

    def clean(self):
        return super().clean()


class VinculoDocumentoTextoForm(forms.ModelFormPlus):
    tipo_vinculo_documento = forms.ModelChoiceField(label='Tipo de Vínculo', queryset=TipoVinculoDocumento.objects, widget=forms.Select)
    documento_texto_alvo = forms.ModelChoiceFieldPlus(
        queryset=DocumentoTexto.objects,
        label='Documento Alvo',
        required=True,
        help_text='Informa o identificador do documento. Obs: Somente serão listados documentos ASSINADOS ou FINALIZADOS e que você tem acesso.',
    )

    class Meta:
        model = VinculoDocumentoTexto
        fields = ['documento_texto_base', 'tipo_vinculo_documento', 'documento_texto_alvo']

    def __init__(self, request, documento_texto_base, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['documento_texto_base'] = forms.ModelChoiceField(
            queryset=DocumentoTexto.objects, widget=AutocompleteWidget(search_fields=DocumentoTexto.SEARCH_FIELDS, readonly=True)
        )
        self.fields['documento_texto_base'].initial = documento_texto_base.pk
        vlqs_documentos_ja_vinculados_ao_documento_base = VinculoDocumentoTexto.objects.filter(documento_texto_base=documento_texto_base).values_list(
            "documento_texto_alvo", flat=True
        )

        documentos_passiveis_vinculacao_ids = list(
            chain(DocumentoTexto.objects.proprios(request.user).values_list('id', flat=True), DocumentoTexto.objects.compartilhados(request.user).values_list('id', flat=True))
        )

        qs_documentos_passiveis_vinculacao = DocumentoTexto.objects.filter(id__in=documentos_passiveis_vinculacao_ids)
        qs_documentos_passiveis_vinculacao = qs_documentos_passiveis_vinculacao.filter(status__in=[DocumentoStatus.STATUS_ASSINADO, DocumentoStatus.STATUS_FINALIZADO])
        qs_documentos_passiveis_vinculacao = qs_documentos_passiveis_vinculacao.exclude(pk=documento_texto_base.pk)
        qs_documentos_passiveis_vinculacao = qs_documentos_passiveis_vinculacao.exclude(pk__in=vlqs_documentos_ja_vinculados_ao_documento_base)
        self.fields['documento_texto_alvo'].queryset = qs_documentos_passiveis_vinculacao.only(
            'pk', 'identificador_tipo_documento_sigla', 'identificador_numero', 'identificador_ano', 'identificador_setor_sigla'
        ).order_by('identificador_tipo_documento_sigla', 'identificador_ano', 'identificador_numero')


class CancelarDocumentoForm(forms.ModelFormPlus):
    justificativa_cancelamento = forms.CharFieldPlus(label='Justificativa', widget=forms.Textarea())

    class Meta:
        model = DocumentoTexto
        fields = ('justificativa_cancelamento',)

    def save(self, *args, **kwargs):
        with transaction.atomic(), reversion.create_revision():
            self.instance.data_cancelamento = get_datetime_now()
            self.instance.cancelar_documento()
            return super().save(*args, **kwargs)


class RestricaoAssinaturaForm(forms.ModelFormPlus):
    TIPO_PAPEL_CHOICES = [[1, 'Cargo'], [2, 'Função']]
    papel = forms.ChoiceField(label='Papel:', choices=TIPO_PAPEL_CHOICES, required=True, widget=forms.RadioSelect)
    cargo_emprego = forms.ModelChoiceFieldPlus(queryset=CargoEmprego.objects, required=False, widget=AutocompleteWidget(search_fields=CargoEmprego.SEARCH_FIELDS))
    funcao = forms.ModelChoiceFieldPlus(queryset=Funcao.objects, required=False, widget=AutocompleteWidget(search_fields=Funcao.SEARCH_FIELDS))

    class Meta:
        model = RestricaoAssinatura
        fields = ('tipo_documento_texto',)

    class Media:
        js = ('/static/documento_eletronico/js/RestricaoAssinaturaForm.js',)

    def clean(self):
        if 'papel' in self.cleaned_data:
            if self.cleaned_data['papel'] == "1" and self.cleaned_data['cargo_emprego'] is None:
                raise forms.ValidationError('Escolha um cargo.')
            elif self.cleaned_data['papel'] == "2" and self.cleaned_data['funcao'] is None:
                raise forms.ValidationError('Escolha uma função.')

        return self.cleaned_data

    def save(self, *args, **kwargs):
        generic_obj = None
        if self.cleaned_data['papel'] == "1":
            generic_obj = self.cleaned_data['cargo_emprego']
        elif self.cleaned_data['papel'] == "2":
            generic_obj = self.cleaned_data['funcao']

        self.instance.papel_content_type = ContentType.objects.get_for_model(generic_obj.__class__)
        self.instance.papel_content_id = generic_obj.id
        self.instance.papel_content_object = generic_obj

        return super().save(*args, **kwargs)


class CompartilhamentoDocumentosPessoaForm(forms.ModelFormPlus):
    documento = forms.ModelChoiceFieldPlus(queryset=DocumentoTexto.objects, required=True, widget=AutocompleteWidget(search_fields=DocumentoTexto.SEARCH_FIELDS))
    pessoa_permitida = forms.ModelChoiceFieldPlus(queryset=Pessoa.objects, required=True, widget=AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS))

    class Meta:
        model = CompartilhamentoDocumentoPessoa
        fields = ('documento', 'pessoa_permitida', 'nivel_permissao')


class CompartilhamentoDocumentosSetorPessoaForm(forms.ModelFormPlus):
    setor_dono = forms.ModelChoiceFieldPlus(queryset=Setor.objects, required=True, widget=AutocompleteWidget(search_fields=Setor.SEARCH_FIELDS))
    pessoa_permitida = forms.ModelChoiceFieldPlus(queryset=Pessoa.objects, required=True, widget=AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS))

    class Meta:
        model = CompartilhamentoSetorPessoa
        fields = ('setor_dono', 'pessoa_permitida', 'nivel_permissao')


class SolicitarCompartilhamentoDocumentoDigitalizadoForm(forms.ModelFormPlus):
    pessoa_solicitante = forms.ModelChoiceFieldPlus(Pessoa.objects, label='Pessoa Solicitante', widget=AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS, readonly=True))
    documento = forms.ModelChoiceFieldPlus(
        DocumentoDigitalizado.objects, label='Documento Sigiloso', widget=AutocompleteWidget(search_fields=DocumentoDigitalizado.SEARCH_FIELDS, readonly=True)
    )

    class Meta:
        model = SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa
        fields = ('pessoa_solicitante', 'documento', 'justificativa_solicitacao')

    def __init__(self, *args, **kwargs):
        documento = kwargs.pop('documento')
        self.processo = kwargs.pop('processo')
        pessoa_solicitante = kwargs.pop('pessoa_solicitante')
        super().__init__(*args, **kwargs)

        self.fields['pessoa_solicitante'].initial = pessoa_solicitante
        self.fields['pessoa_solicitante'].widget.attrs.update(readonly='readonly')
        self.fields['pessoa_solicitante'].widget.attrs.update(disabled='disabled')

        self.fields['documento'].initial = documento
        self.fields['documento'].widget.attrs.update(readonly='readonly')
        self.fields['documento'].widget.attrs.update(disabled='disabled')

    def get_texto_solicitacao(self):
        texto = """<h1>Solicitação de Acesso de Visualização</h1>
        <h2>[SUAP] Solicitação de Visualização do Documento {0} </h2>
        <dl>
            <dt>Processo:</dt><dd>{5}</dd>
            <dt>Data:</dt><dd>{1}</dd>
            <dt>Solicitante:</dt><dd>{2}</dd>
            <dt>Motivação:</dt><dd>{3}</dd>
        </dl>
        <p>--</p>
        <p>Para mais informações, acesse:
            <a href="{4}">{5}</a>
        </p>
        """.format(
            self.instance.documento,
            self.instance.data_criacao.strftime('%d/%m/%Y %H:%M'),
            self.instance.pessoa_solicitante,
            self.instance.justificativa_solicitacao,
            self.processo.get_absolute_url(),
            self.processo,
        )
        return texto

    def enviar_email(self):
        texto = self.get_texto_solicitacao()
        destino = [self.instance.documento.dono_documento.get_vinculo()] if self.instance.documento.dono_documento else []
        if destino:
            self.instance.enviar_mail(texto, destino)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.enviar_email()


class AvaliarSolicitacaoCompartilhamentoDocumentoDigitalizadoForm(forms.ModelFormPlus):
    STATUS_DEFERIDA = 1
    STATUS_INDEFERIDA = 2

    STATUS_CHOICES = ((STATUS_DEFERIDA, 'Deferida'), (STATUS_INDEFERIDA, 'Indeferida'))
    status_solicitacao = forms.ChoiceField(choices=STATUS_CHOICES, label='Situação da Solicitação', required=True)

    class Meta:
        model = SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa
        fields = ('status_solicitacao', 'justificativa_autorizacao')

    def __init__(self, *args, **kwargs):
        self.processo = kwargs.pop('processo')
        self.documento_removido = kwargs.pop('documento_removido')
        super().__init__(*args, **kwargs)
        if self.documento_removido:
            self.fields['status_solicitacao'].choices = ((self.STATUS_INDEFERIDA, 'Indeferida'),)
            self.fields['status_solicitacao'].help_text = "A solicitação não pode ser deferida pois o documento foi removido do processo {}.".format(
                self.processo.numero_protocolo_fisico
            )

    def get_texto_solicitacao(self):
        texto = """<h1>Solicitação de Acesso de Visualização</h1>
        <h2>[SUAP] Solicitação de Visualização do Documento {0}</h2>
        <dl>
            <dt>Data:</dt><dd>{1}</dd>
            <dt>Solicitante:</dt><dd>{2}</dd>
            <dt>Motivação:</dt><dd>{3}</dd>
            <dt>Processo:</dt><dd>{4}</dd>
            <dt>Status:</dt><dd>{5}</dd>
            <dt>Justificativa (Des)Autorização:</dt><dd>{6}</dd>
        </dl>
        <p>--</p>
        <p>Para mais informações, acesse:
            <a href="{7}>{4}</a>
        </p>
        """.format(
            self.instance.documento,
            self.instance.data_criacao.strftime('%d/%m/%Y %H:%M'),
            self.instance.pessoa_solicitante,
            self.instance.justificativa_solicitacao,
            self.processo,
            self.instance.status_solicitacao,
            self.instance.justificativa_autorizacao,
            self.processo.get_absolute_url(),
        )
        return texto

    def enviar_email(self):
        texto = self.get_texto_solicitacao()
        destino = [self.instance.pessoa_solicitante.pessoafisica.get_vinculo()]
        self.instance.enviar_mail(texto, destino)

    @transaction.atomic()
    def save(self, commit=True):
        if not self.instance.id:
            self.instance.data_autorizacao = datetime.now()
            self.instance.usuario_autorizacao = self.request.user
        solicitacao = super().save(commit)
        if solicitacao.deferida():
            compartilhamento = CompartilhamentoDocumentoDigitalizadoPessoa()
            compartilhamento.documento = solicitacao.documento
            compartilhamento.pessoa_permitida = solicitacao.pessoa_solicitante
            compartilhamento.data_criacao = datetime.now()
            compartilhamento.usuario_criacao = solicitacao.usuario_autorizacao
            compartilhamento.save()
        # Se não estivesse
        if not solicitacao.pendente():
            self.enviar_email()
        return solicitacao


class DocumentoTextoFormEditarInteressados(forms.FormPlus):
    documento = forms.CharFieldPlus()
    interessados = forms.MultipleModelChoiceFieldPlus(queryset=Pessoa.objects.all(), label='Interessados', required=True)
    observacao_alteracao_interessados = forms.CharFieldPlus(label='Justificativa', widget=forms.Textarea())
    senha = forms.CharFieldPlus(label='Senha', widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        self.documento = kwargs.pop('documento')
        super().__init__(*args, **kwargs)
        self.fields['documento'].initial = self.documento
        self.fields['documento'].widget.attrs['readonly'] = True
        self.fields['interessados'].initial = self.documento.interessados.all().values_list('pk', flat=True)

    def clean_senha(self):
        usuario_autenticado = authenticate(username=self.request.user.username, password=self.cleaned_data.get('senha'))
        if not usuario_autenticado:
            raise forms.ValidationError('Senha inválida')
        return self.cleaned_data.get('senha')


class DocumentoTextoPessoalForm(forms.ModelFormPlus):
    tipo = forms.ModelChoiceField(TipoDocumentoTexto.ativos_pessoais, label='Tipo do Documento', required=True)
    modelo = forms.ModelChoiceField(ModeloDocumento.ativos.all(), label='Modelo', required=True)
    assunto = forms.CharField(widget=TextareaCounterWidget(max_length=255), label='Assunto')
    classificacao = forms.ModelMultiplePopupChoiceField(Classificacao.objects, label='Classificações', required=False, disabled=True)

    instrucoes_gerais = forms.CharFieldPlus(label='', max_length=100000,
                                            required=False,
                                            widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': '30', 'cols': '80'}))

    ciencia_instrucoes_gerais = forms.BooleanField(widget=forms.CheckboxInput,
                                                   required=True,
                                                   label='Estou ciente sobre as instruções gerais.')

    hipotese_legal = forms.ModelChoiceField(
        HipoteseLegal.objects.all(), label='Hipótese Legal', required=False, help_text='A hipótese legal só é obrigatória para documentos sigilosos ou restritos'
    )

    class Meta:
        model = DocumentoTextoPessoal
        fields = ('tipo', 'modelo', 'nivel_acesso', 'hipotese_legal', 'assunto')

    class Media:
        js = ['/static/documento_eletronico/js/DocumentoTextoForm.js']

    def clean_nivel_acesso(self):
        nivel_acesso = self.cleaned_data.get('nivel_acesso')
        if self.instance.id:
            old_version = DocumentoTextoPessoal.objects.get(id=self.instance.id)
            self.instance.nivel_acesso = nivel_acesso
            if self.instance.nivel_acesso != old_version.nivel_acesso:
                self.instance.validar_auteracao_nivel_acesso(self.request.user)
        return nivel_acesso

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        edit_mode = bool(self.instance.pk)

        if edit_mode:
            self.fields['tipo'].initial = self.instance.modelo.tipo_documento_texto
            self.fields['tipo'].widget = forms.widgets.HiddenInput()
            self.fields['tipo'].required = False
            self.fields['tipo'].help_text = 'O tipo de documento não pode ser alterado'

        if 'processo_eletronico' in settings.INSTALLED_APPS:
            ConfiguracaoInstrucaoNivelAcesso = apps.get_model('processo_eletronico', 'ConfiguracaoInstrucaoNivelAcesso')
        conf_orientacao = ConfiguracaoInstrucaoNivelAcesso.get_orientacao()
        if conf_orientacao:
            self.fields['ciencia_instrucoes_gerais'].required = True
            self.fields['instrucoes_gerais'] = SpanField(widget=SpanWidget(), label='')
            self.fields['instrucoes_gerais'].widget.label_value = mark_safe('<br>{}'.format(conf_orientacao))
            self.fields['instrucoes_gerais'].widget.original_value = conf_orientacao
            self.fields['instrucoes_gerais'].required = False
        else:
            self.fields['ciencia_instrucoes_gerais'].widget = forms.HiddenInput()
            self.fields['ciencia_instrucoes_gerais'].required = False
            self.fields['instrucoes_gerais'].widget = forms.HiddenInput()

    @transaction.atomic()
    def save(self, commit=True):
        if not self.instance.id:
            self.instance.data_criacao = datetime.now()
            self.instance.usuario_criacao = self.request.user
        self.instance.data_ultima_modificacao = datetime.now()
        self.instance.usuario_ultima_modificacao = self.request.user

        # Cria papel (quando ele ainda não existe)
        # - para que alunos possam criar documentos pessoais
        # - para que alunos possam executar as outras operações relacionadas ao documento pessoal
        if self.request.user.get_vinculo().eh_aluno():
            aluno = self.request.user.get_relacionamento()
            aluno.criar_papel_discente()

        return super().save(commit)


class DocumentoPessoalDigitalizadoForm(forms.ModelFormPlus):
    assunto = forms.CharFieldPlus(label='Assunto')

    hipotese_legal = forms.ModelChoiceField(HipoteseLegal.objects.all(), label='Hipótese Legal', required=False)

    tipo_conferencia = forms.ModelChoiceField(label='Tipo de Conferência', queryset=TipoConferencia.objects, widget=forms.Select)
    tipo = forms.ModelPopupChoiceField(TipoDocumento.ativos_pessoais, label='Tipo', required=True)

    papel = forms.ModelChoiceField(label='Perfil', required=True, queryset=Papel.objects.none())
    senha = forms.CharFieldPlus(label='Senha', required=True, widget=forms.PasswordInput())

    instrucoes_gerais = forms.CharFieldPlus(label='', max_length=100000,
                                            required=False,
                                            widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': '30', 'cols': '80'}))

    ciencia_instrucoes_gerais = forms.BooleanField(widget=forms.CheckboxInput,
                                                   required=True,
                                                   label='Estou ciente sobre as instruções gerais.')

    hipotese_legal = forms.ModelChoiceField(
        HipoteseLegal.objects.all(), label='Hipótese Legal', required=False, help_text='A hipótese legal só é obrigatória para documentos sigilosos ou restritos'
    )

    class Meta:
        model = DocumentoDigitalizadoPessoal
        exclude = ()

    class Media:
        js = ('/static/processo_eletronico/js/DocumentoUploadEditarForm.js',)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.max_file_upload_size = settings.PROCESSO_ELETRONICO_DOCUMENTO_EXTERNO_MAX_UPLOAD_SIZE

            user = self.request.user if self.request else tl.get_user()
            self.tamanho_maximo_upload_personalizado = Configuracao.get_valor_por_chave(app='processo_eletronico', chave='tamanho_maximo_upload_personalizado')
            self.pessoas_permitidas_upload_personalizado = Configuracao.get_valor_por_chave(app='processo_eletronico', chave='pessoas_permitidas_realizar_upload_personalizado')
            pessoa_permitida_upload_personalizado = self.pessoas_permitidas_upload_personalizado and str(user.get_profile().id) in self.pessoas_permitidas_upload_personalizado.split(',')

            self.fields['arquivo'].max_file_size = pessoa_permitida_upload_personalizado and settings.DATA_UPLOAD_MAX_MEMORY_SIZE or self.max_file_upload_size

            vinculo = self.request.user.get_relacionamento()
            self.fields['papel'].queryset = vinculo.papeis_ativos
            if vinculo.papeis_ativos.count() == 1:
                self.fields['papel'].initial = vinculo.papeis_ativos.first().id
        else:
            del self.fields['papel']
            del self.fields['senha']
            del self.fields['tipo_conferencia']

        if 'processo_eletronico' in settings.INSTALLED_APPS:
            ConfiguracaoInstrucaoNivelAcesso = apps.get_model('processo_eletronico', 'ConfiguracaoInstrucaoNivelAcesso')
        conf_orientacao = ConfiguracaoInstrucaoNivelAcesso.get_orientacao()
        if conf_orientacao:
            self.fields['ciencia_instrucoes_gerais'].required = True
            self.fields['instrucoes_gerais'] = SpanField(widget=SpanWidget(), label='')
            self.fields['instrucoes_gerais'].widget.label_value = mark_safe('<br>{}'.format(conf_orientacao))
            self.fields['instrucoes_gerais'].widget.original_value = conf_orientacao
            self.fields['instrucoes_gerais'].required = False
        else:
            self.fields['ciencia_instrucoes_gerais'].widget = forms.HiddenInput()
            self.fields['ciencia_instrucoes_gerais'].required = False
            self.fields['instrucoes_gerais'].widget = forms.HiddenInput()

    def clean_arquivo(self):
        content = self.cleaned_data.get('arquivo', None)
        if content:
            content_type = content.content_type.split('/')[1]
            if content_type not in settings.CONTENT_TYPES:
                raise forms.ValidationError('Tipo de arquivo não permitido. Só são permitidos arquivos com extensão: .PDF')
            # se esta condição for problemática por favor comente o motivo mas não remova.
            if not check_pdf_with_pypdf(content) and not check_pdf_with_gs(content) and not running_tests():
                raise forms.ValidationError('Arquivo corrompido ou mal formado, reimprima o PDF utilizando uma ferramenta de impressão adequada como o CutePDF Writer.')
            return content

        raise forms.ValidationError('Este campo é obrigatório.')

    def clean_senha(self):
        senha = self.cleaned_data['senha']
        if senha:
            usuario_autenticado = authenticate(username=self.request.user.username, password=senha)
            if not usuario_autenticado:
                raise forms.ValidationError('Senha inválida')
        return self.cleaned_data.get('senha')


class DocumentoAlterarNivelAcessoForm(forms.FormPlus):
    # Utilizado pelo alterar nivel de acesso DocumentoTexto e DocumentoDigitalizado
    # Utilizado pelo solicitar alterar nivel de acesso DocumentoTexto e DocumentoDigitalizado

    nivel_acesso_atual = SpanField(label='De', widget=SpanWidget())
    nivel_acesso = forms.ChoiceField(required=True, label='Para')
    hipotese_legal = forms.ModelChoiceField(HipoteseLegal.objects.all(), label='Hipótese Legal', required=False)
    senha = forms.CharFieldPlus(label='Senha', widget=forms.PasswordInput())

    instrucoes_gerais = forms.CharFieldPlus(label='', max_length=100000,
                                            required=False,
                                            widget=forms.Textarea(attrs={'readonly': 'readonly', 'rows': '30', 'cols': '80'}))

    ciencia_instrucoes_gerais = forms.BooleanField(widget=forms.CheckboxInput,
                                                   required=True,
                                                   label='Estou ciente sobre as instruções gerais.')

    justificativa = forms.CharFieldPlus(label='Justificativa', max_length=400, required=False, widget=forms.Textarea())

    pessoas_compartilhadas = forms.MultipleModelChoiceFieldPlus(PessoaFisica.objects,
                                                                label='Compartilhamentos com Pessoas', required=False)

    fieldsets = (
        ('Atual Nível de Acesso', {'fields': ('nivel_acesso_atual',)},),
        ('Novo Nível de Acesso', {'fields': ('instrucoes_gerais',
                                             'ciencia_instrucoes_gerais',
                                             'nivel_acesso',
                                             'hipotese_legal', 'justificativa')},),
        ('Autenticação', {'fields': ('senha',)}),
    )

    class Media:
        js = ['/static/documento_eletronico/js/DocumentoAlteraNivelAcessoForm.js']

    def __init__(self, *args, **kwargs):
        self.documento = kwargs.pop('documento', None)
        self.estah_solicitando = kwargs.pop('estah_solicitando', None)
        self.solicitacao = kwargs.pop('solicitacao', None)
        #
        super().__init__(*args, **kwargs)

        if self.estah_solicitando or self.documento.eh_documento_texto:
            if 'pessoas_compartilhadas' in self.fields:
                del self.fields['pessoas_compartilhadas']

        # Níveis de acesso - DE (Atual)
        de = NivelAcesso.choices()[self.documento.nivel_acesso - 1][1]
        self.fields['nivel_acesso_atual'].widget.label_value = de
        self.fields['nivel_acesso_atual'].widget.original_value = self.documento.nivel_acesso

        # Níveis de acesso - PARA (Novo)
        niveis_acesso_alteracao = list(Documento.NIVEL_ACESSO_CHOICES)
        del niveis_acesso_alteracao[self.documento.nivel_acesso - 1]
        self.fields['nivel_acesso'].choices = niveis_acesso_alteracao
        self.fields['nivel_acesso'].initial = 0
        if self.solicitacao:

            self.fields['nivel_acesso'] = SpanField(widget=SpanWidget(), label='Para')
            self.fields['nivel_acesso'].widget.label_value = self.solicitacao.get_para_nivel_acesso()[1]
            self.fields['nivel_acesso'].widget.original_value = self.solicitacao.get_para_nivel_acesso()[0]
            self.fields['nivel_acesso'].required = False
            #
            self.Media.js = None

            if 'processo_eletronico' in settings.INSTALLED_APPS:
                SolicitacaoAlteracaoNivelAcesso = apps.get_model('processo_eletronico', 'SolicitacaoAlteracaoNivelAcesso')
            hipoteses = SolicitacaoAlteracaoNivelAcesso.get_hipoteses_legais_by_processo_documento_nivel_acesso(2, self.solicitacao.get_para_nivel_acesso()[0])
            if hipoteses:
                self.fields['hipotese_legal'].queryset = hipoteses
            else:
                self.fields['hipotese_legal'].queryset = HipoteseLegal.objects.none()
            #
            if self.solicitacao.hipotese_legal:
                self.fields['hipotese_legal'].initial = self.solicitacao.hipotese_legal.id

        # Instrucoes
        if 'processo_eletronico' in settings.INSTALLED_APPS:
            ConfiguracaoInstrucaoNivelAcesso = apps.get_model('processo_eletronico', 'ConfiguracaoInstrucaoNivelAcesso')
        conf_orientacao = ConfiguracaoInstrucaoNivelAcesso.get_orientacao()
        if conf_orientacao:
            self.fields['ciencia_instrucoes_gerais'].required = True
            self.fields['instrucoes_gerais'] = SpanField(widget=SpanWidget(), label='')
            self.fields['instrucoes_gerais'].widget.label_value = mark_safe('<br>{}'.format(conf_orientacao))
            self.fields['instrucoes_gerais'].widget.original_value = conf_orientacao
            self.fields['instrucoes_gerais'].required = False
        else:
            self.fields['ciencia_instrucoes_gerais'].widget = forms.HiddenInput()
            self.fields['ciencia_instrucoes_gerais'].required = False
            self.fields['instrucoes_gerais'].widget = forms.HiddenInput()

    def clean_senha(self):
        usuario_autenticado = authenticate(username=self.request.user.username, password=self.cleaned_data.get('senha'))
        if not usuario_autenticado:
            raise forms.ValidationError('Senha inválida.')

        return self.cleaned_data.get('senha')

    def clean_nivel_acesso(self):
        niveis_acesso_alteracao = list(Documento.NIVEL_ACESSO_CHOICES)
        del niveis_acesso_alteracao[int(self.cleaned_data.get('nivel_acesso_atual')) - 1]
        diferente = int(self.cleaned_data.get('nivel_acesso_atual')) != int(self.cleaned_data.get('nivel_acesso'))
        nivel_acesso_valido = int(self.cleaned_data.get('nivel_acesso')) in (Documento.NIVEL_ACESSO_RESTRITO, Documento.NIVEL_ACESSO_SIGILOSO, Documento.NIVEL_ACESSO_PUBLICO)
        if not (diferente and nivel_acesso_valido):
            raise forms.ValidationError('Nível de acesso inválido.')
        return self.cleaned_data.get('nivel_acesso')

    def clean_pessoas_compartilhadas(self):
        if self.cleaned_data.get('pessoas_compartilhadas') and not int(self.cleaned_data.get('nivel_acesso')) == Documento.NIVEL_ACESSO_SIGILOSO:
            raise forms.ValidationError('Só é permitido o compartilhamento com pessoas quando o nível de acessso solicitado for sigiloso.')
        return self.cleaned_data.get('pessoas_compartilhadas')

    def clean(self):
        if self.cleaned_data.get('nivel_acesso') and int(self.cleaned_data.get('nivel_acesso')) in (Documento.NIVEL_ACESSO_RESTRITO, Documento.NIVEL_ACESSO_SIGILOSO) and not self.cleaned_data.get('hipotese_legal'):
            raise forms.ValidationError('Selecione uma hipótese legal.')
