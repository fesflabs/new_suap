import datetime
import hashlib
from collections import OrderedDict
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.forms.widgets import RadioSelect
from django.utils.safestring import mark_safe

from comum.models import Ocupacao, PrestadorServico, User, Vinculo
from comum.utils import datas_entre, formata_segundos, get_setor, get_uo
from djtools import forms
from djtools.forms.fields import DateFieldPlus
from djtools.forms.utils import render_field
from djtools.forms.widgets import AutocompleteWidget, TreeWidget
from djtools.html.calendarios import CalendarioPlus
from djtools.utils import save_session_cache
from ponto.compensacao import Contexto
from ponto.enums import TipoFormFrequenciaTerceirizados, TipoLiberacao
from ponto.models import (
    AbonoChefia,
    DocumentoAnexo,
    Frequencia,
    HorarioCompensacao,
    Maquina,
    Observacao,
    RecessoDia,
    RecessoDiaEscolhido,
    RecessoOpcao,
    RecessoOpcaoEscolhida,
    RecessoPeriodoCompensacao,
    TipoAfastamento,
)
from ponto.utils import (
    get_data_ultimo_dia_mes_corrente,
    get_datas_dia_um_e_ultimo_dia_mes_passado,
    get_datas_segunda_feira_e_sexta_feira_semana_passada,
    get_total_tempo_debito_pendente_mes_anterior,
    get_total_tempo_debito_pendente_mes_corrente,
    get_total_tempo_debito_pendente_semana_anterior,
    get_total_tempo_saldo_restante_mes_corrente,
)
from rh.models import CargoEmprego, Funcionario, Servidor, Setor, UnidadeOrganizacional


class ConfiguracaoForm(forms.FormPlus):
    subnets_ponto_online = forms.CharFieldPlus(
        label='Subredes do Ponto Online',
        help_text='Informe as subredes (separadas por ";") através das quais será possível registrar o ponto online pelo SUAP. Utilize "0.0.0.0/0" para não restringir pelo IP do usuário.', required=False)


class FrequenciaFormFactoryBase(forms.FormPlus):
    hoje = date.today()

    class Media:
        js = ('/static/js/frequencia-consulta-form.js',)

    faixa_0 = DateFieldPlus(initial=hoje, label='Início', required=True)
    faixa_1 = DateFieldPlus(initial=hoje, label='Término', required=True)
    so_inconsistentes = forms.BooleanField(initial=False, label='Apenas frequências inconsistentes', required=False)
    so_inconsistentes_apenas_esta_inconsistencia = forms.ChoiceField(
        choices=[
            [None, 'Qualquer'],
            [Frequencia.INCONSISTENCIA_MENOR_JORNADA, Frequencia.DESCRICAO_INCONSISTENCIA.get(Frequencia.INCONSISTENCIA_MENOR_JORNADA)],
            [Frequencia.INCONSISTENCIA_MAIOR_JORNADA, Frequencia.DESCRICAO_INCONSISTENCIA.get(Frequencia.INCONSISTENCIA_MAIOR_JORNADA)],
            [Frequencia.INCONSISTENCIA_FALTA, Frequencia.DESCRICAO_INCONSISTENCIA.get(Frequencia.INCONSISTENCIA_FALTA)],
            [Frequencia.INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS, Frequencia.DESCRICAO_INCONSISTENCIA.get(Frequencia.INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS)],
            [Frequencia.INCONSISTENCIA_TRABALHO_FDS, Frequencia.DESCRICAO_INCONSISTENCIA.get(Frequencia.INCONSISTENCIA_TRABALHO_FDS)],
        ],
        initial=None,
        label='Tipo de Inconsistência',
        required=False,
    )
    so_inconsistentes_situacao_abono = forms.ChoiceField(
        choices=[
            [Frequencia.SITUACAO_INCONSISTENCIA_DESCONSIDERAR_ABONO, 'Desconsiderar abono'],
            [Frequencia.SITUACAO_INCONSISTENCIA_COM_ABONO, 'Com abono'],
            [Frequencia.SITUACAO_INCONSISTENCIA_SEM_ABONO, 'Sem abono'],
            [Frequencia.SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO, 'Com ou sem abono'],
        ],
        initial=Frequencia.SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO,
        label='Situação das Inconsistências/Abono',
        required=False,
    )
    so_inconsistentes_situacao_debito = forms.ChoiceField(
        choices=[
            [Frequencia.SITUACAO_INCONSISTENCIA_DESCONSIDERAR_DEBITO, 'Desconsiderar débito'],
            [Frequencia.SITUACAO_INCONSISTENCIA_COM_DEBITO_TODO_COMPENSADO, 'Com débito totalmente compensado'],
            [Frequencia.SITUACAO_INCONSISTENCIA_COM_DEBITO_PARTE_COMPENSADO, 'Com débito parcialmente compensado'],
            [Frequencia.SITUACAO_INCONSISTENCIA_COM_DEBITO_NADA_COMPENSADO, 'Com débito sem nenhuma compensação'],
            [Frequencia.SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE, 'Com débito compensado ou não'],
        ],
        initial=Frequencia.SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE,
        label='Situação das Inconsistências/Débito de CH',
        required=False,
    )

    METHOD = 'GET'

    # calcula os dias que serão usados pelos EXTRA_BUTTONS a seguir
    seg_feira_semana_passada, sex_feira_semana_passada = get_datas_segunda_feira_e_sexta_feira_semana_passada()
    dia_um_mes_passado, ultimo_dia_mes_passado = get_datas_dia_um_e_ultimo_dia_mes_passado()
    dia_um_mes_atual = datetime.date(hoje.year, hoje.month, 1)
    ultimo_dia_mes_atual = get_data_ultimo_dia_mes_corrente()
    seg_feira_semana_atual = (seg_feira_semana_passada + timedelta(7)).date()
    sex_feira_semana_atual = (sex_feira_semana_passada + timedelta(7)).date()
    um_ano_atras = hoje - relativedelta(years=1)

    EXTRA_BUTTONS = [
        {
            'type': 'button',
            'value': 'Mês Passado',
            'name': '_continue',
            'class': 'btn small btn-frequencias',
            'extra_attrs': {
                'id': 'btn-frequencias-mes-passado',
                'data-dia-inicial': dia_um_mes_passado.strftime('%Y-%m-%d'),
                'data-dia-final': ultimo_dia_mes_passado.strftime('%Y-%m-%d'),
            },
        },
        {
            'type': 'button',
            'value': 'Semana Passada',
            'name': '_continue',
            'class': 'btn small btn-frequencias',
            'extra_attrs': {
                'id': 'btn-frequencias-semana-passada',
                'data-dia-inicial': seg_feira_semana_passada.strftime('%Y-%m-%d'),
                'data-dia-final': (sex_feira_semana_passada + timedelta(2)).strftime('%Y-%m-%d'),
            },
        },
        {
            'type': 'button',
            'value': 'Mês Atual',
            'name': '_continue',
            'class': 'btn small btn-frequencias',
            'extra_attrs': {
                'id': 'btn-frequencias-mes-atual',
                'data-dia-inicial': dia_um_mes_atual.strftime('%Y-%m-%d'),
                'data-dia-final': ultimo_dia_mes_atual.strftime('%Y-%m-%d'),
            },
        },
        {
            'type': 'button',
            'value': 'Semana Atual',
            'name': '_continue',
            'class': 'btn small btn-frequencias',
            'extra_attrs': {
                'id': 'btn-frequencias-semana-atual',
                'data-dia-inicial': seg_feira_semana_atual.strftime('%Y-%m-%d'),
                'data-dia-final': (sex_feira_semana_atual + timedelta(2)).strftime('%Y-%m-%d'),
            },
        },
        {
            'type': 'button',
            'value': 'Últimos 12 Meses ({} à {})'.format(um_ano_atras.strftime('%d/%m/%Y'), hoje.strftime('%d/%m/%Y')),
            'name': '_continue',
            'class': 'btn small btn-frequencias',
            'extra_attrs': {'id': 'btn-frequencias-ultimo-ano', 'data-dia-inicial': um_ano_atras.strftime('%Y-%m-%d'), 'data-dia-final': hoje.strftime('%Y-%m-%d')},
        },
    ]


def FrequenciaFuncionarioFormFactory(request):
    """
    Cria uma classe de formulário com base na permissão do usuário autenticado.
    """
    usuario = request.user
    funcionario_logado = usuario.get_relacionamento()
    initial_servidor = funcionario_logado if funcionario_logado.eh_servidor else None
    queryset = Servidor.objects.all()
    if usuario.has_perm('ponto.pode_ver_frequencia_todos'):
        help_text = 'Pode ver frequência de todos os servidores do instituto.'
    else:
        help_text = []
        if usuario.has_perm('ponto.pode_ver_frequencia_campus'):
            help_text.append('Pode ver frequência dos servidores do seu campus, ou que já foram do seu campus e ' 'de todos os setores em que teve função.')

        elif funcionario_logado.eh_servidor:
            help_text.append("Pode ver frequência dos servidores de todos os setores em que teve função.")

        elif usuario.has_perm('ponto.pode_ver_frequencia_propria') and funcionario_logado.eh_servidor:
            queryset = Servidor.objects.filter(pk=funcionario_logado.pk)
            help_text.append("Pode ver frequência própria.")

        help_text = ' '.join(help_text)

    class FrequenciaFuncionarioForm(FrequenciaFormFactoryBase):
        funcionario = forms.ModelChoiceField(
            queryset=queryset, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS), help_text=help_text, initial=initial_servidor, label='Servidor'
        )

        fieldsets = (
            (
                None,
                {
                    'fields': (
                        'funcionario',
                        ('faixa_0', 'faixa_1'),
                        ('so_inconsistentes',),
                        ('so_inconsistentes_apenas_esta_inconsistencia', 'so_inconsistentes_situacao_abono', 'so_inconsistentes_situacao_debito'),
                    )
                },
            ),
        )

        def clean(self):
            if not self.cleaned_data.get('faixa_1') or not self.cleaned_data.get('faixa_0'):
                raise forms.ValidationError('Corrija os erros abaixo.')
            if self.cleaned_data['faixa_1'] < self.cleaned_data['faixa_0']:
                raise forms.ValidationError('Data Término não pode ser menor do que a Data Início.')
            if self.cleaned_data['faixa_1'] - self.cleaned_data['faixa_0'] > timedelta(days=366):
                raise forms.ValidationError('A diferença entre as datas não pode ser maior que 365 dias.')
            return self.cleaned_data

    return FrequenciaFuncionarioForm


