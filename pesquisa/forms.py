import datetime
import re
from decimal import Decimal

from ckeditor.fields import RichTextFormField
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.forms.models import ModelChoiceField

from cnpq.models import GrupoPesquisa, CurriculoVittaeLattes
from comum.models import Configuracao, TrocarSenha, PrestadorServico, User, UsuarioGrupo, Ano, Vinculo, Sala, \
    EstadoCivil, Pais
from comum.utils import get_uo, get_setor_propi
from djtools import forms
from djtools.forms import MultiFileField
from djtools.forms.widgets import AutocompleteWidget, FilteredSelectMultiplePlus
from djtools.templatetags.filters import format_
from djtools.utils import send_mail
from edu.models import Aluno, Cidade, Disciplina
from pesquisa.models import (
    Participacao,
    Meta,
    Etapa,
    Desembolso,
    Edital,
    Recurso,
    ItemMemoriaCalculo,
    EditalAnexo,
    EditalAnexoAuxiliar,
    RegistroExecucaoEtapa,
    RegistroGasto,
    RegistroConclusaoProjeto,
    FotoProjeto,
    CriterioAvaliacao,
    Avaliacao,
    ItemAvaliacao,
    ProjetoHistoricoDeEnvio,
    BolsaDisponivel,
    Projeto,
    TipoVinculo,
    ComissaoEditalPesquisa,
    AvaliadorExterno,
    RecursoProjeto,
    ProjetoCancelado,
    EditalArquivo,
    EditalSubmissaoObra,
    Obra,
    LinhaEditorial,
    MembroObra,
    ParecerObra,
    PessoaExternaObra,
    ProjetoAnexo,
    HistoricoEquipe,
    LaboratorioPesquisa,
    EquipamentoLaboratorioPesquisa,
    FotoLaboratorioPesquisa,
    AreaConhecimentoParecerista,
    OrigemRecursoEdital,
    SolicitacaoAlteracaoEquipe,
    RegistroFrequencia,
    ServicoLaboratorioPesquisa,
    MaterialLaboratorioPesquisa,
    SolicitacaoServicoLaboratorio,
    FinalidadeServicoLaboratorio,
    MaterialConsumoPesquisa, ColaboradorExterno, ProgramaPosGraduacao, RelatorioProjeto,
)
from rh.enums import Nacionalidade
from rh.models import UnidadeOrganizacional, Servidor, AreaConhecimento, Titulacao, Setor, Instituicao
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms.widgets import PasswordInput
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate


class ConfiguracaoForm(forms.FormPlus):
    setor_propi = forms.ModelChoiceFieldPlus(
        Setor.objects, label='Setor da Pró-Reitoria', required=False, help_text='Os avaliadores externos de projetos de pesquisa serão vinculados automaticamente à este setor'
    )
    nome_propi = forms.CharFieldPlus(label='Nome da Pró-Reitoria', required=False, help_text='Este nome será exibido nos relatórios gerados no módulo de pesquisa')


