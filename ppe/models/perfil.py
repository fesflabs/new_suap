import datetime
import re
from collections import OrderedDict
from random import choice
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db.models import F, Q
from django.db.transaction import atomic
from django.utils.safestring import mark_safe
from rest_framework.authtoken.models import Token
from comum.models import Ano, User, Vinculo, Configuracao
from comum.utils import somar_data, insert_space
from djtools.templatetags.filters import format_iterable
from djtools.thumbs import ImageWithThumbsField
from djtools.unaccent_field import UnaccentField
from djtools.utils import normalizar_nome_proprio, anonimizar_cpf
from djtools.storages import get_overwrite_storage
from django.db import models
from djtools.db.models import (
    BrCpfField,
    CharFieldPlus,
    DateFieldPlus,
    DateTimeFieldPlus,
    ForeignKeyPlus,
    ModelPlus,
    PositiveIntegerField,
    PositiveIntegerFieldPlus,
    ForeignKeyPlus, BrCnpjField
)
from django.apps import apps
from comum.models import PrestadorServico
from djtools.utils import send_mail
from ppe.models import LogPPEModel
from rh.models import Servidor, PessoaFisica
from suap import settings


class Unidade(ModelPlus):
    SEARCH_FIELDS = ["nome", "sigla"]
    nome = models.CharField(max_length=255, verbose_name="Nome")
    sigla = models.CharField(max_length=25, verbose_name="Sigla")
    setor = models.OneToOneField("ppe.Setor",related_name='unidade_setor', on_delete=models.CASCADE)
    municipio = ForeignKeyPlus("comum.Municipio", null=True, blank=True, verbose_name="Município")
    cnpj = BrCnpjField(null=True, blank=True)
    endereco = models.CharField(max_length=255, verbose_name="Endereço", null=True, blank=True)
    numero = models.CharField(max_length=255, verbose_name="Número", null=True, blank=True)
    zona_rual = models.BooleanField(verbose_name="Zona Rural?", default=False)
    bairro = models.CharField(max_length=255, verbose_name="Bairro", null=True, blank=True)
    cep = models.CharField(max_length=255, verbose_name="Cep", null=True, blank=True)
    telefone = models.CharField(max_length=255, verbose_name="Telefone", null=True, blank=True)
    fax = models.CharField(max_length=255, verbose_name="Fax", null=True, blank=True)
    class Meta:
        ordering = ["setor__sigla"]
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"

    def __str__(self):
        return self.sigla

    def save(self, *args, **kwargs):
        Setor = apps.get_model("ppe", "Setor")
        """
        O método foi sobrescrito para preencher automaticamente o campo ``uo`` dos
        setores.
        """
        if self.pk:
            setor_antigo = Unidade.objects.get(pk=self.pk).setor
            novo_setor = self.setor
            ignorar_processamento_setores = setor_antigo == novo_setor
        else:
            ignorar_processamento_setores = False

        super().save(*args, **kwargs)
        if not ignorar_processamento_setores:
            for setor in Setor.objects.all():
                setor.save()

    def clean(self):
        super().clean()
        if self.setor.excluido:
            raise ValidationError('O "setor" deve ser um setor ativo.')

    def get_ext_combo_template(self):
        configuracao_setor_eh_suap = settings.TIPO_ARVORE_SETORES == 'SUAP'
        out = str(self)
        return "<div>{}</div>".format(out)

    # def get_servidores(self):
    #     return Servidor.objects.ativos().filter(setor__uo=self)

    # def get_diretor_geral(self, excluir_substituto=False):
    #     servidor_funcao_qs = ServidorFuncaoHistorico.objects.filter(
    #         atividade__codigo__in=[Atividade.DIRETOR_GERAL, Atividade.REITOR],
    #         setor_suap=self.setor,
    #         data_inicio_funcao__lte=datetime.datetime.today(),
    #     )
    #     servidor_funcao_qs = servidor_funcao_qs.filter(data_fim_funcao__gte=datetime.datetime.today()) | servidor_funcao_qs.filter(
    #         data_fim_funcao__isnull=True
    #     )
    #     if excluir_substituto:
    #         servidor_funcao_qs = servidor_funcao_qs.exclude(funcao__codigo=Funcao.get_sigla_substituicao_chefia())
    #     if not servidor_funcao_qs.exists() and self.setor.superior:
    #         return self.setor.superior.uo.get_diretor_geral()
    #     return Servidor.objects.filter(pk__in=servidor_funcao_qs.values_list("servidor", flat=True))

    def can_change(self, user):
        return user.has_perm("rh.eh_rh_sistemico") or (user.has_perm("rh.eh_rh_campus") and user.get_relacionamento().setor.uo == self)
class Setor(ModelPlus):
    SEARCH_FIELDS = ["sigla", "codigo", "nome",]

    DESCENDENTES = dict()

    unidade = ForeignKeyPlus(
        "ppe.Unidade",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.CASCADE,
        related_name="setor_unidade_set",
        verbose_name="Unidade",
    )
    superior = ForeignKeyPlus("self", null=True, blank=True, verbose_name="Setor Superior", on_delete=models.CASCADE)
    sigla = models.CharField(max_length=15)
    nome = models.CharField(max_length=100)
    excluido = models.BooleanField(
        verbose_name="Excluído", default=False, help_text="Setores excluídos não farão parte das buscas e não devem possuir servidores"
    )

    class Meta:
        ordering = ["sigla"]
        verbose_name = "Setor"
        verbose_name_plural = "Setores"

    def save(self, *args, **kwargs):
        """
        O método foi sobrescrito para preencher automaticamente o campo ``uo``.
        O critério para definir um setor SUAP é ter o campo codigo nulo. Porém, codigo
        é tipo texto e o Django preenche o codigo com uma string vazia quando um
        superusuario edita setores SUAP
        """
        self.unidade = self._get_unidade()
        if not self.pk:
            Setor.DESCENDENTES = dict()
        else:
            superior = Setor.objects.get(pk=self.pk).superior
            if superior != self.superior:
                Setor.DESCENDENTES = dict()
                self.__reload_descendentes()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.sigla

    def get_absolute_url(self):
        return f"/ppe/setor/{self.pk:d}/"

    def get_ext_combo_template(self):
        return self.get_caminho_as_html()

    @classmethod
    def get_folhas(cls):
        """Retorna os setores que não tem filhos (os folhas da árvore de setores)"""
        setores_com_filhos = cls.objects.filter(superior__isnull=False).values_list("superior", flat=True).distinct()
        return cls.objects.exclude(id__in=setores_com_filhos)

    def _get_unidade(self):
        """
        Irá buscar o valor do campo ``uo`` recursivamente da hierarquia de
        setores. O retorno desta função deve ser igual ao valor do campo ``uo``.
        """
        setor_atual = self
        while setor_atual is not None:
            resultado = Unidade.objects.filter(setor=setor_atual)
            if resultado:
                return resultado[0]
            setor_atual = setor_atual.superior
        return None

    @property
    def filhos(self):
        return Setor.objects.filter(superior=self)

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


    # ---------------------------------------------------------------------
    # Lista de Servidores do Setor
    # ---------------------------------------------------------------------
    # def get_servidores(self, recursivo=True):
    #     if recursivo:
    #         return Servidor.objects.ativos().filter(setor__in=self.descendentes)
    #     else:
    #         return Servidor.objects.ativos().filter(setor=self)
    #
    # def qtd_servidores(self, recursivo=False):
    #     if recursivo:
    #         return Servidor.objects.ativos_permanentes().filter(setor__in=self.descendentes).count()
    #     else:
    #         return Servidor.objects.ativos_permanentes().filter(setor=self).count()
    #
    # def get_servidores_por_periodo(self, data_inicial=None, data_final=None, recursivo=True):
    #     if (data_inicial is None) and (data_final is None):
    #         #
    #         # returna a lista atual de servidores baseado no atributo 'setor' de 'Servidor'
    #         #
    #         return self.get_servidores(recursivo)
    #     else:
    #         if data_inicial is None:
    #             #
    #             # foi passado um período com apenas a data final informada
    #             #
    #             return []
    #         else:
    #             #
    #             # nesse ponto, temos um período com data inicial e data final informados
    #             # seleciona os servidores que estavam no setor (OU descendentes) no período informado
    #             #
    #             setores = [self]
    #             if recursivo:
    #                 setores += self.descendentes
    #
    #             if not data_final:
    #                 data_final = datetime.date.today()
    #             #
    #             # selecionar os servidores envolvidos via históricos de setor
    #             #
    #
    #             qs_1 = ServidorSetorHistorico.objects.filter(
    #                 setor__in=setores, data_inicio_no_setor__lte=data_final, data_fim_no_setor__gte=data_inicial
    #             )  # inicio fora e termino dentro do período (incluindo extremidades)
    #
    #             qs_2 = ServidorSetorHistorico.objects.filter(
    #                 setor__in=setores, data_inicio_no_setor__lte=data_final, data_fim_no_setor__isnull=True
    #             )
    #
    #             historicos_setor = (
    #                 (qs_1 | qs_2).exclude(servidor__data_fim_servico_na_instituicao__lt=data_inicial).distinct().order_by("servidor__nome")
    #             )
    #
    #             servidores = []
    #             for historico_setor in historicos_setor:
    #                 if not historico_setor.servidor in servidores:
    #                     servidores.append(historico_setor.servidor)
    #
    #             return servidores
    #
    # def get_funcionarios(self, recursivo=True):
    #     if recursivo:
    #         return Funcionario.objects.filter(setor__in=self.descendentes)
    #     else:
    #         return Funcionario.objects.filter(setor=self)
    #
    # @property
    # def setor_eh_campus(self):
    #     return hasattr(self, "unidadeorganizacional")
    #
    # @property
    # def eh_orgao_colegiado(self):
    #     tipo_orgao = TipoUnidadeOrganizacional.objects.filter(descricao="Conselhos e Órgãos Colegiados").first()
    #     if self.setor_eh_campus:
    #         return self.unidadeorganizacional.tipo == tipo_orgao
    #     return False

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
            if hasattr(s, "unidade"):
                s_repr = f'<span class="admin-setor-uo" title="{s.nome}">{s}</span>'
            elif s == caminho[-1]:
                s_repr = f'<span class="admin-setor" title="{s.nome}">{s} ({s.nome})</span>'
            else:
                s_repr = f'<span title="{s.nome}">{s}</span>'
            caminho_html.append(s_repr)
        return mark_safe(" &rarr; ".join(caminho_html))


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
            ChefiaSetorHistorico.objects.filter(
                setor=self,
            )
            .filter(Q(data_fim_funcao__gte=hoje) | Q(data_fim_funcao__isnull=True))
            .values_list("chefe_imediato", flat=True)
        )
        return ChefiaPPE.objects.filter(excluido=False, pk__in=chefes)

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
        historico_funcao = ChefiaSetorHistorico.objects.filter(
            setor=self,
            data_inicio_funcao__gte=data_inicial,
            data_inicio_funcao__lte=data_final,
        )

        # data de inicio da funcao antes do período informado e data fim da função depois da data inicio do período
        historico_funcao = historico_funcao | ChefiaSetorHistorico.objects.filter(
            setor=self,
            data_inicio_funcao__lt=data_inicial,
            data_fim_funcao__gte=data_inicial,
        )

        # data de inicio da funcao antes do período informado e sem data fim
        historico_funcao = historico_funcao | ChefiaSetorHistorico.objects.filter(
            setor=self,
            data_inicio_funcao__lt=data_inicial,
            data_fim_funcao__isnull=True,
        )

        # data de fim da funcao deve está dentro do período informado
        historico_funcao = historico_funcao | ChefiaSetorHistorico.objects.filter(
            setor=self,
            data_fim_funcao__gte=data_final,
            data_fim_funcao__lte=data_final,
        )

        return historico_funcao.distinct()

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
class FormacaoTecnica (ModelPlus):
    descricao = CharFieldPlus(verbose_name='Descrição', help_text='')

    class Meta:
        verbose_name = 'Formação técnica'
        verbose_name_plural = 'Formações técnicas'

    def __str__(self):
        return self.descricao

