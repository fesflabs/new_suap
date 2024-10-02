import base64
import datetime
import hashlib
import mimetypes
import re
import uuid
from collections import OrderedDict

import tqdm
from ckeditor.fields import RichTextField
from dateutil.relativedelta import relativedelta
from django.apps.registry import apps
from django.conf import settings
from django.contrib.auth.hashers import get_hasher, make_password
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import ProgrammingError, transaction
from django.db.models.aggregates import Max, Sum
from django.db.models.expressions import F
from django.db.transaction import atomic
from django.utils import timezone
from django.utils.safestring import mark_safe
from model_utils.managers import InheritanceManager
from pycpfcnpj import cpfcnpj

from comum import utils

from comum.utils import (
    data_normal,
    datas_entre,
    get_setor,
    get_sigla_reitoria,
    get_uo,
    get_uo_siape,
    periodos_sucessivos,
    retirar_preposicoes_nome,
    convert_bytes_to_strb64,
)
from djtools.choices import Meses, NATUREZA_JURIDICA_CHOICES
from djtools.db import models
from djtools.db.models import ModelPlus, Q, QuerySet
from djtools.storages import get_overwrite_storage
from djtools.templatetags.filters import in_group
from djtools.thumbs import ImageWithThumbsField
from djtools.utils import anonimizar_cpf, cpf_valido, get_age, mask_cpf, mask_numbers, normalizar_nome_proprio, to_ascii
from rh.enums import Nacionalidade
from rh.managers import AreaConhecimentoManager, FuncaoManager, PessoaManager, ServidorQueryset, SetorManager, SetoresSiapeManager, SetoresSuapAtivosManager, SetoresSuapManager, UnidadeOrganizacionalManager

if "edu" in settings.INSTALLED_APPS:
    from edu.managers import FiltroUnidadeOrganizacionalManager

PRIVATE_ROOT_DIR = "private-media/rh"


class TipoUnidadeOrganizacional(ModelPlus):
    descricao = models.CharFieldPlus("Descrição")

    class Meta:
        verbose_name = "Tipo de Unidade Organizacional"
        verbose_name_plural = "Tipos de Unidade Organizacional"

    def __str__(self):
        return self.descricao


class UnidadeOrganizacional(ModelPlus):
    SEARCH_FIELDS = ["nome", "sigla"]

    TIPO_CAMPUS_NAO_PRODUTIVO = 1
    TIPO_CAMPUS_PRODUTIVO = 2
    TIPO_CAMPUS_EAD = 3
    TIPO_REITORIA = 4
    TIPO_CONSELHO = 5

    nome = models.CharField(max_length=255, verbose_name="Nome")
    sigla = models.CharField(max_length=25, verbose_name="Sigla")
    setor = models.OneToOneField("rh.Setor", on_delete=models.CASCADE)
    municipio = models.ForeignKeyPlus("comum.Municipio", null=True, blank=True, verbose_name="Município")
    codigo_protocolo = models.CharField(
        max_length=5, blank=True, verbose_name="Prefixo para geração do número de protocolo", help_text="Este valor deve ter 5 dígitos."
    )
    codigo_ug = models.CharField(max_length=6, blank=True, verbose_name="Código UG")
    codigo_ugr = models.CharField(max_length=6, blank=True, verbose_name="Código UGR")
    cnpj = models.BrCnpjField(null=True, blank=True)
    equivalente = models.ForeignKeyPlus(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to={"setor__codigo__isnull": True},
        help_text="Campus SUAP equivalente. Preencha caso esteja editando um campus SIAPE.",
    )
    endereco = models.CharField(max_length=255, verbose_name="Endereço", null=True, blank=True)
    numero = models.CharField(max_length=255, verbose_name="Número", null=True, blank=True)
    zona_rual = models.BooleanField(verbose_name="Zona Rural?", default=False)
    bairro = models.CharField(max_length=255, verbose_name="Bairro", null=True, blank=True)
    cep = models.CharField(max_length=255, verbose_name="Cep", null=True, blank=True)
    telefone = models.CharField(max_length=255, verbose_name="Telefone", null=True, blank=True)
    fax = models.CharField(max_length=255, verbose_name="Fax", null=True, blank=True)

    # dados acadêmicos
    codigo_inep = models.CharField("Código INEP", max_length=25, blank=True)
    codigo_censup = models.CharField("Código CENSUP", max_length=25, blank=True, null=True)
    codigo_emec = models.CharField("Código e-MEC", max_length=25, blank=True, null=True)
    portaria_criacao = models.TextField("Portaria de Criação", blank=True)
    # outras informações
    tipo = models.ForeignKeyPlus('rh.TipoUnidadeOrganizacional', null=True, blank=False, on_delete=models.CASCADE)

    # SISTEC
    codigo_interno = models.CharFieldPlus("Código Interno", default="", blank=True)
    codigo_sistec = models.CharFieldPlus("Código SISTEC", default="", blank=True)

    # ConectaGOV - Barramento PEN
    setor_recebimento_pen = models.ForeignKey(
        "rh.Setor",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="setor_barramento",
        verbose_name="Setor de Recebimento de Processos Externos))",
        help_text="Setor que irá receber processos enviados por outras instituições via ConectaGOV (barramento)",
    )
    id_repositorio_pen = models.CharFieldPlus(
        "ID Repositório Estruturas",
        default="001",
        blank=True,
        null=True,
        help_text="Identificador do repositório de estruturas - Órgãos do Poder Executivo = 001",
    )
    id_estrutura_pen = models.CharFieldPlus(
        "ID Estrutura PEN", blank=True, null=True, help_text="Identificador da " "estrutura referente a " "esta unidade no barramento"
    )

    objects = UnidadeOrganizacionalManager()
    locals = FiltroUnidadeOrganizacionalManager() if "edu" in settings.INSTALLED_APPS else UnidadeOrganizacionalManager()

    class Meta:
        db_table = "unidadeorganizacional"
        ordering = ["setor__sigla"]
        verbose_name = "Campus"
        verbose_name_plural = "Campi"

    def __str__(self):
        return self.sigla

    def save(self, *args, **kwargs):
        Setor = apps.get_model("rh", "Setor")
        """
        O método foi sobrescrito para preencher automaticamente o campo ``uo`` dos
        setores.
        """
        if self.pk:
            setor_antigo = UnidadeOrganizacional.objects.get(pk=self.pk).setor
            novo_setor = self.setor
            ignorar_processamento_setores = setor_antigo == novo_setor
        else:
            ignorar_processamento_setores = False

        super().save(*args, **kwargs)
        if not ignorar_processamento_setores:
            for setor in Setor.todos.all():
                setor.save()

    def clean(self):
        super().clean()
        if self.codigo_protocolo and len(self.codigo_protocolo) != 5:
            raise ValidationError('O "prefixo para geração do número de protocolo" deve ter 5 dígitos.')
        if self.setor.excluido:
            raise ValidationError('O "setor" deve ser um setor ativo.')

    def get_ext_combo_template(self):
        configuracao_setor_eh_suap = settings.TIPO_ARVORE_SETORES == 'SUAP'
        out = str(self)
        if configuracao_setor_eh_suap and self.setor.codigo:
            out += " (SIAPE)"
        return "<div>{}</div>".format(out)

    def get_servidores(self):
        return Servidor.objects.ativos().filter(setor__uo=self)

    @property
    def eh_reitoria(self):
        return self.sigla == get_sigla_reitoria()

    def get_diretor_geral(self, excluir_substituto=False):
        servidor_funcao_qs = ServidorFuncaoHistorico.objects.filter(
            atividade__codigo__in=[Atividade.DIRETOR_GERAL, Atividade.REITOR],
            setor_suap=self.setor,
            data_inicio_funcao__lte=datetime.datetime.today(),
        )
        servidor_funcao_qs = servidor_funcao_qs.filter(data_fim_funcao__gte=datetime.datetime.today()) | servidor_funcao_qs.filter(
            data_fim_funcao__isnull=True
        )
        if excluir_substituto:
            servidor_funcao_qs = servidor_funcao_qs.exclude(funcao__codigo=Funcao.get_sigla_substituicao_chefia())
        if not servidor_funcao_qs.exists() and self.setor.superior:
            return self.setor.superior.uo.get_diretor_geral()
        return Servidor.objects.filter(pk__in=servidor_funcao_qs.values_list("servidor", flat=True))

    def can_change(self, user):
        return user.has_perm("rh.eh_rh_sistemico") or (user.has_perm("rh.eh_rh_campus") and user.get_relacionamento().setor.uo == self)


class Pessoa(ModelPlus):
    SEARCH_FIELDS = ["search_fields_optimized"]
    RELEVANCE_ORDERING = [
        ("pessoafisica__eh_servidor", True),
        ("pessoafisica__eh_prestador", True),
        ("pessoafisica__eh_aluno", True),
        ("pessoafisica__eh_residente", True),
        ("pessoafisica__eh_trabalhadoreducando", True),
        ("pessoajuridica__isnull", False),
    ]

    nome = models.UnaccentField(max_length=200, db_index=True)
    nome_usual = models.UnaccentField("Nome Usual", max_length=30, blank=True, help_text="O nome apresentado no crachá ou razão social", db_index=True)
    nome_social = models.UnaccentField("Nome Social", max_length=200, blank=True, db_index=True)
    nome_registro = models.UnaccentField("Nome de Registro", max_length=200, blank=True, db_index=True)
    email = models.EmailField(blank=True, verbose_name="E-mail Principal")
    email_secundario = models.EmailField(
        blank=True, verbose_name="E-mail Secundário", help_text="E-mail utilizado para recuperação de senha."
    )
    website = models.URLField(blank=True)
    excluido = models.BooleanField(verbose_name="Excluído", default=False, help_text="Indica se a última ocorrência é de exclusão")
    setores_adicionais = models.ManyToManyField(
        "rh.Setor",
        verbose_name="Setores Adicionais",
        blank=True,
        help_text="O funcionário terá acesso aos processos dos setores adicionais no sistema de protocolo.",
    )
    natureza_juridica = models.CharField("Natureza Jurídica", max_length=5, blank=True, choices=NATUREZA_JURIDICA_CHOICES)
    sistema_origem = models.CharField(
        max_length=50,
        blank=True,
        choices=[["", "Cadastro manual"], ["SIAPE", "SIAPE"], ["WS-SIAPE", "WS-SIAPE"], ["SIAFI", "SIAFI"]],
        help_text="Indica de qual sistema a pessoa veio: SIAPE, SIAFI etc",
    )

    uuid = models.UUIDField(unique=True, default=uuid.uuid4)

    """
     Campo de busca criado para otimizar a consulta em Pessoa, PessoaFisica e PessoaJuridica.
     Caso os campos definidos em SEARCH_FIELDS envolvam mais de uma entidade, o que é o caso, a engine do banco de
     dados acaba tendo que fazer uma busca sequencial (Seq Scan). A ideia deste novo atributo é concentrar todas essas
     informações, de forma que o banco de dados possa fazer uma busca otimizada (Bitmap Scan), já que apenas uma coluna
     de uma tabela será alvo da consulta. Obs: Os dados redundantes, presentes nesse atributo, serão atualizados no save
     de Pessoa. Cada entidade filha deverá definir esse conteúdo através da sobreescrita do método
     _get_search_fields_optimized_value.

     Durante' os testes, no universo de 315.000 registros, a consulta caiu, em média, de 4 segundos para 0,2 segundos.
    """
    search_fields_optimized = models.UnaccentField(max_length=400, db_index=True)

    objects = PessoaManager()

    class Meta:
        db_table = "pessoa"
        ordering = ("nome",)
        permissions = (
            ("pode_editar_email_secundario_servidor", "Pode editar e-mail secundário"),
            ("pode_editar_email_institucional", "Pode editar e-mail institucional"),
            ("pode_editar_email_secundario_aluno", "Pode editar e-mail secundário do aluno"),
            ("pode_editar_email_secundario_prestador", "Pode editar e-mail secundário do Prestador de Serviço"),
            ("pode_editar_email_academico", "Pode editar e-mail acadêmico"),
            ("pode_editar_email_google_classroom", "Pode editar e-mail google classroom"),
        )

    def __str__(self):
        if hasattr(self, "pessoafisica"):
            Aluno = None
            if "edu" in settings.INSTALLED_APPS:
                Aluno = apps.get_model("edu", "aluno")

            qs_servidor = Servidor.objects.filter(id=self.id)

            qs_aluno = None
            if Aluno:
                qs_aluno = Aluno.objects.filter(pessoa_fisica__id=self.id)

            if qs_servidor.exists():
                matricula, nome, cpf = qs_servidor.values_list("matricula", "nome", "cpf")[0]
                if not cpf:
                    cpf = ""
                return f"{nome} (CPF: {anonimizar_cpf(cpf)}, Servidor {matricula})"
            elif Aluno and qs_aluno.exists():
                matricula, nome, cpf = qs_aluno.values_list("matricula", "pessoa_fisica__nome", "pessoa_fisica__cpf")[0]
                if not cpf:
                    cpf = ""
                return f"{nome} (CPF: {anonimizar_cpf(cpf)}, Aluno {matricula})"
            else:
                cpf = self.pessoafisica.cpf
                if not cpf:
                    cpf = ""
                return f"{self.pessoafisica.nome} (CPF: {anonimizar_cpf(cpf)})"
        elif hasattr(self, "pessoajuridica"):  # Pessoa jurídica
            return f"{self.pessoajuridica.nome} ({self.pessoajuridica.cnpj})"
        else:
            return self.nome

    def get_representantes(self):
        return self.pessoajuridica.ocupacaoprestador_set.filter(ocupacao__representante=True) if hasattr(self, "pessoajuridica") else ""

    def get_absolute_url(self):
        if hasattr(self, "pessoajuridica"):
            return self.pessoajuridica.get_absolute_url()
        elif hasattr(self, "pessoafisica"):
            return self.pessoafisica.get_absolute_url()

    def save(self, *args, **kwargs):
        """
        Caso `self` tenha username, um usuário será criado para `self`.
        """
        Configuracao = apps.get_model("comum", "configuracao")
        if not Configuracao.get_valor_por_chave(
            "rh", "permite_email_institucional_email_secundario"
        ) and Configuracao.eh_email_institucional(self.email_secundario):
            raise ValidationError("Escolha um e-mail que não seja institucional.")

        # Ajustando as informações reduntantes que serão usadas para uma busca mais eficiente na entidade.
        self.search_fields_optimized = self._get_search_fields_optimized_content_to_save()
        return super().save(*args, **kwargs)

    def _get_search_fields_optimized_content_to_save(self):
        """
        Esse método retorna o conteúdo que deverá ser armazenado no atributo search_fields_optimized. As classes filhas
        de Pessoa deverão sobreescrever esse método para personalizar essa informação.
        :return: texto
        """
        return self.nome

    def get_foto_75x100_url(self):
        default_img = "/static/comum/img/default.jpg"
        if hasattr(self, "pessoafisica"):
            retorno = self.pessoafisica.get_foto_75x100_url()
        elif hasattr(self, "pessoajuridica"):
            retorno = self.pessoajuridica.get_foto_75x100_url()
        return retorno if retorno else default_img

    def get_foto_150x200_url(self):
        default_img = "/static/comum/img/default.jpg"
        if hasattr(self, "pessoafisica"):
            retorno = self.pessoafisica.get_foto_150x200_url()
        elif hasattr(self, "pessoajuridica"):
            retorno = self.pessoajuridica.get_foto_150x200_url()
        return retorno if retorno else default_img

    def get_ext_combo_template(self):
        if hasattr(self, "pessoafisica"):
            template = self.pessoafisica.get_ext_combo_template()
        elif hasattr(self, "pessoajuridica"):
            template = self.pessoajuridica.get_ext_combo_template()
        else:
            out = [f"{self.nome}"]
            template = """
                      <div>
                          {}
                      </div>
                      """.format(
                "".join(out)
            )

        return template

    # TODO: Talvez essas properties possam virar atributos
    @property
    def eh_pessoa_fisica(self):
        retorno = False
        if hasattr(self, "pessoafisica"):
            retorno = True
        return retorno

    # TODO: Talvez essas properties possam virar atributos
    @property
    def eh_pessoa_juridica(self):
        retorno = False
        if hasattr(self, "pessoajuridica"):
            retorno = True
        return retorno

    def get_cpf_ou_cnpj(self):
        if hasattr(self, "pessoafisica"):
            return self.pessoafisica.cpf
        elif hasattr(self, "pessoajuridica"):  # Pessoa jurídica
            return self.pessoajuridica.cnpj
        return "-"

    def cpf_ou_cnpj_valido(self):
        if settings.DEBUG:
            return True

        if hasattr(self, "pessoafisica"):
            return cpfcnpj.validate(self.pessoafisica.cpf)
        elif hasattr(self, "pessoajuridica"):  # Pessoa jurídica
            return cpfcnpj.validate(self.pessoajuridica.cnpj)
        else:
            return False

    @property
    def telefones(self):
        tels = " / ".join([self.telefones_pessoais or "", self.telefones_institucionais or ""])
        if tels.strip().endswith("/"):
            tels = tels.strip()[:-1]
        return tels

    @property
    def telefones_pessoais(self):
        return ", ".join(self.pessoatelefone_set.values_list("numero", flat=True))

    @property
    def telefones_institucionais(self):
        out = []
        if hasattr(self, "setor") and self.setor:
            for st in self.setor.setortelefone_set.all():
                out.append(f"{st}")
        return ", ".join(out)

    @property
    def endereco(self):
        return "{}".format(self.pessoaendereco or "")

    @property
    def endereco_cep(self):
        return self.pessoaendereco.cep if self.pessoaendereco else ""

    @property
    def endereco_municipio(self):
        return self.pessoaendereco.municipio if self.pessoaendereco else ""

    @property
    def endereco_logradouro(self):
        return self.pessoaendereco.logradouro if self.pessoaendereco else ""

    @property
    def endereco_numero(self):
        return self.pessoaendereco.numero if self.pessoaendereco else ""

    @property
    def endereco_complemento(self):
        return self.pessoaendereco.complemento if self.pessoaendereco else ""

    @property
    def endereco_bairro(self):
        return self.pessoaendereco.bairro if self.pessoaendereco else ""

    @property
    def pessoaendereco(self):
        return self.pessoaendereco_set.all().first()


class AreaVinculacao(ModelPlus):
    descricao = models.CharFieldPlus("Descrição")
    ordem = models.IntegerField(blank=True, default=1)

    class Meta:
        verbose_name = "Área de Vinculação"
        verbose_name_plural = "Áreas de Vinculação"
        ordering = ("ordem",)

    def __str__(self):
        return self.descricao

    def save(self):
        if not self.ordem:
            self.ordem = AreaVinculacao.objects.all().aggregate(Max("ordem")).get("ordem__max", 0) + 1
        super().save()


class Setor(ModelPlus):
    SEARCH_FIELDS = ["sigla", "codigo", "nome", "codigo_siorg"]

    DESCENDENTES = dict()

    codigo = models.CharField(
        "Código SIAPE",
        max_length=9,
        unique=True,
        null=True,
        blank=True,
        help_text="Caso o setor tenha este campo em branco será considerado setor SUAP",
    )
    uo = models.ForeignKeyPlus(
        "rh.UnidadeOrganizacional",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.CASCADE,
        related_name="setor_set",
        verbose_name="Campus",
        db_column="uo_id",
    )
    superior = models.ForeignKeyPlus("self", null=True, blank=True, verbose_name="Setor Superior", on_delete=models.CASCADE)
    sigla = models.CharField(max_length=15)
    nome = models.CharField(max_length=100)
    excluido = models.BooleanField(
        verbose_name="Excluído", default=False, help_text="Setores excluídos não farão parte das buscas e não devem possuir servidores"
    )
    setores_compartilhados = models.ManyToManyField("self")
    codigo_siorg = models.CharField(max_length=6, blank=True, verbose_name="Código SIORG")

    areas_vinculacao = models.ManyToManyFieldPlus(AreaVinculacao, verbose_name="Áreas de Vinculação", blank=True)
    equivalencia_codigo = models.CharField('Código de Equivalência', max_length=9, unique=True, null=True, blank=True, help_text='Código do setor SIAPE que é equivalente a este setor SUAP.')

    objects = SetoresSuapAtivosManager()
    todos = SetorManager()
    suap = SetoresSuapManager()
    siape = SetoresSiapeManager()

    data_criacao = models.DateFieldPlus(verbose_name="Data de Criação", null=True, blank=True)
    horario_funcionamento = models.TextField(verbose_name="Horário de Funcionamento", null=True, blank=True)
    bases_legais_internas = RichTextField(verbose_name="Bases Legais Internas", null=True, blank=True)
    bases_legais_externas = RichTextField(verbose_name="Bases Legais Externas", null=True, blank=True)

    class Meta:
        db_table = "setor"
        ordering = ["sigla"]
        verbose_name = "Setor"
        verbose_name_plural = "Setores"

        # Definindo o manager principal. É esse manager que será usado, por default, em todas as consultas do Django,
        # como por exemplo nas rotinas de dump e em fields de ModelForms. Essa definição é muito mais prática e segura
        # do que a abordagem do Django de usar o primeiro manager definido na classe.
        # Observar migration do RH - 0104_auto_20190123_1947.py.
        # https://docs.djangoproject.com/pt-br/2.1/topics/db/managers/#default-managers
        default_manager_name = "todos"
        # FIXME: essa definição de um manager default=objects quebrou o manager de setores SIAPE utilizado no histórico de função do servidor, pois o admin carregava apenas setores suap ativos como instâncias válidas, não sendo possível salvar uma instância de setor SIAPE.

        permissions = (
            ("pode_gerenciar_setor_telefone", "Pode gerenciar telefones de setores"),
            ("pode_gerenciar_setor_jornada_historico", "Pode gerenciar carga horária de setores"),
        )

    def save(self, *args, **kwargs):
        """
        O método foi sobrescrito para preencher automaticamente o campo ``uo``.
        O critério para definir um setor SUAP é ter o campo codigo nulo. Porém, codigo
        é tipo texto e o Django preenche o codigo com uma string vazia quando um
        superusuario edita setores SUAP
        """
        self.uo = self._get_uo()
        if not self.codigo:
            self.codigo = None

        if not self.pk:
            Setor.DESCENDENTES = dict()
        else:
            superior = Setor.todos.get(pk=self.pk).superior
            if superior != self.superior:
                Setor.DESCENDENTES = dict()
                self.__reload_descendentes()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.sigla

    def get_absolute_url(self):
        return f"/rh/setor/{self.pk:d}/"

    def get_ext_combo_template(self):
        return self.get_caminho_as_html()

    @classmethod
    def get_folhas(cls):
        """Retorna os setores que não tem filhos (os folhas da árvore de setores)"""
        setores_com_filhos = cls.objects.filter(superior__isnull=False).values_list("superior", flat=True).distinct()
        return cls.objects.exclude(id__in=setores_com_filhos)

    @classmethod
    def raiz(cls):
        from comum.utils import get_sigla_reitoria

        try:
            return cls.objects.get(sigla=get_sigla_reitoria())
        except cls.MultipleObjectsReturned:
            raise Exception("Existe mais de um setor raiz.")
        except cls.DoesNotExist:
            raise Exception("Setor raiz inexistente.")

    def _get_uo(self):
        """
        Irá buscar o valor do campo ``uo`` recursivamente da hierarquia de
        setores. O retorno desta função deve ser igual ao valor do campo ``uo``.
        """
        setor_atual = self
        while setor_atual is not None:
            resultado = UnidadeOrganizacional.objects.filter(setor=setor_atual)
            if resultado:
                return resultado[0]
            setor_atual = setor_atual.superior
        return None

    @property
    def filhos(self):
        return Setor.todos.filter(superior=self)

    def __get_descendentes_helper(self, lista):
        lista.append(self)
        for f in self.filhos:
            f.__get_descendentes_helper(lista)
        return lista

    def __reload_descendentes(self):
        lista = [self]
        for f in self.filhos:
            f.__get_descendentes_helper(lista)
        Setor.DESCENDENTES[self] = lista

    @property
    def descendentes(self):
        if not Setor.DESCENDENTES.get(self):
            self.__reload_descendentes()
        return self.DESCENDENTES.get(self)

    @property
    def ids_descendentes(self):
        return [i.id for i in self.descendentes]

    def get_codigo_siorg(self):
        if self.codigo_siorg:
            return self.codigo_siorg
        setor = self.superior
        while setor is not None:
            if setor.codigo_siorg:
                return setor.codigo_siorg
            setor = setor.superior
        return None

    # ---------------------------------------------------------------------
    # Lista de Servidores do Setor
    # ---------------------------------------------------------------------
    def get_servidores(self, recursivo=True):
        if recursivo:
            return Servidor.objects.ativos().filter(setor__in=self.descendentes)
        else:
            return Servidor.objects.ativos().filter(setor=self)

    def qtd_servidores(self, recursivo=False):
        if recursivo:
            return Servidor.objects.ativos_permanentes().filter(setor__in=self.descendentes).count()
        else:
            return Servidor.objects.ativos_permanentes().filter(setor=self).count()

    def get_servidores_por_periodo(self, data_inicial=None, data_final=None, recursivo=True):
        if (data_inicial is None) and (data_final is None):
            #
            # returna a lista atual de servidores baseado no atributo 'setor' de 'Servidor'
            #
            return self.get_servidores(recursivo)
        else:
            if data_inicial is None:
                #
                # foi passado um período com apenas a data final informada
                #
                return []
            else:
                #
                # nesse ponto, temos um período com data inicial e data final informados
                # seleciona os servidores que estavam no setor (OU descendentes) no período informado
                #
                setores = [self]
                if recursivo:
                    setores += self.descendentes

                if not data_final:
                    data_final = datetime.date.today()
                #
                # selecionar os servidores envolvidos via históricos de setor
                #

                qs_1 = ServidorSetorHistorico.objects.filter(
                    setor__in=setores, data_inicio_no_setor__lte=data_final, data_fim_no_setor__gte=data_inicial
                )  # inicio fora e termino dentro do período (incluindo extremidades)

                qs_2 = ServidorSetorHistorico.objects.filter(
                    setor__in=setores, data_inicio_no_setor__lte=data_final, data_fim_no_setor__isnull=True
                )

                historicos_setor = (
                    (qs_1 | qs_2).exclude(servidor__data_fim_servico_na_instituicao__lt=data_inicial).distinct().order_by("servidor__nome")
                )

                servidores = []
                for historico_setor in historicos_setor:
                    if not historico_setor.servidor in servidores:
                        servidores.append(historico_setor.servidor)

                return servidores

    def get_funcionarios(self, recursivo=True):
        if recursivo:
            return Funcionario.objects.filter(setor__in=self.descendentes)
        else:
            return Funcionario.objects.filter(setor=self)

    @property
    def setor_eh_campus(self):
        return hasattr(self, "unidadeorganizacional")

    @property
    def eh_orgao_colegiado(self):
        tipo_orgao = TipoUnidadeOrganizacional.objects.filter(descricao="Conselhos e Órgãos Colegiados").first()
        if self.setor_eh_campus:
            return self.unidadeorganizacional.tipo == tipo_orgao
        return False

    def get_caminho(self, ordem_descendente=True):
        """
        Retorna a lista de setores que fazem a hierarquia do setor desde o setor
        raiz.
        """
        caminho = []
        setor_atual = self
        while setor_atual:
            caminho.append(setor_atual)
            setor_atual = setor_atual.superior
        #
        if ordem_descendente:
            caminho.reverse()

        return caminho

    def get_caminho_setor(self, setor):
        """
        Retorna a lista de setores que fazem a hierarquia do setor desde o setor informado
        """
        caminho = [self]
        if self != setor and self.id in self.ids_descendentes:
            setor_atual = self.superior
            while setor_atual != setor:
                caminho.append(setor_atual)
                setor_atual = setor_atual.superior
            caminho.append(setor_atual)
        caminho.reverse()
        return caminho

    def get_caminho_as_html(self):
        caminho = self.get_caminho()
        caminho_html = []
        for s in caminho:
            if hasattr(s, "unidadeorganizacional"):
                s_repr = f'<span class="admin-setor-uo" title="{s.nome}">{s}</span>'
            elif s == caminho[-1]:
                s_repr = f'<span class="admin-setor" title="{s.nome}">{s} ({s.nome})</span>'
            else:
                s_repr = f'<span title="{s.nome}">{s}</span>'
            caminho_html.append(s_repr)
        return mark_safe(" &rarr; ".join(caminho_html))

    def pode_gerar_carteira_funcional(self):
        """
        Define se podem ser geradas carteiras funcionais do setor.
        """
        servidores = Servidor.objects.filter(setor=self)
        setor_pode_gerar = True
        for servidor in servidores:
            if not servidor.pode_gerar_carteira_funcional():
                setor_pode_gerar = False
                break
        return setor_pode_gerar

    @classmethod
    def get_setores_vazios(cls):
        """
        Deve retornar queryset de setores que não tem ninguém. Cada setorX desse
        queryset deve satisfazer as 3 condições:
        - Ninguém lotado no setorX (FK setor do funcionario)
        - Ninguém onde setorX é um dos setores adicionais
        - Ninguém de algum setor que tenha o setorX compartilhado.
        Resumindo, é o setor que ninguém é responsável por receber processos.
        """
        setores = (
            Setor.objects.filter(funcionarios__isnull=True)
            .exclude(pessoa__setores_adicionais__id=F("id"))
            .exclude(setores_compartilhados=F("id"))
            .exclude(compartilhamentosetorpessoa__setor_dono__id=F("id"))
            .exclude(compartilhamentoprocessoeletronicopoderchefe_setor_dono_set__setor_dono__id=F("id"))
        )
        return setores

    @property
    def chefes(self):
        """Retorna os servidores com função do setor"""
        hoje = datetime.date.today()
        chefes = (
            ServidorFuncaoHistorico.objects.filter(
                setor_suap=self,
                funcao__codigo__in=[Funcao.CODIGO_CD, Funcao.CODIGO_FG],
            )
            .filter(Q(data_fim_funcao__gte=hoje) | Q(data_fim_funcao__isnull=True))
            .values_list("servidor", flat=True)
        )
        return Servidor.objects.filter(excluido=False, pk__in=chefes)

    def historico_funcao(self, data_inicial=None, data_final=None):
        """histórico de funções exercidas no Setor em um período
        procura a interseção entre período informado e os períodos das funções
        """
        hoje = datetime.datetime.date(datetime.datetime.now())
        if not data_inicial:
            data_inicial = hoje
        if not data_final:
            data_final = hoje

        # data de inicio da funcao dentro do período informado
        historico_funcao = ServidorFuncaoHistorico.objects.filter(
            setor_suap=self,
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia(),
            data_inicio_funcao__gte=data_inicial,
            data_inicio_funcao__lte=data_final,
        )

        # data de inicio da funcao antes do período informado e data fim da função depois da data inicio do período
        historico_funcao = historico_funcao | ServidorFuncaoHistorico.objects.filter(
            setor_suap=self,
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia(),
            data_inicio_funcao__lt=data_inicial,
            data_fim_funcao__gte=data_inicial,
        )

        # data de inicio da funcao antes do período informado e sem data fim
        historico_funcao = historico_funcao | ServidorFuncaoHistorico.objects.filter(
            setor_suap=self,
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia(),
            data_inicio_funcao__lt=data_inicial,
            data_fim_funcao__isnull=True,
        )

        # data de fim da funcao deve está dentro do período informado
        historico_funcao = historico_funcao | ServidorFuncaoHistorico.objects.filter(
            setor_suap=self,
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia(),
            data_fim_funcao__gte=data_final,
            data_fim_funcao__lte=data_final,
        )

        return historico_funcao.distinct()

    # jornada de trabalho do setor em uma determinada data
    def jornada_trabalho_por_periodo_dict(self, data_inicio, data_fim):
        qs_1 = SetorJornadaHistorico.objects.filter(setor=self, data_inicio_da_jornada__lte=data_fim, data_fim_da_jornada__gte=data_inicio)
        qs_2 = SetorJornadaHistorico.objects.filter(setor=self, data_inicio_da_jornada__lte=data_fim, data_fim_da_jornada__isnull=True)
        qs = (qs_1 | qs_2).distinct()
        jornadas = dict()
        for jornada_historico in qs:
            data_inicio_jornada = jornada_historico.data_inicio_da_jornada
            data_fim_jornada = jornada_historico.data_fim_da_jornada
            if data_inicio_jornada <= data_inicio:
                data_inicio_jornada = data_inicio
            if not data_fim_jornada or data_fim_jornada >= data_fim:
                data_fim_jornada = data_fim
            for dia in datas_entre(data_inicio_jornada, data_fim_jornada):
                jornadas[dia] = jornada_historico.jornada_trabalho

        return jornadas

    def get_jornadas_setor_por_data(self, data=None):
        if data is None:
            data = datetime.date.today()

        qs_1 = SetorJornadaHistorico.objects.filter(setor=self, data_inicio_da_jornada__lte=data, data_fim_da_jornada__gte=data)
        qs_2 = SetorJornadaHistorico.objects.filter(setor=self, data_inicio_da_jornada__lte=data, data_fim_da_jornada__isnull=True)
        return (qs_1 | qs_2).distinct()

    def get_jornada_trabalho(self, data=None):
        qs = self.get_jornadas_setor_por_data(data)
        return qs.first()

    def jornada_trabalho(self, data=None):
        jornada = self.get_jornada_trabalho(data)
        return jornada.jornada_trabalho if jornada else None

    def tipo_jornada_trabalho_por_data(self, data=None):
        jornada = self.jornada_trabalho(data)
        return 'Flexibilizada' if jornada and jornada.nome == "30 HORAS SEMANAIS" else 'Padrão'

    # mensagens referentes a situação dos períodos cadastrados para o setor
    def jornada_trabalho_pendencias(self):
        periodos = list()
        for periodo in SetorJornadaHistorico.objects.filter(setor=self).order_by("data_inicio_da_jornada"):
            periodos.append((periodo.data_inicio_da_jornada, periodo.data_fim_da_jornada))

        if periodos:
            #
            # se a data final do último período for nula, usa a data de 'hoje' de modo a processar períodos "fechados"
            #
            ultimo_periodo = periodos[-1:][0]
            data_inicial = ultimo_periodo[0]
            data_final = ultimo_periodo[1]
            if not data_final:
                periodos.pop()  # remove o último período
                if data_inicial < datetime.date.today():
                    periodos.append((data_inicial, datetime.date.today()))  # adiciona o último período com data final igual a hoje
                else:
                    periodos.append((data_inicial, data_inicial))  # último período com data inicial ainda no futuro

            periodos_mensagens_pendencias = periodos_sucessivos(periodos)
            mensagens_periodos = periodos_mensagens_pendencias[1]
        else:
            mensagens_periodos = ("Sem histórico de jornada de trabalho.",)

        return mensagens_periodos

    def salvar_areas_vinculacao_recursivamente(self, areas_vinculacao):
        for setor_filho in self.filhos.all():
            setor_filho.areas_vinculacao.clear()
            for area_vinculacao in areas_vinculacao:
                setor_filho.areas_vinculacao.add(area_vinculacao)
            setor_filho.salvar_areas_vinculacao_recursivamente(areas_vinculacao)

    def telefones(self, sem_ramal=False):
        out = []
        for st in self.setortelefone_set.all():
            valor = st
            if sem_ramal:
                valor = st.numero
            out.append(f"{valor}")
        if out:
            return ", ".join(out)
        return None


