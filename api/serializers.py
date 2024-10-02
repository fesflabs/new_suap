import datetime
import html
from collections import OrderedDict

from django.utils.html import strip_tags
from rest_framework import serializers

from ae.models import Programa, Participacao
from api.models import AplicacaoOAuth2 as Application
from api.services_utils import ResponseSerializer
from comum.models import User
from contracheques.models import ContraCheque, ContraChequeRubrica as ContraChequeRubricaModel
from contratos.models import Contrato
from demandas.models import Atualizacao
from edu.models import Aluno, ProfessorDiario, ProfessorMinicurso, DiarioEspecial
from edu.models import CursoCampus
from edu.models.diarios import MaterialDiario, ItemConfiguracaoAvaliacao, Diario
from edu.models.historico import MatriculaPeriodo, MatriculaDiario
from eventos.models import Banner
from ferias.models import Ferias, InterrupcaoFerias
from patrimonio.models import Inventario
from pesquisa.models import Projeto as ProjetoPesquisa, Participacao as PartPesquisa
from ponto.models import Frequencia
from projetos.models import Projeto as ProjetoExtensao, Participacao as PartExtensao
from protocolo.models import Processo, Tramite
from rh.models import Servidor, UnidadeOrganizacional, Setor, ServidorOcorrencia, ServidorAfastamento
from django.conf import settings


class Autenticacao(ResponseSerializer):
    login_autenticado = serializers.CharField(help_text='Username do usuário')


class Token(ResponseSerializer):
    token = serializers.CharField()


class Profile(ResponseSerializer):
    matricula = serializers.CharField(required=False, allow_blank=True)
    nome_usual = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    url_foto_75x100 = serializers.CharField(required=False, allow_blank=True)
    cargo = serializers.CharField(required=False, allow_blank=True)
    setor = serializers.CharField(required=False, allow_blank=True)
    telefones = serializers.CharField(required=False, allow_blank=True)

    def set_profile_from_pessoa_fisica(self, pessoa_fisica):
        self.nome_usual = pessoa_fisica.nome_usual
        self.email = pessoa_fisica.email
        self.url_foto_75x100 = pessoa_fisica.get_foto_75x100_url()
        try:
            self.matricula = str(pessoa_fisica.funcionario.servidor.matricula)
        except Exception:
            self.matricula = ''
        try:
            self.cargo = str(pessoa_fisica.funcionario.servidor.cargo_emprego)
        except Exception:
            self.cargo = ''
        try:
            self.setor = str(pessoa_fisica.funcionario.setor)
        except Exception:
            self.setor = ''
        self.telefones = pessoa_fisica.telefones_institucionais


class PontoFrequencia(ResponseSerializer):
    data_referencia = serializers.CharField(help_text="Formato 'dd/mm/aaaa'")
    jornada_trabalho = serializers.CharField(help_text='Em horas')
    registros = serializers.CharField(help_text="Formato 'hh:mm|hh:mm|...'")
    carga_horaria = serializers.CharField(help_text="Formato 'hh:mm:ss'")


class TempoIntervalo(ResponseSerializer):
    data_referencia = serializers.CharField(help_text="Formato 'dd/mm/aaaa'")
    horas = serializers.IntegerField()
    minutos = serializers.IntegerField()
    segundos = serializers.IntegerField()
    minutos_inteiros = serializers.IntegerField()
    segundos_inteiros = serializers.IntegerField()
    terceiro_registro_ocorrido = serializers.BooleanField()


class EventoCalendarioAdministrativo(ResponseSerializer):
    data_inicio = serializers.CharField(help_text="Formato 'dd/mm/aaaa'")
    data_fim = serializers.CharField(help_text="Formato 'dd/mm/aaaa'")
    descricao = serializers.CharField(help_text="Formato 'dd/mm/aaaa'")
    #
    # usados na comparação entre 2 eventos
    _data_inicio = None
    _data_fim = None
    _descricao = ""

    def __init__(self, **kwargs):
        data_inicio = kwargs.pop('data_inicio', None)
        data_fim = kwargs.pop('data_fim', None)
        descricao = kwargs.pop('descricao', "")
        #
        if data_inicio:
            self.data_inicio = data_inicio.strftime('%d/%m/%Y')
        if data_fim:
            self.data_fim = data_fim.strftime('%d/%m/%Y')
        self.descricao = descricao
        #
        self._data_inicio = data_inicio
        self._data_fim = data_fim
        self._descricao = descricao
        #
        super().__init__(**kwargs)

    def __eq__(self, other):
        inicio_dia = self._data_inicio.day
        inicio_mes = self._data_inicio.month
        inicio_ano = self._data_inicio.year
        fim_dia = self._data_fim.day
        fim_mes = self._data_fim.month
        fim_ano = self._data_fim.year
        descricao = self._descricao.upper()
        #
        outro_evento_inicio_dia = other._data_inicio.day
        outro_evento_inicio_mes = other._data_inicio.month
        outro_evento_inicio_ano = other._data_inicio.year
        outro_evento_fim_dia = other._data_fim.day
        outro_evento_fim_mes = other._data_fim.month
        outro_evento_fim_ano = other._data_fim.year
        outro_evento_descricao = other._descricao.upper()
        #
        eh_igual = (
            inicio_dia == outro_evento_inicio_dia
            and inicio_mes == outro_evento_inicio_mes
            and inicio_ano == outro_evento_inicio_ano
            and descricao == outro_evento_descricao
            and fim_dia == outro_evento_fim_dia
            and fim_mes == outro_evento_fim_mes
            and fim_ano == outro_evento_fim_ano
        )
        #
        return eh_igual


class CalendarioAdministrativo(ResponseSerializer):
    ano = serializers.CharField()
    campus = serializers.CharField()
    documentos_legais = EventoCalendarioAdministrativo(many=True)
    eventos = EventoCalendarioAdministrativo(many=True)
    recessos = EventoCalendarioAdministrativo(many=True)
    feriados = EventoCalendarioAdministrativo(many=True)
    ferias = EventoCalendarioAdministrativo(many=True)


class EstatisticaServidores(ResponseSerializer):
    quantidade_ativos = serializers.IntegerField()


class ListaServidores(ResponseSerializer):
    quantidade = serializers.IntegerField()
    servidores = Profile(many=True)


class ContraChequeMesAno(ResponseSerializer):
    mes = serializers.CharField()
    ano = serializers.CharField()


class ContraChequeDisponivel(ResponseSerializer):
    meses = ContraChequeMesAno(many=True)


