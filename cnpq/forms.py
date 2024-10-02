import datetime

import xlrd

from cnpq import tasks
from cnpq.models import (
    PeriodicoRevista,
    ClassificacaoPeriodico,
    ProducaoBibliografica,
    ProducaoTecnica,
    OrientacaoAndamento,
    OrientacaoConcluida,
    RegistroPatente,
    GrupoPesquisa,
    TrabalhoEvento,
    CurriculoVittaeLattes,
)
from comum.models import Ano
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget
from rh.models import UnidadeOrganizacional, Servidor, Titulacao

DOCENTE = 'docente'
TECNICO_ADMINISTRATIVO = 'tecnico_administrativo'

CATEGORIA_CHOICES = (('', 'Todos'), (DOCENTE, 'Docente'), (TECNICO_ADMINISTRATIVO, 'Tecnico Administrativo'))


class ServidoresSemLattesForm(forms.FormPlus):
    SUBMIT_LABEL = 'Buscar'
    IMPORTADOS = 'Importados'
    NAO_IMPORTADOS = 'Não Importados'
    campus = forms.ModelChoiceField(label='Filtrar por Campus', required=False, queryset=UnidadeOrganizacional.objects.suap(), empty_label='Todos')
    categoria = forms.ChoiceField(choices=CATEGORIA_CHOICES, label='Filtrar por Categoria', required=False)
    situacao = forms.ChoiceField(choices=[(IMPORTADOS, IMPORTADOS), (NAO_IMPORTADOS, NAO_IMPORTADOS)], label='Filtrar por Situação', required=False)

    def filtrar(self):
        servidores = Servidor.objects.filter(excluido=False).order_by('nome').distinct()
        if self.cleaned_data.get('campus'):
            servidores = servidores.filter(setor__uo=self.cleaned_data.get('campus'))
        if self.cleaned_data.get('categoria'):
            servidores = servidores.filter(cargo_emprego__grupo_cargo_emprego__categoria=self.cleaned_data.get('categoria'))
        if self.cleaned_data.get('situacao'):
            if self.cleaned_data.get('situacao') == self.IMPORTADOS:
                servidores = servidores.filter(vinculos__vinculo_curriculo_lattes__isnull=False)
            else:
                servidores = servidores.filter(vinculos__vinculo_curriculo_lattes__isnull=True)
        return servidores


class ImportarListaCompletaForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus(help_text='O arquivo deve ser no formato "xls"')

    def clean_arquivo(self):
        arquivo_up = self.cleaned_data.get('arquivo')
        file_contents = arquivo_up.read()
        arquivo_up.seek(0)
        try:
            xlrd.open_workbook(file_contents=file_contents)
        except Exception:
            raise forms.ValidationError('Não foi possível processar a planilha. Verifique se o formato do arquivo é .xls ou .xlsx.')
        return arquivo_up

    def processar(self):
        arquivo_up = self.cleaned_data.get('arquivo')
        file_contents = arquivo_up.read()
        arquivo_up.close()
        return tasks.importar_planilha_periodico_qualis(file_contents)


class AnoResumoForm(forms.FormPlus):
    ano = forms.IntegerField(label='Filtrar a partir do ano de:', required=False, widget=forms.Select())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        maior_ano = datetime.datetime.today().year
        _anos = list(range(maior_ano, 1960, -1))
        ANO_CHOICES = [[a, str(a)] for a in _anos]
        self.fields['ano'].widget.choices = ANO_CHOICES


class PeriodicoRevistaForm(forms.ModelFormPlus):
    class Meta:
        model = PeriodicoRevista
        exclude = ()


class ClassificacaoPeriodicoForm(forms.ModelFormPlus):
    periodico = forms.ModelChoiceField(queryset=PeriodicoRevista.objects, widget=AutocompleteWidget(search_fields=PeriodicoRevista.SEARCH_FIELDS), label='Periódico')

    class Meta:
        model = ClassificacaoPeriodico
        exclude = ()

    def __init__(self, *args, **kwargs):
        editar = kwargs.pop('editar')
        super().__init__(*args, **kwargs)
        self.fields['area_avaliacao'].label = 'Área de Avaliação'
        self.fields['estrato'].label = 'Classificação'
        if editar:
            del self.fields['periodico']