class SetorJornadaHistorico(ModelPlus):
    setor = models.ForeignKeyPlus("rh.Setor", verbose_name="Setor", null=False, blank=False, on_delete=models.CASCADE)
    jornada_trabalho = models.ForeignKeyPlus("rh.JornadaTrabalho", verbose_name="Jornada de Trabalho", null=False, blank=False)
    data_inicio_da_jornada = models.DateFieldPlus("Data Inicial da Jornada", null=False, blank=False, default=datetime.datetime.today)
    data_fim_da_jornada = models.DateFieldPlus("Data Final da Jornada", null=True, blank=True)

    def __str__(self):
        # MeuSetor: 2 horas semanas - 01/01/0000 a 31/12/9999

        data_fim = "-"
        if self.data_fim_da_jornada:
            data_fim = self.data_fim_da_jornada.strftime("%d/%m/%Y")

        if self.data_fim_da_jornada:
            return "{}: {} - {} a {}".format(self.setor, self.jornada_trabalho, self.data_inicio_da_jornada.strftime("%d/%m/%Y"), data_fim)
        else:
            return "{}: {} - a partir de {}".format(self.setor, self.jornada_trabalho, self.data_inicio_da_jornada.strftime("%d/%m/%Y"))

    class Meta:
        verbose_name = "Histórico de Jornada do Setor"
        verbose_name_plural = "Históricos de Jornadas dos Setores"
        ordering = ("setor", "-data_inicio_da_jornada")


class PessoaJuridica(Pessoa):
    SEARCH_FIELDS = ["search_fields_optimized"]
    RELEVANCE_ORDERING = []

    nome_fantasia = models.CharFieldPlus(verbose_name="Nome Fantasia", blank=True)
    cnpj = models.BrCnpjField(unique=True)

    ramo_atividade = models.CharFieldPlus(verbose_name="Ramo de Atividade", null=True, blank=True)
    nome_representante_legal = models.CharFieldPlus(verbose_name="Nome do Representante Legal", null=True, blank=True)

    inscricao_estadual = models.CharField(max_length=20, null=True, blank=True, verbose_name="Inscrição Estadual")
    matricula = models.CharFieldPlus("Matrícula", max_length=30, db_index=True)
    vinculos = GenericRelation(
        "comum.Vinculo",
        related_query_name="pessoasjuridicas",
        object_id_field="id_relacionamento",
        content_type_field="tipo_relacionamento",
    )

    class Meta:
        db_table = "pessoa_juridica"
        verbose_name = "Pessoa Jurídica"
        verbose_name_plural = "Pessoas Jurídicas"

    def __str__(self):
        if self.nome_fantasia and len(self.nome_fantasia) > 1:
            return f"{normalizar_nome_proprio(self.nome_fantasia)} ({self.matricula})"
        return f"{normalizar_nome_proprio(self.nome)} ({self.matricula})"

    def get_absolute_url(self):
        return f"/rh/pessoajuridica/{self.pk}/"

    def get_vinculo(self):
        return self.vinculo_set.first()

    def get_foto_75x100_url(self):
        return "/static/comum/img/default.jpg"

    def get_foto_150x200_url(self):
        return "/static/comum/img/default.jpg"

    def get_representantes(self):
        return self.ocupacaoprestador_set.filter(ocupacao__representante=True)

    def get_ext_combo_template(self):
        out = [f"{self.pessoajuridica.nome} ({self.pessoajuridica.cnpj})"]
        template = """
              <div>
                  {}
              </div>
              """.format(
            "".join(out)
        )

        if self.excluido:
            template += '<p class="false">Vínculo inativo</p>'

        return template

    def get_user(self):
        from comum.models import User

        qs = User.objects.filter(username=self.matricula)
        return qs.exists() and qs[0] or None

    def _get_search_fields_optimized_content_to_save(self):
        return "{}{}{}".format(self.nome or "", self.cnpj or "", self.matricula or "")

    def save(self, *args, **kwargs):
        from comum.models import Vinculo

        if not cpfcnpj.validate(self.cnpj):
            raise ValidationError(f"O CNPJ {self.cnpj} associado a {self.nome_fantasia} não é valido.")

        self.matricula = re.sub(r"\D", "", str(self.cnpj))

        super().save(*args, **kwargs)

        user = self.get_user()
        if not Vinculo.objects.filter(pessoasjuridicas=self).exists():
            vinculo = Vinculo()
            vinculo.pessoa = self.pessoa_ptr
            vinculo.user = user
            vinculo.relacionamento = self
            vinculo.save()
        return self


class PessoaJuridicaContato(models.ModelPlus):
    pessoa_juridica = models.ForeignKey(PessoaJuridica, on_delete=models.CASCADE)
    descricao = models.CharField("Descrição", null=True, max_length=200)
    telefone = models.CharField("Telefone", null=True, max_length=45)
    email = models.EmailField("E-mail", null=True)
    via_form_suap = models.BooleanField("Via SUAP?", default=False)

    class Meta:
        verbose_name = "Contato da Pessoa Jurídica"
        verbose_name_plural = "Contatos da Pessoa Jurídica"


class PessoasFisicasPodePegarChaveManager(models.Manager):
    """
    Manager que retorna apenas as pessoas aptas a pegar chave, seja porque já possuem
    digital seja porque não precisam da digital.
    """

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .extra(where=["(tem_digital_fraca=True or template is not null)"])
        )
        return qs


class PessoasFisicasPodeCadastrarAtendimentos(models.Manager):
    """
    Manager que retorna apenas as pessoas que podem cadastrar ou editar atendimentos de alunos.
    """

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .filter(
                Q(user__groups__permissions__codename="add_demandaalunoatendida")
                | Q(user__groups__permissions__codename="change_demandaalunoatendida")
            )
            .distinct()
        )
        return qs


class PessoaFisica(Pessoa):
    SEARCH_FIELDS = ["search_fields_optimized"]
    RELEVANCE_ORDERING = [("eh_servidor", True), ("eh_prestador", True), ("eh_aluno", True), ("eh_residente", True), ("eh_trabalhadoreducando", True)]

    user = models.OneToOneField("comum.User", null=True, blank=True, on_delete=models.CASCADE)
    cpf = models.CharField(max_length=20, null=True, verbose_name="CPF", blank=False, db_index=True)
    passaporte = models.CharFieldPlus(max_length=50, verbose_name="Nº do Passaporte", blank=True, default="")
    # TODO verificar documento identificador
    documento_identificador = models.CharFieldPlus(max_length=50, null=True, blank=False, db_index=True)
    sexo = models.CharField(max_length=1, null=True, choices=[["M", "Masculino"], ["F", "Feminino"]])
    grupo_sanguineo = models.CharField(
        "Grupo Sanguíneo", max_length=2, null=True, blank=True, choices=[["A", "A"], ["B", "B"], ["AB", "AB"], ["O", "O"]]
    )
    fator_rh = models.CharField("Fator RH", max_length=8, null=True, blank=True, choices=[["+", "+"], ["-", "-"]])
    titulo_numero = models.CharField(max_length=12, null=True, blank=True)
    titulo_zona = models.CharField(max_length=3, null=True, blank=True)
    titulo_secao = models.CharField(max_length=4, null=True, blank=True)
    titulo_uf = models.BrEstadoBrasileiroField(null=True, blank=True)
    titulo_data_emissao = models.DateField(null=True)
    rg = models.CharField(max_length=20, null=True, verbose_name="RG")
    rg_orgao = models.CharField(max_length=10, null=True)
    rg_data = models.DateField(null=True)
    rg_uf = models.BrEstadoBrasileiroField(null=True)
    nascimento_municipio = models.ForeignKeyPlus(
        "comum.Municipio", null=True, blank=True, verbose_name="Município", on_delete=models.CASCADE
    )
    nascimento_data = models.DateFieldPlus("Data de Nascimento", null=True)
    nome_mae = models.CharField("Nome da Mãe", max_length=100, null=True)
    nome_pai = models.CharField("Nome do Pai", max_length=100, null=True, blank=True)
    foto = ImageWithThumbsField(
        storage=get_overwrite_storage(), use_id_for_name=True, upload_to="fotos", sizes=((75, 100), (150, 200)), null=True, blank=True
    )
    cnh_carteira = models.CharField(max_length=10, null=True, blank=True)
    cnh_registro = models.CharField(max_length=10, null=True, blank=True)
    cnh_categoria = models.CharField(max_length=10, null=True, blank=True)
    cnh_emissao = models.DateField(null=True, blank=True)
    cnh_uf = models.CharField(max_length=2, null=True, blank=True)
    cnh_validade = models.DateField(null=True, blank=True)
    ctps_numero = models.CharField(max_length=20, null=True, blank=True)
    ctps_uf = models.CharField(max_length=2, null=True, blank=True)
    ctps_data_prim_emprego = models.DateField(null=True, blank=True)
    ctps_serie = models.CharField(max_length=10, null=True, blank=True)
    pis_pasep = models.CharField(max_length=20, null=True, blank=True, verbose_name="PIS / PASEP")
    pagto_banco = models.ForeignKeyPlus("rh.Banco", null=True, blank=True, on_delete=models.CASCADE, verbose_name="Banco")
    pagto_agencia = models.CharField(max_length=20, null=True, blank=True, verbose_name="Agência")
    pagto_ccor = models.CharField(max_length=20, null=True, blank=True, verbose_name="Conta")
    pagto_ccor_tipo = models.CharField(max_length=2, blank=True, null=True, verbose_name="Tipo")
    username = models.CharField(max_length=50, null=True, unique=True, db_index=True)
    tem_digital_fraca = models.BooleanField(
        default=False,
        blank=True,
        verbose_name="Permitir registro de ponto sem impressão digital",
        help_text="Pessoas com impressão digital fraca devem ter essa " "opção marcada",
    )
    senha_ponto = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Senha para registro de ponto sem impressão digital",
        help_text="Pessoas com impressão digital fraca devem ter uma senha " "definida para usar o terminal",
    )
    data_obito = models.DateField(null=True, blank=True)
    template = models.BinaryField(null=True, blank=True, editable=False)
    template_importado_terminal = models.BooleanField(default=False, verbose_name="Digital importada do terminal")
    # busca = SearchField(search=['nome', 'get_cpf_ou_cnpj'])
    estado_civil = models.ForeignKeyPlus("comum.EstadoCivil", null=True, on_delete=models.CASCADE)
    raca = models.ForeignKeyPlus("comum.Raca", null=True, on_delete=models.CASCADE)

    nacionalidade = models.IntegerField("Nacionalidade", choices=Nacionalidade.get_choices(), null=True)
    pais_origem = models.ForeignKeyPlus(
        "comum.Pais", verbose_name="País de Origem", null=True, on_delete=models.CASCADE
    )  # para estrangeiro

    deficiencia = models.ForeignKeyPlus("rh.Deficiencia", verbose_name="Deficiência", null=True, on_delete=models.CASCADE)
    lattes = models.URLField(blank=True)
    eh_servidor = models.BooleanField(default=False)
    eh_aluno = models.BooleanField(default=False)
    eh_residente = models.BooleanField(default=False)
    eh_trabalhadoreducando = models.BooleanField(default=False)
    eh_prestador = models.BooleanField(default=False)

    objects = InheritanceManager()
    pode_pegar_chave = PessoasFisicasPodePegarChaveManager()
    pode_cadastrar_atendimentos = PessoasFisicasPodeCadastrarAtendimentos()

    class History:
        ignore_fields = ('template', 'search_fields_optimized')

    class Meta:
        db_table = "pessoa_fisica"
        verbose_name = "Pessoa Física"
        verbose_name_plural = "Pessoas Físicas"

        permissions = (
            ("pode_gerar_cracha", "Pode gerar crachá"),
            ("pode_cadastrar_digital", "Pode cadastrar digital"),
            ("pode_atualizar_digital", "Pode atualizar digital"),
            ("pode_gerar_carteira", "Pode gerar carteira"),
        )

    def __str__(self):
        return self.nome

    def get_ext_combo_template_text(self):
        vinculo = self.sub_instance()
        return f"{vinculo}"

    def get_ext_combo_template(self):
        vinculo = self.sub_instance()
        if not type(vinculo) == PessoaFisica and hasattr(vinculo, "get_ext_combo_template"):
            return vinculo.get_ext_combo_template()
        else:
            template = """<div class="person">
                <div class="photo-circle">
                    <img src="{0}" alt="Foto de {1}" />
                </div>
                <dl>
                    <dt class="sr-only">Nome</dt><dd><strong>{1}</strong> ({2})</dd>
                    <dt class="sr-only">Categoria</dt><dd>Pessoa Física</dd>
                </dl>
            </div>
        """.format(
                self.get_foto_75x100_url(), self.nome or "Sem nome", f"{anonimizar_cpf(self.cpf)}"
            )

        if self.excluido:
            template += '<p class="false">Vínculo inativo</p>'

        return template

    def _get_search_fields_optimized_content_to_save(self):
        return "{}{}{}{}".format(self.nome or "", self.cpf or "", self.username or "", re.sub(r'\D', '', str(self.cpf)) or "")

    def save(self, *args, **kwargs):
        from comum.models import PrestadorServico
        """
        Caso `self` tenha username, um usuário será criado para `self`.
        """
        tem_aluno = False
        aluno_com_passaporte = None

        if self.pk:
            if "edu" in settings.INSTALLED_APPS:
                tem_aluno = self.aluno_edu_set.all().exists()
                aluno_com_passaporte = self.aluno_edu_set.exclude(passaporte="").last()
            self.eh_servidor = Servidor.objects.filter(pessoafisica_ptr=self.pk).exists()
            self.eh_aluno = tem_aluno
            # Atualiza o eh_prestador de acordo com ocupação vigente
            if hasattr(self, "ocupacaoprestador_set") and self.ocupacaoprestador_set.filter(
                    data_fim__gte=datetime.datetime.today()).exists():
                self.eh_prestador = PrestadorServico.objects.filter(pessoafisica_ptr=self.pk).exists()

        if self.username:
            from comum.models import User

            try:
                user = User.objects.get(username=self.username)
            except User.DoesNotExist:
                user = User.objects.create_user(self.username, email="", password=None)
                Configuracao = apps.get_model("comum", "configuracao")
                if not Configuracao.get_valor_por_chave("ldap_backend", "utilizar_autenticacao_via_ldap"):
                    hasher = get_hasher()
                    sigla = Configuracao.get_valor_por_chave("comum", "instituicao_sigla") or ""
                    cpf = self.cpf.replace(".", "").replace("-", "")
                    password = make_password(f"{sigla}.{cpf}", "", hasher)
                    User.objects.filter(id=user.id).update(password=password)

            self.user = user
            try:
                self.user.reset_profile()
                self.user.reset_vinculo()
            except Exception:
                pass
        else:
            self.user = None

        if not self.nome_usual:
            if len(self.nome.split(" ")) > 1:
                self.nome_usual = " ".join(self.nome.split()[:1] + self.nome.split()[-1:])[:30]
            else:
                # Ocorre quando nome só possui uma palavra
                self.nome_usual = self.nome[:30]

        if not self.nome_registro and self.nome:
            self.nome_registro = self.nome

        if self.nome_social:
            self.nome = self.nome_social
        else:
            self.nome = self.nome_registro

        if self.cpf:
            self.documento_identificador = self.cpf
        else:
            self.cpf = None
            if aluno_com_passaporte:
                self.documento_identificador = aluno_com_passaporte.passaporte
            else:
                self.documento_identificador = None

        # Comentado à pedido de Augusto
        # if not settings.DEBUG and not cpfcnpj.validate(self.cpf):
        #     raise ValidationError(u"O CPF {} associado a {} não é valido.".format(self.cpf, self.nome))
        return super().save(*args, **kwargs)

    def get_emails_disponiveis(self, tipo="institucional"):
        """
        Regras para geração de emails:
            - institucional:
                Não pode existir email em Servidor.email
            - academico:
                Não pode existir email com mesmo prefixo em Servidor.email (exceto se servidor for `self`)
                Não pode existr email em Servidor.email_academico e Aluno.email_academico
            - google_classroom:
                Não pode existir email em Servidor.email_google_classroom e Aluno.email_google_classroom

        """
        from edu.models import Aluno
        from comum.models import Configuracao

        assert tipo in ("institucional", "academico", "google_classroom")

        dominio = Configuracao.get_valor_por_chave("ldap_backend", f"dominio_{tipo}")
        if not dominio:
            return []

        def define_emails(tokens, abrevia_nome=False, abrevia_sobrenome=False, numero=None):
            emails_possiveis = []
            emails_existentes = []
            prefixos_possiveis = []
            for t1 in tokens:
                for t2 in tokens:
                    if not t1 == t2:

                        nome = t1[0] if abrevia_nome else t1
                        sobrenome = t2[0] if abrevia_sobrenome else t2
                        if numero:
                            emails_possiveis.append(f"{nome}.{sobrenome}{numero}@{dominio}")
                            prefixos_possiveis.append(f"{nome}.{sobrenome}{numero}@")
                        else:
                            emails_possiveis.append(f"{nome}.{sobrenome}@{dominio}")
                            prefixos_possiveis.append(f"{nome}.{sobrenome}@")

            EmailBlockList = apps.get_model("comum", "EmailBlockList")
            if tipo == "institucional":
                emails_servidores = Servidor.objects.filter(email_institucional__in=emails_possiveis).values_list(
                    "email_institucional", flat=True
                )
                emails_ldap = []
                if not settings.DEBUG and 'ldap_backend' in settings.INSTALLED_APPS:
                    from ldap_backend.models import LdapConf
                    ldap_conf = LdapConf.get_active()
                    emails_ldap = [email_possivel for email_possivel in emails_possiveis if ldap_conf.get_usernames_from_mail(email_possivel)]
                emails_existentes = set().union(emails_servidores, emails_ldap)
            elif tipo == "academico":
                dominioinstitucional = Configuracao.get_valor_por_chave("ldap_backend", "dominio_institucional")
                emails_institucionais_possiveis = [prefixo + dominioinstitucional for prefixo in prefixos_possiveis]

                emails_institucional = (
                    Servidor.objects.exclude(id=self.id)
                    .filter(email_institucional__in=emails_institucionais_possiveis)
                    .values_list("email_institucional", flat=True)
                )
                """ Se encontrou email institucional, vai remover da lista de emails possiveis """
                emails_institucional = [email.split("@")[0] + "@" + dominio for email in emails_institucional]
                emails_possiveis = [email for email in emails_possiveis if not email in emails_institucional]
                emails_ldap = []

                emails_academico = Servidor.objects.filter(email_academico__in=emails_possiveis).values_list("email_academico", flat=True)
                emails_alunos = Aluno.objects.filter(email_academico__in=emails_possiveis).values_list("email_academico", flat=True)
                emails_bloqueados = EmailBlockList.objects.filter(email__in=emails_possiveis).values_list("email", flat=True)
                if not settings.DEBUG and 'ldap_backend' in settings.INSTALLED_APPS:
                    from ldap_backend.models import LdapConf
                    ldap_conf = LdapConf.get_active()
                    emails_ldap = [email_possivel for email_possivel in emails_possiveis if ldap_conf.get_usernames_from_principalname(email_possivel)]

                emails_existentes = set().union(emails_academico, emails_alunos, emails_bloqueados, emails_ldap)
            elif tipo == "google_classroom":
                emails_servidores = Servidor.objects.filter(email_google_classroom__in=emails_possiveis).values_list(
                    "email_google_classroom", flat=True
                )
                emails_alunos = Aluno.objects.filter(email_google_classroom__in=emails_possiveis).values_list(
                    "email_google_classroom", flat=True
                )
                emails_bloqueados = EmailBlockList.objects.filter(email__in=emails_possiveis).values_list("email", flat=True)
                emails_existentes = set().union(emails_servidores, emails_alunos, emails_bloqueados)

            return set(emails_possiveis) - set(emails_existentes)

        tokens = to_ascii(retirar_preposicoes_nome(self.nome).lower()).replace(".", "").split()
        if tipo == "institucional":
            emails = define_emails(tokens)
        else:
            emails = define_emails(tokens)
            emails = emails.union(define_emails(tokens, abrevia_nome=True))
            emails = emails.union(define_emails(tokens, abrevia_sobrenome=True))
            if len(emails) == 0:
                cont = 1
                while len(emails) == 0:
                    emails = define_emails(tokens, numero=cont)
                    cont = cont + 1

        return emails

    def get_foto_75x100_url(self):
        path_img = ""
        default_img = "/static/comum/img/default.jpg"
        if self.eh_aluno:
            aluno = self.aluno_edu_set.first()
            if aluno and aluno.foto:
                path_img = aluno.foto.url_75x100
        elif self.eh_residente:
            residente = self.residente_set.first()
            if residente and residente.foto:
                path_img = residente.foto.url_75x100
        elif self.eh_trabalhadoreducando:
            trabalhadoreducando = self.trabalhadoreducando_set.first()
            if trabalhadoreducando and trabalhadoreducando.foto:
                path_img = trabalhadoreducando.foto.url_75x100
        else:
            if self.foto:
                path_img = self.foto.url_75x100
        return path_img or default_img

    def get_foto_150x200_url(self):
        path_img = ""
        default_img = "/static/comum/img/default.jpg"
        if self.eh_aluno:
            aluno = self.aluno_edu_set.first()
            if aluno and aluno.foto:
                path_img = aluno.foto.url_150x200
        elif self.eh_residente:
            residente = self.residente_set.first()
            if residente and residente.foto:
                path_img = residente.foto.url_150x200
        elif self.eh_trabalhadoreducando:
            trabalhadoreducando = self.trabalhadoreducando_set.first()
            if trabalhadoreducando and trabalhadoreducando.foto:
                path_img = trabalhadoreducando.foto.url_150x200
        else:
            if self.foto:
                path_img = self.foto.url_150x200
        return path_img or default_img

    def get_foto_url(self):
        return self.foto and self.foto.url or "/static/comum/img/default.jpg"

    def get_template(self, encoding="utf-8"):
        if self.template is None:
            return "".encode(encoding)
        if type(self.template) == memoryview:
            template = self.template.tobytes()
        else:
            template = self.template
        if encoding == "utf-8":
            return template
        else:
            return template.decode("utf-8").encode(encoding)

    def get_usuario_ldap(self, attrs=None):
        from ldap_backend.models import LdapConf

        return LdapConf.get_active().get_user(self.username, attrs=attrs)

    def get_absolute_url(self):
        sub_instance = self.sub_instance()
        if type(sub_instance) == PessoaFisica:
            return "#"
        return sub_instance.get_absolute_url()

    def sub_instance(self):
        """
        Retorna a especialização da PessoaFisica, pode ser um objeto da classe:
            a) Servidor
            b) PrestadorServico
            c) Aluno
            d) Residente
            e) TrabalhadorEducando
            f) PessoaFisica
        """
        try:
            if self.eh_servidor:
                return self.funcionario.servidor

            if self.eh_prestador:
                return self.funcionario.prestadorservico

            if self.eh_aluno:
                return self.aluno_edu_set.all()[0]

            if self.eh_residente:
                return self.residente_set.all()[0]

            if self.eh_trabalhadoreducando:
                return self.trabalhadoreducando_set.all()[0]
        except Exception:
            pass

        return self

    def get_vinculo(self):
        if self.eh_servidor or self.eh_prestador:
            return self.funcionario.get_vinculo()
        elif self.eh_aluno:
            return self.aluno_edu_set.all()[0].get_vinculo()
        elif self.eh_residente:
            return self.residente_set.all()[0].get_vinculo()
        elif self.eh_trabalhadoreducando:
            return self.trabalhadoreducando_set.all()[0].get_vinculo()
        elif self.user and self.user.get_vinculo():
            return self.user.get_vinculo()

    @property
    def banco_display(self):
        return f"{self.pagto_banco}, AG: {self.pagto_agencia}, CC: {self.pagto_ccor}"

    @property
    def ctps_display(self):
        return "Número: {}, UF: {}, Prim.Emprego: {}, Série: {}".format(
            self.ctps_numero or "",
            self.ctps_uf or "",
            self.ctps_data_prim_emprego and self.ctps_data_prim_emprego.strftime("%d/%m/%Y") or "",
            self.ctps_serie or "",
        )

    @property
    def cnh_display(self):
        return "Cart: {}, Reg: {}, Categ: {}, Emissão: {}, UF: {}, Validade: {}".format(
            self.cnh_carteira or "",
            self.cnh_registro or "",
            self.cnh_categoria or "",
            self.cnh_emissao or "",
            self.cnh_uf or "",
            self.cnh_validade or "",
        )

    @property
    def rg_display(self):
        return "{} - {}/{} - {}".format(
            self.rg, self.rg_orgao or "", self.rg_uf or "", self.rg_data and self.rg_data.strftime("%d/%m/%Y") or ""
        )

    @property
    def titulo_eleitoral_display(self):
        return "Número: {}, Zona: {}, Seção: {}, UF: {}, Emissão: {}".format(
            self.titulo_numero or "",
            self.titulo_zona or "",
            self.titulo_secao or "",
            self.titulo_uf or "",
            self.titulo_data_emissao and self.titulo_data_emissao.strftime("%d/%m/%Y") or "",
        )

    def pode_gerar_cracha(self):
        DocumentoControleTipo = apps.get_model("comum", "DocumentoControleTipo")
        try:
            cracha = DocumentoControleTipo.objects.get(identificador=DocumentoControleTipo.CRACHA)
            if (
                self.situacao
                and not self.data_obito
                and all([self.grupo_sanguineo, self.fator_rh, self.nome_usual, self.foto])
                and (self.situacao.codigo,) in cracha.abrangencia.values_list("codigo")
            ):
                return True
            return False
        except Exception:
            return False

    @property
    def idade(self):
        if self.nascimento_data:
            return get_age(self.nascimento_data)
        return "-"

    def tem_digital(self):
        return bool(self.get_template())

    def outra_pessoa_fisica_mesmo_cpf_tem_digital(self):
        pessoas_fisicas = PessoaFisica.objects.filter(cpf=self.cpf, template__isnull=False).exclude(id=self.id)
        return pessoas_fisicas.exists()

    def get_digital_outra_pessoa_fisica_mesmo_cpf(self):
        if self.outra_pessoa_fisica_mesmo_cpf_tem_digital():
            pessoas_fisicas = PessoaFisica.objects.filter(cpf=self.cpf, template__isnull=False).exclude(id=self.id)
            if pessoas_fisicas.exists():
                return pessoas_fisicas[0].get_template()

    def pode_reaproveitar_digital(self):
        if self.outra_pessoa_fisica_mesmo_cpf_tem_digital() and not self.tem_digital():
            return True
        return False

    def get_atendimento_enf_aberto(self):
        if "saude" in settings.INSTALLED_APPS:
            from saude.models import Atendimento, SituacaoAtendimento, TipoAtendimento

            if Atendimento.objects.filter(
                tipo=TipoAtendimento.ENFERMAGEM_MEDICO, prontuario__vinculo__user=self.user, situacao=SituacaoAtendimento.ABERTO
            ).exists():
                return Atendimento.objects.filter(
                    tipo=TipoAtendimento.ENFERMAGEM_MEDICO, prontuario__vinculo__user=self.user, situacao=SituacaoAtendimento.ABERTO
                )[0].id
        return None

    def get_atendimento_odonto_aberto(self):
        if "saude" in settings.INSTALLED_APPS:
            from saude.models import Atendimento, SituacaoAtendimento, TipoAtendimento

            if Atendimento.objects.filter(
                tipo=TipoAtendimento.ODONTOLOGICO, prontuario__vinculo__user=self.user, situacao=SituacaoAtendimento.ABERTO
            ).exists():
                return Atendimento.objects.filter(
                    tipo=TipoAtendimento.ODONTOLOGICO, prontuario__vinculo__user=self.user, situacao=SituacaoAtendimento.ABERTO
                )[0]
        return None

    @property
    def emails(self):
        lista = []
        if self.email:
            lista.append(self.email)
        if self.user and self.user.email:
            lista.append(self.user.email)
        if self.email_secundario:
            lista.append(self.email_secundario)
        return " - ".join(lista)

    @property
    def primeiro_ultimo_nome(self):
        nomes = self.nome.split(" ")
        return nomes[0], nomes[-1]

    @property
    def tipo_sanguineo(self):
        return f"{self.get_grupo_sanguineo_display()}{self.get_fator_rh_display()}"

    def get_cpf_ou_passaporte(self):
        if self.nacionalidade and int(self.nacionalidade) == Nacionalidade.ESTRANGEIRO and not self.cpf:
            return self.passaporte
        else:
            return self.cpf

    def projetos_extensao(self):
        if 'projetos' in settings.INSTALLED_APPS:
            ParticipacaoExtensao = apps.get_model('projetos', 'Participacao')
            return ParticipacaoExtensao.objects.filter(vinculo_pessoa__pessoa_id=self.id)
        else:
            return None

    def is_user(self, request):
        return request.user.id and request.user.id == self.user_id

    def get_dados_bancarios(self):
        qs = self.dadosbancariospessoafisica_set.all()
        return qs

    def get_dados_bancarios_folha_pagamento(self):
        if self.get_dados_bancarios():
            return self.get_dados_bancarios().order_by('-prioritario_servico_social')[0]
        return False

    def get_dados_bancarios_banco(self):
        if self.get_dados_bancarios_folha_pagamento():
            banco = self.get_dados_bancarios_folha_pagamento().banco
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


class FuncionariosDoMeuSetorManager(models.Manager):
    def get_queryset(self):
        setor = get_setor()
        return super().get_queryset().filter(setor__id__in=setor.ids_descendentes)


class FuncionariosDoMeuCampusManager(models.Manager):
    def get_queryset(self):
        uo = get_uo()
        return super().get_queryset().filter(setor__uo=uo)


