import base64
import io
from itertools import chain
import operator
import re
import uuid
from datetime import datetime, timedelta
from functools import reduce

import qrcode
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, Count, Subquery, F, Value
from django.db.models.query import QuerySet
from django.db.utils import IntegrityError
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_fsm import FSMIntegerField, transition, ConcurrentTransitionMixin
from model_utils.managers import InheritanceManager
from queryset_sequence import QuerySetSequence
from reversion import revisions as reversion

from comum.models import User
from comum.models import Vinculo, Configuracao
from comum.utils import get_setor, get_todos_setores, tl, get_values_from_choices
from conectagov_pen.api_pen_services import cancelar_tramite
from conectagov_pen.models import ProcessoBarramento, TramiteBarramento
# Comentado por conta do "pode_ler_consulta_publica"
# from contratos.models import Contrato
from djtools.db import models
from djtools.middleware.threadlocals import get_user
from djtools.templatetags.filters import format_iterable
from djtools.templatetags.filters import in_group
from djtools.utils import send_notification, get_datetime_now, render
from documento_eletronico.assinar_documento import gerar_assinatura_documento_senha
from documento_eletronico.models import (
    Assinatura,
    Documento,
    RegistroAcaoDocumentoTexto,
    RegistroAcaoDocumento,
    DocumentoTexto,
    DocumentoDigitalizado,
    CompartilhamentoDocumentoDigitalizadoPessoa,
    TipoConferencia,
    TipoDocumento,
    HipoteseLegal,
    NivelAcesso as NivelAcessoEnum
)
from documento_eletronico.status import DocumentoStatus, SolicitacaoStatus
from documento_eletronico.utils import gerar_hash, get_variaveis
from documento_eletronico.utils import processar_template_ckeditor, EstagioProcessamentoVariavel, \
    convert_pdf_to_string_b64
from processo_eletronico.exceptions import ProcessoEletronicoException
from rh.models import Servidor, ServidorFuncaoHistorico, Setor, Pessoa, PessoaFisica
from .managers import SolicitacaoDespachoManager, SolicitacaoCienciaManager, TipoProcessoManager
from .status import SolicitacaoJuntadaStatus, SolicitacaoJuntadaDocumentoStatus, ProcessoStatus, CienciaStatus
from .utils import (
    gerar_capa_processo_pdf,
    gerar_requerimento_processo_pdf,
    gerar_parecer_pdf,
    gerar_despacho_pdf,
    setores_que_sou_chefe_ou_tenho_poder_de_chefe,
    gerar_minuta_pdf,
    gerar_processo_pdf,
    gerar_partes_processo_pdf,
    gerar_processo_zip,
    acesso_ao_processo_em_funcao_cargo
)

"""
Estrutura do Número     Total de Dígitos
00000.000000/00             13
00000.000000/00-0           13 + 1 dígito verificador
00000.000000/00-00          13 + 2 dígitos verificadores
00000.000000/00-DV          13 + letras “D” e “V”
00000.000000/0000-00        15 + 2 dígitos verificadores
00000.000000/0000-DV        15 + letras “D” e “V”
0000000.00000000/0000-00    19 + 2 dígitos verificadores
"""

MSG_NAO_POSSUI_ACESSO_CAIXA_PROCESSO = (
    'Você não possui acesso a caixa de processos </br></br> '
    'Apenas as seguintes pessoas poderão ter acesso a caixa de processos de um setor: </br>'
    '  - Chefe do setor; </br>'
    '  - Pessoas autorizadas pelo chefe de setor; </br>'
    '  - Pessoas com poder de chefe de processos e documentos eletrônicos. </br></br>'
    'Se precisar ter acesso a caixa de processos de um setor entre contato com o chefe desse setor. </br></br>'
    'Se precisar ter poder de chefe de processos e documentos eletrônicos em um setor entre contato com '
    'o chefe desse setor.</strong> </br></br>'
    'Se você já for chefe de setor entre em contato com a Gestão de Pessoas para verificar seu cadastro de '
    'chefe de setor no SUAP. </br></br>'
    'Se você deseja ter poderes de chefe de processos e documentos eletrônicos em um setor entre em contato '
    'com o chefe desse setor.'
)


def formatar_numero_protocolo_21(numero_protocolo):
    """
        Method that formats a protocolo number
        Tests:
            >>> print formatar_numero_protocolo_21('000043900000001201583')
            0000439.00000001/2015-83
    """
    #
    if numero_protocolo.isdigit() and len(numero_protocolo) == 21:
        siorg = numero_protocolo[0:7]
        numero_processo = numero_protocolo[7:15]
        ano = numero_protocolo[15:19]
        dv = numero_protocolo[19:21]
        return "{}.{}/{}-{}".format(siorg, numero_processo, ano, dv)
    raise ValidationError('Número de protocolo inválido: %s.' % numero_protocolo)


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def convert_to_snake_case(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def get_chave_secreta():
    return settings.DOC_SECRET_KEY


def get_chave(pessoa):
    return '{}:{}'.format(get_chave_secreta(), pessoa.id)


def gerar_assinatura_tramite_senha(tramite, pessoa):
    from djtools.security.signature import create_signature

    chave = get_chave(pessoa)
    return create_signature(chave, tramite.hash_conteudo).decode('utf-8')


class HistoricoProcesso(models.ModelPlus):
    TIPO_STATUS = 1
    TIPO_NIVEL_ACESSO = 2
    TIPO_CHOICES = [[TIPO_STATUS, 'Situação'], [TIPO_NIVEL_ACESSO, 'Nivel de Acesso']]

    processo = models.ForeignKeyPlus('processo_eletronico.Processo')
    data_hora = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True)
    usuario = models.CurrentUserField(verbose_name='Usuário de Criação')
    tipo = models.PositiveIntegerField('Tipo', choices=TIPO_CHOICES)
    descricao = models.TextField('Descrição')


class ProcessoPermissionMixin:
    def by_user(self, user):
        pessoa_fisica = user.get_profile()
        setores = Tramite.get_todos_setores(user)
        # 1 - Um processo pode ser visualizado se é publico
        predicate_publicos = Q(nivel_acesso=Processo.NIVEL_ACESSO_PUBLICO)
        predicate_meus = Q(interessados=pessoa_fisica)
        # 2 - Se for restrito, ele so podera ser acessado por quem esta no mesmo setor no qual ele foi criado
        # # e pelos setores que ele tramitou
        predicate_restritos = Q(nivel_acesso=Processo.NIVEL_ACESSO_RESTRITO) & \
            (Q(setor_criacao__in=setores) | Q(tramites__destinatario_setor__in=setores))
        # 3 - Se for privado, quem criou o processo tem acesso juntamente com as pessoas por quem ele tramitou.
        predicate_privados = Q(nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO) & \
            (Q(usuario_gerador=user) | Q(tramites__destinatario_pessoa=pessoa_fisica))
        # 4 - Se existe algum documento que está aguardando a assinatura do usuário para poder ser anexado ao processo.
        predicate_com_documento_pendente_de_assinatura_para_ser_anexado = Q(
            solicitacoes_assinatura_com_anexacao__solicitacao_assinatura__solicitado=pessoa_fisica) & Q(
            solicitacoes_assinatura_com_anexacao__solicitacao_assinatura__status=SolicitacaoStatus.STATUS_ESPERANDO
        )
        return self.filter(
            predicate_meus | predicate_publicos | predicate_restritos | predicate_privados | predicate_com_documento_pendente_de_assinatura_para_ser_anexado
        ).distinct()


class ProcessoQuerySet(QuerySet, ProcessoPermissionMixin):
    pass


class ProcessoManager(models.Manager, ProcessoPermissionMixin):
    def get_queryset(self):
        return ProcessoQuerySet(self.model, using=self._db)


class AtivosManager(models.Manager, ProcessoPermissionMixin):
    def get_queryset(self):
        queryset = ProcessoQuerySet(self.model, using=self._db)
        return queryset.filter(status=ProcessoStatus.STATUS_ATIVO)