class IndicadoresForm(forms.FormPlus):
    PUBLICACAO_BIBLIOGRAFICA = 'publicacao_bibliografica'
    PRODUCAO_TECNICA = 'producao_tecnica'
    ORIENTACAO_EM_ANDAMENTO = 'orientacao_em_andamento'
    ORIENTACAO_CONCLUIDA = 'orientacao_concluida'
    REGISTRO_PATENTE = 'registro_patente'

    PUBLICACOES_CHOICES = (
        ('', 'Todos'),
        (PUBLICACAO_BIBLIOGRAFICA, 'Publicações Bibliográficas'),
        (PRODUCAO_TECNICA, 'Produções Técnicas'),
        (ORIENTACAO_EM_ANDAMENTO, 'Orientações em Andamento'),
        (ORIENTACAO_CONCLUIDA, 'Orientações Concluídas'),
        (REGISTRO_PATENTE, 'Registros ou Patentes'),
    )

    categoria = forms.ChoiceField(choices=CATEGORIA_CHOICES, label='Filtrar por Categoria:', required=False)
    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap(), label='Filtrar por Campus:', empty_label='Todos', required=False)
    publicacao = forms.ChoiceField(choices=PUBLICACOES_CHOICES, label='Filtrar por Publicação:', required=False)
    servidor = forms.ModelChoiceField(queryset=Servidor.objects.ativos(), widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS), label='Nome/Matrícula do Servidor', required=False)
    grupo_pesquisa = forms.ModelChoiceFieldPlus(queryset=GrupoPesquisa.objects, widget=AutocompleteWidget(search_fields=GrupoPesquisa.SEARCH_FIELDS), label='Grupo de Pesquisa', required=False)
    apenas_no_exercicio = forms.BooleanField(label='Considerar apenas a produção durante o exercício na instituição', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data.get('publicacao'):
            publicacao = self.data.get('publicacao')
            if publicacao:
                campus = self.data.get('campus')
                categoria = self.data.get('categoria')
                tipo_publicacao = self.data.get('tipo_publicacao')

                classe = self.get_classe()
                tipo_publicacao_choices = self.get_tipo_publicacao_choices()
                tipo_publicacao_choices = sorted(list(tipo_publicacao_choices.items()), key=lambda e: e[1])

                # Pega os anos para exibir no filtro somente os anos que tem ocorrência do "Modelo"
                anos = []
                data_anos_qtd = classe.get_anos_qtd(tipo_publicacao, categoria, campus)
                for ano_qtd in data_anos_qtd:
                    ano = ano_qtd[0] and str(ano_qtd[0])
                    if ano:
                        anos.append([ano, ano])

                if tipo_publicacao and tipo_publicacao not in dict(tipo_publicacao_choices):
                    self.data._mutable = True
                    self.data.pop('tipo_publicacao')
                    self.data.pop('ano_ini')
                    self.data.pop('ano_fim')
                    self.data._mutable = False

                self.fields['tipo_publicacao'] = forms.ChoiceField(
                    choices=[('', 'Todos')] + tipo_publicacao_choices,
                    label='Filtrar por Tipo de Publicações:',
                    required=False,
                )

                if tipo_publicacao and tipo_publicacao == 'TRABALHO-EM-EVENTOS':
                    self.fields['natureza_evento'] = forms.ChoiceField(
                        choices=[
                            ('', 'Todos'),
                            (TrabalhoEvento.NATUREZA_COMPLETO, 'Artigo Completo'),
                            (TrabalhoEvento.NATUREZA_RESUMO, 'Resumo'),
                            (TrabalhoEvento.NATUREZA_RESUMO_EXPANDIDO, 'Resumo Expandido'),
                        ],
                        label='Filtrar por Natureza do Evento:',
                        required=False,
                    )
                    self.fields['classificacao_trab'] = forms.ChoiceField(
                        choices=[
                            ('', 'Todos'),
                            ('INTERNACIONAL', 'Internacional'),
                            ('NACIONAL', 'Nacional'),
                            ('REGIONAL', 'Regional'),
                            ('LOCAL', 'Local'),
                            ('NAO_INFORMADO', 'Não Informado'),
                        ],
                        label='Filtrar por Classificação do Evento:',
                        required=False,
                    )
                if tipo_publicacao and tipo_publicacao in ['ARTIGO-PUBLICADO', 'ARTIGO-ACEITO-PARA-PUBLICACAO']:
                    self.fields['qualis_capes'] = forms.ChoiceField(
                        choices=[('', 'Todos'), ('A1', 'A1'), ('A2', 'A2'), ('B1', 'B1'), ('B2', 'B2'), ('B3', 'B3'), ('B4', 'B4'), ('B5', 'B5'), ('C', 'C')],
                        label='Filtrar por Qualis:',
                        required=False,
                    )

                self.fields['ano_ini'] = forms.ChoiceField(
                    choices=[('', 'Todos')] + anos, label='Filtrar por Ano >=:', required=False
                )
                self.fields['ano_fim'] = forms.ChoiceField(
                    choices=[('', 'Todos')] + anos, label='Filtrar por Ano <=:', required=False
                )

    def get_classe(self):
        return self.get_dados()[0]

    def get_tipo_publicacao_choices(self):
        return self.get_dados()[1]

    def get_atributo_tipo_publicacao(self):
        return self.get_dados()[2]

    def get_dados(self):
        publicacao = self.data.get('publicacao')
        classe, choices, atributo_tipo = None, None, None
        if publicacao:
            if publicacao == self.PUBLICACAO_BIBLIOGRAFICA:
                choices = ProducaoBibliografica.tipo_pub_choices
                classe = ProducaoBibliografica
                atributo_tipo = 'tipo_pub'
            elif publicacao == self.PRODUCAO_TECNICA:
                choices = ProducaoTecnica.tipo_pub_choices
                classe = ProducaoTecnica
                atributo_tipo = 'tipo_pub'
            elif publicacao == self.ORIENTACAO_EM_ANDAMENTO:
                choices = OrientacaoAndamento.tipo_choices
                classe = OrientacaoAndamento
                atributo_tipo = 'tipo'
            elif publicacao == self.ORIENTACAO_CONCLUIDA:
                choices = OrientacaoConcluida.tipo_choices
                classe = OrientacaoConcluida
                atributo_tipo = 'tipo'
            elif publicacao == self.REGISTRO_PATENTE:
                choices = RegistroPatente.tipo_choices
                classe = RegistroPatente
                atributo_tipo = 'tipo_pub'

        return classe, choices, atributo_tipo


class ProducaoServidorForm(forms.FormPlus):
    servidor = forms.ModelChoiceField(queryset=Servidor.objects.ativos(), widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS), label='Nome/Matrícula do Servidor', required=False)
    palavra_chave = forms.CharField(label='Palavra-chave', required=False, max_length=255)
    inicio_periodo = forms.ModelChoiceField(Ano.objects, label='Ano inicial:', required=False)
    fim_periodo = forms.ModelChoiceField(Ano.objects, label='Ano final:', required=False)

    def clean(self):
        if (
            self.cleaned_data.get('inicio_periodo')
            and self.cleaned_data.get('fim_periodo')
            and self.cleaned_data.get('fim_periodo').ano < self.cleaned_data.get('inicio_periodo').ano
        ):
            raise forms.ValidationError('O ano final do período deve ser maior ou igual ao ano inicial.')
        if not self.cleaned_data.get('servidor') and not self.cleaned_data.get('palavra_chave'):
            raise forms.ValidationError('Informe um servidor ou uma palavra-chave.')
        return self.cleaned_data