class Funcionario(PessoaFisica):
    SEARCH_FIELDS = ["nome", "cpf", "username"]
    setor = models.ForeignKeyPlus(
        "rh.Setor",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="funcionarios",
        verbose_name="Setor SUAP",
        help_text="Este setor poderá ser modificado manualmente pelos responsáveis pelo RH",
    )
    setor_funcao = models.ForeignKeyPlus(
        "rh.Setor",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="funcionarios_com_funcao",
        verbose_name="Setor da Função SIAPE",
    )
    setor_lotacao = models.ForeignKeyPlus(
        "rh.Setor",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="funcionarios_lotados",
        verbose_name="Setor de Lotação SIAPE",
    )

    objects = models.Manager()
    do_meu_setor = FuncionariosDoMeuSetorManager()
    do_meu_campus = FuncionariosDoMeuCampusManager()

    class Meta:
        db_table = "suap_funcionario"
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"

    def __str__(self):
        return f"{self.nome} ({self.username})"

    def get_vinculo(self):
        if hasattr(self, "prestadorservico"):
            return self.prestadorservico.get_vinculo()
        else:
            return self.servidor.get_vinculo()

    @property
    def campus(self):
        return self.setor and self.setor.uo or None

    def eh_chefe_do_setor_hoje(self, setor):
        hoje = datetime.datetime.today()
        historico_funcao = self.historico_funcao(hoje, hoje).filter(
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia(), setor_suap__isnull=False
        )

        if historico_funcao.exists():
            for funcao_setor in historico_funcao:
                if setor in funcao_setor.setor_suap.descendentes:
                    return True
        return False

    def eh_chefe_de(self, servidor):
        return False

    def eh_do_meu_setor(self, funcionario, incluir_subsetores=True):
        if incluir_subsetores:
            return funcionario.setor in self.setor.descendentes
        else:
            return self.setor == funcionario.setor

    def eh_do_meu_campus(self, funcionario):
        if self.setor and funcionario.setor:
            return self.setor.uo == funcionario.setor.uo
        return False

    def get_ext_combo_template(self):
        if hasattr(self, "servidor"):
            return self.servidor.get_ext_combo_template()
        elif hasattr(self, "prestadorservico"):
            return self.prestadorservico.get_ext_combo_template()
        else:
            out = [f'<dt class="sr-only">Nome</dt><dd><strong>{self.nome}</strong></dd>']
            out.append('<dt class="sr-only">Categoria</dt><dd>Funcionário</dd>')
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

    def get_setores_por_periodo(self, data_inicial, data_final):
        pass

    #
    # jornada de trabalho do funcionario em uma determinada data
    #
    def jornada_trabalho_por_periodo_dict(self, setor, data_inicio, data_fim):
        jornadas = dict()
        if self.eh_servidor:
            qs_1 = CargaHorariaReduzida.objects.filter(servidor=self, data_inicio__lte=data_fim, data_termino__gte=data_inicio)
            qs_2 = CargaHorariaReduzida.objects.filter(servidor=self, data_inicio__lte=data_fim, data_termino__isnull=True)
            qs = (qs_1 | qs_2).distinct()
            jornadas = dict()
            for jornada_historico in qs:
                data_inicio_jornada = jornada_historico.data_inicio
                data_fim_jornada = jornada_historico.data_termino
                if data_inicio_jornada <= data_inicio:
                    data_inicio_jornada = data_inicio
                if not data_fim_jornada or data_fim_jornada >= data_fim:
                    data_fim_jornada = data_fim
                for dia in datas_entre(data_inicio_jornada, data_fim_jornada):
                    jornadas[dia] = jornada_historico.nova_jornada

        return jornadas

    def chefes_na_data(self, data, considerar_setor_no_qual_tem_funcao=False, chefes_setor_lotacao=False):
        """
        Chefe(s) do Funcionário em uma determinada data.
            - No escopo do Setor atual (default)
            - No escopo do Setor Superior em relação ao Setor no qual o funcionário está com funcão

        1) se sou o reitor, eu mando em mim
        2) não sou o reitor, então os chefes do meu setor são os meus chefes
            - se eu for um dos chefes
                - eu não posso mandar em mim
                - os demais chefes que são "substituição de chefia" também não podem mandar em mim
        3) ainda não há chefes? então, procura nos setores superiores recursivamente até achar (ou não!)
        """
        chefes_na_data = Funcionario.objects.none()
        setores_na_data = []
        meu_setor = self.setor_na_data(data, chefes_setor_lotacao)
        if meu_setor:
            if settings.TIPO_ARVORE_SETORES == 'SUAP' and chefes_setor_lotacao:
                # verificando se existe a equivalência a nível de setor... se existir é só selecionar o setor suap diretamente
                setor_check_codigo = Setor.suap.filter(equivalencia_codigo=meu_setor.codigo).first()
                if setor_check_codigo:
                    meu_setor = setor_check_codigo
                else:
                    # selecionando o setor suap equivalente ao setor siape de lotação
                    meu_setor_suap = Setor.suap.filter(sigla=meu_setor).first()
                    # verificando se os setores são os mesmos pela equivalência da UO
                    if meu_setor_suap and meu_setor.uo.equivalente == meu_setor_suap.uo:
                        # a variável meu_setor passa a ser o setor suap de lotação
                        # essa troca é necessária, pois a chefia acontece nos setores suap
                        meu_setor = meu_setor_suap

            setores_na_data.append(meu_setor)

        if considerar_setor_no_qual_tem_funcao:
            minhas_funcoes_na_data = self.servidor.historico_funcao(data, data)
            for funcao in minhas_funcoes_na_data:
                if funcao.setor_suap:
                    setor_superior = funcao.setor_suap.superior
                    if setor_superior:
                        setores_na_data.append(setor_superior)

        if setores_na_data:
            sou_o_reitor = self.eh_servidor and self.servidor.eh_reitor(data)

            if sou_o_reitor:
                chefes_na_data = Funcionario.objects.filter(id=self.id)
            else:
                historico_funcao_do_setor = ServidorFuncaoHistorico.objects.none()

                for setor_na_data in setores_na_data:
                    historico_funcao_do_setor_atual = setor_na_data.historico_funcao(data, data)

                    sou_um_dos_chefes = historico_funcao_do_setor_atual.filter(servidor__id=self.id).exists()

                    if sou_um_dos_chefes:
                        # não posso me mandar !!!
                        historico_funcao_do_setor_atual = historico_funcao_do_setor_atual.exclude(servidor__id=self.id)

                        if historico_funcao_do_setor_atual.exists():
                            # retirar quem for "substituicao de chefia"
                            historico_funcao_do_setor_atual = historico_funcao_do_setor_atual.exclude(funcao__codigo=Funcao.get_sigla_substituicao_chefia())

                    if not historico_funcao_do_setor_atual.exists():
                        # "sobe" na árvore dos setores
                        setor_superior = setor_na_data.superior
                        while setor_superior and not historico_funcao_do_setor_atual.exists():
                            historico_funcao_do_setor_atual = setor_superior.historico_funcao(data, data)
                            setor_superior = setor_superior.superior

                    historico_funcao_do_setor = historico_funcao_do_setor | historico_funcao_do_setor_atual

                if historico_funcao_do_setor.exists():
                    chefes_na_data = Funcionario.objects.filter(id__in=historico_funcao_do_setor.values_list("servidor__id", flat=True))

        return chefes_na_data

    def chefes_imediatos(self):
        if self.setor:
            setor = self.setor

            if self.eh_chefe_do_setor_hoje(self.setor):
                if self.setor.superior:
                    setor = self.setor.superior

            while not setor.historico_funcao().exists() and setor.superior:
                setor = setor.superior

            return Servidor.objects.filter(pk__in=setor.historico_funcao().values_list("servidor_id", flat=True))
        return Funcionario.objects.none()

    def setor_na_data(self, data, chefes_setor_lotacao=False):
        """
        Setor do Funcionário em uma determinada data.
        """
        historico = None
        if chefes_setor_lotacao:
            historico = ServidorSetorLotacaoHistorico.objects.filter(servidor=self).filter(
                Q(data_inicio_setor_lotacao__lte=data), Q(data_fim_setor_lotacao__gte=data) | Q(data_fim_setor_lotacao__isnull=True)
            )
            if historico.exists():
                return historico[0].setor_lotacao
        else:
            historico = ServidorSetorHistorico.objects.filter(servidor=self).filter(
                Q(data_inicio_no_setor__lte=data), Q(data_fim_no_setor__gte=data) | Q(data_fim_no_setor__isnull=True)
            )

            if historico.exists():
                return historico[0].setor

        return None