class Processo(ConcurrentTransitionMixin, models.ModelPlus):
    SEARCH_FIELDS = ['numero_protocolo', 'numero_protocolo_fisico', 'assunto', 'interessados__nome']

    PERMISSAO_OPERAR_PROCESSO = 1
    PERMISSAO_OPERAR_CRIAR_PROCESSO = 2
    PERMISSAO_RETORNO_PROGRAMADO = 4
    PERMISSAO_PROCESSO_CHOICES = [
        [PERMISSAO_OPERAR_PROCESSO, 'Permissão para Operar Processos Eletrônicos'],
        # Corresponde ao grupo Tramitador de Processos Eletrônicos
        [PERMISSAO_OPERAR_CRIAR_PROCESSO, 'Permissão para Criar e Operar Processos Eletrônicos'],
        # Corresponde ao grupo Operador de Processo Eletrônico
        [PERMISSAO_RETORNO_PROGRAMADO,
         'Permissão para cadastrar Retorno Programado nos trâmites de Processos Eletrônicos'],
    ]

    NIVEL_ACESSO_PUBLICO = 1
    NIVEL_ACESSO_RESTRITO = 2
    NIVEL_ACESSO_PRIVADO = 3
    NIVEL_ACESSO_CHOICES = [[NIVEL_ACESSO_PUBLICO, 'Público'], [NIVEL_ACESSO_RESTRITO, 'Restrito'],
                            [NIVEL_ACESSO_PRIVADO, 'Privado']]

    # Dados obrigatórios do NUP
    CODIGO_SIORG = 439  # Código SIORG do IFRN.

    uuid = models.UUIDField(unique=True, default=uuid.uuid4)
    # Numero unico de protocolo (NUP 21)
    numero_protocolo = models.CharFieldPlus('Número Único de Protocolo', max_length=25, editable=False, unique=True,
                                            db_index=True)

    # Numero único de protocolo (NUP 17)
    # Este atributo foi criado temporariamente por conta de sistemas do Governo que eram pra estar usando o NUP 21 mas
    # ainda estão usando NUP 17, contrariando o que o próprio governo determinou.
    numero_protocolo_fisico = models.CharFieldPlus('Número Único de Protocolo', max_length=25, editable=False,
                                                   blank=True, null=True, db_index=True)

    # Lista de interessados
    interessados = models.ManyToManyFieldPlus('rh.Pessoa')
    tipo_processo = models.ForeignKeyPlus('processo_eletronico.TipoProcesso', verbose_name='Tipo de Processo')
    assunto = models.UnaccentField('Assunto', blank=True, db_index=True)
    nivel_acesso = models.PositiveIntegerField('Nível de Acesso', choices=NIVEL_ACESSO_CHOICES,
                                               default=NIVEL_ACESSO_PUBLICO)
    hipotese_legal = models.ForeignKeyPlus('documento_eletronico.HipoteseLegal', verbose_name='Hipótese Legal',
                                           blank=False, null=True)

    # Dados de controle do processo.
    status = FSMIntegerField('Situação', default=ProcessoStatus.STATUS_ATIVO, choices=ProcessoStatus.STATUS_CHOICES,
                             protected=True)
    # Dados do usuario gerador do processo:
    data_hora_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data/Hora da Criação')
    usuario_gerador = models.CurrentUserField(verbose_name='Cadastrado por', null=True, editable=False,
                                              related_name='created_by')
    setor_criacao = models.ForeignKeyPlus('rh.Setor', null=False, blank=False, on_delete=models.CASCADE,
                                          verbose_name="Setor de Criação", related_name='processos_setor_origem')
    # Dados da última modificação feita no modelo.
    modificado_por = models.CurrentUserField(verbose_name='Modificado por', null=False, related_name='modified_by')
    ultima_modificacao = models.DateTimeField(auto_now=True)
    ultimo_tramite = models.OneToOneFieldPlus('processo_eletronico.Tramite', null=True,
                                              related_name='processo_ultimo_tramite')
    setor_atual = models.ForeignKeyPlus('rh.Setor', null=True, related_name='processo_setor_atual')

    # dados da finalização
    data_finalizacao = models.DateTimeField(editable=False, null=True, verbose_name='Data de Finalização')
    usuario_finalizacao = models.ForeignKeyPlus('comum.User', related_name='usuario_finalizacao_set', editable=False,
                                                null=True, on_delete=models.CASCADE)
    observacao_finalizacao = models.TextField('Despacho', blank=True, editable=False)

    # Processos relacionados
    processos_relacionados = models.ManyToManyFieldPlus(
        'self', through='ProcessosRelacionados', symmetrical=False, related_name='relacionamentos',
        verbose_name='Processos Relacionados', blank=True
    )

    # Demanda_495 - pessoas que marcam para acompanhar os processos públicos
    pessoas_acompanhando_processo = models.ManyToManyFieldPlus(
        'rh.Pessoa', related_name='pessoas_acompanhando_processo',
        verbose_name='Usuários Que Marcaram o Processo como Interesse', blank=True
    )

    objects = ProcessoManager()
    ativos = AtivosManager()

    class Meta:
        verbose_name = 'Processo Eletrônico'
        verbose_name_plural = 'Processos Eletrônicos'
        permissions = (('pode_tramitar_processos_eletronicos', "Pode Tramitar processos eletrônicos"),
                       ('pode_abrir_requerimento', "Pode abrir requerimento"),
                       ('pode_alterar_nivel_acesso', "Pode alterar nível de acesso dos processos"))

    def __str__(self):
        return self.get_numero_unico_protocolo()

    @staticmethod
    @transaction.atomic
    def atualizar_status_processo(processo):

        if processo.status in [ProcessoStatus.STATUS_ARQUIVADO, ProcessoStatus.STATUS_FINALIZADO,
                               ProcessoStatus.STATUS_ANEXADO]:
            return processo

        solicitacoes_juntada = SolicitacaoJuntada.objects.filter(tramite__processo=processo)
        solicitacoes_ciencia = SolicitacaoCiencia.objects.filter(processo=processo)

        # =============================================================================================
        # Atualiza o status de cada uma das SOLICITAÇÕES DE JUNTADA do processo
        # =============================================================================================
        for solicitacao_juntada in solicitacoes_juntada:
            # print(u'>>> >>> Sol de juntada >>> {}'.format(solicitacao_juntada.__dict__))

            # CASO 1: Se a solicitacao ja tiver sido CONCLUIDA pelo solicitado
            #   - Nada vai ser feito com essa solicitacao

            # CASO 2: Se a solicitacao tiver PENDENTE e PRAZO NAO EXPIRADO e TIVER OU NAO DOCUMENTOS AGUARDANDO AVALIACAO
            #   - Nada vai ser feito com essa solicitacao

            # CASO 3: Se a solicitacao tiver PENDENTE e PRAZO EXPIRADO e TIVER DOCUMENTOS AGUARDANDO AVALIACAO
            #   - A solicitacao tera seu status aterado para CONCLUIDA
            if (
                    solicitacao_juntada.estah_esperando() and solicitacao_juntada.expirou and solicitacao_juntada.possui_solicitacoes_de_juntada_pendentes()) and (
                    not solicitacao_juntada.estah_concluida()
            ):
                solicitacao_juntada.concluir_solicitacao()
                solicitacao_juntada.save()

            # CASO 4: Se a solicitacao tiver PENDENTE e PRAZO EXPIRADO e NAO TIVER DOCUMENTOS
            #   - A solicitacao tera seu status aterado para EXPIRADA
            if (
                    solicitacao_juntada.estah_esperando() and solicitacao_juntada.expirou and not solicitacao_juntada.possui_solicitacoes_de_juntada_pendentes()) and (
                    not solicitacao_juntada.estah_concluida()
            ):
                solicitacao_juntada.expirar_solicitacao()
                solicitacao_juntada.save()

            # CASO 5: Se a solicitacao tiver CONCLUIDA e NAO TIVER DOCUMENTOS PENDENTES DE ANALISE
            #   - A solicitacao tera seu status aterado para FINALIZADA
            if (
                    solicitacao_juntada.estah_concluida() and not solicitacao_juntada.possui_solicitacoes_de_juntada_pendentes()) and not solicitacao_juntada.estah_finalizada():
                solicitacao_juntada.finalizar_solicitacao()
                solicitacao_juntada.save()

        # =============================================================================================
        # Atualiza o status de cada uma das SOLICITAÇÕES DE CIENCIA do processo
        # =============================================================================================
        for solicitacao_ciencia in solicitacoes_ciencia:
            # print(u'>>> >>> Sol de ciencia >>> {}'.format(solicitacao_ciencia.__dict__))

            # CASO 1: Se a solicitacao tiver com status CANCELADA
            #   - Nada vai ser feito com essa solicitacao

            # CASO 2: Se a solicitacao tiver com status CONSIDERADO CIENTE
            #   - Nada vai ser feito com essa solicitacao

            # CASO 3: Se a solicitacao tiver com status CIENTE
            #   - Nada vai ser feito com essa solicitacao

            # CASO 4: Se a solicitacao tiver com status AGUARDANDO CIENCIA e TIVER SIDO DADO CIENCIA (tem data de ciencia)
            #   - A solicitacao tera seu status aterado para CIENTE
            if (
                    solicitacao_ciencia.esta_esperando_nao_expirado() and solicitacao_ciencia.data_ciencia is not None) and not solicitacao_ciencia.estah_ciente():
                solicitacao_ciencia.ciente()
                solicitacao_ciencia.save()

            # CASO 5: Se a solicitacao tiver com status AGUARDANDO CIENCIA e NAO TIVER SIDO DADO CIENCIA (tem data de ciencia) e TIVER PRAZO EXPIRADO
            #   - A solicitacao tera seu status aterado para CONSIDERADO CIENTE
            if (
                    solicitacao_ciencia.esta_esperando_expirado() and solicitacao_ciencia.data_ciencia is None) and not solicitacao_ciencia.considerado_ciente():
                solicitacao_ciencia.considerar_ciente()
                try:
                    papel = solicitacao_ciencia.solicitado.user.get_relacionamento().papeis_ativos.first()
                    if not papel:
                        raise Exception()
                except Exception:
                    raise ValidationError(f"O solicitado {solicitacao_ciencia.solicitado.nome} não possui papel ativo!")
                assunto = "Termo de Ciência: Conhecimento/Notificação"
                solicitacao_ciencia.gerar_termo_ciencia(processo, solicitacao_ciencia.solicitado.user, papel, assunto)
                solicitacao_ciencia.save()

            # CASO 6: Se a solicitacao tiver com status AGUARDANDO CIENCIA e NAO TIVER SIDO DADO CIENCIA (tem data de ciencia) e NAO TIVER PRAZO EXPIRADO
            #   - Nada vai ser feito com essa solicitacao

        # =============================================================================================
        # Atualiza o status do PROCESSO
        # =============================================================================================

        # Juntada
        # ----------------
        solicitacoes_juntada_pendentes = solicitacoes_juntada.filter(
            status=SolicitacaoJuntadaStatus.STATUS_ESPERANDO).exists()

        solicitacoes_juntada_concluida = solicitacoes_juntada.filter(
            status=SolicitacaoJuntadaStatus.STATUS_CONCLUIDO).exists()

        # Ciencia
        # ----------------
        solicitacoes_ciencia_pendentes = solicitacoes_ciencia.filter(data_ciencia__isnull=True,
                                                                     status=CienciaStatus.STATUS_ESPERANDO).exists()

        solicitacoes_ciencia_pendentes_com_juntada = solicitacoes_ciencia.filter(
            data_ciencia__isnull=True, status=CienciaStatus.STATUS_ESPERANDO, data_limite_juntada__isnull=False
        ).exists()

        solicitacoes_ciencia_pendentes_sem_juntada = solicitacoes_ciencia.filter(
            data_ciencia__isnull=True, status=CienciaStatus.STATUS_ESPERANDO, data_limite_juntada__isnull=True
        ).exists()

        # Altera a situação do processo para "Aguardando juntada de documentos"
        # - O processo pode ter este status quando:
        #   - Existir alguma solicitação de juntada com o status PENDENTE
        #   - OU Se existir solicitacao de CIENCIA PENDENTE e que seja COM JUNTADA (com data limite de juntada)
        # --------------------------------
        if (
                solicitacoes_juntada_pendentes or solicitacoes_ciencia_pendentes_com_juntada) and not processo.esta_aguardando_juntada():
            processo.aguardar_juntada_documento()
            processo.save()

        # Altera a situação do processo "Aguardando ciência"
        # - O processo pode ter este status quando:
        #   - Existir alguma solicitacao de ciencia PENDENTE e que NAO SEJA COM JUNTADA (sem data limite de juntada)
        # --------------------------------
        elif solicitacoes_ciencia_pendentes_sem_juntada and not processo.esta_aguardando_ciencia():
            processo.aguardar_ciencia()
            processo.save()

        # Altera a situação do processo para "Em validação de juntada de documentos"
        # - O processo pode ter este status quando:
        #   - Existir alguma solicitação de juntada com o status "Concluída pelo solicitado"
        #   - E não existir nehuma solicitação de juntada pendente
        #   - E não ciencias pendentes com juntada
        # --------------------------------
        elif (
                solicitacoes_juntada_concluida and (
                not solicitacoes_juntada_pendentes and not solicitacoes_ciencia_pendentes_com_juntada)
        ) and not processo.esta_em_homologacao_juntada():
            processo.homologar_juntada_documento()
            processo.save()

        # Altera a situação do processo "Em Tramite"
        # --------------------------------
        elif not solicitacoes_ciencia_pendentes and (
                processo.esta_aguardando_ciencia() and not processo.esta_aguardando_juntada()) and not processo.esta_ativo():
            processo.informar_ciencia()
            processo.save()
        else:

            coloca_em_tramite_pelas_juntadas = True
            if solicitacoes_juntada_pendentes or solicitacoes_juntada_concluida:
                coloca_em_tramite_pelas_juntadas = False

            coloca_em_tramite_por_ciencias = True
            if solicitacoes_ciencia_pendentes:
                coloca_em_tramite_por_ciencias = False

            if (coloca_em_tramite_pelas_juntadas and coloca_em_tramite_por_ciencias) and not processo.esta_ativo():
                if not processo.esta_em_tramite_externo():
                    processo.colocar_em_tramite()
                    processo.save()

        return processo

    def verificar_dados_processo(self):

        if self.interessados is None:
            raise ValidationError("Não é possível tramitar o atual processo, pois não possui um interessado válido.")

        invalidos = []
        for interessado in self.interessados.all():
            if not interessado.cpf_ou_cnpj_valido():
                invalidos.append("{}".format(interessado))
        if invalidos:
            raise ValidationError(
                "Não é possível tramitar o atual processo, pois os seguintes interessados não são válidos: {}.".format(
                    ", ".join(invalidos)))

    def verificar_criacao_processo(self):
        if 'protocolo' in settings.INSTALLED_APPS:
            ProcessoNup17 = apps.get_model("protocolo", "Processo")
            if not ProcessoNup17.objects.filter(numero_processo_eletronico=self.numero_protocolo).exists():
                raise ValidationError("Dados do processo: O número de processo físico não foi criado.")
            self.verificar_dados_processo()

    def save(self, *args, **kwargs):
        with transaction.atomic():
            is_insert = self.pk is None
            if is_insert:
                if not hasattr(self, 'setor_criacao') or self.setor_criacao is None:
                    self.setor_criacao = get_setor(self.usuario_gerador)
                # NUP 21
                self.numero_protocolo = self._proximo_numero_unico_protocolo()
            else:
                processo_salvo_banco = Processo.objects.get(id=self.id)
                if processo_salvo_banco.setor_criacao_id != self.setor_criacao_id:
                    raise ValidationError(
                        'O setor de criação do processo não pode ser alterado uma vez que o ' 'número do processo depende do setor.')

            self.setor_atual = self.get_setor_atual()

            if not hasattr(self, 'modificado_por'):
                self.modificado_por = tl.get_user()
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
            except IntegrityError as e:
                # Atribui ao numero_protocolo o valor do próximo NUP 21 para resolver problema que acontecia
                # de retornar o mesmo NUP 21 para duas transações concorrentes.
                # Exemplo da mensagem de erro: duplicate key value violates unique constraint "processo_eletronico_processo_numero_protocolo_key"
                # DETAIL: Key (numero_protocolo)=(0116337.00000057/2019-37) already exists.
                if 'processo_eletronico_processo_numero_protocolo_key' in ''.join(e.args):
                    self.numero_protocolo = self._proximo_numero_unico_protocolo()
                    super().save(*args, **kwargs)
                else:
                    raise e

    def get_absolute_url(self):
        return f'/processo_eletronico/processo/{self.id}/'

    def get_absolute_url_consulta_publica(self):
        return f'/processo_eletronico/visualizar_processo/{self.uuid}/'

    # def get_capa_pdf(self, user=None):
    def get_capa_pdf(self):
        # user = user or tl.get_user()
        # return gerar_capa_processo_pdf(user=user, processo=self)
        return gerar_capa_processo_pdf(processo=self)

    def get_capa_pdf_as_string_b64(self, user=None):
        return convert_pdf_to_string_b64(pdf=self.get_capa_pdf(user=user))

    def get_requerimento_pdf(self):
        return gerar_requerimento_processo_pdf(processo=self)

    def get_requerimento_pdf_as_string_b64(self):
        return convert_pdf_to_string_b64(pdf=self.get_requerimento_pdf())

    def get_pdf(self, user=None, leitura_para_barramento=False, eh_consulta_publica=False):
        pdf = gerar_processo_pdf(processo=self, user=user, leitura_para_barramento=leitura_para_barramento,
                                 eh_consulta_publica=eh_consulta_publica)
        return pdf

    def get_zip(self, user=None, leitura_para_barramento=False, eh_consulta_publica=False):
        return gerar_processo_zip(processo=self, user=user, leitura_para_barramento=leitura_para_barramento, eh_consulta_publica=eh_consulta_publica)

    def get_partes_processo_pdf(self, user=None, leitura_para_barramento=False):
        '''
        Este método está descrito em :func:`~utils.gerar_partes_processo_pdf`.
        '''
        partes_processo_pdf = gerar_partes_processo_pdf(processo=self, user=user,
                                                        leitura_para_barramento=leitura_para_barramento)
        return partes_processo_pdf

    @property
    def get_nre_processo_barramento(self):
        if ProcessoBarramento.objects.filter(processo=self).exists():
            return ProcessoBarramento.objects.get(processo=self).nre_barramento_pen
        return None

    @property
    def get_interessados_externos(self):
        if ProcessoBarramento.objects.filter(processo=self, criado_no_suap=False).exists():
            processo_barramento = ProcessoBarramento.objects.get(processo=self)
            if TramiteBarramento.objects.filter(processo_barramento=processo_barramento,
                                                status=TramiteBarramento.STATUS_RECEBIDO).exists():
                metadados_processo = TramiteBarramento.objects.filter(processo_barramento=processo_barramento,
                                                                      status=TramiteBarramento.STATUS_RECEBIDO)[
                    0].metadados_processo
                if 'processo' in metadados_processo:
                    interessados = metadados_processo['processo']['interessados']
                    interessados_externos = list()
                    for interessado in interessados:
                        interessados_externos.append(interessado['nome'])
                    if interessados_externos:
                        return interessados_externos
        return None

    @property
    def get_tipo_processo_no_orgao_origem(self):
        if ProcessoBarramento.objects.filter(processo=self, criado_no_suap=False).exists():
            processo_barramento = ProcessoBarramento.objects.get(processo=self)
            if TramiteBarramento.objects.filter(processo_barramento=processo_barramento,
                                                status=TramiteBarramento.STATUS_RECEBIDO).exists():
                metadados_processo = TramiteBarramento.objects.filter(processo_barramento=processo_barramento,
                                                                      status=TramiteBarramento.STATUS_RECEBIDO)[
                    0].metadados_processo
                if 'processo' in metadados_processo:
                    return metadados_processo['processo']['processoDeNegocio']
        return None

    @property
    def qrcode(self):
        img = qrcode.make(self.get_absolute_url())
        buffer_img = io.BytesIO()
        img.save(buffer_img, 'png')
        return buffer_img

    @property
    def qrcode_base64image(self):
        qrcode_data = base64.b64encode(self.qrcode.getvalue())
        return "data:image/png;base64," + qrcode_data.decode('utf-8')

    def get_codigo_protocolo(self):
        pessoa_fisica = self.usuario_gerador.get_profile()
        if pessoa_fisica.funcionario.setor.uo.codigo_protocolo is not None:
            return pessoa_fisica.funcionario.setor.uo.codigo_protocolo
        return None

    def get_setor_atual(self):
        if self.ultimo_tramite:
            if self.ultimo_tramite.foi_recebido:
                return self.ultimo_tramite.destinatario_setor or self.ultimo_tramite.destinatario_pessoa.pessoafisica.sub_instance().setor
            elif not self.ultimo_tramite.tramite_barramento:
                return self.ultimo_tramite.remetente_setor or self.ultimo_tramite.remetente_pessoa.pessoafisica.sub_instance().setor
        else:
            return self.setor_criacao

    def get_registros_acoes(self):
        return self.registroacaoprocesso_set.all()

    def get_registros_acoes_restrito(self):
        return self.registroacaoprocesso_set.all().exclude(
            tipo__in=[RegistroAcaoProcesso.TIPO_VISUALIZACAO, RegistroAcaoProcesso.TIPO_IMPRESSAO])

    def get_numero_unico_protocolo(self):
        return '{}'.format(self.numero_protocolo_fisico or self.numero_protocolo)

    def get_interessados(self):
        return ', '.join([interessado.nome for interessado in self.interessados.all()])

    get_interessados.short_description = 'interessados'

    def get_ultimo_comentario(self):
        return self.comentarios.latest('data')

    def pode_ver_informacoes_basicas(self, usuario):
        usuario = usuario or get_user()
        if self.eh_publico() or self.eh_restrito():
            return True
        if hasattr(self, '_pode_ver_informacoes_basicas_privado'):
            return self._pode_ver_informacoes_basicas_privado
        esta_com_processo = False
        if self.ultimo_tramite:
            if self.ultimo_tramite.foi_recebido:
                pessoa_com_processo = self.ultimo_tramite.destinatario_pessoa
            else:
                pessoa_com_processo = self.ultimo_tramite.remetente_pessoa
            esta_com_processo = pessoa_com_processo and pessoa_com_processo.pk == usuario.get_profile().pk
        else:
            esta_com_processo = self.usuario_gerador == usuario

        acesso_em_funcao_cargo = acesso_ao_processo_em_funcao_cargo(usuario, self)
        self._pode_ver_informacoes_basicas_privado = esta_com_processo or acesso_em_funcao_cargo or self.interessados.filter(
            pk=usuario.get_profile().pk).exists()
        #
        return self._pode_ver_informacoes_basicas_privado

    # A Portaria Interministerial numero 2.321, de 30 de dezembro de 2014 entra em vigor em 2018. A partir dessa data
    # o metodo abaixo deve ser utilizado para gerar os numeros do protocolo.
    # http://www.comprasgovernamentais.gov.br/index.php/legislacao?layout=edit&id=574
    @transaction.atomic()
    def _proximo_numero_unico_protocolo(self):
        """
        Formato 21: 19 digitos + 2 digitos verificadores: 0000000.00000000/0000-00
                                                          0000439.00000001/2015-83
        Obs: Contando a formatação são 24 characteres ao total.
        """
        # Obtendo o código SIORG do setor.
        # http://www.comprasgovernamentais.gov.br/index.php/legislacao?layout=edit&id=574
        codigo_siorg = self.setor_criacao.get_codigo_siorg()
        if not codigo_siorg:
            raise Exception(
                'O setor "{}" não está com o código SIORG cadastrado.' ' É impossível gerar o número do processo sem essa informação.'.format(
                    self.setor_criacao))

        # Ano corrente.
        ano_corrente = datetime.today().year
        # Código de identificacao da unidade administrativa
        # Montando o número do processo.
        # Grupo 1:
        #   O primeiro grupo será constituído de sete (07) dígitos referentes ao código de
        #   identificação da unidade administrativa no SIORG, que identificará a unidade
        #   protocolizadora do órgão ou entidade de origem do documento, avulso ou
        #   processo; Caso o código seja constituído de menos de sete dígitos,
        #   deverão ser atribuídos zeros à esquerda até que se complete o número
        #   de dígitos do primeiro grupo do NUP.
        codigo_unidade = '%07d' % int(codigo_siorg)
        # Grupo 2:
        #   O segundo grupo, separado do primeiro grupo por um ponto, será constituído de
        #   oito dígitos e determinará o registro sequencial dos documentos, avulsos ou
        #   processos, sequência que deverá ser reiniciada a cada ano;
        try:
            ultimo_processo_ano = Processo.objects.filter(numero_protocolo__startswith=codigo_unidade,
                                                          data_hora_criacao__year=ano_corrente).latest('id')
            id_processo = ultimo_processo_ano.numero_protocolo.split('/')[0]
            proximo_id_processo = int(id_processo.split('.')[1]) + 1
        except Processo.DoesNotExist:
            # Ainda não existe nenhum processo no ano corrente
            proximo_id_processo = 1
        #
        id_processo = '%08d' % proximo_id_processo
        # Montando número base do protocolo
        numero_protocolo = '{}{}{}'.format(codigo_unidade, id_processo, ano_corrente)
        # Calculando os dois digitos verificadores.
        dv = '%02d' % (98 - (int(numero_protocolo) % 97))
        return '{}.{}/{}-{}'.format(codigo_unidade, id_processo, ano_corrente, dv)

    # A Portaria Interministerial numero 2.321, de 30 de dezembro de 2014 foi
    # suspensa até 2018. E até lá devemos usar a numeração antiga descrita no
    # metodo abaixo.
    def _proximo_numero_formato17(self):
        # Obtendo o código do protocolo.
        codigo_protocolo = int(self.get_codigo_protocolo())
        codigo_unidade = '%05d' % codigo_protocolo
        if not codigo_protocolo:
            raise Exception(
                'Não foi possível obter o \'código do protocolo\', necessário para ' 'a geração do número do processo.')
        # Ano corrente.
        ano_corrente = datetime.today().year

        try:
            ultimo_processo_ano = Processo.objects.filter(numero_protocolo__startswith=codigo_unidade,
                                                          data_hora_criacao__year=ano_corrente).latest('id')
            # 23057.000001.2009-41
            proximo_id_processo = int(ultimo_processo_ano.numero_protocolo.split('.')[1]) + 1
        except Processo.DoesNotExist:
            # Ainda não existe nenhum processo no ano corrente
            proximo_id_processo = 1

        # Montando o número do processo.
        # Inicialmente o número do processo é montando formatado de maneira básica, somente com os
        # números. Os dígitos verificadores não estão presentes.
        # Ex: 040000014122000
        numero_protocolo = '%5d%06d%4d' % (codigo_protocolo, proximo_id_processo, ano_corrente)

        # Calculando o primeiro digito verificador.
        dv1 = (11 - (reduce(lambda x, y: x + y,
                            [int(numero_protocolo[::-1][x - 2]) * x for x in range(16, 1, -1)]) % 11)) % 10

        # Calculando o segundo digito verificador.
        numero_protocolo = numero_protocolo + str(dv1)
        dv2 = (11 - (reduce(lambda x, y: x + y,
                            [int(numero_protocolo[::-1][x - 2]) * x for x in range(17, 1, -1)]) % 11)) % 10

        # Número do processo completamente calculado e formatado.
        # Ex: 04000.001412/2000-26
        numero_protocolo = '%05d.%06d.%4d-%d%d' % (codigo_protocolo, proximo_id_processo, ano_corrente, dv1, dv2)
        return numero_protocolo

    def eh_publico(self):
        return self.nivel_acesso == Processo.NIVEL_ACESSO_PUBLICO

    def eh_restrito(self):
        return self.nivel_acesso == Processo.NIVEL_ACESSO_RESTRITO

    def eh_privado(self):
        return self.nivel_acesso == Processo.NIVEL_ACESSO_PRIVADO

    def eh_do_meu_setor(self, user):
        return self.setor_criacao == get_setor(user)

    def esta_nos_meus_setores(self, user):
        # return self.setor_atual in list(get_todos_setores(user))
        setores = Tramite.get_todos_setores(user, deve_poder_criar_processo=False)
        return self.setor_atual in list(setores)

    def esta_aguardando_ciencia(self):
        return self.status == ProcessoStatus.STATUS_AGUARDANDO_CIENCIA

    def esta_aguardando_juntada(self):
        return self.status == ProcessoStatus.STATUS_AGUARDANDO_JUNTADA

    def esta_em_homologacao_juntada(self):
        return self.status == ProcessoStatus.STATUS_EM_HOMOLOGACAO

    def esta_em_tramite_externo(self):
        return self.status == ProcessoStatus.STATUS_EM_TRAMITE_EXTERNO

    def esta_finalizado(self):
        return self.status == ProcessoStatus.STATUS_FINALIZADO

    def esta_anexado(self):
        return self.status == ProcessoStatus.STATUS_ANEXADO

    def esta_ativo(self):
        return self.status == ProcessoStatus.STATUS_ATIVO

    def tem_tramite(self):
        return self.tramites.exists()

    def tem_tramite_externo(self):
        return self.tramites.filter(tramite_barramento__isnull=False).exists()

    def tramitavel(self):
        return self.status == ProcessoStatus.STATUS_ATIVO

    def esta_na_caixa_entrada(self, setores=None, user=None, recebido=None):
        tramites = Tramite.get_caixa_entrada(setores, user)
        tramites = tramites.filter(processo=self)
        if recebido is not None:
            tramites = tramites.filter(data_hora_recebimento__isnull=not recebido)

        return tramites.exists()

    def esta_na_caixa_saida(self, setores=None, user=None):
        return Tramite.get_caixa_saida(setores, user).filter(processo=self).exists()

    def pode_realizar_upload(self, user=None):
        user = user or tl.get_user()
        vinculo = user.get_relacionamento()
        return vinculo and vinculo.papeis_ativos.exists()

    def possui_solicitacoes_juntada_documento(self):
        return SolicitacaoJuntada.objects.filter(tramite__processo=self).exists()

    def solicitacoes_juntada_documento(self):
        return SolicitacaoJuntada.objects.filter(tramite__processo=self)

    def pode_solicitar_ciencia(self, user=None):
        return not self.possui_solicitacoes_pendentes() and self.pode_editar(user)

    def get_responsavel_atual(self):
        ultimo_tramite = self.get_ultimo_tramite()
        if ultimo_tramite:
            return ultimo_tramite.pessoa_recebimento.pessoafisica
        else:
            return self.usuario_gerador.get_profile()

    def pode_dar_ciencia(self, user=None):
        # É necessário tomar cuidado para não dar ciência em documentos equivocadamente.
        # O SUAP não permite cancelar ou anular a ciência.
        # Apenas o solicitante pode dar ciencia em um processo
        user = user or tl.get_user()
        pessoa = user.get_profile()

        if SolicitacaoCiencia.objects.filter(solicitado=pessoa, status=CienciaStatus.STATUS_ESPERANDO, processo=self):
            return True

    def possui_ciencias_pendentes(self):
        return self.solicitacaociencia_set.filter(data_ciencia__isnull=True,
                                                  status=CienciaStatus.STATUS_ESPERANDO).exists()

    def solicitacoes_ciencias_pendentes(self):
        return self.solicitacaociencia_set.filter(data_ciencia__isnull=True, status=CienciaStatus.STATUS_ESPERANDO)

    def possui_solicitacoes_pendentes(self):
        if self.ultimo_tramite:
            return self.ultimo_tramite.possui_pedido_juntada_pendente()
        return None

    def possui_solicitacoes_pendentes_para(self, user=None):
        user = user or get_user()
        if self.ultimo_tramite:
            return self.ultimo_tramite.possui_pedido_juntada_pendente_para(user)
        return None

    def possui_pendencias_documentais(self):
        # Se existe alguma solicitação de despacho, o processo não pode ser encaminhado até a sua resolução
        # Se existe algum documento aguardando assinatura para ser anexado com tramite, o processo não pode
        # ser encaminhado
        """
        if (
                self.tem_solicitacoes_despacho_pendentes()
                or self.tem_solicitacoes_assinatura_com_tramite_pendentes()
                or self.possui_solicitacoes_pendentes()
                or self.tem_documentos_a_ser_anexado_aguardando_assinatura()
                or self.tem_solicitacoes_nivel_acesso_aberto()
        ):
        """

        # Foi tirado o trecho self.tem_solicitacoes_nivel_acesso_aberto() conforme documentado na issue 6086
        if (
                self.tem_solicitacoes_despacho_pendentes()
                or self.tem_solicitacoes_assinatura_com_tramite_pendentes()
                or self.possui_solicitacoes_pendentes()
                or self.tem_documentos_a_ser_anexado_aguardando_assinatura()
        ):
            return True
        else:
            return False

    def todas_solicitacoes_juntada_concluiram(self):
        pass

    def tem_solicitacoes_nivel_acesso_aberto(self):
        pred_list = [
            Q(processo=self),
            Q(documento_texto__in=self.get_documentos_texto_processo()),
            Q(documento_digitalizado__in=self.get_documentos_digitalizado_processo()),
        ]
        pred = reduce(operator.or_, pred_list) & Q(situacao=SolicitacaoAlteracaoNivelAcesso.SITUACAO_SOLICITADO)
        existe_solicitacoes = SolicitacaoAlteracaoNivelAcesso.objects.filter(pred).exists()
        return existe_solicitacoes

    def pode_ser_encaminhado(self, remetente_user=None):
        '''
        Um processo ativo só pode ser encaminhado nos seguintes casos:
        (1) Caso não existam trâmites e a pessoa quem criou é que está tentando tramitar ou o processo não é privado
        e o setor do processo faz parte do setores da pessoa.
        (2) Caso o processo tenha sido recebido e esteja na caixa de entrada da pessoa e/ou setor.
        (3) Existe alguma pendencia no processo: Se existe alguma solicitação de despacho, o processo não pode ser
            encaminhado até a sua resolução, se existe algum documento aguardando assinatura para ser anexado com
            tramite, o processo não pode ser encaminhado, se existe algum documento esperando para entrar no processo

        Obs: Essa análise é feita tanto para o processo em si como para os processos apensados, caso existam.

        :param remetente_setores setores que querem remeter o processo:
        :param remetente_pessoa pessoa que quer remeter o processo:
        :return: Booleano dizendo se o processo pode ser encaminhado ou não.
        '''
        processos = list()
        processos.append(self)
        processos.extend(self.get_processos_apensados())
        for p in processos:
            if not p.__pode_ser_encaminhado(remetente_user):
                return False

        return True

    def __pode_ser_encaminhado(self, remetente_user=None):
        """
        # Processo que não estão ativos, não podem ser encaminhados
        # Se o processo possui alguma pendência relativas a documentos que podem a vir fazer parte do processo,
        # tais pendencias impedem o tramite.
        if not processo.tramitavel() or processo.possui_pendencias_documentais():
            return False
        #
        user = get_user()
        remetente_user = remetente_user or user
        remetente_pessoa = remetente_user and remetente_user.get_profile() or user.get_profile()
        pode_tramitar = user.has_perm('processo_eletronico.pode_tramitar_processos_eletronicos')
        remetente_setores = Tramite.get_todos_setores(remetente_user)

        #
        if not processo.tem_tramite():
            print(u'>>> CASO 1 {} {} {}'.format(user, processo, processo.id))
            if (remetente_pessoa == processo.usuario_gerador.pessoafisica) or \
                    (pode_tramitar and not processo.eh_privado() and processo.setor_criacao in remetente_setores):
                return True
        elif pode_tramitar and processo.esta_na_caixa_entrada(setores=remetente_setores, user=remetente_user, recebido=True):
            return True
        elif (
            processo.interessados.filter(pk=remetente_pessoa.pk).exists()
            and remetente_user.get_vinculo().eh_servidor()
            and processo.esta_na_caixa_entrada(setores=[remetente_user.get_relacionamento().setor], recebido=True)
        ):
            return True
        elif pode_tramitar and processo.get_ultimo_tramite().eh_tramite_externo and processo.get_ultimo_tramite().tramite_barramento.estah_recusado:
            return True
        else:
            return False
        """

        # Processo que não estão ativos, não podem ser encaminhados
        # Se o processo possui alguma pendência relativas a documentos que podem a vir fazer parte do processo,
        # tais pendencias impedem o tramite.
        if not self.tramitavel() or self.possui_pendencias_documentais():
            return False

        remetente_user = remetente_user or get_user()
        remetente_pessoa_fisica = remetente_user.get_profile()
        remetente_setores = Tramite.get_todos_setores(remetente_user)
        remetente_vinculo = remetente_user.get_vinculo()

        if not self.tem_tramite():
            if (remetente_pessoa_fisica == self.usuario_gerador.pessoafisica) or (
                    not self.eh_privado() and self.setor_criacao in remetente_setores):
                return True

        if self.esta_na_caixa_entrada(setores=remetente_setores, user=remetente_user, recebido=True):
            return True

        # Permite editar o  processo com ultimo tramite externo  e  recusado
        if self.ultimo_tramite:
            if (
                    self.ultimo_tramite.eh_tramite_externo
                    and (self.ultimo_tramite.tramite_barramento.status == TramiteBarramento.STATUS_RECUSADO)
                    and (self.ultimo_tramite.remetente_setor in remetente_setores)
            ):
                return True

        if self.interessados.filter(
                pk=remetente_pessoa_fisica.pk).exists() and remetente_user.get_vinculo().eh_servidor():
            # Caso o user seja interessado no processo apenas o seu setor deve ser considerado na lista de setores a serem
            # verificados na caixa de entrada
            if remetente_vinculo.setor and self.esta_na_caixa_entrada(setores=[remetente_vinculo.setor], recebido=True):
                return True
            else:
                return False

        return False

    # TODO: Este método "pode_ler", apesar de existir, só estava sendo usado em um local. O método "verifica_pode_ver_processo",
    # que está presenta na camada de visão, estava sendo usado em 19 locais. Por preucaução, vou comentar este método
    # pode ler e criar um novo método, com o mesmo nome, só que usando o conteúdo de  "verifica_pode_ver_processo".
    # Implementação Antiga.
    # def pode_ler(self, user=None):
    #     user = user or tl.get_user()
    #     if self.eh_publico() or self.pode_editar():
    #         return True
    #     else:
    #         pessoa_logada = user.get_profile()
    #         if not self.tem_tramite() and pessoa_logada == self.usuario_gerador.pessoafisica:
    #             return True
    #         elif self.interessados.filter(pk=pessoa_logada.pk):
    #             return True
    #     return False

    # Implementação nova, com conteúdo do método "verifica_pode_ver_processo" que foi retirado do views.py.
    def pode_ler(self, user=None, lancar_excecao=False):

        # Utilizado quando existe usuario logado
        # ----------------------------------------
        user = user or tl.get_user()
        # Se existe algum despacho para ser dado no processo, então ele deve ser visto.
        solicitacao_despacho = SolicitacaoDespacho.objects.solicitacao_pendente(user.get_profile(), self.id)
        # Se não, verifica se o processo existe a minha lista de processos.
        processos = Processo.objects.by_user(user).filter(id=self.id)
        acesso_em_funcao_cargo = acesso_ao_processo_em_funcao_cargo(user, self)
        if not solicitacao_despacho.exists() and not processos.exists() and not acesso_em_funcao_cargo:
            if lancar_excecao:
                raise PermissionDenied()
            else:
                return False

        return True

    def pode_ler_consulta_publica(self):
        # Utilizado quando a consulta for pública realizada por "processo_eletronico/consulta_publica/"
        # Nesse tipo de consulta os processos são listados por esta view
        # As demandas 845 e 846 solicitaram que o processo fosse mostrado na íntegra mediante algumas regras
        # Para atender a essas demandas implementamos as seguintes regras
        # - Se o processo estiver vinculado a um "contratos.Contrato.processo"
        # - Considerando o tipo de processo veriricamos se o flag de "permite_visualizar_na_integra_publico" em "processo.TipoProcesso" estiver true
        # - Se o processo for público
        # ----------------------------------------

        # - Considerando a issue 5200 retiramos qualquer possibilidade de
        #   consulta a íntegra de processos pública
        if self.eh_publico():
            if self.tipo_processo.consulta_publica:
                return True
            Contrato = apps.get_model('contratos', 'Contrato')
            if Contrato and Contrato.objects.filter(processo__numero_processo_eletronico=self.numero_protocolo).exists():
                return True
        return False

    def clean(self):
        # TODO: Como Hipotese Legal está sendo usado em vários locais, ver uma forma de criar um método estático em
        # Hipótese Legal para realizar essa validação.
        if self.nivel_acesso in (Processo.NIVEL_ACESSO_PRIVADO, Processo.NIVEL_ACESSO_RESTRITO):
            hipoteses_legais_opcoes = None
            if self.nivel_acesso == Processo.NIVEL_ACESSO_PRIVADO:
                hipoteses_legais_opcoes = HipoteseLegal.objects.filter(nivel_acesso=NivelAcessoEnum.SIGILOSO.name)
            elif self.nivel_acesso == Processo.NIVEL_ACESSO_RESTRITO:
                hipoteses_legais_opcoes = HipoteseLegal.objects.filter(nivel_acesso=NivelAcessoEnum.RESTRITO.name)

            if hipoteses_legais_opcoes and not self.hipotese_legal:
                raise ValidationError({
                    'hipotese_legal': 'O nível de acesso "{}" exige que você defina uma hipótese legal.'.format(
                        self.get_nivel_acesso_display())})
        else:
            self.hipotese_legal = None

        if self.hipotese_legal and ((
            self.hipotese_legal.nivel_acesso == NivelAcessoEnum.SIGILOSO.name and self.nivel_acesso != Processo.NIVEL_ACESSO_PRIVADO) or (
            self.hipotese_legal.nivel_acesso == NivelAcessoEnum.RESTRITO.name and self.nivel_acesso != Processo.NIVEL_ACESSO_RESTRITO)
        ):
            raise ValidationError({
                'hipotese_legal': 'Escolha uma hipótese legal compatível com o nível de acesso "{}".'.format(
                    self.get_nivel_acesso_display())})

        super().clean()

    '''
        Só pode editar quem estiver com o processo e tenha a permissão pode_tramitar_processo
        Servidores Aposentados não podem editar
    '''

    def pode_editar(self, user=None):
        user = user or tl.get_user()
        if user.eh_servidor and user.get_relacionamento().eh_aposentado:
            return False
        return self.pode_ser_encaminhado(user)

    def pode_alterar_nivel_acesso(self, user=None):
        user = user or get_user()

        # Se for da gestão pode alterar sempre
        if user.groups.filter(name='Gestão Nível de Acesso dos Processos Documentos Eletrônicos').exists():
            return True

        # Processo não finalizado pode ser alterado por quem puder editar
        if self.pode_editar(user):
            return True

        # Processo finalizado pode ser alterado pelos seus interessados
        if self.esta_finalizado() and user.get_profile().pessoa_ptr in self.interessados.all():
            return True

        return False

    def pode_finalizar(self):
        # Só pode finalizar se não tiver nenhum documento pendente e pode editar o documento
        return not self.tem_documento_pendente() and self.pode_editar()

    def pode_desfinalizar(self, user):
        # Só pode desfinalizar se o processo estiver finalizado e o processo esteja na caixa de entrada do usuario
        # return self.esta_finalizado() and type(user.get_relacionamento()) == Servidor and \
        #       self.setor_atual in list(get_todos_setores(user))

        setores = Tramite.get_todos_setores(user, deve_poder_criar_processo=False)
        return self.esta_finalizado() and type(user.get_relacionamento()) == Servidor and self.setor_atual in list(
            setores)

    def pode_arquivar(self):
        return self.pode_editar() and not bool(self.get_apensamento())

    def pode_anexar(self, user):
        return not bool(self.get_apensamento()) and self.get_processos_podem_ser_anexados(user).exists()

    def pode_apensar(self, user):
        return self.get_processos_podem_ser_apensados(user).exists()

    def pode_ser_recebido(self, destinatario_setores=None, destinatario_user=None):
        """
        destinatario_user = destinatario_user or get_user()
        destinatario_pessoa = destinatario_user.get_profile()
        vinculo = destinatario_user.get_vinculo()
        relacionamento = destinatario_user.get_relacionamento()

        if destinatario_setores is None:
            destinatario_setores = Tramite.get_todos_setores(user=destinatario_user)

        if destinatario_user.has_perm('processo_eletronico.pode_tramitar_processos_eletronicos') and \
                self.esta_na_caixa_entrada(setores=destinatario_setores, user=destinatario_user, recebido=False):
            return True
        elif self.interessados.filter(pk=destinatario_pessoa.pk).exists() and vinculo.eh_servidor() and self.esta_na_caixa_entrada(setores=[relacionamento.setor], recebido=False):
            return True
        """

        destinatario_user = destinatario_user or get_user()
        vinculo_destinatario = destinatario_user.get_vinculo()
        destinatario_pessoa_fisica = destinatario_user.get_profile()

        if destinatario_setores is None:
            destinatario_setores = Tramite.get_todos_setores(user=destinatario_user)

        if self.esta_na_caixa_entrada(setores=destinatario_setores, user=destinatario_user, recebido=False):
            return True

        if self.interessados.filter(pk=destinatario_pessoa_fisica.id).exists() and vinculo_destinatario.eh_servidor():
            # Caso o user seja interessado apenas o seu setor sera considerado para ser buscado na caixa de entrada
            if vinculo_destinatario.setor and self.esta_na_caixa_entrada(setores=[vinculo_destinatario.setor],
                                                                         recebido=False):
                return True
            else:
                return False

        return False

    # demanda_495 - acompanhar processos publicos
    def pode_cadastrar_interesse(self, user=None):
        """Verifica se pode adicionar da lista de pessoas_acomapanhando_processo. É uma lista de pessoas que
         não estão cadastrados como interessados mas tem interesse em  acompanhar os andamentos (tramites)"""
        user = user or tl.get_user()
        return (
            self.eh_publico()
            and self.tramitavel()
            and not self.pessoas_acompanhando_processo.filter(pk=user.get_profile().pk).exists()
            and not self.interessados.filter(pk=user.get_profile().pk).exists()
        )

    def pode_remover_interesse(self, user=None):
        """Verifica se pode remover pessoa  da lista de pessoas_acomapanhando_processo."""
        user = user or tl.get_user()
        return self.eh_publico() and (
            self.tramitavel() or self.esta_finalizado()) and self.pessoas_acompanhando_processo.filter(
            pk=user.get_profile().pk).exists()

    def possui_solicitacao_juntada_pendente(self):
        if self.ultimo_tramite:
            return self.ultimo_tramite.possui_pedido_juntada_pendente()

    def tem_documento_pendente(self):
        doc_pendentes = DocumentoTextoProcesso.objects.filter(processo=self, data_hora_remocao__isnull=True).exclude(
            documento__status=DocumentoStatus.STATUS_FINALIZADO)
        return doc_pendentes.exists()

    def tem_documento_sigiloso(self):
        doc_sigilosos_doc_texto = DocumentoTextoProcesso.objects.filter(processo=self, data_hora_remocao__isnull=True,
                                                                        documento__nivel_acesso=Documento.NIVEL_ACESSO_SIGILOSO)
        doc_sigilosos_doc_digitalizado = DocumentoDigitalizadoProcesso.objects.filter(
            processo=self, data_hora_remocao__isnull=True, documento__nivel_acesso=Documento.NIVEL_ACESSO_SIGILOSO
        )
        return doc_sigilosos_doc_texto.exists() or doc_sigilosos_doc_digitalizado.exists()

    def ultimo_tramite_pode_ser_removido(self, lancar_excecao=False, setores=None, user=None):
        if self.esta_na_caixa_saida(setores=setores, user=user) and not self.get_ultimo_tramite().eh_tramite_externo:
            return True
        elif self.get_ultimo_tramite():
            if (
                    self.get_ultimo_tramite().eh_tramite_externo
                    and not self.get_ultimo_tramite().tramite_barramento.estah_recusado
                    and (
                    self.get_ultimo_tramite().tramite_barramento.foi_cancelado_automaticamente_pelo_barramento or not self.get_ultimo_tramite().tramite_barramento.foi_recebido_no_destino)
            ):
                return True

    @transaction.atomic()
    def remover_ultimo_tramite(self, setores=None, user=None):
        '''
        Remove o último trâmite do processo em si e dos processos apensados a ele, caso o mesmo encontra-se na caixa de
        saída dos setores e/ou pessoa em questão, caso contrário uma exceção será lançada.

         Obs: Essa análise é feita tanto para o processo em si como para os processos apensados, caso existam.

        :param setores setores nos quais o processo encontra-se na caixa de saída
        :param user pessoa com a qual o processo encontra-se na caixa de saída
        :raise Exception caso o processo não encontre-se na caixa de saída dos setores e/ou pesssoa em questão
        '''
        processos = list()
        processos.append(self)
        processos.extend(self.get_processos_apensados())

        for p in processos:
            p.__remover_ultimo_tramite(p, setores, user)

    @staticmethod
    def __remover_ultimo_tramite(processo, setores=None, user=None):
        if processo.ultimo_tramite_pode_ser_removido(lancar_excecao=True, setores=setores, user=user):
            # Desfazendo o vínculo @OneToOne entre trâmite e processo. A rotina abaixo evita o erro 'Processo matching
            # query does not exist.' e também garante que ao remover o trâmite o processo não seja também excluído por
            # cascata.
            tramite_a_ser_removido = processo.get_ultimo_tramite()
            processo.ultimo_tramite = None
            processo.save()

            # Cancela o  tramite externo para barramento ainda nao recebido
            if processo.get_ultimo_tramite().eh_tramite_externo and processo.ultimo_tramite_pode_ser_removido():
                TramiteBarramento = apps.get_model('conectagov_pen', 'TramiteBarramento')
                cancelamento_tramite = cancelar_tramite(tramite_a_ser_removido.tramite_barramento.id_tramite_barramento)
                if cancelamento_tramite['status_code'] == 200:
                    tramite_a_ser_removido.tramite_barramento.status = TramiteBarramento.STATUS_CANCELADO
                    tramite_a_ser_removido.tramite_barramento.save()
                    processo.colocar_em_tramite()
                    processo.save()

            # Nesta rotina o último trâmite é de fato removido do banco de dados, e o atributo "ultimo_tramite" de
            # processo é atualizado para apontar trâmite anterior ao que foi removido.
            tramite_a_ser_removido.delete()

            # if -  Remove o vinculo para retorno progrmado tendo em vista remoção do tramite solicitante
            # elif - Remove as informações da data de retorno e do tramite de retorno
            if tramite_a_ser_removido.eh_gerador_retorno_programado_pendente:
                TramiteRetornoProgramado.objects.get(tramite_gerador=tramite_a_ser_removido).delete()
            elif tramite_a_ser_removido.eh_resposta_retorno_programado:
                retorno_programado = TramiteRetornoProgramado.objects.get(
                    tramite_gerador=tramite_a_ser_removido.processo.ultimo_tramite, data_prevista_retorno__isnull=False)
                retorno_programado.data_efetiva_retorno = None
                retorno_programado.tramite_retorno = None
                retorno_programado.save()

    def get_ultimo_tramite(self):
        tramites_processo = self.tramites.all()
        if tramites_processo.exists():
            return tramites_processo.latest('data_hora_encaminhamento')
        return None

    def pode_solicitar_anexo(self, user):
        if self.ultimo_tramite:
            return self.ultimo_tramite.foi_recebido and self.pode_editar(user)
        return False

    def get_requerimento_processo(self, only_check_if_exists=False):
        tipo_documento_requerimento = TipoDocumento.objects.filter(nome="Requerimento").first()
        qs = self.documentodigitalizadoprocesso_set.filter(documento__arquivo__endswith='html',
                                                           documento__tipo=tipo_documento_requerimento,
                                                           data_hora_remocao__isnull=True)
        exists = qs.exists()

        if only_check_if_exists:
            return exists
        else:
            if exists:
                return qs[0]
            else:
                return None

    def has_requerimento_processo(self):
        return self.get_requerimento_processo(only_check_if_exists=True)

    def get_documentos_texto_processo(self):
        # Retorna todos os documentos de texto que não foram removidos do processo.
        ids = self.documentotextoprocesso_set.filter(data_hora_remocao__isnull=True).values_list('documento__id')
        documentos_textos = DocumentoTexto.objects.filter(id__in=ids)
        return documentos_textos

    def get_documentos_digitalizado_processo(self):
        # Retorna todos os documentos digitalizados que não foram removidos do processo.
        ids = self.documentodigitalizadoprocesso_set.filter(data_hora_remocao__isnull=True).values_list('documento__id')
        documentos_digitalizados = DocumentoDigitalizado.objects.filter(id__in=ids)
        return documentos_digitalizados

    def get_documentos_processo(self):
        documentos_textos = self.documentotextoprocesso_set.filter(data_hora_remocao__isnull=True)
        documentos_digitalizados = self.documentodigitalizadoprocesso_set.filter(data_hora_remocao__isnull=True)

        qs = QuerySetSequence(documentos_textos.all(), documentos_digitalizados.all())
        return qs.order_by('-data_hora_inclusao')

    def get_hashs_documentos_processo(self, use_sha256=False):
        hashs_documentos = list()
        for doc in self.get_documentos_processo():
            if use_sha256:
                hashs_documentos.append(doc.documento.hash_conteudo_as_sha256)
            else:
                hashs_documentos.append(doc.documento.hash_conteudo)
        return hashs_documentos

    def get_documentos_aguardando_assinatura_para_serem_anexados(self):
        qs = self.solicitacoes_assinatura_com_anexacao.filter(
            solicitacao_assinatura__status=SolicitacaoStatus.STATUS_ESPERANDO,
            solicitacao_assinatura__condicionantes__isnull=True
        )
        qs2 = []
        if self.solicitacoes_assinatura_com_anexacao.all():
            solicitacoes_pendentes = self.solicitacoes_assinatura_com_anexacao.all()[
                0].solicitacao_assinatura.get_solicitacoes_dependentes()
            if solicitacoes_pendentes:
                qs2 = solicitacoes_pendentes[0].condicionantes.all()

        if qs.exists() or qs2 is not None:
            documentos_ids = []
            if qs.exists():
                documentos_ids = qs.values_list('solicitacao_assinatura__documento__id', flat=True)
            else:
                if qs2:
                    solicit_anexacao = SolicitacaoAssinaturaComAnexacaoProcesso.objects.filter(
                        solicitacao_assinatura__id=qs2[0].id)
                    if solicit_anexacao[0].solicitacao_assinatura.documento.estah_aguardando_assinatura:
                        documentos_ids = solicit_anexacao.values_list('solicitacao_assinatura__documento__id',
                                                                      flat=True)
            return DocumentoTexto.objects.filter(pk__in=documentos_ids)

        return DocumentoTexto.objects.none()

    def get_documentos_aguardando_para_serem_anexados(self):
        if self.ultimo_tramite:
            return self.ultimo_tramite.pedido_juntada_documento_pendente()
        return SolicitacaoJuntadaDocumento.objects.none()

    def get_pareceres_simples(self):
        return ParecerSimples.objects.filter(processo_minuta__processo=self)

    @property
    def tem_documento_cancelado_ativo_no_processo(self):
        return self.documentotextoprocesso_set.filter(data_hora_remocao__isnull=True,
                                                      documento__status=DocumentoStatus.STATUS_CANCELADO).exists()

    def pode_atribuir_processo(self, user=None):
        if not user:
            user = tl.get_user()
        return setores_que_sou_chefe_ou_tenho_poder_de_chefe(user).filter(id=self.setor_atual_id).exists()

    @classmethod
    def listar_todos_documentos_processo(cls, processo, anexo=None):
        # Retorna todos os documentos que não foram removidos do processo além dos despachos.
        documentos_texto = processo.documentotextoprocesso_set.filter(data_hora_remocao__isnull=True).annotate(classe=models.Value('documento_texto'))
        documentos_digitalizados = processo.documentodigitalizadoprocesso_set.filter(data_hora_remocao__isnull=True).annotate(classe=models.Value('documento_digitalizado'))
        despachos = processo.tramites.filter(despacho_corpo__isnull=False).annotate(data_hora_inclusao=F('data_hora_encaminhamento')).annotate(classe=models.Value('despacho'))
        minutas = processo.get_minutas().annotate(classe=models.Value('minuta'))
        pareceres = processo.get_pareceres_simples().annotate(classe=models.Value('parecer'))

        processo_anexado = ''
        data_hora_anexado = ''
        if processo.status == ProcessoStatus.STATUS_ANEXADO:
            if not anexo:
                anexo = Anexacao.objects.filter(processo_anexado=processo).first()
            processo_anexado = str(anexo.processo_anexado)
            data_hora_anexado = anexo.data_hora_criacao

            documentos_texto = documentos_texto.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=Value(data_hora_anexado))
            documentos_digitalizados = documentos_digitalizados.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=Value(data_hora_anexado))
            despachos = despachos.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=Value(data_hora_anexado))
            minutas = minutas.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=Value(data_hora_anexado))
            pareceres = pareceres.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=Value(data_hora_anexado))
        else:
            documentos_texto = documentos_texto.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=F('data_hora_inclusao'))
            documentos_digitalizados = documentos_digitalizados.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=F('data_hora_inclusao'))
            despachos = despachos.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=F('data_hora_inclusao'))
            minutas = minutas.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=F('data_hora_inclusao'))
            pareceres = pareceres.annotate(processo_anexado=models.Value(processo_anexado), data_hora_anexado=F('data_hora_inclusao'))

        return (documentos_texto, documentos_digitalizados, despachos, minutas, pareceres)

    def get_todos_documentos_processo(self, reverse=True):
        lista_completa = Processo.listar_todos_documentos_processo(self)
        for anexo in self.get_anexos():
            lista_completa += Processo.listar_todos_documentos_processo(anexo.processo_anexado, anexo)
        # Ordenando tudo
        return sorted(chain(*lista_completa), key=operator.attrgetter('data_hora_anexado', 'data_hora_inclusao'), reverse=reverse)

    def get_documentos_removidos(self):
        # Retorna todos os documentos que não foram removidos do processo.
        qs = QuerySetSequence(
            self.documentotextoprocesso_set.filter(data_hora_remocao__isnull=False),
            self.documentodigitalizadoprocesso_set.filter(data_hora_remocao__isnull=False)
        )
        for anexo in self.get_anexos():
            qs = qs | QuerySetSequence(
                anexo.processo_anexado.documentotextoprocesso_set.filter(data_hora_remocao__isnull=False),
                anexo.processo_anexado.documentodigitalizadoprocesso_set.filter(data_hora_remocao__isnull=False)
            )
        return qs.order_by('-data_hora_remocao')

    def get_minutas(self):
        # Retorna todos as minutas que não foram removidos do processo.
        return self.processominuta_set.filter(data_hora_remocao__isnull=True)

    def get_minutas_removidas(self):
        # Retorna todos as minutas que não foram removidos do processo.
        return self.processominuta_set.filter(data_hora_remocao__isnull=False)

    def get_apensamento_processo(self):
        # Só pode ter um ativo
        return ApensamentoProcesso.objects.filter(processo=self, data_hora_remocao__isnull=True).last()

    def get_apensamento(self):
        # Só pode ter um ativo
        apensamento_processo = self.get_apensamento_processo()
        if apensamento_processo:
            return apensamento_processo.apensamento

        return None

    def get_processos_apensados(self):
        apensamento = self.get_apensamento()
        if not apensamento:
            return Processo.objects.none()

        processos_ids = apensamento.apensamentoprocesso_set.filter(data_hora_remocao__isnull=True).exclude(
            processo=self).values_list('processo', flat=True)
        return Processo.objects.filter(id__in=processos_ids)

    def get_todos_apensamentosprocessos(self):
        apensamentos = Apensamento.objects.filter(apensamentoprocesso__processo=self).filter(
            data_hora_remocao__isnull=False).all()
        return ApensamentoProcesso.objects.filter(apensamento__in=apensamentos).exclude(processo=self).order_by(
            'data_hora_criacao')

    def get_numero_protocolo_processos_apensados(self):
        return ', '.join(self.get_processos_apensados().values_list('numero_protocolo', flat=True))

    @transition(field=status, source=ProcessoStatus.STATUS_ATIVO, target=ProcessoStatus.STATUS_ANEXADO)
    def marcar_como_anexado(self):
        pass

    @transition(field=status, source=[ProcessoStatus.STATUS_ATIVO, ProcessoStatus.STATUS_AGUARDANDO_CIENCIA],
                target=ProcessoStatus.STATUS_AGUARDANDO_CIENCIA)
    def aguardar_ciencia(self):
        pass

    @transition(field=status, source=ProcessoStatus.STATUS_AGUARDANDO_CIENCIA, target=ProcessoStatus.STATUS_ATIVO)
    def informar_ciencia(self):
        pass

    @transition(field=status, source=[ProcessoStatus.STATUS_ATIVO, ProcessoStatus.STATUS_AGUARDANDO_JUNTADA],
                target=ProcessoStatus.STATUS_AGUARDANDO_JUNTADA)
    def aguardar_juntada_documento(self):
        pass

    @transition(field=status, source=ProcessoStatus.STATUS_AGUARDANDO_JUNTADA,
                target=ProcessoStatus.STATUS_EM_HOMOLOGACAO)
    def homologar_juntada_documento(self):
        pass

    @transition(field=status, source=ProcessoStatus.STATUS_AGUARDANDO_JUNTADA, target=ProcessoStatus.STATUS_ATIVO)
    def cancelar_juntada_documento(self):
        pass

    @transition(
        field=status,
        source=[ProcessoStatus.STATUS_AGUARDANDO_JUNTADA, ProcessoStatus.STATUS_EM_HOMOLOGACAO,
                ProcessoStatus.STATUS_FINALIZADO, ProcessoStatus.STATUS_EM_TRAMITE_EXTERNO],
        target=ProcessoStatus.STATUS_ATIVO,
    )
    def colocar_em_tramite(self):
        pass

    @transition(field=status, source=ProcessoStatus.STATUS_ATIVO, target=ProcessoStatus.STATUS_FINALIZADO)
    def finalizar_processo(self):
        pass

    @transition(field=status, source=ProcessoStatus.STATUS_FINALIZADO, target=ProcessoStatus.STATUS_ARQUIVADO)
    def arquivar_processo(self):
        pass

    @transition(field=status, source=ProcessoStatus.STATUS_ATIVO, target=ProcessoStatus.STATUS_EM_TRAMITE_EXTERNO)
    def colocar_em_tramite_externo(self):
        pass

    def get_processos_anexados(self):
        processos_anexados_ids = Anexacao.objects.filter(processo_anexador=self).values_list('processo_anexado_id',
                                                                                             flat=True)
        return Processo.objects.filter(id__in=processos_anexados_ids)

    def get_anexos(self):
        return Anexacao.objects.filter(processo_anexador=self)

    @transaction.atomic()
    def apensar_processos(self, processos_a_apensar, justificativa, request):
        apensamento = self.get_apensamento()
        resgistrar_acao_processo = False
        if not apensamento:
            apensamento = Apensamento.objects.create(justificativa_criacao=justificativa)
            apensamento.apensar_processo(self, justificativa)
            resgistrar_acao_processo = True

        for processo_a_apensar in processos_a_apensar:
            apensamento.apensar_processo(processo_a_apensar, justificativa)

        # Registra a açao de apensamento
        if resgistrar_acao_processo:
            RegistroAcaoProcesso.criar(
                RegistroAcaoProcesso.TIPO_APENSACAO, self, request,
                'Processo apensado ao(s) processo(s) {}'.format(self.get_numero_protocolo_processos_apensados())
            )

        for processo_a_apensar in processos_a_apensar:
            RegistroAcaoProcesso.criar(
                RegistroAcaoProcesso.TIPO_APENSACAO,
                processo_a_apensar,
                request,
                'Processo apensado ao(s) processo(s) {}'.format(
                    processo_a_apensar.get_numero_protocolo_processos_apensados()),
            )

    @transaction.atomic()
    def desapensar_processo(self, justificativa, request):
        apensamento_processo = self.get_apensamento_processo()
        if apensamento_processo:
            outros_apensamentos_processos = apensamento_processo.apensamento.apensamentoprocesso_set.filter(
                data_hora_remocao__isnull=True).exclude(processo_id=self.id)
            # Se so tiver mais um processo apensado finaliza a apensação
            if outros_apensamentos_processos.count() == 1:
                apensamento_processo.apensamento.finalizar(justificativa, request)
            else:
                apensamento_processo.finalizar(justificativa, request)

    @transaction.atomic
    def anexar(self, processo_a_anexar, user, justificativa):
        processo_a_anexar.marcar_como_anexado()
        processo_a_anexar.save()
        anexacao = Anexacao(processo_anexador=self, processo_anexado=processo_a_anexar)
        anexacao.save()

    def get_processos_podem_ser_anexados(self, user):
        # Processos que o usuário pode ver
        processos = Processo.ativos.by_user(user)
        # Exclui os processos que já estão anexados e o próprio processo anexador
        processos_que_podem_ser_anexados = processos.exclude(status=ProcessoStatus.STATUS_ANEXADO).exclude(id=self.id)
        # Exclui processos mais novos que o processo anexador
        processos_que_podem_ser_anexados = processos_que_podem_ser_anexados.exclude(
            data_hora_criacao__lt=self.data_hora_criacao)
        # pegando os processos que tem os mesmo interessados, só que pode ter os mesmo mais alguns
        for interessado in self.interessados.all():
            processos_que_podem_ser_anexados = processos_que_podem_ser_anexados.filter(interessados=interessado)

        # Retirar os processos que tem quantidades de interessados diferentes do processo anexador para
        # garantir que sejam os mesmos
        # Necessário para remover os subconjuntos
        ids = processos_que_podem_ser_anexados.values_list('id', flat=True)
        processos_que_podem_ser_anexados = Processo.objects.filter(id__in=ids).annotate(
            qtd=Count('interessados')).filter(qtd=self.interessados.count())
        # Retirar os processos que tem quantidades de classificações diferentes do processo anexador para
        # garantir que sejam os mesmos
        # Necessário para remover os subconjuntos
        ids = processos_que_podem_ser_anexados.values_list('id', flat=True)
        processos_que_podem_ser_anexados = (
            Processo.objects.filter(id__in=ids).annotate(qtd=Count('tipo_processo__classificacoes')).filter(
                qtd=self.tipo_processo.classificacoes.count())
        )

        # remoçao de processos com apensamentos vigentes
        processos_que_podem_ser_anexados.exclude(apensamentoprocesso__data_hora_remocao__isnull=True,
                                                 apensamentoprocesso__data_hora_criacao__lte=datetime.now())

        # processos sigilosos só podem ser anexados a processos sigilosos
        if self.nivel_acesso == Processo.NIVEL_ACESSO_PRIVADO:
            processos_que_podem_ser_anexados = processos_que_podem_ser_anexados.filter(
                nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO)
        else:
            processos_que_podem_ser_anexados = processos_que_podem_ser_anexados.exclude(
                nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO)

        return processos_que_podem_ser_anexados

    def get_processos_podem_ser_apensados(self, user):
        processos = Processo.ativos.by_user(user)
        # Exclui os processos que já estão apensados e o próprio processo apensador
        processos_que_podem_ser_apensados = processos.exclude(status=ProcessoStatus.STATUS_ANEXADO).exclude(id=self.id)
        processos_que_podem_ser_apensados = processos_que_podem_ser_apensados.exclude(apensamentoprocesso__isnull=False,
                                                                                      apensamentoprocesso__data_hora_remocao__isnull=True)

        if self.nivel_acesso == Processo.NIVEL_ACESSO_PRIVADO:
            processos_que_podem_ser_apensados = processos_que_podem_ser_apensados.filter(
                nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO)
        else:
            processos_que_podem_ser_apensados = processos_que_podem_ser_apensados.exclude(
                nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO)

        return processos_que_podem_ser_apensados

    def get_ext_combo_template(self):
        out = ['%s' % (self)]
        if self.interessados.exists():
            out.append('<span class="cinza"><strong>Interessados:</strong> %s</span>' % ', '.join(
                self.interessados.values_list('nome', flat=True)))
        else:
            out.append('<span class="false">Não possui pessoa interessada</span>')

        if not hasattr(self, 'assunto'):
            out.append('<span class="false">Não possui assunto</span>')
        else:
            out.append('<span class="cinza"><strong>Assunto:</strong> %s</span>' % self.assunto)

        if self.get_processos_apensados().exists():
            out.append('<span class="cinza"><strong>Processos apensados:</strong> %s</span>' % ', '.join(
                self.get_processos_apensados().values_list('numero_protocolo', flat=True)))

        template = '''
        <div style="overflow: hidden">
            <div style="float: left">
                {}
            </div>
        </div>
        '''.format(
            '<br/>'.join(out)
        )
        return template

    def solicitacoes_ciencia(self):
        return self.solicitacaociencia_set.filter()

    def get_ciencia_pendente(self, user):
        return self.solicitacaociencia_set.filter(solicitado=user, status=CienciaStatus.STATUS_ESPERANDO).first()
        # data_ciencia__isnull=True, data_limite_ciencia__date__gte=today).first()

    def get_solicitacao_de_juntada(self, user):
        user = user or tl.get_user()
        today = get_datetime_now().today()
        return self.solicitacaociencia_set.filter(solicitado=user.get_profile(), data_ciencia__isnull=False,
                                                  data_limite_juntada__date__gte=today).first()

    def existe_ciencias_pendentes(self, user=None):
        user = user or tl.get_user()
        today = get_datetime_now().today()
        qs = self.solicitacaociencia_set.filter(data_ciencia__isnull=True, data_limite_ciencia__date__gte=today)
        qs = qs.filter(solicitado=user.get_profile()) if user else qs
        return qs.exists()

    def pode_solicitar_juntada_documento(self, user=None):
        if self.ultimo_tramite and self.ultimo_tramite.foi_recebido:
            return self.pode_editar(user)
        return False

    @transaction.atomic()
    def adicionar_documento_texto(self, documento, registro_acao_observacao=None):
        msg_erro = 'O documento não pode ser adicionado {0}'
        from documento_eletronico.models import DocumentoTexto
        #
        if not isinstance(documento, DocumentoTexto):
            raise ProcessoEletronicoException(msg_erro.format('porque seu tipo é incompatível.'))
        # Rever essa regra após o advendo da SolicitacaoAssinaturaComAnexacaoProcesso.
        if self.get_apensamento() and documento.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
            raise ProcessoEletronicoException(msg_erro.format('porque o processo tem apensamentos e o documento é sigiloso.'))
        #
        if not documento.estah_finalizado:
            raise ProcessoEletronicoException(msg_erro.format('porque ele não está finalizado.'))
        #
        documento_processo = DocumentoTextoProcesso(processo=self, documento=documento)
        documento_processo.save()
        #
        RegistroAcaoDocumentoTexto.objects.create(
            tipo=RegistroAcaoDocumento.TIPO_ADICAO_EM_PROCESSO,
            documento=documento,
            ip=tl.get_request().META['REMOTE_ADDR'],
            observacao=registro_acao_observacao or ('Documento adicionado ao processo {}.'.format(self)),
        )

    @transaction.atomic()
    def adicionar_documento_digitalizado(self, documento, usuario=None, pessoas_compartilhadas=None):
        # Adicionando o documento ao processo
        msg_erro = 'O documento não pode ser adicionado {0}'
        from documento_eletronico.models import DocumentoDigitalizado
        if not isinstance(documento, DocumentoDigitalizado):
            raise Exception(msg_erro.format('porque ele tem que ser do tipo DocumentoDigitalizado.'))

        documento_digitalizado_processo, created = DocumentoDigitalizadoProcesso.objects.get_or_create(processo=self,
                                                                                                       documento=documento)
        if documento.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
            if not pessoas_compartilhadas and usuario:
                raise ValidationError(
                    "É necessário informar os parâmetros usuário e pessoas compartilhadas para documentos sigilosos.")
            CompartilhamentoDocumentoDigitalizadoPessoa.objects.filter(documento=documento).delete()
            for pessoa in pessoas_compartilhadas:
                compartilhamento = CompartilhamentoDocumentoDigitalizadoPessoa()
                compartilhamento.documento = documento
                compartilhamento.pessoa_permitida = pessoa
                compartilhamento.data_criacao = datetime.now()
                compartilhamento.usuario_criacao = usuario
                compartilhamento.save()
        return documento_digitalizado_processo

    def solicitacoes_despacho(self):
        return self.solicitacaodespacho_set.all()

    def tem_solicitacoes_despacho_pendentes(self):
        return self.solicitacoes_despacho().filter(status=SolicitacaoStatus.STATUS_ESPERANDO).exists()

    def despachos(self):
        return self.tramites.filter(assinaturatramite__isnull=False)

    def adicionar_relacionamento(self, processo, symm=True):
        relationship, _ = ProcessosRelacionados.objects.update_or_create(processo_origem=self, processo_alvo=processo)
        if symm:
            # avoid recursion by passing `symm=False`
            processo.adicionar_relacionamento(self, False)
        return relationship

    def remover_relacionamento(self, processo, symm=True):
        ProcessosRelacionados.objects.filter(processo_origem=self, processo_alvo=processo).delete()
        if symm:
            # avoid recursion by passing `symm=False`
            processo.remover_relacionamento(self, False)

    def get_relacionamentos(self):
        return self.processos_relacionados.filter(relacionado_com__processo_origem=self)

    def get_relacionado_a(self):
        return self.relacionamentos.filter(relacionado_a__processo_alvo=self)

    def tem_solicitacoes_assinatura_com_tramite_pendentes(self):
        return self.solicitacoes_assinatura_com_anexacao.filter(
            solicitacao_assinatura__status=SolicitacaoStatus.STATUS_ESPERANDO, destinatario_setor_tramite__isnull=False
        ).exists()

    def tem_documentos_a_ser_anexado_aguardando_assinatura(self):
        tem_doc_a_ser_anexado = False
        for sol in self.solicitacoes_assinatura_com_anexacao.filter(
                solicitacao_assinatura__status__in=[SolicitacaoStatus.STATUS_DEFERIDA,
                                                    SolicitacaoStatus.STATUS_ESPERANDO],
                destinatario_setor_tramite__isnull=True
        ):
            if sol.solicitacao_assinatura.documento.estah_aguardando_assinatura:
                tem_doc_a_ser_anexado = True

        return tem_doc_a_ser_anexado

    @staticmethod
    @transaction.atomic()
    def criar(tipo_processo, assunto, interessados, nivel_acesso=None, hipotese_legal=None):
        """

        :param tipo_processo: TipoProcesso instance
        :param assunto: Assunto do Processo
        :param interessados:  Lista de Pessoa instance
        :return: Processo instance
        """
        if not nivel_acesso:
            nivel_acesso = tipo_processo.nivel_acesso_default
        processo = Processo(
            tipo_processo=tipo_processo,
            assunto=assunto,
            nivel_acesso=nivel_acesso,
            hipotese_legal=hipotese_legal
        )
        processo.clean()
        processo.save()

        for interessado in interessados:
            if not isinstance(interessado, Pessoa):
                raise Exception(
                    "O interessado do processo deve ser do tipo Pessoa ou seus descendentes (PessoaFisica, PessoaJuridica).")
            processo.interessados.add(interessado)

        processo.clean()
        processo.save()
        processo.verificar_criacao_processo()
        return processo

    @staticmethod
    @transaction.atomic()
    def cadastrar_processo(user, processo_tramite, papel, documentos_texto=None, documentos_digitalizados=None,
                           interessados=None, setor_processo=None):
        """
            Este método cria um processo a partir de:
                1. :param user
                    - request.user
                2. :param processo_tramite
                    - Dicionário com os dados básicos do processo e seu tramite
                        - tipo_processo: obj TipoProcesso
                        - assunto: char com descricao livre da solicitacao
                        - setor_destino:
                            - Setor do primeiro trâmite do processo
                            - obj 'rh.Setor'
                3. :param papel
                    - obj Papel com um dos papeis ativos do usuario (user.get_relacionamento().papeis_ativos)
                4. :param documentos_texto
                    - Lista de objs DocumentoTexto
                5. :param documentos_digitalizados
                    - Lista de dicionarios contendo os dados de um documento para fazer upload
                        - identificador_numero: PositiveIntegerField blank=True null=True
                        - identificador_ano: blank=True null=True
                        - identificador_setor_sigla: CharFieldPlus max_length=100 blank=True null=True
                        - identificador_tipo_documento_sigla: CharFieldPlus max_length=50 blank=True null=True
                        - tipo: obj 'documento_eletronico.TipoDocumento'
                        - tipo_conferencia: obj TipoConferencia
                        - assunto: Char
                        - nivel_acesso: Documento.NIVEL_ACESSO_CHOICES
                        - arquivo
                6 :param interessados
                        - List of PessoaFisica

        """
        # Parametros obrigatorios, inclusive os itens dos dicionarios e seus tipos
        if not user or not processo_tramite or not papel:
            return None
        if 'tipo_processo' not in processo_tramite or 'assunto' not in processo_tramite or 'setor_destino' not in processo_tramite:
            return None
        for dg in documentos_digitalizados:
            if not dg['tipo'] or not dg['tipo_conferencia'] or not dg['assunto'] or not dg['nivel_acesso']:
                return None
            if not type(dg['tipo']) is TipoDocumento or not type(dg['tipo_conferencia']) is TipoConferencia:
                return None
            if not dg['nivel_acesso'] in (
                    DocumentoDigitalizado.NIVEL_ACESSO_SIGILOSO, DocumentoDigitalizado.NIVEL_ACESSO_RESTRITO,
                    DocumentoDigitalizado.NIVEL_ACESSO_PUBLICO):
                return None

        setor_processo = setor_processo or get_setor(user)
        processo = Processo.objects.create(
            tipo_processo=processo_tramite['tipo_processo'],
            assunto=processo_tramite['assunto'],
            nivel_acesso=processo_tramite['tipo_processo'].nivel_acesso_default,
            setor_criacao=setor_processo,
        )
        if interessados:
            for interessado in interessados:
                processo.interessados.add(interessado)
            processo.save()
        else:
            processo.interessados.add(user.pessoafisica)
            processo.save()

        processo.verificar_criacao_processo()
        tramite_novo = Tramite()
        tramite_novo.processo = processo
        tramite_novo.tramitar_processo(
            remetente_setor=setor_processo,
            remetente_pessoa=user.pessoafisica,
            destinatario_setor=processo_tramite['setor_destino'],
            papel=papel,
            despacho_corpo=None,
            destinatario_pessoa=None,
            assinar_tramite=False,
        )

        for dt in documentos_texto:
            obj_dt = DocumentoTexto.objects.get(id=dt)
            processo.adicionar_documento_texto(obj_dt)

        for dg in documentos_digitalizados:
            documento = DocumentoDigitalizado()
            documento.identificador_numero = dg.get('identificador_numero', None)
            documento.identificador_ano = dg.get('identificador_ano', None)
            documento.identificador_setor_sigla = dg.get('identificador_setor_sigla', None)
            documento.identificador_tipo_documento_sigla = dg.get('identificador_tipo_documento_sigla', None)

            documento.tipo = dg['tipo']
            documento.tipo_conferencia = dg['tipo_conferencia']
            documento.assunto = dg['assunto']
            documento.nivel_acesso = dg['nivel_acesso']

            documento.usuario_criacao = user
            documento.usuario_ultima_modificacao = user
            documento.setor_dono = setor_processo
            documento.identificador_setor_sigla = setor_processo.sigla if setor_processo else ''

            documento.interno = True
            documento.data_emissao = datetime.now()
            documento.data_criacao = datetime.now()
            documento.data_ultima_modificacao = datetime.now()

            documento.arquivo.save(dg['arquivo'].name, dg['arquivo'])
            documento.save()
            documento.assinar_via_senha(user, papel)
            dg['arquivo'].close()

            DocumentoDigitalizadoProcesso.objects.create(processo=processo, documento=documento)

        return processo

    @staticmethod
    @transaction.atomic()
    def adicionar_documentos_processo(processo, user, papel, documentos_texto=None, documentos_digitalizados=None,
                                      setor_processo=None):
        """
            Este método cria um processo a partir de:
                1. :param processo
                    - instancia de um processo eletrônico
                2. :param user
                    - request.user
                3. :param papel
                    - obj Papel com um dos papeis ativos do usuario (user.get_relacionamento().papeis_ativos)
                4. :param documentos_texto
                    - Lista de objs DocumentoTexto
                5. :param documentos_digitalizados
                    - Lista de dicionarios contendo os dados de um documento para fazer upload
                        - identificador_numero: PositiveIntegerField blank=True null=True
                        - identificador_ano: blank=True null=True
                        - identificador_setor_sigla: CharFieldPlus max_length=100 blank=True null=True
                        - identificador_tipo_documento_sigla: CharFieldPlus max_length=50 blank=True null=True
                        - tipo: obj 'documento_eletronico.TipoDocumento'
                        - tipo_conferencia: obj TipoConferencia
                        - assunto: Char
                        - nivel_acesso: Documento.NIVEL_ACESSO_CHOICES
                        - arquivo

        """
        for dt in documentos_texto:
            obj_dt = DocumentoTexto.objects.get(id=dt)
            processo.adicionar_documento_texto(obj_dt)

        setor_processo = setor_processo or get_setor(user)

        for dg in documentos_digitalizados:
            documento = DocumentoDigitalizado()
            documento.identificador_numero = dg.get('identificador_numero', None)
            documento.identificador_ano = dg.get('identificador_ano', None)
            documento.identificador_setor_sigla = dg.get('identificador_setor_sigla', None)
            documento.identificador_tipo_documento_sigla = dg.get('identificador_tipo_documento_sigla', None)

            documento.tipo = dg['tipo']
            documento.tipo_conferencia = dg['tipo_conferencia']
            documento.assunto = dg['assunto']
            documento.nivel_acesso = dg['nivel_acesso']

            documento.usuario_criacao = user
            documento.usuario_ultima_modificacao = user
            documento.setor_dono = setor_processo
            documento.identificador_setor_sigla = setor_processo.sigla if setor_processo else ''

            documento.interno = True
            documento.data_emissao = datetime.now()
            documento.data_criacao = datetime.now()
            documento.data_ultima_modificacao = datetime.now()

            documento.arquivo.save(dg['arquivo'].name, dg['arquivo'])
            documento.save()
            documento.assinar_via_senha(user, papel)
            dg['arquivo'].close()

            DocumentoDigitalizadoProcesso.objects.create(processo=processo, documento=documento)

        return processo

    @transaction.atomic()
    def alterar_nivel_acesso(self, novo_nivel_acesso, nova_hipotese_legal, user, ip, destinatario_setor=None, justificativa=None):
        #
        if not self.pode_alterar_nivel_acesso(user):
            raise Exception(f'Esse processo não pode ser alterado por {user.get_profile()}.')

        de = Processo.NIVEL_ACESSO_CHOICES[self.nivel_acesso - 1][1]
        para = Processo.NIVEL_ACESSO_CHOICES[novo_nivel_acesso - 1][1]

        if self.nivel_acesso == novo_nivel_acesso:
            raise Exception(f'Impossível alterar o nível de acesso de {de} para {para}.')
        #
        if destinatario_setor:
            if not destinatario_setor in get_todos_setores(user):
                raise Exception(f'O setor de destino deve ser um dos setores do usuário {user.get_profile()}.')

        obs = f'Alterou o nível de acesso de {de} para {para} mediante justificativa: {justificativa}'
        tipo = RegistroAcaoProcesso.TIPO_EDICAO_NIVEL_ACESSO

        """

         NIVEL_ACESSO_PUBLICO = 1
         NIVEL_ACESSO_RESTRITO = 2
         NIVEL_ACESSO_PRIVADO = 3

         * So tera 'papel' quando for para assinar a mudanca de nivel de acesso na nova implementacao

         Principais regras para gerar tramite após a alteração de Nível de Acesso:
           1 - Se nível de acesso tiver for alterado de PÚBLICO OU RESTRITO para PRIVADO
               - O processo deverá tramitar para o usuário
               - Será gerado um outro trâmite para esse usuário
               - Gera tramite para não deixar que o processo trave após mudanca de PRIVADO para outro nível de acesso

           2 - Se nível de acesso tiver for alterado de PRIVADO para PÚBLICO OU RESTRITO
               - O processo deverá tramitar o setor do usuário
               - Será gerado um outro trâmite para esse setor
               - Gera tramite para não deixar que o processo trave após mudanca de PRIVADO para outro nível de acesso

           3 - Qualquer outra opção não gera tramite

        """

        if self.nivel_acesso in [Processo.NIVEL_ACESSO_PUBLICO,
                                 Processo.NIVEL_ACESSO_RESTRITO] and novo_nivel_acesso == Processo.NIVEL_ACESSO_PRIVADO:
            # Regra 1

            self.hipotese_legal = nova_hipotese_legal
            self.nivel_acesso = novo_nivel_acesso
            self.clean()
            self.save()

            tramite_novo = Tramite()
            tramite_novo.processo = self

            tramite_novo.tramitar_processo(
                remetente_pessoa=user.get_profile(),
                remetente_setor=get_setor(user),
                despacho_corpo=None,
                destinatario_pessoa=user.get_profile().pessoa_ptr,
                destinatario_setor=None,
                assinar_tramite=False,
                papel=None,
            )

            tramite_novo.receber_processo(pessoa_recebimento=user.get_profile(), data_hora_recebimento=datetime.today())
            RegistroAcaoProcesso.objects.create(processo=self, tipo=tipo, ip=ip, observacao=obs)

        elif self.nivel_acesso == Processo.NIVEL_ACESSO_PRIVADO and novo_nivel_acesso in [
                Processo.NIVEL_ACESSO_PUBLICO, Processo.NIVEL_ACESSO_RESTRITO]:
            # Regra 2

            if destinatario_setor is None:
                raise Exception('O setor de destino deve ser informado e deve ser um dos setores do usuário {}.'.format(
                    user.get_profile()))

            self.hipotese_legal = nova_hipotese_legal
            self.nivel_acesso = novo_nivel_acesso
            self.clean()
            self.save()

            tramite_novo = Tramite()
            tramite_novo.processo = self

            tramite_novo.tramitar_processo(
                remetente_pessoa=user.get_profile(),
                remetente_setor=get_setor(user),
                despacho_corpo=None,
                destinatario_pessoa=None,
                destinatario_setor=destinatario_setor,
                assinar_tramite=False,
                papel=None,
            )

            tramite_novo.receber_processo(pessoa_recebimento=user.get_profile(), data_hora_recebimento=datetime.today())
            RegistroAcaoProcesso.objects.create(processo=self, tipo=tipo, ip=ip, observacao=obs)
        else:
            # Regra 3

            self.hipotese_legal = nova_hipotese_legal
            self.nivel_acesso = novo_nivel_acesso
            self.clean()
            self.save()

            RegistroAcaoProcesso.objects.create(processo=self, tipo=tipo, ip=ip, observacao=obs)

        return None

    # ==================================================================================================================
    # PERMISSÕES DO PROCESSO E DOCUMENTO ELETRÔNICO
    # Essa rotina irah retornar todos os setores aos quais o usuário logado estah habilitado a trabalhar
    # ==================================================================================================================
    @staticmethod
    def setores_que_posso_trabalhar_nos_processos(nivel_permissao, user):

        # >>> Processo.PERMISSAO_OPERAR_PROCESSO:
        # Equivalente ao grupo "Tramitador de Processos Eletrônicos"
        #   permission "pode_tramitar_processos_eletronicos"
        # Serah chamado pelo Tramite.get_todos_setores(user, deve_poder_criar_processo=False)

        # >>> Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO:
        # Equivalente ao grupo "Operador de Processo Eletrônico"
        # Serah chamado pelo Tramite.get_todos_setores(user, deve_poder_criar_processo=True)

        pessoa = user.get_profile()

        if not user.is_authenticated or user.eh_aluno or not [True for s in Processo.PERMISSAO_PROCESSO_CHOICES if
                                                              s[0] == nivel_permissao] or not pessoa:
            return Setor.objects.none()
        #
        setores_compartilhados_qs = Subquery(
            CompartilhamentoProcessoEletronicoSetorPessoa.objects.filter(
                nivel_permissao=nivel_permissao, pessoa_permitida=pessoa
            ).values('setor_dono_id')
        )
        setores_compartilhados_com_pessoa = Setor.objects.filter(pk__in=setores_compartilhados_qs).distinct()
        setores_chefiados = setores_que_sou_chefe_ou_tenho_poder_de_chefe(user)
        return (setores_chefiados | setores_compartilhados_com_pessoa).distinct()

    @staticmethod
    def sincronizar_permissoes_processo_documento(user):

        # >>> Processo.PERMISSAO_OPERAR_PROCESSO:
        # >>> Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO:
        eh_tramitador = in_group(user, 'Tramitador de Processos Eletrônicos')
        eh_operador = in_group(user, 'Operador de Processo Eletrônico')
        if not eh_tramitador and Processo.setores_que_posso_trabalhar_nos_processos(Processo.PERMISSAO_OPERAR_PROCESSO, user).exists():
            grupo = Group.objects.get(name='Tramitador de Processos Eletrônicos')
            grupo.user_set.add(user)

        if not eh_operador and Processo.setores_que_posso_trabalhar_nos_processos(Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO, user).exists():
            grupo = Group.objects.get(name='Operador de Processo Eletrônico')
            grupo.user_set.add(user)

    # ==================================================================================================================
    # PERMISSÕES DO PROCESSO E DOCUMENTO ELETRÔNICO
    # Essas rotinas irão atualizar os setores aos quais o usuário logado estah habilitado a trabalhar ou tenha poder de chefe
    # ==================================================================================================================

    @staticmethod
    def atualizar_compartilhamentos__pessoa(permissao, usuario_criacao, setor_dono, pessoa_compartilhamento):
        # =====================================
        # Atualiza PESSOAS que podem OPERAR processos em um setor
        # =====================================

        if not [True for s in Processo.PERMISSAO_PROCESSO_CHOICES if s[0] == permissao]:
            return False

        CompartilhamentoProcessoEletronicoSetorPessoa.objects.filter(setor_dono=setor_dono,
                                                                     nivel_permissao=permissao).delete()

        for po in pessoa_compartilhamento:
            c = CompartilhamentoProcessoEletronicoSetorPessoa()
            c.setor_dono = setor_dono
            c.pessoa_permitida = po
            c.nivel_permissao = permissao
            c.data_criacao = datetime.today()
            c.usuario_criacao = usuario_criacao
            c.save()
        return True

    @staticmethod
    def atualizar_compartilhamentos__setor(permissao, usuario_criacao, setor_dono, setor_compartilhamento):
        # =====================================
        # Atualiza PESSOAS que podem OPERAR E CRIAR processos em um setor
        # =====================================

        if not [True for s in Processo.PERMISSAO_PROCESSO_CHOICES if s[0] == permissao]:
            return False

        for setor in setor_compartilhamento:
            for servidor in setor.get_servidores():
                c = CompartilhamentoProcessoEletronicoSetorPessoa()
                c.pessoa_permitida = servidor
                c.setor_dono = setor_dono
                c.nivel_permissao = permissao
                c.data_criacao = datetime.today()
                c.usuario_criacao = usuario_criacao
                c.save()
        return True

    @staticmethod
    def atualizar_compartilhamentos__setor_poder_chefe(usuario_criacao, setor_dono, pessoas_poder_de_chefe):
        # =====================================
        # Atualiza PESSOAS que possuem PODER DE CHEFE para processos em um setor
        # =====================================
        CompartilhamentoProcessoEletronicoPoderDeChefe.objects.filter(setor_dono=setor_dono, de_oficio=False).delete()

        for po in pessoas_poder_de_chefe:
            CompartilhamentoProcessoEletronicoPoderDeChefe.objects.get_or_create(setor_dono=setor_dono, pessoa_permitida=po,
                                                                                 defaults={'data_criacao': datetime.today(), 'usuario_criacao': usuario_criacao})
        return True

    @staticmethod
    @transaction.atomic()
    def atualizar_compartilhamentos(usuario_criacao, setor_dono, setor_operar, setor_operar_criar, pessoa_operar,
                                    pessoa_operar_criar, pessoa_retorno_programado):

        Processo.atualizar_compartilhamentos__pessoa(Processo.PERMISSAO_OPERAR_PROCESSO, usuario_criacao, setor_dono,
                                                     pessoa_operar)
        Processo.atualizar_compartilhamentos__pessoa(Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO, usuario_criacao,
                                                     setor_dono, pessoa_operar_criar)
        Processo.atualizar_compartilhamentos__pessoa(Processo.PERMISSAO_RETORNO_PROGRAMADO, usuario_criacao, setor_dono,
                                                     pessoa_retorno_programado)
        Processo.atualizar_compartilhamentos__setor(Processo.PERMISSAO_OPERAR_PROCESSO, usuario_criacao, setor_dono,
                                                    setor_operar)
        Processo.atualizar_compartilhamentos__setor(Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO, usuario_criacao,
                                                    setor_dono, setor_operar_criar)

        return True

    def get_metadados(self):
        metadados_processo = {}
        metadados_processo['total_em_kb_docs_digitalizados'] = 0
        metadados_processo['total_em_kb_docs_textos'] = 0

        docs_d_processo = DocumentoDigitalizadoProcesso.objects.filter(processo=self)
        docs_t_processo = DocumentoTextoProcesso.objects.filter(processo=self)

        for d in docs_d_processo:
            try:
                metadados_processo['total_em_kb_docs_digitalizados'] += d.documento.tamanho_em_kb
            except Exception:
                pass

        for d in docs_t_processo:
            try:
                metadados_processo['total_em_kb_docs_textos'] += d.documento.tamanho_em_kb
            except Exception:
                pass

        return metadados_processo

    def pode_solicitar_alteracao_nivel_acesso(self, user=None):
        return not self.pode_alterar_nivel_acesso(user)

    def listar_solicitacoes_nivel_acesso_aberto(self):
        solicitacoes = SolicitacaoAlteracaoNivelAcesso.objects.filter(
            processo=self,
            situacao=SolicitacaoAlteracaoNivelAcesso.SITUACAO_SOLICITADO
        )
        return solicitacoes.order_by('situacao', 'data_hora_solicitacao')

    def existe_solicitacoes_nivel_acesso_aberto(self):
        return self.listar_solicitacoes_nivel_acesso_aberto().exists()

    @staticmethod
    def get_processos_por_pessoa_fisica(pessoa_fisica, filtrar_pessoa_por_tipo_vinculo=False):
        pessoasfisicas_pks = [pessoa_fisica.pk]
        vinculo = pessoa_fisica.get_vinculo()

        if filtrar_pessoa_por_tipo_vinculo:
            qs_pessoasfisicas_por_cpf = PessoaFisica.objects.filter(cpf=pessoa_fisica.cpf)
            if vinculo.eh_aluno():
                qs_pessoasfisicas_por_cpf = qs_pessoasfisicas_por_cpf.filter(eh_aluno=vinculo.eh_aluno())
            elif vinculo.eh_servidor():
                qs_pessoasfisicas_por_cpf = qs_pessoasfisicas_por_cpf.filter(eh_servidor=vinculo.eh_servidor())
            elif vinculo.eh_prestador():
                qs_pessoasfisicas_por_cpf = qs_pessoasfisicas_por_cpf.filter(eh_prestador=vinculo.eh_prestador())
            pessoasfisicas_pks = qs_pessoasfisicas_por_cpf.values_list('pk', flat=True)
        if vinculo and vinculo.user:
            return Processo.objects.filter(
                Q(interessados__pessoafisica__pk__in=pessoasfisicas_pks)
                | Q(usuario_gerador__pessoafisica__pk__in=pessoasfisicas_pks)
                | Q(modificado_por__pessoafisica__pk__in=pessoasfisicas_pks)
                | Q(usuario_finalizacao__pessoafisica__pk__in=pessoasfisicas_pks)
                | Q(pessoas_acompanhando_processo__pessoafisica__pk__in=pessoasfisicas_pks)
            )
        return Processo.objects.filter(pessoas_acompanhando_processo=pessoa_fisica)

    def pode_editar_dados_basicos(self):
        if self.status == ProcessoStatus.STATUS_ANEXADO or not (self.pode_editar() and not self.tem_tramite()):
            return False
        else:
            return True


