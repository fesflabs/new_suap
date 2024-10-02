import base64
import calendar
import collections
import hashlib
import io
import os
import re
import urllib
import uuid
from datetime import datetime, timedelta, date
from django.db.models import Sum

import magic
import qrcode
import user_agents
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import user_login_failed, user_logged_in, user_logged_out
from django.contrib.auth.models import Group, AbstractUser, AnonymousUser
from django.contrib.auth.models import UserManager
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError
from django.db.models.query_utils import Q
from django.db.transaction import atomic
from django.dispatch import receiver
from django.http import HttpResponse
from django.template.defaultfilters import truncatechars
from django.urls import reverse_lazy
from django_extensions.db.fields import AutoSlugField
from sentry_sdk import capture_exception

from comum import signer
from comum.utils import tl, daterange, adicionar_mes, get_uo, FLAG_LOG_GERENCIAMENTO_GRUPO, \
    registrar_inclusao_remocao_grupo, registrar_remocao_grupo, registrar_adicao_grupo
from djtools.choices import SituacaoSolicitacaoDocumento
from djtools.db import models
from djtools.db.models import CurrentUserField, DateFieldPlus
from djtools.db.models import ModelPlus
from djtools.html.calendarios import CalendarioPlus
from djtools.storages.utils import download_media_content, get_overwrite_storage, cache_file
from djtools.utils import to_ascii, mask_cep, send_mail, send_notification, normalizar_nome_proprio, \
    get_client_ip, b64encode, b64decode, render_from_string, getattr_coalesce, decrypt
from rh.enums import Nacionalidade
from rh.models import Setor, UnidadeOrganizacional, PessoaFisica, Servidor, Funcionario, Pessoa, Papel, Funcao, \
    PessoaExterna

try:
    from collections.abc import Iterable
except ImportError:  # Python 2.7 compatibility
    from collections import Iterable

Group._meta.ordering = ['name']


class Publico(ModelPlus):
    TIPO_SETOR_SUAP = 'setor_suap'
    TIPO_SETOR_FUNCAO_SIAPE = 'setor_funcao'
    TIPO_SETOR_LOTACAO_SIAPE = 'setor_lotacao'
    TIPO_SETOR_CHOICES = ((TIPO_SETOR_SUAP, 'Setor SUAP'), (TIPO_SETOR_FUNCAO_SIAPE, 'Setor da Função SIAPE'), (TIPO_SETOR_LOTACAO_SIAPE, 'Setor de Lotação SIAPE'))

    BASE_FUNCIONARIO = 'Funcionario'
    BASE_SERVIDOR = 'Servidor'
    BASE_ALUNO = 'Aluno'
    BASE_PRESTADORSERVICO = 'PrestadorServico'
    BASE_CHOICES = ((BASE_FUNCIONARIO, BASE_FUNCIONARIO), (BASE_SERVIDOR, BASE_SERVIDOR), (BASE_ALUNO, BASE_ALUNO), (BASE_PRESTADORSERVICO, BASE_PRESTADORSERVICO))

    nome = models.CharFieldPlus('Nome')
    modelo_base = models.CharFieldPlus('Modelo base', choices=BASE_CHOICES)
    manager_base = models.CharFieldPlus('Manager base', default='objects')
    filtro = models.TextField('Filtro', blank=True, help_text='Informe os parâmetros para filtro dos modelos em formato json.')
    filtro_exclusao = models.TextField('Filtro de Exclusão', blank=True, help_text='Informe os parâmetros para filtro de exclusão dos modelos em formato json.')

    class Meta:
        verbose_name = 'Público'
        verbose_name_plural = 'Públicos'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def get_queryset(self):
        import json

        try:
            qs = getattr(self.get_classe_modelo(), self.manager_base)
        except AttributeError:
            qs = getattr(self.get_classe_modelo(), 'objects')
            qs = getattr(qs, self.manager_base)()

        if self.filtro:
            filtro = json.loads(self.filtro)
            qs = qs.filter(**filtro)

        if self.filtro_exclusao:
            filtro_exclusao = json.loads(self.filtro_exclusao)
            qs = qs.exclude(**filtro_exclusao)

        return qs.distinct()

    def q_filter_queryset(self, campi, tipo_setor=None):
        campi_ids = campi.values_list('id', flat=True)
        if self.modelo_base == self.BASE_ALUNO:
            return Q(curso_campus__diretoria__setor__uo__id__in=campi_ids)
        else:
            if tipo_setor == self.TIPO_SETOR_SUAP:
                return Q(setor__uo__id__in=campi_ids)
            elif tipo_setor == self.TIPO_SETOR_FUNCAO_SIAPE:
                return Q(setor_funcao__uo__equivalente__id__in=campi_ids)
            else:
                return Q(setor_lotacao__uo__equivalente__id__in=campi_ids)

    def get_queryset_vinculo(self, campi=None, tipo_setor=None):
        ids = []
        resultado = self.get_queryset().filter(self.q_filter_queryset(campi, tipo_setor))
        if resultado.exists():
            if hasattr(resultado[0], 'vinculo'):
                ids = resultado.values_list('vinculo__id', flat=True)
            elif hasattr(resultado[0], 'vinculos'):
                ids = resultado.values_list('vinculos__id', flat=True)
            else:
                lista_ids = list()
                for funcionario in resultado:
                    lista_ids.append(funcionario.get_vinculo().id)
                ids = lista_ids
        return Vinculo.objects.filter(id__in=ids).distinct()

    def get_classe_modelo(self):
        if self.modelo_base == self.BASE_FUNCIONARIO:
            from rh.models import Funcionario

            return Funcionario
        elif self.modelo_base == self.BASE_SERVIDOR:
            return Servidor
        elif self.modelo_base == self.BASE_ALUNO:
            from edu.models import Aluno

            return Aluno
        elif self.modelo_base == self.BASE_PRESTADORSERVICO:
            return PrestadorServico


class ConselhoProfissional(models.ModelPlus):
    nome = models.CharFieldPlus('Nome do Conselho', max_length=100)
    sigla = models.CharFieldPlus('Sigla do Conselho', max_length=10)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Conselho Profissional'
        verbose_name_plural = 'Conselhos Profissionais'

    def __str__(self):
        return '{} ({})'.format(self.nome, self.sigla)


class AreaAtuacao(models.ModelPlus):
    nome = models.CharFieldPlus('Nome', max_length=120, unique=True, help_text='Informe um nome para a área de atuação')
    slug = AutoSlugField('Slug', max_length=120, unique=True, populate_from=('nome',))
    icone = models.CharFieldPlus(
        'Ícone', max_length=80, blank=True, default='list', help_text='Informe um ícone para representar esta Área de Atuação. Fonte: https://fontawesome.com/'
    )
    ativo = models.BooleanField('Ativo?', default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Área de Atuação'
        verbose_name_plural = 'Áreas de Atuação'

    def __str__(self):
        return self.nome


class UserManager(UserManager):
    def superusers(self):
        return self.filter(is_superuser=True)

    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)


class User(AbstractUser):
    login_attempts = models.IntegerField('Tentativas de Login', default=0)
    SEARCH_FIELDS = ['pessoafisica__search_fields_optimized']

    eh_servidor = models.BooleanField(default=False)
    eh_aluno = models.BooleanField(default=False)
    eh_residente = models.BooleanField(default=False)
    eh_trabalhadoreducando = models.BooleanField(default=False)
    eh_prestador = models.BooleanField(default=False)
    eh_docente = models.BooleanField(default=False)
    eh_tecnico_administrativo = models.BooleanField(default=False)
    VINCULOS = {}
    PESSOAS_FISICAS = {}

    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    # objects = DefaultSelectOrPrefetchManager(select_related=('pessoafisica',))
    # objects = UserManager().select_related('pessoafisica')
    objects = UserManager()

    class History:
        blank_fields = ('password',)
        ignore_fields = ('login_attempts', 'last_login')

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        db_table = 'auth_user'

    def get_profile(self):
        pessoa_fisica = self.PESSOAS_FISICAS.get(self.id)
        if not pessoa_fisica:
            pessoa_fisica = PessoaFisica.objects.filter(user=self).first()
            self.PESSOAS_FISICAS[self.id] = pessoa_fisica
        return pessoa_fisica

    def get_vinculo(self):
        vinculo = self.VINCULOS.get(self.id)
        if not vinculo:
            vinculo = self.VINCULOS[self.id] = self.vinculo_set.first()
        return vinculo

    def get_tipo(self):
        if self.eh_servidor:
            if self.eh_docente:
                return "Servidor (Docente)"
            else:
                return "Servidor (Técnico-Administrativo)"
        elif self.eh_aluno:
            return "Aluno"
        elif self.eh_residente:
            return "Residente"
        elif self.eh_trabalhadoreducando:
            return "Trabalhador Educando"
        else:
            return "Prestador de Serviço"

    def reset_vinculo(self):
        try:
            del self.VINCULOS[self.id]
        except Exception:
            pass

    def reset_profile(self):
        try:
            del self.PESSOAS_FISICAS[self.id]
        except Exception:
            pass

    def get_relacionamento(self):
        try:
            return self.get_vinculo().relacionamento
        except AttributeError:
            return None

    def get_relacionamento_title(self):
        if not self.get_vinculo():
            return 'Usuário sem relacionamento'
        return self.get_vinculo().get_relacionamento_title()

    def tema_preferido(self):
        return self.preferencia and self.preferencia.tema != "" and self.preferencia.tema or Preferencia.PADRAO

    @property
    def eh_notificado_suap(self):
        return self.preferencia.via_suap if self.preferencia else True

    @property
    def eh_notificado_email(self):
        return self.preferencia.via_email if self.preferencia else True

    def tem_historico_grupos(self):
        return LogEntry.objects.filter(object_id=self.id, action_flag=FLAG_LOG_GERENCIAMENTO_GRUPO).exists()

    def eh_gerenciador_do_grupo(self, grupo):
        return (
            self.is_superuser or self.groups.filter(pk__in=list(GerenciamentoGrupo.objects.filter(grupos_gerenciados=grupo).values_list('grupo_gerenciador', flat=True))).exists()
        )

    def gerenciamento_do_grupo(self, grupo=None):
        gerenciamento_do_grupo = GerenciamentoGrupo.objects.all()
        if not grupo:
            if self.is_superuser:
                return gerenciamento_do_grupo
            return gerenciamento_do_grupo.filter(grupo_gerenciador__pk__in=self.groups.all().values_list('pk', flat=True))

        gerenciamento_do_grupo = gerenciamento_do_grupo.filter(grupos_gerenciados=grupo)
        if self.is_superuser:
            return gerenciamento_do_grupo
        return gerenciamento_do_grupo.filter(grupo_gerenciador__pk__in=self.groups.all().values_list('pk', flat=True))

    def has_group(self, group):
        if isinstance(group, str):
            group_list = [g.strip() for g in group.split(',')]
        elif isinstance(group, Iterable):
            group_list = [g.strip() for g in group]
        else:
            raise TypeError('The first parameter must be a basestring or an iterable')
        return self.groups.filter(name__in=group_list).exists() or self.is_superuser

    def get_groups(self, permission=None):
        if permission:
            app, permissao = permission.split('.')
            return self.groups.filter(permissions__content_type__app_label=app, permissions__codename=permissao)
        else:
            return self.groups.all()


AnonymousUser.has_group = lambda x, y: False


class CertificadoDigital(models.ModelPlus):
    user = models.ForeignKeyPlus(User, verbose_name='Usuário')
    arquivo = models.FileFieldPlus(verbose_name='Arquivo', upload_to='certificados_digitais')
    nome = models.CharFieldPlus(verbose_name='Nome')
    organizacao = models.CharFieldPlus(verbose_name='Organização')
    unidade = models.CharFieldPlus(verbose_name='Unidade Organizacional')
    validade = models.DateFieldPlus(verbose_name='Validade')
    conteudo = models.TextField('Conteúdo')

    class Meta:
        verbose_name = 'Certificado Digital'
        verbose_name_plural = 'Certificados Digitais'

    def __str__(self):
        return '{} - {} - (VÁLIDO ATÉ {})'.format(self.nome, self.organizacao, self.validade.strftime("%d/%m/%Y"))

    def assinar_arquivo_pdf(self, caminho_arquivo, senha, tipo_documento=None, codigo_autenticacao=None, adicionar_texto=False, titulo=None, adicionar_imagem=False, x=0, y=0, bgcolor='#EEEEEE', page=0):
        documento = cache_file(caminho_arquivo)
        local_filename = cache_file(self.arquivo.name)
        signed = signer.sign(
            local_filename, senha, documento, sign_img=adicionar_imagem, suffix='',
            bgcolor=bgcolor, x=x, y=y, document_type=tipo_documento, authentication_code=codigo_autenticacao, page=page, title=titulo
        )
        storage = get_overwrite_storage()
        with open(signed, 'rb') as f:
            storage.save(caminho_arquivo, f)

        if os.path.exists(local_filename):
            os.unlink(local_filename)

    def verificar_arquivo_pdf(self, caminho_arquivo):
        return signer.verify(caminho_arquivo, self.conteudo)


class Device(models.ModelPlus):
    user = models.ForeignKeyPlus(User, null=False, blank=False, verbose_name='Usuário')
    user_agent = models.TextField(null=False, blank=False, verbose_name='Agente do Dispositivo', db_index=True)
    nickname = models.CharFieldPlus('Apelido', blank=True, null=True, db_index=True)
    friendly_name = models.TextField(null=False, blank=False, verbose_name='Dispositivo', db_index=True)
    activated = models.BooleanField(default=True, verbose_name='Ativado')

    class History:
        disabled = True

    class Meta:
        unique_together = ('user', 'user_agent')
        verbose_name = 'Dispositivo'
        verbose_name_plural = 'Dispositivos'

    def get_name(self):
        if self.nickname:
            return self.nickname
        elif self.friendly_name:
            return self.friendly_name
        else:
            return self.user_agent

    def __str__(self):
        return f'Dispositivo: {self.get_name()}'


class SessionInfo(models.ModelPlus):
    session_id = models.TextField(null=False, blank=False, unique=True, verbose_name='Identificador da Sessão')
    device = models.ForeignKeyPlus('comum.Device')
    ip_address = models.TextField(null=False, blank=False, verbose_name='Endereço IP', db_index=True)
    date_time = models.DateTimeFieldPlus(auto_now_add=True, verbose_name='Horário do Login')
    expired = models.BooleanField(verbose_name='Expirada', default=False)

    class History:
        disabled = True

    class Meta:
        verbose_name = 'Informação de Sessão'
        verbose_name_plural = 'Informações de Sessões'

    def can_change(self, user):
        return False

    def __str__(self):
        return f'Sessão #{self.pk}'


class VinculoQueryset(models.QuerySet):
    def servidores(self):
        return self.filter(tipo_relacionamento__app_label='rh', tipo_relacionamento__model='servidor')

    def prestadores(self):
        return self.filter(tipo_relacionamento__app_label='comum', tipo_relacionamento__model='prestadorservico')

    def alunos(self):
        return self.filter(tipo_relacionamento__app_label='edu', tipo_relacionamento__model='aluno')

    def funcionarios(self):
        return self.servidores() | self.prestadores()

    def pessoas_externas(self):
        return self.filter(tipo_relacionamento__app_label='rh', tipo_relacionamento__model='pessoaexterna')

    def pessoas_fisicas(self):
        return self.funcionarios() | self.alunos()

    def pessoas_juridicas(self):
        return self.filter(tipo_relacionamento__app_label='rh', tipo_relacionamento__model='pessoajuridica')


class VinculoManager(models.Manager):
    def get_queryset(self):
        return VinculoQueryset(self.model, using=self._db)

    def servidores(self):
        return self.get_queryset().servidores()

    def servidores_tecnicos_administrativos(self):
        return self.servidores().filter(id_relacionamento__in=Servidor.objects.tecnicos_administrativos().values_list('id', flat=True))

    def servidores_docentes(self):
        return self.servidores().filter(id_relacionamento__in=Servidor.objects.docentes().values_list('id', flat=True))

    def prestadores(self):
        return self.get_queryset().prestadores()

    def alunos(self):
        return self.get_queryset().alunos()

    def pessoas_externas(self):
        return self.get_queryset().pessoas_externas()

    def pessoas_juridicas(self):
        return self.get_queryset().pessoas_juridicas()

    def funcionarios(self):
        return self.get_queryset().funcionarios()

    def funcionarios_ativos(self):
        return self.funcionarios().filter(pessoa__excluido=False)

    def pessoas_fisicas(self):
        return self.get_queryset().pessoas_fisicas()


class Vinculo(models.ModelPlus):
    SERVIDOR = Q(app_label='rh', model='servidor')
    PRESTADOR = Q(app_label='comum', model='prestadorservico')
    ALUNO = Q(app_label='edu', model='aluno')
    RESIDENTE = Q(app_label='residencia', model='residente')
    PESSOA_JURIDICA = Q(app_label='rh', model='pessoajuridica')
    PESSOA_EXTERNA = Q(app_label='rh', model='pessoaexterna')
    CHEFE_PPE = Q(app_label='ppe', model='chefiappe')

    ESCOLHAS_VINCULO = SERVIDOR | PRESTADOR | ALUNO | PESSOA_JURIDICA | PESSOA_EXTERNA | RESIDENTE | CHEFE_PPE

    SEARCH_FIELDS = ['search']

    user = models.ForeignKeyPlus('comum.User', verbose_name='Usuário', null=True, on_delete=models.CASCADE)
    pessoa = models.ForeignKeyPlus('rh.Pessoa', verbose_name='Pessoa', on_delete=models.CASCADE)
    setor = models.ForeignKeyPlus('rh.Setor', verbose_name='Setor', null=True, on_delete=models.SET_NULL)

    tipo_relacionamento = models.ForeignKeyPlus(
        ContentType, verbose_name='Tipo de Relacionamento', limit_choices_to=ESCOLHAS_VINCULO, null=False, blank=False, on_delete=models.CASCADE
    )

    id_relacionamento = models.PositiveIntegerField(verbose_name='Identificador do Relacionamento', null=False)
    relacionamento = GenericForeignKey('tipo_relacionamento', 'id_relacionamento')

    search = models.SearchField(attrs=['user.username', 'pessoa.nome', 'pessoa.pessoafisica.cpf', 'pessoa.pessoajuridica.cnpj'])

    objects = VinculoManager()

    class Meta:
        verbose_name = 'Vínculo'
        verbose_name_plural = 'Vínculos'
        unique_together = ('tipo_relacionamento', 'id_relacionamento')

    def __str__(self):
        return f'{self.relacionamento} ({type(self.relacionamento)._meta.verbose_name})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            del self.user.VINCULOS[self.user.id]
        except Exception:
            pass

    def eh_servidor(self):
        return self.tipo_relacionamento.model == 'servidor'

    def eh_prestador(self):
        return self.tipo_relacionamento.model == 'prestadorservico'

    def eh_usuario_externo(self):
        return self.eh_prestador() and self.relacionamento.usuario_externo

    def eh_chefia_imediata(self):
        return self.eh_prestador() and self.relacionamento.chefia_imediata

    def eh_funcionario(self):
        return self.eh_servidor() or self.eh_prestador()

    def eh_aluno(self):
        return self.tipo_relacionamento.model == 'aluno'

    def eh_residente(self):
        return self.tipo_relacionamento.model == 'residente'

    def eh_trabalhadoreducando(self):
        return self.tipo_relacionamento.model == 'trabalhadoreducando'

    def eh_pessoaexterna(self):
        return self.tipo_relacionamento.model == 'pessoaexterna'

    def eh_pessoajuridica(self):
        return self.tipo_relacionamento.model == 'pessoajuridica'

    def get_areas_tematicas_interesse(self):
        return ', '.join(self.areatematica_set.all().values_list('descricao', flat=True))

    def get_email(self):
        if self.eh_servidor():
            return self.relacionamento.email or self.relacionamento.email_secundario
        elif self.eh_prestador():
            return self.relacionamento.email_secundario
        elif self.eh_aluno() or self.eh_residente() or self.eh_trabalhadoreducando():
            if self.relacionamento.pessoa_fisica.email:
                return self.relacionamento.pessoa_fisica.email
            elif self.relacionamento.pessoa_fisica.email_secundario:
                return self.relacionamento.pessoa_fisica.email_secundario
            elif self.relacionamento.email_academico:
                return self.relacionamento.email_academico
        elif self.eh_pessoajuridica():
            return self.relacionamento.email
        elif self.eh_pessoaexterna():
            return self.relacionamento.email

    @property
    def get_vinculo_institucional_title(self):
        retorno = 'Nenhum'
        if self.eh_servidor() and not self.relacionamento.excluido:
            if self.relacionamento.eh_aposentado:
                retorno = 'Aposentado'
            elif self.relacionamento.eh_estagiario:
                retorno = 'Estagiário'
            else:
                retorno = 'Servidor'
        elif self.eh_prestador() and self.relacionamento.ativo:
            retorno = 'Prestador de Serviço'
        elif self.eh_trabalhadoreducando() and self.relacionamento.ativo:
            retorno = 'Trabalhador Educando'
        elif self.eh_residente() and self.relacionamento.ativo:
            retorno = 'Residente'
        elif self.eh_aluno() and self.relacionamento.situacao.ativo:
            retorno = 'Aluno'
        return retorno

    def get_ext_combo_template(self):
        return self.relacionamento.get_ext_combo_template()

    def get_relacionamento_title(self):
        relacionamento = self.relacionamento
        if relacionamento:
            try:
                return relacionamento.cargo_emprego.nome
            except AttributeError:
                return relacionamento._meta.verbose_name
        return 'Nenhum'

    @staticmethod
    def get_vinculos_ou_falsos_vinculos(pessoas):
        vinculos = []
        for pessoa in pessoas:
            if hasattr(pessoa, 'pessoafisica'):
                try:
                    vinculos.append(pessoa.pessoafisica.sub_instance().get_vinculo())
                except Exception:
                    relacionamento = PessoaExterna(pessoa_fisica=pessoa.pessoafisica, email=pessoa.pessoafisica.email)
                    vinculos.append(Vinculo(relacionamento=relacionamento))

            elif hasattr(pessoa, 'pessoajuridica'):
                vinculos.append(Vinculo(relacionamento=pessoa.pessoajuridica))
        return vinculos


