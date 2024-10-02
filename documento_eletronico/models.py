import base64
import hashlib
import io
import json
import uuid
import qrcode
from binascii import unhexlify
from datetime import datetime
from enum import Enum
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from comum.models import Configuracao
from comum.utils import (get_setor, get_todos_setores, get_values_from_choices, tl)
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from django.apps.registry import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max, Q
from django.urls import reverse
from django.utils.html import format_html
from django_fsm import FSMIntegerField, transition
from djtools.db import models
from djtools.middleware.threadlocals import get_user
from djtools.templatetags.filters import (format_iterable, format_profile, status)
from djtools.utils import get_datetime_now, send_notification, deprecated
from model_utils.managers import InheritanceManager
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel, MPTTModelBase
from processo_eletronico.utils import setores_que_sou_chefe_ou_tenho_poder_de_chefe
from reversion import revisions as reversion
from reversion.models import Version
from rh.models import Pessoa, Servidor

from .assinar_documento import (gerar_assinatura_documento_senha, verificar_assinatura_senha)
from .managers import (AssinaturaDocumentoTextoManager, AtivosDocumentosPessoaisManager, AtivosManager,
                       DocumentoDigitalizadoAnexoManager,
                       DocumentoDigitalizadoManager,
                       DocumentoDigitalizadoPessoalManager,
                       DocumentoTextoManager, DocumentoTextoPessoalManager,
                       PodemClassificarManager, SolicitacaoAssinaturaManager,
                       SolicitacaoRevisorManager)
from .status import (AvaliacaoSolicitacaoStatus, DocumentoStatus,
                     SolicitacaoStatus)
from .utils import (
    EstagioProcessamentoVariavel, Notificar,
    app_processo_eletronico_estah_instalada, convert_pdf_to_string_b64, eh_procurador, existem_solicitacoes_juntada_pendentes,
    file_upload_to, gerar_hash, gerar_pdf_documento_digitalizado,
    gerar_pdf_documento_texto, get_processos_vinculados_ao_documento,
    get_variaveis, merge_pdfs_pdf, processar_template_ckeditor,
    processar_template_documentos_anexados, solicitacoes_juntada_pendentes,
    usuario_deve_ter_acesso_a_documento_publico_e_cancelado_atraves_de_processo,
    usuario_deve_ter_acesso_a_documento_restrito_atraves_de_processo,
    usuario_deve_ter_acesso_a_documento_restrito_atraves_de_solicitacao_juntada_pendente,
    acesso_ao_documento_em_funcao_cargo,
)

from .generators import identificador_sequencial, identificador_sequencial_anual

# TODO: Ajustar as entidades Documento e Processo para utilizar este enum para o controle de Nivel de Acesso.


class NivelAcesso(Enum):
    '''
    Níveis de acesso que defimem o nível de sigilo de determinado registro.
    Por padrão, caso vá utilizar este enum em algum modelo, use os métodos "choices", pois ele exibe as opções na ordem
    que elas tão definidas no método, caso contrário, será utilizada a ordem alfabética (NivelAcesso.__members__).

    Ex:
    (1) Registros exibidos na ordem definida no método.
    class MyModel(models.ModelPlus):
        nivel_acesso = models.CharFieldPlus(verbose_name=u'Nível de Acesso', max_length=NivelAcesso.max_length(), choices=NivelAcesso.choices())

    (2) Registros exibidos em ordem alfabética
    class MyModel(models.ModelPlus):
        nivel_acesso = models.CharFieldPlus(verbose_name=u'Nível de Acesso', max_length=NivelAcesso.max_length(), choices=choices=[(tag.name, tag.value) for tag in NivelAcesso])


    Exemplo de filtro:
    historicos_legais = HipoteseLegal.objects.filter(nivel_acesso=NivelAcesso.SIGILOSO.name)
    '''

    # name (id) = value (description)
    SIGILOSO = 'Sigiloso'
    RESTRITO = 'Restrito'
    PUBLICO = 'Público'

    @classmethod
    def max_length(cls):
        return 10

    @classmethod
    def get_by_name(cls, name):
        for tag in NivelAcesso:
            if tag.name == name:
                return tag
        return None

    @classmethod
    def choices(cls):
        '''
        Método que retorna todas as opções de níveis de acesso.
        :return: tupla com id e descricao dos níveis de acesso
        '''
        return tuple((i.name, i.value) for i in (cls.SIGILOSO, cls.RESTRITO, cls.PUBLICO))

    @classmethod
    def choices_for_hipotese_legal(cls):
        '''
        Método que retorna as opções de níveis de acesso voltadas para o cadastro de hipóteses legais.
        :return: tupla com id e descricao dos níveis de acesso
        '''
        return tuple((i.name, i.value) for i in (cls.SIGILOSO, cls.RESTRITO))


class Documento(models.ModelPlus):

    NIVEL_ACESSO_SIGILOSO = 1
    NIVEL_ACESSO_RESTRITO = 2
    NIVEL_ACESSO_PUBLICO = 3
    NIVEL_ACESSO_CHOICES = ((NIVEL_ACESSO_SIGILOSO, 'Sigiloso'), (NIVEL_ACESSO_RESTRITO, 'Restrito'), (NIVEL_ACESSO_PUBLICO, 'Público'))
    ##################################################################################
    #
    #   Dados a serem preenchidos pelo usuário
    #
    ##################################################################################
    assunto = models.CharFieldPlus('Assunto', db_index=True)
    nivel_acesso = models.PositiveIntegerField(choices=NIVEL_ACESSO_CHOICES, default=NIVEL_ACESSO_PUBLICO, verbose_name='Nível de Acesso')
    hipotese_legal = models.ForeignKeyPlus('documento_eletronico.HipoteseLegal', verbose_name='Hipótese Legal', blank=False, null=True)

    # Um documento com setor Dono é um documento PESSOAL conforme demanda 796
    # - property eh_documento_pessoal
    # O dono de um documento Pessoal é o usuário que o criou -- usuario_criacao
    # Os documentos pessoais podem ser criados apemas para TipoDocumento específicos
    setor_dono = models.ForeignKeyPlus('rh.Setor', verbose_name='Setor Dono', null=True)

    ##################################################################################
    #
    #   Dados automaticos
    #
    ##################################################################################
    data_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.ForeignKeyPlus(
        'comum.User', verbose_name='Usuário de Criação', editable=False, related_name='%(app_label)s_%(class)s_usuario_criacao', on_delete=models.CASCADE, null=True
    )
    data_ultima_modificacao = models.DateTimeFieldPlus('Data da Última Modificação', editable=False)
    usuario_ultima_modificacao = models.ForeignKeyPlus(
        'comum.User',
        verbose_name='Usuário da Última Modificação',
        editable=False,
        related_name='%(app_label)s_%(class)s_usuario_ultima_modificacao',
        on_delete=models.CASCADE,
        null=True,
    )
    data_remocao = models.DateTimeFieldPlus('Data de Remoção', blank=True, null=True)
    usuario_remocao = models.ForeignKeyPlus(
        'comum.User', verbose_name='Usuário de Remoção', blank=True, null=True, related_name='%(app_label)s_%(class)s_usuario_remocao', on_delete=models.CASCADE
    )
    justificativa_remocao = models.TextField('Justificativa de Remoção', blank=True, null=True)
    data_emissao = models.DateTimeFieldPlus('Data de Emissão', blank=True, null=True)

    # Lista de pessoas vinculadas ao documento
    interessados = models.ManyToManyFieldPlus('rh.Pessoa', related_name='%(app_label)s_%(class)s_interessados')

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ('id',)
        abstract = True

    def clean_hipotese_legal(self):
        # TODO: Como Hipotese Legal está sendo usado em vários locais, ver uma forma de criar um método estático em
        # Hipótese Legal para realizar essa validação.
        if self.nivel_acesso in (Documento.NIVEL_ACESSO_SIGILOSO, Documento.NIVEL_ACESSO_RESTRITO):
            # Deve verificar sempre, exceto
            #   Se for documento_texto e nao tiver em RASCUNHO não precisa verificar
            #     - documentos texto podem ter sua hipotese legal definida a qualquer tempo antes de ser CONCLUIDO
            if not (self.eh_documento_texto and self.estah_em_rascunho):
                hipoteses_legais_opcoes = None
                if self.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
                    hipoteses_legais_opcoes = HipoteseLegal.objects.filter(nivel_acesso=NivelAcesso.SIGILOSO.name)
                elif self.nivel_acesso == Documento.NIVEL_ACESSO_RESTRITO:
                    hipoteses_legais_opcoes = HipoteseLegal.objects.filter(nivel_acesso=NivelAcesso.RESTRITO.name)
                if hipoteses_legais_opcoes and not self.hipotese_legal:
                    raise ValidationError(f'O nível de acesso "{self.get_nivel_acesso_display()}" exige que você '
                                          f'defina uma Hipótese Legal para o documento. Para isso, vá em Editar > '
                                          f'Dados Básicos.')
        else:
            self.hipotese_legal = None

        if self.hipotese_legal and (
            (self.hipotese_legal.nivel_acesso == NivelAcesso.SIGILOSO.name and self.nivel_acesso != Documento.NIVEL_ACESSO_SIGILOSO)
            or (self.hipotese_legal.nivel_acesso == NivelAcesso.RESTRITO.name and self.nivel_acesso != Documento.NIVEL_ACESSO_RESTRITO)
        ):
            raise ValidationError(f'Escolha uma hipótese legal compatível com o nível de acesso "{self.get_nivel_acesso_display()}"')

    def clean(self):
        self.clean_hipotese_legal()
        super().clean()

    @staticmethod
    def refresh(instance):
        """
            Select and return instance from database.
            Usage:    ``instance = refresh(instance)``
        """
        return instance.__class__.objects.get(pk=instance.pk)

    def get_absolute_url(self):
        return f"/documento_eletronico/visualizar_documento/{self.pk}/"

    def get_versions(self):
        return Version.objects.get_for_object(self)

    @property
    def eh_documento_texto(self):
        return hasattr(self, 'documentotexto')

    @property
    def eh_documento_digitalizado(self):
        return hasattr(self, 'documentodigitalizado')

    @property
    def eh_publico(self):
        return self.nivel_acesso == self.NIVEL_ACESSO_PUBLICO

    @property
    def eh_restrito(self):
        return self.nivel_acesso == self.NIVEL_ACESSO_RESTRITO

    @property
    def eh_privado(self):
        return self.nivel_acesso == self.NIVEL_ACESSO_SIGILOSO

    @property
    def qrcode(self):
        img = qrcode.make(self.get_url_autenticacao(completa=True))
        buffer_img = io.BytesIO()
        img.save(buffer_img, 'png')
        return buffer_img

    @property
    def qrcode_base64image(self):
        qrcode_data = base64.b64encode(self.qrcode.getvalue())
        return "data:image/png;base64," + qrcode_data.decode('utf-8')

    @property
    def codigo_autenticacao(self):
        return self.hash_conteudo[0:10]

    @property
    def tamanho_em_bytes(self):
        raise NotImplementedError

    @property
    def tamanho_em_kb(self):
        raise NotImplementedError

    @property
    def tamanho_em_mb(self):
        raise NotImplementedError

    @property
    def hash_conteudo(self):
        raise NotImplementedError

    @property
    def hash_conteudo_as_sha256(self):
        raise NotImplementedError

    def pode_ler(self, user=None, consulta_publica_hash=None, leitura_para_barramento=False, eh_consulta_publica=False, verificar_acesso_cargo=True):
        if not eh_consulta_publica and (user is None or user.is_anonymous):
            raise Exception("A consulta não pública não pode ser anônima.")
        #
        pode_ler = self.tem_permissao_ler(user, consulta_publica_hash, leitura_para_barramento, eh_consulta_publica)
        if verificar_acesso_cargo and not pode_ler:
            return acesso_ao_documento_em_funcao_cargo(user=user, documento=self)
        return pode_ler

    def pode_editar(self, user):
        if user is None:
            raise Exception("A edição de documentos não pode ser anônima.")
        return self.tem_permissao_editar(user)

    def pode_clonar_documento(self, user=None):
        user = user or tl.get_user()
        return self.pode_ler(user) and user.has_perm('documento_eletronico.add_documentotexto') and self.modelo.tipo_documento_texto.ativo

    def pode_compartilhar(self, user=None):
        user = user or tl.get_user()

        if self.usuario_criacao == user:
            return True

        if not self.eh_documento_pessoal:
            setor = get_setor(user)
            if self.nivel_acesso == self.NIVEL_ACESSO_SIGILOSO:
                return False
            elif self.nivel_acesso == self.NIVEL_ACESSO_RESTRITO and self.setor_dono == setor:
                return True
            elif self.nivel_acesso == self.NIVEL_ACESSO_PUBLICO and self.setor_dono == setor:
                return True

        return False

    def as_pdf(self):
        raise NotImplementedError

    def tem_solicitacao_pendente_compartilhamento(self, user=None):
        user = user or tl.get_user()
        return self.solicitacao_compartilhamento_pessoa_documento_digitalizado.filter(
            usuario_solicitacao=user, status_solicitacao=SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.STATUS_AGUARDANDO
        ).exists()

    def get_processos(self, exibir_somente_processos_nos_quais_documento_nao_foi_removido=False):
        return get_processos_vinculados_ao_documento(
            documento=self, exibir_somente_processos_nos_quais_documento_nao_foi_removido=exibir_somente_processos_nos_quais_documento_nao_foi_removido
        )

    def tem_permissao_editar(self, user):
        raise NotImplementedError

    def tem_permissao_ler(self, user, consulta_publica_hash, leitura_para_barramento, eh_consulta_publica=False):
        raise NotImplementedError

    def tem_permissao_estrita_leitura(self, pessoa=None):
        raise NotImplementedError

    def pode_ser_excluido(self, user=None):
        return False

    @transaction.atomic()
    def assinar_via_senha(self, user, papel):
        raise NotImplementedError

    @transaction.atomic()
    def assinar_via_token(self, cert, hmac, pessoa_fisica, papel):
        raise NotImplementedError

    def possui_assinaturas(self):
        raise NotImplementedError

    def assinaturas(self):
        raise NotImplementedError

    def admite_interessados(self):
        raise NotImplementedError

    def pode_vincular_interessado(self):
        raise NotImplementedError

    def get_pdf(self, orientacao='portrait', user=None, consulta_publica_hash=None, leitura_para_barramento=False):
        raise NotImplementedError

    def get_pdf_as_string_b64(self, orientacao='portrait', user=None, consulta_publica_hash=None, leitura_para_barramento=False):
        pdf = self.get_pdf(orientacao, user, consulta_publica_hash, leitura_para_barramento)
        return convert_pdf_to_string_b64(pdf)

    def salvar_pdf(self, filename, orientacao='portrait', user=None, consulta_publica_hash=None, leitura_para_barramento=False):
        pdf = self.get_pdf(orientacao, user, consulta_publica_hash, leitura_para_barramento)
        arquivo = open(filename, 'wb')
        arquivo.write(pdf)
        arquivo.close()

    @property
    def eh_documento_de_setor(self):
        return self.setor_dono

    @property
    def eh_documento_pessoal(self):
        # Documento pessoal (Texto ou Digital)
        # - Não tem setor_dono (tem apenas usuario_criacao)
        # - Não eh um anexo_simples
        return not self.setor_dono and not self.eh_documento_anexo_simples

    @property
    def eh_documento_anexo_simples(self):
        eh_anexo_simples = self.eh_documento_digitalizado and self.anexo_simples
        return not self.setor_dono and eh_anexo_simples