class ProcessosRelacionados(models.Model):
    processo_origem = models.ForeignKeyPlus('processo_eletronico.Processo', related_name='relacionado_a',
                                            on_delete=models.CASCADE)
    processo_alvo = models.ForeignKeyPlus('processo_eletronico.Processo', related_name='relacionado_com',
                                          on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Processo Relacionado'
        verbose_name_plural = 'Processos Relacionados'
        unique_together = ('processo_origem', 'processo_alvo')


class TipoProcesso(models.ModelPlus):
    SEARCH_FIELDS = ['nome']

    nome = models.CharFieldPlus('Nome', unique=True)

    # Níveis de acesso (do mais restritivo para o menos restritivo)
    # Privado (Sigiloso) - Restrito - Público
    permite_nivel_acesso_privado = models.BooleanField('Privado?', default=True)
    permite_nivel_acesso_restrito = models.BooleanField('Restrito?', default=True)
    permite_nivel_acesso_publico = models.BooleanField('Público?', default=True)

    nivel_acesso_default = models.PositiveIntegerField('Nível de Acesso Padrão', choices=Processo.NIVEL_ACESSO_CHOICES,
                                                       default=Processo.NIVEL_ACESSO_PRIVADO)
    classificacoes = models.ManyToManyFieldPlus('documento_eletronico.Classificacao', verbose_name='Classificação',
                                                blank=True)

    orientacoes_requerimento = models.TextField('Orientações para Abertura de Requerimento', blank=True, null=True)

    consulta_publica = models.BooleanField('Pode ser visualizado integralmente na consulta pública', default=False,
                                           help_text='Todos os documentos públicos deste tipo de processo podem ser visualizados integralmente na consulta pública.')
    ativo = models.BooleanField('ativo', default=True, help_text='Somente os registros ativos ficam disponíveis no cadastro de processos.')

    objects = TipoProcessoManager()

    class Meta:
        verbose_name = 'Tipo de Processo'
        verbose_name_plural = 'Tipos de Processos'
        ordering = ('nome',)

    def __str__(self):
        return self.nome

    def clean(self):
        niveis_acesso_permitidos_keys, niveis_acesso_permitidos_values = self.niveis_acesso_permitidos
        if not niveis_acesso_permitidos_keys:
            raise ValidationError('Defina pelo menos um nível de acesso para o tipo de processo.')

        if self.nivel_acesso_default and self.nivel_acesso_default not in niveis_acesso_permitidos_keys:
            niveis_acesso_permitidos_values_descricao_amigavel = format_iterable(value=niveis_acesso_permitidos_values,
                                                                                 final_separator=' ou ')
            raise ValidationError(
                {
                    'nivel_acesso_default': 'O nível de acesso padrão tem de ser um dos níveis permitidos'
                                            ' para o tipo de processo em questão: {}.'.format(
                                                niveis_acesso_permitidos_values_descricao_amigavel)
                }
            )

        super().clean()

    def get_classificacoes(self, ):
        return ','.join(p.descricao for p in self.classificacoes.all())

    @property
    def niveis_acesso_permitidos(self):
        niveis_acesso_permitidos_keys = list()

        if self.permite_nivel_acesso_privado:
            niveis_acesso_permitidos_keys.append(Processo.NIVEL_ACESSO_PRIVADO)
        if self.permite_nivel_acesso_restrito:
            niveis_acesso_permitidos_keys.append(Processo.NIVEL_ACESSO_RESTRITO)
        if self.permite_nivel_acesso_publico:
            niveis_acesso_permitidos_keys.append(Processo.NIVEL_ACESSO_PUBLICO)

        niveis_acesso_permitidos_values = get_values_from_choices(niveis_acesso_permitidos_keys,
                                                                  Processo.NIVEL_ACESSO_CHOICES)
        return niveis_acesso_permitidos_keys, niveis_acesso_permitidos_values


class Anexacao(models.ModelPlus):
    processo_anexador = models.ForeignKeyPlus('processo_eletronico.Processo', verbose_name='Processo Anexador',
                                              related_name='anexacao_anexadoras')
    processo_anexado = models.ForeignKeyPlus('processo_eletronico.Processo', verbose_name='Processo Anexado',
                                             related_name='anexacao_anexadas')
    data_hora_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.CurrentUserField(verbose_name='Usuário de Criação', related_name='anexacoes_criadas',
                                              editable=False)
    justificativa_criacao = models.TextField('Justificativa de Criação', editable=False)  # eh necessario?
    data_hora_remocao = models.DateTimeFieldPlus(verbose_name='Data de Remoção', blank=True, null=True, editable=False)
    usuario_remocao = models.ForeignKeyPlus(
        'comum.User', verbose_name='Usuário de Remoção', related_name='anexacoes_removidas', editable=False, blank=True,
        null=True, on_delete=models.CASCADE
    )
    justificativa_remocao = models.TextField('Justificativa de Remoção', blank=True, editable=False)

    class Meta:
        verbose_name = 'Anexação de Documentos'
        verbose_name_plural = 'Anexações de Documentos'


class Apensamento(models.ModelPlus):
    data_hora_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.CurrentUserField(verbose_name='Usuário de Criação', related_name='apensamentos_criados',
                                              editable=False)
    justificativa_criacao = models.TextField('Justificativa de Criação', editable=False)
    data_hora_remocao = models.DateTimeFieldPlus(verbose_name='Data de Remoção', blank=True, null=True, editable=False)
    usuario_remocao = models.ForeignKeyPlus(
        'comum.User', verbose_name='Usuário de Remoção', related_name='apensamentos_removidos', editable=False,
        blank=True, null=True, on_delete=models.CASCADE
    )
    justificativa_remocao = models.TextField('Justificativa de Remoção', blank=True, editable=False)

    def finalizar(self, justificativa, request):
        usuario = request.user
        self.usuario_remocao = usuario
        self.justificativa_remocao = justificativa
        self.data_hora_remocao = get_datetime_now()
        self.save()
        self._desapensar_processos(justificativa, request)

    def get_apensamentos_processos(self):
        return self.apensamentoprocesso_set.filter(data_hora_remocao__isnull=True)

    def get_processos(self):
        processos_ids = self.get_apensamentos_processos().values_list('processo_id', flat=True)
        return Processo.objects.filter(id__in=processos_ids)

    def get_numero_protocolo_processos_apensados(self):
        return ', '.join(self.get_processos().values_list('numero_protocolo', flat=True))

    def apensar_processo(self, processo, justificativa):
        ApensamentoProcesso.objects.create(processo=processo, apensamento=self, justificativa_criacao=justificativa)

    @transaction.atomic()
    def _desapensar_processos(self, justificativa, request):
        apensamentos_processos = self.get_apensamentos_processos()

        # Registra a açao de desapensamento
        for apensamento_processo in apensamentos_processos:
            RegistroAcaoProcesso.criar(
                RegistroAcaoProcesso.TIPO_DESAPENSACAO,
                apensamento_processo.processo,
                request,
                'Processo desapensado do(s) processo(s) {}'.format(
                    apensamento_processo.processo.get_numero_protocolo_processos_apensados()),
            )

        for apensamento_processo in apensamentos_processos:
            apensamento_processo.finalizar(justificativa, request, registrar_acao=False)


class ApensamentoProcesso(models.ModelPlus):
    apensamento = models.ForeignKeyPlus('processo_eletronico.Apensamento', on_delete=models.CASCADE)
    processo = models.ForeignKeyPlus(Processo, on_delete=models.CASCADE)
    data_hora_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.CurrentUserField(verbose_name='Usuário de Criação',
                                              related_name='apensamentoprocesso_criados', editable=False)
    justificativa_criacao = models.TextField('Justificativa de Criação', editable=False)
    data_hora_remocao = models.DateTimeFieldPlus(verbose_name='Data de Remoção', blank=True, null=True, editable=False)
    usuario_remocao = models.ForeignKeyPlus(
        'comum.User', verbose_name='Usuário de Remoção', related_name='apensamentoprocesso_removidos', editable=False,
        blank=True, null=True, on_delete=models.CASCADE
    )
    justificativa_remocao = models.TextField('Justificativa de Remoção', blank=True, editable=False)

    def finalizar(self, justificativa, request, registrar_acao=True):
        observacao_desapensamento = 'Processo desapensado do(s) ' 'processo(s) {}'.format(
            self.processo.get_numero_protocolo_processos_apensados())
        usuario = request.user
        self.usuario_remocao = usuario
        self.justificativa_remocao = justificativa
        self.data_hora_remocao = get_datetime_now()
        self.save()

        if registrar_acao:
            RegistroAcaoProcesso.criar(RegistroAcaoProcesso.TIPO_DESAPENSACAO, self.processo, request,
                                       observacao_desapensamento)


class DocumentoProcessoMeta:
    def get_titulo(self):
        raise NotImplementedError

    def get_data_inclusao(self):
        return None

    def get_url(self):
        raise NotImplementedError


class DocumentoProcesso(models.ModelPlus, DocumentoProcessoMeta):
    '''
    Anexação é a inclusão natural de um documento, feito manualmente pelo usuário.

    Juntada por Anexacão ocorrerá através de um processamento, quando um processo for anexado a outro.
    Ex: Processo B, que tem 5 documentos, será anexado ao processo A. Os registros de DocumentoProcesso de B serão
    processados e o "atributo motivo_vinculo_documento_processo_remocao será preenchido com JUNTADA_POR_ANEXACAO.
    No caso serão criados 5 registros de DocumentoProcesso vinculados ao processo A e o atributo
    "motivo_vinculo_documento_processo_inclusai será preenchido com JUNTADA_POR_ANEXACAO.

    Desentramento é a remocão natural de um documento, feito manualmente pelo usuário.
    '''

    MOTIVO_ANEXACAO = 1
    MOTIVO_JUNTADA_POR_ANEXACAO = 2
    MOTIVO_DESENTRANHAMENTO = 3

    MOTIVO_CHOICES_TO_ADD = ((MOTIVO_ANEXACAO, 'Anexação'), (MOTIVO_JUNTADA_POR_ANEXACAO, 'Juntada por Anexação'))

    MOTIVO_CHOICES_TO_REMOVE = (
        (MOTIVO_JUNTADA_POR_ANEXACAO, 'Juntada por Anexação'), (MOTIVO_DESENTRANHAMENTO, 'Desentranhamento'))

    processo = models.ForeignKeyPlus('processo_eletronico.Processo', verbose_name='Processo')

    # CRIAÇÃO DO VÍNCULO ENTRE DOCUMENTO E PROCESSO
    data_hora_inclusao = models.DateTimeFieldPlus('Data de Inclusão', auto_now_add=True, editable=False)
    usuario_inclusao = models.CurrentUserField(verbose_name='Usuário de Inclusão',
                                               related_name='%(app_label)s_%(class)s_documentos_processos_criados',
                                               null=False, editable=False)
    motivo_vinculo_documento_processo_inclusao = models.PositiveIntegerField(
        'Motivo de Inclusão', blank=True, null=True, choices=MOTIVO_CHOICES_TO_ADD, default=MOTIVO_ANEXACAO,
        editable=False
    )

    # REMOCÃO LÓGICA DO VÍNCULO ENTRE DOCUMENTO E PROCESSO
    data_hora_remocao = models.DateTimeFieldPlus('Data de Remoção', blank=True, null=True, editable=False)
    usuario_remocao = models.ForeignKeyPlus(
        'comum.User',
        verbose_name='Usuário de Remoção',
        related_name='%(app_label)s_%(class)s_documentos_processos_alterados',
        editable=False,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    motivo_vinculo_documento_processo_remocao = models.PositiveIntegerField('Motivo de Remoção', blank=True, null=True,
                                                                            choices=MOTIVO_CHOICES_TO_REMOVE)
    justificativa_remocao = models.TextField('Justificativa de Remoção', blank=False, null=True)

    class Meta:
        abstract = True

    @property
    def tem_motivo_entrada_default(self):
        return self.get_motivo_vinculo_documento_processo == self.MOTIVO_ANEXACAO

    def get_motivo_entrada_display(self):
        return self.get_motivo_vinculo_documento_processo_inclusao_display()

    def axenar_documento_ao_processo(self, processo, motivo_vinculo_documento_processo_inclusao):
        raise NotImplementedError

    def remover_documento(self, user, motivo, justificativa):
        self.usuario_remocao = user
        self.data_hora_remocao = datetime.now()
        self.motivo_vinculo_documento_processo_remocao = motivo
        self.justificativa_remocao = justificativa
        self.save()

    def get_titulo(self):
        return f'{self.documento.tipo}: {self.documento}'

    def get_data_inclusao(self):
        return f'Incluído em {self.data_hora_inclusao.strftime("%d/%m/%Y %H:%M")}'

    def get_url(self):
        raise NotImplementedError


class DocumentoTextoProcesso(DocumentoProcesso):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento')

    def clean(self):
        if not self.processo and not (self.documento.estah_assinado or self.documento.estah_finalizado):
            raise ValidationError(
                'O documento {} não está assinado. Os processos apenas podem conter ' 'documentos assinados.'.format(
                    self.documento))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Doc. {self.documento} - Proc. {self.processo}'

    def get_cname(self):
        return convert_to_snake_case(DocumentoTextoProcesso.__name__)

    def get_documento(self, ):
        return self.documento

    def axenar_documento_ao_processo(self, processo, motivo_vinculo_documento_processo_inclusao):
        return DocumentoTextoProcesso.objects.get_or_create(
            documento=self.documento,
            processo=processo,
            data_hora_remocao__isnull=True,
            defaults={'motivo_vinculo_documento_processo_inclusao': motivo_vinculo_documento_processo_inclusao},
        )

    def as_pdf(self):
        return self.documento.as_pdf()

    def foi_adicionado_novamente(self):
        # Se o documento x foi removido e depois foi adicionado novamente ao processo
        return DocumentoTextoProcesso.objects.filter(processo_id=self.processo.id,
                                                     documento_id=self.documento.id,
                                                     data_hora_remocao__isnull=True).exclude(id=self.id).exists()

    def documento_adicionado_novamente(self):
        # Documento que foi adicionado novamente no lugar deste
        return DocumentoTextoProcesso.objects.filter(processo_id=self.processo.id,
                                                     documento_id=self.documento.id,
                                                     data_hora_remocao__isnull=True).exclude(
            id=self.id).order_by('id').last()

    def get_url(self):
        documento_id = self.documento.id
        if tl.get_user().is_anonymous:
            documento_id = self.documento.uuid

        return f'/documento_eletronico/conteudo_documento/{documento_id}/?mostrar_anexos=s'


class DocumentoDigitalizadoProcesso(DocumentoProcesso):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoDigitalizado', verbose_name='Documento')

    def __str__(self):
        return f'Doc. {self.documento} - Proc. {self.processo}'

    def get_cname(self):
        return convert_to_snake_case(DocumentoDigitalizadoProcesso.__name__)

    def get_documento(self, ):
        return self.documento

    def axenar_documento_ao_processo(self, processo, motivo_vinculo_documento_processo_inclusao):
        return DocumentoDigitalizadoProcesso.objects.get_or_create(
            documento=self.documento,
            processo=processo,
            data_hora_remocao__isnull=True,
            defaults={'motivo_vinculo_documento_processo_inclusao': motivo_vinculo_documento_processo_inclusao},
        )

    def as_pdf(self):
        return self.documento.as_pdf()

    def get_url(self):
        documento_id = self.documento.id
        if tl.get_user().is_anonymous:
            documento_id = self.documento.uuid

        return f'/documento_eletronico/visualizar_documento_digitalizado/{documento_id}/#view=FitH&toolbar=0'


class ComentarioProcesso(models.ModelPlus):
    processo = models.ForeignKeyPlus('processo_eletronico.Processo', related_name='comentarios')
    pessoa = models.ForeignKeyPlus('rh.Pessoa')
    comentario = models.TextField('Comentário')
    desconsiderado_em = models.DateTimeFieldPlus('Data de Inclusão', null=True)
    data = models.DateTimeFieldPlus('Data de Inclusão', auto_now_add=True, editable=False)

    class Meta:
        ordering = ('-data',)


class Tramite(models.ModelPlus, DocumentoProcessoMeta):
    processo = models.ForeignKeyPlus('processo_eletronico.Processo', related_name='tramites', on_delete=models.CASCADE)

    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    data_hora_encaminhamento = models.DateTimeField('Data de Encaminhamento', auto_now_add=True)
    data_hora_recebimento = models.DateTimeField(null=True)

    # Dados do despacho
    despacho_cabecalho = models.TextField('Cabeçalho', null=True, blank=True)
    despacho_corpo = models.TextField('Corpo', null=True, blank=True)
    despacho_rodape = models.TextField('Rodapé', null=True, blank=True)

    pessoa_recebimento = models.ForeignKeyPlus('rh.Pessoa', blank=True, null=True, related_name='tramites_recebidos',
                                               on_delete=models.CASCADE)
    remetente_setor = models.ForeignKeyPlus('rh.Setor', related_name='tramites_remetente', on_delete=models.CASCADE,
                                            null=True)
    remetente_pessoa = models.ForeignKeyPlus('rh.Pessoa', related_name='tramites_remetente', on_delete=models.CASCADE,
                                             null=True)

    # Exclusivo, ou o processo é enviado para o setor "padrão", ou para pessoa, caso seja pessoal ou sigiloso
    destinatario_setor = models.ForeignKeyPlus('rh.Setor', null=True, related_name='tramites_destinatario',
                                               on_delete=models.CASCADE)
    destinatario_pessoa = models.ForeignKeyPlus('rh.Pessoa', null=True, related_name='tramites_destinatario',
                                                on_delete=models.CASCADE)
    rotulo = models.CharFieldPlus('Rótulo', null=True, blank=True, max_length=10)
    atribuido_para = models.ForeignKeyPlus('rh.PessoaFisica', related_name='tramite_pe_atribuido_para',
                                           on_delete=models.CASCADE, null=True)
    atribuido_por = models.ForeignKeyPlus('rh.PessoaFisica', related_name='tramite_pe_atribuido_por',
                                          on_delete=models.CASCADE, null=True)
    atribuido_em = models.DateTimeFieldPlus('Atribuído em', null=True)
    em_atendimento = models.BooleanField('Em atendimento', default=False)
    atendido = models.BooleanField('Atendido', default=False)

    tramite_barramento = models.OneToOneFieldPlus('conectagov_pen.TramiteBarramento', verbose_name='Tramite Barramento',
                                                  related_name='tramite_suap_barramento', null=True)

    class History:
        blank_fields = ('despacho_cabecalho', 'despacho_corpo', 'despacho_rodape',)

    class Meta:
        ordering = ('-data_hora_encaminhamento',)

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Se o destinatário for uma pessoa e essa pessoa não for a mesma que estiver tentando receber o processo, então
        # uma exceção será gerada.
        if self.processo.eh_privado() and self.data_hora_recebimento and self.destinatario_pessoa_id != self.pessoa_recebimento_id:
            raise Exception('A pessoa destinatária deste processo não é a mesma que está recebendo.')

        if self.destinatario_pessoa and self.destinatario_setor:
            raise Exception('Um processo não pode ter como destinatários um setor e uma pessoa ao mesmo tempo.')

        if self.processo.eh_privado() and not self.destinatario_pessoa:
            raise Exception('Como o processo é privado, ele só pode ser encaminhado para uma pessoa.')

        # Se está num momento de "update".
        if self.id:
            # Obtendo o trâmite direto no do banco de dados. Se o conteúdo textual do despacho de encaminhamento estiver
            # diferente e o trâmite já tiver sido assinado, então uma exceção será lançada.
            tramite_db = Tramite.objects.get(pk=self.id)
            if (
                    tramite_db.despacho_cabecalho != self.despacho_cabecalho or tramite_db.despacho_corpo != self.despacho_corpo or tramite_db.despacho_rodape != self.despacho_rodape
            ) and self.tem_assinatura:
                raise Exception('O conteúdo textual do trâmite não pode ser mais alterado pois já foi assinado.')

        super().save(*args, **kwargs)
        self.__atualizar_ultimo_tramite_processo()

    @property
    def eh_despacho(self, ):
        return True

    @property
    def foi_recebido(self):
        return bool(self.pessoa_recebimento_id)

    def get_pdf(self, orientacao='portrait', user=None, eh_consulta_publica=False):
        if not eh_consulta_publica:
            user = user or tl.get_user()
        pdf = gerar_despacho_pdf(tramite=self,
                                 orientacao=orientacao,
                                 user=user,
                                 eh_consulta_publica=eh_consulta_publica)
        return pdf

    def get_pdf_as_string_b64(self, orientacao='portrait', user=None):
        pdf = self.get_pdf(orientacao, user)
        return convert_pdf_to_string_b64(pdf)

    def solicitacao_despacho_em_espera(self):
        despacho = SolicitacaoDespacho.objects.filter(processo=self.processo, status=SolicitacaoStatus.STATUS_ESPERANDO)
        return despacho.first()

    @transaction.atomic
    def delete(self):
        super().delete()
        self.__atualizar_ultimo_tramite_processo()

    def get_assinatura(self):
        if self.assinaturatramite_set.exists():
            return self.assinaturatramite_set.first()
        else:
            return None

    def get_retorno_programado(self):
        if self.eh_gerador_retorno_programado_pendente:
            return TramiteRetornoProgramado.objects.filter(tramite_gerador=self,
                                                           data_prevista_retorno__isnull=False).first()
        elif self.eh_resposta_retorno_programado:
            return TramiteRetornoProgramado.objects.filter(tramite_gerador=self.processo.ultimo_tramite,
                                                           data_prevista_retorno__isnull=False).first()
        else:
            return None

    @property
    def atrasado(self):
        trinta_dias = self.data_hora_encaminhamento + timedelta(days=30)
        if trinta_dias > datetime.today():
            return False
        return True

    @property
    def retorno_programado_atrasado(self):
        if self.tem_retorno_programado and self.get_retorno_programado().data_prevista_retorno < datetime.today().date():
            return True
        return False

    @property
    def tem_assinatura(self):
        return self.get_assinatura() is not None

    @property
    def tem_retorno_programado(self):
        return self.get_retorno_programado() is not None

    @transaction.atomic
    def __atualizar_ultimo_tramite_processo(self):
        tramites_processo = self.processo.tramites.all()
        if tramites_processo.exists():
            ultimo_tramite = tramites_processo.latest('data_hora_encaminhamento')
            self.processo.ultimo_tramite = ultimo_tramite
            self.processo.save()

    @property
    def recebido(self):
        return bool(self.data_hora_recebimento)

    @property
    def hash_conteudo(self):
        if all([self.despacho_cabecalho + self.despacho_corpo + self.despacho_rodape]):
            return gerar_hash(str(self.id) + self.despacho_cabecalho + self.despacho_corpo + self.despacho_rodape)
        else:
            return gerar_hash(str(self.id))

    @property
    def eh_tramite_externo(self):
        return bool(self.tramite_barramento)

    @property
    def eh_gerador_retorno_programado_pendente(self):
        return TramiteRetornoProgramado.objects.filter(tramite_gerador=self, data_efetiva_retorno__isnull=True).exists()

    @property
    def eh_resposta_retorno_programado(self):
        return TramiteRetornoProgramado.objects.filter(tramite_gerador__processo=self.processo,
                                                       data_prevista_retorno__isnull=False,
                                                       data_efetiva_retorno__isnull=True).exists()

    @property
    def conteudo(self):
        if all([self.despacho_cabecalho + self.despacho_corpo + self.despacho_rodape]):
            return str(self.id) + self.despacho_cabecalho + self.despacho_corpo + self.despacho_rodape

    def as_pdf(self):
        html = self.conteudo
        import pdfkit

        pdf_bytes = pdfkit.from_string(html, False)
        return pdf_bytes

    @property
    def valido(self):
        return self.assinaturatramite.validar_tramite()

    @property
    def status(self):
        return 'Recebido' if self.recebido else 'Aguardando recebimento'

    @property
    def destinatario_label(self):
        return str(self.destinatario_setor) if self.destinatario_setor else self.destinatario_pessoa.nome_usual

    @classmethod
    def get_todos_setores(cls, user=None, deve_poder_criar_processo=False):
        # Essa rotina irá retornar todos os setores aos quais o usuário logado foi habilitado a trabalhar nos processos
        ids_setores = list()
        if deve_poder_criar_processo:
            ids_setores += list(
                Processo.setores_que_posso_trabalhar_nos_processos(Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO,
                                                                   user).values_list('id', flat=True))
        else:
            ids_setores += list(
                Processo.setores_que_posso_trabalhar_nos_processos(Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO,
                                                                   user).values_list('id', flat=True))
            ids_setores += list(Processo.setores_que_posso_trabalhar_nos_processos(Processo.PERMISSAO_OPERAR_PROCESSO,
                                                                                   user).values_list('id', flat=True))

        Processo.sincronizar_permissoes_processo_documento(user)

        return Setor.objects.filter(pk__in=set(list(ids_setores)))

    @classmethod
    def get_caixa_entrada(cls, setores=None, user=None, filtros=None):
        user = user or get_user()
        pessoa = user.get_profile()
        setores = Tramite.get_todos_setores(user) if not setores else setores

        tramites_entrada = cls.objects.filter(
            Q(destinatario_setor__in=setores,
              processo__nivel_acesso__in=[Processo.NIVEL_ACESSO_PUBLICO, Processo.NIVEL_ACESSO_RESTRITO])
            | Q(destinatario_pessoa=pessoa, processo__nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO)
        )

        tramites_entrada = tramites_entrada.filter(processo_ultimo_tramite__isnull=False,
                                                   processo__status=ProcessoStatus.STATUS_ATIVO)
        tramites_entrada = tramites_entrada.filter(reduce(operator.and_, filtros)) if filtros else tramites_entrada
        return tramites_entrada

    @classmethod
    def get_caixa_saida(cls, setores=None, user=None, filtros=None):
        """
        Retorna os trâmites que foram encaminhados PELO setor e ainda não foram recebidos
        no destino;
        """
        user = user or get_user()

        pessoa = user.get_profile()

        if setores is None:
            setores = Tramite.get_todos_setores(user)

        tramites_saida = cls.objects.filter(
            Q(remetente_setor__in=setores,
              processo__nivel_acesso__in=[Processo.NIVEL_ACESSO_PUBLICO, Processo.NIVEL_ACESSO_RESTRITO])
            | Q(remetente_pessoa=pessoa, processo__nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO)
        )
        tramites_saida = tramites_saida.filter(processo__ultimo_tramite__isnull=False,
                                               processo__status=ProcessoStatus.STATUS_ATIVO,
                                               data_hora_recebimento__isnull=True)
        tramites_saida = tramites_saida.filter(reduce(operator.and_, filtros)) if filtros else tramites_saida
        return tramites_saida

    @classmethod
    def get_caixa_aguardando_retorno(cls, setores=None, user=None, filtros=None):
        """
        Retorna os trâmites que foram encaminhados PELO setor com data de retorno informada mas ainda não foram retornados (data_efetiva_retorno__isnull=True)
        """
        user = user or get_user()

        pessoa = user.get_profile()

        if setores is None:
            setores = Tramite.get_todos_setores(user)

        tramites_aguardando_retorno = cls.objects.filter(
            Q(tramite_gerador__tramite_gerador__remetente_setor__in=setores,
              tramite_gerador__data_prevista_retorno__isnull=False,
              processo__nivel_acesso__in=[Processo.NIVEL_ACESSO_PUBLICO, Processo.NIVEL_ACESSO_RESTRITO])
            | Q(tramite_gerador__tramite_gerador__remetente_pessoa=pessoa,
                tramite_gerador__data_prevista_retorno__isnull=False,
                processo__nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO))
        tramites_aguardando_retorno = tramites_aguardando_retorno.filter(processo__ultimo_tramite__isnull=False,
                                                                         processo__status=ProcessoStatus.STATUS_ATIVO,
                                                                         tramite_retorno__isnull=True,
                                                                         tramite_gerador__data_efetiva_retorno__isnull=True)
        tramites_aguardando_retorno = tramites_aguardando_retorno.filter(
            reduce(operator.and_, filtros)) if filtros else tramites_aguardando_retorno
        return tramites_aguardando_retorno

    @classmethod
    def get_caixa_saida_externos(cls, setores=None, user=None, filtros=None):
        """
        Retorna os trâmites externos que foram encaminhados PELO setor e ainda não foram recebidos
        no destino;
        """
        user = user or get_user()

        pessoa = user.get_profile()

        if setores is None:
            setores = Tramite.get_todos_setores(user)

        tramites_saida = cls.objects.filter(
            Q(remetente_setor__in=setores,
              processo__nivel_acesso__in=[Processo.NIVEL_ACESSO_PUBLICO, Processo.NIVEL_ACESSO_RESTRITO])
            | Q(remetente_pessoa=pessoa, processo__nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO)
        )
        tramites_saida = tramites_saida.filter(
            processo__ultimo_tramite__isnull=False, processo__status=ProcessoStatus.STATUS_EM_TRAMITE_EXTERNO,
            data_hora_recebimento__isnull=True
        )
        tramites_saida = tramites_saida.filter(reduce(operator.and_, filtros)) if filtros else tramites_saida
        return tramites_saida

    def __str__(self):
        return f'Trâmite #{self.pk}'

    def get_cname(self):
        return convert_to_snake_case(Tramite.__name__)

    def get_destino(self):
        if self.destinatario_setor:
            return self.destinatario_setor
        return self.destinatario_pessoa

    def get_absolute_url(self):
        return f'/processo_eletronico/tramite/visualizar/{self.pk}/'

    def possui_pedido_juntada_pendente(self):
        status = [SolicitacaoJuntadaStatus.STATUS_ESPERANDO, SolicitacaoJuntadaStatus.STATUS_CONCLUIDO]
        return self.solicitacaojuntada_set.filter(status__in=status).exists()

    def possui_pedido_juntada_pendente_para(self, user):
        solicitado = user.get_profile()
        status = [SolicitacaoJuntadaStatus.STATUS_ESPERANDO, SolicitacaoJuntadaStatus.STATUS_CONCLUIDO]
        return self.solicitacaojuntada_set.filter(solicitado=solicitado, status__in=status).exists()

    def pedido_juntada_pendente(self):
        status = [SolicitacaoJuntadaStatus.STATUS_ESPERANDO, SolicitacaoJuntadaStatus.STATUS_CONCLUIDO]
        return self.solicitacaojuntada_set.filter(status__in=status).all()

    def pedido_juntada_documento_pendente(self):
        pendencias = SolicitacaoJuntadaDocumento.objects.filter(solicitacao_juntada__tramite=self,
                                                                status=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO).all()
        return pendencias

    def _tramitar_processo_apensado(
            self, processo, remetente_setor, remetente_pessoa, despacho_corpo, data, destinatario_pessoa,
            destinatario_setor, assinar_tramite, papel, nome_papel
    ):

        processo.verificar_dados_processo()
        tramite = Tramite()
        modelo = ModeloDespacho.get_modelo()
        tramite.processo = processo
        tramite.remetente_setor = remetente_setor
        tramite.remetente_pessoa = remetente_pessoa
        tramite.data_hora_encaminhamento = data

        variaveis = get_variaveis(documento_identificador='',
                                  estagio_processamento_variavel=EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO)

        tramite.despacho_cabecalho = processar_template_ckeditor(texto=modelo.cabecalho, variaveis=variaveis)
        tramite.despacho_corpo = despacho_corpo
        tramite.despacho_rodape = processar_template_ckeditor(texto=modelo.rodape, variaveis=variaveis)
        tramite.destinatario_pessoa = destinatario_pessoa
        tramite.destinatario_setor = destinatario_setor
        tramite.save()

        if assinar_tramite:
            assinatura = Assinatura()
            assinatura.pessoa = remetente_pessoa
            assinatura.papel = papel
            assinatura.nome_papel = nome_papel
            assinatura.hmac = gerar_assinatura_tramite_senha(tramite, remetente_pessoa)
            assinatura.save()
            assinatura_tramite = AssinaturaTramite()
            assinatura_tramite.tramite = tramite
            assinatura_tramite.assinatura = assinatura
            assinatura_tramite.save()

    @transaction.atomic()
    def tramitar_processo(self, remetente_setor, remetente_pessoa, despacho_corpo, destinatario_pessoa,
                          destinatario_setor, assinar_tramite=True, papel=None):
        if assinar_tramite and not papel:
            raise ValidationError(
                "O presente trâmite não pode ser assinado, pois o usuário não possui um perfil ativo.")
        self.processo.verificar_dados_processo()
        data = datetime.now()
        # Dados de quem está fazendo o encaminhamento.
        modelo = ModeloDespacho.get_modelo()
        self.remetente_setor = remetente_setor
        self.remetente_pessoa = remetente_pessoa
        self.data_hora_encaminhamento = data

        variaveis = get_variaveis(documento_identificador='',
                                  estagio_processamento_variavel=EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO,
                                  setor_dono=remetente_setor)

        # if despacho_corpo será adicionado o despacho_corpo, cabecalho e rodape ao tramite
        if despacho_corpo:
            self.despacho_cabecalho = processar_template_ckeditor(texto=modelo.cabecalho, variaveis=variaveis)
            self.despacho_corpo = despacho_corpo
            self.despacho_rodape = processar_template_ckeditor(texto=modelo.rodape, variaveis=variaveis)

        # Setor de destino do encaminhamento.
        self.destinatario_pessoa = destinatario_pessoa
        self.destinatario_setor = destinatario_setor

        sid = transaction.savepoint()
        try:
            nome_papel = 'Remetente'
            # TODO: Ver com Diego se tem algum motivo para que o trâmite dos processos "filhos" (apensados) tenha que
            # ser realizado primeiro.
            for processo in self.processo.get_processos_apensados():
                self._tramitar_processo_apensado(
                    processo, remetente_setor, remetente_pessoa, despacho_corpo, data, destinatario_pessoa,
                    destinatario_setor, assinar_tramite, papel, nome_papel
                )

            self.save()
            if assinar_tramite:
                # Assinando encaminhamento
                assinatura = Assinatura()
                assinatura.pessoa = remetente_pessoa
                assinatura.papel = papel  # or remetente_pessoa.funcionario.servidor.papeis_ativos[0]
                assinatura.nome_papel = nome_papel
                assinatura.hmac = gerar_assinatura_tramite_senha(self, remetente_pessoa)
                assinatura.save()
                assinatura_tramite = AssinaturaTramite()
                assinatura_tramite.tramite = self
                assinatura_tramite.assinatura = assinatura
                assinatura_tramite.save()
        except Exception:
            transaction.savepoint_rollback(sid)
            raise

    def _tramitar_receber_apensado(self, processo, data, pessoa_recebimento):
        tramite = Tramite.objects.get(processo=processo, data_hora_recebimento__isnull=True)
        tramite.data_hora_recebimento = data
        tramite.pessoa_recebimento = pessoa_recebimento
        tramite.save()

    def receber_processo(self, pessoa_recebimento, data_hora_recebimento, usuario_recebimento=None):
        data = datetime.today()
        sid = transaction.savepoint()

        self.data_hora_recebimento = data_hora_recebimento
        self.pessoa_recebimento = pessoa_recebimento

        if self.eh_tramite_externo:
            self.processo.usuario_gerador = usuario_recebimento

        try:
            if self.processo.nivel_acesso in [Processo.NIVEL_ACESSO_RESTRITO, Processo.NIVEL_ACESSO_PUBLICO]:
                self.atribuir_tramite()
            for processo in self.processo.get_processos_apensados():
                self._tramitar_receber_apensado(processo, data, pessoa_recebimento)
            self.save()
        except Exception:
            transaction.savepoint_rollback(sid)
            raise

    def pode_visualizar(self, user):
        # Atenção: Tramite usava a antiga versão de "pode_ler", que agora está comentada. Agora esta usando a nova versão
        # de pode_ler, que em tese é a mais apropriada. Vamos observar se ocorre algum comportamento indesejado.
        return self.processo.pode_ler(user)

    def pode_editar(self, user):
        return True

    def atribuir_tramite(self):
        if self.processo.nivel_acesso not in [Processo.NIVEL_ACESSO_RESTRITO, Processo.NIVEL_ACESSO_PUBLICO]:
            raise ValidationError(
                'Somente processos restritos ou públicos podem ser atribuídos a algum funcionário do setor.')

        funcionarios_do_setor_destino = self.destinatario_setor.get_funcionarios()
        funcionarios_aptos_a_receber_tramite = TramiteDistribuicao.objects.filter(
            pessoa_para_distribuir__in=funcionarios_do_setor_destino,
            tipos_processos_atendidos=self.processo.tipo_processo, setor=self.destinatario_setor
        )
        if funcionarios_aptos_a_receber_tramite.exists():
            tramites_em_atendimento = list()
            for funcionario in funcionarios_aptos_a_receber_tramite:
                qtd_tramites_em_atendimento_pelo_funcionario = Tramite.objects.filter(
                    atribuido_para=funcionario.pessoa_para_distribuir).count()
                tramites_em_atendimento.append({'funcionario': funcionario.pessoa_para_distribuir,
                                                'qtd': qtd_tramites_em_atendimento_pelo_funcionario})

            tramites_em_atendimento = sorted(tramites_em_atendimento, key=lambda i: (i['qtd']))
            funcionario_para_atribuicao = tramites_em_atendimento[0]['funcionario']
            self.atribuido_para = funcionario_para_atribuicao
            self.atribuido_em = datetime.now()

    def get_titulo(self):
        return f'Despacho #{self.id}'

    def get_url(self):
        tramite_id = self.id
        if tl.get_user().is_anonymous:
            tramite_id = self.uuid

        return f'/processo_eletronico/tramite/conteudo/{tramite_id}/'


# Demanda_497
class PrioridadeTramite(models.ModelPlus):
    ALTA_PRIORIDADE = 1
    MEDIA_PRIORIDADE = 2
    BAIXA_PRIORIDADE = 3

    PRIORIDADE_CHOICES = ((ALTA_PRIORIDADE, 'Alta'), (MEDIA_PRIORIDADE, 'Média'), (BAIXA_PRIORIDADE, 'Baixa'))
    tramite = models.OneToOneFieldPlus('processo_eletronico.Tramite', on_delete=models.CASCADE)
    prioridade = models.PositiveIntegerField(choices=PRIORIDADE_CHOICES)
    justificativa = models.TextField(editable=True)
    data_hora_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    usuario_criacao = models.CurrentUserField(verbose_name='Usuário de Criação', editable=False)

    class Meta:
        ordering = ("prioridade",)

    def __str__(self):
        retorno = '{}'.format(dict(self.PRIORIDADE_CHOICES)[self.prioridade])
        return retorno


class RegistroAcaoProcesso(models.ModelPlus):
    TIPO_CRIACAO = 1
    TIPO_VISUALIZACAO = 2
    TIPO_IMPRESSAO = 3
    TIPO_EDICAO = 4
    TIPO_APENSACAO = 5
    TIPO_DESAPENSACAO = 6
    TIPO_ANEXACAO = 7
    TIPO_FINALIZACAO = 8
    TIPO_DESFINALIZACAO = 9
    TIPO_EDICAO_INTERESSADOS = 10
    TIPO_EDICAO_NIVEL_ACESSO = 11
    TIPO_EDICAO_ASSUNTO = 12

    TIPO_CHOICES = (
        (TIPO_CRIACAO, 'Criação'),
        (TIPO_VISUALIZACAO, 'Visualização'),
        (TIPO_IMPRESSAO, 'Impressão'),
        (TIPO_EDICAO, 'Edição'),
        (TIPO_APENSACAO, 'Apensação'),
        (TIPO_DESAPENSACAO, 'Desapensação'),
        (TIPO_ANEXACAO, 'Anexação'),
        (TIPO_FINALIZACAO, 'Finalização'),
        (TIPO_DESFINALIZACAO, 'Remoção de Finalização'),
        (TIPO_EDICAO_INTERESSADOS, 'Edição dos Interessados'),
        (TIPO_EDICAO_NIVEL_ACESSO, 'Edição do Nível de Acesso'),
        (TIPO_EDICAO_ASSUNTO, 'Edição do Assunto'),
    )

    processo = models.ForeignKeyPlus('processo_eletronico.Processo', editable=False)
    user = models.CurrentUserField(editable=False)
    data = models.DateTimeFieldPlus('Data', auto_now_add=True, editable=False)
    ip = models.GenericIPAddressField(verbose_name='IP', editable=False)
    tipo = models.PositiveIntegerField(choices=TIPO_CHOICES, editable=False)
    observacao = models.TextField(editable=False)

    class Meta:
        ordering = ("-data",)

    def __str__(self):
        if self.tipo in [self.TIPO_APENSACAO, self.TIPO_DESAPENSACAO, self.TIPO_ANEXACAO, self.TIPO_EDICAO_ASSUNTO]:
            retorno = self.observacao
        else:
            retorno = '{} do processo.'.format(dict(self.TIPO_CHOICES)[self.tipo])
        return retorno

    @classmethod
    def criar(cls, tipo_acao, processo, request, observacao):
        ip = request.META.get('REMOTE_ADDR', '')
        cls.objects.create(tipo=tipo_acao, processo=processo, ip=ip, observacao=observacao)


class Notificao(models.ModelPlus):
    processo = models.ForeignKeyPlus(Processo)
    solicitante = models.CurrentUserField(related_name="%(app_label)s_%(class)s_solicitado_por")
    solicitado = models.ForeignKeyPlus('rh.PessoaFisica', related_name="%(app_label)s_%(class)s_solicitado_a")

    data_solicitacao = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField('Motivo da Solicitação', blank=True, null=True)

    class Meta:
        ordering = ('data_solicitacao',)
        abstract = True


class SolicitacaoCiencia(Notificao):
    TIPO_NOTIFICACAO = 1
    TIPO_INTIMICAO = 2
    TIPO_CITACAO = 3

    TIPO_CHOICES = ((TIPO_NOTIFICACAO, 'Notificação'), (TIPO_INTIMICAO, 'Intimação'), (TIPO_CITACAO, 'Citação'))

    data_ciencia = models.DateTimeField(blank=True, null=True)
    data_limite_ciencia = models.DateTimeField(blank=True, null=True)
    tipo = models.PositiveIntegerField(default=TIPO_NOTIFICACAO, choices=TIPO_CHOICES, editable=False)
    # Data limite para juntada de documentos
    data_limite_juntada = models.DateTimeField(blank=True, null=True)

    status = FSMIntegerField(default=CienciaStatus.STATUS_ESPERANDO, choices=CienciaStatus.STATUS_CHOICES,
                             protected=True)

    # Informações sobre o cancelamento da solicitação
    cancelada_por = models.ForeignKeyPlus('rh.Pessoa', related_name="%(app_label)s_%(class)s_cancelada_por", blank=True,
                                          null=True)
    data_cancelamento = models.DateTimeField(blank=True, null=True)
    justificativa_cancelamento = models.TextField('Justificativa do Cancelamento', blank=True, null=True)

    objects = SolicitacaoCienciaManager()

    class Meta:
        ordering = ('data_solicitacao',)

    def estah_ciente(self):
        return self.status == CienciaStatus.STATUS_CIENTE

    def considerado_ciente(self):
        return self.status == CienciaStatus.STATUS_CONSIDERADO_CIENTE

    def esta_expirada(self):
        today = get_datetime_now().date()
        return self.data_limite_ciencia.date() < today

    def esta_esperando(self):
        return self.status == CienciaStatus.STATUS_ESPERANDO

    def esta_esperando_expirado(self):
        return self.status == CienciaStatus.STATUS_ESPERANDO and self.esta_expirada()

    def esta_esperando_nao_expirado(self):
        return self.status == CienciaStatus.STATUS_ESPERANDO and not self.esta_expirada()

    def esta_cancelada(self):
        return self.status == CienciaStatus.STATUS_CANCELADA

    def pode_cancelar_ciencia(self, user=None):
        user = user or get_user()
        return (user == self.solicitante or (self.processo.esta_nos_meus_setores(
            user) and not self.processo.eh_privado())) and self.esta_esperando_nao_expirado()

    def verificar_ciencia(self):
        today = get_datetime_now().date()
        if self.data_ciencia is None and today > self.data_limite_ciencia.date():
            self.considerar_ciente()
            self.save()

    # TODO sera excluida quando a atualizar_status_processo estiver estavel
    @transaction.atomic()
    def atualizar_status_ciencia(self):
        if self.data_ciencia is not None and self.esta_esperando_nao_expirado():
            self.ciente()
        elif self.esta_expirada():
            self.considerar_ciente()
        self.save()

    def enviar_mail(self):
        titulo = '[SUAP] Solicitação de Ciência: Processo Eletrônico {}'.format(self.processo)
        texto = self.get_texto_solicitacao()
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.solicitado.get_vinculo()],
                          categoria='Processos Eletrônicos: Solicitação de Ciência')

    def get_data_ciencia(self):
        if self.data_ciencia:
            return self.data_ciencia.date()
        return None

    def get_status_display(self):
        """
        Retorna o valor, display, do estado atual.

        Returns:
            String contendo o display do estado atual.
        """
        for status in CienciaStatus.STATUS_CHOICES:
            if status[0] == self.status:
                return mark_safe(status[1])
        return mark_safe(CienciaStatus.STATUS_CHOICES[0][1])

    def get_texto_solicitacao(self):
        texto_info_email = ''
        texto_email_automatico = ''
        email_processo_eletronico = Configuracao.get_valor_por_chave('processo_eletronico', 'email_processo_eletronico')
        exibir_alerta_email_auto = Configuracao.get_valor_por_chave('processo_eletronico', 'exibir_alerta_email_auto')

        if email_processo_eletronico is not None:
            texto_info_email = ' ou entre em contato através do e-mail {}'.format(email_processo_eletronico)
        if exibir_alerta_email_auto:
            texto_email_automatico = '<b>Este e-mail é automático. Por favor, não responder. </b> '

        texto = """<h1>Solicitação de Ciência</h1>
        <h2>Processo Eletrônico {0}</h2>
        <dl>
           <dt>Data:</dt><dd>{1}</dd>
           <dt>Assunto:</dt><dd>{2}</dd>
           <dt>Interessado(s):</dt><dd>{3}</dd>
           <dt>Solicitante:</dt><dd>{4}</dd>
           <dt>Motivação:</dt><dd>{5}</dd>
        </dl>
        <p>--</p>
        <p>{6}Para mais informações, acesse:
            <a href="{7}/admin/processo_eletronico/processo/?opcao=3">
                {7}/admin/processo_eletronico/processo/?opcao=3
            </a>{8}.
        </p>
        """.format(
            self.processo,
            self.data_solicitacao.strftime('%d/%m/%Y %H:%M'),
            self.processo.assunto,
            self.processo.get_interessados(),
            self.solicitante,
            self.motivo,
            texto_email_automatico,
            settings.SITE_URL,
            texto_info_email,
        )
        return texto

    @transition(field=status, source=CienciaStatus.STATUS_ESPERANDO, target=CienciaStatus.STATUS_CONSIDERADO_CIENTE)
    def considerar_ciente(self):
        pass

    @transition(field=status, source=CienciaStatus.STATUS_ESPERANDO, target=CienciaStatus.STATUS_CIENTE)
    def ciente(self):
        pass

    @transition(field=status, source=CienciaStatus.STATUS_ESPERANDO, target=CienciaStatus.STATUS_CANCELADA)
    def cancelar_ciencia(self, user, justificativa):
        self.justificativa_cancelamento = justificativa
        self.data_cancelamento = get_datetime_now()
        self.cancelada_por = user.get_profile().pessoa_ptr

    @transaction.atomic()
    def informar_ciencia(self, data_ciencia):
        self.data_ciencia = data_ciencia
        self.ciente()
        # Quando o usuário informa a ciencia do documento, é aberto a ele, o período para
        # solicitar a jundata de documentos
        tramite = self.processo.ultimo_tramite
        if self.data_limite_juntada and tramite:
            SolicitacaoJuntada.objects.create(tramite=tramite, solicitante=self.solicitante, solicitado=self.solicitado,
                                              data_limite=self.data_limite_juntada, motivo=self.motivo)

    @transaction.atomic()
    def gerar_termo_ciencia(self, processo, user, papel, assunto, content=None):
        setor = get_setor(user)
        if not setor and not user.get_vinculo().eh_usuario_externo():
            return
        if not content:
            pessoafisica = user.get_profile()
            instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
            content = render('processo_eletronico/imprimir_ciencia_pdf.html', {'instance': pessoafisica, 'solicitacao': self, 'setor': setor, 'hoje': datetime.today(), 'instituicao': instituicao}).content

        qs = DocumentoDigitalizado.objects.all()
        pk = qs.latest('id').id if qs.exists() else 0

        today = get_datetime_now()
        documento = DocumentoDigitalizado()
        tipo_documento = TipoDocumento.objects.filter(nome="Termo").first()
        if tipo_documento is None:
            raise ValidationError('Tipo de Documento "Termo" não existe.')

        documento.identificador_tipo_documento_sigla = tipo_documento.sigla
        documento.identificador_numero = pk + 1
        documento.identificador_ano = today.year
        documento.identificador_setor_sigla = setor.sigla if setor else None
        documento.tipo = tipo_documento
        documento.interno = True
        documento.tipo_conferencia = TipoConferencia.objects.get(descricao='Cópia Simples')
        documento.usuario_criacao = user
        documento.data_ultima_modificacao = today
        documento.usuario_ultima_modificacao = user
        documento.data_emissao = today
        documento.setor_dono = get_setor(user)
        documento.dono_documento = user.get_profile()
        documento.data_criacao = today
        documento.assunto = assunto
        documento.nivel_acesso = Documento.NIVEL_ACESSO_RESTRITO
        documento.arquivo.save('ciencia.html', ContentFile(content))
        # Assina o documento de acordo com o papel selecionado na tela
        documento.assinar_via_senha(user, papel)
        documento.save()

        documento_processo = DocumentoDigitalizadoProcesso()
        documento_processo.processo = processo
        documento_processo.documento = documento
        documento_processo.data_hora_inclusao = today
        documento_processo.usuario_inclusao = user
        documento_processo.motivo_vinculo_documento_processo_inclusao = DocumentoProcesso.MOTIVO_ANEXACAO
        documento_processo.save()
        return processo

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class SolicitacaoAssinaturaComAnexacaoProcesso(models.ModelPlus):
    solicitacao_assinatura = models.OneToOneField('documento_eletronico.SolicitacaoAssinatura',
                                                  on_delete=models.CASCADE)
    processo_para_anexar = models.ForeignKeyPlus('processo_eletronico.Processo',
                                                 related_name='solicitacoes_assinatura_com_anexacao',
                                                 on_delete=models.CASCADE)
    # Dados do tramite a ser gerado
    destinatario_setor_tramite = models.ForeignKeyPlus('rh.Setor', null=True, on_delete=models.CASCADE)
    # Corpo do Despacho do trâmite a ser gerado
    despacho_corpo = models.TextField('Despacho', null=True, blank=True)
    papel_solicitante = models.ForeignKeyPlus('rh.Papel', null=True)

    def anexar_ao_processo(self):
        pass