class BuscaProjetoForm(forms.FormPlus):
    palavra_chave = forms.CharField(label='Palavra-chave', required=False)
    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    edital = forms.ModelChoiceField(Edital.objects.order_by('-inicio_inscricoes'), required=False)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=False)
    METHOD = 'GET'

    class Media:
        js = ['/static/pesquisa/js/meusprojetosform.js']

    def __init__(self, *args, **kwargs):
        self.ano = kwargs.pop('ano', None)
        super().__init__(*args, **kwargs)

        if self.request.user.groups.filter(name='Coordenador de Pesquisa') and not self.request.user.groups.filter(name='Avaliador Sistêmico de Projetos de Pesquisa'):
            self.fields['edital'].queryset = Edital.objects.finalizados()
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.uo().filter(id=get_uo(self.request.user).id)
        self.fields['uo'].initial = get_uo(self.request.user).id

        ANO_CHOICES = []
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')

        if editais:
            ANO_CHOICES.append(['', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            for ano in range(ano_limite, ano_inicio, -1):
                ANO_CHOICES.append([str(ano), str(ano)])
        else:
            ANO_CHOICES.append(['Selecione um ano', 'Nenhum edital cadastrado'])

        self.fields['ano'].choices = ANO_CHOICES
        if self.ano:
            self.fields['edital'].queryset = Edital.objects.filter(inicio_inscricoes__year=self.ano)


class RegistroConclusaoProjetoForm(forms.ModelFormPlus):
    class Meta:
        model = RegistroConclusaoProjeto
        exclude = ['projeto', 'dt_avaliacao', 'avaliador', 'aprovado', 'obs_avaliador']


class EditalForm(forms.ModelFormPlus):
    participa_aluno = forms.BooleanField(
        label='Participação de Aluno Obrigatória', help_text='Marque esta opção caso seja obrigatória a participação de aluno em todos os projetos', required=False, initial=True
    )
    participa_servidor = forms.BooleanField(
        label='Participação de Servidor Obrigatória',
        help_text='Marque esta opção caso seja obrigatória a participação de servidor em todos os projetos',
        required=False,
        initial=True,
    )
    titulacoes_avaliador = forms.ModelMultipleChoiceField(
        queryset=Titulacao.objects,
        label='Titulações dos Avaliadores',
        required=False,
        widget=FilteredSelectMultiplePlus('', True),
        help_text='Selecione quais titulações serão permitidas para os avaliadores deste edital.',
    )

    inicio_pre_selecao = forms.DateTimeFieldPlus(label='Início da Pré-Seleção', required=False)
    inicio_selecao = forms.DateTimeFieldPlus(label='Início da Seleção', required=False)
    fim_selecao = forms.DateTimeFieldPlus(label='Fim da Seleção', required=False)
    divulgacao_selecao = forms.DateTimeFieldPlus(label='Divulgação da Seleção', required=False)

    class Meta:
        model = Edital
        exclude = ('data_avaliacao_classificacao',)

    class Media:
        js = ['/static/pesquisa/js/editalform.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['titulacoes_avaliador'].queryset = Titulacao.objects.all()
        self.fields[
            'formato'
        ].help_text = 'Edital com formato simplificado não possui as fases de pré-seleção e seleção. Este tipo de formato é ideal para cadastro de projetos com fomento externo ou para registros de projetos executados em anos anteriores.'

        if self.instance.tipo_edital:
            self.fields['tipo_edital'].initial = self.instance.tipo_edital
            self.fields['tipo_edital'].widget.attrs.update(readonly='readonly')

    def clean(self):
        if self.cleaned_data.get('inicio_inscricoes') and self.cleaned_data.get('fim_inscricoes') and self.cleaned_data['fim_inscricoes'] <= self.cleaned_data['inicio_inscricoes']:
            raise forms.ValidationError('A data do fim das inscrições deve ser maior que a data do início das inscrições.')
        if self.cleaned_data.get('prazo_avaliacao') and not self.cleaned_data.get('prazo_aceite_indicacao'):
            self.add_error('prazo_aceite_indicacao', 'É necessário informar o prazo para aceite nos casos em que há prazo para avaliação.')
        if self.cleaned_data.get('formato') == Edital.FORMATO_COMPLETO:

            if not self.cleaned_data.get('titulacoes_avaliador'):
                self.add_error('titulacoes_avaliador', 'Este campo é obrigatório.')

            if not self.cleaned_data.get('inicio_pre_selecao'):
                self.add_error('inicio_pre_selecao', 'Preenchimento obrigatório.')

            if not self.cleaned_data.get('inicio_selecao'):
                self.add_error('inicio_selecao', 'Preenchimento obrigatório.')

            if not self.cleaned_data.get('fim_selecao'):
                self.add_error('fim_selecao', 'Preenchimento obrigatório.')

            if not self.cleaned_data.get('divulgacao_selecao'):
                self.add_error('divulgacao_selecao', 'Preenchimento obrigatório.')

            if self.cleaned_data.get('tipo_edital') and not self.cleaned_data['tipo_edital'] == Edital.PESQUISA_INOVACAO_CONTINUO:
                if (
                    self.cleaned_data.get('inicio_pre_selecao')
                    and self.cleaned_data.get('fim_inscricoes')
                    and self.cleaned_data['inicio_pre_selecao'] <= self.cleaned_data['fim_inscricoes']
                ):
                    raise forms.ValidationError('A data da pré-seleção deve ser maior que a data do fim das inscrições.')
                if (
                    self.cleaned_data.get('inicio_pre_selecao')
                    and self.cleaned_data.get('inicio_selecao')
                    and self.cleaned_data['inicio_selecao'] <= self.cleaned_data['inicio_pre_selecao']
                ):
                    raise forms.ValidationError('A data da seleção deve ser maior que a data da pré-seleção.')
                if (
                    self.cleaned_data.get('inicio_selecao')
                    and self.cleaned_data.get('divulgacao_selecao')
                    and self.cleaned_data['divulgacao_selecao'] <= self.cleaned_data['inicio_selecao']
                ):
                    raise forms.ValidationError('A data da divulgação deve ser maior que a data da seleção.')
                if (
                    self.cleaned_data.get('data_recurso')
                    and self.cleaned_data.get('divulgacao_selecao')
                    and self.cleaned_data['divulgacao_selecao'] <= self.cleaned_data['data_recurso']
                ):
                    raise forms.ValidationError('A data da divulgação deve ser maior que a data limite para interpor recurso.')

            if (
                self.cleaned_data.get('qtd_maxima_alunos_bolsistas')
                and self.cleaned_data.get('qtd_maxima_alunos')
                and self.cleaned_data['qtd_maxima_alunos_bolsistas'] > self.cleaned_data['qtd_maxima_alunos']
            ):
                raise forms.ValidationError('A quantidade de alunos bolsistas não pode ser maior que a quantidade máxima de alunos.')

            if (
                self.cleaned_data.get('qtd_maxima_servidores_bolsistas')
                and self.cleaned_data.get('qtd_maxima_servidores')
                and self.cleaned_data['qtd_maxima_servidores_bolsistas'] > self.cleaned_data['qtd_maxima_servidores']
            ):
                raise forms.ValidationError('A quantidade de servidores bolsistas não pode ser maior que a quantidade máxima de servidores.')

            if self.cleaned_data.get('participa_aluno') and self.cleaned_data.get('qtd_maxima_alunos') and (self.cleaned_data.get('qtd_maxima_alunos') == 0):
                raise forms.ValidationError('Quando a participação de aluno é obrigatória, é preciso informar a quantidade máxima de alunos.')

            if self.cleaned_data.get('participa_servidor') and self.cleaned_data.get('qtd_maxima_servidores') and (self.cleaned_data.get('qtd_maxima_servidores') == 0):
                raise forms.ValidationError('Quando a participação de servidor é obrigatória, é preciso informar a quantidade máxima de servidores.')

            if not self.cleaned_data.get('peso_avaliacao_lattes_coordenador') and not self.cleaned_data.get('peso_avaliacao_projeto') and not self.cleaned_data.get('peso_avaliacao_grupo_pesquisa'):
                raise forms.ValidationError('Informe os pesos do currículo do coordenador, pontuação do projeto e do grupo de pesquisa.')

        return super().clean()


class RecursoForm(forms.ModelFormPlus):
    origem_recurso = forms.ModelChoiceField(OrigemRecursoEdital.objects.filter(ativo=True), label='Origem')

    class Meta:
        model = Recurso
        fields = ('origem_recurso', 'valor', 'despesa')


class CriterioAvaliacaoForm(forms.ModelFormPlus):
    class Meta:
        model = CriterioAvaliacao
        exclude = ('edital',)


class EditalAnexoForm(forms.ModelFormPlus):
    class Meta:
        model = EditalAnexo
        exclude = ('edital',)


class EditalAnexoAuxiliarForm(forms.ModelFormPlus):
    class Meta:
        model = EditalAnexoAuxiliar
        exclude = ('edital', 'arquivo')


class OfertaProjetoPesquisaFormMultiplo(forms.FormPlus):
    campi = forms.MultipleModelChoiceFieldPlus(label='Campi', queryset=UnidadeOrganizacional.objects.uo().all(), widget=FilteredSelectMultiplePlus('', True), required=True)
    num_maximo_ic = forms.IntegerFieldPlus(label='Bolsas de Iniciação Científica', help_text='Informe o número máximo de Bolsas de Iniciação Científica.', required=False)
    num_maximo_pesquisador = forms.IntegerFieldPlus(label='Bolsas para Pesquisador', help_text='Informe o número máximo de Bolsas para Pesquisador.', required=False)

    def __init__(self, *args, **kwargs):
        self.edital = kwargs.pop("edital", None)
        super().__init__(*args, **kwargs)
        self.fields['num_maximo_ic'].initial = 0
        self.fields['num_maximo_pesquisador'].initial = 0
        if self.edital.forma_selecao == Edital.GERAL or not self.edital.tem_formato_completo():
            self.fields['num_maximo_ic'].widget = forms.HiddenInput()
            self.fields['num_maximo_pesquisador'].widget = forms.HiddenInput()

        if self.request.user.groups.filter(name='Coordenador de Pesquisa') and not self.request.user.groups.filter(name='Diretor de Pesquisa'):
            self.fields['campi'].queryset = UnidadeOrganizacional.objects.uo().filter(id=get_uo(self.request.user).id)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.edital.tem_formato_completo():
            if self.cleaned_data.get('num_maximo_ic') is None or self.cleaned_data.get('num_maximo_pesquisador') is None:
                raise forms.ValidationError('Informe o número máximo de bolsas.')

        return cleaned_data


class OfertaProjetoPesquisaForm(forms.ModelFormPlus):
    uo = forms.ModelChoiceFieldPlus(UnidadeOrganizacional.objects.uo(), label='Campus', required=False)

    class Meta:
        model = BolsaDisponivel
        fields = ['uo', 'num_maximo_ic', 'num_maximo_pesquisador']


class ItemMemoriaCalculoForm(forms.ModelFormPlus):
    class Meta:
        model = ItemMemoriaCalculo
        exclude = ('projeto', 'data_cadastro')


class ProjetoForm(forms.ModelFormPlus):
    edital = forms.ModelChoiceField(queryset=Edital.objects, widget=AutocompleteWidget(search_fields=Edital.SEARCH_FIELDS, readonly=True))
    area_conhecimento = forms.ModelChoiceField(AreaConhecimento.objects, label='Área do Conhecimento', required=True)
    grupo_pesquisa = forms.ModelChoiceField(GrupoPesquisa.objects, label='Grupo de Pesquisa', required=True)
    ppg = forms.ModelChoiceField(ProgramaPosGraduacao.objects, label='Programa de Pós-Graduação Vinculado', required=False)
    deseja_receber_bolsa = forms.BooleanField(label='O Coordenador Receberá Bolsa?', required=False, initial=True)
    fundamentacao_teorica = RichTextFormField(label='Fundamentação Teórica')
    referencias_bibliograficas = RichTextFormField(label='Referências Bibliográficas')
    introducao = RichTextFormField(label='Introdução')
    termo_compromisso_coordenador = RichTextFormField(label='Termo de Compromisso', required=False)
    aceita_termo = forms.BooleanField(label='Aceito o Termo de Compromisso', required=False, initial=False)

    class Meta:
        model = Projeto
        exclude = (
            'data_conclusao_planejamento',
            'cota_bolsa_aluno',
            'cota_bolsa_pesquisador',
            'pontuacao_curriculo',
            'pontuacao_curriculo_normalizado',
            'pontuacao_grupo_pesquisa',
            'pontuacao_grupo_pesquisa_normalizado',
            'pontuacao_total',
        )

    fieldsets = (
        (None, {'fields': ('edital', 'uo', 'titulo', 'valor_global_projeto')}),
        ('Dados do Projeto', {'fields': ('inicio_execucao', 'fim_execucao', 'deseja_receber_bolsa', 'area_conhecimento', 'grupo_pesquisa', 'ppg', 'parceria_externa', 'palavras_chaves')}),
        (
            'Descrição do Projeto',
            {
                'fields': (
                    'resumo',
                    'introducao',
                    'justificativa',
                    'fundamentacao_teorica',
                    'objetivo_geral',
                    'metodologia',
                    'acompanhamento_e_avaliacao',
                    'resultados_esperados',
                    'referencias_bibliograficas',
                    'termo_compromisso_coordenador',
                    'aceita_termo',
                )
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.edital = kwargs.pop("edital", None)
        grupo_pesquisa_online = kwargs.pop("grupo_pesquisa_online", None)
        super().__init__(*args, **kwargs)
        self.fields['palavras_chaves'].required = True
        ids_campi = []

        if self.user.get_relacionamento().setor_lotacao is not None:
            if self.user.get_relacionamento().setor_lotacao.uo.equivalente:
                ids_campi.append(self.user.get_relacionamento().setor_lotacao.uo.equivalente.id)
            else:
                ids_campi.append(self.request.user.get_relacionamento().setor_lotacao.uo.id)

        if self.user.get_relacionamento().setor is not None:
            ids_campi.append(self.user.get_relacionamento().setor.uo.id)

        campus = self.instance.edital.get_uos_edital_pesquisa()
        self.fields['resumo'].help_text = ''
        self.fields['objetivo_geral'].help_text = ''
        self.fields['metodologia'].help_text = ''
        self.fields['resultados_esperados'].help_text = ''
        self.fields['justificativa'].help_text = 'Informe a justificativa e a motivação para o desenvolvimento do projeto.'
        if self.instance.uo_id:
            self.fields['uo'].widget.original_value = self.instance.uo
        else:
            self.fields['uo'].queryset = campus.filter(id__in=ids_campi)
        self.fields['area_conhecimento'].queryset = AreaConhecimento.objects.filter(superior__isnull=False).order_by('descricao')

        if not self.instance.pk or self.user.groups.filter(name='Diretor de Pesquisa').exists():
            self.fields.pop('pre_aprovado')
            self.fields.pop('data_pre_avaliacao')
            self.fields.pop('aprovado')
            self.fields.pop('data_avaliacao')
            self.fields.pop('pontuacao')

        self.fields['grupo_pesquisa'].help_text = (
            'Se seu grupo de pesquisa não consta na listagem, <a class="confirm" data-confirm="Ao sair desta página, os'
            ' dados digitados serão perdidos. Deseja Continuar?" href="/pesquisa/atualizar_grupos_de_pesquisa/"> '
            'atualize seus Grupos de Pesquisa. </a>'
        )

        self.fields['grupo_pesquisa'].required = grupo_pesquisa_online and self.instance.edital.exige_grupo_pesquisa
        curriculo = CurriculoVittaeLattes.objects.filter(vinculo=self.user.get_vinculo())
        if curriculo.exists():
            instituicao_sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
            self.fields['grupo_pesquisa'].queryset = curriculo[0].grupos_pesquisa.filter(instituicao=instituicao_sigla).order_by('descricao')
        else:
            if self.instance.grupo_pesquisa:
                self.fields['grupo_pesquisa'].initial = self.instance.grupo_pesquisa
            else:
                del self.fields['grupo_pesquisa']
        self.fields['resultados_esperados'].label = 'Resultados Esperados'
        self.fields['area_conhecimento'].required = True

        if self.instance.pk:
            instance = self.instance
        else:
            instance = self

        if not instance.edital.coordenador_pode_receber_bolsa:
            self.fields['deseja_receber_bolsa'].initial = False
            self.fields['deseja_receber_bolsa'].widget = forms.Select(attrs=dict(readonly='readonly'))
            self.fields['deseja_receber_bolsa'].help_text = 'Este edital não prevê bolsa para coordenador.'

        if self.user.get_relacionamento().funcao:
            if self.user.get_relacionamento().funcao.codigo == 'CD':
                self.fields['deseja_receber_bolsa'].initial = False
                self.fields['deseja_receber_bolsa'].widget = forms.Select(attrs=dict(readonly='readonly'))
                self.fields['deseja_receber_bolsa'].help_text = 'Servidor com cargo de direção não pode receber bolsa.'

        if (
            self.edital
            and not self.edital.permite_coordenador_com_bolsa_previa
            and Participacao.objects.filter(
                projeto__aprovado=True,
                vinculo=TipoVinculo.BOLSISTA,
                bolsa_concedida=True,
                ativo=True,
                vinculo_pessoa=self.user.get_vinculo(),
                projeto__fim_execucao__gte=datetime.datetime.now(),
            ).exists()
        ):
            self.fields['deseja_receber_bolsa'].initial = False
            self.fields['deseja_receber_bolsa'].widget = forms.Select(attrs=dict(readonly='readonly'))
            self.fields['deseja_receber_bolsa'].help_text = 'Já existe uma bolsa de projeto em outro edital vinculado a este coordenador.'

        if self.instance.pk:
            self.fields['fundamentacao_teorica'].initial = self.instance.fundamentacao_teorica
            self.fields['referencias_bibliograficas'].initial = self.instance.referencias_bibliograficas
            self.fields['introducao'].initial = self.instance.introducao
            coordenador_projeto = Participacao.objects.filter(projeto=self.instance, responsavel=True)
            if coordenador_projeto[0].vinculo == TipoVinculo.VOLUNTARIO:
                self.fields['deseja_receber_bolsa'].initial = False
            else:
                self.fields['deseja_receber_bolsa'].initial = True
            del self.fields['termo_compromisso_coordenador']
            del self.fields['aceita_termo']

        if self.instance.pk and self.user.groups.filter(name='Diretor de Pesquisa').exists():
            self.fieldsets = self.fieldsets + (
                ('Seleção', {'fields': ('pre_aprovado', 'data_pre_avaliacao', 'aprovado', 'data_avaliacao', 'pontuacao')}),
            )

        if not self.instance.pk and not self.edital.termo_compromisso_coordenador:
            del self.fields['termo_compromisso_coordenador']
            del self.fields['aceita_termo']

        elif not self.instance.pk:
            self.fields['termo_compromisso_coordenador'].initial = self.edital.termo_compromisso_coordenador
            self.fields['termo_compromisso_coordenador'].widget.attrs['readonly'] = True

        if self.edital.tem_formato_completo():
            del self.fields['valor_global_projeto']
        self.fields['ppg'].queryset = ProgramaPosGraduacao.objects.filter(ativo=True)
        self.fields['ppg'].help_text = 'Caso o projeto seja vinculado à um Programa de Pós-Graduação da Instituição, selecione o Programa.'
        self.fields['parceria_externa'].required = False
        self.fields['parceria_externa'].help_text = 'Caso o projeto possua parceria externa, informe o nome do Programa/Instituição.'

    def clean(self, *args, **kwargs):
        if not self.instance.pk and self.edital.termo_compromisso_coordenador and not self.cleaned_data['aceita_termo']:
            raise forms.ValidationError('Você precisa aceitar o termo de compromisso para submeter o projeto.')

        if not self.user.groups.filter(name='Diretor de Pesquisa'):
            if self.instance and self.instance.data_pre_avaliacao and not self.instance.get_status() == Projeto.STATUS_EM_INSCRICAO:
                raise forms.ValidationError('O projeto já foi pré-avaliado')
            if self.instance.participacao_set.count() and not Participacao.objects.filter(responsavel=True, vinculo_pessoa=self.user.get_vinculo()):
                raise forms.ValidationError('Apenas o coordenador pode editar o projeto')

        if (
            self.cleaned_data.get('inicio_execucao')
            and self.cleaned_data.get('fim_execucao')
            and (self.cleaned_data.get('inicio_execucao') > self.cleaned_data.get('fim_execucao'))
        ):
            self.add_error('inicio_execucao', 'A data de início do projeto não pode ser maior do que a data de término.')

        if self.cleaned_data.get('uo') and self.cleaned_data.get('uo') not in self.edital.get_uos_edital_pesquisa():
            self.add_error('uo',
                           'Este edital não possui oferta para o campus selecionado.')

        return super().clean(*args, **kwargs)


def ext_combo_template_aluno(obj):
    out = [f'<dt class="sr-only">Nome</dt><dd><strong>{obj}</strong></dd>']
    img_src = obj.get_foto_75x100_url()
    out.append(f'<dt class="sr-only">Campus</dt><dd>{obj.curso_campus}</dd>')

    if obj.ira:
        out.append(f'<dt>Coeficiente de Rendimento Escolar:</dt><dd>{obj.get_ira()}</dd>')
    else:
        out.append('<dt>Coeficiente de Rendimento Escolar:</dt><dd class="false">Não possui</dd>')

    if obj.pessoa_fisica.lattes:
        out.append('<dt>Currículo Lattes:</dt><dd class="true">Sim</dd>')
    else:
        out.append('<dt>Currículo Lattes:</dt><dd class="false">Sem registro no SUAP</dd>')

    template = '''<div class="person">
        <div class="photo-circle">
            <img src="{}" alt="Foto de {}" />
        </div>
        <dl>{}</dl>
    </div>
    '''.format(
        img_src, obj, ''.join(out)
    )
    return template


class ParticipacaoAlunoForm(forms.ModelFormPlus):
    aluno = forms.ModelChoiceField(
        queryset=Aluno.ativos.all(),
        widget=AutocompleteWidget(extraParams=dict(ext_combo_template=ext_combo_template_aluno), search_fields=Aluno.SEARCH_FIELDS),
        label='Participante',
        required=True,
    )
    data = forms.DateFieldPlus(label='Data de Entrada', help_text='A data não pode ser maior do que hoje.')

    class Meta:
        model = Participacao
        fields = ('vinculo', 'carga_horaria', 'aluno', 'data')

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop('projeto', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields.pop('aluno')
            self.historico = HistoricoEquipe.objects.filter(participante=self.instance, projeto=self.instance.projeto).order_by('id')
            if self.historico and self.historico[0].data_movimentacao:
                self.fields['data'].initial = self.historico[0].data_movimentacao
        elif self.projeto.edital.discente_proprio_campus:
            self.fields['aluno'].queryset = Aluno.ativos.filter(curso_campus__diretoria__setor__uo=self.projeto.uo)
        self.fields['vinculo'].label = 'Vínculo'

    def clean(self):
        if self.instance.pk:
            instance = self.instance.projeto
            ja_eh_cadastrado = True
            if self.historico.order_by('-id').exists():
                if (
                    self.cleaned_data.get('data')
                    and self.historico.order_by('-id')[0].data_movimentacao_saida
                    and self.cleaned_data.get('data') > self.historico.order_by('-id')[0].data_movimentacao_saida
                ):
                    raise forms.ValidationError('A data informada é maior do que a data de término do vínculo mais recente do participante, não é possível inserir/editar aluno.')
        else:
            instance = self.projeto
            ja_eh_cadastrado = False

        if self.cleaned_data.get('data') and self.cleaned_data.get('data') > instance.fim_execucao:
            raise forms.ValidationError('A data informada é maior do que a data de término do projeto, não é possível inserir/editar aluno.')

        if not ja_eh_cadastrado and instance.edital.tem_formato_completo():
            aluno = 0
            participantes = Participacao.ativos.filter(projeto=instance)
            if participantes:
                for participante in participantes:
                    if not participante.is_servidor():
                        aluno += 1
            if aluno >= instance.edital.qtd_maxima_alunos:
                raise forms.ValidationError('O número máximo de alunos para este projeto já foi atingido.')

        if self.cleaned_data.get('aluno') and instance.edital.lattes_obrigatorio:
            if not self.cleaned_data.get('aluno').pessoa_fisica.lattes:
                raise forms.ValidationError(
                    'Não há currículo lattes registrado no SUAP. Oriente seu aluno a cadastrar seu currículo lattes na área de informações pessoais no SUAP.'
                )

        if self.cleaned_data.get('vinculo') == "Bolsista" and instance.edital.tem_formato_completo():

            if not ja_eh_cadastrado:
                aluno_com_bolsa = 0
                extrapolou_cota = False
                participantes = Participacao.ativos.filter(projeto=instance, vinculo='Bolsista')
                if participantes:
                    for participante in participantes:
                        if not participante.is_servidor():
                            aluno_com_bolsa += 1

                if self.instance.pk:
                    if aluno_com_bolsa > instance.edital.qtd_maxima_alunos_bolsistas:
                        extrapolou_cota = True
                else:
                    if aluno_com_bolsa >= instance.edital.qtd_maxima_alunos_bolsistas:
                        extrapolou_cota = True

                if extrapolou_cota:
                    raise forms.ValidationError('A cota de alunos bolsistas para este projeto já foi utilizada. O mesmo só poderá ser cadastrado como voluntário.')

            if self.instance.pk:
                mensagem_alerta = instance.mensagem_restricao_adicionar_membro(categoria=Participacao.ALUNO, bolsista=True, participacao=self.instance)
                if mensagem_alerta:
                    raise forms.ValidationError(mensagem_alerta)

            if instance.edital.forma_selecao == Edital.CAMPUS:
                if BolsaDisponivel.objects.filter(edital=instance.edital, uo=instance.uo).exists():
                    plano_oferta = BolsaDisponivel.objects.get(edital=instance.edital, uo=instance.uo).num_maximo_ic
                else:
                    raise forms.ValidationError('Nenhuma cota foi cadastrada neste edital para aluno bolsista. O mesmo só poderá ser cadastrado como voluntário.')
            else:
                plano_oferta = instance.edital.qtd_bolsa_alunos
            if instance.edital.forma_selecao == Edital.CAMPUS:
                bolsistas_geral = Participacao.ativos.filter(
                    projeto__edital=instance.edital, projeto__uo=instance.uo, vinculo='Bolsista', bolsa_concedida=True, projeto__aprovado=True
                )
            else:
                bolsistas_geral = Participacao.ativos.filter(projeto__edital=instance.edital, vinculo='Bolsista', bolsa_concedida=True, projeto__aprovado=True)
            bolsistas_geral_aluno = 0
            for bolsista in bolsistas_geral:
                if not (bolsista.id == self.instance.id):
                    if not bolsista.is_servidor():
                        bolsistas_geral_aluno = bolsistas_geral_aluno + 1
            if plano_oferta <= bolsistas_geral_aluno:
                raise forms.ValidationError('A cota de alunos bolsistas deste edital já foi atingida. O mesmo só poderá ser cadastrado como voluntário.')

            data = datetime.date.today()
            if datetime.date.today() < self.projeto.inicio_execucao:
                data = self.projeto.inicio_execucao
            msg = Participacao.get_mensagem_aluno_nao_pode_ter_bolsa(self.cleaned_data.get('aluno'), data=data)
            if msg:
                raise forms.ValidationError(msg)

        if instance.fim_execucao < datetime.date.today():
            raise forms.ValidationError('Data término da execução do projeto é maior que a data atual, não é possível inserir/editar aluno.')
        return self.cleaned_data


def ext_combo_template_servidor(obj):
    out = [f'<dt class="sr-only">Nome</dt><dd><strong>{obj.nome}<strong> (Mat. {obj.matricula})</dd>']
    if obj.setor:
        out.append(f'<dt class="sr-only">Setor</dt><dd>{obj.setor.get_caminho_as_html()}</dd>')
    if obj.cargo_emprego:
        out.append(f'<dt class="sr-only">Cargo</dt><dd>{obj.cargo_emprego}</dd>')
    if hasattr(obj.get_vinculo(), 'vinculo_curriculo_lattes'):
        out.append('<dt class="sr-only">Currículo Lattes</dt><dd class="true">Tem currículo Lattes</dd>')
    else:
        out.append('<dt class="sr-only">Currículo Lattes</dt><dd class="false">Não há Currículo Lattes</dd>')
    template = '''<div class="person">
        <div class="photo-circle">
            <img src="{}" alt="Foto de {}" />
        </div>
        <dl>{}</dl>
    </div>
    '''.format(
        obj.get_foto_75x100_url(), obj.nome, ''.join(out)
    )
    return template


class ParticipacaoServidorForm(forms.ModelFormPlus):
    servidor = forms.ModelChoiceField(
        queryset=Servidor.objects.ativos(),
        widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS, extraParams=dict(ext_combo_template=ext_combo_template_servidor)),
        label='Participante',
        required=True,
    )
    data = forms.DateFieldPlus(label='Data de Entrada', help_text='A data não pode ser maior do que hoje.')

    class Meta:
        model = Participacao
        fields = ('vinculo', 'carga_horaria', 'servidor', 'data')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields.pop('servidor')
            self.historico = HistoricoEquipe.objects.filter(participante=self.instance, projeto=self.instance.projeto).order_by('id')
            self.fields['data'].initial = self.historico[0].data_movimentacao
        self.fields['vinculo'].label = 'Vínculo'

    def clean(self):
        if self.instance.pk:
            instance = self.instance.projeto
            ja_eh_cadastrado = True
            if self.historico.exists():
                if (
                    self.cleaned_data.get('data')
                    and self.historico.order_by('-id')[0].data_movimentacao_saida
                    and self.cleaned_data.get('data') > self.historico.order_by('-id')[0].data_movimentacao_saida
                ):
                    raise forms.ValidationError(
                        'A data informada é maior do que a data de término do vínculo mais recente do participante, não é possível inserir/editar servidor.'
                    )
        else:
            instance = self.projeto
            ja_eh_cadastrado = False
        cleaned_data = super().clean()
        if self.cleaned_data.get('data') and self.cleaned_data.get('data') > instance.fim_execucao:
            raise forms.ValidationError('A data informada é maior do que a data de término do projeto, não é possível inserir/editar servidor.')
        if not ja_eh_cadastrado and instance.edital.tem_formato_completo():
            pesquisador = 0
            participantes = Participacao.ativos.filter(projeto=instance)
            if participantes:
                for participante in participantes:
                    if participante.is_servidor():
                        pesquisador += 1
            if pesquisador >= instance.edital.qtd_maxima_servidores:
                raise forms.ValidationError('O número máximo de servidores para este projeto já foi atingido.')

        if self.cleaned_data.get('vinculo') == "Bolsista" and instance.edital.tem_formato_completo():
            if self.instance.pk:
                if self.instance.responsavel == True and not self.instance.projeto.edital.coordenador_pode_receber_bolsa:
                    raise forms.ValidationError('Este edital não permite bolsa para coordenador. O mesmo só poderá ser voluntário.')
                elif self.instance.vinculo_pessoa.relacionamento.funcao:
                    if self.instance.vinculo_pessoa.relacionamento.funcao.codigo == 'CD':
                        raise forms.ValidationError('Servidor com cargo de direção não pode receber bolsa. O mesmo só poderá ser voluntário.')
            else:
                if self.cleaned_data.get('servidor') and self.cleaned_data.get('servidor').funcao:
                    if self.cleaned_data.get('servidor').funcao.codigo == 'CD':
                        raise forms.ValidationError('Servidor com cargo de direção não pode receber bolsa. O mesmo só poderá ser voluntário.')

            pesquisador_com_bolsa = 0
            extrapolou_cota = False
            participantes = Participacao.ativos.filter(projeto=instance, vinculo='Bolsista', responsavel=False)
            if participantes:
                for participante in participantes:
                    if participante.is_servidor():
                        if self.instance.pk:
                            if self.instance.vinculo_pessoa.id != participante.vinculo_pessoa.id:
                                pesquisador_com_bolsa += 1
                        else:
                            pesquisador_com_bolsa += 1

            if self.instance.pk:
                if pesquisador_com_bolsa > instance.edital.qtd_maxima_servidores_bolsistas:
                    extrapolou_cota = True
            else:
                if pesquisador_com_bolsa >= instance.edital.qtd_maxima_servidores_bolsistas:
                    extrapolou_cota = True

            if extrapolou_cota:
                raise forms.ValidationError('A cota de pesquisadores bolsistas para este projeto já foi utilizada. O mesmo só poderá ser cadastrado como voluntário.')

            if instance.edital.forma_selecao == Edital.CAMPUS:
                if BolsaDisponivel.objects.filter(edital=instance.edital, uo=instance.uo).exists():
                    plano_oferta = BolsaDisponivel.objects.get(edital=instance.edital, uo=instance.uo).num_maximo_pesquisador
                else:
                    plano_oferta = 0
            else:
                plano_oferta = instance.edital.qtd_bolsa_servidores
            if instance.edital.forma_selecao == Edital.CAMPUS:
                bolsistas_geral = Participacao.ativos.filter(
                    projeto__edital=instance.edital, projeto__uo=instance.uo, vinculo='Bolsista', bolsa_concedida=True, projeto__aprovado=True
                )
            else:
                bolsistas_geral = Participacao.ativos.filter(projeto__edital=instance.edital, vinculo='Bolsista', bolsa_concedida=True, projeto__aprovado=True)
            bolsistas_geral_servidor = 0
            for bolsista in bolsistas_geral:
                if not bolsista.id == self.instance.id:
                    if bolsista.is_servidor():
                        bolsistas_geral_servidor = bolsistas_geral_servidor + 1
            if plano_oferta <= bolsistas_geral_servidor:
                raise forms.ValidationError('A oferta de bolsas para pesquisadores já foi utilizada. O mesmo só poderá ser cadastrado como voluntário.')

        if self.cleaned_data.get('servidor'):
            if not hasattr(self.cleaned_data.get('servidor').get_vinculo(), 'vinculo_curriculo_lattes'):
                raise forms.ValidationError('O servidor não possui Currículo Lattes cadastrado.')

            if not self.cleaned_data.get('servidor').get_vinculo().vinculo_curriculo_lattes.grupos_pesquisa.all():
                if instance.edital.exige_grupo_pesquisa:
                    from cnpq.views import atualizar_grupos_pesquisa
                    status = atualizar_grupos_pesquisa(self.cleaned_data.get('servidor').get_vinculo().vinculo_curriculo_lattes)
                    if status == 0:
                        raise forms.ValidationError('O servidor não está vinculado a nenhum grupo de pesquisa.')

        return cleaned_data


class AlterarCoordenadorForm(forms.FormPlus):
    participacao = forms.ModelChoiceField(Participacao.objects, label='Novo Coordenador', required=True)

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop("projeto", None)
        super().__init__(*args, **kwargs)
        qs_participacoes = self.projeto.participacao_set.filter(ativo=True)
        servidores_ids = []
        for p in qs_participacoes:
            if p.is_servidor():
                servidores_ids.append(p.vinculo_pessoa.id)
        self.fields['participacao'].queryset = self.projeto.participacao_set.filter(ativo=True, vinculo_pessoa__in=servidores_ids, responsavel=False)

    def clean(self):
        if (
            self.cleaned_data.get('participacao')
            and self.cleaned_data['participacao'].vinculo == TipoVinculo.BOLSISTA
            and self.projeto.edital.coordenador_pode_receber_bolsa == False
        ):
            raise forms.ValidationError('O coordenador não pode ser bolsista. Edite o vínculo do pesquisador antes de alterar o coordenador do projeto.')


class MetaForm(forms.ModelFormPlus):
    class Meta:
        model = Meta
        exclude = ('projeto', 'data_cadastro')


class EtapaForm(forms.ModelFormPlus):
    responsavel = forms.ModelChoiceField(Participacao.objects, label='Responsável', required=True)
    integrantes = forms.MultipleModelChoiceField(Participacao.objects, label='Integrantes da Atividade', required=False)

    class Meta:
        model = Etapa
        exclude = ('meta', 'data_cadastro')

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop("proj", None)
        super().__init__(*args, **kwargs)
        self.fields['responsavel'].queryset = self.projeto.participacao_set.filter(ativo=True)
        self.fields['integrantes'].queryset = self.projeto.participacao_set.filter(ativo=True)
        if self.instance.pk:
            self.initial['integrantes'] = [t.pk for t in self.instance.integrantes.all()]

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.cleaned_data.get('inicio_execucao') and self.cleaned_data.get('fim_execucao'):
            if self.cleaned_data['inicio_execucao'] > self.projeto.fim_execucao:
                raise forms.ValidationError('A data de início de execução da atividade não pode ser maior que a data final de execução do projeto.')

            if self.cleaned_data['fim_execucao'] > self.projeto.fim_execucao:
                raise forms.ValidationError('A data do fim de execução da atividade não pode ser maior que a data final de execução do projeto.')

            if self.cleaned_data['inicio_execucao'] > self.cleaned_data['fim_execucao']:
                raise forms.ValidationError('A data de início de execução da atividade não pode ser maior que a data final de execução da atividade.')
            if (
                self.projeto.edital.prazo_atividade
                and (self.cleaned_data.get('fim_execucao') - self.cleaned_data.get('inicio_execucao')).days > self.projeto.edital.prazo_atividade
            ):
                raise forms.ValidationError(f'O prazo máximo de cada atividade neste projeto deve ser de {self.projeto.edital.prazo_atividade} dias.')

        return cleaned_data


class EquipeEtapaForm(forms.ModelFormPlus):
    integrantes = forms.MultipleModelChoiceField(Participacao.objects, label='Integrantes da Atividade', required=False)

    class Meta:
        model = Etapa
        fields = ['integrantes']

    def __init__(self, *args, **kwargs):
        projeto = kwargs.pop("proj", None)
        super().__init__(*args, **kwargs)
        self.fields['integrantes'].queryset = projeto.participacao_set.filter(ativo=True)
        self.initial['integrantes'] = [t.pk for t in self.instance.integrantes.all()]


class DesembolsoForm(forms.ModelFormPlus):
    clonar_operacao = forms.IntegerFieldPlus(
        label='Repetir Desembolso até o mês', max_length=2, required=False, help_text='Deixe em branco se este desembolso não se repetirá nos meses subsequentes.'
    )

    class Meta:
        model = Desembolso
        exclude = ('projeto', 'data_cadastro', 'despesa')
        fields = ['item', 'ano', 'mes', 'valor']

    def __init__(self, *args, **kwargs):
        projeto = kwargs.pop("proj", None)
        super().__init__(*args, **kwargs)
        self.fields['item'].widget = forms.Select()
        if not self.instance.pk:

            self.fields['item'].queryset = ItemMemoriaCalculo.objects.filter(projeto=projeto)
        else:
            self.fields['item'].queryset = ItemMemoriaCalculo.objects.filter(pk=self.instance.item.id)
            del self.fields['clonar_operacao']

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if cleaned_data.get('clonar_operacao') and cleaned_data.get('clonar_operacao') > 12:
            self.add_error('clonar_operacao', 'O máximo permitido são 12 meses.')
        return cleaned_data


class UploadArquivoForm(forms.ModelFormPlus):
    arquivo = forms.FileFieldPlus(label='Arquivo', required=True)

    class Meta:
        model = EditalArquivo
        fields = ['nome', 'arquivo']


class UploadProjetoAnexoForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus(label='Arquivo', required=True)

    def __init__(self, *args, **kwargs):
        self.origem = kwargs.pop("origem", None)
        super().__init__(*args, **kwargs)


class UploadArquivoPesquisaForm(forms.FormPlus):
    anexo = forms.ChoiceField(choices=[])
    arquivo = forms.FileFieldPlus()

    def __init__(self, *args, **kwargs):
        participacao = kwargs.pop("membro", None)
        super().__init__(*args, **kwargs)
        self.fields['anexo'].choices = participacao.get_tipos_anexos().values_list('id', 'nome')


class RegistroGastoForm(forms.ModelFormPlus):
    arquivo = forms.FileFieldPlus(label='Nota Fiscal ou Cupom', required=False)
    cotacao_precos = forms.FileFieldPlus(label='Cotação de Preços', required=False, help_text='Envie um arquivo ZIP contendo as três propostas de cotação de preços deste item.')

    class Meta:
        model = RegistroGasto
        exclude = (
            'item',
            'dt_avaliacao',
            'avaliador',
            'aprovado',
            'justificativa_reprovacao',
            'desembolso',
            'obs_cancelamento_avaliacao',
            'avaliacao_cancelada_por',
            'avaliacao_cancelada_em',
        )


class RegistroExecucaoEtapaForm(forms.ModelFormPlus):
    arquivo = forms.FileFieldPlus(
        label='Arquivo', required=False, help_text='Junte todas as evidências (fotos, resultados de análises, atas de reuniões, etc) em um único arquivo no formato PDF'
    )

    class Meta:
        model = RegistroExecucaoEtapa
        exclude = (
            'etapa',
            'dt_avaliacao',
            'avaliador',
            'aprovado',
            'info_ind_qualitativo',
            'justificativa_reprovacao',
            'obs_cancelamento_avaliacao',
            'avaliacao_cancelada_por',
            'avaliacao_cancelada_em',
        )

    def __init__(self, *args, **kwargs):
        self.etapa = kwargs.pop("etapa", None)
        super().__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.cleaned_data.get('inicio_execucao') and self.cleaned_data.get('fim_execucao'):
            if self.cleaned_data['inicio_execucao'] > self.etapa.meta.projeto.fim_execucao:
                raise forms.ValidationError('A data de início de execução da atividade não pode ser maior que a data final de execução do projeto.')

            if self.cleaned_data['fim_execucao'] > self.etapa.meta.projeto.fim_execucao:
                raise forms.ValidationError('A data do fim de execução da atividade não pode ser maior que a data final de execução do projeto.')

            if self.cleaned_data['inicio_execucao'] > self.cleaned_data['fim_execucao']:
                raise forms.ValidationError('A data de início de execução da atividade não pode ser maior que a data final de execução da atividade.')
        else:
            raise forms.ValidationError('As datas do início e do fim da execução são obrigatórias.')

        return cleaned_data


class ValidacaoConclusaoProjetoForm(forms.FormPlus):
    aprovado = forms.BooleanField(required=False)
    obs = forms.CharField(widget=forms.Textarea(), label='Observação')

    def __init__(self, *args, **kwargs):
        registro = kwargs.pop("registro", None)
        super().__init__(*args, **kwargs)
        if registro.obs_avaliador:
            self.fields['obs'].initial = registro.obs_avaliador


class FotoProjetoForm(forms.FormPlus):
    fotos = MultiFileField(filetypes=['jpg', 'png', 'jpeg'], min_num=0, max_num=10, max_file_size=1024 * 1024 * 5, label='Fotos',
                           help_text='Selecione uma ou mais fotos.')
    legenda = forms.CharFieldPlus(label='Legenda', required=False, widget=forms.Textarea())


class EditarFotoProjetoForm(forms.ModelFormPlus):
    class Meta:
        model = FotoProjeto
        fields = ('imagem', 'legenda',)


def AvaliacaoFormFactory(request, avaliacao, projeto, avaliador, vinculo):
    class AvaliacaoForm(forms.FormPlus):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            if avaliacao:
                for item in avaliacao.itemavaliacao_set.all().order_by('criterio_avaliacao__id'):
                    nota_choices = []
                    maior_nota = (2 * item.criterio_avaliacao.pontuacao_maxima) + 1
                    notas = [x * 0.5 for x in range(int(maior_nota))]
                    notas.sort(reverse=True)
                    for nota in notas:
                        nota_choices.append([str(nota), str(nota)])

                    self.fields[str(item.criterio_avaliacao.pk)] = forms.ChoiceField(
                        choices=nota_choices,
                        label=item.criterio_avaliacao.descricao,
                        help_text='Pontuação Máxima: %s' % (format_(item.criterio_avaliacao.pontuacao_maxima)),
                        initial=float(item.pontuacao),
                    )
                    self.fields[f'parecer_{str(item.criterio_avaliacao.pk)}'] = forms.CharField(
                        label='Parecer', widget=forms.Textarea(), required=True, initial=item and item.parecer or None
                    )
            else:
                for criterio_avaliacao in projeto.edital.criterioavaliacao_set.all():
                    nota_choices = []
                    maior_nota = (2 * criterio_avaliacao.pontuacao_maxima) + 1
                    notas = [x * 0.5 for x in range(int(maior_nota))]
                    notas.sort(reverse=True)
                    for nota in notas:
                        nota_choices.append([str(nota), str(nota)])

                    self.fields[str(criterio_avaliacao.pk)] = forms.ChoiceField(
                        choices=nota_choices, label=criterio_avaliacao.descricao, help_text='Pontuação Máxima: %s' % (format_(criterio_avaliacao.pontuacao_maxima))
                    )
                    self.fields[f'parecer_{str(criterio_avaliacao.pk)}'] = forms.CharField(label='Parecer', widget=forms.Textarea(), required=True)
            self.avaliacao = avaliacao

        def clean(self, *args, **kwargs):
            cleaned_data = super().clean()
            if not self.errors:
                for criterio_avaliacao in projeto.edital.criterioavaliacao_set.all():
                    valor_pontuacao = Decimal(cleaned_data.get(str(criterio_avaliacao.pk)))
                    if valor_pontuacao > criterio_avaliacao.pontuacao_maxima:
                        self.errors[str(criterio_avaliacao.pk)] = ['Pontuação informada maior que a máxima permitida.']
                        del cleaned_data[str(criterio_avaliacao.pk)]
            return cleaned_data

        @transaction.atomic()
        def save(self):
            if not self.avaliacao:
                self.avaliacao = Avaliacao()
                self.avaliacao.projeto = projeto
                self.avaliacao.avaliador = avaliador
                self.avaliacao.vinculo = vinculo
                self.avaliacao.pontuacao = Decimal('0')
                self.avaliacao.save()
            for criterio_avaliacao in self.avaliacao.projeto.edital.criterioavaliacao_set.all():
                try:
                    item = ItemAvaliacao.objects.get(avaliacao=self.avaliacao, criterio_avaliacao=criterio_avaliacao)
                except Exception:
                    item = ItemAvaliacao()
                    item.avaliacao = self.avaliacao
                    item.criterio_avaliacao = criterio_avaliacao
                item.pontuacao = self.cleaned_data.get(str(criterio_avaliacao.id), 0)
                item.parecer = self.cleaned_data.get(f'parecer_{str(criterio_avaliacao.pk)}', 0)
                item.save()
            self.avaliacao.save()

    return AvaliacaoForm(request.POST or None)


class ReprovarExecucaoEtapaForm(forms.FormPlus):
    obs = forms.CharField(widget=forms.Textarea(), label='Justificativa da Não Aprovação')


class ReprovarExecucaoGastoForm(forms.FormPlus):
    obs = forms.CharField(widget=forms.Textarea(), label='Justificativa da Não Aprovação')


class ProjetoHistoricoDeEnvioForm(forms.ModelFormPlus):
    class Meta:
        model = ProjetoHistoricoDeEnvio
        exclude = ('projeto', 'data_operacao', 'situacao', 'operador')


class ProjetoAvaliadorForm(forms.FormPlus):
    areas_de_conhecimento = forms.ModelMultiplePopupChoiceField(AreaConhecimento.objects.filter(superior__isnull=False), required=False, label="Áreas de Conhecimento")

    def __init__(self, pessoa, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['areas_de_conhecimento'].initial = pessoa.areas_de_conhecimento.all().values_list('pk', flat=True)


class IndicarAvaliadoresForm(forms.FormPlus):
    nome = forms.CharFieldPlus(label='Nome', required=False)
    matricula = forms.CharFieldPlus(label='Matrícula', required=False)
    titulacao = forms.ModelChoiceFieldPlus(queryset=Titulacao.objects, label='Filtrar por Titulação:', required=False)
    disciplina_ingresso = forms.ModelChoiceFieldPlus(queryset=Disciplina.objects, label='Disiciplina de Ingresso', required=False)
    filtrar_por_area = forms.BooleanField(label='Apenas Avaliadores da Área do Projeto', required=False)
    area_conhecimento = forms.ModelChoiceFieldPlus(
        AreaConhecimento.objects.filter(superior__isnull=False).order_by('descricao'), required=False, label="Filtrar por Área de Conhecimento"
    )


class AvaliadoresAreaConhecimentoForm(forms.FormPlus):
    METHOD = 'GET'
    palavra_chave = forms.CharField(label='Nome', required=False)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo().all(), label='Campus', required=False, widget=forms.Select(attrs={'onchange': 'submeter_form(this)'}))
    titulacao = forms.ModelChoiceField(queryset=Titulacao.objects, label='Filtrar por Titulação:', required=False)
    area_conhecimento = forms.ModelChoiceField(
        queryset=AreaConhecimento.objects.all().order_by('descricao'), empty_label='Selecione uma Área de Conhecimento', label='Filtrar por Área de Conhecimento:', required=False
    )
    situacao = forms.ChoiceField(label='Situação', choices=(('', '--------'), ('Ativos', 'Ativos'), ('Inativos', 'Inativos')), required=False)


class ComissaoEditalPesquisaForm(forms.ModelFormPlus):
    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    edital = forms.ModelChoiceField(queryset=Edital.objects.order_by('-id'), label='Filtrar por Edital:', required=True)

    clonar_comissao = forms.BooleanField(label='Clonar Comissão de um Edital anterior', initial=False, required=False)

    vinculos_membros = forms.MultipleModelChoiceFieldPlus(Vinculo.objects, label='Membro', required=False)

    clonar_comissao_edital = ModelChoiceField(queryset=Edital.objects.order_by('-id'), label='Clonar Comissão do Edital:', required=True)

    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=False, empty_label='Todos')

    class Meta:
        model = ComissaoEditalPesquisa
        fields = ('ano', 'edital', 'uo', 'clonar_comissao', 'vinculos_membros', 'clonar_comissao_edital')

    class Media:
        js = ['/static/pesquisa/js/meusprojetosform.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clonar_comissao_edital'].required = False

        if not self.instance.pk:
            if not self.request.user.groups.filter(name='Diretor de Pesquisa'):
                if self.request.user.groups.filter(name='Coordenador de Pesquisa'):
                    self.fields['edital'].queryset = Edital.objects.filter(forma_selecao=Edital.CAMPUS).order_by('-id')
                else:
                    self.fields['edital'].queryset = Edital.objects.filter(forma_selecao=Edital.GERAL).order_by('-id')
        else:
            self.fields['clonar_comissao_edital'].widget = forms.HiddenInput()
            self.fields['clonar_comissao'].widget = forms.HiddenInput()

        internos = Servidor.objects.ativos().filter(areas_de_conhecimento__isnull=False).values_list('id', flat=True)
        externos = AvaliadorExterno.objects.all().values_list('vinculo', flat=True)

        queryset = Vinculo.objects.filter(
            Q(id_relacionamento__in=internos, tipo_relacionamento__model='servidor') | Q(id__in=externos))
        self.fields['vinculos_membros'].queryset = queryset.order_by('pessoa__nome')

        if self.instance.pk:
            avaliadores = self.instance.vinculos_membros.all()
            for avaliador in avaliadores:
                if avaliador not in queryset:
                    avaliadores = avaliadores.exclude(id=avaliador.id)
            self.initial['vinculos_membros'] = [registro.id for registro in avaliadores]
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []

        if editais:
            ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            for ano in range(ano_limite, ano_inicio, -1):
                ANO_CHOICES.append([str(ano), str(ano)])
        else:
            ANO_CHOICES.append(['Selecione um ano', 'Nenhum edital cadastrado'])

        self.fields['ano'].choices = ANO_CHOICES

        if not self.request.user.groups.filter(name='Diretor de Pesquisa'):
            self.fields['uo'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(id=get_uo(self.request.user).id), required=True)
            self.fields['uo'].initial = get_uo(self.request.user).id

    def clean(self):
        cleaned_data = super().clean()
        comissao_existe = None
        if not self.instance.pk:
            if not self.cleaned_data.get('edital'):
                raise forms.ValidationError('Selecione um edital.')

            if self.request.user.groups.filter(name='Pré-Avaliador Sistêmico de Projetos de Pesquisa'):
                comissao_existe = ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data['edital'])

            if self.request.user.groups.filter(name='Coordenador de Pesquisa'):
                comissao_existe = ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data['edital'], uo=get_uo(self.request.user))

            if comissao_existe:
                raise forms.ValidationError('Já existe uma comissão cadastrada para este edital.')

            if not self.cleaned_data.get('vinculos_membros') and not self.cleaned_data.get('clonar_comissao_edital'):
                raise forms.ValidationError('Informe os membros da comissão ou selecione um edital para clonar a comissão de avaliação.')

            if self.cleaned_data.get('clonar_comissao_edital'):
                if (
                    self.cleaned_data.get('uo')
                    and not ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data.get('clonar_comissao_edital'), uo=self.cleaned_data.get('uo')).exists()
                ):
                    self.add_error('clonar_comissao_edital', 'Não existe comissão para o edital e campus selecionados.')
                if not ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data.get('clonar_comissao_edital')).exists():
                    self.add_error('clonar_comissao_edital', 'Não existe comissão para o edital selecionado.')

        if self.cleaned_data.get('edital') and not (self.cleaned_data.get('edital').tipo_edital == Edital.PESQUISA_INOVACAO_CONTINUO):
            membros_para_checar_titulacao = None
            if self.cleaned_data.get('vinculos_membros'):
                membros_para_checar_titulacao = self.cleaned_data.get('vinculos_membros')
            elif self.cleaned_data.get('clonar_comissao_edital'):
                comissao_a_clonar = ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data.get('clonar_comissao_edital'))
                if self.cleaned_data.get('uo'):
                    comissao_a_clonar = comissao_a_clonar.filter(uo=self.cleaned_data.get('uo'))
                if comissao_a_clonar.exists():
                    comissao_a_clonar = comissao_a_clonar[0]
                    membros_para_checar_titulacao = comissao_a_clonar.vinculos_membros.all()

            if membros_para_checar_titulacao:
                edital = self.cleaned_data.get('edital')
                titulacoes = edital.titulacoes_avaliador.all().values_list('codigo', flat=True)
                nomes_titulacoes = ', '.join(edital.titulacoes_avaliador.all().values_list('nome', flat=True))
                for pessoa in membros_para_checar_titulacao:
                    if pessoa.eh_servidor():
                        servidor = pessoa.relacionamento
                        if (not servidor.titulacao) or not (servidor.titulacao.codigo in titulacoes):
                            if not servidor.titulacao:
                                string_erro = f'{pessoa} não possui nenhuma titulação cadastrada no SUAP.'
                            else:
                                string_erro = f'{pessoa.pessoa.nome} ({servidor.titulacao}) não possui nenhuma das titulações exigidas no edital ({nomes_titulacoes}).'
                            raise forms.ValidationError(string_erro)
                    elif AvaliadorExterno.objects.filter(vinculo=pessoa).exists():
                        avaliador_externo = AvaliadorExterno.objects.get(vinculo=pessoa)
                        if not (avaliador_externo.titulacao.codigo in titulacoes):
                            raise forms.ValidationError(
                                f'{pessoa.pessoa.nome} ({avaliador_externo.titulacao}) não possui nenhuma das titulações exigidas no edital ({nomes_titulacoes}).'
                            )

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        comissao = super().save(False)
        comissao.save()

        if self.cleaned_data.get('clonar_comissao_edital'):
            del self.cleaned_data['vinculos_membros']
            if self.cleaned_data.get('uo'):
                comissao_clonada = ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data.get('clonar_comissao_edital'), uo=self.cleaned_data.get('uo'))
            else:
                comissao_clonada = ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data.get('clonar_comissao_edital'))

            for item in comissao_clonada[0].vinculos_membros.all():
                comissao.vinculos_membros.add(item)

        return comissao