class Servidor(Funcionario):
    SEARCH_FIELDS = ["nome", "matricula", "cpf", "username"]

    matricula = models.CharField("Matrícula", max_length=20, unique=True, db_index=True)
    pessoa_fisica = models.ForeignKeyPlus("rh.PessoaFisica", db_index=True, null=False, blank=False, related_name="servidores", default=1)
    matricula_crh = models.CharField("Matrícula CRH", max_length=20, db_index=True)  # é o mesmo dado de rh.PCA.codigo_crh_pca
    matricula_sipe = models.CharField("Matrícula SIPE", max_length=20, db_index=True)
    matricula_anterior = models.CharField("Matrícula Anterior", max_length=20, null=True, blank=True)
    qtde_depend_ir = models.IntegerField(null=True, blank=True)
    nivel_padrao = models.CharField(max_length=4, null=True, blank=True)
    opera_raio_x = models.BooleanField(default=False)
    num_processo_aposentadoria = models.CharField(max_length=30, null=True, blank=True)
    numerador_prop_aposentadoria = models.CharField(max_length=20, null=True, blank=True)
    denominador_prop_aposentadoria = models.CharField(max_length=20, null=True, blank=True)
    data_cadastro_siape = models.DateField(null=True, blank=True)

    data_inicio_servico_publico = models.DateField(null=True, blank=True)
    data_inicio_exercicio_na_instituicao = models.DateField(null=True, blank=True)
    data_posse_na_instituicao = models.DateField(null=True, blank=True)
    data_posse_no_cargo = models.DateField(null=True, blank=True)
    data_inicio_exercicio_no_cargo = models.DateField(null=True, blank=True)

    data_fim_servico_na_instituicao = models.DateField(null=True, blank=True)

    # O campo excluido é definido pelo método rh.ServidorOcorrencia.save

    # email extraido do SIAPE
    email_siape = models.EmailField(blank=True, verbose_name="Email SIAPE")
    # Modelagem nova para email
    email_institucional = models.EmailField("Email Institucional", blank=True)
    email_academico = models.EmailField("Email Acadêmico", blank=True)
    email_google_classroom = models.EmailField("Email do Google Classroom", blank=True)

    alterado_em = models.DateTimeField(auto_now=True)

    identificacao_unica_siape = models.CharField(max_length=20, null=True, blank=True, default="Novo")

    codigo_vaga = models.CharField(max_length=7, null=True, blank=True)  # é o mesmo dado de rh.PCA.codigo_vaga_siape_pca

    cargo_classe = models.ForeignKeyPlus("rh.CargoClasse", null=True, blank=True, on_delete=models.CASCADE)
    cargo_emprego = models.ForeignKeyPlus("rh.CargoEmprego", null=True, blank=True, on_delete=models.CASCADE)
    cargo_emprego_area = models.ForeignKeyPlus(
        "rh.CargoEmpregoArea", verbose_name="Área do Cargo Emprego", null=True, blank=True, on_delete=models.CASCADE
    )

    cargo_emprego_data_ocupacao = models.DateField(null=True, blank=True)
    cargo_emprego_data_saida = models.DateField(null=True, blank=True)
    situacao = models.ForeignKeyPlus("rh.Situacao", null=False, verbose_name="Situação", on_delete=models.CASCADE)
    jornada_trabalho = models.ForeignKeyPlus("rh.JornadaTrabalho", null=True, blank=True, on_delete=models.CASCADE)
    # TODO: Verificar para poder retirar
    funcao = models.ForeignKeyPlus("rh.Funcao", null=True, blank=True, on_delete=models.CASCADE)
    funcao_atividade = models.ForeignKeyPlus("rh.Atividade", null=True, blank=True, on_delete=models.CASCADE)
    funcao_opcao = models.BooleanField(null=True)
    funcao_codigo = models.CharField(max_length=20, null=True, blank=True)
    funcao_data_ocupacao = models.DateField(null=True, blank=True)
    funcao_data_saida = models.DateField(null=True, blank=True)
    regime_juridico = models.ForeignKeyPlus("rh.RegimeJuridico", null=True, blank=True, on_delete=models.CASCADE)
    nivel_escolaridade = models.ForeignKeyPlus("rh.NivelEscolaridade", null=True, blank=True, on_delete=models.CASCADE)
    setor_lotacao_data_ocupacao = models.DateField(null=True)
    data_exclusao_instituidor = models.DateField(null=True, blank=True)
    titulacao = models.ForeignKeyPlus("rh.Titulacao", null=True, blank=True, on_delete=models.CASCADE)
    setor_exercicio = models.ForeignKeyPlus(
        "rh.Setor",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="servidores_exercicio",
        verbose_name="Setor de Exercício SIAPE",
    )
    areas_de_conhecimento = models.ManyToManyFieldPlus("rh.AreaConhecimento", blank=True)

    eh_docente = models.BooleanField(null=True)
    eh_tecnico_administrativo = models.BooleanField(null=True)
    vinculos = GenericRelation(
        "comum.Vinculo", related_query_name="servidores", object_id_field="id_relacionamento", content_type_field="tipo_relacionamento"
    )

    data_ultima_atualizacao_webservice = models.DateTimeField(null=True, blank=True)

    # Managers
    objects = ServidorQueryset.as_manager()

    numero_registro = models.CharFieldPlus('Número de Registro no Conselho Profissional', null=True,
                                           blank=True)

    class Meta:
        db_table = "servidor"
        verbose_name = "Servidor"
        verbose_name_plural = "Servidores"

        permissions = (
            ("pode_ver_relatorios_rh", "Pode ver relatórios do RH"),
            ("chefe", "Chefe"),
            ("gabinete", "Gabinete"),
            ("auditor", "Auditor"),
            ("eh_servidor", "Servidor"),
            ("eh_rh_sistemico", "RH Sistêmico"),
            ("eh_rh_campus", "RH Campus"),
            ("cadastrador_rsc_simec", "Cadastrador RSC/SIMEC"),
            ("pode_ver_cpf_servidor", "Pode ver CPF"),
            ("pode_ver_dados_pessoais_servidor", "Pode ver dados pessoais de servidores"),
            ("pode_ver_telefones_pessoais_servidor", "Pode ver telefones pessoais de servidores"),
            ("pode_ver_endereco_servidor", "Pode visualizar endereço de servidores"),
            ("pode_ver_dados_bancarios_servidor", "Pode visualizar dados bancários de servidores"),
            ("pode_ver_dados_professor_servidor", "Pode visualizar dados de professor de servidores"),
            ("pode_ver_ferias_servidor", "Pode visualizar Férias dos servidores"),
            ("pode_ver_ocorrencias_afastamentos_servidor", "Pode visualizar Ocorrências e Afastamentos dos Servidores"),
            ("pode_ver_historico_setores_servidor", "Pode visualizar historico de setor dos Servidores"),
            ("pode_ver_historico_funcional_servidor", "Pode visualizar historico funcional dos Servidores"),
            ("pode_ver_historico_funcao_servidor", "Pode visualizar historico de funções dos Servidores"),
            ("pode_ver_arquivos_servidor", "Pode visualizar arquivos dos Servidores"),
            ("pode_ver_contracheques_servidor", "Pode visualizar contracheques dos Servidores"),
            ("pode_ver_viagens_servidor", "Pode visualizar viagens dos Servidores"),
            ("pode_editar_cargo_emprego_externo", "Pode editar cargo emprego de servidor fora do PCCTAE"),
            ("pode_ver_identificacao_unica_siape", "Pode visualizar Identificação Única SIAPE"),
            ("pode_importar_servidor_ws", "Pode importar servidor via Webservice"),
            ("pode_gerenciar_extracao_scdp", "Pode gerenciar extração SCDP"),
            ("pode_gerenciar_extracao_siape", "Pode gerenciar extração SIAPE"),
        )

    def __str__(self):
        return f"{self.nome} ({self.matricula})"

    def get_absolute_url(self):
        return f"/rh/servidor/{self.matricula}/"

    def save(self, *args, **kwargs):
        from comum.models import Vinculo

        self.eh_servidor = True

        def campus_siape_igual_campus_suap(setor_a, setor_b):
            return setor_a and setor_b and setor_b.uo and setor_b.uo.equivalente and setor_b.uo.equivalente == setor_a.uo

        # A restrição só será feita se o servidor tiver setor de exercício SIAPE
        # e não for estagiário.
        if self.setor_exercicio and not self.eh_estagiario:
            Configuracao = apps.get_model("comum", "configuracao")
            if Configuracao.get_valor_por_chave(app="comum", chave="setores") == "SUAP":
                if not campus_siape_igual_campus_suap(self.setor, self.setor_exercicio):
                    if self.setor and self.setor.uo:
                        from chaves.models import Chave

                        chaves = Chave.objects.filter(pessoas=self, sala__predio__uo=self.setor.uo)
                        for chave in chaves:
                            chave.pessoas.remove(self)
                        self.setor = None

            else:
                self.setor = self.setor_exercicio

        # Seta se o servidor é tec. administrativo ou docente
        nao_tem_categoria = not self.eh_docente and not self.eh_tecnico_administrativo
        if nao_tem_categoria and self.cargo_emprego and self.cargo_emprego.grupo_cargo_emprego.categoria == "docente":
            self.eh_docente = True

        if (
                nao_tem_categoria
                and not self.eh_tecnico_administrativo
                and self.cargo_emprego
                and self.cargo_emprego.grupo_cargo_emprego.categoria == "tecnico_administrativo"
        ):
            self.eh_tecnico_administrativo = True

        if self.pk:
            servidor_anterior = Servidor.objects.get(pk=self.pk)
            historico_setores_servidor = ServidorSetorHistorico.objects.filter(servidor=self)
            if self.setor:
                if not historico_setores_servidor.exists():
                    #
                    # não tem histórico SUAP
                    if self.data_cadastro_siape:
                        ServidorSetorHistorico.objects.create(
                            servidor=self, setor=self.setor, data_inicio_no_setor=self.data_cadastro_siape
                        )
                    else:
                        ServidorSetorHistorico.objects.create(servidor=self, setor=self.setor,
                                                              data_inicio_no_setor=datetime.date.today())
                else:
                    if servidor_anterior.setor != self.setor:
                        historico_setor_data_inicio_hoje = historico_setores_servidor.filter(
                            data_inicio_no_setor=datetime.date.today())
                        if historico_setor_data_inicio_hoje.exists():
                            historico_atualizar = historico_setor_data_inicio_hoje[0]
                            historico_atualizar.setor = self.setor
                            historico_atualizar.save()
                        else:
                            """
                            o último histórico SUAP deve ser resolvido:
                                Se não há último histórico SIAPE:
                                    Cria-se um novo histórico SUAP:
                                        data inicial = hoje
                                        data final = nenhuma
                                Senão
                                    Se data inicial >= data inicial do último histórico SIAPE
                                        O último histórico SUAP já refere-se ao último histórico SIAPE.
                                        Atualiza o último histórico SUAP:
                                            setor = setor informado pelo RH
                                            data final = data final do último histórico SIAPE
                                    Senão (situação NORMAL)
                                        Conclui o último histórico SUAP:
                                            data final = data inicial do atual histórico SIAPE - 1 dia
                                        Cria-se um novo histórico SUAP:
                                            data inicial = data inicial do último histórico SIAPE
                                            data final = nenhuma
                            """
                            historico_siape = self.historico_setor_siape()
                            ultimo_historico_siape = None
                            if historico_siape.exists():
                                ultimo_historico_siape = historico_siape.order_by("-data_inicio_setor_lotacao")[0]
                            if not ultimo_historico_siape:
                                #
                                # cria novo histórico suap a partir de HOJE
                                ServidorSetorHistorico.objects.create(
                                    servidor=self, setor=self.setor, data_inicio_no_setor=datetime.date.today()
                                )
                            else:
                                ultimo_historico_suap = ServidorSetorHistorico.objects.filter(servidor=self).order_by(
                                    "-data_inicio_no_setor"
                                )[0]
                                #
                                data_inicial_ultimo_historico_suap = ultimo_historico_suap.data_inicio_no_setor
                                data_inicial_ultimo_historico_siape = ultimo_historico_siape.data_inicio_setor_lotacao
                                data_final_ultimo_historico_siape = ultimo_historico_siape.data_fim_setor_lotacao
                                #
                                if data_inicial_ultimo_historico_suap >= data_inicial_ultimo_historico_siape:
                                    #
                                    # situação ANORMAL
                                    # atualiza o último histórico suap no dia
                                    ultimo_historico_suap.setor = self.setor
                                    ultimo_historico_suap.data_fim_no_setor = data_final_ultimo_historico_siape
                                    ultimo_historico_suap.save()
                                else:
                                    #
                                    # situação NORMAL
                                    # finaliza o último histórico suap no dia
                                    # anterior ao primeiro dia do último histórico siape
                                    ultimo_historico_suap.data_fim_no_setor = data_inicial_ultimo_historico_siape - datetime.timedelta(
                                        days=1
                                    )
                                    ultimo_historico_suap.save()
                                    #
                                    # cria novo histórico suap
                                    ServidorSetorHistorico.objects.create(
                                        servidor=self, setor=self.setor,
                                        data_inicio_no_setor=data_inicial_ultimo_historico_siape
                                    )

            self.pessoa_fisica = self.pessoafisica_ptr
            self.username = self.cpf.replace(".", "").replace("-", "")
            servidor = super().save(*args, **kwargs)
        else:
            self.username = self.cpf.replace(".", "").replace("-", "")
            servidor = super().save(*args, **kwargs)
            if self.setor:
                if self.data_cadastro_siape:
                    ServidorSetorHistorico.objects.create(servidor=self, setor=self.setor,
                                                          data_inicio_no_setor=self.data_cadastro_siape)
                else:
                    ServidorSetorHistorico.objects.create(servidor=self, setor=self.setor,
                                                          data_inicio_no_setor=datetime.date.today())

        user = self.get_user()
        qs = Vinculo.objects.filter(servidores=self)
        if not qs.exists():
            vinculo = Vinculo()
        else:
            vinculo = qs.first()
        vinculo.pessoa = self.pessoa_ptr
        vinculo.user = user
        vinculo.relacionamento = self
        vinculo.setor = self.setor
        vinculo.save()

        cache.delete(f'servidor_tem_setor_middleware_{self.matricula}')
        Servidor.objects.filter(pk=self.pk).update(pessoa_fisica=self.pk)
        return servidor
    
    def estah_afastado_ou_de_ferias_ateh(self, dia):
        retorno = []
        if "ferias" in settings.INSTALLED_APPS:
            from ferias.models import ParcelaFerias

            parcela = ParcelaFerias.objects.filter(ferias__servidor=self, data_inicio__lte=dia, data_fim__gte=dia).first()
            if parcela:
                retorno.append(f"De férias até {parcela.data_fim.strftime('%d/%m/%Y')}")

        afastamento = ServidorAfastamento.objects.filter(
            servidor=self, data_inicio__lte=dia, data_termino__gte=dia, cancelado=False
        ).first()
        if afastamento:
            retorno.append(f"Afastado até {afastamento.data_termino.strftime('%d/%m/%Y')}")
        return ", ".join(retorno)

    def get_titulacao(self):
        if self.titulacao:
            if self.sexo == "M":
                return self.titulacao.titulo_masculino or self.titulacao.nome
            else:
                return self.titulacao.titulo_feminino or self.titulacao.nome
        return None

    @classmethod
    def get_by_cpf_ou_matricula(cls, cpf_ou_matricula):
        if cpf_valido(cpf_ou_matricula):
            # Buscar por CPF
            res = cls.objects.filter(pessoa_fisica__cpf=mask_numbers(cpf_ou_matricula)) | cls.objects.filter(
                pessoa_fisica__cpf=mask_cpf(cpf_ou_matricula)
            )
            if not res:
                return None
            elif len(res) == 1:
                return res[0]
            elif len(res) > 1:
                # Existem pelo menos 2 pessoas físicas com o mesmo CPF,
                # provavelmente são servidores e apenas um está ativo.
                try:
                    return Servidor.objects.get(pk__in=res.values_list("pk", flat=True), excluido=False)
                except (Servidor.DoesNotExist, Servidor.MultipleObjectsReturned):
                    return res.latest("id")
        else:
            # Buscar por matrícula
            try:
                return Servidor.objects.get(matricula=cpf_ou_matricula)
            except Servidor.DoesNotExist:
                return None

    def get_vinculo(self):
        return self.vinculo_set.first()

    def get_user(self):
        from comum.models import User

        qs = User.objects.filter(username=self.cpf.replace('.', '').replace('-', ''))
        return qs.exists() and qs[0] or None

    @staticmethod
    def quadro_referencia_administrativos():
        """Total por nível (A, B, C, D e E) e total geral por campus de lotação SIAPE considerando apenas
        ativos permanentes e cedidos.
        """
        Situacao = apps.get_model("rh", "Situacao")
        quadro_tecnicos = (
            Servidor.objects.filter(
                excluido=False,
                eh_tecnico_administrativo=True,
                cargo_classe__codigo__in=("A", "B", "C", "D", "E"),
                sistema_origem__exact="SIAPE",
                situacao__codigo__in=Situacao.SITUACOES_EFETIVOS,
            )
            .values("setor_lotacao__uo__id", "setor_lotacao__uo__sigla", "cargo_classe__codigo")
            .order_by("setor_lotacao__uo__sigla")
        )

        quadro_final = OrderedDict()
        for s in quadro_tecnicos:
            campus_id = s["setor_lotacao__uo__id"]
            campus_sigla = s["setor_lotacao__uo__sigla"]
            cargo_classe = s["cargo_classe__codigo"]

            if campus_id not in quadro_final:
                quadro_final[campus_id] = dict(sigla=campus_sigla, A=0, B=0, C=0, D=0, E=0, total=0)

            quadro_final[campus_id][cargo_classe] += 1
            quadro_final[campus_id]["total"] += 1
        # ----
        return quadro_final

    @staticmethod
    def quadro_referencia_docentes():
        """Total de docentes por Jornada de Trabalho"""
        Situacao = apps.get_model("rh", "Situacao")
        # ------
        quadro_docentes = (
            Servidor.objects.filter(
                excluido=False,
                eh_docente=True,
                sistema_origem__exact="SIAPE",
                situacao__codigo__in=Situacao.SITUACOES_EFETIVOS_E_TEMPORARIOS,
            )
            .values(
                "setor_lotacao__uo__id",
                "setor_lotacao__uo__sigla",
                "jornada_trabalho__codigo",
                "situacao__codigo",
                "jornada_trabalho__docente_peso",
            )
            .order_by("setor_lotacao__uo__sigla")
        )

        quadro_final = OrderedDict()
        quadro_total = {
            "20": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
            "40": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
            "99": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
            "TT": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
            "NA": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
        }

        for s in quadro_docentes:
            campus_id = s["setor_lotacao__uo__id"]
            campus_sigla = s["setor_lotacao__uo__sigla"] or "Sem Campus"
            jornada_codigo = s["jornada_trabalho__codigo"] or "NA"
            situacao_codigo = s["situacao__codigo"]
            jornada_peso = s["jornada_trabalho__docente_peso"] or 0

            if campus_id not in quadro_final:
                quadro_final[campus_id] = {
                    "sigla": campus_sigla,
                    "20": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
                    "40": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
                    "99": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
                    "TT": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
                    "NA": {"qtd_efetivos": 0, "peso_efetivos": 0, "qtd_temporarios": 0, "peso_temporarios": 0},
                }

            descricao_vinculo = "efetivos"
            if not situacao_codigo in Situacao.SITUACOES_EFETIVOS:
                descricao_vinculo = "temporarios"
            quadro_final[campus_id][jornada_codigo]["qtd_" + descricao_vinculo] += 1
            quadro_final[campus_id][jornada_codigo]["peso_" + descricao_vinculo] += jornada_peso
            quadro_final[campus_id]["TT"]["qtd_" + descricao_vinculo] += 1
            quadro_final[campus_id]["TT"]["peso_" + descricao_vinculo] += jornada_peso

            quadro_total[jornada_codigo]["qtd_" + descricao_vinculo] += 1
            quadro_total[jornada_codigo]["peso_" + descricao_vinculo] += jornada_peso
            quadro_total["TT"]["qtd_" + descricao_vinculo] += 1
            quadro_total["TT"]["peso_" + descricao_vinculo] += jornada_peso
        # ------
        return (quadro_final, quadro_total)

    def pode_gerar_carteira_funcional(self):
        """
        Define se pode ser gerada carteira funcional para o servidor em questão.
        Atualmente geramos carteira funcionais para Ativos Permamentes e Aposentados vivos
        """
        DocumentoControleTipo = apps.get_model("comum", "DocumentoControleTipo")
        try:
            carteira = DocumentoControleTipo.objects.get(pk=DocumentoControleTipo.CARTEIRA_FUNCIONAL)
            if (
                self.situacao
                and not self.data_obito
                and all(
                    [
                        self.nome,
                        self.grupo_sanguineo,
                        self.fator_rh,
                        self.nome_mae,
                        self.rg,
                        self.rg_orgao,
                        self.nascimento_municipio,
                        self.cpf,
                        self.nascimento_data,
                        self.foto,
                        self.cargo_emprego,
                    ]
                )
                and (self.situacao.codigo,) in carteira.abrangencia.values_list("codigo")
            ):
                return True
            return False
        except Exception:
            return False

    def get_ext_combo_template(self):
        out = [f'<dt class="sr-only">Nome</dt><dd><strong>{self.nome}</strong> (Mat. {self.matricula})</dd>']
        if self.setor:
            out.append(f'<dt class="sr-only">Setor</dt><dd>{self.setor.get_caminho_as_html()}</dd>')
        if self.cargo_emprego:
            out.append(f'<dt class="sr-only">Cargo</dt><dd>{self.cargo_emprego}</dd>')
        template = '''<div class="person">
            <div class="photo-circle">
                <img src="{}" alt="Foto de {}" />
            </div>
            <dl>{}</dl>
        </div>
        '''.format(
            self.get_foto_75x100_url(), self.nome, "".join(out)
        )
        return template

    def tem_acesso_servicos_microsoft(self):
        if self.cargo_emprego and not self.eh_aposentado:
            return ".edu.br" in self.email and (self.eh_docente or in_group(self.user, "Usuário do Microsoft Imagine"))

    def eh_chefe_dos_setores_hoje(self):
        if self.setor:
            setores_id_que_eh_chefe_hoje = list()
            hoje = datetime.datetime.today()
            historico_funcao = self.historico_funcao(hoje, hoje).filter(
                funcao__codigo__in=Funcao.get_codigos_funcao_chefia(), setor_suap__isnull=False
            )

            if historico_funcao.exists():
                for funcao_setor in historico_funcao:
                    for setor in funcao_setor.setor_suap.descendentes:
                        setores_id_que_eh_chefe_hoje.append(setor.id)
                if setores_id_que_eh_chefe_hoje:
                    return Setor.objects.filter(pk__in=setores_id_que_eh_chefe_hoje)
                return None
        else:
            return None

    def eh_chefe_de(self, servidor):
        if servidor.setor and self.setor:
            return self.eh_chefe_do_setor_hoje(servidor.setor)
        return False

    def eh_chefe_do_setor_hoje(self, setor):
        hoje = datetime.datetime.today()
        historico_funcao = self.historico_funcao(hoje, hoje).filter(
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia(), setor_suap__isnull=False
        )

        if historico_funcao.exists():
            for funcao_setor in historico_funcao:
                if setor in funcao_setor.setor_suap.descendentes:
                    return True
        return False

    def eh_chefe_do_setor_periodo(self, setor, data_ini, data_fim):
        historico_funcao = self.historico_funcao(data_ini, data_fim).filter(
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia(), setor_suap__isnull=False
        )
        if historico_funcao.exists():
            for funcao_setor in historico_funcao:
                if setor in funcao_setor.setor_suap.descendentes:
                    return True
        return False

    def get_funcoes_no_periodo(self, data_ini, data_fim):
        """
        funcoes_por_dia = {
            dia1: funcao,
            ...
            diaN: funcao,
            diaN: funcao,
            ...
            diaN: funcao
        }

        funcao é uma instância de rh.ServidorFuncaoHistorico
        """
        historico_funcao = self.historico_funcao(data_ini, data_fim).filter(
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia(), setor_suap__isnull=False
        )

        funcoes_por_dia = {}

        if historico_funcao.exists():
            for funcao in historico_funcao:
                for dia in datas_entre(funcao.data_inicio_funcao, funcao.data_fim_funcao or datetime.date.today()):
                    funcoes_por_dia[dia] = funcao

        return funcoes_por_dia

    def get_dias_liberado_frequencia_periodo(self, data_ini, data_fim):
        dias_liberado_frequencia = []

        qry_dias_liberado_frequencia = self.historico_funcao(data_ini, data_fim).filter(
            setor_suap__isnull=False,
            funcao__codigo__in=ServidorFuncaoHistorico.FUNCOES_LIBERADO_FREQUENCIA,
            nivel__in=ServidorFuncaoHistorico.NIVEIS_LIBERADO_FREQUENCIA,
        )

        if qry_dias_liberado_frequencia.exists():
            for funcao_servidor in qry_dias_liberado_frequencia:
                if funcao_servidor.data_inicio_funcao < data_ini:
                    funcao_servidor.data_inicio_funcao = data_ini
                if not funcao_servidor.data_fim_funcao or funcao_servidor.data_fim_funcao > data_fim:
                    funcao_servidor.data_fim_funcao = data_fim
                dias_liberado_frequencia += datas_entre(funcao_servidor.data_inicio_funcao, funcao_servidor.data_fim_funcao)

        return dias_liberado_frequencia

    def chefes_imediatos(self):
        if self.setor:
            setor = self.setor

            if self.eh_chefe_do_setor_hoje(self.setor):
                if self.setor.superior:
                    setor = self.setor.superior

            while not setor.historico_funcao().exists() and setor.superior:
                setor = setor.superior

            return Servidor.objects.filter(pk__in=setor.historico_funcao().values_list("servidor_id", flat=True))
        return Servidor.objects.none()

    def eh_liberado_controle_frequencia(self):
        return self.historico_funcao_ativa().filter(nivel__in=["1", "2", "3"], funcao__codigo=Funcao.CODIGO_CD).exists()
        # return self.funcao_display in ['CD1', 'CD2', 'CD3']

    @property
    def disciplina_ingresso(self):
        if self.eh_docente and self.professor_set.all().exists():
            return self.professor_set.all()[0].disciplina
        return "-"

    @property
    def professor(self):
        if "edu" in settings.INSTALLED_APPS:
            return self.professor_set.first()
        else:
            return None

    @classmethod
    def get_sem_setor_suap(cls, do_meu_campus=False):
        servidores = cls.objects.vinculados().filter(setor__isnull=True).exclude(situacao__codigo=Situacao.APOSENTADOS)
        if do_meu_campus:
            meu_campus_siape = get_uo_siape()
            servidores = servidores.filter(setor_lotacao__uo=meu_campus_siape) | servidores.filter(setor_funcao__uo=meu_campus_siape)
        return servidores.order_by("nome")

    @classmethod
    def get_sem_cargo(cls, do_meu_campus=False):
        situacoes = (Situacao.APOSENTADOS,) + Situacao.situacoes_siape_estagiarios()
        servidores = cls.objects.vinculados().filter(cargo_emprego__isnull=True).exclude(situacao__codigo__in=situacoes)
        if do_meu_campus:
            servidores = servidores.filter(setor__uo=get_uo())
        return servidores.order_by("nome")

    @staticmethod
    def get_servidores_com_cargafuncao(campus=None, funcao=None):
        servidores = Servidor.objects.filter(funcao__isnull=False, excluido=False)
        if campus:
            servidores = servidores.filter(setor__uo=campus)
        if funcao:
            servidores = servidores.filter(funcao=funcao)
        servidores = servidores.order_by("setor__uo__setor__sigla", "nome")
        return servidores

    @property
    def eh_aposentado(self):
        return self.situacao.codigo == Situacao.APOSENTADOS

    @property
    def eh_estagiario(self):
        return self.situacao.codigo in Situacao.situacoes_siape_estagiarios()

    @property
    def get_grupo_cargo_emprego(self):
        if self.cargo_emprego:
            return self.cargo_emprego.grupo_cargo_emprego
        return None

    @property
    def dependentes(self):
        Dependente = apps.get_model("comum", "dependente")
        return Dependente.objects.filter(servidor=self)

    @property
    def atividade(self):
        return self.funcao_atividade

    @property
    def funcao_display(self):
        return "{}{}".format(self.funcao and self.funcao.codigo or "", self.funcao_codigo or "")

    @property
    def categoria(self):
        """
        Teoricamente pode retornar 3 strings:
            ['Técnico-administrativo', 'Docente', 'ESTAGIARIO']
        """
        if self.eh_docente:
            return "docente"
        elif self.eh_tecnico_administrativo:
            return "tecnico_administrativo"
        elif self.eh_estagiario:
            return "estagiario"
        return "indefinida"

    @property
    def categoria_display(self):
        """
        Teoricamente pode retornar 3 strings:
            ['Técnico-administrativo', 'Docente', 'ESTAGIARIO']
        """
        if self.eh_docente:
            return "Docente"
        elif self.eh_tecnico_administrativo:
            return "Técnico-administrativo"
        elif self.eh_estagiario:
            return "Estagiário"
        return "Indefinida"

    @property
    def ocorrencias(self):
        ServidorOcorrencia = apps.get_model("rh", "ServidorOcorrencia")
        return ServidorOcorrencia.objects.filter(servidor=self)

    @property
    def ocorrencias_display(self):
        return "<br>".join(
            [
                "{}: {} - {}".format(
                    so.ocorrencia.grupo_ocorrencia.nome, so.ocorrencia.nome, [so.data.strftime("%d/%m/%Y") if so else ""][0]
                )
                for so in self.ocorrencias
            ]
        )

    @property
    def afastamentos(self):
        ServidorAfastamento = apps.get_model("rh", "ServidorAfastamento")
        return ServidorAfastamento.objects.filter(servidor=self, cancelado=False)

    @property
    def afastamentos_para_capacitacao_strictu_sensu(self):
        return self.afastamentos.filter(afastamento__codigo=AfastamentoSiape.AFASTAMENTO_STRICTU_SENSU)

    @property
    def afastamentos_para_capacitacao_strictu_sensu_hoje(self):
        hoje = datetime.date.today()
        return self.afastamentos.filter(
            afastamento__codigo=AfastamentoSiape.AFASTAMENTO_STRICTU_SENSU, data_inicio__lte=hoje, data_termino__gte=hoje
        )

    @property
    def tempo_afastado_para_capacitacao_strictu_sensu(self):
        tempo = datetime.timedelta(0)
        hoje = datetime.datetime.today().date()
        if self.afastamentos_para_capacitacao_strictu_sensu.exists():
            for afastamento in self.afastamentos_para_capacitacao_strictu_sensu:
                data_fim = afastamento.data_termino
                if afastamento.data_termino >= hoje:
                    data_fim = hoje
                tempo += data_fim - afastamento.data_inicio

        return tempo

    @property
    def ultimo_afastamento_para_capacitacao_strictu_sensu(self):
        if self.afastamentos_para_capacitacao_strictu_sensu.exists():
            return self.afastamentos_para_capacitacao_strictu_sensu.latest("data_termino")
        return None

    @property
    def dois_anos_apos_ultimo_afastamento_para_capacitacao_strictu_sensu(self):
        ultimo_afastamento = self.ultimo_afastamento_para_capacitacao_strictu_sensu
        if ultimo_afastamento:
            return ultimo_afastamento.data_termino + relativedelta(years=2)
        return None

    @property
    def afastamentos_para_capacitacao_3_meses(self):
        return self.afastamentos.filter(afastamento__codigo=AfastamentoSiape.LICENCA_CAPACITACAO_3_MESES)

    @property
    def ultimo_afastamento_para_capacitacao_3_meses(self):
        if self.afastamentos_para_capacitacao_3_meses.exists():
            return self.afastamentos_para_capacitacao_3_meses.latest("data_termino")
        return None

    @property
    def dois_anos_apos_ultimo_afastamento_para_capacitacao_3_meses(self):
        ultimo_afastamento = self.ultimo_afastamento_para_capacitacao_3_meses
        if ultimo_afastamento:
            return ultimo_afastamento.data_termino + relativedelta(years=2)
        return None

    @property
    def total_dias_afastado_interrompe_pagamento(self, data_inicio=None, data_fim=None):
        hoje = datetime.datetime.today().date()
        if not data_inicio:
            data_inicio = self.data_inicio_exercicio_no_cargo
        if not data_fim:
            data_fim = hoje
        afastamentos = self.afastamentos.filter(
            afastamento__interrompe_pagamento=True, data_inicio__gte=data_inicio, data_termino__lte=data_fim, cancelado=False
        )
        total_dias_afastamentos = datetime.timedelta(0)

        for afastamento in afastamentos:
            afastamento_data_fim = afastamento.data_termino
            afastamento_data_inicio = afastamento.data_inicio
            if afastamento_data_inicio < data_inicio:
                afastamento_data_inicio = data_inicio
            if afastamento_data_fim > data_fim:
                afastamento_data_fim = data_fim
            total_dias_afastamentos += (afastamento_data_fim - afastamento_data_inicio) + datetime.timedelta(1)

        # aplica os afastamentos ao tempo calculado, NÃO considerando o fator
        return total_dias_afastamentos

    @property
    def media_ultima_progressao(self):
        ProcessoProgressao = apps.get_model("progressoes.ProcessoProgressao")
        if self.processoprogressao_set.filter(
            tipo=ProcessoProgressao.TIPO_PROGRESSAO_MERITO, status=ProcessoProgressao.STATUS_FINALIZADO
        ).exists():
            return (
                self.processoprogressao_set.filter(
                    tipo=ProcessoProgressao.TIPO_PROGRESSAO_MERITO, status=ProcessoProgressao.STATUS_FINALIZADO
                )
                .latest("pk")
                .media_processo
            )
        return None

    @property
    def afastamentos_display(self):
        return "<br/>".join(
            [
                "{}: {} - {}".format(
                    servidor_afastamento.afastamento.get_tipo_display(),
                    servidor_afastamento.afastamento.nome,
                    [servidor_afastamento.data_inicio.strftime("%d/%m/%Y") if servidor_afastamento else ""][0],
                )
                for servidor_afastamento in self.afastamentos
            ]
        )

    @property
    def data_previsao_estabilidade(self):
        if self.data_inicio_exercicio_no_cargo:
            data_previsao_estabilidade = self.data_inicio_exercicio_no_cargo + relativedelta(years=3)
            if self.total_dias_afastado_interrompe_pagamento:
                data_previsao_estabilidade = data_previsao_estabilidade + self.total_dias_afastado_interrompe_pagamento
            return data_previsao_estabilidade
        return None

    # -----------------------------------------------------------------
    # -----------------------------------------------------------------
    # data_inicio_no_servico_publico
    @property
    def calcula_inicio_no_servico_publico(self):
        so = self.servidorocorrencia_set.filter(subgrupo__descricao__unaccent__icontains="INCLUSAO NO SERVICO PUBLICO").order_by("data")
        if so.exists():
            return so[0].data
        return None

    # data_posse_na_instituicao
    @property
    def calcula_posse_na_instituicao(self):
        # via PCA
        pca = self.pca_set.all().order_by("data_entrada_pca")
        if pca.exists():
            return pca[0].data_entrada_pca

        # via OCORRENCIA
        so = self.servidorocorrencia_set.filter(subgrupo__descricao="INCLUSAO NO ORGAO").order_by("data")
        if so.exists():
            return so[0].data
        return None

    #  data_inicio_exercicio_na_instituicao

    @property
    def calcula_inicio_exercicio_na_instituicao(self):  # início do exercício
        # via PCA
        pca = self.pca_set.all().order_by("data_entrada_pca")
        if pca.exists():
            return pca[0].inicio_exercicio_pca

        # via OCORRENCIA
        so = self.servidorocorrencia_set.filter(subgrupo__descricao="INCLUSAO NO ORGAO").order_by("data")
        if so.exists():
            return so[0].data
        return None

    # data_inicio_exercicio_no_cargo
    @property
    def calcula_inicio_exercicio_no_cargo(self):  # início do exercício no cargo
        # via PCA
        pcas = self.pca_set.filter(servidor_vaga_pca=self.codigo_vaga).order_by("-data_entrada_pca")
        if pcas.exists():
            return pcas[0].inicio_exercicio_pca

        # via OCORRENCIA
        so = self.servidorocorrencia_set.filter(subgrupo__descricao="INCLUSAO NO ORGAO").order_by("data")
        if so.exists():
            return so[0].data
        return None

    # data_posse_no_cargo

    @property
    def calcula_posse_no_cargo(self):  # posse no cargo
        # via PCA
        pcas = self.pca_set.filter(servidor_vaga_pca=self.codigo_vaga).order_by("-data_entrada_pca")
        if pcas.exists():
            return pcas[0].data_entrada_pca

        # via OCORRENCIA
        so = self.servidorocorrencia_set.filter(subgrupo__descricao="INCLUSAO NO ORGAO").order_by("data")
        if so.exists():
            return so[0].data
        return None

    # data_fim_servico_na_instituicao
    @property
    def calcula_fim_servico_na_instituicao(self):
        pca = self.pca_set.all().order_by("-data_entrada_pca")
        existe_pca = pca.exists()
        if existe_pca:
            pca = pca[0]
        ocorrencia_exclusao = self.servidorocorrencia_set.filter(subgrupo__descricao="EXCLUSAO").order_by("-data")
        existe_ocorrencia_exclusao = ocorrencia_exclusao.exists()
        if existe_ocorrencia_exclusao:
            ocorrencia_exclusao = ocorrencia_exclusao[0]

        referencia = "pca"
        if existe_pca and existe_ocorrencia_exclusao:
            if pca.data_entrada_pca >= ocorrencia_exclusao.data:
                referencia = "pca"
            elif pca.forma_vacancia_pca:
                referencia = "pca"
            else:
                referencia = "ocorrencia"
        elif existe_pca:
            referencia = "pca"
        else:
            referencia = "ocorrencia"

        if referencia == "pca":
            if pca.fim_exercicio_pca_or_None:
                return pca.fim_exercicio_pca_or_None

        elif referencia == "ocorrencia":
            # via OCORRENCIA
            so_inclusao = (
                self.servidorocorrencia_set.filter(subgrupo__descricao__in=["INCLUSAO NO ORGAO", "INCLUSAO NO SERVICO PUBLICO"])
                .exclude(ocorrencia__nome="REFORMA ADMINISTRATIVA")
                .order_by("-data")
            )
            so = self.servidorocorrencia_set.filter(subgrupo__descricao="EXCLUSAO").order_by("-data") or self.servidorocorrencia_set.filter(
                ocorrencia__grupo_ocorrencia__nome__unaccent__icontains="EXCLUSAO"
            ).order_by("-data")

            if so.exists() and so_inclusao.exists():
                if self.situacao.codigo in Situacao.situacoes_servidores_de_carreira():
                    if so_inclusao.latest("data").data <= so.latest("data").data:
                        return so[0].data
                else:
                    return so.latest("data").data
        return None

    @property
    def datas_ultimas_progressoes(self):
        datas = []
        for pca in self.pca_set.all():
            try:
                # posicionamento mais atual (índice 0 com data em ordem decrescente)
                posicionamento = pca.posicionamentopca_set.filter(forma_entrada__codigo=FormaProvimentoVacancia.CODIGO_PROGRESSAO).order_by(
                    "-data_inicio_posicionamento_pca"
                )[0]
                datas.append(posicionamento.data_inicio_posicionamento_pca)
            except Exception:
                continue  # vai para o prox pca
        return datas

    @property
    def data_ultima_progressao(self):
        if self.datas_ultimas_progressoes:
            return self.datas_ultimas_progressoes[0]
        return None

    @property
    def aposentadoria(self):
        ServidorOcorrencia = apps.get_model("rh", "ServidorOcorrencia")
        sos = ServidorOcorrencia.objects.filter(servidor=self, ocorrencia__grupo_ocorrencia__nome__unaccent__icontains="aposent")
        ocorrencias = []
        for so in sos:
            if so.diploma_legal:
                ocorrencias.append(
                    "{}: Diploma: {} - {} - {}, Tipo: {}, {}, Data: {}. ".format(
                        so.ocorrencia.codigo,
                        so.diploma_legal_num,
                        so.diploma_legal.sigla,
                        so.diploma_legal_data,
                        so.ocorrencia.nome,
                        so.ocorrencia.grupo_ocorrencia.nome,
                        so.data.strftime("%d/%m/%Y"),
                    )
                )
            else:
                ocorrencias.append(
                    "{}: Diploma: Não definido, Tipo: {}, {}, Data: {}. ".format(
                        so.ocorrencia.codigo, so.ocorrencia.nome, so.ocorrencia.grupo_ocorrencia.nome, so.data.strftime("%d/%m/%Y")
                    )
                )
        return "".join(ocorrencias) or "Sem ocorência de aposentadoria."

    @property
    def data_aposentadoria(self):
        ServidorOcorrencia = apps.get_model("rh", "ServidorOcorrencia")
        sos = ServidorOcorrencia.objects.filter(servidor=self, ocorrencia__grupo_ocorrencia__nome__unaccent__icontains="aposent")
        if sos.exists():
            return sos[0].data
        return None

    @property
    def data_aposentadoria_pca(self):
        qs_aposentadoria_pca = self.pca_set.filter(forma_vacancia_pca__descricao__unaccent__icontains="APOSENT").order_by(
            "-data_vacancia_pca"
        )
        if qs_aposentadoria_pca.exists():
            return qs_aposentadoria_pca[0].data_vacancia_pca
        return None

    @property
    def campus_lotacao_siape(self):
        if self.setor_lotacao:
            return self.setor_lotacao.uo
        return None

    @property
    def campus_exercicio_siape(self):
        if self.setor_exercicio:
            return self.setor_exercicio.uo
        return None

    @property
    def ferias(self):
        return ", ".join(self.get_ferias())  # string contendo as férias separadas por ','

    @property
    def ferias_lista(self):
        return self.get_ferias()  # lista contendo as férias

    @property
    def jornada_trabalho_servidor_pca(self):
        if self.pca_set.all().exists():
            pca = self.pca_set.all().latest("data_entrada_pca")
            if pca.jornadatrabalhopca_set.all().exists():
                jornada = pca.jornadatrabalhopca_set.all().latest("data_inicio_jornada_trabalho_pca").qtde_jornada_trabalho_pca
        else:
            jornada = ""
        return jornada

    @property
    def is_historico_setor_com_pendencias(self):
        historico_siape = self.historico_setor_siape()
        historico_suap = self.historico_setor_suap()
        #
        sem_setor_siape = not historico_siape.exists()
        sem_setor_suap = not historico_suap.exists() or self.setor is None
        #
        if historico_siape.exists() and historico_suap.exists():
            setor_siape = historico_siape.order_by("-data_inicio_setor_lotacao")[0].setor_exercicio
            setor_suap = historico_suap.order_by("-data_inicio_no_setor")[0].setor
            setor_historico_suap_com_campus_invalido = not (
                setor_suap and setor_siape and setor_siape.uo and setor_siape.uo.equivalente and setor_siape.uo.equivalente == setor_suap.uo
            )
        else:
            setor_historico_suap_com_campus_invalido = True
        #
        if historico_suap.exists():
            setor_atual_difere_do_setor_historico_suap = self.setor.id != historico_suap.order_by("-data_inicio_no_setor")[0].setor.id
        else:
            setor_atual_difere_do_setor_historico_suap = True
        #
        return sem_setor_siape or sem_setor_suap or setor_historico_suap_com_campus_invalido or setor_atual_difere_do_setor_historico_suap

    @property
    def papeis(self):
        return self.papel_set.all()

    @property
    def papeis_ativos(self):
        hoje = datetime.date.today()
        papeis_datas_menores_hoje = self.papel_set.filter(data_inicio__lte=hoje)
        return papeis_datas_menores_hoje.filter(data_fim__isnull=True) | papeis_datas_menores_hoje.filter(data_fim__gte=hoje)

    def eh_reitor(self, na_data=datetime.date.today()):
        return self.historico_funcao(na_data, na_data).filter(funcao__codigo="CD", nivel__in=("1", "0001")).exists()

    def has_funcao_por_data(self, data):
        return self.historico_funcao(data, data)

    def tempo_servico_na_instituicao(self):
        if self.data_inicio_exercicio_na_instituicao:
            return (
                (self.data_fim_servico_na_instituicao or datetime.date.today())
                - self.data_inicio_exercicio_na_instituicao
                + datetime.timedelta(1)
            )
        return None

    def tempo_servico_no_cargo(self, data_referencia=datetime.date.today()):
        if data_referencia > datetime.date.today():
            data_referencia = datetime.date.today()
        if self.data_inicio_exercicio_no_cargo:
            if self.data_fim_servico_na_instituicao and data_referencia < self.data_fim_servico_na_instituicao:
                return data_referencia - self.data_inicio_exercicio_no_cargo
            return (self.data_fim_servico_na_instituicao or data_referencia) - self.data_inicio_exercicio_no_cargo + datetime.timedelta(1)
        return None

    def tempo_servico_na_instituicao_via_pca(self, ficto=False, data_referencia=datetime.date.today()):
        # calcula o TEMPO REAL ou TEMPO FICTO
        # retorna um timedelta

        tempo_servico = datetime.timedelta(0)  # em timedelta
        # calcula o tempo ficto (considera o fator do regime juridico)
        for pca in self.pca_set.all():
            tempo_servico += pca.tempo_servico_pca(ficto, data_referencia)
        return tempo_servico

    def tempo_servico_no_cargo_via_pca(self, ficto=False, data_referencia=datetime.date.today()):
        tempo_servico = datetime.timedelta(0)  # em timedelta
        for pca in self.pca_set.filter(servidor_vaga_pca=self.codigo_vaga):
            tempo_servico += pca.tempo_servico_pca(ficto, data_referencia)
        return tempo_servico

    def get_ferias(self):
        """
        Modelo novo baseado em suap.ferias.models.Ferias.
        Modelo antigo baseado em suap.rh.models.ServidorOcorrencia
            Executar o script no banco: ServidorOcorrencia.objects.filter(ocorrencia__nome__unaccent__icontains='ferias').delete()
        """

        # Ano -> Períodos: dd/mm/aaaa até dd/mm/aaaa, dd/mm/aaaa até dd/mm/aaaa, dd/mm/aaaa até dd/mm/aaaa. Interrupções: 1ª dd/mm/aaaa - cont. dd/mm/aaaa até dd/mm/aaaa, ...
        servidor_ferias_lista = []
        if "ferias" in settings.INSTALLED_APPS:
            from ferias.models import Ferias, InterrupcaoFerias

            servidor_ferias = Ferias.objects.filter(servidor=self).order_by("ano__ano")
            # a lista que será retornada pela propriedade
            for ferias in servidor_ferias:
                servidor_ferias_str = f"{ferias.ano} -> Períodos: "

                if ferias.data_inicio_periodo1:
                    servidor_ferias_str += "{} até {}".format(
                        ferias.data_inicio_periodo1.strftime("%d/%m/%Y"), ferias.data_fim_periodo1.strftime("%d/%m/%Y")
                    )
                if ferias.data_inicio_periodo2:
                    servidor_ferias_str += ", {} até {}".format(
                        ferias.data_inicio_periodo2.strftime("%d/%m/%Y"), ferias.data_fim_periodo2.strftime("%d/%m/%Y")
                    )
                if ferias.data_inicio_periodo3:
                    servidor_ferias_str += ", {} até {}".format(
                        ferias.data_inicio_periodo3.strftime("%d/%m/%Y"), ferias.data_fim_periodo3.strftime("%d/%m/%Y")
                    )
                servidor_ferias_str += ". "

                interrupcoes = InterrupcaoFerias.objects.filter(ferias=ferias).order_by("data_interrupcao_periodo")
                if interrupcoes.exists():
                    servidor_ferias_str += "Interrupções -> "
                    for idx, interrupcao in enumerate(interrupcoes):
                        if idx > 0:
                            servidor_ferias_str += ", "
                        servidor_ferias_str += "{}ª {} - cont. {} até {}".format(
                            idx + 1,
                            interrupcao.data_interrupcao_periodo and interrupcao.data_interrupcao_periodo.strftime("%d/%m/%Y") or "-",
                            interrupcao.data_inicio_continuacao_periodo
                            and interrupcao.data_inicio_continuacao_periodo.strftime("%d/%m/%Y")
                            or "-",
                            interrupcao.data_fim_continuacao_periodo
                            and interrupcao.data_fim_continuacao_periodo.strftime("%d/%m/%Y")
                            or "-",
                        )
                servidor_ferias_lista.append(servidor_ferias_str)
        return servidor_ferias_lista

    def get_matriculas_por_cpf(self):
        return Servidor.objects.filter(cpf=self.cpf).exclude(id=self.id)

    #
    # obtém a jornada de trabalho do servidor em certa data
    # retorna uma instância de rh.JornadaTrabalho
    #
    def jornada_trabalho_servidor(self, data=None):
        if not data:
            data = datetime.date.today()

        jornada_funcao = self.get_jornadas_funcoes_dict(data_inicio=data, data_fim=data).get(data)
        if jornada_funcao:
            return jornada_funcao

        jornada_setor = dict()
        if self.cargo_emprego and self.cargo_emprego.grupo_cargo_emprego.categoria == "tecnico_administrativo":
            jornada_setor = self.get_jornadas_por_setores_dict(data_inicio=data, data_fim=data).get(data)
        jornada_servidor = self.get_jornadas_servidor_dict(data_inicio=data, data_fim=data).get(data)

        jornada_funcionario = self.get_jornadas_por_funcionario_dict(data_inicio=data, data_fim=data).get(data)
        if jornada_funcionario:
            return jornada_funcionario

        if jornada_setor and jornada_servidor:
            return (
                jornada_setor
                if jornada_setor.get_jornada_trabalho_diaria() <= jornada_servidor.get_jornada_trabalho_diaria()
                else jornada_servidor
            )

        return jornada_setor or jornada_servidor

    # obtém a jornada de trabalho do servidor em um período
    # retorna um dicionario com os dias e as jornadas de trabalho
    def get_jornadas_servidor_dict(self, data_inicio, data_fim):
        jornadas_trabalho_servidor = dict()

        if self.eh_estagiario:
            for dia in datas_entre(data_inicio, data_fim):
                jornadas_trabalho_servidor[dia] = self.jornada_trabalho
            return jornadas_trabalho_servidor

        jornadas_trabalhos_pca = JornadaTrabalhoPCA.objects.filter(pk__in=self.pca_set.all().values_list("jornadatrabalhopca", flat=True))

        if jornadas_trabalhos_pca.exists():
            jornadas_de_trabalho = {}  # {nome: instância, ...}

            for jornada in jornadas_trabalhos_pca:
                data_inicio_jornada = jornada.data_inicio_jornada_trabalho_pca
                data_fim_jornada = jornada.data_fim_jornada_trabalho_pca
                if data_inicio_jornada <= data_inicio:
                    data_inicio_jornada = data_inicio
                if not data_fim_jornada or data_fim_jornada >= data_fim:
                    data_fim_jornada = data_fim
                for dia in datas_entre(data_inicio_jornada, data_fim_jornada):
                    if jornada.qtde_jornada_trabalho_pca == "99":
                        nome_jornada = "DEDICACAO EXCLUSIVA"
                    else:
                        nome_jornada = f"{jornada.qtde_jornada_trabalho_pca} HORAS SEMANAIS"

                    jornadas_trabalho_servidor[dia] = JornadaTrabalho.get_jornada(nome_jornada)

                    if nome_jornada not in jornadas_de_trabalho:
                        jornadas_de_trabalho[nome_jornada] = JornadaTrabalho.get_jornada(nome_jornada)

                    jornadas_trabalho_servidor[dia] = jornadas_de_trabalho[nome_jornada]

        # procura ocorrências de jornada de trabalho em processos de ch reduzida
        servidor_jornadas_via_ch_reduzida = HorarioSemanal.get_jornadas_servidor_horario(self, data_inicio, data_fim)
        jornadas_trabalho_servidor.update(servidor_jornadas_via_ch_reduzida)

        return jornadas_trabalho_servidor

        #
        # obtém a jornada de trabalho de um funcionario cadastradas pela chefia analisando o seu historico setor em um período
        # retorna um dicionario com os dias e as jornadas de trabalho
        #

    def get_jornadas_por_funcionario_dict(self, data_inicio, data_fim):
        jornadas_funcionarios = dict()
        historico_setor = self.historico_setor_suap(data_inicio, data_fim)
        if historico_setor.exists():
            for hist_setor in historico_setor:
                data_inicio_setor = hist_setor.data_inicio_no_setor
                data_fim_setor = hist_setor.data_fim_no_setor
                if data_inicio_setor <= data_inicio:
                    data_inicio_setor = data_inicio
                if not data_fim_setor or data_fim_setor >= data_fim:
                    data_fim_setor = data_fim

                jornada_trabalho_funcionario_no_setor = self.jornada_trabalho_por_periodo_dict(
                    hist_setor.setor, data_inicio_setor, data_fim_setor
                )

                for dia in datas_entre(data_inicio_setor, data_fim_setor):
                    jornadas_funcionarios[dia] = jornada_trabalho_funcionario_no_setor.get(dia)
        return jornadas_funcionarios

    #
    # obtém a jornada de trabalho de um servidor analisando o seu historico setor em um período
    # retorna um dicionario com os dias e as jornadas de trabalho
    #
    def get_jornadas_por_setores_dict(self, data_inicio, data_fim):
        jornadas_setores = dict()
        historico_setor = self.historico_setor_suap(data_inicio, data_fim)
        if historico_setor.exists():
            for hist_setor in historico_setor:
                data_inicio_setor = hist_setor.data_inicio_no_setor
                data_fim_setor = hist_setor.data_fim_no_setor
                if data_inicio_setor <= data_inicio:
                    data_inicio_setor = data_inicio
                if not data_fim_setor or data_fim_setor >= data_fim:
                    data_fim_setor = data_fim

                jornada_trabalho_setor = hist_setor.setor.jornada_trabalho_por_periodo_dict(data_inicio_setor, data_fim_setor)
                for dia in datas_entre(data_inicio_setor, data_fim_setor):
                    jornadas_setores[dia] = jornada_trabalho_setor.get(dia)
        return jornadas_setores

    # obtém a jornada de trabalho de um servidor analisando o seu historico de funcoes em um período
    # retorna um dicionario com os dias e as jornadas de trabalho
    def get_jornadas_funcoes_dict(self, data_inicio, data_fim):
        jornadas_funcoes = dict()

        if self.eh_estagiario:
            return jornadas_funcoes

        historico_funcoes_servidor = self.historico_funcao(data_inicio=data_inicio, data_fim=data_fim).filter(
            funcao__codigo__in=Funcao.get_codigos_funcao_chefia()
        )

        quarenta_horas = JornadaTrabalho.get_jornada("40 HORAS SEMANAIS")
        if historico_funcoes_servidor.exists():
            for funcao in historico_funcoes_servidor:
                data_inicio_funcao = funcao.data_inicio_funcao
                data_fim_funcao = funcao.data_fim_funcao
                if data_inicio_funcao <= data_inicio:
                    data_inicio_funcao = data_inicio

                if not data_fim_funcao or data_fim_funcao >= data_fim:
                    data_fim_funcao = data_fim

                for dia in datas_entre(data_inicio_funcao, data_fim_funcao):
                    jornadas_funcoes[dia] = quarenta_horas

        # procura ocorrências de jornada de trabalho em processos de ch reduzida
        servidor_jornadas_via_ch_reduzida = HorarioSemanal.get_jornadas_servidor_horario(self, data_inicio, data_fim)
        jornadas_funcoes.update(servidor_jornadas_via_ch_reduzida)

        return jornadas_funcoes

    # obtém a jornada de trabalho de um servidor em um período
    # retorna um dicionario com os dias e as jornadas de trabalho
    def get_jornadas_periodo_dict(self, data_inicio, data_fim):
        jornada_padrao = JornadaTrabalho.get_jornada("40 HORAS SEMANAIS")
        jornadas = dict()
        jornadas_funcoes = dict()
        jornadas_setores = dict()
        if self.eh_tecnico_administrativo:
            jornadas_funcoes = self.get_jornadas_funcoes_dict(data_inicio, data_fim)
            jornadas_setores = self.get_jornadas_por_setores_dict(data_inicio, data_fim)
        elif self.eh_docente:
            jornadas_funcoes = self.get_jornadas_funcoes_dict(data_inicio, data_fim)

        jornadas_servidor = self.get_jornadas_servidor_dict(data_inicio, data_fim)
        """ jornadas_funcionario pega tambem para ESTAGIARIOS """
        jornadas_funcionario = self.get_jornadas_por_funcionario_dict(data_inicio, data_fim)

        for dia in datas_entre(data_inicio, data_fim):
            if jornadas_funcoes.get(dia):
                jornadas[dia] = jornadas_funcoes.get(dia)
            elif jornadas_setores.get(dia) or jornadas_servidor.get(dia) or jornadas_funcionario.get(dia):
                if jornadas_setores.get(dia) and jornadas_servidor.get(dia):
                    if jornadas_setores.get(dia).get_jornada_trabalho_diaria() <= jornadas_servidor.get(dia).get_jornada_trabalho_diaria():
                        jornadas[dia] = jornadas_setores.get(dia)
                    else:
                        jornadas[dia] = jornadas_servidor.get(dia)
                else:
                    jornadas[dia] = jornadas_setores.get(dia) or jornadas_servidor.get(dia)

                """ jornadas_funcionario sobrepoe jornadas-setores e jornadas_servidor """
                if jornadas_funcionario.get(dia):
                    jornadas[dia] = jornadas_funcionario.get(dia)

            else:
                jornadas[dia] = jornada_padrao
        return jornadas

    #
    # obtém uma lista do(s) setor(es) SUAP do servidor em certo período
    #
    def setor_suap_servidor_por_periodo(self, data_inicial=None, data_final=None):
        if (data_inicial is None) and (data_final is None):  # período informado?
            #
            # período não foi informado ... retorna o setor atual
            #
            return [self.setor]
        else:
            #
            # uma das datas pode ser nula
            #
            if data_inicial is None:
                data_inicial = data_final
            elif data_final is None:
                data_final = data_inicial

            #
            # nesse ponto, temos um período válido
            # obtém o(s) setor(es) no período
            #
            if data_inicial != data_final:
                qs_1 = ServidorSetorHistorico.objects.filter(
                    servidor=self,
                    data_inicio_no_setor__lte=data_inicial,
                    data_fim_no_setor__gte=data_inicial,
                    data_fim_no_setor__lte=data_final,
                )  # inicio fora e termino dentro do período (incluindo extremidades)

                qs_2 = ServidorSetorHistorico.objects.filter(
                    servidor=self,
                    data_inicio_no_setor__gt=data_inicial,
                    data_inicio_no_setor__lt=data_final,
                    data_fim_no_setor__lt=data_final,
                )  # inicio dentro e termino dentro do período (nao incluindo extremidades)

                qs_3 = ServidorSetorHistorico.objects.filter(
                    servidor=self, data_inicio_no_setor__lte=data_inicial, data_fim_no_setor__gte=data_final
                )  # inicio fora e termino fora do período (incluindo extremidades)

                qs_4 = ServidorSetorHistorico.objects.filter(
                    servidor=self, data_inicio_no_setor__lte=data_final, data_fim_no_setor__isnull=True
                )  # período com data final não definida

                historicos = (qs_1 | qs_2 | qs_3 | qs_4).distinct()
            else:
                qs_1 = ServidorSetorHistorico.objects.filter(
                    servidor=self, data_inicio_no_setor__lte=data_inicial, data_fim_no_setor__gte=data_final
                )  # data informada dentro do período

                qs_2 = ServidorSetorHistorico.objects.filter(
                    servidor=self, data_inicio_no_setor__lte=data_inicial, data_fim_no_setor__isnull=True
                )  # data inicial antes ou igual a data informada e data final não definida

                historicos = (qs_1 | qs_2).distinct()

            setores = []
            for historico in historicos.select_related("setor"):
                if historico.setor not in setores:
                    setores.append(historico.setor)

            return setores

    # verifica qual o setor do servidor em um dia específico
    def setor_suap_servidor_no_dia(self, dia):
        qs_setor = self.servidorsetorhistorico_set.filter(data_inicio_no_setor__lte=dia)
        if qs_setor.exists():
            # verificando data final no setor
            qs_setor = qs_setor.filter(data_fim_no_setor__gte=dia) | qs_setor.filter(data_fim_no_setor__isnull=True)
            if qs_setor.exists():
                return qs_setor[0].setor
        return None

    def historico_setor_suap(self, data_inicio=None, data_fim=None):
        if not data_inicio:
            data_inicio = self.calcula_inicio_exercicio_na_instituicao or datetime.date.today()
        if not data_fim:
            data_fim = datetime.date.today()
        #
        historico_setor = ServidorSetorHistorico.objects.filter(
            servidor=self, data_inicio_no_setor__lte=data_fim, data_fim_no_setor__gte=data_inicio
        ) | ServidorSetorHistorico.objects.filter(servidor=self, data_inicio_no_setor__lte=data_fim, data_fim_no_setor__isnull=True)
        return historico_setor

    def historico_setor_siape(self, data_inicio=None, data_fim=None):
        if not data_inicio:
            data_inicio = self.calcula_inicio_exercicio_na_instituicao or datetime.date.today()
        if not data_fim:
            data_fim = datetime.date.today()
        #
        historico_setor = ServidorSetorLotacaoHistorico.objects.filter(
            servidor=self, data_inicio_setor_lotacao__lte=data_fim, data_fim_setor_lotacao__gte=data_inicio
        ) | ServidorSetorLotacaoHistorico.objects.filter(
            servidor=self, data_inicio_setor_lotacao__lte=data_fim, data_fim_setor_lotacao__isnull=True
        )
        return historico_setor

    def historico_funcao(self, data_inicio=None, data_fim=None):
        """histórico de função do Servidor em um período
        procura a interseção entre período informado e os períodos das funções
        """
        if not data_inicio:
            data_inicio = self.data_inicio_exercicio_na_instituicao or datetime.date.today()
        if not data_fim:
            data_fim = datetime.date.today()

        # data de inicio da funcao dentro do período informado
        historico_funcao = ServidorFuncaoHistorico.objects.filter(
            servidor=self, data_inicio_funcao__gte=data_inicio, data_inicio_funcao__lte=data_fim
        )

        # data de inicio da funcao antes do período informado e data fim da função depois da data inicio do período
        historico_funcao = historico_funcao | ServidorFuncaoHistorico.objects.filter(
            servidor=self, data_inicio_funcao__lt=data_inicio, data_fim_funcao__gte=data_inicio
        )

        # data de inicio da funcao antes do período informado e sem data fim
        historico_funcao = historico_funcao | ServidorFuncaoHistorico.objects.filter(
            servidor=self, data_inicio_funcao__lt=data_inicio, data_fim_funcao__isnull=True
        )

        # data de fim da funcao deve está dentro do período informado
        historico_funcao = historico_funcao | ServidorFuncaoHistorico.objects.filter(
            servidor=self, data_fim_funcao__gte=data_fim, data_fim_funcao__lte=data_fim
        )

        return historico_funcao.distinct()

    def historico_funcao_ativa(self):
        hoje = datetime.date.today()
        historico_funcao_ativa = ServidorFuncaoHistorico.objects.filter(
            servidor=self, data_inicio_funcao__lte=hoje, data_fim_funcao__gte=hoje
        ) | ServidorFuncaoHistorico.objects.filter(servidor=self, data_inicio_funcao__lte=hoje, data_fim_funcao__isnull=True)
        return historico_funcao_ativa

    @staticmethod
    def importar_funcao_servidor(verbosity=3):
        servidores = Servidor.objects.filter(cargo_emprego__isnull=False, excluido=False)
        estagiarios = Servidor.objects.filter(situacao__codigo__in=Situacao.situacoes_siape_estagiarios(), excluido=False)
        if verbosity:
            servidores = tqdm.tqdm(servidores)
            estagiarios = tqdm.tqdm(estagiarios)
        for servidor in servidores:
            servidor._definir_papel_do_servidor()
        for estagiario in estagiarios:
            estagiario._definir_papel_do_estagiario()

    def _definir_papel_do_servidor(self):
        if Papel.objects.filter(papel_content_id__isnull=True).exists():
            raise Exception(
                "Existem registros de Papel sem CargoEmprego ou Funcao definidos. "
                'Execute o command "importar_funcao_servidor_atualizar_genericfk" para resolver '
                "o problema."
            )

        kwargs = dict(
            detalhamento=self.cargo_emprego.nome,
            portaria="",
            data_fim=self.cargo_emprego_data_saida,
            tipo_papel=Papel.TIPO_PAPEL_CARGO,
            descricao=self.cargo_emprego.nome,
        )
        data_inicio = self.cargo_emprego_data_ocupacao if self.cargo_emprego_data_ocupacao else self.data_inicio_exercicio_no_cargo
        papel_cargo, criou = Papel.objects.update_or_create(
            pessoa=self.pessoafisica,
            data_inicio=data_inicio,
            papel_content_type=ContentType.objects.get_for_model(self.cargo_emprego),
            papel_content_id=self.cargo_emprego.id,
            defaults=kwargs,
        )
        hoje = datetime.date.today()
        if self.historico_funcao(hoje, hoje).exists():
            for funcao in self.historico_funcao(hoje, hoje).all():
                funcao.save()

    def _definir_papel_do_estagiario(self):
        if Papel.objects.filter(papel_content_id__isnull=True).exists():
            raise Exception(
                "Existem registros de Papel sem CargoEmprego ou Funcao definidos. "
                'Execute o command "importar_funcao_servidor_atualizar_genericfk" para resolver '
                "o problema."
            )

        kwargs = dict(
            detalhamento=self.situacao.nome,
            portaria="",
            data_fim=self.cargo_emprego_data_saida,
            tipo_papel=Papel.TIPO_PAPEL_CARGO,
            descricao=self.situacao.nome,
        )

        data_inicio = self.cargo_emprego_data_ocupacao if self.cargo_emprego_data_ocupacao else self.data_inicio_exercicio_no_cargo
        papel_cargo, criou = Papel.objects.update_or_create(
            pessoa=self.pessoafisica,
            data_inicio=data_inicio,
            papel_content_type=ContentType.objects.get_for_model(self.situacao),
            papel_content_id=self.situacao.id,
            defaults=kwargs,
        )
        hoje = datetime.date.today()
        if self.historico_funcao(hoje, hoje).exists():
            for funcao in self.historico_funcao(hoje, hoje).all():
                funcao.save()

    def qtd_horas_trabalhadas_gecc(self, ano):
        if "cursos" in settings.INSTALLED_APPS:
            from cursos.enums import SituacaoCurso, SituacaoParticipante

            qtd_horas = (
                self.participante_set.filter(
                    curso__situacao__in=[
                        SituacaoCurso.FINALIZADO,
                        SituacaoCurso.INICIADO,
                        SituacaoCurso.AGUARDANDO_CADASTRO_EM_FOLHA,
                        SituacaoCurso.CADASTRADO_EM_FOLHA,
                    ],
                    curso__ano_pagamento=ano,
                )
                .exclude(situacao=SituacaoParticipante.NAO_LIBERADO)
                .aggregate(horas=Sum("horas_trabalhada"))
            )

            return qtd_horas.get("horas") or 0
        else:
            return 0

    # IFMA/Tássio

    def get_funcao(self):
        from comum.models import FuncaoCodigo

        if self.funcao and self.funcao_codigo:
            funcao = FuncaoCodigo.objects.filter(nome__unaccent__icontains=self.funcao.codigo).filter(
                nome__unaccent__icontains=self.funcao_codigo
            )
            if funcao.exists():
                return funcao[0]
        return None