class Minuta(models.ModelPlus):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    # Dados da minuta do documento
    assunto = models.CharFieldPlus('Assunto', blank=True)
    corpo = models.TextField('Corpo')
    cabecalho = models.TextField('Cabeçalho')
    rodape = models.TextField('Rodapé')
    data_criacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True, editable=False)
    # Documento de origem
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento de Texto')

    class History:
        blank_fields = ('cabecalho', 'corpo', 'rodape',)

    class Meta:
        verbose_name = 'Minuta'
        verbose_name_plural = 'Minutas'
        ordering = ('id',)

    @property
    def identificador(self):
        return f'Minuta #{self.id}'

    @property
    def eh_minuta(self):
        return True

    def get_pdf(self, orientacao='portrait', user=None, consulta_publica_hash=None, leitura_para_barramento=False,
                eh_consulta_publica=False):
        if not eh_consulta_publica:
            user = user or tl.get_user()
        pdf = gerar_minuta_pdf(minuta=self,
                               orientacao=orientacao,
                               user=user,
                               consulta_publica_hash=consulta_publica_hash,
                               leitura_para_barramento=leitura_para_barramento,
                               eh_consulta_publica=eh_consulta_publica)
        return pdf

    def get_pdf_as_string_b64(self, orientacao='portrait', user=None, consulta_publica_hash=None,
                              leitura_para_barramento=False):
        pdf = self.get_pdf(orientacao, user, consulta_publica_hash, leitura_para_barramento)
        return convert_pdf_to_string_b64(pdf)

    def __str__(self):
        return self.identificador

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f'/processo_eletronico/processo/visualizar_minuta/{self.pk}'

    def pode_ler(self, user, consulta_publica_hash=None, leitura_para_barramento=False):
        return self.documento.pode_ler(user, consulta_publica_hash, leitura_para_barramento)

    def pode_editar(self, user):
        return self.documento.pode_editar(user)

    def pode_clonar_documento(self, user=None):
        user = user or tl.get_user()
        return self.pode_ler(user) and self.documento.pode_clonar_documento(user)

    @property
    def conteudo(self):
        return '{}|{}|{}|{}|{}'.format(self.identificador, self.cabecalho, self.corpo, self.rodape,
                                       self.data_criacao.strftime('%d/%m/%Y'))

    def as_pdf(self):
        html = self.conteudo
        import pdfkit

        pdf_bytes = pdfkit.from_string(html, False)
        return pdf_bytes

    @property
    def hash_conteudo(self):
        return gerar_hash(self.conteudo)

    @property
    def cabecalho_para_visualizacao(self):
        return self.cabecalho

    @property
    def rodape_para_visualizacao(self):
        return self.rodape

    @property
    def corpo_para_visualizacao(self):
        return self.corpo

    def clonar_documento(self, usuario, setor_dono, modelo=None, nivel_acesso=None, hipotese_legal=None):
        with transaction.atomic():
            documento_novo = DocumentoTexto.objects.create(
                setor_dono=setor_dono,
                usuario_criacao=usuario,
                assunto=self.assunto,
                data_ultima_modificacao=get_datetime_now(),
                usuario_ultima_modificacao=usuario,
                modelo=modelo if modelo else self.documento.modelo,
                nivel_acesso=nivel_acesso if nivel_acesso else self.documento.nivel_acesso
            )
            documento_novo.corpo = self.corpo
            if nivel_acesso in [Documento.NIVEL_ACESSO_RESTRITO, Documento.NIVEL_ACESSO_SIGILOSO]:
                if not hipotese_legal:
                    documento_novo.nivel_acesso = self.documento.modelo.nivel_acesso_padrao
                else:
                    documento_novo.hipotese_legal = hipotese_legal

            documento_novo.save()
            return documento_novo