class EquipeProjetoForm(forms.FormPlus):
    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    edital = forms.ModelChoiceField(queryset=Edital.objects.order_by('-id'), empty_label='Selecione um Edital', label='Filtrar por Edital:', required=False)

    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.uo(), empty_label='Selecione um Campus', label='Filtrar por Campus:', required=False)
    METHOD = 'GET'
    TIPO_EXIBICAO = ((0, 'Detalhado'), (1, 'Simples'))
    tipo_de_exibicao = forms.ChoiceField(choices=TIPO_EXIBICAO, label='Tipo de Exibição', required=False, initial=0)
    TIPO_SITUACAO = ((0, 'Todos'), (1, 'Concluído'), (2, 'Em execução'))
    situacao = forms.ChoiceField(choices=TIPO_SITUACAO, label='Filtrar Projetos por Situação', required=False, initial=0)

    class Media:
        js = ['/static/pesquisa/js/meusprojetosform.js']

    def __init__(self, *args, **kwargs):
        self.ano = kwargs.pop('ano', None)
        super().__init__(*args, **kwargs)
        participantes = Participacao.objects.filter(projeto__aprovado=True).values_list('vinculo_pessoa', flat=True)
        self.fields['pessoa'] = forms.ModelChoiceFieldPlus(Vinculo.objects.filter(id__in=set(participantes)), required=False)
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []
        if editais.exists():
            ANO_CHOICES.append(['', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            ANO_CHOICES += [(ano, str(ano)) for ano in range(ano_limite, ano_inicio, -1)]
        else:
            ANO_CHOICES.append(['', 'Nenhum edital cadastrado'])
        self.fields['ano'].choices = ANO_CHOICES
        if self.ano:
            self.fields['edital'].queryset = Edital.objects.filter(inicio_inscricoes__year=self.ano)


class AvaliadorExternoForm(forms.ModelFormPlus):
    cpf = forms.BrCpfField(label='CPF')
    telefone = forms.BrTelefoneField(max_length=45, label='Telefone para Contato')
    lattes = forms.URLField(label='Lattes', help_text='Endereço do Currículo Lattes', required=True)
    areas = forms.ModelMultipleChoiceField(queryset=AreaConhecimento.objects.filter(superior__isnull=False), widget=FilteredSelectMultiplePlus('', True), label='Áreas de Conhecimento', required=False)

    class Meta:
        model = AvaliadorExterno
        fields = ('nome', 'email', 'telefone', 'titulacao', 'instituicao_origem', 'lattes')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['cpf'].initial = self.instance.vinculo.relacionamento.cpf
            self.fields['areas'].initial = self.instance.vinculo.relacionamento.areas_de_conhecimento.all().values_list('pk', flat=True)

    def clean_cpf(self):
        prestador = PrestadorServico.objects.filter(cpf=self.cleaned_data['cpf'])
        if prestador:
            avaliadores = AvaliadorExterno.objects.filter(vinculo=prestador[0].get_vinculo())
            erro = False
            if not self.instance.id and avaliadores.exists():
                erro = True
            else:
                if avaliadores.exclude(id=self.instance.id).exists():
                    erro = True
            if erro:
                raise forms.ValidationError('Já existe um avaliador externo cadastrado com este CPF.')
        return self.cleaned_data['cpf']

    @transaction.atomic
    def save(self, commit=True):

        nome = self.cleaned_data['nome']
        cpf = self.cleaned_data['cpf']
        email = self.cleaned_data['email']
        numero_telefone = self.cleaned_data['telefone']
        areas = self.cleaned_data['areas']
        username = cpf.replace('.', '').replace('-', '')
        qs = PrestadorServico.objects.filter(cpf=cpf)
        prestador_existente = qs.exists()
        if prestador_existente:
            prestador = qs[0]
        else:
            prestador = PrestadorServico()

        prestador.nome = nome
        prestador.username = username
        prestador.cpf = cpf
        prestador.email = email
        if not prestador.email_secundario:
            prestador.email_secundario = email
        prestador.ativo = True
        if not prestador.setor:
            prestador.setor = get_setor_propi()

        prestador.save()

        telefones = prestador.pessoatelefone_set.all()
        if not telefones.exists():
            prestador.pessoatelefone_set.create(numero=numero_telefone)
        else:
            telefone = telefones[0]
            telefone.numero = numero_telefone
            telefone.save()

        avaliador = super().save(False)

        avaliador.pessoa_fisica = prestador
        avaliador.vinculo = prestador.get_vinculo()
        avaliador.email = email
        avaliador.save()

        if areas:
            ids_areas = list()
            for area in areas:
                ids_areas.append(area.id)
                if area not in prestador.areas_de_conhecimento.all():
                    prestador.areas_de_conhecimento.add(area)
            outras_areas = prestador.areas_de_conhecimento.exclude(id__in=ids_areas)
            if outras_areas.exists():
                for area in outras_areas:
                    prestador.areas_de_conhecimento.remove(area)
        try:
            LdapConf = apps.get_model('ldap_backend', 'LdapConf')
            conf = LdapConf.get_active()
            conf.sync_user(prestador)
        except Exception:
            pass

        self.enviar_email(prestador.username, email)

        return avaliador

    def enviar_email(self, username, email):
        obj = TrocarSenha.objects.create(username=username)
        url = f'{settings.SITE_URL}/comum/trocar_senha/{obj.username}/{obj.token}/'
        conteudo = '''
        <h1>Pesquisa</h1>
        <h2>Cadastro de Avaliador Externo</h2>
        <p>Prezado usuário,</p>
        <br />
        <p>Você foi cadastrado como Avaliador Externo de Projetos de Pesquisa.</p>
        <p>Caso ainda não tenha definido uma senha de acesso, por favor, acesse: {}.</p>
        <br />
        <p>Caso o token seja inválido, informe o seu cpf nos campos 'usuário' e 'cpf' ('usuário' tem que ser sem pontuação).</p>
        <p>Em seguida será reenviado um email com as instruções para criação da senha de acesso.</p>
        '''.format(
            url
        )
        return send_mail('[SUAP] Cadastro de Avaliador Externo', conteudo, settings.DEFAULT_FROM_EMAIL, [email])


class CancelarProjetoForm(forms.ModelFormPlus):
    justificativa_cancelamento = forms.CharField(widget=forms.Textarea(), label='Justificativa do Cancelamento')

    class Meta:
        model = ProjetoCancelado
        fields = ['justificativa_cancelamento', 'arquivo_comprovacao']


class IndicarAvaliadorForm(forms.FormPlus):
    METHOD = 'GET'
    AVALIACAO_STATUS = ((0, 'Todos'), (1, 'Projetos avaliados'), (2, 'Projetos não avaliados'), (3, 'Projetos parcialmente avaliados'))
    palavra_chave = forms.CharField(label='Avaliador', required=False)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=False, widget=forms.Select(attrs={'onchange': 'submeter_form(this)'}))
    status_avaliacao = forms.ChoiceField(choices=AVALIACAO_STATUS, label='Situação da avaliação', required=False, widget=forms.Select(attrs={'onchange': 'submeter_form(this)'}))


class AvaliarCancelamentoProjetoForm(forms.ModelFormPlus):
    obs_avaliacao = forms.CharField(widget=forms.Textarea(), label='Parecer do Avaliador')
    parecer_favoravel = forms.BooleanField(label='Concorda com o Cancelamento', required=False)

    class Meta:
        model = ProjetoCancelado
        fields = ['obs_avaliacao', 'parecer_favoravel']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['obs_avaliacao'].initial = self.instance.obs_avaliacao
        self.fields['parecer_favoravel'].initial = self.instance.parecer_favoravel


class ValidarCancelamentoProjetoForm(forms.ModelFormPlus):
    parecer_validacao = forms.CharField(widget=forms.Textarea(), label='Parecer do Avaliador')
    cancelado = forms.BooleanField(label='Cancelar Projeto', required=False)
    aprova_proximo = forms.BooleanField(
        label='Aprovar Pŕoximo Projeto',
        help_text='O primeiro projeto da lista de espera será aprovado automaticamente e o coordenador será notificado por email. Só terá efeito se a opção \'Cancelar Projeto\' for selecionada.',
        required=False,
    )

    class Meta:
        model = ProjetoCancelado
        fields = ['parecer_validacao', 'cancelado']

    def __init__(self, *args, **kwargs):
        eh_continuo = kwargs.pop("eh_continuo", None)
        super().__init__(*args, **kwargs)
        self.fields['parecer_validacao'].initial = self.instance.parecer_validacao
        self.fields['cancelado'].initial = self.instance.cancelado
        if eh_continuo:
            self.fields["aprova_proximo"].widget = forms.HiddenInput()


class RecursoPesquisaForm(forms.ModelFormPlus):
    justificativa = forms.CharField(widget=forms.Textarea(), label='Justificativa do Recurso')

    class Meta:
        model = RecursoProjeto
        fields = ['justificativa']


class AvaliarRecursoProjetoForm(forms.ModelFormPlus):
    parecer = forms.CharField(widget=forms.Textarea(), label='Parecer do Avaliador')
    parecer_favoravel = forms.BooleanField(label='Aceitar Recurso', required=False)

    class Meta:
        model = RecursoProjeto
        fields = ['parecer', 'parecer_favoravel']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parecer'].initial = self.instance.parecer
        self.fields['parecer_favoravel'].initial = self.instance.parecer_favoravel


class ValidarRecursoProjetoForm(forms.ModelFormPlus):
    parecer_validacao = forms.CharField(widget=forms.Textarea(), label='Parecer')
    aceito = forms.BooleanField(label='Aceitar Recurso', required=False)
    aprovar_projeto = forms.BooleanField(label='Aprovar Este Projeto', required=False)

    class Meta:
        model = RecursoProjeto
        fields = ['parecer_validacao', 'aceito']


class EditaisPesquisaForm(forms.FormPlus):
    METHOD = 'GET'
    PENDENTES_ACEITE = 'Pendentes de Aceite'
    PENDENTES_VALIDACAO = 'Pendentes de Validação'
    PARECER_FAVORAVEL = 'Parecer Favorável'
    VALIDADO = 'Validado'
    SITUACOES_CHOICES = (
        ('', 'Todas'),
        (PENDENTES_ACEITE, PENDENTES_ACEITE),
        (PENDENTES_VALIDACAO, PENDENTES_VALIDACAO),
        (PARECER_FAVORAVEL, PARECER_FAVORAVEL),
        (VALIDADO, VALIDADO),
    )
    edital = forms.ModelChoiceField(queryset=Edital.objects.order_by('-id'), empty_label='Selecione um Edital', label='Filtrar por Edital:', required=False)
    situacao = forms.ChoiceField(label='Filtrar por Situação', choices=SITUACOES_CHOICES, required=False)


class EditarProjetoEmExecucaoForm(forms.ModelFormPlus):
    class Meta:
        model = Projeto
        fields = ['valor_global_projeto', 'titulo', 'inicio_execucao', 'fim_execucao']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.edital.tem_formato_completo():
            del self.fields['valor_global_projeto']


class SupervisorForm(forms.FormPlus):
    AVALIACAO_STATUS = ((1, 'Projetos em conflito'), (0, 'Todos'))
    palavra_chave = forms.CharField(label='Nome do Supervisor', required=False)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=False, widget=forms.Select(attrs={'onchange': 'submeter_form(this)'}))

    situacao = forms.ChoiceField(choices=AVALIACAO_STATUS, label='Filtrar por Situação', required=False, widget=forms.Select(attrs={'onchange': 'submeter_form(this)'}))