def user_unicode(self):
    nome = self.get_full_name()
    profile = self.get_profile()
    if profile:
        nome = profile.nome_usual
    return f'{nome} ({self.username})'


def user_get_ext_combo_template(self):
    try:
        vinculo = self.get_vinculo()
        out = [f'<dt class="sr-only">Nome</dt><dd>{vinculo.pessoa.nome}</dd>']
        if vinculo.eh_servidor():
            if vinculo.setor:
                out.append(f'<dt>Setor:</dt><dd>{vinculo.setor.get_caminho_as_html()}</dd>')
            out.append(f'<dt>Cargo:</dt><dd>{vinculo.relacionamento.cargo_emprego}</dd>')
        out.append(f'<dt>Login:</dt><dd>{self.username}</dd>')
        if self.email:
            out.append(f'<dt>E-mail:</dt><dd>{self.email}</dd>')
        template = '''<div class="person">
            <div class="photo-circle">
                <img alt="Foto de {}" src="{}" />
            </div>
            <dl>{}</dl>
        </div>
        '''.format(
            vinculo.pessoa.nome, vinculo.pessoa.pessoa_fisica.get_foto_75x100_url(), ''.join(out)
        )
        return template
    except Exception:
        return str(self)


User.get_ext_combo_template = user_get_ext_combo_template
User.__str__ = user_unicode
User._meta.ordering = ('first_name', 'last_name')


def gerar_mensagem_atividade_irregular(request, user, header, session_id):
    ip_address = get_client_ip(request)
    ua_string = request.META.get('HTTP_USER_AGENT', '-')
    ua = user_agents.parse(ua_string)
    ua_device = str(ua)

    context = {
        'username': user.username,
        'ua_device': ua_device,
        'ip_address': ip_address,
        'hoje': datetime.now(),
        'site_url': settings.SITE_URL,
        'session_id': session_id
    }
    default_message = '''
        <dl>
            <dt>Matrícula:</dt>
            <dd>{{ username }}</dd>
            <dt>Dispositivo:</dt>
            <dd>{{ ua_device }}</dd>
            <dt>Data:</dt>
            <dd>{{ hoje|format }}</dd>
            <dt>Endereço IP:</dt>
            <dd>{{ ip_address }}</dd>
        </dl>
        <p>Saiba a <a href="https://ipinfo.io/{{ ip_address }}">localização provável do acesso</a> (serviço do site ipinfo.io).</p>
        <br>
        <p>Caso reconheça este login, por favor desconsidere esta notificação.</p>
        <br>
        <p>Caso não reconheça este login, por favor efetuar os passos abaixo para garantir a segurança dos seus dados e acesso:</p>
        <ol>
            {% if session_id %}
            <li>
                <a href="{{ site_url }}/comum/remote_logout/{{ session_id }}/">Efetuar o logout</a> (saída) do acesso em questão.
            </li>
            {% endif %}
            <li>
                <p>
                    Analisar os outros acessos e dispositivos atualmente em vigor (sessões) na sua matrícula, em
                    <a href="{{ site_url }}/admin/comum/sessioninfo/">Informações de Sessões</a>.
                </p>
                <p>A página acima também pode ser encontrada pelo menu "Tec. da Informação :: Sessões".</p>
            </li>
            <li>
                <p>
                    Analisar os dispositivos que conseguiram se autenticar na sua matrícula, em
                    <a href="{{ site_url }}/admin/comum/device/">Informações de Dispositivos</a>.
                </p>
                <p>A página acima também pode ser encontrada pelo menu "Tec. da Informação :: Dispositivos".</p>
            </li>
            <li>
                <a href="{{ site_url }}/comum/solicitar_trocar_senha/">Alterar a sua Senha</a>.
            </li>
            <li>
                Notificar o responsável pela TI da sua unidade.
            </li>
        </ol>
        <h3>Ação Opcional:</h3>
        <p>Caso deseje, você também pode verificar se algum de seus e-mails, ou telefones, podem ter sido expostos
        em algum incidente de segurança, utilizando o website <a href="https://haveibeenpwned.com/">"Have I Been Pwned"</a>.</p>
        <p>O mesmo site acima também é capaz de verificar se a senha que você utiliza é uma senha que já foi comprometida em algum incidente de segurança, tornando-a conhecida como uma senha comumente utilizável e recorrente: <a href="https://haveibeenpwned.com/Passwords">https://haveibeenpwned.com/Passwords</a>.</p>
    '''
    return render_from_string(header + default_message, context)


@receiver(user_login_failed)
def login_failed(sender, credentials, request, **kwargs):
    user = User.objects.filter(username=credentials.get('username')).first()
    if user:
        user.login_attempts += 1
        user.save()

        try:
            with atomic():
                vinculo = user.get_vinculo()
                title = 'Alerta de tentativas excessivas de login sem sucesso'
                header = f'''
                    <h1>Alerta de tentativas excessivas de login sem sucesso: {user.login_attempts} tentativas</h1>
                    <p>Nova tentativa de login no <b>SUAP</b> após <b>{user.login_attempts}</b> tentativas sem sucesso com os seguintes dados de acesso:</p>
                '''
                if user.login_attempts in [4, 10, 20, 50, 100] and vinculo:
                    expire_date = datetime.now() + timedelta(days=3)
                    message = gerar_mensagem_atividade_irregular(request, user, header, None)
                    send_notification(title, message, settings.DEFAULT_FROM_EMAIL, [user.get_vinculo()], data_permite_excluir=expire_date, data_permite_marcar_lida=expire_date)
                    email_secundario = getattr_coalesce(vinculo, 'pessoa.pessoafisica.email_secundario')
                    if email_secundario:
                        send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [email_secundario])
                    return
        except Exception:
            pass


@receiver(user_logged_in)
def logged_in(sender, user, request, **kwargs):
    cache.delete(f'servidor_tem_setor_middleware_{user.username}')
    try:
        with atomic():
            ua_string = request.META.get('HTTP_USER_AGENT', '-')
            cookie = request.COOKIES.get(settings.SUAP_CONTROL_COOKIE_NAME, '')
            notificar = True
            ua = user_agents.parse(ua_string)
            ua_device = str(ua)
            vinculo = request.user.get_vinculo()
            title = header = ''
            old_login_attempts = user.login_attempts
            expire_date = datetime.now() + timedelta(days=3)

            device, created = Device.objects.get_or_create(user=user, user_agent=ua_string, friendly_name=ua_device)
            obj = SessionInfo.objects.create(session_id=request.session.session_key, device=device, ip_address=get_client_ip(request))
            session_id = obj.pk

            user.login_attempts = 0
            user.save()
            email_secundario = getattr_coalesce(vinculo, 'pessoa.pessoafisica.email_secundario')

            if vinculo:
                if old_login_attempts > 2:
                    title = 'Alerta de login após diversas tentativas'
                    header = f'''
                        <h1>Alerta de login após {old_login_attempts} tentativas</h1>
                        <p>Novo login no <b>SUAP</b> após <b>{old_login_attempts}</b> tentativas de login com os seguintes dados de acesso:</p>
                    '''
                    message = gerar_mensagem_atividade_irregular(request, user, header, None)
                    send_notification(title, message, settings.DEFAULT_FROM_EMAIL, [vinculo], data_permite_excluir=expire_date, data_permite_marcar_lida=expire_date)
                    if email_secundario:
                        send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [email_secundario])
                    return

                if cookie:
                    try:
                        cookie_data = decrypt(cookie)
                    except Exception:
                        cookie_data = {}
                    try:
                        if request.user.username in cookie_data.get('usernames', []):
                            notificar = False
                    except Exception as e:
                        if settings.DEBUG:
                            raise e
                        capture_exception(e)

                # Se dispositivo esta desativado deve sempre notificar
                if not device.activated:
                    title = 'Alerta de dispositivo desativado'
                    header = f'''
                        <h1>{title}</h1>
                        <p>Novo login no <b>SUAP</b> em um dispositivo desativado com os seguintes dados de acesso:</p>
                    '''

                # Se dispositivo foi criado e nao tem cookies deve sempre notificar caso contrario nao notifica
                if created and notificar:
                    title = 'Alerta de dispositivo desconhecido'
                    header = f'''
                        <h1>{title}</h1>
                        <p>Novo login no <b>SUAP</b> em um dispositivo não utilizado previamente (desconhecido) com os seguintes dados de acesso:</p>
                    '''

                if title and header:
                    message = gerar_mensagem_atividade_irregular(request, user, header, session_id)
                    send_notification(title, message, settings.DEFAULT_FROM_EMAIL, [vinculo], data_permite_excluir=expire_date, data_permite_marcar_lida=expire_date)
                    if email_secundario:
                        send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [email_secundario])
    except IntegrityError:
        pass
    except Exception as e:
        capture_exception(e)


@receiver(user_logged_out)
def logged_out(sender, user, request, **kwargs):
    try:
        with atomic():
            SessionInfo.objects.filter(device__user=user, session_id=request.session.session_key).update(expired=True)
    except Exception as e:
        capture_exception(e)


def user_post_save(sender, **kwargs):
    """
    Sincroniza o usuário e os grupos e permissões deste.

    É chamado sempre que um usuário é salvo (por exemplo após efetuar login) e
    também no command ``sync_users``.

    Nota: estranhamente este signal não funciona nas edições de usuário no admin
    """
    user = kwargs['instance']
    # Setando o user do profile relacionado
    tem_profile = PessoaFisica.objects.filter(username=user.username).update(user=user)
    if not tem_profile:
        return

    profile = user.get_profile()
    profile_sub_instance = user.get_relacionamento()
    profile_sub_instance_class_name = profile_sub_instance.__class__.__name__

    eh_servidor = profile_sub_instance_class_name == 'Servidor'
    eh_prestador = profile_sub_instance_class_name == 'PrestadorServico'
    eh_aluno = profile_sub_instance_class_name == 'Aluno'
    eh_residente = profile_sub_instance_class_name == 'Residente'
    eh_trabalhadoreducando = profile_sub_instance_class_name == 'TrabalhadorEducando'

    User.objects.filter(id=user.id).update(
        is_active=True,
        is_staff=True,
        email=profile.email,
        first_name=profile.nome.split()[0],
        last_name=profile.nome.split()[-1],
        eh_servidor=eh_servidor,
        eh_prestador=eh_prestador,
        eh_aluno=eh_aluno,
        eh_residente=eh_residente,
        eh_trabalhadoreducando=eh_trabalhadoreducando,
        eh_tecnico_administrativo=eh_servidor and bool(profile_sub_instance.eh_tecnico_administrativo),
        eh_docente=eh_servidor and bool(profile_sub_instance.eh_docente),
    )

    """
    Verificando se é um Servidor e adicionando nos grupos: Aposentado ou Servidor
    Inativa o usuário caso o servidor esteja excluído
    """
    if eh_servidor:
        if profile_sub_instance.excluido or profile_sub_instance.eh_aposentado:
            UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user).delete()
            user.groups.clear()
            user.user_permissions.clear()
            if profile_sub_instance.eh_aposentado:
                user.groups.add(Group.objects.get(name='Aposentado'))
            elif profile_sub_instance.excluido:
                User.objects.filter(id=user.id).update(is_active=False, is_staff=False)
        else:
            user.groups.add(Group.objects.get(name='Servidor'))

    # Se possui ocupacao_ativa add ao grupo 'Prestador de Serviço' se não adiciona no grupo 'Usuario Externo'
    elif eh_prestador:
        if not profile_sub_instance.ativo:
            User.objects.filter(id=user.id).update(is_active=False, is_staff=False)
        elif profile_sub_instance.possui_ocupacao_ativa():
            user.groups.add(Group.objects.get_or_create(name='Prestador de Serviço')[0])
        else:
            user.groups.add(Group.objects.get_or_create(name='Usuário Externo')[0])

    elif eh_aluno:
        user.groups.add(Group.objects.get(name='Aluno'))

    elif eh_residente:
        user.groups.add(Group.objects.get(name='Residente'))

    elif eh_trabalhadoreducando:
        user.groups.add(Group.objects.get(name='Trabalhador(a) Educando(a)'))

    if hasattr(profile_sub_instance, 'avaliador'):
        avaliador = profile_sub_instance.avaliador
        grupo_avaliador_interno = Group.objects.get(name='Avaliador Interno')
        grupo_avaliador_externo = Group.objects.get(name='Avaliador Externo')

        if eh_servidor and avaliador.ativo:
            user.groups.add(grupo_avaliador_interno)
        else:
            user.groups.remove(grupo_avaliador_interno)

        if eh_prestador and avaliador.ativo:
            user.groups.add(grupo_avaliador_externo)
        else:
            user.groups.remove(grupo_avaliador_externo)

    if 'processo_eletronico' in settings.INSTALLED_APPS:
        grupo_tem_poder_chefe = Group.objects.get(name='Servidores Com Poder de Chefe')
        CompartilhamentoProcessoEletronicoPoderDeChefe = apps.get_model("processo_eletronico", "compartilhamentoprocessoeletronicopoderdechefe")
        if CompartilhamentoProcessoEletronicoPoderDeChefe.objects.filter(pessoa_permitida=profile).exists():
            user.groups.add(grupo_tem_poder_chefe)
        else:
            user.groups.remove(grupo_tem_poder_chefe)

    if 'plan_estrategico' in settings.INSTALLED_APPS:
        grupo_tem_poder_gestor = Group.objects.get_or_create(name='Coordenador de UA')[0]
        CompartilhamentoPoderdeGestorUA = apps.get_model("plan_estrategico", "compartilhamentopoderdegestorua")
        if CompartilhamentoPoderdeGestorUA.objects.filter(pessoa_permitida=profile).exists():
            user.groups.add(grupo_tem_poder_gestor)

    # NOTA: Executa o código daqui para baixo se o usuário for um servidor

    if not eh_servidor or not profile_sub_instance.setor:
        return

    cargo_emprego = profile_sub_instance.cargo_emprego.codigo if profile_sub_instance.cargo_emprego else ''

    if cargo_emprego == '701009':
        user.groups.add(Group.objects.get(name='Auditor'))

    if 'saude' in settings.INSTALLED_APPS:
        if cargo_emprego == '701064':
            user.groups.add(Group.objects.get(name='Odontólogo'))
        elif cargo_emprego == '701093':
            user.groups.add(Group.objects.get(name='Odontólogo'))
        elif cargo_emprego == '701241':
            user.groups.add(Group.objects.get(name='Técnico em Saúde Bucal'))
        elif cargo_emprego == '701047':
            user.groups.add(Group.objects.get(name='Médico'))
        elif cargo_emprego == '701029':
            user.groups.add(Group.objects.get(name='Enfermeiro'))
        elif cargo_emprego == '701030':
            user.groups.add(Group.objects.get(name='Enfermeiro'))
        elif cargo_emprego == '701233':
            user.groups.add(Group.objects.get(name='Técnico em Enfermagem'))
        elif cargo_emprego == '701411':
            user.groups.add(Group.objects.get(name='Auxiliar de Enfermagem'))
        elif cargo_emprego == '701038':
            user.groups.add(Group.objects.get(name='Fisioterapeuta'))
        elif cargo_emprego == '701055':
            user.groups.add(Group.objects.get(name='Nutricionista'))
        elif cargo_emprego == '701060':
            user.groups.add(Group.objects.get(name='Psicólogo'))

    grupo_chefe = Group.objects.get(name='Chefe de Setor')
    hoje = datetime.now()
    tem_funcao_hoje = False
    if not profile_sub_instance.eh_estagiario:
        tem_funcao_hoje = (
            profile_sub_instance.servidorfuncaohistorico_set.filter(setor_suap__isnull=False, funcao__codigo__in=Funcao.get_codigos_funcao_chefia())
            .filter(data_inicio_funcao__lte=hoje)
            .filter(Q(data_fim_funcao__gte=hoje) | Q(data_fim_funcao__isnull=True))
            .exists()
        )

    if tem_funcao_hoje:
        user.groups.add(grupo_chefe)
    else:
        [user.user_permissions.remove(permissao) for permissao in grupo_chefe.permissions.all()]
        user.groups.remove(grupo_chefe)

    if 'cursos' in settings.INSTALLED_APPS:
        Participante = apps.get_model('cursos', 'participante')
        Curso = apps.get_model('cursos', 'Curso')
        if Participante.objects.filter(servidor=profile_sub_instance).exists() or Curso.objects.filter(responsaveis=profile_sub_instance).exists():
            user.groups.add(Group.objects.get(name='Visualizador de Cursos e Concursos'))

    if 'ponto' in settings.INSTALLED_APPS:
        '''
        Verificando se o servidor vai ser inserido ou retirado do grupo de administrador do ponto
        A verificação será da seguinte forma:
           1 - verificar se o servidor tem função ativa no histórico de função
           2 - não pode adicionar estagiário no grupo de administrador do ponto
        '''
        grupo_admin_ponto = Group.objects.get_or_create(name='ponto Administrador')[0]
        if tem_funcao_hoje:
            user.groups.add(grupo_admin_ponto)
        else:
            user.groups.remove(grupo_admin_ponto)

    if 'protocolo' in settings.INSTALLED_APPS:
        if (profile_sub_instance.eh_tecnico_administrativo or (profile_sub_instance.funcao and not profile_sub_instance.eh_estagiario)) and not user.groups.filter(
            name__startswith='protocolo'
        ).exists():
            user.groups.add(Group.objects.get(name='Tramitador de processos'))

    # Comentado pois ja eh realizaod no novo modelo de permissoes do processo eletronico
    # if 'processo_eletronico' in settings.INSTALLED_APPS:
    #    if (profile_sub_instance.eh_tecnico_administrativo or (
    #            profile_sub_instance.funcao and not profile_sub_instance.eh_estagiario)):
    #        user.groups.add(Group.objects.get(name=u'Tramitador de Processos Eletrônicos'))