def FrequenciaDocenteFormFactory(request):
    form_class = FrequenciaFuncionarioFormFactory(request)
    form_class.fieldsets = ((None, {'fields': ('funcionario', ('faixa_0', 'faixa_1'), ('so_inconsistentes',))}),)
    return form_class


def FrequenciasPorSetorFormFactory(request):
    hoje = date.today()

    class FormFrequenciaSetor(forms.FormPlus):
        METHOD = 'GET'
        setor = forms.ModelChoiceField(queryset=Setor.objects, widget=AutocompleteWidget(search_fields=Setor.SEARCH_FIELDS), initial=get_setor().id)
        recursivo = forms.BooleanField(required=False, label='Incluir Sub-setores?')
        faixa_0 = DateFieldPlus(initial=hoje, label='Início', required=True)
        faixa_1 = DateFieldPlus(initial=hoje, label='Término', required=True)

        fieldsets = (('', {'fields': ('setor', 'recursivo', 'faixa_0', 'faixa_1')}),)

    return FormFrequenciaSetor


##############################
# Frequências de Estagiários #
##############################
def FrequenciaEstagiariosFormFactory(data=None):
    fields = dict()
    fields['faixa_0'] = DateFieldPlus(initial=date.today(), label='Início')
    fields['faixa_1'] = DateFieldPlus(initial=date.today(), label='Término')
    fieldsets = ((None, {'fields': ('faixa_0', 'faixa_1')}),)

    return type('FrequenciaEstagiariosForm', (forms.BaseForm,), {'base_fields': fields, 'fieldsets': fieldsets, 'METHOD': 'GET', 'TITLE': 'Frequências de Estagiários'})


##############################
#     Frequência Noturna     #
##############################
def FrequenciaNoturnaFormFactory(user):
    CARGO_EMPREGO_CHOICES = [['docente', 'Docente'], ['tecnico_administrativo', 'Técnico-Administrativo'], ['professor_substituto_temporario', 'Professor Substituto/Temporário']]
    hoje = date.today()

    class FormFrequenciaNoturnaSetor(forms.FormPlus):
        cargo_emprego = forms.ChoiceField(widget=RadioSelect(), choices=CARGO_EMPREGO_CHOICES)
        uo = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap().all(), widget=forms.Select, label='Campus')
        faixa_0 = DateFieldPlus(initial=hoje, label='Início')
        faixa_1 = DateFieldPlus(initial=hoje, label='Término')

        METHOD = 'GET'

    return FormFrequenciaNoturnaSetor


############################
# Frequências de Bolsistas #
############################
def FrequenciaBolsistasFormFactory(data=None):
    fields = dict()
    hoje = date.today()
    fields['faixa_0'] = DateFieldPlus(initial=hoje, label='Início')
    fields['faixa_1'] = DateFieldPlus(initial=hoje, label='Término')

    fieldsets = ((None, {'fields': ('faixa_0', 'faixa_1')}),)

    return type('FrequenciaBolsistasForm', (forms.BaseForm,), {'base_fields': fields, 'fieldsets': fieldsets, 'METHOD': 'GET', 'TITLE': 'Frequências de Bolsistas'})


################################
# Frequências de Terceirizados #
################################
def FrequenciaTerceirizadosFormFactory(request, tipo_form):
    """
    Retorna uma classe que serve para construção do formulário para listar
    frequências de todos os terceirizados da Instituição.
    """
    funcionario_logado = request.user.get_profile().sub_instance()
    qs_prestador = PrestadorServico.objects.none()
    raiz = Setor.objects.none()

    if request.user.has_perm('ponto.pode_ver_frequencia_terceirizados_todos'):
        raiz = Setor.raiz()
        qs_prestador = PrestadorServico.objects.all()
    elif request.user.has_perm('ponto.pode_ver_frequencia_terceirizados_campus'):
        qs_prestador = PrestadorServico.objects.filter(setor__uo=funcionario_logado.setor.uo)
        raiz = funcionario_logado.setor.uo.setor
    elif request.user.has_perm('ponto.pode_ver_frequencia_terceirizados_setor'):
        qs_prestador = PrestadorServico.objects.filter(setor=funcionario_logado.setor)
        raiz = funcionario_logado.setor

    if request.user.has_perm('ponto.pode_ver_frequencia_terceirizados_propria'):
        qs_prestador = (qs_prestador | PrestadorServico.objects.filter(cpf=funcionario_logado.cpf)).distinct()

    hoje = date.today()
    fields = dict()
    fields['faixa_0'] = DateFieldPlus(initial=hoje, label='Início')
    fields['faixa_1'] = DateFieldPlus(initial=hoje, label='Término')

    fieldsets = ()

    if tipo_form == TipoFormFrequenciaTerceirizados.POR_SETOR:
        fieldsets = ((None, {'fields': ('setor', 'recursivo', ('faixa_0', 'faixa_1'), 'ocupacao')}),)
        fields['ocupacao'] = forms.ModelChoiceField(queryset=Ocupacao.objects.all(), widget=forms.Select, empty_label='Todos', label='Tipo prestador', required=False)
        fields['setor'] = forms.ModelChoiceField(queryset=Setor.objects.all(), widget=TreeWidget(root_nodes=[raiz]), initial=get_setor().id)
        fields['recursivo'] = forms.BooleanField(required=False, label='Incluir Sub-setores?')

    if tipo_form == TipoFormFrequenciaTerceirizados.POR_TERCEIRIZADO:
        fields['terceirizado'] = forms.ModelChoiceFieldPlus(
            queryset=qs_prestador,
            widget=AutocompleteWidget(search_fields=PrestadorServico.SEARCH_FIELDS),
            initial=qs_prestador.filter(cpf=request.user.get_profile().cpf)[0] if qs_prestador.filter(cpf=request.user.get_profile().cpf).exists() else None,
        )
        fieldsets = ((None, {'fields': ('terceirizado', ('faixa_0', 'faixa_1'))}),)

    return type('FrequenciaTerceirizadosForm', (forms.BaseForm,), {'base_fields': fields, 'fieldsets': fieldsets, 'METHOD': 'GET'})


# Frequência de Setor
def setor_raiz_por_permissao_ponto(request):
    if request.user.has_perm('ponto.pode_ver_frequencia_todos') or request.user.has_perm('ponto.pode_ver_frequencias_enquanto_foi_chefe'):
        return Setor.raiz()
    elif request.user.has_perm('ponto.pode_ver_frequencia_campus'):
        return request.user.get_profile().funcionario.setor.uo.setor
    else:
        return Setor.objects.none()


def FrequenciaCargoEmpregoFormFactory(data=None):
    hoje = date.today()

    class FormFrequenciaCargoEmprego(forms.FormPlus):
        cargo_emprego = forms.ModelChoiceField(queryset=CargoEmprego.utilizados.filter(excluido=False), widget=forms.Select)
        faixa_0 = DateFieldPlus(initial=hoje, label='Início')
        faixa_1 = DateFieldPlus(initial=hoje, label='Término')
        METHOD = 'GET'

        def clean_faixa_1(self):
            diff = self.cleaned_data['faixa_1'] - self.cleaned_data['faixa_0']
            if diff.days > 30:
                raise forms.ValidationError('Faixa não deve exceder 30 dias!')
            return self.cleaned_data['faixa_1']

    return FormFrequenciaCargoEmprego