@reversion.register()
class DocumentoTexto(Documento):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    SEARCH_FIELDS = ['identificador']

    '''
    O identificador definitivo do documento só será preechido quando o documento receber a assinatura balizadora. Então
    inicialmente o idenficador é NULL.
    '''
    identificador = models.CharFieldPlus('Identificador do Documento', max_length=100, blank=True, null=False, db_index=True)
    identificador_tipo_documento_sigla = models.CharFieldPlus('Sigla do Tipo de Documento', max_length=50, blank=True, null=True)
    identificador_numero = models.PositiveIntegerField('Número', blank=True, null=True)
    identificador_ano = models.PositiveIntegerField('Ano', blank=True, null=True)
    identificador_setor_sigla = models.CharFieldPlus('Sigla do Setor', max_length=100, blank=True, null=True)
    identificador_dono_documento = models.CharFieldPlus('Identificador Dono Documento', max_length=100, blank=True, null=True)
    #
    status = FSMIntegerField('Situação', default=DocumentoStatus.STATUS_RASCUNHO, choices=DocumentoStatus.STATUS_CHOICES, protected=True)
    modelo = models.ForeignKeyPlus('documento_eletronico.ModeloDocumento', verbose_name='Modelo de Documento de Texto', blank=False, null=False, on_delete=models.PROTECT)
    corpo = models.TextField('Corpo')

    '''
    Como o lançamento da versão "documentos otimizados", os atributos cabecalho e rodape serão mantidos por questão de
    compatibilidade com os documentos antigos para os quais não foi possível realizar a otimização, ou seja, criar
    referências de cabeçalho e rodapé (atributos cabecalho_base_original e rodape_base_original).

    Dessa forma, o módulo de documentos eletrônicos passa a funcionar da seguite forma: caso os atributos
    cabecalho_base_original e rodape_base_original estejam preenchidos, eles terão prioridade, caso contrário, os atributos
    cabecalho e rodape serão utilizados.

    Toda vez que precisar visualizar o cabeçalho e /ou rodapé, utilizar os métodos  "cabecalho_para_visualizacao()" ou
    "rodape_para_visualizacao()", pois eles já fazem esse tratamento e devolvem o conteudo correto.
    '''
    cabecalho = models.TextField('Cabeçalho')
    rodape = models.TextField('Rodapé')

    # Com base nos atributos "cabecalho_base_original" e "rodape_base_original  teremos condições de saber qual foi a
    # versão do cabeçalho e rodapé, vindos de tipo de documento, utilizados nos novos documentos após esse ajuste entrar
    # no ar.
    cabecalho_base_original = models.ForeignKeyPlus(
        'documento_eletronico.TipoDocumentoTextoHistoricoConteudo', null=True, editable=False,
        on_delete=models.PROTECT, related_name='documentos_usando_cabecalho'
    )
    rodape_base_original = models.ForeignKeyPlus(
        'documento_eletronico.TipoDocumentoTextoHistoricoConteudo', null=True, editable=False,
        on_delete=models.PROTECT, related_name='documentos_usando_rodape'
    )
    variaveis = models.TextField('Variaveis', editable=False)

    usuarios_marcadores_favoritos = models.ManyToManyFieldPlus('comum.User', verbose_name='Usuários Que Marcaram o Documento como Favorito', editable=False, blank=True)
    data_cancelamento = models.DateTimeField(blank=True, null=True)
    justificativa_cancelamento = models.TextField('Justificativa do Cancelamento', blank=True, null=True)

    assinatura_balizadora = models.ForeignKey(
        'documento_eletronico.AssinaturaDocumentoTexto', null=True,
        related_name='%(app_label)s_%(class)s_assinatura_balizadora',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Documento de Texto'
        verbose_name_plural = 'Documentos de Texto'
        ordering = ('-data_ultima_modificacao', 'modelo__tipo_documento_texto__nome', '-identificador_numero')
        permissions = (
            ('pode_vincular_interesssados', "Pode vincular interessados"),
            ('pode_alterar_nivel_acesso_documento_texto', "Pode alterar nível de acesso dos documentos eletrônicos - texto"),
            ('pode_ver_todos_log_acoes_documento_texto', "Pode acessar todos os logs de acessos - texto")
        )

    objects = DocumentoTextoManager()

    class History:
        blank_fields = ('cabecalho', 'rodape', 'corpo')
        encrypt_fields = ('variaveis',)

    def __str__(self):
        return f"{self.identificador}"

    @classmethod
    def get_ultimo_identificador_definitivo(cls, pessoal=False, **kwargs):
        qs = cls.objects.impessoais().filter(**kwargs) if not pessoal else cls.objects.pessoais().filter(**kwargs)
        last_doc = qs.filter(assinatura_balizadora__isnull=False).order_by('assinatura_balizadora__id').last()
        identificador_numero_max = last_doc.identificador_numero if last_doc else 0
        return identificador_numero_max

    def get_documentos_url(self):
        return f"{reverse(f'admin:{self._meta.app_label}_{self._meta.model_name}_changelist')}?opcao=1"

    def as_pdf(self):
        html = self.cabecalho_para_visualizacao + self.corpo_para_visualizacao + self.rodape_para_visualizacao
        import pdfkit

        pdf_bytes = pdfkit.from_string(html, False)
        return pdf_bytes

    def admite_interessados(self):
        return self.modelo.tipo_documento_texto.vincular_pessoa

    def pode_vincular_interessado(self, user=None):
        user = user or tl.get_user()
        pode_vincular = user.has_perm('documento_eletronico.pode_vincular_interesssados') and self.tem_permissao_editar(user)
        return not self.eh_documento_pessoal and self.admite_interessados() and (self.estah_concluido or self.estah_assinado or self.estah_finalizado) and pode_vincular

    def get_interessados(self):
        return self.interessados.all()

    def get_sugestao_identificador_definitivo(self, *args, **kwargs):
        kwargs['pessoal'] = self.eh_documento_pessoal
        kwargs['klass'] = DocumentoTexto
        return self.tipo.get_sugestao_identificador_definitivo(*args, **kwargs)

    def estah_para_receber_assinatura_balizadora(self, user_que_deseja_assinar):
        '''
        Método que verifica se o servidor que pretende realizar a assinatura está tentando realizar a assinatura bali-
        zadora, ou seja, aquela assinatura que irá gerar o identificador do documento e assim tornar o conteúdo do
        documento imutável.

        :param user_que_deseja_assinar:
        :return True caso seja a assinatura balizadora, False caso contrário:
        '''
        # Tem identificador definitivo?
        if self.tem_identificador_definitivo:
            return False

        # Tem assinaturas já realizadas?
        if self.assinaturadocumentotexto_set.all().exists():
            return False

        # Tem solicitação de assinatura balizadora pendente para outro servidor?
        qs_solicitacao_assinatura_balizadora_pendente = SolicitacaoAssinatura.objects.filter(documento=self, condicionantes__isnull=True, status=SolicitacaoStatus.STATUS_ESPERANDO)
        if qs_solicitacao_assinatura_balizadora_pendente.exists():
            qtd_solicitacao_assinatura_balizadora_pendente = qs_solicitacao_assinatura_balizadora_pendente.count()
            if qtd_solicitacao_assinatura_balizadora_pendente > 1:
                raise ValidationError(
                    'O documento em questão apresenta uma situação inválida: ele possui {:d} '
                    'solicitações de assinaturas balizadoras pendentes'.format(qtd_solicitacao_assinatura_balizadora_pendente)
                )

            solicitacao_assinatura_balizadora_pendente = qs_solicitacao_assinatura_balizadora_pendente.first()
            if not solicitacao_assinatura_balizadora_pendente:
                return False
            if solicitacao_assinatura_balizadora_pendente.solicitado.user != user_que_deseja_assinar:
                return False

        # O servidor que deseja assinar não é o dono do documento e não tem permissão para editar o documento?
        elif self.usuario_criacao != user_que_deseja_assinar and not self.tem_permissao_editar(user_que_deseja_assinar):
            return False

        return True

    def estah_compartilhado(self):
        return self.compartilhamento_pessoa_documento.exists()

    def obter_pessoas_podem_ler(self):
        nivel_permissao = NivelPermissao.LER
        pessoas_permitidas_documento_id = self.compartilhamento_pessoa_documento.filter(nivel_permissao=nivel_permissao).values_list('pessoa_permitida_id', flat=True)
        pessoas_permitidas_setor_id = self.setor_dono.compartilhamentosetorpessoa_set.filter(nivel_permissao=nivel_permissao).values_list('pessoa_permitida_id', flat=True)

        return Pessoa.objects.filter(id__in=pessoas_permitidas_documento_id) | Pessoa.objects.filter(id__in=pessoas_permitidas_setor_id)

    def obter_pessoas_podem_editar(self):
        nivel_permissao = NivelPermissao.EDITAR
        pessoas_permitidas_documento_id = self.compartilhamento_pessoa_documento.filter(nivel_permissao=nivel_permissao).values_list('pessoa_permitida_id', flat=True)
        pessoas_permitidas_setor_id = self.setor_dono.compartilhamentosetorpessoa_set.filter(nivel_permissao=nivel_permissao).values_list('pessoa_permitida_id', flat=True)

        return Pessoa.objects.filter(id__in=pessoas_permitidas_documento_id) | Pessoa.objects.filter(id__in=pessoas_permitidas_setor_id)

    def validar_auteracao_nivel_acesso(self, usuario):
        if self.id and self.usuario_criacao != usuario:
            if self.eh_documento_pessoal:
                raise ValidationError(
                    'Só quem pode alterar o nível de acesso de um documento Pessoal '
                    'é o usuário que criou o documento'
                )
            if not self.pode_alterar_nivel_acesso(usuario):
                raise ValidationError('Você não pode alterar o nível de acesso deste documento')

    def clean(self, usuario=None, old_version=None):

        try:
            if not self.modelo:
                raise ValidationError('É obrigatório indicar um modelo para adicionar um documento.')
        except ModeloDocumento.DoesNotExist:
            raise ValidationError('Não existe modelo cadastrado para o tipo de documento informado.')

        if old_version and self.nivel_acesso != old_version.nivel_acesso:
            usuario = usuario or tl.get_user()
            self.validar_auteracao_nivel_acesso(usuario)

        if self.tem_identificador_definitivo:
            #
            q_list = Q(modelo__tipo_documento_texto=self.tipo) & \
                Q(setor_dono=self.setor_dono) & \
                Q(identificador_numero=self.identificador_numero) & \
                Q(identificador_ano=self.identificador_ano)

            if self.eh_documento_pessoal:
                q_list = q_list & Q(usuario_criacao=usuario)

            outro_doc_com_mesmo_identificador = DocumentoTexto.objects.filter(q_list)

            # Se tem "id", então ajustamos a consulta para não trazermos o próprio documento.
            if self.id:
                outro_doc_com_mesmo_identificador = outro_doc_com_mesmo_identificador.exclude(pk=self.id)

            outro_doc_com_mesmo_identificador = outro_doc_com_mesmo_identificador.first()
            if outro_doc_com_mesmo_identificador:
                raise ValidationError(
                    'Já existe um documento no(a) {} do mesmo tipo e com o mesmo número e ano, criado por {} em {}.'.format(
                        outro_doc_com_mesmo_identificador.setor_dono,
                        outro_doc_com_mesmo_identificador.usuario_criacao,
                        outro_doc_com_mesmo_identificador.data_criacao.strftime('%d/%m/%Y - %H:%M'),
                    )
                )
        super().clean()

    @property
    def eh_documento_texto(self):
        return True

    @property
    def eh_documento_digitalizado(self):
        return False

    # TODO: Retornar a data da assinatura balizadora.
    @property
    def data_hora_oficial(self):
        raise NotImplementedError

    @transaction.atomic
    def save(self, *args, **kargs):
        is_insert = not self.id
        ignore_clean = kargs.pop('ignore_clean', None)
        if is_insert:
            self.montar_cabecalho_rodape_padrao()
            self.montar_corpo_padrao()
        else:
            if not ignore_clean:
                # um documento assinado pode ser alvo de novas solicitações de assinatura
                old_version = None
                if self.eh_documento_pessoal:
                    old_version = DocumentoTextoPessoal.objects.get(id=self.id)
                else:
                    old_version = DocumentoTexto.objects.get(id=self.id)
                if old_version.status == DocumentoStatus.STATUS_ASSINADO and old_version.hash_conteudo != self.hash_conteudo:
                    raise ValidationError("Um documento assinado não pode ser alterado.")

                if old_version.modelo.tipo_documento_texto != self.modelo.tipo_documento_texto:
                    raise ValidationError("O tipo do documento não pode ser alterado.")

                if self.cabecalho_base_original and self.modelo.tipo_documento_texto != self.cabecalho_base_original.tipo_documento_texto:
                    raise ValidationError("O tipo de documento do modelo deste documento está divergindo do tipo de documento referenciado no cabeçalho deste documento.")
                if self.rodape_base_original and self.modelo.tipo_documento_texto != self.rodape_base_original.tipo_documento_texto:
                    raise ValidationError("O tipo de documento do modelo deste documento está divergindo do tipo de documento referenciado no rodapé deste documento.")

                self.clean(old_version=old_version)

        # Coloquei assim pq caso o documento esteja sendo gerado ele ainda não tem pk dai daria um erro de campo not null
        self.identificador = self.get_identificador
        super().save(*args, **kargs)
        if not self.eh_documento_pessoal:
            DocumentoTexto.objects.filter(pk=self.pk).update(identificador=self.get_identificador)
        else:
            DocumentoTextoPessoal.objects.filter(pk=self.pk).update(identificador=self.get_identificador)

        # Se for pessoal adiciona o criador como interessado
        if self.eh_documento_pessoal:
            self.interessados.clear()
            self.interessados.add(self.usuario_criacao.get_profile())

        # Garante que os anexos terao o mesmo nivel de acesso do pai
        anexos_simples = self.get_apenas_anexos_digitalizados_simples()
        for anexo_simples in anexos_simples:
            anexo_simples.nivel_acesso = self.nivel_acesso
            anexo_simples.hipotese_legal = self.hipotese_legal
            anexo_simples.save()

        try:
            ip = tl.get_request().META['REMOTE_ADDR']
        except AttributeError:
            ip = "127.0.0.1"

        if is_insert:
            RegistroAcaoDocumentoTexto.objects.create(tipo=RegistroAcaoDocumento.TIPO_CRIACAO, documento=self, ip=ip, observacao='')

    def get_url_autenticacao(self, completa=False):
        url = settings.SITE_URL + '/autenticar-documento/'
        if completa:
            url += f'?codigo_verificador={self.id:d}&codigo_autenticacao={self.codigo_autenticacao}'
        return url

    ##################################################################################
    #
    #   Conjunto de Getters/Properties
    #
    ##################################################################################

    def pode_ser_excluido(self, user=None):
        user = user or tl.get_user()

        if self.eh_documento_de_setor:
            # Quando e quem pode excluir documento (documentos de setor)
            # - Documento (estah_em_rascunho or estah_concluido) E NAO TER tem_identificador_definitivo
            # - Criador do documento OU (quem possa editar o documento E tenha setor_suap no mesmo setor dono
            # https://gitlab.ifrn.edu.br/cosinf/suap/-/issues/6426

            quando_pode = (self.estah_em_rascunho or self.estah_concluido) and not self.tem_identificador_definitivo
            quem_pode = self.usuario_criacao == user or (self.tem_permissao_editar(user) and user.get_relacionamento().setor == self.setor_dono)

            return quando_pode and quem_pode
        else:
            return self.usuario_criacao == user and (self.estah_em_rascunho or self.estah_concluido) and not self.tem_identificador_definitivo

    def estah_marcado_como_favorito(self, user=None):
        user = user or tl.get_user()
        return self.usuarios_marcadores_favoritos.all().filter(id=user.id).exists()

    @property
    def tipo(self):
        return self.modelo.tipo_documento_texto

    @property
    def usa_sequencial_anual(self):
        return self.tipo.usa_sequencial_anual

    @property
    def get_identificador(self):
        if self.tem_identificador_definitivo:
            if not self.eh_documento_pessoal:
                if self.usa_sequencial_anual:
                    result = f'{self.identificador_tipo_documento_sigla} {self.identificador_numero}/{self.identificador_ano} - {self.identificador_setor_sigla}'
                else:
                    result = f'{self.identificador_tipo_documento_sigla} {self.identificador_setor_sigla} N° {self.identificador_numero}'
            else:
                result = f'{self.identificador_tipo_documento_sigla} {self.identificador_numero}/{self.identificador_ano} - {self.identificador_dono_documento}'
        else:
            # ZERO indica que o documento está sendo criado, portando não tem "id"x.
            if not self.eh_documento_pessoal:
                result = f'Documento {self.pk or 0:d}'
            else:
                result = f'Documento Pessoal {self.pk or 0:d}'

        return result

    @property
    def tem_identificador_definitivo(self):
        if not self.eh_documento_pessoal:
            return self.identificador_tipo_documento_sigla and self.identificador_numero and self.identificador_setor_sigla
        else:
            return self.identificador_tipo_documento_sigla and self.identificador_numero and self.identificador_ano

    @property
    def conteudo_eh_imutavel(self):
        '''
        Este método retrona True caso o conteúdo do documento em si (cabeçalho, corpo e rodapé) não podem mais sofrer
        alteração, caso contrário retorna False.

        Obs: As assinaturas não são consideradas conteúdo do documento, logo um documento com conteúdo imutável pode
        ainda receber mais assinaturas.
        :return:
        '''
        return self.tem_identificador_definitivo or self.tem_assinaturas

    @property
    def get_vinculos_documento_texto(self):
        return self.vinculos_como_documento_texto_base.all() | self.vinculos_como_documento_texto_alvo.all()

    @property
    def get_vinculos_documento_texto_to_display(self):
        result = list()
        for vinculo in self.get_vinculos_documento_texto:
            if vinculo.documento_texto_base == self:
                descricao = vinculo.get_descricao_voz_ativa(incluir_documento_texto_base=False, incluir_documento_texto_alvo=False)
                documento_vinculado = vinculo.documento_texto_alvo
            else:
                descricao = vinculo.get_descricao_voz_passiva(incluir_documento_texto_base=False, incluir_documento_texto_alvo=False)
                documento_vinculado = vinculo.documento_texto_base

            result.append({'id': vinculo.id, 'descricao': descricao, 'documento_vinculado': documento_vinculado})

        return result

    @property
    def estah_em_revisado(self):
        return self.status == DocumentoStatus.STATUS_REVISADO

    @property
    def estah_em_rascunho(self):
        return self.status == DocumentoStatus.STATUS_RASCUNHO

    @property
    def estah_concluido(self):
        return self.status == DocumentoStatus.STATUS_CONCLUIDO

    @property
    def estah_cancelado(self):
        return self.status == DocumentoStatus.STATUS_CANCELADO

    @property
    def estah_aguardando_assinatura(self):
        return self.status == DocumentoStatus.STATUS_AGUARDANDO_ASSINATURA

    @property
    def estah_em_revisao(self):
        return self.status == DocumentoStatus.STATUS_EM_REVISAO

    @property
    def estah_assinado(self):
        return self.status == DocumentoStatus.STATUS_ASSINADO

    @property
    def estah_finalizado(self):
        return self.status == DocumentoStatus.STATUS_FINALIZADO

    # TODO: Devido a assinatura "balizadora", o método não pode mais se basear na data de cria
    @classmethod
    def get_ultimo_documento_com_identificador_definitivo(cls, tipo_documento_texto, setor, ano):
        identificador_numero_max = cls.objects.filter(
            modelo__tipo_documento_texto=tipo_documento_texto,
            setor_dono=setor,
            identificador_ano=ano
        ).aggregate(Max('identificador_numero'))['identificador_numero__max']
        if identificador_numero_max:
            return cls.objects.get(modelo__tipo_documento_texto=tipo_documento_texto, setor_dono=setor, identificador_ano=ano, identificador_numero=identificador_numero_max)
        return None

    def get_registros_acoes(self, ocultar_acesso_cargo=True):
        qs = RegistroAcaoDocumentoTexto.objects.filter(documento=self)
        #
        if ocultar_acesso_cargo:
            return qs.exclude(tipo=RegistroAcaoDocumentoTexto.TIPO_ACESSO_EM_FUNCAO_CARGO)
        return qs

    @deprecated('A função clonar_documento na view assumiu esta responsabilidade')
    def clonar_documento(self, usuario, setor_dono):
        with transaction.atomic():
            documento_novo = DocumentoTexto.objects.create(
                setor_dono=setor_dono,
                usuario_criacao=usuario,
                assunto=self.assunto,
                data_ultima_modificacao=get_datetime_now(),
                usuario_ultima_modificacao=usuario,
                modelo=self.modelo,
                nivel_acesso=self.nivel_acesso,
            )
            # Quando o documento é criado o conteúdo do cabeçalho, rodapé e do corpo são definidos com base no modelo
            # do documento. Uma vez definido isso, se faz necessário apenas copiar o corpo do documento que está sendo
            # clonado.
            # Se o documento em questão for restrito ou sigiloso e não tiver definido a hipotese legal dele o seu clone
            # colocado no nível de acesso padrão.
            documento_novo.corpo = self.corpo
            if self.nivel_acesso in [Documento.NIVEL_ACESSO_RESTRITO, Documento.NIVEL_ACESSO_SIGILOSO]:
                if not self.hipotese_legal:
                    documento_novo.nivel_acesso = self.modelo.nivel_acesso_padrao
                else:
                    documento_novo.hipotese_legal = self.hipotese_legal

            documento_novo.save()
            return documento_novo

    def montar_cabecalho_rodape_padrao(self):
        # Se o documento tem conteúdo redundante é sinal de que foram criados a moda antiga, ou seja, fazendo uma cópia
        # dos mesmos campos do tipo de documento do respectivo modelo de documento. Somente quem já tiver sido criado a
        # moda antiga terá a informação atualizada.
        if self.has_cabecalho_rodape_redundante:
            self.cabecalho = self.__processar_conteudo_documento(self.tipo.cabecalho_padrao, estagio_processamento_variavel=EstagioProcessamentoVariavel.CRIACAO_DOCUMENTO)
            self.rodape = self.__processar_conteudo_documento(self.tipo.rodape_padrao, estagio_processamento_variavel=EstagioProcessamentoVariavel.CRIACAO_DOCUMENTO)

        self.cabecalho_base_original = TipoDocumentoTextoHistoricoConteudo.objects.get(
            tipo_documento_texto=self.tipo, area_conteudo=TipoDocumentoTextoHistoricoConteudo.CABECALHO, hash=self.tipo.cabecalho_hash
        )
        self.rodape_base_original = TipoDocumentoTextoHistoricoConteudo.objects.get(
            tipo_documento_texto=self.tipo, area_conteudo=TipoDocumentoTextoHistoricoConteudo.RODAPE, hash=self.tipo.rodape_hash
        )

    def montar_corpo_padrao(self):
        if self.modelo and not self.corpo:
            self.corpo = self.__processar_conteudo_documento(self.modelo.corpo_padrao, estagio_processamento_variavel=EstagioProcessamentoVariavel.CRIACAO_DOCUMENTO)

    def atribuir_identificador_e_processar_conteudo_final(
        self, identificador_tipo_documento_sigla, identificador_numero,
            identificador_ano, identificador_setor_sigla, identificador_dono_documento,
            data_emissao
    ):

        self.identificador_tipo_documento_sigla = identificador_tipo_documento_sigla
        self.identificador_numero = identificador_numero
        self.identificador_ano = identificador_ano
        # Documentos pessoais não possuem identificador_setor_sigla
        if identificador_setor_sigla:
            self.identificador_setor_sigla = identificador_setor_sigla
        if identificador_dono_documento:
            self.identificador_dono_documento = identificador_dono_documento
        self.data_emissao = data_emissao

        # Registrando as variaveis utilizadas pelo documento antes dele ser assinado. Nesse caso, o estágio de processamento
        # da variável não vai fazer diferença uma vez que estamos passando os parâmetros "usuario" e "setor_dono", assim
        # como faz iternamente o método "__processar_conteudo_documento".
        variaveis = get_variaveis(documento_identificador=self.get_identificador, usuario=self.usuario_criacao, setor_dono=self.setor_dono)
        self.variaveis = json.dumps(variaveis)

        if self.has_cabecalho_rodape_redundante:
            self.cabecalho = processar_template_ckeditor(texto=self.cabecalho, variaveis=variaveis)
            self.corpo = processar_template_ckeditor(texto=self.corpo, variaveis=variaveis)
            self.rodape = processar_template_ckeditor(texto=self.rodape, variaveis=variaveis)

        # Inserindo no corpo os anexos do documento
        anexos = self.get_todos_anexos()
        if anexos:
            self.corpo = self.corpo + processar_template_documentos_anexados({'anexos': anexos})

    def __processar_conteudo_documento(self, conteudo, estagio_processamento_variavel=None):
        if self.conteudo_eh_imutavel:
            if self.has_cabecalho_rodape_otimizado:
                return processar_template_ckeditor(conteudo, self.variaveis_as_dict)
            else:
                return conteudo
        else:
            variaveis_correntes = get_variaveis(
                documento_identificador=self.identificador, estagio_processamento_variavel=estagio_processamento_variavel, usuario=self.usuario_criacao, setor_dono=self.setor_dono
            )
            return processar_template_ckeditor(conteudo, variaveis_correntes)

    @property
    def has_cabecalho_rodape_otimizado(self):
        return self.cabecalho_base_original is not None and self.rodape_base_original is not None

    @property
    def has_cabecalho_rodape_redundante(self):
        return bool(self.cabecalho + self.rodape)

    @property
    def variaveis_as_dict(self):
        if self.variaveis:
            return json.loads(self.variaveis)
        else:
            return None

    @property
    def cabecalho_para_visualizacao(self):
        if self.has_cabecalho_rodape_otimizado:
            return self.__processar_conteudo_documento(self.cabecalho_base_original.conteudo)
        else:
            return self.__processar_conteudo_documento(self.cabecalho)

    @property
    def rodape_para_visualizacao(self):
        if self.has_cabecalho_rodape_otimizado:
            return self.__processar_conteudo_documento(self.rodape_base_original.conteudo)
        else:
            return self.__processar_conteudo_documento(self.rodape)

    @property
    def corpo_para_visualizacao(self):
        return self.__processar_conteudo_documento(self.corpo)

    @property
    def tem_assinaturas(self):
        return AssinaturaDocumentoTexto.objects.filter(documento=self).exists()

    def get_assinaturas(self,):
        assinaturas = list()
        for assinatura in AssinaturaDocumentoTexto.objects.filter(documento=self):
            assinaturas.append(f"{assinatura.pessoa}")
        return assinaturas

    def get_primeira_assinatura(self):
        return self.assinatura_balizadora

    def get_ultima_assinatura(self):
        assinatura_documento_texto = AssinaturaDocumentoTexto.objects.filter(documento=self).order_by('-assinatura__data_assinatura').first()
        return assinatura_documento_texto

    def get_data_primeira_assinatura(self):
        assinatura_documento_texto = self.get_primeira_assinatura()
        return assinatura_documento_texto.assinatura.data_assinatura if assinatura_documento_texto else None

    def get_data_ultima_assinatura(self):
        assinatura_documento_texto = self.get_ultima_assinatura()
        return assinatura_documento_texto.assinatura.data_assinatura if assinatura_documento_texto else None

    def get_data_finalizacao(self):
        registro_acao_finalizacao = RegistroAcaoDocumentoTexto.objects.filter(documento=self, tipo=RegistroAcaoDocumentoTexto.TIPO_FINALIZACAO).order_by('-data').first()
        if registro_acao_finalizacao:
            return registro_acao_finalizacao.data
        return None

    @property
    def conteudo(self):
        return '{}|{}|{}|{}|{}'.format(
            self.id, self.cabecalho_para_visualizacao, self.corpo_para_visualizacao, self.rodape_para_visualizacao, self.data_criacao.strftime('%d/%m/%Y')
        )

    @property
    def hash_conteudo(self):
        return gerar_hash(self.conteudo)

    @property
    def hash_conteudo_as_sha256(self):
        return gerar_hash(self.conteudo, use_sha256=True)

    @property
    def tamanho_em_bytes(self):
        try:
            size = len(f'{self.cabecalho_para_visualizacao}{self.corpo_para_visualizacao}{self.rodape_para_visualizacao}')
            return size
        except Exception:
            return 0

    @property
    def tamanho_em_kb(self):
        try:
            size = round((self.tamanho_em_bytes / 1024.0), 2)
            return size
        except Exception:
            return 0

    @property
    def tamanho_em_mb(self):
        try:
            size = round((self.tamanho_em_kb / 1024.0), 2)
            return size
        except Exception:
            return 0

    def get_url_publica(self):
        return settings.SITE_URL + f'/documento_eletronico/imprimir_documento_pdf/{self.id:d}/?hash={self.hash_conteudo}'

    ##################################################################################
    #
    #   Conjunto de métodos que lidam com as permissões para trocar de estado
    #
    ##################################################################################
    def tem_permissao_ler(self, user, consulta_publica_hash=None, leitura_para_barramento=False, eh_consulta_publica=False):
        # Se é uma consulta pública (verifica autenticidade do doc)
        #   ou Consulta para o Barramento
        #   ou Consulta publica para ver processo na integra
        if consulta_publica_hash:
            return self.eh_publico and self.estah_finalizado and consulta_publica_hash == self.hash_conteudo
        # Ou a consulta em si seja para a impressão dos documentos de um processo ou consulta para barramento....
        elif eh_consulta_publica or leitura_para_barramento:
            return self.eh_publico and self.estah_finalizado
        else:
            #
            if not self.eh_documento_pessoal:
                # Se for documento vinculado a SETOR
                # -----------------------------------
                # Permissão "Natural", dada pelo módulo de Documento Eletrônico.
                if user.has_perm('documento_eletronico.view_documentotexto') and (
                    self.usuario_criacao == user
                    or (self.eh_publico and self.estah_finalizado)
                    or (DocumentoTexto.objects.compartilhados(user, NivelPermissao.LER) | DocumentoTexto.objects.proprios(user)).filter(pk=self.pk).exists()
                ):
                    return True
                # Permissão "Alternativa", dada pelo módulo de Processo Eletrônico.
                elif self.eh_restrito:
                    usuario_pode_ver_doc_restrito_via_processo = usuario_deve_ter_acesso_a_documento_restrito_atraves_de_processo(user=user, documento=self)
                    usuario_pode_ver_doc_restrito_via_juntada_pendente = usuario_deve_ter_acesso_a_documento_restrito_atraves_de_solicitacao_juntada_pendente(user=user, documento=self)
                    if usuario_pode_ver_doc_restrito_via_processo or usuario_pode_ver_doc_restrito_via_juntada_pendente:
                        return True
                elif self.eh_publico and self.estah_cancelado:
                    return usuario_deve_ter_acesso_a_documento_publico_e_cancelado_atraves_de_processo(user=user, documento=self)
            else:
                # Se for documento vinculado a PESSOA
                # -----------------------------------
                pode_ler = self.usuario_criacao == user or (self.eh_publico and self.estah_finalizado)
                estah_compartilhado = DocumentoTextoPessoal.objects.compartilhados(user, NivelPermissao.LER).filter(pk=self.pk).exists()
                if user.has_perm('documento_eletronico.view_documentotextopessoal') and (pode_ler or estah_compartilhado):
                    return True
                elif self.eh_restrito:
                    usuario_pode_ver_doc_restrito_via_processo = usuario_deve_ter_acesso_a_documento_restrito_atraves_de_processo(user=user, documento=self)
                    usuario_pode_ver_doc_restrito_via_juntada_pendente = usuario_deve_ter_acesso_a_documento_restrito_atraves_de_solicitacao_juntada_pendente(user=user, documento=self)
                    if usuario_pode_ver_doc_restrito_via_processo or usuario_pode_ver_doc_restrito_via_juntada_pendente:
                        return True
                elif self.eh_publico and self.estah_cancelado:
                    return usuario_deve_ter_acesso_a_documento_publico_e_cancelado_atraves_de_processo(user=user, documento=self)
        #
        return False

    def tem_permissao_estrita_leitura(self, pessoa=None):
        pessoa_pode_ler = self.compartilhamento_pessoa_documento.filter(pessoa_permitida=pessoa, nivel_permissao=NivelPermissao.LER).exists()
        pessoa_pode_editar = self.compartilhamento_pessoa_documento.filter(pessoa_permitida=pessoa, nivel_permissao=NivelPermissao.EDITAR).exists()
        if pessoa_pode_ler or pessoa_pode_editar:
            return True
        return False

    # TODOD: Rever esse método, pois ele está permitido que o usuário que teve a assinatura solicitada possa solicitar
    # novas assinaturas. É isso mesmo? Outra coisa, precisamos rever todos os Managers de Documento, para incluir como
    # primeiro parâmetro, sendo opcional, o id do próprio documento, visando desempenho!
    def tem_permissao_editar(self, user):
        if self.eh_documento_pessoal:
            return self.usuario_criacao == user or DocumentoTextoPessoal.objects.compartilhados(user, NivelPermissao.EDITAR)

        if user.eh_aluno:
            return False

        if user.get_vinculo().eh_usuario_externo():
            return False

        return self.usuario_criacao == user or (DocumentoTexto.objects.compartilhados(user, NivelPermissao.EDITAR) | DocumentoTexto.objects.proprios(user)).filter(pk=self.pk).exists()

    def pode_editar(self, user=None):
        user = user or tl.get_user()
        if not self.eh_documento_pessoal:
            solicitacao_balizadora_pendente = self.get_solicitacao_balizadora_pendente()
            if (self.estah_em_revisao and self.sou_revisor(user)) or (
                solicitacao_balizadora_pendente and solicitacao_balizadora_pendente.solicitado.user == user and not solicitacao_balizadora_pendente.solicitado.eh_aluno
            ):
                return True
            elif self.estah_em_rascunho:
                return self.tem_permissao_editar(user)
            return False
        else:
            return self.tem_permissao_editar(user) and self.estah_em_rascunho

    def pode_concluir_documento(self, user=None):
        user = user or tl.get_user()

        if not self.eh_documento_pessoal:
            setor_dono = self.setor_dono
            setor_usuario_criacao = self.usuario_criacao.get_relacionamento().setor
            servidores_com_acesso = Servidor.objects.ativos().filter(setor=setor_dono)
            estagiarios_com_acesso = Servidor.objects.estagiarios().filter(setor=setor_dono)
            servidores_e_estagiarios_do_setor = servidores_com_acesso or estagiarios_com_acesso

            # Em um documento revisado, todos os servidores do setor podem deferir
            if self.estah_em_revisado and (
                self.usuario_criacao == user
                or (user.eh_servidor and user.get_relacionamento().eh_chefe_do_setor_hoje(setor_dono))
                or (user.eh_servidor and user.get_relacionamento().eh_chefe_do_setor_hoje(setor_usuario_criacao))
                or user.get_relacionamento() in servidores_e_estagiarios_do_setor
            ):
                return True
            # Senão se o documento não estiver em modo rascunho,
            # uma minuta não pode ser gerada a partir dele.
            elif not self.estah_em_rascunho:
                return False
            # Senão, verifique se tem permissão
            else:
                return self.pode_editar(user)
        else:
            return self.pode_editar(user)

    def pode_receber_anexos(self):
        user = tl.get_user()

        # Soh pode receber anexo se
        # - estiver em rascunho
        # - for o usuario_criacao
        # - se o tipo permite_documentos_anexos
        # - se o documento que for receber anexo (self) for anexo de outro

        foi_anexado = DocumentoTextoAnexoDocumentoTexto.objects.filter(documento_anexado=self)

        return self.estah_em_rascunho and \
            self.usuario_criacao == user and \
            self.modelo.tipo_documento_texto.permite_documentos_anexos and \
            not foi_anexado

    # Um documento só pode ser cancelado se não estiver em um processo.
    # E seu estado for assinado ou finalizado
    def pode_ser_cancelado(self, user=None):
        user = user or tl.get_user()
        if (self.estah_concluido or self.estah_assinado or self.estah_finalizado) and (self.usuario_criacao == user) and \
                not self.estah_vinculado_a_processos_e_nao_foi_removido() and not existem_solicitacoes_juntada_pendentes(self):
            return True
        #
        return False

    def get_vinculos_com_processos(self):
        if app_processo_eletronico_estah_instalada():
            return self.documentotextoprocesso_set.all()
        # TODO: Isso aqui tem que ser revisto pois acredito que vai gerar excessão caso o módulo de documento eletrônico
        # não esteja instalado.
        return self.documentotextoprocesso_set.none()

    def estah_vinculado_a_processos(self):
        return self.get_vinculos_com_processos().exists()

    def estah_vinculado_a_processos_e_nao_foi_removido(self):
        return self.get_vinculos_com_processos().filter(data_hora_remocao__isnull=True).exists()

    #
    # Verificar se um documento em minuta pode ser revertido para rascunho.
    #
    def pode_retornar_para_rascunho(self, user=None):
        user = user or tl.get_user()
        return self.estah_concluido and self.tem_permissao_editar(user)

    #   Os metodos a seguir lidam com os possiveis estados que um revisão pode estar
    def pode_solicitar_revisao(self, user=None):
        if self.eh_documento_pessoal:
            return False

        # Apenas uma minuta pode ser enviada para revisão
        if not self.estah_concluido:
            return False
        #
        user = user or tl.get_user()
        if self.usuario_criacao == user:
            return True
        else:
            pessoa = user.get_profile()
            setor = get_setor(user)
            if self.tem_permissao_editar(user):
                return True
            elif self.compartilhamento_pessoa_documento.filter(pessoa_permitida=pessoa, nivel_permissao=NivelPermissao.EDITAR).exists():
                return True
            documento_sigiloso = self.nivel_acesso == self.NIVEL_ACESSO_SIGILOSO
            if not documento_sigiloso and self.setor_dono == setor:
                return True
            return False

    def pode_cancelar_revisao(self, user=None):
        if not self.estah_em_revisao:
            return False
        user = user or tl.get_user()
        #
        # O criar do arquivo pode cancelar uma revisao
        #
        if self.usuario_criacao == user:
            return SolicitacaoRevisao.objects.filter(documento=self, data_resposta__isnull=True).exists()
        #
        # O solicitante pode cancelar a solicitação
        #
        return SolicitacaoRevisao.objects.filter(documento=self, data_resposta__isnull=True).filter(Q(solicitante=user) | Q(revisor=user.get_profile())).exists()

    # Apenas o criador e os servidores do setor de criação do documento podem rejeitar a revisão
    def pode_rejeitar_revisao(self, user=None):
        if not self.estah_em_revisado:
            return False
        else:
            if self.usuario_criacao == user:
                return True
            user_logado = user or tl.get_user()
            servidor_dono_documento = self.usuario_criacao.get_relacionamento()
            setor_servidor_dono_documento = servidor_dono_documento.setor
            servidores_com_acesso = Servidor.objects.ativos().filter(setor=setor_servidor_dono_documento)
            estagiarios_com_acesso = Servidor.objects.estagiarios().filter(setor=setor_servidor_dono_documento)
            servidores_e_estagiarios_do_setor = servidores_com_acesso or estagiarios_com_acesso
            servidores_e_estagiarios_do_setor_com_permissao_ao_setor_dono = list()

            for servidor in servidores_e_estagiarios_do_setor:
                if setor_servidor_dono_documento in get_todos_setores(servidor.get_user()):
                    servidores_e_estagiarios_do_setor_com_permissao_ao_setor_dono.append(servidor)
            return user_logado.get_relacionamento() in servidores_e_estagiarios_do_setor_com_permissao_ao_setor_dono

    def get_ultima_solicitacao_revisao_sem_avaliacao(self):
        if SolicitacaoRevisao.objects.filter(documento=self, data_avaliacao__isnull=True).order_by('-data_resposta').exists():
            return SolicitacaoRevisao.objects.filter(documento=self, data_avaliacao__isnull=True).order_by('-data_resposta').first()
        return None

    # Metodos que lidam com as assinaturas
    def pode_solicitar_assinatura(self, user=None):
        user = user or tl.get_user()
        # Apenas uma minuta ou uma documento aguardando assinatura podem ser alvos de uma nova assinatura
        # E apenas os usuários que podem editar um documento, podem solicitar a assinatura de alguém.
        if (self.estah_concluido or self.estah_aguardando_assinatura or self.estah_assinado) and self.get_solicitacao_assinatura_com_anexacao_processo() is None:
            return self.tem_permissao_editar(user)

    def pode_assinar(self, user=None):
        user = user or tl.get_user()
        vinculo = user.get_relacionamento()
        if not vinculo.papeis_ativos.exists():
            return False
        # já que a solicitação já adiciona o usuario como visualizador
        usuario_assinou = AssinaturaDocumentoTexto.objects.filter(documento=self, assinatura__pessoa=user.get_profile()).exists()
        # Um usuário pode assinar um documento, se ele não tiver assinado anteriormente.  Se ele tem permissão de
        # editar ou se possui uma solicitação pendente
        return not usuario_assinou and (
            (self.estah_assinado and self.usuario_criacao == user)
            or (self.estah_concluido and self.tem_permissao_editar(user))
            or (self.estah_aguardando_assinatura and self.tem_solicitacao_assinatura_pendente(user))
        )

    # Posso cancelar um assinatura enquanto o documento nao tiver uma assinatura aceita
    # e se eu for o solicitante.
    def pode_cancelar_assinaturas(self, user=None):
        user = user or tl.get_user()
        solicitacao = (
            SolicitacaoAssinatura.objects.filter(documento=self, status=SolicitacaoStatus.STATUS_ESPERANDO)
            .filter(Q(solicitante=user.get_profile()) | Q(solicitado=user.get_profile()))
            .exists()
        )
        # Se existe uma solicitação de assinatura pendente, então podemos cancela-la
        return True if solicitacao else False

    # documento com id diferente mas mesmo ano e numero para um dado setor e tipo.
    def pode_resgatar(self,):
        documento_com_mesmo_idenficador = DocumentoTexto.objects.filter(
            modelo__tipo_documento_texto=self.tipo, setor_dono=self.setor_dono, identificador_numero=self.identificador_numero, identificador_ano=self.identificador_ano
        ).exclude(id=self.id)
        return not documento_com_mesmo_idenficador.exists()

    def clean_hipotese_legal(self):
        '''
        A validação da hipótese legal só vai ser realizada nos casos em que o status anterior do documento era rascunho.
        Neste cenário, caso o nível do acesso seja sigiloso ou restrito, o usuário terá condições de editar os dados
        básicos do documento e informar a hipótese legal.
        '''
        if self.pk:
            if self.eh_documento_pessoal:
                documento_texto_old = DocumentoTextoPessoal.objects.filter(pk=self.id).first()
                if documento_texto_old and documento_texto_old.status == DocumentoStatus.STATUS_RASCUNHO:
                    super().clean_hipotese_legal()
            else:
                documento_texto_old = DocumentoTexto.objects.filter(pk=self.id).first()
                if documento_texto_old and documento_texto_old.status == DocumentoStatus.STATUS_RASCUNHO:
                    super().clean_hipotese_legal()

    def pode_finalizar_documento(self, user=None):
        '''
        Verifica se o documento está assinado e se o usuário pode editar o documento. Caso afirmativo para as duas situações
        retorna verdadeiro.
        '''
        user = user or tl.get_user()
        if self.estah_assinado and self.tem_permissao_editar(user):
            return True
        else:
            return False

    def pode_imprimir(self, user=None):
        user = user or tl.get_user()
        if (self.estah_concluido or self.estah_assinado or self.estah_finalizado) and self.pode_ler(user):
            return True
        return False

    def get_or_create_solicitacao_balizadora(self, solicitado, solicitante):
        try:
            # Se existe alguma solicitação balizadora retorne.
            obj = SolicitacaoAssinatura.objects.get(
                documento_id=self.id, condicionantes__isnull=True, status__in=[SolicitacaoStatus.STATUS_ESPERANDO, SolicitacaoStatus.STATUS_DEFERIDA]
            )
        except SolicitacaoAssinatura.DoesNotExist:
            obj = SolicitacaoAssinatura(documento_id=self.id, solicitado=solicitado, solicitante=solicitante)
            obj.save()
        return obj

    def _assinar(self, assinatura):
        # Cria a solicitação de assinatura balizadora, se necessário for.
        self.get_or_create_solicitacao_balizadora(assinatura.pessoa, assinatura.pessoa.user)

        assinatura, _ = AssinaturaDocumentoTexto.objects.get_or_create(documento=self, assinatura=assinatura)
        #
        if not self.assinatura_balizadora:
            self.assinatura_balizadora = assinatura

    @transaction.atomic()
    def assinar_via_senha(self, user, papel, data_emissao):
        if not self.tem_identificador_definitivo:
            raise ValidationError("Documento sem identificador definitivo.")

        # Esta restrição foi posta aqui, ao invés do método "gerar_assinatura_documento_senha", porque ela só deve
        # ser aplicada a documentos criados dentro do SUAP.
        if not RestricaoAssinatura.documentoTextoPodeSerAssinado(papel=papel, documento_texto=self):
            raise ValidationError(
                'O servidor "{}", usando o perfil "{} ({})", '
                'não pode assinar o tipo de documento "{}."'.format(user, papel, papel.papel_content_object, self.modelo.tipo_documento_texto)
            )

        pessoa_fisica = user.get_profile()
        if self.pode_assinar(user) and papel is not None:
            assinatura, _ = Assinatura.objects.get_or_create(
                # Dados do assinante
                pessoa=pessoa_fisica,
                # Devido a issue 5135 ficou definido que o documento tambem
                # pode ser assinado por estrangeiro sem cpf. Assim, fica salvo na
                # assinatura um CPF ou PASSAPORTE. Para saber mais veja a issue.
                cpf=pessoa_fisica.get_cpf_ou_passaporte(),
                # Dados da assinatura
                hmac=gerar_assinatura_documento_senha(self, pessoa_fisica),
                nome_papel=papel.detalhamento,
                papel=papel,
                data_assinatura=data_emissao,
            )

            self._assinar(assinatura)
            #
            self.save()

            # Assina os anexos simples deste documento
            # Garante que os anexos terao o mesmo nivel de acesso do pai
            anexos_simples = self.get_apenas_anexos_digitalizados_simples()
            for anexo_simples in anexos_simples:
                anexo_simples.nivel_acesso = self.nivel_acesso
                anexo_simples.hipotese_legal = self.hipotese_legal
                anexo_simples.save()
                anexo_simples.assinar_via_senha(user, papel)

        else:
            raise ValidationError(f'O documento não pode ser assinado por {pessoa_fisica}.')

    @transaction.atomic()
    def assinar_via_token(self, cert, hmac, pessoa_fisica, papel):

        if self.pode_assinar(pessoa_fisica.user):
            # Procuro o documento já possui uma assinatura com um dado
            assinatura, _ = AssinaturaDigital.objects.get_or_create(
                pessoa=pessoa_fisica,
                cpf=pessoa_fisica.cpf,
                papel=papel,
                defaults={
                    'hmac': hmac,
                    'chave_publica': cert.get_public_key(),
                    'numero_serie_certificado': cert.serial_number,
                    'certificado_criado_em': cert.data_range.begin(),
                    'certificado_expira_em': cert.data_range.end(),
                },
            )
            self._assinar(assinatura)
            self.save()
        else:
            raise ValidationError(f'O documento não pode ser assinado por {pessoa_fisica}.')

    ##################################################################################
    #
    #   Conjunto de métodos que lidam as transições entre estados
    #
    ##################################################################################

    @transition(
        field=status,
        source=[DocumentoStatus.STATUS_RASCUNHO, DocumentoStatus.STATUS_REVISADO, DocumentoStatus.STATUS_AGUARDANDO_ASSINATURA],
        target=DocumentoStatus.STATUS_CONCLUIDO,
        permission=lambda instance: instance.pode_concluir_documento(),
    )
    def concluir(self):
        pass

    @transition(field=status, source=[DocumentoStatus.STATUS_CONCLUIDO, DocumentoStatus.STATUS_REVISADO], target=DocumentoStatus.STATUS_RASCUNHO)
    def editar_documento(self):
        pass

    @transition(
        field=status, source=[DocumentoStatus.STATUS_CONCLUIDO, DocumentoStatus.STATUS_ASSINADO, DocumentoStatus.STATUS_FINALIZADO], target=DocumentoStatus.STATUS_CANCELADO
    )
    def cancelar_documento(self):
        pass

    @transition(field=status, source=DocumentoStatus.STATUS_CONCLUIDO, target=DocumentoStatus.STATUS_EM_REVISAO)
    def colocar_em_revisao(self):
        pass

    @transition(field=status, source=DocumentoStatus.STATUS_EM_REVISAO, target=DocumentoStatus.STATUS_CONCLUIDO)
    def cancelar_revisao(self):
        pass

    @transition(field=status, source=DocumentoStatus.STATUS_EM_REVISAO, target=DocumentoStatus.STATUS_REVISADO)
    def finalizar_revisao(self):
        pass

    @transition(field=status, source=[DocumentoStatus.STATUS_CONCLUIDO, DocumentoStatus.STATUS_ASSINADO], target=DocumentoStatus.STATUS_AGUARDANDO_ASSINATURA)
    def solicitar_assinatura(self):
        pass

    @transition(field=status, source=DocumentoStatus.STATUS_AGUARDANDO_ASSINATURA, target=DocumentoStatus.STATUS_CONCLUIDO)
    def cancelar_assinatura(self):
        pass

    @transition(
        field=status,
        source=[DocumentoStatus.STATUS_AGUARDANDO_ASSINATURA, DocumentoStatus.STATUS_CONCLUIDO, DocumentoStatus.STATUS_ASSINADO],
        target=DocumentoStatus.STATUS_ASSINADO,
    )
    def marcar_como_assinado(self):
        pass

    @transition(field=status, source=DocumentoStatus.STATUS_ASSINADO, target=DocumentoStatus.STATUS_FINALIZADO)
    def finalizar_documento(self):
        if self.modelo.tipo_documento_texto.vincular_pessoa:
            servidores_interessados = []
            vinculos_interessados = []
            texto_documento = BeautifulSoup(self.corpo, 'html.parser').text
            for servidor in Servidor.objects.all():
                if servidor.matricula in texto_documento:
                    servidores_interessados.append(servidor)
                    vinculos_interessados.append(servidor.get_vinculo())

            self.interessados.set(servidores_interessados)
            url_documento = urljoin(settings.SITE_URL, self.get_absolute_url())
            assunto = '[SUAP] Documento Eletrônico: Vinculação como interessado no documento'
            mensagem = f'''<h1>Documento Eletrônico</h1> <h2>Vinculação como interessado no documento</h2>
                <p>Você foi vinculada ao documento <a href="{url_documento}">{self}</a> automaticamente pelo SUAP.
                </p>'''

            send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, vinculos_interessados, html=mensagem, fail_silently=True)

    def get_status(self):
        return self.get_status_display()

    def tem_historico_revisoes(self):
        return reversion.get_for_object(self).exists()

    def get_solicitacao_balizadora(self):
        return self.solicitacaoassinatura_set.filter(status=SolicitacaoStatus.STATUS_DEFERIDA, condicionantes__isnull=True).first()

    def get_qs_solicitacao_balizadora_pendente(self):
        return self.solicitacaoassinatura_set.filter(status=SolicitacaoStatus.STATUS_ESPERANDO, condicionantes__isnull=True)

    def tem_solicitacao_balizadora_pendente(self):
        return self.get_qs_solicitacao_balizadora_pendente().exists()

    def get_solicitacao_balizadora_pendente(self):
        return self.get_qs_solicitacao_balizadora_pendente().first()

    def get_solicitacao_assinatura_com_anexacao_processo(self):
        from processo_eletronico.models import \
            SolicitacaoAssinaturaComAnexacaoProcesso

        solicitacao_balizadora_pendente = None
        if self.tem_solicitacao_balizadora_pendente():
            solicitacao_balizadora_pendente = self.get_solicitacao_balizadora_pendente()
        elif SolicitacaoAssinaturaComAnexacaoProcesso.objects.filter(solicitacao_assinatura=self.get_solicitacao_balizadora()):
            processo = SolicitacaoAssinaturaComAnexacaoProcesso.objects.filter(solicitacao_assinatura=self.get_solicitacao_balizadora())[0].processo_para_anexar
            if processo.tem_documentos_a_ser_anexado_aguardando_assinatura() and processo.get_documentos_aguardando_para_serem_anexados():
                solicitacao_balizadora_pendente = self.get_solicitacao_balizadora()

        if hasattr(solicitacao_balizadora_pendente, 'solicitacaoassinaturacomanexacaoprocesso'):
            return solicitacao_balizadora_pendente.solicitacaoassinaturacomanexacaoprocesso

        return None

    def get_solicitacoes_assinatura(self):
        return self.solicitacaoassinatura_set.all()

    def get_solicitacoes_juntada_pendentes(self):
        return solicitacoes_juntada_pendentes(self)

    def solicitado_por(self):
        return SolicitacaoAssinatura.objects.filter(documento=self, data_resposta__isnull=True).values_list('solicitante__pessoafisica__nome_usual', flat=True)

    def solicitado_a(self):
        user = tl.get_user()
        return SolicitacaoAssinatura.objects.filter(documento=self, data_resposta__isnull=True, solicitante=user).values_list(
            'solicitado__user__pessoafisica__nome_usual', flat=True
        )

    def revisoes(self):
        return SolicitacaoRevisao.objects.filter(documento=self)

    def revisor(self):
        return set(SolicitacaoRevisao.objects.filter(documento=self).values_list('revisor__pessoafisica__nome_usual', flat=True).order_by('-data_solicitacao'))

    def sou_revisor(self, user=None):
        me = user or tl.get_user()
        return SolicitacaoRevisao.objects.filter(documento=self, data_resposta__isnull=True, revisor=me.get_profile()).exists()

    def tem_solicitacao_assinatura_pendente(self, user=None):
        user = user or tl.get_user()
        solicitacoes_pendentes = self.solicitacaoassinatura_set.filter(documento=self, status=SolicitacaoStatus.STATUS_ESPERANDO, solicitado=user.get_profile())
        if not solicitacoes_pendentes.exists():
            return False

        for solicitacao in solicitacoes_pendentes:
            if solicitacao.estah_aguardando_outra_assinatura():
                return False
        return True

    def assinado_por(self,):
        return self.assinaturadocumentotexto_set.all().values_list('assinatura__pessoa__nome', flat=True)

    def get_assinado_por(self):
        assinaturas = self.assinaturadocumentotexto_set.all()
        assinantes = [format_profile(obj.assinatura.pessoa, obj.assinatura.pessoa.nome) for obj in assinaturas]
        return ', '.join(assinantes)

    def possui_assinatura(self):
        return AssinaturaDocumentoTexto.objects.filter(documento=self).exists()

    def assinaturas(self):
        return AssinaturaDocumentoTexto.objects.filter(documento=self).all()

    def imprimir_assinaturas(self):
        assinaturas = list()
        for assinatura in AssinaturaDocumentoTexto.objects.filter(documento=self):
            if assinatura.validar_documento():
                assinaturas.append(f"{assinatura.assinatura.pessoa}")
        return assinaturas

    def possuia_assinatura_de(self, user):
        pessoa = user.get_profile()
        return AssinaturaDocumentoTexto.objects.filter(documento=self, pessoa=pessoa, cpf=pessoa.get_cpf_ou_cnpj()).exists()

    def get_nivel_acesso(self):
        return format_html(status(self.get_nivel_acesso_display()))

    # TODO: Após fazer refactory nos métodos ler, tem_permissao_ler e views.verificar_permissao_leitura_documento,
    # adicionar a este método as chamadas a essas regras de validação.
    def get_pdf(self, orientacao='portrait', user=None, consulta_publica_hash=None, leitura_para_barramento=False, eh_consulta_publica=False):
        if not eh_consulta_publica:
            user = user or tl.get_user()
        pdf = gerar_pdf_documento_texto(
            documento=self,
            orientacao=orientacao,
            user=user,
            consulta_publica_hash=consulta_publica_hash,
            leitura_para_barramento=leitura_para_barramento,
            eh_consulta_publica=eh_consulta_publica
        )

        if self.possui_anexos():
            anexos = self.get_todos_anexos()
            lista_pdfs = list()
            lista_pdfs.append(pdf)
            for anexo in anexos:
                pode_ler = anexo.documento_anexado.pode_ler(user=user, consulta_publica_hash=consulta_publica_hash, leitura_para_barramento=leitura_para_barramento, eh_consulta_publica=eh_consulta_publica)
                if pode_ler:
                    lista_pdfs.append(anexo.documento_anexado.get_pdf(user=user))
            return merge_pdfs_pdf(lista_pdfs, self.id)

        return pdf

    @classmethod
    def adicionar_documento_texto(self, usuario, setor_dono, assunto, modelo, nivel_acesso, hipotese_legal=None, corpo=None, documento=None, variaveis=None):
        with transaction.atomic():

            if documento:
                documento_novo = DocumentoTexto.objects.get(pk=documento)
                documento_novo.assunto = assunto
                # IFMA inicio IRLAN 11/12/2018 (útil para quando muda o modelo no atos administrativo)
                documento_novo.modelo = modelo
                # IFMA fim IRLAN
            else:
                documento_novo = DocumentoTexto.objects.create(
                    setor_dono=setor_dono,
                    usuario_criacao=usuario,
                    assunto=assunto,
                    data_ultima_modificacao=get_datetime_now(),
                    usuario_ultima_modificacao=usuario,
                    modelo=modelo,
                    nivel_acesso=nivel_acesso,
                )
            # Quando o documento é criado o conteúdo do cabeçalho, rodapé e do corpo são definidos com base no modelo
            # do documento. Uma vez definido isso, se faz necessário apenas copiar o corpo do documento que está sendo

            if corpo:
                documento_novo.corpo = corpo
            if modelo.classificacao.all().exists:
                documento_novo.classificacao = modelo.classificacao.all()

            if hipotese_legal:
                documento_novo.hipotese_legal = hipotese_legal

            documento_novo.save()

            if variaveis:
                variaveis_correntes = get_variaveis(
                    documento_identificador=None,
                    estagio_processamento_variavel=EstagioProcessamentoVariavel.CRIACAO_DOCUMENTO, usuario=usuario,
                    setor_dono=setor_dono)
                variaveis_correntes.update(variaveis)
                documento_novo.corpo = processar_template_ckeditor(texto=modelo.corpo_padrao,
                                                                   variaveis=variaveis_correntes)
                documento_novo.save()

            return documento_novo

    def get_anexos_documentos_texto(self):
        return DocumentoTextoAnexoDocumentoTexto.objects.filter(documento=self)

    def get_anexos_documentos_digitalizado(self):
        return DocumentoTextoAnexoDocumentoDigitalizado.objects.filter(documento=self)

    def get_apenas_anexos_digitalizados_simples(self):
        return DocumentoDigitalizadoAnexoSimples.objects.filter(pk=self.pk)

    def get_todos_anexos(self):
        dt = self.get_anexos_documentos_texto()
        dd = self.get_anexos_documentos_digitalizado()
        docs = list(dt) + list(dd)
        docs.sort(key=lambda a: a.data_hora_inclusao)
        return docs

    def possui_anexos(self):
        dt = self.get_anexos_documentos_texto().exists()
        dd = self.get_anexos_documentos_digitalizado().exists()
        return dt or dd

    def get_qtd_todos_anexos(self):
        return len(self.get_todos_anexos())

    def pode_alterar_nivel_acesso(self, user=None):
        user = user or get_user()

        if self.estah_finalizado:
            # Se for da gestão de nível de acesso pode alterar sempre
            if user.groups.filter(name='Gestão Nível de Acesso dos Processos Documentos Eletrônicos').exists():
                return True

            # Se for documento pessoal
            # Se for dono do documento
            if self.usuario_criacao == user:
                return True

            # Se for documento de setor
            if self.eh_documento_de_setor:
                # Chefe do setor ou poder de chefe no setor dono OU poder editar documentos daquele setor
                meus_setores = list()
                meus_setores_chefe_poder_chefe = setores_que_sou_chefe_ou_tenho_poder_de_chefe(user).values_list('id', flat=True)
                meu_setor = get_setor(user)
                for s in meus_setores_chefe_poder_chefe:
                    meus_setores.append(s)
                meus_setores.append(meu_setor)

                # Setores que podem vir em `meus_setores` do user
                # - Setor SUAP
                # - Setores que sou Chefe
                # - Setores que tem poder de Chefe
                if self.setor_dono in meus_setores:
                    return True

        return False

    @transaction.atomic()
    def alterar_nivel_acesso(self, novo_nivel_acesso, nova_hipotese_legal, user, ip, justificativa):
        #
        if not self.pode_alterar_nivel_acesso(user):
            raise Exception(f'Esse documento não pode ser alterado por {user.get_profile()}.')

        de = NivelAcesso.choices()[self.nivel_acesso - 1][1]
        para = NivelAcesso.choices()[novo_nivel_acesso - 1][1]

        if self.nivel_acesso == novo_nivel_acesso:
            raise Exception(f'Impossível alterar o nível de acesso de {de} para {para}.')

        obs = f'Alterou o nível de acesso de {de} para {para}'
        if justificativa:
            obs += f' mediante justificativa: {justificativa}'
        obs += '.'

        tipo = RegistroAcaoDocumentoTexto.TIPO_EDICAO_NIVEL_ACESSO

        self.hipotese_legal = nova_hipotese_legal
        self.nivel_acesso = novo_nivel_acesso
        self.clean()
        self.save()

        RegistroAcaoDocumentoTexto.objects.create(tipo=tipo, documento=self, ip=ip, observacao=obs)

        return None

    def listar_solicitacoes_nivel_acesso_aberto(self):
        from processo_eletronico.models import SolicitacaoAlteracaoNivelAcesso
        solicitacoes = SolicitacaoAlteracaoNivelAcesso.objects.filter(
            documento_texto=self,
            situacao=SolicitacaoAlteracaoNivelAcesso.SITUACAO_SOLICITADO
        )
        return solicitacoes

    def existe_solicitacoes_juntadas_aberta(self):
        return True

    def existe_solicitacoes_nivel_acesso_aberto(self):
        return self.listar_solicitacoes_nivel_acesso_aberto().exists()

    def pode_solicitar_alteracao_nivel_acesso(self, user=None):
        return not self.pode_alterar_nivel_acesso(user) and self.estah_finalizado

    @staticmethod
    def get_documentos_por_pessoa_fisica(pessoa_fisica):
        vinculo = pessoa_fisica.get_vinculo()
        if vinculo and vinculo.user:
            user = vinculo.user
            return DocumentoTexto.objects.filter(
                Q(usuario_criacao=user)
                | Q(usuario_ultima_modificacao=user)
                | Q(usuario_remocao=user)
                | Q(interessados=pessoa_fisica)
            )
        return DocumentoTexto.objects.filter(interessados=pessoa_fisica)