models.signals.post_save.connect(user_post_save, sender=User, dispatch_uid='comum.models')
models.signals.m2m_changed.connect(registrar_inclusao_remocao_grupo, sender=User.groups.through)


class AnoManager(models.Manager):
    def ultimos(self):
        return self.get_queryset().filter(ano__gt=1999, ano__lte=datetime.today().year + 1)


class Ano(models.ModelPlus):
    """
    Representa o ano e pode ser reutilizado em outros módulos.
    """

    SEARCH_FIELDS = ['ano']
    ano = models.SmallIntegerField(unique=True)

    objects = AnoManager()

    class Meta:
        ordering = ['-ano']
        verbose_name = 'Ano'
        verbose_name_plural = 'Anos'

    def __str__(self):
        return f'{self.ano}'


class Configuracao(models.ModelPlus):
    """
    Classe que mapeia as configurações utilizadas no SUAP.
    Exemplo:
       setor_padrao_extracao_siape = 10
       Onde 10 é o código do setor.

    Todas as configurações devem ser cadastradas e obtidas dinâmicamente.
    """

    app = models.CharField('Aplicação', max_length=50, null=False)
    chave = models.CharField('Chave', max_length=50)
    valor = models.TextField('Valor', null=True)
    descricao = models.TextField('Descrição')

    class Meta:
        unique_together = ['app', 'chave']
        verbose_name = 'Configuração'
        verbose_name_plural = 'Configurações'
        ordering = ['chave']

    def save(self, *args, **kwargs):
        """
        O método foi sobrescrito para remover a variável de classe ``_cached``
        """
        cache.delete('_CONFIGURACAO_CACHED')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.descricao

    @classmethod
    def _get_conf_por_chave(cls, app, chave):
        """
        Retorna uma Configuracao se existir uma com a chave passada como parâmetro, None caso contrário
        """
        return cls.objects.filter(app=app, chave=chave).first()

    @classmethod
    def get_valor_por_chave(cls, app, chave, enviroment_variable_name=None):
        key = f'{app}-configuracao-{chave}'
        data = cache.get('_CONFIGURACAO_CACHED', {})
        if not data:
            for _app, _chave, _valor in Configuracao.objects.values_list('app', 'chave', 'valor'):
                data[f'{_app}-configuracao-{_chave}'] = _valor
            cache.set('_CONFIGURACAO_CACHED', data)
        return data.get(key, os.environ.get(enviroment_variable_name.upper()) if enviroment_variable_name else None)

    @classmethod
    def clear_cache(cls):
        cache.delete('_CONFIGURACAO_CACHED')

    @classmethod
    def eh_email_institucional(cls, email):
        dominios_institucionais = cls.get_valor_por_chave("comum", "dominios_institucionais")
        if email and dominios_institucionais:
            for dominio in dominios_institucionais.split(";"):
                if dominio.lower().strip() in email.lower():
                    return True
        return False


class DocumentoControleTipo(models.ModelPlus):
    CARTEIRA_FUNCIONAL = 'carteira_funcional'
    CRACHA = 'cracha'

    TIPO_DOCUMENTO_CHOICES = [['', 'Selecione um Tipo de Documento'], [CARTEIRA_FUNCIONAL, 'Carteira Funcional'], [CRACHA, 'Crachá']]
    """
    Representa um tipo de documento a ser controlado
    Exemplo: "Carteira Funcional (Abrangência: Servidores Ativos Permanentes)"
    """
    descricao = models.CharFieldPlus('Descrição', help_text='Descrição do documento. Ex: Carteira Funcional')
    abrangencia = models.ManyToManyFieldPlus('rh.Situacao', verbose_name='Abrangência')
    identificador = models.CharFieldPlus('Identificador', null=True, blank=True)

    class Meta:
        verbose_name = 'Tipo de Documento para Controle'
        verbose_name_plural = 'Tipos de Documentos para Controle'

    def __str__(self):
        return '{} (Abrangência: {})'.format(self.descricao, ', '.join(ab.nome_siape for ab in self.abrangencia.all()))

    def get_link_csv(self):
        return f'/comum/gerar_cvs/{self.id:d}/'

    def save(self, *args, **kwargs):
        for item in self.TIPO_DOCUMENTO_CHOICES:
            if item[0] == self.identificador:
                self.descricao = item[1]
                break
        super().save(*args, **kwargs)


class DocumentoControle(models.ModelPlus):
    # campos comuns
    documento_tipo = models.ForeignKeyPlus('comum.DocumentoControleTipo', verbose_name='Tipo do Documento', null=True, blank=False, on_delete=models.CASCADE)
    solicitante_vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Solicitante', null=True, blank=False)
    justificativa = models.CharFieldPlus('Justificativa', max_length=2000, null=True, blank=False)
    ativo = models.BooleanField(default=True)
    data_solicitacao = models.DateTimeFieldPlus(auto_now_add=True, blank=True, null=True)
    status_solicitacao = models.IntegerField(
        'Situação da Solicitação', choices=SituacaoSolicitacaoDocumento.get_choices(), null=False, blank=False, default=SituacaoSolicitacaoDocumento.NAO_ATENDIDA
    )

    # campos de carteira funcional
    documento_id = models.CharFieldPlus('Identificação do Documento', null=True, blank=True)

    # campos de crachá
    nome_sugerido = models.CharFieldPlus('Nome Sugerido', null=True, max_length=20, blank=True)
    nome_social = models.CharFieldPlus('Nome Social', max_length=20, help_text='Limite de 20 caracteres.', null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitação de Documento'
        verbose_name_plural = 'Solicitações de Documentos'
        unique_together = ('documento_tipo', 'documento_id')

    def __str__(self):
        return f'{str(self.documento_tipo)} - ID: {self.id}'

    def get_absolute_url(self):
        return f"/comum/ver_solicitacao_documento/{self.id:d}/"

    def save(self, *args, **kwargs):
        # tratando as informações do campo documento_id
        if self.documento_id == '':
            self.documento_id = None

        '''
        No caso, só grava histórico quando for um registro novo. No update não precisa gravar.
        '''
        grava_historico = False
        if self.pk:
            obj_old = DocumentoControle.objects.get(pk=self.pk)
            if obj_old.status_solicitacao != self.status_solicitacao:
                grava_historico = True
        else:
            grava_historico = True

        super().save(*args, **kwargs)
        if grava_historico:
            self._salva_dados_historico(tl.get_request(), self.status_solicitacao)

    def pode_atender_solicitacao(self, request):
        return (
            'comum.change_documentocontrole' in request.user.get_group_permissions() or 'Confeccionador de Documentos' in request.user.groups.values_list('name', flat=True)
        ) and self.status_solicitacao == SituacaoSolicitacaoDocumento.NAO_ATENDIDA

    def pode_rejeitar_solicitacao(self, request):
        return 'comum.change_documentocontrole' in request.user.get_group_permissions() or 'Confeccionador de Documentos' in request.user.groups.values_list('name', flat=True)

    @atomic()
    def atender_solicitacao(self, request):
        if self.pode_atender_solicitacao(request):
            # Verifica se o usuário tem solicitação para o mesmo tipo de documento. Caso positivo, inativaremos esses registros
            qs_solicitacao = DocumentoControle.objects.filter(
                solicitante_vinculo=self.solicitante_vinculo, status_solicitacao=SituacaoSolicitacaoDocumento.ATENDIDA, documento_tipo=self.documento_tipo
            )
            if qs_solicitacao.exists():
                qs_solicitacao.update(ativo=False)

            situacao = SituacaoSolicitacaoDocumento.ATENDIDA

            # salvando histórico
            request.POST = dict()
            request.POST['motivo'] = 'Solicitação atendida.'

            # alterando objeto principal
            self.status_solicitacao = situacao
            self.save()

    @atomic()
    def rejeitar_solicitacao(self, request):
        if self.pode_atender_solicitacao(request):
            situacao = SituacaoSolicitacaoDocumento.REJEITADA

            # salvando histórico
            self._salva_dados_historico(request, situacao)

            # salvando objeto principal
            self.status_solicitacao = situacao
            self.save()

    def _salva_dados_historico(self, request, situacao):
        # guardando informações no histórico
        historico = DocumentoControleHistorico()
        historico.solicitacao = self
        historico.responsavel_vinculo = request.user.get_vinculo()
        historico.situacao_historico = situacao
        if request and request.POST and request.POST.get('motivo'):
            historico.motivo = request.POST.get('motivo')
        elif self.justificativa and self.status_solicitacao is not SituacaoSolicitacaoDocumento.ATENDIDA:
            historico.motivo = self.justificativa
        historico.save()

    def get_classe_css(self):
        classe_css = 'alert'
        if self.status_solicitacao == SituacaoSolicitacaoDocumento.REJEITADA:
            classe_css = 'error'
        elif self.status_solicitacao == SituacaoSolicitacaoDocumento.ATENDIDA:
            classe_css = 'success'
        return classe_css


class DocumentoControleHistorico(models.ModelPlus):
    responsavel_vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Responsável', null=True, blank=False)
    solicitacao = models.ForeignKeyPlus('comum.DocumentoControle', verbose_name='Solicitação', null=False, blank=False, on_delete=models.CASCADE)
    situacao_historico = models.IntegerField('Situação', choices=SituacaoSolicitacaoDocumento.get_choices(), null=False, blank=False)
    data_historico = models.DateTimeFieldPlus(auto_now_add=True, blank=True, null=True)
    motivo = models.CharFieldPlus('Motivo', max_length=2000, null=False, blank=False)

    class Meta:
        verbose_name = 'Histórico da Solicitação de Documento'
        verbose_name_plural = 'Histórico das Solicitações de Documentos'

    def get_classe_css(self):
        classe_css = 'alert'
        if self.situacao_historico == SituacaoSolicitacaoDocumento.REJEITADA:
            classe_css = 'error'
        elif self.situacao_historico == SituacaoSolicitacaoDocumento.ATENDIDA:
            classe_css = 'success'
        return classe_css


class ConfiguracaoImpressaoDocumento(models.ModelPlus):
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Campus', on_delete=models.CASCADE)
    relacao_impressao = models.ManyToManyField('rh.UnidadeOrganizacional', verbose_name='Relação de Impressão', related_name='uo_relacao_impressao_set')
    tipos_documento = models.ManyToManyFieldPlus('comum.DocumentoControleTipo', verbose_name='Tipos de Documento')
    local_impressao = models.CharFieldPlus(
        'Local de Impressão', max_length=30, null=True, blank=True, help_text='Este campo deverá ser preenchido caso o documento necessite do local de expedição. Ex: Natal/RN'
    )

    class Meta:
        verbose_name = 'Configuração de Impressão de Documento'
        verbose_name_plural = 'Configurações de Impressão de Documento'

    def __str__(self):
        return f'Configuração de Impressão de Documento ({self.uo.nome})'


class ConfiguracaoCarteiraFuncional(models.ModelPlus):
    margem_top_bloco_1 = models.IntegerField('Margem do Topo Bloco 1', default=0, null=False, blank=0)
    margem_top_bloco_2 = models.IntegerField('Margem do Topo Bloco 2', default=0, null=False, blank=0)
    margem_top_bloco_3 = models.IntegerField('Margem do Topo Bloco 3', default=0, null=False, blank=0)
    margem_top_bloco_4 = models.IntegerField('Margem do Topo Bloco 4', default=0, null=False, blank=0)

    class Meta:
        verbose_name = 'Configuração da Carteira Funcional'
        verbose_name_plural = 'Configurações da Carteira Funcional'


class NivelEnsino(models.ModelPlus):
    SEARCH_FIELDS = ['descricao']
    FUNDAMENTAL = 1
    GRADUACAO = 3
    MEDIO = 2
    POS_GRADUACAO = 4
    MEDIO_FORMACAO_TECNICA = 5

    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Nível de Ensino'
        verbose_name_plural = 'Níveis de Ensino'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao


class OrgaoEmissorRg(models.ModelPlus):
    SEARCH_FIELDS = ['nome']
    nome = models.CharFieldPlus(verbose_name='Nome')

    class Meta:
        verbose_name = 'Orgão Emissor de Identidade'
        verbose_name_plural = 'Orgãos Emissores de Identidade'

    def __str__(self):
        return self.nome


class Pais(ModelPlus):
    codigo = models.CharField(max_length=4)
    nome = models.CharField(max_length=30, null=True, blank=True)
    equiparado = models.BooleanField(default=False)
    excluido = models.BooleanField(verbose_name='Excluído', default=False)
    codigo_censup = models.CharField(verbose_name='Código CENSUP', default='', blank=True, max_length=3)
    codigo_educacenso = models.CharField(verbose_name='Código EDUCACENSO', default='', blank=True, max_length=3)

    class Meta:
        db_table = 'pais'
        verbose_name = 'País'
        verbose_name_plural = 'Países'

    def __str__(self):
        return self.nome


class TerritorioIdentidade(ModelPlus):
    nome = models.CharField(max_length=100, null=True, blank=True)
    lista_cidades = models.CharField(max_length=2000, null=True, blank=True)

    class Meta:
        verbose_name = 'Território de identidade'
        verbose_name_plural = 'Territórios de identidade'

    def __str__(self):
        return self.nome

class UnidadeFederativa(ModelPlus):
    nome = models.CharField(max_length=30, null=True, blank=True)
    sigla = models.CharField(max_length=2, null=True, blank=True)

    class Meta:
        db_table = 'unidade_federativa'
        verbose_name = 'Unidade Federativa'
        verbose_name_plural = 'Unidades Federativas'

    def __str__(self):
        return self.nome

class Municipio(models.ModelPlus):
    SEARCH_FIELDS = ['codigo', 'identificacao', 'nome', 'uf']

    codigo = models.CharField('Código SIAFI', max_length=50, blank=True, editable=False)
    identificacao = models.CharFieldPlus(unique=True, editable=False, help_text='Este campo é preenchido automaticamente pelo sistema')
    nome = models.CharFieldPlus()
    uf = models.BrEstadoBrasileiroField()
    uf_code = models.CharField(max_length=10, verbose_name='Código IBGE UF', null=True, blank=True, help_text='Código IBGE UF')
    territorio_identidade = models.ForeignKey(TerritorioIdentidade, verbose_name='Território Identidade', on_delete=models.CASCADE , null=True, blank=True)

    class Meta:
        ordering = ['identificacao']
        verbose_name = 'Município'
        verbose_name_plural = 'Municípios'

    def save(self, *args, **kwargs):
        """
        O método foi sobrescrito para preencher automaticamente o campo ``identificacao``
        """
        self.nome = self.nome.strip()
        self.uf = self.uf.strip()
        self.identificacao = Municipio.get_identificacao(self.nome, self.uf)[:255]
        # Está cadastrando e existe município com a mesma identificação
        if not self.pk and Municipio.objects.filter(identificacao=self.identificacao).exists():
            raise Exception(f'Municipio existente com identificacao "{self.identificacao}". Use o metodo de classe Municipio.get_or_create.')

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nome} / {self.uf}'

    @staticmethod
    def get_identificacao(nome, uf):
        return (f'{to_ascii(nome)}-{to_ascii(uf)}').replace(' ', '').upper()

    @classmethod
    def get_or_create(cls, nome, uf):
        identificacao = Municipio.get_identificacao(nome, uf)
        try:
            obj = cls.objects.get(identificacao=identificacao)
            return obj, 0
        except cls.DoesNotExist:
            obj = cls.objects.create(nome=nome, uf=uf)
            return obj, 1


class PessoaEndereco(models.ModelPlus):
    pessoa = models.ForeignKeyPlus(Pessoa, on_delete=models.CASCADE)
    municipio = models.ForeignKeyPlus('comum.Municipio', verbose_name='Município', null=True, on_delete=models.CASCADE)
    logradouro = models.CharFieldPlus(null=True)
    numero = models.CharField('Nº', max_length=50, null=True)
    complemento = models.CharFieldPlus(null=True)
    bairro = models.CharFieldPlus(null=True)
    cep = models.CharField('CEP', max_length=9, null=True)
    via_form_suap = models.BooleanField('Via SUAP?', default=False)

    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'

    def save(self, *args, **kwargs):
        """
        O método foi sobrescrito para preencher automaticamente o campo ``identificacao``
        """
        for attr in ['logradouro', 'numero', 'complemento', 'bairro']:
            val = getattr(self, attr)
            if val:
                setattr(self, attr, val.strip())
        self.cep = mask_cep(self.cep)
        super().save(*args, **kwargs)

    def __str__(self):
        out = []
        for attr in ['logradouro', 'numero', 'complemento', 'bairro', 'cep', 'municipio']:
            val = getattr(self, attr)
            if val:
                out.append(str(val))
        return ', '.join(out)

    @classmethod
    def create_for_siape(cls, pessoa, logradouro, numero, complemento, bairro, municipio_nome, municipio_uf, cep):
        municipio, created = Municipio.get_or_create(municipio_nome, municipio_uf)
        cls.objects.create(pessoa=pessoa, logradouro=logradouro, numero=numero, complemento=complemento, bairro=bairro, cep=cep, municipio=municipio)


class PessoaTelefone(models.ModelPlus):
    """
    Armazena os telefones de pessoas.

    Formas de cadastro:
        - Extração SIAPE
        - Extração SIAFI
        - Cadastro manual de PFs e PJs
    """

    pessoa = models.ForeignKeyPlus(Pessoa, on_delete=models.CASCADE)
    numero = models.CharField('Número', max_length=45)  # 45 é o tamanho do telefone SIAFI
    ramal = models.CharField(max_length=5, blank=True)  # Evitar que CharField tenha null=True
    observacao = models.CharField('Observação', max_length=50, blank=True)  # Evitar que CharField tenha null=True

    class Meta:
        verbose_name = 'Telefone'
        verbose_name_plural = 'Telefones'

    def __str__(self):
        if self.observacao:
            return f'{self.numero} ({self.observacao})'
        else:
            return self.numero


class InscricaoFiscal(models.ModelPlus):
    PREFERENCIA_CHOICE = [['M', 'Matutino'], ['V', 'Vespertino'], ['A', 'Matutino e Vespertino']]

    servidor = models.ForeignKeyPlus('rh.Servidor', default=tl.get_user, on_delete=models.CASCADE)
    numero_filhos_menores_21_anos = models.PositiveIntegerField('Número de filhos menores de 21 anos')
    data_inicio_servico_na_instituicao = models.DateFieldPlus('Data do início do serviço na Instituição')


class Ocupacao(models.ModelPlus):
    codigo = models.CharField('Código que identifica a classificação das ocupações definidas pela CBO-2002', max_length=6, null=True, blank=True)
    descricao = models.CharField('Nome das ocupações definidas pela CBO-2002', max_length=256, null=False)
    representante = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Ocupação'
        verbose_name_plural = 'Ocupações'

    def __str__(self):
        if self.codigo:
            return f'{self.codigo} - {self.descricao}'
        return self.descricao


class PrestadorServicoManager(models.Manager):

    def prestadores(self):
        return self.get_queryset().filter(usuario_externo=False, eh_prestador=True)

    def usuarios_externos(self):
        return self.get_queryset().filter(usuario_externo=True, eh_prestador=True)

    def get_queryset(self):
        return super().get_queryset()