class ContraChequeRubrica(ResponseSerializer):
    descricao = serializers.CharField(source='rubrica.nome')
    valor = serializers.CharField()


class ContraChequeDetalhe(ContraChequeMesAno):
    vantagens = ContraChequeRubrica(many=True)
    descontos = ContraChequeRubrica(many=True)
    total_vantagens = serializers.CharField()
    total_descontos = serializers.CharField()
    total_liquido = serializers.CharField()


class VersaoApp(ResponseSerializer):
    tipo_versao = serializers.CharField()
    ultima_versao = serializers.CharField(allow_blank=True)
    ultima_versao_link = serializers.CharField(allow_blank=True)
    penultima_versao = serializers.CharField(allow_blank=True)
    penultima_versao_link = serializers.CharField(allow_blank=True)


class MeuProcesso(ResponseSerializer):
    data_cadastro = serializers.CharField(help_text="Formato 'dd/mm/aaaa'")
    assunto = serializers.CharField()
    numero_processo = serializers.CharField()
    setor_atual = serializers.CharField()
    responsavel_atual = serializers.CharField()
    status = serializers.CharField(help_text=', '.join(['{} - {}'.format(status[0], status[1]) for status in Processo.PROCESSO_STATUS]))


class MeusProcessos(ResponseSerializer):
    meus_processos = MeuProcesso(many=True)


class AlunoSerializer(serializers.ModelSerializer):
    nome = serializers.SerializerMethodField()
    curso = serializers.CharField(source='curso_campus.descricao_historico')
    campus = serializers.CharField(source='curso_campus.diretoria.setor.uo')
    situacao = serializers.CharField(source='situacao.descricao')
    cota_sistec = serializers.SerializerMethodField()
    cota_mec = serializers.SerializerMethodField()
    situacao_sistemica = serializers.SerializerMethodField()
    matricula_regular = serializers.BooleanField(source='aluno_especial')
    linha_pesquisa = serializers.SerializerMethodField()
    curriculo_lattes = serializers.URLField(source='pessoa_fisica.lattes')

    def get_nome(self, obj):
        return obj.get_nome()

    def get_cota_sistec(self, obj):
        return obj.get_cota_sistec_display()

    def get_cota_mec(self, obj):
        return obj.get_cota_mec_display()

    def get_situacao_sistemica(self, obj):
        return obj.get_situacao_sistemica()[1]

    def get_linha_pesquisa(self, obj):
        if obj.linha_pesquisa:
            return obj.linha_pesquisa.descricao
        else:
            return None

    class Meta:
        model = Aluno
        fields = ('matricula', 'nome', 'curso', 'campus', 'situacao', 'cota_sistec', 'cota_mec', 'situacao_sistemica', 'matricula_regular', 'linha_pesquisa', 'curriculo_lattes')


class AlunoCarometro(serializers.ModelSerializer):
    nome = serializers.SerializerMethodField()
    curso = serializers.CharField(source='curso_campus.descricao_historico')
    campus = serializers.CharField(source='curso_campus.diretoria.setor.uo')
    foto = serializers.ImageField()

    def get_nome(self, obj):
        return obj.get_nome()

    class Meta:
        model = Aluno
        fields = ('matricula', 'nome', 'curso', 'campus', 'foto')


class CursoCampusSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField()
    descricao = serializers.CharField(source='descricao_historico')
    diretoria = serializers.CharField(source='diretoria.setor.sigla')
    natureza_participacao = serializers.SerializerMethodField()
    eixo = serializers.SerializerMethodField()
    modalidade = serializers.SerializerMethodField()
    coordenador = serializers.SerializerMethodField()
    carga_horaria = serializers.SerializerMethodField()
    componentes_curriculares = serializers.SerializerMethodField()

    def get_natureza_participacao(self, obj):
        serializers.CharField(source='natureza_participacao.descricao')
        if obj.natureza_participacao:
            return obj.natureza_participacao.descricao
        else:
            return None

    def get_coordenador(self, obj):
        if obj.coordenador:
            return obj.coordenador.nome
        else:
            return None

    def get_eixo(self, obj):
        if obj.eixo:
            return obj.eixo.descricao
        else:
            return None

    def get_modalidade(self, obj):
        if obj.modalidade:
            return obj.modalidade.descricao
        else:
            return None

    def get_carga_horaria(self, obj):
        ch_total = 0
        for matriz in obj.matrizes.all():
            ch_total += matriz.get_carga_horaria_total_prevista()
        return ch_total

    def get_componentes_curriculares(self, obj):
        componentes = []

        for matriz in obj.matrizes.all():
            for componente_curricular in matriz.componentecurricular_set.all():
                componentes.append(
                    {'codigo': componente_curricular.componente_id, 'sigla': componente_curricular.componente.sigla, 'nome': componente_curricular.componente.descricao_historico}
                )

        return componentes

    class Meta:
        model = CursoCampus
        fields = ('codigo', 'descricao', 'diretoria', 'carga_horaria', 'natureza_participacao', 'eixo', 'modalidade', 'coordenador', 'componentes_curriculares')


class AtualizacaoSerializer(serializers.ModelSerializer):
    tipo = serializers.SerializerMethodField()
    tags = serializers.StringRelatedField(many=True)
    grupos = serializers.StringRelatedField(many=True)
    demanda = serializers.StringRelatedField()

    def get_tipo(self, obj):
        return obj.get_tipo_display()

    class Meta:
        model = Atualizacao
        fields = ('id', 'tipo', 'descricao', 'tags', 'grupos', 'data', 'demanda')


class BaseConhecimentoSerializer(serializers.ModelSerializer):
    class Meta:
        if 'centralservicos' in settings.INSTALLED_APPS:
            from centralservicos.models import BaseConhecimento

            model = BaseConhecimento
            fields = ('pk', 'resumo', 'solucao')


class UnidadeOrganizacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadeOrganizacional
        fields = ('nome', 'sigla', 'endereco', 'cep', 'telefone', 'fax')


