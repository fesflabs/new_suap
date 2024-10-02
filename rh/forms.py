import datetime
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.contrib import auth
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms.models import BaseInlineFormSet
from pycpfcnpj import cpfcnpj
from comum.models import User, PessoaTelefone, EstadoCivil, ConselhoProfissional
import re

from comum.models import Ano, Configuracao, Municipio, PessoaEndereco, PrestadorServico, TrocarSenha
from comum.utils import get_setor_cppd, retirar_preposicoes_nome
from djtools import forms
from djtools.choices import Anos, Meses
from djtools.forms.widgets import AutocompleteWidget, BRCpfWidget, TreeWidget
from djtools.forms.wizard import FormWizardPlus
from djtools.templatetags.filters import in_group
from djtools.utils import mask_numbers, send_mail, to_ascii
from rh.importador_ws import ImportadorWs
from rh.models import (
    AcaoSaude,
    AfastamentoSiape,
    AgendaAtendimentoHorario,
    AreaVinculacao,
    Atividade,
    Avaliador,
    Banco,
    CampoExcecaoWS,
    CargaHorariaReduzida,
    CargoClasse,
    CargoEmprego,
    DataConsultaBloqueada,
    Deficiencia,
    ExcecaoDadoWS,
    Funcao,
    Funcionario,
    HorarioAgendado,
    HorarioSemanal,
    Instituicao,
    JornadaTrabalho,
    JornadaTrabalhoPCA,
    Ocorrencia,
    PCA,
    PessoaExterna,
    PessoaFisica,
    PessoaJuridica,
    RegimeJuridico,
    RegimeJuridicoPCA,
    Servidor,
    ServidorFuncaoHistorico,
    ServidorOcorrencia,
    ServidorSetorHistorico,
    Setor,
    SetorJornadaHistorico,
    Situacao,
    SolicitacaoAlteracaoFoto,
    Titulacao,
    UnidadeOrganizacional,
    PessoaJuridicaContato,
    CargoEmpregoArea,
    FormaProvimentoVacancia,
    ServidorReativacaoTemporaria, NivelEscolaridade,
    DadosBancariosPF,
)
from rh.enums import Nacionalidade
from rh.management.commands import importador_pj


def situacoes_usadas():
    situacoes_servidores = (
        Servidor.objects.filter(situacao__isnull=False).values_list("situacao", flat=True).order_by("situacao").distinct()
    )
    situacoes = Situacao.objects.filter(id__in=situacoes_servidores)
    return situacoes


def get_situacao_choices():
    situacao_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    for situacao in situacoes_usadas():
        situacao_choices.append((situacao.id, str(situacao)))
    return situacao_choices


def ocorrencias_usadas():
    return Ocorrencia.objects.filter(
        id__in=ServidorOcorrencia.objects.filter(ocorrencia__isnull=False)
        .values_list("ocorrencia", flat=True)
        .order_by("ocorrencia")
        .distinct()
    )


def get_classe_choices():
    servidores = Servidor.objects.all()
    classe_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    classes_servidores = (
        servidores.filter(cargo_classe__isnull=False).values_list("cargo_classe", flat=True).order_by("cargo_classe").distinct()
    )
    classes = CargoClasse.objects.filter(id__in=classes_servidores)
    for classe in classes:
        classe_choices.append((classe.id, str(classe)))
    return classe_choices


def get_funcao_choices():
    funcao_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    [funcao_choices.append((funcao.id, str(funcao))) for funcao in Funcao.objects.usadas()]
    return funcao_choices


def get_cargo_choices():
    cargo_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    cargos = CargoEmprego.utilizados.all().order_by("nome")
    for cargo in cargos:
        cargo_choices.append((cargo.id, str(cargo)))
    return cargo_choices


def get_cargo_area_choices():
    cargo_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    cargos = CargoEmpregoArea.objects.all().order_by("descricao")
    for cargo in cargos:
        cargo_choices.append((cargo.id, str(cargo)))
    return cargo_choices


def get_titulacao_choices():
    titulacao_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    titulacoes = Titulacao.objects.all().order_by("nome")
    for titulacao in titulacoes:
        titulacao_choices.append((titulacao.id, str(titulacao)))
    return titulacao_choices


def get_atividade_choices():
    servidores = Servidor.objects.all()
    atividade_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    atividades_servidores = (
        servidores.filter(funcao_atividade__isnull=False).values_list("funcao_atividade", flat=True).order_by("funcao_atividade").distinct()
    )
    atividades = Atividade.objects.filter(id__in=atividades_servidores)
    for atividade in atividades:
        atividade_choices.append((atividade.id, str(atividade)))
    return atividade_choices


def get_jornada_choices():
    servidores = Servidor.objects.all()
    jornada_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    jornadas_servidores = (
        servidores.filter(jornada_trabalho__isnull=False).values_list("jornada_trabalho", flat=True).order_by("jornada_trabalho").distinct()
    )
    jornadas = JornadaTrabalho.objects.filter(id__in=jornadas_servidores)
    for jornada in jornadas:
        jornada_choices.append((jornada.id, str(jornada)))
    return jornada_choices


def get_jornada_setor_choices():
    setores = SetorJornadaHistorico.objects.all()
    jornada_setor_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    jornadas_setores = (
        setores.filter(jornada_trabalho__isnull=False).values_list("jornada_trabalho", flat=True).order_by("jornada_trabalho").distinct()
    )
    jornadas_setor = JornadaTrabalho.objects.filter(id__in=jornadas_setores).order_by("nome").distinct()
    for jornada in jornadas_setor:
        jornada_setor_choices.append((jornada.id, str(jornada)))
    return jornada_setor_choices


def get_regime_choices():
    servidores = Servidor.objects.all()
    regime_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    regimes_servidores = (
        servidores.filter(regime_juridico__isnull=False).values_list("regime_juridico", flat=True).order_by("regime_juridico").distinct()
    )
    regimes = RegimeJuridico.objects.filter(id__in=regimes_servidores)
    for regime in regimes:
        regime_choices.append((regime.id, str(regime)))
    return regime_choices


def get_setor_lotacao_siape_choices():
    setor_lotacao_siape_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    setores = Setor.siape.all()
    for setor in setores:
        setor_lotacao_siape_choices.append((setor.id, str(setor)))
    return setor_lotacao_siape_choices


def get_campus_lotacao_siape_choices():
    campus_lotacao_siape_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    campi = UnidadeOrganizacional.objects.siape().all()
    for campus in campi:
        campus_lotacao_siape_choices.append((campus.id, str(campus)))
    return campus_lotacao_siape_choices


def get_setor_exercicio_siape_choices():
    setor_exercicio_siape_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    setores = Setor.siape.all()
    for setor in setores:
        setor_exercicio_siape_choices.append((setor.id, str(setor)))
    return setor_exercicio_siape_choices


def get_campus_exercicio_siape_choices():
    campus_exercicio_siape_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    campi = UnidadeOrganizacional.objects.siape().all()
    for campus in campi:
        campus_exercicio_siape_choices.append((campus.id, str(campus)))
    return campus_exercicio_siape_choices


def get_deficiencia_choices():
    deficiencia_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    qs_deficiencia = Deficiencia.objects.all()
    for d in qs_deficiencia:
        deficiencia_choices.append((d.id, str(d.descricao)))
    return deficiencia_choices


def get_nivel_choices():  # FIX-ME: há algum model com essas informações?
    """
    nível = XYY
    X = nível de capacitação (1 a 4)
    YY = nível por mérito (1 a 16)
    nível inicial = 101
    nível final = 416
    """
    nivel_choices = [("qualquer", "--Qualquer--"), ("vazio", "--Vazio--"), ("nao_vazio", "--Não vazio--")]
    for capacitacao in range(1, 5):  # 1 a 4
        for merito in range(1, 17):  # 1 a 16
            capacitacao_merito = "{}{}".format(capacitacao, ((merito < 10 and "0%s" % merito) or merito))
            nivel_choices.append((capacitacao_merito, capacitacao_merito))
    return nivel_choices


class ConfiguracaoForm(forms.FormPlus):
    setor_rh = forms.ModelChoiceFieldPlus(Setor.objects, label="Setor da Diretoria de Gestão de Pessoas", help_text="DIGPE", required=False)
    setor_procuradoria = forms.ModelChoiceFieldPlus(Setor.objects, label="Setor da Procuradoria Jurídica", help_text="PROJU", required=False)
    setor_auditoria_geral = forms.ModelChoiceFieldPlus(Setor.objects, label="Setor da Auditoria Geral", help_text="AUDGE", required=False)

    fag_considerado_chefia = forms.BooleanField(
        label="Função de Apoio à Gestão - é considerado de chefia?",
        help_text="Marque essa opção entenda que uma função Função de Apoio a gestão permitirá gerenciar o dados e informações servidor como chefe do setor.",
        required=False,
    )
    sigla_funcao_apoio_gestao = forms.CharFieldPlus(label="Sigla Função de Apoio à gestão", help_text="FAG-IFXX", required=False)
    sigla_funcao_substituicao_chefia = forms.CharFieldPlus(
        label="Sigla Função para Substituição de Chefia", help_text="SUB-CHEFIA", required=False
    )
    permite_email_institucional_email_secundario = forms.BooleanField(
        label="Permite email institucional no email secundário?",
        help_text="Marque essa opção caso permita que na escolha do email secundário possa ser escolhido email institucional.",
        required=False,
    )
    fuc_considerado_chefia = forms.BooleanField(
        label="Função de Coordenador de Curso - FUC é considerado de chefia?",
        help_text="Marque essa opção entenda que uma função FUC de coordenação de curso permitirá gerenciar o dados e informações servidor como chefe do setor.",
        required=False,
    )

    urlProducaoWS = forms.CharFieldPlus(label="URL de Produção do WS", required=False)
    urlHomologacaoWS = forms.CharFieldPlus(label="URL de Homologação do WS", required=False)

    siglaSistemaWS = forms.CharFieldPlus(label="Sigla do Sistema para o WS", help_text="IFRN", required=False)
    nomeSistemaWS = forms.CharFieldPlus(label="Nome do Sistema para o WS", help_text="Instituto Federal do RN", required=False)
    senhaWS = forms.CharFieldPlus(label="Senha do WS", required=False)
    codOrgaoWS = forms.CharFieldPlus(label="Código do Orgão para o WS", help_text="12345", required=False)