class PrestadorServico(Funcionario):
    ativo = models.BooleanField(verbose_name="Ativo", default=True, help_text="Somente prestadores de serviço ativos podem usar os terminais de ponto e chaves")
    vinculos = GenericRelation('comum.Vinculo', related_query_name='prestadores', object_id_field='id_relacionamento', content_type_field='tipo_relacionamento')
    pessoa_fisica = models.ForeignKeyPlus('rh.PessoaFisica', db_index=True, null=False, blank=False, related_name="prestadores", default=1)
    matricula = models.CharFieldPlus('Matrícula', max_length=30, db_index=True)
    areas_de_conhecimento = models.ManyToManyFieldPlus('rh.AreaConhecimento', blank=True)
    usuario_externo = models.BooleanField(verbose_name="Usuário Externo", default=False,
                                          help_text="Indica se o prestador é um Usuário Externo")
    chefia_imediata = models.BooleanField(verbose_name="Chefia imediata", default=False,
                                          help_text="Indica se o prestador é uma Chefia imediata")

    bolsista = models.BooleanField(verbose_name="Bolsita", default=False,
                                          help_text="Indica se o prestador é um Bolsita")
    justificativa_cadastro = models.ForeignKeyPlus('comum.JustificativaUsuarioExterno', verbose_name='Justificativa para Cadastro', null=True)

    email_google_classroom = models.EmailField('Email do Google Classroom', blank=True)
    data_admissao = DateFieldPlus(verbose_name='Data de Admissão', null=True, blank=True)
    data_demissao = DateFieldPlus(verbose_name='Data de Demissão', null=True, blank=True)

    objects = PrestadorServicoManager()

    class Meta:
        verbose_name = 'Prestador de serviço'
        verbose_name_plural = 'Prestadores de serviço'
        permissions = (('eh_prestador', 'Prestador de Serviço'),
                       ("change_usuarioexterno", "Pode gerenciar Usuário Externo"),)

    def __str__(self):
        return f'{normalizar_nome_proprio(self.nome)} ({self.matricula})'

    def save(self, *args, **kwargs):
        # Verifica se é estrangeiro para vincular passaporte
        if self.nacionalidade and int(self.nacionalidade) == Nacionalidade.ESTRANGEIRO and not self.cpf:
            self.matricula = re.sub(r'\W', '', str(self.passaporte))
        else:
            self.matricula = re.sub(r'\D', '', str(self.cpf))

        # Verifica se possui ocupação Ativa (EX: Recepcionista), caso  possua é que será setado eh_prestador = True
        if not self.possui_ocupacao_ativa():
            self.usuario_externo = True
        self.eh_prestador = True

        if not self.username:
            self.username = self.matricula
        super().save(*args, **kwargs)

        if not hasattr(self, 'avaliador'):
            User.objects.filter(username=self.matricula).update(is_active=self.ativo, eh_prestador=True)
        else:
            User.objects.filter(username=self.matricula).update(is_active=True, eh_prestador=True)

        user = self.get_user()
        qs = Vinculo.objects.filter(Q(prestadores=self))
        if not qs.exists():
            vinculo = Vinculo()
        else:
            vinculo = qs.first()
        vinculo.pessoa = self.pessoa_ptr
        vinculo.user = user
        vinculo.relacionamento = self
        vinculo.setor = self.setor
        vinculo.save()

        PrestadorServico.objects.filter(pk=self.pk).update(pessoa_fisica=self.pk)

        try:
            LdapConf = apps.get_model('ldap_backend', 'LdapConf')
            conf = LdapConf.get_active()
            conf.sync_user(self)
        except Exception:
            pass

    def get_absolute_url(self):
        return reverse_lazy('prestador_servico', kwargs={'id': self.pk})

    def get_vinculo(self):
        return self.vinculo_set.first()

    def get_user(self):
        return User.objects.filter(username=self.username).first()

    def get_ext_combo_template(self):
        out = [f'<dt class="sr-only">Nome</dt><dd><strong>{self.nome}</strong></dd>']
        out.append('<dt class="sr-only">Categoria</dt><dd>Prestador de Serviço</dd>')
        if self.setor:
            out.append(f'<dt class="sr-only">Setor</dt><dd>{self.setor.get_caminho_as_html()}</dd>')
        template = '''<div class="person">
            <div class="photo-circle">
                <img src="{}" alt="Foto de {}" />
            </div>
            <dl>{}</dl>
        </div>
        '''.format(
            self.get_foto_75x100_url(), self.nome, ''.join(out)
        )
        return template

    def eh_chefe_do_setor_hoje(self, setor):
        return False

    def tem_ocupacao_ativa(self):
        hoje = date.today()
        ocupacoes = OcupacaoPrestador.objects.filter(prestador=self, data_inicio__lte=hoje, data_fim__gte=hoje)
        if ocupacoes.exists():
            return True
        return False

    @property
    def papeis_ativos(self):
        hoje = date.today()
        papeis_datas_menores_hoje = self.papel_set.filter(data_inicio__lte=hoje)
        return papeis_datas_menores_hoje.filter(data_fim__isnull=True) | papeis_datas_menores_hoje.filter(data_fim__gte=hoje)

    def chefes_imediatos(self):
        if self.setor:
            setor = self.setor

            while not setor.historico_funcao().exists() and setor.superior:
                setor = setor.superior

            return Servidor.objects.filter(pk__in=setor.historico_funcao().values_list('servidor_id', flat=True))
        return PrestadorServico.objects.none()

    def possui_ocupacao_ativa(self):
        return self.ocupacaoprestador_set.filter(data_fim__gte=date.today()).exists()


class UsuarioExternoManager(models.Manager):
    def get_queryset(self):
        query_set = super().get_queryset()
        return query_set.filter(usuario_externo=True, eh_prestador=True)


class JustificativaUsuarioExterno(models.ModelPlus):
    justificativa = models.CharFieldPlus('Perfil', max_length=255)
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = 'Perfil para Cadastro de Usuário Externo'
        verbose_name_plural = 'Perfis para Cadastro de Usuários Externos'


class UsuarioExterno(PrestadorServico):
    objects = UsuarioExternoManager()

    class Meta:
        verbose_name = 'Usuário Externo'
        verbose_name_plural = 'Usuários Externos'
        proxy = True

    def get_absolute_url(self):
        return "/comum/usuario_externo/{:d}/".format(self.id)

    def ativar(self, *args, **kwargs):
        self.ativo = True
        self.save()
        kwargs = dict(detalhamento="{} - Usuário Externo".format(self.pessoafisica.cpf),
                      descricao="{} - Usuário Externo".format(self.pessoafisica.cpf), data_fim=None)
        papel_cargo, criou = Papel.objects.update_or_create(
            pessoa=self.pessoafisica,
            tipo_papel=Papel.TIPO_PAPEL_USUARIOEXTERNO,
            data_inicio=datetime.now(),
            papel_content_type=ContentType.objects.get_for_model(self),
            papel_content_id=self.id,
            defaults=kwargs,
        )

    def pode_ser_ativado(self, *args, **kwargs):
        if not self.ativo:
            return True
        return False

    def inativar(self, *args, **kwargs):
        self.ativo = False
        self.save()
        Papel.objects.filter(pessoa=self.pessoafisica, tipo_papel=Papel.TIPO_PAPEL_USUARIOEXTERNO).update(
            data_fim=datetime.now() - timedelta(days=1))

    def documentos_assinados(self, *args, **kwargs):
        DocumentoTexto = apps.get_model("documento_eletronico", "DocumentoTexto")
        return DocumentoTexto.objects.assinados(self.user).order_by('-data_criacao')

    def processos_que_sou_interessado(self, *args, **kwargs):
        Processo = apps.get_model("processo_eletronico", "Processo")
        return Processo.objects.filter(interessados=self).order_by('-data_hora_criacao')

    def cadastrar_telefone(self, telefone):
        PessoaTelefone = apps.get_model("comum", "PessoaTelefone")
        PessoaTelefone.objects.create(pessoa_id=self.user.get_profile().pessoafisica.id,
                                      numero=telefone)

    def get_ext_combo_template(self):
        out = ['<h4>{}</h4>'.format(self.nome)]
        out.append('<h5>Usuário Externo</h5>')
        if self.setor:
            out.append('<p>{}</p>'.format(self.setor.get_caminho_as_html()))
        template = '''<div class="person">
             <div class="photo-circle">
                 <img src="{}"/>
             </div>
             <div>
                 {}
             </div>
         </div>
         '''.format(
            self.get_foto_75x100_url(), ''.join(out)
        )
        return template

    def save(self, *args, **kwargs):
        self.usuario_externo = True
        super().save(*args, **kwargs)

    def enviar_email_pre_cadastro(self):
        conteudo = f'''<h1>Ativação de Cadastro de Usuário Externo - SUAP </h1>
        <p>Prezado(a) {self.nome},</p>
        <p>Foi realizado um cadastro de Usuário Externo no SUAP/IFRN</p>
        <p>Acesse o endereço abaixo para autenticar no SUAP e clique na opção Entrar com Gov.BR</p>
        <p><a href="{settings.SITE_URL}">{settings.SITE_URL}</a></p>.
        <p><span>ATENÇÃO:</span> É necessário ter conta no <a href="https://sso.acesso.gov.br/">Gov.BR</a></p>
        '''
        return send_mail('[SUAP] Cadastro de Usuário Externo', conteudo, settings.DEFAULT_FROM_EMAIL, [self.email])