class SetorSerializer(serializers.ModelSerializer):
    hierarquia = serializers.SerializerMethodField()
    telefones = serializers.SerializerMethodField()
    chefes = serializers.SerializerMethodField()
    campus = serializers.SerializerMethodField()
    total_servidores = serializers.SerializerMethodField()

    def get_hierarquia(self, obj):
        caminho = obj.get_caminho()
        caminho_str = []
        for s in caminho:
            if hasattr(s, 'unidadeorganizacional'):
                s_repr = str(s)
            elif s == caminho[-1]:
                s_repr = str(s)
            else:
                s_repr = str(s)
            caminho_str.append(s_repr)
        return caminho_str

    def get_campus(self, obj):
        if obj.uo:
            return obj.uo.sigla
        else:
            return None

    def get_total_servidores(self, obj):
        return obj.get_servidores().count()

    def get_telefones(self, obj):
        telefones = []
        for telefone in obj.setortelefone_set.all():
            telefones.append(str(telefone))
        return telefones

    def get_chefes(self, obj):
        chefes = []
        for chefe in obj.chefes:
            chefes.append(chefe.nome)
        return chefes

    class Meta:
        model = Setor
        fields = ('nome', 'sigla', 'hierarquia', 'campus', 'telefones', 'chefes', 'total_servidores')


class ServidorSerializer(serializers.ModelSerializer):
    setor_suap = serializers.SerializerMethodField()
    setor_siape = serializers.SerializerMethodField()
    jornada_trabalho = serializers.CharField(source='jornada_trabalho.nome')
    campus = serializers.SerializerMethodField()
    cargo = serializers.SerializerMethodField()
    funcao = serializers.SerializerMethodField()
    disciplina_ingresso = serializers.SerializerMethodField()
    telefones_institucionais = serializers.SerializerMethodField()
    url_foto_75x100 = serializers.SerializerMethodField()
    curriculo_lattes = serializers.URLField(source='pessoa_fisica.lattes')

    def get_campus(self, obj):

        if obj.setor and obj.setor.uo:
            return obj.setor.uo.sigla
        else:
            if obj.setor_exercicio and obj.setor_exercicio.uo:
                return obj.setor_exercicio.uo.sigla
            return None

    def get_setor_suap(self, obj):
        if obj.setor:
            return obj.setor.sigla
        else:
            return None

    def get_setor_siape(self, obj):
        if obj.setor_exercicio:
            return obj.setor_exercicio.sigla
        else:
            return None

    def get_cargo(self, obj):
        if obj.cargo_emprego:
            return obj.cargo_emprego.nome
        else:
            return None

    def get_url_foto_75x100(self, obj):
        return obj.get_foto_75x100_url()

    def get_funcao(self, obj):
        hoje = datetime.datetime.now()
        historico_list = []
        for historico in obj.historico_funcao(hoje, hoje):
            historico_list.append(historico.funcao_display)
        return historico_list

    def get_disciplina_ingresso(self, obj):
        if obj.eh_docente and obj.professor_set.all().exists():
            return str(obj.professor_set.all()[0].disciplina)
        return '-'

    def get_telefones_institucionais(self, obj):
        return obj.telefones_institucionais.split(', ')

    class Meta:
        model = Servidor
        fields = (
            'matricula',
            'nome',
            'cargo',
            'setor_suap',
            'setor_siape',
            'jornada_trabalho',
            'funcao',
            'campus',
            'telefones_institucionais',
            'categoria',
            'disciplina_ingresso',
            'url_foto_75x100',
            'curriculo_lattes',
        )


class ProjetoPesquisaSerializer(serializers.ModelSerializer):
    campus = serializers.CharField(source='uo.sigla')
    grupo = serializers.SerializerMethodField()
    codigo_area_conhecimento = serializers.CharField(source='area_conhecimento.superior.codigo')
    area_conhecimento = serializers.CharField(source='area_conhecimento.superior.descricao')
    codigo_sub_area_conhecimento = serializers.CharField(source='area_conhecimento.codigo')
    sub_area_conhecimento = serializers.CharField(source='area_conhecimento.descricao')
    equipe = serializers.SerializerMethodField()
    resumo = serializers.SerializerMethodField()
    justificativa = serializers.SerializerMethodField()
    coordenador = serializers.SerializerMethodField()
    situacao = serializers.SerializerMethodField()

    def get_grupo(self, obj):
        if obj.grupo_pesquisa:
            return obj.grupo_pesquisa.descricao
        else:
            return None

    def get_equipe(self, obj):
        nomes_participantes = []
        participantes = obj.get_participacoes_alunos() + obj.get_participacoes_servidores()
        for participante in participantes:
            string = participante.pessoa.nome
            nomes_participantes.append(string)

        return ', '.join(nomes_participantes)

    def get_resumo(self, obj):
        return strip_tags(html.unescape(obj.resumo)).replace("\r\n", "")

    def get_coordenador(self, obj):

        if obj.participacao_set.filter(responsavel=True).exists():
            return obj.participacao_set.filter(responsavel=True)[0].pessoa.nome
        return ''

    def get_situacao(self, obj):
        return obj.get_status()

    def get_justificativa(self, obj):
        return strip_tags(html.unescape(obj.justificativa)).replace("\r\n", "")

    class Meta:
        model = ProjetoPesquisa
        fields = (
            'id',
            'titulo',
            'situacao',
            'coordenador',
            'campus',
            'grupo',
            'inicio_execucao',
            'fim_execucao',
            'codigo_area_conhecimento',
            'area_conhecimento',
            'codigo_sub_area_conhecimento',
            'sub_area_conhecimento',
            'resumo',
            'justificativa',
            'equipe',
        )


class ProjetoExtensaoSerializer(serializers.ModelSerializer):
    campus = serializers.CharField(source='uo.sigla')
    foco_tecnologico = serializers.CharField(source='focotecnologico.descricao')
    area_conhecimento = serializers.SerializerMethodField()
    equipe = serializers.SerializerMethodField()
    coordenador = serializers.CharField(source='vinculo_coordenador.pessoa.nome')

    def get_area_conhecimento(self, obj):
        if obj.area_conhecimento:
            return obj.area_conhecimento.descricao
        else:
            return None

    def get_equipe(self, obj):
        nomes_participantes = []
        participantes = obj.get_participacoes_alunos() + obj.get_participacoes_servidores()
        for participante in participantes:
            nomes_participantes.append(participante.pessoa.nome)

        return ', '.join(nomes_participantes)

    class Meta:
        model = ProjetoExtensao
        fields = ('id', 'titulo', 'coordenador', 'campus', 'inicio_execucao', 'fim_execucao', 'foco_tecnologico', 'area_conhecimento', 'resumo', 'justificativa', 'equipe')


class ProgramaSerializer(serializers.ModelSerializer):
    campus = serializers.CharField(source='instituicao.sigla')

    class Meta:
        model = Programa
        fields = ('id', 'titulo', 'descricao', 'campus')