class ServidorSetorHistorico(ModelPlus):
    servidor = models.ForeignKeyPlus("rh.Servidor", null=False)
    setor = models.ForeignKeyPlus("rh.Setor", null=False, on_delete=models.CASCADE)
    data_inicio_no_setor = models.DateField(null=False)
    data_fim_no_setor = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "suap_servidorsetorhistorico"
        unique_together = ("servidor", "data_inicio_no_setor")
        verbose_name = "Histórico Setor Servidor"
        verbose_name_plural = "Histórico Setores Servidor"

    def __str__(self):
        return "{} - {} - {}".format(self.servidor.nome, self.setor.nome, self.data_inicio_no_setor.strftime("%d/%m/%Y"))


class ServidorSetorLotacaoHistorico(ModelPlus):
    servidor = models.ForeignKeyPlus("rh.Servidor", null=False, blank=False)
    setor_lotacao = models.ForeignKeyPlus("rh.Setor", null=False, blank=False, on_delete=models.CASCADE)
    setor_exercicio = models.ForeignKeyPlus(
        "rh.Setor", related_name="servidor_setor_exercicio_historico", null=False, blank=False, on_delete=models.CASCADE
    )
    data_inicio_setor_lotacao = models.DateField(null=False, blank=False, db_index=True)
    data_fim_setor_lotacao = models.DateFieldPlus(null=True, blank=True)
    hora_atualizacao_siape = models.DateTimeFieldPlus(null=False, blank=False)

    class Meta:
        unique_together = ("servidor", "data_inicio_setor_lotacao")
        verbose_name = "Histórico Setor de Lotação do Servidor"
        verbose_name_plural = "Histórico Setores de Lotação do Servidor"

    def __str__(self):
        return "{} - {} (Exercício::. {}) - de {} até ".format(
            self.servidor.nome, self.setor_lotacao.sigla, self.setor_exercicio.sigla, self.data_inicio_setor_lotacao.strftime("%d/%m/%Y")
        )


class CargoClasse(ModelPlus):
    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=40)
    excluido = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Classe do Cargo"
        verbose_name_plural = "Classes do Cargo"

    def __str__(self):
        return self.nome


class GrupoCargoEmprego(ModelPlus):
    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=40)
    sigla = models.CharField(max_length=10)
    categoria = models.CharField(
        max_length=30,
        null=True,
        choices=[["docente", "Docente"], ["tecnico_administrativo", "Técnico-Administrativo"]],
        default="tecnico_administrativo",
    )
    excluido = models.BooleanField(default=False)

    class Meta:
        db_table = "grupo_cargo_emprego"
        verbose_name = "Grupo de Cargo Emprego"
        verbose_name_plural = "Grupos de Cargo Emprego"

    def __str__(self):
        return self.nome


class CargoEmpregoUtilizadosManager(models.Manager):
    def get_queryset(self):
        try:
            return (
                super()
                .get_queryset()
                .filter(id__in=Servidor.objects.values_list("cargo_emprego", flat=True))
            )
        except ProgrammingError:
            return super().get_queryset()


class CargoEmprego(ModelPlus):
    SEARCH_FIELDS = ["codigo", "nome", "nome_amigavel"]

    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=40)
    nome_amigavel = models.CharField("Nome amigável", max_length=40, blank=True, null=False)
    descricao_sumaria = models.TextField(verbose_name="Descrição Sumária do Cargo", blank=True)
    grupo_cargo_emprego = models.ForeignKeyPlus(GrupoCargoEmprego, on_delete=models.CASCADE)
    sigla_escolaridade = models.CharField(max_length=2)
    excluido = models.BooleanField(default=False)

    # Managers
    objects = models.Manager()
    utilizados = CargoEmpregoUtilizadosManager()

    class Meta:
        db_table = "cargo_emprego"
        ordering = ["nome"]
        verbose_name = "Cargo Emprego"
        verbose_name_plural = "Cargos de Emprego"

    def __str__(self):
        return f"{self.nome} ({self.grupo_cargo_emprego.sigla}) - {self.codigo}"


class CargoEmpregoArea(ModelPlus):
    SEARCH_FIELDS = ["descricao"]

    cargo_emprego = models.ForeignKeyPlus(CargoEmprego, on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Área do Cargo Emprego"
        verbose_name_plural = "Áreas dos Cargos de Emprego"

    def __str__(self):
        return f"{self.cargo_emprego.nome} - {self.descricao}"


class Funcao(ModelPlus):
    SEARCH_FIELDS = ["codigo", "nome"]
    CODIGO_ESTAGIARIO = "ETG"
    CODIGO_FG = "FG"
    CODIGO_CD = "CD"
    CODIGO_FUC = "FUC"

    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=40)
    excluido = models.BooleanField(default=False)
    funcao_suap = models.BooleanField("Função SUAP", default=False, help_text="Essa função pode ser gerenciada dentro do SUAP?")
    funcao_siape = models.BooleanField("Função SIAPE", default=True, help_text="Essa função tem origem no SIAPE?")

    objects = FuncaoManager()

    class Meta:
        db_table = "funcao"
        verbose_name = "Função"
        verbose_name_plural = "Funções"

    def __str__(self):
        return self.nome

    @property
    def eh_substituicao_chefia(self):
        if self.codigo == Funcao.get_sigla_substituicao_chefia():
            return True
        return False

    @classmethod
    def get_codigos_funcao_ajustar_pontos(self):
        codigos = [self.CODIGO_CD, self.CODIGO_FG]
        if self.get_sigla_substituicao_chefia():
            codigos.append(self.get_sigla_substituicao_chefia())
        return codigos

    @classmethod
    def get_codigos_funcao_chefia(self):
        codigos = [
            self.CODIGO_FG,
            self.CODIGO_CD,
        ]
        if self.get_sigla_substituicao_chefia():
            codigos.append(self.get_sigla_substituicao_chefia())
        Configuracao = apps.get_model("comum", "configuracao")
        if Configuracao.get_valor_por_chave(app="rh", chave="fuc_considerado_chefia"):
            codigos.append(self.CODIGO_FUC)
        if Configuracao.get_valor_por_chave(app="rh", chave="fag_considerado_chefia") and self.get_sigla_funcao_apoio_a_gestao():
            codigos.append(self.get_sigla_funcao_apoio_a_gestao())
        return codigos

    @classmethod
    def get_sigla_substituicao_chefia(cls):
        Configuracao = apps.get_model("comum", "configuracao")
        return Configuracao.get_valor_por_chave(app="rh", chave="sigla_funcao_substituicao_chefia")

    @classmethod
    def get_sigla_funcao_apoio_a_gestao(cls):
        Configuracao = apps.get_model("comum", "configuracao")
        return Configuracao.get_valor_por_chave(app="rh", chave="sigla_funcao_apoio_gestao")


class AtividadesUsadasManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(servidor__isnull=False).distinct()

    def __str__(self):
        return self.nome


class Atividade(ModelPlus):
    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=40)
    excluido = models.BooleanField(default=False)

    DIRETOR_GERAL = "0009"
    DIRETOR = "0099"
    REITOR = "0062"

    objects = models.Manager()
    usadas = AtividadesUsadasManager()

    class Meta:
        db_table = "atividade"
        verbose_name = "Atividade"
        verbose_name_plural = "Atividades"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class ServidoresCarreiraManager(models.Manager):
    """
    Servidores sem ocorrência de exclusão.

    É utiliazdo no relatório de aniversariantes (pois exclui os falecidos) e nas
    funções gerais da app `patrimonio`.
    """

    def get_queryset(self):
        return super().get_queryset().filter(codigo__in=Situacao.situacoes_servidores_de_carreira())


class Situacao(ModelPlus):
    SEARCH_FIELDS = ("codigo", "nome", "nome_siape")

    # situações SIAPE (efetivos)
    ATIVO_PERMANENTE = "01"
    CEDIDO_REQUISITADO = "03"
    ATIVO_EM_OUTRO_ORGAO = "08"

    # situações SIAPE (temporários)
    CONTRATO_TEMPORARIO = "12"
    CONT_PROF_SUBSTITUTO = "52"
    CONTR_PROF_VISITANTE = "53"
    CONT_PROF_TEMPORARIO = "54"

    # outras situações SIAPE
    ESTAGIARIO = "66"
    ESTAGIARIO_SIGEPE = "70"

    EXERC_DESCENT_CARREI = "18"
    EXERCICIO_PROVISORIO = "19"
    COLABORADOR_PCCTAE = "41"
    COLABORADOR_ICT = "42"

    EXERC_7_ART93_8112 = "44"

    REQ_DE_OUTROS_ORGAOS = "14"
    SEM_VINCULO = "05"
    NOMEADO_CARGO_COMIS = "04"

    APOSENTADOS = "02"

    INSTITUIDOR_PENSAO = "15"
    PENSIONISTA = "84"

    SITUACOES_ATIVOS = [
        ATIVO_PERMANENTE,
        CEDIDO_REQUISITADO,
        ATIVO_EM_OUTRO_ORGAO,
        COLABORADOR_PCCTAE,
        CONT_PROF_SUBSTITUTO,
        CONT_PROF_TEMPORARIO,
        COLABORADOR_ICT,
        ESTAGIARIO,
        ESTAGIARIO_SIGEPE,
        EXERCICIO_PROVISORIO,
        CONTR_PROF_VISITANTE,
        EXERC_DESCENT_CARREI,
        NOMEADO_CARGO_COMIS,
        EXERC_7_ART93_8112,
    ]

    SITUACOES_EFETIVOS = [ATIVO_PERMANENTE, ATIVO_EM_OUTRO_ORGAO]

    SITUACOES_SUBSTITUTOS_OU_TEMPORARIOS = [CONT_PROF_SUBSTITUTO, CONT_PROF_TEMPORARIO]

    SITUACOES_TEMPORARIOS = [CONTRATO_TEMPORARIO, CONT_PROF_SUBSTITUTO, CONT_PROF_TEMPORARIO]

    SITUACOES_EFETIVOS_E_TEMPORARIOS = SITUACOES_EFETIVOS + SITUACOES_TEMPORARIOS

    SITUACOES_EM_EXERCICIO_NO_INSTITUTO = (
        ATIVO_PERMANENTE,
        CONT_PROF_SUBSTITUTO,
        CONT_PROF_TEMPORARIO,
        CONTR_PROF_VISITANTE,
        COLABORADOR_PCCTAE,
        EXERCICIO_PROVISORIO,
        COLABORADOR_ICT,
        EXERC_DESCENT_CARREI,
        EXERC_7_ART93_8112,
        NOMEADO_CARGO_COMIS,
    )

    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome_siape = models.CharField(max_length=40)
    nome = models.CharField(max_length=40)
    excluido = models.BooleanField(default=False)

    objects = models.Manager()
    servidores_de_carreira = ServidoresCarreiraManager()

    class Meta:
        db_table = "situacao"
        verbose_name = "Situação"
        verbose_name_plural = "Situações"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} - {self.codigo}"

    @staticmethod
    def situacoes_usadas_no_instituto():
        situacoes_servidores = (
            Servidor.objects.filter(situacao__isnull=False).values_list("situacao", flat=True).order_by("situacao").distinct()
        )
        return Situacao.objects.filter(id__in=situacoes_servidores)

    @staticmethod
    def situacoes_servidores_de_carreira():
        return (
            Situacao.ATIVO_PERMANENTE,
            Situacao.ATIVO_EM_OUTRO_ORGAO,
            Situacao.CONTRATO_TEMPORARIO,
            Situacao.CONT_PROF_SUBSTITUTO,
            Situacao.CONT_PROF_TEMPORARIO,
            Situacao.EXERC_DESCENT_CARREI,
            Situacao.EXERCICIO_PROVISORIO,
            Situacao.COLABORADOR_PCCTAE,
            Situacao.COLABORADOR_ICT,
            Situacao.EXERC_7_ART93_8112,
        )

    @staticmethod
    def situacoes_servidores_de_carreira_vinculada_ao_orgao():
        return (Situacao.ATIVO_PERMANENTE, Situacao.ATIVO_EM_OUTRO_ORGAO)

    @staticmethod
    def situacoes_carreira_em_exercicio_provisorio():
        return (Situacao.EXERCICIO_PROVISORIO, Situacao.COLABORADOR_PCCTAE, Situacao.COLABORADOR_ICT, Situacao.EXERC_7_ART93_8112)

    @staticmethod
    def situacoes_sem_vinculo_com_administracao_publica():
        return (Situacao.SEM_VINCULO, Situacao.NOMEADO_CARGO_COMIS)

    @staticmethod
    def situacoes_siape_estagiarios():
        return (Situacao.ESTAGIARIO, Situacao.ESTAGIARIO_SIGEPE)

    @property
    def is_temporaria(self):
        return self.codigo in self.SITUACOES_TEMPORARIOS


class JornadaTrabalho(ModelPlus):
    codigo = models.CharField(max_length=10, null=True, unique=True)  # "40"
    nome = models.CharField(max_length=40)  # "40 horas semanais"
    excluido = models.BooleanField(default=False)
    docente_peso = models.FloatField(default=1)

    _CACHE = list()

    @classmethod
    def get_jornada(cls, nome):
        if not cls._CACHE:
            cls._CACHE = list(cls.objects.all())
        for jornada in cls._CACHE:
            if jornada.nome == nome:
                return jornada
        return None

    def __str__(self):
        return self.nome

    def get_jornada_trabalho_diaria(self):
        if self.nome == "40 HORAS SEMANAIS" or self.nome == "DEDICACAO EXCLUSIVA":
            return 8
        elif self.nome == "30 HORAS SEMANAIS":
            return 6
        elif self.nome == "25 HORAS SEMANAIS":
            return 5
        elif self.nome == "20 HORAS SEMANAIS":
            return 4

    def get_jornada_trabalho_semanal(self):
        if self.nome == "40 HORAS SEMANAIS" or self.nome == "DEDICACAO EXCLUSIVA":
            return 40
        elif self.nome == "30 HORAS SEMANAIS":
            return 30
        elif self.nome == "25 HORAS SEMANAIS":
            return 25
        elif self.nome == "20 HORAS SEMANAIS":
            return 20

    class Meta:
        db_table = "jornada_trabalho"
        verbose_name = "Jornada de Trabalho"
        verbose_name_plural = "Jornadas de Trabalho"


class RegimeJuridico(ModelPlus):
    SEARCH_FIELDS = ["sigla", "nome"]

    codigo_regime = models.CharField(max_length=2, null=True, db_index=True)
    sigla = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=40)
    excluido = models.BooleanField(default=False)

    class Meta:
        db_table = "regime_juridico"

    def __str__(self):
        return self.nome


class SubgrupoOcorrencia(ModelPlus):
    """
    Subgrupos são classes pertencentes ao SUAP apenas. Esses dados não existem no SIAPE
    e forão incluídos apenas para facilitar a compreensão dos diferentes tipos de ocorrências
    """

    descricao = models.CharField(max_length=40, null=True)

    class Meta:
        db_table = "subgrupo_ocorrencia"

    def __str__(self):
        return self.descricao


class GrupoOcorrencia(ModelPlus):
    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=40)
    excluido = models.BooleanField(default=False)

    class Meta:
        db_table = "grupo_ocorrencia"
        verbose_name = "Grupo de Ocorrência"
        verbose_name_plural = "Grupos de Ocorrência"

    def __str__(self):
        return self.nome


class Ocorrencia(ModelPlus):
    REDISTRIBUICAO = "02100"
    POSSE_OUTRO_CARGO_INACUMULAVEL = "02122"

    codigo = models.CharField(max_length=5, unique=True)
    nome = models.CharField(max_length=60)
    excluido = models.BooleanField(default=False)
    grupo_ocorrencia = models.ForeignKeyPlus(GrupoOcorrencia, on_delete=models.CASCADE)
    interrompe_pagamento = models.BooleanField(default=False, blank=True)

    class Meta:
        db_table = "ocorrencia"
        verbose_name = "Ocorrência"
        verbose_name_plural = "Ocorrências"

    def __str__(self):
        return self.nome


class AfastamentoSiape(ModelPlus):
    LICENCA_TRATAMENTO_SAUDE_EST = "0084"
    LICENCA_TRATAMENTO_SAUDE_INFERIOR_15_DIAS_EST = "0270"
    HIST_CLT_LICENCA_TRATAMENTO_SAUDE = "0181"
    HIST_CLT_LICENCA_TRATAMENTO_SAUDE_1 = "0239"
    LICENCA_TRATAMENTO_SAUDE_CONVENIO_INSS = "0163"
    LICENCA_TRATAMENTO_SAUDE_CONTRIBUICAO_RGPS_15_DIAS = "0162"
    HIST_EST_L1711_52_LICENCA_TRATAMENTO_SAUDE = "0238"

    LICENCAS_TRATAMENTO_SAUDE = [
        LICENCA_TRATAMENTO_SAUDE_EST,
        LICENCA_TRATAMENTO_SAUDE_INFERIOR_15_DIAS_EST,
        HIST_CLT_LICENCA_TRATAMENTO_SAUDE,
        HIST_CLT_LICENCA_TRATAMENTO_SAUDE_1,
        LICENCA_TRATAMENTO_SAUDE_CONVENIO_INSS,
        LICENCA_TRATAMENTO_SAUDE_CONTRIBUICAO_RGPS_15_DIAS,
        HIST_EST_L1711_52_LICENCA_TRATAMENTO_SAUDE,
    ]

    AFASTAMENTO_STRICTU_SENSU = "0028"
    LICENCA_CAPACITACAO_3_MESES = "0081"

    FALTAS = 1
    ATRASOS = 2
    LICENCA_INCENTIVADA = 3
    OUTROS = 4

    TIPO_AFASTAMENTO_CHOICES = ((FALTAS, "Faltas"), (ATRASOS, "Atrasos"), (LICENCA_INCENTIVADA, "Licença Incentivada"), (OUTROS, "Outros"))
    codigo = models.CharField(max_length=4, unique=True, db_index=True)
    sigla = models.CharField(max_length=10)
    nome = models.CharField(max_length=60)
    tipo = models.PositiveIntegerField("Tipos de Afastamentos", choices=TIPO_AFASTAMENTO_CHOICES)
    interrompe_pagamento = models.BooleanField("Interrompe pagamento", default=False, blank=True)
    interrompe_tempo_servico = models.BooleanField("Interrompe tempo de serviço", default=False, blank=True)
    excluido = models.BooleanField("Excluído", default=False)
    #
    # demanda 1062 - afastamentos que suspendem estágio probatório
    # OFÍCIO-CIRCULAR Nº 9/2021/DAJ/COLEP/CGGP/SAA-MEC
    suspende_estagio_probatorio = models.BooleanField("Suspende estágio probatório", default=False, blank=True)

    #
    # FIXME: remover essa redefinição do 'save' caso o atributo 'interrompe_tempo_servico' seja setado no 'extrator'
    def save(self, *args, **kwargs):
        #
        # no caso de novo registro (via extrator do SIAPE, espera-se),
        # seta o atributo interrompe_tempo_servico tendo o mesmo valor de interrompe_pagamento
        if not self.id:
            self.interrompe_tempo_servico = self.interrompe_pagamento
        #
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    class Meta:
        verbose_name = "Afastamentos SIAPE"
        verbose_name_plural = "Afastamentos SIAPE"


class ServidorAfastamento(ModelPlus):
    servidor = models.ForeignKeyPlus("rh.Servidor", editable=False, on_delete=models.CASCADE)
    afastamento = models.ForeignKeyPlus(AfastamentoSiape, editable=False, on_delete=models.CASCADE)

    data_inicio = models.DateField(null=True, editable=False, db_index=True)
    data_termino = models.DateField(null=True, blank=True, db_index=True)
    quantidade_dias_afastamento = models.PositiveIntegerFieldPlus("Quantidade de dias afastamento", default=0)
    tem_efeito_financeiro = models.BooleanField("Tem efeito financeiro", null=False, blank=False, default=False)
    cancelado = models.BooleanField("Cancelado", null=False, blank=False, default=False)

    class Meta:
        unique_together = ("servidor", "afastamento", "data_inicio")
        index_together = [["servidor", "afastamento", "data_inicio"]]
        verbose_name = "Afastamento SIAPE do Servidor"
        verbose_name_plural = "Afastamentos SIAPE dos Servidores"

    def __str__(self):
        return f"{self.servidor} - {self.afastamento.nome} ({self.data_inicio} à {self.data_termino})"

    def save(self, *args, **kwargs):
        self.quantidade_dias_afastamento = self.get_qtde_dias().days
        super().save(*args, **kwargs)

    def get_qtde_dias(self):
        if not self.data_termino:
            return datetime.timedelta(1)

        dt_termino = self.data_termino
        dt_inicio = self.data_inicio

        if isinstance(dt_inicio, datetime.datetime):
            dt_inicio = datetime.datetime.date(dt_inicio)
        if isinstance(dt_termino, datetime.datetime):
            dt_termino = datetime.datetime.date(dt_termino)

        return dt_termino - dt_inicio

    @classmethod
    def get_afastamentos(cls, servidor, data_inicial, data_final):
        return cls.objects.filter(servidor=servidor, data_inicio__lte=data_final, data_termino__gte=data_inicial, cancelado=False)


class DiplomaLegal(ModelPlus):
    codigo = models.CharField(max_length=10, null=True, unique=True)
    nome = models.CharField(max_length=40)
    sigla = models.CharField(max_length=10)
    excluido = models.BooleanField(default=False)

    class Meta:
        db_table = "diploma_legal"
        verbose_name = "Diploma Legal"
        verbose_name_plural = "Diplomas Legais"

    def __str__(self):
        return self.sigla