class OcupacaoPrestador(models.ModelPlus):
    prestador = models.ForeignKeyPlus('comum.PrestadorServico', null=False, blank=False, on_delete=models.CASCADE)
    ocupacao = models.ForeignKeyPlus('comum.Ocupacao', null=False, blank=False, on_delete=models.CASCADE)
    empresa = models.ForeignKeyPlus('rh.PessoaJuridica', verbose_name='Pessoa Jurídica', null=False, blank=False, on_delete=models.CASCADE)
    data_inicio = models.DateFieldPlus('Data de início', null=False, blank=False)
    data_fim = models.DateFieldPlus('Data fim', null=False, blank=False)
    setor_suap = models.ForeignKeyPlus('rh.Setor', null=True, blank=False, related_name='cargo_funcao_setor_suap', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Ocupação de Prestador de Serviço'
        verbose_name_plural = 'Ocupações dos Prestadores de Serviços'

    def __str__(self):
        if self.ocupacao:
            return f"{self.prestador.nome} - {self.ocupacao} - {self.empresa}"
        else:
            return f"{self.prestador.nome} - {self.empresa}"

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.pode_editar():
            Papel.objects.filter(
                pessoa=self.prestador.pessoa_fisica,
                tipo_papel=Papel.TIPO_PAPEL_OCUPACAO,
                data_inicio=self.data_inicio,
                papel_content_type=ContentType.objects.get_for_model(self.ocupacao),
                papel_content_id=self.ocupacao.id,
            ).delete()
        else:
            raise ValidationError('Impossível apagar Ocupação deste prestador')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        kwargs = dict(detalhamento=str(self), descricao=str(self), setor_suap=self.setor_suap, data_fim=self.data_fim, portaria='-')
        papel, criou = Papel.objects.update_or_create(
            pessoa=self.prestador.pessoa_fisica,
            tipo_papel=Papel.TIPO_PAPEL_OCUPACAO,
            data_inicio=self.data_inicio,
            papel_content_type=ContentType.objects.get_for_model(self.ocupacao),
            papel_content_id=self.ocupacao.id,
            defaults=kwargs,
        )

    def pode_editar(self):
        if 'documento_eletronico' in settings.INSTALLED_APPS:
            from rh.models import Papel
            from documento_eletronico.models import Assinatura

            papeis = Papel.objects.filter(
                pessoa=self.prestador.pessoa_fisica,
                tipo_papel=Papel.TIPO_PAPEL_OCUPACAO,
                data_inicio=self.data_inicio,
                papel_content_type=ContentType.objects.get_for_model(self.ocupacao),
                papel_content_id=self.ocupacao.id,
            )

            if self.pk and Assinatura.objects.filter(papel__in=papeis).exists():
                return False
            else:
                return True
        else:
            return True


class Predio(models.ModelPlus):
    SEARCH_FIELDS = ['nome', 'uo__setor__sigla']
    nome = models.CharField(max_length=100)
    uo = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', null=False, on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)

    # Sistemas Construtivos
    estrutura = models.ManyToManyFieldPlus('comum.EstruturaPredio', blank=True, verbose_name='Estrutura')
    cobertura = models.ManyToManyFieldPlus('comum.CoberturaPredio', blank=True, verbose_name='Cobertura')
    vedacao = models.ManyToManyFieldPlus('comum.VedacaoPredio', blank=True, verbose_name='Vedação')
    sistema_sanitario = models.ManyToManyFieldPlus('comum.SistemaSanitarioPredio', blank=True, verbose_name='Sistema Sanitário')
    sistema_abastecimento = models.ManyToManyFieldPlus('comum.SistemaAbastecimentoPredio', blank=True, verbose_name='Sistema de Abastecimento')
    sistema_alimentacao_eletrica = models.ManyToManyFieldPlus('comum.SistemaAlimentacaoEletricaPredio', blank=True, verbose_name='Sistema de Alimentação Elétrica')
    potencia_transformador = models.PositiveIntegerField('Potência do Transformador', null=True, blank=True, help_text='Informar em KVA')
    informacao_sistema_alimentacao_eletrica = models.TextField("Informações Adicionais", null=True, blank=True, help_text='Informações adicionais do sistema de alimentação elétrica')
    sistema_protecao_descarga_atmosferica = models.ManyToManyFieldPlus('comum.SistemaProtecaoDescargaAtmosfericaPredio', blank=True, verbose_name='Sistema de Proteção Contra Descargas Atmosféricas')
    acabamento_externo = models.ManyToManyFieldPlus('comum.AcabamentoExternoPredio', blank=True, verbose_name='Acabamento Externo (Fachadas)')

    class Meta:
        unique_together = ('nome', 'uo')
        verbose_name = 'Prédio'
        verbose_name_plural = 'Prédios'
        ordering = ['uo__setor__sigla', 'nome']

    def __str__(self):
        return f"{self.nome} ({str(self.uo)})"

    def get_absolute_url(self):
        return f"/comum/predio/{self.pk}/"

    def get_obra_original(self):
        return self.obra_set.filter(tipo=Obra.TIPO_ORIGINAL).first()

    def get_area_construida(self):
        return self.obra_set.exclude(tipo=Obra.TIPO_REFORMA).aggregate(Sum('area_construida'))['area_construida__sum']

    def get_area_acrescentada(self):
        return self.obra_set.filter(tipo=Obra.TIPO_AMPLIACAO).aggregate(Sum('area_construida'))['area_construida__sum']

    def get_ampliacoes(self):
        return self.obra_set.filter(tipo=Obra.TIPO_AMPLIACAO).order_by('data_recebimento')

    def get_reformas(self):
        return self.obra_set.filter(tipo=Obra.TIPO_REFORMA).order_by('data_recebimento')

    def get_combates_incendio_panico(self):
        return self.combateincendiopanico_set.all()

    def tem_sistema_construtivo(self):
        return self.estrutura.exists() or self.cobertura.exists() or self.vedacao.exists() or self.sistema_sanitario.exists() or self.sistema_abastecimento.exists() or self.sistema_alimentacao_eletrica.exists() or self.sistema_protecao_descarga_atmosferica.exists() or self.acabamento_externo.exists()


class Obra(models.ModelPlus):

    TIPO_ORIGINAL = 0
    TIPO_AMPLIACAO = 1
    TIPO_REFORMA = 2
    TIPO_CHOICES = [[TIPO_ORIGINAL, 'Original'], [TIPO_AMPLIACAO, 'Ampliação'], [TIPO_REFORMA, 'Reforma']]

    predio = models.ForeignKeyPlus(Predio, verbose_name='Prédio', on_delete=models.CASCADE)
    tipo = models.PositiveIntegerField(verbose_name='Tipo da Obra', choices=TIPO_CHOICES)
    data_inicio = models.DateFieldPlus(verbose_name="Início da Obra")
    descricao = models.TextField("Descrição do Escopo", null=True, blank=True)
    data_recebimento = models.DateFieldPlus(verbose_name="Recebimento Definitivo", null=True, blank=True)
    # processo_recebimento = models.ForeignKeyPlus("protocolo.Processo", verbose_name="Processo de Recebimento", null=True, blank=True)
    area_construida = models.DecimalFieldPlus(verbose_name="Área Construída", help_text="Informar em m²", null=True, blank=True)

    def get_idade_obra(self):
        hoje = datetime.now()
        return relativedelta(self.data_recebimento, hoje)

    def save(self, *args, **kwargs):
        if self.tipo == Obra.TIPO_ORIGINAL and Obra.objects.filter(predio_id=self.predio.pk, tipo=Obra.TIPO_ORIGINAL).exclude(pk=self.pk).exists():
            raise ValueError('Não é possível cadastrar mais de uma obra do tipo Original')
        if self.tipo != Obra.TIPO_ORIGINAL and not Obra.objects.filter(predio_id=self.predio.pk).exists():
            raise ValueError('O primeiro cadastro deve ser da obra Original.')
        super().save(*args, **kwargs)


class CombateIncendioPanico(models.ModelPlus):
    predio = models.ForeignKeyPlus(Predio, verbose_name='Prédio', on_delete=models.CASCADE)
    protocolo_pscip = models.CharFieldPlus("Protocolo PSCIP", null=True, blank=True)
    data_vistoria = models.DateFieldPlus("Vistoria Técnica", null=True, blank=True)
    data_validade_alvara = models.DateFieldPlus("Validade do Alvará", null=True, blank=True)
    alvara = models.PrivateFileField(verbose_name='Alvará', max_length=255, null=True, blank=True, upload_to='comum/predio/alvaras')
    observacoes = models.TextField("Observações", null=True, blank=True)

    class Meta:
        verbose_name = 'Combate a Incêndio e Pânico'
        verbose_name_plural = 'Combates a Incêndio e Pânico'
        ordering = ['predio__uo__setor__sigla', '-data_vistoria']


class EstruturaPredio(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Estrutura'
        verbose_name_plural = 'Estruturas'


class CoberturaPredio(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Cobertura'
        verbose_name_plural = 'Coberturas'


class VedacaoPredio(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Vedação'
        verbose_name_plural = 'Vedações'


class SistemaSanitarioPredio(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Sistema Sanitário'
        verbose_name_plural = 'Sistemas Sanitários'


class SistemaAbastecimentoPredio(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Sistema de Abastecimento'
        verbose_name_plural = 'Sistemas de Abastecimentos'


class SistemaAlimentacaoEletricaPredio(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Sistema de Alimentação Elétrica'
        verbose_name_plural = 'Sistemas de Alimentação Elétrica'


class SistemaProtecaoDescargaAtmosfericaPredio(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Sistema de Proteção Contra Descargas Atmosféricas'
        verbose_name_plural = 'Sistemas de Proteção Contra Descargas Atmosféricas'


class AcabamentoExternoPredio(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Acabamento Externo (Fachada)'
        verbose_name_plural = 'Acabamentos Externos (Fachadas)'


class AtivasManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ativa=True)


class Sala(models.ModelPlus):
    SEARCH_FIELDS = ['nome', 'predio__nome', 'predio__uo__nome', 'predio__uo__sigla']

    nome = models.CharField(max_length=100)
    predio = models.ForeignKeyPlus(Predio, verbose_name='Prédio', on_delete=models.CASCADE)
    ativa = models.BooleanField('Ativa', default=True)
    agendavel = models.BooleanField('Agendável', default=False)
    setores = models.ManyToManyFieldPlus(Setor, blank=True, help_text='Informe os setores que estão na sala. Esse campo é opcional e meramente informativo.')
    capacidade = models.PositiveIntegerField('Capacidade da sala (em número de pessoas)', null=True, blank=True)
    avaliadores_de_agendamentos = models.ManyToManyFieldPlus(
        'comum.User',
        blank=True,
        related_name='salas_avaliadas',
        verbose_name='Avaliadores de Agendamento',
        help_text='Informe os usuários responsáveis por responder às solicitações de agendamento. Digite parte da matrícula ou primeiro nome.',
    )
    restringir_agendamentos_no_campus = models.BooleanField('Agendamento apenas por servidores do campus', default=False)
    informacoes_complementares = models.TextField(
        'Informações complementares', null=True, blank=True, help_text='As informações complementares serão exibidas para o usuário durante a solicitação de agendamento'
    )

    area_util = models.DecimalFieldPlus("Área Útil", null=True, blank=True, help_text="Informar em m²")
    area_parede = models.DecimalFieldPlus("Área de Parede", null=True, blank=True, help_text="Informar em m²")
    uso = models.ForeignKeyPlus('comum.UsoSala', blank=True, null=True, verbose_name='Uso da sala')
    classificacao = models.ForeignKeyPlus('comum.ClassificacaoSala', blank=True, null=True, verbose_name='Classificação')

    # Acabamento e sistemas prediais
    instalacao_eletrica = models.ManyToManyFieldPlus('comum.InstalacaoEletricaSala', blank=True, verbose_name='Instalação Elétrica')
    instalacao_logica = models.ManyToManyFieldPlus('comum.InstalacaoLogicaSala', blank=True, verbose_name='Instalação de Lógica')
    instalacao_hidraulica = models.ManyToManyFieldPlus('comum.InstalacaoHidraulicaSala', blank=True, verbose_name='Instalação Hidráulica')
    instalacao_gases = models.ManyToManyFieldPlus('comum.InstalacaoGasesSala', blank=True, verbose_name='Instalação de Gases')
    climatizacao = models.ManyToManyFieldPlus('comum.ClimatizacaoSala', blank=True, verbose_name='Climatização')
    acabamento_parede = models.ManyToManyFieldPlus('comum.AcabamentoParedeSala', blank=True, verbose_name='Acabamento das Paredes')
    piso = models.ManyToManyFieldPlus('comum.PisoSala', blank=True, verbose_name='Piso')
    forro = models.ManyToManyFieldPlus('comum.ForroSala', blank=True, verbose_name='Forro')
    esquadrias = models.ManyToManyFieldPlus('comum.EsquadriasSala', blank=True, verbose_name='Esquadrias')

    # Managers
    objects = models.Manager()
    ativas = AtivasManager()

    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'
        unique_together = ('nome', 'predio')
        ordering = ('nome',)
        permissions = (('pode_avaliar_solicitacao_reserva_de_sala', 'Pode avaliar solicitação reserva de sala'),)

    def __str__(self):
        return f"{self.nome} - {str(self.predio)}"

    def get_absolute_url(self):
        return f"/comum/sala/visualizar/{self.id:d}/"

    # RN4 Sala disponível para agendamento, é uma sala com o status ativo e agendável
    #  verdadeiro e ter pelo menos um avaliador responsável pela sala.
    def is_agendavel(self):
        return self.ativa and self.agendavel and self.avaliadores_de_agendamentos.exists()

    def pode_agendar(self, user):
        if self.restringir_agendamentos_no_campus:
            return self.predio.uo == get_uo(user)
        else:
            return True

    def get_solicitacoes_reserva_pendentes(self, data_inicio, data_fim, hora_inicio=None, hora_fim=None):
        """
            Retornas solicitações pendentes que conflitam com os parâmetros passados
        """
        solicitacoes_conflitantes = SolicitacaoReservaSala.pendentes.filter(sala=self)
        # Remove as solicitações que a data_fim vem antes da data_inicio de pesquisa
        solicitacoes_sem_antes = solicitacoes_conflitantes.exclude(data_fim__lt=data_inicio)
        # Remove as solicitações que a data_inicio vem depois da data_fim de pesquisa
        solicitacoes_sem_depois = solicitacoes_conflitantes.exclude(data_inicio__gt=data_fim)
        solicitacoes_conflitantes = solicitacoes_sem_antes & solicitacoes_sem_depois
        if hora_inicio and hora_fim:
            # Remove as solicitações que a data_fim é igual a data_inicio mas a hora não conflita
            solicitacoes_sem_antes = solicitacoes_conflitantes.exclude(Q(data_fim=data_inicio) & (Q(hora_fim__lte=hora_inicio) | Q(hora_inicio__gte=hora_fim)))
            # Remove as solicitações que a data_inicio é igual a data_fim mas a hora não conflita
            solicitacoes_sem_depois = solicitacoes_conflitantes.exclude(Q(data_inicio=data_fim) & (Q(hora_fim__lte=hora_inicio) | Q(hora_inicio__gte=hora_fim)))
            # Adicionando as que são exatamente iguais
            solicitacoes_iguais = solicitacoes_conflitantes.filter(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim)
            solicitacoes_conflitantes = solicitacoes_sem_antes & solicitacoes_sem_depois
            return solicitacoes_conflitantes | solicitacoes_iguais

        return solicitacoes_conflitantes

    def get_solicitacoes_conflitantes(self, data_inicio, data_fim):
        """
            Retona uma lista de solicitações que estão conflitando com as datas nos parâmetros, levando em consideração a recorrência
        """
        solicitacoes_candidatas = self.get_solicitacoes_reserva_pendentes(data_inicio.date(), data_fim.date(), data_inicio.time(), data_fim.time())
        esperar_por_ids = []
        for solicitacao_candidata in solicitacoes_candidatas:
            for datas_candidatas_inicio, datas_candidatas_fim in solicitacao_candidata.get_datas_solicitadas():
                if not (data_inicio >= datas_candidatas_fim or data_fim <= datas_candidatas_inicio):
                    esperar_por_ids.append(solicitacao_candidata.id)

        return SolicitacaoReservaSala.objects.filter(id__in=esperar_por_ids)

    def get_reservas(self, data_inicio, data_fim):
        """
            Retornas reservas (provinientes de uma solicitações atendidas ou de uma indisponibilização) que conflitam com os parâmetros passados
        """
        reservas = ReservaSala.deferidas.filter(sala=self)

        # Remove as reservas que a data_fim vem antes da data_inicio de pesquisa
        reservas = reservas.exclude(data_fim__lte=data_inicio)
        # Remove as reservas que a data_inicio vem depois da data_fim de pesquisa
        reservas = reservas.exclude(data_inicio__gte=data_fim)
        return reservas

    def tem_conflito_reserva(self, solicitacao):
        for [solicitacao_data_inicio, solicitacao_data_fim] in solicitacao.get_datas_solicitadas():
            if self.get_reservas(solicitacao_data_inicio, solicitacao_data_fim).exists():
                return True
        return False

    def programacao_atual(self, solicitacao_atual=None):
        # a partir do mês corrente
        data_agora = datetime.now()
        ano_corrente = data_agora.year
        mes_corrente = data_agora.month
        # ------------
        # até o mês do último agendamento que 'caia' pelo menos dentro do mês corrente
        qs_solicitacoes = SolicitacaoReservaSala.pendentes.filter(sala=self)
        qs_reservas = ReservaSala.deferidas.filter(sala=self)
        cal_meses = []
        if qs_solicitacoes or qs_reservas:
            # pega data_fim do último agendamento
            if not qs_solicitacoes:
                data_fim = qs_reservas.latest('data_fim').data_fim.date()
            elif not qs_reservas:
                data_fim = qs_solicitacoes.latest('data_fim').data_fim
            else:
                data_fim_solicitacao = qs_solicitacoes.latest('data_fim').data_fim
                data_fim_reserva = qs_reservas.latest('data_fim').data_fim.date()
                data_fim = data_fim_solicitacao
                if data_fim_reserva > data_fim_solicitacao:
                    data_fim = data_fim_reserva
            # o último agendamento deve 'cair' pelo menos dentro do mês corrente
            # (mes agenda >= mes corrente E ano agenda >= ano corrente) OU (ano agenda > ano corrente)
            # ex:
            #    mes/ano corrente = 10/2013
            #    mes/ano solicitacao   = 01/2014
            #    ** o mes da solicitacao é menor que o mês corrente (o teste (mes solicitacao >= mes corrente E ano solicitacao >= ano corrente) FALHA!!)
            #    ** porém, ano solicitacao é maior (por isso da necessidade do teste (ano solicitacao > ano corrente)
            if (data_fim.year == ano_corrente and data_fim.month >= mes_corrente) or (data_fim.year > ano_corrente):
                ultimo_ano = data_fim.year
                ultimo_mes = data_fim.month

                cal = CalendarioPlus()
                cal.mostrar_mes_e_ano = True

                mes = mes_corrente  # inicializa mês
                for ano in range(ano_corrente, ultimo_ano + 1):
                    mes_final = 12  # por padrão
                    if ano == ultimo_ano:
                        mes_final = ultimo_mes
                    for mes in range(mes, mes_final + 1):
                        # -----------------------
                        # Adição das Solicitações
                        for solicitacao in qs_solicitacoes:
                            solicitacao_conflito = False
                            for [agenda_data_inicio, agenda_data_fim] in solicitacao.get_datas_solicitadas():
                                if agenda_data_inicio.year == ano and agenda_data_inicio.month == mes:
                                    if solicitacao_atual:
                                        for [solicitacao_data_inicio, solicitacao_data_fim] in solicitacao_atual.get_datas_solicitadas():
                                            if agenda_data_inicio.date() == solicitacao_data_inicio.date() and solicitacao == solicitacao_atual:
                                                solicitacao_conflito = True
                                                break

                                    dia_todo_list = solicitacao.get_dia_todo_list()
                                    title = f'Solicitação de {solicitacao.solicitante.get_relacionamento()}'
                                    if solicitacao_atual and solicitacao_conflito:
                                        css = 'evento'
                                    else:
                                        css = 'alert'

                                    # Se for o dia todo os eventos são separados, o primeiro e o ultimo tem o horário diferenciado
                                    if dia_todo_list:
                                        data_fim = datetime(agenda_data_inicio.year, agenda_data_inicio.month, agenda_data_inicio.day, 23, 59, 59)  # hour,minute,second
                                        horario = '{} às {}'.format(agenda_data_inicio.strftime("%H:%M"), data_fim.strftime("%H:%M"))
                                        if solicitacao.pode_ver():
                                            descricao = '<a href="/comum/sala/ver_solicitacao/{}/"><strong>{}</strong> {}</a>'.format(
                                                solicitacao.id, horario, solicitacao.justificativa
                                            )
                                        else:
                                            descricao = f'<p><strong>{horario}</strong> {solicitacao.justificativa}</p>'
                                        cal.adicionar_evento_calendario(agenda_data_inicio, data_fim, descricao, css, title)

                                        for dia_todo in dia_todo_list:
                                            horario = 'Todo o dia'
                                            if solicitacao.pode_ver():
                                                descricao = '<a href="/comum/sala/ver_solicitacao/{}/"><strong>{}</strong> {}</a>'.format(
                                                    solicitacao.id, horario, solicitacao.justificativa
                                                )
                                            else:
                                                descricao = f'<p><strong>{horario}</strong> {solicitacao.justificativa}</p>'
                                            cal.adicionar_evento_calendario(dia_todo, dia_todo, descricao, css, title, dia_todo=True)

                                        data_inicio = datetime(agenda_data_fim.year, agenda_data_fim.month, agenda_data_fim.day, 0, 0, 0)  # hour,minute,second
                                        horario = '{} às {}'.format(data_inicio.strftime("%H:%M"), agenda_data_fim.strftime("%H:%M"))
                                        if solicitacao.pode_ver():
                                            descricao = '<a href="/comum/sala/ver_solicitacao/{}/"><strong>{}</strong> {}</a>'.format(
                                                solicitacao.id, horario, solicitacao.justificativa
                                            )
                                        else:
                                            descricao = f'<p><strong>{horario}</strong> {solicitacao.justificativa}</p>'
                                        cal.adicionar_evento_calendario(data_inicio, agenda_data_fim, descricao, css, title)
                                    else:
                                        horario = '{} às {}'.format(agenda_data_inicio.strftime("%H:%M"), agenda_data_fim.strftime("%H:%M"))
                                        if solicitacao.pode_ver():
                                            descricao = '<a href="/comum/sala/ver_solicitacao/{}/"><strong>{}</strong> {}</a>'.format(
                                                solicitacao.id, horario, solicitacao.justificativa
                                            )
                                        else:
                                            descricao = f'<p><strong>{horario}</strong> {solicitacao.justificativa}</p>'
                                        cal.adicionar_evento_calendario(agenda_data_inicio, agenda_data_fim, descricao, css, title)
                        # -------------------
                        # Adição das Reservas
                        data_inicial = date(ano, mes, 0o1)
                        data_final = date(ano, mes, 0o1) + relativedelta(months=+1)
                        qs_reservas_inicio = qs_reservas.filter(data_inicio__range=[data_inicial, data_final])
                        qs_reservas_fim = qs_reservas.filter(data_fim__range=[data_inicial, data_final])
                        queryset_reservas = qs_reservas_inicio | qs_reservas_fim
                        for reserva in queryset_reservas:
                            agenda_data_inicio = reserva.data_inicio
                            agenda_data_fim = reserva.data_fim
                            dia_todo_list = reserva.get_dia_todo_list()

                            if hasattr(reserva, 'indisponibilizacaosala'):
                                indisponibilizacao = reserva.indisponibilizacaosala
                                css = 'error'
                                title = f'Registrado por {indisponibilizacao.usuario}'
                                # Se for o dia todo os eventos são separados, o primeiro e o ultimo tem o horário diferenciado
                                if dia_todo_list:
                                    data_fim = datetime(agenda_data_inicio.year, agenda_data_inicio.month, agenda_data_inicio.day, 23, 59, 59)  # hour,minute,second
                                    horario = '{} às {}'.format(agenda_data_inicio.strftime("%H:%M"), data_fim.strftime("%H:%M"))
                                    descricao = '<a href="/comum/sala/ver_indisponibilizacao/{}/"><strong>{}</strong> {}</a>'.format(
                                        indisponibilizacao.id, horario, indisponibilizacao.justificativa
                                    )
                                    cal.adicionar_evento_calendario(agenda_data_inicio, data_fim, descricao, css, title)

                                    for dia_todo in dia_todo_list:
                                        horario = 'Todo o dia'
                                        descricao = '<a href="/comum/sala/ver_indisponibilizacao/{}/"><strong>{}</strong> {}</a>'.format(
                                            indisponibilizacao.id, horario, indisponibilizacao.justificativa
                                        )
                                        cal.adicionar_evento_calendario(dia_todo, dia_todo, descricao, css, title, dia_todo=True)

                                    data_inicio = datetime(agenda_data_fim.year, agenda_data_fim.month, agenda_data_fim.day, 0, 0, 0)  # hour,minute,second
                                    horario = '{} às {}'.format(data_inicio.strftime("%H:%M"), agenda_data_fim.strftime("%H:%M"))
                                    descricao = '<a href="/comum/sala/ver_indisponibilizacao/{}/"><strong>{}</strong> {}</a>'.format(
                                        indisponibilizacao.id, horario, indisponibilizacao.justificativa
                                    )
                                    cal.adicionar_evento_calendario(data_inicio, agenda_data_fim, descricao, css, title)
                                else:
                                    horario = '{} às {}'.format(agenda_data_inicio.strftime("%H:%M"), agenda_data_fim.strftime("%H:%M"))
                                    descricao = '<a href="/comum/sala/ver_indisponibilizacao/{}/"><strong>{}</strong> {}</a>'.format(
                                        indisponibilizacao.id, horario, indisponibilizacao.justificativa
                                    )
                                    cal.adicionar_evento_calendario(agenda_data_inicio, agenda_data_fim, descricao, css, title)

                            else:
                                solicitacao = reserva.solicitacao
                                if solicitacao_atual and solicitacao == solicitacao_atual:
                                    css = 'evento'
                                else:
                                    css = 'success'
                                title = f'Agendada para {solicitacao.solicitante.get_relacionamento()}'

                                # Se for o dia todo os eventos são separados, o primeiro e o ultimo tem o horário diferenciado
                                if dia_todo_list:
                                    data_fim = datetime(agenda_data_inicio.year, agenda_data_inicio.month, agenda_data_inicio.day, 23, 59, 59)  # hour,minute,second
                                    horario = '{} às {}'.format(agenda_data_inicio.strftime("%H:%M"), data_fim.strftime("%H:%M"))
                                    if solicitacao.pode_ver():
                                        descricao = '<a href="/comum/sala/ver_solicitacao/{}/"><strong>{}</strong> {}</a>'.format(
                                            solicitacao.id, horario, truncatechars(solicitacao.justificativa, 75)
                                        )
                                    else:
                                        descricao = f'<p><strong>{horario}</strong> {truncatechars(solicitacao.justificativa, 75)}</p>'
                                    cal.adicionar_evento_calendario(agenda_data_inicio, data_fim, descricao, css, title)

                                    for dia_todo in dia_todo_list:
                                        horario = 'Todo o dia'
                                        if solicitacao.pode_ver():
                                            descricao = '<a href="/comum/sala/ver_solicitacao/{}/"><strong>{}</strong> {}</a>'.format(
                                                solicitacao.id, horario, truncatechars(solicitacao.justificativa, 75)
                                            )
                                        else:
                                            descricao = f'<p><strong>{horario}</strong> {truncatechars(solicitacao.justificativa, 75)}</p>'
                                        cal.adicionar_evento_calendario(dia_todo, dia_todo, descricao, css, title, dia_todo=True)

                                    data_inicio = datetime(agenda_data_fim.year, agenda_data_fim.month, agenda_data_fim.day, 0, 0, 0)  # hour,minute,second
                                    horario = '{} às {}'.format(data_inicio.strftime("%H:%M"), agenda_data_fim.strftime("%H:%M"))
                                    if solicitacao.pode_ver():
                                        descricao = '<a href="/comum/sala/ver_solicitacao/{}/"><strong>{}</strong> {}</a>'.format(
                                            solicitacao.id, horario, truncatechars(solicitacao.justificativa, 75)
                                        )
                                    else:
                                        descricao = f'<p><strong>{horario}</strong> {truncatechars(solicitacao.justificativa, 75)}</p>'
                                    cal.adicionar_evento_calendario(data_inicio, agenda_data_fim, descricao, css, title)
                                else:
                                    horario = '{} às {}'.format(agenda_data_inicio.strftime("%H:%M"), agenda_data_fim.strftime("%H:%M"))
                                    if solicitacao.pode_ver():
                                        descricao = '<a href="/comum/sala/ver_solicitacao/{}/"><strong>{}</strong> {}</a>'.format(
                                            solicitacao.id, horario, truncatechars(solicitacao.justificativa, 75)
                                        )
                                    else:
                                        descricao = f'<p><strong>{horario}</strong> {truncatechars(solicitacao.justificativa, 75)}</p>'
                                    cal.adicionar_evento_calendario(agenda_data_inicio, agenda_data_fim, descricao, css, title)

                        # -------------------
                        cal_meses.append(cal.formato_mes(ano, mes))
                        # -------------------
                    mes = 1  # reinicia mês (o ano subsequente deve começar por janeiro)
        # ------------
        return cal_meses  # lista de calendários formato mês

    # ----------------------------------------

    @classmethod
    def eh_avaliador_salas(cls, user):
        return user.has_perm('comum.pode_avaliar_solicitacao_reserva_de_sala') and user.salas_avaliadas.exists()

    def eh_avaliador(self, user):
        return user.has_perm('comum.pode_avaliar_solicitacao_reserva_de_sala') and self.avaliadores_de_agendamentos.filter(id=user.id).exists()

    def tem_dados_complementares(self):
        return self.area_util or self.area_parede or self.uso or self.classificacao

    def tem_acabamento_sistemas_prediais(self):
        return self.instalacao_eletrica.exists() or self.instalacao_logica.exists() or self.instalacao_hidraulica.exists() or self.instalacao_gases.exists() or self.climatizacao.exists() or self.acabamento_parede.exists() or self.piso.exists() or self.forro.exists() or self.esquadrias.exists()


class UsoSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Uso da Sala'
        verbose_name_plural = 'Usos da Sala'


class ClassificacaoSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    descricao_expandida = models.TextField(verbose_name="Descrição Expandida")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Classificação'
        verbose_name_plural = 'Classificações'

    def __str__(self):
        return '{} - {}'.format(self.descricao, self.descricao_expandida)


class InstalacaoEletricaSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Instalação Elétrica'
        verbose_name_plural = 'Instalações Elétricas'


class InstalacaoLogicaSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Instalação de Lógica'
        verbose_name_plural = 'Instalações de Lógica'


class InstalacaoHidraulicaSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Instalação Hidráulica'
        verbose_name_plural = 'Instalações Hidráulicas'


class InstalacaoGasesSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Instalação de Gases'
        verbose_name_plural = 'Instalações de Gases'


class ClimatizacaoSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Climatização'
        verbose_name_plural = 'Climatizações'


class AcabamentoParedeSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Acabamento da Parede'
        verbose_name_plural = 'Acabamentos das Paredes'


class PisoSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Piso'
        verbose_name_plural = 'Pisos'


class ForroSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Forro'
        verbose_name_plural = 'Forros'


class EsquadriasSala(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name="Descrição")
    ativo = models.BooleanField(verbose_name="Ativo", default=True)

    class Meta:
        verbose_name = 'Esquadria'
        verbose_name_plural = 'Esquadrias'


class SolicitacaoAbertasManager(models.Manager):
    def get_queryset(self):
        agora = datetime.now()
        return super().get_queryset().filter(data_hora_inicio__gt=agora)


class SolicitacaoPendentesManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO)


class SolicitacaoReservaSala(models.ModelPlus):
    RECORRENCIA_EVENTO_UNICO = 'evento_unico'
    RECORRENCIA_SEMANALMENTE = 'semanalmente'
    RECORRENCIA_QUINZENALMENTE = 'quinzenalmente'
    RECORRENCIA_MENSALMENTE = 'mensalmente'
    RECORRENCIA_CHOICES = (
        (RECORRENCIA_EVENTO_UNICO, 'Evento único'),
        (RECORRENCIA_SEMANALMENTE, 'Semanalmente'),
        (RECORRENCIA_QUINZENALMENTE, 'Quinzenalmente'),
        (RECORRENCIA_MENSALMENTE, 'Mensalmente'),
    )

    STATUS_DEFERIDA = 'deferida'
    STATUS_INDEFERIDA = 'indeferida'
    STATUS_PARCIALMENTE_DEFERIDA = 'parcialmente_deferida'
    STATUS_AGUARDANDO_AVALIACAO = 'aguardando_avaliacao'
    STATUS_EXCLUIDA = 'excluida'
    STATUS_CHOICES = (
        (STATUS_DEFERIDA, 'Deferida'),
        (STATUS_INDEFERIDA, 'Indeferida'),
        (STATUS_PARCIALMENTE_DEFERIDA, 'Parcialmente Deferida'),
        (STATUS_AGUARDANDO_AVALIACAO, 'Aguardando Avaliação'),
        (STATUS_EXCLUIDA, 'Excluída'),
    )

    sala = models.ForeignKeyPlus('Sala', verbose_name='Sala solicitada', on_delete=models.CASCADE)
    solicitante = models.ForeignKeyPlus('comum.User', related_name='solicitacao_reserva_solicitante', null=True)
    data_solicitacao = models.DateTimeFieldPlus('Data da Solicitação')
    data_inicio = models.DateFieldPlus('Data de Início')
    hora_inicio = models.TimeFieldPlus('Hora de Início')
    data_hora_inicio = models.DateTimeFieldPlus('Data Hora Início', null=False)
    data_fim = models.DateFieldPlus('Data de Fim')
    hora_fim = models.TimeFieldPlus('Hora de Fim')
    data_hora_fim = models.DateTimeFieldPlus('Data Hora Início', null=False)

    justificativa = models.TextField()
    recorrencia = models.CharFieldPlus('Recorrência', choices=RECORRENCIA_CHOICES)
    interessados_vinculos = models.ManyToManyFieldPlus('comum.Vinculo', blank=True)
    anexo = models.FileFieldPlus(
        'Anexo', upload_to='upload/comum/solicitacao_reserva_sala/',
        filetypes=['doc', 'pdf'],
        null=True, blank=True
    )
    # TODO: verificar que é melhor deixar aqui ou criar um modelo separado
    recorrencia_segunda = models.BooleanField("Segunda", default=False)
    recorrencia_terca = models.BooleanField("Terça", default=False)
    recorrencia_quarta = models.BooleanField("Quarta", default=False)
    recorrencia_quinta = models.BooleanField("Quinta", default=False)
    recorrencia_sexta = models.BooleanField("Sexta", default=False)
    recorrencia_sabado = models.BooleanField("Sábado", default=False)
    recorrencia_domingo = models.BooleanField("Domingo", default=False)
    status = models.CharFieldPlus('Situação', choices=STATUS_CHOICES, default=STATUS_AGUARDANDO_AVALIACAO)

    # avaliação
    data_avaliacao = models.DateTimeFieldPlus('Data da Avaliação', null=True)
    avaliador = CurrentUserField(default=None, related_name='solicitacao_reserva_avaliador')
    observacao_avaliador = models.TextField('Observação', blank=True)

    # Cancelamento pelo próprio solicitante
    cancelada = models.BooleanField('Cancelada', default=False)
    justificativa_cancelamento = models.TextField('Justificativa do Cancelamento', blank=True)
    data_cancelamento = models.DateTimeFieldPlus('Data da Avaliação', null=True)

    objects = models.Manager()
    abertas = SolicitacaoAbertasManager()
    pendentes = SolicitacaoPendentesManager()

    class Meta:
        verbose_name = 'Solicitação de Reserva de Sala'
        verbose_name_plural = 'Solicitações de Reserva de Sala'

    def get_absolute_url(self):
        return f"/comum/sala/ver_solicitacao/{self.id:d}/"

    def save(self, *args, **kwargs):
        self.data_hora_inicio = self.get_data_hora_inicio()
        self.data_hora_fim = self.get_data_hora_fim()
        super().save(*args, **kwargs)

    def gerar_reservas(self):
        for data_inicio, data_fim in self.get_datas_solicitadas():
            reserva = ReservaSala()
            reserva.sala = self.sala
            reserva.solicitacao = self
            reserva.data_inicio = data_inicio
            reserva.data_fim = data_fim
            reserva.save()

    def get_esperar_por(self):
        """
            Retona uma lista de solicitações que estão conflitando com a solicitação, levando em consideração a recorrência
        """
        solicitacoes_candidatas = self.sala.get_solicitacoes_reserva_pendentes(self.data_inicio, self.data_fim, self.hora_inicio, self.hora_fim).exclude(id=self.id)
        esperar_por_ids = []
        for solicitacao_candidata in solicitacoes_candidatas:
            for datas_candidatas_inicio, datas_candidatas_fim in solicitacao_candidata.get_datas_solicitadas():
                for datas_solicitadas_inicio, datas_solicitadas_fim in self.get_datas_solicitadas():
                    if not (datas_solicitadas_inicio >= datas_candidatas_fim or datas_solicitadas_fim <= datas_candidatas_inicio):
                        esperar_por_ids.append(solicitacao_candidata.id)

        return SolicitacaoReservaSala.objects.filter(id__in=esperar_por_ids)

    def get_datas_solicitadas(self):
        """
            Retorna datas solicitadas em datetime como uma lista de tuplas, cada tupla contem o datetime inicio e o fim
        """
        if hasattr(self, 'datas_solicitadas'):
            return self.datas_solicitadas

        primeira_data_adicionada = None
        qtd_dias_mes = []
        if self.recorrencia != self.RECORRENCIA_EVENTO_UNICO:
            datas_solicitadas = []
            for index, data in enumerate(daterange(self.data_inicio, self.data_fim)):
                if datas_solicitadas:
                    primeira_data_adicionada = datas_solicitadas[0][0].date()

                if self.recorrencia == self.RECORRENCIA_SEMANALMENTE:
                    self.__adicionar_dia_recorrencia(datas_solicitadas, data)

                # O periodo é quinzenal porém com relação a data quinzena é igual a 14 dias
                elif self.recorrencia == self.RECORRENCIA_QUINZENALMENTE:
                    if not primeira_data_adicionada or (
                        primeira_data_adicionada
                        and primeira_data_adicionada + timedelta(14 * ((index + 1) // 14)) <= data < primeira_data_adicionada + timedelta(14 * ((index + 1) // 14) + 7)
                    ):
                        self.__adicionar_dia_recorrencia(datas_solicitadas, data)

                elif self.recorrencia == self.RECORRENCIA_MENSALMENTE:
                    # pegar a quantidade do mês e decrementar
                    qtd_dias = calendar.monthrange(data.year, data.month)[1]
                    if [data.month, qtd_dias] not in qtd_dias_mes:
                        qtd_dias_mes.append([data.month, qtd_dias])

                    quantidade_mes = 0
                    for mes, dias in qtd_dias_mes:
                        if index - dias >= 0:
                            index -= dias
                            quantidade_mes += 1
                        else:
                            break

                    if not primeira_data_adicionada or adicionar_mes(primeira_data_adicionada, quantidade_mes) <= data < adicionar_mes(
                        primeira_data_adicionada, quantidade_mes
                    ) + timedelta(7):
                        self.__adicionar_dia_recorrencia(datas_solicitadas, data)

            return datas_solicitadas

        return [[self.get_data_hora_inicio(), self.get_data_hora_fim()]]

    def __adicionar_dia_recorrencia(self, datas_solicitadas, data):
        """
            Adicionar a data na lista de datas_solicitadas com base na recorrencia
        """
        # data.weekday() = Monday is 0 and Sunday is 6
        SEGUNDA = 0
        TERCA = 1
        QUARTA = 2
        QUINTA = 3
        SEXTA = 4
        SABADO = 5
        DOMINGO = 6

        if self.recorrencia_segunda and data.weekday() == SEGUNDA:
            datas_solicitadas.append([self.get_data_hora_inicio(data), self.get_data_hora_fim(data)])
        if self.recorrencia_terca and data.weekday() == TERCA:
            datas_solicitadas.append([self.get_data_hora_inicio(data), self.get_data_hora_fim(data)])
        if self.recorrencia_quarta and data.weekday() == QUARTA:
            datas_solicitadas.append([self.get_data_hora_inicio(data), self.get_data_hora_fim(data)])
        if self.recorrencia_quinta and data.weekday() == QUINTA:
            datas_solicitadas.append([self.get_data_hora_inicio(data), self.get_data_hora_fim(data)])
        if self.recorrencia_sexta and data.weekday() == SEXTA:
            datas_solicitadas.append([self.get_data_hora_inicio(data), self.get_data_hora_fim(data)])
        if self.recorrencia_sabado and data.weekday() == SABADO:
            datas_solicitadas.append([self.get_data_hora_inicio(data), self.get_data_hora_fim(data)])
        if self.recorrencia_domingo and data.weekday() == DOMINGO:
            datas_solicitadas.append([self.get_data_hora_inicio(data), self.get_data_hora_fim(data)])

    def get_recorrencias(self):
        recorrencias = []
        if self.recorrencia != SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO:
            if self.recorrencia_segunda:
                recorrencias.append('segunda')
            if self.recorrencia_terca:
                recorrencias.append('terca')
            if self.recorrencia_quarta:
                recorrencias.append('quarta')
            if self.recorrencia_quinta:
                recorrencias.append('quinta')
            if self.recorrencia_sexta:
                recorrencias.append('sexta')
            if self.recorrencia_sabado:
                recorrencias.append('sabado')
            if self.recorrencia_domingo:
                recorrencias.append('domingo')
        return ', '.join(recorrencias)

    def get_ch_solicitacao(self):
        seconds = 0
        for [solicitacao_data_inicio, solicitacao_data_fim] in self.get_datas_solicitadas():
            periodo = (solicitacao_data_fim - solicitacao_data_inicio)
            seconds += periodo.seconds
        ch_reserva = seconds / 3600
        return ch_reserva

    def pode_cancelar(self, user=None):
        if not user:
            user = tl.get_user()

        eh_avaliador = self.sala.eh_avaliador(user)
        return (eh_avaliador and self.status == self.STATUS_DEFERIDA and self.data_hora_fim > datetime.now()) or (
            self.solicitante == user and self.status != self.STATUS_INDEFERIDA and self.status != self.STATUS_EXCLUIDA and self.data_hora_fim > datetime.now()
        )

    # UC04 - RN1 essa opção só estará disponível para avaliador e se a data final da requisição for menor ou igual a data atual e a requisição não tenha sido avaliada.
    def pode_avaliar(self, user=None):
        if not user:
            user = tl.get_user()

        eh_avaliador = self.sala.eh_avaliador(user)
        return (user.is_superuser or eh_avaliador) and self.data_hora_fim >= datetime.now() and (self.status == SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO)

    def pode_excluir(self, user=None):
        if not user:
            user = tl.get_user()
        return (user.is_superuser) or (self.solicitante == user and self.status == SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO)

    def pode_ver(self, user=None):
        if not user:
            user = tl.get_user()

        eh_avaliador = self.sala.eh_avaliador(user)
        return (
            user.is_superuser
            or eh_avaliador
            or self.solicitante == user
            or self.status == SolicitacaoReservaSala.STATUS_DEFERIDA
            or self.status == SolicitacaoReservaSala.STATUS_PARCIALMENTE_DEFERIDA
        )

    def vinculos_envolvidos(self, solicitante=True, interessados=True, avaliadores_sala=True):
        vinculos = []
        if solicitante:
            vinculos.append(self.solicitante.get_vinculo())
        if interessados:
            for interessado in self.interessados_vinculos.all():
                vinculos.append(interessado)
        if avaliadores_sala:
            for avaliador in self.sala.avaliadores_de_agendamentos.all():
                vinculos.append(avaliador.get_vinculo())

        return list(set(vinculos))

    def notificar_cadastro(self):
        if self.status == SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO:
            url = f'{settings.SITE_URL}/comum/sala/ver_solicitacao/{self.id}/'
            titulo = '[SUAP] Reservas de Salas: Nova Solicitação'
            mensagem = '''<h1>Solicitação de Reserva de Sala Efetuada</h1>
                <dl>
                    <dt>Sala:</dt><dd>{}</dd>
                    <dt>Período:</dt><dd>{}</dd>
                    <dt>Requisitante:</dt><dd>{}</dd>
                    <dt>Link da Solicitação:</dt><dd>{}</dd>
                </dl>'''.format(
                self.sala, self.get_periodo(), self.solicitante.get_profile().nome, url
            )
            vinculos = self.vinculos_envolvidos(solicitante=True, interessados=True, avaliadores_sala=True)
            send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, vinculos)

    def notificar_avaliacao(self):
        if self.status != SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO:
            avaliador = "SUAP"
            if self.avaliador:
                avaliador = self.avaliador.get_profile().nome

            titulo = f'[SUAP] Reservas de Salas: Solicitação {self.get_status_display()}'
            mensagem = '''<h1>Solicitação de Reserva de Sala: {}</h1>
                <dl>
                    <dt>Sala:</dt><dd>{}</dd>
                    <dt>Período:</dt><dd>{}</dd>
                    <dt>Requisitante:</dt><dd>{}</dd>
                    <dt>Avaliador:</dt><dd>{}</dd>'''.format(
                self.get_status_display(), self.sala, self.get_periodo(), self.solicitante.get_profile().nome, avaliador
            )
            if self.observacao_avaliador:
                mensagem += f'<dt>Observação do Avaliador:</dt><dd>{self.observacao_avaliador}</dd>'
            mensagem += '</dl>'
            vinculos = self.vinculos_envolvidos(solicitante=True, interessados=True, avaliadores_sala=False)
            send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, vinculos)

    def notificar_cancelamento(self):
        if self.status == SolicitacaoReservaSala.STATUS_INDEFERIDA:
            cancelada_por = self.solicitante
            titulo = '[SUAP] Reservas de Salas: Solicitação Cancelada'
            mensagem = '''<h1>Solicitação de Reserva de Sala Cancelada</h1>
                <dl>
                    <dt>Sala:</dt><dd>{}</dd>
                    <dt>Período:</dt><dd>{}</dd>
                    <dt>Requisitante:</dt><dd>{}</dd>
                    <dt>Cancelada por:</dt><dd>{}</dd>
                    '''.format(
                self.sala, self.get_periodo(), self.solicitante.get_profile().nome, cancelada_por
            )
            if self.observacao_avaliador:
                mensagem += f'<dt>Observação do Avaliador:</dt><dd>{self.observacao_avaliador}</dd>'
            mensagem += '</dl>'
            vinculos = self.vinculos_envolvidos(solicitante=False, interessados=True, avaliadores_sala=True)
            send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, vinculos)

    def get_data_hora_inicio(self, data=None):
        if not data:
            data = self.data_inicio
        return datetime.combine(data, self.hora_inicio)

    def get_data_hora_fim(self, data=None):
        if not data:
            data = self.data_fim
        return datetime.combine(data, self.hora_fim)

    def get_periodo(self):
        if self.recorrencia == SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO:
            if self.data_fim == self.data_inicio:
                return '{} às {} do dia {}'.format(self.hora_inicio.strftime('%H:%M'), self.hora_fim.strftime('%H:%M'), self.data_inicio.strftime('%d/%m/%Y'))
            else:
                return '{} do dia {} às {} do dia {}'.format(
                    self.hora_inicio.strftime('%H:%M'), self.data_inicio.strftime('%d/%m/%Y'), self.hora_fim.strftime('%H:%M'), self.data_fim.strftime('%d/%m/%Y')
                )
        else:
            datas = '{} a {}'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))
            if self.data_fim == self.data_inicio:
                datas = self.data_inicio.strftime('%d/%m/%Y')
            return '{} | Horário: {} - {}'.format(datas, self.hora_inicio.strftime('%H:%M'), self.hora_fim.strftime('%H:%M'))

    def get_dia_todo_list(self):
        dia_todo = []
        if self.recorrencia == self.RECORRENCIA_EVENTO_UNICO:
            dias = (self.data_fim - self.data_inicio).days
            if dias == 1:
                dia_todo.append(self.data_inicio + timedelta(1))
            else:
                for dia in range(1, dias):
                    dia_todo.append(self.data_inicio + timedelta(dia))

        return dia_todo


class ReservaDeferidasManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(cancelada=False)


class ReservaSala(models.ModelPlus):
    sala = models.ForeignKeyPlus('Sala', verbose_name='Sala Solicitada', on_delete=models.CASCADE)
    solicitacao = models.ForeignKeyPlus('SolicitacaoReservaSala', verbose_name='Solicitação de Sala', null=True, on_delete=models.CASCADE)
    data_inicio = models.DateTimeFieldPlus('Data/Hora de Início')
    data_fim = models.DateTimeFieldPlus('Data/Hora Final')

    cancelada = models.BooleanField('Cancelada', default=False)
    justificativa_cancelamento = models.TextField('Justificativa do Cancelamento', blank=True)
    cancelada_por = CurrentUserField(default=None)
    data_cancelamento = models.DateTimeFieldPlus('Data da Avaliação', null=True)

    ocorreu = models.BooleanField('Atividade Ocorreu', null=True)
    motivo_nao_ocorreu = models.TextField('Motivo da Atividade Não Ter Ocorrido', blank=True)

    objects = models.Manager()
    deferidas = ReservaDeferidasManager()

    class Meta:
        verbose_name = 'Reserva de Sala'
        verbose_name_plural = 'Reservas de Salas'

    def get_periodo(self):
        if self.solicitacao and self.solicitacao.recorrencia == SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO:
            if self.data_fim.date() == self.data_inicio.date():
                return '{} às {} do dia {}'.format(self.data_inicio.strftime('%H:%M'), self.data_fim.strftime('%H:%M'), self.data_inicio.strftime('%d/%m/%Y'))
            else:
                return '{} do dia {} às {} do dia {}'.format(
                    self.data_inicio.strftime('%H:%M'), self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%H:%M'), self.data_fim.strftime('%d/%m/%Y')
                )
        else:
            datas = '{} a {}'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))
            if self.data_fim.date() == self.data_inicio.date():
                datas = self.data_inicio.strftime('%d/%m/%Y')
            return '{} | Horário: {} - {}'.format(datas, self.data_inicio.strftime('%H:%M'), self.data_fim.strftime('%H:%M'))

    def pode_cancelar(self, user=None):
        if not user:
            user = tl.get_user()

        eh_avaliador = self.sala.eh_avaliador(user)
        # Não deve ser possível cancelar reserva de sala deferida após ter passado o período de reserva da mesma.
        return (eh_avaliador or self.solicitacao.solicitante == user) and self.data_fim > datetime.now()

    # RN7  A data final do registro de manutenção menor que a data atual.
    def pode_excluir(self, user=None):
        if not user:
            user = tl.get_user()

        eh_avaliador = user.salas_avaliadas.filter(id=self.sala_id).exists()
        return (user.is_superuser) or (eh_avaliador and self.data_fim > datetime.now())

    @atomic
    def cancelar(self, notificar=True):
        self.data_cancelamento = datetime.now()
        self.cancelada = True
        if self.solicitacao:
            # se ainda tiver reservas não canceladas
            if self.solicitacao.reservasala_set.filter(cancelada=False).exclude(id=self.id).exists():
                self.solicitacao.status = SolicitacaoReservaSala.STATUS_PARCIALMENTE_DEFERIDA
            else:
                self.solicitacao.status = SolicitacaoReservaSala.STATUS_INDEFERIDA

            self.solicitacao.save()

        self.save()
        if notificar:
            self.notificar_cancelamento()

    def notificar_cancelamento(self):
        if self.cancelada and self.solicitacao:
            titulo = '[SUAP] Reservas de Salas: Reserva Cancelada'
            mensagem = '''<h1>Reserva de Sala Cancelada:</h1>
                <dl>
                    <dt>Sala:</dt><dd>{}</dd>
                    <dt>Período:</dt><dd>{}</dd>
                    <dt>Requisitante:</dt><dd>{}</dd>
                    <dt>Motivo:</dt><dd>{}</dd>
                </dl>'''.format(
                self.sala, self.get_periodo(), self.solicitacao.solicitante.get_profile().nome, self.justificativa_cancelamento
            )
            vinculos = self.solicitacao.vinculos_envolvidos(solicitante=True, interessados=True, avaliadores_sala=True)
            send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, vinculos)

    def get_dia_todo_list(self):
        dia_todo = []
        dias = (self.data_fim - self.data_inicio).days
        for dia in range(1, dias):
            dia_todo.append(self.data_inicio + timedelta(dia))

        return dia_todo


class IndisponibilizacaoSalaEmAndamentoManager(models.Manager):
    def get_queryset(self):
        query_set = super().get_queryset()
        data_agora = datetime.now()
        # lista todos os registros de manutenção de salas na qual data inicio maiorigual que data atual e data fim menor/igual que data atual.
        query_set = query_set.filter(data_inicio__lte=data_agora, data_fim__gte=data_agora)
        return query_set


class IndisponibilizacaoSala(ReservaSala):
    usuario = CurrentUserField(related_name='indisponibilizacao_sala_usuario')
    data = models.DateTimeFieldPlus()
    justificativa = models.TextField()

    objects = models.Manager()
    em_andamento = IndisponibilizacaoSalaEmAndamentoManager()

    class Meta:
        verbose_name = 'Indisponibilização de Reserva de Sala'
        verbose_name_plural = 'Indisponibilizações de Reserva de Salas'


class RepresentanteLegal(PessoaFisica):
    matricula = models.CharField(max_length=7, unique=True)

    class Meta:
        verbose_name = 'Representante Legal'
        verbose_name_plural = 'Representantes Legais'


class GrauParentesco(models.ModelPlus):
    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=50)
    excluido = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Grau de Parentesco'
        verbose_name_plural = 'Graus de Parentesco'

    def __str__(self):
        return self.nome