class ParticipacaoSerializer(serializers.ModelSerializer):
    aluno = serializers.CharField(source='aluno.pessoa_fisica.nome')
    programa = serializers.CharField(source='programa.tipo')
    sigla = serializers.CharField(source='programa.instituicao.sigla')
    data_inicio = serializers.CharField()
    data_termino = serializers.CharField()

    class Meta:
        model = Participacao
        fields = ('id', 'aluno', 'programa', 'sigla', 'data_inicio', 'data_termino')


class InventarioSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(source='numero')
    descricao = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    estado_conservacao = serializers.SerializerMethodField()
    valor_inicial = serializers.SerializerMethodField()
    valor_liquido_contabil = serializers.SerializerMethodField()
    campus = serializers.CharField(source='carga_contabil.campus.sigla')

    def get_descricao(self, obj):
        return obj.get_descricao()

    def get_status(self, obj):
        return obj.get_status()

    def get_estado_conservacao(self, obj):
        return obj.get_estado_conservacao_display()

    def get_valor_inicial(self, obj):
        return obj.entrada_permanente.get_valor()

    def get_valor_liquido_contabil(self, obj):
        return obj.get_valor()

    class Meta:
        model = Inventario
        fields = ('id', 'codigo', 'descricao', 'status', 'estado_conservacao', 'valor_inicial', 'valor_liquido_contabil', 'campus')


class ProcessoSerializer(serializers.ModelSerializer):
    interessado = serializers.CharField(source='interessado_nome')
    campus = serializers.CharField(source='uo.sigla')
    situacao = serializers.SerializerMethodField()
    tramites = serializers.SerializerMethodField()

    def get_situacao(self, obj):
        return obj.get_status_display()

    def get_tramites(self, obj):
        setores_tramites = []
        for tramite in obj.tramite_set.all():
            setores_tramites.append(str(tramite.orgao_encaminhamento))

        return setores_tramites

    class Meta:
        model = Processo
        fields = ('id', 'numero_processo', 'interessado', 'assunto', 'data_cadastro', 'campus', 'situacao', 'tramites')


class TramiteProcessoSerializer(serializers.ModelSerializer):
    vinculo_encaminhamento = serializers.CharField(source='vinculo_encaminhamento.pessoa.nome')
    vinculo_recebimento = serializers.CharField(source='vinculo_recebimento.pessoa.nome')
    orgao_encaminhamento = serializers.SerializerMethodField()
    orgao_recebimento = serializers.SerializerMethodField()
    situacao = serializers.SerializerMethodField()

    def get_orgao_encaminhamento(self, obj):
        return str(obj.orgao_encaminhamento)

    def get_orgao_recebimento(self, obj):
        return str(obj.orgao_recebimento)

    def get_situacao(self, obj):
        if obj.recebido:
            return 'Recebido'
        else:
            return 'Aguardando recebimento'

    class Meta:
        model = Tramite
        fields = (
            'ordem',
            'orgao_encaminhamento',
            'data_encaminhamento',
            'vinculo_encaminhamento',
            'observacao_encaminhamento',
            'orgao_recebimento',
            'data_recebimento',
            'vinculo_recebimento',
            'observacao_recebimento',
            'situacao',
        )


class DetalheProcessoSerializer(serializers.ModelSerializer):
    interessado = serializers.CharField(source='interessado_nome')
    campus = serializers.CharField(source='uo.sigla')
    operador = serializers.CharField(source='vinculo_cadastro.pessoa.nome')
    tipo_processo = serializers.SerializerMethodField()
    situacao = serializers.SerializerMethodField()
    orgao_responsavel = serializers.SerializerMethodField()
    tramites = serializers.SerializerMethodField()

    def get_situacao(self, obj):
        return obj.get_status_display()

    def get_tramites(self, obj):
        tramites = TramiteProcessoSerializer(obj.tramite_set.all(), many=True).data

        if obj.status in [Processo.STATUS_FINALIZADO, Processo.STATUS_ARQUIVADO]:
            tramites.append(
                OrderedDict(
                    [
                        ('ordem', obj.tramite_set.count() + 1),
                        ('setor', str(obj.tramite_set.order_by('-ordem')[0].orgao_interno_recebimento)),
                        ('data_finalizacao', obj.data_finalizacao),
                        ('pessoa_finalizacao', obj.vinculo_finalizacao.pessoa.nome),
                        ('observacao_finalizacao', obj.observacao_finalizacao),
                        ('situacao', obj.get_status_display()),
                    ]
                )
            )
        return tramites

    def get_tipo_processo(self, obj):
        return obj.get_tipo_display()

    def get_orgao_responsavel(self, obj):
        return str(obj.get_orgao_responsavel_atual())

    class Meta:
        model = Processo
        fields = (
            'id',
            'numero_processo',
            'interessado',
            'assunto',
            'data_cadastro',
            'campus',
            'situacao',
            'tipo_processo',
            'operador',
            'orgao_responsavel',
            'numero_documento',
            'palavras_chave',
            'tramites',
        )


class ContratoSerializer(serializers.ModelSerializer):
    campus = serializers.SerializerMethodField()
    valor_total = serializers.SerializerMethodField()
    valor_executado = serializers.SerializerMethodField()

    def get_campus(self, obj):
        return obj.get_uos_as_string()

    def get_valor_total(self, obj):
        return obj.get_valor_total()

    def get_valor_executado(self, obj):
        return obj.get_valor_executado()

    class Meta:
        model = Contrato
        fields = ('id', 'numero', 'campus', 'objeto', 'data_inicio', 'data_fim', 'valor_total', 'valor_executado')


