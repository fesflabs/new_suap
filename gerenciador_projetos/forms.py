import datetime

from django.core.exceptions import ValidationError
from django.db.models import Max

from comum.models import User, AreaAtuacao
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget
from gerenciador_projetos.enums import TipoRecorrencia, SituacaoProjeto
from gerenciador_projetos.models import Projeto, Tarefa, HistoricoEvolucao, Tag, Lista, TipoAtividade, ListaProjeto, \
    RecorrenciaTarefa
from rh.models import UnidadeOrganizacional


class ProjetoForm(forms.ModelFormPlus):
    areas = forms.MultipleModelChoiceField(AreaAtuacao.objects.filter(ativo=True), required=True, label="Áreas de Atuação:")
    gerentes = forms.MultipleModelChoiceFieldPlus(
        queryset=User.objects,
        label='Gerentes',
        required=True,
    )
    interessados = forms.MultipleModelChoiceFieldPlus(
        queryset=User.objects,
        label='Interessados',
        help_text='Interessados são usuários que possuem acesso de leitura a todas as infromações do projeto.',
        required=False,
    )
    membros = forms.MultipleModelChoiceFieldPlus(
        queryset=User.objects,
        label='Membros',
        help_text='Membros são usuários que podem contribuir com o projeto no desenvolvimento de suas tarefas.',
        required=False,
    )
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap().all(), label='Campus')

    class Meta:
        model = Projeto
        fields = ('areas', 'titulo', 'descricao', 'data_conclusao_estimada', 'uo', 'gerentes', 'interessados', 'membros', 'visibilidade', 'situacao', 'data_conclusao')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        servidores = User.objects.filter(is_active=True, pessoafisica__isnull=False, vinculo__tipo_relacionamento__model__in=['servidor', 'prestadorservico'],)
        self.fields['gerentes'].queryset = servidores
        self.fields['interessados'].queryset = servidores
        self.fields['membros'].queryset = servidores
        self.fields['situacao'].required = False
        self.instance.situacao = SituacaoProjeto.ABERTO
        if not self.instance.pk:
            self.fields['situacao'].widget = forms.HiddenInput()
        else:
            self.fields['areas'].initial = self.instance.areas.all().values_list('pk', flat=True)

    class Media:
        js = ('/static/gerenciador_projetos/js/ProjetoForm.js',)


def TarefaFormFactory(request, projeto, tarefa=None, tarefa_pai=None):
    class TarefaForm(forms.ModelFormPlus):
        descricao = forms.CharField(label='Descrição', widget=forms.Textarea, required=True)
        atribuido_a = forms.MultipleModelChoiceFieldPlus(queryset=User.objects.none(), required=False, label='Atribuído a')
        observadores = forms.MultipleModelChoiceFieldPlus(
            queryset=User.objects,
            label='Observadores',
            help_text='Vincule a esta tarefa usuários que podem ter interesse em acompanhar o andamento da mesma.',
            required=False,
        )
        tags = forms.MultipleModelChoiceFieldPlus(
            queryset=Tag.objects.filter(projeto_id=projeto.id), widget=AutocompleteWidget(multiple=True, search_fields=['nome']), label='Tags', help_text='Vincule tags a esta tarefa', required=False
        )
        data_inicio = forms.DateFieldPlus(label='Data de Início', required=False)
        data_conclusao_estimada = forms.DateFieldPlus(label='Data de Conclusão Estimada', required=False)
        data_conclusao = forms.DateFieldPlus(label='Data de Conclusão', required=False)

        class Meta:
            model = Tarefa
            fields = ['titulo', 'descricao', 'tags', 'tipo_atividade', 'atribuido_a', 'prioridade', 'data_inicio', 'data_conclusao_estimada', 'data_conclusao', 'observadores', 'tarefa_pai']

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            servidores = User.objects.filter(
                is_active=True, pessoafisica__isnull=False, vinculo__tipo_relacionamento__model='servidor', vinculo__tipo_relacionamento__app_label='rh'
            )
            self.fields['observadores'].queryset = servidores
            self.fields['atribuido_a'].queryset = projeto.membros.all() | User.objects.filter(pk__in=projeto.gerentes.values_list('id', flat=True))

            if tarefa_pai:
                self.fields['tarefa_pai'].initial = tarefa_pai
                self.fields['tarefa_pai'].widget.attrs.update(readonly="readonly")
            else:
                tarefas = Tarefa.objects.filter(tarefa_pai__isnull=True, projeto=projeto)
                if tarefa:
                    self.fields['tarefa_pai'].queryset = tarefas.exclude(pk=tarefa.pk)
                else:
                    self.fields['tarefa_pai'].queryset = tarefas

    return TarefaForm


class DashboardForm(forms.FormPlus):
    SITUACAO_CHOICES = (
        (None, '----'),
        ('Aberta', 'Aberta'),
        ('Em Andamento', 'Em Andamento'),
        ('Concluída', 'Concluída'),
    )
    atribuido_a = forms.MultipleModelChoiceFieldPlus(queryset=User.objects.none(), required=False, label='Atribuído a')
    exibir_concluidas = forms.BooleanField(required=False, label='Exibir Concluídas')

    def __init__(self, *args, **kwargs):
        projeto = kwargs.pop('projeto')
        super().__init__(*args, **kwargs)
        self.fields['atribuido_a'].queryset = projeto.membros.all() | User.objects.filter(pk__in=projeto.gerentes.values_list('id', flat=True))


class HistoricoEvolucaoForm(forms.ModelFormPlus):
    class Meta:
        model = HistoricoEvolucao
        fields = ['comentario', 'anexo', 'data_conclusao']