class Pensionista(PessoaFisica):
    matricula = models.CharField("Matrícula do Pensionista", max_length=8, unique=True)
    representante_legal = models.ForeignKeyPlus(RepresentanteLegal, null=True, blank=True, on_delete=models.CASCADE)
    numero_processo = models.CharField(max_length=15, blank=True, null=True)
    grau_parentesco = models.ForeignKeyPlus(GrauParentesco, blank=True, null=True, on_delete=models.CASCADE)
    data_inicio_pagto_beneficio = models.DateField(blank=True, null=True)
    data_fim_pagto_beneficio = models.DateField(blank=True, null=True)

    @property
    def instituidor(self):
        if self.contracheque_set.all().exists():
            return self.contracheque_set.latest('id').servidor
        return None

    def get_absolute_url(self):
        return f'/comum/pensionista/{self.matricula}/'


class Dependente(PessoaFisica):
    matricula = models.CharField(max_length=8, unique=True)
    servidor = models.ForeignKeyPlus(Servidor, related_name='servidordependente', on_delete=models.CASCADE)
    representante_legal = models.ForeignKeyPlus(RepresentanteLegal, null=True, blank=True, on_delete=models.CASCADE)
    grau_parentesco = models.ForeignKeyPlus(GrauParentesco, blank=True, null=True, on_delete=models.CASCADE)
    codigo_condicao = models.CharField(max_length=3, null=True, blank=True)