class ProcessoMinuta(models.ModelPlus, DocumentoProcessoMeta):
    # Lingacoes da minuta
    minuta = models.ForeignKeyPlus(Minuta, verbose_name='Minuta')
    processo = models.ForeignKeyPlus(Processo, verbose_name='Processo')
    # CRIAÇÃO DO VÍNCULO ENTRE DOCUMENTO E PROCESSO
    data_hora_inclusao = models.DateTimeFieldPlus('Data de Inclusão', auto_now_add=True, editable=False)
    usuario_inclusao = models.CurrentUserField(verbose_name='Usuário de Inclusão',
                                               related_name='minutas_processos_criados', null=False, editable=False)
    # REMOCÃO LÓGICA DO VÍNCULO ENTRE PREVIA E PROCESSO
    data_hora_remocao = models.DateTimeFieldPlus('Data de Remoção', blank=True, null=True, editable=False)
    usuario_remocao = models.ForeignKeyPlus(
        'comum.User', verbose_name='Usuário de Remoção', related_name='minutas_processos_alterados', editable=False,
        blank=True, null=True, on_delete=models.CASCADE
    )
    justificativa_remocao = models.TextField('Justificativa de Remoção', blank=False, null=True)

    def __str__(self):
        return f'Minuta #{self.minuta} - Processo: {self.processo}'

    def get_motivo_entrada_display(self):
        return ""  # self.get_motivo_vinculo_documento_processo_inclusao_display()

    def remover_minuta(self, user, motivo, justificativa):
        self.usuario_remocao = user
        self.data_hora_remocao = datetime.now()
        self.motivo_vinculo_documento_processo_remocao = motivo
        self.justificativa_remocao = justificativa
        self.save()

    @property
    def documento(self):
        return self.get_documento()

    @property
    def eh_minuta(self):
        return True

    def get_documento(self):
        return self.minuta.documento

    @property
    def parecer(self):
        return Parecer.objects.filter(processo_minuta=self).select_subclasses().first()

    def pode_remover_parecer(self):
        if not self.parecer:
            return False
        #
        ultimo_tramite = self.processo.get_ultimo_tramite()
        if not ultimo_tramite:
            return True
        #
        return self.parecer.data_hora_inclusao > ultimo_tramite.data_hora_encaminhamento

    def get_titulo(self):
        return f'Minuta - {self.documento.tipo}: {self.documento}'

    def get_url(self):
        minuta_id = self.minuta.id
        if tl.get_user().is_anonymous:
            minuta_id = self.minuta.uuid

        return f'/processo_eletronico/processo/conteudo_minuta/{minuta_id}/'