class ProjetosAtrasadosForm(forms.FormPlus):
    SITUACAO_STATUS = ((1, 'Projetos em Atraso'), (2, 'Projetos com Atividades Atrasadas'), (3, 'Projetos em dia'), (0, 'Todos'))
    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')
    edital = forms.ModelChoiceField(
        queryset=Edital.objects.filter(formato=Edital.FORMATO_COMPLETO).order_by('-inicio_inscricoes'),
        empty_label='Selecione um Edital',
        label='Filtrar por Edital:',
        required=False,
    )
    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.uo(), empty_label='Selecione um Campus', label='Filtrar por Campus:', required=False)
    situacao = forms.ChoiceField(choices=SITUACAO_STATUS, label='Filtrar por Situação', required=False)

    METHOD = 'GET'

    def __init__(self, *args, **kwargs):
        self.ano = kwargs.pop('ano', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []
        if editais.exists():
            ANO_CHOICES.append(['', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            ANO_CHOICES += [(ano, str(ano)) for ano in range(ano_limite, ano_inicio, -1)]
        else:
            ANO_CHOICES.append(['', 'Nenhum edital cadastrado'])

        if self.ano:
            self.fields['edital'].queryset = Edital.objects.filter(inicio_inscricoes__year=self.ano)
        self.fields['ano'].choices = ANO_CHOICES
        if not self.request.user.has_perm('projetos.pode_visualizar_avaliadores_externos'):
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(id=get_uo(self.request.user).id)


class CancelarAvaliacaoEtapaForm(forms.ModelFormPlus):
    obs_cancelamento_avaliacao = forms.CharField(label='Motivo do Cancelamento', widget=forms.Textarea(), required=True)

    class Meta:
        model = RegistroExecucaoEtapa
        fields = ['obs_cancelamento_avaliacao']


class CancelarAvaliacaoGastoForm(forms.ModelFormPlus):
    obs_cancelamento_avaliacao = forms.CharField(label='Motivo do Cancelamento', widget=forms.Textarea(), required=True)

    class Meta:
        model = RegistroGasto
        fields = ['obs_cancelamento_avaliacao']


class IndicadoresForm(forms.FormPlus):
    PARTICIPACOES_PROJETOS = 'participacoes_projeto'

    INDICADORES_CHOICES = (('', 'Todos'), (PARTICIPACOES_PROJETOS, 'Participações em Projetos'))

    campus = forms.ModelChoiceField(
        queryset=UnidadeOrganizacional.objects.suap(),
        label='Filtrar por Campus:',
        empty_label='Todos',
        widget=forms.Select(attrs={'onchange': "$('#filtro').submit();"}),
        required=False,
    )
    indicador = forms.ChoiceField(
        choices=INDICADORES_CHOICES, label='Filtrar por tipo de Indicador:', widget=forms.Select(attrs={'onchange': "$('#filtro').submit();"}), required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pega os anos para exibir no filtro somente os anos que tem ocorrência do "Modelo"
        anos_choice = []  # [('', u'Todos')]
        datas = Projeto.objects.all().dates('inicio_execucao', 'year')
        for data in datas:
            ano = (data.year, str(data.year))
            anos_choice.append(ano)

        self.fields['ano_inicio'] = forms.ChoiceField(
            choices=anos_choice, label='Filtrar por Ano >=:', widget=forms.Select(attrs={'onchange': "$('#filtro').submit();"}), required=False
        )
        self.fields['ano_fim'] = forms.ChoiceField(
            choices=anos_choice, label='Filtrar por Ano <=:', widget=forms.Select(attrs={'onchange': "$('#filtro').submit();"}), required=False
        )


class CampusForm(forms.FormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Filtrar por Campus', required=False, empty_label='Todos')


class AnoForm(forms.FormPlus):
    METHOD = 'GET'
    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []
        if editais.exists():
            ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            ANO_CHOICES += [(ano, str(ano)) for ano in range(ano_limite, ano_inicio, -1)]
        else:
            ANO_CHOICES.append(['Selecione um ano', 'Nenhum edital cadastrado'])
        self.fields['ano'].choices = ANO_CHOICES


class EditaisForm(forms.FormPlus):
    METHOD = 'GET'
    INSCRICAO = 'Em Inscrição'
    PRE_SELECAO = 'Em Pré-Seleção'
    SELECAO = 'Em Seleção'
    EXECUCAO = 'Em Execução'
    CONCLUIDO = 'Concluído'
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Filtrar por Campus', required=False, empty_label='Todos')
    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')
    periodo = forms.ChoiceField(
        label='Período',
        required=False,
        choices=[('', 'Todos'), (INSCRICAO, INSCRICAO), (PRE_SELECAO, PRE_SELECAO), (SELECAO, SELECAO), (EXECUCAO, EXECUCAO), (CONCLUIDO, CONCLUIDO)],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []
        if editais.exists():
            ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            ANO_CHOICES += [(ano, str(ano)) for ano in range(ano_limite, ano_inicio, -1)]
        else:
            ANO_CHOICES.append(['Selecione um ano', 'Nenhum edital cadastrado'])
        self.fields['ano'].choices = ANO_CHOICES


class MeusProjetosForm(forms.FormPlus):
    METHOD = 'GET'

    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    TODOS = 'Todos'
    PROJETOS_EM_EDICAO = 'Projetos em Edição'
    PROJETOS_ENVIADOS = 'Projetos Enviados'
    PROJETOS_PRE_SELECIONADOS = 'Projetos Pré-Selecionados'
    PROJETOS_EM_EXECUCAO = 'Projetos em Execução'
    PROJETOS_ENCERRADOS = 'Projetos Encerrados'
    PROJETOS_CANCELADOS = 'Projetos Cancelados'

    AVALIACAO_STATUS = (
        (TODOS, TODOS),
        (PROJETOS_EM_EDICAO, PROJETOS_EM_EDICAO),
        (PROJETOS_ENVIADOS, PROJETOS_ENVIADOS),
        (PROJETOS_PRE_SELECIONADOS, PROJETOS_PRE_SELECIONADOS),
        (PROJETOS_EM_EXECUCAO, PROJETOS_EM_EXECUCAO),
        (PROJETOS_ENCERRADOS, PROJETOS_ENCERRADOS),
        (PROJETOS_CANCELADOS, PROJETOS_CANCELADOS),
    )
    edital = forms.ModelChoiceField(queryset=Edital.objects, empty_label='Selecione um Edital', label='Filtrar por Edital:', required=False)

    situacao = forms.ChoiceField(choices=AVALIACAO_STATUS, label='Filtrar por Situação', required=False)

    class Media:
        js = ['/static/pesquisa/js/meusprojetosform.js']

    def __init__(self, *args, **kwargs):
        self.ano = kwargs.pop('ano', None)
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []
        if editais.exists():
            ANO_CHOICES.append(['', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            ANO_CHOICES += [(ano, str(ano)) for ano in range(ano_limite, ano_inicio, -1)]
        else:
            ANO_CHOICES.append(['', 'Nenhum edital cadastrado'])

        if self.ano:
            self.fields['edital'].queryset = Edital.objects.filter(inicio_inscricoes__year=self.ano)
        self.fields['ano'].choices = ANO_CHOICES


class GerenciarSupervisorForm(forms.FormPlus):
    METHOD = 'GET'

    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    edital = forms.ModelChoiceField(queryset=Edital.objects, empty_label='Selecione um Edital', label='Filtrar por Edital:', required=False)

    class Media:
        js = ['/static/pesquisa/js/meusprojetosform.js']

    def __init__(self, *args, **kwargs):
        self.ano = kwargs.pop('ano', None)
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []
        if editais.exists():
            ANO_CHOICES.append(['', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            ANO_CHOICES += [(ano, str(ano)) for ano in range(ano_limite, ano_inicio, -1)]
        else:
            ANO_CHOICES.append(['', 'Nenhum edital cadastrado'])

        if self.ano:
            self.fields['edital'].queryset = Edital.objects.filter(inicio_inscricoes__year=self.ano)
        self.fields['ano'].choices = ANO_CHOICES


class EditalSubmissaoObraForm(forms.ModelFormPlus):
    linha_editorial = forms.ModelMultipleChoiceField(
        label='Linhas Editoriais', required=True, widget=FilteredSelectMultiplePlus('', True), queryset=LinhaEditorial.objects.order_by('nome')
    )

    class Meta:
        model = EditalSubmissaoObra
        fields = (
            'titulo',
            'linha_editorial',
            'arquivo',
            'data_inicio_submissao',
            'data_termino_submissao',
            'data_inicio_verificacao_plagio',
            'data_termino_verificacao_plagio',
            'data_inicio_analise_especialista',
            'data_termino_analise_especialista',
            'data_inicio_validacao_conselho',
            'data_termino_validacao_conselho',
            'data_inicio_termos',
            'data_termino_termos',
            'data_inicio_revisao_linguistica',
            'data_termino_revisao_linguistica',
            'data_inicio_diagramacao',
            'data_termino_diagramacao',
            'data_inicio_solicitacao_isbn',
            'data_termino_solicitacao_isbn',
            'data_inicio_impressao_boneco',
            'data_termino_impressao_boneco',
            'data_revisao_layout',
            'data_inicio_correcao_final',
            'data_termino_correcao_final',
            'data_inicio_analise_liberacao',
            'data_termino_analise_liberacao',
            'data_inicio_impressao',
            'data_termino_impressao',
            'data_lancamento',
            'local_lancamento',
            'observacoes_lancamento',
            'questionario_parecerista',
        )

    def clean(self):
        cleaned_data = super().clean()

        if (
            cleaned_data.get('data_inicio_submissao')
            and cleaned_data.get('data_termino_submissao')
            and cleaned_data.get('data_termino_submissao') < cleaned_data.get('data_inicio_submissao')
        ):
            self.add_error('data_termino_submissao', 'A data final de submissão não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_verificacao_plagio')
            and cleaned_data.get('data_termino_verificacao_plagio')
            and cleaned_data.get('data_termino_verificacao_plagio') < cleaned_data.get('data_inicio_verificacao_plagio')
        ):
            self.add_error('data_termino_verificacao_plagio', 'A data final de verificação de plágio não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_analise_especialista')
            and cleaned_data.get('data_termino_analise_especialista')
            and cleaned_data.get('data_termino_analise_especialista') < cleaned_data.get('data_inicio_analise_especialista')
        ):
            self.add_error('data_termino_analise_especialista', 'A data final da análise de especialista não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_validacao_conselho')
            and cleaned_data.get('data_termino_validacao_conselho')
            and cleaned_data.get('data_termino_validacao_conselho') < cleaned_data.get('data_inicio_validacao_conselho')
        ):
            self.add_error('data_termino_validacao_conselho', 'A data final da validação do conselho não pode ser menor do que a data de início.')

        if cleaned_data.get('data_inicio_termos') and cleaned_data.get('data_termino_termos') and cleaned_data.get('data_termino_termos') < cleaned_data.get('data_inicio_termos'):
            self.add_error('data_termino_termos', 'A data final dos termos não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_revisao_linguistica')
            and cleaned_data.get('data_termino_revisao_linguistica')
            and cleaned_data.get('data_termino_revisao_linguistica') < cleaned_data.get('data_inicio_revisao_linguistica')
        ):
            self.add_error('data_termino_revisao_linguistica', 'A data final da revisão linguística não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_diagramacao')
            and cleaned_data.get('data_termino_diagramacao')
            and cleaned_data.get('data_termino_diagramacao') < cleaned_data.get('data_inicio_diagramacao')
        ):
            self.add_error('data_termino_diagramacao', 'A data final da diagramação não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_solicitacao_isbn')
            and cleaned_data.get('data_termino_solicitacao_isbn')
            and cleaned_data.get('data_termino_solicitacao_isbn') < cleaned_data.get('data_inicio_solicitacao_isbn')
        ):
            self.add_error('data_termino_solicitacao_isbn', 'A data final da solicitação do ISBN não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_impressao_boneco')
            and cleaned_data.get('data_termino_impressao_boneco')
            and cleaned_data.get('data_termino_impressao_boneco') < cleaned_data.get('data_inicio_impressao_boneco')
        ):
            self.add_error('data_termino_impressao_boneco', 'A data final da impressão do boneco não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_correcao_final')
            and cleaned_data.get('data_termino_correcao_final')
            and cleaned_data.get('data_termino_correcao_final') < cleaned_data.get('data_inicio_correcao_final')
        ):
            self.add_error('data_termino_correcao_final', 'A data final da correção final não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_analise_liberacao')
            and cleaned_data.get('data_termino_analise_liberacao')
            and cleaned_data.get('data_termino_analise_liberacao') < cleaned_data.get('data_inicio_analise_liberacao')
        ):
            self.add_error('data_termino_analise_liberacao', 'A data final da análise de liberação não pode ser menor do que a data de início.')

        if (
            cleaned_data.get('data_inicio_impressao')
            and cleaned_data.get('data_termino_impressao')
            and cleaned_data.get('data_termino_impressao') < cleaned_data.get('data_inicio_impressao')
        ):
            self.add_error('data_termino_impressao', 'A data final da impressão não pode ser menor do que a data de início.')

        return cleaned_data


class SubmeterObraForm(forms.ModelFormPlus):
    linha_editorial = forms.ModelChoiceField(LinhaEditorial.objects, label='Linha Editorial')
    cidade = forms.ModelChoiceFieldPlus(Cidade.objects, label='Cidade', required=False, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS))
    area = forms.ModelChoiceField(queryset=AreaConhecimento.objects.filter(superior__isnull=True).exclude(descricao='MULTIDISCIPLINAR'), label='Área')
    sinopse = forms.CharFieldPlus(label='Sinopse', widget=forms.Textarea(), max_length=556)
    sinopse_quarta_capa = forms.CharFieldPlus(label='Sinopse para Quarta Capa', widget=forms.Textarea(), max_length=1050)
    biografia_autor_organizador = forms.CharFieldPlus(label='Biografia do Autor/Organizador', widget=forms.Textarea(), max_length=660)
    eh_autor_organizador = forms.BooleanField(label='Você é o Autor ou Organizador desta obra?', required=False)
    leu_politica_editorial = forms.BooleanField(
        label='Declaro ter lido os seguintes documentos: Política editorial, Direitos Autorais e Autorização de publicação da obra', required=True
    )
    telefone = forms.BrTelefoneField(max_length=255, required=True, label='Telefone', help_text='Formato: "(XX) XXXXX-XXXX"')
    cpf = forms.BrCpfField(max_length=25, required=False, label='CPF', help_text='Formato: "XXX.XXX.XXX-XX"')
    cep = forms.BrCepField(max_length=25, required=False, label='CEP', help_text='Formato: "XXXXX-XXX"')

    class Meta:
        model = Obra
        fields = (
            'tipo_autor',
            'foto_autor_organizador',
            'biografia_autor_organizador',
            'telefone',
            'termo_compromisso_autor_editora',
            'titulo',
            'sinopse',
            'sinopse_quarta_capa',
            'linha_editorial',
            'area',
            'nucleos_pesquisa',
            'tipo_submissao',
            'recurso_impressao',
            'arquivo',
            'obra_sem_identificacao_autor',
        )

    fieldsets = (
        ('Dados do Autor/Organizador', {'fields': ('tipo_autor', 'biografia_autor_organizador', 'telefone', 'foto_autor_organizador', 'termo_compromisso_autor_editora')}),
        ('Dados da Obra', {'fields': ('titulo', 'sinopse', 'sinopse_quarta_capa', 'linha_editorial', 'area', 'nucleos_pesquisa', 'tipo_submissao', 'recurso_impressao')}),
        ('Arquivo da Obra', {'fields': ('arquivo', 'obra_sem_identificacao_autor')}),
        ('Declaração de Aceitação dos Termos e Condições para Publicação da Obra', {'fields': ('leu_politica_editorial',)}),
    )

    class Media:
        js = ['/static/pesquisa/js/submeterobraform.js']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['termo_compromisso_autor_editora'].required = True
        self.fields['linha_editorial'].queryset = LinhaEditorial.objects.filter(id__in=self.instance.edital.linha_editorial.values_list('id', flat=True))
        self.fields['sinopse'].label = 'Sinopse para Catálogo'
        self.fields['sinopse'].help_text = ' Sinopse curta que estará em catálogo da Editora {}, quando houver a publicação. Número máximo de caracteres: 556'.format(
            Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
        )
        self.fields['sinopse_quarta_capa'].help_text = 'Número máximo de caracteres: 1050'
        self.fields['foto_autor_organizador'].required = True
        self.fields['biografia_autor_organizador'].help_text = 'Número máximo de caracteres: 660'