class TipoConferencia(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        ordering = ('descricao',)
        verbose_name = 'Tipo de Conferência'
        verbose_name_plural = 'Tipos de Conferência'

    def __str__(self):
        return f"{self.descricao}"


@reversion.register()
class DocumentoDigitalizado(Documento):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    SEARCH_FIELDS = [
        'identificador_tipo_documento_sigla', 'identificador_numero',
        'identificador_ano', 'identificador_setor_sigla',
        'dono_documento__nome'
    ]

    identificador_tipo_documento_sigla = models.CharFieldPlus('Sigla do Tipo de Documento', max_length=50, blank=True, null=True)
    identificador_numero = models.PositiveIntegerField('Número', blank=True, null=True)
    identificador_ano = models.PositiveIntegerField('Ano', blank=True, null=True)
    identificador_setor_sigla = models.CharFieldPlus('Sigla do Setor', max_length=100, blank=True, null=True)

    tipo = models.ForeignKeyPlus('documento_eletronico.TipoDocumento')

    # Seu tamanho foi alterado
    # Considerar https://gitlab.ifrn.edu.br/cosinf/suap/-/issues/3705
    arquivo = models.FileFieldPlus('Arquivo', upload_to=file_upload_to, max_length=400)
    interno = models.BooleanField('Documento Interno', help_text='Documento produzido na instituição', null=True)
    orgao_externo = models.CharFieldPlus('Órgão Externo', help_text='Nome do órgão externo que produziu o documento')
    tipo_conferencia = models.ForeignKeyPlus(TipoConferencia, verbose_name='Tipo de Conferência')

    dono_documento = models.ForeignKeyPlus(
        'rh.PessoaFisica', verbose_name='Dono do Documento', null=True,
        help_text='Esse campo é obrigatório caso você esteja adicionando um ' 'documento sigiloso.',
        related_name='donos_documento'
    )

    # Indica que esse documento é anexo de um documento texto
    # - Sobre e regras
    #   - Esse documento só existe pra ser anexo de um documento_texto que possa receber anexos
    #   - Sera assinado quando o documento pai for assinado
    #   - Se for removido da lista de anexo deixara de existir
    #   - Sera impresso junto com o pai (merge com o pdf do pai)
    #   - Quando for assinado nao podera ser mais alterado
    #   - Depois de anexado pode ser alterado. Depois de assinado nao podera mais
    #   - As regras de visualizacao e edicao seguem as mesmas do pai
    # - Campos automáticos
    #   - nivel_acesso sera o mesmo do pai (sincronizado)
    #   - hipotese_legal sera o mesmo do pai (sincronizado)
    # - Não possui
    #   - Setor_dono
    anexo_simples = models.BooleanField(default=False, editable=False)

    objects = DocumentoDigitalizadoManager()

    class Meta:
        verbose_name = 'Documento Digitalizado'
        verbose_name_plural = 'Documentos Digitalizados'
        permissions = (
            ('pode_alterar_nivel_acesso_documento_digitalizado', "Pode alterar nível de acesso dos documentos eletrônicos - digitalizado"),
            ('pode_ver_todos_log_acoes_documento_digitalizado', "Pode acessar todos os logs de acessos - digitalizado"),
        )

    def __str__(self):
        return f"{self.assunto}"

    def get_pdf(self, orientacao='portrait', user=None, consulta_publica_hash=None, leitura_para_barramento=False, eh_consulta_publica=False):
        if not eh_consulta_publica:
            user = user or tl.get_user()

        pdf = gerar_pdf_documento_digitalizado(
            documento=self,
            orientacao=orientacao,
            user=user,
            consulta_publica_hash=consulta_publica_hash,
            leitura_para_barramento=leitura_para_barramento,
            eh_consulta_publica=eh_consulta_publica
        )

        return pdf

    @staticmethod
    @transaction.atomic()
    def criar(file_content, file_name, tipo_documento, assunto, user, papel, nivel_acesso):
        data_hora_atual = datetime.now()

        documento = DocumentoDigitalizado()
        documento.identificador_tipo_documento_sigla = tipo_documento.sigla
        # documento.identificador_numero = self.id
        documento.identificador_ano = datetime.now().year
        documento.identificador_setor_sigla = get_setor(user).sigla
        documento.tipo = tipo_documento
        documento.interno = True
        documento.tipo_conferencia = TipoConferencia.objects.get(descricao='Cópia Simples')
        documento.setor_dono = get_setor(user)
        documento.assunto = assunto
        documento.data_emissao = data_hora_atual
        documento.nivel_acesso = nivel_acesso

        # Informando a hipótese legal que será usada ao criado o documento digitalizado restrito, caso existam hipóteses
        # cadastradas para tal.
        # TODO: Todos os documentos deve ser restritos mesmo? Se for restrito qual hipotese legal padrão?
        if documento.nivel_acesso == Documento.NIVEL_ACESSO_RESTRITO:
            if HipoteseLegal.objects.filter(nivel_acesso=NivelAcesso.RESTRITO.name).exists():
                hipotese_legal_documento_abertura_requerimento_id = Configuracao.get_valor_por_chave('processo_eletronico',
                                                                                                     'hipotese_legal_documento_abertura_requerimento')
                if not hipotese_legal_documento_abertura_requerimento_id:
                    raise ValidationError(
                        'Impossível gerar o documento digitalizado do requerimento pois não há hipótese legal configurada para isso no módulo de processo eletrônico. Entre em contato com os administradores do sistema.'
                    )
                documento.hipotese_legal = HipoteseLegal.objects.get(pk=hipotese_legal_documento_abertura_requerimento_id)

        documento.usuario_criacao = user
        documento.data_criacao = data_hora_atual
        documento.usuario_ultima_modificacao = user
        documento.data_ultima_modificacao = data_hora_atual
        documento.arquivo.save(file_name, ContentFile(file_content))
        documento.assinar_via_senha(user, papel)
        # Chamando a validação do domínio.
        documento.clean()
        documento.save()
        return documento

    @property
    def conteudo(self):
        return self.arquivo

    @property
    def hash_conteudo(self):
        sha512 = hashlib.sha512()
        for chunk in self.arquivo.chunks():
            sha512.update(chunk)
        return sha512.hexdigest()

    @property
    def hash_conteudo_as_sha256(self):
        sha256 = hashlib.sha256()
        for chunk in self.arquivo.chunks():
            sha256.update(chunk)
        return sha256.hexdigest()

    def _assinar(self, assinatura):
        AssinaturaDocumentoDigitalizado.objects.get_or_create(documento=self, assinatura=assinatura)
        self.data_emissao = get_datetime_now()

    @property
    def eh_documento_texto(self):
        return False

    @property
    def eh_documento_digitalizado(self):
        return True

    # Um documento digitalizado é sempre assinado no seu upload.
    @property
    def estah_assinado(self):
        return True

    @property
    def tamanho_em_bytes(self):
        try:
            size = len(self.conteudo)
            return size
        except Exception:
            return 0

    @property
    def tamanho_em_kb(self):
        try:
            size = round((self.tamanho_em_bytes / 1024.0), 2)
            return size
        except Exception:
            return 0

    @property
    def tamanho_em_mb(self):
        try:
            size = round((self.tamanho_em_kb / 1024.0), 2)
            return size
        except Exception:
            return 0

    @transaction.atomic()
    def assinar_via_senha(self, user, papel):
        pessoa_fisica = user.get_profile()
        hmac = gerar_assinatura_documento_senha(self, pessoa_fisica)
        if not verificar_assinatura_senha(self, pessoa_fisica, hmac):
            raise ValidationError(f'O documento não pode ser assinado por {user}.')

        '''
        Issue #3308

        Da forma como foi implementado originalmente, o sistema só permite a assinatura de um mesmo documento uma única vez,
        seja ele externo (DocumentoDigitalizado) ou interno (DocumentoTexto). Acontece que, no caso dos documentos externos,
        um mesmo documento pode ser adicionado "n" vezes. Ex: Adicionar o mesmo documento em processos distintos.

        Antes do ajuste abaixo, o usuário poderia adicionar o mesmo documento, "n" vezes, desde que utilizasse o mesmo papel.
        Nesse caso,o registro de Assinatura criado na primeira vez que o documento foi adicionado era reproveitado, criando-se
        apenas novos registros em DocumentoDigitalizado e AssinaturaDocumentoDigitalizado. Caso contrário, estourava na
        tela o erro "duplicate key value violates unique constraint documento_eletronico_assinatura_hmac_key".

        No caso agora fizemos um ajuste para que o usuário possa adicionar o mesmo documento "n" vezes, independente
        do papel que escolha. Se ele já tiver adicionado o mesmo documento em um momento anterior, a mesma
        assinatura será utilizada. Obs: (1) Essa solução de contorno não é a ideal, mas é rápida e de baixo impacto,
        visto que essa assinatura é só uma garantia de conferênca, ou seja, o usuário apenas está confirmando
        que foi ele que adicionou o documento, e não assinando o documento em si, como ocorre com os documentos
        criado internamente. Outro fator é que a assinatura em si (hamac - resultado do método gerar_assinatura_documento_senha())
        não leva em conta o papel utilizado. (2) Uma outra possível solução seria remover a constraint unique do atributo
        hmac. Não gosto dessa solução porque, no caso de documentos internos, ser unique é um verdade e uma necessidade!
        (3) Uma solução mais robusta demandaria mais tempo e também uma remodelagem das classes de forma a reaproveitamos
        o mesmo documento externo. Creio que também não seria necessário solicitar um papel, neste caso, já que é apenas
        uma conferência.
        '''

        # Dados da Assinatura do documento
        assinatura, _ = Assinatura.objects.get_or_create(
            # Dados do assinante
            pessoa=pessoa_fisica,
            cpf=pessoa_fisica.cpf,
            # Dados da assinatura
            hmac=hmac,
            defaults={'nome_papel': papel.detalhamento, 'papel': papel},
        )
        self._assinar(assinatura)
        self.save()

    @transaction.atomic()
    def assinar_via_token(self, cert, hmac, pessoa_fisica, papel):
        if self.pode_assinar(pessoa_fisica.user):
            # Procuro o documento já possui uma assinatura com um dado
            assinatura, _ = AssinaturaDigital.objects.get_or_create(
                pessoa=pessoa_fisica,
                cpf=pessoa_fisica.cpf,
                papel=papel,
                # Dados da Assinatura
                defaults={
                    'hmac': hmac,
                    'chave_publica': cert.get_public_key(),
                    'numero_serie_certificado': cert.serial_number,
                    'certificado_criado_em': cert.data_range.begin(),
                    'certificado_expira_em': cert.data_range.end(),
                },
            )
            self._assinar(assinatura)
            self.save()
        else:
            raise ValidationError(f'O documento não pode ser assinado por {pessoa_fisica}.')

    def get_absolute_url(self,):
        return f"/documento_eletronico/visualizar_documento_digitalizado/{self.pk}/"

    def get_url_autenticacao(self, completa=False):
        url = settings.SITE_URL + '/verificar-documento-externo/'
        if completa:
            url += f'?codigo_verificador={self.id:d}&codigo_autenticacao={self.codigo_autenticacao:s}'
        return url

    @property
    def tem_solicitacao_compartilhamento_pessoa_documento_digitalizado_pendentes(self):
        return self.solicitacao_compartilhamento_pessoa_documento_digitalizado.filter(
            status_solicitacao=SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.STATUS_AGUARDANDO
        ).exists()

    @property
    def solicitacoes_compartilhamento_pessoa_documento_digitalizado_pendentes(self):
        return self.solicitacao_compartilhamento_pessoa_documento_digitalizado.filter(status_solicitacao=SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.STATUS_AGUARDANDO)

    def pode_assinar(self, user=None):
        user = user or tl.get_user()
        # já que a solicitação já adiciona o usuario como visualizador
        usuario_assinou = AssinaturaDocumentoDigitalizado.objects.filter(documento=self, pessoa=user.get_profile()).exists()
        return not usuario_assinou and self.tem_permissao_editar(user)

    def assinado_por(self):
        return Pessoa.objects.filter(pk__in=AssinaturaDocumentoDigitalizado.objects.filter(documento=self).values_list('assinatura__pessoa__pk', flat=True)).all()

    def possui_assinatura(self):
        return AssinaturaDocumentoDigitalizado.objects.filter(documento=self).exists()

    def possuia_assinatura_de(self, user):
        pessoa = user.get_profile()
        return AssinaturaDocumentoDigitalizado.objects.filter(documento=self, pessoa=pessoa, cpf=pessoa.get_cpf_ou_cnpj()).exists()

    def assinaturas(self):
        assinaturas = list()
        for assinatura in AssinaturaDocumentoDigitalizado.objects.filter(documento=self):
            if assinatura.validar_documento():
                assinaturas.append(assinatura)
        return assinaturas

    def eh_valido(self):
        for assinaturadd in AssinaturaDocumentoDigitalizado.objects.filter(documento=self):
            if assinaturadd.validar_documento():
                return True
        return False

    def imprimir_assinaturas(self):
        return [assinatura.assinatura.pessoa for assinatura in self.assinaturas()]

    # TODO: Rever este método, pois creio que ele está bastante antigo e fora do contexto atual. Tem validação que creio
    # que não faça mais sentido, pensando em DocumentoDigitalizado (adicionado ao sistema via UPLOAD).
    def tem_permissao_ler(self, user, consulta_publica_hash=None, leitura_para_barramento=False, eh_consulta_publica=False):
        # Se é uma consulta pública para ver proceso na integra
        if eh_consulta_publica:
            return self.eh_publico and self.estah_assinado
        # Se é uma consulta pública (para verificar autenticidade)
        elif consulta_publica_hash:
            if consulta_publica_hash == self.hash_conteudo:
                return True
        # Se é uma consulta para o barramento
        elif leitura_para_barramento:
            if self.eh_publico:
                return True
        # Se o documento é público pode ler
        elif self.eh_publico:
            return True
        else:
            if acesso_ao_documento_em_funcao_cargo(user=user, documento=self):
                return True
            if self.eh_documento_de_setor:
                # ----------------------------------
                # DOCUMENTO VINCULADO A SETOR
                # ----------------------------------

                # <<<
                # Permissão "Natural", definida pelo próprio módulo de Documento Eletrônico
                # >>>
                if self.usuario_criacao == user:
                    return True

                pessoa = user.get_profile()
                #
                meus_setores_chefe_poder_chefe = setores_que_sou_chefe_ou_tenho_poder_de_chefe(user).values_list('id', flat=True)
                setores_compartilhados_pessoa = CompartilhamentoSetorPessoa.objects.filter(pessoa_permitida_id=pessoa.id).values_list('setor_dono_id', flat=True)
                todos_setores = list(meus_setores_chefe_poder_chefe) + list(setores_compartilhados_pessoa)
                # Lista todos os documentos, exceto os SIGILOSOS
                if not user.eh_aluno and not self.eh_privado and self.setor_dono.id in todos_setores:
                    return True

                # Verifica se é privado e se o documento ta compartilhado com ele
                if self.eh_privado and (
                    self.usuario_criacao == user or self.compartilhamento_pessoa_documento_digitalizado.filter(pessoa_permitida_id=pessoa.id).exists()
                ):
                    return True

                # <<<
                # Permissão "Alternativa", feita via módulo de Processo Eletrônico.
                # Caso esteja de pose do processo eletronico que contenha o arquivo e possa lero processo
                # >>>
                if self.eh_restrito:
                    usuario_pode_ver_doc_restrito_via_processo = usuario_deve_ter_acesso_a_documento_restrito_atraves_de_processo(user=user, documento=self)
                    usuario_pode_ver_doc_restrito_via_juntada_pendente = usuario_deve_ter_acesso_a_documento_restrito_atraves_de_solicitacao_juntada_pendente(user=user, documento=self)
                    if usuario_pode_ver_doc_restrito_via_processo or usuario_pode_ver_doc_restrito_via_juntada_pendente:
                        return True
            else:
                # ----------------------------------
                # DOCUMENTO PESSOAL
                # ----------------------------------

                if self.usuario_criacao == user:
                    return True

                documento_sigiloso = self.nivel_acesso == self.NIVEL_ACESSO_SIGILOSO

                if documento_sigiloso and (
                    self.usuario_criacao == user or user.get_profile().id in self.compartilhamento_pessoa_documento_digitalizado.values_list('pessoa_permitida_id', flat=True)
                ):
                    return True

                if self.eh_restrito:
                    usuario_pode_ver_doc_restrito_via_processo = usuario_deve_ter_acesso_a_documento_restrito_atraves_de_processo(user=user, documento=self)
                    usuario_pode_ver_doc_restrito_via_juntada_pendente = usuario_deve_ter_acesso_a_documento_restrito_atraves_de_solicitacao_juntada_pendente(user=user, documento=self)
                    if usuario_pode_ver_doc_restrito_via_processo or usuario_pode_ver_doc_restrito_via_juntada_pendente:
                        return True

        return False

    def tem_permissao_editar(self, user=None):
        if not user:
            user = tl.get_user()
        if not self.dono_documento and self.usuario_criacao == user:
            return True
        elif self.dono_documento == user.get_profile():
            return True
        return False

    def pode_editar(self, user=None):
        if self.eh_documento_anexo_simples:
            return False

        if self.eh_documento_pessoal:
            user = user or tl.get_user()
            # Pode editar se tiver permissao, se não estiver juntado a processo e se não for anexo de outro documento
            processos_incluido = self.get_processos(exibir_somente_processos_nos_quais_documento_nao_foi_removido=True)
            documentos_que_estah_anexado = DocumentoTextoAnexoDocumentoDigitalizado.objects.filter(documento_anexado=self)
            return self.tem_permissao_editar(user) and not processos_incluido and not documentos_que_estah_anexado

        return super().pode_editar(user)

    #
    def pode_vincular_interessado(self):
        return False

    def admite_interessados(self):
        return False

    def pode_alterar_nivel_acesso(self, user=None, processo=None,):
        user = user or tl.get_user()

        # Se for da gestão de nível de acesso pode alterar sempre
        if user.groups.filter(name='Gestão Nível de Acesso dos Processos Documentos Eletrônicos').exists():
            return True

        # Se tem permissão de editar o documento digitalizado
        if self.tem_permissao_editar(user):
            return True

        if self.eh_documento_de_setor:
            # Se pode alterar o nivel de acesso do processo ao qual este documento está vinculado
            if processo:
                if processo.pode_alterar_nivel_acesso(user=user):
                    return True
            else:
                from processo_eletronico.models import DocumentoDigitalizadoProcesso
                processos_doc = DocumentoDigitalizadoProcesso.objects.filter(documento=self).first()
                if processos_doc:
                    return processos_doc.processo.pode_alterar_nivel_acesso(user=user)

        return False

    @transaction.atomic()
    def alterar_nivel_acesso(self, novo_nivel_acesso, nova_hipotese_legal, user, ip, justificativa, pessoas_compartilhadas=None):

        if not self.pode_alterar_nivel_acesso(user):
            raise Exception(f'Esse documento não pode ser alterado por {user.get_profile()}.')

        de = NivelAcesso.choices()[self.nivel_acesso - 1][1]
        para = NivelAcesso.choices()[novo_nivel_acesso - 1][1]

        if self.nivel_acesso == novo_nivel_acesso:
            raise Exception(f'Impossível alterar o nível de acesso de {de} para {para}.')

        obs = f'Alterou o nível de acesso de {de} para {para}'
        if justificativa:
            obs += f' mediante justificativa: {justificativa}'
        obs += '.'

        tipo = RegistroAcaoDocumentoDigitalizado.TIPO_EDICAO_NIVEL_ACESSO

        self.hipotese_legal = nova_hipotese_legal
        self.nivel_acesso = novo_nivel_acesso
        self.clean()
        self.save()

        if pessoas_compartilhadas:
            CompartilhamentoDocumentoDigitalizadoPessoa.objects.filter(documento=self).delete()
            # Compartilhando com o dono
            compartilhamento = CompartilhamentoDocumentoDigitalizadoPessoa()
            compartilhamento.documento = self
            compartilhamento.pessoa_permitida = user.get_profile()
            compartilhamento.data_criacao = datetime.now()
            compartilhamento.usuario_criacao = user
            compartilhamento.save()

            for pessoa in pessoas_compartilhadas:
                compartilhamento = CompartilhamentoDocumentoDigitalizadoPessoa()
                compartilhamento.documento = self
                compartilhamento.pessoa_permitida = pessoa
                compartilhamento.data_criacao = datetime.now()
                compartilhamento.usuario_criacao = user
                compartilhamento.save()

        RegistroAcaoDocumentoDigitalizado.objects.create(tipo=tipo, documento=self, ip=ip, observacao=obs)
        return None

    def pode_solicitar_alteracao_nivel_acesso(self, user=None):
        return not self.pode_alterar_nivel_acesso(user)

    def listar_solicitacoes_nivel_acesso_aberto(self):
        from processo_eletronico.models import SolicitacaoAlteracaoNivelAcesso
        solicitacoes = SolicitacaoAlteracaoNivelAcesso.objects.filter(
            documento_digitalizado=self,
            situacao=SolicitacaoAlteracaoNivelAcesso.SITUACAO_SOLICITADO
        )
        return solicitacoes

    def existe_solicitacoes_nivel_acesso_aberto(self):
        return self.listar_solicitacoes_nivel_acesso_aberto().exists()


@reversion.register()
class TipoDocumento(models.ModelPlus):
    """
    Classe que representa todos os tipos de documento. Ex: Memorando, Ofício, Portaria, RG, CPF, Certidão de Nascimento.
    """
    SEARCH_FIELDS = ['nome']
    #
    nome = models.CharFieldPlus('Descrição', unique=True)
    sigla = models.CharFieldPlus('Sigla', unique=True, max_length=50)
    vincular_pessoa = models.BooleanField('Permite vincular interessado', default=False)
    ativo = models.BooleanField('ativo', default=True, help_text='Somente os registros ativos ficam disponíveis no cadastro de documentos.')

    permite_documentos_pessoais = models.BooleanField('Permite criar documentos pessoais', default=False)

    objects = models.Manager()
    ativos = AtivosManager()
    ativos_pessoais = AtivosDocumentosPessoaisManager()

    class Meta:
        ordering = ('nome',)
        verbose_name = 'Tipo de Documento Externo'
        verbose_name_plural = 'Tipos de Documentos Externos'

    def __str__(self):
        return self.nome


@reversion.register(follow=["tipodocumento_ptr"])
class TipoDocumentoTexto(TipoDocumento):

    SEQUENCE_GENERATOR_MAP = [
        ('identificador_sequencial', "Identificador Sequencial", identificador_sequencial),
        ('identificador_sequencial_anual', "Identificador Sequencial Anual", identificador_sequencial_anual)
    ]
    #
    SEQUENCE_GENERATOR_FN = {k: func for k, _, func in SEQUENCE_GENERATOR_MAP}
    SEQUENCE_GENERATOR_CHOICES = [(k, label) for k, label, _ in SEQUENCE_GENERATOR_MAP]
    #
    cabecalho_padrao = models.TextField('Cabeçalho Padrão', blank=True)
    cabecalho_hash = models.TextField('Hash do Cabeçalho', editable=False)
    rodape_padrao = models.TextField('Rodapé Padrão', blank=True)
    rodape_hash = models.TextField('Hash do Rodapé', editable=False)
    permite_documentos_anexos = models.BooleanField('Permite receber documentos em anexo', default=False)
    #
    tipo_sequencia = models.CharField(max_length=50, choices=SEQUENCE_GENERATOR_CHOICES, default='identificador_sequencial_anual', verbose_name="Tipo de numeração")

    class Meta:
        ordering = ('nome',)
        verbose_name = 'Tipo de Documento Interno'
        verbose_name_plural = 'Tipos de Documentos Internos'

    @property
    def sequenciador(self):
        return self.SEQUENCE_GENERATOR_FN[self.tipo_sequencia]

    @property
    def usa_sequencial_anual(self):
        return self.tipo_sequencia == 'identificador_sequencial_anual'

    @property
    def usa_sequencial_universal(self):
        return self.tipo_sequencia == 'identificador_sequencial'

    def get_modelos_ativos(self):
        return self.modelos.filter(ativo=True)

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Gerando o Hash
        self.processar_hash_conteudo()
        super().save(*args, **kwargs)

        # Atenção: Esta rotina só pode ser invocada depois que os hashs do cabecalho e rodapés estiverem definidos.
        self.gerar_historico_conteudo()
        # self.atualizar_documentos()

    def atualizar_documentos(self):
        # Somente os documentos nas situações listados abaixo podem ter seus cabeçalhos atualizados.
        documentos = DocumentoTexto.objects.filter(
            modelo__tipo_documento_texto=self,
            status__in=[DocumentoStatus.STATUS_RASCUNHO, DocumentoStatus.STATUS_CONCLUIDO, DocumentoStatus.STATUS_EM_REVISAO, DocumentoStatus.STATUS_REVISADO],
        )
        for documento in documentos:
            documento.montar_cabecalho_rodape_padrao()
            documento.save(update_fields=['cabecalho', 'rodape', 'cabecalho_base_original', 'rodape_base_original'])

    def processar_hash_conteudo(self):
        self.cabecalho_hash = gerar_hash(self.cabecalho_padrao)
        self.rodape_hash = gerar_hash(self.rodape_padrao)

    def gerar_historico_conteudo(self):
        '''
        A rotina abaixo cria um registro de histórico para o cabeçalho e rodapé do tipo de documento em questão, caso
        ainda não exista o registro no histórico.
        '''
        TipoDocumentoTextoHistoricoConteudo.objects.get_or_create(
            tipo_documento_texto=self, area_conteudo=TipoDocumentoTextoHistoricoConteudo.CABECALHO, hash=self.cabecalho_hash, defaults={'conteudo': self.cabecalho_padrao}
        )

        TipoDocumentoTextoHistoricoConteudo.objects.get_or_create(
            tipo_documento_texto=self, area_conteudo=TipoDocumentoTextoHistoricoConteudo.RODAPE, hash=self.rodape_hash, defaults={'conteudo': self.rodape_padrao}
        )

    def get_sugestao_identificador_definitivo(self, *args, **kwargs):
        return self.sequenciador(*args, **kwargs)


class TipoDocumentoTextoHistoricoConteudo(models.ModelPlus):
    CABECALHO = 'C'
    RODAPE = 'R'
    AREA_CONTEUDO_CHOICES = ((CABECALHO, 'Cabeçalho'), (RODAPE, 'Rodapé'))

    tipo_documento_texto = models.ForeignKeyPlus('documento_eletronico.TipoDocumentoTexto', verbose_name='Tipo de Documento', related_name='historicos_conteudo')
    area_conteudo = models.CharField(max_length=1, choices=AREA_CONTEUDO_CHOICES, verbose_name='Área de Conteúdo')
    conteudo = models.TextField('Conteúdo')
    hash = models.TextField('Hash')
    data_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True)

    class Meta:
        ordering = ('tipo_documento_texto__nome', 'data_criacao')
        verbose_name = 'Tipo de Documento Interno (Histórico Conteúdo)'
        verbose_name_plural = 'Tipos de Documentos Internos ((Histórico Conteúdo)'

    def __str__(self):
        return f'{self.id} - {self.tipo_documento_texto} - {self.get_area_conteudo_display()}'

    def save(self, *args, **kwargs):
        if self.id:
            raise ValidationError('Edição não permitida.')
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        raise ValidationError('Exclusão não permitida.')