class AssinaturaParecerSimples(models.ModelPlus):
    assinatura = models.ForeignKeyPlus('documento_eletronico.Assinatura')
    parecer = models.ForeignKeyPlus('processo_eletronico.ParecerSimples')

    @property
    def valido(self):
        # O parâmetro "documento" pode ser "qualquer coisa", seja um DocumentoTexto, Trâmite(despacho), Parecer etc.
        # O que importa é que ele tenha um atributo chamado hash_conteudo.
        return self.assinatura.validar_documento(documento=self.parecer)


class Parecer(models.ModelPlus):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    data_hora_inclusao = models.DateTimeFieldPlus('Data de Inclusão', auto_now_add=True, editable=False)
    usuario_inclusao = models.CurrentUserField(verbose_name='Usuário de Inclusão', null=False, editable=False)
    processo_minuta = models.ForeignKeyPlus('processo_eletronico.ProcessoMinuta', null=False, blank=False,
                                            on_delete=models.CASCADE)

    objects = InheritanceManager()

    class Meta:
        verbose_name = 'Parecer'
        verbose_name_plural = 'Pareceres'

    def __str__(self):
        return f'Parecer #{self.id}'

    def pode_ler(self, user, consulta_publica_hash=None, leitura_para_barramento=False):
        return self.processo_minuta.minuta.pode_ler(user, consulta_publica_hash, leitura_para_barramento)


class ParecerSimples(Parecer, DocumentoProcessoMeta):
    cabecalho = models.TextField('Cabeçalho')
    corpo = models.TextField('Corpo')
    rodape = models.TextField('Rodapé')

    class History:
        blank_fields = ('cabecalho', 'corpo', 'rodape',)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Parecer Simples'
        verbose_name_plural = 'Pareceres Simples'

    @property
    def conteudo(self):
        return '{}|{}|{}|{}|{}'.format(self.id, self.cabecalho, self.corpo, self.rodape,
                                       self.data_hora_inclusao.strftime('%d/%m/%Y'))

    def as_pdf(self):
        html = self.conteudo
        import pdfkit

        pdf_bytes = pdfkit.from_string(html, False)
        return pdf_bytes

    @property
    def hash_conteudo(self):
        return gerar_hash(self.conteudo)

    def get_absolute_url(self):
        return f'/processo_eletronico/processo/visualizar_parecer/{self.pk}'

    @property
    def eh_parecer(self):
        return True

    def get_pdf(self, orientacao='portrait', user=None, consulta_publica_hash=None, leitura_para_barramento=False,
                eh_consulta_publica=False):
        if not eh_consulta_publica:
            user = user or tl.get_user()
        pdf = gerar_parecer_pdf(
            parecer_simples=self, orientacao=orientacao, user=user,
            consulta_publica_hash=consulta_publica_hash,
            leitura_para_barramento=leitura_para_barramento,
            eh_consulta_publica=eh_consulta_publica
        )
        return pdf

    def get_pdf_as_string_b64(self, orientacao='portrait', user=None, consulta_publica_hash=None,
                              leitura_para_barramento=False, eh_consulta_publica=False):
        pdf = self.get_pdf(orientacao, user, consulta_publica_hash, leitura_para_barramento, eh_consulta_publica)
        return convert_pdf_to_string_b64(pdf)

    @property
    def cabecalho_para_visualizacao(self):
        return self.cabecalho

    @property
    def rodape_para_visualizacao(self):
        return self.rodape

    @property
    def corpo_para_visualizacao(self):
        return self.corpo

    def _assinar(self, assinatura):
        AssinaturaParecerSimples.objects.get_or_create(parecer=self, assinatura=assinatura)

    def possui_assinatura(self):
        return AssinaturaParecerSimples.objects.filter(parecer=self).exists()

    def assinaturas(self):
        return AssinaturaParecerSimples.objects.filter(parecer=self).all()

    def pode_assinar(self):
        # O cara apenas pode assinar um parecer se ele pode editar o processo.
        return self.processo_minuta.processo.pode_editar()

    @transaction.atomic()
    def assinar_via_senha(self, user, papel):
        user = user or get_user()
        pessoa_fisica = user.get_profile()
        if self.pode_assinar() and papel is not None:
            assinatura, _ = Assinatura.objects.get_or_create(
                # Dados do assinante
                pessoa=pessoa_fisica,
                cpf=pessoa_fisica.cpf,
                # Dados da assinatura
                hmac=gerar_assinatura_documento_senha(self, pessoa_fisica),
                nome_papel=papel.detalhamento,
                papel=papel,
            )
            self._assinar(assinatura)
            self.save()
        else:
            raise ValidationError('O documento não pode ser assinado por {}.'.format(pessoa_fisica))

    @property
    def valido(self):
        for assinatura_parecer_simples in self.assinaturas():
            if not assinatura_parecer_simples.valido:
                return False

        return True

    def get_titulo(self):
        return f'Parecer sobre a minuta - {self.documento}'

    def get_url(self):
        parecer_id = self.id
        if tl.get_user().is_anonymous:
            parecer_id = self.uuid

        return f'/processo_eletronico/processo/conteudo_parecer/{parecer_id}/'


@reversion.register(follow=["parecer_ptr"])
class ParecerDocumentoTexto(Parecer):
    parecer = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', related_name='parecer_documento_texto')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Parecer Interno'
        verbose_name_plural = 'Pareceres Internos'

    @property
    def conteudo(self):
        return '{}|{}|{}|{}|{}'.format(self.parecer_id, self.parecer.cabecalho, self.parecer.corpo, self.parecer.rodape,
                                       self.parecer.data_hora_inclusao.strftime('%d/%m/%Y'))

    def as_pdf(self):
        html = self.conteudo
        import pdfkit

        pdf_bytes = pdfkit.from_string(html, False)
        return pdf_bytes

    @property
    def hash_conteudo(self):
        return gerar_hash(self.parecer.conteudo)

    def get_absolute_url(self):
        return self.parecer.get_absolute_url()

    @property
    def cabecalho_para_visualizacao(self):
        return self.parecer.cabecalho

    @property
    def rodape_para_visualizacao(self):
        return self.parecer.rodape

    @property
    def corpo_para_visualizacao(self):
        return self.parecer.corpo


class ParecerDocumentoDigitalizado(Parecer):
    parecer = models.ForeignKeyPlus('documento_eletronico.DocumentoDigitalizado',
                                    related_name='parecer_documento_digitalizado')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Parecer Externos'
        verbose_name_plural = 'Pareceres Externos'

    def get_absolute_url(self):
        return self.parecer.get_absolute_url()


class ModeloDespacho(models.ModelPlus):
    cabecalho = models.TextField('Cabeçalho')
    rodape = models.TextField('Rodapé')

    class Meta:
        verbose_name = 'Modelo de Despacho'
        verbose_name_plural = 'Modelos de Despachos'

    @classmethod
    def get_modelo(cls):
        return cls.objects.all()[0]

    def __str__(self):
        return f'Modelo de Despacho #{self.id}'


class ModeloParecer(models.ModelPlus):
    cabecalho = models.TextField('Cabeçalho')
    rodape = models.TextField('Rodapé')

    class Meta:
        verbose_name = 'Modelo de Parecer'
        verbose_name_plural = 'Modelos de Pareceres'

    @classmethod
    def get_modelo(cls):
        return cls.objects.all()[0]

    def __str__(self):
        return f'Modelo de Parecer #{self.id}'


class AssinaturaTramite(models.ModelPlus):
    assinatura = models.OneToOneFieldPlus('documento_eletronico.Assinatura', on_delete=models.CASCADE)
    tramite = models.OneToOneFieldPlus('processo_eletronico.Tramite', on_delete=models.CASCADE)

    def __str__(self):
        return "Assinatura do Despacho do Trâmite {}".format(self.tramite)

    def validar_tramite(self):
        return gerar_assinatura_tramite_senha(self.tramite, self.assinatura.pessoa) == self.assinatura.hmac


class SolicitacaoDespacho(models.ModelPlus):
    processo = models.ForeignKeyPlus('processo_eletronico.processo')
    status = FSMIntegerField(default=SolicitacaoStatus.STATUS_ESPERANDO, choices=SolicitacaoStatus.STATUS_CHOICES,
                             protected=True)
    justificativa_rejeicao = models.TextField('Justificativa da Rejeição', blank=True, null=True)

    # Dados do despacho
    despacho_cabecalho = models.TextField('Cabeçalho', null=True, blank=True)
    despacho_corpo = models.TextField('Corpo', null=False, blank=False)
    despacho_rodape = models.TextField('Rodapé', null=True, blank=True)

    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_resposta = models.DateTimeField(blank=True, null=True)

    # Dados do tramite a ser gerado
    destinatario_setor_tramite = models.ForeignKeyPlus(
        'rh.Setor', verbose_name='Setor de Destino de Trâmite', null=True, related_name='destinatario_setor_tramite',
        on_delete=models.CASCADE
    )
    destinatario_pessoa_tramite = models.ForeignKeyPlus(
        'rh.Pessoa', verbose_name='Pessoa de Destino de Trâmite', null=True, related_name='destinatario_pessoa_tramite',
        on_delete=models.CASCADE
    )
    tramite_gerado = models.OneToOneFieldPlus('processo_eletronico.Tramite',
                                              related_name='%(app_label)s_%(class)s_despacho', null=True)

    # Usuario logado
    remetente_setor = models.ForeignKeyPlus('rh.Setor', related_name='%(app_label)s_%(class)s_remetente_setor',
                                            on_delete=models.CASCADE)
    remetente_pessoa = models.ForeignKeyPlus('rh.Pessoa', related_name='%(app_label)s_%(class)s_remetente_pessoa',
                                             on_delete=models.CASCADE)

    solicitado = models.ForeignKeyPlus('rh.PessoaFisica', related_name='%(app_label)s_%(class)s_solicitado_a')

    objects = SolicitacaoDespachoManager()

    class History:
        blank_fields = ('despacho_cabecalho', 'despacho_corpo', 'despacho_rodape',)

    def __str__(self):
        return "Solicitação de Despacho {}".format(self.pk)

    def get_absolute_url(self):
        return '/processo_eletronico/solicitar_despacho/visualizar/{}/'.format(self.id)

    @transition(field=status, source=SolicitacaoStatus.STATUS_ESPERANDO, target=SolicitacaoStatus.STATUS_DEFERIDA)
    def deferir_solicitacao(self):
        pass

    @transition(field=status, source=SolicitacaoStatus.STATUS_ESPERANDO, target=SolicitacaoStatus.STATUS_INDEFERIDA)
    def indeferir_solicitacao(self):
        pass

    def indeferida(self):
        return self.status == SolicitacaoStatus.STATUS_INDEFERIDA

    def deferida(self):
        return self.status == SolicitacaoStatus.STATUS_DEFERIDA

    def em_espera(self):
        return self.status == SolicitacaoStatus.STATUS_ESPERANDO

    def eh_remetente(self, user=None):
        user = user or tl.get_user()
        pessoa_fisica = user.get_profile()
        return self.remetente_pessoa.get_cpf_ou_cnpj() == pessoa_fisica.cpf

    def eh_solicitado(self, user=None):
        user = user or tl.get_user()
        pessoa_fisica = user.get_profile()
        return self.solicitado.cpf == pessoa_fisica.cpf

    def get_conteudo(self):
        return self.despacho_corpo

    def get_destino(self):
        if self.destinatario_pessoa_tramite is not None:
            return self.destinatario_pessoa_tramite
        return self.destinatario_setor_tramite

    def get_cabecalho(self):
        variaveis = get_variaveis(documento_identificador='')
        return processar_template_ckeditor(texto=self.despacho_cabecalho, variaveis=variaveis)

    def get_corpo(self):
        variaveis = get_variaveis(documento_identificador='')
        return processar_template_ckeditor(texto=self.despacho_corpo, variaveis=variaveis)

    def get_rodape(self):
        variaveis = get_variaveis(documento_identificador='')
        return processar_template_ckeditor(texto=self.despacho_rodape, variaveis=variaveis)

    def save(self, *args, **kwargs):
        if self.destinatario_pessoa_tramite or self.destinatario_setor_tramite:
            return super().save(*args, **kwargs)
        else:
            raise ValidationError("A tramitação deve ter um único destino informado.")

    def ultimo_tramite(self):
        return self.processo.ultimo_tramite if self.processo.ultimo_tramite else self.get_tramite_temporario()

    def get_tramite_temporario(self):
        return Tramite(
            processo=self.processo,
            remetente_setor=self.remetente_setor,
            remetente_pessoa=self.remetente_pessoa,
            despacho_corpo=self.despacho_corpo,
            destinatario_setor=self.destinatario_setor_tramite,
            destinatario_pessoa=self.destinatario_pessoa_tramite,
            data_hora_encaminhamento=self.data_solicitacao,
        )

    @transaction.atomic()
    def gerar_tramite(self, remetente_pessoa, papel):
        tramite = Tramite()
        tramite.processo = self.processo
        tramite.tramitar_processo(
            remetente_setor=self.remetente_setor,
            remetente_pessoa=remetente_pessoa,
            despacho_corpo=self.despacho_corpo,
            destinatario_setor=self.destinatario_setor_tramite,
            destinatario_pessoa=self.destinatario_pessoa_tramite,
            papel=papel,
        )
        self.tramite_gerado = tramite
        self.data_resposta = get_datetime_now()
        self.save()