class ChefiaPPE(ModelPlus):
    nome = UnaccentField(max_length=200, db_index=True)
    cpf = models.CharField(max_length=20, null=True, verbose_name="CPF", blank=False, db_index=True)
    funcao = models.CharField('Função', max_length=60, )
    formacao = models.CharField('Formação', max_length=100)
    email = models.EmailField(blank=True, verbose_name="E-mail Principal")
    excluido = models.BooleanField(verbose_name="Excluído", default=False,
                                   help_text="Indica se a última ocorrência é de exclusão")
    pessoa_fisica = ForeignKeyPlus("rh.PessoaFisica")
    vinculos = GenericRelation(
        "comum.Vinculo", related_query_name="chefiappe", object_id_field="id_relacionamento",
        content_type_field="tipo_relacionamento"
    )
    class Meta:
        verbose_name = 'Chefia imediata'
        verbose_name_plural = 'Chefias imediatas'

    def get_absolute_url(self):
        return "/ppe/chefia_imediata/{:d}/".format(self.id)

    def get_ext_combo_template(self):
        template = """
                    <div class="person">
                        <div>
                            <h4>{} ({})</h4>
                            <h5>Chefia</h5>
                        </div>
                    </div>
                    """.format(
            self.nome or "Sem nome", self.cpf
        )

        if self.pessoa_fisica.excluido:
            template += '<p class="false">Vínculo inativo</p>'

        return template
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

    def get_user(self):
        from comum.models import User

        qs = User.objects.filter(username=self.cpf.replace(".", "").replace("-", ""))
        return qs.exists() and qs[0] or None

    def get_vinculo(self):
        return self.vinculos.first()

    @property
    def pessoafisica(self):
        return self.pessoa_fisica

    def enviar_email_pre_cadastro(self):
        conteudo = f'''<h1>Ativação de Cadastro de Chefia imediata - SUAP </h1>
        <p>Prezado(a) {self.nome},</p>
        <p>Foi realizado um cadastro de Chefia imediata no SUAP/FESFSUS</p>    
        <p><a href="{settings.SITE_URL}">{settings.SITE_URL}</a></p>.

        '''
        return send_mail('[SUAP] Cadastro de Chefia imediata', conteudo, settings.DEFAULT_FROM_EMAIL, [self.email])

    def save(self, *args, **kwargs):
        from comum.models import Vinculo

        self.matricula = re.sub(r"\D", "", str(self.cpf)) or None

        instance = self.__dict__.copy()
        instance.pop("id")
        instance.pop("_state")
        instance.pop("matricula")
        instance.pop("formacao")
        instance.pop("funcao")
        instance.pop("pessoa_fisica_id")
        instance['username'] = self.matricula
        if "_pessoa_fisica_cache" in instance:
            instance.pop("_pessoa_fisica_cache")

        if not self.pk and not getattr(self, "pessoa_fisica", None):
            self.pessoa_fisica = PessoaFisica.objects.create(**instance)
        else:
            PessoaFisica.objects.filter(id=self.pessoa_fisica.id).update(**instance)
        super().save(*args, **kwargs)

        qs = Vinculo.objects.filter(chefiappe=self)
        if not qs.exists():
            vinculo = Vinculo()
        else:
            vinculo = qs.first()
        vinculo.pessoa = self.pessoa_fisica.pessoa_ptr
        vinculo.relacionamento = self
        vinculo.user = self.pessoa_fisica.user
        vinculo.save()
        self.enviar_email_pre_cadastro()
        return self



class SequencialMatriculaTrabalhadorEducando(ModelPlus):
    prefixo = CharFieldPlus(max_length=255)
    contador = PositiveIntegerField()

    @staticmethod
    def proximo_numero(prefixo):
        qs_sequencial = SequencialMatriculaTrabalhadorEducando.objects.filter(prefixo=prefixo)
        if qs_sequencial.exists():
            sequencial = qs_sequencial[0]
            contador = sequencial.contador
        else:
            sequencial = SequencialMatriculaTrabalhadorEducando()
            sequencial.prefixo = prefixo
            contador = 1
        sequencial.contador = contador + 1
        sequencial.save()
        numero = f'000000000{contador}'
        matricula = f'{prefixo}{numero[-4:]}'
        if TrabalhadorEducando.objects.filter(matricula=matricula).exists():
            return SequencialMatriculaTrabalhadorEducando.proximo_numero(prefixo)
        else:
            return matricula