# TODO: A entidade RestricaoAssinatura estava com uma entrada no menu porem seu admin não existe mais,
# o que estava acarretando um erro. Por hora, comentei a entrada no menu, mas depois vou averiguar se
# a entidade deve permanecer ou não, e se não, remover ela dos fontes.


class RestricaoAssinatura(models.ModelPlus):
    tipo_documento_texto = models.ForeignKeyPlus('documento_eletronico.TipoDocumentoTexto', verbose_name='Tipo de Documento', related_name='restricoes_assinatura')

    # GenericForeignKey - No caso ela vai armazenar o papel que pode realizar determinada assinatura. Lêa-se como papel
    # o cargo ou função exercida pela pessoa.
    papel_limit_choices = models.Q(app_label='rh', model='CargoEmprego') | models.Q(app_label='rh', model='Funcao')
    papel_content_type = models.ForeignKeyPlus(ContentType, verbose_name='Papel', limit_choices_to=papel_limit_choices, null=False, blank=False, on_delete=models.CASCADE)
    papel_content_id = models.PositiveIntegerField(verbose_name='Papel Object', null=False)
    papel_content_object = GenericForeignKey('papel_content_type', 'papel_content_id')

    class Meta:
        ordering = ('tipo_documento_texto__nome',)
        unique_together = ('tipo_documento_texto', 'papel_content_type', 'papel_content_id')
        verbose_name = 'Restrição de Assinatura'
        verbose_name_plural = 'Restrições de Assinatura'

    @classmethod
    def documentoTextoPodeSerAssinado(cls, papel, documento_texto):
        restricoes_assinatura = cls.objects.filter(tipo_documento_texto=documento_texto.modelo.tipo_documento_texto)
        if not restricoes_assinatura.exists():
            return True
        else:
            restricoes_assinatura = cls.objects.filter(papel_content_type=papel.papel_content_type, papel_content_id=papel.papel_content_id)
            if restricoes_assinatura.exists():
                return True

        return False