def GetBuscarServidorForm():
    # Nota: deixei que este form seja acessado via factory porque o correto
    # funcionamento do campo setor precisa que o usuário esteja logado; assim,
    # o formulário não pode ser carregado estaticamente.

    class BuscaServidorForm(forms.FormPlus):
        servidores = Servidor.objects.all()

        matricula = forms.CharField(max_length=10, required=False, label="Matrícula", help_text="Filtrar por exatamente esta matrícula")
        nome = forms.CharField(max_length=80, required=False, help_text="Filtrar por parte do nome")
        cpf = forms.CharField(max_length=14, required=False, label="CPF", help_text="Filtrar por exatamente este CPF")

        categoria_choices = (
            ("todos", "Todos os Servidores"),
            ("docente", "Apenas Docentes"),
            ("tecnico_administrativo", "Apenas Administrativos"),
        )
        categoria = forms.ChoiceField(choices=categoria_choices, required=False)

        excluido_choices = (
            ("", "Qualquer servidor"),
            ("1", "Servidores com ocorrência de exclusão"),
            ("0", "Servidores sem ocorrência de exclusão"),
        )
        excluido = forms.ChoiceField(label="Escopo da Pesquisa", choices=excluido_choices, required=False, initial="0", help_text="")

        cargo_choices = get_cargo_choices()
        cargo_emprego = forms.ChoiceField(choices=cargo_choices, required=False)

        cargo_area_choices = get_cargo_area_choices()
        cargo_emprego_area = forms.ChoiceField(choices=cargo_area_choices, required=False)

        classe_choices = get_classe_choices()
        classe = forms.ChoiceField(
            choices=classe_choices, required=False, help_text="Mostrando somente as classes utilizadas pela instituição"
        )

        nivel_choices = get_nivel_choices()
        nivel = forms.ChoiceField(label="Nível", choices=nivel_choices, required=False)

        funcao_choices = get_funcao_choices()
        funcao = forms.ChoiceField(
            label="Função", help_text="Mostrando somente as funções utilizadas pela instituição", choices=funcao_choices, required=False
        )

        atividade_choices = get_atividade_choices()
        funcao_atividade = forms.ChoiceField(
            label="Atividade",
            help_text="Mostrando somente as atividades utilizadas pela instituição",
            choices=atividade_choices,
            required=False,
        )

        jornada_choices = get_jornada_choices()
        jornada_trabalho = forms.ChoiceField(label="Jornada de Trabalho do Servidor", choices=jornada_choices, required=False)

        jornada_setor_choices = get_jornada_setor_choices()
        jornada_setor_trabalho = forms.ChoiceField(label="Jornada de Trabalho do Setor", choices=jornada_setor_choices, required=False)

        regime_choices = get_regime_choices()
        regime_juridico = forms.ChoiceField(label="Regime Jurídico", choices=regime_choices, required=False)

        titulacao_choices = get_titulacao_choices()
        titulacao = forms.ChoiceField(label="Titulação", choices=titulacao_choices, required=False)

        situacao_choices = get_situacao_choices()
        situacao = forms.ChoiceField(label="Situação", choices=situacao_choices, required=False)

        setor = forms.ModelChoiceField(
            label="Setor SUAP", queryset=Setor.objects.all(), widget=TreeWidget(), required=False, help_text="Selecione um setor SUAP"
        )
        setor_contem = forms.CharField(label="Setor SUAP", required=False, help_text="Parte do nome ou da sigla do setor SUAP")

        setor_lotacao_siape_choices = get_setor_lotacao_siape_choices()
        setor_lotacao_siape = forms.ChoiceField(
            label="Setor lotação SIAPE",
            choices=setor_lotacao_siape_choices,
            required=False,
            help_text="Selecione um setor de lotação SIAPE",
        )

        campus_lotacao_siape_choices = get_campus_lotacao_siape_choices()
        campus_lotacao_siape = forms.ChoiceField(
            label="Campus Lotação SIAPE",
            choices=campus_lotacao_siape_choices,
            required=False,
            help_text="Selecione um campus de lotação SIAPE",
        )

        setor_exercicio_siape_choices = get_setor_exercicio_siape_choices()
        setor_exercicio_siape = forms.ChoiceField(
            label="Setor Exercício SIAPE",
            choices=setor_exercicio_siape_choices,
            required=False,
            help_text="Selecione um setor de exercício SIAPE",
        )

        campus_exercicio_siape_choices = get_campus_exercicio_siape_choices()
        campus_exercicio_siape = forms.ChoiceField(
            label="Campus Exercício SIAPE",
            choices=campus_exercicio_siape_choices,
            required=False,
            help_text="Selecione um campus de exercício SIAPE",
        )

        recursivo = forms.BooleanField(required=False, help_text='Incluir sub-setores para filtro "Setor SUAP"')

        agrupador = forms.CharField(
            label="Agrupar por",
            required=False,
            widget=forms.Select(),
            help_text="Para agrupar, marque pelo menos uma das informações na caixa abaixo",
        )

        subagrupador = forms.CharField(
            label="Sub-agrupar por",
            required=False,
            widget=forms.Select(),
            help_text="Para agrupar, marque pelo menos uma das informações na caixa abaixo",
        )

        tem_digital_choices = (("", "Qualquer"), ("sim", "Sim"), ("nao", "Não"))
        tem_digital = forms.ChoiceField(label="Tem digital cadastrada", choices=tem_digital_choices, required=False, help_text="")

        aniversariantes = forms.MesField(label="Aniversariantes", required=False, empty_label="Todos")
        if "edu" in settings.INSTALLED_APPS:
            from edu.models import Disciplina

            disciplina_ingresso_choices = [("vazio", "--Vazio--"), ("nulo", "--Docente sem disciplina de ingresso cadastrada--")]
            disciplinas = Disciplina.objects.all()
            for disciplina in disciplinas:
                disciplina_ingresso_choices.append((disciplina.id, str(disciplina)))

            disciplina_ingresso_choices = disciplina_ingresso_choices
            disciplina_ingresso = forms.ChoiceField(
                label="Disciplina de Ingresso", choices=disciplina_ingresso_choices, required=False, help_text="No caso de docentes"
            )

        deficiencia = forms.ChoiceField(label="Deficiência", choices=get_deficiencia_choices(), required=False)

        fieldsets = (
            ("Filtro Geral", {"fields": ("excluido",)}),
            ("Filtro por Dados Pessoais", {"fields": (("nome", "cpf"), "deficiencia")}),
            (
                "Filtro por Dados Funcionais",
                {
                    "fields": (
                        ("matricula", "categoria"),
                        "situacao",
                        "cargo_emprego",
                        "cargo_emprego_area",
                        ("classe", "nivel"),
                        ("funcao", "funcao_atividade"),
                        ("jornada_trabalho", "regime_juridico", "jornada_setor_trabalho"),
                    )
                },
            ),
            ("Filtro por Dados como Professor", {"fields": ("disciplina_ingresso",)}),
            (
                "Filtro por Setor Lotação/Exercício",
                {
                    "fields": (
                        "setor",
                        "recursivo",
                        "setor_contem",
                        ("setor_lotacao_siape", "campus_lotacao_siape"),
                        ("setor_exercicio_siape", "campus_exercicio_siape"),
                    )
                },
            ),
            ("Filtro por Outros dados", {"fields": ("titulacao", "aniversariantes", "tem_digital")}),
            ("Agrupar Resultados", {"fields": ("agrupador", "subagrupador")}),
        )

        METHOD = "GET"

    return BuscaServidorForm


def get_campus_choices():
    campus_choices = [("", "Todos")]
    campus = UnidadeOrganizacional.objects.suap().all()
    for campus in campus:
        campus_choices.append((campus.id, str(campus)))
    return campus_choices


def get_funcaoservidor_choices():
    funcao_choices = [("", "Todas")]
    funcoes = Funcao.objects.usadas()
    for funcao in funcoes:
        funcao_choices.append((funcao.id, str(funcao)))
    return funcao_choices


def ServidorFuncaoFormFactory():
    """
    Cria uma classe para construir filtros para a busca de servidores
    com funcao.

    """

    class CampusFuncao(forms.FormPlus):
        campus_choices = get_campus_choices()
        campus = forms.ChoiceField(
            choices=campus_choices, label="Campus", widget=forms.Select(attrs={"onchange": "submeter_form(this)"}), required=False
        )
        funcao_choices = get_funcaoservidor_choices()
        funcao = forms.ChoiceField(
            choices=funcao_choices, label="Função", widget=forms.Select(attrs={"onchange": "submeter_form(this)"}), required=False
        )

    return CampusFuncao


class UploadArquivosExtratorForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus(required=True, label="Arquivos Extrator Zipado")

    def clean_arquivo(self):
        if "arquivo" in self.files:
            arquivo = self.files["arquivo"]
            if arquivo.name.endswith(".zip"):
                return self.cleaned_data
            raise forms.ValidationError("Arquivos tem que estar zipados (.zip)")


def CampusAnoFormFactory():
    class CampusAnoForm(forms.FormPlus):
        campus_choices = get_campus_choices()
        campus = forms.ChoiceField(choices=campus_choices, label="Campus", required=False)

        ano = forms.ChoiceField(choices=Anos.get_choices(), label="Ano", required=True)

    return CampusAnoForm


class SetorForm(forms.ModelFormPlus):
    setores_compartilhados = forms.MultipleModelChoiceFieldPlus(required=False, queryset=Setor.objects.all())
    superior = forms.ModelChoiceField(label="Setor Superior", queryset=Setor.objects.all(), widget=TreeWidget(), required=False)

    class Meta:
        model = Setor
        exclude = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fieldsets = [
            ("Dados Gerais", {"fields": ["codigo", "codigo_siorg", "superior", "sigla", "nome", "excluido"]}),
            ("Protocolo", {"fields": ["setores_compartilhados"]}),
            ("Avaliação Integrada", {"fields": ["areas_vinculacao"]}),
            ("Funcionamento", {"fields": ["data_criacao", "horario_funcionamento", "bases_legais_internas", "bases_legais_externas"]}),
        ]

        if not self.request.user.is_superuser:
            del self.fieldsets[0][1]["fields"][0]

    def clean_superior(self):
        if self.cleaned_data["superior"] and self.instance.id == self.cleaned_data["superior"].id:
            raise forms.ValidationError("O setor superior não pode ser o próprio setor.")
        return self.cleaned_data["superior"]


class BasesLegaisSetorForm(forms.ModelFormPlus):
    class Meta:
        model = Setor
        fields = ("data_criacao", "horario_funcionamento", "bases_legais_internas", "bases_legais_externas")