class ServidorOcorrencia(ModelPlus):
    servidor = models.ForeignKeyPlus("rh.Servidor", editable=False, on_delete=models.CASCADE)
    ocorrencia = models.ForeignKeyPlus(Ocorrencia, editable=False, on_delete=models.CASCADE)
    subgrupo = models.ForeignKeyPlus(SubgrupoOcorrencia, null=True, editable=False, on_delete=models.CASCADE)
    diploma_legal = models.ForeignKeyPlus(DiplomaLegal, null=True, editable=False, on_delete=models.CASCADE)
    diploma_legal_data = models.DateField(null=True, editable=False)
    diploma_legal_num = models.CharField(max_length=10, editable=False)
    data = models.DateField(null=True, editable=False, db_index=True)
    data_termino = models.DateField(null=True, blank=True, db_index=True)
    quantidade_dias_ocorrencia = models.PositiveIntegerFieldPlus("Quantidade de dias ocorrência", default=0)

    class Meta:
        db_table = "servidor_ocorrencia"
        verbose_name = "Ocorrência de Servidor"
        verbose_name_plural = "Ocorrências de Servidores"

    def save(self, *args, **kwargs):
        self.quantidade_dias_ocorrencia = self.get_qtde_dias().days
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            "\n"
            + "\n".join(
                [
                    ": ".join(["servidor\t", self.servidor.nome]),
                    ": ".join(["ocorrencia\t", self.ocorrencia.nome]),
                    ": ".join(["grupo_ocorrencia", self.ocorrencia.grupo_ocorrencia.nome]),
                    ": ".join(["subgrupo\t", self.subgrupo and self.subgrupo.descricao or "-"]),
                    ": ".join(["data\t\t", str(self.data)]),
                    ": ".join(["termino\t\t", str(self.data_termino)]),
                ]
            )
            + "\n\n"
        )

    def get_qtde_dias(self):
        if not self.data_termino:
            return datetime.timedelta(1)

        dt_data = self.data
        dt_termino = self.data_termino

        if isinstance(dt_data, datetime.datetime):
            dt_data = datetime.datetime.date(dt_data)
        if isinstance(dt_termino, datetime.datetime):
            dt_termino = datetime.datetime.date(dt_termino)

        return dt_termino - dt_data

    @classmethod
    def get_afastamentos(cls, servidor, data_inicial, data_final):
        # TODO:
        # Este método poderia receber o `grupo_ocorrencia` como parâmetro, mas
        # teria que tratar os casos onde `data_termino` é `None`.
        return cls.objects.filter(
            servidor=servidor, ocorrencia__grupo_ocorrencia__nome="AFASTAMENTO", data__lte=data_final, data_termino__gte=data_inicial
        )


class ServidorReativacaoTemporaria(ModelPlus):
    servidor = models.ForeignKeyPlus("rh.Servidor", verbose_name="Servidor")
    data_inicio = models.DateField(
        "Data de Início",
        null=False,
    )
    data_fim = models.DateField("Data de Fim", null=False)

    class Meta:
        verbose_name = "Reativação Temporária de Servidor"
        verbose_name_plural = "Reativações Temporárias dos Servidores"

    def __str__(self):
        return f"Reativação Temporária de {self.servidor} - {self.data_inicio} à {self.data_fim}"


class NivelEscolaridade(ModelPlus):
    nome = models.CharField(max_length=45)
    codigo = models.CharField(max_length=10, null=True, unique=True)
    descricao = models.CharField(max_length=60)
    excluido = models.BooleanField(default=False)

    class Meta:
        db_table = "nivel_escolaridade"
        verbose_name = "Nível de Escolaridade"
        verbose_name_plural = "Níveis de Escolaridade"

    def __str__(self):
        return self.nome


class Titulacao(ModelPlus):
    nome = models.CharField(max_length=40, blank=True)
    codigo = models.CharField(max_length=4, blank=True, unique=True)
    titulo_masculino = models.CharFieldPlus("Título Masculino", blank=True)
    titulo_feminino = models.CharFieldPlus("Título Feminino", blank=True)

    class Meta:
        db_table = "titulacao"
        ordering = ["nome"]
        verbose_name = "Titulação"
        verbose_name_plural = "Titulações"

    def __str__(self):
        return self.nome


class Banco(ModelPlus):
    codigo = models.CharField(max_length=3)
    sigla = models.CharField(max_length=15)
    nome = models.CharField(max_length=30)
    excluido = models.BooleanField(default=False)

    def __str__(self):
        return self.nome

    def get_ext_combo_template(self):
        return f'{self.codigo} - {self.nome}'


class ServidorFuncaoHistoricoQueryset(QuerySet):
    def atuais(self):
        hoje = datetime.date.today()
        return self.filter(Q(data_inicio_funcao__lte=hoje), Q(data_fim_funcao__gte=hoje) | Q(data_fim_funcao__isnull=True))

    def substitutos(self):
        return self.filter(funcao__codigo=Funcao.get_sigla_substituicao_chefia())


class ServidorFuncaoHistoricoManager(models.Manager):
    def get_query_set(self):
        return self.get_queryset()

    def get_queryset(self):
        qs = ServidorFuncaoHistoricoQueryset(self.model, using=self._db)
        return qs

    def atuais(self):
        return self.get_queryset().atuais()

    def substitutos(self):
        return self.get_queryset().substitutos()


class ServidorFuncaoHistorico(ModelPlus):
    FUNCOES_LIBERADO_FREQUENCIA = ["CD"]
    NIVEIS_LIBERADO_FREQUENCIA = ["1", "2", "3"]

    servidor = models.ForeignKeyPlus("rh.Servidor", null=False, on_delete=models.CASCADE)
    data_inicio_funcao = models.DateFieldPlus(null=False, blank=False, db_index=True, verbose_name="Data de Início da Função")
    data_fim_funcao = models.DateFieldPlus(null=True, blank=False, verbose_name="Data de Fim da Função")
    atividade = models.ForeignKeyPlus("rh.Atividade", null=True, on_delete=models.CASCADE)
    funcao = models.ForeignKeyPlus("rh.Funcao", null=False, on_delete=models.CASCADE, verbose_name="Função")
    nivel = models.CharField(max_length=4, null=True, blank=True, verbose_name="Nível")
    setor = models.ForeignKeyPlus("rh.Setor", null=False, blank=False, on_delete=models.CASCADE)
    setor_suap = models.ForeignKeyPlus(
        "rh.Setor", null=True, blank=False, related_name="setor_suap", on_delete=models.CASCADE, verbose_name="Setor SUAP"
    )
    nome_amigavel = models.CharFieldPlus(verbose_name="Nome Amigável", default="")
    atualiza_pelo_extrator = models.BooleanField(verbose_name="Atualizar pelo extrator", default=True)

    objects = ServidorFuncaoHistoricoManager()

    def __str__(self):
        data_fim = self.data_fim_funcao.strftime("%d/%m/%Y") if self.data_fim_funcao else "Atual"
        return "{} : {} - Setor SIAPE: {} - de {} à {}".format(
            self.funcao_display, self.servidor, self.setor, self.data_inicio_funcao.strftime("%d/%m/%Y"), data_fim
        )

    class Meta:
        unique_together = ("servidor", "data_inicio_funcao")
        verbose_name = "Histórico de Função do Servidor"
        verbose_name_plural = "Histórico de Funções do Servidor"

    @property
    def funcao_display(self):
        return "{}{} - {}".format(self.funcao and self.funcao.codigo or "", self.nivel or "", self.setor_suap or "")

    @property
    def get_nome_amigavel(self):
        return f'{self.nome_amigavel or (self.atividade and self.atividade.nome) or ""} {self.funcao_display}'

    @property
    def estah_ativa(self):
        hoje = datetime.date.today()
        if self.data_inicio_funcao > hoje:
            return False
        return not self.data_fim_funcao or self.data_fim_funcao >= hoje

    @atomic()
    def save(self, *args, **kwargs):
        Configuracao = apps.get_model("comum", "configuracao")
        configuracao_setor = Configuracao.get_valor_por_chave(app="comum", chave="setores")
        if configuracao_setor == "SIAPE":
            self.setor_suap = self.setor

        super().save(*args, **kwargs)

        if Papel.objects.filter(papel_content_id__isnull=True).exists():
            raise Exception(
                "Existem registros de Papel sem CargoEmprego ou Funcao definidos. "
                'Execute o command "importar_funcao_servidor_atualizar_genericfk" para '
                "resolver o problema."
            )

        if self.nome_amigavel:
            detalhamento = f"{self.nome_amigavel} - {self.funcao_display}"
        elif self.atividade:
            detalhamento = f"{self.atividade.nome} - {self.funcao_display}"
        else:
            detalhamento = self.funcao_display
        kwargs = dict(
            detalhamento=detalhamento,
            portaria="",
            descricao=f"{self.funcao.nome} - {self.funcao.codigo}",
            setor_suap=self.setor_suap,
            data_fim=self.data_fim_funcao,
            tipo_papel=Papel.TIPO_PAPEL_FUNCAO,
        )
        servidor = Servidor.objects.get(pk=self.servidor.pk)
        papel, criou = Papel.objects.update_or_create(
            pessoa=servidor.pessoafisica_ptr,
            data_inicio=self.data_inicio_funcao,
            papel_content_type=ContentType.objects.get_for_model(self.funcao),
            papel_content_id=self.funcao.id,
            defaults=kwargs,
        )


# ---- MAPA TEMPO DE SERVIÇO -----
class PCA(ModelPlus):
    SEARCH_FIELDS = ["servidor__nome", "servidor__matricula"]

    servidor = models.ForeignKeyPlus("rh.Servidor", null=False, blank=False, on_delete=models.CASCADE)
    servidor_matricula_crh = models.CharField(
        max_length=8, null=False, blank=False
    )  # CO-CRH-PCA - é o mesmo dado de rh.Servidor.matricula_crh
    servidor_vaga_pca = models.CharField(
        max_length=7, null=False, blank=False
    )  # CO-VAGA-SIAPE-PCA - é o mesmo dado de rh.Servidor.codigo_vaga
    # ligacao pca --> posicionamentos
    codigo_pca = models.CharField(
        max_length=11, null=False, blank=False, unique=True, db_index=True
    )  # CH-PCA - é o mesmo dado de rh.PosicionamentoPCA.codigo_pca_posicionamento
    # cargo
    cargo_pca = models.ForeignKeyPlus("rh.CargoEmprego", null=False, blank=False, on_delete=models.CASCADE)  # CH-CARGO-PCA

    # entrada
    forma_entrada_pca = models.ForeignKeyPlus(
        "rh.FormaProvimentoVacancia", related_name="forma_entrada", null=True, on_delete=models.CASCADE
    )  # CO-FORMA-ENTRADA-PCA
    data_entrada_pca = models.DateFieldPlus(null=False, blank=False, db_index=True)  # DA-ENTRADA-PCA
    texto_entrada_pca = models.CharField(max_length=60, blank=True)  # TX-ENTRADA-PCA
    # vacância
    forma_vacancia_pca = models.ForeignKeyPlus(
        "rh.FormaProvimentoVacancia", related_name="forma_vacancia", null=True, on_delete=models.CASCADE
    )  # CO-FORMA-VACANCIA-PCA
    data_vacancia_pca = models.DateFieldPlus(blank=True)  # DA-VACANCIA-PCA
    texto_vacancia_pca = models.CharField(max_length=60, blank=True)  # TX-VACANCIA-PCA

    class Meta:
        ordering = ["-data_entrada_pca"]
        verbose_name = "Provimento de Cargo"
        verbose_name_plural = "Provimentos de Cargos"

    def __str__(self):
        return f'Provimento de Cargo {self.servidor} - {self.data_entrada_pca.strftime("%d/%m/%Y")}'

    @property
    def inicio_exercicio_pca(self):
        # retorna uma data
        data_inicio_exercicio_pca = None
        if self.posicionamentopca_set.all().exists():
            data_inicio_exercicio_pca = (
                self.posicionamentopca_set.all().order_by("data_inicio_posicionamento_pca")[0].data_inicio_posicionamento_pca
            )  # usa o posicionamento mais antigo (índice 0)
        if data_inicio_exercicio_pca and (data_inicio_exercicio_pca - self.data_entrada_pca).days <= 15:
            return data_inicio_exercicio_pca
        return self.data_entrada_pca

    @property
    def fim_exercicio_pca(self):
        # retorna uma data
        return self.data_vacancia_pca

    @property
    def fim_exercicio_pca_or_None(self):
        data_fim = self.fim_exercicio_pca
        if (data_fim is not None) and (data_fim.year == 2500):
            data_fim = None
        return data_fim

    def tempo_servico_pca(self, ficto=False, data_referencia=None):
        tempo_servico = datetime.timedelta(0)
        data_inicio_exercicio_descontada = False
        for regime in self.regimejuridicopca_set.all().order_by("data_inicio_regime_juridico_pca"):
            tempo_servico += regime.tempo_servico(ficto, data_referencia)
            if not data_inicio_exercicio_descontada:
                if ficto:
                    # dedução proporcional ao fator do regime jurídico
                    tempo_servico -= datetime.timedelta(
                        (self.inicio_exercicio_pca - regime.data_inicio_regime_juridico_pca).days
                        * float(regime.valor_fator_tempo_regime_juridico_pca)
                    )
                else:
                    tempo_servico -= self.inicio_exercicio_pca - regime.data_inicio_regime_juridico_pca
                data_inicio_exercicio_descontada = True
        return tempo_servico  # um timedelta que representa o tempo de servico

    @classmethod
    def montar_timeline(cls, pcas):
        timeline = OrderedDict()
        for pca in pcas:
            if pca.data_entrada_pca:
                descricao_entrada_pca = (
                    "<h4>Entrada no PCA</h4> <dl><dt>Forma entrada: </dt><dd>{}</dd><dt>Cargo: </dt><dd>{}</dd></dl>".format(
                        pca.forma_entrada_pca, pca.cargo_pca
                    )
                )
                if timeline.get(pca.data_entrada_pca):
                    if timeline[pca.data_entrada_pca].get("eventos"):
                        evento = OrderedDict()
                        evento["descricao"] = descricao_entrada_pca
                        evento["css"] = "success"
                        timeline[pca.data_entrada_pca]["eventos"].append(evento)
                    else:
                        evento = OrderedDict()
                        evento["descricao"] = descricao_entrada_pca
                        evento["css"] = "success"
                        timeline[pca.data_entrada_pca]["eventos"] = [evento]
                    timeline[pca.data_entrada_pca]["css"] = "success"

                else:
                    timeline[pca.data_entrada_pca] = OrderedDict()
                    timeline[pca.data_entrada_pca]["eventos"] = []
                    evento = OrderedDict()
                    evento["descricao"] = descricao_entrada_pca
                    evento["css"] = "success"
                    timeline[pca.data_entrada_pca]["eventos"].append(evento)
                    timeline[pca.data_entrada_pca]["css"] = "success"

            for jornada_trabalho in pca.jornadatrabalhopca_set.all().order_by("data_inicio_jornada_trabalho_pca"):
                horas_semanais = "-"
                if jornada_trabalho.qtde_jornada_trabalho_pca:
                    if jornada_trabalho.qtde_jornada_trabalho_pca == "99":
                        horas_semanais = "Dedicação Exclusiva"
                    else:
                        horas_semanais = f"{jornada_trabalho.qtde_jornada_trabalho_pca} h"
                descricao_jornada_trabalho = "<h4>Início Jornada de Trabalho</h4> <dl><dt>Horas Semanais:</dt><dd>{}</dd></dl>".format(
                    horas_semanais
                )
                evento = OrderedDict(dict(descricao=descricao_jornada_trabalho, css="extra"))

                if timeline.get(jornada_trabalho.data_inicio_jornada_trabalho_pca):
                    if timeline[jornada_trabalho.data_inicio_jornada_trabalho_pca].get("eventos"):
                        timeline[jornada_trabalho.data_inicio_jornada_trabalho_pca]["eventos"].append(evento)
                    else:
                        timeline[jornada_trabalho.data_inicio_jornada_trabalho_pca]["eventos"] = [evento]
                else:
                    timeline[jornada_trabalho.data_inicio_jornada_trabalho_pca] = OrderedDict()
                    timeline[jornada_trabalho.data_inicio_jornada_trabalho_pca]["eventos"] = []
                    timeline[jornada_trabalho.data_inicio_jornada_trabalho_pca]["eventos"].append(evento)

                if not timeline[jornada_trabalho.data_inicio_jornada_trabalho_pca].get("css"):
                    timeline[jornada_trabalho.data_inicio_jornada_trabalho_pca]["css"] = "info"

            for regime in pca.regimejuridicopca_set.all().order_by("data_inicio_regime_juridico_pca"):
                regime_desc = "-"
                regime_nome = "Regime jurídico"
                valor_fator = regime.valor_fator_tempo_regime_juridico_pca
                if regime.regime_juridico:
                    regime_desc = regime.regime_juridico.sigla
                    regime_nome = regime.regime_juridico.nome.capitalize()

                descricao_regime = "<h4>Início: {} ({})</h4> <dl><dt>Fator:</dt><dd>{}</dd></dl>".format(
                    regime_nome, regime_desc, valor_fator
                )
                evento = OrderedDict(dict(descricao=descricao_regime, css="alert"))
                if timeline.get(regime.data_inicio_regime_juridico_pca):
                    if timeline[regime.data_inicio_regime_juridico_pca].get("eventos"):
                        timeline[regime.data_inicio_regime_juridico_pca]["eventos"].append(evento)
                    else:
                        timeline[regime.data_inicio_regime_juridico_pca]["eventos"] = [evento]
                else:
                    timeline[regime.data_inicio_regime_juridico_pca] = OrderedDict()
                    timeline[regime.data_inicio_regime_juridico_pca]["eventos"] = []
                    timeline[regime.data_inicio_regime_juridico_pca]["eventos"].append(evento)

                if not timeline[regime.data_inicio_regime_juridico_pca].get("css"):
                    timeline[regime.data_inicio_regime_juridico_pca]["css"] = "alert"

            for posicionamento in pca.posicionamentopca_set.all().order_by("data_inicio_posicionamento_pca"):
                descricao = (
                    f"<h4>Início de Exercício</h4><p>{posicionamento.forma_entrada}</p>"
                    if posicionamento.forma_entrada.codigo in ["009", "128"]
                    else f"<h4>Mudança de Posicionamento PCA</h4><p>{posicionamento.forma_entrada}</p>"
                )
                evento = OrderedDict(dict(descricao=descricao, css="info"))

                if timeline.get(posicionamento.data_inicio_posicionamento_pca):
                    if timeline[posicionamento.data_inicio_posicionamento_pca].get("eventos"):
                        timeline[posicionamento.data_inicio_posicionamento_pca]["eventos"].append(evento)
                    else:
                        timeline[posicionamento.data_inicio_posicionamento_pca]["eventos"] = [evento]
                else:
                    timeline[posicionamento.data_inicio_posicionamento_pca] = OrderedDict()
                    timeline[posicionamento.data_inicio_posicionamento_pca]["eventos"] = []
                    timeline[posicionamento.data_inicio_posicionamento_pca]["eventos"].append(evento)

                if not timeline[posicionamento.data_inicio_posicionamento_pca].get("css"):
                    timeline[posicionamento.data_inicio_posicionamento_pca]["css"] = "info"

            if pca.data_vacancia_pca and pca.data_vacancia_pca.year != 2500:
                descricao_vacancia_pca = (
                    "<h4>Vacância no PCA</h4> <dl><dt>Forma vacância:</dt><dd>{}</dd><dt>Cargo: </dt><dd>{}</dd></dl>".format(
                        pca.forma_vacancia_pca, pca.cargo_pca
                    )
                )
                if timeline.get(pca.data_vacancia_pca):
                    if timeline[pca.data_vacancia_pca].get("eventos"):
                        evento = OrderedDict()
                        evento["descricao"] = descricao_vacancia_pca
                        evento["css"] = "error"
                        timeline[pca.data_vacancia_pca]["eventos"].append(evento)
                    else:
                        evento = OrderedDict()
                        evento["descricao"] = descricao_vacancia_pca
                        evento["css"] = "error"
                        timeline[pca.data_vacancia_pca]["eventos"] = [evento]
                else:
                    timeline[pca.data_vacancia_pca] = OrderedDict()
                    timeline[pca.data_vacancia_pca]["eventos"] = []
                    evento = OrderedDict()
                    evento["descricao"] = descricao_vacancia_pca
                    evento["css"] = "error"
                    timeline[pca.data_vacancia_pca]["eventos"].append(evento)

                timeline[pca.data_vacancia_pca]["css"] = "error"
        timeline = sorted(timeline.items(), key=lambda x: x[0])
        return OrderedDict(timeline)


class RegimeJuridicoPCA(ModelPlus):
    pca = models.ForeignKeyPlus("rh.PCA", on_delete=models.CASCADE)
    regime_juridico = models.ForeignKeyPlus("rh.RegimeJuridico", null=True, on_delete=models.CASCADE)
    codigo_regime_juridico_pca = models.CharField(max_length=2)  # CO-REGIME-JURIDICO-PCA - é o mesmo dado de rh.RegimeJuridico.codigo
    data_inicio_regime_juridico_pca = models.DateFieldPlus(db_index=True)  # DA-IN-REGIME-JURIDICO-PCA
    data_fim_regime_juridico_pca = models.DateFieldPlus(db_index=True)  # DA-FIM-REGIME-JURIDICO-PCA
    valor_fator_tempo_regime_juridico_pca = models.DecimalFieldPlus()  # VA-FATOR-TEMPO-REGIME-PCA

    class Meta:
        verbose_name = "Regime Jurídico do PCA"
        verbose_name_plural = "Regimes Jurídicos do PCA"

    @property
    def data_fim_regime_juridico_pca_or_None(self):
        data_fim = self.data_fim_regime_juridico_pca
        if (data_fim is not None) and (data_fim.year == 2500):
            data_fim = None
        return data_fim

    def tempo_servico(self, ficto=False, data_referencia=None):
        data_fim = self.data_fim_regime_juridico_pca_or_None or datetime.date.today()
        if data_referencia:
            if data_referencia < self.data_inicio_regime_juridico_pca:
                return datetime.timedelta(0)
            elif data_referencia < data_fim:
                data_fim = data_referencia

        tempo_servico = data_fim - self.data_inicio_regime_juridico_pca + datetime.timedelta(1)
        # afastamentos durante o período do regime
        #        afastamentos = ServidorOcorrencia.objects.filter(servidor=self.pca.servidor,
        #                                                         ocorrencia__interrompe_pagamento=True,
        #                                                         data__gte=self.data_inicio_regime_juridico_pca,
        #                                                         data_termino__lte=data_fim)
        afastamentos = ServidorAfastamento.objects.filter(
            servidor=self.pca.servidor,
            afastamento__interrompe_tempo_servico=True,
            data_inicio__gte=self.data_inicio_regime_juridico_pca,
            data_termino__lte=data_fim,
            cancelado=False,
        )
        total_dias_afastamentos = datetime.timedelta(0)
        for afastamento in afastamentos:
            afastamento_data_fim = afastamento.data_termino
            afastamento_data_inicio = afastamento.data_inicio
            if afastamento_data_inicio < self.data_inicio_regime_juridico_pca:
                afastamento_data_inicio = self.data_inicio_regime_juridico_pca
            if afastamento_data_fim > self.data_fim_regime_juridico_pca:
                afastamento_data_fim = self.data_fim_regime_juridico_pca
            total_dias_afastamentos += (afastamento_data_fim - afastamento_data_inicio) + datetime.timedelta(1)

        # aplica os afastamentos ao tempo calculado, NÃO considerando o fator
        tempo_servico -= datetime.timedelta(total_dias_afastamentos.days)
        if ficto:
            # aplica o fator ao tempo calculado
            # aplica os afastamentos ao tempo calculado, considerando o fator novamente
            tempo_servico = datetime.timedelta(tempo_servico.days * float(self.valor_fator_tempo_regime_juridico_pca))

        return tempo_servico

    def __str__(self):
        return "{} {} - {} à {} - {}".format(
            self.codigo_regime_juridico_pca,
            self.regime_juridico or "",
            self.data_inicio_regime_juridico_pca,
            self.data_fim_regime_juridico_pca,
            self.valor_fator_tempo_regime_juridico_pca,
        )


class JornadaTrabalhoPCA(ModelPlus):
    pca = models.ForeignKeyPlus("rh.PCA", on_delete=models.CASCADE)
    qtde_jornada_trabalho_pca = models.CharField(max_length=2)  # QT-JORNADA-TRABALHO-PCA
    data_inicio_jornada_trabalho_pca = models.DateFieldPlus()  # DA-INI-JORNADA-TRABALHO-PCA
    data_fim_jornada_trabalho_pca = models.DateFieldPlus()  # DA-FIM-JORNADA-TRABALHO-PCA

    class Meta:
        verbose_name = "Jornada de Trabalho do PCA"
        verbose_name_plural = "Jornadas de Trabalho do PCA"

    def __str__(self):
        return "{} - {} - {} à {}".format(
            self.pca, self.qtde_jornada_trabalho_pca, self.data_inicio_jornada_trabalho_pca, self.data_fim_jornada_trabalho_pca
        )


class PosicionamentoPCA(ModelPlus):
    pca = models.ForeignKeyPlus("rh.PCA", null=False, on_delete=models.CASCADE)
    codigo_pca_posicionamento = models.CharField(
        max_length=11, db_index=True
    )  # CH-PCA-POSICIONAMENTO - é o mesmo dado de rh.PCA.codigo_pca
    codigo_posicionamento_pca = models.CharField(max_length=9, null=False, db_index=True)  # CH-POSICIONAMENTO-PCA
    forma_entrada = models.ForeignKeyPlus("rh.FormaProvimentoVacancia", on_delete=models.CASCADE)  # CO-FORMA-ENTRADA-POS-PCA
    data_inicio_posicionamento_pca = models.DateFieldPlus(db_index=True)  # DA-INI-POSICIONAMENTO-PCA
    data_fim_posicionamento_pca = models.DateFieldPlus()  # DA-FIM-POSICIONAMENTO-PCA

    def __str__(self):
        return "{} - {} - {} à {}".format(
            self.pca, self.codigo_posicionamento_pca, self.data_inicio_posicionamento_pca, self.data_fim_posicionamento_pca
        )

    def data_fim_posicionamento_pca_or_None(self):
        data_fim = self.data_fim_posicionamento_pca
        if (data_fim is not None) and (data_fim.year == 2500):
            data_fim = None
        return data_fim

    class Meta:
        verbose_name = "Posicionamento no PCA"
        verbose_name_plural = "Posicionamentos no PCA"
        unique_together = ("codigo_pca_posicionamento", "codigo_posicionamento_pca", "forma_entrada", "data_inicio_posicionamento_pca")
        ordering = ["-data_inicio_posicionamento_pca"]


class FormaProvimentoVacancia(ModelPlus):
    SEARCH_FIELDS = ["codigo", "descricao"]

    CODIGO_PROGRESSAO = "046"
    CODIGO_POSSE_EM_OUTRO_CARGO_INACUMULADO = "611"
    CODIGO_REDISTRIBUICAO = "007"

    codigo = models.CharField(max_length=10, unique=True)
    descricao = models.CharField(max_length=40)

    class Meta:
        verbose_name = "Jornada de Trabalho do PCA"
        verbose_name_plural = "Jornadas de Trabalho do PCA"

    def __str__(self):
        return f"{self.descricao}"