@reversion.register()
class TipoVinculoDocumento(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', unique=True, max_length=50)
    descricao_voz_ativa = models.CharFieldPlus('Descrição na Voz Ativa', unique=True, max_length=100)
    descricao_voz_passiva = models.CharFieldPlus('Descrição na Voz Passiva', unique=True, max_length=100)

    class Meta:
        ordering = ('descricao',)
        verbose_name = 'Tipo de Vínculo de Documento'
        verbose_name_plural = 'Tipos de Vínculos de Documentos'

    def __str__(self):
        return self.descricao_voz_ativa

    def save(self, *args, **kwargs):
        self.descricao_voz_ativa = self.descricao_voz_ativa.lower()
        self.descricao_voz_passiva = self.descricao_voz_passiva.lower()
        super().save(*args, **kwargs)


@reversion.register()
class VinculoDocumentoTexto(models.ModelPlus):
    tipo_vinculo_documento = models.ForeignKeyPlus('documento_eletronico.TipoVinculoDocumento', verbose_name='Tipo de Vínculo', related_name='vinculos_documento_texto')
    documento_texto_base = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento Base', related_name='vinculos_como_documento_texto_base')
    documento_texto_alvo = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento Alvo', related_name='vinculos_como_documento_texto_alvo')
    data_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.CurrentUserField(verbose_name='Usuário de Criação', editable=False)

    class Meta:
        ordering = ('tipo_vinculo_documento',)
        verbose_name = 'Tipo de Vínculo de Documento'
        verbose_name_plural = 'Tipos de Vínculos de Documentos'

    def __str__(self):
        return self.get_descricao_voz_ativa()

    def get_descricao_voz_ativa(self, incluir_documento_texto_base=True, incluir_documento_texto_alvo=True):
        return self.__get_descricao(
            oracao=self.tipo_vinculo_documento.descricao_voz_ativa,
            documento_texto_a=self.documento_texto_base if incluir_documento_texto_base else None,
            documento_texto_b=self.documento_texto_alvo if incluir_documento_texto_alvo else None,
        )

    def get_descricao_voz_passiva(self, incluir_documento_texto_base=True, incluir_documento_texto_alvo=True):
        return self.__get_descricao(
            oracao=self.tipo_vinculo_documento.descricao_voz_passiva,
            documento_texto_a=self.documento_texto_alvo if incluir_documento_texto_alvo else None,
            documento_texto_b=self.documento_texto_base if incluir_documento_texto_base else None,
        )

    def __get_descricao(self, oracao, documento_texto_a=None, documento_texto_b=None):
        result = '{a} {oracao} {b}'
        result = result.replace('{a}', documento_texto_a.identificador if documento_texto_a else '')
        result = result.replace('{oracao}', oracao)
        result = result.replace('{b}', documento_texto_b.identificador if documento_texto_b else '')
        result = result.strip()
        if not documento_texto_a:
            result = result[0].upper() + result[1:]
        return result


class HipoteseLegal(models.ModelPlus):
    nivel_acesso = models.CharFieldPlus(verbose_name='Nível de Acesso', max_length=NivelAcesso.max_length(), choices=NivelAcesso.choices_for_hipotese_legal())
    descricao = models.CharFieldPlus('Descrição', unique=True)
    base_legal = models.CharFieldPlus('Base Legal')

    class Meta:
        ordering = ('descricao',)
        verbose_name = 'Hipótese Legal'
        verbose_name_plural = 'Hipóteses Legais'

    def __str__(self):
        return f'{self.descricao} ({self.base_legal})'


@reversion.register()
class ModeloDocumento(models.ModelPlus):
    nome = models.CharFieldPlus('Descrição', unique=True)
    corpo_padrao = models.TextField('Corpo Padrão', blank=True)
    tipo_documento_texto = models.ForeignKeyPlus('documento_eletronico.TipoDocumentoTexto', verbose_name='Tipo de Documento', related_name='modelos')

    # Níveis de acesso (do mais restritivo para o menos restritivo)
    # Sigiloso - Restrito - Público
    permite_nivel_acesso_sigiloso = models.BooleanField('Sigiloso?', default=True)
    permite_nivel_acesso_restrito = models.BooleanField('Restrito?', default=True)
    permite_nivel_acesso_publico = models.BooleanField('Público?', default=True)

    nivel_acesso_padrao = models.PositiveIntegerField('Nível de Acesso Padrão', choices=Documento.NIVEL_ACESSO_CHOICES, default=Documento.NIVEL_ACESSO_SIGILOSO)
    classificacao = models.ManyToManyFieldPlus('documento_eletronico.Classificacao', verbose_name='Classificação', blank=True)

    ativo = models.BooleanField('ativo', default=True, help_text='Somente os registros ativos ficam disponíveis no cadastro de documentos.')

    objects = models.Manager()
    ativos = AtivosManager()

    class Meta:
        ordering = ('tipo_documento_texto__nome', 'nome')
        verbose_name = 'Modelo de Documento'
        verbose_name_plural = 'Modelos de Documentos'

    def __str__(self):
        return f"{self.nome}"

    def clean(self):
        # Em caso de edição, a alteração do atributo "tipo_documento_texto" só será permitida caso não exista nenhum
        # documento criado.
        if self.pk:
            modelo_documento_antes_alteracao = ModeloDocumento.objects.get(pk=self.pk)
            if self.tipo_documento_texto != modelo_documento_antes_alteracao.tipo_documento_texto:
                docs_criados_deste_modelo = DocumentoTexto.objects.filter(modelo=self)
                if docs_criados_deste_modelo.exists():
                    raise ValidationError('Não é possível alterar o tipo de documento deste modelo ' 'por já haverem documentos criados.')

        niveis_acesso_permitidos_keys, niveis_acesso_permitidos_values = self.niveis_acesso_permitidos
        if not niveis_acesso_permitidos_keys:
            raise ValidationError('Defina pelo menos um nível de acesso para o modelo.')

        if self.nivel_acesso_padrao and self.nivel_acesso_padrao not in niveis_acesso_permitidos_keys:
            niveis_acesso_permitidos_values_descricao_amigavel = format_iterable(value=niveis_acesso_permitidos_values, final_separator=' ou ')
            raise ValidationError(
                f'O nível de acesso padrão tem de ser um dos níveis permitidos para o modelo em questão: {niveis_acesso_permitidos_values_descricao_amigavel}.'
            )

    @property
    def niveis_acesso_permitidos(self):
        niveis_acesso_permitidos_keys = list()

        if self.permite_nivel_acesso_sigiloso:
            niveis_acesso_permitidos_keys.append(Documento.NIVEL_ACESSO_SIGILOSO)
        if self.permite_nivel_acesso_restrito:
            niveis_acesso_permitidos_keys.append(Documento.NIVEL_ACESSO_RESTRITO)
        if self.permite_nivel_acesso_publico:
            niveis_acesso_permitidos_keys.append(Documento.NIVEL_ACESSO_PUBLICO)

        niveis_acesso_permitidos_values = get_values_from_choices(niveis_acesso_permitidos_keys, Documento.NIVEL_ACESSO_CHOICES)
        return niveis_acesso_permitidos_keys, niveis_acesso_permitidos_values


class MetaClassificacao(MPTTModelBase, models.SUAPMetaModel):
    pass


class Classificacao(MPTTModel, models.ModelPlus, metaclass=MetaClassificacao):
    SEARCH_FIELDS = ['codigo', 'descricao']

    TEMPO_CORRENTE_TRANSFERIR = 1
    TEMPO_CORRENTE_ELIMINAR = 2
    TEMPO_CORRENTE_CHOICES = ((TEMPO_CORRENTE_TRANSFERIR, 'Transferir para Intermediário'), (TEMPO_CORRENTE_ELIMINAR, 'Eliminar'))

    TEMPO_INTERMEDIARIO_GUARDAR = 1
    TEMPO_INTERMEDIARIO_ELIMINAR = 2
    TEMPO_INTERMEDIARIO_CHOICES = ((TEMPO_INTERMEDIARIO_GUARDAR, 'Guardar Permanentemente'), (TEMPO_INTERMEDIARIO_ELIMINAR, 'Eliminar'))
    pai = TreeForeignKey('self', null=True, blank=True, related_name='filhos', db_index=True, on_delete=models.CASCADE)

    codigo = models.CharFieldPlus('Código', unique=True, max_length=10)
    descricao = models.TextField('Descrição')

    fase_corrente = models.TextField('Fase Corrente', blank=True)
    fase_intermediaria = models.TextField('Fase Intermediária', blank=True)
    destinacao_final = models.TextField('Destinação Final', blank=True)
    observacoes = models.TextField('Observações', blank=True)

    suficiente_para_classificar_processo = models.BooleanField('Suficiente para classificar um processo?', default=True)
    ativo = models.BooleanField('Ativo', default=True)

    migrado = models.BooleanField('Migrado', default=False)
    mec = models.BooleanField('Do MEC', default=False)

    objects = models.Manager()
    podem_classificar = PodemClassificarManager()

    class Meta:
        verbose_name = 'Classificação'
        verbose_name_plural = 'Classificações'
        ordering = ('codigo',)

    class MPTTMeta:
        parent_attr = 'pai'
        order_insertion_by = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"


class Solicitacao(models.ModelPlus):
    solicitante = models.CurrentUserField(related_name="%(app_label)s_%(class)s_solicitado_por")
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    status = FSMIntegerField(default=SolicitacaoStatus.STATUS_ESPERANDO, choices=SolicitacaoStatus.STATUS_CHOICES, protected=True)
    #
    solicitado = models.ForeignKeyPlus('rh.PessoaFisica', related_name="%(app_label)s_%(class)s_solicitado_a")
    #
    data_resposta = models.DateTimeField(blank=True, null=True)
    justificativa_rejeicao = models.TextField('Justificativa da Rejeição', blank=True, null=True)

    class Meta:
        ordering = ('data_solicitacao',)
        abstract = True

    def __str__(self):
        return f"{self.solicitado.nome_usual}"

    def delete(self, *args, **kwargs):
        ignore_clean = kwargs.pop('ignore_clean', None)
        if not ignore_clean:
            self.pode_ser_removida(raise_exception=True)
        return super().delete(*args, **kwargs)

    def pode_ser_removida(self, solicitante_user=None, raise_exception=False):
        user = solicitante_user or tl.get_user()
        try:
            if self.status != SolicitacaoStatus.STATUS_ESPERANDO:
                return False

            if self.solicitante != user:
                raise ValidationError('A solicitação só pode ser removida pelo solicitante.')

            return True
        except Exception as e:
            if raise_exception:
                raise e
            else:
                return False

    def pode_deferir(self, user=None):
        try:
            user = user or tl.get_user()
            user_profile = user.get_profile()
        except AttributeError:
            user_profile = self.solicitado.user.get_profile()
        return self.solicitado == user_profile and self.status == SolicitacaoStatus.STATUS_ESPERANDO

    def pode_indeferir(self, user=None):
        try:
            user = user or tl.get_user()
            user_profile = user.get_profile()
        except AttributeError:
            user_profile = self.solicitado.user.get_profile()
        return self.solicitado == user_profile and self.status == SolicitacaoStatus.STATUS_ESPERANDO

    @transition(
        field=status, source=SolicitacaoStatus.STATUS_ESPERANDO, target=SolicitacaoStatus.STATUS_DEFERIDA, conditions=[pode_deferir], on_error=SolicitacaoStatus.STATUS_ESPERANDO
    )
    def deferir_solicitacao(self):
        self.deferir_solicitacao_impl()

    @transition(field=status, source=SolicitacaoStatus.STATUS_ESPERANDO, target=SolicitacaoStatus.STATUS_INDEFERIDA, on_error=SolicitacaoStatus.STATUS_ESPERANDO)
    def indeferir_solicitacao(self):
        self.indeferir_solicitacao_impl()

    def enviar_mail(self, titulo=None, texto=None, destino=None):
        titulo = titulo or f'[SUAP] Solicitação de Documento: Processo Eletrônico {self.processo}'
        texto = texto or self.get_texto_solicitacao()
        destino = destino or [self.solicitado.get_vinculo()]
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, destino, categoria='Solicitação de Documento para Processo Eletrônico')

    def deferir_solicitacao_impl(self):
        raise NotImplementedError

    def indeferir_solicitacao_impl(self):
        raise NotImplementedError

    def get_texto_solicitacao(self):
        raise NotImplementedError