# Serializers utilizados pelo SUAP Mobile


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    matricula = serializers.CharField(source="username")
    nome_usual = serializers.SerializerMethodField()
    cpf = serializers.SerializerMethodField()
    rg = serializers.SerializerMethodField()
    filiacao = serializers.SerializerMethodField()
    data_nascimento = serializers.SerializerMethodField()
    naturalidade = serializers.SerializerMethodField()
    tipo_sanguineo = serializers.SerializerMethodField()
    email = serializers.CharField()
    url_foto_75x100 = serializers.SerializerMethodField()
    url_foto_150x200 = serializers.SerializerMethodField()
    tipo_vinculo = serializers.SerializerMethodField()
    vinculo = serializers.SerializerMethodField()

    def get_id(self, obj):
        return obj.get_profile().id

    def get_nome_usual(self, obj):
        return obj.get_profile().nome_usual

    def get_cpf(self, obj):
        return obj.get_profile().cpf

    def get_rg(self, obj):
        return obj.get_profile().rg_display

    def get_data_nascimento(self, obj):
        return obj.get_profile().nascimento_data

    def get_tipo_sanguineo(self, obj):
        return obj.get_profile().tipo_sanguineo

    def get_naturalidade(self, obj):
        if obj.get_profile().nascimento_municipio:
            return '{}/{}'.format(obj.get_profile().nascimento_municipio.nome, obj.get_profile().nascimento_municipio.uf)
        return '-'

    def get_filiacao(self, obj):
        return [obj.get_profile().nome_mae, obj.get_profile().nome_pai]

    def get_url_foto_75x100(self, obj):
        return obj.get_profile().get_foto_75x100_url()

    def get_url_foto_150x200(self, obj):
        return obj.get_profile().get_foto_150x200_url()

    def get_tipo_vinculo(self, obj):
        return obj.get_vinculo().get_vinculo_institucional_title

    def get_vinculo(self, obj):
        sub_instance = obj.get_relacionamento()

        if type(sub_instance) == Aluno:
            return AlunoSerializer(sub_instance).data
        elif type(sub_instance) == Servidor:
            return ServidorSerializer(sub_instance).data
        else:
            return None

    class Meta:
        model = User
        fields = (
            'id',
            'matricula',
            'nome_usual',
            'cpf',
            'rg',
            'filiacao',
            'data_nascimento',
            'naturalidade',
            'tipo_sanguineo',
            'email',
            'url_foto_75x100',
            'url_foto_150x200',
            'tipo_vinculo',
            'vinculo',
        )


class MatriculaPeriodoSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='diario.id')
    sigla = serializers.CharField(source='diario.componente_curricular.componente.sigla')
    descricao = serializers.CharField(source='diario.componente_curricular.componente.descricao_historico')
    observacao = serializers.SerializerMethodField()
    locais_de_aula = serializers.SerializerMethodField()
    horarios_de_aula = serializers.SerializerMethodField()

    def get_locais_de_aula(self, obj):
        locais = []
        if obj.diario.local_aula:
            locais.append(str(obj.diario.local_aula))
        return locais

    def get_horarios_de_aula(self, obj):
        return obj.diario.get_horario_aulas()

    def get_observacao(self, obj):
        if obj.diario.is_semestral_segundo_semestre():
            return 'Esta disciplina será ofertada apenas no segundo semestre.'
        elif obj.is_cancelado():
            return obj.get_situacao_diario_boletim().get('rotulo')

    class Meta:
        model = MatriculaPeriodo
        fields = ('id', 'sigla', 'descricao', 'observacao', 'locais_de_aula', 'horarios_de_aula')


class MatriculaDiarioSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='diario.id')
    ano_letivo = serializers.CharField(source='diario.ano_letivo.ano')
    periodo_letivo = serializers.CharField(source='diario.periodo_letivo')
    componente_curricular = serializers.CharField(source='diario.componente_curricular.componente')
    professores = serializers.SerializerMethodField()
    locais_de_aula = serializers.SerializerMethodField()
    data_inicio = serializers.CharField(source='diario.calendario_academico.data_inicio')
    data_fim = serializers.CharField(source='diario.calendario_academico.data_fim')
    participantes = serializers.SerializerMethodField()
    aulas = serializers.SerializerMethodField()
    materiais_de_aula = serializers.SerializerMethodField()

    def get_professores(self, obj):
        professores = []
        for professordiario in obj.diario.professordiario_set.all():
            professor = {
                'foto': professordiario.professor.get_foto_75x100_url(),
                'nome': professordiario.professor.get_nome(),
                'matricula': professordiario.professor.get_matricula(),
                'email': professordiario.professor.vinculo.pessoa.email,
            }
            professores.append(professor)
        return professores

    def get_locais_de_aula(self, obj):
        locais = []
        if obj.diario.local_aula:
            locais.append(str(obj.diario.local_aula))
        return locais

    def get_participantes(self, obj):
        participantes = []
        for matricula_diario in obj.diario.get_matriculas_diario():
            participante = {
                'foto': matricula_diario.matricula_periodo.aluno.get_foto_75x100_url(),
                'nome': matricula_diario.matricula_periodo.aluno.get_nome(),
                'matricula': matricula_diario.matricula_periodo.aluno.matricula,
                'email': matricula_diario.matricula_periodo.aluno.email_academico,
            }
            participantes.append(participante)
        return participantes

    def get_aulas(self, obj):
        aulas = []
        obj.set_faltas(obj.diario.get_aulas())

        for falta in obj.faltas:
            aula = {
                'data': falta.aula.data,
                'etapa': falta.aula.etapa,
                'quantidade': falta.aula.quantidade,
                'faltas': falta.quantidade,
                'professor': falta.aula.professor_diario.professor.vinculo.pessoa.nome,
                'conteudo': falta.aula.conteudo,
            }
            aulas.append(aula)
        return aulas

    def get_materiais_de_aula(self, obj):
        materiais = []
        for material_diario in MaterialDiario.objects.filter(professor_diario__diario=obj.diario).order_by('-data_vinculacao'):
            material = {
                'url': material_diario.material_aula.get_absolute_url(),
                'descricao': material_diario.material_aula.descricao,
                'data_vinculacao': material_diario.data_vinculacao,
            }
            materiais.append(material)
        return materiais

    class Meta:
        model = MatriculaDiario
        fields = (
            'id',
            'ano_letivo',
            'periodo_letivo',
            'componente_curricular',
            'professores',
            'locais_de_aula',
            'data_inicio',
            'data_fim',
            'participantes',
            'aulas',
            'materiais_de_aula',
        )


class ItemConfiguracaoAvaliacaoSerializer(serializers.ModelSerializer):
    diario = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()
    etapa = serializers.CharField(source="configuracao_avaliacao.etapa")

    def get_diario(self, obj):
        return str(obj.configuracao_avaliacao.diario)

    def get_tipo(self, obj):
        return obj.get_tipo_display()

    class Meta:
        model = ItemConfiguracaoAvaliacao
        fields = ('id', 'diario', 'tipo', 'sigla', 'descricao', 'nota_maxima', 'peso', 'data', 'etapa')