class MembroObraForm(forms.ModelFormPlus):
    telefone = forms.BrTelefoneField(max_length=255, required=True, label='Telefone', help_text='Formato: "(XX) XXXXX-XXXX"')
    cpf = forms.BrCpfField(max_length=25, required=True, label='CPF', help_text='Formato: "XXX.XXX.XXX-XX"')
    cep = forms.BrCepField(max_length=25, required=True, label='CEP', help_text='Formato: "XXXXX-XXX"')
    cidade = forms.ModelChoiceFieldPlus(Cidade.objects, label='Cidade', required=True, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS))

    class Meta:
        model = MembroObra
        fields = ('nome', 'endereco', 'complemento', 'bairro', 'cep', 'cidade', 'rg', 'rg_orgao_emissor', 'cpf', 'sexo', 'estado_civil', 'profissao', 'email', 'telefone')


class JustificativaPreAvaliacaoForm(forms.ModelFormPlus):
    class Meta:
        model = Projeto
        fields = ('obs_reprovacao',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['obs_reprovacao'].label = 'Justificativa da Pré-Avaliação'
        self.fields['obs_reprovacao'].required = True


class VerificaAutenticidadeForm(forms.ModelFormPlus):
    autenticidade_obs = forms.CharFieldPlus(label='Observações', required=False, widget=forms.Textarea())

    class Meta:
        model = Obra
        fields = ('autentica', 'autenticidade_obs')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['autentica'].required = True


class AvaliacaoPareceristaObraForm(forms.ModelFormPlus):
    comentario = RichTextFormField(label='Observações Complementares')
    nota = forms.ChoiceField(label='Nota', choices=[])

    class Meta:
        model = ParecerObra
        fields = ('situacao', 'nota', 'comentario', 'arquivo_parecer_area')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nota'].required = True
        self.fields['arquivo_parecer_area'].required = True

        nota_choices = []
        maior_nota = (10 * 10) + 1
        notas = [x * 0.1 for x in range(maior_nota)]
        notas.sort(reverse=True)
        for nota in notas:
            nota_choices.append([str(nota), str(nota)])
        self.fields['nota'].choices = nota_choices
        if self.instance.nota:
            self.initial['nota'] = str(round(self.instance.nota, 2))


class ReenviarObraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = ('obra_corrigida',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['obra_corrigida'].required = True


class RevisarAutorForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = ('revisada_pelo_autor',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['revisada_pelo_autor'].required = True


class AvaliacaoConselhoEditorialForm(forms.ModelFormPlus):
    obs_conselho_editorial = RichTextFormField(label='Observações')

    class Meta:
        model = Obra
        fields = ('situacao_conselho_editorial', 'obs_conselho_editorial')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['situacao_conselho_editorial'].required = True
        self.fields['situacao_conselho_editorial'].label = 'Parecer'


class AnaliseLiberacaoForm(forms.ModelFormPlus):
    obs_liberacao_publicacao = forms.CharFieldPlus(label='Observações', widget=forms.Textarea())

    class Meta:
        model = Obra
        fields = ('aprovacao_liberacao_publicacao', 'obs_liberacao_publicacao')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['aprovacao_liberacao_publicacao'].required = True
        self.fields['obs_liberacao_publicacao'].required = True


class AceiteEditoraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = ('status_obra',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status_obra'].required = True


class UploadTermosForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = (
            'termo_autorizacao_publicacao',
            'termo_cessao_direitos_autorais',
            'termo_uso_imagem',
            'termo_nome_menor',
            'contrato_cessao_direitos',
            'termo_autorizacao_uso_imagem',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['termo_autorizacao_publicacao'].required = True
        self.fields['termo_cessao_direitos_autorais'].required = True

        if self.instance.termo_autorizacao_publicacao_assinado == Obra.SIM:
            del self.fields['termo_autorizacao_publicacao']
        if self.instance.termo_cessao_direitos_autorais_assinado == Obra.SIM:
            del self.fields['termo_cessao_direitos_autorais']

        if self.instance.termo_uso_imagem_assinado == Obra.SIM:
            del self.fields['termo_uso_imagem']
        if self.instance.termo_nome_menor_assinado == Obra.SIM:
            del self.fields['termo_nome_menor']
        if self.instance.contrato_cessao_direitos_assinado == Obra.SIM:
            del self.fields['contrato_cessao_direitos']
        if self.instance.termo_autorizacao_uso_imagem_assinado == Obra.SIM:
            del self.fields['termo_autorizacao_uso_imagem']


class TermoAssinadoForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = (
            'termo_autorizacao_publicacao_assinado',
            'termo_cessao_direitos_autorais_assinado',
            'termo_uso_imagem_assinado',
            'termo_nome_menor_assinado',
            'contrato_cessao_direitos_assinado',
            'termo_autorizacao_uso_imagem_assinado',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.termo_autorizacao_publicacao or self.instance.termo_autorizacao_publicacao == Obra.NAO:
            self.fields['termo_autorizacao_publicacao_assinado'].required = True
        if not self.instance.termo_cessao_direitos_autorais or self.instance.termo_cessao_direitos_autorais == Obra.NAO:
            self.fields['termo_cessao_direitos_autorais_assinado'].required = True

        if self.instance.termo_uso_imagem == Obra.NAO:
            self.fields['termo_uso_imagem_assinado'].required = True
        if self.instance.termo_nome_menor == Obra.NAO:
            self.fields['termo_nome_menor_assinado'].required = True
        if self.instance.contrato_cessao_direitos == Obra.NAO:
            self.fields['contrato_cessao_direitos_assinado'].required = True
        if self.instance.termo_autorizacao_uso_imagem == Obra.NAO:
            self.fields['termo_autorizacao_uso_imagem_assinado'].required = True


class RevisarObraForm(forms.ModelFormPlus):
    obs_revisor = forms.CharFieldPlus(label='Observações do Revisor', widget=forms.Textarea(), required=False)

    class Meta:
        model = Obra
        fields = ('arquivo_obra_revisada', 'link_obra_revisada', 'obs_revisor')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['arquivo_obra_revisada'].required = True


class ConclusaoObraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = ('obra_concluida',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['obra_concluida'].required = True


class EmitirParecerRevisaoObraForm(forms.ModelFormPlus):
    parecer_revisor = forms.CharFieldPlus(label='Parecer do Revisor', widget=forms.Textarea())

    class Meta:
        model = Obra
        fields = ('parecer_revisor', 'versao_final_revisao')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['versao_final_revisao'].required = True


class CadastrarDiagramacaoObraForm(forms.ModelFormPlus):
    obs_diagramador = forms.CharFieldPlus(label='Observações do Diagramador', widget=forms.Textarea(), required=False)

    class Meta:
        model = Obra
        fields = (
            'arquivo_diagramacao_capa',
            'arquivo_diagramacao_miolo',
            'arquivo_diagramacao_capa_impresso',
            'arquivo_diagramacao_miolo_impresso',
            'arquivo_diagramacao_versao_final',
            'diagramacao_link',
            'obs_diagramador',
            'arquivo_diagramacao_versao_final_ebook',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['arquivo_diagramacao_miolo'].required = True
        self.fields['arquivo_diagramacao_capa'].required = True
        if not self.instance.tipo_submissao == Obra.IMPRESSO:
            del self.fields['arquivo_diagramacao_capa_impresso']
            del self.fields['arquivo_diagramacao_miolo_impresso']
            self.fields['arquivo_diagramacao_capa'].label = f'Diagramação da Capa - {self.instance.tipo_submissao}'
            self.fields['arquivo_diagramacao_miolo'].label = f'Diagramação do Miolo - {self.instance.tipo_submissao}'
        else:
            self.fields['arquivo_diagramacao_capa'].label = 'Diagramação da Capa - Ebook'
            self.fields['arquivo_diagramacao_miolo'].label = 'Diagramação do Miolo - Ebook'
            self.fields['arquivo_diagramacao_capa_impresso'].label = 'Diagramação da Capa - Impresso'
            self.fields['arquivo_diagramacao_miolo_impresso'].label = 'Diagramação do Miolo - Impresso'
            self.fields['arquivo_diagramacao_capa_impresso'].required = True
            self.fields['arquivo_diagramacao_miolo_impresso'].required = True

        if not self.instance.diagramacao_avaliada_em:
            del self.fields['arquivo_diagramacao_versao_final_ebook']
        else:
            self.fields['arquivo_diagramacao_versao_final_ebook'].required = True


class CadastrarISBNObraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = ('isbn', 'isbn_impresso')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.tipo_submissao != Obra.IMPRESSO:
            self.fields['isbn'].label = f'ISBN ({self.instance.tipo_submissao})'
            self.fields['isbn'].required = True
            del self.fields['isbn_impresso']
        else:
            self.fields['isbn'].label = 'ISBN (Ebook)'
            self.fields['isbn'].required = True
            self.fields['isbn_impresso'].required = True


class AvaliacaoDiagramacaoForm(forms.ModelFormPlus):
    justificativa_capa = forms.CharFieldPlus(
        label='Justificativa', widget=forms.Textarea(), required=False, help_text='Em caso de reprovação, por qualquer motivo, indique sua sugestão ou crítica.'
    )
    justificativa_capa_impresso = forms.CharFieldPlus(
        label='Justificativa', widget=forms.Textarea(), required=False, help_text='Em caso de reprovação, por qualquer motivo, indique sua sugestão ou crítica.'
    )
    justificativa_miolo = forms.CharFieldPlus(
        label='Justificativa', widget=forms.Textarea(), required=False, help_text='Em caso de reprovação, por qualquer motivo, indique sua sugestão ou crítica.'
    )
    justificativa_miolo_impresso = forms.CharFieldPlus(
        label='Justificativa', widget=forms.Textarea(), required=False, help_text='Em caso de reprovação, por qualquer motivo, indique sua sugestão ou crítica.'
    )

    class Meta:
        model = Obra
        fields = (
            'diagramacao_capa_aprovada',
            'justificativa_capa',
            'diagramacao_miolo_aprovada',
            'justificativa_miolo',
            'diagramacao_capa_aprovada_impresso',
            'justificativa_capa_impresso',
            'diagramacao_miolo_aprovada_impresso',
            'justificativa_miolo_impresso',
            'obs_sobre_diagramacao',
        )

    class Media:
        js = ['/static/pesquisa/js/avaliacaodiagramacaoform.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diagramacao_capa_aprovada'].required = True
        self.fields['diagramacao_miolo_aprovada'].required = True
        if not self.instance.tipo_submissao == Obra.IMPRESSO:
            del self.fields['diagramacao_capa_aprovada_impresso']
            del self.fields['diagramacao_miolo_aprovada_impresso']
            del self.fields['justificativa_capa_impresso']
            del self.fields['justificativa_miolo_impresso']
            self.fields['diagramacao_capa_aprovada'].label = f'Aprovar Capa - {self.instance.tipo_submissao}'
            self.fields['diagramacao_miolo_aprovada'].label = f'Aprovar Miolo - {self.instance.tipo_submissao}'
        else:
            self.fields['diagramacao_capa_aprovada'].label = 'Aprovar Capa - Ebook'
            self.fields['diagramacao_miolo_aprovada'].label = 'Aprovar Miolo - Ebook'
            self.fields['diagramacao_capa_aprovada_impresso'].label = 'Aprovar Capa - Impresso'
            self.fields['diagramacao_miolo_aprovada_impresso'].label = 'Aprovar Miolo - Impresso'
            self.fields['diagramacao_capa_aprovada_impresso'].required = True
            self.fields['diagramacao_miolo_aprovada_impresso'].required = True

    def clean(self, *args, **kwargs):
        if self.cleaned_data.get('diagramacao_capa_aprovada') == Obra.NAO and not self.cleaned_data.get('justificativa_capa'):
            self.add_error('justificativa_capa', 'Informe a justificativa para a reprovação.')
        if self.cleaned_data.get('diagramacao_miolo_aprovada') == Obra.NAO and not self.cleaned_data.get('justificativa_miolo'):
            self.add_error('justificativa_miolo', 'Informe a justificativa para a reprovação.')
        if self.instance.tipo_submissao == Obra.IMPRESSO:
            if self.cleaned_data.get('diagramacao_capa_aprovada_impresso') == Obra.NAO and not self.cleaned_data.get('justificativa_capa_impresso'):
                self.add_error('justificativa_capa_impresso', 'Informe a justificativa para a reprovação.')
            if self.cleaned_data.get('diagramacao_miolo_aprovada_impresso') == Obra.NAO and not self.cleaned_data.get('justificativa_miolo_impresso'):
                self.add_error('justificativa_miolo_impresso', 'Informe a justificativa para a reprovação.')

        return super().clean(*args, **kwargs)


class FichaCatalograficaForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = ('ficha_catalografica', 'ficha_catalografica_impresso')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.tipo_submissao != Obra.IMPRESSO:
            self.fields['ficha_catalografica'].label = f'Ficha Catalográfica ({self.instance.tipo_submissao})'
            del self.fields['ficha_catalografica_impresso']
        else:
            self.fields['ficha_catalografica'].label = 'Ficha Catalográfica (Ebook)'


class PublicacaoObraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = (
            'situacao_publicacao',
            'num_copias',
            'data_envio_impressao',
            'link_repositorio_virtual',
            'data_liberacao_repositorio_virtual',
            'bibliotecas_campi',
            'acervo_fisico',
            'biblioteca_nacional',
            'publicacao_autor',
            'publicacao_coautor',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.submetido_por_vinculo == self.request.user.get_vinculo():
            del self.fields['situacao_publicacao']
            del self.fields['num_copias']
            del self.fields['data_envio_impressao']
            del self.fields['link_repositorio_virtual']
            del self.fields['bibliotecas_campi']
            del self.fields['acervo_fisico']
            del self.fields['biblioteca_nacional']
            del self.fields['publicacao_autor']
            del self.fields['publicacao_coautor']
        else:
            del self.fields['data_liberacao_repositorio_virtual']
            self.fieldsets = (
                ('Publicação', {'fields': (('situacao_publicacao',), ('num_copias',), ('data_envio_impressao',), ('link_repositorio_virtual',))}),
                ('Distribuição', {'fields': (('bibliotecas_campi',), ('acervo_fisico',), ('biblioteca_nacional',), ('publicacao_autor',), ('publicacao_coautor',))}),
            )


class IndicarPareceristaForm(forms.FormPlus):
    user = forms.MultipleModelChoiceFieldPlus(queryset=User.objects, label='Usuário', help_text="Informe parte do nome/matrícula/email institucional")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ids_usuarios = UsuarioGrupo.objects.filter(group__name='Parecerista de Obra').only('user').values_list('user_id', flat=True)
        self.fields['user'].queryset = User.objects.filter(is_active=True, id__in=ids_usuarios)


class IndicarConselheiroForm(forms.FormPlus):
    user = forms.MultipleModelChoiceFieldPlus(queryset=User.objects, label='Usuário', help_text="Informe parte do nome/matrícula/email institucional")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ids_usuarios = UsuarioGrupo.objects.filter(group__name='Conselheiro Editorial').values_list('user', flat=True)
        self.fields['user'].queryset = User.objects.filter(is_active=True, id__in=ids_usuarios)


class IndicarRevisorForm(forms.FormPlus):
    user = forms.MultipleModelChoiceFieldPlus(queryset=User.objects, label='Usuário', help_text="Informe parte do nome/matrícula/email institucional")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ids_usuarios = UsuarioGrupo.objects.filter(group__name='Revisor de Obra').values_list('user', flat=True)
        self.fields['user'].queryset = User.objects.filter(is_active=True, id__in=ids_usuarios)


class IndicarDiagramadorForm(forms.FormPlus):
    user = forms.MultipleModelChoiceFieldPlus(queryset=User.objects, label='Usuário', help_text="Informe parte do nome/matrícula/email institucional")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ids_usuarios = UsuarioGrupo.objects.filter(group__name='Diagramador de Obra').values_list('user', flat=True)
        self.fields['user'].queryset = User.objects.filter(is_active=True, id__in=ids_usuarios)


class ChecklistObraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = (
            'checklist_capa_nome_autor',
            'checklist_capa_titulo',
            'checklist_capa_subtitulo',
            'checklist_capa_marca_editora',
            'checklist_capa_marca_serie',
            'checklist_capa_marca_colecao',
            'checklist_orelha_texto_editora',
            'checklist_orelha_marca_editora',
            'checklist_lombada_nome_autor',
            'checklist_lombada_titulo',
            'checklist_lombada_marca_editora',
            'checklist_quarta_capa_sinopse',
            'checklist_quarta_capa_codigo_isbn',
            'checklist_quarta_capa_marca_instituicao',
            'checklist_quarta_capa_abeu',
            'checklist_quarta_capa_comemorativa',
            'checklist_orelha_verso_foto_autor',
            'checklist_orelha_verso_nome_autor',
            'checklist_orelha_verso_texto_autor',
            'checklist_folha_rosto_nome_autor',
            'checklist_folha_rosto_titulo',
            'checklist_folha_rosto_subtitulo',
            'checklist_folha_rosto_editora',
            'checklist_folha_rosto_cidade_ano',
            'checklist_ficha_tecnica_institucional',
            'checklist_ficha_tecnica_marca',
            'checklist_ficha_tecnica_conselho',
            'checklist_ficha_tecnica_creditos',
            'checklist_ficha_tecnica_formato',
            'checklist_ficha_tecnica_prefixo',
            'checklist_ficha_tecnica_linha',
            'checklist_ficha_tecnica_link',
            'checklist_ficha_tecnica_marca_editora',
            'checklist_ficha_tecnica_endereco',
            'checklist_ficha_tecnica_edital',
            'checklist_ficha_catalografica_nome',
            'checklist_ficha_catalografica_titulo',
            'checklist_ficha_catalografica_autores',
            'checklist_ficha_catalografica_paginas',
            'checklist_ficha_catalografica_ano',
            'checklist_miolo_prefacio',
            'checklist_miolo_apresentacao',
            'checklist_miolo_sumario',
            'checklist_miolo_sequencia',
            'checklist_miolo_num_paginas',
            'checklist_miolo_titulos',
            'checklist_miolo_imagens',
            'checklist_miolo_margens',
            'checklist_miolo_sangrias',
            'checklist_pagina_final_marca',
            'checklist_colofao_tipografias',
            'checklist_colofao_papel_capa',
            'checklist_colofao_papel_miolo',
            'checklist_colofao_grafica',
            'checklist_colofao_copyright',
            'checklist_revisao_ortografica',
            'checklist_revisao_linguistica',
            'checklist_revisao_normalizacao',
            'checklist_divulgacao_midias',
            'checklist_divulgacao_convite_virtual',
            'checklist_divulgacao_convite_impresso',
            'checklist_divulgacao_repositorio',
            'checklist_tipo_arquivo_ebook',
            'checklist_tipo_arquivo_impresso',
        )

    fieldsets = (
        (
            'Capa',
            {
                'fields': (
                    ('checklist_capa_nome_autor',),
                    ('checklist_capa_titulo',),
                    ('checklist_capa_subtitulo',),
                    ('checklist_capa_marca_editora',),
                    ('checklist_capa_marca_serie',),
                    ('checklist_capa_marca_colecao',),
                )
            },
        ),
        ('Orelha Frente', {'fields': (('checklist_orelha_texto_editora',), ('checklist_orelha_marca_editora',))}),
        ('Lombada', {'fields': (('checklist_lombada_nome_autor',), ('checklist_lombada_titulo',), ('checklist_lombada_marca_editora',))}),
        (
            'Quarta Capa',
            {
                'fields': (
                    ('checklist_quarta_capa_sinopse',),
                    ('checklist_quarta_capa_codigo_isbn',),
                    ('checklist_quarta_capa_marca_instituicao',),
                    ('checklist_quarta_capa_abeu',),
                    ('checklist_quarta_capa_comemorativa',),
                )
            },
        ),
        ('Orelha Verso', {'fields': (('checklist_orelha_verso_foto_autor',), ('checklist_orelha_verso_nome_autor',), ('checklist_orelha_verso_texto_autor',))}),
        (
            'Folha de Rosto',
            {
                'fields': (
                    ('checklist_folha_rosto_nome_autor',),
                    ('checklist_folha_rosto_titulo',),
                    ('checklist_folha_rosto_subtitulo',),
                    ('checklist_folha_rosto_editora',),
                    ('checklist_folha_rosto_cidade_ano',),
                )
            },
        ),
        (
            'Ficha Técnica',
            {
                'fields': (
                    ('checklist_ficha_tecnica_institucional',),
                    ('checklist_ficha_tecnica_marca',),
                    ('checklist_ficha_tecnica_conselho',),
                    ('checklist_ficha_tecnica_creditos',),
                    ('checklist_ficha_tecnica_formato',),
                    ('checklist_ficha_tecnica_prefixo',),
                    ('checklist_ficha_tecnica_linha',),
                    ('checklist_ficha_tecnica_link',),
                    ('checklist_ficha_tecnica_marca_editora',),
                    ('checklist_ficha_tecnica_endereco',),
                    ('checklist_ficha_tecnica_edital',),
                )
            },
        ),
        (
            'Ficha Catalográfica',
            {
                'fields': (
                    ('checklist_ficha_catalografica_nome',),
                    ('checklist_ficha_catalografica_titulo',),
                    ('checklist_ficha_catalografica_autores',),
                    ('checklist_ficha_catalografica_paginas',),
                    ('checklist_ficha_catalografica_ano',),
                )
            },
        ),
        (
            'Miolo',
            {
                'fields': (
                    ('checklist_miolo_prefacio',),
                    ('checklist_miolo_apresentacao',),
                    ('checklist_miolo_sumario',),
                    ('checklist_miolo_sequencia',),
                    ('checklist_miolo_num_paginas',),
                    ('checklist_miolo_titulos',),
                    ('checklist_miolo_imagens',),
                    ('checklist_miolo_margens',),
                    ('checklist_miolo_sangrias',),
                )
            },
        ),
        ('Página Final', {'fields': (('checklist_pagina_final_marca',),)}),
        (
            'Colofão',
            {
                'fields': (
                    ('checklist_colofao_tipografias',),
                    ('checklist_colofao_papel_capa',),
                    ('checklist_colofao_papel_miolo',),
                    ('checklist_colofao_grafica',),
                    ('checklist_colofao_copyright',),
                )
            },
        ),
        ('Revisão', {'fields': (('checklist_revisao_ortografica',), ('checklist_revisao_linguistica',), ('checklist_revisao_normalizacao',))}),
        (
            'Divulgação',
            {
                'fields': (
                    ('checklist_divulgacao_midias',),
                    ('checklist_divulgacao_convite_virtual',),
                    ('checklist_divulgacao_convite_impresso',),
                    ('checklist_divulgacao_repositorio',),
                )
            },
        ),
        ('Tipo de Arquivo', {'fields': (('checklist_tipo_arquivo_ebook',), ('checklist_tipo_arquivo_impresso',))}),
    )


class ChecklistObraDiagramadorForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = (
            'checklist_diagramador_capa_nome_autor',
            'checklist_diagramador_capa_titulo',
            'checklist_diagramador_capa_subtitulo',
            'checklist_diagramador_capa_marca_editora',
            'checklist_diagramador_capa_marca_serie',
            'checklist_diagramador_capa_marca_colecao',
            'checklist_diagramador_orelha_texto_editora',
            'checklist_diagramador_orelha_marca_editora',
            'checklist_diagramador_lombada_nome_autor',
            'checklist_diagramador_lombada_titulo',
            'checklist_diagramador_lombada_marca_editora',
            'checklist_diagramador_quarta_capa_sinopse',
            'checklist_diagramador_quarta_capa_codigo_isbn',
            'checklist_diagramador_quarta_capa_marca_instituicao',
            'checklist_diagramador_quarta_capa_abeu',
            'checklist_diagramador_quarta_capa_comemorativa',
            'checklist_diagramador_orelha_verso_foto_autor',
            'checklist_diagramador_orelha_verso_nome_autor',
            'checklist_diagramador_orelha_verso_texto_autor',
            'checklist_diagramador_folha_rosto_nome_autor',
            'checklist_diagramador_folha_rosto_titulo',
            'checklist_diagramador_folha_rosto_subtitulo',
            'checklist_diagramador_folha_rosto_editora',
            'checklist_diagramador_folha_rosto_cidade_ano',
            'checklist_diagramador_ficha_tecnica_institucional',
            'checklist_diagramador_ficha_tecnica_marca',
            'checklist_diagramador_ficha_tecnica_conselho',
            'checklist_diagramador_ficha_tecnica_creditos',
            'checklist_diagramador_ficha_tecnica_formato',
            'checklist_diagramador_ficha_tecnica_prefixo',
            'checklist_diagramador_ficha_tecnica_linha',
            'checklist_diagramador_ficha_tecnica_link',
            'checklist_diagramador_ficha_tecnica_marca_editora',
            'checklist_diagramador_ficha_tecnica_endereco',
            'checklist_diagramador_ficha_tecnica_edital',
            'checklist_diagramador_ficha_catalografica_nome',
            'checklist_diagramador_ficha_catalografica_titulo',
            'checklist_diagramador_ficha_catalografica_autores',
            'checklist_diagramador_ficha_catalografica_paginas',
            'checklist_diagramador_ficha_catalografica_ano',
            'checklist_diagramador_miolo_prefacio',
            'checklist_diagramador_miolo_apresentacao',
            'checklist_diagramador_miolo_sumario',
            'checklist_diagramador_miolo_sequencia',
            'checklist_diagramador_miolo_num_paginas',
            'checklist_diagramador_miolo_titulos',
            'checklist_diagramador_miolo_imagens',
            'checklist_diagramador_miolo_margens',
            'checklist_diagramador_miolo_sangrias',
            'checklist_miolo_alerta_reproducao',
            'checklist_diagramador_pagina_final_marca',
            'checklist_diagramador_colofao_tipografias',
            'checklist_diagramador_colofao_papel_capa',
            'checklist_diagramador_colofao_papel_miolo',
            'checklist_diagramador_colofao_grafica',
            'checklist_diagramador_colofao_copyright',
            'checklist_diagramador_divulgacao_midias',
            'checklist_diagramador_divulgacao_convite_virtual',
            'checklist_diagramador_divulgacao_convite_impresso',
            'checklist_diagramador_divulgacao_repositorio',
            'checklist_diagramador_tipo_arquivo_ebook',
            'checklist_diagramador_tipo_arquivo_impresso',
        )

    fieldsets = (
        (
            'Capa',
            {
                'fields': (
                    ('checklist_diagramador_capa_nome_autor',),
                    ('checklist_diagramador_capa_titulo',),
                    ('checklist_diagramador_capa_subtitulo',),
                    ('checklist_diagramador_capa_marca_editora',),
                    ('checklist_diagramador_capa_marca_serie',),
                    ('checklist_diagramador_capa_marca_colecao',),
                )
            },
        ),
        ('Orelha Frente', {'fields': (('checklist_diagramador_orelha_texto_editora',), ('checklist_diagramador_orelha_marca_editora',))}),
        ('Lombada', {'fields': (('checklist_diagramador_lombada_nome_autor',), ('checklist_diagramador_lombada_titulo',), ('checklist_diagramador_lombada_marca_editora',))}),
        (
            'Quarta Capa',
            {
                'fields': (
                    ('checklist_diagramador_quarta_capa_sinopse',),
                    ('checklist_diagramador_quarta_capa_codigo_isbn',),
                    ('checklist_diagramador_quarta_capa_marca_instituicao',),
                    ('checklist_diagramador_quarta_capa_abeu',),
                    ('checklist_diagramador_quarta_capa_comemorativa',),
                )
            },
        ),
        (
            'Orelha Verso',
            {
                'fields': (
                    ('checklist_diagramador_orelha_verso_foto_autor',),
                    ('checklist_diagramador_orelha_verso_nome_autor',),
                    ('checklist_diagramador_orelha_verso_texto_autor',),
                )
            },
        ),
        (
            'Folha de Rosto',
            {
                'fields': (
                    ('checklist_diagramador_folha_rosto_nome_autor',),
                    ('checklist_diagramador_folha_rosto_titulo',),
                    ('checklist_diagramador_folha_rosto_subtitulo',),
                    ('checklist_diagramador_folha_rosto_editora',),
                    ('checklist_diagramador_folha_rosto_cidade_ano',),
                )
            },
        ),
        (
            'Ficha Técnica',
            {
                'fields': (
                    ('checklist_diagramador_ficha_tecnica_institucional',),
                    ('checklist_diagramador_ficha_tecnica_marca',),
                    ('checklist_diagramador_ficha_tecnica_conselho',),
                    ('checklist_diagramador_ficha_tecnica_creditos',),
                    ('checklist_diagramador_ficha_tecnica_formato',),
                    ('checklist_diagramador_ficha_tecnica_prefixo',),
                    ('checklist_diagramador_ficha_tecnica_linha',),
                    ('checklist_diagramador_ficha_tecnica_link',),
                    ('checklist_diagramador_ficha_tecnica_marca_editora',),
                    ('checklist_diagramador_ficha_tecnica_endereco',),
                    ('checklist_diagramador_ficha_tecnica_edital',),
                )
            },
        ),
        (
            'Ficha Catalográfica',
            {
                'fields': (
                    ('checklist_diagramador_ficha_catalografica_nome',),
                    ('checklist_diagramador_ficha_catalografica_titulo',),
                    ('checklist_diagramador_ficha_catalografica_autores',),
                    ('checklist_diagramador_ficha_catalografica_paginas',),
                    ('checklist_diagramador_ficha_catalografica_ano',),
                )
            },
        ),
        (
            'Miolo',
            {
                'fields': (
                    ('checklist_diagramador_miolo_prefacio',),
                    ('checklist_diagramador_miolo_apresentacao',),
                    ('checklist_diagramador_miolo_sumario',),
                    ('checklist_diagramador_miolo_sequencia',),
                    ('checklist_diagramador_miolo_num_paginas',),
                    ('checklist_diagramador_miolo_titulos',),
                    ('checklist_diagramador_miolo_imagens',),
                    ('checklist_diagramador_miolo_margens',),
                    ('checklist_diagramador_miolo_sangrias',),
                    ('checklist_miolo_alerta_reproducao',),
                )
            },
        ),
        ('Página Final', {'fields': (('checklist_diagramador_pagina_final_marca',),)}),
        (
            'Colofão',
            {
                'fields': (
                    ('checklist_diagramador_colofao_tipografias',),
                    ('checklist_diagramador_colofao_papel_capa',),
                    ('checklist_diagramador_colofao_papel_miolo',),
                    ('checklist_diagramador_colofao_grafica',),
                    ('checklist_diagramador_colofao_copyright',),
                )
            },
        ),
        (
            'Divulgação',
            {
                'fields': (
                    ('checklist_diagramador_divulgacao_midias',),
                    ('checklist_diagramador_divulgacao_convite_virtual',),
                    ('checklist_diagramador_divulgacao_convite_impresso',),
                    ('checklist_diagramador_divulgacao_repositorio',),
                )
            },
        ),
        ('Tipo de Arquivo', {'fields': (('checklist_diagramador_tipo_arquivo_ebook',), ('checklist_diagramador_tipo_arquivo_impresso',))}),
    )


class PessoaExternaObraForm(forms.ModelFormPlus):
    cidade = forms.ModelChoiceFieldPlus(Cidade.objects, label='Cidade', required=True, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS))
    email_secundario = forms.EmailField(label='Email Alternativo', help_text='Informe um email diferente do institucional.')
    telefone = forms.BrTelefoneField(max_length=255, required=False, label='Telefone', help_text='Formato: "(XX) XXXXX-XXXX"')
    cpf = forms.BrCpfField(max_length=25, required=True, label='CPF', help_text='Formato: "XXX.XXX.XXX-XX"')
    cep = forms.BrCepField(max_length=25, required=False, label='CEP', help_text='Formato: "XXXXX-XXX"')
    eh_parecerista = forms.BooleanField(
        label='Esta pessoa é parecerista?', required=False, help_text='Caso este campo seja marcado, esta pessoa será adicionada automaticamente do grupo "Parecerista de Obra"'
    )
    areas_de_conhecimento = forms.ModelMultiplePopupChoiceField(AreaConhecimento.objects.filter(superior__isnull=False), required=False, label="Áreas de Conhecimento")

    class Meta:
        model = PessoaExternaObra
        exclude = ('pessoa_fisica', 'autocadastro', 'validado_em', 'validado_por')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['cpf'].initial = self.instance.pessoa_fisica.cpf
            self.fields['eh_parecerista'].initial = self.instance.pessoa_fisica.user.groups.filter(name='Parecerista de Obra').exists()
            self.fields['email_secundario'].initial = self.instance.pessoa_fisica.email_secundario
            if AreaConhecimentoParecerista.objects.filter(parecerista=self.instance.pessoa_fisica).exists():
                self.initial['areas_de_conhecimento'] = [f.id for f in AreaConhecimentoParecerista.objects.filter(parecerista=self.instance.pessoa_fisica)[0].areas_de_conhecimento.all()]

    def clean_cpf(self):
        prestador = PrestadorServico.objects.filter(cpf=self.cleaned_data['cpf'])
        if prestador:
            pessoas_externas = PessoaExternaObra.objects.filter(pessoa_fisica=prestador[0])
            erro = False
            if not self.instance.id and pessoas_externas.exists():
                erro = True
            else:
                if pessoas_externas.exclude(id=self.instance.id).exists():
                    erro = True
            if erro:
                raise forms.ValidationError('Já existe uma pessoa externa cadastrada com este CPF.')
        return self.cleaned_data['cpf']

    def clean(self):
        if (
            self.cleaned_data.get('email_secundario')
            and not Configuracao.get_valor_por_chave('rh', 'permite_email_institucional_email_secundario')
            and Configuracao.eh_email_institucional(self.cleaned_data.get('email_secundario'))
        ):
            raise forms.ValidationError('Escolha um e-mail que não seja institucional.')
        return super().clean()

    @transaction.atomic
    def save(self, commit=True):

        nome = self.cleaned_data['nome']
        cpf = self.cleaned_data['cpf']
        email = self.cleaned_data['email']
        numero_telefone = self.cleaned_data['telefone']
        eh_parecerista = self.cleaned_data.get('eh_parecerista')
        areas_de_conhecimento = self.cleaned_data.get('areas_de_conhecimento')
        email_secundario = self.cleaned_data['email_secundario']
        username = cpf.replace('.', '').replace('-', '')
        qs = PrestadorServico.objects.filter(cpf=cpf)
        prestador_existente = qs.exists()
        if prestador_existente:
            prestador = qs[0]
        else:
            prestador = PrestadorServico()

        prestador.nome = nome
        prestador.username = username
        prestador.cpf = cpf
        prestador.email = email
        prestador.email_secundario = email_secundario
        prestador.ativo = True
        if not prestador.setor:
            prestador.setor = get_setor_propi()

        prestador.save()

        telefones = prestador.pessoatelefone_set.all()
        if not telefones.exists():
            prestador.pessoatelefone_set.create(numero=numero_telefone)
        else:
            telefone = telefones[0]
            telefone.numero = numero_telefone
            telefone.save()

        avaliador = super().save(False)

        avaliador.pessoa_fisica = prestador
        avaliador.email = email
        avaliador.validado_em = datetime.datetime.now()
        avaliador.validado_por = self.request.user.get_vinculo()
        avaliador.save()
        grupo = Group.objects.get(name='Parecerista de Obra')
        if eh_parecerista:
            avaliador.pessoa_fisica.user.groups.add(grupo)
            if areas_de_conhecimento:
                if AreaConhecimentoParecerista.objects.filter(parecerista=prestador).exists():
                    registro_areas = AreaConhecimentoParecerista.objects.filter(parecerista=prestador)[0]
                else:
                    registro_areas = AreaConhecimentoParecerista()
                    registro_areas.parecerista = prestador
                    registro_areas.save()
                for item in areas_de_conhecimento:
                    registro_areas.areas_de_conhecimento.add(item)
        else:
            avaliador.pessoa_fisica.user.groups.remove(grupo)
        try:
            LdapConf = apps.get_model('ldap_backend', 'LdapConf')
            conf = LdapConf.get_active()
            conf.sync_user(prestador)
        except Exception:
            pass

        if not prestador_existente:
            self.enviar_email(prestador.username, email)

        return avaliador

    def enviar_email(self, username, email):
        obj = TrocarSenha.objects.create(username=username)
        url = f'{settings.SITE_URL}/comum/trocar_senha/{obj.username}/{obj.token}/'
        conteudo = '''
        <h1>Pesquisa</h1>
        <h2>Cadastro de Pessoa Externa</h2>
        <p>Prezado usuário,</p>
        <br />
        <p>Você acaba de ser cadastrado como pessoa externa vinculada à obra.</p>
        <p>Caso ainda não tenha definido uma senha de acesso, por favor, acesse: {}.</p>
        <br />
        <p>Caso o token seja inválido, informe o seu cpf nos campos 'usuário' e 'cpf' ('usuário' tem que ser sem pontuação).</p>
        <p>Em seguida será reenviado um email com as instruções para criação da senha de acesso.</p>
        '''.format(
            url
        )
        return send_mail('[SUAP] Cadastro de Avaliador Externo', conteudo, settings.DEFAULT_FROM_EMAIL, [email])


class EstatisticasForm(forms.FormPlus):
    METHOD = 'GET'

    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap(), empty_label='Selecione um Campus', label='Filtrar por Campus:', required=False)

    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    edital = forms.ModelChoiceField(queryset=Edital.objects, empty_label='Selecione um Edital', label='Filtrar por Edital:', required=False)

    formato_edital = forms.ChoiceField(
        choices=[('', 'Todos'), (Edital.FORMATO_COMPLETO, Edital.FORMATO_COMPLETO), (Edital.FORMATO_SIMPLIFICADO, Edital.FORMATO_SIMPLIFICADO)],
        required=False,
        label='Formato do Edital:',
    )

    TODOS = 'Todos'
    PROJETOS_ENVIADOS = 'Projetos Enviados'
    PROJETOS_PRE_SELECIONADOS = 'Projetos Pré-Selecionados'
    PROJETOS_APROVADOS = 'Projetos Aprovados'
    PROJETOS_EM_EXECUCAO = 'Projetos em Execução'
    PROJETOS_CONCLUIDOS = 'Projetos Concluídos'
    PROJETOS_CANCELADOS = 'Projetos Cancelados'
    PROJETOS_INATIVADOS = 'Projetos Inativados'

    AVALIACAO_STATUS = (
        (TODOS, TODOS),
        (PROJETOS_ENVIADOS, PROJETOS_ENVIADOS),
        (PROJETOS_PRE_SELECIONADOS, PROJETOS_PRE_SELECIONADOS),
        (PROJETOS_APROVADOS, PROJETOS_APROVADOS),
        (PROJETOS_EM_EXECUCAO, PROJETOS_EM_EXECUCAO),
        (PROJETOS_CONCLUIDOS, PROJETOS_CONCLUIDOS),
        (PROJETOS_CANCELADOS, PROJETOS_CANCELADOS),
        (PROJETOS_INATIVADOS, PROJETOS_INATIVADOS),
    )

    situacao = forms.ChoiceField(choices=AVALIACAO_STATUS, label='Filtrar por Situação', required=False)

    grupo_pesquisa = forms.ModelChoiceFieldPlus(
        queryset=GrupoPesquisa.objects,
        empty_label='Selecione um Grupo de Pesquisa',
        label='Filtrar por Grupo de Pesquisa:',
        widget=AutocompleteWidget(search_fields=GrupoPesquisa.SEARCH_FIELDS),
        required=False,
    )

    class Media:
        js = ['/static/pesquisa/js/meusprojetosform.js']

    def __init__(self, *args, **kwargs):
        self.ano = kwargs.pop('ano', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []
        if editais.exists():
            ANO_CHOICES.append(['', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            ANO_CHOICES += [(ano, str(ano)) for ano in range(ano_limite, ano_inicio, -1)]
        else:
            ANO_CHOICES.append(['', 'Nenhum edital cadastrado'])

        if self.ano:
            self.fields['edital'].queryset = Edital.objects.filter(inicio_inscricoes__year=self.ano)
        self.fields['ano'].choices = ANO_CHOICES
        if not self.request.user.has_perm('pesquisa.add_origemrecursoedital'):
            del self.fields['campus']
        self.fields['grupo_pesquisa'].queryset = GrupoPesquisa.objects.filter(id__in=Projeto.objects.all().values_list('grupo_pesquisa', flat=True))


class RelatorioDimensaoForm(forms.FormPlus):
    METHOD = 'GET'
    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap(), required=False, label='Filtrar por Campus')

    formato_edital = forms.ChoiceField(
        choices=[('Todos', 'Todos'), (Edital.FORMATO_COMPLETO, Edital.FORMATO_COMPLETO), (Edital.FORMATO_SIMPLIFICADO, Edital.FORMATO_SIMPLIFICADO)],
        required=False,
        label='Formato do Edital:',
    )
    ppg = forms.ModelChoiceFieldPlus(queryset=ProgramaPosGraduacao.objects, label='Programa de Pós-Graduação', required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []

        if editais:
            ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            for ano in range(ano_limite, ano_inicio, -1):
                ANO_CHOICES.append([str(ano), str(ano)])
        else:
            ANO_CHOICES.append(['Selecione um ano', 'Nenhum edital cadastrado'])
        if not self.request.user.groups.filter(name__in=['Gerente Sistêmico de Extensão', 'Visualizador de Projetos']):
            del self.fields['campus']

        self.fields['ano'].choices = ANO_CHOICES


class AnexosDiversosProjetoForm(forms.ModelFormPlus):
    descricao = forms.CharField(label='Descrição', required=True)
    vinculo_membro_equipe = forms.ModelChoiceField(Vinculo.objects, required=False, label='Membro da Equipe')
    arquivo_anexo = forms.FileFieldPlus(label='Arquivo')

    class Meta:
        model = ProjetoAnexo
        fields = ['descricao', 'vinculo_membro_equipe', 'desembolso', 'ano', 'mes']

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop('projeto', None)
        self.participacao = kwargs.pop('participacao', None)
        super().__init__(*args, **kwargs)
        self.fields['desembolso'].required = False
        self.fields['ano'].required = False
        self.fields['mes'].required = False
        self.equipe = self.projeto.participacao_set.all()
        self.fields['vinculo_membro_equipe'].queryset = Vinculo.objects.filter(id__in=self.equipe.values_list('vinculo_pessoa', flat=True))

        if self.participacao:
            self.fields['vinculo_membro_equipe'].queryset = Vinculo.objects.filter(id=self.participacao.vinculo_pessoa.id)
            self.fields['descricao'].initial = 'Termo de Desligamento - %s' % self.participacao.pessoa.nome
            self.fields['descricao'].widget.attrs['readonly'] = True
        self.fields['desembolso'].queryset = Desembolso.objects.filter(projeto=self.projeto).order_by('despesa', 'mes', 'ano')

    def clean(self):
        if self.cleaned_data.get('mes') and not self.cleaned_data.get('ano'):
            self.add_error('ano', 'Informe o ano.')

        return super().clean()


class ListaMensalBolsistaForm(forms.FormPlus):
    METHOD = 'GET'
    ano = forms.ModelChoiceField(queryset=Ano.objects, label='Informe o Ano')
    mes = forms.ChoiceField(
        label='Informe o Mês',
        choices=[
            [1, 'Janeiro'],
            [2, 'Fevereiro'],
            [3, 'Março'],
            [4, 'Abril'],
            [5, 'Maio'],
            [6, 'Junho'],
            [7, 'Julho'],
            [8, 'Agosto'],
            [9, 'Setembro'],
            [10, 'Outubro'],
            [11, 'Novembro'],
            [12, 'Dezembro'],
        ],
    )
    edital = forms.ModelChoiceField(Edital.objects.order_by('-inicio_inscricoes'), required=False)


class DataInativacaoForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Data de Inativação', required=True)
    justificativa = forms.CharFieldPlus(label='Justificativa', max_length=1000, required=True, widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop("projeto", None)
        self.participacao = kwargs.pop("participacao", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        data_informada = self.cleaned_data.get('data')
        if data_informada and data_informada > self.projeto.fim_execucao:
            raise forms.ValidationError('A data de inativação não pode ser após o fim do projeto.')
        if data_informada:
            historicos = HistoricoEquipe.objects.filter(projeto=self.projeto, participante=self.participacao).order_by('-id')
            if historicos.exists():
                ultimo_historico = historicos[0]
                if ultimo_historico.data_movimentacao > self.cleaned_data.get('data'):
                    raise forms.ValidationError('A data de inativação não pode ser menor do que a data de início do vínculo atual.')
        return cleaned_data


class LaboratorioPesquisaForm(forms.ModelFormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', required=True, widget=forms.Textarea())
    servicos_realizados = forms.CharFieldPlus(label='Serviços Realizados', required=False, widget=forms.Textarea())
    membros = forms.MultipleModelChoiceFieldPlus(
        label='Membros',
        queryset=Vinculo.objects.filter(tipo_relacionamento__in=ContentType.objects.filter(Vinculo.SERVIDOR | Vinculo.ALUNO).values_list('id', flat=True)),
        required=False,
    )
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=True)

    class Meta:
        model = LaboratorioPesquisa
        fields = ('nome', 'coordenador', 'uo', 'descricao', 'contato', 'area_pesquisa', 'sala', 'servicos_realizados', 'horario_funcionamento', 'membros')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.request.user.has_perm('pesquisa.add_origemrecursoedital'):
            self.fields['sala'].required = False
        elif self.instance.pk and self.request.user.get_relacionamento() == self.instance.coordenador:
            self.fields['nome'].widget.attrs.update(readonly='readonly')
            self.fields['coordenador'].widget = forms.HiddenInput()
            self.fields['uo'].widget = forms.HiddenInput()
        if self.instance.pk:
            self.fields['sala'].queryset = Sala.ativas.filter(predio__uo=self.instance.uo)


class EquipamentoLaboratorioForm(forms.ModelFormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', widget=forms.Textarea())

    class Meta:
        model = EquipamentoLaboratorioPesquisa
        fields = ('nome', 'descricao', 'patrimonio', 'situacao', 'imagem')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['imagem'].required = False
        Inventario = apps.get_model('patrimonio', 'Inventario')
        if not Inventario:
            del self.fields['patrimonio']


class FotoLaboratorioForm(forms.ModelFormPlus):
    class Meta:
        model = FotoLaboratorioPesquisa
        fields = ('descricao', 'imagem')


class SituacaoObraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = ('situacao',)


class RegistroConclusaoProjetoObsForm(forms.ModelFormPlus):
    class Meta:
        model = RegistroConclusaoProjeto
        fields = ['obs_avaliador']


class AreaConhecimentoPareceristaForm(forms.ModelFormPlus):
    areas_de_conhecimento = forms.ModelMultiplePopupChoiceField(AreaConhecimento.objects.filter(superior__isnull=False), required=False, label="Áreas de Conhecimento")

    class Meta:
        model = AreaConhecimentoParecerista
        fields = ('areas_de_conhecimento',)


class EditarHistoricoEquipeForm(forms.ModelFormPlus):
    class Meta:
        model = HistoricoEquipe
        fields = ('data_movimentacao', 'data_movimentacao_saida', 'vinculo', 'carga_horaria', 'obs')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_movimentacao'].label = 'Data de Início'
        self.fields['data_movimentacao_saida'].label = 'Data de Término'
        self.fields['obs'].label = 'Observações'
        self.fields['obs'].required = False


class AlterarAutorForm(forms.ModelFormPlus):
    submetido_por_vinculo = forms.ModelChoiceFieldPlus(Vinculo.objects, required=True)

    class Meta:
        model = Obra
        fields = ('submetido_por_vinculo',)


class PareceristasObraForm(forms.FormPlus):
    METHOD = 'GET'
    palavra_chave = forms.CharField(label='Nome', required=False)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo().all(), label='Campus', required=False)
    area_conhecimento = forms.ModelChoiceField(
        queryset=AreaConhecimento.objects.all().order_by('descricao'), empty_label='Selecione uma Área de Conhecimento', label='Filtrar por Área de Conhecimento:', required=False
    )


class ClonarProjetoForm(forms.FormPlus):
    edital = forms.ModelChoiceField(Edital.objects, required=False, label='Filtrar por Edital')
    clona_equipe = forms.BooleanField(label='Equipe', initial=True, required=False)
    clona_atividade = forms.BooleanField(label='Metas/Atividades', initial=True, required=False)
    clona_memoria_calculo = forms.BooleanField(label='Memória de Cálculo', initial=True, required=False)
    clona_desembolso = forms.BooleanField(label='Desembolso', initial=True, required=False)
    data_inicio = forms.DateFieldPlus(label='Data de Início')
    data_fim = forms.DateFieldPlus(label='Data de Término')

    fieldsets = (
        ('Selecione o Projeto a Ser Clonado', {'fields': ('edital', 'projeto')}),
        ('Selecione os Dados a Serem Clonados', {'fields': ('clona_equipe', 'clona_atividade', 'clona_memoria_calculo', 'clona_desembolso')}),
        ('Informe o Período do Novo Projeto', {'fields': (('data_inicio', 'data_fim'),)}),
    )

    def __init__(self, *args, **kwargs):
        self.edital = kwargs.pop('edital', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        projetos = Projeto.objects.filter(id__in=Participacao.objects.filter(vinculo_pessoa=self.request.user.get_vinculo(), responsavel=True).values_list('projeto', flat=True))

        self.fields['projeto'] = forms.ChainedModelChoiceField(
            projetos, label='Projeto:', empty_label='Selecione o Edital', required=True, obj_label='titulo', form_filters=[('edital', 'edital')]
        )
        self.fields['edital'].queryset = Edital.objects.filter(id__in=projetos.values_list('edital', flat=True))

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if cleaned_data.get('clona_desembolso') and not cleaned_data.get('clona_memoria_calculo'):
            self.add_error('clona_desembolso', 'Não é possível clonar os desembolsos sem clonar a memória de cálculo.')

    def processar(self):
        return self.cleaned_data.get('projeto').clonar_projeto(
            edital=self.edital,
            clona_equipe=self.cleaned_data.get('clona_equipe'),
            clona_atividade=self.cleaned_data.get('clona_atividade'),
            clona_memoria_calculo=self.cleaned_data.get('clona_memoria_calculo'),
            clona_desembolso=self.cleaned_data.get('clona_desembolso'),
            data_inicio=self.cleaned_data.get('data_inicio'),
            data_fim=self.cleaned_data.get('data_fim'),
        )


class ComissaoAvaliacaoForm(forms.ModelFormPlus):
    SUBMIT_LABEL = 'Continuar >>'
    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    edital = forms.ModelChoiceField(queryset=Edital.objects.order_by('-id'), label='Filtrar por Edital:', required=True)

    uo = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.uo(), empty_label='Selecione um Campus', label='Filtrar por Campus:', required=False)

    class Meta:
        model = ComissaoEditalPesquisa
        fields = ('ano', 'edital', 'uo')

    class Media:
        js = ['/static/pesquisa/js/meusprojetosform.js']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if not self.request.user.groups.filter(name='Diretor de Pesquisa'):
            if self.request.user.groups.filter(name='Coordenador de Pesquisa'):
                self.fields['edital'].queryset = Edital.objects.filter(forma_selecao=Edital.CAMPUS).order_by('-id')
            else:
                self.fields['edital'].queryset = Edital.objects.filter(forma_selecao=Edital.GERAL).order_by('-id')

        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []

        if editais:
            ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            for ano in range(ano_limite, ano_inicio, -1):
                ANO_CHOICES.append([str(ano), str(ano)])
        else:
            ANO_CHOICES.append(['Selecione um ano', 'Nenhum edital cadastrado'])

        self.fields['ano'].choices = ANO_CHOICES

        if not self.request.user.groups.filter(name='Diretor de Pesquisa'):
            self.fields['uo'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(id=get_uo(self.request.user).id), required=True)
            self.fields['uo'].initial = get_uo(self.request.user).id

    def clean(self):
        cleaned_data = super().clean()
        comissao_existe = None

        if not self.cleaned_data.get('edital'):
            raise forms.ValidationError('Selecione um edital.')

        if self.request.user.groups.filter(name='Pré-Avaliador Sistêmico de Projetos de Pesquisa'):
            comissao_existe = ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data['edital'])

        if self.request.user.groups.filter(name='Coordenador de Pesquisa'):
            comissao_existe = ComissaoEditalPesquisa.objects.filter(edital=self.cleaned_data['edital'], uo=get_uo(self.request.user))

        if comissao_existe:
            raise forms.ValidationError('Já existe uma comissão cadastrada para este edital.')

        return cleaned_data


class ComissaoAvaliacaoPorAreaForm(forms.FormPlus):
    area_conhecimento = forms.ModelChoiceField(
        AreaConhecimento.objects.filter(superior__isnull=False).order_by('descricao'), required=False, label="Filtrar por Área de Conhecimento"
    )


class ClonarEtapaForm(forms.FormPlus):
    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop('projeto', None)
        super().__init__(*args, **kwargs)
        self.fields['meta'] = forms.ModelChoiceField(Meta.objects.filter(projeto=self.projeto).order_by('ordem'), label='Selecione a Meta')
        self.fields['etapa'] = forms.ChainedModelChoiceField(
            Etapa.objects.filter(meta__projeto=self.projeto).order_by('ordem'),
            label='Selecione a Atividade:',
            empty_label='Selecione a meta',
            required=True,
            obj_label='descricao',
            form_filters=[('meta', 'meta')],
        )


class AlterarChefiaForm(forms.ModelFormPlus):
    responsavel_anuencia = forms.ModelChoiceField(label='Servidor', queryset=Servidor.objects, required=True, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))

    class Meta:
        model = Projeto
        fields = ('responsavel_anuencia',)


class InativarProjetoForm(forms.ModelFormPlus):
    motivo_inativacao = forms.CharFieldPlus(label='Motivo da Inativação', widget=forms.Textarea())

    class Meta:
        model = Projeto
        fields = ('motivo_inativacao',)


class EmailCoordenadoresForm(forms.FormPlus):
    PROJETOS_EM_EDICAO = 'Projetos em Edição'
    PROJETOS_ENVIADOS = 'Projetos Enviados'
    PROJETOS_PRE_SELECIONADOS = 'Projetos Pré-Selecionados'
    PROJETOS_EM_EXECUCAO = 'Projetos em Execução'
    PROJETOS_EM_ATRASO = 'Projetos em Atraso'
    PROJETOS_CONCLUIDOS = 'Projetos Concluídos'
    AVALIACAO_STATUS = (
        (PROJETOS_EM_EDICAO, PROJETOS_EM_EDICAO),
        (PROJETOS_ENVIADOS, PROJETOS_ENVIADOS),
        (PROJETOS_PRE_SELECIONADOS, PROJETOS_PRE_SELECIONADOS),
        (PROJETOS_EM_EXECUCAO, PROJETOS_EM_EXECUCAO),
        (PROJETOS_EM_ATRASO, PROJETOS_EM_ATRASO),
        (PROJETOS_CONCLUIDOS, PROJETOS_CONCLUIDOS),
    )

    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    edital = forms.ModelChoiceFieldPlus(queryset=Edital.objects, empty_label='Selecione um Edital', label='Filtrar por Edital:', required=True)
    situacao = forms.ChoiceField(choices=AVALIACAO_STATUS, label='Filtrar por Situação', required=False)

    class Media:
        js = ['/static/pesquisa/js/meusprojetosform.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.request.user.groups.filter(name__in=['Gerente Sistêmico de Extensão', 'Coordenador de Extensão']):
            self.fields['edital'].queryset = Edital.objects.all()

        ano_limite = datetime.date.today().year
        editais = Edital.objects.all().order_by('inicio_inscricoes')
        ANO_CHOICES = []

        if editais:
            ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
            ano_inicio = editais[0].inicio_inscricoes.year - 1
            for ano in range(ano_limite, ano_inicio, -1):
                ANO_CHOICES.append([str(ano), str(ano)])
        else:
            ANO_CHOICES.append(['Selecione um ano', 'Nenhum edital cadastrado'])

        self.fields['ano'].choices = ANO_CHOICES


class SolicitarAlteracaoEquipeForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoAlteracaoEquipe
        fields = ('descricao',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].widget = forms.Textarea()


class AvaliarAlteracaoEquipeForm(forms.ModelFormPlus):
    atendida = forms.BooleanField(label='Atendida', required=False)

    class Meta:
        model = SolicitacaoAlteracaoEquipe
        fields = ('atendida', 'justificativa')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['justificativa'].widget = forms.Textarea()


class RegistrarFrequenciaForm(forms.ModelFormPlus):
    data_fim = forms.DateFieldPlus(label='Até o dia', help_text='Caso este campo seja preenchido, será gerado um registro para cada dia do período informado.', required=False)

    class Meta:
        model = RegistroFrequencia
        fields = ('descricao', 'data', 'data_fim', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].widget = forms.Textarea()

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()

        if self.cleaned_data.get('data') and self.cleaned_data.get('data').year < (datetime.date.today().year - 2):
            self.add_error('data', 'A data inicial não pode ser tão antiga.')

        if self.cleaned_data.get('data') and self.cleaned_data.get('data_fim') and self.cleaned_data.get('data_fim') < self.cleaned_data.get('data'):
            self.add_error('data_fim', 'A data final precisa ser maior do que a data inicial.')
        if self.cleaned_data.get('data') and self.cleaned_data.get('data_fim') and self.cleaned_data.get('data_fim').year > datetime.date.today().year:
            self.add_error('data_fim', 'A data final precisa ser este ano.')
        return cleaned_data


class AceiteTermoForm(forms.FormPlus):
    texto = RichTextFormField(label='Termo de Compromisso', required=False)
    aceito = forms.BooleanField(label='Aceito o Termo de Compromisso', required=True, initial=False)
    senha = forms.CharFieldPlus(widget=PasswordInput, required=True, max_length=255, help_text='Digite a mesma senha utilizada para acessar o SUAP.')

    def __init__(self, *args, **kwargs):
        self.participacao = kwargs.pop('participacao', None)
        super().__init__(*args, **kwargs)
        if self.participacao.is_servidor():
            self.fields['texto'].initial = self.participacao.projeto.edital.termo_compromisso_servidor
        elif self.participacao.eh_aluno():
            self.fields['texto'].initial = self.participacao.projeto.edital.termo_compromisso_aluno
        else:
            self.fields['texto'].initial = self.participacao.projeto.edital.termo_compromisso_colaborador_externo
        self.fields['texto'].widget.attrs['readonly'] = True

    def clean_senha(self):
        if not self.cleaned_data['senha']:
            raise ValidationError('Preencha a senha para confirmar a exclusão.')
        if not authenticate(username=self.request.user.username, password=self.cleaned_data['senha']):
            raise ValidationError('Senha incorreta.')


class ServicoLaboratorioForm(forms.ModelFormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', widget=forms.Textarea())
    materiais_utilizados = forms.CharFieldPlus(label='Materiais Utilizados', widget=forms.Textarea())
    equipamentos = forms.ModelMultipleChoiceField(
        queryset=EquipamentoLaboratorioPesquisa.objects, label='Equipamentos Utilizados', required=False, widget=FilteredSelectMultiplePlus('', True)
    )

    class Meta:
        model = ServicoLaboratorioPesquisa
        fields = ('descricao', 'materiais_utilizados', 'equipamentos', 'ativo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipamentos'].queryset = EquipamentoLaboratorioPesquisa.objects.filter(laboratorio=self.instance.laboratorio)
        if self.instance.pk and self.instance.equipamentos.exists():
            self.initial['equipamentos'] = [t.id for t in self.instance.equipamentos.all()]


class MaterialLaboratorioPesquisaForm(forms.ModelFormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', widget=forms.Textarea())
    adicionar_novo = forms.BooleanField(label='Não encontrei o material na lista. Quero cadastrar o novo material.', required=False)

    class Meta:
        model = MaterialLaboratorioPesquisa
        fields = ('material', 'adicionar_novo', 'descricao', 'quantidade', 'valor_unitario', 'imagem')

    class Media:
        js = ['/static/pesquisa/js/materiallaboratoriopesquisaform.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['material'].queryset = MaterialConsumoPesquisa.objects.filter(ativo=True)
        self.fields['material'].required = False
        self.fields['descricao'].required = False
        self.fields['imagem'].required = False
        if self.instance.pk:
            del self.fields['adicionar_novo']
            self.fields['material'].widget.readonly = True


class SolicitarServicoLaboratorioForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoServicoLaboratorio
        fields = ('servico', 'finalidade', 'data', 'hora_inicio', 'hora_termino', 'descricao', 'arquivo')

    def __init__(self, *args, **kwargs):
        self.laboratorio = kwargs.pop('laboratorio', None)
        super().__init__(*args, **kwargs)
        self.fields['descricao'].widget = forms.Textarea()
        self.fields['servico'].queryset = ServicoLaboratorioPesquisa.objects.filter(laboratorio=self.laboratorio)
        self.fields['finalidade'].queryset = FinalidadeServicoLaboratorio.objects.filter(ativo=True)


class AvaliarSolicitacaoLaboratorioForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoServicoLaboratorio
        fields = ('parecer',)

    def __init__(self, *args, **kwargs):
        self.opcao = kwargs.pop('opcao', None)
        super().__init__(*args, **kwargs)
        self.fields['parecer'].label = 'Resposta'
        self.fields['parecer'].widget = forms.Textarea()
        if self.opcao:
            self.fields['parecer'].help_text = 'Informe os dados do agendamento (Data e hora, recomendações, etc.)'
        else:
            self.fields['parecer'].help_text = 'Informe a justificativa'


class MinhasSolicitacoesServicosForm(forms.FormPlus):
    laboratorio = forms.ModelChoiceFieldPlus(queryset=LaboratorioPesquisa.objects, label='Laboratório', required=False)
    situacao = forms.ChoiceField(choices=(('', 'Todas'),) + SolicitacaoServicoLaboratorio.SITUACOES_CHOICES, label='Situação', required=False)


class FiltrarLaboratorioPesquisaForm(forms.FormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=False)
    area_pesquisa = forms.ModelChoiceField(AreaConhecimento.objects, label='Área de Pesquisa', required=False)


class GerarListaFrequenciaForm(forms.FormPlus):
    data_inicio = forms.DateFieldPlus(label='Data de Início', required=False)
    data_termino = forms.DateFieldPlus(label='Data de Término', required=False)
    participante = forms.ModelChoiceFieldPlus(label='Participante', queryset=Vinculo.objects, required=False)

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop('projeto', None)
        super().__init__(*args, **kwargs)
        self.fields['participante'].queryset = Vinculo.objects.filter(id__in=self.projeto.participacao_set.values_list('vinculo_pessoa', flat=True))


class AutoCadastroPareceristaForm(forms.ModelFormPlus):
    cep = forms.BrCepField(max_length=25, required=False, label='CEP', help_text='Formato: "XXXXX-XXX"')
    cidade = forms.ModelChoiceField(queryset=Cidade.objects, label='Cidade', required=True)
    estado_civil = forms.ModelChoiceField(queryset=EstadoCivil.objects, label='Estado Civil', required=True)
    instituicao_origem = forms.ModelChoiceField(queryset=Instituicao.objects, label='Instituição', required=False)
    email_secundario = forms.EmailField(label='Email Alternativo', help_text='Informe um email diferente do institucional.')
    telefone = forms.BrTelefoneField(max_length=255, required=False, label='Telefone', help_text='Formato: "(XX) XXXXX-XXXX"')
    cpf = forms.BrCpfField(max_length=25, required=True, label='CPF', help_text='Formato: "XXX.XXX.XXX-XX"')
    areas_de_conhecimento = forms.ModelMultiplePopupChoiceField(AreaConhecimento.objects.filter(superior__isnull=False), required=True, label="Áreas de Conhecimento")

    class Meta:
        model = PessoaExternaObra
        exclude = ('ativo', 'pessoa_fisica', 'eh_parecerista', 'validado_em', 'validado_por')

    def clean_cpf(self):
        prestador = PrestadorServico.objects.filter(cpf=self.cleaned_data['cpf'])
        if prestador:
            pessoas_externas = PessoaExternaObra.objects.filter(pessoa_fisica=prestador[0])
            erro = False
            if not self.instance.id and pessoas_externas.exists():
                erro = True
            else:
                if pessoas_externas.exclude(id=self.instance.id).exists():
                    erro = True
            if erro:
                raise forms.ValidationError('Já existe uma pessoa externa cadastrada com este CPF.')
        return self.cleaned_data['cpf']

    def clean(self):
        if (
            self.cleaned_data.get('email_secundario')
            and not Configuracao.get_valor_por_chave('rh', 'permite_email_institucional_email_secundario')
            and Configuracao.eh_email_institucional(self.cleaned_data.get('email_secundario'))
        ):
            raise forms.ValidationError('Escolha um e-mail que não seja institucional.')
        return super().clean()

    @transaction.atomic
    def save(self, commit=True):

        nome = self.cleaned_data['nome']
        cpf = self.cleaned_data['cpf']
        email = self.cleaned_data['email']
        numero_telefone = self.cleaned_data['telefone']
        areas_de_conhecimento = self.cleaned_data.get('areas_de_conhecimento')
        email_secundario = self.cleaned_data['email_secundario']
        username = cpf.replace('.', '').replace('-', '')
        qs = PrestadorServico.objects.filter(cpf=cpf)
        prestador_existente = qs.exists()
        if prestador_existente:
            prestador = qs[0]
        else:
            prestador = PrestadorServico()

        prestador.nome = nome
        prestador.username = username
        prestador.cpf = cpf
        prestador.email = email
        prestador.email_secundario = email_secundario
        prestador.ativo = True
        if not prestador.setor:
            prestador.setor = get_setor_propi()

        prestador.save()

        telefones = prestador.pessoatelefone_set.all()
        if not telefones.exists():
            prestador.pessoatelefone_set.create(numero=numero_telefone)
        else:
            telefone = telefones[0]
            telefone.numero = numero_telefone
            telefone.save()

        avaliador = super().save(False)

        avaliador.pessoa_fisica = prestador
        avaliador.email = email
        avaliador.ativo = False
        avaliador.save()
        if areas_de_conhecimento:
            if AreaConhecimentoParecerista.objects.filter(parecerista=prestador).exists():
                registro_areas = AreaConhecimentoParecerista.objects.filter(parecerista=prestador)[0]
            else:
                registro_areas = AreaConhecimentoParecerista()
                registro_areas.parecerista = prestador
                registro_areas.save()
            for item in areas_de_conhecimento:
                registro_areas.areas_de_conhecimento.add(item)

        return avaliador


class ColaboradorExternoForm(forms.ModelFormPlus):
    cpf = forms.BrCpfField(label='CPF', required=False)
    passaporte = forms.CharField(label='Nº do Passaporte', required=False, help_text='Esse campo é obrigatório para estrangeiros. Ex: BR123456')
    nacionalidade = forms.ChoiceField(label='Nacionalidade', choices=Nacionalidade.get_choices(), required=True)
    pais_origem = forms.ModelChoiceFieldPlus(queryset=Pais.objects, label='País de Origem', required=False)
    telefone = forms.BrTelefoneField(max_length=45, label='Telefone para Contato')
    lattes = forms.URLField(label='Lattes', help_text='Endereço do Currículo Lattes', required=False)

    class Meta:
        model = ColaboradorExterno
        exclude = ('ativo', 'prestador')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].help_text = 'Informe um email diferente do institucional.'
        if self.instance and self.instance.pk:
            self.fields['cpf'].initial = self.instance.prestador.cpf
            self.fields['passaporte'].initial = self.instance.prestador.passaporte
            self.fields['nacionalidade'].initial = self.instance.prestador.nacionalidade
            self.fields['pais_origem'].initial = self.instance.prestador.pais_origem

    def clean_passaporte(self):
        nacionalidade = self.cleaned_data.get('nacionalidade')
        passaporte = self.cleaned_data.get('passaporte')
        if nacionalidade and int(nacionalidade) == Nacionalidade.ESTRANGEIRO:
            if not passaporte:
                self.add_error('passaporte', 'Informe o passaporte.')
            prestador = PrestadorServico.objects.filter(passaporte=passaporte)
            if self.instance.id:
                prestador = prestador.exclude(id=self.instance.prestador.id)
            if prestador.exists():
                self.add_error('passaporte', 'Este passaporte já está sendo usado por outro prestador.')
        return passaporte

    def clean(self):
        if (
            self.cleaned_data.get('email')
            and not Configuracao.get_valor_por_chave('rh', 'permite_email_institucional_email_secundario')
            and Configuracao.eh_email_institucional(self.cleaned_data.get('email'))
        ):
            self.add_error('email', 'Escolha um e-mail que não seja institucional.')
        nacionalidade = self.cleaned_data.get('nacionalidade')
        cpf = self.cleaned_data.get('cpf')
        pais_origem = self.cleaned_data.get('pais_origem')
        try:
            eh_estrangeiro = int(nacionalidade) == Nacionalidade.ESTRANGEIRO
        except Exception:
            eh_estrangeiro = False
        if not cpf and not eh_estrangeiro:
            self.add_error('cpf', "O campo CPF é obrigatório para nacionalidade Brasileira.")

        if eh_estrangeiro and not pais_origem:
            self.add_error('pais_origem', "O campo de país de origem é obrigatório para estrangeiros.")

        return super().clean()

    @transaction.atomic
    def save(self, commit=True):

        nome = self.cleaned_data['nome']
        cpf = self.cleaned_data['cpf']
        email = self.cleaned_data['email']
        numero_telefone = self.cleaned_data['telefone']
        nacionalidade = self.cleaned_data['nacionalidade']
        passaporte = self.cleaned_data['passaporte']
        pais_origem = self.cleaned_data['pais_origem']
        if nacionalidade and int(nacionalidade) == Nacionalidade.ESTRANGEIRO and not cpf:
            username = re.sub(r'\W', '', str(passaporte))
        else:
            username = re.sub(r'\D', '', str(cpf))
        qs = PrestadorServico.objects.filter(user__username=username)
        prestador_existente = qs.exists()
        if prestador_existente:
            prestador = qs[0]
        else:
            prestador = PrestadorServico()

        prestador.nome = nome
        prestador.username = username
        prestador.cpf = cpf
        prestador.nacionalidade = nacionalidade
        prestador.passaporte = passaporte
        prestador.pais_origem = pais_origem
        prestador.email = email
        prestador.email_secundario = email
        prestador.ativo = True
        if not prestador.setor:
            prestador.setor = get_setor_propi()

        prestador.save()

        telefones = prestador.pessoatelefone_set.all()
        if not telefones.exists():
            prestador.pessoatelefone_set.create(numero=numero_telefone)
        else:
            telefone = telefones[0]
            telefone.numero = numero_telefone
            telefone.save()

        avaliador = super().save(False)

        avaliador.prestador = prestador
        avaliador.email = email
        avaliador.save()
        try:
            LdapConf = apps.get_model('ldap_backend', 'LdapConf')
            conf = LdapConf.get_active()
            conf.sync_user(prestador)
        except Exception:
            pass

        return avaliador


def ext_combo_template_colaborador(obj):
    identificador = obj.prestador.cpf or obj.prestador.passaporte
    out = [f'<dt class="sr-only">Nome</dt><dd><strong>{obj.nome}</strong> (CPF/Passaporte: {identificador})</dd>']
    if obj.prestador.setor:
        out.append(f'<dt class="sr-only">Setor</dt><dd>{obj.prestador.setor.get_caminho_as_html()}</dd>')
    template = '''<div class="person">
        <dl>{}</dl>
    </div>
    '''.format(
        ''.join(out)
    )
    return template


class ParticipacaoColaboradorForm(forms.ModelFormPlus):
    prestador = forms.ModelChoiceField(
        queryset=ColaboradorExterno.objects.filter(ativo=True),
        widget=AutocompleteWidget(search_fields=['nome', 'prestador__cpf', 'prestador__passaporte'], extraParams=dict(ext_combo_template=ext_combo_template_colaborador)),
        label='Participante',
        required=True,
        help_text='O Colaborador precisa ser cadastrado previamente pelo Coordenador de Pesquisa.',
    )

    data = forms.DateFieldPlus(label='Data de Entrada', help_text='A data não pode ser maior do que hoje.')

    class Meta:
        model = Participacao
        fields = ('carga_horaria', 'prestador', 'data')

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop('projeto', None)
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields.pop('prestador')
            self.historico = HistoricoEquipe.objects.filter(participante=self.instance, projeto=self.instance.projeto).order_by('id')
            self.fields['data'].initial = self.historico[0].data_movimentacao

    def clean(self):
        if self.instance.pk:
            instance = self.instance.projeto
            if self.historico.exists():
                if (
                    self.cleaned_data.get('data')
                    and self.historico.order_by('-id')[0].data_movimentacao_saida
                    and self.cleaned_data.get('data') > self.historico.order_by('-id')[0].data_movimentacao_saida
                ):
                    raise forms.ValidationError(
                        'A data informada é maior do que a data de término do vínculo mais recente do participante, não é possível inserir/editar colaborador.'
                    )
        else:
            instance = self.projeto
        if self.cleaned_data.get('data') and self.cleaned_data.get('data') > instance.fim_execucao:
            raise forms.ValidationError('A data informada é maior do que a data de término do projeto, não é possível inserir/editar colaborador.')
        if self.cleaned_data.get('data') and self.cleaned_data.get('data') < instance.inicio_execucao:
            raise forms.ValidationError('A data informada é anterior a data de início do projeto, não é possível inserir/editar colaborador.')

        if instance.fim_execucao < datetime.date.today():
            raise forms.ValidationError('Data término da execução do projeto é maior que a data atual, não é possível inserir/editar colaborador.')

        return self.cleaned_data


class EditarFrequenciaForm(forms.ModelFormPlus):
    class Meta:
        model = RegistroFrequencia
        fields = ('descricao', 'data', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].widget = forms.Textarea()


class RelatorioProjetoForm(forms.ModelFormPlus):
    class Meta:
        model = RelatorioProjeto
        fields = ('descricao', 'tipo', 'arquivo', 'obs')

    def __init__(self, *args, **kwargs):
        self.projeto = kwargs.pop("projeto", None)
        super().__init__(*args, **kwargs)
        self.fields['obs'].widget = forms.Textarea()

    def clean(self):
        deu_erro = False
        if not self.instance.pk:
            if self.cleaned_data.get('tipo') == RelatorioProjeto.FINAL and RelatorioProjeto.objects.filter(projeto=self.projeto, tipo=RelatorioProjeto.FINAL).exists():
                deu_erro = True
        else:
            if self.cleaned_data.get('tipo') == RelatorioProjeto.FINAL and RelatorioProjeto.objects.filter(projeto=self.projeto, tipo=RelatorioProjeto.FINAL).exclude(id=self.instance.pk).exists():
                deu_erro = True
        if deu_erro:
            self.add_error('tipo', 'Já existe um relatório final cadastrado.')
        return self.cleaned_data


class CancelamentoObraForm(forms.ModelFormPlus):
    class Meta:
        model = Obra
        fields = ('justificativa_cancelamento', )