class SolicitacaoAssinatura(Solicitacao):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto')
    condicionantes = models.ManyToManyFieldPlus('self', symmetrical=False, verbose_name='Assinatura condicionada à')
    objects = SolicitacaoAssinaturaManager()

    class Meta:
        ordering = ('data_solicitacao',)

    @transaction.atomic()
    def delete_removendo_solicitacoes_dependentes(self):
        # Essa chamada não precisava ser feita aqui, mas resolvi fazê-la só pra impedir o processamento caso a
        # solicitação que está se tentando excluir não puder ser excluída, evitando assim processamento desnecessário.
        self.pode_ser_removida(raise_exception=True)

        # Obtendo todas as solicitações dependentes. No caso a remoção será feita de baixo pra cima por conta das FKs.
        solicitacoes_dependentes = self.get_solicitacoes_dependentes()[::-1]
        for sd in solicitacoes_dependentes:
            sd.delete()

        self.delete()

        solicitacoes_assinatura_pendentes = SolicitacaoAssinatura.objects.filter(documento=self.documento, status=SolicitacaoStatus.STATUS_ESPERANDO).exists()
        if not solicitacoes_assinatura_pendentes:
            if self.documento.tem_assinaturas:
                self.documento.marcar_como_assinado()
            else:
                self.documento.concluir()
            self.documento.save()

    def get_solicitacoes_dependentes(self, qs_condicionantes=None, add_solicitacoes_irmas=False):
        '''
        Este método retorna uma lista contendo todas as assinaturas dependentes da solicitação atual e suas 'irmãs'.
        Cenário exemplo:

        1   João
        1   Pedro
        1   Carlos
        2   Maria
        2   Daniela
        3   Caio

        Supondo que tente-se remover a solicitação de assinatura de Pedro, do grupo 1, o método irá retornar uma lista
        contendo:

        2   Maria
        2   Daniela
        3   Caio

        ou

        2   Daniela
        2   Maria
        3   Caio

        A ordem dos registros não tem importância, o que importa é a ordem de dependência dos grupos.

        :param qs_condicionantes queryset contendo as condicionantes que devem ser aplicadas na thread corrente.
        :param add_solicitacoes_irmas indica se as solicitações irmãs devem ser adicionadas na lista
        :return: lista com todas as solicitações dependentes, na ordem descendente
        '''
        if not qs_condicionantes:
            if self.condicionantes.all():
                qs_condicionantes = self.condicionantes.all()
            else:
                qs_condicionantes = SolicitacaoAssinatura.objects.filter(id=self.id)
                # Necessário para poder adicionar as solicitações irmãs quando está tentando se remover uma assinatura
                # balizadora.
                add_solicitacoes_irmas = True

        result = list()
        qs_solicitacoes_irmas = SolicitacaoAssinatura.objects.filter(condicionantes__in=qs_condicionantes).distinct()
        if qs_solicitacoes_irmas:
            # Adicionando todas as solicitações irmãs caso seja pertinente.
            if add_solicitacoes_irmas:
                for si in qs_solicitacoes_irmas:
                    result.append(si)

            # Adicionando todas as solicitações que tem como condicionantes as irmãs da thread corrente.
            for sd in self.get_solicitacoes_dependentes(qs_condicionantes=qs_solicitacoes_irmas, add_solicitacoes_irmas=True):
                result.append(sd)

        return result

    def eh_balizadora(self):
        return not self.condicionantes

    def estah_aguardando_outra_assinatura(self):
        '''
        :return: True se a solicitação de assinatura em questão depender de outra e esta outra não estiver DEFERIDA. Caso
        contrário, retornará False.
        '''
        return self.condicionantes.filter(~Q(status=SolicitacaoStatus.STATUS_DEFERIDA)).exists()

    def __str__(self):
        return f"{self.solicitado.nome_usual}"

    def condicionada_a(self,):
        if self.condicionantes.exists():
            solicitados = []
            for condicionante in self.condicionantes.all():
                solicitados.append(condicionante.solicitado)
            return solicitados
        else:
            return None

    def pode_deferir(self, user=None):
        user = user or tl.get_user()
        if not self.solicitado == user.get_profile():
            return False

        if not self.condicionantes.exists():
            return True
        else:
            # Se não existir nenhuma solicitação condicionante não deferida, então pode.
            return not self.condicionantes.filter(~Q(status=SolicitacaoStatus.STATUS_DEFERIDA)).exists()

    def notificar_condicionantes(self):
        if not self.condicionantes.filter(~Q(status=SolicitacaoStatus.STATUS_DEFERIDA)).exists():
            # Se eu não tenho permissão de acesso mas minhas condicionantes já foram deferidas:
            if not self.documento.pode_ler(self.solicitado.user):
                CompartilhamentoDocumentoPessoa.objects.get_or_create(
                    pessoa_permitida=self.solicitado.user.get_profile(), documento=self.documento, nivel_permissao=NivelPermissao.LER
                )

    def adicionar_condicionantes(self, condicionantes):
        for condicionante in condicionantes:
            if condicionante not in self.condicionantes.all():
                self.condicionantes.add(condicionante)

    def deferir_solicitacao_impl(self):
        self.notificar_condicionantes()

    def indeferir_solicitacao_impl(self):
        SolicitacaoAssinatura.objects.filter(condicionantes=self).delete()

    def clean(self):
        if AssinaturaDocumentoTexto.objects.filter(assinatura__pessoa=self.solicitado.user.get_profile(), documento=self.documento).exists():
            raise ValidationError(f"O usuário {self.solicitado} já assinou o documento.")