# TODO: Rever a parte de Requerimento e Processo no tocante a adição de documentos internos e externos (upload), de forma
# a unificar esse upload. Outra coisa que pode ser analisada é a unificação de Requerimento e Processo, já que são entidades
# muito próximas.
class Requerimento(models.ModelPlus):
    SITUACAO_INICIADO = 1  # status-iniciado
    SITUACAO_FINALIZADO = 2  # status-finalizado
    SITUACAO_CANCELADO = 3  # status-cancelado

    SITUACAO_CHOICES = [[SITUACAO_INICIADO, 'Iniciado'], [SITUACAO_FINALIZADO, 'Finalizado'],
                        [SITUACAO_CANCELADO, 'Cancelado']]

    # Pessoa que abriu o requerimento
    # Todos os requerimentos da pessoa sao abertos por ela mesma
    # Foi usado o Vinculo para se adequar a modelagem feita por Hugo
    interessado = models.ForeignKeyPlus('comum.Vinculo')

    # Ex.: Acesso à Informação: Demanda do e-SIC, Gestão de Contrato: Acréscimo Contratual
    tipo_processo = models.ForeignKeyPlus('processo_eletronico.TipoProcesso', verbose_name='Tipo de Processo')
    hipotese_legal = models.ForeignKeyPlus('documento_eletronico.HipoteseLegal', verbose_name='Hipótese Legal',
                                           blank=False, null=True)

    # Descrição resumida do objeto do requerimento
    # Ex: Alteração de período de férias.
    # Tem o mesmo nome do atributo da classe Processo
    assunto = models.CharFieldPlus('Assunto', db_index=True)

    # Só aparece no PDF do requerimento que será anexado ao processo. É neste campo que o usuário deverá detalhar o período.
    # Ex: Por interesse da administração, gostaria de alterar as minhas férias de 20/jan/2019 a 10/fev2019 para 15/fev/2019 a 05/mar/2019
    # Esta alteração será necessária para poder implemenetar o sistema X.
    descricao = models.CharFieldPlus('Descrição', max_length=510, blank=False, null=True)

    # Setor de destino do processo a ser aberto por este requerimento
    destinatario_setor = models.ForeignKeyPlus('rh.Setor', blank=True, null=True,
                                               verbose_name="Setor de Destino do Processo")

    situacao = models.PositiveIntegerField('Situação', choices=SITUACAO_CHOICES)

    data_hora_iniciado = models.DateTimeField(auto_now_add=True, verbose_name='Data/Hora Iniciado')
    data_hora_finalizado = models.DateTimeField(blank=True, null=True, verbose_name='Data/Hora Finalizado')
    data_hora_cancelado = models.DateTimeField(blank=True, null=True, verbose_name='Data/Hora Cancelado')

    processo = models.ForeignKeyPlus(Processo, blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Requerimento'
        verbose_name_plural = 'Requerimentos'

    def __str__(self):
        return "{}".format(self.assunto)

    def get_absolute_url(self):
        return '/processo_eletronico/gerenciar_requerimento/{}/'.format(self.id)

    # TODO: Colocar todas as validações no clean() e verificar os locais que chamam o save() e fazer a chamada ao clean()
    # antes. A priori náo é uma boa prática chamar o clean() dentro do save() porque o clean acabará sendo chamado 2
    # vezes. Ex: Ao usar o ModelForm do Django, ele mesmo já chama o clean() do modelo antes de chamar o save().
    def save(self, request_user, *args, **kwargs):
        is_insert = self.pk is None
        vinculo_pessoa = Vinculo.objects.get(user=request_user)
        #
        if is_insert:
            # Situacao inicial
            self.situacao = self.SITUACAO_INICIADO
            # A data_hora_iniciado eh preenchida pelo seu auto_now_add

            # Pega o vinculo da pessoa logada e seta no requerimento
            self.interessado = vinculo_pessoa
        else:
            requerimento_db = Requerimento.objects.get(id=self.id)

            # Verifica se a pessoa logada pode ter acesso a alterar o requerimento
            if vinculo_pessoa != requerimento_db.interessado:
                raise Exception('O requerimento só pode ser alterado pela pessoa que o cadastrou.')

            # Condição principal para que um requerimento possa ser alterado
            if not requerimento_db.pode_editar():
                raise Exception('Este requerimento não pode ser alterado.')

            # Se está alterando situcao para cancelado
            if self.is_cancelado():
                self.data_hora_cancelado = get_datetime_now()
            else:
                # Se está alterando situcao para finalizado
                if self.is_finalizado():
                    # Só pode finalizar se tiver um processo associado
                    if self.processo is None:
                        raise Exception('Para finalizar é preciso ter um Processo associado.')
                    # Só pode finalizar se tiver destinatario_setor
                    if self.destinatario_setor is None:
                        raise Exception('Para finalizar é preciso que informe o Setor de Destino do Processo.')
                    self.data_hora_finalizado = get_datetime_now()

        return super().save(*args, **kwargs)

    def clean(self):
        # TODO: Como Hipotese Legal está sendo usado em vários locais, ver uma forma de criar um método estático em
        # Hipótese Legal para realizar essa validação.
        if not hasattr(self, 'tipo_processo'):
            raise ValidationError({'tipo_processo': 'Selecione o tipo do processo.'})
        #
        nivel_acesso_default = self.tipo_processo.nivel_acesso_default
        nivel_acesso_default_display = self.tipo_processo.get_nivel_acesso_default_display()
        #
        if nivel_acesso_default in (Processo.NIVEL_ACESSO_PRIVADO, Processo.NIVEL_ACESSO_RESTRITO):
            hipoteses_legais_opcoes = None
            if nivel_acesso_default == Processo.NIVEL_ACESSO_PRIVADO:
                hipoteses_legais_opcoes = HipoteseLegal.objects.filter(nivel_acesso=NivelAcessoEnum.SIGILOSO.name)
            elif nivel_acesso_default == Processo.NIVEL_ACESSO_RESTRITO:
                hipoteses_legais_opcoes = HipoteseLegal.objects.filter(nivel_acesso=NivelAcessoEnum.RESTRITO.name)

            if hipoteses_legais_opcoes and not self.hipotese_legal:
                raise ValidationError({
                    'hipotese_legal': 'O nível de acesso "{}" exige que você defina uma hipótese legal.'.format(
                        nivel_acesso_default_display)})
        else:
            self.hipotese_legal = None

        if self.hipotese_legal and (
                (
                    self.hipotese_legal.nivel_acesso == NivelAcessoEnum.SIGILOSO.name and nivel_acesso_default != Processo.NIVEL_ACESSO_PRIVADO)
                or (
                    self.hipotese_legal.nivel_acesso == NivelAcessoEnum.RESTRITO.name and nivel_acesso_default != Processo.NIVEL_ACESSO_RESTRITO)
        ):
            raise ValidationError({
                'hipotese_legal': 'Escolha uma hipótese legal compatível com o nível de acesso "{}"'.format(
                    nivel_acesso_default_display)})

        super().clean()

    def delete(self, *args, **kwargs):
        raise Exception('Impossível excluir um requerimento.')

    def is_iniciado(self):
        return self.situacao == self.SITUACAO_INICIADO

    def is_finalizado(self):
        return self.situacao == self.SITUACAO_FINALIZADO

    def is_cancelado(self):
        return self.situacao == self.SITUACAO_CANCELADO

    def get_situacao_as_html(self):
        if self.is_iniciado():
            return format_html('<span class="status status-alert">{} em {}</span>'.format(self.SITUACAO_CHOICES[0][1],
                                                                                          self.data_hora_iniciado.strftime(
                                                                                              '%d/%m/%Y às %H:%M:%S')))
        elif self.is_finalizado():
            return format_html('<span class="status status-success">{} em {}</span>'.format('Processo criado',
                                                                                            self.data_hora_finalizado.strftime(
                                                                                                '%d/%m/%Y às %H:%M:%S')))
        elif self.is_cancelado():
            return format_html('<span class="status status-error">{} em {}</span>'.format(self.SITUACAO_CHOICES[2][1],
                                                                                          self.data_hora_cancelado.strftime(
                                                                                              '%d/%m/%Y às %H:%M:%S')))

    def pode_editar(self):
        return self.is_iniciado()

    def get_numero_requerimento(self):
        return '{:04d}'.format(self.id)

    @staticmethod
    def get_requerimento_by_user(request_user, requerimento_id):
        vinculo_pessoa = Vinculo.objects.get(user=request_user)
        return Requerimento.objects.filter(Q(id=requerimento_id) & Q(interessado=vinculo_pessoa)).first()

    @staticmethod
    def get_requerimentos_by_user(request_user):
        vinculo_pessoa = Vinculo.objects.get(user=request_user)
        return Requerimento.objects.filter(interessado=vinculo_pessoa).order_by('-id')

    @staticmethod
    def _get_tipo_documento_requerimento():
        # ---------------------------
        # Validacoes para cadastrar o processo
        # ---------------------------
        try:
            tipo_documento_requerimento = TipoDocumento.objects.get(
                pk=Configuracao.get_valor_por_chave('documento_eletronico', 'tipo_documento_requerimento'))
            return tipo_documento_requerimento
        except TipoDocumento.DoesNotExist:
            raise ValidationError(
                'Para criar um requerimento se faz necessário definir a configuração "Tipo de Documento para Requerimento" do módulo "Documento Eletrônico".')

    def _gerar_documento(self, tipo_documento_requerimento, pdf, user, papel):
        # ---------------------------
        # Gera PDF do requerimento
        # ---------------------------
        documento = DocumentoDigitalizado()
        documento.identificador_tipo_documento_sigla = tipo_documento_requerimento.sigla
        documento.identificador_numero = self.id
        documento.identificador_ano = datetime.now().year
        documento.identificador_setor_sigla = get_setor(user).sigla
        documento.tipo = tipo_documento_requerimento
        documento.interno = True
        documento.tipo_conferencia = TipoConferencia.objects.get(descricao='Cópia Simples')
        documento.setor_dono = get_setor(user)
        documento.assunto = self.assunto
        documento.data_emissao = datetime.now()

        # O nivel de acesso do PDF do requerimento era definnido de acordo com o "tipo_processo.nivel_acesso_default" do
        # requerimento. Para proteger os dados do interessado o nível acesso do PDF será RESTRITO
        documento.nivel_acesso = Documento.NIVEL_ACESSO_RESTRITO

        # Informando a hipótese legal que será usada ao criado o documento digitalizado restrito, caso existam hipóteses
        # cadastradas para tal.
        if HipoteseLegal.objects.filter(nivel_acesso=NivelAcessoEnum.RESTRITO.name).exists():
            hipotese_legal_documento_abertura_requerimento_id = Configuracao.get_valor_por_chave('processo_eletronico',
                                                                                                 'hipotese_legal_documento_abertura_requerimento')
            if not hipotese_legal_documento_abertura_requerimento_id:
                raise ValidationError(
                    'Impossível gerar o documento digitalizado do requerimento pois não há hipótese legal configurada para isso no módulo de processo eletrônico. Entre em contato com os administradores do sistema.'
                )
            documento.hipotese_legal = HipoteseLegal.objects.get(pk=hipotese_legal_documento_abertura_requerimento_id)

        documento.usuario_criacao = user
        documento.data_criacao = datetime.now()
        documento.usuario_ultima_modificacao = user
        documento.data_ultima_modificacao = datetime.now()
        documento.arquivo.save('requerimento_n.html', ContentFile(pdf.content))
        documento.assinar_via_senha(user, papel)
        # Chamando a validação do domínio.
        documento.clean()
        documento.save()
        return documento

    def _vincular_requerimento_processo(self, tipo_documento_requerimento, pdf, user, papel):
        # ---------------------------
        # Vincula PDF do requerimento ao processo
        # ---------------------------
        documento = self._gerar_documento(tipo_documento_requerimento, pdf, user, papel)
        DocumentoDigitalizadoProcesso.objects.create(processo=self.processo, documento=documento)

    def _adicionar_documentos_processo(self, user, papel):
        documentos_requerimento = self._listar_documentos()
        for doc in documentos_requerimento:
            if doc.digitalizado:
                documento = None
                compartilhamento_pessoa = None
                if hasattr(doc, 'documento') and doc.documento.eh_documento_pessoal:
                    documento = doc.documento
                else:
                    documento = doc.gerar_documento_digitalizado(user, papel)
                    compartilhamento_pessoa = doc.compartilhamento_pessoa.all()
                self.processo.adicionar_documento_digitalizado(documento, user, compartilhamento_pessoa)
            else:
                self.processo.adicionar_documento_texto(doc.documento)

    def _listar_documentos(self):
        documentos_texto = DocumentoTextoRequerimento.objects.filter(requerimento_id=self.id).extra(select={'digitalizado': False})
        documentos_digitalizados = DocumentoDigitalizadoRequerimento.objects.filter(requerimento_id=self.id).extra(select={'digitalizado': True})
        documentos_digitalizados_outros = DocumentoDigitalizadoRequerimentoOutros.objects.filter(requerimento_id=self.id).extra(select={'digitalizado': True})
        documentos_requerimento = list(documentos_texto) + list(documentos_digitalizados) + list(documentos_digitalizados_outros)
        documentos_requerimento.sort(key=lambda a: a.data_hora_cadastro, reverse=True)
        return documentos_requerimento

    def _cadastrar_tramite(self, user, papel):
        tramite_novo = Tramite()
        tramite_novo.processo = self.processo
        tramite_novo.tramitar_processo(
            remetente_setor=get_setor(user),
            remetente_pessoa=user.get_profile(),
            despacho_corpo=None,
            destinatario_pessoa=None,
            destinatario_setor=self.destinatario_setor,
            assinar_tramite=False,
            papel=papel,
        )

    def _gerar_processo(self):
        self.processo = Processo(tipo_processo=self.tipo_processo, assunto=self.assunto,
                                 nivel_acesso=self.tipo_processo.nivel_acesso_default,
                                 hipotese_legal=self.hipotese_legal)
        self.processo.clean()
        self.processo.save()

        self.processo.interessados.add(self.interessado.pessoa)

        self.processo.clean()
        self.processo.save()
        # ---------------------------
        # Verifica a criacao do processo
        # ---------------------------
        self.processo.verificar_criacao_processo()

    def _finalizar_requerimento(self, user):
        self.situacao = Requerimento.SITUACAO_FINALIZADO
        self.save(user)

    @transaction.atomic()
    def cadastrar_processo(self, user, papel, pdf):
        """
        Passar a lista de pessoas que compartilham o acesso aos documentos sigilosos.
        """
        try:
            # ---------------------------
            # Cadastrando o processo
            # ---------------------------
            tipo_documento_requerimento = Requerimento._get_tipo_documento_requerimento()
            # Criando processo eletronico
            # ---------------------------
            self._gerar_processo()
            # Finaliza o requerimento e vincula o processo ao requerimento
            # ---------------------------
            self._finalizar_requerimento(user)
            # Vinculando o PDF do requerimento ao processo
            # ---------------------------
            self._vincular_requerimento_processo(tipo_documento_requerimento, pdf, user, papel)
            # Cadastra os documentos do requerimeto no processo (se houver)
            # ---------------------------
            self._adicionar_documentos_processo(user, papel)
            # Cadastra tramite do processo
            # ---------------------------
            self._cadastrar_tramite(user, papel)
            return self.processo
        except Exception as e:
            raise e

    @staticmethod
    def get_sugestao_primeiro_tramite(tipo_processo, uo_origem_interessado):
        c = ConfiguracaoTramiteProcesso.objects.filter(tipo_processo=tipo_processo,
                                                       uo_origem_interessado=uo_origem_interessado)
        if c:
            return c[0].setor_destino_primeiro_tramite
        else:
            return None


class DocumentoTextoRequerimento(models.ModelPlus):
    requerimento = models.ForeignKeyPlus('processo_eletronico.Requerimento')
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento')

    data_hora_cadastro = models.DateTimeField(blank=True, null=True, auto_now_add=True)

    def clean(self):
        if not (self.documento.estah_assinado or self.documento.estah_finalizado):
            raise ValidationError(
                'O documento {} não está assinado. Os requerimentos apenas podem conter ' 'documentos assinados.'.format(
                    self.documento))

    def get_cname(self):
        return 'documento_texto_processo_requerimento'

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Doc. {}'.format(self.documento)


class DocumentoDigitalizadoRequerimento(models.ModelPlus):
    requerimento = models.ForeignKeyPlus('processo_eletronico.Requerimento')
    arquivo = models.FileFieldPlus('Arquivo', upload_to='private-media/requerimentos_documentos/')
    tipo = models.ForeignKeyPlus('documento_eletronico.TipoDocumento', related_name='tipo_documento_requerimento')

    assunto = models.CharFieldPlus('Assunto', db_index=True)
    nivel_acesso = models.PositiveIntegerField(choices=Documento.NIVEL_ACESSO_CHOICES,
                                               default=Documento.NIVEL_ACESSO_PUBLICO, verbose_name='Nível de Acesso')
    hipotese_legal = models.ForeignKeyPlus('documento_eletronico.HipoteseLegal', verbose_name='Hipótese Legal',
                                           blank=False, null=True)

    tipo_conferencia = models.ForeignKeyPlus(TipoConferencia, verbose_name='Tipo de Conferência',
                                             related_name='tipo_conferencia_requerimento')

    identificador_numero = models.PositiveIntegerField('Número', blank=True, null=True)
    identificador_ano = models.PositiveIntegerField('Ano', blank=True, null=True)

    identificador_setor_sigla = models.CharFieldPlus('Sigla do Setor', max_length=100, blank=True, null=True)
    identificador_tipo_documento_sigla = models.CharFieldPlus('Sigla do Tipo de Documento', max_length=50, blank=True,
                                                              null=True)

    data_hora_cadastro = models.DateTimeField(blank=True, null=True, auto_now_add=True)

    compartilhamento_pessoa = models.ManyToManyFieldPlus('rh.Pessoa', verbose_name='Compartilhamento com pessoas',
                                                         blank=True)

    class Meta:
        verbose_name = 'Documento Digitalizado'
        verbose_name_plural = 'Documentos Digitalizados'

    def __str__(self):
        return "{}".format(self.assunto)

    def clean(self):
        # TODO: Como Hipotese Legal está sendo usado em vários locais, ver uma forma de criar um método estático em
        # Hipótese Legal para realizar essa validação.
        if self.nivel_acesso in (Documento.NIVEL_ACESSO_SIGILOSO, Documento.NIVEL_ACESSO_RESTRITO):
            hipoteses_legais_opcoes = None
            if self.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
                hipoteses_legais_opcoes = HipoteseLegal.objects.filter(nivel_acesso=NivelAcessoEnum.SIGILOSO.name)
            elif self.nivel_acesso == Documento.NIVEL_ACESSO_RESTRITO:
                hipoteses_legais_opcoes = HipoteseLegal.objects.filter(nivel_acesso=NivelAcessoEnum.RESTRITO.name)

            if hipoteses_legais_opcoes and not self.hipotese_legal:
                raise ValidationError({
                    'hipotese_legal': 'O nível de acesso "{}" exige que você defina uma hipótese legal.'.format(
                        self.get_nivel_acesso_display())})
        else:
            self.hipotese_legal = None

        if self.hipotese_legal and (
                (
                    self.hipotese_legal.nivel_acesso == NivelAcessoEnum.SIGILOSO.name and self.nivel_acesso != Documento.NIVEL_ACESSO_SIGILOSO)
                or (
                    self.hipotese_legal.nivel_acesso == NivelAcessoEnum.RESTRITO.name and self.nivel_acesso != Documento.NIVEL_ACESSO_RESTRITO)
        ):
            raise ValidationError({
                'hipotese_legal': 'Escolha uma hipótese legal compatível com o nível de acesso "{}".'.format(
                    self.get_nivel_acesso_display())})

        super().clean()

    @transaction.atomic()
    def gerar_documento_digitalizado(self, user, papel):
        documento = DocumentoDigitalizado()
        documento.identificador_tipo_documento_sigla = self.identificador_setor_sigla
        documento.identificador_numero = self.identificador_numero
        documento.identificador_ano = self.identificador_ano
        documento.identificador_setor_sigla = get_setor(user).sigla
        documento.tipo = self.tipo
        documento.tipo_conferencia = self.tipo_conferencia
        documento.assunto = self.assunto
        documento.nivel_acesso = self.nivel_acesso
        documento.hipotese_legal = self.hipotese_legal
        documento.interno = True
        documento.setor_dono = get_setor(user)
        documento.data_emissao = datetime.now()
        documento.usuario_criacao = user
        documento.data_criacao = datetime.now()
        documento.usuario_ultima_modificacao = user
        documento.data_ultima_modificacao = datetime.now()
        documento.arquivo.save(self.arquivo.name, self.arquivo)
        # Chamando a validação do domínio.
        documento.clean()
        documento.save()
        documento.assinar_via_senha(user, papel)
        return documento


class DocumentoDigitalizadoRequerimentoOutros(models.ModelPlus):
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoDigitalizado', verbose_name='Documento')
    requerimento = models.ForeignKeyPlus('processo_eletronico.Requerimento')
    data_hora_cadastro = models.DateTimeField(blank=True, null=True, auto_now_add=True)

    def __str__(self):
        return 'Doc. {} - Proc. {}'.format(self.documento, self.requerimento)

    def get_documento(self,):
        return self.documento

    def axenar_documento_ao_processo(self, processo, motivo_vinculo_documento_processo_inclusao):
        return DocumentoDigitalizadoProcesso.objects.get_or_create(
            documento=self.documento,
            processo=processo,
            data_hora_remocao__isnull=True,
            defaults={'motivo_vinculo_documento_processo_inclusao': motivo_vinculo_documento_processo_inclusao},
        )

    def as_pdf(self):
        return self.documento.as_pdf()


class ConfiguracaoTramiteProcesso(models.ModelPlus):
    tipo_processo = models.ForeignKeyPlus('processo_eletronico.TipoProcesso', verbose_name='Tipo de Processo')

    uo_origem_interessado = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Origem do interessado')

    setor_destino_primeiro_tramite = models.ForeignKeyPlus('rh.Setor', verbose_name="Destino do primeiro trâmite")

    class Meta:
        verbose_name = 'Configuração do Trâmite do Processo'
        verbose_name_plural = 'Configurações do Trâmite do Processo'


class ConfiguracaoProcessoEletronico(models.ModelPlus):
    setores_que_podem_cadastrar_retorno_programado = models.ManyToManyFieldPlus(Setor, blank=True,
                                                                                related_name='setores_permitidos_retorno_programado_set',
                                                                                help_text='Informe os setores que podem cadastrar data de retorno programado nos trâmites.',
                                                                                verbose_name="Setores permitidos para uso do Retorno Programado")

    class Meta:
        verbose_name = 'Configuração do Módulo de Processos Eletrônicos'
        verbose_name_plural = 'Configurações do Módulo de Processos Eletrônicos'


class SolicitacaoJuntada(models.ModelPlus):
    tramite = models.ForeignKeyPlus(Tramite)
    status = FSMIntegerField(default=SolicitacaoJuntadaStatus.STATUS_ESPERANDO,
                             choices=SolicitacaoJuntadaStatus.STATUS_CHOICES, protected=True)
    # Dados do solicitante
    solicitante = models.CurrentUserField(related_name="%(app_label)s_%(class)s_solicitado_por")
    motivo = models.TextField('Motivo da Solicitação', blank=True, null=True)
    # A data limite para o usuário realizar o pedido de juntada.
    data_limite = models.DateTimeField(verbose_name='Data limite para Juntada de Documento', blank=False, null=False)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    # Dados do solicitado
    solicitado = models.ForeignKeyPlus('rh.Pessoa', related_name="%(app_label)s_%(class)s_solicitado_a")
    # Informa que o usuário terminou
    data_conclusao = models.DateTimeField(blank=True, null=True)
    # Informações sobre o cancelamento da solicitação
    cancelada_por = models.ForeignKeyPlus('rh.Pessoa', related_name="%(app_label)s_%(class)s_cancelada_por", blank=True,
                                          null=True)
    data_cancelamento = models.DateTimeField(blank=True, null=True)
    justificativa_cancelamento = models.TextField('Justificativa do Cancelamento', blank=True, null=True)

    class Meta:
        verbose_name = 'Pedido de Juntada de Documento'
        verbose_name_plural = 'Pedidos de Juntada de Documentos'
        ordering = ['-data_solicitacao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_status = self.status

    @property
    def processo(self):
        return self.tramite.processo

    @property
    def expirou(self):
        if get_datetime_now().date() > self.data_limite.date():
            return True
        else:
            return False

    def possui_solicitacoes_de_juntada(self):
        return self.solicitacaojuntadadocumento_set.exists()

    def possui_solicitacoes_de_juntada_pendentes(self):
        return self.solicitacaojuntadadocumento_set.filter(
            status=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO).exists()

    def solicitacoes_de_juntada_pendentes(self):
        return self.solicitacaojuntadadocumento_set.filter(status=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO)

    def solicitacoes_de_juntada(self):
        return self.solicitacaojuntadadocumento_set.all()

    def estah_esperando(self):
        return self.status == SolicitacaoJuntadaStatus.STATUS_ESPERANDO

    def estah_concluida(self):
        return self.status == SolicitacaoJuntadaStatus.STATUS_CONCLUIDO

    def estah_finalizada(self):
        return self.status == SolicitacaoJuntadaStatus.STATUS_FINALIZADO

    def estah_cancelada(self):
        return self.status == SolicitacaoJuntadaStatus.STATUS_CANCELADO

    def estah_expirada(self):
        return self.status == SolicitacaoJuntadaStatus.STATUS_EXPIRADO

    def estah_ativo(self):
        return self.estah_esperando()

    def processo_na_caixa_entrada(self, user):
        setores = Tramite.get_todos_setores(user)
        return self.processo.esta_na_caixa_entrada(setores=setores, user=user, recebido=True)

    def usuario_pode_deferir(self, user):
        pessoa_logada = user.get_profile()
        if pessoa_logada.pessoa_ptr == self.solicitado:
            return False
        # return self.estah_concluida() and (user == self.solicitante or self.processo_na_caixa_entrada(user))
        # Se o solicitante nao estiver mais no setor ele nao pode avaliar
        # Se o processo estiver em um dos meus setores pode deferir a solicitacao de juntada
        # Se for um processo privado o solicitante vai poder deferir pq o processo ta com ele
        return self.estah_concluida() and (self.processo.esta_nos_meus_setores(user) or (self.processo.eh_privado() and user == self.solicitante))

    def usuario_pode_cancelar(self, user):
        return user == self.solicitante

    def pode_anexar_documento(self, user=None):
        user = user or get_user()
        pessoa = user.get_profile().pessoa_ptr
        return self.estah_ativo() and pessoa == self.solicitado

    def pode_adicionar_documento_interno(self, user=None):
        user = user or get_user()
        usuario_esta_aposentado = user.get_relacionamento().eh_servidor and user.get_relacionamento().eh_aposentado
        eh_usuario_externo = user.get_vinculo().eh_usuario_externo()
        return self.pode_anexar_documento(user) and not usuario_esta_aposentado and not eh_usuario_externo

    def pode_deferir_documento(self, user=None):
        user = user or get_user()
        return self.estah_concluida() and self.usuario_pode_deferir(
            user) and self.processo.esta_em_homologacao_juntada()

    def pode_juntar_documento(self, user):
        return self.estah_ativo() and self.solicitado == user.get_profile()

    def pode_cancelar_solicitacao(self, user=None):
        user = user or get_user()
        if self.estah_ativo() and not self.possui_solicitacoes_de_juntada_pendentes():
            return self.usuario_pode_cancelar(user)
        return False

    @transition(field=status, source=SolicitacaoJuntadaStatus.STATUS_CONCLUIDO,
                target=SolicitacaoJuntadaStatus.STATUS_FINALIZADO)
    def finalizar_solicitacao(self):
        pass

    @transition(field=status, source=SolicitacaoJuntadaStatus.STATUS_ESPERANDO,
                target=SolicitacaoJuntadaStatus.STATUS_CANCELADO)
    def cancelar_solicitacao(self, user, justificativa):
        self.justificativa_cancelamento = justificativa
        self.data_cancelamento = get_datetime_now()
        self.cancelada_por = user.get_profile().pessoa_ptr
        self.save()
        #

        # TODO - CANCELAR SOL JUNTADA - substituir pelo ataualizar_status_processo
        # self.processo.cancelar_juntada_documento()

        self.processo.save()

    @transition(field=status, source=SolicitacaoJuntadaStatus.STATUS_ESPERANDO,
                target=SolicitacaoJuntadaStatus.STATUS_EXPIRADO)
    def expirar_solicitacao(self):
        pass

    @transition(field=status, source=SolicitacaoJuntadaStatus.STATUS_ESPERANDO,
                target=SolicitacaoJuntadaStatus.STATUS_CONCLUIDO)
    def concluir_solicitacao(self):
        self.data_conclusao = get_datetime_now()

    def enviar_mail(self):
        titulo = '[SUAP] Solicitação de Juntada de Documento(s): Processo Eletrônico {}'.format(self.processo)
        texto = self.get_texto_solicitacao()
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.solicitado.get_vinculo()],
                          categoria='Processos Eletrônicos: Solicitação de Juntada de Documentos')

    def get_texto_solicitacao(self):
        texto_info_email = ''
        email_processo_eletronico = Configuracao.get_valor_por_chave('processo_eletronico', 'email_processo_eletronico')

        if email_processo_eletronico is not None:
            texto_info_email = ' ou entre em contato através do e-mail {}'.format(email_processo_eletronico)

        texto = """<h1>Solicitação de Juntada de Documento(s)</h1>
           <h2>Processo Eletrônico {0}</h2>
           <dl>
              <dt>Data:</dt><dd>{1}</dd>
              <dt>Assunto:</dt><dd>{2}</dd>
              <dt>Interessado(s):</dt><dd>{3}</dd>
              <dt>Solicitante:</dt><dd>{4}</dd>
              <dt>Motivação:</dt><dd>{5}</dd>
              <dt>Data Limite:</dt><dd>{6}</dd>
           </dl>
           <p>--</p>
           <p>Para mais informações, acesse:
               <a href="{7}/admin/processo_eletronico/processo/?opcao=6">
                   {7}/admin/processo_eletronico/processo/?opcao=6
               </a>{8}.
           </p>
           """.format(
            self.processo,
            self.data_solicitacao.strftime('%d/%m/%Y %H:%M'),
            self.processo.assunto,
            self.processo.get_interessados(),
            self.solicitante,
            self.motivo,
            self.data_limite,
            settings.SITE_URL,
            texto_info_email,
        )
        return texto

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.tramite.processo.aguardar_juntada_documento()
            self.tramite.processo.save()
        #
        if self.old_status != self.status:
            self.processo.save()
        super().save(*args, **kwargs)
        self.old_status = self.status