class BoletimSerializer(serializers.ModelSerializer):
    codigo_diario = serializers.CharField(source="diario.id")
    disciplina = serializers.SerializerMethodField()
    segundo_semestre = serializers.SerializerMethodField()
    carga_horaria = serializers.SerializerMethodField()
    carga_horaria_cumprida = serializers.SerializerMethodField()
    numero_faltas = serializers.SerializerMethodField()
    percentual_carga_horaria_frequentada = serializers.SerializerMethodField()
    situacao = serializers.SerializerMethodField()
    quantidade_avaliacoes = serializers.IntegerField(source="diario.componente_curricular.qtd_avaliacoes")
    nota_etapa_1 = serializers.SerializerMethodField()
    nota_etapa_2 = serializers.SerializerMethodField()
    nota_etapa_3 = serializers.SerializerMethodField()
    nota_etapa_4 = serializers.SerializerMethodField()
    media_disciplina = serializers.SerializerMethodField()
    nota_avaliacao_final = serializers.SerializerMethodField()
    media_final_disciplina = serializers.SerializerMethodField()

    def get_disciplina(self, obj):
        return '{} - {}'.format(obj.diario.componente_curricular.componente.sigla, obj.diario.componente_curricular.componente.descricao_historico)

    def get_segundo_semestre(self, obj):
        return obj.diario.is_semestral_segundo_semestre()

    def get_carga_horaria(self, obj):
        return obj.diario.get_carga_horaria()

    def get_carga_horaria_cumprida(self, obj):
        return obj.diario.get_carga_horaria_cumprida()

    def get_numero_faltas(self, obj):
        return obj.get_numero_faltas()

    def get_percentual_carga_horaria_frequentada(self, obj):
        return obj.get_percentual_carga_horaria_frequentada()

    def get_situacao(self, obj):
        return obj.get_situacao_diario_boletim().get("rotulo")

    def get_nota_etapa_1(self, obj):
        dict = {"nota": obj.get_nota_1_boletim(), "faltas": obj.get_numero_faltas_primeira_etapa()}
        return dict

    def get_nota_etapa_2(self, obj):
        dict = {"nota": obj.get_nota_2_boletim(), "faltas": obj.get_numero_faltas_segunda_etapa()}
        return dict

    def get_nota_etapa_3(self, obj):
        dict = {"nota": obj.get_nota_3_boletim(), "faltas": obj.get_numero_faltas_terceira_etapa()}
        return dict

    def get_nota_etapa_4(self, obj):
        dict = {"nota": obj.get_nota_4_boletim(), "faltas": obj.get_numero_faltas_quarta_etapa()}
        return dict

    def get_media_disciplina(self, obj):
        return obj.get_media_disciplina_boletim()

    def get_nota_avaliacao_final(self, obj):
        dict = {"nota": obj.get_nota_final_boletim(), "faltas": 0}
        return dict

    def get_media_final_disciplina(self, obj):
        if obj.get_media_final_disciplina_boletim():
            return str(obj.get_media_final_disciplina_boletim())
        else:
            return None

    class Meta:
        model = MatriculaDiario
        fields = (
            'codigo_diario',
            'disciplina',
            'segundo_semestre',
            'carga_horaria',
            'carga_horaria_cumprida',
            'numero_faltas',
            'percentual_carga_horaria_frequentada',
            'situacao',
            'quantidade_avaliacoes',
            'nota_etapa_1',
            'nota_etapa_2',
            'nota_etapa_3',
            'nota_etapa_4',
            'media_disciplina',
            'nota_avaliacao_final',
            'media_final_disciplina',
        )


class ContraChequeAnoMesSerializer(serializers.ModelSerializer):
    ano = serializers.IntegerField(source='ano.ano')
    nome_mes = serializers.SerializerMethodField()

    def get_nome_mes(self, obj):
        return obj.get_mes_display()

    class Meta:
        model = ContraCheque
        fields = ('ano', 'mes', 'nome_mes', 'bruto', 'liquido', 'desconto')


class ContraChequeSerializer(serializers.ModelSerializer):
    rendimentos = serializers.SerializerMethodField()
    descontos = serializers.SerializerMethodField()
    ano = serializers.IntegerField(source='ano.ano')
    nome_mes = serializers.SerializerMethodField()

    def get_nome_mes(self, obj):
        return obj.get_mes_display()

    def get_rendimentos(self, obj):
        rendimentos = ContraChequeRubricaModel.objects.filter(contra_cheque=obj, tipo__nome='Rendimento')
        return ContraChequeRubrica(rendimentos, many=True).data

    def get_descontos(self, obj):
        descontos = ContraChequeRubricaModel.objects.filter(contra_cheque=obj, tipo__nome='Desconto')
        return ContraChequeRubrica(descontos, many=True).data

    class Meta:
        model = ContraCheque
        fields = ('ano', 'mes', 'nome_mes', 'rendimentos', 'descontos', 'bruto', 'liquido', 'desconto')


class FrequenciasHojeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Frequencia
        fields = ('acao', 'horario')


class AcessoResponsaveisSerializer(serializers.Serializer):
    matricula = serializers.CharField()
    chave = serializers.CharField()


class InterrupcaoFeriasSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterrupcaoFerias
        fields = ('data_interrupcao_periodo', 'data_inicio_continuacao_periodo', 'data_fim_continuacao_periodo')


class FeriasSerializer(serializers.ModelSerializer):
    ano = serializers.IntegerField(source='ano.ano')
    status = serializers.SerializerMethodField()
    interrupcoes = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.get_status()

    def get_interrupcoes(self, obj):
        return InterrupcaoFeriasSerializer(obj.interrupcaoferias_set.all(), many=True).data

    class Meta:
        model = Ferias
        fields = (
            'ano',
            'data_inicio_periodo1',
            'data_fim_periodo1',
            'data_inicio_periodo2',
            'data_fim_periodo2',
            'data_inicio_periodo3',
            'data_fim_periodo3',
            'interrupcoes',
            'status',
        )


class ServidorOcorrenciaSerializer(serializers.ModelSerializer):
    tipo_ocorrencia = serializers.SerializerMethodField()
    descricao = serializers.CharField(source='ocorrencia.nome')
    total_dias = serializers.SerializerMethodField()

    def get_tipo_ocorrencia(self, obj):
        if obj.subgrupo:
            return obj.subgrupo.descricao
        else:
            return obj.ocorrencia.grupo_ocorrencia.nome

    def get_total_dias(self, obj):
        if obj.data_termino:
            return (obj.data - obj.data_termino).days + 1
        else:
            return None

    class Meta:
        model = ServidorOcorrencia
        fields = ('tipo_ocorrencia', 'descricao', 'data', 'data_termino', 'total_dias')