class SolicitacaoRevisao(models.ModelPlus):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto')
    solicitante = models.CurrentUserField(related_name="revisao_solicitado_por")
    revisor = models.ForeignKeyPlus('rh.Pessoa', verbose_name='Revisor')
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_resposta = models.DateTimeField(blank=True, null=True)
    status = FSMIntegerField(default=SolicitacaoStatus.STATUS_ESPERANDO, choices=SolicitacaoStatus.STATUS_CHOICES, protected=True)
    observacao = models.TextField('Observação', blank=True, null=True)
    notas_revisor = models.TextField('Notas do Revisor', blank=True, null=True)
    avaliador = models.ForeignKeyPlus('rh.Pessoa', verbose_name='Avaliador', related_name="revisao_avaliada_por", null=True)
    data_avaliacao = models.DateTimeField(blank=True, null=True)
    status_avaliacao = FSMIntegerField(default=AvaliacaoSolicitacaoStatus.STATUS_ESPERANDO, choices=AvaliacaoSolicitacaoStatus.STATUS_CHOICES, null=True)

    # Managers
    objects = SolicitacaoRevisorManager()

    class Meta:
        ordering = ('data_solicitacao',)

    @transition(field=status, source=SolicitacaoStatus.STATUS_ESPERANDO, target=SolicitacaoStatus.STATUS_DEFERIDA)
    def deferir_solicitacao(self):
        pass

    @transition(field=status, source=SolicitacaoStatus.STATUS_ESPERANDO, target=SolicitacaoStatus.STATUS_INDEFERIDA)
    def indeferir_solicitacao(self):
        pass

    @transition(field=status_avaliacao, source=AvaliacaoSolicitacaoStatus.STATUS_ESPERANDO, target=AvaliacaoSolicitacaoStatus.STATUS_DEFERIDA)
    def deferir_avaliacao(self):
        pass

    @transition(field=status_avaliacao, source=AvaliacaoSolicitacaoStatus.STATUS_ESPERANDO, target=AvaliacaoSolicitacaoStatus.STATUS_INDEFERIDA)
    def indeferir_avaliacao(self):
        pass

    @transaction.atomic()
    def adicionar_avaliacao_deferida(self, user):
        try:
            if not self.avaliador:
                self.avaliador = user.get_relacionamento()
                self.data_avaliacao = get_datetime_now()
                self.deferir_avaliacao()
        except SolicitacaoRevisao.DoesNotExist:
            pass

    @transaction.atomic()
    def adicionar_avaliacao_indeferida(self, user):
        try:
            if not self.avaliador:
                self.avaliador = user.get_relacionamento()
                self.data_avaliacao = get_datetime_now()
                self.indeferir_avaliacao()
                self.save()
        except SolicitacaoRevisao.DoesNotExist:
            pass

    def get_status_avaliacao(self):
        return self.get_status_avaliacao_display()


class Assinatura(models.ModelPlus):
    # Dados do assinante
    pessoa = models.ForeignKeyPlus('rh.Pessoa')
    cpf = models.CharFieldPlus('CPF', blank=False, null=False)
    nome_papel = models.CharFieldPlus('Nome do Papel', help_text='Nome do Papel da Pessoa')
    papel = models.ForeignKeyPlus('rh.Papel')
    data_assinatura = models.DateTimeField(auto_now_add=True)
    hmac = models.TextField('Hash Assinado', unique=True)

    class Meta:
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        ordering = ('-data_assinatura',)

    objects = InheritanceManager()

    def __str__(self):
        return f"Assinatura de {self.pessoa.nome_usual}"

    def get_nome_papel(self):
        if self.papel:
            return str(self.papel).upper()
        return str(self.pessoa.pessoafisica.funcionario.servidor.cargo_emprego).upper()

    # TODO: Refazer a assinatura deste método. Ao invés de documento, o atributo passado deveria ser o "hash_conteudo"
    # do documento. Isso melhoraria a legibilidade, já que este método é útil para verificar a integridade da assinatura
    # de doocumentos de texto, despachos (registrados nos trâmites), pareceres de minutas etc.
    def validar_documento(self, documento):
        '''
        O objetivo deste método é verificar se o documento está íntegro, ou seja, se seu conteúdo não foi violado, usando
        como base assinatura realizada. Se a assinatura estiver válida, ou seja, o "hmac" gravado em banco está igual com
        o "hmac" gerado em tempo de execução, então é sinal de que a assinatura está intacta e consequentemente o documento
        está íntegro.

        :param documento: Pode ser qualquer objeto desde que contenha um atributo chamado "hash_conteudo"
        :return: True se o documento estiver íntegro e False caso contrário.
        '''
        return verificar_assinatura_senha(documento, self.pessoa, self.hmac)

    def save(self, *args, **kwargs):
        if self.pk is None:
            super().save(*args, **kwargs)


class AssinaturaDigital(Assinatura):
    chave_publica = models.TextField('Public Key RSA')
    numero_serie_certificado = models.CharField(max_length=48, null=True, blank=True)
    certificado_criado_em = models.DateTimeField(blank=True, null=True)
    certificado_expira_em = models.DateTimeField(blank=True, null=True)

    objects = InheritanceManager()

    class Meta:
        verbose_name = 'Assinatura Digital'
        verbose_name_plural = 'Assinaturas Digitais'
        ordering = ('-data_assinatura',)

    def validar_documento(self, documento):
        # Um documento é dito valido se o hash dele, o hash assinado e
        # batem. E se o assinador é realmente quem diz ser.

        rsakey = RSA.importKey(self.chave_publica)
        signer = PKCS1_v1_5.new(rsakey)
        digest = SHA256.new()
        digest.update(documento.hash_conteudo)
        return signer.verify(digest, unhexlify(self.hmac))