class MaquinaForm(forms.ModelFormPlus):
    usuarios = forms.MultipleModelChoiceFieldPlus(label='Usuários', required=False, queryset=User.objects.all())

    class Meta:
        model = Maquina
        exclude = ('versao_terminal',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['uo'].queryset = UnidadeOrganizacional.objects.suap()


def AbonoChefiaFormFactory(tipo_inconsistencia):
    choices = AbonoChefia.CHOICES_POR_INCONSISTENCIAS[tipo_inconsistencia]

    class AbonoChefiaForm(forms.ModelFormPlus):
        acao_abono = forms.ChoiceField(label='Avaliação da Chefia', choices=choices)

        class Meta:
            model = AbonoChefia
            exclude = ('pessoa', 'chefe_imediato', 'data')

    return AbonoChefiaForm


def AbonoChefiaLoteFormFactory(tipo_inconsistencia, frequencias_dias):
    choices = AbonoChefia.CHOICES_POR_INCONSISTENCIAS[tipo_inconsistencia]
    frequencias_dias_choices = [[dias, dias] for dias in frequencias_dias]

    class AbonoChefiaLoteForm(forms.FormPlus):
        descricao = forms.CharField(label='Descrição', required=False, widget=forms.Textarea())
        acao_abono = forms.ChoiceField(label='Avaliação da Chefia', choices=choices, required=True)
        frequencias_dias = forms.MultipleChoiceField(
            label="frequencias_dias", widget=forms.widgets.CheckboxSelectMultiple(attrs={"checked": ""}), choices=frequencias_dias_choices, required=True
        )
        METHOD = 'POST'

    return AbonoChefiaLoteForm


class ObservacaoForm(forms.ModelFormPlus):
    class Meta:
        model = Observacao
        exclude = ('pessoa', 'data')


class ObservacaoAdminForm(forms.ModelFormPlus):
    data = DateFieldPlus()

    class Meta:
        model = Observacao
        fields = ('data', 'descricao')

    def save(self, *args, **kwargs):
        self.instance.vinculo = self.request.user.get_vinculo()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.is_valid():
            is_superuser = self.request.user.is_superuser
            tem_abono = AbonoChefia.objects.filter(data=self.cleaned_data['data'], vinculo_pessoa=self.request.user.get_vinculo()).exists()
            if not is_superuser and tem_abono:
                raise forms.ValidationError('Existe uma ação da chefia imediata com relação à frequência inconsistente na data informada.')
        return self.cleaned_data


class LiberacaoForm(forms.ModelFormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap(), label='Unidade Organizacional', empty_label='Todas', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.request.user.is_superuser or self.request.user.has_perm('ponto.eh_gerente_sistemico_ponto'):
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.suap().all()
        else:
            uo_logado = get_uo(self.request.user.get_profile())
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.suap().filter(id=uo_logado.pk)

    """
    Assegura que a UO escolhida seja a da pessoa logada, a não ser que seja
    gerente_sistemico_ponto.
    """

    def clean_uo(self):
        if self.request.user.has_perm('ponto.eh_gerente_sistemico_ponto'):
            return self.cleaned_data["uo"]
        else:
            if get_uo(self.request.user) != self.cleaned_data["uo"]:
                raise forms.ValidationError('Sua Unidade Organizacional deve ser escolhida.')
            else:
                return self.cleaned_data["uo"]

    def clean(self):
        clean = super().clean()
        if clean.get('tipo') == TipoLiberacao.get_numero(TipoLiberacao.LIBERACAO_PARCIAL):
            if not clean.get('ch_maxima_exigida') > 0:
                self.add_error('ch_maxima_exigida', 'Para o tipo \'{}\', a carga horária máxima exigida deve ' 'ser informada.'.format(TipoLiberacao.LIBERACAO_PARCIAL))
        else:
            clean['ch_maxima_exigida'] = 0  # força ZERO
        return clean


# FIXME: o ideal seria utilizar o daterange widget para tratar as duas datas do afastamento.
class AfastamentoForm(forms.ModelFormPlus):
    data_ini = DateFieldPlus()
    data_fim = DateFieldPlus()
    vinculo = forms.ModelChoiceField(queryset=Vinculo.objects.none(), widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS))
    tipo = forms.ModelChoiceField(queryset=TipoAfastamento.objects.all(), widget=AutocompleteWidget(search_fields=TipoAfastamento.SEARCH_FIELDS))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vinculo'].queryset = Vinculo.objects.filter(tipo_relacionamento=ContentType.objects.get(Vinculo.SERVIDOR))

    def clean(self):
        self.validate_unique()
        if not self.errors:
            if self.cleaned_data['data_ini'] > self.cleaned_data['data_fim']:
                raise forms.ValidationError('A data inicial é maior que a final')
        return self.cleaned_data


##########################################################################################
# COMPENSAÇÃO DE HORÁRIO E RECESSOS
##########################################################################################


def get_type_form_multiplas_compensacao_horario(
    request,
    periodo_data_inicial,
    periodo_data_final,
    apenas_recessos=False,
    apenas_os_recessos_escolhidos=[],
    apenas_debitos_do_periodo_consultado=False,
    omite_debitos_de_acompanhamentos_especificos=False,
):
    """ Permite que saldos excedentes de carga horária de um certo período possam ser distribuídos em um ou
        mais dias com débitos, gerando os informes de compensação.

        O universo de dias dos débitos depende do período informado e inclui:
            - dias do mês anterior à data inicial do período informado (atendendo a regra do mês seguinte)
            - dias do mês que contém a data final do período informado e que são menores que essa data
            - dias ref. a compensações em acompanhamento (ex: recessos) que podem ser compensados no período
              informado (posteriormento ou anteriormente)

        Um calendário será exibido com os dias que possuem débito e os que possuem saldo. Será destacado, se for
        o caso, os dias em débito a compensar ref. a compensações em acompanhamento (ex: recessos).

        Trata-se de um formulário com fields dinâmicos. Cada field representa um informe de compensação de horário,
        contendo: (1) a carga horária compensada (no 'value' do field); (2) a data do débito e a data do saldo utilizado
        (no 'name' do field). Se o formulário não conter dados de requisição, uma distribuição padrão do saldo será
        feita. Durante a exibição do formulário será possível editar a distribuição que foi feita, 'resetando' a atual.

        A edição da distribuição do saldo permite, manualmente, que certo saldo produzido seja utilizado por um certo
        débito.

                                                                          saldos
        período informado/período dos saldos                        |-----------------|

                                                      acomp.        normal + recessos           acomp.
        período envolvido/período dos débitos     |-----------|---------------------------|-----------------|
    """

    def _get_field_name(_data_debito, _data_saldo):
        return '{}_{}'.format(_data_debito.strftime('%Y%m%d'), _data_saldo.strftime('%Y%m%d'))

    funcionario = request.user.get_profile().sub_instance()

    # contexto conforme período informado

    compensacao_contexto = Contexto(servidor=funcionario, periodo_data_inicial=periodo_data_inicial, periodo_data_final=periodo_data_final)

    saldos = OrderedDict()
    for dia_saldo, dia_situacao in list(compensacao_contexto.dias_saldos.items()):
        if dia_situacao.saldo_qtd_restante > 0:
            saldos[dia_saldo] = dia_situacao.saldo_qtd_restante

    datas_recesso = list(compensacao_contexto.todos_dias_debitos_especificos.keys())
    recessos_escolhidos = compensacao_contexto.get_acompanhamentos_envolvidos  # queryset de RecessoOpcaoEscolhida

    debitos = OrderedDict()
    debitos_situacoes = []

    if apenas_recessos:
        # considera apenas os débitos de recessos
        for data_debito in datas_recesso:
            dia_situacao = compensacao_contexto.get_dia(data_debito, add_se_nao_existir=True)
            if apenas_os_recessos_escolhidos:
                acompanhamentos_referentes_ao_debito = dia_situacao.acompanhamentos_envolvidos_contendo_o_dia_como_debito
                if acompanhamentos_referentes_ao_debito.exists():
                    if set(apenas_os_recessos_escolhidos).intersection(acompanhamentos_referentes_ao_debito):
                        debito_qtd_restante = dia_situacao.debito_qtd_restante
                        if debito_qtd_restante > 0:
                            debitos[data_debito] = debito_qtd_restante
                            debitos_situacoes.append(dia_situacao)
            else:
                debito_qtd_restante = dia_situacao.debito_qtd_restante
                if debito_qtd_restante > 0:
                    debitos[data_debito] = debito_qtd_restante
                    debitos_situacoes.append(dia_situacao)
    else:
        if apenas_debitos_do_periodo_consultado:
            dias_debitos = compensacao_contexto.dias_debitos
        else:
            dias_debitos = compensacao_contexto.todos_dias_debitos

        for dia_debito, dia_situacao in list(dias_debitos.items()):
            if omite_debitos_de_acompanhamentos_especificos and dia_situacao.is_debito_especifico:
                continue
            if dia_situacao.debito_qtd_restante > 0:
                debitos[dia_debito] = dia_situacao.debito_qtd_restante
                debitos_situacoes.append(dia_situacao)

    recessos_escolhidos_pendentes = RecessoOpcaoEscolhida.objects.none()
    for dia_situacao in debitos_situacoes:
        recessos_escolhidos_pendentes = (recessos_escolhidos_pendentes | dia_situacao.acompanhamentos_envolvidos_contendo_o_dia_como_debito).distinct()

    periodo_envolvido_data_inicial = None
    periodo_envolvido_data_final = None

    frequencias_no_periodo = compensacao_contexto.get_frequencias_as_queryset

    fields = {}  # {'fieldname': field}
    saldos_utilizacao = OrderedDict()  # {data_saldo: ?, data_saldo: ?, ...}
    debitos_saldos_utilizacao = OrderedDict()  # {data_debito: {data_saldo: ?, data_saldo: ?, ...}, ...}

    if debitos:
        # período de abrangência dos débitos
        periodo_envolvido_data_inicial = min(debitos.keys())
        periodo_envolvido_data_final = max(debitos.keys())

        #
        # processa as datas do período envolvido, procurando débitos e criando os fields ref. aos informes de
        # compensação
        if not request.POST:
            ###########
            # Não há dados POSTados na requisição. Distribui o saldo e cria os fields automaticamente.
            ###########
            for data_debito in datas_entre(periodo_envolvido_data_inicial, periodo_envolvido_data_final, sabado=False, domingo=False):
                debito_na_data = debitos.get(data_debito, 0)
                if debito_na_data:
                    debitos_saldos_utilizacao[data_debito] = OrderedDict()
                    #
                    # pega o saldo para quitar o débito
                    carga_horaria_a_compensar = 0
                    for data_saldo, saldo in list(saldos.items()):
                        #
                        # o saldo pode ser utilizado pelo débito?
                        saldo_pode_ser_utilizado = data_saldo in compensacao_contexto.get_dia(data_debito).debito_dias_dos_saldos

                        if saldo_pode_ser_utilizado:
                            if data_saldo not in saldos_utilizacao:
                                saldos_utilizacao[data_saldo] = 0
                            #
                            saldo_a_utilizar = saldo - saldos_utilizacao[data_saldo]
                            if saldo_a_utilizar > 0:
                                carga_horaria_a_compensar += saldo_a_utilizar
                                if carga_horaria_a_compensar >= debito_na_data:
                                    diferenca = carga_horaria_a_compensar - debito_na_data
                                    carga_horaria_a_compensar = debito_na_data  # limita-se ao débito
                                    saldo_a_utilizar -= diferenca
                                #
                                saldos_utilizacao[data_saldo] += saldo_a_utilizar
                                if data_saldo not in debitos_saldos_utilizacao[data_debito]:
                                    debitos_saldos_utilizacao[data_debito][data_saldo] = 0
                                debitos_saldos_utilizacao[data_debito][data_saldo] += saldo_a_utilizar
                        #
                        if carga_horaria_a_compensar == debito_na_data:
                            break
                    #
                    # fields OCULTOS ref. a compensação do débito
                    for data_saldo, _saldo in list(debitos_saldos_utilizacao[data_debito].items()):
                        ##############
                        field_name = _get_field_name(data_debito, data_saldo)
                        #
                        field_value = '{h}:{m}:{s}'.format(**formata_segundos(_saldo))
                        field_debito_compensacao = forms.TimeFieldPlus(widget=forms.HiddenInput, required=False, initial=field_value)
                        fields[field_name] = field_debito_compensacao
        else:
            ###########
            # Há dados POSTados na requisição. Nesse caso, a distribuição do saldo e os fields de compensação
            # estão na requisição.
            ###########
            #
            # inicializa os débitos sem distribuir os saldos e sem criar os fields
            for data_debito in datas_entre(periodo_envolvido_data_inicial, periodo_envolvido_data_final, sabado=False, domingo=False):
                debito_na_data = debitos.get(data_debito, 0)
                if debito_na_data:
                    # apenas prepara
                    debitos_saldos_utilizacao[data_debito] = OrderedDict()
            #
            # distribui os saldos e cria os fields
            for field_name in list(request.POST.keys()):
                try:
                    #
                    # formato esperado para um field ref. a um informe de compensaçao = 'datadebito_datasaldo'
                    data_debito = datetime.datetime.strptime(field_name.split('_')[0], '%Y%m%d').date()
                    data_saldo = datetime.datetime.strptime(field_name.split('_')[1], '%Y%m%d').date()
                    ##############
                    #
                    field_value = datetime.datetime.strptime(request.POST[field_name].strip(), '%H:%M:%S').time()
                    field_debito_compensacao = forms.TimeFieldPlus(widget=forms.HiddenInput, required=False, initial=field_value)
                    fields[field_name] = field_debito_compensacao
                    #
                    saldo_utilizado = Frequencia.time_para_segundos(field_value)
                    #
                    if data_saldo not in saldos_utilizacao:
                        saldos_utilizacao[data_saldo] = 0
                    saldos_utilizacao[data_saldo] += saldo_utilizado
                    #
                    if data_debito not in debitos_saldos_utilizacao:
                        debitos_saldos_utilizacao[data_debito] = OrderedDict()
                    if data_saldo not in debitos_saldos_utilizacao[data_debito]:
                        debitos_saldos_utilizacao[data_debito][data_saldo] = 0
                    debitos_saldos_utilizacao[data_debito][data_saldo] += saldo_utilizado
                except Exception:
                    pass

    #
    # prepara o calendário
    calendario = CalendarioPlus()
    calendario.mostrar_mes_e_ano = True
    calendario.envolve_mes_em_um_box = True
    calendario.destacar_hoje = False
    #
    # adiciona os saldos no calendário
    saldo_total_em_segundos = 0
    saldo_total_distribuido_em_segundos = 0
    saldo_total_a_distribuir_em_segundos = 0
    for data_saldo, saldo in list(saldos.items()):
        saldo_utilizado = saldos_utilizacao.get(data_saldo, 0)
        saldo_a_utilizar = saldo - saldo_utilizado
        saldo_total_em_segundos += saldo
        saldo_total_distribuido_em_segundos += saldo_utilizado
        saldo_total_a_distribuir_em_segundos += saldo_a_utilizar
        #
        link_frequencia = '/ponto/ver_frequencia/{}/?datas={}'.format(funcionario.matricula, data_saldo.strftime('%d%m%Y'))
        #
        info_saldo = (
            '<li class="alert saldo">'
            ''
            '<span class="data" hidden="hidden">{data}</span>'
            '<span class="valor-em-segundos" hidden="hidden">{saldo_em_segundos}</span>'
            '<span class="valor-distribuido-em-segundos" hidden="hidden">{distribuindo_em_segundos}</span>'
            '<span class="valor-a-distribuir-em-segundos" hidden="hidden">{distribuir_em_segundos}</span>'
            '<h4>Saldo: <strong><span class="valor-a-distribuir-view">{saldo}</span></strong></h4>'
            '<dl>'
            '<dt>Distribuído:</dt>'
            '<dd><span class="valor-distribuido-view">{saldo_distruibuido}</span></dd>'
            '</dl>'
            '<div class="clear"></div>'
            '<p><a class="btn default popup" href="{link}"><span class="far fa-clock" aria-hidden="true"></span> '
            'Frequência do Dia</a></p>'
            '</li>'.format(
                **dict(
                    data=data_saldo.strftime('%Y%m%d'),
                    saldo_em_segundos=saldo,
                    distribuindo_em_segundos=saldo_utilizado,
                    distribuir_em_segundos=saldo_a_utilizar,
                    saldo_distruibuido=formata_segundos(saldo_utilizado, '{h}h ', '{m}min ', '{s}seg ', True),
                    saldo=formata_segundos(saldo_a_utilizar, '{h}h ', '{m}min ', '{s}seg ', True),
                    link=link_frequencia,
                )
            )
        )
        #
        saldo_totalmente_utilizado_info = ''
        if saldo_a_utilizar > 0:
            saldo_totalmente_utilizado_info = 'hidden="hidden"'
        info_saldo += (
            '<li class="info saldo-totalmente-utilizado" {}>'
            '<p><strong>Este saldo está sendo totalmente utilizado/distribuído.</strong></p>'
            '</li>'.format(saldo_totalmente_utilizado_info)
        )

        #
        # adiciona no calendário
        calendario.adicionar_evento_calendario(data_inicio=data_saldo, data_fim=data_saldo, descricao=info_saldo, css_class='info', title='')

    # totaliza os débitos
    debito_total_em_segundos = 0
    debito_periodo_consultado_total_em_segundos = 0
    debito_total_compensado_em_segundos = 0
    for data_debito, debito in list(debitos.items()):
        debito_total_em_segundos += debito
        for compensado in list(debitos_saldos_utilizacao.get(data_debito, {}).values()):
            debito_total_compensado_em_segundos += compensado
        if periodo_data_inicial <= data_debito <= periodo_data_final:
            debito_periodo_consultado_total_em_segundos += debito

    debito_total_restante_em_segundos = debito_total_em_segundos - debito_total_compensado_em_segundos
    if debito_total_restante_em_segundos < 0:
        debito_total_restante_em_segundos = 0

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        ######################################################################
        # adiciona os débitos no calendário
        for _data_debito in self.debitos_saldos_utilizacao:
            self.add_debito_no_calendario(_data_debito)
            ######################################################################

    def add_debito_no_calendario(self, _data_debito):
        #
        # saldos utilizados pelo débito (renderiza os fields ref. aos informes de compensação do débito)
        info_saldos_utilizados = []
        _saldos_utilizados_total = 0
        for _data_saldo, _saldo_utilizado in list(self.debitos_saldos_utilizacao[_data_debito].items()):
            _saldos_utilizados_total += _saldo_utilizado
            _field_name = _get_field_name(_data_debito, _data_saldo)
            ###########
            # renderiza o field dentro do calendário via djtools.forms.utils.render_field
            _field_debito_compensacao_render = render_field(self, _field_name)
            ###########
            info_saldos_utilizados.append(
                ''
                '<span class="valor-em-segundos" hidden="hidden">{}</span>'
                '<p>Saldo utilizado: <strong><span class="valor-view">{}</span></strong> em {}.</p>'
                '{}'
                ''.format(
                    _saldo_utilizado, formata_segundos(_saldo_utilizado, '{h}h ', '{m}min ', '{s}seg ', True), _data_saldo.strftime('%d/%m/%Y'), _field_debito_compensacao_render
                )
            )
        #
        _debito = self.debitos.get(_data_debito, 0)
        _debito_restante = _debito - _saldos_utilizados_total
        if _debito_restante < 0:
            _debito_restante = 0
        #
        _link_frequencia = '/ponto/ver_frequencia/{}/?datas={}'.format(funcionario.matricula, _data_debito.strftime('%d%m%Y'))
        #
        info_debito = (
            '<li class="error debito">'
            '<span class="data" hidden="hidden">{data}</span>'
            '<span class="valor-em-segundos" hidden="hidden">{debito_em_segundos}</span>'
            '<span class="valor-compensado-em-segundos" hidden="hidden">{compensado_em_segundos}</span>'
            '<h4>Débito: <strong><span class="valor-restante-view">{debito_restante}</span></strong></h4>'
            '<dl>'
            '<dt>Compensando:</dt>'
            '<dd><span class="valor-compensado-view">{saldo_utilizado_total}</span></dd>'
            '</dl>'
            '<div class="clear"></div>'
            '<p><a class="btn default popup" href="{link}"><span class="far fa-clock" aria-hidden="true"></span> '
            'Frequência do Dia</a></p>'
            '</li>'.format(
                **dict(
                    data=_data_debito.strftime('%Y%m%d'),
                    debito_em_segundos=_debito,
                    compensado_em_segundos=_saldos_utilizados_total,
                    saldo_utilizado_total=formata_segundos(_saldos_utilizados_total, '{h}h ', '{m}min ', '{s}seg ', True),
                    debito_restante=formata_segundos(_debito_restante, '{h}h ', '{m}min ', '{s}seg ', True),
                    link=_link_frequencia,
                )
            )
        )
        #
        _debito_totalmente_compensado_info = ''
        if _debito > _saldos_utilizados_total:
            _debito_totalmente_compensado_info = 'hidden="hidden"'
        info_debito += (
            '<li class="info debito-totalmente-compensado" {}>'
            '<p><strong>Este débito está sendo totalmente compensado.</strong></p>'
            '</li>'.format(_debito_totalmente_compensado_info)
        )
        #
        # débito abaixo do mínimo?
        if _debito < HorarioCompensacao.DEBITO_MINIMO_EM_SEGUNDOS:
            info_debito += (
                '<li class="info info-extra">'
                '<p>Débito abaixo de {}.</p>'
                '</li>'.format(formata_segundos(HorarioCompensacao.DEBITO_MINIMO_EM_SEGUNDOS, '{h}h ', '{m}min ', '{s}seg ', True))
            )
        #
        # débito refere-se a um dia de recesso ?
        if _data_debito in self.datas_recesso:
            _recessos_escolhidos = self.compensacao_contexto.get_dia(_data_debito).acompanhamentos_envolvidos_contendo_o_dia_como_debito

            for _recesso_escolhido in _recessos_escolhidos:
                info_debito += f'<li class="info info-extra"><p>Acompanhamento: <strong>{_recesso_escolhido.recesso_opcao}</strong></p></li>'

            # no dia em questão houve carga horária trabalhada?
            if self.frequencias_no_periodo.filter(horario__date=_data_debito).exists():
                info_debito += '<li class="info info-extra"><p>Carga Horária trabalhada não esperada.</p></li>'
        #
        # exibe os saldos utilizados pelo débito
        for info_saldo_utilizado in info_saldos_utilizados:
            info_debito += '<li class="extra saldo-utilizado">' '{}' '</li>'.format(info_saldo_utilizado)
        #
        # adiciona no calendário
        self.calendario.adicionar_evento_calendario(data_inicio=_data_debito, data_fim=_data_debito, descricao=info_debito, css_class='error', title='')

    @property
    def media(self):
        return forms.Media(css={}, js=('/static/js/ponto-util.js', '/static/js/informar-compensacao.js'))

    def form_rendered(self):
        # O form renderizado não segue o padrão tabular label: field.
        # Os fields foram renderizados no calendário (no conteúdo do eventos) via método
        # djtools.forms.utils.render_field. Esse código foi baseado no templatetag djtools.forms.utils.render_form,
        # o qual cria um conteúdo HTML de um form organizado nas seções: 1) erros do formulário e 2) fields do
        # formulário. Para o caso deste form, este método substituíra (não chamará) a implementação de
        # djtools.forms.utils.render_form.
        # Para isso, foi refatorada a tag djtools.templatetags.tags.RenderFormNode:
        #   - se o form já possui o atributo 'rendered', não precisa criá-lo (via djtools.forms.utils.render_form)

        periodo_renderizado_data_inicial = self.periodo_envolvido_data_inicial or self.compensacao_contexto.get_periodo[0]
        periodo_renderizado_data_final = self.periodo_envolvido_data_final or self.compensacao_contexto.get_periodo[1]

        periodo_situacao_data_inicial = self.compensacao_contexto.get_periodo[0]
        periodo_situacao_data_final = self.compensacao_contexto.get_periodo[1]

        if periodo_renderizado_data_inicial > periodo_situacao_data_inicial:
            periodo_renderizado_data_inicial = periodo_situacao_data_inicial

        if periodo_renderizado_data_final < periodo_situacao_data_final:
            periodo_renderizado_data_final = periodo_situacao_data_final

        out = [
            '<div>',
            # seção 1) erros do formulário
            #          copiado de "djtools.forms.utils.render_form"
            '{}'.format('<ul class="errorlist">{}</ul>'.format(''.join(['<li>{}</li>'.format(error) for error in self.non_field_errors()]))) if self.non_field_errors() else '',
            # seção 2) fields do formulário via conteúdo HTML específico (no conteúdo do evento do calendário) no qual
            #          os fields são inseridos em locais que não seguem o padrão "label: field", MAS são renderizados
            #          via "djtools.forms.utils.render_field" (aproveitamento do código de um formfield renderizado)
            self.calendario.formato_periodo(
                mes_inicio=periodo_renderizado_data_inicial.month,
                ano_inicio=periodo_renderizado_data_inicial.year,
                mes_fim=periodo_renderizado_data_final.month,
                ano_fim=periodo_renderizado_data_final.year,
                omite_mes_sem_eventos=True,
            )
            if self.calendario.eventos
            else '',
            '</div>',
        ]
        return mark_safe(''.join(out))

    def clean(self):
        _clean = super(self.__class__, self).clean()
        #
        # 1) o total de saldo utilizado deve existir e ser menor ou igual ao total de saldo disponível
        _total_saldo = self.saldo_total_em_segundos
        _total_saldo_utilizado = 0  # em segundos (soma novamente, confirmando o valor)

        _saldos_utilizados = OrderedDict()  # {data_saldo: ?, data_saldo: ?, ...}
        _debitos_saldos_utilizados = OrderedDict()  # {data_debito: {data_saldo: ?, data_saldo: ?}}

        for _field_name in list(self.fields.keys()):
            _saldo_utilizado = Frequencia.time_para_segundos(self.cleaned_data.get(_field_name))
            if _saldo_utilizado:
                _total_saldo_utilizado += _saldo_utilizado
                ####
                _data_debito = datetime.datetime.strptime(_field_name.split('_')[0], '%Y%m%d').date()
                _data_saldo = datetime.datetime.strptime(_field_name.split('_')[1], '%Y%m%d').date()

                if _data_saldo not in _saldos_utilizados:
                    _saldos_utilizados[_data_saldo] = 0

                if _data_debito not in _debitos_saldos_utilizados:
                    _debitos_saldos_utilizados[_data_debito] = OrderedDict()

                if _data_saldo not in _debitos_saldos_utilizados[_data_debito]:
                    _debitos_saldos_utilizados[_data_debito][_data_saldo] = 0

                _saldos_utilizados[_data_saldo] += _saldo_utilizado
                _debitos_saldos_utilizados[_data_debito][_data_saldo] += _saldo_utilizado

        if not _total_saldo_utilizado > 0:
            self.add_error(None, 'Nenhuma compensação de horário foi informada.')

        if _total_saldo_utilizado > _total_saldo:
            self.add_error(None, 'A carga horária total utilizada/distribuída é maior que o saldo total a utilizar.')

        #
        # 2) os saldos utilizados por cada débito devem ser possíveis de utilização pelo débito em questão
        # 3) o total dos saldos utilizados por cada débito deve ser menor ou igual ao débito em questão
        for _data_debito, _saldos in list(_debitos_saldos_utilizados.items()):
            _total_saldo_utilizado_pelo_debito = 0

            for _data_saldo, _saldo_utilizado in list(_saldos.items()):
                _pode_compensar = _data_saldo in self.compensacao_contexto.get_dia(_data_debito).debito_dias_dos_saldos

                if not _pode_compensar:
                    self.add_error(
                        None,
                        'O Saldo em {} não pode ser '
                        'utilizado para compensar o Débito em {}. '
                        'Saldo fora do período de compensação do Débito.'.format(_data_saldo.strftime('%d/%m/%Y'), _data_debito.strftime('%d/%m/%Y')),
                    )
                #
                _total_saldo_utilizado_pelo_debito += _saldo_utilizado

            if _data_debito in self.debitos:
                if _total_saldo_utilizado_pelo_debito > self.debitos[_data_debito]:
                    self.add_error(
                        None,
                        'O total de Saldo Utilizado para compensar o Débito em {} ({}) '
                        'é maior que o próprio Débito ({}).'.format(_data_debito.strftime('%d/%m/%Y'), _total_saldo_utilizado_pelo_debito, self.debitos[_data_debito]),
                    )
            else:
                self.add_error(None, 'O Débito em {} não foi encontrado.'.format(_data_debito.strftime('%d/%m/%Y')))
        #
        # 4) os saldos utilizados por data do saldo deve ser menor ou igual ao saldo produzido no dia em questão
        for _data_saldo, _saldo_utilizado in list(_saldos_utilizados.items()):
            if _data_saldo in self.saldos:
                if _saldo_utilizado > self.saldos[_data_saldo]:
                    self.add_error(
                        None,
                        'O total de utilização ({}) do Saldo Produzido '
                        'em {} é maior que o próprio Saldo ({}).'.format(
                            formata_segundos(_saldo_utilizado, '{h}h ', '{m}min ', '{s}seg ', True),
                            _data_saldo.strftime('%Y/%m/%d'),
                            formata_segundos(self.saldos[_data_saldo], '{h}h ', '{m}min ', '{s}seg ', True),
                        ),
                    )
            else:
                self.add_error(None, 'O Saldo em {} não foi encontrado.'.format(_data_saldo.strftime('%d/%m/%Y')))

        return _clean

    def save(self):
        # retorna uma lista das compensações salvas
        compensacoes_salvas = []

        if self.is_valid():
            _funcionario = self.request.user.get_profile().sub_instance()

            for _field_name in list(self.fields.keys()):
                _ch_compensada = self.cleaned_data.get(_field_name)

                if _ch_compensada:
                    _data_debito = datetime.datetime.strptime(_field_name.split('_')[0], '%Y%m%d').date()
                    _data_saldo = datetime.datetime.strptime(_field_name.split('_')[1], '%Y%m%d').date()

                    obs_na_data_compensacao_info_extra = ''
                    obs_na_data_aplicacao_info_extra = ''

                    if _data_debito in self.datas_recesso:
                        _recesso_escolhido = self.compensacao_contexto.get_dia(_data_debito).acompanhamentos_envolvidos_contendo_o_dia_como_debito

                        for _recesso in _recesso_escolhido:
                            # as observações terão uma informação extra sobre o recesso que está sendo compensado
                            obs_na_data_compensacao_info_extra += ' ({})'.format(_recesso.recesso_opcao)
                            obs_na_data_aplicacao_info_extra += obs_na_data_compensacao_info_extra

                    # evita duplicidade de informes que estão sendo salvos (ocorrências em jun-jul-ago de 2019)
                    # FIXME: possível gargalo !!!
                    compensacao_salva = HorarioCompensacao.objects.filter(
                        funcionario=_funcionario, data_compensacao=_data_saldo, data_aplicacao=_data_debito, ch_compensada=_ch_compensada
                    ).exists()

                    if not compensacao_salva:
                        recesso_compensacao = HorarioCompensacao()  # models.HorarioCompensacao
                        recesso_compensacao.funcionario = _funcionario
                        recesso_compensacao.data_compensacao = _data_saldo
                        recesso_compensacao.data_aplicacao = _data_debito
                        recesso_compensacao.ch_compensada = _ch_compensada

                        recesso_compensacao.save()
                        compensacoes_salvas.append(recesso_compensacao)

                        if recesso_compensacao.id:
                            # insere as observações padrões no ponto
                            obs_na_data_compensacao = '{}{}.'.format(
                                recesso_compensacao.get_auto_obs_descricao_na_data_compensacao(),
                                obs_na_data_compensacao_info_extra,  # pode ter a informação extra sobre a compensacao
                            )
                            obs_na_data_aplicacao = '{}{}.'.format(
                                recesso_compensacao.get_auto_obs_descricao_na_data_aplicacao(), obs_na_data_aplicacao_info_extra  # pode ter a informação extra sobre a compensacao
                            )
                            recesso_compensacao.save_observacao_no_ponto(descricao_na_data_compensacao=obs_na_data_compensacao, descricao_na_data_aplicacao=obs_na_data_aplicacao)

        if compensacoes_salvas:
            save_session_cache(self.request, 'total_tempo_debito_pendente_semana_anterior', get_total_tempo_debito_pendente_semana_anterior)
            save_session_cache(self.request, 'total_tempo_debito_pendente_mes_anterior', get_total_tempo_debito_pendente_mes_anterior)
            save_session_cache(self.request, 'total_tempo_debito_pendente_mes_corrente', get_total_tempo_debito_pendente_mes_corrente)
            save_session_cache(self.request, 'total_tempo_saldo_restante_mes_corrente', get_total_tempo_saldo_restante_mes_corrente)

        return compensacoes_salvas

    return type(
        'MultiplasCompensacaoHorarioFORM',
        (forms.BaseForm,),
        {
            'base_fields': fields,
            'datas_recesso': datas_recesso,
            'recessos_escolhidos': recessos_escolhidos,
            'recessos_escolhidos_pendentes': recessos_escolhidos_pendentes,
            #######
            'compensacao_contexto': compensacao_contexto,
            'periodo_envolvido_data_inicial': periodo_envolvido_data_inicial,
            'periodo_envolvido_data_final': periodo_envolvido_data_final,
            'saldos': saldos,
            'saldo_total_em_segundos': saldo_total_em_segundos,
            'saldo_total_view': formata_segundos(saldo_total_em_segundos, '{h:2d}h ', '{m:2d}min ', '{s:02d}seg ', True),
            'saldo_total_distribuido_em_segundos': saldo_total_distribuido_em_segundos,
            'saldo_total_distribuido_view': formata_segundos(saldo_total_distribuido_em_segundos, '{h:2d}h ', '{m:2d}min ', '{s:2d}seg ', True),
            'saldo_total_a_distribuir_em_segundos': saldo_total_a_distribuir_em_segundos,
            'saldo_total_a_distribuir_view': formata_segundos(saldo_total_a_distribuir_em_segundos, '{h:2d}h ', '{m:2d}min ', '{s:2d}seg ', True),
            'saldos_utilizacao': saldos_utilizacao,
            'debitos': debitos,
            'debitos_saldos_utilizacao': debitos_saldos_utilizacao,
            'debito_total_em_segundos': debito_total_em_segundos,
            'debito_total_view': formata_segundos(debito_total_em_segundos, '{h:2d}h ', '{m:2d}min ', '{s:2d}seg ', True),
            'debito_periodo_consultado_total_em_segundos': debito_periodo_consultado_total_em_segundos,
            'debito_periodo_consultado_total_view': formata_segundos(debito_periodo_consultado_total_em_segundos, '{h:2d}h ', '{m:2d}min ', '{s:2d}seg ', True),
            'debito_total_compensado_em_segundos': debito_total_compensado_em_segundos,
            'debito_total_compensado_view': formata_segundos(debito_total_compensado_em_segundos, '{h:2d}h ', '{m:2d}min ', '{s:2d}seg ', True),
            'debito_total_restante_em_segundos': debito_total_restante_em_segundos,
            'debito_total_restante_view': formata_segundos(debito_total_restante_em_segundos, '{h:2d}h ', '{m:2d}min ', '{s:2d}seg ', True),
            #######
            'add_debito_no_calendario': add_debito_no_calendario,
            'calendario': calendario,
            'frequencias_no_periodo': frequencias_no_periodo,
            'rendered': form_rendered,
            'METHOD': 'POST',
            'SUBMIT_LABEL': 'Salvar',
            '__init__': __init__,
            'media': media,
            'clean': clean,
            'save': save,
            'request': request,
        },
    )


class HorarioCompensacaoEditarObservacoesPontoForm(forms.ModelFormPlus):
    class Meta:
        model = HorarioCompensacao
        fields = ('observacoes',)


class RecessoOpcaoForm(forms.ModelFormPlus):
    qtde_max_dias_escolhidos = forms.IntegerField(
        label='Quantidade de Dias a Escolher', help_text='Número máximo de Dias que ' 'podem ser escolhidos', min_value=1, initial=1, required=False
    )

    class Meta:
        model = RecessoOpcao
        fields = ('descricao', 'publico_alvo_servidores', 'publico_alvo_campi', 'qtde_max_dias_escolhidos', 'periodo_de_escolha_data_inicial', 'periodo_de_escolha_data_final')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['publico_alvo_campi'].queryset = UnidadeOrganizacional.objects.suap().all()

    def save(self, commit=True):
        if not self.instance.id:
            self.instance.tipo = RecessoOpcao.TIPO_NATAL_ANO_NOVO
            self.instance.responsavel = self.request.user.get_profile().sub_instance()
        return super().save(commit)


class RecessoOpcaoOutroForm(forms.ModelFormPlus):
    def save(self, commit=True):
        if not self.instance.id:
            self.instance.tipo = RecessoOpcao.TIPO_OUTRO
            self.instance.responsavel = self.request.user.get_profile().sub_instance()
        return super().save(commit)

    class Meta:
        model = RecessoOpcao
        fields = ('descricao', 'publico_alvo_servidores', 'publico_alvo_campi')


class RecessoDiaAddForm(forms.ModelFormPlus):
    data_inicial = forms.DateFieldPlus(label='Data Inicial', required=False)
    data_final = forms.DateFieldPlus(label='Data Final', required=False)

    def __init__(self, *args, **kwargs):
        self.recesso_opcao = kwargs.pop('recesso_opcao', None)
        self.is_data_unica = kwargs.pop('is_data_unica', False)
        assert self.recesso_opcao is not None
        super().__init__(*args, **kwargs)

    def clean(self):
        clean = super().clean()

        data_inicial, data_final = self._clean_get_datas()

        if data_inicial and data_final:
            for data in datas_entre(data_inicial, data_final):
                if RecessoDia.objects.filter(data=data, recesso_opcao__id=self.recesso_opcao.id).exists():
                    self.add_error(None, 'Dia {} já adicionado.'.format(data.strftime('%d/%m/%Y')))

        return clean

    def _clean_get_datas(self):
        clean = self.cleaned_data

        data_inicial = clean.get('data_inicial')
        data_final = clean.get('data_final')

        if self.is_data_unica:
            if not data_inicial:
                self.add_error('data_inicial', 'Data não informada.')
            data_final = data_inicial
        else:
            if data_inicial and data_final:
                if data_inicial > data_final:
                    self.add_error('data_inicial', 'Data Inicial deve ser menor ou igual à Data Final.')
            else:
                self.add_error(None, 'Período não informado.')

        clean['data_inicial'] = data_inicial
        clean['data_final'] = data_final

        return data_inicial, data_final

    def save(self, commit=True):
        data_inicial, data_final = self._clean_get_datas()

        recesso_dia = None
        if data_inicial and data_final:
            for data in datas_entre(data_inicial, data_final):
                recesso_dia = RecessoDia()
                recesso_dia.recesso_opcao = self.recesso_opcao
                recesso_dia.data = data
                recesso_dia.save()
        return recesso_dia  # retorna o último dia salvo do período informado

    class Meta:
        model = RecessoDia
        fields = ('data_inicial', 'data_final')


class RecessoPeriodoCompensacaoAddForm(forms.ModelFormPlus):
    data_inicial = forms.DateFieldPlus(label='Data Inicial', required=False)
    data_final = forms.DateFieldPlus(label='Data Final', required=False)

    def __init__(self, *args, **kwargs):
        self.recesso_opcao = kwargs.pop('recesso_opcao', None)
        self.is_data_unica = kwargs.pop('is_data_unica', False)
        assert self.recesso_opcao is not None
        super().__init__(*args, **kwargs)

    def clean(self):
        clean = super().clean()

        data_inicial, data_final = self._clean_get_datas()

        if data_inicial and data_final:
            # período conflita com outro já cadastrado?
            pass

        return clean

    def _clean_get_datas(self):
        clean = self.cleaned_data

        data_inicial = clean.get('data_inicial')
        data_final = clean.get('data_final')

        if self.is_data_unica:
            if not data_inicial:
                self.add_error('data_inicial', 'Data não informada.')

            data_final = data_inicial
        else:
            if data_inicial and data_final:
                if data_inicial > data_final:
                    self.add_error('data_inicial', 'Data Inicial deve ser menor ou igual à Data Final.')
            else:
                self.add_error(None, 'Período não informado.')

        clean['data_inicial'] = data_inicial
        clean['data_final'] = data_final

        return data_inicial, data_final

    def save(self, commit=True):
        self.instance.recesso_opcao = self.recesso_opcao
        return super().save(commit)

    class Meta:
        model = RecessoPeriodoCompensacao
        exclude = ()


class RecessoPeriodoEscolhaForm(forms.ModelFormPlus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.instance is not None

    def clean(self):
        clean = super().clean()
        data_inicial = clean.get('periodo_de_escolha_data_inicial')
        data_final = clean.get('periodo_de_escolha_data_final')
        apenas_uma_data_foi_informada = (data_inicial and not data_final) or (not data_inicial and data_final)
        if apenas_uma_data_foi_informada:
            self.add_error(None, 'Defina as duas datas do período ou deixe-as em branco.')
        if data_inicial and data_final and data_inicial > data_final:
            self.add_error(None, 'A data inicial deve ser menor ou igual a data final.')
        return clean

    class Meta:
        model = RecessoOpcao
        fields = ('periodo_de_escolha_data_inicial', 'periodo_de_escolha_data_final')


def get_type_form_dias_escolhidos(request, recesso_opcao=None):
    """
        Etapa de escolha dos dias de recesso por parte dos funcionários/servidores (view "escolher_dia_de_recesso")

        1 field checkbox para cada instância de models.RecessoDia obtidos via parâmetro 'recesso_opcao'
    """

    _funcionario = request.user.get_relacionamento()

    # escolhendo novos dias de recesso ou modificando dias escolhidos
    modo_add = True if not recesso_opcao else False

    recessos_opcoes = RecessoOpcao.get_recessos_opcoes_com_dias_a_escolher_hoje(_funcionario)

    #
    # determina o escopo dos dias de recesso a escolher
    if modo_add:
        dias_recesso = RecessoDia.objects.filter(
            recesso_opcao__id__in=(recessos_opcoes.get('com_dias_a_escolher') | recessos_opcoes.get('com_dias_a_editar') | recessos_opcoes.get('com_dias_a_remarcar'))
        )
    else:
        dias_recesso = RecessoDia.objects.filter(
            recesso_opcao=recesso_opcao,
            recesso_opcao__id__in=(recessos_opcoes.get('com_dias_a_editar') | recessos_opcoes.get('com_dias_a_remarcar') | recessos_opcoes.get('com_dias_que_ainda_pode_editar')),
        )

    fields = {}  # {'fieldname': field}
    fieldsets = {}  # {'opcao_recesso_id': ('opção de recesso', {'fields': ['fieldname', ...]}), ...}
    for _dia_recesso in dias_recesso:
        _dia_recesso_eh_disponivel = True
        if _dia_recesso_eh_disponivel:
            _dia_recesso_ja_escolhido = RecessoDiaEscolhido.objects.filter(
                recesso_opcao_escolhida__funcionario=_funcionario, recesso_opcao_escolhida__recesso_opcao=_dia_recesso.recesso_opcao, dia=_dia_recesso
            )
            fieldname = 'dia_recesso_{}'.format(_dia_recesso.id)
            fields[fieldname] = forms.BooleanField(label='Dia {}'.format(_dia_recesso.data.strftime('%d/%m/%Y')), required=False, initial=_dia_recesso_ja_escolhido.exists())
            if _dia_recesso.recesso_opcao.id not in fieldsets:
                mensagem_qtd_dias_a_escolher = '<span class="status status-alert inline">'
                if _dia_recesso.recesso_opcao.qtde_max_dias_escolhidos == 1:
                    mensagem_qtd_dias_a_escolher += 'Atenção: Você pode escolher somente <strong>1 dia</strong>. '
                else:
                    mensagem_qtd_dias_a_escolher += 'Atenção: Você pode escolher até <strong>{} dias</strong>. '.format(_dia_recesso.recesso_opcao.qtde_max_dias_escolhidos)
                mensagem_qtd_dias_a_escolher += 'Prazo final: <strong>{}</span></strong>'.format(_dia_recesso.recesso_opcao.periodo_de_escolha_data_final.strftime('%d/%m/%Y'))

                title_fieldset = '{} {} '.format(_dia_recesso.recesso_opcao, mensagem_qtd_dias_a_escolher)

                if _dia_recesso_ja_escolhido.exists():
                    _recesso_opcao_escolhida = _dia_recesso_ja_escolhido[0].recesso_opcao_escolhida
                    if _recesso_opcao_escolhida.validacao == RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR:
                        title_fieldset += (
                            ' <span class="status status-rejeitado inline">'
                            'Validação: {} (Motivo: {})</span>'
                            ''.format(_recesso_opcao_escolhida.get_validacao_display(), _recesso_opcao_escolhida.motivo_nao_autorizacao)
                        )
                fieldsets[_dia_recesso.recesso_opcao.id] = (title_fieldset, {'fields': []})
            fieldsets[_dia_recesso.recesso_opcao.id][1]['fields'].append(fieldname)

    # confirmar o chefe imediato/validador
    for fieldset_recesso_opcao_id in list(fieldsets.keys()):
        escolha = RecessoOpcaoEscolhida.objects.filter(funcionario=_funcionario, recesso_opcao__id=fieldset_recesso_opcao_id)

        if escolha.exists():
            minha_escolha = escolha[0]
            chefes = minha_escolha.chefes  # instâncias de rh.Funcionario

            if minha_escolha.validador:
                # pode ser um validador que tenha sido escolhido (força bruta) pelo superusuario
                chefes = chefes | Funcionario.objects.filter(id=minha_escolha.validador.id)
        else:
            # escolha fake (para hoje)
            minha_escolha = RecessoOpcaoEscolhida(funcionario=_funcionario, data_escolha=datetime.date.today())
            chefes = minha_escolha.chefes
            try:
                minha_escolha.validador = chefes[0].sub_instance()  # sugere o primeiro da lista
            except Exception:
                pass

        field_queryset = Servidor.objects.filter(id__in=[chefe.id for chefe in chefes])
        field_initial = minha_escolha.validador

        fieldname = 'validador_chefe_imediato_{}'.format(fieldset_recesso_opcao_id)

        fields[fieldname] = forms.ModelChoiceField(label='Chefe Imediato/Validador', required=False, queryset=field_queryset, initial=field_initial.id if field_initial else None)

        fieldsets[fieldset_recesso_opcao_id][1]['fields'].insert(0, fieldname)

    if not fields:
        mensagem_erro = 'Não há dias disponíveis para escolher ou modificar. '
        raise ValidationError(mensagem_erro)

    fieldsets = list(fieldsets.values())

    def clean(self):
        funcionario = self.request.user.get_relacionamento()
        totais_dias_escolhidos = {}
        for field_name in list(self.fields.keys()):
            dia_foi_escolhido = self.cleaned_data[field_name]  # True ou False
            if dia_foi_escolhido:
                dia_recesso_id = field_name.split('dia_recesso_')
                if len(dia_recesso_id) > 1:
                    dia_recesso_id = dia_recesso_id[1]
                    dia_recesso = RecessoDia.objects.filter(id=dia_recesso_id)
                    if dia_recesso.exists():
                        dia_recesso = dia_recesso[0]
                        # o funcionário pode escolher esse dia? Se for útil para ele, sim.
                        is_dia_util = HorarioCompensacao.is_dia_util(funcionario.get_vinculo(), dia_recesso.data)
                        if not is_dia_util[0]:
                            self.add_error(field_name, 'Não é um dia útil para você: {}'.format('. '.join(is_dia_util[1])))
                        #
                        _recesso_opcao = dia_recesso.recesso_opcao
                        if _recesso_opcao.id not in totais_dias_escolhidos:
                            # {recesso_opcao_id: [recesso_opcao, qtd_max_dias_a_escolher, qtd_dias_escolhidos], ...}
                            totais_dias_escolhidos[_recesso_opcao.id] = [_recesso_opcao, _recesso_opcao.qtde_max_dias_escolhidos, 0]
                        totais_dias_escolhidos[_recesso_opcao.id][2] += 1  # incrementa qtde de dias escolhidos

        if totais_dias_escolhidos:
            # clean na quantidade de dias escolhidos
            for _recesso_opcao_id in list(totais_dias_escolhidos.keys()):
                _recesso_opcao = totais_dias_escolhidos[_recesso_opcao_id][0]
                _qtd_max_dias_a_escolher = totais_dias_escolhidos[_recesso_opcao_id][1]
                _qtd_dias_escolhidos = totais_dias_escolhidos[_recesso_opcao_id][2]
                if _qtd_dias_escolhidos > _qtd_max_dias_a_escolher:
                    self.add_error(None, 'Recesso \'{}\': Você pode escolher, no máximo, {} dia(s).'.format(_recesso_opcao, _qtd_max_dias_a_escolher))
        else:
            self.add_error(None, 'Você não escolheu nenhum dia.')

        return self.cleaned_data

    def save(self):
        funcionario = self.request.user.get_profile().sub_instance()
        novas_recesso_opcoes_escolhidas = []
        for field_name in list(self.fields.keys()):
            dia_recesso_id = field_name.split('dia_recesso_')
            if len(dia_recesso_id) > 1:
                dia_recesso_id = dia_recesso_id[1]
                dia_recesso = RecessoDia.objects.filter(id=dia_recesso_id)
                if dia_recesso.exists():
                    dia_recesso = dia_recesso[0]
                    #
                    # opção de recesso escolhida
                    recesso_opcao_escolhida = RecessoOpcaoEscolhida.objects.filter(funcionario=funcionario, recesso_opcao=dia_recesso.recesso_opcao)
                    if recesso_opcao_escolhida.exists():
                        # edita a opção de recesso escolhida
                        recesso_opcao_escolhida = recesso_opcao_escolhida[0]
                        recesso_opcao_escolhida.data_escolha = datetime.date.today()
                        recesso_opcao_escolhida.validacao = RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO
                        # validador
                        chefe_imediato_fieldname = 'validador_chefe_imediato_{}'.format(dia_recesso.recesso_opcao.id)
                        if chefe_imediato_fieldname in self.cleaned_data:
                            recesso_opcao_escolhida.validador = self.cleaned_data[chefe_imediato_fieldname]
                        recesso_opcao_escolhida.motivo_nao_autorizacao = ''
                        recesso_opcao_escolhida.save()
                    else:
                        # salva uma nova opção de recesso escolhida
                        recesso_opcao_escolhida = RecessoOpcaoEscolhida()
                        recesso_opcao_escolhida.funcionario = funcionario
                        recesso_opcao_escolhida.recesso_opcao = dia_recesso.recesso_opcao
                        # validador
                        chefe_imediato_fieldname = 'validador_chefe_imediato_{}'.format(dia_recesso.recesso_opcao.id)
                        if chefe_imediato_fieldname in self.cleaned_data:
                            recesso_opcao_escolhida.validador = self.cleaned_data[chefe_imediato_fieldname]
                        recesso_opcao_escolhida.save()
                        novas_recesso_opcoes_escolhidas.append(recesso_opcao_escolhida)
                    #
                    dia_escolhido = self.cleaned_data[field_name]  # True ou False
                    dia_escolhido_salvo = RecessoDiaEscolhido.objects.filter(
                        recesso_opcao_escolhida__funcionario=funcionario, recesso_opcao_escolhida__recesso_opcao=dia_recesso.recesso_opcao, dia=dia_recesso
                    )
                    if dia_escolhido:
                        if not dia_escolhido_salvo.exists():  # ainda não foi salvo?
                            # salva o dia escolhido
                            dia_recesso_escolhido = RecessoDiaEscolhido()
                            dia_recesso_escolhido.recesso_opcao_escolhida = recesso_opcao_escolhida
                            dia_recesso_escolhido.dia = dia_recesso
                            dia_recesso_escolhido.save()
                    else:
                        # o dia não foi escolhido
                        if dia_escolhido_salvo.exists():  # mas já foi salvo anteriormente
                            # remove o dia escolhido
                            dia_escolhido_salvo[0].delete()
        #
        # não escolher nenhum dia de uma nova opção de recesso equivale a excluir essa opção de recesso
        for nova_recesso_opcao_escolhida in novas_recesso_opcoes_escolhidas:
            if not nova_recesso_opcao_escolhida.dias_escolhidos.all().exists():
                nova_recesso_opcao_escolhida.delete()  # não marcou nenhum dia na nova opção de recesso

    return type(
        'RecessoDiaEscolhidoForm',
        (forms.BaseForm,),
        {
            'base_fields': fields,
            'fieldsets': fieldsets,
            'METHOD': 'POST',
            'SUBMIT_LABEL': 'Salvar',
            'save': save,
            'clean': clean,
            'request': request,
            'ha_dias_disponiveis_para_escolha': True if fields else False,
        },
    )


class RecessoOpcaoEscolhidaValidarForm(forms.ModelFormPlus):
    """ Validação do chefe imediato de uma opção de recesso escolhida por um funcionário/servidor.
        Um e-mail de notificação será enviado ao funcionário/servidor.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # redefine as opções de validação, removendo a opção 'Aguardando'
        self.fields['validacao'].choices = RecessoOpcaoEscolhida.VALIDACAO_CHOICES[1:]

    def clean(self):
        clean = super().clean()
        validacao = self.cleaned_data.get('validacao')
        if validacao:
            if int(validacao) in [RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO, RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR]:
                motivo_nao_autorizacao = self.cleaned_data.get('motivo_nao_autorizacao')
                if not motivo_nao_autorizacao:
                    self.add_error('motivo_nao_autorizacao', 'Informe o motivo da não autorização.')
        else:
            self.add_error('validacao', 'Informe a validação.')
        return clean

    def save(self, commit=True):
        if self.is_valid():
            validacao = int(self.cleaned_data.get('validacao'))

            if validacao in [RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO, RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO, RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR]:
                self.instance.validador = self.request.user.get_profile().sub_instance()
                if validacao == RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO:
                    self.cleaned_data['motivo_nao_autorizacao'] = ''
            else:
                self.cleaned_data['motivo_nao_autorizacao'] = ''

            self.instance.dias_efetivos_a_compensar_cache = ''  # atualiza dias_efetivos_a_compensar
            save = super().save(commit)

            if save:
                # envia o email
                self.instance.notifica_validacao()
            return save
        return None

    class Meta:
        model = RecessoOpcaoEscolhida
        fields = ('validacao', 'motivo_nao_autorizacao')


class RecessoPeriodoCompensacaoAdminForm(forms.ModelFormPlus):
    class Meta:
        model = RecessoPeriodoCompensacao
        fields = ('data_inicial', 'data_final')


class RecessoDiaAdminForm(forms.ModelFormPlus):
    class Meta:
        model = RecessoDia
        fields = ('data',)


class HorarioCompensacaoPeriodoForm(forms.FormPlus):
    class Media:
        js = ('/static/js/ponto-util.js',)

    data_inicio = DateFieldPlus(label='Data Início', initial=datetime.date.today())
    data_fim = DateFieldPlus(label='Data Fim', initial=datetime.date.today())

    def clean(self):
        clean = super().clean()

        if 'data_fim' in clean and 'data_inicio' in clean:
            if clean['data_fim'] < clean['data_inicio']:
                self.add_error('data_fim', 'Data Fim deve ser maior ou igual à Data Início.')

        return clean


class RecessoOpcaoEscolhidaEditarChefeForm(forms.ModelFormPlus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['validador'].label = 'Chefe Imediato/Validador'
        self.fields['validador'].queryset = Servidor.objects.filter(id__in=[chefe.id for chefe in self.instance.chefes])

    class Meta:
        model = RecessoOpcaoEscolhida
        fields = ('validador',)
        widgets = {'validador': forms.Select}


class LocalizarServidorForm(forms.FormPlus):
    servidor = forms.ModelChoiceFieldPlus(label='Servidor', queryset=Servidor.objects)


class RecessoOpcaoEscolhidaEditarForm(forms.ModelFormPlus):
    class Meta:
        model = RecessoOpcaoEscolhida
        exclude = ()


class DocumentoAnexoForm(forms.ModelFormPlus):
    class Meta:
        model = DocumentoAnexo
        fields = ('descricao', 'anexo')

    def __init__(self, *args, **kwargs):
        vinculo = kwargs.pop('vinculo')
        data = kwargs.pop('data')
        super().__init__(*args, **kwargs)

        self.instance.vinculo = vinculo
        self.instance.data = data

    def clean_anexo(self):
        arquivo = self.cleaned_data['anexo']
        filename = hashlib.md5('{}{}{}'.format(self.instance.vinculo.id, self.instance.data, datetime.datetime.now()).encode()).hexdigest()
        filename += '{}'.format(arquivo.name[arquivo.name.rfind('.'):])

        arquivo.name = filename

        return self.cleaned_data['anexo']


class DocumentoAnexoChangeForm(forms.ModelFormPlus):
    class Meta:
        model = DocumentoAnexo
        fields = ('descricao',)