class SetorAddForm(SetorForm):
    # jornada de trabalho atual APENAS durante a inclusão de um novo setor
    jornada_trabalho = forms.ModelChoiceField(label="Jornada de Trabalho Atual", queryset=JornadaTrabalho.objects, required=False)
    data_inicio_da_jornada = forms.DateFieldPlus(label="Data Inicial da Jornada de Trabalho Atual", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fieldsets += ("Carga Horária Atual", {"fields": ["jornada_trabalho", "data_inicio_da_jornada"]})

    def clean(self):
        cleaned_data = super().clean()
        #
        jornada_trabalho = cleaned_data.get("jornada_trabalho", None)
        data_inicio_da_jornada = cleaned_data.get("data_inicio_da_jornada", None)
        if jornada_trabalho or data_inicio_da_jornada:
            if jornada_trabalho and not data_inicio_da_jornada:
                self.add_error("data_inicio_da_jornada", "A Data Inicial da Jornada de Trabalho Atual deve ser informada.")
            if data_inicio_da_jornada and not jornada_trabalho:
                self.add_error("jornada_trabalho", "A Jornada de Trabalho Atual deve ser informada.")
        #
        return cleaned_data

    def _save_m2m(self):
        super()._save_m2m()
        #
        # adiciona jornada de trabalho que foi informada durante a inclusão do novo setor
        jornada_trabalho = self.cleaned_data.get("jornada_trabalho", None)
        data_inicio_da_jornada = self.cleaned_data.get("data_inicio_da_jornada", None)
        if jornada_trabalho and data_inicio_da_jornada:
            nova_jornada = SetorJornadaHistorico()
            nova_jornada.setor = self.instance  # nesse ponto, o setor já foi salvo e tem ID
            nova_jornada.jornada_trabalho = jornada_trabalho
            nova_jornada.data_inicio_da_jornada = data_inicio_da_jornada
            nova_jornada.save()


def SetorJornadaHistoricoFormFactory(request):
    raiz = Setor.objects.none()
    if request.user.has_perm("rh.eh_rh_sistemico"):
        raiz = Setor.raiz()
    elif request.user.has_perm("rh.pode_gerenciar_setor_jornada_historico"):
        funcionario = request.user.get_relacionamento()
        raiz = funcionario.setor.superior if funcionario.setor else raiz

    class SetorJornadaHistoricoForm(forms.ModelForm):
        setor = forms.ModelChoiceField(queryset=Setor.objects.all(), widget=TreeWidget(root_nodes=[raiz]))

        class Meta:
            model = SetorJornadaHistorico
            fields = ("setor", "jornada_trabalho", "data_inicio_da_jornada", "data_fim_da_jornada")

        def clean(self):
            super().clean()
            if not self.errors:
                #
                # periodo adicionado/editado
                #
                periodo_data_inicio = self.cleaned_data["data_inicio_da_jornada"]
                periodo_data_fim = self.cleaned_data["data_fim_da_jornada"]

                #
                # valida o período
                #
                if periodo_data_fim and periodo_data_inicio > periodo_data_fim:
                    self._errors["data_inicio_da_jornada"] = self.error_class(["A data inicial deve ser menor ou igual à data final."])
                    del self.cleaned_data["data_fim_da_jornada"]

            return self.cleaned_data

    return SetorJornadaHistoricoForm


class PessoaEnderecoForm(forms.ModelFormPlus):
    municipio = forms.ModelChoiceFieldPlus(Municipio.objects, label="Município")
    complemento = forms.CharFieldPlus(label="Complemento", required=False)
    cep = forms.BrCepField(max_length=255, required=True, label="CEP")

    class Meta:
        model = PessoaEndereco
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["via_form_suap"].widget = forms.HiddenInput()
        self.fields["via_form_suap"].initial = True


class PessoaFisicaForm(forms.ModelFormPlus):
    class Meta:
        model = PessoaFisica
        exclude = ()

    cpf = forms.BrCpfField()
    nascimento_data = forms.DateFieldPlus(required=False, label="Data de Nascimento")

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not cpfcnpj.validate(cpf):
            self.add_error("cpf", "O CPF informado não é válido")
        return cpf


class PessoaExternaForm(forms.ModelFormPlus):
    class Meta:
        model = PessoaExterna
        fields = ("nome", "sexo", "cpf", "nascimento_data")

    cpf = forms.BrCpfField()
    email = forms.EmailField(required=True)
    nascimento_data = forms.DateFieldPlus(required=False, label="Data de Nascimento")

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        if not cpfcnpj.validate(cpf):
            self.add_error("cpf", "O CPF informado não é válido.")
        if self.instance and not self.instance.pk and PessoaExterna.objects.filter(cpf=cpf):
            self.add_error("cpf", "O CPF informado já está cadastrado.")

        return cpf


class PessoaJuridicaForm(forms.ModelFormPlus):
    nome = forms.CharField(label="Razão Social", required=True)
    nome_fantasia = forms.CharField(
        label="Nome Fantasia", required=False, help_text="Na ausência do nome fantasia, é para repetir a razão social"
    )
    cnpj = forms.BrCnpjField()

    class Meta:
        model = PessoaJuridica
        exclude = ()

    def clean_cnpj(self):
        cnpj = self.cleaned_data.get("cnpj")
        if not cpfcnpj.validate(cnpj):
            self.add_error("cpf", "O CNPJ informado não é válido")
        return cnpj


class PessoaJurificaContatoForm(forms.ModelFormPlus):
    descricao = forms.CharField(label="Descrição", required=False)
    telefone = forms.CharField(label="Telefone", required=False)
    email = forms.EmailField(label="E-mail", required=False)

    class Meta:
        model = PessoaJuridicaContato
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["via_form_suap"].widget = forms.HiddenInput()
        self.fields["via_form_suap"].initial = True


class ImportacaoPJForm(forms.FormPlus):
    pj = forms.FileFieldPlus(
        label="Pessoa Jurídica",
        required=False,
        help_text="Arquivo em formato CSV contendo as colunas Razão Social, CNPJ, Endereco, Bairro, Telefone, Cep ,Cidade UF",
    )

    def processar(self):
        command = importador_pj.Command()
        errors = command.handle(*[], **{"pj": self.cleaned_data["pj"]})
        return errors


############
# Servidor #
############


def get_choices_nome_usual(nome):
    nome_capitalizado = retirar_preposicoes_nome(nome)
    choices = [["", "---"]]
    for token in nome_capitalizado.split():
        for token1 in nome_capitalizado.split():
            if token != token1:
                choice = to_ascii("{} {}".format(token, token1))
                choices.append([choice, choice])
    return choices


class ServidorInformacoesPessoaisForm(forms.ModelFormPlus):
    nome_usual = forms.ChoiceField(label="Nome Usual", required=True, help_text="Nome que será exibido no SUAP")
    nascimento_municipio = forms.ModelChoiceFieldPlus(Municipio.objects.all(), required=False, label="Naturalidade")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = get_choices_nome_usual(self.instance.nome)
        self.fields["nome_usual"].choices = choices
        if len(choices) == 1:
            self.fields["nome_usual"].required = False

    class Meta:
        model = Servidor
        fields = ["nome_usual"]


class PessoaFisicaInformacoesDigitaisFracasForm(forms.ModelFormPlus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "senha_ponto" in self.fields:
            self.fields["senha_ponto"].widget = forms.PasswordInput(attrs={"autocomplete": "off"})

    class Meta:
        model = PessoaFisica
        fields = ["tem_digital_fraca", "senha_ponto"]

    def clean_senha_ponto(self):
        # Usado para criptografar a senha
        if self.cleaned_data["senha_ponto"]:
            from hashlib import md5

            m = md5()
            m.update(self.cleaned_data["senha_ponto"].encode())
            self.cleaned_data["senha_ponto"] = m.hexdigest()
        return self.cleaned_data["senha_ponto"]


class PessoaFisicaAlterarSenhaPontoForm(forms.ModelFormPlus):
    senha = forms.CharField(label="Senha para confirmar", widget=forms.PasswordInput)
    confirmar = forms.BooleanField(label="Confirma a operação")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "senha_ponto" in self.fields:
            self.fields["senha_ponto"].widget = forms.PasswordInput(attrs={"autocomplete": "off"})

    class Meta:
        model = PessoaFisica
        fields = ["senha_ponto"]

    def clean_senha_ponto(self):
        # Usado para criptografar a senha
        if self.cleaned_data["senha_ponto"]:
            from hashlib import md5

            m = md5()
            m.update(self.cleaned_data["senha_ponto"].encode())
            self.cleaned_data["senha_ponto"] = m.hexdigest()
        return self.cleaned_data["senha_ponto"]

    def clean(self):
        cleaned_data = super().clean()
        if "confirmar" in cleaned_data and cleaned_data["confirmar"]:
            if cleaned_data.get("senha") and not auth.authenticate(username=self.request.user.username, password=cleaned_data["senha"]):
                raise forms.ValidationError("A senha não confere com a do usuário logado.")

        return cleaned_data


class ServidorForm(ServidorInformacoesPessoaisForm):
    setor = forms.ModelChoiceField(label="Setor SUAP", queryset=Setor.objects.all(), widget=TreeWidget(), required=False)
    setor_exercicio = forms.ModelChoiceField(
        label="Setor de Exercício SIAPE", queryset=Setor.siape.all(), widget=TreeWidget(), required=False
    )
    setores_adicionais = forms.MultipleModelChoiceFieldPlus(
        required=False,
        queryset=Setor.objects.all(),
        help_text="Os setores adicionais estarão visíveis para o servidor no módulo de protocolo",
    )
    cpf = forms.CharField(label="CPF", widget=BRCpfWidget, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "senha_ponto" in self.fields:
            self.fields["senha_ponto"].widget = forms.PasswordInput(attrs={"autocomplete": "off"})

        if "cargo_emprego" in self.fields:
            qs_cargoemprego = CargoEmprego.utilizados
            if self.request.user.has_perm("rh.pode_editar_cargo_emprego_externo"):
                qs_cargoemprego = CargoEmprego.objects

            self.fields["cargo_emprego"] = forms.ModelChoiceField(
                label="Cargo Emprego",
                queryset=qs_cargoemprego,
                required=False,
                widget=AutocompleteWidget(search_fields=CargoEmprego.SEARCH_FIELDS),
            )

    def clean_setor(self):
        """
        Assegura que o setor SUAP seja do mesmo campus (equivalente) do setor de
        exercício SIAPE. Essa condição só vale quando as árvores de Setor SUAP e
        SIAPE são distintas.
        """
        if Configuracao.get_valor_por_chave(app="comum", chave="setores") == "SUAP":
            obj = self.instance
            # Tentando encontrar o setor_exercicio.uo.equivalente
            try:
                uo_equivalente = obj.setor_exercicio.uo.equivalente
            except AttributeError:
                uo_equivalente = None

            if (
                obj.setor_exercicio
                and self.cleaned_data["setor"]
                and uo_equivalente != self.cleaned_data["setor"].uo
                and not obj.eh_estagiario
            ):
                raise forms.ValidationError("O setor SUAP deve estar no mesmo campus do setor de exercício SIAPE: %s" % uo_equivalente)

        return self.cleaned_data["setor"]

    def clean_nome(self):
        """
        Assegura que o nome SUAP seja do mesmo que veio do SIAPE
        """
        if to_ascii(self.instance.nome).lower() and to_ascii(self.instance.nome).lower() != to_ascii(self.cleaned_data["nome"]).lower():
            raise forms.ValidationError("O nome do servidor deve ser igual ao nome que vem no SIAPE")
        return self.cleaned_data["nome"]

    def clean_foto(self):
        # Usado para definir que o nome da foto é "<pk>.jpg"
        from django.core.files.uploadedfile import InMemoryUploadedFile

        foto_file = self.cleaned_data["foto"]
        if isinstance(foto_file, InMemoryUploadedFile):
            # Pode ser ImageWithThumbsFieldFile caso não seja submetida nenhuma foto
            foto_file.name = "%s.jpg" % self.instance.pk
        return self.cleaned_data["foto"]

    def clean_senha_ponto(self):
        # Usado para criptografar a senha
        if self.cleaned_data["senha_ponto"]:
            from hashlib import md5

            m = md5()
            m.update(self.cleaned_data["senha_ponto"].encode())
            self.cleaned_data["senha_ponto"] = m.hexdigest()
        return self.cleaned_data["senha_ponto"]


class ServidorSetorHistoricoForm(forms.ModelFormPlus):
    class Meta:
        model = ServidorSetorHistorico
        fields = ("servidor", "setor", "data_inicio_no_setor", "data_fim_no_setor")

    servidor = forms.ModelChoiceField(
        label="Servidor", queryset=Servidor.objects.all(), required=True, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS)
    )
    setor = forms.ModelChoiceField(label="Setor SUAP", queryset=Setor.objects.all(), widget=TreeWidget(), required=True)
    fieldsets = [("", {"fields": ["servidor", "setor", "data_inicio_no_setor", "data_fim_no_setor"]})]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["servidor"].widget.readonly = True

    def clean(self):
        super().clean()
        if not self.errors:
            if not self.instance.pk:
                servidor = self.cleaned_data["servidor"]
                data_inicio_no_setor = self.cleaned_data["data_inicio_no_setor"]
                setor = self.cleaned_data["setor"]
                historico = ServidorSetorHistorico.objects.filter(servidor=servidor).order_by("-data_inicio_no_setor")
                if historico:
                    historico_atual = historico[0]
                    if setor != historico_atual.setor:
                        if data_inicio_no_setor > historico_atual.data_inicio_no_setor:
                            #
                            # atualizando a data fim do então período mais atual
                            dia_subtr = timedelta(days=1)
                            ServidorSetorHistorico.objects.filter(pk=historico_atual.pk).update(
                                data_fim_no_setor=(data_inicio_no_setor - dia_subtr)
                            )

                            # raise forms.ValidationError(
                            #     u'Não é possível criar Histórico para periodos a frente do mais atual')
            else:
                servidor = self.cleaned_data["servidor"]
                servidor_historico_atual = ServidorSetorHistorico.objects.filter(servidor=servidor).order_by("-data_inicio_no_setor")[0]
                if servidor_historico_atual.pk == self.instance.pk:
                    if self.cleaned_data["data_fim_no_setor"]:
                        raise forms.ValidationError("Não é possível fechar o este periodo. Ele é o mais atual")
        return self.cleaned_data


def GetServidorFuncaoHistoricoForm(user):
    funcionario = user.get_relacionamento()
    setor_funcionario = funcionario.setor
    setor_exercicio_funcionario = funcionario.setor_exercicio
    qs_suap = Setor.suap.none()
    qs_siape = Setor.siape.none()
    if user.has_perm("rh.eh_rh_sistemico"):
        qs_suap = Setor.suap.filter(excluido=False)
        qs_siape = Setor.siape.filter(excluido=False)

    elif user.has_perm("rh.eh_rh_campus") or user.has_perm("rh.gabinete"):
        qs_suap = Setor.suap.filter(excluido=False, uo=setor_funcionario.uo)
        if setor_exercicio_funcionario:
            qs_siape = Setor.siape.filter(excluido=False, uo=setor_exercicio_funcionario.uo)
        else:
            qs_siape = Setor.siape.filter(excluido=False, uo__equivalente=setor_funcionario.uo)

    class ServidorFuncaoHistoricoForm(forms.ModelFormPlus):
        servidor = forms.ModelChoiceField(label="Servidor", queryset=Servidor.objects.all(), required=True, widget=AutocompleteWidget())
        data_inicio_funcao = forms.DateFieldPlus(label="Data Início na Função", required=True)
        data_fim_funcao = forms.DateFieldPlus(
            label="Data Fim na Função", required=False, help_text="Deixar em branco caso essa seja a função atual do servidor."
        )
        funcao = forms.ModelChoiceField(label="Função", queryset=Funcao.objects.filter(funcao_suap=True), required=True)
        atividade = forms.ModelChoiceField(label="Atividade", queryset=Atividade.usadas, required=False)
        setor = forms.ModelChoiceField(label="Setor SIAPE", queryset=qs_siape, widget=AutocompleteWidget(), required=True)
        setor_suap = forms.ModelChoiceField(label="Setor SUAP", queryset=qs_suap, widget=AutocompleteWidget(), required=True)
        nome_amigavel = forms.CharFieldPlus(label="Nome Amigável da Função", required=False)
        nivel = forms.CharFieldPlus(max_length=4, required=False, label="Nível")
        atualiza_pelo_extrator = forms.BooleanField(
            label="Atualiza pelo extrator?", required=False, help_text="Informar se esse registro será afetado pelo extrator siape."
        )

        class Meta:
            model = ServidorFuncaoHistorico
            fields = (
                "servidor",
                "data_inicio_funcao",
                "data_fim_funcao",
                "funcao",
                "nivel",
                "atividade",
                "setor",
                "setor_suap",
                "nome_amigavel",
                "atualiza_pelo_extrator",
            )

    return ServidorFuncaoHistoricoForm


def GetServidorFuncaoSiapeHistoricoForm(user):
    funcionario = user.get_relacionamento()
    raiz = None
    if user.has_perm("rh.eh_rh_sistemico"):
        raiz = Setor.raiz()
    elif user.has_perm("rh.eh_rh_campus") or user.has_perm("rh.gabinete"):
        raiz = funcionario.setor.uo.setor

    class ServidorFuncaoSiapeHistoricoForm(forms.ModelFormPlus):
        servidor = forms.ModelChoiceField(
            label="Servidor", queryset=Servidor.objects, required=True, widget=AutocompleteWidget(readonly=True)
        )
        funcao = forms.ModelChoiceField(label="Função", queryset=Funcao.objects, required=True, widget=AutocompleteWidget(readonly=True))
        atividade = forms.ModelChoiceField(label="Atividade", queryset=Atividade.usadas, required=True, widget=AutocompleteWidget())
        setor_suap = forms.ModelChoiceField(
            label="Setor SUAP", queryset=Setor.suap.filter(excluido=False), widget=TreeWidget(root_nodes=[raiz]), required=True
        )
        nome_amigavel = forms.CharFieldPlus(label="Nome Amigável da Função", required=False)
        data_fim_funcao = forms.DateFieldPlus(
            label="Data Fim na Função", required=False, help_text="Deixar em branco caso essa seja a função atual do servidor."
        )
        atualiza_pelo_extrator = forms.BooleanField(
            label="Atualiza pelo extrator?", required=False, help_text="Informar se esse registro será afetado pelo extrator siape."
        )

        class Meta:
            model = ServidorFuncaoHistorico
            fields = ("servidor", "funcao", "atividade", "setor_suap", "data_fim_funcao", "nome_amigavel", "atualiza_pelo_extrator")

    return ServidorFuncaoSiapeHistoricoForm


class AvaliadorExternoForm(forms.ModelFormPlus):
    matricula_siape = forms.CharFieldPlus(width=300, label="Matrícula SIAPE")
    nome = forms.CharFieldPlus(width=300, label="Nome")
    cpf = forms.BrCpfField(label="CPF")
    email = forms.EmailField(max_length=255, label="E-mail para Contato")
    numero_telefone = forms.BrTelefoneField(max_length=45, label="Telefone para Contato")
    instituicao_origem = forms.ModelChoiceField(Instituicao.objects, label="Instituição de Origem")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["matricula_siape"].initial = self.instance.matricula_siape
            self.fields["nome"].initial = self.instance.vinculo.pessoa.pessoafisica.nome
            self.fields["cpf"].initial = self.instance.vinculo.pessoa.pessoafisica.cpf
            self.fields["email"].initial = self.instance.vinculo.pessoa.pessoafisica.email
            self.fields["instituicao_origem"].initial = self.instance.instituicao_origem
            telefones = self.instance.vinculo.pessoa.pessoafisica.pessoatelefone_set.filter(observacao=Avaliador.TELEFONE_CELULAR)
            if telefones.exists():
                telefone = telefones[0]
                self.fields["numero_telefone"].initial = telefone.numero

    class Meta:
        model = Avaliador
        fields = ("ativo",)

    def clean_cpf(self):
        if not self.instance.id:
            prestador = PrestadorServico.objects.filter(cpf=self.cleaned_data["cpf"])
            if prestador.exists() and Avaliador.objects.filter(vinculo__pessoa=prestador[0].pessoafisica.pessoa_ptr).exists():
                raise forms.ValidationError("Já existe um avaliador externo cadastrado com este CPF.")

        return self.cleaned_data["cpf"]

    def clean_email(self):
        Configuracao = apps.get_model("comum", "configuracao")
        if not Configuracao.get_valor_por_chave(
            "rh", "permite_email_institucional_email_secundario"
        ) and Configuracao.eh_email_institucional(self.cleaned_data["email"]):
            raise forms.ValidationError("Escolha um e-mail que não seja institucional.")

        return self.cleaned_data["email"]

    @transaction.atomic
    def save(self, commit=True):
        matricula_siape = self.cleaned_data.get("matricula_siape")
        nome = self.cleaned_data.get("nome")
        cpf = self.cleaned_data.get("cpf")
        email = self.cleaned_data.get("email")
        numero_telefone = self.cleaned_data.get("numero_telefone")
        instituicao_origem = self.cleaned_data.get("instituicao_origem")
        username = cpf.replace(".", "").replace("-", "")
        qs = PrestadorServico.objects.filter(cpf=cpf)
        prestador_existente = qs.exists()
        if prestador_existente:
            prestador = qs[0]
        else:
            prestador = PrestadorServico()

        prestador.nome = nome
        prestador.nome_registro = nome
        prestador.username = username
        prestador.cpf = cpf
        prestador.email = email
        if not prestador.email_secundario or prestador.email_secundario != email:
            prestador.email_secundario = email
        prestador.ativo = True
        if not prestador.setor:
            prestador.setor = get_setor_cppd()

        prestador.save()

        telefones = prestador.pessoatelefone_set.filter(observacao=Avaliador.TELEFONE_CELULAR)
        if not telefones.exists():
            prestador.pessoatelefone_set.create(numero=numero_telefone, observacao=Avaliador.TELEFONE_CELULAR)
        else:
            telefone = telefones[0]
            telefone.numero = numero_telefone
            telefone.save()

        # atualizando email secundário da pessoa física
        pessoa_fisica = PessoaFisica.objects.filter(username=username)
        if pessoa_fisica.exists():
            pessoa = pessoa_fisica[0]
            if pessoa.email_secundario != email:
                pessoa.email_secundario = email

        avaliador = super().save(False)
        avaliador.matricula_siape = matricula_siape
        avaliador.vinculo = prestador.vinculos.first()
        avaliador.email_contato = email
        avaliador.instituicao_origem = instituicao_origem
        avaliador.save()

        LdapConf = apps.get_model("ldap_backend", "LdapConf")
        conf = LdapConf.get_active()
        conf.sync_user(prestador)

        if not prestador_existente:
            self.enviar_email(prestador.username, email)

        return avaliador

    def enviar_email(self, username, email):
        obj = TrocarSenha.objects.create(username=username)
        url = "{}/comum/trocar_senha/{}/{}/".format(settings.SITE_URL, obj.username, obj.token)
        conteudo = (
            """
            <h1>Cadastro de Avaliador Externo</h1>
            <p>Prezado usuário,</p>
            <br />
            <p>Você acaba de ser cadastrado no banco de dados de avaliadores externos do IFRN e poderá ser selecionado
            para eventuais processos de RSC ou Professor titular, para definição de senha referente às suas credenciais
            da rede, por favor, acesse o endereço: %s.</p>
            """
            % url
        )
        return send_mail("[SUAP] Cadastro de Avaliador Externo", conteudo, settings.DEFAULT_FROM_EMAIL, [email])


class AtualizarDadosAvaliadorForm(forms.FormPlus):
    nome = forms.CharFieldPlus(max_length=200)
    sexo = forms.ChoiceField(choices=[["M", "Masculino"], ["F", "Feminino"]], required=False)
    nascimento_data = forms.DateFieldPlus(label="Data de Nascimento")
    email = forms.EmailField(max_length=255, label="E-mail para Contato")

    matricula_siape = forms.CharFieldPlus(label="Matrícula SIAPE", max_length=50)
    instituicao_origem = forms.ModelChoiceFieldPlus(Instituicao.objects)

    numero_documento_identificacao = forms.CharField(
        label="Número do Documento de Identificação", max_length=50, help_text="Somente números"
    )
    emissor_documento_identificacao = forms.CharField(label="Emissor do Documento de Identificação", max_length=50)
    pis_pasep = forms.CharFieldPlus(label="PIS/PASEP", max_length=50)

    telefone_celular = forms.BrTelefoneField(max_length=45, label="Telefone Celular")
    telefone_residencial = forms.BrTelefoneField(max_length=45, required=False, label="Telefone Residencial")
    telefone_comercial = forms.BrTelefoneField(max_length=45, required=False, label="Telefone Comercial")

    municipio = forms.CharFieldPlus(max_length=255, label="Município")
    logradouro = forms.CharFieldPlus(max_length=255, label="Logradouro")
    numero = forms.CharFieldPlus(max_length=255, label="Número", width=100)
    bairro = forms.CharFieldPlus(max_length=255, label="Bairro")
    complemento = forms.CharFieldPlus(max_length=255, label="Complemento")
    cep = forms.BrCepField(max_length=255, label="CEP")

    banco = forms.ModelChoiceFieldPlus(Banco.objects)
    numero_agencia = forms.CharField(label="Número da Agência", max_length=50, help_text="Ex: 3293-X")
    tipo_conta = forms.ChoiceField(label="Tipo da Conta", choices=Avaliador.TIPOCONTA_CHOICES)
    numero_conta = forms.CharField(label="Número da Conta", max_length=50, help_text="Ex: 23384-6")
    operacao = forms.CharField(label="Operação", max_length=50, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pessoa_fisica = self.request.user.get_profile()
        avaliador = Avaliador.objects.get(vinculo__pessoa=pessoa_fisica.pessoa_ptr)

        self.fields["nome"].initial = pessoa_fisica.nome
        self.fields["nascimento_data"].initial = pessoa_fisica.nascimento_data
        self.fields["email"].initial = avaliador.email_contato
        self.fields["sexo"].initial = pessoa_fisica.sexo

        self.fields["matricula_siape"].initial = avaliador.matricula_siape
        self.fields["instituicao_origem"].initial = avaliador.instituicao_origem

        self.fields["numero_documento_identificacao"].initial = avaliador.numero_documento_identificacao
        self.fields["emissor_documento_identificacao"].initial = avaliador.emissor_documento_identificacao
        self.fields["pis_pasep"].initial = avaliador.pis_pasep

        telefones = pessoa_fisica.pessoatelefone_set
        if telefones.exists():
            telefone_celular = telefones.filter(observacao=Avaliador.TELEFONE_CELULAR)
            if telefone_celular.exists():
                self.fields["telefone_celular"].initial = telefone_celular[0].numero

            telefone_residencial = telefones.filter(observacao=Avaliador.TELEFONE_RESIDENCIAL)
            if telefone_residencial.exists():
                self.fields["telefone_residencial"].initial = telefone_residencial[0].numero

            telefone_comercial = telefones.filter(observacao=Avaliador.TELEFONE_COMERCIAL)
            if telefone_comercial.exists():
                self.fields["telefone_comercial"].initial = telefone_comercial[0].numero

        self.fields["municipio"].initial = avaliador.endereco_municipio
        self.fields["logradouro"].initial = avaliador.endereco_logradouro
        self.fields["numero"].initial = avaliador.endereco_numero
        self.fields["bairro"].initial = avaliador.endereco_bairro
        self.fields["complemento"].initial = avaliador.endereco_complemento
        self.fields["cep"].initial = avaliador.endereco_cep

        self.fields["banco"].queryset = Banco.objects.filter(excluido=False)
        self.fields["banco"].initial = avaliador.banco

        self.fields["numero_agencia"].initial = avaliador.numero_agencia
        self.fields["tipo_conta"].initial = avaliador.tipo_conta
        self.fields["numero_conta"].initial = avaliador.numero_conta
        self.fields["operacao"].initial = avaliador.operacao

    @transaction.atomic
    def save(self, commit=True):
        pessoa_fisica = self.request.user.get_profile()
        avaliador = Avaliador.objects.get(vinculo__pessoa=pessoa_fisica.pessoa_ptr)
        pessoa_fisica.nome = self.cleaned_data["nome"]
        pessoa_fisica.nascimento_data = self.cleaned_data["nascimento_data"]
        avaliador.email_contato = self.cleaned_data["email"]
        pessoa_fisica.sexo = self.cleaned_data["sexo"]

        avaliador.matricula_siape = self.cleaned_data["matricula_siape"]
        avaliador.instituicao_origem = self.cleaned_data["instituicao_origem"]

        avaliador.numero_documento_identificacao = self.cleaned_data["numero_documento_identificacao"]
        avaliador.emissor_documento_identificacao = self.cleaned_data["emissor_documento_identificacao"]
        avaliador.pis_pasep = self.cleaned_data["pis_pasep"]

        telefones = pessoa_fisica.pessoatelefone_set
        telefone_celular = telefones.filter(observacao=Avaliador.TELEFONE_CELULAR)
        if telefone_celular.exists():
            telefone_celular[0].numero = self.cleaned_data["telefone_celular"]
            telefone_celular[0].observacao = Avaliador.TELEFONE_CELULAR
            telefone_celular[0].save()
        else:
            pessoa_fisica.pessoatelefone_set.create(numero=self.cleaned_data["telefone_celular"], observacao=Avaliador.TELEFONE_CELULAR)

        telefone_residencial = telefones.filter(observacao=Avaliador.TELEFONE_RESIDENCIAL)
        if telefone_residencial.exists():
            telefone_residencial[0].numero = self.cleaned_data["telefone_residencial"]
            telefone_celular[0].observacao = Avaliador.TELEFONE_RESIDENCIAL
            telefone_residencial[0].save()
        else:
            pessoa_fisica.pessoatelefone_set.create(
                numero=self.cleaned_data["telefone_residencial"], observacao=Avaliador.TELEFONE_RESIDENCIAL
            )

        telefone_comercial = telefones.filter(observacao=Avaliador.TELEFONE_COMERCIAL)
        if telefone_comercial.exists():
            telefone_comercial[0].numero = self.cleaned_data["telefone_comercial"]
            telefone_celular[0].observacao = Avaliador.TELEFONE_COMERCIAL
            telefone_comercial[0].save()
        else:
            pessoa_fisica.pessoatelefone_set.create(numero=self.cleaned_data["telefone_comercial"], observacao=Avaliador.TELEFONE_COMERCIAL)

        avaliador.endereco_municipio = self.cleaned_data["municipio"]
        avaliador.endereco_logradouro = self.cleaned_data["logradouro"]
        avaliador.endereco_numero = self.cleaned_data["numero"]
        avaliador.endereco_bairro = self.cleaned_data["bairro"]
        avaliador.endereco_complemento = self.cleaned_data["complemento"]
        avaliador.endereco_cep = self.cleaned_data["cep"]

        avaliador.banco = self.cleaned_data["banco"]
        avaliador.numero_agencia = self.cleaned_data["numero_agencia"]
        avaliador.tipo_conta = self.cleaned_data["tipo_conta"]
        avaliador.numero_conta = self.cleaned_data["numero_conta"]
        avaliador.operacao = self.cleaned_data["operacao"]

        pessoa_fisica.save()
        avaliador.save()

        try:
            LdapConf = apps.get_model("ldap_backend", "LdapConf")
            conf = LdapConf.get_active()
            conf.sync_user(pessoa_fisica)
        except Exception:
            pass


class AfastamentosServidoresForm(forms.FormPlus):
    TIPO_AFASTAMENTO_CHOICES = [["Todos", "Todos"]]
    TIPO_AFASTAMENTO_CHOICES += list(map(list, AfastamentoSiape.TIPO_AFASTAMENTO_CHOICES))

    CATEGORIA_CHOICES = [
        ["Todos", "Todos os Servidores"],
        ["docente", "Apenas Docentes"],
        ["tecnico_administrativo", "Apenas Administrativos"],
    ]
    CANCELADO_CHOICES = [["Todos", "Todos"], [False, "Ativos"], [True, "Cancelados"]]

    tipo_afastamento = forms.ChoiceField(choices=TIPO_AFASTAMENTO_CHOICES)
    afastamento = forms.ModelChoiceFieldPlus(
        queryset=AfastamentoSiape.objects,
        label="Afastamento",
        required=False,
        help_text="Caso você não escolha nenhum afastamento específico, a consulta irá considerar todos os tipos de afastamento.",
    )
    uo = forms.ModelChoiceField(
        queryset=UnidadeOrganizacional.objects.suap(),
        label="Campi",
        required=False,
        help_text="Caso você não escolha nenhum campus, a consulta irá considerar todos os campi.",
    )
    categoria = forms.ChoiceField(label="Categoria", choices=CATEGORIA_CHOICES, required=False)
    situacao = forms.ChoiceField(label="Situação de Afastamento", initial=False, choices=CANCELADO_CHOICES, required=False)

    data_inicio = forms.DateFieldPlus(label="Data de Início")
    data_termino = forms.DateFieldPlus(label="Data de Término")

    def clean(self):
        super().clean()
        if not self.errors:
            #
            # periodo adicionado/editado
            #
            periodo_data_inicio = self.cleaned_data["data_inicio"]
            periodo_data_termino = self.cleaned_data["data_termino"]

            #
            # valida o período
            #
            if periodo_data_termino and periodo_data_inicio > periodo_data_termino:
                self._errors["data_inicio"] = self.error_class(["A data de início deve ser menor ou igual à data término."])
                del self.cleaned_data["data_termino"]

        return self.cleaned_data


class ViagensPorCampusForm(forms.FormPlus):
    ano = forms.ModelChoiceField(Ano.objects.all(), label="Ano", required=True)
    mes = forms.ChoiceField(label="Mês", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mes"].choices = [[0, "Todos"]] + Meses.get_choices()


class ImportarArquivoSCDPForm(forms.FormPlus):
    CHOICES = ((0, "Viagens"), (1, "Bilhetes"))
    tipo = forms.ChoiceField(choices=CHOICES, label="Tipo de Arquivo", required=True)
    arquivo = forms.FileFieldPlus(required=True, label="Arquivo", allow_empty_file=False)

    def clean(self):
        if len(self.files) != 1:
            # evitar o não envio de arquivo
            raise ValidationError("Nenhum arquivo selecionado.")
        if self.files["arquivo"].size == 0:
            # evitar o envio de arquivos vazios
            raise ValidationError("O arquivo enviado está vazio.")
        return self.cleaned_data["arquivo"]


class DefinirAreasVinculacaoWizard(FormWizardPlus):
    arvore_setores = forms.ModelChoiceField(
        label="Árvore de Setores", queryset=Setor.objects, widget=TreeWidget(attrs=dict(readonly="readonly")), required=False
    )
    palavra_chave = forms.CharFieldPlus(width=255, label="Palavra-chave")
    setores = forms.ModelMultipleChoiceField(queryset=Setor.objects, widget=forms.CheckboxSelectMultiple())
    areas_vinculacao = forms.ModelMultipleChoiceField(
        queryset=AreaVinculacao.objects, widget=forms.CheckboxSelectMultiple(), label="Áreas de Vinculação"
    )
    recursivamente = forms.BooleanField(label="Definir Recursivamente", required=False)

    steps = (
        [("Filtro", {"fields": ("arvore_setores", "palavra_chave")})],
        [("Seleção dos Setores", {"fields": ("setores", "areas_vinculacao", "recursivamente")})],
    )

    def next_step(self):
        palavra_chave = self.get_entered_data("palavra_chave")
        if "setores" in self.fields:
            if palavra_chave:
                self.fields["setores"].queryset = Setor.objects.filter(sigla__icontains=palavra_chave)

    def processar(self):
        for setor in self.cleaned_data["setores"]:
            for area_vinculacao in self.cleaned_data["areas_vinculacao"]:
                setor.areas_vinculacao.add(area_vinculacao)
            if self.cleaned_data["recursivamente"]:
                setor.salvar_areas_vinculacao_recursivamente(self.cleaned_data["areas_vinculacao"])
            setor.save()


class AreaVinculacaoForm(forms.ModelFormPlus):
    ordem = forms.ChoiceField(choices=[])

    class Meta:
        model = AreaVinculacao
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ordem_choices = []
        qtd = AreaVinculacao.objects.count()

        for ordem in range(1, qtd + 2):
            ordem_choices.append([ordem, ordem])

        self.fields["ordem"].choices = ordem_choices

    def save(self, *args, **kwargs):
        if self.instance.ordem < AreaVinculacao.objects.count():
            qs = AreaVinculacao.objects.exclude(pk=self.instance.pk).filter(ordem__gte=self.instance.ordem).order_by("ordem")
            range_ordem = list(range(self.instance.ordem + 1, AreaVinculacao.objects.count() + 1))
        else:
            qs = AreaVinculacao.objects.exclude(pk=self.instance.pk).filter(ordem__lte=self.instance.ordem).order_by("ordem")
            range_ordem = list(range(1, self.instance.ordem + 1))

        for index, obj in enumerate(qs):
            obj.ordem = range_ordem[index]
            obj.save()

        return super().save(*args, **kwargs)


class ServidoresParaCapacitacaoPorSetorForm(forms.FormPlus):
    setor = forms.ModelChoiceField(
        label="Setor SUAP", queryset=Setor.objects.all(), widget=TreeWidget(), required=True, help_text="Selecione um setor SUAP"
    )

    setores_filhos = forms.BooleanField(required=False, label="Incluir setores filhos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuario_logado = self.request.user
        servidor = usuario_logado.get_profile().funcionario.sub_instance()
        raiz = None
        if usuario_logado.is_superuser:
            raiz = Setor.raiz()
        elif servidor.setor:
            raiz = servidor.setor

        self.fields["setor"].widget.root_nodes = [raiz]


class InstituicaoForm(forms.ModelFormPlus):
    unidade_gestora = forms.IntegerField(label="Unidade Gestora", required=False)
    uasg = forms.IntegerField(label="UASG", required=False)

    class Meta:
        model = Instituicao
        fields = ("nome", "unidade_gestora", "uasg", "ativo")


###############
# CH Reduzida #
###############


class ProcessoCargaHorariaReduzidaRHForm(forms.ModelFormPlus):
    # Form do RH para cadastrar CH reduzida
    PROCESSO_ELETRONICO = "eletronico"
    PROCESSO_FISICO = "fisico"
    TIPO_PROTOCOLO_CHOICE = ((PROCESSO_ELETRONICO, "Protocolo eletrônico"), (PROCESSO_FISICO, "Protocolo físico"))

    servidor = forms.ModelChoiceFieldPlus(
        queryset=Servidor.objects, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS), required=True
    )

    if "processo_eletronico" in settings.INSTALLED_APPS:
        from processo_eletronico.models import Processo as ProcessoEletronico

        protocolo_eletronico = forms.ModelChoiceFieldPlus(
            queryset=ProcessoEletronico.objects,
            widget=AutocompleteWidget(search_fields=ProcessoEletronico.SEARCH_FIELDS),
            required=False,
            label="Protocolo eletrônico",
        )

    if "protocolo" in settings.INSTALLED_APPS:
        from protocolo.models import Processo as ProcessoFisico

        protocolo_fisico = forms.ModelChoiceFieldPlus(
            queryset=ProcessoFisico.objects,
            widget=AutocompleteWidget(search_fields=ProcessoFisico.SEARCH_FIELDS),
            required=False,
            label="Protocolo físico",
        )

    tipo_protocolo = forms.ChoiceField(widget=forms.RadioSelect(), choices=TIPO_PROTOCOLO_CHOICE, label="Tipo de protocolo:")

    class Meta:
        model = CargaHorariaReduzida
        fields = ("servidor", "data_inicio", "data_termino", "tipo")
        if "protocolo" in settings.INSTALLED_APPS:
            fields += ("protocolo_fisico",)
        if "processo_eletronico" in settings.INSTALLED_APPS:
            fields += ("protocolo_eletronico",)
        if "protocolo" in settings.INSTALLED_APPS or "processo_eletronico" in settings.INSTALLED_APPS:
            fields += ("tipo_protocolo",)

    class Media:
        js = ("/static/rh/js/TipoProcoloCHReduzida.js",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuario_logado_eh_rh_sistemico = in_group(self.request.user, "Coordenador de Gestão de Pessoas Sistêmico")
        servidor_logado = self.request.user.get_relacionamento()
        uo_id = servidor_logado.setor.uo_id
        if not (usuario_logado_eh_rh_sistemico or self.request.user.is_superuser):
            self.fields["servidor"].queryset = Servidor.objects.ativos().filter(setor__uo_id=uo_id)

        if self.instance:
            if "protocolo_fisico" in self.fields:
                from protocolo.models import Processo as ProcessoFisico

                if isinstance(self.instance.protocolo_content_object, ProcessoFisico):
                    self.fields["tipo_protocolo"].initial = self.PROCESSO_FISICO
                    self.fields["protocolo_fisico"].initial = self.instance.protocolo_content_id

            if "protocolo_eletronico" in self.fields:
                from processo_eletronico.models import Processo as ProcessoEletronico

                if isinstance(self.instance.protocolo_content_object, ProcessoEletronico):
                    self.fields["tipo_protocolo"].initial = self.PROCESSO_ELETRONICO
                    self.fields["protocolo_eletronico"].initial = self.instance.protocolo_content_id

    def clean(self):
        clean = super().clean()
        if clean.get("data_inicio") and clean.get("data_termino"):
            if clean.get("tipo") == CargaHorariaReduzida.TIPO_AFASTAMENTO_PARCIAL:
                if clean.get("data_inicio") >= clean.get("data_termino"):
                    self.add_error("data_inicio", "Data início deve ser menor que data término")
                elif clean.get("data_termino") < clean.get("data_inicio") + timedelta(days=30):
                    self.add_error(
                        "data_termino",
                        "A data mínima do término do afastamento, "
                        "deve ser {}".format((clean.get("data_inicio") + timedelta(days=31)).strftime("%d/%m/%Y")),
                    )
        if clean.get("servidor"):
            servidor_solicitante = clean.get("servidor")
            if not servidor_solicitante.setor:
                self.add_error("servidor", "Servidor não tem setor.")

        if self.is_tipo_protocolo_eletronico() and not self.cleaned_data.get("protocolo_eletronico"):
            self.add_error("protocolo_eletronico", "É obrigatório informar um protocolo. ")

        if self.is_tipo_protocolo_fisico() and not self.cleaned_data.get("protocolo_fisico"):
            self.add_error("protocolo_fisico", "É obrigatório informar um protocolo. ")
        return clean

    def save(self, commit=True):
        if not self.instance.id:
            if self.instance.tipo == CargaHorariaReduzida.TIPO_AFASTAMENTO_PARCIAL:
                self.instance.status = CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_RH
            else:
                self.instance.status = CargaHorariaReduzida.STATUS_AGUARDANDO_CADASTRAR_HORARIO

            self.instance.ano = datetime.date.today().year

        if self.is_tipo_protocolo_eletronico() and self.cleaned_data["protocolo_eletronico"]:
            self.instance.protocolo_content_object = self.cleaned_data["protocolo_eletronico"]
        elif self.is_tipo_protocolo_fisico() and self.cleaned_data["protocolo_fisico"]:
            self.instance.protocolo_content_object = self.cleaned_data["protocolo_fisico"]
        return super().save(commit)

    def is_tipo_protocolo_eletronico(self):
        return self.cleaned_data.get("tipo_protocolo") == "eletronico"

    def is_tipo_protocolo_fisico(self):
        return self.cleaned_data.get("tipo_protocolo") == "fisico"


class DocumentacaoExigidaUploadForm(forms.FormPlus):
    arquivo = forms.AjaxFileUploadField("/rh/afastamento_pacial_upload/", "onCompleteUpload")
    SUBMIT_LABEL = "Salvar"

    def __init__(self, *args, **kwargs):
        processo = kwargs.pop("processo")
        super().__init__(*args, **kwargs)
        self.fields["arquivo"].widget.request = self.request
        self.fields["arquivo"].widget.params["processo"] = processo.id


class SalvarProcessoAfastamentoForm(forms.FormPlus):
    data_inicial = forms.DateFieldPlus()
    data_final = forms.DateFieldPlus()
    nova_jornada = forms.ChoiceField(label="Jornada pretendida", choices=())
    processo = None

    def __init__(self, *args, **kwargs):
        self.processo = kwargs.pop("processo")
        # self.processo = self.instance
        super().__init__(*args, **kwargs)

        self.fields["nova_jornada"].choices = self.processo.get_carga_horaria_disponivel_choice()

        # inicializando os campos
        self.fields["data_inicial"].initial = self.processo.data_inicio
        self.fields["data_final"].initial = self.processo.data_termino

        if self.processo.nova_jornada:
            self.fields["nova_jornada"].initial = self.processo.nova_jornada.split("HORAS SEMANAIS")[0].strip()

        if (
            self.processo.status == CargaHorariaReduzida.STATUS_NOVOS_DOCUMENTOS_SOLICITADOS
            or self.processo.status == CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_CHEFE
        ):
            self.fields["data_inicial"].widget.attrs["disabled"] = True
            self.fields["data_inicial"].widget.attrs["readonly"] = True

            self.fields["data_final"].widget.attrs["disabled"] = True
            self.fields["data_final"].widget.attrs["readonly"] = True

            self.fields["nova_jornada"].widget.attrs["disabled"] = True
            self.fields["nova_jornada"].widget.attrs["readonly"] = True

    def clean(self):
        clean = super().clean()
        if not self.processo.documentos.all().exists():
            raise Exception("Adicone pelo menos um arquivo.")
        if clean.get("data_inicial") and clean.get("data_final"):
            if clean.get("data_inicial") >= clean.get("data_final"):
                self.add_error("data_inicial", "Data início deve ser menor que data término")
            elif clean.get("data_inicial") < datetime.date.today():
                self.add_error("data_inicial", "Não poderá haver solicitação de afastamento com datas passadas")
            elif clean.get("data_inicial") < datetime.date.today() + timedelta(days=30):
                self.add_error(
                    "data_inicial",
                    "A data do início do afastamento, "
                    "deve ser no mínimo {}".format(datetime.date.today() + timedelta(days=30)).strftime("%d/%m/%Y"),
                )
            elif clean.get("data_final") < clean.get("data_inicial") + timedelta(days=30):
                self.add_error(
                    "data_final",
                    "A data mínima do término do afastamento, "
                    "deve ser {}".format(clean.get("data_inicial") + timedelta(days=31)).strftime("%d/%m/%Y"),
                )
        return clean

    def save(self):
        data_inicio = self.cleaned_data.get("data_inicial")
        data_final = self.cleaned_data.get("data_final")
        nova_jornada = self.cleaned_data["nova_jornada"]

        self.processo.data_inicio = data_inicio
        self.processo.data_termino = data_final
        self.processo.nova_jornada = "{} HORAS SEMANAIS ".format(nova_jornada)
        self.processo.save()


class AdicionarHorarioAfastamentoForm(forms.FormPlus):
    SUBMIT_LABEL = "Salvar"

    data_inicial_horario = forms.DateFieldPlus(label="Data inicial")
    data_fim_horario = forms.DateFieldPlus(label="Data final")
    nova_jornada = forms.ChoiceField(label="Jornada pretendida", choices=())
    seg = forms.ChoiceField(label="SEG", choices=())
    ter = forms.ChoiceField(label="TER", choices=())
    qua = forms.ChoiceField(label="QUA", choices=())
    qui = forms.ChoiceField(label="QUI", choices=())
    sex = forms.ChoiceField(label="SEX", choices=())
    processo = None

    fieldsets = ((None, {"fields": ("data_inicial_horario", "data_fim_horario", "nova_jornada", ("seg", "ter", "qua", "qui", "sex"))}),)

    class Media:
        js = ["/static/rh/js/AdicionarHorarioAfastamentoForm.js"]

    def __init__(self, *args, **kwargs):
        self.processo = kwargs.pop("processo")
        super().__init__(*args, **kwargs)
        # inicializando os campos
        self.fields["nova_jornada"].choices = self.processo.get_carga_horaria_disponivel_choice()
        self.fields["seg"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()
        self.fields["ter"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()
        self.fields["qua"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()
        self.fields["qui"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()
        self.fields["sex"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()

        # recuperando dados ja gravados
        self.fields["data_inicial_horario"].initial = self.processo.data_inicio
        self.fields["data_fim_horario"].initial = self.processo.data_termino

        nova_jornada = self.processo.nova_jornada if self.processo.nova_jornada else self.processo.servidor.jornada_trabalho.nome
        if nova_jornada:
            if nova_jornada == 'DEDICACAO EXCLUSIVA':
                jornada_semanal = '40'
            else:
                jornada_semanal = nova_jornada.split("HORAS SEMANAIS")[0].strip()
            self.fields["nova_jornada"].initial = jornada_semanal
            ch_diaria = int(int(jornada_semanal) / 5)
            self.fields["seg"].initial = ch_diaria
            self.fields["ter"].initial = ch_diaria
            self.fields["qua"].initial = ch_diaria
            self.fields["qui"].initial = ch_diaria
            self.fields["sex"].initial = ch_diaria

        if (
            self.processo.status == CargaHorariaReduzida.STATUS_NOVOS_DOCUMENTOS_SOLICITADOS
            or self.processo.status == CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_CHEFE
        ):
            self.fields["data_inicial"].widget.attrs["disabled"] = True
            self.fields["data_inicial"].widget.attrs["readonly"] = True

            self.fields["data_final"].widget.attrs["disabled"] = True
            self.fields["data_final"].widget.attrs["readonly"] = True

            self.fields["nova_jornada"].widget.attrs["disabled"] = True
            self.fields["nova_jornada"].widget.attrs["readonly"] = True

    def clean(self):
        clean = super().clean()
        soma = (
            int(self.cleaned_data.get("seg"))
            + int(self.cleaned_data.get("ter"))
            + int(self.cleaned_data.get("qua"))
            + int(self.cleaned_data.get("qui"))
            + int(self.cleaned_data.get("sex"))
        )
        if not soma == int(self.cleaned_data["nova_jornada"]):
            self.add_error("nova_jornada", "A carga horária escolhida não corresponde à soma semanal, " "corrija e tente novamente.")
        return clean

    def save(self):
        data_inicio = self.cleaned_data.get("data_inicial_horario")
        data_final = self.cleaned_data.get("data_fim_horario")
        seg = self.cleaned_data.get("seg")
        ter = self.cleaned_data.get("ter")
        qua = self.cleaned_data.get("qua")
        qui = self.cleaned_data.get("qui")
        sex = self.cleaned_data.get("sex")
        nova_jornada = self.cleaned_data["nova_jornada"]

        horario = HorarioSemanal()
        horario.data_inicio = data_inicio
        horario.data_fim = data_final
        horario.seg = seg
        horario.ter = ter
        horario.qua = qua
        horario.qui = qui
        horario.sex = sex
        horario.processo_reducao_ch = self.processo
        horario.jornada_semanal = nova_jornada
        horario.save()

        if self.processo.status == CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH:
            self.processo.status = CargaHorariaReduzida.STATUS_ALTERANDO_HORARIO
            self.processo.save()


class EditarHorarioAfastamentoForm(forms.FormPlus):
    SUBMIT_LABEL = "Salvar"

    data_inicial_horario = forms.DateFieldPlus(label="Data inicial")
    data_fim_horario = forms.DateFieldPlus(label="Data final")
    nova_jornada = forms.ChoiceField(label="Jornada pretendida", choices=())
    seg = forms.ChoiceField(label="SEG", choices=())
    ter = forms.ChoiceField(label="TER", choices=())
    qua = forms.ChoiceField(label="QUA", choices=())
    qui = forms.ChoiceField(label="QUI", choices=())
    sex = forms.ChoiceField(label="SEX", choices=())
    horario = None

    fieldsets = ((None, {"fields": ("data_inicial_horario", "data_fim_horario", "nova_jornada", ("seg", "ter", "qua", "qui", "sex"))}),)

    class Media:
        js = ["/static/rh/js/AdicionarHorarioAfastamentoForm.js"]

    def __init__(self, *args, **kwargs):
        self.horario = kwargs.pop("horario")
        self.processo = CargaHorariaReduzida.objects.filter(id=self.horario.processo_reducao_ch.id)[0]
        super().__init__(*args, **kwargs)

        # inicializando os campos
        self.fields["nova_jornada"].choices = self.processo.get_carga_horaria_disponivel_choice()
        self.fields["seg"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()
        self.fields["ter"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()
        self.fields["qua"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()
        self.fields["qui"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()
        self.fields["sex"].choices = self.processo.get_carga_horaria_disponivel_diaria_choice()

        # recuperando dados ja gravados
        self.fields["data_inicial_horario"].initial = self.horario.data_inicio
        self.fields["data_fim_horario"].initial = self.horario.data_fim
        self.fields["nova_jornada"].initial = self.horario.jornada_semanal
        self.fields["seg"].initial = self.horario.seg
        self.fields["ter"].initial = self.horario.ter
        self.fields["qua"].initial = self.horario.qua
        self.fields["qui"].initial = self.horario.qui
        self.fields["sex"].initial = self.horario.sex

    def clean(self):
        clean = super().clean()
        soma = (
            int(self.cleaned_data.get("seg"))
            + int(self.cleaned_data.get("ter"))
            + int(self.cleaned_data.get("qua"))
            + int(self.cleaned_data.get("qui"))
            + int(self.cleaned_data.get("sex"))
        )
        if not soma == int(self.cleaned_data["nova_jornada"]):
            self.add_error("nova_jornada", "A carga horária escolhida não corresponde à soma semanal, " "corrija e tente novamente")
        return clean

    def save(self):
        data_inicio = self.cleaned_data.get("data_inicial_horario")
        data_final = self.cleaned_data.get("data_fim_horario")
        seg = self.cleaned_data.get("seg")
        ter = self.cleaned_data.get("ter")
        qua = self.cleaned_data.get("qua")
        qui = self.cleaned_data.get("qui")
        sex = self.cleaned_data.get("sex")
        nova_jornada = self.cleaned_data["nova_jornada"]

        horario = self.horario
        horario.data_inicio = data_inicio
        horario.data_fim = data_final
        horario.seg = seg
        horario.ter = ter
        horario.qua = qua
        horario.qui = qui
        horario.sex = sex
        horario.processo_reducao_ch = self.processo
        horario.jornada_semanal = nova_jornada
        horario.save()

        if self.processo.status == CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH:
            self.processo.status = CargaHorariaReduzida.STATUS_ALTERANDO_HORARIO
            self.processo.save()


class IndeferirProcessoAfastamentoParcialRHForm(forms.ModelFormPlus):
    class Meta:
        model = CargaHorariaReduzida
        fields = ("motivo_indeferimento_rh",)
        widgets = {"motivo_indeferimento_rh": forms.Textarea}

    def save(self, commit=True):
        processo = self.instance
        processo.status = CargaHorariaReduzida.STATUS_INDEFERIDO_PELO_RH
        processo.servidor_rh_validador = self.request.user.get_profile().sub_instance()
        processo.motivo_indeferimento_rh = self.cleaned_data.get("motivo_indeferimento_rh")
        return super().save(commit)


class AniversarianteForm(forms.FormPlus):
    uo = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.uo(), label="Campus", required=False)

    METHOD = "GET"

    class Meta:
        fields = ("uo",)


class PosicionamentoPCAForm(forms.ModelForm):
    pca = forms.ModelChoiceField(queryset=PCA.objects, widget=AutocompleteWidget(search_fields=PCA.SEARCH_FIELDS), label="PCA")

    class Meta:
        model = PCA
        exclude = ()


class CronogramaFolhaForm(forms.ModelFormPlus):
    mes = forms.ChoiceField(choices=Meses.get_choices(), required=True, label="Mês")
    ano = forms.ModelChoiceFieldPlus(Ano.objects, required=True, widget=forms.Select(), label="Ano")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ano"].queryset = Ano.objects.all()

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean(*args, **kwargs)

        data = datetime.date.min

        data_abertura_atualizacao_folha = self.cleaned_data.get("data_abertura_atualizacao_folha", data)
        data_fechamento_processamento_folha = self.cleaned_data.get("data_fechamento_processamento_folha", data)
        data_consulta_previa_folha = self.cleaned_data.get("data_consulta_previa_folha", data)
        data_abertura_proxima_folha = self.cleaned_data.get("data_abertura_proxima_folha", data)

        if data_abertura_atualizacao_folha > data_fechamento_processamento_folha:
            self.add_error(
                "data_abertura_atualizacao_folha",
                "A data da abertura para atualização da folha deve ser menor que a data de fechamento para o processamento da folha.",
            )
        if data_abertura_atualizacao_folha > data_consulta_previa_folha:
            self.add_error(
                "data_abertura_atualizacao_folha",
                "A data da abertura para atualização da folha deve ser menor que a data de consulta da prévia.",
            )
        if data_abertura_atualizacao_folha > data_abertura_proxima_folha:
            self.add_error(
                "data_abertura_atualizacao_folha",
                "A data da abertura para atualização da folha deve ser menor que a data de abertura da próxima folha.",
            )

        if data_fechamento_processamento_folha < data_abertura_atualizacao_folha:
            self.add_error(
                "data_fechamento_processamento_folha",
                "A data de fechamento para o processamento da folha não pode ser menor que a data de abertura para atualização da folha.",
            )
        if data_fechamento_processamento_folha > data_consulta_previa_folha:
            self.add_error(
                "data_fechamento_processamento_folha",
                "A data de fechamento para o processamento da folha não pode ser maior que a data de consulta da prévia.",
            )
        if data_fechamento_processamento_folha > data_abertura_proxima_folha:
            self.add_error(
                "data_fechamento_processamento_folha",
                "A data de fechamento para o processamento da folha não pode ser maior que a data de abertura da próxima folha.",
            )

        if data_consulta_previa_folha < data_abertura_atualizacao_folha:
            self.add_error(
                "data_consulta_previa_folha",
                "A data de consulta da prévia não pode ser menor que a data de abertura para atualização da folha.",
            )
        if data_consulta_previa_folha < data_fechamento_processamento_folha:
            self.add_error(
                "data_consulta_previa_folha",
                "A data de consulta da prévia não pode ser menor que a data de fechamento para processamento da folha.",
            )
        if data_consulta_previa_folha > data_abertura_proxima_folha:
            self.add_error(
                "data_consulta_previa_folha", "A data de consulta da prévia não pode ser maior que a data de abertura da próxima folha."
            )

        if data_abertura_proxima_folha < data_abertura_atualizacao_folha:
            self.add_error(
                "data_abertura_proxima_folha",
                "A data de abertura da próxima folha não pode ser menor que a data de abertura para atualização da folha.",
            )
        if data_abertura_proxima_folha < data_fechamento_processamento_folha:
            self.add_error(
                "data_abertura_proxima_folha",
                "A data de abertura da próxima folha não pode ser menor que a data de fechamento para processamento da folha.",
            )
        if data_abertura_proxima_folha < data_consulta_previa_folha:
            self.add_error(
                "data_abertura_proxima_folha",
                "A data de abertura da próxima folha não pode ser menor que a data de consulta da próxima folha.",
            )

        return cleaned_data


class AcaoSaudeForm(forms.ModelFormPlus):
    DOMINGO = 0
    SEGUNDA = 1
    TERCA = 2
    QUARTA = 3
    QUINTA = 4
    SEXTA = 5
    SABADO = 6
    DIAS_RESUMIDO_CHOICES = (
        (SEGUNDA, "Segunda"),
        (TERCA, "Terça"),
        (QUARTA, "Quarta"),
        (QUINTA, "Quinta"),
        (SEXTA, "Sexta"),
        (SABADO, "Sábado"),
        (DOMINGO, "Domingo"),
    )

    dias_semanas = forms.MultipleChoiceField(
        choices=DIAS_RESUMIDO_CHOICES, widget=forms.CheckboxSelectMultiple, required=True, label="Dias da Semana"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AdicionarHorarioAcaoSaudeForm(forms.ModelFormPlus):
    class Meta:
        model = AgendaAtendimentoHorario
        exclude = ()

    def __init__(self, *args, **kwrags):
        acao_saude = kwrags.pop("acao_saude", None)
        super().__init__(*args, **kwrags)
        if acao_saude:
            self.fields["acao_saude"].initial = acao_saude.id
            self.fields["acao_saude"].widget = forms.HiddenInput()


class HorarioAgendamentoForm(forms.ModelFormPlus):
    class Meta:
        model = HorarioAgendado
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AgendaAtendimentoInLineFormSet(BaseInlineFormSet):
    def clean(self):
        return self.cleaned_data


class AgendaAtendimentoHorarioForm(forms.ModelFormPlus):
    hora_inicio = forms.TimeFieldPlus()
    hora_fim = forms.TimeFieldPlus()
    quantidade_vaga = forms.IntegerFieldPlus()
    profissional = forms.ModelChoiceFieldPlus(
        queryset=Servidor.objects.all(),
        widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS),
        required=True,
        label="Profissionais",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = AgendaAtendimentoHorario
        exclude = ()


class AgendarAtendimentoForm(forms.ModelFormPlus):
    data_consulta = forms.DateFieldPlus(label="Data da Consulta")
    solicitante = forms.ModelChoiceFieldPlus(
        queryset=Funcionario.objects,
        widget=AutocompleteWidget(
            search_fields=Funcionario.SEARCH_FIELDS, help_text="Você pode selecionar outro servidor ou prestador de serviço."
        ),
    )
    horario = forms.ModelChoiceFieldPlus(queryset=AgendaAtendimentoHorario.objects, widget=forms.Select())

    class Meta:
        model = HorarioAgendado
        exclude = ()

    fieldsets = [("", {"fields": ["horario", "solicitante", "data_consulta", "retorno"]})]

    class Media:
        js = ("/static/rh/js/datepicker-week-restriction.js",)

    def __init__(self, *args, **kwargs):
        horario = kwargs.pop("horario", None)
        acao_saude = kwargs.pop("acao_saude", None)
        super().__init__(*args, **kwargs)

        usuario_logado = self.request.user

        if not acao_saude and horario:
            acao_saude = horario.acao_saude

        if acao_saude:
            # verificando datas bloqueadas
            qs_datas = DataConsultaBloqueada.objects.filter(acao_saude=acao_saude)
            lista_datas = []
            for data in qs_datas:
                lista_datas.append(data.data_consulta_bloqueada.strftime("%Y-%m-%d"))

            self.fields["horario"].queryset = acao_saude.agendaatendimentohorario_set.all()
            self.fields["data_consulta"].widget.attrs.update(
                {"weeks": ",".join(eval(acao_saude.dias_semanas)), "dates": lista_datas}
            )

        if self.request.GET.get("v"):
            self.fields["horario"].initial = int(self.request.GET.get("v"))

        if horario:
            self.fields["horario"].initial = horario.id
            self.fields["horario"].widget = forms.HiddenInput()

        if not usuario_logado.has_perm("rh.add_acaosaude"):
            self.fields["solicitante"].initial = usuario_logado.get_profile().sub_instance().id
            self.fields["solicitante"].widget = forms.HiddenInput()

    def clean(self):
        super().clean()
        horario_agenda = self.cleaned_data.get("horario")
        solicitante = self.cleaned_data.get("solicitante")
        data_consulta = self.cleaned_data.get("data_consulta")
        if horario_agenda:
            if not horario_agenda.tem_vaga_disponivel(data_consulta):
                raise ValidationError("Não há vagas para o horário e dia selecionados.")
            if horario_agenda.esta_agendado_em_algum_horario(solicitante):
                raise ValidationError("Você já está agendado nesta ação de saúde.")

            # verificando datas bloqueadas
            for i in horario_agenda.acao_saude.dataconsultabloqueada_set.all():
                if data_consulta and data_consulta == i.data_consulta_bloqueada:
                    raise ValidationError(f"A data {i.data_consulta_bloqueada.strftime('%d-%m-%Y')} está bloqueada para consultas.")

            # verificando dia de semana bloqueados
            if data_consulta:
                dia_semana = 0 if data_consulta.isoweekday() == 7 else data_consulta.isoweekday()
                if str(dia_semana) not in eval(horario_agenda.acao_saude.dias_semanas):
                    weekday = ["no domingo", "na segunda-feira", "na terça-feira", "na quarta-feira", "na quinta-feira", "na sexta-feira", "no sábado"]
                    raise ValidationError(f"Não é permitido para este evento agendamento {weekday[data_consulta.weekday()]} ")
        else:
            raise ValidationError("Nenhum horário foi selecionado.")


class DataConsultaBloqueadaForm(forms.ModelFormPlus):
    acao_saude = forms.ModelChoiceFieldPlus(
        AcaoSaude.ativas, label="Ação de Saúde", widget=AutocompleteWidget(search_fields=AcaoSaude.SEARCH_FIELDS)
    )

    class Meta:
        model = DataConsultaBloqueada
        exclude = ("houve_remarcacao",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["acao_saude"].queryset = AcaoSaude.ativas.all()


class PCAForm(forms.ModelFormPlus):
    servidor = forms.ModelChoiceFieldPlus(
        Servidor.objects, label="Servidor", widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS)
    )
    servidor_matricula_crh = forms.CharFieldPlus(
        label="Matrícula CRH do Servidor",
        help_text="Preencha caso cadastro do servidor no SUAP não tenha ainda a matricula CRH",
        required=False,
    )
    forma_entrada_pca = forms.ModelChoiceFieldPlus(
        FormaProvimentoVacancia.objects,
        label="Forma de Entrada",
        widget=AutocompleteWidget(search_fields=FormaProvimentoVacancia.SEARCH_FIELDS),
    )
    cargo_pca = forms.ModelChoiceFieldPlus(CargoEmprego.objects, label="Cargo Emprego")
    servidor_vaga_pca = forms.CharFieldPlus(label="Código de Vaga")
    data_entrada_pca = forms.DateFieldPlus(label="Data de Entrada")

    forma_vacancia_pca = forms.ModelChoiceFieldPlus(
        FormaProvimentoVacancia.objects,
        label="Forma de Vacância",
        widget=AutocompleteWidget(search_fields=FormaProvimentoVacancia.SEARCH_FIELDS),
    )
    data_vacancia_pca = forms.DateFieldPlus(label="Data de Vacância", required=False)

    class Meta:
        model = PCA
        fields = (
            "servidor",
            "servidor_matricula_crh",
            "cargo_pca",
            "codigo_pca",
            "servidor_vaga_pca",
            "data_entrada_pca",
            "forma_entrada_pca",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["forma_entrada_pca"].queryset = FormaProvimentoVacancia.objects.exclude(
            descricao="Atualize o cadastro de {}".format(self.Meta.model._meta.verbose_name_plural)
        )

    def save(self, *args, **kwargs):
        self.instance.servidor_matricula_crh = self.instance.servidor_matricula_crh
        if not self.instance.data_vacancia_pca:
            # Deixamos essa data preenchida para manter padronização com o SIAPE
            self.instance.data_vacancia_pca = datetime.date(2500, 12, 31)
        return super().save(*args, **kwargs)


class JornadaTrabalhoPCAForm(forms.ModelFormPlus):
    pca = forms.ModelChoiceField(queryset=PCA.objects, widget=AutocompleteWidget(search_fields=PCA.SEARCH_FIELDS), label="PCA")

    class Meta:
        model = JornadaTrabalhoPCA
        fields = ("pca", "qtde_jornada_trabalho_pca", "data_inicio_jornada_trabalho_pca", "data_fim_jornada_trabalho_pca")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_inicio_jornada_trabalho_pca"].label = "Data Início"
        self.fields["data_fim_jornada_trabalho_pca"].label = "Data Fím"
        self.fields["data_fim_jornada_trabalho_pca"].required = False
        self.fields["qtde_jornada_trabalho_pca"].label = "Qtd de Horas"
        self.fields["qtde_jornada_trabalho_pca"].help_text = "Exemplos de Jornada: 20, 30, 40 ou Dedicação Exclusiva"

    def save(self, *args, **kwargs):
        if not self.instance.data_fim_jornada_trabalho_pca:
            # Deixamos essa data preenchida para manter padronização com o SIAPE
            self.instance.data_fim_jornada_trabalho_pca = datetime.date(2500, 12, 31)
        return super().save(*args, **kwargs)


class RegimeJuridicoPCAForm(forms.ModelFormPlus):
    pca = forms.ModelChoiceField(queryset=PCA.objects, widget=AutocompleteWidget(search_fields=PCA.SEARCH_FIELDS), label="PCA")
    regime_juridico = forms.ModelChoiceField(
        queryset=RegimeJuridico.objects, widget=AutocompleteWidget(search_fields=RegimeJuridico.SEARCH_FIELDS), label="Regime Jurídico"
    )

    class Meta:
        model = RegimeJuridicoPCA
        fields = ("pca", "regime_juridico", "data_inicio_regime_juridico_pca", "data_fim_regime_juridico_pca")


class RelatorioAfastamentosCriticosForm(forms.FormPlus):
    METHOD = "GET"
    CATEGORIA_CHOICES = [
        ["Todos", "Todos os Servidores"],
        ["docente", "Apenas Docentes"],
        ["tecnico_administrativo", "Apenas Administrativos"],
    ]

    uo = forms.ModelChoiceField(
        queryset=UnidadeOrganizacional.objects.suap(),
        label="Campi",
        required=False,
        help_text="Caso você não escolha nenhum campus, a consulta irá considerar todos os campi.",
    )
    categoria = forms.ChoiceField(choices=CATEGORIA_CHOICES, required=False)


class WebserviceSIAPEForm(forms.FormPlus):
    """
    getPensionista(cpfPensionista, cpf, siglaSistema, nomeSistema, senha)
    consultaDadosRepresentanteLegal(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosFuncionais(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosDependentes(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    obterVersao(siglaSistema)
    consultaDadosPA(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    listaUorgs(siglaSistema, nomeSistema, senha, cpf, codOrgao, codUorg)
    consultaDadosEscolares(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosPessoais(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosAfastamento(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosEnderecoResidencial(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaTotalizadorVagasOrgao(siglaSistema, nomeSistema, senha, cpf, codOrgao)
    consultaPensaoRecebida(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosFinanceiros(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    listaServidores(siglaSistema, nomeSistema, senha, cpf, codOrgao, codUorg)
    consultaDadosDocumentacao(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosBancarios(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaPensoesInstituidas(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosSICAJ(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    verificaVinculo(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    dadosUorg(siglaSistema, nomeSistema, senha, cpf, codOrgao, codUorg)
    consultaDadosUorg(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    consultaDadosCurriculo(siglaSistema, nomeSistema, senha, cpf, codOrgao, parmExistPag, parmTipoVinculo)
    """

    cpf = forms.CharFieldPlus(label="CPF", required=False)
    cpf_pensionista = forms.CharFieldPlus(label="CPF Pensionista", required=False)
    consulta = forms.ChoiceField(label="Consulta", choices=())
    codUorg = forms.ChoiceField(label="Setor", choices=(), required=False)
    parmExistPag = forms.ChoiceField(label="ParmExistPag", choices=(["a", "a"], ["b", "b"]))
    parmTipoVinculo = forms.ChoiceField(label="ParmTipoVinculo", choices=(["a", "a"], ["b", "b"], ["c", "c"]))

    SUBMIT_LABEL = "Consultar"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ws = ImportadorWs()
        self.fields["consulta"].choices = ws._get_services_siape()
        setores = []
        for setor in Setor.siape.filter(uo__sigla__isnull=False).values_list("codigo", "sigla"):
            setores.append([int(setor[0]), setor[1]])
        self.fields["codUorg"].choices = setores

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        return mask_numbers(cpf)


class ImportarServidorWSForm(forms.FormPlus):
    cpf = forms.BrCpfField(label="CPF", required=False)
    apenas_servidores_em_exercicio = forms.BooleanField(
        label="Pesquisar somente servidor em exercício na instituicão?",
        help_text="Ao marcar esta opção, serão desconsiderados aposentados, pensionistas, cedidos ou em exercício externo ao órgão de lotação.",
        required=False,
    )
    SUBMIT_LABEL = "Consultar"

    def clean_cpf(self):
        cpf = self.cleaned_data.get("cpf")
        return mask_numbers(cpf)


class DocentesPorDisciplinaFiltroForm(forms.Form):
    filtro_disciplinas_cadastradas = (
        (0, "Todos"),
        (1, "Docentes sem disciplina de ingresso cadastrada"),
        (2, "Docentes com disciplina de ingresso cadastrada"),
    )
    SUBMIT_LABEL = "Filtrar"
    METHOD = "GET"
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap().all(), label="Campus", required=False)
    disciplinas = forms.ChoiceField(label="Filtro de docentes por disciplina", choices=filtro_disciplinas_cadastradas, required=False)

    fieldsets = (("", {"fields": (("campus", "disciplinas"),)}),)


class BancoForm(forms.ModelFormPlus):
    class Meta:
        model = Banco
        fields = ("codigo", "sigla", "nome", "excluido")

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        erro = False
        if self.cleaned_data.get("codigo"):
            if not self.instance.pk and Banco.objects.filter(codigo=self.cleaned_data.get("codigo")).exists():
                erro = True
            elif self.instance.pk and Banco.objects.exclude(id=self.instance.pk).filter(codigo=self.cleaned_data.get("codigo")).exists():
                erro = True
        if erro:
            self.add_error("codigo", "Um banco com o código informado já foi cadastrado.")
        return cleaned_data


def SetorRaizFormFactory(request):
    setor_usuario = request.user.get_relacionamento().setor

    class SetorRaizForm(forms.FormPlus):
        raiz = forms.ModelChoiceFieldPlus(
            queryset=Setor.objects, widget=AutocompleteWidget(search_fields=Setor.SEARCH_FIELDS), initial=setor_usuario, label="Setor"
        )

    return SetorRaizForm


class EditarServidorCargoEmpregoAreaForm(forms.ModelFormPlus):
    class Meta:
        model = Servidor
        fields = ("cargo_emprego_area",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["cargo_emprego_area"].queryset = self.instance.cargo_emprego.cargoempregoarea_set.all()


class ServidoresPorAreaFiltroForm(forms.Form):
    SUBMIT_LABEL = "Filtrar"
    METHOD = "GET"
    filtro_cargo_area_cadastradas = ((0, "Todos"), (1, "Com área cadastrada"), (2, "Sem área cadastrada"))

    com_area_cadastrada = forms.ChoiceField(label="Escopo dos Servidores", choices=filtro_cargo_area_cadastradas, required=False)
    campus = forms.ModelChoiceFieldPlus(UnidadeOrganizacional.objects.uo().all(), label="Campus", required=False)
    cargo_emprego = forms.ModelChoiceFieldPlus(
        CargoEmprego.utilizados.filter(cargoempregoarea__isnull=False).distinct(), label="Cargo Emprego", required=False
    )
    cargo_emprego_area = forms.ModelChoiceFieldPlus(CargoEmpregoArea.objects, label="Área", required=False)


class ServidorReativacaoTemporariaForm(forms.ModelFormPlus):
    class Meta:
        model = ServidorReativacaoTemporaria
        fields = (
            "servidor",
            "data_inicio",
            "data_fim",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Servidor.objects.filter(excluido=True)
        if self.instance.pk and not self.instance.servidor.excluido:
            queryset |= Servidor.objects.filter(pk=self.instance.servidor_id)
            self.fields["servidor"].widget = AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS, readonly=True)
        self.fields["servidor"].queryset = queryset


class ExcecaoDadoWSForm(forms.ModelFormPlus):
    campos = forms.MultipleModelChoiceFieldPlus(label="Dados", required=False, queryset=CampoExcecaoWS.objects.all())

    class Meta:
        model = ExcecaoDadoWS
        exclude = ()


class SolicitacaoAlteracaoFotoForm(forms.ModelFormPlus):
    solicitante = forms.ModelChoiceField(queryset=Servidor.objects, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS), label='Solicitante')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #
        # carregando o queryset do autocomplete
        self.fields["solicitante"].queryset = Servidor.objects.filter(excluido=False)
        user = self.request.user
        is_superuser = user.is_superuser
        #
        # verifica o vínculo e seta um valor inicial para o campo
        if user.eh_servidor:
            self.fields["solicitante"].initial = user.get_relacionamento()
        #
        # ocultando campos que são de preenchimento automático pelo sistema de controle
        self.fields["situacao"].widget = forms.HiddenInput()
        self.fields["data_interacao"].widget = forms.HiddenInput()
        self.fields["responsavel_interacao"].widget = forms.HiddenInput()
        self.fields["motivo_rejeicao"].widget = forms.HiddenInput()
        #
        # se for superuser, pode selecionar que é o solicitante
        if not is_superuser:
            self.fields["solicitante"].widget = forms.HiddenInput()

    class Meta:
        model = SolicitacaoAlteracaoFoto
        exclude = ()

    def clean(self):
        solicitante = self.cleaned_data.get("solicitante")
        if SolicitacaoAlteracaoFoto.objects.filter(solicitante=solicitante, situacao=SolicitacaoAlteracaoFoto.AGUARDADO_VALIDACAO).exists():
            raise forms.ValidationError(f"Já existe uma solicitação para {solicitante} aguardando validação. Não é possível realizar uma nova solicitação.")
        return self.cleaned_data


class RejeitarSolicitacaoAlteracaoFotoForm(forms.FormPlus):
    motivo_rejeicao = forms.CharField(widget=forms.Textarea, required=True, label='Motivo da Rejeição')
    solicitacao = forms.IntegerFieldPlus(label="Solicitação", widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super().__init__(*args, **kwargs)
        if instance.id:
            self.fields["solicitacao"].initial = instance.id

    def processar(self, request):
        s = SolicitacaoAlteracaoFoto.objects.get(id=request.POST.get("solicitacao"))
        s.rejeitar(request)


## FORMS FESF
class EmpregadoFesfForm(forms.ModelFormPlus):
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

    # titulo_eleitor
    titulo_numero = forms.CharField(max_length=12, required=False, label='Título de Eleitor')
    titulo_zona = forms.CharField(max_length=3, required=False, label='Zona')
    titulo_secao = forms.CharField(max_length=4, required=False, label='Seção')
    titulo_data_emissao = forms.DateFieldPlus(required=False, label='Data de Emissão')
    titulo_uf = forms.BrEstadoBrasileiroField(label='Estado Emissor', required=False)

    # CTPS
    ctps_numero = forms.CharField(max_length=20, required=False, label='CTPS Número')
    ctps_uf = forms.BrEstadoBrasileiroField(label='CTPS UF', required=False)
    ctps_serie = forms.CharField(max_length=3, required=False, label='CTPS Série')

    nascimento_data = forms.DateFieldPlus(label='Data de Nascimento', required=False)
    nome_pai = forms.CharFieldPlus(label='Nome do Pai', required=False)
    nome_mae = forms.CharFieldPlus(label='Nome da Mãe', required=False)
    naturalidade = forms.ModelChoiceFieldPlus(Municipio.objects, required=False, label='Naturalidade')

    logradouro = forms.CharFieldPlus(max_length=255, required=False, label='Logradouro', width=500)
    numero = forms.CharFieldPlus(max_length=255, required=False, label='Número', width=100)
    complemento = forms.CharField(max_length=255, required=False, label='Complemento')
    bairro = forms.CharField(max_length=255, required=False, label='Bairro')
    cep = forms.BrCepField(max_length=255, required=False, label='CEP')
    municipio = forms.ModelChoiceFieldPlus(Municipio.objects.all().order_by('pk'), required=False, label='Cidade', help_text='Preencha o nome da cidade sem acento.')
    nivel_escolaridade = forms.ModelChoiceFieldPlus(NivelEscolaridade.objects.all().order_by('pk'), required=False, label='Formação',
                                           help_text='Preencha a Formação.')

    setor = forms.ModelChoiceField(label='Lotação', queryset=Setor.objects.all(), widget=TreeWidget(), required=True)
    cargo_emprego = forms.ModelChoiceFieldPlus(CargoEmprego.utilizados.all(), label='Cargo', required=False)
    estado_civil = forms.ModelChoiceFieldPlus(EstadoCivil.objects.all(), label='Estado civil', required=False)
    email = forms.EmailField(max_length=255, label='E-mail')
    telefone = forms.BrTelefoneField(max_length=255, required=False, label='Telefone', help_text='Formato: "(XX) XXXXX-XXXX"')
    telefone_celular = forms.BrTelefoneField(max_length=45, label="Telefone Celular", required=False)

    titulo_data_emissao = forms.DateFieldPlus(label='Data da Emissão', required=False)
    # conselho classe
    numero_registro = forms.CharField(max_length=255, required=False, label='Número de Registro Conselho Profissional')

    fieldsets = (
        ('Dados Pessoais', {'fields': ('nome_registro', 'cpf', 'matricula', 'passaporte', 'nacionalidade', 'sexo', 'nascimento_data', 'nome_pai', 'nome_mae', 'naturalidade', 'estado_civil', 'nivel_escolaridade',)}),
        ('RG', {'fields': ('rg', 'rg_orgao', 'rg_data', 'rg_uf')}),
        ("Título de Eleitor", {"fields": ('titulo_numero', 'titulo_zona', 'titulo_secao', 'titulo_data_emissao', 'titulo_uf')}),
        ('Documentos', {'fields': ('ctps_numero', 'ctps_uf', 'ctps_serie', 'pis_pasep', 'numero_registro')}),
        ('Endereço', {'fields': ('cep', 'municipio', 'logradouro', 'numero', 'complemento', 'bairro')}),
        ('Dados para Contato', {'fields': ('email', 'telefone')}),
        ('Dados funcionais', {'fields': ('setor', 'cargo_emprego','situacao',)}),
        ('Dados Bancários', {'fields': ('pagto_banco', 'pagto_agencia', 'pagto_ccor',)}),

    )

    class Meta:
        model = Servidor
        exclude = ('excluido', 'vinculo', 'uuid', 'search_fields_optimized', 'documento_identificador' ,'username' ,'raca', 'pais_origem', 'deficiencia', 'pessoa_fisica', 'matricula_crh' ,'matricula_sipe' ,'setor_lotacao_data_ocupacao', 'nome'  )

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
        matricula = self.cleaned_data.get('matricula')
        nacionalidade = self.data.get('nacionalidade')
        eh_estrangeiro = int(nacionalidade) == Nacionalidade.ESTRANGEIRO if nacionalidade else False
        empregado_ja_cadastrado = False
        if not cpf and not eh_estrangeiro:
            self.add_error('cpf', "O campo CPF é obrigatório para nacionalidades Brasileira")

        cpf_formatado = cpf.replace(".", "").replace("-", "")
        if not self.instance.pk and User.objects.filter(username=cpf_formatado).exists():
            self.add_error('cpf', f"O usuário com o CPF {cpf_formatado} já existe.")
        if not self.instance.pk and Servidor.objects.filter(matricula=matricula).exists():
            self.add_error('matricula', f"Já existe usuário com matrícula igual a {matricula}.")
        return self.cleaned_data


class AdicionarDadosBancariosPFForm(forms.ModelFormPlus):
    numero_conta = forms.CharField(label='Número da Conta', required=True, widget=forms.TextInput(attrs={'pattern': '[0-9a-zA-Z]+'}), help_text='Utilize apenas números e letras')

    class Meta:
        model = DadosBancariosPF
        fields = ('banco', 'numero_agencia', 'tipo_conta', 'numero_conta', 'operacao', 'prioritario_servico_social')

    def __init__(self, pessoa_fisica, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.instance.pessoa_fisica = pessoa_fisica
        if pessoa_fisica.is_user(self.request):
            del self.fields['prioritario_servico_social']

    def clean(self):
        prioritario_servico_social = self.cleaned_data.get('prioritario_servico_social')
        dados = DadosBancariosPF.objects.filter(pessoa_fisica=self.instance.pessoa_fisica, prioritario_servico_social=True)
        if prioritario_servico_social and dados.exists():
            if (self.instance.pk and dados.exclude(id=self.instance.pk).exists()) or not self.instance.pk:
                raise forms.ValidationError('Já existe outro Dado Bancário marcado como prioritário para esta pessoa.')
        return self.cleaned_data