class AssinaturaDocumentoTexto(models.ModelPlus):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto')
    assinatura = models.ForeignKeyPlus('documento_eletronico.Assinatura')

    objects = AssinaturaDocumentoTextoManager()

    # TODO: verificar se é melhor adicionar um pos_signal para notificar solicitacoes
    @transaction.atomic()
    def _notificar_assinatura(self,):
        solicitacao = SolicitacaoAssinatura.objects.filter(documento=self.documento, solicitado=self.assinatura.pessoa, data_resposta__isnull=True).first()
        if solicitacao:
            solicitacao.deferir_solicitacao()
            solicitacao.data_resposta = get_datetime_now()
            solicitacao.save()

            self.documento.marcar_como_assinado()
            self.documento.save()

            # Rotina que adiciona o documento a um processo caso haja uma SolicitacaoAssinaturaComAnexacaoProcesso registrada
            # atrelada a solicitação de assainatura que acabou de ser deferida.
            if solicitacao and app_processo_eletronico_estah_instalada():
                SolicitacaoAssinaturaComAnexacaoProcesso = apps.get_model('processo_eletronico', 'SolicitacaoAssinaturaComAnexacaoProcesso')

            try:
                # Se ainda há assinaturas pendentes, o status volta a ser AGUARDANDO_ASSINATURA
                solicitacoes_pendentes = self.documento.solicitacaoassinatura_set.filter(documento=self.documento, status=SolicitacaoStatus.STATUS_ESPERANDO)

                if solicitacoes_pendentes.exists():
                    self.documento.solicitar_assinatura()
                    self.documento.save()
                else:
                    solicitacao_assinatura_com_anexacao_processo = SolicitacaoAssinaturaComAnexacaoProcesso.objects.filter(
                        solicitacao_assinatura=solicitacao.documento.get_solicitacao_balizadora()
                    )

                    if solicitacao_assinatura_com_anexacao_processo:
                        if self.documento.estah_aguardando_assinatura:
                            self.documento.marcar_como_assinado()
                            self.documento.save()

                        self.documento.finalizar_documento()
                        self.documento.save()
                        # Registrar ação
                        RegistroAcaoDocumentoTexto.objects.create(
                            tipo=RegistroAcaoDocumento.TIPO_FINALIZACAO,
                            user=solicitacao.solicitante,
                            documento=self.documento,
                            ip=tl.get_request().META['REMOTE_ADDR'],
                            observacao=f'Documento finalizado automaticamente após assinatura de {solicitacao.solicitado}.',
                        )

                        solicitacao_assinatura_com_anexacao_processo = solicitacao_assinatura_com_anexacao_processo.first()
                        processo = solicitacao_assinatura_com_anexacao_processo.processo_para_anexar
                        processo.adicionar_documento_texto(
                            documento=self.documento,
                            registro_acao_observacao='Documento adicionado ao processo {} automaticamente ' 'após a assinatura de {}.'.format(processo, solicitacao.solicitado),
                        )

                        if solicitacao_assinatura_com_anexacao_processo.destinatario_setor_tramite:
                            solicitante = solicitacao_assinatura_com_anexacao_processo.solicitacao_assinatura.solicitante
                            remetente_setor = get_setor(solicitante)
                            destinatario_setor = solicitacao_assinatura_com_anexacao_processo.destinatario_setor_tramite
                            despacho_corpo = solicitacao_assinatura_com_anexacao_processo.despacho_corpo
                            papel_solicitante = solicitacao_assinatura_com_anexacao_processo.papel_solicitante
                            # Tramite
                            Tramite = apps.get_model('processo_eletronico', 'Tramite')
                            tramite = Tramite()
                            tramite.processo = processo
                            assinar_tramite = True
                            if not papel_solicitante and not despacho_corpo:
                                assinar_tramite = False
                            tramite.tramitar_processo(
                                remetente_setor=remetente_setor,
                                remetente_pessoa=solicitante.get_profile(),
                                destinatario_setor=destinatario_setor,
                                destinatario_pessoa=None,
                                despacho_corpo=despacho_corpo,
                                assinar_tramite=assinar_tramite,
                                papel=papel_solicitante,
                            )
                            tramite.save()
            except SolicitacaoAssinaturaComAnexacaoProcesso.DoesNotExist:
                pass
            except SolicitacaoAssinaturaComAnexacaoProcesso.MultipleObjectsReturned:
                raise ValidationError('Mais de uma solicitação de assinatura com anexação a processo foi encontrada.')

    def validar_documento(self):
        return self.assinatura.validar_documento(self.documento)

    def save(self, *args, **kwargs):
        if self.pk is None:
            self._notificar_assinatura()
            super().save(*args, **kwargs)


class AssinaturaDocumentoDigitalizado(models.ModelPlus):
    assinatura = models.ForeignKeyPlus('documento_eletronico.Assinatura')
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoDigitalizado', on_delete=models.CASCADE)

    def validar_documento(self):
        return self.assinatura.validar_documento(self.documento)

    def save(self, *args, **kwargs):
        if self.pk is None:
            super().save(*args, **kwargs)


class NivelPermissao:
    LER = 1
    EDITAR = 2
    CHOICES = ((LER, 'Leitura'), (EDITAR, 'Leitura e Edição'))


class TipoPermissao:
    COMPARTILHAMENTO = 1
    REVISAO = 2
    CHOICES = ((COMPARTILHAMENTO, 'Compartilhamento'), (REVISAO, 'Revisão'))


@reversion.register()
class CompartilhamentoDocumentoPessoa(models.ModelPlus):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', related_name='compartilhamento_pessoa_documento', on_delete=models.CASCADE)
    pessoa_permitida = models.ForeignKeyPlus('rh.Pessoa', verbose_name='Pessoa Colaboradora', null=True)
    nivel_permissao = models.PositiveIntegerField('Permissão de Acesso', choices=NivelPermissao.CHOICES, default=NivelPermissao.LER)
    data_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.CurrentUserField(verbose_name='Usuário de Criação', editable=False)
    tipo_permissao = models.PositiveIntegerField('Tipo de Permissão de Acesso', choices=TipoPermissao.CHOICES, default=TipoPermissao.COMPARTILHAMENTO)
    solicitacao_assinatura = models.OneToOneField('documento_eletronico.SolicitacaoAssinatura', on_delete=models.CASCADE, blank=True, null=True, editable=False)

    class Meta:
        verbose_name = 'Compartilhamento de Documentos com Pessoa'
        verbose_name_plural = 'Compartilhamento de Documentos com Pessoas'

    def __str__(self):
        return f'Compartilhamento do documento {self.documento} com {self.pessoa_permitida}'

    def save(self, *args, **kwargs):
        suspender_notificacao = kwargs.pop('suspender_notificacao', False)
        if suspender_notificacao is False:
            Notificar.add_compartilhamento_de_documento(self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        Notificar.remove_compartilhamento_de_documento(self)


@reversion.register()
class CompartilhamentoDocumentoDigitalizadoPessoa(models.ModelPlus):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoDigitalizado', related_name='compartilhamento_pessoa_documento_digitalizado', on_delete=models.CASCADE)
    pessoa_permitida = models.ForeignKeyPlus('rh.Pessoa', verbose_name='Pessoa Colaboradora', null=True)
    data_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.CurrentUserField(verbose_name='Usuário de Criação', editable=False)

    class Meta:
        verbose_name = 'Compartilhamento de Documentos Digitalizados com Pessoa'
        verbose_name_plural = 'Compartilhamento de Documentos Digitalizados com Pessoas'

    def __str__(self):
        return f'Compartilhamento do documento {self.documento} com {self.pessoa_permitida}'


@reversion.register()
class SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa(models.ModelPlus):
    STATUS_AGUARDANDO = 0
    STATUS_DEFERIDA = 1
    STATUS_INDEFERIDA = 2

    STATUS_CHOICES = ((STATUS_AGUARDANDO, 'Pendente'), (STATUS_DEFERIDA, 'Deferida'), (STATUS_INDEFERIDA, 'Indeferida'))

    pessoa_solicitante = models.ForeignKeyPlus('rh.Pessoa', verbose_name='Pessoa Solicitante')
    documento = models.ForeignKeyPlus(
        'documento_eletronico.DocumentoDigitalizado', related_name='solicitacao_compartilhamento_pessoa_documento_digitalizado', on_delete=models.CASCADE
    )
    justificativa_solicitacao = models.TextField('Justificativa Solicitação de Acesso', blank=False)
    status_solicitacao = models.IntegerField('Situação', blank=False, choices=STATUS_CHOICES, default=STATUS_AGUARDANDO)
    data_criacao = models.DateTimeFieldPlus('Data da Solicitação', auto_now_add=True, editable=False)
    usuario_solicitacao = models.CurrentUserField(verbose_name='Usuário de Criação', editable=False)
    usuario_autorizacao = models.ForeignKeyPlus(
        'comum.User', verbose_name='Usuário Autorizador', related_name='usuario_autorizacao_solicitacao_compartilhamento_documento_digitalizado', null=True
    )
    data_autorizacao = models.DateTimeFieldPlus('Data da Autorização', null=True)
    justificativa_autorizacao = models.TextField('Justificativa (Des)Autorização', blank=True, default='')

    class Meta:
        verbose_name = 'Solicitação de Compartilhamento de Documento Digitalizado Sigiloso'
        verbose_name_plural = 'Solicitações de Compartilhamento de Documentos Digitalizados Sigilosos'

    def __str__(self):
        return f'{self.pessoa_solicitante} Solicitou de Compartilhamento do documento {self.documento}'

    def enviar_mail(self, texto, destino):
        titulo = f'[SUAP] Solicitação de Visualização: Documento Eletrônico {self.documento}'
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, destino, categoria='Documento Eletrônico: Solicitação de Visualização')

    def deferida(self):
        return self.status_solicitacao == SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.STATUS_DEFERIDA

    def indeferida(self):
        return self.status_solicitacao == SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.STATUS_INDEFERIDA

    def pendente(self):
        return self.status_solicitacao == SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.STATUS_AGUARDANDO


@reversion.register()
class CompartilhamentoSetorPessoa(models.ModelPlus):
    setor_dono = models.ForeignKeyPlus('rh.Setor')
    pessoa_permitida = models.ForeignKeyPlus('rh.Pessoa', verbose_name='Pessoa Colaboradora', null=True)
    nivel_permissao = models.PositiveIntegerField('Permissão de Acesso', choices=NivelPermissao.CHOICES, default=NivelPermissao.LER)
    data_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.CurrentUserField(verbose_name='Usuário de Criação', editable=False)

    class Meta:
        verbose_name = 'Configuração de Compartilhamento de Documentos entre Setor e Pessoas'
        verbose_name_plural = 'Configurações de Compartilhamento de Documentos entre Setores e Pessoas'

    def __str__(self):
        return f'Compartilhamento do(a) {self.setor_dono} com {self.pessoa_permitida} com permissão de {dict(NivelPermissao.CHOICES)[self.nivel_permissao]}'


class RegistroAcaoDocumento(models.ModelPlus):
    TIPO_CRIACAO = 1
    TIPO_VISUALIZACAO = 2
    TIPO_IMPRESSAO = 3
    TIPO_EDICAO = 4
    TIPO_ASSINATURA = 5
    TIPO_ADICAO_EM_PROCESSO = 6
    TIPO_REMOCAO_EM_PROCESSO = 7
    TIPO_COMPARTILHAMENTO = 8
    TIPO_DESCOMPARTILHAMENTO = 9
    TIPO_SOLICITAR_REVISAO = 10
    TIPO_REVISADO = 11
    TIPO_CANCELAR_REVISAO = 12
    TIPO_CANCELAR_DOCUMENTO = 13
    TIPO_FINALIZACAO = 14
    TIPO_EDICAO_INTERESSADOS = 15
    TIPO_AVALIACAO_REVISAO = 16
    TIPO_SOLICITACAO_ASSINATURA_REJEITADA = 17
    TIPO_EDICAO_NIVEL_ACESSO = 18
    TIPO_ACESSO_EM_FUNCAO_CARGO = 19

    TIPO_CHOICES = (
        (TIPO_CRIACAO, 'Criação'),
        (TIPO_VISUALIZACAO, 'Visualização'),
        (TIPO_IMPRESSAO, 'Impressão'),
        (TIPO_EDICAO, 'Edição'),
        (TIPO_ASSINATURA, 'Assinatura'),
        (TIPO_ADICAO_EM_PROCESSO, 'Adição em Processo'),
        (TIPO_REMOCAO_EM_PROCESSO, 'Remoção em Processo'),
        (TIPO_COMPARTILHAMENTO, 'Compartilhamento'),
        (TIPO_DESCOMPARTILHAMENTO, 'Descompartilhamento'),
        (TIPO_SOLICITAR_REVISAO, 'Solicitação de Revisão'),
        (TIPO_REVISADO, 'Revisão'),
        (TIPO_CANCELAR_REVISAO, 'Solicitação de revisão revogada'),
        (TIPO_CANCELAR_DOCUMENTO, 'Cancelar documento'),
        (TIPO_FINALIZACAO, 'Finalização'),
        (TIPO_EDICAO_INTERESSADOS, 'Edição de interessados'),
        (TIPO_AVALIACAO_REVISAO, 'Revisão avaliada'),
        (TIPO_SOLICITACAO_ASSINATURA_REJEITADA, 'Solicitação de assinatura rejeitada'),
        (TIPO_EDICAO_NIVEL_ACESSO, 'Alteração de Nível de Acesso'),
        (TIPO_ACESSO_EM_FUNCAO_CARGO, 'Acesso em função do cargo'),
    )

    tipo = models.PositiveIntegerField(choices=TIPO_CHOICES, editable=False)
    # Permite null para ação executada em todos os documentos, como por exemplo compartilhamento do setor
    user = models.CurrentUserField(editable=False)
    data = models.DateTimeFieldPlus('Data', auto_now_add=True, editable=False)
    ip = models.GenericIPAddressField(verbose_name='IP', editable=False)
    observacao = models.TextField(editable=False)

    class Meta:
        ordering = ('-data',)
        abstract = True

    def __str__(self):
        if self.tipo in [self.TIPO_ADICAO_EM_PROCESSO, self.TIPO_REMOCAO_EM_PROCESSO, self.TIPO_COMPARTILHAMENTO, self.TIPO_DESCOMPARTILHAMENTO]:
            retorno = self.observacao
        else:
            retorno = f'{dict(self.TIPO_CHOICES)[int(self.tipo)]} do documento.'
        return retorno

    def eh_compartilhamento(self):
        return self.tipo == self.TIPO_COMPARTILHAMENTO

    def eh_descompartilhamento(self):
        return self.tipo == self.TIPO_DESCOMPARTILHAMENTO


class RegistroAcaoDocumentoTexto(RegistroAcaoDocumento):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', editable=False, null=True)

    @classmethod
    def registrar_acao(cls, documento, tipo_acao, user, ip, observacao=''):
        if documento:
            acoes = [RegistroAcaoDocumento.TIPO_VISUALIZACAO, RegistroAcaoDocumento.TIPO_IMPRESSAO]
            if (documento.eh_publico and tipo_acao in acoes) or (documento.eh_documento_pessoal and documento.usuario_criacao == user):
                return
        elif tipo_acao not in [RegistroAcaoDocumento.TIPO_COMPARTILHAMENTO, RegistroAcaoDocumento.TIPO_DESCOMPARTILHAMENTO]:
            raise Exception("O tipo de ação registrado exige um documento.")
        #
        user = user if not user.is_anonymous else None
        cls.objects.create(tipo=tipo_acao, documento=documento, ip=ip, observacao=observacao, user=user)

    @classmethod
    def registar_acesso(cls, documento, user, ip, acesso_via_cargo):
        if acesso_via_cargo:
            tipo = cls.TIPO_ACESSO_EM_FUNCAO_CARGO
            obs = "Acesso Procuradoria" if eh_procurador(user) else "Acesso Auditoria"
            cls.registrar_acao(documento, tipo, user, ip, observacao=obs)
        else:
            tipo = RegistroAcaoDocumentoTexto.TIPO_VISUALIZACAO
            cls.registrar_acao(documento, tipo, user, ip)


class RegistroAcaoDocumentoDigitalizado(RegistroAcaoDocumento):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoDigitalizado', editable=False, null=True)


class DocumentoTextoPessoal(DocumentoTexto):

    class Meta:
        proxy = True
        verbose_name = 'Documento de Texto Pessoal'
        verbose_name_plural = 'Documentos de Texto Pessoais'

    objects = DocumentoTextoPessoalManager()


class DocumentoDigitalizadoPessoal(DocumentoDigitalizado):

    class Meta:
        proxy = True
        verbose_name = 'Documento Digitalizado Pessoal'
        verbose_name_plural = 'Documentos Digitalizados Pessoais'

    objects = DocumentoDigitalizadoPessoalManager()

    def get_absolute_url(self,):
        return f"/documento_eletronico/visualizar_documento_digitalizado_pessoal/{self.pk}/"

    def __str__(self):
        return f"Documento Digitalizado Pessoal - {self.assunto}"


class DocumentoTextoAnexoDocumentoTexto(models.ModelPlus):

    data_hora_inclusao = models.DateTimeFieldPlus('Data de Inclusão', auto_now_add=True, editable=False)
    usuario_inclusao = models.CurrentUserField(verbose_name='Usuário de Inclusão', related_name='documentos_anexados_texto_usuarios', null=False, editable=False)
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento', related_name='documentos_anexados_documento_texto')
    documento_anexado = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento', related_name='documentos_anexados_documento_texto_anexado')

    class Meta:
        verbose_name = 'Documento Texto Anexado'
        verbose_name_plural = 'Documentos Textos Anexados'

    def __str__(self):
        return f"{self.documento_anexado} anexado a {self.documento}"


class DocumentoTextoAnexoDocumentoDigitalizado(models.ModelPlus):

    data_hora_inclusao = models.DateTimeFieldPlus('Data de Inclusão', auto_now_add=True, editable=False)
    usuario_inclusao = models.CurrentUserField(verbose_name='Usuário de Inclusão', related_name='documentos_anexados_digitalizado_usuarios', null=False, editable=False)
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento', related_name='documentos_anexados_documento_digitalizado')
    documento_anexado = models.ForeignKeyPlus('documento_eletronico.DocumentoDigitalizado', verbose_name='Documento', related_name='documentos_anexados_documento_digitalizado_anexado')

    class Meta:
        verbose_name = 'Documento Digitalizado Anexado'
        verbose_name_plural = 'Documentos Digitalizados Anexados'

    def __str__(self):
        return f"{self.documento_anexado} anexado a {self.documento}"


class DocumentoDigitalizadoAnexoSimples(DocumentoDigitalizado):

    class Meta:
        proxy = True
        verbose_name = 'Documento Digitalizado Anexo Simples'
        verbose_name_plural = 'Documentos Digitalizados Anexos Simples'

    objects = DocumentoDigitalizadoAnexoManager()

    def get_absolute_url(self,):
        return f"/documento_eletronico/visualizar_documento_digitalizado_pessoal/{self.pk}/"

    def pode_ler(self, user=None, consulta_publica_hash=None, leitura_para_barramento=False, eh_consulta_publica=False):
        if not eh_consulta_publica:
            user = user or tl.get_user()
        # Este é um documento anexo ximples
        # Ele só existe para ser anexado a um documento
        # Neste caso o pode ler dele sempre será o do documento ao qual ele foi anexado
        doc = DocumentoTextoAnexoDocumentoDigitalizado.objects.get(documento_anexado__pk=self.id)
        return doc.documento.pode_ler(user, consulta_publica_hash, leitura_para_barramento, eh_consulta_publica)