class Beneficio(models.ModelPlus):
    codigo = models.CharField(max_length=2, null=True, unique=True)
    nome = models.CharField(max_length=30)
    excluido = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Benefício'
        verbose_name_plural = 'Benefícios'

    def __str__(self):
        return self.nome


class BeneficioDependente(models.ModelPlus):
    dependente = models.ForeignKeyPlus(Dependente, on_delete=models.CASCADE)
    beneficio = models.ForeignKeyPlus(Beneficio, on_delete=models.CASCADE)
    data_inicio = models.DateField()
    data_termino = models.DateField(null=True)

    class Meta:
        verbose_name = 'Associação Benefício-Dependente'
        verbose_name_plural = 'Associações Benefício-Dependente'

    def __str__(self):
        return '{} - {} - {}'.format(self.dependente.nome, self.beneficio.nome, self.data_inicio.strftime('%d-%m-%Y'))


class SetorTelefone(models.ModelPlus):
    """
    Armazena os telefones dos setores.
    """

    setor = models.ForeignKeyPlus(Setor, on_delete=models.CASCADE)
    numero = models.BrTelefoneField('Número')
    ramal = models.CharField(max_length=5, blank=True)  # Evitar que CharField tenha null=True
    observacao = models.CharField('Observação', max_length=50, blank=True)  # Evitar que CharField tenha null=True

    class Meta:
        verbose_name = 'Telefone do Setor'
        verbose_name_plural = 'Telefones do Setor'

    def __str__(self):
        out = []
        if self.numero:
            out.append(self.numero)
        if self.ramal:
            if self.numero:
                out.append(f'(ramal: {self.ramal})')
            else:
                out.append(f'ramal: {self.ramal}')
        return ' '.join(out)


class ContatoEmergencia(models.ModelPlus):
    pessoa_fisica = models.ForeignKeyPlus(PessoaFisica, verbose_name='Servidor', on_delete=models.CASCADE)
    nome_contato = models.CharFieldPlus('Nome do Contato', max_length=200, blank=False, null=False)
    telefone = models.BrTelefoneField('Telefone', max_length=15)

    class Meta:
        verbose_name = 'Contato de Emergência'
        verbose_name_plural = 'Contatos de Emergência'

    def __str__(self):
        return 'Contato de Emergência de {} ({})'.format(self.pessoa_fisica.nome_usual, self.nome_contato)


class Arquivo(models.ModelPlus):
    FS_ROOT_PATH = 'upload/'
    DIR_PKI = settings.BASE_DIR + '/djtools/security/pki/'
    PRIV_KEY = 'ksb_priv_key.pem'
    PUB_KEY = 'ksb_pub_key.pem'
    CERT = 'ksb_cert.pem'
    PASSWORD = '12345'
    nome = models.CharField(null=False, unique=False, max_length=255)
    data_geracao = models.DateTimeField()
    assinatura = models.CharField(max_length=500)
    vinculo = models.ForeignKeyPlus('comum.Vinculo', null=True)

    criptografado = models.BooleanField(null=False, default=True)

    def __str__(self):
        return self.nome

    @staticmethod
    def codificar(plain_id):
        return b64encode('IFRN' + str(((plain_id * 2) + 133) * -1))

    @staticmethod
    def decodificar(masked_id):
        return ((int(b64decode(masked_id)[4:]) * -1) - 133) // 2

    def get_field_file(self, user):
        arquivo = models.FileFieldPlus(verbose_name='arquivo', blank=False)
        return models.FieldFilePlus(self, arquivo, self.get_path(user))

    def save(self, nome, vinculo, *args, **kwargs):
        ext_file = nome[nome.rfind('.'):]
        self.vinculo = vinculo
        self.criptografado = True
        self.data_geracao = datetime.now()
        self.nome = hashlib.md5(f'{vinculo.id}{nome}{self.data_geracao}'.encode()).hexdigest()
        self.nome = f'{self.nome}{ext_file}'
        super().save(*args, **kwargs)

    def store(self, user, content):
        relative_path = self.get_path(user)
        get_overwrite_storage().save(relative_path, io.BytesIO(content))

    def load(self, user):
        relative_path = self.get_path(user)
        content = download_media_content(relative_path)
        return content or ''

    @staticmethod
    def get_content_type(content):
        return magic.from_buffer(content[:1024], mime=True)

    def delete(self, *args, **kwargs):
        if 'contratos' in settings.INSTALLED_APPS_SUAP:
            from contratos.models import AnexoContrato, Contrato, Aditivo, PublicacaoAditivo, PublicacaoContrato, Ocorrencia

            AnexoContrato.objects.filter(arquivo__id=self.id).update(arquivo=None)
            Contrato.objects.filter(arquivo__id=self.id).update(arquivo=None)
            Aditivo.objects.filter(arquivo__id=self.id).update(arquivo=None)
            PublicacaoAditivo.objects.filter(arquivo__id=self.id).update(arquivo=None)
            PublicacaoContrato.objects.filter(arquivo__id=self.id).update(arquivo=None)
            Ocorrencia.objects.filter(arquivo__id=self.id).update(arquivo=None)

        if 'convenios' in settings.INSTALLED_APPS_SUAP:
            from convenios.models import AnexoConvenio

            AnexoConvenio.objects.filter(arquivo__id=self.id).update(arquivo=None)

        if 'projetos' in settings.INSTALLED_APPS_SUAP:
            from projetos.models import ProjetoAnexo, Edital, EditalAnexoAuxiliar

            ProjetoAnexo.objects.filter(arquivo__id=self.id).update(arquivo=None)
            Edital.objects.filter(arquivo__id=self.id).update(arquivo=None)
            EditalAnexoAuxiliar.objects.filter(arquivo__id=self.id).update(arquivo=None)

        super().delete(*args, **kwargs)

    def get_path(self, user):
        from djtools.templatetags.filters import in_group
        pode_ver = False
        path = ''
        if 'contratos' in settings.INSTALLED_APPS_SUAP:
            # pode_ver é True porque todos os documentos de contrato são públicos

            if hasattr(self, 'anexocontrato'):
                pode_ver = True
                anexo = self.anexocontrato
                extensao = os.path.splitext(anexo.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'contratos/contrato/{anexo.contrato.id:d}/anexos/{anexo.id:d}/{anexo.id:d}{extensao}')

            elif hasattr(self, 'contrato'):
                pode_ver = True
                contrato = self.contrato
                extensao = os.path.splitext(contrato.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'contratos/contrato/{contrato.id:d}/{contrato.id:d}{extensao}')

            elif hasattr(self, 'aditivo'):
                pode_ver = True
                aditivo = self.aditivo
                extensao = os.path.splitext(aditivo.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'contratos/contrato/{aditivo.contrato.id:d}/aditivos/{aditivo.id:d}/{aditivo.id:d}{extensao}')

            elif hasattr(self, 'publicacaoaditivo'):
                pode_ver = True
                pub_aditivo = self.publicacaoaditivo
                extensao = os.path.splitext(pub_aditivo.arquivo.nome)[1]
                path = os.path.join(
                    Arquivo.FS_ROOT_PATH,
                    f'contratos/contrato/{pub_aditivo.aditivo.contrato.id:d}/aditivos/{pub_aditivo.aditivo.id:d}/publicacao/{pub_aditivo.id:d}{extensao}',
                )

            elif hasattr(self, 'publicacaocontrato'):
                pode_ver = True
                pub_contrato = self.publicacaocontrato
                extensao = os.path.splitext(pub_contrato.arquivo.nome)[1]
                return os.path.join(Arquivo.FS_ROOT_PATH, f'contratos/contrato/{pub_contrato.contrato.id:d}/publicacao/{pub_contrato.id:d}{extensao}')

            elif hasattr(self, 'ocorrencia'):
                pode_ver = True
                ocorrencia = self.ocorrencia
                extensao = os.path.splitext(ocorrencia.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'contratos/contrato/{ocorrencia.contrato.id:d}/ocorrencia/{ocorrencia.id:d}{extensao}')

            elif hasattr(self, 'medicao'):
                pode_ver = True
                medicao = self.medicao
                extensao = os.path.splitext(medicao.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'contratos/contrato/{medicao.parcela.cronograma.contrato.id:d}/medicao/{medicao.id:d}{extensao}')

        if 'convenios' in settings.INSTALLED_APPS_SUAP:
            if hasattr(self, 'anexoconvenio'):
                pode_ver = in_group(user, ['Operador de Convênios Sistêmico', 'Operador de Convênios', 'Visualizador de Convênios'])
                anexo_convenio = self.anexoconvenio
                extensao = os.path.splitext(anexo_convenio.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'convenios/convenio/{anexo_convenio.convenio.id:d}/anexo/{anexo_convenio.id:d}{extensao}')

        if 'projetos' in settings.INSTALLED_APPS_SUAP and user.is_authenticated:
            if hasattr(self, 'projetoanexo'):
                anexo_projeto = self.projetoanexo
                extensao = os.path.splitext(anexo_projeto.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'projetos/projeto/{anexo_projeto.projeto.id:d}/anexo/{anexo_projeto.id:d}{extensao}')

                projeto = anexo_projeto.projeto
                is_pre_avaliador_sistemico_extensao = user.groups.filter(name='Pré-Avaliador Sistêmico de Projetos de Extensão').exists()
                eh_coordenador = projeto.is_responsavel(user)
                is_gerente_sistemico = projeto.is_gerente_sistemico(user)
                is_avaliador = projeto.is_avaliador(user)
                is_pre_avaliador = user.groups.filter(name='Coordenador de Extensão').exists()
                mesmo_campus = projeto.uo == get_uo(user)
                eh_visualizador = user.groups.filter(name='Visualizador de Projetos').exists()
                eh_participante = projeto.eh_participante(user)

                pode_ver = (is_pre_avaliador_sistemico_extensao
                            or eh_coordenador
                            or is_gerente_sistemico
                            or is_avaliador
                            or (is_pre_avaliador and mesmo_campus)
                            or eh_participante
                            or eh_visualizador)

            elif hasattr(self, 'edital'):
                pode_ver = user.has_perm('projetos.pode_visualizar_projeto')
                edital = self.edital
                extensao = os.path.splitext(edital.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'projetos/edital/{edital.id:d}{extensao}')

            elif hasattr(self, 'editalanexoauxiliar'):
                pode_ver = user.has_perm('projetos.pode_visualizar_projeto')
                anexo = self.editalanexoauxiliar
                extensao = os.path.splitext(anexo.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'projetos/edital/anexos/{anexo.edital.id:d}/{anexo.id:d}{extensao}')

        if 'pesquisa' in settings.INSTALLED_APPS_SUAP and user.is_authenticated:
            if hasattr(self, 'pesquisa_anexo_arquivo'):
                from pesquisa.models import Participacao

                anexo_projeto = self.pesquisa_anexo_arquivo
                extensao = os.path.splitext(anexo_projeto.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'pesquisa/projeto/{anexo_projeto.projeto.id:d}/anexo/{anexo_projeto.id:d}{extensao}')

                projeto = anexo_projeto.projeto
                is_coordenador_pesquisa = user.groups.filter(name__in=['Coordenador de Pesquisa', 'Pré-Avaliador Sistêmico de Projetos de Pesquisa', 'Diretor de Pesquisa'])
                vinculo = user.get_vinculo()
                is_coordenador = Participacao.objects.filter(projeto=projeto, vinculo_pessoa=vinculo, responsavel=True).exists()
                is_gerente_sistemico = user.groups.filter(name='Diretor de Pesquisa')
                is_avaliador = user.groups.filter(name='Avaliador Sistêmico de Projetos de Pesquisa')
                is_pre_avaliador = user.groups.filter(name__in=['Coordenador de Pesquisa', 'Pré-Avaliador Sistêmico de Projetos de Pesquisa'])
                mesmo_campus = projeto.uo == get_uo(user)
                eh_participante = projeto.eh_participante(user)
                pode_ver = (is_coordenador_pesquisa
                            or is_coordenador
                            or is_gerente_sistemico
                            or is_avaliador
                            or (is_pre_avaliador and mesmo_campus)
                            or eh_participante
                            or projeto.vinculo_supervisor == vinculo)

            elif hasattr(self, 'pesquisa_edital_arquivo'):
                pode_ver = user.has_perm('pesquisa.pode_visualizar_projeto')
                edital = self.pesquisa_edital_arquivo
                extensao = os.path.splitext(edital.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, 'pesquisa/edital/{ed}/{ed}{ext}'.format(ed=edital.id, ext=extensao))

            elif hasattr(self, 'pesquisa_edital_anexoauxiliar'):
                pode_ver = user.has_perm('pesquisa.pode_visualizar_projeto')
                anexo = self.pesquisa_edital_anexoauxiliar
                extensao = os.path.splitext(anexo.arquivo.nome)[1]
                path = os.path.join(Arquivo.FS_ROOT_PATH, f'pesquisa/edital/{anexo.edital.id:d}/anexo/{anexo.id:d}{extensao}')
        #
        if not pode_ver and not user.groups.filter(name='Auditor').exists():
            raise PermissionDenied()

        return path


class Notificacao(models.ModelPlus):
    modulo = models.CharField(null=False, max_length=25)
    descricao = models.CharField(null=False, max_length=100)
    titulo = models.CharField(null=False, max_length=100)
    mensagem = models.TextField(null=False, max_length=1024)

    def __str__(self):
        return self.descricao


class Notificador:
    def notificar(self, notificacao_id, email_remetente, email_destinatario, titulo_dict, mensagem_dict):
        if settings.DEBUG:
            return 0
        from django.template import Template, Context

        notificacao = Notificacao.objects.get(pk=notificacao_id)

        titulo = Template(notificacao.titulo).render(Context(titulo_dict))
        mensagem = Template(notificacao.mensagem).render(Context(mensagem_dict))

        msg = EmailMultiAlternatives(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [email_destinatario])
        msg.attach_alternative(mensagem, "text/html")

        # servidor tem e-mail?
        if email_destinatario:
            return msg.send()
        else:
            return 0


class Log(models.ModelPlus):
    app = models.CharField('Aplicação', max_length=50, null=False)
    horario = models.DateTimeField(auto_now_add=True, verbose_name='Horário')
    titulo = models.CharFieldPlus(verbose_name='Título')
    texto = models.TextField(null=True)


class EstadoCivil(ModelPlus):
    codigo_siape = models.CharField(max_length=1, blank=True)
    nome_siape = models.CharField(max_length=25)
    nome = models.CharField(max_length=25)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Estado Civil'
        verbose_name_plural = 'Estados Civis'

    def __str__(self):
        return self.nome


class Raca(models.ModelPlus):
    SEARCH_FIELDS = ['descricao']
    descricao = models.CharFieldPlus('Descrição', unique=True)
    codigo_siape = models.IntegerField('Código SIAPE', default=0)
    inativo_siape = models.BooleanField('Inativo no SIAPE', default=False)
    codigo_censup = models.CharField('Código Censup', default='', blank=True, max_length=10)

    class Meta:
        verbose_name = 'Raça'
        verbose_name_plural = 'Raças'

    def __str__(self):
        return self.descricao