class RecorrenciaTarefaForm(forms.ModelFormPlus):
    dia_do_mes = forms.TypedChoiceField(label='Dia do Mês', choices=[(x, x) for x in range(1, 32)], coerce=int, required=False)

    class Meta:
        model = RecorrenciaTarefa
        fields = ['tipo_recorrencia', 'dia_da_semana', 'dia_do_mes', 'mes_do_ano', 'data_fim']

    class Media:
        js = ('/static/gerenciador_projetos/js/RecorrenciaTarefaForm.js',)

    def clean(self):
        tipo_recorrencia = self.cleaned_data.get('tipo_recorrencia')
        if tipo_recorrencia == TipoRecorrencia.SEMANALMENTE and not self.cleaned_data.get('dia_da_semana'):
            raise forms.ValidationError('É necessário informar o dia da semana para a recorrêncial semanal.')
        elif tipo_recorrencia == TipoRecorrencia.MENSALMENTE and not self.cleaned_data.get('dia_do_mes'):
            raise forms.ValidationError('É necessário informar o dia do mês para a recorrêncial mensal.')
        elif tipo_recorrencia == TipoRecorrencia.ANUALMENTE and (not self.cleaned_data.get('dia_do_mes') or not self.cleaned_data.get('mes_do_ano')):
            raise forms.ValidationError('É necessário informar o dia e mês para a recorrêncial anual.')
        elif tipo_recorrencia == TipoRecorrencia.ANUALMENTE and self.cleaned_data.get('dia_do_mes') and self.cleaned_data.get('mes_do_ano'):
            try:
                datetime.datetime(datetime.date.today().year, int(self.cleaned_data.get('mes_do_ano')), int(self.cleaned_data.get('dia_do_mes')))
            except ValueError:
                raise forms.ValidationError('O Dia/Mês informado ({}/{}) não é válido.'.format(self.cleaned_data.get('dia_do_mes'), self.cleaned_data.get('mes_do_ano')))

        return self.cleaned_data

    def clean_data_fim(self):
        if self.cleaned_data['data_fim'] and self.instance.tarefa.data_conclusao_estimada and (self.cleaned_data['data_fim'] > self.instance.tarefa.data_conclusao_estimada):
            raise forms.ValidationError('A data fim da recorrência não pode ser maior que a data de conclusão estimada da tarefa.')

        return self.cleaned_data['data_fim']


class AtualizarPosicaoListaProjetoForm(forms.FormPlus):
    posicao = forms.IntegerFieldPlus(label='Posição', help_text='Informe a nova posição desta lista no projeto.')


class AdicionarOuVincularListaProjetoForm(forms.FormPlus):
    acao = forms.ChoiceField(label='Ação', widget=forms.RadioSelect(), choices=[['A', 'Adicionar'], ['V', 'Vincular']], initial='A')
    posicao = forms.IntegerFieldPlus(label='Posição', initial=1)
    titulo = forms.CharField(label='Nome', required=False)
    lista = forms.ModelChoiceFieldPlus(queryset=Lista.objects.none(), widget=forms.Select(), required=False, label='Listas Disponíveis')

    class Media:
        js = ('/static/gerenciador_projetos/js/AdicionarOuVincularListaProjetoForm.js',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.projeto = kwargs.pop('projeto')
        super().__init__(*args, **kwargs)
        posicao = ListaProjeto.objects.filter(projeto=self.projeto).aggregate(Max('posicao'))['posicao__max']
        self.fields['lista'].queryset = Lista.get_disponiveis(self.request.user, self.projeto)
        self.fields['posicao'].initial = posicao + 1 if posicao else 1

    def clean(self):
        acao = self.cleaned_data.get('acao')
        lista = self.cleaned_data.get('lista')
        titulo = self.cleaned_data.get('titulo')
        if acao == 'V' and not lista:
            raise ValidationError('Nenhuma lista foi vinculada. Por favor verifique.')
        elif acao == 'A' and not titulo:
            raise ValidationError('Informe um título para criar uma lista vinculada ao projeto.')

        return self.cleaned_data

    def save(self):
        acao = self.cleaned_data.get('acao')
        if acao == 'V':
            ListaProjeto.objects.get_or_create(lista=self.cleaned_data.get('lista'), projeto=self.projeto, posicao=self.cleaned_data.get('posicao'))
        else:
            lista = Lista.objects.get_or_create(nome=self.cleaned_data.get('titulo'), criada_por=self.request.user)[0]
            ListaProjeto.objects.get_or_create(lista=lista, projeto=self.projeto, posicao=self.cleaned_data.get('posicao'))


""" Inicio Admin Forms """


class ListaForm(forms.ModelFormPlus):
    class Meta:
        model = Lista
        fields = ['nome', 'ativa']


class TagForm(forms.ModelFormPlus):
    class Meta:
        model = Tag
        fields = ['nome', 'cor']  # , 'projeto'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['nome'].initial = self.instance.nome
            self.fields['cor'].initial = self.instance.cor


class TipoAtividadeForm(forms.ModelFormPlus):
    class Meta:
        model = TipoAtividade
        fields = ['nome']


class MinhasTarefasForm(forms.FormPlus):
    projeto = forms.ModelChoiceFieldPlus(label='Projetos', queryset=Projeto.objects)

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario')
        super().__init__(*args, **kwargs)
        self.fields['projeto'].queryset = Projeto.objects.filter(tarefa__atribuido_a=usuario).distinct()


class BuscaHistoricoEvolucaoForm(forms.FormPlus):
    data_inicio = forms.DateFieldPlus(label='Data Inicial', required=False)
    data_final = forms.DateFieldPlus(label='Data Final', required=False)