class ServidorAfastamentoSerializer(serializers.ModelSerializer):
    tipo_afastamento = serializers.SerializerMethodField()
    descricao = serializers.CharField(source='afastamento.nome')
    total_dias = serializers.SerializerMethodField()

    def get_tipo_afastamento(self, obj):
        return obj.afastamento.get_tipo_display()

    def get_total_dias(self, obj):
        if obj.data_termino:
            return (obj.data_termino - obj.data_inicio).days + 1
        else:
            return None

    class Meta:
        model = ServidorAfastamento
        fields = ('tipo_afastamento', 'descricao', 'data_inicio', 'data_termino', 'total_dias')


class ParticipacaoProjetoExtensaoSerializer(serializers.ModelSerializer):
    edital = serializers.CharField(source='projeto.edital.titulo')
    projeto = serializers.CharField(source='projeto.titulo')

    class Meta:
        model = PartExtensao
        fields = ('edital', 'projeto')


class ParticipacaoProjetoPesquisaSerializer(serializers.ModelSerializer):
    edital = serializers.CharField(source='projeto.edital.titulo')
    projeto = serializers.CharField(source='projeto.titulo')

    class Meta:
        model = PartPesquisa
        fields = ('edital', 'projeto')


class DiarioSerializer(serializers.ModelSerializer):
    componente_curricular = serializers.CharField(source='componente_curricular.componente')
    professores = serializers.SerializerMethodField()
    locais_de_aula = serializers.SerializerMethodField()
    data_inicio = serializers.CharField(source='calendario_academico.data_inicio')
    data_fim = serializers.CharField(source='calendario_academico.data_fim')
    participantes = serializers.SerializerMethodField()
    aulas = serializers.SerializerMethodField()
    materiais_de_aula = serializers.SerializerMethodField()

    def get_professores(self, obj):
        professores = []
        for professordiario in obj.professordiario_set.all():
            professor = {
                'foto': professordiario.professor.get_foto_75x100_url(),
                'nome': professordiario.professor.get_nome(),
                'matricula': professordiario.professor.get_matricula(),
                'email': professordiario.professor.vinculo.pessoa.email,
            }
            professores.append(professor)
        return professores

    def get_locais_de_aula(self, obj):
        locais = []
        if obj.local_aula:
            locais.append(str(obj.local_aula))
        return locais

    def get_participantes(self, obj):
        participantes = []
        for matricula_diario in obj.get_matriculas_diario():
            participante = {
                'foto': matricula_diario.matricula_periodo.aluno.get_foto_75x100_url(),
                'nome': matricula_diario.matricula_periodo.aluno.get_nome(),
                'matricula': matricula_diario.matricula_periodo.aluno.matricula,
                'email': matricula_diario.matricula_periodo.aluno.email_academico,
            }
            participantes.append(participante)
        return participantes

    def get_aulas(self, obj):
        aulas = []

        for aula in obj.get_aulas():
            aula = {
                'data': aula.data,
                'etapa': aula.etapa,
                'quantidade': aula.quantidade,
                'professor': aula.professor_diario.professor.vinculo.pessoa.nome,
                'conteudo': aula.conteudo,
            }
            aulas.append(aula)
        return aulas

    def get_materiais_de_aula(self, obj):
        materiais = []
        for material_diario in MaterialDiario.objects.filter(professor_diario__diario=obj).order_by('-data_vinculacao'):
            material = {
                'url': material_diario.material_aula.get_absolute_url(),
                'descricao': material_diario.material_aula.descricao,
                'data_vinculacao': material_diario.data_vinculacao,
            }
            materiais.append(material)
        return materiais

    class Meta:
        model = Diario
        fields = (
            'id',
            'ano_letivo',
            'periodo_letivo',
            'componente_curricular',
            'professores',
            'locais_de_aula',
            'data_inicio',
            'data_fim',
            'participantes',
            'aulas',
            'materiais_de_aula',
        )


class ProfessorDiarioSerializer(serializers.ModelSerializer):
    diario = serializers.CharField(source='diario.pk')
    disciplina_componente = serializers.CharField(source='diario.componente_curricular.componente.descricao')
    diario_dividido = serializers.SerializerMethodField()
    local = serializers.CharField(source='diario.local_aula')
    modalidade = serializers.CharField(source='diario.turma.curso_campus.modalidade')
    horarios_aula = serializers.SerializerMethodField()
    numero_alunos = serializers.SerializerMethodField()
    ch_semanal = serializers.SerializerMethodField()

    def get_ch_semanal(self, obj):
        return obj.get_qtd_creditos_efetiva()

    def get_numero_alunos(self, obj):
        return obj.diario.get_alunos_ativos().count()

    def get_horarios_aula(self, obj):
        return obj.diario.get_horario_aulas()

    def get_diario_dividido(self, obj):
        return obj.diario.get_professores().count() > 1

    class Meta:
        model = ProfessorDiario
        fields = ('diario', 'disciplina_componente', 'diario_dividido', 'local', 'modalidade', 'horarios_aula', 'numero_alunos', 'ch_semanal')


class ProfessorMinicursoSerializer(serializers.ModelSerializer):
    turma = serializers.CharField(source='turma_minicurso.minicurso.descricao')
    modalidade = serializers.CharField(source='turma_minicurso.minicurso.modalidade')
    numero_alunos = serializers.SerializerMethodField()
    ch_semanal = serializers.SerializerMethodField()

    def get_numero_alunos(self, obj):
        return obj.turma_minicurso.participantes.count()

    def get_ch_semanal(self, obj):
        return obj.get_carga_horaria_semanal_ha()

    class Meta:
        model = ProfessorMinicurso
        fields = ('turma', 'modalidade', 'numero_alunos', 'ch_semanal')


class DiarioEspecialSerializer(serializers.ModelSerializer):
    descricao = serializers.SerializerMethodField()
    horario_aulas = serializers.SerializerMethodField()
    numero_alunos = serializers.SerializerMethodField()
    ch_semanal = serializers.SerializerMethodField()

    def get_descricao(self, obj):
        return 'Atividade Específica de Ensino'

    def get_numero_alunos(self, obj):
        return obj.participantes.count()

    def get_horario_aulas(self, obj):
        return obj.get_horario_aulas()

    def get_ch_semanal(self, obj):
        return obj.componente.ch_qtd_creditos

    class Meta:
        model = DiarioEspecial
        fields = ('descricao', 'sala', 'horario_aulas', 'numero_alunos', 'ch_semanal')