class TrocarSenha(models.ModelPlus):
    """
    Guarda o token para mudança de senha e é utilizado no suapexterno.
    """

    username = models.CharFieldPlus()
    email = models.EmailField()
    token = models.CharField(max_length=128)
    validade = models.DateTimeField()

    def save(self, *args, **kwargs):
        """
        Define os atributos ``email``, ``token`` e ``validade``.
        """

        pessoa_fisica = PessoaFisica.objects.get(username=self.username)
        # if not pessoa_fisica.email_secundario:
        #     raise ValueError('Pessoa sem email alternativo')

        # Definindo email
        self.email = pessoa_fisica.email_secundario

        # Definindo validade
        agora = datetime.now()
        self.validade = agora + timedelta(1)  # válido por 24 horas

        # Definindo token
        frase = f'{str(agora)}{self.username}{settings.SECRET_KEY}'.encode()
        self.token = hashlib.sha512(frase).hexdigest()

        super().save(*args, **kwargs)

    @classmethod
    def token_valido(cls, username, token):
        agora = datetime.now()
        return cls.objects.filter(username=username, token=token, validade__gte=agora).exists()

    def enviar_email(self, base_url=''):
        url = f'{settings.SITE_URL}/comum/trocar_senha/{self.username}/{self.token}/'
        conteudo = '''<h1>Solicitação de Mudança de Senha</h1>
        <p>Prezado usuário,</p>
        <p>Para realizar a mudança de senha referente às suas credenciais da rede, por favor, acesse o endereço abaixo:</p>
        <p><a href="{url}">{url}</a></p>'''.format(
            url=url
        )
        return send_mail('[SUAP] Solicitação de Mudança de Senha', conteudo, settings.DEFAULT_FROM_EMAIL, [self.email])


class GerenciamentoGrupo(models.ModelPlus):
    grupo_gerenciador = models.ForeignKeyPlus(Group, related_name='grupo_gerenciador_set', on_delete=models.CASCADE)
    grupos_gerenciados = models.ManyToManyField(Group, related_name='grupos_gerenciados_set')
    eh_local = models.BooleanField('É Local?', default=False)

    NOME_GRUPO_GERENCIADOR_FORMAT = '{} Administrador'

    class Meta:
        verbose_name = "Gerenciamento de Grupo"
        verbose_name_plural = "Gerenciamento de Grupos"

    def __str__(self):
        return f"{self.grupo_gerenciador.name}"

    @classmethod
    def user_can_manage(cls, user):
        return user.is_superuser or cls.objects.filter(grupo_gerenciador__in=user.groups.all()).exists()

    def get_grupos_gerenciados(self):
        grupos = []
        for grupo in self.grupos_gerenciados.all():
            grupo.eh_local = self.eh_local
            grupos.append(grupo)
        return grupos

    @staticmethod
    def get_grupos_gerenciados_por(group):
        result = []
        qs = GerenciamentoGrupo.objects.filter(grupo_gerenciador=group)
        if qs.exists():
            for gerenciamento_grupo in qs:
                result.extend(gerenciamento_grupo.get_grupos_gerenciados())
        return result

    @staticmethod
    def get_grupos_que_gerenciam(group):
        result = []
        qs = GerenciamentoGrupo.objects.filter(grupos_gerenciados=group)
        if qs.exists():
            for gerenciamento_grupo in qs:
                result.append(gerenciamento_grupo.grupo_gerenciador)
        return result


class UsuarioGrupo(models.ModelPlus):
    user = models.ForeignKeyPlus(User, on_delete=models.CASCADE)
    group = models.ForeignKeyPlus(Group, on_delete=models.CASCADE)
    setores = models.ManyToManyFieldPlus('rh.Setor', through='comum.UsuarioGrupoSetor')

    class Meta:
        verbose_name = 'Vínculo de Usuário em Grupo'
        verbose_name_plural = 'Vínculos de Usuário em Grupo'
        db_table = 'auth_user_groups'
        managed = False

    def __str__(self):
        return f'Vínculo do usuário {self.user} no grupo {self.group}'


models.signals.post_delete.connect(registrar_remocao_grupo, sender=UsuarioGrupo, dispatch_uid='comum.models')
models.signals.post_save.connect(registrar_adicao_grupo, sender=UsuarioGrupo, dispatch_uid='comum.models')


class UsuarioGrupoSetor(models.ModelPlus):
    usuario_grupo = models.ForeignKeyPlus(UsuarioGrupo, on_delete=models.CASCADE, db_column='usuariogrupo_id')
    setor = models.ForeignKeyPlus('rh.Setor', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Vínculo de Usuário em Setor'
        verbose_name_plural = 'Vínculos de Usuário em Setor'
        db_table = 'comum_usuariogrupo_setores'

    def __str__(self):
        return f'Vínculo do usuário no setor {self.setor}'


class Comentario(models.ModelPlus):
    """
    Modelo que representa os comentários realizados para uma demanda.
    """

    cadastrado_por = models.CurrentUserField()
    cadastrado_em = models.DateTimeFieldPlus(auto_now=True)
    resposta = models.ForeignKeyPlus('Comentario', null=True, blank=True, on_delete=models.CASCADE)
    texto = models.TextField()
    # Fk Genérica para uso por qualquer modelo
    content_type = models.ForeignKeyPlus(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if hasattr(self.content_object, 'comentario_post_save'):
            self.content_object.comentario_post_save(self)

    def __str__(self):
        return f'{self.cadastrado_por} - {self.texto}'


class RegistroEmissaoDocumento(models.ModelPlus):
    tipo = models.CharFieldPlus(verbose_name='Tipo de Documento')
    data_emissao = models.DateFieldPlus(verbose_name='Data de Emissão')
    codigo_verificador = models.TextField(verbose_name='Código Verificador')
    documento = models.FileFieldPlus(upload_to='documentos', verbose_name='Documento', filetypes=('pdf',))
    data_validade = models.DateFieldPlus(null=True, blank=True, verbose_name='Validade')

    modelo_pk = models.IntegerField('Id da Referência', null=True)
    tipo_objeto = models.ForeignKeyPlus(ContentType, on_delete=models.CASCADE, null=True, verbose_name='Referência')
    objeto = GenericForeignKey('tipo_objeto', 'modelo_pk')
    cancelado = models.BooleanField(verbose_name='Cancelado', default=False)

    class Meta:
        verbose_name = 'Registro de Emissão de Documento'
        verbose_name_plural = 'Registros de Emissão de Documento'

    def as_pdf_response(self):
        return HttpResponse(self.documento.read(), content_type='application/pdf')

    def __str__(self):
        return self.tipo

    def get_url_download_documento(self):
        return f'/comum/baixar_documento/{self.pk}/{self.codigo_verificador}/'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        default_storage.delete(self.documento.name)

    @staticmethod
    def qrcode(url):
        img = qrcode.make(url)
        buffer_img = io.BytesIO()
        img.save(buffer_img, 'png')
        return base64.encodebytes(buffer_img.getvalue()).decode()

    @staticmethod
    def url_autenticacao(tipo, data_emissao, codigo_verificador, completa=False):
        url = settings.SITE_URL + '/comum/autenticar_documento/'
        if completa:
            params = urllib.parse.urlencode(
                dict(
                    tipo=tipo, data_emissao=data_emissao.strftime('%d/%m/%Y'),
                    codigo_verificador=codigo_verificador[0:6]
                )
            )
            return f'{url}?{params}'
        return url


class TipoCarteiraFuncional(models.ModelPlus):
    MODELO_2015 = '2015'
    MODELO_2016 = '2016'
    MODELOS_CHOICES = ((MODELO_2015, 'Modelo 2015'), (MODELO_2016, 'Modelo 2016'))

    nome = models.CharFieldPlus('Nome')
    template = models.CharFieldPlus('Template', choices=MODELOS_CHOICES)
    data_cadastro = models.DateTimeFieldPlus(auto_now_add=True)
    modelo = models.FileFieldPlus(upload_to='comum/carteira_funcional/', null=True, blank=True, verbose_name='Modelo')
    ativo = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Tipo de Carteira Funcional'
        verbose_name_plural = 'Tipos de Carteira Funcional'

    def save(self, *args, **kwargs):
        if self.ativo:
            TipoCarteiraFuncional.objects.all().update(ativo=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class IndexLayout(ModelPlus):
    usuario = models.CurrentUserField()
    quadro_nome = models.CharFieldPlus('Nome do Quadro')
    quadro_coluna = models.PositiveIntegerField('Coluna no Leiaute', default=1)
    quadro_ordem = models.PositiveIntegerField('Ordem de Apresentação')
    escondido = models.BooleanField(default=False)

    class History:
        disabled = True

    @classmethod
    def get_layouts_usuario(cls, request):
        if request.session.get('index_layout'):
            return request.session.get('index_layout')
        else:
            layouts = cls.objects.filter(usuario=request.user).order_by('quadro_coluna', 'quadro_ordem')
            result = collections.OrderedDict()
            for layout in layouts.values():
                result[layout['quadro_nome']] = {'coluna': layout['quadro_coluna'], 'ordem': layout['quadro_ordem'], 'escondido': layout['escondido']}
            request.session['index_layout'] = result
            return result

    @staticmethod
    def recarregar_layouts(request):
        try:
            del request.session['index_layout']
        except KeyError:
            pass


class ManutencaoProgramada(ModelPlus):
    FUNCIONALIDADE = 'Funcionalidade'
    MANUTENCAO = 'Manutenção'
    BUG = 'Bug'
    TIPO_CHOICES = ((FUNCIONALIDADE, 'Adição de Funcionalidades'), (MANUTENCAO, 'Manutenção Preventiva'), (BUG, 'Correção de Bugs'))
    usuario = models.CurrentUserField(verbose_name='Última Alteração por')
    data_cadastro = models.DateTimeFieldPlus(auto_now_add=True)
    tipo = models.CharFieldPlus(choices=TIPO_CHOICES)
    data_hora_atualizacao = models.DateTimeFieldPlus('Data da atualização')
    previsao_minutos_inatividade = models.PositiveIntegerFieldPlus('Previsão de minutos de inatividade')
    efetivos_minutos_inatividade = models.PositiveIntegerFieldPlus('Efetivos minutos de inatividade', null=True, blank=True)
    data_hora_inicio_notificacao = models.DateTimeFieldPlus('Data de início notificação')
    equipe_manutencao = models.ManyToManyFieldPlus('comum.Vinculo', verbose_name='Equipe de manutenção')
    motivo = models.TextField()

    class Meta:
        verbose_name = 'Manutenção Programada'
        verbose_name_plural = 'Manutenções Programadas'

    def __str__(self):
        return f'{self.get_tipo_display()} às {self.data_hora_atualizacao.date()}'

    @classmethod
    def proximas_atualizacoes(cls):
        agora = datetime.now()
        return cls.objects.filter(data_hora_atualizacao__gte=agora).order_by('data_hora_atualizacao')

    @classmethod
    def proxima_notificacao(cls):
        agora = datetime.now()
        return cls.proximas_atualizacoes().filter(data_hora_inicio_notificacao__lte=agora).order_by('data_hora_atualizacao').first()

    def clean(self):
        if self.data_hora_atualizacao < self.data_hora_inicio_notificacao:
            raise ValidationError('O horário de atualização deve ser maior que o horário de notificação.')


class Preferencia(ModelPlus):
    PADRAO = 'Padrão'
    DUNAS = 'Dunas'
    AURORA = 'Aurora'
    LUNA = 'Luna'
    GOVBR = 'Gov.br'
    ALTO_CONSTRASTE = 'Alto Contraste'
    IFS = 'IFs'
    TEMA_CHOICES = ((PADRAO, 'Padrão'), (DUNAS, 'Dunas'), (AURORA, 'Aurora'), (LUNA, 'Luna'), (GOVBR, 'Gov.br'), (ALTO_CONSTRASTE, 'Alto Contraste'), (IFS, 'IFs'))

    usuario = models.OneToOneFieldPlus(User, on_delete=models.CASCADE, verbose_name='Usuário')
    tema = models.CharFieldPlus('Opção de Tema', choices=TEMA_CHOICES, default=PADRAO)
    via_suap = models.BooleanField('Notificação Via SUAP', default=True)
    via_email = models.BooleanField('Notificação Via E-mail', default=True)
    data_cadastro = models.DateTimeFieldPlus(auto_now_add=True)

    class Meta:
        verbose_name = 'Preferência do Usuário'
        verbose_name_plural = 'Preferências do Usuário'

    def __str__(self):
        return f'Preferências de: {self.usuario}'


class FuncaoCodigo(ModelPlus):
    nome = models.CharField(verbose_name='Cargo/Função', max_length=7, null=False)

    def __str__(self):
        return '%s' % self.nome

    class Meta:
        verbose_name = 'Código de Função'
        verbose_name_plural = 'Códigos de Funções'


class CategoriaNotificacao(ModelPlus):
    assunto = models.CharFieldPlus(verbose_name='Assunto')
    ativa = models.BooleanField(verbose_name='Ativa?', default=True)
    forcar_habilitacao = models.BooleanField(verbose_name='Forçar Habilitação', help_text='Se marcar o usuário não poderá desabilitar as preferências de notificação associadas a esta categoria.', default=False)

    class Meta:
        verbose_name = 'Categoria de Notificação'
        verbose_name_plural = 'Categorias de Notificações'

    def __str__(self):
        return self.assunto


class NotificacaoSistema(ModelPlus):
    categoria = models.ForeignKeyPlus('comum.CategoriaNotificacao', null=False, blank=False)
    mensagem = models.TextField(verbose_name='Mensagem')
    objeto_relacionado = models.CharFieldPlus('Objeto Relacionado', null=True, db_index=True)
    data_envio = models.DateTimeField(auto_now_add=True, verbose_name='Data de Envio')

    class Meta:
        verbose_name = 'Mensagem da Notificação'
        verbose_name_plural = 'Mensagens das Notificações'

    class History:
        disabled = True

    def __str__(self):
        return str(self.categoria)


class RegistroNotificacao(ModelPlus):
    notificacao = models.ForeignKeyPlus('comum.NotificacaoSistema', null=False, blank=False, verbose_name='Notificação')
    vinculo = models.ForeignKeyPlus('comum.Vinculo', null=False, blank=False, verbose_name='Vínculo')
    lida = models.BooleanField(verbose_name='Lida?', default=False)
    data = models.DateTimeField(auto_now_add=True)
    data_permite_marcar_lida = models.DateTimeFieldPlus(auto_now_add=True)
    data_permite_excluir = models.DateTimeFieldPlus(auto_now_add=True)

    class History:
        disabled = True

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        ordering = ('-data',)

    def __str__(self):
        return self.get_assunto

    def save(self, *args, **kwargs):
        self.limpar_cache(self.vinculo.user)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f'/comum/notificacao/{self.pk}/'

    def pode_ler(self):
        return self.data_permite_marcar_lida < datetime.now()

    def pode_excluir(self):
        return self.data_permite_excluir < datetime.now()

    @classmethod
    def contar_nao_lidas(cls, user):
        key = f'__NOTIFICACOES_NAO_LIDAS-{user.username}'
        count = cache.get(key, -1)
        if count == -1:
            count = cls.objects.filter(vinculo__user=user, lida=False).count()
            cache.set(key, count)
        return count

    @classmethod
    def limpar_cache(cls, user):
        try:
            key = f'__NOTIFICACOES_NAO_LIDAS-{user.username}'
            cache.delete(key)
        except Exception:
            pass

    @property
    def get_assunto(self):
        return self.notificacao.categoria.assunto

    def outras_notificacoes_nao_lidas_mesmo_objeto(self):
        registro_notificacoes_anteriores = RegistroNotificacao.objects.none()
        if self.notificacao.objeto_relacionado:
            registro_notificacoes_anteriores = RegistroNotificacao.objects.filter(vinculo=self.vinculo, notificacao__objeto_relacionado=self.notificacao.objeto_relacionado, lida=False).exclude(pk=self.pk)
        return registro_notificacoes_anteriores

    def get_mensagem(self):
        return self.notificacao.mensagem

    def get_preferencia(self):
        return PreferenciaNotificacao.objects.filter(vinculo=self.vinculo, categoria=self.notificacao.categoria).first()

    def get_preferencia_via_suap(self):
        return self.get_preferencia().via_suap

    def get_preferencia_via_email(self):
        return self.get_preferencia().via_email


class PreferenciaNotificacao(ModelPlus):
    categoria = models.ForeignKeyPlus('comum.CategoriaNotificacao', null=False, blank=False)
    vinculo = models.ForeignKeyPlus('comum.Vinculo', null=False, blank=False, verbose_name='Vínculo')
    via_suap = models.BooleanField(verbose_name='Via SUAP', default=True)
    via_email = models.BooleanField(verbose_name='Via E-mail', default=True)
    data = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Preferência de Notificação'
        verbose_name_plural = 'Preferências de Notificações'
        ordering = ('-data',)

    def pode_desabilitar(self):
        return not self.categoria.forcar_habilitacao


class GroupDetail(ModelPlus):
    group = models.ForeignKeyPlus('auth.Group', null=False, blank=False)
    app = models.CharFieldPlus('App', null=True, blank=False,)
    app_manager = models.CharFieldPlus('App Manager', null=True, blank=False,)
    descricao = models.TextField('Descrição do Grupo', null=False, blank=False,)

    class Meta:
        verbose_name = 'Detalhes do Grupo'
        verbose_name_plural = 'Detalhes dos Grupos'
        unique_together = ('app', 'group')

    def __str__(self):
        return f'{self.group} - {self.app}'

    def get_absolute_url(self):
        return f"/comum/grupos_usuarios/?modulo={self.app_manager}&grupo={self.group.id:d}"


class EmailBlockList(ModelPlus):
    '''
    Registra os emails que não poderão mais ser escolhidos no SUAP
    '''
    email = models.EmailField('Email', null=False, blank=False, unique=True, db_index=True,
                              help_text='Este email não poderá mais ser escolhido para ser usado no SUAP.')

    data_criacao = models.DateTimeField(verbose_name='Data de criação', auto_now_add=True)

    class Meta:
        verbose_name = 'Email na BlockList'
        verbose_name_plural = 'Emails na Blocklist'

class BolsistaManager(models.Manager):
    def get_queryset(self):
        query_set = super().get_queryset()
        return query_set.filter(bolsista=True, eh_prestador=True)

class Bolsista(PrestadorServico):    
    objects = BolsistaManager()

    class Meta:
        verbose_name = 'Bolsista'
        verbose_name_plural = 'Bolsistas'
        proxy = True

    def get_absolute_url(self):
        return "/ppe/bolsista/{:d}/".format(self.id)
    def ativar(self, *args, **kwargs):
        self.ativo = True
        self.save()

    def pode_ser_ativado(self, *args, **kwargs):
        if not self.ativo:
            return True
        return False

    def inativar(self, *args, **kwargs):
        self.ativo = False
        self.save()

    def cadastrar_telefone(self, telefone):
        PessoaTelefone = apps.get_model("comum", "PessoaTelefone")
        PessoaTelefone.objects.create(pessoa_id=self.user.get_profile().pessoafisica.id,
                                      numero=telefone)

    def get_ext_combo_template(self):
        out = ['<h4>{}</h4>'.format(self.nome)]
        out.append('<h5>Bolsista</h5>')
        if self.setor:
            out.append('<p>{}</p>'.format(self.setor.get_caminho_as_html()))
        template = '''<div class="person">
             <div class="photo-circle">
                 <img src="{}"/>
             </div>
             <div>
                 {}
             </div>
         </div>
         '''.format(
            self.get_foto_75x100_url(), ''.join(out)
        )
        return template

    def save(self, *args, **kwargs):
        self.bolsista = True
        super().save(*args, **kwargs)

    def enviar_email_pre_cadastro(self):
        conteudo = f'''<h1>Ativação de Cadastro de Bolsista - SUAP </h1>
        <p>Prezado(a) {self.nome},</p>
        <p>Foi realizado um cadastro de Bolsista no SUAP/FESFSUS</p>    
        <p><a href="{settings.SITE_URL}">{settings.SITE_URL}</a></p>.

        '''
        return send_mail('[SUAP] Cadastro de Bolsista', conteudo, settings.DEFAULT_FROM_EMAIL, [self.email])