class SolicitacaoJuntadaDocumento(models.ModelPlus):
    solicitacao_juntada = models.ForeignKeyPlus(SolicitacaoJuntada)
    status = FSMIntegerField(default=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO,
                             choices=SolicitacaoJuntadaDocumentoStatus.STATUS_CHOICES, protected=True)
    # Motivação do pedido da juntada
    motivo = models.TextField('Motivação da Juntada', blank=True, null=True)
    # Texto relativo a analise de deferimento
    parecer = models.TextField('Parecer da Avaliação', blank=True, null=True)
    data_pedido = models.DateTimeField(auto_now_add=True)

    avaliado_por = models.ForeignKeyPlus('rh.PessoaFisica', related_name="%(app_label)s_%(class)s_avaliado_por",
                                         blank=True, null=True)
    avaliado_em = models.DateTimeField(null=True)

    anexo_limit_choices = models.Q(app_label='documento_eletronico', model='DocumentoTexto') | models.Q(
        app_label='documento_eletronico', model='DocumentoDigitalizado')

    anexo_content_type = models.ForeignKeyPlus(ContentType, verbose_name='Anexo', limit_choices_to=anexo_limit_choices,
                                               null=True, blank=True, on_delete=models.CASCADE)
    anexo_content_id = models.PositiveIntegerField(verbose_name='Anexo Object ID', null=True)
    anexo_content_object = GenericForeignKey('anexo_content_type', 'anexo_content_id')

    class Meta:
        ordering = ['-data_pedido']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_status = self.status

    @property
    def processo(self):
        return self.solicitacao_juntada.processo

    @property
    def documento(self):
        return self.anexo_content_object

    def esta_esperando(self):
        return self.status == SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO

    def get_documento_url(self):
        return self.anexo_content_object.get_absolute_url()

    def pode_remover(self):
        return self.solicitacao_juntada.estah_ativo()

    def pode_deferir_documento(self, user=None):
        return self.solicitacao_juntada.pode_deferir_documento(user) and self.esta_esperando()

    @transition(
        field=status,
        source=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO,
        target=SolicitacaoJuntadaDocumentoStatus.STATUS_DEFERIDO,
        on_error=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO,
    )
    def deferir_solicitacao_juntada_documento(self, user, justificativa=None):
        hoje = datetime.now()
        self.avaliado_por = user.get_profile()
        self.parecer = justificativa
        self.avaliado_em = hoje

        if ContentType.objects.get_for_model(DocumentoTexto) == self.anexo_content_type:
            self.processo.adicionar_documento_texto(self.anexo_content_object)
        elif ContentType.objects.get_for_model(DocumentoDigitalizado) == self.anexo_content_type:
            # A pessoa compartilhada sera quem defiriu
            pessoas_compartilhadas = [tl.get_user().get_profile()]
            self.processo.adicionar_documento_digitalizado(self.anexo_content_object,
                                                           self.solicitacao_juntada.solicitante, pessoas_compartilhadas)
        else:
            raise ValidationError("O tipo do anexo não foi reconhecido.")

    @transition(
        field=status,
        source=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO,
        target=SolicitacaoJuntadaDocumentoStatus.STATUS_INDEFERIDO,
        on_error=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO,
    )
    def indeferir_solicitacao_juntada_documento(self, user, justificativa):
        self.avaliado_por = user.get_profile()
        self.parecer = justificativa

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.old_status = self.status


class LogCommandProcessoEletronico(models.ModelPlus):
    dt_ini_execucao = models.DateTimeFieldPlus('Início da execução', null=True, blank=True)
    dt_fim_execucao = models.DateTimeFieldPlus('Fim da execução', null=True, blank=True)
    sucesso = models.BooleanField('Sucesso', default=False)
    log = models.TextField('Log de altração de status', blank=True, null=True)
    log_erro = models.TextField('Log de erro', blank=True, null=True)
    comando = models.CharFieldPlus('Comando', max_length=255)

    def __str__(self):
        return self.comando


class NumerosProcessoEletronicoPorSetor(models.ModelPlus):
    setor = models.ForeignKeyPlus('rh.Setor', null=True, blank=True, verbose_name="Setor", on_delete=models.CASCADE)

    criou = models.PositiveIntegerField('Criou', null=True, blank=True)
    tramitou = models.PositiveIntegerField('Criou', null=True, blank=True)

    class History:
        disabled = True


class NumerosProcessoEletronicoPorTipo(models.ModelPlus):
    tipo = models.ForeignKeyPlus(TipoProcesso, null=True, blank=True, verbose_name="Tipo", on_delete=models.CASCADE)

    qtd = models.PositiveIntegerField('Criou', null=True, blank=True)

    class History:
        disabled = True


class NumerosProcessoEletronicoGeral(models.ModelPlus):
    qtd_processos = models.PositiveIntegerField('Qtd Processos', null=True, blank=True)

    STATUS_ATIVO = models.PositiveIntegerField('Em trâmite', null=True, blank=True)
    STATUS_ARQUIVADO = models.PositiveIntegerField('Arquivado', null=True, blank=True)
    STATUS_SOBRESTADO = models.PositiveIntegerField('Sobrestado', null=True, blank=True)
    STATUS_FINALIZADO = models.PositiveIntegerField('Finalizado', null=True, blank=True)
    STATUS_ANEXADO = models.PositiveIntegerField('Anexado', null=True, blank=True)
    STATUS_REABERTO = models.PositiveIntegerField('Reaberto', null=True, blank=True)
    STATUS_AGUARDANDO_CIENCIA = models.PositiveIntegerField('Aguardando ciência', null=True, blank=True)
    STATUS_AGUARDANDO_JUNTADA = models.PositiveIntegerField('Aguardando juntada de documentos', null=True, blank=True)
    STATUS_EM_HOMOLOGACAO = models.PositiveIntegerField('Em validação de juntada de documentos', null=True, blank=True)

    qtd_documentos_texto = models.PositiveIntegerField('Qtd Documentos', null=True, blank=True)
    qtd_documentos_digitalizado = models.PositiveIntegerField('Qtd Documentos', null=True, blank=True)

    class History:
        disabled = True


class NumerosProcessoEletronicoTempoPorTipo(models.ModelPlus):
    uo_origem_interessado = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Origem')
    tipo = models.ForeignKeyPlus(TipoProcesso, null=True, blank=True, verbose_name="Tipo", on_delete=models.CASCADE)
    tempo_medio = models.PositiveIntegerField('Tempo Médio', null=True, blank=True)
    qtd = models.PositiveIntegerField('Quantidade', null=True, blank=True)

    class History:
        disabled = True


class CompartilhamentoProcessoEletronicoSetorPessoa(models.ModelPlus):
    setor_dono = models.ForeignKeyPlus('rh.Setor',
                                       related_name='compartilhamentoprocessoeletronicosetorpessoa_setor_dono_set')

    pessoa_permitida = models.ForeignKeyPlus(
        'rh.Pessoa', verbose_name='Pessoa Colaboradora', null=True,
        related_name='compartilhamentoprocessoeletronicosetorpessoa_pessoa_permitida_set'
    )
    nivel_permissao = models.PositiveIntegerField('Permissão de Acesso', choices=Processo.PERMISSAO_PROCESSO_CHOICES)

    data_criacao = models.DateTimeFieldPlus('Data de Criação', editable=False, null=True, blank=True)
    usuario_criacao = models.ForeignKeyPlus(
        User, verbose_name='Usuário de Criação', editable=False, null=True, blank=True,
        related_name='compartilhamentoprocessoeletronicosetorpessoa_usuario_criacao_set'
    )

    class Meta:
        verbose_name = 'Configuração de Compartilhamento de Processos Eletrônicos entre Setor e Pessoas'
        verbose_name_plural = 'Configurações de Compartilhamento de Processos Eletrônicos entre Setores e Pessoas'

    def __str__(self):
        try:
            nome_permissao = Processo.PERMISSAO_PROCESSO_CHOICES[self.nivel_permissao - 1][1]
        except IndexError:
            nome_permissao = Processo.PERMISSAO_PROCESSO_CHOICES[self.nivel_permissao - 2][1]
        return 'Compartilhamento do setor {} com a pessoa {} com permissão de {}'.format(
            self.setor_dono, self.pessoa_permitida, nome_permissao
        )

    def save(self, *args, **kwargs):
        log = CompartilhamentoProcessoEletronicoLog()
        log.setor_dono = self.setor_dono
        log.pessoa_permitida = self.pessoa_permitida
        log.data_criacao = datetime.today()
        log.usuario_criacao = self.usuario_criacao
        log.nivel_permissao = self.nivel_permissao
        log.operacao = CompartilhamentoProcessoEletronicoLog.OPERACAO_ADICAO
        log.save()
        super().save(*args, **kwargs)

    def delete(self):
        log = CompartilhamentoProcessoEletronicoLog()
        log.setor_dono = self.setor_dono
        log.pessoa_permitida = self.pessoa_permitida
        log.data_criacao = datetime.today()
        log.usuario_criacao = self.usuario_criacao
        log.nivel_permissao = self.nivel_permissao
        log.operacao = CompartilhamentoProcessoEletronicoLog.OPERACAO_EXCLUSAO
        log.save()
        super().delete()


class CompartilhamentoProcessoEletronicoSetorSetor(models.ModelPlus):
    setor_dono = models.ForeignKeyPlus('rh.Setor',
                                       related_name='compartilhamentoprocessoeletronicosetorsetor_setor_dono_set')

    setor_permitido = models.ForeignKeyPlus(
        'rh.Setor', verbose_name='Setor Colaborador', null=True,
        related_name='compartilhamentoprocessoeletronicosetorsetor_setor_permitido_set'
    )
    nivel_permissao = models.PositiveIntegerField('Permissão de Acesso', choices=Processo.PERMISSAO_PROCESSO_CHOICES)

    data_criacao = models.DateTimeFieldPlus('Data de Criação', editable=False, null=True, blank=True)
    usuario_criacao = models.ForeignKeyPlus(
        User, verbose_name='Usuário de Criação', editable=False, null=True, blank=True,
        related_name='compartilhamentoprocessoeletronicosetorsetor_setor_dono_set'
    )

    class Meta:
        verbose_name = 'Configuração de Compartilhamento de Processos Eletrônicos entre Setores'
        verbose_name_plural = 'Configurações de Compartilhamento de Processos Eletrônicos entre Setores'

    def __str__(self):
        return 'Compartilhamento do setor {} com o setor {} com permissão de {}'.format(
            self.setor_dono, self.setor_permitido, Processo.PERMISSAO_PROCESSO_CHOICES[self.nivel_permissao - 1][1]
        )

    def save(self, *args, **kwargs):
        log = CompartilhamentoProcessoEletronicoLog()
        log.setor_dono = self.setor_dono
        log.setor_permitido = self.setor_permitido
        log.data_criacao = datetime.today()
        log.usuario_criacao = self.usuario_criacao
        log.nivel_permissao = self.nivel_permissao
        log.operacao = CompartilhamentoProcessoEletronicoLog.OPERACAO_ADICAO
        log.save()
        super().save(*args, **kwargs)

    def delete(self):
        log = CompartilhamentoProcessoEletronicoLog()
        log.setor_dono = self.setor_dono
        log.setor_permitido = self.setor_permitido
        log.data_criacao = datetime.today()
        log.usuario_criacao = self.usuario_criacao
        log.nivel_permissao = self.nivel_permissao
        log.operacao = CompartilhamentoProcessoEletronicoLog.OPERACAO_EXCLUSAO
        log.save()
        super().delete()


def atualizar_compartilhamento_poder_chefe(sender, **kwargs):
    instance = kwargs['instance']
    if isinstance(instance, ServidorFuncaoHistorico):
        if instance.setor_suap:
            CompartilhamentoProcessoEletronicoPoderDeChefe.objects.filter(setor_dono=instance.setor_suap,
                                                                          de_oficio=True).delete()
            pessoas = []
            for chefe in instance.setor_suap.chefes:
                pessoas.append(chefe.pessoafisica_ptr)
                CompartilhamentoProcessoEletronicoPoderDeChefe.objects.get_or_create(setor_dono=instance.setor_suap, pessoa_permitida=chefe.pessoafisica_ptr, de_oficio=True)
            # if pessoas:
            #    CompartilhamentoProcessoEletronicoPoderDeChefe.objects.filter(setor_dono=instance.setor_suap, de_oficio=True).exclude(pessoa_permitida__in=pessoas).delete()


models.signals.post_save.connect(atualizar_compartilhamento_poder_chefe,
                                 sender=ServidorFuncaoHistorico)


class CompartilhamentoProcessoEletronicoPoderDeChefe(models.ModelPlus):
    setor_dono = models.ForeignKeyPlus('rh.Setor',
                                       related_name='compartilhamentoprocessoeletronicopoderchefe_setor_dono_set')

    pessoa_permitida = models.ForeignKeyPlus(
        'rh.Pessoa', verbose_name='Pessoa com Poder de Chefe', null=True,
        related_name='compartilhamentoprocessoeletronicopoderchefe_pessoa_permitida_set'
    )

    data_criacao = models.DateTimeFieldPlus('Data de Criação', editable=False, null=True, blank=True)
    usuario_criacao = models.ForeignKeyPlus(
        User, verbose_name='Usuário de Criação', editable=False, null=True, blank=True,
        related_name='compartilhamentoprocessoeletronicopoderchefe_usuario_criacao_set'
    )
    de_oficio = models.BooleanField('Chefe de ofício?', default=False)

    class Meta:
        verbose_name = 'Configuração de Compartilhamento de Processos Eletrônicos com Poder de Chefe'
        verbose_name_plural = 'Configurações de Compartilhamento de Processos Eletrônicos com Poder de Chefe'
        permissions = (('pode_gerenciar_permissoes_do_setor', "Pode gerenciar permissoes do setor"),)

    def __str__(self):
        return 'Poder de chefe no setor {} para {}'.format(self.setor_dono, self.pessoa_permitida)

    def save(self, *args, **kwargs):
        log = CompartilhamentoProcessoEletronicoLog()
        log.setor_dono = self.setor_dono
        log.pessoa_permitida = self.pessoa_permitida
        log.data_criacao = datetime.today()
        log.usuario_criacao = self.usuario_criacao
        log.nivel_permissao = CompartilhamentoProcessoEletronicoLog.PERMISSAO_PODER_DE_CHEFE
        log.operacao = CompartilhamentoProcessoEletronicoLog.OPERACAO_ADICAO
        log.save()
        super().save(*args, **kwargs)

    def delete(self):
        log = CompartilhamentoProcessoEletronicoLog()
        log.setor_dono = self.setor_dono
        log.pessoa_permitida = self.pessoa_permitida
        log.data_criacao = datetime.today()
        log.usuario_criacao = self.usuario_criacao
        log.nivel_permissao = CompartilhamentoProcessoEletronicoLog.PERMISSAO_PODER_DE_CHEFE
        log.operacao = CompartilhamentoProcessoEletronicoLog.OPERACAO_EXCLUSAO
        log.save()
        super().delete()


class CompartilhamentoProcessoEletronicoLog(models.ModelPlus):
    OPERACAO_ADICAO = 1
    OPERACAO_EXCLUSAO = 2
    OPERACAO = [[OPERACAO_ADICAO, 'ADIÇÃO'], [OPERACAO_EXCLUSAO, 'EXCLUSÃO']]

    PERMISSAO_OPERAR_PROCESSO = 1
    PERMISSAO_OPERAR_CRIAR_PROCESSO = 2
    PERMISSAO_PODER_DE_CHEFE = 3
    PERMISSAO_RETORNO_PROGRAMADO = 4
    PERMISSAO_PROCESSO_CHOICES = [
        [PERMISSAO_OPERAR_PROCESSO, 'Permissão para Operar Processos Eletrônicos'],
        # Corresponde ao grupo Tramitador de Processos Eletrônicos
        [PERMISSAO_OPERAR_CRIAR_PROCESSO, 'Permissão para Criar e Operar Processos Eletrônicos'],
        # Corresponde ao grupo Operador de Processo Eletrônico
        [PERMISSAO_PODER_DE_CHEFE, 'Poder de chefe nos Processos Eletrônicos'],
        [PERMISSAO_RETORNO_PROGRAMADO,
         'Permissão para cadastrar Retorno Programado nos trâmites de Processos Eletrônicos'],
    ]

    setor_dono = models.ForeignKeyPlus('rh.Setor', related_name='compartilhamentoprocessoeletronicolog_setor_dono_set')

    setor_permitido = models.ForeignKeyPlus('rh.Setor', verbose_name='Setor Colaborador', null=True,
                                            related_name='compartilhamentoprocessoeletronicolog_setor_permitido_set')
    pessoa_permitida = models.ForeignKeyPlus(
        'rh.Pessoa', verbose_name='Pessoa com Poder de Chefe', null=True,
        related_name='compartilhamentoprocessoeletronicolog_pessoa_permitida_set'
    )

    data_criacao = models.DateTimeFieldPlus('Data de Criação', editable=False)
    usuario_criacao = models.ForeignKeyPlus(
        User, verbose_name='Usuário de Criação', editable=False,
        related_name='compartilhamentoprocessoeletronicolog_usuario_criacao_set', null=True, blank=True
    )

    nivel_permissao = models.PositiveIntegerField('Permissão de Acesso', choices=PERMISSAO_PROCESSO_CHOICES)

    operacao = models.PositiveIntegerField('Permissão de Acesso', choices=OPERACAO)

    class Meta:
        verbose_name = 'Log de Compartilhamento de Processos Eletrônicos'
        verbose_name_plural = 'Log de Compartilhamento de Processos Eletrônicos'

    def __str__(self):
        setor_pessoa = 'o setor "{}"'.format(self.setor_permitido) if (
            self.setor_permitido) else 'a pessoa "{}"'.format(self.pessoa_permitida)
        permissao_operacao = (
            'adicionada a permissão de "{}"'.format(self.PERMISSAO_PROCESSO_CHOICES[self.nivel_permissao - 1][1])
            if (self.operacao == self.OPERACAO_ADICAO)
            else 'excluída a permissão de {}'.format(self.PERMISSAO_PROCESSO_CHOICES[self.nivel_permissao - 1][1])
        )
        return 'Foi {} em {} por "{}" para {}'.format(permissao_operacao, self.data_criacao, self.usuario_criacao,
                                                      setor_pessoa)


class TramiteDistribuicao(models.ModelPlus):
    setor = models.ForeignKey('rh.Setor', verbose_name="Setor", related_name='setor_tramite_distribuicao',
                              on_delete=models.CASCADE)
    pessoa_para_distribuir = models.ForeignKey('rh.PessoaFisica', verbose_name="Distribuir para",
                                               related_name='atribuir_tramite_para', on_delete=models.CASCADE)
    tipos_processos_atendidos = models.ManyToManyFieldPlus(
        'processo_eletronico.TipoProcesso', related_name='tipos_processos_atendidos',
        verbose_name='Tipos de Processo Para Receber', blank=True
    )

    class Meta:
        verbose_name = 'Distribuição de Trâmite'
        verbose_name_plural = 'Distribuição dos Trâmites por Tipo de Processo'

    def pode_excluir(self, user=None):
        if not user:
            user = tl.get_user()
        if self.setor in setores_que_sou_chefe_ou_tenho_poder_de_chefe(user):
            return True
        return False

    def pode_ver(self, user=None):
        if not user:
            user = tl.get_user()
        if self.setor in setores_que_sou_chefe_ou_tenho_poder_de_chefe(user):
            return True
        return False

    def get_absolute_url(self):
        return '/admin/processo_eletronico/tramitedistribuicao/{}/'.format(self.id)


class TramiteRetornoProgramado(models.ModelPlus):
    tramite_gerador = models.OneToOneFieldPlus('Tramite', verbose_name='Trâmite Gerador do Retorno',
                                               related_name='tramite_gerador', null=False)
    data_prevista_retorno = models.DateFieldPlus('Data de Retorno', null=False)
    data_efetiva_retorno = models.DateFieldPlus('Data Efetiva do Retorno', null=True)
    tramite_retorno = models.OneToOneFieldPlus('Tramite', verbose_name='Trâmite Solicitante do Retorno',
                                               related_name='tramite_retorno', null=True)

    class Meta:
        verbose_name = 'Retorno Programado'
        verbose_name_plural = 'Retornos Programados'


class ConfiguracaoInstrucaoNivelAcesso(models.ModelPlus):

    orientacao = models.TextField('Orientação', blank=True, null=True)
    ativo = models.BooleanField('Ativo?', default=True, help_text='Se estiver ativa será exibida para o usuário no momento da definição/alteração do nível de acesso.')

    class Meta:
        verbose_name = 'Instrução sobre Nível de Acesso'
        verbose_name_plural = 'Instrução sobre Nível de Acesso'

    @staticmethod
    def get_orientacao():
        conf = ConfiguracaoInstrucaoNivelAcesso.objects.filter(orientacao__isnull=False, ativo=True)
        if conf:
            return conf[0].orientacao
        return None


class SolicitacaoAlteracaoNivelAcesso(models.ModelPlus):

    # processo
    processo = models.ForeignKeyPlus('processo_eletronico.Processo', null=True, related_name='processo_analise_nivel_acesso_set')
    # documento_digitalizado
    documento_digitalizado = models.ForeignKeyPlus('documento_eletronico.DocumentoDigitalizado',
                                                   verbose_name='Documento Digitalizado', null=True, related_name='documentodigitalizado_analise_nivel_acesso_set')
    # documento_texto
    documento_texto = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento de Texto', null=True, related_name='documentotexto_analise_nivel_acesso_set')

    # quem solicitou
    data_hora_solicitacao = models.DateTimeFieldPlus('Data de Criação', auto_now_add=True)
    # quando solicitou
    usuario_solicitante = models.CurrentUserField(verbose_name='Usuário de Criação')
    # pq solicitou
    descricao = models.TextField('Descrição')

    """
    nivel de acesso - processo
    NIVEL_ACESSO_PUBLICO = 1
    NIVEL_ACESSO_RESTRITO = 2
    NIVEL_ACESSO_PRIVADO = 3
    nivel de acesso - documento
    NIVEL_ACESSO_SIGILOSO = 1
    NIVEL_ACESSO_RESTRITO = 2
    NIVEL_ACESSO_PUBLICO = 3
    """

    de_nivel_acesso = models.PositiveIntegerField(verbose_name='De')
    para_nivel_acesso = models.PositiveIntegerField(verbose_name='Para')
    hipotese_legal = models.ForeignKeyPlus('documento_eletronico.HipoteseLegal', verbose_name='Hipótese Legal', null=True)

    # quem analisou
    usuario_analise = models.ForeignKeyPlus('comum.User', related_name='usuario_analise_nivel_acesso_set', editable=False,
                                            null=True, on_delete=models.CASCADE)
    # quando analisou
    data_analise = models.DateTimeFieldPlus(editable=False, null=True)

    # deferido
    SITUACAO_SOLICITADO = 1
    SITUACAO_DEFERIDO = 2
    SITUACAO_INDEFERIDO = 3
    SITUACAO_CHOICES = [[SITUACAO_SOLICITADO, 'Solicitado'],
                        [SITUACAO_DEFERIDO, 'Deferido'],
                        [SITUACAO_INDEFERIDO, 'Indeferido']]
    situacao = models.PositiveIntegerField('Situacao',
                                           choices=SITUACAO_CHOICES,
                                           default=SITUACAO_SOLICITADO)

    # Para os casos em que esta solicitação fo deferida em lote por outra solicitação (verifica na view "analisar_solicitacao_alteracao_nivel_acesso")
    # - Indica qual demanda provocou o deferimento
    deferido_pela_solicitacao = models.ForeignKeyPlus('processo_eletronico.SolicitacaoAlteracaoNivelAcesso',
                                                      verbose_name='Deferido pela solicitação', editable=False, null=True,
                                                      on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Solicitação de Alteração de Nível de Acesso'
        verbose_name_plural = 'Solicitações de Alteração de Nível de Acesso'

    def __str__(self):
        return 'Solicitação de alteração cadastrada por {} em {}'.format(self.usuario_solicitante, self.data_hora_solicitacao)

    def get_choice_nivel_acesso(self):
        if self.processo:
            return Processo.NIVEL_ACESSO_CHOICES
        elif self.documento_digitalizado or self.documento_texto:
            return Documento.NIVEL_ACESSO_CHOICES
        return None

    def get_de_nivel_acesso(self):
        choices = self.get_choice_nivel_acesso()
        for na in choices:
            if na[0] == self.de_nivel_acesso:
                return na
        return None

    def get_para_nivel_acesso(self):
        choices = self.get_choice_nivel_acesso()
        for na in choices:
            if na[0] == self.para_nivel_acesso:
                return na
        return None

    def get_nivel_acesso_de(self):
        return self.get_nivel_acesso_de()

    def get_documento_processo(self):
        return self.processo or self.documento_digitalizado or self.documento_texto

    @staticmethod
    def get_documento_processo_por_tipo_id(obj_tipo_str, obj_id):
        try:
            if obj_tipo_str == 'processo':
                return Processo.objects.get(id=obj_id)
            elif obj_tipo_str == 'documento_texto':
                return DocumentoTexto.objects.get(id=obj_id)
            elif obj_tipo_str == 'documento_digitalizado':
                return DocumentoDigitalizado.objects.get(id=obj_id)
            else:
                return None
        except Exception:
            return None

    def get_tipo_documento_processo_str(self):
        if self.processo:
            return 'processo'
        elif self.documento_digitalizado:
            return 'documento_digitalizado'
        else:
            return 'documento_texto'
        return None

    def get_tipo_documento_processo_int(self):
        if self.processo:
            return 3
        elif self.documento_digitalizado:
            return 2
        elif self.documento_texto:
            return 1
        else:
            return None

    def eh_processo(self):
        if self.processo:
            return True
        else:
            return False

    def eh_documento_digitalizado(self):
        if self.documento_digitalizado:
            return True
        else:
            return False

    def eh_documento_texto(self):
        if self.documento_texto:
            return True
        else:
            return False

    def listar_solicitacoes_nivel_acesso_aberto(self):
        return self.get_documento_processo().listar_solicitacoes_nivel_acesso_aberto()

    def existe_solicitacoes_nivel_acesso_aberto(self):
        return self.listar_solicitacoes_nivel_acesso_aberto().exists()

    def get_solicitacoes_iguais_em_aberto(self):
        lista_solicitacoes = SolicitacaoAlteracaoNivelAcesso.objects.filter(situacao=SolicitacaoAlteracaoNivelAcesso.SITUACAO_SOLICITADO)

        lista_solicitacoes = lista_solicitacoes.exclude(id=self.id)

        if self.processo:
            lista_solicitacoes = lista_solicitacoes.filter(processo__id=self.processo.id)
        elif self.documento_digitalizado:
            lista_solicitacoes = lista_solicitacoes.filter(documento_digitalizado__id=self.documento_digitalizado.id)
        else:
            lista_solicitacoes = lista_solicitacoes.filter(documento_texto__id=self.documento_texto.id)

        lista_solicitacoes = lista_solicitacoes.filter(para_nivel_acesso=self.para_nivel_acesso)

        return lista_solicitacoes

    @staticmethod
    def get_hipoteses_legais_by_processo_documento_nivel_acesso(documento_processo, documento_processo_nivel_acesso_id):
        # documento_processo
        # 1 = documento_texto
        # 2 = documento_digitalizado
        # 3 = processo
        documento_processo_nivel_acesso_id = int(documento_processo_nivel_acesso_id)
        nivel_acesso = None

        if documento_processo == 3:
            if documento_processo_nivel_acesso_id == Processo.NIVEL_ACESSO_PRIVADO:
                nivel_acesso = NivelAcessoEnum.SIGILOSO
            elif documento_processo_nivel_acesso_id == Processo.NIVEL_ACESSO_RESTRITO:
                nivel_acesso = NivelAcessoEnum.RESTRITO
            if nivel_acesso:
                return HipoteseLegal.objects.filter(nivel_acesso=nivel_acesso.name)

        if documento_processo in (1, 2):
            if documento_processo_nivel_acesso_id == Documento.NIVEL_ACESSO_SIGILOSO:
                nivel_acesso = NivelAcessoEnum.SIGILOSO
            elif documento_processo_nivel_acesso_id == Documento.NIVEL_ACESSO_RESTRITO:
                nivel_acesso = NivelAcessoEnum.RESTRITO

        if nivel_acesso:
            return HipoteseLegal.objects.filter(nivel_acesso=nivel_acesso.name)

        return None

    @staticmethod
    def qtd_solicitacoes_em_aberto_que_posso_analisar(user):
        lista_solicitacoes = SolicitacaoAlteracaoNivelAcesso.objects.filter(
            situacao=SolicitacaoAlteracaoNivelAcesso.SITUACAO_SOLICITADO)
        qtd = 0
        for sol in lista_solicitacoes:
            if sol.get_documento_processo().pode_alterar_nivel_acesso(user=user):
                qtd += 1
        return qtd

    @transaction.atomic()
    def deferir(self, user, ip, destinatario_setor=None, pessoas_compartilhadas=None):
        object = self.get_documento_processo()
        self.usuario_analise = user
        self.data_analise = datetime.now()
        self.situacao = SolicitacaoAlteracaoNivelAcesso.SITUACAO_DEFERIDO
        kwargs = dict(
            novo_nivel_acesso=self.para_nivel_acesso,
            nova_hipotese_legal=self.hipotese_legal,
            user=user,
            ip=ip,
            justificativa=self.hipotese_legal
        )
        if self.eh_processo():
            object.alterar_nivel_acesso(destinatario_setor=destinatario_setor, **kwargs)
        else:
            if object.eh_documento_digitalizado:
                kwargs['pessoas_compartilhadas'] = pessoas_compartilhadas
            #
            object.alterar_nivel_acesso(**kwargs)

        self.save()

    #
    def indeferir(self, user, justificativa):
        self.usuario_analise = user
        self.data_analise = datetime.now()
        self.situacao = SolicitacaoAlteracaoNivelAcesso.SITUACAO_INDEFERIDO
        self.justificativa = justificativa
        self.save()