class AtividadeDocenteSerializer(serializers.ModelSerializer):
    horario_aulas = serializers.SerializerMethodField()
    ch_semanal = serializers.SerializerMethodField()

    def get_ch_semanal(self, obj):
        return obj.ch_aula_efetiva

    def get_horario_aulas(self, obj):
        return obj.get_horario_aulas()

    class Meta:
        if 'pit_rit' in settings.INSTALLED_APPS:
            from pit_rit.models import AtividadeDocente

            model = AtividadeDocente
            fields = ('descricao', 'tipo_atividade', 'sala', 'horario_aulas', 'ch_semanal', 'deferida')


class PlanoIndividualTrabalhoSerializer(serializers.ModelSerializer):
    publicado = serializers.BooleanField(source='deferida')
    ano_letivo = serializers.CharField(source='ano_letivo.ano')
    periodo_letivo = serializers.CharField()
    professor = serializers.SerializerMethodField()
    campus = serializers.SerializerMethodField()
    ch_semanal_total = serializers.SerializerMethodField()
    atividades_ensino = serializers.SerializerMethodField()
    atividades_pesquisa = serializers.SerializerMethodField()
    atividades_extensao = serializers.SerializerMethodField()
    atividades_gestao = serializers.SerializerMethodField()

    class Meta:
        if 'pit_rit' in settings.INSTALLED_APPS:
            from pit_rit.models import PlanoIndividualTrabalho

            model = PlanoIndividualTrabalho
            fields = (
                'ano_letivo',
                'periodo_letivo',
                'professor',
                'campus',
                'ch_semanal_total',
                'publicado',
                'atividades_ensino',
                'atividades_pesquisa',
                'atividades_extensao',
                'atividades_gestao',
            )

    def get_campus(self, obj):
        if obj.professor.vinculo.setor:
            return obj.professor.vinculo.setor.uo.sigla
        elif obj.professor.vinculo.relacionamento.setor_lotacao:
            return obj.professor.vinculo.relacionamento.setor_lotacao.uo.sigla
        else:
            return None

    def get_professor(self, obj):
        return str(obj.professor)

    def get_atividades_ensino(self, obj):
        return {
            'cursos_regulares': ProfessorDiarioSerializer(obj.get_vinculo_diarios(False), many=True).data,
            'cursos_ch_maior_160': ProfessorDiarioSerializer(obj.get_vinculo_diarios(), many=True).data,
            'cursos_ch_menor_160': ProfessorMinicursoSerializer(obj.get_vinculos_minicurso(), many=True).data,
            'ch_semanal_manutencao_ensino': (obj.get_ch_diarios() + obj.get_ch_diarios(True) + obj.get_ch_minicursos_ha()),
            'diarios_especiais': DiarioEspecialSerializer(obj.get_vinculos_diarios_especiais(), many=True).data,
            'atividades_apoio': AtividadeDocenteSerializer(obj.get_atividades_ensino(), many=True).data,
        }

    def get_atividades_pesquisa(self, obj):
        return AtividadeDocenteSerializer(obj.get_atividades_pesquisa(), many=True).data

    def get_atividades_extensao(self, obj):
        return AtividadeDocenteSerializer(obj.get_atividades_extensao(), many=True).data

    def get_atividades_gestao(self, obj):
        return AtividadeDocenteSerializer(obj.get_atividades_gestao(), many=True).data

    def get_ch_semanal_total(self, obj):
        return obj.get_ch_semanal_total()


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'titulo', 'imagem', 'tipo', 'link', 'data_inicio', 'data_termino')


# Nova API ###################################################################


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email']


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['url', 'id', 'name', 'client_type', 'authorization_grant_type', 'redirect_uris', 'client_id', 'client_secret', 'user']
        read_only_fields = ['id', 'client_id', 'client_secret', 'user']

    user = UserSerializer(read_only=True)

    def create(self, validated_data):
        application = Application(
            user=self.context['request'].user,
            name=validated_data['name'],
            client_type=validated_data['client_type'],
            authorization_grant_type=validated_data['authorization_grant_type'],
            redirect_uris=validated_data['redirect_uris'],
        )
        application.save()
        return application


class ServidorSerializer2(serializers.Serializer):
    matricula = serializers.CharField()
    nome = serializers.CharField()
    data_de_nascimento = serializers.DateField()
    cpf = serializers.CharField()
    cargo = serializers.CharField()
    categoria_do_cargo = serializers.CharField()
    setor = serializers.CharField()
    campus = serializers.CharField()
    ativo = serializers.BooleanField()
    situacao = serializers.CharField()
    endereco = serializers.CharField()
    email = serializers.EmailField()
    telefone = serializers.CharField()
    foto = serializers.URLField()
    dados_bancarios = serializers.SerializerMethodField()

    def get_dados_bancarios(self, obj):
        return dict(
            codigo_do_banco=obj['banco_codigo'],
            nome_do_banco=obj['banco_nome'],
            agencia=obj['banco_conta_agencia'],
            conta=obj['banco_conta_numero'],
            operacao=obj.get('banco_conta_operacao') or '',
        )


class ServidorSerializer3(serializers.Serializer):
    cpf = serializers.CharField()
    nome = serializers.CharField()
    siape = serializers.CharField()
    campusId = serializers.CharField()
    campusNome = serializers.CharField()
    email = serializers.CharField()
    tipoUsuario = serializers.CharField()
    sexo = serializers.CharField()
    situacao = serializers.CharField()
    excluido = serializers.BooleanField()


class ContraChequeSerializer2(serializers.Serializer):
    matricula = serializers.CharField()
    ano = serializers.IntegerField()
    mes = serializers.IntegerField()
    valor_bruto = serializers.DecimalField(max_digits=12, decimal_places=2)
    rubricas = serializers.SerializerMethodField()

    def get_rubricas(self, obj):
        rubricas = []
        for ccr in obj['ccr_list']:
            rubricas.append(
                dict(
                    valor=str(ccr['valor'] or 0),
                    prazo=ccr['prazo'],
                    codigo=ccr['rubrica__codigo'],
                    nome=ccr['rubrica__nome'],
                    tipo_codigo=ccr['tipo__codigo'],
                    tipo_nome=ccr['tipo__nome'],
                )
            )
        return rubricas