class Instituicao(ModelPlus):
    SEARCH_FIELDS = ["nome"]

    nome = models.CharField("Instituição", max_length=150)
    ativo = models.BooleanField("Ativo", default=True)
    unidade_gestora = models.IntegerField("Unidade Gestora", null=True)
    uasg = models.IntegerField("UASG", null=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Instituição"
        verbose_name_plural = "Instituições"
        unique_together = ("nome",)

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return f"/rh/instituicao/{self.pk:d}/"


class AvaliadorExternosManager(models.Manager):
    def get_queryset(self):
        from comum.models import Vinculo

        return super(self.__class__, self).get_queryset().filter(vinculo__tipo_relacionamento=ContentType.objects.get(Vinculo.PRESTADOR))


class AvaliadorInternosManager(models.Manager):
    def get_queryset(self):
        from comum.models import Vinculo

        return super(self.__class__, self).get_queryset().filter(vinculo__tipo_relacionamento=ContentType.objects.get(Vinculo.SERVIDOR))


class Avaliador(ModelPlus):
    SEARCH_FIELDS = ["vinculo__pessoa__nome", "vinculo__pessoa__pessoafisica__cpf", "matricula_siape", "numero_documento_identificacao", "pis_pasep"]

    TIPOCONTA_CONTACORRENTE = "Conta Corrente"
    TIPOCONTA_POUPANCA = "Conta Poupança"
    TIPOCONTA_CHOICES = ((TIPOCONTA_CONTACORRENTE, "Conta Corrente"), (TIPOCONTA_POUPANCA, "Conta Poupança"))
    TELEFONE_CELULAR = "Telefone Celular"
    TELEFONE_RESIDENCIAL = "Telefone Residencial"
    TELEFONE_COMERCIAL = "Telefone Comercial"

    vinculo = models.OneToOneField("comum.Vinculo", on_delete=models.CASCADE)
    ativo = models.BooleanField("Ativo", default=True, help_text="Somente avaliadores com situação ativa podem avaliar")
    email_contato = models.EmailField("Email para Contato", blank=True)
    titulacao = models.ForeignKeyPlus("rh.Titulacao", null=True, blank=True, on_delete=models.CASCADE)
    padrao_vencimento = models.ForeignKeyPlus("rh.PadraoVencimento", null=True, blank=True, on_delete=models.CASCADE)

    padrao = models.BooleanField("Ativo", default=True, help_text="Somente avaliadores com situação ativa podem avaliar")

    matricula_siape = models.CharField("Matrícula SIAPE", max_length=50)
    instituicao_origem = models.ForeignKeyPlus(
        "rh.Instituicao", blank=True, null=True, verbose_name="Instituição", on_delete=models.CASCADE
    )

    numero_documento_identificacao = models.CharField("Número do Documento de Identificação", max_length=50, help_text="Somente números")
    emissor_documento_identificacao = models.CharField("Emissor do Documento de Identificação", max_length=50)
    pis_pasep = models.CharField("PIS/PASEP", max_length=50)

    endereco_municipio = models.CharFieldPlus("Município", blank=True)
    endereco_logradouro = models.CharFieldPlus(blank=True)
    endereco_numero = models.CharField("Nº", max_length=50, blank=True)
    endereco_complemento = models.CharFieldPlus(blank=True)
    endereco_bairro = models.CharFieldPlus(blank=True)
    endereco_cep = models.CharField("CEP", max_length=9, blank=True)

    banco = models.ForeignKeyPlus("rh.Banco", blank=True, null=True, verbose_name="Bancos", on_delete=models.CASCADE)
    numero_agencia = models.CharField("Número da Agência", max_length=50, help_text="Ex: 3293-X")
    tipo_conta = models.CharField("Tipo da Conta", max_length=50, choices=TIPOCONTA_CHOICES)
    numero_conta = models.CharField("Número da Conta", max_length=50, help_text="Ex: 23384-6")
    operacao = models.CharField("Operação", max_length=50, blank=True)

    objects = models.Manager()
    externos = AvaliadorExternosManager()
    internos = AvaliadorInternosManager()

    class Meta:
        verbose_name = "Avaliador Externo"
        verbose_name_plural = "Avaliadores"

    def __str__(self):
        pessoa_fisica = self.vinculo.user.get_profile()
        if self.eh_interno():
            return f"{pessoa_fisica.nome} ({self.vinculo.relacionamento.matricula})"
        else:
            return f"{pessoa_fisica.nome} - {anonimizar_cpf(pessoa_fisica.cpf)}"

    def get_absolute_url(self):
        return f"/rh/avaliador/{self.pk:d}/"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.eh_interno():
            grupo = Group.objects.get(name="Avaliador Interno")
        elif self.eh_externo():
            grupo = Group.objects.get(name="Avaliador Externo")

        if self.ativo and grupo:
            self.vinculo.user.groups.add(grupo)
        else:
            self.vinculo.user.groups.remove(grupo)

    def get_matricula(self):
        if self.eh_interno():
            return self.eh_interno().matricula
        if self.eh_externo():
            return self.matricula_siape

    def qtd_avaliacoes_realizadas(self, avaliacao):
        if "rsc" in settings.INSTALLED_APPS:
            Avaliacao = apps.get_model("rsc", "Avaliacao")
            if isinstance(avaliacao, Avaliacao):
                return self.avaliacao_avaliador_rsc.filter(status__in=[Avaliacao.DEFERIDA, Avaliacao.INDEFERIDA]).count()

        if "professor_titular" in settings.INSTALLED_APPS:
            Avaliacao = apps.get_model("professor_titular", "Avaliacao")
            if isinstance(avaliacao, Avaliacao):
                return self.avaliacao_avaliador_titular.filter(status__in=[Avaliacao.FINALIZADA]).count()

    """
    Método que verifica a quantidade de avaliações realizadas no ano pelo avaliador
    - se o parametro avaliacao for passado, será verificada a instância e mostrada apenas a quantidade desta,
     caso contrario, irá mostra a soma de todas as avaliações
    """

    def avaliacoes_realizadas_no_ano(self, avaliacao=None):
        ano_corrente = datetime.date.today().year
        qtd_avaliacoes_rsc = 0
        qtd_avaliacoes_titular = 0

        if "rsc" in settings.INSTALLED_APPS:
            ProcessoAvaliador = apps.get_model("rsc", "ProcessoAvaliador")
            Avaliacao = apps.get_model("rsc", "Avaliacao")
            qtd_avaliacoes_rsc = self.processo_avaliador_rsc.filter(
                data_cadastro__year=ano_corrente, status=ProcessoAvaliador.AVALIACAO_FINALIZADA
            ).count()
            if isinstance(avaliacao, Avaliacao):
                return qtd_avaliacoes_rsc

        if "professor_titular" in settings.INSTALLED_APPS:
            ProcessoAvaliador = apps.get_model("professor_titular", "ProcessoAvaliador")
            Avaliacao = apps.get_model("professor_titular", "Avaliacao")
            qtd_avaliacoes_titular = self.processo_avaliador_titular.filter(
                data_cadastro__year=ano_corrente, status=ProcessoAvaliador.AVALIACAO_FINALIZADA
            ).count()
            if isinstance(avaliacao, Avaliacao):
                return qtd_avaliacoes_titular

        return qtd_avaliacoes_rsc + qtd_avaliacoes_titular

    def qtd_perda_prazo_aceite(self, avaliacao=None):
        ano_corrente = datetime.date.today().year
        qtd_avaliacoes_rsc = 0
        qtd_avaliacoes_titular = 0

        if "rsc" in settings.INSTALLED_APPS:
            ProcessoAvaliador = apps.get_model("rsc", "ProcessoAvaliador")
            Avaliacao = apps.get_model("rsc", "Avaliacao")
            qtd_avaliacoes_rsc = self.processo_avaliador_rsc.filter(
                data_cadastro__year=ano_corrente, status=ProcessoAvaliador.EXCEDEU_TEMPO_ACEITE
            ).count()
            if isinstance(avaliacao, Avaliacao):
                return qtd_avaliacoes_rsc

        if "professor_titular" in settings.INSTALLED_APPS:
            ProcessoAvaliador = apps.get_model("professor_titular", "ProcessoAvaliador")
            Avaliacao = apps.get_model("professor_titular", "Avaliacao")
            qtd_avaliacoes_titular = self.processo_avaliador_titular.filter(
                data_cadastro__year=ano_corrente, status=ProcessoAvaliador.EXCEDEU_TEMPO_ACEITE
            ).count()
            if isinstance(avaliacao, Avaliacao):
                return qtd_avaliacoes_titular

        return qtd_avaliacoes_rsc + qtd_avaliacoes_titular

    def qtd_perda_prazo_avaliacao(self, avaliacao=None):
        ano_corrente = datetime.date.today().year
        qtd_avaliacoes_rsc = 0
        qtd_avaliacoes_titular = 0

        if "rsc" in settings.INSTALLED_APPS:
            ProcessoAvaliador = apps.get_model("rsc", "ProcessoAvaliador")
            Avaliacao = apps.get_model("rsc", "Avaliacao")
            qtd_avaliacoes_rsc = self.processo_avaliador_rsc.filter(
                data_cadastro__year=ano_corrente, status=ProcessoAvaliador.EXCEDEU_TEMPO_AVALIACAO
            ).count()
            if isinstance(avaliacao, Avaliacao):
                return qtd_avaliacoes_rsc

        if "professor_titular" in settings.INSTALLED_APPS:
            ProcessoAvaliador = apps.get_model("professor_titular", "ProcessoAvaliador")
            Avaliacao = apps.get_model("professor_titular", "Avaliacao")
            qtd_avaliacoes_titular = self.processo_avaliador_titular.filter(
                data_cadastro__year=ano_corrente, status=ProcessoAvaliador.EXCEDEU_TEMPO_AVALIACAO
            ).count()
            if isinstance(avaliacao, Avaliacao):
                return qtd_avaliacoes_titular

        return qtd_avaliacoes_rsc + qtd_avaliacoes_titular

    def qtd_rejeicao_avaliacao(self, avaliacao=None):
        ano_corrente = datetime.date.today().year
        qtd_avaliacoes_rsc = 0
        qtd_avaliacoes_titular = 0

        if "rsc" in settings.INSTALLED_APPS:
            ProcessoAvaliador = apps.get_model("rsc", "ProcessoAvaliador")
            Avaliacao = apps.get_model("rsc", "Avaliacao")
            qtd_avaliacoes_rsc = self.processo_avaliador_rsc.filter(
                data_cadastro__year=ano_corrente, status=ProcessoAvaliador.REJEITADO_PELO_AVALIADOR
            ).count()
            if isinstance(avaliacao, Avaliacao):
                return qtd_avaliacoes_rsc

        if "professor_titular" in settings.INSTALLED_APPS:
            ProcessoAvaliador = apps.get_model("professor_titular", "ProcessoAvaliador")
            Avaliacao = apps.get_model("professor_titular", "Avaliacao")
            qtd_avaliacoes_titular = self.processo_avaliador_titular.filter(
                data_cadastro__year=ano_corrente, status=ProcessoAvaliador.REJEITADO_PELO_AVALIADOR
            ).count()
            if isinstance(avaliacao, Avaliacao):
                return qtd_avaliacoes_titular

        return qtd_avaliacoes_rsc + qtd_avaliacoes_titular

    def qtd_avaliacoes_pagas(self, avaliacao):
        if "rsc" in settings.INSTALLED_APPS:
            Avaliacao = apps.get_model("rsc", "Avaliacao")
            if isinstance(avaliacao, Avaliacao):
                return self.avaliacao_avaliador_rsc.filter(
                    avaliacao_paga=True, status__in=[Avaliacao.DEFERIDA, Avaliacao.INDEFERIDA]
                ).count()

        if "professor_titular" in settings.INSTALLED_APPS:
            Avaliacao = apps.get_model("professor_titular", "Avaliacao")
            if isinstance(avaliacao, Avaliacao):
                return self.avaliacao_avaliador_titular.filter(avaliacao_paga=True, status__in=[Avaliacao.FINALIZADA]).count()

    def qtd_avaliacoes_nao_pagas(self, avaliacao):
        if "rsc" in settings.INSTALLED_APPS:
            Avaliacao = apps.get_model("rsc", "Avaliacao")
            if isinstance(avaliacao, Avaliacao):
                return self.avaliacao_avaliador_rsc.filter(
                    avaliacao_paga=False, status__in=[Avaliacao.DEFERIDA, Avaliacao.INDEFERIDA]
                ).count()

        if "professor_titular" in settings.INSTALLED_APPS:
            Avaliacao = apps.get_model("professor_titular", "Avaliacao")
            if isinstance(avaliacao, Avaliacao):
                return self.avaliacao_avaliador_titular.filter(avaliacao_paga=False, status__in=[Avaliacao.FINALIZADA]).count()

    def eh_interno(self):
        if self.vinculo.eh_servidor():
            return self.vinculo.relacionamento
        return None

    def eh_externo(self):
        if self.vinculo.eh_prestador():
            return self.vinculo.relacionamento
        return None


class ConsolidadasManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter().exclude(situacao__in=[4, 17, 1005])


class Viagem(ModelPlus):
    SITUACAO_CHOICES = (
        (1, "Criado"),
        (2, "Solicitado Passagem"),
        (3, "Reservado Passagem"),
        (4, "Cancelado"),
        (6, "Aprovado pelo Proponente"),
        (7, "Aprovado pelo Ordenador de Despesa"),
        (8, "Efetuado a Execução Financeira"),
        (9, "Prestado Contas"),
        (10, "Aprovado pelo Proponente - Prest. Contas"),
        (11, "Aprovado pelo Ordenador de Despesa - Prest. Contas"),
        (15, "Viagem Encerrada"),
        (17, "Não Aprovada"),
        (20, "Viagem não realizada"),
        (1001, "Em Andamento"),
        (1002, "Em Prestação de Contas"),
        (1003, "Prestação de Contas Pendente"),
        (1004, "Encerrada - realizada"),
        (1005, "Encerrada - não realizada"),
    )

    codigo_siorg = models.CharFieldPlus("Código Siorg Solicitante", null=False, blank=False)
    nome_siorg = models.CharFieldPlus("Nome Siorg Solicitante", null=False, blank=False)

    servidor = models.ForeignKeyPlus("rh.Servidor", related_name="viagemscdpservidor_set", null=True, on_delete=models.CASCADE)
    pessoa_fisica = models.ForeignKeyPlus("rh.PessoaFisica", related_name="viagemscdppessoafisica_set", null=True, on_delete=models.CASCADE)

    nome_proposto = models.CharFieldPlus("Nome do Proposto", null=False, blank=False)

    tipo_proposto = models.CharFieldPlus("Tipo de Proposto", null=False, blank=False)

    numero_pcdp = models.CharFieldPlus("Número PCDP", null=False, blank=False, unique=True)
    motivo_viagem = models.TextField("Motivo da Viagem", blank=True)
    objetivo_viagem = models.TextField("Objetivo da Viagem", blank=True)

    data_inicio_viagem = models.DateFieldPlus("Data Inicial da Viagem", null=False, blank=False, db_index=True)
    data_fim_viagem = models.DateFieldPlus("Data Fim da Viagem", null=False, blank=False, db_index=True)

    quantidade_viagens = models.IntegerField("Quantidade de Viagens", null=True, blank=True)
    quantidade_de_dias_afastamento = models.IntegerField("Quantidade de dias afastados", null=True, blank=True)
    quantidade_de_diarias = models.DecimalFieldPlus("Quantidade de diarias", null=True, blank=True)

    valor_desconto_auxilio_alimentacao = models.DecimalFieldPlus("Valor de desconto do auxílio alimentação", null=True, blank=True)
    valor_desconto_auxilio_transporte = models.DecimalFieldPlus("Valor de desconto do auxílio transporte", null=True, blank=True)

    valor_passagem = models.DecimalFieldPlus("Valor da passagem", null=True, blank=True)
    valor_diaria = models.DecimalFieldPlus("Valor da diária", null=True, blank=True)
    valor_viagem = models.DecimalFieldPlus("Valor da viagem", null=True, blank=True)

    situacao = models.PositiveIntegerField("Situação", choices=SITUACAO_CHOICES)

    consolidadas = ConsolidadasManager()
    objects = models.Manager()

    class Meta:
        verbose_name = "Viagem"
        verbose_name_plural = "Viagens"
        permissions = (
            ("pode_ver_relatorios_viagens", "Pode ver relatórios viagens"),
            ("pode_ver_relatorios_viagens_detalhados", "Pode ver relatórios viagens detalhados"),
        )

    def __str__(self):
        return "Viagem de {} - {} (de {} à {}) - {}".format(
            self.servidor,
            self.objetivo_viagem,
            self.data_inicio_viagem.strftime("%d/%m/%Y"),
            self.data_fim_viagem.strftime("%d/%m/%Y"),
            self.get_situacao_display(),
        )

    def get_absolute_url(self):
        return f"/rh/tela_pcdp/{self.pk:d}/"

    def get_motivo_viagem_truncate(self):
        return self.motivo_viagem[:254]

    @property
    def get_data_emissao_bilhetes(self):
        if self.bilheteviagem_set.all().exists():
            return self.bilheteviagem_set.all().latest("data_emissao").data_emissao
        return None

    @classmethod
    def get_viagens(cls, servidor, data_inicial, data_final):
        return cls.consolidadas.filter(servidor=servidor, data_inicio_viagem__lte=data_final, data_fim_viagem__gte=data_inicial)


class BilheteViagem(ModelPlus):
    viagem = models.ForeignKeyPlus("rh.Viagem", null=True, blank=True, verbose_name="Viagem")
    numero = models.CharFieldPlus("Número do Bilhete", null=False, blank=False)
    tipo = models.CharFieldPlus("Tipo", null=False, blank=False)
    data_emissao = models.DateFieldPlus("Data da Emissão", null=True, blank=False, db_index=True)
    status = models.CharFieldPlus("Status", null=False, blank=False)

    class Meta:
        unique_together = ("viagem", "numero")
        verbose_name = "Bilhete da Viagem"
        verbose_name_plural = "Bilhetes das Viagens"

    def __str__(self):
        return f"Bilhete {self.numero} ({self.status})"


class Papel(models.ModelPlus):
    TIPO_PAPEL_CARGO = 'cargo'
    TIPO_PAPEL_FUNCAO = 'funcao'
    TIPO_PAPEL_COMISSAOCONSELHO = 'comissaoconselho'
    TIPO_PAPEL_OCUPACAO = 'ocupacao'  # usado pelos prestadores de serviço
    TIPO_PAPEL_DISCENTE = 'discente'  # usado pelos alunos ativos = matriculados
    TIPO_PAPEL_USUARIOEXTERNO = 'usuarioexterno'  # usado pelos usuários externos (proxy from PrestadorServico)

    TIPOS_PAPEIS = [
        (TIPO_PAPEL_CARGO, TIPO_PAPEL_CARGO),
        (TIPO_PAPEL_FUNCAO, TIPO_PAPEL_FUNCAO),
        (TIPO_PAPEL_COMISSAOCONSELHO, TIPO_PAPEL_COMISSAOCONSELHO),
        (TIPO_PAPEL_OCUPACAO, TIPO_PAPEL_OCUPACAO),
        (TIPO_PAPEL_DISCENTE, TIPO_PAPEL_DISCENTE),
        (TIPO_PAPEL_USUARIOEXTERNO, TIPO_PAPEL_USUARIOEXTERNO),
    ]
    pessoa = models.ForeignKeyPlus("rh.PessoaFisica", verbose_name="Pessoa Física", on_delete=models.CASCADE)
    tipo_papel = models.CharField("Tipo de papel", default=TIPO_PAPEL_CARGO, choices=TIPOS_PAPEIS, null=False, blank=False, max_length=255)

    # TODO: Com o uso da GenericKey, o campo descricao agora armazena uma informação redundate (nome do CargoEmprego /
    # codigo - nome da Funcao). Ver com Lucas se é interessante manter essa informação redundante, a título de "histórico",
    # ou se esse campo pode ser descartado. Obs: O mesmo ocorre com o campo detalhamento.
    descricao = models.TextField("Descrição", null=False, blank=False)
    detalhamento = models.TextField("Detalhamento", blank=False)
    portaria = models.CharField("portaria", null=False, blank=False, max_length=50)
    data_inicio = models.DateFieldPlus("Data de início", null=True, blank=False)
    data_fim = models.DateFieldPlus("Data fim", null=True)

    setor_suap = models.ForeignKeyPlus(
        "rh.Setor", null=True, blank=False, related_name="papel_servidor_setor_suap", on_delete=models.CASCADE
    )

    # Dados do tipo de papel exercido pelo servidor. Por enquanto só dois tipos de papéis estão sendo
    # carregados: CargoEmprego e Funcao. Para abstrair isso está sendo usado o GenericKey.
    papel_limit_choices = (
        models.Q(app_label="rh", model="CargoEmprego")
        | models.Q(app_label="rh", model="Funcao")
        | models.Q(app_label="comum", model="Ocupacao")
    )
    papel_content_type = models.ForeignKeyPlus(
        ContentType, verbose_name="Papel (Type)", limit_choices_to=papel_limit_choices, null=False, blank=False, on_delete=models.CASCADE
    )
    papel_content_id = models.PositiveIntegerField(verbose_name="Papel (Id)", null=False)
    papel_content_object = GenericForeignKey("papel_content_type", "papel_content_id")

    def __str__(self):
        return self.detalhamento

    class Meta:
        verbose_name = "Papel"
        verbose_name_plural = "Papéis"
        unique_together = ("pessoa", "papel_content_type", "papel_content_id", "data_inicio")


class GrupoDeficiencia(ModelPlus):
    codigo = models.CharFieldPlus("Código", null=False, blank=False)
    descricao = models.CharFieldPlus("Descrição", null=False, blank=False)

    class Meta:
        verbose_name = "Grupo de Deficiência"
        verbose_name_plural = "Grupos de Deficiências"

    def __str__(self):
        return f"[{self.codigo}] - {self.descricao}"


class Deficiencia(ModelPlus):
    grupo_deficiencia = models.ForeignKeyPlus("rh.GrupoDeficiencia", verbose_name="Grupo de Deficiência", on_delete=models.CASCADE)
    codigo = models.CharFieldPlus("Código", null=False, blank=False)
    descricao = models.CharFieldPlus("Descrição", null=False, blank=False)

    class Meta:
        verbose_name = "Deficiência"
        verbose_name_plural = "Deficiências"

    def __str__(self):
        return f"{self.grupo_deficiencia.descricao} - {self.descricao}"


######################################################################################################
# Carga Horária Reduzida
######################################################################################################
class CargaHorariaReduzida(ModelPlus):
    TIPO_AFASTAMENTO_PARCIAL = 0
    TIPO_CH_EXCEPCIONAL = 1

    STATUS_AGUARDANDO_VALIDACAO_CHEFE = 0
    STATUS_AGUARDANDO_VALIDACAO_RH = 1
    STATUS_DEFERIDO_PELO_RH = 2
    STATUS_INDEFERIDO_PELO_RH = 3
    STATUS_INDEFERIDO_PELO_CHEFE = 4
    STATUS_NOVOS_DOCUMENTOS_SOLICITADOS = 5
    STATUS_AGUARDANDO_ENVIO_CHEFE = 6
    STATUS_ALTERANDO_HORARIO = 7
    STATUS_AGUARDANDO_CADASTRAR_HORARIO = 8
    STATUS_HORARIO_CADASTRADO = 9

    STATUS_AMIGAVEL_DEFERIDO = "deferir"
    STATUS_AMIGAVEL_INDEFERIDO = "indeferir"
    STATUS_AMIGAVEL_SOLICITAR_DOCUMENTOS = "solicitardocumentos"

    STATUS_AMIGAVEL_CHOICES = [
        [STATUS_AMIGAVEL_DEFERIDO, "Deferir"],
        [STATUS_AMIGAVEL_INDEFERIDO, "Indeferir"],
        [STATUS_AMIGAVEL_SOLICITAR_DOCUMENTOS, "Solicitar documentos"],
    ]

    TIPO_CHOICES = [[TIPO_AFASTAMENTO_PARCIAL, "Afastamento parcial"], [TIPO_CH_EXCEPCIONAL, "Carga horária excepcional"]]
    STATUS_CHOICES = [
        [STATUS_AGUARDANDO_VALIDACAO_CHEFE, "Aguardando validação do chefe"],
        [STATUS_AGUARDANDO_VALIDACAO_RH, "Aguardando validação do RH"],
        [STATUS_DEFERIDO_PELO_RH, "Deferido"],
        [STATUS_INDEFERIDO_PELO_RH, "Indeferido"],
        [STATUS_INDEFERIDO_PELO_CHEFE, "Indeferido pelo chefe"],
        [STATUS_NOVOS_DOCUMENTOS_SOLICITADOS, "Novos documentos solicitados pelo RH"],
        [STATUS_AGUARDANDO_ENVIO_CHEFE, "Aguardando envio para o chefe"],
        [STATUS_ALTERANDO_HORARIO, "Alterando horário"],
        [STATUS_AGUARDANDO_CADASTRAR_HORARIO, "Aguardando cadastrar horário"],
        [STATUS_HORARIO_CADASTRADO, "Horário cadastrado"],
    ]

    protocolo_content_type = models.ForeignKeyPlus(ContentType, on_delete=models.CASCADE, null=True, blank=False, default=None)
    protocolo_content_id = models.PositiveIntegerField(verbose_name="Protocolo (Id)", default=0)
    protocolo_content_object = GenericForeignKey("protocolo_content_type", "protocolo_content_id")

    servidor = models.ForeignKeyPlus("rh.Servidor", on_delete=models.CASCADE)
    chefe_imediato_validador = models.ForeignKeyPlus(
        "rh.Servidor", null=True, blank=True, related_name="chefe_imediato_validador", on_delete=models.CASCADE
    )
    servidor_rh_validador = models.ForeignKeyPlus(
        "rh.Servidor", null=True, blank=True, related_name="servidor_rh_validador", verbose_name="Validador", on_delete=models.CASCADE
    )
    numero = models.IntegerField("Número do Processo", blank=True, null=True)
    data_inicio = models.DateFieldPlus("Início da Alteração", blank=False, null=True)
    data_termino = models.DateFieldPlus("Término da Alteração", blank=False, null=True)
    tipo = models.IntegerField(choices=TIPO_CHOICES)
    status = models.IntegerField("Situação do Processo", choices=STATUS_CHOICES)
    nova_jornada = models.CharFieldPlus("Nova Jornada de Trabalho", blank=True, null=True)
    ano = models.IntegerField()
    motivo_indeferimento_chefe = models.CharField("Motivo do Indeferimento", max_length=2000, blank=False, null=True)
    motivo_indeferimento_rh = models.CharField("Motivo do Indeferimento", max_length=2000, blank=False, null=True)
    descricao_novos_documentos = models.CharField("Descrição dos novos documentos", max_length=2000, blank=False, null=True)

    class Meta:
        verbose_name = "Processo de Alteração de Carga Horária"
        verbose_name_plural = "Processos de Alteração de Carga Horária"

    def __str__(self):
        return f"Processo de Alteração de Carga Horária - {self.servidor}"

    @property
    def status_estilizado(self):
        class_css = "status-error"
        status_display = self.get_status_display()

        if self.status == CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_CHEFE:
            class_css = "status-em-tramite"
        if self.status == CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_RH:
            class_css = "status-em-tramite"
        if self.status == CargaHorariaReduzida.STATUS_INDEFERIDO_PELO_CHEFE:
            class_css = "status-rejeitado"
        if self.status == CargaHorariaReduzida.STATUS_INDEFERIDO_PELO_RH:
            class_css = "status-rejeitado"
        if self.status == CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH:
            class_css = "status-success"
        if self.status == CargaHorariaReduzida.STATUS_NOVOS_DOCUMENTOS_SOLICITADOS:
            class_css = "status-alert"
        return f"<span class='status {class_css} text-nowrap-normal'>{status_display}</span>"

    def get_carga_horaria_disponivel_choice(self):
        opcao_maximo = self.servidor.jornada_trabalho.get_jornada_trabalho_diaria() * 5 or 40
        lista_carga = []
        for limite in range(1, opcao_maximo + 1):
            if limite == 1:
                lista_carga.append([limite, f"{limite} HORA SEMANAL "])
            else:
                lista_carga.append([limite, f"{limite} HORAS SEMANAIS "])

        return lista_carga

    def get_carga_horaria_disponivel_diaria_choice(self):
        opcao_maximo = int(self.servidor.jornada_trabalho.get_jornada_trabalho_diaria())
        lista_carga = []

        for limite in range(0, opcao_maximo + 3):
            # if limite % 5 == 0:
            lista_carga.append([limite, f"{limite} h "])

        return lista_carga

    """
    editar: o servidor pode editar antes de enviar o processo para validação do chefe
    """

    def servidor_pode_editar(self):
        return self.status == self.STATUS_AGUARDANDO_ENVIO_CHEFE

    def processo_editavel(self):
        return self.status == self.STATUS_AGUARDANDO_ENVIO_CHEFE or self.status == self.STATUS_NOVOS_DOCUMENTOS_SOLICITADOS

    def servidor_pode_enviar_novos_documentos(self):
        return self.status == self.STATUS_NOVOS_DOCUMENTOS_SOLICITADOS

    def status_processo_indeferido_pelo_rh(self):
        return self.status == self.status == self.STATUS_INDEFERIDO_PELO_RH

    def status_documentos_solicitados(self):
        return self.status == self.STATUS_NOVOS_DOCUMENTOS_SOLICITADOS

    @staticmethod
    def servidor_tem_funcao(servidor):
        return servidor.funcao

    @staticmethod
    def setor_servidor_eh_flexivel(servidor):
        jonada_trabalho_setor = servidor.setor.jornada_trabalho()
        return jonada_trabalho_setor.nome == "30 HORAS SEMANAIS"

    def chefe_pode_validar(self):
        return self.status == self.STATUS_AGUARDANDO_VALIDACAO_CHEFE

    def rh_pode_validar(self):
        return (
            self.status == self.STATUS_AGUARDANDO_VALIDACAO_RH
            or self.status == self.STATUS_DEFERIDO_PELO_RH
            or self.status == self.STATUS_ALTERANDO_HORARIO
        )

    def status_deferido(self):
        return self.status == self.STATUS_DEFERIDO_PELO_RH

    def rh_pode_editar_horario(self):
        return self.status == self.STATUS_AGUARDANDO_VALIDACAO_RH or self.status != self.STATUS_DEFERIDO_PELO_RH

    def obter_emails_chefes(self):
        emails = []
        for chefe in self.chefe:
            emails.append(chefe.email)
        return emails

    def tipo_afastamento_parcial(self):
        return self.tipo == self.TIPO_AFASTAMENTO_PARCIAL

    def tipo_ch_excepcional(self):
        return self.tipo == self.TIPO_CH_EXCEPCIONAL

    @property
    def chefe(self):
        return self.servidor.chefes_na_data(data=datetime.datetime.now())

    @staticmethod
    def get_processos_afastamento_aguardando_validacao(chefe_imediato_validador):
        processos_afastamento_ids = []
        for processo_afastamento in CargaHorariaReduzida.objects.filter(status=CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_CHEFE):
            if chefe_imediato_validador.id in [chefe.id for chefe in processo_afastamento.chefe]:
                processos_afastamento_ids.append(processo_afastamento.id)
        return CargaHorariaReduzida.objects.filter(id__in=processos_afastamento_ids)

    @staticmethod
    def get_processos_rh_a_validar():
        processos_pendentes_de_validacao_rh = CargaHorariaReduzida.objects.filter(
            status=CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_RH
        )
        return processos_pendentes_de_validacao_rh

    def validar_periodos_horarios(self):
        periodos_horarios = []
        menor_data = None
        maior_data = None
        for periodo in self.horariosemanal_set.all():
            periodos_horarios += ((periodo.data_inicio, periodo.data_fim),)

            if not menor_data:
                menor_data = periodo.data_inicio
            if not maior_data:
                maior_data = periodo.data_fim

            if periodo.data_inicio < menor_data:
                menor_data = periodo.data_inicio
            if periodo.data_fim > maior_data:
                maior_data = periodo.data_fim

        if periodos_horarios:
            if self.data_inicio < menor_data:
                periodos_ok, periodos_mensagem = (
                    False,
                    "Há um período de horário não coberto: {} a {}.".format(
                        self.data_inicio.strftime("%d/%m/%Y"), (menor_data - datetime.timedelta(1)).strftime("%d/%m/%Y")
                    ),
                )
            #
            elif self.data_inicio > menor_data:
                periodos_ok, periodos_mensagem = (
                    False,
                    "Há um período de horário inválido: {} a {}.".format(
                        menor_data.strftime("%d/%m/%Y"), (self.data_inicio - datetime.timedelta(1)).strftime("%d/%m/%Y")
                    ),
                )

            elif self.data_termino > maior_data:
                periodos_ok, periodos_mensagem = (
                    False,
                    "Há um período de horário não coberto: {} a {}.".format(
                        (maior_data + datetime.timedelta(1)).strftime("%d/%m/%Y"), self.data_termino.strftime("%d/%m/%Y")
                    ),
                )
            #
            elif self.data_termino < maior_data:
                periodos_ok, periodos_mensagem = (
                    False,
                    "Há um período de horário inválido: {} a {}.".format(
                        (self.data_termino + datetime.timedelta(1)).strftime("%d/%m/%Y"), maior_data.strftime("%d/%m/%Y")
                    ),
                )
            else:
                periodos_ok, periodos_mensagem = utils.periodos_sucessivos(periodos_horarios)
                periodos_mensagem = "".join(periodos_mensagem)
                #
                if not periodos_ok:
                    periodos_mensagem = "Existem períodos/dias descobertos entre os " "períodos informados ou períodos sobrepostos"

        return periodos_ok, periodos_mensagem


class DocumentacaoExigida(models.EncryptedPKModel):
    processo = models.ForeignKeyPlus(
        "rh.CargaHorariaReduzida",
        blank=True,
        null=False,
        verbose_name="processo associado ao arquivo",
        related_name="documentos",
        on_delete=models.CASCADE,
    )
    nome = models.CharFieldPlus(max_length=255)
    diretorio = models.CharFieldPlus(max_length=255, unique=True)
    tamanho = models.BigIntegerField()

    objects = models.EncryptedPKModelManager()


class JornadaTrabalhoInternaCargaHorariaReduzida:
    """Jornada de trabalho adaptada para efeitos no ponto"""

    nome = None  # é uma string no formato 'x HORAS SEMANAIS'

    def __init__(self, nome):
        self.nome = nome

    def __str__(self):
        return self.nome

    def get_jornada_trabalho_diaria(self):
        return float(self.nome.split("HORAS SEMANAIS")[0].strip())

    def get_jornada_trabalho_semanal(self):
        return self.get_jornada_trabalho_diaria() * 5


class HorarioSemanal(ModelPlus):
    processo_reducao_ch = models.ForeignKeyPlus(
        "rh.CargaHorariaReduzida", blank=True, null=False, verbose_name="Processo de afastamento", on_delete=models.CASCADE
    )
    data_inicio = models.DateFieldPlus("Data Inicial")
    data_fim = models.DateFieldPlus("Data Final", null=True)
    seg = models.IntegerField("SEG", blank=False, null=False)
    ter = models.IntegerField("TER", blank=False, null=False)
    qua = models.IntegerField("QUA", blank=False, null=False)
    qui = models.IntegerField("QUI", blank=False, null=False)
    sex = models.IntegerField("SEX", blank=False, null=False)
    jornada_semanal = models.CharFieldPlus("Jornada de Trabalho", blank=True, null=True)

    class Meta:
        ordering = ("data_inicio",)
        verbose_name = "Horário de Afasmento"
        verbose_name_plural = "Horários de Afastamento"

    def __str__(self):
        return f"Horário do Afastamento - {self.processo_reducao_ch.servidor}"

    @staticmethod
    def get_jornadas_servidor_horario(servidor, data_inicio, data_fim):
        jornadas_trabalho_servidor = dict()
        filtro_1 = HorarioSemanal.objects.filter(data_inicio__gte=data_inicio, data_inicio__lte=data_fim)
        filtro_2 = HorarioSemanal.objects.filter(data_fim__gte=data_inicio, data_fim__lte=data_fim)
        filtro_3 = HorarioSemanal.objects.filter(data_inicio__lte=data_inicio, data_fim__gte=data_fim)

        processos_de_ch_reduzida = CargaHorariaReduzida.objects.filter(
            servidor=servidor, status=CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH
        )
        for processo in processos_de_ch_reduzida:
            afastamentos = (filtro_1 | filtro_2 | filtro_3).distinct().filter(processo_reducao_ch=processo)
            for afastamento in afastamentos:
                inicio_afastamento = afastamento.data_inicio
                for dia in datas_entre(inicio_afastamento, afastamento.data_fim):
                    if data_inicio <= dia <= data_fim:
                        if dia.weekday() == 0:
                            jornadas_trabalho_servidor[dia] = JornadaTrabalhoInternaCargaHorariaReduzida(nome=f"{afastamento.seg}")
                        elif dia.weekday() == 1:
                            jornadas_trabalho_servidor[dia] = JornadaTrabalhoInternaCargaHorariaReduzida(nome=f"{afastamento.ter}")
                        elif dia.weekday() == 2:
                            jornadas_trabalho_servidor[dia] = JornadaTrabalhoInternaCargaHorariaReduzida(nome=f"{afastamento.qua}")
                        elif dia.weekday() == 3:
                            jornadas_trabalho_servidor[dia] = JornadaTrabalhoInternaCargaHorariaReduzida(nome=f"{afastamento.qui}")
                        elif dia.weekday() == 4:
                            jornadas_trabalho_servidor[dia] = JornadaTrabalhoInternaCargaHorariaReduzida(nome=f"{afastamento.sex}")
        return jornadas_trabalho_servidor


class AreaConhecimento(models.ModelPlus):
    superior = models.ForeignKeyPlus("rh.AreaConhecimento", null=True, verbose_name="Superior", on_delete=models.CASCADE)
    codigo = models.CharField("Código", max_length=8, unique=True)
    descricao = models.CharField("Descrição", max_length=255)

    objects = AreaConhecimentoManager()

    class Meta:
        verbose_name = "Área do Conhecimento"
        verbose_name_plural = "Áreas de Conhecimento"

    def __str__(self):
        return f"{self.descricao} ({self.superior})" if self.superior else self.descricao


class CronogramaFolha(models.ModelPlus):
    mes = models.PositiveIntegerField("Mês", null=False, blank=False)
    ano = models.ForeignKeyPlus("comum.Ano", verbose_name="Ano", null=False, blank=False, on_delete=models.CASCADE)
    data_abertura_atualizacao_folha = models.DateFieldPlus("Abertura do SIAPE para Atualização da Folha", null=False, blank=False)
    data_fechamento_processamento_folha = models.DateFieldPlus("Fechamento do SIAPE para Processamento da Folha", null=False, blank=False)
    data_consulta_previa_folha = models.DateFieldPlus("Consulta da Prévia da Folha", null=False, blank=False)
    data_abertura_proxima_folha = models.DateFieldPlus("Abertura da Próxima Folha", null=False, blank=False)
    data_cadastro = models.DateTimeFieldPlus("Data de Cadastro", null=True, blank=True, auto_now_add=datetime.datetime.now())

    class Meta:
        verbose_name = "Cronograma da Folha"
        verbose_name_plural = "Cronogramas das Folhas"

    def __str__(self):
        return f"{Meses.get_mes(self.mes)}/{self.ano.ano}"

    @classmethod
    def get_cronograma_hoje(cls):
        hoje = datetime.datetime.now()
        qs_cronograma = CronogramaFolha.objects.filter(data_fechamento_processamento_folha__gte=hoje).order_by(
            "data_fechamento_processamento_folha"
        )
        if not qs_cronograma.exists():
            return None
        return qs_cronograma[0]


class AcaoSaudeAtivaManager(models.Manager):
    def get_queryset(self):
        hoje = datetime.datetime.now()
        return super().get_queryset().filter(periodo_inscricao_inicio__lte=hoje, periodo_inscricao_fim__gte=hoje)


class AcaoSaude(models.ModelPlus):
    SEARCH_FIELDS = ("descricao",)

    descricao = models.CharFieldPlus("Descrição", null=False, blank=False)
    data_inicio = models.DateFieldPlus("Data Início da Ação", null=False, blank=False)
    data_fim = models.DateFieldPlus("Data Final da Ação", null=False, blank=True)
    periodo_inscricao_inicio = models.DateFieldPlus("Data de Início das Inscrições", null=False, blank=False)
    periodo_inscricao_fim = models.DateFieldPlus("Data Fim das Inscrições", null=False, blank=False)
    dias_semanas = models.CharFieldPlus("Dias da Semana", null=True)
    data_cadastro = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    ativas = AcaoSaudeAtivaManager()

    class Meta:
        verbose_name = "Ação de Saúde"
        verbose_name_plural = "Ações de Saúde"

    def periodo_acao(self):
        return f"{data_normal(self.data_inicio)} à {data_normal(self.data_fim)}"

    def save(self, *args, **kwargs):
        if not self.data_fim:
            self.data_fim = self.data_inicio
        super().save(*args, **kwargs)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return f"/rh/acao_saude/{self.pk}/"

    def em_periodo_inscricao(self):
        hoje = datetime.datetime.date(datetime.datetime.now())
        if self.periodo_inscricao_inicio <= hoje <= self.periodo_inscricao_fim:
            return True
        return False

    def acao_finalizada(self):
        hoje = datetime.datetime.date(datetime.datetime.now())
        if self.data_fim < hoje:
            return True
        return False

    def eh_profissional_da_acao(self, servidor):
        return self.agendaatendimentohorario_set.filter(profissional=servidor).exists()

    @staticmethod
    def pode_ver_toda_agenda(user):
        if in_group(user, "Gestor de Agenda de Saúde") or in_group(user, "Coordenador de Saúde Sistêmico") or user.is_superuser:
            return True
        return False


class AgendaAtendimentoHorario(models.ModelPlus):
    acao_saude = models.ForeignKeyPlus(AcaoSaude, verbose_name="Ação de Saúde", on_delete=models.CASCADE, null=True)
    profissional = models.ForeignKeyPlus(Servidor, verbose_name="Profissional", on_delete=models.CASCADE, null=True)
    hora_inicio = models.TimeFieldPlus("Início do Atendimento", null=False, blank=False)
    hora_fim = models.TimeFieldPlus("Fim do Atendimento", null=False, blank=False)
    quantidade_vaga = models.PositiveIntegerField("Quantidade de Vagas", null=False, blank=False, default=0)

    class Meta:
        verbose_name = "Horário de Atendimento"
        verbose_name_plural = "Horários de Atendimento"

    def tem_vaga_disponivel(self, dia):
        if self.quantidade_vaga > HorarioAgendado.objects.filter(horario=self, cancelado=False, data_consulta=dia).count():
            return True
        return False

    def pode_agendar(self, dia):
        return self.tem_vaga_disponivel(dia) and self.acao_saude.em_periodo_inscricao()

    def horario_atendimento(self):
        return "De {} até {}".format(self.hora_inicio.strftime("%H:%M"), self.hora_fim.strftime("%H:%M"))

    def esta_agendado_em_algum_horario(self, funcionario):
        return HorarioAgendado.objects.filter(horario__acao_saude=self.acao_saude, solicitante=funcionario, cancelado=False).exists()

    def __str__(self):
        return f"Hora do atendimento: {self.horario_atendimento()} ({self.profissional})"


class HorarioAgendado(models.ModelPlus):
    horario = models.ForeignKeyPlus(AgendaAtendimentoHorario, verbose_name="Horário", on_delete=models.CASCADE)
    data_consulta = models.DateFieldPlus("Data da Consulta", null=True, blank=True)
    solicitante = models.ForeignKeyPlus(Funcionario, null=True, blank=True, related_name="solicitante", on_delete=models.CASCADE)
    retorno = models.BooleanField("É um retorno?", null=False, blank=True, default=False)
    cancelado = models.BooleanField("Cancelado", null=False, blank=True, default=False)
    data_cancelamento = models.DateTimeFieldPlus("Data de Cancelamento", null=True, blank=True)
    data_cadastro = models.DateTimeFieldPlus(auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Horário Agendado"
        verbose_name_plural = "Horários Agendados"
        permissions = (("pode_cancelar_agendamento", "Pode Cancelar Agendamento"),)

    def cancelar_horario(self):
        self.cancelado = True
        self.data_cancelamento = datetime.datetime.now()
        self.save()


class DataConsultaBloqueada(models.ModelPlus):
    acao_saude = models.ForeignKeyPlus(AcaoSaude, verbose_name="Ação de Saúde", on_delete=models.CASCADE, null=True)
    data_consulta_bloqueada = models.DateFieldPlus("Data da Consulta", null=False)
    motivo_bloqueio = models.CharFieldPlus("Motivo do Bloqueio", max_length=100)
    houve_remarcacao = models.BooleanField("Houve Remarcaçao de Consulta", default=False)

    class Meta:
        verbose_name = "Data de Consulta Bloqueada"
        verbose_name_plural = "Datas de Consultas Bloqueadas"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class PessoaExterna(models.ModelPlus):
    SEARCH_FIELDS = ["nome", "cpf", "user__username", "matricula"]

    nome = models.UnaccentField(max_length=200, db_index=True)
    nome_usual = models.UnaccentField("Nome Usual", max_length=30, blank=True, help_text="O nome apresentado no crachá ou razão social", db_index=True)
    nome_social = models.UnaccentField("Nome Social", max_length=200, blank=True, db_index=True)
    nome_registro = models.UnaccentField("Nome de Registro", max_length=200, blank=True, db_index=True)
    email = models.EmailField(blank=True, verbose_name="E-mail Principal")
    email_secundario = models.EmailField(
        blank=True, verbose_name="E-mail Secundário", help_text="E-mail utilizado para recuperação de senha."
    )
    website = models.URLField(blank=True)
    excluido = models.BooleanField(verbose_name="Excluído", default=False, help_text="Indica se a última ocorrência é de exclusão")
    setores_adicionais = models.ManyToManyField(
        "rh.Setor",
        verbose_name="Setores Adicionais",
        blank=True,
        help_text="O funcionário terá acesso aos processos dos setores adicionais no sistema de protocolo.",
    )
    natureza_juridica = models.CharField("Natureza Jurídica", max_length=5, blank=True, choices=NATUREZA_JURIDICA_CHOICES)
    sistema_origem = models.CharField(
        max_length=50,
        blank=True,
        choices=[["", "Cadastro manual"], ["SIAPE", "SIAPE"], ["WS-SIAPE", "WS-SIAPE"], ["SIAFI", "SIAFI"]],
        help_text="Indica de qual sistema a pessoa veio: SIAPE, SIAFI etc",
    )

    cpf = models.CharField(max_length=20, null=True, verbose_name="CPF", blank=False, db_index=True)
    sexo = models.CharField(max_length=1, null=True, choices=[["M", "Masculino"], ["F", "Feminino"]])
    grupo_sanguineo = models.CharField(
        "Grupo Sanguíneo", max_length=2, null=True, blank=True, choices=[["A", "A"], ["B", "B"], ["AB", "AB"], ["O", "O"]]
    )
    fator_rh = models.CharField("Fator RH", max_length=8, null=True, blank=True, choices=[["+", "+"], ["-", "-"]])
    titulo_numero = models.CharField(max_length=12, null=True, blank=True)
    titulo_zona = models.CharField(max_length=3, null=True, blank=True)
    titulo_secao = models.CharField(max_length=4, null=True, blank=True)
    titulo_uf = models.BrEstadoBrasileiroField(null=True, blank=True)
    titulo_data_emissao = models.DateField(null=True)
    rg = models.CharField(max_length=20, null=True, verbose_name="RG")
    rg_orgao = models.CharField(max_length=10, null=True)
    rg_data = models.DateField(null=True)
    rg_uf = models.BrEstadoBrasileiroField(null=True)
    nascimento_municipio = models.ForeignKey("comum.Municipio", null=True, blank=True, verbose_name="Município", on_delete=models.CASCADE)
    nascimento_data = models.DateFieldPlus("Data de Nascimento", null=True)
    nome_mae = models.CharField("Nome da Mãe", max_length=100, null=True)
    nome_pai = models.CharField("Nome do Pai", max_length=100, null=True, blank=True)
    foto = ImageWithThumbsField(
        storage=get_overwrite_storage(),
        use_id_for_name=True,
        upload_to="fotos_pessoa_externa",
        sizes=((75, 100), (150, 200)),
        null=True,
        blank=True,
    )
    cnh_carteira = models.CharField(max_length=10, null=True, blank=True)
    cnh_registro = models.CharField(max_length=10, null=True, blank=True)
    cnh_categoria = models.CharField(max_length=10, null=True, blank=True)
    cnh_emissao = models.DateField(null=True, blank=True)
    cnh_uf = models.CharField(max_length=2, null=True, blank=True)
    cnh_validade = models.DateField(null=True, blank=True)
    ctps_numero = models.CharField(max_length=20, null=True, blank=True)
    ctps_uf = models.CharField(max_length=2, null=True, blank=True)
    ctps_data_prim_emprego = models.DateField(null=True, blank=True)
    ctps_serie = models.CharField(max_length=10, null=True, blank=True)
    pis_pasep = models.CharField(max_length=20, null=True, blank=True)
    pagto_banco = models.ForeignKey("rh.Banco", null=True, blank=True, on_delete=models.CASCADE)
    pagto_agencia = models.CharField(max_length=20, null=True, blank=True)
    pagto_ccor = models.CharField(max_length=20, null=True, blank=True)
    pagto_ccor_tipo = models.CharField(max_length=2, blank=True, null=True)
    username = models.CharField(max_length=50, null=True, unique=True, db_index=True)
    tem_digital_fraca = models.BooleanField(
        default=False,
        blank=True,
        verbose_name="Permitir registro de ponto sem impressão digital",
        help_text="Servidores com impressão digital fraca devem ter essa " "opção marcada",
    )
    senha_ponto = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Senha para registro de ponto sem impressão digital",
        help_text="Servidores com impressão digital fraca devem ter uma senha " "definida para bater o ponto",
    )
    data_obito = models.DateField(null=True, blank=True)
    template = models.BinaryField(null=True, blank=True, editable=False)
    template_importado_terminal = models.BooleanField(default=False, verbose_name="Digital importada do terminal")
    # busca = SearchField(search=['nome', 'get_cpf_ou_cnpj'])
    estado_civil = models.ForeignKey("comum.EstadoCivil", null=True, on_delete=models.CASCADE)
    raca = models.ForeignKey("comum.Raca", null=True, on_delete=models.CASCADE)

    nacionalidade = models.IntegerField("Nacionalidade", choices=Nacionalidade.get_choices(), null=True)
    pais_origem = models.ForeignKey("comum.Pais", verbose_name="País de Origem", null=True, on_delete=models.CASCADE)  # para estrangeiro

    deficiencia = models.ForeignKey("rh.Deficiencia", verbose_name="Deficiência", null=True, on_delete=models.CASCADE)
    lattes = models.URLField(blank=True)
    matricula = models.CharFieldPlus("Matrícula", null=True, blank=False, max_length=30, db_index=True)
    pessoa_fisica = models.ForeignKeyPlus("rh.PessoaFisica")
    vinculos = GenericRelation(
        "comum.Vinculo", related_query_name="pessoasexternas", object_id_field="id_relacionamento", content_type_field="tipo_relacionamento"
    )

    class Meta:
        verbose_name = "Pessoa Externa"
        verbose_name_plural = "Pessoas Externas"

    def __str__(self):
        return f"{self.nome} - {self.matricula}"

    def get_vinculo(self):
        return self.vinculos.first()

    def get_ext_combo_template(self):
        template = """
                    <div class="person">
                        <div>
                            <h4>{} ({})</h4>
                            <h5>Pessoa Externa</h5>
                        </div>
                    </div>
                    """.format(
            self.nome or "Sem nome", anonimizar_cpf(self.cpf)
        )

        if self.pessoa_fisica.excluido:
            template += '<p class="false">Vínculo inativo</p>'

        return template

    def get_user(self):
        from comum.models import User

        qs = User.objects.filter(username=self.matricula)
        return qs.exists() and qs[0] or None

    @property
    def pessoafisica(self):
        return self.pessoa_fisica

    def save(self, *args, **kwargs):
        from comum.models import Vinculo

        self.matricula = re.sub(r"\D", "", str(self.cpf)) or None

        instance = self.__dict__.copy()
        instance.pop("id")
        instance.pop("_state")
        instance.pop("matricula")
        instance.pop("pessoa_fisica_id")
        if "_pessoa_fisica_cache" in instance:
            instance.pop("_pessoa_fisica_cache")

        if not self.pk and not getattr(self, "pessoa_fisica", None):
            self.pessoa_fisica = PessoaFisica.objects.create(**instance)
        else:
            PessoaFisica.objects.filter(id=self.pessoa_fisica.id).update(**instance)
        super().save(*args, **kwargs)

        qs = Vinculo.objects.filter(pessoasexternas=self)
        if not qs.exists():
            vinculo = Vinculo()
        else:
            vinculo = qs.first()
        vinculo.pessoa = self.pessoa_fisica.pessoa_ptr
        vinculo.relacionamento = self
        vinculo.save()
        return self


#     Essa classe veio do módulo de progressões
class PadraoVencimento(models.ModelPlus):
    CATEGORIA_DOCENTE = "docente"
    CATEGORIA_TECNICO_ADMINISTRATIVO = "tecnico_administrativo"
    CHOICES_CATEGORIA = [[CATEGORIA_DOCENTE, "Docente"], [CATEGORIA_TECNICO_ADMINISTRATIVO, "Técnico Administrativo"]]

    CHOICES_CLASSE = [["A", "A"], ["B", "B"], ["C", "C"], ["D", "D"], ["E", "E"]]
    CHOICES_POSICAO_VERTICAL = [[f"{str(posicao).zfill(2)}", f"{str(posicao).zfill(2)}"] for posicao in range(1, 17)]

    categoria = models.CharField(max_length=50, choices=CHOICES_CATEGORIA)
    classe = models.CharField("Classe", max_length=1, choices=CHOICES_CLASSE)
    posicao_vertical = models.CharField("Mérito", max_length=2, choices=CHOICES_POSICAO_VERTICAL)

    class Meta:
        ordering = ["categoria", "classe", "posicao_vertical"]
        unique_together = ("categoria", "classe", "posicao_vertical")
        verbose_name = "Padrão de Vencimento"
        verbose_name_plural = "Padrões de Vencimento"

    def __str__(self):
        return f"{self.classe}{self.posicao_vertical}"  # ex: E01


class ArquivoUnico(models.ModelPlus):
    # Conteudo é o arquivo em si.
    conteudo = models.FileFieldPlus(
        verbose_name="Arquivo",
        upload_to="private-media/rh/arquivo_unico/",
        # validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls', 'csv', 'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png', 'zip', 'txt'])],
        # max_file_size=settings.FILE_UPLOAD_MAX_MEMORY_SIZE,
    )
    # Tipo do conteúdo (content_type). Ex: Application/pdf
    tipo_conteudo = models.CharFieldPlus(verbose_name="Tipo de Conteúdo", max_length=100)
    # Tamanho em bytes do arquivo (size).
    tamanho_em_bytes = models.PositiveIntegerFieldPlus(verbose_name="Tamanho em bytes")
    # Charset
    charset = models.CharFieldPlus(verbose_name="Charset", max_length=50, blank=True, null=True)
    # Hash 512 dos bytes do arquivo. A ideia desse hash é servir para verificação. Não expor ele publicamente.
    hash_sha512 = models.CharFieldPlus(verbose_name="Hash 512", max_length=128, unique=True)
    # Nome original no primeiro upload
    nome_original_primeiro_upload = models.CharFieldPlus(verbose_name="Nome Original do Primeiro Upload", max_length=100)
    # Data do primeiro upload do arquivo.
    data_hora_primeiro_upload = models.DateTimeFieldPlus("Data e Hora do Primeiro Upload")
    # Data de criação do registro.
    # Atenção: Não coloquei o "auto_now_add=True" pra poder forçar o desenvolvedor a fornecer e data e horas atuais
    # e assim poder gerar o hash_sha512_link_id.
    data_hora_criacao_registro = models.DateTimeFieldPlus("Data e Hora da Criação do Registro")
    hash_sha512_link_id = models.CharFieldPlus(verbose_name="Hash 512 Link Id", max_length=128, unique=True)

    class Meta:
        verbose_name = "Arquivo Único"
        verbose_name_plural = "Arquivos Únicos"

    @classmethod
    def get_or_create_from_file_bytes(
        cls,
        bytes,
        tipo_conteudo,
        nome_original_primeiro_upload,
        data_hora_primeiro_upload,
        tamanho_em_bytes_para_validar=None,
        hash_sha512_para_validar=None,
    ):

        tamanho_em_bytes = len(bytes)
        if tamanho_em_bytes_para_validar and tamanho_em_bytes != tamanho_em_bytes_para_validar:
            raise ValidationError("O tamanho em bytes informado diverge do tamanho real do arquivo.")

        hash_sha512 = hashlib.sha512(bytes).hexdigest()
        if hash_sha512_para_validar and hash_sha512 != hash_sha512_para_validar:
            raise ValidationError("O hash_sha512 informado diverge do calculado para o arquivo.")

        try:
            created = False
            arquivo = cls.objects.get(hash_sha512=hash_sha512)
            if arquivo:
                return arquivo, created
        except cls.DoesNotExist:
            content_file = ContentFile(bytes)
            # if tamanho_em_bytes_para_validar and content_file.size != tamanho_em_bytes_para_validar:
            #     raise ValidationError('O tamanho em bytes informado diverge do tamanho real do arquivo.')

            created = True
            arquivo = ArquivoUnico()
            arquivo.tipo_conteudo = tipo_conteudo
            arquivo.tamanho_em_bytes = tamanho_em_bytes

            arquivo.hash_sha512 = hash_sha512
            arquivo.data_hora_criacao_registro = timezone.now()
            hash_sha512_link_id_str = "[{}],[{}]".format(
                arquivo.data_hora_criacao_registro.strftime("%d%m%Y__%H:%M:%S.%f"), arquivo.hash_sha512
            )
            hash_sha512_link_id_bytes = (hash_sha512_link_id_str).encode("utf-8")
            arquivo.hash_sha512_link_id = hashlib.sha512(hash_sha512_link_id_bytes).hexdigest()

            arquivo.nome_original_primeiro_upload = utils.limitar_tamanho_nome_arquivo(nome_original_primeiro_upload, 100)
            arquivo.data_hora_primeiro_upload = data_hora_primeiro_upload

            # Tentando obter a extensão a partir do nome original do arquivo. Se houver uma e ela for válida para o
            # mimetype em questão, então ela será usada. Obs: O mimetypes parece ser bem legal, mas preferi usar
            # essa abordagem porque para um mesmo "mimetype", podem haver "n" extensões, e as vezes a extensão retornada
            # pelo "mimetypes.guess_extension()" acaba sendo uma extensão pouco conhecida ou até mesmo bugada, como é o
            # o caso de "jpe" para o mimetype 'image/jpeg'. Outra vantagem é que usamos a extensão "orginal" definida
            # no nome do arquivo.
            # Exemplos:
            # In[2]: mimetypes.guess_extension('image/jpeg')
            # Out[2]: '.jpe'

            # In[3]: mimetypes.guess_all_extensions('image/jpeg')
            # Out[3]: ['.jpe', '.jpeg', '.jpg']
            #
            # In[4]: mimetypes.guess_extension('video/mpeg')
            # Out[4]: '.m1v'
            #
            # In[5]: mimetypes.guess_all_extensions('video/mpeg')
            # Out[5]: ['.m1v', '.mpa', '.mpe', '.mpeg', '.mpg', '.m2v']
            extensao = ".{}".format(nome_original_primeiro_upload.split(".")[-1])
            if not extensao in mimetypes.guess_all_extensions(tipo_conteudo):
                extensao = mimetypes.guess_extension(tipo_conteudo)
            nome_arquivo = "{}{}".format("AU", extensao)
            # Nesse momento, o arquivo é criado em disco. O "save=False" indica que não é para salvar ainda a instancia
            # de ArquivoUnico no banco.
            arquivo.conteudo.save(nome_arquivo, content_file, save=False)

            try:
                # Tentando persistir uma instância de ArquivoUnico.
                arquivo.save()
                # arquivo.delete()
                # raise Exception('Proocando rollback...')
                return arquivo, created
            except Exception as e:
                # Em caso de erro, o arquivo que foi persitido em disco é removido, para não gerar lixo.
                arquivo.conteudo.delete(save=False)
                raise e

    @classmethod
    def get_or_create_from_file_strb64(
        cls,
        strb64,
        tipo_conteudo,
        nome_original_primeiro_upload,
        data_hora_primeiro_upload,
        tamanho_em_bytes_para_validar=None,
        hash_sha512_para_validar=None,
    ):
        bytes_b64 = strb64.encode("utf-8")
        bytes = base64.b64decode(bytes_b64)
        return cls.get_or_create_from_file_bytes(
            bytes,
            tipo_conteudo,
            nome_original_primeiro_upload,
            data_hora_primeiro_upload,
            tamanho_em_bytes_para_validar,
            hash_sha512_para_validar,
        )

    def get_conteudo_as_bytes(self):
        bytes = self.conteudo.file.read()
        return bytes

    def get_conteudo_as_strb64(self):
        return convert_bytes_to_strb64(self.get_conteudo_as_bytes())


class AbstractVinculoArquivoUnico(models.ModelPlus):
    arquivo_unico = models.ForeignKeyPlus("rh.ArquivoUnico", on_delete=models.PROTECT)
    nome_original = models.CharFieldPlus(verbose_name="Nome Original", max_length=100)
    nome_exibicao = models.CharFieldPlus(verbose_name="Nome para Exibição", max_length=50, blank=True, null=True)
    descricao = models.CharFieldPlus(verbose_name="Descrição", max_length=100)
    data_hora_upload = models.DateTimeFieldPlus("Data e Hora do Upload")
    data_hora_criacao_registro = models.DateTimeFieldPlus("Data e Hora da Criação do Registro", auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ("-data_hora_upload",)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.clean()
        super().save(force_insert, force_update, using, update_fields)

    def clean(self):
        if self.nome_original:
            self.nome_original = utils.limitar_tamanho_nome_arquivo(self.nome_original, 100)

    def add_extensao_ao_nome_exibicao_com_base_no_nome_original(self):
        extensao = ".{}".format(self.nome_original.split(".")[-1])
        self.nome_exibicao = f"{self.nome_exibicao}{extensao}"


# dados cadastrados aqui não serão atualizados via ws
class ExcecaoDadoWS(models.ModelPlus):
    DADO_CHOICE = (
        ("nome", "Nome"),
        ("situacao", "Situação"),
    )
    servidor = models.ForeignKeyPlus("rh.Servidor", verbose_name="Servidor", on_delete=models.CASCADE)
    campos = models.ManyToManyFieldPlus("rh.CampoExcecaoWS", verbose_name="Campos")

    class Meta:
        verbose_name = "Exceção Dados para Webservice"
        verbose_name_plural = "Exceções Dados para Webservice"


class CampoExcecaoWS(models.ModelPlus):
    campo = models.CharField("Campo", max_length=255)

    class Meta:
        verbose_name = "Campo de exceção"
        verbose_name_plural = "Campos de exceção"


class SolicitacaoAlteracaoFoto(models.ModelPlus):
    AGUARDADO_VALIDACAO = 1
    VALIDADA = 2
    REJEITADA = 3
    SITUCAO_CHOICES = [
        [AGUARDADO_VALIDACAO, "Aguardando validação"],
        [VALIDADA, "Validada"],
        [REJEITADA, "Rejeitada"]
    ]
    foto = models.FileFieldPlus(
        "Foto",
        upload_to='fotos',
        null=False,
        blank=False,
        check_mimetype=False,
        filetypes=['png', 'jpg', 'jpeg'],
        max_file_size=5242880,
    )
    descricao = models.TextField("Descrição", null=True, blank=True, help_text="Se necessário, descreva o motivo da alteração da foto.")
    solicitante = models.ForeignKey("rh.Servidor", verbose_name="Solicitante", on_delete=models.SET_NULL, null=True, blank=False)
    situacao = models.IntegerFieldPlus("Situação", choices=SITUCAO_CHOICES, null=False, blank=False, default=AGUARDADO_VALIDACAO)
    data_interacao = models.DateTimeFieldPlus("Data da Interação", null=True, blank=True)
    responsavel_interacao = models.ForeignKey("rh.Servidor", verbose_name="Responsável pela Interação", on_delete=models.SET_NULL, null=True, blank=True, related_name="responsavel_interacao")
    motivo_rejeicao = models.TextField("Motivo da Rejeição", null=True, blank=True)

    class Meta:
        verbose_name = "Solicitação de Alteração de Foto"
        verbose_name_plural = "Solicitações de Alteração de Foto"

    def get_situacao_html(self):
        css = "alert"
        if self.situacao == SolicitacaoAlteracaoFoto.VALIDADA:
            css = "success"
        if self.situacao == SolicitacaoAlteracaoFoto.REJEITADA:
            css = "error"
        html = f'<span class="status status-{css}">{self.get_situacao_display()}</span>'
        return mark_safe(html)

    @transaction.atomic
    def validar(self, responsavel_usuario):
        self.situacao = self.VALIDADA
        self.data_interacao = datetime.datetime.now()
        self.responsavel_interacao = responsavel_usuario.get_relacionamento()
        qs = Servidor.objects.filter(matricula=self.solicitante.matricula)
        if qs.exists():
            servidor_solicitante = qs[0]
            servidor_solicitante.foto.save(f"{servidor_solicitante.matricula}.jpg", ContentFile(self.foto.read()))
            servidor_solicitante.save()
            self.save()
        else:
            raise Servidor.DoesNotExist("Não foi possível encontrar o solicitante.")

    def rejeitar(self, request):
        self.situacao = self.REJEITADA
        self.motivo_rejeicao = request.POST.get("motivo_rejeicao")
        self.data_interacao = datetime.datetime.now()
        self.responsavel_interacao = request.user.get_relacionamento()
        self.save()

    @staticmethod
    def pode_solicitar_alteracao_foto(user):
        if user.eh_servidor:
            existe_solicitacao = SolicitacaoAlteracaoFoto.objects.filter(situacao=SolicitacaoAlteracaoFoto.AGUARDADO_VALIDACAO, solicitante=user.get_relacionamento()).exists()
            return user.is_superuser or not existe_solicitacao
        return False

    def get_absolute_url(self):
        return f"/rh/detalhe_solicitacao_alteracao_foto/{self.pk}/"


class DadosBancariosPF(models.ModelPlus):
    BANCO_BB = 'BANCO DO BRASIL'
    BANCO_CEF = 'CAIXA ECONÔMICA'
    BRADESCO = 'BRADESCO'
    ITAU = 'ITAU'
    SANTANDER = 'SANTANDER'
    NORDESTE = 'BANCO DO NORDESTE'
    INTER = 'INTER'
    NUBANK = 'NUBANK'
    HSBC = 'HSBC'
    NEXT = 'NEXT '
    PAGSEGURO = 'PAGSEGURO'
    PICPAY = 'PICPAY'
    VOTORANTIM = 'VOTORANTIM'
    C6 = 'C6'
    MERCADOPAGO = 'MERCADO PAGO'
    NEON = 'NEON'

    BANCO_CHOICES = [
        [BANCO_BB, '001 - Banco do Brasil'],
        [BANCO_CEF, '104 - Caixa Econômica'],
        [BRADESCO, '237 - Bradesco'],
        [ITAU, '341 - Itaú'],
        [SANTANDER, '033 - Santander'],
        [NORDESTE, '004 - Banco do Nordeste'],
        [INTER, '077 - INTER'],
        [NUBANK, '260 - NUBANK'],
        [HSBC, '399 - HSBC'],
        [NEXT, '237 - NEXT'],
        [PAGSEGURO, '290 - Pagseguro Internet S.A'],
        [PICPAY, '380 - Banco PicPay Serviços S/A'],
        [VOTORANTIM, '655 - Banco Votorantim'],
        [C6, '336 - Banco C6'],
        [MERCADOPAGO, '323 - MERCADO PAGO'],
        [NEON, '735 - NEON'],
    ]

    TIPOCONTA_CONTACORRENTE = 'Conta Corrente'
    TIPOCONTA_POUPANCA = 'Conta Poupança'
    TIPOCONTA_SALARIO = 'Conta Salário'

    TIPOCONTA_CHOICES = [[TIPOCONTA_CONTACORRENTE, 'Conta Corrente'], [TIPOCONTA_POUPANCA, 'Conta Poupança'], [TIPOCONTA_SALARIO, 'Conta Salário']]

    banco = models.CharField('Banco', max_length=50, choices=BANCO_CHOICES, null=True)
    instituicao = models.ForeignKeyPlus('rh.Banco', verbose_name='Banco', null=True, on_delete=models.SET_NULL)
    numero_agencia = models.CharField('Número da Agência', max_length=50, null=True, help_text='Ex: 3293-X')
    tipo_conta = models.CharField('Tipo da Conta', max_length=50, choices=TIPOCONTA_CHOICES, null=True)
    numero_conta = models.CharField('Número da Conta', max_length=50, null=True, help_text='Ex: 23384-6')
    operacao = models.CharField('Operação', max_length=50, null=True, blank=True)

    pessoa_fisica = models.ForeignKeyPlus('rh.PessoaFisica', related_name="dadosbancariospessoafisica_set")
    prioritario_servico_social = models.BooleanField('Prioritário para Serviço Social', default=False)
    atualizado_por = models.ForeignKeyPlus(
        'comum.Vinculo', null=True, verbose_name='Atualizado Por',
        related_name='dadosbancariospessoafisica_atualizado_por',
        on_delete=models.CASCADE
    )
    atualizado_em = models.DateTimeFieldPlus('Atualizado em', null=True)

    class Meta:
        verbose_name = 'Dados Bancários'
        verbose_name_plural = 'Dados Bancários'

        permissions = (
            ('change_dados_bancarios', 'Pode alterar dados bancários'),
        )