class ProducaoCampusForm(forms.FormPlus):
    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap(), label='Campus', required=True)
    palavra_chave = forms.CharField(label='Palavra-chave', required=False, max_length=255)
    inicio_periodo = forms.ModelChoiceField(Ano.objects, label='Ano inicial:', required=True)
    fim_periodo = forms.ModelChoiceField(Ano.objects, label='Ano final:', required=True)

    def clean(self):
        if (
            self.cleaned_data.get('inicio_periodo')
            and self.cleaned_data.get('fim_periodo')
            and self.cleaned_data.get('fim_periodo').ano < self.cleaned_data.get('inicio_periodo').ano
        ):
            raise forms.ValidationError('O ano final do período deve ser maior ou igual ao ano inicial.')
        return self.cleaned_data


class CampusForm(forms.Form):
    METHOD = 'GET'
    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap(), label='Campus', required=False)


class TitulacaoForm(forms.FormPlus):
    servidor = forms.ModelChoiceField(queryset=Servidor.objects.ativos(), widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS), label='Nome/Matrícula do Servidor', required=False)
    titulacao = forms.ModelChoiceField(queryset=Titulacao.objects, label='Titulação', required=False, empty_label='Todas')
    atuacao = forms.CharField(label='Áreas de Atuação', required=False, max_length=255, help_text='Pode pesquisar pela grande área, área, subárea ou especialidade')
    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap(), label='Campus', required=False, empty_label='Todos')
    grupo_pesquisa = forms.ModelChoiceField(
        queryset=GrupoPesquisa.objects,
        widget=AutocompleteWidget(search_fields=GrupoPesquisa.SEARCH_FIELDS),
        label='Grupo de Pesquisa',
        help_text='Informe o código ou nome do grupo de pesquisa',
        required=False,
    )
    apenas_grupos_pesquisa = forms.BooleanField(label='Apenas com grupos de pesquisa', required=False)
    sexo = forms.ChoiceField(label='Sexo', choices=[['', 'Todos'], ['M', 'Masculino'], ['F', 'Feminino']], required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['grupo_pesquisa'].queryset = GrupoPesquisa.objects.filter(id__in=CurriculoVittaeLattes.objects.values_list('grupos_pesquisa', flat=True))

    def clean(self):
        if (
            not self.cleaned_data.get('servidor')
            and not self.cleaned_data.get('titulacao')
            and not self.cleaned_data.get('atuacao')
            and not self.cleaned_data.get('campus')
            and not self.cleaned_data.get('grupo_pesquisa')
            and not self.cleaned_data.get('sexo')
            and not self.cleaned_data.get('apenas_grupos_pesquisa')
        ):
            raise forms.ValidationError('Informe pelo menos um dos parâmetros de busca.')
        return self.cleaned_data