class TrabalhadorEducando(LogPPEModel):
    SEARCH_FIELDS = ["pessoa_fisica__search_fields_optimized", "matricula"]

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
    TECNICO_ADM = "TÉCNICO EM ADMINISTRAÇÃO"
    TECNICO_ANALCLIN = "TÉCNICO EM ANÁLISES CLÍNICAS"
    TECNICO_COMERC = "TÉCNICO EM COMÉRCIO"
    TECNICO_COMUNIC = "TÉCNICO EM COMUNICAÇÃO VISUAL"
    TECNICO_CONT = "TÉCNICO EM CONTABILIDADE"
    TECNICO_ENF = "TÉCNICO EM ENFERMAGEM"
    TECNICO_FAR = "TÉCNICO EM FARMÁCIA"
    TECNICO_FIN = "TÉCNICO EM FINANÇAS"
    TECNICO_GERSAUDE = "TÉCNICO EM GERÊNCIA EM SAÚDE"
    TECNICO_INF = "TÉCNICO EM INFORMÁTICA"
    TECNICO_LOG = "TÉCNICO EM LOGÍSTICA"
    TECNICO_MANUTINFO = "TÉCNICO EM MANUTENÇÃO E SUPORTE EM INFORMÁTICA"
    TECNICO_MEIOAMB = "TÉCNICO EM MEIO AMBIENTE"
    TECNICO_NUTRI = "TÉCNICO EM NUTRIÇÃO E DIETÉTICA"
    TECNICO_RH = "TÉCNICO EM RECURSOS HUMANOS"
    TECNICO_REDES = "TÉCNICO EM REDES DE COMPUTADORES"
    TECNICO_SBUC = "TÉCNICO EM SAÚDE BUCAL"
    TECNICO_SECRET = "TÉCNICO EM SECRETARIADO"
    TECNICO_SEGTRAB = "TÉCNICO EM SEGURANÇA DO TRABALHO"
    TECNICO_VENDAS = "TÉCNICO EM VENDAS"

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
        [TECNICO_ADM, TECNICO_ADM],
        [TECNICO_ANALCLIN, TECNICO_ANALCLIN],
        [TECNICO_COMERC, TECNICO_COMERC],
        [TECNICO_COMUNIC, TECNICO_COMUNIC],
        [TECNICO_CONT, TECNICO_CONT],
        [TECNICO_ENF, TECNICO_ENF],
        [TECNICO_FAR, TECNICO_FAR],
        [TECNICO_FIN, TECNICO_FIN],
        [TECNICO_GERSAUDE, TECNICO_GERSAUDE],
        [TECNICO_INF, TECNICO_INF],
        [TECNICO_LOG, TECNICO_LOG],
        [TECNICO_MANUTINFO, TECNICO_MANUTINFO],
        [TECNICO_MEIOAMB, TECNICO_MEIOAMB],
        [TECNICO_NUTRI, TECNICO_NUTRI],
        [TECNICO_RH, TECNICO_RH],
        [TECNICO_REDES, TECNICO_REDES],
        [TECNICO_SBUC, TECNICO_SBUC],
        [TECNICO_SECRET, TECNICO_SECRET],
        [TECNICO_SEGTRAB, TECNICO_SEGTRAB],
        [TECNICO_VENDAS, TECNICO_VENDAS],
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
    matricula = CharFieldPlus('Matrícula', max_length=255, db_index=True)
    foto = ImageWithThumbsField(storage=get_overwrite_storage(), use_id_for_name=True, upload_to='trabalhadoreseducandos',
                                sizes=((75, 100), (150, 200)), null=True, blank=True)
    pessoa_fisica = ForeignKeyPlus('rh.PessoaFisica', verbose_name='Pessoa Física', related_name='trabalhadoreducando_set')
    estado_civil = CharFieldPlus(choices=ESTADO_CIVIL_CHOICES, null=True)
    numero_dependentes = PositiveIntegerFieldPlus('Número de Dependentes', null=True)

    # endereco
    logradouro = CharFieldPlus(max_length=255, verbose_name='Logradouro (Avenida, Rua, etc)', null=True)
    numero = CharFieldPlus(max_length=255, verbose_name='Número', null=True)
    complemento = CharFieldPlus(max_length=255, verbose_name='Complemento', null=True, blank=True)
    bairro = CharFieldPlus(max_length=255, verbose_name='Bairro', null=True)
    cep = CharFieldPlus(max_length=255, verbose_name='CEP', null=True, blank=True)
    cidade = ForeignKeyPlus('comum.Municipio', verbose_name='Cidade', null=True)
    tipo_zona_residencial = CharFieldPlus(choices=TIPO_ZONA_RESIDENCIAL_CHOICES, verbose_name='Zona Residencial',
                                                 null=True, blank=True)

    # endereco profissional
    logradouro_profissional = CharFieldPlus(max_length=255, verbose_name='Logradouro Profissional', null=True,
                                                   blank=True)
    numero_profissional = CharFieldPlus(max_length=255, verbose_name='Número Profissional', null=True,
                                               blank=True)
    complemento_profissional = CharFieldPlus(max_length=255, verbose_name='Complemento Profissional', null=True,
                                                    blank=True)
    bairro_profissional = CharFieldPlus(max_length=255, verbose_name='Bairro Profissional', null=True,
                                               blank=True)
    cep_profissional = CharFieldPlus(max_length=255, verbose_name='CEP Profissional', null=True, blank=True)
    cidade_profissional = ForeignKeyPlus('comum.Municipio', verbose_name='Cidade Profissional', null=True,
                                                related_name='trabalhadoreducando_cidade_profissional_set')
    tipo_zona_residencial_profissional = CharFieldPlus(choices=TIPO_ZONA_RESIDENCIAL_CHOICES,
                                                              verbose_name='Zona Residencial Profissional', null=True,
                                                              blank=True)
    telefone_profissional = CharFieldPlus(max_length=255, verbose_name='Telefone Profissional', null=True,
                                                 blank=True)

    # dados familiares
    nome_pai = CharFieldPlus(max_length=255, verbose_name='Nome do Pai', null=True, blank=True)
    estado_civil_pai = CharFieldPlus(verbose_name='Estado Civil do Pai', choices=ESTADO_CIVIL_CHOICES, null=True, blank=True)
    nome_mae = CharFieldPlus(max_length=255, verbose_name='Nome da Mãe', null=True, blank=False)
    estado_civil_mae = CharFieldPlus(verbose_name='Estado Civil da Mãe', choices=ESTADO_CIVIL_CHOICES, null=True, blank=True)
    responsavel = CharFieldPlus(max_length=255, verbose_name='Nome do Responsável', null=True, blank=True)
    parentesco_responsavel = CharFieldPlus(verbose_name='Parentesco do Responsável', choices=PARENTESCO_CHOICES,
                                                  null=True, blank=True)
    autorizacao_carteira_estudantil = models.BooleanField(
        verbose_name='Autorização para Emissão da Carteira Estudantil',
        help_text='O aluno autoriza o envio de seus dados pessoais para o Sistema Brasileiro de Educação (SEB) para fins de emissão da carteira de estudante digital de acordo com a Medida Provisória Nº 895, de 6 de setembro de 2019',
        default=False,
    )

    # contato
    telefone_principal = CharFieldPlus(max_length=255, verbose_name='Telefone Principal', null=True, blank=False)
    telefone_secundario = CharFieldPlus(max_length=255, verbose_name='Telefone Secundário', null=True,
                                               blank=True)
    telefone_adicional_1 = CharFieldPlus(max_length=255, verbose_name='Telefone do Responsável', null=True,
                                                blank=True)
    telefone_adicional_2 = CharFieldPlus(max_length=255, verbose_name='Telefone do Responsável', null=True,
                                                blank=True)
    facebook = models.URLField('Facebook', blank=True, null=True)
    instagram = models.URLField('Instagram', blank=True, null=True)
    twitter = models.URLField('Twitter', blank=True, null=True)
    linkedin = models.URLField('Linkedin', blank=True, null=True)
    skype = CharFieldPlus('Skype', blank=True, null=True)

    # outras informacoes
    tipo_sanguineo = CharFieldPlus(max_length=255, verbose_name='Tipo Sanguíneo', null=True, blank=True,
                                          choices=TIPO_SANGUINEO_CHOICES)
    nacionalidade = CharFieldPlus(max_length=255, verbose_name='Nacionalidade', null=True,
                                         choices=TIPO_NACIONALIDADE_CHOICES)
    passaporte = CharFieldPlus(max_length=50, verbose_name='Nº do Passaporte', default='')
    pais_origem = ForeignKeyPlus('comum.Pais', verbose_name='País de Origem', null=True, blank=True,
                                        help_text='Obrigatório para estrangeiros')
    naturalidade = ForeignKeyPlus(
        'comum.Municipio',
        verbose_name='Naturalidade',
        null=True,
        blank=True,
        related_name='trabalhadoreducando_naturalidade_set',
        help_text='Cidade em que o(a) trabalhadoreducando nasceu. Obrigatório para brasileiros',
    )

    tipo_necessidade_especial = CharFieldPlus(verbose_name='Tipo de Necessidade Especial', null=True, blank=True,
                                                     choices=TIPO_NECESSIDADE_ESPECIAL_CHOICES)
    tipo_transtorno = CharFieldPlus(verbose_name='Tipo de Transtorno', null=True, blank=True,
                                           choices=TIPO_TRANSTORNO_CHOICES)
    superdotacao = CharFieldPlus(verbose_name='Superdotação', null=True, blank=True,
                                        choices=SUPERDOTACAO_CHOICES)

    # dados escolares
    nivel_ensino_anterior = ForeignKeyPlus('comum.NivelEnsino', null=True, blank=True, on_delete=models.CASCADE)
    tipo_instituicao_origem = CharFieldPlus(max_length=255, verbose_name='Tipo de Instituição', null=True,
                                                   choices=TIPO_INSTITUICAO_ORIGEM_CHOICES, blank=True)
    nome_instituicao_anterior = CharFieldPlus(max_length=255, verbose_name='Nome da Instituição', null=True,
                                                     blank=True)
    ano_conclusao_estudo_anterior = ForeignKeyPlus(
        'comum.Ano', verbose_name='Ano de Conclusão de Estudo Anterior',
        null=True,
        related_name='trabalhadoreducando_ano_conclusao_anterior_set',
        blank=True,
        on_delete=models.CASCADE
    )
    habilitacao_pedagogica = CharFieldPlus(max_length=255,
                                                  verbose_name='Habilitação para Curso de Formação Pedagógica',
                                                  null=True, blank=True)

    categoria = CharFieldPlus('Categoria', max_length=100, choices=CATEGORIAS_CHOICES, null=True, blank=True)

    formacao_tecnica = ForeignKeyPlus('ppe.FormacaoTecnica', verbose_name='Formação técnica ',
                              null=True, blank=True)
    data_admissao = DateFieldPlus(verbose_name='Data de Admissão', null=True, blank=True)
    data_demissao = DateFieldPlus(verbose_name='Data de Demissão', null=True, blank=True)
    numero_registro = CharFieldPlus('Número de Registro no Conselho de Fiscalização Profissional', null=True, blank=True)
    conselho = ForeignKeyPlus('comum.ConselhoProfissional', verbose_name='Conselho de Fiscalização Profissional', null=True, blank=True)

    # rg
    numero_rg = CharFieldPlus(max_length=255, verbose_name='Número do RG', null=True, blank=True)
    uf_emissao_rg = ForeignKeyPlus('comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
                                          related_name='trabalhadoreducando_emissor_rg_set')
    orgao_emissao_rg = ForeignKeyPlus('comum.OrgaoEmissorRg', verbose_name='Orgão Emissor', null=True, blank=True)
    data_emissao_rg = DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)

    # titulo_eleitor
    numero_titulo_eleitor = CharFieldPlus(max_length=255, verbose_name='Título de Eleitor', null=True,
                                                 blank=True)
    zona_titulo_eleitor = CharFieldPlus(max_length=255, verbose_name='Zona', null=True, blank=True)
    secao = CharFieldPlus(max_length=255, verbose_name='Seção', null=True, blank=True)
    data_emissao_titulo_eleitor = DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    uf_emissao_titulo_eleitor = ForeignKeyPlus(
        'comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
        related_name='trabalhadoreducando_emissor_titulo_eleitor_set', on_delete=models.CASCADE
    )

    # carteira de reservista
    numero_carteira_reservista = CharFieldPlus(max_length=255, verbose_name='Número da Carteira de Reservista',
                                                      null=True, blank=True)
    regiao_carteira_reservista = CharFieldPlus(max_length=255, verbose_name='Região', null=True, blank=True)
    serie_carteira_reservista = CharFieldPlus(max_length=255, verbose_name='Série', null=True, blank=True)
    estado_emissao_carteira_reservista = ForeignKeyPlus(
        'comum.UnidadeFederativa', verbose_name='Estado Emissor', null=True, blank=True,
        related_name='trabalhadoreducando_estado_emissor_carteira_reservista_set', on_delete=models.CASCADE
    )
    ano_carteira_reservista = models.PositiveIntegerField(verbose_name='Ano', null=True, blank=True)

    # certidao_civil
    tipo_certidao = CharFieldPlus(max_length=255, verbose_name='Tipo de Certidão', null=True, blank=True,
                                         choices=TIPO_CERTIDAO_CHOICES)
    cartorio = CharFieldPlus(max_length=255, verbose_name='Cartório', null=True, blank=True)
    numero_certidao = CharFieldPlus(max_length=255, verbose_name='Número de Termo', null=True, blank=True)
    folha_certidao = CharFieldPlus(max_length=255, verbose_name='Folha', null=True, blank=True)
    livro_certidao = CharFieldPlus(max_length=255, verbose_name='Livro', null=True, blank=True)
    data_emissao_certidao = DateFieldPlus(verbose_name='Data de Emissão', null=True, blank=True)
    matricula_certidao = CharFieldPlus(max_length=255, verbose_name='Matrícula', null=True, blank=True)

    # dados da matrícula
    data_matricula = DateTimeFieldPlus(verbose_name='Data da Matrícula', auto_now_add=True)
    cota_sistec = CharFieldPlus(max_length=255, verbose_name='Cota SISTEC', null=True,
                                       choices=COTA_SISTEC_CHOICES, blank=True)
    cota_mec = CharFieldPlus(max_length=255, verbose_name='Cota MEC', null=True, choices=COTA_MEC_CHOICES,
                                    blank=True)

    renda_per_capita = models.DecimalField(
        null=True,
        max_digits=15,
        decimal_places=2,
        verbose_name='Renda Per Capita',
        help_text='Número de salários mínimos ganhos pelos integrantes da família dividido pelo número de integrantes',
    )

    observacao_historico = models.TextField('Observação para o Histórico', null=True, blank=True)
    observacao_matricula = models.TextField('Observação da Matrícula', null=True, blank=True)

    alterado_em = DateTimeFieldPlus('Data de Alteração', auto_now=True, null=True, blank=True)
    email_academico = models.EmailField('Email Acadêmico', blank=True)
    email_qacademico = models.EmailField('Email Q-Acadêmico', blank=True)
    email_google_classroom = models.EmailField('Email do Google Classroom', blank=True)

    csf = models.BooleanField(verbose_name='Ciência sem Fronteiras', default=False)

    # caracterizacao_socioeconomica
    documentada = models.BooleanField('Doc. Entregue', default=False)
    data_documentacao = models.DateTimeField('Data de Entrega da Documentação', null=True)

    # saúde
    cartao_sus = CharFieldPlus('Cartão SUS', null=True, blank=True)

    codigo_educacenso = CharFieldPlus('Código EDUCACENSO', null=True, blank=True)

    nis = CharFieldPlus('NIS', null=True, help_text='Número de Identificação Social', blank=True)

    poder_publico_responsavel_transporte = CharFieldPlus(
        'Poder Público Responsável pelo Transporte Escolar', choices=PODER_PUBLICO_RESPONSAVEL_TRANSPORTE_CHOICES,
        null=True, blank=True
    )
    tipo_veiculo = CharFieldPlus('Tipo de Veículo Utilizado no Transporte Escolar',
                                        choices=TIPO_VEICULO_CHOICES_FOR_FORM, null=True, blank=True)
    vinculos = GenericRelation(
        'comum.Vinculo', related_query_name='trabalhadoreseducandos_set',
        object_id_field='id_relacionamento',
        content_type_field='tipo_relacionamento'
    )

    formacao = ForeignKeyPlus('ppe.FormacaoPPE', null=True, blank=True)
    turma = ForeignKeyPlus('ppe.Turma', null=True, blank=True)
    situacao = ForeignKeyPlus('ppe.SituacaoMatricula', verbose_name='Situação', on_delete=models.CASCADE,null=True, blank=True)

    class Meta:
        ordering = ('pessoa_fisica__nome',)
        verbose_name = 'Trabalhador Educando'
        verbose_name_plural = 'Trabalhadores Educandos'

        permissions = (
            ('efetuarmatriculatrabalhadoreducando', 'Pode efetuar o cadastro de Trabalhador Educando'),
            ('emitir_diploma', 'Pode emitir diploma de Trabalhador Educando'),
            ('emitir_boletim', 'Pode emitir boletim de Trabalhador Educando'),
            ('emitir_historico', 'Pode emitir histórico de Trabalhador Educando'),
            ('efetuar_matricula', 'Pode efetuar matricula de Trabalhador Educando'),
            ('pode_sincronizar_dados', 'Pode sincronizar dados de Trabalhador Educando'),
            ('gerar_relatorio', 'Pode gerar relatórios de Trabalhador Educando'),
            ('pode_ver_chave_acesso_pais', 'Pode ver chave de acesso dos pais'),
            ('change_foto', 'Pode editar foto de Trabalhador Educando'),
            ('view_dados_academicos', 'Pode visualizar dados acadêmicos de Trabalhador Educando'),
            ('view_dados_pessoais', 'Pode visualizar dados pessoais de Trabalhador Educando'),
        )


    @property
    def papeis(self):
        return self.pessoa_fisica.papel_set.all()

    @property
    def papeis_ativos(self):
        hoje = datetime.date.today()
        papeis_datas_menores_hoje = self.pessoa_fisica.papel_set.filter(data_inicio__lte=hoje)
        return papeis_datas_menores_hoje.filter(data_fim__isnull=True) | papeis_datas_menores_hoje.filter(data_fim__gte=hoje)


    def get_etapas_disponives(self):
        etapas = []
        hoje = datetime.date.today()

        from ppe.models import EtapaMonitoramento, Avaliacao
        id_tipo_avaliacao_respondidas = self.avaliacao_set.filter(papel_avalidor=Avaliacao.AUTOAVALIACAO).values_list('tipo_avaliacao__id', flat=True)
        qs_etapas = EtapaMonitoramento.objects.filter(data_inicio__lte=hoje)

        for etapa in qs_etapas:
            avaliacao = self.avaliacao_set.filter(tipo_avaliacao=etapa.tipo_avaliacao, papel_avalidor=Avaliacao.AUTOAVALIACAO)
            if not avaliacao.exists():
                if not etapa.tipo_avaliacao.pre_requisito or (etapa.tipo_avaliacao.pre_requisito and etapa.tipo_avaliacao.pre_requisito.id in id_tipo_avaliacao_respondidas):
                    etapas.append(etapa)

        return etapas

    def get_observacoes(self):
        return self.observacao_set.all()

    def get_setor_atual(self):
        hoje = datetime.date.today()
        historico = self.trabalhadorsetorhistorico_set.filter(data_inicio__lte=hoje, data_fim__isnull=True).first()
        if historico:
            return historico.setor
        else:
            return None

    def get_unidade_atual(self):
        setor = self.get_setor_atual()
        if setor:
            return Unidade.objects.filter(setor=setor.get_caminho()[0].id).first()
        else:
            return None

    def get_chefe_atual(self):
        setor = self.get_setor_atual()
        if setor:
            return setor.chefes.first()
        else:
            return None

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
        self.pessoa_fisica.eh_trabalhadoreducando = True
        if self.passaporte:
            self.pessoa_fisica.passaporte = self.passaporte
        self.pessoa_fisica.save()

        user = self.get_user()
        qs = Vinculo.objects.filter(trabalhadoreseducandos_set=self)  # TO-DO: corrigir lá no model Vinculo
        if not qs.exists():
            vinculo = Vinculo()
        else:
            vinculo = qs.first()
        vinculo.pessoa = self.pessoa_fisica.pessoa_ptr
        vinculo.user = user
        vinculo.relacionamento = self
        vinculo.save()

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
        return f'/ppe/trabalhadoreducando/{self.matricula}/'

    def pode_matricula_online(self):
        return True
    
    #checar isso depois
    def pode_emitir_declaracao(self):
        # if self.curso_campus.modalidade_id is None:
        #     return False
        # alunos de Curso FIC anterior a 2018
        # if self.curso_campus.modalidade.pk == Modalidade.FIC and self.ano_letivo.ano < 2018:
        #     return False
        # # alunos que ainda são do Q-Acadêmico
        # if not self.matriz and not self.eh_aluno_minicurso():
        #     return False
        return True

    # def is_ultima_matricula_em_aberto(self):
    #     from ppe.models import SituacaoMatricula
    #     return self.get_ultima_matricula().situacao.id == SituacaoMatricula.EM_ABERTO

    def possui_vinculo(self):
        from ppe.models import SituacaoMatricula
        situacao_valida = (            
            self.situacao.pk == SituacaoMatricula.TRANCADO
            or self.situacao.pk == SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE
        )
        if situacao_valida:
            return True
        else:
            return self.situacao.pk == SituacaoMatricula.MATRICULADO and not self.get_ultima_matricula().curso_turma.is_aberto()

    def get_ultima_matricula(self):
        return self.get_matriculas_curso_turma().first()

    def is_matriculado(self):
        from ppe.models import SituacaoMatricula
        return self.situacao and self.situacao.pk == SituacaoMatricula.MATRICULADO
    
    def get_urls_documentos(self):
        lista = []
        # if self.pode_emitir_declaracao():
        #     lista.append(('Declaração de Vínculo', f'/edu/declaracaovinculo_pdf/{self.pk}/'))
        # if self.possui_historico():            
        if self.is_matriculado() and self.pode_emitir_declaracao():
            # lista.append(('Declaração de Carga Horária Integralizada', f'/edu/declaracao_ch_cumprida_pdf/{self.pk}/'))
            # if not self.is_ultima_matricula_em_aberto():
            lista.append(('Declaração de Matrícula', f'/ppe/declaracaomatriculappe_pdf/{self.pk}/'))
                #lista.append(('Comprovante de Dados Acadêmicos', f'/edu/comprovante_dados_academicos_pdf/{self.pk}'))
        return lista
    
    def get_matriculas_curso_turma(self):#, orderbyDesc=True):
        qs = self.matriculacursoturma_set
        return qs
        # if ate_ano_letivo and ate_periodo_letivo:
        # if self.curso_campus.periodicidade == CursoCampus.PERIODICIDADE_SEMESTRAL:
        #     qs = (
        #         qs.filter(ano_letivo__ano__lte=ate_ano_letivo.ano)
        #         .exclude(ano_letivo__ano=ate_ano_letivo.ano, periodo_letivo=ate_periodo_letivo)
        #         .exclude(ano_letivo__ano=ate_ano_letivo.ano, periodo_letivo=2)
        #     )
        # else:
        #     qs = qs.filter(ano_letivo__ano__lt=ate_ano_letivo.ano)

        # if orderbyDesc:
        #     return qs.order_by('-ano_letivo__ano', '-periodo_letivo')
        # else:
        #     return qs.order_by('ano_letivo__ano', 'periodo_letivo')
    
    @staticmethod
    def random(size=20, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
        """Returns a randomic string."""
        return ''.join([choice(allowed_chars) for _ in range(size)])

    @staticmethod
    def codificar(s):
        left = TrabalhadorEducando.random(7, '0123456789')
        right = TrabalhadorEducando.random(13, '0123456789')
        s = str(s).encode("utf-8").hex()
        return f'{left}{s}{right}'

    @staticmethod
    def decodificar(s):
        s = s[7:]
        s = s[:-13]
        s = bytes.fromhex(str(s)).decode("utf-8")
        return s

    def get_matricula_codificada(self):
        return TrabalhadorEducando.codificar(self.matricula)

    def get_foto_75x100_url(self):
        return self.foto and self.foto.url_75x100 or '/static/comum/img/default.jpg'

    def get_foto_150x200_url(self):
        return self.foto and self.foto.url_150x200 or '/static/comum/img/default.jpg'

    def criar_papel_discente(self):
        if 'rh' in settings.INSTALLED_APPS:
            Papel = apps.get_model('rh', 'Papel')
            ContentType = apps.get_model('contenttypes.ContentType')
            trabalhadoreducando = self.get_vinculo().relacionamento
            if not trabalhadoreducando.papeis_ativos.exists():

                kwargs = dict(
                    detalhamento=f"{trabalhadoreducando.matricula} - Discente",
                    descricao=f"{trabalhadoreducando.matricula} - Discente",
                    data_fim=None
                )
                papel_cargo, criou = Papel.objects.update_or_create(
                    pessoa=trabalhadoreducando.pessoa_fisica,
                    tipo_papel=Papel.TIPO_PAPEL_DISCENTE,
                    data_inicio=datetime.datetime.now(),
                    papel_content_type=ContentType.objects.get_for_model(trabalhadoreducando),
                    papel_content_id=trabalhadoreducando.id,
                    defaults=kwargs,
                )
    def get_historico(self, final=False, ordernar_por=1, exibir_optativas=False, eletronico=False):


        grupos_cursos = OrderedDict()
        grupos_cursos['Formação Permanente'] = []
        grupos_cursos['Transversais'] = []
        grupos_cursos['Específicos'] = []
        observacoes = []

        # ids_componenentes_associados = list(
        #     self.matriz.componentecurricular_set.filter(componente_curricular_associado__isnull=False).values_list('componente_curricular_associado__componente', flat=True)
        # )
        # ids_componenentes_associados_pagos = list(
        #     MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self, equivalencia_componente__componente__in=ids_componenentes_associados)
        #     .exclude(situacao__in=(MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_REPROVADO_POR_FALTA))
        #     .values_list('equivalencia_componente__componente', flat=True)
        # ) + list(
        #     MatriculaDiario.objects.filter(
        #         matricula_periodo__aluno=self, situacao=MatriculaDiario.SITUACAO_APROVADO, diario__componente_curricular__componente__in=ids_componenentes_associados
        #     ).values_list('diario__componente_curricular__componente', flat=True)
        # )

        # for pk in ids_componenentes_associados:
        #     pk_nao_certificaveis.append(pk)
        #
        # for pk in ids_componenentes_associados_pagos:
        #     if pk in ids_componenentes_associados:
        #         ids_componenentes_associados.remove(pk)

        qs_cursos = self.formacao.cursoformacaoppe_set.all()





        # if ordernar_por == Aluno.ORDENAR_HISTORICO_POR_COMPONENTE:
        #     qs_componentes_curriculares = qs_componentes_curriculares.order_by('componente__sigla')
        # elif ordernar_por == Aluno.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ:
        #     qs_componentes_curriculares = qs_componentes_curriculares.order_by('periodo_letivo')

        # for pk in (
        #     MatriculaDiario.objects.exclude(situacao__in=[MatriculaDiario.SITUACAO_CURSANDO, MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_CANCELADO])
        #     .filter(matricula_periodo__aluno=self)
        #     .values_list('diario__componente_curricular__componente__id', flat=True)
        # ):
        #     pk_nao_certificaveis.append(pk)
        # for pk in MatriculaDiarioResumida.objects.filter(matricula_periodo__aluno=self).values_list('equivalencia_componente__componente__id', flat=True):
        #     pk_nao_certificaveis.append(pk)
        # for pk in AproveitamentoEstudo.objects.filter(matricula_periodo__aluno=self).values_list('componente_curricular__componente__id', flat=True):
        #     pk_nao_certificaveis.append(pk)
        # for pk in CertificacaoConhecimento.objects.filter(matricula_periodo__aluno=self).values_list('componente_curricular__componente__id', flat=True):
        #     pk_nao_certificaveis.append(pk)

        for curso in qs_cursos:
            cursos_formacao = curso.get_grupo_componente_historico(grupos_cursos)

            repetir = True
            curso_cursado = None

            componente = dict(
                pk=None,
                matricula_diario=None,
                matricula_diario_resumida=None,
                sigla_componente=curso.curso.codigo,
                descricao_componente=curso.curso.descricao,
                codigo_turma=None,
                codigo_diario='',
                carga_horaria=curso.curso.ch_total or '-',
                media_final_disciplina=None,
                percentual_carga_horaria_frequentada=None,
                situacao_display=None,
                situacao_legend='',
                certificavel=False,
                cursada=False,
                certificada=False,
                aproveitada=False,
                equivalente=False,
            )
            cursos_formacao.append(componente)




        for grupo in list(grupos_cursos.values()):
            for componente in grupo:
                componente['sigla_componente'] = insert_space(componente['sigla_componente'], 9)

        filiacao = []
        if self.nome_pai:
            filiacao.append(self.nome_pai)
        if self.nome_mae:
            filiacao.append(self.nome_mae)
        filiacao = normalizar_nome_proprio(format_iterable(filiacao))

        if self.observacao_historico:
            observacoes.append(self.observacao_historico)

        historico = dict()
        historico.update(assinatura_eletronica=eletronico)
        # DADOS PESSOAIS
        historico.update(
            sexo=self.pessoa_fisica.sexo,
            nome=self.get_nome_social_composto(),
            cpf=self.pessoa_fisica.cpf,
            data_nascimento=self.pessoa_fisica.nascimento_data,
            nacionalidade=self.nacionalidade and self.get_nacionalidade_display() or None,
            naturalidade=self.naturalidade,
        )
        historico.update(professores=[])
        # RG
        historico.update(numero_rg=self.numero_rg, orgao_emissao_rg=self.orgao_emissao_rg, uf_emissao_rg=self.uf_emissao_rg, data_emissao_rg=self.data_emissao_rg)
        # FILIAÇÃO
        historico.update(nome_pai=self.nome_pai, nome_mae=self.nome_mae)
        # ENDEREÇO
        historico.update(logradouro=self.logradouro, numero=self.numero, complemento=self.complemento, bairro=self.bairro, cidade=self.cidade, cep=self.cep)
        # TÍTULO DE ELEITOR
        historico.update(
            numero_titulo_eleitor=self.numero_titulo_eleitor,
            zona_titulo_eleitor=self.zona_titulo_eleitor,
            secao_titulo_eleitor=self.secao,
            uf_emissao_titulo_eleitor=self.uf_emissao_titulo_eleitor,
            data_emissao_titulo_eleitor=self.data_emissao_titulo_eleitor,
        )
        # CARTEIRA RESERVISTA
        historico.update(
            numero_carteira_reservista=self.numero_carteira_reservista,
            regiao_carteira_reservista=self.regiao_carteira_reservista,
            serie_carteira_reservista=self.serie_carteira_reservista,
            uf_emissao_carteira_reservista=self.estado_emissao_carteira_reservista,
            ano_carteira_reservista=self.ano_carteira_reservista,
        )
        # DADOS ACADEMICOS
        historico.update(
            matricula=self.matricula,
            situacao=self.situacao,
            data_matricula=self.data_matricula,
        )
        # DADOS DO CURSO
        # historico.update(
        #     codigo_emec_curso=self.curso_campus.codigo_emec,
        #     descricao_curso=self.curso_campus.descricao_historico,
        #     regime=self.matriz.estrutura.get_tipo_avaliacao_display,
        #     periodicidade=self.curso_campus.get_periodicidade_display,
        #     descricao_matriz=self.matriz.descricao,
        #     reconhecimento_texto=self.matriz_curso.get_reconhecimento(),
        #     resolucao_criacao=self.matriz_curso.get_autorizacao()
        # )



        # # QUADRO RESUMO
        # historico.update(
        #     ch_componentes_obrigatorios=self.matriz and self.get_ch_componentes_regulares_obrigatorios_esperada() or 0,
        #     ch_componentes_obrigatorios_cumprida=self.matriz and self.get_ch_componentes_regulares_obrigatorios_cumprida() or 0,
        #     ch_componentes_optativos=self.matriz and self.get_ch_componentes_regulares_optativos_esperada() or 0,
        #     ch_componentes_optativos_cumprida=self.matriz and self.get_ch_componentes_regulares_optativos_cumprida() or 0,
        #     ch_componentes_eletivos=self.matriz and self.get_ch_componentes_eletivos_esperada() or 0,
        #     ch_componentes_eletivos_cumprida=self.matriz and self.get_ch_componentes_eletivos_cumprida() or 0,
        #     ch_componentes_seminario=self.matriz and self.get_ch_componentes_seminario_esperada() or 0,
        #     ch_componentes_seminario_cumprida=self.matriz and self.get_ch_componentes_seminario_cumprida() or 0,
        #     ch_componentes_pratica_como_componente=self.matriz and self.get_ch_pratica_como_componente_esperada() or 0,
        #     ch_componentes_pratica_como_componente_cumprida=self.matriz and self.get_ch_componentes_pratica_como_componente_cumprida() or 0,
        #     ch_componentes_visita_tecnica=self.matriz and self.get_ch_visita_tecnica_esperada() or 0,
        #     ch_componentes_visita_tecnica_cumprida=self.matriz and self.get_ch_componentes_visita_tecnica_cumprida() or 0,
        #     ch_componentes_pratica_profissional=self.matriz and self.get_ch_componentes_pratica_profissional_esperada(incluir_atpa=True) or 0,
        #     ch_componentes_pratica_profissional_cumprida=self.matriz and self.get_ch_componentes_pratica_profissional_cumprida(incluir_atpa=True) or 0,
        #     ch_componentes_tcc=self.matriz and self.get_ch_componentes_tcc_esperada() or 0,
        #     ch_componentes_tcc_cumprida=self.matriz and self.get_ch_componentes_tcc_cumprida() or 0,
        #     ch_atividades_complementares=self.matriz and self.get_ch_atividades_complementares_esperada() or 0,
        #     ch_atividades_complementares_cumprida=self.matriz and self.get_ch_atividades_complementares_cumprida() or 0,
        #     ch_atividades_extensao=self.matriz and self.get_ch_atividades_extensao_esperada() or 0,
        #     ch_atividades_extensao_cumprida=self.matriz and self.get_ch_atividade_extensao_cumprida() or 0,
        #     ch_total=self.matriz and self.matriz.get_carga_horaria_total_prevista() or 0,
        #     ch_total_cumprida=self.matriz and self.get_carga_horaria_total_cumprida() or 0,
        # )
        # # DIPLOMA
        # registro_emissao_diploma = self.get_registro_emissao_diploma()
        # historico.update(
        #     data_conclusao_curso=self.dt_conclusao_curso,
        #     data_emissao_diploma=self.data_expedicao_diploma,
        #     data_colacao_grau=self.get_data_colacao_grau(),
        #     responsavel_emissao_diploma=registro_emissao_diploma and registro_emissao_diploma.emissor or None,
        #     emitiu_diploma=registro_emissao_diploma is not None,
        #     livro=registro_emissao_diploma and registro_emissao_diploma.get_livro(),
        #     folha=registro_emissao_diploma and registro_emissao_diploma.folha,
        #     numero_registro=registro_emissao_diploma and registro_emissao_diploma.numero_registro,
        #     data_expedicao=registro_emissao_diploma and registro_emissao_diploma.data_expedicao,
        #     dirigente_maximo=registro_emissao_diploma and registro_emissao_diploma.dirigente_maximo or None,
        # )

        # COMPONENTES
        historico.update(grupos_cursos=grupos_cursos, observacoes=observacoes)

        return historico

    def get_turmas_matricula_online(self, turma_indisponiveis_com_motivo=None):
        turmas = []
        from ppe.models import Turma
        turmas = Turma.objects.all()

        return turmas

    #TODO
    def pode_matricular_turma(self):
        return self.turma == None

    #TODO
    def pode_remover_da_turma(self, user):
        return True

    def pode_ser_matriculado_no_curso_turma(self, curso_turma, ignorar_quebra_requisito=False):
        from ppe.models import MatriculaCursoTurma
        if MatriculaCursoTurma.objects.filter(
            trabalhador_educando=self,
            curso_turma__curso_formacao__curso__descricao=curso_turma.curso_formacao.curso.descricao,
            situacao=MatriculaCursoTurma.SITUACAO_CURSANDO,
        ).exists():
            return False, 'O aluno está cursando este curso.'
        #TODO

        # qs_componente_curricular = self.formacao.cursoformacaoppe_set.filter(curso=curso_turma.curso)
        # if qs_componente_curricular.exists():
        #     componente_curricular = qs_componente_curricular[0]
        #     return self.pode_cursar_componente_curricular(componente_curricular, False, ignorar_quebra_requisito)
        # else:
        #     return self.pode_cursar_componente_curricular(diario.componente_curricular, True, ignorar_quebra_requisito)

        return True, ''


    def pode_ser_matriculado_no_curso_turma(self, curso_turma, ignorar_quebra_requisito=False):
        from ppe.models import MatriculaCursoTurma
        if MatriculaCursoTurma.objects.filter(
            trabalhador_educando=self,
            curso_turma=curso_turma,
            situacao=MatriculaCursoTurma.SITUACAO_CURSANDO,
        ).exists():
            return False, 'O trabalhador está cursando este componente em outro diário.'

        return True, ''

class Observacao(LogPPEModel):
    observacao = models.TextField('Observação da Matrícula')
    trabalhadoreducando = ForeignKeyPlus(TrabalhadorEducando, verbose_name='Trabalhador Educando')
    data = DateFieldPlus(verbose_name='Data')
    usuario = ForeignKeyPlus('comum.User', verbose_name='Usuário', related_name='trabalhadoreducando_observacao_set')

    class Meta:
        permissions = (('adm_delete_observacao', 'Pode deletar observações de outros usuários'),)

#FES ANAMINESE

class TrabalhoAnteriorAoPPE(ModelPlus):
    descricao = CharFieldPlus(verbose_name='Trabalho Antes de Ingressar ao ppe', help_text='')

    class Meta:
        verbose_name = 'Trabalho Antes de Ingressar ao ppe'
        verbose_name_plural = '(Anamnese) Trabalhos Antes de Ingressar ao ppe'

    def __str__(self):
        return self.descricao

class MeioTransporte (ModelPlus):
    descricao = CharFieldPlus(verbose_name='Meio de Transporte para deslocamento para o trabalho', help_text='')

    class Meta:
        verbose_name = 'Meio de Transporte para deslocamento para o trabalho'
        verbose_name_plural = '(Anamnese) Meios de Transporte para deslocamento para o trabalho'

    def __str__(self):
        return self.descricao

class ResideCom (ModelPlus):
    descricao = CharFieldPlus(verbose_name='Pessoa com a qual o Trabalhador Educando reside', help_text='')

    class Meta:
        verbose_name = 'Pessoa com a qual o Trabalhador Educando reside'
        verbose_name_plural = '(Anamnese) Pessoas com as quais o Trabalhador Educando reside'

    def __str__(self):
        return self.descricao

class MembrosCarteiraAssinada (ModelPlus):
    descricao = CharFieldPlus(verbose_name='Pessoa da família do Trabalhador Educando que tem carteira assinada', help_text='')

    class Meta:
        verbose_name = 'Pessoa da família do Trabalhador Educando que tem carteira assinada'
        verbose_name_plural = '(Anamnese) Pessoas da família do Trabalhador Educando que tem carteira assinada'

    def __str__(self):
        return self.descricao

class ResidenciaSaneamentoBasico (ModelPlus): 
    descricao = CharFieldPlus(verbose_name='Tipo de Saneamento básico', help_text='')

    class Meta:
        verbose_name = 'Saneamento básico'
        verbose_name_plural = '(Anamnese) Saneamentos básicos'

    def __str__(self):
        return self.descricao

class ItensResidencia (ModelPlus): 
    descricao = CharFieldPlus(verbose_name='Item da Residência do Trabalhador Educando', help_text='')

    class Meta:
        verbose_name = 'Item da Residência do Trabalhador Educando'
        verbose_name_plural = '(Anamnese) Itens da Residência do Trabalhador Educando'

    def __str__(self):
        return self.descricao

class ParticipacaoGruposSociais (ModelPlus): 
    descricao = CharFieldPlus(verbose_name='Grupo Social que o Trabalhador Educando participa', help_text='')

    class Meta:
        verbose_name = 'Grupo Social que o trabalhador educando participa'
        verbose_name_plural = '(Anamnese) Grupos Sociais que o trabalhador educando participa'

    def __str__(self):
        return self.descricao

class CursosTrabalhadorEducando (ModelPlus): 
    descricao = CharFieldPlus(verbose_name='Curso que o trabalhador educando realiza/realizou', help_text='')

    class Meta:
        verbose_name = 'Curso que o trabalhador educando realiza/realizou'
        verbose_name_plural = '(Anamnese) Cursos que o trabalhador educando realiza/realizou'

    def __str__(self):
        return self.descricao

class RedeSocial (ModelPlus): 
    descricao = CharFieldPlus(verbose_name='Rede social que trabalhador educando participa', help_text='')

    class Meta:
        verbose_name = 'Rede social que trabalhador educando participa'
        verbose_name_plural = '(Anamnese) Redes sociais que trabalhador educando participa'

    def __str__(self):
        return self.descricao

class Anamnese (LogPPEModel):
    NAO = False
    SIM = True
    SIM_NAO_CHOICES = (
        (NAO, 'Não'),
        (SIM, 'Sim')
    )

    EMPTY_CHOICES = [['', '----']]
    ESTADO_CIVIL_CHOICES = [['Solteiro(a)', 'Solteiro(a)'], ['Casado(a)', 'Casado(a)'], ['Separado(a)', 'Separado(a)'],
                            ['Divorciado(a)', 'Divorciado(a)'], ['Viúvo(a)', 'Viúvo(a)'], ['União Estável', 'União Estável'], 
                            ['Outro', 'Outro']]
    SEXO_IDENTIDADE_GENERO_CHOICES = [['Masculino', 'Masculino'], ['Feminino', 'Feminino'], ['Pessoa transsexual', 'Pessoa transsexual'], ['Outro', 'Outro']]
    ORIENTACAO_SEXUAL_CHOICES = [['Heterossexual', 'Heterossexual'], ['Homossexual', 'Homossexual'],
                                ['Bissexual', 'Bissexual'], ['Outro', 'Outro']]
    RACA_COR_CHOICES = [['Branco', 'Branco'], ['Preto', 'Preto'], ['Amarelo', 'Amarelo'], ['Pardo', 'Pardo'], ['Indígena', 'Indígena']]
    RELIGIAO_CHOICES = [['Católica', 'Católica'], ['Evangélica', 'Evangélica'], ['Candomblé', 'Candomblé'], 
                        ['Umbanda', 'Umbanda'], ['Espírita', 'Espírita'], ['Ateu', 'Ateu'], 
                        ['Sem religião', 'Sem religião'], ['Outra religião', 'Outra religião']]
    DENOMINACAO_EVANGELICA_CHOICES = [['Assembléia de Deus', 'Assembléia de Deus'], ['Pentecostal', 'Pentecostal'], 
                                    ['Universal', 'Universal'], ['Adventista', 'Adventista'], ['Presbiteriana', 'Presbiteriana'], 
                                    ['Batista', 'Batista'], ['Outra', 'Outra']]
    TRABALHO_ANTERIOR_PPE_CHOICES = [['Setor privado com carteira assinada', 'Setor privado com carteira assinada'], 
                                    ['Setor privado sem carteira assinada', 'Setor privado sem carteira assinada'], 
                                    ['Autônomo', 'Autônomo'], ['Aprendiz', 'Aprendiz'], ['Outros', 'Outros']]
    MEIO_TRANSPORTE_CHOICES = [['Onibus', 'Ônibus'], ['Carro', 'Carro'], ['Moto', 'Moto'], 
                                ['Bicicleta', 'Bicicleta'], ['Metrô', 'Metrô'], ['Outros', 'Outros']] 
    RESIDE_COM_CHOICES = [['Sozinho', 'Sozinho'], ['Pai', 'Pai'], ['Mãe', 'Mãe'], ['Irmãos', 'Irmãos'], 
                            ['Primos', 'Primos'], ['Avós', 'Avós'], ['Tios', 'Tios'], ['Esposo(a)', 'Esposo(a)'], 
                            ['Outras pessoas', 'Outras pessoas']]
    MEMBROS_CARTEIRA_ASSINADA_CHOICES = [['Você', 'Você'], ['Pai', 'Pai'], ['Mãe', 'Mãe'], ['Irmãos', 'Irmãos'], 
                                            ['Primos', 'Primos'], ['Avós', 'Avós'], ['Tios', 'Tios'], ['Esposo(a)', 'Esposo(a)'], 
                                            ['Outras pessoas', 'Outras pessoas']]
    RENDA_FAMILIAR_CHOICES = [['1 SM', 'Até um salário mínimo (SM)'], ['1 e 3', 'Entre 1 e 3 SM'], 
                            ['3 e 5', 'Entre 3 e 5 SM'], ['5 e 7', 'Entre 5 e 7 SM'], ['Acima 7 SM', 'Acima de 7 SM']]
    RESPONSABILIDADE_FINANCEIRA_CHOICES = [['Unico', 'Único(a) Responsável'], 
                                            ['Principal', 'Principal responsável, mas recebe ajuda de outra(s) pessoa(s)'], 
                                            ['Divide', 'Divide igualmente as responsabilidades com outra(s) pessoa(s)'], 
                                            ['Contribui', 'Contribui apenas com uma pequena parte'], 
                                            ['Nao', 'Não tem nenhuma responsabilidade financeira']]
    VEICULO_CHOICES = [['Nao', 'Não possui'], ['Carro Exclusivo', 'Carro de uso exclusivo'], 
                        ['Carro Compartilhado', 'Carro compartilhado com outra(s) pessoa(s)'], 
                        ['Moto Exclusiva', 'Moto de uso exclusivol'], 
                        ['Moto Compartilhada', 'Moto compartilhada com outra(s) pessoa(s)']]
    MORADIA_CHOICES = [['Propria Familiar', 'Própria: Familiar'], ['Propria Pessoal', 'Própria: Pessoal'], 
                        ['Alugada', 'Alugada'], ['Emprestada', 'Emprestada']]
    TIPO_MORADIA_CHOICES = [['Casa', 'Casa'], ['Apartamento', 'Apartamento']]
    ESTRUTURA_MORADIA_CHOICES = [['Alvenaria', 'Alvenaria (Bloco)'], ['Madeira', 'Madeira'], ['Sape', 'Sapê'], 
                                    ['Taipa', 'Taipa'], ['Outro', 'Outro']]    
    CONSUMO_BEBIDA_ALCOOLICA_CHOICES = [['Nao', 'Não'], ['Uma vez mês', 'Uma vez por mês ou menos'], 
                                        ['Uma vez semana', 'Uma vez por semana '], ['2 e 4 vezes semana', 'Entre 2 e 4 vezes por semana'], 
                                        ['Diariamente', 'Diariamente']]
    FORMA_INGRESSO_CHOICES = [['Enem', 'Enem'], ['Vestibular', 'Vestibular'],]
    MODALIDADE_ENSINO_CHOICES = [['Presencial', 'Presencial'], ['EAD', 'EAD (Ensino à Distância)'], ['Semi presencial', 'Semi presencial (EAD e presencial)']]
    TIPO_INSTITUICAO_CHOICES = [['Pública', 'Pública'], ['Particular', 'Particular'],]
    FORMA_INGRESSO_CHOICES = [['Nao', 'Não'], ['PROUNI', 'PROUNI'],['FIES', 'FIES'], ['Outros', 'Outros']]


    trabalhador_educando = models.OneToOneField(TrabalhadorEducando, verbose_name='Trabalhador Educando', on_delete=models.CASCADE)
    nome = CharFieldPlus(max_length=255, verbose_name='Nome Completo')
    cpf = BrCpfField(verbose_name='CPF (apenas números)')
    telefone = CharFieldPlus(max_length=255, verbose_name='Telefone (xx) 9 xxxx-xxxx')
    numero_whatsapp = CharFieldPlus(max_length=255, verbose_name='Número do Whatsapp', blank=True, null=True)
    email = CharFieldPlus(max_length=255, verbose_name='E-mail')
    participa_rede_social = models.ManyToManyField(RedeSocial, verbose_name = 'Participa de alguma rede social?')
    link_facebook = models.URLField(verbose_name = 'Link da sua conta no Facebook', blank=True, null=True)
    link_instagram = models.URLField(verbose_name = 'Link da sua conta no Instagram', blank=True, null=True)
    outra_rede_social = models.URLField(verbose_name = 'Link da sua conta em outras redes sociais (se tiver)', blank=True, null=True)
    identidade_genero = CharFieldPlus(max_length=255, verbose_name = 'Sexo / identidade de gênero', choices=SEXO_IDENTIDADE_GENERO_CHOICES)
    outro_genero = CharFieldPlus(max_length=255, verbose_name = 'Se outro gênero, qual?', blank=True, null=True)
    orientacao_sexual = CharFieldPlus(max_length=255, verbose_name = 'Qual a sua orientação sexual?', choices=ORIENTACAO_SEXUAL_CHOICES)
    outra_orientacao = CharFieldPlus(max_length=255, verbose_name = 'Se outra orientação sexual, qual?', blank=True, null=True)
    idade = PositiveIntegerFieldPlus(verbose_name = 'Idade')
    raça = CharFieldPlus(max_length=255, verbose_name = 'Raça / Cor', choices=RACA_COR_CHOICES)
    religiao = CharFieldPlus(max_length=255, verbose_name = 'Religião', choices=RELIGIAO_CHOICES)
    outra_religiao = CharFieldPlus(max_length=255, verbose_name = 'Se outra religião, qual?', blank=True, null=True)
    denominacao_evangelica = CharFieldPlus(max_length=255, verbose_name = 'Se for evangélica, informe a denominação a qual está vinculado(a)', blank=True, null=True, choices=DENOMINACAO_EVANGELICA_CHOICES)
    outra_denominacao_evangelica = CharFieldPlus(max_length=255, verbose_name = 'Se outra denominação, qual?', blank=True, null=True)
    cidade = ForeignKeyPlus('comum.Municipio', verbose_name='Cidade de nascimento', on_delete=models.CASCADE)
    #estado = ForeignKeyPlus('comum.UnidadeFederativa', verbose_name='Estado de nascimento', on_delete=models.CASCADE)
    trabalhou_anteriormente = models.BooleanField(verbose_name = 'Você já trabalhou antes do PPE?')
    onde_trabalhou_anteriormente = models.ManyToManyField(TrabalhoAnteriorAoPPE, verbose_name = 'Caso você tenha trabalhado antes de ingressar no PPE, onde foi?', blank=True)
    outro_tipo_trabalho = CharFieldPlus(max_length=255, verbose_name = 'Se outros tipos de trabalho, quais?', blank=True, null=True)

    #caracterizacao geral ppe 
    ano_conclusao_tecnico_medio = PositiveIntegerFieldPlus(verbose_name = 'Ano de conclusão do curso técnico de nível médio')
    ano_ingresso_ppe = PositiveIntegerFieldPlus(verbose_name = 'Ano de ingresso no Programa Primeiro Emprego (PPE)', min_value = 2016)
    formacao_tecnica = CharFieldPlus(max_length=255, verbose_name = 'Formação Técnica')
    municipio_antes_ppe = ForeignKeyPlus('comum.Municipio', verbose_name = 'Município de Moradia antes do PPE', related_name='anamnese_municipio_anterior_ppe_set', on_delete=models.CASCADE)
    municipio_ppe = ForeignKeyPlus('comum.Municipio', verbose_name = 'Município onde trabalhará pelo PPE', related_name='anamnese_municipio_ppe_set', on_delete=models.CASCADE)
    unidade_trabalho = CharFieldPlus(max_length=255, verbose_name = 'Unidade / Local de trabalho onde atuará')
    meio_transporte = models.ManyToManyField(MeioTransporte, verbose_name = 'Qual o meio de transporte utilizadoem seu deslocamento para o trabalho?')
    outro_meio = CharFieldPlus(max_length=255, verbose_name = 'Se outros meios de transporte, quais?', blank=True, null=True)

    #estrutura familiar
    chefe_parental = models.BooleanField(verbose_name = 'Você era chefa de família monoparental (sozinha)? (pergunta exclusiva para mulheres)', blank=True, null=True, choices=SIM_NAO_CHOICES)
    estado_civil = CharFieldPlus(max_length=255, verbose_name = 'Estado Civil', choices=ESTADO_CIVIL_CHOICES)
    outro_estado_civil = CharFieldPlus(max_length=255, verbose_name = 'Se outro estado civil, qual?', blank=True, null=True)
    tem_filhos = models.BooleanField(verbose_name = 'Tem filhos?')
    quantidade_filhos = PositiveIntegerFieldPlus(verbose_name = "Se sim, quantos filhos?", blank=True, null=True)
    local_residencia = CharFieldPlus(max_length=255, verbose_name = 'Local de residência')
    cidade_residencia = CharFieldPlus(max_length=255, verbose_name = 'Cidade de residência')
    reside_com = models.ManyToManyField(ResideCom, verbose_name = 'Reside com')
    ouras_pessoas_moradia = CharFieldPlus(max_length=255, verbose_name = 'Se outras pessoas moram com você, quem são?', blank=True, null=True)
    total_moradores = PositiveIntegerFieldPlus(verbose_name = "Número total de moradores")
    membros_familia_carteira_assinada = models.ManyToManyField(MembrosCarteiraAssinada, verbose_name = 'Quais membros da sua família trabalham com carteira assinada?')
    outros_membros_carteira_assinada = CharFieldPlus(max_length=255, verbose_name = 'Se outras pessoas, quais?', blank=True, null=True)
    renda_familiar = CharFieldPlus(max_length=255, verbose_name = 'Renda familiar mensal', choices=RENDA_FAMILIAR_CHOICES)
    responsabilidade_financeira = CharFieldPlus(max_length=255, verbose_name = 'Qual a sua responsabilidade financeira pela manutenção da sua família?', choices=RESPONSABILIDADE_FINANCEIRA_CHOICES)
    veiculo_automotor = CharFieldPlus(max_length=255, verbose_name = 'Veículo automotor', choices=VEICULO_CHOICES)

    #estrutura residencial 
    moradia = CharFieldPlus(max_length=255, verbose_name = 'Moradia', choices=MORADIA_CHOICES)
    tipo_moradia = CharFieldPlus(max_length=255, verbose_name = 'Tipo de moradia', choices=TIPO_MORADIA_CHOICES)
    estrutura_moradia = CharFieldPlus(max_length=255, verbose_name = 'Estrutura da moradia', choices=ESTRUTURA_MORADIA_CHOICES)
    outro_tipo_moradia = CharFieldPlus(max_length=255, verbose_name = 'Se outro tipo de moradia, qual?', blank=True, null=True)
    quantidade_quartos = CharFieldPlus(max_length=255, verbose_name = 'Quantidade de quartos')
    quantidade_banheiros = CharFieldPlus(max_length=255, verbose_name = 'Quantidade de banheiros')
    residencia_saneamento_basico = models.ManyToManyField(ResidenciaSaneamentoBasico, verbose_name = 'Sua residência tem (*pode escolher mais de uma opção)')
    outra_fonte_agua = CharFieldPlus(max_length=255, verbose_name = 'Se outra fonte de água, qual?', blank=True, null=True)
    outro_tipo_esgoto = CharFieldPlus(max_length=255, verbose_name = 'Se outro tipo de esgoto, qual?', blank=True, null=True)
    outra_fonte_energia = CharFieldPlus(max_length=255, verbose_name = 'Se outra fonte de energia, qual?', blank=True, null=True)
    itens_residencia = models.ManyToManyField(ItensResidencia, verbose_name = 'Sua residência tem (*pode escolher mais de uma opção)')
    quantidade_tvs = PositiveIntegerFieldPlus(verbose_name = 'Quantos aparelhos de televisão?')
    quantidade_celulares = PositiveIntegerFieldPlus(verbose_name = 'Quantos aparelhos celulares?')
    quantidade_computadores = PositiveIntegerFieldPlus(verbose_name = 'Quantos computadores?')
    quantidade_notebooks = PositiveIntegerFieldPlus(verbose_name = 'Quantos notebook?')
    quantidade_tablets = PositiveIntegerFieldPlus(verbose_name = 'Quantos tablets?')

    #estilo vida 
    fumante = models.BooleanField(verbose_name = 'Fumo', choices=SIM_NAO_CHOICES)
    bebida_alcoolica = CharFieldPlus(max_length=255, verbose_name = 'Consumo de bebida alcoólica', choices=CONSUMO_BEBIDA_ALCOOLICA_CHOICES)
    substancias_psicoativas = CharFieldPlus(max_length=255, verbose_name = 'Uso de substâncias psicoativas (drogas não permitidas)', choices=CONSUMO_BEBIDA_ALCOOLICA_CHOICES)
    atividade_fisica = CharFieldPlus(max_length=255, verbose_name = 'Pratica atividade física', choices=CONSUMO_BEBIDA_ALCOOLICA_CHOICES)
    participa_grupos_sociais = models.ManyToManyField(ParticipacaoGruposSociais, verbose_name = 'Participação em grupos sociais (*pode escolher mais de uma opção)')
    participa_conselho_politica = CharFieldPlus(max_length=255, verbose_name = 'Se participa de conselhos depolíticas públicas, quais são?', blank=True, null=True)
    participa_outros_grupos = CharFieldPlus(max_length=255, verbose_name = 'Se participo de outros grupos sociais, quais são?', blank=True, null=True)

    #habitos estudo
    fez_cursos = models.ManyToManyField(CursosTrabalhadorEducando, verbose_name = 'Você fez ou faz algum desses cursos?')
    outro_curso_tecnico = CharFieldPlus(max_length=255, verbose_name = 'Se outro curso técnico de nível médio, qual?', blank=True, null=True)
    outro_curso_profissional = CharFieldPlus(max_length=255, verbose_name = 'Se outro curso de qualificação profissional, qual?', blank=True, null=True)
    outro_curso = CharFieldPlus(max_length=255, verbose_name = 'Se outro curso, qual?', blank=True, null=True)
    tentou_faculdade = models.BooleanField(verbose_name = 'Tentou acesso à faculdade/universidade?', choices=SIM_NAO_CHOICES)
    ingressou_faculdade = models.BooleanField(verbose_name = 'Ingressou em algumafaculdade/universidade?', choices=SIM_NAO_CHOICES)
    ano_faculdade = PositiveIntegerFieldPlus(verbose_name = 'Caso tenha ingressado emfaculdade/universidade, em que ano iniciou?', blank=True, null=True)
    forma_ingresso_faculdade = CharFieldPlus(max_length=255, verbose_name = 'Caso tenha ingressado em faculdade/universidade, qual a forma de ingresso', blank=True, null=True)
    modalidade_faculdade = CharFieldPlus(max_length=255, verbose_name = 'Caso tenha ingressado em faculdade/universidade, qual modalidade de ensino?', blank=True, null=True)
    tipo_faculdade = CharFieldPlus(max_length=255, verbose_name = 'Caso tenha ingressado emfaculdade/universidade, qual tipode instituição?', blank=True, null=True)
    beneficio_faculdade = CharFieldPlus(max_length=255, verbose_name = 'Caso a faculdade/universidade seja particular, você recebe benefício de algum programa?', blank=True, null=True)
    outro_beneficio = CharFieldPlus(max_length=255, verbose_name = 'Se outro tipo de benefício, qual?', blank=True, null=True)

    class Meta:
        verbose_name = 'Anamnese do Trabalhador Educando'

    def __str__(self):
        return 'Anamnese'


class TrabalhadorSetorHistorico(ModelPlus):
    trabalhador_educando = ForeignKeyPlus("ppe.TrabalhadorEducando", null=False, on_delete=models.CASCADE)
    data_inicio = DateFieldPlus(null=False, blank=False, db_index=True,
                                              verbose_name="Data de Início")
    data_fim = DateFieldPlus(null=True, blank=True, verbose_name="Data de Fim")
    setor = ForeignKeyPlus(
        "ppe.Setor", null=True, blank=False, related_name="setor_trabalhador", on_delete=models.CASCADE,
        verbose_name="Setor Lotação Trabalhador"
    )

    class Meta:
        verbose_name = "Histórico de Setor do Trabalhador Educando"
        verbose_name_plural = "Históricos de Setores do Trabalhador Educando"
    @property
    def estah_ativa(self):
        hoje = datetime.date.today()
        if self.data_inicio > hoje:
            return False
        return not self.data_chefia or self.data_fim_chefia >= hoje


class ChefiaSetorHistorico(ModelPlus):

    chefe_imediato = ForeignKeyPlus("ppe.ChefiaPPE", null=False, on_delete=models.CASCADE)
    data_inicio_funcao = DateFieldPlus(null=False, blank=False, db_index=True, verbose_name="Data de Início da Função")
    data_fim_funcao = DateFieldPlus(null=True, blank=False, verbose_name="Data de Fim da Função")
    setor = ForeignKeyPlus("ppe.Setor", null=False, blank=False, on_delete=models.CASCADE)
    nome_amigavel = CharFieldPlus(verbose_name="Nome Amigável", default="")
    def __str__(self):
        data_fim = self.data_fim_funcao.strftime("%d/%m/%Y") if self.data_fim_funcao else "Atual"
        return "{} : {} - Setor SIAPE: {} - de {} à {}".format(
            self.nome_amigavel, self.chefe_imediato, self.setor, self.data_inicio_funcao.strftime("%d/%m/%Y"), data_fim
        )

    class Meta:
        # unique_together = ("chefe_imediato", "data_inicio_funcao")
        verbose_name = "Histórico de Chefia"
        verbose_name_plural = "Histórico de Chefias"


    @property
    def estah_ativa(self):
        hoje = datetime.date.today()
        if self.data_inicio_funcao > hoje:
            return False
        return not self.data_fim_funcao or self.data_fim_funcao >= hoje

    @atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)



